"""Amendment-1 registration boundary for covered-earnings correction.

The amended vintage-2 source artifact is complete and accepted.  The new
methodology bytes nevertheless leave at least one section 6.1 membership fact
unresolved for every target family, and registration-time model-universe,
weight-input, and concordance authorities remain absent.

This module therefore exposes the exact registry schemas and validators, but
it never labels a reduced or unresolved object ``calibration_target_specs.v3``.
Every getter for a final frozen registry aborts until all registration
prerequisites can be resolved from immutable authority.
"""

from __future__ import annotations

import copy
import hashlib
import math
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import build_covered_earnings_membership_adjudication as adjudication
import build_ssa_covered_earnings_calibration_targets as extraction

DESIGN_PATH = "docs/design/covered_earnings_correction.md"
BASE_DESIGN_RATIFICATION_COMMIT = "59fd058b943c2b9960af9cb98ecdec97709cc2dd"
DESIGN_RATIFICATION_COMMIT = "062d74187e3263cd4a7fad3851a9b8c699a2556c"
DESIGN_REVISION = 16
DESIGN_BLOB_SHA256 = (
    "c4f3ae022d2e623f4316600e16ec3bded10f0160d197ce64e37f35015e55c92f"
)
RATIFICATION_CLOSURE_BINDINGS = (
    {
        "path": ("docs/analysis/amendment_13_ratification/closure_v1.json"),
        "raw_byte_size": 842,
        "raw_sha256": (
            "fce13fc1e5e2b4026a34dab735ca36186b147260bd0a137979aa52711affabd7"
        ),
    },
    {
        "path": ("docs/analysis/amendment_14_ratification/closure_v1.json"),
        "raw_byte_size": 842,
        "raw_sha256": (
            "0770fc470187d41bc32198b1acbad61927f07f27f26192cb5093a30e411d57d4"
        ),
    },
)
ROOT = Path(__file__).resolve().parents[1]

CALIBRATION_TARGET_SPECS_SCHEMA_VERSION = "calibration_target_specs.v3"
VERIFIED_ROLE_SPECS_SCHEMA_VERSION = "verified_role_specs.v1"
PHYSICAL_SOURCE_CELL_SPECS_SCHEMA_VERSION = "physical_source_cell_specs.v1"
OFFICIAL_SOURCE_ALIAS_SPECS_SCHEMA_VERSION = "official_source_alias_specs.v1"
OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS_SCHEMA_VERSION = (
    "official_source_arithmetic_rule_specs.v1"
)

PROPOSED_SOURCE_ARTIFACT_VINTAGE_ID = (
    "ssa_covered_earnings_calibration_targets.vintage2"
)
TARGET_YEARS = tuple(range(1968, 2023))
ROLE_RULE_ID = (
    "verified_calendar_year_1968_2008_train_2009_2014_validation_"
    "2015_2022_heldout_v1"
)
ROLE_ORDER = ("train", "validation", "held_out_diagnostic")

TARGET_FAMILY_ORDER = (
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

CALIBRATION_TARGET_SPEC_FIELDS = (
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

UNIVERSE_FIELDS = (
    "publication_scope",
    "geography",
    "population",
    "time_basis",
    "worker_unit",
    "duplicate_worker_rule",
    "zero_earner_rule",
)
TRANSFORMATION_FIELDS = (
    "operation",
    "operand_cell_ids",
    "formula",
    "domain",
)
UNIVERSE_CONCORDANCE_FIELDS = (
    "official_ratio_universe",
    "model_analogue_universe",
    "element_mappings",
    "frame_relation",
    "verification_status",
    "source_sha256",
)
UNIVERSE_ELEMENT_MAPPING_FIELDS = (
    "official_element",
    "model_rule",
    "status",
)
CANDIDATE_OUTPUT_SELECTOR_FIELDS = (
    "calendar_year",
    "year_source_class",
    "availability",
    "field_ids",
    "aggregation",
    "joint_probability_rule",
    "cap_stage",
    "projection_draw_reduction",
    "unit",
)
TOLERANCE_NOT_APPLICABLE_FIELDS = ("applicability",)
TOLERANCE_SELECTION_GATE_FIELDS = (
    "applicability",
    "metric",
    "maximum",
)
PUBLISHED_ROUNDING_INTERVAL_FIELDS = (
    "status",
    "lower",
    "upper",
    "lower_closed",
    "upper_closed",
    "rule_source_document_id",
    "rule_citation",
)

_HEX_64 = re.compile(r"[0-9a-f]{64}")
_TARGET_ID = re.compile(r"(?P<family>[a-z0-9_]+):(?P<year>[0-9]{4})")
_SOURCE_CELL_ID = re.compile(
    r"(?P<table>[^/\s]+)/(?P<year>[0-9]{4})/(?P<component>[^/\s]+)"
)
_MAPPING_STATUSES = {
    "exact_concept_match",
    "registered_frame_difference",
}
_LOSS_BY_TARGET_FAMILY = {
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
_RAW_FAMILY_COEFFICIENT = {
    "b2_wage_total_intensity": 2,
    "b2_se_total_intensity": 2,
    "b11_se_only_worker_share": 1,
    "b11_dual_type_worker_share": 1,
}
_DEPENDENCY_GROUP_BY_TARGET_FAMILY = {
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
_SOURCE_STATUSES = {"historical", "preliminary"}
_AVAILABLE_SOURCE_CLASSES = {
    "direct_questionnaire",
    "boundary_2014",
    "projected",
}
_UNAVAILABLE_SOURCE_CLASSES = {
    "structural_gap_imputed",
    "claim_specific_boundary_gap",
}
_FITTING_FAMILIES = frozenset(
    family
    for family, loss in _LOSS_BY_TARGET_FAMILY.items()
    if loss != "no_fitting_loss"
)
_INTENSITY_FAMILIES = {
    "b2_wage_total_intensity",
    "b2_se_total_intensity",
}
_B11_SELECTION_FAMILIES = {
    "b11_se_only_worker_share",
    "b11_dual_type_worker_share",
}
_SOURCE_COMPONENTS_BY_TARGET_FAMILY = {
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


def _row_law(
    *,
    operation: str,
    formula: str,
    domain: str,
    stored_unit: str,
    field_ids: Sequence[str],
    aggregation: str,
    cap_stage: str,
) -> dict[str, Any]:
    return {
        "transformation": {
            "operation": operation,
            "formula": formula,
            "domain": domain,
        },
        "stored_unit": stored_unit,
        "selector": {
            "field_ids": list(field_ids),
            "aggregation": aggregation,
            "joint_probability_rule": (
                "analytic_joint_state_within_projection_draw"
            ),
            "cap_stage": cap_stage,
            "unit": stored_unit,
        },
    }


_TARGET_FAMILY_ROW_LAWS = {
    "b2_wage_total_intensity": _row_law(
        operation="divide",
        formula="c5/c11",
        domain="strictly_positive_denominator",
        stored_unit="current_dollars_per_worker",
        field_ids=(
            "covered_employee_wages_uncapped",
            "b2_wage_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(covered_employee_wages_uncapped)/"
            "sum(b2_wage_worker_membership_probability_analytic)"
        ),
        cap_stage="pre_person_level_oasdi_cap",
    ),
    "b2_se_total_intensity": _row_law(
        operation="divide",
        formula="c8/c12",
        domain="strictly_positive_denominator_signed_numerator",
        stored_unit="current_dollars_per_worker",
        field_ids=(
            "covered_se_net_earnings_pre_seca",
            "b2_se_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(covered_se_net_earnings_pre_seca)/"
            "sum(b2_se_worker_membership_probability_analytic)"
        ),
        cap_stage="pre_seca_factor_threshold_and_oasdi_cap",
    ),
    "b11_se_only_worker_share": _row_law(
        operation="subtract_then_divide",
        formula="(workers_total-workers_wage)/workers_total",
        domain="nonnegative_implied_numerator_strictly_positive_total",
        stored_unit="share",
        field_ids=(
            "b11_se_only_worker_probability_analytic",
            "b11_any_worker_probability_analytic",
        ),
        aggregation=(
            "sum(b11_se_only_worker_probability_analytic)/"
            "sum(b11_any_worker_probability_analytic)"
        ),
        cap_stage="registered_worker_membership_definition",
    ),
    "b11_dual_type_worker_share": _row_law(
        operation="add_subtract_then_divide",
        formula=(
            "(workers_wage+workers_self_employment-workers_total)/"
            "workers_total"
        ),
        domain="nonnegative_implied_numerator_strictly_positive_total",
        stored_unit="share",
        field_ids=(
            "b11_dual_type_worker_probability_analytic",
            "b11_any_worker_probability_analytic",
        ),
        aggregation=(
            "sum(b11_dual_type_worker_probability_analytic)/"
            "sum(b11_any_worker_probability_analytic)"
        ),
        cap_stage="registered_worker_membership_definition",
    ),
    "b11_wage_only_worker_share": _row_law(
        operation="subtract_then_divide",
        formula="(workers_total-workers_self_employment)/workers_total",
        domain="nonnegative_implied_numerator_strictly_positive_total",
        stored_unit="share",
        field_ids=(
            "b11_wage_only_worker_probability_analytic",
            "b11_any_worker_probability_analytic",
        ),
        aggregation=(
            "sum(b11_wage_only_worker_probability_analytic)/"
            "sum(b11_any_worker_probability_analytic)"
        ),
        cap_stage="registered_worker_membership_definition",
    ),
    "b2_type_count_mix": _row_law(
        operation="divide_by_component_sum",
        formula="c12/(c11+c12)",
        domain="nonnegative_components_strictly_positive_sum",
        stored_unit="share",
        field_ids=(
            "b2_wage_worker_membership_probability_analytic",
            "b2_se_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(b2_se_worker_membership_probability_analytic)/"
            "(sum(b2_wage_worker_membership_probability_analytic)+"
            "sum(b2_se_worker_membership_probability_analytic))"
        ),
        cap_stage="registered_worker_membership_definition",
    ),
    "b2_se_total_component_share": _row_law(
        operation="divide_by_component_sum",
        formula="c8/(c5+c8)",
        domain="strictly_positive_component_sum",
        stored_unit="share",
        field_ids=(
            "covered_employee_wages_uncapped",
            "covered_se_net_earnings_pre_seca",
        ),
        aggregation=(
            "sum(covered_se_net_earnings_pre_seca)/"
            "(sum(covered_employee_wages_uncapped)+"
            "sum(covered_se_net_earnings_pre_seca))"
        ),
        cap_stage="pre_seca_factor_threshold_and_oasdi_cap_component_ratio",
    ),
    "b2_wage_taxable_intensity": _row_law(
        operation="divide",
        formula="c13/c11",
        domain="strictly_positive_denominator",
        stored_unit="current_dollars_per_worker",
        field_ids=(
            "oasdi_taxable_wages_person",
            "b2_wage_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(oasdi_taxable_wages_person)/"
            "sum(b2_wage_worker_membership_probability_analytic)"
        ),
        cap_stage="post_person_level_oasdi_cap_over_registered_membership",
    ),
    "b2_se_taxable_intensity": _row_law(
        operation="divide",
        formula="c17/c12",
        domain="strictly_positive_denominator",
        stored_unit="current_dollars_per_worker",
        field_ids=(
            "oasdi_taxable_se_person",
            "b2_se_worker_membership_probability_analytic",
        ),
        aggregation=(
            "sum(oasdi_taxable_se_person)/"
            "sum(b2_se_worker_membership_probability_analytic)"
        ),
        cap_stage="post_wage_first_oasdi_cap_over_registered_membership",
    ),
    "b2_wage_taxable_fraction": _row_law(
        operation="divide",
        formula="c13/c5",
        domain="strictly_positive_denominator",
        stored_unit="share",
        field_ids=(
            "oasdi_taxable_wages_person",
            "covered_employee_wages_uncapped",
        ),
        aggregation=(
            "sum(oasdi_taxable_wages_person)/"
            "sum(covered_employee_wages_uncapped)"
        ),
        cap_stage="post_person_level_oasdi_cap_over_pre_cap_amount",
    ),
    "b2_se_taxable_fraction": _row_law(
        operation="divide",
        formula="c17/c8",
        domain="strictly_positive_denominator",
        stored_unit="share",
        field_ids=(
            "oasdi_taxable_se_person",
            "covered_se_net_earnings_pre_seca",
        ),
        aggregation=(
            "sum(oasdi_taxable_se_person)/"
            "sum(covered_se_net_earnings_pre_seca)"
        ),
        cap_stage="post_wage_first_oasdi_cap_over_pre_seca_net_amount",
    ),
    "b11_taxable_earnings_component_reconciliation": _row_law(
        operation="subtract_components_from_total",
        formula=(
            "taxable_earnings_total-taxable_earnings_wage-"
            "taxable_earnings_self_employment"
        ),
        domain="structural_dependence_only_no_numeric_equality_assertion",
        stored_unit="current_dollars",
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
        cap_stage="post_person_level_oasdi_cap",
    ),
    "b11_contributions_component_reconciliation": _row_law(
        operation="subtract_components_from_total",
        formula=(
            "contributions_total-contributions_wage-"
            "contributions_self_employment"
        ),
        domain="structural_dependence_only_no_numeric_equality_assertion",
        stored_unit="current_dollars",
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
        cap_stage="post_person_level_oasdi_cap_and_registered_rates",
    ),
    "b11_se_contribution_share": _row_law(
        operation="divide_by_component_sum",
        formula=(
            "contributions_self_employment/"
            "(contributions_wage+contributions_self_employment)"
        ),
        domain="nonnegative_components_strictly_positive_sum",
        stored_unit="share",
        field_ids=(
            "oasdi_taxable_wages_person",
            "registered_wage_oasdi_combined_rate",
            "oasdi_taxable_se_person",
            "registered_se_oasdi_rate",
        ),
        aggregation=(
            "sum(oasdi_taxable_se_person*registered_se_oasdi_rate)/"
            "sum(oasdi_taxable_wages_person*"
            "registered_wage_oasdi_combined_rate+"
            "oasdi_taxable_se_person*registered_se_oasdi_rate)"
        ),
        cap_stage="post_person_level_oasdi_cap_and_registered_rates",
    ),
}

_AVAILABLE_SELECTOR_SCALAR_FIELDS = (
    "aggregation",
    "joint_probability_rule",
    "cap_stage",
    "projection_draw_reduction",
    "unit",
)

UNRESOLVED_AUTHORITY_FIELDS = (
    {
        "field": "universe",
        "status": "unresolved_source_membership",
        "reason": (
            "committed bytes do not settle every zero, loss-only, threshold, "
            "multiple-job, and multiple-component membership case"
        ),
    },
    {
        "field": "model_universe_id",
        "status": "missing_frozen_model_selector",
        "reason": (
            "no immutable correction selector freezes the required age, "
            "annual-presence, worker-type, duplicate, and zero-earner laws"
        ),
    },
    {
        "field": "model_weight_source_sha256",
        "status": "missing_registered_weight_input_digest",
        "reason": (
            "no immutable correction model-weight input is available to hash"
        ),
    },
    {
        "field": "denominator_and_joint_analytic_selectors",
        "status": "selector_ids_resolved_membership_predicates_unestablished",
        "reason": (
            "design-fixed selector IDs and joint reduction cannot become "
            "executable until every source-membership predicate is settled"
        ),
    },
    {
        "field": "universe_concordance",
        "status": "cannot_pass_without_both_universes",
        "reason": (
            "an exact official-to-model mapping cannot be certified while "
            "the official membership and model selector remain unresolved"
        ),
    },
)

RESOLVED_AUTHORITY_FIELDS = (
    {
        "field": "model_weight_field",
        "status": "resolved_from_committed_first_estimates_authority",
        "value": "weight",
        "authority_id": (
            "first_estimates_fixed_start_wave_psid_cross_sectional_weight_v1"
        ),
    },
)


class RegistryValidationError(ValueError):
    """A supplied registry violates a ratified schema or identity law."""


class RegistrationAborted(RegistryValidationError):
    """Immutable authority is insufficient to emit a final registry."""


def _run_git(
    *arguments: str,
    text: bool = False,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
    """Run raw-object Git with ambient Git controls removed."""

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=text,
        env=environment,
    )


def design_binding() -> dict[str, Any]:
    """Return the ratified design identity."""

    ancestry = _run_git(
        "merge-base",
        "--is-ancestor",
        BASE_DESIGN_RATIFICATION_COMMIT,
        DESIGN_RATIFICATION_COMMIT,
    )
    if ancestry.returncode != 0:
        raise RegistrationAborted(
            "base design is not an ancestor of amendment-1 ratification"
        )
    worktree_bytes = (ROOT / DESIGN_PATH).read_bytes()
    head = _run_git("show", f"HEAD:{DESIGN_PATH}")
    if head.returncode != 0:
        raise RegistrationAborted(
            "covered-earnings design is unavailable from HEAD"
        )
    ratified = _run_git("show", f"{DESIGN_RATIFICATION_COMMIT}:{DESIGN_PATH}")
    if ratified.returncode != 0:
        raise RegistrationAborted(
            "covered-earnings design is unavailable from ratification commit"
        )
    head_bytes = head.stdout
    ratified_bytes = ratified.stdout
    if not (worktree_bytes == head_bytes == ratified_bytes):
        raise RegistrationAborted(
            "covered-earnings design differs across worktree, HEAD, and "
            "ratification commit"
        )
    if hashlib.sha256(head_bytes).hexdigest() != DESIGN_BLOB_SHA256:
        raise RegistrationAborted("covered-earnings design blob digest drift")
    return {
        "path": DESIGN_PATH,
        "ratification_commit": DESIGN_RATIFICATION_COMMIT,
        "revision": DESIGN_REVISION,
        "blob_sha256": DESIGN_BLOB_SHA256,
        "ratification_closures": [
            dict(binding) for binding in RATIFICATION_CLOSURE_BINDINGS
        ],
    }


def role_for_year(year: int) -> str:
    """Independently derive the only permitted evidentiary role."""

    if type(year) is not int:
        raise RegistryValidationError("verified calendar year must be int")
    if 1968 <= year <= 2008:
        return "train"
    if 2009 <= year <= 2014:
        return "validation"
    if 2015 <= year <= 2022:
        return "held_out_diagnostic"
    raise RegistryValidationError(
        f"verified calendar year {year!r} is outside 1968-2022"
    )


def model_year_source_class_for_year(year: int) -> str:
    """Return the design-frozen direct/gap/boundary/projected class."""

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


def calibration_target_schema() -> dict[str, Any]:
    """Return the exact public shape without fabricating a target row."""

    return {
        "schema_version": CALIBRATION_TARGET_SPECS_SCHEMA_VERSION,
        "row_fields": list(CALIBRATION_TARGET_SPEC_FIELDS),
        "universe_fields": list(UNIVERSE_FIELDS),
        "transformation_fields": list(TRANSFORMATION_FIELDS),
        "universe_concordance_fields": list(UNIVERSE_CONCORDANCE_FIELDS),
        "universe_element_mapping_fields": list(
            UNIVERSE_ELEMENT_MAPPING_FIELDS
        ),
        "candidate_output_selector_fields": list(
            CANDIDATE_OUTPUT_SELECTOR_FIELDS
        ),
        "published_rounding_interval_fields": list(
            PUBLISHED_ROUNDING_INTERVAL_FIELDS
        ),
        "tolerance_not_applicable_fields": list(
            TOLERANCE_NOT_APPLICABLE_FIELDS
        ),
        "tolerance_selection_gate_fields": list(
            TOLERANCE_SELECTION_GATE_FIELDS
        ),
    }


def target_family_registry() -> list[dict[str, Any]]:
    """Return the exact amendment-1 14-family order and coefficient law."""

    rows = []
    for family in TARGET_FAMILY_ORDER:
        raw_coefficient = _RAW_FAMILY_COEFFICIENT.get(family, 0)
        rows.append(
            {
                "target_family": family,
                "dependency_group": _DEPENDENCY_GROUP_BY_TARGET_FAMILY[family],
                "loss": _LOSS_BY_TARGET_FAMILY[family],
                "raw_family_coefficient": raw_coefficient,
                "normalized_effective_weight_numerator": raw_coefficient,
                "normalized_effective_weight_denominator": (
                    6 if raw_coefficient else 1
                ),
                "transformation": copy.deepcopy(
                    _TARGET_FAMILY_ROW_LAWS[family]["transformation"]
                ),
                "stored_unit": _TARGET_FAMILY_ROW_LAWS[family]["stored_unit"],
                "available_candidate_output_selector": copy.deepcopy(
                    _TARGET_FAMILY_ROW_LAWS[family]["selector"]
                ),
            }
        )
    return rows


def accepted_source_artifact() -> dict[str, Any]:
    """Return exactly the validator-accepted, tracked vintage-2 artifact."""

    lineage = extraction.validate_tracked_vintage_lineage()
    if lineage["tracked_vintage_suffixes"] != [2]:
        raise RegistrationAborted(
            "source artifact lineage is not exactly H={2}"
        )
    artifact = extraction.build()
    extraction.validate_artifact(artifact)
    if extraction.render() != extraction.OUT_PATH.read_bytes():
        raise RegistrationAborted(
            "tracked vintage-2 bytes do not reproduce from committed sources"
        )
    return artifact


def registration_status() -> dict[str, Any]:
    """Re-adjudicate committed bytes and report the remaining closed gates."""

    artifact = accepted_source_artifact()
    membership = adjudication.build()
    return {
        "registration_complete": False,
        "source_artifact_status": "accepted",
        "source_artifact_vintage_id": artifact["artifact_vintage_id"],
        "source_artifact_schema_version": artifact["schema_version"],
        "source_artifact_lineage_suffixes": [2],
        "optional_covered_share_status": artifact["optional_covered_share"][
            "status"
        ],
        "calibration_target_schema_version": (
            CALIBRATION_TARGET_SPECS_SCHEMA_VERSION
        ),
        "target_family_order": list(TARGET_FAMILY_ORDER),
        "emitted_target_row_count": 0,
        "resolved_authority_fields": copy.deepcopy(
            list(RESOLVED_AUTHORITY_FIELDS)
        ),
        "unresolved_authority_fields": copy.deepcopy(
            list(UNRESOLVED_AUTHORITY_FIELDS)
        ),
        "registration_authority_adjudications": copy.deepcopy(
            membership["registration_authority_adjudications"]
        ),
        "family_dispositions": copy.deepcopy(
            membership["family_dispositions"]
        ),
        "failure_disposition": "abort",
    }


def _exact_keys(
    value: object,
    fields: Sequence[str],
    where: str,
) -> Mapping[str, Any]:
    if type(value) is not dict:
        raise RegistryValidationError(f"{where} must be a JSON object")
    missing = set(fields) - set(value)
    extra = set(value) - set(fields)
    if missing or extra:
        raise RegistryValidationError(
            f"{where} has wrong fields; "
            f"missing={sorted(missing)!r}, extra={sorted(extra)!r}"
        )
    return value


def _nonempty_string(value: object, where: str) -> str:
    if type(value) is not str or not value:
        raise RegistryValidationError(f"{where} must be a nonempty string")
    return value


def _json_year(value: object, where: str) -> int:
    if type(value) is not int or value not in TARGET_YEARS:
        raise RegistryValidationError(
            f"{where} must be an integer calendar year in 1968-2022"
        )
    return value


def _ordered_unique_strings(
    value: object,
    where: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    if type(value) is not list or (not value and not allow_empty):
        raise RegistryValidationError(
            f"{where} must be an ordered "
            f"{'possibly empty' if allow_empty else 'nonempty'} array"
        )
    if any(type(item) is not str or not item for item in value):
        raise RegistryValidationError(
            f"{where} members must be nonempty strings"
        )
    if len(value) != len(set(value)):
        raise RegistryValidationError(f"{where} members must be unique")
    return value


def _finite_json_number(value: object, where: str) -> int | float:
    if type(value) not in {int, float}:
        raise RegistryValidationError(f"{where} must be a finite JSON number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise RegistryValidationError(f"{where} must be a finite JSON number")
    return value


def _source_cell_year(value: object, where: str) -> int:
    source_cell_id = _nonempty_string(value, where)
    match = _SOURCE_CELL_ID.fullmatch(source_cell_id)
    if match is None:
        raise RegistryValidationError(
            f"{where} must encode an ASCII calendar year"
        )
    return _json_year(int(match.group("year")), where)


def _validate_universe(value: object, where: str) -> None:
    universe = _exact_keys(value, UNIVERSE_FIELDS, where)
    for field in UNIVERSE_FIELDS:
        _nonempty_string(universe[field], f"{where}.{field}")


def _validate_rounding_interval(
    value: object,
    row: Mapping[str, Any],
) -> None:
    where = f"{row['target_id']}.published_rounding_interval"
    interval = _exact_keys(
        value,
        PUBLISHED_ROUNDING_INTERVAL_FIELDS,
        where,
    )
    status = interval["status"]
    other_fields = PUBLISHED_ROUNDING_INTERVAL_FIELDS[1:]
    if status == "not_established_from_source_bytes":
        if any(interval[field] is not None for field in other_fields):
            raise RegistryValidationError(
                f"{where} unverified values must all be null"
            )
        return
    if status != "source_verified":
        raise RegistryValidationError(f"{where}.status")
    lower = _finite_json_number(interval["lower"], f"{where}.lower")
    upper = _finite_json_number(interval["upper"], f"{where}.upper")
    if lower > upper:
        raise RegistryValidationError(f"{where} lower exceeds upper")
    for field in ("lower_closed", "upper_closed"):
        if type(interval[field]) is not bool:
            raise RegistryValidationError(f"{where}.{field} must be boolean")
    for field in ("rule_source_document_id", "rule_citation"):
        _nonempty_string(interval[field], f"{where}.{field}")
    if row["target_family"] in _SOURCE_COMPONENTS_BY_TARGET_FAMILY:
        raise RegistryValidationError(
            f"{where} B2/B11 source bytes cannot verify rounding"
        )


def _validate_transformation(value: object, row: Mapping[str, Any]) -> None:
    where = f"{row['target_id']}.transformation"
    transformation = _exact_keys(value, TRANSFORMATION_FIELDS, where)
    operands = _ordered_unique_strings(
        transformation["operand_cell_ids"],
        f"{where}.operand_cell_ids",
    )
    if operands != row["source_cell_ids"]:
        raise RegistryValidationError(
            f"{where}.operand_cell_ids must equal source_cell_ids"
        )
    for field in ("operation", "formula", "domain"):
        _nonempty_string(transformation[field], f"{where}.{field}")
    expected = _TARGET_FAMILY_ROW_LAWS[row["target_family"]]["transformation"]
    for field, expected_value in expected.items():
        if transformation[field] != expected_value:
            raise RegistryValidationError(
                f"{where}.{field} violates target-family law"
            )


def _validate_concordance(value: object, where: str) -> None:
    concordance = _exact_keys(
        value,
        UNIVERSE_CONCORDANCE_FIELDS,
        where,
    )
    for field in ("official_ratio_universe", "model_analogue_universe"):
        _nonempty_string(concordance[field], f"{where}.{field}")
    mappings = concordance["element_mappings"]
    if type(mappings) is not list or not mappings:
        raise RegistryValidationError(
            f"{where}.element_mappings must be nonempty"
        )
    for index, value in enumerate(mappings):
        mapping = _exact_keys(
            value,
            UNIVERSE_ELEMENT_MAPPING_FIELDS,
            f"{where}.element_mappings[{index}]",
        )
        _nonempty_string(
            mapping["official_element"],
            f"{where}.element_mappings[{index}].official_element",
        )
        _nonempty_string(
            mapping["model_rule"],
            f"{where}.element_mappings[{index}].model_rule",
        )
        if mapping["status"] not in _MAPPING_STATUSES:
            raise RegistryValidationError(
                f"{where}.element_mappings[{index}].status"
            )
    if (
        concordance["frame_relation"]
        != "frame_relative_not_population_aligned"
    ):
        raise RegistryValidationError(f"{where}.frame_relation")
    if concordance["verification_status"] != "pass":
        raise RegistryValidationError(f"{where}.verification_status")
    if (
        type(concordance["source_sha256"]) is not str
        or _HEX_64.fullmatch(concordance["source_sha256"]) is None
    ):
        raise RegistryValidationError(f"{where}.source_sha256")


def _validate_tolerance(value: object, where: str) -> None:
    if type(value) is not dict:
        raise RegistryValidationError(f"{where} must be a tagged object")
    applicability = value.get("applicability")
    if applicability == "not_selection_gate":
        _exact_keys(value, TOLERANCE_NOT_APPLICABLE_FIELDS, where)
        return
    if applicability != "selection_gate":
        raise RegistryValidationError(f"{where}.applicability")
    tolerance = _exact_keys(value, TOLERANCE_SELECTION_GATE_FIELDS, where)
    _nonempty_string(tolerance["metric"], f"{where}.metric")
    maximum = _finite_json_number(tolerance["maximum"], f"{where}.maximum")
    if maximum <= 0:
        raise RegistryValidationError(f"{where}.maximum")


def _validate_selector(
    value: object,
    row: Mapping[str, Any],
) -> str:
    where = f"{row['target_id']}.candidate_output_selector"
    selector = _exact_keys(value, CANDIDATE_OUTPUT_SELECTOR_FIELDS, where)
    if _json_year(selector["calendar_year"], f"{where}.calendar_year") != (
        row["target_year"]
    ):
        raise RegistryValidationError(f"{where}.calendar_year mismatch")
    if selector["year_source_class"] != row["model_year_source_class"]:
        raise RegistryValidationError(f"{where}.year_source_class mismatch")
    source_class = row["model_year_source_class"]
    if source_class in _AVAILABLE_SOURCE_CLASSES:
        expected_availability = "available"
    elif source_class in _UNAVAILABLE_SOURCE_CLASSES:
        expected_availability = (
            "not_applicable_no_claim_independent_model_analogue"
        )
    else:
        raise RegistryValidationError(f"{where}.year_source_class")
    if selector["availability"] != expected_availability:
        raise RegistryValidationError(
            f"{where}.availability violates source-class law"
        )
    if expected_availability == "available":
        field_ids = _ordered_unique_strings(
            selector["field_ids"],
            f"{where}.field_ids",
        )
        for field in _AVAILABLE_SELECTOR_SCALAR_FIELDS:
            _nonempty_string(selector[field], f"{where}.{field}")
        if (
            selector["projection_draw_reduction"]
            != "arithmetic_mean_over_20_draws"
        ):
            raise RegistryValidationError(f"{where}.projection_draw_reduction")
        if selector["unit"] != row["stored_unit"]:
            raise RegistryValidationError(f"{where}.unit mismatch")
        expected = _TARGET_FAMILY_ROW_LAWS[row["target_family"]]["selector"]
        if field_ids != expected["field_ids"]:
            raise RegistryValidationError(
                f"{where}.field_ids violate target-family law"
            )
        for field in (
            "aggregation",
            "joint_probability_rule",
            "cap_stage",
            "unit",
        ):
            if selector[field] != expected[field]:
                raise RegistryValidationError(
                    f"{where}.{field} violates target-family law"
                )
    else:
        field_ids = _ordered_unique_strings(
            selector["field_ids"],
            f"{where}.field_ids",
            allow_empty=True,
        )
        if field_ids:
            raise RegistryValidationError(
                f"{where}.field_ids must be empty when unavailable"
            )
        for field in _AVAILABLE_SELECTOR_SCALAR_FIELDS:
            if selector[field] is not None:
                raise RegistryValidationError(
                    f"{where}.{field} must be null when unavailable"
                )
    return expected_availability


def _expected_selection_eligibility(
    row: Mapping[str, Any],
    availability: str,
) -> bool:
    return (
        row["effective_role"] == "validation"
        and row["target_family"] in _FITTING_FAMILIES
        and row["model_year_source_class"]
        in {"direct_questionnaire", "boundary_2014"}
        and availability == "available"
    )


def _expected_tolerances(target_family: str) -> tuple[dict, dict]:
    if target_family in _INTENSITY_FAMILIES:
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
    if target_family in _B11_SELECTION_FAMILIES:
        cell_maximum = 0.03
        family_maximum = 0.015
    else:
        raise RegistryValidationError(
            f"{target_family} has no registered selection tolerance"
        )
    return (
        {
            "applicability": "selection_gate",
            "metric": "absolute_share_error",
            "maximum": cell_maximum,
        },
        {
            "applicability": "selection_gate",
            "metric": "rms_absolute_share_error",
            "maximum": family_maximum,
        },
    )


def validate_calibration_target_row_schema(
    value: object,
    *,
    index: int = 0,
) -> None:
    """Validate exact row-local laws without claiming foreign-key authority."""

    row = _exact_keys(
        value,
        CALIBRATION_TARGET_SPEC_FIELDS,
        f"calibration_target_specs[{index}]",
    )
    target_id = _nonempty_string(row["target_id"], "target_id")
    target_family = _nonempty_string(
        row["target_family"],
        f"{target_id}.target_family",
    )
    match = _TARGET_ID.fullmatch(target_id)
    if (
        match is None
        or match.group("family") != target_family
        or target_family not in TARGET_FAMILY_ORDER
    ):
        raise RegistryValidationError(f"{target_id!r} target-ID grammar")
    parsed_year = int(match.group("year"))
    for field in (
        "target_year",
        "verified_calendar_year",
        "source_year",
    ):
        if _json_year(row[field], f"{target_id}.{field}") != parsed_year:
            raise RegistryValidationError(
                f"{target_id}.{field} violates year-equality law"
            )
    for field in (
        "stored_unit",
        "model_universe_id",
    ):
        _nonempty_string(row[field], f"{target_id}.{field}")
    expected_dependency_group = _DEPENDENCY_GROUP_BY_TARGET_FAMILY[
        target_family
    ]
    if row["dependency_group"] != expected_dependency_group:
        raise RegistryValidationError(
            f"{target_id}.dependency_group must be "
            f"{expected_dependency_group}"
        )
    if row["model_weight_field"] != "weight":
        raise RegistryValidationError(
            f"{target_id}.model_weight_field must be weight"
        )
    expected_stored_unit = _TARGET_FAMILY_ROW_LAWS[target_family][
        "stored_unit"
    ]
    if row["stored_unit"] != expected_stored_unit:
        raise RegistryValidationError(
            f"{target_id}.stored_unit must be {expected_stored_unit}"
        )
    if (
        row["source_artifact_vintage_id"]
        != PROPOSED_SOURCE_ARTIFACT_VINTAGE_ID
    ):
        raise RegistryValidationError(
            f"{target_id}.source_artifact_vintage_id"
        )
    source_cell_ids = _ordered_unique_strings(
        row["source_cell_ids"],
        f"{target_id}.source_cell_ids",
    )
    resolved_observation_ids = _ordered_unique_strings(
        row["resolved_observation_ids"],
        f"{target_id}.resolved_observation_ids",
    )
    _ordered_unique_strings(
        row["physical_source_cell_ids"],
        f"{target_id}.physical_source_cell_ids",
    )
    _ordered_unique_strings(
        row["primitive_ancestry_ids"],
        f"{target_id}.primitive_ancestry_ids",
    )
    if len(resolved_observation_ids) != len(source_cell_ids):
        raise RegistryValidationError(
            f"{target_id}.resolved_observation_ids must resolve "
            "source_cell_ids one-to-one"
        )
    for index, source_cell_id in enumerate(source_cell_ids):
        if (
            _source_cell_year(
                source_cell_id,
                f"{target_id}.source_cell_ids[{index}]",
            )
            != parsed_year
        ):
            raise RegistryValidationError(
                f"{target_id}.source_cell_ids[{index}] "
                "violates year-equality law"
            )
    source_components = _SOURCE_COMPONENTS_BY_TARGET_FAMILY.get(target_family)
    if source_components is not None:
        table_id, component_ids = source_components
        expected_source_cell_ids = [
            f"{table_id}/{parsed_year}/{component_id}"
            for component_id in component_ids
        ]
        if source_cell_ids != expected_source_cell_ids:
            raise RegistryValidationError(
                f"{target_id}.source_cell_ids violate target-family law"
            )
    if row["source_status"] not in _SOURCE_STATUSES:
        raise RegistryValidationError(f"{target_id}.source_status")
    expected_class = model_year_source_class_for_year(parsed_year)
    if row["model_year_source_class"] != expected_class:
        raise RegistryValidationError(
            f"{target_id}.model_year_source_class drift"
        )
    _validate_universe(row["universe"], f"{target_id}.universe")
    _validate_transformation(row["transformation"], row)
    _validate_rounding_interval(row["published_rounding_interval"], row)
    if (
        type(row["model_weight_source_sha256"]) is not str
        or _HEX_64.fullmatch(row["model_weight_source_sha256"]) is None
    ):
        raise RegistryValidationError(
            f"{target_id}.model_weight_source_sha256"
        )
    _validate_concordance(
        row["universe_concordance"],
        f"{target_id}.universe_concordance",
    )
    expected_role = role_for_year(parsed_year)
    if (
        row["role_rule_id"] != ROLE_RULE_ID
        or row["declared_role"] != expected_role
        or row["effective_role"] != expected_role
    ):
        raise RegistryValidationError(
            f"{target_id} role was not independently recomputed"
        )
    if (
        row["source_status"] == "preliminary"
        and expected_role != "held_out_diagnostic"
    ):
        raise RegistryValidationError(
            f"{target_id}.source_status preliminary outside held-out role"
        )
    expected_status = "preliminary" if parsed_year >= 2021 else "historical"
    if row["source_status"] != expected_status:
        raise RegistryValidationError(
            f"{target_id}.source_status violates source artifact law"
        )
    expected_loss = _LOSS_BY_TARGET_FAMILY[target_family]
    if row["loss"] != expected_loss:
        raise RegistryValidationError(
            f"{target_id}.loss must be {expected_loss}"
        )
    availability = _validate_selector(
        row["candidate_output_selector"],
        row,
    )
    if type(row["selection_eligible"]) is not bool:
        raise RegistryValidationError(f"{target_id}.selection_eligible")
    expected_selection_eligible = _expected_selection_eligibility(
        row,
        availability,
    )
    if row["selection_eligible"] is not expected_selection_eligible:
        raise RegistryValidationError(
            f"{target_id}.selection_eligible violates role/source-class law"
        )
    loss_weight = _finite_json_number(
        row["loss_weight"],
        f"{target_id}.loss_weight",
    )
    if type(loss_weight) is not int:
        raise RegistryValidationError(
            f"{target_id}.loss_weight must be an exact JSON integer"
        )
    model_choice_cell = availability == "available" and (
        (
            expected_role == "train"
            and row["model_year_source_class"] == "direct_questionnaire"
            and target_family in _FITTING_FAMILIES
        )
        or expected_selection_eligible
    )
    expected_loss_weight = (
        _RAW_FAMILY_COEFFICIENT[target_family] if model_choice_cell else 0
    )
    if loss_weight != expected_loss_weight:
        raise RegistryValidationError(
            f"{target_id}.loss_weight must equal exact amendment-1 integer "
            f"mass {expected_loss_weight}"
        )
    _validate_tolerance(row["cell_tolerance"], f"{target_id}.cell_tolerance")
    _validate_tolerance(
        row["family_tolerance"],
        f"{target_id}.family_tolerance",
    )
    if expected_selection_eligible:
        expected_cell_tolerance, expected_family_tolerance = (
            _expected_tolerances(target_family)
        )
    else:
        expected_cell_tolerance = {"applicability": "not_selection_gate"}
        expected_family_tolerance = {"applicability": "not_selection_gate"}
    if row["cell_tolerance"] != expected_cell_tolerance:
        raise RegistryValidationError(
            f"{target_id}.cell_tolerance violates selection law"
        )
    if row["family_tolerance"] != expected_family_tolerance:
        raise RegistryValidationError(
            f"{target_id}.family_tolerance violates selection law"
        )


def _abort_message() -> str:
    status = registration_status()
    missing = ", ".join(
        row["field"] for row in status["unresolved_authority_fields"]
    )
    return (
        "covered-earnings correction registration aborted: "
        "source artifact accepted; no target family clears every "
        f"prerequisite; unresolved fields={missing}"
    )


def calibration_target_specs() -> list[dict[str, Any]]:
    """Abort instead of returning reduced or unresolved v3 target rows."""

    raise RegistrationAborted(_abort_message())


def physical_source_cell_specs() -> list[dict[str, Any]]:
    """Abort until the complete both-vintage physical registry is proven."""

    raise RegistrationAborted(_abort_message())


def official_source_alias_specs() -> list[dict[str, Any]]:
    """Abort until the complete both-vintage alias registry is proven."""

    raise RegistrationAborted(_abort_message())


def official_source_arithmetic_rule_specs() -> list[dict[str, Any]]:
    """Abort until every source-defined arithmetic rule is proven."""

    raise RegistrationAborted(_abort_message())


def frozen_registries() -> dict[str, Any]:
    """Abort rather than certify a partial collection as frozen authority."""

    raise RegistrationAborted(_abort_message())


def validate_calibration_target_specs(value: object) -> None:
    """Validate row-local laws, then abort before claiming full authority."""

    if type(value) is not list or not value:
        raise RegistryValidationError(
            "calibration_target_specs.v3 must be a nonempty ordered array"
        )
    for index, row in enumerate(value):
        validate_calibration_target_row_schema(row, index=index)
    expected_target_ids = [
        f"{family}:{year}"
        for family in TARGET_FAMILY_ORDER
        for year in TARGET_YEARS
    ]
    actual_target_ids = [row["target_id"] for row in value]
    if actual_target_ids != expected_target_ids:
        raise RegistryValidationError(
            "calibration_target_specs.v3 must contain exactly the 14-family "
            "by 55-year ordered expansion"
        )
    raise RegistrationAborted(_abort_message())


def validate_frozen_registries(**_: object) -> None:
    """Reject all purported final registry sets while prerequisites fail."""

    raise RegistrationAborted(_abort_message())


__all__ = [
    "CALIBRATION_TARGET_SPECS_SCHEMA_VERSION",
    "CALIBRATION_TARGET_SPEC_FIELDS",
    "CANDIDATE_OUTPUT_SELECTOR_FIELDS",
    "DESIGN_PATH",
    "DESIGN_RATIFICATION_COMMIT",
    "DESIGN_REVISION",
    "OFFICIAL_SOURCE_ALIAS_SPECS_SCHEMA_VERSION",
    "OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS_SCHEMA_VERSION",
    "PHYSICAL_SOURCE_CELL_SPECS_SCHEMA_VERSION",
    "PUBLISHED_ROUNDING_INTERVAL_FIELDS",
    "PROPOSED_SOURCE_ARTIFACT_VINTAGE_ID",
    "ROLE_RULE_ID",
    "RegistrationAborted",
    "RegistryValidationError",
    "TARGET_FAMILY_ORDER",
    "TARGET_YEARS",
    "TOLERANCE_NOT_APPLICABLE_FIELDS",
    "TOLERANCE_SELECTION_GATE_FIELDS",
    "TRANSFORMATION_FIELDS",
    "UNIVERSE_CONCORDANCE_FIELDS",
    "UNIVERSE_ELEMENT_MAPPING_FIELDS",
    "UNIVERSE_FIELDS",
    "UNRESOLVED_AUTHORITY_FIELDS",
    "VERIFIED_ROLE_SPECS_SCHEMA_VERSION",
    "accepted_source_artifact",
    "calibration_target_schema",
    "calibration_target_specs",
    "design_binding",
    "frozen_registries",
    "model_year_source_class_for_year",
    "official_source_alias_specs",
    "official_source_arithmetic_rule_specs",
    "physical_source_cell_specs",
    "registration_status",
    "role_for_year",
    "target_family_registry",
    "validate_calibration_target_row_schema",
    "validate_calibration_target_specs",
    "validate_frozen_registries",
    "verified_role_specs",
]
