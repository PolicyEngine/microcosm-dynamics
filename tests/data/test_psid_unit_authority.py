"""Tests for the Amendment 10 (§24) unit-authority machinery."""

from __future__ import annotations

import pytest

import populace_dynamics.data.psid_unit_authority as unit_authority
from populace_dynamics.data.psid_unit_authority import (
    ACTUAL_CANDIDATES,
    ACTUAL_CLAUSE_TABLE,
    ACTUAL_NO_DENOTATION_CANDIDATES,
    ANCHORS,
    ARTIFACT_PARTITION,
    CLAUSE_TABLE,
    COMPILED_TERMINALS,
    FAILURE_TERMINALS,
    NO_UNIT,
    TERMINAL_ORDER,
    UNIT_ABSENT_RESOLUTION_REASON,
    UNIT_VOCABULARY,
    actual_candidate_disposition,
    actual_candidate_table,
    actual_candidates,
    artifact_of_position,
    canonical_json_bytes,
    canonical_sha256,
    clause_occurrences,
    coding_candidate_disposition,
    coding_candidate_table,
    coding_candidates,
    denotation_candidate_disposition,
    denotation_candidate_occurrence_identity,
    denotation_candidate_overselected_count,
    denotation_candidate_start_count,
    denotation_candidate_start_partition,
    denotation_candidate_table,
    denotation_candidate_unselected_count,
    denotation_candidates,
    description_statements,
    extract_statements,
    failure_reason_rows,
    field_unit,
    normalize_description,
    segment_start_authority_table,
    statement_anchor,
    statement_disposition,
    statement_predicate,
    statement_table,
    successor_census,
    successor_terminal,
)
from populace_dynamics.data.psid_unit_predicate_authority import (
    CODING_START_AUTHORITY,
    PREDICATE_AUTHORITY,
    SEGMENT_START_AUTHORITY,
)

COMPILED = "compiled_source_numeric_grammar"
PARTIAL_RANGE = "compiled_source_numeric_grammar_partial_range_exact_replay"
INCOMPLETE = "incomplete_source_numeric_authority"
UNSUPPORTED = "unsupported_source_numeric_format"
CONFLICTING = "conflicting_source_numeric_format"
VALUE_CODE_ONLY = "value_code_domain_no_numeric_grammar"
RANGE_UNESTABLISHED = "value_code_range_physical_rendering_unestablished"

DOLLARS = "The values for this variable represent dollars and cents."
PER_HOUR = "The values for this variable represent dollars and cents per hour."
HOURS = (
    "The values for this variable represent the actual number of hours per "
    'week Wife/"Wife" worked.'
)

RAW_V100 = (
    "5. Length of Interview\n"
    "Code actual number of MINUTES (e.g. 1 hour and 10 minutes - 70 minutes)."
)
RAW_V121 = (
    "B3. Is he/she in school? (Code number of children in FU in school and "
    "living at home)\n(exclude in-laws)"
)
RAW_V155 = (
    "C20. (If Yes) What kinds of things have you done on your car(s) in the "
    "last year?\nPRIORITY CODE - highest number."
)
RAW_V194 = (
    "Thumbnail sketch evidence on housing\n"
    "PRIORITY CODE the lowest number applicable."
)
RAW_V229 = (
    "F46. About how much did you make per hour for this?\n"
    "(Code dollars and cents per hour.)"
)
RAW_V228 = (
    "F43. What did you do?\n"
    "(Code same as other occupation code (Col. 12). If two or more jobs, "
    "code the one with the\nlowest code number (highest status)"
)
RAW_V373 = (
    "Average Value Per Room in Dwelling Unit\n"
    "For Homeowners: V5 House Value / V102 Number of rooms in DU\n"
    "*For Renters: 10 x V11 Annual Rent / V102 Number of rooms in DU\n"
    "*For those who neither own nor rent: 10 x V12 Rental Value / V102     "
    "Number of rooms in DU\n"
    "xxxx. Coded in Dollars\n"
    "*(Calculated value assumes that value of DU is approximately 10 times "
    "its annual rental\nvalue)"
)
RAW_V418 = (
    "Housing and Neighborhood Quality Redone (Revised V387)\n"
    "Owns home V103 = 1\n"
    "Lives 5-30 miles from center of city of 50,000 or more V189 = 2, 3\n"
    "Single Family home V190 = 1\n"
    "Neighborhood of Single Family Houses V192 = 2\n"
    "Value per room Value - (10 x rent for non-owners) > 2000   V374=4-8\n"
    "Actual - Required rooms   V381 = 5 - 9\n"
    "No visible defects V194 = 5\n"
    "OMITS: Car Lack Felt Share\n"
    "Dwelling (Hard to Determine)\n"
    "Changes: Distance to Center, Surplus of Rooms"
)
RAW_V494 = (
    "Annual food needs standard\n"
    "Based on the USDA Low Cost plan estimates of the weekly food costs, "
    "according to the table\n"
    "below (reproduced from Family Economics Review March, 1967), summed "
    "for the family and\n"
    "converted to an annual amount and adjusted for economies of scale by "
    "USDA rules as\nfollows:\n"
    "Single person-add 20%\nTwo persons-add 10%\nThree persons-add 5%\n"
    "Four persons-no change\nFive persons-deduct 5%\n"
    "Six or more persons-deduct 10%\n"
    "INDIVIDUAL FOOD STANDARD (LOW COST)\n"
    "Under 4:Male=3.90\nUnder 4:Female=3.90\n"
    "4-6:Male=4.60\n4-6:Female=4.60\n"
    "7-9:Male=5.50\n7-9:Female=5.50\n"
    "10-12:Male=6.40\n10-12:Female=6.30\n"
    "13-15:Male=7.40\n13-15:Female=6.90\n"
    "16-20:Male=8.70\n16-20:Female=7.20\n"
    "21-35:Male=7.50\n21-35:Female=6.50\n"
    "36-55:Male=6.90\n36-55:Female=6.30\n"
    "56+:Male=6.30\n56+:Female=5.40\n"
    "(NOTE that the values for this variable are in 1967 dollars. This "
    "same standard will be\n"
    "used in both Waves I and II. Adjustments for inflation, etc. are left "
    "to users.)"
)
RAW_V2137 = "J1. Code number of things mentioned to J1"
RAW_V2192 = (
    "L25-27. (M9) Code Number of States or Countries in which R has lived "
    "including present\nlocation"
)
RAW_V2470 = (
    "Weekly Food Needs\n"
    "This variable's values are based on USDA Low-Cost Plan estimates of "
    "weekly food costs,\n"
    "according to the table below (reproduced from Family Economics "
    "Review, June 1967), summed\n"
    "for the family as it was at the time of the interview.\n"
    "INDIVIDUAL FOOD STANDARD (LOW COST)\n"
    "$3.90 for both males and females under age 4\n"
    "$4.60 for both males and females age 4-6\n"
    "$5.50 for both males and females age 7-9\n"
    "$6.40 for males age 10-12\n$6.30 for females age 10-12\n"
    "$7.40 for males age 13-15\n$6.90 for females age 13-15\n"
    "$8.70 for males age 16-20\n$7.20 for females age 16-20\n"
    "$7.50 for males age 21-35\n$6.50 for females age 21-35\n"
    "$6.90 for males age 36-55\n$6.30 for females age 36-55\n"
    "$6.30 for males age 56 and older\n"
    "$5.40 for females age 56 and older\n"
    "This same standard has been used in previous waves. Since the table is "
    "from 1967, values\n"
    "are in 1967 dollars. Adjustments for inflation, etc., are left to "
    "users.\n"
    "The actual weekly food needs in dollars and cents are coded here."
)
RAW_V4367 = (
    "Number of months used food stamps in 1975\n"
    "Code 1-11 for actual number of months used food stamps in 1975"
)
RAW_V4742 = "Length of Interview\nCode actual number of minutes"
RAW_V5453 = (
    "E13. How long have you been looking for work?\n"
    "Code actual number of weeks (01 - 98)"
)
RAW_V9378 = (
    "Annual 1983 Food Standard\n"
    "This variable is generated by multiplying the weekly food needs "
    "(V8853) by 52 and then\n"
    "making the following adjustments for economies of scale:\n"
    "+20% for one-person families\n+10% for two-person families\n"
    "+ 5% for three-person families\n"
    "no adjustment for four-person families\n"
    "- 5% for five-person families\n"
    "-10% for families with six or more persons\n"
    "The values represent the actual annual food standard in whole dollars "
    "for the 1983 family.\n"
    "Note that V8823 is based on a table from 1967, with 1967 dollar values."
)
RAW_ER55305 = (
    "H6k3. (Are/Is) (you/HEAD) currently in treatment for "
    "(your/his/her) cancer, in remission,\n"
    "or has it been cured?\n"
    "IF R says can't afford insurance to get treatment, are doing nothing, "
    "etc, ENTER: 4"
)

ROUND2_RAW_DESCRIPTIONS = (
    RAW_V100,
    RAW_V121,
    RAW_V155,
    RAW_V194,
    RAW_V228,
    RAW_V229,
    RAW_V373,
    RAW_V418,
    RAW_V494,
    RAW_V2137,
    RAW_V2192,
    RAW_V2470,
    RAW_V4367,
    RAW_V4742,
    RAW_V5453,
    RAW_V9378,
    RAW_ER55305,
)


# --------------------------------------------------------------------------
# Stage 1 — normalization
# --------------------------------------------------------------------------


def test_normalization_is_exactly_three_steps() -> None:
    assert normalize_description("a\nb") == "a b"
    assert normalize_description("a   b") == "a b"
    assert normalize_description("  a\n   b  ") == "a b"
    assert normalize_description(None) == ""


def test_normalization_preserves_case_punctuation_and_quotes() -> None:
    raw = "Wife's/\"Wife's\" PAY’ — A.B."
    assert normalize_description(raw) == raw


def test_normalization_does_not_fold_tabs_or_other_whitespace() -> None:
    # Only LF and U+0020 participate; the derivation already stripped
    # per-line leading and trailing tabs, so a surviving tab is content.
    assert normalize_description("a\tb") == "a\tb"
    assert normalize_description("\ta\t") == "\ta\t"
    assert normalize_description(" \ta\t ") == "\ta\t"
    assert normalize_description("\ra\r") == "\ra\r"
    assert normalize_description("\va\v") == "\va\v"
    assert normalize_description("\N{NO-BREAK SPACE}a\N{NO-BREAK SPACE}") == (
        "\N{NO-BREAK SPACE}a\N{NO-BREAK SPACE}"
    )


# --------------------------------------------------------------------------
# Stage 2 — statement extraction
# --------------------------------------------------------------------------


def test_statement_requires_a_space_or_text_start_before_the_anchor() -> None:
    assert extract_statements(DOLLARS) == (DOLLARS,)
    assert extract_statements("AMOUNT " + DOLLARS) == (DOLLARS,)
    # Glued on the left, so neither the capitalized opener nor the
    # lowercase one that would otherwise start at "values" can open.
    assert extract_statements("xvalues for this variable represent x.") == ()


def test_nested_anchor_cannot_open_a_second_statement() -> None:
    text = "The value for this variable represents dollars and cents."
    assert extract_statements(text) == (text,)
    assert statement_anchor(text) == "The value for this variable "


def test_terminator_ignores_an_interior_decimal_point() -> None:
    text = "The values for this variable represent 1.5 hours per week."
    assert extract_statements(text) == (text,)


def test_terminator_stops_at_the_first_period_before_a_space() -> None:
    text = "The values for this variable represent dollars. Something else."
    assert extract_statements(text) == (
        "The values for this variable represent dollars.",
    )


def test_unterminated_statement_runs_to_the_end_of_the_text() -> None:
    text = "The values for this variable represent dollars and cents"
    assert extract_statements(text) == (text,)


def test_two_statements_are_returned_in_text_order() -> None:
    text = f"{DOLLARS} {HOURS}"
    assert extract_statements(text) == (DOLLARS, HOURS)


def test_every_anchor_is_reachable() -> None:
    for anchor in ANCHORS:
        text = f"{anchor}dollars and cents."
        assert extract_statements(text) == (text,)


@pytest.mark.parametrize(
    "text",
    [
        "The actual weekly food needs in dollars and cents are coded here.",
        (
            "The code values represent the actual number of persons "
            "currently in the FU."
        ),
        (
            "The values represent the actual annual food standard in whole "
            "dollars for the 1983 family."
        ),
    ],
)
def test_omitted_denotation_families_are_selected(text: str) -> None:
    assert extract_statements(text) == (text,)
    assert statement_disposition(text)[0] is not None


def test_actual_residual_selector_covers_line_start_and_embedded_tail() -> (
    None
):
    description = (
        "Question text Actual number of weeks\n"
        "Actual dollars and cents per hour"
    )
    assert actual_candidates(description) == (
        "Actual number of weeks",
        "Actual dollars and cents per hour",
    )
    assert description_statements(description) == actual_candidates(
        description
    )


def test_actual_explicit_no_denotation_is_not_a_statement() -> None:
    candidate = "Actual - Required rooms   V381 = 5 - 9"
    assert candidate in actual_candidates(RAW_V418)
    assert actual_candidate_disposition(candidate) == "explicit_no_denotation"
    assert description_statements(RAW_V418) == ()
    assert field_unit(RAW_V418) == (None, "no_denotation_statement")


def test_actual_candidate_adjudication_is_closed_and_fail_closed() -> None:
    assert len(ACTUAL_CANDIDATES) == len(set(ACTUAL_CANDIDATES)) == 82
    assert ACTUAL_NO_DENOTATION_CANDIDATES < set(ACTUAL_CANDIDATES)
    assert (
        actual_candidate_disposition("Actual number of weeks")
        == "whole_domain_denotation"
    )


def test_exhaustive_candidate_selector_covers_lexemes_and_actual_lines() -> (
    None
):
    candidates = denotation_candidates(RAW_V4742)
    assert len(candidates) == denotation_candidate_start_count(RAW_V4742)
    assert candidates[0] == "Length of Interview Code actual number of minutes"
    assert "Code actual number of minutes" in candidates
    assert "minutes" in candidates
    assert denotation_candidate_unselected_count(RAW_V4742) == 0
    assert denotation_candidate_overselected_count(RAW_V4742) == 0
    assert (
        actual_candidate_disposition(
            "Actual - Required rooms = 2 or more (V891 EQ 5 - 8)"
        )
        == "explicit_no_denotation"
    )
    assert (
        actual_candidate_disposition("Actual furlongs per fortnight")
        == "unadjudicated_no_denotation"
    )
    assert (
        denotation_candidate_disposition(
            "A component represents a lookup value."
        )
        == "unadjudicated_context_free_candidate"
    )
    assert statement_disposition("Actual furlongs per fortnight") == (
        None,
        "unadjudicated_denotation_candidate",
    )


@pytest.mark.parametrize(
    ("description", "candidate", "statement", "unit"),
    [
        (
            RAW_V100,
            "Code actual number of MINUTES (e.g.",
            "Code actual number of MINUTES (e.g. 1 hour and 10 minutes - "
            "70 minutes).",
            "minute",
        ),
        (
            RAW_V121,
            "Code number of children in FU in school and living at home) "
            "(exclude in-laws)",
            "Code number of children in FU in school and living at home) "
            "(exclude in-laws)",
            "count",
        ),
        (
            RAW_V229,
            "Code dollars and cents per hour.)",
            "Code dollars and cents per hour.)",
            "united_states_dollar_per_hour",
        ),
        (
            RAW_V373,
            "Coded in Dollars *(Calculated value assumes that value of DU is "
            "approximately 10 times its annual rental value)",
            "Coded in Dollars",
            "united_states_dollar",
        ),
        (
            RAW_V2137,
            "Code number of things mentioned to J1",
            "Code number of things mentioned to J1",
            "count",
        ),
        (
            RAW_V2192,
            "Code Number of States or Countries in which R has lived including "
            "present location",
            "Code Number of States or Countries in which R has lived including "
            "present location",
            "count",
        ),
        (
            RAW_V4367,
            "Code 1-11 for actual number of months used food stamps in 1975",
            "Code 1-11 for actual number of months used food stamps in 1975",
            "month",
        ),
        (
            RAW_V4742,
            "Code actual number of minutes",
            "Code actual number of minutes",
            "minute",
        ),
        (
            RAW_V5453,
            "Code actual number of weeks (01 - 98)",
            "Code actual number of weeks (01 - 98)",
            "week",
        ),
    ],
)
def test_complete_raw_coding_descriptions_name_the_grounded_unit(
    description: str,
    candidate: str,
    statement: str,
    unit: str,
) -> None:
    assert candidate in coding_candidates(description)
    assert coding_candidate_disposition(candidate) == (
        "whole_domain_denotation"
    )
    assert statement in description_statements(description)
    assert statement_disposition(statement) == (unit, "unit_naming_clause")
    assert field_unit(description) == (
        unit,
        "derived_from_denotation_statement",
    )


@pytest.mark.parametrize(
    ("description", "statement"),
    [
        (RAW_V155, "CODE - highest number."),
        (RAW_V194, "CODE the lowest number applicable."),
    ],
)
def test_complete_raw_priority_code_descriptions_are_visible_defeaters(
    description: str,
    statement: str,
) -> None:
    assert coding_candidates(description) == (statement,)
    assert coding_candidate_disposition(statement) == (
        "whole_domain_denotation"
    )
    assert description_statements(description) == (statement,)
    assert statement_disposition(statement) == (None, "defeating_clause")
    assert field_unit(description) == (
        None,
        "defeated_denotation_statement",
    )


def test_complete_raw_enter_colon_instruction_is_explicitly_nonwhole() -> None:
    candidate = "ENTER: 4"
    assert coding_candidates(RAW_ER55305) == (candidate,)
    assert coding_candidate_disposition(candidate) == (
        "explicit_no_whole_domain_denotation"
    )
    assert description_statements(RAW_ER55305) == ()
    assert field_unit(RAW_ER55305) == (None, "no_denotation_statement")


@pytest.mark.parametrize(
    "description",
    [
        "Code actual number of MINUTES (e.g.",
        "Code actual number of MINUTES (e.g. fabricated continuation.",
        "Code same as other occupation code (Col.",
        "Code same as other occupation code (Col. fabricated continuation.",
    ],
)
def test_truncated_or_fabricated_abbreviation_span_cannot_inherit_authority(
    description: str,
) -> None:
    candidate = coding_candidates(description)[0]
    assert candidate in {
        "Code actual number of MINUTES (e.g.",
        "Code same as other occupation code (Col.",
    }
    assert coding_candidate_disposition(candidate) == (
        "whole_domain_denotation"
    )
    assert description_statements(description) == (candidate,)
    assert statement_disposition(candidate) == (
        None,
        "unadjudicated_denotation_candidate",
    )
    assert field_unit(description) == (
        None,
        "defeated_denotation_statement",
    )


def test_full_abbreviation_spans_retain_only_their_exact_adjudication() -> (
    None
):
    assert field_unit(RAW_V100)[0] == "minute"
    assert field_unit(RAW_V228) == (None, "no_statement_names_a_unit")


def test_complete_raw_v494_copular_statement_names_1967_dollars() -> None:
    statement = "the values for this variable are in 1967 dollars."
    assert statement in description_statements(RAW_V494)
    assert statement_predicate(statement) == "in 1967 dollars."
    assert statement_disposition(statement) == (
        "united_states_dollar",
        "unit_naming_clause",
    )
    assert field_unit(RAW_V494) == (
        "united_states_dollar",
        "derived_from_denotation_statement",
    )


@pytest.mark.parametrize("description", [RAW_V2470, RAW_V9378])
def test_complete_raw_food_family_keeps_context_and_derives_dollars(
    description: str,
) -> None:
    statements = description_statements(description)
    assert statements
    assert statement_disposition(statements[0]) == (
        None,
        "no_unit_naming_clause",
    )
    assert any(
        statement_disposition(statement)
        == ("united_states_dollar", "unit_naming_clause")
        for statement in statements[1:]
    )
    assert field_unit(description) == (
        "united_states_dollar",
        "derived_from_denotation_statement",
    )


@pytest.mark.parametrize("description", ROUND2_RAW_DESCRIPTIONS)
def test_round2_raw_descriptions_have_total_exact_start_cover(
    description: str,
) -> None:
    partition = denotation_candidate_start_partition(description)
    assert set(partition) == {
        "whole_domain_denotation",
        "explicit_no_whole_domain_denotation",
        "explicit_no_denotation",
        "unadjudicated_start",
    }
    assert sum(partition.values()) == denotation_candidate_start_count(
        description
    )
    assert partition["unadjudicated_start"] == 0
    assert denotation_candidate_unselected_count(description) == 0
    assert denotation_candidate_overselected_count(description) == 0


def test_every_actual_denotation_has_one_full_span_clause() -> None:
    clause_map = dict(ACTUAL_CLAUSE_TABLE)
    expected = set(ACTUAL_CANDIDATES) - ACTUAL_NO_DENOTATION_CANDIDATES
    assert set(clause_map) == expected
    for candidate in expected:
        assert statement_disposition(candidate)[1] != "no_unit_naming_clause"


# --------------------------------------------------------------------------
# Stage 2 — whole-domain predicate
# --------------------------------------------------------------------------


def test_range_scoped_statement_has_no_whole_domain_predicate() -> None:
    text = (
        "The values for this variable in the range 00001-99998 represent "
        "the amount of child support received in whole dollars."
    )
    assert extract_statements(text) == (text,)
    assert statement_predicate(text) is None
    assert statement_disposition(text) == (
        None,
        "not_a_whole_domain_denotation",
    )


def test_values_in_range_family_is_selected_but_subrange_scoped() -> None:
    text = "Values in the range 001-998 represent number of hours per year."
    assert extract_statements(text) == (text,)
    assert statement_disposition(text) == (
        None,
        "not_a_whole_domain_denotation",
    )


def test_whole_domain_predicate_strips_subject_and_verb() -> None:
    assert statement_predicate(DOLLARS) == "dollars and cents."
    assert (
        statement_predicate("This variable represents whole dollars.")
        == "whole dollars."
    )


@pytest.mark.parametrize(
    "text",
    [
        "Coded value represents the last two digits of the year.",
        "The code value represents the actual number of persons in the FU.",
        (
            "The code values for this variable represent the actual number "
            "of miles per year."
        ),
        (
            "The range of values for this variable represents actual age "
            "in years."
        ),
        "The values in this variable refer to the state and county.",
        "This four digit variable represents the month and day.",
        "The values for this variable indicate the year of graduation.",
    ],
)
def test_audited_direct_denotation_openers_are_selected(text: str) -> None:
    assert extract_statements(text) == (text,)
    assert statement_predicate(text) is not None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "This variable contains the year of data collection.",
            "year",
        ),
        (
            "The actual number of minutes taken by the interviewer to "
            "administer the questionnaire is coded here.",
            "minute",
        ),
        (
            "This is the number of businesses owned by either the Head, "
            'the Wife/"Wife", or both.',
            "count",
        ),
        ("The values are in 1967 dollars.", "united_states_dollar"),
    ],
)
def test_coded_and_value_subject_families_name_units(
    text: str,
    expected: str,
) -> None:
    assert statement_disposition(text) == (
        expected,
        "unit_naming_clause",
    )


@pytest.mark.parametrize(
    "text",
    [
        "The data coded here represent income in whole dollars.",
        "The month coded here is that of the most recent move.",
        "The values for this variable sum the total number of reports.",
    ],
)
def test_unenumerated_longer_source_like_predicates_defeat(text: str) -> None:
    assert statement_disposition(text) == (None, "defeating_clause")


@pytest.mark.parametrize(
    "text",
    [
        "This variable contains the last two digits of the year.",
        "This variable contains the total number of records.",
        "This variable indicates whether a record exists.",
        "This variable refers to the first mention of ownership.",
        "The values in this variable refer to the state and county.",
        "The condition of the car in best shape is coded here",
        (
            "The actual 1985 sequence number (V30490) of the individual who "
            "produced the income is coded here."
        ),
    ],
)
def test_explicit_coded_and_direct_defeaters(text: str) -> None:
    assert statement_disposition(text) == (None, "defeating_clause")


def test_include_is_selected_but_explicitly_not_a_denotation() -> None:
    text = "The values for this variable include all children living here."
    assert extract_statements(text) == (text,)
    assert statement_disposition(text) == (
        None,
        "not_a_whole_domain_denotation",
    )


@pytest.mark.parametrize(
    "text",
    [
        "Values in the range 0001-9998 denote interview identifiers.",
        "the value here represents a weighted average hourly wage.",
        "The negative values indicate a loss in whole dollars.",
    ],
)
def test_audited_subrange_families_cannot_establish_a_unit(text: str) -> None:
    assert extract_statements(text) == (text,)
    assert statement_disposition(text) == (
        None,
        "not_a_whole_domain_denotation",
    )


# --------------------------------------------------------------------------
# Stage 3 — the clause table
# --------------------------------------------------------------------------


def test_maximal_munch_prefers_the_longer_nested_clause() -> None:
    assert statement_disposition(PER_HOUR) == (
        "united_states_dollar_per_hour",
        "unit_naming_clause",
    )
    assert statement_disposition(DOLLARS) == (
        "united_states_dollar",
        "unit_naming_clause",
    )


def test_two_distinct_units_in_one_statement_fail_closed() -> None:
    text = (
        "The values for this variable represent dollars and cents per hour; "
        "if salary is given as an annual figure, it is divided by 2000 "
        "hours per year; if weekly, by 40 hours per week."
    )
    assert statement_disposition(text) == (None, "conflicting_unit_clauses")


def test_a_defeating_clause_beats_a_unit_clause() -> None:
    text = (
        "The values for this variable represent the actual marginal tax "
        "rate based on this person's percent proration, taxable income, "
        "number of exemptions, and tax table used."
    )
    assert statement_disposition(text) == (None, "defeating_clause")


def test_a_statement_naming_no_unit_fails_closed() -> None:
    text = (
        "The values for this variable represent overall income profits or "
        "losses."
    )
    assert statement_disposition(text) == (None, "no_unit_naming_clause")


def test_administration_does_not_match_a_ratio_defeater() -> None:
    text = (
        "The values for this variable represent the Veterans Administration "
        "Pension income of all other FU members in the FU in 1992 in whole "
        "dollars."
    )
    assert statement_disposition(text)[0] == "united_states_dollar"


def test_a_per_hour_tail_outranks_the_bare_money_clause() -> None:
    text = "This variable represents dollar and cents amount per hour."
    assert statement_disposition(text) == (
        "united_states_dollar_per_hour",
        "unit_naming_clause",
    )


@pytest.mark.parametrize(
    "predicate",
    [
        "dollars and cents amount per hour",
        "nominal whole dollars",
        "whole dollars nominal amount",
        "whole dollars / hour",
        "whole dollars\N{NO-BREAK SPACE}per hour",
        "whole dollars per hour",
        "number of hours per day",
        "number of miles per week",
        "number of persons per acre",
        "number of hours (0001-2080) per day",
        "whole dollars (nominal) per hour",
    ],
)
def test_every_unenumerated_longer_phrase_fails_closed(
    predicate: str,
) -> None:
    text = f"This variable represents {predicate}."
    assert statement_disposition(text) == (None, "defeating_clause")


def test_explicit_and_general_plural_defeat_is_one_full_span_hit() -> None:
    predicate = "dollars and cents amount per hour"
    assert clause_occurrences(predicate) == ((0, len(predicate), NO_UNIT),)


def test_every_authorized_positive_defeats_unknown_left_and_right_extensions() -> (
    None
):
    positive_rows = [
        (predicate, unit)
        for predicate, unit, reason in PREDICATE_AUTHORITY
        if reason == "unit_naming_clause"
    ]
    assert len(positive_rows) == 1_531
    for predicate, unit in positive_rows:
        assert unit is not None
        assert unit in {
            found for _start, _end, found in clause_occurrences(predicate)
        }
        for extension in (f"unknown {predicate}", f"{predicate} unknown"):
            units = {
                found for _start, _end, found in clause_occurrences(extension)
            }
            if predicate.startswith(
                ("CODE ", "Code ", "Coded ", "ENTER ", "RECORD ")
            ):
                # Direct coding predicates are not lexical clause rows, so
                # an unknown extension may have no clause hit at all.  It
                # still cannot inherit any positive unit.
                assert units in (set(), {NO_UNIT})
            else:
                assert units == {NO_UNIT}
            assert not set(UNIT_VOCABULARY) & units


@pytest.mark.parametrize(
    ("predicate", "unit"),
    [
        ("dollars and cents per hour", "united_states_dollar_per_hour"),
        (
            "dollar and cents amount per hour",
            "united_states_dollar_per_hour",
        ),
        ("number of hours per week", "hour_per_week"),
        ("hours per week", "hour_per_week"),
        ("hours per year", "hour_per_year"),
        (
            "number of hours (0001-2080) per year",
            "hour_per_year",
        ),
        ("number of miles per year", "mile_per_year"),
    ],
)
def test_enumerated_ratio_phrase_survives(
    predicate: str,
    unit: str,
) -> None:
    text = f"This variable represents {predicate}."
    assert statement_disposition(text) == (unit, "unit_naming_clause")


def test_a_density_is_defeated_rather_than_counted() -> None:
    text = (
        "The values for this variable represent the number of persons per "
        "room with one implied decimal place; e.g., a value of 20 here "
        "represents 2.0 persons per room."
    )
    assert statement_disposition(text) == (None, "defeating_clause")


@pytest.mark.parametrize(
    ("statement", "unit"),
    [
        ("Actual dollar and cents per hour", "united_states_dollar_per_hour"),
        ("Actual number of dollars", "united_states_dollar"),
        (
            "Actual expenditure in hundreds of dollars",
            "hundreds_of_united_states_dollars",
        ),
        ("Actual dollars per week", "united_states_dollar_per_week"),
        ("Actual hours worked per week", "hour_per_week"),
        ("Actual number of hours per year", "hour_per_year"),
        ("Actual number in FU", "count"),
        ("Actual number in Family Unit", "count"),
        ("Actual number in family unit", "count"),
        ("Actual year", "year"),
    ],
)
def test_supplemental_actual_clauses_resolve(
    statement: str,
    unit: str,
) -> None:
    assert statement_disposition(statement) == (unit, "unit_naming_clause")


@pytest.mark.parametrize(
    "statement",
    [
        "Actual interview number was coded: 0001-6620)",
        "Actual Minus Required Rooms for Family",
        "Actual minus required rooms for family",
        "Actual score:",
    ],
)
def test_supplemental_actual_defeaters_resolve(statement: str) -> None:
    assert statement_disposition(statement) == (None, "defeating_clause")


def test_clause_occurrences_drop_only_strictly_contained_matches() -> None:
    hits = clause_occurrences("dollars and cents per hour")
    assert [unit for _start, _end, unit in hits] == [
        "united_states_dollar_per_hour"
    ]


def test_longest_non_nested_same_disposition_clause_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predicate = "total weeks and weeks worked"
    # A registered conflict leaves nonnested lexical rows to the tie-break;
    # an unregistered complete phrase would instead fail closed first.
    monkeypatch.setitem(
        unit_authority._PREDICATE_AUTHORITY,
        predicate,
        (None, "conflicting_unit_clauses"),
    )
    hits = clause_occurrences(predicate)
    assert hits == ((16, 28, "week"),)


def test_clause_matching_is_invariant_to_table_enumeration_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predicate = "number of hours per day"
    expected = clause_occurrences(predicate)
    monkeypatch.setattr(
        "populace_dynamics.data.psid_unit_authority.CLAUSE_TABLE",
        tuple(reversed(CLAUSE_TABLE)),
    )
    assert set(clause_occurrences(predicate)) == set(expected)


def test_every_clause_unit_is_in_the_closed_vocabulary() -> None:
    for _clause, unit in CLAUSE_TABLE:
        assert unit == NO_UNIT or unit in UNIT_VOCABULARY


def test_clause_table_has_no_duplicate_clause() -> None:
    clauses = [clause for clause, _unit in CLAUSE_TABLE]
    assert len(clauses) == len(set(clauses))


# --------------------------------------------------------------------------
# Field disposition
# --------------------------------------------------------------------------


def test_field_with_no_statement_has_no_unit() -> None:
    assert field_unit("House value") == (None, "no_denotation_statement")
    assert field_unit(None) == (None, "no_denotation_statement")


def test_field_takes_the_single_unit_its_statements_name() -> None:
    assert field_unit(f"AMOUNT {DOLLARS}") == (
        "united_states_dollar",
        "derived_from_denotation_statement",
    )


def test_field_with_two_distinct_statement_units_fails_closed() -> None:
    assert field_unit(f"{DOLLARS}\n{HOURS}") == (
        None,
        "conflicting_statement_units",
    )


def test_primary_and_residual_selectors_union_and_conflict() -> None:
    description = (
        "The values for this variable represent the actual number of years.\n"
        "Actual number of months"
    )
    assert field_unit(description) == (None, "conflicting_statement_units")


def test_defeated_statement_blocks_a_positive_statement() -> None:
    defeated = (
        "The values for this variable represent the number of persons per "
        "room."
    )
    for text in (f"{DOLLARS} {defeated}", f"{defeated} {DOLLARS}"):
        assert field_unit(text) == (None, "defeated_denotation_statement")


def test_unadjudicated_actual_candidate_blocks_a_positive_statement() -> None:
    text = f"{DOLLARS}\nActual furlongs per fortnight"
    assert field_unit(text) == (None, "defeated_denotation_statement")


def test_conflicting_statement_blocks_a_positive_statement() -> None:
    conflict = (
        "The values for this variable represent dollars and cents per hour; "
        "if salary is given as an annual figure, it is divided by 2000 hours "
        "per year; if weekly, by 40 hours per week."
    )
    assert statement_disposition(conflict) == (
        None,
        "conflicting_unit_clauses",
    )
    assert field_unit(f"{DOLLARS} {conflict}") == (
        None,
        "defeated_denotation_statement",
    )


def test_field_whose_only_statement_names_nothing_fails_closed() -> None:
    text = "The values for this variable represent the actual age of the Head."
    assert field_unit(text) == (None, "no_statement_names_a_unit")


def test_line_wrapped_statement_still_matches() -> None:
    wrapped = "The values for this variable represent dollars\nand cents."
    assert field_unit(wrapped)[0] == "united_states_dollar"


# --------------------------------------------------------------------------
# The successor terminal function
# --------------------------------------------------------------------------


def test_compiled_field_without_a_unit_moves_to_incomplete() -> None:
    assert successor_terminal(COMPILED, None) == (INCOMPLETE, True)
    assert successor_terminal(PARTIAL_RANGE, None) == (INCOMPLETE, True)


def test_compiled_field_with_a_unit_does_not_move() -> None:
    for terminal in COMPILED_TERMINALS:
        assert successor_terminal(terminal, "united_states_dollar") == (
            terminal,
            False,
        )


@pytest.mark.parametrize(
    "terminal",
    [
        VALUE_CODE_ONLY,
        RANGE_UNESTABLISHED,
        "nonnumeric_source_field_outside_numeric_grammar",
        CONFLICTING,
        UNSUPPORTED,
        INCOMPLETE,
    ],
)
def test_precedence_keeps_every_noncompiled_terminal_fixed(
    terminal: str,
) -> None:
    assert successor_terminal(terminal, None) == (terminal, False)
    assert successor_terminal(terminal, "week") == (terminal, False)


def test_terminal_order_is_the_ten_ratified_terminals() -> None:
    assert len(TERMINAL_ORDER) == 10
    assert len(set(TERMINAL_ORDER)) == 10
    assert COMPILED_TERMINALS <= set(TERMINAL_ORDER)
    assert set(FAILURE_TERMINALS) <= set(TERMINAL_ORDER)


# --------------------------------------------------------------------------
# Denominator partition
# --------------------------------------------------------------------------


def test_artifact_partition_covers_the_whole_denominator() -> None:
    assert sum(size for _name, size in ARTIFACT_PARTITION) == 89_599
    assert artifact_of_position(0) == ARTIFACT_PARTITION[0][0]
    assert artifact_of_position(3_867) == ARTIFACT_PARTITION[0][0]
    assert artifact_of_position(3_868) == ARTIFACT_PARTITION[1][0]
    assert artifact_of_position(89_598) == ARTIFACT_PARTITION[-1][0]
    with pytest.raises(ValueError):
        artifact_of_position(89_599)


# --------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------


def _row(wave: int, field: str, status: str, description: str | None) -> dict:
    return {
        "interview_wave": wave,
        "raw_field_id": field,
        "derivation_status": status,
        "resolution_reason": "structural_literal_domain",
        "source_description": description,
    }


def test_successor_census_moves_only_unitless_compiled_fields() -> None:
    rows = [
        _row(1968, "A", COMPILED, f"pay {DOLLARS}"),
        _row(1968, "B", COMPILED, "House value"),
        _row(1968, "C", UNSUPPORTED, "House value"),
        _row(1968, "D", VALUE_CODE_ONLY, "House value"),
    ]
    census = successor_census(rows)
    counts = {
        row["derivation_status"]: row["field_count"]
        for row in census["count_rows"]
    }
    assert counts[COMPILED] == 1
    assert counts[INCOMPLETE] == 1
    assert counts[UNSUPPORTED] == 1
    assert counts[VALUE_CODE_ONLY] == 1
    assert census["movement_row_count"] == 1
    moved = census["movement_rows"][0]
    assert moved["raw_field_id"] == "B"
    assert moved["resolution_reason"] == UNIT_ABSENT_RESOLUTION_REASON
    assert moved["unit_absence_reason"] == "no_denotation_statement"
    assert census["field_count"] == 4
    assert census["denominator_sha256"] == canonical_sha256(
        [[1968, "A"], [1968, "B"], [1968, "C"], [1968, "D"]]
    )


def test_ordered_assignment_binds_a_retained_resolution_reason() -> None:
    row = _row(1968, "A", COMPILED, DOLLARS)
    row["resolution_reason"] = "first_retained_reason"
    first = successor_census([row])
    changed_row = dict(row)
    changed_row["resolution_reason"] = "changed_retained_reason"
    changed = successor_census([changed_row])

    assert first["denominator_sha256"] == changed["denominator_sha256"]
    assert first["count_array_sha256"] == changed["count_array_sha256"]
    assert first["ordered_assignment_sha256"] == canonical_sha256(
        [(1968, "A", COMPILED, "first_retained_reason")]
    )
    assert (
        first["ordered_assignment_sha256"]
        != (changed["ordered_assignment_sha256"])
    )


def test_successor_census_rejects_a_duplicate_field_key() -> None:
    rows = [
        _row(1968, "A", COMPILED, None),
        _row(1968, "A", COMPILED, None),
    ]
    with pytest.raises(ValueError, match="duplicate field key"):
        successor_census(rows)


def test_successor_census_rejects_an_unknown_terminal() -> None:
    with pytest.raises(ValueError, match="unknown ratified terminal"):
        successor_census([_row(1968, "A", "made_up", None)])


def test_successor_census_rejects_a_short_row() -> None:
    row = _row(1968, "A", COMPILED, None)
    del row["resolution_reason"]
    with pytest.raises(ValueError, match="unexpected keys"):
        successor_census([row])


def test_successor_census_rejects_an_extra_member() -> None:
    row = _row(1968, "A", COMPILED, None)
    row["extra"] = "not canonical"
    with pytest.raises(ValueError, match="unexpected keys"):
        successor_census([row])


@pytest.mark.parametrize(
    ("member", "value", "message"),
    [
        ("interview_wave", True, "JSON integer"),
        ("raw_field_id", 1, "JSON string"),
        ("derivation_status", 1, "JSON string"),
        ("resolution_reason", None, "JSON string"),
        ("source_description", 1, "JSON string or null"),
    ],
)
def test_successor_census_rejects_noncanonical_member_types(
    member: str,
    value: object,
    message: str,
) -> None:
    row = _row(1968, "A", COMPILED, None)
    row[member] = value
    with pytest.raises(ValueError, match=message):
        successor_census([row])


def test_failure_reason_rows_follow_precedence_then_reason() -> None:
    rows = failure_reason_rows(
        [
            (1970, "B", INCOMPLETE, "zeta"),
            (1969, "A", UNSUPPORTED, "beta"),
            (1971, "C", INCOMPLETE, "alpha"),
            (1972, "D", CONFLICTING, "gamma"),
            (1973, "E", COMPILED, "not-a-failure"),
        ]
    )
    assert [
        (row["derivation_status"], row["resolution_reason"]) for row in rows
    ] == [
        (CONFLICTING, "gamma"),
        (UNSUPPORTED, "beta"),
        (INCOMPLETE, "alpha"),
        (INCOMPLETE, "zeta"),
    ]
    assert rows[2]["field_keys"] == [[1971, "C"]]


def test_statement_table_is_sorted_and_carries_a_witness() -> None:
    rows = [
        _row(1968, "B", COMPILED, HOURS),
        _row(1968, "A", COMPILED, f"{DOLLARS} {HOURS}"),
    ]
    table = statement_table(rows)
    assert [row["statement"] for row in table] == sorted({DOLLARS, HOURS})
    by_statement = {row["statement"]: row for row in table}
    assert by_statement[HOURS]["field_count"] == 2
    assert by_statement[HOURS]["witness_field_key"] == [1968, "B"]
    assert by_statement[DOLLARS]["typed_value_unit"] == (
        "united_states_dollar"
    )


def test_actual_candidate_table_is_sorted_and_carries_adjudication() -> None:
    rows = [
        _row(1968, "B", COMPILED, "Actual number of weeks"),
        _row(1968, "A", COMPILED, "Actual number of weeks"),
        _row(1968, "C", COMPILED, "Actual made-up measure"),
    ]
    table = actual_candidate_table(rows)
    assert [row["candidate"] for row in table] == sorted(
        {"Actual number of weeks", "Actual made-up measure"}
    )
    by_candidate = {row["candidate"]: row for row in table}
    assert by_candidate["Actual number of weeks"]["field_count"] == 2
    assert by_candidate["Actual number of weeks"]["witness_field_key"] == [
        1968,
        "B",
    ]
    assert by_candidate["Actual made-up measure"]["adjudication"] == (
        "unadjudicated_no_denotation"
    )


def test_coding_candidate_table_covers_every_potential_coding_start() -> None:
    rows = [
        _row(1968, "A", COMPILED, RAW_V100),
        _row(1968, "B", COMPILED, RAW_V229),
    ]
    table = coding_candidate_table(rows)
    assert [row["candidate"] for row in table] == sorted(
        {
            "Code actual number of MINUTES (e.g.",
            "Code dollars and cents per hour.)",
        }
    )
    assert all(
        row["adjudication"] == "whole_domain_denotation" for row in table
    )
    assert all(row["selected_statement"] is not None for row in table)
    assert all(
        row["occurrence_count"] == row["field_count"] == 1 for row in table
    )


def test_denotation_candidate_table_dispositions_every_contextual_start() -> (
    None
):
    rows = [_row(1976, "V4742", COMPILED, RAW_V4742)]
    table = denotation_candidate_table(rows)
    assert len(table) == denotation_candidate_start_count(RAW_V4742)
    assert all(
        set(row)
        == {
            "segment",
            "word_ordinal",
            "start_utf8_byte",
            "candidate",
            "context_key_sha256",
            "adjudication",
            "occurrence_count",
            "field_count",
            "witness_field_key",
        }
        for row in table
    )
    code_row = next(
        row
        for row in table
        if row["candidate"] == "Code actual number of minutes"
    )
    assert code_row["adjudication"] == "whole_domain_denotation"
    assert code_row["word_ordinal"] == 3
    assert code_row["witness_field_key"] == [1976, "V4742"]
    assert not any(
        row["adjudication"] == "unadjudicated_start" for row in table
    )


def test_occurrence_identity_binds_every_start_and_exact_cover() -> None:
    rows = [
        _row(1976, "V4742", COMPILED, RAW_V4742),
        _row(1983, "V9378", COMPILED, RAW_V9378),
    ]
    identity = denotation_candidate_occurrence_identity(rows)
    expected_count = sum(
        denotation_candidate_start_count(row["source_description"])
        for row in rows
    )
    assert identity["row_count"] == expected_count
    assert sum(identity["partition"].values()) == expected_count
    assert identity["partition"]["unadjudicated_start"] == 0
    assert identity["unselected_count"] == 0
    assert identity["overselected_count"] == 0
    assert identity["byte_count"] > 0
    assert len(identity["sha256"]) == 64


def test_frozen_semantic_authorities_have_exact_identity() -> None:
    assert len(PREDICATE_AUTHORITY) == 2_586
    assert len({row[0] for row in PREDICATE_AUTHORITY}) == len(
        PREDICATE_AUTHORITY
    )
    assert canonical_sha256(PREDICATE_AUTHORITY) == (
        "791bbe9436a26516e28aacf243f104d74f8e8053204d3759a414c894fa073f32"
    )

    assert len(CODING_START_AUTHORITY) == 203
    assert len({row[0] for row in CODING_START_AUTHORITY}) == len(
        CODING_START_AUTHORITY
    )
    assert canonical_sha256(CODING_START_AUTHORITY) == (
        "ac2bddbed10bb445215bb19354259685efe24c82b2f59b258dec5d23fcf8497b"
    )
    assert all(
        (selected is not None) == (disposition == "whole_domain_denotation")
        for _candidate, disposition, selected in CODING_START_AUTHORITY
    )

    assert len(SEGMENT_START_AUTHORITY) == 59_445
    assert len({row[0] for row in SEGMENT_START_AUTHORITY}) == len(
        SEGMENT_START_AUTHORITY
    )
    assert sum(
        len(vector) for _segment, vector in SEGMENT_START_AUTHORITY
    ) == (1_114_747)
    assert canonical_sha256(SEGMENT_START_AUTHORITY) == (
        "df58afe79ea36b39e3a39477b7566f7e0d47dd34c75c83b669fcf072a8235345"
    )
    assert all(
        vector and len(vector) == segment.count(" ") + 1
        for segment, vector in SEGMENT_START_AUTHORITY
    )
    assert all(
        set(vector) <= {"D", "N", "W"}
        for _segment, vector in SEGMENT_START_AUTHORITY
    )
    assert segment_start_authority_table()[0] == {
        "segment": SEGMENT_START_AUTHORITY[0][0],
        "start_dispositions": SEGMENT_START_AUTHORITY[0][1],
        "start_count": len(SEGMENT_START_AUTHORITY[0][1]),
    }


def test_cleartext_start_authorities_replace_the_opaque_hash_registry() -> (
    None
):
    assert not hasattr(
        unit_authority,
        "EXPLICIT_NO_DENOTATION_CANDIDATE_HASHES",
    )


def test_canonical_serialization_matches_section_10_1() -> None:
    assert canonical_json_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}\n'
    assert canonical_sha256([]) == (
        "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
    )
