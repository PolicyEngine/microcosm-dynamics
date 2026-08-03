"""Authenticated-corpus vectors for the revision-9 source compiler."""

from pathlib import Path

import pytest

from populace_dynamics.data import psid_source_compiler as compiler
from populace_dynamics.data.psid_source_classifier import (
    classify_complete_corpus,
)

PSID_ROOT = Path("~/PolicyEngine/psid-data").expanduser()


@pytest.fixture(scope="module")
def evidence_corpus():
    return compiler.load_authenticated_evidence(
        psid_root=PSID_ROOT,
        authenticate_source_files=True,
    )


@pytest.fixture(scope="module")
def all_raw_derivations(evidence_corpus):
    return compiler.derive_all_raw_censuses(evidence_corpus, PSID_ROOT)


@pytest.fixture(scope="module")
def complete_classification(evidence_corpus, all_raw_derivations):
    return classify_complete_corpus(evidence_corpus, all_raw_derivations)


@pytest.fixture(scope="module")
def wave_1968_derivation(all_raw_derivations):
    return next(
        row
        for row in all_raw_derivations
        if any(
            census["interview_wave"] == 1968
            for census in row["field_census_rows"]
        )
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


def test_a6_r01_through_r11_and_complete_ratified_census(
    evidence_corpus,
    all_raw_derivations,
    complete_classification,
):
    census_by_key = {
        (row["interview_wave"], row["raw_field_id"]): row
        for derivation in all_raw_derivations
        for row in derivation["field_census_rows"]
    }
    vector_digests = {
        (1968, "V93"): (
            "0d184b17049ff03bdffe4c462131f126e771108e5588436aa0551e02fd0c80c0"
        ),
        (1979, "V6302"): (
            "7bf8f994c2cbaa804238ecfd051afee9a801119574c73b6ce14abe7fe66006e0"
        ),
        (1988, "V15133"): (
            "c41db6073cbcbc51b73e5d035f611a4f13314b713017bf640685441bf5b03c49"
        ),
        (1968, "V210"): (
            "4072529f3cab60900f04eb216e73f0ec6307aa8ed60c439dcfaf51b04018a448"
        ),
        (1968, "V76"): (
            "4082fbc67ab457ddad4115b66ab785e816e20b393b195786fbd47ba384b7aa2d"
        ),
        (1979, "V6363"): (
            "a56fa8d49cc90e874cd900d689302fe91138dbaaa895db6731e61fbe152989bf"
        ),
        (1969, "V945"): (
            "a6b22c77d629041af436acce61508baf1b40d6eaf8be7089c1b529520873c9e5"
        ),
        (1968, "V97"): (
            "7728fee41416e99342a836afc5ce9710f91599c333c8f533620cf2f53009b2e9"
        ),
        (1985, "V11811"): (
            "e7c597b7362015d7443a5eb921efce6ea041df1f795bd4e2cbb4e75a1106445e"
        ),
        (1968, "V117"): (
            "09422b1415d0c4b7d281ab156451fb733dc204827fa98dbe93a0e53f94065998"
        ),
        (1985, "V11812"): (
            "294a0d815f3fa92ddcf3bd79e2578e57acf6b0926143116f4f8f7459a80e29ce"
        ),
    }
    assert {
        key: census_by_key[key]["observed_token_rows_sha256"]
        for key in vector_digests
    } == vector_digests

    result = complete_classification
    assert result["denominator_sha256"] == (
        "7e497f20e05cbdad384daece86d4aa08b16587b83cb6290193b6fdc28705b764"
    )
    assert result["count_array_sha256"] == (
        "421105abb63991c3cc1d14d15c98ff68803f7e50dd992107fd797a01ec346624"
    )
    assert result["ordered_assignment_sha256"] == (
        "5c9020ad92ced4916dd1152f0ce06cc276878a0ca312cd34f9d25c3c3977e72e"
    )
    status_by_key = {
        (row["interview_wave"], row["raw_field_id"]): row["derivation_status"]
        for row in result["classification_rows"]
    }
    assert [status_by_key[key] for key in vector_digests] == [
        "compiled_source_numeric_grammar",
        "compiled_source_numeric_grammar",
        (
            "compiled_source_numeric_grammar_"
            "padding_underdetermined_exact_replay"
        ),
        (
            "compiled_source_numeric_grammar_"
            "padding_underdetermined_exact_replay"
        ),
        "compiled_source_numeric_grammar",
        "compiled_source_numeric_grammar",
        "compiled_source_numeric_grammar_partial_range_exact_replay",
        (
            "compiled_source_numeric_grammar_"
            "padding_underdetermined_exact_replay"
        ),
        "value_code_range_physical_rendering_unestablished",
        (
            "compiled_source_numeric_grammar_"
            "finite_domain_arm_ambiguous_exact_replay"
        ),
        "value_code_range_physical_rendering_unestablished",
    ]


def test_a6_r01_through_r11_field_derivation_details(
    complete_classification,
):
    details = {
        (row["interview_wave"], row["raw_field_id"]): row
        for row in complete_classification["field_details"]
    }
    expectations = {
        (1968, "V93"): (
            4_802,
            "unsigned_ascii_integer",
            "left_ascii_space_padding",
        ),
        (1979, "V6302"): (
            6_373,
            "unsigned_ascii_integer",
            "left_ascii_space_padding",
        ),
        (1988, "V15133"): (
            7_114,
            "unsigned_ascii_integer",
            "padding_arm_underdetermined_width_one_exact_replay_v1",
        ),
        (1968, "V210"): (
            512,
            "unsigned_literal_ascii_decimal",
            (
                "padding_arm_underdetermined_no_padding_capacity_"
                "exact_replay_v1"
            ),
        ),
        (1968, "V76"): (
            4_802,
            "leading_ascii_minus_signed_integer",
            "left_ascii_space_padding",
        ),
        (1979, "V6363"): (
            6_373,
            "unsigned_literal_ascii_decimal",
            "left_ascii_space_padding",
        ),
        (1969, "V945"): (
            4_460,
            "leading_ascii_minus_signed_literal_ascii_decimal",
            "left_ascii_space_padding",
        ),
        (1968, "V97"): (
            4_802,
            "unsigned_ascii_integer",
            (
                "padding_arm_underdetermined_no_padding_capacity_"
                "exact_replay_v1"
            ),
        ),
        (1985, "V11811"): (0, None, None),
        (1968, "V117"): (
            4_799,
            "unsigned_ascii_integer",
            (
                "padding_arm_underdetermined_finite_domain_arm_"
                "ambiguous_exact_replay_v1"
            ),
        ),
        (1985, "V11812"): (0, None, None),
    }
    assert {
        key: (
            details[key]["nonmissing_observation_count"],
            details[key]["selected_token_form"],
            details[key]["selected_arm"],
        )
        for key in expectations
    } == expectations

    assert details[(1968, "V93")]["padding_arm_candidate_results"] == [
        {
            "profile_kind": "zero_left_padding",
            "accepted_observation_count": 3_733,
            "diagnostic_observation_count": 1_069,
            "rejected_observation_count": 1_069,
            "status": "fail",
        },
        {
            "profile_kind": "left_ascii_space_padding",
            "accepted_observation_count": 4_802,
            "diagnostic_observation_count": 1_069,
            "rejected_observation_count": 0,
            "status": "pass",
        },
    ]
    v945_ranges = details[(1969, "V945")]["range_renderability_counts"]
    assert sum(row["source_member_count"] for row in v945_ranges) == 692_700
    assert sum(row["renderable_member_count"] for row in v945_ranges) == (
        429_270
    )
    assert sum(row["unrenderable_member_count"] for row in v945_ranges) == (
        263_430
    )
    assert details[(1968, "V117")]["range_renderability_counts"] == [
        {
            "source_entry_index": 0,
            "source_member_count": 96,
            "renderable_member_count": 96,
            "arm_invariant_renderable_member_count": 87,
            "arm_ambiguous_renderable_member_count": 9,
            "unrenderable_member_count": 0,
        }
    ]
    for key in ((1985, "V11811"), (1985, "V11812")):
        assert details[key]["token_form_candidate_results"] == []
        assert details[key]["padding_arm_candidate_results"] == []
    v11812_literals = {
        row["source_value_lexeme"]: row
        for row in details[(1985, "V11812")]["registered_literals"]
    }
    assert v11812_literals["0"]["raw_token_hex"] == "2030"
    assert v11812_literals["1"] == {
        "source_entry_index": 1,
        "source_value_lexeme": "1",
        "typed_disposition": "ordinary",
        "raw_token_hex": None,
        "producer_transition": "zero_count_physical_unestablished",
        "final_disposition": "physical_rendering_unestablished",
    }
