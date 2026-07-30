"""Source-reproduction tests for entry-11 identity evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SOURCE = (
    ROOT
    / "data"
    / "external"
    / "snapshots"
    / "ssa_level_anchors_vintage1"
    / "supplement2025_4b.html"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_covered_earnings_source_identity_evidence as builder  # noqa: E402
import covered_earnings_correction_registry as registry  # noqa: E402


@pytest.fixture(scope="module")
def evidence() -> dict:
    return builder.build()


def test__identity_evidence__does_not_mint_vintage2_authority(evidence):
    assert evidence["schema_version"] == (
        "covered_earnings_source_identity_evidence.v1"
    )
    assert evidence["authority"] == {
        "status": "non_authoritative_source_identity_evidence_only",
        "final_registry_registration": "aborted",
        "artifact_vintage_identity_assigned": False,
        "physical_cell_id_namespace": (
            "covered_earnings_source_evidence_occurrence.v1"
        ),
        "physical_cell_id_namespace_status": "non_authoritative",
        "physical_cell_id_namespace_adjudication": (
            "the final physical-ID occurrence law is under-specified; "
            "evidence IDs distinguish the committed vintage-1 and entry-11 "
            "re-extraction occurrences while structural locators carry the "
            "design-specified stable identity"
        ),
    }
    assert evidence["source_verification"]["network_capture"] is False
    assert evidence["source_verification"]["vintage1_reproduction"] == (
        "exact_byte_equality_pass"
    )


def test__physical_evidence__has_all_945_exact_12_field_rows(evidence):
    rows = evidence["physical_source_cell_evidence"]
    assert evidence["physical_source_cell_evidence_schema_version"] == (
        "physical_source_cell_evidence.v1"
    )
    assert len(rows) == 120 + 825 == 945
    assert all(
        set(row) == set(builder.PHYSICAL_SOURCE_CELL_EVIDENCE_FIELDS)
        for row in rows
    )
    assert len({row["physical_cell_id"] for row in rows}) == 945
    assert len({row["structural_locator_id"] for row in rows}) == 921
    assert all(
        len(row[field]) == 64
        for row in rows
        for field in (
            "structural_locator_id",
            "as_published_token_sha256",
            "normalized_semantic_sha256",
            "full_source_sha256",
        )
    )


def test__physical_evidence__hashes_the_design_locator_tuple(evidence):
    for row in evidence["physical_source_cell_evidence"]:
        preimage = [
            row["publication_family_id"],
            row["edition_id"],
            row["source_document_id"],
            row["table_id"],
            row["row_path"],
            row["nested_column_header_path"],
            row["calendar_year"],
        ]
        assert (
            row["structural_locator_id"]
            == hashlib.sha256(
                builder.canonical_json_bytes(preimage)
            ).hexdigest()
        )


def test__alias_evidence__has_complete_proven_relation_counts(evidence):
    rows = evidence["official_source_alias_evidence"]
    assert evidence["official_source_alias_evidence_schema_version"] == (
        "official_source_alias_evidence.v1"
    )
    assert len(rows) == 873
    assert all(
        set(row) == set(builder.OFFICIAL_SOURCE_ALIAS_EVIDENCE_FIELDS)
        for row in rows
    )
    assert Counter(row["relation"] for row in rows) == {
        "same_physical_cell": 24,
        "cross_vintage_republication": 24,
        "shared_primitive": 220,
        "structural_formula_sibling": 605,
    }
    assert not any(
        row["relation"] == "exact_arithmetic_sibling" for row in rows
    )


def test__cross_vintage_evidence__uses_vintage1_and_reextraction_endpoints(
    evidence,
):
    physical = {
        row["physical_cell_id"]: row
        for row in evidence["physical_source_cell_evidence"]
    }
    rows = [
        row
        for row in evidence["official_source_alias_evidence"]
        if row["relation"]
        in {"same_physical_cell", "cross_vintage_republication"}
    ]
    assert len(rows) == 48
    assert {row["effective_calendar_year"] for row in rows} == set(
        range(2015, 2023)
    )
    for row in rows:
        assert ":committed_vintage1:" in row["left_physical_cell_id"]
        assert ":entry11_source_reextraction:" in (
            row["right_physical_cell_id"]
        )
        left = physical[row["left_physical_cell_id"]]
        right = physical[row["right_physical_cell_id"]]
        assert {
            field: left[field]
            for field in (
                "structural_locator_id",
                "as_published_token_sha256",
                "normalized_semantic_sha256",
                "full_source_sha256",
            )
        } == {
            field: right[field]
            for field in (
                "structural_locator_id",
                "as_published_token_sha256",
                "normalized_semantic_sha256",
                "full_source_sha256",
            )
        }


def test__arithmetic_evidence__is_complete_and_structural_only(evidence):
    rows = evidence["official_source_arithmetic_rule_evidence"]
    assert (
        evidence["official_source_arithmetic_rule_evidence_schema_version"]
        == "official_source_arithmetic_rule_evidence.v1"
    )
    assert len(rows) == 275
    assert all(
        set(row)
        == set(builder.OFFICIAL_SOURCE_ARITHMETIC_RULE_EVIDENCE_FIELDS)
        for row in rows
    )
    assert Counter(row["relation_class"] for row in rows) == {
        "worker_membership": 55,
        "total_component": 110,
        "taxable_earnings_gross_contribution": 110,
    }
    assert {
        (
            row["assertion_scope"],
            row["numeric_validation_law"],
            row["formula_ast"],
        )
        for row in rows
    } == {
        (
            "structural_dependence_only",
            "not_applicable_no_published_numeric_assertion",
            None,
        )
    }
    assert evidence["adjudication"]["exact_arithmetic_rule_count"] == 0
    assert (
        evidence["adjudication"]["exact_arithmetic_sibling_alias_count"] == 0
    )


def test__definition_hashes__bind_exact_verified_raw_html_cells(evidence):
    source = SOURCE.read_bytes()
    rows = evidence["source_definition_fragments"]
    assert len(rows) == 5
    assert len({row["source_definition_locator_id"] for row in rows}) == 5
    for row in rows:
        fragments = [
            value.encode("utf-8") for value in row["exact_raw_html_cells_utf8"]
        ]
        assert all(fragment in source for fragment in fragments)
        assert (
            row["source_definition_fragment_sha256"]
            == hashlib.sha256(b"\x00".join(fragments)).hexdigest()
        )
        assert all(
            not coordinate.rsplit("[", 1)[-1].startswith("20")
            for coordinate in row["citation_coordinates"]
        )


def test__identity_validator__reresolves_every_row_from_sources(evidence):
    builder.validate_evidence(copy.deepcopy(evidence))


def test__identity_evidence__has_no_authoritative_registry_api(evidence):
    assert not hasattr(registry, "source_identity_evidence")
    assert not hasattr(registry, "validate_source_identity_evidence")
    assert "source_identity_evidence" not in registry.__all__
    assert "validate_source_identity_evidence" not in registry.__all__
    assert (
        evidence["physical_source_cell_evidence_schema_version"]
        != registry.PHYSICAL_SOURCE_CELL_SPECS_SCHEMA_VERSION
    )
    assert (
        evidence["official_source_alias_evidence_schema_version"]
        != registry.OFFICIAL_SOURCE_ALIAS_SPECS_SCHEMA_VERSION
    )
    assert (
        evidence["official_source_arithmetic_rule_evidence_schema_version"]
        != registry.OFFICIAL_SOURCE_ARITHMETIC_RULE_SPECS_SCHEMA_VERSION
    )


@pytest.mark.parametrize(
    ("evidence_key", "final_key"),
    (
        (
            "physical_source_cell_evidence",
            "physical_source_cell_specs",
        ),
        (
            "official_source_alias_evidence",
            "official_source_alias_specs",
        ),
        (
            "official_source_arithmetic_rule_evidence",
            "official_source_arithmetic_rule_specs",
        ),
    ),
)
def test__identity_evidence__cannot_enter_final_registry_ingestion(
    evidence,
    evidence_key,
    final_key,
):
    rows = copy.deepcopy(evidence[evidence_key])
    with pytest.raises(registry.RegistryValidationError, match="wrong fields"):
        registry.validate_calibration_target_row_schema(rows[0])
    with pytest.raises(registry.RegistryValidationError, match="wrong fields"):
        registry.validate_calibration_target_specs(rows)
    with pytest.raises(registry.RegistrationAborted):
        registry.validate_frozen_registries(**{final_key: rows})


def test__identity_validator__rejects_structural_locator_corruption(evidence):
    changed = copy.deepcopy(evidence)
    changed["physical_source_cell_evidence"][0]["structural_locator_id"] = (
        "0" * 64
    )
    with pytest.raises(
        builder.EvidenceValidationError,
        match="structural-locator hash drift",
    ):
        builder.validate_evidence(changed)


def test__identity_validator__rejects_coherent_token_digest_corruption(
    evidence,
):
    changed = copy.deepcopy(evidence)
    changed["physical_source_cell_evidence"][0][
        "as_published_token_sha256"
    ] = ("0" * 64)
    with pytest.raises(
        builder.EvidenceValidationError,
        match="fresh committed-source re-resolution",
    ):
        builder.validate_evidence(changed)


def test__identity_validator__rejects_omitted_alias(evidence):
    changed = copy.deepcopy(evidence)
    changed["official_source_alias_evidence"].pop()
    with pytest.raises(builder.EvidenceValidationError, match="alias count"):
        builder.validate_evidence(changed)


def test__pinned_evidence__has_independent_canonical_byte_pins():
    raw = builder.OUT_PATH.read_bytes()
    assert len(raw) == 1_515_381
    assert hashlib.sha256(raw).hexdigest() == (
        "1080acc9672abf209bb9c5ec06170ca351b26200ba1727652fd515b25b216380"
    )
    value = json.loads(raw)
    assert builder.canonical_json_bytes(value) == raw
    assert builder.load_pinned_evidence() == value


def test__pinned_evidence__reproduces_all_sources_and_registries():
    builder.validate_pinned_evidence()


def test__pinned_evidence__rejects_byte_drift_before_source_rebuild(
    tmp_path,
    monkeypatch,
):
    changed_path = tmp_path / builder.OUT_PATH.name
    changed = bytearray(builder.OUT_PATH.read_bytes())
    changed[-2] ^= 1
    changed_path.write_bytes(changed)
    monkeypatch.setattr(builder, "OUT_PATH", changed_path)
    with pytest.raises(builder.EvidenceValidationError, match="sha256"):
        builder.load_pinned_evidence()


def test__validator__rejects_coherently_rehashed_definition(evidence):
    changed = copy.deepcopy(evidence)
    fragment = changed["source_definition_fragments"][0]
    fragment["exact_raw_html_cells_utf8"][0] += " "
    fragments = [
        value.encode("utf-8")
        for value in fragment["exact_raw_html_cells_utf8"]
    ]
    digest = hashlib.sha256(b"\x00".join(fragments)).hexdigest()
    fragment["source_definition_fragment_sha256"] = digest
    locator = fragment["source_definition_locator_id"]
    for rule in changed["official_source_arithmetic_rule_evidence"]:
        if rule["source_definition_locator_id"] == locator:
            rule["source_definition_fragment_sha256"] = digest
    with pytest.raises(
        builder.EvidenceValidationError,
        match="fresh committed-source re-resolution",
    ):
        builder.validate_evidence(changed)
