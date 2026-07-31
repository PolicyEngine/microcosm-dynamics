"""Tests for the frozen PSID year map and crosswalk boundary."""

from __future__ import annotations

import ast
import copy
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import pytest

from populace_dynamics.data import psid_covered_earnings_registry as registry


def _dictionary_audit_stub() -> dict:
    return {
        "inventory_ratification_abort": {
            "registration_required_item_ids": ["V-B5", "V-B6", "V-B8"]
        }
    }


def test_production_reference_year_domain_is_exact():
    rows = registry.production_year_rows()
    assert len(rows) == 55
    assert [row.earnings_reference_year for row in rows] == list(
        range(1968, 2023)
    )
    assert Counter(row.year_source_class for row in rows) == {
        "direct_questionnaire": 37,
        "structural_gap_imputed": 8,
        "claim_specific_boundary_gap": 1,
        "boundary_2014": 1,
        "projected": 8,
    }
    assert registry._canonical_hash(rows) == (
        registry.PRODUCTION_YEAR_ROWS_SHA256
    )
    for row in rows:
        if row.year_source_class == "direct_questionnaire":
            assert row.interview_wave == row.earnings_reference_year + 1
        else:
            assert row.interview_wave is None


def test_inventory_wave_domain_is_exact_and_always_wave_minus_one():
    rows = registry.inventory_wave_rows()
    assert len(rows) == 43
    assert [row.interview_wave for row in rows] == list(
        registry.STAGED_INTERVIEW_WAVES
    )
    assert Counter(row.inventory_year_disposition for row in rows) == {
        "direct_questionnaire": 37,
        "inventory_only_outside_production_support": 1,
        "inventory_only_post_cutoff": 5,
    }
    assert registry._canonical_hash(rows) == (
        registry.INVENTORY_WAVE_ROWS_SHA256
    )
    for row in rows:
        assert row.earnings_reference_year == row.interview_wave - 1


def test_boundary_2014_is_not_the_wave_2015_questionnaire_answer():
    assert registry.year_source_class(2014) == "boundary_2014"
    assert registry.direct_interview_wave(2014) is None
    assert registry.earnings_reference_year(2015) == 2014
    assert registry.inventory_year_disposition(2015) == (
        "inventory_only_post_cutoff"
    )


def test_invalid_years_and_boolean_years_fail_closed():
    for function, value in (
        (registry.year_source_class, 1967),
        (registry.year_source_class, 2023),
        (registry.earnings_reference_year, 1998),
        (registry.inventory_year_disposition, 2014),
        (registry.year_source_class, True),
        (registry.inventory_year_disposition, False),
    ):
        with pytest.raises(registry.ReferenceRegistryError):
            function(value)


def test_reference_eras_partition_through_the_boundary():
    registry.validate_reference_eras()
    assert [
        (
            spec.reference_era_id,
            spec.first_reference_year,
            spec.last_reference_year,
        )
        for spec in registry.REFERENCE_ERA_SPECS
    ] == [
        ("ry1968_1974_early_totals", 1968, 1974),
        ("ry1975_1977_spouse_concept_seam", 1975, 1977),
        ("ry1978_1992_pre_er_totals", 1978, 1992),
        ("ry1993_2001_er_biennial_transition", 1993, 2001),
        ("ry2002_2014_modern_boundary", 2002, 2014),
    ]
    for year in range(1968, 2015):
        spec = registry.reference_era(year)
        assert spec.first_reference_year <= year <= spec.last_reference_year


def test_source_concept_seams_preserve_mixed_and_exact_once_laws():
    seams = {row["seam_id"]: row for row in registry.SOURCE_CONCEPT_SEAMS}
    assert seams["spouse_reference_1975_mixed"] == {
        "seam_id": "spouse_reference_1975_mixed",
        "interview_wave": 1976,
        "earnings_reference_year": 1975,
        "role": "spouse_or_partner",
        "raw_field_id": "V4379",
        "remuneration_type": "mixed",
        "registration_required_item_id": None,
    }
    for seam_id, raw_field_id in (
        ("spouse_reference_1976_unresolved", "V5289"),
        ("spouse_reference_1977_unresolved", "V5788"),
    ):
        assert seams[seam_id]["raw_field_id"] == raw_field_id
        assert seams[seam_id]["remuneration_type"] is None
        assert seams[seam_id]["registration_required_item_id"] == "V-B6"
    assert (
        seams["pre_er_farm_business_exact_once"]["last_reference_year"] == 1992
    )
    assert seams["er_farm_business_exact_once"]["first_reference_year"] == 1993
    assert seams["er_farm_business_exact_once"]["first_interview_wave"] == 1994
    assert seams["modern_bc_de_direct"]["first_reference_year"] == 2002
    assert seams["modern_bc_de_direct"]["first_interview_wave"] == 2003


def test_source_concept_seams_are_immutable_and_independently_hashed():
    assert registry._canonical_hash(registry.SOURCE_CONCEPT_SEAMS) == (
        registry.SOURCE_CONCEPT_SEAMS_SHA256
    )
    v4379 = next(
        row
        for row in registry.SOURCE_CONCEPT_SEAMS
        if row.get("raw_field_id") == "V4379"
    )
    with pytest.raises(TypeError):
        v4379["remuneration_type"] = "wages_only"


def test_v4379_concept_mutation_fails_frozen_registry_validation(monkeypatch):
    seams = tuple(dict(row) for row in registry.SOURCE_CONCEPT_SEAMS)
    v4379 = next(row for row in seams if row.get("raw_field_id") == "V4379")
    v4379["remuneration_type"] = "wages_only"
    monkeypatch.setattr(registry, "SOURCE_CONCEPT_SEAMS", seams)

    with pytest.raises(
        registry.ReferenceRegistryError,
        match="source concept seam registry hash drifted",
    ):
        registry.validate_frozen_registry()


@pytest.mark.parametrize(
    "mutation",
    [
        "delete",
        "extra",
        "duplicate",
        "reorder",
        "wrong_source_class",
        "wrong_direct_wave",
        "gap_with_wave",
    ],
)
def test_production_domain_mutations_fail_independent_comparison(mutation):
    rows = [asdict(row) for row in registry.production_year_rows()]
    if mutation == "delete":
        rows.pop()
    elif mutation == "extra":
        rows.append(copy.deepcopy(rows[-1]))
        rows[-1]["earnings_reference_year"] = 2023
    elif mutation == "duplicate":
        rows.append(copy.deepcopy(rows[-1]))
    elif mutation == "reorder":
        rows[0], rows[1] = rows[1], rows[0]
    elif mutation == "wrong_source_class":
        rows[0]["year_source_class"] = "projected"
    elif mutation == "wrong_direct_wave":
        rows[0]["interview_wave"] = 1970
    elif mutation == "gap_with_wave":
        gap = next(
            row
            for row in rows
            if row["year_source_class"] == "structural_gap_imputed"
        )
        gap["interview_wave"] = gap["earnings_reference_year"] + 1
    with pytest.raises(registry.ReferenceRegistryError, match="exact-match"):
        registry.validate_production_year_rows(rows)


def test_official_crosswalk_is_v2_and_fails_closed():
    audit = _dictionary_audit_stub()
    status = registry.crosswalk_registration_status(audit)
    assert status == {
        "target_schema_version": "psid_covered_earnings_crosswalk.v2",
        "target_artifact_id": "psid_covered_earnings_crosswalk.v2",
        "status": "registration_required",
        "failure_disposition": "abort_crosswalk_registration",
        "unavailable_prerequisites": [
            "psid_questionnaire_slot_specs.v1",
            "psid_covered_earnings_source_field_inventory.v1",
        ],
        "registration_required_item_ids": ["V-B5", "V-B6", "V-B8"],
    }
    with pytest.raises(
        registry.CrosswalkRegistrationRequiredError,
        match="psid_covered_earnings_crosswalk.v2",
    ) as exc:
        registry.require_ratified_crosswalk(audit)
    assert exc.value.item_ids == ("V-B5", "V-B6", "V-B8")


def test_year_registry_imports_no_reader_or_inventory_artifact():
    source = Path(registry.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "populace_dynamics.data.family" not in imported
    assert "populace_dynamics.data.psid_questionnaire_inventory" not in (
        imported
    )
