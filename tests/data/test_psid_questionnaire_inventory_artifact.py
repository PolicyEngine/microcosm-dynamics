"""Checks on the committed, fail-closed PSID dictionary audit."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

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


def _reseal(artifact: dict) -> None:
    artifact["integrity"]["content_sha256"] = "0" * 64
    artifact["integrity"]["content_sha256"] = inventory.sha256_bytes(
        inventory.canonical_json_bytes(artifact)
    )


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
    assert len(manifest) == 176
    assert sum(row["size_bytes"] for row in manifest) == 1_514_409_083
    assert len({row["document_id"] for row in manifest}) == 176
    assert (
        inventory.sha256_bytes(inventory.canonical_json_bytes(manifest))
        == inventory.SOURCE_AUTHORITY_MANIFEST_SHA256
    )
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
        elif row["dictionary_role"] == "family_codebook":
            assert Path(row["path"]).suffix.lower() == ".pdf"
            assert row["encoding"] == "binary"
            provenance = row["provenance"]
            assert provenance["source_organization"] == (
                "Panel Study of Income Dynamics"
            )
            assert provenance["source_product"] == "Family File Codebook"
            assert provenance["source_edition"] == str(row["interview_wave"])
            assert provenance["local_staging_authentication"] == (
                "path_size_sha256_verified"
            )
            assert provenance["network_capture_performed_in_unit"] is False
            assert provenance["retrieval_provenance_status"] == (
                "registration_required_missing_original_retrieval_url_"
                "timestamp"
            )
            archive = provenance["local_family_archive"]
            assert archive["member_size_bytes"] == row["size_bytes"]
            assert archive["member_sha256"] == row["sha256"]
            assert archive["membership_authentication"] == (
                "archive_member_bytes_equal_registered_codebook_bytes"
            )
        else:
            assert Path(row["path"]).suffix in {".do", ".sps"}
            assert row["encoding"] == "windows-1252"
    raw_rows = [
        row for row in manifest if row["dictionary_role"] == "raw_fixed_width"
    ]
    assert len(raw_rows) == len(inventory.INTERVIEW_WAVES)
    codebook_rows = [
        row for row in manifest if row["dictionary_role"] == "family_codebook"
    ]
    assert len(codebook_rows) == inventory.CODEBOOK_AUTHORITY_FILE_COUNT
    assert (
        sum(row["size_bytes"] for row in codebook_rows)
        == inventory.CODEBOOK_AUTHORITY_TOTAL_SIZE_BYTES
    )
    assert (
        inventory.sha256_bytes(inventory.canonical_json_bytes(codebook_rows))
        == inventory.CODEBOOK_AUTHORITY_MANIFEST_SHA256
    )


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
    assert summary["dictionary_file_count"] == 133
    assert summary["dictionary_total_size_bytes"] == 133_885_700
    assert summary["setup_dictionary_file_count"] == 90
    assert summary["setup_dictionary_total_size_bytes"] == 24_205_059
    assert summary["codebook_file_count"] == 43
    assert summary["codebook_total_size_bytes"] == 109_680_641
    assert summary["codebook_authority_manifest_sha256"] == (
        "b0ff4b6a09b5cb664ecd9c99a2de61f5c8a47cdb48889cd19f64f77bca11fd34"
    )
    assert summary["raw_fixed_width_file_count"] == 43
    assert summary["raw_fixed_width_total_size_bytes"] == 1_380_523_383
    assert summary["source_authority_file_count"] == 176
    assert summary["source_authority_total_size_bytes"] == 1_514_409_083
    assert summary["source_authority_manifest_sha256"] == (
        "52906f7a36955d20282dbce2dd4bac260395d3ce3961bd0baf763290c3152116"
    )
    assert summary["main_dictionary_field_count"] == 89_599
    assert summary["explicit_spss_numeric_format_count"] == 2_919
    assert summary["main_spss_missing_values_declaration_count"] == 0
    assert summary["main_spss_value_label_statement_count"] == 0
    format_evidence = summary["format_file_evidence"]
    assert [
        (
            row["interview_wave"],
            row["value_label_map_count"],
            row["value_label_row_count"],
            row["explicit_truncation_count"],
            row["field_bound_format_maps_sha256"],
        )
        for row in format_evidence
    ] == [
        (
            2021,
            3_212,
            25_263,
            2_460,
            "39a29fa289ddd41852214e30bb7d77e41534c41efd21a75a68633282e808cfd2",
        ),
        (
            2023,
            3_078,
            23_374,
            2_327,
            "d58883d52bb8a76b64206ae36093563e6cbb9d6c542de2bb3189f0e4b70cc2f2",
        ),
    ]
    for row in format_evidence:
        wave = row["interview_wave"]
        assert row["source_document_ids"] == [
            f"psid-family-{wave}-stata_value_labels",
            f"psid-family-{wave}-spss_value_labels",
        ]
        assert row["field_bound_format_map_columns"] == list(
            inventory.FIELD_BOUND_FORMAT_MAP_COLUMNS
        )
        assert row["code_label_columns"] == list(inventory.CODE_LABEL_COLUMNS)
        assert (
            len(row["field_bound_format_maps"]) == row["value_label_map_count"]
        )
    assert artifact["integrity"]["reproduced_from_source_bytes"] is False


def test_2021_and_2023_field_bound_maps_preserve_referee_anchors():
    artifact = _artifact()
    evidence_by_wave = {
        row["interview_wave"]: {
            field_map[0]: field_map
            for field_map in row["field_bound_format_maps"]
        }
        for row in artifact["evidence_summary"]["format_file_evidence"]
    }
    maps_2021 = evidence_by_wave[2021]
    assert {
        "ER78203",
        "ER78204",
        "ER78205",
        "ER78217",
        "ER78246",
        "ER78517",
        "ER78518",
        "ER78519",
        "ER78531",
        "ER78560",
        "ER81059",
        "ER81100",
        "ER81186",
        "ER81227",
    }.issubset(maps_2021)
    assert dict(maps_2021["ER78203"][2]) == {
        1: "Someone else only",
        2: "Both someone else and self",
        3: "Self-employed only",
        8: "DK",
        9: "NA; refused",
        0: (
            "Inap.:  did not work for money in 2020; has not worked for "
            "money since January 1, 2019 (ER78172=5); DK, NA, or RF "
            "whether worked for money since January 1, 2019 "
            "(ER78172=8 or 9)"
        ),
    }
    assert dict(maps_2021["ER78204"][2])[1] == "Unincorporated"
    assert dict(maps_2021["ER78205"][2])[1] == "Federal government"
    assert dict(maps_2021["ER81059"][2])[9] == "DK; NA; refused"
    maps_2023 = evidence_by_wave[2023]
    assert {
        "ER85036",
        "ER85077",
        "ER85163",
        "ER85204",
    }.issubset(maps_2023)


@pytest.mark.parametrize(
    "mutation",
    [
        "drop_all_evidence",
        "drop_one_map_and_reseal",
        "forge_source_ids",
        "forge_format_source_identity",
        "forge_codebook_source_identity",
        "claim_ratified",
        "drop_schema_identity",
    ],
)
def test_registered_format_evidence_cannot_be_discarded_or_resealed(
    mutation: str,
):
    artifact = copy.deepcopy(_artifact())
    evidence = artifact["evidence_summary"]["format_file_evidence"]
    if mutation == "drop_all_evidence":
        evidence.clear()
    elif mutation == "drop_one_map_and_reseal":
        wave = evidence[0]
        wave["field_bound_format_maps"].pop()
        wave["value_label_map_count"] = len(wave["field_bound_format_maps"])
        wave["value_label_row_count"] = sum(
            len(row[2]) for row in wave["field_bound_format_maps"]
        )
        wave["field_bound_format_maps_sha256"] = inventory.sha256_bytes(
            inventory.canonical_json_bytes(wave["field_bound_format_maps"])
        )
    elif mutation == "forge_source_ids":
        evidence[0]["source_document_ids"] = ["invented-do", "invented-sps"]
    elif mutation == "forge_format_source_identity":
        source = next(
            row
            for row in artifact["source_authority_manifest"]
            if row["document_id"] == "psid-family-2021-stata_value_labels"
        )
        source["path"] = "family/2021/FORGED_formats.do"
        source["size_bytes"] += 1
        source["sha256"] = "f" * 64
    elif mutation == "forge_codebook_source_identity":
        source = next(
            row
            for row in artifact["source_authority_manifest"]
            if row["document_id"] == "psid-family-1976-codebook"
        )
        source["sha256"] = "f" * 64
    elif mutation == "claim_ratified":
        artifact["target_artifacts"][0]["status"] = "ratified"
        artifact["inventory_ratification_abort"]["status"] = "ratified"
        artifact["inventory_ratification_abort"][
            "failure_disposition"
        ] = "continue_inventory_ratification"
        artifact["inventory_ratification_abort"][
            "registration_required_item_ids"
        ] = []
        artifact["registration_required_items"] = []
        artifact["integrity"]["reproduced_from_source_bytes"] = True
    else:
        artifact.pop("schema_version")
    _reseal(artifact)

    with pytest.raises(inventory.DictionaryDriftError):
        inventory.validate_integrity(artifact)


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
