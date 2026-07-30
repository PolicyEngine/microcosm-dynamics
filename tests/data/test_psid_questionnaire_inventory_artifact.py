"""Checks on the committed, fail-closed PSID dictionary audit."""

from __future__ import annotations

import json
import re
from pathlib import Path

from populace_dynamics.data import psid_questionnaire_inventory as inventory

ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "psid_questionnaire_dictionary_inventory_"
    "registration_required_v1.json"
)


def _artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


def test_committed_audit_has_exact_identity_and_full_physical_domain():
    artifact = _artifact()
    assert artifact["schema_version"] == inventory.SCHEMA_VERSION
    assert artifact["artifact_id"] == inventory.ARTIFACT_ID
    assert artifact["physical_field_count"] == 89_599
    assert len(artifact["physical_fields"]) == 89_599
    assert artifact["interview_waves"] == list(inventory.INTERVIEW_WAVES)
    assert artifact["roles"] == list(inventory.ROLES)
    assert artifact["field_purposes"] == list(inventory.FIELD_PURPOSES)
    inventory.validate_integrity(artifact)


def test_manifest_pins_all_staged_dictionary_and_raw_source_files():
    artifact = _artifact()
    manifest = artifact["source_authority_manifest"]
    assert len(manifest) == 133
    assert sum(row["size_bytes"] for row in manifest) == 1_404_728_442
    assert len({row["document_id"] for row in manifest}) == 133
    assert {row["interview_wave"] for row in manifest} == set(
        inventory.INTERVIEW_WAVES
    )
    for row in manifest:
        assert row["path"].startswith("family/")
        assert re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
        assert row["size_bytes"] > 0
        if row["dictionary_role"] == "raw_fixed_width":
            assert Path(row["path"]).suffix == ".txt"
            assert row["encoding"] == "binary"
        else:
            assert Path(row["path"]).suffix in {".do", ".sps"}
            assert row["encoding"] == "windows-1252"
    raw_rows = [
        row for row in manifest if row["dictionary_role"] == "raw_fixed_width"
    ]
    assert len(raw_rows) == len(inventory.INTERVIEW_WAVES)


def test_every_physical_field_uses_wave_minus_one_reference_year():
    artifact = _artifact()
    columns = artifact["physical_field_columns"]
    wave_index = columns.index("interview_wave")
    reference_index = columns.index("earnings_reference_year")
    key_index = columns.index("source_field_key")
    keys = []
    for row in artifact["physical_fields"]:
        assert row[reference_index] == row[wave_index] - 1
        assert row[6] == row[5] - row[4] + 1
        keys.append(row[key_index])
    assert len(keys) == len(set(keys))


def test_source_evidence_records_the_exact_ratification_blockers():
    artifact = _artifact()
    summary = artifact["evidence_summary"]
    assert summary["dictionary_file_count"] == 90
    assert summary["dictionary_total_size_bytes"] == 24_205_059
    assert summary["raw_fixed_width_file_count"] == 43
    assert summary["raw_fixed_width_total_size_bytes"] == 1_380_523_383
    assert summary["source_authority_file_count"] == 133
    assert summary["source_authority_total_size_bytes"] == 1_404_728_442
    assert summary["main_dictionary_field_count"] == 89_599
    assert summary["explicit_spss_numeric_format_count"] == 2_919
    assert summary["main_spss_missing_values_declaration_count"] == 0
    assert summary["main_spss_value_label_statement_count"] == 0
    assert summary["format_file_evidence"] == [
        {
            "explicit_truncation_count": 2_460,
            "interview_wave": 2021,
            "source_document_id": "psid-family-2021-spss_value_labels",
            "value_label_map_count": 3_212,
            "value_label_row_count": 25_263,
        },
        {
            "explicit_truncation_count": 2_327,
            "interview_wave": 2023,
            "source_document_id": "psid-family-2023-spss_value_labels",
            "value_label_map_count": 3_078,
            "value_label_row_count": 23_374,
        },
    ]
    assert artifact["integrity"]["reproduced_from_source_bytes"] is False


def test_official_artifacts_are_explicitly_not_emitted():
    artifact = _artifact()
    assert artifact["target_artifacts"] == [
        {
            "artifact_id": inventory.SLOT_SPECS_ID,
            "schema_version": inventory.SLOT_SPECS_ID,
            "status": "not_emitted_registration_required",
        },
        {
            "artifact_id": inventory.SOURCE_INVENTORY_ID,
            "schema_version": "psid_source_field_inventory.v1",
            "status": "not_emitted_registration_required",
        },
    ]
    abort = artifact["inventory_ratification_abort"]
    assert abort["failure_disposition"] == "abort_inventory_ratification"
    assert abort["registration_required_item_ids"] == [
        "V-B5",
        "V-B6",
        "V-B8",
    ]
    assert {
        row["registration_item_id"]
        for row in artifact["registration_required_items"]
    } == {"V-B5", "V-B6", "V-B8"}


def test_v4379_is_pinned_without_self_certifying_a_concept():
    artifact = _artifact()
    columns = artifact["physical_field_columns"]
    raw_field_index = columns.index("raw_field_id")
    wave_index = columns.index("interview_wave")
    rows = [
        row
        for row in artifact["physical_fields"]
        if row[wave_index] == 1976 and row[raw_field_index] == "V4379"
    ]
    assert len(rows) == 1
    assert rows[0][columns.index("exact_short_label")] == (
        "WIFES ANNUAL WAGE    H25"
    )
    assert "remuneration_type" not in columns
    assert "source_disposition" not in columns
