"""Offline tests for the nonoperative questionnaire closure attempt."""

from __future__ import annotations

import copy
import hashlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ARTIFACT_PATH = (
    ROOT
    / "data"
    / "external"
    / "covered_earnings_questionnaire_closure_attempt_v1.json"
)
MEMBERSHIP_V2_PATH = (
    ROOT
    / "data"
    / "external"
    / "covered_earnings_membership_adjudication_v2.json"
)
ARTIFACT_SHA256 = (
    "3a262fbc0d9b6106632abb222385ca08a270ae4b51af5a8936278d53be2a2017"
)
MEMBERSHIP_V2_SHA256 = (
    "7306c898d044df0ce86754b8468b26e32d8696027e8dde2f7d5935d79f1abb14"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_covered_earnings_questionnaire_closure_attempt as builder  # noqa: E402


def _artifact() -> dict:
    value = builder._strictly_parsed_document(
        ARTIFACT_PATH.read_bytes(), "committed questionnaire closure attempt"
    )
    assert isinstance(value, dict)
    return value


def _membership_v2() -> dict:
    value = builder._strictly_parsed_document(
        MEMBERSHIP_V2_PATH.read_bytes(), "frozen membership v2"
    )
    assert isinstance(value, dict)
    return value


def _reseal(value: dict) -> None:
    value["integrity"]["content_sha256"] = builder._content_sha256(value)


def test_closure_attempt_is_canonical_byte_reproducible_and_sha_pinned():
    raw = ARTIFACT_PATH.read_bytes()
    value = _artifact()
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    assert len(raw) == 50_474
    assert raw == builder.canonical_json_bytes(value)
    assert raw == builder.render()
    assert value["schema_version"] == builder.SCHEMA_VERSION
    assert value["artifact_id"] == builder.ARTIFACT_ID
    assert value["integrity"]["content_sha256"] == (
        "6c6e5d99c8221d5a2c1c125ec8f6ed9284d1ea7ba8d8fbe867a238da44454ec8"
    )
    builder.validate_closure_attempt(value)


def test_membership_v2_frozen_bytes_are_preserved_exactly():
    value = _artifact()
    assert hashlib.sha256(MEMBERSHIP_V2_PATH.read_bytes()).hexdigest() == (
        MEMBERSHIP_V2_SHA256
    )
    assert len(MEMBERSHIP_V2_PATH.read_bytes()) == 57_125
    assert value["integrity"]["membership_v2_raw_sha256_preserved"] == (
        MEMBERSHIP_V2_SHA256
    )
    source = next(
        row
        for row in value["source_artifact_identities"]
        if row["source_artifact_id"] == "membership_adjudication_v2"
    )
    assert source["size_bytes"] == 57_125
    assert source["sha256"] == MEMBERSHIP_V2_SHA256


def test_design_authority_locators_bind_the_frozen_ratified_prefix():
    value = _artifact()
    design = builder.FROZEN_DESIGN_PREFIX
    live = (ROOT / design["committed_path"]).read_bytes()
    frozen = live[: design["size_bytes"]]
    assert len(frozen) == design["size_bytes"]
    assert hashlib.sha256(frozen).hexdigest() == design["sha256"]
    locators = value["design_authority_locators"]
    assert len(locators) == 6
    assert {row["locator_id"] for row in locators} == {
        row[0] for row in builder.DESIGN_LOCATOR_SPECS
    }
    for row in locators:
        assert row["committed_path"] == design["committed_path"]
        assert row["identity_scope"] == "append_only_prefix"
        assert row["full_source_sha256"] == design["sha256"]
        assert row["size_bytes"] == design["size_bytes"]
        assert 0 <= row["byte_start"] < row["byte_end"] <= len(frozen)
        assert (
            hashlib.sha256(
                frozen[row["byte_start"] : row["byte_end"]]
            ).hexdigest()
            == row["range_sha256"]
        )
        assert re.fullmatch(r"[0-9a-f]{64}", row["range_sha256"])


def test_supersession_is_blocked_by_design_and_failed_capture_registration():
    value = _artifact()
    adjudication = value["supersession_adjudication"]
    assert adjudication == {
        "membership_v3_permitted": False,
        "disposition": "blocked_missing_ratified_append_only_successor_registry",
        "legacy_membership_v2_disposition": "byte_frozen_preserved",
        "operative_effect": "none",
        "design_blocking_locator_ids": [
            "closed_methodology_registry_requires_successor",
            "membership_v2_legacy_envelope_law",
            "membership_methodology_successor_law",
            "frozen_membership_methodology_identity_law",
            "closed_psid_source_disposition_law",
            "frozen_vb_source_rows_and_residuals_law",
        ],
        "independent_capture_blocker": {
            "disposition": "corpus_registration_failed",
            "document_candidate_count": 456,
            "verified_document_count": 440,
            "failed_document_count": 16,
            "accepted_authority_registry": None,
        },
    }
    assert value["attempt_scope"]["accepted_authority_registration"] is False
    assert value["closure_disposition"]["membership_v3_emitted"] is False
    assert not (
        ROOT
        / "data"
        / "external"
        / "covered_earnings_membership_adjudication_v3.json"
    ).exists()


def test_all_membership_facts_retain_v2_verdicts_and_exact_row_hashes():
    value = _artifact()
    source = _membership_v2()
    rows = value["membership_fact_readjudications"]
    assert len(rows) == len(source["facts"]) == 30
    for index, (row, fact) in enumerate(
        zip(rows, source["facts"], strict=True)
    ):
        assert row["source_pointer"] == f"/facts/{index}"
        assert (
            row["v2_fact_row_sha256"]
            == hashlib.sha256(builder.canonical_json_bytes(fact)).hexdigest()
        )
        assert row["fact_id"] == fact["fact_id"]
        assert row["prior_v2_verdict"] == fact["verdict"]
        assert row["closure_attempt_verdict"] == fact["verdict"]
        assert row["psid_corpus_source_disposition"] == (
            "does_not_establish_membership_facts"
        )
        assert row["evidence_locator_ids"] == []
        assert row["supersession_effect"] == "none"
    assert value["membership_verdict_summary"] == {
        "fact_count": 30,
        "established_count": 2,
        "partially_established_count": 17,
        "unestablished_count": 11,
    }


def test_all_membership_family_dispositions_remain_fail_closed():
    value = _artifact()
    source = _membership_v2()
    rows = value["membership_family_dispositions"]
    assert len(rows) == len(source["family_dispositions"]) == 14
    for index, (row, family) in enumerate(
        zip(rows, source["family_dispositions"], strict=True)
    ):
        assert row["source_pointer"] == f"/family_dispositions/{index}"
        assert (
            row["v2_family_row_sha256"]
            == hashlib.sha256(builder.canonical_json_bytes(family)).hexdigest()
        )
        assert row["target_family"] == family["target_family"]
        assert row["prior_v2_verdict"] == "fail_closed"
        assert row["closure_attempt_verdict"] == "fail_closed"
        assert (
            row["missing_source_fact_ids"] == family["missing_source_fact_ids"]
        )
        assert (
            row["missing_registration_authority_ids"]
            == family["missing_registration_authority_ids"]
        )
        assert row["supersession_effect"] == "none"


def test_psid_evidentiary_closure_does_not_change_operative_residuals():
    value = _artifact()
    evidence = value["psid_questionnaire_evidence_results"]
    assert len(evidence) == 8
    assert (
        sum(
            row["evidentiary_verdict"] == "established_by_questionnaire_corpus"
            for row in evidence
        )
        == 7
    )
    assert (
        sum(bool(row["remaining_unestablished_facts"]) for row in evidence)
        == 1
    )
    assert {row["operative_effect"] for row in evidence} == {"none"}
    assert value["psid_vb_family_summary"] == [
        {
            "family_id": "V-B5",
            "targeted_residual_count": 1,
            "evidentially_closed_count": 1,
            "evidentiary_remaining_residual_count": 0,
            "operative_residual_count": 1,
            "operative_source_disposition": "registration_required",
            "operative_change": "none",
        },
        {
            "family_id": "V-B6",
            "targeted_residual_count": 4,
            "evidentially_closed_count": 3,
            "evidentiary_remaining_residual_count": 1,
            "operative_residual_count": 4,
            "operative_source_disposition": "registration_required",
            "operative_change": "none",
        },
        {
            "family_id": "V-B8",
            "targeted_residual_count": 3,
            "evidentially_closed_count": 3,
            "evidentiary_remaining_residual_count": 0,
            "operative_residual_count": 3,
            "operative_source_disposition": "registration_required",
            "operative_change": "none",
        },
    ]
    assert value["closure_disposition"] == {
        "evidentiary_residuals_by_family": {"V-B5": 0, "V-B6": 1, "V-B8": 0},
        "operative_residuals_by_family": {"V-B5": 1, "V-B6": 4, "V-B8": 3},
        "membership_facts_changed": 0,
        "membership_families_changed": 0,
        "membership_v3_emitted": False,
        "closure_attempt_status": "nonoperative_partial_evidentiary_closure",
        "required_next_authority_action": "restore_all_456_capture_identities_then_ratify_append_only_successor_registry_and_fresh_adjudication",
    }


@pytest.mark.parametrize(
    "mutation",
    (
        "top_level",
        "source_identity",
        "design_locator",
        "scope",
        "supersession",
        "membership_summary",
        "membership_fact",
        "membership_family",
        "operative_psid",
        "questionnaire_evidence",
        "family_summary",
        "closure_disposition",
        "membership_sha",
    ),
)
def test_closure_validator_rejects_coherently_resealed_mutations(
    mutation: str,
):
    value = copy.deepcopy(_artifact())
    if mutation == "top_level":
        value["unexpected"] = None
    elif mutation == "source_identity":
        value["source_artifact_identities"][0]["size_bytes"] += 1
    elif mutation == "design_locator":
        value["design_authority_locators"][0]["line_start"] += 1
    elif mutation == "scope":
        value["attempt_scope"]["accepted_authority_registration"] = True
    elif mutation == "supersession":
        value["supersession_adjudication"]["membership_v3_permitted"] = True
    elif mutation == "membership_summary":
        value["membership_verdict_summary"]["established_count"] += 1
    elif mutation == "membership_fact":
        value["membership_fact_readjudications"][0][
            "closure_attempt_verdict"
        ] = "established"
    elif mutation == "membership_family":
        value["membership_family_dispositions"][0][
            "closure_attempt_verdict"
        ] = "established"
    elif mutation == "operative_psid":
        value["operative_psid_vb_rows"][0]["operative_residual_count"] = 0
    elif mutation == "questionnaire_evidence":
        value["psid_questionnaire_evidence_results"][0][
            "operative_effect"
        ] = "operative"
    elif mutation == "family_summary":
        value["psid_vb_family_summary"][0]["operative_change"] = "changed"
    elif mutation == "closure_disposition":
        value["closure_disposition"]["membership_v3_emitted"] = True
    else:
        value["integrity"]["membership_v2_raw_sha256_preserved"] = "0" * 64
    _reseal(value)
    with pytest.raises(ValueError):
        builder.validate_closure_attempt(value)
