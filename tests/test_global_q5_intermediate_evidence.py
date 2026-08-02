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
