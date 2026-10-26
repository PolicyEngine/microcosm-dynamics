"""Schema and lookup tests using invented legal rows and invented captures.

All monetary values, text and dates in these fixtures are invented examples
of the schema. They make no claim about actual coverage law.
"""

import copy
import hashlib
import json
from datetime import date
from fractions import Fraction

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.coverage_rules import (
    CONSEQUENCES,
    SCHEMA_VERSION,
    AlternativeRequiredError,
    CaptureIntegrityError,
    CoverageRegistry,
    CoverageRegistryError,
    CoverageRule,
    NoRuleError,
    OpenRuleError,
    RegistryValidationError,
    RuleGapError,
    RuleOverlapError,
    TableDefinitionUnverifiedError,
    ThresholdUnavailableError,
    UnknownIdentifierError,
    load_registry,
    source_text,
)

INVENTED_BYTES = b"<p>Invented source passage for schema tests only.</p>"
INVENTED_CITATION = {
    "capture": "invented.html",
    "sha256": hashlib.sha256(INVENTED_BYTES).hexdigest(),
    "authority": "INVENTED authority",
    "location": "INVENTED section",
}


def invented_row(start=1968, end=2026, rule_id="INVENTED_rule"):
    return {
        "rule_id": rule_id,
        "family": "INVENTED_family",
        "effective_start": f"{start}-01-01",
        "effective_end": f"{end}-12-31",
        "citations": [copy.deepcopy(INVENTED_CITATION)],
        "trigger_facts": ["amount"],
        "consequence": "covered",
        "residual_default": {
            "consequence": "covered",
            "description": "INVENTED residual when no case applies.",
        },
        "cases": [],
        "open_alternatives": [],
        "identification_class": "awaiting_ce2",
        "description": "INVENTED regime for schema tests only.",
        "parameters": {"invented_value": 17},
        "worked_examples": [],
        "rare_exclusion": None,
        "alternative": None,
        "open_reason": None,
    }


def invented_payload(rows=None, thresholds=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "income_years": [1968, 2026],
        "rules": rows if rows is not None else [invented_row()],
        "thresholds": thresholds or [],
    }


@given(
    st.sampled_from(["calculation", "published_inputs", "published_outputs"])
)
def test_example_schema_requires_inputs_outcome_and_oracle(field):
    row = invented_row()
    example = {
        "example_id": "INVENTED_example",
        "income_year": 2024,
        "citation": copy.deepcopy(INVENTED_CITATION),
        "source_passage": "INVENTED passage; no published legal example.",
        "expected_rule_id": row["rule_id"],
        "calculation": "INVENTED_calculation",
        "published_inputs": {"INVENTED_input": 1},
        "published_outputs": {"INVENTED_output": 1},
    }
    row["worked_examples"] = [example]
    CoverageRule.from_dict(row)
    del example[field]
    with pytest.raises(RegistryValidationError, match="example"):
        CoverageRule.from_dict(row)


def invented_registry(tmp_path, rows=None, thresholds=None):
    (tmp_path / "invented.html").write_bytes(INVENTED_BYTES)
    return CoverageRegistry.from_dict(
        invented_payload(rows, thresholds), capture_root=tmp_path
    )


def invented_threshold(values=None, indexing=None):
    return {
        "threshold_id": "INVENTED_threshold",
        "aggregation_scope": "person_year",
        "eligible_concept": "INVENTED eligible base",
        "comparison": "at_least",
        "published_values": values or {"2024": 100},
        "citations": [copy.deepcopy(INVENTED_CITATION)],
        "indexing": indexing,
        "monotone": True,
    }


INVENTED_INDEX = {
    "kind": "awi",
    "base_amount": 100,
    "base_index": 100,
    "lag_years": 2,
    "round_to": 10,
    "rounding": "nearest",
    "floor": "prior_year",
    "first_year": 2025,
    "last_year": 2026,
}


@given(st.integers(1968, 2026), st.booleans())
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_every_lookup_is_nonempty_or_typed_refusal(tmp_path, year, present):
    registry = invented_registry(tmp_path, [invented_row(1980, 2000)])
    family = "INVENTED_family" if present else "INVENTED_missing"
    try:
        rules = registry.lookup(family, year)
    except CoverageRegistryError:
        assert not present or not 1980 <= year <= 2000
    else:
        assert rules
        assert present and 1980 <= year <= 2000


@given(st.integers(1969, 2026), st.integers(1968, 2026))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_partition_and_row_order_round_trip(tmp_path, boundary, year):
    rows = [
        invented_row(1968, boundary - 1, "INVENTED_before"),
        invented_row(boundary, 2026, "INVENTED_after"),
    ]
    forward = invented_registry(tmp_path, rows)
    reverse = invented_registry(tmp_path, list(reversed(rows)))
    assert forward.to_json() == reverse.to_json()
    assert forward.lookup("INVENTED_family", year) == reverse.lookup(
        "INVENTED_family", year
    )
    restored = CoverageRegistry.from_dict(
        json.loads(forward.to_json()), capture_root=tmp_path
    )
    assert restored.to_json() == forward.to_json()
    assert len(restored.lookup("INVENTED_family", year)) == 1


@given(st.integers(1968, 2026), st.integers(1, 28))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_date_gap_refuses_even_when_year_has_rows(tmp_path, year, day):
    before = invented_row(rule_id="INVENTED_before")
    after = invented_row(rule_id="INVENTED_after")
    before["effective_end"] = f"{year}-06-{day:02d}"
    after["effective_start"] = f"{year}-07-01"
    registry = invented_registry(tmp_path, [before, after])
    with pytest.raises(RuleGapError):
        registry.lookup("INVENTED_family", year)
    with pytest.raises(RuleGapError):
        registry.lookup_date("INVENTED_family", date(year, 6, day + 1))


def test_midyear_law_change_returns_both_regimes(tmp_path):
    before = invented_row(rule_id="INVENTED_before")
    after = invented_row(rule_id="INVENTED_after")
    before["effective_end"] = "1991-07-01"
    after["effective_start"] = "1991-07-02"
    registry = invented_registry(tmp_path, [before, after])
    assert len(registry.lookup("INVENTED_family", 1991)) == 2
    assert registry.lookup_date("INVENTED_family", date(1991, 7, 1))[
        0
    ].rule_id == ("INVENTED_before")
    assert registry.lookup_date("INVENTED_family", date(1991, 7, 2))[
        0
    ].rule_id == ("INVENTED_after")


@given(st.integers(1968, 2026))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_overlap_requires_named_options_and_explicit_selection(tmp_path, year):
    rows = [
        invented_row(rule_id="INVENTED_a"),
        invented_row(rule_id="INVENTED_b"),
    ]
    with pytest.raises(RuleOverlapError):
        invented_registry(tmp_path, rows)
    for row, name in zip(rows, ("reading_a", "reading_b"), strict=True):
        row["alternative"] = {
            "group": "INVENTED_question",
            "name": name,
            "explanation": "INVENTED unresolved source question",
        }
    registry = invented_registry(tmp_path, rows)
    with pytest.raises(AlternativeRequiredError):
        registry.lookup("INVENTED_family", year)
    assert (
        registry.lookup("INVENTED_family", year, alternative="reading_b")[
            0
        ].rule_id
        == "INVENTED_b"
    )


@given(
    st.sampled_from(["awaiting_ce2", "identified", "prior", "unidentified"])
)
@settings(deadline=None)
def test_awaiting_evidence_is_never_identified(identification):
    row = invented_row()
    row["identification_class"] = identification
    assert CoverageRule.from_dict(row).is_identified == (
        identification == "identified"
    )


@given(st.text(min_size=1).filter(lambda value: value not in {"amount"}))
@settings(deadline=None)
def test_unknown_fact_is_refused(value):
    row = invented_row()
    row["trigger_facts"] = ["INVENTED_unknown_" + value]
    with pytest.raises(RegistryValidationError):
        CoverageRule.from_dict(row)


@given(st.binary(min_size=1).filter(lambda value: value != INVENTED_BYTES))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_every_cited_hash_matches(tmp_path, changed):
    registry = invented_registry(tmp_path)
    (tmp_path / "invented.html").write_bytes(changed)
    with pytest.raises(CaptureIntegrityError):
        CoverageRegistry.from_dict(registry.to_dict(), capture_root=tmp_path)


@given(st.sampled_from(["population", "bound", "citation"]))
@settings(deadline=None)
def test_rare_bound_requires_population_bound_and_citation(missing):
    row = invented_row()
    candidate = {
        "population": "INVENTED population",
        "bound": "INVENTED upper bound",
        "citation": copy.deepcopy(INVENTED_CITATION),
    }
    row["rare_exclusion"] = {
        "strict": "unresolved",
        "negligible_candidate": candidate,
        "searches": ["INVENTED search"],
    }
    assert CoverageRule.from_dict(row).rare_exclusion is not None
    del candidate[missing]
    with pytest.raises(RegistryValidationError):
        CoverageRule.from_dict(row)


@given(st.integers(0, 1000), st.integers(1, 1000))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_monotone_publications_cannot_fall(tmp_path, lower, increase):
    threshold = invented_threshold({"2024": lower, "2025": lower + increase})
    registry = invented_registry(tmp_path, thresholds=[threshold])
    assert registry.threshold(
        "INVENTED_threshold", 2025
    ) >= registry.threshold("INVENTED_threshold", 2024)
    threshold["published_values"] = {"2024": lower + increase, "2025": lower}
    with pytest.raises(RegistryValidationError):
        invented_registry(tmp_path, thresholds=[threshold])


@given(st.integers(0, 1000))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_index_floor_and_exact_rounding(tmp_path, wage_index):
    threshold = invented_threshold(indexing=INVENTED_INDEX)
    registry = invented_registry(tmp_path, thresholds=[threshold])
    actual = registry.threshold(
        "INVENTED_threshold",
        2025,
        index_inputs={"national_average_wage_index_2023": wage_index},
    )
    # Independent integer oracle for the invented $10 half-up rounding.
    expected = max(100, ((wage_index + 5) // 10) * 10)
    assert actual == Fraction(expected)
    assert actual >= registry.threshold("INVENTED_threshold", 2024)


def test_no_guess_for_unpublished_threshold(tmp_path):
    registry = invented_registry(
        tmp_path, thresholds=[invented_threshold(indexing=INVENTED_INDEX)]
    )
    with pytest.raises(ThresholdUnavailableError, match="national_average"):
        registry.threshold("INVENTED_threshold", 2025)
    with pytest.raises(
        ThresholdUnavailableError, match="prior_year_threshold_2025"
    ):
        registry.threshold(
            "INVENTED_threshold",
            2026,
            index_inputs={"national_average_wage_index_2024": 200},
        )


@given(st.integers(10000, 1000000), st.sampled_from([1, 3]))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_quarter_sum_uses_named_exact_cents(tmp_path, cents, numerator):
    index = {
        "kind": "quarter_of_coverage_sum",
        "first_year": 2025,
        "last_year": 2026,
        "parameter_name": "INVENTED_quarters_cents",
        "multiplier_numerator": numerator,
        "multiplier_denominator": 2,
    }
    registry = invented_registry(
        tmp_path, thresholds=[invented_threshold(indexing=index)]
    )
    with pytest.raises(ThresholdUnavailableError, match="INVENTED_quarters"):
        registry.threshold("INVENTED_threshold", 2026)
    assert registry.threshold(
        "INVENTED_threshold",
        2026,
        index_inputs={"INVENTED_quarters_cents": [cents] * 4},
    ) == Fraction(cents * 4 * numerator, 200)


@pytest.mark.parametrize("year", [1967, 2027])
def test_year_support_is_explicit(tmp_path, year):
    with pytest.raises(NoRuleError):
        invented_registry(tmp_path).lookup("INVENTED_family", year)


def test_open_rule_refuses_and_payload_is_immutable(tmp_path):
    row = invented_row()
    row["open_reason"] = "INVENTED blocked source"
    row["consequence"] = None
    row["residual_default"]["consequence"] = None
    row["open_alternatives"] = [
        {"name": "INVENTED_a", "description": "INVENTED first reading"},
        {"name": "INVENTED_b", "description": "INVENTED second reading"},
    ]
    registry = invented_registry(tmp_path, [row])
    with pytest.raises(OpenRuleError):
        registry.lookup("INVENTED_family", 2000)
    with pytest.raises(TypeError):
        registry.rules[0].parameters["invented_value"] = 99


def test_selected_alternative_never_borrows_a_different_reading(tmp_path):
    rows = [
        invented_row(rule_id="INVENTED_a"),
        invented_row(rule_id="INVENTED_b"),
    ]
    rows[1]["effective_start"] = "2000-07-01"
    for row, name in zip(rows, ("a", "b"), strict=True):
        row["alternative"] = {
            "group": "INVENTED_group",
            "name": name,
            "explanation": "INVENTED incomplete support for reading b",
        }
    registry = invented_registry(tmp_path, rows)
    with pytest.raises(RuleGapError, match="selected alternative b"):
        registry.lookup("INVENTED_family", 2000, alternative="b")
    assert registry.lookup("INVENTED_family", 2000, alternative="a")[
        0
    ].rule_id == ("INVENTED_a")


def test_verified_table_membership_requires_quoted_evidence(tmp_path):
    invented_registry(tmp_path)
    raw = invented_payload()
    raw["table_definitions"] = [
        {"definition_id": "INVENTED_table", "status": "verified"}
    ]
    with pytest.raises(RegistryValidationError):
        CoverageRegistry.from_dict(raw, capture_root=tmp_path)
    raw["table_definitions"] = [
        {
            "definition_id": "INVENTED_table",
            "status": "TABLE_DEFINITION_UNVERIFIED",
            "reason": "INVENTED missing operational definition",
        }
    ]
    registry = CoverageRegistry.from_dict(raw, capture_root=tmp_path)
    with pytest.raises(TableDefinitionUnverifiedError):
        registry.table_definition("INVENTED_table")


def test_verified_ret_concept_cannot_backcast_outside_its_support(tmp_path):
    invented_registry(tmp_path)
    raw = invented_payload()
    raw["earnings_test"] = {
        "status": "verified",
        "citations": [INVENTED_CITATION],
        "verified_income_years": [2026],
    }
    registry = CoverageRegistry.from_dict(raw, capture_root=tmp_path)
    assert registry.earnings_test_concept(2026)["status"] == "verified"
    with pytest.raises(OpenRuleError):
        registry.earnings_test_concept(1968)


def test_loader_verifies_nested_citation_and_path(tmp_path):
    registry = invented_registry(tmp_path)
    path = tmp_path / "invented_registry.json"
    path.write_text(registry.to_json())
    assert load_registry(path) == registry
    raw = registry.to_dict()
    raw["nested_citation"] = copy.deepcopy(INVENTED_CITATION)
    loaded = CoverageRegistry.from_dict(raw, capture_root=tmp_path)
    assert loaded.rules == registry.rules
    assert dict(loaded.metadata["nested_citation"]) == INVENTED_CITATION


def test_loader_accepts_separate_registry_and_capture_directories(tmp_path):
    captures = tmp_path / "captures"
    captures.mkdir()
    registry = invented_registry(captures)
    path = tmp_path / "registry.json"
    path.write_text(registry.to_json())
    assert load_registry(path, capture_root=captures) == registry
    with pytest.raises(CaptureIntegrityError):
        load_registry(path)


@pytest.mark.parametrize(
    "mutation", ["empty_cites", "date", "range", "field", "status"]
)
def test_schema_rejects_malformed_rows(mutation):
    row = invented_row()
    if mutation == "empty_cites":
        row["citations"] = []
    elif mutation == "date":
        row["effective_start"] = "1968-1-1"
    elif mutation == "range":
        row["effective_end"] = "1967-12-31"
    elif mutation == "field":
        row["extra"] = "INVENTED extra field"
    else:
        row["identification_class"] = "pending_means_identified"
    with pytest.raises(RegistryValidationError):
        CoverageRule.from_dict(row)


@given(st.lists(st.just(INVENTED_CITATION), max_size=3))
@settings(deadline=None)
def test_every_rule_requires_at_least_one_pinned_citation(citations):
    row = invented_row()
    row["citations"] = citations
    if citations:
        assert CoverageRule.from_dict(row).citations
    else:
        with pytest.raises(
            RegistryValidationError, match="at least one citation"
        ):
            CoverageRule.from_dict(row)


@given(st.sampled_from(sorted(CONSEQUENCES)), st.booleans())
@settings(deadline=None)
def test_residual_default_equals_top_level_consequence(consequence, mismatch):
    row = invented_row()
    row["consequence"] = consequence
    row["residual_default"]["consequence"] = consequence
    assert (
        CoverageRule.from_dict(row).residual_default["consequence"]
        == consequence
    )
    if mismatch:
        row["residual_default"]["consequence"] = (
            "noncovered" if consequence == "covered" else "covered"
        )
        with pytest.raises(RegistryValidationError, match="residual default"):
            CoverageRule.from_dict(row)


@given(st.sampled_from(sorted(CONSEQUENCES)), st.booleans())
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_lookup_returns_validated_cases_and_residual(
    tmp_path, consequence, fact
):
    row = invented_row()
    row["cases"] = [
        invented_case("invented_case", 1, consequence, when={"amount": fact})
    ]
    registry = invented_registry(tmp_path, [row])
    result = registry.lookup("INVENTED_family", 2024)[0]
    assert result.cases[0]["when"]["amount"] is fact
    assert result.cases[0]["consequence"] == consequence
    assert result.residual_default["consequence"] == result.consequence
    assert result.resolve({"invented_case"})["consequence"] == consequence
    assert result.resolve(()) == result.residual_default
    assert CoverageRule.from_dict(result.to_dict()) == result
    with pytest.raises(TypeError):
        result.cases[0]["when"]["amount"] = not fact


def invented_case(case_id, precedence, consequence="covered", **extra):
    case = {
        "case_id": case_id,
        "precedence": precedence,
        "when": {"amount": f"INVENTED condition for {case_id}"},
        "consequence": consequence,
    }
    case.update(extra)
    return case


@given(
    st.sampled_from(
        [
            "consequence",
            "when",
            "undeclared_fact",
            "case_id_missing",
            "case_id_format",
            "case_id_duplicate",
            "unknown_field",
        ]
    )
)
@settings(deadline=None)
def test_malformed_case_is_refused(field):
    row = invented_row()
    row["cases"] = [
        invented_case("invented_a", 1),
        invented_case("invented_b", 2, "noncovered"),
    ]
    CoverageRule.from_dict(row)
    case = row["cases"][0]
    if field == "consequence":
        case[field] = "unresolved"
    elif field == "when":
        case[field] = {}
    elif field == "undeclared_fact":
        case["when"] = {"occupation": "INVENTED undeclared fact"}
    elif field == "case_id_missing":
        del case["case_id"]
    elif field == "case_id_format":
        case["case_id"] = "INVENTED Case"
    elif field == "case_id_duplicate":
        case["case_id"] = "invented_b"
    else:
        case["INVENTED_extra"] = "INVENTED"
    with pytest.raises(RegistryValidationError, match="case"):
        CoverageRule.from_dict(row)


@given(
    st.sampled_from(["gap", "duplicate", "zero", "boolean", "text", "missing"])
)
@settings(deadline=None)
def test_case_precedence_runs_from_one_without_gaps(defect):
    row = invented_row()
    first = invented_case("invented_a", 1)
    second = invented_case("invented_b", 2, "noncovered")
    row["cases"] = [first, second]
    CoverageRule.from_dict(row)
    if defect == "gap":
        second["precedence"] = 3
    elif defect == "duplicate":
        second["precedence"] = 1
    elif defect == "zero":
        first["precedence"], second["precedence"] = 0, 1
    elif defect == "boolean":
        first["precedence"] = True
    elif defect == "text":
        second["precedence"] = "2"
    else:
        del second["precedence"]
    with pytest.raises(RegistryValidationError, match="case"):
        CoverageRule.from_dict(row)


@given(st.lists(st.sampled_from(sorted(CONSEQUENCES)), max_size=6), st.data())
@settings(deadline=None)
def test_first_matching_case_by_precedence_decides(consequences, data):
    cases = [
        invented_case(f"invented_case_{rank}", rank, consequence)
        for rank, consequence in enumerate(consequences, 1)
    ]
    rank_of = {case["case_id"]: case["precedence"] for case in cases}
    row = invented_row()
    row["cases"] = data.draw(st.permutations(cases))
    rule = CoverageRule.from_dict(row)
    row["cases"] = cases
    assert CoverageRule.from_dict(row) == rule
    assert [c["precedence"] for c in rule.cases] == sorted(rank_of.values())
    matched = (
        data.draw(st.sets(st.sampled_from(sorted(rank_of))))
        if cases
        else set()
    )
    result = rule.resolve(matched)
    if matched:
        winner = min(matched, key=rank_of.__getitem__)
        assert result["case_id"] == winner
        assert result["consequence"] == consequences[rank_of[winner] - 1]
    else:
        assert result == rule.residual_default


@given(
    st.sampled_from(
        [
            "valid",
            "later",
            "same_consequence",
            "unknown",
            "self",
            "empty",
            "duplicate",
        ]
    )
)
@settings(deadline=None)
def test_case_override_precedes_and_changes_its_target(kind):
    row = invented_row()
    exception = invented_case(
        "invented_exception", 1, "covered", overrides=["invented_exclusion"]
    )
    exclusion = invented_case("invented_exclusion", 2, "noncovered")
    row["cases"] = [exclusion, exception]
    if kind == "later":
        exception["precedence"], exclusion["precedence"] = 2, 1
    elif kind == "same_consequence":
        exclusion["consequence"] = "covered"
    elif kind == "unknown":
        exception["overrides"] = ["invented_missing"]
    elif kind == "self":
        exception["overrides"] = ["invented_exception"]
    elif kind == "empty":
        exception["overrides"] = []
    elif kind == "duplicate":
        exception["overrides"] = ["invented_exclusion"] * 2
    if kind != "valid":
        with pytest.raises(RegistryValidationError, match="overrid"):
            CoverageRule.from_dict(row)
        return
    rule = CoverageRule.from_dict(row)
    both = {"invented_exclusion", "invented_exception"}
    assert rule.resolve(both)["consequence"] == "covered"
    assert rule.resolve({"invented_exclusion"})["consequence"] == "noncovered"


def test_resolve_separates_caller_errors_from_refusals():
    row = invented_row()
    row["cases"] = [invented_case("invented_a", 1)]
    rule = CoverageRule.from_dict(row)
    with pytest.raises(UnknownIdentifierError) as caught:
        rule.resolve({"invented_typo"})
    assert not isinstance(caught.value, CoverageRegistryError)
    for malformed in ("invented_a", [1], None):
        with pytest.raises(TypeError):
            rule.resolve(malformed)
    row["cases"] = []
    row["open_reason"] = "INVENTED unresolved legal question"
    row["consequence"] = None
    row["residual_default"]["consequence"] = None
    row["open_alternatives"] = [
        {"name": "INVENTED_a", "description": "INVENTED first reading"},
        {"name": "INVENTED_b", "description": "INVENTED second reading"},
    ]
    with pytest.raises(OpenRuleError):
        CoverageRule.from_dict(row).resolve(())


@given(
    st.sampled_from([None, "open"]),
    st.sampled_from(["covered", "noncovered", "covered_above_threshold"]),
)
@settings(deadline=None)
def test_open_row_has_named_options_and_no_chosen_consequence(
    open_value, chosen
):
    row = invented_row()
    row["open_reason"] = "INVENTED unresolved legal question"
    row["consequence"] = open_value
    row["residual_default"]["consequence"] = open_value
    row["open_alternatives"] = [
        {"name": "INVENTED_a", "description": "INVENTED first reading"},
        {"name": "INVENTED_b", "description": "INVENTED second reading"},
    ]
    parsed = CoverageRule.from_dict(row)
    assert parsed.consequence in {None, "open"}
    assert len({o["name"] for o in parsed.open_alternatives}) >= 2
    saved_alternatives = row["open_alternatives"]
    row["open_alternatives"] = []
    with pytest.raises(RegistryValidationError, match="named alternatives"):
        CoverageRule.from_dict(row)
    row["open_alternatives"] = saved_alternatives
    row["consequence"] = chosen
    row["residual_default"]["consequence"] = chosen
    with pytest.raises(RegistryValidationError, match="chosen consequence"):
        CoverageRule.from_dict(row)


@given(
    st.sampled_from(
        ["chosen_reading", "selected_reading", "operative_current_text"]
    )
)
@settings(deadline=None)
def test_open_row_cannot_choose_an_operative_reading(field):
    row = invented_row()
    row["open_reason"] = "INVENTED unresolved legal question"
    row["consequence"] = None
    row["residual_default"]["consequence"] = None
    row["open_alternatives"] = [
        {"name": "INVENTED_a", "description": "INVENTED first reading"},
        {"name": "INVENTED_b", "description": "INVENTED second reading"},
    ]
    row["parameters"][field] = "INVENTED_a"
    with pytest.raises(RegistryValidationError, match="chosen reading"):
        CoverageRule.from_dict(row)
    row["parameters"] = {"INVENTED_nested": [{field: "INVENTED_a"}]}
    with pytest.raises(RegistryValidationError, match="chosen reading"):
        CoverageRule.from_dict(row)


@given(st.text().filter(lambda value: value != "unresolved"))
@settings(deadline=None)
def test_rare_strict_reading_remains_unresolved(value):
    row = invented_row()
    row["rare_exclusion"] = {
        "strict": value,
        "negligible_candidate": None,
        "searches": ["INVENTED search"],
    }
    with pytest.raises(RegistryValidationError, match="strict reading"):
        CoverageRule.from_dict(row)


@given(st.integers(0, 4999))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_quarter_sum_cannot_breach_statutory_nondecrease(tmp_path, cents):
    index = {
        "kind": "quarter_of_coverage_sum",
        "first_year": 2025,
        "last_year": 2026,
        "parameter_name": "INVENTED_quarters_cents",
        "multiplier_numerator": 1,
        "multiplier_denominator": 2,
    }
    registry = invented_registry(
        tmp_path, thresholds=[invented_threshold(indexing=index)]
    )
    with pytest.raises(ValueError, match="statutory nondecrease"):
        registry.threshold(
            "INVENTED_threshold",
            2026,
            index_inputs={"INVENTED_quarters_cents": [cents] * 4},
        )


@pytest.mark.parametrize("escape", ["traversal", "absolute", "symlink"])
@given(st.binary(min_size=1, max_size=100))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_capture_path_escape_is_refused_with_existing_matching_bytes(
    tmp_path, escape, data
):
    captures = tmp_path / "captures"
    captures.mkdir(exist_ok=True)
    registry = invented_registry(captures)
    outside = tmp_path / "outside.html"
    outside.write_bytes(data)
    link = captures / "outside_link.html"
    link.unlink(missing_ok=True)
    link.symlink_to(outside)
    paths = {
        "traversal": "../outside.html",
        "absolute": str(outside),
        "symlink": link.name,
    }
    raw = registry.to_dict()
    raw["nested_citation"] = {
        **INVENTED_CITATION,
        "capture": paths[escape],
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    with pytest.raises(
        CaptureIntegrityError, match="escapes capture directory"
    ):
        CoverageRegistry.from_dict(raw, capture_root=captures)


@given(st.sampled_from(["sha256", "authority", "location"]))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_any_nested_capture_key_requires_a_complete_citation(
    tmp_path, missing
):
    registry = invented_registry(tmp_path)
    raw = registry.to_dict()
    raw["nested_citation"] = copy.deepcopy(INVENTED_CITATION)
    del raw["nested_citation"][missing]
    with pytest.raises(RegistryValidationError, match="incomplete citation"):
        CoverageRegistry.from_dict(raw, capture_root=tmp_path)


@pytest.mark.parametrize("verified", [True, False])
@given(st.sampled_from(["sha256", "authority", "location"]))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_all_table_definition_citations_are_schema_validated(
    tmp_path, verified, missing
):
    invented_registry(tmp_path)
    good = {**INVENTED_CITATION, "quote": "INVENTED quote"}
    bad = copy.deepcopy(INVENTED_CITATION)
    del bad[missing]
    raw = invented_payload()
    raw["table_definitions"] = [
        {
            "definition_id": "INVENTED_table",
            "status": (
                "verified" if verified else "TABLE_DEFINITION_UNVERIFIED"
            ),
            "source_definition": "INVENTED definition",
            "reason": "INVENTED unverified definition",
            "citations": [good, bad],
        }
    ]
    with pytest.raises(RegistryValidationError, match="incomplete citation"):
        CoverageRegistry.from_dict(raw, capture_root=tmp_path)


@pytest.mark.parametrize("year", [True, "2024", None])
def test_bad_caller_year_type_raises_type_error(tmp_path, year):
    registry = invented_registry(tmp_path)
    with pytest.raises(TypeError, match="integer"):
        registry.lookup("INVENTED_family", year)


@pytest.mark.parametrize("service_date", [None, "2024-01-01", 2024])
def test_bad_caller_service_date_type_raises_type_error(
    tmp_path, service_date
):
    registry = invented_registry(tmp_path)
    with pytest.raises(TypeError, match="must be a date"):
        registry.lookup_date("INVENTED_family", service_date)


@pytest.mark.parametrize(
    "value, error",
    [
        (True, TypeError),
        (1.5, TypeError),
        ("bad", ValueError),
        ("-1", ValueError),
        (None, TypeError),
    ],
)
def test_bad_caller_index_raises_argument_error(tmp_path, value, error):
    registry = invented_registry(
        tmp_path, thresholds=[invented_threshold(indexing=INVENTED_INDEX)]
    )
    with pytest.raises(error, match="exact index input") as caught:
        registry.threshold(
            "INVENTED_threshold",
            2025,
            index_inputs={"national_average_wage_index_2023": value},
        )
    assert type(caught.value) is error


def test_source_text_omits_script_and_style_content(tmp_path):
    path = tmp_path / "INVENTED_source.html"
    path.write_text(
        "<script>INVENTED hidden script</script><p>INVENTED passage</p><style>INVENTED hidden style</style>"
    )
    assert source_text(path) == "INVENTED passage"


@given(st.integers(1969, 2025), st.integers(1, 12), st.integers(2, 28))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_taxable_year_boundary_uses_actual_start_not_every_calendar_day(
    tmp_path, year, month, day
):
    from datetime import timedelta

    boundary = date(year, month, day)
    before = invented_row(rule_id="INVENTED_before")
    after = invented_row(rule_id="INVENTED_after")
    before["effective_end"] = (boundary - timedelta(days=1)).isoformat()
    after["effective_start"] = boundary.isoformat()
    for row in (before, after):
        row["parameters"]["effective_basis"] = "taxable_year_start"
        row["trigger_facts"].append("taxable_year_start")
    registry = invented_registry(tmp_path, [before, after])
    assert [r.rule_id for r in registry.lookup("INVENTED_family", year)] == [
        "INVENTED_before"
    ]
    assert (
        registry.lookup_date("INVENTED_family", boundary)[0].rule_id
        == "INVENTED_after"
    )
    assert (
        registry.lookup("INVENTED_family", year + 1)[0].rule_id
        == "INVENTED_after"
    )
    del after["parameters"]["effective_basis"]
    with pytest.raises(RegistryValidationError, match="mixes service"):
        invented_registry(tmp_path, [before, after])
    after["parameters"]["effective_basis"] = "taxable_year_start"
    before["trigger_facts"].remove("taxable_year_start")
    with pytest.raises(RegistryValidationError, match="taxable-year axis"):
        invented_registry(tmp_path, [before, after])


@given(st.permutations(tuple(range(5))), st.integers(1968, 2026))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_arbitrary_row_permutations_preserve_lookup_and_round_trip(
    tmp_path, order, year
):
    spans = [
        (1968, 1979),
        (1980, 1989),
        (1990, 1999),
        (2000, 2009),
        (2010, 2026),
    ]
    rows = [
        invented_row(start, end, f"INVENTED_{i}")
        for i, (start, end) in enumerate(spans)
    ]
    original = invented_registry(tmp_path, rows)
    permuted = invented_registry(tmp_path, [rows[i] for i in order])
    assert original.to_json() == permuted.to_json()
    assert original.lookup("INVENTED_family", year) == permuted.lookup(
        "INVENTED_family", year
    )
    assert (
        CoverageRegistry.from_dict(
            json.loads(permuted.to_json()), capture_root=tmp_path
        )
        == original
    )


@given(st.binary(min_size=1, max_size=100))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_capture_symlink_within_root_is_accepted(tmp_path, data):
    registry = invented_registry(tmp_path)
    path = tmp_path / "INVENTED_inside.html"
    path.write_bytes(data)
    link = tmp_path / "INVENTED_inside_link.html"
    link.unlink(missing_ok=True)
    link.symlink_to(path)
    raw = registry.to_dict()
    raw["nested_citation"] = {
        **INVENTED_CITATION,
        "capture": link.name,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    assert (
        CoverageRegistry.from_dict(raw, capture_root=tmp_path).rules
        == registry.rules
    )
