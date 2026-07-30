"""Source reproduction and fail-closed tests for entry-11 extraction."""

from __future__ import annotations

import copy
import hashlib
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SNAPSHOTS = (
    ROOT / "data" / "external" / "snapshots" / "ssa_level_anchors_vintage1"
)
ARTIFACT = (
    ROOT
    / "data"
    / "external"
    / "ssa_covered_earnings_calibration_targets_vintage2.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_ssa_covered_earnings_calibration_targets as builder  # noqa: E402


def _evidence() -> dict:
    return builder.extract_b2_b11_source_evidence()


def _partial_legacy_artifact() -> dict:
    """Construct the withdrawn round-1 shape solely for rejection attacks."""

    evidence = _evidence()
    artifact = {
        "schema_version": builder.SCHEMA_VERSION,
        "artifact_vintage_id": builder.ARTIFACT_VINTAGE_ID,
        "artifact_role": builder.ARTIFACT_ROLE,
        "year_basis": builder.YEAR_BASIS,
        "required_calendar_years": list(builder.REQUIRED_CALENDAR_YEARS),
        "required_source_cell_ids": {
            **evidence["required_source_cell_ids"],
            "ssa_covered_share": [],
        },
        "covered_share_required_years": [],
        "source_document_manifest": evidence["source_document_manifest"],
        "observations": evidence["observations"],
        "cross_table_discrepancies": evidence["cross_table_discrepancies"],
        "integrity": {
            "canonicalization": builder.CANONICALIZATION,
            "content_sha256": "0" * 64,
            "extraction_implementation_commit": (
                builder.EXTRACTION_IMPLEMENTATION_COMMIT
            ),
            "reproduced_from_source_bytes": True,
        },
    }
    artifact["integrity"]["content_sha256"] = builder._content_sha256(artifact)
    return artifact


def _observations_by_id(evidence: dict) -> dict[str, dict]:
    return {
        observation["source_cell_id"]: observation
        for observation in evidence["observations"]
    }


def test__vintage2_authority__is_absent_and_build_fails_closed():
    assert not ARTIFACT.exists()
    with pytest.raises(builder.RegistrationAborted, match="cannot emit"):
        builder.build()
    with pytest.raises(builder.RegistrationAborted, match="cannot emit"):
        builder.render()


def test__b2_b11_evidence__is_complete_and_ordered_without_minting_v2():
    evidence = _evidence()
    assert set(evidence) == {
        "cross_table_discrepancies",
        "observations",
        "required_calendar_years",
        "required_source_cell_ids",
        "source_document_manifest",
    }
    required = evidence["required_source_cell_ids"]
    b2_components = ("c5", "c8", "c11", "c12", "c13", "c17")
    b11_components = (
        "workers_total",
        "workers_wage",
        "workers_self_employment",
        "taxable_earnings_total",
        "taxable_earnings_wage",
        "taxable_earnings_self_employment",
        "contributions_total",
        "contributions_wage",
        "contributions_self_employment",
    )
    assert required["table4_b2"] == [
        f"table4.b2/{year}/{component}"
        for year in range(1968, 2023)
        for component in b2_components
    ]
    assert required["table4_b11"] == [
        f"table4.b11/{year}/{component}"
        for year in range(1968, 2023)
        for component in b11_components
    ]
    assert [
        row["source_cell_id"] for row in evidence["observations"]
    ] == required["table4_b2"] + required["table4_b11"]
    assert len(evidence["observations"]) == 825


def test__b2_b11_evidence__pins_boundary_source_rows():
    rows = _observations_by_id(_evidence())
    expected = {
        "table4.b2/1968/c5": "413,600",
        "table4.b2/1968/c8": "46,400",
        "table4.b2/1968/c11": "84,470",
        "table4.b2/1968/c12": "6,570",
        "table4.b2/2014/c5": "6,873,446",
        "table4.b2/2014/c8": "558,400",
        "table4.b11/1968/workers_total": "89,380",
        "table4.b11/1968/taxable_earnings_total": "375,800",
        "table4.b11/1968/contributions_total": "28,069",
        "table4.b11/2014/workers_total": "165,429",
        "table4.b11/2014/taxable_earnings_total": "6,178,700",
        "table4.b11/2014/contributions_total": "766,159",
    }
    assert {
        source_cell_id: rows[source_cell_id]["as_published"]
        for source_cell_id in expected
    } == expected


def test__b2_b11_evidence__pins_units_status_manifest_and_discrepancies():
    evidence = _evidence()
    assert evidence["source_document_manifest"] == [
        {
            "source_document_id": "ssa_supplement_2025_4b",
            "publication": "Annual Statistical Supplement, 2025",
            "edition": "2025",
            "table_ids": ["table4.b2", "table4.b11"],
            "url": (
                "https://www.ssa.gov/policy/docs/statcomps/supplement/"
                "2025/4b.html"
            ),
            "retrieved_at_utc": "2026-07-27T13:02:54Z",
            "committed_path": (
                "data/external/snapshots/ssa_level_anchors_vintage1/"
                "supplement2025_4b.html"
            ),
            "sha256": builder.SOURCE_SHA256,
            "size_bytes": 488_165,
            "capture_manifest_path": (
                "data/external/snapshots/ssa_level_anchors_vintage1/"
                "capture_manifest.txt"
            ),
            "capture_manifest_entry": (
                "2026-07-27T13:02:54Z "
                f"{builder.SOURCE_SHA256} 488165 supplement2025_4b.html"
            ),
        }
    ]
    for observation in evidence["observations"]:
        year = observation["calendar_year"]
        assert observation["status"] == (
            "preliminary" if year in {2021, 2022} else "historical"
        )
        assert observation["published_rounding_interval"] == (
            builder.ROUNDING_NOT_ESTABLISHED
        )
    assert [
        (
            row["calendar_year"],
            row["concept"],
            row["table4_b2_as_published"],
            row["table4_b11_as_published"],
            row["discrepancy_class"],
        )
        for row in evidence["cross_table_discrepancies"]
    ] == list(builder.EXPECTED_CROSS_TABLE_DISCREPANCIES)


def test__vb7_adjudication__rejects_every_committed_construction():
    adjudication = builder.vb7_adjudication()
    assert adjudication["covered_share_required_years"] == []
    assert adjudication["registration_disposition"] == (
        "abort_no_authoritative_vintage2_or_calibration_target_specs"
    )
    candidates = {
        row["candidate_id"]: row
        for row in adjudication["candidate_constructions"]
    }
    earnings = candidates["table4_b1_reported_taxable_earnings_share"]
    assert earnings["published_percentage_examples"] == {
        "1968": "81.7",
        "2014": "83.1",
    }
    assert earnings["verdict"] == "reject_earnings_share_is_not_worker_share"

    workers = candidates[
        "supplement_workers_with_taxable_earnings_over_"
        "trustees_covered_workers"
    ]
    assert workers["displayed_ratio_comparison_counts"] == {
        "above_one": 31,
        "below_one": 24,
        "equal_one": 0,
    }
    assert workers["example_1978"] == {
        "numerator_thousands": "110,600",
        "denominator_thousands": "109,432",
    }
    assert workers["verdict"].startswith("reject_not_a_source_defined")


def test__membership_adjudication__fails_required_fitting_families():
    relationships = {
        row["family"]: row
        for row in builder.vb7_adjudication()[
            "worker_membership_relationships"
        ]
    }
    assert set(relationships) == {
        "b2_wage_total_intensity",
        "b2_se_total_intensity",
        "b11_worker_distribution",
    }
    assert {row["verdict"] for row in relationships.values()} == {
        "fail_closed"
    }
    assert (
        "zero_and_loss_only_membership"
        in relationships["b2_se_total_intensity"]["not_established"]
    )


def test__partial_round1_shape__is_never_accepted_as_vintage2():
    with pytest.raises(builder.RegistrationAborted, match="V-B7"):
        builder.validate_artifact(_partial_legacy_artifact())


def test__validator__reresolves_coherently_rehashed_cell_from_source_bytes():
    artifact = _partial_legacy_artifact()
    row = next(
        row
        for row in artifact["observations"]
        if row["source_cell_id"] == "table4.b2/1973/c5"
    )
    row["as_published"] = "999"
    row["normalized_value"] = 999_000_000
    artifact["integrity"]["content_sha256"] = builder._content_sha256(artifact)
    with pytest.raises(ValueError, match="re-resolve from source bytes"):
        builder.validate_artifact(artifact)


def test__extractor__rejects_source_drift_before_parsing(
    tmp_path, monkeypatch
):
    copied = tmp_path / "ssa_level_anchors_vintage1"
    shutil.copytree(SNAPSHOTS, copied)
    source = copied / "supplement2025_4b.html"
    changed = bytearray(source.read_bytes())
    changed[-1] ^= 1
    source.write_bytes(changed)
    monkeypatch.setattr(builder.entry10, "SNAPSHOT_DIR", copied)

    def parse_must_not_run(*_args, **_kwargs):
        raise AssertionError("HTML parsing ran before source hashes passed")

    monkeypatch.setattr(builder, "_select_tables", parse_must_not_run)
    with pytest.raises(ValueError, match="source-byte drift"):
        builder.extract_b2_b11_source_evidence()


def test__vb7_fragment_hashes__come_from_verified_source_text():
    adjudication = builder.vb7_adjudication()
    candidates = adjudication["candidate_constructions"]
    digests = {
        value
        for candidate in candidates
        for key, value in candidate.items()
        if key.endswith("_fragment_sha256")
    }
    assert digests
    assert all(
        isinstance(digest, str)
        and len(digest) == 64
        and digest == digest.lower()
        for digest in digests
    )


def test__partial_attack_helper__has_valid_self_hash_before_mutation():
    artifact = _partial_legacy_artifact()
    preimage = copy.deepcopy(artifact)
    preimage["integrity"]["content_sha256"] = "0" * 64
    assert (
        artifact["integrity"]["content_sha256"]
        == hashlib.sha256(
            builder.entry10.canonical_json_bytes(preimage)
        ).hexdigest()
    )
