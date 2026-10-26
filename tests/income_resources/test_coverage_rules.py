"""Schema and lookup tests using invented legal rows and invented captures.

All monetary values, text and dates in these fixtures are invented examples
of the schema. They make no claim about actual coverage law.
"""

import copy
import graphlib
import hashlib
import json
from datetime import date, timedelta
from fractions import Fraction

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.coverage_rules import (
    CONSEQUENCES,
    EFFECTIVE_BASES,
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
INVENTED_AXIS = "INVENTED effective-date clause for schema tests only."
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


INVENTED_TARGET_FAMILY = "INVENTED_other_family"


def invented_target_row():
    """An invented second family that a deferral can name."""
    row = invented_row(rule_id="INVENTED_other_rule")
    row["family"] = INVENTED_TARGET_FAMILY
    return row


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
    if not present:
        with pytest.raises(UnknownIdentifierError):
            registry.lookup(family, year)
        return
    try:
        rules = registry.lookup(family, year)
    except CoverageRegistryError:
        assert not 1980 <= year <= 2000
    else:
        assert rules
        assert 1980 <= year <= 2000


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


@given(st.lists(st.booleans(), min_size=1, max_size=3))
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@example([False])
@example([False, True])
def test_verified_table_membership_requires_quoted_evidence(tmp_path, quoted):
    """Review r2 low 1: the fixture is complete except for the quote."""
    invented_registry(tmp_path)
    raw = invented_payload()
    citations = []
    for has_quote in quoted:
        citation = copy.deepcopy(INVENTED_CITATION)
        if has_quote:
            citation["quote"] = "Invented source passage"
        citations.append(citation)
    raw["table_definitions"] = [
        {
            "definition_id": "INVENTED_table",
            "status": "verified",
            "source_definition": "INVENTED membership definition",
            "citations": citations,
        }
    ]
    if any(quoted):
        registry = CoverageRegistry.from_dict(raw, capture_root=tmp_path)
        assert registry.table_definition("INVENTED_table")["status"] == (
            "verified"
        )
    else:
        with pytest.raises(
            RegistryValidationError, match="quoted source passage"
        ):
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
    if consequence == "deferred":
        row["residual_default"]["defers_to"] = [INVENTED_TARGET_FAMILY]
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
    registry = invented_registry(tmp_path, [row, invented_target_row()])
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
    if consequence == "deferred":
        case["defers_to"] = [INVENTED_TARGET_FAMILY]
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


DEFERRAL_NAMES = [
    "INVENTED_family",
    INVENTED_TARGET_FAMILY,
    "INVENTED_third_family",
    " ",
]


@given(
    st.sampled_from(["case", "residual"]),
    st.sampled_from(sorted(CONSEQUENCES)),
    st.none() | st.lists(st.sampled_from(DEFERRAL_NAMES), max_size=4),
)
@example("case", "deferred", ["INVENTED_family"])
@example("residual", "deferred", [INVENTED_TARGET_FAMILY, "INVENTED_family"])
@example("case", "deferred", [INVENTED_TARGET_FAMILY] * 2)
@example("residual", "deferred", [" "])
@example("residual", "deferred", [])
@example("case", "deferred", None)
@example("case", "covered", [INVENTED_TARGET_FAMILY])
@example("residual", "deferred", [INVENTED_TARGET_FAMILY])
@settings(deadline=None)
def test_defers_to_appears_exactly_on_deferred_outcomes(
    where, consequence, targets
):
    """A deferred outcome names distinct other families; no other does."""
    row = invented_row()
    outcome = {"consequence": consequence}
    if targets is not None:
        outcome["defers_to"] = targets
    if where == "case":
        row["cases"] = [
            {
                "case_id": "invented_case",
                "precedence": 1,
                "when": {"amount": True},
                **outcome,
            }
        ]
    else:
        row["consequence"] = consequence
        row["residual_default"].update(outcome)
    if consequence == "deferred":
        valid = (
            bool(targets)
            and len(set(targets)) == len(targets)
            and all(target.strip() for target in targets)
            and row["family"] not in targets
        )
    else:
        valid = targets is None
    if not valid:
        with pytest.raises(RegistryValidationError, match="defer"):
            CoverageRule.from_dict(row)
        return
    rule = CoverageRule.from_dict(row)
    resolved = rule.resolve({"invented_case"} if where == "case" else ())
    assert resolved["consequence"] == consequence
    assert list(resolved.get("defers_to", ())) == (targets or [])
    assert CoverageRule.from_dict(rule.to_dict()) == rule


@given(st.integers(1, 5), st.booleans(), st.data())
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_registry_refuses_unknown_or_cyclic_deferrals(
    tmp_path, size, unknown, data
):
    """Every deferral chain ends at a family that decides.

    The reference is the standard library's topological sort: the registry
    must accept exactly the acyclic family graphs whose targets exist.
    """
    families = [f"INVENTED_family_{index}" for index in range(size)]
    pairs = [(a, b) for a in families for b in families if a != b]
    edges = data.draw(st.sets(st.sampled_from(pairs))) if pairs else set()
    graph = {f: sorted(b for a, b in edges if a == f) for f in families}
    rows = []
    for index, family in enumerate(families):
        row = invented_row(rule_id=f"INVENTED_rule_{index}")
        row["family"] = family
        targets = list(graph[family])
        if unknown and index == 0:
            targets.append("INVENTED_missing_family")
        if targets and data.draw(st.booleans()):
            row["consequence"] = "deferred"
            row["residual_default"]["consequence"] = "deferred"
            row["residual_default"]["defers_to"] = targets
        elif targets:
            row["cases"] = [
                invented_case(
                    "invented_case", 1, "deferred", defers_to=targets
                )
            ]
        rows.append(row)
    try:
        tuple(graphlib.TopologicalSorter(graph).static_order())
        acyclic = True
    except graphlib.CycleError:
        acyclic = False
    if unknown or not acyclic:
        message = "names no family" if unknown else "deferral cycle"
        with pytest.raises(RegistryValidationError, match=message):
            invented_registry(tmp_path, rows)
        return
    registry = invented_registry(tmp_path, rows)
    for start in families:
        frontier, steps = {start}, 0
        while frontier:
            assert steps <= size, "deferral chain longer than the registry"
            following = set()
            for family in frontier:
                (rule,) = registry.lookup(family, 2024)
                for outcome in (rule.residual_default, *rule.cases):
                    following.update(outcome.get("defers_to", ()))
            frontier, steps = following, steps + 1


def test_deferral_to_an_unknown_family_is_refused(tmp_path):
    row = invented_row()
    row["cases"] = [invented_case("invented_case", 1, "deferred")]
    assert invented_registry(tmp_path, [row, invented_target_row()])
    with pytest.raises(RegistryValidationError, match="names no family"):
        invented_registry(tmp_path, [row])


@given(
    st.sampled_from(sorted(CONSEQUENCES)),
    st.booleans(),
    st.booleans(),
    st.sampled_from(["INVENTED reason the condition decides nothing", " ", 7]),
)
@settings(deadline=None)
def test_case_free_basis_only_explains_case_free_non_excluding_rows(
    consequence, with_case, is_open, basis
):
    """``case_free_basis`` cannot hide an exclusion or a conditional row."""
    row = invented_row()
    row["parameters"]["case_free_basis"] = basis
    if is_open:
        row["open_reason"] = "INVENTED unresolved legal question"
        row["consequence"] = None
        row["residual_default"]["consequence"] = None
        row["open_alternatives"] = [
            {"name": "INVENTED_a", "description": "INVENTED first reading"},
            {"name": "INVENTED_b", "description": "INVENTED second reading"},
        ]
    else:
        row["consequence"] = consequence
        row["residual_default"]["consequence"] = consequence
        if consequence == "deferred":
            row["residual_default"]["defers_to"] = [INVENTED_TARGET_FAMILY]
    if with_case:
        row["cases"] = [invented_case("invented_case", 1)]
    valid = (
        isinstance(basis, str)
        and bool(basis.strip())
        and not is_open
        and not with_case
        and consequence not in {"noncovered", "deferred"}
    )
    if not valid:
        with pytest.raises(RegistryValidationError, match="case_free_basis"):
            CoverageRule.from_dict(row)
        return
    parsed = CoverageRule.from_dict(row)
    assert parsed.parameters["case_free_basis"] == basis
    assert parsed.resolve(()) == parsed.residual_default


@given(
    st.sampled_from(sorted(CONSEQUENCES)),
    st.booleans(),
    st.none() | st.integers(0, 3),
    st.booleans(),
)
@example("open", True, 2, False)
@example("open", True, 1, False)
@example("open", True, 2, True)
@example("open", False, 2, False)
@example("open", True, None, False)
@example("covered", True, 2, False)
@example("open", False, None, False)
@settings(deadline=None)
def test_open_case_sub_question_needs_reason_and_named_readings(
    consequence, with_reason, alternatives, duplicate
):
    """A closed row opens a sub-question only with a reason and readings.

    When the open case decides, resolve refuses; a higher-ranked case
    still wins, and an open case without a reason (missing facts) returns.
    """
    row = invented_row()
    first = invented_case("invented_first", 1, "covered")
    sub = invented_case("invented_sub_question", 2, consequence)
    if with_reason:
        sub["open_reason"] = "INVENTED_SUB_QUESTION: no capture settles it"
    if alternatives is not None:
        names = [f"INVENTED_reading_{i}" for i in range(alternatives)]
        if duplicate and alternatives >= 2:
            names[1] = names[0]
        sub["open_alternatives"] = [
            {"name": name, "description": f"INVENTED {name}"} for name in names
        ]
    row["cases"] = [first, sub]
    if not with_reason and alternatives is None:
        rule = CoverageRule.from_dict(row)
        assert rule.resolve({"invented_sub_question"})["consequence"] == (
            consequence
        )
        return
    valid = (
        consequence == "open"
        and with_reason
        and alternatives is not None
        and alternatives >= 2
        and not duplicate
    )
    if not valid:
        with pytest.raises(RegistryValidationError, match="open"):
            CoverageRule.from_dict(row)
        return
    rule = CoverageRule.from_dict(row)
    with pytest.raises(OpenRuleError, match="INVENTED_SUB_QUESTION"):
        rule.resolve({"invented_sub_question"})
    both = {"invented_first", "invented_sub_question"}
    assert rule.resolve(both)["case_id"] == "invented_first"
    assert rule.resolve(()) == rule.residual_default
    assert CoverageRule.from_dict(rule.to_dict()) == rule


def invented_boundary(side, when, kind="regulation_edition"):
    return {
        "side": side,
        "date": when,
        "kind": kind,
        "citation": copy.deepcopy(INVENTED_CITATION),
        "evidence": "INVENTED edition date, not a change in the law.",
    }


@given(
    st.sampled_from(["start", "end"]),
    st.sampled_from([-1, 0, 1]),
    st.sampled_from(["regulation_edition", "code_edition", "INVENTED"]),
    st.booleans(),
    st.sampled_from([None, "extra_field", "duplicate", "empty"]),
)
@example("end", 0, "regulation_edition", True, None)
@example("start", 0, "code_edition", True, None)
@example("start", 1, "code_edition", True, None)
@example("end", -1, "regulation_edition", True, None)
@example("end", 0, "INVENTED", True, None)
@example("start", 0, "code_edition", False, None)
@example("end", 0, "regulation_edition", True, "extra_field")
@example("end", 0, "regulation_edition", True, "duplicate")
@example("start", 0, "regulation_edition", True, "empty")
@settings(deadline=None)
def test_evidence_only_boundary_sits_on_its_row_edge(
    side, offset, kind, cited, defect
):
    row = invented_row(1980, 1995)
    edge = date(1980, 1, 1) if side == "start" else date(1996, 1, 1)
    entry = invented_boundary(
        side, (edge + timedelta(days=offset)).isoformat(), kind
    )
    if not cited:
        entry["citation"]["capture"] = "INVENTED_uncited.html"
    entries = [entry]
    if defect == "extra_field":
        entry["INVENTED_extra"] = "INVENTED"
    elif defect == "duplicate":
        entries.append(copy.deepcopy(entry))
    elif defect == "empty":
        entries = []
    row["parameters"]["evidence_only_boundaries"] = entries
    valid = (
        offset == 0
        and kind in {"regulation_edition", "code_edition"}
        and cited
        and defect is None
    )
    if not valid:
        with pytest.raises(RegistryValidationError, match="evidence"):
            CoverageRule.from_dict(row)
        return
    rule = CoverageRule.from_dict(row)
    assert rule.parameters["evidence_only_boundaries"][0]["side"] == side


@given(
    st.booleans(),
    st.booleans(),
    st.sampled_from([None, "kind", "capture"]),
)
@example(True, True, None)
@example(False, False, None)
@example(True, False, None)
@example(False, True, None)
@example(True, True, "kind")
@example(True, True, "capture")
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_adjacent_rows_record_an_evidence_boundary_alike(
    tmp_path, on_earlier, on_later, mismatch
):
    (tmp_path / "invented_two.html").write_bytes(INVENTED_BYTES)
    earlier = invented_row(1968, 1995, "INVENTED_earlier")
    later = invented_row(1996, 2026, "INVENTED_later")
    second = dict(INVENTED_CITATION, capture="invented_two.html")
    earlier["citations"].append(copy.deepcopy(second))
    later["citations"].append(copy.deepcopy(second))
    if on_earlier:
        earlier["parameters"]["evidence_only_boundaries"] = [
            invented_boundary("end", "1996-01-01")
        ]
    if on_later:
        entry = invented_boundary("start", "1996-01-01")
        if mismatch == "kind":
            entry["kind"] = "code_edition"
        elif mismatch == "capture":
            entry["citation"] = copy.deepcopy(second)
        later["parameters"]["evidence_only_boundaries"] = [entry]
    valid = on_earlier == on_later and (not on_later or mismatch is None)
    if not valid:
        with pytest.raises(RegistryValidationError, match="evidence-only"):
            invented_registry(tmp_path, [earlier, later])
        return
    registry = invented_registry(tmp_path, [earlier, later])
    assert [r.rule_id for r in registry.lookup("INVENTED_family", 1995)] == [
        "INVENTED_earlier"
    ]


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
        "<script>INVENTED hidden script</script><p>INVENTED passage</p>"
        "<style>INVENTED hidden style</style>"
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
        row["parameters"]["effective_basis_description"] = INVENTED_AXIS
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
    del after["parameters"]["effective_basis_description"]
    with pytest.raises(RegistryValidationError, match="mixes date axes"):
        invented_registry(tmp_path, [before, after])
    after["parameters"]["effective_basis_description"] = INVENTED_AXIS
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


# Review r2 low 1: each v2 guard has a property that fails without it.


@given(
    st.booleans(),
    st.sampled_from([None, *sorted(CONSEQUENCES)]),
    st.integers(0, 3),
    st.booleans(),
)
@example(True, "open", 1, False)
@example(True, None, 2, False)
@example(True, None, 2, True)
@example(False, "covered", 2, False)
@example(False, "covered", 0, False)
@example(False, None, 0, False)
@settings(deadline=None)
def test_open_and_closed_rows_follow_the_alternative_rules(
    is_open, consequence, count, duplicate
):
    """Open rows name two or more distinct readings; closed rows none."""
    row = invented_row()
    row["consequence"] = consequence
    row["residual_default"]["consequence"] = consequence
    if consequence == "deferred":
        row["residual_default"]["defers_to"] = [INVENTED_TARGET_FAMILY]
    row["open_reason"] = "INVENTED open legal question" if is_open else None
    names = [f"INVENTED_reading_{i}" for i in range(count)]
    if duplicate and count >= 2:
        names[1] = names[0]
    row["open_alternatives"] = [
        {"name": name, "description": f"INVENTED {name}"} for name in names
    ]
    distinct = len(set(names)) == len(names)
    if is_open:
        valid = distinct and consequence in {None, "open"} and count >= 2
    else:
        valid = distinct and consequence is not None and count == 0
    if not valid:
        with pytest.raises(RegistryValidationError):
            CoverageRule.from_dict(row)
        return
    rule = CoverageRule.from_dict(row)
    assert [o["name"] for o in rule.open_alternatives] == names


@given(
    st.dictionaries(
        st.sampled_from(["cases", "case_list", "notes", "invented_value"]),
        st.integers(0, 3),
        max_size=4,
    )
)
@example({"cases": 1})
@settings(deadline=None)
def test_cases_live_in_the_schema_not_in_parameters(parameters):
    row = invented_row()
    row["parameters"] = parameters
    if "cases" in parameters:
        with pytest.raises(RegistryValidationError, match="cases belong"):
            CoverageRule.from_dict(row)
        return
    assert dict(CoverageRule.from_dict(row).parameters) == parameters


@given(
    st.one_of(
        st.booleans(),
        st.text(max_size=4),
        st.integers(),
        st.none(),
        st.floats(allow_nan=False),
        st.lists(st.booleans(), max_size=2),
    )
)
@example(0)
@example(None)
@example("  ")
@example(True)
@example("INVENTED condition")
@settings(deadline=None)
def test_case_conditions_are_nonempty_text_or_boolean(condition):
    row = invented_row()
    row["cases"] = [invented_case("invented_a", 1, when={"amount": condition})]
    valid = isinstance(condition, bool) or (
        isinstance(condition, str) and bool(condition.strip())
    )
    if not valid:
        with pytest.raises(RegistryValidationError, match="case condition"):
            CoverageRule.from_dict(row)
        return
    rule = CoverageRule.from_dict(row)
    assert rule.cases[0]["when"]["amount"] == condition


def invented_example(**extra):
    example = {
        "example_id": "INVENTED_example",
        "income_year": 2024,
        "citation": copy.deepcopy(INVENTED_CITATION),
        "source_passage": "INVENTED passage; no published legal example.",
        "expected_rule_id": "INVENTED_rule",
        "calculation": "INVENTED_calculation",
        "published_inputs": {"INVENTED_input": 1},
        "published_outputs": {"INVENTED_output": 1},
    }
    example.update(extra)
    return example


@given(
    st.booleans(),
    st.dictionaries(
        st.text(min_size=1, max_size=4), st.integers(), max_size=2
    ),
)
@example(True, {})
@settings(deadline=None)
def test_examples_test_outcomes_not_repeated_parameters(with_field, payload):
    row = invented_row()
    example = invented_example()
    if with_field:
        example["expected_parameters"] = payload
    row["worked_examples"] = [example]
    if with_field:
        with pytest.raises(RegistryValidationError, match="outcomes"):
            CoverageRule.from_dict(row)
        return
    assert CoverageRule.from_dict(row).worked_examples


def nonempty_passages(value):
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(part, str) and bool(part.strip()) for part in value)
    )


@given(
    st.one_of(
        st.lists(st.one_of(st.text(max_size=5), st.integers()), max_size=3),
        st.text(max_size=5),
        st.none(),
    )
)
@example(["INVENTED second column line"])
@example([])
@example([" "])
@example("INVENTED not a list")
@settings(deadline=None)
def test_supporting_passages_are_nonempty_text(passages):
    """Review r2 low 11: an interleaved example keeps its other lines."""
    row = invented_row()
    row["worked_examples"] = [invented_example(supporting_passages=passages)]
    if not nonempty_passages(passages):
        with pytest.raises(RegistryValidationError, match="supporting"):
            CoverageRule.from_dict(row)
        return
    (parsed,) = CoverageRule.from_dict(row).worked_examples
    assert list(parsed["supporting_passages"]) == passages
    row["worked_examples"] = [invented_example()]
    assert CoverageRule.from_dict(row).worked_examples


def recorded_search(search):
    if isinstance(search, str):
        return bool(search.strip())
    return (
        isinstance(search, dict)
        and isinstance(search.get("query"), str)
        and bool(search["query"].strip())
    )


@given(
    st.lists(
        st.one_of(
            st.text(max_size=5),
            st.fixed_dictionaries({"query": st.text(max_size=5)}),
            st.integers(),
        ),
        max_size=3,
    )
)
@example([])
@example([" "])
@example([{"query": ""}])
@example(["INVENTED search"])
@settings(deadline=None)
def test_null_prevalence_bound_requires_recorded_searches(searches):
    row = invented_row()
    row["rare_exclusion"] = {
        "strict": "unresolved",
        "negligible_candidate": None,
        "searches": searches,
    }
    if not (searches and all(recorded_search(s) for s in searches)):
        with pytest.raises(RegistryValidationError, match="recorded searches"):
            CoverageRule.from_dict(row)
        return
    assert CoverageRule.from_dict(row).rare_exclusion["searches"]


# Review r2 low 2: a year recorded in the registry is data.

REGISTRY_YEARS = st.one_of(
    st.integers(1900, 2100),
    st.text(max_size=4),
    st.none(),
    st.booleans(),
    st.floats(allow_nan=False),
)


def valid_registry_year(year):
    return type(year) is int and 1968 <= year <= 2026


@given(REGISTRY_YEARS)
@example("1999")
@example(1950)
@example(1999)
@settings(deadline=None)
def test_example_income_year_errors_are_registry_data_errors(year):
    row = invented_row()
    row["worked_examples"] = [invented_example(income_year=year)]
    if not valid_registry_year(year):
        with pytest.raises(RegistryValidationError, match="income_year"):
            CoverageRule.from_dict(row)
        return
    assert CoverageRule.from_dict(row).worked_examples[0]["income_year"] == (
        year
    )


@given(REGISTRY_YEARS)
@example("2026")
@example(1950)
@example(2026)
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_ret_verified_years_errors_are_registry_data_errors(tmp_path, year):
    invented_registry(tmp_path)
    raw = invented_payload()
    raw["earnings_test"] = {
        "status": "verified",
        "citations": [INVENTED_CITATION],
        "verified_income_years": [year],
    }
    if not valid_registry_year(year):
        with pytest.raises(RegistryValidationError, match="RET"):
            CoverageRegistry.from_dict(raw, capture_root=tmp_path)
        return
    registry = CoverageRegistry.from_dict(raw, capture_root=tmp_path)
    assert registry.earnings_test_concept(year)["status"] == "verified"


@given(st.one_of(st.integers(1900, 2100), st.text(max_size=4)))
@example("1950")
@example("02024")
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_threshold_year_errors_are_registry_data_errors(tmp_path, year):
    key = str(year)
    threshold = invented_threshold(values={key: 100})
    canonical = key.isascii() and key.isdigit() and str(int(key)) == key
    if not (canonical and 1968 <= int(key) <= 2026):
        with pytest.raises(RegistryValidationError, match="threshold year"):
            invented_registry(tmp_path, thresholds=[threshold])
        return
    registry = invented_registry(tmp_path, thresholds=[threshold])
    assert registry.threshold("INVENTED_threshold", int(key)) == 100


# Review r2 low 3: a typo is a caller error, never a legal refusal.


def test_refusals_and_caller_errors_have_disjoint_types():
    assert not issubclass(CoverageRegistryError, (ValueError, LookupError))
    assert issubclass(UnknownIdentifierError, LookupError)
    assert not issubclass(UnknownIdentifierError, CoverageRegistryError)
    for refusal in (
        NoRuleError,
        RuleGapError,
        OpenRuleError,
        AlternativeRequiredError,
        ThresholdUnavailableError,
        TableDefinitionUnverifiedError,
        RegistryValidationError,
        CaptureIntegrityError,
    ):
        assert issubclass(refusal, CoverageRegistryError)
        assert not issubclass(refusal, (ValueError, LookupError))


@given(st.text(min_size=1, max_size=8))
@example("INVENTED_famliy")
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_unknown_identifiers_raise_a_caller_error(tmp_path, name):
    invented_registry(tmp_path)
    raw = invented_payload(thresholds=[invented_threshold()])
    raw["table_definitions"] = [
        {
            "definition_id": "INVENTED_table",
            "status": "TABLE_DEFINITION_UNVERIFIED",
            "reason": "INVENTED missing operational definition",
        }
    ]
    registry = CoverageRegistry.from_dict(raw, capture_root=tmp_path)
    calls = []
    if name != "INVENTED_family":
        calls += [
            lambda: registry.lookup(name, 2000),
            lambda: registry.lookup_date(name, date(2000, 1, 1)),
        ]
    if name != "INVENTED_table":
        calls.append(lambda: registry.table_definition(name))
    if name != "INVENTED_threshold":
        calls.append(lambda: registry.threshold(name, 2024))
    for call in calls:
        with pytest.raises(UnknownIdentifierError) as caught:
            call()
        assert not isinstance(caught.value, CoverageRegistryError)
    with pytest.raises(TableDefinitionUnverifiedError):
        registry.table_definition("INVENTED_table")


# Review r2 low 4: the date axis is an enum the loader checks.


@given(
    st.sampled_from(
        [None, *sorted(EFFECTIVE_BASES), "INVENTED prose basis", ""]
    ),
    st.booleans(),
)
@example("INVENTED prose basis", True)
@example("payment_date", False)
@example(None, True)
@example("service_date", False)
@settings(deadline=None)
def test_effective_basis_is_an_enum_with_its_clause(basis, described):
    row = invented_row()
    row["trigger_facts"].append("taxable_year_start")
    if basis is not None:
        row["parameters"]["effective_basis"] = basis
    if described:
        row["parameters"]["effective_basis_description"] = INVENTED_AXIS
    if basis is None:
        valid = not described
    else:
        valid = basis in EFFECTIVE_BASES and (
            described or basis == "service_date"
        )
    if not valid:
        with pytest.raises(RegistryValidationError, match="effective_basis"):
            CoverageRule.from_dict(row)
        return
    rule = CoverageRule.from_dict(row)
    assert rule.date_axis == (basis or "service_date")


@given(
    st.sampled_from(sorted(EFFECTIVE_BASES)),
    st.sampled_from(sorted(EFFECTIVE_BASES)),
    st.dates(date(1969, 1, 2), date(2025, 12, 31)),
)
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_one_family_keeps_one_date_axis(tmp_path, first, second, boundary):
    before = invented_row(rule_id="INVENTED_before")
    after = invented_row(rule_id="INVENTED_after")
    before["effective_end"] = (boundary - timedelta(days=1)).isoformat()
    after["effective_start"] = boundary.isoformat()
    for row, basis in ((before, first), (after, second)):
        row["parameters"]["effective_basis"] = basis
        row["parameters"]["effective_basis_description"] = INVENTED_AXIS
        row["trigger_facts"].append("taxable_year_start")
    if first != second:
        with pytest.raises(RegistryValidationError, match="mixes date axes"):
            invented_registry(tmp_path, [before, after])
        return
    registry = invented_registry(tmp_path, [before, after])
    found = [
        r.rule_id for r in registry.lookup("INVENTED_family", boundary.year)
    ]
    if first == "taxable_year_start" or boundary == date(boundary.year, 1, 1):
        expected = (
            ["INVENTED_after"]
            if boundary == date(boundary.year, 1, 1)
            else ["INVENTED_before"]
        )
    else:
        expected = ["INVENTED_before", "INVENTED_after"]
    assert found == expected
    assert [
        r.rule_id for r in registry.lookup_date("INVENTED_family", boundary)
    ] == ["INVENTED_after"]


# Review r2 low 14: supplied inputs and alternatives are never ignored.


def exact_nonnegative(value):
    if isinstance(value, (bool, float)) or value is None:
        return False
    try:
        return Fraction(value) >= 0
    except (ValueError, TypeError, ZeroDivisionError):
        return False


@given(
    st.one_of(
        st.integers(-5, 5),
        st.text(max_size=3),
        st.none(),
        st.booleans(),
        st.floats(allow_nan=False),
    ),
    st.booleans(),
)
@example(-1, True)
@example("1/2", False)
@example(True, False)
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_index_inputs_are_checked_when_a_published_value_decides(
    tmp_path, value, as_list
):
    """Review r2 low 14: [-1, 1, 1, 1] once returned the 2025 value."""
    registry = invented_registry(
        tmp_path,
        thresholds=[
            invented_threshold(
                values={"2024": 100, "2025": 110}, indexing=INVENTED_INDEX
            )
        ],
    )
    supplied = {
        "national_average_wage_index_2023": (
            [value, 1, 1, 1] if as_list else value
        )
    }
    if not exact_nonnegative(value):
        with pytest.raises((TypeError, ValueError)) as caught:
            registry.threshold(
                "INVENTED_threshold", 2025, index_inputs=supplied
            )
        assert not isinstance(caught.value, CoverageRegistryError)
        return
    assert (
        registry.threshold("INVENTED_threshold", 2025, index_inputs=supplied)
        == 110
    )


@given(st.text(min_size=1, max_size=6), st.booleans())
@example("b", True)
@example("a", False)
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_alternative_must_name_a_reading_of_the_family(
    tmp_path, name, with_alternatives
):
    """Review r2 low 14: an alternative was ignored without readings.

    A reading of an open question is not selectable either: the open row
    still refuses, and a settled year would ignore the name.
    """
    rows = [invented_row(start=2001, rule_id="INVENTED_a")]
    open_row = invented_row(end=2000, rule_id="INVENTED_open")
    open_row["open_reason"] = "INVENTED unresolved legal question"
    open_row["consequence"] = None
    open_row["residual_default"]["consequence"] = None
    open_row["open_alternatives"] = [
        {"name": "INVENTED_open_a", "description": "INVENTED first reading"},
        {"name": "INVENTED_open_b", "description": "INVENTED second reading"},
    ]
    sub = invented_case("invented_sub_question", 1, "open")
    sub["open_reason"] = "INVENTED_SUB_QUESTION: no capture settles it"
    sub["open_alternatives"] = [
        {"name": "INVENTED_case_a", "description": "INVENTED first reading"},
        {"name": "INVENTED_case_b", "description": "INVENTED second reading"},
    ]
    rows[0]["cases"] = [sub]
    for year in (2000, 2010):
        for reading in ("INVENTED_open_a", "INVENTED_case_b"):
            with pytest.raises(UnknownIdentifierError, match="open question"):
                invented_registry(tmp_path, [open_row, *rows]).lookup(
                    "INVENTED_family", year, alternative=reading
                )
    rows[0]["cases"] = []
    if with_alternatives:
        rows.append(invented_row(rule_id="INVENTED_b"))
        for row, label in zip(rows, ("a", "b"), strict=True):
            row["alternative"] = {
                "group": "INVENTED_group",
                "name": label,
                "explanation": "INVENTED overlapping readings",
            }
    registry = invented_registry(tmp_path, rows)
    known = {"a", "b"} if with_alternatives else set()
    if name not in known:
        with pytest.raises(UnknownIdentifierError, match="no alternative"):
            registry.lookup("INVENTED_family", 2010, alternative=name)
        return
    (rule,) = registry.lookup("INVENTED_family", 2010, alternative=name)
    assert rule.alternative["name"] == name


@given(st.one_of(st.none(), st.text(max_size=4)))
@example("")
@example(" ")
@example("INVENTED")
@settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_recorded_threshold_description_is_nonempty(tmp_path, description):
    """Review r2 low 14: casual_cash_quarterly had an empty description."""
    threshold = invented_threshold()
    if description is not None:
        threshold["description"] = description
    if description is not None and not description.strip():
        with pytest.raises(
            RegistryValidationError, match="threshold description"
        ):
            invented_registry(tmp_path, thresholds=[threshold])
        return
    registry = invented_registry(tmp_path, thresholds=[threshold])
    assert registry.threshold("INVENTED_threshold", 2024) == 100
