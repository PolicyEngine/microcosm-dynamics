"""Checks on the complete 43-wave codebook adjudication."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from populace_dynamics.data import psid_questionnaire_inventory as inventory

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = (
    ROOT / "data" / "external" / "psid_codebook_inventory_adjudication_v1.json"
)
ERA_DIRECTORY = ROOT / "data" / "external" / "psid_codebook_field_evidence"


def _artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


def _era_artifacts() -> list[dict]:
    return [
        json.loads(
            (ERA_DIRECTORY / f"{era_id}_v1.json").read_text(encoding="utf-8")
        )
        for era_id, _ in inventory.CODEBOOK_ERA_SPECS
    ]


def _reseal(artifact: dict) -> None:
    artifact["integrity"]["content_sha256"] = "0" * 64
    artifact["integrity"]["content_sha256"] = inventory.sha256_bytes(
        inventory.canonical_json_bytes(artifact)
    )


def test_adjudication_has_the_complete_43_wave_domain():
    artifact = _artifact()
    inventory.validate_codebook_inventory_adjudication(artifact)
    assert artifact["complete_domain_totals"] == {
        "interview_wave_count": 43,
        "codebook_authority_count": 43,
        "field_count": 89_599,
        "page_stream_locator_count": 29_897,
        "code_map_row_count": 479_345,
        "closed_range_count": 36_950,
        "description_line_count": 219_518,
        "present_fact_count": 3_116,
        "structural_missing_count": 0,
        "registration_required_residual_count": 32,
    }
    assert artifact["integrity"]["content_sha256"] == (
        inventory.CODEBOOK_ADJUDICATION_CONTENT_SHA256
    )


def test_adjudication_uses_exact_dispositions_without_inventing_absence():
    artifact = _artifact()
    dispositions = artifact["fact_dispositions"]
    assert dispositions["allowed_values"] == [
        "present",
        "structural_missing",
    ]
    assert len(dispositions["present"]) == 3_116
    assert all(
        row["disposition"] == "present" for row in dispositions["present"]
    )
    assert dispositions["structural_missing"] == []
    assert dispositions["structural_missing_status"] == (
        "none_adjudicated_codebook_search_is_not_questionnaire_"
        "absence_proof"
    )


def test_vb5_vb6_vb8_verdicts_preserve_positive_subclaims_and_residuals():
    artifact = _artifact()
    verdicts = {
        row["registration_item_id"]: row for row in artifact["verdicts"]
    }
    assert set(verdicts) == {"V-B5", "V-B6", "V-B8"}
    assert all(
        row["verdict"] == "registration_required" for row in verdicts.values()
    )
    assert len(verdicts["V-B5"]["established_fact_ids"]) == 40
    assert len(verdicts["V-B6"]["established_fact_ids"]) == 32
    assert len(verdicts["V-B8"]["established_fact_ids"]) == 22
    assert all(
        fact_id.startswith("regular-school:")
        for fact_id in verdicts["V-B8"]["established_fact_ids"]
    )
    assert verdicts["V-B6"]["residual_ids"] == [
        ("ry1975_1977_spouse_concept_seam:" "V-B6:V5289_V5788_concept"),
        "ry1975_1977_spouse_concept_seam:V-B6:annual_job_match",
        "ry1975_1977_spouse_concept_seam:V-B6:government_level_absence",
        (
            "ry1975_1977_spouse_concept_seam:"
            "V-B6:secondary_job_attachment_and_absence"
        ),
    ]


def test_cross_era_facts_record_the_1992_1993_seam_and_later_lineage():
    artifact = _artifact()
    facts = {row["fact_id"]: row for row in artifact["cross_era_facts"]}
    seam = facts["cross-era:ry1992_1993_component_seam"]
    assert seam["disposition"] == "present"
    assert seam["source_fact_ids"] == [
        "pre-er-split-rule:1993:ownership_work_seam",
        "er-role-total:1994:head_or_reference_person:ER4140",
        "er-role-total:1994:spouse_or_partner:ER4144",
    ]
    lineage = facts["cross-era:ry2016_2022_exclusion_lineage"]
    assert len(lineage["source_fact_ids"]) == 8
    assert all(
        fact_id.startswith(
            (
                "er-role-total:2017:",
                "er-role-total:2019:",
                "er-role-total:2021:",
                "er-role-total:2023:",
            )
        )
        for fact_id in lineage["source_fact_ids"]
    )
    boundary = facts["cross-era:wave2015_postcutoff_inventory_boundary"]
    assert len(boundary["source_fact_ids"]) == 10
    assert boundary["inventory_wave_rows_sha256"] == (
        inventory.FROZEN_INVENTORY_WAVE_ROWS_SHA256
    )
    assert boundary["codebook_or_crosswalk_inference_used"] is False
    assert artifact["production_admissibility"] == {
        "source_registry": (
            "populace_dynamics.data.psid_covered_earnings_registry"
        ),
        "source_registry_status": "frozen_unit_2_independent_registry",
        "inventory_wave_rows_sha256": (
            inventory.FROZEN_INVENTORY_WAVE_ROWS_SHA256
        ),
        "boundary_earnings_reference_year": 2014,
        "first_inventory_only_interview_wave": 2015,
        "inventory_only_post_cutoff_waves": [2015, 2017, 2019, 2021, 2023],
        "inventory_year_disposition": "inventory_only_post_cutoff",
        "production_use": "lineage_only",
        "derived_from_codebook_bytes": False,
        "crosswalk_inference_used": False,
    }


def test_official_partial_inventory_is_not_emitted():
    artifact = _artifact()
    ratification = artifact["official_inventory_ratification"]
    assert ratification["status"] == "registration_required"
    assert ratification["failure_disposition"] == (
        "abort_inventory_ratification"
    )
    assert ratification["official_partial_artifact_emitted"] is False
    assert not (
        ROOT / "data/external/psid_questionnaire_slot_specs_v1.json"
    ).exists()
    assert not (
        ROOT / "data/external/"
        "psid_covered_earnings_source_field_inventory_v1.json"
    ).exists()
    assert all(
        row["status"] == "registration_required"
        for row in artifact["registration_required_residuals"]
    )


def test_archive_capture_metadata_is_not_a_registration_blocker():
    artifact = _artifact()
    residual_ids = {
        row["residual_id"]
        for row in artifact["registration_required_residuals"]
    }
    assert not any(
        residual_id.endswith(":family_archive_capture_record")
        for residual_id in residual_ids
    )
    for era_artifact in _era_artifacts():
        codebooks = [
            row
            for row in era_artifact["source_authority_manifest"]
            if row["dictionary_role"] == "family_codebook"
        ]
        assert codebooks
        assert all(
            row["path"] and row["size_bytes"] > 0 and len(row["sha256"]) == 64
            for row in codebooks
        )


def test_committed_adjudication_rebuilds_and_resealed_mutation_fails():
    artifacts = _era_artifacts()
    rebuilt = inventory.build_codebook_inventory_adjudication(artifacts)
    assert (
        inventory.render_codebook_inventory_adjudication(rebuilt)
        == ARTIFACT_PATH.read_bytes()
    )
    mutation = copy.deepcopy(rebuilt)
    mutation["verdicts"][0]["verdict"] = "present"
    _reseal(mutation)
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="V-B verdict domain drifted",
    ):
        inventory.validate_codebook_inventory_adjudication(mutation)
