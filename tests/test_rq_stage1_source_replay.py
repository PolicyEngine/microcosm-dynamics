"""Always-runnable validation for the R_Q stage-1 replay parent."""

from __future__ import annotations

import copy
import hashlib
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ARTIFACT_PATH = (
    ROOT / "docs" / "analysis" / "rq_stage1_evidence" / "source_replay_v1.json"
)
CANONICAL_Q5_PATH = (
    ROOT
    / "data"
    / "external"
    / "psid_questionnaire_slot_closure_evidence_v1.json"
)
EXPECTED_RAW_SHA256 = (
    "f2f676db3f9180b85af1977253fb8c10ff7fd60494e1597212b922dfc0f5920a"
)
EXPECTED_CONTENT_SHA256 = (
    "48e259ddf4c9eb60b7f9fdfd73b2576255400a7cdf19e4115d41bcf5bad3e8cc"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_rq_stage1_source_replay as builder  # noqa: E402


def _artifact() -> dict:
    value = builder.replay.strict_parse_document(
        ARTIFACT_PATH.read_bytes(), "committed R_Q source replay"
    )
    assert isinstance(value, dict)
    return value


def _reseal(value: dict) -> None:
    value["integrity"]["content_sha256"] = builder.replay._content_sha256(
        value
    )


def test_source_replay_is_canonical_sha_pinned_and_valid():
    raw = ARTIFACT_PATH.read_bytes()
    artifact = _artifact()
    assert raw == builder.replay.canonical_json_bytes(artifact)
    assert len(raw) == 7_508_291
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_RAW_SHA256
    assert artifact["integrity"]["content_sha256"] == (EXPECTED_CONTENT_SHA256)
    builder.validate_source_replay(artifact)


def test_source_replay_pins_both_roots_and_complete_dispositions():
    artifact = _artifact()
    roots = artifact["upstream_corpus_registry_identity"]
    assert roots["questionnaire_corpus_root"] == builder.QUESTIONNAIRE_ROOT
    assert roots["field_corpus_root"] == builder.FIELD_ROOT
    assert roots["projection_law"] == (
        "fixed_two_root_complete_source_document_projection"
    )
    dispositions = artifact["upstream_disposition_replay"]
    assert dispositions["source_link_disposition_count"] == 465
    assert dispositions["source_link_disposition_counts"] == (
        builder.EXPECTED_LINK_DISPOSITION_COUNTS
    )
    assert dispositions["accepted_document_disposition_count"] == 456
    assert dispositions["accepted_document_disposition_counts"] == (
        builder.EXPECTED_ACCEPTED_DISPOSITION_COUNTS
    )


def test_source_replay_exact_covers_u_and_questionnaire_slice():
    source = _artifact()["source_document_replay"]
    assert (
        source["source_document_count"]
        == len(source["source_documents"])
        == 257
    )
    assert source["source_document_role_counts"] == {
        "questionnaire_flow": 81,
        "dictionary_layout": 86,
        "codebook": 47,
        "raw_fixed_width_data": 43,
    }
    assert (
        source["questionnaire_document_count"]
        == len(source["questionnaire_documents"])
        == 81
    )
    assert source["source_document_keyset_sha256"] == (
        builder.replay.EXPECTED_U_KEYSET_SHA256
    )
    assert source["source_document_domain_sha256"] == (
        builder.replay.EXPECTED_U_DOMAIN_SHA256
    )


def test_source_replay_pins_exact_poppler_authority_and_all_pages():
    pages = _artifact()["questionnaire_page_replay"]
    derivation = pages["questionnaire_page_text_derivation"]
    assert "implementation_path" in derivation
    assert "path" not in derivation
    assert pages["questionnaire_page_text_derivation_byte_size"] == 566
    assert pages["questionnaire_page_text_derivation_sha256"] == (
        "8ce4d7e16753aa0a6c2220006c9aea60330acd62de809db5894ad03eb9123da3"
    )
    assert (
        pages["questionnaire_page_count"]
        == len(pages["questionnaire_page_rows"])
        == 10_190
    )
    assert pages["questionnaire_page_keyset_sha256"] == (
        builder.EXPECTED_PAGE_KEYSET_SHA256
    )
    assert pages["questionnaire_page_domain_sha256"] == (
        builder.EXPECTED_PAGE_DOMAIN_SHA256
    )
    assert pages["document_page_row_count"] == 81
    assert (
        sum(row["page_count"] for row in pages["document_page_rows"]) == 10_190
    )


def test_source_replay_exact_covers_six_eras():
    rows = _artifact()["era_replay_rows"]
    assert [
        (row["questionnaire_document_count"], row["questionnaire_page_count"])
        for row in rows
    ] == [
        (16, 842),
        (6, 408),
        (29, 3_349),
        (12, 1_622),
        (14, 2_337),
        (4, 1_632),
    ]


def test_source_replay_enforces_candidate_nonselection_and_nonauthority():
    artifact = _artifact()
    assert artifact["candidate_nonselection_law"] == (
        builder.CANDIDATE_NONSELECTION_LAW
    )
    assert artifact["authority_disposition"] == {
        "authority_kind": "nonauthority_source_replay_parent",
        "canonical_q5_emitted": False,
        "canonical_annotation_rows_emitted": False,
        "candidate_occurrence_rows_emitted": False,
        "source_manifest_candidate_status": builder.replay.BLOCKED_STATUS,
        "status": builder.STATUS,
    }
    assert not CANONICAL_Q5_PATH.exists()


@pytest.mark.parametrize(
    ("member", "replacement"),
    (
        ("schema_version", "candidate_selected.v1"),
        ("status", "pass"),
    ),
)
def test_validator_rejects_resealed_top_level_mutations(
    member: str, replacement: str
):
    artifact = copy.deepcopy(_artifact())
    artifact[member] = replacement
    _reseal(artifact)
    with pytest.raises(ValueError):
        builder.validate_source_replay(artifact)


def test_validator_rejects_resealed_nested_extra_member():
    artifact = copy.deepcopy(_artifact())
    artifact["source_document_replay"]["candidate_selected"] = True
    _reseal(artifact)
    with pytest.raises(ValueError, match="keyset drift"):
        builder.validate_source_replay(artifact)


def test_validator_rejects_coherent_disposition_swap_and_reseal():
    artifact = copy.deepcopy(_artifact())
    relation = artifact["upstream_disposition_replay"]
    rows = relation["source_link_disposition_rows"]
    included = next(
        row
        for row in rows
        if row["disposition"] == "included_family_questionnaire_flow"
    )
    excluded = next(
        row
        for row in rows
        if row["disposition"] == "excluded_not_family_questionnaire_flow"
    )
    included["disposition"], excluded["disposition"] = (
        excluded["disposition"],
        included["disposition"],
    )
    relation["source_link_disposition_counts"] = dict(
        Counter(row["disposition"] for row in rows)
    )
    relation["source_link_disposition_domain_sha256"] = (
        builder.replay._canonical_digest(rows)
    )
    _reseal(artifact)
    with pytest.raises(ValueError, match="disposition replay drift"):
        builder.validate_source_replay(artifact)


def test_validator_rejects_coherently_reidentified_page_mutation():
    artifact = copy.deepcopy(_artifact())
    pages = artifact["questionnaire_page_replay"]
    row = pages["questionnaire_page_rows"][0]
    row["page_text_utf8_sha256"] = "f" * 64
    row["questionnaire_page_id"] = (
        "psid-questionnaire-page:"
        + builder.replay._canonical_digest(
            [
                row["source_document_id"],
                row["interview_wave"],
                row["page_number"],
                row["page_text_utf8_sha256"],
            ]
        )
    )
    pages["questionnaire_page_keyset_sha256"] = (
        builder.replay._canonical_digest(
            [
                page["questionnaire_page_id"]
                for page in pages["questionnaire_page_rows"]
            ]
        )
    )
    pages["questionnaire_page_domain_sha256"] = (
        builder.replay._canonical_digest(pages["questionnaire_page_rows"])
    )
    pages["document_page_rows"] = builder._document_page_rows(
        artifact["source_document_replay"], pages
    )
    pages["document_page_domain_sha256"] = builder.replay._canonical_digest(
        pages["document_page_rows"]
    )
    artifact["era_replay_rows"] = builder._era_replay_rows(
        artifact["source_document_replay"], pages
    )
    _reseal(artifact)
    with pytest.raises(ValueError, match="questionnaire page replay drift"):
        builder.validate_source_replay(artifact)


def test_validator_rejects_candidate_auto_promotion():
    artifact = copy.deepcopy(_artifact())
    law = artifact["candidate_nonselection_law"]
    law["stage2_candidate_auto_promotion_permitted"] = True
    law["stage2_explicit_adjudication_required_for_every_row"] = False
    _reseal(artifact)
    with pytest.raises(ValueError, match="nonselection-law drift"):
        builder.validate_source_replay(artifact)
