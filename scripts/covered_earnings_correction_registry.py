"""Fail-closed registration boundary for covered-earnings correction.

The committed SSA bytes establish the 825 Table 4.B2/4.B11 source cells, but
they do not establish the worker-universe laws required by section 6.1 of the
ratified design.  They also do not establish a frozen model-universe selector,
production weight input, or passing official-to-model universe concordance.

This module therefore exposes the exact registry schemas and validators, but
it never labels a reduced or unresolved object ``calibration_target_specs.v2``.
Every getter for a final frozen registry aborts until all registration
prerequisites can be resolved from immutable authority.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

import build_covered_earnings_source_identity_evidence as source_identity
import build_ssa_covered_earnings_calibration_targets as extraction

DESIGN_PATH = "docs/design/covered_earnings_correction.md"
DESIGN_RATIFICATION_COMMIT = "59fd058b943c2b9960af9cb98ecdec97709cc2dd"
DESIGN_REVISION = 2

CALIBRATION_TARGET_SPECS_SCHEMA_VERSION = "calibration_target_specs.v2"
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
    "ssa_precisely_universed_covered_share",
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

_HEX_64 = re.compile(r"[0-9a-f]{64}")
_TARGET_ID = re.compile(r"(?P<family>[a-z0-9_]+):(?P<year>\d{4})")
_MAPPING_STATUSES = {
    "exact_concept_match",
    "registered_frame_difference",
}
_LOSSES = {
    "squared_log_ratio",
    "squared_logit_error",
    "no_fitting_loss",
}
_SOURCE_STATUSES = {"historical", "preliminary"}

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
        "field": "model_weight_field",
        "status": "missing_registered_weight_field",
        "reason": (
            "no correction-specific production input manifest registers a "
            "model weight field"
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
        "field": "universe_concordance",
        "status": "cannot_pass_without_both_universes",
        "reason": (
            "an exact official-to-model mapping cannot be certified while "
            "the official membership and model selector remain unresolved"
        ),
    },
)


class RegistryValidationError(ValueError):
    """A supplied registry violates a ratified schema or identity law."""


class RegistrationAborted(RegistryValidationError):
    """Immutable authority is insufficient to emit a final registry."""


def design_binding() -> dict[str, Any]:
    """Return the ratified design identity."""

    return {
        "path": DESIGN_PATH,
        "ratification_commit": DESIGN_RATIFICATION_COMMIT,
        "revision": DESIGN_REVISION,
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
    }


def registration_status() -> dict[str, Any]:
    """Re-adjudicate committed bytes and report why registration aborts."""

    adjudication = extraction.vb7_adjudication()
    return {
        "registration_complete": False,
        "proposed_artifact_vintage_id": (PROPOSED_SOURCE_ARTIFACT_VINTAGE_ID),
        "calibration_target_schema_version": (
            CALIBRATION_TARGET_SPECS_SCHEMA_VERSION
        ),
        "emitted_target_row_count": 0,
        "unresolved_authority_fields": copy.deepcopy(
            list(UNRESOLVED_AUTHORITY_FIELDS)
        ),
        "vb7_registration_disposition": (
            adjudication["registration_disposition"]
        ),
        "covered_share_required_years": copy.deepcopy(
            adjudication["covered_share_required_years"]
        ),
        "membership_adjudications": copy.deepcopy(
            adjudication["worker_membership_relationships"]
        ),
        "failure_disposition": "abort",
    }


def source_identity_evidence() -> dict[str, Any]:
    """Return source-reproduced, explicitly non-authoritative registries."""

    return source_identity.build()


def validate_source_identity_evidence(value: object) -> None:
    """Re-resolve and validate every physical, alias, and rule evidence row."""

    source_identity.validate_evidence(value)


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


def _validate_universe(value: object, where: str) -> None:
    universe = _exact_keys(value, UNIVERSE_FIELDS, where)
    for field in UNIVERSE_FIELDS:
        _nonempty_string(universe[field], f"{where}.{field}")


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
    maximum = tolerance["maximum"]
    if type(maximum) not in {int, float} or not (0 < maximum < float("inf")):
        raise RegistryValidationError(f"{where}.maximum")


def _validate_selector(
    value: object,
    row: Mapping[str, Any],
) -> None:
    where = f"{row['target_id']}.candidate_output_selector"
    selector = _exact_keys(value, CANDIDATE_OUTPUT_SELECTOR_FIELDS, where)
    if _json_year(selector["calendar_year"], f"{where}.calendar_year") != (
        row["target_year"]
    ):
        raise RegistryValidationError(f"{where}.calendar_year mismatch")
    if selector["year_source_class"] != row["model_year_source_class"]:
        raise RegistryValidationError(f"{where}.year_source_class mismatch")
    if selector["availability"] not in {
        "available",
        "not_applicable_no_claim_independent_model_analogue",
    }:
        raise RegistryValidationError(f"{where}.availability")
    _ordered_unique_strings(
        selector["field_ids"],
        f"{where}.field_ids",
        allow_empty=True,
    )
    for field in (
        "aggregation",
        "joint_probability_rule",
        "cap_stage",
        "projection_draw_reduction",
        "unit",
    ):
        _nonempty_string(selector[field], f"{where}.{field}")


def validate_calibration_target_row_schema(
    value: object,
    *,
    index: int = 0,
) -> None:
    """Validate the exact 30-field and nested schemas for one future row."""

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
        "dependency_group",
        "source_artifact_vintage_id",
        "stored_unit",
        "model_universe_id",
        "model_weight_field",
    ):
        _nonempty_string(row[field], f"{target_id}.{field}")
    for field in (
        "source_cell_ids",
        "resolved_observation_ids",
        "physical_source_cell_ids",
        "primitive_ancestry_ids",
    ):
        _ordered_unique_strings(row[field], f"{target_id}.{field}")
    if row["source_status"] not in _SOURCE_STATUSES:
        raise RegistryValidationError(f"{target_id}.source_status")
    expected_class = model_year_source_class_for_year(parsed_year)
    if row["model_year_source_class"] != expected_class:
        raise RegistryValidationError(
            f"{target_id}.model_year_source_class drift"
        )
    _validate_universe(row["universe"], f"{target_id}.universe")
    _validate_transformation(row["transformation"], row)
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
    if row["loss"] not in _LOSSES:
        raise RegistryValidationError(f"{target_id}.loss")
    loss_weight = row["loss_weight"]
    if type(loss_weight) not in {int, float} or not (
        0 <= loss_weight < float("inf")
    ):
        raise RegistryValidationError(f"{target_id}.loss_weight")
    if type(row["selection_eligible"]) is not bool:
        raise RegistryValidationError(f"{target_id}.selection_eligible")
    _validate_tolerance(row["cell_tolerance"], f"{target_id}.cell_tolerance")
    _validate_tolerance(
        row["family_tolerance"],
        f"{target_id}.family_tolerance",
    )
    if type(row["published_rounding_interval"]) is not dict:
        raise RegistryValidationError(
            f"{target_id}.published_rounding_interval"
        )
    _validate_selector(row["candidate_output_selector"], row)


def _abort_message() -> str:
    status = registration_status()
    missing = ", ".join(
        row["field"] for row in status["unresolved_authority_fields"]
    )
    return (
        "covered-earnings correction registration aborted: "
        f"V-B7={status['vb7_registration_disposition']}; "
        f"unresolved fields={missing}"
    )


def calibration_target_specs() -> list[dict[str, Any]]:
    """Abort instead of returning reduced or unresolved v2 target rows."""

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
    """Validate row schemas, then abort because authority is incomplete."""

    if type(value) is not list or not value:
        raise RegistryValidationError(
            "calibration_target_specs.v2 must be a nonempty ordered array"
        )
    for index, row in enumerate(value):
        validate_calibration_target_row_schema(row, index=index)
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
    "PROPOSED_SOURCE_ARTIFACT_VINTAGE_ID",
    "ROLE_RULE_ID",
    "RegistrationAborted",
    "RegistryValidationError",
    "TARGET_FAMILY_ORDER",
    "TARGET_YEARS",
    "TRANSFORMATION_FIELDS",
    "UNIVERSE_CONCORDANCE_FIELDS",
    "UNIVERSE_ELEMENT_MAPPING_FIELDS",
    "UNIVERSE_FIELDS",
    "UNRESOLVED_AUTHORITY_FIELDS",
    "VERIFIED_ROLE_SPECS_SCHEMA_VERSION",
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
    "source_identity_evidence",
    "validate_calibration_target_row_schema",
    "validate_calibration_target_specs",
    "validate_frozen_registries",
    "validate_source_identity_evidence",
    "verified_role_specs",
]
