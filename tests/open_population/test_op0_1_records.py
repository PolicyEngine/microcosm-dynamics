"""Check the draft OP0.1 audit contract using documentation only."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORDS_PATH = ROOT / "docs/design/open_population_op0_1_records.json"
SCHEMA = "open_population_op0_record.v1"
RECORD_IDS = {
    "gate_birth",
    "gate_imm",
    "emigration_check",
    "demographic_target_manifest",
    "gate_pop",
    "demographic_horizon",
}
REQUIRED_ELEMENTS = {
    "source_release",
    "variables",
    "population",
    "exposure_history",
    "holdout_partition",
    "critical_cells",
    "numerical_tolerances",
    "uncertainty_treatment",
    "pass_conjunction",
    "power_procedure",
    "universe_bridge",
    "date_mapping",
    "target_manifest",
    "fitted_support",
    "access",
    "registry_snapshot",
}
REGISTRY_PATH = "docs/design/track_b_holdout_registry.json"
REGISTRY_COMMIT = "daf02425"
REGISTRY_SHA256 = (
    "084b8d50ba3c0fe7cf9bd70e3c7c700c" "60ae682644ead99cca2bb116bfb2ef88"
)
SHA256 = re.compile(r"[0-9a-f]{64}")
MANIFEST_FIELDS = {
    "id",
    "source",
    "table",
    "row",
    "column",
    "vintage",
    "captured_byte_hash",
    "status",
}
MANIFEST_STATUSES = {"available", "not_available", "validation_only"}
POWER_FIELDS = {
    "name",
    "operating_characteristic",
    "inputs",
    "procedure",
    "status",
}


def load_records():
    return json.loads(RECORDS_PATH.read_text(encoding="utf-8"))


def populated(value):
    """Required audit elements carry explanatory content, not placeholders."""
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, (list, dict)) and bool(value)


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def test_all_six_records_are_drafts_with_required_elements():
    document = load_records()
    assert isinstance(document, dict)
    assert document["schema"] == SCHEMA
    assert document["status"] == "draft"
    records = document["records"]
    assert isinstance(records, list)
    assert len(records) == len(RECORD_IDS)
    assert all(isinstance(record, dict) for record in records)
    assert {record["id"] for record in records} == RECORD_IDS
    for record in records:
        assert record["schema"] == SCHEMA, record["id"]
        assert record["status"] == "draft", record["id"]
        assert REQUIRED_ELEMENTS <= record.keys(), record["id"]
        for field in REQUIRED_ELEMENTS:
            assert populated(record[field]), (record["id"], field)


def test_no_nested_element_marks_the_audit_frozen():
    for value in walk(load_records()):
        if isinstance(value, str):
            assert value.strip().casefold() != "frozen"
        elif isinstance(value, dict):
            for marker in ("frozen", "is_frozen"):
                if marker in value:
                    assert value[marker] is False


def test_holdout_years_are_pending_the_pinned_registry():
    for record in load_records()["records"]:
        snapshot = record["registry_snapshot"]
        assert isinstance(snapshot, dict), record["id"]
        assert snapshot["path"] == REGISTRY_PATH, record["id"]
        assert snapshot["commit"] == REGISTRY_COMMIT, record["id"]
        assert snapshot["sha256"] == REGISTRY_SHA256, record["id"]
        assert SHA256.fullmatch(snapshot["sha256"]), record["id"]
        assert snapshot == load_records()["registry_snapshot"]

        partition = record["holdout_partition"]
        assert isinstance(partition, dict), record["id"]
        years = partition["held_out_years"]
        assert isinstance(years, list), record["id"]
        for year in years:
            assert isinstance(year, dict), record["id"]
            assert {"source", "year", "status"} <= year.keys()
            assert isinstance(year["source"], str)
            assert year["source"].strip()
            assert type(year["year"]) is int
            assert 1900 <= year["year"] <= 2200
            assert year["status"] == "pending_registry"


def test_manifests_and_unrun_power_procedures_are_explicit():
    for record in load_records()["records"]:
        manifest = record["target_manifest"]
        assert isinstance(manifest, list) and manifest, record["id"]
        identifiers = []
        for entry in manifest:
            assert isinstance(entry, dict), record["id"]
            assert MANIFEST_FIELDS <= entry.keys(), record["id"]
            for field in MANIFEST_FIELDS - {"vintage"}:
                assert isinstance(entry[field], str), field
                assert entry[field].strip(), field
            assert isinstance(entry["vintage"], (str, int))
            assert not isinstance(entry["vintage"], bool)
            assert str(entry["vintage"]).strip()
            assert entry["status"] in MANIFEST_STATUSES
            digest = entry["captured_byte_hash"]
            assert digest == "to capture" or SHA256.fullmatch(digest)
            identifiers.append(entry["id"])
        assert len(set(identifiers)) == len(identifiers), record["id"]

        power = record["power_procedure"]
        assert isinstance(power, dict), record["id"]
        assert POWER_FIELDS <= power.keys(), record["id"]
        for field in POWER_FIELDS:
            assert populated(power[field]), (record["id"], field)
        assert isinstance(power["name"], str)
        assert power["status"] == "not_run_no_real_data"


def test_access_distinguishes_documentation_from_data_reachability():
    for record in load_records()["records"]:
        access = record["access"]
        assert isinstance(access, list) and access, record["id"]
        for source in access:
            for field in (
                "source_id",
                "url",
                "documentation_url",
                "licence_or_terms",
                "reason",
            ):
                assert isinstance(source[field], str) and source[field].strip()
            assert source["url"].startswith("https://")
            assert source["documentation_url"].startswith("https://")
            assert isinstance(source["public"], bool)
            assert source["reachability"] in {"confirmed", "unverified"}
            assert source["documentation_reachability"] in {
                "confirmed",
                "unverified",
            }
            if source["documentation_reachability"] == "confirmed":
                assert source["read_date"] == "2026-10-24"
