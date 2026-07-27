"""Frozen registries for the anchor-context report.

This module contains only design-ratified literals and exact-registry
validation.  It does not open either production input.
"""

from __future__ import annotations

import copy
from typing import Any

DESIGN_PATH = "docs/design/anchor_context_extraction.md"
DESIGN_RATIFICATION_COMMIT = (
    "1ad337d3a3eaeba3369a3405469b1e74335e156a"
)
DESIGN_REVISION = 4

REPORT_SCHEMA_VERSION = "anchor_context_report.v1"
CONFIGURATION_SCHEMA_VERSION = "anchor_context_report_configuration.v1"
INCIDENT_SCHEMA_VERSION = "anchor_context_report_incident.v1"

FIRST_ESTIMATES_INPUT_PATH = "runs/first_estimates_v1.json"
FIRST_ESTIMATES_INPUT_SHA256 = (
    "719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977"
)
ANCHOR_INPUT_PATH = (
    "data/external/"
    "ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
)
ANCHOR_ARTIFACT_VINTAGE_ID = (
    "ssa_level_anchors.supplement2025_trustees2026.vintage1"
)
ANCHOR_INPUT_SHA256 = (
    "adc782a1a11c50969103c125a82b1539a7017241662d545d86bc6fc9227730c1"
)

PRIMARY_OUTPUT_PATH = "runs/anchor_context_report_v1.json"
SIDECAR_OUTPUT_PATH = "runs/anchor_context_report_v1.json.env.json"

REPORT_YEARS = tuple(range(2015, 2023))
DRAW_INDICES = tuple(range(20))
EXPECTED_DRAW_YEAR_COUNT = len(REPORT_YEARS) * len(DRAW_INDICES)

REQUIRED_SERIES_IDS = (
    "retired_worker_awards",
    "retired_worker_benefits_paid_estimated_allocation",
    "oasi_benefits_paid_estimated_allocation",
    "oasi_trust_fund_benefit_payments",
    "oasdi_trust_fund_benefit_payments",
    "retired_worker_december_current_payment_stock",
    "oasi_december_current_payment_stock",
    "oasdi_december_current_payment_stock",
    "oasdi_workers_with_taxable_earnings",
    "oasdi_reported_taxable_earnings",
    "oasdi_gross_contributions",
    "oasdi_adjusted_taxable_payroll",
    "oasdi_covered_workers",
    "oasi_net_payroll_tax_contributions",
    "oasdi_net_payroll_tax_contributions",
)

_MODEL_METRIC_SPECS: list[dict[str, Any]] = [
    {
        "model_metric_id": (
            "modeled_award_flow.average_monthly_benefit_at_award"
        ),
        "operation": "select",
        "operands": [
            {
                "row_pointer": "/tables/modeled_award_flow/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "average_monthly_benefit_at_award",
                "required_row_values": {"claim_origin": "modeled_award"},
                "required_table_unit_label": (
                    "annualized statutory benefit, eligibility-PIA with "
                    "COLA, no recomputation"
                ),
                "value_unit": "current_dollars_per_month",
            }
        ],
        "unit": "current_dollars_per_month",
    },
    {
        "model_metric_id": "modeled_award_flow.weighted_award_count",
        "operation": "select",
        "operands": [
            {
                "row_pointer": "/tables/modeled_award_flow/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "weighted_award_count",
                "required_row_values": {"claim_origin": "modeled_award"},
                "required_table_unit_label": (
                    "annualized statutory benefit, eligibility-PIA with "
                    "COLA, no recomputation"
                ),
                "value_unit": "frame_weighted_annual_awards",
            }
        ],
        "unit": "frame_weighted_annual_awards",
    },
    {
        "model_metric_id": (
            "combined_own_retirement.frame_annualized_benefit"
        ),
        "operation": "same_key_sum",
        "operands": [
            {
                "row_pointer": "/tables/modeled_award_flow/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "frame_annualized_benefit",
                "required_row_values": {"claim_origin": "modeled_award"},
                "required_table_unit_label": (
                    "annualized statutory benefit, eligibility-PIA with "
                    "COLA, no recomputation"
                ),
                "value_unit": (
                    "nominal_frame_relative_annualized_statutory_benefit_"
                    "dollars_per_calendar_year"
                ),
            },
            {
                "row_pointer": "/tables/opening_stock/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "frame_annualized_benefit",
                "required_row_values": {"claim_origin": "opening_backfill"},
                "required_table_unit_label": (
                    "report-only imputed opening stock; annualized "
                    "statutory benefit, eligibility-PIA with COLA, no "
                    "recomputation"
                ),
                "value_unit": (
                    "nominal_frame_relative_annualized_statutory_benefit_"
                    "dollars_per_calendar_year"
                ),
            },
        ],
        "unit": (
            "nominal_frame_relative_annualized_statutory_benefit_"
            "dollars_per_calendar_year"
        ),
    },
    {
        "model_metric_id": (
            "combined_own_retirement.weighted_beneficiary_count"
        ),
        "operation": "same_key_sum",
        "operands": [
            {
                "row_pointer": "/tables/modeled_award_flow/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "weighted_beneficiary_count",
                "required_row_values": {"claim_origin": "modeled_award"},
                "required_table_unit_label": (
                    "annualized statutory benefit, eligibility-PIA with "
                    "COLA, no recomputation"
                ),
                "value_unit": "frame_weighted_annual_beneficiary_count",
            },
            {
                "row_pointer": "/tables/opening_stock/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "weighted_beneficiary_count",
                "required_row_values": {"claim_origin": "opening_backfill"},
                "required_table_unit_label": (
                    "report-only imputed opening stock; annualized "
                    "statutory benefit, eligibility-PIA with COLA, no "
                    "recomputation"
                ),
                "value_unit": "frame_weighted_annual_beneficiary_count",
            },
        ],
        "unit": "frame_weighted_annual_beneficiary_count",
    },
    {
        "model_metric_id": "revenue.weighted_taxable_payroll",
        "operation": "select",
        "operands": [
            {
                "row_pointer": "/tables/revenue/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "weighted_taxable_payroll",
                "required_row_values": {},
                "required_table_unit_label": (
                    "nominal frame-relative OASDI payroll contributions "
                    "on the labor-income proxy"
                ),
                "value_unit": (
                    "nominal_frame_relative_taxable_payroll_dollars_per_"
                    "calendar_year"
                ),
            }
        ],
        "unit": (
            "nominal_frame_relative_taxable_payroll_dollars_per_calendar_"
            "year"
        ),
    },
    {
        "model_metric_id": "revenue.weighted_covered_earner_count",
        "operation": "select",
        "operands": [
            {
                "row_pointer": "/tables/revenue/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "weighted_covered_earner_count",
                "required_row_values": {},
                "required_table_unit_label": (
                    "nominal frame-relative OASDI payroll contributions "
                    "on the labor-income proxy"
                ),
                "value_unit": "frame_weighted_positive_proxy_earner_count",
            }
        ],
        "unit": "frame_weighted_positive_proxy_earner_count",
    },
    {
        "model_metric_id": "revenue.combined_contributions",
        "operation": "select",
        "operands": [
            {
                "row_pointer": "/tables/revenue/per_draw",
                "key_fields": ["draw_index", "year"],
                "value_field": "combined_contributions",
                "required_row_values": {},
                "required_table_unit_label": (
                    "nominal frame-relative OASDI payroll contributions "
                    "on the labor-income proxy"
                ),
                "value_unit": (
                    "nominal_frame_relative_combined_oasdi_contribution_"
                    "dollars_per_calendar_year"
                ),
            }
        ],
        "unit": (
            "nominal_frame_relative_combined_oasdi_contribution_dollars_"
            "per_calendar_year"
        ),
    },
]

_PAIRINGS: list[dict[str, Any]] = [
    {
        "pairing_id": "pair_retired_worker_awards",
        "model_metric_id": "modeled_award_flow.weighted_award_count",
        "anchor_series_id": "retired_worker_awards",
        "mismatch_codes": [
            "administrative_award_vs_mechanical_claim_stamp",
            "program_population_scope",
        ],
    },
    {
        "pairing_id": (
            "pair_retired_worker_benefits_paid_estimated_allocation"
        ),
        "model_metric_id": (
            "combined_own_retirement.frame_annualized_benefit"
        ),
        "anchor_series_id": (
            "retired_worker_benefits_paid_estimated_allocation"
        ),
        "mismatch_codes": [
            "annualized_statutory_amount_vs_actual_outlay",
            (
                "psid_labor_income_proxy_history_vs_administrative_"
                "covered_earnings_history"
            ),
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
            "official_estimated_allocation",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": "pair_oasi_benefits_paid_estimated_allocation",
        "model_metric_id": (
            "combined_own_retirement.frame_annualized_benefit"
        ),
        "anchor_series_id": "oasi_benefits_paid_estimated_allocation",
        "mismatch_codes": [
            "annualized_statutory_amount_vs_actual_outlay",
            (
                "psid_labor_income_proxy_history_vs_administrative_"
                "covered_earnings_history"
            ),
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
            "official_estimated_allocation",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": "pair_oasi_trust_fund_benefit_payments",
        "model_metric_id": (
            "combined_own_retirement.frame_annualized_benefit"
        ),
        "anchor_series_id": "oasi_trust_fund_benefit_payments",
        "mismatch_codes": [
            "annualized_statutory_amount_vs_actual_outlay",
            (
                "psid_labor_income_proxy_history_vs_administrative_"
                "covered_earnings_history"
            ),
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": "pair_oasdi_trust_fund_benefit_payments",
        "model_metric_id": (
            "combined_own_retirement.frame_annualized_benefit"
        ),
        "anchor_series_id": "oasdi_trust_fund_benefit_payments",
        "mismatch_codes": [
            "annualized_statutory_amount_vs_actual_outlay",
            (
                "psid_labor_income_proxy_history_vs_administrative_"
                "covered_earnings_history"
            ),
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": (
            "pair_retired_worker_december_current_payment_stock"
        ),
        "model_metric_id": (
            "combined_own_retirement.weighted_beneficiary_count"
        ),
        "anchor_series_id": (
            "retired_worker_december_current_payment_stock"
        ),
        "mismatch_codes": [
            "annual_presence_vs_december_current_payment_stock",
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
        ],
    },
    {
        "pairing_id": "pair_oasi_december_current_payment_stock",
        "model_metric_id": (
            "combined_own_retirement.weighted_beneficiary_count"
        ),
        "anchor_series_id": "oasi_december_current_payment_stock",
        "mismatch_codes": [
            "annual_presence_vs_december_current_payment_stock",
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
        ],
    },
    {
        "pairing_id": "pair_oasdi_december_current_payment_stock",
        "model_metric_id": (
            "combined_own_retirement.weighted_beneficiary_count"
        ),
        "anchor_series_id": "oasdi_december_current_payment_stock",
        "mismatch_codes": [
            "annual_presence_vs_december_current_payment_stock",
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
        ],
    },
    {
        "pairing_id": "pair_oasdi_workers_with_taxable_earnings",
        "model_metric_id": "revenue.weighted_covered_earner_count",
        "anchor_series_id": "oasdi_workers_with_taxable_earnings",
        "mismatch_codes": [
            "positive_proxy_vs_workers_with_taxable_earnings",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": "pair_oasdi_reported_taxable_earnings",
        "model_metric_id": "revenue.weighted_taxable_payroll",
        "anchor_series_id": "oasdi_reported_taxable_earnings",
        "mismatch_codes": [
            "labor_income_proxy_vs_reported_taxable_earnings",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_reported_wages",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": "pair_oasdi_gross_contributions",
        "model_metric_id": "revenue.combined_contributions",
        "anchor_series_id": "oasdi_gross_contributions",
        "mismatch_codes": [
            "earnings_year_rate_arithmetic_vs_gross_contributions",
            "labor_income_proxy_vs_taxable_earnings",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_reported_wages",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": "pair_oasdi_adjusted_taxable_payroll",
        "model_metric_id": "revenue.weighted_taxable_payroll",
        "anchor_series_id": "oasdi_adjusted_taxable_payroll",
        "mismatch_codes": [
            "labor_income_proxy_vs_adjusted_taxable_payroll",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_adjusted_payroll",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": "pair_oasdi_covered_workers",
        "model_metric_id": "revenue.weighted_covered_earner_count",
        "anchor_series_id": "oasdi_covered_workers",
        "mismatch_codes": [
            "positive_proxy_vs_trustees_covered_workers",
            "odd_year_earnings_carry",
        ],
    },
    {
        "pairing_id": "pair_oasdi_net_payroll_tax_contributions",
        "model_metric_id": "revenue.combined_contributions",
        "anchor_series_id": "oasdi_net_payroll_tax_contributions",
        "mismatch_codes": [
            "earnings_year_rate_arithmetic_vs_trust_fund_cash",
            "labor_income_proxy_vs_taxable_earnings",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_reported_wages",
            "odd_year_earnings_carry",
        ],
    },
]

_COMPARISON_SPECS: list[dict[str, Any]] = [
    {
        "comparison_id": "cmp_award_average_at_award",
        "availability": {
            "status": "unavailable",
            "reason": "oact_annual_award_average_not_registered_in_v1",
        },
        "model_numerator_metric_id": (
            "modeled_award_flow.average_monthly_benefit_at_award"
        ),
        "model_denominator_metric_id": None,
        "model_formula": (
            'metric("modeled_award_flow.'
            'average_monthly_benefit_at_award",d,y)'
        ),
        "official_numerator_series_id": None,
        "official_denominator_series_id": None,
        "official_formula": None,
        "operation": "model_value_over_official_value",
        "timing_scope": "complete_calendar_year_retired_worker_awards",
        "accounting_scope": (
            "model_statutory_award_amount_vs_administrative_amount_due_at_"
            "award"
        ),
        "mismatch_codes": [
            "administrative_award_vs_mechanical_claim_stamp",
            (
                "official_amount_due_at_award_vs_claim_adjusted_"
                "eligibility_pia_no_aero"
            ),
            "program_population_scope",
            (
                "psid_labor_income_proxy_history_vs_administrative_"
                "covered_earnings_history"
            ),
            "odd_year_earnings_carry",
        ],
    },
    {
        "comparison_id": (
            "cmp_retired_worker_monthly_benefit_per_beneficiary"
        ),
        "availability": {
            "status": "unavailable",
            "reason": (
                "retired_worker_december_total_monthly_benefit_not_"
                "registered_in_vintage1"
            ),
        },
        "model_numerator_metric_id": (
            "combined_own_retirement.frame_annualized_benefit"
        ),
        "model_denominator_metric_id": (
            "combined_own_retirement.weighted_beneficiary_count"
        ),
        "model_formula": (
            'metric("combined_own_retirement.frame_annualized_benefit",'
            'd,y)/(12*metric("combined_own_retirement.'
            'weighted_beneficiary_count",d,y))'
        ),
        "official_numerator_series_id": None,
        "official_denominator_series_id": (
            "retired_worker_december_current_payment_stock"
        ),
        "official_formula": None,
        "operation": "model_intensity_over_official_intensity",
        "timing_scope": (
            "model_calendar_year_annual_presence_vs_official_december_"
            "current_payment"
        ),
        "accounting_scope": (
            "model_annualized_statutory_amount_vs_official_monthly_"
            "current_payment_amount"
        ),
        "mismatch_codes": [
            (
                "annualized_statutory_amount_vs_december_current_payment_"
                "amount"
            ),
            (
                "psid_labor_income_proxy_history_vs_administrative_"
                "covered_earnings_history"
            ),
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "annual_presence_vs_december_current_payment_stock",
            "program_population_scope",
            "odd_year_earnings_carry",
        ],
    },
    {
        "comparison_id": "cmp_reported_taxable_earnings_per_worker",
        "availability": {"status": "available", "reason": None},
        "model_numerator_metric_id": "revenue.weighted_taxable_payroll",
        "model_denominator_metric_id": (
            "revenue.weighted_covered_earner_count"
        ),
        "model_formula": (
            'metric("revenue.weighted_taxable_payroll",d,y)/'
            'metric("revenue.weighted_covered_earner_count",d,y)'
        ),
        "official_numerator_series_id": (
            "oasdi_reported_taxable_earnings"
        ),
        "official_denominator_series_id": (
            "oasdi_workers_with_taxable_earnings"
        ),
        "official_formula": (
            'official("oasdi_reported_taxable_earnings",y)/'
            'official("oasdi_workers_with_taxable_earnings",y)'
        ),
        "operation": "model_intensity_over_official_intensity",
        "timing_scope": "calendar_year_earnings_flow_per_annual_worker",
        "accounting_scope": (
            "model_proxy_taxable_payroll_vs_supplement_reported_taxable_"
            "earnings"
        ),
        "mismatch_codes": [
            "labor_income_proxy_vs_reported_taxable_earnings",
            "positive_proxy_vs_workers_with_taxable_earnings",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_reported_wages",
            "odd_year_earnings_carry",
        ],
    },
    {
        "comparison_id": (
            "cmp_adjusted_taxable_payroll_per_covered_worker"
        ),
        "availability": {"status": "available", "reason": None},
        "model_numerator_metric_id": "revenue.weighted_taxable_payroll",
        "model_denominator_metric_id": (
            "revenue.weighted_covered_earner_count"
        ),
        "model_formula": (
            'metric("revenue.weighted_taxable_payroll",d,y)/'
            'metric("revenue.weighted_covered_earner_count",d,y)'
        ),
        "official_numerator_series_id": (
            "oasdi_adjusted_taxable_payroll"
        ),
        "official_denominator_series_id": "oasdi_covered_workers",
        "official_formula": (
            'official("oasdi_adjusted_taxable_payroll",y)/'
            'official("oasdi_covered_workers",y)'
        ),
        "operation": "model_intensity_over_official_intensity",
        "timing_scope": (
            "calendar_year_adjusted_payroll_flow_per_annual_covered_worker"
        ),
        "accounting_scope": (
            "model_proxy_taxable_payroll_vs_trustees_adjusted_taxable_"
            "payroll"
        ),
        "mismatch_codes": [
            "labor_income_proxy_vs_adjusted_taxable_payroll",
            "positive_proxy_vs_trustees_covered_workers",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_adjusted_payroll",
            "odd_year_earnings_carry",
        ],
    },
    {
        "comparison_id": "cmp_gross_contributions_per_worker",
        "availability": {"status": "available", "reason": None},
        "model_numerator_metric_id": "revenue.combined_contributions",
        "model_denominator_metric_id": (
            "revenue.weighted_covered_earner_count"
        ),
        "model_formula": (
            'metric("revenue.combined_contributions",d,y)/'
            'metric("revenue.weighted_covered_earner_count",d,y)'
        ),
        "official_numerator_series_id": "oasdi_gross_contributions",
        "official_denominator_series_id": (
            "oasdi_workers_with_taxable_earnings"
        ),
        "official_formula": (
            'official("oasdi_gross_contributions",y)/'
            'official("oasdi_workers_with_taxable_earnings",y)'
        ),
        "operation": "model_intensity_over_official_intensity",
        "timing_scope": (
            "calendar_year_contribution_flow_per_annual_worker"
        ),
        "accounting_scope": (
            "model_earnings_year_rate_arithmetic_vs_supplement_gross_"
            "contributions"
        ),
        "mismatch_codes": [
            "earnings_year_rate_arithmetic_vs_gross_contributions",
            "labor_income_proxy_vs_taxable_earnings",
            "positive_proxy_vs_workers_with_taxable_earnings",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_reported_wages",
            "odd_year_earnings_carry",
        ],
    },
    {
        "comparison_id": (
            "cmp_net_payroll_tax_contributions_per_covered_worker"
        ),
        "availability": {"status": "available", "reason": None},
        "model_numerator_metric_id": "revenue.combined_contributions",
        "model_denominator_metric_id": (
            "revenue.weighted_covered_earner_count"
        ),
        "model_formula": (
            'metric("revenue.combined_contributions",d,y)/'
            'metric("revenue.weighted_covered_earner_count",d,y)'
        ),
        "official_numerator_series_id": (
            "oasdi_net_payroll_tax_contributions"
        ),
        "official_denominator_series_id": "oasdi_covered_workers",
        "official_formula": (
            'official("oasdi_net_payroll_tax_contributions",y)/'
            'official("oasdi_covered_workers",y)'
        ),
        "operation": "model_intensity_over_official_intensity",
        "timing_scope": (
            "calendar_year_trust_fund_cash_flow_per_annual_covered_worker"
        ),
        "accounting_scope": (
            "model_earnings_year_rate_arithmetic_vs_trust_fund_cash"
        ),
        "mismatch_codes": [
            "earnings_year_rate_arithmetic_vs_trust_fund_cash",
            "labor_income_proxy_vs_taxable_earnings",
            "positive_proxy_vs_trustees_covered_workers",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_reported_wages",
            "odd_year_earnings_carry",
        ],
    },
    {
        "comparison_id": (
            "cmp_retired_worker_beneficiaries_per_worker"
        ),
        "availability": {"status": "available", "reason": None},
        "model_numerator_metric_id": (
            "combined_own_retirement.weighted_beneficiary_count"
        ),
        "model_denominator_metric_id": (
            "revenue.weighted_covered_earner_count"
        ),
        "model_formula": (
            'metric("combined_own_retirement.weighted_beneficiary_count",'
            'd,y)/metric("revenue.weighted_covered_earner_count",d,y)'
        ),
        "official_numerator_series_id": (
            "retired_worker_december_current_payment_stock"
        ),
        "official_denominator_series_id": (
            "oasdi_workers_with_taxable_earnings"
        ),
        "official_formula": (
            'official("retired_worker_december_current_payment_stock",y)/'
            'official("oasdi_workers_with_taxable_earnings",y)'
        ),
        "operation": "model_intensity_over_official_intensity",
        "timing_scope": (
            "model_calendar_year_annual_presence_vs_official_december_"
            "stock_per_annual_worker"
        ),
        "accounting_scope": (
            "model_own_retirement_presence_vs_administrative_retired_"
            "worker_current_payment"
        ),
        "mismatch_codes": [
            "annual_presence_vs_december_current_payment_stock",
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
            "positive_proxy_vs_workers_with_taxable_earnings",
            "odd_year_earnings_carry",
        ],
    },
    {
        "comparison_id": "cmp_retired_worker_awards_per_worker",
        "availability": {"status": "available", "reason": None},
        "model_numerator_metric_id": (
            "modeled_award_flow.weighted_award_count"
        ),
        "model_denominator_metric_id": (
            "revenue.weighted_covered_earner_count"
        ),
        "model_formula": (
            'metric("modeled_award_flow.weighted_award_count",d,y)/'
            'metric("revenue.weighted_covered_earner_count",d,y)'
        ),
        "official_numerator_series_id": "retired_worker_awards",
        "official_denominator_series_id": (
            "oasdi_workers_with_taxable_earnings"
        ),
        "official_formula": (
            'official("retired_worker_awards",y)/'
            'official("oasdi_workers_with_taxable_earnings",y)'
        ),
        "operation": "model_intensity_over_official_intensity",
        "timing_scope": "calendar_year_awards_per_annual_worker",
        "accounting_scope": (
            "model_mechanical_claim_stamp_vs_administrative_retired_"
            "worker_award"
        ),
        "mismatch_codes": [
            "administrative_award_vs_mechanical_claim_stamp",
            "program_population_scope",
            "positive_proxy_vs_workers_with_taxable_earnings",
            "odd_year_earnings_carry",
        ],
    },
    {
        "comparison_id": (
            "cmp_retired_worker_benefits_per_reported_taxable_earnings"
        ),
        "availability": {"status": "available", "reason": None},
        "model_numerator_metric_id": (
            "combined_own_retirement.frame_annualized_benefit"
        ),
        "model_denominator_metric_id": "revenue.weighted_taxable_payroll",
        "model_formula": (
            'metric("combined_own_retirement.frame_annualized_benefit",'
            'd,y)/metric("revenue.weighted_taxable_payroll",d,y)'
        ),
        "official_numerator_series_id": (
            "retired_worker_benefits_paid_estimated_allocation"
        ),
        "official_denominator_series_id": (
            "oasdi_reported_taxable_earnings"
        ),
        "official_formula": (
            'official("retired_worker_benefits_paid_estimated_allocation",'
            'y)/official("oasdi_reported_taxable_earnings",y)'
        ),
        "operation": "model_intensity_over_official_intensity",
        "timing_scope": (
            "calendar_year_benefit_flow_per_calendar_year_taxable_earnings"
        ),
        "accounting_scope": (
            "model_annualized_statutory_amount_vs_estimated_retired_"
            "worker_outlay_share"
        ),
        "mismatch_codes": [
            "annualized_statutory_amount_vs_actual_outlay",
            (
                "psid_labor_income_proxy_history_vs_administrative_"
                "covered_earnings_history"
            ),
            "opening_backfill_imputation",
            "mechanical_claiming_vs_administrative_in_force_population",
            "program_population_scope",
            "official_estimated_allocation",
            "labor_income_proxy_vs_reported_taxable_earnings",
            "negative_proxy_no_zero_floor",
            "consolidated_person_cap_vs_reported_wages",
            "odd_year_earnings_carry",
        ],
    },
]

_REGISTRY_NAMES = (
    "required_series_ids",
    "model_metric_specs",
    "pairings",
    "comparison_specs",
)


class RegistryValidationError(ValueError):
    """A supplied registry differs from the ratified registry."""


def design_binding() -> dict[str, Any]:
    """Return a deep JSON copy of the ratified design binding."""

    return {
        "path": DESIGN_PATH,
        "ratification_commit": DESIGN_RATIFICATION_COMMIT,
        "revision": DESIGN_REVISION,
    }


def first_estimates_input_identity() -> dict[str, str]:
    """Return the registered first-estimates input identity."""

    return {
        "path": FIRST_ESTIMATES_INPUT_PATH,
        "sha256": FIRST_ESTIMATES_INPUT_SHA256,
    }


def anchor_input_identity() -> dict[str, str]:
    """Return the registered official-anchor input identity."""

    return {
        "path": ANCHOR_INPUT_PATH,
        "artifact_vintage_id": ANCHOR_ARTIFACT_VINTAGE_ID,
        "sha256": ANCHOR_INPUT_SHA256,
    }


def required_series_ids() -> list[str]:
    """Return a fresh JSON array in the ratified 15-series order."""

    return list(REQUIRED_SERIES_IDS)


def model_metric_specs() -> list[dict[str, Any]]:
    """Return a deep JSON copy of the ratified seven-metric registry."""

    return copy.deepcopy(_MODEL_METRIC_SPECS)


def pairings() -> list[dict[str, Any]]:
    """Return a deep JSON copy of the ratified 14-pairing registry."""

    return copy.deepcopy(_PAIRINGS)


def comparison_specs() -> list[dict[str, Any]]:
    """Return a deep JSON copy of the ratified nine-comparison registry."""

    return copy.deepcopy(_COMPARISON_SPECS)


def frozen_registries() -> dict[str, Any]:
    """Return fresh JSON containers for all four registered arrays."""

    return {
        "required_series_ids": required_series_ids(),
        "model_metric_specs": model_metric_specs(),
        "pairings": pairings(),
        "comparison_specs": comparison_specs(),
    }


def _path_child(path: str, child: object) -> str:
    if isinstance(child, int):
        return f"{path}[{child}]"
    return f"{path}.{child}"


def _sorted_reprs(values: set[object]) -> list[str]:
    return sorted(repr(value) for value in values)


def _assert_exact_json(actual: object, expected: object, path: str) -> None:
    """Compare JSON values without Python's bool/int equality coercion."""

    if type(actual) is not type(expected):
        raise RegistryValidationError(
            f"{path} has type {type(actual).__name__}; "
            f"expected {type(expected).__name__}"
        )
    if isinstance(expected, dict):
        actual_keys = set(actual)
        expected_keys = set(expected)
        if actual_keys != expected_keys:
            missing = _sorted_reprs(expected_keys - actual_keys)
            extra = _sorted_reprs(actual_keys - expected_keys)
            raise RegistryValidationError(
                f"{path} has wrong object keys; "
                f"missing={missing}, extra={extra}"
            )
        for key, expected_value in expected.items():
            _assert_exact_json(
                actual[key],
                expected_value,
                _path_child(path, key),
            )
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise RegistryValidationError(
                f"{path} has length {len(actual)}; "
                f"expected {len(expected)}"
            )
        for index, (actual_value, expected_value) in enumerate(
            zip(actual, expected, strict=True)
        ):
            _assert_exact_json(
                actual_value,
                expected_value,
                _path_child(path, index),
            )
        return
    if actual != expected:
        raise RegistryValidationError(
            f"{path} is {actual!r}; expected {expected!r}"
        )


def validate_exact_registry(registry_name: str, value: object) -> None:
    """Validate one named registry by type-aware exact deep equality."""

    if type(registry_name) is not str or registry_name not in _REGISTRY_NAMES:
        raise RegistryValidationError(
            f"registry_name must be one of {_REGISTRY_NAMES!r}"
        )
    expected = frozen_registries()[registry_name]
    _assert_exact_json(value, expected, registry_name)


def validate_frozen_registries(
    *,
    required_series_ids: object,
    model_metric_specs: object,
    pairings: object,
    comparison_specs: object,
) -> None:
    """Validate all frozen registries, preserving every array position."""

    supplied = {
        "required_series_ids": required_series_ids,
        "model_metric_specs": model_metric_specs,
        "pairings": pairings,
        "comparison_specs": comparison_specs,
    }
    for registry_name in _REGISTRY_NAMES:
        validate_exact_registry(registry_name, supplied[registry_name])


__all__ = [
    "ANCHOR_ARTIFACT_VINTAGE_ID",
    "ANCHOR_INPUT_PATH",
    "ANCHOR_INPUT_SHA256",
    "CONFIGURATION_SCHEMA_VERSION",
    "DESIGN_PATH",
    "DESIGN_RATIFICATION_COMMIT",
    "DESIGN_REVISION",
    "DRAW_INDICES",
    "EXPECTED_DRAW_YEAR_COUNT",
    "FIRST_ESTIMATES_INPUT_PATH",
    "FIRST_ESTIMATES_INPUT_SHA256",
    "INCIDENT_SCHEMA_VERSION",
    "PRIMARY_OUTPUT_PATH",
    "REPORT_SCHEMA_VERSION",
    "REPORT_YEARS",
    "REQUIRED_SERIES_IDS",
    "RegistryValidationError",
    "SIDECAR_OUTPUT_PATH",
    "anchor_input_identity",
    "comparison_specs",
    "design_binding",
    "first_estimates_input_identity",
    "frozen_registries",
    "model_metric_specs",
    "pairings",
    "required_series_ids",
    "validate_exact_registry",
    "validate_frozen_registries",
]
