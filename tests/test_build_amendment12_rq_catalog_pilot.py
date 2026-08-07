"""Tests for Amendment 12's pilot-only R_Q catalog-law artifacts."""

from __future__ import annotations

import copy
import hashlib
import os
import subprocess
import sys
from collections import Counter
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
DOC064_AGGREGATE_EVIDENCE = (
    "rq-local-repeat-alias-evidence:"
    "c0fdbc2f6b82371351dbcf266ab083dba8c20cce3298e283012ec5c618bca868"
)
DOC064_REPEAT = (
    "psid-questionnaire-occurrence:"
    "fa99afd9bc2e5f07056c445f6ade49fb32fa787c8579bb19b682c4081f477314"
)
DOC064_AGGREGATE_ENDPOINTS = {
    "psid-questionnaire-occurrence:"
    "bd1f034b1233871d46392ed774c48add7b56ddb0402fe79dcbf7d1c96551f6b7",
    "psid-questionnaire-occurrence:"
    "5c21cb5d94c4633ea60447057e515d060d87fcc099a08ad79d6ded471f86ed2a",
}
DOC064_REDIRECTION_LINEAGE_EVIDENCE = (
    "rq-local-repeat-alias-evidence:"
    "1d2d4b2f78a3a7db10584260b2edd900baa0b49ca81a44b37f93c6495c65b1ea"
)
DOC064_REDIRECTION_LINEAGE_INSTRUCTION = (
    "psid-questionnaire-occurrence:"
    "f72f26cb2f9abc4c7c3a3dc0d22ade4d357e65b6b3c4dd2234cd2013de6ec80c"
)
DOC066_REDIRECTION_EVIDENCE = (
    "rq-local-repeat-evidence:"
    "5977fa11c007f370ece29867bc0d2b6c5d492990396b50d86959b1ec5ec87927"
)
DOC066_REDIRECTION_INSTRUCTION = (
    "psid-questionnaire-occurrence:"
    "65f1752d0f6d39346c412c1d492e574979277aa6c78094f1ad79f0d53cf57452"
)
DOC066_G83_CONTEXT = (
    "psid-questionnaire-occurrence:"
    "adb71d63b14c075a96ab9ebe13b307cffa11870c6120fdf19d6c0be70b2e938b"
)
DOC066_G78_REMUNERATION = (
    "psid-questionnaire-occurrence:"
    "8d4e18a51c801cb05119741cdf0a16249c5f335f462134b10d388363d2ccd54c"
)
DOC074_REDIRECTION_LINEAGE_EVIDENCE = (
    "rq-local-repeat-alias-evidence:"
    "f3c17106bd1dc9ec836c1ae56e7a1a303a2e19e8bb888e0dc86028d28ce05ef3"
)
DOC074_REDIRECTION_LINEAGE_INSTRUCTION = (
    "psid-questionnaire-occurrence:"
    "b9cd9b8340c75927fdd98504bfe9663bad709f3d18a75db944b4f8281d0f8af7"
)

EXPECTED_MUTATIONS = (
    "pilot_slice_reordered",
    "pilot_claims_q5",
    "slice_integrity_q5_emitted_extra",
    "pilot_census_required_key_omitted",
    "pilot_census_extra_member",
    "pilot_census_parent_dispositions_forged",
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
    "aggregate_relation_row_omitted",
    "aggregate_relation_required_key_omitted",
    "aggregate_relation_alias_admitted",
    "aggregate_relation_equivalence_claimed",
    "aggregate_relation_universal_arm_false",
    "aggregate_relation_endpoint_domain_changed",
    "aggregate_relation_source_text_forged",
    "redirection_relation_row_omitted",
    "redirection_relation_subkind_changed",
    "redirection_relation_alias_admitted",
    "redirection_relation_equivalence_claimed",
    "redirection_relation_universal_arm_false",
    "redirection_relation_destination_changed",
    "redirection_relation_source_text_forged",
    "redirection_lineage_row_omitted",
    "redirection_law_gap_demoted_to_seal_defect",
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
    "redirection_evidence_reused_as_alias_support",
    "fragment_stop_promoted_to_alias_support",
    "semantic_alias_adjudication_record_forged",
    "composite_union_forgery",
    "nonledger_admission_without_semantic_decision",
    "continuation_rule_forgery",
    "component_class_sweep_row_omitted",
    "component_class_sweep_relationship_arm_flipped",
    "job_complement_sweep_row_omitted",
    "job_complement_coverage_arm_flipped",
    "exact_pair_support_label_forged",
    "catalog_only_job_source_member_forged",
    "doc036_law_gap_admitted",
    "doc036_component_slot_admitted",
    "doc036_source_occurrence_forged",
    "proof_defect_lawified",
    "proof_defect_action_removed",
    "proof_defect_row_omitted",
    "aggregate_law_gap_demoted_to_seal_defect",
    "aggregate_law_gap_source_projection_forged",
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


def test__amendment_12_design__starts_exactly_after_revision_13():
    raw = a12.DESIGN_PATH.read_bytes()
    suffix = raw[a12.DESIGN_PREFIX_BYTES :]
    heading = (
        b"\n## 26. AMENDMENT SECTION \xe2\x80\x94 Amendment 12: "
        b"pilot-first `R_Q` catalog laws\n"
    )
    assert suffix.startswith(heading)
    assert raw.count(b"## 26. AMENDMENT SECTION") == 1


def test__amendment_12_design__has_balanced_strict_fences():
    raw = a12.DESIGN_PATH.read_bytes()[a12.DESIGN_PREFIX_BYTES :]
    lines = raw.decode("utf-8").splitlines(keepends=True)
    active = None
    body = []
    json_block_count = 0
    for line_number, line in enumerate(lines, start=1):
        stripped = line.lstrip(" ")
        if active is None:
            if not stripped.startswith(("```", "~~~")):
                continue
            marker_character = stripped[0]
            marker_length = len(stripped) - len(
                stripped.lstrip(marker_character)
            )
            info = stripped[marker_length:].strip()
            active = (marker_character, marker_length, info, line_number)
            body = []
            continue
        marker_character, marker_length, info, opening_line = active
        marker = marker_character * marker_length
        if stripped.startswith(marker) and not stripped[len(marker) :].strip():
            if info in {"json", "JSON"}:
                json_block_count += 1
                a12.strict_json_loads(
                    "".join(body).encode("utf-8"),
                    f"Amendment-12 JSON fence at line {opening_line}",
                )
            active = None
            body = []
            continue
        body.append(line)
    assert active is None
    assert json_block_count == 0


def test__amendment_12_design__closes_laws_and_stays_inoperable():
    section = a12.DESIGN_PATH.read_text(encoding="utf-8").split(
        "## 26. AMENDMENT SECTION", 1
    )[1]
    required = (
        "psid-role-assignment:",
        "terminal_outside_r_q_domain_no_alias_admitted",
        "noncatalog_aggregate_or_repeated_instance_relation_no_alias",
        "authenticated_in_domain_exclusive_destination_relation_no_alias",
        "multi_parent_ambiguity_no_selection",
        "component_class_admission_sweep_rows",
        "catalog_only_job_complement_sweep_rows",
        "derived_class_complement_sweeps_v1.json",
        "hierarchy_annotation_authority",
        "A12-T2-R06",
    )
    for value in required:
        assert value in section
    assert (
        section.count("The complete prospective revision-14 comparator") == 1
    )
    assert section.count("This prospective amendment remains inoperable") == 1
    assert "PILOT_NONAUTHORITY_CERTIFIES_NOTHING" in section
    assert "no official\ncatalog, `R_Q`, H, Q5" in section


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
    assert artifact["outside_domain_relation_counts"] == {
        "explicit_cross_reference": 17,
        "explicit_repeat_instruction": 17,
    }
    assert artifact["outside_domain_document_counts"] == {
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


def test__noncatalog_aggregate_relations__reproduce_full_and_pilot_census(
    bundle,
):
    full_rows = bundle["sweeps"]["noncatalog_aggregate_relation_shape_rows"]
    pilot_rows = bundle["repeat"][
        "noncatalog_aggregate_relation_disposition_rows"
    ]
    assert len(full_rows) == 13
    assert len(pilot_rows) == 1
    assert Counter(row["relation"] for row in full_rows) == {
        "explicit_cross_reference": 8,
        "explicit_repeat_instruction": 5,
    }
    assert Counter(row["document_source_position"] for row in full_rows) == {
        7: 4,
        11: 1,
        35: 2,
        44: 1,
        48: 1,
        58: 1,
        61: 1,
        64: 1,
        68: 1,
    }
    assert pilot_rows[0]["document_source_position"] == 58


def test__noncatalog_aggregate_relation__retains_doc064_exact_bytes_no_alias(
    bundle,
):
    row = next(
        value
        for value in bundle["sweeps"][
            "noncatalog_aggregate_relation_shape_rows"
        ]
        if value["source_local_evidence_id"] == DOC064_AGGREGATE_EVIDENCE
    )
    assert row["source_instruction_occurrence_ids"] == [DOC064_REPEAT]
    assert row["source_instruction_matched_texts"] == [
        "one business, repeat questions G7a-G11b for each separate business "
        "up to 5."
    ]
    assert row["source_instruction_page_numbers"] == [22]
    assert row["source_instruction_utf8_byte_starts"] == [772]
    assert row["source_instruction_utf8_byte_ends"] == [847]
    assert (
        set(row["source_alias_anchor_occurrence_ids"])
        | set(row["source_canonical_anchor_occurrence_ids"])
        == DOC064_AGGREGATE_ENDPOINTS
    )
    assert row["endpoint_occurrence_kinds"] == [
        "business_aggregate_anchor",
        "business_aggregate_anchor",
    ]
    assert row["endpoint_raw_node_domains"] == ["aggregate", "aggregate"]
    assert row["alias_admitted"] is False
    assert row["occurrence_equivalence_claimed"] is False


def test__in_domain_redirection__retains_doc066_exact_bytes_no_alias(bundle):
    full_rows = bundle["sweeps"]["in_domain_redirection_shape_rows"]
    pilot_rows = bundle["repeat"]["in_domain_redirection_disposition_rows"]
    assert len(full_rows) == 5
    assert len(pilot_rows) == 2
    assert [row["document_source_position"] for row in full_rows] == [
        15,
        17,
        19,
        66,
        66,
    ]
    row = next(
        value
        for value in full_rows
        if value["source_instruction_occurrence_ids"]
        == [DOC066_REDIRECTION_INSTRUCTION]
    )
    assert row in pilot_rows
    assert row["document_source_position"] == 66
    assert row["source_local_evidence_ids"] == [DOC066_REDIRECTION_EVIDENCE]
    assert row["relation_subkind"] == a12.REDIRECTION_RELATION_SUBKIND
    assert row["relation"] == "explicit_cross_reference"
    assert row["source_instruction_occurrence_ids"] == [
        DOC066_REDIRECTION_INSTRUCTION
    ]
    assert row["source_instruction_matched_texts"] == [
        "should be included at G78, not here."
    ]
    assert row["source_instruction_matched_utf8_sha256s"] == [
        "447cf2de749df16746e08df868557004cf4aa3281f8a386fbd1b06f230cac7d3"
    ]
    assert row["source_instruction_page_numbers"] == [40]
    assert row["source_instruction_utf8_byte_starts"] == [2250]
    assert row["source_instruction_utf8_byte_ends"] == [2286]
    assert row["predecessor_alias_anchor_occurrence_ids"] == [
        DOC066_G83_CONTEXT
    ]
    assert row["predecessor_canonical_anchor_occurrence_ids"] == [
        DOC066_G78_REMUNERATION
    ]
    assert row["current_location_occurrence_id"] == DOC066_G83_CONTEXT
    assert row["destination_occurrence_ids"] == [DOC066_G78_REMUNERATION]
    assert row["endpoint_occurrence_kinds"] == [
        "context_anchor",
        "remuneration_component_anchor",
    ]
    assert row["endpoint_raw_node_domains"] == [
        "component_slot",
        "component_slot",
    ]
    assert row["endpoint_classifications"] == [
        "source_context",
        "source_remuneration_component",
    ]
    assert row["endpoint_printed_identifiers"] == ["G83.", "G78."]
    assert row["alias_admitted"] is False
    assert row["occurrence_equivalence_claimed"] is False
    assert row["universal_repeat_coverage_arm_satisfied"] is True
    grouped = next(
        value
        for value in pilot_rows
        if value["source_instruction_matched_texts"]
        == [
            "farming income should be listed at G2-G4 and not be repeated "
            "here; but if Head’s"
        ]
    )
    assert len(grouped["source_local_evidence_ids"]) == 2
    assert len(grouped["source_evidence_occurrence_id_arrays"]) == 2
    assert len(grouped["destination_occurrence_ids"]) == 2
    assert len(grouped["source_instruction_occurrence_ids"]) == 1


def test__component_cross_reference_sweep__exact_walks_structural_domain(
    bundle,
):
    sweep = bundle["sweeps"]
    assert {
        key: sweep[key]
        for key in (
            "explicit_cross_reference_evidence_count",
            "explicit_cross_reference_instruction_count",
            "complete_cross_reference_evidence_count",
            "complete_cross_reference_instruction_count",
            "in_domain_nonaggregate_cross_reference_evidence_count",
            "in_domain_nonaggregate_cross_reference_instruction_count",
            "wholly_in_domain_nonaggregate_cross_reference_evidence_count",
            "wholly_in_domain_nonaggregate_cross_reference_instruction_count",
            "component_cross_reference_evidence_count",
            "component_cross_reference_instruction_count",
            "binary_component_cross_reference_evidence_count",
            "binary_component_cross_reference_instruction_count",
        )
    } == {
        "explicit_cross_reference_evidence_count": 1_915,
        "explicit_cross_reference_instruction_count": 1_874,
        "complete_cross_reference_evidence_count": 309,
        "complete_cross_reference_instruction_count": 268,
        "in_domain_nonaggregate_cross_reference_evidence_count": 292,
        "in_domain_nonaggregate_cross_reference_instruction_count": 252,
        "wholly_in_domain_nonaggregate_cross_reference_evidence_count": 287,
        "wholly_in_domain_nonaggregate_cross_reference_instruction_count": 251,
        "component_cross_reference_evidence_count": 217,
        "component_cross_reference_instruction_count": 178,
        "binary_component_cross_reference_evidence_count": 205,
        "binary_component_cross_reference_instruction_count": 166,
    }
    rows = sweep["in_domain_component_cross_reference_sweep_rows"]
    assert len(rows) == 162
    assert sum(row["source_evidence_count"] for row in rows) == 195
    assert Counter(row["source_evidence_count"] for row in rows) == {
        1: 138,
        2: 15,
        3: 9,
    }
    assert all(
        set(row) == a12.IN_DOMAIN_COMPONENT_CROSS_REFERENCE_SWEEP_ROW_KEYS
        and row["structural_candidate_satisfied"] is True
        for row in rows
    )
    assert Counter(row["document_source_position"] for row in rows) == {
        1: 4,
        7: 5,
        10: 1,
        11: 10,
        13: 9,
        15: 13,
        17: 11,
        19: 11,
        35: 1,
        48: 2,
        52: 2,
        56: 35,
        58: 42,
        61: 1,
        66: 10,
        70: 5,
    }
    assert {
        key: sweep[key]
        for key in (
            "in_domain_component_cross_reference_sweep_count",
            "in_domain_component_cross_reference_sweep_edge_count",
            "in_domain_component_cross_reference_sweep_alias_instruction_count",
            "in_domain_component_cross_reference_sweep_alias_edge_count",
            "in_domain_component_cross_reference_sweep_alias_pair_count",
            "in_domain_component_cross_reference_sweep_redirection_instruction_count",
            "in_domain_component_cross_reference_sweep_redirection_edge_count",
            "in_domain_component_cross_reference_sweep_stop_instruction_count",
            "in_domain_component_cross_reference_sweep_stop_edge_count",
        )
    } == {
        "in_domain_component_cross_reference_sweep_count": 162,
        "in_domain_component_cross_reference_sweep_edge_count": 195,
        "in_domain_component_cross_reference_sweep_alias_instruction_count": 125,
        "in_domain_component_cross_reference_sweep_alias_edge_count": 147,
        "in_domain_component_cross_reference_sweep_alias_pair_count": 148,
        "in_domain_component_cross_reference_sweep_redirection_instruction_count": 5,
        "in_domain_component_cross_reference_sweep_redirection_edge_count": 6,
        "in_domain_component_cross_reference_sweep_stop_instruction_count": 32,
        "in_domain_component_cross_reference_sweep_stop_edge_count": 42,
    }
    assert {
        key: sweep[key]
        for key in (
            "pilot_in_domain_component_cross_reference_sweep_count",
            "pilot_in_domain_component_cross_reference_sweep_edge_count",
            "pilot_in_domain_component_cross_reference_sweep_alias_instruction_count",
            "pilot_in_domain_component_cross_reference_sweep_alias_edge_count",
            "pilot_in_domain_component_cross_reference_sweep_alias_pair_count",
            "pilot_in_domain_component_cross_reference_sweep_redirection_instruction_count",
            "pilot_in_domain_component_cross_reference_sweep_redirection_edge_count",
            "pilot_in_domain_component_cross_reference_sweep_stop_instruction_count",
            "pilot_in_domain_component_cross_reference_sweep_stop_edge_count",
        )
    } == {
        "pilot_in_domain_component_cross_reference_sweep_count": 91,
        "pilot_in_domain_component_cross_reference_sweep_edge_count": 123,
        "pilot_in_domain_component_cross_reference_sweep_alias_instruction_count": 69,
        "pilot_in_domain_component_cross_reference_sweep_alias_edge_count": 90,
        "pilot_in_domain_component_cross_reference_sweep_alias_pair_count": 91,
        "pilot_in_domain_component_cross_reference_sweep_redirection_instruction_count": 2,
        "pilot_in_domain_component_cross_reference_sweep_redirection_edge_count": 3,
        "pilot_in_domain_component_cross_reference_sweep_stop_instruction_count": 20,
        "pilot_in_domain_component_cross_reference_sweep_stop_edge_count": 30,
    }
    assert [
        row["in_domain_redirection_relation_disposition_id"]
        for row in rows
        if row["repeat_coverage_disposition"]
        == "admitted_exclusive_destination_redirection"
    ] == [
        row["in_domain_redirection_relation_disposition_id"]
        for row in sweep["in_domain_redirection_shape_rows"]
    ]
    assert {
        row["source_local_evidence_ids"][0]
        for row in rows
        if row["repeat_coverage_disposition"]
        == "disclosed_stop_no_redirection_semantics"
    } >= {
        "rq-local-repeat-evidence:"
        "c9b24cb9e34a7050a567093ee0f0500df3e221dd2afa9adfdaba02010fd31509",
        "rq-local-repeat-evidence:"
        "6ce1ef4653dfa56a49ff6baf30052132630c1ed47dfb246dcf38c1e63a24f83f",
        "rq-local-repeat-evidence:"
        "bb6ce7690468d1ef2e0d4a22bfa831bf9b81f7824db8a9dd59e06df44434c877",
        "rq-local-repeat-evidence:"
        "525a55100f92a4f6f05e156d9d784029ea29126e2c5374195545513375b36e8c",
        "rq-local-repeat-evidence:"
        "a06a1898968a9dc0d44b34bbd5ca9efc9bb856a56bde685815ff6621d1f82b39",
    }


def test__round_five_semantic_alias_ledger__exact_covers_structural_sweep(
    bundle,
):
    sweep = bundle["sweeps"]
    rows = sweep["in_domain_component_cross_reference_sweep_rows"]
    adjudication_ids = [row["semantic_alias_adjudication_id"] for row in rows]
    assert sweep["semantic_alias_adjudication_count"] == len(rows) == 162
    assert len(set(adjudication_ids)) == len(adjudication_ids)
    assert sweep["semantic_alias_adjudication_keyset_sha256"] == (
        a12._keyset_sha(adjudication_ids)
    )
    assert sweep["semantic_alias_adjudication_domain_sha256"] == (
        a12._domain_sha(rows)
    )

    dispositions = Counter(row["repeat_coverage_disposition"] for row in rows)
    assert dispositions == {
        "existing_alias_arm": 125,
        "admitted_exclusive_destination_redirection": 5,
        "disclosed_stop_no_redirection_semantics": 32,
    }
    assert sweep["semantic_alias_adjudication_outcome_counts"] == {
        "alias_instruction_count": 125,
        "alias_edge_count": 147,
        "alias_pair_count": 148,
        "redirection_instruction_count": 5,
        "redirection_edge_count": 6,
        "stop_instruction_count": 32,
        "stop_edge_count": 42,
    }
    assert Counter(row["source_instruction_fragment"] for row in rows) == {
        True: 48,
        False: 114,
    }
    assert Counter(row["tier_2_predecessor_ledger_note"] for row in rows) == {
        "round_three_reseal_ledger_already_covers_fragment": 4,
        "new_tier_2_reseal_required_for_incomplete_fragment": 10,
        "fragment_semantically_decisive_no_reseal_required": 34,
        "not_a_source_instruction_fragment": 114,
    }

    for row in rows:
        assert row["semantic_alias_adjudication_round"] == 5
        assert row["semantic_alias_ledger_member"] is True
        assert isinstance(row["semantic_alias_finding"], str)
        assert row["semantic_alias_finding"]
        assert isinstance(row["source_instruction_fragment"], bool)
        assert isinstance(row["tier_2_predecessor_seal_quality_issue"], bool)
        assert isinstance(row["tier_2_predecessor_ledger_note"], str)
        assert row["tier_2_predecessor_ledger_note"]
        if not row["source_instruction_fragment"]:
            assert row["tier_2_predecessor_seal_quality_issue"] is False
            assert row["tier_2_predecessor_ledger_note"] == (
                "not_a_source_instruction_fragment"
            )
        alias_member = row["repeat_coverage_disposition"] == (
            "existing_alias_arm"
        )
        assert (
            row["named_instruction_import_or_occurrence_equivalence_proved"]
            is alias_member
        )
        assert row["occurrence_equivalence_proved"] is (
            alias_member and not row["pairwise_decomposition_required"]
        )
        assert row["approved_pair_count"] >= len(
            row["valid_alias_arm_evidence_ids"]
        )
        if alias_member:
            assert row["valid_alias_arm_evidence_ids"]
            assert set(row["valid_alias_arm_evidence_ids"]) <= set(
                row["source_local_evidence_ids"]
            )
        else:
            assert row["valid_alias_arm_evidence_ids"] == []

        instruction_bytes = row["source_instruction_matched_text"].encode()
        assert row["source_instruction_matched_utf8_sha256"] == (
            hashlib.sha256(instruction_bytes).hexdigest()
        )
        assert row["source_instruction_utf8_byte_end"] - row[
            "source_instruction_utf8_byte_start"
        ] == len(instruction_bytes)
        assert row["source_instruction_page_number"] > 0

        for texts, digests, pages, starts, ends in zip(
            row["source_endpoint_matched_text_arrays"],
            row["source_endpoint_matched_utf8_sha256_arrays"],
            row["source_endpoint_page_number_arrays"],
            row["source_endpoint_utf8_byte_start_arrays"],
            row["source_endpoint_utf8_byte_end_arrays"],
            strict=True,
        ):
            for text, digest, page, start, end in zip(
                texts, digests, pages, starts, ends, strict=True
            ):
                source_bytes = text.encode()
                assert digest == hashlib.sha256(source_bytes).hexdigest()
                assert end - start == len(source_bytes)
                assert page > 0


def test__round_five_semantic_gate__exact_covers_every_alias_candidate(
    bundle,
):
    sweep = bundle["sweeps"]
    rows = sweep["alias_evidence_semantic_adjudication_rows"]
    row_ids = [row["semantic_alias_evidence_adjudication_id"] for row in rows]
    evidence_ids = [row["source_local_evidence_id"] for row in rows]
    embedded_pairs = [
        pair for row in rows for pair in row["approved_pair_rows"]
    ]
    pair_ids = [
        pair["semantic_alias_pair_adjudication_id"] for pair in embedded_pairs
    ]

    assert sweep["alias_evidence_semantic_adjudication_count"] == 265
    assert sweep["ca41663_alias_evidence_adjudication_count"] == 262
    assert sweep["round_five_continuation_restoration_count"] == 3
    assert len(rows) == len(set(row_ids)) == len(set(evidence_ids)) == 265
    assert all(
        set(row) == a12.ALIAS_EVIDENCE_SEMANTIC_ADJUDICATION_ROW_KEYS
        and row["semantic_adjudication_round"] == 5
        and row["structural_filter_satisfied"] is True
        for row in rows
    )
    assert sweep["alias_evidence_semantic_adjudication_keyset_sha256"] == (
        a12._keyset_sha(row_ids)
    )
    assert sweep["alias_evidence_semantic_adjudication_domain_sha256"] == (
        a12._domain_sha(rows)
    )
    assert sweep["alias_evidence_semantic_candidate_origin_counts"] == {
        "ca41663_nonledger_bypass_adjudication": 108,
        "ca41663_structural_ledger_admission": 154,
        "round_five_continuation_restoration": 3,
    }
    assert sweep["alias_evidence_semantic_decision_counts"] == {
        "approved_pairwise_decomposition": 19,
        "approved_pairwise_typed_projection": 41,
        "approved_single_pair": 181,
        "disclosed_stop": 24,
    }
    assert sweep["approved_alias_evidence_count"] == 241
    assert sweep["disclosed_stop_alias_evidence_count"] == 24
    assert Counter(bool(row["approved_pair_rows"]) for row in rows) == {
        True: 241,
        False: 24,
    }
    assert sweep["approved_alias_pair_rows"] == embedded_pairs
    assert sweep["approved_alias_pair_count"] == len(pair_ids) == 270
    assert len(set(pair_ids)) == 270
    assert sweep["approved_alias_pair_keyset_sha256"] == a12._keyset_sha(
        pair_ids
    )
    assert sweep["approved_alias_pair_domain_sha256"] == a12._domain_sha(
        embedded_pairs
    )
    assert sweep["occurrence_closure_alias_pair_count"] == 228
    assert sweep["typed_projection_alias_pair_count"] == 42

    assert sweep["alias_semantic_input_identity_rows"] == [
        {
            "path": "scripts/amendment12_alias_semantic_adjudication_v1.json",
            "byte_size": 74_773,
            "raw_sha256": (
                "733f6c88ca19226db713f437ccaed8e8dfe781957f04e2f164b0dfdedb8e9870"
            ),
        },
        {
            "path": (
                "scripts/amendment12_composite_import_adjudication_v1.json"
            ),
            "byte_size": 131_604,
            "raw_sha256": (
                "47f21d24be95822ba284f10f6a25d8b645cd938d2008bc7762080e2be7d370ff"
            ),
        },
    ]


def test__round_five_nonledger_gate__adjudicates_all_108_bypass_rows(
    bundle,
):
    specification, identity = a12._nonledger_alias_semantic_specification()
    rows = [
        row
        for row in bundle["sweeps"][
            "alias_evidence_semantic_adjudication_rows"
        ]
        if row["candidate_origin"] == "ca41663_nonledger_bypass_adjudication"
    ]
    assert identity == {
        "path": "scripts/amendment12_alias_semantic_adjudication_v1.json",
        "byte_size": 74_773,
        "raw_sha256": (
            "733f6c88ca19226db713f437ccaed8e8dfe781957f04e2f164b0dfdedb8e9870"
        ),
    }
    assert specification["nonledger_census"] == {
        "approved_evidence_count": 94,
        "approved_instructionless_evidence_count": 2,
        "approved_nonrepeat_instruction_count": 2,
        "approved_pair_count": 122,
        "approved_pairwise_decomposition_evidence_count": 19,
        "approved_repeat_instruction_count": 87,
        "approved_single_pair_evidence_count": 75,
        "ca41663_admitted_nonledger_evidence_count": 108,
        "ca41663_admitted_structural_ledger_evidence_count": 154,
        "ca41663_total_admitted_alias_evidence_count": 262,
        "disclosed_stop_evidence_count": 14,
        "pilot_approved_pair_count": 22,
        "pilot_approved_pairwise_decomposition_evidence_count": 0,
        "pilot_approved_repeat_instruction_count": 17,
        "pilot_approved_single_pair_evidence_count": 22,
        "pilot_disclosed_stop_evidence_count": 3,
        "pilot_evidence_count": 25,
        "pilot_stopped_repeat_instruction_count": 3,
        "stopped_repeat_instruction_count": 14,
    }
    assert len(rows) == 108
    assert Counter(row["decision"] for row in rows) == {
        "approved_single_pair": 75,
        "approved_pairwise_decomposition": 19,
        "disclosed_stop": 14,
    }
    assert sum(bool(row["approved_pair_rows"]) for row in rows) == 94
    assert sum(not row["approved_pair_rows"] for row in rows) == 14
    assert sum(row["approved_pair_count"] for row in rows) == 122
    assert [row["source_local_evidence_id"] for row in rows] == (
        specification["ordered_nonledger_candidate_evidence_ids"]
    )

    witness = next(
        row
        for row in rows
        if row["source_local_evidence_id"] == "rq-local-repeat-alias-evidence:"
        "f05c18c7c4061be215d08d28c6b8ad79ac45c10c85f0ebac801bd538b6ec91ff"
    )
    assert witness["source_instruction_matched_texts"] == [
        "G2,3,4   See Section D, Questions D2-3 , 3a for objectives ."
    ]
    assert witness["decision"] == "approved_pairwise_decomposition"
    assert [
        (
            pair["alias_endpoint_matched_text"],
            pair["canonical_endpoint_matched_text"],
        )
        for pair in witness["approved_pair_rows"]
    ] == [
        (
            "G3.   What kind of work did she do?",
            "D2.   What is your main occupation?       "
            "(What sort of work do you do?)",
        ),
        (
            "G4.   What kind of business is that in?",
            "D3a. What kind of business is that in?",
        ),
    ]


def test__round_five_composite_imports__decompose_without_union_or_stop(
    bundle,
):
    specification, identity = a12._composite_import_semantic_specification()
    assert identity == {
        "path": "scripts/amendment12_composite_import_adjudication_v1.json",
        "byte_size": 131_604,
        "raw_sha256": (
            "47f21d24be95822ba284f10f6a25d8b645cd938d2008bc7762080e2be7d370ff"
        ),
    }
    assert specification["census"] == {
        "decomposed_instruction_group_count": 19,
        "decomposed_instruction_group_with_partial_stop_count": 6,
        "full_stop_instruction_group_count": 2,
        "instruction_group_count": 21,
        "pair_producing_evidence_with_multiple_pairs_count": 1,
        "pair_producing_source_evidence_count": 41,
        "pure_decomposed_instruction_group_count": 13,
        "source_evidence_count": 51,
        "stop_source_evidence_count": 10,
        "typed_projection_pair_count": 42,
    }
    decisions = specification["instruction_decisions"]
    assert Counter(row["disposition"] for row in decisions) == {
        "pairwise_decomposition": 13,
        "pairwise_decomposition_with_disclosed_stops": 6,
        "disclosed_stop": 2,
    }
    assert {
        row["sweep_row_index"]
        for row in decisions
        if row["disposition"] == "disclosed_stop"
    } == {103, 140}
    assert sum(len(row["typed_projection_pairs"]) for row in decisions) == 42
    assert sum(len(row["stop_evidence_rows"]) for row in decisions) == 10

    composite_evidence_ids = {
        evidence_id
        for row in decisions
        for evidence_id in row["source_evidence_ids"]
    }
    semantic_rows = [
        row
        for row in bundle["sweeps"][
            "alias_evidence_semantic_adjudication_rows"
        ]
        if row["source_local_evidence_id"] in composite_evidence_ids
    ]
    assert len(semantic_rows) == len(composite_evidence_ids) == 51
    assert Counter(row["decision"] for row in semantic_rows) == {
        "approved_pairwise_typed_projection": 41,
        "disclosed_stop": 10,
    }
    typed_pairs = [
        pair for row in semantic_rows for pair in row["approved_pair_rows"]
    ]
    assert len(typed_pairs) == 42
    assert all(
        pair["pair_kind"] == "typed_instruction_import_projection"
        and pair["class_closure_eligible"] is False
        and pair["typed_projection_union_prohibited"] is True
        and pair["alias_question_selector"]
        and pair["canonical_question_selector"]
        for pair in typed_pairs
    )
    comparable_stop = next(
        row for row in decisions if row["sweep_row_index"] == 140
    )
    assert all(
        stop["finding_code"]
        == "comparability_does_not_prove_equivalence_or_pairing"
        and "comparable questions" in stop["finding"]
        for stop in comparable_stop["stop_evidence_rows"]
    )


def test__round_five_continuations__use_one_exact_whitespace_rule(bundle):
    sweep = bundle["sweeps"]
    rows = [
        row
        for row in sweep["alias_evidence_semantic_adjudication_rows"]
        if row["round_five_continuation_restoration"]
    ]
    assert len(rows) == 3
    assert {
        row["source_instruction_occurrence_ids"][0] for row in rows
    } == set(a12.CONTINUATION_RESTORATION_INSTRUCTION_IDS)
    structural_by_instruction = {
        row["source_instruction_occurrence_id"]: row
        for row in sweep["in_domain_component_cross_reference_sweep_rows"]
    }
    for row in rows:
        citation = row["continuation_composition_citation"]
        instruction_id = row["source_instruction_occurrence_ids"][0]
        assert (
            citation["composition_rule"] == a12.CONTINUATION_COMPOSITION_RULE
        )
        assert citation["continuation_occurrence_id"] == instruction_id
        assert citation["gap_is_whitespace_only"] is True
        assert citation["gap_text"].isspace()
        assert (
            citation["gap_utf8_byte_start"]
            == citation["leading_utf8_byte_end"]
        )
        assert (
            citation["gap_utf8_byte_end"]
            == citation["continuation_utf8_byte_start"]
        )
        assert (
            citation["gap_utf8_sha256"]
            == hashlib.sha256(citation["gap_text"].encode()).hexdigest()
        )
        assert (
            citation["combined_utf8_sha256"]
            == hashlib.sha256(citation["combined_text"].encode()).hexdigest()
        )
        assert row["approved_pair_count"] == 1
        assert row["approved_pair_rows"][0]["pairing_basis_code"] == (
            a12.CONTINUATION_COMPOSITION_RULE
        )
        assert (
            structural_by_instruction[instruction_id][
                "continuation_composition_citation"
            ]
            == citation
        )


def test__round_five_semantic_alias_ledger__stops_known_false_aliases(
    bundle,
):
    rows = bundle["sweeps"]["in_domain_component_cross_reference_sweep_rows"]
    by_instruction = {
        row["source_instruction_occurrence_id"]: row for row in rows
    }
    expected = {
        "psid-questionnaire-occurrence:"
        "6ed791445d19c2af492a3571d5a0d4b7f635eaeaabb5f5f3abf5424b8d04c03a": {
            "document_source_position": 15,
            "source_local_evidence_ids": [
                "rq-local-repeat-alias-evidence:"
                "04d8d08f5721c5c76eafc32cea71b6187c6634e84a4d940328553b8c19724d89"
            ],
            "source_instruction_matched_text": (
                "Make sure if an amount i s gi ven for both H7 and H8 that i t "
                "i s not the\n      same figure recorded twice . Probe to f ind "
                "out in these cases ."
            ),
            "source_instruction_matched_utf8_sha256": (
                "c32f51ff9f858256afc3a954bbbf0282068dd31417c7ce26bf574dd8b5d3485e"
            ),
            "source_instruction_page_number": 40,
            "source_instruction_utf8_byte_start": 1509,
            "source_instruction_utf8_byte_end": 1653,
            "source_endpoint_printed_identifier_arrays": [["I-18", "I-17"]],
            "semantic_alias_finding": (
                "anti_duplication_instruction_disproves_occurrence_"
                "equivalence"
            ),
            "source_instruction_fragment": False,
        },
        "psid-questionnaire-occurrence:"
        "8b9c6613b23e83dd55af058542e6aec3be341440397c632d91c1b74f073291dd": {
            "document_source_position": 17,
            "source_local_evidence_ids": [
                "rq-local-repeat-alias-evidence:"
                "ed65f56aae0cef0e9f3254bf30bf1f22a8b8b1a0bb8769fdcd3e7e3ed64920ca"
            ],
            "source_instruction_matched_text": (
                "Make sure if an amount is given for both H7 and H8 that it "
                "is not"
            ),
            "source_instruction_matched_utf8_sha256": (
                "638ff7f5607248b60959d5b804b269e5dfbdac96275ef8a8fe135372ba8b237e"
            ),
            "source_instruction_page_number": 46,
            "source_instruction_utf8_byte_start": 844,
            "source_instruction_utf8_byte_end": 909,
            "source_endpoint_printed_identifier_arrays": [["H8", "H7"]],
            "semantic_alias_finding": (
                "incomplete_fragment_does_not_prove_occurrence_equivalence"
            ),
            "source_instruction_fragment": True,
            "tier_2_predecessor_seal_quality_issue": True,
            "tier_2_predecessor_ledger_note": (
                "new_tier_2_reseal_required_for_incomplete_fragment"
            ),
        },
        "psid-questionnaire-occurrence:"
        "124dd16396afb1eb91cdefdaf057c3e2450ca445b7a8ea5f788d472db80cc1ba": {
            "document_source_position": 19,
            "source_local_evidence_ids": [
                "rq-local-repeat-alias-evidence:"
                "c4dd9293833e5a1b735bf70a8362777e193d1ff6c5ad216d09223ed63b4b06dd"
            ],
            "source_instruction_matched_text": (
                "Make sure if an amount is given for both H7 and H8 that it "
                "is not\nthe same figure recorded twice. Probe to find out in "
                "these cases."
            ),
            "source_instruction_matched_utf8_sha256": (
                "296e1c0d479e1fc24f6a253e31358fbd8b1ba3f59dbdb84822f934c603912b55"
            ),
            "source_instruction_page_number": 48,
            "source_instruction_utf8_byte_start": 846,
            "source_instruction_utf8_byte_end": 977,
            "source_endpoint_printed_identifier_arrays": [[None, "H7"]],
            "semantic_alias_finding": (
                "anti_duplication_instruction_disproves_occurrence_"
                "equivalence"
            ),
            "source_instruction_fragment": False,
        },
        "psid-questionnaire-occurrence:"
        "2731f348724837fcf2e8be8fac3d039705671d63b5b4496b18c0a82694395e2f": {
            "document_source_position": 66,
            "source_local_evidence_ids": [
                "rq-local-repeat-evidence:"
                "ea4aa070f2995a7a5d96aae117c086cd870eb75a940ee4a520ce8ad53e98bcf3",
                "rq-local-repeat-evidence:"
                "a01ab00d46676b41aa5c4c7d5a8d0c253909acf838ada6d75e7f635ef81bf361",
            ],
            "source_instruction_matched_text": (
                "G4.        Farm income equals total receipts (G2) minus "
                "operating expenses (G3). Do the"
            ),
            "source_instruction_matched_utf8_sha256": (
                "5460f22809e16521009c10578146b19c2c82eaf3a215866bb216056d491d13a0"
            ),
            "source_instruction_page_number": 30,
            "source_instruction_utf8_byte_start": 106,
            "source_instruction_utf8_byte_end": 193,
            "source_endpoint_printed_identifier_arrays": [
                ["G4.", "G2."],
                ["G4.", "G3."],
            ],
            "semantic_alias_finding": (
                "arithmetic_composition_does_not_prove_occurrence_"
                "equivalence"
            ),
            "source_instruction_fragment": True,
            "tier_2_predecessor_seal_quality_issue": False,
            "tier_2_predecessor_ledger_note": (
                "fragment_semantically_decisive_no_reseal_required"
            ),
        },
        "psid-questionnaire-occurrence:"
        "5eb05b791f0abad829debc9863433e0a8e7bd254aa18ac51b6c750caa48bb46a": {
            "document_source_position": 66,
            "source_local_evidence_ids": [
                "rq-local-repeat-evidence:"
                "ed0c801ba48f634dac9e766d90116aab30f533f82aed9846af81aa739b059aba"
            ],
            "source_instruction_matched_text": (
                "If an amount is given for both G11b and G13, probe to be "
                "sure that it is not the"
            ),
            "source_instruction_matched_utf8_sha256": (
                "0c923d7121f8b7a02d951ac9c5d8dc7900a2818233eea9c69452c0e8f4dca024"
            ),
            "source_instruction_page_number": 31,
            "source_instruction_utf8_byte_start": 1795,
            "source_instruction_utf8_byte_end": 1875,
            "source_endpoint_printed_identifier_arrays": [["G13.", "G11b."]],
            "semantic_alias_finding": (
                "incomplete_fragment_does_not_prove_occurrence_equivalence"
            ),
            "source_instruction_fragment": True,
            "tier_2_predecessor_seal_quality_issue": True,
            "tier_2_predecessor_ledger_note": (
                "new_tier_2_reseal_required_for_incomplete_fragment"
            ),
        },
    }
    for instruction_id, citation in expected.items():
        row = by_instruction[instruction_id]
        assert {key: row[key] for key in citation} == citation
        assert row["repeat_coverage_disposition"] == (
            "disclosed_stop_no_redirection_semantics"
        )
        assert row["semantic_alias_ledger_member"] is True
        assert row["occurrence_equivalence_proved"] is False
        assert row["valid_alias_arm_evidence_ids"] == []
        assert row["semantic_alias_finding"]


def test__round_five_fragment_stops__carry_tier_2_seal_quality_notes(bundle):
    rows = bundle["sweeps"]["in_domain_component_cross_reference_sweep_rows"]
    fragments = [row for row in rows if row["source_instruction_fragment"]]
    assert len(fragments) == 48
    known_incomplete_stops = {
        "psid-questionnaire-occurrence:"
        "8b9c6613b23e83dd55af058542e6aec3be341440397c632d91c1b74f073291dd",
        "psid-questionnaire-occurrence:"
        "5eb05b791f0abad829debc9863433e0a8e7bd254aa18ac51b6c750caa48bb46a",
    }
    assert known_incomplete_stops <= {
        row["source_instruction_occurrence_id"] for row in fragments
    }
    assert all(
        isinstance(row["tier_2_predecessor_seal_quality_issue"], bool)
        and isinstance(row["tier_2_predecessor_ledger_note"], str)
        and row["tier_2_predecessor_ledger_note"]
        for row in fragments
    )
    assert Counter(
        row["tier_2_predecessor_seal_quality_issue"] for row in fragments
    ) == {True: 14, False: 34}
    assert Counter(
        row["tier_2_predecessor_ledger_note"] for row in fragments
    ) == {
        "round_three_reseal_ledger_already_covers_fragment": 4,
        "new_tier_2_reseal_required_for_incomplete_fragment": 10,
        "fragment_semantically_decisive_no_reseal_required": 34,
    }
    for row in fragments:
        if row["source_instruction_occurrence_id"] in known_incomplete_stops:
            assert row["repeat_coverage_disposition"] == (
                "disclosed_stop_no_redirection_semantics"
            )
            assert row["occurrence_equivalence_proved"] is False
            assert row["tier_2_predecessor_seal_quality_issue"] is True


def test__lexical_redirection_lineage__remains_a_secondary_regression(bundle):
    sweep = bundle["sweeps"]
    rows = sweep["exclusive_destination_redirection_lineage_rows"]
    assert sweep["repeat_instruction_text_scan_count"] == 2_460
    assert sweep["literal_cross_reference_instruction_count"] == 8
    assert len(rows) == 45
    assert sum(len(row["source_local_evidence_ids"]) for row in rows) == 46
    assert Counter(row["source_text_shape_kind"] for row in rows) == {
        "business_owner_pay_exclusive_placement": 16,
        "primary_farm_income_exclusive_placement": 26,
        "labor_income_g78_exclusive_placement": 3,
    }
    g78_rows = [
        row
        for row in rows
        if row["source_text_shape_kind"]
        == "labor_income_g78_exclusive_placement"
    ]
    assert [row["document_source_position"] for row in g78_rows] == [
        64,
        66,
        74,
    ]
    assert [row["source_local_evidence_ids"] for row in g78_rows] == [
        [DOC064_REDIRECTION_LINEAGE_EVIDENCE],
        [DOC066_REDIRECTION_EVIDENCE],
        [DOC074_REDIRECTION_LINEAGE_EVIDENCE],
    ]
    assert [row["source_instruction_occurrence_id"] for row in g78_rows] == [
        DOC064_REDIRECTION_LINEAGE_INSTRUCTION,
        DOC066_REDIRECTION_INSTRUCTION,
        DOC074_REDIRECTION_LINEAGE_INSTRUCTION,
    ]
    admitted = [
        row for row in rows if row["in_domain_redirection_arm_eligible"]
    ]
    stopped = [
        row
        for row in rows
        if row["lineage_disposition"].startswith("disclosed_stop_")
    ]
    aggregate = [
        row
        for row in rows
        if row["lineage_disposition"]
        == "covered_by_existing_aggregate_nonalias_subkind"
    ]
    assert len(admitted) == 5
    assert len(aggregate) == 2
    assert len(stopped) == 38
    assert (
        sweep["exclusive_destination_redirection_lineage_admitted_count"] == 5
    )
    assert (
        sweep["exclusive_destination_redirection_lineage_aggregate_count"] == 2
    )
    assert sweep["exclusive_destination_redirection_lineage_stop_count"] == 38
    assert (
        sweep["exclusive_destination_redirection_lineage_mixed_stop_count"]
        == 3
    )
    assert (
        sweep[
            "exclusive_destination_redirection_lineage_incomplete_stop_count"
        ]
        == 35
    )
    assert {
        row["in_domain_redirection_relation_disposition_id"]
        for row in admitted
    } == {
        row["in_domain_redirection_relation_disposition_id"]
        for row in sweep["in_domain_redirection_shape_rows"]
    }


def test__five_repeat_dispositions__are_disjoint_and_fail_closed(
    bundle,
):
    sweep = bundle["sweeps"]
    aggregate_instruction_ids = {
        row["source_instruction_occurrence_ids"][0]
        for row in sweep["noncatalog_aggregate_relation_shape_rows"]
    }
    outside_instruction_ids = {
        row["source_instruction_occurrence_id"]
        for row in sweep["outside_domain_repeat_shape_rows"]
    }
    redirection_instruction_ids = {
        row["source_instruction_occurrence_ids"][0]
        for row in sweep["in_domain_redirection_shape_rows"]
    }
    assert aggregate_instruction_ids.isdisjoint(outside_instruction_ids)
    assert redirection_instruction_ids.isdisjoint(outside_instruction_ids)
    assert redirection_instruction_ids.isdisjoint(aggregate_instruction_ids)
    assert sweep["repeat_coverage_census"] == {
        "repeat_occurrence_count": 2_460,
        "valid_direct_proof_instruction_count": 212,
        "outside_domain_instruction_count": 34,
        "noncatalog_aggregate_relation_instruction_count": 13,
        "in_domain_redirection_instruction_count": 5,
        "in_domain_nonalias_relation_instruction_count": 18,
        "incompatible_proof_instruction_count": 64,
        "valid_and_incompatible_instruction_overlap_count": 0,
        "lawful_repeat_coverage_multiple_arm_instruction_count": 0,
        "disclosed_stop_instruction_count": 2_196,
        "otherwise_unresolved_instruction_count": 2_132,
    }
    assert bundle["gate"]["overall_repeat_catalog_coverage_status"] == (
        "fail_closed_unresolved_rows_remain"
    )


def test__repeat_gate__does_not_hide_other_unresolved_instructions(bundle):
    census = bundle["gate"]["pilot_census"]
    assert census["valid_direct_proof_instruction_count"] == 86
    assert census["outside_domain_instruction_count"] == 34
    assert census["noncatalog_aggregate_relation_instruction_count"] == 1
    assert census["in_domain_redirection_instruction_count"] == 2
    assert census["in_domain_nonalias_relation_instruction_count"] == 3
    assert census["incompatible_proof_instruction_count"] == 25
    assert census["lawful_repeat_coverage_multiple_arm_instruction_count"] == 0
    assert census["disclosed_stop_instruction_count"] == 253
    assert census["otherwise_unresolved_instruction_count"] == 228
    assert 376 == 86 + 34 + 1 + 2 + 253
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


def test__derived_class_sweeps__exact_cover_both_source_domains(bundle):
    artifact = bundle["derived"]
    assert artifact["component_class_admission_sweep_count"] == 19_585
    assert artifact["component_class_member_occurrence_count"] == 21_283
    assert artifact["catalog_only_job_complement_sweep_count"] == 12_378
    assert artifact["job_class_member_occurrence_count"] == 14_326
    assert artifact["component_class_candidate_disposition_counts"] == {
        "multi_parent_ambiguity_no_selection": 1_980,
        "unique_parent_assignment": 7_963,
        "zero_lawful_parent_terminal_disposition": 30,
        "zero_parent_terminal_disposition": 9_612,
    }


def test__derived_class_sweeps__exercise_both_alias_proof_forms(bundle):
    artifact = bundle["derived"]
    assert artifact["component_alias_support_origin_counts"] == {
        "exact_pair_equality_sweep": 746,
        "sealed_local_evidence": 143,
    }
    assert artifact["job_alias_support_origin_counts"] == {
        "exact_pair_equality_sweep": 647,
        "sealed_local_evidence": 75,
    }


def test__derived_class_sweeps__construct_aliases_only_from_alias_arm(
    bundle,
):
    sweep = bundle["sweeps"]
    structural_rows = sweep["in_domain_component_cross_reference_sweep_rows"]
    structural_evidence_ids = {
        evidence_id
        for row in structural_rows
        for evidence_id in row["source_local_evidence_ids"]
    }
    structural_alias_evidence_ids = {
        evidence_id
        for row in structural_rows
        if row["repeat_coverage_disposition"] == "existing_alias_arm"
        for evidence_id in row["valid_alias_arm_evidence_ids"]
    }
    semantic_rows_by_evidence = {
        row["source_local_evidence_id"]: row
        for row in sweep["alias_evidence_semantic_adjudication_rows"]
    }
    closure_evidence_ids = {
        row["source_local_evidence_id"]
        for row in sweep["approved_alias_pair_rows"]
        if row["class_closure_eligible"]
    }
    typed_projection_evidence_ids = {
        row["source_local_evidence_id"]
        for row in sweep["approved_alias_pair_rows"]
        if row["typed_projection_union_prohibited"]
    }
    stopped_evidence_ids = {
        evidence_id
        for evidence_id, row in semantic_rows_by_evidence.items()
        if row["approved_pair_count"] == 0
    }
    redirection_evidence_ids = {
        evidence_id
        for row in structural_rows
        if row["repeat_coverage_disposition"]
        == "admitted_exclusive_destination_redirection"
        for evidence_id in row["source_local_evidence_ids"]
    }

    sealed_support_ids = {
        support["source_local_evidence_id"]
        for key in (
            "component_class_admission_sweep_rows",
            "catalog_only_job_complement_sweep_rows",
        )
        for row in bundle["derived"][key]
        for support in row["alias_support_rows"]
        if support["support_origin"] == "sealed_local_evidence"
    }
    assert structural_evidence_ids & sealed_support_ids == (
        structural_alias_evidence_ids & closure_evidence_ids
    )
    assert sealed_support_ids <= closure_evidence_ids
    assert stopped_evidence_ids.isdisjoint(sealed_support_ids)
    assert typed_projection_evidence_ids.isdisjoint(sealed_support_ids)
    assert redirection_evidence_ids.isdisjoint(sealed_support_ids)
    assert all(
        semantic_rows_by_evidence[evidence_id]["approved_pair_count"] > 0
        for evidence_id in sealed_support_ids
    )

    derived_classes = [
        set(row[member_key])
        for row_key, member_key in (
            (
                "component_class_admission_sweep_rows",
                "component_class_member_occurrence_ids",
            ),
            (
                "catalog_only_job_complement_sweep_rows",
                "job_class_member_occurrence_ids",
            ),
        )
        for row in bundle["derived"][row_key]
    ]
    for pair in sweep["approved_alias_pair_rows"]:
        if not pair["typed_projection_union_prohibited"]:
            continue
        pair_members = {
            pair["alias_occurrence_id"],
            pair["canonical_occurrence_id"],
        }
        assert all(
            not pair_members <= derived_class
            for derived_class in derived_classes
        )
    assert {
        "rq-local-repeat-alias-evidence:"
        "d703ee09088e3789c6c77b9a01bc7350062cb744295cce86dd3a0722317cbe2b",
        "rq-local-repeat-alias-evidence:"
        "390e91405eab59354cf25f3deb7cb02dfa5924c655c33272fd226d2f5ba7117f",
        "rq-local-repeat-alias-evidence:"
        "2d00c4bc66f3191d36f783de3a709adba07c3eb894a054d971d72d64ba2870af",
        "rq-local-repeat-evidence:"
        "1851a59e23285cabe0fb25977286cccd786152885b0c8f60bb29517a21f61e23",
        "rq-local-repeat-evidence:"
        "191167ca76ad47c4334c5f3b014abd7d520944d9faadca4b4aa80e52766cd7e2",
    } <= redirection_evidence_ids


def test__derived_job_complement__is_a_complete_two_arm_partition(bundle):
    artifact = bundle["derived"]
    assert artifact["catalog_only_job_coverage_arm_counts"] == {
        "relationship_projection_nonempty": 3_365,
        "terminal_catalog_disposition": 9_013,
    }
    assert all(
        row["catalog_only_disposition_emitted"] is False
        for row in artifact["catalog_only_job_complement_sweep_rows"]
    )


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
                _tier2_member("component:mixed-zero-ineligible", []),
                _tier2_member(
                    "component:mixed-ineligible",
                    [_tier2_candidate("parent:role", eligible=False)],
                ),
            ],
            "multi_parent_ambiguity_no_selection",
            False,
        ),
        (
            [
                _tier2_member(
                    "component:same-parent-context",
                    [_tier2_candidate("parent:job-a-context")],
                ),
                _tier2_member(
                    "component:same-parent-other-slot",
                    [
                        _tier2_candidate(
                            "parent:job-a-other-slot",
                            slot_kind="business_aggregate",
                        )
                    ],
                ),
            ],
            "multi_parent_ambiguity_no_selection",
            False,
        ),
        (
            [
                _tier2_member(
                    "component:eligible-singleton",
                    [_tier2_candidate("parent:job-a")],
                ),
                _tier2_member(
                    "component:ineligible-singleton",
                    [_tier2_candidate("parent:role", eligible=False)],
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


@pytest.mark.parametrize(
    ("relationships", "catalog_only", "coverage_arm"),
    (
        ([], True, "terminal_catalog_disposition"),
        (
            ["a12-candidate-component-class:fixture"],
            False,
            "relationship_projection_nonempty",
        ),
    ),
)
def test__tier2_job_complement_fold__has_both_satisfiable_arms(
    relationships,
    catalog_only,
    coverage_arm,
):
    result = a12.fold_catalog_only_job_complement_fixture(
        "a12-candidate-job-class:fixture", relationships
    )
    assert result["catalog_only_disposition_required"] is catalog_only
    assert result["coverage_arm"] == coverage_arm
    assert result["catalog_only_disposition_emitted"] is False
    assert result["status"] == "prospective_fixture_nonauthority"


def test__tier2_job_complement_fold__rejects_duplicate_relationships():
    with pytest.raises(a12.BuildError, match="duplicate relationship"):
        a12.fold_catalog_only_job_complement_fixture(
            "a12-candidate-job-class:fixture",
            [
                "a12-candidate-component-class:duplicate",
                "a12-candidate-component-class:duplicate",
            ],
        )


def test__predecessor_adjudication__reproduces_round_three_36_14_split(
    bundle,
):
    artifact = bundle["predecessor"]
    derived = bundle["derived"]
    assert artifact["doc036_aggregate_component_slot_count"] == 8
    assert artifact["populated_local_proof_adjudication_count"] == 42
    assert artifact["populated_local_proof_seal_defect_count"] == 28
    assert artifact["populated_local_proof_law_gap_count"] == 14
    assert artifact["seal_defect_disposition_count"] == 36
    assert artifact["law_gap_disposition_count"] == 14
    assert artifact["in_domain_nonalias_law_gap_repair_count"] == 14
    assert artifact["in_domain_nonalias_law_gap_subkind_counts"] == {
        a12.AGGREGATE_RELATION_SUBKIND: 13,
        a12.REDIRECTION_RELATION_SUBKIND: 1,
    }
    assert artifact["round_four_new_fragment_seal_quality_issue_count"] == 10
    assert artifact["tier_2_predecessor_seal_quality_issue_count"] == 46
    assert derived["predecessor_seal_defect_count"] == 36
    assert derived["round_four_new_fragment_seal_quality_issue_count"] == 10
    assert derived["tier_2_predecessor_seal_quality_issue_count"] == 46


def test__round_three_semantic_ledger__exact_covers_all_42_proof_rows(bundle):
    rows = bundle["predecessor"]["populated_local_proof_adjudication_rows"]
    emitted_ids = {row["source_local_evidence_id"] for row in rows}
    ledgers = (
        a12.AGGREGATE_RELATION_LAW_GAP_EVIDENCE_IDS,
        a12.REDIRECTION_LAW_GAP_EVIDENCE_IDS,
        a12.PREDECESSOR_SEAL_DEFECT_EVIDENCE_IDS,
    )
    assert [len(values) for values in ledgers] == [13, 1, 28]
    assert all(
        left.isdisjoint(right)
        for left in ledgers
        for right in ledgers
        if left is not right
    )
    assert set().union(*ledgers) == emitted_ids
    changed = next(
        row
        for row in rows
        if row["source_local_evidence_id"] == DOC066_REDIRECTION_EVIDENCE
    )
    assert changed["in_domain_nonalias_relation_arm_eligible"] is True
    assert changed["in_domain_nonalias_relation_subkind"] == (
        a12.REDIRECTION_RELATION_SUBKIND
    )
    assert changed["law_gap_admitted"] is True
    assert changed["source_instruction_matched_texts"] == [
        "should be included at G78, not here."
    ]
    assert changed["endpoint_printed_identifiers"] == ["G83.", "G78."]
    assert changed["semantic_adjudication_round"] == 3


def test__round_three_pilot_projection__is_11_stop_and_2_relation(bundle):
    rows = [
        row
        for row in bundle["predecessor"][
            "populated_local_proof_adjudication_rows"
        ]
        if row["document_source_position"] in a12.PILOT_POSITIONS
    ]
    assert len(rows) == 13
    assert Counter(
        row["disposition"] == "predecessor_seal_defect" for row in rows
    ) == {True: 11, False: 2}
    assert Counter(
        row["in_domain_nonalias_relation_subkind"]
        for row in rows
        if row["law_gap_admitted"]
    ) == {
        a12.AGGREGATE_RELATION_SUBKIND: 1,
        a12.REDIRECTION_RELATION_SUBKIND: 1,
    }


def test__round_three_adjudications__all_carry_exact_source_citations(bundle):
    proof_rows = bundle["predecessor"][
        "populated_local_proof_adjudication_rows"
    ]
    doc036_rows = bundle["predecessor"]["doc036_aggregate_component_slot_rows"]
    assert len(proof_rows) + len(doc036_rows) == 50
    assert all(row["semantic_adjudication_round"] == 3 for row in proof_rows)
    assert all(row["semantic_adjudication_round"] == 3 for row in doc036_rows)
    assert all(row["source_instruction_matched_texts"] for row in proof_rows)
    assert all(row["endpoint_matched_texts"] for row in proof_rows)
    assert all(row["source_occurrence_matched_text"] for row in doc036_rows)


def test__predecessor_adjudication__reproduces_source_and_seal_flag_censuses(
    bundle,
):
    artifact = bundle["predecessor"]
    assert artifact["source_flag_counts"] == {
        "touches_noncatalog_aggregate_endpoint": 28,
        "occurrence_derived_domain_crossing": 19,
        "corrected_catalog_domain_crossing": 19,
        "raw_node_domain_crossing": 18,
        "context_remuneration_mix": 15,
        "head_spouse_mix": 4,
    }
    assert artifact["seal_defect_flag_counts"] == {
        "touches_noncatalog_aggregate_endpoint": 15,
        "occurrence_derived_domain_crossing": 19,
        "corrected_catalog_domain_crossing": 19,
        "raw_node_domain_crossing": 18,
        "context_remuneration_mix": 14,
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
    assert len(rows) == 7
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
    assert gate["four_disposition_repeat_law_status"] == (
        "pass_law_shape_only"
    )
    assert gate["nonauthority_statement"]["q5_emitted"] is False
    assert gate["nonauthority_statement"]["r_q_emitted"] is False


def test__gate_identity_roles__must_be_an_exact_ordered_partition(bundle):
    candidate = copy.deepcopy(bundle)
    gate = copy.deepcopy(candidate["gate"])
    gate["artifact_identity_rows"] = [
        copy.deepcopy(gate["artifact_identity_rows"][0]) for _ in range(7)
    ]
    gate["artifact_identity_count"] = 7
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
