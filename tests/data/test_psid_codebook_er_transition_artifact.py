"""Checks on the committed RY1993-2000 ER transition era."""

from __future__ import annotations

import json
from pathlib import Path

from populace_dynamics.data import psid_questionnaire_inventory as inventory

ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "psid_codebook_field_evidence"
    / "ry1993_2001_er_transition_v1.json"
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


def test_er_transition_has_the_complete_frozen_domain():
    artifact = _artifact()
    inventory.validate_codebook_era_evidence(artifact)
    assert artifact["interview_waves"] == [
        1994,
        1995,
        1996,
        1997,
        1999,
        2001,
    ]
    assert artifact["extraction_summary"] == {
        "field_count": 15_983,
        "description_line_count": 32_205,
        "code_map_row_count": 91_014,
        "closed_range_count": 8_505,
        "field_with_explicit_missing_count": 15_517,
        "explicit_missing_code_row_count": 40_372,
        "multi_page_field_count": 2_499,
        "page_stream_locator_count": 4_822,
    }
    assert artifact["era_fact_count"] == 30


def test_every_er_role_total_explicitly_excludes_farm_and_business():
    artifact = _artifact()
    totals = [
        fact
        for fact in artifact["era_facts"]
        if fact["fact_class"] == "er_role_total_component_reconciliation"
    ]
    assert len(totals) == 12
    assert {(fact["interview_wave"], fact["role"]) for fact in totals} == {
        (wave, role)
        for wave in (1994, 1995, 1996, 1997, 1999, 2001)
        for role in inventory.ROLES
    }
    assert all(
        fact["remuneration_type"] == "wage_type_excluding_farm_business"
        for fact in totals
    )


def test_1994_head_total_binds_included_and_excluded_components():
    artifact = _artifact()
    fact = next(
        row
        for row in artifact["era_facts"]
        if row["fact_id"]
        == "er-role-total:1994:head_or_reference_person:ER4140"
    )
    assert fact["included_component_raw_field_ids"] == [
        "ER4122",
        "ER4124",
        "ER4126",
        "ER4128",
        "ER4130",
        "ER4132",
        "ER4134",
        "ER4136",
        "ER4138",
    ]
    assert fact["excluded_component_raw_field_ids"] == [
        "ER4117",
        "ER4119",
    ]
    assert set(fact["raw_field_ids"]) == {
        "ER4140",
        *fact["included_component_raw_field_ids"],
        *fact["excluded_component_raw_field_ids"],
    }


def test_decimal_er12080_range_is_reconstructed_without_meaning_corruption():
    artifact = _artifact()
    fields = _fields_by_id(artifact)
    map_index = artifact["field_evidence_columns"].index("code_map")
    assert fields[(1997, "ER12080")][map_index] == [
        ["5,161", "76.49", ".01 - 999,998.99", "Actual amount"],
        ["1,586", "23.51", ".00", "No labor income in 1996"],
        ["-", "-", "999,999.00", "$999,999 or more"],
    ]


def test_er_transition_keeps_farm_allocation_and_editing_residuals():
    artifact = _artifact()
    residuals = {
        row["residual_id"]: row
        for row in artifact["registration_required_residuals"]
    }
    farm = residuals["ry1993_2001_er_transition:role_farm_labor_allocation"]
    assert "combines labor and asset income" in farm["missing_fact"]
    assert "unavailable code" in farm["missing_fact"]
    editing = residuals[
        "ry1993_2001_er_transition:edited_total_reconciliation"
    ]
    assert "rounding/editing/sample-gap differences" in editing["missing_fact"]


def test_er_transition_locator_pins_the_1994_head_total_source_page():
    artifact = _artifact()
    locator = next(
        row
        for row in artifact["source_locators"]
        if row["source_document_id"] == "psid-family-1994-codebook"
        and row["pdf_page"] == 659
    )
    assert (locator["page_object"], locator["content_object"]) == (
        "1985 0 R",
        "1986 0 R",
    )
    assert (locator["byte_start"], locator["byte_end"]) == (
        3_588_231,
        3_592_617,
    )
    assert locator["range_sha256"] == (
        "9ab8fda3b4eb949e9fe54a98bbea3baa9680224d00767fa3a14d9bb51e83ce50"
    )
    assert {"ER4140", "ER4141"}.issubset(
        locator["decoded_raw_field_id_anchors"]
    )
