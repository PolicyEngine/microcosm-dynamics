"""Tests for the amended entry-11 registration boundary."""

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
        "source_artifact_vintage_id": (
            registry.PROPOSED_SOURCE_ARTIFACT_VINTAGE_ID
        ),
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
            "status": "not_established_from_source_bytes",
            "lower": None,
            "upper": None,
            "lower_closed": None,
            "upper_closed": None,
            "rule_source_document_id": None,
            "rule_citation": None,
        },
        "model_universe_id": "future_frozen_selector",
        "model_weight_field": "weight",
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
        "loss_weight": 2,
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


LOSS_BY_FAMILY = {
    "b2_wage_total_intensity": "squared_log_ratio",
    "b2_se_total_intensity": "squared_log_ratio",
    "b11_se_only_worker_share": "squared_logit_error",
    "b11_dual_type_worker_share": "squared_logit_error",
    "b11_wage_only_worker_share": "no_fitting_loss",
    "b2_type_count_mix": "no_fitting_loss",
    "b2_se_total_component_share": "no_fitting_loss",
    "b2_wage_taxable_intensity": "no_fitting_loss",
    "b2_se_taxable_intensity": "no_fitting_loss",
    "b2_wage_taxable_fraction": "no_fitting_loss",
    "b2_se_taxable_fraction": "no_fitting_loss",
    "b11_taxable_earnings_component_reconciliation": "no_fitting_loss",
    "b11_contributions_component_reconciliation": "no_fitting_loss",
    "b11_se_contribution_share": "no_fitting_loss",
}
SOURCE_COMPONENTS_BY_FAMILY = {
    "b2_wage_total_intensity": ("table4.b2", ("c5", "c11")),
    "b2_se_total_intensity": ("table4.b2", ("c8", "c12")),
    "b11_se_only_worker_share": (
        "table4.b11",
        ("workers_total", "workers_wage"),
    ),
    "b11_dual_type_worker_share": (
        "table4.b11",
        ("workers_total", "workers_wage", "workers_self_employment"),
    ),
    "b11_wage_only_worker_share": (
        "table4.b11",
        ("workers_total", "workers_self_employment"),
    ),
    "b2_type_count_mix": ("table4.b2", ("c11", "c12")),
    "b2_se_total_component_share": ("table4.b2", ("c5", "c8")),
    "b2_wage_taxable_intensity": ("table4.b2", ("c11", "c13")),
    "b2_se_taxable_intensity": ("table4.b2", ("c12", "c17")),
    "b2_wage_taxable_fraction": ("table4.b2", ("c5", "c13")),
    "b2_se_taxable_fraction": ("table4.b2", ("c8", "c17")),
    "b11_taxable_earnings_component_reconciliation": (
        "table4.b11",
        (
            "taxable_earnings_total",
            "taxable_earnings_wage",
            "taxable_earnings_self_employment",
        ),
    ),
    "b11_contributions_component_reconciliation": (
        "table4.b11",
        (
            "contributions_total",
            "contributions_wage",
            "contributions_self_employment",
        ),
    ),
    "b11_se_contribution_share": (
        "table4.b11",
        ("contributions_wage", "contributions_self_employment"),
    ),
}
FITTING_FAMILIES = {
    family
    for family, loss in LOSS_BY_FAMILY.items()
    if loss != "no_fitting_loss"
}
RAW_FAMILY_COEFFICIENT = {
    "b2_wage_total_intensity": 2,
    "b2_se_total_intensity": 2,
    "b11_se_only_worker_share": 1,
    "b11_dual_type_worker_share": 1,
}
DEPENDENCY_GROUP_BY_FAMILY = {
    "b2_wage_total_intensity": "b2_component_system",
    "b2_se_total_intensity": "b2_component_system",
    "b11_se_only_worker_share": "b11_worker_type_system",
    "b11_dual_type_worker_share": "b11_worker_type_system",
    "b11_wage_only_worker_share": "b11_worker_type_system",
    "b2_type_count_mix": "b2_component_system",
    "b2_se_total_component_share": "b2_component_system",
    "b2_wage_taxable_intensity": "b2_component_system",
    "b2_se_taxable_intensity": "b2_component_system",
    "b2_wage_taxable_fraction": "b2_component_system",
    "b2_se_taxable_fraction": "b2_component_system",
    "b11_taxable_earnings_component_reconciliation": (
        "b11_taxable_earnings_component_system"
    ),
    "b11_contributions_component_reconciliation": (
        "b11_contribution_component_system"
    ),
    "b11_se_contribution_share": "b11_contribution_component_system",
}
AVAILABLE_SOURCE_CLASSES = {
    "direct_questionnaire",
    "boundary_2014",
    "projected",
}
UNAVAILABLE_AVAILABILITY = "not_applicable_no_claim_independent_model_analogue"
SELECTOR_SCALAR_FIELDS = (
    "aggregation",
    "joint_probability_rule",
    "cap_stage",
    "projection_draw_reduction",
    "unit",
)


def _selection_tolerances(family: str) -> tuple[dict, dict]:
    if family in {
        "b2_wage_total_intensity",
        "b2_se_total_intensity",
    }:
        return (
            {
                "applicability": "selection_gate",
                "metric": "absolute_log_error",
                "maximum": 0.09531017980432493,
            },
            {
                "applicability": "selection_gate",
                "metric": "rms_absolute_log_error",
                "maximum": 0.04879016416943205,
            },
        )
    maxima = (0.03, 0.015)
    return (
        {
            "applicability": "selection_gate",
            "metric": "absolute_share_error",
            "maximum": maxima[0],
        },
        {
            "applicability": "selection_gate",
            "metric": "rms_absolute_share_error",
            "maximum": maxima[1],
        },
    )


def _row_for(
    year: int,
    family: str = "b2_wage_total_intensity",
) -> dict:
    row = _complete_shape_row()
    row["target_id"] = f"{family}:{year}"
    row["target_family"] = family
    row["dependency_group"] = DEPENDENCY_GROUP_BY_FAMILY[family]
    for field in ("target_year", "verified_calendar_year", "source_year"):
        row[field] = year
    table_id, component_ids = SOURCE_COMPONENTS_BY_FAMILY[family]
    source_cells = [
        f"{table_id}/{year}/{component_id}" for component_id in component_ids
    ]
    row["source_cell_ids"] = source_cells
    row["resolved_observation_ids"] = [
        f"observation:{source_cell_id}" for source_cell_id in source_cells
    ]
    physical_ids = [
        f"physical:future:{table_id}:{year}:{component_id}"
        for component_id in component_ids
    ]
    row["physical_source_cell_ids"] = physical_ids
    row["primitive_ancestry_ids"] = list(physical_ids)
    row["transformation"]["operand_cell_ids"] = list(row["source_cell_ids"])
    row["source_status"] = "preliminary" if year >= 2021 else "historical"
    source_class = registry.model_year_source_class_for_year(year)
    role = registry.role_for_year(year)
    row["model_year_source_class"] = source_class
    row["declared_role"] = role
    row["effective_role"] = role
    selector = row["candidate_output_selector"]
    selector["calendar_year"] = year
    selector["year_source_class"] = source_class
    if source_class in AVAILABLE_SOURCE_CLASSES:
        selector["availability"] = "available"
    else:
        selector["availability"] = UNAVAILABLE_AVAILABILITY
        selector["field_ids"] = []
        for field in SELECTOR_SCALAR_FIELDS:
            selector[field] = None
    row["loss"] = LOSS_BY_FAMILY[family]
    selection_eligible = (
        role == "validation"
        and family in FITTING_FAMILIES
        and source_class in {"direct_questionnaire", "boundary_2014"}
    )
    row["selection_eligible"] = selection_eligible
    model_choice_cell = source_class in AVAILABLE_SOURCE_CLASSES and (
        (
            role == "train"
            and source_class == "direct_questionnaire"
            and family in FITTING_FAMILIES
        )
        or selection_eligible
    )
    row["loss_weight"] = (
        RAW_FAMILY_COEFFICIENT[family] if model_choice_cell else 0
    )
    if selection_eligible:
        (
            row["cell_tolerance"],
            row["family_tolerance"],
        ) = _selection_tolerances(family)
    return row


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
    assert registry.CALIBRATION_TARGET_SPECS_SCHEMA_VERSION == (
        "calibration_target_specs.v3"
    )
    assert registry.CALIBRATION_TARGET_SPEC_FIELDS == expected
    assert len(registry.TARGET_FAMILY_ORDER) == 14
    assert "ssa_precisely_universed_covered_share" not in (
        registry.TARGET_FAMILY_ORDER
    )
    schema = registry.calibration_target_schema()
    assert schema["row_fields"] == list(expected)
    assert schema["published_rounding_interval_fields"] == [
        "status",
        "lower",
        "upper",
        "lower_closed",
        "upper_closed",
        "rule_source_document_id",
        "rule_citation",
    ]
    assert schema["tolerance_not_applicable_fields"] == ["applicability"]
    assert schema["tolerance_selection_gate_fields"] == [
        "applicability",
        "metric",
        "maximum",
    ]
    registry.validate_calibration_target_row_schema(_complete_shape_row())


def test__target_family_registry__pins_order_dependencies_and_weights():
    rows = registry.target_family_registry()
    assert [row["target_family"] for row in rows] == list(
        registry.TARGET_FAMILY_ORDER
    )
    assert len(rows) == 14
    by_family = {row["target_family"]: row for row in rows}
    assert {
        family: row["raw_family_coefficient"]
        for family, row in by_family.items()
        if row["raw_family_coefficient"]
    } == RAW_FAMILY_COEFFICIENT
    assert (
        by_family["b2_wage_total_intensity"][
            "normalized_effective_weight_numerator"
        ]
        == 2
    )
    assert (
        by_family["b2_wage_total_intensity"][
            "normalized_effective_weight_denominator"
        ]
        == 6
    )
    assert (
        by_family["b11_dual_type_worker_share"][
            "normalized_effective_weight_numerator"
        ]
        == 1
    )
    assert (
        by_family["b11_dual_type_worker_share"][
            "normalized_effective_weight_denominator"
        ]
        == 6
    )
    assert all(
        row["normalized_effective_weight_denominator"] == 1
        for row in rows
        if row["raw_family_coefficient"] == 0
    )


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


def test__target_schema__accepts_exact_unavailable_rounding_tag():
    row = _row_for(1968)
    registry.validate_calibration_target_row_schema(row)


@pytest.mark.parametrize(
    "interval",
    (
        {"status": "not_established_from_source_bytes"},
        {
            "status": "invented",
            "lower": None,
            "upper": None,
            "lower_closed": None,
            "upper_closed": None,
            "rule_source_document_id": None,
            "rule_citation": None,
        },
        {
            "status": "not_established_from_source_bytes",
            "lower": 0,
            "upper": None,
            "lower_closed": None,
            "upper_closed": None,
            "rule_source_document_id": None,
            "rule_citation": None,
        },
        {
            "status": "source_verified",
            "lower": float("nan"),
            "upper": 1,
            "lower_closed": True,
            "upper_closed": True,
            "rule_source_document_id": "source",
            "rule_citation": "citation",
        },
        {
            "status": "source_verified",
            "lower": 10**1000,
            "upper": 10**1000,
            "lower_closed": True,
            "upper_closed": True,
            "rule_source_document_id": "source",
            "rule_citation": "citation",
        },
        {
            "status": "source_verified",
            "lower": 2,
            "upper": 1,
            "lower_closed": True,
            "upper_closed": True,
            "rule_source_document_id": "source",
            "rule_citation": "citation",
        },
        {
            "status": "source_verified",
            "lower": 1,
            "upper": 2,
            "lower_closed": 1,
            "upper_closed": True,
            "rule_source_document_id": "source",
            "rule_citation": "citation",
        },
        {
            "status": "source_verified",
            "lower": 1,
            "upper": 2,
            "lower_closed": True,
            "upper_closed": True,
            "rule_source_document_id": "",
            "rule_citation": "citation",
        },
    ),
)
def test__target_schema__rejects_invalid_rounding_tags(interval):
    row = _complete_shape_row()
    row["published_rounding_interval"] = interval
    with pytest.raises(registry.RegistryValidationError):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__never_infers_structural_sibling_rounding():
    row = _row_for(
        1968,
        "b11_contributions_component_reconciliation",
    )
    row["published_rounding_interval"] = {
        "status": "source_verified",
        "lower": -1,
        "upper": 1,
        "lower_closed": True,
        "upper_closed": True,
        "rule_source_document_id": "future_verified_source",
        "rule_citation": "future-pinned-byte-citation",
    }
    with pytest.raises(
        registry.RegistryValidationError,
        match="B2/B11 source bytes",
    ):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__requires_the_literal_vintage2_artifact_id():
    row = _complete_shape_row()
    row["source_artifact_vintage_id"] = "wrong_artifact_vintage"
    with pytest.raises(
        registry.RegistryValidationError,
        match="source_artifact_vintage_id",
    ):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__leaves_opaque_identity_resolution_to_full_registry():
    row = _complete_shape_row()
    row["resolved_observation_ids"] = [
        f"observation:{index}:{'1' * 64}"
        for index, _ in enumerate(row["source_cell_ids"])
    ]
    row["physical_source_cell_ids"] = [f"physical:{'2' * 64}"]
    row["primitive_ancestry_ids"] = [f"physical:{'3' * 64}"]
    registry.validate_calibration_target_row_schema(row)
    with pytest.raises(registry.RegistryValidationError, match="14-family"):
        registry.validate_calibration_target_specs([row])


def test__target_schema__rejects_wrong_or_non_ascii_source_cell_years():
    row = _complete_shape_row()
    row["source_cell_ids"] = [
        value.replace("/1968/", "/2022/") for value in row["source_cell_ids"]
    ]
    row["transformation"]["operand_cell_ids"] = list(row["source_cell_ids"])
    with pytest.raises(
        registry.RegistryValidationError,
        match="year-equality law",
    ):
        registry.validate_calibration_target_row_schema(row)

    row = _complete_shape_row()
    row["source_cell_ids"][0] = "table4.b2/１９６８/c5"
    row["transformation"]["operand_cell_ids"] = list(row["source_cell_ids"])
    with pytest.raises(
        registry.RegistryValidationError,
        match="ASCII calendar year",
    ):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__rejects_same_year_wrong_family_source_cells():
    row = _complete_shape_row()
    row["source_cell_ids"][0] = "table4.b2/1968/c8"
    row["transformation"]["operand_cell_ids"] = list(row["source_cell_ids"])
    with pytest.raises(
        registry.RegistryValidationError,
        match="target-family law",
    ):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__rejects_reordered_source_operands():
    row = _complete_shape_row()
    row["source_cell_ids"].reverse()
    row["transformation"]["operand_cell_ids"] = list(row["source_cell_ids"])
    with pytest.raises(
        registry.RegistryValidationError,
        match="target-family law",
    ):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__requires_one_observation_per_logical_source_cell():
    row = _complete_shape_row()
    row["resolved_observation_ids"].pop()
    with pytest.raises(
        registry.RegistryValidationError,
        match="one-to-one",
    ):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__enforces_status_role_and_source_artifact_laws():
    row = _complete_shape_row()
    row["source_status"] = "preliminary"
    with pytest.raises(
        registry.RegistryValidationError,
        match="preliminary outside held-out",
    ):
        registry.validate_calibration_target_row_schema(row)

    preliminary_b2 = _row_for(2021)
    registry.validate_calibration_target_row_schema(preliminary_b2)
    preliminary_b2["source_status"] = "historical"
    with pytest.raises(
        registry.RegistryValidationError,
        match="source artifact law",
    ):
        registry.validate_calibration_target_row_schema(preliminary_b2)


@pytest.mark.parametrize(
    ("family", "expected_loss"),
    tuple(LOSS_BY_FAMILY.items()),
)
def test__target_schema__enforces_each_family_loss(family, expected_loss):
    row = _row_for(1968, family)
    assert row["loss"] == expected_loss
    registry.validate_calibration_target_row_schema(row)
    row["loss"] = (
        "no_fitting_loss"
        if expected_loss != "no_fitting_loss"
        else "squared_log_ratio"
    )
    with pytest.raises(registry.RegistryValidationError, match="\\.loss"):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__hard_zeros_no_fitting_loss_weight_and_selection():
    row = _row_for(1968, "b11_wage_only_worker_share")
    row["loss_weight"] = 99
    with pytest.raises(
        registry.RegistryValidationError,
        match="integer mass 0",
    ):
        registry.validate_calibration_target_row_schema(row)

    row = _row_for(1968, "b11_wage_only_worker_share")
    row["selection_eligible"] = True
    with pytest.raises(
        registry.RegistryValidationError,
        match="selection_eligible",
    ):
        registry.validate_calibration_target_row_schema(row)


@pytest.mark.parametrize(
    ("year", "availability"),
    (
        (1968, "available"),
        (1997, UNAVAILABLE_AVAILABILITY),
        (2009, UNAVAILABLE_AVAILABILITY),
        (2010, "available"),
        (2013, UNAVAILABLE_AVAILABILITY),
        (2014, "available"),
        (2015, "available"),
    ),
)
def test__target_schema__derives_availability_from_source_class(
    year,
    availability,
):
    row = _row_for(year)
    assert row["candidate_output_selector"]["availability"] == availability
    registry.validate_calibration_target_row_schema(row)
    row["candidate_output_selector"]["availability"] = (
        UNAVAILABLE_AVAILABILITY
        if availability == "available"
        else "available"
    )
    with pytest.raises(registry.RegistryValidationError, match="availability"):
        registry.validate_calibration_target_row_schema(row)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("field_ids", ["retained_field"]),
        ("aggregation", "retained_aggregation"),
        ("joint_probability_rule", "retained_joint_rule"),
        ("cap_stage", "retained_cap_stage"),
        (
            "projection_draw_reduction",
            "arithmetic_mean_over_20_draws",
        ),
        ("unit", "retained_unit"),
    ),
)
def test__target_schema__unavailable_selector_retains_no_model_fields(
    field,
    value,
):
    row = _row_for(1997)
    row["candidate_output_selector"][field] = value
    with pytest.raises(registry.RegistryValidationError, match=field):
        registry.validate_calibration_target_row_schema(row)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("field_ids", []),
        ("aggregation", None),
        ("joint_probability_rule", None),
        ("cap_stage", None),
        ("projection_draw_reduction", "different_reduction"),
        ("unit", "different_unit"),
    ),
)
def test__target_schema__available_selector_requires_complete_model_fields(
    field,
    value,
):
    row = _complete_shape_row()
    row["candidate_output_selector"][field] = value
    with pytest.raises(registry.RegistryValidationError, match=field):
        registry.validate_calibration_target_row_schema(row)


@pytest.mark.parametrize("year", (1997, 2015))
def test__target_schema__gap_and_held_out_weights_are_zero(year):
    row = _row_for(year)
    row["loss_weight"] = 1
    with pytest.raises(
        registry.RegistryValidationError,
        match="integer mass 0",
    ):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__requires_exact_integer_mass_on_model_choice_cells():
    train = _row_for(1968)
    assert train["loss_weight"] == 2
    registry.validate_calibration_target_row_schema(train)

    validation = _row_for(2010)
    assert validation["loss_weight"] == 2
    registry.validate_calibration_target_row_schema(validation)

    b11 = _row_for(1968, "b11_dual_type_worker_share")
    assert b11["loss_weight"] == 1
    registry.validate_calibration_target_row_schema(b11)

    train["loss_weight"] = 1
    with pytest.raises(
        registry.RegistryValidationError, match="integer mass 2"
    ):
        registry.validate_calibration_target_row_schema(train)


@pytest.mark.parametrize(
    ("year", "expected"),
    (
        (2009, False),
        (2010, True),
        (2011, False),
        (2012, True),
        (2013, False),
        (2014, True),
    ),
)
def test__target_schema__enforces_validation_selection_matrix(year, expected):
    row = _row_for(year)
    assert row["selection_eligible"] is expected
    registry.validate_calibration_target_row_schema(row)
    row["selection_eligible"] = not expected
    with pytest.raises(
        registry.RegistryValidationError,
        match="selection_eligible",
    ):
        registry.validate_calibration_target_row_schema(row)


@pytest.mark.parametrize("family", tuple(sorted(FITTING_FAMILIES)))
def test__target_schema__pins_selection_tolerances_by_family(family):
    row = _row_for(2010, family)
    expected_cell, expected_family = _selection_tolerances(family)
    assert row["cell_tolerance"] == expected_cell
    assert row["family_tolerance"] == expected_family
    registry.validate_calibration_target_row_schema(row)


@pytest.mark.parametrize(
    ("field", "subfield", "value"),
    (
        ("cell_tolerance", "metric", "wrong_metric"),
        ("cell_tolerance", "maximum", 0.03),
        ("family_tolerance", "metric", "wrong_metric"),
        ("family_tolerance", "maximum", float("inf")),
    ),
)
def test__target_schema__rejects_wrong_selection_tolerances(
    field,
    subfield,
    value,
):
    row = _row_for(2010)
    row[field][subfield] = value
    with pytest.raises(registry.RegistryValidationError, match=field):
        registry.validate_calibration_target_row_schema(row)


def test__target_schema__nongating_rows_have_exact_one_key_tolerances():
    row = _complete_shape_row()
    row["cell_tolerance"] = {
        "applicability": "selection_gate",
        "metric": "absolute_log_error",
        "maximum": 0.09531017980432493,
    }
    with pytest.raises(
        registry.RegistryValidationError,
        match="cell_tolerance",
    ):
        registry.validate_calibration_target_row_schema(row)


def test__registration_status__accepts_source_and_resolves_weight_field():
    status = registry.registration_status()
    assert status["registration_complete"] is False
    assert status["source_artifact_status"] == "accepted"
    assert status["source_artifact_schema_version"] == (
        "ssa_covered_earnings_calibration_targets.v2"
    )
    assert status["source_artifact_lineage_suffixes"] == [2]
    assert status["optional_covered_share_status"] == (
        "unavailable_source_absent"
    )
    assert status["calibration_target_schema_version"] == (
        "calibration_target_specs.v3"
    )
    assert status["target_family_order"] == list(registry.TARGET_FAMILY_ORDER)
    assert status["emitted_target_row_count"] == 0
    assert status["resolved_authority_fields"] == [
        {
            "field": "model_weight_field",
            "status": "resolved_from_committed_first_estimates_authority",
            "value": "weight",
            "authority_id": (
                "first_estimates_fixed_start_wave_psid_cross_sectional_"
                "weight_v1"
            ),
        }
    ]
    assert {
        item["field"] for item in status["unresolved_authority_fields"]
    } == {
        "universe",
        "model_universe_id",
        "model_weight_source_sha256",
        "denominator_and_joint_analytic_selectors",
        "universe_concordance",
    }
    assert len(status["registration_authority_adjudications"]) == 5
    assert len(status["family_dispositions"]) == 14
    assert {row["verdict"] for row in status["family_dispositions"]} == {
        "fail_closed"
    }


def test__accepted_source_artifact__requires_exact_tracked_bytes():
    artifact = registry.accepted_source_artifact()
    assert artifact["artifact_vintage_id"] == (
        "ssa_covered_earnings_calibration_targets.vintage2"
    )
    assert artifact["optional_covered_share"] == (
        registry.extraction.OPTIONAL_COVERED_SHARE_UNAVAILABLE
    )


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
        match="source artifact accepted; no target family",
    ):
        getter()


def test__complete_shape_is_not_mistaken_for_complete_authority():
    row = _complete_shape_row()
    with pytest.raises(
        registry.RegistryValidationError,
        match="14-family",
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
