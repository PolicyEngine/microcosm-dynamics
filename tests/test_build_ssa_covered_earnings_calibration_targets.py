"""Reproduction and fail-closed tests for entry-11 target extraction."""

from __future__ import annotations

import copy
import hashlib
import json
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
ARTIFACT_SHA256 = (
    "310c835b85fc8d040525995c07014300fcc1f6bb441ca7e7944c24693d3af5d1"
)
ARTIFACT_SIZE_BYTES = 732_387
CONTENT_SHA256 = (
    "0856791a3f1085f10cab9dc3870ab0c01d17a5a8c8ab2e37007938fd28236890"
)
BUILDER_COMMIT = "34b8bfdfbce17d39a4a42c586df550278ae209d8"
SOURCE_SHA256 = (
    "c228920ea9d53b1e323e5933b6d9f926e3c9b609d868b549fabc40118554b449"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_ssa_covered_earnings_calibration_targets as builder  # noqa: E402


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_bytes())


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _observations_by_id(artifact: dict) -> dict[str, dict]:
    return {
        observation["source_cell_id"]: observation
        for observation in artifact["observations"]
    }


def test__calibration_target_artifact__is_canonical_and_sha256_pinned():
    raw = ARTIFACT.read_bytes()
    assert raw == _canonical(json.loads(raw))
    assert len(raw) == ARTIFACT_SIZE_BYTES
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256


def test__calibration_target_builder__reproduces_committed_bytes_twice():
    raw = ARTIFACT.read_bytes()
    assert builder.render() == raw
    assert builder.render() == raw


def test__calibration_target_artifact__pins_identity_and_schema():
    artifact = _artifact()
    assert set(artifact) == {
        "artifact_role",
        "artifact_vintage_id",
        "covered_share_required_years",
        "cross_table_discrepancies",
        "integrity",
        "observations",
        "required_calendar_years",
        "required_source_cell_ids",
        "schema_version",
        "source_document_manifest",
        "year_basis",
    }
    assert artifact["schema_version"] == (
        "ssa_covered_earnings_calibration_targets.v1"
    )
    assert artifact["artifact_vintage_id"] == (
        "ssa_covered_earnings_calibration_targets.vintage2"
    )
    assert artifact["artifact_role"] == (
        "official_calibration_target_source_only"
    )
    assert artifact["year_basis"] == "calendar_year"
    assert artifact["required_calendar_years"] == list(range(1968, 2023))
    # V-B7 is registration-time work and no source row is synthesized.
    assert artifact["covered_share_required_years"] == []
    assert artifact["required_source_cell_ids"]["ssa_covered_share"] == []


def test__calibration_target_artifact__pins_complete_ordered_b2_b11_cells():
    artifact = _artifact()
    required = artifact["required_source_cell_ids"]
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
    expected_order = required["table4_b2"] + required["table4_b11"]
    assert [
        row["source_cell_id"] for row in artifact["observations"]
    ] == expected_order
    assert len(artifact["observations"]) == 825


def test__calibration_target_artifact__pins_boundary_source_rows():
    rows = _observations_by_id(_artifact())
    expected = {
        "table4.b2/1968/c5": "413,600",
        "table4.b2/1968/c8": "46,400",
        "table4.b2/1968/c11": "84,470",
        "table4.b2/1968/c12": "6,570",
        "table4.b2/1968/c13": "348,500",
        "table4.b2/1968/c17": "27,340",
        "table4.b2/2014/c5": "6,873,446",
        "table4.b2/2014/c8": "558,400",
        "table4.b2/2014/c11": "154,301",
        "table4.b2/2014/c12": "19,285",
        "table4.b2/2014/c13": "5,834,200",
        "table4.b2/2014/c17": "344,500",
        "table4.b11/1968/workers_total": "89,380",
        "table4.b11/1968/workers_wage": "84,470",
        "table4.b11/1968/workers_self_employment": "6,570",
        "table4.b11/1968/taxable_earnings_total": "375,800",
        "table4.b11/1968/taxable_earnings_wage": "348,500",
        "table4.b11/1968/taxable_earnings_self_employment": "27,300",
        "table4.b11/1968/contributions_total": "28,069",
        "table4.b11/1968/contributions_wage": "26,486",
        "table4.b11/1968/contributions_self_employment": "1,583",
        "table4.b11/2014/workers_total": "165,429",
        "table4.b11/2014/workers_wage": "154,301",
        "table4.b11/2014/workers_self_employment": "19,285",
        "table4.b11/2014/taxable_earnings_total": "6,178,700",
        "table4.b11/2014/taxable_earnings_wage": "5,834,200",
        "table4.b11/2014/taxable_earnings_self_employment": "344,500",
        "table4.b11/2014/contributions_total": "766,159",
        "table4.b11/2014/contributions_wage": "723,441",
        "table4.b11/2014/contributions_self_employment": "42,718",
    }
    assert {
        source_cell_id: rows[source_cell_id]["as_published"]
        for source_cell_id in expected
    } == expected


def test__calibration_target_artifact__pins_units_status_and_rounding_law():
    artifact = _artifact()
    for observation in artifact["observations"]:
        year = observation["calendar_year"]
        component = observation["source_cell_id"].rsplit("/", 1)[1]
        worker_component = component in {
            "c11",
            "c12",
            "workers_total",
            "workers_wage",
            "workers_self_employment",
        }
        if worker_component:
            assert (
                observation["published_unit"],
                observation["stored_unit"],
                observation["scale"],
            ) == ("thousands_of_persons", "persons", 1_000)
        else:
            assert (
                observation["published_unit"],
                observation["stored_unit"],
                observation["scale"],
            ) == (
                "millions_of_current_dollars",
                "current_dollars",
                1_000_000,
            )
        assert observation["status"] == (
            "preliminary" if year in {2021, 2022} else "historical"
        )
        assert observation["published_rounding_interval"] == {
            "status": "not_established_from_source_bytes",
            "lower": None,
            "upper": None,
            "lower_closed": None,
            "upper_closed": None,
            "rule_source_document_id": None,
            "rule_citation": None,
        }
        published = int(observation["as_published"].replace(",", ""))
        assert observation["normalized_value"] == (
            published * observation["scale"]
        )


def test__calibration_target_artifact__pins_source_manifest():
    artifact = _artifact()
    assert artifact["source_document_manifest"] == [
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
            "sha256": SOURCE_SHA256,
            "size_bytes": 488_165,
            "capture_manifest_path": (
                "data/external/snapshots/ssa_level_anchors_vintage1/"
                "capture_manifest.txt"
            ),
            "capture_manifest_entry": (
                "2026-07-27T13:02:54Z "
                f"{SOURCE_SHA256} 488165 supplement2025_4b.html"
            ),
        }
    ]
    source = SNAPSHOTS / "supplement2025_4b.html"
    assert source.stat().st_size == 488_165
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256


def test__calibration_target_artifact__pins_discrepancy_registry():
    artifact = _artifact()
    observed = [
        (
            row["calendar_year"],
            row["concept"],
            row["table4_b2_as_published"],
            row["table4_b11_as_published"],
            row["discrepancy_class"],
        )
        for row in artifact["cross_table_discrepancies"]
    ]
    assert observed == list(builder.EXPECTED_CROSS_TABLE_DISCREPANCIES)
    assert {
        row["adjudication"] for row in artifact["cross_table_discrepancies"]
    } == {"preserve_both_use_registered_table_specific_selector_never_average"}


def test__calibration_target_artifact__pins_integrity_self_hash():
    artifact = _artifact()
    assert artifact["integrity"] == {
        "canonicalization": (
            "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
        ),
        "content_sha256": CONTENT_SHA256,
        "extraction_implementation_commit": BUILDER_COMMIT,
        "reproduced_from_source_bytes": True,
    }
    preimage = copy.deepcopy(artifact)
    preimage["integrity"]["content_sha256"] = "0" * 64
    assert hashlib.sha256(_canonical(preimage)).hexdigest() == CONTENT_SHA256


def test__calibration_target_builder__rejects_source_drift_before_parsing(
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
        builder.build()


def test__calibration_target_validator__rejects_extra_schema_field():
    artifact = _artifact()
    artifact["unexpected"] = None
    with pytest.raises(ValueError, match="top-level fields"):
        builder.validate_artifact(artifact)


def test__calibration_target_validator__rejects_observation_year_alias():
    artifact = _artifact()
    artifact["observations"][0]["calendar_year"] = 1969
    with pytest.raises(ValueError, match="calendar-year equality"):
        builder.validate_artifact(artifact)


def test__calibration_target_validator__rejects_reordered_cells():
    artifact = _artifact()
    artifact["observations"][0], artifact["observations"][1] = (
        artifact["observations"][1],
        artifact["observations"][0],
    )
    with pytest.raises(ValueError, match="reordered"):
        builder.validate_artifact(artifact)


def test__calibration_target_validator__rejects_normalized_value_drift():
    artifact = _artifact()
    artifact["observations"][0]["normalized_value"] += 1
    with pytest.raises(ValueError, match="normalized value drift"):
        builder.validate_artifact(artifact)


def test__calibration_target_validator__rejects_content_hash_drift():
    artifact = _artifact()
    artifact["integrity"]["content_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="content_sha256"):
        builder.validate_artifact(artifact)
