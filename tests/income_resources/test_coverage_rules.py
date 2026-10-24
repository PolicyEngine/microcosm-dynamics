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
    load_registry,
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
def test_awaiting_evidence_is_never_identified(identification):
    row = invented_row()
    row["identification_class"] = identification
    assert CoverageRule.from_dict(row).is_identified == (
        identification == "identified"
    )


@given(st.text(min_size=1).filter(lambda value: value not in {"amount"}))
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


@pytest.mark.parametrize("year", [True, 1967, 2027, "2024", None])
def test_year_support_is_explicit(tmp_path, year):
    with pytest.raises(NoRuleError):
        invented_registry(tmp_path).lookup("INVENTED_family", year)


def test_open_rule_refuses_and_payload_is_immutable(tmp_path):
    row = invented_row()
    row["open_reason"] = "INVENTED blocked source"
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
    raw["nested_citation"] = {
        **INVENTED_CITATION,
        "capture": "../invented.html",
    }
    with pytest.raises(CaptureIntegrityError):
        CoverageRegistry.from_dict(raw, capture_root=tmp_path)


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
