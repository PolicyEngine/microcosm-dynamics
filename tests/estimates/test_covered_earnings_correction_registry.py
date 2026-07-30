"""Tests for the fail-closed entry-11 registration boundary."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import covered_earnings_correction_registry as registry  # noqa: E402


def _complete_shape_row() -> dict:
    year = 1968
    source_cells = [
        "table4.b2/1968/c5",
        "table4.b2/1968/c11",
    ]
    return {
        "target_id": "b2_wage_total_intensity:1968",
        "target_family": "b2_wage_total_intensity",
        "target_year": year,
        "verified_calendar_year": year,
        "role_rule_id": registry.ROLE_RULE_ID,
        "dependency_group": "b2_component_system",
        "source_artifact_vintage_id": ("future_authoritative_source_artifact"),
        "source_cell_ids": source_cells,
        "resolved_observation_ids": [
            "observation:table4.b2/1968/c5",
            "observation:table4.b2/1968/c11",
        ],
        "physical_source_cell_ids": [
            "physical:future:table4.b2:1968:c5",
            "physical:future:table4.b2:1968:c11",
        ],
        "primitive_ancestry_ids": [
            "physical:future:table4.b2:1968:c5",
            "physical:future:table4.b2:1968:c11",
        ],
        "source_year": year,
        "source_status": "historical",
        "model_year_source_class": "direct_questionnaire",
        "universe": {
            "publication_scope": "future-source-derived-scope",
            "geography": "future-source-derived-geography",
            "population": "future-source-derived-population",
            "time_basis": "calendar_year",
            "worker_unit": "future-source-derived-worker-unit",
            "duplicate_worker_rule": "future-source-derived-rule",
            "zero_earner_rule": "future-source-derived-rule",
        },
        "transformation": {
            "operation": "divide",
            "operand_cell_ids": source_cells,
            "formula": "c5/c11",
            "domain": "strictly_positive_ratio",
        },
        "stored_unit": "current_dollars_per_worker",
        "published_rounding_interval": {
            "status": "not_established_from_source_bytes"
        },
        "model_universe_id": "future_frozen_selector",
        "model_weight_field": "future_registered_weight",
        "model_weight_source_sha256": "1" * 64,
        "universe_concordance": {
            "official_ratio_universe": "future-official-universe",
            "model_analogue_universe": "future-model-universe",
            "element_mappings": [
                {
                    "official_element": "worker",
                    "model_rule": "future-frozen-rule",
                    "status": "exact_concept_match",
                },
                {
                    "official_element": "national-frame",
                    "model_rule": "closed-model-frame",
                    "status": "registered_frame_difference",
                },
            ],
            "frame_relation": "frame_relative_not_population_aligned",
            "verification_status": "pass",
            "source_sha256": "2" * 64,
        },
        "declared_role": "train",
        "effective_role": "train",
        "loss": "squared_log_ratio",
        "loss_weight": 0.0,
        "cell_tolerance": {"applicability": "not_selection_gate"},
        "family_tolerance": {"applicability": "not_selection_gate"},
        "selection_eligible": False,
        "candidate_output_selector": {
            "calendar_year": year,
            "year_source_class": "direct_questionnaire",
            "availability": "available",
            "field_ids": ["future_field"],
            "aggregation": "sum(future_field)",
            "joint_probability_rule": "future-frozen-rule",
            "cap_stage": "future-frozen-stage",
            "projection_draw_reduction": "arithmetic_mean_over_20_draws",
            "unit": "current_dollars_per_worker",
        },
    }


def test__target_schema__is_exactly_the_designs_30_fields():
    expected = (
        "target_id",
        "target_family",
        "target_year",
        "verified_calendar_year",
        "role_rule_id",
        "dependency_group",
        "source_artifact_vintage_id",
        "source_cell_ids",
        "resolved_observation_ids",
        "physical_source_cell_ids",
        "primitive_ancestry_ids",
        "source_year",
        "source_status",
        "model_year_source_class",
        "universe",
        "transformation",
        "stored_unit",
        "published_rounding_interval",
        "model_universe_id",
        "model_weight_field",
        "model_weight_source_sha256",
        "universe_concordance",
        "declared_role",
        "effective_role",
        "loss",
        "loss_weight",
        "cell_tolerance",
        "family_tolerance",
        "selection_eligible",
        "candidate_output_selector",
    )
    assert len(expected) == 30
    assert registry.CALIBRATION_TARGET_SPEC_FIELDS == expected
    assert registry.calibration_target_schema()["row_fields"] == list(expected)
    registry.validate_calibration_target_row_schema(_complete_shape_row())


@pytest.mark.parametrize(
    "field",
    (
        "universe",
        "model_universe_id",
        "model_weight_field",
        "model_weight_source_sha256",
        "universe_concordance",
    ),
)
def test__target_schema__rejects_each_round_1_omission(field):
    row = _complete_shape_row()
    del row[field]
    with pytest.raises(registry.RegistryValidationError, match="wrong fields"):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__rejects_the_old_reduced_25_field_shape():
    row = _complete_shape_row()
    for field in (
        "universe",
        "model_universe_id",
        "model_weight_field",
        "model_weight_source_sha256",
        "universe_concordance",
    ):
        del row[field]
    with pytest.raises(
        registry.RegistryValidationError,
        match="model_universe_id.*model_weight_field.*universe",
    ):
        registry.validate_calibration_target_specs([row])


def test__target_schema__requires_exact_source_derived_universe_shape():
    row = _complete_shape_row()
    del row["universe"]["zero_earner_rule"]
    with pytest.raises(
        registry.RegistryValidationError,
        match="zero_earner_rule",
    ):
        registry.validate_calibration_target_row_schema(row)


@pytest.mark.parametrize(
    ("path", "value", "match"),
    (
        (
            ("model_weight_source_sha256",),
            "not-a-digest",
            "model_weight_source_sha256",
        ),
        (
            ("universe_concordance", "verification_status"),
            "unresolved",
            "verification_status",
        ),
        (
            ("universe_concordance", "frame_relation"),
            "population_aligned",
            "frame_relation",
        ),
        (
            (
                "universe_concordance",
                "element_mappings",
                0,
                "status",
            ),
            "invented_status",
            "status",
        ),
    ),
)
def test__target_schema__requires_passing_hashed_concordance(
    path: tuple[object, ...],
    value: object,
    match: str,
):
    row = _complete_shape_row()
    cursor = row
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(registry.RegistryValidationError, match=match):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__recomputes_year_role_and_source_class():
    row = _complete_shape_row()
    row["declared_role"] = "validation"
    with pytest.raises(registry.RegistryValidationError, match="recomputed"):
        registry.validate_calibration_target_row_schema(row)
    row = _complete_shape_row()
    row["model_year_source_class"] = "structural_gap_imputed"
    with pytest.raises(registry.RegistryValidationError, match="class drift"):
        registry.validate_calibration_target_row_schema(row)


def test__registration_status__resolves_all_five_missing_authorities():
    status = registry.registration_status()
    assert status["registration_complete"] is False
    assert status["emitted_target_row_count"] == 0
    assert status["covered_share_required_years"] == []
    assert status["vb7_registration_disposition"] == (
        "abort_no_authoritative_vintage2_or_calibration_target_specs"
    )
    assert {
        item["field"] for item in status["unresolved_authority_fields"]
    } == {
        "universe",
        "model_universe_id",
        "model_weight_field",
        "model_weight_source_sha256",
        "universe_concordance",
    }
    membership = {
        row["family"]: row["verdict"]
        for row in status["membership_adjudications"]
    }
    assert membership == {
        "b2_wage_total_intensity": "fail_closed",
        "b2_se_total_intensity": "fail_closed",
        "b11_worker_distribution": "fail_closed",
    }


@pytest.mark.parametrize(
    "getter",
    (
        registry.calibration_target_specs,
        registry.physical_source_cell_specs,
        registry.official_source_alias_specs,
        registry.official_source_arithmetic_rule_specs,
        registry.frozen_registries,
    ),
)
def test__final_registry_getters__all_abort(getter):
    with pytest.raises(
        registry.RegistrationAborted,
        match="V-B7=.*abort_no_authoritative",
    ):
        getter()


def test__complete_shape_is_not_mistaken_for_complete_authority():
    row = _complete_shape_row()
    with pytest.raises(
        registry.RegistrationAborted,
        match="unresolved fields=universe",
    ):
        registry.validate_calibration_target_specs([copy.deepcopy(row)])


def test__verified_role_specs__remain_exact_and_value_independent():
    assert registry.verified_role_specs() == {
        "schema_version": "verified_role_specs.v1",
        "role_rule_id": registry.ROLE_RULE_ID,
        "year_basis": "verified_calendar_year",
        "ordered_ranges": [
            {"first_year": 1968, "last_year": 2008, "role": "train"},
            {"first_year": 2009, "last_year": 2014, "role": "validation"},
            {
                "first_year": 2015,
                "last_year": 2022,
                "role": "held_out_diagnostic",
            },
        ],
        "role_order": ["train", "validation", "held_out_diagnostic"],
        "derivation": "recompute_never_trust_declared_role",
        "failure_disposition": "abort",
    }
    assert registry.role_for_year(1968) == "train"
    assert registry.role_for_year(2014) == "validation"
    assert registry.role_for_year(2022) == "held_out_diagnostic"
    with pytest.raises(registry.RegistryValidationError):
        registry.role_for_year(True)
