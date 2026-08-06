"""Tests for Amendment 12's pilot-only R_Q catalog-law artifacts."""

from __future__ import annotations

import copy
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_amendment12_rq_catalog_pilot as a12  # noqa: E402

J8_HEAD = (
    "psid-questionnaire-occurrence:"
    "53039f00a24f53c0b553758af54081344977c7654d9212e872df00ab81019f32"
)
NULL_ID_SHE = (
    "psid-questionnaire-occurrence:"
    "55692cbb0f805fe2a9ff24f1defa0652d79c14c47fb974404d13b1f622d13769"
)
Q87_OUTSIDE = (
    "psid-questionnaire-occurrence:"
    "9371a3521c96c33c4f0d91160d15c396a3c6cd4d71420555102973611e149a64"
)
DOC009_ZERO_PARENT = (
    "psid-questionnaire-occurrence:"
    "bf2851857a937216ef2eca4beadd8909b0135f79c317d51460dbf59d56c3dc7f"
)
DOC033_MULTI_PARENT = (
    "psid-questionnaire-occurrence:"
    "9c53e235bbf7f670615e101416e21e412385b0a4910f1845e053f2b041b48154"
)

EXPECTED_MUTATIONS = (
    "pilot_slice_reordered",
    "pilot_claims_q5",
    "role_assignment_omitted",
    "role_assignment_role_flipped",
    "role_assignment_class_invented",
    "role_assignment_alias_admitted",
    "role_assignment_equivalence_claimed",
    "role_sweep_class_omitted",
    "role_sweep_alias_class_claimed",
    "role_sweep_source_member_forged",
    "outside_repeat_target_emptied",
    "outside_repeat_terminal_changed",
    "outside_repeat_universal_arm_false",
    "outside_repeat_alias_admitted",
    "outside_repeat_evidence_not_singleton",
    "outside_repeat_source_target_forged",
    "zero_parent_emits_rq",
    "unique_parent_forced",
    "unique_parent_derived_slot_invented",
    "unique_parent_source_invented",
    "parent_and_source_witness_forged",
    "ambiguity_forced_parent",
    "ambiguity_emits_rq",
    "component_sweep_row_omitted",
    "component_sweep_source_anchor_forged",
    "component_row_extra_key",
    "doc036_law_gap_admitted",
    "doc036_component_slot_admitted",
    "proof_defect_lawified",
    "proof_defect_action_removed",
    "proof_defect_row_omitted",
    "gate_claims_certification",
    "gate_claims_repeat_coverage",
)


@pytest.fixture(scope="module")
def bundle():
    value = a12.load_committed_bundle()
    a12.validate_bundle(value)
    return value


@pytest.fixture(scope="module")
def rejected_mutations(bundle):
    return tuple(a12.run_mutation_tests(bundle))


@pytest.fixture(scope="module")
def source_rebuilt_bundle():
    documents, source_identity = a12._load_documents(a12.SourceReader(None))
    value = a12._build_bundle(
        documents,
        source_identity,
        a12._validate_design_prefix(),
    )
    a12.validate_bundle(value)
    return value


def test__committed_bundle__satisfies_positive_pilot_fixture(bundle):
    assert set(bundle) == set(a12.OUTPUT_FILENAMES)


def test__strict_json__rejects_duplicate_keys():
    with pytest.raises(a12.BuildError, match="invalid strict JSON"):
        a12.strict_json_loads(b'{"a":1,"a":2}\n', "duplicate")


def test__strict_json__rejects_nonfinite_constants():
    with pytest.raises(a12.BuildError, match="invalid strict JSON"):
        a12.strict_json_loads(b'{"a":NaN}\n', "nonfinite")


@pytest.mark.parametrize(
    "raw", (b'{"a":1e400}\n', b'{"a":0.10000000000000001}\n')
)
def test__strict_json__rejects_nonfinite_or_inexact_floats(raw):
    with pytest.raises(a12.BuildError, match="invalid strict JSON"):
        a12.strict_json_loads(raw, "float")


def test__strict_json__rejects_a_leading_bom():
    with pytest.raises(a12.BuildError, match="invalid strict JSON"):
        a12.strict_json_loads(b"\xef\xbb\xbf{}\n", "bom")


def test__canonical_json__is_ascii_compact_sorted_and_terminal_lf():
    assert a12.canonical_bytes({"z": "é", "a": 1}) == (
        b'{"a":1,"z":"\\u00e9"}\n'
    )


def test__revision_13_design__is_an_exact_immutable_prefix():
    identity = a12._validate_design_prefix()
    assert identity["byte_size"] == 3_557_513
    assert identity["sha256"] == a12.DESIGN_PREFIX_SHA256


def test__revision_13_design__equals_the_ratification_tree_entry():
    base = subprocess.check_output(
        [
            "git",
            "cat-file",
            "blob",
            "d0c38508553c6d410d445270ae5d911647529238:"
            "docs/design/covered_earnings_correction.md",
        ],
        cwd=ROOT,
    )
    current = a12.DESIGN_PATH.read_bytes()
    assert len(base) == a12.DESIGN_PREFIX_BYTES
    assert hashlib.sha256(base).hexdigest() == a12.DESIGN_PREFIX_SHA256
    assert current[: len(base)] == base


def test__pinned_source_rebuild__reproduces_every_published_byte(
    bundle,
    source_rebuilt_bundle,
):
    assert {
        key: a12.canonical_bytes(value)
        for key, value in source_rebuilt_bundle.items()
    } == {key: a12.canonical_bytes(value) for key, value in bundle.items()}


def test__pinned_source_rebuild__rejects_a_truncated_era_seal():
    base = a12.SourceReader(None)
    first_seal = a12.ERA_SEALS[0]["path"]

    class TruncatedReader:
        def read(self, path):
            raw = base.read(path)
            return raw[:-1] if path == first_seal else raw

    with pytest.raises(a12.BuildError, match="era seal size drift"):
        a12._load_documents(TruncatedReader())


def test__pilot_slice__is_the_exact_preregistered_16_document_domain(bundle):
    artifact = bundle["slice"]
    assert tuple(artifact["pilot_document_positions"]) == a12.PILOT_POSITIONS
    controls = [
        row["document_source_position"]
        for row in artifact["pilot_document_rows"]
        if row["pilot_role"] == "clean_era_control"
    ]
    assert tuple(controls) == a12.CONTROL_POSITIONS


def test__pilot_slice__has_the_sealed_input_census(bundle):
    census = bundle["slice"]["pilot_census"]
    assert census["questionnaire_occurrence_count"] == 13_219
    assert census["local_anchor_count"] == 6_123
    assert census["source_component_anchor_count"] == 3_095
    assert census["repeat_occurrence_count"] == 376


def test__role_assignments__cover_every_pilot_noncanonical_anchor(bundle):
    artifact = bundle["role"]
    assert artifact["role_assignment_count"] == 947
    assert artifact["unassigned_role_anchor_count"] == 0
    assert all(
        not row["alias_admitted_by_assignment"]
        and not row["occurrence_equivalence_claimed"]
        for row in artifact["role_assignment_rows"]
    )


@pytest.mark.parametrize(
    ("occurrence_id", "role", "printed_identifier", "exact_label"),
    (
        (J8_HEAD, a12.ROLE_HEAD, "J8", "Head"),
        (NULL_ID_SHE, a12.ROLE_SPOUSE, None, "she"),
    ),
)
def test__role_assignments__retain_hard_witness_bytes_without_alias(
    bundle,
    occurrence_id,
    role,
    printed_identifier,
    exact_label,
):
    row = next(
        value
        for value in bundle["role"]["role_assignment_rows"]
        if value["role_anchor_occurrence_id"] == occurrence_id
    )
    assert row["assigned_role"] == role
    assert row["printed_identifier"] == printed_identifier
    assert row["exact_label"] == exact_label
    assert row["proof_form"] == ("exact_label_class_role_assignment_non_alias")
    assert row["alias_admitted_by_assignment"] is False
    assert row["occurrence_equivalence_claimed"] is False


def test__role_sweep__is_corpus_exhaustive_and_role_disjoint(bundle):
    artifact = bundle["sweeps"]
    assert artifact["role_anchor_count"] == 10_521
    assert artifact["role_noncanonical_assignment_reach_count"] == 10_519
    assert artifact["role_exact_label_class_count"] == 273
    assert artifact["role_cross_classification_label_count"] == 0
    assert artifact["role_unreached_anchor_count"] == 0


def test__outside_repeat_dispositions__cover_the_exact_34_row_tail(bundle):
    artifact = bundle["repeat"]
    assert artifact["outside_domain_repeat_disposition_count"] == 34
    assert artifact["relation_counts"] == {
        "explicit_cross_reference": 17,
        "explicit_repeat_instruction": 17,
    }
    assert artifact["document_counts"] == {
        "14": 2,
        "40": 22,
        "56": 5,
        "58": 4,
        "66": 1,
    }


def test__outside_repeat_disposition__retains_q87_witness_without_alias(
    bundle,
):
    row = next(
        value
        for value in bundle["repeat"]["outside_domain_repeat_disposition_rows"]
        if value["source_instruction_occurrence_id"] == Q87_OUTSIDE
    )
    assert row["unresolved_target_reference"]["matched_text"] == "B4, (P. 7)"
    assert row["evidence_occurrence_ids"] == [Q87_OUTSIDE]
    assert row["alias_anchor_occurrence_id"] is None
    assert row["referenced_anchor_occurrence_id"] is None
    assert row["alias_admitted"] is False


def test__repeat_gate__does_not_hide_other_unresolved_instructions(bundle):
    census = bundle["gate"]["pilot_census"]
    assert census["valid_direct_proof_instruction_count"] == 106
    assert census["outside_domain_instruction_count"] == 34
    assert census["incompatible_proof_instruction_count"] == 9
    assert census["otherwise_unresolved_instruction_count"] == 228
    assert bundle["gate"]["overall_repeat_catalog_coverage_status"] == (
        "fail_closed_unresolved_rows_remain"
    )


def test__component_parents__exact_partition_the_pilot(bundle):
    artifact = bundle["component"]
    assert artifact["zero_parent_disposition_count"] == 1_488
    assert artifact["unique_parent_assignment_count"] == 1_307
    assert artifact["multi_parent_ambiguity_count"] == 300
    assert artifact["complete_component_resolution_count"] == 3_095
    assert artifact["serialized_parent_cardinality_counts"] == {
        "zero": 1_466,
        "one": 1_329,
        "multiple": 300,
    }
    assert all(
        row["r_q_relationship_emitted"] is False
        for key in (
            "zero_parent_disposition_rows",
            "unique_parent_assignment_rows",
            "multi_parent_ambiguity_rows",
        )
        for row in artifact[key]
    )
    assert all(
        row["tier_2_unique_parent_arm_eligible"] is True
        for row in artifact["unique_parent_assignment_rows"]
    )


def test__zero_parent__retains_doc009_witness_as_nonrelationship(bundle):
    row = next(
        value
        for value in bundle["component"]["zero_parent_disposition_rows"]
        if value["component_anchor_occurrence_id"] == DOC009_ZERO_PARENT
    )
    assert row["component_kind"] == "source_remuneration_component"
    assert row["serialized_parent_cardinality"] == 0
    assert row["disposition"] == "zero_parent_terminal_disposition"
    assert row["forced_parent_selection"] is False
    assert row["r_q_relationship_emitted"] is False


def test__multi_parent__retains_doc033_witness_without_selection(bundle):
    row = next(
        value
        for value in bundle["component"]["multi_parent_ambiguity_rows"]
        if value["component_anchor_occurrence_id"] == DOC033_MULTI_PARENT
    )
    assert row["component_kind"] == "source_context"
    assert row["serialized_parent_cardinality"] == 3
    assert row["raw_parent_category_ambiguity"] is True
    assert row["eligible_parent_category_ambiguity"] is True
    assert row["eligible_ineligible_mixed_ambiguity"] is False
    assert row["forced_parent_selection"] is False
    assert row["r_q_relationship_emitted"] is False


def test__component_sweep__is_corpus_exhaustive(bundle):
    artifact = bundle["sweeps"]
    assert artifact["component_parent_shape_count"] == 21_283
    assert artifact["serialized_parent_cardinality_counts"] == {
        "zero": 10_664,
        "one": 8_809,
        "multiple": 1_810,
    }
    assert artifact["raw_cross_category_multi_parent_count"] == 466
    assert artifact["eligible_cross_category_multi_parent_count"] == 462
    assert artifact["eligible_ineligible_mixed_multi_parent_count"] == 4
    assert artifact["ineligible_parent_reference_count"] == 34


def _tier2_candidate(
    source_id,
    canonical_id="psid-job-slot:job-a",
    slot_kind="context_only",
    *,
    eligible=True,
):
    return {
        "source_parent_occurrence_id": source_id,
        "resolved_canonical_parent_node_id": (
            canonical_id if eligible else None
        ),
        "eligible_parent": eligible,
        "derived_slot_kind": slot_kind if eligible else None,
        "support_proof_id": f"fixture-proof:{source_id}",
    }


def _tier2_member(member_id, candidates):
    return {
        "component_anchor_occurrence_id": member_id,
        "parent_candidate_rows": candidates,
    }


@pytest.mark.parametrize(
    ("members", "expected_disposition", "relationship_eligible"),
    (
        (
            [_tier2_member("component:zero", [])],
            "zero_parent_terminal_disposition",
            False,
        ),
        (
            [
                _tier2_member(
                    "component:ineligible",
                    [_tier2_candidate("parent:role", eligible=False)],
                )
            ],
            "zero_lawful_parent_terminal_disposition",
            False,
        ),
        (
            [
                _tier2_member(
                    "component:unique",
                    [_tier2_candidate("parent:job-a")],
                )
            ],
            "unique_parent_assignment",
            True,
        ),
        (
            [
                _tier2_member(
                    "component:alias-a",
                    [_tier2_candidate("parent:job-a-alias-1")],
                ),
                _tier2_member(
                    "component:alias-b",
                    [_tier2_candidate("parent:job-a-alias-2")],
                ),
            ],
            "unique_parent_assignment",
            True,
        ),
        (
            [
                _tier2_member(
                    "component:same-category-multi",
                    [
                        _tier2_candidate("parent:job-a-1"),
                        _tier2_candidate("parent:job-a-2"),
                    ],
                )
            ],
            "multi_parent_ambiguity_no_selection",
            False,
        ),
        (
            [
                _tier2_member(
                    "component:cross-category-multi",
                    [
                        _tier2_candidate("parent:job-a"),
                        _tier2_candidate(
                            "parent:farm",
                            "psid-job-slot:farm-aggregate",
                            "farm_aggregate",
                        ),
                    ],
                )
            ],
            "multi_parent_ambiguity_no_selection",
            False,
        ),
        (
            [
                _tier2_member("component:mixed-zero", []),
                _tier2_member(
                    "component:mixed-parent",
                    [_tier2_candidate("parent:job-a")],
                ),
            ],
            "multi_parent_ambiguity_no_selection",
            False,
        ),
        (
            [
                _tier2_member(
                    "component:conflict-a",
                    [_tier2_candidate("parent:job-a")],
                ),
                _tier2_member(
                    "component:conflict-b",
                    [_tier2_candidate("parent:job-b", "psid-job-slot:job-b")],
                ),
            ],
            "multi_parent_ambiguity_no_selection",
            False,
        ),
    ),
)
def test__tier2_component_class_fold__has_satisfiable_nonauthority_fixtures(
    members,
    expected_disposition,
    relationship_eligible,
):
    result = a12.fold_component_class_fixture("source_context", members)
    assert result["disposition"] == expected_disposition
    assert result["tier_2_relationship_arm_eligible"] is relationship_eligible
    assert result["forced_parent_selection"] is False
    assert result["r_q_relationship_emitted"] is False
    assert result["status"] == "prospective_fixture_nonauthority"


def test__tier2_component_class_fold__rejects_duplicate_source_candidates():
    candidate = _tier2_candidate("parent:duplicate")
    members = [_tier2_member("component:duplicate", [candidate, candidate])]
    with pytest.raises(a12.BuildError, match="duplicate source parent"):
        a12.fold_component_class_fixture("source_context", members)


def test__tier2_component_class_fold__rejects_resolved_ineligible_candidate():
    candidate = _tier2_candidate("parent:invalid", eligible=False)
    candidate["resolved_canonical_parent_node_id"] = "psid-job-slot:invented"
    members = [_tier2_member("component:invalid", [candidate])]
    with pytest.raises(a12.BuildError, match="ineligible candidate resolved"):
        a12.fold_component_class_fixture("source_context", members)


def test__predecessor_adjudication__keeps_all_candidates_as_seal_defects(
    bundle,
):
    artifact = bundle["predecessor"]
    assert artifact["doc036_aggregate_component_slot_count"] == 8
    assert artifact["defective_populated_local_proof_count"] == 42
    assert artifact["seal_defect_disposition_count"] == 50
    assert artifact["law_gap_disposition_count"] == 0


def test__predecessor_adjudication__reproduces_overlapping_projections(bundle):
    assert bundle["predecessor"]["defect_category_counts"] == {
        "touches_noncatalog_aggregate_endpoint": 28,
        "occurrence_derived_domain_crossing": 19,
        "corrected_catalog_domain_crossing": 19,
        "raw_node_domain_crossing": 18,
        "context_remuneration_mix": 15,
        "head_spouse_mix": 4,
    }


def test__pilot_artifacts__are_canonical_and_below_blob_limit():
    for path in a12._artifact_paths(a12.OUTPUT_ROOT).values():
        raw = path.read_bytes()
        assert len(raw) < 50_000_000
        assert raw == a12.canonical_bytes(
            a12.strict_json_loads(raw, str(path))
        )


def test__gate__pins_every_subordinate_artifact_raw_identity(bundle):
    rows = bundle["gate"]["artifact_identity_rows"]
    assert len(rows) == 6
    for row in rows:
        raw = a12.canonical_bytes(bundle[row["artifact_role"]])
        assert row["byte_size"] == len(raw)
        assert row["raw_sha256"] == hashlib.sha256(raw).hexdigest()


def test__gate__is_explicitly_pilot_nonauthority(bundle):
    gate = bundle["gate"]
    assert gate["certification_status"] == (
        "PILOT_NONAUTHORITY_CERTIFIES_NOTHING"
    )
    assert gate["tier_2_protocol_status"] == (
        "not_started_requires_ratification_and_predecessor_reseals"
    )
    assert gate["nonauthority_statement"]["q5_emitted"] is False
    assert gate["nonauthority_statement"]["r_q_emitted"] is False


def test__gate_identity_roles__must_be_an_exact_ordered_partition(bundle):
    candidate = copy.deepcopy(bundle)
    gate = copy.deepcopy(candidate["gate"])
    gate["artifact_identity_rows"] = [
        copy.deepcopy(gate["artifact_identity_rows"][0]) for _ in range(6)
    ]
    gate["artifact_identity_count"] = 6
    gate["artifact_identity_domain_sha256"] = a12._domain_sha(
        gate["artifact_identity_rows"]
    )
    candidate["gate"] = a12._reseal_artifact(gate)
    with pytest.raises(a12.BuildError, match="identity role partition"):
        a12.validate_bundle(candidate)


def test__transactional_writer__restores_every_prior_destination(
    bundle,
    tmp_path,
    monkeypatch,
):
    a12._write_bundle(bundle, tmp_path)
    paths = a12._artifact_paths(tmp_path)
    before = {key: path.read_bytes() for key, path in paths.items()}
    replacement_count = 0
    real_replace = os.replace

    def fail_second_staged_replacement(source, destination):
        nonlocal replacement_count
        if ".a12-stage-" in Path(source).name:
            replacement_count += 1
            if replacement_count == 2:
                raise OSError("injected middle replacement failure")
        return real_replace(source, destination)

    monkeypatch.setattr(a12.os, "replace", fail_second_staged_replacement)
    with pytest.raises(a12.BuildError, match="prior destinations restored"):
        a12._write_bundle(bundle, tmp_path)
    assert {key: path.read_bytes() for key, path in paths.items()} == before


def test__transactional_writer__removes_partial_first_publication(
    bundle,
    tmp_path,
    monkeypatch,
):
    replacement_count = 0
    real_replace = os.replace

    def fail_second_staged_replacement(source, destination):
        nonlocal replacement_count
        if ".a12-stage-" in Path(source).name:
            replacement_count += 1
            if replacement_count == 2:
                raise OSError("injected first-publication failure")
        return real_replace(source, destination)

    monkeypatch.setattr(a12.os, "replace", fail_second_staged_replacement)
    with pytest.raises(a12.BuildError, match="prior destinations restored"):
        a12._write_bundle(bundle, tmp_path)
    assert not any(
        path.exists() for path in a12._artifact_paths(tmp_path).values()
    )


def test__transactional_writer__rejects_existing_hard_link_aliases(
    bundle,
    tmp_path,
):
    a12._write_bundle(bundle, tmp_path)
    paths = list(a12._artifact_paths(tmp_path).values())
    paths[1].unlink()
    os.link(paths[0], paths[1])
    with pytest.raises(a12.BuildError, match="output inode collision"):
        a12._write_bundle(bundle, tmp_path)


def test__mutation_inventory__is_complete(rejected_mutations):
    assert rejected_mutations == EXPECTED_MUTATIONS


@pytest.mark.parametrize("mutation_name", EXPECTED_MUTATIONS)
def test__law_mutation__is_rejected(rejected_mutations, mutation_name):
    assert mutation_name in rejected_mutations
