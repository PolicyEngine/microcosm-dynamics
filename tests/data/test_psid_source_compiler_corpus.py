"""Authenticated-corpus vectors for the revision-9 source compiler."""

from pathlib import Path

import pytest

from populace_dynamics.data import psid_source_compiler as compiler

PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()


@pytest.fixture(scope="module")
def evidence_corpus():
    return compiler.load_authenticated_evidence(
        psid_root=PSID_ROOT,
        authenticate_source_files=True,
    )


@pytest.fixture(scope="module")
def wave_1968_derivation(evidence_corpus):
    source_document = next(
        row
        for row in evidence_corpus.source_manifest
        if row["document_role"] == "raw_fixed_width_data"
        and row["interview_waves"] == [1968]
    )
    return compiler.frame_fixed_width_records(
        source_document,
        evidence_corpus.fields,
        PSID_ROOT,
    )


def test_complete_authenticated_denominator_and_document_roles(
    evidence_corpus,
):
    assert len(evidence_corpus.fields) == 89_599
    assert (
        compiler.canonical_sha256(
            [list(field.key) for field in evidence_corpus.fields]
        )
        == compiler.EXPECTED_DENOMINATOR_SHA256
    )
    role_counts = {
        role: sum(
            row["document_role"] == role
            for row in evidence_corpus.source_manifest
        )
        for role in (
            "dictionary_layout",
            "codebook",
            "raw_fixed_width_data",
        )
    }
    assert role_counts == {
        "dictionary_layout": 86,
        "codebook": 47,
        "raw_fixed_width_data": 43,
    }


def test_a6_1968_raw_framing_and_observed_token_digests(
    wave_1968_derivation,
):
    assert wave_1968_derivation["record_count"] == 4_802
    assert wave_1968_derivation["record_framing"]["record_width"] == 771
    census = {
        row["raw_field_id"]: row
        for row in wave_1968_derivation["field_census_rows"]
    }
    assert {
        field: census[field]["observed_token_rows_sha256"]
        for field in ("V93", "V210", "V76", "V97", "V117")
    } == {
        "V93": (
            "0d184b17049ff03bdffe4c462131f126e771108e5588436aa0551e02fd0c80c0"
        ),
        "V210": (
            "4072529f3cab60900f04eb216e73f0ec6307aa8ed60c439dcfaf51b04018a448"
        ),
        "V76": (
            "4082fbc67ab457ddad4115b66ab785e816e20b393b195786fbd47ba384b7aa2d"
        ),
        "V97": (
            "7728fee41416e99342a836afc5ce9710f91599c333c8f533620cf2f53009b2e9"
        ),
        "V117": (
            "09422b1415d0c4b7d281ab156451fb733dc204827fa98dbe93a0e53f94065998"
        ),
    }
