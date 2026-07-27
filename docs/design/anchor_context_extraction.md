# The anchor context extraction: pinned official SSA series and the context report

- **Status:** DRAFT revision 4 for referee rounds. Nothing here authorizes an
  extraction commit, registration, or production report run.
- **Resolves:** only the §12 annual SSA/Trustees level-anchor extraction
  successor named first in leverage order by the first estimates report.
  This design does **not** resolve amendment 1's deferred §7 context ratio.
  The separately named OACT successor and its resolution criterion are in
  §3. Forecast-ledger entry 10 registers against this design's resolution
  criterion when the design ratifies.
- **Evidence base:** the entry-8 published artifact
  (`runs/first_estimates_v1.json`, sha256
  `719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977`)
  for the model-side concepts, and the 2026-07-26 anchor scoping survey
  reproduced in the ratification PR record for the official-series
  determinations. Official values are transcribed only by the later
  provenance-pinned extraction; this design does not hard-code them.

## 1. What this is — and the one thing it is not

A **context-anchor extraction** is an immutable, provenance-pinned artifact
vintage of official SSA/Trustees annual series for 2015-2022. A separate
**context report** presents model and official context under the comparison
law in §4, with the complete mismatch law attached to every registered
pairing.

It is **not level alignment**. No model number is scaled, calibrated,
reweighted, corrected toward, or characterized as a share of an official
total. The report's three labels — `frame-relative`, `pre-alignment`, and
`labor-income proxy` — remain on every model table. The W1 national bridge
remains a separate, later successor. The report distinguishes concepts and
publishes only the scale-invariant comparisons authorized below; it makes no
claim that the closed model frame is an estimate of what SSA pays or collects.

## 2. The extraction and immutable vintage

The first artifact is the literal versioned path
`data/external/ssa_level_anchors_supplement2025_trustees2026_vintage1.json`.
Its immutable `artifact_vintage_id` is the literal
`ssa_level_anchors.supplement2025_trustees2026.vintage1`. The generic name
`ssa_level_anchors.json` is not an artifact identity and must not be consumed
as a moving alias.

The artifact follows the committed `ssa_cola_history.json` precedent:
explicit schema, deterministic offline build, canonical content hash,
coverage assertions, and a verified-against statement, extended by the
following fail-closed laws.

### 2.1 Schema identity, vintage identity, and exact series identity

- `schema_version` is the literal `ssa_level_anchors.v1`. It changes only
  when the artifact's shape changes; it is not a data-vintage number.
- `artifact_vintage_id` and the versioned filename above identify the
  immutable bytes, source captures, normalized values, and expected artifact
  hash of vintage 1.
- `artifact_role` is the literal `official_context_only`, which confers no
  alignment authority.
- `year_basis` is `calendar_year`, and
  `required_calendar_years` equals `[2015, 2016, 2017, 2018, 2019, 2020,
  2021, 2022]` exactly.
- `required_series_ids` equals the following ordered 15-literal array
  exactly, and the keys of `determinations` equal the same set with no
  missing or extra key:

```json
[
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
  "oasdi_net_payroll_tax_contributions"
]
```

These literal identities correspond, in order, to Supplement 6.A1
retired-worker awards; Supplement 4.A5 retired-worker and OASI estimated
benefit allocations; Supplement 4.A1 and 4.A3 OASI/OASDI trust-fund benefit
payments; Supplement 5.A4 retired-worker/OASI/OASDI December current-payment
stocks; Supplement 4.B11 OASDI workers, reported taxable earnings, and gross
contributions; Trustees VI.G1 adjusted taxable payroll; Trustees IV.B4
covered workers; and Supplement 4.A1/4.A3 OASI/OASDI net payroll-tax
contributions.

### 2.2 Source and cell law

Each determination carries its literal `series_id`, exact official concept
and scope, published and stored units without silent rescaling, accounting
and time basis, and a `source_table` object. `source_table` contains the exact
publication, edition/report year, reviewed table ID, exact published table
title, and a reference to a literal source-document manifest entry. Every
manifest entry contains the exact official URL, committed raw-snapshot path,
retrieval timestamp, and sha256 of the exact captured bytes.

Trustees source identity is reviewed literal data, never generated from a
filename, URL, or table-number pattern. In vintage 1 this includes the
verified `lr4b4.html`/Table IV.B4 and `lr6g1.html`/Table VI.G1 identities.
The historical migrations IV.B3→IV.B4 and VI.G6→VI.G1 are the concrete
reason generation is forbidden.

Every one of the eight observation objects under each determination contains:

- normalized numeric `value`, literal source-cell `as_published`, explicit
  `published_unit`, `stored_unit`, and any exact scale multiplier;
- `year_basis: calendar_year` and the literal calendar year;
- `source_document_id`, exact `source_table_id`, and source URL;
- exact `source_row_header_path` and `source_column_header_path`, preserving
  every nested header needed to identify one cell; and
- per-cell `source_status` plus a statement that `verified_against` means
  exact-cell transcription, not concept equivalence.

Status is cell authority. For all three registered Table 4.B11 series,
2015-2020 cells must be `historical` and 2021-2022 cells must be
`preliminary`; any other classification aborts. Every Table 4.A5 observation
must be `estimated_allocation`, preserving the Supplement's warning that
benefit-type allocations are estimated and can differ from trust-fund
accounting totals. A convenience `preliminary_years` field, if emitted, is
derived from the cell statuses and exact-checked against them; it can never
override them.

### 2.3 Build, refresh, and fail-closed verification

A committed builder reads only the committed, hash-verified raw snapshots,
parses the registered cells, and emits canonical JSON deterministically and
offline. A reproduction test pins the artifact sha256 and rebuilds it in CI.
Network access occurs only when a coordinator captures a proposed new
vintage, never during a build or report.

A refresh appends a new artifact-vintage ID, versioned filename, raw snapshot
set, manifest entry, values, hashes, and referee record. Every prior artifact,
snapshot, source hash, value, and expected artifact hash remains retained
byte-for-byte. A refresh may not replace vintage 1 in place; a
`schema_version` change is reserved for a shape change.

Extraction or validation aborts on a missing/extra/reordered required ID; a
missing year, unit, literal cell, status, URL, source hash, title, table ID,
or row/column header path; a locator that selects a different cell; a
generated Trustees identity; source-byte or canonical-value drift; a
preliminary cell presented as final; a 4.A5 cell not marked estimated
allocation; or a `verified_against` claim of conceptual equivalence. No
missing official value is interpolated, backfilled, or synthesized.

## 3. Amendment-1 disposition and the OACT successor

Supplement Table 6.A2 splits each year into January-November and December.
Those subperiod averages cannot produce one annual average without subperiod
award weights that this design does not invent. That is a limitation of the
static table, not proof that an annual denominator is impossible: OACT can
return annual cells.

Amendment 1 therefore remains `deferred_to_anchor_extraction` in
`runs/first_estimates_v1.json`, which this work does not edit. The separate
**OACT annual award-average pinned-capture successor** resolves the deferral
only when a referee-ratified artifact records and verifies:

1. the exact request method and submitted request, including every parameter
   or POST-body byte;
2. the response URL or exact POST identity;
3. the aggregation definition requested and returned;
4. the committed response bytes and their sha256; and
5. exactly one verified annual **retired-worker average monthly benefit at
   award**, covering the complete calendar year, in dollars per month and not
   average PIA, for every year 2015-2022.

The future OACT comparison has this exact ordered mismatch-code array:

```json
[
  "administrative_award_vs_mechanical_claim_stamp",
  "official_amount_due_at_award_vs_claim_adjusted_eligibility_pia_no_aero",
  "program_population_scope",
  "psid_labor_income_proxy_history_vs_administrative_covered_earnings_history",
  "odd_year_earnings_carry"
]
```

The second code means that the official value is the administratively due
amount at award, while the model value is a claim-age-adjusted,
COLA-stepped eligibility PIA with no AERO recomputation. The fourth means
that SSA uses administrative covered-earnings history while the model uses
PSID labor-income-proxy history. The first, third, and fifth retain the
meanings frozen in §4.1. No nonempty subset or reordered version of this
array is sufficient.

The sole resolving sequence is: referee-ratified pinned OACT artifact →
fresh registration for `anchor_context_report.v2`, including the new
artifact, schema/version, exact model selector, exact OACT series selector,
the exact scope note `model own-retirement awards vs administrative
retired-worker awards`, and exact mismatch array above → one registered run
→ append-only v2 report and environment sidecar → publication-PR merge. Only
that publication-PR merge resolves the OACT successor and amendment 1.
Artifact ratification, registration, computation, or creation of unmerged
report bytes does not. The OACT artifact alone does not amend v1's frozen
registries.

Landing-page or request-and-response bytes without the method, parameters,
aggregation identity, and annual-cell verification do not meet the
criterion.

## 4. The context report

### 4.1 Pairing objects, crosswalk, and mismatch inventory

The published first-estimates artifact has exactly the three table objects
`tables.modeled_award_flow`, `tables.opening_stock`, and `tables.revenue`.
It has no `combined_own_retirement` object. Model IDs are executable only
through this exact ordered `model_metric_specs` registry:

```json
[
  {
    "model_metric_id": "modeled_award_flow.average_monthly_benefit_at_award",
    "operation": "select",
    "operands": [
      {
        "row_pointer": "/tables/modeled_award_flow/per_draw",
        "key_fields": ["draw_index", "year"],
        "value_field": "average_monthly_benefit_at_award",
        "required_row_values": {"claim_origin": "modeled_award"},
        "required_table_unit_label": "annualized statutory benefit, eligibility-PIA with COLA, no recomputation",
        "value_unit": "current_dollars_per_month"
      }
    ],
    "unit": "current_dollars_per_month"
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
        "required_table_unit_label": "annualized statutory benefit, eligibility-PIA with COLA, no recomputation",
        "value_unit": "frame_weighted_annual_awards"
      }
    ],
    "unit": "frame_weighted_annual_awards"
  },
  {
    "model_metric_id": "combined_own_retirement.frame_annualized_benefit",
    "operation": "same_key_sum",
    "operands": [
      {
        "row_pointer": "/tables/modeled_award_flow/per_draw",
        "key_fields": ["draw_index", "year"],
        "value_field": "frame_annualized_benefit",
        "required_row_values": {"claim_origin": "modeled_award"},
        "required_table_unit_label": "annualized statutory benefit, eligibility-PIA with COLA, no recomputation",
        "value_unit": "nominal_frame_relative_annualized_statutory_benefit_dollars_per_calendar_year"
      },
      {
        "row_pointer": "/tables/opening_stock/per_draw",
        "key_fields": ["draw_index", "year"],
        "value_field": "frame_annualized_benefit",
        "required_row_values": {"claim_origin": "opening_backfill"},
        "required_table_unit_label": "report-only imputed opening stock; annualized statutory benefit, eligibility-PIA with COLA, no recomputation",
        "value_unit": "nominal_frame_relative_annualized_statutory_benefit_dollars_per_calendar_year"
      }
    ],
    "unit": "nominal_frame_relative_annualized_statutory_benefit_dollars_per_calendar_year"
  },
  {
    "model_metric_id": "combined_own_retirement.weighted_beneficiary_count",
    "operation": "same_key_sum",
    "operands": [
      {
        "row_pointer": "/tables/modeled_award_flow/per_draw",
        "key_fields": ["draw_index", "year"],
        "value_field": "weighted_beneficiary_count",
        "required_row_values": {"claim_origin": "modeled_award"},
        "required_table_unit_label": "annualized statutory benefit, eligibility-PIA with COLA, no recomputation",
        "value_unit": "frame_weighted_annual_beneficiary_count"
      },
      {
        "row_pointer": "/tables/opening_stock/per_draw",
        "key_fields": ["draw_index", "year"],
        "value_field": "weighted_beneficiary_count",
        "required_row_values": {"claim_origin": "opening_backfill"},
        "required_table_unit_label": "report-only imputed opening stock; annualized statutory benefit, eligibility-PIA with COLA, no recomputation",
        "value_unit": "frame_weighted_annual_beneficiary_count"
      }
    ],
    "unit": "frame_weighted_annual_beneficiary_count"
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
        "required_table_unit_label": "nominal frame-relative OASDI payroll contributions on the labor-income proxy",
        "value_unit": "nominal_frame_relative_taxable_payroll_dollars_per_calendar_year"
      }
    ],
    "unit": "nominal_frame_relative_taxable_payroll_dollars_per_calendar_year"
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
        "required_table_unit_label": "nominal frame-relative OASDI payroll contributions on the labor-income proxy",
        "value_unit": "frame_weighted_positive_proxy_earner_count"
      }
    ],
    "unit": "frame_weighted_positive_proxy_earner_count"
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
        "required_table_unit_label": "nominal frame-relative OASDI payroll contributions on the labor-income proxy",
        "value_unit": "nominal_frame_relative_combined_oasdi_contribution_dollars_per_calendar_year"
      }
    ],
    "unit": "nominal_frame_relative_combined_oasdi_contribution_dollars_per_calendar_year"
  }
]
```

Every `row_pointer` is an RFC 6901 JSON Pointer resolving to the named
row array; pointers to `aggregate` or any fallback path are forbidden. The
benefit arrays have exactly the keys `draw_index`, `claim_origin`, `year`,
`unweighted_award_count`, `weighted_award_count`,
`average_monthly_benefit_at_award`, `unweighted_beneficiary_count`,
`weighted_beneficiary_count`, and `frame_annualized_benefit`. The revenue
array has exactly `draw_index`, `year`, `unweighted_person_year_count`,
`weighted_person_year_count`, `unweighted_covered_earner_count`,
`weighted_covered_earner_count`, `weighted_taxable_payroll`,
`employee_contributions`, `employer_contributions`,
`combined_contributions`, and `odd_year_carry_affected`.

Each array must contain exactly the 160-key Cartesian grid
`draw_index = 0..19` × `year = 2015..2022`. Validation detects duplicate
keys before constructing an index and then rejects a missing or extra key,
unequal operand grids, wrong `claim_origin`, absent/null/non-numeric/nonfinite
selected values, a changed `required_table_unit_label`, unequal operand
`value_unit` values, a result `unit` unequal to its operand `value_unit`, or a
nonpositive ratio denominator. The table labels are exact source-inventory
assertions; field-specific `value_unit` is the compatibility law, so the
different flow and opening-stock table labels do not prevent their two
registered same-unit sums. A `same_key_sum` joins its two operands on exactly
`(draw_index, year)` and sums only after both rows pass those assertions. The
validator exact-checks the registry above, including entry and operand order,
object key sets, every literal selector, operation, row constraint, table
label, value unit, and result unit.

These selectors were checked against the published
`runs/first_estimates_v1.json` bytes on published master at the pinned hash:
all nine operand selectors exist and are numeric and non-null in all 160
rows, both combined joins are one-to-one and complete, and every \(N\),
\(P\), and \(W\) value used as a denominator is positive.

Mismatch metadata belongs to a comparison, not a source series. Level
pairings below annotate only the two separate descriptive level panels; a
pairing does not authorize a derived comparison. The
`anchor_context_report.v1` configuration contains this ordered `pairings`
array. Each object has exactly `pairing_id`, `model_metric_id`,
`anchor_series_id`, and an ordered, nonempty `mismatch_codes` array. The v1
validator asserts exact equality, including array order, with all 14 rows
below; no schema-valid v1 report may omit, add, or reassign a pairing or
mismatch code.

| `pairing_id` | `model_metric_id` | `anchor_series_id` | ordered `mismatch_codes` |
|---|---|---|---|
| `pair_retired_worker_awards` | `modeled_award_flow.weighted_award_count` | `retired_worker_awards` | [`administrative_award_vs_mechanical_claim_stamp`, `program_population_scope`] |
| `pair_retired_worker_benefits_paid_estimated_allocation` | `combined_own_retirement.frame_annualized_benefit` | `retired_worker_benefits_paid_estimated_allocation` | [`annualized_statutory_amount_vs_actual_outlay`, `psid_labor_income_proxy_history_vs_administrative_covered_earnings_history`, `opening_backfill_imputation`, `program_population_scope`, `official_estimated_allocation`, `odd_year_earnings_carry`] |
| `pair_oasi_benefits_paid_estimated_allocation` | `combined_own_retirement.frame_annualized_benefit` | `oasi_benefits_paid_estimated_allocation` | [`annualized_statutory_amount_vs_actual_outlay`, `psid_labor_income_proxy_history_vs_administrative_covered_earnings_history`, `opening_backfill_imputation`, `program_population_scope`, `official_estimated_allocation`, `odd_year_earnings_carry`] |
| `pair_oasi_trust_fund_benefit_payments` | `combined_own_retirement.frame_annualized_benefit` | `oasi_trust_fund_benefit_payments` | [`annualized_statutory_amount_vs_actual_outlay`, `psid_labor_income_proxy_history_vs_administrative_covered_earnings_history`, `opening_backfill_imputation`, `program_population_scope`, `odd_year_earnings_carry`] |
| `pair_oasdi_trust_fund_benefit_payments` | `combined_own_retirement.frame_annualized_benefit` | `oasdi_trust_fund_benefit_payments` | [`annualized_statutory_amount_vs_actual_outlay`, `psid_labor_income_proxy_history_vs_administrative_covered_earnings_history`, `opening_backfill_imputation`, `program_population_scope`, `odd_year_earnings_carry`] |
| `pair_retired_worker_december_current_payment_stock` | `combined_own_retirement.weighted_beneficiary_count` | `retired_worker_december_current_payment_stock` | [`annual_presence_vs_december_current_payment_stock`, `opening_backfill_imputation`, `program_population_scope`] |
| `pair_oasi_december_current_payment_stock` | `combined_own_retirement.weighted_beneficiary_count` | `oasi_december_current_payment_stock` | [`annual_presence_vs_december_current_payment_stock`, `opening_backfill_imputation`, `program_population_scope`] |
| `pair_oasdi_december_current_payment_stock` | `combined_own_retirement.weighted_beneficiary_count` | `oasdi_december_current_payment_stock` | [`annual_presence_vs_december_current_payment_stock`, `opening_backfill_imputation`, `program_population_scope`] |
| `pair_oasdi_workers_with_taxable_earnings` | `revenue.weighted_covered_earner_count` | `oasdi_workers_with_taxable_earnings` | [`positive_proxy_vs_workers_with_taxable_earnings`, `odd_year_earnings_carry`] |
| `pair_oasdi_reported_taxable_earnings` | `revenue.weighted_taxable_payroll` | `oasdi_reported_taxable_earnings` | [`labor_income_proxy_vs_reported_taxable_earnings`, `negative_proxy_no_zero_floor`, `consolidated_person_cap_vs_reported_wages`, `odd_year_earnings_carry`] |
| `pair_oasdi_gross_contributions` | `revenue.combined_contributions` | `oasdi_gross_contributions` | [`earnings_year_rate_arithmetic_vs_gross_contributions`, `labor_income_proxy_vs_taxable_earnings`, `negative_proxy_no_zero_floor`, `consolidated_person_cap_vs_reported_wages`, `odd_year_earnings_carry`] |
| `pair_oasdi_adjusted_taxable_payroll` | `revenue.weighted_taxable_payroll` | `oasdi_adjusted_taxable_payroll` | [`labor_income_proxy_vs_adjusted_taxable_payroll`, `negative_proxy_no_zero_floor`, `consolidated_person_cap_vs_adjusted_payroll`, `odd_year_earnings_carry`] |
| `pair_oasdi_covered_workers` | `revenue.weighted_covered_earner_count` | `oasdi_covered_workers` | [`positive_proxy_vs_trustees_covered_workers`, `odd_year_earnings_carry`] |
| `pair_oasdi_net_payroll_tax_contributions` | `revenue.combined_contributions` | `oasdi_net_payroll_tax_contributions` | [`earnings_year_rate_arithmetic_vs_trust_fund_cash`, `labor_income_proxy_vs_taxable_earnings`, `negative_proxy_no_zero_floor`, `consolidated_person_cap_vs_reported_wages`, `odd_year_earnings_carry`] |

The frozen mismatch meanings are:

- `administrative_award_vs_mechanical_claim_stamp`: SSA records an
  administratively effectuated, payable-not-guaranteed award; the model stamps
  a mechanical claim-age crossing.
- `official_amount_due_at_award_vs_claim_adjusted_eligibility_pia_no_aero`:
  SSA records the administratively due amount at award; the model records a
  claim-age-adjusted, COLA-stepped eligibility PIA and performs no AERO
  recomputation.
- `annualized_statutory_amount_vs_actual_outlay`: the model records and
  annualizes 12 times the claim-age-adjusted, COLA-stepped eligibility PIA for
  each included claimant-year, with no partial first/last years or post-claim
  AERO recomputation; the anchor records actual outlays to an administrative
  in-force population.
- `annualized_statutory_amount_vs_december_current_payment_amount`: the model
  annualizes the claim-age-adjusted, COLA-stepped eligibility PIA over its
  annual-presence population; the unavailable 5.A4 numerator would be the
  total monthly amount in current-payment status in December, not an annual
  outlay.
- `psid_labor_income_proxy_history_vs_administrative_covered_earnings_history`:
  benefit inputs use PSID labor-income-proxy histories, which can include
  non-covered income and omit or mismeasure covered income; SSA award and
  payment records use administrative covered-earnings histories.
- `opening_backfill_imputation`: the full own-retirement construction consumes
  the model's report-only imputed opening stock in addition to modeled-award
  flow; no SSA source class is a model `opening_backfill`.
- `program_population_scope`: the row note names the model own-retirement
  population and the anchor's retired-worker, OASI, or OASDI scope. OASI adds
  auxiliaries and survivors; OASDI also adds DI.
- `official_estimated_allocation`: Supplement 4.A5 benefit-type amounts are
  estimated allocations, not trust-fund accounting totals.
- `annual_presence_vs_december_current_payment_stock`: the model counts a
  person assigned an annualized amount during the calendar year; 5.A4 is a
  December current-payment point stock.
- `positive_proxy_vs_workers_with_taxable_earnings`: the model count is
  positive PSID labor-income-proxy records; Supplement 4.B11 counts persons
  with OASDI taxable earnings.
- `positive_proxy_vs_trustees_covered_workers`: the model count is positive
  PSID labor-income-proxy records; Trustees IV.B4 counts workers paid during
  the year in employment on which OASDI taxes are due, with historical
  observations subject to revision.
- `labor_income_proxy_vs_taxable_earnings`: the model caps a labor-income
  proxy, not reported OASDI taxable earnings.
- `labor_income_proxy_vs_reported_taxable_earnings`: the model's person-level
  proxy construction differs from employer-reported taxable wages.
- `labor_income_proxy_vs_adjusted_taxable_payroll`: the model's person-level
  proxy construction differs from actuarially adjusted taxable payroll.
- `negative_proxy_no_zero_floor`: `min(proxy, wage_base)` has no zero floor;
  negative proxy earnings reduce model payroll and contributions while those
  records are absent from the model's positive-proxy earner count.
- `consolidated_person_cap_vs_reported_wages`: the model caps consolidated
  person earnings once, while reported employer wages can include
  multi-employer excess and later employee refunds.
- `consolidated_person_cap_vs_adjusted_payroll`: Trustees taxable payroll
  adjusts multi-employer excess wages for the lower effective contribution
  rate; the model instead caps consolidated person earnings once.
- `odd_year_earnings_carry`: the engine draws even-year earnings and carries
  the prior even-year value into odd years (2015 repeats 2014, 2017 repeats
  2016, and so on).
- `earnings_year_rate_arithmetic_vs_gross_contributions`: the model multiplies
  earnings-year proxy payroll by the combined rate. Table 4.B11 publishes
  gross OASDI contributions expressly unadjusted for multi-employer refunds
  and tax credits; those cells are not trust-fund cash.
- `earnings_year_rate_arithmetic_vs_trust_fund_cash`: Table 4.A1/4.A3 net
  payroll-tax contributions are trust-fund cash with estimated deposits and
  later adjustments, not model earnings-year rate multiplication.
- `no_model_oasi_di_allocation`: the model computes only combined OASDI
  contributions. It has no OASI/DI allocation or split, and no OASI share may
  be inferred from it.

No v1 pairing maps `revenue.employee_contributions` or
`revenue.employer_contributions` to official source legs. Such pairings
remain excluded unless separately anchored to reviewed Table 3.C3 series and
ratified with their own mismatch law. The required official series
`oasi_net_payroll_tax_contributions` remains in the official-anchor level
panel but is absent from `pairings` and every `comparison_specs` object. It is
level-only and unpaired: the model has no registered OASI/DI allocation, and
this design registers no denominator for an OASI cash intensity.

### 4.2 Closed comparison law

For draw \(d\) and year \(y\), let \(A\) be modeled average monthly benefit
at award, \(Q\) weighted modeled-award count,
\(B=B_{flow}+B_{stock}\) combined annualized benefit,
\(N=N_{flow}+N_{stock}\) combined beneficiary count, \(P\) modeled taxable
payroll, \(W\) modeled positive-proxy earner count, and \(C\) modeled combined
contribution amount.

Before W1, a comparison must be invariant to global model-weight rescaling
\(w_i\rightarrow k w_i\). The following JSON is the complete ordered
`comparison_specs` registry; a report may not invent another comparison:

```json
[
  {
    "comparison_id": "cmp_award_average_at_award",
    "availability": {
      "status": "unavailable",
      "reason": "oact_annual_award_average_not_registered_in_v1"
    },
    "model_numerator_metric_id": "modeled_award_flow.average_monthly_benefit_at_award",
    "model_denominator_metric_id": null,
    "model_formula": "metric(\"modeled_award_flow.average_monthly_benefit_at_award\",d,y)",
    "official_numerator_series_id": null,
    "official_denominator_series_id": null,
    "official_formula": null,
    "operation": "model_value_over_official_value",
    "timing_scope": "complete_calendar_year_retired_worker_awards",
    "accounting_scope": "model_statutory_award_amount_vs_administrative_amount_due_at_award",
    "mismatch_codes": [
      "administrative_award_vs_mechanical_claim_stamp",
      "official_amount_due_at_award_vs_claim_adjusted_eligibility_pia_no_aero",
      "program_population_scope",
      "psid_labor_income_proxy_history_vs_administrative_covered_earnings_history",
      "odd_year_earnings_carry"
    ]
  },
  {
    "comparison_id": "cmp_retired_worker_monthly_benefit_per_beneficiary",
    "availability": {
      "status": "unavailable",
      "reason": "retired_worker_december_total_monthly_benefit_not_registered_in_vintage1"
    },
    "model_numerator_metric_id": "combined_own_retirement.frame_annualized_benefit",
    "model_denominator_metric_id": "combined_own_retirement.weighted_beneficiary_count",
    "model_formula": "metric(\"combined_own_retirement.frame_annualized_benefit\",d,y)/(12*metric(\"combined_own_retirement.weighted_beneficiary_count\",d,y))",
    "official_numerator_series_id": null,
    "official_denominator_series_id": "retired_worker_december_current_payment_stock",
    "official_formula": null,
    "operation": "model_intensity_over_official_intensity",
    "timing_scope": "model_calendar_year_annual_presence_vs_official_december_current_payment",
    "accounting_scope": "model_annualized_statutory_amount_vs_official_monthly_current_payment_amount",
    "mismatch_codes": [
      "annualized_statutory_amount_vs_december_current_payment_amount",
      "psid_labor_income_proxy_history_vs_administrative_covered_earnings_history",
      "opening_backfill_imputation",
      "annual_presence_vs_december_current_payment_stock",
      "program_population_scope",
      "odd_year_earnings_carry"
    ]
  },
  {
    "comparison_id": "cmp_reported_taxable_earnings_per_worker",
    "availability": {"status": "available", "reason": null},
    "model_numerator_metric_id": "revenue.weighted_taxable_payroll",
    "model_denominator_metric_id": "revenue.weighted_covered_earner_count",
    "model_formula": "metric(\"revenue.weighted_taxable_payroll\",d,y)/metric(\"revenue.weighted_covered_earner_count\",d,y)",
    "official_numerator_series_id": "oasdi_reported_taxable_earnings",
    "official_denominator_series_id": "oasdi_workers_with_taxable_earnings",
    "official_formula": "official(\"oasdi_reported_taxable_earnings\",y)/official(\"oasdi_workers_with_taxable_earnings\",y)",
    "operation": "model_intensity_over_official_intensity",
    "timing_scope": "calendar_year_earnings_flow_per_annual_worker",
    "accounting_scope": "model_proxy_taxable_payroll_vs_supplement_reported_taxable_earnings",
    "mismatch_codes": [
      "labor_income_proxy_vs_reported_taxable_earnings",
      "positive_proxy_vs_workers_with_taxable_earnings",
      "negative_proxy_no_zero_floor",
      "consolidated_person_cap_vs_reported_wages",
      "odd_year_earnings_carry"
    ]
  },
  {
    "comparison_id": "cmp_adjusted_taxable_payroll_per_covered_worker",
    "availability": {"status": "available", "reason": null},
    "model_numerator_metric_id": "revenue.weighted_taxable_payroll",
    "model_denominator_metric_id": "revenue.weighted_covered_earner_count",
    "model_formula": "metric(\"revenue.weighted_taxable_payroll\",d,y)/metric(\"revenue.weighted_covered_earner_count\",d,y)",
    "official_numerator_series_id": "oasdi_adjusted_taxable_payroll",
    "official_denominator_series_id": "oasdi_covered_workers",
    "official_formula": "official(\"oasdi_adjusted_taxable_payroll\",y)/official(\"oasdi_covered_workers\",y)",
    "operation": "model_intensity_over_official_intensity",
    "timing_scope": "calendar_year_adjusted_payroll_flow_per_annual_covered_worker",
    "accounting_scope": "model_proxy_taxable_payroll_vs_trustees_adjusted_taxable_payroll",
    "mismatch_codes": [
      "labor_income_proxy_vs_adjusted_taxable_payroll",
      "positive_proxy_vs_trustees_covered_workers",
      "negative_proxy_no_zero_floor",
      "consolidated_person_cap_vs_adjusted_payroll",
      "odd_year_earnings_carry"
    ]
  },
  {
    "comparison_id": "cmp_gross_contributions_per_worker",
    "availability": {"status": "available", "reason": null},
    "model_numerator_metric_id": "revenue.combined_contributions",
    "model_denominator_metric_id": "revenue.weighted_covered_earner_count",
    "model_formula": "metric(\"revenue.combined_contributions\",d,y)/metric(\"revenue.weighted_covered_earner_count\",d,y)",
    "official_numerator_series_id": "oasdi_gross_contributions",
    "official_denominator_series_id": "oasdi_workers_with_taxable_earnings",
    "official_formula": "official(\"oasdi_gross_contributions\",y)/official(\"oasdi_workers_with_taxable_earnings\",y)",
    "operation": "model_intensity_over_official_intensity",
    "timing_scope": "calendar_year_contribution_flow_per_annual_worker",
    "accounting_scope": "model_earnings_year_rate_arithmetic_vs_supplement_gross_contributions",
    "mismatch_codes": [
      "earnings_year_rate_arithmetic_vs_gross_contributions",
      "labor_income_proxy_vs_taxable_earnings",
      "positive_proxy_vs_workers_with_taxable_earnings",
      "negative_proxy_no_zero_floor",
      "consolidated_person_cap_vs_reported_wages",
      "odd_year_earnings_carry"
    ]
  },
  {
    "comparison_id": "cmp_net_payroll_tax_contributions_per_covered_worker",
    "availability": {"status": "available", "reason": null},
    "model_numerator_metric_id": "revenue.combined_contributions",
    "model_denominator_metric_id": "revenue.weighted_covered_earner_count",
    "model_formula": "metric(\"revenue.combined_contributions\",d,y)/metric(\"revenue.weighted_covered_earner_count\",d,y)",
    "official_numerator_series_id": "oasdi_net_payroll_tax_contributions",
    "official_denominator_series_id": "oasdi_covered_workers",
    "official_formula": "official(\"oasdi_net_payroll_tax_contributions\",y)/official(\"oasdi_covered_workers\",y)",
    "operation": "model_intensity_over_official_intensity",
    "timing_scope": "calendar_year_trust_fund_cash_flow_per_annual_covered_worker",
    "accounting_scope": "model_earnings_year_rate_arithmetic_vs_trust_fund_cash",
    "mismatch_codes": [
      "earnings_year_rate_arithmetic_vs_trust_fund_cash",
      "labor_income_proxy_vs_taxable_earnings",
      "positive_proxy_vs_trustees_covered_workers",
      "negative_proxy_no_zero_floor",
      "consolidated_person_cap_vs_reported_wages",
      "odd_year_earnings_carry"
    ]
  },
  {
    "comparison_id": "cmp_retired_worker_beneficiaries_per_worker",
    "availability": {"status": "available", "reason": null},
    "model_numerator_metric_id": "combined_own_retirement.weighted_beneficiary_count",
    "model_denominator_metric_id": "revenue.weighted_covered_earner_count",
    "model_formula": "metric(\"combined_own_retirement.weighted_beneficiary_count\",d,y)/metric(\"revenue.weighted_covered_earner_count\",d,y)",
    "official_numerator_series_id": "retired_worker_december_current_payment_stock",
    "official_denominator_series_id": "oasdi_workers_with_taxable_earnings",
    "official_formula": "official(\"retired_worker_december_current_payment_stock\",y)/official(\"oasdi_workers_with_taxable_earnings\",y)",
    "operation": "model_intensity_over_official_intensity",
    "timing_scope": "model_calendar_year_annual_presence_vs_official_december_stock_per_annual_worker",
    "accounting_scope": "model_own_retirement_presence_vs_administrative_retired_worker_current_payment",
    "mismatch_codes": [
      "annual_presence_vs_december_current_payment_stock",
      "opening_backfill_imputation",
      "program_population_scope",
      "positive_proxy_vs_workers_with_taxable_earnings",
      "odd_year_earnings_carry"
    ]
  },
  {
    "comparison_id": "cmp_retired_worker_awards_per_worker",
    "availability": {"status": "available", "reason": null},
    "model_numerator_metric_id": "modeled_award_flow.weighted_award_count",
    "model_denominator_metric_id": "revenue.weighted_covered_earner_count",
    "model_formula": "metric(\"modeled_award_flow.weighted_award_count\",d,y)/metric(\"revenue.weighted_covered_earner_count\",d,y)",
    "official_numerator_series_id": "retired_worker_awards",
    "official_denominator_series_id": "oasdi_workers_with_taxable_earnings",
    "official_formula": "official(\"retired_worker_awards\",y)/official(\"oasdi_workers_with_taxable_earnings\",y)",
    "operation": "model_intensity_over_official_intensity",
    "timing_scope": "calendar_year_awards_per_annual_worker",
    "accounting_scope": "model_mechanical_claim_stamp_vs_administrative_retired_worker_award",
    "mismatch_codes": [
      "administrative_award_vs_mechanical_claim_stamp",
      "program_population_scope",
      "positive_proxy_vs_workers_with_taxable_earnings",
      "odd_year_earnings_carry"
    ]
  },
  {
    "comparison_id": "cmp_retired_worker_benefits_per_reported_taxable_earnings",
    "availability": {"status": "available", "reason": null},
    "model_numerator_metric_id": "combined_own_retirement.frame_annualized_benefit",
    "model_denominator_metric_id": "revenue.weighted_taxable_payroll",
    "model_formula": "metric(\"combined_own_retirement.frame_annualized_benefit\",d,y)/metric(\"revenue.weighted_taxable_payroll\",d,y)",
    "official_numerator_series_id": "retired_worker_benefits_paid_estimated_allocation",
    "official_denominator_series_id": "oasdi_reported_taxable_earnings",
    "official_formula": "official(\"retired_worker_benefits_paid_estimated_allocation\",y)/official(\"oasdi_reported_taxable_earnings\",y)",
    "operation": "model_intensity_over_official_intensity",
    "timing_scope": "calendar_year_benefit_flow_per_calendar_year_taxable_earnings",
    "accounting_scope": "model_annualized_statutory_amount_vs_estimated_retired_worker_outlay_share",
    "mismatch_codes": [
      "annualized_statutory_amount_vs_actual_outlay",
      "psid_labor_income_proxy_history_vs_administrative_covered_earnings_history",
      "opening_backfill_imputation",
      "program_population_scope",
      "official_estimated_allocation",
      "labor_income_proxy_vs_reported_taxable_earnings",
      "negative_proxy_no_zero_floor",
      "consolidated_person_cap_vs_reported_wages",
      "odd_year_earnings_carry"
    ]
  }
]
```

`metric(id,d,y)` resolves only through `model_metric_specs`;
`official(id,y)` is the anchor observation normalized to its registered base
unit by its exact scale multiplier. For
`model_intensity_over_official_intensity`, the runner evaluates the literal
model and official formulas and divides the former by the latter. For
`model_value_over_official_value`, it divides the named model value by the
official value. An `unavailable` entry is schema-bearing disclosure only:
its null selector or formula is required, and any attempted evaluation
aborts. All available official numerator and denominator IDs above must be
present in the frozen 15-series registry. Evaluation also aborts on a
missing, null, non-numeric, nonfinite, or nonpositive model or official
denominator, or a nonfinite intermediate or result.

The validator asserts exact deep equality with this registry: nine entries
in this order, the exact object key set and availability tagged union, exact
formulas, exact official IDs, operation, scopes, and ordered nonempty
mismatch arrays. Missing, extra, reordered, or altered content aborts.
Unregistered Cartesian combinations of payroll, contribution, worker,
benefit, or award anchors abort. No growth, 2015=100 index, or other
within-series operation is registered in v1. The model-only \(C/P\)
mechanical 12.4-percent identity may appear solely in a diagnostics block
outside `comparison_specs`; it has no official comparator, the no-zero-floor
effect cancels from its numerator and denominator, and it is not independent
validation evidence.

For every nonlinear statistic, components required for a full in-force
own-retirement measure are first combined within the same `(draw, year)`;
the ratio is then computed independently for each draw; only then are its
across-draw mean and sample SD published. Dividing aggregate means is
forbidden.

Official levels appear descriptively only in the mandatory, complete
official-anchor panel, in official units. Model levels appear descriptively
only in the mandatory, complete, separate frame-relative model panel. The
exact panel schemas and coverage law are frozen in §5.2; descriptive-only
status never permits either panel, series, metric, or annual row to be
omitted. Those panels have no shared gap axis or column, percentage-difference
or percent-error column, "national level" axis, or level overlay. Direct
model-total/official-total ratios, absolute model/official gaps, shares of
official totals, coverage/capture rates, anchor-derived scale factors,
rescaled model series, and any `aligned`, `calibrated`, `validated`,
`matched`, `accuracy`, or `close to SSA` claim are forbidden before W1.
Renaming a forbidden total ratio a "context ratio" does not admit it.
Fabricated causal decompositions of a model/anchor difference are forbidden.

### 4.3 Revision-10.1 travel and evidential-status law

Every annual benefit-derived comparison carries the first estimates report's
frozen birth-timing reference. Annual comparisons are baseline-only unless
new annual, per-draw stress outputs are separately registered. The published
cumulative total-ledger stress percentages must never be applied
mechanically to annual values. Births−1 and births+1 remain stress scenarios,
not confidence intervals or uncertainty bounds.

If annual stresses are later registered, the complete numerator,
denominator, inclusion set, and ratio are recomputed for births−1 and births+1
within each draw before reduction. Official anchors remain unchanged; the
sensitivity belongs only to the model. Revenue-only comparisons are
unaffected. Opening-backfill immunity means only that amendment 2 found its
chronology predicate immune; it is not evidence that the entire dollar path
is birth-invariant.

For any full own-retirement measure, modeled-award flow and opening stock are
combined within draw and year before any nonlinear statistic or across-draw
reduction. Every measure that consumes opening stock inherits the exact
status `report-only imputed`, is secondary/non-headline, and may never be
promoted to a headline. Extracting official anchors does not retire the
birth-timing envelope. Only the separately named, ratified birth-timing
resolution may retire it by amendment.

## 5. Executable ceremony contract

The design ratifies through standing adversarial referee rounds. The
extraction then lands in its own referee-gated PR containing retained raw
captures, a literal source manifest, the builder, the versioned vintage-1
artifact, and its reproduction test. The report implementation lands in a
separate referee-gated PR with no production execution.

### 5.1 Fixture-only rehearsal

Pre-registration rehearsal is fixture-only. Its entry point is structurally
unable to open either production input — `runs/first_estimates_v1.json` or
`data/external/ssa_level_anchors_supplement2025_trustees2026_vintage1.json`
— and cannot compute or emit any statistic derived from them. Tests use only
committed nonproduction fixtures and assert that production paths and hashes
are rejected.

The reason is the registered-estimates charter's
configuration-before-execution law: both production inputs are committed and
deterministic, so reading them in a "rehearsal" would reveal the
estimate-bearing report before its configuration was registered. Any report
or rehearsal invocation that can deserialize production values or compute a
production report statistic occurs only after fresh registration and counts
as the one registered run. Actual input-byte hashing and validation occur
inside that sealed runner's preparation phase, not in pre-launch rehearsal or
checks.

### 5.2 Frozen report and failure artifacts

The append-only production output is
`runs/anchor_context_report_v1.json`, paired with
`runs/anchor_context_report_v1.json.env.json`, the exact `<primary>.env.json`
path used by the repository's sidecar writer. Both paths must be absent before
the run; the primary report records the sidecar content hash so the pair is
integrity-bound. The report's schema is `anchor_context_report.v1` and
contains identity, registration reference, the registered configuration
echo, runtime provenance, both production-input paths and hashes, results,
the three labels and evidential statuses, integrity metadata, and
`certifies_nothing` statements.

The configuration echo is the exact registered configuration object, created
before execution with exactly these 11 keys and no others:

- `schema_version`: JSON string literal
  `anchor_context_report_configuration.v1`;
- `registration_reference`: nonempty JSON string;
- `design`: object with exactly `path` equal to
  `docs/design/anchor_context_extraction.md`, `ratification_commit` a
  40-lowercase-hex JSON string, and `revision` the JSON integer `4`;
- `implementation_commit`: 40-lowercase-hex JSON string;
- `invocation`: ordered nonempty JSON string array containing every actual
  argument of the isolated invocation, including the actual fresh empty
  pycache-sentinel and registration paths, with no shell interpolation;
- `first_estimates_input`: object with exactly `path` equal to
  `runs/first_estimates_v1.json` and `sha256` equal to
  `719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977`;
- `anchor_input`: object with exactly `path` equal to
  `data/external/ssa_level_anchors_supplement2025_trustees2026_vintage1.json`,
  `artifact_vintage_id` equal to
  `ssa_level_anchors.supplement2025_trustees2026.vintage1`, and `sha256` a
  64-lowercase-hex JSON string;
- `required_series_ids`: an exact copy of §2.1's ordered 15-string array;
- `model_metric_specs`: an exact deep copy of §4.1's ordered registry;
- `pairings`: an exact deep copy of §4.1's ordered 14-object registry; and
- `comparison_specs`: an exact deep copy of §4.2's ordered nine-object
  registry, not a digest or reconstruction.

All nested objects have only the keys declared here or in their frozen
registry. Let `canonical_json_bytes` be the UTF-8 encoding of
`json.dumps(value, sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False) + "\n"`. Registration validation
requires `canonical_json_bytes(configuration_echo)` to equal the complete
registered configuration bytes and exact-checks every value and type before
launch. Incident validation requires exact object equality with that same
echo. The sealed preparation phase then hashes the actual input bytes and
requires equality with the registered hashes. The primary report records
SHA-256 of the exact sidecar bytes.

The primary report's `results` object has exactly the three keys
`comparison_results`, `official_anchor_level_panel`, and
`model_level_panel`, with no others. Their frozen schemas and coverage are:

- `comparison_results` is an ordered nine-object array in exact
  `comparison_specs` order. An available spec contributes one object with
  exactly `comparison_id`, `availability`, `evaluated`, and `annual_rows`;
  `comparison_id` equals the spec ID, `availability` is the literal
  `available`, `evaluated` is the JSON boolean `true`, and `annual_rows`
  contains exactly eight rows in year order 2015 through 2022. Each row has
  exactly `year`, `model_statistic_mean`, `model_statistic_sample_sd`,
  `official_statistic`, `comparison_mean`, and `comparison_sample_sd`.
  `year` is the JSON integer for that position. Every other field is a finite
  JSON number, excluding booleans; both sample SDs are nonnegative. The model
  statistic fields reduce the spec's literal model formula across the 20
  draws, `official_statistic` evaluates its literal official formula, and the
  comparison fields are the mean and sample SD of the literal operation
  evaluated separately within each draw as required by §4.2.
- An unavailable spec instead contributes exactly one non-evaluated
  disclosure object with exactly `comparison_id`, `availability`,
  `evaluated`, and `reason`. Its ID equals the spec ID, `availability` is the
  literal `unavailable`, `evaluated` is the JSON boolean `false`, and `reason`
  exactly equals the spec's non-null availability reason. It has no
  `annual_rows`, value, mean, SD, or other estimate-bearing field, and
  attempting to evaluate it aborts. Thus the frozen registry produces exactly
  56 evaluated annual rows—seven available specs times eight years—and
  exactly two single-object unavailable disclosures.
- `official_anchor_level_panel` is an ordered 15-object array in exact
  `required_series_ids` order. Each object has exactly `series_id`,
  `stored_unit`, and `annual_rows`; the ID and unit equal that determination's
  registered values. `annual_rows` contains exactly eight objects, ordered
  2015 through 2022, each with exactly `year` and `value`. `year` is the JSON
  integer for that position and `value` is the finite JSON number, excluding
  booleans, equal to the anchor observation normalized to `stored_unit`. All
  120 rows are mandatory, expressly including all eight rows for the
  level-only, unpaired `oasi_net_payroll_tax_contributions`.
- `model_level_panel` is an ordered seven-object array in exact
  `model_metric_specs` order. Each object has exactly `model_metric_id`,
  `unit`, and `annual_rows`; the ID and unit exactly equal its metric spec.
  `annual_rows` contains exactly eight objects, ordered 2015 through 2022,
  each with exactly `year`, `mean`, and `sample_sd`. `year` is the JSON integer
  for that position; `mean` and `sample_sd` are finite JSON numbers, excluding
  booleans, reducing the metric's 20 draw values, and `sample_sd` is
  nonnegative. All 56 model-level rows are mandatory.

Results validation checks each array position directly and detects duplicate
IDs and `(ID, year)` keys before constructing any lookup or index. A missing,
extra, duplicate, or reordered comparison ID, official series ID, model
metric ID, or year; a wrong tagged-union branch, object key set, literal,
type, count, unit, reason, value, reduction, or nonfinite number; or any
omitted or added panel or row aborts publication. Exact configuration-echo
equality does not substitute for this independent, complete results
validation, and an empty or cherry-picked `results` object is invalid.

Any preparation, invariant, compute, or publication failure writes the next
append-only `runs/anchor_context_report_incident_<n>.json`. Here `<n>` is
canonical positive base-10 with no leading zero. The file must be a
repo-relative path directly under `runs/`, must not traverse outside the
repository, and must not already exist. Its object has exactly the following
nine keys and types, with no extras:

- `schema_version`: JSON string literal
  `anchor_context_report_incident.v1`;
- `incident_index`: JSON integer \(n\geq1\), excluding booleans, exactly
  equal to the filename suffix;
- `timestamp_utc`: JSON string that is a real UTC date and time in
  `YYYY-MM-DDTHH:MM:SSZ` form or the same form with one through six
  fractional-second digits before the literal `Z`;
- `phase`: JSON string enum `preparation | invariant | compute |
  publication`;
- `reason`: nonempty machine-readable JSON string;
- `reason_detail`: free-text JSON string;
- `registration_reference`: JSON string exactly equal to
  `configuration_echo.registration_reference`;
- `configuration_echo`: JSON object exactly equal to the pre-execution
  registered object above; and
- `artifact_path`: JSON null except when `phase` is `publication` and a
  partial primary report exists, in which case it is exactly the
  traversal-free repo-relative string `runs/anchor_context_report_v1.json`
  and that file exists.

Existing incident suffixes must be exactly `1..n-1`; the writer uses `n`,
never overwrites, and any later artifact or fresh registration references the
complete ordered history. Publication writes the primary before its sidecar,
so a sidecar-only partial state is forbidden and every permitted partial
state has the primary path named above. A partial primary permanently
occupies the append-only v1 path; recovery requires a newly ratified report
version and output path plus fresh registration, not another v1 attempt.

The schema-validation test enforces the exact key sets and JSON types,
literal schema version, phase enum, valid ISO-8601-Z timestamp,
index/filename equality, canonical `runs/` location and contiguity,
configuration-echo identity, canonical finite JSON, and the
`artifact_path` iff-rule. No incident field outside `configuration_echo` may
contain an estimate-bearing value or statistic derived from either production
input. Ordinary failure metadata — index, timestamp, phase, reason,
`reason_detail`, registration reference, and permitted partial-artifact path
— is expressly allowed. A record is retry-eligible if and only if its phase
is `preparation` or `compute`, its machine `reason` begins `external_`, and
the failure occurred before any estimate-bearing information was yielded;
every other incident requires fresh registration.

### 5.3 Six concrete pre-launch checks and canonical run law

The coordinator records all six checks before launch:

1. Identify the ratified design and referee-gated implementation commits and
   verify that no production-input execution has occurred.
2. Record the fresh registration reference and byte-exact registered
   configuration.
3. Compare the expected production-input path, anchor-vintage-ID, and sha256
   literals in the precomputed echo with the registered configuration without
   opening either production input; the sealed runner performs actual-byte
   hashing after launch.
4. Verify that both `anchor_context_report_v1` output paths are absent and
   identify the next unused contiguous incident index.
5. Verify that the precomputed configuration echo and exact isolated command
   `python -I -B -X
   pycache_prefix=<fresh-empty-sentinel-directory>
   scripts/run_anchor_context_report.py
   --registration <registered-configuration-path>` byte-match registration.
6. Acknowledge `publishes_regardless`, incident publication, and the
   retry/fresh-registration law below before starting the runner.

The canonical execution law is one registered run; `publishes_regardless`;
`no_self_rescue`; and at most one coordinator-adjudicated, report-first retry
solely for a §5.2 retry-eligible incident — exactly phase `preparation` or
`compute`, machine `reason` beginning `external_`, and no estimate-bearing
information yielded. The append-only incident is published before retry
adjudication. A published `anchor_context_report_v1`, any changed
configuration byte, or a second failure of any kind requires fresh
registration; there is no same-ceremony v2 path. This paragraph is the sole
normative execution law document-wide; any other clause or eventual
registration that appears to describe execution defers to it.

The no-retry production sequence is therefore: fresh registration with the
six checks and sealed invocation → one registered run → append-only report
pair or incident record → publication regardless → publication PR. The only
retry branch is: retry-eligible incident → publish that incident → coordinator
adjudication → one unchanged-configuration retry → report pair or second
incident → publication regardless. Forecast-ledger entry 10 resolves at the
context report publication PR's merge, not at extraction alone.

## 6. What is unchanged

The first estimates artifact and its labels; ratified design revision 10.1
and every frozen key; the §10 gap block; the deferred amendment-1 field; the
W1 bridge's position in successor order; and the registered-estimates
execution law. The anchor artifact and report create no alignment,
nationalization, administrative-payment, gate, threshold, floor, verdict, or
forward-production claim.
