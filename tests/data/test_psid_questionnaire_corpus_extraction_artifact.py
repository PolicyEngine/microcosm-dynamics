"""Offline checks for the committed PSID questionnaire extraction audit."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
ARTIFACT_PATH = (
    ROOT / "data" / "external" / "psid_questionnaire_corpus_extraction_v1.json"
)
ARTIFACT_SHA256 = (
    "5fb39a0ada3ccb0da0883e4db7bb6b36edeb60865d90ed061bc0b74e1fd12347"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_psid_questionnaire_corpus_extraction as builder  # noqa: E402


def _artifact() -> dict:
    value = builder._strictly_parsed_document(
        ARTIFACT_PATH.read_bytes(), "committed questionnaire extraction"
    )
    assert isinstance(value, dict)
    return value


def _reseal(value: dict) -> None:
    value["integrity"]["content_sha256"] = builder._content_sha256(value)


def test_committed_extraction_is_canonical_and_has_exact_identity():
    raw = ARTIFACT_PATH.read_bytes()
    value = _artifact()
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    assert len(raw) == 81_177
    assert raw == builder.canonical_json_bytes(value)
    assert value["schema_version"] == builder.SCHEMA_VERSION
    assert value["artifact_id"] == builder.ARTIFACT_ID
    assert value["integrity"] == {
        "canonicalization": builder.CANONICALIZATION,
        "content_sha256": (
            "18ec2e023152d179de68d72ebf1966549a6e46ef48743aa9ec607f565de3128c"
        ),
        "source_byte_ranges_verified": True,
        "structural_status": "pass",
    }
    builder.validate_structure(value)


def test_source_identities_and_authority_disposition_record_acceptance():
    value = _artifact()
    identities = {
        row["source_artifact_id"]: row
        for row in value["source_artifact_identities"]
    }
    assert identities == {
        source_id: {"source_artifact_id": source_id, **identity}
        for source_id, identity in builder.FROZEN_INPUTS.items()
    }
    assert identities["membership_adjudication_v2"]["sha256"] == (
        "7306c898d044df0ce86754b8468b26e32d8696027e8dde2f7d5935d79f1abb14"
    )
    assert value["authority_disposition"] == {
        "corpus_registration_status": "pass",
        "accepted_corpus_authority": True,
        "verified_candidate_documents_may_support_nonoperative_audit": True,
        "membership_v3_or_supersession_effect": "none",
    }


def test_every_locator_is_absolute_path_free_and_fail_closed():
    value = _artifact()
    passages = value["passage_locators"]
    whole_documents = value["whole_document_locators"]
    assert len(passages) == 61
    assert len(whole_documents) == 37
    assert len({row["locator_id"] for row in passages}) == len(passages)
    assert len({row["locator_id"] for row in whole_documents}) == 37
    for row in [*passages, *whole_documents]:
        assert row["filename"] == Path(row["filename"]).name
        assert not Path(row["filename"]).is_absolute()
        assert "/Users/" not in json.dumps(row)
        assert re.fullmatch(r"[0-9a-f]{64}", row["full_file_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}", row["range_sha256"])
        assert row["size_bytes"] > 0
        assert 0 <= row["byte_start"] < row["byte_end"] <= row["size_bytes"]
    for row in whole_documents:
        assert row["byte_start"] == 0
        assert row["byte_end"] == row["size_bytes"]
        assert row["range_sha256"] == row["full_file_sha256"]
        assert row["location_type"] == "whole_document_exact_file_range"
    assert [row["interview_wave"] for row in whole_documents] == [
        *range(1968, 1998),
        *range(1999, 2012, 2),
    ]


def test_absence_proofs_are_source_backed_and_references_resolve():
    value = _artifact()
    locator_ids = {
        row["locator_id"]
        for row in [
            *value["passage_locators"],
            *value["whole_document_locators"],
        ]
    }
    absence_rows = value["absence_proofs"]
    absence_ids = {row["absence_proof_id"] for row in absence_rows}
    assert absence_ids == {
        "vb5_1968_1975_unsupported_slot_absence",
        "vb6_1977_1978_wife_section_exhaustion",
        "vb8_pre_2013_current_regular_school_absence",
    }
    for row in absence_rows:
        assert row["searched_locator_ids"]
        assert set(row["searched_locator_ids"]) <= locator_ids
        assert row["search_domain"]
        assert row["search_implementation"].endswith("_v1")
        assert row["excluded_near_matches"]
    pre2013 = next(
        row
        for row in absence_rows
        if row["absence_proof_id"]
        == "vb8_pre_2013_current_regular_school_absence"
    )
    assert len(pre2013["searched_interview_waves"]) == 37
    assert len(pre2013["searched_locator_ids"]) == 37
    for residual in value["psid_vb_residual_extractions"]:
        assert set(residual["evidence_locator_ids"]) <= locator_ids
        assert set(residual["absence_proof_ids"]) <= absence_ids


def test_membership_fact_domain_is_recorded_as_not_established_by_psid():
    rows = _artifact()["membership_fact_extractions"]
    assert len(rows) == 30
    assert [row["source_pointer"] for row in rows] == [
        f"/facts/{index}" for index in range(30)
    ]
    assert len({row["fact_id"] for row in rows}) == 30
    assert {row["source_disposition"] for row in rows} == {
        "does_not_establish_membership_facts"
    }
    assert {row["authority_scope"] for row in rows} == {
        "psid_variable_semantics_only"
    }
    assert all(row["evidence_locator_ids"] == [] for row in rows)
    verdicts = [row["retained_v2_verdict"] for row in rows]
    assert verdicts.count("established") == 2
    assert (
        verdicts.count("partially_established_required_fact_unestablished")
        == 17
    )
    assert verdicts.count("unestablished") == 11


def test_eight_target_residuals_have_honest_evidentiary_outcomes():
    value = _artifact()
    rows = value["psid_vb_residual_extractions"]
    assert len(rows) == 8
    assert [row["residual_id"] for row in rows] == list(
        builder.TARGET_RESIDUAL_INDEXES
    )
    assert (
        sum(
            row["evidentiary_verdict"] == "established_by_questionnaire_corpus"
            for row in rows
        )
        == 7
    )
    partial = [
        row
        for row in rows
        if row["evidentiary_verdict"]
        == "partially_established_required_fact_unestablished"
    ]
    assert [row["residual_id"] for row in partial] == [
        "ry1975_1977_spouse_concept_seam:V-B6:secondary_job_attachment_and_absence"
    ]
    assert partial[0]["remaining_unestablished_facts"] == [
        "No captured questionnaire or editing instruction supplies the exact allocation from V4901-V4906 components to annual V4379/V5289/V5788 totals."
    ]
    assert {row["operative_effect"] for row in rows} == {
        "none_accepted_corpus_and_frozen_design_domain"
    }
    assert value["family_extraction_summary"] == [
        {
            "family_id": "V-B5",
            "targeted_residual_count": 1,
            "evidentially_closed_count": 1,
            "remaining_partial_count": 0,
            "remaining_residual_count": 0,
            "operative_verdict": "registration_required",
        },
        {
            "family_id": "V-B6",
            "targeted_residual_count": 4,
            "evidentially_closed_count": 3,
            "remaining_partial_count": 1,
            "remaining_residual_count": 1,
            "operative_verdict": "registration_required",
        },
        {
            "family_id": "V-B8",
            "targeted_residual_count": 3,
            "evidentially_closed_count": 3,
            "remaining_partial_count": 0,
            "remaining_residual_count": 0,
            "operative_verdict": "registration_required",
        },
    ]


@pytest.mark.parametrize(
    "mutation",
    (
        "top_level",
        "source_identity",
        "authority_disposition",
        "extraction_method",
        "passage_locator",
        "whole_document_locator",
        "absence_proof",
        "membership_fact",
        "residual",
        "family_summary",
        "integrity_status",
    ),
)
def test_structure_rejects_coherently_resealed_mutations(mutation: str):
    value = copy.deepcopy(_artifact())
    if mutation == "top_level":
        value["unexpected"] = None
    elif mutation == "source_identity":
        value["source_artifact_identities"][0]["sha256"] = "0" * 64
    elif mutation == "authority_disposition":
        value["authority_disposition"]["accepted_corpus_authority"] = False
    elif mutation == "extraction_method":
        value["extraction_method"]["derived_text_retained"] = True
    elif mutation == "passage_locator":
        value["passage_locators"][0]["range_sha256"] = "0" * 64
    elif mutation == "whole_document_locator":
        value["whole_document_locators"][0]["byte_end"] -= 1
    elif mutation == "absence_proof":
        value["absence_proofs"][0]["searched_locator_ids"].append("missing")
    elif mutation == "membership_fact":
        value["membership_fact_extractions"][0][
            "source_disposition"
        ] = "established"
    elif mutation == "residual":
        value["psid_vb_residual_extractions"][0][
            "operative_effect"
        ] = "operative"
    elif mutation == "family_summary":
        value["family_extraction_summary"][0]["remaining_residual_count"] = 1
    else:
        value["integrity"]["structural_status"] = "fail"
    _reseal(value)
    with pytest.raises(ValueError):
        builder.validate_structure(value)
