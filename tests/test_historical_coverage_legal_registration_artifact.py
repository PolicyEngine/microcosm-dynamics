"""Offline checks for the committed historical legal-registration audit."""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ARTIFACT = (
    ROOT
    / "data"
    / "external"
    / "historical_coverage_legal_registration_required_v1.json"
)
TARGET_REGISTRY = (
    ROOT / "data" / "registries" / "historical_coverage_rule_specs_v1.json"
)
ARTIFACT_SIZE_BYTES = 104_115
ARTIFACT_SHA256 = (
    "22d495904da30b5991a507f90231c598b53ba915ff197f17027177a3fa49a69f"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_historical_coverage_rule_specs as builder  # noqa: E402


def _artifact() -> dict[str, Any]:
    value = builder.strict_json_loads(
        ARTIFACT.read_bytes(), "committed legal-registration audit"
    )
    assert isinstance(value, dict)
    return value


def _reseal(value: dict[str, Any]) -> None:
    value["integrity"]["content_sha256"] = builder._content_sha256(value)


def _reseal_array(
    value: dict[str, Any],
    *,
    rows_field: str,
    count_field: str,
    digest_field: str,
) -> None:
    rows = value[rows_field]
    value[count_field] = len(rows)
    value[digest_field] = builder._sha256(builder.canonical_json_bytes(rows))
    _reseal(value)


def _reseal_sources(value: dict[str, Any]) -> None:
    documents = value["source_document_candidates"]
    ordered_ids = [row["source_document_id"] for row in documents]
    value["ordered_source_document_ids"] = ordered_ids
    value["source_document_candidate_count"] = len(documents)
    value["source_document_keyset_sha256"] = builder._sha256(
        builder.canonical_json_bytes(ordered_ids)
    )
    value["source_document_rows_sha256"] = builder._sha256(
        builder.canonical_json_bytes(documents)
    )
    census = builder._source_authority_class_census(documents)
    value["source_authority_class_census"] = census
    value["source_authority_class_census_count"] = len(census)
    value["source_authority_class_census_sha256"] = builder._sha256(
        builder.canonical_json_bytes(census)
    )
    _reseal(value)


def test_committed_audit_is_canonical_size_sha_and_structure_pinned():
    raw = ARTIFACT.read_bytes()
    assert len(raw) == ARTIFACT_SIZE_BYTES
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    value = _artifact()
    builder.validate_registration_required_audit_structure(value)
    assert raw == builder.canonical_json_bytes(value)
    assert b"/Users/" not in raw
    assert b"~/" not in raw
    assert b"maxghenis" not in raw
    assert b"data/external/snapshots/" not in raw
    assert b"repository_relative_path" not in raw
    assert b"blob_oid" not in raw
    assert b"tree_mode" not in raw


def test_capture_and_candidate_manifest_census_is_exact():
    value = _artifact()
    assert value["staging"] == builder.STAGING_IDENTITY
    identity = value["capture_manifest_identity"]
    assert identity == {
        "locator": {
            "location_type": "full_file_byte_range",
            "filename": "capture_manifest.tsv",
            "full_file_sha256": (
                "58951b038ac6bc5122952e5db8d76e3e78572b8c1bac403d2c0b561af16b68ac"
            ),
            "size_bytes": 18_835,
            "byte_start": 0,
            "byte_end": 18_835,
            "range_sha256": (
                "58951b038ac6bc5122952e5db8d76e3e78572b8c1bac403d2c0b561af16b68ac"
            ),
        },
        "row_count": 112,
        "declared_source_byte_size": 1_750_563_108,
    }
    documents = value["source_document_candidates"]
    assert value["source_document_candidate_count"] == len(documents) == 111
    assert all(
        set(row) == set(builder.SOURCE_DOCUMENT_FIELDS) for row in documents
    )
    assert value["ordered_source_document_ids"] == [
        row["source_document_id"] for row in documents
    ]
    assert value["ordered_source_document_ids"] == sorted(
        value["ordered_source_document_ids"],
        key=lambda item: item.encode("utf-8"),
    )
    assert len(set(value["ordered_source_document_ids"])) == 111
    assert value["source_document_keyset_sha256"] == (
        "dea682ab96ffc4e489799b218bab065163a81cfa89768992ef1f44e3b6a87ede"
    )
    positions = [row["manifest_position"] for row in documents]
    positions.extend(
        row["manifest_position"] for row in value["rejected_source_documents"]
    )
    assert sorted(positions) == list(range(1, 113))


def test_authority_class_and_rank_census_is_exact():
    value = _artifact()
    census = {
        row["authority_class"]: (
            row["authority_rank"],
            row["source_document_count"],
        )
        for row in value["source_authority_class_census"]
    }
    assert census == {
        "federal_statute": (1, 45),
        "federal_regulation": (1, 11),
        "executed_section_218_agreement_or_modification": (1, 0),
        "state_enactment_or_official_determination": (1, 0),
        "ssa_administering_material": (2, 6),
        "irs_administering_material": (2, 45),
        "opm_administering_material": (2, 0),
        "rrb_administering_material": (2, 0),
        "corroborating_only": (None, 4),
    }
    assert value["source_authority_class_census_sha256"] == (
        "338d68378370bd21472eae2191389b25e9f8c7fa4808c6772852a9ac31714c81"
    )


def test_expanded_session_law_chain_is_registered_from_manifest_rows():
    expected_filenames = {
        "statute-plaw-92-5-85Stat10.pdf",
        "statute-plaw-92-336-86Stat418.pdf",
        "statute-plaw-92-603-86Stat1353.pdf",
        "statute-plaw-93-66-87Stat153.pdf",
        "statute-plaw-93-233-87Stat953.pdf",
        "statute-plaw-93-368-88Stat422.pdf",
        "statute-plaw-94-92-89Stat465.pdf",
        "statute-plaw-94-455-90Stat1707.pdf",
        "statute-plaw-95-216-91Stat1535.pdf",
        "statute-plaw-95-600-92Stat2942.pdf",
        "statute-plaw-95-615-92Stat3100.pdf",
        "statute-plaw-96-222-94Stat223.pdf",
        "statute-plaw-97-34-95Stat194.pdf",
        "statute-plaw-97-248-96Stat559.pdf",
        "statute-plaw-99-272-100Stat315.pdf",
        "statute-plaw-99-509-100Stat1971.pdf",
        "statute-plaw-99-514-100Stat2915.pdf",
        "statute-plaw-100-203-101Stat1330.pdf",
        "statute-plaw-100-647-102Stat3488.pdf",
        "statute-plaw-101-508-104Stat1388.pdf",
    }
    rows = {
        row["locator"]["filename"]: row
        for row in _artifact()["source_document_candidates"]
        if row["locator"]["filename"].startswith("statute-plaw-")
    }
    assert set(rows) == expected_filenames
    assert all(
        row["authority_class"] == "federal_statute" for row in rows.values()
    )
    assert (
        rows["statute-plaw-99-272-100Stat315.pdf"]["sha256"]
        == "5f22693be907106f02a2361fac70a5791be0e82020b2286e37ea1b313d4d69c8"
    )
    assert (
        rows["statute-plaw-99-272-100Stat315.pdf"]["byte_size"] == 52_194_111
    )
    assert (
        rows["statute-plaw-101-508-104Stat1388.pdf"]["sha256"]
        == "be952b86e3d8317e46d011d017ea6828524162df90b7208c2f3df7a32676dc24"
    )
    assert (
        rows["statute-plaw-101-508-104Stat1388.pdf"]["byte_size"] == 99_936_403
    )


def test_annual_rank2_irs_sequence_is_complete_for_1968_through_1989():
    value = _artifact()
    irs_filenames = {
        row["locator"]["filename"]
        for row in value["source_document_candidates"]
        if row["authority_class"] == "irs_administering_material"
    }
    expected = {
        "f1040sc--1968.pdf",
        "f1040sf--1968.pdf",
        "i1040--1968.pdf",
    }
    for year in range(1969, 1990):
        expected.add(f"f1040sse--{year}.pdf")
        expected.add(f"i1040--{year}.pdf")
    assert irs_filenames == expected
    assert len(expected) == 45


def test_invalid_pdf_is_rejected_before_future_manifest_admission():
    value = _artifact()
    assert value["rejected_source_document_count"] == 1
    rejected = value["rejected_source_documents"][0]
    assert rejected["locator"]["filename"] == "statute104-1388-469.pdf"
    assert rejected["declared_media_type"] == "application/pdf"
    assert rejected["observed_media_type"] == "text/html"
    assert rejected["rejection_code"] == "media_type_magic_mismatch"
    assert rejected["manifest_position"] == 16
    assert rejected["locator"]["full_file_sha256"] == rejected["sha256"]
    assert rejected["locator"]["size_bytes"] == rejected["byte_size"]


def test_fail_closed_dependencies_gaps_constraints_and_zero_row_census():
    value = _artifact()
    assert [row["dependency_id"] for row in value["dependency_rows"]] == [
        "official_psid_source_field_inventory"
    ]
    assert {row["gap_id"] for row in value["source_gap_rows"]} == {
        "v_b1_missing_executed_section_218_instrument_universe",
        "v_b4_missing_annual_base_determination_bytes",
    }
    assert value["source_gap_count"] == 2
    assert value["source_gap_sha256"] == (
        "3f3345ec8fb41ecffc7efdef857128581cad736a00835ba7f0742763cb8fc134"
    )
    assert {
        row["constraint_id"] for row in value["evidence_constraint_rows"]
    } == {
        "v_b4_se_aggregation_domain_unresolved",
        "v_b4_optional_method_inputs_unavailable",
        "v_b4_electing_church_threshold_path_incomplete",
    }
    assert value["evidence_constraint_count"] == 3
    assert value["evidence_constraint_sha256"] == (
        "9f88936beb236c82459964963d7ccff1bcf555495dfedc7d0d74e9c05d5d0cf6"
    )
    assert all(
        row["rule_row_count"] == 0 for row in value["rule_registry_census"]
    )
    assert value["registry_emitted"] is False
    assert value["status"] == "registration_required"
    assert value["failure_disposition"] == "abort_registration"
    assert not TARGET_REGISTRY.exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "extra-top-level",
        "boolean-byte-size",
        "absolute-source-locator",
        "absolute-staging-path",
        "promote-compilation",
        "reorder-sources",
        "drop-rejection",
        "drop-dependency",
        "drop-source-gap",
        "change-constraint",
        "nonzero-rule-census",
        "claim-pass",
    ],
)
def test_coherently_resealed_authority_mutations_fail_closed(mutation):
    value = copy.deepcopy(_artifact())
    if mutation == "extra-top-level":
        value["alias"] = "forbidden"
        _reseal(value)
    elif mutation == "boolean-byte-size":
        value["source_document_candidates"][0]["byte_size"] = True
        _reseal_sources(value)
    elif mutation == "absolute-source-locator":
        value["source_document_candidates"][0]["locator"][
            "filename"
        ] = "/tmp/authority.pdf"
        _reseal_sources(value)
    elif mutation == "absolute-staging-path":
        value["staging"]["relative_capture_path"] = "/tmp/capture"
        _reseal(value)
    elif mutation == "promote-compilation":
        row = next(
            row
            for row in value["source_document_candidates"]
            if row["locator"]["filename"] == "comp2-F099-272.html"
        )
        row["authority_class"] = "federal_statute"
        _reseal_sources(value)
    elif mutation == "reorder-sources":
        value["source_document_candidates"][0:2] = reversed(
            value["source_document_candidates"][0:2]
        )
        _reseal_sources(value)
    elif mutation == "drop-rejection":
        value["rejected_source_documents"] = []
        _reseal_array(
            value,
            rows_field="rejected_source_documents",
            count_field="rejected_source_document_count",
            digest_field="rejected_source_document_rows_sha256",
        )
    elif mutation == "drop-dependency":
        value["dependency_rows"] = []
        _reseal_array(
            value,
            rows_field="dependency_rows",
            count_field="dependency_count",
            digest_field="dependency_sha256",
        )
    elif mutation == "drop-source-gap":
        value["source_gap_rows"].pop()
        _reseal_array(
            value,
            rows_field="source_gap_rows",
            count_field="source_gap_count",
            digest_field="source_gap_sha256",
        )
    elif mutation == "change-constraint":
        value["evidence_constraint_rows"][0]["required_resolution"] = "guess"
        _reseal_array(
            value,
            rows_field="evidence_constraint_rows",
            count_field="evidence_constraint_count",
            digest_field="evidence_constraint_sha256",
        )
    elif mutation == "nonzero-rule-census":
        value["rule_registry_census"][0]["rule_row_count"] = 1
        _reseal_array(
            value,
            rows_field="rule_registry_census",
            count_field="rule_registry_census_count",
            digest_field="rule_registry_census_sha256",
        )
    elif mutation == "claim-pass":
        value["registry_emitted"] = True
        value["status"] = "pass"
        _reseal(value)
    with pytest.raises(ValueError):
        builder.validate_registration_required_audit_structure(value)
