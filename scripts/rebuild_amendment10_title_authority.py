#!/usr/bin/env python3
"""Rebuild Amendment 10 title authority from the complete raw census.

This construction is intentionally separate from the successor-census runner.
It enumerates the closed title/header grammar over all 89,599 source rows,
adjudicates every contextual candidate, and then rebuilds the context-free
segment/start authority from the pre-title Amendment 10 baseline.  Contexts
whose title and non-title occurrences require different tags retain the
baseline vector and are resolved by the runtime contextual overlay.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pprint
import re
import resource
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from populace_dynamics.data.psid_unit_authority import (
    _TITLE_UNMARKED_OUTPUT_BLOCKS,
    _TITLE_UNMARKED_OUTPUT_LINES,
    TITLE_GENERIC_UNIT_FAMILIES,
    TITLE_LITERAL_FAMILIES,
    _coding_candidate_spans,
    _extract_statement_spans,
    _merge_title_start_tag,
    _normalized_segments,
    _normalized_title_start,
    _raw_title,
    _title_body_code_row,
    _title_body_instruction_row,
    _title_editorial_note_row,
    _title_selector_spans,
    _word_start_offsets,
    canonical_json_bytes,
    canonical_sha256,
    normalize_description,
    title_header_candidates,
)

BASELINE_COMMIT = "4a71b8f2"
OLD_TITLE_COMMIT = "f70d327"
BASELINE_SEGMENT_SHA256 = (
    "ddd4a48d3508247e4be04bd2959ca1b59bbf5f4b448ca843fc2d044804f795e1"
)
EXPECTED_FIELD_COUNT = 89_599

TITLE_MODULE = Path("src/populace_dynamics/data/psid_unit_title_authority.py")
PREDICATE_MODULE = Path(
    "src/populace_dynamics/data/psid_unit_predicate_authority.py"
)

PHYSICAL_WORD_UNIT = {
    "day": "day",
    "days": "day",
    "dollar": "united_states_dollar",
    "dollars": "united_states_dollar",
    "hour": "hour",
    "hours": "hour",
    "mile": "mile",
    "miles": "mile",
    "minute": "minute",
    "minutes": "minute",
    "month": "month",
    "months": "month",
    "week": "week",
    "weeks": "week",
    "year": "year",
    "years": "year",
}

FAMILY_UNIT = {
    "dollar_amount": "united_states_dollar",
    "dollar_value": "united_states_dollar",
    "dollars_per_hour": "united_states_dollar_per_hour",
    "dollars_per_week": "united_states_dollar_per_week",
    "hours_a_week": "hour_per_week",
    "hours_per_week": "hour_per_week",
    "hours_per_year": "hour_per_year",
    "in_dollars": "united_states_dollar",
    "in_minutes": "minute",
    "miles_per_year": "mile_per_year",
    "nominal_day_token": "day",
    "nominal_dollar_token": "united_states_dollar",
    "nominal_hour_token": "hour",
    "nominal_mile_token": "mile",
    "nominal_minute_token": "minute",
    "nominal_month_token": "month",
    "nominal_week_token": "week",
    "nominal_year_token": "year",
    "number_of_days": "day",
    "number_of_months": "month",
    "number_of_weeks": "week",
    "number_of_years": "year",
    "parenthetical_in_years": "year",
    "percent_word": "percent",
}

UNIT_FAMILIES = defaultdict(set)
for _family, _unit in FAMILY_UNIT.items():
    UNIT_FAMILIES[_unit].add(_family)


def _cross_lf_pattern(spelling: str, *, ignore_case: bool) -> re.Pattern[str]:
    """Compile one exact grammar spelling with SP/LF separator closure."""

    body = r"[ \n]+".join(re.escape(part) for part in spelling.split(" "))
    return re.compile(
        rf"(?<![A-Za-z])(?:{body})(?![A-Za-z])",
        re.ASCII | (re.IGNORECASE if ignore_case else 0),
    )


_CROSS_LF_COMPOUND_PATTERNS = tuple(
    (family, _cross_lf_pattern(spelling, ignore_case=False))
    for family, spellings in TITLE_LITERAL_FAMILIES
    for spelling in spellings
    if " " in spelling or "\n" in spelling
) + tuple(
    (family, _cross_lf_pattern(spelling, ignore_case=True))
    for family, spellings in TITLE_GENERIC_UNIT_FAMILIES
    for spelling in spellings
    if " " in spelling or "\n" in spelling
)


def _cross_lf_compound_transition(
    description: str,
) -> tuple[
    tuple[tuple[str, int, int, str], ...],
    tuple[tuple[str, int, int, str], ...],
]:
    """Return raw and maximal grammar compounds whose match crosses an LF."""

    found: set[tuple[str, int, int, str]] = set()
    for family, pattern in _CROSS_LF_COMPOUND_PATTERNS:
        for match in pattern.finditer(description):
            spelling = match.group()
            if "\n" not in spelling:
                continue
            start, end = match.span()
            found.add(
                (
                    family,
                    len(description[:start].encode("utf-8")),
                    len(description[:end].encode("utf-8")),
                    spelling,
                )
            )
    maximal = tuple(
        candidate
        for candidate in found
        if not any(
            candidate[1] >= other[1]
            and candidate[2] <= other[2]
            and (candidate[1], candidate[2]) != (other[1], other[2])
            for other in found
        )
    )
    return tuple(
        sorted(found, key=lambda row: (row[1], row[2], row[0]))
    ), tuple(sorted(maximal, key=lambda row: (row[1], row[2], row[0])))


REFERENCE_HEAD = re.compile(
    r"^(?:\(?bkt\.?\b|accuracy\b|average accuracy\b|bracket\b)",
    re.IGNORECASE,
)
MONEY_WORDS = re.compile(
    r"\b(?:amount|benefits?|costs?|earn(?:ed|ing|ings)?|income|make|made|pay|paid|"
    r"payments?|prices?|salary|spend|spent|value|wages?)\b",
    re.IGNORECASE,
)
EXPLICIT_US_CURRENCY = re.compile(
    r"\$|\b(?:dollars?|cents?|USD)\b",
    re.IGNORECASE,
)
YEARLY_MONEY_WORDS = re.compile(
    r"\b(?:amount|benefits?|costs?|earnings?|expenditures?|expenses?|income|"
    r"payments?|premiums?|rent|salary|taxes|value|wages?)\b",
    re.IGNORECASE,
)
WEEKLY_MONEY_WORDS = re.compile(
    r"\b(?:amount|costs?|earnings?|expenditures?|expenses?|food|income|pay|"
    r"spending|wages?)\b",
    re.IGNORECASE,
)
DIRECT_PHYSICAL_AFTER_HOW_MANY = re.compile(
    r"^\s+(?:of\s+(?:these|those|the)\s+)?"
    r"(?:(?:actual|additional|average|approximate|calendar|completed|"
    r"consecutive|full|more|other|remaining|school|total|usual|whole)\s+){0,3}"
    r"(days?|dollars?|hours?|miles?|minutes?|months?|weeks?|years?)\b",
    re.IGNORECASE,
)
YES_NO_BEFORE_QUANTIFIER = re.compile(
    r"\b(?:can|could|do|does|did|would)\b[^?]{0,40}\b(?:know|recall|"
    r"remember|tell|estimate)\b",
    re.IGNORECASE,
)
UNSUPPORTED_RATE = re.compile(
    r"\b(?:per|a)\s+(?:day|month|week|year)\b",
    re.IGNORECASE,
)

DOLLARS_WORTH_SELECTOR_HEAD = re.compile(
    r"^F(?:9|12|16)\. How many dollars' worth of stamps(?: or benefits)? "
    r"did you (?:get in \d{4}|receive)\?--"
)
DOLLARS_WORTH_1992_COMPOSITE_HEADS = frozenset(
    {
        "F8. Did you (or anyone else in your family) use government food "
        "stamps at any time in 1992? F9. How many dollars' worth of stamps "
        f"did you get in 1992? - {selector}"
        for selector in ("AMOUNT", "TIME UNIT")
    }
)
PENSION_ALTERNATIVE_FORMAT = re.compile(
    r"\bEither in dollars per month or year, or as a percent of "
    r"(?:your|her) pay when (?:you|she) left that job\?",
    re.IGNORECASE,
)
HIGHEST_COLLEGE_YEAR_TITLE = re.compile(
    r"^(?:G45|N45|K30|L30|L43|M43|K46|K53|K78d|L53|L78d)\. "
    r"(?:Altogether, )?[Ww]hat is the highest year of college "
    r"(?:you have|she has|\(you/she\) \(have/has\)|"
    r"\(you/he/she\) \(have/has\)|"
    r"\(you have/\[(?:she/he|he/she)\] has\)) completed\?$"
)
SCHOOL_YEARS_OUTSIDE_US_TITLE = re.compile(
    r"^(?:K83a\. \(Between \[PY IW DATE\] and now, how/How\) many years "
    r"of school did \(you/she\) complete outside of the U\.S\.\?|"
    r"L83a\. \(Between \[PY IW DATE\] and now, how/How\) many years "
    r"of school did \(you/he/she\) complete outside of the U\.S\.\?)$"
)
GRADE_OR_YEAR_ATTENDING_TITLE = re.compile(
    r"^(?:K84a\. \(Earlier you said \[you are/\[SPOUSE/PARTNER\] is\] "
    r"still in school\.\) What grade or year \(are/is\) \(you/she\) attending\?|"
    r"L84a\. \(Earlier you said \[you are/\[HEAD\] is\] still in school\.\) "
    r"What grade or year \(are/is\) \(you/he/she\) attending\?)$"
)
CALENDAR_YEAR_EDUCATION_TITLE = re.compile(
    r"^(?:K83\. In what month and year did \(you/she\) receive\(your/her\) "
    r"highest degree\?--YEAR|"
    r"L83\. In what month and year did \(you/he/she\) receive your/his/her "
    r"highest degree\?--YEAR)$"
)
CALENDAR_COHORT_SHA256 = (
    "ae57aabad4d23427a2ef3ba74bb0e2a43ff7d8e5f601ab09b341463ec6574995"
)
RAW_INPUT_RELATION_SHA256 = (
    "563b1eaede9dcb5a085d8014dd3a4aacb2d3419ce7d0a0eb65063753b375ca6e"
)
OUTPUT_LABEL_ENDING_ADJUDICATION_SHA256 = (
    "7a3865642ec7e2795a56dfdeaacc69b4a7b2afdabe2e2457ce1b0f1badaaf6d5"
)
CURRENCY_DEFAULT_REMOVED_FIELD_PROJECTION_SHA256 = (
    "52652010ae3956fc7e419f5163ecd6d00762e8a888e46ca117fc8bea51f39777"
)
SEMANTIC_COMPONENT_DEDUP_REGRESSIONS = {
    "ER49467": "AMOUNT FROM PREVIOUS EMPLOYER",
    "ER53141": "MONTH",
    "ER55217": "AMOUNT FROM PREVIOUS EMPLOYER",
    "ER62267": "TIME UNIT",
    "ER62339": "AMOUNT FROM PREVIOUS EMPLOYER",
    "ER62347": "TIME UNIT",
}
FIRST_QUESTION_TYPICAL_WEEK_F1A_FIELDS = frozenset(
    {
        "ER66714",
        "ER66727",
        "ER72718",
        "ER72731",
        "ER78795",
        "ER78808",
        "ER82788",
        "ER82801",
    }
)
FIRST_QUESTION_TYPICAL_WEEK_DE60A_FIELDS = frozenset(
    {"ER66683", "ER72685", "ER78761", "ER82753"}
)
FIRST_QUESTION_H59L_FIELDS = frozenset(
    {"ER23274", "ER40408", "ER46381", "ER51742"}
)
FIRST_QUESTION_IMM19_FIELDS = frozenset({"ER81263", "ER81316"})
FIRST_QUESTION_P34_FIELDS = frozenset(
    {"ER68025", "ER74047", "ER80169", "ER84139"}
)
FIRST_QUESTION_A8_FIELDS = frozenset(
    {"ER66029", "ER72029", "ER78030", "ER82031"}
)
FIRST_QUESTION_OTHER_COUNT_FIELDS = frozenset({"V11867", "V12242", "ER81270"})
LATER_QUESTION_COUNT_FIELDS = frozenset(
    {"V203", "V235", "V236", "V278", "V15919", "V15944", "V15969"}
)
LATER_QUESTION_WEEK_FIELDS = frozenset({"V223", "V658"})
LATER_QUESTION_TYPICAL_WEEK_FIELDS = frozenset({"V225", "V659"})
LATER_QUESTION_HOUR_FIELDS = frozenset({"V290"})
QUESTION_LINE_SUFFIX_COUNT_FIELDS = frozenset({"V8651", "V8652"})


def _git_source(commit: str, path: Path) -> str:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path.as_posix()}"], text=True
    )


def _literal_assignment(source: str, name: str) -> Any:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        elif isinstance(node, ast.Assign):
            target = node.targets[0] if len(node.targets) == 1 else None
            value = node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(value)
    raise ValueError(f"missing literal assignment {name}")


def _char_offset(text: str, byte_offset: int) -> int:
    return len(text.encode("utf-8")[:byte_offset].decode("utf-8"))


def _candidate_char_span(
    header: str, candidate: tuple[str, int, int, str]
) -> tuple[int, int]:
    return (
        _char_offset(header, candidate[1]),
        _char_offset(header, candidate[2]),
    )


def _is_reference_header(header: str) -> bool:
    return bool(REFERENCE_HEAD.match(header.lstrip()))


def _is_threshold(header: str, candidate: tuple[str, int, int, str]) -> bool:
    start, end = _candidate_char_span(header, candidate)
    left = header[max(0, start - 36) : start].lower()
    right = header[end : end + 22].lower()
    if candidate[0] in {"dollar_symbol", "percent_symbol"}:
        return True
    if re.search(
        r"(?:at least|less than|more than|under|over|up to|minimum of|"
        r"maximum of|several|couple of|last)\s+(?:\d+\s+)?$",
        left,
    ):
        return True
    return bool(re.match(r"\s*(?:or more|or less)\b", right))


def _selector_terminal_component(
    label: str,
) -> tuple[str, int, int]:
    """Return the last ``--`` component and its raw character span."""

    components = _selector_components(label)
    if not components:
        return "", 0, 0
    component, start, end = components[-1]
    return component, start, end


def _selector_components(label: str) -> tuple[tuple[str, int, int], ...]:
    """Return every nonempty nested ``--`` component with raw spans."""

    markers = list(re.finditer(r"--", label))
    bounds: list[tuple[int, int]] = []
    component_start = 0
    for marker in markers:
        bounds.append((component_start, marker.start()))
        component_start = marker.end()
    bounds.append((component_start, len(label)))

    components: list[tuple[str, int, int]] = []
    for component_index, (raw_start, raw_end) in enumerate(bounds):
        raw_component = label[raw_start:raw_end]
        leading = len(raw_component) - len(raw_component.lstrip())
        trailing = len(raw_component) - len(raw_component.rstrip())
        start = raw_start + leading
        end = raw_end - trailing
        # A three-hyphen source marker leaves one marker hyphen at the start
        # of the first captured component because the structural scanner has
        # already consumed the first ``--`` pair.
        if component_index == 0:
            while start < end and label[start] == "-":
                start += 1
        if start < end:
            components.append((label[start:end], start, end))
    return tuple(components)


def _unique_physical_unit(component: str) -> str | None:
    cleaned = normalize_description(component).upper()
    matches = {
        unit
        for spelling, unit in PHYSICAL_WORD_UNIT.items()
        if re.search(rf"\b{re.escape(spelling.upper())}\b", cleaned)
    }
    if re.search(r"\bPERCENT(?:AGE)?\b", cleaned):
        matches.add("percent")
    return next(iter(matches)) if len(matches) == 1 else None


def _output_label_unit(label: str) -> str | None:
    component, _start, _end = _selector_terminal_component(label)
    cleaned = normalize_description(component).upper()
    physical = (
        r"(?:DAYS?|HOURS?|MILES?|MINUTES?|MONTHS?(?: [1-5])?|"
        r"WEEKS?|YEARS?(?: [1-5])?|PERCENT(?:AGE)?)"
    )
    # Discovery of a unique unit word is not enough: labels such as ``FIRST
    # MENTION IF PAID BY HOUR`` are categorical.  These are the closed
    # source-attested quantity/coordinate label constructions.
    quantity_label = bool(
        re.match(rf"^(?:(?:NUMBER OF|TOTAL)\s+)?{physical}(?:\s|$)", cleaned)
        or re.match(
            rf"^(?:BEGINNING|ENDING|END)\s+{physical}(?:\s|$)",
            cleaned,
        )
        or re.fullmatch(r"(?:HEAD|WIFE/\"WIFE\")\s+(?:HOURS|MINUTES)", cleaned)
        or re.fullmatch(
            rf"(?:MOST RECENT|SECOND MOST RECENT) ATTACHMENT\s+{physical}",
            cleaned,
        )
    )
    if not quantity_label:
        return None
    return _unique_physical_unit(component)


def _continuation_output_label_unit(label: str) -> str | None:
    """Recognize only the 200 source-attested continuation output labels."""

    cleaned = label.strip().upper()
    if re.fullmatch(r"MONTH(?: [1-5])?|MONTHS", cleaned):
        return "month"
    if re.fullmatch(r"YEAR(?: [1-5])?|YEARS", cleaned):
        return "year"
    if cleaned == "WEEKS":
        return "week"
    if cleaned == "DAYS":
        return "day"
    if re.fullmatch(r"PERCENT OF (?:PAY|EMPLOYER CONTRIBUTION)", cleaned):
        return "percent"
    return None


def _response_selector_component(component: str) -> str | None:
    """Return one closed unit-less response selector, if present."""

    cleaned = normalize_description(component).upper()
    match = re.match(
        r"^(?:AMOUNT|TIME UNIT|TYPE|LUMP(?: SUM)?)(?:\s|$)",
        cleaned,
    )
    return cleaned if match is not None else None


def _response_selector_family(component: str) -> str | None:
    """Collapse an exact response component to its closed leading label."""

    cleaned = _response_selector_component(component)
    if cleaned is None:
        return None
    for family in (
        "TYPE OF RESPONSE",
        "TIME UNIT",
        "LUMP SUM",
        "AMOUNT",
        "TYPE",
    ):
        if cleaned.startswith(family):
            return family
    raise ValueError(f"unclassified response selector: {component!r}")


def _categorical_hour_selector(component: str) -> bool:
    """Recognize exact selector labels where ``HOUR(S)`` is categorical."""

    cleaned = normalize_description(component).upper()
    return bool(
        re.fullmatch(
            r"(?:FIRST|SECOND|THIRD) MENTION IF PAID BY HOUR"
            r"(?: FOR CURRENT MAIN JOB)?|"
            r"2\. SAME JOB: WORKED MORE HOURS/GOT A RAISE",
            cleaned,
        )
    )


def _legacy_first_line_title(description: str) -> str:
    """Return the pre-extension title solely for pinned transition audits."""

    first_lf = description.find("\n")
    if first_lf < 0:
        return description
    end = first_lf
    if description[:first_lf].endswith("--"):
        second_lf = description.find("\n", first_lf + 1)
        end = len(description) if second_lf < 0 else second_lf
    return description[:end]


def _pre_round3_title(description: str) -> str:
    """Return the title under the selector/header law before round 3."""

    first_lf = description.find("\n")
    if first_lf < 0:
        return description
    header_end = first_lf
    if description[:first_lf].endswith("--"):
        second_lf = description.find("\n", first_lf + 1)
        header_end = len(description) if second_lf < 0 else second_lf
    for kind, _start, end, _label in _title_selector_spans(description):
        if kind not in {"single_hyphen", "single_hyphen_next_line"}:
            header_end = max(header_end, end)
    return description[:header_end]


def _round3_candidate_transition(
    description: str,
) -> tuple[
    tuple[tuple[str, int, int, str], ...],
    frozenset[tuple[str, int, int, str]],
    frozenset[tuple[str, int, int, str]],
    frozenset[tuple[str, int, int, str]],
    frozenset[tuple[str, int, int, str]],
    frozenset[tuple[str, int, int, str]],
    frozenset[tuple[str, int, int, str]],
]:
    """Partition final candidates by monotone round-3 grammar extension."""

    baseline_header = _pre_round3_title(description)
    baseline = frozenset(title_header_candidates(baseline_header))
    first_question = description.find("?")
    question_header = (
        description[: max(len(baseline_header), first_question + 1)]
        if first_question >= 0
        else baseline_header
    )
    after_question = frozenset(title_header_candidates(question_header))
    singleton_end = len(question_header)
    for kind, _start, end, _label in _title_selector_spans(description):
        if kind in {"single_hyphen", "single_hyphen_next_line"}:
            singleton_end = max(singleton_end, end)
    singleton_header = description[:singleton_end]
    after_singletons = frozenset(title_header_candidates(singleton_header))
    last_question = description.rfind("?")
    all_questions_header = description[: max(singleton_end, last_question + 1)]
    after_all_questions = frozenset(
        title_header_candidates(all_questions_header)
    )
    last_question_lf = (
        description.find("\n", last_question) if last_question >= 0 else -1
    )
    question_line_end = singleton_end
    if last_question >= 0:
        question_line_end = (
            len(description) if last_question_lf < 0 else last_question_lf
        )
    question_line_header = description[: max(singleton_end, question_line_end)]
    after_question_line = frozenset(
        title_header_candidates(question_line_header)
    )
    bounded_header = _raw_title(description)
    after_continuations = frozenset(title_header_candidates(bounded_header))
    final = frozenset(title_header_candidates(description))
    first_question_delta = after_question - baseline
    singleton_delta = after_singletons - after_question
    later_question_delta = after_all_questions - after_singletons
    question_line_suffix_delta = after_question_line - after_all_questions
    question_continuation_delta = after_continuations - after_question_line
    full_body_delta = final - after_continuations
    if (
        baseline
        | first_question_delta
        | singleton_delta
        | later_question_delta
        | question_line_suffix_delta
        | question_continuation_delta
        | full_body_delta
        != final
    ):
        raise ValueError("round-3 candidate transition is not an exact cover")
    return (
        tuple(sorted(baseline, key=lambda row: (row[1], row[2], row[0]))),
        first_question_delta,
        singleton_delta,
        later_question_delta,
        question_line_suffix_delta,
        question_continuation_delta,
        full_body_delta,
    )


def _first_question_positive(
    field_id: str, candidate: tuple[str, int, int, str]
) -> tuple[str, str] | None:
    """Return the exact independently audited first-question W clauses."""

    family = candidate[0]
    if (
        field_id
        in (
            FIRST_QUESTION_TYPICAL_WEEK_F1A_FIELDS
            | FIRST_QUESTION_TYPICAL_WEEK_DE60A_FIELDS
        )
        and family == "nominal_hour_token"
    ):
        return "hour_per_week", "typical_week_hours_title_denotation"
    if (
        field_id in FIRST_QUESTION_H59L_FIELDS
        and family == "nominal_day_token"
    ):
        return "day", "wrapped_alternative_days_title_denotation"
    if (
        field_id in FIRST_QUESTION_IMM19_FIELDS
        and family == "nominal_year_token"
    ):
        return "year", "outside_us_years_title_denotation"
    if field_id in FIRST_QUESTION_P34_FIELDS and family == "percent_word":
        return "percent", "pension_percent_title_denotation"
    if (
        field_id
        in (FIRST_QUESTION_A8_FIELDS | FIRST_QUESTION_OTHER_COUNT_FIELDS)
        and family == "how_many_count_marker"
    ):
        return "count", "direct_count_question_title_denotation"
    return None


def _first_question_negative_reason(
    candidate: tuple[str, int, int, str], header: str
) -> str:
    """Classify one audited first-question N start without inferring a unit."""

    family = candidate[0]
    if family == "number_of_years" and re.search(
        r"\bpension|retirement plan\b", header, re.IGNORECASE
    ):
        return "pension_formula_year_phrase_is_input"
    if family in {
        "dollar_symbol",
        "hundreds_of_dollars",
        "nominal_dollar_token",
        "percent_word",
    }:
        return "first_question_amount_or_threshold_input"
    if family in {
        "per_month_rate_phrase",
        "daily_morphology",
        "weekly_morphology",
    }:
        return "first_question_frequency_or_rate_input"
    if family in {"how_many_count_marker", "number_of_years"}:
        return "first_question_quantifier_or_formula_input"
    return "first_question_coordinate_frequency_or_comparison_input"


def _later_question_positive(
    field_id: str, candidate: tuple[str, int, int, str]
) -> tuple[str, str] | None:
    """Return the exact independently audited later-question W clauses."""

    family = candidate[0]
    if (
        field_id in LATER_QUESTION_COUNT_FIELDS
        and family == "how_many_count_marker"
    ):
        return "count", "later_direct_count_question_title_denotation"
    if (
        field_id in LATER_QUESTION_WEEK_FIELDS
        and family == "nominal_week_token"
    ):
        return "week", "later_direct_weeks_title_denotation"
    if (
        field_id in LATER_QUESTION_TYPICAL_WEEK_FIELDS
        and family == "hours_a_week"
    ):
        return "hour_per_week", "later_typical_week_hours_title_denotation"
    if (
        field_id in LATER_QUESTION_HOUR_FIELDS
        and family == "nominal_hour_token"
    ):
        return "hour", "later_direct_hours_title_denotation"
    return None


def _question_line_suffix_positive(
    field_id: str, candidate: tuple[str, int, int, str]
) -> tuple[str, str] | None:
    """Return the two audited W clauses after a line's final question mark."""

    if (
        field_id in QUESTION_LINE_SUFFIX_COUNT_FIELDS
        and candidate[0] == "number_of_count_marker"
    ):
        return "count", "parenthetical_count_suffix_title_denotation"
    return None


def _standalone_output_label_ending(
    description: str,
    candidate: tuple[str, int, int, str],
) -> tuple[str, bool, str] | None:
    """Adjudicate one mechanically label-shaped, line-final body ending.

    The caller supplies a maximal full-body candidate.  This superdomain is
    otherwise field-blind: an exact physical line of one to eight ASCII words
    must end at the candidate, must not be an Actual/Code statement head, and
    must either begin with ASCII uppercase or consist only of the candidate.
    A qualifying output label additionally needs a nonempty label prefix, a
    directly mapped candidate family, and no encoded ``digit(s) of``
    coordinate marker.
    """

    family = candidate[0]
    start, end = _candidate_char_span(description, candidate)
    line_start = description.rfind("\n", 0, start) + 1
    line_end = description.find("\n", start)
    if line_end < 0:
        line_end = len(description)
    line = description[line_start:line_end]
    if (
        end != line_end
        or re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+){0,7}", line) is None
        or line.startswith(("Actual ", "Code "))
        or not ("A" <= line[0] <= "Z" or line == candidate[3])
    ):
        return None
    prefix = description[line_start:start]
    if not prefix.strip():
        return line, False, "bare_unit_token_has_no_label_prefix"
    if FAMILY_UNIT.get(family) is None:
        return line, False, "compound_or_rate_family_not_direct_unit"
    if re.search(r"\bdigits?\b", prefix, re.ASCII):
        return line, False, "encoded_coordinate_not_quantity_output"
    return line, True, "exact_standalone_output_label_line"


def _removed_field_projection(
    denominator_field_keys: tuple[tuple[int, str], ...],
    removal_events: tuple[tuple[int, str, str], ...],
) -> tuple[tuple[int, str], ...]:
    """Filter denominator order to fields named by at least one event."""

    removed_keys = {
        (wave, field_id) for wave, field_id, _false_class in removal_events
    }
    return tuple(key for key in denominator_field_keys if key in removed_keys)


def _unmarked_output_positive(
    description: str,
    candidate: tuple[str, int, int, str],
) -> tuple[str, str] | None:
    """Admit exact unmarked output subtitle starts under the general law."""

    family = candidate[0]
    standalone = _standalone_output_label_ending(description, candidate)
    if standalone is not None and standalone[1]:
        unit = FAMILY_UNIT[family]
        return unit, "standalone_output_label_names_currency"
    start, _end = _candidate_char_span(description, candidate)
    line_start = description.rfind("\n", 0, start) + 1
    line_end = description.find("\n", start)
    if line_end < 0:
        line_end = len(description)
    line = description[line_start:line_end]
    next_end = description.find("\n", line_end + 1)
    if next_end < 0:
        next_end = len(description)
    following = (
        description[line_end + 1 : next_end]
        if line_end < len(description)
        else ""
    )
    if line == "Number of years from now":
        if family == "number_of_years":
            return "year", "unmarked_year_output_title_denotation"
        return None
    if line.startswith("Total consumption as a percent of"):
        if family == "percent_word":
            return "percent", "unmarked_percent_output_title_denotation"
        return None
    if line in _TITLE_UNMARKED_OUTPUT_LINES:
        if family == "number_of_count_marker":
            return "count", "unmarked_count_output_title_denotation"
        return None
    if (line, following) in _TITLE_UNMARKED_OUTPUT_BLOCKS and (
        family == "percent_word"
    ):
        return "percent", "unmarked_percentage_output_title_denotation"
    if (line, following) in _TITLE_UNMARKED_OUTPUT_BLOCKS and (
        family == "in_dollars"
    ):
        return (
            "united_states_dollar",
            "wrapped_in_dollars_output_title_denotation",
        )
    return None


def _full_body_negative_reason(
    description: str, candidate: tuple[str, int, int, str]
) -> str:
    """Ground one full-body title defeat or its cross-class delegation."""

    start, _end = _candidate_char_span(description, candidate)
    line_start = description.rfind("\n", 0, start) + 1
    line_end = description.find("\n", start)
    if line_end < 0:
        line_end = len(description)
    line = description[line_start:line_end]
    if description.startswith("Annual food standard (Needs)\n"):
        return "input_table_or_subrange_not_field_denotation"
    if line.startswith(("Actual ", "actual ")):
        return "delegated_to_actual_statement_grammar"
    normalized = normalize_description(description)
    normalized_start = _normalized_title_start(description, candidate[1])
    if any(
        offset <= normalized_start < offset + len(statement)
        for offset, statement in _coding_candidate_spans(normalized)
    ):
        return "delegated_to_coding_statement_grammar"
    if any(
        offset <= normalized_start < offset + len(statement)
        for offset, statement in _extract_statement_spans(normalized)
    ):
        return "delegated_to_primary_statement_grammar"
    next_end = description.find("\n", line_end + 1)
    if next_end < 0:
        next_end = len(description)
    following = (
        description[line_end + 1 : next_end]
        if line_end < len(description)
        else ""
    )
    if (line, following) in _TITLE_UNMARKED_OUTPUT_BLOCKS and (
        candidate[0] == "nominal_dollar_token"
    ):
        return "unmarked_output_dollar_phrase_is_conversion_input"
    local_start = max(0, start - 90)
    local_end = min(len(description), start + 180)
    local = normalize_description(description[local_start:local_end])
    if re.search(
        r"(?:^|\s)(?:IF|If|ENTER|Enter|PROBE|NOTE|Note|ASK|Ask|RECORD|Record)\b|"
        r"\b(?:threshold|table|subrange|range of values|valid response|"
        r"less than|more than|at least|at most|or more|or less|missing data|"
        r"input|instruction|code values?)\b",
        local,
    ):
        return "instruction_threshold_table_or_subrange_defeat"
    if re.search(
        r"(?:=|\+|\*|/)|\b(?:formula|sum|summation|calculate|calculated|"
        r"calculation|compute|computed|convert|converted|divide|divided|"
        r"multiply|multiplied|prorat|weighted|component|operand|ratio)\b|"
        r"\b(?:V|ER)\d+[A-Z_]*\b",
        local,
        re.IGNORECASE,
    ):
        return "formula_or_operand_defeat"
    if candidate[0] in {
        "nominal_day_token",
        "nominal_month_token",
        "nominal_year_token",
        "number_of_days",
        "number_of_months",
        "number_of_years",
        "reference_hour_token",
    } and re.search(
        r"\b(?:age|birth|born|calendar|current|date|last|model|next|"
        r"previous|reference|school|since|during|from|through|until)\b",
        local,
        re.IGNORECASE,
    ):
        return "calendar_or_reference_body_prose_defeat"
    return "explanatory_body_prose_defeat"


def _legacy_output_label(
    header: str,
) -> tuple[str | None, int | None, int | None, str]:
    """Replay the superseded single-label parser only to pin its corrections."""

    if "\n" in header:
        first, label = header.split("\n", 1)
        start = len(first.encode("utf-8")) + 1
        return (
            _continuation_output_label_unit(label),
            start,
            start + len(label.encode("utf-8")),
            label,
        )
    match = re.search(
        r"(?P<mark>--|(?<!-)-)\s*(?P<label>(?:NUMBER OF\s+)?"
        r"(?:DAYS?|HOURS?|MILES?|MINUTES?|MONTHS?|WEEKS?|YEARS?|"
        r"PERCENT(?:AGE)?)(?:\s+(?:FOR|OF)\b.*)?)$",
        header,
    )
    if match is None:
        return None, None, None, ""
    label = match.group("label")
    start = len(header[: match.start("label")].encode("utf-8"))
    return (
        _unique_physical_unit(label),
        start,
        start + len(label.encode("utf-8")),
        label,
    )


def _header_selector_occurrences(
    header: str,
) -> tuple[tuple[str, int, int, str, str, bool], ...]:
    """Enumerate every exact nested selector component and byte span."""

    found: dict[tuple[int, int, str], tuple[str, int, int, str, str, bool]] = (
        {}
    )
    kind_rank = {
        "double_hyphen": 0,
        "split_hyphen": 1,
        "next_line": 2,
        "single_hyphen": 3,
        "single_hyphen_next_line": 4,
    }
    for kind, label_start, _label_end, label in _title_selector_spans(header):
        components = _selector_components(label)
        for component_index, (
            component,
            relative_start,
            relative_end,
        ) in enumerate(components):
            terminal = component_index == len(components) - 1
            semantic_component = bool(
                _output_label_unit(component) is not None
                or _response_selector_component(component) is not None
                or _categorical_hour_selector(component)
            )
            if not terminal and not semantic_component:
                continue
            # The ``--\nLABEL`` layout is a generic extraction continuation.
            # It is a semantic selector only for the exact closed output or
            # response vocabulary established by the source census.
            if kind == "next_line" and not semantic_component:
                continue
            start_char = label_start + relative_start
            end_char = label_start + relative_end
            start_byte = len(header[:start_char].encode("utf-8"))
            end_byte = len(header[:end_char].encode("utf-8"))
            row = (
                kind,
                start_byte,
                end_byte,
                component,
                label,
                terminal,
            )
            key = (start_byte, end_byte, component)
            previous = found.get(key)
            if previous is not None and previous[5] != terminal:
                raise ValueError(
                    f"selector component has inconsistent terminal status: "
                    f"{key!r}"
                )
            if previous is None or kind_rank[kind] < kind_rank[previous[0]]:
                found[key] = row
    return tuple(
        sorted(found.values(), key=lambda row: (row[1], row[2], row[0]))
    )


def _header_output_labels(
    header: str,
) -> tuple[tuple[str, int, int, str, str], ...]:
    """Return every selector component naming a closed quantity token."""

    return tuple(
        (unit, start, end, component, label)
        for _kind, start, end, component, label, _terminal in _header_selector_occurrences(
            header
        )
        if (unit := _output_label_unit(component)) is not None
    )


def _header_response_selectors(header: str) -> tuple[str, ...]:
    """Return exact unit-less response-component selectors in one header."""

    found: list[str] = []
    for (
        _kind,
        _start,
        _end,
        component,
        _label,
        _terminal,
    ) in _header_selector_occurrences(header):
        if selector := _response_selector_component(component):
            found.append(selector)
    return tuple(found)


def _body_ground_units(description: str) -> set[str]:
    """Read only exact unit-naming source lines as corroborating groundings."""

    units: set[str] = set()
    normalized_body = normalize_description(
        "\n".join(description.split("\n")[1:])
    ).lower()
    if re.match(
        r"the values for this variable(?: in the range 001-997)? represent "
        r"the actual number of months(?=\b|head|wife)",
        normalized_body,
    ):
        units.add("month")
    for line in description.split("\n")[1:]:
        lower = line.strip().lower()
        if not lower.startswith(
            ("actual ", "the code values ", "the values ", "values ")
        ):
            continue
        if re.search(r"dollars? (?:and cents )?per hour", lower):
            units.add("united_states_dollar_per_hour")
        elif re.search(r"dollars? per week", lower):
            units.add("united_states_dollar_per_week")
        elif re.search(r"hours? (?:worked )?(?:a|per) week", lower):
            units.add("hour_per_week")
        elif re.search(r"hours? per year", lower):
            units.add("hour_per_year")
        elif re.search(r"miles? per year", lower):
            units.add("mile_per_year")
        elif re.search(r"(?:number of |in )minutes?\b", lower):
            units.add("minute")
        elif re.search(r"(?:number of |in )hours?\b", lower):
            units.add("hour")
        elif re.search(r"(?:number of |in )days?\b", lower):
            units.add("day")
        elif re.search(r"(?:number of |in )weeks?\b", lower):
            units.add("week")
        elif re.search(
            r"(?:number of |in )months?(?:\b|(?=head\b)|(?=wife\b))", lower
        ):
            units.add("month")
        elif re.search(r"(?:number of |in )years?\b", lower):
            units.add("year")
        elif re.search(r"(?:number of |in )miles?\b", lower):
            units.add("mile")
        elif re.search(r"\bpercent(?:age)?\b", lower):
            units.add("percent")
        elif re.search(r"\bdollars?\b|\bdollar amount\b", lower):
            units.add("united_states_dollar")
        elif re.search(
            r"^actual (?:number of|count of)\b|"
            r"^(?:the )?values?\b.*\brepresent(?:s)? (?:the )?(?:total )?"
            r"number of\b",
            lower,
        ):
            units.add("count")
    return units


def _paid_extra_hours_yes_no(description: str, header: str) -> bool:
    """Identify the exact 62-field paid-extra-hours Boolean cohort."""

    header_local = re.search(
        r"\bwork more hours than usual\b.*\bget paid\b",
        header,
        re.IGNORECASE,
    )
    wrapped = re.search(
        r"\bwork more hours than usual\b", header, re.IGNORECASE
    ) and re.search(
        r"\bget paid for those extra hours of work\?--CURRENT MAIN JOB\b",
        description,
        re.IGNORECASE,
    )
    return bool(header_local or wrapped)


def _calendar_coordinate_candidate(
    header: str, candidate: tuple[str, int, int, str]
) -> bool:
    """Defeat exact calendar-coordinate nouns that do not name durations."""

    family, _start, _end, spelling = candidate
    if (family, spelling.lower()) not in {
        ("nominal_day_token", "day"),
        ("nominal_month_token", "month"),
        ("nominal_year_token", "year"),
    }:
        return False
    start, _end = _candidate_char_span(header, candidate)
    if start == 0:
        return True
    lower = header.lower()
    if family == "nominal_year_token" and re.search(
        r"\b(?:year model|model year)\b", lower
    ):
        return True
    return family in {"nominal_month_token", "nominal_year_token"} and bool(
        re.search(r"\b(?:month|year) of birth\b", lower)
    )


def _selector_unit_is_denotational(
    row: dict[str, Any], header: str, unit: str, component: str
) -> tuple[bool, str]:
    """Adjudicate an exact unit-token selector as quantity or coordinate."""

    cleaned = normalize_description(component).upper()
    if unit == "month" and not re.search(r"\bMONTHS\b", cleaned):
        return False, "singular_month_selector_is_calendar_coordinate"
    if unit == "year" and not re.search(r"\bYEARS\b", cleaned):
        if re.search(r"\bAt what age\b", header, re.IGNORECASE):
            return True, "age_question_year_selector_names_duration_unit"
        return False, "singular_year_selector_is_calendar_coordinate"
    if unit == "day" and not re.search(r"\bDAYS\b", cleaned):
        return False, "singular_day_selector_is_calendar_coordinate"
    if unit == "week" and not re.search(r"\bWEEKS\b", cleaned):
        return False, "singular_week_selector_is_calendar_coordinate"
    return True, "exact_output_label_names_unit"


def _overtime_amount_is_explicit_hours(
    header: str, response_selectors: tuple[str, ...]
) -> bool:
    """Identify the 14 numeric overtime-hour AMOUNT fields, not TIME UNIT."""

    return response_selectors == ("AMOUNT",) and bool(
        re.match(
            r"^(?:BC|DE)14[Bb]4\. How many hours did that overtime amount to\b",
            header,
        )
    )


def _dollars_worth_amount_is_explicit_dollars(
    header: str, response_selectors: tuple[str, ...]
) -> bool:
    """Identify the eleven dollar-valued food-stamp AMOUNT fields."""

    return response_selectors == ("AMOUNT",) and bool(
        DOLLARS_WORTH_SELECTOR_HEAD.match(header)
        or normalize_description(header) in DOLLARS_WORTH_1992_COMPOSITE_HEADS
    )


def _pension_amount_is_explicit_dollars(
    header: str, response_selectors: tuple[str, ...]
) -> bool:
    """Identify the 24 monetary pension AMOUNT arms."""

    return (
        len(response_selectors) == 1
        and response_selectors[0].startswith("AMOUNT")
        and PENSION_ALTERNATIVE_FORMAT.search(normalize_description(header))
        is not None
    )


def _direct_physical_title(
    description: str,
    header: str,
    candidate: tuple[str, int, int, str],
) -> bool:
    family, _start, _end, spelling = candidate
    lower = header.lower()
    start, end = _candidate_char_span(header, candidate)
    left = lower[max(0, start - 48) : start]
    right = lower[end : end + 56]
    if family == "nominal_hour_token":
        if re.search(
            r"\bwork more hours than usual\b.*\bget paid\b|"
            r"\b(?:in addition to|besides) the weeks and hours worked\b|"
            r"\bwhat hours you could work\b|\bduring work hours\b|"
            r"\bdid you tell me\b.*\bwork earlier\b.*\bwork hours\b|"
            r"\bextra hour\b.*\bearn\b.*\bthat hour\b",
            lower,
        ):
            return False
        if _paid_extra_hours_yes_no(description, header):
            return False
        return bool(
            start == 0
            or re.search(
                r"\b(?:annual|average|elapsed|total|usual|work(?:ed|ing)?)\s+"
                r"(?:[a-z'-]+\s+){0,3}$",
                left,
            )
            or re.search(r"\bwork\s+$", left)
            or re.match(r"\s+(?:of|spent|worked|working)\b", right)
        )
    if family == "nominal_day_token":
        return bool(
            start == 0
            or re.search(r"\b(?:actual|interview|total)\s+$", left)
            or re.match(r"\s+(?:missed|unemployed|worked)\b", right)
            or re.match(r"\s+of (?:current )?interview\b", right)
        )
    if family == "nominal_week_token":
        return bool(
            start == 0
            or re.search(r"\btotal\s+$", left)
            or re.match(
                r"\s+(?:missed|of vacation|on strike|unemployed|worked)\b",
                right,
            )
            or re.match(r"\s+of (?:current )?interview\b", right)
        )
    if family == "nominal_month_token":
        if left.endswith("["):
            return False
        return bool(
            start == 0
            or re.search(r"\b(?:actual|interview|total)\s+$", left)
            or re.match(
                r"\s+of (?:birth|current interview|death|interview|move)\b",
                right,
            )
            or re.match(
                r"\s+(?:employed|received|unemployed|used|worked)\b", right
            )
        )
    if family == "nominal_year_token":
        if left.endswith("["):
            return False
        return bool(
            start == 0
            or re.search(
                r"\b(?:actual|interview|model|school|total)\s+$",
                left,
            )
            or re.match(
                r"\s+(?:born|completed|employed|model|of (?:birth|current "
                r"interview|death|education|interview|move)|schooling|"
                r"unemployed|worked)\b",
                right,
            )
        )
    if family == "nominal_minute_token":
        return bool(
            start == 0
            or re.search(
                r"\b(?:commut(?:e|ing)|elapsed|interview length|travel time)"
                r"[^?]{0,45}$",
                left,
            )
        )
    if family == "nominal_mile_token":
        return bool(
            start == 0
            or re.search(r"\bdistance(?: traveled)?\s+$", left)
            or re.match(r"\s+traveled\b", right)
        )
    if family == "nominal_dollar_token":
        return bool(
            re.search(r"\b(?:annual|actual|total)\s+$", left)
            or re.match(r"\s+(?:cost|saved|spent|value)\b", right)
            or (left.endswith("total ") and re.match(r"\s+cost\b", right))
        )
    return False


def _old_authority() -> tuple[tuple[Any, ...], ...]:
    source = _git_source(OLD_TITLE_COMMIT, TITLE_MODULE)
    return _literal_assignment(source, "TITLE_START_AUTHORITY")


def _adjudicate_context(
    row: dict[str, Any],
    candidates: tuple[tuple[str, int, int, str], ...],
    old_rows_by_sha: dict[str, list[tuple[Any, ...]]],
    currency_default_removals: list[tuple[int, str, str]] | None = None,
) -> list[tuple[str | None, str, str]]:
    """Return one explicit W/N decision for each title candidate."""

    description = row["source_description"]
    header = _raw_title(description)
    lower = header.lower()
    sha = hashlib.sha256(description.encode("utf-8")).hexdigest()
    old_exact = {
        (old[2], old[3], old[4], old[5]): (old[6], old[7], old[8])
        for old in old_rows_by_sha.get(sha, [])
    }
    old_positive = [
        old
        for old in old_rows_by_sha.get(sha, [])
        if old[7] == "whole_domain_denotation" and old[6] is not None
    ]

    def record_currency_default_removal(false_class: str) -> None:
        if currency_default_removals is not None:
            currency_default_removals.append(
                (
                    row["interview_wave"],
                    row["raw_field_id"],
                    false_class,
                )
            )

    selected: dict[int, tuple[str, str]] = {}
    forced_negative: dict[int, str] = {}
    semantic_lock: str | None = None
    semantic_lock_reason = ""
    (
        _baseline_candidates,
        first_question_delta,
        singleton_delta,
        later_question_delta,
        question_line_suffix_delta,
        question_continuation_delta,
        full_body_delta,
    ) = _round3_candidate_transition(description)
    final_candidates = frozenset(candidates)
    if (
        not first_question_delta <= final_candidates
        or not later_question_delta <= final_candidates
        or not singleton_delta <= final_candidates
        or not question_line_suffix_delta <= final_candidates
        or not question_continuation_delta <= final_candidates
        or not full_body_delta <= final_candidates
    ):
        raise ValueError(
            f"round-3 candidate missing from final header: "
            f"{row['interview_wave']} {row['raw_field_id']}"
        )
    for index, candidate in enumerate(candidates):
        if candidate in first_question_delta:
            forced_negative[index] = _first_question_negative_reason(
                candidate, header
            )
        elif candidate in later_question_delta:
            forced_negative[index] = (
                "later_question_phrase_not_value_denotation"
            )
        elif candidate in singleton_delta:
            forced_negative[index] = (
                "singleton_title_phrase_not_value_denotation"
            )
        elif candidate in question_line_suffix_delta:
            forced_negative[index] = (
                "question_line_suffix_phrase_not_value_denotation"
            )
        elif candidate in question_continuation_delta:
            forced_negative[index] = (
                "question_continuation_phrase_not_value_denotation"
            )
        elif candidate in full_body_delta:
            forced_negative[index] = _full_body_negative_reason(
                description, candidate
            )

    all_candidates = candidates
    bounded_candidates = tuple(
        candidate
        for candidate in all_candidates
        if candidate not in full_body_delta
    )
    if all_candidates[: len(bounded_candidates)] != bounded_candidates:
        raise ValueError("full-body candidates are not a terminal raw suffix")
    # All bounded-header inference below is deliberately blind to the
    # conservative full-body superdomain.  Full-body starts receive only the
    # default/delegation defeats above or the exact output-registry overrides
    # near the end of this function.  Prefix order preserves every index.
    candidates = bounded_candidates

    def select(index: int, unit: str, reason: str) -> None:
        if semantic_lock is not None and semantic_lock != unit:
            forced_negative[index] = semantic_lock_reason
            return
        previous = selected.get(index)
        if previous is not None and previous[0] != unit:
            raise ValueError(
                f"candidate assigned two units: {row['interview_wave']} "
                f"{row['raw_field_id']} {candidates[index]!r}"
            )
        selected[index] = (unit, reason)

    # Every exact selector occurrence controls the alternatives named in its
    # logical question block.  ER47619 deliberately has two same-unit W starts.
    output_labels = _header_output_labels(header)
    response_selectors = _header_response_selectors(header)
    overtime_amount_hours = _overtime_amount_is_explicit_hours(
        header, response_selectors
    )
    dollars_worth_amount = _dollars_worth_amount_is_explicit_dollars(
        header, response_selectors
    )
    pension_amount_dollars = _pension_amount_is_explicit_dollars(
        header, response_selectors
    )
    active_response_selectors = (
        ()
        if overtime_amount_hours or dollars_worth_amount
        else response_selectors
    )
    output_matching: set[int] = set()
    output_units: set[str] = set()
    selector_negative_reasons: set[str] = set()
    for (
        output_unit,
        label_byte_start,
        label_byte_end,
        component,
        _label,
    ) in output_labels:
        denotes_unit, selector_reason = _selector_unit_is_denotational(
            row, header, output_unit, component
        )
        matching = [
            index
            for index, candidate in enumerate(candidates)
            if label_byte_start <= candidate[1]
            and candidate[2] <= label_byte_end
            and FAMILY_UNIT.get(candidate[0]) == output_unit
        ]
        if not matching:
            raise ValueError(
                f"output label not discovered: {row['interview_wave']} "
                f"{row['raw_field_id']} {component!r} in {header!r}"
            )
        if not denotes_unit:
            selector_negative_reasons.add(selector_reason)
            for index in matching:
                forced_negative[index] = selector_reason
            continue
        effective_output_unit = output_unit
        label_char_start = _char_offset(header, label_byte_start)
        if output_unit == "hour" and re.search(
            r"\b(?:each|per) year\b",
            header[:label_char_start],
            re.IGNORECASE,
        ):
            effective_output_unit = "hour_per_year"
        output_units.add(effective_output_unit)
        for index in matching:
            output_matching.add(index)
            forced_negative.pop(index, None)
            select(index, effective_output_unit, selector_reason)

    if len(output_units) > 1:
        raise ValueError(
            f"conflicting output selectors: {row['interview_wave']} "
            f"{row['raw_field_id']} {sorted(output_units)!r}"
        )
    if output_labels:
        for index in range(len(candidates)):
            if index not in output_matching:
                forced_negative[index] = (
                    next(iter(selector_negative_reasons))
                    if selector_negative_reasons and not output_matching
                    else "alternative_defeated_by_output_label"
                )
    if active_response_selectors:
        for index in range(len(candidates)):
            forced_negative[index] = (
                "alternative_defeated_by_response_selector"
            )

    # These terminal labels contain an hour word but select a categorical
    # mention/job-change arm, not an hour-valued output.
    for (
        _kind,
        start,
        end,
        component,
        _label,
        _terminal,
    ) in _header_selector_occurrences(header):
        if not _categorical_hour_selector(component):
            continue
        for index, candidate in enumerate(candidates):
            if (
                start <= candidate[1]
                and candidate[2] <= end
                and FAMILY_UNIT.get(candidate[0]) == "hour"
            ):
                forced_negative[index] = (
                    "categorical_hour_selector_not_quantity"
                )

    reference = _is_reference_header(header)
    selector = " ".join(active_response_selectors)
    if reference:
        for index in range(len(candidates)):
            forced_negative[index] = "referenced_input_or_accuracy_title"

    # Preserve every earlier contextual adjudication unless an exact output
    # selector newly exposes that the phrase belongs to a different subfield.
    selector_controls = bool(output_labels or active_response_selectors)
    if not selector_controls and not reference:
        for index, candidate in enumerate(candidates):
            exact = old_exact.get(candidate)
            if exact is None:
                continue
            unit, disposition, reason = exact
            if disposition == "whole_domain_denotation" and unit is not None:
                select(index, unit, reason)
            else:
                forced_negative[index] = reason

        # A newly maximal compound may contain an old positive which the new
        # scanner correctly suppressed.  Transfer the adjudication only when
        # the compound's supported unit is the same semantic target.
        for old in old_positive:
            if any(
                candidate == (old[2], old[3], old[4], old[5])
                for candidate in candidates
            ):
                continue
            containing = [
                (index, candidate)
                for index, candidate in enumerate(candidates)
                if candidate[1] <= old[3] and old[4] <= candidate[2]
            ]
            if len(containing) == 1:
                index, candidate = containing[0]
                compound_unit = FAMILY_UNIT.get(candidate[0], old[6])
                if compound_unit == old[6]:
                    select(index, old[6], old[8])

    inherited_units = {unit for unit, _reason in selected.values()}
    if len(inherited_units) > 1:
        raise ValueError(
            f"inherited title conflict: {row['interview_wave']} "
            f"{row['raw_field_id']} {sorted(inherited_units)!r}"
        )
    if inherited_units:
        semantic_lock = next(iter(inherited_units))
        semantic_lock_reason = "phrase_subordinate_to_preserved_title_unit"

    if _paid_extra_hours_yes_no(description, header):
        for index, candidate in enumerate(candidates):
            if candidate[0] in {"nominal_hour_token", "nominal_week_token"}:
                forced_negative[index] = (
                    "conditional_paid_extra_hours_yes_no_input"
                )

    for index, candidate in enumerate(candidates):
        if _calendar_coordinate_candidate(header, candidate):
            forced_negative[index] = "calendar_coordinate_not_duration_unit"
        if "year-to-year changes" in header.lower():
            if candidate[0] == "number_of_years":
                select(
                    index,
                    "count",
                    "count_of_changes_title_denotation",
                )
            elif candidate[0] == "nominal_year_token":
                forced_negative[index] = "year_phrase_modifies_change_count"

    # An included/excluded/comparison operand is not a second title
    # denotation merely because it repeats the governing unit word.
    for index, candidate in enumerate(candidates):
        if candidate[0] != "nominal_hour_token":
            continue
        start, _end = _candidate_char_span(header, candidate)
        left = header[:start]
        if re.search(
            r"\b(?:excluding|including)\s+$|\bcomparable to 1967\s+$",
            left,
            re.IGNORECASE,
        ):
            forced_negative[index] = (
                "hour_phrase_modifies_included_or_reference_input"
            )

    # A repeated period noun in ``all/most of the <period>`` describes the
    # coverage of the event named by the governing quantity.  It is not a
    # second stored-value denotation (for example, V7980's governing
    # ``how many days`` versus its terminal ``all or most of the day``).
    for index, candidate in enumerate(candidates):
        if candidate[0] not in {
            "nominal_day_token",
            "nominal_week_token",
            "nominal_month_token",
            "nominal_year_token",
        }:
            continue
        start, _end = _candidate_char_span(header, candidate)
        if re.search(
            r"\b(?:all|most|all or most) of the\s+$",
            header[:start],
            re.IGNORECASE,
        ):
            forced_negative[index] = "period_phrase_is_reference_coverage"

    if not reference and not selector_controls:
        # Supported rate compounds precede their bases.  Unsupported rate
        # spellings remain visible explicit defeats.
        for index, candidate in enumerate(candidates):
            family = candidate[0]
            if family == "per_hour_rate_phrase":
                would_select = bool(
                    MONEY_WORDS.search(header)
                    and "SALAR" not in description.upper()
                    and not _is_threshold(header, candidate)
                )
                has_currency = bool(EXPLICIT_US_CURRENCY.search(description))
                if would_select and not has_currency:
                    record_currency_default_removal("money-question/per-hour")
                if would_select and has_currency:
                    select(
                        index,
                        "united_states_dollar_per_hour",
                        "money_question_denotes_dollars_per_hour",
                    )
                else:
                    forced_negative[index] = (
                        "unsupported_or_input_per_hour_phrase"
                    )
            elif family == "per_week_rate_phrase":
                if re.search(r"\bhow much time\b", lower):
                    select(
                        index,
                        "hour_per_week",
                        "time_question_denotes_hours_per_week",
                    )
                elif MONEY_WORDS.search(header):
                    if EXPLICIT_US_CURRENCY.search(description):
                        select(
                            index,
                            "united_states_dollar_per_week",
                            "money_question_denotes_dollars_per_week",
                        )
                    else:
                        record_currency_default_removal("per-week-money")
                        forced_negative[index] = (
                            "currency_unmarked_money_per_week_phrase"
                        )
                else:
                    forced_negative[index] = (
                        "unsupported_or_input_per_week_phrase"
                    )
            elif family in {"hours_a_week", "hours_per_week"}:
                if not _is_threshold(header, candidate):
                    select(
                        index,
                        "hour_per_week",
                        "title_names_hours_per_week",
                    )
                else:
                    forced_negative[index] = "rate_phrase_is_threshold"
            elif family == "dollars_per_hour":
                select(
                    index,
                    "united_states_dollar_per_hour",
                    "title_names_dollars_per_hour",
                )
            elif family == "dollars_per_week":
                select(
                    index,
                    "united_states_dollar_per_week",
                    "title_names_dollars_per_week",
                )
            elif family == "hours_per_year":
                if not _is_threshold(header, candidate):
                    select(
                        index,
                        "hour_per_year",
                        "title_names_hours_per_year",
                    )
            elif family == "miles_per_year":
                if not _is_threshold(header, candidate):
                    select(
                        index,
                        "mile_per_year",
                        "title_names_miles_per_year",
                    )
            elif family in {
                "dollars_per_month_or_year",
                "dollars_per_year",
                "per_day_rate_phrase",
                "per_month_rate_phrase",
                "per_year_rate_phrase",
                "hundreds_of_dollars",
            }:
                forced_negative[index] = (
                    "unsupported_rate_or_scale_title_phrase"
                )

        # Morphological spellings are separately enumerated.  Only the two
        # source-grounded supported rate families and yearly total money
        # labels are positive.
        for index, candidate in enumerate(candidates):
            family = candidate[0]
            if family == "hourly_morphology":
                defeated = bool(
                    re.search(
                        r"\bpercent change in hourly\b|\bhow is that\?|"
                        r"\bdo you have an hourly\b|\bpaid other than\b.*\bhourly\b",
                        lower,
                    )
                    or (
                        "--" in description
                        and "MENTION" in description.upper()
                        and any(
                            marker in description.upper()
                            for marker in ("HOURLY", "PAID BY")
                        )
                    )
                    or re.search(r"--\s*(?:AMOUNT|TIME UNIT)", description)
                )
                would_select = bool(
                    re.search(r"\bhourly (?:earnings?|wage|rate)\b", lower)
                    and not defeated
                )
                has_currency = bool(EXPLICIT_US_CURRENCY.search(description))
                if would_select and not has_currency:
                    record_currency_default_removal("hourly-money")
                if would_select and has_currency:
                    select(
                        index,
                        "united_states_dollar_per_hour",
                        "hourly_money_title_denotation",
                    )
                else:
                    forced_negative[index] = "hourly_status_or_input_phrase"
            elif family == "yearly_morphology":
                would_select = bool(YEARLY_MONEY_WORDS.search(header))
                has_currency = bool(EXPLICIT_US_CURRENCY.search(description))
                if would_select and not has_currency:
                    record_currency_default_removal("yearly-money")
                if would_select and has_currency:
                    select(
                        index,
                        "united_states_dollar",
                        "yearly_total_money_title_denotation",
                    )
                else:
                    forced_negative[index] = (
                        "yearly_reference_or_unsupported_rate"
                    )
            elif family == "weekly_morphology":
                candidate_start, _candidate_end = _candidate_char_span(
                    header, candidate
                )
                if re.match(
                    r"weekly food needs?\b",
                    header[candidate_start:],
                    re.IGNORECASE,
                ) and EXPLICIT_US_CURRENCY.search(description):
                    select(
                        index,
                        "united_states_dollar",
                        "weekly_food_need_dollar_title_denotation",
                    )
                else:
                    forced_negative[index] = (
                        "weekly_reference_or_unsupported_rate"
                    )
            elif family == "monthly_morphology":
                would_select = bool(
                    re.search(
                        r"\bmonthly (?:mortgage|loan) payments?\b|"
                        r"--MONTHLY\s+AMOUNT\b|\bAFDC Maximum Monthly Allowance\b",
                        description,
                        re.IGNORECASE,
                    )
                )
                has_currency = bool(EXPLICIT_US_CURRENCY.search(description))
                if would_select and not has_currency:
                    record_currency_default_removal("monthly-money")
                if would_select and has_currency:
                    select(
                        index,
                        "united_states_dollar",
                        "monthly_money_amount_title_denotation",
                    )
                else:
                    forced_negative[index] = "unsupported_morphological_rate"
            elif family == "daily_morphology":
                forced_negative[index] = "unsupported_morphological_rate"

        # ``Total Weekly ... Work Hours`` has one governing hour phrase.  The
        # adjective supplies the supported denominator; it is not a second
        # positive candidate of its own.
        if re.search(r"\btotal weekly\b.*\bwork hours?\b", lower):
            for index, candidate in enumerate(candidates):
                if candidate[0] == "nominal_hour_token":
                    selected.pop(index, None)
                    selected[index] = (
                        "hour_per_week",
                        "weekly_modifies_whole_work_hour_measure",
                    )
                elif candidate[0] == "weekly_morphology":
                    forced_negative[index] = (
                        "weekly_modifier_subordinate_to_hour_rate"
                    )

        scoped_units = {unit for unit, _reason in selected.values()}
        if len(scoped_units) > 1:
            raise ValueError(
                "conflicting independently positive scoped title clauses: "
                f"{row['interview_wave']} {row['raw_field_id']} "
                f"{sorted(scoped_units)!r}"
            )
        if semantic_lock is None and scoped_units:
            semantic_lock = next(iter(scoped_units))
            semantic_lock_reason = "phrase_subordinate_to_scoped_title_unit"

        # Exact raw-body lines corroborate which title alternative denotes the
        # stored field.  They never consult derivation status or field_unit.
        body_units = _body_ground_units(description)
        if len(body_units) == 1:
            body_unit = next(iter(body_units))
            refinement_bases = {
                "hour_per_week": "hour",
                "hour_per_year": "hour",
                "mile_per_year": "mile",
                "united_states_dollar_per_hour": "united_states_dollar",
                "united_states_dollar_per_week": "united_states_dollar",
            }
            for index, (unit, _reason) in selected.items():
                if (
                    unit != body_unit
                    and refinement_bases.get(unit) != body_unit
                ):
                    forced_negative[index] = (
                        "phrase_is_input_to_exact_raw_body_unit"
                    )
            surviving_units = {
                unit
                for index, (unit, _reason) in selected.items()
                if index not in forced_negative
            }
            semantic_lock = (
                next(iter(surviving_units)) if surviving_units else body_unit
            )
            semantic_lock_reason = "phrase_is_input_to_exact_raw_body_unit"

        # These source-attested education questions store the completed
        # college-year level (1--4), so their singular ``year`` is the value
        # unit rather than a calendar coordinate.  The exact title grammar is
        # closed above over every observed section code and person spelling.
        if HIGHEST_COLLEGE_YEAR_TITLE.fullmatch(header):
            for index, candidate in enumerate(candidates):
                if candidate[0] == "nominal_year_token":
                    forced_negative.pop(index, None)
                    select(
                        index,
                        "year",
                        "highest_college_year_title_denotation",
                    )

        if SCHOOL_YEARS_OUTSIDE_US_TITLE.fullmatch(
            normalize_description(description)
        ):
            for index, candidate in enumerate(candidates):
                if candidate[0] == "nominal_year_token":
                    forced_negative.pop(index, None)
                    select(
                        index,
                        "year",
                        "school_years_outside_us_title_denotation",
                    )

        # Count syntax is denotational only in these closed constructions.
        for index, candidate in enumerate(candidates):
            family = candidate[0]
            if family == "how_many_count_marker":
                start, end = _candidate_char_span(header, candidate)
                direct = DIRECT_PHYSICAL_AFTER_HOW_MANY.match(header[end:])
                before = header[max(0, start - 60) : start]
                has_rate = bool(UNSUPPORTED_RATE.search(header[end:]))
                selector_defeat = selector and any(
                    marker in selector
                    for marker in (
                        "AMOUNT",
                        "PERCENT",
                        "TIME UNIT",
                        "TYPE",
                    )
                )
                wrapped_remaining_days = bool(
                    re.match(
                        r"\s+of the remaining\s+days\b",
                        description[end:],
                        re.IGNORECASE,
                    )
                )
                if selector_defeat:
                    forced_negative[index] = (
                        "count_marker_is_response_format_input"
                    )
                    if direct is not None:
                        word = direct.group(1).lower()
                        unit = PHYSICAL_WORD_UNIT[word]
                        physical_start = end + direct.start(1)
                        for other_index, other in enumerate(candidates):
                            if (
                                FAMILY_UNIT.get(other[0]) == unit
                                and _candidate_char_span(header, other)[0]
                                == physical_start
                            ):
                                forced_negative[other_index] = (
                                    "unit_phrase_is_response_format_input"
                                )
                elif direct is not None:
                    word = direct.group(1).lower()
                    unit = PHYSICAL_WORD_UNIT[word]
                    physical_start = end + direct.start(1)
                    matching = [
                        other_index
                        for other_index, other in enumerate(candidates)
                        if FAMILY_UNIT.get(other[0]) == unit
                        and _candidate_char_span(header, other)[0]
                        == physical_start
                    ]
                    supported_rate_selected = any(
                        value[0]
                        in {
                            "hour_per_week",
                            "hour_per_year",
                            "mile_per_year",
                        }
                        for value in selected.values()
                    )
                    if has_rate and not supported_rate_selected:
                        forced_negative[index] = (
                            "unsupported_count_rate_question"
                        )
                        for other_index in matching:
                            forced_negative[other_index] = (
                                "unsupported_count_rate_question"
                            )
                    else:
                        for other_index in matching:
                            select(
                                other_index,
                                unit,
                                "how_many_directly_governs_unit_noun",
                            )
                        forced_negative[index] = (
                            "count_marker_subordinate_to_unit_noun"
                        )
                elif wrapped_remaining_days:
                    forced_negative[index] = (
                        "count_marker_precedes_wrapped_physical_day_noun"
                    )
                elif YES_NO_BEFORE_QUANTIFIER.search(before):
                    forced_negative[index] = (
                        "quantified_phrase_is_yes_no_input"
                    )
                elif has_rate:
                    forced_negative[index] = "unsupported_count_rate_question"
                else:
                    select(index, "count", "how_many_direct_count_denotation")

            elif family in {
                "number_of_count_marker",
                "number_in_family_unit_marker",
            }:
                start, end = _candidate_char_span(header, candidate)
                remainder = header[end : end + 48]
                left = header[:start]
                identifier = bool(
                    re.search(
                        r"\b(?:ID|Interview|Person|Sequence)\s+$",
                        left,
                        re.IGNORECASE,
                    )
                    or re.search(
                        r"Survey Research Center identifying\s+$",
                        left,
                        re.IGNORECASE,
                    )
                )
                indefinite_yes_no = bool(
                    re.search(r"\bhave you had a\s+$", left, re.IGNORECASE)
                    and re.match(
                        r"\s+different kinds of jobs\b",
                        remainder,
                        re.IGNORECASE,
                    )
                )
                limit_yes_no = bool(
                    re.search(
                        r"\bdoing anything to limit the\s+$",
                        left,
                        re.IGNORECASE,
                    )
                    and re.match(r"\s+children\b", remainder, re.IGNORECASE)
                )
                checkpoint = bool(
                    re.search(
                        r"INTERVIEWER CHECKPOINT:\s*$", left, re.IGNORECASE
                    )
                    and re.match(
                        r"\s+Current Jobs\b", remainder, re.IGNORECASE
                    )
                )
                continuation_subrange = bool(
                    "\n" in header[:start]
                    and "values for this variable" in left.lower()
                    and "range" in left.lower()
                    and "represent the actual" in left.lower()
                )
                if family == "number_of_count_marker" and identifier:
                    forced_negative[index] = "number_phrase_is_identifier"
                elif family == "number_of_count_marker" and (
                    indefinite_yes_no or limit_yes_no
                ):
                    forced_negative[index] = "number_phrase_is_yes_no_input"
                elif family == "number_of_count_marker" and checkpoint:
                    forced_negative[index] = (
                        "number_phrase_is_checkpoint_input"
                    )
                elif (
                    family == "number_of_count_marker"
                    and continuation_subrange
                ):
                    forced_negative[index] = (
                        "number_phrase_is_subrange_metadata"
                    )
                elif family == "number_of_count_marker" and re.match(
                    r"\s+(?:days?|hours?|miles?|minutes?|months?|weeks?|years?)\b",
                    remainder,
                    re.IGNORECASE,
                ):
                    forced_negative[index] = (
                        "count_marker_subordinate_to_unit_noun"
                    )
                elif re.search(
                    r"\b(?:persons?|people) per room\b|\bratio\b", lower
                ):
                    forced_negative[index] = "unsupported_ratio_title"
                else:
                    select(index, "count", "nominal_count_title_denotation")
            elif family == "nominal_count_token":
                forced_negative[index] = (
                    "count_word_is_instruction_not_denotation"
                )

        singleton_label_spans: list[tuple[int, int, str]] = []
        for kind, label_start, label_end, label in _title_selector_spans(
            description
        ):
            if kind not in {"single_hyphen", "single_hyphen_next_line"}:
                continue
            start_byte = len(header[:label_start].encode("utf-8"))
            end_byte = len(header[:label_end].encode("utf-8"))
            singleton_label_spans.append((start_byte, end_byte, label))
        for index, candidate in enumerate(candidates):
            if (
                candidate in singleton_delta
                and candidate[0] == "number_of_count_marker"
                and any(
                    start <= candidate[1]
                    and candidate[2] <= end
                    and normalize_description(label)
                    .upper()
                    .startswith("TOTAL NUMBER OF ")
                    for start, end, label in singleton_label_spans
                )
            ):
                forced_negative.pop(index, None)
                select(
                    index,
                    "count",
                    "total_number_selector_title_denotation",
                )

        # Direct physical title nouns that do not rely on question grammar.
        for index, candidate in enumerate(candidates):
            family = candidate[0]
            unit = FAMILY_UNIT.get(family)
            if unit is None or index in selected:
                continue
            if family in {
                "dollar_amount",
                "dollar_value",
                "in_dollars",
                "in_minutes",
                "number_of_days",
                "number_of_months",
                "number_of_weeks",
                "number_of_years",
                "parenthetical_in_years",
            } and not _is_threshold(header, candidate):
                select(index, unit, "direct_title_unit_denotation")
            elif (
                family == "percent_word"
                and (
                    re.search(r"^(?:.*?\s)?percent(?:age)?\b", lower)
                    or re.search(
                        r"\b(?:what|how much) percent(?:age)?\b", lower
                    )
                )
                and "AMOUNT" not in selector
                and "TIME UNIT" not in selector
            ):
                select(index, "percent", "direct_percent_title_denotation")
            elif _direct_physical_title(
                description, header, candidate
            ) and not _is_threshold(header, candidate):
                select(index, unit, "direct_nominal_title_unit_denotation")

        if re.match(
            r"^F1(?:[b-h]|d2)\. \(In a typical week, how many hours "
            r"\[do you/does \[he/she\]\] spend\)",
            header,
        ) and body_units == {"hour_per_week"}:
            governing_hour_char = header.find("hours")
            governing_hour_byte = len(
                header[:governing_hour_char].encode("utf-8")
            )
            for index, candidate in enumerate(candidates):
                if (
                    candidate[0] == "nominal_hour_token"
                    and candidate[1] == governing_hour_byte
                ):
                    forced_negative.pop(index, None)
                    select(
                        index,
                        "hour_per_week",
                        "typical_week_hours_title_denotation",
                    )
                elif candidate[0] == "nominal_week_token":
                    forced_negative[index] = "typical_week_rate_denominator"
                elif candidate[0] == "how_many_count_marker":
                    forced_negative[index] = (
                        "count_marker_subordinate_to_unit_noun"
                    )

        if header.startswith(
            "B6. During the last year how many miles did you and your "
            "family drive in (your car/all of"
        ) and body_units == {"mile_per_year"}:
            for index, candidate in enumerate(candidates):
                if candidate[0] == "nominal_mile_token":
                    forced_negative.pop(index, None)
                    select(
                        index,
                        "mile_per_year",
                        "last_year_miles_title_denotation",
                    )
                elif candidate[0] == "nominal_year_token":
                    forced_negative[index] = "last_year_rate_denominator"
                elif candidate[0] == "how_many_count_marker":
                    forced_negative[index] = (
                        "count_marker_subordinate_to_unit_noun"
                    )

        if dollars_worth_amount:
            for index, candidate in enumerate(candidates):
                if candidate[0] == "nominal_dollar_token":
                    forced_negative.pop(index, None)
                    select(
                        index,
                        "united_states_dollar",
                        "dollars_worth_amount_title_denotation",
                    )
                elif candidate[0] == "how_many_count_marker":
                    forced_negative[index] = (
                        "count_marker_subordinate_to_unit_noun"
                    )

    for index, candidate in enumerate(candidates):
        if candidate not in first_question_delta:
            continue
        if row["raw_field_id"] in (
            FIRST_QUESTION_TYPICAL_WEEK_F1A_FIELDS
            | FIRST_QUESTION_TYPICAL_WEEK_DE60A_FIELDS
        ):
            if candidate[0] == "nominal_week_token":
                forced_negative[index] = "typical_week_rate_denominator"
            elif candidate[0] == "how_many_count_marker":
                forced_negative[index] = (
                    "count_marker_subordinate_to_unit_noun"
                )
        elif (
            row["raw_field_id"] in FIRST_QUESTION_IMM19_FIELDS
            and candidate[0] == "how_many_count_marker"
        ):
            forced_negative[index] = "count_marker_subordinate_to_unit_noun"
        positive = _first_question_positive(row["raw_field_id"], candidate)
        if positive is None:
            continue
        forced_negative.pop(index, None)
        selected[index] = positive

    for index, candidate in enumerate(candidates):
        if candidate not in later_question_delta:
            continue
        if (
            row["raw_field_id"]
            in (
                LATER_QUESTION_WEEK_FIELDS
                | LATER_QUESTION_TYPICAL_WEEK_FIELDS
                | LATER_QUESTION_HOUR_FIELDS
            )
            and candidate[0] == "how_many_count_marker"
        ):
            forced_negative[index] = "count_marker_subordinate_to_unit_noun"
        positive = _later_question_positive(row["raw_field_id"], candidate)
        if positive is None:
            continue
        forced_negative.pop(index, None)
        selected[index] = positive

    for index, candidate in enumerate(candidates):
        if candidate not in question_line_suffix_delta:
            continue
        positive = _question_line_suffix_positive(
            row["raw_field_id"], candidate
        )
        if positive is None:
            continue
        forced_negative.pop(index, None)
        selected[index] = positive

    for index, candidate in enumerate(all_candidates):
        if candidate not in full_body_delta:
            continue
        start, _end = _candidate_char_span(description, candidate)
        line_start = description.rfind("\n", 0, start) + 1
        line_end = description.find("\n", start)
        if line_end < 0:
            line_end = len(description)
        line = description[line_start:line_end]
        if (
            candidate[0] == "per_hour_rate_phrase"
            and line in {"Amount per hour", "Amount per hour."}
            and EXPLICIT_US_CURRENCY.search(description) is None
        ):
            record_currency_default_removal("unmarked-amount/hour")
        positive = _unmarked_output_positive(description, candidate)
        if positive is None:
            continue
        forced_negative.pop(index, None)
        selected[index] = positive

    if pension_amount_dollars:
        for index, candidate in enumerate(candidates):
            if candidate[0] == "in_dollars":
                forced_negative.pop(index, None)
                select(
                    index,
                    "united_states_dollar",
                    "pension_amount_arm_denotes_dollars",
                )

    # Exact standalone output labels clear neighboring formula defeats above.
    # Every remaining per-start defeat outranks a tentative inherited or
    # inferred positive.
    for index in forced_negative:
        selected.pop(index, None)

    positive_units = {unit for unit, _reason in selected.values()}
    if len(positive_units) > 1:
        raise ValueError(
            "multiple positive title units: "
            f"{row['interview_wave']} {row['raw_field_id']} {header!r} "
            f"{sorted(positive_units)!r}"
        )

    candidates = all_candidates
    result: list[tuple[str | None, str, str]] = []
    for index, candidate in enumerate(candidates):
        if index in selected:
            unit, reason = selected[index]
            result.append((unit, "whole_domain_denotation", reason))
            continue
        exact = old_exact.get(candidate)
        reason = forced_negative.get(index)
        if (
            reason is None
            and exact is not None
            and exact[1] != "whole_domain_denotation"
        ):
            reason = exact[2]
        if reason is None and selected:
            reason = "phrase_subordinate_to_selected_title_unit"
        if reason is None and _is_threshold(header, candidate):
            reason = "threshold_or_boolean_input_phrase"
        if reason is None and candidate[0] in {
            "dollar_symbol",
            "percent_symbol",
        }:
            reason = "symbol_marks_fixed_input_or_formula"
        if reason is None:
            reason = "contextual_title_phrase_not_whole_domain_denotation"
        result.append((None, "explicit_no_whole_domain_denotation", reason))
    return result


def _render_title_module(
    authority: tuple[tuple[Any, ...], ...],
    output_label_endings: tuple[tuple[Any, ...], ...],
    currency_default_removal_events: tuple[tuple[int, str, str], ...],
    currency_default_removed_fields: tuple[tuple[int, str], ...],
) -> str:
    literal = pprint.pformat(
        TITLE_LITERAL_FAMILIES, width=88, sort_dicts=False
    )
    generic = pprint.pformat(
        TITLE_GENERIC_UNIT_FAMILIES, width=88, sort_dicts=False
    )
    rows = pprint.pformat(authority, width=100, sort_dicts=False)
    ending_rows = pprint.pformat(
        output_label_endings, width=100, sort_dicts=False
    )
    removal_event_rows = pprint.pformat(
        currency_default_removal_events, width=100, sort_dicts=False
    )
    removed_rows = pprint.pformat(
        currency_default_removed_fields, width=100, sort_dicts=False
    )
    return f'''"""Frozen Amendment-10 field-title/header semantic authority.

Generated only after enumerating the conservative complete-description
title/header candidate superdomain of all 89,599 lawful field descriptions.
``TITLE_START_AUTHORITY`` supplies one contextual adjudication for every
independently discovered candidate. Context is the SHA-256 of the complete
raw description plus the exact description-relative UTF-8 byte span. Unknown
matches fail closed.
"""

from __future__ import annotations

# The generated authority relations are compact data literals.  Black's
# expanded form adds more than a million source lines without changing data.
# fmt: off
TITLE_LITERAL_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = {literal}

# Closed case-insensitive ASCII-boundary token/compound grammar.  Candidate
# spans are nevertheless true UTF-8 byte offsets in the raw description.
TITLE_GENERIC_UNIT_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = {generic}

# Complete mechanically label-shaped full-body ending adjudication.
# (interview_wave, raw_field_id, exact_physical_line, family, spelling,
#  qualifies_as_output_label, reason)
OUTPUT_LABEL_ENDING_ADJUDICATION: tuple[
    tuple[int, str, str, str, str, bool, str], ...
] = {ending_rows}

# Complete 209-event relation in denominator-then-candidate order.
# (interview_wave, raw_field_id, rejected_currency_default_branch)
CURRENCY_DEFAULT_REMOVAL_EVENTS: tuple[tuple[int, str, str], ...] = {removal_event_rows}

# Denominator-ordered unique-field projection of the 209 title starts removed
# by the six no-currency default-rejection branches.
CURRENCY_DEFAULT_REMOVED_FIELD_PROJECTION: tuple[tuple[int, str], ...] = {removed_rows}

# (description_sha256, bounded_context_header, family, description_start_byte,
#  description_end_byte, spelling,
#  typed_value_unit, disposition, reason, witness_wave, witness_field)
TITLE_START_AUTHORITY: tuple[
    tuple[str, str, str, int, int, str, str | None, str, str, int, str], ...
] = {rows}
# fmt: on
'''


def _rebuild_segment_authority(
    rows: Iterable[dict[str, Any]],
    decisions: dict[
        tuple[str, str, int, int, str], tuple[str | None, str, str]
    ],
) -> tuple[tuple[tuple[str, str], ...], dict[str, Any]]:
    baseline_source = _git_source(BASELINE_COMMIT, PREDICATE_MODULE)
    baseline = _literal_assignment(baseline_source, "SEGMENT_START_AUTHORITY")
    if canonical_sha256(baseline) != BASELINE_SEGMENT_SHA256:
        raise ValueError(
            "pre-title baseline segment authority identity changed"
        )
    baseline_map = dict(baseline)
    desired: dict[tuple[str, int], set[str]] = defaultdict(set)
    overlay_counts: Counter[tuple[str, str]] = Counter()
    raw_overlay_counts: Counter[tuple[str, str, str]] = Counter()
    preserved_title_defeat_fields: set[tuple[int, str]] = set()
    preserved_title_defeat_contexts: set[str] = set()
    title_start_collision_counts: Counter[tuple[str, str, str]] = Counter()
    title_start_collision_fields: set[tuple[int, str]] = set()

    for row in rows:
        description = row["source_description"]
        sha = hashlib.sha256(description.encode("utf-8")).hexdigest()
        text = normalize_description(description)
        absolute_tags: dict[int, str] = {}
        for family, start, end, spelling in title_header_candidates(
            description
        ):
            unit, disposition, _reason = decisions[
                (sha, family, start, end, spelling)
            ]
            offset = _normalized_title_start(description, start)
            while offset > 0 and text[offset - 1] != " ":
                offset -= 1
            tag = (
                "W"
                if disposition == "whole_domain_denotation"
                and unit is not None
                else "N"
            )
            previous = absolute_tags.get(offset)
            if previous is None:
                absolute_tags[offset] = tag
            else:
                merged = _merge_title_start_tag(previous, tag)
                absolute_tags[offset] = merged
                if previous != tag:
                    title_start_collision_counts[(previous, tag, merged)] += 1
                    title_start_collision_fields.add(
                        (row["interview_wave"], row["raw_field_id"])
                    )

        for _ordinal, absolute, segment in _normalized_segments(text):
            if segment not in baseline_map:
                raise ValueError(
                    f"segment absent from clean baseline: {segment!r}"
                )
            starts = _word_start_offsets(segment)
            for word_ordinal, relative in enumerate(starts):
                baseline_tag = baseline_map[segment][word_ordinal]
                absolute_start = absolute + relative
                tag = _merge_title_start_tag(
                    baseline_tag, absolute_tags.get(absolute_start)
                )
                desired[(segment, word_ordinal)].add(tag)
                if absolute_start in absolute_tags:
                    raw_title_tag = absolute_tags[absolute_start]
                    overlay_counts[(baseline_tag, tag)] += 1
                    raw_overlay_counts[(baseline_tag, raw_title_tag, tag)] += 1
                    if (baseline_tag, raw_title_tag, tag) == (
                        "W",
                        "N",
                        "W",
                    ):
                        preserved_title_defeat_fields.add(
                            (row["interview_wave"], row["raw_field_id"])
                        )
                        preserved_title_defeat_contexts.add(sha)

    rebuilt: list[tuple[str, str]] = []
    for segment, baseline_vector in baseline:
        vector = list(baseline_vector)
        for word_ordinal in range(len(vector)):
            tags = desired.get((segment, word_ordinal), {vector[word_ordinal]})
            if len(tags) == 1:
                vector[word_ordinal] = next(iter(tags))
        rebuilt.append((segment, "".join(vector)))
    frozen = tuple(rebuilt)
    collisions = [
        {
            "segment": segment,
            "word_ordinal": word_ordinal,
            "effective_tags": sorted(tags),
        }
        for (segment, word_ordinal), tags in sorted(desired.items())
        if len(tags) > 1
    ]
    preserved_title_defeat_field_digest = hashlib.sha256(
        "".join(
            f"{wave}\t{field}\n"
            for wave, field in sorted(preserved_title_defeat_fields)
        ).encode("utf-8")
    ).hexdigest()
    preserved_title_defeat_context_digest = hashlib.sha256(
        "".join(
            f"{context}\n"
            for context in sorted(preserved_title_defeat_contexts)
        ).encode("utf-8")
    ).hexdigest()
    demotion_count = sum(
        count
        for (baseline_tag, _raw_title_tag, effective_tag), count in (
            raw_overlay_counts.items()
        )
        if baseline_tag == "W" and effective_tag == "N"
    )
    stats = {
        "context_varying_segment_start_count": len(collisions),
        "context_varying_segment_starts": collisions,
        "changed_segment_vector_count": sum(
            old_vector != new_vector
            for (_old_segment, old_vector), (_new_segment, new_vector) in zip(
                baseline, frozen, strict=True
            )
        ),
        "title_overlay_baseline_to_effective_counts": [
            {
                "baseline_tag": baseline_tag,
                "effective_tag": effective_tag,
                "occurrence_count": count,
            }
            for (baseline_tag, effective_tag), count in sorted(
                overlay_counts.items()
            )
        ],
        "title_overlay_baseline_raw_to_effective_counts": [
            {
                "baseline_tag": baseline_tag,
                "raw_title_tag": raw_title_tag,
                "effective_tag": effective_tag,
                "occurrence_count": count,
            }
            for (
                baseline_tag,
                raw_title_tag,
                effective_tag,
            ), count in sorted(raw_overlay_counts.items())
        ],
        "title_overlay_baseline_whole_to_effective_defeat_demotion_count": (
            demotion_count
        ),
        "title_defeat_over_baseline_whole_preserved_occurrence_count": (
            raw_overlay_counts[("W", "N", "W")]
        ),
        "title_defeat_over_baseline_whole_preserved_field_keys": sorted(
            preserved_title_defeat_fields
        ),
        "title_defeat_over_baseline_whole_preserved_field_key_sha256": (
            preserved_title_defeat_field_digest
        ),
        "title_defeat_over_baseline_whole_preserved_context_count": len(
            preserved_title_defeat_contexts
        ),
        "title_defeat_over_baseline_whole_preserved_context_sha256": (
            preserved_title_defeat_context_digest
        ),
        "shared_normalized_title_start_counts": [
            {
                "previous_tag": previous,
                "next_tag": next_tag,
                "effective_tag": effective,
                "occurrence_count": count,
            }
            for (previous, next_tag, effective), count in sorted(
                title_start_collision_counts.items()
            )
        ],
        "shared_normalized_title_start_field_keys": sorted(
            title_start_collision_fields
        ),
    }
    expected_preserved_title_defeat_fields = {
        *((1994, f"ER{field}") for field in range(3062, 3074)),
        (1997, "ER12067"),
        (1997, "ER12069"),
        (1997, "ER12073"),
        (1997, "ER12075"),
        (1997, "ER12077"),
        (1997, "ER12079"),
        (1997, "ER12082"),
    }
    if (
        dict(raw_overlay_counts)
        != {
            ("D", "N", "N"): 72_025,
            ("D", "W", "W"): 8_203,
            ("W", "N", "W"): 19,
        }
        or demotion_count != 0
        or preserved_title_defeat_fields
        != expected_preserved_title_defeat_fields
        or preserved_title_defeat_field_digest
        != "c6311b97636e71626967c0946ecc9b45b37fe843047d9eec642acd5e6f3beebf"
        or len(preserved_title_defeat_contexts) != 19
        or preserved_title_defeat_context_digest
        != "dc8df507698bac0c85d2c9837490a6b14d99e583ebdfa14aa62493be2c6f628c"
    ):
        raise ValueError(
            "baseline/raw-title/effective overlay partition changed: "
            f"{raw_overlay_counts!r} demotions={demotion_count} "
            f"fields={preserved_title_defeat_fields!r} "
            f"field_sha={preserved_title_defeat_field_digest} "
            f"contexts={len(preserved_title_defeat_contexts)} "
            f"context_sha={preserved_title_defeat_context_digest}"
        )
    if dict(title_start_collision_counts) != {
        ("N", "W", "W"): 2,
        ("W", "N", "W"): 4,
    } or title_start_collision_fields != {
        (1989, "V16821"),
        (1989, "V17140"),
        (2003, "ER23274"),
        (2007, "ER40408"),
        (2009, "ER46381"),
        (2011, "ER51742"),
    }:
        raise ValueError(
            "shared normalized title-start partition changed: "
            f"{title_start_collision_counts!r} "
            f"{title_start_collision_fields!r}"
        )
    return frozen, stats


def _replace_segment_authority(
    rebuilt: tuple[tuple[str, str], ...], context_varying_count: int
) -> None:
    # Use the last committed, Black-formatted relation only as a textual
    # template.  The values still come exclusively from the clean baseline
    # rebuild above.  Replacing just each vector literal keeps the semantic
    # diff reviewable instead of reflowing all 59,445 unchanged segment rows.
    source = _git_source(OLD_TITLE_COMMIT, PREDICATE_MODULE)
    tree = ast.parse(source)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "SEGMENT_START_AUTHORITY"
    )
    assert isinstance(assignment.value, ast.Tuple)
    template_rows = assignment.value.elts
    if len(template_rows) != len(rebuilt):
        raise ValueError("segment template row count changed")
    line_starts = [0]
    for line in source.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))
    replacements: list[tuple[int, int, str]] = []
    for node, (segment, vector) in zip(template_rows, rebuilt, strict=True):
        assert isinstance(node, ast.Tuple) and len(node.elts) == 2
        template_segment = ast.literal_eval(node.elts[0])
        if template_segment != segment:
            raise ValueError("segment template order changed")
        vector_node = node.elts[1]
        assert isinstance(vector_node, ast.Constant)
        if vector_node.value == vector:
            continue
        start = line_starts[vector_node.lineno - 1] + vector_node.col_offset
        end = (
            line_starts[vector_node.end_lineno - 1]
            + vector_node.end_col_offset
        )
        replacements.append((start, end, json.dumps(vector)))
    for start, end, replacement in reversed(replacements):
        source = source[:start] + replacement + source[end:]
    old_overlay_text = (
        "The separate title authority supplies the one\n"
        "field-context-dependent overlay whose segment also occurs outside a title."
    )
    new_overlay_text = (
        f"The separate title authority supplies the {context_varying_count}\n"
        "field-context-dependent segment/start overlays whose effective title tag\n"
        "differs across source contexts."
    )
    if source.count(old_overlay_text) != 1:
        raise ValueError("predicate template overlay description changed")
    source = source.replace(old_overlay_text, new_overlay_text)
    PREDICATE_MODULE.write_text(source)


def _iter_rows(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_text(path: Path, content: str) -> None:
    """Publish one complete text artifact without exposing a partial file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-input",
        type=Path,
        default=Path("/private/tmp/amend10-raw-input.jsonl"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("/private/tmp/amendment10-title-audit.json"),
    )
    parser.add_argument(
        "--candidate-table",
        type=Path,
        default=Path("/private/tmp/amendment10-title-candidate-table.jsonl"),
        help="row-complete audit ledger written only with --audit-only",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="validate and rebuild in memory without changing authority modules",
    )
    args = parser.parse_args()

    candidate_table_stage: Path | None = None
    candidate_table_stream = None
    if args.audit_only:
        args.candidate_table.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=args.candidate_table.parent,
            prefix=f".{args.candidate_table.name}.",
            suffix=".tmp",
        )
        candidate_table_stage = Path(temporary_name)
        candidate_table_stream = os.fdopen(descriptor, "w")

    old_by_sha: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for old in _old_authority():
        old_by_sha[old[0]].append(old)

    authority: list[tuple[Any, ...]] = []
    output_label_endings: list[tuple[Any, ...]] = []
    currency_default_removals: list[tuple[int, str, str]] = []
    decisions: dict[
        tuple[str, str, int, int, str], tuple[str | None, str, str]
    ] = {}
    occurrence_counts: Counter[tuple[str, str | None, str, str]] = Counter()
    context_counts: Counter[tuple[str, str | None, str, str]] = Counter()
    baseline_candidate_occurrences = 0
    baseline_candidate_fields = 0
    first_question_candidate_occurrences = 0
    first_question_candidate_fields: set[tuple[int, str]] = set()
    first_question_candidate_families: Counter[str] = Counter()
    first_question_dispositions: Counter[str] = Counter()
    first_question_positive_reasons: Counter[str] = Counter()
    first_question_positive_fields: set[tuple[int, str]] = set()
    later_question_candidate_occurrences = 0
    later_question_candidate_fields: set[tuple[int, str]] = set()
    later_question_candidate_families: Counter[str] = Counter()
    later_question_dispositions: Counter[str] = Counter()
    later_question_positive_reasons: Counter[str] = Counter()
    later_question_positive_fields: set[tuple[int, str]] = set()
    question_line_suffix_candidate_occurrences = 0
    question_line_suffix_candidate_fields: set[tuple[int, str]] = set()
    question_line_suffix_candidate_families: Counter[str] = Counter()
    question_line_suffix_dispositions: Counter[str] = Counter()
    question_line_suffix_positive_reasons: Counter[str] = Counter()
    question_line_suffix_positive_fields: set[tuple[int, str]] = set()
    question_continuation_candidate_occurrences = 0
    question_continuation_candidate_fields: set[tuple[int, str]] = set()
    question_continuation_candidate_families: Counter[str] = Counter()
    question_continuation_dispositions: Counter[str] = Counter()
    full_body_candidate_occurrences = 0
    full_body_candidate_fields: set[tuple[int, str]] = set()
    full_body_candidate_families: Counter[str] = Counter()
    full_body_dispositions: Counter[str] = Counter()
    full_body_positive_reasons: Counter[str] = Counter()
    full_body_negative_reasons: Counter[str] = Counter()
    full_body_positive_fields: set[tuple[int, str]] = set()
    production_cross_lf_candidate_occurrences = 0
    production_cross_lf_candidate_fields: set[tuple[int, str]] = set()
    production_cross_lf_dispositions: Counter[str] = Counter()
    production_cross_lf_positive_fields: set[tuple[int, str]] = set()
    cross_lf_raw_compound_occurrences = 0
    cross_lf_compound_occurrences = 0
    cross_lf_compound_fields: set[tuple[int, str]] = set()
    cross_lf_compound_families: Counter[str] = Counter()
    cross_lf_compound_boundaries: Counter[str] = Counter()
    cross_lf_compound_dispositions: Counter[str] = Counter()
    cross_lf_compound_groundings: Counter[str] = Counter()
    cross_lf_compound_positive_fields: set[tuple[int, str]] = set()
    cross_lf_primary_delegation_fields: set[tuple[int, str]] = set()
    cross_lf_reference_defeat_fields: set[tuple[int, str]] = set()
    cross_lf_hours_per_week_component_occurrences = 0
    cross_lf_hours_per_week_component_reasons: Counter[str] = Counter()
    singleton_delta_candidate_occurrences = 0
    singleton_delta_candidate_fields: set[tuple[int, str]] = set()
    singleton_delta_candidate_families: Counter[str] = Counter()
    singleton_delta_dispositions: Counter[str] = Counter()
    singleton_delta_positive_reasons: Counter[str] = Counter()
    singleton_delta_positive_fields: set[tuple[int, str]] = set()
    matched_fields = 0
    candidate_occurrences = 0
    positive_candidate_occurrences = 0
    positive_fields = 0
    continuation_headers = 0
    continuation_output_labels: Counter[str] = Counter()
    continuation_line2_candidate_occurrences = 0
    compiled_continuation_without_line1_unit: list[list[Any]] = []
    paid_extra_hours_yes_no_fields = 0
    paid_extra_hours_yes_no_candidates = 0
    paid_extra_hours_yes_no_field_keys: set[tuple[int, str]] = set()
    paid_extra_hours_yes_no_contexts: set[str] = set()
    paid_extra_hours_yes_no_candidate_decisions: Counter[
        tuple[str, str, str | None, str, str]
    ] = Counter()
    paid_extra_hours_yes_no_transition_families: Counter[tuple[str, str]] = (
        Counter()
    )
    structural_selector_occurrences = 0
    structural_selector_fields = 0
    structural_selector_kinds: Counter[str] = Counter()
    structural_selector_label_lines: Counter[int] = Counter()
    structural_selector_line8_keys: list[list[Any]] = []
    singleton_direct_occurrences = 0
    singleton_direct_fields: set[tuple[int, str]] = set()
    singleton_nested_response_occurrences = 0
    singleton_nested_response_fields: set[tuple[int, str]] = set()
    singleton_unit_signatures: Counter[tuple[str, str]] = Counter()
    singleton_unit_fields: set[tuple[int, str]] = set()
    singleton_unit_counts: Counter[str] = Counter()
    singleton_response_counts: Counter[str] = Counter()
    singleton_nonsemantic_direct_occurrences = 0
    food_body_code_occurrences = 0
    food_body_code_fields: set[tuple[int, str]] = set()
    body_instruction_occurrences = 0
    body_instruction_fields: set[tuple[int, str]] = set()
    editorial_note_occurrences = 0
    editorial_note_fields: set[tuple[int, str]] = set()
    separator_next_line_occurrences = 0
    separator_next_line_fields: set[tuple[int, str]] = set()
    header_physical_line_counts: Counter[int] = Counter()
    external_unit_selector_counts: Counter[str] = Counter()
    external_unit_selector_lines: Counter[int] = Counter()
    external_unit_selector_fields: set[tuple[int, str]] = set()
    external_unit_selector_contained = 0
    raw_physical_unit_selector_counts: Counter[str] = Counter()
    raw_physical_unit_selector_fields: set[tuple[int, str]] = set()
    raw_physical_unit_selector_contained = 0
    raw_response_selector_counts: Counter[str] = Counter()
    raw_response_selector_lines: Counter[tuple[str, int]] = Counter()
    quantity_selector_counts: Counter[str] = Counter()
    unique_unit_selector_counts: Counter[str] = Counter()
    categorical_hour_selector_count = 0
    nonterminal_semantic_components: Counter[str] = Counter()
    semantic_component_dedup_regressions: dict[str, int] = {}
    stable_calendar_contexts: dict[str, set[str]] = defaultdict(set)
    stable_calendar_fields: Counter[str] = Counter()
    stable_calendar_shas: set[str] = set()
    age_year_selector_fields = 0
    age_year_selector_contexts: set[str] = set()
    legacy_age_year_selector_fields = 0
    legacy_age_year_selector_contexts: set[str] = set()
    overtime_amount_fields = 0
    overtime_time_unit_fields = 0
    overtime_candidate_decisions: Counter[
        tuple[str, str, str, str | None, str, str]
    ] = Counter()
    dollars_worth_amount_fields = 0
    dollars_worth_time_unit_fields = 0
    dollars_worth_contexts: set[str] = set()
    dollars_worth_body_grounded_fields = 0
    dollars_worth_candidate_decisions: Counter[
        tuple[str, str, str, str | None, str, str]
    ] = Counter()
    dollars_worth_field_keys: dict[str, set[tuple[int, str]]] = defaultdict(
        set
    )
    dollars_worth_full_body_fields: set[tuple[int, str]] = set()
    pension_selector_fields: Counter[str] = Counter()
    pension_selector_contexts: dict[str, set[str]] = defaultdict(set)
    pension_candidate_decisions: Counter[
        tuple[str, str, str, str | None, str, str]
    ] = Counter()
    experience_fields = 0
    experience_contexts: set[str] = set()
    experience_contexts_by_unit: dict[str, set[str]] = defaultdict(set)
    experience_units: Counter[str] = Counter()
    experience_nonselector_fields = 0
    experience_nonselector_contexts: set[str] = set()
    experience_nonselector_context_fields: dict[str, set[tuple[int, str]]] = (
        defaultdict(set)
    )
    experience_nonselector_candidate_decisions: Counter[
        tuple[str, str, str | None, str, str]
    ] = Counter()
    typical_week_time_use_fields = 0
    typical_week_time_use_contexts: set[str] = set()
    typical_week_time_use_people: Counter[str] = Counter()
    typical_week_candidate_decisions: Counter[
        tuple[str, str, str | None, str, str]
    ] = Counter()
    typical_week_reference_without_article_fields: set[tuple[int, str]] = set()
    highest_college_year_fields = 0
    highest_college_year_contexts: set[str] = set()
    highest_college_year_body_grounded_fields = 0
    highest_college_year_candidate_decisions: Counter[
        tuple[str, str, str | None, str, str]
    ] = Counter()
    highest_college_year_full_body_fields: set[tuple[int, str]] = set()
    school_years_outside_us_fields = 0
    school_years_outside_us_contexts: set[str] = set()
    education_title_negative_controls: Counter[str] = Counter()
    last_year_miles_fields = 0
    last_year_miles_candidate_decisions: dict[
        str, tuple[str | None, str, str]
    ] = {}
    number_of_times_selector_fields = 0
    year_to_year_count_fields = 0
    er47619_fields = 0
    er47619_week_decisions: list[tuple[str | None, str, str]] = []
    multi_positive_fields = 0
    multi_positive_field_keys: set[tuple[int, str]] = set()
    multi_positive_multiplicities: Counter[int] = Counter()
    multi_positive_units: Counter[str] = Counter()
    multi_positive_reasons: Counter[str] = Counter()
    input_relation_hasher = hashlib.sha256()
    input_relation_hasher.update(b"[")
    field_count = 0
    denominator_field_keys: list[tuple[int, str]] = []

    for row in _iter_rows(args.raw_input):
        field_count += 1
        denominator_field_keys.append(
            (row["interview_wave"], row["raw_field_id"])
        )
        if field_count > 1:
            input_relation_hasher.update(b",")
        input_relation_hasher.update(
            json.dumps(
                [
                    row["interview_wave"],
                    row["raw_field_id"],
                    row["derivation_status"],
                    row["resolution_reason"],
                    row["source_description"],
                ],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
        )
        description = row["source_description"]
        sha = hashlib.sha256(description.encode("utf-8")).hexdigest()
        header = _raw_title(description)
        candidates = title_header_candidates(description)
        raw_lines = description.split("\n")
        field_key = (row["interview_wave"], row["raw_field_id"])
        selector_spans = _title_selector_spans(description)
        semantic_selector_components = _header_selector_occurrences(header)
        semantic_component_keys = {
            (start, end, component)
            for _kind, start, end, component, _label, _terminal in (
                semantic_selector_components
            )
        }
        if len(semantic_component_keys) != len(semantic_selector_components):
            raise ValueError(
                f"duplicate semantic selector component: {field_key}"
            )
        expected_dedup_component = SEMANTIC_COMPONENT_DEDUP_REGRESSIONS.get(
            row["raw_field_id"]
        )
        if expected_dedup_component is not None:
            component_count = sum(
                normalize_description(component).upper()
                == expected_dedup_component
                for _kind, _start, _end, component, _label, _terminal in (
                    semantic_selector_components
                )
            )
            semantic_component_dedup_regressions[row["raw_field_id"]] = (
                component_count
            )
            if component_count != 1:
                raise ValueError(
                    f"semantic selector component dedup changed: {field_key} "
                    f"{expected_dedup_component!r}={component_count}"
                )
        structural_selector_occurrences += len(selector_spans)
        structural_selector_fields += bool(selector_spans)
        header_physical_line_counts[header.count("\n") + 1] += 1
        for kind, start, _end, _label in selector_spans:
            label_line = description.count("\n", 0, start) + 1
            structural_selector_kinds[kind] += 1
            structural_selector_label_lines[label_line] += 1
            if label_line == 8:
                structural_selector_line8_keys.append(
                    [row["interview_wave"], row["raw_field_id"]]
                )

        for kind, start, end, label in selector_spans:
            if kind not in {"single_hyphen", "single_hyphen_next_line"}:
                continue
            nested = kind == "single_hyphen" and any(
                other_kind not in {"single_hyphen", "single_hyphen_next_line"}
                and other_start <= start
                and end <= other_end
                and (other_start, other_end) != (start, end)
                for other_kind, other_start, other_end, _other_label in (
                    selector_spans
                )
            )
            response_family = _response_selector_family(label)
            output_unit = _output_label_unit(label)
            if nested:
                singleton_nested_response_occurrences += 1
                singleton_nested_response_fields.add(field_key)
                if response_family != "TIME UNIT" or output_unit is not None:
                    raise ValueError(
                        f"unexpected nested singleton selector: "
                        f"{field_key} {label!r}"
                    )
                continue

            singleton_direct_occurrences += 1
            singleton_direct_fields.add(field_key)
            if output_unit is not None:
                signature = normalize_description(label).upper()
                singleton_unit_signatures[(kind, signature)] += 1
                singleton_unit_fields.add(field_key)
                singleton_unit_counts[output_unit] += 1
            elif response_family is not None:
                singleton_response_counts[response_family] += 1
            else:
                singleton_nonsemantic_direct_occurrences += 1

        line_starts: list[int] = []
        line_cursor = 0
        for raw_line in raw_lines:
            line_starts.append(line_cursor)
            line_cursor += len(raw_line) + 1
        for line_index, raw_line in enumerate(raw_lines):
            line_start = line_starts[line_index]
            line_end = line_start + len(raw_line)
            if _title_body_code_row(raw_lines[0], raw_line):
                food_body_code_occurrences += 1
                food_body_code_fields.add(field_key)
                if any(
                    line_start <= start < line_end
                    for _kind, start, _end, _label in selector_spans
                ):
                    raise ValueError(
                        f"body code row admitted as selector: {field_key} "
                        f"line {line_index + 1}"
                    )
            if _title_body_instruction_row(raw_line):
                body_instruction_occurrences += 1
                body_instruction_fields.add(field_key)
                if any(
                    line_start <= start < line_end
                    for _kind, start, _end, _label in selector_spans
                ):
                    raise ValueError(
                        f"body instruction admitted as selector: {field_key} "
                        f"line {line_index + 1}"
                    )
            if _title_editorial_note_row(raw_line):
                editorial_note_occurrences += 1
                editorial_note_fields.add(field_key)
                if any(
                    line_start <= start < line_end
                    for _kind, start, _end, _label in selector_spans
                ):
                    raise ValueError(
                        f"editorial note admitted as selector: {field_key} "
                        f"line {line_index + 1}"
                    )
            if (
                line_index
                and re.fullmatch(r"-+", raw_lines[line_index - 1])
                and raw_line.strip()
                and (
                    raw_line.strip()[0].isupper()
                    or raw_line.strip()[0].isdigit()
                    or raw_line.strip()[0] in "[("
                )
            ):
                separator_next_line_occurrences += 1
                separator_next_line_fields.add(field_key)
                if any(
                    start == line_start
                    for _kind, start, _end, _label in selector_spans
                ):
                    raise ValueError(
                        f"separator introduced selector: {field_key} "
                        f"line {line_index + 1}"
                    )

        for (
            _kind,
            component_start,
            _end,
            component,
            _label,
            terminal,
        ) in semantic_selector_components:
            component_char_start = _char_offset(header, component_start)
            component_line = header.count("\n", 0, component_char_start) + 1
            if unit := _unique_physical_unit(component):
                unique_unit_selector_counts[unit] += 1
                raw_physical_unit_selector_counts[unit] += 1
                raw_physical_unit_selector_fields.add(field_key)
                raw_physical_unit_selector_contained += 1
                if component_line >= 2:
                    external_unit_selector_counts[unit] += 1
                    external_unit_selector_lines[component_line] += 1
                    external_unit_selector_fields.add(field_key)
                    external_unit_selector_contained += 1
            if unit := _output_label_unit(component):
                quantity_selector_counts[unit] += 1
            if response_family := _response_selector_family(component):
                raw_response_selector_counts[response_family] += 1
                raw_response_selector_lines[
                    (response_family, component_line)
                ] += 1
            if _categorical_hour_selector(component):
                categorical_hour_selector_count += 1
            if not terminal:
                response_selector = _response_selector_component(component)
                cleaned = normalize_description(component).upper()
                if response_selector is not None:
                    component_family = response_selector.split(" FOR ", 1)[0]
                elif re.match(r"^MONTH(?:\s|$)", cleaned):
                    component_family = "MONTH"
                elif re.match(r"^YEAR(?:\s|$)", cleaned):
                    component_family = "YEAR"
                else:
                    raise ValueError(
                        f"unexpected nonterminal semantic component: "
                        f"{field_key} {component!r}"
                    )
                nonterminal_semantic_components[component_family] += 1
        if len(raw_lines) > 1 and raw_lines[0].endswith("--"):
            continuation_headers += 1
            continuation_unit = _continuation_output_label_unit(raw_lines[1])
            if continuation_unit is not None:
                label = raw_lines[1].strip().upper()
                if label.startswith("MONTH"):
                    label_family = "MONTHS" if label == "MONTHS" else "MONTH"
                elif label.startswith("YEAR"):
                    label_family = "YEARS" if label == "YEARS" else "YEAR"
                elif label.startswith("PERCENT"):
                    label_family = "PERCENT"
                else:
                    label_family = label
                continuation_output_labels[label_family] += 1
                first_line_candidates = title_header_candidates(raw_lines[0])
                if row["derivation_status"].startswith(
                    "compiled_source_numeric_grammar"
                ) and not any(
                    candidate[0] in FAMILY_UNIT
                    for candidate in first_line_candidates
                ):
                    compiled_continuation_without_line1_unit.append(
                        [row["interview_wave"], row["raw_field_id"]]
                    )
            line2_start = len(raw_lines[0].encode("utf-8")) + 1
            continuation_line2_candidate_occurrences += sum(
                candidate[1] >= line2_start for candidate in candidates
            )
        if candidates:
            matched_fields += 1
        candidate_occurrences += len(candidates)
        adjudications = _adjudicate_context(
            row,
            candidates,
            old_by_sha,
            currency_default_removals,
        )
        (
            baseline_candidates,
            first_question_delta,
            singleton_delta,
            later_question_delta,
            question_line_suffix_delta,
            question_continuation_delta,
            full_body_delta,
        ) = _round3_candidate_transition(description)
        for candidate in candidates:
            if candidate not in full_body_delta:
                continue
            ending = _standalone_output_label_ending(description, candidate)
            if ending is None:
                continue
            line, qualifies, reason = ending
            output_label_endings.append(
                (
                    row["interview_wave"],
                    row["raw_field_id"],
                    line,
                    candidate[0],
                    candidate[3],
                    qualifies,
                    reason,
                )
            )
        if len(candidates) != (
            len(baseline_candidates)
            + len(first_question_delta)
            + len(later_question_delta)
            + len(singleton_delta)
            + len(question_line_suffix_delta)
            + len(question_continuation_delta)
            + len(full_body_delta)
        ):
            raise ValueError(f"round-3 transition count changed: {field_key}")
        baseline_candidate_occurrences += len(baseline_candidates)
        baseline_candidate_fields += bool(baseline_candidates)
        decision_by_candidate = dict(
            zip(candidates, adjudications, strict=True)
        )
        raw_cross_lf, cross_lf_compounds = _cross_lf_compound_transition(
            description
        )
        cross_lf_raw_compound_occurrences += len(raw_cross_lf)
        for compound in cross_lf_compounds:
            cross_lf_compound_occurrences += 1
            cross_lf_compound_fields.add(field_key)
            cross_lf_compound_families[compound[0]] += 1
            boundary = (
                "bounded_header"
                if compound[2] <= len(header.encode("utf-8"))
                else "full_body"
            )
            cross_lf_compound_boundaries[boundary] += 1
            contained = [
                (candidate, decision)
                for candidate, decision in decision_by_candidate.items()
                if compound[1] <= candidate[1] and candidate[2] <= compound[2]
            ]
            exact = decision_by_candidate.get(compound)
            if exact is not None and exact[1] == "whole_domain_denotation":
                cross_lf_compound_dispositions["W"] += 1
                cross_lf_compound_groundings[
                    "exact_production_title_start"
                ] += 1
                cross_lf_compound_positive_fields.add(field_key)
            else:
                if contained and any(
                    decision[1] == "whole_domain_denotation"
                    for _candidate, decision in contained
                ):
                    raise ValueError(
                        "cross-LF compound contains a positive component: "
                        f"{field_key} {compound!r} {contained!r}"
                    )
                if contained:
                    cross_lf_compound_groundings[
                        "contained_production_starts_explicitly_defeated"
                    ] += 1
                else:
                    normalized = normalize_description(description)
                    normalized_start = _normalized_title_start(
                        description, compound[1]
                    )
                    primary_delegation = any(
                        offset <= normalized_start < offset + len(statement)
                        for offset, statement in _extract_statement_spans(
                            normalized
                        )
                    )
                    referenced_other_field = compound[
                        0
                    ] == "number_in_family_unit_marker" and bool(
                        re.search(
                            r"be receiving food stamps; therefore,? this "
                            r"number might not equal ?(?:V22405|ER\d+) "
                            r"\(Number in Family Unit\)\.",
                            normalized,
                        )
                    )
                    if primary_delegation:
                        cross_lf_compound_groundings[
                            "delegated_to_primary_statement_grammar"
                        ] += 1
                        cross_lf_primary_delegation_fields.add(field_key)
                    elif referenced_other_field:
                        cross_lf_compound_groundings[
                            "referenced_other_field_not_field_denotation"
                        ] += 1
                        cross_lf_reference_defeat_fields.add(field_key)
                    else:
                        raise ValueError(
                            "cross-LF compound lacks an exact N grounding: "
                            f"{field_key} {compound!r}"
                        )
                cross_lf_compound_dispositions["N"] += 1
            if compound[0] == "hours_per_week":
                if {candidate[0] for candidate, _decision in contained} != {
                    "nominal_hour_token",
                    "nominal_week_token",
                } or len(contained) != 2:
                    raise ValueError(
                        "cross-LF hours/week component partition changed: "
                        f"{field_key} {compound!r} {contained!r}"
                    )
                cross_lf_hours_per_week_component_occurrences += 2
                cross_lf_hours_per_week_component_reasons.update(
                    decision[2] for _candidate, decision in contained
                )
        for candidate, decision in decision_by_candidate.items():
            if "\n" not in candidate[3]:
                continue
            production_cross_lf_candidate_occurrences += 1
            production_cross_lf_candidate_fields.add(field_key)
            tag = "W" if decision[1] == "whole_domain_denotation" else "N"
            production_cross_lf_dispositions[tag] += 1
            if tag == "W":
                production_cross_lf_positive_fields.add(field_key)
        for candidate in first_question_delta:
            decision = decision_by_candidate[candidate]
            first_question_candidate_occurrences += 1
            first_question_candidate_fields.add(field_key)
            first_question_candidate_families[candidate[0]] += 1
            tag = "W" if decision[1] == "whole_domain_denotation" else "N"
            first_question_dispositions[tag] += 1
            if tag == "W":
                first_question_positive_reasons[decision[2]] += 1
                first_question_positive_fields.add(field_key)
        for candidate in later_question_delta:
            decision = decision_by_candidate[candidate]
            later_question_candidate_occurrences += 1
            later_question_candidate_fields.add(field_key)
            later_question_candidate_families[candidate[0]] += 1
            tag = "W" if decision[1] == "whole_domain_denotation" else "N"
            later_question_dispositions[tag] += 1
            if tag == "W":
                later_question_positive_reasons[decision[2]] += 1
                later_question_positive_fields.add(field_key)
        for candidate in singleton_delta:
            decision = decision_by_candidate[candidate]
            singleton_delta_candidate_occurrences += 1
            singleton_delta_candidate_fields.add(field_key)
            singleton_delta_candidate_families[candidate[0]] += 1
            tag = "W" if decision[1] == "whole_domain_denotation" else "N"
            singleton_delta_dispositions[tag] += 1
            if tag == "W":
                singleton_delta_positive_reasons[decision[2]] += 1
                singleton_delta_positive_fields.add(field_key)
        for candidate in question_line_suffix_delta:
            decision = decision_by_candidate[candidate]
            question_line_suffix_candidate_occurrences += 1
            question_line_suffix_candidate_fields.add(field_key)
            question_line_suffix_candidate_families[candidate[0]] += 1
            tag = "W" if decision[1] == "whole_domain_denotation" else "N"
            question_line_suffix_dispositions[tag] += 1
            if tag == "W":
                question_line_suffix_positive_reasons[decision[2]] += 1
                question_line_suffix_positive_fields.add(field_key)
        for candidate in question_continuation_delta:
            decision = decision_by_candidate[candidate]
            question_continuation_candidate_occurrences += 1
            question_continuation_candidate_fields.add(field_key)
            question_continuation_candidate_families[candidate[0]] += 1
            tag = "W" if decision[1] == "whole_domain_denotation" else "N"
            question_continuation_dispositions[tag] += 1
        for candidate in full_body_delta:
            decision = decision_by_candidate[candidate]
            full_body_candidate_occurrences += 1
            full_body_candidate_fields.add(field_key)
            full_body_candidate_families[candidate[0]] += 1
            tag = "W" if decision[1] == "whole_domain_denotation" else "N"
            full_body_dispositions[tag] += 1
            if tag == "W":
                full_body_positive_reasons[decision[2]] += 1
                full_body_positive_fields.add(field_key)
            else:
                full_body_negative_reasons[decision[2]] += 1
        if candidate_table_stream is not None:
            candidate_table_stream.write(
                json.dumps(
                    {
                        "field_key": [
                            row["interview_wave"],
                            row["raw_field_id"],
                        ],
                        "derivation_status": row["derivation_status"],
                        "resolution_reason": row["resolution_reason"],
                        "raw_candidate_domain": description,
                        "raw_candidate_domain_byte_count": len(
                            description.encode("utf-8")
                        ),
                        "raw_candidate_domain_sha256": sha,
                        "candidate_offsets": (
                            "zero-based UTF-8 byte offsets in "
                            "raw_candidate_domain"
                        ),
                        "bounded_context_header": header,
                        "bounded_context_header_sha256": hashlib.sha256(
                            header.encode("utf-8")
                        ).hexdigest(),
                        "candidate_count": len(candidates),
                        "candidates": [
                            {
                                "family": family,
                                "start_byte": start,
                                "end_byte": end,
                                "spelling": spelling,
                                "unit": decision[0],
                                "tag": (
                                    "W"
                                    if decision[1] == "whole_domain_denotation"
                                    else "N"
                                ),
                                "disposition": decision[1],
                                "reason": decision[2],
                            }
                            for (
                                family,
                                start,
                                end,
                                spelling,
                            ), decision in zip(
                                candidates, adjudications, strict=True
                            )
                        ],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                )
                + "\n"
            )
        for (
            _kind,
            start,
            end,
            component,
            _label,
            terminal,
        ) in _header_selector_occurrences(header):
            if terminal:
                continue
            output_unit = _output_label_unit(component)
            if output_unit is not None:
                matching = [
                    decision
                    for candidate, decision in zip(
                        candidates, adjudications, strict=True
                    )
                    if start <= candidate[1]
                    and candidate[2] <= end
                    and FAMILY_UNIT.get(candidate[0]) == output_unit
                ]
                if len(matching) != 1 or matching[0][1] == (
                    "whole_domain_denotation"
                ):
                    raise ValueError(
                        f"nonterminal coordinate selector changed: "
                        f"{field_key} {component!r} {matching!r}"
                    )
            elif _response_selector_component(component) is not None and any(
                disposition == "whole_domain_denotation"
                for _unit, disposition, _reason in adjudications
            ):
                raise ValueError(
                    f"nonterminal response selector failed to defeat title: "
                    f"{field_key} {component!r}"
                )

        legacy_header = _legacy_first_line_title(description)
        legacy_unit, _legacy_start, _legacy_end, legacy_label = (
            _legacy_output_label(legacy_header)
        )
        legacy_cleaned = normalize_description(legacy_label).upper()
        calendar_category: str | None = None
        if legacy_unit == "month" and not re.search(
            r"\bMONTHS\b", legacy_cleaned
        ):
            calendar_category = "selector_month"
        elif (
            legacy_unit == "year"
            and not re.search(r"\bYEARS\b", legacy_cleaned)
            and not re.search(r"\bAt what age\b", legacy_header, re.IGNORECASE)
        ):
            calendar_category = "selector_year"
        elif legacy_unit == "year" and re.search(
            r"\bAt what age\b", legacy_header, re.IGNORECASE
        ):
            legacy_age_year_selector_fields += 1
            legacy_age_year_selector_contexts.add(sha)

        if calendar_category is None:
            legacy_bytes = len(legacy_header.encode("utf-8"))
            direct_categories: set[str] = set()
            for candidate in candidates:
                if candidate[2] > legacy_bytes:
                    continue
                if (
                    candidate[0] == "number_of_years"
                    and "year-to-year changes" in legacy_header.lower()
                ):
                    direct_categories.add("year_to_year_change")
                elif _calendar_coordinate_candidate(legacy_header, candidate):
                    direct_categories.add(
                        f"direct_{FAMILY_UNIT[candidate[0]]}"
                    )
            if len(direct_categories) > 1:
                raise ValueError(
                    f"multiple legacy calendar categories: {field_key} "
                    f"{sorted(direct_categories)!r}"
                )
            if direct_categories:
                calendar_category = next(iter(direct_categories))
        if calendar_category is not None:
            stable_calendar_contexts[calendar_category].add(sha)
            stable_calendar_fields[calendar_category] += 1
            stable_calendar_shas.add(sha)

        if any(
            reason == "age_question_year_selector_names_duration_unit"
            and disposition == "whole_domain_denotation"
            for _unit, disposition, reason in adjudications
        ):
            age_year_selector_fields += 1
            age_year_selector_contexts.add(sha)

        response_selectors = _header_response_selectors(header)
        overtime_amount = _overtime_amount_is_explicit_hours(
            header, response_selectors
        )
        overtime_time_unit = bool(
            response_selectors == ("TIME UNIT",)
            and re.match(
                r"^(?:BC|DE)14[Bb]4\. How many hours did that overtime amount to\b",
                header,
            )
        )
        if overtime_amount or overtime_time_unit:
            overtime_category = "amount" if overtime_amount else "time_unit"
            overtime_candidate_decisions.update(
                (
                    overtime_category,
                    "full_body" if candidate in full_body_delta else "bounded",
                    candidate[0],
                    decision[0],
                    decision[1],
                    decision[2],
                )
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            )
            hour_rows = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "nominal_hour_token"
            ]
            count_rows = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "how_many_count_marker"
            ]
            if overtime_amount:
                overtime_amount_fields += 1
                positive_hour = (
                    "hour",
                    "whole_domain_denotation",
                    "how_many_directly_governs_unit_noun",
                )
                if not (
                    hour_rows.count(positive_hour) == 1
                    and all(
                        row == positive_hour
                        or row[1] != "whole_domain_denotation"
                        for row in hour_rows
                    )
                    and count_rows
                    and all(
                        row[1] != "whole_domain_denotation"
                        for row in count_rows
                    )
                ):
                    raise ValueError(
                        f"overtime AMOUNT adjudication changed: {field_key}"
                    )
            else:
                overtime_time_unit_fields += 1
                if any(
                    decision[1] == "whole_domain_denotation"
                    for decision in hour_rows + count_rows
                ):
                    raise ValueError(
                        f"overtime TIME UNIT became positive: {field_key}"
                    )

        dollars_worth_amount = _dollars_worth_amount_is_explicit_dollars(
            header, response_selectors
        )
        dollars_worth_time_unit = bool(
            response_selectors == ("TIME UNIT",)
            and (
                DOLLARS_WORTH_SELECTOR_HEAD.match(header)
                or normalize_description(header)
                in DOLLARS_WORTH_1992_COMPOSITE_HEADS
            )
        )
        if dollars_worth_amount or dollars_worth_time_unit:
            dollars_worth_category = (
                "amount" if dollars_worth_amount else "time_unit"
            )
            dollars_worth_contexts.add(sha)
            dollars_worth_field_keys[dollars_worth_category].add(field_key)
            dollars_worth_candidate_decisions.update(
                (
                    dollars_worth_category,
                    "full_body" if candidate in full_body_delta else "bounded",
                    candidate[0],
                    decision[0],
                    decision[1],
                    decision[2],
                )
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            )
            if any(candidate in full_body_delta for candidate in candidates):
                dollars_worth_full_body_fields.add(field_key)
            dollar_rows = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "nominal_dollar_token"
            ]
            count_rows = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "how_many_count_marker"
            ]
            if dollars_worth_amount:
                dollars_worth_amount_fields += 1
                dollars_worth_body_grounded_fields += _body_ground_units(
                    description
                ) == {"united_states_dollar"}
                positive_dollar = (
                    "united_states_dollar",
                    "whole_domain_denotation",
                    "dollars_worth_amount_title_denotation",
                )
                if (
                    dollar_rows.count(positive_dollar) != 1
                    or any(
                        decision != positive_dollar
                        and decision[1] == "whole_domain_denotation"
                        for decision in dollar_rows
                    )
                    or any(
                        decision[1] == "whole_domain_denotation"
                        for decision in count_rows
                    )
                ):
                    raise ValueError(
                        f"dollars-worth AMOUNT adjudication changed: "
                        f"{field_key} {dollar_rows!r} {count_rows!r}"
                    )
            else:
                dollars_worth_time_unit_fields += 1
                if any(
                    decision[1] == "whole_domain_denotation"
                    for decision in dollar_rows + count_rows
                ):
                    raise ValueError(
                        f"dollars-worth TIME UNIT became positive: {field_key}"
                    )

        if PENSION_ALTERNATIVE_FORMAT.search(normalize_description(header)):
            pension_amount = _pension_amount_is_explicit_dollars(
                header, response_selectors
            )
            pension_time_unit = bool(
                len(response_selectors) == 1
                and response_selectors[0].startswith("TIME UNIT")
            )
            pension_lump_sum = bool(
                len(response_selectors) == 1
                and response_selectors[0].startswith("LUMP SUM")
            )
            pension_percent = any(
                unit == "percent"
                and normalize_description(component)
                .upper()
                .startswith("PERCENT")
                for unit, _start, _end, component, _label in (
                    _header_output_labels(header)
                )
            )
            pension_categories = [
                category
                for category, present in (
                    ("amount", pension_amount),
                    ("time_unit", pension_time_unit),
                    ("percent", pension_percent),
                    ("lump_sum", pension_lump_sum),
                )
                if present
            ]
            if len(pension_categories) != 1:
                raise ValueError(
                    f"pension selector category changed: {field_key} "
                    f"{pension_categories!r} {response_selectors!r}"
                )
            pension_category = pension_categories[0]
            pension_selector_fields[pension_category] += 1
            pension_selector_contexts[pension_category].add(sha)
            pension_candidate_decisions.update(
                (
                    pension_category,
                    "full_body" if candidate in full_body_delta else "bounded",
                    candidate[0],
                    decision[0],
                    decision[1],
                    decision[2],
                )
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            )
            in_dollars_rows = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "in_dollars"
            ]
            positive_units = {
                unit
                for unit, disposition, _reason in adjudications
                if disposition == "whole_domain_denotation"
                and unit is not None
            }
            expected_positive_units = {
                "amount": {"united_states_dollar"},
                "time_unit": set(),
                "percent": {"percent"},
                "lump_sum": set(),
            }[pension_category]
            positive_in_dollars = (
                "united_states_dollar",
                "whole_domain_denotation",
                "pension_amount_arm_denotes_dollars",
            )
            if (
                positive_units != expected_positive_units
                or (
                    pension_category == "amount"
                    and (
                        in_dollars_rows.count(positive_in_dollars) != 1
                        or any(
                            decision != positive_in_dollars
                            and decision[1] == "whole_domain_denotation"
                            for decision in in_dollars_rows
                        )
                    )
                )
                or (
                    pension_category != "amount"
                    and any(
                        decision[1] == "whole_domain_denotation"
                        for decision in in_dollars_rows
                    )
                )
            ):
                raise ValueError(
                    f"pension selector adjudication changed: {field_key} "
                    f"{pension_category} {in_dollars_rows!r} "
                    f"{positive_units!r}"
                )

        if re.search(
            r"\bHow many years(?:'| of) experience\b", header, re.IGNORECASE
        ):
            positive_units = {
                unit
                for unit, disposition, _reason in adjudications
                if disposition == "whole_domain_denotation"
                and unit is not None
            }
            selector_units = {
                unit
                for unit, _start, _end, _component, _label in (
                    _header_output_labels(header)
                )
            }
            if selector_units:
                if (
                    len(selector_units) != 1
                    or positive_units != selector_units
                ):
                    raise ValueError(
                        f"experience selector conflict: {field_key} "
                        f"selectors={selector_units!r}, "
                        f"positives={positive_units!r}"
                    )
                experience_fields += 1
                experience_contexts.add(sha)
                experience_unit = next(iter(positive_units))
                experience_contexts_by_unit[experience_unit].add(sha)
                experience_units[experience_unit] += 1
            else:
                experience_nonselector_fields += 1
                experience_nonselector_contexts.add(sha)
                experience_nonselector_context_fields[sha].add(field_key)
                experience_nonselector_candidate_decisions.update(
                    (
                        (
                            "full_body"
                            if candidate in full_body_delta
                            else "bounded"
                        ),
                        candidate[0],
                        decision[0],
                        decision[1],
                        decision[2],
                    )
                    for candidate, decision in zip(
                        candidates, adjudications, strict=True
                    )
                )
                if positive_units or _body_ground_units(description) != {
                    "month"
                }:
                    raise ValueError(
                        f"experience body defeat changed: {field_key} "
                        f"positives={positive_units!r}, "
                        f"body={_body_ground_units(description)!r}"
                    )

        if HIGHEST_COLLEGE_YEAR_TITLE.fullmatch(header):
            highest_college_year_fields += 1
            highest_college_year_contexts.add(sha)
            body_units = _body_ground_units(description)
            highest_college_year_body_grounded_fields += body_units == {"year"}
            candidate_rows = [
                (
                    "full_body" if candidate in full_body_delta else "bounded",
                    candidate[0],
                    decision[0],
                    decision[1],
                    decision[2],
                )
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            ]
            highest_college_year_candidate_decisions.update(candidate_rows)
            full_body_rows = [
                row for row in candidate_rows if row[0] == "full_body"
            ]
            if full_body_rows:
                highest_college_year_full_body_fields.add(field_key)
            if (
                [row for row in candidate_rows if row[0] == "bounded"]
                != [
                    (
                        "bounded",
                        "nominal_year_token",
                        "year",
                        "whole_domain_denotation",
                        "highest_college_year_title_denotation",
                    )
                ]
                or any(
                    row
                    not in {
                        (
                            "full_body",
                            "number_of_years",
                            None,
                            "explicit_no_whole_domain_denotation",
                            "delegated_to_primary_statement_grammar",
                        ),
                        (
                            "full_body",
                            "nominal_year_token",
                            None,
                            "explicit_no_whole_domain_denotation",
                            "formula_or_operand_defeat",
                        ),
                    }
                    for row in full_body_rows
                )
                or body_units not in (set(), {"year"})
            ):
                raise ValueError(
                    f"highest-college-year adjudication changed: "
                    f"{field_key} {candidate_rows!r} body={body_units!r}"
                )

        normalized_description = normalize_description(description)
        if SCHOOL_YEARS_OUTSIDE_US_TITLE.fullmatch(normalized_description):
            school_years_outside_us_fields += 1
            school_years_outside_us_contexts.add(sha)
            decisions_by_family = {
                candidate[0]: decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            }
            if decisions_by_family != {
                "nominal_year_token": (
                    "year",
                    "whole_domain_denotation",
                    "school_years_outside_us_title_denotation",
                )
            }:
                raise ValueError(
                    f"school-years-outside-US adjudication changed: "
                    f"{field_key} {decisions_by_family!r}"
                )

        control_category: str | None = None
        if GRADE_OR_YEAR_ATTENDING_TITLE.fullmatch(normalized_description):
            control_category = "grade_or_year_attending"
        elif CALENDAR_YEAR_EDUCATION_TITLE.fullmatch(normalized_description):
            control_category = "calendar_year"
        if control_category is not None:
            education_title_negative_controls[control_category] += 1
            if any(
                disposition == "whole_domain_denotation"
                for _unit, disposition, _reason in adjudications
            ):
                raise ValueError(
                    f"education negative control became positive: "
                    f"{field_key} {control_category} {adjudications!r}"
                )

        typical_week_field = bool(
            re.match(
                r"^F1(?:[b-h]|d2)\. \(In a typical week, how many hours "
                r"\[do you/does \[he/she\]\] spend\)",
                header,
            )
            or row["raw_field_id"]
            in (
                FIRST_QUESTION_TYPICAL_WEEK_F1A_FIELDS
                | FIRST_QUESTION_TYPICAL_WEEK_DE60A_FIELDS
            )
        )
        if typical_week_field:
            typical_week_time_use_fields += 1
            typical_week_time_use_contexts.add(sha)
            if "Reference\nPerson" in description:
                typical_week_time_use_people["reference_person"] += 1
                if "the Reference\nPerson" not in description:
                    typical_week_reference_without_article_fields.add(
                        field_key
                    )
            elif "Spouse/Partner" in description:
                typical_week_time_use_people["spouse_partner"] += 1
            else:
                raise ValueError(
                    f"typical-week person grounding changed: {field_key}"
                )
            candidate_rows = [
                (
                    "full_body" if candidate in full_body_delta else "bounded",
                    candidate[0],
                    decision[0],
                    decision[1],
                    decision[2],
                )
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            ]
            typical_week_candidate_decisions.update(candidate_rows)
            expected_body_units = (
                set()
                if row["raw_field_id"]
                in FIRST_QUESTION_TYPICAL_WEEK_DE60A_FIELDS
                else {"hour_per_week"}
            )
            hour_decisions = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "nominal_hour_token"
            ]
            week_decisions = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "nominal_week_token"
            ]
            how_many_decisions = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "how_many_count_marker"
            ]
            governing_hour = (
                "hour_per_week",
                "whole_domain_denotation",
                "typical_week_hours_title_denotation",
            )
            allowed_other_hours = {
                (
                    None,
                    "explicit_no_whole_domain_denotation",
                    "question_line_suffix_phrase_not_value_denotation",
                ),
                (
                    None,
                    "explicit_no_whole_domain_denotation",
                    "formula_or_operand_defeat",
                ),
            }
            if (
                _body_ground_units(description) != expected_body_units
                or hour_decisions.count(governing_hour) != 1
                or any(
                    decision != governing_hour
                    and decision not in allowed_other_hours
                    for decision in hour_decisions
                )
                or not week_decisions
                or any(
                    decision
                    != (
                        None,
                        "explicit_no_whole_domain_denotation",
                        "typical_week_rate_denominator",
                    )
                    for decision in week_decisions
                )
                or how_many_decisions
                != [
                    (
                        None,
                        "explicit_no_whole_domain_denotation",
                        "count_marker_subordinate_to_unit_noun",
                    )
                ]
            ):
                raise ValueError(
                    f"typical-week time-use adjudication changed: "
                    f"{field_key} {candidate_rows!r}"
                )

        if header.startswith(
            "B6. During the last year how many miles did you and your family "
            "drive in (your car/all of"
        ):
            last_year_miles_fields += 1
            decisions_by_family = {
                candidate[0]: decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            }
            last_year_miles_candidate_decisions = decisions_by_family
            if (
                field_key != (1974, "V3520")
                or _body_ground_units(description) != {"mile_per_year"}
                or decisions_by_family
                != {
                    "nominal_year_token": (
                        None,
                        "explicit_no_whole_domain_denotation",
                        "last_year_rate_denominator",
                    ),
                    "how_many_count_marker": (
                        None,
                        "explicit_no_whole_domain_denotation",
                        "count_marker_subordinate_to_unit_noun",
                    ),
                    "nominal_mile_token": (
                        "mile_per_year",
                        "whole_domain_denotation",
                        "last_year_miles_title_denotation",
                    ),
                    "number_of_count_marker": (
                        None,
                        "explicit_no_whole_domain_denotation",
                        "delegated_to_primary_statement_grammar",
                    ),
                    "miles_per_year": (
                        None,
                        "explicit_no_whole_domain_denotation",
                        "delegated_to_primary_statement_grammar",
                    ),
                }
            ):
                raise ValueError(
                    f"last-year miles adjudication changed: "
                    f"{field_key} {decisions_by_family!r}"
                )

        raw_selector_components = {
            normalize_description(
                _selector_terminal_component(label)[0]
            ).upper()
            for _kind, _start, _end, label in selector_spans
        }
        if "NUMBER OF TIMES" in raw_selector_components:
            number_of_times_selector_fields += 1
            count_positive = any(
                candidate[0] == "number_of_count_marker"
                and decision[1] == "whole_domain_denotation"
                and decision[0] == "count"
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            )
            minute_positive = any(
                candidate[0] == "nominal_minute_token"
                and decision[1] == "whole_domain_denotation"
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
            )
            if not count_positive or minute_positive:
                raise ValueError(
                    f"NUMBER OF TIMES selector adjudication changed: {field_key}"
                )
        if re.fullmatch(
            r"Number of year-to-year changes in (?:county|state|region)",
            header,
        ):
            year_to_year_count_fields += 1
            count_rows = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "number_of_years"
            ]
            year_rows = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "nominal_year_token"
            ]
            if (
                count_rows
                != [
                    (
                        "count",
                        "whole_domain_denotation",
                        "count_of_changes_title_denotation",
                    )
                ]
                or len(year_rows) != 1
                or year_rows[0][1] == "whole_domain_denotation"
            ):
                raise ValueError(
                    f"year-to-year change count adjudication changed: "
                    f"{field_key} {count_rows!r} {year_rows!r}"
                )
        if _paid_extra_hours_yes_no(description, header):
            paid_extra_hours_yes_no_fields += 1
            paid_extra_hours_yes_no_field_keys.add(field_key)
            paid_extra_hours_yes_no_contexts.add(sha)
            cohort_pairs = [
                (candidate, decision)
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] in {"nominal_hour_token", "nominal_week_token"}
            ]
            cohort_rows = [decision for _candidate, decision in cohort_pairs]
            paid_extra_hours_yes_no_candidates += len(cohort_rows)
            paid_extra_hours_yes_no_candidate_decisions.update(
                (
                    "full_body" if candidate in full_body_delta else "bounded",
                    candidate[0],
                    decision[0],
                    decision[1],
                    decision[2],
                )
                for candidate, decision in cohort_pairs
            )
            for candidate, _decision in cohort_pairs:
                if candidate in first_question_delta:
                    stage = "first_question"
                elif candidate in baseline_candidates:
                    stage = "baseline"
                else:
                    stage = "other"
                paid_extra_hours_yes_no_transition_families[
                    (stage, candidate[0])
                ] += 1
            if any(
                disposition == "whole_domain_denotation"
                for _unit, disposition, _reason in cohort_rows
            ):
                raise ValueError(
                    "paid-extra-hours Boolean cohort contains a positive title "
                    f"candidate: {row['interview_wave']} {row['raw_field_id']}"
                )
        row_positive_count = sum(
            disposition == "whole_domain_denotation" and unit is not None
            for unit, disposition, _reason in adjudications
        )
        if row["raw_field_id"] == "ER47619":
            er47619_fields += 1
            week_rows = [
                decision
                for candidate, decision in zip(
                    candidates, adjudications, strict=True
                )
                if candidate[0] == "nominal_week_token"
                and candidate[3].upper() == "WEEKS"
            ]
            er47619_week_decisions = week_rows
            if week_rows != [
                (
                    "week",
                    "whole_domain_denotation",
                    "exact_output_label_names_unit",
                ),
                (
                    "week",
                    "whole_domain_denotation",
                    "exact_output_label_names_unit",
                ),
                (
                    None,
                    "explicit_no_whole_domain_denotation",
                    "delegated_to_primary_statement_grammar",
                ),
            ]:
                raise ValueError(
                    f"ER47619 duplicate selector changed: {week_rows!r}"
                )
        if row_positive_count > 1:
            positive_rows = [
                decision
                for decision in adjudications
                if decision[0] is not None
                and decision[1] == "whole_domain_denotation"
            ]
            positive_units = {decision[0] for decision in positive_rows}
            if len(positive_units) != 1:
                raise ValueError(
                    f"multi-positive field has multiple units: "
                    f"{field_key} {positive_rows!r}"
                )
            multi_positive_fields += 1
            multi_positive_field_keys.add(field_key)
            multi_positive_multiplicities[len(positive_rows)] += 1
            multi_positive_units.update(
                decision[0] for decision in positive_rows
            )
            multi_positive_reasons.update(
                decision[2] for decision in positive_rows
            )
        positive_candidate_occurrences += row_positive_count
        positive_fields += bool(row_positive_count)
        for candidate, decision in zip(candidates, adjudications, strict=True):
            family, start, end, spelling = candidate
            unit, disposition, reason = decision
            key = (sha, family, start, end, spelling)
            existing = decisions.get(key)
            if existing is not None and existing != decision:
                raise ValueError(
                    f"same context adjudicated differently: {key!r}"
                )
            occurrence_counts[(family, unit, disposition, reason)] += 1
            if existing is not None:
                continue
            decisions[key] = decision
            context_counts[(family, unit, disposition, reason)] += 1
            authority.append(
                (
                    sha,
                    header,
                    family,
                    start,
                    end,
                    spelling,
                    unit,
                    disposition,
                    reason,
                    row["interview_wave"],
                    row["raw_field_id"],
                )
            )

    input_relation_hasher.update(b"]\n")
    input_relation_sha256 = input_relation_hasher.hexdigest()
    if field_count != EXPECTED_FIELD_COUNT:
        raise ValueError(
            f"expected {EXPECTED_FIELD_COUNT} rows, got {field_count}"
        )
    if input_relation_sha256 != RAW_INPUT_RELATION_SHA256:
        raise ValueError(
            "lawful raw input relation identity changed: "
            f"{input_relation_sha256}"
        )
    expected_structural_kinds = {
        "double_hyphen": 48_038,
        "next_line": 2_317,
        "single_hyphen": 3_118,
        "single_hyphen_next_line": 353,
        "split_hyphen": 410,
    }
    expected_structural_lines = {
        1: 33_850,
        2: 13_529,
        3: 5_478,
        4: 1_207,
        5: 112,
        6: 15,
        7: 44,
        8: 1,
    }
    expected_header_lines = {
        1: 46_993,
        2: 32_117,
        3: 7_583,
        4: 2_171,
        5: 419,
        6: 130,
        7: 62,
        8: 14,
        9: 20,
        10: 68,
        11: 14,
        13: 2,
        14: 2,
        15: 2,
        16: 2,
    }
    if (
        structural_selector_occurrences != 54_236
        or structural_selector_fields != 51_397
        or dict(structural_selector_kinds) != expected_structural_kinds
        or dict(structural_selector_label_lines) != expected_structural_lines
        or dict(header_physical_line_counts) != expected_header_lines
        or structural_selector_line8_keys != [[2011, "ER52049"]]
        or food_body_code_occurrences != 88
        or len(food_body_code_fields) != 16
        or body_instruction_occurrences != 78
        or len(body_instruction_fields) != 78
        or editorial_note_occurrences != 20
        or len(editorial_note_fields) != 20
        or separator_next_line_occurrences != 17
        or len(separator_next_line_fields) != 10
    ):
        raise ValueError(
            "structural selector census changed: "
            f"{structural_selector_occurrences} occurrences, "
            f"{structural_selector_fields} fields, "
            f"{structural_selector_kinds!r}, "
            f"starts={structural_selector_label_lines!r}, "
            f"headers={header_physical_line_counts!r}, "
            f"line8={structural_selector_line8_keys!r}, "
            f"food={food_body_code_occurrences}/"
            f"{len(food_body_code_fields)}, "
            f"body-instructions={body_instruction_occurrences}/"
            f"{len(body_instruction_fields)}, "
            f"editorial-notes={editorial_note_occurrences}/"
            f"{len(editorial_note_fields)}, "
            f"separators={separator_next_line_occurrences}/"
            f"{len(separator_next_line_fields)}"
        )
    expected_singleton_unit_signatures = {
        ("single_hyphen", "BEGINNING MONTH FOR JOB 3"): 1,
        ("single_hyphen", "HOURS"): 2,
        ("single_hyphen", "MONTH"): 216,
        ("single_hyphen", "MONTH BEGAN FIRST EXTRA JOB"): 24,
        ("single_hyphen", "MONTH BEGAN SECOND EXTRA JOB"): 24,
        ("single_hyphen", "MONTH ENDED FIRST EXTRA JOB"): 24,
        ("single_hyphen", "MONTH ENDED SECOND EXTRA JOB"): 24,
        ("single_hyphen", "MONTH LAST EMPLOYER"): 9,
        ("single_hyphen", "MONTH LAST POSITION"): 12,
        ("single_hyphen", "MONTH NEXT-TO-LAST POSITION"): 4,
        ("single_hyphen", "MONTH OF FIRST MENTION"): 9,
        ("single_hyphen", "MONTH OF SECOND MENTION"): 9,
        ("single_hyphen", "MONTH OF THIRD MENTION"): 9,
        ("single_hyphen", "PERCENT"): 22,
        ("single_hyphen", "PERCENT OF PAY"): 1,
        ("single_hyphen", "TOTAL MONTHS"): 3,
        ("single_hyphen", "WEEKS"): 2,
        ("single_hyphen", "YEAR"): 225,
        ("single_hyphen", "YEAR (FIRST OF TWO OR MORE)"): 4,
        ("single_hyphen", "YEAR (LAST/ ONLY)"): 1,
        ("single_hyphen", "YEAR (LAST/ONLY)"): 3,
        ("single_hyphen", "YEAR (MARRIED ONLY ONCE)"): 1,
        ("single_hyphen", "YEAR BEGAN FIRST EXTRA JOB"): 24,
        ("single_hyphen", "YEAR BEGAN SECOND EXTRA JOB"): 24,
        ("single_hyphen", "YEAR ENDED FIRST EXTRA JOB"): 24,
        ("single_hyphen", "YEAR ENDED SECOND EXTRA JOB"): 14,
        ("single_hyphen", "YEAR ENDED SECOND JOB"): 10,
        ("single_hyphen", "YEAR LAST EMPLOYER"): 9,
        ("single_hyphen", "YEAR LAST POSITION"): 12,
        ("single_hyphen", "YEAR NEXT-TO-LAST POSITION"): 4,
        ("single_hyphen", "YEAR OF FIRST"): 2,
        ("single_hyphen", "YEAR OF FIRST MENTION"): 9,
        ("single_hyphen", "YEAR OF SECOND MENTION"): 9,
        ("single_hyphen", "YEAR OF THIRD MENTION"): 9,
        ("single_hyphen_next_line", "MONTH"): 52,
        ("single_hyphen_next_line", "MONTH LAST EMPLOYER"): 3,
        ("single_hyphen_next_line", "MONTH LAST POSITION"): 4,
        ("single_hyphen_next_line", "MONTH NEXT-TO-LAST POSITION"): 4,
        ("single_hyphen_next_line", "TOTAL MONTHS"): 5,
        ("single_hyphen_next_line", "YEAR"): 49,
        ("single_hyphen_next_line", "YEAR LAST EMPLOYER"): 3,
        ("single_hyphen_next_line", "YEAR LAST POSITION"): 4,
        ("single_hyphen_next_line", "YEAR NEXT-TO-LAST POSITION"): 4,
    }
    if (
        singleton_direct_occurrences != 3_463
        or len(singleton_direct_fields) != 3_457
        or singleton_nested_response_occurrences != 8
        or len(singleton_nested_response_fields) != 7
        or dict(singleton_unit_signatures)
        != expected_singleton_unit_signatures
        or len(singleton_unit_fields) != 907
        or dict(singleton_unit_counts)
        != {
            "hour": 2,
            "month": 436,
            "percent": 23,
            "week": 2,
            "year": 444,
        }
        or dict(singleton_response_counts)
        != {
            "AMOUNT": 31,
            "LUMP SUM": 3,
            "TIME UNIT": 52,
            "TYPE": 10,
            "TYPE OF RESPONSE": 10,
        }
        or singleton_nonsemantic_direct_occurrences != 2_450
    ):
        raise ValueError(
            "singleton selector partition changed: "
            f"direct={singleton_direct_occurrences}/"
            f"{len(singleton_direct_fields)}, nested="
            f"{singleton_nested_response_occurrences}/"
            f"{len(singleton_nested_response_fields)}, units="
            f"{singleton_unit_counts!r}/{len(singleton_unit_fields)}, "
            f"responses={singleton_response_counts!r}, "
            f"nonsemantic={singleton_nonsemantic_direct_occurrences}, "
            f"signatures={singleton_unit_signatures!r}"
        )
    expected_external_units = {
        "day": 148,
        "hour": 34,
        "minute": 28,
        "month": 747,
        "percent": 97,
        "week": 180,
        "year": 622,
    }
    if (
        dict(external_unit_selector_counts) != expected_external_units
        or len(external_unit_selector_fields) != 1_855
        or external_unit_selector_contained != 1_856
        or dict(external_unit_selector_lines)
        != {2: 1_141, 3: 580, 4: 123, 5: 8, 6: 4}
    ):
        raise ValueError(
            "external selector census changed: "
            f"{external_unit_selector_counts!r}, "
            f"{len(external_unit_selector_fields)} fields, "
            f"{external_unit_selector_contained} contained, "
            f"{external_unit_selector_lines!r}"
        )
    if (
        dict(raw_physical_unit_selector_counts)
        != {
            "day": 399,
            "hour": 195,
            "minute": 28,
            "month": 1_995,
            "percent": 166,
            "week": 469,
            "year": 1_691,
        }
        or len(raw_physical_unit_selector_fields) != 4_942
        or raw_physical_unit_selector_contained != 4_943
    ):
        raise ValueError(
            "parser-derived physical selector census changed: "
            f"{raw_physical_unit_selector_counts!r}, "
            f"{len(raw_physical_unit_selector_fields)}, "
            f"{raw_physical_unit_selector_contained}"
        )
    expected_raw_response_counts = {
        "AMOUNT": 1_842,
        "LUMP SUM": 39,
        "TIME UNIT": 2_077,
        "TYPE": 21,
        "TYPE OF RESPONSE": 10,
    }
    expected_raw_response_lines = {
        ("AMOUNT", 1): 1_277,
        ("AMOUNT", 2): 413,
        ("AMOUNT", 3): 98,
        ("AMOUNT", 4): 25,
        ("AMOUNT", 5): 26,
        ("AMOUNT", 6): 2,
        ("AMOUNT", 7): 1,
        ("LUMP SUM", 1): 14,
        ("LUMP SUM", 2): 25,
        ("TIME UNIT", 1): 1_486,
        ("TIME UNIT", 2): 391,
        ("TIME UNIT", 3): 145,
        ("TIME UNIT", 4): 32,
        ("TIME UNIT", 5): 20,
        ("TIME UNIT", 6): 2,
        ("TIME UNIT", 7): 1,
        ("TYPE", 1): 10,
        ("TYPE", 2): 10,
        ("TYPE", 3): 1,
        ("TYPE OF RESPONSE", 1): 10,
    }
    if (
        dict(raw_response_selector_counts) != expected_raw_response_counts
        or dict(raw_response_selector_lines) != expected_raw_response_lines
    ):
        raise ValueError(
            "raw AMOUNT/TIME UNIT census changed: "
            f"{raw_response_selector_counts!r}, "
            f"{raw_response_selector_lines!r}"
        )

    expected_first_question_families = {
        "daily_morphology": 8,
        "dollar_symbol": 80,
        "how_many_count_marker": 25,
        "hundreds_of_dollars": 1,
        "nominal_day_token": 101,
        "nominal_dollar_token": 1,
        "nominal_hour_token": 66,
        "nominal_minute_token": 6,
        "nominal_month_token": 233,
        "nominal_week_token": 93,
        "nominal_year_token": 313,
        "number_of_years": 28,
        "per_month_rate_phrase": 14,
        "percent_word": 7,
        "weekly_morphology": 2,
    }
    expected_singleton_delta_families = {
        "dollar_symbol": 65,
        "how_many_count_marker": 2,
        "nominal_count_token": 8,
        "nominal_dollar_token": 2,
        "nominal_month_token": 196,
        "nominal_week_token": 4,
        "nominal_year_token": 186,
        "number_of_count_marker": 33,
        "percent_word": 13,
    }
    expected_later_question_families = {
        "dollar_symbol": 6,
        "hours_a_week": 18,
        "how_many_count_marker": 32,
        "monthly_morphology": 6,
        "nominal_day_token": 63,
        "nominal_hour_token": 1,
        "nominal_month_token": 82,
        "nominal_week_token": 182,
        "nominal_year_token": 19,
        "percent_word": 5,
    }
    expected_question_line_suffix_families = {
        "nominal_count_token": 29,
        "nominal_hour_token": 8,
        "nominal_month_token": 5,
        "nominal_week_token": 8,
        "nominal_year_token": 1,
        "number_of_count_marker": 2,
    }
    expected_question_continuation_families = {
        "dollar_symbol": 1,
        "nominal_count_token": 66,
        "nominal_month_token": 15,
        "nominal_year_token": 2,
    }
    expected_full_body_families = {
        "dollar_amount": 145,
        "dollar_symbol": 526,
        "dollar_value": 18,
        "dollars_per_week": 2,
        "hourly_morphology": 263,
        "hours_per_week": 837,
        "hours_per_year": 25,
        "hundreds_of_dollars": 4,
        "in_dollars": 55,
        "in_minutes": 1,
        "miles_per_year": 1,
        "monthly_morphology": 170,
        "nominal_count_token": 36,
        "nominal_day_token": 388,
        "nominal_dollar_token": 2_557,
        "nominal_hour_token": 1_179,
        "nominal_mile_token": 68,
        "nominal_minute_token": 59,
        "nominal_month_token": 1_007,
        "nominal_week_token": 960,
        "nominal_year_token": 5_360,
        "number_in_family_unit_marker": 9,
        "number_of_count_marker": 3_579,
        "number_of_days": 7,
        "number_of_months": 88,
        "number_of_weeks": 1_006,
        "number_of_years": 109,
        "per_day_rate_phrase": 23,
        "per_hour_rate_phrase": 470,
        "per_month_rate_phrase": 3,
        "per_week_rate_phrase": 163,
        "per_year_rate_phrase": 2,
        "percent_symbol": 284,
        "percent_word": 314,
        "reference_hour_token": 32,
        "weekly_morphology": 220,
    }
    expected_full_body_negative_reasons = {
        "calendar_or_reference_body_prose_defeat": 1_456,
        "delegated_to_actual_statement_grammar": 365,
        "delegated_to_coding_statement_grammar": 648,
        "delegated_to_primary_statement_grammar": 11_004,
        "explanatory_body_prose_defeat": 839,
        "formula_or_operand_defeat": 3_618,
        "input_table_or_subrange_not_field_denotation": 8,
        "instruction_threshold_table_or_subrange_defeat": 2_005,
        "unmarked_output_dollar_phrase_is_conversion_input": 1,
    }
    expected_first_question_positive_fields = {
        (wave, field_id)
        for wave, field_id in (
            (2003, "ER23274"),
            (2007, "ER40408"),
            (2009, "ER46381"),
            (2011, "ER51742"),
            (2017, "ER66029"),
            (2017, "ER66683"),
            (2017, "ER66714"),
            (2017, "ER66727"),
            (2017, "ER68025"),
            (2019, "ER72029"),
            (2019, "ER72685"),
            (2019, "ER72718"),
            (2019, "ER72731"),
            (2019, "ER74047"),
            (2021, "ER78030"),
            (2021, "ER78761"),
            (2021, "ER78795"),
            (2021, "ER78808"),
            (2021, "ER80169"),
            (2021, "ER81270"),
            (2021, "ER81263"),
            (2021, "ER81316"),
            (2023, "ER82031"),
            (2023, "ER82753"),
            (2023, "ER82788"),
            (2023, "ER82801"),
            (2023, "ER84139"),
            (1985, "V11867"),
            (1985, "V12242"),
        )
    }
    expected_later_question_positive_fields = {
        (wave, field_id)
        for wave, field_id in (
            (1968, "V203"),
            (1968, "V223"),
            (1968, "V225"),
            (1968, "V235"),
            (1968, "V236"),
            (1968, "V278"),
            (1968, "V290"),
            (1969, "V658"),
            (1969, "V659"),
            (1988, "V15919"),
            (1988, "V15944"),
            (1988, "V15969"),
        )
    }
    expected_full_body_positive_fields = {
        (wave, field_id)
        for wave, field_id in (
            (1968, "V150"),
            (1968, "V125"),
            (1968, "V207"),
            (1968, "V265"),
            (1968, "V324"),
            (1969, "V865"),
            (1970, "V1479"),
            (1971, "V2191"),
            (1972, "V2817"),
            (1972, "V2818"),
            (1972, "V2900"),
            (1973, "V3235"),
            (1974, "V3657"),
            (1976, "V5076"),
            (1978, "V6196"),
            (1976, "V4832"),
            (1976, "V4903"),
            (1978, "V6145"),
            (1979, "V6742"),
            (1980, "V7375"),
            (1981, "V8027"),
            (1981, "V8028"),
            (1983, "V9337"),
            (1983, "V9338"),
            (1985, "V11917"),
            (1985, "V11918"),
        )
    }
    if (
        baseline_candidate_occurrences != 58_298
        or baseline_candidate_fields != 46_453
        or first_question_candidate_occurrences != 978
        or len(first_question_candidate_fields) != 788
        or dict(first_question_candidate_families)
        != expected_first_question_families
        or dict(first_question_dispositions) != {"N": 945, "W": 33}
        or first_question_positive_reasons
        != {
            "direct_count_question_title_denotation": 7,
            "outside_us_years_title_denotation": 2,
            "pension_percent_title_denotation": 4,
            "typical_week_hours_title_denotation": 12,
            "wrapped_alternative_days_title_denotation": 8,
        }
        or first_question_positive_fields
        != expected_first_question_positive_fields
        or singleton_delta_candidate_occurrences != 509
        or len(singleton_delta_candidate_fields) != 463
        or dict(singleton_delta_candidate_families)
        != expected_singleton_delta_families
        or dict(singleton_delta_dispositions) != {"N": 453, "W": 56}
        or singleton_delta_positive_reasons
        != {
            "dollars_worth_amount_title_denotation": 1,
            "exact_output_label_names_unit": 22,
            "total_number_selector_title_denotation": 33,
        }
        or len(singleton_delta_positive_fields) != 56
        or later_question_candidate_occurrences != 414
        or len(later_question_candidate_fields) != 145
        or dict(later_question_candidate_families)
        != expected_later_question_families
        or dict(later_question_dispositions) != {"N": 399, "W": 15}
        or later_question_positive_reasons
        != {
            "later_direct_count_question_title_denotation": 7,
            "later_direct_hours_title_denotation": 1,
            "later_direct_weeks_title_denotation": 3,
            "later_typical_week_hours_title_denotation": 4,
        }
        or later_question_positive_fields
        != expected_later_question_positive_fields
        or question_line_suffix_candidate_occurrences != 53
        or len(question_line_suffix_candidate_fields) != 48
        or dict(question_line_suffix_candidate_families)
        != expected_question_line_suffix_families
        or dict(question_line_suffix_dispositions) != {"N": 51, "W": 2}
        or question_line_suffix_positive_reasons
        != {"parenthetical_count_suffix_title_denotation": 2}
        or question_line_suffix_positive_fields
        != {(1982, "V8651"), (1982, "V8652")}
        or question_continuation_candidate_occurrences != 84
        or len(question_continuation_candidate_fields) != 84
        or dict(question_continuation_candidate_families)
        != expected_question_continuation_families
        or dict(question_continuation_dispositions) != {"N": 84}
        or full_body_candidate_occurrences != 19_970
        or len(full_body_candidate_fields) != 11_085
        or dict(full_body_candidate_families) != expected_full_body_families
        or dict(full_body_dispositions) != {"N": 19_944, "W": 26}
        or dict(full_body_negative_reasons)
        != expected_full_body_negative_reasons
        or full_body_positive_reasons
        != {
            "standalone_output_label_names_currency": 2,
            "unmarked_count_output_title_denotation": 19,
            "unmarked_percent_output_title_denotation": 2,
            "unmarked_percentage_output_title_denotation": 1,
            "unmarked_year_output_title_denotation": 1,
            "wrapped_in_dollars_output_title_denotation": 1,
        }
        or full_body_positive_fields != expected_full_body_positive_fields
        or (
            baseline_candidate_occurrences
            + first_question_candidate_occurrences
            + singleton_delta_candidate_occurrences
            + later_question_candidate_occurrences
            + question_line_suffix_candidate_occurrences
            + question_continuation_candidate_occurrences
            + full_body_candidate_occurrences
        )
        != 80_306
    ):
        raise ValueError(
            "round-3 title transition changed: "
            f"baseline={baseline_candidate_occurrences}/"
            f"{baseline_candidate_fields}, first-question="
            f"{first_question_candidate_occurrences}/"
            f"{len(first_question_candidate_fields)} "
            f"{first_question_candidate_families!r} "
            f"{first_question_dispositions!r} "
            f"{first_question_positive_reasons!r}, singleton="
            f"{singleton_delta_candidate_occurrences}/"
            f"{len(singleton_delta_candidate_fields)} "
            f"{singleton_delta_candidate_families!r} "
            f"{singleton_delta_dispositions!r} "
            f"{singleton_delta_positive_reasons!r}, later-question="
            f"{later_question_candidate_occurrences}/"
            f"{len(later_question_candidate_fields)} "
            f"{later_question_candidate_families!r} "
            f"{later_question_dispositions!r} "
            f"{later_question_positive_reasons!r}, question-line-suffix="
            f"{question_line_suffix_candidate_occurrences}/"
            f"{len(question_line_suffix_candidate_fields)} "
            f"{question_line_suffix_dispositions!r}, continuation="
            f"{question_continuation_candidate_occurrences}/"
            f"{len(question_continuation_candidate_fields)} "
            f"{question_continuation_dispositions!r}, full-body="
            f"{full_body_candidate_occurrences}/"
            f"{len(full_body_candidate_fields)} "
            f"{full_body_dispositions!r} {full_body_positive_reasons!r}"
        )

    expected_calendar_contexts = {
        "selector_year": 391,
        "selector_month": 390,
        "direct_year": 99,
        "direct_month": 15,
        "direct_day": 2,
        "year_to_year_change": 3,
    }
    expected_calendar_fields = {
        "selector_year": 659,
        "selector_month": 652,
        "direct_year": 169,
        "direct_month": 28,
        "direct_day": 14,
        "year_to_year_change": 3,
    }
    calendar_context_counts = {
        category: len(contexts)
        for category, contexts in stable_calendar_contexts.items()
    }
    calendar_digest = hashlib.sha256(
        "".join(f"{value}\n" for value in sorted(stable_calendar_shas)).encode(
            "utf-8"
        )
    ).hexdigest()
    if (
        calendar_context_counts != expected_calendar_contexts
        or dict(stable_calendar_fields) != expected_calendar_fields
        or len(stable_calendar_shas) != 900
        or calendar_digest != CALENDAR_COHORT_SHA256
    ):
        raise ValueError(
            "lawful raw calendar cohort changed: "
            f"{calendar_context_counts!r}, {stable_calendar_fields!r}, "
            f"{len(stable_calendar_shas)} contexts, {calendar_digest}"
        )
    if (
        age_year_selector_fields,
        len(age_year_selector_contexts),
        legacy_age_year_selector_fields,
        len(legacy_age_year_selector_contexts),
    ) != (24, 7, 18, 5):
        raise ValueError(
            "age-YEAR selector cohort changed: "
            f"{age_year_selector_fields}, {len(age_year_selector_contexts)}, "
            f"{legacy_age_year_selector_fields}, "
            f"{len(legacy_age_year_selector_contexts)}"
        )
    if (overtime_amount_fields, overtime_time_unit_fields) != (14, 14):
        raise ValueError(
            "overtime AMOUNT/TIME UNIT cohort changed: "
            f"{overtime_amount_fields}, {overtime_time_unit_fields}"
        )
    expected_overtime_candidate_decisions = {
        (
            "amount",
            "bounded",
            "how_many_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "count_marker_subordinate_to_unit_noun",
        ): 14,
        (
            "amount",
            "bounded",
            "nominal_hour_token",
            "hour",
            "whole_domain_denotation",
            "how_many_directly_governs_unit_noun",
        ): 14,
        (
            "time_unit",
            "bounded",
            "how_many_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "alternative_defeated_by_response_selector",
        ): 14,
        (
            "time_unit",
            "bounded",
            "nominal_hour_token",
            None,
            "explicit_no_whole_domain_denotation",
            "alternative_defeated_by_response_selector",
        ): 14,
    }
    if dict(overtime_candidate_decisions) != (
        expected_overtime_candidate_decisions
    ):
        raise ValueError(
            "overtime per-start partition changed: "
            f"{overtime_candidate_decisions!r}"
        )
    if (
        dollars_worth_amount_fields,
        dollars_worth_time_unit_fields,
        len(dollars_worth_contexts),
        dollars_worth_body_grounded_fields,
    ) != (11, 11, 20, 2):
        raise ValueError(
            "dollars-worth AMOUNT/TIME UNIT cohort changed: "
            f"{dollars_worth_amount_fields}, "
            f"{dollars_worth_time_unit_fields}, "
            f"{len(dollars_worth_contexts)}, "
            f"{dollars_worth_body_grounded_fields}"
        )
    expected_dollars_worth_candidate_decisions = {
        (
            "amount",
            "bounded",
            "how_many_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "count_marker_subordinate_to_unit_noun",
        ): 11,
        (
            "amount",
            "bounded",
            "nominal_dollar_token",
            "united_states_dollar",
            "whole_domain_denotation",
            "dollars_worth_amount_title_denotation",
        ): 11,
        (
            "amount",
            "full_body",
            "nominal_dollar_token",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ): 2,
        (
            "time_unit",
            "bounded",
            "how_many_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "alternative_defeated_by_response_selector",
        ): 11,
        (
            "time_unit",
            "bounded",
            "nominal_dollar_token",
            None,
            "explicit_no_whole_domain_denotation",
            "alternative_defeated_by_response_selector",
        ): 11,
        (
            "time_unit",
            "full_body",
            "nominal_month_token",
            None,
            "explicit_no_whole_domain_denotation",
            "formula_or_operand_defeat",
        ): 2,
    }
    if dict(dollars_worth_candidate_decisions) != (
        expected_dollars_worth_candidate_decisions
    ):
        raise ValueError(
            "dollars-worth per-start partition changed: "
            f"{dollars_worth_candidate_decisions!r}"
        )
    expected_dollars_worth_field_keys = {
        "amount": {
            (1993, "V21713"),
            (1994, "ER3060"),
            (1995, "ER6059"),
            (1996, "ER8156"),
            (1997, "ER11050"),
            (1999, "ER14241"),
            (1999, "ER14256"),
            (1999, "ER14285"),
            (2001, "ER18371"),
            (2001, "ER18387"),
            (2001, "ER18417"),
        },
        "time_unit": {
            (1993, "V21714"),
            (1994, "ER3061"),
            (1995, "ER6060"),
            (1996, "ER8157"),
            (1997, "ER11051"),
            (1999, "ER14242"),
            (1999, "ER14257"),
            (1999, "ER14286"),
            (2001, "ER18372"),
            (2001, "ER18388"),
            (2001, "ER18418"),
        },
    }
    if dict(dollars_worth_field_keys) != expected_dollars_worth_field_keys:
        raise ValueError(
            "dollars-worth field-key partition changed: "
            f"{dollars_worth_field_keys!r}"
        )
    if dollars_worth_full_body_fields != {
        (1995, "ER6060"),
        (1999, "ER14285"),
        (2001, "ER18417"),
    }:
        raise ValueError(
            "dollars-worth full-body field cohort changed: "
            f"{dollars_worth_full_body_fields!r}"
        )
    expected_pension_selector_fields = {
        "amount": 24,
        "time_unit": 24,
        "percent": 24,
        "lump_sum": 24,
    }
    pension_context_counts = {
        category: len(contexts)
        for category, contexts in pension_selector_contexts.items()
    }
    if dict(
        pension_selector_fields
    ) != expected_pension_selector_fields or pension_context_counts != {
        category: 4 for category in expected_pension_selector_fields
    }:
        raise ValueError(
            "pension selector sibling cohort changed: "
            f"{pension_selector_fields!r}, {pension_context_counts!r}"
        )
    pension_common_family_counts = {
        "in_dollars": 24,
        "nominal_month_token": 12,
        "nominal_year_token": 24,
        "per_month_rate_phrase": 12,
        "percent_word": 24,
    }
    expected_pension_candidate_decisions: dict[
        tuple[str, str, str, str | None, str, str], int
    ] = {}
    for category in ("time_unit", "lump_sum"):
        for family, count in pension_common_family_counts.items():
            expected_pension_candidate_decisions[
                (
                    category,
                    "bounded",
                    family,
                    None,
                    "explicit_no_whole_domain_denotation",
                    "alternative_defeated_by_response_selector",
                )
            ] = count
    for family, count in pension_common_family_counts.items():
        if family == "in_dollars":
            expected_pension_candidate_decisions[
                (
                    "amount",
                    "bounded",
                    family,
                    "united_states_dollar",
                    "whole_domain_denotation",
                    "pension_amount_arm_denotes_dollars",
                )
            ] = count
        else:
            expected_pension_candidate_decisions[
                (
                    "amount",
                    "bounded",
                    family,
                    None,
                    "explicit_no_whole_domain_denotation",
                    "alternative_defeated_by_response_selector",
                )
            ] = count
    for family, count in pension_common_family_counts.items():
        expected_pension_candidate_decisions[
            (
                "percent",
                "bounded",
                family,
                None,
                "explicit_no_whole_domain_denotation",
                "alternative_defeated_by_output_label",
            )
        ] = count
    expected_pension_candidate_decisions[
        (
            "percent",
            "bounded",
            "percent_word",
            "percent",
            "whole_domain_denotation",
            "exact_output_label_names_unit",
        )
    ] = 24
    if dict(pension_candidate_decisions) != (
        expected_pension_candidate_decisions
    ):
        raise ValueError(
            "pension per-start partition changed: "
            f"{pension_candidate_decisions!r}"
        )
    if (
        experience_fields,
        len(experience_contexts),
        dict(experience_units),
    ) != (
        102,
        32,
        {"year": 34, "month": 34, "week": 34},
    ):
        raise ValueError(
            "experience selector cohort changed: "
            f"{experience_fields}, {len(experience_contexts)}, "
            f"{experience_units!r}"
        )
    experience_context_counts = {
        unit: len(contexts)
        for unit, contexts in experience_contexts_by_unit.items()
    }
    experience_context_digest = hashlib.sha256(
        "".join(f"{value}\n" for value in sorted(experience_contexts)).encode(
            "utf-8"
        )
    ).hexdigest()
    if (
        experience_context_counts != {"year": 11, "month": 11, "week": 10}
        or experience_context_digest
        != "26ddc3bf9f32e208733ed85a5e0db0ec5ad817a00450e85483b74a06b5656e9f"
    ):
        raise ValueError(
            "experience selector context identities changed: "
            f"{experience_context_counts!r} {experience_context_digest}"
        )
    if (
        experience_nonselector_fields,
        len(experience_nonselector_contexts),
    ) != (12, 4):
        raise ValueError(
            "experience body-grounded defeat cohort changed: "
            f"{experience_nonselector_fields}, "
            f"{len(experience_nonselector_contexts)}"
        )
    experience_nonselector_context_digest = hashlib.sha256(
        "".join(
            f"{value}\n" for value in sorted(experience_nonselector_contexts)
        ).encode("utf-8")
    ).hexdigest()
    if experience_nonselector_context_digest != (
        "56c3d8f981b9eb5de3aa49d1f23b84340d969b11ae72944ec657631b7d29a49a"
    ):
        raise ValueError(
            "experience body-grounded context identities changed: "
            f"{experience_nonselector_context_digest}"
        )
    expected_experience_nonselector_candidate_decisions = {
        (
            "bounded",
            "how_many_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "count_marker_subordinate_to_unit_noun",
        ): 12,
        (
            "bounded",
            "nominal_year_token",
            None,
            "explicit_no_whole_domain_denotation",
            "phrase_is_input_to_exact_raw_body_unit",
        ): 12,
        (
            "full_body",
            "number_of_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ): 2,
        (
            "full_body",
            "number_of_months",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ): 10,
    }
    if dict(experience_nonselector_candidate_decisions) != (
        expected_experience_nonselector_candidate_decisions
    ):
        raise ValueError(
            "experience body-grounded per-start partition changed: "
            f"{experience_nonselector_candidate_decisions!r}"
        )
    expected_experience_nonselector_context_fields = {
        "2f11e7aad9256014919937d79fea9a3c2e8cccf9ad931023ad206679d8dcf7e9": {
            (1993, "V22842")
        },
        "418b260a6b4aa000d850a4489a42069cb12f15d1819560648c1fb8aaf5328e8f": {
            (1988, "V15181"),
            (1989, "V16682"),
            (1990, "V18120"),
            (1991, "V19420"),
            (1992, "V20720"),
        },
        "61aae002fc14e9071b7a9c4bd53daa13876d30e6a81afe71586ebb71d9690011": {
            (1993, "V22489")
        },
        "6c92990ad271489b6bb3467bece6804ca3d9fe889da5a15831996c90a0a40667": {
            (1988, "V15483"),
            (1989, "V17001"),
            (1990, "V18422"),
            (1991, "V19722"),
            (1992, "V21022"),
        },
    }
    if dict(experience_nonselector_context_fields) != (
        expected_experience_nonselector_context_fields
    ):
        raise ValueError(
            "experience body-grounded context-to-field map changed: "
            f"{experience_nonselector_context_fields!r}"
        )
    expected_typical_week_candidate_decisions = {
        (
            "bounded",
            "daily_morphology",
            None,
            "explicit_no_whole_domain_denotation",
            "unsupported_morphological_rate",
        ): 8,
        (
            "bounded",
            "how_many_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "count_marker_subordinate_to_unit_noun",
        ): 68,
        (
            "bounded",
            "nominal_day_token",
            None,
            "explicit_no_whole_domain_denotation",
            "first_question_coordinate_frequency_or_comparison_input",
        ): 8,
        (
            "bounded",
            "nominal_hour_token",
            "hour_per_week",
            "whole_domain_denotation",
            "typical_week_hours_title_denotation",
        ): 68,
        (
            "bounded",
            "nominal_hour_token",
            None,
            "explicit_no_whole_domain_denotation",
            "question_line_suffix_phrase_not_value_denotation",
        ): 8,
        (
            "bounded",
            "nominal_week_token",
            None,
            "explicit_no_whole_domain_denotation",
            "typical_week_rate_denominator",
        ): 72,
        (
            "full_body",
            "hours_per_week",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ): 64,
        (
            "full_body",
            "nominal_hour_token",
            None,
            "explicit_no_whole_domain_denotation",
            "formula_or_operand_defeat",
        ): 8,
        (
            "full_body",
            "number_of_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ): 64,
    }
    if (
        typical_week_time_use_fields,
        len(typical_week_time_use_contexts),
        dict(typical_week_time_use_people),
    ) != (
        68,
        17,
        {"reference_person": 32, "spouse_partner": 36},
    ):
        raise ValueError(
            "typical-week time-use cohort changed: "
            f"{typical_week_time_use_fields}, "
            f"{len(typical_week_time_use_contexts)}, "
            f"{typical_week_time_use_people!r}"
        )
    if dict(typical_week_candidate_decisions) != (
        expected_typical_week_candidate_decisions
    ):
        raise ValueError(
            "typical-week candidate partition changed: "
            f"{typical_week_candidate_decisions!r}"
        )
    if typical_week_reference_without_article_fields != {
        (2017, "ER66714"),
        (2019, "ER72718"),
        (2021, "ER78795"),
        (2023, "ER82788"),
    }:
        raise ValueError(
            "typical-week no-article Reference Person cohort changed: "
            f"{typical_week_reference_without_article_fields!r}"
        )
    expected_highest_college_year_candidate_decisions = {
        (
            "bounded",
            "nominal_year_token",
            "year",
            "whole_domain_denotation",
            "highest_college_year_title_denotation",
        ): 62,
        (
            "full_body",
            "number_of_years",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ): 2,
        (
            "full_body",
            "nominal_year_token",
            None,
            "explicit_no_whole_domain_denotation",
            "formula_or_operand_defeat",
        ): 12,
    }
    if (
        highest_college_year_fields,
        len(highest_college_year_contexts),
        highest_college_year_body_grounded_fields,
    ) != (62, 46, 2):
        raise ValueError(
            "highest-college-year cohort changed: "
            f"{highest_college_year_fields}, "
            f"{len(highest_college_year_contexts)}, "
            f"{highest_college_year_body_grounded_fields}"
        )
    if dict(highest_college_year_candidate_decisions) != (
        expected_highest_college_year_candidate_decisions
    ):
        raise ValueError(
            "highest-college-year candidate partition changed: "
            f"{highest_college_year_candidate_decisions!r}"
        )
    if highest_college_year_full_body_fields != {
        (1985, "V11959"),
        (1985, "V12314"),
        (1986, "V13512"),
        (1986, "V13582"),
        (1987, "V14559"),
        (1987, "V14629"),
        (1988, "V16033"),
        (1988, "V16103"),
        (1989, "V17430"),
        (1989, "V17500"),
    }:
        raise ValueError(
            "highest-college-year full-body cohort changed: "
            f"{highest_college_year_full_body_fields!r}"
        )
    if (
        school_years_outside_us_fields,
        len(school_years_outside_us_contexts),
    ) != (2, 2):
        raise ValueError(
            "school-years-outside-US cohort changed: "
            f"{school_years_outside_us_fields}, "
            f"{len(school_years_outside_us_contexts)}"
        )
    if dict(education_title_negative_controls) != {
        "calendar_year": 2,
        "grade_or_year_attending": 2,
    }:
        raise ValueError(
            "education title negative controls changed: "
            f"{education_title_negative_controls!r}"
        )
    if last_year_miles_fields != 1:
        raise ValueError(
            f"last-year miles cohort changed: {last_year_miles_fields}"
        )
    if number_of_times_selector_fields != 72:
        raise ValueError(
            "NUMBER OF TIMES selector cohort changed: "
            f"{number_of_times_selector_fields}"
        )
    if year_to_year_count_fields != 3:
        raise ValueError(
            "year-to-year change count cohort changed: "
            f"{year_to_year_count_fields}"
        )
    expected_multi_positive_field_keys = {
        (1968, "V150"),
        (1968, "V203"),
        (1968, "V223"),
        (1968, "V225"),
        (1968, "V235"),
        (1968, "V236"),
        (1969, "V556"),
        (1969, "V658"),
        (1969, "V659"),
        (1981, "V8027"),
        (2003, "ER23274"),
        (2007, "ER40408"),
        (2009, "ER46381"),
        (2011, "ER47619"),
        (2011, "ER51742"),
    }
    expected_multi_positive_reasons = {
        "exact_output_label_names_unit": 2,
        "how_many_direct_count_denotation": 5,
        "how_many_directly_governs_unit_noun": 2,
        "later_direct_count_question_title_denotation": 3,
        "later_direct_weeks_title_denotation": 3,
        "later_typical_week_hours_title_denotation": 4,
        "nominal_count_title_denotation": 2,
        "title_names_hours_per_week": 3,
        "unmarked_count_output_title_denotation": 2,
        "wrapped_alternative_days_title_denotation": 8,
    }
    if (
        (er47619_fields, multi_positive_fields) != (1, 15)
        or multi_positive_field_keys != expected_multi_positive_field_keys
        or dict(multi_positive_multiplicities) != {2: 12, 3: 2, 4: 1}
        or dict(multi_positive_units)
        != {
            "count": 12,
            "day": 8,
            "hour_per_week": 7,
            "week": 7,
        }
        or dict(multi_positive_reasons) != expected_multi_positive_reasons
    ):
        raise ValueError(
            "multi-positive selector census changed: "
            f"ER47619={er47619_fields}, all={multi_positive_fields}, "
            f"keys={multi_positive_field_keys!r}, "
            f"multiplicity={multi_positive_multiplicities!r}, "
            f"units={multi_positive_units!r}, reasons="
            f"{multi_positive_reasons!r}"
        )
    if (
        unique_unit_selector_counts["hour"],
        quantity_selector_counts["hour"],
        categorical_hour_selector_count,
    ) != (195, 118, 77):
        raise ValueError(
            "hour selector partition changed: "
            f"{unique_unit_selector_counts['hour']}, "
            f"{quantity_selector_counts['hour']}, "
            f"{categorical_hour_selector_count}"
        )
    if dict(nonterminal_semantic_components) != {
        "TIME UNIT": 11,
        "MONTH": 6,
        "YEAR": 6,
    }:
        raise ValueError(
            "nonterminal semantic selector partition changed: "
            f"{nonterminal_semantic_components!r}"
        )
    if semantic_component_dedup_regressions != {
        field_id: 1 for field_id in SEMANTIC_COMPONENT_DEDUP_REGRESSIONS
    }:
        raise ValueError(
            "semantic component dedup regression cohort changed: "
            f"{semantic_component_dedup_regressions!r}"
        )
    if (
        paid_extra_hours_yes_no_fields,
        paid_extra_hours_yes_no_candidates,
    ) != (62, 186):
        raise ValueError(
            "paid-extra-hours Boolean cohort changed: "
            f"{paid_extra_hours_yes_no_fields} fields, "
            f"{paid_extra_hours_yes_no_candidates} candidates"
        )
    expected_paid_extra_hours_yes_no_candidate_decisions = {
        (
            "bounded",
            "nominal_hour_token",
            None,
            "explicit_no_whole_domain_denotation",
            "conditional_paid_extra_hours_yes_no_input",
        ): 124,
        (
            "bounded",
            "nominal_week_token",
            None,
            "explicit_no_whole_domain_denotation",
            "conditional_paid_extra_hours_yes_no_input",
        ): 62,
    }
    paid_extra_hours_yes_no_field_key_digest = hashlib.sha256(
        "".join(
            f"{wave}\t{field}\n"
            for wave, field in sorted(paid_extra_hours_yes_no_field_keys)
        ).encode("utf-8")
    ).hexdigest()
    paid_extra_hours_yes_no_context_digest = hashlib.sha256(
        "".join(
            f"{value}\n" for value in sorted(paid_extra_hours_yes_no_contexts)
        ).encode("utf-8")
    ).hexdigest()
    if (
        dict(paid_extra_hours_yes_no_candidate_decisions)
        != expected_paid_extra_hours_yes_no_candidate_decisions
        or paid_extra_hours_yes_no_field_key_digest
        != "d8394af5a24f1673116b425a4ac75a570f3497cfe03b484ffc80236ae1af9a2d"
        or len(paid_extra_hours_yes_no_contexts) != 19
        or paid_extra_hours_yes_no_context_digest
        != "ce3fe977b9284e1cd1482c05e177c4cad7633d8d5da24d2b71a6b488dce86a15"
        or dict(paid_extra_hours_yes_no_transition_families)
        != {
            ("baseline", "nominal_hour_token"): 78,
            ("baseline", "nominal_week_token"): 62,
            ("first_question", "nominal_hour_token"): 46,
        }
    ):
        raise ValueError(
            "paid-extra-hours Boolean per-start partition changed: "
            f"{paid_extra_hours_yes_no_candidate_decisions!r} "
            f"{paid_extra_hours_yes_no_transition_families!r} "
            f"{paid_extra_hours_yes_no_field_key_digest} "
            f"{len(paid_extra_hours_yes_no_contexts)}/"
            f"{paid_extra_hours_yes_no_context_digest}"
        )

    unknown = candidate_occurrences - sum(occurrence_counts.values())
    if unknown:
        raise ValueError(f"unadjudicated title occurrences: {unknown}")
    if (candidate_occurrences, matched_fields) != (80_306, 51_957):
        raise ValueError(
            "final title candidate census changed: "
            f"{candidate_occurrences}/{matched_fields}"
        )
    expected_cross_lf_compound_families = {
        "dollar_amount": 8,
        "dollars_per_month_or_year": 96,
        "hours_per_week": 64,
        "how_many_count_marker": 1,
        "in_dollars": 11,
        "number_in_family_unit_marker": 18,
        "number_of_count_marker": 6,
        "number_of_years": 1,
        "per_hour_rate_phrase": 8,
        "per_month_rate_phrase": 22,
        "per_week_rate_phrase": 21,
    }
    expected_cross_lf_primary_delegation_fields = {
        (1982, "V8346"),
        (1984, "V11072"),
        (1985, "V12433"),
        (1986, "V13672"),
        (1987, "V14719"),
        (1988, "V16194"),
    }
    expected_cross_lf_reference_defeat_fields = {
        (1993, "V21702"),
        (1994, "ER3075"),
        (1995, "ER6074"),
        (1996, "ER8171"),
        (1997, "ER11065"),
        (1999, "ER14284"),
        (2001, "ER18416"),
        (2003, "ER21681"),
        (2005, "ER25683"),
        (2007, "ER36701"),
        (2009, "ER42708"),
        (2011, "ER48024"),
        (2013, "ER53721"),
        (2015, "ER60736"),
        (2017, "ER66783"),
        (2019, "ER72787"),
        (2021, "ER78864"),
        (2023, "ER82857"),
    }
    if (
        production_cross_lf_candidate_occurrences != 2
        or len(production_cross_lf_candidate_fields) != 2
        or dict(production_cross_lf_dispositions) != {"W": 2}
        or production_cross_lf_positive_fields
        != {(1968, "V324"), (2021, "ER81270")}
        or cross_lf_raw_compound_occurrences != 368
        or cross_lf_raw_compound_occurrences - cross_lf_compound_occurrences
        != 112
        or cross_lf_compound_occurrences != 256
        or len(cross_lf_compound_fields) != 227
        or dict(cross_lf_compound_families)
        != expected_cross_lf_compound_families
        or dict(cross_lf_compound_boundaries)
        != {"bounded_header": 118, "full_body": 138}
        or dict(cross_lf_compound_dispositions) != {"N": 254, "W": 2}
        or dict(cross_lf_compound_groundings)
        != {
            "contained_production_starts_explicitly_defeated": 230,
            "delegated_to_primary_statement_grammar": 6,
            "exact_production_title_start": 2,
            "referenced_other_field_not_field_denotation": 18,
        }
        or cross_lf_primary_delegation_fields
        != expected_cross_lf_primary_delegation_fields
        or cross_lf_reference_defeat_fields
        != expected_cross_lf_reference_defeat_fields
        or cross_lf_compound_positive_fields
        != {(1968, "V324"), (2021, "ER81270")}
        or cross_lf_hours_per_week_component_occurrences != 128
        or dict(cross_lf_hours_per_week_component_reasons)
        != {
            "delegated_to_primary_statement_grammar": 40,
            "instruction_threshold_table_or_subrange_defeat": 88,
        }
    ):
        raise ValueError(
            "cross-LF title candidate census changed: "
            f"production={production_cross_lf_candidate_occurrences}/"
            f"{len(production_cross_lf_candidate_fields)} "
            f"{production_cross_lf_dispositions!r}; generalized="
            f"{cross_lf_raw_compound_occurrences}->"
            f"{cross_lf_compound_occurrences}/"
            f"{len(cross_lf_compound_fields)} "
            f"{cross_lf_compound_families!r} "
            f"{cross_lf_compound_boundaries!r} "
            f"{cross_lf_compound_dispositions!r} "
            f"{cross_lf_compound_groundings!r} "
            f"primary={cross_lf_primary_delegation_fields!r} "
            f"references={cross_lf_reference_defeat_fields!r} "
            f"hours/week={cross_lf_hours_per_week_component_occurrences} "
            f"{cross_lf_hours_per_week_component_reasons!r}"
        )

    frozen_output_label_endings = tuple(output_label_endings)
    if (
        len(frozen_output_label_endings) != 21
        or len(canonical_json_bytes(frozen_output_label_endings)) != 2_425
        or canonical_sha256(frozen_output_label_endings)
        != OUTPUT_LABEL_ENDING_ADJUDICATION_SHA256
        or sum(row[5] for row in frozen_output_label_endings) != 2
    ):
        raise ValueError(
            "standalone output-label ending adjudication changed: "
            f"{len(frozen_output_label_endings)} rows, "
            f"{len(canonical_json_bytes(frozen_output_label_endings))} bytes, "
            f"{canonical_sha256(frozen_output_label_endings)}, "
            f"qualifying={sum(row[5] for row in frozen_output_label_endings)}"
        )

    frozen_currency_default_removals = tuple(currency_default_removals)
    currency_default_removed_fields = _removed_field_projection(
        tuple(denominator_field_keys), frozen_currency_default_removals
    )
    currency_default_removal_counts = Counter(
        false_class
        for _wave, _field_id, false_class in currency_default_removals
    )
    if (
        len(currency_default_removals) != 209
        or len(currency_default_removed_fields) != 206
        or {
            key: count
            for key, count in Counter(
                (wave, field_id)
                for wave, field_id, _false_class in currency_default_removals
            ).items()
            if count > 1
        }
        != {
            (1969, "V647"): 2,
            (1969, "V663"): 2,
            (1969, "V667"): 2,
        }
        or dict(currency_default_removal_counts)
        != {
            "hourly-money": 80,
            "monthly-money": 57,
            "money-question/per-hour": 37,
            "per-week-money": 3,
            "unmarked-amount/hour": 6,
            "yearly-money": 26,
        }
        or len(canonical_json_bytes(currency_default_removed_fields)) != 3_339
        or canonical_sha256(currency_default_removed_fields)
        != CURRENCY_DEFAULT_REMOVED_FIELD_PROJECTION_SHA256
    ):
        raise ValueError(
            "currency-default removal projection changed: "
            f"{len(currency_default_removals)} starts, "
            f"{len(currency_default_removed_fields)} fields, "
            f"{currency_default_removal_counts!r}, "
            f"{len(canonical_json_bytes(currency_default_removed_fields))} "
            f"bytes, {canonical_sha256(currency_default_removed_fields)}"
        )

    frozen = tuple(authority)
    rebuilt, overlay_stats = _rebuild_segment_authority(
        _iter_rows(args.raw_input), decisions
    )
    if not args.audit_only:
        TITLE_MODULE.write_text(
            _render_title_module(
                frozen,
                frozen_output_label_endings,
                frozen_currency_default_removals,
                currency_default_removed_fields,
            )
        )
        _replace_segment_authority(
            rebuilt, overlay_stats["context_varying_segment_start_count"]
        )

    candidate_table_metadata: dict[str, Any] = {}
    if candidate_table_stream is not None:
        assert candidate_table_stage is not None
        candidate_table_stream.flush()
        os.fsync(candidate_table_stream.fileno())
        candidate_table_stream.close()
        candidate_table_metadata = {
            "candidate_table_path": str(args.candidate_table),
            "candidate_table_byte_count": candidate_table_stage.stat().st_size,
            "candidate_table_sha256": _file_sha256(candidate_table_stage),
            "candidate_table_row_count": field_count,
        }

    def grouped(
        counter: Counter[tuple[str, str | None, str, str]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "family": family,
                "unit": unit,
                "disposition": disposition,
                "reason": reason,
                "count": count,
            }
            for (family, unit, disposition, reason), count in sorted(
                counter.items(),
                key=lambda item: (
                    item[0][0],
                    item[0][1] or "",
                    item[0][2],
                    item[0][3],
                ),
            )
        ]

    def grouped_by_boundary(
        counter: Counter[tuple[str, str, str | None, str, str]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "boundary": boundary,
                "family": family,
                "unit": unit,
                "disposition": disposition,
                "reason": reason,
                "count": count,
            }
            for (
                boundary,
                family,
                unit,
                disposition,
                reason,
            ), count in sorted(
                counter.items(),
                key=lambda item: (
                    item[0][0],
                    item[0][1],
                    item[0][2] or "",
                    item[0][3],
                    item[0][4],
                ),
            )
        ]

    def grouped_by_category_boundary(
        counter: Counter[tuple[str, str, str, str | None, str, str]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "category": category,
                "boundary": boundary,
                "family": family,
                "unit": unit,
                "disposition": disposition,
                "reason": reason,
                "count": count,
            }
            for (
                category,
                boundary,
                family,
                unit,
                disposition,
                reason,
            ), count in sorted(
                counter.items(),
                key=lambda item: (
                    item[0][0],
                    item[0][1],
                    item[0][2],
                    item[0][3] or "",
                    item[0][4],
                    item[0][5],
                ),
            )
        ]

    report = {
        "audit_only": args.audit_only,
        "field_count": field_count,
        "raw_input_relation_sha256": input_relation_sha256,
        "output_label_ending_adjudication_row_count": len(
            frozen_output_label_endings
        ),
        "output_label_ending_adjudication_byte_count": len(
            canonical_json_bytes(frozen_output_label_endings)
        ),
        "output_label_ending_adjudication_sha256": canonical_sha256(
            frozen_output_label_endings
        ),
        "currency_default_removed_start_count": len(currency_default_removals),
        "currency_default_removed_field_count": len(
            currency_default_removed_fields
        ),
        "currency_default_removed_class_counts": dict(
            sorted(currency_default_removal_counts.items())
        ),
        "currency_default_removed_field_projection_byte_count": len(
            canonical_json_bytes(currency_default_removed_fields)
        ),
        "currency_default_removed_field_projection_sha256": canonical_sha256(
            currency_default_removed_fields
        ),
        "structural_selector_occurrence_count": (
            structural_selector_occurrences
        ),
        "structural_selector_field_count": structural_selector_fields,
        "structural_selector_kind_counts": dict(
            sorted(structural_selector_kinds.items())
        ),
        "structural_selector_label_line_counts": dict(
            sorted(structural_selector_label_lines.items())
        ),
        "structural_selector_line8_keys": structural_selector_line8_keys,
        "singleton_direct_selector_occurrence_count": (
            singleton_direct_occurrences
        ),
        "singleton_direct_selector_field_count": len(singleton_direct_fields),
        "singleton_nested_response_occurrence_count": (
            singleton_nested_response_occurrences
        ),
        "singleton_nested_response_field_count": len(
            singleton_nested_response_fields
        ),
        "singleton_unit_selector_occurrence_count": sum(
            singleton_unit_signatures.values()
        ),
        "singleton_unit_selector_field_count": len(singleton_unit_fields),
        "singleton_unit_selector_counts": dict(
            sorted(singleton_unit_counts.items())
        ),
        "singleton_unit_selector_signature_counts": [
            {
                "kind": kind,
                "label": label,
                "occurrence_count": count,
            }
            for (kind, label), count in sorted(
                singleton_unit_signatures.items()
            )
        ],
        "singleton_response_selector_counts": dict(
            sorted(singleton_response_counts.items())
        ),
        "singleton_nonsemantic_direct_occurrence_count": (
            singleton_nonsemantic_direct_occurrences
        ),
        "structural_excluded_lookalike_occurrence_count": (
            food_body_code_occurrences
            + body_instruction_occurrences
            + editorial_note_occurrences
            + separator_next_line_occurrences
        ),
        "header_physical_line_counts": dict(
            sorted(header_physical_line_counts.items())
        ),
        "food_body_code_excluded_occurrence_count": (
            food_body_code_occurrences
        ),
        "food_body_code_excluded_field_count": len(food_body_code_fields),
        "food_body_code_excluded_keys": sorted(food_body_code_fields),
        "body_instruction_excluded_occurrence_count": (
            body_instruction_occurrences
        ),
        "body_instruction_excluded_field_count": len(body_instruction_fields),
        "body_instruction_excluded_keys": sorted(body_instruction_fields),
        "editorial_note_excluded_occurrence_count": (
            editorial_note_occurrences
        ),
        "editorial_note_excluded_field_count": len(editorial_note_fields),
        "editorial_note_excluded_keys": sorted(editorial_note_fields),
        "separator_next_line_excluded_occurrence_count": (
            separator_next_line_occurrences
        ),
        "separator_next_line_excluded_field_count": len(
            separator_next_line_fields
        ),
        "separator_next_line_excluded_keys": sorted(
            separator_next_line_fields
        ),
        "external_unit_selector_occurrence_count": sum(
            external_unit_selector_counts.values()
        ),
        "external_unit_selector_field_count": len(
            external_unit_selector_fields
        ),
        "external_unit_selector_contained_count": (
            external_unit_selector_contained
        ),
        "external_unit_selector_counts": dict(
            sorted(external_unit_selector_counts.items())
        ),
        "external_unit_selector_line_counts": dict(
            sorted(external_unit_selector_lines.items())
        ),
        "raw_physical_unit_selector_occurrence_count": sum(
            raw_physical_unit_selector_counts.values()
        ),
        "raw_physical_unit_selector_field_count": len(
            raw_physical_unit_selector_fields
        ),
        "raw_physical_unit_selector_contained_count": (
            raw_physical_unit_selector_contained
        ),
        "raw_physical_unit_selector_counts": dict(
            sorted(raw_physical_unit_selector_counts.items())
        ),
        "raw_response_selector_counts": dict(
            sorted(raw_response_selector_counts.items())
        ),
        "raw_response_selector_line_counts": {
            label: {
                str(line): count
                for (line_label, line), count in sorted(
                    raw_response_selector_lines.items()
                )
                if line_label == label
            }
            for label in sorted(raw_response_selector_counts)
        },
        "unique_unit_selector_counts": dict(
            sorted(unique_unit_selector_counts.items())
        ),
        "quantity_selector_counts": dict(
            sorted(quantity_selector_counts.items())
        ),
        "categorical_hour_selector_count": (categorical_hour_selector_count),
        "nonterminal_semantic_component_counts": dict(
            sorted(nonterminal_semantic_components.items())
        ),
        "semantic_component_dedup_regression_counts": dict(
            sorted(semantic_component_dedup_regressions.items())
        ),
        "calendar_context_counts": calendar_context_counts,
        "calendar_field_counts": dict(stable_calendar_fields),
        "calendar_context_sha_count": len(stable_calendar_shas),
        "calendar_context_sha256": calendar_digest,
        "age_year_selector_field_count": age_year_selector_fields,
        "age_year_selector_context_count": len(age_year_selector_contexts),
        "legacy_age_year_selector_field_count": (
            legacy_age_year_selector_fields
        ),
        "legacy_age_year_selector_context_count": len(
            legacy_age_year_selector_contexts
        ),
        "overtime_amount_hour_field_count": overtime_amount_fields,
        "overtime_time_unit_field_count": overtime_time_unit_fields,
        "overtime_candidate_decision_counts": (
            grouped_by_category_boundary(overtime_candidate_decisions)
        ),
        "dollars_worth_amount_field_count": dollars_worth_amount_fields,
        "dollars_worth_time_unit_field_count": (
            dollars_worth_time_unit_fields
        ),
        "dollars_worth_context_count": len(dollars_worth_contexts),
        "dollars_worth_body_grounded_field_count": (
            dollars_worth_body_grounded_fields
        ),
        "dollars_worth_candidate_decision_counts": (
            grouped_by_category_boundary(dollars_worth_candidate_decisions)
        ),
        "dollars_worth_field_keys": {
            category: sorted(field_keys)
            for category, field_keys in sorted(
                dollars_worth_field_keys.items()
            )
        },
        "dollars_worth_full_body_field_keys": sorted(
            dollars_worth_full_body_fields
        ),
        "pension_selector_field_counts": dict(
            sorted(pension_selector_fields.items())
        ),
        "pension_selector_context_counts": dict(
            sorted(pension_context_counts.items())
        ),
        "pension_candidate_decision_counts": (
            grouped_by_category_boundary(pension_candidate_decisions)
        ),
        "experience_selector_field_count": experience_fields,
        "experience_selector_context_count": len(experience_contexts),
        "experience_selector_unit_counts": dict(experience_units),
        "experience_selector_context_counts_by_unit": dict(
            sorted(experience_context_counts.items())
        ),
        "experience_selector_context_sha256": experience_context_digest,
        "experience_body_defeat_field_count": experience_nonselector_fields,
        "experience_body_defeat_context_count": len(
            experience_nonselector_contexts
        ),
        "experience_body_defeat_context_sha256": (
            experience_nonselector_context_digest
        ),
        "experience_body_defeat_candidate_decision_counts": (
            grouped_by_boundary(experience_nonselector_candidate_decisions)
        ),
        "experience_body_defeat_context_field_keys": {
            sha: sorted(field_keys)
            for sha, field_keys in sorted(
                experience_nonselector_context_fields.items()
            )
        },
        "typical_week_time_use_field_count": typical_week_time_use_fields,
        "typical_week_time_use_context_count": len(
            typical_week_time_use_contexts
        ),
        "typical_week_time_use_person_counts": dict(
            sorted(typical_week_time_use_people.items())
        ),
        "typical_week_candidate_decision_counts": grouped_by_boundary(
            typical_week_candidate_decisions
        ),
        "typical_week_reference_without_article_field_keys": sorted(
            typical_week_reference_without_article_fields
        ),
        "highest_college_year_field_count": highest_college_year_fields,
        "highest_college_year_context_count": len(
            highest_college_year_contexts
        ),
        "highest_college_year_body_grounded_field_count": (
            highest_college_year_body_grounded_fields
        ),
        "highest_college_year_candidate_decision_counts": (
            grouped_by_boundary(highest_college_year_candidate_decisions)
        ),
        "highest_college_year_full_body_field_keys": sorted(
            highest_college_year_full_body_fields
        ),
        "school_years_outside_us_field_count": school_years_outside_us_fields,
        "school_years_outside_us_context_count": len(
            school_years_outside_us_contexts
        ),
        "education_title_negative_control_counts": dict(
            sorted(education_title_negative_controls.items())
        ),
        "pre_round3_candidate_occurrence_count": (
            baseline_candidate_occurrences
        ),
        "pre_round3_candidate_field_count": baseline_candidate_fields,
        "first_question_candidate_occurrence_count": (
            first_question_candidate_occurrences
        ),
        "first_question_candidate_field_count": len(
            first_question_candidate_fields
        ),
        "first_question_candidate_family_counts": dict(
            sorted(first_question_candidate_families.items())
        ),
        "first_question_candidate_disposition_counts": dict(
            sorted(first_question_dispositions.items())
        ),
        "first_question_positive_reason_counts": dict(
            sorted(first_question_positive_reasons.items())
        ),
        "first_question_positive_field_keys": sorted(
            first_question_positive_fields
        ),
        "singleton_delta_candidate_occurrence_count": (
            singleton_delta_candidate_occurrences
        ),
        "singleton_delta_candidate_field_count": len(
            singleton_delta_candidate_fields
        ),
        "singleton_delta_candidate_family_counts": dict(
            sorted(singleton_delta_candidate_families.items())
        ),
        "singleton_delta_candidate_disposition_counts": dict(
            sorted(singleton_delta_dispositions.items())
        ),
        "singleton_delta_positive_reason_counts": dict(
            sorted(singleton_delta_positive_reasons.items())
        ),
        "singleton_delta_positive_field_keys": sorted(
            singleton_delta_positive_fields
        ),
        "later_question_candidate_occurrence_count": (
            later_question_candidate_occurrences
        ),
        "later_question_candidate_field_count": len(
            later_question_candidate_fields
        ),
        "later_question_candidate_family_counts": dict(
            sorted(later_question_candidate_families.items())
        ),
        "later_question_candidate_disposition_counts": dict(
            sorted(later_question_dispositions.items())
        ),
        "later_question_positive_reason_counts": dict(
            sorted(later_question_positive_reasons.items())
        ),
        "later_question_positive_field_keys": sorted(
            later_question_positive_fields
        ),
        "question_line_suffix_candidate_occurrence_count": (
            question_line_suffix_candidate_occurrences
        ),
        "question_line_suffix_candidate_field_count": len(
            question_line_suffix_candidate_fields
        ),
        "question_line_suffix_candidate_family_counts": dict(
            sorted(question_line_suffix_candidate_families.items())
        ),
        "question_line_suffix_candidate_disposition_counts": dict(
            sorted(question_line_suffix_dispositions.items())
        ),
        "question_line_suffix_positive_reason_counts": dict(
            sorted(question_line_suffix_positive_reasons.items())
        ),
        "question_line_suffix_positive_field_keys": sorted(
            question_line_suffix_positive_fields
        ),
        "question_continuation_candidate_occurrence_count": (
            question_continuation_candidate_occurrences
        ),
        "question_continuation_candidate_field_count": len(
            question_continuation_candidate_fields
        ),
        "question_continuation_candidate_family_counts": dict(
            sorted(question_continuation_candidate_families.items())
        ),
        "question_continuation_candidate_disposition_counts": dict(
            sorted(question_continuation_dispositions.items())
        ),
        "full_body_candidate_occurrence_count": (
            full_body_candidate_occurrences
        ),
        "full_body_candidate_field_count": len(full_body_candidate_fields),
        "full_body_candidate_family_counts": dict(
            sorted(full_body_candidate_families.items())
        ),
        "full_body_candidate_disposition_counts": dict(
            sorted(full_body_dispositions.items())
        ),
        "full_body_positive_reason_counts": dict(
            sorted(full_body_positive_reasons.items())
        ),
        "full_body_negative_reason_counts": dict(
            sorted(full_body_negative_reasons.items())
        ),
        "full_body_positive_field_keys": sorted(full_body_positive_fields),
        "production_cross_lf_candidate_occurrence_count": (
            production_cross_lf_candidate_occurrences
        ),
        "production_cross_lf_candidate_field_count": len(
            production_cross_lf_candidate_fields
        ),
        "production_cross_lf_candidate_disposition_counts": dict(
            sorted(production_cross_lf_dispositions.items())
        ),
        "production_cross_lf_positive_field_keys": sorted(
            production_cross_lf_positive_fields
        ),
        "cross_lf_raw_compound_occurrence_count": (
            cross_lf_raw_compound_occurrences
        ),
        "cross_lf_nested_compound_occurrence_count": (
            cross_lf_raw_compound_occurrences - cross_lf_compound_occurrences
        ),
        "cross_lf_maximal_compound_occurrence_count": (
            cross_lf_compound_occurrences
        ),
        "cross_lf_maximal_compound_field_count": len(cross_lf_compound_fields),
        "cross_lf_maximal_compound_family_counts": dict(
            sorted(cross_lf_compound_families.items())
        ),
        "cross_lf_maximal_compound_boundary_counts": dict(
            sorted(cross_lf_compound_boundaries.items())
        ),
        "cross_lf_maximal_compound_disposition_counts": dict(
            sorted(cross_lf_compound_dispositions.items())
        ),
        "cross_lf_maximal_compound_grounding_counts": dict(
            sorted(cross_lf_compound_groundings.items())
        ),
        "cross_lf_primary_delegation_field_keys": sorted(
            cross_lf_primary_delegation_fields
        ),
        "cross_lf_reference_defeat_field_keys": sorted(
            cross_lf_reference_defeat_fields
        ),
        "cross_lf_maximal_compound_positive_field_keys": sorted(
            cross_lf_compound_positive_fields
        ),
        "cross_lf_hours_per_week_component_occurrence_count": (
            cross_lf_hours_per_week_component_occurrences
        ),
        "cross_lf_hours_per_week_component_reason_counts": dict(
            sorted(cross_lf_hours_per_week_component_reasons.items())
        ),
        "last_year_miles_field_count": last_year_miles_fields,
        "last_year_miles_candidate_decisions": dict(
            sorted(last_year_miles_candidate_decisions.items())
        ),
        "number_of_times_selector_field_count": (
            number_of_times_selector_fields
        ),
        "year_to_year_count_field_count": year_to_year_count_fields,
        "er47619_field_count": er47619_fields,
        "er47619_week_decisions": er47619_week_decisions,
        "multiple_positive_title_field_count": multi_positive_fields,
        "multiple_positive_title_field_keys": sorted(
            multi_positive_field_keys
        ),
        "multiple_positive_title_multiplicity_counts": dict(
            sorted(multi_positive_multiplicities.items())
        ),
        "multiple_positive_title_unit_counts": dict(
            sorted(multi_positive_units.items())
        ),
        "multiple_positive_title_reason_counts": dict(
            sorted(multi_positive_reasons.items())
        ),
        "matched_field_count": matched_fields,
        "candidate_occurrence_count": candidate_occurrences,
        "positive_candidate_occurrence_count": positive_candidate_occurrences,
        "negative_candidate_occurrence_count": (
            candidate_occurrences - positive_candidate_occurrences
        ),
        "positive_field_count": positive_fields,
        "positive_field_count_beyond_eight_witnesses": positive_fields - 8,
        "authority_context_count": len(frozen),
        "positive_authority_context_count": sum(
            row[7] == "whole_domain_denotation" for row in frozen
        ),
        "negative_authority_context_count": sum(
            row[7] != "whole_domain_denotation" for row in frozen
        ),
        "unadjudicated_occurrence_count": 0,
        "continuation_header_count": continuation_headers,
        "continuation_output_label_field_count": sum(
            continuation_output_labels.values()
        ),
        "continuation_output_label_counts": dict(
            sorted(continuation_output_labels.items())
        ),
        "continuation_line2_candidate_occurrence_count": (
            continuation_line2_candidate_occurrences
        ),
        "compiled_continuation_without_line1_unit_count": len(
            compiled_continuation_without_line1_unit
        ),
        "compiled_continuation_without_line1_unit_keys": (
            compiled_continuation_without_line1_unit
        ),
        "paid_extra_hours_yes_no_field_count": (
            paid_extra_hours_yes_no_fields
        ),
        "paid_extra_hours_yes_no_candidate_count": (
            paid_extra_hours_yes_no_candidates
        ),
        "paid_extra_hours_yes_no_candidate_decision_counts": (
            grouped_by_boundary(paid_extra_hours_yes_no_candidate_decisions)
        ),
        "paid_extra_hours_yes_no_transition_family_counts": [
            {
                "stage": stage,
                "family": family,
                "count": count,
            }
            for (stage, family), count in sorted(
                paid_extra_hours_yes_no_transition_families.items()
            )
        ],
        "paid_extra_hours_yes_no_field_keys": sorted(
            paid_extra_hours_yes_no_field_keys
        ),
        "paid_extra_hours_yes_no_field_key_sha256": (
            paid_extra_hours_yes_no_field_key_digest
        ),
        "paid_extra_hours_yes_no_context_count": len(
            paid_extra_hours_yes_no_contexts
        ),
        "paid_extra_hours_yes_no_context_sha256": (
            paid_extra_hours_yes_no_context_digest
        ),
        "title_authority_sha256": canonical_sha256(frozen),
        "segment_start_authority_sha256": canonical_sha256(rebuilt),
        "segment_start_row_count": len(rebuilt),
        "segment_start_count": sum(
            len(vector) for _segment, vector in rebuilt
        ),
        "context_reason_unit_family": grouped(context_counts),
        "occurrence_reason_unit_family": grouped(occurrence_counts),
        **candidate_table_metadata,
        **overlay_stats,
    }
    usage = resource.getrusage(resource.RUSAGE_SELF)
    report["generator_max_rss_bytes"] = int(
        usage.ru_maxrss if sys.platform == "darwin" else usage.ru_maxrss * 1024
    )
    _atomic_write_text(
        args.report,
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )
    if candidate_table_stage is not None:
        os.replace(candidate_table_stage, args.candidate_table)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
