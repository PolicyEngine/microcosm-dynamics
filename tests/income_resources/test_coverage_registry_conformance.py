"""Conformance of pinned public legal artifacts in data/external.

Published worked examples retain their cited passages. These tests use no
survey observations and do not implement the CE3 component classifier.
"""

import gzip
import hashlib
import importlib.util
import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.coverage_rules import (
    CAPTURE_DIRECTORY,
    REGISTRY_PATH,
    TRIGGER_FACTS,
    AlternativeRequiredError,
    CoverageRegistry,
    CoverageRegistryError,
    NoRuleError,
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
        if "capture" in value:
            yield value
        for child in value.values():
            yield from citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from citations(child)


@pytest.fixture(scope="module")
def assemble():
    spec = importlib.util.spec_from_file_location(
        "ce1_assemble_registry", REGISTRY_PATH.parent / "assemble_registry.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build


def test_canonical_registry_matches_research_fragments(registry, assemble):
    assert PUBLISHED_CASES, "CE1 needs published conformance cases"
    assert len(PUBLISHED_CASES) == len(set(PUBLISHED_CASES))
    assert assemble().encode("utf-8") == REGISTRY_PATH.read_bytes()
    assert registry.to_json().encode("utf-8") == REGISTRY_PATH.read_bytes()


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


MANIFEST_ENTRY = re.compile(
    r"^(?P<time>.+) (?P<sha256>[0-9a-f]{64}) (?P<size>\d+) (?P<name>\S+)$"
)
CAPTURE_METADATA = re.compile(
    r"^(capture_manifest.*\.txt|sources_.*\.json|source_inventory\.json"
    r"|SOURCE_INVENTORY\.md)$"
)


def test_capture_folder_and_manifests_list_the_same_bytes():
    entries = []
    for manifest in sorted(CAPTURE_DIRECTORY.glob("capture_manifest*.txt")):
        for line in manifest.read_text().splitlines():
            entry = MANIFEST_ENTRY.match(line)
            if entry and not line.startswith("#"):
                entries.append(entry)
    assert entries
    for entry in entries:
        data = (CAPTURE_DIRECTORY / entry["name"]).read_bytes()
        assert len(data) == int(entry["size"]), entry["name"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    captures = {
        path.name
        for path in CAPTURE_DIRECTORY.iterdir()
        if path.is_file() and not CAPTURE_METADATA.match(path.name)
    }
    assert captures == {entry["name"] for entry in entries}


def structured_provenance(row):
    value = row.get("provenance")
    return value if isinstance(value, dict) else {}


def test_page_extracts_record_their_originals():
    inventory = json.loads(
        (CAPTURE_DIRECTORY / "source_inventory.json").read_text()
    )
    extracts = [
        row
        for row in inventory
        if "extracted_from" in structured_provenance(row)
    ]
    names = {row["file"] for row in extracts}
    assert len(names) == 5
    for row in extracts:
        data = (CAPTURE_DIRECTORY / row["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
        original = row["provenance"]["extracted_from"]
        assert row["provenance"]["signature_status"] == (
            "original_signature_invalidated_by_page_extraction"
        )
        assert "recorded URL" in row["provenance"]["original_retrieval"]
        assert not (CAPTURE_DIRECTORY / original["file"]).exists()
        assert original["bytes"] > len(data)
        assert re.fullmatch(r"[0-9a-f]{64}", original["sha256"])
        pages = row["provenance"]["original_pdf_pages"]
        assert pages == sorted(set(pages))
        assert pages[0] == 1 and pages[-1] <= original["pages"]
    derived = [
        row
        for row in inventory
        if structured_provenance(row).get("derived_from") in names
    ]
    assert len(derived) == 2
    for row in derived:
        extract = next(
            r
            for r in extracts
            if r["file"] == row["provenance"]["derived_from"]
        )
        assert row["provenance"]["source_sha256"] == extract["sha256"]


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
    assert threshold["aggregation_scope"] == "employer_employee_quarter"
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
        if rules[0].parameters.get("effective_basis") == "taxable_year_start":
            assert max(r.effective_end for r in rules) >= date(year, 1, 1)
        else:
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


@settings(
    deadline=None,
    max_examples=8,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(st.randoms())
def test_real_loader_is_row_order_independent_and_round_trips(
    registry, assemble, tmp_path, random
):
    raw = registry.to_dict()
    random.shuffle(raw["rules"])
    random.shuffle(raw["thresholds"])
    restored = CoverageRegistry.from_dict(raw, capture_root=CAPTURE_DIRECTORY)
    assert restored.to_json() == registry.to_json()
    assert json.loads(restored.to_json()) == restored.to_dict()
    for path in REGISTRY_PATH.parent.glob("*.json"):
        if path == REGISTRY_PATH:
            continue
        fragment = json.loads(path.read_text())
        if path.name.endswith("_rules.json") or path.name.startswith(
            "thresholds_"
        ):
            random.shuffle(fragment)
        (tmp_path / path.name).write_text(json.dumps(fragment))
    assert assemble(tmp_path).encode("utf-8") == REGISTRY_PATH.read_bytes()


@settings(deadline=None)
@given(st.data())
def test_real_cases_and_open_readings_obey_schema(registry, data):
    rule = data.draw(st.sampled_from(registry.rules))
    assert rule.residual_default["consequence"] == rule.consequence
    for outcome in (rule.residual_default, *rule.cases):
        deferred = outcome["consequence"] == "deferred"
        assert deferred == ("defers_to" in outcome)
        if deferred:
            assert rule.family not in outcome["defers_to"]
            assert set(outcome["defers_to"]) <= set(registry.families)
    for case in rule.cases:
        assert case["when"]
        assert set(case["when"]) <= set(rule.trigger_facts)
        assert case["consequence"] in CONSEQUENCE_VALUES
    if rule.open_reason:
        assert rule.consequence in {None, "open"}
        assert len(rule.open_alternatives) >= 2
        assert rule.alternative is None


CONSEQUENCE_VALUES = {
    "covered",
    "noncovered",
    "covered_above_threshold",
    "open",
    "deferred",
}
PARAMETER_EVIDENCE = {
    "citation",
    "citations",
    "code_edition_evidence",
    "later_edition_reliance",
    "case_free_basis",
}
CONDITION_KEY = re.compile(
    r"(^|_)(conditions?|requires_all|any_of|exceptions?)$"
)
CONDITION_WORDS = re.compile(
    r"\b(only when|only if|unless|except|excepts|excepted|is excluded|"
    r"are excluded|excludes|remains excluded|depends on)\b",
    re.IGNORECASE,
)


def parameter_leaves(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in PARAMETER_EVIDENCE:
                yield from parameter_leaves(child, (*path, key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from parameter_leaves(child, path)
    else:
        yield path, value


def condition_signals(row):
    """Why a closed row's text or parameters name a statutory condition."""
    signals = []
    if row["consequence"] == "noncovered":
        signals.append("noncovered residual")
    for path, value in parameter_leaves(row["parameters"]):
        if value in CONSEQUENCE_VALUES:
            signals.append(f"consequence parameter {'.'.join(path)}")
        if path and CONDITION_KEY.search(path[-1]):
            signals.append(f"condition parameter {'.'.join(path)}")
    words = CONDITION_WORDS.search(row["description"])
    if words:
        signals.append(f"description says {words.group(0)!r}")
    return signals


def rows_missing_condition_cases(rows):
    """Closed rows that name a condition but carry neither cases nor basis.

    A closed row's residual applies when no case holds, so a condition left
    in prose or parameters would apply its exclusion unconditionally.
    """
    return {
        row["rule_id"]: signals
        for row in rows
        if row["open_reason"] is None
        and not row["cases"]
        and "case_free_basis" not in row["parameters"]
        and (signals := condition_signals(row))
    }


def test_closed_rows_naming_a_condition_carry_cases():
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    assert rows_missing_condition_cases(rows) == {}
    for row in rows:
        if "case_free_basis" in row["parameters"]:
            assert not row["cases"]
            assert row["consequence"] not in {"noncovered", "deferred"}
            leaves = parameter_leaves(row["parameters"])
            assert not any(v in CONSEQUENCE_VALUES for _, v in leaves)


@settings(deadline=None)
@given(
    st.sampled_from(sorted(CONSEQUENCE_VALUES - {"open"})),
    st.sampled_from(["", "unless the employer elects", "only when paid"]),
    st.booleans(),
)
def test_condition_detector_flags_every_signal(consequence, words, key):
    """The detector is the test's oracle, so its own signals are tested."""
    row = {
        "consequence": consequence,
        "description": f"INVENTED rule {words}".strip(),
        "parameters": {"required_conditions": ["a"]} if key else {},
        "open_reason": None,
        "cases": [],
    }
    expected = (consequence == "noncovered") + bool(words) + key
    assert len(condition_signals(row)) == expected
    flagged = rows_missing_condition_cases([{"rule_id": "INVENTED", **row}])
    assert bool(flagged) == bool(expected)
    with_case = {**row, "rule_id": "INVENTED", "cases": [{"case_id": "a"}]}
    assert rows_missing_condition_cases([with_case]) == {}


def test_consequences_live_in_cases_not_parameters():
    rows = json.loads(REGISTRY_ARTIFACT.read_text())["rules"]
    stored = [
        (row["rule_id"], ".".join(path))
        for row in rows
        for path, value in parameter_leaves(row["parameters"])
        if value in CONSEQUENCE_VALUES
    ]
    assert stored == []


def test_real_deferral_targets_cover_the_deferring_years(registry):
    """Every deferral names a family with a rule in each deferring year.

    Exhaustive over every deferring outcome and every year of its row, so
    no target family leaves a year where the deferral reaches no rule. An
    open or alternative-only target refuses rather than misclassifying.
    """
    absent, checked = [], set()
    for rule in registry.rules:
        for outcome in (rule.residual_default, *rule.cases):
            if outcome["consequence"] != "deferred":
                continue
            for target in outcome["defers_to"]:
                for year in range(
                    rule.effective_start.year, rule.effective_end.year + 1
                ):
                    if (target, year) in checked:
                        continue
                    checked.add((target, year))
                    try:
                        assert registry.lookup(target, year)
                    except (OpenRuleError, AlternativeRequiredError):
                        continue
                    except NoRuleError:
                        absent.append((rule.rule_id, target, year))
    assert checked
    assert absent == []


def service_date_condition_holds(condition, service_day):
    """Evaluate a case's ``services_performed_date`` text on one date.

    Only the two forms CE1 writes are accepted, so a new phrasing fails
    loudly instead of matching by accident.
    """
    match = re.fullmatch(
        r"(on or after|before) (\d{4}-\d{2}-\d{2})", condition
    )
    assert match, condition
    boundary = date.fromisoformat(match[2])
    if match[1] == "before":
        return service_day < boundary
    return service_day >= boundary


def cash_equivalent_transfer_cases(rule, service_day):
    """Cases matching a cash-equivalent transfer without dominion, by date."""
    return {
        c["case_id"]
        for c in rule.cases
        if c["when"].get("noncash_transfer_cash_equivalence") is True
        and service_date_condition_holds(
            c["when"]["services_performed_date"], service_day
        )
    }


SSR_95_3P_PUBLISHED = date(1995, 8, 7)


@example(date(1990, 6, 15))
@example(SSR_95_3P_PUBLISHED - timedelta(days=1))
@example(SSR_95_3P_PUBLISHED)
@given(st.dates(date(1988, 1, 1), date(2026, 12, 31)))
@settings(deadline=None)
def test_cash_equivalent_agricultural_transfer_follows_ssr_95_3p(
    registry, service_day
):
    """INVENTED transfer: cattle the employee must sell back at once.

    POMS RS 01402.020 A: before SSR 95-3P (published 1995-08-07) SSA
    excluded noncash transfers from wages; from that date a cash-equivalent
    transfer is tested as cash wages. The 1990 example is the review's
    repro: it used to fall through to the residual.
    """
    (rule,) = registry.lookup("agricultural_service", service_day.year)
    matched = cash_equivalent_transfer_cases(rule, service_day)
    assert len(matched) == 1
    expected = (
        "noncovered"
        if service_day < SSR_95_3P_PUBLISHED
        else "covered_above_threshold"
    )
    resolved = rule.resolve(matched)
    assert resolved["consequence"] == expected
    assert resolved is not rule.residual_default
    # A bona fide commodity transfer with dominion stays outside wages.
    genuine = {
        c["case_id"]
        for c in rule.cases
        if "dominion and control" in c["when"].get("cash_remuneration", "")
    }
    assert len(genuine) == 1
    assert rule.resolve(genuine)["consequence"] == "noncovered"


def test_tribal_council_cases_and_uncaptured_crp_history(registry):
    tribal = registry.lookup("tribal_council_service", 2019)[0]
    council = {"no_section_418a_inclusion"}
    assert tribal.resolve(council)["consequence"] == "noncovered"
    agreement = council | {"section_418a_agreement_inclusion"}
    assert tribal.resolve(agreement)["consequence"] == "covered"
    # Council staff and tribal employees are not council-member service.
    assert tribal.resolve(set())["consequence"] == "covered"
    with pytest.raises(OpenRuleError, match="CRP_PRE2008"):
        registry.lookup("self_employment_conservation_reserve", 2007)


@pytest.mark.parametrize(
    ("family", "year", "matched", "expected"),
    [
        # HIGH-1 repros: each condition's failure no longer excludes.
        ("self_employment_conservation_reserve", 2010, set(), "deferred"),
        (
            "self_employment_conservation_reserve",
            2010,
            {"crp_payment_to_beneficiary"},
            "noncovered",
        ),
        ("self_employment_farm_rental_participation", 1970, set(), "open"),
        (
            "self_employment_farm_rental_participation",
            1970,
            {"participation_under_required_arrangement"},
            "covered",
        ),
        ("self_employment_retired_partner", 2000, set(), "covered"),
        (
            "self_employment_limited_partner",
            2000,
            {
                "guaranteed_payment_for_services",
                "limited_partner_distributive_share",
            },
            "covered",
        ),
        ("self_employment_insurance_termination", 2000, set(), "deferred"),
        ("self_employment_treaty_fishing", 2000, set(), "covered"),
        (
            "student_service",
            1980,
            {
                "section_218_agreement_covers_students",
                "enrolled_student_at_employing_school",
            },
            "covered",
        ),
        (
            "tribal_council_service",
            2000,
            {
                "later_418a_retroactive_coverage",
                "federally_recognized_council_member",
            },
            "covered",
        ),
        (
            "self_employment_rental_income",
            2000,
            {"parking_warehouse_storage_space", "real_estate_rentals"},
            "covered",
        ),
        (
            "international_organization_service",
            2000,
            {
                "transferred_federal_employee_410r",
                "designated_international_organization",
            },
            "covered",
        ),
        ("nonresident_alien_service", 2000, set(), "covered"),
        ("foreign_government_service", 2000, set(), "covered"),
    ],
)
def test_failed_conditions_no_longer_exclude(
    registry, family, year, matched, expected
):
    (rule,) = registry.lookup(family, year)
    assert rule.resolve(matched)["consequence"] == expected


@settings(deadline=None)
@given(
    st.sampled_from(
        [
            "domestic_cash_quarterly",
            "casual_cash_quarterly",
            "homeworker_cash_quarterly",
            "election_remuneration_quarterly",
            "cash_tips_monthly",
        ]
    )
)
def test_period_thresholds_keep_employers_separate(registry, threshold_id):
    threshold = next(
        t for t in registry.thresholds if t["threshold_id"] == threshold_id
    )
    period = "month" if threshold_id == "cash_tips_monthly" else "quarter"
    assert threshold["aggregation_scope"] == f"employer_employee_{period}"


@settings(deadline=None)
@given(st.data())
def test_real_case_precedence_is_first_match(registry, data):
    rule = data.draw(st.sampled_from([r for r in registry.rules if r.cases]))
    by_id = {case["case_id"]: case for case in rule.cases}
    assert len(by_id) == len(rule.cases)
    assert sorted(c["precedence"] for c in rule.cases) == list(
        range(1, len(rule.cases) + 1)
    )
    matched = data.draw(st.sets(st.sampled_from(sorted(by_id))))
    result = rule.resolve(matched)
    if matched:
        winner = min(matched, key=lambda case_id: by_id[case_id]["precedence"])
        assert result is by_id[winner]
    else:
        assert result == rule.residual_default
    for case in rule.cases:
        for target in case.get("overrides", ()):
            assert by_id[target]["precedence"] > case["precedence"]
            assert by_id[target]["consequence"] != case["consequence"]
            assert rule.resolve({case["case_id"], target}) is case


FEDERAL_EXCEPTIONS = (
    "official_position_service",
    "after_official_service_from_1988_11_10",
    "fers_or_fsps_election",
    "legislative_not_retirement_covered_1983",
    "legislative_lump_sum_after_1983",
    "legislative_ceased_coverage_after_1983",
)
FEDERAL_PARAGRAPH_6 = (
    "federal_penal_inmate",
    "federal_hospital_student_employee",
    "temporary_emergency_employee",
)


@settings(deadline=None)
@given(st.integers(1984, 2026), st.data())
def test_federal_exceptions_outrank_the_grandfather_exclusion(
    registry, year, data
):
    (rule,) = registry.lookup("federal_retirement_service", year)
    ids = {case["case_id"] for case in rule.cases}
    assert ("fers_or_fsps_election" in ids) == (year >= 1987)
    # Review MED-1 repro: a Member of Congress serving since 1983.
    member = {"grandfathered_continuous_service", "official_position_service"}
    assert rule.resolve(member)["consequence"] == "covered"
    excluded = data.draw(
        st.sets(
            st.sampled_from(
                ["grandfathered_continuous_service", "federal_annuitant"]
            ),
            min_size=1,
        )
    )
    exception = data.draw(
        st.sampled_from(sorted(ids.intersection(FEDERAL_EXCEPTIONS)))
    )
    assert rule.resolve(excluded | {exception})["consequence"] == "covered"
    # 410(a)(5)(C)-(H) lift paragraph (5) only; paragraph (6) still applies.
    inmate = data.draw(st.sampled_from(FEDERAL_PARAGRAPH_6))
    assert (
        rule.resolve(excluded | {exception, inmate})["consequence"]
        == "noncovered"
    )
    # Pub. L. 98-369 section 2601(d) requalification displaces (G)(ii).
    requalified = {
        "defra_2601d_requalification",
        "legislative_lump_sum_after_1983",
        "grandfathered_continuous_service",
    }
    assert rule.resolve(requalified)["consequence"] == "noncovered"


@settings(deadline=None)
@given(st.integers(1984, 2026))
def test_federal_legislative_branch_exception_is_returned(registry, year):
    rule = registry.lookup("federal_retirement_service", year)[0]
    assert any(
        c["consequence"] == "covered"
        and "legislative" in str(c["when"]).lower()
        for c in rule.cases
    )


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
    if example.get("income_year_basis") == (
        "source_edition_lookup_year_for_undated_published_example"
    ):
        assert example["income_year"] == example["source_edition_year"]
    returned = registry.lookup(rule.family, example["income_year"])
    matched = [r for r in returned if r.rule_id == example["expected_rule_id"]]
    assert len(matched) == 1
    for threshold_id, amount in example.get("expected_thresholds", {}).items():
        assert (
            registry.threshold(threshold_id, example["income_year"]) == amount
        )
    outcome = published_outcome(registry, matched[0], example)
    assert outcome == example["published_outputs"]
    if "expected_amount" in example:
        assert (
            outcome["annual_cash_wages_dollars"] == example["expected_amount"]
        )


def published_outcome(registry, rule, example):
    """Evaluate only the published example's facts against the returned law.

    The oracle is test-side arithmetic and condition checks, independent of
    stored expected parameters. Exhausting the inputs and comparing the whole
    output mapping prevents unused published facts or outcomes.
    """
    facts = dict(example["published_inputs"])
    kind = example["calculation"]
    params = rule.parameters
    year = example["income_year"]
    if kind == "domestic_threshold":
        annual = facts.pop("weekly_cash_wages") * facts.pop("weeks")
        over_18 = facts.pop("employee_over_18")
        unrelated = facts.pop("employee_unrelated")
        eligible = over_18 and unrelated
        threshold = registry.threshold(params["threshold_id"], year)
        result = {
            "annual_cash_wages_dollars": annual,
            "social_security_coverage": (
                "covered"
                if eligible
                and annual >= threshold
                and rule.consequence == "covered_above_threshold"
                else "noncovered"
            ),
        }
    elif kind in {"agricultural_cash_wages", "domestic_cash_wages"}:
        cash = facts.pop("cash_wages_cents")
        employer_paid_tax = facts.pop("employer_paid_employee_fica_cents")
        if kind == "agricultural_cash_wages":
            threshold_id = params["threshold_ids"][0]
            clears = cash >= 100 * registry.threshold(threshold_id, year)
            all_cash = params["all_cash_covered_when_test_met"]
            suffix = ""
        else:
            annual = facts.pop("expected_annual_cash_at_least_cents")
            over_18 = facts.pop("employee_over_18")
            unrelated = facts.pop("employee_unrelated")
            eligible = over_18 and unrelated
            clears = eligible and annual >= 100 * registry.threshold(
                params["threshold_id"], year
            )
            all_cash = params["all_cash_covered_when_threshold_met"]
            suffix = "_per_payday"
        ss_cash = cash + (
            employer_paid_tax
            if params["employer_paid_employee_fica_included_in_wages"]
            else 0
        )
        result = {
            f"social_security_wages{suffix}_cents": (
                ss_cash
                if clears
                and all_cash
                and rule.consequence == "covered_above_threshold"
                else 0
            ),
            f"federal_income_tax_wages{suffix}_cents": cash
            + employer_paid_tax,
        }
    elif kind == "agricultural_commodity":
        dominion = facts.pop("employee_exercises_dominion_and_control")
        if dominion:
            matched = {
                c["case_id"]
                for c in rule.cases
                if "dominion and control"
                in c["when"].get("cash_remuneration", "")
            }
            assert matched
            consequence = rule.resolve(matched)["consequence"]
        else:
            matched = cash_equivalent_transfer_cases(rule, date(year, 1, 1))
            assert len(matched) == 1
            consequence = rule.resolve(matched)["consequence"]
        result = {
            "commodity_remuneration": {
                "noncovered": "not_wages",
                "covered_above_threshold": "wages",
            }[consequence]
        }
    elif kind == "parent_child_business":
        parent = facts.pop("parent_works_for_child")
        business = facts.pop("trade_or_business")
        controlled = facts.pop("son_controls_work")
        assert parent and business and controlled
        case = next(
            c
            for c in rule.cases
            if c["when"]
            .get("family_service", "")
            .startswith("parent employed by child in")
        )
        result = {"social_security_coverage": case["consequence"]}
    elif kind == "order_service":
        required = facts.pop("required_order_duties")
        vow = facts.pop("vow_of_poverty")
        if required and vow:
            excluded = params["poverty_vow_self_employment_excluded"]
            result = {
                "self_employment_coverage": (
                    "noncovered" if excluded else "covered"
                )
            }
        else:
            consequence = next(
                c["consequence"]
                for c in rule.cases
                if c["when"]
                .get("religious_order_service", "")
                .startswith("ordinary employment for a third party")
            )
            result = {
                "social_security_and_medicare_treatment": {
                    "noncovered": "not_subject_to_FICA",
                    "covered": "subject_to_FICA",
                }[consequence]
            }
    elif kind == "minister_exemption":
        effective = facts.pop("exemption_granted")
        condition = (
            "effective 1402(e) exemption" if effective else "not established"
        )
        consequence = next(
            c["consequence"]
            for c in rule.cases
            if c["when"].get("clergy_or_religious_exemption") == condition
        )
        result = {"social_security_coverage": consequence}
    elif kind == "section_218_reentry":
        new_member = facts.pop("state_treats_as_new_member")
        prior_vote = facts.pop("prior_vote")
        rule_value = params["section_218_divided_vote_same_group_return"][
            "state_new_member" if new_member else "state_existing_member"
        ]
        covered = rule_value == "compulsorily_covered" or (
            rule_value == "retains_prior_vote" and prior_vote == "yes"
        )
        assert params["section_218_first"]
        result = {"agreement_coverage": "covered" if covered else "noncovered"}
    elif kind == "state_local_mandatory":
        agreement = facts.pop("section_218_covered")
        member = facts.pop("qualified_retirement_system_member")
        assert params["section_218_first"]
        assert date(year, 1, 1) >= date.fromisoformat(
            params["mandatory_start"]
        )
        if agreement:
            case = next(
                c
                for c in rule.cases
                if c["when"]
                .get("section_218_position", "")
                .startswith("covered by effective")
            )
        else:
            membership = (
                "member of an IRS-qualified system"
                if member
                else "not a member of an IRS-qualified system"
            )
            case = next(
                c
                for c in rule.cases
                if c["when"].get("public_retirement_system_participation")
                == membership
            )
        result = {"social_security_coverage": case["consequence"]}
    elif kind == "minister_gross_concept":
        salary = facts.pop("salary_cents")
        housing = facts.pop("parsonage_value_cents", 0)
        foreign_exclusion = facts.pop("income_tax_foreign_exclusion_cents", 0)
        exclusions = params["gross_income_exclusions_disregarded"]
        amount = salary + (housing if "26USC107" in exclusions else 0)
        if "26USC911" not in exclusions:
            amount -= foreign_exclusion
        result = {"included_se_gross_concept_cents": amount}
    elif kind == "farm_agent":
        owner_participates = facts.pop("owner_personally_participates")
        agent_participates = facts.pop("agent_participates")
        participation = owner_participates or (
            agent_participates and params["agent_activities_count"]
        )
        case = next(
            c
            for c in rule.cases
            if c["when"].get("material_participation") is participation
        )
        result = {
            "rental_income_included_in_nese": {
                "covered": True,
                "noncovered": False,
            }[case["consequence"]]
        }
    else:
        pytest.fail(f"missing published-example oracle: {kind}")
    assert not facts, f"unused published inputs: {facts}"
    return result


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
    assert before.rule_id == "se_community_income_1968_1979"
    for year in (1980, 2000, 2003, 2004):
        with pytest.raises(OpenRuleError):
            registry.lookup("self_employment_community_income", year)
    after = registry.lookup_date(
        "self_employment_community_income", date(2004, 3, 2)
    )[0]
    assert after.rule_id == "se_community_income_2004_2026"
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
