"""Reproduction tests for ``runs/pia_rule_coverage_v1.json``.

The artifact is a REPORTED per-rule coverage record (reads no gate,
changes no gate): for every statutory rule the oracle implements, which
committed cross-engine cases and which committed SSA worked examples
exercise it, which rules have zero case coverage, what the module does
not implement at all, and the DRAFT definition of ``"computes exactly"``
quoted as a proposal.

All tests are always runnable. They touch only committed files -- the
oracle source, the two committed evidence artifacts, the committed test
modules and ``gates.yaml`` -- plus the build script. No engine is
executed here, exactly as none is executed by the builder: the tests
that run the Axiom engine and a policyengine-us Simulation live in
``tests/ss/`` and are unchanged.

Two kinds of test:

* **Derivation.** Every code span re-derives from the source with
  ``ast``; every named worked example and every named test exists;
  bracket occupancy, dime-floor coverage, shape counts and the
  foundation factor split recompute from the committed artifacts; every
  not-implemented search re-runs and is still empty.
* **Framing.** The artifact stays REPORTED, adopts no definition,
  quotes ``gates.yaml``'s single ``"computes exactly"`` occurrence as it
  reads on disk, and records where its derivation differs from the
  DRAFT packet's claim rather than silently adopting it.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "pia_rule_coverage_v1.json"
CROSS_ENGINE = ROOT / "runs" / "pia_cross_engine_v1.json"
AUX = ROOT / "runs" / "aux_benefit_examples_v1.json"
GATES = ROOT / "gates.yaml"
SCRIPTS = ROOT / "scripts"

EXPECTED_RULE_IDS = (
    "R1_415b1_wage_base_cap",
    "R2_415b3_nawi_indexation",
    "R3_415b2B_computation_year_count",
    "R4_415b_top_n_divide_and_floor",
    "R5_415a1A_pia_brackets",
    "R6_415a1B_bend_points",
    "R7_415g_dime_floor",
    "R8_402q_worker_early_reduction",
    "R9_402w_delayed_retirement_credit",
    "R10_416l_fra_schedule",
    "R11_402q1_spousal_early_reduction",
    "R12_402bc_402k3_spouse_benefit",
    "R13_402q_survivor_reduction_ramp",
    "R14_402ef_widow_riblim_drc_dual",
    "R15_402e3_f4_remarriage_protection",
    "R16_age62_composition",
)


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def _import_builder():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_pia_rule_coverage as builder

    return builder


def _defined_names(relative: str) -> dict[str, tuple[int, int]]:
    tree = ast.parse((ROOT / relative).read_text())
    out: dict[str, tuple[int, int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            out.setdefault(node.name, (node.lineno, node.end_lineno))
    return out


# --------------------------------------------------------------------------
# Schema and reported-record framing
# --------------------------------------------------------------------------
def test_schema_and_reported_not_gated():
    art = _artifact()
    assert art["schema_version"] == "pia_rule_coverage.v1"
    assert art["run"] == "pia_rule_coverage_v1"
    assert art["reported_not_gated"] is True
    assert "Changes no gate" in art["purpose"]
    assert art["gate_status"]["gates_yaml_block"] is None


def test_no_gate_b2_pia_oracle_exists_in_gates_yaml():
    assert "gate_b2_pia_oracle" not in GATES.read_text()


def test_computes_exactly_occurrences_match_gates_yaml_on_disk():
    art = _artifact()
    lines = GATES.read_text().splitlines()
    found = [
        {"line": index + 1, "text": line.strip()}
        for index, line in enumerate(lines)
        if "computes exactly" in line
    ]
    assert art["gate_status"]["computes_exactly_occurrences"] == found
    assert len(found) == 1
    assert (
        art["computes_exactly_definition_proposal"]["gates_yaml_line_642"]
        == lines[641].strip()
    )


def test_the_definition_is_quoted_as_a_proposal_and_not_adopted():
    block = _artifact()["computes_exactly_definition_proposal"]
    assert block["status"] == "proposal_not_ratified"
    assert block["adopted_here"] is False
    assert set(block["conditions"]) == {
        "E1_independent_re_execution",
        "E2_external_anchor",
        "E3_exercised_branches_and_boundaries",
    }
    assert set(block["exclusions"]) == {
        "X1_named_non_coverage",
        "X2_named_constants",
    }


def test_no_engine_was_executed_and_revisions_are_quoted():
    art = _artifact()
    cross = json.loads(CROSS_ENGINE.read_text())
    block = art["no_engine_executed"]
    assert block["engine_revision_quoted"] == cross["engine_revision"]
    assert block["pe_us_revision_quoted"] == cross["pe_us_revision"]
    assert "executed neither" in block["statement"]


def test_sources_are_pinned_to_the_bytes_on_disk():
    art = _artifact()
    groups = ("oracle", "evidence_artifacts", "tests")
    for group in groups:
        for pin in art["sources"][group]:
            path = ROOT / pin["path"]
            assert path.is_file(), pin["path"]
            assert (
                pin["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
            )
            assert pin["bytes"] == path.stat().st_size
    consumer = art["sources"]["consumer"]
    assert (ROOT / consumer["path"]).is_file()


# --------------------------------------------------------------------------
# The rule inventory
# --------------------------------------------------------------------------
def test_every_rule_is_present_exactly_once():
    art = _artifact()
    ids = [rule["id"] for rule in art["rule_inventory"]]
    assert ids == list(EXPECTED_RULE_IDS)
    assert art["n_rules"] == len(EXPECTED_RULE_IDS) == 16


def test_every_rule_carries_a_statute_and_an_e1_e2_e3_status():
    for rule in _artifact()["rule_inventory"]:
        assert rule["statute"].startswith("42 USC"), rule["id"]
        assert rule["title"]
        for condition in ("e1", "e2", "e3"):
            assert rule[condition]["status"], (rule["id"], condition)
            assert rule[condition]["basis"], (rule["id"], condition)


def test_every_code_span_rederives_from_the_source():
    for rule in _artifact()["rule_inventory"]:
        for span in rule["code"]:
            source = (ROOT / span["module"]).read_text().splitlines()
            if span["kind"] in ("function", "class"):
                defined = _defined_names(span["module"])
                assert span["symbol"] in defined, span
                first, last = defined[span["symbol"]]
                assert (span["first_line"], span["last_line"]) == (
                    first,
                    last,
                ), span
            line = source[span["first_line"] - 1]
            assert span["symbol"] in line, span


def test_every_named_worked_example_exists_in_the_aux_artifact():
    art = _artifact()
    aux = json.loads(AUX.read_text())["ssa_worked_examples"]
    names = {
        example["name"]
        for group in ("spousal", "survivor")
        for example in aux[group]
    }
    named = {
        name
        for rule in art["rule_inventory"]
        for name in rule["ssa_worked_examples"]
    }
    assert named <= names
    assert art["coverage_summary"]["every_named_worked_example_exists"] is True
    # Every committed example is claimed by exactly one rule, so no row
    # of evidence is silently unused.
    assert named == names


def test_every_named_test_exists_in_its_pinned_module():
    art = _artifact()
    for rule in art["rule_inventory"]:
        for reference in rule["tests"]:
            module, *qualifiers = reference.split("::")
            assert (ROOT / module).is_file(), reference
            defined = _defined_names(module)
            for qualifier in qualifiers:
                assert qualifier in defined, reference
            assert qualifiers[-1].startswith("test"), reference
    assert art["coverage_summary"]["every_named_test_exists"] is True
    assert art["coverage_summary"]["every_named_test_module_is_pinned"] is True


def test_coverage_summary_partitions_the_rule_inventory():
    art = _artifact()
    summary = art["coverage_summary"]
    rules = {rule["id"]: rule for rule in art["rule_inventory"]}
    assert set(summary["rules_with_cross_engine_cases"]) | set(
        summary["rules_with_no_cross_engine_case"]
    ) == set(rules)
    assert not set(summary["rules_with_cross_engine_cases"]) & set(
        summary["rules_with_no_cross_engine_case"]
    )
    for rule_id in summary["rules_with_cross_engine_cases"]:
        assert rules[rule_id]["cross_engine"]["n_cases"] > 0
    for rule_id in summary["rules_with_no_cross_engine_case"]:
        assert rules[rule_id]["cross_engine"]["n_cases"] == 0
    for rule_id in summary["rules_with_an_ssa_worked_example"]:
        assert rules[rule_id]["ssa_worked_examples"]


def test_zero_coverage_rules_have_no_case_of_any_kind():
    art = _artifact()
    rules = {rule["id"]: rule for rule in art["rule_inventory"]}
    derived = [
        rule["id"]
        for rule in art["rule_inventory"]
        if rule["cross_engine"]["n_cases"] == 0
        and not rule["ssa_worked_examples"]
        and not rule["pe_us_foundation_cases"]
    ]
    assert [row["id"] for row in art["zero_coverage_rules"]] == derived
    assert art["n_zero_coverage_rules"] == len(derived)
    for row in art["zero_coverage_rules"]:
        assert row["only_evidence"] == rules[row["id"]]["tests"]
        assert row["only_evidence"], row["id"]


def test_packet_verdicts_are_quoted_as_proposals_not_adopted():
    for rule in _artifact()["rule_inventory"]:
        block = rule["packet_proposed_verdict"]
        assert block["status"] == "proposal_not_ratified"
        assert block["verdict"]
        # The artifact records no verdict of its own; only the three
        # condition statuses and the packet's proposal.
        assert "verdict" not in rule


# --------------------------------------------------------------------------
# Cross-engine evidence recomputes from the committed artifact
# --------------------------------------------------------------------------
def test_cross_engine_inventory_recomputes():
    art = _artifact()["evidence_inventory"]["cross_engine"]
    cross = json.loads(CROSS_ENGINE.read_text())
    rows = cross["workers"]
    assert art["n_cases"] == cross["n_workers"] == len(rows) == 240
    assert art["n_exact_to_cent"] == cross["n_exact_to_cent"]
    assert art["max_abs_diff_dollars"] == cross["max_abs_diff_dollars"]
    shapes: dict[str, int] = {}
    for row in rows:
        shapes[row["shape"]] = shapes.get(row["shape"], 0) + 1
    assert art["shape_counts"] == dict(sorted(shapes.items()))
    assert art["n_distinct_shapes"] == len(shapes)
    assert sum(art["shape_counts"].values()) == 240


def test_bracket_occupancy_recomputes_from_committed_aime_values():
    art = _artifact()["evidence_inventory"]["cross_engine"]
    rows = json.loads(CROSS_ENGINE.read_text())["workers"]
    for cohort, block in art["bracket_occupancy"].items():
        first, second = block["bend_points"]
        aimes = [r["aime_oracle"] for r in rows if str(r["cohort"]) == cohort]
        assert block["n"] == len(aimes)
        assert block["n_aime_zero"] == sum(1 for a in aimes if a == 0)
        assert block["n_first_bracket_only"] == sum(
            1 for a in aimes if 0 < a <= first
        )
        assert block["n_reaching_second_bracket"] == sum(
            1 for a in aimes if first < a <= second
        )
        assert block["n_reaching_third_bracket"] == sum(
            1 for a in aimes if a > second
        )
        assert block["all_three_brackets_exercised"] is True


def test_dime_floor_coverage_recomputes_and_is_non_vacuous():
    art = _artifact()["evidence_inventory"]["cross_engine"]["dime_floor"]
    rows = json.loads(CROSS_ENGINE.read_text())["workers"]
    on_a_dime = sum(
        1
        for r in rows
        if abs(round(r["pia_oracle"] * 10) - r["pia_oracle"] * 10) < 1e-6
    )
    not_whole = sum(
        1 for r in rows if abs(r["pia_oracle"] - round(r["pia_oracle"])) > 1e-9
    )
    assert art["n_pia_values_on_an_exact_dime"] == on_a_dime == len(rows)
    assert art["n_pia_values_not_a_whole_dollar"] == not_whole > 0


def test_r3_degeneracy_rests_on_the_artifacts_own_note():
    art = _artifact()
    cross = json.loads(CROSS_ENGINE.read_text())
    rule = next(
        r
        for r in art["rule_inventory"]
        if r["id"] == "R3_415b2B_computation_year_count"
    )
    assert rule["e1"]["status"] == "degenerate"
    assert rule["cross_engine"]["n_cases_distinguishing_the_constant"] == 0
    assert rule["cross_engine"]["artifact_note"] == cross["notes"]
    assert "hard-coded 35" in cross["notes"]


def test_r4_zero_pad_branch_is_recorded_as_unexercised():
    art = _artifact()
    cross = json.loads(CROSS_ENGINE.read_text())
    rule = next(
        r
        for r in art["rule_inventory"]
        if r["id"] == "R4_415b_top_n_divide_and_floor"
    )
    assert rule["cross_engine"]["n_cases_reaching_the_zero_pad_branch"] == 0
    assert rule["e3"]["status"] == "branch_unexercised"
    # The reason is the committed worker design: 41-year histories can
    # never be shorter than the 35 computation years.
    assert "41 calendar years" in cross["worker_design"]
    # The claim rests on a source read, not on the committed rows, and
    # the artifact must say so and name the builder it read.
    source = rule["cross_engine"]["derivation_source"]
    assert "scripts/build_cross_engine_pia_artifact.py" in source
    assert "_build_workers" in source
    assert (ROOT / "scripts" / "build_cross_engine_pia_artifact.py").is_file()
    assert "not a row-level derivation" in source


def test_r2_branch_derivation_names_its_source_and_checks_out():
    art = _artifact()
    cross = json.loads(CROSS_ENGINE.read_text())
    rule = next(
        r
        for r in art["rule_inventory"]
        if r["id"] == "R2_415b3_nawi_indexation"
    )
    block = rule["cross_engine"]["branch_derivation_inputs"]
    low, high = block["history_span_ages"]
    assert (
        block["n_years_at_or_after_indexing_year"]
        + block["n_years_before_indexing_year"]
        == high - low + 1
    )
    assert (
        block["n_years_at_or_after_indexing_year"]
        == high - block["indexing_age"] + 1
    )
    assert "worker_design" in rule["cross_engine"]["derivation_source"]
    assert "41 calendar years" in cross["worker_design"]
    # The indexing age quoted is the oracle's own constant.
    benefits = (
        ROOT / "src" / "populace_dynamics" / "ss" / "benefits.py"
    ).read_text()
    assert f"_INDEXING_AGE = {block['indexing_age']}" in benefits
    # Both committed cohorts put the indexing year inside the span.
    for cohort in cross["cohorts"].values():
        birth = cohort["birth_year"]
        assert birth + low <= birth + block["indexing_age"] <= birth + high


def test_foundation_factor_split_recomputes():
    art = _artifact()["evidence_inventory"]["pe_us_pia_foundation"]
    cases = json.loads(AUX.read_text())["pe_us_pia_foundation"]["cases"]
    factors = art["factor_coverage"]
    assert art["n_cases"] == len(cases) == 40
    assert factors["n_cases_invoking_402q_reduction"] == sum(
        1 for c in cases if c["our_factor"] < 1.0
    )
    assert factors["n_cases_invoking_402w_credit"] == sum(
        1 for c in cases if c["our_factor"] > 1.0
    )
    assert factors["n_cases_exactly_at_fra"] == sum(
        1 for c in cases if c["our_factor"] == 1.0
    )
    assert factors["n_cases_at_claim_age_62"] == sum(
        1 for c in cases if c["claim_age"] == 62
    )
    assert factors["n_cases_invoking_402q_reduction"] + factors[
        "n_cases_invoking_402w_credit"
    ] + factors["n_cases_exactly_at_fra"] == len(cases)


def test_rules_priced_on_the_foundation_use_its_derived_counts():
    art = _artifact()
    factors = art["evidence_inventory"]["pe_us_pia_foundation"][
        "factor_coverage"
    ]
    rules = {rule["id"]: rule for rule in art["rule_inventory"]}
    assert (
        rules["R8_402q_worker_early_reduction"]["pe_us_foundation_cases"]
        == factors["n_cases_invoking_402q_reduction"]
    )
    assert (
        rules["R9_402w_delayed_retirement_credit"]["pe_us_foundation_cases"]
        == factors["n_cases_invoking_402w_credit"]
    )
    assert (
        rules["R16_age62_composition"]["pe_us_foundation_cases"]
        == factors["n_cases_at_claim_age_62"]
    )


def test_worked_example_inventory_recomputes_and_records_the_ratios():
    art = _artifact()["evidence_inventory"]["ssa_worked_examples"]
    block = json.loads(AUX.read_text())["ssa_worked_examples"]
    committed = [
        example
        for group in ("spousal", "survivor")
        for example in block[group]
    ]
    assert art["n_examples"] == len(committed) == 10
    assert art["max_abs_deviation"] == block["max_abs_deviation"]
    by_name = {example["name"]: example for example in committed}
    for row in art["examples"]:
        source = by_name[row["name"]]
        assert row["expected"] == source["expected"]
        assert row["our_output"] == source["our_output"]
        assert row["citation"] == source["citation"]
        assert row["abs_deviation"] == pytest.approx(
            abs(source["our_output"] - source["expected"])
        )
        if row["base_pia"]:
            assert row["expected_over_base_pia"] == pytest.approx(
                round(source["expected"] / row["base_pia"], 8)
            )


def test_anchor_classification_is_the_packets_and_covers_every_row():
    art = _artifact()["evidence_inventory"]["ssa_worked_examples"]
    block = art["anchor_classification"]
    assert block["status"] == "proposal_not_ratified"
    split = set(block["packet_published_percentage_anchors"]) | set(
        block["packet_arithmetic_or_branch_selection"]
    )
    assert split == {row["name"] for row in art["examples"]}
    assert not set(block["packet_published_percentage_anchors"]) & set(
        block["packet_arithmetic_or_branch_selection"]
    )


def test_grid_thinness_recomputes():
    art = _artifact()["evidence_inventory"]["grids"]
    aux = json.loads(AUX.read_text())
    couple, survivor = aux["couple_grid"], aux["survivor_grid"]
    assert art["couple_grid"]["n_rows"] == len(couple) == 36
    assert art["couple_grid"][
        "n_rows_with_both_spouses_drawing_an_excess"
    ] == sum(
        1
        for r in couple
        if r["excess_spousal_worker"] > 0 and r["excess_spousal_spouse"] > 0
    )
    assert (
        art["couple_grid"]["n_rows_with_both_spouses_drawing_an_excess"] == 0
    )
    assert art["survivor_grid"]["n_rows"] == len(survivor) == 9
    assert len(art["survivor_grid"]["distinct_own_deceased_pia_pairs"]) == 1


# --------------------------------------------------------------------------
# X1 / X2: named constants and named non-coverage
# --------------------------------------------------------------------------
def test_every_not_implemented_search_reruns_and_is_still_empty():
    art = _artifact()["not_implemented"]
    assert art["all_absent"] is True
    for name, block in art["searches"].items():
        root = ROOT / block["search_root"]
        files = sorted(root.rglob("*.py"))
        assert block["n_files_searched"] == len(files), name
        hits = [
            f"{path.relative_to(ROOT).as_posix()}:{pattern}"
            for path in files
            for pattern in block["patterns"]
            if pattern in path.read_text()
        ]
        assert hits == block["hits"] == [], name


def test_family_maximum_absence_is_disclosed_where_it_bites():
    art = _artifact()["not_implemented"]["family_maximum_bites_here"]
    assert art["symbols"] == ["spousal_benefit", "widow_benefit"]
    household = (ROOT / art["consumer"]).read_text()
    # The consumer sums both own benefits and both excess spousal
    # amounts; nothing caps the total.
    assert "excess_spousal_a" in household
    assert "excess_spousal_b" in household
    assert "family_max" not in household


def test_named_constants_point_at_the_real_declarations():
    art = _artifact()["named_constants"]
    for key in (
        "computation_years",
        "survivor_reduction_period_months",
    ):
        span = art[key]["code"]
        line = (
            (ROOT / span["module"])
            .read_text()
            .splitlines()[span["first_line"] - 1]
        )
        assert span["symbol"] in line, key
        assert str(art[key]["value"]) in line, key
        assert art[key]["exact_domain"]
        assert art[key]["wrong_outside"]


def test_computation_year_constant_names_its_live_caller():
    art = _artifact()["named_constants"]["computation_years"]
    caller = art["live_caller_outside_the_domain"]
    assert caller["symbol"] == "widow_benefit"
    defined = _defined_names(caller["code"]["module"])
    assert defined["widow_benefit"] == (
        caller["code"]["first_line"],
        caller["code"]["last_line"],
    )


# --------------------------------------------------------------------------
# Packet reconciliation and byte-level reproduction
# --------------------------------------------------------------------------
def test_packet_reconciliation_records_each_difference_with_a_derivation():
    differences = _artifact()["packet_reconciliation"]["differences"]
    assert len(differences) >= 3
    for row in differences:
        assert row["field"]
        assert row["packet_states"]
        assert row["derived_here"]
        assert row["consequence"]


def test_clipped_shape_count_correction_matches_the_committed_shapes():
    art = _artifact()
    shapes = art["evidence_inventory"]["cross_engine"]["shape_counts"]
    rule = next(
        r for r in art["rule_inventory"] if r["id"] == "R1_415b1_wage_base_cap"
    )
    assert (
        rule["cross_engine"]["n_cases_labelled_wage_base_clipped"]
        == shapes["clipped_always"] + shapes["rand_clipped_always"]
    )
    assert rule["cross_engine"]["exact_binding_count_determinable"] is False


def test_build_reproduces_the_committed_artifact():
    builder = _import_builder()
    rebuilt = builder.build()
    committed = _artifact()
    assert set(rebuilt) == set(committed)
    for key in committed:
        if key == "build":
            continue
        assert rebuilt[key] == committed[key], key


def test_build_is_deterministic_across_runs():
    builder = _import_builder()
    first, second = builder.build(), builder.build()
    first.pop("build")
    second.pop("build")
    assert json.dumps(first, sort_keys=True) == json.dumps(
        second, sort_keys=True
    )
