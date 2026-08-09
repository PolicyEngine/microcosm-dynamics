"""Focused tests for the Amendment-12 tier-2 targeted-sweep builder."""

from __future__ import annotations

import copy
import hashlib
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_amendment12_tier2_targeted_sweeps as sweeps  # noqa: E402
import validate_amendment13_execution_law as a13  # noqa: E402


def _write_seal_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    law = a13.build_ratification_bound_execution_template()
    for row in law["successor_era_seal_rows"]:
        path = root / (
            f"era_{row['era_order_position']:02d}_successor_seal_v1.json"
        )
        path.write_bytes(sweeps.canonical_bytes(row))


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    seal_root = tmp_path_factory.mktemp("successor-seals")
    _write_seal_fixture(seal_root)
    value = sweeps.build_artifact(seal_root=seal_root, verify_git=False)
    sweeps.validate_artifact(value)
    return value


def _repin(value):
    payload = {
        key: copy.deepcopy(member)
        for key, member in value.items()
        if key not in {"artifact_id", "integrity"}
    }
    digest = hashlib.sha256(sweeps.canonical_bytes(payload)).hexdigest()
    value["artifact_id"] = sweeps.ARTIFACT_ID_PREFIX + digest
    value["integrity"] = {
        "canonicalization": sweeps.CANONICALIZATION,
        "payload_sha256": digest,
    }


def _repin_domain(value, rows_key, count_key, digest_key):
    rows = value[rows_key]
    value[count_key] = len(rows)
    value[digest_key] = sweeps._domain_sha(rows)


def test__canonical_json__is_compact_ascii_sorted_with_terminal_lf():
    assert sweeps.canonical_bytes({"z": "é", "a": 1}) == (
        b'{"a":1,"z":"\\u00e9"}\n'
    )


def test__fresh_rebuild__covers_all_81_documents_without_promoting_outputs(
    artifact,
):
    assert artifact["document_positions_swept"] == list(range(1, 82))
    assert artifact["document_count"] == 81
    source = artifact["source_rebuild"]
    assert source["fresh_in_memory_rebuild"] is True
    assert (
        source["committed_tier1_artifacts_used_as_expected_evidence"] is False
    )
    assert source["rebuilt_bundle_artifact_count"] == 8
    assert [
        row["artifact_role"] for row in source["rebuilt_bundle_artifact_rows"]
    ] == list(sweeps.a12.OUTPUT_FILENAMES)


def test__lifecycle__is_exact_nonauthority_and_emits_nothing(artifact):
    assert artifact["lifecycle"] == {
        "nonauthority": True,
        "authority_emitted": False,
        "certification_emitted": False,
        "q5_input_emitted": False,
        "production_output_emitted": False,
    }


def test__seal_bindings__bind_all_six_exact_canonical_files(artifact):
    rows = artifact["successor_seal_bindings"]
    assert len(rows) == 6
    assert [row["era_order_position"] for row in rows] == list(range(1, 7))
    assert all(row["byte_size"] > 0 for row in rows)
    assert all(len(row["raw_sha256"]) == 64 for row in rows)
    assert all(
        row["successor_era_seal_id"].startswith("a13-successor-era-seal:")
        for row in rows
    )


def test__continuation_sweep__preserves_five_plus_eight_plus_two(artifact):
    value = artifact["continuation_admission_rule_sweep"]
    assert value["document_positions_scanned"] == list(range(1, 82))
    assert value["a12_continuation_citation_count"] == 5
    assert value["a13_terminal_disclosure_successor_count"] == 8
    assert value["a13_exact_g75_composition_successor_count"] == 2
    assert value["targeted_hit_count"] == value["adjudicated_hit_count"] == 15
    assert value["predecessor_domains_disjoint"] is True
    assert value["instruction_domains_disjoint"] is True
    assert value["unexplained_targeted_hit_count"] == 0
    assert all(
        row["successor_payload"]["terminal_status"]
        == a13.INCOMPLETE_FRAGMENT_STATUS
        for row in value["a13_terminal_disclosure_successor_rows"]
    )
    assert {
        row["document_source_position"]
        for row in value["a13_exact_g75_composition_successor_rows"]
    } == {66, 70}


def test__pairwise_sweep__adjudicates_every_candidate_without_union(artifact):
    value = artifact["pairwise_decomposition_admission_rule_sweep"]
    assert value["document_positions_scanned"] == list(range(1, 82))
    candidates = value["candidate_adjudication_rows"]
    assert value["candidate_decision_counts"] == dict(
        sorted(Counter(row["decision"] for row in candidates).items())
    )
    assert value["approved_pair_rows"] == [
        pair
        for row in candidates
        if row["decision"] in sweeps.PAIRWISE_APPROVAL_DECISIONS
        for pair in row["approved_pair_rows"]
    ]
    assert value["every_candidate_adjudicated"] is True
    assert value["occurrence_union_constructed"] is False
    assert value["occurrence_union_rows"] == []
    assert value["unexplained_targeted_hit_count"] == 0
    typed = [
        row
        for row in value["approved_pair_rows"]
        if row["pair_kind"] == "typed_instruction_import_projection"
    ]
    assert value["typed_projection_pair_count"] == len(typed)
    assert value["composite_stop_adjudication_count"] == sum(
        row["composite_stop_citation"] is not None for row in candidates
    )
    assert all(
        row["typed_projection_union_prohibited"] is True
        and row["class_closure_eligible"] is False
        for row in typed
    )


def test__semantic_gate__covers_265_and_appends_38_nonalias_repairs(artifact):
    value = artifact["semantic_ledger_alias_gate_sweep"]
    assert value["document_positions_scanned"] == list(range(1, 82))
    assert value["semantic_ledger_adjudication_count"] == 265
    ledger_rows = value["semantic_ledger_adjudication_rows"]
    assert value["semantic_ledger_decision_counts"] == dict(
        sorted(Counter(row["decision"] for row in ledger_rows).items())
    )
    assert value["semantic_approved_alias_evidence_count"] == sum(
        row["decision"] in sweeps.ALIAS_APPROVAL_DECISIONS
        for row in ledger_rows
    )
    assert value["structural_valid_alias_evidence_count"] == len(
        {
            evidence_id
            for row in value["structural_filter_projection_rows"]
            for evidence_id in row["valid_alias_arm_evidence_ids"]
        }
    )
    assert value["structural_only_alias_admission_count"] == 0
    assert value["alias_admissions_from_semantic_ledger_only"] is True
    assert value["structural_predicates_filter_only"] is True
    assert value["repaired_nonalias_successor_count"] == 38
    assert Counter(
        row["successor_kind"]
        for row in value["repaired_nonalias_successor_rows"]
    ) == {
        "semantically_incompatible_local_proof": 28,
        "incomplete_fragment_terminal_disclosure": 8,
        "composed_fragment_complete_instruction": 2,
    }
    assert all(
        row["successor_payload"]["alias_admitted"] is False
        and row["successor_payload"]["occurrence_equivalence_admitted"]
        is False
        and row["successor_payload"]["repeat_coverage_arm_admitted"] is False
        for row in value["repaired_nonalias_successor_rows"]
    )
    assert value["untouched_law_gap_predecessor_count"] == 14
    assert value["repaired_and_law_gap_domains_disjoint"] is True
    assert value["unexplained_targeted_hit_count"] == 0


def test__output_root__is_configurable_and_round_trips_canonical_bytes(
    artifact, tmp_path
):
    output = sweeps._write_artifact(artifact, tmp_path)
    assert output == tmp_path / sweeps.OUTPUT_FILENAME
    assert output.read_bytes() == sweeps.canonical_bytes(artifact)
    assert sweeps._load_artifact(output) == artifact


def test__committed_seal_gate__rejects_untracked_fixture(tmp_path):
    seal_root = tmp_path / "seals"
    _write_seal_fixture(seal_root)
    law = a13.build_ratification_bound_execution_template()
    with pytest.raises(sweeps.SweepError, match="outside repository"):
        sweeps._load_successor_seal_bindings(
            law,
            seal_root,
            verify_git=True,
        )


def _mutation_certification(value):
    value["lifecycle"]["certification_emitted"] = True


def _mutation_document_omitted(value):
    value["document_positions_swept"].pop()
    value["document_count"] -= 1
    value["document_position_domain_sha256"] = sweeps._domain_sha(
        value["document_positions_swept"]
    )


def _mutation_seal_omitted(value):
    value["successor_seal_bindings"].pop()
    _repin_domain(
        value,
        "successor_seal_bindings",
        "successor_seal_binding_count",
        "successor_seal_binding_domain_sha256",
    )


def _mutation_continuation_overlap(value):
    value["continuation_admission_rule_sweep"][
        "instruction_domains_disjoint"
    ] = False


def _mutation_disclosure_omitted(value):
    target = value["continuation_admission_rule_sweep"]
    target["a13_terminal_disclosure_successor_rows"].pop()
    _repin_domain(
        target,
        "a13_terminal_disclosure_successor_rows",
        "a13_terminal_disclosure_successor_count",
        "a13_terminal_disclosure_successor_domain_sha256",
    )
    target["a13_terminal_disclosure_successor_keyset_sha256"] = (
        sweeps._keyset_sha(
            [
                row["successor_row_id"]
                for row in target["a13_terminal_disclosure_successor_rows"]
            ]
        )
    )
    target["targeted_hit_count"] -= 1
    target["adjudicated_hit_count"] -= 1


def _mutation_fragment_alias(value):
    target = value["continuation_admission_rule_sweep"]
    target["a13_exact_g75_composition_successor_rows"][0]["successor_payload"][
        "alias_admitted"
    ] = True
    target["a13_exact_g75_composition_successor_domain_sha256"] = (
        sweeps._domain_sha(target["a13_exact_g75_composition_successor_rows"])
    )


def _mutation_occurrence_union(value):
    target = value["pairwise_decomposition_admission_rule_sweep"]
    target["occurrence_union_constructed"] = True
    target["occurrence_union_rows"] = [{"forged": True}]


def _mutation_typed_projection_union(value):
    target = value["pairwise_decomposition_admission_rule_sweep"]
    pair_id = next(
        row["semantic_alias_pair_adjudication_id"]
        for row in target["approved_pair_rows"]
        if row["pair_kind"] == "typed_instruction_import_projection"
    )
    for pair in target["approved_pair_rows"]:
        if pair["semantic_alias_pair_adjudication_id"] == pair_id:
            pair["typed_projection_union_prohibited"] = False
    for candidate in target["candidate_adjudication_rows"]:
        for pair in candidate["approved_pair_rows"]:
            if pair["semantic_alias_pair_adjudication_id"] == pair_id:
                pair["typed_projection_union_prohibited"] = False
    target["candidate_adjudication_domain_sha256"] = sweeps._domain_sha(
        target["candidate_adjudication_rows"]
    )
    target["approved_pair_domain_sha256"] = sweeps._domain_sha(
        target["approved_pair_rows"]
    )
    typed = [
        row
        for row in target["approved_pair_rows"]
        if row["pair_kind"] == "typed_instruction_import_projection"
    ]
    target["typed_projection_pair_domain_sha256"] = sweeps._domain_sha(typed)


def _mutation_ledger_row_omitted(value):
    target = value["semantic_ledger_alias_gate_sweep"]
    target["semantic_ledger_adjudication_rows"].pop()
    _repin_domain(
        target,
        "semantic_ledger_adjudication_rows",
        "semantic_ledger_adjudication_count",
        "semantic_ledger_adjudication_domain_sha256",
    )


def _mutation_structural_only_alias(value):
    target = value["semantic_ledger_alias_gate_sweep"]
    target["structural_filter_projection_rows"][0][
        "valid_alias_arm_evidence_ids"
    ].append("forged-structural-only-evidence")
    target["structural_filter_projection_domain_sha256"] = sweeps._domain_sha(
        target["structural_filter_projection_rows"]
    )
    structural_ids = sorted(
        {
            evidence_id
            for row in target["structural_filter_projection_rows"]
            for evidence_id in row["valid_alias_arm_evidence_ids"]
        }
    )
    target["structural_valid_alias_evidence_ids"] = structural_ids
    target["structural_valid_alias_evidence_count"] = len(structural_ids)
    target["structural_valid_alias_evidence_domain_sha256"] = (
        sweeps._domain_sha(structural_ids)
    )


def _mutation_repaired_alias(value):
    target = value["semantic_ledger_alias_gate_sweep"]
    target["repaired_nonalias_successor_rows"][0]["successor_payload"][
        "alias_admitted"
    ] = True
    target["repaired_nonalias_successor_domain_sha256"] = sweeps._domain_sha(
        target["repaired_nonalias_successor_rows"]
    )


def _mutation_law_gap_omitted(value):
    target = value["semantic_ledger_alias_gate_sweep"]
    target["untouched_law_gap_predecessor_ids"].pop()
    target["untouched_law_gap_predecessor_count"] -= 1
    target["untouched_law_gap_predecessor_domain_sha256"] = sweeps._domain_sha(
        target["untouched_law_gap_predecessor_ids"]
    )


@pytest.mark.parametrize(
    "mutation",
    (
        _mutation_certification,
        _mutation_document_omitted,
        _mutation_seal_omitted,
        _mutation_continuation_overlap,
        _mutation_disclosure_omitted,
        _mutation_fragment_alias,
        _mutation_occurrence_union,
        _mutation_typed_projection_union,
        _mutation_ledger_row_omitted,
        _mutation_structural_only_alias,
        _mutation_repaired_alias,
        _mutation_law_gap_omitted,
    ),
)
def test__mutation__fails_closed_after_coherent_envelope_repin(
    artifact, mutation
):
    candidate = copy.deepcopy(artifact)
    mutation(candidate)
    _repin(candidate)
    with pytest.raises(sweeps.SweepError):
        sweeps.validate_artifact(candidate)
