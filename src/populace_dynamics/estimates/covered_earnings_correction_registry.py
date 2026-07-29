"""Frozen entry-11 calibration-target extraction registries.

This module freezes the Table 4.B2 and Table 4.B11 portion of
``calibration_target_specs.v2`` that can be established from the committed
Supplement bytes.  It deliberately does not invent the V-B7 covered-share
rows, model-weight identity, universe concordance, or registration-time
physical-source authority.

The public getters return fresh JSON containers.  Validation is fail-closed:
it independently recomputes every encoded year, role, selection flag, loss
weight, physical-alias closure, and structural-sibling residual before
performing type-aware exact equality against the frozen registry.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

DESIGN_PATH = "docs/design/covered_earnings_correction.md"
DESIGN_RATIFICATION_COMMIT = "59fd058b943c2b9960af9cb98ecdec97709cc2dd"
DESIGN_REVISION = 2

CALIBRATION_TARGET_SPECS_SCHEMA_VERSION = "calibration_target_specs.v2"
VERIFIED_ROLE_SPECS_SCHEMA_VERSION = "verified_role_specs.v1"
OFFICIAL_SOURCE_ALIAS_SPECS_SCHEMA_VERSION = "official_source_alias_specs.v1"
OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS_SCHEMA_VERSION = (
    "official_source_arithmetic_rule_specs.v1"
)
STRUCTURAL_SIBLING_SPECS_SCHEMA_VERSION = "structural_sibling_specs.v1"

SOURCE_ARTIFACT_VINTAGE_ID = (
    "ssa_covered_earnings_calibration_targets.vintage2"
)
SOURCE_DOCUMENT_ID = "ssa_supplement_2025_4b"
SOURCE_SHA256 = (
    "c228920ea9d53b1e323e5933b6d9f926e3c9b609d868b549fabc40118554b449"
)
TARGET_YEARS = tuple(range(1968, 2023))

ROLE_RULE_ID = (
    "verified_calendar_year_1968_2008_train_2009_2014_validation_"
    "2015_2022_heldout_v1"
)
ROLE_ORDER = ("train", "validation", "held_out_diagnostic")

NO_TOLERANCE = {"applicability": "not_selection_gate"}
INTENSITY_CELL_TOLERANCE = {
    "applicability": "selection_gate",
    "metric": "absolute_log_error",
    "maximum": 0.09531017980432493,
}
INTENSITY_FAMILY_TOLERANCE = {
    "applicability": "selection_gate",
    "metric": "rms_absolute_log_error",
    "maximum": 0.04879016416943205,
}
TYPE_MIX_CELL_TOLERANCE = {
    "applicability": "selection_gate",
    "metric": "absolute_share_error",
    "maximum": 0.03,
}
TYPE_MIX_FAMILY_TOLERANCE = {
    "applicability": "selection_gate",
    "metric": "rms_absolute_share_error",
    "maximum": 0.015,
}
ROUNDING_NOT_ESTABLISHED = {
    "status": "not_established_from_source_bytes",
    "lower": None,
    "upper": None,
    "lower_closed": None,
    "upper_closed": None,
    "rule_source_document_id": None,
    "rule_citation": None,
}

SHARED_PRIMITIVES = (
    ("c11", "workers_wage", "wage_worker_count"),
    ("c12", "workers_self_employment", "self_employment_worker_count"),
    ("c13", "taxable_earnings_wage", "wage_taxable_earnings"),
    (
        "c17",
        "taxable_earnings_self_employment",
        "self_employment_taxable_earnings",
    ),
)

STRUCTURAL_GROUPS = (
    {
        "group_id": "b11_worker_membership",
        "relation_class": "worker_membership",
        "components": (
            "workers_total",
            "workers_wage",
            "workers_self_employment",
        ),
        "ordered_operands": (
            "workers_wage",
            "workers_self_employment",
        ),
        "output": "workers_total",
        "definition": (
            "a. Workers with earnings in both wage and salary employment "
            "and self-employment are counted in each type of employment "
            "but only once in the total."
        ),
        "citation": "supplement2025_4b.html#L15813",
    },
    {
        "group_id": "b11_taxable_earnings_components",
        "relation_class": "total_component",
        "components": (
            "taxable_earnings_total",
            "taxable_earnings_wage",
            "taxable_earnings_self_employment",
        ),
        "ordered_operands": (
            "taxable_earnings_wage",
            "taxable_earnings_self_employment",
        ),
        "output": "taxable_earnings_total",
        "definition": (
            "b. Includes Social Security taxable wages as reported by "
            "employers and Social Security taxable self-employment income "
            "as reported by self-employed workers. See Table 2.A3 for "
            "annual maximum taxable earnings."
        ),
        "citation": "supplement2025_4b.html#L15816",
    },
    {
        "group_id": "b11_contribution_components",
        "relation_class": "total_component",
        "components": (
            "contributions_total",
            "contributions_wage",
            "contributions_self_employment",
        ),
        "ordered_operands": (
            "contributions_wage",
            "contributions_self_employment",
        ),
        "output": "contributions_total",
        "definition": (
            "NOTES: Totals do not necessarily equal the sum of rounded "
            "components."
        ),
        "citation": ("supplement2025_4b.html#L15807-L15822"),
    },
)

CONTRIBUTION_DISPLAY_RESIDUALS = {
    1969: -1,
    1971: -1,
    1986: 1,
    1993: -1,
    2001: 1,
    2010: -1,
    2019: 1,
    2021: 1,
}


def _family(
    target_family: str,
    *,
    dependency_group: str,
    table_id: str,
    component_ids: tuple[str, ...],
    operation: str,
    formula: str,
    domain: str,
    stored_unit: str,
    loss: str,
    family_weight: float,
    tolerance_kind: str | None,
    field_ids: tuple[str, ...],
    aggregation: str,
    cap_stage: str,
) -> dict[str, Any]:
    return {
        "target_family": target_family,
        "dependency_group": dependency_group,
        "table_id": table_id,
        "component_ids": component_ids,
        "operation": operation,
        "formula": formula,
        "domain": domain,
        "stored_unit": stored_unit,
        "loss": loss,
        "family_weight": family_weight,
        "tolerance_kind": tolerance_kind,
        "field_ids": field_ids,
        "aggregation": aggregation,
        "cap_stage": cap_stage,
    }


# The covered-share family occupies position five in the final registry.  It
# is intentionally absent here because its V-B7 bytes and universe have not
# been registered.  The remaining order is exactly the design's order.
_FAMILY_TEMPLATES = (
    _family(
        "b2_wage_total_intensity",
        dependency_group="b2_component_system",
        table_id="table4.b2",
        component_ids=("c5", "c11"),
        operation="divide",
        formula="c5/c11",
        domain="strictly_positive_ratio",
        stored_unit="current_dollars_per_worker",
        loss="squared_log_ratio",
        family_weight=0.25,
        tolerance_kind="intensity",
        field_ids=(
            "covered_employee_wages_uncapped",
            "b2_wage_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(covered_employee_wages_uncapped)/"
            "sum(b2_wage_worker_membership_probability_analytic)"
        ),
        cap_stage="uncapped_before_covered_wage_measurement",
    ),
    _family(
        "b2_se_total_intensity",
        dependency_group="b2_component_system",
        table_id="table4.b2",
        component_ids=("c8", "c12"),
        operation="divide",
        formula="c8/c12",
        domain="strictly_positive_ratio",
        stored_unit="current_dollars_per_worker",
        loss="squared_log_ratio",
        family_weight=0.25,
        tolerance_kind="intensity",
        field_ids=(
            "covered_se_net_earnings_pre_seca",
            "b2_se_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(covered_se_net_earnings_pre_seca)/"
            "sum(b2_se_worker_membership_probability_analytic)"
        ),
        cap_stage="pre_seca_factor_threshold_and_cap",
    ),
    _family(
        "b11_se_only_worker_share",
        dependency_group="b11_worker_type_system",
        table_id="table4.b11",
        component_ids=("workers_total", "workers_wage"),
        operation="derived_exclusive_share",
        formula="(workers_total-workers_wage)/workers_total",
        domain="open_unit_interval",
        stored_unit="share",
        loss="squared_logit_error",
        family_weight=0.125,
        tolerance_kind="type_mix",
        field_ids=(
            "b11_se_only_worker_probability_analytic",
            "b11_any_worker_probability_analytic",
        ),
        aggregation=(
            "sum(b11_se_only_worker_probability_analytic)/"
            "sum(b11_any_worker_probability_analytic)"
        ),
        cap_stage="worker_membership_before_cap",
    ),
    _family(
        "b11_dual_type_worker_share",
        dependency_group="b11_worker_type_system",
        table_id="table4.b11",
        component_ids=(
            "workers_total",
            "workers_wage",
            "workers_self_employment",
        ),
        operation="derived_exclusive_share",
        formula=(
            "(workers_wage+workers_self_employment-workers_total)/"
            "workers_total"
        ),
        domain="open_unit_interval",
        stored_unit="share",
        loss="squared_logit_error",
        family_weight=0.125,
        tolerance_kind="type_mix",
        field_ids=(
            "b11_dual_type_worker_probability_analytic",
            "b11_any_worker_probability_analytic",
        ),
        aggregation=(
            "sum(b11_dual_type_worker_probability_analytic)/"
            "sum(b11_any_worker_probability_analytic)"
        ),
        cap_stage="worker_membership_before_cap",
    ),
    _family(
        "b11_wage_only_worker_share",
        dependency_group="b11_worker_type_system",
        table_id="table4.b11",
        component_ids=("workers_total", "workers_self_employment"),
        operation="derived_exclusive_share",
        formula=("(workers_total-workers_self_employment)/workers_total"),
        domain="closed_unit_interval",
        stored_unit="share",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "b11_wage_only_worker_probability_analytic",
            "b11_any_worker_probability_analytic",
        ),
        aggregation=(
            "sum(b11_wage_only_worker_probability_analytic)/"
            "sum(b11_any_worker_probability_analytic)"
        ),
        cap_stage="worker_membership_before_cap",
    ),
    _family(
        "b2_type_count_mix",
        dependency_group="b2_component_system",
        table_id="table4.b2",
        component_ids=("c12", "c11"),
        operation="divide_by_sum",
        formula="c12/(c11+c12)",
        domain="closed_unit_interval",
        stored_unit="share_of_overlapping_marginal_worker_counts",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "b2_se_worker_membership_probability_analytic",
            "b2_wage_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(b2_se_worker_membership_probability_analytic)/"
            "(sum(b2_wage_worker_membership_probability_analytic)+"
            "sum(b2_se_worker_membership_probability_analytic))"
        ),
        cap_stage="worker_membership_before_cap",
    ),
    _family(
        "b2_se_total_component_share",
        dependency_group="b2_component_system",
        table_id="table4.b2",
        component_ids=("c8", "c5"),
        operation="divide_by_sum",
        formula="c8/(c5+c8)",
        domain="closed_unit_interval",
        stored_unit="share",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "covered_se_net_earnings_pre_seca",
            "covered_employee_wages_uncapped",
        ),
        aggregation=(
            "sum(covered_se_net_earnings_pre_seca)/"
            "(sum(covered_employee_wages_uncapped)+"
            "sum(covered_se_net_earnings_pre_seca))"
        ),
        cap_stage="before_seca_factor_threshold_and_cap",
    ),
    _family(
        "b2_wage_taxable_intensity",
        dependency_group="b2_component_system",
        table_id="table4.b2",
        component_ids=("c13", "c11"),
        operation="divide",
        formula="c13/c11",
        domain="nonnegative_ratio",
        stored_unit="current_dollars_per_worker",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "oasdi_taxable_wages_person",
            "b2_wage_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(oasdi_taxable_wages_person)/"
            "sum(b2_wage_worker_membership_probability_analytic)"
        ),
        cap_stage="after_person_level_wage_cap",
    ),
    _family(
        "b2_se_taxable_intensity",
        dependency_group="b2_component_system",
        table_id="table4.b2",
        component_ids=("c17", "c12"),
        operation="divide",
        formula="c17/c12",
        domain="nonnegative_ratio",
        stored_unit="current_dollars_per_worker",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "oasdi_taxable_se_person",
            "b2_se_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(oasdi_taxable_se_person)/"
            "sum(b2_se_worker_membership_probability_analytic)"
        ),
        cap_stage="after_seca_factor_threshold_and_residual_cap",
    ),
    _family(
        "b2_wage_taxable_fraction",
        dependency_group="b2_component_system",
        table_id="table4.b2",
        component_ids=("c13", "c5"),
        operation="divide",
        formula="c13/c5",
        domain="closed_unit_interval",
        stored_unit="share",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "oasdi_taxable_wages_person",
            "covered_employee_wages_uncapped",
        ),
        aggregation=(
            "sum(oasdi_taxable_wages_person)/"
            "sum(covered_employee_wages_uncapped)"
        ),
        cap_stage="taxable_after_person_cap_over_uncapped",
    ),
    _family(
        "b2_se_taxable_fraction",
        dependency_group="b2_component_system",
        table_id="table4.b2",
        component_ids=("c17", "c8"),
        operation="divide",
        formula="c17/c8",
        domain="closed_unit_interval",
        stored_unit="share",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "oasdi_taxable_se_person",
            "covered_se_net_earnings_pre_seca",
        ),
        aggregation=(
            "sum(oasdi_taxable_se_person)/"
            "sum(covered_se_net_earnings_pre_seca)"
        ),
        cap_stage="taxable_after_seca_law_over_pre_seca_net",
    ),
    _family(
        "b11_taxable_earnings_component_reconciliation",
        dependency_group="b11_taxable_earnings_component_system",
        table_id="table4.b11",
        component_ids=(
            "taxable_earnings_total",
            "taxable_earnings_wage",
            "taxable_earnings_self_employment",
        ),
        operation="structural_component_reconciliation",
        formula=(
            "taxable_earnings_total-taxable_earnings_wage-"
            "taxable_earnings_self_employment"
        ),
        domain="finite_display_residual",
        stored_unit="current_dollars",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "oasdi_person_taxable_payroll",
            "oasdi_taxable_wages_person",
            "oasdi_taxable_se_person",
        ),
        aggregation=(
            "sum(oasdi_person_taxable_payroll)-"
            "sum(oasdi_taxable_wages_person)-"
            "sum(oasdi_taxable_se_person)"
        ),
        cap_stage="after_person_level_wage_first_residual_cap",
    ),
    _family(
        "b11_contributions_component_reconciliation",
        dependency_group="b11_contribution_component_system",
        table_id="table4.b11",
        component_ids=(
            "contributions_total",
            "contributions_wage",
            "contributions_self_employment",
        ),
        operation="structural_component_reconciliation",
        formula=(
            "contributions_total-contributions_wage-"
            "contributions_self_employment"
        ),
        domain="finite_display_residual",
        stored_unit="current_dollars",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "oasdi_taxable_wages_person",
            "registered_wage_oasdi_combined_rate",
            "oasdi_taxable_se_person",
            "registered_se_oasdi_rate",
        ),
        aggregation=(
            "sum(oasdi_taxable_wages_person*"
            "registered_wage_oasdi_combined_rate+"
            "oasdi_taxable_se_person*registered_se_oasdi_rate)-"
            "sum(oasdi_taxable_wages_person*"
            "registered_wage_oasdi_combined_rate)-"
            "sum(oasdi_taxable_se_person*registered_se_oasdi_rate)"
        ),
        cap_stage="after_taxable_earnings_and_registered_rates",
    ),
    _family(
        "b11_se_contribution_share",
        dependency_group="b11_contribution_component_system",
        table_id="table4.b11",
        component_ids=(
            "contributions_self_employment",
            "contributions_wage",
        ),
        operation="divide_by_sum",
        formula=(
            "contributions_self_employment/"
            "(contributions_wage+contributions_self_employment)"
        ),
        domain="closed_unit_interval",
        stored_unit="share",
        loss="no_fitting_loss",
        family_weight=0.0,
        tolerance_kind=None,
        field_ids=(
            "oasdi_taxable_se_person",
            "registered_se_oasdi_rate",
            "oasdi_taxable_wages_person",
            "registered_wage_oasdi_combined_rate",
        ),
        aggregation=(
            "sum(oasdi_taxable_se_person*registered_se_oasdi_rate)/"
            "sum(oasdi_taxable_wages_person*"
            "registered_wage_oasdi_combined_rate+"
            "oasdi_taxable_se_person*registered_se_oasdi_rate)"
        ),
        cap_stage="after_taxable_earnings_and_registered_rates",
    ),
)

TARGET_FAMILY_ORDER = tuple(
    template["target_family"] for template in _FAMILY_TEMPLATES
)
SELECTION_ELIGIBLE_FAMILIES = frozenset(TARGET_FAMILY_ORDER[:4])


class RegistryValidationError(ValueError):
    """A supplied extraction registry violates the ratified frozen laws."""


def _canonical_json_bytes(value: Any) -> bytes:
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


def _sha256_canonical(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _source_cell_id(table_id: str, year: int, component_id: str) -> str:
    return f"{table_id}/{year}/{component_id}"


def _physical_cell_id(source_cell_id: str) -> str:
    return f"physical_source_cell:{source_cell_id}"


def _observation_id(source_cell_id: str) -> str:
    return f"observation:{source_cell_id}"


def role_for_year(year: int) -> str:
    """Independently derive the sole permitted evidentiary role."""

    if type(year) is not int:
        raise RegistryValidationError("verified calendar year must be int")
    if 1968 <= year <= 2008:
        return "train"
    if 2009 <= year <= 2014:
        return "validation"
    if 2015 <= year <= 2022:
        return "held_out_diagnostic"
    raise RegistryValidationError(f"verified calendar year {year} is invalid")


def model_year_source_class_for_year(year: int) -> str:
    """Return the frozen direct/gap/boundary/projected source class."""

    role_for_year(year)
    if 1968 <= year <= 1996 or (1998 <= year <= 2012 and year % 2 == 0):
        return "direct_questionnaire"
    if year == 2013:
        return "claim_specific_boundary_gap"
    if year == 2014:
        return "boundary_2014"
    if year >= 2015:
        return "projected"
    return "structural_gap_imputed"


def _availability_for_year(year: int) -> str:
    if model_year_source_class_for_year(year) in {
        "structural_gap_imputed",
        "claim_specific_boundary_gap",
    }:
        return "not_applicable_no_claim_independent_model_analogue"
    return "available"


def _selection_eligible(target_family: str, year: int) -> bool:
    return (
        target_family in SELECTION_ELIGIBLE_FAMILIES
        and role_for_year(year) == "validation"
        and model_year_source_class_for_year(year)
        in {"direct_questionnaire", "boundary_2014"}
    )


def _loss_weight(template: Mapping[str, Any], year: int) -> float:
    if (
        template["loss"] == "no_fitting_loss"
        or role_for_year(year) != "train"
        or model_year_source_class_for_year(year) != "direct_questionnaire"
    ):
        return 0.0
    positive_train_cell_count = 35
    return template["family_weight"] / positive_train_cell_count


def _tolerances(
    template: Mapping[str, Any], year: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not _selection_eligible(template["target_family"], year):
        return copy.deepcopy(NO_TOLERANCE), copy.deepcopy(NO_TOLERANCE)
    if template["tolerance_kind"] == "intensity":
        return (
            copy.deepcopy(INTENSITY_CELL_TOLERANCE),
            copy.deepcopy(INTENSITY_FAMILY_TOLERANCE),
        )
    if template["tolerance_kind"] == "type_mix":
        return (
            copy.deepcopy(TYPE_MIX_CELL_TOLERANCE),
            copy.deepcopy(TYPE_MIX_FAMILY_TOLERANCE),
        )
    raise AssertionError("selection-eligible family lacks tolerance kind")


def _structural_locator_id(source_cell_id: str) -> str:
    return f"structural_locator:{source_cell_id}"


def _arithmetic_rule_id(group_id: str, year: int) -> str:
    return f"{group_id}:{year}"


def _definition_locator_id(group: Mapping[str, Any], year: int) -> str:
    preimage = [
        "ssa_annual_statistical_supplement",
        "2025",
        SOURCE_DOCUMENT_ID,
        "table4.b11",
        group["citation"],
        year,
    ]
    return _sha256_canonical(preimage)


def _build_arithmetic_rule_specs() -> list[dict[str, Any]]:
    rows = []
    for year in TARGET_YEARS:
        for group in STRUCTURAL_GROUPS:
            components = group["components"]
            operands = [
                _structural_locator_id(
                    _source_cell_id("table4.b11", year, component)
                )
                for component in group["ordered_operands"]
            ]
            output = _structural_locator_id(
                _source_cell_id("table4.b11", year, group["output"])
            )
            siblings = [
                _structural_locator_id(
                    _source_cell_id("table4.b11", year, component)
                )
                for component in components
            ]
            rows.append(
                {
                    "arithmetic_rule_id": _arithmetic_rule_id(
                        group["group_id"], year
                    ),
                    "effective_calendar_year": year,
                    "relation_class": group["relation_class"],
                    "ordered_operand_structural_locator_ids": operands,
                    "output_structural_locator_id": output,
                    "sibling_structural_locator_ids": siblings,
                    "assertion_scope": "structural_dependence_only",
                    "numeric_validation_law": (
                        "not_applicable_no_published_numeric_assertion"
                    ),
                    "formula_ast": None,
                    "source_definition_locator_id": (
                        _definition_locator_id(group, year)
                    ),
                    "source_definition_fragment_sha256": hashlib.sha256(
                        group["definition"].encode("utf-8")
                    ).hexdigest(),
                }
            )
    return rows


def _build_alias_specs() -> list[dict[str, Any]]:
    rows = []
    for year in TARGET_YEARS:
        for b2_component, b11_component, concept in SHARED_PRIMITIVES:
            rows.append(
                {
                    "alias_group_id": (f"shared_primitive:{concept}:{year}"),
                    "left_physical_cell_id": _physical_cell_id(
                        _source_cell_id("table4.b2", year, b2_component)
                    ),
                    "right_physical_cell_id": _physical_cell_id(
                        _source_cell_id("table4.b11", year, b11_component)
                    ),
                    "relation": "shared_primitive",
                    "effective_calendar_year": year,
                    "arithmetic_rule_id": None,
                    "adjudication": (
                        "shared_primitive_by_registered_source_rule"
                    ),
                }
            )
        for group in STRUCTURAL_GROUPS:
            for left_component, right_component in combinations(
                group["components"], 2
            ):
                rows.append(
                    {
                        "alias_group_id": (
                            f"structural_sibling:{group['group_id']}:{year}"
                        ),
                        "left_physical_cell_id": _physical_cell_id(
                            _source_cell_id("table4.b11", year, left_component)
                        ),
                        "right_physical_cell_id": _physical_cell_id(
                            _source_cell_id(
                                "table4.b11", year, right_component
                            )
                        ),
                        "relation": "structural_formula_sibling",
                        "effective_calendar_year": year,
                        "arithmetic_rule_id": _arithmetic_rule_id(
                            group["group_id"], year
                        ),
                        "adjudication": (
                            "structural_formula_sibling_by_registered_"
                            "definition"
                        ),
                    }
                )
    return rows


_OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS = _build_arithmetic_rule_specs()
_OFFICIAL_SOURCE_ALIAS_SPECS = _build_alias_specs()


def _adjacency() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in _OFFICIAL_SOURCE_ALIAS_SPECS:
        left = row["left_physical_cell_id"]
        right = row["right_physical_cell_id"]
        result.setdefault(left, []).append(right)
        result.setdefault(right, []).append(left)
    return result


_ALIAS_ADJACENCY = _adjacency()


def _alias_closure(direct_physical_ids: Sequence[str]) -> list[str]:
    ordered = list(direct_physical_ids)
    seen = set(ordered)
    cursor = 0
    while cursor < len(ordered):
        current = ordered[cursor]
        cursor += 1
        for neighbor in _ALIAS_ADJACENCY.get(current, ()):
            if neighbor not in seen:
                seen.add(neighbor)
                ordered.append(neighbor)
    return ordered


def _build_calibration_target_specs() -> list[dict[str, Any]]:
    rows = []
    for template in _FAMILY_TEMPLATES:
        target_family = template["target_family"]
        for year in TARGET_YEARS:
            source_cell_ids = [
                _source_cell_id(
                    template["table_id"],
                    year,
                    component_id,
                )
                for component_id in template["component_ids"]
            ]
            physical_ids = [
                _physical_cell_id(source_cell_id)
                for source_cell_id in source_cell_ids
            ]
            source_class = model_year_source_class_for_year(year)
            availability = _availability_for_year(year)
            field_ids = (
                list(template["field_ids"])
                if availability == "available"
                else []
            )
            cell_tolerance, family_tolerance = _tolerances(template, year)
            role = role_for_year(year)
            rows.append(
                {
                    "target_id": f"{target_family}:{year}",
                    "target_family": target_family,
                    "target_year": year,
                    "verified_calendar_year": year,
                    "role_rule_id": ROLE_RULE_ID,
                    "dependency_group": template["dependency_group"],
                    "source_artifact_vintage_id": (SOURCE_ARTIFACT_VINTAGE_ID),
                    "source_cell_ids": source_cell_ids,
                    "resolved_observation_ids": [
                        _observation_id(source_cell_id)
                        for source_cell_id in source_cell_ids
                    ],
                    "physical_source_cell_ids": physical_ids,
                    "primitive_ancestry_ids": _alias_closure(physical_ids),
                    "source_year": year,
                    "source_status": (
                        "preliminary" if year in {2021, 2022} else "historical"
                    ),
                    "model_year_source_class": source_class,
                    "transformation": {
                        "operation": template["operation"],
                        "operand_cell_ids": list(source_cell_ids),
                        "formula": template["formula"],
                        "domain": template["domain"],
                    },
                    "stored_unit": template["stored_unit"],
                    "published_rounding_interval": copy.deepcopy(
                        ROUNDING_NOT_ESTABLISHED
                    ),
                    "declared_role": role,
                    "effective_role": role,
                    "loss": template["loss"],
                    "loss_weight": _loss_weight(template, year),
                    "cell_tolerance": cell_tolerance,
                    "family_tolerance": family_tolerance,
                    "selection_eligible": _selection_eligible(
                        target_family, year
                    ),
                    "candidate_output_selector": {
                        "calendar_year": year,
                        "year_source_class": source_class,
                        "availability": availability,
                        "field_ids": field_ids,
                        "aggregation": (
                            template["aggregation"]
                            if availability == "available"
                            else (
                                "not_applicable_no_claim_independent_"
                                "model_analogue"
                            )
                        ),
                        "joint_probability_rule": (
                            "analytic_probabilities_within_draw_year"
                        ),
                        "cap_stage": template["cap_stage"],
                        "projection_draw_reduction": (
                            "arithmetic_mean_over_projection_draws_0_19"
                        ),
                        "unit": template["stored_unit"],
                    },
                }
            )
    return rows


def _build_structural_sibling_specs() -> list[dict[str, Any]]:
    rows = []
    families = (
        (
            "b11_taxable_earnings_component_reconciliation",
            "b11_taxable_earnings_components",
            (
                "taxable_earnings_total",
                "taxable_earnings_wage",
                "taxable_earnings_self_employment",
            ),
        ),
        (
            "b11_contributions_component_reconciliation",
            "b11_contribution_components",
            (
                "contributions_total",
                "contributions_wage",
                "contributions_self_employment",
            ),
        ),
    )
    for target_family, group_id, components in families:
        for year in TARGET_YEARS:
            published_residual = (
                CONTRIBUTION_DISPLAY_RESIDUALS.get(year, 0)
                if "contributions" in target_family
                else 0
            )
            rows.append(
                {
                    "structural_sibling_id": (
                        f"{target_family}:{year}:display_components"
                    ),
                    "target_id": f"{target_family}:{year}",
                    "verified_calendar_year": year,
                    "source_cell_ids": [
                        _source_cell_id("table4.b11", year, component)
                        for component in components
                    ],
                    "relation": "structural_formula_sibling",
                    "arithmetic_rule_id": _arithmetic_rule_id(group_id, year),
                    "assertion_scope": "structural_dependence_only",
                    "numeric_validation_law": (
                        "not_applicable_no_published_numeric_assertion"
                    ),
                    "formula_ast": None,
                    "published_display_residual": published_residual,
                    "stored_display_residual": (
                        published_residual * 1_000_000
                    ),
                    "rounding_disposition": ("rounding_interval_unavailable"),
                }
            )
    return rows


_CALIBRATION_TARGET_SPECS = _build_calibration_target_specs()
_STRUCTURAL_SIBLING_SPECS = _build_structural_sibling_specs()


def design_binding() -> dict[str, Any]:
    """Return a fresh copy of the ratified design identity."""

    return {
        "path": DESIGN_PATH,
        "ratification_commit": DESIGN_RATIFICATION_COMMIT,
        "revision": DESIGN_REVISION,
    }


def verified_role_specs() -> dict[str, Any]:
    """Return the complete verified-year role authority."""

    return {
        "schema_version": VERIFIED_ROLE_SPECS_SCHEMA_VERSION,
        "role_rule_id": ROLE_RULE_ID,
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
        "role_order": list(ROLE_ORDER),
        "derivation": "recompute_never_trust_declared_role",
        "failure_disposition": "abort",
    }


def calibration_target_specs() -> list[dict[str, Any]]:
    """Return the 770 frozen B2/B11 target rows in design order."""

    return copy.deepcopy(_CALIBRATION_TARGET_SPECS)


def official_source_alias_specs() -> list[dict[str, Any]]:
    """Return the complete same-year alias/sibling rows for this unit."""

    return copy.deepcopy(_OFFICIAL_SOURCE_ALIAS_SPECS)


def official_source_arithmetic_rule_specs() -> list[dict[str, Any]]:
    """Return structural-only worker/total/component rules for this unit."""

    return copy.deepcopy(_OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS)


def structural_sibling_specs() -> list[dict[str, Any]]:
    """Return both 55-year B11 reconciliation residual registries."""

    return copy.deepcopy(_STRUCTURAL_SIBLING_SPECS)


def frozen_registries() -> dict[str, Any]:
    """Return every registry frozen by the B2/B11 extraction unit."""

    return {
        "calibration_target_specs_schema_version": (
            CALIBRATION_TARGET_SPECS_SCHEMA_VERSION
        ),
        "verified_role_specs": verified_role_specs(),
        "calibration_target_specs": calibration_target_specs(),
        "official_source_alias_specs_schema_version": (
            OFFICIAL_SOURCE_ALIAS_SPECS_SCHEMA_VERSION
        ),
        "official_source_alias_specs": official_source_alias_specs(),
        "official_source_arithmetic_rule_specs_schema_version": (
            OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS_SCHEMA_VERSION
        ),
        "official_source_arithmetic_rule_specs": (
            official_source_arithmetic_rule_specs()
        ),
        "structural_sibling_specs_schema_version": (
            STRUCTURAL_SIBLING_SPECS_SCHEMA_VERSION
        ),
        "structural_sibling_specs": structural_sibling_specs(),
    }


def _parse_year_from_source_identity(value: str, prefix: str = "") -> int:
    if type(value) is not str or not value.startswith(prefix):
        raise RegistryValidationError(
            f"source identity {value!r} lacks prefix {prefix!r}"
        )
    logical_id = value[len(prefix) :]
    parts = logical_id.split("/")
    if len(parts) != 3 or not re.fullmatch(r"\d{4}", parts[1]):
        raise RegistryValidationError(
            f"source identity {value!r} has invalid year grammar"
        )
    return int(parts[1])


def _validate_target_row(row: object, index: int) -> None:
    if type(row) is not dict:
        raise RegistryValidationError(f"calibration_target_specs[{index}]")
    target_id = row.get("target_id")
    family = row.get("target_family")
    if type(target_id) is not str or type(family) is not str:
        raise RegistryValidationError(f"target row {index} identity type")
    match = re.fullmatch(r"(?P<family>[a-z0-9_]+):(?P<year>\d{4})", target_id)
    if match is None or match.group("family") != family:
        raise RegistryValidationError(f"{target_id!r} target-ID grammar")
    parsed_year = int(match.group("year"))
    year_fields = (
        "target_year",
        "verified_calendar_year",
        "source_year",
    )
    for field in year_fields:
        value = row.get(field)
        if type(value) is not int or value != parsed_year:
            raise RegistryValidationError(
                f"{target_id}.{field} violates year-equality law"
            )

    identity_fields = (
        ("source_cell_ids", ""),
        ("resolved_observation_ids", "observation:"),
        ("physical_source_cell_ids", "physical_source_cell:"),
        ("primitive_ancestry_ids", "physical_source_cell:"),
    )
    for field, prefix in identity_fields:
        values = row.get(field)
        if (
            type(values) is not list
            or not values
            or len(values) != len(set(values))
        ):
            raise RegistryValidationError(
                f"{target_id}.{field} must be ordered nonempty unique"
            )
        for value in values:
            if _parse_year_from_source_identity(value, prefix) != parsed_year:
                raise RegistryValidationError(
                    f"{target_id}.{field} violates year-equality law"
                )

    transformation = row.get("transformation")
    if type(transformation) is not dict:
        raise RegistryValidationError(f"{target_id}.transformation")
    if transformation.get("operand_cell_ids") != row["source_cell_ids"]:
        raise RegistryValidationError(
            f"{target_id} transformation operand closure mismatch"
        )
    for value in transformation["operand_cell_ids"]:
        if _parse_year_from_source_identity(value) != parsed_year:
            raise RegistryValidationError(
                f"{target_id} operand violates year-equality law"
            )

    selector = row.get("candidate_output_selector")
    if (
        type(selector) is not dict
        or type(selector.get("calendar_year")) is not int
    ):
        raise RegistryValidationError(f"{target_id} candidate selector schema")
    if selector["calendar_year"] != parsed_year:
        raise RegistryValidationError(
            f"{target_id} candidate selector violates year-equality law"
        )
    expected_source_class = model_year_source_class_for_year(parsed_year)
    if (
        row.get("model_year_source_class") != expected_source_class
        or selector.get("year_source_class") != expected_source_class
    ):
        raise RegistryValidationError(f"{target_id} source-class drift")

    expected_role = role_for_year(parsed_year)
    if (
        row.get("role_rule_id") != ROLE_RULE_ID
        or row.get("declared_role") != expected_role
        or row.get("effective_role") != expected_role
    ):
        raise RegistryValidationError(
            f"{target_id} role was not independently recomputed"
        )
    expected_status = (
        "preliminary" if parsed_year in {2021, 2022} else "historical"
    )
    if row.get("source_status") != expected_status:
        raise RegistryValidationError(f"{target_id} source-status drift")
    if (
        expected_role != "held_out_diagnostic"
        and expected_status != "historical"
    ):
        raise RegistryValidationError(
            f"{target_id} preliminary model-choice source"
        )
    if row.get("published_rounding_interval") != ROUNDING_NOT_ESTABLISHED:
        raise RegistryValidationError(f"{target_id} inferred rounding")

    template = _FAMILY_TEMPLATES[
        TARGET_FAMILY_ORDER.index(row["target_family"])
    ]
    if row.get("loss") != template["loss"]:
        raise RegistryValidationError(f"{target_id} loss drift")
    expected_weight = _loss_weight(template, parsed_year)
    if (
        type(row.get("loss_weight")) is not float
        or not math.isfinite(row["loss_weight"])
        or row["loss_weight"] != expected_weight
    ):
        raise RegistryValidationError(f"{target_id} loss-weight drift")
    if row.get("selection_eligible") is not _selection_eligible(
        family, parsed_year
    ):
        raise RegistryValidationError(f"{target_id} selection law drift")
    cell_tolerance, family_tolerance = _tolerances(template, parsed_year)
    if (
        row.get("cell_tolerance") != cell_tolerance
        or row.get("family_tolerance") != family_tolerance
    ):
        raise RegistryValidationError(f"{target_id} tolerance drift")


def _validate_arithmetic_rules(value: object) -> None:
    if type(value) is not list:
        raise RegistryValidationError(
            "official_source_arithmetic_rule_specs must be an array"
        )
    rule_ids = set()
    for index, row in enumerate(value):
        if type(row) is not dict:
            raise RegistryValidationError(f"arithmetic rule {index} schema")
        rule_id = row.get("arithmetic_rule_id")
        year = row.get("effective_calendar_year")
        if type(rule_id) is not str or type(year) is not int:
            raise RegistryValidationError(f"arithmetic rule {index} identity")
        if rule_id in rule_ids:
            raise RegistryValidationError(
                f"duplicate arithmetic rule {rule_id}"
            )
        rule_ids.add(rule_id)
        if not rule_id.endswith(f":{year}"):
            raise RegistryValidationError(f"{rule_id} year mismatch")
        if (
            row.get("assertion_scope") != "structural_dependence_only"
            or row.get("numeric_validation_law")
            != "not_applicable_no_published_numeric_assertion"
            or row.get("formula_ast") is not None
        ):
            raise RegistryValidationError(
                f"{rule_id} asserted displayed numeric equality"
            )


def validate_alias_closure(
    target_specs: object,
    alias_specs: object,
    arithmetic_rule_specs: object,
) -> None:
    """Reject missing, extra, cross-year, or rule-orphaned aliases."""

    if type(alias_specs) is not list:
        raise RegistryValidationError(
            "official_source_alias_specs must be an array"
        )
    _validate_arithmetic_rules(arithmetic_rule_specs)
    rule_ids = {row["arithmetic_rule_id"] for row in arithmetic_rule_specs}
    referenced_rule_ids = set()
    endpoints = set()
    for index, row in enumerate(alias_specs):
        if type(row) is not dict:
            raise RegistryValidationError(f"alias row {index} schema")
        year = row.get("effective_calendar_year")
        if type(year) is not int:
            raise RegistryValidationError(f"alias row {index} year type")
        left = row.get("left_physical_cell_id")
        right = row.get("right_physical_cell_id")
        left_year = _parse_year_from_source_identity(
            left, "physical_source_cell:"
        )
        right_year = _parse_year_from_source_identity(
            right, "physical_source_cell:"
        )
        if left_year != year or right_year != year:
            raise RegistryValidationError(
                f"alias row {index} violates year-equality law"
            )
        endpoints.update((left, right))
        rule_id = row.get("arithmetic_rule_id")
        sibling = row.get("relation") in {
            "exact_arithmetic_sibling",
            "structural_formula_sibling",
        }
        if sibling != (rule_id is not None):
            raise RegistryValidationError(
                f"alias row {index} arithmetic-rule nullability"
            )
        if rule_id is not None:
            if rule_id not in rule_ids:
                raise RegistryValidationError(
                    f"alias row {index} has orphan arithmetic rule"
                )
            referenced_rule_ids.add(rule_id)
    if referenced_rule_ids != rule_ids:
        raise RegistryValidationError(
            "not every arithmetic rule is referenced by alias closure"
        )

    if type(target_specs) is not list:
        raise RegistryValidationError(
            "calibration_target_specs must be an array"
        )
    supplied_adjacency: dict[str, list[str]] = {}
    for row in alias_specs:
        left = row["left_physical_cell_id"]
        right = row["right_physical_cell_id"]
        supplied_adjacency.setdefault(left, []).append(right)
        supplied_adjacency.setdefault(right, []).append(left)
    for target in target_specs:
        direct = target["physical_source_cell_ids"]
        expected = list(direct)
        seen = set(expected)
        cursor = 0
        while cursor < len(expected):
            current = expected[cursor]
            cursor += 1
            for neighbor in supplied_adjacency.get(current, ()):
                if neighbor not in seen:
                    seen.add(neighbor)
                    expected.append(neighbor)
        if target["primitive_ancestry_ids"] != expected:
            raise RegistryValidationError(
                f"{target['target_id']} primitive alias closure mismatch"
            )
        target_year = target["verified_calendar_year"]
        if any(
            _parse_year_from_source_identity(
                physical_id, "physical_source_cell:"
            )
            != target_year
            for physical_id in expected
        ):
            raise RegistryValidationError(
                f"{target['target_id']} cross-year primitive in closure"
            )
    _assert_exact_json(
        alias_specs,
        _OFFICIAL_SOURCE_ALIAS_SPECS,
        "official_source_alias_specs",
    )
    _assert_exact_json(
        arithmetic_rule_specs,
        _OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS,
        "official_source_arithmetic_rule_specs",
    )


def _sorted_reprs(values: set[object]) -> list[str]:
    return sorted(repr(value) for value in values)


def _assert_exact_json(actual: object, expected: object, path: str) -> None:
    if type(actual) is not type(expected):
        raise RegistryValidationError(
            f"{path} has type {type(actual).__name__}; "
            f"expected {type(expected).__name__}"
        )
    if isinstance(expected, dict):
        actual_keys = set(actual)
        expected_keys = set(expected)
        if actual_keys != expected_keys:
            raise RegistryValidationError(
                f"{path} has wrong keys; "
                f"missing={_sorted_reprs(expected_keys - actual_keys)}, "
                f"extra={_sorted_reprs(actual_keys - expected_keys)}"
            )
        for key, expected_value in expected.items():
            _assert_exact_json(
                actual[key],
                expected_value,
                f"{path}.{key}",
            )
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise RegistryValidationError(
                f"{path} length {len(actual)} != {len(expected)}"
            )
        for index, (actual_value, expected_value) in enumerate(
            zip(actual, expected, strict=True)
        ):
            _assert_exact_json(
                actual_value,
                expected_value,
                f"{path}[{index}]",
            )
        return
    if actual != expected:
        raise RegistryValidationError(
            f"{path} is {actual!r}; expected {expected!r}"
        )


def validate_calibration_target_specs(value: object) -> None:
    """Validate schema, year law, role law, closure, and exact row order."""

    if type(value) is not list or len(value) != 770:
        raise RegistryValidationError(
            "calibration_target_specs must contain 770 B2/B11 rows"
        )
    for index, row in enumerate(value):
        _validate_target_row(row, index)
    validate_alias_closure(
        value,
        _OFFICIAL_SOURCE_ALIAS_SPECS,
        _OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS,
    )
    _assert_exact_json(
        value,
        _CALIBRATION_TARGET_SPECS,
        "calibration_target_specs",
    )


def validate_structural_sibling_specs(value: object) -> None:
    """Validate structural-only scope and the complete display residual law."""

    if type(value) is not list or len(value) != 110:
        raise RegistryValidationError(
            "structural_sibling_specs must contain 110 rows"
        )
    for row in value:
        target_id = row.get("target_id") if isinstance(row, dict) else None
        if (
            not isinstance(row, dict)
            or row.get("relation") != "structural_formula_sibling"
            or row.get("assertion_scope") != "structural_dependence_only"
            or row.get("numeric_validation_law")
            != "not_applicable_no_published_numeric_assertion"
            or row.get("formula_ast") is not None
            or row.get("rounding_disposition")
            != "rounding_interval_unavailable"
        ):
            raise RegistryValidationError(
                f"{target_id!r} structural-sibling law drift"
            )
        year = row["verified_calendar_year"]
        expected = (
            CONTRIBUTION_DISPLAY_RESIDUALS.get(year, 0)
            if "contributions" in row["target_id"]
            else 0
        )
        if (
            row["published_display_residual"] != expected
            or row["stored_display_residual"] != expected * 1_000_000
        ):
            raise RegistryValidationError(
                f"{target_id} display-residual drift"
            )
    _assert_exact_json(
        value,
        _STRUCTURAL_SIBLING_SPECS,
        "structural_sibling_specs",
    )


def _published_integer(value: object, where: str) -> int:
    if type(value) is not str or not re.fullmatch(
        r"-?\d{1,3}(?:,\d{3})*|-?\d+", value
    ):
        raise RegistryValidationError(f"{where} invalid published integer")
    return int(value.replace(",", ""))


def validate_structural_sibling_observations(
    observations: object,
) -> None:
    """Recompute all 110 B11 residuals from artifact observations."""

    if type(observations) is not list:
        raise RegistryValidationError("observations must be an array")
    by_id = {}
    for row in observations:
        if not isinstance(row, dict):
            raise RegistryValidationError("observation is not an object")
        source_cell_id = row.get("source_cell_id")
        if source_cell_id in by_id:
            raise RegistryValidationError(
                f"duplicate observation {source_cell_id!r}"
            )
        by_id[source_cell_id] = row

    for spec in _STRUCTURAL_SIBLING_SPECS:
        values = [
            _published_integer(
                by_id[source_cell_id]["as_published"],
                source_cell_id,
            )
            for source_cell_id in spec["source_cell_ids"]
        ]
        residual = values[0] - values[1] - values[2]
        if residual != spec["published_display_residual"]:
            raise RegistryValidationError(
                f"{spec['target_id']} observed residual {residual} != "
                f"{spec['published_display_residual']}"
            )
        for source_cell_id in spec["source_cell_ids"]:
            if (
                by_id[source_cell_id]["published_rounding_interval"]
                != ROUNDING_NOT_ESTABLISHED
            ):
                raise RegistryValidationError(
                    f"{source_cell_id} inferred a rounding interval"
                )


def validate_frozen_registries(
    *,
    calibration_targets: object,
    aliases: object,
    arithmetic_rules: object,
    structural_siblings: object,
) -> None:
    """Validate all unit-1 frozen registries and their foreign keys."""

    validate_calibration_target_specs(calibration_targets)
    validate_alias_closure(
        calibration_targets,
        aliases,
        arithmetic_rules,
    )
    validate_structural_sibling_specs(structural_siblings)
    _assert_exact_json(
        aliases,
        _OFFICIAL_SOURCE_ALIAS_SPECS,
        "official_source_alias_specs",
    )
    _assert_exact_json(
        arithmetic_rules,
        _OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS,
        "official_source_arithmetic_rule_specs",
    )


__all__ = [
    "CALIBRATION_TARGET_SPECS_SCHEMA_VERSION",
    "CONTRIBUTION_DISPLAY_RESIDUALS",
    "DESIGN_PATH",
    "DESIGN_RATIFICATION_COMMIT",
    "DESIGN_REVISION",
    "OFFICIAL_SOURCE_ALIAS_SPECS_SCHEMA_VERSION",
    "OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS_SCHEMA_VERSION",
    "RegistryValidationError",
    "ROLE_RULE_ID",
    "SOURCE_ARTIFACT_VINTAGE_ID",
    "STRUCTURAL_SIBLING_SPECS_SCHEMA_VERSION",
    "TARGET_FAMILY_ORDER",
    "TARGET_YEARS",
    "VERIFIED_ROLE_SPECS_SCHEMA_VERSION",
    "calibration_target_specs",
    "design_binding",
    "frozen_registries",
    "model_year_source_class_for_year",
    "official_source_alias_specs",
    "official_source_arithmetic_rule_specs",
    "role_for_year",
    "structural_sibling_specs",
    "validate_alias_closure",
    "validate_calibration_target_specs",
    "validate_frozen_registries",
    "validate_structural_sibling_observations",
    "validate_structural_sibling_specs",
    "verified_role_specs",
]
