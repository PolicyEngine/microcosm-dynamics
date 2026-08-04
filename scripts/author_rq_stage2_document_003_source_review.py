#!/usr/bin/env python3
"""Author the reviewer's candidate-free source review for document 3.

The reviewer read every one of the 47 exact ``fam1969_QxQs.pdf`` page texts
before this table was written.  Every span below is resolved against the exact
UTF-8 page bytes produced by the pinned Poppler derivation, never against a
stage-1 candidate row.  The retained domain is the printed covered-earnings
hierarchy of the 1969 instrument and its question-by-question objectives.

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
* reject prospective job search, labor-supply preferences, commuting, health,
  transfers, pensions, property income, other-member grids, general family
  finances, and nonemployment household prose because they establish no
  realized two-role covered-earnings node;
* retain the page-6 work-for-housing sequence as the source-proved in-kind-pay
  exception, and retain the page-45 proxy-respondent text only for role
  attachment.
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

DOCUMENT_SOURCE_POSITION = 3
SCHEMA_VERSION = "rq_stage2_document_source_review.v1"
AUTHORITY_KIND = "reviewer_authored_source_bytes_only_nonauthority"
PAGE_COUNT = 47
PDF_FILENAME = "fam1969_QxQs.pdf"
PDF_SIZE = 19_003_206
PDF_SHA256 = "54106e94319c099e7a7272622965b345eae74b3001035c295500ea1db33f8138"
DOCUMENT_ID = (
    "psid-source-document:"
    "ef8dfca68fb7c22a80b83c1fe09b7f28431be4e22ade7d6e5acc21b660f546d9"
)
OUTPUT_PATH = (
    ROOT
    / "docs"
    / "analysis"
    / "rq_stage2_annotations"
    / "document_003_fam1969_QxQs_source_review_v1.json"
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
INCOME_PATHS = ("p24_farmer", "p24_not_farmer")
SAME_IDENTIFIER_ALIASES = (
    {"alias": "p45_proxy_head", "canonical": "p45_head"},
)
PRINTED_IDENTIFIER_CODE = (
    r"(?:[A-M][A-Za-z0-9]*[0-9][A-Za-z0-9]*|"
    r"ClO|Dl|DS|DlO|Dll|El|ElO|Fl|Gl|HZ|HS|Hlla|Hllb)"
)
PRINTED_IDENTIFIER_TAIL = rf"(?:{PRINTED_IDENTIFIER_CODE}|[0-9]+[A-Za-z]*)"
PRINTED_IDENTIFIER_PREFIX_RE = re.compile(
    rf"^(?P<identifier>{PRINTED_IDENTIFIER_CODE}"
    rf"(?:(?:\s*,\s*|-){PRINTED_IDENTIFIER_TAIL})*[,.]?)(?=\s+)",
    re.ASCII,
)

PAGE_NOTES = {
    1: "Reviewed children and education material; no covered-earnings evidence retained.",
    2: "Reviewed siblings and transportation material; get-to-work prose is not job-node evidence.",
    3: "Reviewed car ownership and repair material; do-it-yourself work prose is outside scope.",
    4: "Reviewed car repair and housing introduction; living-quarters examples are contextual only.",
    5: "Reviewed utilities and property-debt material; no covered-earnings evidence retained.",
    6: "Retained the exact work-for-housing compensation and rent sequence; repair prose is outside scope.",
    7: "Reviewed do-it-yourself housing and local-ties material; no covered-earnings evidence retained.",
    8: "Retained Head work-status routing, occupation context, and purpose text; movement prose is outside scope.",
    9: "Retained current-job and prior-job context plus explicit first-job and omission routes.",
    10: "Retained vacation, sickness, unemployment, and main-job time context and purpose text.",
    11: "Retained main-job hours, extra-job context, hourly pay, and the D2 coding cross-reference.",
    12: "Retained actual extra-job weeks and hours; counterfactual rates and labor-supply preferences are outside scope.",
    13: "Reviewed commute time and cost material; no covered-earnings evidence retained.",
    14: "Reviewed attendance and new-job planning material; prospective work is outside scope.",
    15: "Reviewed moving, reservation-pay, and job-satisfaction material; no realized earnings node is established.",
    16: "Retained only the exact E6-to-D6 cross-reference; prospective job-search prose is outside scope.",
    17: "Retained actual prior-year work, sickness, unemployment context, and the D10-17 cross-reference.",
    18: "Retained actual work-for-money, occupation, hours, and weeks evidence; future work plans are outside scope.",
    19: "Retained Wife work-for-money, occupation, weeks, and hours evidence plus exact objective cross-references.",
    20: "Reviewed housework and childcare material; household work is outside covered earnings.",
    21: "Reviewed food-spending material; no covered-earnings evidence retained.",
    22: "Reviewed meals, food stamps, and free-food material; no covered-earnings evidence retained.",
    23: "Reviewed family-meals material; no covered-earnings evidence retained.",
    24: "Retained income-scope purpose, farmer routing, farm receipts, and the H11b cross-reference.",
    25: "Retained farm/business aggregates, incorporation context, the H7 route, and add-in guidance.",
    26: "Retained Head wage total, bonuses, professional/trade income, amount periods, and H8 cross-references.",
    27: "Retained nonfarmer farm income and the incorporated-owner H8 cross-reference; property income is outside scope.",
    28: "Reviewed welfare material; transfer income is outside the covered-earnings hierarchy.",
    29: "Reviewed Social Security and pension material; transfers and pensions are outside scope.",
    30: "Reviewed compensation, alimony, and support material; nonemployment receipts are outside scope.",
    31: "Retained Wife total earnings and its H7 relation; transfer-income prose is outside scope.",
    32: "Reviewed the other-family-member income grid; it is outside the fixed Head/Wife role domain.",
    33: "Reviewed nonrecurring money and overall-finance material; no covered-earnings evidence retained.",
    34: "Reviewed support and expectations material; no covered-earnings evidence retained.",
    35: "Reviewed savings and medical-insurance material; no covered-earnings evidence retained.",
    36: "Reviewed disability and health material; worklike prose does not establish an earnings node.",
    37: "Reviewed leisure and training material; no realized covered-earnings evidence retained.",
    38: "Reviewed union and future-plans material; no covered-earnings evidence retained.",
    39: "Reviewed attitude items; job and work examples do not establish source earnings nodes.",
    40: "Reviewed hypothetical job preferences and attitudes; no realized earnings evidence retained.",
    41: "Reviewed attitudes containing job examples; no covered-earnings evidence retained.",
    42: "Reviewed background and demographic material; no covered-earnings evidence retained.",
    43: "Reviewed education, training, and job-application prose; no realized earnings node is established.",
    44: "Reviewed migration and job-history material; it does not define a covered-earnings hierarchy node.",
    45: "Retained exact proxy-respondent Head/Wife attachment evidence; other interviewer fields are outside scope.",
    46: "Reviewed disfigurement, address, and job prose; no covered-earnings evidence retained.",
    47: "Reviewed structure and neighborhood material; no covered-earnings evidence retained.",
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256(source_tools.canonical_json_bytes(value))


def page_texts() -> list[str]:
    path = CAPTURE_ROOT / PDF_FILENAME
    raw = path.read_bytes()
    if len(raw) != PDF_SIZE or _sha256(raw) != PDF_SHA256:
        raise ValueError("fam1969_QxQs.pdf whole-file identity drift")
    if questionnaire_inventory._pdftotext_version() != "26.04.0":
        raise ValueError("document 3 Poppler version drift")
    pages = questionnaire_inventory._pdftotext_pages(path)
    if len(pages) != PAGE_COUNT:
        raise ValueError("document 3 page-count drift")
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
    6: [
        unit(
            FLOW,
            at("FOR THOSE WHO NEITHER OWN NOR RENT"),
            key="p6_neither",
        ),
        unit(
            REM,
            block(
                "How is that?     Do you do some work in return for your housing?",
                "(\\>Jhat?)",
            ),
            flow="p6_neither",
        ),
        unit(
            PURPOSE,
            block(
                "This set of questions is to determine whether this housing should",
                "housing from essentially free living quarters.",
            ),
            flow="p6_neither",
        ),
        unit(
            REM,
            line("How much would it rent for if it was rented?"),
            flow="p6_neither",
        ),
        unit(
            PURPOSE,
            block(
                "If R asks, we want rent for a comparable house or apartment includ-",
                "use this to make a better estimate of the family's economic status.",
            ),
            flow="p6_neither",
        ),
    ],
    8: [
        unit(
            C,
            block(
                "Now we would like to know about your present job: are you working",
                "now, looking for work, retired, a housewife, or what?",
            ),
        ),
        unit(
            PURPOSE,
            block(
                "This question and the following D, E, and F sequence apply to the",
                "which section to ask, see Crucial Instructions for this Questionnaire .",
            ),
            anchors=(("p8_head", ROLE, at("head")),),
        ),
        unit(
            FLOW,
            at("working\n          now"),
            key="p8_working",
        ),
        unit(
            FLOW,
            at("looking for work"),
            key="p8_looking",
        ),
        unit(
            FLOW,
            at("retired, a housewife, or what?"),
            key="p8_retired",
        ),
        unit(
            C,
            at("What is your main occupation?"),
            anchors=(("p8_main_occupation", JOB, at("main occupation")),),
            parents=("p8_main_occupation",),
            flow="p8_working",
        ),
        unit(
            C,
            at("What kind of work did you do when you worked?"),
            flow="p8_retired",
        ),
        unit(
            PURPOSE,
            block(
                "Again, remember these questions refer to the head of the family.",
                "or d) shovel coal into a furnace.",
            ),
            flow=("p8_working", "p8_looking", "p8_retired"),
        ),
    ],
    9: [
        unit(
            PURPOSE,
            block(
                "4.   Other particularly unacceptable answers are:",
                'you do" when the initial response is inadequate.',
            ),
            flow=("p8_working", "p8_looking", "p8_retired"),
        ),
        unit(
            C,
            line("Do you work for someone else, yourself, or what?"),
            parents=("p8_main_occupation",),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "Do not assume tha t R is self- employed or not.",
                "may help us to be sure we get all his jobs.",
            ),
            flow="p8_working",
        ),
        unit(
            C,
            line("How long have you had this job?"),
            anchors=(("p9_current_job", JOB, at("this job")),),
            parents=("p9_current_job",),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "We are primarily interested in how long he has been working for this",
                "new position as a new job, accept that and continue with D6-9.",
            ),
            flow="p8_working",
        ),
        unit(
            C,
            block(
                "What happened to the job you had before",
                "were you laid off or what?",
            ),
            anchors=(("p9_prior_job", JOB, at("the job you had before")),),
            parents=("p9_prior_job",),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "The alterna tives given in the question are purposely a bit negative",
                "omitted .",
            ),
            flow="p8_working",
        ),
        unit(
            FLOW,
            block(
                "If the head of the household has jus t entered the labor force",
                "omitted .",
            ),
            key="p9_first_job_omission",
            flow="p8_working",
        ),
        unit(
            C,
            block(
                "Does your present job pay more than the previous job?",
                "than the one you had bef ore? Why is that?",
            ),
            parents=("p9_current_job", "p9_prior_job"),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "These three questions t aken together are designed to get a com-",
                "the answer was volunteered .",
            ),
            flow="p8_working",
        ),
        unit(
            FLOW,
            spanned(
                "In this case D9 may be omitted since",
                "the answer was volunteered .",
            ),
            key="p9_d9_omission",
            flow="p8_working",
        ),
    ],
    10: [
        unit(
            PURPOSE,
            block(
                "GENERAL INSTRUCTIONS FOR QUESTIONS Dl0-Dl6",
                "be that the head was in school for part of the year.",
            ),
            flow="p8_working",
        ),
        unit(
            C,
            block(
                "Did you take any vacation during 1968?",
                "take?",
            ),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "This figure should include unpaid as well as paid vacation.",
                'redundant and write down the "2 weeks . "',
            ),
            flow="p8_working",
        ),
        unit(
            C,
            block(
                "Did you miss any work in 1968 because you were sick or because",
                "anyone else in the family was sick? How much work did you miss?",
            ),
            flow=("p8_working", "p8_looking"),
        ),
        unit(
            PURPOSE,
            block(
                "Again, include both paid and unpaid sick leave .",
                'sick 4 days and took off a week when my wife had an operation."',
            ),
            flow=("p8_working", "p8_looking"),
        ),
        unit(
            C,
            block(
                "Did you miss any work in 1968 because you were unemployed or on",
                "strike? How much work did you miss?",
            ),
            flow="p8_working",
        ),
        unit(
            C,
            line(
                "Then, how many weeks were you unemployed or laid off in 1968?"
            ),
            flow="p8_looking",
        ),
        unit(
            PURPOSE,
            block(
                "Unemployment here technically means completely without work.",
                "the head's answer here and note any clarification in the margin .",
            ),
            flow=("p8_working", "p8_looking"),
        ),
        unit(
            PURPOSE,
            block(
                "For heads who are currently employed we ask later about extra jobs",
                "whether such work coincided with unemployment on his main job.",
            ),
            flow="p8_working",
        ),
        unit(
            C,
            line(
                "Then how many weeks did you work on your main job (jobs) in 1968?"
            ),
            anchors=(("p10_main_job", JOB, at("main job")),),
            parents=("p10_main_job",),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "If the respondent changed his main job during the year this applies",
                "mental check at this point to see that the time does indeed add up.",
            ),
            flow="p8_working",
        ),
    ],
    11: [
        unit(
            C,
            block(
                "And on the average , how many hours a week did you work on your main",
                "of overtime did you work in 1968 ?",
            ),
            parents=("p10_main_job",),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "We are ultimately interested in the total number of hours the head",
                "wasn't paid fo r t he extra work .",
            ),
            flow="p8_working",
        ),
        unit(
            C,
            block(
                "Did you have any extra jobs or other ways of making money in",
                "else?",
            ),
            anchors=(("p11_extra_jobs", JOB, at("extra jobs")),),
            parents=("p11_extra_jobs",),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "In this question , as in D2 , we would like complete enough informa-",
                "also relevant if he volunteers i t .",
            ),
            flow="p8_working",
        ),
        unit(
            REPEAT,
            block(
                "In this question , as in D2 , we would like complete enough informa-",
                'good; "I work at the hospital" is not.',
            ),
            flow="p8_working",
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            REM,
            line("How much did you make per hour at this?"),
            parents=("p11_extra_jobs",),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "This should be s t raightforwar d where the head is working for someone",
                'an answer like "I can\'t figure it by the hour" is acceptable.',
            ),
            flow="p8_working",
        ),
    ],
    12: [
        unit(
            C,
            block(
                "And how many weeks did you work on this extra job in 1968? On",
                "the average, how many hours a week did you work on your extra job(s)?",
            ),
            parents=("p11_extra_jobs",),
            flow="p8_working",
        ),
        unit(
            PURPOSE,
            block(
                "Here our objective is to find out the total number of hours the head",
                'what?"',
            ),
            flow="p8_working",
        ),
    ],
    16: [
        unit(
            REPEAT,
            line("E6   See D6"),
            flow="p8_looking",
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    17: [
        unit(
            C,
            line("How many weeks did you work in 1968?"),
            flow="p8_looking",
        ),
        unit(
            C,
            line("About how many hours a week did you work when you worked?"),
            flow="p8_looking",
        ),
        unit(
            C,
            line("How many weeks were you sick in 1968?"),
            flow="p8_looking",
        ),
        unit(
            C,
            line("Then how many weeks were you unemployed in 1968?"),
            flow="p8_looking",
        ),
        unit(
            PURPOSE,
            block(
                "These questions are roughly equivalent to Dl0-17 and those",
                "ask E9 and ElO to divide the year between sickness and unemployment.",
            ),
            flow="p8_looking",
        ),
        unit(
            REPEAT,
            spanned(
                "These questions are roughly equivalent to Dl0-17 and those",
                "instructions apply.",
            ),
            flow="p8_looking",
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    18: [
        unit(
            C,
            line(
                "During the last year (1968) di d you do any work for money?"
            ),
            anchors=(("p18_work_for_money", JOB, at("work for money")),),
            parents=("p18_work_for_money",),
            flow="p8_retired",
        ),
        unit(
            PURPOSE,
            block(
                "Such work may have been irregular part-time work or work on a full",
                "any money earning activity during 1968.",
            ),
            flow="p8_retired",
        ),
        unit(
            C,
            line("What kind of work did you do when you worked?"),
            parents=("p18_work_for_money",),
            flow="p8_retired",
        ),
        unit(
            PURPOSE,
            line("The response must be occupation codable - see D2"),
            flow="p8_retired",
        ),
        unit(
            REPEAT,
            line("The response must be occupation codable - see D2"),
            flow="p8_retired",
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            C,
            block(
                "How many weeks did you work last year?",
                "did you work?",
            ),
            parents=("p18_work_for_money",),
            flow="p8_retired",
        ),
        unit(
            PURPOSE,
            block(
                "We want to be able to calculate the total hours of work in 1968.",
                "generally don't fit into such a schedule.",
            ),
            flow="p8_retired",
        ),
    ],
    19: [
        unit(
            C,
            block(
                "Did your wife do any work for money last year?",
                "did she do?",
            ),
            anchors=(
                ("p19_wife", ROLE, at("wife")),
                ("p19_wife_job", JOB, at("work for money")),
            ),
            parents=("p19_wife_job",),
        ),
        unit(
            PURPOSE,
            line("See objectives for Dl-D2"),
        ),
        unit(
            REPEAT,
            line("See objectives for Dl-D2"),
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            C,
            block(
                "About how many weeks did she work last year?",
                "hours a week did she work?",
            ),
            parents=("p19_wife_job",),
        ),
        unit(
            PURPOSE,
            line("See objectives f or D16-D17"),
        ),
        unit(
            REPEAT,
            line("See objectives f or D16-D17"),
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    24: [
        unit(
            PURPOSE,
            block(
                "The income asked about in this section is, of course, the largest",
                "important that you try to get complete and accurate responses.",
            ),
        ),
        unit(
            PURPOSE,
            block(
                "We regard the Family Unit as having had the same composition all",
                "too.",
            ),
        ),
        unit(
            FLOW,
            at("Farmer or rancher"),
            key="p24_farmer",
        ),
        unit(
            FLOW,
            at("Not a farmer or rancher"),
            key="p24_not_farmer",
        ),
        unit(
            PURPOSE,
            spanned(
                "A farmer for our purposes",
                "farmers apply to ranchers also.",
            ),
        ),
        unit(
            REPEAT,
            spanned(
                "We pick up farming as a secondary source of income in Hllb",
                "for non-farmers .",
            ),
            flow="p24_not_farmer",
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            FARM,
            block(
                "What were your total receipts from farming in 1968, including soil",
                "bank payments and commodity credit loans?",
            ),
            flow="p24_farmer",
        ),
        unit(
            PURPOSE,
            block(
                "The following are included here as receipts from normal farming",
                "4)   receipts from commodity credit loans",
            ),
            flow="p24_farmer",
        ),
        unit(
            PURPOSE,
            block(
                "Do not include as farming receiEts:",
                "3)   crop loans - not income",
            ),
            flow="p24_farmer",
        ),
    ],
    25: [
        unit(
            FARM,
            block(
                "What were your total operating expenses , not counting living",
                "expenses?",
            ),
            flow="p24_farmer",
        ),
        unit(
            PURPOSE,
            block(
                "Farm operating expenses may include :",
                "7)   property taxes (b ut not Federal Income Taxes)",
            ),
            flow="p24_farmer",
        ),
        unit(
            FARM,
            line("That left you a ne t income of"),
            flow="p24_farmer",
        ),
        unit(
            PURPOSE,
            block(
                "Simply defined, farm in come equals total receipts less operating",
                "to discover omissions and correct errors .",
            ),
            flow="p24_farmer",
        ),
        unit(
            BUS,
            block(
                "Did you (R and Family) own a business at any time during 1968, or",
                "have a financial interest in any business enterprise?",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "The responden t need not be a businessman for this question to be",
                "enterprise .",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            C,
            block(
                "Is it a corporation or an unincorporated business, or do you have",
                "an interest in both kinds ?",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "If the respondent does not seem to under stand the question, assume",
                "clearly for such persons.",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            FLOW,
            at("(FOR UNINCORPORATED BUSINESSES)"),
            key="p25_unincorporated",
            flow=INCOME_PATHS,
        ),
        unit(
            BUS,
            spanned(
                "How much was your family's ' share",
                "you took out plus any profits you left in?",
            ),
            flow="p25_unincorporated",
        ),
        unit(
            PURPOSE,
            spanned(
                "The figure should include the total profits from the business in",
                "ident ification, and add.",
            ),
            flow="p25_unincorporated",
        ),
        unit(
            REPEAT,
            spanned(
                "If he does give you separate figures for",
                "ident ification, and add.",
            ),
            flow="p25_unincorporated",
            repeat={"relation": "explicit_repeat_instruction"},
        ),
        unit(
            REPEAT,
            spanned(
                "If the wife or other member of the family",
                "labeled and added in here.",
            ),
            flow="p25_unincorporated",
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    26: [
        unit(
            TOT,
            block(
                "How much did you (Head) receive from wages and salaries in 1968,",
                "that is, before anything was deducted for taxes and other things?",
            ),
            anchors=(("p26_head", ROLE, at("Head")),),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            spanned(
                "This question applies only to the Head of the family and its ob-",
                "W2 form(s) .",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            REPEAT,
            spanned(
                "It should include income from a second job if the",
                "cases where he has two jobs.",
            ),
            flow=INCOME_PATHS,
            repeat={"relation": "explicit_repeat_instruction"},
        ),
        unit(
            PURPOSE,
            block(
                "1)   Fixed salary rates :",
                "not R's current salary rate.",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "2)   Complicated work history :",
                "sent it along .",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            REPEAT,
            block(
                "3)   Businessmen: The wages and salaries that unincorporated",
                "included here.",
            ),
            flow=INCOME_PATHS,
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            REM,
            block(
                "In addition to this, did you have any income from bonuses, overtime",
                "or commissions? How much was that?",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                'Note the phrase "In addition to this."',
                "thing has been left out of the H8 figure.",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            REPEAT,
            block(
                "If R has already included some or all of his income from these",
                "thing has been left out of the H8 figure.",
            ),
            flow=INCOME_PATHS,
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            PURPOSE,
            block(
                "Hlla    (IN ANSWERING QUESTIONS Hlla-llk, IT IS VERY IMPORTANT TO STATE",
                "WHETHER THE AMOUNTS GIVEN ARE WEEKLY, MONTHLY, ANNUAL, OR WHAT)",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            REM,
            block(
                "Did you (Head) receive any other income in 1968 from a professional",
                "practice or trade?",
            ),
            anchors=(("p26_other_head", ROLE, at("Head")),),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "1)   Income BEFORE TAXES but AFTER EXPENSES is called for",
                "and the latter is included here.",
            ),
            flow=INCOME_PATHS,
        ),
    ],
    27: [
        unit(
            FARM,
            at("farming or market gardening"),
            flow="p24_not_farmer",
        ),
        unit(
            REPEAT,
            block(
                "If farming is R's primary occupation, his income",
                '"farming" income, however .',
            ),
            flow="p24_not_farmer",
            repeat={"relation": "explicit_cross_reference"},
        ),
        unit(
            REPEAT,
            spanned(
                "If R is the owner of a small incorporated",
                "H8 .",
            ),
            flow=INCOME_PATHS,
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    31: [
        unit(
            TOT,
            line("Wife's Income"),
            anchors=(("p31_wife", ROLE, at("Wife")),),
            flow=INCOME_PATHS,
        ),
        unit(
            PURPOSE,
            block(
                "1.   Make sur e the wife ' s income from all sources is recorded,",
                "however small the amount .",
            ),
            flow=INCOME_PATHS,
        ),
        unit(
            REPEAT,
            block(
                "3.   If some or all of the wife's income is from work in the family",
                "included in H7 .",
                last_occurrence=1,
            ),
            flow=INCOME_PATHS,
            repeat={"relation": "explicit_cross_reference"},
        ),
    ],
    45: [
        unit(PURPOSE, line("Who was respondent?")),
        unit(
            PURPOSE,
            block(
                "We have asked you to interview the head of the FU, but in cases",
                "other than the head may have been your respondent.",
            ),
            anchors=(
                ("p45_head", ROLE, at("head")),
                ("p45_proxy_head", ROLE, at("head", 1)),
            ),
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
    if set(PAGE_NOTES) != set(range(1, PAGE_COUNT + 1)):
        raise ValueError("page review notes do not cover every page")
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
            if kind in {C, REM, TOT, FARM, BUS}:
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

    page_review_rows = []
    for page_number, text in enumerate(pages, start=1):
        page_review_rows.append(
            {
                "page_number": page_number,
                "page_text_utf8_sha256": _sha256(text.encode("utf-8")),
                "review_note": PAGE_NOTES[page_number],
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
                "all_47_pages_including_empty_occurrence_pages"
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
        rows[max(0, containing_index - 7) : containing_index + 1]
    ):
        stripped = row["text"].lstrip()
        if stripped.startswith("SECTION "):
            return None
        match = PRINTED_IDENTIFIER_PREFIX_RE.match(stripped)
        if match is not None:
            return match.group("identifier")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    review = build_review(page_texts())
    raw = source_tools.canonical_json_bytes(review)
    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_bytes() != raw:
            raise SystemExit("document 3 source review drift")
        print(f"document 3 source review reproduces: {OUTPUT_PATH}")
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
