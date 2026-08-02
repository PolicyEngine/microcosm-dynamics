"""Unit tests for the source-independent historical legal-rule row law."""

from __future__ import annotations

import copy
import json

import pytest

from populace_dynamics.data import historical_coverage_rule_validation as rules

SECA_KEY = f"psid-slot:{'a' * 64}"
STUDENT_KEY = f"psid-slot:{'b' * 64}"
OTHER_KEY = f"psid-slot:{'c' * 64}"


def _literal(value: str) -> dict:
    return {
        "op": "literal",
        "value": value,
        "value_type": "enum",
        "unit": None,
    }


def _unconditional_rule(
    *,
    rule_id: str = "seca-1968-1990",
    effective_start: int = 1968,
    effective_end: int = 1990,
) -> dict:
    source_sha256 = "a" * 64
    return {
        "rule_id": rule_id,
        "authority_status": "verified",
        "status_family": "historical_seca",
        "effective_start": effective_start,
        "effective_end": effective_end,
        "jurisdiction": "federal",
        "authority_rank": 1,
        "source_document_id": f"legal-source:{source_sha256}",
        "source_sha256": source_sha256,
        "exact_citation": "PDF p. 1: exact source span",
        "covered_facts": [],
        "excluded_facts": [],
        "required_micro_facts": [],
        "transform": _literal("covered_self_employment"),
        "reason_code": "historical_seca_eligible_concept_v1",
        "unresolved_action": "unresolved",
        "verification_class": "registration_required",
        "verification_claim_ids": ["V-B4"],
        "affected_inventory_keys": [SECA_KEY],
        "optional_row_consequences": [],
    }


def _fact_bearing_student_rule() -> dict:
    rule_id = "student-nexus-rule"
    source_sha256 = "b" * 64
    slot = {
        "micro_fact_id": "student-nexus-fact",
        "field_purpose": "employer_school_nexus",
        "source_field_ref": {
            "source_inventory_key": STUDENT_KEY,
            "raw_field_id": "ER_STUDENT",
        },
        "typed_value_type": "enum",
        "typed_value_unit": None,
        "presence_predicate_ast": {
            "op": "typed_nonmissing",
            "source_field_ref": "self",
        },
        "missing_reason_code": "student_nexus_missing",
    }
    binding_id = f"{rule_id}:covered:1"
    binding = {
        "fact_binding_id": binding_id,
        "premise_ast": {
            "op": "equal",
            "args": [
                {"op": "micro_fact", "micro_fact_id": "student-nexus-fact"},
                _literal("school_is_employer"),
            ],
        },
        "micro_fact_slots": [slot],
    }
    return {
        "rule_id": rule_id,
        "authority_status": "verified",
        "status_family": "student_service",
        "effective_start": 1968,
        "effective_end": 2023,
        "jurisdiction": "federal",
        "authority_rank": 1,
        "source_document_id": f"legal-source:{source_sha256}",
        "source_sha256": source_sha256,
        "exact_citation": "PDF p. 2: exact student-service span",
        "covered_facts": [binding],
        "excluded_facts": [],
        "required_micro_facts": [copy.deepcopy(slot)],
        "transform": {
            "op": "case",
            "args": [
                {"op": "fact_binding", "fact_binding_id": binding_id},
                _literal("noncovered"),
                _literal("no_disposition"),
            ],
        },
        "reason_code": "student_service_employer_nexus_v1",
        "unresolved_action": "unresolved",
        "verification_class": "direct_only_optional",
        "verification_claim_ids": ["V-B9"],
        "affected_inventory_keys": [STUDENT_KEY],
        "optional_row_consequences": [
            {
                "optional_consequence_id": f"{rule_id}:{STUDENT_KEY}",
                "source_inventory_key": STUDENT_KEY,
                "consequence": "unresolved",
                "reason_code": "student_direct_authority_unavailable",
            }
        ],
    }


def _negative_student_rule() -> dict:
    row = _fact_bearing_student_rule()
    row.update(
        {
            "authority_status": "authority_absent",
            "authority_rank": None,
            "source_document_id": None,
            "source_sha256": None,
            "exact_citation": None,
            "covered_facts": [],
            "excluded_facts": [],
            "required_micro_facts": [],
            "transform": None,
            "unresolved_action": None,
        }
    )
    return row


def _retag_student_rule(
    row: dict,
    *,
    rule_id: str,
    micro_fact_id: str | None = None,
) -> dict:
    """Change only authored IDs, preserving the row's normalized semantics."""

    row = copy.deepcopy(row)
    old_rule_id = row["rule_id"]
    binding = row["covered_facts"][0]
    old_binding_id = binding["fact_binding_id"]
    new_binding_id = f"{rule_id}:covered:1"
    slot = binding["micro_fact_slots"][0]
    old_micro_fact_id = slot["micro_fact_id"]
    new_micro_fact_id = micro_fact_id or f"{rule_id}-microfact"
    row["rule_id"] = rule_id
    binding["fact_binding_id"] = new_binding_id
    binding["premise_ast"]["args"][0]["micro_fact_id"] = new_micro_fact_id
    slot["micro_fact_id"] = new_micro_fact_id
    row["required_micro_facts"][0]["micro_fact_id"] = new_micro_fact_id
    row["transform"]["args"][0]["fact_binding_id"] = new_binding_id
    for consequence in row["optional_row_consequences"]:
        assert consequence["optional_consequence_id"].startswith(
            f"{old_rule_id}:"
        )
        consequence["optional_consequence_id"] = (
            f"{rule_id}:{consequence['source_inventory_key']}"
        )
    assert old_binding_id != new_binding_id
    assert old_micro_fact_id != new_micro_fact_id or micro_fact_id is not None
    return row


def test_unconditional_and_fact_bearing_rows_pass_closed_syntax():
    rules.validate_rule_row_syntax(_unconditional_rule())
    rules.validate_rule_row_syntax(_fact_bearing_student_rule())
    rules.validate_rule_row_syntax(_negative_student_rule())


def test_structural_missing_and_conflict_branches_are_representable():
    structural = _fact_bearing_student_rule()
    slot = structural["covered_facts"][0]["micro_fact_slots"][0]
    slot["source_field_ref"]["raw_field_id"] = None
    slot["presence_predicate_ast"] = {"op": "literal_false"}
    structural["required_micro_facts"][0] = copy.deepcopy(slot)
    rules.validate_rule_row_syntax(structural)

    conflict = _negative_student_rule()
    conflict["authority_status"] = "authority_conflict"
    rules.validate_rule_row_syntax(conflict)


def test_state_local_jurisdiction_uses_only_the_frozen_51_id_domain():
    row = _unconditional_rule(effective_end=2023)
    row["status_family"] = "section_218_and_mandatory_state_local"
    row["verification_claim_ids"] = ["V-B1"]
    row["jurisdiction"] = "inventory-state:psid-01"
    rules.validate_rule_row_syntax(row)
    row["jurisdiction"] = "inventory-state:psid-52"
    with pytest.raises(
        rules.LegalRuleValidationError, match="state/local domain"
    ):
        rules.validate_rule_row_syntax(row)


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("extra_key", "keyset drift"),
        ("boolean_endpoint", "JSON integer"),
        ("inclusive_end", "half-open effective interval"),
        ("wrong_claim", "claim projection drift"),
        ("wrong_source_id", "primary source identity"),
        ("required_facts", "exact derived array"),
        ("constant_transform", "semantically constant"),
        ("unused_microfact", "every and only declared microfact"),
        ("presence_default", "presence predicate"),
        ("optional_key_order", "source key order"),
        ("cross_affected_key", "outside the affected domain"),
        ("malformed_inventory_key", "malformed key"),
        ("nonfederal_jurisdiction", "nonfederal jurisdiction"),
        ("off_family_purpose", "outside the family domain"),
        ("multiply_arity", "multiply requires two operands"),
    ],
)
def test_coherent_row_mutations_fail_closed(mutation: str, match: str):
    row = _fact_bearing_student_rule()
    if mutation == "extra_key":
        row["callback"] = "forbidden"
    elif mutation == "boolean_endpoint":
        row["effective_start"] = True
    elif mutation == "inclusive_end":
        row["effective_end"] = 2024
    elif mutation == "wrong_claim":
        row["verification_claim_ids"] = ["V-B1"]
    elif mutation == "wrong_source_id":
        row["source_document_id"] = f"legal-source:{'c' * 64}"
    elif mutation == "required_facts":
        row["required_micro_facts"] = []
    elif mutation == "constant_transform":
        row["transform"] = {
            "op": "case",
            "args": [
                {
                    "op": "fact_binding",
                    "fact_binding_id": "student-nexus-rule:covered:1",
                },
                _literal("noncovered"),
                _literal("noncovered"),
            ],
        }
    elif mutation == "unused_microfact":
        first_slot = row["covered_facts"][0]["micro_fact_slots"][0]
        second_slot = copy.deepcopy(first_slot)
        second_slot["micro_fact_id"] = "student-nexus-fact-unused"
        row["covered_facts"][0]["micro_fact_slots"].append(second_slot)
        row["required_micro_facts"].append(copy.deepcopy(second_slot))
    elif mutation == "presence_default":
        row["covered_facts"][0]["micro_fact_slots"][0][
            "presence_predicate_ast"
        ] = {"op": "literal_true"}
    elif mutation == "optional_key_order":
        row["optional_row_consequences"][0]["source_inventory_key"] = OTHER_KEY
    elif mutation == "cross_affected_key":
        row["covered_facts"][0]["micro_fact_slots"][0]["source_field_ref"][
            "source_inventory_key"
        ] = OTHER_KEY
    elif mutation == "malformed_inventory_key":
        row["affected_inventory_keys"] = ["psid-slot:not-a-digest"]
        row["covered_facts"][0]["micro_fact_slots"][0]["source_field_ref"][
            "source_inventory_key"
        ] = "psid-slot:not-a-digest"
        row["required_micro_facts"][0]["source_field_ref"][
            "source_inventory_key"
        ] = "psid-slot:not-a-digest"
        row["optional_row_consequences"][0][
            "source_inventory_key"
        ] = "psid-slot:not-a-digest"
        row["optional_row_consequences"][0][
            "optional_consequence_id"
        ] = "student-nexus-rule:psid-slot:not-a-digest"
    elif mutation == "nonfederal_jurisdiction":
        row["jurisdiction"] = "inventory-state:psid-01"
    elif mutation == "off_family_purpose":
        row["covered_facts"][0]["micro_fact_slots"][0][
            "field_purpose"
        ] = "railroad_covered_service"
        row["required_micro_facts"][0][
            "field_purpose"
        ] = "railroad_covered_service"
    elif mutation == "multiply_arity":
        binding_id = "student-nexus-rule:covered:1"
        row["transform"] = {
            "op": "case",
            "args": [
                {
                    "op": "and",
                    "args": [
                        {"op": "fact_binding", "fact_binding_id": binding_id},
                        {
                            "op": "equal",
                            "args": [
                                {
                                    "op": "multiply",
                                    "args": [
                                        {
                                            "op": "rational",
                                            "numerator": 1,
                                            "denominator": 1,
                                            "unit": "dimensionless",
                                        },
                                        {
                                            "op": "rational",
                                            "numerator": 1,
                                            "denominator": 1,
                                            "unit": "usd",
                                        },
                                        {
                                            "op": "rational",
                                            "numerator": 1,
                                            "denominator": 1,
                                            "unit": "dimensionless",
                                        },
                                    ],
                                },
                                {
                                    "op": "rational",
                                    "numerator": 1,
                                    "denominator": 1,
                                    "unit": "usd",
                                },
                            ],
                        },
                    ],
                },
                _literal("noncovered"),
                _literal("no_disposition"),
            ],
        }
    with pytest.raises(rules.LegalRuleValidationError, match=match):
        rules.validate_rule_row_syntax(row)


def test_registration_required_negative_row_is_unrepresentable():
    row = _unconditional_rule()
    row.update(
        {
            "authority_status": "authority_absent",
            "authority_rank": None,
            "source_document_id": None,
            "source_sha256": None,
            "exact_citation": None,
            "transform": None,
            "unresolved_action": None,
        }
    )
    with pytest.raises(
        rules.LegalRuleValidationError,
        match="registration_required row must be verified",
    ):
        rules.validate_rule_row_syntax(row)


def test_duplicate_normalized_bindings_abort_despite_distinct_authored_ids():
    row = _fact_bearing_student_rule()
    first = row["covered_facts"][0]
    second = copy.deepcopy(first)
    second["fact_binding_id"] = "student-nexus-rule:covered:2"
    second_slot = second["micro_fact_slots"][0]
    second_slot["micro_fact_id"] = "student-nexus-fact-copy"
    second["premise_ast"]["args"][0][
        "micro_fact_id"
    ] = "student-nexus-fact-copy"
    row["covered_facts"].append(second)
    row["required_micro_facts"].append(copy.deepcopy(second_slot))
    row["transform"]["args"][0] = {
        "op": "and",
        "args": [
            {
                "op": "fact_binding",
                "fact_binding_id": "student-nexus-rule:covered:1",
            },
            {
                "op": "fact_binding",
                "fact_binding_id": "student-nexus-rule:covered:2",
            },
        ],
    }
    with pytest.raises(
        rules.LegalRuleValidationError,
        match="duplicate normalized fact-binding semantics",
    ):
        rules.validate_rule_row_syntax(row)


def test_micro_fact_ids_are_globally_unique_across_rule_rows():
    first = _retag_student_rule(
        _fact_bearing_student_rule(),
        rule_id="student-a",
        micro_fact_id="shared-microfact",
    )
    second = _retag_student_rule(
        _fact_bearing_student_rule(),
        rule_id="student-b",
        micro_fact_id="shared-microfact",
    )
    with pytest.raises(
        rules.LegalRuleValidationError, match="globally unique"
    ):
        rules.validate_rule_rows_syntax([first, second])


def test_row_array_rejects_order_and_artificial_fragmentation():
    first = _unconditional_rule(
        rule_id="seca-a", effective_start=1968, effective_end=1979
    )
    second = _unconditional_rule(
        rule_id="seca-b", effective_start=1979, effective_end=1990
    )
    with pytest.raises(
        rules.LegalRuleValidationError,
        match="operatively identical rules must be merged",
    ):
        rules.validate_rule_rows_syntax([first, second])
    with pytest.raises(
        rules.LegalRuleValidationError,
        match="unsigned UTF-8 byte order",
    ):
        rules.validate_rule_rows_syntax([second, first])


def test_exact_duplicate_semantics_abort_with_distinct_rule_ids():
    first = _unconditional_rule(rule_id="seca-a")
    second = _unconditional_rule(rule_id="seca-b")
    with pytest.raises(
        rules.LegalRuleValidationError,
        match="duplicate verified rule semantics",
    ):
        rules.validate_rule_rows_syntax([first, second])


def test_nonconsecutive_and_fact_bearing_fragments_cannot_escape_merge_law():
    first = _retag_student_rule(
        _fact_bearing_student_rule(), rule_id="student-a"
    )
    first["effective_end"] = 1980
    unrelated = _retag_student_rule(
        _fact_bearing_student_rule(), rule_id="student-middle"
    )
    unrelated["source_sha256"] = "c" * 64
    unrelated["source_document_id"] = f"legal-source:{'c' * 64}"
    last = _retag_student_rule(
        _fact_bearing_student_rule(), rule_id="student-z"
    )
    last["effective_start"] = 1980
    with pytest.raises(
        rules.LegalRuleValidationError,
        match="operatively identical rules must be merged",
    ):
        rules.validate_rule_rows_syntax([first, unrelated, last])


def test_colliding_authored_micro_fact_id_cannot_hide_adjacent_fragmentation():
    def two_slot_rule(
        *,
        rule_id: str,
        effective_start: int,
        effective_end: int,
        first_micro_fact_id: str,
        second_micro_fact_id: str,
    ) -> dict:
        row = _retag_student_rule(
            _fact_bearing_student_rule(),
            rule_id=rule_id,
            micro_fact_id=first_micro_fact_id,
        )
        row["effective_start"] = effective_start
        row["effective_end"] = effective_end
        binding = row["covered_facts"][0]
        first_slot = binding["micro_fact_slots"][0]
        second_slot = copy.deepcopy(first_slot)
        second_slot["micro_fact_id"] = second_micro_fact_id
        binding["micro_fact_slots"].append(second_slot)
        row["required_micro_facts"].append(copy.deepcopy(second_slot))
        binding["premise_ast"] = {
            "op": "and",
            "args": [
                {
                    "op": "equal",
                    "args": [
                        {
                            "op": "micro_fact",
                            "micro_fact_id": first_micro_fact_id,
                        },
                        _literal("school_is_employer"),
                    ],
                },
                {
                    "op": "equal",
                    "args": [
                        {
                            "op": "micro_fact",
                            "micro_fact_id": second_micro_fact_id,
                        },
                        _literal("school_is_employer"),
                    ],
                },
            ],
        }
        return row

    first = two_slot_rule(
        rule_id="student-a",
        effective_start=1968,
        effective_end=1980,
        first_micro_fact_id="micro:covered:1:2",
        second_micro_fact_id="student-a-second-fact",
    )
    second = two_slot_rule(
        rule_id="student-b",
        effective_start=1980,
        effective_end=2023,
        first_micro_fact_id="student-b-first-fact",
        second_micro_fact_id="student-b-second-fact",
    )
    first, second = json.loads(json.dumps([first, second]))

    with pytest.raises(
        rules.LegalRuleValidationError,
        match="adjacent operatively identical rules must be merged",
    ):
        rules.validate_rule_rows_syntax([first, second])


def _result(
    rule_id: str,
    rank: int,
    status: str,
    *,
    reason: str | None = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "status_family": "historical_seca",
        "authority_rank": rank,
        "classified_status": status,
        "reason_code": reason or f"{rule_id}-reason",
    }


def test_authority_precedence_preserves_all_controlling_provenance():
    controlling = rules.derive_controlling_result(
        [
            _result("rank2", 2, "covered_self_employment"),
            _result("rank1-b", 1, "covered_self_employment"),
            _result("rank1-a", 1, "covered_self_employment"),
            _result("neutral", 1, "no_disposition"),
        ]
    )
    assert controlling == {
        "authority_rank": 1,
        "classified_status": "covered_self_employment",
        "controlling_rule_ids": ["rank1-a", "rank1-b"],
        "reason_codes": ["rank1-a-reason", "rank1-b-reason"],
    }


def test_controlling_primitive_does_not_pretend_to_validate_a_partition():
    """Rank 2 can control this fold but cannot satisfy §19 rank-1 coverage."""

    assert (
        rules.derive_controlling_result(
            [_result("rank2", 2, "covered_self_employment")]
        )["authority_rank"]
        == 2
    )


@pytest.mark.parametrize(
    ("results", "match"),
    [
        (
            [
                _result("a", 1, "covered_self_employment"),
                _result("b", 1, "noncovered"),
            ],
            "same-rank",
        ),
        (
            [
                _result("a", 1, "covered_self_employment"),
                _result("b", 2, "noncovered"),
            ],
            "lower-rank",
        ),
        ([_result("a", 1, "no_disposition")], "no dispositive"),
    ],
)
def test_authority_conflicts_and_empty_disposition_abort(results, match):
    with pytest.raises(rules.LegalRuleValidationError, match=match):
        rules.derive_controlling_result(results)
