"""Conformance of pinned public legal artifacts in data/external.

Published worked examples retain their cited passages. These tests use no
survey observations and do not implement the CE3 component classifier.
"""

import gzip
import hashlib
import json
import re
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
    CoverageRule,
    OpenRuleError,
    ThresholdUnavailableError,
    load_registry,
    source_text,
)

REGISTRY_ARTIFACT = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "income_resources_ce1"
    / "coverage_rules.json"
)
PUBLISHED_CASES = [
    (row["rule_id"], example["example_id"])
    for row in json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    for example in row["worked_examples"]
]


@pytest.fixture(scope="module")
def registry():
    return load_registry(REGISTRY_ARTIFACT)


def citations(value):
    if isinstance(value, dict):
        if "capture" in value and "sha256" in value:
            yield value
        for child in value.values():
            yield from citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from citations(child)


def test_canonical_registry_matches_research_fragments(registry):
    root = CAPTURE_DIRECTORY.parent.parent / "income_resources_ce1"

    def read(name):
        return json.loads((root / name).read_text())

    assert PUBLISHED_CASES, "CE1 needs published conformance cases"
    assert len(PUBLISHED_CASES) == len(set(PUBLISHED_CASES))
    rows = [
        CoverageRule.from_dict(row).to_dict()
        for name in (
            "government_rules.json",
            "se_rules.json",
            "other_rules.json",
            "se_modifier_rules.json",
        )
        for row in read(name)
    ]
    assert {r["rule_id"]: r for r in rows} == {
        r.rule_id: r.to_dict() for r in registry.rules
    }
    thresholds = [
        threshold
        for name in (
            "thresholds_government.json",
            "thresholds_se.json",
            "thresholds_other.json",
        )
        for threshold in read(name)
    ]
    canonical = registry.to_dict()
    assert {t["threshold_id"]: t for t in thresholds} == {
        t["threshold_id"]: t for t in canonical["thresholds"]
    }
    ret = read("earnings_test_root.json")
    ret["self_employment_guidance"] = read("earnings_test_se.json")
    ret["historical_research"] = read("ret_history_government.json")
    ret["definition_modifier_research"] = read("ret_history_modifiers.json")
    assert ret == canonical["earnings_test"]
    assert (
        read("table_definitions_root.json") == canonical["table_definitions"]
    )


def test_every_pinned_citation_matches_its_capture(registry):
    found = list(citations(registry.to_dict()))
    assert found
    digests = {}
    texts = {}
    for citation in found:
        path = CAPTURE_DIRECTORY / citation["capture"]
        if path not in digests:
            digests[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digests[path] == citation["sha256"]
        if citation.get("quote"):
            if path not in texts:
                texts[path] = source_text(path)
            assert " ".join(citation["quote"].split()) in texts[path]


def test_archived_threshold_table_matches_every_published_year(registry):
    name = "ssa_oact_cola_covthresh_wayback_20261013081352.html"
    html = (CAPTURE_DIRECTORY / name).read_text()
    rows = re.findall(
        r'<td align="center">(\d{4})</td>\s*'
        r"<td>\$?([\d,]+)</td>\s*<td>\$?([\d,]+)</td>",
        html,
    )
    assert len(rows) == 33
    assert {int(row[0]) for row in rows} == set(range(1994, 2027))
    for year, domestic, election in rows:
        assert registry.threshold("domestic_cash_annual", int(year)) == int(
            domestic.replace(",", "")
        )
        assert registry.threshold(
            "election_remuneration_annual", int(year)
        ) == int(election.replace(",", ""))
    assert (
        gzip.decompress((CAPTURE_DIRECTORY / (name + ".gz")).read_bytes())
        == (CAPTURE_DIRECTORY / name).read_bytes()
    )
    inventory = json.loads(
        (CAPTURE_DIRECTORY / "source_inventory.json").read_text()
    )
    blocked = next(
        row
        for row in inventory
        if row.get("url") == "https://www.ssa.gov/oact/cola/CovThresh.html"
    )
    assert blocked["status"] == "SOURCE_BLOCKED"
    assert blocked["reason"] == "HTTP 403"
    assert blocked["resolution"]["status"] == "answered_by_archived_capture"
    assert blocked["resolution"]["capture"] == name


@settings(deadline=None)
@given(st.integers(1968, 1993))
def test_archived_pre1994_footnote_agrees_with_quarterly_statute(
    registry, year
):
    threshold = next(
        t
        for t in registry.thresholds
        if t["threshold_id"] == "domestic_cash_quarterly"
    )
    assert registry.threshold("domestic_cash_quarterly", year) == 50
    assert threshold["aggregation_scope"] == "calendar_quarter"
    assert any(
        c["capture"] == "lii_42_409.html" for c in threshold["citations"]
    )
    assert any(
        c.get("quote", "").startswith("Prior to 1994")
        for c in threshold["citations"]
    )


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


@pytest.mark.parametrize(
    ("rule_id", "example_id"),
    PUBLISHED_CASES,
    ids=[example_id for _, example_id in PUBLISHED_CASES],
)
def test_published_examples_conform_to_legal_lookup(
    registry, rule_id, example_id
):
    rule = next(r for r in registry.rules if r.rule_id == rule_id)
    example = next(
        e for e in rule.worked_examples if e["example_id"] == example_id
    )
    citation = example["citation"]
    passage = " ".join(example["source_passage"].split())
    assert passage in source_text(CAPTURE_DIRECTORY / citation["capture"])
    assert example["expected_rule_id"] == rule.rule_id
    if example.get("income_year_basis") == (
        "source_edition_lookup_year_for_undated_published_example"
    ):
        assert example["income_year"] == example["source_edition_year"]
    returned = registry.lookup(rule.family, example["income_year"])
    matched = [r for r in returned if r.rule_id == example["expected_rule_id"]]
    assert len(matched) == 1
    for key, value in example["expected_parameters"].items():
        assert matched[0].parameters[key] == value
    for threshold_id, amount in example.get("expected_thresholds", {}).items():
        assert (
            registry.threshold(threshold_id, example["income_year"]) == amount
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


def test_primary_act_boundaries_preserve_midyear_changes(registry):
    for family, boundary, before_id, after_id in (
        (
            "communist_organization_service",
            date(2014, 12, 19),
            "communist_organization_service_1968",
            "communist_organization_service_2014_1219",
        ),
        (
            "tribal_council_service",
            date(2018, 9, 20),
            "tribal_council_service_1968",
            "tribal_council_service_2018_0920",
        ),
    ):
        assert (
            registry.lookup_date(family, boundary - timedelta(days=1))[
                0
            ].rule_id
            == before_id
        )
        assert registry.lookup_date(family, boundary)[0].rule_id == after_id
        assert len(registry.lookup(family, boundary.year)) == 2


def test_community_income_uses_operational_taxable_year_change(registry):
    before = registry.lookup("self_employment_community_income", 1979)[0]
    after = registry.lookup("self_employment_community_income", 1980)[0]
    assert before.rule_id == "se_community_income_1968_1979"
    assert after.rule_id == "se_community_income_1980_2026"
    assert (
        after.parameters["operational_taxable_year_condition"][
            "first_included_month"
        ]
        == "1980-10"
    )
    assert after.parameters["statutory_text_amendment_date"] == "2004-03-02"


@settings(deadline=None)
@given(st.integers(1985, 2026))
def test_fishing_additional_cash_is_a_per_trip_upper_bound(registry, year):
    threshold = next(
        t
        for t in registry.thresholds
        if t["threshold_id"] == "fishing_additional_cash_per_trip"
    )
    assert threshold["comparison"] == "at_most"
    assert threshold["aggregation_scope"] == "employer_employee_trip"
    assert registry.threshold(threshold["threshold_id"], year) == 100


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


@settings(deadline=None)
@given(st.integers(1968, 2026))
def test_ret_concept_refuses_years_with_unverified_dependencies(
    registry, year
):
    with pytest.raises(OpenRuleError):
        registry.earnings_test_concept(year)


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
