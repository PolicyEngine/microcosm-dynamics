"""Registered G examples, source figures and declared coverage classes.

Verification class: statutory conformance. Only invented configurations and
captured statutory examples are admitted, with no population, behavioral or
forecast claim. Published figures retain capture literals. Derived monthly
rates and statutory dollar floors are labelled separately from published
presentation figures. Registry completeness, determinism, scenario order
independence, declared coverage, maximum-tag truth, and capture-section
containment are executable invariants.
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
            "auxiliary_percent_of_pia": (
                row.auxiliary_payable * 100 / state.pia if state.pia else F(0)
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


def _check_maximum_tags(example):
    bindings = set()
    for scenario in run_example(example).values():
        result = scenario.get("result")
        if isinstance(result, g.FamilyBenefits):
            bindings.add(result.family_maximum_binding)
        elif isinstance(result, g.HouseholdBenefits):
            bindings.update(
                record.family_maximum_binding
                for record in result.records.values()
            )
    for tag, binding in (
        ("maximum:binding", True),
        ("maximum:nonbinding", False),
    ):
        if tag in example["tags"]:
            assert binding in bindings, (example["id"], tag, bindings)
    return bindings


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
    if rule == "nearest_tenth":
        return F(int(value * 10 + F(1, 2)), 10)
    raise AssertionError(f"Unknown registry rounding: {rule}")


# Shorthand citations resolve to captured headings and their following peer.
# Each pair narrows the previous section, so a child heading cannot silently
# match elsewhere in the document. The captures use headings, bold examples,
# plain-text tables and table rows; not every section has an HTML anchor.
CITATION_SECTIONS = {
    "poms_rs_00615_756": {
        "B.3": (
            ("B. Procedure", "To Link to this section"),
            (
                "3. Death Case - Different Original Benefits - WIB DRCs Not Involved",
                "4. Widow(er) and Other Survivor Rates Based on Different PIAs - Windexing",
            ),
        ),
        "B.4": (
            ("B. Procedure", "To Link to this section"),
            (
                "4. Widow(er) and Other Survivor Rates Based on Different PIAs - Windexing",
                None,
            ),
        ),
    },
    "poms_rs_00615_710": {
        "Example": (("C. EXAMPLE", "To Link to this section"),),
    },
    "poms_rs_00615_682": {
        "Example": (("EXAMPLE:", "To Link to this section"),),
    },
    "poms_rs_00615_768": {
        "F.1": (
            ("F. EXAMPLES", "To Link to this section"),
            (
                "EXAMPLE 1. Dually Entitled Beneficiary Reduced to Zero Payable",
                "EXAMPLE 2. Dually Entitled Beneficiary with a Partial Payable",
            ),
        ),
        "F.2": (
            ("F. EXAMPLES", "To Link to this section"),
            (
                "EXAMPLE 2. Dually Entitled Beneficiary with a Partial Payable",
                "EXAMPLE 3. Dually Entitled Beneficiary with Zero Payable and a Combined Family Maximum",
            ),
        ),
    },
    "poms_rs_00615_320": {
        "C. Example": (("C. Example", "To Link to this section"),),
    },
    "poms_rs_00615_694": {
        "C. Example": (("C. Example", "D. Reference"),),
    },
    "poms_rs_00615_240": {
        "Example": (
            (
                "3. Spouse's Benefit with Subsequent RIB",
                "4. Spouse's Reentitlement",
            ),
            ("Example:", None),
        ),
    },
    "ssa_ssb_v75n3_family_maximum": {
        "Table 1": (("Table 1.", "Table 2."),),
        "Table 2": (("Table 2.", "Table A-1."),),
        "Table A-1": (("Table A-1.", "Table A-2."),),
        "Table A-2": (("Table A-2.", None),),
        "Table A-2 household integration": (("Table A-2.", None),),
    },
    "poms_rs_00615_005": {
        "B. Example": (
            (
                "B. POLICY - USE OF FRACTIONS INSTEAD OF DECIMAL EQUIVALENTS",
                "C. POLICY - ADJUSTMENTS TO REDUCED BENEFITS AFTER 1/78 DUE TO COLA OR RECOMPUTATION",
            ),
            ("EXAMPLE:", None),
        ),
    },
    "poms_rs_00615_301": {
        "B.1 example": (
            (
                "B. Policy - reduced widow(er)'s benefits",
                "To Link to this section",
            ),
            (
                "1. Amount of WIB reduction",
                "2. Chart - widow(er)'s benefit reduction factors",
            ),
        ),
    },
    "poms_rs_00615_692": {
        "Example": (
            (
                "C. Formula for computing DRCs",
                "D. Chart for Delayed Retirement Credits",
            ),
            (
                "2. Computation errors with the decimal equivalent or multiplication sequence",
                None,
            ),
            ("For example:", None),
        ),
    },
    "poms_rs_00615_736": {
        label: (
            ("B. Procedure", "To Link to this section"),
            ("3. EXAMPLES", None),
            bounds,
        )
        for label, bounds in {
            "B.3 example 1 (1979 formula)": ("Example 1 .", "Example 2."),
            "B.3 example 1 (1981 formula)": ("Example 1 .", "Example 2."),
            "B.3 example 2": ("Example 2.", "Example 3."),
            "B.3 example 3": ("Example 3.", None),
        }.items()
    },
    "ssa_oact_familymax": {
        "2026 determination": (
            ("Determination of family-maximum bend points for 2026", None),
        ),
    },
    "poms_rs_00605_910": {
        "1981 third constant": (
            ("RS 00605.910 Family Maximum Chart", "To Link to this section"),
            ("1981 Up through 270.00", "1982 Up through 294.00"),
        ),
    },
    "poms_gn_02603_060": {
        "A.5": (
            (
                "A. Examples of permanent full deductions",
                "B. Examples of permanent partial deductions",
            ),
            (
                "5. Full deduction for dual entitlement",
                "6. Full deduction because",
            ),
        ),
        "A.8": (
            (
                "A. Examples of permanent full deductions",
                "B. Examples of permanent partial deductions",
            ),
            ("8. Full deduction because", "9. Full deduction because"),
        ),
        "A.9": (
            (
                "A. Examples of permanent full deductions",
                "B. Examples of permanent partial deductions",
            ),
            ("9. Full deduction because", None),
        ),
        "B.2": (
            (
                "B. Examples of permanent partial deductions",
                "C. Examples of temporary deductions",
            ),
            (
                "2. Partial deduction and age reduction Involved",
                "3. Partial deduction for dual entitlement",
            ),
        ),
    },
    "poms_rs_00615_340": {
        "3.a": (
            ("3. Examples", "To Link to this section"),
            ("a. Increased Amount", "b. No Increase in Amount"),
        ),
        "3.b": (
            ("3. Examples", "To Link to this section"),
            ("b. No Increase in Amount", None),
        ),
    },
}


def _citation_section(example):
    source = example["capture_id"]
    citation = example["section"]
    assert source in CITATION_SECTIONS, (example["id"], source)
    assert citation in CITATION_SECTIONS[source], (example["id"], citation)
    text = source_text(source)
    for start, end in CITATION_SECTIONS[source][citation]:
        assert start in text, (example["id"], citation, start)
        # Include the heading so existing source_start boundaries remain
        # independently checked within this same captured section.
        text = text[text.index(start) :]
        if end is not None:
            assert end in text, (example["id"], citation, end)
            text = text[: text.index(end)]
    return text


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda value: value["id"])
def test_registry_cited_section_contains_every_published_figure(example):
    text = _citation_section(example)
    for figure in example["expected"]:
        assert figure["literal"] in text, (example["id"], figure["literal"])


@given(st.sampled_from(EXAMPLES))
@settings(deadline=None)
def test_registry_unknown_sections_are_rejected(example):
    test_registry_cited_section_contains_every_published_figure(example)
    changed = copy.deepcopy(example)
    changed["section"] = "MUTATED: NO SUCH CAPTURE SECTION"
    with pytest.raises(AssertionError):
        _citation_section(changed)


@pytest.mark.parametrize("section", ["F.1", "F.2"])
def test_registry_other_parisi_example_figures_are_rejected(section):
    example = next(
        example
        for example in EXAMPLES
        if example["capture_id"] == "poms_rs_00615_768"
        and example["section"] == section
    )
    changed = copy.deepcopy(example)
    changed["section"] = "F.2" if section == "F.1" else "F.1"
    with pytest.raises(AssertionError):
        check_example(changed)


def _capture_section(example):
    cited = _citation_section(example)
    for figure in example["expected"]:
        assert figure["literal"] in cited, (example["id"], figure["literal"])
    # Preserve the earlier explicit boundaries as an independent check.
    text = source_text(example["capture_id"])
    if example.get("source_start"):
        assert example["source_start"] in text, example["id"]
        text = text.split(example["source_start"], 1)[1]
    if example.get("source_end"):
        assert example["source_end"] in text, example["id"]
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


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda value: value["id"])
def test_registered_maximum_tags_match_computed_scenarios(example):
    _check_maximum_tags(example)


def test_poms_340_certified_child_in_care_reproduces_reviewer_amounts():
    state = _state(
        {
            "kind": "survivor",
            "pia": "1000",
            "family_maximum": "1750",
            "widow_drc_savings_clause": False,
        }
    )
    common = {
        "beneficiary_id": "w",
        "role": "widow",
        "birth_year": 1935,
        "reduction_months": 60,
        "reduction_period_months": 60,
    }
    child = {"beneficiary_id": "c", "role": "child"}
    caring = _family_output(
        state,
        _members([{**common, "child_in_care": "c"}, child]),
        g.YearMonth(2026, 1),
    )
    ordinary = _family_output(
        state,
        _members([{**common, "child_in_care": False}, child]),
        g.YearMonth(2026, 1),
    )
    assert caring["rows"]["w"].auxiliary_payable == F(750)
    assert caring["rows"]["c"].auxiliary_payable == F(750)
    assert caring["result"].record_total == F(1500)
    assert ordinary["rows"]["w"].auxiliary_payable == F(715)


def test_survivor_snapshot_attestations_are_supported_by_capture_facts():
    facts = {
        ("rs-00615-756-seven-children", "case"): (
            "Death Case - Different Original Benefits - WIB DRCs Not Involved"
        ),
        ("rs-00615-756-windexed", "case"): (
            "Nora is entitled as a widow with an OB calculated under the "
            "alternate computation as prescribed by the 1983 amendments"
        ),
        ("rs-00615-710-widow-drc", "case"): (
            "The survivors to be entitled in 3/00 are a widow and a child."
        ),
        ("rs-00615-682-divorced-widow", "before"): (
            "A surviving divorced mother (E1) and two children are entitled "
            "to $101.90 each"
        ),
        ("rs-00615-682-divorced-widow", "after"): (
            "At age 60, E1 becomes entitled as D6 and is paid outside the "
            "maximum."
        ),
        ("rs-00615-320-rib-lim", "case"): (
            "B's spouse, age 66, comes in to file for widow's benefits."
        ),
        **{
            ("rs-00615-340-increased-amount", name): (
                "are reduced to 71.5% of the PIA because of the 64 RF."
            )
            for name in (
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
            )
        },
        ("rs-00615-340-no-increase", "ordinary"): (
            "after age reduction they receive about 92.9% of the PIA."
        ),
        ("rs-00615-340-no-increase", "caring"): (
            "after age reduction they receive about 92.9% of the PIA."
        ),
    }
    snapshots = {
        (example["id"], name): (example, raw["state"])
        for example in EXAMPLES
        for name, raw in example["inputs"]["scenarios"].items()
        if raw.get("state", {}).get("kind") == "survivor"
    }
    assert set(snapshots) == set(facts)
    for key, (example, state) in snapshots.items():
        assert state["widow_drc_savings_clause"] is False, key
        assert facts[key] in source_text(example["capture_id"]), key


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
    "widow:child_in_care",
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


@given(st.sampled_from(EXAMPLES), st.booleans())
@settings(deadline=None, max_examples=50)
def test_registry_maximum_tag_truth_is_scenario_order_independent(
    example, reverse
):
    bindings = _check_maximum_tags(example)
    changed = copy.deepcopy(example)
    scenarios = list(changed["inputs"]["scenarios"].items())
    changed["inputs"]["scenarios"] = dict(
        reversed(scenarios) if reverse else scenarios
    )
    assert bindings == _check_maximum_tags(changed)


@given(
    st.sampled_from(
        [
            example
            for example in EXAMPLES
            if len(
                set(example["tags"])
                & {"maximum:binding", "maximum:nonbinding"}
            )
            == 1
            and all(
                raw["operation"] == "family"
                for raw in example["inputs"]["scenarios"].values()
            )
        ]
    )
)
@settings(deadline=None)
def test_registry_false_maximum_tags_are_rejected(example):
    bindings = _check_maximum_tags(example)
    assert len(bindings) == 1
    false_tag = "maximum:nonbinding" if True in bindings else "maximum:binding"
    changed = copy.deepcopy(example)
    changed["tags"].append(false_tag)
    with pytest.raises(AssertionError):
        _check_maximum_tags(changed)
