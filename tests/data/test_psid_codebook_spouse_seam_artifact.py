"""Checks on the committed 1976-1978 spouse-concept seam."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from populace_dynamics.data import psid_questionnaire_inventory as inventory

ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "psid_codebook_field_evidence"
    / "ry1975_1977_spouse_concept_seam_v1.json"
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


def test_spouse_seam_has_frozen_complete_source_domain():
    artifact = _artifact()
    inventory.validate_codebook_era_evidence(artifact)
    assert artifact["interview_waves"] == [1976, 1977, 1978]
    assert artifact["extraction_summary"] == {
        "field_count": 1_838,
        "description_line_count": 3_697,
        "code_map_row_count": 10_573,
        "closed_range_count": 796,
        "field_with_explicit_missing_count": 1_507,
        "explicit_missing_code_row_count": 2_807,
        "multi_page_field_count": 263,
        "page_stream_locator_count": 557,
    }
    assert artifact["era_fact_count"] == 32
    assert Counter(row["fact_class"] for row in artifact["era_facts"]) == {
        "spouse_annual_amount_concept": 3,
        "spouse_job_context_concept": 5,
        "secondary_job_context_concept": 24,
    }


def test_v4379_is_source_bound_as_mixed():
    artifact = _artifact()
    fact = next(
        row
        for row in artifact["era_facts"]
        if row["fact_id"] == "spouse-seam-amount:1976:V4379"
    )
    assert fact["status"] == "established_from_codebook_bytes"
    assert fact["remuneration_type"] == "mixed"
    assert fact["raw_field_ids"] == ["V4379", "V4382"]
    fields = _fields_by_id(artifact)
    columns = artifact["field_evidence_columns"]
    description_index = columns.index("full_source_description")
    assert (
        "labor part of unincorporated business income is in V4379"
        in fields[(1976, "V4382")][description_index]
    )


def test_v5289_and_v5788_maps_are_complete_without_concept_overclaim():
    artifact = _artifact()
    fields = _fields_by_id(artifact)
    columns = artifact["field_evidence_columns"]
    map_index = columns.index("code_map")
    for wave, field_id in ((1977, "V5289"), (1978, "V5788")):
        assert (
            fields[(wave, field_id)][map_index][-2:]
            == [
                ["2,062", "34.33", "1 - 99,998", "Actual amount"],
                ["-", "-", "99,999", "$99,999 or more"],
            ]
            if wave == 1977
            else [
                ["2,166", "35.20", "1 - 99,998", "Actual amount"],
                ["-", "-", "99,999", "$99,999 or more"],
            ]
        )
        fact = next(
            row
            for row in artifact["era_facts"]
            if row["fact_id"] == f"spouse-seam-amount:{wave}:{field_id}"
        )
        assert fact["status"] == (
            "amount_established_remuneration_type_residual"
        )
        assert fact["remuneration_type"] == (
            "not_established_wages_only_or_mixed"
        )
    residual_ids = {
        row["residual_id"]
        for row in artifact["registration_required_residuals"]
    }
    assert (
        "ry1975_1977_spouse_concept_seam:" "V-B6:V5289_V5788_concept"
    ) in residual_ids
    assert (
        "ry1975_1977_spouse_concept_seam:" "V-B6:government_level_absence"
    ) in residual_ids
    assert (
        "ry1975_1977_spouse_concept_seam:"
        "V-B6:secondary_job_attachment_and_absence"
    ) in residual_ids


def test_1976_context_maps_remain_interview_time_unmatched():
    artifact = _artifact()
    facts = [
        row
        for row in artifact["era_facts"]
        if row["fact_class"] == "spouse_job_context_concept"
    ]
    assert {row["raw_field_ids"][0] for row in facts} == {
        "V4844",
        "V4845",
        "V4850",
        "V4855",
        "V4858",
    }
    assert all(
        row["job_match_timing"]
        == "not_established_against_annual_V4379_amount"
        for row in facts
    )
    purposes = {row["raw_field_ids"][0]: row["field_purpose"] for row in facts}
    assert purposes["V4845"] == "government_employer_indicator"
    assert purposes["V4850"] == "government_employer_indicator"
    secondary = [
        row
        for row in artifact["era_facts"]
        if row["fact_class"] == "secondary_job_context_concept"
    ]
    assert {(row["interview_wave"], row["role"]) for row in secondary} == {
        (1976, "head_or_reference_person"),
        (1976, "spouse_or_partner"),
        (1977, "head_or_reference_person"),
        (1978, "head_or_reference_person"),
    }
    assert all(
        row["annual_role_total_attachment_status"] == "registration_required"
        for row in secondary
    )
    fields = _fields_by_id(artifact)
    map_index = artifact["field_evidence_columns"].index("code_map")
    assert fields[(1976, "V4844")][map_index][1:] == [
        ["1,556", "26.54", "1", "Someone else"],
        ["15", ".26", "2", "Both someone else and self"],
        ["85", "1.45", "3", "Self only"],
        ["-", "-", "9", "NA; DK"],
    ]


def test_vb6_residual_is_only_the_1977_1978_questionnaire_absence():
    artifact = _artifact()
    residuals = {
        row["residual_id"]: row
        for row in artifact["registration_required_residuals"]
    }
    old_id = "ry1975_1977_spouse_concept_seam:V-B6:annual_job_match"
    new_id = (
        "ry1975_1977_spouse_concept_seam:"
        "V-B6:1977_1978_spouse_current_job_context_absence"
    )
    assert old_id not in residuals
    residual = residuals[new_id]
    assert residual["searched_interview_waves"] == [1977, 1978]
    assert residual["established_1976_context_raw_field_ids"] == [
        "V4844",
        "V4845",
        "V4850",
        "V4855",
        "V4858",
    ]
    assert "structurally absent" in residual["missing_fact"]
    assert "timing/attachment" not in residual["missing_fact"]


def test_1976_page_locator_pins_spouse_amount_and_business_link():
    artifact = _artifact()
    locator = next(
        row
        for row in artifact["source_locators"]
        if row["source_document_id"] == "psid-family-1976-codebook"
        and row["pdf_page"] == 20
    )
    assert locator["page_object"] == "68 0 R"
    assert locator["content_object"] == "69 0 R"
    assert (locator["byte_start"], locator["byte_end"]) == (
        97_770,
        103_323,
    )
    assert locator["range_sha256"] == (
        "091710de49532f542e33a871620bd456fb9e8b454bf118646f48c5745fafae6d"
    )
    assert {"V4379", "V4382"}.issubset(locator["decoded_raw_field_id_anchors"])
