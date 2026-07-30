"""Checks on the committed 2003-2015 BC/DE codebook era."""

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
    / "ry2002_2014_modern_bc_de_v1.json"
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


def test_modern_artifact_has_the_complete_frozen_domain():
    artifact = _artifact()
    inventory.validate_codebook_era_evidence(artifact)
    assert artifact["interview_waves"] == list(range(2003, 2016, 2))
    assert artifact["extraction_summary"] == {
        "field_count": 33_154,
        "description_line_count": 77_828,
        "code_map_row_count": 166_010,
        "closed_range_count": 10_624,
        "field_with_explicit_missing_count": 31_777,
        "explicit_missing_code_row_count": 82_019,
        "multi_page_field_count": 5_838,
        "page_stream_locator_count": 11_096,
    }
    assert artifact["era_fact_count"] == 1_866
    assert Counter(fact["fact_class"] for fact in artifact["era_facts"]) == {
        "er_role_total_component_reconciliation": 14,
        "modern_bc_de_questionnaire_field": 1_828,
        "regular_school_enrollment_branch": 6,
        "lexical_enrollment_like_code_non_evidentiary": 18,
    }


def test_bc46_amount_and_unit_are_role_job_and_reference_year_bound():
    artifact = _artifact()
    facts = {fact["fact_id"]: fact for fact in artifact["era_facts"]}
    amount = facts["modern-job-context:2003:ER21182"]
    unit = facts["modern-job-context:2003:ER21183"]
    assert amount["field_purpose"] == "amount"
    assert unit["field_purpose"] == "reporting_unit"
    for fact in (amount, unit):
        assert fact["role"] == "head_or_reference_person"
        assert fact["job_slot"] == "job_1"
        assert fact["source_question_id"] == "BC46"
        assert fact["information_date_basis"] == "reference_year"
        assert fact["job_match_timing"] == "explicit_source_job_number"
    monthly = facts["modern-job-context:2003:ER21133"]
    assert monthly["field_purpose"] == "monthly_employment_indicator"
    assert monthly["reporting_unit"] == "complete_source_indicator_code_map"
    assert monthly["information_date_basis"] == "reference_year_month"
    salary = facts["modern-job-context:2003:ER21153"]
    assert salary["job_slot"] == "current_main_job"
    assert salary["field_purpose"] == "salary_amount"
    assert salary["reporting_unit"] == (
        "dollars_and_cents_paired_with_source_reporting_unit"
    )
    assert salary["job_match_timing"] == ("explicit_current_main_job_wording")
    tenure = facts["modern-job-context:2003:ER21171"]
    assert tenure["field_purpose"] == "employer_tenure_years"
    assert tenure["reporting_unit"] == "years"
    weeks = facts["modern-job-context:2007:ER36168"]
    assert weeks["field_purpose"] == "weeks_worked"
    assert weeks["reference_periodicity"] == "reference_year_weeks"
    hours = facts["modern-job-context:2003:ER21176"]
    assert hours["field_purpose"] == "average_hours_per_week"
    assert hours["reporting_unit"] == "hours_per_week"


def test_bc46_complete_amount_and_unit_maps_are_preserved():
    artifact = _artifact()
    fields = _fields_by_id(artifact)
    map_index = artifact["field_evidence_columns"].index("code_map")
    amount_map = fields[(2003, "ER21182")][map_index]
    assert amount_map[:4] == [
        ["-", "-", "-999,997.00", "Loss of $999,997 or more"],
        ["4", ".05", "-999,996.99 - -.01", "Actual loss"],
        ["5,385", "68.84", ".01 - 9,999,996.99", "Actual amount"],
        ["-", "-", "9,999,997.00", "$9,999,997 or more"],
    ]
    assert amount_map[-3:] == [
        ["278", "3.55", "9,999,998.00", "DK"],
        ["167", "2.14", "9,999,999.00", "NA; refused"],
        [
            "1,988",
            "25.42",
            ".00",
            (
                "Inap.: did not work for money in 2002 or has not worked "
                "for money since January 1, 2001 (ER21127=5, 8, or 9); "
                "began working for this employer in 2003 (ER21130=2003)"
            ),
        ],
    ]
    assert [row[3] for row in fields[(2003, "ER21183")][map_index][0:7]] == [
        "Hour",
        "Day",
        "Week",
        "Two weeks",
        "Month",
        "Year",
        "Other",
    ]


def test_modern_role_totals_and_component_fields_preserve_exclusion_lineage():
    artifact = _artifact()
    fact = next(
        row
        for row in artifact["era_facts"]
        if row["fact_id"]
        == "er-role-total:2015:head_or_reference_person:ER65216"
    )
    assert fact["included_component_raw_field_ids"] == [
        "ER65200",
        "ER65202",
        "ER65204",
        "ER65206",
        "ER65208",
        "ER65210",
        "ER65212",
        "ER65214",
    ]
    assert fact["excluded_component_raw_field_ids"] == [
        "ER65195",
        "ER65197",
    ]
    fields = _fields_by_id(artifact)
    map_index = artifact["field_evidence_columns"].index("code_map")
    assert fields[(2003, "ER21855")][map_index][0][3] == "Actual loss"
    assert fields[(2003, "ER21870")][map_index][1][3] == "Actual amount"
    assert fields[(2003, "ER21929")][map_index][0][3] == "Actual amount"


def test_vb8_later_branches_are_positive_but_composite_stays_residual():
    artifact = _artifact()
    enrollment = [
        fact
        for fact in artifact["era_facts"]
        if fact["fact_class"] == "regular_school_enrollment_branch"
    ]
    assert {
        (fact["interview_wave"], fact["branch"]) for fact in enrollment
    } == {
        (2013, "continuing_role_update"),
        (2015, "new_role_background"),
        (2015, "continuing_role_update"),
    }
    assert len(enrollment) == 6
    assert all(
        fact["stable_cross_wave_mapping_status"]
        == "registration_required_branch_and_freshness_composite"
        for fact in enrollment
    )
    residual_ids = {
        row["residual_id"]
        for row in artifact["registration_required_residuals"]
    }
    assert "ry2002_2014_modern_bc_de:V-B8:branch_freshness" in (residual_ids)
    assert (
        "ry2002_2014_modern_bc_de:" "V-B8:pre_2013_questionnaire_absence_proof"
    ) in residual_ids
    assert (
        "ry2002_2014_modern_bc_de:job_chronology_exposure_attachment"
        in residual_ids
    )
    assert (
        "ry2002_2014_modern_bc_de:job_amount_role_total_reconciliation"
        in residual_ids
    )


def test_modern_amount_and_unit_pages_have_exact_raw_stream_locators():
    artifact = _artifact()
    locators = {
        (row["source_document_id"], row["pdf_page"]): row
        for row in artifact["source_locators"]
    }
    amount_page = locators[("psid-family-2003-codebook", 56)]
    assert (amount_page["page_object"], amount_page["content_object"]) == (
        "174 0 R",
        "175 0 R",
    )
    assert (amount_page["byte_start"], amount_page["byte_end"]) == (
        108_575,
        110_192,
    )
    assert amount_page["range_sha256"] == (
        "9d655842a0aba6272176928b8f512cc75952b81121d44b730f223090ff54241b"
    )
    unit_page = locators[("psid-family-2003-codebook", 57)]
    assert (unit_page["page_object"], unit_page["content_object"]) == (
        "177 0 R",
        "178 0 R",
    )
    assert unit_page["range_sha256"] == (
        "6c6431b868037aa7e979a8ef5ec091d0ddb00e088598ac5d23763db810286bf5"
    )
