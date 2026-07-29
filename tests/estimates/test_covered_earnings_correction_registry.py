"""Tests for the frozen entry-11 B2/B11 target registries."""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
ARTIFACT = (
    ROOT
    / "data"
    / "external"
    / "ssa_covered_earnings_calibration_targets_vintage2.json"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import covered_earnings_correction_registry as registry  # noqa: E402


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_bytes())


def _target(target_id: str) -> dict:
    return next(
        row
        for row in registry.calibration_target_specs()
        if row["target_id"] == target_id
    )


def test__target_registry__pins_schema_order_and_complete_b2_b11_expansion():
    rows = registry.calibration_target_specs()
    assert registry.CALIBRATION_TARGET_SPECS_SCHEMA_VERSION == (
        "calibration_target_specs.v2"
    )
    assert registry.TARGET_FAMILY_ORDER == (
        "b2_wage_total_intensity",
        "b2_se_total_intensity",
        "b11_se_only_worker_share",
        "b11_dual_type_worker_share",
        "b11_wage_only_worker_share",
        "b2_type_count_mix",
        "b2_se_total_component_share",
        "b2_wage_taxable_intensity",
        "b2_se_taxable_intensity",
        "b2_wage_taxable_fraction",
        "b2_se_taxable_fraction",
        "b11_taxable_earnings_component_reconciliation",
        "b11_contributions_component_reconciliation",
        "b11_se_contribution_share",
    )
    assert len(rows) == 14 * 55 == 770
    assert [(row["target_family"], row["target_year"]) for row in rows] == [
        (family, year)
        for family in registry.TARGET_FAMILY_ORDER
        for year in range(1968, 2023)
    ]
    assert all(
        set(row)
        == {
            "candidate_output_selector",
            "cell_tolerance",
            "declared_role",
            "dependency_group",
            "effective_role",
            "family_tolerance",
            "loss",
            "loss_weight",
            "model_year_source_class",
            "physical_source_cell_ids",
            "primitive_ancestry_ids",
            "published_rounding_interval",
            "resolved_observation_ids",
            "role_rule_id",
            "selection_eligible",
            "source_artifact_vintage_id",
            "source_cell_ids",
            "source_status",
            "source_year",
            "stored_unit",
            "target_family",
            "target_id",
            "target_year",
            "transformation",
            "verified_calendar_year",
        }
        for row in rows
    )
    registry.validate_calibration_target_specs(rows)


def test__target_registry__pins_verified_role_authority():
    assert registry.verified_role_specs() == {
        "schema_version": "verified_role_specs.v1",
        "role_rule_id": (
            "verified_calendar_year_1968_2008_train_2009_2014_validation_"
            "2015_2022_heldout_v1"
        ),
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
    assert {
        year: registry.role_for_year(year)
        for year in (1968, 2008, 2009, 2014, 2015, 2022)
    } == {
        1968: "train",
        2008: "train",
        2009: "validation",
        2014: "validation",
        2015: "held_out_diagnostic",
        2022: "held_out_diagnostic",
    }


def test__target_registry__pins_source_class_selection_and_weight_laws():
    rows = registry.calibration_target_specs()
    fitting_families = registry.TARGET_FAMILY_ORDER[:4]
    for family in fitting_families:
        family_rows = [row for row in rows if row["target_family"] == family]
        assert sum(row["loss_weight"] > 0 for row in family_rows) == 35
        assert {
            row["target_year"]
            for row in family_rows
            if row["selection_eligible"]
        } == {2010, 2012, 2014}
    assert (
        sum(
            row["loss_weight"]
            for row in rows
            if row["target_family"] == "b2_wage_total_intensity"
        )
        == 0.25
    )
    assert (
        sum(
            row["loss_weight"]
            for row in rows
            if row["target_family"] == "b11_se_only_worker_share"
        )
        == 0.125
    )

    expected_classes = {
        1968: "direct_questionnaire",
        1996: "direct_questionnaire",
        1997: "structural_gap_imputed",
        1998: "direct_questionnaire",
        2009: "structural_gap_imputed",
        2010: "direct_questionnaire",
        2011: "structural_gap_imputed",
        2012: "direct_questionnaire",
        2013: "claim_specific_boundary_gap",
        2014: "boundary_2014",
        2015: "projected",
        2022: "projected",
    }
    assert {
        year: registry.model_year_source_class_for_year(year)
        for year in expected_classes
    } == expected_classes

    no_fitting_rows = [row for row in rows if row["loss"] == "no_fitting_loss"]
    assert no_fitting_rows
    assert all(row["loss_weight"] == 0.0 for row in no_fitting_rows)
    assert not any(row["selection_eligible"] for row in no_fitting_rows)


def test__target_registry__pins_validation_tolerance_tags():
    intensity = _target("b2_wage_total_intensity:2010")
    assert intensity["cell_tolerance"] == {
        "applicability": "selection_gate",
        "metric": "absolute_log_error",
        "maximum": 0.09531017980432493,
    }
    assert intensity["family_tolerance"] == {
        "applicability": "selection_gate",
        "metric": "rms_absolute_log_error",
        "maximum": 0.04879016416943205,
    }
    type_mix = _target("b11_dual_type_worker_share:2014")
    assert type_mix["cell_tolerance"] == {
        "applicability": "selection_gate",
        "metric": "absolute_share_error",
        "maximum": 0.03,
    }
    assert type_mix["family_tolerance"] == {
        "applicability": "selection_gate",
        "metric": "rms_absolute_share_error",
        "maximum": 0.015,
    }
    assert _target("b2_wage_total_intensity:2009")["cell_tolerance"] == {
        "applicability": "not_selection_gate"
    }
    assert _target("b11_wage_only_worker_share:2010")["cell_tolerance"] == {
        "applicability": "not_selection_gate"
    }


@pytest.mark.parametrize(
    "field",
    (
        "target_year",
        "verified_calendar_year",
        "source_year",
    ),
)
def test__target_validator__rejects_integer_year_field_alias(field):
    rows = registry.calibration_target_specs()
    rows[0][field] = 1969
    with pytest.raises(registry.RegistryValidationError, match="year"):
        registry.validate_calibration_target_specs(rows)


def test__target_validator__rejects_bool_as_year():
    rows = registry.calibration_target_specs()
    rows[0]["verified_calendar_year"] = True
    with pytest.raises(registry.RegistryValidationError, match="year"):
        registry.validate_calibration_target_specs(rows)


@pytest.mark.parametrize(
    ("field", "prefix"),
    (
        ("source_cell_ids", ""),
        ("resolved_observation_ids", "observation:"),
        ("physical_source_cell_ids", "physical_source_cell:"),
        ("primitive_ancestry_ids", "physical_source_cell:"),
    ),
)
def test__target_validator__rejects_source_identity_year_alias(field, prefix):
    rows = registry.calibration_target_specs()
    value = rows[0][field][0]
    assert value.startswith(prefix)
    rows[0][field][0] = value.replace("/1968/", "/1969/")
    with pytest.raises(registry.RegistryValidationError, match="year|closure"):
        registry.validate_calibration_target_specs(rows)


def test__target_validator__rejects_target_id_year_alias():
    rows = registry.calibration_target_specs()
    rows[0]["target_id"] = "b2_wage_total_intensity:1969"
    with pytest.raises(registry.RegistryValidationError, match="year"):
        registry.validate_calibration_target_specs(rows)


def test__target_validator__rejects_operand_year_alias():
    rows = registry.calibration_target_specs()
    rows[0]["transformation"]["operand_cell_ids"][0] = "table4.b2/1969/c5"
    with pytest.raises(
        registry.RegistryValidationError, match="operand|closure"
    ):
        registry.validate_calibration_target_specs(rows)


def test__target_validator__rejects_candidate_selector_year_alias():
    rows = registry.calibration_target_specs()
    rows[0]["candidate_output_selector"]["calendar_year"] = 1969
    with pytest.raises(registry.RegistryValidationError, match="year"):
        registry.validate_calibration_target_specs(rows)


@pytest.mark.parametrize("role_field", ("declared_role", "effective_role"))
def test__target_validator__recomputes_role_never_trusts_declared(
    role_field,
):
    rows = registry.calibration_target_specs()
    row = next(row for row in rows if row["target_year"] == 2009)
    row[role_field] = "train"
    with pytest.raises(registry.RegistryValidationError, match="recomputed"):
        registry.validate_calibration_target_specs(rows)


def test__target_validator__rejects_reordered_or_extra_row_schema():
    rows = registry.calibration_target_specs()
    rows[0], rows[1] = rows[1], rows[0]
    with pytest.raises(registry.RegistryValidationError):
        registry.validate_calibration_target_specs(rows)

    rows = registry.calibration_target_specs()
    rows[0]["unexpected"] = None
    with pytest.raises(registry.RegistryValidationError, match="wrong keys"):
        registry.validate_calibration_target_specs(rows)


def test__alias_registry__pins_complete_same_year_relationship_classes():
    aliases = registry.official_source_alias_specs()
    rules = registry.official_source_arithmetic_rule_specs()
    assert len(aliases) == 55 * (4 + 3 * 3) == 715
    assert len(rules) == 55 * 3 == 165
    assert Counter(row["relation"] for row in aliases) == {
        "shared_primitive": 220,
        "structural_formula_sibling": 495,
    }
    registry.validate_alias_closure(
        registry.calibration_target_specs(),
        aliases,
        rules,
    )


def test__alias_validator__rejects_cross_year_alias():
    aliases = registry.official_source_alias_specs()
    aliases[0]["right_physical_cell_id"] = aliases[0][
        "right_physical_cell_id"
    ].replace("/1968/", "/1969/")
    with pytest.raises(registry.RegistryValidationError, match="year"):
        registry.validate_alias_closure(
            registry.calibration_target_specs(),
            aliases,
            registry.official_source_arithmetic_rule_specs(),
        )


def test__alias_validator__rejects_missing_or_extra_alias():
    aliases = registry.official_source_alias_specs()
    with pytest.raises(registry.RegistryValidationError):
        registry.validate_alias_closure(
            registry.calibration_target_specs(),
            aliases[:-1],
            registry.official_source_arithmetic_rule_specs(),
        )

    aliases = registry.official_source_alias_specs()
    extra = copy.deepcopy(aliases[0])
    extra["alias_group_id"] = "unregistered_extra"
    aliases.append(extra)
    with pytest.raises(registry.RegistryValidationError):
        registry.validate_alias_closure(
            registry.calibration_target_specs(),
            aliases,
            registry.official_source_arithmetic_rule_specs(),
        )


def test__alias_validator__rejects_numeric_equality_assertion_on_structural_rule():
    rules = registry.official_source_arithmetic_rule_specs()
    contribution_rule = next(
        row
        for row in rules
        if row["arithmetic_rule_id"] == "b11_contribution_components:1969"
    )
    contribution_rule["assertion_scope"] = "exact_published_value_equality"
    contribution_rule["numeric_validation_law"] = "exact_rational_ast_equality"
    contribution_rule["formula_ast"] = {"rational": 0}
    with pytest.raises(
        registry.RegistryValidationError,
        match="numeric equality",
    ):
        registry.validate_alias_closure(
            registry.calibration_target_specs(),
            registry.official_source_alias_specs(),
            rules,
        )


def test__structural_sibling_registry__pins_all_display_residual_years():
    rows = registry.structural_sibling_specs()
    registry.validate_structural_sibling_specs(rows)
    contribution_rows = [
        row for row in rows if "contributions" in row["target_id"]
    ]
    taxable_rows = [
        row for row in rows if "taxable_earnings" in row["target_id"]
    ]
    assert {
        row["verified_calendar_year"]: row["published_display_residual"]
        for row in contribution_rows
        if row["published_display_residual"]
    } == {
        1969: -1,
        1971: -1,
        1986: 1,
        1993: -1,
        2001: 1,
        2010: -1,
        2019: 1,
        2021: 1,
    }
    assert all(row["published_display_residual"] == 0 for row in taxable_rows)


def test__1969_contributions__is_structural_only_not_exact_equality():
    row = next(
        row
        for row in registry.structural_sibling_specs()
        if row["target_id"]
        == "b11_contributions_component_reconciliation:1969"
    )
    assert row == {
        "structural_sibling_id": (
            "b11_contributions_component_reconciliation:1969:"
            "display_components"
        ),
        "target_id": ("b11_contributions_component_reconciliation:1969"),
        "verified_calendar_year": 1969,
        "source_cell_ids": [
            "table4.b11/1969/contributions_total",
            "table4.b11/1969/contributions_wage",
            "table4.b11/1969/contributions_self_employment",
        ],
        "relation": "structural_formula_sibling",
        "arithmetic_rule_id": "b11_contribution_components:1969",
        "assertion_scope": "structural_dependence_only",
        "numeric_validation_law": (
            "not_applicable_no_published_numeric_assertion"
        ),
        "formula_ast": None,
        "published_display_residual": -1,
        "stored_display_residual": -1_000_000,
        "rounding_disposition": "rounding_interval_unavailable",
    }
    target = _target("b11_contributions_component_reconciliation:1969")
    assert target["effective_role"] == "train"
    assert target["loss"] == "no_fitting_loss"
    assert target["loss_weight"] == 0.0
    assert target["selection_eligible"] is False


def test__structural_sibling_validator__recomputes_committed_observations():
    registry.validate_structural_sibling_observations(
        _artifact()["observations"]
    )


def test__structural_sibling_validator__rejects_changed_1969_component():
    observations = _artifact()["observations"]
    row = next(
        row
        for row in observations
        if row["source_cell_id"] == "table4.b11/1969/contributions_wage"
    )
    assert row["as_published"] == "31,501"
    row["as_published"] = "31,500"
    with pytest.raises(
        registry.RegistryValidationError,
        match="observed residual",
    ):
        registry.validate_structural_sibling_observations(observations)


def test__frozen_registry_getters__return_deep_copies_and_validate():
    first = registry.frozen_registries()
    second = registry.frozen_registries()
    first["calibration_target_specs"][0]["target_year"] = 1969
    assert second["calibration_target_specs"][0]["target_year"] == 1968
    registry.validate_frozen_registries(
        calibration_targets=second["calibration_target_specs"],
        aliases=second["official_source_alias_specs"],
        arithmetic_rules=second["official_source_arithmetic_rule_specs"],
        structural_siblings=second["structural_sibling_specs"],
    )
