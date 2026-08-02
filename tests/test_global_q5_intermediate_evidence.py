"""Always-runnable checks for the global Q5 intermediate evidence.

These artifacts are deliberately non-authoritative: section 19 does not
permit the canonical Q5 closure without the complete Class-B field-source
derivation.  The tests consequently pin the reproducible questionnaire
denominator and the lawful lower bounds, but never assert a passing Q5.
"""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EVIDENCE_DIRECTORY = ROOT / "docs" / "analysis" / "global_q5_evidence"
CATALOG_PATH = (
    EVIDENCE_DIRECTORY / "global_relationship_catalog_evidence_v1.json"
)
ABSENCE_STOP_PATH = (
    EVIDENCE_DIRECTORY / "global_absence_domain_stop_evidence_v1.json"
)
CANONICAL_Q5_PATH = (
    ROOT
    / "data"
    / "external"
    / "psid_questionnaire_slot_closure_evidence_v1.json"
)
EXPECTED_WAVE_DOMAIN_SHA256 = (
    "b681b78ebc82110e24fb73878b1a2b72b6bee7924ea3db1413f7acd68e163fda"
)
EXPECTED_SOURCE_DOCUMENT_KEYSET_SHA256 = (
    "8b7cad855b791c5cd7d235a74d4a0f1ecc7511dc0458db11d6b04c1b6af2c36a"
)
EXPECTED_SOURCE_DOCUMENT_DOMAIN_SHA256 = (
    "9d7a98db7c2889eba150f70935f492aebbc41cd521e4139dc1ec886ecd9945ce"
)
EXPECTED_QUESTIONNAIRE_KEYSET_SHA256 = (
    "3326c9ba70b7f83f19b0ea934630d26ced73f230be1628cb74031d17160cb1a5"
)
EXPECTED_QUESTIONNAIRE_DOMAIN_SHA256 = (
    "b06139b147391d06b4f90a8f28de472a936ec08b3e9eb37001a5a70e2b3c3543"
)
CATALOG_RAW_SHA256 = (
    "3cb612aa73388fa4929a5f5531d6ef2919bb2764a5150d3f3ea8ee75da6a0e2e"
)
CATALOG_CONTENT_SHA256 = (
    "6b939e8aa7681469014aff5a87f9f925ab56acbace8bc2aecfffaad336fd0266"
)
ABSENCE_STOP_RAW_SHA256 = (
    "8fa57c10c08ad6726f848e087503f453e2704760b2f1fe2c8e1ee46dd0293f90"
)
ABSENCE_STOP_CONTENT_SHA256 = (
    "9a64846c879b90b8500672d32ebb0ce4d5ae15ed1f27d4fea87bead9f3d843e3"
)

ERA_EXPECTATIONS = (
    (
        "wave1968_ry1968_1974_early_totals",
        16,
        842,
        48,
        [1, 2],
        [
            (
                "wave1968_ry1968_1974_early_totals:"
                "questionnaire_slot_closure"
            ),
            (
                "wave1968_ry1968_1974_early_totals:"
                "unsupported_job_context_absence_proofs"
            ),
        ],
    ),
    (
        "ry1975_1977_spouse_concept_seam",
        6,
        408,
        18,
        [5],
        ["ry1975_1977_spouse_concept_seam:questionnaire_slot_closure"],
    ),
    (
        "ry1978_1992_pre_er_totals",
        29,
        3_349,
        90,
        [11],
        ["ry1978_1992_pre_er_totals:questionnaire_slot_closure"],
    ),
    (
        "ry1993_2001_er_transition",
        12,
        1_622,
        36,
        [14],
        ["ry1993_2001_er_transition:questionnaire_slot_closure"],
    ),
    (
        "ry2002_2014_modern_bc_de",
        14,
        2_337,
        42,
        [18],
        ["ry2002_2014_modern_bc_de:questionnaire_slot_closure"],
    ),
    (
        "ry2015_2022_exclusion_lineage",
        4,
        1_632,
        24,
        [26],
        ["ry2015_2022_exclusion_lineage:questionnaire_slot_closure"],
    ),
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_global_q5_intermediate_evidence as builder  # noqa: E402


def _catalog() -> dict:
    value = builder.strict_parse_document(
        CATALOG_PATH.read_bytes(), "committed global catalog evidence"
    )
    assert isinstance(value, dict)
    return value


def _era_path(era_id: str) -> Path:
    return EVIDENCE_DIRECTORY / f"{era_id}_slot_evidence_v1.json"


def _era(era_id: str) -> dict:
    path = _era_path(era_id)
    value = builder.strict_parse_document(
        path.read_bytes(), f"committed {era_id} intermediate evidence"
    )
    assert isinstance(value, dict)
    return value


def _reseal(value: dict) -> None:
    value["integrity"]["content_sha256"] = builder._content_sha256(value)


def _all_eras() -> dict[str, dict]:
    return {era_id: _era(era_id) for era_id, *_ in ERA_EXPECTATIONS}


def _absence_stop() -> dict:
    value = builder.strict_parse_document(
        ABSENCE_STOP_PATH.read_bytes(), "committed absence-domain stop"
    )
    assert isinstance(value, dict)
    return value


def test_strict_parser_and_canonical_json_reject_ambiguous_documents():
    assert builder.canonical_json_bytes({"b": 2, "a": 1}) == (
        b'{"a":1,"b":2}\n'
    )
    assert builder.strict_parse_document(b'{"a":1}\n', "fixture") == {"a": 1}
    with pytest.raises(ValueError):
        builder.canonical_json_bytes({"a": float("nan")})

    rejected = (
        b'{"a":1,"a":2}\n',
        b'{"a":NaN}\n',
        b'{"a":Infinity}\n',
        b'{"a":1e10000}\n',
        b'{"a":0.10000000000000001}\n',
        b'\xef\xbb\xbf{"a":1}\n',
        b"\xff",
    )
    for raw in rejected:
        with pytest.raises(ValueError, match="uniquely parseable JSON"):
            builder.strict_parse_document(raw, "fixture")


def test_catalog_is_canonical_and_mirrored_by_the_validator():
    raw = CATALOG_PATH.read_bytes()
    artifact = _catalog()
    assert raw == builder.canonical_json_bytes(artifact)
    builder.validate_catalog_evidence(artifact)
    assert artifact["integrity"]["content_sha256"] == (
        builder._content_sha256(artifact)
    )
    assert hashlib.sha256(raw).hexdigest() == CATALOG_RAW_SHA256
    assert artifact["integrity"]["content_sha256"] == CATALOG_CONTENT_SHA256


def test_catalog_pins_the_complete_global_source_denominator():
    artifact = _catalog()
    wave_domain = artifact["wave_domain"]
    assert wave_domain["interview_wave_count"] == 43
    assert wave_domain["interview_wave_domain_sha256"] == (
        EXPECTED_WAVE_DOMAIN_SHA256
    )
    denominator = artifact["source_denominator"]
    assert denominator["source_document_count"] == 257
    assert denominator["source_document_role_counts"] == {
        "questionnaire_flow": 81,
        "dictionary_layout": 86,
        "codebook": 47,
        "raw_fixed_width_data": 43,
    }
    assert denominator["source_document_keyset_sha256"] == (
        EXPECTED_SOURCE_DOCUMENT_KEYSET_SHA256
    )
    assert denominator["source_document_domain_sha256"] == (
        EXPECTED_SOURCE_DOCUMENT_DOMAIN_SHA256
    )
    assert denominator["questionnaire_document_count"] == 81
    assert denominator["questionnaire_document_keyset_sha256"] == (
        EXPECTED_QUESTIONNAIRE_KEYSET_SHA256
    )
    assert denominator["questionnaire_document_domain_sha256"] == (
        EXPECTED_QUESTIONNAIRE_DOMAIN_SHA256
    )


def test_all_questionnaire_pages_and_only_lawful_baselines_are_recorded():
    artifact = _catalog()
    pages = artifact["questionnaire_page_evidence"]
    assert pages["questionnaire_page_count"] == 10_190
    assert len(pages["questionnaire_page_rows"]) == 10_190

    baseline = artifact["relationship_catalog_evidence"]
    rows = baseline["mandatory_baseline_relationship_rows"]
    assert baseline["mandatory_baseline_relationship_count"] == len(rows) == 3
    for row in rows:
        preimage = [
            row["job_slot_id"],
            row["questionnaire_component_slot_id"],
            row["slot_kind"],
        ]
        assert row["relationship_id"] == (
            "psid-questionnaire-relationship:"
            + hashlib.sha256(
                builder.canonical_json_bytes(preimage)
            ).hexdigest()
        )


def test_global_r_q_and_q5_remain_explicitly_blocked():
    artifact = _catalog()
    assert artifact["status"] == builder.BLOCKED_STATUS
    assert artifact["authority_disposition"]["canonical_q5_emitted"] is False
    relationships = artifact["relationship_catalog_evidence"]
    assert relationships["global_relationship_count"] is None
    assert relationships["global_relationship_rows"] is None
    assert relationships["r_q_status"] == (
        "blocked_incomplete_source_occurrence_annotation"
    )


@pytest.mark.parametrize(
    (
        "era_id",
        "questionnaire_document_count",
        "questionnaire_page_count",
        "hierarchy_lower_bound_count",
        "residual_source_indices",
        "residual_ids",
    ),
    ERA_EXPECTATIONS,
)
def test_era_evidence_pins_source_slice_residuals_and_lawful_lower_bound(
    era_id: str,
    questionnaire_document_count: int,
    questionnaire_page_count: int,
    hierarchy_lower_bound_count: int,
    residual_source_indices: list[int],
    residual_ids: list[str],
):
    path = _era_path(era_id)
    if not path.is_file():
        pytest.skip(f"{era_id} staged commit has not landed yet")
    raw = path.read_bytes()
    artifact = _era(era_id)
    assert raw == builder.canonical_json_bytes(artifact)
    builder.validate_era_evidence(artifact, _catalog())
    assert artifact["integrity"]["content_sha256"] == (
        builder._content_sha256(artifact)
    )
    assert artifact["era_id"] == era_id
    assert artifact["status"] == builder.BLOCKED_STATUS
    assert (
        artifact["authority_disposition"]["canonical_era_row_emitted"] is False
    )
    assert artifact["questionnaire_document_count"] == (
        questionnaire_document_count
    )
    assert artifact["questionnaire_page_count"] == questionnaire_page_count
    assert artifact["residual_ids"] == residual_ids
    assert artifact["residual_source_indices"] == residual_source_indices
    assert artifact["mandatory_baseline_relationship_count"] == 3
    assert len(artifact["mandatory_baseline_relationship_rows"]) == 3
    assert artifact["baseline_hierarchy_row_count"] == (
        hierarchy_lower_bound_count
    )
    assert len(artifact["baseline_hierarchy_rows"]) == (
        hierarchy_lower_bound_count
    )
    cardinality = artifact["complete_hierarchy_cardinality"]
    assert cardinality["design_fixed_baseline_hierarchy_lower_bound"] == (
        hierarchy_lower_bound_count
    )
    assert cardinality["design_fixed_baseline_expanded_lower_bound"] == (
        hierarchy_lower_bound_count * 35
    )
    assert cardinality["r_q_count"] is None
    assert cardinality["hierarchy_row_count"] is None
    assert cardinality["expanded_row_count"] is None
    absence = artifact["absence_domain_evidence"]
    assert absence["absence_proof_count"] is None
    assert absence["blocking_prerequisites"]


def test_no_canonical_q5_was_emitted():
    assert not CANONICAL_Q5_PATH.exists()


def test_catalog_validator_rejects_a_coherently_resealed_mutation():
    artifact = copy.deepcopy(_catalog())
    artifact["source_denominator"]["source_document_count"] -= 1
    _reseal(artifact)
    with pytest.raises(ValueError):
        builder.validate_catalog_evidence(artifact)


def test_era_validator_rejects_a_coherently_resealed_mutation():
    era_id = ERA_EXPECTATIONS[-1][0]
    if not _era_path(era_id).is_file():
        pytest.skip(f"{era_id} staged commit has not landed yet")
    artifact = copy.deepcopy(_era(era_id))
    artifact["questionnaire_page_count"] -= 1
    _reseal(artifact)
    with pytest.raises(ValueError):
        builder.validate_era_evidence(artifact, _catalog())


def test_absence_stop_is_canonical_mirrored_and_pinned():
    raw = ABSENCE_STOP_PATH.read_bytes()
    artifact = _absence_stop()
    assert raw == builder.canonical_json_bytes(artifact)
    builder.validate_absence_stop_evidence(artifact, _catalog(), _all_eras())
    assert hashlib.sha256(raw).hexdigest() == ABSENCE_STOP_RAW_SHA256
    assert artifact["integrity"]["content_sha256"] == (
        ABSENCE_STOP_CONTENT_SHA256
    )


def test_absence_stop_preserves_every_unknown_and_scope_constraint():
    artifact = _absence_stop()
    relationships = artifact["relationship_catalog_stop"]
    assert relationships["mandatory_baseline_relationship_count"] == 3
    assert relationships["global_r_q_count"] is None

    hierarchy = artifact["hierarchy_domain_stop"]
    assert hierarchy["global_hierarchy_cardinality_equation"] == (
        "|H|=86*|R_Q|"
    )
    assert hierarchy["global_expanded_cardinality_equation"] == (
        "|expanded|=3010*|R_Q|"
    )
    assert hierarchy["design_fixed_baseline_hierarchy_lower_bound"] == 258
    assert hierarchy["design_fixed_baseline_expanded_lower_bound"] == 9_030
    assert all(
        row["complete_hierarchy_row_count"] is None
        and row["absence_proof_count"] is None
        for row in hierarchy["era_cardinalities"]
    )

    absence = artifact["absence_domain_stop"]
    for key in (
        "observed_hierarchy_row_count",
        "positive_occurrence_row_count",
        "structural_expanded_key_count",
        "near_match_source_annotation_count",
        "absence_proofs",
        "absence_proof_count",
        "absence_proof_domain_sha256",
    ):
        assert absence[key] is None
    assert absence["unsupported_zero_or_empty_claim_emitted"] is False
    scope = absence["proof_scope_law"]
    assert scope["target_h_coordinate_count"] == 1
    assert scope["searched_interview_waves"] == (
        "exact_singleton_matching_h_interview_wave"
    )
    assert scope["era_wide_proof_allowed"] is False
    assert scope["cross_wave_proof_allowed"] is False
    assert scope["per_inventory_key_proof_allowed"] is False
    assert absence["relation_equations"] == {
        "observed_hierarchy_count": "|observed_H|=|O_H|",
        "positive_occurrence_count": "|positive|=|O_P|",
        "structural_expanded_key_count": "|structural|=sum_h|M_h|",
        "expanded_partition": "|O_P|+sum_h|M_h|=35*|H|",
        "absence_proof_count": "|P|=|{h_in_H:M_h_is_nonempty}|",
        "near_match_annotation_count": (
            "|near_match_source_annotation|="
            "|questionnaire_occurrence|+|field_stream_locator|"
        ),
    }
    assert len(absence["absence_proof_member_order"]) == 11
    assert len(absence["target_predicate_member_order"]) == 6
    assert len(absence["search_implementation_member_order"]) == 15
    assert len(absence["conclusion_member_order"]) == 3


def test_absence_stop_rejects_closure_and_coherently_resealed_mutation():
    artifact = _absence_stop()
    disposition = artifact["class_a_inventory_blocker_disposition"]
    assert disposition["source_indices_closed"] == []
    assert disposition["source_indices_surviving"] == [1, 2, 5, 11, 14, 18, 26]
    assert all(
        row["closed_by_intermediate_evidence"] is False
        for row in disposition["residual_rows"]
    )
    blocking_members = {
        member
        for group in artifact["blocking_members"]
        for member in group["members"]
    }
    assert (
        "source_document_manifest.field_source_derivation."
        "numeric_grammar_derivation_rows"
    ) in blocking_members
    predicates = {
        row["predicate"]: row for row in artifact["blocking_predicates"]
    }
    assert predicates[
        "unique_same_wave_leading_question_identifier_resolution"
    ]["ambiguity_evidence"] == [
        "2023:G13.:ER83121",
        "2023:G13.:ER83495",
    ]

    mutated = copy.deepcopy(artifact)
    mutated["hierarchy_domain_stop"][
        "design_fixed_baseline_hierarchy_lower_bound"
    ] -= 1
    _reseal(mutated)
    with pytest.raises(ValueError):
        builder.validate_absence_stop_evidence(
            mutated, _catalog(), _all_eras()
        )
