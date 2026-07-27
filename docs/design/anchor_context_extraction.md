# The anchor context extraction: pinned official SSA series and the context report

- **Status:** DRAFT revision 2 for referee rounds. Nothing here authorizes an
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
  when the artifact's shape or validation contract changes; it is not a
  data-vintage number.
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

Only after those conditions and a registered publication may the context
report compute \(A/A^{SSA}\). The OACT successor must also ratify a new report
schema/version and its explicit
`modeled_award_flow.average_monthly_benefit_at_award`↔OACT pairing with an
ordered, nonempty `mismatch_codes` array; the OACT artifact alone does not
amend v1's frozen 15-pair crosswalk. Landing-page or request-and-response
bytes without the method, parameters, aggregation identity, and annual-cell
verification do not meet the criterion.

## 4. The context report

### 4.1 Pairing objects, crosswalk, and mismatch inventory

Mismatch metadata belongs to a comparison, not a source series. The
`anchor_context_report.v1` configuration contains an ordered `pairings`
array. Each object has exactly `pairing_id`, `model_metric_id`,
`anchor_series_id`, and an ordered, nonempty `mismatch_codes` array. The v1
validator asserts exact equality, including array order, with all 15 rows
below; no schema-valid v1 report may omit, add, or reassign a pairing or
mismatch code.

| `pairing_id` | `model_metric_id` | `anchor_series_id` | ordered `mismatch_codes` |
|---|---|---|---|
| `pair_retired_worker_awards` | `modeled_award_flow.weighted_award_count` | `retired_worker_awards` | [`administrative_award_vs_mechanical_claim_stamp`, `program_population_scope`] |
| `pair_retired_worker_benefits_paid_estimated_allocation` | `combined_own_retirement.frame_annualized_benefit` | `retired_worker_benefits_paid_estimated_allocation` | [`annualized_statutory_amount_vs_actual_outlay`, `opening_backfill_imputation`, `program_population_scope`, `official_estimated_allocation`, `odd_year_earnings_carry`] |
| `pair_oasi_benefits_paid_estimated_allocation` | `combined_own_retirement.frame_annualized_benefit` | `oasi_benefits_paid_estimated_allocation` | [`annualized_statutory_amount_vs_actual_outlay`, `opening_backfill_imputation`, `program_population_scope`, `official_estimated_allocation`, `odd_year_earnings_carry`] |
| `pair_oasi_trust_fund_benefit_payments` | `combined_own_retirement.frame_annualized_benefit` | `oasi_trust_fund_benefit_payments` | [`annualized_statutory_amount_vs_actual_outlay`, `opening_backfill_imputation`, `program_population_scope`, `odd_year_earnings_carry`] |
| `pair_oasdi_trust_fund_benefit_payments` | `combined_own_retirement.frame_annualized_benefit` | `oasdi_trust_fund_benefit_payments` | [`annualized_statutory_amount_vs_actual_outlay`, `opening_backfill_imputation`, `program_population_scope`, `odd_year_earnings_carry`] |
| `pair_retired_worker_december_current_payment_stock` | `combined_own_retirement.weighted_beneficiary_count` | `retired_worker_december_current_payment_stock` | [`annual_presence_vs_december_current_payment_stock`, `opening_backfill_imputation`, `program_population_scope`] |
| `pair_oasi_december_current_payment_stock` | `combined_own_retirement.weighted_beneficiary_count` | `oasi_december_current_payment_stock` | [`annual_presence_vs_december_current_payment_stock`, `opening_backfill_imputation`, `program_population_scope`] |
| `pair_oasdi_december_current_payment_stock` | `combined_own_retirement.weighted_beneficiary_count` | `oasdi_december_current_payment_stock` | [`annual_presence_vs_december_current_payment_stock`, `opening_backfill_imputation`, `program_population_scope`] |
| `pair_oasdi_workers_with_taxable_earnings` | `revenue.weighted_covered_earner_count` | `oasdi_workers_with_taxable_earnings` | [`positive_proxy_vs_covered_worker`, `negative_proxy_no_zero_floor`, `odd_year_earnings_carry`] |
| `pair_oasdi_reported_taxable_earnings` | `revenue.weighted_taxable_payroll` | `oasdi_reported_taxable_earnings` | [`labor_income_proxy_vs_reported_taxable_earnings`, `negative_proxy_no_zero_floor`, `consolidated_person_cap_vs_reported_wages`, `odd_year_earnings_carry`] |
| `pair_oasdi_gross_contributions` | `revenue.combined_contributions` | `oasdi_gross_contributions` | [`earnings_year_rate_arithmetic_vs_gross_contributions`, `labor_income_proxy_vs_taxable_earnings`, `negative_proxy_no_zero_floor`, `consolidated_person_cap_vs_reported_wages`, `odd_year_earnings_carry`] |
| `pair_oasdi_adjusted_taxable_payroll` | `revenue.weighted_taxable_payroll` | `oasdi_adjusted_taxable_payroll` | [`labor_income_proxy_vs_adjusted_taxable_payroll`, `negative_proxy_no_zero_floor`, `consolidated_person_cap_vs_adjusted_payroll`, `odd_year_earnings_carry`] |
| `pair_oasdi_covered_workers` | `revenue.weighted_covered_earner_count` | `oasdi_covered_workers` | [`positive_proxy_vs_covered_worker`, `negative_proxy_no_zero_floor`, `odd_year_earnings_carry`] |
| `pair_oasi_net_payroll_tax_contributions` | `revenue.combined_contributions` | `oasi_net_payroll_tax_contributions` | [`earnings_year_rate_arithmetic_vs_trust_fund_cash`, `no_model_oasi_di_allocation`, `labor_income_proxy_vs_taxable_earnings`, `negative_proxy_no_zero_floor`, `odd_year_earnings_carry`] |
| `pair_oasdi_net_payroll_tax_contributions` | `revenue.combined_contributions` | `oasdi_net_payroll_tax_contributions` | [`earnings_year_rate_arithmetic_vs_trust_fund_cash`, `labor_income_proxy_vs_taxable_earnings`, `negative_proxy_no_zero_floor`, `odd_year_earnings_carry`] |

The frozen mismatch meanings are:

- `administrative_award_vs_mechanical_claim_stamp`: SSA records an
  administratively effectuated, payable-not-guaranteed award; the model stamps
  a mechanical claim-age crossing.
- `annualized_statutory_amount_vs_actual_outlay`: the model records and
  annualizes 12 times the COLA-stepped eligibility PIA for each included
  claimant-year, with no partial first/last years or post-claim recomputation;
  the anchor records actual outlays to an administrative in-force population.
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
- `positive_proxy_vs_covered_worker`: the model count is positive PSID
  labor-income-proxy records, not administratively verified covered workers.
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
ratified with their own mismatch law.

### 4.2 Closed comparison law

For draw \(d\) and year \(y\), let \(A\) be modeled average monthly benefit
at award, \(Q\) weighted modeled-award count,
\(B=B_{flow}+B_{stock}\) combined annualized benefit,
\(N=N_{flow}+N_{stock}\) combined beneficiary count, \(P\) modeled taxable
payroll, \(W\) modeled positive-proxy earner count, and \(C\) modeled combined
contribution amount.

Before W1, a comparison must be invariant to global model-weight rescaling
\(w_i\rightarrow k w_i\). The following is the **closed list** of admissible
intensities; a report may not invent another:

1. \(A/A^{SSA}\), but only after §3's OACT successor resolves. It is
   unavailable in vintage 1.
2. \(B/(12N)\), against the same-table 5.A4 retired-worker
   monthly-benefit/count intensity. This is secondary because it consumes
   opening stock. The frozen 15-series vintage contains the 5.A4 count cells
   but not the total-monthly-benefit numerator cells, so the official
   comparison is unavailable in vintage 1; no unregistered cell may be read
   silently.
3. \(P/W\), against a separately named official taxable-earnings or adjusted
   payroll intensity using only registered anchors.
4. \(C/W\), against a separately named official gross-contribution or
   trust-fund-cash intensity; those official concepts may not be conflated.
5. \(N/W\) and \(Q/W\), with every component and timing scope named.
6. \(B/P\), against retired-worker benefits paid divided by the separately
   named official taxable-earnings concept.
7. Within-series growth or 2015=100 indexes.
8. \(C/P\), only as the model's mechanical combined-rate diagnostic, never
   as independent validation evidence.

For every nonlinear statistic, components required for a full in-force
own-retirement measure are first combined within the same `(draw, year)`;
the ratio is then computed independently for each draw; only then are its
across-draw mean and sample SD published. Dividing aggregate means is
forbidden.

Official levels may appear descriptively only in an official-anchor panel,
in official units. Model levels may appear descriptively only in a separate
frame-relative model panel. Those panels have no shared gap axis or column,
percentage-difference or percent-error column, "national level" axis, or
level overlay. Direct model-total/official-total ratios, absolute
model/official gaps, shares of official totals, coverage/capture rates,
anchor-derived scale factors, rescaled model series, and any `aligned`,
`calibrated`, `validated`, `matched`, `accuracy`, or `close to SSA` claim are
forbidden before W1. Renaming a forbidden total ratio a "context ratio" does
not admit it. Fabricated causal decompositions of a model/anchor difference
are forbidden.

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
`runs/anchor_context_report_v1.env.json`. Both paths must be absent before the
run; the primary report records the sidecar content hash so the pair is
integrity-bound. The report's schema is `anchor_context_report.v1` and
contains identity, registration reference, the registered configuration
echo, runtime provenance, both production-input paths and hashes, results,
the three labels and evidential statuses, integrity metadata, and
`certifies_nothing` statements.

The configuration echo is constructed before execution and pins the fresh
registration reference; ratified design and implementation commits; exact
isolated invocation; first-estimates artifact path and sha256; anchor path,
artifact-vintage ID, and sha256; the exact ordered 15-series-ID array; and a
digest of the exact ordered pairing crosswalk.

Any preparation, invariant, compute, or publication failure writes the next
append-only `runs/anchor_context_report_incident_<n>.json` with schema
`anchor_context_report_incident.v1`. It has exactly the nine keys
`schema_version`, `incident_index`, `timestamp_utc`, `phase`, `reason`,
`reason_detail`, `registration_reference`, `configuration_echo`, and
`artifact_path`. The phase enum is `preparation | invariant | compute |
publication`; `artifact_path` is non-null if and only if a publication-phase
partial artifact exists. The echo is copied from pre-execution registered
bytes, and no field outside it contains an output-derived value. Incident
indices are contiguous, never overwrite, and are cross-referenced by any
later artifact or fresh registration. A record is retry-eligible if and only
if its phase is `preparation` or `compute`, its machine `reason` begins
`external_`, and the failure occurred before any estimate-bearing information
was yielded; every other incident requires fresh registration.

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
solely for an external pre-output failure that yielded no estimate-bearing
information. The append-only incident is published before retry
adjudication. A published `anchor_context_report_v1`, any changed
configuration byte, or a second failure of any kind requires fresh
registration; there is no same-ceremony v2 path. This paragraph is the sole
normative execution law document-wide; any other clause or eventual
registration that appears to describe execution defers to it.

The production sequence is therefore: fresh registration with the six checks
and sealed invocation → one registered run → append-only report pair or
incident record → publication regardless → publication PR. Forecast-ledger
entry 10 resolves at the context report publication PR's merge, not at
extraction alone.

## 6. What is unchanged

The first estimates artifact and its labels; ratified design revision 10.1
and every frozen key; the §10 gap block; the deferred amendment-1 field; the
W1 bridge's position in successor order; and the registered-estimates
execution law. The anchor artifact and report create no alignment,
nationalization, administrative-payment, gate, threshold, floor, verdict, or
forward-production claim.
