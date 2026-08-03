#!/usr/bin/env python3
"""Author the reviewer's candidate-free source review for document 9.

The reviewer read every one of the 103 exact ``fam1972_QxQs.pdf`` page texts
before this table was written.  Every span below is resolved against the exact
UTF-8 page bytes produced by the pinned Poppler derivation, never against a
stage-1 candidate row.  The retained domain is the printed covered-earnings
hierarchy of the 1972 instrument and its question-by-question objectives.

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
* reject worklike prose in the children, transportation, housing, commuting,
  housework, food, verbal-test, feelings, time-use, health, past-mobility,
  and observation sequences, which name no covered-earnings node.
"""

from __future__ import annotations

import argparse
import hashlib
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

DOCUMENT_SOURCE_POSITION = 9
SCHEMA_VERSION = "rq_stage2_document_source_review.v1"
AUTHORITY_KIND = "reviewer_authored_source_bytes_only_nonauthority"
PAGE_COUNT = 103
PDF_FILENAME = "fam1972_QxQs.pdf"
PDF_SIZE = 26_299_526
PDF_SHA256 = "a8db4c8732c8386f0d783ee80e8411b61144938946f5d2cdc5bcc4df2176c84f"
DOCUMENT_ID = (
    "psid-source-document:"
    "d2d3202855c5ca4d89846302985b553dd6a615bc4682ecc7a914506c687efb25"
)
OUTPUT_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_009_fam1972_QxQs_source_review_v1.json"
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
    "No printed job or aggregate parent resolves inside this document; the "
    "parent is preserved unresolved for later global assembly."
)

C = "context_anchor"
REM = "remuneration_component_anchor"
TOT = "role_total_anchor"
JOB = "job_anchor"
ROLE = "role_anchor"
FARM = "farm_aggregate_anchor"
BUS = "business_aggregate_anchor"
FLOW = "flow_branch_label"
REPEAT = "repeat_or_alias_instruction"
PURPOSE = "field_purpose_prompt"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256(source_tools.canonical_json_bytes(value))


def page_texts() -> list[str]:
    path = CAPTURE_ROOT / PDF_FILENAME
    raw = path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("fam1972_QxQs.pdf whole-file identity drift")
    if questionnaire_inventory._pdftotext_version() != "26.04.0":
        raise ValueError("document 9 Poppler version drift")
    pages = questionnaire_inventory._pdftotext_pages(path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("document 9 page-count drift")
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
    repeat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "where": where,
        "anchors": anchors,
        "parents": parents,
        "flow": flow,
        "key": key,
        "repeat": repeat,
    }


# Page -> ordered reviewer units.  Pages absent from this table were reviewed
# in full and carry no lawful covered-earnings occurrence.
PAGES: dict[int, list[dict[str, Any]]] = {
    15: [
        unit(FLOW, at("(TURN TO El, PAGE 12)"), key="p15_e"),
        unit(FLOW, at("(IF NOT CLEAR)"), key="p15_notclear"),
        unit(
            FLOW, at("(IF 1 YEAR OR HORE, TURN TO DlO, PAGE 8)"), key="p15_yr"
        ),
        unit(FLOW, at("(IF LESS THAN 1 YEAR)"), key="p15_less"),
        unit(
            C,
            line("We would like to know about your (HEAD"),
            anchors=(
                ("p15_head", ROLE, at("HEAD")),
                ("p15_job", JOB, at("present job")),
            ),
            parents=("p15_job",),
        ),
        unit(
            C,
            line("What is your main occupation?"),
            anchors=(("p15_occ", JOB, at("main occupation")),),
            parents=("p15_job",),
        ),
        unit(C, line("Tell me a little more about"), parents=("p15_job",)),
        unit(
            C, line("What kind of business is that in?"), parents=("p15_job",)
        ),
        unit(
            C,
            line("Do you work for someone else, yourself, or what?"),
            parents=("p15_job",),
        ),
        unit(
            C,
            line("How long have you had this job?"),
            anchors=(("p15_thisjob", JOB, at("this job")),),
            parents=("p15_job",),
        ),
        unit(
            C,
            block(
                "What happened to the job you had before", "laid off, or what?"
            ),
            anchors=(("p15_prior", JOB, at("the job you had before")),),
            parents=("p15_prior",),
            flow="p15_less",
        ),
        unit(
            C,
            line(
                "Does your present job pay more than the one you had before?"
            ),
            parents=("p15_job", "p15_prior"),
            flow="p15_less",
        ),
    ],
    16: [
        unit(
            C,
            line(
                "The D, E, and F sequences apply to the Head of the household"
            ),
            anchors=(("p16_head", ROLE, at("Head")),),
        ),
        unit(
            FLOW, at("Working Now, or Only Temporarily Laid Off"), key="p16_d"
        ),
        unit(C, at("Ask D sequence"), flow="p16_d"),
        unit(
            C,
            block(
                "This includes all persons who have an employer",
                "home on sick leave should also be asked the D sequence.",
            ),
            anchors=(
                ("p16_employer", JOB, at("employer")),
                ("p16_hasjob", JOB, at("a job")),
            ),
            parents=("p16_employer",),
            flow="p16_d",
        ),
        unit(FLOW, at("Looking For Work (Unemployed)"), key="p16_e"),
        unit(C, at("Ask E sequence"), flow="p16_e"),
        unit(
            C,
            block(
                "This should include all persons who are not now working",
                "he should be asked the E sequence",
            ),
            anchors=(
                ("p16_employer2", JOB, at("an employer")),
                ("p16_marketjob", JOB, at("a job")),
            ),
            parents=("p16_employer2",),
            flow="p16_e",
        ),
        unit(
            FLOW,
            at("Retired, Permanently Disabled, Housewife or Student"),
            key="p16_f",
        ),
        unit(C, at("Ask F sequence"), flow="p16_f"),
        unit(
            C,
            block(
                "Section F should be asked of Heads of households who are not in",
                "better to ask the more complete D or E sections.",
            ),
            anchors=(
                ("p16_heads", ROLE, at("Heads of households")),
                ("p16_parttime", JOB, at("part-time jobs")),
            ),
            parents=("p16_parttime",),
            flow="p16_f",
        ),
    ],
    17: [
        unit(
            C,
            block(
                "Again, remember questions in the D-F sequence refer to the",
                "Head of the family.",
            ),
            anchors=(("p17_head", ROLE, at("Head of the family")),),
        ),
        unit(
            C,
            block(
                "Probe for clear, complete answers.",
                "various white-collar occupations.",
            ),
            anchors=(("p17_occs", JOB, at("white-collar occupations")),),
            parents=("p17_occs",),
        ),
        unit(
            C,
            block(
                "The name of the place where the Head works is inadequate",
                "the manager, a teller, or the janitor).",
            ),
            parents=("p17_occs",),
        ),
        unit(
            C,
            block(
                "Avoid vague job titles which may apply to a wide range of",
                "engineer, he may:",
            ),
            anchors=(("p17_titles", JOB, at("job titles")),),
            parents=("p17_titles",),
        ),
        unit(
            C,
            block(
                "The answers to this question are fitted into an industrial",
                "bear the following points in mind:",
            ),
            anchors=(("p17_indocc", JOB, at("particular occupation")),),
            parents=("p17_indocc",),
        ),
    ],
    18: [
        unit(
            C,
            block(
                "The length of time with the present employer, not the time",
                "is what is wanted .",
            ),
            anchors=(("p18_employer", JOB, at("present employer")),),
            parents=("p18_employer",),
        ),
        unit(
            C,
            block(
                "We have mentioned negative alternatives to make it easier for",
                "and don't ask D7, 8 and 9.",
            ),
            anchors=(("p18_firstjob", JOB, at('"First Job"')),),
            parents=("p18_firstjob",),
        ),
        unit(
            REM,
            block(
                "The answers to these questions should tell us if R's present",
                "change was for better or worse.",
            ),
            anchors=(("p18_pjob", JOB, at("job pays better")),),
            parents=("p18_pjob",),
        ),
    ],
    19: [
        unit(FLOW, at("(GO TO Dl4)"), key="p19_d14"),
        unit(FLOW, at("(GO TO Dl6)"), key="p19_d16"),
        unit(FLOW, at("(GO TO D20)"), key="p19_d20"),
        unit(
            C,
            block(
                "Did you miss any work in 1971 because you were unemployed or on strike?",
                "How much \\vork did you mis s?",
            ),
        ),
        unit(
            C,
            line(
                "how many weeks did you actually work on your main job in 1971?"
            ),
            anchors=(("p19_main", JOB, at("main job")),),
            parents=("p19_main",),
        ),
        unit(
            C,
            block(
                "And, on the average,how many hours a week did you work on your main job last",
                "year?",
            ),
            parents=("p19_main",),
        ),
        unit(
            C,
            line("Did you have any overtime"),
            anchors=(("p19_ot", REM, at("overtime")),),
            parents=("p19_main",),
        ),
        unit(
            C,
            line("How many hours did that overtime amount to in 1971?"),
            parents=("p19_main",),
        ),
        unit(
            REM,
            block(
                "If you were to work more hours than usual during some week, would you get paid",
                "for those extra hours of work?",
            ),
            parents=("p19_main",),
        ),
        unit(
            REM,
            at("would b~ your hourly rate"),
            parents=("p19_main",),
            flow="p19_d20",
        ),
        unit(
            REM,
            at("Do you have an hourly wage rate"),
            parents=("p19_main",),
            flow="p19_d20",
        ),
        unit(
            REM,
            line("What is yo ur hourly wage rate for your regular"),
            parents=("p19_main",),
        ),
    ],
    20: [
        unit(
            C,
            block(
                "Questions Dl0-Dl6 should give a complete accounting of the",
                "should add to 52 weeks.",
            ),
            anchors=(
                ("p20_head", ROLE, at("Head's")),
                ("p20_main", JOB, at("main job")),
            ),
            parents=("p20_main",),
        ),
        unit(
            C,
            block(
                "Unemployment means time completely without work--including no",
                "in the margin.",
            ),
            parents=("p20_main",),
        ),
        unit(
            C,
            block(
                "Note that these questions apply to the main job only. Overtime",
                "amount.",
            ),
            anchors=(("p20_ot", REM, at("Overtime")),),
            parents=("p20_main",),
        ),
        unit(
            REM,
            block(
                'The reply to D20 should be "NO," if the Head\'s income is a',
                'as he wishes, then the reply should also be "YES."',
            ),
            anchors=(
                ("p20_head2", ROLE, at("Head's income")),
                (
                    "p20_salary",
                    REM,
                    at("fixed salary plus additional pay for overtime"),
                ),
            ),
            parents=("p20_main",),
        ),
    ],
    21: [
        unit(
            REM,
            block(
                "Hourly rates for overtime work are usually higher (often",
                "difference between the two rates appears to be out of line.",
            ),
            anchors=(
                ("p21_rates", REM, at("Hourly rates for overtime work")),
            ),
        ),
        unit(
            REM,
            block(
                'In general, the reply to this question should be "YES" if the',
                "salary.",
            ),
            anchors=(
                ("p21_head", ROLE, at("Head")),
                ("p21_salary", REM, at("salary.")),
            ),
        ),
    ],
    22: [
        unit(FLOW, at("(GO TO D30)"), key="p22_d30"),
        unit(
            C,
            block(
                "Did you have any extra jobs or other w<1ys of making money",
                "your main job in 19 71?",
            ),
            anchors=(
                ("p22_extra", JOB, at("extra jobs")),
                ("p22_main", JOB, at("main job")),
            ),
            parents=("p22_extra",),
        ),
        unit(C, line("D25."), parents=("p22_extra",)),
        unit(C, line("D26. Anything else?"), parents=("p22_extra",)),
        unit(
            REM,
            line("About how much did you make per hour at this?"),
            parents=("p22_extra",),
        ),
        unit(
            C,
            line(
                "And how many weeks did you work on your extra job(s) in 1971?"
            ),
            parents=("p22_extra",),
        ),
        unit(
            C,
            line(
                "On the average, how many hours a week did you work on your extra job(s)?"
            ),
            parents=("p22_extra",),
        ),
        unit(
            C,
            block(
                "Was there more work available on (your job) (any of your jobs) so that you",
                "could have worked more if you had wanted to?",
            ),
            parents=("p22_main",),
        ),
    ],
    23: [
        unit(
            C,
            block(
                "This question refers to second jobs held simultaneously with",
                "current employment.",
            ),
            anchors=(
                ("p23_second", JOB, at("second jobs")),
                ("p23_main", JOB, at("main job")),
                ("p23_head", ROLE, at("Head's")),
            ),
            parents=("p23_second",),
        ),
        unit(
            REM,
            block(
                "But, if the Head has worked at a number of irregular jobs, there",
                "legging, that is also relevant if he volunteers it.",
            ),
            anchors=(
                ("p23_irregular", JOB, at("irregular jobs")),
                ("p23_extraincome", REM, at("extra income")),
            ),
            parents=("p23_irregular",),
        ),
        unit(
            REM,
            block(
                "If the extra work is such that it is difficult to estimate an",
                "extra job, try to get hourly pay for each job.",
            ),
            anchors=(
                ("p23_extra", JOB, at("extra job")),
                ("p23_hourlypay", REM, at("hourly pay")),
            ),
            parents=("p23_extra",),
        ),
        unit(
            C,
            block(
                "Responses may fit the question framework",
                "an estimate of the hours spent in 1971 on extra jobs.",
            ),
            parents=("p23_extra",),
        ),
        unit(
            C,
            block(
                "D30 is designed to determine whether Head had the choice of",
                "RESTRICTED TO DEFINITE, POSITIVE ANSWERS.",
            ),
            parents=("p23_main",),
        ),
    ],
    26: [
        unit(FLOW, at("(GO TO D52)"), key="p26_d52"),
        unit(
            C,
            block(
                "Have you been thinking about getting a new job, or will you keep the job you",
                "have now?",
            ),
            anchors=(("p26_newjob", JOB, at("a new job")),),
            parents=("p26_newjob",),
        ),
        unit(
            C,
            line("kind of job do you have in mind?"),
            parents=("p26_newjob",),
        ),
        unit(
            REM,
            line("How much might you earn?"),
            parents=("p26_newjob",),
        ),
        unit(
            REM,
            block(
                "Would you be willing to move to another community if you could earn more monev",
                "there?",
            ),
        ),
        unit(
            REM,
            block("How much would a job have to", "move?"),
            anchors=(("p26_movejob", JOB, at("a job have to")),),
            parents=("p26_movejob",),
        ),
    ],
    27: [
        unit(
            C,
            block(
                "A new job can mean with the same employer, a different",
                "employer, or plans for self-employment.",
            ),
            anchors=(
                ("p27_newjob", JOB, at("A new job")),
                ("p27_employer", JOB, at("same employer")),
                ("p27_selfemp", BUS, at("self-employment")),
            ),
            parents=("p27_newjob",),
        ),
        unit(
            C,
            block(
                "These questions will give us some feel for the amount of serious",
                "such forced replies would probably be meaningless.",
            ),
            anchors=(("p27_anotherjob", JOB, at("another job")),),
            parents=("p27_anotherjob",),
        ),
        unit(
            REM,
            block(
                "Be sure to get a time reference",
                "non-money considerations, probe to get a rate of pay.",
            ),
            anchors=(("p27_rate", REM, at("rate of pay")),),
        ),
    ],
    28: [
        unit(
            FLOW,
            at("SECTION E:   IF LOOKING FOR \\YORK, UNEHPLOYED IN Q. Dl"),
            key="p28_e",
        ),
        unit(FLOW, at("(GO TO E6)"), key="p28_e6", flow="p28_e"),
        unit(FLOW, at("(GO TO E9)"), key="p28_e9", flow="p28_e"),
        unit(
            C,
            line("kind of job are you looking for?"),
            anchors=(("p28_lookjob", JOB, at("job are you looking for")),),
            parents=("p28_lookjob",),
            flow="p28_e",
        ),
        unit(
            REM,
            line("Hmv much might you earn?"),
            parents=("p28_lookjob",),
            flow="p28_e",
        ),
        unit(
            C,
            line("What have you been doing to find a job?"),
            parents=("p28_lookjob",),
            flow="p28_e",
        ),
        unit(
            C,
            line(
                "How many places have you been to in the last few 'veeks to find out about a job?"
            ),
            parents=("p28_lookjob",),
            flow="p28_e",
        ),
        unit(
            C,
            line("What sort of work did you do on your last job?"),
            anchors=(("p28_lastjob", JOB, at("last job")),),
            parents=("p28_lastjob",),
            flow="p28_e",
        ),
        unit(
            C,
            line("E6a. What kind of business"),
            parents=("p28_lastjob",),
            flow="p28_e",
        ),
        unit(
            C,
            block(
                "What happened to that job - did the company fold, were you laid-off, or",
                "what?",
            ),
            parents=("p28_lastjob",),
            flow="p28_e",
        ),
        unit(
            C,
            line("How many weeks did you work in 1971?"),
            parents=("p28_lastjob",),
            flow="p28_e",
        ),
        unit(
            C,
            line("About how many hours a week did you"),
            parents=("p28_lastjob",),
            flow="p28_e",
        ),
        unit(
            C,
            line(
                "Then, how many weeks were you unemployed or laid off in 1971?"
            ),
            parents=("p28_lastjob",),
            flow="p28_e",
        ),
    ],
    29: [
        unit(
            C,
            block(
                'An occupation such as "truck driver," "maid," "keypunch',
                "D2-D3; they apply here.",
            ),
            anchors=(("p29_occ", JOB, at("An occupation")),),
            parents=("p29_occ",),
        ),
        unit(
            REM,
            block(
                "Be sure to record the pay period, e.g., $3 per hour,",
                "$500 per month, etc .",
            ),
            anchors=(("p29_payperiod", REM, at("pay period")),),
        ),
        unit(
            C,
            block(
                '"Places" may be public or private employment agencies,',
                "unions, prospective employers themselves, etc.",
            ),
            anchors=(("p29_employers", JOB, at("prospective employers")),),
            parents=("p29_employers",),
        ),
        unit(
            C,
            line(
                "Enter here the total number of weeks actually worked in 1971."
            ),
            parents=("p29_occ",),
        ),
        unit(
            C,
            block(
                "If the Head's work schedule was irregular, be sure the total",
                "responses to E7 and E8.",
            ),
            anchors=(("p29_head", ROLE, at("Head's")),),
            parents=("p29_occ",),
        ),
    ],
    32: [
        unit(FLOW, at("(GO TO E26)"), key="p32_e26"),
        unit(
            C,
            line(
                "Are there jobs available around here that just aren't worth taking?"
            ),
            anchors=(("p32_avail", JOB, at("jobs available")),),
            parents=("p32_avail",),
        ),
        unit(
            REM,
            line("How much do they pay?"),
            parents=("p32_avail",),
        ),
        unit(
            REM,
            block("How much would a job have", "ing to move?"),
            anchors=(("p32_movejob", JOB, at("a job have")),),
            parents=("p32_movejob",),
        ),
    ],
    33: [
        unit(
            REM,
            block(
                "We want to know what level of pay the respondent considers to",
                "which case, E25 need not be asked.",
            ),
            anchors=(
                ("p33_pay", REM, at("level of pay")),
                ("p33_jobs", JOB, at("jobs in the area")),
            ),
            parents=("p33_jobs",),
        ),
        unit(
            REM,
            block(
                "Be sure to get a time reference",
                "monetary considerations, probe to get a rate of pay.",
            ),
            anchors=(("p33_rate", REM, at("rate of pay")),),
        ),
    ],
    34: [
        unit(
            FLOW,
            at(
                "SECTION F:    RETIRED, HOUSEIHFE, STUDENT, PERMANENTLY DISABLED"
            ),
            key="p34_f",
        ),
        unit(FLOW, at("(GO TO F7)", 0), key="p34_f2yes", flow="p34_f"),
        unit(FLOW, at("(GO TO F7)", 1), key="p34_f6yes", flow="p34_f"),
        unit(
            FLOW,
            at("(IF YES TO F2 OR TO F6)"),
            key="p34_f7",
            flow=("p34_f2yes", "p34_f6yes"),
        ),
        unit(FLOW, at("(GO TO Fl2)"), key="p34_f12", flow="p34_f"),
        unit(
            REM,
            line(
                "During the last year (1971) , did you (HEAD) do any work for money?"
            ),
            anchors=(
                ("p34_head", ROLE, at("HEAD")),
                ("p34_workformoney", JOB, at("work for money")),
            ),
            parents=("p34_workformoney",),
            flow="p34_f",
        ),
        unit(
            C,
            line("Are you thinking about going to work?"),
            flow="p34_f",
        ),
        unit(
            C,
            line("What kind of work did you do when you worked?"),
            anchors=(("p34_occ", JOB, at("occupation")),),
            parents=("p34_occ",),
            flow="p34_f",
        ),
        unit(
            C,
            line("F3a . What kind of business is that in?"),
            parents=("p34_occ",),
            flow="p34_f",
        ),
        unit(
            C,
            line("How many weeks did you work last year?"),
            parents=("p34_occ",),
            flow="p34_f",
        ),
        unit(
            C,
            line(
                "About how many hours a week did you work (when you worked)?"
            ),
            parents=("p34_occ",),
            flow="p34_f",
        ),
        unit(
            C,
            line(
                "Are you thinking of getting a ne'\" job in the next year or so?"
            ),
            anchors=(("p34_newjob", JOB, at("job in the next year")),),
            parents=("p34_newjob",),
            flow="p34_f",
        ),
        unit(
            C,
            line("kind of job do you have in mind?"),
            parents=("p34_newjob",),
            flow="p34_f7",
        ),
        unit(
            REM,
            line("How much might you earn?"),
            parents=("p34_newjob",),
            flow="p34_f7",
        ),
        unit(
            C,
            line(
                "How many places have you been to in the last few weeks to find out about"
            ),
            parents=("p34_newjob",),
            flow="p34_f7",
        ),
        unit(
            C,
            line("Are there jobs around here that just aren't worth taking?"),
            anchors=(("p34_avail", JOB, at("jobs around here")),),
            parents=("p34_avail",),
            flow="p34_f",
        ),
        unit(
            REM,
            line("How much do they pay?"),
            parents=("p34_avail",),
            flow="p34_f",
        ),
    ],
    35: [
        unit(
            REM,
            block(
                "For such Heads, work may have been irregular part-time work or",
                "We are interested in any tnoney earning activity during 1971.",
            ),
            anchors=(
                ("p35_heads", ROLE, at("Heads")),
                ("p35_fulltime", JOB, at("full-time job prior to retirement")),
                ("p35_moneyearn", REM, at("tnoney earning activity")),
            ),
            parents=("p35_fulltime",),
        ),
        unit(
            C,
            block(
                '"Going to work" can mean in the immediate or distant future,',
                "on a regular or irregular basis, or full or part-time.",
            ),
        ),
        unit(
            C,
            block(
                "We want to be able to calculate the total hours of work in 1971.",
                "52 weeks in terms of work, vacation, sickness, etc.",
            ),
            parents=("p35_fulltime",),
        ),
        unit(
            C,
            block(
                '"New job" can mean a different position with the same employer,',
                "ferent job and different employer.",
            ),
            anchors=(
                ("p35_newjob", JOB, at('"New job"')),
                ("p35_employer", JOB, at("same employer")),
            ),
            parents=("p35_newjob",),
        ),
        unit(
            C,
            block(
                "Be specific and avoid vague titles (see D2-3). We want to",
                "in mind.",
            ),
            parents=("p35_newjob",),
        ),
        unit(
            REM,
            line(
                "Be sure to state pay period--$3 per hour, $500 per month, etc."
            ),
            anchors=(("p35_payperiod", REM, at("pay period")),),
            parents=("p35_newjob",),
        ),
    ],
    36: [
        unit(
            C,
            block(
                '"Places" may be public or private employment agencies,',
                "unions, prospective employers themselves, etc.",
            ),
            anchors=(("p36_employers", JOB, at("prospective employers")),),
            parents=("p36_employers",),
        ),
        unit(
            REM,
            block(
                "We want to know what level of pay the R considers to be",
                "asked.",
            ),
            anchors=(
                ("p36_pay", REM, at("level of pay")),
                ("p36_jobs", JOB, at("jobs around here")),
            ),
            parents=("p36_jobs",),
        ),
    ],
    37: [
        unit(
            FLOW, at("(Q's G2-G9 REFER TO WIFE's OCCUPATION)"), key="p37_wife"
        ),
        unit(FLOW, at("(GO TO GlO, PAGE 17)"), key="p37_g10", flow="p37_wife"),
        unit(FLOW, at("(GO TO G8)"), key="p37_g8", flow="p37_wife"),
        unit(
            REM,
            line("Did your wife do any work for money in 1971?"),
            anchors=(
                ("p37_wiferole", ROLE, at("wife")),
                ("p37_wifejob", JOB, at("work for money")),
            ),
            parents=("p37_wifejob",),
            flow="p37_wife",
        ),
        unit(
            C,
            line("What kind of work did she do?"),
            parents=("p37_wifejob",),
            flow="p37_wife",
        ),
        unit(
            C,
            line("G3a.       What kind of business is that in?"),
            parents=("p37_wifejob",),
            flow="p37_wife",
        ),
        unit(
            C,
            line("About how many weeks did she work last year?"),
            parents=("p37_wifejob",),
            flow="p37_wife",
        ),
        unit(
            C,
            line("And about how many hours a week did she work?"),
            parents=("p37_wifejob",),
            flow="p37_wife",
        ),
        unit(
            C,
            block(
                "Was there more work available so that your ~vife could have worked more",
                "in 1971 if she had wanted to?",
            ),
            parents=("p37_wifejob",),
            flow="p37_wife",
        ),
    ],
    38: [
        unit(
            C,
            block(
                "Since many of the questions in this section apply to things that",
                "questions in this section .",
            ),
            anchors=(("p38_wife", ROLE, at("wife")),),
        ),
        unit(C, line("See Section D, Questions D2-3, 3a for objectives.")),
        unit(
            C,
            block(
                "See the objectives for E7, 8; they are the same for these two",
                "to get an estimate of the total number of hours worked in 1971.",
            ),
            anchors=(("p38_wife2", ROLE, at("wife")),),
        ),
        unit(C, line("See Section D, Questions D30-31 for objectives.")),
    ],
    39: [
        unit(FLOW, at("(GO '1.'0 GlS)"), key="p39_g15"),
        unit(
            C,
            at("HIFE UNDER 65 1:U'm DID NOT HORK IN 19 71"),
            anchors=(("p39_wife", ROLE, at("HIFE")),),
        ),
        unit(
            C,
            line(
                "If your wife wanted to work, would she be able to find a job easily?"
            ),
            anchors=(("p39_wifejob", JOB, at("a job easily")),),
            parents=("p39_wifejob",),
        ),
        unit(
            C,
            block(
                "Hhat about the next few years?",
                "in the near future?",
            ),
            parents=("p39_wifejob",),
        ),
    ],
    40: [
        unit(
            C,
            block(
                "The following questions, Gll-14 , are to be asked only of",
                "under 65.",
            ),
            anchors=(("p40_wife", ROLE, at("wife")),),
        ),
        unit(
            C,
            block(
                "If the wife wasn ' t working in 1971 but has gotten a job since",
                "ing this question .",
            ),
            anchors=(("p40_wifejob", JOB, at("a job since")),),
            parents=("p40_wifejob",),
        ),
        unit(
            REM,
            block(
                "We are interested in knowing if children and family obligations,",
                "considerations which might prompt her to go to work.",
            ),
            anchors=(("p40_financial", REM, at("financial")),),
        ),
    ],
    48: [
        unit(FLOW, at("SECTION H:   Il'\\COHE"), key="p48_h"),
        unit(FLOW, at("(GO TO HS)", 1), key="p48_h8", flow="p48_h"),
        unit(
            C,
            block(
                "To get an accurate financial picture of people all over the country, we need to",
                "know the income of all the families that we interview.",
            ),
            flow="p48_h",
        ),
        unit(
            FLOW,
            at("FARl'fER, OR RANCl-lER"),
            key="p48_farmbranch",
            flow="p48_h",
        ),
        unit(
            C,
            line("FARl'fER, OR RANCl-lER"),
            anchors=(("p48_farmer", FARM, at("FARl'fER, OR RANCl-lER")),),
            flow="p48_h",
        ),
        unit(
            REM,
            block(
                "Hhat were your total receipts from farming in 1971, including",
                "soil bank payments and commodity credit loans?",
            ),
            anchors=(("p48_farming", FARM, at("farming")),),
            parents=("p48_farmer",),
            flow="p48_farmbranch",
        ),
        unit(
            REM,
            block(
                "Hhat were your total operating expenses, not counting living",
                "expenses?",
            ),
            parents=("p48_farmer",),
            flow="p48_farmbranch",
        ),
        unit(
            REM,
            line("That left you a net income from farming of?"),
            anchors=(("p48_netfarm", FARM, at("net income from farming")),),
            parents=("p48_farmer",),
            flow="p48_farmbranch",
        ),
        unit(
            C,
            block(
                "Did you (R AND FA}1ILY) own a business at any time in 1971, or have a financial",
                "interest in any business enterprise?",
            ),
            anchors=(("p48_business", BUS, at("a business")),),
            flow="p48_h",
        ),
        unit(
            C,
            block(
                "Is it a corporation or an unincorporated business,",
                "interest in both kinds?",
            ),
            anchors=(("p48_unincorp", BUS, at("unincorporated business,")),),
            parents=("p48_business",),
            flow="p48_h",
        ),
        unit(
            REM,
            block(
                "How much was your (FANILY's) share of the total income from the business",
                "in 1971- that is, the amount you took out plus any profit left in?",
            ),
            parents=("p48_business",),
            flow="p48_h",
        ),
        unit(
            TOT,
            block(
                "How much did you (HEAD) receive from wages and salaries in 1971, that is, before",
                "anything was deducted for taxes or other things?",
            ),
            anchors=(
                ("p48_head", ROLE, at("HEAD")),
                ("p48_wages", REM, at("wages and salaries")),
            ),
            flow="p48_h",
        ),
    ],
    49: [
        unit(
            C,
            block(
                "Family income is, of course, this study's single most important",
                "get complete and accurate responses.",
            ),
        ),
        unit(
            C,
            block(
                "Below are some guides to follow when asking income questions where",
                "the family composition changed between 1971 and 1972",
            ),
        ),
        unit(
            REPEAT,
            block(
                "1. If last year's Head married in 1971 or 1972, consider the",
                "until June, 1971 .",
            ),
            repeat={"relation": "explicit_repeat_instruction"},
        ),
    ],
    50: [
        unit(
            C,
            block(
                "A farmer for our purposes is anyone whose",
                'We consider "rancher" and "farmer" synonymous',
            ),
            anchors=(("p50_farmer", FARM, at("A farmer")),),
        ),
        unit(
            REPEAT,
            line("Farm income for nonfarmers should be picked up in Hllb."),
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            REM,
            block(
                "The following are included here as receipts from nortnal",
                "receive a set price for his crop.",
            ),
            parents=("p50_farmer",),
        ),
        unit(
            REM,
            block(
                "Farm operating expenses may include:",
                "7) property taxes (but not Federal Income Taxes)",
            ),
            anchors=(("p50_wages", REM, at("wages for employees")),),
            parents=("p50_farmer",),
        ),
        unit(
            REM,
            block(
                "Farm income equals total receipts less operating expenses.",
                "discover omissions and correct errors.",
            ),
            anchors=(("p50_farmincome", FARM, at("Farm income")),),
            parents=("p50_farmer",),
        ),
        unit(
            C,
            block(
                "The respondent need not be a businessman for this question to",
                "in the enterprise.",
            ),
            anchors=(("p50_business", BUS, at("The business")),),
        ),
    ],
    51: [
        unit(
            C,
            block(
                "If the respondent does not seem to understand the quest :lon,",
                "persons.",
            ),
            anchors=(("p51_corp", BUS, at('"corporation"')),),
        ),
        unit(
            REM,
            block(
                "The figure should include the total profits from the business",
                "that should also be labeled and included here.",
            ),
            anchors=(
                ("p51_business", BUS, at("the business")),
                ("p51_profit", REM, at("profit from the business")),
                ("p51_salary", REM, at("Head's salary")),
                ("p51_wife", ROLE, at("wife")),
            ),
            parents=("p51_business",),
        ),
        unit(
            TOT,
            block(
                "This question applies only to the 1972 Head of the FU. For",
                "It should include income from a second job if the Head had one.",
            ),
            anchors=(
                ("p51_head2", ROLE, at("Head of the FU")),
                ("p51_secondjob", JOB, at("second job")),
            ),
        ),
        unit(
            REM,
            block(
                "1) Fixed salary rates: If the Head now makes $7,000",
                "1971 income--not the current salary rate.",
            ),
            anchors=(("p51_fixedsalary", REM, at("Fixed salary rates")),),
        ),
        unit(
            C,
            block(
                "2) Complicated work history: If the Head had several",
                "you may have to help him reconstruct his income.",
            ),
            anchors=(("p51_jobs", JOB, at("jobs and was unemployed")),),
            parents=("p51_jobs",),
        ),
        unit(
            REM,
            block(
                "3) Businessmen: The wages and salaries that unincorpo-",
                "here.",
                last_occurrence=1,
            ),
            anchors=(
                (
                    "p51_unincorp",
                    BUS,
                    spanned("unincorpo-", "rated businessmen"),
                ),
                ("p51_otherjob", JOB, at("some other job")),
            ),
            parents=("p51_otherjob",),
        ),
        unit(
            REPEAT,
            block(
                "Make sure if an amount is given for both H7 and H8",
                "Probe to find out in these cases.",
            ),
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    52: [
        unit(FLOW, at("(GO TO Hll)"), key="p52_h11"),
        unit(FLOW, at('(IF "YES" TO ANY'), key="p52_yes"),
        unit(
            REM,
            block(
                "In addition to thisi did you have any income from bonuses, overtime, or",
                "commissions?",
            ),
            anchors=(("p52_bonus", REM, at("bonuses, overtime, or")),),
        ),
        unit(REM, line("How much was that?")),
        unit(
            C,
            line("Did you (HEAD) receive any other income in 1971 from:"),
            anchors=(("p52_head", ROLE, at("HEAD")),),
        ),
        unit(REM, at("a) professional practice or trade?"), flow="p52_yes"),
        unit(
            REM,
            at("b) farming or market gardening,"),
            anchors=(
                ("p52_farming", FARM, at("farming or market gardening")),
            ),
            flow="p52_yes",
        ),
        unit(REM, at("roomers or boarders?"), flow="p52_yes"),
        unit(
            REM,
            spanned(
                "c) dividends, interest, rent,", "trust funds, or royalties?"
            ),
            flow="p52_yes",
        ),
        unit(REM, at("d) ADC, AFDC?"), flow="p52_yes"),
        unit(REM, at("e) other welfare?"), flow="p52_yes"),
        unit(REM, at("f) Social Security?"), flow="p52_yes"),
        unit(
            REM,
            spanned("g) other retirement pay, pensions,", "or annuities?"),
            flow="p52_yes",
        ),
        unit(
            REM,
            spanned("h) unemployment, or workmen's", "compensation?"),
            flow="p52_yes",
        ),
        unit(REM, at("i) alimony?     Child support?"), flow="p52_yes"),
        unit(REM, at("j) help from relatives?"), flow="p52_yes"),
        unit(REM, at("k) anything else?"), flow="p52_yes"),
    ],
    53: [
        unit(
            REPEAT,
            block(
                'Note the phrase "In addition to this." If Head has already',
                "just note that; there is no need to separate it.",
            ),
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            REM,
            block(
                "In answering Questions Hlla-llk it is very important to state",
                "want.",
            ),
        ),
        unit(
            REM,
            block(
                "1) Income BEFORE TAXES but AFTER EXPENSES is what is wanted",
                "and the latter is included here.",
            ),
            anchors=(
                ("p53_practice", REM, at("PROFESSIONAL PRACTICE")),
                ("p53_selfemp", BUS, at("Self-employed doctors")),
            ),
        ),
        unit(
            REM,
            block(
                "1. FARMING OR MARKET GARDENING: If farming is R's primary",
                "income, however.",
            ),
            anchors=(
                ("p53_farming", FARM, at("FARMING OR MARKET GARDENING")),
            ),
        ),
        unit(
            REM,
            block(
                "2. ROOMERS OR BOARDERS: We want net income here",
                "included as income here .",
            ),
        ),
    ],
    54: [
        unit(
            REM,
            block(
                "1. DIVIDENDS: Dividends are the amounts paid to owners of",
                "included.",
            ),
            anchors=(
                ("p54_business", BUS, at("incorporated business")),
                ("p54_salary", REM, at("the salary he paid himself")),
            ),
            parents=("p54_business",),
        ),
        unit(
            REM,
            block(
                "2. INTEREST: Receipts here include primarily income from",
                "on personal loans made.",
            ),
        ),
        unit(
            REM,
            block(
                "3. RENT: In addition to his own home R may own other real",
                "additions) .",
            ),
        ),
        unit(
            REM,
            block(
                "4. TRUST FUNDS:   A trust fund is money invested by a person",
                "belong here.",
                last_occurrence=1,
            ),
        ),
        unit(
            REM,
            block(
                "5. ROYALTIES: These include such things as payments for",
                "when copies of their books are sold.",
            ),
        ),
        unit(
            REM,
            block(
                "ADC is Aid to Dependent Children, while AFDC is Aid to Families of",
                "by those covered under this program.",
            ),
        ),
    ],
    55: [
        unit(
            REM,
            block(
                "Other welfare includes all other public programs contingent",
                "participation.",
            ),
        ),
        unit(
            REM,
            block(
                "Unlike public welfare, benefits received under Social Security",
                "18 are also paid a certain allowance.",
            ),
            anchors=(("p55_wages", REM, at("wages and salaries")),),
        ),
    ],
    56: [
        unit(
            REM,
            block(
                "OTHER RETIRE}ffiNT PAY: Some retired people will be receiving",
                "their employees.",
            ),
            anchors=(("p56_deferred", REM, at("deferred compensation")),),
        ),
        unit(
            REM,
            block(
                "PENSIONS: Private pensions from previous employers will be",
                "personally.",
            ),
            anchors=(("p56_employers", JOB, at("previous employers")),),
            parents=("p56_employers",),
        ),
        unit(
            REM,
            block(
                "1. UNEMPLOYMENT COMPENSATION: All 50 states participate in",
                "ineligible for these benefits.",
            ),
            anchors=(("p56_selfemp", BUS, at("self-employed")),),
        ),
        unit(
            REM,
            block(
                "2. WORKMEN'S COMPENSATION: This is entirely state administered",
                "exclude government employees.",
            ),
            anchors=(("p56_occ", JOB, at("hazardous occupations")),),
            parents=("p56_occ",),
        ),
        unit(
            REM,
            block(
                "ALIMONY: Income to a divorced or separated woman should be in-",
                "with AFDC payments which should be recorded in Hlld.",
            ),
        ),
    ],
    57: [
        unit(
            REM,
            block(
                "Relatives include related family members who live outside",
                "employment of a family member should be included here.",
            ),
        ),
        unit(
            REM,
            block(
                "1. TRAINING PROGRAM ALLOWANCES: Various Manpower Develop-",
                "of income, which should be included.",
            ),
        ),
        unit(
            REM,
            block(
                "2. ILLEGAL SOURCES OF INCOME: This is indeed income and",
                "we would be happy to have it if R mentions it.",
            ),
        ),
        unit(
            REPEAT,
            line("3. Be sure there is no double-counting here."),
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    58: [
        unit(FLOW, at("YES, WIFE IN FU"), key="p58_wifefu"),
        unit(
            REM,
            block(
                "How much money can a person earn before they start to cut his welfare?",
                "(WEEK,MONTH)",
            ),
        ),
        unit(
            C,
            line("DOES HEAD HAVE WIFE IN FU?"),
            anchors=(
                ("p58_head", ROLE, at("HEAD")),
                ("p58_wife", ROLE, at("WIFE")),
            ),
        ),
        unit(
            C,
            line("Did your wife have any income during 1971?"),
            anchors=(("p58_wife2", ROLE, at("wife")),),
            flow="p58_wifefu",
        ),
        unit(
            C,
            line("Was it income from wages, salary, a business, or what?"),
            anchors=(
                ("p58_business", BUS, at("a business")),
                ("p58_wagesalary", REM, at("wages, salary")),
            ),
            parents=("p58_business",),
            flow="p58_wifefu",
        ),
        unit(
            TOT,
            line("How much was it before deductions?"),
            flow="p58_wifefu",
        ),
    ],
    59: [
        unit(
            REPEAT,
            block(
                "1 . Make sure the wife ' s income from all sources is recorded .",
                "wife's name.",
            ),
            anchors=(("p59_wife", ROLE, at("wife ' s income")),),
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            REPEAT,
            block(
                "3. If some or all of the wife's income is from work in the",
                "margin.",
            ),
            anchors=(("p59_business", BUS, at("family business")),),
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    60: [
        unit(FLOW, at("IF WAGES OR BUSINESS"), key="p60_wb"),
        unit(FLOW, at("(GO TO H37)"), key="p60_h37"),
        unit(C, line("PEOPLE J.!1 AND OLDER")),
        unit(REM, line("much did that a E'Ount to in 1971?")),
        unit(
            C,
            block(
                "Was tha t from wages, a pension, a busine s s", "or v1hat '?"
            ),
            anchors=(
                ("p60_business", BUS, at("busine s s")),
                ("p60_wages", REM, at("wages, a pension")),
            ),
            parents=("p60_business",),
        ),
        unit(
            C,
            line("kind of work did (he/she) do?"),
            anchors=(("p60_occ", JOB, at("(OCCUPATION)")),),
            parents=("p60_occ",),
            flow="p60_wb",
        ),
        unit(
            C,
            block("Can you tell me about how many weeks", "(he/she) Harked?"),
            parents=("p60_occ",),
            flow="p60_wb",
        ),
        unit(
            C,
            line("About hm.;r many hours a week was that?"),
            parents=("p60_occ",),
            flow="p60_wb",
        ),
        unit(C, line("Did (he/she) have any other income?")),
        unit(C, line("What ~vas that from?")),
        unit(REM, line("How much Has that last year?")),
        unit(
            REPEAT,
            line("BACK TO H27 FOR 2nd, etc. ADDITIONAL HE~lliERS LISTED"),
            repeat={"relation": "explicit_repeat_instruction"},
        ),
    ],
    61: [
        unit(
            REPEAT,
            block(
                "Refer to page 2 of the cover sheet . Except for current Head",
                "between the 1971 and 1972 interview.",
            ),
            anchors=(
                ("p61_head", ROLE, at("current Head")),
                ("p61_wife", ROLE, at("wife")),
            ),
            repeat={"relation": "explicit_repeat_instruction"},
        ),
        unit(
            REM,
            block(
                "The most common source here will be wages, whether from regular",
                "funds should also be included.",
            ),
            anchors=(
                ("p61_wages", REM, at("wages, whether from regular")),
                ("p61_oddjobs", JOB, at("odd jobs")),
            ),
            parents=("p61_oddjobs",),
        ),
        unit(
            C,
            block(
                "The occupation for these individuals need not be so specific as",
                "that for Heads and wives.",
            ),
            anchors=(
                ("p61_occ", JOB, at("The occupation")),
                ("p61_heads", ROLE, at("Heads and wives")),
            ),
            parents=("p61_occ",),
        ),
        unit(
            C,
            block(
                "If the employment of this individual was irregular, try to get",
                '"More than half time" here refers to the average over the year.',
            ),
            parents=("p61_occ",),
        ),
        unit(
            REPEAT,
            block(
                "Income here refers to amounts in addition to that recorded in",
                "for all family members.",
            ),
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    63: [
        unit(
            C,
            line("RELATION TO HEAD"),
            anchors=(("p63_head", ROLE, at("RELATION TO HEAD")),),
        ),
        unit(
            C,
            line("(OCCUPATION)"),
            anchors=(("p63_occ", JOB, at("(OCCUPATION)")),),
            parents=("p63_occ",),
        ),
    ],
    64: [
        unit(
            REPEAT,
            block(
                "This page is a repetition of the previous one, in case more",
                "interview if 5 or more others need to be listed .",
            ),
            repeat={
                "relation": "explicit_repeat_instruction",
                "alias": ("p63_occ",),
                "canonical": ("p60_occ",),
                "evidence": ("p60_occ", "p63_occ"),
                "resolution": "document_local_source_evidence_complete",
            },
        ),
    ],
    65: [
        unit(FLOW, at("(CO TO 1141)"), key="p65_h41"),
        unit(C, line("else living here in 1971")),
        unit(
            REPEAT,
            line("(TURN BACK AND ASK H27-H38 FOR THESE ADDITIONAL MEHl\\ERS)"),
            repeat={
                "relation": "explicit_cross_reference",
                "evidence": ("p60_occ",),
            },
        ),
        unit(
            REM,
            block(
                "Did you get any other money in 1971 - like a big settlement from an insurance",
                "company, or an inheritance?",
            ),
        ),
        unit(
            REM,
            block(
                "Now thinking of your (FAMILY's) tot;:~l income - including everything -was it",
                "higher in 1971, or higher the year before, in 1970?",
            ),
        ),
    ],
    89: [
        unit(FLOW, at("(GO TO M6)"), key="p89_m6"),
        unit(
            C,
            line("was your father's usual occupation when you"),
            anchors=(("p89_focc", JOB, at("usual occupation")),),
            parents=("p89_focc",),
        ),
        unit(
            C,
            line("first full time regular job"),
            anchors=(
                ("p89_head", ROLE, at("HEAD's")),
                ("p89_firstjob", JOB, at("first full time regular job")),
            ),
            parents=("p89_firstjob",),
        ),
        unit(
            C,
            block(
                "Have you had a number of different kinds of jobs, or have you mostly worked",
                "in the same occupation you started in, or what?",
            ),
            anchors=(
                ("p89_jobs", JOB, at("different kinds of jobs")),
                ("p89_sameocc", JOB, at("same occupation you started in")),
            ),
            parents=("p89_jobs",),
        ),
    ],
    90: [
        unit(
            C,
            line("See D2-3; the same instructions apply."),
            parents=(),
        ),
        unit(
            C,
            block(
                "We are only interested in the number of occupations the Head",
                "the labor force currently.",
            ),
            anchors=(
                ("p90_occs", JOB, at("occupations the Head")),
                ("p90_head", ROLE, at("Head")),
                ("p90_parttime", JOB, at("part-time jobs")),
            ),
            parents=("p90_occs",),
        ),
    ],
}


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
    repeat_units: dict[tuple[int, int, int], dict[str, Any]] = {}

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
            if kind in {C, REM, TOT}:
                add(page_number, start, end, PURPOSE, item["flow"])
            if kind in COMPONENT_KINDS:
                component_parents[(page_number, start, end, kind)] = item[
                    "parents"
                ]
            if kind == REPEAT:
                repeat_units[(page_number, start, end)] = item["repeat"] or {
                    "relation": "explicit_repeat_instruction"
                }
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
        else:
            paths = branch_paths(flow_key)
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

    repeat_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        if spec["occurrence_kind"] != REPEAT:
            continue
        coordinate = (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        declared = repeat_units[coordinate]
        alias = [anchor_review_id[key] for key in declared.get("alias", ())]
        canonical = [
            anchor_review_id[key] for key in declared.get("canonical", ())
        ]
        evidence = [
            anchor_review_id[key] for key in declared.get("evidence", ())
        ]
        evidence = sorted(
            {*evidence, *alias, *canonical, spec["review_occurrence_id"]},
            key=lambda item: order_index[item],
        )
        resolution = declared.get(
            "resolution", "preserved_for_global_resolution"
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
                "all_103_pages_including_empty_occurrence_pages"
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
    for row in stage1_candidates._physical_lines(page_text):
        line_start = len(page_text[: row["start"]].encode("utf-8"))
        line_end = len(page_text[: row["end"]].encode("utf-8"))
        if line_start <= byte_start < line_end:
            return stage1_candidates._printed_identifier(row["text"])
    raise ValueError("source review occurrence does not resolve to a line")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    review = build_review(page_texts())
    raw = source_tools.canonical_json_bytes(review)
    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_bytes() != raw:
            raise SystemExit("document 9 source review drift")
        print(f"document 9 source review reproduces: {OUTPUT_PATH}")
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
