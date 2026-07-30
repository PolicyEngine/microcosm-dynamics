"""Checks on the committed 1968-1975 codebook evidence era."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from populace_dynamics.data import psid_questionnaire_inventory as inventory

ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "psid_codebook_field_evidence"
    / "wave1968_ry1968_1974_early_totals_v1.json"
)


def _artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


def _fields_by_id(artifact: dict) -> dict[tuple[int, str], list]:
    columns = artifact["field_evidence_columns"]
    wave_index = columns.index("interview_wave")
    field_index = columns.index("raw_field_id")
    return {
        (row[wave_index], row[field_index]): row
        for row in artifact["field_evidence"]
    }


def _reseal(artifact: dict) -> None:
    artifact["integrity"]["content_sha256"] = "0" * 64
    artifact["integrity"]["content_sha256"] = inventory.sha256_bytes(
        inventory.canonical_json_bytes(artifact)
    )


def test_early_era_has_frozen_complete_source_domain():
    artifact = _artifact()
    inventory.validate_codebook_era_evidence(artifact)
    assert artifact["interview_waves"] == list(range(1968, 1976))
    assert artifact["extraction_summary"] == {
        "field_count": 3_868,
        "description_line_count": 10_184,
        "code_map_row_count": 22_328,
        "closed_range_count": 1_666,
        "field_with_explicit_missing_count": 2_555,
        "explicit_missing_code_row_count": 4_358,
        "multi_page_field_count": 618,
        "page_stream_locator_count": 1_197,
    }
    assert artifact["era_fact_count"] == 64
    assert len(artifact["registration_required_residuals"]) == 5


def test_early_role_totals_preserve_full_maps_and_mixed_head_concepts():
    artifact = _artifact()
    columns = artifact["field_evidence_columns"]
    code_map_index = columns.index("code_map")
    description_index = columns.index("full_source_description")
    fields = _fields_by_id(artifact)
    assert fields[(1968, "V74")][code_map_index] == [
        ["861", "17.93", "0", "None"],
        ["3,941", "82.07", "1 - 65,490", "Actual amount"],
    ]
    assert "farm income" in fields[(1968, "V74")][description_index].lower()
    assert fields[(1975, "V3865")][code_map_index][-1] == [
        "-",
        "-",
        "99,999",
        "$99,999 or more",
    ]
    role_totals = [
        fact
        for fact in artifact["era_facts"]
        if fact["fact_class"] == "role_total_amount_concept"
    ]
    assert len(role_totals) == 16
    assert all(
        fact["remuneration_type"] == "mixed"
        for fact in role_totals
        if fact["role"] == "head_or_reference_person"
    )


def test_vb5_positive_fields_do_not_overclaim_attachment_closure():
    artifact = _artifact()
    vb5_facts = [
        fact
        for fact in artifact["era_facts"]
        if fact["fact_class"] == "occupation_industry_concept"
    ]
    assert len(vb5_facts) == 40
    assert sum(fact["job_slot"] == "main_job" for fact in vb5_facts) == 32
    assert sum(fact["job_slot"] == "secondary_job" for fact in vb5_facts) == 8
    residual = {
        row["residual_id"]: row
        for row in artifact["registration_required_residuals"]
    }[
        "wave1968_ry1968_1974_early_totals:"
        "occupation_industry_attachment_closure"
    ]
    assert residual["status"] == "registration_required"
    assert "Appendix V2" in residual["registration_required_item"]
    assert "secondary-job industry" in residual["missing_fact"]


def test_early_pdf_locator_pins_page_object_stream_and_range():
    artifact = _artifact()
    locator = next(
        row
        for row in artifact["source_locators"]
        if row["source_document_id"] == "psid-family-1968-codebook"
        and row["pdf_page"] == 19
    )
    assert locator["page_object"] == "65 0 R"
    assert locator["content_object"] == "66 0 R"
    assert (locator["byte_start"], locator["byte_end"]) == (
        90_847,
        95_977,
    )
    assert locator["range_sha256"] == (
        "563e3ced7b45524b2b4ca0cb40945dc25d0e849983374567ca7268eca2d1b134"
    )
    assert {"V74", "V75"}.issubset(locator["decoded_raw_field_id_anchors"])


def test_early_authorities_are_bound_to_local_archive_members():
    artifact = _artifact()
    codebooks = [
        row
        for row in artifact["source_authority_manifest"]
        if row["dictionary_role"] == "family_codebook"
    ]
    assert len(codebooks) == 8
    for row in codebooks:
        archive = row["provenance"]["local_family_archive"]
        assert archive["path"].endswith(".zip")
        assert archive["member_path"].lower().endswith(".pdf")
        assert archive["member_size_bytes"] == row["size_bytes"]
        assert archive["member_sha256"] == row["sha256"]
        assert archive["membership_authentication"] == (
            "archive_member_bytes_equal_registered_codebook_bytes"
        )


def test_frozen_era_identity_rejects_a_resealed_semantic_mutation():
    artifact = copy.deepcopy(_artifact())
    artifact["era_facts"][0]["reporting_unit"] = "hours"
    _reseal(artifact)
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="frozen identity",
    ):
        inventory.validate_codebook_era_evidence(artifact)
