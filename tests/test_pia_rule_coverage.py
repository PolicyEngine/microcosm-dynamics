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
  quotes ``gates.yaml``'s single ``"computes exactly"`` occurrence from
  a blob-pinned citation, and records where its derivation differs from
  the DRAFT packet's claim rather than silently adopting it.
* **Derived bases (v2).** The consumer symbols are re-derived by
  ``ast``; the R4 / R8 / R9 E3 bases are re-run as searches over
  ``tests/ss/``; the typed bend points are re-checked against every
  committed PIA; the ``gates.yaml`` citation is rescanned from the
  pinned blob (working tree while it matches, git object store after).
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import subprocess
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


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _pinned_gates_yaml(blob_sha1: str) -> bytes:
    """The pinned blob: the working tree while it matches, else the git
    object store (the citation must survive the gate commit)."""
    on_disk = GATES.read_bytes()
    if _git_blob_sha1(on_disk) == blob_sha1:
        return on_disk
    result = subprocess.run(
        ["git", "cat-file", "blob", blob_sha1],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    assert _git_blob_sha1(result.stdout) == blob_sha1
    return result.stdout


def test_computes_exactly_citation_is_blob_pinned_and_rescans_from_the_blob():
    """Referee B, D7: the citation is pinned to a gates.yaml BLOB so the
    commit that inserts the gate block changes neither this artifact
    nor this test."""
    art = _artifact()
    citation = art["gate_status"]["gates_yaml_citation"]
    assert citation["path"] == "gates.yaml"
    raw = _pinned_gates_yaml(citation["git_blob_sha1"])
    assert citation["sha256"] == hashlib.sha256(raw).hexdigest()
    assert citation["bytes"] == len(raw)
    lines = raw.decode("utf-8").splitlines()
    found = [
        {"line": index + 1, "text": line.strip()}
        for index, line in enumerate(lines)
        if citation["phrase"] in line
    ]
    assert citation["phrase"] == "computes exactly"
    assert citation["occurrences"] == found
    assert citation["n_occurrences"] == len(found) == 1
    assert found[0]["line"] == citation["cited_line"] == 642
    assert citation["cited_line_text"] == lines[641].strip()
    assert (
        art["computes_exactly_definition_proposal"]["gates_yaml_line_642"]
        == lines[641].strip()
    )
    assert (
        art["computes_exactly_definition_proposal"][
            "gates_yaml_line_642_pinned_to_blob"
        ]
        == citation["git_blob_sha1"]
    )
    assert citation["gate_b2_pia_oracle_present_in_pinned_blob"] is False
    assert "gate_b2_pia_oracle" not in raw.decode("utf-8")


def test_gates_yaml_citation_pin_is_the_builders_constant():
    builder = _import_builder()
    citation = _artifact()["gate_status"]["gates_yaml_citation"]
    assert citation["git_blob_sha1"] == builder.GATES_YAML_BLOB_SHA1
    assert len(citation["git_blob_sha1"]) == 40


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
    # Referee A, section 5.a item 6: the family-maximum search must
    # also cover the other names an implementation might carry.
    assert set(art["searches"]["family_maximum"]["patterns"]) >= {
        "family_max",
        "familyMax",
        "maximum_family_benefit",
        "fam_max",
    }
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
    assert "CoupleBenefit.total" in art["note"]
    assert "CoupleBenefits" not in art["note"]


def test_consumer_symbols_are_pinned_by_ast_and_the_v1_name_does_not_exist():
    """F1 (referee B, D4; referee A, F9-4): the class is CoupleBenefit;
    CoupleBenefits exists nowhere. Re-derived here with ast."""
    art = _artifact()
    consumer = art["sources"]["consumer"]["path"]
    tree = ast.parse((ROOT / consumer).read_text())
    classes = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert "CoupleBenefit" in classes
    assert "CoupleBenefits" not in classes
    assert "CoupleBenefits" not in functions
    assert "couple_benefits" not in functions
    assert "couple_benefit" in functions
    methods = {
        node.name
        for node in ast.walk(classes["CoupleBenefit"])
        if isinstance(node, ast.FunctionDef)
    }
    assert "total" in methods
    for block in (
        art["sources"]["consumer_symbols"],
        art["not_implemented"]["family_maximum_bites_here"][
            "consumer_symbols"
        ],
    ):
        assert block["qualified_summation_symbol"] == "CoupleBenefit.total"
        assert block["class"]["symbol"] == "CoupleBenefit"
        assert block["class"]["kind"] == "class"
        assert (block["class"]["first_line"], block["class"]["last_line"]) == (
            classes["CoupleBenefit"].lineno,
            classes["CoupleBenefit"].end_lineno,
        )
        assert block["summation_property"]["symbol"] == "total"
        assert block["function"]["symbol"] == "couple_benefit"
        assert (
            block["function"]["first_line"],
            block["function"]["last_line"],
        ) == (
            functions["couple_benefit"].lineno,
            functions["couple_benefit"].end_lineno,
        )
        assert block["name_the_v1_artifact_used"] == "CoupleBenefits"
        assert block["name_the_v1_artifact_used_exists"] is False
        assert block["packet_name_exists"] is False
    # No identifier under src/ or tests/ is the plural name (an ast
    # scan of names, attributes and definitions -- not a substring
    # search, which would trip on this very sentence).
    plural = "CoupleBenefit" + "s"
    for root in ("src", "tests"):
        for path in (ROOT / root).rglob("*.py"):
            tree = ast.parse(path.read_text())
            identifiers = (
                {
                    node.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Name)
                }
                | {
                    node.attr
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Attribute)
                }
                | {
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                }
            )
            assert plural not in identifiers, path
    recon = next(
        row
        for row in art["packet_reconciliation"]["differences"]
        if "household consumer" in row["field"]
    )
    assert "CoupleBenefit.total" in recon["derived_here"]
    assert "CoupleBenefits" in recon["v1_defect"]


def test_spans_fail_loudly_on_a_duplicate_function_name():
    """Referee A, section 5.a item 7: a nested helper with a colliding
    name must not silently relabel a rule's span."""
    builder = _import_builder()
    probe = ROOT / "tests" / "_dup_span_probe_tmp.py"
    probe.write_text("def f():\n    pass\n\n\ndef f():\n    pass\n")
    try:
        with pytest.raises(ValueError, match="duplicate function name 'f'"):
            builder._spans("tests/_dup_span_probe_tmp.py")
    finally:
        probe.unlink()
    # The three pinned modules have no duplicate function or class name.
    for relative in (
        "src/populace_dynamics/ss/benefits.py",
        "src/populace_dynamics/ss/params.py",
        "src/populace_dynamics/household.py",
    ):
        assert builder._spans(relative)


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
# v2: the checkable E3 bases are derived and re-run here (A6 / B D5)
# --------------------------------------------------------------------------
def _rule(art, rule_id):
    return next(r for r in art["rule_inventory"] if r["id"] == rule_id)


def _calls_in_tests_ss(function_name):
    """This module's own ast scan of tests/ss/ for calls of a name."""
    sites = []
    for path in sorted((ROOT / "tests" / "ss").rglob("*.py")):
        tree = ast.parse(path.read_text())
        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef):
                continue
            for node in ast.walk(function):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = (
                    func.id
                    if isinstance(func, ast.Name)
                    else func.attr if isinstance(func, ast.Attribute) else None
                )
                if name == function_name:
                    first = node.args[0] if node.args else None
                    sites.append(
                        (
                            path.relative_to(ROOT).as_posix(),
                            function.name,
                            node.lineno,
                            (
                                first.value
                                if isinstance(first, ast.Constant)
                                else None
                            ),
                        )
                    )
    return sites


def test_r8_basis_no_test_asserts_early_reduction_at_zero_is_derived():
    art = _artifact()
    block = _rule(art, "R8_402q_worker_early_reduction")["e3"][
        "basis_derivation"
    ]
    sites = _calls_in_tests_ss("early_reduction")
    assert block["n_call_sites"] == len(sites) >= 1
    assert [
        (
            s["module"],
            s["enclosing_function"],
            s["line"],
            s["first_argument_literal"],
        )
        for s in block["call_sites"]
    ] == sites
    literals = sorted({s[3] for s in sites if s[3] is not None})
    assert block["first_argument_literals"] == literals
    assert 0 not in literals
    assert block["zero_or_negative_asserted"] is False
    assert block["claim_holds"] is True
    assert block["every_first_argument_is_a_literal"] is True
    assert (
        _rule(art, "R8_402q_worker_early_reduction")["e3"]["status"]
        == "partial_and_one_branch_unexercised"
    )


def test_r4_basis_no_test_reaches_the_zero_pad_is_derived():
    art = _artifact()
    block = _rule(art, "R4_415b_top_n_divide_and_floor")["e3"][
        "basis_derivation"
    ]
    sites = _calls_in_tests_ss("aime")
    assert block["n_call_sites"] == len(sites) >= 1
    assert block["computation_years"] == 35
    for recorded, (module, function, line, _) in zip(
        block["call_sites"], sites, strict=True
    ):
        assert (
            recorded["module"],
            recorded["enclosing_function"],
            recorded["line"],
        ) == (
            module,
            function,
            line,
        )
        # Re-derive the literal range lengths inside the enclosing test.
        tree = ast.parse((ROOT / module).read_text())
        lengths = [
            node.args[1].value - node.args[0].value
            for fn in ast.walk(tree)
            if isinstance(fn, ast.FunctionDef) and fn.name == function
            for node in ast.walk(fn)
            if isinstance(node, ast.Call)
            and (isinstance(node.func, ast.Name) and node.func.id == "range")
            and len(node.args) == 2
            and all(isinstance(a, ast.Constant) for a in node.args)
        ]
        assert recorded["literal_range_lengths_in_enclosing_test"] == lengths
        assert lengths and min(lengths) >= 35
        assert recorded["min_history_length_if_literal"] == min(lengths)
    assert block["every_direct_aime_test_builds_at_least_n_years"] is True
    assert block["claim_holds"] is True
    assert "static ast read" in block["derivation_kind"]


def test_r9_basis_dead_branch_is_derived_from_the_committed_schedule():
    art = _artifact()
    block = _rule(art, "R9_402w_delayed_retirement_credit")["e3"][
        "basis_derivation"
    ]
    doc = json.loads(
        (
            ROOT / "data" / "external" / "ssa_claim_ages_2023supplement.json"
        ).read_text()
    )
    fra_values = sorted(
        {int(r["fra_months"]) for r in doc["fra_schedule"]["schedule"]}
    )
    benefits = (
        ROOT / "src" / "populace_dynamics" / "ss" / "benefits.py"
    ).read_text()
    params = (
        ROOT / "src" / "populace_dynamics" / "ss" / "params.py"
    ).read_text()
    assert "_AGE_70_MONTHS = 70 * 12" in benefits
    assert "max_delayed_months: int = 48" in params
    assert block["age_70_months"] == 840
    assert block["max_delayed_months"] == 48
    assert block["fra_months_values"] == fra_values
    assert block["max_fra_months"] == max(fra_values) == 804
    assert block["window_months_by_fra"] == {
        str(fra): min(48, 840 - fra) for fra in fra_values
    }
    assert block["min_window_months"] == 36
    assert block["branch_reachable_iff_fra_months_at_least"] == 840
    assert block["claim_holds"] is True


def test_status_provenance_discloses_typed_labels_and_derived_bases():
    art = _artifact()
    block = art["status_provenance"]
    assert "builder's READING" in block["statement"]
    assert block["rules_with_a_derived_e3_basis"] == ["R4", "R8", "R9"]
    assert block["every_derived_basis_holds"] is True
    for rule in art["rule_inventory"]:
        for condition in ("e1", "e2", "e3"):
            assert isinstance(rule[condition]["status"], str)


# --------------------------------------------------------------------------
# v2: the typed bend points are pinned to the committed rows (B D6)
# --------------------------------------------------------------------------
def _own_pia(aime, first, second):
    amount = (
        0.90 * min(aime, first)
        + 0.32 * max(0.0, min(aime, second) - first)
        + 0.15 * max(0.0, aime - second)
    )
    return math.floor(amount * 10.0 + 1e-9) / 10.0


def test_typed_bend_points_reproduce_every_committed_pia_and_are_unique():
    art = _artifact()
    block = art["evidence_inventory"]["cross_engine"]["bend_points_provenance"]
    rows = json.loads(CROSS_ENGINE.read_text())["workers"]
    assert block["pia_factors_typed"] == [0.9, 0.32, 0.15]
    assert set(block["by_cohort"]) == {"2020", "2026"}
    for cohort, cell in block["by_cohort"].items():
        first, second = cell["typed_pair"]
        occupancy = art["evidence_inventory"]["cross_engine"][
            "bracket_occupancy"
        ][cohort]
        assert occupancy["bend_points"] == [first, second]
        cohort_rows = [r for r in rows if str(r["cohort"]) == cohort]
        reproduced = sum(
            1
            for r in cohort_rows
            if abs(_own_pia(r["aime_oracle"], first, second) - r["pia_oracle"])
            < 1e-9
        )
        assert cell["n_rows"] == len(cohort_rows) == 120
        assert cell["n_rows_reproduced_to_the_dime"] == reproduced == 120
        assert cell["reproduces_every_committed_pia"] is True
        neighbours = [
            [first + d1, second + d2]
            for d1 in range(-3, 4)
            for d2 in range(-3, 4)
            if (d1, d2) != (0, 0)
            and all(
                abs(
                    _own_pia(r["aime_oracle"], first + d1, second + d2)
                    - r["pia_oracle"]
                )
                < 1e-9
                for r in cohort_rows
            )
        ]
        assert (
            cell[
                "neighbouring_integer_pairs_within_3_dollars_also_reproducing_all_rows"
            ]
            == neighbours
            == []
        )
        assert cell["pair_is_unique_within_3_dollars"] is True
    assert block["by_cohort"]["2020"]["typed_pair"] == [960.0, 5785.0]
    assert block["by_cohort"]["2026"]["typed_pair"] == [1286.0, 7749.0]
    assert block["by_cohort"]["2020"]["ssa_anchor_test"] is None
    anchor = block["by_cohort"]["2026"]["ssa_anchor_test"]
    module, test = anchor.split("::")
    assert test in _defined_names(module)
    assert block["pairs_without_an_ssa_anchor_test"] == ["2020"]
    assert block["every_pair_reproduces_its_cohort"] is True


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
