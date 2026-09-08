"""Tests for the PIA gate partition v1 artifact
(runs/pia_gate_partition_v1.json): the THRESHOLD-BINDING derivation from
the verified coverage record runs/pia_rule_coverage_v1.json.

The artifact is a REPORTED record (reads no gate, changes no gate,
awards no status): it derives the per-rule E1 / E2 / E3 partition under
an explicit total mapping and under every filed alternative reading,
the precision claim, the worked-example classification, the E1 clause,
the family-maximum and frozen-scope disclosures, the certification
scope with what a pass does not authorise, the rulings filed and priced
-- and carries the DRAFT ``gate_b2_pia_oracle`` block as a string.

All tests are always runnable: they touch only committed files and the
two builders; no engine runs. The bindings that recompute the partition
with the test module's own mapping, the alternatives, the ast
re-derivations and the mutated-builder test live in
``tests/test_gates_derivations.py``; this file pins the artifact, its
builder and its internal consistency, and holds the PRE-LOCK MARKER
``GATE_B2_PIA_ORACLE_BLOCK_LANDED``.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "pia_gate_partition_v1.json"
COVERAGE = ROOT / "runs" / "pia_rule_coverage_v1.json"
GATES = ROOT / "gates.yaml"
SCRIPTS = ROOT / "scripts"
BUILDER = SCRIPTS / "build_pia_gate_partition_v1.py"
COVERAGE_BUILDER = SCRIPTS / "build_pia_rule_coverage.py"

#: The VERIFIED coverage record (floors v2 at cd8f167). Must not move.
COVERAGE_COMMITTED = (
    75_382,
    "7517d27a78eaa85ec4a12f1dfe9663e535c4ea54ca3d6edf5648ea075dd6d25d",
)
#: THIS artifact's committed bytes (size, sha256), re-stated in the same
#: commit as any rebuild.
GATE_V1_COMMITTED = (
    169_031,
    "d14b7192425cc1f91e0e853fd48bca5896f89b1ddb1d2f20cccec24f984735aa",
)
#: PRE-LOCK MARKER. False until the commit that inserts the
#: gate_b2_pia_oracle block flips it, in every file the artifact's
#: flip_plan names, in the same commit.
GATE_B2_PIA_ORACLE_BLOCK_LANDED = False

RULE_IDS = (
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


def _coverage() -> dict:
    return json.loads(COVERAGE.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _import_builder():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import build_pia_gate_partition_v1 as builder

    return builder


def _block(art: dict) -> dict:
    text = art["draft_gates_yaml_fragment"]["text"]
    return yaml.safe_load("gates:\n" + text)["gates"]["gate_b2_pia_oracle"]


# --------------------------------------------------------------------------
# Framing and pins
# --------------------------------------------------------------------------
def test_schema_reported_and_nothing_awarded():
    art = _artifact()
    assert art["schema_version"] == "pia_gate_partition.v1"
    assert art["run"] == "pia_gate_partition_v1"
    assert art["reported_not_gated"] is True
    assert art["ceremony"]["gates_yaml_untouched"] is True
    dnd = " ".join(art["does_not_do"])
    for phrase in (
        "edit gates.yaml",
        "execute the Axiom rules engine",
        "award any per-rule status",
        "make any ruling",
    ):
        assert phrase in dnd, phrase


def test_artifact_bytes_are_pinned_to_the_committed_digest():
    assert ARTIFACT.stat().st_size == GATE_V1_COMMITTED[0]
    assert _sha(ARTIFACT) == GATE_V1_COMMITTED[1]


def test_source_coverage_is_the_verified_v2_read_by_path():
    art = _artifact()
    assert COVERAGE.stat().st_size == COVERAGE_COMMITTED[0]
    assert _sha(COVERAGE) == COVERAGE_COMMITTED[1]
    src = art["source_coverage"]
    assert (src["size_bytes"], src["sha256"]) == COVERAGE_COMMITTED
    assert src["path"] == "runs/pia_rule_coverage_v1.json"
    coverage = _coverage()
    assert src["built_utc"] == coverage["build"]["built_utc"]
    for rel, sha in src["its_source_pins_rechecked_on_disk"].items():
        assert _sha(ROOT / rel) == sha, rel
    assert (
        art["coverage_does_not_establish_carried"]
        == coverage["does_not_establish"]
    )
    assert (
        art["computes_exactly_definition_carried"]
        == coverage["computes_exactly_definition_proposal"]
    )
    assert art["status_provenance_carried"] == coverage["status_provenance"]
    assert art["named_constants_carried"] == coverage["named_constants"]
    assert (
        art["packet_reconciliation_carried"]
        == coverage["packet_reconciliation"]
    )


def test_builders_are_sha_pinned():
    art = _artifact()
    pins = art["revision_pins"]
    assert pins["gate_builder_sha256"] == _sha(BUILDER)
    assert pins["coverage_builder_sha256"] == _sha(COVERAGE_BUILDER)
    assert pins["source_coverage_sha256"] == COVERAGE_COMMITTED[1]


def test_gates_yaml_pre_lock_guard():
    text = GATES.read_text()
    art = _artifact()
    if not GATE_B2_PIA_ORACLE_BLOCK_LANDED:
        for name in (
            "gate_b2_pia_oracle",
            "pia_gate_partition_v1",
            "pia_rule_coverage_v1",
        ):
            assert name not in text, name
        cites = art["gates_yaml_citations"]
        assert cites["gate_b2_pia_oracle_present"] is False
        assert cites["artifact_named"] is False
        assert cites["coverage_named"] is False
        return
    assert "gate_b2_pia_oracle" in yaml.safe_load(text)["gates"]


def test_gates_yaml_citations_derive_by_search_on_the_pinned_blob():
    art = _artifact()
    coverage = _coverage()
    cites = art["gates_yaml_citations"]
    assert (
        cites["git_blob_sha1"]
        == coverage["gate_status"]["gates_yaml_citation"]["git_blob_sha1"]
    )
    assert cites["computes_exactly"]["occurrences"] == [
        coverage["gate_status"]["gates_yaml_citation"]["cited_line"]
    ]
    assert cites["computes_exactly"]["n_occurrences"] == 1
    assert 1056 in cites["standing_rule_lines"]
    assert 3294 in cites["standing_rule_lines"]
    assert 4869 in cites["standing_rule_lines"]
    lc = cites["line_citations"]
    assert lc["no_self_rescue"] == 565
    assert lc["gate_2_n_gated_cells"] == 917
    assert lc["gate_2_own_record_outside_2a_2b_2c"] == 782
    if cites["byte_identical_to_working_tree"]:
        lines = GATES.read_text().split("\n")
        assert "computes exactly" in lines[641]
        assert "n_gated_cells: 46" in lines[916]
        assert "OUTSIDE 2a / 2b / 2c" in lines[781]


# --------------------------------------------------------------------------
# The partition and the derived blocks
# --------------------------------------------------------------------------
def test_rule_order_and_partition_counts():
    art = _artifact()
    assert tuple(art["rule_order"]) == RULE_IDS
    gp = art["gate_partition"]
    assert gp["all_three"] == ["R10_416l_fra_schedule"]
    assert (gp["n_all_three"], gp["n_strict_subset"], gp["n_none"]) == (
        1,
        10,
        5,
    )
    assert gp["reading_applied"].startswith("strict")
    assert set(gp["rulings_that_can_move_it"]) == {
        "P1",
        "P6",
        "P8",
        "P9",
        "P13",
    }
    strict = art["partitions"]["strict"]
    assert set(strict["all_three"]) | set(strict["strict_subset"]) | set(
        strict["none"]
    ) == set(RULE_IDS)
    for rid, entry in strict["per_rule"].items():
        n_failing = len(entry["failing_conditions"])
        expected = {
            0: "all_three",
            1: "strict_subset",
            2: "strict_subset",
            3: "none",
        }
        assert entry["class"] == expected[n_failing], rid
        assert entry["e1_waived"] is False


def test_partition_mapping_is_total_over_the_coverage_labels():
    art = _artifact()
    coverage = _coverage()
    mapping = art["partitions"]["strict"]["mapping"]
    for condition in ("e1", "e2", "e3"):
        used = {r[condition]["status"] for r in coverage["rule_inventory"]}
        assert used <= set(mapping[condition]), condition
    for rule in coverage["rule_inventory"]:
        entry = art["partitions"]["strict"]["per_rule"][rule["id"]]
        assert entry["status_labels"] == {
            "e1": rule["e1"]["status"],
            "e2": rule["e2"]["status"],
            "e3": rule["e3"]["status"],
        }
        assert entry["holds"] == {
            "e1": mapping["e1"][rule["e1"]["status"]],
            "e2": mapping["e2"][rule["e2"]["status"]],
            "e3": mapping["e3"][rule["e3"]["status"]],
        }


def test_alternative_readings_keep_r10_as_the_only_full_award():
    art = _artifact()
    alts = art["partitions"]["alternatives"]
    for name in (
        "axiom_only_e1",
        "p6_e1_waiver_for_r11_r15",
        "p9_constant_override_counts_as_e2",
        "p6_waiver_and_p9_override",
    ):
        assert alts[name]["all_three"] == ["R10_416l_fra_schedule"], name
        assert "moves_vs_strict" in alts[name]
        assert "ruling" in alts[name]
    assert art["partitions"]["invariant_under_every_reading"][
        "rules_holding_all_three_under_every_variant"
    ] == ["R10_416l_fra_schedule"]
    packet = alts["packet_proposed_verdicts"]
    assert set(packet["verdicts"]) == set(RULE_IDS)
    assert (
        "R10_416l_fra_schedule"
        in packet[
            "rules_the_packet_calls_computes_exactly_or_a_qualified_form"
        ]
    )


def test_precision_examples_case_set_and_granularity_blocks():
    art = _artifact()
    coverage = _coverage()
    p = art["precision_claim_P11"]
    assert p["agreement_tolerance_dollars"] == 0.005
    assert p["largest_observed_is_within_the_bound"] is True
    ex = art["worked_examples_classification_P7"]
    assert ex["n_examples"] == 10
    assert (
        ex["n_published_percentage"],
        ex["n_arithmetic_or_branch_selection"],
    ) == (
        7,
        3,
    )
    assert set(ex["examples"]) == {
        e["name"]
        for e in coverage["evidence_inventory"]["ssa_worked_examples"][
            "examples"
        ]
    }
    facts = art["case_set_P8"]
    assert facts["cross_engine"]["n_cases"] == 240
    assert facts["pe_us_foundation"]["n_cases"] == 40
    assert facts["couple_grid"]["n_rows"] == 36
    assert facts["survivor_grid"]["n_rows"] == 9
    assert set(facts["per_rule"]) == set(RULE_IDS)
    gran = art["granularity_P13"]
    assert gran["n_rules"] == 16
    assert (
        "R14_402ef_widow_riblim_drc_dual"
        in gran["rules_flagged_as_bundling_several_statutory_operations"]
    )


def test_e1_clause_family_maximum_and_frozen_scope_blocks():
    art = _artifact()
    clause = art["e1_clause_S8"]
    assert clause["clause"].startswith(
        "E1 as committed 2026-07-05 at engine ffef7b4"
    )
    assert clause["axiom_half"]["re_executed_in_this_ceremony"] is False
    assert (
        clause["policyengine_us_half"]["re_executed_in_this_ceremony"] is True
    )
    fm = art["family_maximum_P10"]
    assert (
        fm["consumer"]["qualified_summation_symbol"] == "CoupleBenefit.total"
    )
    assert fm["consumer"]["class_lines"] == [133, 149]
    assert fm["consumer"]["total_property_lines"] == [142, 149]
    assert fm["search"]["absent"] is True
    assert fm["search"]["hits"] == []
    frozen = art["frozen_scope_P15"]
    assert frozen["key_sentence_present_in_module"] is True
    assert "FORBIDDEN" in frozen["clause"]
    scope = art["certification_scope"]
    assert len(scope["does_not_authorise_P14"]) >= 7
    assert scope["partition_under_the_strict_reading"]["all_three"] == [
        "R10_416l_fra_schedule"
    ]


# --------------------------------------------------------------------------
# The DRAFT block
# --------------------------------------------------------------------------
def test_draft_block_parses_recomputes_its_digest_and_is_a_draft():
    art = _artifact()
    frag = art["draft_gates_yaml_fragment"]
    text = frag["text"]
    assert (
        frag["text_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    )
    assert frag["n_lines"] == len(text.splitlines())
    assert frag["n_bytes"] == len(text.encode("utf-8"))
    block = _block(art)
    assert block["id"] == "b2_statutory_benefit_oracle"
    assert block["status"] == "draft_pending_referee_round"
    assert block["locked"] is False
    assert block["kind"] == "exact_agreement_per_rule"
    assert block["floor_run"] == "runs/pia_gate_partition_v1.json"
    assert block["floor_run_sha256"] == "<FILLED AT RATIFICATION>"
    assert block["derived_from_coverage_sha256"] == COVERAGE_COMMITTED[1]
    t = block["thresholds"]
    assert t["locked"] is False
    assert t["coverage_run_sha256"] == COVERAGE_COMMITTED[1]
    assert set(t["rule_inventory"]) == set(RULE_IDS)
    assert t["partition"]["strict_reading"]["all_three"] == [
        "R10_416l_fra_schedule"
    ]
    assert (
        t["coverage_record_does_not_establish"]
        == _coverage()["does_not_establish"]
    )
    assert set(t["open_rulings"]) == {
        "P1",
        "P6",
        "P8",
        "P9",
        "P13",
        "S7",
        "S8",
    }
    for rid, entry in t["rule_inventory"].items():
        assert (
            entry["strict_reading"]["class"]
            == art["partitions"]["strict"]["per_rule"][rid]["class"]
        )


def test_draft_block_wording_audit_recomputes():
    art = _artifact()
    text = art["draft_gates_yaml_fragment"]["text"]
    flat = " ".join(text.split()).lower()
    assert {
        w: len(re.findall(rf"\b{w}\b", flat)) for w in ("anchored", "aligned")
    } == {
        "anchored": 0,
        "aligned": 0,
    }
    without = {k: v for k, v in art.items() if k != "wording_audit"}
    flat_art = " ".join(json.dumps(without).split()).lower()
    assert all(
        len(re.findall(rf"\b{w}\b", flat_art)) == 0
        for w in ("anchored", "aligned")
    )
    audit = art["wording_audit"]
    assert audit["forbidden_words_absent_from_fragment"] is True
    assert audit["forbidden_words_absent_from_artifact"] is True
    assert audit["all_required_phrases_present"] is True
    for item in audit["required_phrases"]:
        assert item["holds"] is True, item["item"]


def test_open_questions_and_flip_plan():
    art = _artifact()
    ids = [q["id"] for q in art["open_questions_for_the_ceremony"]]
    assert ids == ["P1", "P6", "P8", "P9", "P13", "S7", "S8"]
    plan = art["flip_plan"]
    assert plan["marker"] == "GATE_B2_PIA_ORACLE_BLOCK_LANDED"
    assert set(plan["files_carrying_the_marker"]) == {
        "tests/test_gates_derivations.py",
        "tests/test_pia_gate_partition_v1.py",
    }
    pattern = re.compile(
        r"^GATE_B2_PIA_ORACLE_BLOCK_LANDED = (True|False)$", re.M
    )
    for rel in plan["files_carrying_the_marker"]:
        found = pattern.findall((ROOT / rel).read_text())
        assert found == [str(GATE_B2_PIA_ORACLE_BLOCK_LANDED)], rel
    assert any(
        "test_computes_exactly_citation_is_blob_pinned" in s
        for s in plan["tests_that_survive_the_flip_unchanged"]
    )


# --------------------------------------------------------------------------
# Reproduction
# --------------------------------------------------------------------------
def _strip_volatile(art: dict) -> dict:
    out = json.loads(json.dumps(art))
    out.pop("elapsed_seconds", None)
    out["revision_pins"].pop("populace_dynamics_sha", None)
    return out


def test_build_reproduces_the_committed_artifact():
    builder = _import_builder()
    fresh = builder.run(verbose=False)
    committed = _artifact()
    assert _strip_volatile(fresh) == _strip_volatile(committed)
