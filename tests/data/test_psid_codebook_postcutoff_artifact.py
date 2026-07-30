"""Checks on the committed 2017-2023 exclusion-lineage era."""

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
    / "ry2015_2022_exclusion_lineage_v1.json"
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


def test_postcutoff_artifact_has_the_complete_frozen_domain():
    artifact = _artifact()
    inventory.validate_codebook_era_evidence(artifact)
    assert artifact["interview_waves"] == [2017, 2019, 2021, 2023]
    assert artifact["extraction_summary"] == {
        "field_count": 19_011,
        "description_line_count": 47_501,
        "code_map_row_count": 100_875,
        "closed_range_count": 6_129,
        "field_with_explicit_missing_count": 18_327,
        "explicit_missing_code_row_count": 45_537,
        "multi_page_field_count": 4_190,
        "page_stream_locator_count": 6_964,
    }
    assert Counter(fact["fact_class"] for fact in artifact["era_facts"]) == {
        "er_role_total_component_reconciliation": 8,
        "modern_bc_de_questionnaire_field": 528,
        "regular_school_enrollment_branch": 16,
    }


def test_postcutoff_role_totals_preserve_exact_exclusion_lineage():
    artifact = _artifact()
    facts = [
        fact
        for fact in artifact["era_facts"]
        if fact["fact_class"] == "er_role_total_component_reconciliation"
    ]
    assert len(facts) == 8
    assert {(fact["interview_wave"], fact["role"]) for fact in facts} == {
        (wave, role)
        for wave in (2017, 2019, 2021, 2023)
        for role in inventory.ROLES
    }
    assert all(
        len(fact["included_component_raw_field_ids"]) == 8
        and len(fact["excluded_component_raw_field_ids"]) == 2
        for fact in facts
    )
    head_2023 = next(
        fact
        for fact in facts
        if fact["fact_id"]
        == "er-role-total:2023:head_or_reference_person:ER85496"
    )
    assert head_2023["included_component_raw_field_ids"] == [
        "ER85480",
        "ER85482",
        "ER85484",
        "ER85486",
        "ER85488",
        "ER85490",
        "ER85492",
        "ER85494",
    ]
    assert head_2023["excluded_component_raw_field_ids"] == [
        "ER85475",
        "ER85477",
    ]


def test_postcutoff_enrollment_has_both_role_branches_every_wave():
    artifact = _artifact()
    enrollment = [
        fact
        for fact in artifact["era_facts"]
        if fact["fact_class"] == "regular_school_enrollment_branch"
    ]
    assert len(enrollment) == 16
    assert {
        (fact["interview_wave"], fact["role"], fact["branch"])
        for fact in enrollment
    } == {
        (wave, role, branch)
        for wave in (2017, 2019, 2021, 2023)
        for role in inventory.ROLES
        for branch in ("new_role_background", "continuing_role_update")
    }
    assert all(
        fact["information_date_basis"]
        == (
            "current_label_question_wording_not_explicit"
            if fact["interview_wave"] == 2017
            else "explicit_current_interview_time"
        )
        for fact in enrollment
    )


def test_regular_school_map_keeps_inapplicable_distinct_from_no():
    artifact = _artifact()
    fields = _fields_by_id(artifact)
    map_index = artifact["field_evidence_columns"].index("code_map")
    code_map = fields[(2023, "ER85036")][map_index]
    meanings = {row[2]: row[3] for row in code_map}
    assert meanings["1"] == "Yes"
    assert meanings["5"] == "No"
    assert meanings["9"] == "DK; NA; refused"
    assert meanings["0"].startswith("Inap.:")
    assert meanings["0"] != meanings["5"]


def test_postcutoff_residuals_preserve_farm_and_enrollment_fail_close():
    artifact = _artifact()
    residuals = {
        row["residual_id"]: row
        for row in artifact["registration_required_residuals"]
    }
    assert (
        residuals["ry2015_2022_exclusion_lineage:role_farm_labor_allocation"][
            "status"
        ]
        == "registration_required"
    )
    assert (
        residuals["ry2015_2022_exclusion_lineage:V-B8:branch_freshness"][
            "status"
        ]
        == "registration_required"
    )


def test_postcutoff_total_pages_are_raw_stream_pinned():
    artifact = _artifact()
    locators = {
        (row["source_document_id"], row["pdf_page"]): row
        for row in artifact["source_locators"]
    }
    first = locators[("psid-family-2017-codebook", 1996)]
    assert (first["page_object"], first["content_object"]) == (
        "5994 0 R",
        "5995 0 R",
    )
    assert (first["byte_start"], first["byte_end"]) == (
        3_567_572,
        3_569_457,
    )
    assert first["range_sha256"] == (
        "e13d8ce147d18a2d8ccaa4ec932b131909bffc7107f85a4c70783905672aef17"
    )
    last = locators[("psid-family-2023-codebook", 1262)]
    assert (last["page_object"], last["content_object"]) == (
        "3792 0 R",
        "3793 0 R",
    )
    assert last["range_sha256"] == (
        "b9e884303149c03d2d22ad60c862797315794e43c07594073d662775e89109a2"
    )
