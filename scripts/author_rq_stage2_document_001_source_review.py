#!/usr/bin/env python3
"""Author the reviewer's candidate-free source review for document 1.

The reviewer read every one of the 50 exact ``fam1968_QxQs.pdf`` page texts
before this table was written.  Every span below is resolved against the exact
UTF-8 page bytes produced by the pinned Poppler derivation, never against a
stage-1 candidate row.  The retained domain is the printed covered-earnings
hierarchy of the 1968 instrument and its question-by-question objectives.

Retention law applied to every page:

* retain a printed question when it collects job identity, job attachment
  quantity, a remuneration amount or rate, a farm or business aggregate
  figure, a role's total earnings, or a role's income source;
* classify a money question as ``remuneration_component_anchor`` and a
  classifying question as ``context_anchor``, both paired with the same-span
  ``field_purpose_prompt``;
* retain a lexeme anchor only where the printed text names the role, job, or
  aggregate node that the retained question measures;
* retain a ``flow_branch_label`` only for an exact printed routing or
  conditional directive, and give an occurrence a nonroot path only where a
  printed directive on its own page explicitly gates it;
* reject prospective job search, labor-supply preferences, health, transfers,
  pensions, property income, other-member grids, general family finances, and
  nonemployment household prose because they establish no realized two-role
  covered-earnings node;
* reject the page-2 work-for-housing valuation sequence and the page-34
  all-family pay-in-kind item because neither resolves to a fixed role and a
  source job; retain the page-44 proxy-respondent text only for role attachment.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_global_q5_intermediate_evidence as source_tools  # noqa: E402
import build_rq_stage1_candidates as stage1_candidates  # noqa: E402

from populace_dynamics.data import (  # noqa: E402
    psid_questionnaire_inventory as questionnaire_inventory,
)

DOCUMENT_SOURCE_POSITION = 1
SCHEMA_VERSION = "rq_stage2_document_source_review.v1"
AUTHORITY_KIND = "reviewer_authored_source_bytes_only_nonauthority"
PAGE_COUNT = 50
PDF_FILENAME = "fam1968_QxQs.pdf"
PDF_SIZE = 19_043_891
PDF_SHA256 = "0689bde3c02bd054cb5b2a25bf8f6cf8a10d26465d669e6c2000ac39daf7a055"
DOCUMENT_ID = (
    "psid-source-document:"
    "cfa4d879a9c44c0e007b397bbaa8afc05db555be0ba08e30a86c04d31bbf06d8"
)
OUTPUT_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_001_fam1968_QxQs_source_review_v1.json"
)
CAPTURE_ROOT = (
    Path("~/PolicyEngine/psid-data").expanduser()
    / "documentation"
    / "capture1"
)
CANONICALIZATION = source_tools.CANONICALIZATION

KIND_ORDER = {
    kind: position
    for position, kind in enumerate(stage1_candidates.OCCURRENCE_KINDS)
}
ANCHOR_KINDS = {
    "role_anchor",
    "job_anchor",
    "remuneration_component_anchor",
    "role_total_anchor",
    "farm_aggregate_anchor",
    "business_aggregate_anchor",
    "context_anchor",
}
COMPONENT_KINDS = {"remuneration_component_anchor", "context_anchor"}
ANCHOR_CLASSIFICATION = {
    "job_anchor": ("job_slot", "source_job"),
    "remuneration_component_anchor": (
        "component_slot",
        "source_remuneration_component",
    ),
    "role_total_anchor": ("aggregate", "role_total"),
    "farm_aggregate_anchor": ("aggregate", "farm_aggregate"),
    "business_aggregate_anchor": ("aggregate", "business_aggregate"),
    "context_anchor": ("component_slot", "source_context"),
}

NO_PARENT_NOTE = (
    "Parent resolution is not applicable to this non-component anchor."
)
PARENT_NOTE = (
    "The parent job or aggregate anchor is the exact printed node that this "
    "retained question measures in the same printed sequence."
)
NO_LOCAL_PARENT_NOTE = (
    "The exact source context names no local job or aggregate parent; it "
    "therefore retains the permitted no-job-context sentinel resolution for "
    "later global assembly."
)

PRINTED_IDENTIFIER_PREFIX_RE = re.compile(
    r"^(?P<identifier>"
    r"(?:[A-N][A-Za-z0-9]*(?:[,-][A-Za-z0-9-]+)*,?"
    r"(?:\([A-Za-z0-9, -]+\))?|I [A-Za-z0-9]+(?:-[A-Za-z0-9]+)?))"
    r"\s{2,}",
    re.ASCII,
)
OCR_IDENTIFIERS_WITHOUT_DIGITS = {"Fl", "FlO", "Gl", "Jl,la", "Jllb"}

C = "context_anchor"
REM = "remuneration_component_anchor"
TOT = "role_total_anchor"
JOB = "job_anchor"
ROLE = "role_anchor"
FARM = "farm_aggregate_anchor"
BUS = "business_aggregate_anchor"
FLOW = "flow_branch_label"
REPEAT = "repeat_or_alias_instruction"
COMPOSITE_CROSS_REFERENCE_RESOLUTION = (
    "document_local_composite_cross_reference_evidence_complete"
)
PURPOSE = "field_purpose_prompt"
INCOME_PATHS = ("p24_farmer", "p24_not_farmer")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256(source_tools.canonical_json_bytes(value))


def page_texts() -> list[str]:
    path = CAPTURE_ROOT / PDF_FILENAME
    raw = path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("fam1968_QxQs.pdf whole-file identity drift")
    if questionnaire_inventory._pdftotext_version() != "26.04.0":
        raise ValueError("document 1 Poppler version drift")
    pages = questionnaire_inventory._pdftotext_pages(path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("document 1 page-count drift")
    return pages


def _byte_offset(page_text: str, char_index: int) -> int:
    return len(page_text[:char_index].encode("utf-8"))


def _char_index(page_text: str, marker: str, occurrence: int) -> int:
    found = 0
    index = page_text.find(marker)
    while index >= 0:
        if found == occurrence:
            return index
        found += 1
        index = page_text.find(marker, index + 1)
    raise ValueError(f"marker not found: {marker!r} #{occurrence}")


def _trimmed_line(
    page_text: str, marker: str, occurrence: int
) -> tuple[int, int]:
    index = _char_index(page_text, marker, occurrence)
    start = page_text.rfind("\n", 0, index) + 1
    end = page_text.find("\n", index)
    if end < 0:
        end = len(page_text)
    if end > start and page_text[end - 1] == "\r":
        end -= 1
    while start < end and page_text[start] in " \t":
        start += 1
    while end > start and page_text[end - 1] in " \t":
        end -= 1
    return _byte_offset(page_text, start), _byte_offset(page_text, end)


def line(marker: str, occurrence: int = 0) -> dict[str, Any]:
    return {"how": "line", "marker": marker, "occurrence": occurrence}


def block(
    first: str,
    last: str,
    first_occurrence: int = 0,
    last_occurrence: int = 0,
) -> dict[str, Any]:
    return {
        "how": "block",
        "first": first,
        "last": last,
        "first_occurrence": first_occurrence,
        "last_occurrence": last_occurrence,
    }


def at(needle: str, occurrence: int = 0) -> dict[str, Any]:
    return {"how": "needle", "needle": needle, "occurrence": occurrence}


def spanned(
    first: str,
    last: str,
    first_occurrence: int = 0,
    last_occurrence: int = 0,
) -> dict[str, Any]:
    """Exact printed slice from the start of ``first`` to the end of ``last``."""

    return {
        "how": "spanned",
        "first": first,
        "last": last,
        "first_occurrence": first_occurrence,
        "last_occurrence": last_occurrence,
    }


def resolve(page_text: str, spec: dict[str, Any]) -> tuple[int, int]:
    how = spec["how"]
    if how == "line":
        return _trimmed_line(page_text, spec["marker"], spec["occurrence"])
    if how == "block":
        start, _ = _trimmed_line(
            page_text, spec["first"], spec["first_occurrence"]
        )
        _, end = _trimmed_line(
            page_text, spec["last"], spec["last_occurrence"]
        )
        if end <= start:
            raise ValueError(
                f"block does not advance: {spec['first']!r} -> {spec['last']!r}"
            )
        return start, end
    if how == "spanned":
        first = _char_index(page_text, spec["first"], spec["first_occurrence"])
        last = _char_index(page_text, spec["last"], spec["last_occurrence"])
        end_index = last + len(spec["last"])
        if end_index <= first:
            raise ValueError(
                f"span does not advance: {spec['first']!r} -> {spec['last']!r}"
            )
        return (
            _byte_offset(page_text, first),
            _byte_offset(page_text, end_index),
        )
    index = _char_index(page_text, spec["needle"], spec["occurrence"])
    return (
        _byte_offset(page_text, index),
        _byte_offset(page_text, index + len(spec["needle"])),
    )


def _char_from_byte(page_text: str, byte_offset: int) -> int:
    return len(page_text.encode("utf-8")[:byte_offset].decode("utf-8"))


def resolve_within(
    page_text: str, spec: dict[str, Any], low: int, high: int
) -> tuple[int, int]:
    """Resolve an anchor needle inside its own retained printed unit."""

    if spec["how"] != "needle":
        return resolve(page_text, spec)
    char_low = _char_from_byte(page_text, low)
    char_high = _char_from_byte(page_text, high)
    window = page_text[char_low:char_high]
    index = _char_index(window, spec["needle"], spec["occurrence"])
    start = char_low + index
    end = start + len(spec["needle"])
    return _byte_offset(page_text, start), _byte_offset(page_text, end)


def unit(
    kind: str,
    where: dict[str, Any],
    anchors: tuple[tuple[str, str, dict[str, Any]], ...] = (),
    parents: tuple[str, ...] = (),
    flow: str | None = None,
    key: str | None = None,
    anchor_key: str | None = None,
    emit_purpose: bool = True,
    repeat: dict[str, Any] | tuple[dict[str, Any], ...] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "where": where,
        "anchors": anchors,
        "parents": parents,
        "flow": flow,
        "key": key,
        "anchor_key": anchor_key,
        "emit_purpose": emit_purpose,
        "repeat": repeat,
    }


# Page -> ordered reviewer units.  Pages absent from this table were reviewed
# in full and carry no lawful covered-earnings occurrence.
PAGES: dict[int, list[dict[str, Any]]] = {
    13: [
        unit(
            C,
            line("Are you working now, unemployed, retired, or what?"),
            anchor_key="p13_f1_context",
        ),
        unit(
            FLOW,
            at("Working now or laid off only temporarily:"),
            key="p13_working",
        ),
        unit(
            PURPOSE,
            block(
                "This includes all persons who have an employer",
                "laid off but know they will be going back to work soon. : · · ·",
            ),
            flow="p13_working",
        ),
        unit(FLOW, at("Unemployed:"), key="p13_unemployed"),
        unit(
            PURPOSE,
            block(
                "All persons who are no t now working",
                "he should be asked the unemployed sequence.",
            ),
            flow="p13_unemployed",
        ),
        unit(
            FLOW,
            at("Retired, Housewife, or Student:"),
            key="p13_retired",
        ),
        unit(
            PURPOSE,
            block(
                "Persons totally and permanently disabled",
                "he should be asked the employed se c tion.",
            ),
            flow="p13_retired",
        ),
    ],
    14: [
        unit(
            C,
            block(
                "What is your main occupation?",
                "What kind of work did you do when you worked?",
            ),
            anchors=(("p14_main_occupation", JOB, at("main occupation")),),
            parents=("p14_main_occupation",),
            flow=("p13_working", "p13_unemployed", "p13_retired"),
            anchor_key="p14_f2_context",
        ),
        unit(
            PURPOSE,
            line("Sections F,G,H refer to Head of the family."),
            anchors=(("p14_head", ROLE, at("Head")),),
            flow=("p13_working", "p13_unemployed", "p13_retired"),
        ),
        unit(
            PURPOSE,
            block(
                "1.   Probe for a clear, complete answer.",
                "workers can be made, which is our objective.",
            ),
            flow=("p13_working", "p13_unemployed", "p13_retired"),
        ),
        unit(
            PURPOSE,
            block(
                "4.   If the Head is unemployed or retired",
                "when he worked, with the above detail.",
            ),
            flow=("p13_unemployed", "p13_retired"),
        ),
        unit(
            PURPOSE,
            block(
                "5.   Particularly unacceptable answers are:",
                "Sailor (officer, enlisted man, deck hand, or what?)",
            ),
            flow=("p13_working", "p13_unemployed", "p13_retired"),
        ),
        unit(
            C,
            line("Do you work for someone else, yourself, or what?"),
            parents=("p14_main_occupation",),
            flow="p13_working",
        ),
        unit(
            PURPOSE,
            block(
                "Do not assume that R is self-employed or not.",
                "it may help us to be sure we get all his jobs .",
            ),
            flow="p13_working",
        ),
    ],
    15: [
        unit(
            C,
            line("How long have you been working for your present employer?"),
            anchors=(("p15_present_employer", JOB, at("present employer")),),
            parents=("p15_present_employer",),
            flow="p13_working",
        ),
        unit(
            PURPOSE,
            spanned(
                "Employer in this question means",
                "here is to get a measure of the steadiness of the head's employment.",
            ),
            flow="p13_working",
        ),
        unit(
            C,
            block(
                "What happened to the job you had before",
                "GS",
            ),
            anchors=(("p15_prior_job", JOB, at("the job you had before")),),
            parents=("p15_prior_job",),
            flow=("p13_working", "p13_unemployed"),
            anchor_key="p15_f7_context",
        ),
        unit(
            PURPOSE,
            spanned(
                "For some young respondents, this question may be irrelevant",
                "for the same company.",
            ),
            flow=("p13_working", "p13_unemployed"),
        ),
        unit(
            C,
            line(
                "Would you say your present job is be t ter than th e one you had before?"
            ),
            anchors=(("p15_present_job", JOB, at("present job")),),
            parents=("p15_present_job",),
            flow="p13_working",
        ),
        unit(
            PURPOSE,
            spanned(
                "It may be better or worse be cause of working c onditions",
                "response.",
            ),
            flow="p13_working",
        ),
        unit(
            FLOW,
            spanned(
                "If the respondent does not mention comparative pay speci-",
                "fically than you should ask F9.",
            ),
            key="p15_ask_f9",
            flow="p13_working",
        ),
        unit(
            C,
            line("Does it pay more than the previous job?"),
            parents=("p15_present_job",),
            flow="p15_ask_f9",
        ),
        unit(
            PURPOSE,
            block(
                'The term "pay more" can mean',
                "on the basis of what his previous job would pay ~ ·",
            ),
            flow="p15_ask_f9",
        ),
        unit(
            C,
            line(
                "How many different employers have you had in the last ten years?"
            ),
            flow=("p13_working", "p13_unemployed"),
            anchor_key="p15_f10_context",
        ),
        unit(
            PURPOSE,
            block(
                '"Different employers" does not mean',
                "a different company, however .",
            ),
            flow=("p13_working", "p13_unemployed"),
        ),
    ],
    18: [
        unit(
            C,
            block(
                "Have you ever been out of a job or on strike for two months or",
                "more at one time? When was the last time that happened?",
            ),
            flow=("p13_working", "p13_unemployed"),
            anchor_key="p18_f31_context",
        ),
        unit(
            PURPOSE,
            block(
                'If R asks, by "out of a job"',
                "employment while off from his main job.",
            ),
            flow=("p13_working", "p13_unemployed"),
        ),
        unit(
            C,
            block(
                "In the last year, how many days were you unemployed",
                "without work?",
            ),
            flow="p13_working",
        ),
        unit(
            PURPOSE,
            block(
                "Again, unemployed means completely without work.",
                "have to ask him how many days he lost from work.",
            ),
            flow="p13_working",
        ),
        unit(
            C,
            block(
                "How many days of work did you miss on your main job",
                "year because you were sick or otherwise unable to work?",
            ),
            anchors=(("p18_main_job", JOB, at("main job")),),
            parents=("p18_main_job",),
            flow="p13_working",
        ),
        unit(
            PURPOSE,
            block(
                "Weather, illness of children, death in the family",
                "respondent was unemployed which have already been counted in F33.",
            ),
            flow="p13_working",
        ),
        unit(
            C,
            line("About how many weeks of vacation did you take last year?"),
            parents=("p18_main_job",),
            flow="p13_working",
        ),
        unit(
            PURPOSE,
            block(
                "Be sure to specify whether the figureR gives is days or weeks.",
                "time he worked in 1967.",
            ),
            flow="p13_working",
        ),
    ],
    19: [
        unit(
            C,
            line(
                "Then how many weeks did you actually work on your main job in 1967?"
            ),
            anchors=(("p19_f36_main_job", JOB, at("main job")),),
            parents=("p19_f36_main_job",),
            flow="p13_working",
            anchor_key="p19_f36_context",
        ),
        unit(
            PURPOSE,
            block(
                '"Weeks actually worked" means',
                'worked should be "47 1/2."',
            ),
            flow="p13_working",
        ),
        unit(
            C,
            line("Do you have a standard workweek on your main job?"),
            anchors=(("p19_f37_main_job", JOB, at("main job")),),
            parents=("p19_f37_main_job",),
            flow="p13_working",
            anchor_key="p19_f37_context",
        ),
        unit(
            PURPOSE,
            block(
                "Some people have very well defined work weeks",
                '"on the average," see Q . F41.',
            ),
            flow="p13_working",
        ),
        unit(
            FLOW,
            at("(IF STANDARD WORKWEEK)"),
            key="p19_standard",
            flow="p13_working",
        ),
        unit(
            C,
            spanned("How many hours a week is that?", "amount to last year?"),
            anchors=(("p19_f38_main_job", JOB, at("main job")),),
            parents=("p19_f38_main_job",),
            flow="p19_standard",
            anchor_key="p19_f38_context",
        ),
        unit(
            PURPOSE,
            block(
                "The answers to the first question may be something like",
                "necessary here.",
            ),
            flow="p19_standard",
        ),
        unit(
            FLOW,
            at("(IF NO STANDARD WORKWEEK)"),
            key="p19_no_standard",
            flow="p13_working",
        ),
        unit(
            C,
            spanned(
                "On the average, how many hours a week",
                "did you work on your main job last year?",
            ),
            anchors=(("p19_f41_main_job", JOB, at("main job")),),
            parents=("p19_f41_main_job",),
            flow="p19_no_standard",
            anchor_key="p19_f41_context",
        ),
        unit(
            PURPOSE,
            block(
                "To get the total hours worked on the main job in 1967",
                "this is okay; just give an explanation in the margin.",
            ),
            flow="p19_no_standard",
        ),
        unit(
            C,
            spanned(
                "Did you have any other jobs",
                "What did you do? Anything else?",
            ),
            anchors=(("p19_extra_jobs", JOB, at("other jobs")),),
            parents=("p19_extra_jobs",),
            flow="p13_working",
        ),
        unit(
            REM,
            spanned(
                "About\n         how much did you make per hour for this?",
                "About\n         how much did you make per hour for this?",
            ),
            parents=("p19_extra_jobs",),
            flow="p13_working",
        ),
        unit(
            PURPOSE,
            block(
                "If R is reluctant to indicate what he did on his second job",
                "counted in reply to hours spent on the main job.",
            ),
            flow="p13_working",
        ),
    ],
    20: [
        unit(
            C,
            line("See F2"),
            parents=("p14_main_occupation",),
            flow="p13_unemployed",
            anchor_key="p20_g1_context",
            emit_purpose=False,
        ),
        unit(
            REPEAT,
            line("See F2"),
            flow="p13_unemployed",
            repeat={
                "relation": "explicit_cross_reference",
                "alias": ("p20_g1_context",),
                "canonical": ("p14_f2_context",),
                "resolution": "document_local_source_evidence_complete",
            },
        ),
        unit(
            C,
            line("See F36~41"),
            flow="p13_unemployed",
            anchor_key="p20_g2_4_context",
            emit_purpose=False,
        ),
        unit(
            REPEAT,
            line("See F36~41"),
            flow="p13_unemployed",
            repeat={
                "relation": "explicit_cross_reference",
                "evidence": (
                    "p19_f36_context",
                    "p19_f37_context",
                    "p19_f38_context",
                    "p19_f41_context",
                    "p20_g2_4_context",
                ),
                "resolution": COMPOSITE_CROSS_REFERENCE_RESOLUTION,
            },
        ),
        unit(
            C,
            line("See F7"),
            parents=("p15_prior_job",),
            flow="p13_unemployed",
            anchor_key="p20_g5_context",
            emit_purpose=False,
        ),
        unit(
            REPEAT,
            line("See F7"),
            flow="p13_unemployed",
            repeat={
                "relation": "explicit_cross_reference",
                "alias": ("p20_g5_context",),
                "canonical": ("p15_f7_context",),
                "resolution": "document_local_source_evidence_complete",
            },
        ),
        unit(
            C,
            line("See FlO"),
            flow="p13_unemployed",
            anchor_key="p20_g6_context",
            emit_purpose=False,
        ),
        unit(
            REPEAT,
            line("See FlO"),
            flow="p13_unemployed",
            repeat={
                "relation": "explicit_cross_reference",
                "alias": ("p20_g6_context",),
                "canonical": ("p15_f10_context",),
                "resolution": "document_local_source_evidence_complete",
            },
        ),
    ],
    21: [
        unit(
            C,
            block(
                'See F31-32. The "last time" here',
                "of unemployment.",
            ),
            flow="p13_unemployed",
            anchor_key="p21_g25_26_context",
            emit_purpose=False,
        ),
        unit(
            REPEAT,
            block(
                'See F31-32. The "last time" here',
                "of unemployment.",
            ),
            flow="p13_unemployed",
            repeat={
                "relation": "explicit_cross_reference",
                "alias": ("p21_g25_26_context",),
                "canonical": ("p18_f31_context",),
                "resolution": "document_local_source_evidence_complete",
            },
        ),
    ],
    22: [
        unit(
            C,
            spanned(
                "Hl-2        During the last year (1967)",
                "money?",
            ),
            flow="p13_retired",
            anchor_key="p22_h1_context",
        ),
        unit(
            C,
            spanned(
                "What\n             kind of work did you do when you worked?",
                "(What was your occupation?)",
            ),
            anchors=(("p22_occupation", JOB, at("occupation")),),
            parents=("p22_occupation",),
            flow="p13_retired",
            anchor_key="p22_h2_context",
        ),
        unit(
            PURPOSE,
            block(
                "See F2 for a suitable reply to the occupation question.",
                "year, and not what they were doing at the time they retired.",
            ),
            flow="p13_retired",
        ),
        unit(
            REPEAT,
            spanned(
                "See F2 for a suitable reply",
                "to the occupation question.",
            ),
            flow="p13_retired",
            repeat=(
                {
                    "relation": "explicit_cross_reference",
                    "alias": ("p22_occupation",),
                    "canonical": ("p14_main_occupation",),
                    "resolution": "document_local_source_evidence_complete",
                },
                {
                    "relation": "explicit_cross_reference",
                    "alias": ("p22_h2_context",),
                    "canonical": ("p14_f2_context",),
                    "resolution": "document_local_source_evidence_complete",
                },
            ),
        ),
        unit(
            C,
            block(
                "See F36-41, remembering that our objective",
                "that R actually worked in 1967.",
            ),
            parents=("p22_occupation",),
            flow="p13_retired",
            anchor_key="p22_h3_4_context",
            emit_purpose=False,
        ),
        unit(
            REPEAT,
            block(
                "See F36-41, remembering that our objective",
                "that R actually worked in 1967.",
            ),
            flow="p13_retired",
            repeat={
                "relation": "explicit_cross_reference",
                "evidence": (
                    "p19_f36_context",
                    "p19_f37_context",
                    "p19_f38_context",
                    "p19_f41_context",
                    "p22_h3_4_context",
                ),
                "resolution": COMPOSITE_CROSS_REFERENCE_RESOLUTION,
            },
        ),
        unit(
            PURPOSE,
            block(
                "See F36-41, remembering that our objective",
                "that R actually worked in 1967.",
            ),
            flow="p13_retired",
        ),
        unit(
            PURPOSE,
            at("SECTION I:     MARITAL STATUS, EMPLOYMENT OF WIFE"),
            anchors=(("p22_wife", ROLE, at("WIFE")),),
        ),
    ],
    23: [
        unit(
            C,
            line("See Fl-2."),
            anchor_key="p23_i9_10_context",
            emit_purpose=False,
        ),
        unit(
            REPEAT,
            line("See Fl-2."),
            repeat={
                "relation": "explicit_cross_reference",
                "evidence": (
                    "p13_f1_context",
                    "p14_f2_context",
                    "p23_i9_10_context",
                ),
                "resolution": COMPOSITE_CROSS_REFERENCE_RESOLUTION,
            },
        ),
        unit(
            C,
            line("See F36 -41."),
            anchor_key="p23_i11_12_context",
            emit_purpose=False,
        ),
        unit(
            REPEAT,
            line("See F36 -41."),
            repeat={
                "relation": "explicit_cross_reference",
                "evidence": (
                    "p19_f36_context",
                    "p19_f37_context",
                    "p19_f38_context",
                    "p19_f41_context",
                    "p23_i11_12_context",
                ),
                "resolution": COMPOSITE_CROSS_REFERENCE_RESOLUTION,
            },
        ),
    ],
    24: [
        unit(
            PURPOSE,
            spanned(
                "The income asked about in this section",
                "important that you try to get complete and accurate responses.",
            ),
        ),
        unit(
            PURPOSE,
            block(
                "We regard the Family Unit as having had the same composition",
                "ask about his work and earnings too.",
            ),
        ),
        unit(FLOW, at("Farmer"), key="p24_farmer"),
        unit(FLOW, at("Not a farmer"), key="p24_not_farmer"),
        unit(
            PURPOSE,
            spanned(
                "A farmer for our purposes",
                "farming.",
            ),
        ),
        unit(
            PURPOSE,
            spanned(
                "We pick up farming as a secondary source of income in Jllb,",
                "for non-farmers.",
            ),
            flow="p24_not_farmer",
        ),
        unit(
            FARM,
            block(
                "What were your total reciepts from farming in 1967",
                "bank payments and commodity credit loans?",
            ),
            flow="p24_farmer",
        ),
        unit(
            PURPOSE,
            block(
                "The following are included here as receipts from normal farming",
                "4) receipts from commodity credit loans",
            ),
            flow="p24_farmer",
        ),
        unit(
            PURPOSE,
            block(
                "Do not include as farming receipts:",
                "3) crop loans   - not income",
            ),
            flow="p24_farmer",
        ),
    ],
    25: [
        unit(
            FARM,
            line(
                "What were your total operating expenses, not counting living expenses?"
            ),
            flow="p24_farmer",
        ),
        unit(
            PURPOSE,
            block(
                "Farm operating expenses may include :",
                "7) Property taxes (but not Federal Income Taxes)",
            ),
            flow="p24_farmer",
        ),
        unit(
            FARM,
            line("That left you a ne t income of ----"),
            flow="p24_farmer",
            anchor_key="p25_farm_net",
        ),
        unit(
            PURPOSE,
            block(
                "Simply defined, farm income equals total receipts",
                "t o discover omissions and correct errors.",
            ),
            flow="p24_farmer",
        ),
        unit(
            BUS,
            block(
                "Did you (Rand Family) own a business at any time during 1967",
                "have a financial interest in any business enterprise?",
            ),
            flow=INCOME_PATHS,
            anchor_key="p25_business",
        ),
        unit(
            PURPOSE,
            block(
                "The respondent need not be a businessman",
                "has money invested in the enterprise .",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            C,
            block(
                "Is it a corporation or an unincorporated business",
                "an interest in both kinds?",
            ),
            parents=("p25_business",),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "If the respondent does not seem to understand the question",
                "clearly for such persons .",
            ),
            flow=INCOME_PATHS,
        ),
    ],
    26: [
        unit(
            FLOW,
            at("(FOR UNINCORPORATED BUSINESSES)"),
            key="p26_unincorporated",
            flow=INCOME_PATHS,
        ),
        unit(
            BUS,
            spanned(
                "How much was your family's share",
                "you took out plus any profits you left in?",
            ),
            flow="p26_unincorporated",
        ),
        unit(
            PURPOSE,
            block(
                "The figure should include the total profits from the business",
                "a salary by the business , that should also be labeled and added in here.",
            ),
            flow="p26_unincorporated",
        ),
        unit(
            TOT,
            block(
                "How much did you (Head) receive from wages and salaries in 1967",
                "before anything was deducted for taxes and other things?",
            ),
            anchors=(("p26_head", ROLE, at("Head")),),
            flow=INCOME_PATHS,
            anchor_key="p26_head_wages_total",
        ),
        unit(
            PURPOSE,
            block(
                "This question applies only to the Head of the family",
                "It's a good idea to probe to make sure in cases where he has two jobs.",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "1. Fixed salary rates:",
                "not R's current salary rate.",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "2. Complicated work history:",
                "down your figuring and sent it along.",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "3. Businessmen: The wages and salaries",
                "some other job should be included here.",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            REM,
            block(
                "In additon to this, did you have any income from bonuses",
                "or commissions? How much was that?",
            ),
            parents=("p26_head_wages_total",),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                'Note the phrase "In addition to this . "',
                "out of the J8 figure.",
            ),
            flow=INCOME_PATHS,
        ),
    ],
    27: [
        unit(
            REM,
            block(
                "Did you (Head) receive · any other income in 1967",
                "practice or trade?",
            ),
            anchors=(
                ("p27_head", ROLE, at("Head")),
                (
                    "p27_professional_trade_job",
                    JOB,
                    at("professional\n        practice or trade"),
                ),
            ),
            parents=("p27_professional_trade_job",),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "1. Income BEFORE TAXES but AFTER EXPENSES",
                "and the latter is included here .",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            FARM,
            at("farming or market gardening"),
            flow="p24_not_farmer",
            anchor_key="p27_secondary_farm",
        ),
        unit(
            PURPOSE,
            block(
                "If farming is R's primary occupation",
                "however .",
            ),
            flow="p24_not_farmer",
        ),
    ],
    28: [
        unit(
            PURPOSE,
            spanned(
                "If R is the owner of a small incorporated business",
                "salary he paid himself should be entered under J8.",
            ),
            flow=INCOME_PATHS,
        ),
    ],
    32: [
        unit(
            TOT,
            line("Wife's _Income"),
            anchors=(("p32_wife", ROLE, at("Wife")),),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "1. Make sure the wife's income from all sources",
                "small the amount .",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "3. If some or all of the wife's income is from work in the family",
                "the source and the fact it was not included in J7.",
            ),
            flow=INCOME_PATHS,
        ),
    ],
    44: [
        unit(PURPOSE, line("Who was respondent?")),
        unit(
            PURPOSE,
            block(
                "We have asked you to interview the head of the FU",
                "other than the head may have been your R.",
            ),
            anchors=(
                ("p44_head", ROLE, at("head")),
                ("p44_proxy_head", ROLE, at("head", 1)),
            ),
        ),
    ],
}

SAME_IDENTIFIER_ALIASES = (
    {
        "alias": "p44_proxy_head",
        "canonical": "p44_head",
    },
)


def _path_sort_key(path: list[str]) -> tuple[bytes, ...]:
    return tuple(item.encode("utf-8") for item in path)


def _branch_ref(review_id: str, parent_path: list[str], count: int) -> str:
    """Address one semantic branch when a printed label has many parents."""

    if count == 1:
        return review_id
    return f"{review_id}#parent-path-" + _canonical_digest(list(parent_path))


def _review_occurrence_id(
    page_number: int, start: int, end: int, kind: str, matched: bytes
) -> str:
    return "rq-review-occurrence:" + _canonical_digest(
        [
            DOCUMENT_ID,
            page_number,
            start,
            end,
            kind,
            _sha256(matched),
        ]
    )


def build_review(pages: list[str]) -> dict[str, Any]:
    raw_rows: list[dict[str, Any]] = []
    anchor_span: dict[str, tuple[int, int, int, str]] = {}
    branch_span: dict[str, tuple[int, int, int]] = {}
    component_parents: dict[tuple[int, int, int, str], tuple[str, ...]] = {}
    repeat_units: dict[tuple[int, int, int], tuple[dict[str, Any], ...]] = {}
    repeat_key_span: dict[str, tuple[int, int, int]] = {}

    def add(page_number, start, end, kind, flow_key):
        raw_rows.append(
            {
                "page": page_number,
                "start": start,
                "end": end,
                "kind": kind,
                "flow": flow_key,
            }
        )

    for page_number in sorted(PAGES):
        text = pages[page_number - 1]
        for item in PAGES[page_number]:
            start, end = resolve(text, item["where"])
            kind = item["kind"]
            add(page_number, start, end, kind, item["flow"])
            if kind == FLOW:
                if item["key"] is None:
                    raise ValueError("a branch label needs a reviewer key")
                branch_span[item["key"]] = (page_number, start, end)
            if kind in {C, REM, TOT, FARM, BUS} and item["emit_purpose"]:
                add(page_number, start, end, PURPOSE, item["flow"])
            if kind in ANCHOR_KINDS and item["anchor_key"] is not None:
                if item["anchor_key"] in anchor_span:
                    raise ValueError(
                        f"duplicate reviewer anchor key: {item['anchor_key']}"
                    )
                anchor_span[item["anchor_key"]] = (
                    page_number,
                    start,
                    end,
                    kind,
                )
            if kind in COMPONENT_KINDS:
                component_parents[(page_number, start, end, kind)] = item[
                    "parents"
                ]
            if kind == REPEAT:
                declared_repeats = item["repeat"] or {
                    "relation": "explicit_repeat_instruction"
                }
                if isinstance(declared_repeats, dict):
                    declared_repeats = (declared_repeats,)
                if not declared_repeats:
                    raise ValueError(
                        "a retained repeat instruction needs downstream facts"
                    )
                repeat_units[(page_number, start, end)] = tuple(
                    declared_repeats
                )
                if item["key"] is not None:
                    if item["key"] in repeat_key_span:
                        raise ValueError(
                            f"duplicate reviewer repeat key: {item['key']}"
                        )
                    repeat_key_span[item["key"]] = (
                        page_number,
                        start,
                        end,
                    )
            for key, anchor_kind, where in item["anchors"]:
                a_start, a_end = resolve_within(text, where, start, end)
                add(page_number, a_start, a_end, anchor_kind, item["flow"])
                if key in anchor_span:
                    raise ValueError(f"duplicate reviewer anchor key: {key}")
                anchor_span[key] = (page_number, a_start, a_end, anchor_kind)

    seen: set[tuple[int, int, int, str]] = set()
    ordered: list[dict[str, Any]] = []
    for row in raw_rows:
        coordinate = (row["page"], row["start"], row["end"], row["kind"])
        if coordinate in seen:
            raise ValueError(f"duplicate reviewer occurrence: {coordinate}")
        seen.add(coordinate)
        ordered.append(row)
    ordered.sort(
        key=lambda row: (
            row["page"],
            row["start"],
            row["end"],
            KIND_ORDER[row["kind"]],
        )
    )

    review_id_by_coordinate: dict[tuple[int, int, int, str], str] = {}
    occurrence_specs: list[dict[str, Any]] = []
    for row in ordered:
        text = pages[row["page"] - 1]
        matched = text.encode("utf-8")[row["start"] : row["end"]]
        matched.decode("utf-8")
        review_id = _review_occurrence_id(
            row["page"], row["start"], row["end"], row["kind"], matched
        )
        coordinate = (row["page"], row["start"], row["end"], row["kind"])
        review_id_by_coordinate[coordinate] = review_id
        occurrence_specs.append(
            {
                "occurrence_kind": row["kind"],
                "page_number": row["page"],
                "parent_review_branch_paths": [[]],
                "review_note": (
                    "Whole-page source review retained this exact UTF-8 "
                    f"{row['kind']} slice."
                ),
                "review_occurrence_id": review_id,
                "utf8_byte_start": row["start"],
                "utf8_byte_end": row["end"],
                "_flow": row["flow"],
            }
        )

    branch_review_id: dict[str, str] = {}
    for key, (page_number, start, end) in branch_span.items():
        branch_review_id[key] = review_id_by_coordinate[
            (page_number, start, end, FLOW)
        ]
    branch_parent_keys: dict[str, tuple[str, ...]] = {}
    for page_number in sorted(PAGES):
        for item in PAGES[page_number]:
            if item["kind"] != FLOW:
                continue
            flow = item["flow"]
            if flow is None:
                branch_parent_keys[item["key"]] = ()
            elif isinstance(flow, str):
                branch_parent_keys[item["key"]] = (flow,)
            else:
                branch_parent_keys[item["key"]] = tuple(flow)

    def parent_paths(key: str) -> list[list[str]]:
        """Complete root-to-parent paths under which this label is printed."""

        parents = branch_parent_keys[key]
        if not parents:
            return [[]]
        paths: list[list[str]] = []
        for parent in parents:
            for path in branch_paths(parent):
                if path not in paths:
                    paths.append(path)
        paths.sort(key=_path_sort_key)
        return paths

    def branch_paths(key: str) -> list[list[str]]:
        """Complete root-to-leaf paths this label itself resolves."""

        prefixes = parent_paths(key)
        count = len(prefixes)
        return [
            [*prefix, _branch_ref(branch_review_id[key], prefix, count)]
            for prefix in prefixes
        ]

    order_index = {
        spec["review_occurrence_id"]: position
        for position, spec in enumerate(occurrence_specs)
    }
    branch_order = {
        branch_review_id[key]: order_index[branch_review_id[key]]
        for key in branch_review_id
    }

    def _order_of(branch_ref: str) -> int:
        return branch_order[branch_ref.split("#parent-path-")[0]]

    branch_key_by_review_id = {
        review_id: key for key, review_id in branch_review_id.items()
    }
    for spec in occurrence_specs:
        flow_key = spec.pop("_flow")
        if spec["occurrence_kind"] == FLOW:
            key = branch_key_by_review_id[spec["review_occurrence_id"]]
            paths = parent_paths(key)
        elif flow_key is None:
            continue
        elif isinstance(flow_key, str):
            paths = branch_paths(flow_key)
        else:
            paths = []
            for key in flow_key:
                for path in branch_paths(key):
                    if path not in paths:
                        paths.append(path)
            paths.sort(key=_path_sort_key)
        if any(
            _order_of(branch) >= order_index[spec["review_occurrence_id"]]
            for path in paths
            for branch in path
        ):
            raise ValueError(
                "a gating branch label must precede the occurrence it gates: "
                f"{flow_key} on page {spec['page_number']}"
            )
        spec["parent_review_branch_paths"] = paths

    anchor_review_id = {
        key: review_id_by_coordinate[(page, start, end, kind)]
        for key, (page, start, end, kind) in anchor_span.items()
    }
    repeat_review_id = {
        key: review_id_by_coordinate[(page, start, end, REPEAT)]
        for key, (page, start, end) in repeat_key_span.items()
    }

    local_anchor_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        kind = spec["occurrence_kind"]
        if kind not in ANCHOR_KINDS:
            continue
        text = pages[spec["page_number"] - 1]
        matched = text.encode("utf-8")[
            spec["utf8_byte_start"] : spec["utf8_byte_end"]
        ].decode("utf-8")
        if kind == "role_anchor":
            node_domain = "role"
            classification = stage1_candidates._role_classification(matched)
        else:
            node_domain, classification = ANCHOR_CLASSIFICATION[kind]
        parents: list[str] = []
        note = NO_PARENT_NOTE
        if kind in COMPONENT_KINDS:
            keys = component_parents.get(
                (
                    spec["page_number"],
                    spec["utf8_byte_start"],
                    spec["utf8_byte_end"],
                    kind,
                ),
                (),
            )
            parents = [anchor_review_id[key] for key in keys]
            note = PARENT_NOTE if parents else NO_LOCAL_PARENT_NOTE
            if kind == REM and len(parents) != 1:
                raise ValueError(
                    "a retained remuneration component needs one exact local "
                    "job or aggregate parent"
                )
            if kind == C and len(parents) > 1:
                raise ValueError(
                    "a retained context component cannot have multiple parents"
                )
        local_anchor_specs.append(
            {
                "classification": classification,
                "classification_status": "provisional_document_local",
                "node_domain": node_domain,
                "parent_resolution_note": note,
                "parent_review_occurrence_ids": parents,
                "printed_identifier": _printed_identifier(
                    text, spec["utf8_byte_start"]
                ),
                "review_occurrence_id": spec["review_occurrence_id"],
            }
        )

    occurrence_by_review_id = {
        item["review_occurrence_id"]: item for item in occurrence_specs
    }
    repeat_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        if spec["occurrence_kind"] != REPEAT:
            continue
        coordinate = (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        for declared in repeat_units[coordinate]:
            alias = [
                anchor_review_id[key] for key in declared.get("alias", ())
            ]
            canonical = [
                anchor_review_id[key] for key in declared.get("canonical", ())
            ]
            evidence = [
                anchor_review_id[key] for key in declared.get("evidence", ())
            ]
            evidence.extend(
                repeat_review_id[key]
                for key in declared.get("evidence_repeats", ())
            )
            evidence = sorted(
                {*evidence, *alias, *canonical, spec["review_occurrence_id"]},
                key=lambda item: order_index[item],
            )
            resolution = declared.get("resolution")
            if resolution == "document_local_source_evidence_complete":
                if len(alias) != 1 or len(canonical) != 1:
                    raise ValueError(
                        "a resolved document-local repeat needs exactly one "
                        "alias and one canonical anchor"
                    )
            elif resolution == COMPOSITE_CROSS_REFERENCE_RESOLUTION:
                evidence_anchor_ids = {
                    item
                    for item in evidence
                    if item in set(anchor_review_id.values())
                }
                same_span_context_ids = {
                    item
                    for item in evidence_anchor_ids
                    if occurrence_by_review_id[item]["occurrence_kind"] == C
                    and (
                        occurrence_by_review_id[item]["page_number"],
                        occurrence_by_review_id[item]["utf8_byte_start"],
                        occurrence_by_review_id[item]["utf8_byte_end"],
                    )
                    == coordinate
                }
                if (
                    declared["relation"] != "explicit_cross_reference"
                    or alias
                    or canonical
                    or len(same_span_context_ids) != 1
                    or len(evidence_anchor_ids - same_span_context_ids) < 2
                    or any(
                        occurrence_by_review_id[item]["occurrence_kind"] != C
                        for item in evidence_anchor_ids
                    )
                ):
                    raise ValueError(
                        "a composite range reference needs no selected alias "
                        "endpoints, its same-span context anchor, and at least "
                        "two exact target-context anchors"
                    )
            else:
                raise ValueError("repeat resolution status is not recognized")
            if resolution == COMPOSITE_CROSS_REFERENCE_RESOLUTION:
                spec["review_note"] = (
                    "Whole-page source review retained this exact UTF-8 "
                    "composite cross-reference instruction, its same-span "
                    "context anchor, and its complete ordered document-local "
                    "target-context evidence. Source interpretation is "
                    "complete; one-to-one global partitioning belongs to the "
                    "later global catalog, and this shard assigns no alias "
                    "endpoint or global ID."
                )
            repeat_specs.append(
                {
                    "alias_anchor_review_occurrence_ids": sorted(
                        alias, key=lambda item: order_index[item]
                    ),
                    "canonical_anchor_review_occurrence_ids": sorted(
                        canonical, key=lambda item: order_index[item]
                    ),
                    "evidence_review_occurrence_ids": evidence,
                    "relation": declared["relation"],
                    "resolution_status": resolution,
                    "review_occurrence_id": spec["review_occurrence_id"],
                    "target_scope": "document_local",
                }
            )
    for declared in SAME_IDENTIFIER_ALIASES:
        alias = anchor_review_id[declared["alias"]]
        canonical = anchor_review_id[declared["canonical"]]
        repeat_specs.append(
            {
                "alias_anchor_review_occurrence_ids": [alias],
                "canonical_anchor_review_occurrence_ids": [canonical],
                "evidence_review_occurrence_ids": sorted(
                    [alias, canonical], key=lambda item: order_index[item]
                ),
                "relation": "same_printed_identifier_and_exact_label",
                "resolution_status": (
                    "document_local_source_evidence_complete"
                ),
                "review_occurrence_id": alias,
                "target_scope": "document_local",
            }
        )

    occurrence_by_page: dict[int, int] = {}
    for spec in occurrence_specs:
        occurrence_by_page[spec["page_number"]] = (
            occurrence_by_page.get(spec["page_number"], 0) + 1
        )
    page_review_rows = []
    for page_number, text in enumerate(pages, start=1):
        retained = occurrence_by_page.get(page_number, 0)
        page_review_rows.append(
            {
                "page_number": page_number,
                "page_text_utf8_sha256": _sha256(text.encode("utf-8")),
                "review_note": (
                    "Whole page reviewed against exact source bytes; "
                    f"{retained} source occurrence atoms retained."
                ),
                "review_status": "complete",
                "whole_page_review_complete": True,
            }
        )

    review: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "review_id": "rq-stage2-source-review:"
        + _canonical_digest([DOCUMENT_ID, DOCUMENT_SOURCE_POSITION]),
        "authority_kind": AUTHORITY_KIND,
        "document_source_position": DOCUMENT_SOURCE_POSITION,
        "source_document_id": DOCUMENT_ID,
        "review_method": {
            "source_rows_derived_from_page_bytes": True,
            "whole_page_review": (
                "all_50_pages_including_empty_occurrence_pages"
            ),
            "span_granularity": (
                "exact_utf8_lexeme_physical_line_or_source_block"
            ),
            "candidate_nonselection": (
                "candidates_joined_only_after_source_rows_complete"
            ),
            "global_ids_assigned": False,
        },
        "page_review_rows": page_review_rows,
        "occurrence_specs": occurrence_specs,
        "local_anchor_specs": local_anchor_specs,
        "repeat_alias_specs": repeat_specs,
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": "complete",
    }
    import copy

    zeroed = copy.deepcopy(review)
    zeroed["integrity"]["content_sha256"] = "0" * 64
    review["integrity"]["content_sha256"] = _canonical_digest(zeroed)
    return review


def _printed_identifier(page_text: str, byte_start: int) -> str | None:
    rows = stage1_candidates._physical_lines(page_text)
    containing_index = None
    for index, row in enumerate(rows):
        line_start = len(page_text[: row["start"]].encode("utf-8"))
        line_end = len(page_text[: row["end"]].encode("utf-8"))
        if line_start <= byte_start < line_end:
            containing_index = index
            break
    if containing_index is None:
        raise ValueError("source review occurrence does not resolve to a line")
    for row in reversed(
        rows[max(0, containing_index - 5) : containing_index + 1]
    ):
        stripped = row["text"].lstrip()
        if stripped.startswith("SECTION "):
            return None
        match = PRINTED_IDENTIFIER_PREFIX_RE.match(stripped)
        if match is None:
            continue
        identifier = match.group("identifier")
        if any(character.isdigit() for character in identifier):
            return identifier
        if identifier in OCR_IDENTIFIERS_WITHOUT_DIGITS:
            return identifier
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    review = build_review(page_texts())
    raw = source_tools.canonical_json_bytes(review)
    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_bytes() != raw:
            raise SystemExit("document 1 source review drift")
        print(f"document 1 source review reproduces: {OUTPUT_PATH}")
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(raw)
    import collections

    census = collections.Counter(
        spec["occurrence_kind"] for spec in review["occurrence_specs"]
    )
    print(f"wrote {OUTPUT_PATH}")
    print(f"occurrences: {len(review['occurrence_specs'])}")
    for kind in stage1_candidates.OCCURRENCE_KINDS:
        print(f"  {kind}: {census[kind]}")
    print(f"local anchors: {len(review['local_anchor_specs'])}")
    print(f"repeat/alias: {len(review['repeat_alias_specs'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
