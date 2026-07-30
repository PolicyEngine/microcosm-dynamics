"""Checks on the committed RY1978-1992 pre-ER codebook era."""

from __future__ import annotations

import json
from pathlib import Path

from populace_dynamics.data import psid_questionnaire_inventory as inventory

ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "psid_codebook_field_evidence"
    / "ry1978_1992_pre_er_totals_v1.json"
)


def _artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


def test_pre_er_artifact_has_the_complete_frozen_domain():
    artifact = _artifact()
    inventory.validate_codebook_era_evidence(artifact)
    assert artifact["interview_waves"] == list(range(1979, 1994))
    assert artifact["extraction_summary"] == {
        "field_count": 15_745,
        "description_line_count": 48_103,
        "code_map_row_count": 88_545,
        "closed_range_count": 9_230,
        "field_with_explicit_missing_count": 14_179,
        "explicit_missing_code_row_count": 28_301,
        "multi_page_field_count": 2_241,
        "page_stream_locator_count": 5_261,
    }
    assert artifact["era_fact_count"] == 60


def test_pre_er_totals_distinguish_explicit_and_unresolved_composition():
    artifact = _artifact()
    totals = [
        fact
        for fact in artifact["era_facts"]
        if fact["fact_class"] == "role_total_amount_concept"
    ]
    assert len(totals) == 30
    explicit = [
        fact
        for fact in totals
        if fact["farm_business_in_total_status"]
        == "explicitly_included_exactly_once"
    ]
    unresolved = [
        fact
        for fact in totals
        if fact["farm_business_in_total_status"]
        == "not_established_by_total_description"
    ]
    assert len(explicit) == 24
    assert {(fact["interview_wave"], fact["role"]) for fact in unresolved} == {
        (1979, "spouse_or_partner"),
        (1980, "spouse_or_partner"),
        (1981, "spouse_or_partner"),
        (1982, "head_or_reference_person"),
        (1982, "spouse_or_partner"),
        (1983, "spouse_or_partner"),
    }


def test_pre_er_split_rules_preserve_the_1983_and_1992_seams():
    artifact = _artifact()
    facts = {fact["fact_id"]: fact for fact in artifact["era_facts"]}
    hours_rule = facts["pre-er-split-rule:1984:V10254"]
    assert hours_rule["earnings_reference_year"] == 1983
    assert hours_rule["rule_scope"] == (
        "hours_based_rule_first_explicit_in_codebooks"
    )
    assert hours_rule["raw_field_ids"] == ["V10254"]
    ownership_rule = facts["pre-er-split-rule:1993:ownership_work_seam"]
    assert ownership_rule["earnings_reference_year"] == 1992
    assert ownership_rule["raw_field_ids"] == [
        "V21733",
        "V21738",
        "V21803",
        "V21806",
        "V21807",
        "V23323",
        "V23324",
    ]


def test_pre_er_residual_names_the_unestablished_early_rules():
    artifact = _artifact()
    residual = next(
        row
        for row in artifact["registration_required_residuals"]
        if row["residual_id"]
        == "ry1978_1992_pre_er_totals:early_split_and_inclusion"
    )
    assert residual["status"] == "registration_required"
    assert (
        "RY1978-1982 labor/asset split algorithm" in residual["missing_fact"]
    )
    assert "RY1981 V8690" in residual["missing_fact"]


def test_pre_2013_enrollment_like_codes_prevent_blanket_absence_claim():
    artifact = _artifact()
    facts = [
        fact
        for fact in artifact["era_facts"]
        if fact["fact_class"]
        == "enrollment_like_code_not_stable_current_status"
    ]
    assert len(facts) == 28
    assert {
        "pre-2013-enrollment-like:1985:V11957",
        "pre-2013-enrollment-like:1985:V11958",
    }.issubset({fact["fact_id"] for fact in facts})
    assert all(
        fact["regular_school_equivalence_status"] == "not_established"
        for fact in facts
    )


def test_pre_er_exact_total_locators_are_raw_stream_pinned():
    artifact = _artifact()
    by_coordinate = {
        (row["source_document_id"], row["pdf_page"]): row
        for row in artifact["source_locators"]
    }
    early = by_coordinate[("psid-family-1979-codebook", 148)]
    assert (early["page_object"], early["content_object"]) == (
        "452 0 R",
        "453 0 R",
    )
    assert (early["byte_start"], early["byte_end"]) == (783_607, 788_271)
    assert early["range_sha256"] == (
        "b7474483bfa665f7448cdcf1a0de9c34ba6c4acadc83d6da34643184c1691f4e"
    )
    seam = by_coordinate[("psid-family-1993-codebook", 454)]
    assert (seam["page_object"], seam["content_object"]) == (
        "1370 0 R",
        "1371 0 R",
    )
    assert {"V23323", "V23324"}.issubset(seam["decoded_raw_field_id_anchors"])
