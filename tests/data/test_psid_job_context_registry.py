"""Artifact and mutation tests for raw PSID job-context extraction specs."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from populace_dynamics.data import psid_job_context_registry as registry

REPO_ROOT = Path(__file__).resolve().parents[2]
DICTIONARY_AUDIT_PATH = (
    REPO_ROOT
    / "data"
    / "external"
    / "psid_questionnaire_dictionary_inventory_"
    "registration_required_v1.json"
)
REGISTRY_PATH = (
    REPO_ROOT
    / "data"
    / "external"
    / "psid_modern_job_context_raw_extraction_specs_v1.json"
)


@pytest.fixture(scope="module")
def evidence() -> tuple[dict, str, dict]:
    audit_bytes = DICTIONARY_AUDIT_PATH.read_bytes()
    audit = json.loads(audit_bytes)
    audit_sha256 = hashlib.sha256(audit_bytes).hexdigest()
    artifact = json.loads(REGISTRY_PATH.read_bytes())
    return audit, audit_sha256, artifact


def _reseal(candidate: dict) -> None:
    keys = [row["raw_extraction_key"] for row in candidate["rows"]]
    candidate["row_count"] = len(candidate["rows"])
    candidate["row_keyset_sha256"] = registry._keyset_hash(keys)
    candidate["integrity"]["content_sha256"] = "0" * 64
    candidate["integrity"]["content_sha256"] = hashlib.sha256(
        registry.canonical_json_bytes(candidate)
    ).hexdigest()


def _rekey(row: dict) -> None:
    row["raw_extraction_key"] = registry._extraction_key(
        row["source_field_key"],
        registry._coordinate(row),
    )


def test_registry_identity_and_independent_domain_are_exact(evidence):
    audit, audit_sha256, artifact = evidence
    assert artifact["schema_version"] == registry.SCHEMA_VERSION
    assert artifact["artifact_id"] == registry.ARTIFACT_ID
    assert artifact["authority_scope"] == "physical_extraction_only"
    assert artifact["interview_waves"] == list(registry.MODERN_INTERVIEW_WAVES)
    assert artifact["source_block_role_map"] == {
        "BC": "head",
        "DE": "spouse",
        "FAMILY": "shared",
    }
    assert artifact["row_count"] == 3_123
    assert len(registry.expected_reader_coordinates()) == 3_123
    registry.validate_raw_extraction_registry(
        artifact,
        audit,
        dictionary_audit_file_sha256=audit_sha256,
    )


def test_each_wave_has_complete_shared_role_and_job_domains(evidence):
    _, _, artifact = evidence
    by_wave = Counter(row["interview_wave"] for row in artifact["rows"])
    assert by_wave == {
        wave: 297 if wave in (2003, 2005) else 281
        for wave in range(2003, 2024, 2)
    }
    for wave in registry.MODERN_INTERVIEW_WAVES:
        wave_rows = [
            row for row in artifact["rows"] if row["interview_wave"] == wave
        ]
        assert (
            sum(
                row["source_context_scope"]
                == "family_shared_interview_current"
                for row in wave_rows
            )
            == 3
        )
        for role in ("head", "spouse"):
            role_rows = [
                row for row in wave_rows if row["reader_role"] == role
            ]
            assert (
                sum(
                    row["source_context_scope"] == "role_block_unadjudicated"
                    for row in role_rows
                )
                == 23
            )
            for job_number in range(1, 5):
                job_rows = [
                    row
                    for row in role_rows
                    if row["reader_job_slot"] == f"job_{job_number}"
                ]
                expected_job_rows = 31 if wave in (2003, 2005) else 29
                assert len(job_rows) == expected_job_rows


def test_rows_are_raw_only_and_never_claim_official_semantics(evidence):
    _, _, artifact = evidence
    assert set(artifact["rows"][0]) == set(registry.ROW_COLUMNS)
    for row in artifact["rows"]:
        assert not set(row).intersection(
            registry.FORBIDDEN_OFFICIAL_ROW_FIELDS
        )
        assert row["earnings_reference_year"] == row["interview_wave"] - 1
        assert row["raw_width"] == (
            row["layout_end_1indexed"] - row["layout_start_1indexed"] + 1
        )
        assert row["source_document_ids"]
        assert (
            f"psid-family-{row['interview_wave']}-raw_fixed_width"
            in row["source_document_ids"]
        )
        assert row["reader_field_id"].endswith("_raw")


def test_source_anchors_and_coding_width_seam_are_pinned(evidence):
    _, _, artifact = evidence

    def one(wave, raw_field_id):
        matches = [
            row
            for row in artifact["rows"]
            if row["interview_wave"] == wave
            and row["raw_field_id"] == raw_field_id
        ]
        assert len(matches) == 1
        return matches[0]

    assert one(2003, "ER21002")["layout_start_1indexed"] == 2
    assert one(2003, "ER21003")["reader_field_id"] == (
        "state_of_residence_psid_raw"
    )
    assert one(2003, "ER21129")["reader_field_id"] == (
        "job_beginning_month_raw"
    )
    assert one(2003, "ER21145")["raw_width"] == 3
    assert one(2003, "ER21174")["reader_field_id"] == (
        "calculated_elapsed_weeks_raw"
    )
    assert one(2003, "ER21175")["reader_field_id"] == (
        "calculated_elapsed_weeks_accuracy_raw"
    )
    assert one(2017, "ER66195")["raw_width"] == 4
    assert one(2023, "ER82642")["reader_field_id"] == (
        "prior_year_job_earnings_reporting_unit_raw"
    )


def test_late_wave_reader_subset_preserves_field_bound_map_evidence(evidence):
    audit, _, artifact = evidence
    maps_by_wave = {
        row["interview_wave"]: {
            field_map[0] for field_map in row["field_bound_format_maps"]
        }
        for row in audit["evidence_summary"]["format_file_evidence"]
    }
    for wave in (2021, 2023):
        reader_rows = [
            row for row in artifact["rows"] if row["interview_wave"] == wave
        ]
        assert len(reader_rows) == 281
        assert (
            sum(
                row["raw_field_id"] in maps_by_wave[wave]
                for row in reader_rows
            )
            == 210
        )


def test_both_interview_current_state_fields_remain_distinct(evidence):
    _, _, artifact = evidence
    for wave in registry.MODERN_INTERVIEW_WAVES:
        shared = {
            row["reader_field_id"]: row
            for row in artifact["rows"]
            if row["interview_wave"] == wave
            and row["source_block"] == "FAMILY"
        }
        assert set(shared) == {
            "family_interview_id_raw",
            "state_of_residence_psid_raw",
            "state_of_residence_current_raw",
        }
        assert shared["state_of_residence_psid_raw"]["raw_field_id"] != (
            shared["state_of_residence_current_raw"]["raw_field_id"]
        )


def test_official_inventory_crosswalk_and_g17_remain_unemitted(evidence):
    _, _, artifact = evidence
    assert artifact["official_artifact_status"] == {
        "g17_inventory_crosswalk_evidence.v1": (
            "not_emitted_upstream_registration_required"
        ),
        "psid_covered_earnings_crosswalk.v2": (
            "not_emitted_upstream_registration_required"
        ),
        "psid_covered_earnings_source_field_inventory.v1": (
            "not_emitted_registration_required"
        ),
        "psid_questionnaire_slot_specs.v1": (
            "not_emitted_registration_required"
        ),
        "registration_required_item_ids": ["V-B5", "V-B6", "V-B8"],
    }


def test_committed_registry_reproduces_from_dictionary_audit(evidence):
    audit, audit_sha256, artifact = evidence
    rebuilt = registry.build_raw_extraction_registry(
        audit,
        dictionary_audit_file_sha256=audit_sha256,
    )
    assert rebuilt == artifact
    assert (
        registry.render_registry(
            rebuilt,
            audit,
            dictionary_audit_file_sha256=audit_sha256,
        )
        == REGISTRY_PATH.read_bytes()
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "omit",
        "add",
        "duplicate",
        "reorder",
        "wrong_job",
        "wrong_role",
        "wrong_label",
        "wrong_coordinate",
        "wrong_reference_year",
    ],
)
def test_physical_scope_domain_mutations_fail_even_when_resealed(
    evidence,
    mutation,
):
    audit, audit_sha256, artifact = evidence
    candidate = copy.deepcopy(artifact)
    if mutation == "omit":
        candidate["rows"].pop(100)
    elif mutation == "add":
        extra = copy.deepcopy(candidate["rows"][100])
        extra["source_field_key"] = "psid-physical-field:" + "f" * 64
        _rekey(extra)
        candidate["rows"].append(extra)
    elif mutation == "duplicate":
        candidate["rows"].append(copy.deepcopy(candidate["rows"][100]))
    elif mutation == "reorder":
        candidate["rows"][100], candidate["rows"][101] = (
            candidate["rows"][101],
            candidate["rows"][100],
        )
    elif mutation == "wrong_job":
        row = next(
            row
            for row in candidate["rows"]
            if row["reader_job_slot"] == "job_1"
        )
        row["reader_job_slot"] = "job_2"
        _rekey(row)
    elif mutation == "wrong_role":
        row = next(
            row for row in candidate["rows"] if row["reader_role"] == "head"
        )
        row["reader_role"] = "spouse"
        _rekey(row)
    elif mutation == "wrong_label":
        candidate["rows"][100]["exact_short_label"] = "CHANGED"
    elif mutation == "wrong_coordinate":
        candidate["rows"][100]["layout_start_1indexed"] += 1
    elif mutation == "wrong_reference_year":
        candidate["rows"][100]["earnings_reference_year"] -= 1
    _reseal(candidate)
    with pytest.raises(registry.RawExtractionRegistryError):
        registry.validate_raw_extraction_registry(
            candidate,
            audit,
            dictionary_audit_file_sha256=audit_sha256,
        )


def test_label_parser_is_exact_and_fail_closed():
    parsed = registry.parse_source_label(
        2003,
        "BC46 AMOUNT EARNED LAST YEAR--JOB 4",
    )
    assert parsed == {
        "source_block": "BC",
        "reader_role": "head",
        "reader_job_slot": "job_4",
        "source_context_scope": "explicit_job_label",
        "source_question_id": "BC46",
        "reader_field_id": "prior_year_job_earnings_amount_raw",
        "field_ordinal": 1,
    }
    assert (
        registry.parse_source_label(
            2003,
            "BC46 APPROXIMATE EARNINGS--JOB 4",
        )
        is None
    )
    assert registry._is_relevant_candidate(
        2003,
        "BC46 APPROXIMATE EARNINGS--JOB 4",
    )
