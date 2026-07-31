"""Reproducibility and fail-closed tests for entry-11 adjudication."""

from __future__ import annotations

import hashlib
import json
import sys
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ARTIFACT = (
    ROOT
    / "data"
    / "external"
    / "covered_earnings_membership_adjudication_v2.json"
)
ARTIFACT_SHA256 = (
    "7306c898d044df0ce86754b8468b26e32d8696027e8dde2f7d5935d79f1abb14"
)
PDF_CAPTURE = (
    ROOT
    / "data"
    / "external"
    / "snapshots"
    / "covered_earnings_methodology_capture1"
    / "supplement2025_4b.pdf"
)

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_covered_earnings_membership_adjudication as builder  # noqa: E402


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test__adjudication__is_canonical_and_byte_reproducible():
    raw = ARTIFACT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    assert raw == builder.render()
    value = _artifact()
    builder.validate_adjudication(value)
    assert raw == builder.canonical.canonical_json_bytes(value)


def test__adjudication__binds_every_verdict_to_exact_captured_bytes():
    value = _artifact()
    locators_by_id = {
        locator["locator_id"]: locator for locator in value["source_locators"]
    }
    locator_ids = {
        locator["locator_id"] for locator in value["source_locators"]
    }
    assert len(locator_ids) == 19
    assert {row["location_type"] for row in value["source_locators"]} == {
        "html_line_and_byte_range",
        "pdf_compressed_content_stream_byte_range",
    }
    for fact in value["facts"]:
        assert fact["evidence_locator_ids"]
        assert set(fact["evidence_locator_ids"]) <= locator_ids

    expected_pdf_locators = {
        "pdf_b10_title_and_all_areas_row": (
            24,
            "46 0 R",
            169_638,
            173_740,
            "d4cf272ec1595e40e4cb31e10619d7f1a4d5ccc788f70d06c58ea968d1efca66",
            (b"Table 4.B10",),
        ),
        "pdf_b10_2023_technical_notes": (
            25,
            "48 0 R",
            174_071,
            176_401,
            "a02c9224f597e306d4ac220374fa2297c649824564fa6bc86a2ab1432b4a34f4",
            (
                b"Table 4.B10",
                b"state totals and subtotals are unduplicated counts of workers",
                b"each ty\\\rpe of employment.",
            ),
        ),
        "pdf_b11_title_headers_and_early_rows": (
            26,
            "50 0 R",
            176_721,
            180_412,
            "4ddb1cc58abcb6c0f342b56ee8b36429797bb1fe0f8829d18c5e14025d132422",
            (b"Table 4.B11",),
        ),
        "pdf_b11_later_rows_and_notes": (
            27,
            "52 0 R",
            180_740,
            184_070,
            "664050a4b71544eefef56366ee4bb1bb629383bcff365c1068e84682beda7e23",
            (
                b"Table 4.B11",
                b"Workers with earnings in both wage and salary employment",
                b"counted in each type of employment but only on)-5.9 "
                b"(ce in the total.",
            ),
        ),
    }
    pdf_raw = PDF_CAPTURE.read_bytes()
    for locator_id, expected in expected_pdf_locators.items():
        page, content_object, byte_start, byte_end, range_sha256, anchors = (
            expected
        )
        locator = locators_by_id[locator_id]
        assert locator["pdf_page"] == page
        assert locator["content_object"] == content_object
        assert locator["byte_start"] == byte_start
        assert locator["byte_end"] == byte_end
        assert locator["range_sha256"] == range_sha256
        decoded = zlib.decompress(pdf_raw[byte_start:byte_end])
        assert all(anchor in decoded for anchor in anchors)

    b12_start, b12_end = 184_687, 188_746
    b12_sha256 = (
        "533efd86dcdf006c01b77cd6469099d0c7cc395d2b4702ef34e9601f33ffbc12"
    )
    b12_bytes = pdf_raw[b12_start:b12_end]
    assert hashlib.sha256(b12_bytes).hexdigest() == b12_sha256
    assert b"Table 4.B12" in zlib.decompress(b12_bytes)
    pdf_locators = [
        locator
        for locator in value["source_locators"]
        if locator["location_type"]
        == "pdf_compressed_content_stream_byte_range"
    ]
    assert all(
        locator["content_object"] != "55 0 R" for locator in pdf_locators
    )
    assert all(
        (locator["byte_start"], locator["byte_end"]) != (b12_start, b12_end)
        for locator in pdf_locators
    )
    assert all(
        locator["range_sha256"] != b12_sha256 for locator in pdf_locators
    )


def test__candidate_source_dispositions__cover_all_five_named_sources():
    rows = _artifact()["candidate_source_dispositions"]
    assert [row["source_document_id"] for row in rows] == [
        "ssa_glossary",
        "ssa_oasdi_program_reference",
        "ssa_eedata_2023_intro",
        "ssa_supplement_2025_highlights",
        "ssa_supplement_2025_4b_pdf",
    ]
    assert all(row["evidence_locator_ids"] for row in rows)
    assert rows[0]["verdict"] == "does_not_establish_membership_facts"
    assert (
        "glossary_uncaptured_dynamic_definitions"
        in rows[0]["evidence_locator_ids"]
    )
    assert rows[3]["verdict"] == "does_not_establish_membership_facts"


def test__model_authority_locators__re_resolve_repo_lines_and_bytes():
    value = _artifact()
    locators = value["repo_authority_locators"]
    assert len(locators) == len(builder.REPO_AUTHORITY_LOCATOR_SPECS)
    locator_ids = {row["locator_id"] for row in locators}
    for authority in value["registration_authority_adjudications"]:
        assert authority["citations"]
        assert set(authority["citations"]) <= locator_ids
    builder.validate_adjudication(value)


def test__adjudication__covers_the_complete_recheck_shopping_list():
    value = _artifact()
    by_group = {
        group: [row for row in value["facts"] if row["group"] == group]
        for group in ("b2_wage", "b2_se", "b11")
    }
    assert {group: len(rows) for group, rows in by_group.items()} == {
        "b2_wage": 8,
        "b2_se": 11,
        "b11": 11,
    }
    assert {row["fact_id"] for row in by_group["b2_wage"]} >= {
        "b2_wage_exact_c11_predicate",
        "b2_wage_zero_treatment",
        "b2_wage_below_threshold_treatment",
        "b2_wage_same_type_dedup",
        "b2_wage_cap_treatment",
        "b2_wage_multiple_employer_treatment",
        "b2_wage_c5_c11_population_identity",
        "b2_wage_historical_continuity",
    }
    assert {row["fact_id"] for row in by_group["b2_se"]} >= {
        "b2_se_c8_signed_ordering",
        "b2_se_threshold_and_cap_ordering",
        "b2_se_loss_netting",
        "b2_se_loss_only_membership",
        "b2_se_zero_and_net_zero_membership",
        "b2_se_below_threshold_membership",
        "b2_se_exact_c12_predicate",
        "b2_se_c8_c12_population_identity",
        "b2_se_aggregation_and_dedup",
        "b2_se_wage_first_exhaustion",
        "b2_se_historical_continuity",
    }
    assert {row["fact_id"] for row in by_group["b11"]} >= {
        "b11_exact_t_definition",
        "b11_exact_w_definition",
        "b11_exact_s_definition",
        "b11_t_unduplicated_union",
        "b11_zero_loss_threshold_cases",
        "b11_cap_and_wage_exhaustion",
        "b11_same_type_wage_dedup",
        "b11_same_type_se_dedup",
        "b11_timing",
        "b11_geography",
        "b11_historical_continuity",
    }


def test__adjudication__records_exact_family_fail_closed_lists():
    rows = _artifact()["family_dispositions"]
    assert [row["target_family"] for row in rows] == list(
        builder.TARGET_FAMILY_FACT_IDS
    )
    assert len(rows) == 14
    assert {row["verdict"] for row in rows} == {"fail_closed"}
    assert all(row["missing_fact_list"] for row in rows)
    by_family = {row["target_family"]: row for row in rows}
    assert (
        "exact_c11_person_year_predicate_for_every_historical_regime"
        in by_family["b2_wage_total_intensity"]["missing_source_fact_ids"]
    )
    assert (
        "c8_signed_negative_and_seca_factor_stage"
        in by_family["b2_se_total_intensity"]["missing_source_fact_ids"]
    )
    assert (
        "exact_annual_unique_person_definition_T_1968_2022"
        in by_family["b11_dual_type_worker_share"]["missing_source_fact_ids"]
    )
    assert (
        by_family["b2_wage_taxable_fraction"]["missing_source_fact_ids"] == []
    )
    accounting = by_family["b11_contributions_component_reconciliation"]
    assert accounting["missing_registration_authority_ids"] == list(
        builder.COMMON_REGISTRATION_AUTHORITY_IDS
    )
    assert (
        builder.MEMBERSHIP_SELECTOR_AUTHORITY_ID
        not in accounting["missing_registration_authority_ids"]
    )


def test__model_authorities__resolve_exact_repo_defined_fields_only():
    rows = _artifact()["registration_authority_adjudications"]
    assert len(rows) == 5
    by_id = {row["authority_id"]: row for row in rows}
    assert by_id["model_weight_field"] == {
        "authority_id": "model_weight_field",
        "status": "resolved_from_committed_first_estimates_authority",
        "resolved_value": "weight",
        "reason_id": (
            "first_estimates_fixed_start_wave_psid_cross_sectional_weight_v1"
        ),
        "citations": [
            "first_estimates_weight_law",
            "m6_anchor_weight_implementation",
            "ledger_weight_implementation",
        ],
    }
    assert by_id["model_universe_id"]["resolved_value"] is None
    assert by_id["model_weight_source_sha256"]["resolved_value"] is None
    assert by_id["denominator_and_joint_analytic_selectors"][
        "resolved_value"
    ] == {
        "covered_share_denominator_selector_id": (
            "registered_covered_share_denominator_indicator"
        ),
        "b2_b11_membership_selector_ids": [
            "b2_wage_worker_membership_probability_analytic",
            "b2_se_worker_membership_probability_analytic",
            "b11_wage_only_worker_probability_analytic",
            "b11_se_only_worker_probability_analytic",
            "b11_dual_type_worker_probability_analytic",
            "b11_any_worker_probability_analytic",
        ],
        "joint_probability_reduction": (
            "analytic_joint_state_within_projection_draw"
        ),
        "membership_predicates": None,
    }
    assert by_id["universe_concordance"]["status"] == "registration_required"


def test__pdf_extraction__is_recorded_but_never_used_as_evidence():
    method = _artifact()["pdf_extraction_method"]
    assert method["tool"] == "Poppler pdftotext"
    assert method["tool_version"] == "26.04.0"
    assert method["derived_text_retained"] is False
    assert method["derived_text_evidentiary_status"] == (
        "locator_only_not_evidence"
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("locator", "source locator"),
        ("repo_locator", "repo authority locator"),
        ("candidate", "candidate source dispositions"),
        ("fact", "fact table"),
        ("family", "family fail-closed"),
        ("authority", "registration authority"),
    ),
)
def test__adjudication__rejects_coherently_rehashed_corruption(
    mutation,
    message,
):
    value = _artifact()
    if mutation == "locator":
        value["source_locators"][0]["byte_start"] += 1
    elif mutation == "repo_locator":
        value["repo_authority_locators"][0]["line_start"] += 1
    elif mutation == "candidate":
        value["candidate_source_dispositions"][0]["verdict"] = "accepted"
    elif mutation == "fact":
        value["facts"][0]["verdict"] = "established"
    elif mutation == "family":
        value["family_dispositions"][0]["verdict"] = "open"
    else:
        value["registration_authority_adjudications"][1][
            "resolved_value"
        ] = "person_weight"
    value["integrity"]["content_sha256"] = builder._content_sha256(value)
    with pytest.raises(ValueError, match=message):
        builder.validate_adjudication(value)


@pytest.mark.parametrize(
    ("mutation", "accepted"),
    [
        ("equal_bytes", True),
        ("strict_append", True),
        ("shorter_bytes", False),
        ("equal_length_outside_cited_ranges", False),
        ("equal_length_inside_cited_range", False),
        ("lf_to_crlf", False),
    ],
)
def test__append_only_prefix__accepts_only_exact_prefix_extensions(
    mutation,
    accepted,
):
    committed_path = "docs/design/first_estimates_report.md"
    adjudicated = builder._adjudicated_source_bytes(committed_path)
    # Cited ranges for this document include bytes 3462-3959; byte 0 is
    # outside every cited range.
    if mutation == "equal_bytes":
        live = adjudicated
    elif mutation == "strict_append":
        live = adjudicated + b"\nAppended amendment text.\n"
    elif mutation == "shorter_bytes":
        live = adjudicated[:-1]
    elif mutation == "equal_length_outside_cited_ranges":
        live = bytes([adjudicated[0] ^ 1]) + adjudicated[1:]
    elif mutation == "equal_length_inside_cited_range":
        live = (
            adjudicated[:3500]
            + bytes([adjudicated[3500] ^ 1])
            + adjudicated[3501:]
        )
    else:
        live = adjudicated.replace(b"\n", b"\r\n")
    assert len(live) > 0
    if accepted:
        builder._verify_append_only_prefix(committed_path, adjudicated, live)
    else:
        with pytest.raises(ValueError, match="append-only authority prefix"):
            builder._verify_append_only_prefix(
                committed_path, adjudicated, live
            )
