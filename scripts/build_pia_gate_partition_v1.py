"""PIA gate partition v1: the GATE-SCHEMA derivation from the coverage record.

THRESHOLD BINDING for ``gate_b2_pia_oracle`` (the packet's ceremony step
5's prerequisite), NOT A GATE RUN, NOT A RATIFICATION. This script reads
the verified per-rule coverage record ``runs/pia_rule_coverage_v1.json``
BY PATH with its size and sha256 pinned and derives from its committed
E1 / E2 / E3 status labels, case sets and evidence inventory -- never
from typed verdicts -- everything the ``gate_b2_pia_oracle`` block needs:

* the per-rule E1 / E2 / E3 partition under an EXPLICIT, TOTAL mapping
  from status label to "holds" (every label the coverage record uses
  must be in the mapping, or the build fails): which rules hold all
  three, which a strict subset (and which condition fails), which none;
* the same partition under every filed alternative reading (Axiom-only
  E1; the P6 per-rule E1 waiver for R11-R15; the P9 constant-override
  reading of E2; the packet's own proposed verdicts) so a ruling changes
  a pointer, not a number;
* the precision claim to the cent (P11), the anchor-vs-arithmetic
  classification of the ten worked examples (P7), the E1 clause for the
  Axiom half with the policyengine-us half recorded as re-executed by
  the verification (S8), the family-maximum disclosure re-derived by
  ``ast`` (P10), the frozen-scope clause re-read from the module (P15),
  the certification scope with what a pass does NOT authorise (P14),
  the case-set facts (P8) and the granularity facts (P13);
* the rulings FILED and PRICED, none made
  (``open_questions_for_the_ceremony``: P1, P6, P8, P9, P13, S7, S8);
* the DRAFT ``gate_b2_pia_oracle`` block as a string
  (``draft_gates_yaml_fragment.text``) with every ruling a placeholder.

It writes NO ``gates.yaml`` byte, opens no committed artifact for
writing, executes NEITHER engine and awards no status. Run from the
repository root::

    .venv/bin/python scripts/build_pia_gate_partition_v1.py
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COVERAGE_REL = "runs/pia_rule_coverage_v1.json"
SOURCE_COVERAGE_PATH = ROOT / SOURCE_COVERAGE_REL
ARTIFACT_REL = "runs/pia_gate_partition_v1.json"
ARTIFACT_PATH = ROOT / ARTIFACT_REL
COVERAGE_BUILDER_REL = "scripts/build_pia_rule_coverage.py"
HOUSEHOLD_REL = "src/populace_dynamics/household.py"
SS_INIT_REL = "src/populace_dynamics/ss/__init__.py"
GATES_REL = "gates.yaml"

ARTIFACT_SCHEMA_VERSION = "pia_gate_partition.v1"
RUN_NAME = "pia_gate_partition_v1"
GATE_NAME = "gate_b2_pia_oracle"
MARKER = "GATE_B2_PIA_ORACLE_BLOCK_LANDED"

#: The VERIFIED coverage record this derivation reads (floors v2 at
#: cd8f167; independent verification VERIFIED -- READY FOR THRESHOLD
#: BINDING). Pinned here AND in tests/test_gates_derivations.py.
SOURCE_COVERAGE_COMMITTED = (
    75_382,
    "7517d27a78eaa85ec4a12f1dfe9663e535c4ea54ca3d6edf5648ea075dd6d25d",
)
GATES_YAML_BLOB_AT_BINDING = "b0c39af1e13a705f90b85d3e6b9a91e1d3c5485c"

#: The E1 clause (S8): the cross-engine artifact's committing commit and
#: date (git log -- runs/pia_cross_engine_v1.json: 80d3666, 2026-07-05)
#: and the verification's re-execution of the policyengine-us half.
CROSS_ENGINE_COMMIT = "80d3666"
CROSS_ENGINE_COMMIT_DATE = "2026-07-05"
PE_US_HALF_REEXECUTED = {
    "by": "the floors v2 independent verification (claiming-v2-verify/REPORT.md section 16)",
    "test": "tests/ss/test_aux_benefits.py::test_pe_us_simulation_matches_oracle_foundation_live",
    "cases": 12,
    "policyengine_us_checkout": "a03e82e5",
    "result": "PASSED (the oracle's pia() and benefit_factor() agreed to float32 precision)",
    "note": (
        "even on a host with the Axiom wheel, "
        "tests/ss/test_cross_engine.py::"
        "test_committed_artifact_matches_live_engine_spotcheck skips unless "
        "the policyengine-us checkout is at bf71be3b"
    ),
}
FORBIDDEN_WORDS = ("anchored", "aligned")

PACKET_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "cap-claiming-pia-gates/REPORT.md (104,338 bytes, sha256 "
    "de224e0ccb5a3f7d...)"
)
REFEREE_A_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "claiming-referee-A/REPORT.md (47,570 bytes, sha256 15e614b165bbbfe3...)"
)
REFEREE_B_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "claiming-referee-B/REPORT.md (62,507 bytes, sha256 4f4eebafdcb995ec...)"
)
FLOORS_V2_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "claiming-floors-v2/REPORT.md (49,890 bytes, sha256 303f077d9967a405...)"
)
VERIFICATION_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "claiming-v2-verify/REPORT.md (66,687 bytes, sha256 847f29ac0704c18c...)"
)

DOES_NOT_DO = [
    "edit gates.yaml (byte-identical to origin/master; the block lives "
    "only as the string in draft_gates_yaml_fragment.text)",
    f"open {SOURCE_COVERAGE_REL}, runs/pia_cross_engine_v1.json or "
    "runs/aux_benefit_examples_v1.json for writing",
    "execute the Axiom rules engine or a policyengine-us Simulation "
    "(neither is run here; the E1 clause records what was and was not "
    "re-executed in this ceremony)",
    "award any per-rule status: the partition is a READING of the "
    "coverage record's status labels under an explicit mapping, emitted "
    "under every filed alternative; the ratifying round fixes the "
    "mapping",
    "make any ruling: P1, P6, P8, P9, P13, S7 and S8 are FILED and "
    "PRICED in open_questions_for_the_ceremony",
    "retire the two live-file 'gate name absent' tests; the flip commit "
    "does that and flips the pre-lock markers in the same commit",
]

#: The mapping from the coverage record's status labels to "holds". It is
#: TOTAL over the labels the record uses (the build fails on an unmapped
#: label) and every variant is emitted beside the strict reading.
E1_STRICT = {
    "satisfied": True,
    "policyengine_us_only": True,
    "degenerate": False,
    "unsatisfiable_today": False,
}
E1_AXIOM_ONLY = {
    "satisfied": True,
    "policyengine_us_only": False,
    "degenerate": False,
    "unsatisfiable_today": False,
}
E2_STRICT = {
    "satisfied": True,
    "satisfied_with_a_constant_override": False,
    "weak": False,
    "partial": False,
    "implied": False,
    "absent": False,
}
E2_P9_OVERRIDE = {**E2_STRICT, "satisfied_with_a_constant_override": True}
E3_STRICT = {
    "all_branches_exercised": True,
    "exhaustive": True,
    "both_branches_reached": True,
    "partial": False,
    "partial_and_one_branch_unexercised": False,
    "partial_with_a_named_simplification": False,
    "branch_unexercised": False,
    "unexercised": False,
    "unit_test_only": False,
}
WAIVABLE_E1 = "unsatisfiable_today"
AUXILIARY_RULES = (
    "R11_402q1_spousal_early_reduction",
    "R12_402bc_402k3_spouse_benefit",
    "R13_402q_survivor_reduction_ramp",
    "R14_402ef_widow_riblim_drc_dual",
    "R15_402e3_f4_remarriage_protection",
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _sha_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pin(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    return {
        "path": relative,
        "sha256": _sha_of_file(path),
        "bytes": path.stat().st_size,
    }


def _git_sha(cwd: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=cwd, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _pinned_gates_yaml() -> bytes:
    on_disk = (ROOT / GATES_REL).read_bytes()
    if _git_blob_sha1(on_disk) == GATES_YAML_BLOB_AT_BINDING:
        return on_disk
    raw = subprocess.check_output(
        ["git", "cat-file", "blob", GATES_YAML_BLOB_AT_BINDING],
        cwd=ROOT,
        stderr=subprocess.DEVNULL,
    )
    if _git_blob_sha1(raw) != GATES_YAML_BLOB_AT_BINDING:
        raise RuntimeError("git object store returned the wrong blob")
    return raw


def normalized(text: str) -> str:
    return " ".join(text.split())


def short_id(rule_id: str) -> str:
    return rule_id.split("_", 1)[0]


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
def load_source_coverage() -> dict[str, Any]:
    size = SOURCE_COVERAGE_PATH.stat().st_size
    digest = _sha_of_file(SOURCE_COVERAGE_PATH)
    if (size, digest) != SOURCE_COVERAGE_COMMITTED:
        raise RuntimeError(
            f"{SOURCE_COVERAGE_REL} is not the verified artifact: "
            f"({size}, {digest}) != {SOURCE_COVERAGE_COMMITTED}"
        )
    return json.loads(SOURCE_COVERAGE_PATH.read_text())


def check_source_pins(coverage: dict[str, Any]) -> dict[str, Any]:
    """Every source the coverage record pins is still those bytes."""
    checked = {}
    groups = coverage["sources"]
    for group in ("oracle", "evidence_artifacts", "tests"):
        for pin in groups[group]:
            live = _pin(pin["path"])
            if (live["sha256"], live["bytes"]) != (
                pin["sha256"],
                pin["bytes"],
            ):
                raise RuntimeError(
                    f"{pin['path']} moved since the coverage build"
                )
            checked[pin["path"]] = live["sha256"]
    consumer = groups["consumer"]
    live = _pin(consumer["path"])
    if (live["sha256"], live["bytes"]) != (
        consumer["sha256"],
        consumer["bytes"],
    ):
        raise RuntimeError("household.py moved since the coverage build")
    checked[consumer["path"]] = live["sha256"]
    return checked


# --------------------------------------------------------------------------
# The partition, under the strict mapping and every alternative
# --------------------------------------------------------------------------
def _holds(mapping: dict[str, bool], label: str, condition: str) -> bool:
    if label not in mapping:
        raise RuntimeError(f"unmapped {condition} status label {label!r}")
    return mapping[label]


def partition_under(
    rules: list[dict[str, Any]],
    e1_map: dict[str, bool],
    e2_map: dict[str, bool],
    e3_map: dict[str, bool],
    *,
    waive_e1_label: str | None = None,
) -> dict[str, Any]:
    per_rule: dict[str, Any] = {}
    all_three: list[str] = []
    strict_subset: dict[str, Any] = {}
    none: list[str] = []
    for rule in rules:
        rid = rule["id"]
        labels = {
            "e1": rule["e1"]["status"],
            "e2": rule["e2"]["status"],
            "e3": rule["e3"]["status"],
        }
        waived = waive_e1_label is not None and labels["e1"] == waive_e1_label
        holds = {
            "e1": True if waived else _holds(e1_map, labels["e1"], "E1"),
            "e2": _holds(e2_map, labels["e2"], "E2"),
            "e3": _holds(e3_map, labels["e3"], "E3"),
        }
        failing = [c.upper() for c, h in holds.items() if not h]
        entry = {
            "status_labels": labels,
            "holds": holds,
            "e1_waived": waived,
            "failing_conditions": failing,
        }
        if not failing:
            entry["class"] = "all_three"
            all_three.append(rid)
        elif len(failing) < 3:
            entry["class"] = "strict_subset"
            strict_subset[rid] = failing
        else:
            entry["class"] = "none"
            none.append(rid)
        per_rule[rid] = entry
    return {
        "mapping": {
            "e1": e1_map,
            "e2": e2_map,
            "e3": e3_map,
            "e1_waived_for_label": waive_e1_label,
        },
        "all_three": all_three,
        "strict_subset": strict_subset,
        "none": none,
        "n_all_three": len(all_three),
        "n_strict_subset": len(strict_subset),
        "n_none": len(none),
        "per_rule": per_rule,
    }


def partitions(coverage: dict[str, Any]) -> dict[str, Any]:
    rules = coverage["rule_inventory"]
    strict = partition_under(rules, E1_STRICT, E2_STRICT, E3_STRICT)
    axiom_only = partition_under(rules, E1_AXIOM_ONLY, E2_STRICT, E3_STRICT)
    p6 = partition_under(
        rules, E1_STRICT, E2_STRICT, E3_STRICT, waive_e1_label=WAIVABLE_E1
    )
    p9 = partition_under(rules, E1_STRICT, E2_P9_OVERRIDE, E3_STRICT)
    p6_p9 = partition_under(
        rules,
        E1_STRICT,
        E2_P9_OVERRIDE,
        E3_STRICT,
        waive_e1_label=WAIVABLE_E1,
    )
    packet = {r["id"]: r["packet_proposed_verdict"]["verdict"] for r in rules}
    packet_computes_exactly = sorted(
        rid for rid, v in packet.items() if v.startswith("computes_exactly")
    )

    def diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
        moved = {}
        for rid in a["per_rule"]:
            ca, cb = a["per_rule"][rid]["class"], b["per_rule"][rid]["class"]
            fa = a["per_rule"][rid]["failing_conditions"]
            fb_ = b["per_rule"][rid]["failing_conditions"]
            if ca != cb or fa != fb_:
                moved[rid] = {
                    "strict": {"class": ca, "failing": fa},
                    "variant": {"class": cb, "failing": fb_},
                }
        return moved

    return {
        "strict": {
            "reading": (
                "the definition's letter: E1 holds iff an independent "
                "engine executed the rule on every registered case within "
                "the committed bound (Axiom on the 240, or the "
                "policyengine-us foundation block -- labels satisfied and "
                "policyengine_us_only); E2 holds iff at least one registered "
                "case's expected value is an SSA-published figure (label "
                "satisfied only); E3 holds iff every branch and boundary is "
                "hit (labels all_branches_exercised, exhaustive, "
                "both_branches_reached)"
            ),
            **strict,
        },
        "alternatives": {
            "axiom_only_e1": {
                "reading": "E1 requires the Axiom engine: policyengine_us_only does not count",
                "ruling": "a reading the round may prefer under P6's logic; not in the packet",
                **axiom_only,
                "moves_vs_strict": diff(strict, axiom_only),
            },
            "p6_e1_waiver_for_r11_r15": {
                "reading": (
                    "E1 WAIVED per rule where the label is "
                    f"{WAIVABLE_E1} (no second engine exists for the "
                    "auxiliary path, by construction); the waiver is named "
                    "per rule and does not fail the rule"
                ),
                "ruling": "P6 option (a)",
                **p6,
                "moves_vs_strict": diff(strict, p6),
            },
            "p9_constant_override_counts_as_e2": {
                "reading": (
                    "E2 holds for satisfied_with_a_constant_override: the "
                    "81-percent-at-62 survivor example reproduces SSA only "
                    "by overriding survivor_reduction_period_months to 72 "
                    "in its inputs (shipped default 84)"
                ),
                "ruling": "P9 option (b)",
                **p9,
                "moves_vs_strict": diff(strict, p9),
            },
            "p6_waiver_and_p9_override": {
                "reading": "both alternatives together",
                "ruling": "P6 (a) + P9 (b)",
                **p6_p9,
                "moves_vs_strict": diff(strict, p6_p9),
            },
            "packet_proposed_verdicts": {
                "reading": (
                    "the packet's own per-rule verdict strings, quoted for "
                    "comparison and NOT adopted (the coverage record marks "
                    "them proposal_not_ratified)"
                ),
                "verdicts": packet,
                "rules_the_packet_calls_computes_exactly_or_a_qualified_form": packet_computes_exactly,
                "rules_holding_all_three_under_the_strict_reading": strict[
                    "all_three"
                ],
                "packet_qualified_forms_that_the_strict_reading_does_not_award": sorted(
                    set(packet_computes_exactly) - set(strict["all_three"])
                ),
            },
        },
        "invariant_under_every_reading": {
            "rules_holding_all_three_under_every_variant": sorted(
                set(strict["all_three"])
                & set(axiom_only["all_three"])
                & set(p6["all_three"])
                & set(p9["all_three"])
                & set(p6_p9["all_three"])
            ),
            "rules_holding_none_under_every_variant": sorted(
                set(strict["none"])
                & set(axiom_only["none"])
                & set(p6["none"])
                & set(p9["none"])
                & set(p6_p9["none"])
            ),
        },
    }


# --------------------------------------------------------------------------
# P7, P8, P11, P13, S8 -- read from the coverage record, derived where it
# can be
# --------------------------------------------------------------------------
def _decimals(value: float) -> int:
    text = repr(value)
    if "e" in text or "E" in text:
        return 17
    return len(text.split(".")[1]) if "." in text else 0


def worked_examples(coverage: dict[str, Any]) -> dict[str, Any]:
    block = coverage["evidence_inventory"]["ssa_worked_examples"]
    cls = block["anchor_classification"]
    published = set(cls["packet_published_percentage_anchors"])
    arithmetic = set(cls["packet_arithmetic_or_branch_selection"])
    rows = {}
    for ex in block["examples"]:
        name = ex["name"]
        if name in published:
            label = "published_percentage"
        elif name in arithmetic:
            label = "arithmetic_or_branch_selection"
        else:
            raise RuntimeError(f"unclassified worked example {name}")
        rows[name] = {
            "group": ex["group"],
            "citation": ex["citation"],
            "expected": ex["expected"],
            "our_output": ex["our_output"],
            "abs_deviation": ex["abs_deviation"],
            "expected_over_base_pia": ex["expected_over_base_pia"],
            "ratio_decimal_places": _decimals(ex["expected_over_base_pia"]),
            "agrees_to_the_cent": abs(ex["our_output"] - ex["expected"])
            <= 0.005,
            "packet_classification": label,
        }
    by_rule = {}
    for rule in coverage["rule_inventory"]:
        names = rule["ssa_worked_examples"]
        if not names:
            continue
        by_rule[rule["id"]] = {
            "examples": names,
            "published_percentage": [
                n
                for n in names
                if rows[n]["packet_classification"] == "published_percentage"
            ],
            "arithmetic_or_branch_selection": [
                n
                for n in names
                if rows[n]["packet_classification"]
                == "arithmetic_or_branch_selection"
            ],
            "e2_status_label": rule["e2"]["status"],
        }
    return {
        "artifact": block["artifact"],
        "n_examples": block["n_examples"],
        "max_abs_deviation": block["max_abs_deviation"],
        "rule_as_stated_by_the_packet": cls["rule_as_stated_by_the_packet"],
        "classification_source": (
            "the packet's reading of each row's citation and note, carried "
            "by the coverage record as proposal_not_ratified; NOT a "
            "measurement. expected_over_base_pia and ratio_decimal_places "
            "are derived so a referee re-adjudicates each row"
        ),
        "n_published_percentage": len(published),
        "n_arithmetic_or_branch_selection": len(arithmetic),
        "examples": rows,
        "by_rule": by_rule,
        "all_agree_to_the_cent": all(
            r["agrees_to_the_cent"] for r in rows.values()
        ),
        "adjudication_note": cls["adjudication_note"],
    }


def precision_claim(coverage: dict[str, Any]) -> dict[str, Any]:
    ce = coverage["evidence_inventory"]["cross_engine"]
    disc = coverage["computes_exactly_definition_proposal"][
        "precision_disclosure"
    ]
    largest = max(
        disc["cross_engine_max_abs_diff_dollars"],
        disc["aux_worked_example_max_abs_deviation"],
        disc["pe_us_foundation_max_pia_abs_deviation"],
    )
    return {
        "claim": (
            '"computes exactly" means TO THE CENT: |oracle - independent '
            f"engine| <= {ce['agreement_tolerance_dollars']} dollars on every "
            "registered case (the bound runs/pia_cross_engine_v1.json "
            "commits as agreement_tolerance_dollars). NOT bit-exact."
        ),
        "agreement_tolerance_dollars": ce["agreement_tolerance_dollars"],
        "observed": disc,
        "largest_observed_dollar_deviation": largest,
        "largest_observed_is_within_the_bound": largest
        <= ce["agreement_tolerance_dollars"],
        "n_cross_engine_cases_exact_to_the_cent": ce["n_exact_to_cent"],
        "pe_us_residual_cause_quoted_not_verified": coverage[
            "evidence_inventory"
        ]["pe_us_pia_foundation"]["residual_note_is_quoted_not_verified"],
    }


def case_set_facts(coverage: dict[str, Any]) -> dict[str, Any]:
    ei = coverage["evidence_inventory"]
    ce = ei["cross_engine"]
    found = ei["pe_us_pia_foundation"]
    grids = ei["grids"]
    per_rule = {}
    for rule in coverage["rule_inventory"]:
        per_rule[rule["id"]] = {
            "cross_engine_cases": rule["cross_engine"]["n_cases"],
            "ssa_worked_examples": rule["ssa_worked_examples"],
            "pe_us_foundation_cases": rule["pe_us_foundation_cases"],
            "tests": rule["tests"],
        }
    return {
        "cross_engine": {
            "n_cases": ce["n_cases"],
            "eligibility_years": sorted(
                c["eligibility_year"] for c in ce["cohorts"].values()
            ),
            "birth_years": sorted(
                c["birth_year"] for c in ce["cohorts"].values()
            ),
            "history_span_ages": [22, 62],
            "n_distinct_shapes": ce["n_distinct_shapes"],
            "what_the_rows_cannot_show": ce["what_the_rows_cannot_show"],
        },
        "pe_us_foundation": {
            "n_cases": found["n_cases"],
            "aime_values": found["aime_values"],
            "claim_ages": found["claim_ages"],
            "birth_years": found["birth_years"],
        },
        "couple_grid": {
            k: grids["couple_grid"][k]
            for k in (
                "n_rows",
                "n_rows_with_worker_excess",
                "n_rows_with_spouse_excess",
                "n_rows_with_both_spouses_drawing_an_excess",
            )
        },
        "survivor_grid": {
            "n_rows": grids["survivor_grid"]["n_rows"],
            "distinct_own_deceased_pia_pairs": grids["survivor_grid"][
                "distinct_own_deceased_pia_pairs"
            ],
        },
        "per_rule": per_rule,
    }


def granularity_facts(coverage: dict[str, Any]) -> dict[str, Any]:
    bundled = {
        r["id"]: r.get("granularity_note")
        for r in coverage["rule_inventory"]
        if r.get("bundles_multiple_operations")
    }
    return {
        "n_rules": coverage["n_rules"],
        "cut": "the packet's sixteen rules (coverage does_not_establish[3])",
        "rules_flagged_as_bundling_several_statutory_operations": bundled,
        "also_bundling_per_the_packet": {
            "R12_402bc_402k3_spouse_benefit": "one-half of the worker's PIA AND the 402(k)(3)(A) dual-entitlement offset (two operations)"
        },
        "consequence": (
            "granularity fixes what a downstream citation may claim: a rule "
            "that bundles four operations earns or loses the status as a "
            "block; splitting R14 into base / RIB-LIM / DRC pass-through / "
            "dual entitlement (and R12 into half-PIA / offset) would let each "
            "operation carry its own E1 / E2 / E3 -- the coverage record "
            "carries no per-operation case sets, so the split partition "
            "cannot be derived from committed bytes here"
        ),
    }


def e1_clause(coverage: dict[str, Any]) -> dict[str, Any]:
    ce = coverage["evidence_inventory"]["cross_engine"]
    return {
        "clause": (
            f"E1 as committed {CROSS_ENGINE_COMMIT_DATE} at engine "
            f"{ce['engine_revision']} (commit {CROSS_ENGINE_COMMIT}, "
            "runs/pia_cross_engine_v1.json), not re-executed in this "
            "ceremony -- for the Axiom half (R1-R7)."
        ),
        "axiom_half": {
            "rules": [
                r["id"]
                for r in coverage["rule_inventory"]
                if r["cross_engine"]["n_cases"] > 0
            ],
            "engine_revision": ce["engine_revision"],
            "pe_us_revision_the_parameters_came_from": ce["pe_us_revision"],
            "re_executed_in_this_ceremony": False,
            "why": (
                "no host in the ceremony carried the maturin-built Axiom "
                "wheel (verification section 16: the pure-Python client has "
                "NativeCompiledDenseProgram None, so the tests' own "
                "_engine_available probe fails)"
            ),
        },
        "policyengine_us_half": {
            "rules": [
                r["id"]
                for r in coverage["rule_inventory"]
                if r["pe_us_foundation_cases"] > 0
            ],
            "re_executed_in_this_ceremony": True,
            **PE_US_HALF_REEXECUTED,
        },
        "coverage_record_statement": coverage["no_engine_executed"][
            "statement"
        ],
    }


# --------------------------------------------------------------------------
# P10 and P15 -- re-derived from the modules by ast / by read
# --------------------------------------------------------------------------
def family_maximum(coverage: dict[str, Any]) -> dict[str, Any]:
    fm = coverage["not_implemented"]["family_maximum_bites_here"]
    tree = ast.parse((ROOT / HOUSEHOLD_REL).read_text())
    spans: dict[str, tuple[int, int]] = {}
    total_span = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "CoupleBenefit":
            spans["CoupleBenefit"] = (node.lineno, node.end_lineno)
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "total":
                    total_span = (item.lineno, item.end_lineno)
        if isinstance(node, ast.FunctionDef) and node.name == "couple_benefit":
            spans["couple_benefit"] = (node.lineno, node.end_lineno)
    if total_span is None or "CoupleBenefit" not in spans:
        raise RuntimeError("CoupleBenefit.total not found by ast")
    cs = fm["consumer_symbols"]
    expected = {
        "CoupleBenefit": (cs["class"]["first_line"], cs["class"]["last_line"]),
        "total": (
            cs["summation_property"]["first_line"],
            cs["summation_property"]["last_line"],
        ),
        "couple_benefit": (
            cs["function"]["first_line"],
            cs["function"]["last_line"],
        ),
    }
    derived = {
        "CoupleBenefit": spans["CoupleBenefit"],
        "total": total_span,
        "couple_benefit": spans["couple_benefit"],
    }
    if derived != expected:
        raise RuntimeError(f"consumer spans differ: {derived} != {expected}")
    plural_defined = any(
        isinstance(n, (ast.ClassDef, ast.FunctionDef))
        and n.name in ("CoupleBenefits", "couple_benefits")
        for n in ast.walk(tree)
    )
    searches = coverage["not_implemented"]["searches"]["family_maximum"]
    return {
        "P10": (
            "the family maximum (the cap on total benefits payable on one "
            "earnings record) is NOT IMPLEMENTED; spousal_benefit and "
            "widow_benefit return uncapped amounts and the household "
            "consumer sums both own benefits and both excess spousal "
            "amounts with no cap"
        ),
        "consumer": {
            "module": HOUSEHOLD_REL,
            "qualified_summation_symbol": "CoupleBenefit.total",
            "class_lines": list(derived["CoupleBenefit"]),
            "total_property_lines": list(derived["total"]),
            "couple_benefit_function_lines": list(derived["couple_benefit"]),
            "derived_by": "ast over the pinned module at build time; equal to the coverage record's consumer_symbols",
            "plural_name_defined_anywhere_in_the_module": plural_defined,
            "packet_name_couple_benefits_exists": cs["packet_name_exists"],
            "v1_artifact_name_CoupleBenefits_exists": cs[
                "name_the_v1_artifact_used_exists"
            ],
        },
        "auxiliary_functions_returning_uncapped_amounts": fm["symbols"],
        "search": {
            "root": searches["search_root"],
            "patterns": searches["patterns"],
            "n_files_searched": searches["n_files_searched"],
            "hits": searches["hits"],
            "absent": searches["absent"],
        },
        "where_it_bites": (
            "precisely where auxiliary benefits stack; no committed case "
            "stacks enough on one record for the cap to bind, so the "
            "omission is an UNCAUGHT class, recorded as such and never as bite"
        ),
    }


def frozen_scope(coverage: dict[str, Any]) -> dict[str, Any]:
    text = (ROOT / SS_INIT_REL).read_text()
    key_sentence = "Do not extend this module's rule coverage; extend the Axiom encodings."
    if key_sentence not in normalized(text):
        raise RuntimeError("frozen-scope sentence not found in ss/__init__.py")
    return {
        "P15": coverage["frozen_scope"]["quote"],
        "source": SS_INIT_REL,
        "key_sentence": key_sentence,
        "key_sentence_present_in_module": True,
        "consequence": coverage["frozen_scope"]["consequence"],
        "clause": (
            "a PASS certifies a FROZEN reference oracle. Extending the "
            "module's rule coverage to clear a gap is FORBIDDEN by the "
            "module's own docstring, so a missing rule is closed in Axiom "
            "(rulespec-us us/statutes/42/415, 402, 416) and re-certified "
            "here as a cross-engine case, never by growing this module; a "
            "rule that fails is fixed in Axiom, not here."
        ),
    }


def known_gaps(coverage: dict[str, Any]) -> dict[str, Any]:
    """The coverage record's five gaps, restated (its ids kept as
    pointers; the record's own sentences are not copied verbatim)."""
    ids = [g["id"] for g in coverage["known_gaps"]]
    facts = case_set_facts(coverage)
    return {
        "coverage_record_ids": ids,
        "r3_computation_year_count_is_degenerate": (
            "the oracle hard-codes 35 and the engine derives n; every "
            "committed case has elapsed - 5 = 35 for both cohorts, so no "
            "case separates the constant from the derived value. Exact "
            "domain: retirement workers attaining 62 in 1991 or later. A "
            "live caller reaches outside it: widow_benefit takes "
            "deceased_pia from the caller, and a deceased worker's PIA "
            "computed through aime() gets a 35-year divisor it should not."
        ),
        "r4_zero_pad_branch_unexercised": (
            "every committed worker history has 41 entries, so the "
            "short-history zero pad of aime() is a no-op in every case and "
            "in every test under tests/ss/ (derived by ast in the coverage "
            "record)"
        ),
        "r8_r16_absent_from_the_240": (
            "the cross-engine rows carry aime and pia only; every rule from "
            "402(q) onward rests on the 40-case policyengine-us foundation "
            f"block (AIME {facts['pe_us_foundation']['aime_values']}, claim ages "
            f"{facts['pe_us_foundation']['claim_ages']}, birth years "
            f"{facts['pe_us_foundation']['birth_years']}) and the ten worked examples"
        ),
        "r11_r15_no_second_engine": (
            "policyengine-us has no spousal or survivor computation, so E1 "
            "is unsatisfiable for the auxiliary rules today -- structural, "
            "not incidental; what would satisfy it is the Axiom rulespec-us "
            "us/statutes/42/402 encodings"
        ),
        "r12_r14_grid_thinness": (
            f"the couple grid has {facts['couple_grid']['n_rows']} rows and "
            f"{facts['couple_grid']['n_rows_with_both_spouses_drawing_an_excess']} "
            "with both spouses drawing an excess; the survivor grid sits at "
            f"{len(facts['survivor_grid']['distinct_own_deceased_pia_pairs'])} "
            "(own, deceased) PIA pair; no worked example has own_pia above "
            "zero, so the 402(k) dual-entitlement maximum is never checked "
            "against a published figure"
        ),
    }


# --------------------------------------------------------------------------
# gates.yaml citations (derived by search on the pinned blob)
# --------------------------------------------------------------------------
def gates_yaml_citations() -> dict[str, Any]:
    raw = _pinned_gates_yaml()
    lines = raw.decode("utf-8").split("\n")

    def line_of(token: str, expected: int | None = None) -> int:
        hits = [i + 1 for i, line in enumerate(lines) if token in line]
        if expected is not None:
            if expected not in hits:
                raise RuntimeError(f"gates.yaml:{expected} lacks {token!r}")
            return expected
        if len(hits) != 1:
            raise RuntimeError(f"{token!r} occurs {len(hits)} times, not once")
        return hits[0]

    computes = [
        i + 1 for i, line in enumerate(lines) if "computes exactly" in line
    ]
    standing = [
        i + 1
        for i, line in enumerate(lines)
        if "description_claims_exactly_the_scored_surface" in line
    ]
    return {
        "git_blob_sha1": GATES_YAML_BLOB_AT_BINDING,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "byte_identical_to_working_tree": raw
        == (ROOT / GATES_REL).read_bytes(),
        "computes_exactly": {
            "occurrences": computes,
            "n_occurrences": len(computes),
            "line_text": lines[computes[0] - 1].strip() if computes else None,
        },
        "standing_rule_lines": standing,
        "line_citations": {
            "no_self_rescue": line_of("no_self_rescue: >-", 565),
            "gate_2_n_gated_cells": line_of("n_gated_cells: 46", 917),
            "gate_2_own_record_outside_2a_2b_2c": line_of(
                "OUTSIDE 2a / 2b / 2c", 782
            ),
            "gate_2_spousal_survivor_levels_need_2c": line_of(
                "spousal / survivor benefit LEVELS in GENERATED panels", 777
            ),
            "gate_m4_faithful_candidate_oc": line_of(
                "faithful_candidate_oc:", 3206
            ),
            "gate_w1_tolerance_rule": line_of("tolerance_rule: >-", 4350),
            "sampling_floor_protocol": line_of("noise_floor:", 19),
        },
        "gate_b2_pia_oracle_present": "gate_b2_pia_oracle"
        in raw.decode("utf-8"),
        "gate_b2_claiming_present": "gate_b2_claiming" in raw.decode("utf-8"),
        "artifact_named": ARTIFACT_REL in raw.decode("utf-8"),
        "coverage_named": SOURCE_COVERAGE_REL in raw.decode("utf-8"),
        "pin_semantics": (
            "PROVENANCE of the line citations only; NOT a freeze of the live "
            "file. The coverage record's own citation is blob-pinned the "
            "same way and survives the gate commit; the two live-file 'gate "
            "name absent' tests do not."
        ),
    }


# --------------------------------------------------------------------------
# Certification scope (P14) and the rulings
# --------------------------------------------------------------------------
def certification_scope(parts: dict[str, Any]) -> dict[str, Any]:
    strict = parts["strict"]
    return {
        "tranche": "b2_statutory_benefit_oracle",
        "headline": (
            "if ratified, a PASS certifies PER RULE, over exactly the "
            "registered case set and exactly the domain named in "
            "named_constants, that the oracle's value agrees to the cent "
            "with an independent execution (E1), matches an SSA-published "
            "figure on at least one case (E2) and exercises every branch "
            "(E3). The gate-level verdict is the PARTITION, never one "
            "boolean; a downstream citation names the RULE, never the gate."
        ),
        "partition_under_the_strict_reading": {
            "all_three": strict["all_three"],
            "strict_subset": strict["strict_subset"],
            "none": strict["none"],
        },
        "supports": [
            "the #74 SF (statutory formula) component wherever a rule holds "
            "all three conditions -- with the CITATION being the rule",
            "gate_1's benefit_space block (the PIA-proxy functional): a "
            "certified R5 / R6 / R7 is what makes that proxy a statutory "
            "object rather than a formula",
        ],
        "does_not_authorise_P14": [
            "any household benefit TOTAL: without the family maximum, "
            "stacked auxiliary benefits on one earnings record are UNCAPPED "
            "(CoupleBenefit.total, household.py)",
            "any survivor or disability PIA computed through aime(): R3's "
            "constant is outside its exact domain there",
            "spousal or survivor benefit LEVELS in GENERATED panels: those "
            "need gate_2c (gates.yaml:772-783) as well as this gate",
            "any benefit in nominal post-entitlement dollars: no COLA is "
            "applied anywhere in ss/",
            "anything listed in not_implemented (WEP / GPO, the retirement "
            "earnings test, the special minimum PIA, child's and parent's "
            "benefits, the disability PIA, recomputation)",
            "any statement about a rule finer than the sixteen-rule cut "
            "(P13): R12 and R14 earn or lose the status as blocks",
            "any rule that holds a strict subset or none of E1 / E2 / E3: "
            "the partition names it and the status is NOT awarded",
            "the claiming-age distribution, which is gate_b2_claiming's",
        ],
    }


def open_questions(
    parts: dict[str, Any],
    facts: dict[str, Any],
    gran: dict[str, Any],
    clause: dict[str, Any],
) -> list[dict[str, Any]]:
    strict = parts["strict"]
    alts = parts["alternatives"]
    return [
        {
            "id": "P1",
            "name": "is_exact_agreement_a_gate",
            "question": (
                "every locked gate prices a tolerance against measured "
                "noise; this one has none. Accept kind "
                "exact_agreement_per_rule as a gate kind, or strike the "
                'clause \'benefit formulas earn per-rule "computes exactly" '
                "status' from gates.yaml:642 by amendment instead."
            ),
            "options": {
                "a_accept_the_gate_kind": {
                    "what_it_does": (
                        "the standing rule is discharged by DEFINING the "
                        "status (E1 + E2 + E3, X1 + X2, to the cent) and "
                        "awarding it per rule; the partition under the "
                        "strict reading is the first award"
                    ),
                    "priced": {
                        "rules_awarded_under_the_strict_reading": strict[
                            "all_three"
                        ],
                        "n_strict_subset": strict["n_strict_subset"],
                        "n_none": strict["n_none"],
                    },
                },
                "b_strike_gates_yaml_642_by_amendment": {
                    "what_it_does": (
                        "gate_2.description drops the clause; no status is "
                        "defined or awarded; the coverage record and this "
                        "artifact stay REPORTED; the tests in tests/ss/ "
                        "remain the only thing that executes either engine"
                    ),
                    "priced": (
                        "a gate_2 metadata-only amendment with its own "
                        "ceremony; nothing in this block lands; the standing "
                        "rule is discharged the other way"
                    ),
                },
            },
            "the_one_outcome_the_standing_rule_forbids": (
                "leaving the clause undefined and unawarded in "
                "gate_2.description while gate_2's 46 cells (gates.yaml:917) "
                "gate no benefit-formula cell and its own certification_scope "
                "puts own-record benefit levels OUTSIDE 2a / 2b / 2c (:782)"
            ),
            "placeholder_in_block": "<RULING P1 gate_kind>",
            "status": "FILED and PRICED; not ruled (decide first: the packet's section 11 step 2)",
        },
        {
            "id": "P6",
            "name": "e1_unsatisfiable_for_r11_r15",
            "question": (
                "no second engine exists for the auxiliary rules, by "
                "construction. Waive E1 per rule (the waiver named per "
                "rule), or split the gate and hold the auxiliary half until "
                "the Axiom 402 encodings land?"
            ),
            "options": {
                "a_per_rule_e1_waiver": {
                    "partition": {
                        "all_three": alts["p6_e1_waiver_for_r11_r15"][
                            "all_three"
                        ],
                        "strict_subset": alts["p6_e1_waiver_for_r11_r15"][
                            "strict_subset"
                        ],
                        "none": alts["p6_e1_waiver_for_r11_r15"]["none"],
                    },
                    "moves_vs_strict": alts["p6_e1_waiver_for_r11_r15"][
                        "moves_vs_strict"
                    ],
                    "reading": (
                        "no auxiliary rule reaches all three even with E1 "
                        "waived: each still fails E3 (partial case sets) or "
                        "E2 (partial / absent), so the waiver moves class "
                        "labels, not the awarded set"
                    ),
                },
                "b_split_the_gate_and_hold_the_auxiliary_half": {
                    "partition_of_the_own_benefit_half": {
                        "rules": [
                            r
                            for r in strict["per_rule"]
                            if r not in AUXILIARY_RULES
                        ],
                        "all_three": [
                            r
                            for r in strict["all_three"]
                            if r not in AUXILIARY_RULES
                        ],
                    },
                    "held_rules": list(AUXILIARY_RULES),
                    "what_would_release_them": (
                        "the Axiom rulespec-us us/statutes/42/402 encodings "
                        "executing the registered auxiliary cases, committed "
                        "as a cross-engine artifact with its own bound"
                    ),
                },
            },
            "placeholder_in_block": "<RULING P6 e1_waiver>",
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "P8",
            "name": "case_set_sufficiency",
            "question": (
                "two eligibility years, two birth cohorts, four claim ages, "
                "one (own, deceased) survivor pair, zero couple rows with "
                "both spouses drawing an excess: is that the registered "
                "case set, or must the ceremony build a wider one first?"
            ),
            "facts": {
                "cross_engine": facts["cross_engine"],
                "pe_us_foundation": facts["pe_us_foundation"],
                "couple_grid": facts["couple_grid"],
                "survivor_grid": facts["survivor_grid"],
            },
            "priced": {
                "what_a_wider_set_could_move": {
                    "E3_partial_from_sampling": [
                        rid
                        for rid, e in strict["per_rule"].items()
                        if "E3" in e["failing_conditions"]
                        and e["status_labels"]["e3"].startswith("partial")
                    ],
                    "E3_branch_unexercised_reachable_with_short_histories": [
                        "R4_415b_top_n_divide_and_floor"
                    ],
                    "R3_would_be_SEPARATED_not_satisfied": (
                        "a worker with fewer than 40 elapsed years gives the "
                        "engine a derived n below 35 while the oracle keeps "
                        "35; a wider set converts R3's degenerate agreement "
                        "into an E1 DISAGREEMENT outside the exact domain, "
                        "which is the honest result"
                    ),
                },
                "what_a_wider_set_cannot_move": {
                    "E1_for_the_auxiliary_rules": list(AUXILIARY_RULES),
                    "why": "no second engine; see P6",
                },
                "cost": (
                    "the machinery is committed "
                    "(scripts/build_cross_engine_pia_artifact.py, "
                    "scripts/build_aux_benefit_examples.py); a rebuilt "
                    "artifact needs the Axiom wheel for the 240-side and a "
                    "policyengine-us Python for the foundation side, neither "
                    "of which the ceremony's hosts had for the Axiom half"
                ),
            },
            "placeholder_in_block": "<RULING P8 case_set>",
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "P9",
            "name": "survivor_reduction_period",
            "question": (
                "is the survivor reduction period certifiable at the shipped "
                "constant 84 months? The 81-percent-at-62 worked example "
                "reproduces SSA only by overriding "
                "survivor_reduction_period_months to 72 in its own inputs."
            ),
            "options": {
                "a_constant_override_does_not_satisfy_e2": {
                    "R13_class": strict["per_rule"][
                        "R13_402q_survivor_reduction_ramp"
                    ]["class"],
                    "R13_failing": strict["per_rule"][
                        "R13_402q_survivor_reduction_ramp"
                    ]["failing_conditions"],
                },
                "b_override_counts_as_e2_with_the_domain_named": {
                    "R13_class": alts["p9_constant_override_counts_as_e2"][
                        "per_rule"
                    ]["R13_402q_survivor_reduction_ramp"]["class"],
                    "R13_failing": alts["p9_constant_override_counts_as_e2"][
                        "per_rule"
                    ]["R13_402q_survivor_reduction_ramp"][
                        "failing_conditions"
                    ],
                    "moves_vs_strict": alts[
                        "p9_constant_override_counts_as_e2"
                    ]["moves_vs_strict"],
                },
                "c_add_a_survivor_fra_schedule": (
                    "FORBIDDEN by the frozen-scope clause (P15): the fix "
                    "lands in Axiom, not in this module"
                ),
            },
            "named_constant": "survivor_reduction_period_months = 84 (exact for survivor cohorts born 1962 or later); X2 of the definition",
            "placeholder_in_block": "<RULING P9 survivor_period>",
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "P13",
            "name": "rule_granularity",
            "question": (
                "sixteen rules is the packet's cut; R14 bundles four "
                "statutory operations and R12 two. Granularity fixes what a "
                "downstream citation may claim."
            ),
            "facts": gran,
            "priced": (
                "keeping the cut: R12 and R14 are awarded or withheld as "
                "blocks (both hold a strict subset under every reading "
                "here). Splitting: each operation carries its own "
                "conditions, which the coverage record cannot derive from "
                "committed bytes (no per-operation case sets), so a split "
                "needs a v2 coverage build before any status is awarded at "
                "the finer grain"
            ),
            "placeholder_in_block": "<RULING P13 granularity>",
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "S7",
            "name": "sequencing_constraint",
            "question": (
                "the two live-file 'gate name absent' tests fail the moment "
                "gate_b2_claiming or gate_b2_pia_oracle lands "
                "(tests/test_pia_rule_coverage.py::"
                "test_no_gate_b2_pia_oracle_exists_in_gates_yaml, "
                "tests/test_claiming_publication_floor.py::"
                "test_no_gate_b2_claiming_exists_in_gates_yaml); the "
                "coverage record's blob-pinned citation survives the commit"
            ),
            "constraint": (
                "the lock commit retires those two assertions and flips the "
                "pre-lock markers in the SAME commit (flip_plan), or "
                "supersedes the artifacts with a v2 in the same PR"
            ),
            "placeholder_in_block": "ceremony_notes.flip_plan",
            "status": "RECORDED as a sequencing constraint; not a threshold ruling",
        },
        {
            "id": "S8",
            "name": "e1_clause",
            "question": "the E1 status of every rule rests on the committed cross-engine artifact",
            "clause": clause["clause"],
            "policyengine_us_half": clause["policyengine_us_half"],
            "placeholder_in_block": "<RULING S8 e1_clause>",
            "status": "CLAUSE CARRIED; the Axiom half not re-executed by anyone in this ceremony",
        },
    ]


def flip_plan() -> dict[str, Any]:
    return {
        "rule": (
            f"the commit that inserts the {GATE_NAME} block into gates.yaml "
            f"(under `gates:`, a NEW top-level key) flips {MARKER} from "
            "False to True in EVERY file that carries it, IN THE SAME "
            "COMMIT, retires "
            "tests/test_pia_rule_coverage.py::"
            "test_no_gate_b2_pia_oracle_exists_in_gates_yaml in that commit, "
            "admits the new key at every master-compare site, and changes "
            "nothing else in those files"
        ),
        "marker": MARKER,
        "files_carrying_the_marker": [
            "tests/test_gates_derivations.py",
            "tests/test_pia_gate_partition_v1.py",
        ],
        "live_file_tests_the_flip_retires": [
            "tests/test_pia_rule_coverage.py::"
            "test_no_gate_b2_pia_oracle_exists_in_gates_yaml",
            "tests/test_claiming_publication_floor.py::"
            "test_no_gate_b2_claiming_exists_in_gates_yaml (if the claiming "
            "block lands in the same PR; otherwise its own flip retires it)",
        ],
        "tests_that_survive_the_flip_unchanged": [
            "tests/test_pia_rule_coverage.py::"
            "test_computes_exactly_citation_is_blob_pinned_and_rescans_from_the_blob "
            "(reads the pinned blob from the object store once the working "
            "tree moves on; verification section 11 simulation C)"
        ],
        "master_compare_sites_that_must_admit_the_new_key": [
            "tests/test_gates_derivations.py::"
            "test_gate_m4_flip_leaves_locked_siblings_byte_identical",
            "tests/test_gate_w1_derivations.py (the `added in (...)` assert)",
            "tests/test_gate_m6_derivations.py (the sole-new-key assert)",
        ],
        "what_flips_with_it": [
            "tests/test_gates_derivations.py: _gate_b2_pia_oracle_block() "
            "reads the LIVE gates.yaml block instead of the artifact's draft "
            "fragment (LOCKED-HOT); the pre-lock guard inverts",
            "gates.yaml: floor_run_sha256 replaces <FILLED AT RATIFICATION> "
            f"with the sha256 of {ARTIFACT_REL} AS RATIFIED; every "
            "<RULING ...> placeholder is replaced; status -> locked; "
            "locked -> true; a history entry is added",
            "tests/tier_counts.json and tests/README-tiers.md re-refreshed "
            "by LIVE collection",
        ],
    }


# --------------------------------------------------------------------------
# The DRAFT block
# --------------------------------------------------------------------------
def draft_fragment(
    coverage: dict[str, Any],
    parts: dict[str, Any],
    examples: dict[str, Any],
    precision: dict[str, Any],
    facts: dict[str, Any],
    clause: dict[str, Any],
    fm: dict[str, Any],
    frozen: dict[str, Any],
    gaps: dict[str, Any],
    scope: dict[str, Any],
    citations: dict[str, Any],
) -> str:
    strict = parts["strict"]
    alts = parts["alternatives"]
    ce = coverage["evidence_inventory"]["cross_engine"]
    nc = coverage["named_constants"]
    disc = precision["observed"]
    dne = coverage["does_not_establish"]
    cons = fm["consumer"]

    def code_span(rule: dict[str, Any]) -> str:
        spans = []
        for c in rule["code"]:
            module = c["module"].replace("src/populace_dynamics/", "")
            spans.append(f"{module}:{c['first_line']}-{c['last_line']}")
        return ", ".join(spans)

    rule_lines = []
    for rule in coverage["rule_inventory"]:
        rid = rule["id"]
        e = strict["per_rule"][rid]
        moves = []
        for name, alt in alts.items():
            if name == "packet_proposed_verdicts":
                continue
            if rid in alt["moves_vs_strict"]:
                moves.append(name)
        ruling = ""
        if rid in AUXILIARY_RULES:
            ruling += " <RULING P6 e1_waiver>"
        if rid == "R13_402q_survivor_reduction_ramp":
            ruling += " <RULING P9 survivor_period>"
        if rule.get("bundles_multiple_operations") or rid.startswith("R12"):
            ruling += " <RULING P13 granularity>"
        rule_lines.append(
            f"        {rid}:\n"
            f'          code: "{code_span(rule)}"\n'
            f'          e1: {e["status_labels"]["e1"]}\n'
            f'          e2: {e["status_labels"]["e2"]}\n'
            f'          e3: {e["status_labels"]["e3"]}\n'
            f'          cases: {{ cross_engine: {rule["cross_engine"]["n_cases"]}, '
            f'pe_us_foundation: {rule["pe_us_foundation_cases"]}, '
            f'ssa_worked_examples: {len(rule["ssa_worked_examples"])} }}\n'
            f'          strict_reading: {{ class: {e["class"]}, failing: [{", ".join(e["failing_conditions"])}] }}\n'
            f'          moved_by_an_alternative_reading: [{", ".join(moves)}]\n'
            f'          packet_proposed_verdict: {rule["packet_proposed_verdict"]["verdict"]}   # quoted, NOT adopted\n'
            f'          rulings: "{ruling.strip() or "none"}"'
        )
    rules_text = "\n".join(rule_lines)
    dne_lines = "\n".join(
        "          - >-\n            " + normalized(line) for line in dne
    )
    subset_lines = "\n".join(
        f'            {rid}: [{", ".join(fails)}]'
        for rid, fails in strict["strict_subset"].items()
    )
    ex_lines = "\n".join(
        f'          {name}: {{ group: {ex["group"]}, expected_over_base_pia: {ex["expected_over_base_pia"]}, '
        f'classification: {ex["packet_classification"]} }}'
        for name, ex in examples["examples"].items()
    )
    cite = citations["line_citations"]

    text = f"""  gate_b2_pia_oracle:
    # DRAFT -- NOT APPLIED TO gates.yaml. Emitted by
    # scripts/build_pia_gate_partition_v1.py into
    # runs/pia_gate_partition_v1.json (draft_gates_yaml_fragment.text) at
    # the threshold-binding sitting of 2026-09-08 (the prerequisite of the
    # packet's PIA ceremony step 5). Every status label below is READ from
    # the VERIFIED coverage record runs/pia_rule_coverage_v1.json
    # ({SOURCE_COVERAGE_COMMITTED[0]:,} B, sha256 {SOURCE_COVERAGE_COMMITTED[1][:16]}...) and the partition is
    # DERIVED from those labels under the explicit mapping in
    # thresholds.statistic; bound by tests/test_gates_derivations.py (the
    # test_gate_b2_pia_oracle_* bindings). Nothing is typed, nothing is
    # awarded. Every "<RULING ...>" placeholder is an open question the
    # ratifying round must fill; options and prices are in the artifact's
    # open_questions_for_the_ceremony. This block also proposes the FIRST
    # definition of gates.yaml:{citations['computes_exactly']['occurrences'][0]}'s phrase "computes exactly".
    id: b2_statutory_benefit_oracle
    status: draft_pending_referee_round
    locked: false
    kind: exact_agreement_per_rule   # <RULING P1 gate_kind>
    derived_from_coverage: {SOURCE_COVERAGE_REL}
    derived_from_coverage_sha256: {SOURCE_COVERAGE_COMMITTED[1]}
    derived_from_coverage_size_bytes: {SOURCE_COVERAGE_COMMITTED[0]}
    floor_run: {ARTIFACT_REL}
    floor_run_sha256: <FILLED AT RATIFICATION>
    covers: >-
      the STATUTORY BENEFIT ORACLE (#74 component SF): the sixteen
      enumerated rules of populace_dynamics.ss.benefits and
      populace_dynamics.ss.params listed in rule_inventory, over EXACTLY
      their registered case sets. The gate is EXACT-AGREEMENT, not
      floor-priced: the quantities are statutory arithmetic over pinned
      parameters, so the null is agreement TO THE CENT and there is no
      noise floor to derive. It DEFINES the phrase "computes exactly"
      (gates.yaml:{citations['computes_exactly']['occurrences'][0]}, gate_2.description -- its only occurrence in
      the file, and undefined there) and awards it PER RULE as a
      PARTITION: under the strict reading {strict['n_all_three']} rule holds all three
      conditions ({', '.join(strict['all_three'])}), {strict['n_strict_subset']} hold a strict subset and
      {strict['n_none']} hold none. It certifies a FROZEN-SCOPE REFERENCE ORACLE, NOT a
      benefit calculator: the rules in not_implemented are absent by design
      and are published as absent. It does not authorise any household
      benefit total, any survivor or disability PIA through aime(), any
      spousal or survivor LEVEL in a generated panel, or any nominal
      post-entitlement dollar.
    holdout_basis: []
    holdout_basis_note: >-
      DELIBERATELY EMPTY. A statutory formula has no population to hold
      out: it is a deterministic function of statute and parameters. Its
      null is agreement with an INDEPENDENT EXECUTION plus agreement with
      an SSA-PUBLISHED figure -- not a person-disjoint split (gate 1 / 2a /
      2b / 2c / m4; the sampling-floor protocol at gates.yaml:{cite['sampling_floor_protocol']}) and not a
      vintage-priced deviation (gate_w1 family B, :{cite['gate_w1_tolerance_rule']}). The round accepts or
      rejects this structural claim first (<RULING P1 gate_kind>).
    external_basis:
      - axiom_rules_engine (independent Rust implementation; engine_revision {ce['engine_revision']}, runs/pia_cross_engine_v1.json)
      - policyengine_us Simulation (independent Python implementation of the own-benefit path only; pe_us_revision {ce['pe_us_revision']})
      - ssa_published_figures (bend-point determinations; 402(q)/(w) percentages; RS 00615.020 / .301 / .302 / .310 spousal and survivor percentages, cited per row in runs/aux_benefit_examples_v1.json)
    data_staged: >-
      runs/pia_cross_engine_v1.json ({ce['n_cases']} cases, committed, test-pinned by
      tests/ss/test_cross_engine.py) and runs/aux_benefit_examples_v1.json
      (10 SSA worked examples + 40 policyengine-us foundation cases + a
      36-row couple grid + a 9-row survivor grid, committed, test-pinned by
      tests/ss/test_aux_benefits.py). The per-rule coverage record
      {SOURCE_COVERAGE_REL} EXISTS (floors v2 at cd8f167,
      independently verified) and the gate-schema artifact
      {ARTIFACT_REL} derives this block from it.
    lock_ceremony:
      exists: false
      required: >-
        coverage record -> adversarial referees -> fixes -> verification ->
        THRESHOLD BINDING (this block) -> P1 decided first -> adversarial
        referee round -> fixes -> verification -> ratifying merge, which
        fills every placeholder, sets floor_run_sha256, flips
        GATE_B2_PIA_ORACLE_BLOCK_LANDED and retires the live-file guard
        test in the same commit. NOT YET RUN past the binding.
    thresholds:
      locked: false
      status: draft_pending_referee_round
      tranche_id: b2_statutory_benefit_oracle
      kind: exact_agreement_per_rule
      coverage_run: {SOURCE_COVERAGE_REL}
      coverage_run_sha256: {SOURCE_COVERAGE_COMMITTED[1]}
      floor_run: {ARTIFACT_REL}
      floor_run_sha256: <FILLED AT RATIFICATION>
      evidence_runs:
        - {{ path: runs/pia_cross_engine_v1.json, sha256: {coverage['sources']['evidence_artifacts'][0]['sha256']} }}
        - {{ path: runs/aux_benefit_examples_v1.json, sha256: {coverage['sources']['evidence_artifacts'][1]['sha256']} }}
      e1_clause: "<RULING S8 e1_clause>"
      e1_clause_as_carried: >-
        {clause['clause']} The policyengine-us half (R8 / R9 / R10 / R16
        through the 40-case foundation block) WAS re-executed in this
        ceremony by the floors v2 verification
        (test_pe_us_simulation_matches_oracle_foundation_live, {clause['policyengine_us_half']['cases']}
        foundation cases, policyengine-us checkout {clause['policyengine_us_half']['policyengine_us_checkout']}, PASSED). The
        Axiom half (R1-R7 on the 240) was NOT: no ceremony host carried the
        maturin-built wheel. Any E1 status below rests on the committed
        artifact as built on its recorded date.
      estimand: >-
        Per RULE (one statutory operation with its own citation and branch
        structure), the value the oracle computes for every registered case
        of that rule. Per the standing rule
        description_claims_exactly_the_scored_surface (gates.yaml:1056,
        :3294, :4869) the surface claimed is EXACTLY the sixteen rules of
        rule_inventory over their registered case sets -- NOT the OASDI
        benefit, NOT any rule in not_implemented, NOT any quantity computed
        from a constant outside the domain named in named_constants, and
        NOT any operation finer than the sixteen-rule cut (<RULING P13 granularity>).
      statistic: >-
        Per rule, THREE conditions, all required -- the definition of
        "computes exactly" (P2):
        E1 INDEPENDENT RE-EXECUTION -- |our_value - independent_engine_value|
           <= {ce['agreement_tolerance_dollars']} dollars (TO THE CENT) on EVERY registered case, the bound
           committed as runs/pia_cross_engine_v1.json.agreement_tolerance_dollars;
           labels that hold: satisfied, policyengine_us_only; labels that do
           not: degenerate, unsatisfiable_today (<RULING P6 e1_waiver>).
        E2 EXTERNAL ANCHOR -- at least one registered case whose expected
           value is an SSA-PUBLISHED figure, not a value recomputed from the
           same formula; label that holds: satisfied; labels that do not:
           satisfied_with_a_constant_override (<RULING P9 survivor_period>),
           weak, partial, implied, absent.
        E3 EXERCISED BRANCHES AND BOUNDARIES -- every branch and boundary of
           the rule as written is hit by at least one registered case, the
           case set committed cell by cell; labels that hold:
           all_branches_exercised, exhaustive, both_branches_reached; labels
           that do not: partial (any form), branch_unexercised, unexercised,
           unit_test_only.
        X1 NAMED NON-COVERAGE and X2 NAMED CONSTANTS are published below so
        the status can never be read as "computes everything".
        PRECISION (P11): NOT bit-exactness. Observed: cross-engine max
        |diff| {disc['cross_engine_max_abs_diff_dollars']} dollars on {ce['n_cases']}; aux worked-example max deviation
        {disc['aux_worked_example_max_abs_deviation']}; policyengine-us foundation max PIA deviation
        {disc['pe_us_foundation_max_pia_abs_deviation']} dollars and max factor deviation
        {disc['pe_us_foundation_max_factor_abs_deviation']} (float32 storage, the artifact's own note, quoted not
        verified). "Exactly" means TO THE CENT and the block says so.
        E1 alone is AGREEMENT, not correctness: two engines fed the same
        parameters can agree on the same mistake; E2 is what makes it a
        claim about the statute.
      protocol:
        deterministic: true
        seeds: none
        case_registration: >-
          A candidate registers, BEFORE scoring, the case set per rule and
          the independent engine revision. Case sets are committed in the
          coverage record per rule with every input and both engines'
          outputs, so a referee re-derives rather than trusts.
        pass_rule: >-
          The gate does NOT produce one boolean over all rules. It awards
          computes_exactly PER RULE, and the gate-level verdict is the
          PARTITION: which rules hold E1+E2+E3, which hold a strict subset
          (and which condition fails), and which are not implemented. A
          partition that changes -- a rule losing a condition -- is a FAIL
          for that rule and must be published as such. Any downstream
          artifact citing the oracle must cite the RULE, never the gate.
      no_floor:
        rationale: >-
          There is no noise floor and none is derived. Statutory arithmetic
          over pinned parameters is deterministic; the only dispersion is
          floating-point representation, which is BOUNDED, not sampled. The
          gate-1 / gate-2 / m4 half-split construction and the gate_w1
          vintage-priced tolerance rule are both INAPPLICABLE and are named
          so no referee has to ask; the gate_m4 faithful_candidate_oc
          (gates.yaml:{cite['gate_m4_faithful_candidate_oc']}) has no analogue here.
        floating_point_disclosure:
          cross_engine_max_abs_diff_dollars: {disc['cross_engine_max_abs_diff_dollars']}
          aux_worked_example_max_abs_deviation: {disc['aux_worked_example_max_abs_deviation']}
          pe_us_foundation_max_pia_abs_deviation: {disc['pe_us_foundation_max_pia_abs_deviation']}
          pe_us_foundation_max_factor_abs_deviation: {disc['pe_us_foundation_max_factor_abs_deviation']}
          agreement_tolerance_dollars: {ce['agreement_tolerance_dollars']}
      rule_inventory:
        # Sixteen rules. Every e1 / e2 / e3 value is the coverage record's
        # status LABEL (the builder's reading of derived evidence, disclosed
        # as such in status_provenance); strict_reading is the class under
        # the mapping in statistic; moved_by_an_alternative_reading names
        # the filed readings that change the class. NOTHING here is awarded.
{rules_text}
      partition:
        strict_reading:
          all_three: [{', '.join(strict['all_three'])}]
          strict_subset:
{subset_lines}
          none: [{', '.join(strict['none'])}]
        invariant_under_every_filed_reading:
          all_three: [{', '.join(parts['invariant_under_every_reading']['rules_holding_all_three_under_every_variant'])}]
          none: [{', '.join(parts['invariant_under_every_reading']['rules_holding_none_under_every_variant'])}]
        alternative_readings: >-
          axiom_only_e1 (policyengine_us_only does not count): all-three
          [{', '.join(alts['axiom_only_e1']['all_three'])}]; p6_e1_waiver_for_r11_r15: all-three
          [{', '.join(alts['p6_e1_waiver_for_r11_r15']['all_three'])}]; p9_constant_override_counts_as_e2:
          all-three [{', '.join(alts['p9_constant_override_counts_as_e2']['all_three'])}]; the packet's own
          proposed verdicts call {len(alts['packet_proposed_verdicts']['rules_the_packet_calls_computes_exactly_or_a_qualified_form'])} rules computes_exactly or a qualified
          form, of which the strict reading awards {len(strict['all_three'])}. Every reading is
          emitted per rule in the artifact's partitions block.
        status_provenance: >-
          the labels are the coverage builder's READING of derived evidence
          (case counts, ast spans, bracket occupancy, the dime-floor sweep,
          the not-implemented searches, the derived R4 / R8 / R9 bases);
          a label is pinned only by the byte-reproduction test, which is why
          this block awards nothing and the packet's verdicts are quoted.
      worked_examples_classification:
        # P7: which of the ten rows are SSA-published percentages and which
        # are the oracle's own arithmetic / branch selection. The split is
        # the packet's reading, carried by the coverage record; the ratio is
        # emitted so a referee re-adjudicates each row.
        n_published_percentage: {examples['n_published_percentage']}
        n_arithmetic_or_branch_selection: {examples['n_arithmetic_or_branch_selection']}
        rows:
{ex_lines}
        consequence: >-
          a row classified arithmetic_or_branch_selection does NOT count
          toward E2; the coverage record's E2 labels for R12 (partial) and
          R14 (partial) already reflect that split.
      case_set:
        # P8 facts, from the coverage record.
        cross_engine: {{ n_cases: {facts['cross_engine']['n_cases']}, eligibility_years: {facts['cross_engine']['eligibility_years']}, birth_years: {facts['cross_engine']['birth_years']}, history_span_ages: [22, 62], n_distinct_shapes: {facts['cross_engine']['n_distinct_shapes']} }}
        pe_us_foundation: {{ n_cases: {facts['pe_us_foundation']['n_cases']}, aime_values: {facts['pe_us_foundation']['aime_values']}, claim_ages: {facts['pe_us_foundation']['claim_ages']}, birth_years: {facts['pe_us_foundation']['birth_years']} }}
        couple_grid: {{ n_rows: {facts['couple_grid']['n_rows']}, n_rows_with_both_spouses_drawing_an_excess: {facts['couple_grid']['n_rows_with_both_spouses_drawing_an_excess']} }}
        survivor_grid: {{ n_rows: {facts['survivor_grid']['n_rows']}, distinct_own_deceased_pia_pairs: {len(facts['survivor_grid']['distinct_own_deceased_pia_pairs'])} }}
        sufficiency: "<RULING P8 case_set>"
      known_gaps:
        r3_computation_year_count: >-
          {gaps['r3_computation_year_count_is_degenerate']}
        r4_zero_pad_branch_unexercised: >-
          {gaps['r4_zero_pad_branch_unexercised']}
        r8_r16_absent_from_the_240: >-
          {gaps['r8_r16_absent_from_the_240']}
        r11_r15_no_second_engine: >-
          {gaps['r11_r15_no_second_engine']}
        r12_r14_grid_thinness: >-
          {gaps['r12_r14_grid_thinness']}
      named_constants:
        # X2 of the definition: quantities the statute makes a SCHEDULE and
        # the module makes a CONSTANT, with the domain over which each is exact.
        computation_years:
          value: {nc['computation_years']['value']}
          code: ss/benefits.py:{nc['computation_years']['code']['first_line']}
          statute: {nc['computation_years']['statute']}
          exact_domain: {nc['computation_years']['exact_domain']}
          wrong_outside: {nc['computation_years']['wrong_outside']}
        survivor_reduction_period_months:
          value: {nc['survivor_reduction_period_months']['value']}
          code: ss/params.py:{nc['survivor_reduction_period_months']['code']['first_line']}
          statute: {nc['survivor_reduction_period_months']['statute']}
          exact_domain: {nc['survivor_reduction_period_months']['exact_domain']}
          wrong_outside: >-
            {nc['survivor_reduction_period_months']['wrong_outside']}
          ruling: "<RULING P9 survivor_period>"
        one_month_eligibility_subtlety:
          code: ss/benefits.py:{nc['one_month_eligibility_subtlety']['code']['first_line']}-{nc['one_month_eligibility_subtlety']['code']['last_line']}
          content: >-
            {nc['one_month_eligibility_subtlety']['content']}
      not_implemented:
        # X1 of the definition. Each search re-runs in the coverage record's
        # tests: root, patterns, files searched, empty hit list.
        family_maximum: >-
          NOT IMPLEMENTED (P10). {fm['P10']}: {', '.join(fm['auxiliary_functions_returning_uncapped_amounts'])} return UNCAPPED
          amounts and household.CoupleBenefit.total (class CoupleBenefit,
          household.py:{cons['class_lines'][0]}-{cons['class_lines'][1]}; the total property :{cons['total_property_lines'][0]}-{cons['total_property_lines'][1]}; derived
          by ast) sums both own benefits and both excess spousal amounts.
          The family maximum binds precisely where auxiliary benefits stack;
          no committed case stacks enough for it to bind, so this is a KNOWN
          UNCAUGHT class, never bite. Search: {fm['search']['patterns']} over
          {fm['search']['n_files_searched']} files under {fm['search']['root']}, no hits.
        wep_gpo: NOT IMPLEMENTED
        retirement_earnings_test: NOT IMPLEMENTED
        special_minimum_pia: NOT IMPLEMENTED
        cola_applied_to_pia: NOT IMPLEMENTED (nothing in ss/ references COLA)
        child_and_parent_benefits: NOT IMPLEMENTED (incl. the child-in-care spouse)
        disability_pia: NOT IMPLEMENTED (no freeze, no alternate computation years)
        recomputation_post_entitlement: NOT IMPLEMENTED
        by_design: >-
          {frozen['key_sentence']} ({frozen['source']}). These absences
          are a scope decision, not a defect; the gate publishes them so
          "computes exactly" is never read as "computes everything".
      degenerate_candidates:
        # Teeth, REASONED from the committed test inventory, not executed
        # (no engine runs in this ceremony). For an exact-agreement gate the
        # degenerate candidate is a PERTURBED ORACLE.
        dime_floor_to_nearest: {{ candidate: "415(g) rounds to the NEAREST dime instead of DOWN", caught_by: "R7 -- the exhaustive integer-AIME sweep, tests/ss/test_cross_engine.py" }}
        second_bracket_rate_off_by_0_01: {{ candidate: "32% -> 33%", caught_by: "R5 -- every worker above the first bend point in the 240" }}
        bend_point_base_year_wrong: {{ candidate: "NAWI base 1978 instead of 1977", caught_by: "R6 -- the 2026 and 2015 SSA determinations and the load-time cross-check against every stored policyengine-us year" }}
        spousal_first_bracket_uses_the_worker_rate: {{ candidate: "5/9 %/mo instead of 25/36 %/mo for the spouse", caught_by: "R11 -- the 32.5%-at-62 published figure" }}
        rib_lim_applied_when_the_deceased_delayed: {{ candidate: "cap at 82.5% even when the factor exceeds 1", caught_by: "R14 -- the DRC pass-through row (1320.0)" }}
        family_maximum_omitted: {{ candidate: "the SHIPPED oracle", caught_by: "NOTHING -- a KNOWN UNCAUGHT class (P10)" }}
        catch_structure: >-
          every implemented rule with an E2 anchor is caught by a
          perturbation of the quantity that anchor pins. The uncaught
          classes are, exactly: R3 outside its exact domain, R11-R15 under
          an E1-only perturbation (no second engine exists to disagree),
          and every rule in not_implemented. Stated as uncaught, never
          advertised as covered.
      governance:
        registration: >-
          Pre-registered on issue #42, as every other candidate run. Because
          the statistic is exact agreement rather than a threshold, what a
          candidate registers is the CASE SET and the engine revision; the
          number is not negotiable.
        amendment_rules:
          inherits: gate_1
          no_self_rescue: >-
            Inherited verbatim (gates.yaml:{cite['no_self_rescue']}). Sharpened here: a rule may
            not be REMOVED from rule_inventory, and a case may not be
            removed from a rule's registered case set, because the oracle
            failed it.
          amendments_only_via: >-
            public proposal + adversarial referee round + verification +
            maintainer ratification by merge.
          description_claims_exactly_the_scored_surface: >-
            Bound by the standing rule (gates.yaml:1056, :3294, :4869). THIS
            GATE'S FIRST DUTY IS TO DISCHARGE gate_2.description's "benefit
            formulas earn per-rule 'computes exactly' status" (:{citations['computes_exactly']['occurrences'][0]}), which
            today claims a status no gate_2 cell gates -- gate_2's 46 cells
            (:{cite['gate_2_n_gated_cells']}) contain no benefit-formula cell, and gate_2's own
            certification_scope puts own-record benefit levels OUTSIDE 2a /
            2b / 2c (:{cite['gate_2_own_record_outside_2a_2b_2c']}). Either this gate defines and awards the status
            (<RULING P1 gate_kind>), or gate_2's description is amended to
            drop the clause. Leaving both is the one outcome the standing
            rule forbids (P3).
        frozen_scope_clause: >-
          {frozen['clause']}
      certification_scope:
        tranche: b2_statutory_benefit_oracle
        certifies: >-
          {scope['headline']}
        supports:
          - >-
            {scope['supports'][0]}
          - >-
            {scope['supports'][1]}
        does_not_authorise:
{chr(10).join('          - >-' + chr(10) + '            ' + normalized(line) for line in scope['does_not_authorise_P14'])}
      coverage_record_does_not_establish:
        # every does_not_establish line of runs/pia_rule_coverage_v1.json, carried
{dne_lines}
      open_rulings:
        # Each is FILED and PRICED in runs/pia_gate_partition_v1.json
        # open_questions_for_the_ceremony; none is made here.
        P1: "<RULING P1 gate_kind> -- exact agreement as a gate kind vs an amendment striking gates.yaml:{citations['computes_exactly']['occurrences'][0]}; decide FIRST"
        P6: "<RULING P6 e1_waiver> -- per-rule E1 waivers for R11-R15 vs splitting the gate and holding the auxiliary half"
        P8: "<RULING P8 case_set> -- is the registered case set sufficient, or must a wider one be built first"
        P9: "<RULING P9 survivor_period> -- the 84-month constant vs the override reading of E2"
        P13: "<RULING P13 granularity> -- the sixteen-rule cut vs splitting R12 / R14"
        S7: "sequencing constraint -- ceremony_notes.flip_plan (the two live-file guard tests)"
        S8: "<RULING S8 e1_clause> -- E1 as committed {CROSS_ENGINE_COMMIT_DATE} at engine {ce['engine_revision']}, not re-executed (Axiom half)"
      ceremony_notes:
        placeholders_the_ratifying_round_must_fill:
          - "<RULING P1 gate_kind>"
          - "<RULING P6 e1_waiver>"
          - "<RULING P8 case_set>"
          - "<RULING P9 survivor_period>"
          - "<RULING P13 granularity>"
          - "<RULING S8 e1_clause>"
          - "<FILLED AT RATIFICATION>"
        flip_plan: >-
          the commit that inserts this block flips
          GATE_B2_PIA_ORACLE_BLOCK_LANDED from False to True in
          tests/test_gates_derivations.py and
          tests/test_pia_gate_partition_v1.py, RETIRES
          tests/test_pia_rule_coverage.py::
          test_no_gate_b2_pia_oracle_exists_in_gates_yaml (and its claiming
          twin tests/test_claiming_publication_floor.py::
          test_no_gate_b2_claiming_exists_in_gates_yaml if gate_b2_claiming
          lands in the same PR) -- both read the live file by design and
          fail the moment the block lands (verification section 11: exactly
          those two) -- admits the new key at the three master-compare sites
          (test_gate_m4_flip_leaves_locked_siblings_byte_identical,
          tests/test_gate_w1_derivations.py, tests/test_gate_m6_derivations.py),
          fills floor_run_sha256 with the ratified sha256 of
          runs/pia_gate_partition_v1.json, and re-refreshes the tier
          manifest -- all in the SAME commit. The coverage record's
          blob-pinned gates.yaml citation survives the commit unchanged.
        derivations_bound_by: tests/test_gates_derivations.py (test_gate_b2_pia_oracle_*) and tests/test_pia_gate_partition_v1.py
        wording_audit: >-
          the two words the standing wording audit forbids occur 0 times in
          this block (artifact wording_audit.forbidden_word_counts); the
          definition of "computes exactly" is stated (P2); what a pass does
          not authorise is stated (P14); every does_not_establish line of
          the coverage record is carried.
"""
    return text


# --------------------------------------------------------------------------
# Wording audit
# --------------------------------------------------------------------------
def required_phrases(coverage: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        {
            "item": "the standing rule",
            "required_phrases": [
                "description_claims_exactly_the_scored_surface",
                "gates.yaml:1056, :3294, :4869",
            ],
        },
        {
            "item": "computes exactly is defined (P2)",
            "required_phrases": [
                "E1 INDEPENDENT RE-EXECUTION",
                "E2 EXTERNAL ANCHOR",
                "E3 EXERCISED BRANCHES AND BOUNDARIES",
                "X1 NAMED NON-COVERAGE",
                "X2 NAMED CONSTANTS",
                "TO THE CENT",
            ],
        },
        {
            "item": "what a pass does not authorise (P14)",
            "required_phrases": [
                "does_not_authorise",
                "any household benefit TOTAL",
            ],
        },
        {
            "item": "the E1 clause (S8)",
            "required_phrases": [
                "E1 as committed 2026-07-05 at engine ffef7b4",
                "not re-executed",
            ],
        },
        {
            "item": "family maximum disclosure (P10)",
            "required_phrases": [
                "CoupleBenefit.total",
                "KNOWN UNCAUGHT class",
            ],
        },
        {
            "item": "frozen scope (P15)",
            "required_phrases": [
                "Do not extend this module's rule coverage; extend the Axiom encodings."
            ],
        },
        {
            "item": "precision to the cent (P11)",
            "required_phrases": ["NOT bit-exactness"],
        },
        {
            "item": "the partition is the verdict",
            "required_phrases": ["does NOT produce one boolean"],
        },
    ]
    for i, line in enumerate(coverage["does_not_establish"]):
        items.append(
            {
                "item": f"coverage does_not_establish[{i}] carried",
                "required_phrases": [normalized(line)],
            }
        )
    return items


def wording_audit(
    fragment: str, artifact_json_without_audit: str, coverage: dict[str, Any]
) -> dict[str, Any]:
    flat = normalized(fragment)
    low_f = flat.lower()
    low_a = normalized(artifact_json_without_audit).lower()
    forbidden = {
        w: {
            "fragment": len(re.findall(rf"\b{w}\b", low_f)),
            "artifact_excluding_this_block": len(
                re.findall(rf"\b{w}\b", low_a)
            ),
        }
        for w in FORBIDDEN_WORDS
    }
    checklist = []
    for item in required_phrases(coverage):
        present = {p: (p in flat) for p in item["required_phrases"]}
        checklist.append(
            {
                **item,
                "required_present": present,
                "holds": all(present.values()),
            }
        )
    return {
        "scope": (
            "the draft gate_b2_pia_oracle block (draft_gates_yaml_fragment."
            "text) and this artifact's JSON with this audit block removed. "
            "No PR is opened by this sitting; the PR body's audit is owed by "
            "the verification round at PR time."
        ),
        "forbidden_words": list(FORBIDDEN_WORDS),
        "forbidden_word_counts": forbidden,
        "forbidden_words_absent_from_fragment": all(
            v["fragment"] == 0 for v in forbidden.values()
        ),
        "forbidden_words_absent_from_artifact": all(
            v["artifact_excluding_this_block"] == 0 for v in forbidden.values()
        ),
        "required_phrases": checklist,
        "all_required_phrases_present": all(c["holds"] for c in checklist),
    }


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
def run(verbose: bool = True) -> dict[str, Any]:
    started = time.time()
    coverage = load_source_coverage()
    source_pins = check_source_pins(coverage)
    parts = partitions(coverage)
    examples = worked_examples(coverage)
    precision = precision_claim(coverage)
    facts = case_set_facts(coverage)
    gran = granularity_facts(coverage)
    clause = e1_clause(coverage)
    fm = family_maximum(coverage)
    frozen = frozen_scope(coverage)
    gaps = known_gaps(coverage)
    scope = certification_scope(parts)
    citations = gates_yaml_citations()
    if citations["computes_exactly"]["occurrences"] != [
        coverage["gate_status"]["gates_yaml_citation"]["cited_line"]
    ]:
        raise RuntimeError(
            "the computes-exactly citation differs from the coverage record's"
        )
    if verbose:
        strict = parts["strict"]
        print(
            f"strict partition: all three {strict['all_three']}; strict subset "
            f"{strict['n_strict_subset']}; none {strict['none']}"
        )
        for name, alt in parts["alternatives"].items():
            if "all_three" in alt:
                print(
                    f"  {name}: all three {alt['all_three']}; moves {sorted(alt['moves_vs_strict'])}"
                )

    fragment = draft_fragment(
        coverage,
        parts,
        examples,
        precision,
        facts,
        clause,
        fm,
        frozen,
        gaps,
        scope,
        citations,
    )
    parsed = yaml.safe_load("gates:\n" + fragment)["gates"][GATE_NAME]
    if parsed["status"] != "draft_pending_referee_round" or parsed["locked"]:
        raise RuntimeError("the draft block must parse as a draft")
    if len(parsed["thresholds"]["rule_inventory"]) != coverage["n_rules"]:
        raise RuntimeError("the draft block's rule inventory is short")
    fragment_meta = {
        "text": fragment,
        "text_sha256": _sha_of_text(fragment),
        "n_lines": len(fragment.splitlines()),
        "n_bytes": len(fragment.encode("utf-8")),
        "indent": (
            "2 spaces under `gates:`; parse with "
            f"yaml.safe_load('gates:\\n' + text)['gates']['{GATE_NAME}']"
        ),
        "status_in_text": "draft_pending_referee_round",
        "written_nowhere_else": (
            "asserted by tests/test_pia_gate_partition_v1.py and "
            "tests/test_gates_derivations.py: gates.yaml mentions neither "
            f"{GATE_NAME} nor this artifact nor {SOURCE_COVERAGE_REL} while "
            f"{MARKER} is False, and the text occurs in no other tracked file"
        ),
    }

    artifact: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "run": RUN_NAME,
        "reported_not_gated": True,
        "component": (
            "statutory benefit oracle (#74 component SF); THRESHOLD BINDING "
            "for gate_b2_pia_oracle, the prerequisite of the packet's PIA "
            "ceremony step 5"
        ),
        "purpose": (
            "the gate-schema derivation from the VERIFIED coverage record "
            f"{SOURCE_COVERAGE_REL}: the per-rule E1 / E2 / E3 partition "
            "under an explicit total mapping and under every filed "
            "alternative, the precision claim, the worked-example "
            "classification, the E1 clause, the family-maximum and frozen-"
            "scope disclosures re-derived from the modules, the "
            "certification scope with what a pass does not authorise, the "
            "rulings filed and priced, the wording audit and the DRAFT "
            "gate_b2_pia_oracle block as a string. It edits no gates.yaml "
            "byte, executes no engine, awards no status and makes no ruling."
        ),
        "does_not_do": DOES_NOT_DO,
        "source_coverage": {
            "path": SOURCE_COVERAGE_REL,
            "size_bytes": SOURCE_COVERAGE_COMMITTED[0],
            "sha256": SOURCE_COVERAGE_COMMITTED[1],
            "schema_version": coverage["schema_version"],
            "built_utc": coverage["build"]["built_utc"],
            "committed_at": "cd8f167280de47444164d2ab0ec11dd061b59b00 (floors v2)",
            "verified_by": VERIFICATION_REPORT,
            "read_by": "path, with size and sha256 checked before any value is read",
            "its_source_pins_rechecked_on_disk": source_pins,
        },
        "ceremony": {
            "step": (
                "the prerequisite of the packet's PIA sequence step 5 "
                "(section 11): the per-rule partition bound to the coverage "
                "record; P1 is decided first by the round"
            ),
            "packet": PACKET_REPORT,
            "referees": {
                "A_statistical": REFEREE_A_REPORT,
                "B_contract_and_record": REFEREE_B_REPORT,
            },
            "floors_v2": FLOORS_V2_REPORT,
            "verification": VERIFICATION_REPORT,
            "gates_yaml_untouched": True,
            "gates_yaml_stub": (
                f"{GATE_NAME} (DRAFT as a string in draft_gates_yaml_fragment; "
                "not in gates.yaml)"
            ),
            "next": (
                "P1 decided -> adversarial referee round on these bound "
                "readings -> the rulings -> verification -> ratifying merge "
                f"with the {MARKER} flip and the live-file guard test retired"
            ),
        },
        "derivation_convention": {
            "partition": (
                "per rule, class = all_three if E1, E2 and E3 all hold under "
                "the mapping; strict_subset if one or two hold; none if none; "
                "the mapping is TOTAL over the labels the coverage record "
                "uses and the build fails on an unmapped label"
            ),
            "strict_mapping": parts["strict"]["mapping"],
            "precision": precision["claim"],
            "rule_id_rule": "the coverage record's sixteen ids, in its order",
        },
        "rule_order": [r["id"] for r in coverage["rule_inventory"]],
        "partitions": parts,
        "gate_partition": {
            "all_three": parts["strict"]["all_three"],
            "strict_subset": parts["strict"]["strict_subset"],
            "none": parts["strict"]["none"],
            "n_all_three": parts["strict"]["n_all_three"],
            "n_strict_subset": parts["strict"]["n_strict_subset"],
            "n_none": parts["strict"]["n_none"],
            "reading_applied": "strict (the definition's letter); see partitions.alternatives",
            "rulings_that_can_move_it": {
                "P1": "yes: if the clause is struck instead, no partition is awarded and the record stays REPORTED",
                "P6": (
                    "class labels only: E1 waived for R11-R15 moves no rule "
                    "into all_three (each still fails E2 or E3)"
                    if not parts["alternatives"]["p6_e1_waiver_for_r11_r15"][
                        "moves_vs_strict"
                    ]
                    or set(
                        parts["alternatives"]["p6_e1_waiver_for_r11_r15"][
                            "all_three"
                        ]
                    )
                    == set(parts["strict"]["all_three"])
                    else "yes"
                ),
                "P8": "yes, on a rebuilt case set: E3 for the sampling-limited rules; R3 would be SEPARATED (an E1 disagreement outside the exact domain), not satisfied",
                "P9": (
                    "class label of R13 only"
                    if set(
                        parts["alternatives"][
                            "p9_constant_override_counts_as_e2"
                        ]["all_three"]
                    )
                    == set(parts["strict"]["all_three"])
                    else "yes"
                ),
                "P13": "yes, at a finer grain, after a v2 coverage build with per-operation case sets",
            },
            "status": "DERIVED under the strict reading; pending the rulings named",
        },
        "precision_claim_P11": precision,
        "worked_examples_classification_P7": examples,
        "case_set_P8": facts,
        "granularity_P13": gran,
        "e1_clause_S8": clause,
        "family_maximum_P10": fm,
        "frozen_scope_P15": frozen,
        "known_gaps_restated": gaps,
        "named_constants_carried": coverage["named_constants"],
        "not_implemented_searches_carried": coverage["not_implemented"][
            "searches"
        ],
        "additional_absences_carried": coverage["not_implemented"][
            "additional_absences_from_a_full_read_of_the_module"
        ],
        "certification_scope": scope,
        "computes_exactly_definition_carried": coverage[
            "computes_exactly_definition_proposal"
        ],
        "status_provenance_carried": coverage["status_provenance"],
        "packet_reconciliation_carried": coverage["packet_reconciliation"],
        "coverage_does_not_establish_carried": coverage["does_not_establish"],
        "gates_yaml_citations": citations,
        "flip_plan": flip_plan(),
        "open_questions_for_the_ceremony": open_questions(
            parts, facts, gran, clause
        ),
        "draft_gates_yaml_fragment": fragment_meta,
        "revision_pins": {
            "populace_dynamics_sha": _git_sha(ROOT),
            "source_coverage_sha256": SOURCE_COVERAGE_COMMITTED[1],
            "source_coverage_size_bytes": SOURCE_COVERAGE_COMMITTED[0],
            "coverage_builder_sha256": _sha_of_file(
                ROOT / COVERAGE_BUILDER_REL
            ),
            "gate_builder_sha256": _sha_of_file(Path(__file__).resolve()),
            "gates_yaml_git_blob_for_the_citations": GATES_YAML_BLOB_AT_BINDING,
            "gates_yaml_pin_semantics": citations["pin_semantics"],
            "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        },
        "build": {"built_by": "scripts/build_pia_gate_partition_v1.py"},
    }
    audit = wording_audit(fragment, json.dumps(artifact), coverage)
    if not audit["forbidden_words_absent_from_fragment"]:
        raise RuntimeError(
            f"forbidden word in the draft block: {audit['forbidden_word_counts']}"
        )
    if not audit["forbidden_words_absent_from_artifact"]:
        raise RuntimeError(
            f"forbidden word in the artifact: {audit['forbidden_word_counts']}"
        )
    if not audit["all_required_phrases_present"]:
        raise RuntimeError(
            "required phrase missing: "
            + str(
                [
                    c["item"]
                    for c in audit["required_phrases"]
                    if not c["holds"]
                ]
            )
        )
    artifact["wording_audit"] = audit
    artifact["elapsed_seconds"] = round(time.time() - started, 1)
    return artifact


def main() -> None:
    artifact = run(verbose=True)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"wrote {ARTIFACT_PATH} ({ARTIFACT_PATH.stat().st_size} bytes)")
    frag = artifact["draft_gates_yaml_fragment"]
    print(
        f"draft block: {frag['n_lines']} lines, {frag['n_bytes']} bytes, "
        f"sha256 {frag['text_sha256']}"
    )


if __name__ == "__main__":
    main()
