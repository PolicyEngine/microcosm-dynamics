"""Tests for the Amendment 10 (§24) unit-authority machinery."""

from __future__ import annotations

import pytest

import populace_dynamics.data.psid_unit_authority as unit_authority

from populace_dynamics.data.psid_unit_authority import (
    ANCHORS,
    ACTUAL_CANDIDATES,
    ACTUAL_CLAUSE_TABLE,
    ACTUAL_NO_DENOTATION_CANDIDATES,
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
    description_statements,
    denotation_candidate_disposition,
    denotation_candidate_start_count,
    denotation_candidate_table,
    denotation_candidate_unselected_count,
    denotation_candidates,
    extract_statements,
    failure_reason_rows,
    field_unit,
    normalize_description,
    statement_anchor,
    statement_disposition,
    statement_predicate,
    statement_table,
    successor_census,
    successor_terminal,
)
from populace_dynamics.data.psid_unit_predicate_authority import (
    EXPLICIT_NO_DENOTATION_CANDIDATE_COUNT,
    EXPLICIT_NO_DENOTATION_CANDIDATE_HASHES,
    EXPLICIT_NO_DENOTATION_CANDIDATE_RELATION_SHA256,
    PREDICATE_AUTHORITY,
    PREDICATE_AUTHORITY_ROW_COUNT,
    PREDICATE_AUTHORITY_SHA256,
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


def test_actual_residual_selector_covers_line_start_and_embedded_tail() -> None:
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
    description = "Actual - Required rooms V381 = 5 - 9"
    assert actual_candidates(description) == (description,)
    assert description_statements(description) == ()


def test_actual_candidate_adjudication_is_closed_and_fail_closed() -> None:
    assert len(ACTUAL_CANDIDATES) == len(set(ACTUAL_CANDIDATES)) == 82
    assert ACTUAL_NO_DENOTATION_CANDIDATES < set(ACTUAL_CANDIDATES)
    assert (
        actual_candidate_disposition("Actual number of weeks")
        == "whole_domain_denotation"
    )


def test_exhaustive_candidate_selector_covers_lexemes_and_actual_lines() -> None:
    description = (
        "A component represents a lookup value.\n"
        "Actual number of weeks\n"
        "Question text without a denotation."
    )
    assert denotation_candidates(description) == (
        "A component represents a lookup value.",
        "Actual number of weeks Question text without a denotation.",
        "Actual number of weeks",
    )
    assert denotation_candidate_disposition(
        "A component represents a lookup value."
    ) == "unadjudicated_no_denotation"
    assert denotation_candidate_disposition(
        "Actual number of weeks"
    ) == "whole_domain_denotation"
    assert denotation_candidate_start_count(description) == 15
    assert denotation_candidate_unselected_count(description) == 0
    assert (
        denotation_candidate_unselected_count(
            "Actual number of weeks\nFormula prose without a period"
        )
        == 0
    )
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
    assert statement_disposition("Actual furlongs per fortnight") == (
        None,
        "unadjudicated_denotation_candidate",
    )


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


def test_every_authorized_positive_defeats_unknown_left_and_right_extensions(
) -> None:
    positive_rows = [
        (predicate, unit)
        for predicate, unit, reason in PREDICATE_AUTHORITY
        if reason == "unit_naming_clause"
    ]
    assert len(positive_rows) == 1_521
    for predicate, unit in positive_rows:
        assert unit is not None
        assert unit in {
            found for _start, _end, found in clause_occurrences(predicate)
        }
        for extension in (f"unknown {predicate}", f"{predicate} unknown"):
            assert {found for _start, _end, found in clause_occurrences(extension)} == {
                NO_UNIT
            }


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
    assert first["ordered_assignment_sha256"] != (
        changed["ordered_assignment_sha256"]
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


def test_denotation_candidate_table_covers_selected_and_rejected_rows() -> None:
    rows = [
        _row(1968, "A", COMPILED, DOLLARS),
        _row(1968, "B", COMPILED, "A component represents a code."),
    ]
    table = denotation_candidate_table(rows)
    assert [row["candidate"] for row in table] == sorted(
        {DOLLARS, "A component represents a code."}
    )
    by_candidate = {row["candidate"]: row for row in table}
    assert by_candidate[DOLLARS]["adjudication"] == (
        "contains_whole_domain_denotation"
    )
    assert by_candidate["A component represents a code."]["adjudication"] == (
        "unadjudicated_no_denotation"
    )


def test_frozen_semantic_authorities_have_exact_identity() -> None:
    assert len(PREDICATE_AUTHORITY) == PREDICATE_AUTHORITY_ROW_COUNT == 2_558
    assert len({row[0] for row in PREDICATE_AUTHORITY}) == len(
        PREDICATE_AUTHORITY
    )
    assert canonical_sha256(PREDICATE_AUTHORITY) == PREDICATE_AUTHORITY_SHA256
    assert (
        len(EXPLICIT_NO_DENOTATION_CANDIDATE_HASHES)
        == EXPLICIT_NO_DENOTATION_CANDIDATE_COUNT
        == 53_255
    )
    assert (
        canonical_sha256(sorted(EXPLICIT_NO_DENOTATION_CANDIDATE_HASHES))
        == EXPLICIT_NO_DENOTATION_CANDIDATE_RELATION_SHA256
    )


def test_canonical_serialization_matches_section_10_1() -> None:
    assert canonical_json_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}\n'
    assert canonical_sha256([]) == (
        "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
    )
