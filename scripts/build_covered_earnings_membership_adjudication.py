"""Build the byte-resolved entry-11 worker-membership adjudication.

The adjudication reads only the five committed methodology captures.  HTML
facts resolve to exact inclusive line ranges and half-open byte ranges.  PDF
facts resolve to exact compressed content-stream byte ranges in the pinned
PDF.  Poppler text extraction was used only to locate and visually inspect
the relevant pages; no derived text is retained or treated as evidence.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import build_ssa_level_anchors as canonical

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = (
    ROOT
    / "data"
    / "external"
    / "snapshots"
    / "covered_earnings_methodology_capture1"
)
CAPTURE_MANIFEST_PATH = SNAPSHOT_DIR / "capture_manifest.txt"
OUT_PATH = (
    ROOT
    / "data"
    / "external"
    / "covered_earnings_membership_adjudication_v2.json"
)

SCHEMA_VERSION = "covered_earnings_membership_adjudication.v2"
ADJUDICATION_ID = "entry11_unit1b_membership_readjudication_v2"
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"

SOURCE_SPECS = {
    "ssa_glossary": {
        "filename": "glossary.html",
        "sha256": (
            "94fe0175a7de2c98087b18f1ecc22fa67ae62e7c5910725998deab0a3b64a6db"
        ),
        "size_bytes": 20_336,
        "url": "https://www.ssa.gov/policy/about/glossary.html",
    },
    "ssa_oasdi_program_reference": {
        "filename": "oasdi-reference.html",
        "sha256": (
            "32048535a2baf80ff7a8f4c3c89012a51b414e3a35bafcb3510e031eec758688"
        ),
        "size_bytes": 257_526,
        "url": "https://www.ssa.gov/policy/about/oasdi-reference.html",
    },
    "ssa_eedata_2023_intro": {
        "filename": "eedata2023_intro.html",
        "sha256": (
            "b8802cfce61af1d053830ed62c1d46559df1617c87b4264f0ec81eff5bea048a"
        ),
        "size_bytes": 15_591,
        "url": (
            "https://www.ssa.gov/policy/docs/statcomps/eedata_sc/2023/"
            "intro.html"
        ),
    },
    "ssa_supplement_2025_highlights": {
        "filename": "supplement2025_highlights.html",
        "sha256": (
            "b02128d43ac22300f0378c1ad68deb51b2f9469734d1637213f7a830424f18c0"
        ),
        "size_bytes": 22_700,
        "url": (
            "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/"
            "highlights.html"
        ),
    },
    "ssa_supplement_2025_4b_pdf": {
        "filename": "supplement2025_4b.pdf",
        "sha256": (
            "6f1faedb2fdb85b775a3c70eea404a7940d8077abd196614767b44bd0bce130e"
        ),
        "size_bytes": 225_789,
        "url": (
            "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/"
            "4b.pdf"
        ),
    },
}

HTML_LOCATOR_SPECS = (
    (
        "glossary_scope_limitations",
        "ssa_glossary",
        68,
        82,
        "recent-publication scope and publication-specific-note warning",
    ),
    (
        "glossary_uncaptured_dynamic_definitions",
        "ssa_glossary",
        107,
        126,
        "empty definition list and uncaptured runtime JSON request",
    ),
    (
        "oasdi_incomplete_history_disclaimer",
        "ssa_oasdi_program_reference",
        46,
        49,
        "current-framework scope and explicit incomplete-history warning",
    ),
    (
        "oasdi_current_coverage_and_tax_context",
        "ssa_oasdi_program_reference",
        68,
        87,
        "current FICA/SECA, cap, multi-employer, and threshold context",
    ),
    (
        "oasdi_selected_historical_coverage_changes",
        "ssa_oasdi_program_reference",
        91,
        313,
        "selected enacted coverage changes rather than a complete regime map",
    ),
    (
        "oasdi_current_employee_and_seca_rules",
        "ssa_oasdi_program_reference",
        389,
        397,
        "current first-dollar exceptions, cap, and SECA-factor history",
    ),
    (
        "eedata_2023_identity",
        "ssa_eedata_2023_intro",
        5,
        5,
        "publication title limiting the methodology to the 2023 report",
    ),
    (
        "eedata_2023_tax_rules",
        "ssa_eedata_2023_intro",
        38,
        44,
        "2023 wage-first, cap, multi-employer, SECA, threshold, and geography",
    ),
    (
        "eedata_2023_counting_and_sources",
        "ssa_eedata_2023_intro",
        45,
        53,
        "2023 residence, dual-type, CWHS, person-count, and source rules",
    ),
    (
        "supplement_highlights_2024_context",
        "ssa_supplement_2025_highlights",
        39,
        50,
        "2024 headline worker and earnings totals without membership method",
    ),
)

PDF_LOCATOR_SPECS = (
    (
        "pdf_b2_title_headers",
        3,
        "4 0 R",
        94_519,
        98_844,
        "150a1bc2e35fd6e3b13582d511170b7bdc879de933953dd0889ce7bb00c8128d",
        "Table 4.B2 title, headers, and early rows",
    ),
    (
        "pdf_b2_later_rows_and_notes",
        4,
        "6 0 R",
        99_172,
        103_058,
        "fa096e1ac41d187fa4db37312bd2d3a38c1d5cf4f17581c56ccedb33ae59d87b",
        "Table 4.B2 later rows, footnotes, and sources",
    ),
    (
        "pdf_b7_positive_bins_page_1",
        15,
        "28 0 R",
        140_586,
        143_533,
        "698345398c088dfb5e4862daf6c60bef1153943a95619d7d176dea24f93c74fc",
        "Table 4.B7 post-1992 positive wage bands, first page",
    ),
    (
        "pdf_b7_positive_bins_page_2",
        16,
        "30 0 R",
        143_864,
        146_727,
        "37237cff66f36f8adad73066c1c29ed8ce52b05493016eb70c2b5d183351b790",
        "Table 4.B7 post-1992 positive wage bands, second page",
    ),
    (
        "pdf_b7_positive_bins_page_3",
        17,
        "32 0 R",
        147_058,
        149_626,
        "87fb061b85cdf2b0e680f1b5cb559d6a96febb471fcf08771267987691b991d7",
        "Table 4.B7 post-1992 positive wage bands, third page",
    ),
    (
        "pdf_b10_title_and_all_areas_row",
        24,
        "48 0 R",
        174_071,
        176_401,
        "a02c9224f597e306d4ac220374fa2297c649824564fa6bc86a2ab1432b4a34f4",
        "Table 4.B10 title, headers, and 2023 all-areas row",
    ),
    (
        "pdf_b10_2023_technical_notes",
        25,
        "50 0 R",
        176_721,
        180_412,
        "4ddb1cc58abcb6c0f342b56ee8b36429797bb1fe0f8829d18c5e14025d132422",
        "Table 4.B10 2023 CWHS, geography, and unduplication notes",
    ),
    (
        "pdf_b11_title_headers_and_early_rows",
        26,
        "52 0 R",
        180_740,
        184_070,
        "664050a4b71544eefef56366ee4bb1bb629383bcff365c1068e84682beda7e23",
        "Table 4.B11 title, T/W/S headers, and early rows",
    ),
    (
        "pdf_b11_later_rows_and_notes",
        27,
        "55 0 R",
        184_687,
        188_746,
        "533efd86dcdf006c01b77cd6469099d0c7cc395d2b4702ef34e9601f33ffbc12",
        "Table 4.B11 later rows, dual-type note, and sources",
    ),
)

PDF_EXTRACTION_METHOD = {
    "tool": "Poppler pdftotext",
    "tool_version": "26.04.0",
    "command": (
        "pdftotext -layout -enc UTF-8 "
        "data/external/snapshots/covered_earnings_methodology_capture1/"
        "supplement2025_4b.pdf <temporary-output-path>"
    ),
    "visual_check": (
        "pdftoppm 26.04.0 rendered relevant pages for human inspection"
    ),
    "derived_text_retained": False,
    "derived_text_evidentiary_status": "locator_only_not_evidence",
    "fact_binding": (
        "pinned_pdf_sha256_size_page_content_object_and_compressed_stream_"
        "byte_range"
    ),
}


def _fact(
    fact_id: str,
    group: str,
    requirement: str,
    verdict: str,
    evidence_locator_ids: Sequence[str],
    established_scope: str,
    limitation: str,
    missing_fact_id: str | None,
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "group": group,
        "requirement": requirement,
        "verdict": verdict,
        "evidence_locator_ids": list(evidence_locator_ids),
        "established_scope": established_scope,
        "limitation": limitation,
        "missing_fact_id": missing_fact_id,
    }


FACTS = (
    _fact(
        "b2_wage_exact_c11_predicate",
        "b2_wage",
        "exact c11 person-year membership predicate",
        "partially_established_required_fact_unestablished",
        ("pdf_b2_title_headers", "pdf_b2_later_rows_and_notes"),
        "annual wage-type marginal and dual-type inclusion",
        "zero, threshold, and same-type consolidation remain undefined",
        "exact_c11_person_year_predicate_for_every_historical_regime",
    ),
    _fact(
        "b2_wage_zero_treatment",
        "b2_wage",
        "zero and correction-record treatment",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b7_positive_bins_page_1",
            "pdf_b7_positive_bins_page_2",
            "pdf_b7_positive_bins_page_3",
        ),
        "post-1992 B7 wage distributions use positive bands and a cap band",
        "no byte extends the rule to 1968-1991 or correction records",
        "zero_wage_record_membership_for_1968_1991_and_historical_continuity",
    ),
    _fact(
        "b2_wage_below_threshold_treatment",
        "b2_wage",
        "below-threshold wage membership in every regime",
        "unestablished",
        (
            "oasdi_current_coverage_and_tax_context",
            "oasdi_current_employee_and_seca_rules",
            "oasdi_incomplete_history_disclaimer",
        ),
        "current exceptions and selected historical coverage changes",
        "no exact historical threshold schedule is captured or tied to c11",
        "exact_applicable_wage_coverage_threshold_membership_for_every_regime",
    ),
    _fact(
        "b2_wage_same_type_dedup",
        "b2_wage",
        "same-type employer and job deduplication",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b10_title_and_all_areas_row",
            "pdf_b10_2023_technical_notes",
            "eedata_2023_counting_and_sources",
        ),
        "the separate 2023 CWHS/B10 report is unduplicated within type",
        "no continuity bridge binds the 2023 rule to historical B2",
        "same_type_multiple_employer_and_multiple_job_deduplication_for_all_years",
    ),
    _fact(
        "b2_wage_cap_treatment",
        "b2_wage",
        "cap and maximum-earner membership",
        "established",
        (
            "pdf_b2_later_rows_and_notes",
            "pdf_b7_positive_bins_page_1",
            "oasdi_current_employee_and_seca_rules",
        ),
        "c5 includes estimated wages above the limit and post-1992 maximum "
        "earners remain in the wage count",
        "does not independently establish historical employer deduplication",
        None,
    ),
    _fact(
        "b2_wage_multiple_employer_treatment",
        "b2_wage",
        "multi-employer consolidation and refund treatment",
        "partially_established_required_fact_unestablished",
        (
            "oasdi_current_coverage_and_tax_context",
            "eedata_2023_tax_rules",
            "pdf_b10_2023_technical_notes",
        ),
        "current and 2023 employer-level withholding and excess-tax context",
        "tax accounting does not define historical c11 person consolidation",
        "historical_multiple_employer_membership_and_refund_method_with_effective_dates",
    ),
    _fact(
        "b2_wage_c5_c11_population_identity",
        "b2_wage",
        "exact coextensiveness of c5 dollars and c11 people",
        "unestablished",
        ("pdf_b2_title_headers", "pdf_b2_later_rows_and_notes"),
        "the amount, count, and displayed average occupy one wage group",
        "grouping and aggregate arithmetic do not settle edge-case populations",
        "exact_c5_amount_population_equals_c11_unique_worker_population",
    ),
    _fact(
        "b2_wage_historical_continuity",
        "b2_wage",
        "effective dates and continuity for every method change",
        "unestablished",
        (
            "oasdi_selected_historical_coverage_changes",
            "oasdi_incomplete_history_disclaimer",
            "pdf_b2_later_rows_and_notes",
        ),
        "selected enacted changes and one long displayed B2 series",
        "the Program Reference expressly omits historical changes",
        "effective_date_and_historical_method_continuity_map",
    ),
    _fact(
        "b2_se_c8_signed_ordering",
        "b2_se",
        "whether c8 is signed and its order relative to the SECA factor",
        "unestablished",
        (
            "pdf_b2_title_headers",
            "pdf_b2_later_rows_and_notes",
            "eedata_2023_tax_rules",
            "oasdi_current_employee_and_seca_rules",
        ),
        "c8 is labeled reported self-employment net earnings; current "
        "factor context and its 1990 transition are supplied",
        "no byte says whether negatives survive or whether c8 is pre-factor",
        "c8_signed_negative_and_seca_factor_stage",
    ),
    _fact(
        "b2_se_threshold_and_cap_ordering",
        "b2_se",
        "c8 order relative to threshold and cap",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b2_later_rows_and_notes",
            "eedata_2023_tax_rules",
            "oasdi_current_coverage_and_tax_context",
        ),
        "c8 is distinct from capped taxable SE; 2023 threshold law is stated",
        "c8 threshold staging and historical continuity are not stated",
        "c8_threshold_stage_and_historical_continuity",
    ),
    _fact(
        "b2_se_loss_netting",
        "b2_se",
        "within-person and cross-business loss netting",
        "unestablished",
        ("pdf_b2_later_rows_and_notes", "eedata_2023_counting_and_sources"),
        "Schedule SE is identified as an input in the 2023 report",
        "no captured byte defines business-component aggregation or loss order",
        "within_and_cross_business_loss_netting_rule",
    ),
    _fact(
        "b2_se_loss_only_membership",
        "b2_se",
        "loss-only filer c8/c12 treatment",
        "unestablished",
        ("pdf_b2_title_headers", "pdf_b2_later_rows_and_notes"),
        "B2 displays net-earnings dollars and self-employed worker counts",
        "no source says whether loss-only filers contribute or enter c12",
        "loss_only_c8_c12_membership",
    ),
    _fact(
        "b2_se_zero_and_net_zero_membership",
        "b2_se",
        "exact-zero and cross-component net-zero treatment",
        "unestablished",
        ("pdf_b2_title_headers", "pdf_b2_later_rows_and_notes"),
        "the table is structurally scoped to workers with taxable earnings",
        "structural wording is not an executable zero or net-zero predicate",
        "exact_zero_and_net_zero_c8_c12_treatment",
    ),
    _fact(
        "b2_se_below_threshold_membership",
        "b2_se",
        "below-threshold c8/c12 treatment",
        "partially_established_required_fact_unestablished",
        (
            "eedata_2023_identity",
            "eedata_2023_tax_rules",
            "oasdi_current_coverage_and_tax_context",
            "oasdi_incomplete_history_disclaimer",
        ),
        "the 2023 report states the $400 taxability result",
        "it neither binds B2 nor establishes every historical regime",
        "below_threshold_c8_c12_treatment_for_every_regime",
    ),
    _fact(
        "b2_se_exact_c12_predicate",
        "b2_se",
        "exact c12 person-year predicate",
        "partially_established_required_fact_unestablished",
        ("pdf_b2_title_headers", "pdf_b2_later_rows_and_notes"),
        "c12 is the displayed total number in the self-employed type",
        "loss, zero, threshold, aggregation, and exhausted-cap cases remain",
        "exact_c12_person_year_predicate",
    ),
    _fact(
        "b2_se_c8_c12_population_identity",
        "b2_se",
        "exact coextensiveness of c8 dollars and c12 people",
        "unestablished",
        ("pdf_b2_title_headers", "pdf_b2_later_rows_and_notes"),
        "the displayed average is structurally c8 divided by c12",
        "the sources do not equate edge-case amount and count populations",
        "exact_c8_amount_population_equals_c12_unique_worker_population",
    ),
    _fact(
        "b2_se_aggregation_and_dedup",
        "b2_se",
        "business/component aggregation and same-type deduplication",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b10_2023_technical_notes",
            "eedata_2023_counting_and_sources",
            "pdf_b2_later_rows_and_notes",
        ),
        "the separate 2023 B10 system is unduplicated within type",
        "no byte supplies B2 historical business aggregation or continuity",
        "business_component_aggregation_and_same_type_dedup_for_all_b2_years",
    ),
    _fact(
        "b2_se_wage_first_exhaustion",
        "b2_se",
        "c12 membership when wages exhaust the shared cap",
        "partially_established_required_fact_unestablished",
        ("eedata_2023_tax_rules", "pdf_b2_later_rows_and_notes"),
        "the 2023 report establishes wage-first taxable-earnings ordering",
        "it does not state c12 membership after zero residual taxable SE",
        "c12_membership_when_wages_exhaust_shared_cap",
    ),
    _fact(
        "b2_se_historical_continuity",
        "b2_se",
        "complete SE computation and membership regime map",
        "partially_established_required_fact_unestablished",
        (
            "oasdi_selected_historical_coverage_changes",
            "oasdi_current_employee_and_seca_rules",
            "oasdi_incomplete_history_disclaimer",
        ),
        "selected SE coverage changes and the 1990 factor transition",
        "loss, threshold, aggregation, dedup, and count continuity are absent",
        "complete_se_effective_date_and_methodology_continuity_map",
    ),
    _fact(
        "b11_exact_t_definition",
        "b11",
        "exact annual unique-person T definition",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b11_title_headers_and_early_rows",
            "pdf_b11_later_rows_and_notes",
        ),
        "T is the displayed annual total and is cross-type unduplicated",
        "same-type uniqueness and the complete person-year predicate are absent",
        "exact_annual_unique_person_definition_T_1968_2022",
    ),
    _fact(
        "b11_exact_w_definition",
        "b11",
        "exact annual unique-person W definition",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b11_title_headers_and_early_rows",
            "pdf_b10_2023_technical_notes",
        ),
        "W is the displayed wage-worker marginal; B10 is 2023-unduplicated",
        "the B10 rule cannot be transferred to historical B11",
        "exact_annual_unique_person_definition_W_1968_2022",
    ),
    _fact(
        "b11_exact_s_definition",
        "b11",
        "exact annual unique-person S definition",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b11_title_headers_and_early_rows",
            "pdf_b10_2023_technical_notes",
        ),
        "S is the displayed SE-worker marginal; B10 is 2023-unduplicated",
        "historical business aggregation and unique-person rules are absent",
        "exact_annual_unique_person_definition_S_1968_2022",
    ),
    _fact(
        "b11_t_unduplicated_union",
        "b11",
        "T is the unduplicated union of W and S",
        "established",
        ("pdf_b11_later_rows_and_notes",),
        "dual-type workers enter both marginals and only once in T",
        "does not settle either marginal's same-type predicate",
        None,
    ),
    _fact(
        "b11_zero_loss_threshold_cases",
        "b11",
        "zero, loss-only, net-zero, and threshold membership",
        "unestablished",
        (
            "pdf_b11_later_rows_and_notes",
            "eedata_2023_tax_rules",
            "oasdi_current_coverage_and_tax_context",
            "oasdi_incomplete_history_disclaimer",
        ),
        "current threshold context exists outside B11",
        "no captured byte defines these B11 cases across 1968-2022",
        "zero_loss_net_zero_and_threshold_membership_all_historical_regimes",
    ),
    _fact(
        "b11_cap_and_wage_exhaustion",
        "b11",
        "cap membership including wage-exhausted SE",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b11_later_rows_and_notes",
            "eedata_2023_tax_rules",
            "oasdi_current_coverage_and_tax_context",
        ),
        "the annual cap and current wage-first order are established",
        "S membership after wages exhaust the cap is not established",
        "cap_membership_including_wage_exhausts_cap_all_historical_regimes",
    ),
    _fact(
        "b11_same_type_wage_dedup",
        "b11",
        "same-type wage-job and employer deduplication",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b10_2023_technical_notes",
            "eedata_2023_counting_and_sources",
            "pdf_b11_later_rows_and_notes",
        ),
        "the separate 2023 B10/CWHS counts are unduplicated within type",
        "B11 uses different named sources and has no historical bridge",
        "same_type_wage_job_and_employer_dedup_all_historical_regimes",
    ),
    _fact(
        "b11_same_type_se_dedup",
        "b11",
        "same-type SE business/component deduplication",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b10_2023_technical_notes",
            "eedata_2023_counting_and_sources",
            "pdf_b11_later_rows_and_notes",
        ),
        "the separate 2023 B10/CWHS counts are unduplicated within type",
        "no B11 historical business/component aggregation rule is supplied",
        "same_type_se_business_and_component_dedup_all_historical_regimes",
    ),
    _fact(
        "b11_timing",
        "b11",
        "calendar-year and SE tax-year timing",
        "partially_established_required_fact_unestablished",
        (
            "pdf_b11_title_headers_and_early_rows",
            "eedata_2023_counting_and_sources",
        ),
        "B11 has annual rows; the separate 2023 report says during the year",
        "historical calendar/tax-year assignment and continuity are unstated",
        "exact_calendar_year_and_se_tax_year_timing_all_historical_regimes",
    ),
    _fact(
        "b11_geography",
        "b11",
        "exact historical population geography",
        "unestablished",
        (
            "eedata_2023_tax_rules",
            "eedata_2023_counting_and_sources",
            "pdf_b11_later_rows_and_notes",
        ),
        "the separate 2023 report defines its geography and residence coding",
        "B11 has no matching geography note for 1968-2022",
        "exact_population_geography_all_historical_regimes",
    ),
    _fact(
        "b11_historical_continuity",
        "b11",
        "historical method continuity and effective dates",
        "unestablished",
        (
            "pdf_b11_later_rows_and_notes",
            "oasdi_incomplete_history_disclaimer",
            "oasdi_selected_historical_coverage_changes",
        ),
        "B11 presents a long series and the reference lists selected changes",
        "no continuity statement exists and the reference disclaims completeness",
        "historical_method_continuity_and_effective_dates",
    ),
)

B2_WAGE_FACT_IDS = tuple(
    fact["fact_id"] for fact in FACTS if fact["group"] == "b2_wage"
)
B2_SE_FACT_IDS = tuple(
    fact["fact_id"] for fact in FACTS if fact["group"] == "b2_se"
)
B11_FACT_IDS = tuple(
    fact["fact_id"] for fact in FACTS if fact["group"] == "b11"
)

TARGET_FAMILY_FACT_IDS = {
    "b2_wage_total_intensity": B2_WAGE_FACT_IDS,
    "b2_se_total_intensity": B2_SE_FACT_IDS,
    "b11_se_only_worker_share": B11_FACT_IDS,
    "b11_dual_type_worker_share": B11_FACT_IDS,
    "b11_wage_only_worker_share": B11_FACT_IDS,
    "b2_type_count_mix": B2_WAGE_FACT_IDS + B2_SE_FACT_IDS,
    "b2_se_total_component_share": B2_SE_FACT_IDS,
    "b2_wage_taxable_intensity": B2_WAGE_FACT_IDS,
    "b2_se_taxable_intensity": B2_SE_FACT_IDS,
    "b2_wage_taxable_fraction": B2_WAGE_FACT_IDS,
    "b2_se_taxable_fraction": B2_SE_FACT_IDS,
    "b11_taxable_earnings_component_reconciliation": (),
    "b11_contributions_component_reconciliation": (),
    "b11_se_contribution_share": (),
}

REGISTRATION_AUTHORITY_ADJUDICATIONS = (
    {
        "authority_id": "model_universe_id",
        "status": "registration_required",
        "resolved_value": None,
        "reason_id": "missing_registered_correction_model_universe_selector",
        "citations": [
            "docs/design/covered_earnings_correction.md:2281",
            "docs/design/covered_earnings_correction.md:5628",
            "docs/design/covered_earnings_correction.md:8457",
            "docs/design/first_estimates_report.md:89",
        ],
    },
    {
        "authority_id": "model_weight_field",
        "status": "resolved_from_committed_first_estimates_authority",
        "resolved_value": "weight",
        "reason_id": (
            "first_estimates_fixed_start_wave_psid_cross_sectional_weight_v1"
        ),
        "citations": [
            "docs/design/first_estimates_report.md:540",
            "src/populace_dynamics/harness/m6_cells.py:113",
            "src/populace_dynamics/estimates/ledgers.py:879",
        ],
    },
    {
        "authority_id": "model_weight_source_sha256",
        "status": "registration_required",
        "resolved_value": None,
        "reason_id": "missing_registered_model_weight_input_digest",
        "citations": [
            "runs/first_estimates_v1.json:8",
            "runs/first_estimates_v1.json:178",
            "src/populace_dynamics/data/psid.py:63",
            "scripts/registered_m6_inputs.py:48",
        ],
    },
    {
        "authority_id": "denominator_and_joint_analytic_selectors",
        "status": "partially_resolved_fail_closed",
        "resolved_value": {
            "selector_ids_and_joint_reduction": "design_frozen",
            "membership_predicates": None,
        },
        "reason_id": "selector_ids_resolved_membership_predicates_unestablished",
        "citations": [
            "docs/design/covered_earnings_correction.md:229",
            "docs/design/covered_earnings_correction.md:242",
            "docs/design/covered_earnings_correction.md:8550",
        ],
    },
    {
        "authority_id": "universe_concordance",
        "status": "registration_required",
        "resolved_value": {
            "frame_relation": "frame_relative_not_population_aligned"
        },
        "reason_id": "cannot_pass_without_official_and_model_universes",
        "citations": [
            "docs/design/covered_earnings_correction.md:2247",
            "docs/design/covered_earnings_correction.md:2281",
            "docs/design/first_estimates_report.md:59",
            "runs/first_estimates_v1.json:356",
        ],
    },
)

GLOBAL_MISSING_AUTHORITY_IDS = tuple(
    row["reason_id"]
    for row in REGISTRATION_AUTHORITY_ADJUDICATIONS
    if row["status"] != "resolved_from_committed_first_estimates_authority"
)


def _manifest_entries() -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    literal_lines = CAPTURE_MANIFEST_PATH.read_text(
        encoding="utf-8"
    ).splitlines()
    if len(literal_lines) != len(SOURCE_SPECS):
        raise ValueError("methodology capture manifest entry count drift")
    entries: list[dict[str, Any]] = []
    raw_by_id: dict[str, bytes] = {}
    for line_number, ((source_id, spec), line) in enumerate(
        zip(SOURCE_SPECS.items(), literal_lines, strict=True),
        start=1,
    ):
        parts = line.split(" ")
        if len(parts) != 5:
            raise ValueError(f"manifest line {line_number} grammar drift")
        timestamp, sha256, size, filename, url = parts
        required = (
            "2026-07-30T05:07:30Z",
            spec["sha256"],
            str(spec["size_bytes"]),
            spec["filename"],
            spec["url"],
        )
        if tuple(parts) != required:
            raise ValueError(f"manifest line {line_number} identity drift")
        raw = (SNAPSHOT_DIR / filename).read_bytes()
        if (
            len(raw) != spec["size_bytes"]
            or hashlib.sha256(raw).hexdigest() != sha256
        ):
            raise ValueError(f"{source_id} committed source bytes drift")
        committed_path = str((SNAPSHOT_DIR / filename).relative_to(ROOT))
        entries.append(
            {
                "source_document_id": source_id,
                "retrieved_at_utc": timestamp,
                "committed_path": committed_path,
                "sha256": sha256,
                "size_bytes": int(size),
                "url": url,
                "capture_manifest_line": line_number,
                "capture_manifest_entry": line,
            }
        )
        raw_by_id[source_id] = raw
    return entries, raw_by_id


def _html_locator(
    locator_id: str,
    source_document_id: str,
    line_start: int,
    line_end: int,
    description: str,
    raw: bytes,
) -> dict[str, Any]:
    lines = raw.splitlines(keepends=True)
    if not 1 <= line_start <= line_end <= len(lines):
        raise ValueError(f"{locator_id} line range is outside source bytes")
    byte_start = sum(map(len, lines[: line_start - 1]))
    byte_end = sum(map(len, lines[:line_end]))
    excerpt = raw[byte_start:byte_end]
    return {
        "locator_id": locator_id,
        "source_document_id": source_document_id,
        "location_type": "html_line_and_byte_range",
        "line_start": line_start,
        "line_end": line_end,
        "byte_start": byte_start,
        "byte_end": byte_end,
        "range_sha256": hashlib.sha256(excerpt).hexdigest(),
        "description": description,
    }


def _pdf_locator(
    locator_id: str,
    page: int,
    content_object: str,
    byte_start: int,
    byte_end: int,
    range_sha256: str,
    description: str,
    raw: bytes,
) -> dict[str, Any]:
    if (
        byte_start < 0
        or byte_end <= byte_start
        or hashlib.sha256(raw[byte_start:byte_end]).hexdigest() != range_sha256
    ):
        raise ValueError(f"{locator_id} PDF byte-range identity drift")
    return {
        "locator_id": locator_id,
        "source_document_id": "ssa_supplement_2025_4b_pdf",
        "location_type": "pdf_compressed_content_stream_byte_range",
        "pdf_page": page,
        "content_object": content_object,
        "byte_start": byte_start,
        "byte_end": byte_end,
        "range_sha256": range_sha256,
        "description": description,
    }


def _source_locators(raw_by_id: Mapping[str, bytes]) -> list[dict[str, Any]]:
    locators = [
        _html_locator(*spec, raw_by_id[spec[1]]) for spec in HTML_LOCATOR_SPECS
    ]
    pdf_raw = raw_by_id["ssa_supplement_2025_4b_pdf"]
    locators.extend(_pdf_locator(*spec, pdf_raw) for spec in PDF_LOCATOR_SPECS)
    return locators


def _family_dispositions() -> list[dict[str, Any]]:
    fact_by_id = {fact["fact_id"]: fact for fact in FACTS}
    rows = []
    for family, fact_ids in TARGET_FAMILY_FACT_IDS.items():
        missing_source = [
            fact_by_id[fact_id]["missing_fact_id"]
            for fact_id in fact_ids
            if fact_by_id[fact_id]["missing_fact_id"] is not None
        ]
        missing_authority = list(GLOBAL_MISSING_AUTHORITY_IDS)
        rows.append(
            {
                "target_family": family,
                "required_source_fact_ids": list(fact_ids),
                "missing_source_fact_ids": missing_source,
                "missing_registration_authority_ids": missing_authority,
                "missing_fact_list": missing_source + missing_authority,
                "verdict": "fail_closed",
            }
        )
    return rows


def _content_sha256(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return hashlib.sha256(canonical.canonical_json_bytes(preimage)).hexdigest()


def validate_adjudication(value: Mapping[str, Any]) -> None:
    """Re-resolve every verdict and locator from the committed source bytes."""

    expected_keys = {
        "schema_version",
        "adjudication_id",
        "source_capture_manifest",
        "pdf_extraction_method",
        "source_locators",
        "facts",
        "family_dispositions",
        "registration_authority_adjudications",
        "integrity",
    }
    if set(value) != expected_keys:
        raise ValueError("adjudication top-level fields missing or extra")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["adjudication_id"] != ADJUDICATION_ID
        or value["pdf_extraction_method"] != PDF_EXTRACTION_METHOD
    ):
        raise ValueError("adjudication identity or extraction method drift")

    manifest, raw_by_id = _manifest_entries()
    if value["source_capture_manifest"] != manifest:
        raise ValueError("source capture manifest drift")
    expected_locators = _source_locators(raw_by_id)
    if value["source_locators"] != expected_locators:
        raise ValueError(
            "source locator does not re-resolve from pinned bytes"
        )
    locator_ids = [row["locator_id"] for row in expected_locators]
    if len(locator_ids) != len(set(locator_ids)):
        raise ValueError("source locator IDs are not unique")

    if value["facts"] != list(FACTS):
        raise ValueError("fact table drift")
    fact_ids = [row["fact_id"] for row in value["facts"]]
    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("fact IDs are not unique")
    for row in value["facts"]:
        evidence = row["evidence_locator_ids"]
        if not evidence or any(item not in locator_ids for item in evidence):
            raise ValueError(f"{row['fact_id']} lacks exact byte evidence")
        if row["verdict"] == "established":
            if row["missing_fact_id"] is not None:
                raise ValueError(
                    f"{row['fact_id']} established/missing conflict"
                )
        elif row["missing_fact_id"] is None:
            raise ValueError(
                f"{row['fact_id']} unestablished without missing ID"
            )

    expected_families = _family_dispositions()
    if value["family_dispositions"] != expected_families:
        raise ValueError("family fail-closed dispositions drift")
    if any(row["verdict"] != "fail_closed" for row in expected_families):
        raise ValueError("an unresolved family was opened")
    if value["registration_authority_adjudications"] != list(
        REGISTRATION_AUTHORITY_ADJUDICATIONS
    ):
        raise ValueError("registration authority adjudication drift")

    integrity = value["integrity"]
    if set(integrity) != {
        "canonicalization",
        "content_sha256",
        "reproduced_from_source_bytes",
    }:
        raise ValueError("adjudication integrity fields missing or extra")
    if (
        integrity["canonicalization"] != CANONICALIZATION
        or integrity["reproduced_from_source_bytes"] is not True
        or integrity["content_sha256"] != _content_sha256(value)
    ):
        raise ValueError("adjudication integrity failure")


def build() -> dict[str, Any]:
    """Build the complete, source-byte-resolved adjudication."""

    manifest, raw_by_id = _manifest_entries()
    value = {
        "schema_version": SCHEMA_VERSION,
        "adjudication_id": ADJUDICATION_ID,
        "source_capture_manifest": manifest,
        "pdf_extraction_method": copy.deepcopy(PDF_EXTRACTION_METHOD),
        "source_locators": _source_locators(raw_by_id),
        "facts": copy.deepcopy(list(FACTS)),
        "family_dispositions": _family_dispositions(),
        "registration_authority_adjudications": copy.deepcopy(
            list(REGISTRATION_AUTHORITY_ADJUDICATIONS)
        ),
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
            "reproduced_from_source_bytes": True,
        },
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    validate_adjudication(value)
    return value


def render() -> bytes:
    """Render the validated adjudication as canonical JSON bytes."""

    return canonical.canonical_json_bytes(build())


def main() -> None:
    OUT_PATH.write_bytes(render())


if __name__ == "__main__":
    main()
