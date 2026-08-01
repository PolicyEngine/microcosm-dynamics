#!/usr/bin/env python3
"""Build the offline, ratio/share/trajectory-only validation matrix.

At execution time this builder reads only committed repository bytes. Reviewed
external captures are represented below by frozen source pins and extracted
cells, so rebuilding does not depend on the coordinator's mutable staging path.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("matrix.json")

INPUT_PATHS = [
    "runs/first_estimates_v1.json",
    "runs/anchor_context_report_v1.json",
    "data/external/ssa_level_anchors_supplement2025_trustees2026_vintage1.json",
    "runs/gate_m6_candidate3_v1.json",
    "runs/gate1_rank_knn_v5.json",
    "runs/replication_ppi_mermin_v1.json",
    "runs/replication_ppi_shared_v1.json",
    "runs/replication_mermin_rows_v1.json",
    "runs/replication_r7_sharing_v1.json",
    "runs/replication_cost_ordering_v1.json",
    "docs/design/covered_earnings_correction.md",
    "docs/design/anchor_context_extraction.md",
]

MERMIN_URL = (
    "https://www.urban.org/sites/default/files/publication/51966/"
    "411260-Distributional-Effects-of-Reforming-Social-Security-through-"
    "Benefit-Reductions.PDF"
)
FAVREAULT_STEUERLE_URL = (
    "https://www.urban.org/sites/default/files/publication/46231/"
    "311436-Social-Security-Spouse-and-Survivor-Benefits-for-the-Modern-"
    "Family.PDF"
)

CBO_60392_LONG_TERM_URL = (
    "https://www.cbo.gov/system/files/2024-08/"
    "60392-Long-Term-Social-Security-Projections.xlsx"
)
WISH_BILL_PDF_URL = (
    "https://www.congress.gov/117/bills/hr4289/BILLS-117hr4289ih.pdf"
)
MORNINGSTAR_WISH_REPORT_URL = (
    "https://www.morningstar.com/content/cs-assets/v3/assets/"
    "blt9415ea4cc4157833/bltbbad12f4cb956f93/"
    "68a338a0fd4281840b31bbf3/Morningstar_WISH_Act_Analysis.pdf"
)

# These pins and extracted cells were reviewed from the coordinator's
# 2026-08-01 REFRESH. The external bytes remain outside this repository; this
# committed builder freezes everything used by the canonical output.
REFRESH_REVIEW = {
    "staging_manifest": {
        "external_path": (
            "~/PolicyEngine/psid-data/validation-sources/manifest.jsonl"
        ),
        "sha256": (
            "72c180e8d162d9cc09017c355214ba0f9e1175b2d79f294ec2de96ee28cb2e1a"
        ),
        "size_bytes": 12042,
        "entry_count": 30,
        "unique_filename_count": 30,
        "all_declared_sha256_and_sizes_verified": True,
    },
    "not_located_record": {
        "external_path": (
            "~/PolicyEngine/psid-data/validation-sources/NOT-LOCATED.md"
        ),
        "sha256": (
            "2c69cb5c259d5eb3c7f99d60df8ccad5e00e7cad74966f53b2db95a232a6592a"
        ),
        "size_bytes": 976,
    },
    "captures": {
        "cbo_60392_long_term": {
            "filename": "cbo-60392-Long-Term-Projections.xlsx",
            "url": CBO_60392_LONG_TERM_URL,
            "sha256": (
                "8945d7c5599e944e5786801daf3af9ebad318b24b871198708eeff9bb6c46f7b"
            ),
            "size_bytes": 85665,
        },
        "cbo_60392_additional": {
            "filename": "cbo-60392-Additional-Info.xlsx",
            "url": (
                "https://www.cbo.gov/system/files/2024-08/"
                "60392-Additional-Info.xlsx"
            ),
            "sha256": (
                "9ff92c8e54e5b873f4b7743e695773876714a23c425c3ccb0c5dbb8d0c4dc739"
            ),
            "size_bytes": 67661,
        },
        "cbo_55038_supplemental": {
            "filename": "cbo-att-55038-SupplementalData.xlsx",
            "url": (
                "https://www.cbo.gov/system/files/2019-04/"
                "55038-SupplementalData.xlsx"
            ),
            "sha256": (
                "9403fe44c44b360276d9ccf21a85ef5a55d4e689020ceab715a9e33e38d8429c"
            ),
            "size_bytes": 6147155,
        },
        "cbolt_overview": {
            "filename": "cbo-att-53667-cbolt.pdf",
            "url": (
                "https://www.cbo.gov/system/files/115th-congress-2017-2018/"
                "reports/53667-cbolt.pdf"
            ),
            "sha256": (
                "31447365f66ecedeaa15b2337a0f2e4688cca69ca7398922b3f9b0f9bf08d4cd"
            ),
            "size_bytes": 193463,
        },
        "mint8_report": {
            "filename": "urban-mint8-report.pdf",
            "url": (
                "https://www.urban.org/sites/default/files/publication/104958/"
                "modeling-income-in-the-near-term.pdf"
            ),
            "sha256": (
                "e0da0a4f0be9e70fa675cfae6a42123bad5d4bc82392aeb9f3ce9ace97f0b77d"
            ),
            "size_bytes": 2281292,
        },
        "ssa_mint_beneficiary_tables": {
            "filename": "ssa-mint-tables-beneficiaries.html",
            "url": (
                "https://www.ssa.gov/policy/docs/projections/tables/"
                "beneficiaries.html"
            ),
            "sha256": (
                "a3f6da991356045f165b6517390ab8fbdd84e1de386e2d026ab5dc2ff9009ccf"
            ),
            "size_bytes": 1652291,
        },
        "favreault_2007": {
            "filename": "urban-favreault2007-311436.pdf",
            "url": FAVREAULT_STEUERLE_URL,
            "sha256": (
                "78b25f1b785356bf465ad3d5ddfce8c14c577dbdd7d0710fda7b048f5aa63bf6"
            ),
            "size_bytes": 708709,
        },
        "wish_bill_pdf": {
            "filename": "BILLS-117hr4289ih.pdf",
            "url": WISH_BILL_PDF_URL,
            "sha256": (
                "b327b67932b0d4159b956039f1e695cb16330e3429b2b7a1a2e72685bf0641e1"
            ),
            "size_bytes": 269364,
        },
        "morningstar_wish_landing": {
            "filename": "morningstar-wish-landing.html",
            "url": (
                "https://www.morningstar.com/business/insights/research/"
                "wish-act-national-ltss-insurance-program"
            ),
            "sha256": (
                "1bd1f2a27ba56e4bca4e6c06d7b01b6f4aad72ea9914b6c5ff483e9986d54011"
            ),
            "size_bytes": 146083,
        },
        "morningstar_generic_technical_appendix": {
            "filename": "morningstar-wish-technical-appendix.pdf",
            "url": (
                "https://images.mscomm.morningstar.com/Web/MorningstarInc/"
                "%7B2a14ac78-9500-4062-b8c4-04b85dd25cfd%7D_"
                "Morningstar_Model_of_US_Retirement_Outcomes-Technical_Appendix.pdf"
            ),
            "sha256": (
                "1c350268c803b427e9e3d0d93f7b01a1d4982c1e873ba1afc28617bfa1f9aec7"
            ),
            "size_bytes": 111000,
            "warning": "Generic July 2024 appendix; contains no WISH analysis.",
        },
    },
    "missing_after_refresh": {
        "mermin_2005_publisher_capture": {
            "url": MERMIN_URL,
            "status": (
                "Publisher-controlled bytes were not retrieved; the modern "
                "Urban Institute URLs returned 404 and the web archive was "
                "unavailable. The 20 Mermin comparisons are therefore "
                "reported_not_verified, not canonical verified rows."
            ),
        },
        "morningstar_full_wish_report": {
            "url_discovered_in_captured_landing_json_ld": MORNINGSTAR_WISH_REPORT_URL,
            "status": "not staged; associatedMedia says isAccessibleForFree=false",
        },
        "wish_primary_actuarial_memoranda": (
            "No ARC or Oliver Wyman memorandum was publicly located."
        ),
        "dynasim4_cohort_workbook": (
            "Publisher workbook URL returned 404; no workbook was staged."
        ),
    },
}

RATIFIED_FITTING_FREE_LABELS = [
    "frame-relative",
    "modeled-covered-earnings",
    "deterministic-uncalibrated",
]


def read_bytes(relative: str) -> bytes:
    return (ROOT / relative).read_bytes()


def load_json(relative: str) -> dict[str, Any]:
    return json.loads(read_bytes(relative))


def sha256(relative: str) -> str:
    return hashlib.sha256(read_bytes(relative)).hexdigest()


first = load_json("runs/first_estimates_v1.json")
context = load_json("runs/anchor_context_report_v1.json")
anchors = load_json(
    "data/external/ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
)
m6 = load_json("runs/gate_m6_candidate3_v1.json")
gate1 = load_json("runs/gate1_rank_knn_v5.json")
ppi = load_json("runs/replication_ppi_mermin_v1.json")
ppi_shared = load_json("runs/replication_ppi_shared_v1.json")
mermin_rows = load_json("runs/replication_mermin_rows_v1.json")
sharing = load_json("runs/replication_r7_sharing_v1.json")
ordering = load_json("runs/replication_cost_ordering_v1.json")

SOURCE_ARTIFACT_LABELS = first["tables"]["revenue"]["labels"]


def label_state(source_has_embedded_labels: bool) -> dict[str, Any]:
    """Return the full, non-overclaiming label state required on every row."""

    return {
        "matrix_display": (
            "frame-relative proxy covered-earnings; no population alignment"
        ),
        "source_artifact_embedded_labels": (
            SOURCE_ARTIFACT_LABELS if source_has_embedded_labels else None
        ),
        "source_artifact_label_note": (
            "The entry-8 and entry-10 artifacts embed the legacy proxy array."
            if source_has_embedded_labels
            else "This report-only module artifact embeds no label array."
        ),
        "ratified_fitting_free_exact_label_array": RATIFIED_FITTING_FREE_LABELS,
        "ratified_array_locator": (
            "docs/design/covered_earnings_correction.md §16.7.1"
        ),
        "ratified_array_activation_asserted_by_this_matrix": False,
        "population_alignment_claim": False,
        "individual_administrative_truth_claim": False,
    }


def source_pin(relative: str, pointer: str) -> dict[str, str]:
    return {
        "path": relative,
        "sha256": sha256(relative),
        "json_pointer": pointer,
    }


def official_locator(series_id: str, role: str) -> dict[str, Any]:
    series = anchors["determinations"][series_id]
    observation = series["observations"][0]
    table = series["source_table"]
    return {
        "role": role,
        "series_id": series_id,
        "publisher": "Social Security Administration",
        "document": table["publication"],
        "edition_or_report_year": table["edition_or_report_year"],
        "page": "not applicable (HTML)",
        "table": table["table_id"],
        "table_title": table["table_title"],
        "row_locator": "calendar-year rows 2015 through 2022",
        "column_header_path": observation["source_column_header_path"],
        "url": observation["source_url"],
        "committed_extraction": {
            "path": (
                "data/external/"
                "ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
            ),
            "sha256": sha256(
                "data/external/"
                "ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
            ),
            "json_pointer": f"/determinations/{series_id}/observations",
        },
    }


TRUSTEES_ROWS: list[dict[str, Any]] = [
    {
        "comparison_id": "cmp_reported_taxable_earnings_per_worker",
        "quantity": "Reported taxable earnings per worker",
        "unit": "current dollars per annual worker (ratio, not a dollar total)",
        "population": (
            "Our denominator counts positive proxy earners; SSA counts people "
            "with reported OASDI taxable earnings."
        ),
        "benefit": "Not a benefit measure.",
        "earnings": (
            "Our consolidated person-level labor-income proxy is capped once, "
            "has no zero floor, and is not employer-reported taxable earnings."
        ),
    },
    {
        "comparison_id": "cmp_adjusted_taxable_payroll_per_covered_worker",
        "quantity": "Adjusted taxable payroll per covered worker",
        "unit": "current dollars per annual covered worker (ratio, not a dollar total)",
        "population": (
            "Our denominator counts positive proxy earners; Trustees count "
            "workers paid in OASDI-covered employment."
        ),
        "benefit": "Not a benefit measure.",
        "earnings": (
            "Our capped proxy differs from actuarially adjusted payroll, "
            "including multi-employer excess-wage treatment and the absent zero floor."
        ),
    },
    {
        "comparison_id": "cmp_gross_contributions_per_worker",
        "quantity": "Gross OASDI contributions per worker",
        "unit": "current dollars per annual worker (ratio, not a dollar total)",
        "population": (
            "Our denominator counts positive proxy earners; SSA counts people "
            "with OASDI taxable earnings."
        ),
        "benefit": "Not a benefit measure.",
        "earnings": (
            "Our value is earnings-year proxy payroll times 12.4%; Supplement "
            "gross contributions are unadjusted for refunds and credits and are "
            "not the same accounting object."
        ),
    },
    {
        "comparison_id": "cmp_net_payroll_tax_contributions_per_covered_worker",
        "quantity": "Net payroll-tax contributions per covered worker",
        "unit": "current dollars per annual covered worker (ratio, not a dollar total)",
        "population": (
            "Our denominator counts positive proxy earners; Trustees count "
            "workers paid in OASDI-covered employment."
        ),
        "benefit": "Not a benefit measure.",
        "earnings": (
            "Our value is earnings-year rate arithmetic on a capped proxy; the "
            "official numerator is trust-fund cash with estimated deposits and later adjustments."
        ),
    },
    {
        "comparison_id": "cmp_retired_worker_beneficiaries_per_worker",
        "quantity": "Retired-worker beneficiaries per worker",
        "unit": "annualized-presence beneficiaries per annual worker",
        "population": (
            "Our numerator is a mechanical own-retirement annual-presence "
            "population including report-only opening backfill; SSA is the "
            "December retired-worker current-payment stock. Denominators are "
            "positive proxy earners versus workers with taxable earnings."
        ),
        "benefit": (
            "Mechanical claim-age crossings and imputed opening claims differ "
            "from administrative entitlement and in-force payment histories."
        ),
        "earnings": "The worker denominator retains the proxy-versus-reported-earnings mismatch.",
    },
    {
        "comparison_id": "cmp_retired_worker_awards_per_worker",
        "quantity": "Retired-worker awards per worker",
        "unit": "mechanical claim stamps per annual worker",
        "population": (
            "Our numerator is modeled own-retirement claim stamps; SSA counts "
            "administratively effectuated retired-worker awards. Denominators "
            "are positive proxy earners versus workers with taxable earnings."
        ),
        "benefit": (
            "An SSA award is administratively effectuated and payable-not-"
            "guaranteed; our event is a mechanical claim-age crossing."
        ),
        "earnings": "The worker denominator retains the proxy-versus-reported-earnings mismatch.",
    },
    {
        "comparison_id": "cmp_retired_worker_benefits_per_reported_taxable_earnings",
        "quantity": "Retired-worker benefits per reported taxable earnings",
        "unit": "benefit-flow share of annual taxable earnings",
        "population": (
            "Our numerator is an own-retirement annual-presence population with "
            "opening backfill; SSA is an estimated retired-worker allocation."
        ),
        "benefit": (
            "Our numerator annualizes 12 statutory monthly amounts with no "
            "partial first/last year or AERO recomputation; SSA records estimated "
            "actual outlays."
        ),
        "earnings": (
            "Our denominator is the capped labor-income proxy with no zero floor; "
            "SSA's denominator is reported taxable earnings."
        ),
    },
]


def build_trustees_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    result_by_id = {
        row["comparison_id"]: (index, row)
        for index, row in enumerate(context["results"]["comparison_results"])
    }
    spec_by_id = {
        row["comparison_id"]: row
        for row in context["configuration_echo"]["comparison_specs"]
    }
    for definition in TRUSTEES_ROWS:
        comparison_id = definition["comparison_id"]
        index, result = result_by_id[comparison_id]
        spec = spec_by_id[comparison_id]
        annual = result["annual_rows"]
        model_base = annual[0]["model_statistic_mean"]
        official_base = annual[0]["official_statistic"]
        model_values = [
            {
                "year": item["year"],
                "mean": item["model_statistic_mean"],
                "sample_sd_across_draws": item["model_statistic_sample_sd"],
            }
            for item in annual
        ]
        published_values = [
            {"year": item["year"], "value": item["official_statistic"]}
            for item in annual
        ]
        relative = [
            {
                "year": item["year"],
                "percent": 100.0 * (item["comparison_mean"] - 1.0),
            }
            for item in annual
        ]
        trajectory = [
            {
                "year": item["year"],
                "our_index_2015_100": (
                    100.0 * item["model_statistic_mean"] / model_base
                ),
                "published_index_2015_100": (
                    100.0 * item["official_statistic"] / official_base
                ),
                "deviation_index_points": 100.0
                * (
                    item["model_statistic_mean"] / model_base
                    - item["official_statistic"] / official_base
                ),
            }
            for item in annual
        ]
        locator_ids = [
            spec["official_numerator_series_id"],
            spec["official_denominator_series_id"],
        ]
        locators = [
            official_locator(series_id, role)
            for series_id, role in zip(
                locator_ids, ["numerator", "denominator"], strict=False
            )
        ]
        rows.append(
            {
                "row_id": f"ssa.{comparison_id.removeprefix('cmp_')}",
                "external_model": "SSA Trustees / Annual Statistical Supplement",
                "quantity": definition["quantity"],
                "comparison_scope": ["ratio", "trajectory"],
                "our": {
                    "value": model_values,
                    "unit": definition["unit"],
                    "formula": spec["model_formula"],
                    "label_state": label_state(True),
                    "source": source_pin(
                        "runs/anchor_context_report_v1.json",
                        f"/results/comparison_results/{index}/annual_rows",
                    ),
                },
                "published": {
                    "value": published_values,
                    "unit": definition["unit"],
                    "formula": spec["official_formula"],
                    "source_locators": locators,
                },
                "deviation": {
                    "signed_native_unit": [
                        {
                            "year": item["year"],
                            "value": item["model_statistic_mean"]
                            - item["official_statistic"],
                        }
                        for item in annual
                    ],
                    "relative_percent": relative,
                    "our_over_published_ratio": [
                        {
                            "year": item["year"],
                            "value": item["comparison_mean"],
                        }
                        for item in annual
                    ],
                    "trajectory_2015_100": trajectory,
                    "definition": (
                        "signed = ours - published; relative percent = "
                        "100*(ours/published - 1); trajectory deviation compares "
                        "separately indexed paths"
                    ),
                },
                "concept_mismatch": {
                    "frame": (
                        "Our 20-draw 2015-2022 result is frame-relative and "
                        "unaligned; official values are national administrative "
                        "or actuarial series. No population-level correspondence is claimed."
                    ),
                    "population": definition["population"],
                    "year_basis": (
                        "Both sides use calendar years 2015-2022, but the model "
                        "carries prior even-year earnings into odd years; official "
                        "historical observations follow their source accounting and revision basis."
                    ),
                    "benefit_concept": definition["benefit"],
                    "earnings_and_accounting": definition["earnings"],
                    "mismatch_codes": spec["mismatch_codes"],
                },
                "evidential_status": (
                    "scale-invariant context only; no level-alignment authority"
                ),
            }
        )
    return rows


def cbo_workbook_locator(
    sheet: str,
    table: str,
    observation_range: str,
    definition_range: str,
) -> list[dict[str, Any]]:
    return [
        {
            "publisher": "Congressional Budget Office",
            "document": (
                "CBO's 2024 Long-Term Projections for Social Security, "
                "Long-Term Social Security Projections data workbook"
            ),
            "page": "not applicable (XLSX)",
            "table": table,
            "sheet": sheet,
            "observation_range": observation_range,
            "definition_or_note_range": definition_range,
            "url": CBO_60392_LONG_TERM_URL,
            "reviewed_external_capture": deepcopy(
                REFRESH_REVIEW["captures"]["cbo_60392_long_term"]
            ),
        }
    ]


def build_cbo_rows() -> list[dict[str, Any]]:
    revenue_rows = first["tables"]["revenue"]["per_draw"]
    by_draw: dict[int, dict[int, dict[str, float]]] = {}
    for item in revenue_rows:
        by_draw.setdefault(item["draw_index"], {})[item["year"]] = item
    years = list(range(2015, 2023))

    our_payroll_path = []
    for year in years:
        indices = [
            100.0
            * values[year]["weighted_taxable_payroll"]
            / values[2015]["weighted_taxable_payroll"]
            for values in by_draw.values()
        ]
        our_payroll_path.append(
            {
                "year": year,
                "mean_index_2015_100": statistics.mean(indices),
                "sample_sd_across_paired_draw_indices": statistics.stdev(
                    indices
                ),
            }
        )

    cbo_payroll_trillions = [
        6.448,
        6.639,
        6.983,
        7.312,
        7.665,
        7.717,
        8.349,
        9.151,
    ]
    cbo_payroll_path = [
        {
            "year": year,
            "index_2015_100": 100.0 * value / cbo_payroll_trillions[0],
        }
        for year, value in zip(years, cbo_payroll_trillions, strict=False)
    ]
    payroll_deviation = [
        {
            "year": year,
            "index_points": ours["mean_index_2015_100"]
            - published["index_2015_100"],
        }
        for year, ours, published in zip(
            years, our_payroll_path, cbo_payroll_path, strict=False
        )
    ]

    our_tax_shares = []
    for year in years:
        shares = [
            100.0
            * values[year]["combined_contributions"]
            / values[year]["weighted_taxable_payroll"]
            for values in by_draw.values()
        ]
        assert max(shares) - min(shares) < 1e-12
        assert abs(statistics.mean(shares) - 12.4) < 1e-12
        our_tax_shares.append(
            {
                "year": year,
                "mean_percent": 12.4,
                "sample_sd_across_draws": 0.0,
                "variation_note": "exact mechanical identity; floating noise suppressed",
            }
        )
    cbo_tax_share_values = [
        12.82,
        13.09,
        13.05,
        12.58,
        12.80,
        13.50,
        12.20,
        12.63,
    ]
    cbo_tax_shares = [
        {"year": year, "percent": value}
        for year, value in zip(years, cbo_tax_share_values, strict=False)
    ]
    tax_share_deviation = [
        {
            "year": year,
            "percentage_points": ours["mean_percent"] - published,
        }
        for year, ours, published in zip(
            years, our_tax_shares, cbo_tax_share_values, strict=False
        )
    ]

    return [
        {
            "row_id": "cbo.taxable_payroll.trajectory_2015_100",
            "external_model": "CBOLT / CBO (historical actual-data segment)",
            "quantity": "Taxable-payroll trajectory normalized to 2015",
            "comparison_scope": ["trajectory"],
            "our": {
                "value": our_payroll_path,
                "unit": "index, 2015 = 100 within each draw",
                "label_state": label_state(True),
                "source": source_pin(
                    "runs/first_estimates_v1.json", "/tables/revenue/per_draw"
                ),
                "formula": (
                    "100 * weighted_taxable_payroll(year) / "
                    "weighted_taxable_payroll(2015), paired within draw"
                ),
            },
            "published": {
                "value": cbo_payroll_path,
                "unit": "index, 2015 = 100",
                "underlying_published_values_withheld_from_comparison": (
                    "Dollar levels are retained only as frozen extraction inputs "
                    "to calculate the allowed index; they are not reported as a comparison."
                ),
                "source_locators": cbo_workbook_locator(
                    "2",
                    "Taxable payroll, title A6; headers A9:C9",
                    "A40:C47 (calendar years 2015-2022)",
                    "A127 (actual-data note)",
                ),
            },
            "deviation": {
                "signed_index_points": payroll_deviation,
                "definition": "ours 2015-index minus published 2015-index",
            },
            "concept_mismatch": {
                "frame": (
                    "Our path is an unaligned, frame-relative taxable-payroll "
                    "proxy; CBO's path is national OASDI taxable payroll."
                ),
                "population": (
                    "Our closed PSID reproduction panel and survey weights do "
                    "not represent CBO's national covered-worker population."
                ),
                "year_basis": (
                    "Both paths cover calendar years 2015-2022, but our odd "
                    "years carry prior even-wave earnings; CBO marks these cells "
                    "as actual data rather than CBOLT projections."
                ),
                "benefit_concept": "Not a benefit measure.",
                "earnings_and_accounting": (
                    "Our capped labor-income proxy is not employer-reported "
                    "wages and self-employment income under CBO's taxable-payroll accounting."
                ),
                "mismatch_codes": [
                    "unaligned_proxy_vs_national_taxable_payroll",
                    "closed_psid_panel_vs_national_covered_workers",
                    "odd_year_carry_vs_annual_administrative_data",
                    "cbo_overlap_is_actual_data_not_projection",
                ],
            },
            "evidential_status": (
                "scale-free historical trajectory context; no level or population alignment"
            ),
        },
        {
            "row_id": "cbo.tax_revenue.share_of_taxable_payroll",
            "external_model": "CBOLT / CBO (historical actual-data segment)",
            "quantity": "Social Security tax revenues as a share of taxable payroll",
            "comparison_scope": ["share", "trajectory"],
            "our": {
                "value": our_tax_shares,
                "unit": "percent of frame-relative proxy taxable payroll",
                "label_state": label_state(True),
                "source": source_pin(
                    "runs/first_estimates_v1.json", "/tables/revenue/per_draw"
                ),
                "formula": "100 * combined_contributions / weighted_taxable_payroll",
            },
            "published": {
                "value": cbo_tax_shares,
                "unit": "percent of national taxable payroll",
                "source_locators": cbo_workbook_locator(
                    "1",
                    "Social Security tax revenues as a percentage of taxable payroll",
                    "A40:D47 (calendar years 2015-2022)",
                    "A129 (tax-revenue definition)",
                ),
            },
            "deviation": {
                "signed_percentage_points": tax_share_deviation,
                "definition": "ours minus published, in percentage points",
            },
            "concept_mismatch": {
                "frame": (
                    "Our denominator is unaligned frame-relative proxy payroll; "
                    "CBO's denominator is national OASDI taxable payroll."
                ),
                "population": (
                    "Our closed PSID reproduction panel differs from CBO's "
                    "national covered-worker and beneficiary populations."
                ),
                "year_basis": (
                    "Both cover calendar 2015-2022, with odd-year earnings carry "
                    "on our side and CBO actual-data accounting on the published side."
                ),
                "benefit_concept": (
                    "Our numerator has no benefit component; CBO tax revenues "
                    "include federal income taxes paid on Social Security benefits."
                ),
                "earnings_and_accounting": (
                    "Our 12.4% value is mechanical employee-plus-employer "
                    "contribution arithmetic. CBO total tax revenue combines "
                    "payroll taxes with income taxes on benefits and is not a statutory-rate check."
                ),
                "mismatch_codes": [
                    "mechanical_contributions_vs_total_tax_revenue",
                    "income_tax_on_benefits_absent_from_ours",
                    "unaligned_proxy_vs_national_taxable_payroll",
                    "odd_year_carry_vs_annual_administrative_data",
                ],
            },
            "evidential_status": (
                "qualified share context; numerator concepts differ; no level alignment"
            ),
        },
    ]


def mermin_locator(table: str, pdf_page: int) -> list[dict[str, Any]]:
    return [
        {
            "publisher": "Urban Institute",
            "document": (
                "Mermin (2005), Distributional Effects of Reforming Social "
                "Security through Benefit Reductions, report 411260, DYNASIM3 Runid 432"
            ),
            "page": {"pdf": pdf_page},
            "table": table,
            "url": MERMIN_URL,
            "capture_status": (
                "Publisher-controlled bytes missing after REFRESH; this "
                "locator has not been verified against an accepted capture."
            ),
            "unmanifested_corroborating_copy": {
                "sha256": (
                    "88934782c267fb0d7f08106ef930a19866c41c89504d04ad7a6d77d454d034ae"
                ),
                "manifested": False,
                "accepted_as_verified_source": False,
                "scope": (
                    "Provisionally corroborates only Table 2 progressive-price-"
                    "indexing Q1 98.7, Q3 81.3, and Q5 71.7; it does not verify "
                    "this row or any other Mermin cell under the capture rule."
                ),
            },
        }
    ]


def mermin_reported_value_provenance(
    relative: str, pointer: str
) -> dict[str, Any]:
    """Describe the only committed provenance for a reported Mermin value."""

    return {
        "classification": "reported_not_verified",
        "numeric_source": source_pin(relative, pointer),
        "numeric_source_note": (
            "The value is transcribed in a committed replication artifact, "
            "not extracted from a manifested publisher-controlled capture."
        ),
        "publisher_capture_status": "missing_after_refresh",
    }


def scalar_deviation(ours: float, published: float) -> dict[str, Any]:
    return {
        "signed_percentage_points": ours - published,
        "absolute_percentage_points": abs(ours - published),
        "relative_percent": 100.0 * (ours / published - 1.0),
        "definition": "signed = ours - published",
    }


PPI_GENERATED_MISMATCH = {
    "frame": (
        "Our row is a report-only Phase-A replication using the gate-filtered "
        "candidate-11 earnings generator, not the entry-8 M6 projected population; "
        "the DYNASIM row is a published model projection. No frame alignment is claimed."
    ),
    "population": (
        "Our support is ages 25-59 in the 1998-2022 biennial panel transported "
        "to 2050; DYNASIM reports 5,351 retired workers ages 62-67 in 2050."
    ),
    "year_basis": (
        "Our single 2050 eligibility transport applies the 2012-2050 wedge; "
        "DYNASIM's mixed ages imply mixed eligibility years near 2047 under the 2005 vintage."
    ),
    "benefit_concept": (
        "Both are own-record benefits as percent of scheduled, but our PPI "
        "incidence uses a proxy PIA chain and excludes spouse/survivor benefits."
    ),
    "earnings_and_accounting": (
        "Our quintiles rank individual proxy AIME; Mermin ranks spouse-shared "
        "lifetime income. Our careers are truncated and proxy-based rather than full §415(b) careers."
    ),
    "mismatch_codes": [
        "phase_a_generator_vs_dynasim_projection",
        "individual_aime_vs_shared_lifetime_income_quintile",
        "truncated_proxy_career_vs_full_415b_career",
        "single_eligibility_year_vs_mixed_eligibility_years",
    ],
}

PPI_SHARED_MISMATCH = {
    "frame": (
        "Our row is a report-only real-PSID-couple regrouping, not generated "
        "population output; DYNASIM is a projected synthetic population. No frame alignment is claimed."
    ),
    "population": (
        "Our common support contains observed PSID retirees/couples with a "
        "coverage restriction; DYNASIM reports 5,351 projected retired workers ages 62-67 in 2050."
    ),
    "year_basis": (
        "Observed 1998-2022 histories are transported to a single 2050 "
        "eligibility cohort; DYNASIM uses a mixed 2050 cross-section and 2005 assumptions."
    ),
    "benefit_concept": (
        "Both report own-record PPI benefits as percent of scheduled; our "
        "shared measure is only the ranking variable and benefits remain own-record."
    ),
    "earnings_and_accounting": (
        "Our shared-lifetime ranking matches Mermin's stated concept, but uses "
        "compressed proxy histories and a restricted PSID common support rather than full careers."
    ),
    "mismatch_codes": [
        "real_psid_common_support_vs_dynasim_projection",
        "truncated_proxy_career_vs_full_415b_career",
        "single_eligibility_year_vs_mixed_eligibility_years",
    ],
}


def build_ppi_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pi_block = ppi["three_way_comparison"]["pi_scalars"]
    pi_ours = pi_block["generated_pooled_mean_pct"]["mean"]
    pi_published = pi_block["dynasim_pct"]
    rows.append(
        {
            "row_id": "dynasim.mermin.price_indexing.all",
            "external_model": "DYNASIM3",
            "quantity": "Price-indexed benefit as percent of scheduled, all workers",
            "comparison_scope": ["ratio"],
            "our": {
                "value": pi_ours,
                "unit": "percent of scheduled benefit",
                "label_state": label_state(False),
                "source": source_pin(
                    "runs/replication_ppi_mermin_v1.json",
                    "/three_way_comparison/pi_scalars/generated_pooled_mean_pct/mean",
                ),
                "provenance_status": (
                    "reported-not-gated; gate-1 candidate 11 generator; not M6-certified"
                ),
            },
            "published": {
                "value": pi_published,
                "unit": "percent of scheduled benefit",
                "provenance": mermin_reported_value_provenance(
                    "runs/replication_ppi_mermin_v1.json",
                    "/three_way_comparison/pi_scalars/dynasim_pct",
                ),
                "source_locators": mermin_locator("Table 2", 16),
            },
            "deviation": scalar_deviation(pi_ours, pi_published),
            "concept_mismatch": deepcopy(PPI_GENERATED_MISMATCH),
            "evidential_status": "module replication; reported-not-gated",
        }
    )
    for index, item in enumerate(
        ppi["three_way_comparison"]["ppi_by_quintile"]
    ):
        ours = item["generated_pooled"]["mean"]
        published = item["dynasim_pct"]
        quintile = item["quintile"]
        rows.append(
            {
                "row_id": f"dynasim.mermin.ppi.generated.q{quintile}",
                "external_model": "DYNASIM3",
                "quantity": (
                    "Progressive-price-indexed benefit as percent of scheduled, "
                    f"generated individual-AIME quintile {quintile}"
                ),
                "comparison_scope": ["ratio", "distributional_share"],
                "our": {
                    "value": ours,
                    "unit": "percent of scheduled benefit",
                    "label_state": label_state(False),
                    "source": source_pin(
                        "runs/replication_ppi_mermin_v1.json",
                        f"/three_way_comparison/ppi_by_quintile/{index}/generated_pooled/mean",
                    ),
                    "provenance_status": (
                        "reported-not-gated; gate-1 candidate 11 generator; not M6-certified"
                    ),
                },
                "published": {
                    "value": published,
                    "unit": "percent of scheduled benefit",
                    "provenance": mermin_reported_value_provenance(
                        "runs/replication_ppi_mermin_v1.json",
                        f"/three_way_comparison/ppi_by_quintile/{index}/dynasim_pct",
                    ),
                    "source_locators": mermin_locator("Table 2", 16),
                },
                "deviation": scalar_deviation(ours, published),
                "concept_mismatch": deepcopy(PPI_GENERATED_MISMATCH),
                "evidential_status": "module replication; reported-not-gated",
            }
        )
    for index, item in enumerate(
        ppi_shared["three_way_comparison"]["ppi_by_quintile"]
    ):
        ours = item["shared_ppi_pct"]
        published = item["anchor_dynasim_ppi_pct"]
        quintile = item["quintile"]
        rows.append(
            {
                "row_id": f"dynasim.mermin.ppi.real_shared.q{quintile}",
                "external_model": "DYNASIM3",
                "quantity": (
                    "Progressive-price-indexed benefit as percent of scheduled, "
                    f"real-PSID shared-lifetime-income quintile {quintile}"
                ),
                "comparison_scope": ["ratio", "distributional_share"],
                "our": {
                    "value": ours,
                    "unit": "percent of scheduled benefit",
                    "label_state": label_state(False),
                    "source": source_pin(
                        "runs/replication_ppi_shared_v1.json",
                        f"/three_way_comparison/ppi_by_quintile/{index}/shared_ppi_pct",
                    ),
                    "provenance_status": "real-data-only; reported-not-gated",
                },
                "published": {
                    "value": published,
                    "unit": "percent of scheduled benefit",
                    "provenance": mermin_reported_value_provenance(
                        "runs/replication_ppi_shared_v1.json",
                        f"/three_way_comparison/ppi_by_quintile/{index}/anchor_dynasim_ppi_pct",
                    ),
                    "source_locators": mermin_locator("Table 2", 16),
                },
                "deviation": scalar_deviation(ours, published),
                "concept_mismatch": deepcopy(PPI_SHARED_MISMATCH),
                "evidential_status": "module replication; real-data-only; reported-not-gated",
            }
        )
    return rows


NRA_MISMATCH = {
    "frame": (
        "Our row is a real-data-only, report-not-gated module result on a "
        "restricted Phase-A PSID frame; DYNASIM is a projected population. No frame alignment is claimed."
    ),
    "population": (
        "Our retirees were eligible in 2005-2019 (births 1943-1957); DYNASIM "
        "reports projected retired workers ages 62-67 in 2050."
    ),
    "year_basis": (
        "Observed-era claim-age behavior is combined with a 2050-policy NRA; "
        "DYNASIM applies its 2050 cross-section under 2005 assumptions."
    ),
    "benefit_concept": (
        "Both are retired-worker own-record benefits as percent of scheduled, "
        "but ours is a person-weighted statutory-factor ratio with no earnings "
        "test or behavioral response; the published aggregate is dollar-weighted."
    ),
    "earnings_and_accounting": (
        "Our distribution ranks transported individual proxy AIME; Mermin ranks "
        "spouse-shared lifetime income."
    ),
    "mismatch_codes": [
        "observed_retirees_vs_projected_2050_cross_section",
        "observed_claim_age_behavior_vs_2050_behavior",
        "individual_aime_vs_shared_lifetime_income_quintile",
        "person_weighted_factor_ratio_vs_dollar_weighted_benefit_ratio",
    ],
}

COLA_MISMATCH = {
    "frame": NRA_MISMATCH["frame"],
    "population": NRA_MISMATCH["population"],
    "year_basis": NRA_MISMATCH["year_basis"],
    "benefit_concept": (
        "Our COLA ratio compounds from claim age; Mermin credits COLAs from age-62 "
        "first eligibility. The 80-85 row also uses our committed survival weighting."
    ),
    "earnings_and_accounting": (
        "The PIA-independent ratio does not validate benefit levels, lifetime "
        "accumulation, or population weights."
    ),
    "mismatch_codes": [
        "observed_retirees_vs_projected_2050_cross_section",
        "claim_age_cola_start_vs_age62_eligibility_start",
        "person_weighted_factor_ratio_vs_dollar_weighted_benefit_ratio",
        "module_survival_weighting_vs_dynasim_population_weighting",
    ],
}


def build_mermin_remaining_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    nra_table = mermin_rows["nra_raise_to_70"]["table"]
    for index, item in enumerate(nra_table["by_quintile"]):
        quintile = item["quintile"]
        ours = item["our_pct_of_scheduled"]
        published = item["anchor_pct"]
        rows.append(
            {
                "row_id": f"dynasim.mermin.nra70.q{quintile}",
                "external_model": "DYNASIM3",
                "quantity": (
                    "NRA-to-70 benefit as percent of scheduled, "
                    f"individual-AIME quintile {quintile}"
                ),
                "comparison_scope": ["ratio", "distributional_share"],
                "our": {
                    "value": ours,
                    "unit": "percent of scheduled benefit",
                    "label_state": label_state(False),
                    "source": source_pin(
                        "runs/replication_mermin_rows_v1.json",
                        f"/nra_raise_to_70/table/by_quintile/{index}/our_pct_of_scheduled",
                    ),
                    "provenance_status": "real-data-only; reported-not-gated",
                },
                "published": {
                    "value": published,
                    "unit": "percent of scheduled benefit",
                    "provenance": mermin_reported_value_provenance(
                        "runs/replication_mermin_rows_v1.json",
                        f"/nra_raise_to_70/table/by_quintile/{index}/anchor_pct",
                    ),
                    "source_locators": mermin_locator("Table 2", 16),
                },
                "deviation": scalar_deviation(ours, published),
                "concept_mismatch": deepcopy(NRA_MISMATCH),
                "evidential_status": "module replication; real-data-only; reported-not-gated",
            }
        )
    overall = nra_table["overall"]
    rows.append(
        {
            "row_id": "dynasim.mermin.nra70.all",
            "external_model": "DYNASIM3",
            "quantity": "NRA-to-70 benefit as percent of scheduled, all scored retirees",
            "comparison_scope": ["ratio"],
            "our": {
                "value": overall["our_pct_of_scheduled"],
                "unit": "percent of scheduled benefit",
                "label_state": label_state(False),
                "source": source_pin(
                    "runs/replication_mermin_rows_v1.json",
                    "/nra_raise_to_70/table/overall/our_pct_of_scheduled",
                ),
                "provenance_status": "real-data-only; reported-not-gated",
            },
            "published": {
                "value": overall["anchor_pct"],
                "unit": "percent of scheduled benefit",
                "provenance": mermin_reported_value_provenance(
                    "runs/replication_mermin_rows_v1.json",
                    "/nra_raise_to_70/table/overall/anchor_pct",
                ),
                "source_locators": mermin_locator("Table 2", 16),
            },
            "deviation": scalar_deviation(
                overall["our_pct_of_scheduled"], overall["anchor_pct"]
            ),
            "concept_mismatch": deepcopy(NRA_MISMATCH),
            "evidential_status": "module replication; real-data-only; reported-not-gated",
        }
    )
    for index, item in enumerate(mermin_rows["cola_minus_0_4pp"]["table"]):
        age_group = item["age_group"]
        ours = item["our_pct_of_scheduled"]
        published = item["anchor_pct"]
        if age_group == "62-67":
            locator = mermin_locator("Table 2", 16)
        else:
            locator = mermin_locator("Table 4", 18)
        rows.append(
            {
                "row_id": f"dynasim.mermin.cola_minus_0_4pp.age_{age_group.replace('-', '_')}",
                "external_model": "DYNASIM3",
                "quantity": (
                    "Benefit under COLA minus 0.4 percentage points as percent "
                    f"of scheduled, ages {age_group}"
                ),
                "comparison_scope": ["ratio", "age_trajectory"],
                "our": {
                    "value": ours,
                    "unit": "percent of scheduled benefit",
                    "label_state": label_state(False),
                    "source": source_pin(
                        "runs/replication_mermin_rows_v1.json",
                        f"/cola_minus_0_4pp/table/{index}/our_pct_of_scheduled",
                    ),
                    "provenance_status": "real-data-only; reported-not-gated",
                },
                "published": {
                    "value": published,
                    "unit": "percent of scheduled benefit",
                    "provenance": mermin_reported_value_provenance(
                        "runs/replication_mermin_rows_v1.json",
                        f"/cola_minus_0_4pp/table/{index}/anchor_pct",
                    ),
                    "source_locators": locator,
                },
                "deviation": scalar_deviation(ours, published),
                "concept_mismatch": deepcopy(COLA_MISMATCH),
                "evidential_status": "module replication; real-data-only; reported-not-gated",
            }
        )
    return rows


SHARING_MISMATCH = {
    "frame": (
        "Our row is a report-only real-PSID-couple replication on coverage-0.8 "
        "long-stayers; DYNASIM is a SIPP+PSID-calibrated synthetic projection. "
        "No frame or population alignment is claimed."
    ),
    "population": (
        "Our observed retirees were eligible in 2005-2019 (births 1943-1957); "
        "DYNASIM reports 1960-1980 cohorts evaluated in 2049. Spouse histories "
        "are often sparser in our frame."
    ),
    "year_basis": (
        "Our observed-era careers and expected claim-age reduction are used as "
        "the analogue; the publication is a 2049 projection with 2050 cost balancing."
    ),
    "benefit_concept": (
        "Both apply package 1b earnings sharing with no survivor benefit and a "
        "4.5% global increase, but our scalar is borrowed from DYNASIM rather "
        "than re-derived for cost neutrality and we omit mortality and within-couple claim timing."
    ),
    "earnings_and_accounting": (
        "Our sharing uses available PSID spouse earnings and the committed proxy "
        "PIA chain; DYNASIM uses its full synthetic careers and family histories."
    ),
    "mismatch_codes": [
        "observed_psid_couples_vs_dynasim_2049_projection",
        "sparse_spouse_histories",
        "anchor_calibrated_scalar_not_rederived",
        "no_mortality_or_within_couple_claim_timing",
    ],
}


def sharing_locator() -> list[dict[str, Any]]:
    return [
        {
            "publisher": "Urban Institute",
            "document": (
                "Favreault and Steuerle (2007), Social Security Spouse and "
                "Survivor Benefits for the Modern Family, report 311436, "
                "DYNASIM3 runid 440v2"
            ),
            "page": {"pdf": 30, "printed": 20},
            "table": "Table 3",
            "url": FAVREAULT_STEUERLE_URL,
            "reviewed_external_capture": deepcopy(
                REFRESH_REVIEW["captures"]["favreault_2007"]
            ),
        }
    ]


def build_sharing_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cells = sharing["package_1b_primary"]["magnitude_check"]["cells"]
    for index, item in enumerate(cells):
        cell_id = item["cell"].replace(":", ".")
        ours = item["our_share_pct"]
        published = item["dynasim_pct"]
        rows.append(
            {
                "row_id": f"dynasim.favreault_steuerle.package1b.{cell_id}",
                "external_model": "DYNASIM3",
                "quantity": (
                    "Package 1b winner/loser share: "
                    + item["cell"].replace(":", ", ")
                ),
                "comparison_scope": ["share", "distributional_incidence"],
                "our": {
                    "value": ours,
                    "unit": "percent of current-law scheduled beneficiaries in cell",
                    "label_state": label_state(False),
                    "source": source_pin(
                        "runs/replication_r7_sharing_v1.json",
                        f"/package_1b_primary/magnitude_check/cells/{index}/our_share_pct",
                    ),
                    "provenance_status": "real-couples-only; reported-not-gated",
                },
                "published": {
                    "value": published,
                    "unit": "percent of current-law scheduled beneficiaries in cell",
                    "source_locators": sharing_locator(),
                },
                "deviation": scalar_deviation(ours, published),
                "concept_mismatch": deepcopy(SHARING_MISMATCH),
                "evidential_status": (
                    "module replication; complete predeclared set of 12 anchor cells "
                    "with published share >=20%; reported-not-gated"
                ),
            }
        )
    return rows


ORDERING_MISMATCH = {
    "frame": (
        "Our ordinal result is scored once on a common Phase-A frame; the "
        "published order comes from DYNASIM/CBO actuarial scoring. No level alignment is claimed."
    ),
    "population": (
        "Our common restricted PSID career frame differs from DYNASIM's projected "
        "population and from the national actuarial population."
    ),
    "year_basis": (
        "Our result is a common-evaluation-age per-capita analogue; the published "
        "column is a 75-year actuarial effect under 2005 assumptions."
    ),
    "benefit_concept": (
        "Our ordering uses benefit-reduction magnitudes; the publication orders "
        "reductions in the 75-year deficit as a share of taxable payroll. Only rank order is compared."
    ),
    "earnings_and_accounting": (
        "Per-capita statutory benefit changes and actuarial-payroll balance effects "
        "have incompatible units; no numeric magnitude deviation is computed."
    ),
    "mismatch_codes": [
        "per_capita_benefit_delta_vs_75_year_actuarial_payroll_effect",
        "restricted_common_frame_vs_national_projection",
        "ordinal_only_no_level_matching",
    ],
}


def build_ordering_row() -> dict[str, Any]:
    test = ordering["tests"]["T2_mermin_kendall_tau"]
    return {
        "row_id": "dynasim.mermin.four_reform_cost_ordering",
        "external_model": "DYNASIM3 / CBO 2005 actuarial scoring",
        "quantity": "Ordinal benefit-reduction ordering across four reforms",
        "comparison_scope": ["ordering"],
        "our": {
            "value": test["our_order_by_reduction"],
            "unit": "descending ordinal benefit-reduction magnitude",
            "label_state": label_state(False),
            "source": source_pin(
                "runs/replication_cost_ordering_v1.json",
                "/tests/T2_mermin_kendall_tau/our_order_by_reduction",
            ),
            "provenance_status": "ordinal-only; reported-not-gated",
        },
        "published": {
            "value": test["anchor_order_by_reduction"],
            "unit": "descending ordinal 75-year deficit reduction",
            "provenance": mermin_reported_value_provenance(
                "runs/replication_cost_ordering_v1.json",
                "/tests/T2_mermin_kendall_tau/anchor_order_by_reduction",
            ),
            "source_locators": mermin_locator(
                "Table 1, 75-year deficit/surplus row", 15
            ),
        },
        "deviation": {
            "kendall_tau": test["kendall_tau"],
            "discordant_pair_count": 1,
            "pair_count": 6,
            "definition": (
                "Kendall tau compares the two descending orders; magnitudes are "
                "not subtracted because their units are incompatible"
            ),
        },
        "concept_mismatch": deepcopy(ORDERING_MISMATCH),
        "evidential_status": "ordinal synthesis; reported-not-gated",
    }


def wish_bill_locator(
    page: int, section: str, provision: str
) -> list[dict[str, Any]]:
    return [
        {
            "publisher": "United States Congress",
            "document": (
                "H.R. 4289 (117th Congress), Well-Being Insurance for Seniors "
                "to be at Home Act, introduced text (H.R. 4289 IH)"
            ),
            "page": {"pdf": page, "printed": page},
            "table": "not applicable (statutory text)",
            "section": section,
            "provision": provision,
            "url": WISH_BILL_PDF_URL,
            "reviewed_external_capture": deepcopy(
                REFRESH_REVIEW["captures"]["wish_bill_pdf"]
            ),
        }
    ]


def wish_financing_stub() -> dict[str, Any]:
    payroll_rows = first["tables"]["revenue"]["per_draw"]
    by_draw: dict[int, dict[int, float]] = {}
    for item in payroll_rows:
        by_draw.setdefault(item["draw_index"], {})[item["year"]] = item[
            "weighted_taxable_payroll"
        ]
    years = sorted(next(iter(by_draw.values())))
    annual = []
    for year in years:
        indices = [
            100.0 * values[year] / values[years[0]]
            for values in by_draw.values()
        ]
        annual.append(
            {
                "year": year,
                "mean_index_2015_100": statistics.mean(indices),
                "sample_sd_across_paired_draw_indices": statistics.stdev(
                    indices
                ),
            }
        )
    pairs = [(2015, 2016), (2017, 2018), (2019, 2020), (2021, 2022)]
    biennial = []
    for start, end in pairs:
        indices = []
        for values in by_draw.values():
            base = values[2015] + values[2016]
            indices.append(100.0 * (values[start] + values[end]) / base)
        biennial.append(
            {
                "component_years": [start, end],
                "mean_index_2015_2016_100": statistics.mean(indices),
                "sample_sd_across_paired_draw_indices": statistics.stdev(
                    indices
                ),
            }
        )
    return {
        "status": (
            "statutory_parameter_captured; actuarial_trajectory_and_adequacy_blocked"
        ),
        "quantity": "Mechanical single-side 0.3-percentage-point payroll surtax",
        "our": {
            "share_of_proxy_payroll": 0.003,
            "share_of_proxy_payroll_percent": 0.3,
            "share_of_modeled_combined_12_4_percent_contributions": 0.003
            / 0.124,
            "annual_relative_trajectory": annual,
            "odd_year_carry_aware_biennial_relative_trajectory": biennial,
            "absolute_revenue_levels_published": False,
            "trajectory_interpretation": (
                "A 0.003-times-proxy-payroll base index, not a policy-effective "
                "revenue forecast. The bill applies after 2021, so only 2022 "
                "overlaps the certified artifact's calendar span."
            ),
            "label_state": label_state(True),
            "source": source_pin(
                "runs/first_estimates_v1.json", "/tables/revenue/per_draw"
            ),
            "formula": "0.003 * weighted_taxable_payroll; trajectory normalized within draw",
        },
        "published": {
            "employee_rate_percent": 0.3,
            "employer_rate_percent": 0.3,
            "combined_wage_rate_percent": 0.6,
            "self_employment_rate_percent": 0.6,
            "effective_period": "wages received/paid after 2021",
            "source_locators": [
                *wish_bill_locator(
                    17,
                    "§5(a)(1)-(2)",
                    "employee and separate employer applicable percentages",
                ),
                *wish_bill_locator(
                    18,
                    "§5(a)(3)",
                    "self-employment applicable percentage",
                ),
            ],
            "actuarial_revenue_or_cost_trajectory": None,
        },
        "source_needed": [
            "primary ARC/Oliver Wyman actuarial memorandum",
            f"Morningstar full WISH report: {MORNINGSTAR_WISH_REPORT_URL}",
        ],
        "concept_mismatch": {
            "frame": (
                "Our base is the unaligned frame-relative proxy payroll; WISH "
                "actuarial work concerns a national covered-payroll base."
            ),
            "population": (
                "The artifact is a closed 2015-2022 reproduction panel, not the "
                "covered workforce or beneficiary population used by WISH actuaries."
            ),
            "year_basis": (
                "Our path ends in 2022 and is normalized to 2015; a WISH financing "
                "analysis uses a policy effective date and a long actuarial horizon."
            ),
            "benefit_concept": (
                "The current artifact has no LTSS eligibility, vesting, benefit, "
                "spend-down, adequacy, trust-fund, or program-cost model."
            ),
            "earnings_and_accounting": (
                "Multiplying proxy payroll by 0.003 is one statutory wage-tax "
                "side only. The bill separately imposes 0.3% on employers (0.6% "
                "combined, and 0.6% for self-employment), so this requested path "
                "is not total revenue or an actuarial solvency/sufficiency estimate."
            ),
        },
    }


def build_wish_parameter_row() -> dict[str, Any]:
    return {
        "row_id": "wish.hr4289.employee_rate.share_of_payroll",
        "external_model": "WISH Act statutory text (not an actuarial model)",
        "quantity": "Single-side WISH employee payroll-tax rate",
        "comparison_scope": ["share"],
        "our": {
            "value": 0.3,
            "unit": "percent of frame-relative proxy taxable payroll",
            "label_state": label_state(True),
            "source": source_pin(
                "runs/first_estimates_v1.json", "/tables/revenue/per_draw"
            ),
            "formula": "100 * (0.003 * weighted_taxable_payroll) / weighted_taxable_payroll",
            "provenance_status": "mechanical single-side parameter check only",
        },
        "published": {
            "value": 0.3,
            "unit": "percent of IRC §3121(a) wages received after 2021",
            "companion_parameters": {
                "separate_employer_rate_percent": 0.3,
                "combined_employee_employer_rate_percent": 0.6,
                "self_employment_rate_percent": 0.6,
            },
            "source_locators": wish_bill_locator(
                17,
                "§5(a)(1)-(2)",
                "employee rate and separate employer rate after 2021",
            ),
        },
        "deviation": {
            "signed_percentage_points": 0.0,
            "our_over_published_ratio": 1.0,
            "definition": "ours minus published employee-side rate",
        },
        "concept_mismatch": {
            "frame": (
                "Our denominator is an unaligned frame-relative labor-income "
                "proxy; the bill applies nationally to IRC §3121(a) wages."
            ),
            "population": (
                "Our closed 2015-2022 PSID reproduction panel is not the national "
                "employee population subject to the proposed tax."
            ),
            "year_basis": (
                "The scalar parameter matches, but the bill applies after 2021; "
                "only 2022 overlaps our artifact and no published revenue path exists."
            ),
            "benefit_concept": (
                "The bill finances a new LTSS benefit; our artifact models only "
                "own-record Social Security retirement benefits and no LTSS outcome."
            ),
            "earnings_and_accounting": (
                "The requested 0.003 calculation represents only the employee "
                "side. The bill separately levies employers at 0.3% and self-employment "
                "at 0.6%; this row is not a total-financing or actuarial check."
            ),
            "mismatch_codes": [
                "proxy_payroll_vs_irc_3121a_wages",
                "closed_panel_vs_national_tax_base",
                "single_side_vs_combined_financing",
                "no_actuarial_revenue_or_cost_projection",
                "no_ltss_benefit_model",
            ],
        },
        "evidential_status": (
            "statutory single-side parameter identity; not actuarial validation"
        ),
    }


def available_series_inventory() -> dict[str, Any]:
    tables: dict[str, Any] = {}
    for table_name, table in first["tables"].items():
        per_draw = table["per_draw"]
        aggregates = table["aggregate"]
        tables[table_name] = {
            "json_pointer": f"/tables/{table_name}",
            "labels": table["labels"],
            "unit_label": table["unit_label"],
            "years": sorted({item["year"] for item in per_draw}),
            "draw_indices": sorted({item["draw_index"] for item in per_draw}),
            "per_draw_row_count": len(per_draw),
            "per_draw_fields": list(per_draw[0]),
            "aggregate_row_count": len(aggregates),
            "aggregate_metrics": sorted(
                {item["metric"] for item in aggregates}
            ),
            "biennial_companion_row_count": len(table["biennial_companion"]),
            "odd_year_carry_disclosure": table["odd_year_carry_disclosure"],
        }
    return {
        "source": source_pin("runs/first_estimates_v1.json", "/"),
        "projection": first["configuration_echo"]["projection"],
        "tables": tables,
        "counts": {
            "per_draw_row_count": len(first["counts"]["per_draw"]),
            "aggregate_metric_count": len(first["counts"]["aggregate"]),
            "aggregate_metrics": [
                item["metric"] for item in first["counts"]["aggregate"]
            ],
        },
        "diagnostics": {
            "per_draw_row_count": len(first["diagnostics"]["per_draw"]),
            "aggregate_metric_count": len(first["diagnostics"]["aggregate"]),
            "aggregate_metrics": [
                item["metric"] for item in first["diagnostics"]["aggregate"]
            ],
            "included_career_per_draw_row_count": len(
                first["diagnostics"]["included_career_per_draw"]
            ),
            "additional_objects": [
                "birth_timing_sensitivity",
                "common_support_agreement",
                "context_ratio",
                "payment_year_convention",
                "benefit_measure",
                "revenue_population_basis",
            ],
        },
        "entry10_comparisons": {
            "evaluated": [
                item["comparison_id"]
                for item in context["results"]["comparison_results"]
                if item["evaluated"]
            ],
            "unavailable": [
                {
                    "comparison_id": item["comparison_id"],
                    "reason": item["reason"],
                }
                for item in context["results"]["comparison_results"]
                if not item["evaluated"]
            ],
        },
    }


def blocked_comparisons(wish: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "comparison_id": "ssa.award_average_at_award",
            "external_model": "SSA administrative series",
            "status": "blocked",
            "reason": "OACT annual award average is not registered in vintage 1.",
            "our_support": "available",
            "published_support": "not in committed anchor extraction",
        },
        {
            "comparison_id": "ssa.retired_worker_monthly_benefit_per_beneficiary",
            "external_model": "SSA administrative series",
            "status": "blocked",
            "reason": (
                "December total monthly retired-worker benefit numerator is not "
                "registered in vintage 1."
            ),
            "our_support": "available",
            "published_support": "not in committed anchor extraction",
        },
        {
            "comparison_id": "mint.replacement_rates_and_distribution",
            "external_model": "MINT",
            "status": "blocked",
            "reason": (
                "The REFRESH supplies published MINT quantities, but first_estimates "
                "publishes no birth-cohort or age-67 cut, AWI or household-income "
                "denominator, benefit percentile, claiming-age distribution, or "
                "lifetime-earnings replacement-rate distribution."
            ),
            "our_support": "not available in comparable concept",
            "published_support": (
                "MINT8 report and SSA MINT8.23 beneficiary tables captured and reviewed"
            ),
            "published_examples_not_promoted_to_rows": [
                {
                    "quantity": (
                        "Average per-capita Social Security income relative to "
                        "average wage at age 67"
                    ),
                    "cohorts": [
                        "1936-39",
                        "1940-49",
                        "1950-59",
                        "1960-69",
                        "1970-79",
                        "1980-89",
                        "1990-99",
                        "2000-09",
                        "2010-19",
                        "2020-29",
                        "2030-32",
                    ],
                    "published_values": [
                        0.26,
                        0.28,
                        0.25,
                        0.21,
                        0.20,
                        0.19,
                        0.19,
                        0.19,
                        0.20,
                        0.20,
                        0.21,
                    ],
                    "locator": {
                        "document": "Urban Institute MINT8 Final Report",
                        "page": {"pdf": 16},
                        "table": "Figure 4",
                        "reviewed_external_capture": deepcopy(
                            REFRESH_REVIEW["captures"]["mint8_report"]
                        ),
                    },
                },
                {
                    "quantity": (
                        "Mean household-income share from Social Security, all "
                        "current-law beneficiaries age 60 or older"
                    ),
                    "years": [2024, 2030, 2050, 2070],
                    "published_percent": [42, 43, 48, 50],
                    "locator": {
                        "document": "SSA Projected Profile of Beneficiaries",
                        "page": "not applicable (HTML)",
                        "table": (
                            "tableIncome2024, tableIncome2030, tableIncome2050, "
                            "tableIncome2070; All beneficiaries > Total"
                        ),
                        "reviewed_external_capture": deepcopy(
                            REFRESH_REVIEW["captures"][
                                "ssa_mint_beneficiary_tables"
                            ]
                        ),
                    },
                },
            ],
        },
        {
            "comparison_id": "cbo.cohort_lifetime_and_fiscal_outputs",
            "external_model": "CBOLT / CBO",
            "status": "blocked",
            "reason": (
                "Two overlapping 2015-2022 share/trajectory rows are built, but "
                "the certified artifact has no cohort replacement rates, lifetime "
                "benefit/tax accumulation, age-65 present values, household-earnings "
                "quintiles, trust-fund, GDP, actuarial-balance, or depletion series."
            ),
            "our_support": (
                "taxable-payroll trajectory and contribution/payroll share only"
            ),
            "published_support": (
                "2024 report and data workbooks captured; unsupported tables have exact locators"
            ),
            "published_examples_not_promoted_to_rows": [
                {
                    "quantity": "Initial replacement rates",
                    "locator": (
                        "cbo-60392-Long-Term-Projections.xlsx sheet 10, all "
                        "workers A14:R18, men A20:R24, women A26:R30, definitions A34:A38"
                    ),
                },
                {
                    "quantity": "Retired-worker lifetime benefits relative to earnings",
                    "locator": (
                        "same workbook sheet 11, A14:R30, definitions A34:A38"
                    ),
                },
                {
                    "quantity": "Lifetime benefit-to-tax ratios",
                    "locator": (
                        "same workbook sheet 14, A12:I46, definitions A50:A54"
                    ),
                },
            ],
        },
        {
            "comparison_id": "dynasim.lifetime_benefit_tax_and_cohort_tables",
            "external_model": "DYNASIM",
            "status": "blocked",
            "reason": (
                "The entry-8 artifact has no lifetime accumulation, discounting, "
                "post-2022 survival path, or comparable cohort/quintile output."
            ),
            "our_support": "not available in comparable concept",
            "published_support": (
                "Favreault-Steuerle Table 4 captured; DYNASIM4 workbook remains 404"
            ),
            "published_examples_not_promoted_to_rows": [
                {
                    "quantity": "Lifetime benefits / payroll taxes by married cohort",
                    "locator": {
                        "document": (
                            "Favreault and Steuerle (2007), Social Security Spouse "
                            "and Survivor Benefits for the Modern Family"
                        ),
                        "page": {"pdf": 33, "printed": 23},
                        "table": "Table 4",
                        "reviewed_external_capture": deepcopy(
                            REFRESH_REVIEW["captures"]["favreault_2007"]
                        ),
                    },
                }
            ],
        },
        {
            "comparison_id": "wish.financing_and_adequacy",
            "external_model": "WISH actuaries / Morningstar",
            "status": "blocked",
            "reason": (
                "No ARC/Oliver Wyman memorandum is present. The full Morningstar "
                "WISH report identified by the captured landing page is not staged; "
                "the staged technical appendix is generic and contains no WISH analysis. "
                "The unpaginated webpage summary cannot supply a page/table-level "
                "actuarial revenue, cost, balance, sufficiency, or adequacy row."
            ),
            "our_support": (
                "single-side 0.3% identity and 2015-2022 proxy-payroll base trajectory only"
            ),
            "published_support": (
                "bill parameter and Morningstar summary captured; primary actuarial "
                "memo and paginated Morningstar WISH report absent"
            ),
            "published_examples_not_promoted_to_rows": [
                {
                    "quantity": (
                        "Retirement-shortfall rates among households projected "
                        "to qualify for WISH benefits"
                    ),
                    "published_values": {
                        "single_women_percent": {"without": 58, "with": 28},
                        "single_men_percent": {"without": 34, "with": 16},
                    },
                    "locator": {
                        "document": "Morningstar WISH Granted landing page",
                        "page": "not applicable (unpaginated HTML)",
                        "table": "Key Findings, first bullet",
                        "reviewed_external_capture": deepcopy(
                            REFRESH_REVIEW["captures"][
                                "morningstar_wish_landing"
                            ]
                        ),
                    },
                    "warning": (
                        "Notes-only: full report/table absent and our artifact "
                        "has no retirement-shortfall or LTSS model."
                    ),
                }
            ],
        },
    ]


rows: list[dict[str, Any]] = []
rows.extend(build_trustees_rows())
rows.extend(build_cbo_rows())
rows.extend(build_sharing_rows())
wish = wish_financing_stub()
rows.append(build_wish_parameter_row())

reported_not_verified: list[dict[str, Any]] = []
reported_not_verified.extend(build_ppi_rows())
reported_not_verified.extend(build_mermin_remaining_rows())
reported_not_verified.append(build_ordering_row())

for row in rows:
    row["verification_class"] = "verified"
for row in reported_not_verified:
    row["verification_class"] = "reported_not_verified"

all_rows = [*rows, *reported_not_verified]
assert len(rows) == 22
assert len(reported_not_verified) == 20
assert len({row["row_id"] for row in all_rows}) == len(all_rows)
assert not any(".mermin." in row["row_id"] for row in rows)
for row in all_rows:
    assert row["our"]["label_state"]["population_alignment_claim"] is False
    assert all(row["concept_mismatch"].values())
    assert row["published"]["source_locators"]

matrix = {
    "schema_version": "cross_model_validation_matrix.v2",
    "canonicalization": "UTF-8, sorted keys, indent=2, allow_nan=false, one trailing newline",
    "purpose": (
        "Frame-relative comparison of ratios, shares, trajectories, and orderings "
        "against published SSA, CBO, DYNASIM, and WISH statutory quantities; "
        "never national dollar levels"
    ),
    "honesty_frame": {
        "allowed_comparison_scopes": [
            "ratio",
            "share",
            "trajectory",
            "ordering",
        ],
        "absolute_dollar_level_comparisons": False,
        "population_alignment_claim": False,
        "source_artifact_labels": SOURCE_ARTIFACT_LABELS,
        "ratified_fitting_free_exact_label_array": RATIFIED_FITTING_FREE_LABELS,
        "ratified_array_locator": (
            "docs/design/covered_earnings_correction.md §16.7.1"
        ),
        "ratified_array_activation_asserted_by_this_matrix": False,
        "interpretation": (
            "Every row remains a frame-relative proxy-covered-earnings result. "
            "The exact ratified array is quoted, while the committed entry-8 and "
            "entry-10 artifacts retain their legacy embedded array; this matrix "
            "does not assert the external activation event."
        ),
    },
    "inputs": [
        {"path": relative, "sha256": sha256(relative)}
        for relative in INPUT_PATHS
    ],
    "external_capture_review": REFRESH_REVIEW,
    "available_series_inventory": available_series_inventory(),
    "certification_context": {
        "entry8_first_estimates": {
            "source": source_pin("runs/first_estimates_v1.json", "/"),
            "configured_engine": first["configuration_echo"][
                "candidate_specs"
            ],
        },
        "m6": {
            "source": source_pin(
                "runs/gate_m6_candidate3_v1.json", "/verdict"
            ),
            "status": m6["verdict"]["status"],
            "valid": m6["verdict"]["valid"],
            "n_seeds_pass": m6["gate_contract_result"]["n_seeds_pass"],
            "seed_pass": m6["gate_contract_result"]["seed_pass"],
            "family_a_gated": True,
            "family_b_gated": m6["family_b"]["gated"],
            "family_c_gated": m6["family_c"]["gating"],
            "not_certified": [
                {"margin": item["margin"], "detail": item["detail"]}
                for item in m6["family_b"]["not_certified"]
            ],
        },
        "ppi_gate1_generator": {
            "source": source_pin("runs/gate1_rank_knn_v5.json", "/verdict"),
            "gate_1_pass": gate1["verdict"]["gate_1_pass"],
            "geometry_seed_passes": gate1["verdict"]["n_geometry_pass"],
            "battery_seed_passes": gate1["verdict"]["n_battery_pass"],
            "warning": (
                "PPI generated rows use this backward-law generator and are "
                "reported-not-gated module replications; M6 certification does not transfer."
            ),
        },
    },
    "row_count": len(rows),
    "total_row_count": len(all_rows),
    "rows": rows,
    "reported_not_verified": {
        "row_count": len(reported_not_verified),
        "reason": (
            "Mermin publisher-controlled bytes were not retrievable; values "
            "are retained from committed replication artifacts but are not "
            "accepted as verified external-source cells."
        ),
        "rows": reported_not_verified,
    },
    "wish_financing_stub": wish,
    "blocked_comparisons": blocked_comparisons(wish),
    "honest_gaps": [
        "No population-aligned or national-dollar comparison is supported.",
        "No certified series extends beyond 2022.",
        "No trust-fund balance, GDP share, actuarial balance, or depletion year is published.",
        "No lifetime benefit/tax present value or lifetime-earnings denominator is published.",
        "No comparable MINT or CBOLT distributional replacement-rate output is published.",
        "No spouse, survivor, auxiliary, or DI benefit output appears in first_estimates.",
        "No cohort/quintile/race/sex/poverty distribution comparable to published model tables appears in first_estimates.",
        "No LTSS use, eligibility, spend-down, adequacy, program cost, or financing-sufficiency model exists.",
    ],
}

OUT.write_text(
    json.dumps(
        matrix, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
    )
    + "\n",
    encoding="utf-8",
)
