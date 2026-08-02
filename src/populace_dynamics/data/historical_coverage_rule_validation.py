"""Pure validators for historical coverage legal-rule rows.

This module implements the source-independent parts of the row law in
sections 4.1 and 19.2 of the covered-earnings design.  It deliberately does
not manufacture the official PSID source-field inventory, legal-domain
cells, interval partitions, or a passing registry.  Those objects can be
validated only after their independently ratified inputs exist.
"""

from __future__ import annotations

import copy
import itertools
import json
import re
from collections.abc import Mapping, MutableSet, Sequence
from fractions import Fraction
from typing import Any

RULE_ROW_KEYS = (
    "rule_id",
    "authority_status",
    "status_family",
    "effective_start",
    "effective_end",
    "jurisdiction",
    "authority_rank",
    "source_document_id",
    "source_sha256",
    "exact_citation",
    "covered_facts",
    "excluded_facts",
    "required_micro_facts",
    "transform",
    "reason_code",
    "unresolved_action",
    "verification_class",
    "verification_claim_ids",
    "affected_inventory_keys",
    "optional_row_consequences",
)
FACT_BINDING_KEYS = (
    "fact_binding_id",
    "premise_ast",
    "micro_fact_slots",
)
MICRO_FACT_SLOT_KEYS = (
    "micro_fact_id",
    "field_purpose",
    "source_field_ref",
    "typed_value_type",
    "typed_value_unit",
    "presence_predicate_ast",
    "missing_reason_code",
)
SOURCE_FIELD_REF_KEYS = ("source_inventory_key", "raw_field_id")
OPTIONAL_CONSEQUENCE_KEYS = (
    "optional_consequence_id",
    "source_inventory_key",
    "consequence",
    "reason_code",
)

FIELD_PURPOSES = (
    "interview_and_role_attachment",
    "amount",
    "reporting_unit",
    "month_or_exposure",
    "assignment",
    "employee_self_or_mixed",
    "incorporation",
    "government_level",
    "industry",
    "occupation",
    "enrollment",
    "job_identifier",
    "state_of_residence",
    "section_218_group",
    "section_218_position",
    "public_retirement_system_participation",
    "federal_retirement_system",
    "federal_service",
    "railroad_covered_employer",
    "railroad_covered_service",
    "ministerial_service",
    "clergy_remuneration",
    "church_employee_service",
    "religious_order_service",
    "clergy_or_religious_exemption",
    "domestic_service",
    "agricultural_service",
    "election_work",
    "family_service",
    "casual_service",
    "foreign_government_service",
    "international_organization_service",
    "nonresident_alien_status",
    "employer_school_nexus",
    "statutory_student_service",
)

FAMILY_SPECS = {
    "section_218_and_mandatory_state_local": (
        "V-B1",
        "registration_required",
        1968,
        2023,
    ),
    "clergy_religious_service": (
        "V-B2",
        "direct_only_optional",
        1968,
        2023,
    ),
    "domestic_service": (
        "V-B3",
        "direct_only_optional",
        1968,
        2023,
    ),
    "agricultural_service": (
        "V-B3",
        "direct_only_optional",
        1968,
        2023,
    ),
    "election_work": (
        "V-B3",
        "direct_only_optional",
        1968,
        2023,
    ),
    "family_service": (
        "V-B3",
        "direct_only_optional",
        1968,
        2023,
    ),
    "casual_service": (
        "V-B3",
        "direct_only_optional",
        1968,
        2023,
    ),
    "foreign_government_service": (
        "V-B3",
        "direct_only_optional",
        1968,
        2023,
    ),
    "international_organization_service": (
        "V-B3",
        "direct_only_optional",
        1968,
        2023,
    ),
    "nonresident_alien_service": (
        "V-B3",
        "direct_only_optional",
        1968,
        2023,
    ),
    "historical_seca": (
        "V-B4",
        "registration_required",
        1968,
        1990,
    ),
    "student_service": (
        "V-B9",
        "direct_only_optional",
        1968,
        2023,
    ),
    "federal_retirement_service": (
        None,
        "direct_only_optional",
        1968,
        2023,
    ),
    "railroad_service": (
        None,
        "direct_only_optional",
        1968,
        2023,
    ),
}

FAMILY_FIELD_PURPOSES = {
    "section_218_and_mandatory_state_local": (
        "government_level",
        "state_of_residence",
        "section_218_group",
        "section_218_position",
        "public_retirement_system_participation",
    ),
    "clergy_religious_service": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "ministerial_service",
        "clergy_remuneration",
        "church_employee_service",
        "religious_order_service",
        "clergy_or_religious_exemption",
    ),
    "domestic_service": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "domestic_service",
    ),
    "agricultural_service": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "agricultural_service",
    ),
    "election_work": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "election_work",
    ),
    "family_service": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "family_service",
    ),
    "casual_service": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "casual_service",
    ),
    "foreign_government_service": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "foreign_government_service",
    ),
    "international_organization_service": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "international_organization_service",
    ),
    "nonresident_alien_service": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "nonresident_alien_status",
    ),
    "historical_seca": (
        "amount",
        "reporting_unit",
        "month_or_exposure",
        "employee_self_or_mixed",
        "incorporation",
    ),
    "student_service": (
        "enrollment",
        "employer_school_nexus",
        "statutory_student_service",
    ),
    "federal_retirement_service": (
        "federal_retirement_system",
        "federal_service",
    ),
    "railroad_service": (
        "railroad_covered_employer",
        "railroad_covered_service",
    ),
}

STATE_LOCAL_JURISDICTIONS = (
    "federal",
    *(f"inventory-state:psid-{ordinal:02d}" for ordinal in range(1, 52)),
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_INVENTORY_KEY = re.compile(r"^psid-slot:[0-9a-f]{64}$")
_VALUE_TYPES = frozenset({"rational", "json_integer", "boolean", "enum"})
_CLASSIFIED_STATUSES = frozenset(
    {
        "covered_wage",
        "covered_self_employment",
        "noncovered",
        "no_disposition",
    }
)
_COMPARISONS = frozenset(
    {"equal", "less", "less_equal", "greater_equal", "greater"}
)
_PREMISE_OPERATORS = _COMPARISONS | {"and", "or"}
_TRANSFORM_OPERATORS = _PREMISE_OPERATORS | {
    "add",
    "subtract",
    "multiply",
    "divide",
    "minimum",
    "maximum",
    "case",
}

# type, unit, nullable
AstSignature = tuple[str, str | None, bool]


class LegalRuleValidationError(ValueError):
    """Raised when a legal-rule row violates the closed ratified grammar."""


def _fail(label: str, message: str) -> LegalRuleValidationError:
    return LegalRuleValidationError(f"{label}: {message}")


def _exact_keys(value: Any, keys: Sequence[str], label: str) -> Mapping:
    if not isinstance(value, Mapping) or set(value) != set(keys):
        raise _fail(label, "keyset drift")
    return value


def _nonnull_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise _fail(label, "expected a nonempty string")
    return value


def _json_integer(value: Any, label: str) -> int:
    if type(value) is not int:
        raise _fail(label, "expected a JSON integer excluding booleans")
    return value


def _unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise _fail(label, "expected an array")
    result = [
        _nonnull_string(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    ]
    if len(result) != len(set(result)):
        raise _fail(label, "contains duplicate strings")
    return result


def _typed_signature(
    value_type: Any,
    unit: Any,
    *,
    nullable: bool,
    label: str,
) -> AstSignature:
    if value_type not in _VALUE_TYPES:
        raise _fail(label, "unregistered value type")
    if value_type in {"rational", "json_integer"}:
        _nonnull_string(unit, f"{label}.unit")
    elif unit is not None:
        raise _fail(label, "boolean/enum unit must be null")
    return value_type, unit, nullable


def _literal_signature(node: Mapping[str, Any], label: str) -> AstSignature:
    _exact_keys(node, ("op", "value", "value_type", "unit"), label)
    value = node["value"]
    value_type = node["value_type"]
    unit = node["unit"]
    if value is None:
        return _typed_signature(value_type, unit, nullable=True, label=label)
    if isinstance(value, bool):
        if value_type != "boolean" or unit is not None:
            raise _fail(label, "boolean literal signature mismatch")
        return "boolean", None, False
    if isinstance(value, str):
        if value_type != "enum" or unit is not None:
            raise _fail(label, "string literal signature mismatch")
        return "enum", None, False
    raise _fail(label, "literal value must be string, boolean, or null")


def _same_nonnullable(
    left: AstSignature, right: AstSignature, label: str
) -> None:
    if left != right or left[2]:
        raise _fail(
            label, "operands must have one identical nonnullable signature"
        )


def _infer_ast(
    node: Any,
    *,
    allowed_leaf_op: str,
    leaf_signatures: Mapping[str, AstSignature],
    used_leaves: MutableSet[str],
    allowed_operators: frozenset[str],
    label: str,
) -> AstSignature:
    if not isinstance(node, Mapping):
        raise _fail(label, "AST node must be an object")
    op = node.get("op")
    if op == allowed_leaf_op:
        id_key = f"{allowed_leaf_op}_id"
        _exact_keys(node, ("op", id_key), label)
        leaf_id = _nonnull_string(node[id_key], f"{label}.{id_key}")
        if leaf_id not in leaf_signatures:
            raise _fail(label, f"unknown {allowed_leaf_op} leaf")
        used_leaves.add(leaf_id)
        return leaf_signatures[leaf_id]
    if op == "rational":
        _exact_keys(node, ("op", "numerator", "denominator", "unit"), label)
        _json_integer(node["numerator"], f"{label}.numerator")
        denominator = _json_integer(
            node["denominator"], f"{label}.denominator"
        )
        if denominator <= 0:
            raise _fail(label, "rational denominator must be positive")
        return _typed_signature(
            "rational", node["unit"], nullable=False, label=label
        )
    if op == "json_integer":
        _exact_keys(node, ("op", "value", "unit"), label)
        _json_integer(node["value"], f"{label}.value")
        return _typed_signature(
            "json_integer", node["unit"], nullable=False, label=label
        )
    if op == "literal":
        return _literal_signature(node, label)
    if op not in allowed_operators:
        raise _fail(label, "unregistered or forbidden AST operation")
    _exact_keys(node, ("op", "args"), label)
    args = node["args"]
    if not isinstance(args, list):
        raise _fail(label, "operator args must be an array")
    if op in {"subtract", "divide", *tuple(_COMPARISONS)}:
        expected_arity = 2
    elif op == "case":
        expected_arity = 3
    else:
        expected_arity = None
    if expected_arity is not None and len(args) != expected_arity:
        raise _fail(label, f"{op} requires exactly {expected_arity} arguments")
    if expected_arity is None and len(args) < 2:
        raise _fail(label, f"{op} requires at least two arguments")
    signatures = [
        _infer_ast(
            arg,
            allowed_leaf_op=allowed_leaf_op,
            leaf_signatures=leaf_signatures,
            used_leaves=used_leaves,
            allowed_operators=allowed_operators,
            label=f"{label}.args[{index}]",
        )
        for index, arg in enumerate(args)
    ]
    if op in {"and", "or"}:
        if any(
            signature != ("boolean", None, False) for signature in signatures
        ):
            raise _fail(label, f"{op} requires nonnullable boolean operands")
        return "boolean", None, False
    if op == "equal":
        _same_nonnullable(signatures[0], signatures[1], label)
        return "boolean", None, False
    if op in _COMPARISONS:
        _same_nonnullable(signatures[0], signatures[1], label)
        if signatures[0][0] not in {"rational", "json_integer"}:
            raise _fail(label, f"{op} requires numeric operands")
        return "boolean", None, False
    if op == "case":
        if signatures[0] != ("boolean", None, False):
            raise _fail(label, "case predicate must be nonnullable boolean")
        if signatures[1] != signatures[2]:
            raise _fail(label, "case branches must have identical signatures")
        return signatures[1]
    if any(
        signature[0] != "rational" or signature[2] for signature in signatures
    ):
        raise _fail(label, f"{op} requires nonnullable rational operands")
    units = [signature[1] for signature in signatures]
    if op in {"add", "subtract", "minimum", "maximum"}:
        if len(set(units)) != 1:
            raise _fail(label, f"{op} operands must have identical units")
        return "rational", units[0], False
    if op == "multiply":
        nondimensionless = [unit for unit in units if unit != "dimensionless"]
        if len(units) != 2 or len(nondimensionless) != 1:
            raise _fail(
                label,
                "multiply requires two operands and exactly one dimensionless unit",
            )
        return "rational", nondimensionless[0], False
    if op == "divide":
        numerator_unit, denominator_unit = units
        if denominator_unit == "dimensionless":
            return "rational", numerator_unit, False
        if numerator_unit == denominator_unit:
            return "rational", "dimensionless", False
        raise _fail(label, "divide unit pair is not registered")
    raise AssertionError(f"unhandled operation: {op}")


def _eval_ast(node: Mapping[str, Any], leaf_values: Mapping[str, Any]) -> Any:
    op = node["op"]
    if op in {"micro_fact", "fact_binding"}:
        return leaf_values[node[f"{op}_id"]]
    if op == "rational":
        return Fraction(node["numerator"], node["denominator"])
    if op == "json_integer":
        return node["value"]
    if op == "literal":
        return node["value"]
    args = node["args"]
    if op == "and":
        for arg in args:
            if not _eval_ast(arg, leaf_values):
                return False
        return True
    if op == "or":
        for arg in args:
            if _eval_ast(arg, leaf_values):
                return True
        return False
    if op == "case":
        selected = args[1] if _eval_ast(args[0], leaf_values) else args[2]
        return _eval_ast(selected, leaf_values)
    values = [_eval_ast(arg, leaf_values) for arg in args]
    if op == "add":
        return sum(values[1:], values[0])
    if op == "subtract":
        return values[0] - values[1]
    if op == "multiply":
        result = values[0]
        for value in values[1:]:
            result *= value
        return result
    if op == "divide":
        if values[1] == 0:
            raise LegalRuleValidationError("transform: division by zero")
        return values[0] / values[1]
    if op == "minimum":
        return min(values)
    if op == "maximum":
        return max(values)
    if op == "equal":
        return values[0] == values[1]
    if op == "less":
        return values[0] < values[1]
    if op == "less_equal":
        return values[0] <= values[1]
    if op == "greater_equal":
        return values[0] >= values[1]
    if op == "greater":
        return values[0] > values[1]
    raise AssertionError(f"unhandled operation: {op}")


def _semantic_bytes(value: Any) -> bytes:
    """Serialize already-validated rule semantics for exact comparisons."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _normalized_ast_leaf_references(
    node: Mapping[str, Any],
    *,
    leaf_op: str,
    replacements: Mapping[str, Any],
    replacement_op: str,
    replacement_id_key: str,
) -> dict[str, Any]:
    """Deep-copy an AST while replacing one registered leaf namespace."""

    if node["op"] == leaf_op:
        original_id = node[f"{leaf_op}_id"]
        return {
            "op": replacement_op,
            replacement_id_key: replacements[original_id],
        }
    result = copy.deepcopy(dict(node))
    if "args" in result:
        result["args"] = [
            _normalized_ast_leaf_references(
                arg,
                leaf_op=leaf_op,
                replacements=replacements,
                replacement_op=replacement_op,
                replacement_id_key=replacement_id_key,
            )
            for arg in result["args"]
        ]
    return result


def _validate_micro_fact_slot(
    slot: Any,
    *,
    global_micro_fact_ids: MutableSet[str],
    affected_inventory_keys: frozenset[str],
    allowed_field_purposes: frozenset[str],
    label: str,
) -> tuple[str, AstSignature]:
    slot = _exact_keys(slot, MICRO_FACT_SLOT_KEYS, label)
    micro_fact_id = _nonnull_string(
        slot["micro_fact_id"], f"{label}.micro_fact_id"
    )
    if micro_fact_id in global_micro_fact_ids:
        raise _fail(label, "micro_fact_id is not globally unique")
    global_micro_fact_ids.add(micro_fact_id)
    if slot["field_purpose"] not in FIELD_PURPOSES:
        raise _fail(
            label, "field_purpose is outside the frozen 35-purpose domain"
        )
    if slot["field_purpose"] not in allowed_field_purposes:
        raise _fail(label, "field_purpose is outside the family domain")
    source_ref = _exact_keys(
        slot["source_field_ref"],
        SOURCE_FIELD_REF_KEYS,
        f"{label}.source_field_ref",
    )
    source_inventory_key = _nonnull_string(
        source_ref["source_inventory_key"],
        f"{label}.source_field_ref.source_inventory_key",
    )
    if _SOURCE_INVENTORY_KEY.fullmatch(source_inventory_key) is None:
        raise _fail(label, "malformed source_inventory_key")
    if source_inventory_key not in affected_inventory_keys:
        raise _fail(
            label, "source_inventory_key is outside the affected domain"
        )
    raw_field_id = source_ref["raw_field_id"]
    if raw_field_id is not None and (
        not isinstance(raw_field_id, str) or not raw_field_id
    ):
        raise _fail(label, "raw_field_id must be a nonempty string or null")
    signature = _typed_signature(
        slot["typed_value_type"],
        slot["typed_value_unit"],
        nullable=False,
        label=label,
    )
    expected_presence = (
        {"op": "literal_false"}
        if raw_field_id is None
        else {"op": "typed_nonmissing", "source_field_ref": "self"}
    )
    if slot["presence_predicate_ast"] != expected_presence:
        raise _fail(
            label, "presence predicate disagrees with the source-field branch"
        )
    _nonnull_string(
        slot["missing_reason_code"], f"{label}.missing_reason_code"
    )
    return micro_fact_id, signature


def _validate_fact_binding(
    binding: Any,
    *,
    expected_id: str,
    global_micro_fact_ids: MutableSet[str],
    affected_inventory_keys: frozenset[str],
    allowed_field_purposes: frozenset[str],
    label: str,
) -> tuple[list[Mapping[str, Any]], bytes]:
    binding = _exact_keys(binding, FACT_BINDING_KEYS, label)
    if binding["fact_binding_id"] != expected_id:
        raise _fail(label, "canonical fact_binding_id drift")
    slots = binding["micro_fact_slots"]
    if not isinstance(slots, list) or not slots:
        raise _fail(label, "micro_fact_slots must be a nonempty array")
    signatures: dict[str, AstSignature] = {}
    for index, slot in enumerate(slots):
        micro_fact_id, signature = _validate_micro_fact_slot(
            slot,
            global_micro_fact_ids=global_micro_fact_ids,
            affected_inventory_keys=affected_inventory_keys,
            allowed_field_purposes=allowed_field_purposes,
            label=f"{label}.micro_fact_slots[{index}]",
        )
        signatures[micro_fact_id] = signature
    used: set[str] = set()
    result_signature = _infer_ast(
        binding["premise_ast"],
        allowed_leaf_op="micro_fact",
        leaf_signatures=signatures,
        used_leaves=used,
        allowed_operators=frozenset(_PREMISE_OPERATORS),
        label=f"{label}.premise_ast",
    )
    if result_signature != ("boolean", None, False):
        raise _fail(label, "premise must return nonnullable boolean/null-unit")
    if used != set(signatures):
        raise _fail(label, "every and only declared microfact must be used")
    slot_indices = {
        slot["micro_fact_id"]: index for index, slot in enumerate(slots)
    }
    normalized_slots = [
        {
            key: copy.deepcopy(value)
            for key, value in slot.items()
            if key != "micro_fact_id"
        }
        for slot in slots
    ]
    normalized_premise = _normalized_ast_leaf_references(
        binding["premise_ast"],
        leaf_op="micro_fact",
        replacements=slot_indices,
        replacement_op="joint_micro_fact_slot",
        replacement_id_key="slot_index",
    )
    signature_preimage = [
        "joint_binding_semantics.v1",
        normalized_slots,
        normalized_premise,
    ]
    return slots, _semantic_bytes(signature_preimage)


def _validate_optional_consequences(
    row: Mapping[str, Any], affected_inventory_keys: list[str]
) -> None:
    consequences = row["optional_row_consequences"]
    if row["verification_class"] == "registration_required":
        if consequences != []:
            raise _fail(
                row["rule_id"], "required rule has optional consequences"
            )
        return
    if not isinstance(consequences, list) or len(consequences) != len(
        affected_inventory_keys
    ):
        raise _fail(row["rule_id"], "optional consequence domain mismatch")
    for index, (consequence, source_key) in enumerate(
        zip(consequences, affected_inventory_keys, strict=True)
    ):
        label = f"{row['rule_id']}.optional_row_consequences[{index}]"
        consequence = _exact_keys(
            consequence, OPTIONAL_CONSEQUENCE_KEYS, label
        )
        if consequence["source_inventory_key"] != source_key:
            raise _fail(label, "source key order drift")
        if (
            consequence["optional_consequence_id"]
            != f"{row['rule_id']}:{source_key}"
        ):
            raise _fail(label, "optional consequence ID drift")
        if consequence["consequence"] not in {"modelable", "unresolved"}:
            raise _fail(label, "unregistered optional consequence")
        _nonnull_string(consequence["reason_code"], f"{label}.reason_code")


def validate_rule_row_syntax(
    row: Any,
    *,
    global_micro_fact_ids: MutableSet[str] | None = None,
) -> None:
    """Validate one 20-field row without pretending to validate its domain.

    Inventory foreign keys, attachment cells, source links, and partitions are
    intentionally outside this function.  A syntactically valid row is not an
    authenticated legal rule.
    """

    row = _exact_keys(row, RULE_ROW_KEYS, "legal rule row")
    rule_id = _nonnull_string(row["rule_id"], "rule_id")
    family = row["status_family"]
    if family not in FAMILY_SPECS:
        raise _fail(rule_id, "unknown status_family")
    claim_id, verification_class, family_start, family_end = FAMILY_SPECS[
        family
    ]
    if row["verification_class"] != verification_class:
        raise _fail(rule_id, "verification class disagrees with family law")
    expected_claim_ids = [] if claim_id is None else [claim_id]
    if row["verification_claim_ids"] != expected_claim_ids:
        raise _fail(rule_id, "verification claim projection drift")
    effective_start = _json_integer(
        row["effective_start"], f"{rule_id}.effective_start"
    )
    effective_end = _json_integer(
        row["effective_end"], f"{rule_id}.effective_end"
    )
    if not family_start <= effective_start < effective_end <= family_end:
        raise _fail(rule_id, "invalid half-open effective interval")
    jurisdiction = _nonnull_string(
        row["jurisdiction"], f"{rule_id}.jurisdiction"
    )
    if family == "section_218_and_mandatory_state_local":
        if jurisdiction not in STATE_LOCAL_JURISDICTIONS:
            raise _fail(
                rule_id, "jurisdiction is outside the state/local domain"
            )
    elif jurisdiction != "federal":
        raise _fail(rule_id, "federal-only family has nonfederal jurisdiction")
    _nonnull_string(row["reason_code"], f"{rule_id}.reason_code")
    affected_inventory_keys = _unique_strings(
        row["affected_inventory_keys"], f"{rule_id}.affected_inventory_keys"
    )
    if any(
        _SOURCE_INVENTORY_KEY.fullmatch(source_key) is None
        for source_key in affected_inventory_keys
    ):
        raise _fail(
            rule_id, "affected_inventory_keys contains a malformed key"
        )
    _validate_optional_consequences(row, affected_inventory_keys)
    authority_status = row["authority_status"]
    if authority_status not in {
        "verified",
        "authority_absent",
        "authority_conflict",
    }:
        raise _fail(rule_id, "unknown authority_status")
    if authority_status != "verified":
        if verification_class != "direct_only_optional":
            raise _fail(rule_id, "registration_required row must be verified")
        if not affected_inventory_keys:
            raise _fail(
                rule_id, "negative optional row requires a nonempty key domain"
            )
        expected_nulls = (
            "authority_rank",
            "source_document_id",
            "source_sha256",
            "exact_citation",
            "transform",
            "unresolved_action",
        )
        if any(row[key] is not None for key in expected_nulls):
            raise _fail(rule_id, "negative row populated an authority field")
        for key in ("covered_facts", "excluded_facts", "required_micro_facts"):
            if row[key] != []:
                raise _fail(rule_id, "negative row populated fact fields")
        return
    authority_rank = _json_integer(
        row["authority_rank"], f"{rule_id}.authority_rank"
    )
    if authority_rank not in {1, 2}:
        raise _fail(rule_id, "authority rank must be 1 or 2")
    source_sha256 = row["source_sha256"]
    if (
        not isinstance(source_sha256, str)
        or _HEX64.fullmatch(source_sha256) is None
    ):
        raise _fail(rule_id, "invalid source SHA-256")
    if row["source_document_id"] != f"legal-source:{source_sha256}":
        raise _fail(
            rule_id, "primary source identity does not match source SHA-256"
        )
    _nonnull_string(row["exact_citation"], f"{rule_id}.exact_citation")
    if row["unresolved_action"] not in {"modelable", "unresolved"}:
        raise _fail(rule_id, "invalid runtime missing-microfact action")
    covered_facts = row["covered_facts"]
    excluded_facts = row["excluded_facts"]
    if not isinstance(covered_facts, list) or not isinstance(
        excluded_facts, list
    ):
        raise _fail(rule_id, "fact bindings must be arrays")
    global_ids = (
        global_micro_fact_ids if global_micro_fact_ids is not None else set()
    )
    derived_required: list[Mapping[str, Any]] = []
    binding_ids: list[str] = []
    joint_binding_signatures: set[bytes] = set()
    affected_key_domain = frozenset(affected_inventory_keys)
    allowed_field_purposes = frozenset(FAMILY_FIELD_PURPOSES[family])
    for kind, bindings in (
        ("covered", covered_facts),
        ("excluded", excluded_facts),
    ):
        for index, binding in enumerate(bindings, start=1):
            binding_id = f"{rule_id}:{kind}:{index}"
            slots, joint_signature = _validate_fact_binding(
                binding,
                expected_id=binding_id,
                global_micro_fact_ids=global_ids,
                affected_inventory_keys=affected_key_domain,
                allowed_field_purposes=allowed_field_purposes,
                label=f"{rule_id}.{kind}_facts[{index - 1}]",
            )
            if joint_signature in joint_binding_signatures:
                raise _fail(
                    rule_id, "duplicate normalized fact-binding semantics"
                )
            joint_binding_signatures.add(joint_signature)
            derived_required.extend(slots)
            binding_ids.append(binding_id)
    if row["required_micro_facts"] != derived_required:
        raise _fail(
            rule_id, "required_micro_facts is not the exact derived array"
        )
    binding_signatures = {
        binding_id: ("boolean", None, False) for binding_id in binding_ids
    }
    used_bindings: set[str] = set()
    transform_signature = _infer_ast(
        row["transform"],
        allowed_leaf_op="fact_binding",
        leaf_signatures=binding_signatures,
        used_leaves=used_bindings,
        allowed_operators=frozenset(_TRANSFORM_OPERATORS),
        label=f"{rule_id}.transform",
    )
    if transform_signature != ("enum", None, False):
        raise _fail(rule_id, "transform must return a nonnull enum/null-unit")
    if used_bindings != set(binding_ids):
        raise _fail(rule_id, "transform must use every and only bound fact")
    vectors = itertools.product((False, True), repeat=len(binding_ids))
    results = {
        _eval_ast(
            row["transform"], dict(zip(binding_ids, vector, strict=True))
        )
        for vector in vectors
    }
    if not results or not results.issubset(_CLASSIFIED_STATUSES):
        raise _fail(
            rule_id, "transform returned an unregistered classification"
        )
    if binding_ids and len(results) < 2:
        raise _fail(rule_id, "fact-bearing transform is semantically constant")


def _normalized_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Remove authored identity spelling while retaining complete semantics."""

    normalized = copy.deepcopy(dict(row))
    micro_fact_ids: dict[str, str] = {}
    fact_binding_ids: dict[str, str] = {}
    for kind in ("covered", "excluded"):
        for binding_position, binding in enumerate(
            normalized[f"{kind}_facts"], start=1
        ):
            original_binding_id = binding["fact_binding_id"]
            canonical_binding_id = f"binding:{kind}:{binding_position}"
            fact_binding_ids[original_binding_id] = canonical_binding_id
            binding["fact_binding_id"] = canonical_binding_id
            binding_micro_fact_ids: dict[str, str] = {}
            for slot_position, slot in enumerate(
                binding["micro_fact_slots"], start=1
            ):
                original_micro_fact_id = slot["micro_fact_id"]
                canonical_micro_fact_id = (
                    f"micro:{kind}:{binding_position}:{slot_position}"
                )
                micro_fact_ids[original_micro_fact_id] = (
                    canonical_micro_fact_id
                )
                micro_fact_ids[canonical_micro_fact_id] = (
                    canonical_micro_fact_id
                )
                binding_micro_fact_ids[original_micro_fact_id] = (
                    canonical_micro_fact_id
                )
                slot["micro_fact_id"] = canonical_micro_fact_id
            binding["premise_ast"] = _normalized_ast_leaf_references(
                binding["premise_ast"],
                leaf_op="micro_fact",
                replacements=binding_micro_fact_ids,
                replacement_op="micro_fact",
                replacement_id_key="micro_fact_id",
            )
    for slot in normalized["required_micro_facts"]:
        slot["micro_fact_id"] = micro_fact_ids[slot["micro_fact_id"]]
    if normalized["transform"] is not None:
        normalized["transform"] = _normalized_ast_leaf_references(
            normalized["transform"],
            leaf_op="fact_binding",
            replacements=fact_binding_ids,
            replacement_op="fact_binding",
            replacement_id_key="fact_binding_id",
        )
    for position, consequence in enumerate(
        normalized["optional_row_consequences"], start=1
    ):
        consequence["optional_consequence_id"] = f"optional:{position}"
    normalized.pop("rule_id")
    return normalized


def _verified_duplicate_signature(row: Mapping[str, Any]) -> bytes | None:
    """Return the row-local portion of §19's establishing duplicate test."""

    if row["authority_status"] != "verified":
        return None
    normalized = _normalized_row(row)
    fields = (
        "source_document_id",
        "source_sha256",
        "authority_rank",
        "status_family",
        "jurisdiction",
        "effective_start",
        "effective_end",
        "covered_facts",
        "excluded_facts",
        "affected_inventory_keys",
        "transform",
    )
    return _semantic_bytes([normalized[field] for field in fields])


def validate_rule_rows_syntax(rows: Any) -> None:
    """Validate canonical rule ordering, IDs, and row-local semantics."""

    if not isinstance(rows, list) or not rows:
        raise _fail("rows", "must be a nonempty array")
    rule_ids: list[str] = []
    global_micro_fact_ids: set[str] = set()
    for row in rows:
        validate_rule_row_syntax(
            row, global_micro_fact_ids=global_micro_fact_ids
        )
        rule_ids.append(row["rule_id"])
    if len(rule_ids) != len(set(rule_ids)):
        raise _fail("rows", "duplicate rule_id")
    if rule_ids != sorted(rule_ids, key=lambda value: value.encode("utf-8")):
        raise _fail("rows", "rule IDs are not in unsigned UTF-8 byte order")
    duplicate_signatures: set[bytes] = set()
    fragmentation_groups: dict[bytes, list[tuple[int, int]]] = {}
    for row in rows:
        duplicate_signature = _verified_duplicate_signature(row)
        if duplicate_signature is not None:
            if duplicate_signature in duplicate_signatures:
                raise _fail("rows", "duplicate verified rule semantics")
            duplicate_signatures.add(duplicate_signature)
        normalized = _normalized_row(row)
        effective_start = normalized.pop("effective_start")
        effective_end = normalized.pop("effective_end")
        fragmentation_groups.setdefault(
            _semantic_bytes(normalized), []
        ).append((effective_start, effective_end))
    for intervals in fragmentation_groups.values():
        intervals.sort()
        if any(
            previous_end == current_start
            for (_, previous_end), (current_start, _) in zip(
                intervals, intervals[1:], strict=False
            )
        ):
            raise _fail(
                "rows", "adjacent operatively identical rules must be merged"
            )


def derive_controlling_result(results: Any) -> dict[str, Any]:
    """Apply the row-result fold, without claiming §19 partition coverage.

    In particular, this primitive may return rank 2.  The unavailable
    inventory-derived partition validator must separately require complete
    verified dispositive rank-1 coverage for registration-required cells.
    """

    if not isinstance(results, list):
        raise _fail("authority results", "expected an array")
    required_keys = (
        "rule_id",
        "status_family",
        "authority_rank",
        "classified_status",
        "reason_code",
    )
    dispositive: list[Mapping[str, Any]] = []
    seen_rule_ids: set[str] = set()
    for index, result in enumerate(results):
        label = f"authority results[{index}]"
        result = _exact_keys(result, required_keys, label)
        rule_id = _nonnull_string(result["rule_id"], f"{label}.rule_id")
        if rule_id in seen_rule_ids:
            raise _fail(label, "duplicate rule result")
        seen_rule_ids.add(rule_id)
        if result["status_family"] not in FAMILY_SPECS:
            raise _fail(label, "unknown status family")
        rank = _json_integer(
            result["authority_rank"], f"{label}.authority_rank"
        )
        if rank not in {1, 2}:
            raise _fail(label, "authority rank must be 1 or 2")
        if result["classified_status"] not in _CLASSIFIED_STATUSES:
            raise _fail(label, "unknown classified status")
        _nonnull_string(result["reason_code"], f"{label}.reason_code")
        if result["classified_status"] != "no_disposition":
            dispositive.append(result)
    if not dispositive:
        raise _fail("authority results", "no dispositive result")
    controlling_rank = min(result["authority_rank"] for result in dispositive)
    controlling = [
        result
        for result in dispositive
        if result["authority_rank"] == controlling_rank
    ]
    controlling_statuses = {
        result["classified_status"] for result in controlling
    }
    if len(controlling_statuses) != 1:
        raise _fail("authority results", "same-rank dispositive conflict")
    classified_status = next(iter(controlling_statuses))
    if any(
        result["classified_status"] != classified_status
        for result in dispositive
        if result["authority_rank"] > controlling_rank
    ):
        raise _fail(
            "authority results", "lower-rank dispositive contradiction"
        )
    controlling = sorted(
        controlling, key=lambda result: result["rule_id"].encode("utf-8")
    )
    return {
        "authority_rank": controlling_rank,
        "classified_status": classified_status,
        "controlling_rule_ids": [result["rule_id"] for result in controlling],
        "reason_codes": [result["reason_code"] for result in controlling],
    }


__all__ = [
    "FACT_BINDING_KEYS",
    "FAMILY_FIELD_PURPOSES",
    "FAMILY_SPECS",
    "FIELD_PURPOSES",
    "LegalRuleValidationError",
    "MICRO_FACT_SLOT_KEYS",
    "OPTIONAL_CONSEQUENCE_KEYS",
    "RULE_ROW_KEYS",
    "SOURCE_FIELD_REF_KEYS",
    "STATE_LOCAL_JURISDICTIONS",
    "derive_controlling_result",
    "validate_rule_row_syntax",
    "validate_rule_rows_syntax",
]
