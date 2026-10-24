"""Conformance of pinned public legal artifacts in data/external.

Published worked examples retain their cited passages. These tests use no
survey observations and do not implement the CE3 component classifier.
"""

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.coverage_rules import (
    CAPTURE_DIRECTORY,
    TRIGGER_FACTS,
    CoverageRegistry,
    CoverageRegistryError,
    OpenRuleError,
    ThresholdUnavailableError,
    load_registry,
    source_text,
)


@pytest.fixture(scope="module")
def registry():
    artifact = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "external"
        / "snapshots"
        / "income_resources_ce1_v1"
        / "coverage_rules.json"
    )
    return load_registry(artifact)


def citations(value):
    if isinstance(value, dict):
        if "capture" in value and "sha256" in value:
            yield value
        for child in value.values():
            yield from citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from citations(child)


def test_every_pinned_citation_matches_its_capture(registry):
    found = list(citations(registry.to_dict()))
    assert found
    for citation in found:
        path = CAPTURE_DIRECTORY / citation["capture"]
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest() == citation["sha256"]
        )
        if citation.get("quote"):
            assert " ".join(citation["quote"].split()) in source_text(path)


@settings(deadline=None)
@given(st.integers(1968, 2026), st.data())
def test_family_year_lookup_is_never_silently_empty(registry, year, data):
    family = data.draw(st.sampled_from(registry.families))
    try:
        rules = registry.lookup(family, year)
    except CoverageRegistryError as refusal:
        assert str(refusal)
    else:
        assert rules
        assert all(r.family == family for r in rules)
        assert min(r.effective_start for r in rules) <= date(year, 1, 1)
        assert max(r.effective_end for r in rules) >= date(year, 12, 31)


def test_all_family_year_coordinates_return_or_refuse(registry):
    for family in registry.families:
        for year in range(1968, 2027):
            try:
                assert registry.lookup(family, year)
            except CoverageRegistryError as refusal:
                assert str(refusal)


@settings(deadline=None)
@given(st.data())
def test_real_ranges_partition_or_name_their_overlap(registry, data):
    family = data.draw(st.sampled_from(registry.families))
    rules = sorted(
        [r for r in registry.rules if r.family == family],
        key=lambda r: (r.effective_start, r.rule_id),
    )
    for left, right in zip(rules, rules[1:], strict=False):
        if right.effective_start <= left.effective_end:
            assert left.alternative and right.alternative
            assert left.alternative["group"] == right.alternative["group"]
            assert left.alternative["name"] != right.alternative["name"]
        else:
            assert (
                left.effective_end + timedelta(days=1) == right.effective_start
            )


@settings(deadline=None)
@given(st.data())
def test_trigger_vocabulary_and_awaiting_identification(registry, data):
    rule = data.draw(st.sampled_from(registry.rules))
    assert set(rule.trigger_facts) <= TRIGGER_FACTS
    assert rule.identification_class == "awaiting_ce2"
    assert not rule.is_identified
    if rule.rare_exclusion is not None:
        rare = rule.rare_exclusion
        assert rare["strict"] == "unresolved"
        if rare["negligible_candidate"] is None:
            assert rare["searches"]
        else:
            candidate = rare["negligible_candidate"]
            assert candidate["bound"] and candidate["population"]
            assert candidate["citation"]


@settings(deadline=None)
@given(st.booleans())
def test_real_loader_is_row_order_independent_and_round_trips(
    registry, reverse
):
    raw = registry.to_dict()
    if reverse:
        raw["rules"].reverse()
        raw["thresholds"].reverse()
    restored = CoverageRegistry.from_dict(raw, capture_root=CAPTURE_DIRECTORY)
    assert restored.to_json() == registry.to_json()
    assert json.loads(restored.to_json()) == restored.to_dict()


def test_published_examples_conform_to_legal_lookup(registry):
    examples = [
        (rule, example)
        for rule in registry.rules
        for example in rule.worked_examples
    ]
    assert examples, "CE1 needs published guidance conformance examples"
    for rule, example in examples:
        citation = example["citation"]
        passage = " ".join(example["source_passage"].split())
        assert passage in source_text(CAPTURE_DIRECTORY / citation["capture"])
        returned = registry.lookup(rule.family, example["income_year"])
        matched = [
            r for r in returned if r.rule_id == example["expected_rule_id"]
        ]
        assert len(matched) == 1
        for key, value in example["expected_parameters"].items():
            assert matched[0].parameters[key] == value
        for threshold_id, amount in example.get(
            "expected_thresholds", {}
        ).items():
            assert (
                registry.threshold(threshold_id, example["income_year"])
                == amount
            )


@settings(deadline=None)
@given(st.integers(1968, 2026), st.data())
def test_real_threshold_is_published_or_requires_exact_named_inputs(
    registry, year, data
):
    threshold = data.draw(st.sampled_from(registry.thresholds))
    try:
        value = registry.threshold(threshold["threshold_id"], year)
    except ThresholdUnavailableError:
        assert str(year) not in threshold["published_values"]
    else:
        assert value >= 0
        assert str(year) in threshold["published_values"]


@settings(deadline=None)
@given(st.data())
def test_law_declared_monotone_thresholds_never_fall(registry, data):
    thresholds = [t for t in registry.thresholds if t.get("monotone")]
    assert thresholds
    threshold = data.draw(st.sampled_from(thresholds))
    values = [
        registry.threshold(threshold["threshold_id"], int(year))
        for year in sorted(threshold["published_values"])
    ]
    assert values == sorted(values)


def test_state_local_change_occurs_after_july_first_1991(registry):
    family = "section_218_and_mandatory_state_local"
    before = registry.lookup_date(family, date(1991, 7, 1))
    after = registry.lookup_date(family, date(1991, 7, 2))
    assert before[0].rule_id != after[0].rule_id
    assert len(registry.lookup(family, 1991)) == 2


def test_open_source_history_refuses_instead_of_backcasting(registry):
    open_rules = [r for r in registry.rules if r.open_reason]
    assert open_rules
    for rule in open_rules:
        with pytest.raises(OpenRuleError):
            registry.lookup_date(rule.family, rule.effective_start)


def test_ret_concept_records_disregarded_limits_and_both_deeming_conditions(
    registry,
):
    ret = registry.metadata["earnings_test"]
    assert {r["paragraph"] for r in ret["disregarded_wage_limits"]} == {
        "409(a)(1)",
        "409(a)(6)(B)",
        "409(a)(6)(C)",
        "409(a)(7)(B)",
        "409(a)(8)",
    }
    assert ret["deeming_rule"]["connective"] == "both"
    assert len(ret["deeming_rule"]["required_conditions"]) == 2
    assert len(ret["gross_income_exclusions_D"]) == 2
    assert not ret["self_employment"]["thresholds_apply"]


def test_table_availability_does_not_infer_a_membership_rule(registry):
    definitions = registry.metadata["table_definitions"]
    assert {d["definition_id"] for d in definitions} == {
        "4.B2.c11",
        "4.B2.c12",
        "4.B11.total",
        "4.B11.wage",
        "4.B11.self_employment",
    }
    for definition in definitions:
        assert definition["status"] in {
            "verified",
            "TABLE_DEFINITION_UNVERIFIED",
        }
        assert definition["citations"]
        assert not definition["table_values_computed"]
        if definition["status"] == "TABLE_DEFINITION_UNVERIFIED":
            assert definition["reason"]
