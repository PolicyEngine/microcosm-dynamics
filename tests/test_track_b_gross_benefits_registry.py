"""Registered G examples, source figures and declared coverage classes.

Verification class: statutory conformance. Only invented configurations and
captured statutory examples are admitted, with no population, behavioral or
forecast claim. Published figures retain capture literals. Derived monthly
rates and statutory dollar floors are labelled separately from published
presentation figures. Registry completeness, determinism, scenario order
independence and declared coverage are executable invariants.
"""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Mapping
from fractions import Fraction as F
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.ss import benefits as oracle
from populace_dynamics.track_b import gross_benefits as g
from tests.track_b_gross_benefit_support import source_text, ssa_params

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "tests/data/track_b/gross_benefit_examples.yaml"
PARAMS = ssa_params()


def load_registry():
    return yaml.safe_load(REGISTRY_PATH.read_text())


REGISTRY = load_registry() if REGISTRY_PATH.exists() else None
EXAMPLES = [] if REGISTRY is None else REGISTRY["examples"]


def _own(raw):
    if raw is None:
        return None
    raw = dict(raw)
    raw["kind"] = g.OwnBenefitKind(raw["kind"])
    raw["pia"] = F(raw["pia"])
    return g.OwnBenefit(**raw)


def _members(raw):
    result = []
    for member in raw:
        member = dict(member)
        member["role"] = g.Role(member["role"])
        if "own_benefit" in member:
            member["own_benefit"] = _own(member["own_benefit"])
        if "original_benefit_basis" in member:
            member["original_benefit_basis"] = F(
                member["original_benefit_basis"]
            )
        result.append(g.Beneficiary(**member))
    return result


def _state(raw):
    raw = dict(raw)
    raw["kind"] = g.FamilyKind(raw["kind"])
    raw["pia"] = F(raw["pia"])
    raw["family_maximum"] = F(raw["family_maximum"])
    if "worker" in raw:
        raw["worker"] = _own(raw["worker"])
    elif raw["kind"] is g.FamilyKind.RETIREMENT:
        raw["worker"] = g.OwnBenefit(g.OwnBenefitKind.OLD_AGE, raw["pia"])
    for key in ("rib_lim_benefit",):
        if key in raw:
            raw[key] = F(raw[key])
    return g.RecordState(**raw)


def _worker_record(raw):
    raw = dict(raw)
    raw["kind"] = g.FamilyKind(raw["kind"])
    raw["eligibility_pia"] = F(raw["eligibility_pia"])
    if "first_dib_entitlement" in raw:
        raw["first_dib_entitlement"] = g.YearMonth(
            *raw["first_dib_entitlement"]
        )
    return g.record_state(g.WorkerRecord(**raw), PARAMS)


def _family_output(state, members, month):
    result = g.family_benefits(
        state, members, payment_month=month, params=PARAMS, standalone=True
    )
    rows = result.by_id()
    own = sum((row.own_benefit or F(0) for row in rows.values()), F(0))
    potentials = {
        member.beneficiary_id: g.original_benefit(
            member.role, state.kind, state.pia, member.original_benefit_basis
        )
        for member in members
    }
    extras = {}
    for member in members:
        row = rows[member.beneficiary_id]
        own_pia = member.own_benefit.pia if member.own_benefit else F(0)
        extras[member.beneficiary_id] = {
            "potential_ob": potentials[member.beneficiary_id],
            "own_pia": own_pia,
            "own_base": (
                g.own_monthly_benefit(member.own_benefit, PARAMS)[0]
                if member.own_benefit
                else F(0)
            ),
            "ob_excess": max(
                F(0), potentials[member.beneficiary_id] - own_pia
            ),
            "deductee_age_amount": (
                row.counted_against_maximum - row.auxiliary_payable
            ),
        }
    return {
        "state": state,
        "members": {member.beneficiary_id: member for member in members},
        "result": result,
        "rows": rows,
        "extra": extras,
        "pre_maximum_total": (result.worker_benefit or F(0))
        + own
        + sum(
            (
                max(F(0), potentials[key] - (row.own_benefit or F(0)))
                for key, row in rows.items()
            ),
            F(0),
        ),
        "record_plus_own": result.record_total + own,
        "rib_lim_floor": g.floor_dime(state.pia * F(825, 1000)),
        "ptap": result.available_for_auxiliaries
        - sum(
            (
                row.counted_against_maximum
                for row in rows.values()
                if row.own_benefit is not None
                and row.subject_to_family_maximum
            ),
            F(0),
        ),
    }


def _scenario(raw):
    operation = raw["operation"]
    month = g.YearMonth(*raw.get("month", [2026, 1]))
    if operation == "family":
        state = (
            _worker_record(raw["worker_record"])
            if "worker_record" in raw
            else _state(raw["state"])
        )
        return _family_output(state, _members(raw["members"]), month)
    if operation == "household":
        records = {
            key: g.HouseholdRecord(
                record["worker_id"],
                _state(record["state"]),
                _members(record.get("members", [])),
            )
            for key, record in raw["records"].items()
        }
        result = g.household_benefits(
            records, payment_month=month, params=PARAMS
        )
        return {
            "result": result,
            "records": {
                key: {"result": record, "rows": record.by_id()}
                for key, record in result.records.items()
            },
        }
    if operation == "worker_age":
        pia = F(raw["pia"])
        base, credited = g.worker_age_adjusted(
            pia,
            raw.get("reduction_months", 0),
            raw.get("delayed_credit_months", 0),
            raw.get("birth_year"),
            PARAMS,
        )
        result = {
            "pia": pia,
            "base": base,
            "credited": credited,
            "increment": credited - base,
            "reduction_months": raw.get("reduction_months", 0),
            "delayed_credit_months": raw.get("delayed_credit_months", 0),
        }
        if raw.get("decimal_comparison"):
            factor = 1 - oracle.early_reduction(
                raw["reduction_months"], PARAMS
            )
            result["decimal_comparison"] = g.floor_dime(
                F(repr(float(pia) * factor))
            )
        return result
    if operation == "widow_age":
        return {
            **raw,
            "rate": g.survivor_age_reduced(
                F(raw["ob"]), raw["months"], raw["period"], PARAMS
            ),
        }
    if operation == "maximum_formula":
        exact = g.family_maximum_formula(F(raw["pia"]), raw["year"], PARAMS)
        return {
            **raw,
            "exact": exact,
            "shown_cents": F(int(exact * 100), 100),
            "rounded_up": g.ceil_dime(exact),
        }
    if operation == "bend_points":
        numerator, denominator = F(raw["nawi"]), F(raw["base_nawi"])
        unrounded = [
            base * numerator / denominator for base in (230, 332, 433)
        ]
        return {
            **raw,
            "shown": {
                str(i): round(value, 2) for i, value in enumerate(unrounded)
            },
            "points": {
                str(i): value
                for i, value in enumerate(
                    g.family_maximum_bend_points(raw["year"], PARAMS)
                )
            },
        }
    if operation == "chart_erratum":
        computed = g.family_maximum_formula(raw["point"], raw["year"], PARAMS)
        return {
            "published": F(raw["published"]),
            "computed": computed,
            "difference": F(raw["published"]) - computed,
        }
    raise AssertionError(f"Unknown registry operation: {operation}")


def run_example(example):
    return {
        key: {"input": raw, **_scenario(raw)}
        for key, raw in example["inputs"]["scenarios"].items()
    }


def _resolve(values, path):
    for component in path.split("."):
        values = (
            values[component]
            if isinstance(values, Mapping)
            else getattr(values, component)
        )
    return F(values)


def _rounded(value, rule):
    if rule is None:
        return value
    if rule == "nearest_dollar":
        return F(int(value + F(1, 2)))
    if rule == "whole_dollar_floor":
        return F(value.numerator // value.denominator)
    raise AssertionError(f"Unknown registry rounding: {rule}")


def _capture_section(example):
    text = source_text(example["capture_id"])
    if example.get("source_start"):
        text = text.split(example["source_start"], 1)[1]
    if example.get("source_end"):
        text = text.split(example["source_end"], 1)[0]
    return text


def check_example(example):
    assert len(example["expected"]) == example["figure_count"], example["id"]
    values = run_example(example)
    text = _capture_section(example)
    checked = 0
    for figure in example["expected"]:
        assert figure["literal"] in text, (example["id"], figure["literal"])
        literal_numbers = {
            F(number.replace(",", ""))
            for number in re.findall(r"\d[\d,]*(?:\.\d+)?", figure["literal"])
        }
        assert F(figure["value"]) in literal_numbers, (
            example["id"],
            figure["literal"],
            figure["value"],
        )
        actual = _rounded(
            _resolve(values, figure["path"]), figure.get("rounding")
        )
        assert actual == F(figure["value"]), (example["id"], figure["path"])
        checked += 1
    assert checked == example["figure_count"], example["id"]
    for figure in example.get("derived_expected", []):
        assert figure["derivation"], example["id"]
        actual = _rounded(
            _resolve(values, figure["path"]), figure.get("rounding")
        )
        assert actual == F(figure["value"]), (example["id"], figure["path"])
    return checked


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda value: value["id"])
def test_registered_statutory_example_reproduces_every_figure(example):
    check_example(example)


def test_registry_schema_and_declared_figures_are_complete():
    registry = load_registry()
    assert registry["schema_version"] == 1
    assert registry["verification_class"] == "statutory_conformance"
    assert "no population" in registry["admitted_scope"]
    ids = [example["id"] for example in registry["examples"]]
    assert len(ids) == len(set(ids))
    vocabulary = set(registry["tag_vocabulary"])
    assert len(vocabulary) == len(registry["tag_vocabulary"])
    for example in registry["examples"]:
        assert example["section"]
        assert example["figure_count"] > 0
        assert example["figure_count"] == len(example["expected"]), example[
            "id"
        ]
        assert set(example["tags"]) <= vocabulary
        assert len(example["tags"]) == len(set(example["tags"]))
        paths = [figure["path"] for figure in example["expected"]]
        assert len(paths) == len(set(paths)), example["id"]


FEATURE_CLASSES = {
    "reduction:worker",
    "reduction:spouse",
    "reduction:widow",
    "credits:worker",
    "credits:own_rib",
    "credits:widow_basis",
    "dual:method_b",
    "dual:method_c",
    "dual:child",
    "dual:all_dual",
    "dual:parent",
    "maximum:binding",
    "maximum:nonbinding",
    "maximum:disability_floor",
    "maximum:disability_aime",
    "maximum:disability_cap",
    "redistribution:zero",
    "redistribution:partial",
    "redistribution:own_age_reduced",
    "outside:divorced_spouse",
    "outside:surviving_divorced_spouse",
    "outside:ieds",
    "rib_lim",
    "cola_path",
    "dwb",
    "parent:one",
    "parent:two",
    "ieds",
    "ssfa:gpo_ignored",
    "ssfa:wep_regular_pia",
}


def _check_coverage(registry):
    expected = (
        FEATURE_CLASSES
        | {f"record:{kind.value}" for kind in g.FamilyKind}
        | {f"role:{role.value}" for role in g.Role}
    )
    assert set(registry["supported_classes"]) == expected
    registered = {
        tag for example in registry["examples"] for tag in example["tags"]
    }
    invented = registry["invented_only_classes"]
    assert set(invented) <= expected
    assert expected <= registered | set(invented)
    assert set(invented).isdisjoint(registered)
    for tag, explanation in invented.items():
        assert explanation["reason"].strip(), tag
        assert explanation["tests"], tag
        for reference in explanation["tests"]:
            file, name = reference.split("::", 1)
            definitions = {
                node.name
                for node in ast.walk(ast.parse((ROOT / file).read_text()))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            assert name in definitions, reference


def test_every_supported_class_has_a_statutory_or_explained_reference_case():
    _check_coverage(REGISTRY)


@given(st.sampled_from(REGISTRY["supported_classes"]))
@settings(deadline=None)
def test_registry_losing_any_supported_class_is_rejected(tag):
    changed = copy.deepcopy(REGISTRY)
    for example in changed["examples"]:
        example["tags"] = [item for item in example["tags"] if item != tag]
    changed["invented_only_classes"].pop(tag, None)
    with pytest.raises(AssertionError):
        _check_coverage(changed)


@given(st.sampled_from(EXAMPLES), st.integers(0, 1000))
@settings(deadline=None, max_examples=50)
def test_registry_missing_figures_always_fail_completeness(example, index):
    changed = copy.deepcopy(example)
    del changed["expected"][index % example["figure_count"]]
    with pytest.raises(AssertionError):
        check_example(changed)


@given(st.sampled_from(EXAMPLES), st.integers(0, 1000))
@settings(deadline=None, max_examples=50)
def test_registry_changed_capture_literals_are_rejected(example, index):
    changed = copy.deepcopy(example)
    changed["expected"][index % example["figure_count"]][
        "literal"
    ] = "REGISTRY MUTATION: THIS FIGURE IS ABSENT FROM THE SOURCE"
    with pytest.raises(AssertionError):
        check_example(changed)


@given(st.sampled_from(EXAMPLES), st.booleans())
@settings(deadline=None, max_examples=50)
def test_registry_is_deterministic_and_scenario_order_independent(
    example, reverse
):
    initial = run_example(example)
    assert initial == run_example(example)
    changed = copy.deepcopy(example)
    scenarios = list(changed["inputs"]["scenarios"].items())
    changed["inputs"]["scenarios"] = dict(
        reversed(scenarios) if reverse else scenarios
    )
    assert initial == run_example(changed)
