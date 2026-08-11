"""Unit tests for the source-only PSID dictionary audit."""

from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from populace_dynamics.data import psid_questionnaire_inventory as inventory


def _audit_stub() -> dict:
    return {
        "inventory_ratification_abort": {
            "registration_required_item_ids": ["V-B5", "V-B6", "V-B8"]
        }
    }


def test_design_dimensions_are_frozen_independently():
    assert inventory.INTERVIEW_WAVES == (
        *range(1968, 1998),
        *range(1999, 2024, 2),
    )
    assert inventory.ROLES == (
        "head_or_reference_person",
        "spouse_or_partner",
    )
    assert len(inventory.FIELD_PURPOSES) == 35
    assert inventory.FIELD_PURPOSES[-23:] == (
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


def test_source_builder_imports_no_reader_or_crosswalk():
    source = Path(inventory.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        "populace_dynamics.data.family",
        "populace_dynamics.data.psid_covered_earnings",
    }
    assert imported.isdisjoint(forbidden)


def test_ratified_outputs_fail_closed_with_registered_items():
    audit = _audit_stub()
    for target, function in (
        (inventory.SLOT_SPECS_ID, inventory.require_ratified_slot_specs),
        (
            inventory.SOURCE_INVENTORY_ID,
            inventory.require_ratified_source_inventory,
        ),
    ):
        with pytest.raises(
            inventory.RegistrationRequiredError,
            match=r"V-B5, V-B6, V-B8",
        ) as exc:
            function(audit)
        assert exc.value.target_artifact_id == target
        assert exc.value.item_ids == ("V-B5", "V-B6", "V-B8")


def test_layout_parsers_accept_type_tokens_and_underscores():
    stata = """
infix
    long V173_1 1 - 4
    V609_A 5 - 6
using "[path]FAM.txt", clear;
label variable V173_1 "FIRST FIELD" ;
label variable V609_A "SECOND FIELD" ;
"""
    spss = """
DATA LIST FILE = PSID FIXED /
    V173_1 1 - 4
    V609_A 5 - 6
.
FORMATS
    V173_1 (F4.1)
.
VARIABLE LABELS
    V173_1 "FIRST FIELD"
    V609_A "SECOND FIELD"
.
"""
    stata_layout, stata_labels = inventory._parse_stata(stata)
    spss_layout, spss_labels, formats = inventory._parse_spss(spss)
    assert (
        stata_layout
        == spss_layout
        == [
            ("V173_1", 1, 4),
            ("V609_A", 5, 6),
        ]
    )
    assert stata_labels == spss_labels
    assert formats == {"V173_1": "F4.1"}


def test_layout_gap_and_ambiguous_files_fail_closed(tmp_path: Path):
    with pytest.raises(inventory.DictionaryDriftError, match="gap/overlap"):
        inventory._assert_layout_complete(
            2003,
            [("A", 1, 1), ("B", 3, 3)],
        )
    (tmp_path / "one.do").write_text("", encoding="utf-8")
    (tmp_path / "two.do").write_text("", encoding="utf-8")
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="expected exactly one main",
    ):
        inventory._single_file(tmp_path, ".do", formats=False)


def test_required_format_pair_cannot_be_silently_omitted(tmp_path: Path):
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="missing its required field-bound format pair",
    ):
        inventory._format_pair_for_wave(tmp_path, 2021)

    do_path = tmp_path / "FAM2021ER_formats.do"
    sps_path = tmp_path / "FAM2021ER_formats.sps"
    do_path.touch()
    sps_path.touch()
    assert inventory._format_pair_for_wave(tmp_path, 2021) == (
        do_path,
        sps_path,
    )
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="unexpected field-bound format pair",
    ):
        inventory._format_pair_for_wave(tmp_path, 2019)


def test_codebook_authority_file_must_be_unique(tmp_path: Path):
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="expected exactly one codebook PDF",
    ):
        inventory._single_codebook_file(tmp_path)

    first = tmp_path / "FAM1976_codebook.pdf"
    first.touch()
    assert inventory._single_codebook_file(tmp_path) == first

    (tmp_path / "alternate_codebook_public.pdf").touch()
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="expected exactly one codebook PDF",
    ):
        inventory._single_codebook_file(tmp_path)


def test_paired_dictionary_label_drift_fails_closed(tmp_path: Path):
    do_path = tmp_path / "FAM.do"
    sps_path = tmp_path / "FAM.sps"
    do_path.write_text(
        """
infix
    A 1 - 1
using "[path]FAM.txt", clear;
label variable A "SOURCE LABEL" ;
""",
        encoding="utf-8",
    )
    sps_path.write_text(
        """
DATA LIST FILE = PSID FIXED /
    A 1 - 1
.
VARIABLE LABELS
    A "DRIFTED LABEL"
.
""",
        encoding="utf-8",
    )
    with pytest.raises(inventory.DictionaryDriftError, match="disagreement"):
        inventory._compare_wave_dictionaries(2003, do_path, sps_path)


def test_field_bound_stata_maps_preserve_complete_positive_evidence(
    tmp_path: Path,
):
    stata_path = tmp_path / "formats.do"
    stata_path.write_bytes(
        (
            "label define AL  ///\n"
            '  -9 "NA; refused"  ///\n'
            '   1 `"Twelfth grade, "High School", GED"\'\n'
            "forvalues n = 2 /3 {\n"
            "    label define AL `n' "
            '"Associate`=char(146)\'s value", modify\n'
            "}\n"
            "label values A AL\n"
        ).encode("cp1252")
    )
    spss_path = tmp_path / "formats.sps"
    spss_path.write_bytes(
        (
            "VALUE LABELS\n"
            "A   /*Truncated value label ends with ...*/\n"
            " -9 'NA; refused'\n"
            "  1 'Truncated'\n"
            "  2 'Truncated'\n"
            "  3 'Truncated'\n"
            ".\nEXECUTE.\n"
        ).encode("cp1252")
    )
    evidence = inventory._format_evidence(
        stata_path,
        spss_path,
        {"A"},
    )
    assert evidence["field_bound_format_map_columns"] == [
        "raw_field_id",
        "stata_value_label_id",
        "code_label_rows",
    ]
    assert evidence["code_label_columns"] == [
        "raw_code",
        "exact_stata_value_label",
    ]
    assert evidence["field_bound_format_maps"] == [
        [
            "A",
            "AL",
            [
                [-9, "NA; refused"],
                [1, 'Twelfth grade, "High School", GED'],
                [2, "Associate’s value"],
                [3, "Associate’s value"],
            ],
        ]
    ]
    assert evidence["value_label_map_count"] == 1
    assert evidence["value_label_row_count"] == 4
    assert evidence["explicit_truncation_count"] == 1


@pytest.mark.parametrize(
    ("stata", "spss", "physical_fields", "message"),
    [
        (
            'label define AL 1 "One" 1 "Duplicate"\nlabel values A AL\n',
            "VALUE LABELS\nA\n 1 'One'\n.\n",
            {"A"},
            "duplicate Stata",
        ),
        (
            'label define AL 1 "One"\nlabel values A BL\n',
            "VALUE LABELS\nA\n 1 'One'\n.\n",
            {"A"},
            "definitions and bindings disagree",
        ),
        (
            'label define AL 1 "One"\nlabel values A AL\n',
            "VALUE LABELS\nA\n 2 'Two'\n.\n",
            {"A"},
            "code domains disagree",
        ),
        (
            'label define AL 1 "One"\nlabel values A AL\n',
            "VALUE LABELS\nA\n 1 'One'\n.\n",
            set(),
            "outside the physical layout",
        ),
    ],
)
def test_field_bound_format_map_drift_fails_closed(
    tmp_path: Path,
    stata: str,
    spss: str,
    physical_fields: set[str],
    message: str,
):
    stata_path = tmp_path / "formats.do"
    spss_path = tmp_path / "formats.sps"
    stata_path.write_text(stata, encoding="cp1252")
    spss_path.write_text(spss, encoding="cp1252")
    with pytest.raises(inventory.DictionaryDriftError, match=message):
        inventory._format_evidence(
            stata_path,
            spss_path,
            physical_fields,
        )


def test_core_integrity_helpers_reject_count_key_and_content_drift():
    row = [
        "psid-physical-field:" + "a" * 64,
        2003,
        2002,
        "ER1",
        1,
        1,
        1,
        None,
        "FIELD",
        ["do", "sps"],
    ]
    artifact = {
        "physical_fields": [row],
        "physical_field_count": 1,
        "physical_field_keyset_sha256": inventory._keyset_hash([row[0]]),
        "integrity": {"content_sha256": "0" * 64},
    }
    artifact["integrity"]["content_sha256"] = inventory.sha256_bytes(
        inventory.canonical_json_bytes(artifact)
    )
    inventory._validate_physical_field_integrity(artifact)
    inventory._validate_content_integrity(artifact)

    bad_count = copy.deepcopy(artifact)
    bad_count["physical_field_count"] = 2
    with pytest.raises(inventory.DictionaryDriftError, match="count"):
        inventory._validate_physical_field_integrity(bad_count)

    bad_keyset = copy.deepcopy(artifact)
    bad_keyset["physical_field_keyset_sha256"] = "f" * 64
    with pytest.raises(inventory.DictionaryDriftError, match="keyset"):
        inventory._validate_physical_field_integrity(bad_keyset)

    bad_content = copy.deepcopy(artifact)
    bad_content["physical_fields"][0][8] = "CHANGED"
    with pytest.raises(inventory.DictionaryDriftError, match="content"):
        inventory._validate_content_integrity(bad_content)


def test_format_evidence_validator_rejects_map_mutation():
    maps = [["ER1", "ER1L", [[1, "Yes"], [5, "No"]]]]
    evidence = {
        "interview_wave": 2021,
        "field_bound_format_map_columns": list(
            inventory.FIELD_BOUND_FORMAT_MAP_COLUMNS
        ),
        "code_label_columns": list(inventory.CODE_LABEL_COLUMNS),
        "field_bound_format_maps": maps,
        "field_bound_format_maps_sha256": inventory.sha256_bytes(
            inventory.canonical_json_bytes(maps)
        ),
        "value_label_map_count": 1,
        "value_label_row_count": 2,
    }
    inventory._validate_format_file_evidence(
        evidence,
        {2021: {"ER1"}},
    )

    mutated = copy.deepcopy(evidence)
    mutated["field_bound_format_maps"][0][2][0][1] = "Changed"
    with pytest.raises(
        inventory.DictionaryDriftError,
        match="field-bound format-map hash mismatch",
    ):
        inventory._validate_format_file_evidence(
            mutated,
            {2021: {"ER1"}},
        )
