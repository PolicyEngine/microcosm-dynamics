# The covered-earnings correction: a common component ledger for benefits and revenue

- **Status:** DRAFT revision 2 for adversarial ratification. This document
  authorizes no extraction, implementation, registration, fitting, evaluation,
  report run, or label change.
- **Amendment pointer:** The revision-2 base was ratified at
  `59fd058b943c2b9960af9cb98ecdec97709cc2dd` after eleven adversarial
  referee rounds. Its original text remains below as the historical ratified
  law. Prospective amendment 1 is appended at §15; it is inoperative unless
  and until ratified under §15.8.
- **Resolves:** the design step for forecast-ledger entry 11 and
  populace-dynamics#332. Entry 11 itself remains open until the publication
  criterion in §9.3 is met.
- **Model contract:** `covered_earnings.v1`.
- **Evidence boundary:** the conditional-GO covered-earnings scoping survey;
  the entry-8 first-estimates artifact and design; the entry-10 anchor artifact,
  report, and design; and the already committed SSA Supplement snapshot cited
  in §6. No value in this document is a fitted coefficient.

## 1. Charter, acceptance target, and nonclaims

The correction is a pure, versioned modeling unit downstream of the frozen
labor-income projection and upstream of both career assembly and the revenue
ledger. It converts each admissible person-year source component into an
auditable annual component ledger. Benefits and revenue consume different
statutory views of the same underlying corrected components; neither consumer
may reconstruct, resample, or independently correct the proxy.

The acceptance target is complete calendar-year support from 1968 through
2022 for every person-year consumed by either downstream ledger. Full support
is a gate to be demonstrated, not a feasibility fact declared by this design.
A 2015–2022 revenue-only correction is the separately named degradation in
§11.2. It is not the plan and cannot retire the benefit-history proxy label.

Production model shape is scoping Option A: annual component/status
classification as `covered_wage`, `covered_self_employment`, `noncovered`, or
`unresolved`. Option B is the component-aware measurement layer inside that
model. Option C is only the registered sensitivity benchmark in §7.4 and is
never a production candidate.

A certified output carries exactly this ordered label array:

```json
[
  "frame-relative",
  "modeled-covered-earnings",
  "aggregate-concept-calibrated-not-population-aligned"
]
```

Spelling, punctuation, order, and token count are frozen. `pre-alignment` is
forbidden on a corrected output because registered aggregate-concept evidence
informed fitting or selection. The labels assert neither national
representativeness, observed statutory coverage, DER equivalence, individual
administrative truth, exact employer payroll, nor causal attribution of the
model/official gap.

This design does not:

- observe Section 218 groups, public-retirement-system participation,
  CSRS/FERS/CSRS Offset, Railroad-covered service, clergy exemptions, or the
  student/employer nexus where the source data do not;
- retrain or change the frozen earnings projection;
- nationalize the closed PSID frame, alter its roster or weights, or fit an
  official national payroll or worker level;
- model employer-level excess withholding, refunds, deposits, or trust-fund
  cash timing; or
- make administrative-validation or person-level accuracy claims.

The entry-8 and entry-10 artifacts, sidecars, vintage-1 official artifact,
`model_metric_specs`, `pairings`, and `comparison_specs` remain byte-for-byte
immutable. This work creates new authorities; it inherits none from the
vintage-1 artifact's `official_context_only` role.

## 2. Why the published ratios are not a correction factor

For a payroll comparison \(j\), the published intensity ratio obeys

\[
R_j =
\frac{P_{\mathrm{proxy}}/W_{\mathrm{positive\ proxy}}}
     {P_{\mathrm{official},j}/W_{\mathrm{official},j}}
=
\frac{P_{\mathrm{proxy}}}{P_{\mathrm{official},j}}
\frac{W_{\mathrm{official},j}}{W_{\mathrm{positive\ proxy}}}.
\]

The reported-earnings, adjusted-payroll, gross-contribution, and
net-contribution ratios are respectively 1.2225, 1.2265, 1.2225, and 1.2337
in 2015 and 1.2413, 1.2482, 1.2413, and 1.2775 in 2022. “1.22–1.28” is
therefore cross-series endpoint shorthand, not the full annual band; maxima
reach 1.3450–1.3725. At the same time, model positive-proxy workers fall from
about 139.1 million to 116.3 million while the applicable official worker
count rises from about 168.2 million to 181.1 million. The identity above
therefore implies model aggregate reported payroll of approximately 1.01 of
official in 2015 and 0.80 in 2022.

The correction can change, within the fixed frame:

- component attribution and modeled coverage incidence;
- recovered self-employment amounts and zero/positive mass;
- removal of modeled noncovered amounts and treatment of negative inputs;
- uncapped wage and self-employment components, consolidated cap exposure,
  person-level taxable payroll, and benefit careers; and
- downstream AIME, PIA, and frame-relative contribution quantities.

It cannot change the roster, weights, national population level, employer
excess/refund accounting, trust-fund timing, the frozen odd-year earnings
carry, claiming, or program-population scope. Noncovered removal can lower an
amount; self-employment recovery and the nonnegative floor can raise it;
incidence and composition can move either way. No candidate, loss, gate, or
interpretation may impose an unconditional aggregate downward sign or require
every official comparison to move toward 1.0.

## 3. Frozen estimands and the common annual ledger

### 3.1 Atomic inputs, statuses, and output fields

The unit of adjudication is
`(stable_person_id, calendar_year, role, source_job_id, source_component_id,
derived_component_id)`. The complete key is stable across input row order.
For a nonderived record, `derived_component_id` equals
`source_component_id`; the two children of a mixed component therefore have
different keys. `source_job_id` may be a registered synthetic identifier for
an aggregate questionnaire component, but never a row number.

Every atomic record carries the following fields or the run aborts:

| Field | Frozen meaning |
|---|---|
| `proxy_labor_income_raw` | Original signed proxy amount, unchanged and recoverable. |
| `adjudicated_source_amount` | Signed annualized amount after the §4 crosswalk, before the Option-B measurement transform. |
| `measurement_adjusted_gain_amount` | Finite, nonnegative Option-B gain or wage amount. It is zero for an admissible SE loss. |
| `measurement_adjusted_se_loss_magnitude` | Finite, nonnegative magnitude of an admissible SE loss; zero for wages, gains, and a negative non-SE anomaly. |
| `measurement_adjusted_net_amount` | Exactly `measurement_adjusted_gain_amount - measurement_adjusted_se_loss_magnitude`; it may be signed only for an admissible SE concept. |
| `measurement_delta` | Exactly `measurement_adjusted_net_amount - adjudicated_source_amount`; it may be signed. |
| `derived_component_id` | Stable identity of the homogeneous wage/SE child; equal to `source_component_id` when no split occurred. |
| `coverage_state_group_id` | Stable §3.1 dependence-group identity shared exactly by records whose annual coverage status must co-move. |
| `status_probabilities` | Ordered four-value vector for `covered_wage`, `covered_self_employment`, `noncovered`, `unresolved`; each value is a canonical exact dyadic and the vector sums to one exactly. |
| `status` | Deterministic class when one probability is exactly one; otherwise `modeled_distribution`. Draw rows carry one of the four realized classes. |
| `classification_reason_codes` | Ordered, nonempty registered reason-code array. |
| `source_provenance` | Source wave, role, job/component, `se_aggregation_group_id`, verified reference year, exact `year_source_class`, raw field IDs, unit, missing-code disposition, admissible-information date, and—on a benefit gap view—operative claim year, career variant, and adjacent base-row hashes. |
| `correction_version` | Immutable `substantive_model_sha256`; evaluation-only provenance is excluded under §§5.4 and 6.2. |
| `uncertainty_provenance` | `expected_value` or the exact §5.4 correction-draw namespace and index. |
| `status_allocated_gain_amounts` | Object with exactly the four status keys, each holding a nonnegative rational-microdollar amount; semantic traversal uses the registered status order. |
| `status_allocated_se_loss_magnitudes` | Object with exactly the same four keys and nonnegative rational-microdollar magnitudes; `covered_wage` is literal zero. |

Literal reported money is normalized once to canonical signed integer
microdollars. Registered annualization and Option-B perform no hidden money
rounding: every rational exposure transform and every finite binary64 mapping
result is retained exactly, with the latter interpreted as its dyadic
rational number of microdollars. Every probability is stored as a reduced dyadic object with
exactly `numerator` and `exponent`, denoting
`numerator * 2**exponent`; zero has exponent zero and every nonzero numerator
is odd. Both are arbitrary-precision JSON integers excluding booleans.
Candidate binary64 probability output is interpreted as its exact
dyadic value, never its displayed decimal. Complement categories are formed
by exact rational subtraction, so the four values sum to literal one.

Every status-allocated and person-year output amount uses the uniform reduced
rational-microdollar object with exactly `numerator` and positive
`denominator`; an unadjusted integer source has denominator one, while an
Option-B or realized-draw amount may remain rational. Multiplication by an
exact probability is rational and incurs no rounding. Numerator and
denominator are coprime arbitrary-precision JSON integers excluding booleans.
For each atomic expected-value record, the four
status-allocated nonnegative gain amounts equal
`measurement_adjusted_gain_amount` with literal zero rational residual, and
the four nonnegative loss magnitudes separately equal
`measurement_adjusted_se_loss_magnitude` with literal zero residual. A loss magnitude
may be allocated only to `covered_self_employment`, `noncovered`, or
`unresolved`; it is always zero for `covered_wage`. A negative non-SE source
amount is preserved as a source anomaly, maps to zero gain and zero SE loss,
and appears in the measurement delta. Across all atomic records for one
person-year,

\[
\sum(T^+-T^-) = \sum X + \sum((T^+-T^-)-X),
\]

where \(X\) is `adjudicated_source_amount`, \(T^+\) is adjusted gain, and
\(T^-\) is the admissible SE loss magnitude. Both sides, both gross channels,
and every component delta publish. An implementation may not force corrected
amounts to reconcile to the raw proxy by hiding the loss channel or
measurement delta.

`ledger_row_schema_specs.v1` freezes the bytes behind every canonical ledger
row. It is one object with exactly `schema_version`, `row_kind`,
`atomic_key_fields`, `field_specs`, `canonical_field_order`, `encodings`,
`row_invariants`, and `failure_disposition`. The schema and row-kind literals
are `ledger_row_schema_specs.v1` and `atomic_component`; key fields are the
exact six-field tuple at the start of §3.1. `field_specs` is an ordered array
containing every key field once followed by every field in the atomic table
above that is not already a key. Each object has exactly `field_id`,
`json_type`, `logical_type`, `unit`, `nullable`, and `definition`; all fields
are nonnullable, and the registered type, unit, and definition must
exact-match §3.1 and the §4.2 provenance schema. `canonical_field_order`
exactly matches that expansion. `encodings` is an exact deep copy of the
integer-microdollar, rational-microdollar, dyadic-probability, canonical JSON,
and keyed-draw laws in §§3.1, 5.4, and 10.1. `row_invariants` is the ordered
executable expansion of the reconciliation, status-domain, group, and
provenance laws in §§3.1–3.2. The failure disposition is `abort`.

This registry is frozen before registration, embedded byte-for-byte in the
configuration and selected model, and readable by every downstream
rematerializer. No implementation-inferred field, insertion order, nullable
exception, or unregistered extension is permitted. Its canonical SHA-256 is
the sole `row_schema_sha256` in §10.2.

Calibration/evaluation reductions accumulate these rationals exactly in
stable-key order and perform one registered round-to-nearest-even binary64
conversion only at a model-target or reported-statistic boundary. Benefits
never apply statutory nonlinearities to an expected rational career; they use
the realized correction draws required by §5.4.

The frozen person-year output registry is:

| Estimand ID | Definition |
|---|---|
| `covered_employee_wages_uncapped` | Sum of nonnegative amounts classified as OASDI-covered employee wages before the person-level maximum. |
| `covered_se_gains_pre_loss` | Nonnegative sum of amounts classified as covered self-employment gains before statutory SE aggregation. |
| `covered_se_loss_magnitude` | Nonnegative magnitude of losses classified as covered self-employment and admissible to the same statutory aggregation unit. |
| `covered_se_net_earnings_pre_seca` | Signed intermediate `covered_se_gains_pre_loss - covered_se_loss_magnitude`; it never offsets wages and is not a final taxable component. |
| `covered_seca_base_uncapped` | Nonnegative self-employment base after the registered year-specific eligible-concept, net-earnings-factor, and threshold law, before wage-first cap coordination. |
| `noncovered_earnings` | Sum assigned noncovered under direct evidence or the registered expected/draw classifier. |
| `noncovered_se_loss_magnitude` | Separately reported nonnegative SE-loss magnitude assigned noncovered; it never enters an OASDI base. |
| `unresolved_earnings` | Sum left outside a defensible covered/noncovered allocation. It is never silently counted as covered. |
| `unresolved_se_loss_magnitude` | Separately reported nonnegative SE-loss magnitude left unresolved. |
| `oasdi_taxable_wages_person` | Covered employee wages after the person-year maximum. |
| `oasdi_taxable_se_person` | Eligible SECA base remaining after wages consume the person-year maximum. |
| `oasdi_person_taxable_payroll` | Sum of the two preceding fields; the revenue tax-base view. |
| `benefit_only_deemed_credits` | Literal zero in v1. No military or other deemed credit is invented without a separate source and legal registry. |
| `benefit_creditable_earnings` | V1 creditable wage plus SE amount under the same combined maximum. It equals `oasdi_person_taxable_payroll` because deemed credits are zero, but remains a separate typed view. |
| `covered_wage_worker_probability_analytic` | Analytic probability of positive covered employee wages in the registered annual worker universe. |
| `b2_wage_worker_membership_probability_analytic` | Analytic probability of meeting the exact 4.B2 `c11` worker-membership rule verified and registered under §6.1. It equals the preceding field only if source bytes prove that equivalence. |
| `positive_covered_se_worker_probability_analytic` | Analytic probability of positive covered SECA base in the registered annual worker universe. |
| `b2_se_worker_membership_probability_analytic` | Analytic probability of meeting the exact 4.B2 `c12` worker-membership rule verified and registered under §6.1. It equals the preceding field only if source bytes prove that equivalence. |
| `b11_wage_only_worker_probability_analytic` | Analytic probability of membership in the wage-only cell implied by the registered 4.B11 total/wage/SE worker-count definitions. |
| `b11_se_only_worker_probability_analytic` | Analytic probability of membership in the SE-only 4.B11 implied cell. |
| `b11_dual_type_worker_probability_analytic` | Analytic probability of membership in both 4.B11 wage and SE component counts. |
| `b11_any_worker_probability_analytic` | Sum of the preceding three mutually exclusive probabilities; the analytic analogue of the registered unduplicated 4.B11 total-worker cell. |
| `registered_covered_share_denominator_indicator` | Deterministic zero/one membership in the exact model analogue of V-B7's verified covered-share denominator; this is a population-universe field, not an earnings or coverage outcome. |
| `modeled_covered_worker_probability_analytic` | Analytic probability, under the registered joint wage/SE status mapping, that person taxable payroll is positive. This is the covered-share calibration selector and is not `proxy > 0`. |
| `modeled_covered_worker_draw_indicator` | Zero/one indicator within one correction draw that taxable payroll is positive. |
| `modeled_covered_worker_draw_grid_fraction_20` | Arithmetic mean of the 20 draw indicators. It is a finite-grid approximation, never renamed an exact probability. |

Worker probabilities use the exact finite joint state law, never a sum of
marginals. For each person-year, the candidate enumerates every registered
joint outcome of remuneration allocation, component coverage, admissible SE
gain/loss netting, threshold application, and—if the verified membership
definition requires it—wage-first cap coordination. Outcome weights are
products only across factors whose `draw_spec` explicitly proves
independent. V1 has no stochastic mixed-allocation or measurement-residual
variate; its sole nondegenerate factor is registered coverage status.
Within an outcome, the deterministic §3.2 transform decides each indicator.
The analytic probability is the exact rational sum of weights for outcomes
where that indicator is one.

`coverage_state_dependence_specs.v1` closes the within-person-year joint law.
The §4.2 crosswalk assigns every derived atomic record exactly one
`coverage_state_group_id`. A group contains only one person-year and one
homogeneous remuneration type. Components representing the same statutory
service/job coverage fact share a group; distinct jobs, synthetic wage/SE
components, and facts that can differ legally have distinct groups. All
members of a nondegenerate group must have byte-identical probability
vectors, direct-rule identity, and coverage reason codes. A disagreement,
missing group, or group spanning a person, year, or remuneration type aborts.

Each nondegenerate group contributes one categorical factor and one keyed
uniform to both analytic enumeration and realized correction draws. Distinct
groups are conditionally independent in v1; direct one-hot groups are
deterministic. This is a declared modeling assumption, not an empirical
claim. Group IDs and memberships are frozen before fitting, and neither a
candidate nor row order may split, merge, or reorder them. The registry has
exactly `schema_version`, `group_construction_rule`,
`within_group_law`, `between_group_law`, `between_year_law`, and
`failure_disposition`, with literals equal to this paragraph and
`failure_disposition: abort`.

An implementation may use a stable-key dynamic program rather than literal
\(2^K\) enumeration, but a fixture test must byte-match exhaustive
enumeration for every registered dependence pattern. A distributional
measurement residual is admissible here only if its candidate spec supplies
an exact finite mass function or an analytic CDF plus truncated first-moment
transform over every threshold used by the state law; otherwise that
candidate is ineligible. The simple
\(1-\prod_k(1-p_k)\) shortcut is allowed only when the registered
factorization proof applies. Summing wage and SE worker probabilities is
always forbidden because a person may have both.

### 3.2 Statutory ordering

For person \(p\), year \(y\), let \(W_{py}\) be uncapped covered employee
wages; let \(G_{py}\) be self-employment gains and losses aggregated only
within the registered SE law; let \(L_y(G)\) be the year-specific
eligible-concept, factor, and threshold transform; and let \(M_y\) be the
registered OASDI contribution and benefit base. Then:

\[
\begin{aligned}
S_{py} &= \max(0,L_y(G_{py})),\\
W^{tax}_{py} &= \min(W_{py}, M_y),\\
S^{tax}_{py} &= \min(S_{py}, \max(0,M_y-W^{tax}_{py})),\\
P^{tax}_{py} &= W^{tax}_{py}+S^{tax}_{py}.
\end{aligned}
\]

These equations run inside each deterministic joint status/measurement
outcome. An expected-value capped or creditable field is the exact
probability-weighted rational sum of those outcome results, never the result
of applying `min`/`max` to expected components. Career nonlinearities remain
draw-based under §5.4 because v1 does not enumerate the full cross-year state
space.

All operands are finite. Component nonnegativity precedes cap coordination.
Admissible self-employment losses may offset admissible self-employment gains
only as the registered historical law directs; no negative
self-employment amount may offset employee wages. The SE threshold is applied
to the eligible aggregated SE concept before the combined cap. Wages consume
the maximum first and SE consumes only the remainder. There is one
consolidated person-year maximum for both downstream views.

Incorporated-owner salary that the crosswalk identifies as employee
remuneration enters wages. Corporate distributions do not enter SECA
earnings. An unverified incorporation or remuneration distinction becomes an
expected allocation or `unresolved`; it never defaults to SE income.

### 3.3 Shared-consumer law

The canonical base component ledger is materialized once per substantive
model and draw. Career assembly and revenue receive its canonical hash and
typed accessor. They may apply a downstream benefit/contribution rate, and
the benefit assembler may derive §8.1's claim-context gaps from corrected
pre-statutory adjacent channels, but neither may alter classification,
measurement, annualization, nonnegativity, wage/SE ordering, or draws.

Consumer domains are not configured selectors. The sealed coordinator
independently reconstructs the complete frozen Stage A–D benefit domain and
the complete unsplit 2015–2022 revenue slices under
`consumer_domain_derivation_specs.v1`. For every
`(projection_draw, correction_draw, person, year)` in their intersection,
base component bytes are identical. A benefit gap row additionally keys
`operative_claim_year` and `career_variant_id`, binds its adjacent base-row
hashes, and is never reusable across claim contexts. Consumers receive only
the coordinator-evaluated typed root streams whose configured source/domain/
rule/unit/opcode closure exact-matched the independently reconstructed
semantic authority in §8.1, plus those root hashes; a
runner-produced aggregate table has no consumer authority. A career-only
correction, revenue-only correction, omitted opening-backfill/difficult row,
self-shrunk support set, or independently sampled pair fails G01/G08/G22.

## 4. Immutable authorities, PSID crosswalk, and information boundary

### 4.1 Historical legal-rule authority

Before any fitting, a new immutable `historical_coverage_rule_specs.v1`
registry and source manifest must be ratified. Each ordered rule object
contains exactly:

`rule_id`, `authority_status`, `status_family`, `effective_start`, `effective_end`,
`jurisdiction`, `authority_rank`, `source_document_id`, `source_sha256`,
`exact_citation`, `covered_facts`, `excluded_facts`, `required_micro_facts`,
`transform`, `reason_code`, `unresolved_action`, `verification_class`,
`verification_claim_ids`, `affected_inventory_keys`, and
`optional_row_consequences`.

`covered_facts` and `excluded_facts` are not prose, names, or implementation
premises. Each is an ordered array of
`direct_law_fact_binding.v1` objects. A binding has exactly
`fact_binding_id`, `premise_ast`, and `micro_fact_slots`.
`fact_binding_id` is respectively the literal
`<rule_id>:covered:<one-based canonical decimal position>` or
`<rule_id>:excluded:<one-based canonical decimal position>`.
`micro_fact_slots` is a nonempty ordered array, and each slot has exactly
`micro_fact_id`,
`field_purpose`, `source_field_ref`, `typed_value_type`,
`typed_value_unit`, `presence_predicate_ast`, and `missing_reason_code`.
`micro_fact_id` is globally unique and `field_purpose` is one of the exact
35 §4.2 purposes. `source_field_ref` has exactly `source_inventory_key` and
`raw_field_id`. Its inventory key must be in the rule's independently
expanded `affected_inventory_keys` closure and its inventory row must have
the same `field_purpose`. For a `present` inventory row, `raw_field_id` is a
nonnull member of that row's `raw_field_ids`. For a
`structural_missing` row it is null. `typed_value_type` is exactly
`rational | json_integer | boolean | enum`; `typed_value_unit` is the
registered nonempty unit for a numeric fact and null for boolean/enum.
For a present row, both exact-match the referenced inventory row's registered
`typed_parse_specs` output and the rule's bound-premise `micro_fact` leaf. For a
structural-missing row, the parse array is correctly empty; the declared
type/unit instead exact-match that bound `premise_ast` leaf's frozen expected
signature, but no value is constructed and the transform is necessarily
skipped.
Missing, extra, cross-purpose, or runner-selected references abort
registration.

`premise_ast` is the boolean/null-unit subset of `psid_rule_ast.v1`. It may
contain only `micro_fact`, registered typed literal, `equal`, `less`,
`less_equal`, `greater_equal`, `greater`, `and`, and `or` nodes; every
`micro_fact` leaf must foreign-key exactly one member of that binding's
`micro_fact_slots`, and every slot must occur at least once.
It has no direct field node, free text, fact name, callback, path, default,
or reference to another binding. Registration type- and unit-checks the
complete premise and requires a nonnullable boolean result. Thus a purported
covered or excluded fact has no representable premise outside the independent
35-purpose inventory.

`required_micro_facts` is an ordered array of the same exact slot objects,
not an independently authored array of names or runner-supplied booleans.
The coordinator derives it before accepting the rule by concatenating every
`covered_facts[*].micro_fact_slots` array in covered-fact order and then
every `excluded_facts[*].micro_fact_slots` array in excluded-fact order.
The configured array must deep-equal that derivation. Because microfact IDs
are globally unique, no deduplication, alias, or implementation ordering
choice exists. It is empty if and only if both bound-fact arrays are empty;
one nonempty bound-fact array necessarily produces a nonempty required-fact
array. An empty pair declares an unconditional rule over the exact
independently expanded affected domain and admits no hidden factual premise.

V1 deliberately permits one source-field reference per microfact. A
composite condition is represented by multiple uniquely named microfacts and
combined only in its fact binding's typed `premise_ast`; the transform
consumes the resulting fact-binding boolean, never a raw fact value. Neither
stage is resolved by field order, first-nonmissing selection, or an
implementation callback. A verified rule row is split into distinct stable
rule IDs wherever wave, role, job, component, or context attachment would
select a different source inventory key. For each affected §3.1 record,
registration independently requires every bound microfact's source key to
occur in that component's exact
`purpose_source_inventory_keys[field_purpose]` attachment closure, including
any enumerated context-only attachment. The coordinator reads that field
from the same stable person/wave/role/job/component record. A key attached to
another person, wave, role, job, component, or purpose is inapplicable and
cannot satisfy the fact.

`presence_predicate_ast` uses the closed
`direct_law_micro_fact_presence_ast.v1` grammar and is exactly one of
`{"op":"typed_nonmissing","source_field_ref":"self"}` or
`{"op":"literal_false"}`. The first form is required for a `present`
inventory row. `literal_false` is required for a `structural_missing` row.
No literal true, alternative reference, boolean combiner, negation,
callback, code, path, implementation default, or unregistered field lookup
exists.

For each affected person/component/year record, the sealed coordinator—not a
fit, classification, evaluation, or runner process—descriptor-reads the
registered PSID field coordinates and evaluates this AST. A
`typed_nonmissing` atom is true only when its inventory row is `present`,
the exact-width raw token is not one of that row's complete
`missing_raw_tokens`, and the token successfully resolves through the
registered inventory `typed_parse_specs` and, where selected, its complete
value-code entry to a typed value. Extraction,
mapping, or typing failure makes the atom false with the registered missing
reason; it never supplies a default. The coordinator also executes the
verified rule's fact premises against only those trusted typed values and
then executes the closed `transform` against only the resulting trusted
fact-binding booleans.

This produces the read-only
`direct_law_micro_fact_presence_ledger.v1`, whose top-level object has
exactly `schema_version`, `rows`, `row_count`, `row_keyset_sha256`, and
`status`. Rows are independently expanded in
`(rule_id,affected_record_key,micro_fact_id)` order and each has exactly
`rule_id`, `affected_record_key`, `micro_fact_id`, `field_purpose`,
`source_inventory_key`, `raw_token_commitment_sha256`,
`typed_value_commitment_sha256`, `present`, and `missing_reason_code`.
`affected_record_key` is the exact §3.1 six-field canonical array
`[stable_person_id,calendar_year,role,source_job_id,source_component_id,
derived_component_id]`, expanded from the complete component domain before
any fact value is read. `source_inventory_key` exact-matches that fact's
single registered `source_field_ref.source_inventory_key`.
`raw_token_commitment_sha256` has a tagged canonical preimage with exactly
`source_disposition`, `affected_record_key`, `source_inventory_key`,
`raw_field_id`, `raw_token_width`, `raw_token_hex`, and
`absence_proof_sha256`. For `present`, the raw-field ID and positive width
are registered, raw token is the exact fixed-width source bytes encoded in
lowercase hex, and absence proof is null. For `structural_missing`, the
raw-field ID, width, and token are null, while the absence-proof hash
exact-matches the inventory row's nonempty source-backed proof. Thus
structural absence has a constructible commitment without inventing a token.
When present,
`typed_value_commitment_sha256` hashes canonical JSON with exactly
`affected_record_key`, `source_inventory_key`, `raw_field_id`,
`typed_value_type`, `typed_value_unit`, and `canonical_typed_value`. Type and
unit exact-match both the microfact
declaration and the chosen parser output; the canonical value is a reduced
rational numerator/positive-denominator pair, a JSON integer excluding
booleans, a JSON boolean, or the registered enum token according to that
type. The typed commitment is null exactly when `present` is false, and the
missing reason is nonnull exactly then. No commitment preimage can omit or
reinterpret field identity, type, unit, or value. Count and keyset hash bind
the complete applicable
rule×record×fact domain. Overall status passes only when that independently
derived domain, every inventory reference, AST result, commitment, and
coordinator-executed direct classification are exact.
The runner receives neither a fact-presence input nor a fact-value input;
only the coordinator's immutable classified output may cross the IPC
boundary. Any runner boolean/value field, omitted ledger row, or
classification inconsistent with this ledger is schema-invalid and fails
G06/G15/G17 before fitting.

G06's independent post-classification validator descriptor-reopens the
registered source bytes and emits
`coordinator_legal_rule_microfact_action_trace.v1`, with exactly
`schema_version`, `expected_domain_count`, `actual_domain_count`,
`expected_domain_sha256`, `actual_domain_sha256`,
`expected_presence_ledger_sha256`, `actual_presence_ledger_sha256`,
`expected_action_trace_sha256`, `actual_action_trace_sha256`,
`domain_mismatch_count`, `presence_mismatch_count`,
`action_mismatch_count`, and `status`. The three counts are actual
nonnegative JSON integers. Status passes only when the domains and all three
hash pairs match and every mismatch count is zero. The expected side is a
fresh coordinator evaluation from inventory/source bytes. It expands each
rule's covered-then-excluded fact-binding slots first, derives the expected
required-microfact array from that expansion, and only then compares the
configured `required_micro_facts`; the configured array is never an expected-
domain input. The actual side is the immutable ledger and classified
component stream used by fitting.

Both action hashes have the exact
`direct_law_action_trace.v1` preimage, whose top level has exactly
`schema_version`, `rows`, `row_count`, `row_keyset_sha256`, and `status`.
Rows are the complete independently derived applicable
record×verified-rule domain in §3.1 atomic-key order, then ascending
`authority_rank`, then `rule_id`. Each row has exactly
`affected_record_key`, `rule_id`, `authority_rank`,
`required_micro_fact_ids`, `presence_bits`, `missing_micro_fact_ids`,
`fact_binding_ids`, `fact_binding_results`,
`input_coverage_unknown_action`, `rule_missing_fact_action`,
`output_coverage_unknown_action`, `transform_disposition`,
`transform_result`, `transform_result_commitment_sha256`,
`controlling_authority_rank`, `controlling_transform_result`,
`final_classification_disposition`, `classified_status`,
`classification_reason_codes`, `classified_component_sha256`, and `status`.
The record key is the exact six-field array above; fact IDs and booleans
positionally equal the rule's complete required-fact order; missing IDs are
exactly the false positions. `fact_binding_ids` is the complete covered-then-
excluded binding-ID order. Its parallel results array contains the
coordinator-evaluated boolean for a binding exactly when all of that
binding's microfact slots are present and JSON null otherwise. An empty
bound-fact domain has two exact empty arrays.

The first input action is the component's registration-time action and each
later input exact-matches the preceding rule row's output. When no fact is
missing, `rule_missing_fact_action` is null,
`transform_disposition: executed_all_facts_present`, and the transform
consumes exactly the complete nonnull binding-result array; its result and
commitment are nonnull. A result is the exact
`direct_law_transform_result.v1` object with keys `status_family`,
`classified_status`, and `reason_code`: family exact-matches the rule,
status is `covered_wage | covered_self_employment | noncovered |
no_disposition`, and reason is the rule's registered reason. Wage-typed
records forbid `covered_self_employment`, SE-typed records forbid
`covered_wage`, and `no_disposition` is a typed noncontrolling result rather
than a default. The commitment hashes that complete canonical object.
Otherwise the action exact-matches the rule's
`unresolved_action`, the transform disposition is
`skipped_missing_fact`, and its result and commitment are null. The output
fold is the §5.1 literal `unresolved`-dominates law: an executed/all-present
row leaves the input action unchanged, while a skipped row folds its
nonnull registered missing-fact action into that input.

For each record, the controlling transform is mechanically frozen. Discard
only executed `no_disposition` results; among the remaining results, the
smallest numeric `authority_rank` is controlling. Every dispositive result
at that rank must have the same `classified_status` or registration aborts;
their distinct rule IDs, status families, and reason codes remain evidence.
Every lower-authority dispositive result must have that same status or
registration aborts, so it can corroborate but never override. The repeated
`controlling_transform_result` is the exact
`direct_law_controlling_result.v1` object with keys `authority_rank`,
`classified_status`, `controlling_rule_ids`, and `reason_codes`; the two
arrays contain every dispositive result at the controlling rank in rule-ID
order. When all facts are present, zero dispositive results is not a direct
classification and aborts any rule set declared direct. Every action row for
the record repeats the resulting nonnull `controlling_authority_rank`,
complete controlling object, and literal `classified_status`; a missing-fact
record instead makes those three fields null and follows the action fold.
Thus distinct provenance survives while neither row order nor an
implementation default can choose between legal outcomes.

`final_classification_disposition` is the same independently derived
`direct | modeled | unresolved` literal on every row for that record:
`direct` only when every applicable rule fact is present, every applicable
transform executes, and the unique controlling-result law passes; otherwise
it equals the completed action fold. A direct row's `classified_status` is
the controlling result's status and its brokered probability vector is the
corresponding exact one-hot vector. An unresolved row has
`classified_status: null` and exact vector `[0,0,0,1]`. A modeled row also
has `classified_status: null`, but before fitting it carries the literal
`candidate_probability_pending` instead of a nonexistent \(q\) or model
vector. Its coordinator-owned classified component exposes only the frozen
feature inputs and modelable disposition to candidate IPC.
`classified_component_sha256` hashes the record key, remuneration type,
final disposition, direct one-hot/unresolved vector or pending marker, and
ordered reason codes; it never hashes a candidate probability in this
pre-fitting trace. Candidate-specific \(q\) vectors are separately
exact-compared after fitting in each registered candidate prediction/ledger
bundle and by G01/G10/G15/G22. Thus phase 3 can finish before fitting without
letting a runner rewrite the later vector. Counts, key hash, row status, and overall
status fail on any omitted, extra, reordered, wrong-presence, wrong-fold,
executed/skipped, precedence/conflict, typed-result, reason, or
classified-byte mismatch. G17 binds this same complete preimage; it does not
hash an implementation-defined trace.

`verification_class` is one of the two literals below.
`affected_inventory_keys` is the exact ordered array of independently
inventoried wave×role×job×component/context keys to which the rule could
apply. `optional_row_consequences` is empty for
`registration_required`; for `direct_only_optional` it has exactly one row
per affected key in identical order, each with exactly
`optional_consequence_id`, `source_inventory_key`, `consequence`, and
`reason_code`, where consequence is `modelable | unresolved`.
`optional_consequence_id` is the literal
`<rule_id>:<source_inventory_key>` and is globally unique. Missing, extra, or
self-selected keys fail registration.
`verification_claim_ids` is the ordered nonempty foreign-key array into the
claim registry below for a verification-bearing rule and the exact empty
array otherwise. `unresolved_action` is a validated rule's runtime
`modelable | unresolved` treatment when its registered person-level
`required_micro_facts` are absent; it never supplies missing legal authority,
choose between verification classes, or override a per-key optional
consequence.

The rule row is a tagged union on `authority_status`, which is
`verified | authority_absent | authority_conflict`. A `verified` row has all
authority/source/citation/fact/transform fields populated under the exact
schema above; `unresolved_action` is the runtime missing-microfact treatment.
An absent/conflict row is permitted only for `direct_only_optional`: its
source document/digest/citation, covered/excluded/required-fact, and transform
fields are null or exact empty arrays; `unresolved_action` is null; and its
complete affected-key and optional-consequence arrays are nonempty and
exact-match the claim result. A `registration_required` rule must be
`verified`; any absent/conflict result aborts before a production
configuration can be accepted. Thus the singular runtime microfact action
cannot act as a generic missing-authority fallback or conflict with
key-specific consequences.

Authority precedence is:

1. byte-pinned enacted federal statute and regulation effective for the
   earnings year;
2. byte-pinned contemporaneous official administering-agency material from
   SSA, IRS, OPM, or RRB that operationalizes that authority; then
3. no rule.

A lower-ranked source cannot override a higher-ranked source. Secondary
literature is not legal authority. Every verification claim in this registry
has exactly one `verification_class`:

- `registration_required` means missing bytes, source-hash drift, an
  effective-year gap, conflicting same-rank dispositions, a lower-rank
  dispositive contradiction, or an unregistered transform aborts the whole
  registration. The complete Section 218 and
  mandatory state/local coverage law, the complete historical SECA
  eligible-concept/factor/threshold/coordination law, and every source needed
  to construct a fitting or selection target have this class.
- `direct_only_optional` means the registry must enumerate, before
  registration, every affected source-inventory key and its exact
  `modelable | unresolved` consequence. Missing or conflicting authority
  disables direct classification for exactly those rows and applies that
  frozen consequence; it neither aborts unrelated rows nor permits a guessed
  legal status. Clergy, Railroad, student, federal-system, and residual
  exclusion facts are in this class unless a separately identified
  registration-required transform consumes them.

There is no `load_bearing_gap` judgment and no implementation-time choice
between abort and fallback. The registration validator derives the required
claim set from the candidate/target ancestry, exact-compares it with the
registry, and applies the class above. Missing required claims abort;
optional facts can have only their predeclared row consequences.

`verification_claim_specs.v1` is the exact ordered nine-object executable
registry corresponding positionally to V-B1 through V-B9 in §13.2. Each
object has exactly `claim_id`, `verification_class`, `claim_subject`,
`affected_inventory_keys`, `required_authority_roles`,
`governing_rule_ids`, `success_disposition`, and
`missing_authority_disposition`. Claim IDs, classes, and subjects
exact-match that table. Inventory keys are independently expanded from
`psid_questionnaire_slot_specs.v1`, never selected by a rule or crosswalk;
authority roles and governing rules are ordered nonempty arrays wherever the
claim consumes them. `success_disposition` is `verified`.
`missing_authority_disposition` is `abort_registration` exactly for
`registration_required` and `apply_exact_optional_row_consequences` exactly
for `direct_only_optional`.

Registration emits `verification_claim_results.v1` in the same nine-row
order. A row has exactly `claim_id`, `authority_input_ids`,
`affected_inventory_keyset_sha256`, `governing_rule_ids`,
`verification_status`, `optional_consequence_specs_sha256`, and `status`.
`verification_status` is `verified | authority_absent |
authority_conflict`; `status` is `pass | fail`. A required row passes only
when verified and otherwise aborts before configuration acceptance. An
optional absent/conflicting row passes only after the complete independently
derived affected-key array exact-matches its frozen consequence rows; its
hash is nonnull. A verified row has that hash null. Missing, extra, duplicate,
reordered, self-scoped, or unclassified claims abort. This registry—not the
prose label “load bearing”—makes V-B5 through V-B8 as executable as the legal
claims.

The treatment of named risk classes is frozen:

| Risk class | V1 disposition |
|---|---|
| State/local | State of residence or government level alone never proves coverage or noncoverage. Direct classification requires the inventory-backed applicable state/jurisdiction coordinate plus the registered Section 218 group/position and public-retirement-system facts. Otherwise use the registered expected mapping or `unresolved`. |
| Federal | Federal status alone never identifies CSRS, FERS, or CSRS Offset. Direct treatment requires the registered system/service facts; otherwise modeled or unresolved. |
| Railroad | Industry/occupation alone never proves Railroad-covered employer or service. Directly supported Railroad remuneration is non-OASDI; separately covered jobs remain separate. Unsupported cases are modeled or unresolved. |
| Clergy/religious | Occupation alone never proves a ministerial concept or approved exemption. Direct treatment requires the registered remuneration and exemption facts. |
| Student | Enrollment and education industry never prove the employer-school nexus or statutory student exception. Absent that nexus, no direct exclusion is allowed. |
| Residual statutory exclusions | Domestic/agricultural thresholds, election work, family/casual service, foreign-government or international-organization service, nonresident-alien rules, and any other class require an effective-year registered rule and its required facts. |

### 4.2 Independent source inventory, reference-year map, and crosswalk

The crosswalk may not define its own completeness universe. Before the
crosswalk is authored, a source-only extractor must publish the immutable,
byte-pinned
`data/external/psid_covered_earnings_source_field_inventory_v1.json`.
Its schema and artifact ID are respectively
`psid_source_field_inventory.v1` and
`psid_covered_earnings_source_field_inventory.v1`. The extractor is
structurally unable to import the covered-earnings reader, crosswalk, candidate
code, or adjudication registries. It reads only the registered PSID setup,
layout, label, codebook/questionnaire, and fixed-width-file identities and
binds every source byte by path, SHA-256, and size.

An independently ratified `psid_questionnaire_slot_specs.v1` defines the
inventory domain. The top-level object has exactly `schema_version`,
`artifact_id`, `source_authority_manifest`, `interview_waves`, `roles`,
`job_slot_ids`, `questionnaire_component_slot_ids`, `field_purposes`,
`expanded_slots`, `expanded_slot_count`, `expanded_slot_keyset_sha256`, and
`canonical_order`. Both identity literals are
`psid_questionnaire_slot_specs.v1`.
The source-only authority manifest has exact immutable document/path/size/hash
rows; the dimension arrays are nonempty, source-derived, and may not be
supplied by the crosswalk. It expands every staged family wave
`1968..1997,1999,2001,...,2023`, both questionnaire roles
`head_or_reference_person` and `spouse_or_partner`, every
questionnaire-defined job slot plus the role-total, farm, and business
aggregate slots, every questionnaire-defined remuneration component/context
slot within each job or aggregate (including separately asked wage/salary,
bonus/overtime/tip/commission, farm, unincorporated-business labor, loss, and
other amount concepts where present), and each of these ordered field
purposes:

```json
[
  "interview_and_role_attachment",
  "amount",
  "reporting_unit",
  "month_or_exposure",
  "assignment",
  "employee_self_or_mixed",
  "incorporation",
  "government_level",
  "industry",
  "occupation",
  "enrollment",
  "job_identifier",
  "state_of_residence",
  "section_218_group",
  "section_218_position",
  "public_retirement_system_participation",
  "federal_retirement_system",
  "federal_service",
  "railroad_covered_employer",
  "railroad_covered_service",
  "ministerial_service",
  "clergy_remuneration",
  "church_employee_service",
  "religious_order_service",
  "clergy_or_religious_exemption",
  "domestic_service",
  "agricultural_service",
  "election_work",
  "family_service",
  "casual_service",
  "foreign_government_service",
  "international_organization_service",
  "nonresident_alien_status",
  "employer_school_nexus",
  "statutory_student_service"
]
```

The array has exactly 35 literals in this order. The final 23 are the
complete named direct-law microfact-purpose domain in v1. Threshold
amounts/periods continue to use the already enumerated `amount`,
`reporting_unit`, and `month_or_exposure` purposes alongside the applicable
service-purpose row. A new direct-law fact or a renamed/merged purpose is a
slot-registry version change; a generic “other legal fact” purpose is
forbidden.

Each `expanded_slots` row has exactly `source_inventory_key`,
`questionnaire_slot_id`, `interview_wave`, `earnings_reference_year`, `role`,
`job_slot`, `questionnaire_component_slot`, `slot_kind`, `field_purpose`,
`questionnaire_presence`, `source_document_ids`, and
`source_locator_sha256s`. `questionnaire_presence` is `asked |
structural_query_slot`; source arrays are ordered and nonempty and bind the
complete pages/layout regions establishing the slot or its absence query.
`slot_kind` is exactly `remuneration_component | role_total |
farm_aggregate | business_aggregate | context_only`; the source-derived
questionnaire structure, not the crosswalk, assigns it.
Each `source_locator_sha256` hashes only the canonical
document/path/page-or-layout/field-coordinate tuple and excludes source
content, labels, values, and full-file digests; the full changing bytes remain
bound in the authority manifest and inventory rows.
`source_inventory_key` is literal `psid-slot:` followed by SHA-256 of
§10.1 canonical bytes of the exact array
`[interview_wave,earnings_reference_year,role,job_slot,
questionnaire_component_slot,slot_kind,field_purpose]`;
`questionnaire_slot_id` is the same tuple without purpose under the identical
encoding and prefix `psid-questionnaire-slot:`. Canonical order is dimension
order as stored above; count/hash bind the entire unique key stream.

The inventory artifact itself has exactly `schema_version`, `artifact_id`,
`questionnaire_slot_specs_identity`, `source_authority_manifest`, `rows`,
`row_count`, `row_keyset_sha256`, `canonical_order`, and `integrity`.
The first two values are the literals above.
`questionnaire_slot_specs_identity` has exactly `schema_version`,
`artifact_id`, `sha256`, `expanded_slot_count`, and
`expanded_slot_keyset_sha256`; it binds the separately ratified slot registry
and exact-matches its count and key hash. `source_authority_manifest` is an
exact deep copy of that registry's complete manifest. `rows` is the expansion
below. `row_count` equals both its length and `expanded_slot_count`;
`row_keyset_sha256` hashes the ordered canonical
`source_inventory_key` array and equals the slot-registry key hash; and
`canonical_order` is the exact dimension order declared above. `integrity`
has exactly `canonicalization`, `content_sha256`,
`extraction_implementation_commit`, and `reproduced_from_source_bytes`, with
the §6.1 canonicalization/content-hash construction, a 40-lowercase-hex
commit, and literal boolean `true`. A manifest, row, count, order, or identity
supplied by the crosswalk is invalid.

The slot registry is derived from and cites the complete questionnaire/layout
domain, not from fields already used by `family.py`. A source inventory that
contains only the current role totals is therefore incomplete by construction.
For every wave×role×job×component/context×purpose key, the inventory has
exactly one row with:

`source_inventory_key`, `questionnaire_slot_id`, `interview_wave`,
`earnings_reference_year`, `role`, `job_slot`,
`questionnaire_component_slot`, `slot_kind`, `field_purpose`,
`source_disposition`,
`raw_field_ids`,
`exact_label_texts`, `full_source_descriptions`, `value_code_map_id`,
`value_code_map`, `typed_parse_specs`, `reporting_unit`, `reference_periodicity`,
`information_date_basis`, `source_file_ids`, `source_byte_sha256s`,
`layout_coordinates`, `missing_raw_tokens`, and `absence_proof`.

The inventory row's two keys and order must positionally equal
`expanded_slots`;
`earnings_reference_year` is always the JSON integer
`interview_wave - 1`. `source_disposition` is exactly `present` or
`structural_missing`. A present row has nonempty field IDs, complete labels
and descriptions, and null `absence_proof`. For a coded present field,
`value_code_map_id` is a nonempty stable ID and `value_code_map` is the
complete ordered raw-token-to-source-meaning array; for an uncoded present
field they are respectively null and the exact empty array. A
present row's `reference_periodicity` is the source-backed literal
`annual | monthly | weekly | hourly | point_in_time | not_applicable`, and
`information_date_basis` is the source-backed literal
`reference_year_end | interview_date | reported_spell_end |
field_specific_date | not_applicable`. The inventory source commitments
establish both values; the crosswalk cannot author or relabel them. A present
row's `missing_raw_tokens` is the complete ordered array of literal
fixed-width tokens that the registered source layout/codebook defines as
blank, missing, refused, unknown, inapplicable, or otherwise not a typed
microfact value. For a coded field it exact-matches the tokens whose complete
value-code map has typed disposition `missing`; for an uncoded field it is
derived directly from the source field grammar and includes the exact-width
blank token. The crosswalk or runtime cannot add or remove a token. A
structural-missing row has empty field, label, description, value-map,
typed-parse, source-file, source-digest, layout, and missing-token arrays, null
`value_code_map_id` and `reporting_unit`, literal `not_applicable` for both
timing fields, and a nonempty absence proof that binds the complete searched
label/layout domain and search implementation. “Not used by the existing
reader,” a short label, or the crosswalk's declaration is not an absence
proof. Duplicate or missing component-purpose keys, an unscanned layout
column, a raw code without a disposition, source drift, or a
wave/reference-year mismatch aborts inventory ratification.

For a present row, `typed_parse_specs` has exactly one object per
`raw_field_id` in identical order. Each object has exactly `raw_field_id`,
`parse_kind`, `raw_width`, `value_code_map_id`, `signed`,
`decimal_places`, `implied_scale`, `typed_value_type`, and
`typed_value_unit`. `raw_width` is the positive JSON-integer width in the
source layout. A `value_code_map` parser has the row's nonnull map ID, null
`signed`, `decimal_places`, `implied_scale`, `typed_value_type`, and
`typed_value_unit`; its chosen entry supplies type, unit, and canonical
value. A `fixed_width_numeric` parser has null map ID, source-backed
boolean `signed`, nonnegative JSON-integer decimal places, a positive reduced
rational implied scale, output type `rational | json_integer`, and the
source-backed nonempty unit. It accepts only the exact-width ASCII
sign/digit/decimal grammar declared by those fields and then applies the
scale in exact rational arithmetic; a `json_integer` output additionally
requires an exact integral result. No whitespace trim, locale conversion,
floating-point parse, coercion, or inferred unit exists. These parser specs
are source-inventory evidence, not crosswalk fields, and their coordinates
and grammar are included in the inventory content hash.

`earnings_reference_year = interview_wave - 1` is the income-attachment
coordinate. It does not assert that a current-job context answer describes
that prior-year service. The crosswalk may attach such a field only when its
registered `admissible_information_date_rule` and job-match rule prove the
reference-year relationship; otherwise the inventory row remains present but
the production consequence is its predeclared `modelable | unresolved`
branch.

The frozen production wave-to-reference-year map is explicit:

| `year_source_class` | Exact mapping and production meaning |
|---|---|
| `direct_questionnaire` | Reference years `1968..1996` map one-to-one to interview waves `1969..1997`; reference years `[1998,2000,2002,2004,2006,2008,2010,2012]` map to waves `[1999,2001,2003,2005,2007,2009,2011,2013]`. |
| `structural_gap_imputed` | Reference years `[1997,1999,2001,2003,2005,2007,2009,2011]` have no direct income wave and are derived only by the cutoff-before-imputation law below. |
| `claim_specific_boundary_gap` | Reference year `2013` has no direct production wave and is derived only after the operative benefit claim year is known. |
| `boundary_2014` | Year `2014` is the frozen projection-boundary row, not the 2015 interview's prior-year answer. |
| `projected` | Years `2015..2022` are frozen projected proxy rows; post-boundary questionnaire answers are inadmissible person facts. |

The 1968 interview's reference year is 1967 and is outside the attachable
production support. Interview waves 2015–2023 remain inventoried because
their existence and exclusion must be auditable, but none is a direct
production earnings source. Every year-indexed production component row,
support row, candidate basis, target selector, Option-C row, evaluation
stratum, and corrected result row carries the literal `year_source_class`.
An explicitly nonannual career row carries
`year_source_class: null`; a typed legacy `before_context` row is not
reclassified as a production source and also carries null unless its frozen
predecessor authority supplies an exact class. An all-key inventory
disposition instead carries its exact three-state
`inventory_year_disposition`. No class may be inferred from row availability.

The reference-year seams, not interview-year aliases, are:

| Reference years | Frozen source-concept adjudication |
|---|---|
| 1968–1974 | Preserve role totals. Unsupported job/context slots are explicit inventory absences. |
| 1975–1977 | These are interview waves 1976–1978. The pinned wave-1976 description for reference-year 1975 field `V4379` includes unincorporated-business labor income, so that source is `mixed`. The wave-1977/1978 short labels do not establish `wages_only`; V-B6 requires their exact reference-year 1976/1977 concepts and code maps or registration aborts. |
| 1978–1992 | Pre-ER edited totals include the applicable farm/business labor parts. Separate fields split or validate the total and are never added twice. |
| 1993–2001 | The farm/business concept seam is reference year 1992/1993: wave 1994 describes 1993. ER role totals and separately carried farm/business labor components combine exactly once. Direct years and biennial structural gaps retain distinct source classes. |
| 2002–2012 | Modern job blocks begin with interview wave 2003 and therefore describe reference year 2002, then 2004, …, 2012. Job amounts, units, and timing reconcile to the appropriate prior-year role total; odd reference years remain structural gaps. |
| 2013 | Claim-specific benefit gap only; no unconditional person-level source row exists. |
| 2014 | Frozen boundary row only. |
| 2015–2022 | Projected path only. |

The implementation must then publish a separate immutable, fully expanded
`psid_covered_earnings_crosswalk.v1`. Its top-level object has exactly
`schema_version`, `artifact_id`, `source_inventory_identity`,
`inventory_key_dispositions`, `component_rows`,
`component_row_count`, `component_row_keyset_sha256`,
`rule_registry_identities`, `canonical_order`, and `integrity`. Both leading
literals are `psid_covered_earnings_crosswalk.v1`.
`source_inventory_identity` binds the path, artifact ID, schema, SHA-256,
row count, and ordered keyset hash of the independently ratified inventory.
`canonical_order` is questionnaire-slot order. `integrity` has the exact
canonical content-hash schema used by the inventory.
`rule_registry_identities` is the exact ordered nine-row
`(registry_id,sha256)` array for `verification_claim_specs.v1`,
`historical_coverage_rule_specs.v1`,
`psid_structural_missing_consequence_specs.v1`, and the six executable
registries below. Every digest is independently recomputed from the
top-level registered deep copy; `direct_classification_rule_ids` foreign-key
the historical registry, and a self-reported or omitted rule identity
aborts.

`inventory_key_dispositions` has exactly one row per independent inventory
row in identical order and no other row. Each has exactly
`source_inventory_key`, `questionnaire_slot_id`, `field_purpose`,
`source_disposition`, `inventory_year_disposition`,
`structural_missing_consequence_spec_id`, and `crosswalk_use`. The first four
fields exact-match the inventory.
`inventory_year_disposition` is independently derived as
`direct_questionnaire` for the exact attachable reference-year set
1968–1996 plus `[1998,2000,2002,2004,2006,2008,2010,2012]`,
`inventory_only_outside_production_support` for interview-wave 1968 /
reference-year 1967, and `inventory_only_post_cutoff` for interview waves
`[2015,2017,2019,2021,2023]` / reference years
`[2014,2016,2018,2020,2022]`.
`crosswalk_use` is `component_input | component_context |
lineage_only` and is recomputed from the independent slot kind, purpose,
production information cutoff, and complete registered component attachment
rules; it is not a crosswalk-selected completeness label. A present row has
null consequence ID. A
`structural_missing` row foreign-keys exactly one row in the independent
`psid_structural_missing_consequence_specs.v1` below; it may never be treated
as a zero or omitted. Both inventory-only year dispositions force
`crosswalk_use: lineage_only` and cannot be referenced by a component,
candidate, target, ledger, or consumer. This all-key disposition array—not the smaller
component array—is G17's exact crosswalk completeness comparator.

`component_rows` has exactly one row for every independently inventoried
`questionnaire_slot_id` whose `slot_kind` is
`remuneration_component | role_total | farm_aggregate |
business_aggregate` and whose every purpose row has
`inventory_year_disposition: direct_questionnaire`, including a row whose
amount purpose is structurally missing. The filtered component-slot stream
is independently derived from the all-key array; the crosswalk cannot omit
or add a slot. A context-only or inventory-only questionnaire slot never
masquerades as a remuneration component. Each component row contains exactly:

`questionnaire_slot_id`, `interview_wave`, `earnings_reference_year`,
`year_source_class`, `role`, `job_slot`, `questionnaire_component_slot`,
`slot_kind`, `purpose_source_inventory_keys`, `source_disposition`,
`source_component_id`, `remuneration_type`, `amount_field_ids`,
`value_code_map_ids`, `reporting_unit`, `periodicity`,
`admissible_information_date_rule`, `annualization_rule_id`,
`reconciliation_rule_id`, `job_spell_match_rule_id`,
`se_aggregation_group_rule_id`, `coverage_state_group_rule_id`,
`era_seam_reason_codes`, `direct_classification_rule_ids`,
`optional_authority_consequence_ids`, `coverage_unknown_action`, and
`structural_missing_consequence_spec_ids`.
Every component row's `year_source_class` is the literal
`direct_questionnaire`; gap, boundary, projected, outside-support, and
post-cutoff inventory rows are produced or retained under their separate
laws and cannot enter this source-component array.

`purpose_source_inventory_keys` has exactly the complete ordered 35-key
§4.2 purpose domain, each mapped to the complete ordered array of independent
inventory keys for that purpose attached to the remuneration slot. An
attached key is either from that questionnaire slot or from a context-only
slot whose same wave/role/job attachment is proved by the registered
job-match rule. Those arrays are disjoint within the component row. Every
component-owned amount/unit/exposure key occurs in exactly one component row;
every state/direct-law microfact key occurs in the exact component/rule
closure independently derived from its slot and affected-record domain; and
a context-only or lineage-only key occurs once in
`inventory_key_dispositions` and may be referenced by multiple component
rows only when a registered reconciliation, job-match, or historical
direct-law rule enumerates those exact uses.
The component count and keyset hash bind the complete ordered
`questionnaire_slot_id` stream.

`remuneration_type` is exactly
`employee | self_employment | mixed | nonremuneration`; `mixed` is a
first-class source concept, not an implementation guess. A component
`source_disposition` is `present` iff its amount-purpose inventory rows and
every remuneration-construction input required by its value-code,
annualization, reconciliation, and job-match rules are present; otherwise it
is `structural_missing_required_input`. A missing state/direct-law microfact
does not erase a valid remuneration component: it remains present and takes
the applicable verified historical rule's coordinator-derived
`unresolved_action` fold under §5.1. Every raw field and value-code map is
reached through the purpose-key arrays and exact-matches the independent
inventory. Every
`value_code_map_id` uniquely resolves through `psid_value_code_specs.v1`,
whose entries deep-equal the corresponding inline inventory map.
`periodicity` is independently recomputed from the attached amount, unit,
and exposure rows' `reference_periodicity` values under the referenced
annualization rule. `admissible_information_date_rule` has exactly
`basis_source_inventory_keys`, `date_field_ids`, and `cutoff_relation`.
Its ordered basis keys identify every attached inventory timing fact; date
fields must be members of those rows' `raw_field_ids`; and cutoff relation is
`on_or_before_reference_service | interview_observation_only |
inadmissible_without_spell_proof`. The referenced job-match rule applies that
source-backed object to runtime interview/spell dates and enumerates every
admissible combination and exact outcome. An incompatible, missing, or
ambiguous combination follows its frozen failure branch. Neither timing
field is authored by the crosswalk.

The component row is an exact tagged union. In the `present` branch,
`source_component_id`, `remuneration_type`, nonempty `amount_field_ids`,
`admissible_information_date_rule`, and every applicable rule ID are nonnull and
exact-match their foreign rows. Reporting unit, periodicity, purpose arrays,
and rule IDs are nonnull/nonempty exactly when the independent purpose
dispositions and rule applicability require them and otherwise are null or
the exact empty array. `optional_authority_consequence_ids` is the complete
ordered array of activated `optional_row_consequences` whose independently
expanded affected key is in this component's purpose-key closure: a row is
activated exactly when its governing `direct_only_optional` rule's
`authority_status` is `authority_absent | authority_conflict`; a
`verified` rule forbids activation. Every linked verification-claim result,
when the rule has one or more claim IDs, must agree with the rule status, but
claim linkage is not the activation source and an untagged federal/Railroad
optional rule may have the exact empty claim-ID array. Its
`coverage_unknown_action` is `unresolved` iff at least one referenced
consequence is `unresolved`, and otherwise is `modelable`, including when
the array is empty. Registration recomputes that aggregation; the component
cannot declare it independently. `structural_missing_consequence_spec_ids`
is the exact empty array. In the `structural_missing_required_input` branch,
source component, remuneration, amount fields, value-code IDs, reporting
unit, periodicity, `admissible_information_date_rule`, and all five
executable rule/group IDs
are
null/empty; direct-classification and seam arrays are empty; and
`optional_authority_consequence_ids` is empty,
`coverage_unknown_action` is null, and
`structural_missing_consequence_spec_ids` is the nonempty ordered array
resolving every remuneration-construction-rule-required missing purpose
key's unique frozen consequence. A direct-law microfact absence never enters
this component-absence branch; it remains attached to a present remuneration
component and is handled by the §4.1/§5.1 fold. No executable field or rule
may hide in an absence row.

`psid_structural_missing_consequence_specs.v1` is a nonempty array ordered by
the independent inventory. It contains exactly one row per
`structural_missing` inventory key, each with exactly
`consequence_spec_id`, `source_inventory_key`, `questionnaire_slot_id`,
`field_purpose`, `consequence`, `reason_code`,
`governing_verification_claim_ids`, `governing_optional_rule_ids`, and
`governing_required_micro_fact_ids`.
`consequence` is `modelable | unresolved`; the claim and optional-rule arrays
are complete ordered foreign keys and may be empty; the microfact array is
the complete ordered foreign-key array and may be empty only when no
verified historical rule requires that key. Missing optional legal
authority continues to use
`historical_coverage_rule_specs[*].optional_row_consequences`; when both laws
apply to a key, consequence and reason must exact-match this registry.
When a governing required microfact exists, this structural registry's
consequence must equal its verified rule's `unresolved_action` and its reason
must equal that microfact's `missing_reason_code`. The structural row is
evidence of absence; the historical-rule fold is the sole operative runtime
action. A conflicting consequence/reason or an omitted governing fact aborts
registration.
Registration-required inventory/source proof may establish a genuine
structural absence, but absent or conflicting authority bytes still abort
under `verification_claim_specs.v1`. Thus questionnaire absence, optional
legal-authority absence, and required-authority failure are distinct tagged
states.

Six separately frozen executable registries close every referenced rule:

- `psid_value_code_specs.v1` maps every literal raw code, including
  employee/self-employed/**mixed** responses and missing sentinels, to one
  typed disposition;
- `psid_annualization_rule_specs.v1` declares required amount/unit/exposure
  inputs, exact rational operations, applicability, and the missing-input
  failure for each annualization ID;
- `psid_reconciliation_rule_specs.v1` declares role-total, job, farm, and
  business operands, precedence, exact-once equations, residual disposition,
  and failure;
- `psid_job_spell_match_rule_specs.v1` declares the admissible
  wave/reference-year timing, role and job identifiers, compatibility tests,
  ambiguity branch, and stable ID construction; and
- `psid_se_aggregation_group_rule_specs.v1` declares the person/year/service
  keys under which SE gains and losses may net and constructs the stable
  `se_aggregation_group_id`; and
- `psid_coverage_state_group_rule_specs.v1` declares which same-service
  components co-move and which must remain separate.

Each is a nonempty array ordered lexicographically by its first ID field,
with unique IDs, exact inventory-key foreign keys, and no unreferenced rule.
Their exact row schemas are:

- a value-code row has exactly `value_code_map_id`,
  `applicable_source_inventory_keys`, `source_commitments`, and `entries`;
  every entry has exactly `raw_code_token`, `source_meaning`,
  `typed_disposition`, `typed_value_type`, `typed_value_unit`,
  `normalized_value`, and `missing_reason_code`.
  Typed disposition is `employee | self_employment | mixed |
  nonremuneration | rational | json_integer | boolean | enum | missing`.
  For the five remuneration/enum dispositions, type is literal `enum`, unit
  is null, and normalized value is the registered enum token (the
  disposition literal itself for a remuneration disposition). A rational
  value is a reduced numerator/positive-denominator pair with a registered
  nonempty unit; a JSON-integer value excludes booleans and also has its
  registered nonempty unit; a boolean has literal boolean normalized value
  and null unit. A missing entry has the other three typed fields null. A
  missing reason is nonnull exactly for `missing` and otherwise null. Thus
  coded boolean/enum direct-law facts have an inventory-backed typed value
  path rather than an implementation coercion. Every literal raw code in the
  inventory occurs once. Within one map, all nonmissing entries have the same
  `typed_value_type` and `typed_value_unit`; only normalized values and
  dispositions may differ, so the parser's output signature cannot depend on
  the observed token;
- an annualization row has exactly `annualization_rule_id`,
  `applicable_source_inventory_keys`, `required_field_purposes`,
  `input_units`, `output_unit`, `formula_ast`, `rounding_rule`,
  `missing_input_disposition`, and `reason_code`;
- a reconciliation row has exactly `reconciliation_rule_id`,
  `applicable_source_inventory_keys`, `ordered_operand_selectors`,
  `precedence_order`, `exact_once_formula_ast`, `residual_disposition`,
  `failure_disposition`, and `reason_code`;
- a job-match row has exactly `job_spell_match_rule_id`,
  `applicable_source_inventory_keys`, `allowed_wave_reference_pairs`,
  `required_role_fields`, `required_job_identifier_fields`,
  `compatibility_predicate_ast`, `ambiguity_action`,
  `stable_component_id_preimage_fields`, `failure_disposition`, and
  `reason_code`; and
- an SE-aggregation row has exactly `se_aggregation_group_rule_id`,
  `applicable_source_inventory_keys`, `person_year_key_fields`,
  `same_service_key_fields`, `eligible_gain_concepts`,
  `eligible_loss_concepts`, `forbidden_cross_group_offsets`,
  `group_id_preimage_fields`, `family_aggregate_allocation_rule`,
  `failure_disposition`, and `reason_code`; its stable output is
  `se_aggregation_group_id`.
  `family_aggregate_allocation_rule` has exactly `action` and
  `allocation_source_inventory_keys`; `action` is the literal
  `require_source_registered_person_allocation`, and its ordered key array
  must resolve present person-allocation fields or be empty. A combined
  family amount with an empty or unusable allocation-key array fails rather
  than entering a group; and
- a coverage-group row has exactly `coverage_state_group_rule_id`,
  `applicable_source_inventory_keys`, `same_service_key_fields`,
  `co_moving_component_types`, `separate_component_types`,
  `mixed_component_rule`, `group_id_preimage_fields`,
  `failure_disposition`, and `reason_code`.

Every `*_ast` and each verified historical rule `transform` uses the closed
`psid_rule_ast.v1` grammar. A node is exactly one of:
`{"op":"field","source_inventory_key":...,"raw_field_id":...}`;
`{"op":"micro_fact","micro_fact_id":...}`;
`{"op":"fact_binding","fact_binding_id":...}`;
`{"op":"rational","numerator":<integer>,"denominator":<positive
integer>,"unit":<registered nonempty unit>}`;
`{"op":"json_integer","value":<JSON integer excluding booleans>,
"unit":<registered nonempty unit>}`;
`{"op":"literal","value":<string, boolean, or null>,
"value_type":<rational, json_integer, enum, or boolean>,
"unit":<registered unit or null>}`; or
`{"op":<operator>,"args":[...]}`, where operator is one of
`add | subtract | multiply | divide | minimum | maximum | equal | less |
less_equal | greater_equal | greater | and | or | case`. `subtract`,
`divide`, `equal`, and the four ordered comparisons have exactly two
arguments; `case`
has exactly three ordered arguments `(boolean predicate, true branch, false
branch)` and evaluates only the selected branch; `add`, `multiply`,
`minimum`, `maximum`, `and`, and `or` have at least two arguments and evaluate
left to right, with boolean short-circuiting only for `and` and `or`.
Registration type- and unit-checks every node and output. Rational
`add | subtract | minimum | maximum` operands have one identical unit and
retain it. Rational multiply permits exactly one `dimensionless` operand and
returns the other unit. Rational divide permits a dimensionless denominator
and returns the numerator unit, or identical units and returns
`dimensionless`; every other unit pair is invalid. `equal` requires
identical operand type and unit and returns boolean/null-unit. Each ordered
comparison requires two rational or two JSON-integer operands with identical
type/unit and returns boolean/null-unit. `and | or` require and return
boolean/null-unit; and `case` requires a
boolean/null-unit predicate plus branches with identical type, unit, and
nullability and returns that branch signature. String literals declare
enum/null-unit and booleans declare boolean/null-unit. A null literal's type
and unit declare its branch signature; numeric types require a nonempty unit
and boolean/enum require null unit. Null is permitted only where both case
branches have that same explicitly nullable signature.
There is no unit inference or coercion. A referenced missing/null
field, wrong type, evaluated division by zero, or nonfinite result takes the
rule's registered failure branch; there is no implicit null propagation.
Every field node foreign-keys a `present` inventory row and its
`raw_field_id` must be a member of that row's `raw_field_ids`, so a
multi-field inventory row never leaves operand selection to field order or
an implementation default.
Every `micro_fact` node is permitted only in a verified
`historical_coverage_rule_specs[*].covered_facts[*].premise_ast` or
`.excluded_facts[*].premise_ast`, foreign-keys exactly one slot in that
same binding, and receives only the coordinator-derived typed value from the
§4.1 ledger. A `fact_binding` node is permitted only in that rule's
`transform`, foreign-keys exactly one row in its covered or excluded binding
arrays, and receives only the coordinator-evaluated nonnullable boolean from
that row's premise. A historical transform may use `fact_binding`, rational,
JSON-integer, literal, and registered operator nodes but no direct `field` or
`micro_fact` node; every bound fact must appear at least once.
Its AST output is exactly one nonnull enum literal
`covered_wage | covered_self_employment | noncovered | no_disposition`.
If either bound-fact array is nonempty, the coordinator enumerates every
boolean vector in complete covered-then-excluded binding order, with
`false` before `true` at each position, evaluates the typed transform once
per vector, and requires at least two distinct enum results. Thus
`case(binding,noncovered,noncovered)`, a literal constant enum, or any other
semantically constant transform cannot cite facts. A constant enum transform
is registration-valid only for the exact empty-covered/empty-excluded
unconditional branch, for which `required_micro_facts` is also exactly empty.
The sealed coordinator—not the AST or runner—wraps that enum with the rule's
registered `status_family` and `reason_code` to construct the exact
`direct_law_transform_result.v1` object in §4.1. Any other transform output
type or value is invalid at registration.
No float literal, executable code, callback, path, implementation default, or
unregistered operator is allowed. Selector/key arrays have declared field
order; formula operands must foreign-key inventoried present rows; every
disposition/failure/reason field is a closed literal registered before
production values are opened.

An ID missing from its registry, a rule with an implicit default, a
nonexecutable prose-only operation, or an input not present in the inventory
aborts registration. Direct role/job annual amounts have first precedence.
Role totals and separate components have second precedence and reconcile
under the frozen rule. Underidentified mixed employee/self-employed amounts
use the registered exact-dyadic conditional expected allocation or remain
`unresolved`; v1 does not draw a mixed share. A combined family farm amount
is never silently assigned to a person.

There is no unconditional atomic common-ledger row for a structural gap.
After Stage C has fixed an operative claim year, the benefit assembler first
removes every corrected source component after that year and only then applies
the registered component-wise immediate-neighbor gap rule. Thus a 2013
claimant cannot use 2014 to fill 2013, while a later claimant may. The same
ordering applies to every odd structural gap after 1996. Opening-backfill
claim-year adjudication occurs before this derivation. Revenue has no 2013 or
other pre-2015 consumer row. Official target years with no claim-independent
model analogue remain exposure-honest, zero-weight, selection-ineligible
diagnostics under §6.2; they cannot create a synthetic consumer row.

`g17_inventory_crosswalk_evidence.v1` has exactly `schema_version`,
`comparison_rows`, `comparison_count`, `comparison_id_order`, and
`overall_status`. `comparison_rows` has exactly fifteen rows ordered
G17-C01 through G17-C15 for: inventory key stream; all-key disposition
stream; component-slot stream; structural-missing consequences; historical
coverage-rule closure; bound-fact/derived-required-microfact
inventory/presence/premise/action closure;
value-code registry; annualization registry; reconciliation registry;
job-match registry; SE-aggregation registry; coverage-group registry; the
nine verification-claim results; the frozen wave/reference/source-class map;
and
`physical_source_structure_projection.v1`. Each row has exactly
`comparison_id`, `domain_name`, `expected_count`, `actual_count`,
`expected_sha256`, `actual_sha256`, and `status`. Counts are nonnegative JSON
integers excluding booleans, hashes cover the complete canonically ordered
domain named by the row, and status is `pass | fail`. The required-microfact
row binds every complete covered/excluded
`(rule_id,fact_binding_id,premise_ast,micro_fact_slots)` specification, the
coordinator-derived `required_micro_facts` array, every complete
`(rule_id,micro_fact_id,field_purpose,source_field_ref,typed_value_type,
typed_value_unit,presence_predicate_ast,missing_reason_code)` slot, every
independently expanded coordinator presence-ledger row, and the exact
fact-binding results in `direct_law_action_trace.v1`. `comparison_count` is
literal 15;
`comparison_id_order` is the exact
ordered ID array; and `overall_status` is `pass` iff all fifteen
expected/actual count and hash pairs are equal and all fifteen domains are
nonempty. G17 additionally requires the claim-result count to be exactly nine
and independently derives every expected stream from the inventory,
source-only slot expansion, authority results, affected record domain, and
registered year map rather than a crosswalk or runner count/digest. An empty,
missing, extra, duplicate, wrong-purpose, self-scoped, or uninventoried
required fact fails. A mismatch between either bound-fact array and the
derived required-fact concatenation, an empty binding slot array, a
premise/slot mismatch, an unbound factual premise, or a fact-bearing
constant transform also fails. Missing support fails the gate; it never
shrinks a domain.

### 4.3 Production information cutoff and status evolution

The micro-information cutoff is the frozen 2014 projection boundary. Direct
observed earnings and job-context lineage ends with income year 2012; income
year 2013 remains the claim-specific gap in §4.2, and 2014 remains
`boundary_2014`. Only context already admissible for the
observed-through-2012 lineage and attributes already present in the
registered pre-mortality 2014 seed domain are admissible.
Official pre-2015 aggregate calibration targets are calibration evidence, not
person facts. No realized job, industry, occupation, government,
self-employment, incorporation, enrollment, or earnings answer outside that
frozen lineage may enter a 2013–2022 production component/status path.

Longitudinal observed jobs match only under the literal
`job_spell_match_rule_id`: same role, verified job identifier where present,
and compatible interview/reference-year timing. Ambiguous or unmatched jobs
close the old spell and create a new stable component ID; row proximity never
matches a spell. `structural_gap_imputed`,
`claim_specific_boundary_gap`, and `boundary_2014` retain those literal
provenance states and never masquerade as direct questionnaire observations.
The base correction operates on the direct adjacent components. Only the
benefit assembler may derive a gap, after it receives the final Stage-C
operative claim year and applies the cutoff described in §4.2.

For an incumbent, the last admissible direct-questionnaire wage/SE expected
shares initialize two
stable synthetic aggregate IDs, `projected#wage` and
`projected#self_employment`, at the 2014 boundary. In every 2014–2022 year,
the selected candidate's registered mixed-allocation logit divides the frozen
nonnegative person-total proxy between those IDs; the two pre-measurement
gains sum exactly to the nonnegative proxy. A negative projected person total
is preserved as a non-SE source anomaly and produces zero gain unless a
separate admissible source identifies it as an SE loss. V1 models no
projected employer count or job birth/death and makes no job-level projection
claim.

For dependence, each `(person,year,projected#wage)` and
`(person,year,projected#self_employment)` receives its own literal
`coverage_state_group_id`; no unobserved projected-employer grouping is
invented. Observed same-service components share or separate only through the
registered `coverage_state_group_rule_id` in §4.2.

The candidate's calendar-year/component functions in §5.3 then produce the
annual deterministic coverage-probability path. A scheduled entrant
initializes the same two synthetic IDs at first modeled presence using only
its frozen proxy total and attributes already admissible to the projection.
Later realized answers are forbidden even if they exist in a staged file.
The two synthetic component gains plus published measurement deltas reconcile
to the frozen person total each year.

The status law advances annually, including projected odd years. A
questionnaire structural-gap year is derived component-wise only after the
benefit cutoff. Years 1997–2011 inherit `structural_gap_imputed`; 2013
inherits `claim_specific_boundary_gap`; neither may become
`direct_questionnaire`. The underlying frozen
earnings projection's odd-year amount carry is not altered or claimed
resolved. `odd_year_earnings_carry` therefore remains in §9.2.

## 5. Classification, measurement, and uncertainty

### 5.1 Option A: component/status classification

Remuneration typing is resolved before statutory coverage. It consumes only
inventory-backed fields through `psid_value_code_specs.v1` and produces
exactly `employee`, `self_employment`, or `mixed`; a source that cannot be
typed follows its registered unresolved consequence. A `mixed` source is
split under §5.2 before either child is classified. A candidate may not infer
remuneration type from the aggregate target it is trying to match.

Direct statutory classification occurs only when §4.1's authority for every
applicable `registration_required | direct_only_optional` verified rule is
complete and every `required_micro_facts` member of every such rule is
coordinator-derived present. If any required fact is absent, that rule's
`transform` is not executed; the frozen missing-fact fold below applies.
That required array must already equal the covered-then-excluded binding-slot
derivation; a rule cannot declare an empty required array while naming a
covered or excluded premise. When all facts are present, the coordinator
evaluates every bound premise and direct status is the unique
`direct_law_controlling_result.v1` status under §4.1; a same-rank conflict,
lower-rank contradiction, absent dispositive result, or typed-result failure
aborts before fitting rather than choosing a status.
Every other in-domain homogeneous record receives exactly one of:

- a deterministic conditional probability vector from a registered
  expected-value mapping;
- the same probability model plus registered correction draws where a
  distribution is required; or
- `unresolved = 1`.

Private-sector, positive proxy, government level, industry, occupation,
self-employment, incorporation, assignment flags, and enrollment are
features or risk strata, not legal truth. Unknown never defaults to
private/covered. Career data-completeness ratios and OASDI coverage
probabilities have different field names, denominators, and meanings.

A wage-typed derived component
has structural probability zero for `covered_self_employment`; an SE-typed
derived component has structural probability zero for `covered_wage`.
`noncovered` and `unresolved` remain possible for either type. A source whose
wage/SE type is uncertain must first take §5.2's reconciled mixed allocation;
the status classifier may not use cross-type coverage probability to hide an
unresolved remuneration type.

For a concrete record, effective `coverage_unknown_action` starts with the
component's registration-time value and folds every applicable verified
rule whose `required_micro_facts` are absent: `unresolved` dominates, and
otherwise the rule's singular `unresolved_action`/component value is
`modelable`. The runtime only executes this frozen fold; it cannot choose an
action. Effective `coverage_unknown_action` is exactly `modelable` or
`unresolved`. For a
modelable wage component with candidate coverage probability \(q\), the
status vector is exactly `[q,0,1-q,0]`; for modelable SE it is
`[0,q,1-q,0]`. For an unresolved wage component it is `[0,0,0,1]` with a
wage type reason code; for unresolved SE it is the same vector with an SE
type reason code. Direct legal classification remains a one-hot vector.
There is no fitted unresolved share and no third complement-allocation
branch in v1. Changing a registered crosswalk/rule policy from `modelable` to
`unresolved` or vice versa requires fresh registration; different
record-level outcomes caused by coordinator-derived fact presence do not
rewrite either artifact.

The crosswalk freezes the authority-availability branch for every inventory
key, and the verified legal registry freezes the person-microfact fold;
the sealed coordinator derives every fact's presence and typed-value
commitment from inventory-backed slots and executes the fold recorded in
`direct_law_micro_fact_presence_ledger.v1`. No runner boolean, value,
applicability key, or shortened fact domain exists. G06 exact-compares the
independently expanded record×rule×fact domain, the derived missing-fact set,
the covered/excluded binding schemas, their inventory-slot concatenation and
runtime booleans, and the resulting action/classification trace.
Registration exact-compares each optional verification failure with its
enumerated affected-key set. The vacuous construction
`covered_facts: [uninventoried premise]`,
`required_micro_facts: []`, and a constant `noncovered` transform is not
parseable: the premise lacks a bound slot, the required array fails its
mandatory derivation, and a fact-bearing constant transform independently
fails registration. No missing optional source can widen a modelable domain,
and no candidate may convert an unresolved row to improve a target or gate.

Every classifier output retains `interview_wave`,
`earnings_reference_year`, and `year_source_class`, copied positionally from
the verified §4.2 map. A classifier, candidate, or downstream evaluator that
relabels a structural gap, boundary, or projected year as direct fails G12
and G17.

### 5.2 Option B: measurement layer

Option B runs after the inventory-backed source adjudication and before
coverage aggregation. It represents adjusted gains and admissible SE-loss
magnitudes as separate nonnegative channels. A gain mapping is
component-specific, extensive-margin preserving, and monotonically
nondecreasing in a positive source amount within its registered
reference-era/source-class stratum. A loss mapping may operate only on a
source component admitted to SE netting by the complete effective-year SECA
registry. Exact zeros remain a separate mass. Stable-person ID, never row
order, breaks ranks.

V1 is deliberately zero-preserving. After separately reported business/farm
components are recovered exactly once, a source-supported positive component
follows its positive mapping and a remaining zero stays zero. Aggregate cells
do not identify which zero careers contain omitted earnings, so v1 never
synthesizes a positive job or amount for an unsupported zero person-year.
Covered-share validation may therefore yield `no_eligible_candidate`.
A later zero-to-positive recovery model requires a new source-supported
estimand, occurrence and amount laws, draw namespace, candidate version, and
fresh registration.

The layer may only:

- recover an independently inventoried business/farm component once under its
  reconciliation rule;
- split a source whose literal `remuneration_type` is `mixed`;
- apply a registered deterministic conditional-mean or monotone rank mapping;
  and
- preserve the raw source, exact mapping delta, source class, and uncertainty
  limitation.

It may not turn an aggregate target into observed individual coverage, erase
the raw proxy, fit a national level, force an unconditional sign, or use an
assignment flag as administrative agreement.

Every mixed component becomes the two stable atomic IDs
`<source_component_id>#wage` and
`<source_component_id>#self_employment` before coverage classification.
`psid_reconciliation_rule_specs.v1` supplies the parent amount and permitted
operands; the selected candidate supplies only the registered conditional
expected wage share. Both children retain the parent's source-inventory key
and `mixed` reason code. It is forbidden to assign the entire parent to one
type or to create only one child.

The expected share is interpreted as an exact dyadic. The wage child is the
exact rational product; the SE child is exact parent minus wage child, so the
residual is literal zero. An admissible signed loss is split on its
nonnegative magnitude. The children use distinct
`coverage_state_group_id` values unless the frozen same-service rule proves a
same-type group; wage and SE children never share a group. V1 has no
stochastic mixed-share or measurement-residual variate. Adding either
requires a new finite draw law and candidate version.

A structural-gap amount is never measured independently. The benefit
assembler derives each gap component from already corrected adjacent
components after its operative-claim-year cutoff, then applies the
gap-reference-year statutory transform. A gap therefore cannot acquire a
free multiplier, mixed-share draw, or later questionnaire field. No
largest-remainder, cent, dollar, or display rounding enters any parent-child
or gap reconciliation.

### 5.3 Frozen selectable candidate set

Aggregate component moments cannot identify worker-level industry,
occupation, government, or persistence effects. V1 therefore uses no fitted
risk-stratum coefficient and no fitted person-specific transition parameter.
Observed self/other, incorporation, and direct component labels adjudicate
remuneration type under §4; they are not coverage labels. Direct legal rules
remain fixed and are never estimated.

`candidate_reference_era_specs.v1` freezes these earnings-reference-year
bases:

| Era ID | Reference years | Source-class law |
|---|---:|---|
| `ry1968_1974_early_totals` | 1968–1974 | Direct questionnaire years only. |
| `ry1975_1977_spouse_concept_seam` | 1975–1977 | Direct waves 1976–1978; the V-B6 concept adjudication, including `mixed`, is part of the basis. |
| `ry1978_1992_pre_er_totals` | 1978–1992 | Direct questionnaire years; pre-ER total reconciliation. |
| `ry1993_2001_er_biennial_transition` | 1993–2001 | Direct 1993–1996 and even 1998–2000 rows estimate parameters; odd structural gaps are derived and contribute no independent fitting row. |
| `ry2002_2014_modern_boundary` | 2002–2014 | Direct even 2002–2012 rows estimate parameters; structural gaps 2003–2011 and claim-specific 2013 are derived and selection-ineligible; 2014 is a separately labeled boundary validation row. |

These are reference-year eras. Seam IDs `1975`, `1978`, `1993`, and `2002`
are never shifted to interview years. `year_source_class` is crossed with
era ID in every candidate input/output row; a direct, structural-gap,
claim-specific-gap, boundary, or projected row can never share a stratum
label merely because its calendar year lies in the same era.

Within source-backed records not directly classified by law, a candidate may
estimate only:

- one wage unknown-coverage logit and one SE unknown-coverage logit per
  declared era basis;
- one positive wage gain multiplier and one positive SE gain multiplier per
  declared era basis; and
- one mixed wage/SE allocation logit per declared era basis, only where the
  crosswalk marks a source component `mixed`.

No other free parameter is permitted. The selectable candidates, in
complexity order, are:

| Candidate ID | Exact era basis | 2015–2022 law |
|---|---|---|
| `ab_era_constant_expected_v1` | One constant parameter of each permitted kind in each of the five reference-era bases, estimated only from direct rows. | Evaluate the last-era constant at boundary 2014 and carry it through 2022. |
| `ab_era_linear_expected_v1` | Intercept and reference-year slope in each era; the 1975–1977 slope is permitted. Gaps do not create observations. | Evaluate the registered 2002–2014 predictor at 2014, then extrapolate it annually through 2022. |
| `ab_pooled_seam_expected_v1` | One component-specific reference-year slope plus intercept shifts at 1975, 1978, 1993, and 2002. | Continue the global slope and last seam intercept annually through 2022. |

For every candidate and year, coverage and mixed-allocation predictors use
the logistic link; positive multipliers use the exponential link and must lie
in `[0.25,4.0]`. Linear time is exactly affine-scaled to `[-1,1]` over the
candidate's declared reference-era endpoints; pooled time is scaled over
1968–2022. A missing year inside an era is not reindexed or compressed.
Parameter domains are the compact intersection of coefficient bounds
`[-16,16]` and the all-years multiplier constraint. A boundary hit publishes
and makes the candidate ineligible.

Every uncertain incumbent and scheduled entrant receives the selected
candidate's calendar-year/component probability; direct classifications
override it. This is the exact annual status-evolution rule. Draw realizations
are conditionally independent across years given that probability path; v1
does not pretend that aggregate targets identify latent legal-status
persistence.

For a benefit structural gap, the candidate is evaluated on the corrected
left and admissible right components first; the benefit assembler then
derives the gap after cutoff. There is no gap-specific parameter vector.
For 2014 and projected years, the last reference-era law operates only on the
two synthetic aggregate IDs in §4.3 and retains `boundary_2014 | projected`
provenance.

`candidate_specs.v1` is the literal three-object array in the table order.
Each object has exactly `candidate_id`, `complexity_rank`, `era_basis`,
`parameter_specs`, `post_2014_rule`, `link_specs`,
`admissible_year_source_classes`, `model_target_selectors`, `numeric_spec`,
`identification_spec`, and `failure_disposition`. `era_basis` is an exact
deep copy of `candidate_reference_era_specs.v1`; `parameter_specs` fully
expands names, reference-year bases, bounds, and zero starting values;
`admissible_year_source_classes` admits only `direct_questionnaire` for
parameter estimation and labels boundary/projected evaluation separately;
`post_2014_rule`, links, and selectors are literal encodings of the laws above
and §6.2.
`failure_disposition` is `ineligible_publish`.

`numeric_spec` has exactly `algorithm`, `arithmetic`, `start_points`,
`max_iterations`, `projected_gradient_tolerance`,
`relative_objective_tolerance`, `step_tolerance`, and
`analytic_derivatives`. The values are
`deterministic_constrained_trust_region_v1`, `ieee754_binary64`,
the ordered \(2p+1\) starts consisting of the zero vector followed by
coordinate `+0.25,-0.25` perturbations in parameter order (deterministically
projected to the nearest feasible interior point),
`10000`, `1e-8`, `1e-12`, `1e-12`, and `true`. Convergence requires all
three tolerances; hitting the iteration limit is failure.

`identification_spec` has exactly `rank_tolerance`,
`maximum_condition_number`, `solution_certificate`,
`parameter_distance_tolerance`, and `objective_distance_tolerance`.
Rank tolerance is
`max(n_train_cells,n_parameters)*2**-52*largest_singular_value`; the maximum
condition number is \(10^8\); `parameter_distance_tolerance` is \(10^{-8}\) and
`objective_distance_tolerance` is \(10^{-10}\).
The solution certificate is
`deterministic_all_starts_agree_positive_curvature_v1`: every registered
start must converge, all parameter vectors must be within \(10^{-8}\) in
maximum coordinate distance, and all objective values must be within
\(10^{-10}\). The selected vector is the result from the first registered
start; the other starts are an agreement check. Its analytic Hessian must be
positive definite at that vector under the rank tolerance, and the train-cell
Jacobian must have full column rank. Failure makes the candidate ineligible.
This is an operationally unique result under the frozen algorithm and starts,
not a claim of a mathematically proven global optimum over the whole compact
domain.

The train-cell Jacobian contains only year-verified, positive-weight direct
target rows. A structural-gap, claim-specific-gap, boundary, projected, or
zero-weight diagnostic row may never increase rank or parameter count.
Regularization cannot substitute for identification. Failure of any fit,
boundary, rank, condition, or solution-certificate test makes the candidate
ineligible and publishes its disposition; settings may not change after
fitting starts. Profile-loss intervals for every free parameter publish as
diagnostics and are never described as administrative uncertainty intervals.

### 5.4 Deterministic-first draw law and nonlinear benefits

The canonical expected-value ledger is always emitted. Calibration, validation,
candidate selection, and the certified modeled-worker denominator use
analytic probabilities only—never realized status indicators or their finite
grid average. Distributional treatment is required for nondegenerate
coverage/status uncertainty that can change top-35 membership. The fixed
correction draw grid is `draw_index = 0..19`.

The draw identity is the `substantive_model_sha256` defined in §6.2 and
§10.2. It binds only model-affecting micro inputs, legal/crosswalk/rule bytes,
candidate/selection/draw laws, selected parameters, and the cell-scoped
fit/selection target identity. It does not bind a whole source-document
digest, held-out or zero-weight value, full target-artifact digest,
vintage-1 byte, evaluation registration, incident, output path, or full
evaluation provenance. Those remain bound by the separate
`evaluation_provenance_sha256`. This separation is normative: an
evaluation-only byte may change a diagnostic/report identity but may not
reseed a correction.

The namespace input is the exact ordered tuple

```text
(
  "covered_earnings.v1",
  substantive_model_sha256,
  stable_person_id,
  calendar_year,
  coverage_state_group_id,
  variate_name,
  correction_draw_index,
  residual_counter
)
```

encoded as canonical JSON UTF-8 bytes. The generator takes SHA-256 of those
bytes, interprets the first eight digest bytes as an unsigned big-endian
integer \(h\), and sets \(u=(h+0.5)/2^{64}\). Fixed CDF order is
`covered_wage`, `covered_self_employment`, `noncovered`, `unresolved`.
The group ID is the registered component/service dependence identity in
§3.1; all member records therefore consume the same uniform. In v1,
`variate_name` is exactly `coverage_status` and `residual_counter` is JSON
integer zero; no additional residual or mixed-share variate is registered.
Process hash functions, mutable seeds, row indices, wall clock, and global
RNG are forbidden.

Correction draws consume no projection, mortality, claiming, marriage, or
other model RNG stream. Calibration and selection use analytic conditional
means and analytic worker probabilities only; no capped quantity or
finite-draw fraction is a fitting target. The same correction draw feeds both
consumers. For
nonlinear career outcomes, each projection draw is crossed with all 20
correction draws; top-35 selection, AIME, PIA, and benefit outputs are
computed within each complete career draw before reduction. Before those
nonlinearities, every structural gap is derived component-wise after the
operative-claim-year cutoff inside that same career draw. Computing
`PIA(expected career)` and calling it `expected PIA` is forbidden.

The registered projection grid is the ordered `projection_draw_index =
0..19`. A fitting/validation selector first computes its complete
weight-scale-invariant ratio or share separately within each projection draw
using analytic correction states, then takes the arithmetic mean over the 20
projection draws; a ratio of across-draw numerator and denominator means is
forbidden. An annual linear or joint-state evaluation metric likewise
computes one analytic value per projection draw and publishes their arithmetic
mean and sample SD. A cross-sectional quantile, tail share, or career
nonlinear instead computes the complete statistic
within each `(projection_draw_index, correction_draw_index)` pair and
publishes the arithmetic mean and sample SD across the lexicographically
ordered 400-pair grid. Observed histories may repeat across projection draws,
but they are not given a different reduction rule.

The evaluation reports finite-grid error honestly. For each registered
metric that uses correction draws it compares the mean over all 20 projection
draws crossed with correction-draw prefixes `0..9` and `0..19`. For a
nonnegative currency, count, intensity, or quantile
metric, the symmetric absolute percent difference
\(2|m_{10}-m_{20}|/(|m_{10}|+|m_{20}|)\) must be at most 0.01; two literal
zeros pass and exactly one zero fails. For a share, probability, or rate, the
absolute difference must be at most 0.005. No signed
corrected-minus-baseline metric is registered: before/after comparison belongs
only to §12 after corrected-evidence lock. `draw_spec.v1` assigns every
corrected draw metric to exactly one of the nonnegative or share unit families
above; a `before_context` metric is `not_applicable`. An unassigned or
multiply assigned corrected metric fails. This is a deterministic resolution
check, not a confidence interval. Failure blocks correction-model eligibility;
it cannot trigger draw shopping.

`draw_spec.v1` has exactly `schema_version`, `draw_indices`,
`substantive_identity_field`, `namespace_fields`, `generator`, `cdf_order`,
`dependence_law`, `metric_unit_families`, `stability_tests`, and
`forbidden_rng_streams`.
The schema literal is `draw_spec.v1`; indices are the ordered integers
0..19; `substantive_identity_field` is the literal
`substantive_model_sha256`; namespace fields are the exact tuple order above;
generator is the literal SHA-256 midpoint law above; CDF order is the
four-status array;
dependence law is the §3.1 joint-enumeration law plus conditional
between-group and between-year independence; metric families and stability
tests are the three exact rules above expanded over every required metric in
`evaluation_specs.v1`; and forbidden streams are exactly
`["projection","mortality","claiming","marriage","global"]`. Missing,
extra, or multiply assigned variates or metrics fail registration.

Canonical input sorting, fixed key order, fixed reduction order, canonical
finite JSON, and the hash generator above make byte-identical replay and
row-order invariance hard gates.

`replay_specs.v1` freezes exactly three source orders and six comparisons.
The source orders are captured physical order (`P`), every registered source
row array reversed (`R`), and every source row array ordered by descending
SHA-256 of canonical stable-key bytes with ascending stable-key ties (`H`).
Each order runs twice in a fresh optimizer/module state, producing
`P1,P2,R1,R2,H1,H2`. The exact comparison order is:

```json
[
  ["replay:P1:P2","P1","P2"],
  ["replay:R1:R2","R1","R2"],
  ["replay:H1:H2","H1","H2"],
  ["order:P1:R1","P1","R1"],
  ["order:P1:H1","P1","H1"],
  ["order:R1:H1","R1","H1"]
]
```

Each replay run emits exact
`fit_selection_replay_bundle.v1` canonical bytes with keys
`schema_version`, `candidate_input_packet_hashes`,
`candidate_parameter_vectors`, `model_choice_predictions`,
`model_choice_losses`, `candidate_identification_results`,
`candidate_dispositions`, `selection_result`, `tie_result`,
`model_identity`, `substantive_model_sha256`,
`keyed_uniform_registry_sha256`, `expected_ledger_identity`,
`realized_ledger_identities`, and `claim_context_gap_identity`.
The three candidate-indexed arrays have exactly the §5.3 candidate order;
every prediction/loss array has the complete independently expanded
model-choice target order; `selection_result` and `tie_result` are the exact
§7.2 objects; and the realized array has the complete lexicographically
ordered 400-draw identity registry. Run/order metadata is intentionally
outside the equality preimage and lives in the result row.
`fit_selection_bundle_sha256` hashes that whole object. No
implementation-chosen replay sub-bundle, omitted field, self-scoped target
array, or empty registry is valid.

Outside that equality preimage, every run emits
`replay_source_order_evidence.v1` with exactly `schema_version`, `run_id`,
`order_id`, `expected_raw_source_order_sha256`, and
`actual_raw_source_order_sha256`. The hashes cover the complete
pre-canonicalization sequence of `(input_id,array_path,stable_row_key)` for
every registered source row. The coordinator independently constructs P, R,
and H from the captured P sequence and requires each actual hash to match the
order implied by the literal run ID. This metadata proves that P/R/H were
really executed; it is excluded from the canonical output bundle so the
invariance comparison remains meaningful.

Every pair must byte-match this entire bundle, thereby comparing all input
packets, parameter bits, predictions, losses, identification results,
dispositions, selection/tie evidence, substantive identity/hash, uniforms,
expected and all 400 realized ledger identities, and claim-context gap
identity.
Exactly six result rows are required; an empty, partial, duplicated, or
reordered registry fails G10. G14 separately performs a trusted second
fit/selection execution after applying the exact common multiplier `7.0` to
every PSID survey weight while leaving every target loss/objective weight
unchanged; all parameter bits, predictions, losses, candidate
dispositions, selection, and substantive model hash must match. Runtime,
evaluation-only provenance, and incident metadata are excluded from both
substantive comparisons.

## 6. New immutable calibration-target vintage

### 6.1 Identity and source evidence

The append-only artifact path is
`data/external/ssa_covered_earnings_calibration_targets_vintage2.json`.
Its `artifact_vintage_id` is the literal
`ssa_covered_earnings_calibration_targets.vintage2`; its schema is the
literal `ssa_covered_earnings_calibration_targets.v1`; and its
`artifact_role` is the literal `official_calibration_target_source_only`.
That role confers no fitting authority: only a separately frozen
`calibration_target_specs` cell may make an observation readable in a
declared phase.

The artifact has exactly these eleven top-level keys:

1. `schema_version`;
2. `artifact_vintage_id`;
3. `artifact_role`;
4. `year_basis`;
5. `required_calendar_years`;
6. `required_source_cell_ids`;
7. `covered_share_required_years`;
8. `source_document_manifest`;
9. `observations`;
10. `cross_table_discrepancies`; and
11. `integrity`.

The first three values are the literals above. `year_basis` is
`calendar_year`; `required_calendar_years` is the ordered JSON-integer array
1968 through 2022 inclusive. `required_source_cell_ids` is an object with
exactly `table4_b2`, `table4_b11`, and `ssa_covered_share`.
`table4_b2` is the year-major Cartesian-product array of literal IDs
`table4.b2/<year>/<component>` for years 1968..2022 and component order
`c5,c8,c11,c12,c13,c17`. `table4_b11` is the same expansion of
`table4.b11/<year>/<component>` over component order
`workers_total,workers_wage,workers_self_employment,
taxable_earnings_total,taxable_earnings_wage,
taxable_earnings_self_employment,contributions_total,
contributions_wage,contributions_self_employment`; and
`ssa_covered_share` is the ordered source-cell-ID array registered under V-B7,
one-to-one with `covered_share_required_years`.
`covered_share_required_years` is the exact ordered year array established by
V-B7 and the §6.2 minimum-coverage law before fitting.

`source_document_manifest` is an ordered nonempty array whose objects contain
exactly `source_document_id`, `publication`, `edition`, `table_ids`, `url`,
`retrieved_at_utc`, `committed_path`, `sha256`, `size_bytes`,
`capture_manifest_path`, and `capture_manifest_entry`. `observations` is
ordered by source-document order, `table_ids` order, ascending year, and
component order. The Supplement manifest entry is first and its `table_ids`
is exactly `["table4.b2","table4.b11"]`; the V-B7 covered-share source entry
follows. Every retrieval timestamp satisfies §10.3's UTC grammar.
Each object contains exactly `source_cell_id`, `source_document_id`,
`table_id`, `table_title`, `calendar_year`, `row_path`,
`nested_column_header_path`, `as_published`, `normalized_value`,
`published_unit`, `stored_unit`, `scale`, `status`,
`published_rounding_interval`, and `source_sha256`. Every normalized value is
a finite JSON number excluding booleans; for every 4.B2/4.B11 cell both it
and `scale` are JSON integers excluding booleans. Literal published text is
retained.
For 4.B2 and 4.B11, 1968–2020 status is `historical` and the snapshot's
footnote-e cells for 2021–2022 status are `preliminary`. Covered-share status
must be copied from its verified source, never inferred from date.
The observation array contains exactly \(6\times55\) 4.B2 cells,
\(9\times55\) 4.B11 cells, and one covered-share cell for every registered
covered-share year; no other cell is permitted.

Every manifest field except `table_ids` and `size_bytes` is a nonempty JSON
string; `table_ids` is an ordered nonempty unique string array; `size_bytes`
is a positive JSON integer excluding booleans; digests are 64 lowercase hex;
paths are traversal-free committed repo-relative files; the capture entry
must parse to the exact timestamp, digest, size, and basename in the same
object; and duplicate document IDs or table ownership fail. In an observation,
`calendar_year` is a JSON integer excluding booleans; `normalized_value` and
`scale` are finite numbers with positive scale; status is
`historical | preliminary`; every other scalar is a nonempty string except
`published_rounding_interval`. That object has exactly `status`, `lower`,
`upper`, `lower_closed`, `upper_closed`, `rule_source_document_id`, and
`rule_citation`. A `source_verified` object has finite numeric bounds with
lower no greater than upper, boolean closure flags, and nonempty source ID
and citation resolving to pinned bytes. A
`not_established_from_source_bytes` object has all six other values JSON
null. The displayed trailing zeroes or a table totals note never establish a
rounding quantum or mode. `source_document_id`, table, and source digest must
resolve to exactly one manifest entry. Source-cell IDs are unique,
exact-match `required_source_cell_ids`, and their year path equals
`calendar_year`.

`cross_table_discrepancies` is the exact ordered ten-object registry in the
committed-byte table below. Each object has exactly `calendar_year`,
`concept`, `table4_b2_source_cell_id`, `table4_b2_as_published`,
`table4_b11_source_cell_id`, `table4_b11_as_published`,
`discrepancy_class`, and `adjudication`. Its order is ascending year and then
concept. `discrepancy_class` is
`coarser_display_pattern_rounding_rule_unverified` or
`literal_source_conflict_not_display_precision`; `adjudication` is always
`preserve_both_use_registered_table_specific_selector_never_average`.
The builder compares all four overlapping primitive series—wage-worker
count, SE-worker count, wage taxable amount, and SE taxable amount—over all
shared 1951–2024 rows. Its exact unequal-cell set must equal this registry.
An eleventh, missing, changed, or newly equal pair aborts extraction; it is
never silently “reconciled.”

`integrity` contains exactly `canonicalization`, `content_sha256`,
`extraction_implementation_commit`, and `reproduced_from_source_bytes`.
`canonicalization` is the literal
`python-json-sort-keys-compact-ascii-no-nan-lf-v1`, denoting §10.1's exact
function;
`content_sha256` is SHA-256 of the canonical artifact after replacing that
field with 64 ASCII zeroes; the implementation commit is 40 lowercase hex;
and `reproduced_from_source_bytes` is JSON boolean `true`. Thus artifact
identity binds the literal ID, schema, all normalized and published cells,
extraction implementation, source manifest, cross-table discrepancy ledger,
and source-byte digests. Missing, extra, duplicate, reordered, wrong-status,
or wrong-year content is rejected positionally before any lookup is
constructed.

The committed Supplement snapshot already establishes:

- Table 4.B2's exact title and wage/SE headers at
  [lines 964–995](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L964);
- its 1968 component row at
  [lines 1254–1266](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1254)
  and 2014 boundary row at
  [lines 1944–1956](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1944);
- its component-count overlap and earnings definitions at
  [lines 2120–2129](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L2120),
  and its 2021–2022 preliminary markers and note at
  [lines 2049–2078](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L2049)
  and
  [line 2132](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L2132);
- Table 4.B11's exact title and component headers at
  [lines 14838–14861](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L14838);
- its 1968 row at
  [lines 15118–15127](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15118)
  and 2014 row at
  [lines 15670–15679](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15670);
  and
- its overlap, taxable-component, and contribution-accounting notes at
  [lines 15803–15822](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15803),
  and its 2021–2022 preliminary markers and note at
  [lines 15754–15777](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15754)
  and
  [line 15825](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15825).

The exact committed snapshot SHA-256 is
`c228920ea9d53b1e323e5933b6d9f926e3c9b609d868b549fabc40118554b449`.
Its byte size is `488165`, and its committed capture-manifest entry freezes
retrieval time `2026-07-27T13:02:54Z`, digest, size, and basename at
[capture-manifest line 4](../../data/external/snapshots/ssa_level_anchors_vintage1/capture_manifest.txt#L4).
Registration and reproduction must match all four fields; the repository path
without that identity is not evidence. Both tables identify their sources as
the SSA Master Earnings File 1-percent sample, BEA, and BLS at
[4.B2 line 2111](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L2111)
and
[4.B11 line 15804](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15804);
the registry preserves that provenance and never describes these cells as
census administrative totals.

The exact `cross_table_discrepancies` rows are:

| Year | Concept | 4.B2 literal | 4.B11 literal | Class |
|---:|---|---:|---:|---|
| 1968 | SE taxable amount | [27,340 (line 1263)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1263) | [27,300 (line 15124)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15124) | `coarser_display_pattern_rounding_rule_unverified` |
| 1969 | SE taxable amount | [27,540 (line 1278)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1278) | [27,500 (line 15136)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15136) | `coarser_display_pattern_rounding_rule_unverified` |
| 1970 | SE taxable amount | [26,920 (line 1293)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1293) | [26,900 (line 15148)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15148) | `coarser_display_pattern_rounding_rule_unverified` |
| 1971 | SE taxable amount | [27,410 (line 1308)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1308) | [27,400 (line 15160)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15160) | `coarser_display_pattern_rounding_rule_unverified` |
| 1972 | SE taxable amount | [32,060 (line 1323)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1323) | [32,100 (line 15172)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15172) | `coarser_display_pattern_rounding_rule_unverified` |
| 1974 | SE taxable amount | [42,360 (line 1353)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1353) | [42,400 (line 15196)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15196) | `coarser_display_pattern_rounding_rule_unverified` |
| 1975 | SE taxable amount | [43,560 (line 1368)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1368) | [43,600 (line 15208)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15208) | `coarser_display_pattern_rounding_rule_unverified` |
| 1977 | SE taxable amount | [52,950 (line 1398)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1398) | [53,000 (line 15232)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15232) | `coarser_display_pattern_rounding_rule_unverified` |
| 1985 | Wage-worker count | [113,100 (line 1510)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1510) | [113,400 (line 15324)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15324) | `literal_source_conflict_not_display_precision` |
| 1992 | SE taxable amount | [146,600 (line 1623)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1623) | [146,900 (line 15412)](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15412) | `literal_source_conflict_not_display_precision` |

The first eight pairs have a numerical pattern consistent with a coarser
4.B11 display, but no committed byte establishes a rounding rule; the last
two are not display-precision explanations. Each table is authoritative only
for the table-specific transformation registered below. No pair is averaged,
substituted, forced equal, or weighted as independent evidence.
Every 4.B2/4.B11 `published_rounding_interval.status` is therefore
`not_established_from_source_bytes` in vintage 2. The table note that totals
need not equal rounded components does not license the builder to infer a
quantum, mode, or interval.

Before target-spec ratification, primary source/data-dictionary bytes must
also establish the exact 4.B2 relationships between `c5` and `c11` and
between `c8` and `c12`, and the exact 4.B11 total/wage/SE worker-membership
relationships: treatment of zero, loss-only, below-threshold, wage-capped,
multiple-job, dual-type, and multiple-component cases. The target specs then
freeze those literal worker-membership rules and the joint analytic selectors
in §3.1. Neither “positive wage/SECA base” nor “any report” is assumed. If
the bytes do not settle every applicable case, the corresponding intensity
or worker-distribution family cannot be registered and the required
B2/B11/covered-share calibration contract fails closed; no alternative
denominator is chosen after values are seen.

The vintage-2 builder reuses the entry-10 ceremony: it reads only committed,
hash-verified source bytes; records exact publication, edition, table title,
row and nested column header paths, `as_published`, normalized value,
published/stored unit, scale, status, URL, retrieval timestamp, and source
SHA-256; emits canonical JSON offline; and has a reproduction test pinning
the canonical artifact hash. Network access is capture-time only. Missing,
extra, duplicate, reordered, ambiguous, preliminary-as-final, or drifting
source cells abort. No missing value is interpolated or synthesized.

The covered-share source is a separate required manifest entry. Registration
aborts unless primary-source bytes establish the exact publication, table,
vintage, numerator, denominator, annual timing, OASDI scope, worker/employment
unit, duplicate-worker treatment, population universe, and every included
year. An SSA annual-unique worker count may not be divided by a CPS/BLS
point-in-time or annual-average employment denominator. “About 94%” is never
a value, prior, or tolerance.

Vintage 2 is never refreshed in place. A changed official byte, corrected
cell, added year, changed source set, or changed normalization produces a new
artifact-vintage ID, a new literal append-only path, a new content hash, and
fresh registration; vintage 2 remains retained. A shape-compatible refresh
may keep the schema version, while any key/type/meaning change also requires
a new schema. No moving alias may appear in a registered configuration.

### 6.2 Frozen `calibration_target_specs`

Three source-identity registries are frozen before target specs.
`physical_source_cell_specs.v1` assigns each cell in the vintage-1 and
vintage-2 official artifacts exactly one physical identity containing:

`physical_cell_id`, `structural_locator_id`, `publication_family_id`, `edition_id`,
`source_document_id`, `table_id`, `row_path`,
`nested_column_header_path`, `calendar_year`, `as_published_token_sha256`,
`normalized_semantic_sha256`, and `full_source_sha256`.

The physical ID is the publication/edition/table/row/header/year/cell-token
identity, not a logical series or target ID. `full_source_sha256` proves the
production extraction but is evaluation provenance; it is excluded from the
cell-scoped substantive projection below. `structural_locator_id` is SHA-256
of the canonical publication-family/edition/document/table/row/header/year
tuple only; it excludes the cell token, normalized value, and source-content
hash and is stable when a G21 evaluation-only value is poisoned.

`official_source_alias_specs.v1` is the complete frozen registry of
cross-vintage physical aliases, republications, shared primitives, and
source-defined siblings. Each ordered row has exactly
`alias_group_id`, `left_physical_cell_id`, `right_physical_cell_id`,
`relation`, `effective_calendar_year`, `arithmetic_rule_id`, and
`adjudication`. `relation` is
`same_physical_cell | cross_vintage_republication | shared_primitive |
exact_arithmetic_sibling | structural_formula_sibling`;
`arithmetic_rule_id` is nonnull exactly for either sibling relation.
`adjudication` is the relation-matched value-blind literal
`identity_by_structural_locator | republication_by_registered_source_rule |
shared_primitive_by_registered_source_rule |
exact_arithmetic_sibling_by_registered_rule |
structural_formula_sibling_by_registered_definition`; it contains no quote,
value, token, content digest, or free text. The full proof bytes/digests
remain only in the physical/source and arithmetic registries retained in
evaluation provenance. Registered rules include the taxable-earnings/gross-
contribution rate relationship and every extracted total/component or
ratio/share sibling. The registry is built from both artifacts and all
extracted formula registries, never from declared target roles. An omitted
known relation, a cycle with inconsistent physical identity, or a
cross-vintage relation without exact source proof aborts registration.

`official_source_arithmetic_rule_specs.v1` is the complete ordered rule
registry. Every row has exactly `arithmetic_rule_id`,
`effective_calendar_year`, `relation_class`,
`ordered_operand_structural_locator_ids`,
`output_structural_locator_id`, `sibling_structural_locator_ids`,
`assertion_scope`, `numeric_validation_law`, `formula_ast`,
`source_definition_locator_id`, and
`source_definition_fragment_sha256`.
`relation_class` is `total_component | ratio_share |
taxable_earnings_gross_contribution | worker_membership`; locator arrays are
nonempty, unique, and foreign-key the physical registry. `assertion_scope` is
`exact_published_value_equality | structural_dependence_only`; its value is
derived from the pinned source definition before any displayed numeric value
is decoded and cannot be selected from the size or sign of a residual.
`numeric_validation_law` is respectively
`exact_rational_ast_equality |
not_applicable_no_published_numeric_assertion`.

An exact-equality row has a nonnull `formula_ast` using the closed rational
grammar `locator`, integer `rational`, and
`add | subtract | multiply | divide` nodes with fixed arity and no float,
path, callback, or implicit rounding. The validator evaluates it on the
literal normalized published values and requires exact rational equality.
A structural-dependence row has `formula_ast: null`. Its ordered
operand/output/sibling locators encode the directed definition graph and its
complete undirected evidentiary/exposure component, but assert no equality,
tolerance, residual range, or unobserved precision. The fragment hash binds
the exact published definition establishing either scope.
`source_definition_locator_id` is SHA-256 of the canonical immutable
publication-family/edition/document/table-or-section/citation-coordinate
tuple and excludes source content, the quoted definition, cell values, and
every full-source digest. Every nonnull arithmetic-rule reference in the
alias registry resolves exactly once, every rule is referenced, and
primitive/output/sibling closure is independently rederived. An extra,
omitted, cyclic, year-mismatched, topology-inconsistent, or source-definition-
inconsistent rule always aborts. Numeric inconsistency aborts only for
`exact_published_value_equality`; a structural-dependence row never performs
that comparison and reports the literal numeric-validation result
`not_applicable_no_published_numeric_assertion`.

In particular, a published total/component or taxable-earnings/contribution
definition is structural-only unless the primary source expressly guarantees
equality of the displayed values at their published precision. A complete
scan of the pinned
[Table 4.B11](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L14840)
rows for 1968–2022 finds zero taxable-earnings residuals: in 1969, for
example, `402,510 = 375,010 + 27,500` exactly. It finds contribution
total-minus-wage-minus-SE residuals of `+1` or `-1` only in 1969, 1971, 1986,
1993, 2001, 2010, 2019, and 2021. The 1969 contribution total `33,233` and
displayed components `31,501 + 1,733 = 33,234` therefore occupy one structural
dependency and exposure component. Its `-1` display residual is retained, but
it is neither a registration inconsistency nor evidence from which an
unreported rounding interval may be inferred.

The independently derived
`physical_source_structure_projection.v1` contains exactly
`schema_version`, `structural_cells`, `structural_alias_relations`, and
`arithmetic_rules`. A projected arithmetic-rule row has exactly
`arithmetic_rule_id`, `effective_calendar_year`, `relation_class`,
`ordered_operand_structural_locator_ids`, `output_structural_locator_id`,
`sibling_structural_locator_ids`, `assertion_scope`,
`numeric_validation_law`, `formula_ast`, and
`source_definition_locator_id`; it deliberately excludes
`source_definition_fragment_sha256`. A structural cell has exactly
`structural_locator_id`, the seven locator fields above, and
`verified_calendar_year`; a structural alias row replaces each physical-cell
endpoint by its validated structural locator and retains exactly relation,
effective year, arithmetic-rule ID, and adjudication. This projection
preserves locator, year, ancestry, alias, assertion scope, and exact-or-
structural dependence closure while excluding `physical_cell_id`,
published/normalized tokens, full-source digests, and observed values. Full
changing registries remain mandatory in evaluation provenance; only this
value-blind structural projection may enter G15/G17 or another non-G21 gate
evidence preimage used by G21.

The target registry schema is `calibration_target_specs.v2`. It is a literal
ordered array expanded cell by cell before fitting. Table 4.B2 and 4.B11
expand exactly over calendar years 1968–2022 in ascending order. The
covered-share objects expand over the exact year array frozen when V-B7 is
resolved. That array must contain at least one **direct-questionnaire**
positive-weight train cell in each reference-era interval `1968–1974`,
`1975–1977`, `1978–1992`, `1993–2001`, and `2002–2008`, plus every available
2009–2014 official cell with its exact model-year source class. A gap or
boundary cell cannot satisfy a direct-support minimum. The array is frozen
before fitting and may not be thinned after values are exposed.

Every target object contains exactly:

`target_id`, `target_family`, `target_year`, `verified_calendar_year`,
`role_rule_id`, `dependency_group`,
`source_artifact_vintage_id`, `source_cell_ids`,
`resolved_observation_ids`, `physical_source_cell_ids`,
`primitive_ancestry_ids`, `source_year`, `source_status`,
`model_year_source_class`, `universe`, `transformation`, `stored_unit`,
`published_rounding_interval`, `model_universe_id`, `model_weight_field`,
`model_weight_source_sha256`, `universe_concordance`, `declared_role`,
`effective_role`, `loss`, `loss_weight`, `cell_tolerance`,
`family_tolerance`, `selection_eligible`, and `candidate_output_selector`.

`target_id` is the unique string `<target_family>:<four-digit-year>`;
`target_family` and `target_year` are parsed from that exact ASCII grammar,
and `verified_calendar_year` must equal the parsed integer. Source cell,
observation, physical-cell, and ancestry IDs are ordered nonempty unique
arrays. `source_year` is a JSON integer excluding booleans; source status is
`historical | preliminary`; both roles are
`train | validation | held_out_diagnostic`; loss is
`squared_log_ratio | squared_logit_error | no_fitting_loss`; loss weight is a
finite nonnegative JSON number; and selection eligibility is a JSON boolean.

Registration resolves every logical source cell to one observation and then
to its complete physical primitive ancestry. It parses the encoded year from
the target ID, every logical cell ID, every transformation operand ID, every
resolved observation, every physical identity, and every primitive-ancestry
member. All parsed years must equal `target_year`, `source_year`, and the
candidate-output selector's calendar year. There is no tolerated alias,
carry, nearest-year lookup, or target-family exception.

`effective_role` is recomputed from that verified year:

```text
1968..2008 -> train
2009..2014 -> validation
2015..2022 -> held_out_diagnostic
```

Every target's `role_rule_id` is the literal
`verified_calendar_year_1968_2008_train_2009_2014_validation_2015_2022_heldout_v1`.
The `verified_role_specs` object used below has exactly `schema_version`,
`role_rule_id`, `year_basis`, `ordered_ranges`, `role_order`,
`derivation`, and `failure_disposition`. Its schema is
`verified_role_specs.v1`; the rule ID is the literal above; year basis is
`verified_calendar_year`; ordered ranges are the three inclusive integer
ranges and roles in the displayed order; role order is
`["train","validation","held_out_diagnostic"]`; derivation is
`recompute_never_trust_declared_role`; and failure disposition is `abort`.

`declared_role` must equal it byte-for-byte. The validator then takes the
transitive closure through `official_source_alias_specs.v1`. Every physical
alias, shared primitive, exact arithmetic sibling, and structural-formula
sibling receives the same honest exposure classification for that year, even
when its own target has
`no_fitting_loss` and zero weight. A model-choice closure containing a
post-2014 physical cell, a different-year operand, or a vintage-1 held-out
alias aborts registration. Either sibling class may publish a zero-weight
diagnostic but can never count as independent validation.

Every train or validation target must have source status `historical`;
`preliminary` is permitted only for `held_out_diagnostic`. A status, year,
role, ancestry, or alias mismatch aborts target-spec registration rather than
silently dropping or relabeling the cell.

`universe` has exactly `publication_scope`, `geography`, `population`,
`time_basis`, `worker_unit`, `duplicate_worker_rule`, and `zero_earner_rule`,
all source-derived strings. `transformation` has exactly `operation`,
`operand_cell_ids`, `formula`, and `domain`; operands exact-match source
cells and the other values are registered strings. `published_rounding_interval`
has the exact tagged schema and source-verification law in §6.1; a derived
target interval is `source_verified` only when interval arithmetic from
verified operand rules determines it, and otherwise is
`not_established_from_source_bytes`.
A `structural_dependence_only` sibling can never establish such an interval:
its rounding tag and every derived precision claim are
`not_established_from_source_bytes`/`rounding_interval_unavailable`, with no
inference from the displayed residual.
`universe_concordance` has exactly `official_ratio_universe`,
`model_analogue_universe`, `element_mappings`, `frame_relation`,
`verification_status`, and `source_sha256`. Each ordered mapping has exactly
`official_element`, `model_rule`, and `status`, with status
`exact_concept_match | registered_frame_difference`. `frame_relation` is the
literal `frame_relative_not_population_aligned`; `verification_status` is
`pass`; and the digest is 64 lowercase hex.
`candidate_output_selector` has exactly `calendar_year`,
`year_source_class`, `availability`, `field_ids`, `aggregation`,
`joint_probability_rule`, `cap_stage`, `projection_draw_reduction`, and
`unit`. The year and source class exact-match the verified target and §4.2.
`availability` is `available` for direct, boundary, and projected annual
views and
`not_applicable_no_claim_independent_model_analogue` for structural or
claim-specific benefit gaps. The latter has empty field IDs, no predicted
value or loss, zero weight, and no selection eligibility. It is an
exposure-honest official diagnostic only; it cannot materialize a consumer
row. The draw reduction is the literal §5.4 law.

Both tolerance fields are tagged objects, never bare null. A selection-gate
cell has exactly `applicability: selection_gate`, `metric`, and finite
`maximum`; any nongating cell has exactly
`{"applicability":"not_selection_gate"}`. Validation intensity values are
`absolute_log_error`/`0.09531017980432493` at cell level and
`rms_absolute_log_error`/`0.04879016416943205` at family level. Type-mix
values are `absolute_share_error`/`0.03` and
`rms_absolute_share_error`/`0.015`; covered-share values are the same metric
names with `0.02` and `0.01`. `selection_eligible` is true exactly for
available validation cells in the five selection-eligible families below
whose source class is `direct_questionnaire` or `boundary_2014`; it is false
for 2009, 2011, and 2013 gap cells. Positive train weights exist only for
available `direct_questionnaire` cells. Every gap, held-out, or
`no_fitting_loss` cell has weight zero.

`model_universe_id` resolves through a frozen selector containing exact age,
annual-presence, employee/SE/both-type, unique-worker, duplicate-worker,
zero-earner, and denominator rules. `model_weight_field` and its input hash
are literal. `universe_concordance` maps every official scope element to the
model selector. It must exact-match numerator and denominator universes
within the official ratio and freeze the model's conceptual analogue, but it
must mark the closed PSID roster/weights versus official national population
as `registered_frame_difference`. It never claims population equality. If
the closed model input cannot construct the registered conceptual
denominator, target registration aborts; the preserved frame difference is
why the certified label says
`aggregate-concept-calibrated-not-population-aligned`.

Roles are exactly `train`, `validation`, or `held_out_diagnostic`.
For projection draw \(d\), year \(y\), and registered person \(i\), every
model formula below forms its weighted numerator and denominator within
\((d,y)\), divides there, and then takes the arithmetic mean over
\(d=0,\ldots,19\) as required by §5.4. `sum` below means stable-key exact
rational summation of `model_weight_field * field`; a denominator must be
strictly positive in every draw. The B11 symbols \(T,W,S\) mean the literal
published total, wage, and SE worker cells. Their exclusive shares are
published-cell-implied transforms, not claims about unrounded latent counts:
\((T-S)/T\) wage-only, \((T-W)/T\) SE-only, and \((W+S-T)/T\) dual-type.
The extractor requires all three implied numerators to be nonnegative and
their exact rational shares to sum to one.

The target families are frozen as follows:

| Target family | Exact official transformation and model selector | Loss | Role and selection law |
|---|---|---|---|
| `b2_wage_total_intensity` | 4.B2 `c5/c11`; model `sum(covered_employee_wages_uncapped) / sum(b2_wage_worker_membership_probability_analytic)` | squared log ratio on model-choice cells | Role is recomputed by verified year; positive-weight direct train cells fit; available direct/boundary validation cells select; gaps are zero-weight unavailable diagnostics; 2015–2022 held out. |
| `b2_se_total_intensity` | 4.B2 `c8/c12`; model `sum(covered_se_net_earnings_pre_seca) / sum(b2_se_worker_membership_probability_analytic)`, where the numerator is the expected signed within-`se_aggregation_group_id` net concept before SECA factor, threshold, or cap | squared log ratio on model-choice cells | Same. |
| `b11_se_only_worker_share` | 4.B11 `(T-W)/T`; model `sum(b11_se_only_worker_probability_analytic) / sum(b11_any_worker_probability_analytic)` | squared logit error on model-choice cells | Same. |
| `b11_dual_type_worker_share` | 4.B11 `(W+S-T)/T`; model `sum(b11_dual_type_worker_probability_analytic) / sum(b11_any_worker_probability_analytic)` | squared logit error on model-choice cells | Same. |
| `ssa_precisely_universed_covered_share` | exact registered numerator/denominator; model `sum(modeled_covered_worker_probability_analytic) / sum(registered_covered_share_denominator_indicator)` under the exact registered timing and duplicate-worker rules | squared logit error on model-choice cells | Same for every available verified year; source-class minimums above apply. |
| `b11_wage_only_worker_share` | 4.B11 `(T-S)/T`; model `sum(b11_wage_only_worker_probability_analytic) / sum(b11_any_worker_probability_analytic)` | no fitting loss | Recomputed year role; zero-weight and selection-ineligible because algebraically dependent. |
| `b2_type_count_mix` | 4.B2 `c12/(c11+c12)` and the analogous model marginal-count ratio | no fitting loss | Recomputed year role; zero-weight and selection-ineligible; overlapping marginal counts are never unique workers. |
| `b2_se_total_component_share` | 4.B2 `c8/(c5+c8)` and the algebraically identical model component ratio | no fitting loss | Recomputed year role; zero-weight dependency check only. |
| `b2_wage_taxable_intensity` | 4.B2 `c13/c11`; model consolidated taxable wage intensity | no fitting loss | Recomputed year role; zero-weight preserved employer-cap mismatch. |
| `b2_se_taxable_intensity` | 4.B2 `c17/c12`; model consolidated taxable SE intensity | no fitting loss | Recomputed year role; zero-weight. |
| `b2_wage_taxable_fraction` | 4.B2 `c13/c5`; model taxable/uncapped wage ratio | no fitting loss | Recomputed year role; zero-weight preserved employer-cap mismatch. |
| `b2_se_taxable_fraction` | 4.B2 `c17/c8`; model taxable/uncapped SE ratio | no fitting loss | Recomputed year role; zero-weight. |
| `b11_taxable_earnings_component_reconciliation` | Literal displayed 4.B11 taxable-earnings total minus displayed wage and SE taxable components; the source relationship is `structural_dependence_only`, so the literal residual is retained with `rounding_interval_unavailable` and no equality/interval adjudication. The complete pinned 1968–2022 scan has zero such residuals. Model diagnostic is `sum(oasdi_person_taxable_payroll) - sum(oasdi_taxable_wages_person) - sum(oasdi_taxable_se_person)`. | no fitting loss | Recomputed year role; zero-weight structural-formula-sibling diagnostic, never independent evidence. |
| `b11_contributions_component_reconciliation` | Literal displayed 4.B11 contribution total minus displayed wage and SE contribution components, retained under the same structural-only/no-rounding-inference law. The complete pinned 1968–2022 scan has `+1` or `-1` residuals only in 1969, 1971, 1986, 1993, 2001, 2010, 2019, and 2021, including 1969's `-1`. Model diagnostic is `sum(oasdi_taxable_wages_person * registered_wage_oasdi_combined_rate + oasdi_taxable_se_person * registered_se_oasdi_rate) - sum(oasdi_taxable_wages_person * registered_wage_oasdi_combined_rate) - sum(oasdi_taxable_se_person * registered_se_oasdi_rate)`; worker total is never summed because component worker counts overlap. | no fitting loss | Recomputed year role; zero-weight structural-formula-sibling diagnostic, never independent evidence. |
| `b11_se_contribution_share` | 4.B11 SE OASDI contributions/(wage+SE OASDI contributions); model `sum(oasdi_taxable_se_person * registered_se_oasdi_rate) / sum(oasdi_taxable_wages_person * registered_wage_oasdi_combined_rate + oasdi_taxable_se_person * registered_se_oasdi_rate)` | no fitting loss | Recomputed year role; zero-weight legal/accounting sibling diagnostic only. |

`dependency_group` is operational and makes no statistical-independence
claim. The two B2 fitting families share
`dependency_group: b2_component_system`, whose objective weight is 0.50 and
whose family subweights are each one half. The two B11 worker-distribution
families share `dependency_group: b11_worker_type_system`, whose objective
weight is 0.25 and whose subweights are each one half. The covered-share
family has one of the two covered-share dependency-group IDs below and weight
0.25. Thus the effective family weights are 0.25, 0.25, 0.125, 0.125, and
0.25 in the selection-eligible table order; positive-weight direct cells
within a family have equal weight after gap cells are excluded by the frozen
source-class rule.

Before target registration, the physical source-ancestry audit above expands
every numerator and denominator to literal physical primitive cells and its
complete evidentiary dependency closure. It must prove that
the covered-share target is not an arithmetic transform or republication of
any selection-eligible B2 or B11 target. Exact target duplication aborts
registration. Shared primitive cells, cross-table discrepancies,
administrative source systems, or sampling frames are recorded rather than
treated as independence; the covered-share dependency-group ID is
`covered_share_system_disjoint_source` or
`covered_share_system_shared_source` according to that pre-fit audit, with
the same frozen 0.25 weight in either branch. No post-exposure reweighting
exists. Every other family receives zero fitting and selection
weight and may only test an arithmetic, reconciliation, legal-rate, or
preserved-mismatch disclosure. Positive
intensity validation requires both RMS absolute log error no greater than
`log(1.05)` and every-cell absolute log error no greater than `log(1.10)`.
B11 worker-type validation requires RMS absolute share error no greater than
0.015 and every-cell absolute share error no greater than 0.03. Covered-share
validation requires RMS absolute share error no greater than 0.01 and every
cell no greater than 0.02. These are precommitted operational acceptance
thresholds, not sampling confidence intervals.

Role is a verified-year consequence, while the target-use trace publishes
`verified_calendar_year`, direct physical ancestry, alias group IDs, sibling
group IDs with assertion scopes, and effective evidentiary role. Every required
4.B2 primitive is
referenced by at least one B2 family; every required 4.B11 worker primitive
is referenced by the worker-distribution families, every taxable primitive by
its reconciliation, and every contribution primitive by its reconciliation
or contribution-share family. A zero-weight transform sharing a primitive
with model choice is marked train/validation in 1968–2014 even though it
cannot enter loss or selection; it is never presented as held-out evidence in
those years. Its 2015–2022 expansion is held out. The B11
taxable/contribution diagnostics receive their verified train/validation role
before 2015 even though their loss weight is zero; their structural-dependence closure
prevents an independent-evidence claim. No physical or logical source cell
can acquire a second, more favorable evidentiary description.

For positive \(m,o\), squared log-ratio loss is
\((\log m-\log o)^2\); a nonpositive operand in train/validation fails that
candidate cell only when the target has a fitting loss.
For \(m,o\) strictly between zero and one, squared logit error is
\((\operatorname{logit}m-\operatorname{logit}o)^2\); a train/validation
endpoint or out-of-domain value fails that candidate cell only when the target
has a fitting loss. A held-out domain violation instead publishes finite
observed/predicted values, null loss, status `domain_fail_diagnostic`, and
exact reason `nonpositive_log_operand | logit_endpoint`; it cannot change
eligibility.
A `no_fitting_loss` domain violation in any role follows that same diagnostic
branch and cannot fail or rescue a candidate.
An unavailable structural-gap target publishes its official observation,
`predicted: null`, `loss: null`, and
`status: no_claim_independent_model_analogue`; it is excluded from RMS
cardinality by the registry rather than dropped at runtime. Zero-weight and
held-out discrepancies use the field name `diagnostic_error`, never `loss`,
so the model-choice loss registry has no evaluation-only bytes.
RMS is the square root of the equal-weighted
arithmetic mean of the registered cell errors, never a ratio of aggregate
means. B11 exact or structural siblings and dependent B2 transformations cannot rescue
or reject a candidate. A source extraction/schema inconsistency is a
preparation incident; a model legal-rate or reconciliation defect is
adjudicated independently by G04, G06, or G07, not by a held-out residual.
The vintage-2 artifact does not extract 4.B2's published average and
percentage siblings (`c14,c15,c16,c18,c19,c20`). Registered diagnostics
derive only from the six pinned primitives and make no independent-agreement
claim about the unextracted display siblings.

“Stored value” means the full-precision deterministic transformation of the
literal published cells, not recovery of unpublished precision. A diagnostic
may say a residual is distinguishable from published rounding only when every
operand has a `source_verified` rounding rule and interval propagation proves
it. Otherwise it publishes `rounding_interval_unavailable` and makes no
precision claim. A `structural_dependence_only` sibling is always in that
otherwise branch: neither its relation nor the magnitude of its literal
display residual authorizes rounding-interval inference.

The expansion order is target-family order above, then ascending year. Source
cell IDs are the literal table/row/header-path identities; model selectors are
the literal formulas above with their exact support-universe selector supplied
by the registered input manifest. Object key insertion order is irrelevant;
arrays have the semantic order just declared and canonical JSON sorts object
keys. Changing a cell, source, year, role, dependency group, formula, loss, weight,
tolerance, selector, target order, or selection eligibility creates a new
registry version and requires fresh registration. Exact deep equality,
including array order, is mandatory.

The substantive official-evidence identity is
`fit_selection_cell_identity.v1`, with exactly:

`schema_version`, `verified_role_specs`, `model_choice_targets`,
`model_choice_physical_cells`, `model_choice_alias_closure`,
`model_weight_identity`, `source_definition_fragments`, and
`canonicalization`.

It contains only positive-weight direct train cells and
selection-eligible direct/boundary validation cells. Each target row retains
its verified year, derived role, dependency group, loss/weight/tolerances,
candidate selector, ordered physical operands, and canonical observed value.
Each physical row retains its stable locator, exact published token,
normalized value, and hashes of only the cell-scoped source fragments needed
to establish that cell and its meaning.
`verified_role_specs` is the exact object above.
`model_choice_alias_closure` is the complete ordered transitive closure
projected to rows with exactly `left_structural_locator_id`,
`right_structural_locator_id`, `relation`, `effective_calendar_year`,
`arithmetic_rule_id`, `assertion_scope`, `numeric_validation_law`,
`arithmetic_rule_projection_sha256`,
`source_definition_locator_id`, and `adjudication`.
`arithmetic_rule_projection_sha256` is the SHA-256 of the exact matching
row in `physical_source_structure_projection.v1.arithmetic_rules`. This hash,
`assertion_scope`, `numeric_validation_law`, and
`source_definition_locator_id` are nonnull exactly when
`arithmetic_rule_id` is nonnull; all four otherwise are JSON null. When
nonnull, all four values exact-match the projected rule. The
closure never contains a value-bearing physical-cell ID, cell token,
normalized value, source-definition fragment digest, or full-source digest.
`source_definition_fragments` contains only the cell-scoped bytes needed to
interpret a model-choice operand itself; a held-out/zero-weight-only
definition fragment is represented in the alias closure solely by its stable
definition locator and value-blind arithmetic-rule projection hash and
remains evaluation provenance.

This identity expressly excludes full source-document SHA/size/capture
entries, artifact-wide content hashes, whole-document `source_sha256` fields,
held-out and zero-weight values and value-bearing spec payloads, vintage-1
bytes, registration, invocation, incident, configuration, and any digest
whose byte domain includes non-model-choice cells. The only retained
held-out/zero-weight structure is the value-blind
locator/relation/assertion-scope/dependence
closure expressly required above.

`substantive_production_input_specs.v1` has exactly `schema_version`,
`included_roles`, `excluded_evaluation_only_roles`, `included_input_ids`,
`excluded_input_ids`, `scoped_fragment_specs`,
`static_dependency_registry_sha256`, `closure_law`, and
`failure_disposition`. Before any value is opened, its inclusion set is
the complete static closure of candidate feature, model-weight, legal-rule,
source-inventory, crosswalk, and train/selection cell-fragment dependencies.
Its exclusion set is the exact manifest complement whose frozen roles are
full target artifact/source document, held-out/zero-weight-only fragment,
vintage-1, projection/evaluation-only, context, or output. Both ordered ID
arrays exact-partition the full allowed input domain: the production-manifest
array plus the four dedicated legal, inventory, crosswalk, and target
authority IDs in §10.1. The legal/inventory/crosswalk IDs are included with
their exact model-affecting scopes; the full target authority is excluded
because `fit_selection_cell_identity.v1` separately binds its model-choice
cells/fragments. The arrays must exact-match the static dependency registry;
runtime “actually opened” behavior cannot add, omit, or relabel an input.
`scoped_fragment_specs` gives every included input exactly one
`whole_input` scope only when every byte is in the static closure; otherwise
it freezes an exhaustive ordered row/field/cell projection and canonical
scoped hash. Thus an excluded post-boundary field sharing a physical PSID
file cannot reseed the model through that file's whole-byte digest.

The hash preimage is the independently reconstructed
`static_substantive_dependency_registry.v1`, with exactly `schema_version`,
`input_nodes`, `dependency_edges`, `scope_rows`, `canonical_order`, and
`closure_law`. `input_nodes` has one row per allowed input-domain ID in
manifest order, each with exactly `input_id`, `role`,
`inclusion_disposition`, and `scope_kind`; disposition is
`included_substantive | excluded_evaluation_only`, and scope kind is
`whole_input | structural_projection | excluded`. `dependency_edges` is the
complete ordered static graph and each row has exactly
`consumer_registry_id`, `consumer_member_id`, `dependency_kind`, `input_id`,
and `scope_id`. `scope_rows` has exactly `scope_id`, `input_id`,
`selector_kind`, and `ordered_structural_member_ids`; selectors are closed
registered row/field/cell projections and structural member IDs contain no
path, value, token, source-content hash, whole-manifest hash, or
evaluation-only digest. The canonical order is input order, then consumer/
member/dependency/input/scope order, then scope ID. Its `closure_law` and the
outer spec's `closure_law` are both the literal
`complete_static_transitive_model_choice_dependency_closure_v1`; outer
`failure_disposition` is literal `abort_registration`.
`static_dependency_registry_sha256` is independently recomputed from these
canonical value-blind bytes and cannot be supplied as an opaque manifest
digest. Nodes, edges, and scopes exact-rederive the included/excluded arrays
and every `scoped_fragment_specs` selector before any scoped content hash is
computed.

`substantive_model_sha256` binds the cell identity and that static input
identity. Complete evaluation provenance remains mandatory in
`full_calibration_evaluation_provenance.v1`, which has exactly
`schema_version`, `calibration_target_artifact_identity`,
`official_source_manifest`, `calibration_target_specs`,
`target_value_commitments`, `physical_source_cell_specs`,
`official_source_alias_specs`, `official_source_arithmetic_rule_specs`,
`psid_source_field_inventory_identity`,
`vintage_1_identity`, `evaluation_input_manifest`,
`configuration_sha256`, and `canonicalization`.
The artifact/inventory/vintage objects have exact path, schema, vintage,
size, and SHA-256 fields. The official and evaluation manifests are the
complete independently registered ordered manifests, not target-derived
subsets. `calibration_target_specs` and all three
physical-source/alias/arithmetic registries are complete deep copies.
`target_value_commitments` has exactly one row per expanded
target spec in identical order, with exactly `target_id`,
`verified_calendar_year`, `physical_source_cell_ids`,
`target_spec_sha256`, and `canonical_observed_value_sha256`; this binds every
value without releasing its decoded value on a no-eligible branch. Missing,
extra, reordered, duplicated, or self-subsetted provenance fails.
`canonicalization` is literal
`python-json-sort-keys-compact-ascii-no-nan-lf-v1`, denoting §10.1's exact
function.
The canonical object's hash is `evaluation_provenance_sha256` and enters
input validation, sidecar, primary integrity, and evaluation binding only.
Neither object nor hash can enter a parameter, loss, selection decision,
substantive model hash, or uniform. The sole gate use is the pair of
baseline/mutant hashes in G21's acyclic evidence to prove that full evaluation
provenance changed; only that boolean predicate, never either hash or object,
may affect eligibility condition 4.

`heldout_noninterference_specs.v1` is a nonempty frozen fixture registry.
Each fixture has exactly `fixture_id`, `baseline_inputs`,
`mutant_inputs`, `independently_mutable_value_keys`,
`shared_derived_diagnostic_poison_keys`,
`exclusive_source_fragment_keys`, and the three corresponding
`*_expected_count` fields. The coordinator independently derives and freezes
the three ordered key arrays and literal counts from the complete
model-choice physical closure, `calibration_target_specs.v2`, all three
physical-source/alias/arithmetic registries, the full official source
manifest, and the vintage-1 inventory.
Each count must equal its array length; the union is nonempty and exact, and
an omitted, extra, duplicate, overlapping, reordered, or count-mismatched key
fails registration.

`baseline_inputs` and `mutant_inputs` are complete ordered arrays with one
row per independently derived fixture input. Each row has exactly `input_id`,
`content_scope`, `fixture_path`, `sha256`, and `fixture_role`; paths are
fixture-only and structurally denied to production workers. Baseline and
mutant IDs/order/scopes/roles exact-match, their hashes differ exactly for
the frozen mutation classes, and every mutation key resolves to exactly one
changed input range. The coordinator derives the arrays and paths from the
complete registered key/fragment domain; configuration cannot supply a
smaller mirror.

The fixture applies two deliberately different mutation mechanisms:

1. every independently mutable primitive/value and every exclusively owned
   source fragment outside the model-choice closure—including held-out and
   vintage-1-exclusive material—is replaced by a distinct domain-valid
   literal or byte sequence in a structurally valid mutant source, and all
   affected document, artifact, manifest, and evaluation-provenance hashes
   are recomputed; and
2. a zero-weight derived diagnostic whose entire physical ancestry is shared
   with model-choice cells is not falsified inside the source artifact.
   Instead, after the trusted validator has proved the unchanged exact-or-
   structural sibling topology and assertion-scope closure, the diagnostic
   broker replaces that target's decoded
   post-validation payload/result value with a distinct domain-valid poison
   at the fit/selection isolation boundary.

The second class covers, among other registered members, derived B11
`(T-S)/T` and B2 type/component diagnostics that cannot be changed while
their shared primitives and formulas remain unchanged. Every non-model-choice
target is in exactly one value-mutation class, every exclusive fragment is in
the third class, and every class's frozen count is tested. Model-choice cells,
shared primitives, exact formulas, structural-dependence edges and scopes,
and shared interpretation fragments remain
byte-identical. Thus every held-out and zero-weight value is poisoned without
claiming that an arithmetically inconsistent official source is valid.
The fixture is branch-exhaustive. Baseline and mutant each rerun all three
fits and §7.2 selection even when the production selection result is
`no_eligible_candidate`; the production held-out handle remains sealed.
`noninterference_pre_g21_bundle.v2` has exactly `schema_version`,
`parameter_vectors`, `model_choice_predictions_and_losses`,
`candidate_dispositions`, `selection_result`, `selection_branch`,
`selected_model_projection`, and `hard_gate_rows_except_g11_g21`.
`selection_branch` is `selected_correction | no_eligible_candidate` and is
independently derived from the complete dispositions and selection result.
The selected projection is an exact tagged union:

- the selected branch has exactly `evaluation_status: evaluated`,
  `model_identity`, `substantive_model_sha256`,
  `keyed_uniform_registry_sha256`, `expected_ledger_streams`,
  `realized_ledger_streams`, `claim_context_gap_identity`, and
  `trusted_consumer_root_streams_sha256`; and
- the no-eligible branch has exactly
  `{"evaluation_status":"not_evaluated",
  "reason":"no_eligible_candidate"}`.

The hard-gate array contains G01–G10, G12–G20, and G22 in that exact order
with complete evidence hashes. G11 is structurally excluded because its
outer process-lifecycle seal occurs only after G21 is fixed; the coordinator
later attaches the same final G11 row to both substantive bundles. A
selected-model-dependent row that is unreachable on the
no-eligible branch retains the row with `status: not_evaluated`, null
observed value, and the hash of the canonical
`no_eligible_candidate` reason object. A parameter, prediction, loss,
disposition, or selection-branch change is never hidden behind that tag.
Equality of this complete baseline/mutant object is G21's evidence and
therefore has no self-reference.

After constructing the two pre-G21 bundles, the coordinator emits one shared
`g21_acyclic_noninterference_evidence.v1` object with exactly
`schema_version`, `fixture_id`, `baseline_pre_g21_bundle_sha256`,
`mutant_pre_g21_bundle_sha256`,
`baseline_selection_branch`, `mutant_selection_branch`,
`expected_independently_mutable_value_count`,
`actual_independently_mutable_value_count`,
`expected_shared_derived_diagnostic_poison_count`,
`actual_shared_derived_diagnostic_poison_count`,
`expected_exclusive_source_fragment_count`,
`actual_exclusive_source_fragment_count`,
`baseline_evaluation_provenance_sha256`,
`mutant_evaluation_provenance_sha256`, `pre_g21_bundles_equal`,
`mutation_domain_complete`, `evaluation_provenance_differs`, and `status`.
The two branch literals come from the respective bundles. The expected counts come from the fixture, actual counts come from the
coordinator-expanded mutation ledger, and all are nonnegative JSON integers.
The three booleans are respectively exact pre-bundle byte equality, equality
of all three expected/actual count pairs plus exact one-time coverage of
every frozen mutation key, and inequality of the two complete evaluation-
provenance hashes. A branch flip necessarily changes the two full bundle
hashes and makes `pre_g21_bundles_equal` false. `status` is `pass` iff all
three booleans are true; it is
`fail` otherwise. This object is G21's complete acyclic comparator preimage.
It contains no eligibility or full-substantive-bundle hash.

Each synthetic run then appends the identical G21 hard-gate row whose
evidence hash covers that object and whose status equals it. Only after G21
is fixed and the outer coordinator has sealed its branch-general RNG
lifecycle does each run receive the identical complete G11 row/seal and
derive
`correction_model_preconstruction_eligibility.v1`. That object has exactly
`condition_1`, `condition_2`, `condition_3`, `condition_4`, `condition_5`,
`condition_6`, and `eligible`. Conditions use
`pass | fail | not_evaluated`; `eligible` is true iff a selected correction
exists and all six conditions pass. Condition 4 uses this acyclic G21
status/count/provenance predicate on both branches, never
`noninterference_results.status`, either full evaluation-provenance hash, or
a full-bundle equality. On `no_eligible_candidate`, condition 1 is evaluated,
condition 4 is `pass | fail` from the complete branch-exhaustive mutation
battery, conditions 2, 3, 5, and 6 are `not_evaluated` because their complete
conjunctions require a selected ledger/model, and preconstruction eligibility
is false. This does not suppress G11: its complete no-eligible lifecycle row
and seal remain evaluated in the hard-gate array.

`noninterference_substantive_bundle.v1` has exactly `schema_version`,
`pre_g21_bundle`, `g21_row`, `complete_hard_gate_results`, and
`correction_model_preconstruction_eligibility`. The complete array has
exactly G01–G22, retaining the no-eligible not-evaluated rows.
Its hash is published in `noninterference_results` but does not feed G21's
own evidence or preconstruction-eligibility preimage, preserving acyclic
identity. On pass, the pre-G21 bundles, constructed G21 rows,
preconstruction-eligibility objects, and full substantive bundles are
byte-identical; only full evaluation provenance and changed diagnostic
observations/residuals may differ. Full-bundle equality is a required
post-preconstruction assertion and publication result, not an input to
preconstruction eligibility or final condition 7. If the acyclic G21
predicate passes but the post-preconstruction full bundles differ, the report
builder raises an
`invariant` incident before constructing a primary: that impossible
staged-derivation disagreement is not converted into an eligibility result.
If the acyclic G21 predicate fails, both unequal pre-bundle hashes and both
resulting full-bundle hashes are retained in the valid `gate_fail` primary;
full-bundle equality is not a schema precondition for that branch.
Parameters, model-choice predictions/losses, dispositions, the exact
selection branch, the branch-tagged selected-model projection, every
non-G21 gate row/evidence hash (including the identically attached outer G11
seal), G21, and preconstruction eligibility are all inside the post-G21
comparison. The outer seal itself is absent from G21's comparator preimage.
A whole-document digest in the substantive/RNG path,
or held-out coupling that changes a disposition into a false no-eligible
result, therefore produces a validly serialized G21 failure rather than
escaping the battery or invalidating the report schema.

Final condition 7 is deliberately absent from every object above. Only after
both complete output byte strings have been assembled does the trusted
finalizer construct `correction_model_eligibility.v2`, with exactly
`preconstruction`, `condition_7`, and `eligible`. `preconstruction` is the
exact already-frozen object. The candidate primary contains the literal
`condition_7: pass` and `eligible` equal to preconstruction eligibility. The
finalizer ignores those two asserted fields while it independently validates
every other primary/sidecar key, branch, canonical byte, sidecar binding,
result hash, and recomputed invariant; it then requires the asserted
condition-7 value and final eligible boolean to equal the independently
derived values, performs a final strict whole-object validation, and
immediately before rename rechecks the live RNG ledger/cache/wrapper seal
against the serialized comparand. Failure is an `invariant` incident and no
primary is renamed. Condition 7, final
eligibility, and either complete output byte hash never enter G21, either
pre-G21 bundle, or either substantive-bundle hash.

### 6.3 The 15 vintage-1 series

Fit none of the 15 vintage-1 series. They are not readable inputs to the
fitting/selection process:

| Vintage-1 series ID | V1 correction disposition |
|---|---|
| `retired_worker_awards` | Structurally not used in fitting; later context only. |
| `retired_worker_benefits_paid_estimated_allocation` | Structurally not used in fitting; later context only. |
| `oasi_benefits_paid_estimated_allocation` | Structurally not used in fitting; later context only. |
| `oasi_trust_fund_benefit_payments` | Structurally not used in fitting; later context only. |
| `oasdi_trust_fund_benefit_payments` | Structurally not used in fitting; later context only. |
| `retired_worker_december_current_payment_stock` | Structurally not used in fitting; later context only. |
| `oasi_december_current_payment_stock` | Structurally not used in fitting; later context only. |
| `oasdi_december_current_payment_stock` | Structurally not used in fitting; later context only. |
| `oasdi_workers_with_taxable_earnings` | Structurally not used in fitting; later worker diagnostic only. |
| `oasdi_reported_taxable_earnings` | Structurally not used in fitting; later payroll diagnostic only. |
| `oasdi_gross_contributions` | Structurally not used in fitting; arithmetic/accounting diagnostic only. |
| `oasdi_adjusted_taxable_payroll` | Structurally not used in fitting; later payroll diagnostic only. |
| `oasdi_covered_workers` | Structurally not used in fitting; later worker diagnostic only. |
| `oasi_net_payroll_tax_contributions` | Structurally not used in fitting and unscored; no model OASI/DI allocation. |
| `oasdi_net_payroll_tax_contributions` | Structurally not used in fitting; later cash-accounting diagnostic only. |

These cells have already been viewed and published. “Held out” means
structurally not used in fitting, parameter estimation, candidate selection,
threshold choice, seed choice, or rescue; it never means unseen. Truly unseen
temporal evidence requires later official cells whose registration predates
their exposure, or a genuinely isolated administrative link.

That seed-choice statement is executable, not semantic: vintage-1 bytes and
their whole-source digests are absent from
`fit_selection_cell_identity.v1` and `substantive_model_sha256`, and the
mutant fixture in §6.2 changes every vintage-1-exclusive byte while requiring
the model hash and all uniforms to remain identical.

The separately registered pre-2015 4.B11 worker primitives are not any of
the vintage-1 artifact's 2015–2022 observations. V1 consumes them only
through the scale-free worker-type shares in §6.2; no 4.B11 national worker
level enters the objective.

## 7. Fitting and candidate-selection law

### 7.1 Isolation and objective

Only verified-year, positive-weight, `direct_questionnaire` train cells with a
fitting loss estimate parameters. Only verified-year,
`selection_eligible` direct/boundary validation cells select among the frozen
candidates. The optimizer and selector receive canonical cell-scoped packets
from the trusted broker; a packet contains no artifact path, whole-document
digest, arbitrary lookup API, diagnostic handle, or source byte outside
`fit_selection_cell_identity.v1`.

Zero-weight, unavailable-gap, and held-out cells run in separate
noncommunicating diagnostic workers and cannot affect a parameter, optimizer,
convergence decision, candidate eligibility, order, threshold, uniform,
tie-break, gate, or publication decision. The optimizer/selector workers are
structurally unable to open vintage-1, anchor-report, target-artifact,
held-out, Option-C, benefit-total, or repository paths under G15's sandbox.
Knowing a forbidden pathname does not grant access.

All model-side targets are weight-scale invariant: shares, per-component
intensities, or distributions. Multiplying every PSID weight by a positive
constant must leave every fitted target and loss byte-identical. A hidden
intercept, offset, target weight, or post-fit factor that matches a national
worker or payroll total is a forbidden level fit.

The registered training objective is the §6.2 weighted mean: 0.50 on the two
B2 intensity families, 0.25 on the two nonredundant B11 worker-type shares,
and 0.25 on covered share, using the within-system subweights frozen there.
It is a predeclared loss weighting, not an independence claim. There is no
regularization term and no candidate-specific target deletion. Full-rank,
condition, and solution-agreement tests in §5.3 are candidate eligibility
conditions, not penalties.

The objective and selection registries are reconstructed from verified
physical ancestry and derived roles, not accepted from target-use traces. A
role, year, physical-cell, or alias-closure mismatch aborts before a value
packet is granted.

### 7.2 Exact selection sequence

Selection is the following lexicographic procedure:

1. run all frozen candidates and publish every success/failure disposition;
2. discard any candidate with nonconvergence, a §5.3 boundary/rank/
   condition/solution-certificate failure, a target-domain violation in a
   positive-weight fitting train cell or selection-eligible validation cell,
   missing output, or nonfinite parameter;
3. discard any candidate failing any validation cell or family tolerance in
   §6.2;
4. among eligible candidates, choose minimum validation loss under §6.2's
   registered dependency-group and within-family weights;
5. if losses differ by at most \(10^{-12}\), choose minimum training loss;
6. if still tied within \(10^{-12}\), choose the earliest complexity order in
   §5.3; and
7. if still tied, choose lexicographically smallest candidate ID.

`selection_spec.v1` has exactly `schema_version`, `candidate_order`,
`training_objective`, `eligibility_rules`, `primary_criterion`,
`tie_tolerance`, `tie_breakers`, and `no_eligible_status`.
Its schema literal is `selection_spec.v1`; candidate order is the §5.3 array;
the objective and eligibility rules are exact deep copies of §§5.3, 6.2,
7.1, and steps 1–3 above; the primary criterion is
`minimum_registered_dependency_weighted_validation_loss`; tie tolerance is
the finite number `1e-12`;
tie-breakers are exactly
`["minimum_training_loss","complexity_rank","candidate_id_lexicographic"]`;
and the no-eligible status is `no_eligible_candidate`.

If no candidate is eligible, the complete evaluation status is the exact
`no_eligible_candidate` failure branch in §10.2 and no production correction
or label certificate exists. This freezes the no-eligible selection branch
but does not terminate the ceremony: the coordinator must still execute the
complete §6.2 baseline/mutant fitting-and-selection battery, construct G21,
and derive conditions 1–6 with the held-out handle sealed. Human adjudication,
candidate/seed shopping, threshold relaxation, target removal, or choosing a
visually preferable held-out path is forbidden. A changed candidate or rule
requires a new design/registry version and fresh registration.

### 7.3 PSID-side validation

PSID cross-validation holds out complete people/households and complete
**direct questionnaire waves/reference eras**, never random person-wave rows.
Each held-out wave row publishes its verified reference year and source class.
Structural-gap, claim-specific-gap, boundary, and projected rows are not
questionnaire holdouts and cannot be counted toward direct-wave coverage.
The diagnostic evaluates parsing,
annualization, reconciliation, transition prediction, and observable
self-employment/sector fields. It is explicitly internal validation, not
administrative covered-earnings validation. Any literature quantity used as
a prior or fitting bound is training evidence and cannot reappear as
independent validation.

In v1 this block is diagnostic-only: no unspecified PSID-internal score can
select a candidate, set a threshold, rescue a candidate, or enter the label
certificate. Making it selection- or certificate-bearing requires a new
registered target family with exact labels, partitions, losses, and
tolerances before exposure.

### 7.4 Option C sensitivity

The only Option-C ID is `aggregate_share_scale_sensitivity_v1`, labeled
`aggregate-scaled-labor-income-proxy`. For each year through 2014 it multiplies
`max(proxy_labor_income_raw, 0)` by the most recent registered pre-2015
**direct-reference-year**
`ssa_precisely_universed_covered_share` cell in the same
`candidate_reference_era_specs.v1` era; years before that era's first direct
cell use its first direct cell. A structural gap, claim-specific gap, or 2014
boundary row retains its own source-class label and cannot masquerade as a
direct covered-share observation. The 2014 scalar is carried unchanged
through 2022. This deterministic, deliberately crude rule publishes aggregate
movement only. It cannot enter careers, AIME, PIA, production revenue,
candidate selection, tolerance adjudication, the label certificate, or a
held-out claim. It is emitted solely to show how the production Option-A+B
model differs from a minimal scalar benchmark.

For a direct, 2014-boundary, or projected position, the proxy operand is the
same-year frozen signed proxy input. For an emitted 1997–2013 claim-context
gap position, `option_c_diagnostic_proxy_gap_rule.v1` descriptor-reads the
same person and gap year from the frozen pre-correction projection's
odd-year proxy-carry stream, after the benefit cutoff has removed positions
after the operative claim year. The value is copied bit-for-bit and repeated
under each applicable career context; it is not averaged, corrected,
reclassified, or installed as an unconditional/common corrected-ledger row.
The coordinator independently expands that person×gap-year source domain
from the immutable projection. A missing, duplicate, wrong-year, or
wrong-person raw-proxy input produces a retained failing sensitivity row
with null numbers and
`reason_code: missing_option_c_diagnostic_proxy`, never a default. This
diagnostic-only raw read is authorized solely by the `before_context`
exception; no trusted corrected root may reference it.

Its annual result domain follows §8.2's
`annual_provenance_context_expansion`: each structural/claim-specific gap
position carries the operative-claim/career coordinates even when the
deterministic scalar value repeats, so no context-free 2013 sensitivity row
exists. Every row is serialized only in the separately tagged
`option_c_sensitivity` sub-block of `before_context_results`, with
`evidence_role: raw_proxy_sensitivity_before_context`. It is never a
corrected metric, trusted-evaluator root, or separate corrected-result block.

`sensitivity_specs.v1` is a one-object ordered array. Its object has exactly
`sensitivity_id`, `label`, `input_selector`, `scalar_selector`,
`reference_era_specs`, `year_source_class_rule`, `pre_2015_rule`,
`diagnostic_proxy_gap_rule`, `post_2014_rule`, `stratum_id`, `statistic`,
`aggregation_rule`, `allowed_outputs`, and `forbidden_uses`; every value is
the literal law in the preceding paragraphs.
`diagnostic_proxy_gap_rule` is the literal closed rule ID
`option_c_diagnostic_proxy_gap_rule.v1`.
The remaining result-domain literals are `stratum_id: overall`,
`statistic: survey_weighted_total_draw_summary`, and
`aggregation_rule:
within_projection_draw_exact_psid_survey_weighted_sum_then_20_draw_mean_sample_sd_v1`.
For each annual/context position, the coordinator exact-sums the scaled
nonnegative person values times their frozen PSID survey weights inside each
of the 20 projection draws, then applies the exact §5.4 mean/sample-SD law.
A successful row therefore has `observation_count: 20`. No unregistered
stratum, statistic, aggregation, correction draw, or row dimension exists.
`allowed_outputs` is exactly `["before_context_results"]`, and
`forbidden_uses` is exactly
`["careers","AIME","PIA","production_revenue","candidate_selection",
"tolerance_adjudication","label_certificate","held_out_claim"]`.

## 8. Normative gates and prohibited circularity

### 8.1 Hard correctness gates

`consumer_domain_derivation_specs.v1` has exactly
`schema_version`, `source_input_ids`, `benefit_stage_a_d_derivation`,
`revenue_unsplit_derivation`, `career_contexts`, `canonical_key_fields`,
`canonical_order`, `expected_domain_hashes`, and `failure_disposition`.
The benefit derivation independently reruns the complete frozen Stage A–D
partition from immutable production inputs: every Stage-A person, Stage-B
candidate, origin, C.5 birth disposition, opening-backfill replacement
operative claim coordinate, Stage-D predicate/disposition, career span,
registered sensitivity, and final benefit metric read is enumerated. Neither
a configured consumer selector nor ledger presence is an input. Low coverage
or missing support therefore cannot delete its own failing key.

The revenue derivation is every
`(projection_draw, stable_person_id, year)` row in the complete unsplit
projection slices for 2015–2022 before filtering a null, nonpositive,
benefit-ineligible, or otherwise difficult earnings row. A missing source
amount receives its registered unresolved disposition or fails support; it
never shrinks the domain. The configuration may bind expected hashes and
counts, but the sealed coordinator independently recomputes them by draw,
consumer, year, Stage disposition, operative-claim context, and career
variant.

`benefit_gap_derivation_specs.v1` has exactly `schema_version`, `gap_years`,
`career_context_key_fields`, `cutoff_order`, `neighbor_rule`,
`component_channels`, `rational_arithmetic`, `gap_year_statutory_rule`,
`rng_rule`, `provenance_by_gap_year`, `gap_row_schema_specs`, and
`failure_disposition`.
`gap_years` is exactly
`[1997,1999,2001,2003,2005,2007,2009,2011,2013]`.
`career_context_key_fields` has exactly `expected_stream_context_fields`,
`realized_stream_context_fields`, and `row_context_fields`. The expected
array is `["projection_draw_index","operative_claim_year",
"career_variant_id"]`; the realized array inserts
`correction_draw_index` after projection draw; and the row array is
`["stable_person_id","operative_claim_year","career_variant_id"]`.
Sources after the operative claim year are discarded before neighbor lookup.
If the gap is after the claim year, no row is emitted. Otherwise each
corrected, pre-statutory
covered-wage, covered-SE-gain, covered-SE-loss, noncovered, and unresolved
channel uses the exact rational mean when both adjacent years are admissible,
carries the only admissible neighbor when one exists, and receives the
registered `unknown` disposition when neither exists. The effective-gap-year
SECA factor/threshold and wage-first cap run in the trusted evaluator only
after that component vector is derived. They are not runner-supplied or
precomputed gap-source fields. Already capped totals are never averaged, and
gap derivation consumes no new uniform. Neighbor years/hashes, operative
claim year, draw, and exact source-class provenance publish.

`provenance_by_gap_year` is the exact ordered nine-row array. Each row has
exactly `gap_year` and `year_source_class`; rows are ordered by ascending
integer gap year, years 1997 through 2011 above have literal
`structural_gap_imputed`, and 2013 has literal
`claim_specific_boundary_gap`. No fallback literal or additional field
exists.
`gap_row_schema_specs` has exactly `schema_version`, `row_kind`,
`base_row_schema_sha256`, `key_fields`, `field_specs`,
`canonical_field_order`, `encodings`, `row_invariants`, and
`failure_disposition`. Its schema and row-kind literals are
`benefit_gap_row_schema_specs.v1` and `claim_context_gap_component`;
`base_row_schema_sha256` hashes the exact registered
`ledger_row_schema_specs.v1`; and `key_fields` is exactly
`["stable_person_id","gap_year","role","source_job_id",
"source_component_id","derived_component_id","operative_claim_year",
"career_variant_id"]`.

`field_specs` is closed rather than a copy of all atomic fields. It contains,
in exact order, those eight keys; `remuneration_type`,
`se_aggregation_group_rule_id`, `gap_se_aggregation_group_id`,
`year_source_class`, `channel_value_status`;
`covered_wage_gain_amount`, `covered_se_gain_amount`,
`covered_se_loss_magnitude`, `noncovered_gain_amount`,
`noncovered_se_loss_magnitude`, `unresolved_gain_amount`,
`unresolved_se_loss_magnitude`; then `left_neighbor_year`,
`right_neighbor_year`, `left_neighbor_row_sha256`,
`right_neighbor_row_sha256`, `gap_derivation_disposition`,
`effective_gap_legal_rule_id`, and `no_new_uniform`. A neighbor coordinate
and hash are nullable together exactly when no known admissible source
component exists on that side after the cutoff. Remuneration type and the
SE-aggregation rule ID must exact-match across two-neighbor rows and copy the
sole neighbor on a carry. Annual `se_aggregation_group_id` and
`coverage_state_group_id` are deliberately absent: both are person-year
identities and cannot be copied across adjacent years. For an SE component,
`gap_se_aggregation_group_id` is freshly derived by the registered
SE-aggregation rule from its same-service key fields with `gap_year`
substituted for year; for a non-SE component, both SE-group fields are null.
The gap stream consumes no new coverage uniform and needs no gap-year
coverage-state group. Source channel values are extracted only from the seven exact
§3.1 status-allocated gain/loss members with the corresponding names; no raw
proxy, adjudicated source, measurement intermediate/delta, probability,
status, reason, or already statutory/capped field is in this schema.

For `mean_both | carry_left | carry_right`,
`channel_value_status: known` and all seven channel values are nonnull
nonnegative rational microdollars produced by the stated exact channel-wise
mean/carry law. For `unknown`, `channel_value_status: unknown`, all seven are
null, both neighbors are null, and the row is retained as complete support;
any required consumer domain containing it fails G12/G22 with
`unknown_gap_component` before a numeric root can evaluate. It is never
filtered, zero-filled, or supplied by a runner. `year_source_class` is the
nonnull provenance-map literal, `effective_gap_legal_rule_id` is the exact
effective-year table foreign key, and `no_new_uniform` is literal boolean
`true`. Canonical order is exactly the field order above; encodings are the
applicable §3.1 rational/canonical encodings; row invariants are the
executable cutoff, provenance-map, neighbor, channel-extraction,
component-identity, gap-SE-group derivation, effective-year-law, and
no-new-uniform laws above; and
failure disposition is `gate_fail`.

`earnings_consumer_dependency_specs.v1` has exactly `schema_version`,
`complete_final_metric_inventory`, `allowed_corrected_ledger_fields`,
`allowed_non_earnings_operands`, `forbidden_direct_earnings_operands`,
`required_ledger_dominator`, `legacy_before_block_exceptions`,
`consumer_source_field_schema_specs`,
`consumer_literal_domain_specs`,
`consumer_evaluator_condition_reason_specs`,
`consumer_semantic_recipe_specs`, and `failure_disposition`. Its metric
inventory is independently reconstructed from the frozen Stage A–D benefit
surface, unsplit revenue surface, model-metric registry, every pairing, and
every comparison spec. Every
final metric or intermediate with any transitive earnings dependency must be
dominated by the hash-verified corrected-ledger accessor; this includes
benefit amounts, counts, insured-status, and claim outputs even when their
published unit is not earnings. Only a dependency-graph-proven
earnings-independent leaf may bypass that dominator. The atomic
`proxy_labor_income_raw` field remains hash-bound audit provenance, but no
corrected source-stream spec may select it. Raw proxy and legacy
first-estimates numbers are permitted as evaluable numeric operands only in
the typed `before_context` block and are forbidden as corrected operands.

`consumer_source_field_schema_specs` is the separately ratified
`consumer_source_field_schema_specs.v1` object with exactly `schema_version`,
`rows`, `canonical_order`, `derivation_law`, and `failure_disposition`.
Every row has exactly `source_schema_id`, `source_kind`,
`authority_input_id`, `authority_object_id`, `key_fields`, `value_field`,
`value_type`, `unit`, `nullable`, `enum_domain_id`,
`unavailable_reason_domain_id`, and `content_binding_derivation_id`. It covers
every and only admissible
corrected-ledger, claim-gap, earnings-independent primitive, and registered
legal-table source field. Ledger and gap rows are exact projections of their
independently frozen row schemas. Primitive and legal rows are independently
ratified field-level schemas in this registry rather than in the evaluator
DAG; their input/object/field tuple, type, unit, nullability, enum and
unavailable-reason domains, and content-binding derivation are all authority.
`source_schema_id` is
literal `consumer-field-schema:` plus SHA-256 of §10.1 canonical bytes of
the other eleven fields. Rows are ordered by source-kind order
`corrected_expected_ledger`, `corrected_realized_ledger`,
`claim_context_gap`, `correction_bound_earnings_independent_input`,
`registered_legal_rule`, then authority-input/object/key/field order.
`canonical_order` is that literal order, `derivation_law` is
`frozen-source-objects-to-field-schemas-v1`, and failure disposition is
`abort_registration`. A missing primitive/legal field schema or a
type-compatible field substitution is therefore unregistrable.

`consumer_literal_domain_specs` is the separately ratified
`consumer_literal_domain_specs.v1` object with exactly `schema_version`,
`rows`, `domain_order`, `canonical_order`, `derivation_law`, and
`failure_disposition`. Every row has exactly `domain_id`, `domain_class`,
`authority_registry_id`, `authority_member_id`, `ordered_literals`,
`literal_count`, and `ordered_literals_sha256`. `domain_class` is exactly
`value_enum | unavailable_reason`; both authority IDs are nonempty frozen
registry/member IDs; and `ordered_literals` is a nonempty array of unique JSON
strings in authority order. Its count is the positive JSON-integer array
length, excluding booleans, and its hash covers the complete canonical array.
`domain_id` is literal `consumer-literal-domain:` plus SHA-256 of §10.1
canonical bytes of
`[domain_class,authority_registry_id,authority_member_id,ordered_literals]`.
Consequently two authorities with identical literal arrays still have
distinct domain IDs and are never signature-compatible merely because their
members happen to match.

Coverage and order are exact. The coordinator scans, in order, every nonnull
source-field `enum_domain_id` and `unavailable_reason_domain_id`, every
recipe-step and recipe-root
`output_enum_domain_id`, and every recipe-root
`unavailable_reason_domain_id`; first reference to a distinct ID fixes its
position. `domain_order` is the exact ID projection of that scan, each
referenced ID has exactly one row of the required class, and no unused row is
permitted. `canonical_order` is
`first-authority-reference-then-ordered-literal`; `derivation_law` is
`closed-literal-domains-from-independent-source-and-recipe-authorities-v1`;
and failure disposition is `abort_registration`. A missing, extra, duplicate,
reordered, open-string, wrong-class, hash-only, or configured-evaluator-only
domain therefore cannot enter reconstruction.

`consumer_evaluator_condition_reason_specs` is the separately ratified
`consumer_evaluator_condition_reason_specs.v1` object with exactly
`schema_version`, `noncoordinate_conditions`, `source_condition_rows`,
`coordinate_condition_rows`, `entropy_precision_schedule_bits`,
`propagation_precedence`, `canonical_order`, `derivation_law`, and
`failure_disposition`. `noncoordinate_conditions` is exactly, in this order:

```json
[
  ["declared_value_type_or_unit_mismatch","abort_registration"],
  ["declared_record_domain_mismatch","abort_registration"],
  ["declared_output_enum_domain_mismatch","abort_registration"],
  ["enum_output_on_unauthorized_opcode","abort_registration"],
  ["unexpected_extra_coordinate","gate_fail"]
]
```

These conditions never manufacture an unavailable authority coordinate. An
unexpected extra coordinate is retained only in the owning stream's failing
count/hash evidence with reason `unexpected_extra_coordinate`; it is not
inserted into the independently derived output domain.

Each `source_condition_rows` member has exactly `condition_id`,
`authority_registry_id`, `authority_member_id`, `reason_domain_id`, and
`reason_code`. It is the complete first-authority-use expansion of every
source-origin unavailability condition reachable from a recipe; each row
foreign-keys the selected source field's `unavailable_reason` literal-domain
row and preserves that row's exact reason literal. `reason_domain_id` equals
that field's `unavailable_reason_domain_id`; `condition_id` is literal
`source-unavailable:` plus SHA-256 of §10.1 canonical bytes of
`[authority_registry_id,authority_member_id,reason_domain_id,reason_code]`;
and rows are ordered by first source-field use then ordered-reason position.
The gap-channel source condition is exactly
`unknown_gap_component -> unknown_gap_component`. No generic source
unavailability or open reason string exists.

Each `coordinate_condition_rows` member has exactly `condition_id`,
`applicable_ops`, and `reason_code`. `applicable_ops` is the exact nonempty
subsequence of the 17-op authority order; “all 17 opcodes” below means that
complete array. Its complete order and mapping are:

| `condition_id` | `applicable_ops` | Exact `reason_code` |
|---|---|---|
| `missing_required_coordinate` | all 17 opcodes | `missing_required_coordinate` |
| `duplicate_required_coordinate` | all 17 opcodes | `duplicate_required_coordinate` |
| `invalid_typed_value` | all 17 opcodes | `invalid_typed_value` |
| `enum_literal_out_of_domain` | `select`, `exact_lookup`, `same_key_choose` | `enum_literal_out_of_domain` |
| `lookup_key_missing` | `exact_lookup` | `lookup_key_missing` |
| `lookup_key_duplicate` | `exact_lookup` | `lookup_key_duplicate` |
| `nonpositive_ratio_denominator` | `same_key_ratio_positive` | `nonpositive_ratio_denominator` |
| `negative_quantile_weight` | `partition_weighted_quantile` | `negative_weight` |
| `nonpositive_quantile_total_weight` | `partition_weighted_quantile` | `nonpositive_total_weight` |
| `negative_top_share_value` | `partition_weighted_top_share` | `negative_value` |
| `negative_top_share_weight` | `partition_weighted_top_share` | `negative_weight` |
| `nonpositive_top_share_total_weight` | `partition_weighted_top_share` | `nonpositive_total_weight` |
| `nonpositive_weighted_value_denominator` | `partition_weighted_top_share` | `nonpositive_weighted_value_denominator` |
| `negative_entropy_probability` | `partition_weighted_mean_shannon_entropy` | `negative_probability` |
| `nonunit_entropy_probability_sum` | `partition_weighted_mean_shannon_entropy` | `nonunit_probability_sum` |
| `negative_entropy_weight` | `partition_weighted_mean_shannon_entropy` | `negative_weight` |
| `nonpositive_entropy_total_weight` | `partition_weighted_mean_shannon_entropy` | `nonpositive_total_weight` |
| `entropy_rounding_bin_unresolved` | `partition_weighted_mean_shannon_entropy` | `entropy_rounding_bin_unresolved` |
| `insufficient_draw_observations` | `draw_mean_sample_sd` | `insufficient_draw_observations` |
| `nonfinite_binary64_conversion` | `partition_weighted_mean_shannon_entropy`, `draw_mean_sample_sd` | `nonfinite_binary64_conversion` |

Repeated reason literals occur once in an unavailable-reason domain.
`entropy_precision_schedule_bits` is the nonempty increasing array of positive
JSON integers, excluding booleans, at which the coordinator retries the
directed-interval proof; it is frozen in this independent registry, not chosen
by an implementation. Exhausting its final precision without certifying one
round-to-nearest-even bin is exactly
`entropy_rounding_bin_unresolved`.
`propagation_precedence` is exactly
`["authority-and-stream-structure",
"first-required-unavailable-input",
"first-local-condition-in-coordinate-condition-order",
"result-conversion"]`. Canonical order is source-condition order followed by
the table order; derivation law is
`closed-source-and-opcode-condition-to-reason-authority-v1`; and failure
disposition is `abort_registration`.

`consumer_semantic_recipe_specs` is the separately ratified
`consumer_semantic_recipe_specs.v1` object with exactly `schema_version`,
`rows`, `metric_order`, `canonical_order`, `derivation_law`, and
`failure_disposition`. It is the semantic recipe authority that is distinct
from the configured evaluator. Its rows are in the independently
reconstructed complete-final-metric order and have exactly
`model_metric_id`, `metric_authority_registry_id`,
`metric_authority_position`, `semantic_recipe_id`, `source_roles`, `steps`,
`root_step_id`, `expected_domain_derivation_id`,
`unavailable_reason_domain_id`, `output_key_fields`, `output_value_type`,
`output_enum_domain_id`, `output_unit`, `draw_reduction_id`, and
`dependency_dominator_id`.
`source_roles` is a nonempty ordered array whose rows have exactly
`source_role_id`, `source_schema_id`, and `domain_derivation_id`; the schema
ID resolves exactly one field-schema row above and the domain ID resolves the
complete source relation required by that recipe. Each `steps` row has common keys
`recipe_step_id`, `op`, `output_domain_derivation_id`,
`output_key_fields`, `output_value_type`, `output_enum_domain_id`, and
`output_unit`, plus only the operation-specific keys in the 17-op table below
after replacing each
`*_node_id` with the corresponding `*_recipe_step_id`, each
`*_node_ids` array with an ordered `*_recipe_step_ids` array, and each source
stream ID with its exact `source_role_id`; any operation-specific
`output_domain_id` is represented only by the common
`output_domain_derivation_id`. A select step also retains the authority
`value_field`; an exact lookup retains the authority table field.
Every predecessor recipe step is earlier in the same row, `root_step_id`
equals the final step, and no cross-root recipe sharing exists.
`semantic_recipe_id` is literal `consumer-recipe:` plus SHA-256 of canonical
bytes of all other row fields except `metric_authority_position`.
`metric_order` exact-matches the complete metric inventory;
`canonical_order` is `metric-order-then-recipe-step-order`;
`derivation_law` is `frozen-metric-semantics-to-role-opcode-recipe-v1`; and
failure disposition is `abort_registration`. The recipe rows, not configured
graph nodes, state whether a metric uses wage or SE, p25 or p10, and every
other source, opcode, domain, rule, type, unit, and reduction choice.
Throughout this evaluator,
`output_domain_derivation_id`, operation-specific `output_domain_id`,
`authoritative_output_record_domain_id`, and `expected_domain_id` identify
record-key coordinate domains only. They never stand in for
`output_enum_domain_id`.

Dependency declaration is not numeric authority. The separately frozen
`trusted_consumer_evaluation_specs.v1` is the coordinator's only executable
consumer grammar, but its configured DAG is never semantic authority. Before
schema-validating or using configured `source_stream_specs`,
`unit_algebra_specs`, `graph_nodes`, or `metric_roots` beyond the bounded
strict JSON syntax parse, the coordinator constructs in memory
`trusted_consumer_semantic_authority.v1` with exactly
`schema_version`, `source_authority_schemas`, `domain_authority_schemas`,
`rule_authority_schemas`, `unit_algebra_specs`,
`root_authority_schemas`, `canonical_order`, `derivation_law`, and
`failure_disposition`.

The reconstruction inputs are only the independently frozen
`ledger_row_schema_specs.v1`, benefit-gap row schema,
`consumer_source_field_schema_specs.v1`,
`consumer_semantic_recipe_specs.v1`, complete final-metric inventory,
`evaluation_specs.v1`, `draw_spec.v1`, the remaining
`earnings_consumer_dependency_specs.v1` fields, the model-metric registry,
all pairing/comparison registries, and the separately frozen
`legal_rounding_rule_specs.v1`,
`consumer_literal_domain_specs.v1`, and
`consumer_evaluator_condition_reason_specs.v1`. The configured evaluator members named
above, their configured hashes, any configured semantic-authority hash, and
all runner bytes are structurally excluded from the reconstruction
function. `derivation_law` is the literal
`frozen-registries-to-exact-root-opcode-authority-v1`;
`schema_version` is `trusted_consumer_semantic_authority.v1`;
`canonical_order` is exactly
`["source_authority_schemas","domain_authority_schemas",
"rule_authority_schemas","unit_algebra_specs","root_authority_schemas"]`;
and `failure_disposition` is `abort_registration`. Configured evaluator data
are comparands only. A mismatch aborts registration before graph execution
or source-value access, and execution is instantiated from the reconstructed
authority object. Exact agreement never transfers authority to the configured
DAG.

Each `source_authority_schemas` row has exactly `source_stream_id`,
`source_kind`, `authority_input_id`, `authority_object_id`, `key_fields`,
`value_field_schemas`, `domain_derivation_id`, `content_binding_id`, and
`dependency_class`. Each nonempty `value_field_schemas` row has exactly
`value_field`, `value_type`, `unit`, `nullable`, `enum_domain_id`, and
`unavailable_reason_domain_id`.
`source_kind`, `authority_input_id`, `authority_object_id`, `key_fields`,
and every field identity are derived from the frozen authority inputs, not
from a graph. The coordinator groups the exact
`consumer_source_field_schema_specs.v1` rows required by each semantic
recipe only when their source kind, authority input/object, key fields, and
content-binding derivation are identical. Ledger signatures also
exact-match `ledger_row_schema_specs.v1`; the four flattened status members
are independently fixed as rational/`probability`; and gap signatures also
exact-match the gap-row schema. Primitive and legal signatures come only
from their separately ratified field-schema rows. `nullable` is a JSON
boolean. `enum_domain_id` is null unless the value type is enum and
otherwise foreign-keys that field's exact closed enum registry.
`unavailable_reason_domain_id` is null exactly when the authoritative field
stream can never emit `state: unavailable`; otherwise it foreign-keys the
field's complete closed source-reason domain. The seven gap-channel fields
have the one-literal domain `["unknown_gap_component"]`. A source without a
frozen field-level type/unit/nullability/reason schema is inadmissible.
The source's `domain_derivation_id` is the exact recipe-source-role foreign
key, and `content_binding_id` is the coordinator result of executing that
field-schema row's `content_binding_derivation_id` against the frozen input;
neither is copied from evaluator configuration.
`source_stream_id` is literal
`consumer-source:` plus SHA-256 of §10.1 canonical bytes of the other eight
fields, so neither a configured name nor a type-compatible field swap can
choose its identity. `source_authority_row_sha256` wherever referenced below
is SHA-256 of §10.1 canonical bytes of that complete nine-field row. Source
rows are ordered by first required occurrence in canonical root/step/source
position, with exact duplicate identities retained once; a semantically
unused configured source is extra.

Each `domain_authority_schemas` row has exactly `domain_id`,
`domain_kind`, `literal_domain_class`, `derivation_registry_id`,
`derivation_member_ids`, `key_fields`, `canonical_order`, `expected_count`,
`expected_keyset_sha256`, and `failure_disposition`. `domain_kind` is exactly
`record_key_domain | enum_literal_domain`. Counts are nonnegative JSON
integers excluding booleans; hashes bind the complete independently derived
ordered key or literal set; and failure disposition is `gate_fail`.

For an enum-literal domain, let \(L\) be the unique referenced
`consumer_literal_domain_specs.v1.rows` member. Its ten-field authority
projection is fixed field by field:

- `domain_id` is exactly `L.domain_id`;
- `domain_kind` is literal `enum_literal_domain`;
- `literal_domain_class` is exactly `L.domain_class`;
- `derivation_registry_id` is exactly `L.authority_registry_id`;
- `derivation_member_ids` is an exact deep copy of `L.ordered_literals`;
- `key_fields` is exactly `["literal"]`;
- `canonical_order` is literal
  `first-authority-reference-then-ordered-literal`;
- `expected_count` is recomputed as the length of `L.ordered_literals` and
  must equal `L.literal_count`;
- `expected_keyset_sha256` is recomputed as SHA-256 of
  `canonical_json_bytes(L.ordered_literals)` and must equal
  `L.ordered_literals_sha256`; and
- `failure_disposition` is literal `gate_fail`.

No projected value is implementation-selected. Thus fixed domain IDs and
ordered literals produce one exact authority-row byte string. No hash-only
or open-string enum is permitted.

For a record-key domain, the coordinator first constructs a normalized
record-domain descriptor \(R\) with exactly `domain_derivation_id`,
`derivation_registry_id`, `derivation_member_ids`, `key_fields`,
`canonical_order`, and `ordered_keys`. It derives every descriptor member and
the complete key array only from the complete frozen consumer, gap, Stage,
revenue, grouping, partition, draw, model-metric, pairing, and comparison
registries before ledger presence is inspected. Configured evaluator, graph,
runner, and ledger bytes supply none of them. `derivation_member_ids` is the
complete ordered authority-member-ID array whose registered expansion and
filter law produces the domain; `key_fields` is the complete ordered,
duplicate-free JSON-string field array; and `canonical_order` is the owning
registry's exact frozen ordering-law literal. `ordered_keys` is the resulting
complete unique ordered array of canonical JSON arrays, each positionally
matching `key_fields`. A scalar domain has `key_fields: []` and the sole key
`[]`; a legitimate empty domain has `ordered_keys: []`.

The record-key authority row is the following exact projection of \(R\):

- `domain_id` is exactly `R.domain_derivation_id`;
- `domain_kind` is literal `record_key_domain`;
- `literal_domain_class` is JSON null;
- `derivation_registry_id`, `derivation_member_ids`, `key_fields`, and
  `canonical_order` are exact deep copies of their namesakes in \(R\);
- `expected_count` is recomputed as the length of `R.ordered_keys`;
- `expected_keyset_sha256` is exactly SHA-256 of
  `canonical_json_bytes(R.ordered_keys)`; and
- `failure_disposition` is literal `gate_fail`.

The hash preimage is the one complete enclosing `ordered_keys` array,
including §10.1's trailing line feed; it is never concatenated key bytes, a
set, a display string, per-key hashes, or a JSON-lines stream. The empty
domain therefore hashes canonical `[]`. Every repeated reference to one
`domain_id` must reconstruct a byte-identical complete descriptor and key
array or registration aborts.

Every source-field `enum_domain_id` and
`unavailable_reason_domain_id`, source `domain_derivation_id`, node output
record-domain and `output_enum_domain_id`, and root `expected_domain_id`,
`output_enum_domain_id`, and `unavailable_reason_domain_id` must equal the
one authority row selected for that semantic step. Unknown, unused, aliased,
merely signature-compatible, open-literal, or configured-only domain IDs
fail registration. Record-key rows come first, in the reconstruction-input
registry order above and then each owning registry's frozen derivation-member
order. Enum-literal rows follow in exact
`consumer_literal_domain_specs.v1.domain_order`. Duplicate IDs are invalid
rather than collapsed; distinct IDs are retained even when their complete
ordered key or literal arrays and hashes are byte-identical.

`rule_authority_schemas` is a closed tagged array in class order: top-k;
weighted quantile; weighted top fraction; entropy; positive-denominator;
draw reduction; then legal rounding in independently extracted effective-year
order. Every row has
`rule_class`, `rule_id`, `authority_registry_id`, and
`authority_row_sha256`, plus only its class-specific fields listed below.

For every nonlegal row, `authority_registry_id` is the literal
`trusted_consumer_rule_literals.v1`, the coordinator-owned literal registry
compiled from frozen `consumer_semantic_recipe_specs.v1`,
`evaluation_specs.v1`, and `draw_spec.v1` semantics;
its row hash covers the complete class-tagged row excluding only
`authority_row_sha256`. Legal rows instead name
`legal_rounding_rule_specs.v1` and carry the independently extracted matching
row hash. Neither registry ID nor hash is configurable.

- the sole top-k row is `rule_id: top35`, with exactly `k: 35`,
  `direction: descending`, and
  `short_partition_rule: take_all_available`;
- the seven weighted-quantile rows are exactly, in this order,
  `p10 = 1/10`, `p25 = 1/4`, `p50 = 1/2`, `p75 = 3/4`,
  `p90 = 9/10`, `p95 = 19/20`, and `p99 = 99/100`, represented by
  exact `numerator` and positive `denominator` JSON integers;
- the three weighted-top-fraction rows are exactly `top10 = 1/10`,
  `top5 = 1/20`, and `top1 = 1/100`, and each additionally has
  `boundary_weight_rule: fractional_exact_weight` and
  `denominator_rule: strictly_positive`;
- the sole entropy row has `rule_id:
  weighted_mean_shannon_entropy_v1`, the exact four-status §3.1
  `status_order`, `log_rule_id:
  natural_log_directed_interval_to_binary64_v1`, and
  `zero_probability_rule: zero_log_zero_is_zero`;
- the sole positive-denominator row has `rule_id: strictly_positive`,
  `parameter_key: denominator_rule`, and exact ordered
  `allowed_ops:
  ["same_key_ratio_positive","partition_weighted_top_share"]`;
- the three draw-reduction rows have only `draw_reduction_id` in addition to
  the four common fields, `rule_id` exactly equals `draw_reduction_id`, and
  their IDs are exactly
  `analytic_linear_within_projection_draw`,
  `analytic_joint_state_within_projection_draw`, and
  `projection_cross_correction_draw`; and
- each legal-rounding row is the exact authority-row projection defined
  below, with common `rule_id` equal to `legal_rounding_rule_id`, including
  its effective range, applicability keys, unit, increment, and modes.

No fourth draw reduction exists for corrected roots;
`fixed_legacy_before_context` is confined to the typed diagnostic block.
Every rule-bearing node parameter, including `k_rule_id`,
`short_partition_rule`, `quantile_rule_id`, `top_fraction_rule_id`,
`boundary_weight_rule`, `denominator_rule`, `log_rule_id`,
`zero_probability_rule`, `legal_rounding_rule_id`, and
`draw_reduction_id`, exact-matches the binding selected by its root authority
row. `short_partition_rule` binds the top-k row;
`boundary_weight_rule` binds the selected top-fraction row;
`log_rule_id` and `zero_probability_rule` bind the entropy row; and every
ordinary `denominator_rule` also binds the positive-denominator row.
Source/content IDs, lookup fields, group/partition/tie keys,
unavailable-reason domains, and `dependency_dominator_id` are reconstructed
from the exact semantic-recipe step, source-field schema, and domain
authority rather than chosen by the graph.

Each `root_authority_schemas` row has exactly `model_metric_id`,
`metric_authority_registry_id`, `metric_authority_position`,
`required_source_bindings`, `required_opcode_chain`,
`required_rule_bindings`, `root_node_id`, `expected_domain_id`,
`key_fields`, `value_type`, `output_enum_domain_id`, `unit`,
`unavailable_reason_domain_id`, `draw_reduction`, and
`dependency_dominator_id`. Rows occur in the
independently reconstructed
complete final-metric order; `model_metric_id` is the root-domain ID and
resolves one frozen metric/evaluation authority at the recorded positive
JSON-integer position. The matching semantic-recipe row is joined to the
source-field, domain, rule, unit, and legal-rounding authorities; no field of
the configured DAG participates in that join. The root
`output_enum_domain_id` equals the final recipe step's ID and is nonnull
exactly for `value_type: enum`. `required_source_bindings` is the exact ordered
projection of every select/lookup node and contains exactly `node_id`,
`source_stream_id`, `value_field`, and `source_authority_row_sha256`.
`required_rule_bindings` contains exactly `node_id`, `rule_key`, `rule_id`,
and `authority_row_sha256` for every rule-bearing node parameter.
The root's semantic-closure hash is SHA-256 of §10.1 canonical bytes of this
complete fifteen-field authority row; its configured closure hash applies the
same function to the configured source/node/rule/root projection in the same
shape.

`required_opcode_chain` is the exact topologically ordered sequence of the
op-tagged node schemas below. For one-based step position \(s\), its
`node_id` is literal `consumer-node:` plus SHA-256 of §10.1 canonical bytes
of `[model_metric_id,metric_authority_position,s,op,
predecessor_node_ids,step_source_binding_without_node_id,
step_rule_bindings_without_node_id,authoritative_output_record_domain_id,
output_key_fields,output_value_type,output_enum_domain_id,output_unit]`. It is
therefore reconstructed without a
configured node ID or circular self-reference. The two step-binding members
are the namesake authority binding fields above excluding only their
subsequently attached `node_id`. A step without a source binding encodes JSON
null, not an omitted value or empty object; a step without a rule binding
encodes `[]`. Multiple rule bindings are in their operation-specific key
order in the table below. `authoritative_output_record_domain_id` is present
in every ID preimage even when the graph-node schema makes that record-key
domain implicit; it is the unique record-key domain ID derived from the
recipe step. `output_enum_domain_id` is independently present in every
preimage and obeys the literal-domain law below.

`predecessor_node_ids` is never null. It is `[]` for `select`; otherwise its
order is exactly input for lookup/group/legal-round/draw-reduction;
left then right for the five same-key binary operations and comparison;
numerator then denominator for ratio; condition, true, then false for choose;
value then rank for top-k; value then weight for quantile and top share; and
the four status-probability nodes in authority status order followed by
weight for entropy. The source binding is the single select or lookup binding
without `node_id`, or null for every other opcode. All key arrays preserve
the recipe/domain registry order and are `[]` only for an independently
declared scalar domain. `output_unit` uses JSON null exactly for a unitless
type. `output_enum_domain_id` is nonnull exactly when `output_value_type` is
`enum` and then foreign-keys the authority-selected `value_enum` row; it is
null for every other type. Every predecessor is earlier in that same root chain, and
`root_node_id` is the last step's ID. The expected global
`graph_nodes` array is the root-order concatenation of these chains; no
cross-root node sharing or configured deduplication changes it. Configured
source specs, nodes, and roots must respectively deep-equal the exact
authority projections and chains.

The only enum-capable opcodes are `select`, `exact_lookup`, and
`same_key_choose`. An enum-valued select exact-copies the selected source
field's enum-domain ID; an enum-valued lookup exact-copies the registered
table value field's enum-domain ID. An enum-valued choose requires its true
branch ID, false branch ID, and independently reconstructed step output ID to
be byte-identical. Every other opcode has non-enum output and requires null.
These are authority-signature checks before values are inspected. Thus two
closed enum domains cannot be joined by choose even when both use null units
and have byte-identical ordered literal arrays.

Thus a `p25` root whose quantile step cites `quantile_rule_id: p10` fails
root-authority reconstruction even if its values and runner proposal agree.
A wage root selecting the authoritative SE field, or the reverse, fails its
source binding even when both fields are rational microdollars. Field
identity, source authority, opcode position, rule ID, domain, type, and unit
all participate in reconstruction.

`trusted_consumer_evaluation_specs.v1` has exactly `schema_version`,
`semantic_authority_sha256`, `value_type_specs`, `unit_algebra_specs`,
`source_stream_specs`, `operation_specs`, `graph_nodes`, `metric_roots`,
`canonical_stream_law`, `numeric_law`, and `failure_disposition`.
`semantic_authority_sha256` is only the configured expected digest of the
complete object above. Its sole preimage is
`canonical_json_bytes` of the complete nine-field reconstructed
`trusted_consumer_semantic_authority.v1` object. The coordinator independently
reconstructs and hashes that object, requires equality, and also
exact-compares every constituent rather than accepting hash equality alone.
Missing, extra, duplicated, reordered, unreachable, or semantically unequal
sources, algebra rows, roots, or nodes abort registration; no configured
graph may define a smaller or different output surface.

Each `source_stream_specs` row has exactly `source_stream_id`, `source_kind`,
`authority_input_id`, `authority_object_id`, `key_fields`, `value_fields`,
`value_types`, `units`, `unavailable_reason_domain_ids`,
`domain_derivation_id`, `content_binding_id`, and
`dependency_class`. The four field arrays are nonempty, equal-length, and
positionally typed. In authority-row order, every configured row must
deep-equal the corresponding `source_authority_schemas` projection:
`value_fields`, `value_types`, `units`, and
`unavailable_reason_domain_ids` are respectively the exact
position-wise projections of `value_field_schemas.value_field`,
`.value_type`, `.unit`, and `.unavailable_reason_domain_id`, while every
other field exact-copies its namesake. The graph cannot substitute a different field with the same
type/unit, or repair a wrong declared type/unit by changing a node
declaration. `source_kind` is exactly one of
`corrected_expected_ledger | corrected_realized_ledger |
claim_context_gap | correction_bound_earnings_independent_input |
registered_legal_rule`; `dependency_class` is
`corrected_earnings | earnings_independent`. A `content_binding_id` is a
foreign key to a coordinator-recomputed complete ledger, gap, primitive-input,
or legal-table stream identity. It is never a path, JSON pointer,
runner-supplied digest, callback, or precomputed consumer result.
`correction_bound_earnings_independent_input` is admitted only after the
complete static dependency graph proves that the selected primitive cannot
transitively depend on earnings. The first-estimates primary or sidecar,
predecessor report, vintage-1 values, every `before_context` block, the
current output, runner IPC, and every precomputed earnings-dependent benefit
or revenue table are forbidden source kinds and have zero broker grants.

For a corrected atomic-ledger source, every `value_fields` member must occur
in the coordinator's independently reconstructed
`earnings_consumer_dependency_specs.allowed_corrected_ledger_fields`;
`proxy_labor_income_raw` and every legacy field are absent from that closed
array. An admitted member may name a direct registered
`ledger_row_schema_specs` field or one of exactly four flattened literals
`status_probability::covered_wage`,
`status_probability::covered_self_employment`,
`status_probability::noncovered`, and
`status_probability::unresolved`, in that status order. A flattened literal
is not a JSON pointer: the coordinator requires the source row's
`status_probabilities` object to have exactly the four §3.1 keys, selects the
named member, and converts its exact dyadic `(numerator, exponent)` to the
unique reduced rational (multiplying the numerator by \(2^e\) for
nonnegative \(e\), or using denominator \(2^{-e}\) otherwise). Each
flattened field has value type `rational` and unit `probability`. No other
nested projection, field path, or source-defined object type is parseable.

`value_type_specs` is the exact ordered array
`["rational","json_integer","boolean","enum","binary64",
"summary_binary64"]`; no other value type is parseable. A rational uses §3.1's reduced
`{"numerator":<integer>,"denominator":<positive integer>}` form; a finite
binary64 source value is decoded by `select`/`exact_lookup` to its exact
dyadic rational, so those nodes declare rational output with the unchanged
unit; raw binary64 never enters a rational opcode. A summary value has exactly
`observation_count`,
`mean_ieee754_binary64_hex`, and `sample_sd_ieee754_binary64_hex`.
The scalar `binary64` value and the latter two summary fields are lowercase
16-hex-digit finite binary64 encodings.
Primary decimal `mean` and `sample_sd` values must round-trip to those exact
bits. Negative zero is canonicalized to positive zero. `unit_algebra_specs`
is the exact `unit_algebra_specs.v1` object with exactly `schema_version`,
`unit_domain`, `rows`, `canonical_order`, `derivation_law`, and
`failure_disposition`. Its `schema_version` is that same literal.
`unit_domain` is the ordered unique nonnull unit-string array obtained by
scanning each reconstructed root in authority order and each recipe step in
step order: the step's source-field or predecessor units in the exact
predecessor order above, followed by its output unit. This includes every
required source field and intermediate output, not only root outputs; first
occurrence wins and JSON null is excluded. Each `rows` member has exactly `operation`,
`left_unit`, `right_unit`, and `result_unit`; `operation` is exactly
`same_key_product | same_key_ratio_positive`. The coordinator derives the
distinct required rows by scanning those operations in reconstructed root/
step order, retaining first occurrence. `canonical_order` is literal
`first-required-root-step-order`; `derivation_law` is
`derive-exact-unit-tuples-from-reconstructed-root-chains-v1`; and
`failure_disposition` is `abort_registration`. A configured missing, extra,
duplicate, reordered, or conflicting-result unit or row aborts registration.
Sum, difference, minimum, maximum, comparison, and choose require equal
units and do not consult the table; each product or ratio resolves exactly
one reconstructed row. No wildcard, prefix, dimensional inference,
commutative reversal, or unregistered unit exists.

`operation_specs` is the exact ordered opcode array:

```json
[
  "select",
  "exact_lookup",
  "same_key_sum",
  "same_key_difference",
  "same_key_product",
  "same_key_min",
  "same_key_max",
  "same_key_ratio_positive",
  "same_key_compare",
  "same_key_choose",
  "group_sum",
  "partition_top_k_sum",
  "partition_weighted_quantile",
  "partition_weighted_top_share",
  "partition_weighted_mean_shannon_entropy",
  "legal_round",
  "draw_mean_sample_sd"
]
```

The coordinator owns the evaluator implementation for this 17-op registry.
Each opcode's only legal node keys, arity, types, domain behavior, and
evaluation rule are the matching row below; `operation_specs` contains no
implementation-selected callback or parameters. The validator constructs
this literal registry independently and exact-compares the configuration
before parsing any graph node.

`graph_nodes` is a unique topological array. Every input-node reference must
point to an earlier row, and every row must be in the transitive closure of at
least one independently derived metric root. In addition, it must byte-equal
the root-order concatenation of `root_authority_schemas.required_opcode_chain`;
topological validity alone supplies no semantic authority. Every node has exactly
`node_id`, `op`, `output_key_fields`, `output_value_type`,
`output_enum_domain_id`, and `output_unit`, plus only the following
operation-specific keys:

| `op` | Additional exact keys and law |
|---|---|
| `select` | `source_stream_id`, `value_field`. The source row already is the complete domain-scoped projection; no opaque selector or value-dependent filter exists. |
| `exact_lookup` | `input_node_id`, `table_source_stream_id`, `input_lookup_key_fields`, `table_lookup_key_fields`, `table_value_field`. The registered table key is unique and lookup is total over the independently derived input domain. |
| `same_key_sum`, `same_key_difference`, `same_key_product`, `same_key_min`, `same_key_max` | `left_node_id`, `right_node_id`. Both complete ordered key streams must be byte-identical before the exact operation. |
| `same_key_ratio_positive` | `numerator_node_id`, `denominator_node_id`, `denominator_rule`, with literal rule `strictly_positive`; key streams must be identical. |
| `same_key_compare` | `left_node_id`, `right_node_id`, `comparator`, where comparator is `lt \| le \| eq \| ge \| gt`; key streams must be identical. |
| `same_key_choose` | `condition_node_id`, `true_node_id`, `false_node_id`; all key streams are identical and the two value branches have identical type, unit, and output enum-domain ID. |
| `group_sum` | `input_node_id`, `group_key_fields`, `member_order_fields`, `output_domain_id`. Group keys and complete membership are independently derived; members use canonical stable-key order. |
| `partition_top_k_sum` | `value_node_id`, `rank_node_id`, `partition_key_fields`, `k_rule_id`, `direction`, `tie_break_key_fields`, `short_partition_rule`, `output_domain_id`. `k_rule_id` is literal `top35`, direction is `descending`, \(k=35\), and short-partition rule is literal `take_all_available`; all four exact-match the unique top-k authority row. Partition and tie fields exact-match the semantic-recipe step and its domain schema; ties use that step's complete stable career key. |
| `partition_weighted_quantile` | `value_node_id`, `weight_node_id`, `partition_key_fields`, `quantile_rule_id`, `tie_break_key_fields`, `output_domain_id`. Value and weight nodes have identical complete keys and rational values; weights are nonnegative with positive partition total. The ID foreign-keys exactly one of the seven authority mappings `p10=1/10`, `p25=1/4`, `p50=1/2`, `p75=3/4`, `p90=9/10`, `p95=19/20`, or `p99=99/100`. Partition and tie fields exact-match the semantic-recipe step and its domain schema. Rows sort by exact value ascending then that step's complete stable-person tie key; output is the smallest value whose exact cumulative weight is at least \(q\) times total weight, with rational type and the input value unit. |
| `partition_weighted_top_share` | `value_node_id`, `weight_node_id`, `partition_key_fields`, `top_fraction_rule_id`, `tie_break_key_fields`, `boundary_weight_rule`, `denominator_rule`, `output_domain_id`. Values and weights are nonnegative rationals on identical complete keys; total weight and weighted-value denominator are positive. The ID is exactly `top10`, `top5`, or `top1`, mapping to `1/10`, `1/20`, or `1/100`; boundary and denominator rules are exactly `fractional_exact_weight` and `strictly_positive`. Partition and tie fields exact-match the semantic-recipe step and its domain schema. Rows sort by exact value descending then that step's stable-person key, fractionally allocate the boundary row, and divide the selected exact weighted-value sum by the complete weighted-value sum, with rational type and unit `share`. |
| `partition_weighted_mean_shannon_entropy` | `probability_node_ids`, `weight_node_id`, `partition_key_fields`, `status_order`, `log_rule_id`, `zero_probability_rule`, `output_domain_id`. The probability array is exactly the four §3.1 status nodes in authority order on identical keys; each row is an exact nonnegative dyadic vector summing to one, weights are nonnegative rationals with positive partition total, log rule is exactly `natural_log_directed_interval_to_binary64_v1`, and zero rule is exactly `zero_log_zero_is_zero`. The coordinator computes the survey-weighted mean of \(-\sum p\ln p\) and emits the uniquely correctly rounded scalar binary64 defined below, with unit `nat`. |
| `legal_round` | `input_node_id`, `legal_rounding_rule_id`; the rule is an exact foreign key into a registered effective-year legal table. |
| `draw_mean_sample_sd` | `input_node_id`, `within_draw_key_fields`, `reduction_draw_fields`, `draw_reduction_id`, `output_domain_id`; the input is rational or scalar binary64, and the reduction ID is exactly `analytic_linear_within_projection_draw`, `analytic_joint_state_within_projection_draw`, or `projection_cross_correction_draw` as selected by the root authority. |

`legal_rounding_rule_specs.v1` is a separately ratified frozen authority
registry, not a graph subobject. Its top level has exactly `schema_version`,
`authority_input_ids`, `rows`, `row_count`, `rule_id_order`,
`authority_row_sha256s`, `canonical_order`, and `failure_disposition`.
`schema_version` is `legal_rounding_rule_specs.v1`.
The coordinator independently extracts its ordered domain from the complete
effective-year statutory benefit/contribution tables and their pinned
authority inputs; the configured registry is an exact deep-copy comparand.
`authority_input_ids` is the nonempty ordered foreign-key array of every
such immutable legal-table input. `row_count` equals the positive row-array
length; ID order and the equal-length parallel row-hash array bind every extracted row,
canonical order is effective start then rule ID, and failure disposition is
`abort_registration`. Missing, extra, duplicate, overlapping, reordered, or
source-unbound rows abort before evaluator reconstruction.

Every `legal_rounding_rule_id` resolves uniquely to one row having exactly
`legal_rounding_rule_id`, `effective_start`, `effective_end`,
`applicability_key_fields`, `input_unit`, `output_unit`, `increment`,
`integer_mode`, and `tie_mode`. Effective ranges are nonoverlapping and
total over the node's independently derived domain; input and output units
are identical; and increment is a positive reduced rational in that unit.
`integer_mode` is exactly `floor | ceiling | truncate_toward_zero | nearest`.
Tie mode is `not_applicable` for the first three and exactly
`to_even | away_from_zero | toward_zero` for nearest. The evaluator divides
the exact rational input by the increment, chooses the mathematical integer
specified by that mode (using the tie rule only at exact half distance), and
returns that integer times the increment as an exact rational. The rule row
contains no result value, callback, formula string, implementation mode, or
free parameter. Missing/duplicate year applicability, a unit mismatch, or an
unknown mode fails the node.

For every op-tagged row above, source IDs/fields, predecessor identities,
lookup keys, group/partition/tie keys, rule fields, output domain, output
keys, type, and unit must byte-match the corresponding independently
reconstructed opcode-chain step. Passing generic arity and signature checks
cannot cure a semantic mismatch.

The signatures are exact. `select` emits its source field's type/unit except
that source `binary64` emits rational with the same unit, and it rejects a
summary source. `exact_lookup` applies the same rule to the table value;
its input node supplies keys, not a coerced value. Same-key sum, difference,
product, minimum, maximum, and positive ratio accept rational inputs only;
sum/difference/minimum/maximum require equal units, product/ratio require the
unique unit-algebra result, and all emit rational. Compare accepts two
rationals or two JSON integers of identical type and unit and emits boolean
with null unit. Choose requires a boolean/null-unit condition; its two
branches have identical non-summary type, unit, and output enum-domain ID and
its output repeats all three. `group_sum` accepts and emits rational with the input unit.
`partition_top_k_sum` requires rational values, a rational or JSON-integer
rank with its registered unit, and emits rational with the value unit.
Weighted quantile requires rational value and weight and emits rational with
the value unit. Weighted top share requires rational value and weight and
emits rational with unit `share`. Weighted entropy requires four
rational/`probability` nodes and a rational survey-weight node and emits
scalar binary64 with unit `nat`. `legal_round` accepts and emits rational
with the same unit. `draw_mean_sample_sd` accepts rational or scalar
binary64, never mixes those types within a stream, and emits
`summary_binary64` with the input unit; its embedded observation count is a
JSON integer excluding booleans. An enum, boolean, JSON integer, scalar
binary64, or summary in any other operand position is a schema error. Every
node's declared output type, enum-domain ID, and unit must equal this
authority signature before graph evaluation.

There is no generic `args`, `parameters`, literal-number, formula-string,
`eval`, callback, dynamically resolved pointer, implementation default,
generic benefit-assembler node, predecessor-result lookup, or unregistered
operation. Constants enter only through coordinator-read registered legal
tables. This finite algebra must express wage/SE grouping and caps, top-35
selection, AIME, bend-point/PIA and claim adjustments, insured-status and
claim predicates, weighted benefit/revenue counts and amounts, contributions,
ratios, survey-weighted quantiles/top shares, mean status entropy, and draw
reductions. If a required intermediate cannot be expressed by these nodes,
registration fails and a newly ratified evaluator version is required;
runner code may not fill the gap.

Every same-key operation requires exact equality of complete canonical key
streams. `exact_lookup` rejects a missing or duplicate table key.
`group_sum` uses the independently reconstructed output domain and cannot
drop an empty or difficult group. Top-35 selection occurs inside each
complete projection×correction×operative-claim×career draw before reduction,
with exact-value descending rank and stable-key ties. Arithmetic and grouped
accumulation are exact rational operations. A scalar-binary64 draw input is
first interpreted as its exact dyadic rational. The sample mean is exact
\(\sum x/n\); sample variance is exact
\(\sum(x-\bar{x})^2/(n-1)\); only its square root is correctly rounded once
to nearest-even binary64. Legal rounding occurs only at a `legal_round`
node. Weighted-quantile and top-share thresholds, cumulative weights,
fractional boundary allocation, numerators, and denominators remain exact
rationals. The entropy op begins with exact dyadic probabilities and rational
weights, evaluates each natural logarithm by arbitrary-precision directed
interval arithmetic over the frozen precision schedule, and stops only when
the complete weighted-mean interval certifies one binary64
round-to-nearest-even bin. It emits that bin's unique finite bit pattern and
never uses a platform `log`.

Failure classification and propagation are exact. A declared
type/unit/record-domain/output-enum-domain mismatch or an enum output on an
unauthorized opcode aborts registration before stream values are inspected.
An unexpected extra source/node coordinate fails the owning stream with
`unexpected_extra_coordinate` evidence but creates no authority row. For an
independently required coordinate, a missing/duplicate input, malformed typed
payload, enum literal outside the selected domain, lookup failure, intrinsic
numeric failure, or result-conversion failure maps only through the exact
`consumer_evaluator_condition_reason_specs.v1` row; the coordinate is
retained as unavailable and is never suppressed or zero-filled.

Before testing a local condition, the evaluator propagates the first
unavailable required input unchanged—never a generic
`unavailable_required_input`. Required-input order is the
`predecessor_node_ids` order above, then canonical member-key order within a
group, partition, or reduction. For `exact_lookup`, only the matched table
cell can propagate because the input node supplies keys rather than a value.
For `same_key_choose`, the condition propagates first; after it yields a
boolean, only the selected branch can propagate and an unavailable unselected
branch is ignored. Only when every required input is available does the
evaluator test applicable local conditions in registered condition-row
order, with result conversion last. A propagated or local reason absent from
the enclosing root's unavailable-reason domain is a reconstruction failure,
not a recoding opportunity.

An empty authority-domain `group_sum` group or `partition_top_k_sum`
partition emits exact rational zero in the input/value unit and has no
unavailable reason. The weighted partition opcodes instead apply their exact
positive-total conditions above. No other intrinsic value-time condition
exists for select, lookup after totality, sum, difference, product, minimum,
maximum, compare, choose, group sum, top-k, or legal round.

For each root, the coordinator derives the required ordered reason domain by
scanning reachable source reasons in recipe-step/source-field order, followed
by reachable local reason codes in recipe-step/condition-row order, retaining
the first occurrence of each literal. The root's
`unavailable_reason_domain_id` must resolve the one
`consumer_literal_domain_specs.v1` row whose ordered literals equal that
derived array exactly. Missing, extra, reordered, or generic reasons abort
registration.

Each `metric_roots` row has exactly `model_metric_id`, `root_node_id`,
`expected_domain_id`, `key_fields`, `value_type`, `output_enum_domain_id`,
`unit`,
`unavailable_reason_domain_id`, `draw_reduction`, and
`dependency_dominator_id`. In authority
order, every row deep-equals those ten namesake fields from its independently
reconstructed `root_authority_schemas` row; none is graph-derived. Root keys include
`year_source_class` and,
for every claim-context benefit gap
(`structural_gap_imputed | claim_specific_boundary_gap`), the nonnull
`operative_claim_year` and `career_variant_id`. They therefore cannot alias
an unconditional structural-gap or 2013 result. Each independently
inventoried metric resolves exactly one root, and every graph node is
reachable from that root array.

`canonical_stream_law` is the literal
`independent-key-order-lf-canonical-typed-value-v1`. Every source, node, and
root stream is the concatenation, in its independently derived key order, of
one §10.1 canonical JSON line having exactly one of:

```json
{"key":[...],"value":{"state":"value","value_type":"<literal>","value":{}}}
{"key":[...],"value":{"state":"unavailable","reason_code":"<registered literal>"}}
```

The first row's `value` member is the exact scalar or summary encoding
declared by its value type, not necessarily a JSON object. Row count,
ordered-keyset SHA-256, and complete value-stream SHA-256 are recorded for
every stream. `numeric_law` is the literal
`exact-rational-until-registered-round-or-summary-v1`, and
`failure_disposition` is `gate_fail`.

The coordinator—not the runner—evaluates this graph. It materializes and
hash-locks all permitted source streams, evaluates every node and root in
topological order, and constructs every corrected downstream/context numeric
row from those trusted root streams.

Without reading runner bytes or evaluator configuration, the coordinator
derives `consumer_result_proposal_authority_schema.v1` from the reconstructed
root authority. That in-memory object has exactly `schema_version`,
`packet_schema_version`, `packet_keys`, `root_domain_sha256`, `row_schemas`,
`canonical_order`, and `failure_disposition`. `packet_schema_version` is
`consumer_result_proposal.v1`; `packet_keys` is exactly
`["schema_version","semantic_authority_sha256","root_domain_sha256","rows"]`;
and `root_domain_sha256` hashes §10.1 canonical bytes of the complete
authority-ordered array of
`[model_metric_id,root_node_id,expected_domain_id,
output_enum_domain_id,key]`.
`row_schemas` is in root-authority order and each row has exactly
`model_metric_id`, `root_node_id`, `expected_domain_id`, `key_fields`,
`value_type`, `output_enum_domain_id`, and
`unavailable_reason_domain_id`, copied from the authority root. Canonical
order is `root-authority-then-derived-key-order`, failure
disposition is `gate_fail`, and no packet or configured graph byte enters
this reconstruction.

The runner packet must have only the four `packet_keys`. Its schema version
is the packet literal and its two hashes equal the independently reconstructed
semantic authority and root-domain hashes. `rows` is the complete nonempty
root-coordinate domain, never a runner-selected subset.

Before any coordinate lookup, every row is validated only against the
authority-independent `consumer_result_proposal_wire_row.v1` envelope. It has
exactly `model_metric_id`, `root_node_id`, `key`,
`output_enum_domain_id`, and `value`. The two IDs are nonempty JSON strings;
`key` is a §10.1-canonical JSON array whose atoms are only JSON strings, JSON
integers excluding booleans, booleans, or null;
`output_enum_domain_id` is null or a nonempty JSON string; and `value` may be
any bounded strict-JSON value at this envelope stage. The coordinate identity
is canonical bytes of `[model_metric_id,root_node_id,key]`. Only the first
occurrence of a recognized authority coordinate is then validated against
its row schema: its key array is exact, its `output_enum_domain_id` equals the
authority value (nonnull exactly for enum output), and `value` is the exact
tagged union below.

An available value has exactly `state: value`, `value_type`, and `value`; its
type equals the root authority and its encoding is exactly:

- `rational`: the reduced two-key positive-denominator object in §3.1;
- `json_integer`: a JSON integer excluding booleans;
- `boolean`: a JSON boolean;
- `enum`: one JSON string in the root's
  `output_enum_domain_id` closed domain;
- `binary64`: one finite lowercase 16-hex-digit encoding; or
- `summary_binary64`: an object with exactly `observation_count`,
  `mean_ieee754_binary64_hex`, and `sample_sd_ieee754_binary64_hex`, with a
  JSON-integer count excluding booleans and two finite lowercase
  16-hex-digit encodings.

An unavailable value has exactly `state: unavailable` and `reason_code`;
the reason is one member of the root's independently reconstructed
`unavailable_reason_domain_id`. No other state, value key, null, coercion,
or extension field exists. Units are absent because only the authority
supplies them. No graph, source schema, domain selector, unit, count
authority, callback, or primary-field value is representable.

Runner mismatch classification is total and precedence-ordered. The
coordinator first hashes the bounded received bytes. Invalid JSON; unequal
top-level keys, schema/header literal or authority/domain hash; a row with
wrong envelope keys or envelope-member type; a noncanonical key container; or
an inversion among the recognized first-occurrence coordinates sets
`packet_schema_mismatch_count: 1`, sets the other three mismatch counts to
zero, and sets `normalized_runner_metric_root_streams_sha256` to SHA-256 of
canonical bytes of
`["consumer-result-proposal-schema-invalid-v1",runner_packet_sha256]`.
No partial row is used.

Otherwise `packet_schema_mismatch_count` is zero and classification resolves
coordinates before inspecting root-specific value semantics. Each
envelope-valid coordinate absent from authority contributes exactly one
`extra_row_count`; its discarded `value` and output-enum-domain semantics are
never inspected. Each occurrence after the first of an expected coordinate
also contributes exactly one extra and is not semantically inspected.
Inversion testing considers only first occurrences of expected coordinates;
unknown and duplicate rows do not participate. Each absent expected
coordinate contributes one `missing_row_count`. Each first expected row whose
output enum-domain ID, tagged-value keys/type/encoding, enum literal,
unavailable reason, or complete value differs from authority contributes one
`value_mismatch_count`. Thus an envelope-valid wholly unknown coordinate is
always extra, while a row that fails the universal envelope is always packet
schema-invalid; neither classification depends on an unknown root schema.
For this branch the normalized hash covers, in authority order, exactly the
first occurrence of every present expected coordinate; missing coordinates
are absent and unknown or duplicate rows are excluded. These rules are
mutually exclusive and leave no implementation-selected sentinel, counter,
order, or partial-normalization choice.

`trusted_consumer_evaluation.v1` has exactly `schema_version`,
`semantic_authority_sha256`, `semantic_comparison`,
`graph_specs_sha256`, `source_stream_results`, `node_results`,
`metric_root_results`, `runner_comparison`, and `status`.
`semantic_authority_sha256` is the coordinator-reconstructed digest.
`semantic_comparison` has exactly
`configured_semantic_authority_sha256`,
`reconstructed_semantic_authority_sha256`,
`configured_source_schema_sha256`, `reconstructed_source_schema_sha256`,
`configured_domain_bindings_sha256`,
`reconstructed_domain_bindings_sha256`,
`configured_rule_bindings_sha256`,
`reconstructed_rule_bindings_sha256`,
`configured_unit_algebra_sha256`,
`reconstructed_unit_algebra_sha256`,
`configured_root_semantics_sha256`,
`reconstructed_root_semantics_sha256`,
`source_schema_mismatch_count`, `domain_mismatch_count`,
`rule_binding_mismatch_count`, `unit_algebra_mismatch_count`,
`root_semantics_mismatch_count`, and `status`. All five counts are actual
nonnegative JSON integers excluding booleans. Passing requires each hash pair
equal and every count zero.

The five comparisons use exact canonical sequences. Source sequences are the
configured `source_stream_specs` rows and the namesake reconstructed
twelve-field projections, in source-authority order. Domain sequences contain
one exact
`[object_class,object_id,parameter_key,domain_id]` row, in source then
root/step order, for every source `domain_derivation_id` and nonnull
field-level `enum_domain_id` or `unavailable_reason_domain_id` (recovered from
the exact source identity),
every step's authoritative output record domain and output enum domain
(including an implicit or null one), every root's `expected_domain_id`,
`output_enum_domain_id`, and `unavailable_reason_domain_id`, and every
proposal-row output enum-domain binding. Rule sequences are
the root-order/step-order arrays of
`[model_metric_id,node_id,rule_key,rule_id,authority_row_sha256]`.
Unit-algebra sequences begin with the exact five-field top-level object
excluding `rows`, followed by each four-field row. Root sequences are the
complete fifteen-field semantic-root rows in metric-authority order; the
configured sequence is reconstructed into that same shape from its
source/node/rule/root comparands.

Each named hash covers its entire corresponding sequence. For each pair, its
mismatch count is the number of unequal positions from zero through one less
than the greater sequence length: an out-of-range side is unequal and two
present positions are equal only when their complete canonical row bytes are
equal. Thus one missing, extra, reordered, or field-unequal row has a unique
mechanical count. The configured/reconstructed combined authority hashes are
the configured scalar comparand and the independently reconstructed complete
authority-object digest; neither substitutes for any constituent sequence.
Configuration acceptance already required the same reconstruction, and this
retained recheck proves the executed object did not replace it.
Its source rows have exactly `source_stream_id`, `row_count`,
`keyset_sha256`, `value_stream_sha256`, `status`, and `reason_code`; node
rows replace the ID with `node_id` and additionally carry the ordered
`predecessor_value_stream_sha256s`; root rows replace it with
`model_metric_id`, `root_node_id` and additionally carry
`expected_root_closure_sha256`, `configured_root_closure_sha256`. The two
closure hashes must equal on a passing root. Passing rows have null reason;
failing rows retain actual counts and hashes.
`runner_comparison` has exactly `runner_packet_sha256`,
`normalized_runner_metric_root_streams_sha256`,
`trusted_metric_root_streams_sha256`, `missing_row_count`,
`extra_row_count`, `value_mismatch_count`,
`packet_schema_mismatch_count`, and `status`.
`runner_packet_sha256` hashes the bounded received bytes before strict packet
parsing, so malformed evidence still has one exact identity. All counts are
actual nonnegative JSON integers. Overall status passes only
when semantic source/domain/rule/unit/root reconstruction, graph/source/node/
root domains and hashes are exact, forbidden-source grants are zero, every
root was coordinator-evaluated, all four runner mismatch counts are zero,
and the two complete root-stream hashes match.

Runner-proposed bytes never populate a corrected result. A runner that
declares a corrected operand but returns a pinned first-estimates number
therefore produces a positive value mismatch at the first differing root and
fails G22; even if a value happens to coincide, the published byte is still
the independently coordinator-derived byte and no legacy path is present.
Immediately before final rename, the trusted validator reconstructs semantic
authority again from the frozen registries without reading the configured
DAG, exact-compares every configured source/domain/rule/unit/root closure,
reevaluates the resulting authoritative chains, and bit-compares every
primary corrected value and every recorded source/node/root hash. A late
authority or byte mismatch is an invariant incident and permits neither
rename. A result byte that is not the trusted authoritative-root byte cannot
be certified.

`gate_specs.v3` is the ordered 22-object registry corresponding positionally
to the list below. Its literal IDs are `G01` through `G22`; each object has
exactly `gate_id`, `normative_statement`, `evidence_selector`, `comparator`,
`required_value`, and `failure_disposition`. The statement text is the
matching item below and every failure disposition is `gate_fail`. Every gate
is conjunctive. One violating record is failure:

1. The common base-ledger key set and every claim-context benefit gap view
   exactly cover the independently reconstructed Stage A–D benefit and
   complete unsplit revenue domains. Each consumer equals its own derived
   domain—not a configured subset—and component bytes are identical on the
   intersection. Missing support fails; it never revises a domain hash.
2. Final wage, SE gain, SE loss-magnitude, SECA-base, noncovered, unresolved,
   capped, and creditable fields are finite and nonnegative.
   `covered_se_net_earnings_pre_seca` is the sole permitted signed statutory
   intermediate.
3. A negative SE amount never offsets employee wages; all permitted
   within-SE loss netting follows the effective-year legal rule.
4. Atomic status amounts and person-year component deltas reconcile exactly
   under §3.1; no unexplained residual is permitted.
5. Unknown coverage never defaults silently to private, covered, noncovered,
   zero, or a full-year amount.
6. Historical SECA factors, thresholds, eligible concepts, incorporation
   treatment, and other legal rules apply only to registered years and to
   typed covered/excluded fact bindings whose complete required-microfact
   arrays, presence, premise values, and transform inputs the coordinator
   derived through the inventory-backed direct-law ledger.
7. Wages precede SE under one combined person-year maximum.
8. The exact same hash-verified underlying component bytes and correction
   draws feed benefits and revenue through the corrected-ledger accessor;
   neither consumer may rematerialize an alternative correction.
9. Raw proxy, raw fields, source wave/role/job, annualization, separate gain
   and loss channels, classification reasons, probabilities, measurement
   delta, and uncertainty provenance remain recoverable.
10. The six exact `replay_specs.v1` rows exist in order and byte-match the
    complete fit/selection bundle, substantive model hash, and expected plus
    realized ledger identities. Empty, missing, duplicate, or reordered rows
    fail.
11. The trusted RNG-provider call ledger has exactly one row per frozen
    provider; the correction midpoint provider exact-matches the exhaustive
    key registry, the one coordinator-only retry-nonce entropy call
    exact-matches its 32-byte pre-production callsite/flow law, and every
    projection, mortality, claiming, marriage, Python, NumPy, other
    OS-entropy, or forbidden provider has zero calls. On both
    `selected_correction` and `no_eligible_candidate`, the complete
    expected principal lifecycle event stream exact-matches the actual stream,
    including every effective creation/destruction boundary and event order;
    the process-lifecycle ledger/cache is sealed only after provider-capable
    work ends, the unchanged wrappers enter irreversible deny-all state, and
    the seal plus zero sticky/post-seal requests exact-rechecks immediately
    before the first rename.
12. No post-boundary questionnaire fact enters production; every gap right
    neighbor is no later than the operative claim year; opening-backfill
    adjudication precedes gap derivation; and no universal 2013 row is reused
    across claim contexts. Revenue has no 2013 key.
13. Career data-completeness and modeled OASDI coverage are separately named
    and computed.
14. A coordinator-owned second execution applies the exact common multiplier
    `7.0` to every PSID survey weight while leaving every target
    loss/objective weight bit-identical. It byte-matches each candidate's
    parameter bits, predictions, losses, identification/disposition, selected
    candidate, tie result, substantive model hash, and ledger identities; no
    level target is granted.
15. Broker grants, worker IPC hashes, physical ancestry/alias closure, and
    sandbox audit exact-match the derived allowlist. Fit/selection workers
    have no path, descriptor, network, subprocess, or content-alias access to
    vintage-1, anchor, held-out, benefit-total, Option-C, repository data,
    runs, or docs bytes, and no runner IPC schema admits a direct-law
    microfact presence boolean or value.
16. Every unresolved amount follows the registered missing-fact policy and
    reason code. No objective term or gate rewards moving unknown mass from
    `unresolved` to covered or noncovered. Weighted unresolved gain/loss
    shares, person-year shares, and status entropy publish overall and by era
    × role, but v1 imposes no evidence-free magnitude cutoff.
17. The independently byte-pinned PSID inventory and crosswalk all-key
    disposition streams match positionally; the complete 35-purpose domain,
    component-slot assembly, structural-missing consequences, six executable
    rule closures, inventory-backed covered/excluded fact-binding
    specifications, coordinator-derived required-microfact projection,
    presence/premise/action ledger, and nine verification-claim results are
    exact; the wave/reference/source-lineage map is exact; and every
    target/evaluation key is present. A missing job, state, direct-law field,
    microfact-ledger row, or cell never shrinks the registry.
18. Nonlinear AIME/PIA results are computed within each complete correction
    career draw before reduction.
19. The selected candidate passes the parameter-count, full-rank Jacobian,
    condition-number, and deterministic solution-agreement law in §5.3, and every losing or
    failed candidate has its complete registered disposition. A losing
    candidate need not pass.
20. Every registered metric that uses correction draws passes the
    10-versus-20 correction-draw stability tolerance.
21. The complete §6.2 two-class held-out/zero-weight value poisoning and
    exclusive-source-byte mutant leaves parameters, model-choice losses,
    candidate dispositions, the selected/no-eligible branch, the branch-tagged
    selected-model projection, every non-G21 gate row/evidence hash, G21
    result, and conditions 1–6 byte-identical. This battery runs even when
    both baseline and production selection are `no_eligible_candidate`; a
    mutant branch flip is failure.
22. Every final corrected earnings-dependent metric in the complete
    independently reconstructed benefit, revenue, pairing, and comparison
    domains is transitively dominated by corrected ledger fields and is
    independently evaluated from the reconstructed semantic authority above.
    Every configured source identity/type/unit, domain, operation rule,
    unit-algebra row, opcode chain, and root closure exact-matches its
    authority schema with zero semantic mismatches. Raw proxy may remain an
    inaccessible audit field in atomic ledger bytes, but raw-proxy or legacy
    numeric earnings have zero corrected-root paths and are evaluable only in
    `before_context`; the runner's complete proposal has the exact packet
    schema and its root stream exact-matches the coordinator's complete root
    stream with zero missing, extra, value-mismatched, or schema-mismatched
    rows. Every certified modeled-worker denominator uses
    `modeled_covered_worker_probability_analytic`, never a draw indicator or
    finite-grid fraction.

`rng_access_specs.v2` has exactly `schema_version`, `providers`,
`lifecycle_phase_domain`, `bootstrap_implementation_specs`,
`provider_capable_principal_authority`, and `canonical_order`. Schema version
is that literal; `providers` is the nonempty ordered provider array;
`lifecycle_phase_domain` is the complete exact
`rng_lifecycle_phase_domain.v1` object in §10.2; the next two members are the
complete exact objects below; and canonical order is `provider-order`. The
provider rows freeze exactly three authority classes:
`correction_keyed_midpoint | coordinator_retry_nonce_entropy | forbidden`.
Every provider row has exactly `provider_id`, `authority_class`,
`provider_identity`, `expected_call_law`, `allowed_callsite_identity`,
`argument_law`, and `flow_law`. The correction class contains only §5.4's
SHA-256 midpoint function and exact expanded key-call law. Every reference
below to an `rng_access_specs.v2` provider or provider order means this
`providers` member.

`rng_bootstrap_implementation_specs.v1` has exactly `schema_version`, `rows`,
and `canonical_order`. Schema version is that literal. Every row has exactly
`object_kind`, `provider_id`,
`repository_relative_path`, `implementation_blob_oid`, `head_blob_oid`, and
`sha256`. Object kind is
`provider_call_ledger | keyed_uniform_lifecycle_cache | provider_wrapper |
native_audit_hook`; provider ID is the matching provider foreign key exactly
for a wrapper and is null otherwise. The path is the unique traversal-free
tracked factory path for that kind/provider pair. Both OIDs are 40 lowercase
hex, identify that path at the registered implementation commit and `HEAD`,
and are equal; `sha256` is the 64-lowercase-hex SHA-256 of those file bytes.
Descriptor-read live bytes must byte-equal both Git blobs and produce that
digest. Rows are exactly one ledger, one cache, the
provider-order wrappers, and one hook, in that order; canonical order is
`ledger-cache-provider-order-wrappers-audit-hook`.

`provider_capable_principal_authority.v1` has exactly `schema_version`,
`code_identity_rows`, `boundary_rows`, `rows`, and `canonical_order`. Schema
version is that literal. Every code-identity row has exactly
`g15_code_identity_id`, `principal_kind`,
`repository_relative_path`, `implementation_blob_oid`, `head_blob_oid`,
`sha256`, `mount_allowlist_id`, `mount_allowlist_sha256`,
`descriptor_allowlist_id`, `descriptor_allowlist_sha256`, `ipc_schema_ids`,
`ipc_schemas_sha256`, and `expected_mount_trace_sha256`. Principal kind is
`worker | coordinator_delegate | proposal_process`; path is the unique
traversal-free tracked implementation path; the two 40-lowercase-hex blob
OIDs identify it at the registered implementation commit and `HEAD` and are
equal; and `sha256` is the 64-lowercase-hex SHA-256 of those file bytes.
Descriptor-read live bytes must byte-equal both Git blobs and produce that
digest. Each mount/descriptor allowlist ID is a nonempty authority-ID string,
and `ipc_schema_ids` is a duplicate-free ordered array of nonempty
authority-ID strings. An empty grant instead uses the two literal allowlist
IDs and empty IPC array specified by the empty-grant law below.
`mount_allowlist_sha256`, `descriptor_allowlist_sha256`,
`ipc_schemas_sha256`, and `expected_mount_trace_sha256` are 64 lowercase hex.
Together the IDs and hashes foreign-key the complete independently
reconstructed G15 authority.
`g15_code_identity_id` is literal `g15-code:` plus SHA-256 of §10.1 canonical
bytes of the other row members. Rows have unique IDs, are ordered
lexicographically by ID, and are the complete code-identity closure for every
provider-capable worker, coordinator delegate, and proposal process.

Every boundary row has exactly `boundary_id`, `phase`, `boundary_order`,
`coordinator_callsite_identity`, and `atomicity_law`. Phase is a
`rng_lifecycle_phase_domain.v1` literal; boundary order is a nonnegative JSON
integer excluding booleans; callsite is the pinned coordinator source/blob/
code-object identity that commits the transition; and atomicity law is
literal `complete-before-next-boundary-or-not-completed`. `boundary_id` is
literal `rng-lifecycle-boundary:` plus SHA-256 of §10.1 canonical bytes of
the other row members in the order above. IDs and callsite/order pairs are
unique; orders are exactly contiguous
`0..(boundary_rows.length - 1)`; and rows are in boundary order. The array
covers every principal authorization, creation, normal destruction, incident
cutoff, cutoff-specific incident-cleanup destruction, delegated-empty-set
barrier, and terminal role cutoff.
Boundary zero is the `bootstrap_phase_state_initialized` sentinel, completed
immediately after the phase cell, direct-exit path, and lifecycle counter are
initialized and before any fallible monitored-object creation. It is the
minimum boundary/order sentinel. It is never an incident cutoff: incident
publication requires a durably reread applicable claim and the frozen
claim-era cutoff row whose phase equals the then-current coordinator phase.
Across the effective principal events on any one legal terminal/cutoff path,
no two creation or destruction events select the same boundary ID/order pair.
Selected-path boundary orders need not be contiguous because unselected
alternative-path and non-event boundary rows remain in the authority.

Every principal-authority row has exactly `principal_authority_id`,
`g15_code_identity_id`, `principal_kind`,
`implementation_identity_sha256`, `provider_capability_kinds`, and
`lifecycle_roles`. The code ID foreign-keys exactly one code-identity row;
principal kind exact-matches it and implementation hash equals its `sha256`.
Capability kinds are
a nonempty canonical-order subset of
`direct_provider_call | keyed_cache_request | provider_request_ipc`.
`lifecycle_roles` is a nonempty array whose rows have exactly
`principal_lifecycle_role_id`, `execution_attempt`, `instance_coordinates`,
`applicable_terminal_pairs`, `creation_phase`, `normal_destruction_phase`,
`creation_boundary_id`, `creation_boundary_order`,
`normal_destruction_boundary_id`, `normal_destruction_boundary_order`,
`incident_cleanup_boundaries`, and `lifecycle_role_order`. Execution attempt
is `initial | authorized_retry`; instance coordinates are a possibly empty
array of unique `<frozen-axis-id>:<member-id>` strings in frozen axis/member
order; and applicable terminal pairs are a nonempty duplicate-free
domain-order array of objects having exactly `terminal_branch` and
`evaluation_completion`, each one of the three legal pairs below. Both phases
are `rng_lifecycle_phase_domain.v1` literals. Every boundary order and
lifecycle role order is a nonnegative JSON integer excluding booleans; role
order is globally unique, and normal destruction boundary is strictly later
than creation boundary. The creation and normal-destruction ID/order pairs
foreign-key exact boundary rows whose phases exact-match the corresponding
role phase; boundary orders are not lifecycle counter values.

`incident_cleanup_boundaries` is the complete possibly empty array of rows
having exactly `incident_cutoff_boundary_id`,
`incident_cutoff_boundary_order`,
`incident_cleanup_destruction_boundary_id`, and
`incident_cleanup_destruction_boundary_order`. It has exactly one row for
every claim-era incident-cutoff boundary applicable to this execution attempt
that is at or after the role's creation boundary and before its normal-
destruction boundary, and no other row. Source and target ID/order pairs
foreign-key exact boundary rows; the source is that cutoff, the target's phase
is literal `incident_handling`, and the target order is strictly greater than
the source order. For every retry-authorizable cutoff, every mapped initial-
attempt cleanup target order is lower than every authorized-retry creation
boundary order. Rows are in cutoff-boundary order. Different cutoff/live-role
pairs have distinct cleanup target pairs, and no target for one cutoff may
substitute for another even if their phases or coordinator callsites
coincide.

Lifecycle role order is the frozen expected principal-creation order across
those boundaries.
`principal_lifecycle_role_id` is literal `rng-principal-role:` plus SHA-256
of §10.1 canonical bytes of the other role members in the order above.
Roles have unique IDs and unique attempt/coordinate/role-order tuples and are
ordered by lifecycle role order. Because the role ID binds the complete
static applicability set rather than the future selected pair, it is known
before the principal is created and is never rewritten.

`principal_authority_id` is literal `rng-principal-authority:` plus SHA-256
of §10.1 canonical bytes of every other authority-row member in the order
above. Authority rows have unique IDs, are ordered by their first lifecycle
role position, and their role arrays independently enumerate every possible
non-root principal instance for both terminal branches, each legal evaluation
completion, the initial attempt, and an authorized retry from the frozen
candidate/provider/domain axes and atomic-boundary registry. Canonical order is
`first-lifecycle-role-order`. The coordinator reconstructs the complete code
and role authority independently before configuration comparison; runner or
configuration bytes cannot add, remove, or scope a code identity, axis
member, or lifecycle role.

The live `trusted_rng_provider_call_ledger.v1` has exactly
`schema_version`, `provider_order`, `events`, `terminal_branch`,
`seal_sequence`, and `canonical_order`. Provider order exact-matches
`rng_access_specs.v2.providers`; schema version is the object literal and
canonical order is `event-sequence`. Each event has exactly `event_sequence`,
`provider_id`, `authority_class`, `callsite_identity`,
`argument_schema_id`, `argument_sha256`, `phase`, `flow_destination`, and
`disposition`. Event sequence is contiguous from JSON integer one, excluding
booleans; provider and authority class foreign-key the frozen row; phase
foreign-keys the exact §10.2 `rng_lifecycle_phase_domain.v1` literal copied
from coordinator state; and disposition is
`authorized_provider_return | denied_forbidden_request`. The nonce event
hashes only its integer-32 argument object and commitment-only flow metadata,
never the private bytes. A midpoint event binds its complete namespace
argument and cache-miss flow. A forbidden request is recorded with its actual
callsite/argument and denial before the provider is reached. Events retain
execution order; at seal, terminal branch and seal sequence become nonnull
and immutable. There is no summarized, worker-written, or selected subset of
this ledger.

Its `flow_law` also freezes
`keyed_uniform_lifecycle_cache.v1`, a coordinator-owned in-memory map keyed
by the complete canonical §5.4 namespace. It is created empty at process
entry before the initial attempt and remains the same object through the
single authorized retry. On a cache miss, and only then, the coordinator
invokes the pinned midpoint provider once, bit-validates the result against
an independent SHA-256 evaluation, stores the exact binary64 bits, and
returns them. On a hit it returns those exact stored bits and makes no
provider call. Both attempts request namespaces only in the independently
expanded canonical registry order. The initial attempt may therefore leave
any exact prefix of the registry in the cache; a retry restarts that order,
reuses every populated key, and
calls the provider exactly once for each previously unseen key. At successful
completion the whole-process provider trace has exactly one call for every
independently expanded registry key and no duplicate, while the registry
itself contains exactly one key/value row. Cache identity, keys, and values
are private coordinator state, never serialized as retry authority or
admitted through runner IPC; a replaced cache, unequal recomputation,
duplicate provider call, altered hit, or missing final key fails G11. An
eligible external-compute incident need not prove zero prior midpoint calls,
because this exact-once cache law spans both attempts.

The ceremony class
contains exactly one pinned `os.urandom` provider and exactly one
implementation-blob/code-object callsite inside the trusted coordinator.
Its argument law is one call with JSON integer byte count `32`; its call must
occur after the exclusive coordinator lock and value-blind prelaunch checks
but before authority reservation, the initial claim, any production-I/O
capability, or any correction import. Its flow law permits the 32 private
bytes only as the in-memory retry nonce, the SHA-256 commitment in the claim,
and the same-process opaque receipt binding in §10.3. The raw bytes, a
derived seed/uniform, or any nonce-dependent bit may not enter candidate
packets, parameters, losses, selection, model identity, keyed uniforms,
ledgers, corrected results, or runner IPC. An authorized retry reuses the
original private nonce and makes zero new entropy calls; the whole-lifecycle
ledger still contains the one original call.

Every other `os.urandom`/`secrets` callsite or argument and all
`ProjectionRNGRegistry` seed/factory methods, Python `random`, NumPy
`random`/`Generator`/`SeedSequence` entry points, native entropy providers,
and discovered aliases are `forbidden`. At coordinator process entry, only
§10.1's exact provider-call-free pre-wrapper bootstrap prefix and the
immediately following fixed bootstrap-installation sequence may execute
before the complete provider-wrapper set and native audit hook are active.
That installation sequence creates its ledger and cache backing, then the
provider-order wrappers and hook, in the exact §8.1 bootstrap-object order.
Before any action outside that prefix and installation sequence—including
strict registration parsing, a phase transition away from `bootstrap`,
delegated-principal lifecycle activity, correction import, or a provider
call—the complete wrapper set and hook must be active. They remain active
through any same-process authorized retry. Cached aliases, native-library,
FFI, and subprocess bypasses are forbidden by the implementation/source
closure. Candidate code cannot write the ledger. This detects a request for
a fresh generator even though `rng.py` returns a new object per call;
before/after generator-state hashes are not evidence.

The wrappers have exactly two irreversible states:
`active_metering | sealed_deny_all`. After all work permitted to request a
provider is complete on the selected or no-eligible branch, the coordinator
destroys every delegated provider-capable principal (worker, coordinator
delegate, and proposal process), atomically seals the same provider ledger
and keyed-uniform cache created at process entry, and transitions the same
wrapper objects to `sealed_deny_all`. They are never
uninstalled, reset, recreated, or replaced. In deny-all state every entropy,
RNG, midpoint, cached-alias, native, FFI, or subprocess request is rejected
before the underlying provider or cache can be reached. The wrapper
atomically increments both post-seal request and denied counts and sets a
sticky violation flag. Any such request prevents a final-path rename even
though it obtained no random bit. Deny-all remains active through primary
construction, sidecar construction, staging, both renames, incident handling,
and process exit.

After installing the direct no-allocation exit path, initializing phase and
counter state, and completing boundary zero, but before creating a monitored
object, the frozen bootstrap constructs one
`runtime_process_start_identity.v1` object with exactly `schema_version`,
`pid`, `kernel_process_start_time_ns`, `interpreter_descriptor_sha256`,
`runner_descriptor_sha256`, and `orig_argv_sha256`. Each descriptor hash
covers a config-independent live object with exactly `schema_version`,
`absolute_path`, `st_dev`, `st_ino`, `mode`, and `sha256`, using respective
schema literal `live_interpreter_descriptor_identity.v1` or
`live_runner_descriptor_identity.v1`. The path is the concrete absolute live
`sys.orig_argv[0]` or `[5]`; device and inode are positive JSON integers
excluding booleans; mode is a nonnegative JSON integer with an executable
bit; and SHA-256 covers descriptor-read bytes of that non-symlink regular
file. The descriptor hash is SHA-256 of the complete corresponding object,
and the argv hash covers the exact live `sys.orig_argv` string array.
Runtime schema version is the object literal; `pid` and kernel-reported
process start time in nanoseconds are positive JSON integers excluding
booleans. The object and its two live descriptor preimages are captured once
at process entry, before registration parsing, and are unchanged through
incident handling, any authorized retry, sealing, publication, and exit.

After strict registration parsing, the projection of
`invocation.interpreter_identity` having exactly `path`, `st_dev`, `st_ino`,
`mode`, and `sha256` must, after renaming only `path` to `absolute_path`,
deep-equal the live interpreter object's non-schema projection;
`environment_lock_sha256` is checked separately. The projection of
`invocation.runner_identity` having exactly `absolute_path`, `st_dev`,
`st_ino`, `mode`, and `sha256` must deep-equal the live runner object's
non-schema projection; repository-relative path and implementation/`HEAD`
blob OIDs are checked separately during repository proof. Thus no
configuration-dependent value enters the process-entry identity.
`coordinator_process_identity_sha256` wherever used below is exactly SHA-256
of this complete object, never a separately constructed process token.

The serialized `rng_bootstrap_identity_records.v1` object has exactly
`schema_version`, `lifecycle_phase_domain`,
`runtime_process_start_identity`, `rows`, and `canonical_order`. Schema
version is the object literal; the phase-domain member is an exact deep copy
of `rng_access_specs.v2.lifecycle_phase_domain`; and the runtime member is the
complete object above. Every row has exactly `object_kind`, `provider_id`,
`object_instance_id`, `implementation_identity`,
`runtime_process_start_identity`, `creation_phase`, and `creation_sequence`.
Object kind and provider ID exact-match one unique
`rng_bootstrap_implementation_specs.v1` row; `implementation_identity` is a
complete deep copy of that row; the runtime object is an exact deep copy; and
creation phase is literal `bootstrap`. `object_instance_id` is literal
`rng-bootstrap-object:` plus SHA-256 of §10.1 canonical bytes of
`[runtime_process_start_identity,object_kind,provider_id,
implementation_identity,creation_sequence]`.
Rows are exactly one ledger, one cache, one wrapper for each provider in
provider order, and one audit hook, in that order. `canonical_order` is
`ledger-cache-provider-order-wrappers-audit-hook`; no other bootstrap
identity row exists. Every live object retains an immutable identity member
that exact-matches its row, and the coordinator retains its original
non-rebindable reference slot. Every pre-rename check requires reference
identity with that retained slot and rereads the identity projection from the
live object; it never reconstructs identity from the saved row alone.

`rng_lifecycle_sequence_namespace.v1` has exactly `schema_version`,
`event_kind_literals`, `counter_initial_value`, `first_sequence`, and
`canonical_order`. Schema version is that literal. Its event-kind literals
are exactly this ordered JSON array:

```json
[
  "bootstrap_object_creation",
  "delegated_principal_creation",
  "delegated_principal_destruction",
  "delegated_provider_capable_set_empty",
  "provider_lifecycle_seal"
]
```

Counter initial value is JSON integer zero, first sequence is JSON integer
one, and canonical order is `event-sequence`.
Before the first monitored object, the frozen bootstrap constructs the pinned
phase domain, installs the direct no-allocation exit path, initializes the
current-phase state cell and this coordinator-only atomic counter, completes
boundary zero, and only then captures the runtime process identity. These
operations are the exact pre-wrapper bootstrap prefix and do not consume a
sequence.
Every G11-monitored bootstrap-object creation, delegated-principal creation
or destruction, empty-set barrier, and seal consumes
exactly one position; no other event does. Every consumed position is a
positive JSON integer excluding booleans, and the counter never resets across
incident handling or an authorized retry. Bootstrap consumes sequence 1 for
the ledger, 2 for the cache, 3 through \(N+2\) for the \(N\) provider-order
wrappers, and \(N+3\) for the audit hook.

The independently expanded
`provider_capable_principal_role_domain.v1` object has exactly
`schema_version`, `terminal_branch`, `evaluation_completion`,
`execution_attempts`, `rows`, and `canonical_order`. Schema version is that
literal. Terminal branch and evaluation completion are one legal pair below.
`execution_attempts` has
exactly one initial row and, iff the private receipt was successfully consumed
and the retry claim durably reread, one following authorized-retry row. Each
attempt row has exactly `execution_attempt`, `outcome`,
`last_entered_lifecycle_phase`, `last_completed_boundary_id`,
`last_completed_boundary_order`, and `cutoff_evidence_sha256`. Outcome is
`retryable_incident | terminal_branch`; phase is the exact coordinator state
at that boundary; boundary ID/order foreign-key one authority boundary row
whose phase it exact-matches; and the hash covers the exact
`attempt_lifecycle_cutoff_evidence.v1` object. That object has exactly
`schema_version`, `execution_attempt`, `outcome`,
`last_entered_lifecycle_phase`, `last_completed_boundary_id`,
`last_completed_boundary_order`,
`initial_claim_sha256`, `triggering_incident_sha256`,
`receipt_consumption_sha256`, `retry_claim_sha256`,
`locked_terminal_branch`, and `locked_evaluation_completion`. The five
non-schema lifecycle members exact-match the attempt row, and schema version
is the object literal.
Every nonnull hash is 64 lowercase hex. Initial claim is always nonnull.
Incident is nonnull exactly for a retryable initial attempt and the following
retry; receipt and retry-claim hashes are nonnull exactly for the retry.
The locked pair is the eventual legal terminal pair. This cutoff object
expressly excludes `rng_access_results`, the lifecycle seal, primary,
sidecar, and all hashes of those objects, so its hash is noncircular. The
initial outcome is retryable incident exactly when the retry row exists, and
the last row's outcome is terminal branch. A retryable-incident row's phase
and boundary ID/order exact-match the durable incident fields and remain the
pre-`incident_handling` cutoff; later cleanup boundaries do not replace those
cutoff fields. A terminal-branch row's phase is literal `lifecycle_closure`
and its boundary is the
frozen terminal-role-cutoff row for that legal pair, which follows every
applicable role-creation and every normal or selected incident-cleanup
destruction boundary and precedes the delegated-empty-set barrier; it is not
an asserted runtime value. These cutoffs are reconstructed from claims, the
durable incident/receipt/retry-claim evidence, the frozen atomic-boundary
registry, and the locked pair, never from actual lifecycle rows.

Every role-domain row has exactly
`principal_lifecycle_role_id`, `principal_authority_id`,
`execution_attempt`, `instance_coordinates`, `creation_phase`,
`effective_creation_boundary_id`, `effective_creation_boundary_order`,
`destruction_phase`, `effective_destruction_boundary_id`,
`effective_destruction_boundary_order`, and `lifecycle_role_order`. Each row
is the exact projection of one authority `lifecycle_roles` row whose
applicable-pair array contains the actual pair, whose execution attempt occurs
in the attempt array, and whose creation boundary is no later than that
attempt's cutoff; the added authority ID identifies its containing authority
row. Creation phase and effective creation boundary ID/order exactly equal
the template's creation phase and pair.

When the template's normal-destruction boundary is no later than the
attempt's cutoff, destruction phase and effective destruction boundary
ID/order exactly equal its normal-destruction phase and pair. Otherwise the
attempt outcome must be `retryable_incident`, and the effective destruction
pair is the unique `incident_cleanup_boundaries` target selected by that
attempt's exact durable cutoff ID/order; destruction phase is that target
row's literal `incident_handling` phase. A generic incident boundary or a
mapping for any other cutoff is invalid. The filtered role set is complete,
and every other field deep-equals the template. IDs and
authority/attempt/coordinate tuples are unique. The combined array containing
each selected row's effective creation and destruction ID/order pairs has no
duplicate across either event kind, so effective boundary order defines one
total expected event order. Rows are in execution-attempt
order and then lifecycle-role order; canonical order is
`attempt-then-lifecycle-role-order`. Configuration or actual lifecycle events
cannot scope this expected domain or choose an effective boundary.

The serialized `provider_capable_principal_lifecycle.v1` object has exactly
`schema_version`, `principal_authority`, `role_domain`, `rows`,
`expected_principal_lifecycle_event_stream`,
`actual_principal_lifecycle_event_stream`,
`expected_worker_lifecycle_projection`,
`actual_worker_lifecycle_projection`, `canonical_order`, and `status`.
Principal authority is a complete exact deep copy of
`rng_access_specs.v2.provider_capable_principal_authority`, and role domain is
the complete exact object above. The two projections are the complete exact
`g15_worker_lifecycle_projection.v1` objects below. Each row has exactly
`principal_instance_id`, `principal_lifecycle_role_id`,
`principal_authority_id`, `execution_attempt`,
`implementation_identity_sha256`, `creation_phase`,
`effective_creation_boundary_id`, `effective_creation_boundary_order`,
`creation_sequence`, `destruction_phase`,
`effective_destruction_boundary_id`,
`effective_destruction_boundary_order`, and `destruction_sequence`. Role,
authority, attempt, implementation, creation phase, and effective creation
pair exact-match the joined authority and role-domain rows. Creation sequence
is a positive JSON integer excluding booleans. Destruction phase, effective
destruction ID/order, and sequence are either all null or all nonnull. When
nonnull they exact-match the role-domain destruction phase and effective pair,
and sequence is a positive JSON integer excluding booleans greater than
creation sequence; any partial group is invalid.

The coordinator captures the event kind, live principal's immutable role,
authority, attempt, and implementation identities, phase, effective boundary
ID/order, and lifecycle sequence in the same atomic action that completes
that exact registered boundary. It writes the immutable actual event trace
and the corresponding lifecycle-row fields from that capture; neither a
worker report nor an after-the-fact authority copy may populate them. For each
lifecycle row, exactly one same-role `delegated_principal_creation` event and,
when its destruction group is nonnull, exactly one same-role
`delegated_principal_destruction` event must exist in the actual stream. Each
event's sequence, phase, effective boundary ID/order, authority, attempt,
implementation identity, and lifecycle-role order exact-match the
corresponding row side and joined authority; no other event for that role and
kind exists.
`principal_instance_id` is literal `rng-principal:` plus SHA-256 of §10.1
canonical bytes of
`[runtime_process_start_identity,principal_lifecycle_role_id,
principal_authority_id,execution_attempt,implementation_identity_sha256,
effective_creation_boundary_id,effective_creation_boundary_order,
creation_sequence]`. Instance IDs, role IDs, effective boundary pairs, and
sequence positions are unique, and rows are in creation-sequence order.
Schema version is the object literal and canonical order is
`creation-sequence`.

Each of `expected_principal_lifecycle_event_stream` and
`actual_principal_lifecycle_event_stream` is a complete
`provider_capable_principal_lifecycle_event_stream.v1` object with exactly
`schema_version`, `events`, and `canonical_order`. Schema version is that
literal and canonical order is `event-sequence`. Each event has exactly
`lifecycle_sequence`, `event_kind`, `principal_lifecycle_role_id`,
`principal_authority_id`, `execution_attempt`,
`implementation_identity_sha256`, `phase`, `effective_boundary_id`,
`effective_boundary_order`, and `lifecycle_role_order`. Event kind is exactly
`delegated_principal_creation | delegated_principal_destruction`; all
identity and role members exact-match the joined authority/domain row.
Lifecycle sequence is a positive JSON integer excluding booleans. Effective
boundary and lifecycle-role orders are nonnegative JSON integers excluding
booleans; the effective ID/order pair foreign-keys one exact authority
boundary row, and `phase` exact-matches that row.

Let \(B\) be the exact bootstrap-identity row count and \(R\) the exact
role-domain row count. The expected stream independently emits one creation
and one destruction event for every role-domain row, projects phase and
effective boundary pair from the corresponding side of that row, sorts the
complete \(2R\)-event array by effective boundary order, and assigns
`lifecycle_sequence` exactly \(B+1\) through \(B+2R\). The actual stream is
the complete immutable coordinator trace of those event kinds in consumed
lifecycle-sequence order, with no projection from expected rows. The two
complete stream objects must deep-equal, and their §10.1 canonical bytes must
be exactly equal, including array order, sequences, event kinds, and every
event field; hash equality alone is insufficient.

The actual row sequence projected to role IDs must equal the independently
expanded role-domain ID sequence with no missing, extra, duplicate, or
reordered role. Status is `pass` iff that equality, exact expected-versus-
actual event-stream equality, and every authority, implementation, attempt,
phase, effective-boundary, nullability, identity, uniqueness, and ordering
law above passes, every destruction group is nonnull, and each of the two
embedded G15 projections below independently satisfies its exact schema and
derivation law; it is `fail` otherwise. Equality of those two valid
projections is adjudicated only by correction gate G15. A null destruction
group therefore remains a coordinator-retained nonpublication failure
preimage but prevents the empty-set barrier, seal, and primary. Reversing two
same-phase destructions changes actual event order/sequence, and recording a
wrong same-phase creation boundary changes the event payload; neither can
serialize as the expected stream.

`g15_mount_epoch.v1` has exactly `schema_version`, `mount_epoch_id`,
`mount_allowlist_id`, `mount_allowlist_sha256`, `descriptor_allowlist_id`,
`descriptor_allowlist_sha256`, `ipc_schema_ids`, `ipc_schemas_sha256`,
`opened_phase`, `closed_phase`, and `mount_trace_sha256`. Schema version is
that literal. IDs and authority hashes exact-match the principal's joined
code-identity row; the IPC ID array is an exact deep copy; phases exact-match
the joined role's creation and destruction phases; and the trace hash is 64
lowercase hex. A principal with no mount, descriptor, or IPC grant uses
literal `mount_allowlist_id: none` and `descriptor_allowlist_id: none`; each
corresponding hash is the canonical hash of its complete empty registry;
`ipc_schema_ids` is the empty array, `ipc_schemas_sha256` is the canonical
empty-array hash, and its trace hash is the canonical empty-trace hash.
Regardless of grant contents, `mount_epoch_id` is always literal
`g15-mount-epoch:` plus
SHA-256 of §10.1 canonical bytes of
`[principal_lifecycle_role_id,mount_allowlist_id,
mount_allowlist_sha256,descriptor_allowlist_id,
descriptor_allowlist_sha256,ipc_schema_ids,ipc_schemas_sha256,
opened_phase,closed_phase,mount_trace_sha256]`.

`g15_worker_lifecycle_projection.v1` has exactly `schema_version`, `rows`,
and `canonical_order`. Schema version is that literal and canonical order is
`role-domain-order`. Each row has exactly
`principal_lifecycle_role_id`, `principal_authority_id`,
`execution_attempt`, `implementation_identity_sha256`, `creation_phase`,
`destruction_phase`, and `mount_epoch`, in role-domain order. Expected rows
join the independently reconstructed authority and role domain to the frozen
allowlist/IPC identities and copy the code row's expected mount-trace hash;
actual rows project those same fields from the complete principal lifecycle
and actual mount/descriptor/IPC audit. Each `mount_epoch` is the complete
exact object above.
For each expected epoch, `mount_trace_sha256` equals the joined
code-identity row's `expected_mount_trace_sha256`; for each actual epoch, it
equals the independently audited trace hash for that runtime principal.

The lifecycle object's `expected_worker_lifecycle_projection` and
`actual_worker_lifecycle_projection` are those respective complete preimages
and are each independently schema-valid and reconstructible. Their canonical
hashes are, respectively, G15's `expected_worker_lifecycle_sha256` and
`actual_worker_lifecycle_sha256`; G15 alone requires their hashes and rows to
equal for the correction. It references these serialized G11 objects and
cannot substitute its own summary. G11 separately validates runtime instance
IDs, effective boundary placement, and exact expected-versus-actual event
streams. No separately summarized provider-capable lifecycle is permitted.

The coordinator serializes the branch-general
`rng_provider_lifecycle_seal.v1` object with exactly `schema_version`,
`terminal_branch`, `evaluation_completion`,
`lifecycle_sequence_namespace`, `bootstrap_identity_records`,
`provider_capable_principal_lifecycle`,
`provider_ledger_identity_sha256`,
`keyed_uniform_cache_identity_sha256`, `wrapper_registry_sha256`,
`wrapper_object_identities_sha256`,
`audit_hook_identity_sha256`,
`provider_capable_workers_destroyed_phase`,
`provider_capable_workers_destroyed_sequence`, `seal_phase`, `seal_sequence`,
`provider_ledger_sha256`, `keyed_uniform_cache_sha256`, `wrapper_state`,
`post_seal_request_count`, `post_seal_denied_count`,
`post_seal_denial_trace_sha256`, `sticky_violation_count`,
`pre_rename_recheck_sha256`, and `status`.
Schema version is the object literal and status is `pass | fail`.
For a correction run, `terminal_branch` is exactly
`selected_correction | no_eligible_candidate`; the only legal
terminal-branch/evaluation-completion pairs are
`selected_correction/complete`,
`selected_correction/preheldout_structural_gate_fail`, and
`no_eligible_candidate/no_eligible_candidate`.
`lifecycle_sequence_namespace` is the complete exact
`rng_lifecycle_sequence_namespace.v1` object; `bootstrap_identity_records` and
`provider_capable_principal_lifecycle` are the complete exact objects above.
`provider_ledger_identity_sha256` hashes the sole ledger-kind bootstrap row,
`keyed_uniform_cache_identity_sha256` hashes the sole cache-kind row,
`wrapper_object_identities_sha256` hashes the complete provider-order array
of wrapper-kind rows, and `audit_hook_identity_sha256` hashes the sole
hook-kind row. Every hash uses §10.1 canonical bytes. The ledger/cache
identities must be unchanged from process entry through any authorized retry.
`wrapper_registry_sha256` hashes the canonical object having exactly
`providers` and `bootstrap_implementation_specs` copied from
`rng_access_specs.v2`.
All four identity projections and the complete bootstrap object must be
unchanged from bootstrap through pre-rename recheck.

The union of every bootstrap `creation_sequence`, every principal creation
and destruction sequence, `provider_capable_workers_destroyed_sequence`, and
`seal_sequence` is exactly the contiguous positive integer range
`1..seal_sequence`, with no duplicate. If \(B\) is the bootstrap row count and
\(R\) is the role-domain row count, the exact principal event-stream
sequences are \(B+1..B+2R\), the destroyed sequence is \(B+2R+1\), and
`seal_sequence` is \(B+2R+2\). The destroyed sequence is the
`delegated_provider_capable_set_empty` barrier after the last non-root
principal destruction; its phase and `seal_phase` are both literal
`lifecycle_closure`. The still-live root coordinator is not a principal row.
At the barrier it atomically revokes its ordinary direct-provider and cache-
request capability and enters `seal_only`; that state can perform only the
immediately following atomic seal and cannot obtain provider or cache output.
`seal_sequence` is exactly one greater than the barrier sequence and is
consumed by the ledger/cache seal plus wrapper transition, with no
intervening lifecycle event. The live ledger's `seal_sequence` exact-matches
it. No delegated provider-capable principal may be created after the barrier,
and the root can never leave `seal_only`. The two state hashes cover the
complete corresponding objects at that point. Wrapper state is
`sealed_deny_all`. The two post-seal counts are actual nonnegative JSON
integers, denied count must equal request count, and sticky violation count is
the JSON integer 0 or 1.
`post_seal_denial_trace_sha256` hashes the complete ordered array of denied
request rows, each having exactly `request_sequence`, `provider_id`,
`callsite_identity`, `argument_sha256`, `phase`, and literal
`disposition: denied_sealed`. `request_sequence` is contiguous from one in
post-seal interception order and phase foreign-keys the exact current
`rng_lifecycle_phase_domain.v1` state. The trace is the canonical empty-array
hash when both counts are zero.

Provider-call `event_sequence`, post-seal `request_sequence`, broker
`exposure_sequence`, and receipt `pop_sequence` are distinct counters from
`rng_lifecycle_sequence_namespace.v1` and from one another. Their values are
never compared, merged, or used to fill a lifecycle-sequence gap.
Authority `boundary_order` is likewise distinct from every counter. It
determines expected principal-event order, but its selected-path values need
not be contiguous and never substitute for `lifecycle_sequence`.

`pre_rename_recheck_sha256` hashes the canonical object containing all seal
fields except `schema_version`, itself, and `status`. The coordinator
constructs that comparand at seal and reconstructs it from the still-live
objects immediately before the first rename, after both staged files exist.
Final status is `pass` iff: the terminal branch/completion pair is legal; the
bootstrap object exact-matches the pinned expected object and every live
ledger/cache/wrapper/hook identity still deep-equals its creation row; the
principal lifecycle passes, including each embedded expected/actual
projection's independent schema and derivation checks and the complete
expected and actual principal event streams deep-equal; every phase/role/
effective-boundary tuple is allowed; every lifecycle sequence is a positive
non-boolean integer and the complete union is exactly `1..seal_sequence` with
no duplicate and the barrier immediately before the seal; the live ledger's
seal sequence, ledger/cache state hashes, and wrapper state exact-match;
request, denied, and sticky values are zero and the denial trace is the
canonical empty-array hash; and the immediate pre-rename reconstruction
equals the sealed comparand with no intervening callback. Status is `fail`
otherwise. Failure to destroy a principal, prove the empty set, or perform
the atomic seal is an invariant incident and permits no primary; any other
mismatch permits neither rename.

`keyed_uniform_registry.v1` is independently expanded from the complete
derived ledger support, every registered `coverage_state_group_id`, the sole
`coverage_status` variate, correction draws 0–19, and residual counter zero.
Each row has exactly the §5.4 namespace fields and
`uniform_ieee754_binary64_hex`, in lexicographic namespace order. Missing,
extra, duplicate, or reordered keys fail. Its canonical SHA-256 is named
`keyed_uniform_registry_sha256` in every exact schema and the
noninterference bundle; any shortened alias is schema-invalid. It is not a
worker-reported list.

`weight_rescale_specs.v1` is exactly four objects with keys
`comparison_id`, `bundle_schema`, `required_fields`,
`base_weight_multiplier`, and `rescaled_weight_multiplier`: one for each
candidate and one selection/tie/model/ledger row. A
`weight_rescale_candidate_bundle.v1` has exactly `schema_version`,
`candidate_id`, `non_weight_candidate_input_packet_hashes`,
`survey_weight_domain_identity`, `registered_objective_weight_identity`,
`parameter_vector`,
`model_choice_predictions`, `model_choice_losses`,
`identification_result`, and `candidate_disposition`. The fourth
`weight_rescale_selection_bundle.v1` has exactly `schema_version`,
`candidate_bundle_hashes`, `candidate_dispositions`,
`selected_candidate_id`, `selection_result`, `tie_result`,
`registered_survey_weight_identity`,
`registered_objective_weight_identity`, `model_identity`,
`substantive_model_sha256`, `expected_ledger_identity`,
`realized_ledger_identities`, and `claim_context_gap_identity`.
Its candidate hashes have exactly three rows in candidate order and its
realized array has exactly the canonical 400-draw registry. The
`required_fields` arrays are these exact key sets in the stated order; no
sub-bundle or digest chosen by the implementation is accepted.

The multipliers are the exact values represented by binary64 `1.0` and
`7.0`. The coordinator, not candidate code, supplies identical non-weight
semantic packets twice and applies the multiplier to the complete PSID
**survey-weight** vector. The complete vector is independently expanded from
the correction-bound PSID roster, the registered survey-weight field, and
every production/evaluation support key; configuration cannot omit a person,
wave, role, direct/gap/boundary/projected row, zero earner, or difficult row.
Every target `loss_weight`, dependency-group/family subweight, tolerance, and
other objective/selection weight remains bit-identical between executions.
The registered survey-weight identity and the separately named canonical
production target-ID/objective-weight identity both remain unchanged in model
serialization; the `7.0` multiplier is gate evidence only. Both executions
therefore serialize against the same production identities after
independently fitting their supplied survey-weight packets.
Registration also proves every positive-weight target is a share, ratio, or
intensity and the broker's level-target grant ledger is empty. G14 passes iff
all four complete canonical bundles match, thereby proving parameter,
prediction, loss, identification, disposition, selection/tie, model, and
expected/400-ledger invariance without pretending the test packet is a new
production configuration.

Each execution also emits a coordinator-owned
`psid_survey_weight_packet.v1` with exactly `schema_version`,
`comparison_id`, `survey_weight_field`, `survey_weight_domain_sha256`,
`row_count`, `rows`, and `multiplier_ieee754_binary64_hex`. Rows are in the
complete independently derived stable weight-key order and each has exactly
`weight_key` and `survey_weight_ieee754_binary64_hex`; the latter is the
positive finite source-weight bit pattern. Base and rescaled packets have
identical rows and respectively the multiplier bits for `1.0` and `7.0`.
The trusted weighted-statistic law decodes each survey weight and the common
multiplier as exact dyadic rationals and applies the multiplier symbolically
before §7.1's exact rational accumulation. It does not serialize a separately
rounded binary64 `7*w_i`, so per-row multiplication rounding cannot create a
false scale effect. Every actual survey-weight read must be traced to exactly
one packet row and the same packet multiplier.

Expected/actual packet hashes, complete broker grant hashes, and the
elementwise weight-key/multiplier trace are G14 evidence outside the equality
bundle and outside `model_identity`; packet hashes are expected to differ
between 1× and 7× and are never compared with each other. The equality
bundle's survey-weight-domain identity binds the common field, ordered keys,
and base bits but excludes only the test multiplier. A second 1× run, a
target-loss-weight rescale, an ignored multiplier, a rounded effective-weight
substitution, a missing survey row, or an unproved packet therefore fails
even if its output bundle happens to match.

`filesystem_isolation_specs.v1` has exactly `schema_version`,
`isolation_backend`, `worker_code_identities`, `mount_allowlists`,
`descriptor_allowlists`, `ipc_schemas`, `broker_grant_registry`,
`forbidden_identity_registry`, `audit_policy`, `assertions`, and
`failure_disposition`. Its provider-capable worker/coordinator-delegate/
proposal-process projection of `worker_code_identities` has exactly the §8.1
`provider_capable_principal_authority.v1.code_identity_rows` schema and deep-
equals that independently reconstructed array; non-provider identities remain
in the broader G15 registry but cannot enter the G11 authority.
`assertions` is the exact nonempty ordered array:

```json
[
  "fit_worker_mount_allowlist",
  "selector_worker_mount_allowlist",
  "descriptor_allowlist",
  "broker_grant_exactness",
  "heldout_path_denied_before_lock",
  "vintage1_and_anchor_path_denied",
  "repository_data_runs_docs_denied",
  "network_denied",
  "subprocess_denied",
  "late_open_and_import_denied",
  "path_and_content_alias_denied",
  "fit_heldout_worker_lifecycle_nonoverlap",
  "trusted_consumer_evaluator_mount_allowlist",
  "runner_proposal_one_way_ipc",
  "trusted_evaluator_context_decoder_lifecycle_nonoverlap"
]
```

Each assertion resolves to one mandatory result row and an exact frozen worker
or worker-group ID; none may be dropped because a backend lacks an audit
facility. One fresh fit worker per candidate and a separate selector worker
see only preloaded cell-scoped packets and pinned runtime libraries;
repository `data`, `runs`, and `docs` are not mounted, non-IPC descriptors
are closed, and network, subprocess, late import, `open`, `os.open`,
`pathlib`, symlink, hardlink, and inherited-descriptor bypasses are denied.
The exact broker/IPC schema admits only the coordinator-classified component
output from §4.1; a `required_micro_facts` presence flag, raw/typed fact
value, alternative affected-record key, or runner classification override is
an extra field and fails `broker_grant_exactness`.
Zero-weight diagnostics run separately; the held-out evaluator is created
only after all replay/rescale/fit-capable workers are destroyed. An
unavailable isolation or audit backend aborts registration. The trusted
consumer evaluator receives only the five typed §8.1 stream kinds; proposal
IPC is runner→coordinator and cannot carry source, graph, or result authority
back to the runner; and the evaluator's proposal channel, process, mounts, and
descriptors are destroyed before a context decoder can exist.

`g15_broker_sandbox_evidence.v1` has exactly `schema_version`,
`expected_broker_grant_registry_sha256`, `actual_broker_grant_ledger_sha256`,
`registered_ipc_schemas_sha256`, `actual_ipc_trace_sha256`,
`physical_source_structure_projection_sha256`,
`trusted_consumer_semantic_authority_sha256`,
`trusted_consumer_semantic_comparison_sha256`,
`trusted_consumer_graph_specs_sha256`,
`trusted_consumer_root_streams_sha256`,
`expected_worker_lifecycle_sha256`, `actual_worker_lifecycle_sha256`,
`isolation_results_sha256`, and `forbidden_access_count`. The first two
hashes compare the complete independently derived grant arrays, the next two
compare every typed worker/coordinator message and direction, the structural
hash is the complete value-blind
ancestry/alias/exact-or-structural-dependence projection above,
the next four hashes bind the reconstructed semantic authority, its exact
zero-mismatch comparison, the configured typed graph comparand, and actual
trusted root streams; and the lifecycle hashes cover the respective complete
objects embedded as
`provider_capable_principal_lifecycle.v1.expected_worker_lifecycle_projection`
and `actual_worker_lifecycle_projection`. The last value is the actual
aggregate nonnegative count. G15 passes iff both
grant arrays and both IPC traces exact-match, the expected and actual
lifecycle projection hashes and rows are equal, all 15 isolation rows pass,
all four trusted-consumer hashes and the structural projection independently
recompute, and forbidden count is zero. Unequal hashes/counts remain
serializable failure evidence.
No mutable token, value, full-source digest, or evaluation-provenance hash is
in this gate evidence object.
G15/G17 validate every sibling's topology, year, source-definition locator,
`assertion_scope`, and `numeric_validation_law`. They evaluate displayed
numbers only for `exact_published_value_equality`; a structural-only residual
is retained as data and can neither fail nor satisfy an exact-equality test.

The executable selector/comparator map is:

| Gate | `evidence_selector` | `comparator` / `required_value` |
|---|---|---|
| G01 | `independently_derived_consumer_domain_and_support_results` | `exact_derived_domain_law / true` |
| G02 | `final_component_domain_scan` | `all_records_true / true` |
| G03 | `se_loss_offset_trace` | `all_records_true / true` |
| G04 | `atomic_and_person_year_reconciliation_residuals` | `all_exact_zero / true` |
| G05 | `unknown_disposition_trace` | `all_records_true / true` |
| G06 | `coordinator_legal_rule_microfact_action_trace` | `exact_bound_fact_derived_microfact_domain_presence_premise_and_action_fold / true` |
| G07 | `wage_first_combined_cap_trace` | `all_records_true / true` |
| G08 | `benefit_revenue_component_hash_pairs` | `all_hash_pairs_equal / true` |
| G09 | `recoverable_provenance_scan` | `all_records_true / true` |
| G10 | `replay_registry_results` | `exact_six_rows_all_hashes_equal / true` |
| G11 | `trusted_rng_provider_call_ledger_and_lifecycle_seal` | `exact_keyed_calls_nonce_exception_forbidden_zero_event_stream_sealed_deny_and_prerename_recheck / true` |
| G12 | `information_cutoff_and_claim_context_gap_evidence` | `all_records_true / true` |
| G13 | `semantic_field_registry_scan` | `all_records_true / true` |
| G14 | `trusted_survey_weight_rescale_reexecution_results` | `exact_four_survey_weight_rows_all_bundles_equal / true` |
| G15 | `broker_sandbox_ipc_structural_closure_evidence` | `exact_grants_ipc_ancestry_alias_lifecycle_and_forbidden_zero / true` |
| G16 | `unresolved_policy_and_disclosure_scan` | `all_records_true / true` |
| G17 | `inventory_crosswalk_lineage_and_required_cell_closure` | `exact_fifteen_domains_counts_and_hashes_equal / true` |
| G18 | `nonlinear_draw_reduction_trace` | `all_records_true / true` |
| G19 | `selected_identification_and_candidate_dispositions` | `all_records_true / true` |
| G20 | `draw_prefix_stability_results` | `all_tolerances_pass / true` |
| G21 | `heldout_noninterference_pre_g21_equality` | `acyclic_prebundle_mutation_domain_and_provenance_predicate / true` |
| G22 | `complete_consumer_dependency_and_trusted_evaluation_results` | `exact_reconstructed_source_domain_rule_unit_root_authority_paths_proposal_and_result_bytes / true` |

The selector strings are reserved result-builder entry points; each emits a
canonical evidence object whose SHA-256 is recorded in the hard-gate row.
Changing a selector, comparator, or required value is a gate-registry version
change and requires fresh registration.

For G21 comparison only, every G01–G10/G12–G20/G22 evidence selector uses its frozen
substantive projection: complete outputs, counts, stable support keys,
structural locators/relations, comparator inputs, and actual comparator
outcome remain; decoded target values, diagnostic residuals, cell-token and
full-source digests, configuration/full-manifest digests, and evaluation
provenance are excluded. G15 uses the exact object above and G17 uses the
inventory/crosswalk lineage plus `physical_source_structure_projection.v1`,
not value-bearing physical IDs. The production report still retains the full
provenance and unfavorable evidence outside these gate preimages. A selector
whose normalized projection drops a substantive parameter, prediction,
loss, ledger byte, support key, access event, dependency path, or comparator
outcome is invalid; this is value-blind evidence, not outcome-only evidence.
For G17 specifically, the lineage projection is the exact
`g17_inventory_crosswalk_evidence.v1` shape. Its fifteen
expected/actual hash preimages bind every inventory and component key,
questionnaire/source locator, disposition, consequence, attachment,
direct-law purpose/fact/predicate/presence/action row, rule foreign key,
verification result, structural source relation, and comparator outcome,
while replacing evaluation-only source/content digests with their stable
locator identities. A model-choice source fragment remains bound unchanged in
`substantive_model_sha256`; an exclusive held-out/zero-weight digest remains
in full evaluation provenance. Thus the projection cannot hide a missing
field or changed disposition, and an evaluation-only byte cannot change
G17's G21 evidence hash.

### 8.2 Empirical evaluation

Hard correctness is necessary but not sufficient. The complete evaluation
also publishes:

- every train and validation target, prediction, residual, loss, tolerance,
  and pass/fail result;
- held-out target diagnostics only after selected-model bytes are locked;
- wage/SE composition, zero/positive incidence, quantiles, tail shares, cap
  exposure, unresolved shares, and modeled covered-worker incidence;
- corrected taxable payroll, contributions, top-35 composition, AIME, and
  PIA plus separately typed legacy `before_context` levels, reduced in the
  registered order without using legacy values as corrected operands; and
- Option C in a visually and structurally separate, explicitly noncorrected
  sub-block of `before_context_results`.

`evaluation_specs.v1` is an ordered expanded array. Each object has exactly
`metric_id`, `result_block`, `source_fields`, `population_selector`,
`weight_field`, `stratum_id`, `reference_era_id`, `year_source_class`,
`role`, `calendar_year`, `operative_claim_year`, `career_variant_id`,
`statistic`, `unit`, `draw_reduction`, `stability_family`, and `gate_role`.
Expansion order is the family order below, listed source-field order, listed
statistic order, overall then reference-era × source-class × role strata,
ascending verified reference year, and the independently derived applicable
benefit-context order. IDs are the colon-joined components of that position,
including the literal `none` for a null context coordinate, so two claim
contexts cannot share a metric ID. Every registered combination has a row
even when its count is zero.

For an annual corrected row, `year_source_class` is the exact §4.2 literal.
Every `structural_gap_imputed | claim_specific_boundary_gap` annual row is a
benefit-context row and has nonnull `operative_claim_year` and
`career_variant_id` copied from the independently derived gap domain; those
coordinates are null only where that domain declares them inapplicable.
In particular, every annual 2013 row is
`claim_specific_boundary_gap`, is expanded once per applicable operative
claim/career coordinate, and has both coordinates nonnull. There is no
unconditional/general-population or revenue 2013 metric. An annual family
that cannot be evaluated in that benefit context omits 2013 from its
independently registered domain rather than synthesizing a base row. A
nonannual career row has `calendar_year`, `year_source_class`, and both
context coordinates null.

The table's `annual_provenance_context_expansion` is the exact ordered
domain of direct-questionnaire annual positions for 1968–1996 and the
registered even years through 2012; every independently derived
operative-claim/career position for each 1997–2011 structural gap and the
2013 claim-specific gap; the 2014 boundary; and projected 2015–2022. Every
corrected annual family below uses this complete expansion. Thus 2013 is
present for each applicable benefit context in every listed corrected annual
family, but never as an unconditional or revenue row. The Option-C branch of
`before_context` separately imports the same expansion under §7.4; the
frozen-legacy branch retains only its predecessor-declared diagnostic domain.

| Family | Exact expansion |
|---|---|
| `composition` | Wage share and SE share of nonnegative covered gains; complete `annual_provenance_context_expansion` and all registered reference-era×source-class×role aggregates. |
| `incidence` | Positive wage, positive SECA base, modeled covered worker, and combined-cap exposure weighted shares; the same complete annual/context expansion and strata. |
| `distribution` | Weighted `p10,p25,p50,p75,p90,p95,p99` and top-`10,5,1` percent amount shares for `covered_employee_wages_uncapped`, `covered_seca_base_uncapped`, and `oasdi_person_taxable_payroll`; complete `annual_provenance_context_expansion`. Stable-person ID breaks weighted-quantile boundary ties. |
| `unresolved` | Weighted gain amount, SE-loss magnitude, and person-year incidence shares; complete `annual_provenance_context_expansion` and every reference-era×source-class×role aggregate, plus mean status entropy over modelable records. |
| `downstream_annual` | Corrected taxable payroll, modeled contributions under frozen rates, and analytic covered-worker-incidence levels; complete `annual_provenance_context_expansion`. |
| `downstream_career` | Corrected AIME, PIA, and top-35 membership-composition levels; `calendar_year: null`, overall registered career universe only. |
| `before_context` | Tagged union: Option C uses the complete annual/context expansion under §7.4, while frozen legacy proxy taxable-payroll, AIME, PIA, and top-35 rows retain their predecessor-declared domain; diagnostic-only, never a corrected metric operand, gate input, selection input, or certificate input. |

`population_selector`, weight, roles, and rate fields are literal references
into registered input/crosswalk objects, not implementation defaults.
Proxy-baseline fields are permitted only in the `before_context` family.
Every corrected `evaluation_specs.v1` row resolves to exactly one §8.1
`consumer_semantic_recipe_specs.v1` row and reconstructed
`root_authority_schemas` row: its `metric_id`, `source_fields`, `statistic`,
unit, reduction, and registry position must all select the same recipe, whose
source roles and steps independently determine the required source bindings,
opcode chain, and rule bindings, including the same-named
quantile/top-share rule. The configured root is accepted only after that
complete closure matches. The coordinator constructs the result from the
authoritative root and bit-compares the published decimal with the root's
summary bits. A runner
proposal is only mismatch evidence and never a result source. Statistics use exact rational
accumulation and stable-key weighted algorithms. `draw_reduction` is
`analytic_linear_within_projection_draw` for a linear annual quantity,
`analytic_joint_state_within_projection_draw` for an annual composition,
incidence, SE-threshold, wage-first-cap, taxable-payroll, contribution, or
worker-indicator statistic under §§3.1–3.2, and
`projection_cross_correction_draw` for every distribution quantile, tail
share, and nonlinear career statistic. The typed legacy family alone uses
`fixed_legacy_before_context`. Each mode publishes the mean and sample SD
under §5.4's exact projection/correction reduction law, except that the fixed
legacy mode copies the frozen predecessor statistic and its registered
uncertainty without a correction draw. Applying
an annual threshold or cap to marginal expected components, computing a
quantile of expected person amounts, or reducing before the complete
within-draw statistic is forbidden. `stability_family` is exactly one §5.4
unit family for every `projection_cross_correction_draw` metric and
`not_applicable` otherwise. The legacy mode always has
`stability_family: not_applicable` and `gate_role: diagnostic_only`.
`gate_role` is `G20` exactly for corrected correction-draw metrics and
`diagnostic_only` otherwise. Any omitted expansion row is failure.

Every modeled covered-worker incidence and certified denominator in this
registry uses `modeled_covered_worker_probability_analytic` within projection
draw and verified calendar year. `modeled_covered_worker_draw_indicator` and
`modeled_covered_worker_draw_grid_fraction_20` remain diagnostics only and
are forbidden from corrected model metrics, pairings, comparison specs, and
certificate inputs.

A complete, valid empirical failure is a publishable result, not an incident
and not a retry opportunity.

The correction evaluation does not open or publish any vintage-1 comparison.
Only §12's separately registered context report may publish the frozen
before/after context ratios, with no required direction.

### 8.3 Circularity prohibitions

The following dataflows are invalid, not merely caveats:

- fitting reported taxable earnings and “validating” on gross contributions;
- fitting payroll and worker counts and validating their ratio;
- treating reported earnings and adjusted payroll as independent evidence;
- treating OASDI net trust-fund cash as earnings-year contributions;
- using benefit totals to tune earnings despite claiming/population
  mismatches;
- using the same literature bounds as priors and validation criteria;
- selecting a candidate, threshold, correction draw, or seed after viewing a
  held-out value;
- placing a whole-document/artifact digest whose byte domain contains
  held-out or zero-weight cells into the substantive model/RNG identity;
- reintroducing a held-out or later-year primitive through a logical alias,
  cross-vintage republication, shared denominator, exact arithmetic sibling,
  or structural-formula sibling;
- leaking realized 2017–2023 PSID job facts into the 2015–2022 projection;
- calling PSID-internal prediction administrative validation;
- double-weighting B2 and B11 exact or structural siblings; or
- allowing Option C or a post-hoc scalar to rescue a failed production
  candidate.

## 9. Evidentiary labels and the label-retirement certificate

### 9.1 Exact certificate conditions

The `first_estimates_report.md` §3.4 proxy label retires only after a
two-artifact proof and an external merge event. The correction evaluation
first derives preconstruction conditions 1–6:

1. the immutable legal, verification-claim, source-inventory, crosswalk,
   structural-missing, direct-law fact-binding/derived-microfact/
   presence/premise/action,
   value-code/annualization/reconciliation/job-match/
   SE-aggregation/coverage-group, wave/reference-lineage, gap-derivation,
   physical-cell/alias/arithmetic, legal-rounding,
   trusted-consumer source/domain/rule/unit/root semantic authority, typed
   evaluator, and exact proposal-packet schema,
   ledger-schema/dependence (including the independently frozen consumer
   source-field schemas and semantic recipes), target, candidate, selection,
   draw, replay, RNG,
   isolation, domain, dependency, gate, and evaluation registries exact-match
   their registered bytes;
2. the common base ledger and operative-claim-year gap views exactly support
   the independently reconstructed complete Stage A–D benefit and unsplit
   revenue domains;
3. all 22 §8.1 hard gates and every registered model-choice validation
   tolerance pass;
4. on a selected branch, `substantive_model_sha256` was locked before
   held-out release and its cell-scoped ancestry contains no vintage-1 or
   post-2014 primitive; on either selection branch, including
   `no_eligible_candidate`, the complete held-out/zero-weight/exclusive-byte
   mutation battery passes without changing a parameter, disposition,
   selection branch, or branch-tagged selected-model projection;
5. all raw inputs, deltas, source classes, status probabilities/draws,
   reasons, claim-context gap neighbors, and component outputs are recoverable
   and reconcile;
6. the exact six-row replay registry, row-order invariance, provider-call RNG
   isolation and branch-general lifecycle seal/deny evidence,
   cutoff-before-imputation, sandbox access, analytic-denominator, and
   nonlinear-draw laws pass.

Only after those six conditions and all noninterference bundle hashes are
frozen does the trusted finalizer prove postconstruction condition 7:

7. the sealed §10 coordinator has constructed and validator-accepted complete
   primary and sidecar bytes, with the primary binding the exact sidecar hash,
   before either final-path rename; both files bind the complete
   selected-or-no-eligible G11 seal and pre-rename recheck comparand, and the
   live wrappers/ledger/cache exact-match that comparand with zero sticky
   violation immediately before the first rename.

The preconstruction object and the final
`correction_model_eligibility.v2` wrapper are exactly those in §§6.2 and
10.2. A `pass` correction report has conditions 1–6 and condition 7 all
`pass`.
That object is not a label-retirement certificate and cannot change a
published label or prove that both final paths now exist. A `gate_fail` or
`no_eligible_candidate` report emits it with `eligible: false`; on the latter,
condition 4 remains evaluated from G21 rather than disappearing with the
selected-model blocks.

The separately registered context report then proves condition 8:

8. after correction-model lock it independently reconstructs the complete
   frozen corrected model-metric domain, all 14 pairings, and all nine
   comparison specs; rebuilds the §8.1 source/domain/rule/unit/root semantic
   authority anew from the correction-bound underlying registries without
   trusting the correction's configured graph or stored authority hash;
   rematerializes and hash-checks every applicable common ledger and
   claim-context gap stream; computes every corrected earnings-dependent
   metric through those authoritative typed chains and exact-compares the
   complete schema-valid runner proposal, locks every authoritative corrected
   root and dependency proof, and destroys every runner-proposal capability;
   confines every evaluable legacy/raw-proxy numeric path to the typed
   `before_context` block;
   transforms both `pairings[*].mismatch_codes` and
   `comparison_specs[*].mismatch_codes` positionally while retaining successor
   registry-row cardinality/order and every unaffected field; mismatch-array
   contents and cardinality obey only §9.2's suppression law; uses analytic modeled-worker
   probabilities for every certified denominator; meters the complete
   context RNG/provider lifecycle under the pinned nonce/keyed/forbidden law;
   only after the corrected roots are locked and every runner-proposal
   capability is destroyed grants the separate context decoder access to all
   15 vintage-1 series and computes every registered context row;
   after all context computation destroys every delegated provider-capable
   context principal at its effective authority boundary, exact-compares the
   complete expected and actual principal event streams, consumes the
   `delegated_provider_capable_set_empty` barrier, seals the same ledger/cache,
   enters irreversible deny-all mode, freezes the complete whole-lifecycle
   RNG evidence, and constructs, validates, and stages the complete
   primary/sidecar candidates;
   immediately before the first rename reconstructs semantic authority from
   the frozen registries, exact-compares every constituent, and
   reevaluates/bit-compares every branch-reachable authoritative root and
   corresponding staged primary field; reconstructs the provider-lifecycle
   comparand from the live bootstrap objects and exact-rechecks it with zero
   post-seal/sticky counts and no intervening callback; then publishes every
   required row regardless.

A validator-passing context report that pins the eligible correction artifact
emits `label_retirement_certificate.status` equal to the literal
`eligible_on_publication_pr_merge`. It cannot attest to its own merge and is
not yet active. Condition 9 is the external event:

9. the publication PR containing that exact context report, its
   integrity-bound sidecar, and the conditional certificate merges.

Only that merge changes the certified successor labels. Before it, the
ordered legacy labels remain in force. Any failed condition produces and
publishes the complete applicable failure-tagged result, never a positive
certificate; §11.2 is the only permitted narrowing if full support cannot be
certified.

### 9.2 Exact mismatch-code disposition

“Retired” means inapplicable to new certified corrected metrics. It never
deletes or edits a vintage-1 code. The exact retired array is:

```json
[
  "psid_labor_income_proxy_history_vs_administrative_covered_earnings_history",
  "labor_income_proxy_vs_reported_taxable_earnings",
  "labor_income_proxy_vs_taxable_earnings",
  "labor_income_proxy_vs_adjusted_taxable_payroll",
  "negative_proxy_no_zero_floor"
]
```

The first code is included even though it does not begin with
`labor_income_proxy_`; benefit-side label retirement would otherwise be
incomplete.

The exact `replacements` object is:

```json
{
  "positive_proxy_vs_trustees_covered_workers": "modeled_coverage_vs_trustees_covered_workers",
  "positive_proxy_vs_workers_with_taxable_earnings": "modeled_coverage_vs_workers_with_taxable_earnings"
}
```

The exact `new_codes` array is:

```json
[
  "modeled_covered_earnings_not_individual_administrative_truth"
]
```

The certified model side is only the fixed-frame weighted sum

\[
\sum_i w_i\,
\texttt{modeled\_covered\_worker\_probability\_analytic}_{i,d,y}
\]

formed within each projection draw and verified calendar year, then reduced
under §5.4's ratio-then-mean law. Draw indicators and the 20-draw grid
fraction are diagnostic-only and forbidden here. The official side keeps its
publication universe. The legacy metric is retained only as
`positive_proxy_earner_count` in `before_context`; the corrected metric is a
separate `modeled_covered_worker_count`.

The successor transformation runs independently and position-exactly over
both complete frozen registry families:
`pairings[*].mismatch_codes` in all 14 pairing rows and
`comparison_specs[*].mismatch_codes` in all nine comparison rows. Scan each
array once from left to right:

1. at the first occurrence of any of the first four retired proxy codes
   above, emit
   `modeled_covered_earnings_not_individual_administrative_truth`; suppress
   any later occurrence from that four-code set in the same array;
2. suppress `negative_proxy_no_zero_floor` without replacement;
3. replace either positive-proxy code in place by its exact value in
   `replacements`; and
4. emit every other code unchanged in its original position.

Duplicate output codes are invalid. The successor pairing and comparison
registries retain exact input cardinality/order and deep-copy every unaffected
field. A missing difficult row is failure, not a smaller domain. This
produces every successor mask deterministically from both frozen registries
and makes the new
modeled-earnings limitation mandatory for every former administrative
earnings-history or payroll pairing. It is a new mismatch, not a renamed
claim that the proxy defect persists.

The following frozen codes remain unchanged wherever the corresponding
pairing remains:

```json
[
  "administrative_award_vs_mechanical_claim_stamp",
  "annual_presence_vs_december_current_payment_stock",
  "annualized_statutory_amount_vs_actual_outlay",
  "annualized_statutory_amount_vs_december_current_payment_amount",
  "consolidated_person_cap_vs_adjusted_payroll",
  "consolidated_person_cap_vs_reported_wages",
  "earnings_year_rate_arithmetic_vs_gross_contributions",
  "earnings_year_rate_arithmetic_vs_trust_fund_cash",
  "mechanical_claiming_vs_administrative_in_force_population",
  "no_model_oasi_di_allocation",
  "odd_year_earnings_carry",
  "official_amount_due_at_award_vs_claim_adjusted_eligibility_pia_no_aero",
  "official_estimated_allocation",
  "opening_backfill_imputation",
  "program_population_scope"
]
```

Frame composition has no frozen v1 mismatch-code literal. Its limitation is
preserved by the exact `frame-relative` and
`aggregate-concept-calibrated-not-population-aligned` labels; v1 adds no
optional frame mismatch code. No claiming, accounting, consolidated-cap,
odd-year, frame, or
program-population defect is relabeled as corrected.

### 9.3 Ledger-entry resolution

Forecast-ledger entry 11 resolves only at the merge of the publication PR in
§9.1(9), whose payload contains the exact-complete validator-passing
post-correction context report, integrity-bound sidecar, registered corrected
label array, and positive label-retirement certificate tied to the complete
correction evaluation artifact. A design merge, implementation merge,
target extraction, registration, fit, unmerged output, revenue-only artifact,
incident-only publication, partial report, or validator-failing report
resolves nothing.

## 10. Registered correction-evaluation ceremony

### 10.1 Strict registration, fixture-only rehearsal, and frozen identities

Pre-registration rehearsal is fixture-only. It is structurally unable to
open production PSID inputs, the frozen projection inputs, the vintage-2
target values, the 15 vintage-1 series, or any production output path. Tests
use committed synthetic fixtures and rejection cases. Reading any production
value or computing any production statistic counts as a production execution
and is forbidden before fresh registration.

At trusted-coordinator process entry, before parsing a registration byte,
performing repository proof, taking a lock, running a pre-launch check,
importing correction code, or making any provider call, the frozen bootstrap
constructs the pinned `rng_lifecycle_phase_domain.v1`, installs the direct
no-allocation exit path, initializes the current-phase state to `bootstrap`
and the `rng_lifecycle_sequence_namespace.v1` counter to zero, and completes
boundary zero. It then captures the exact
`runtime_process_start_identity.v1`; any capture failure takes the defined
preclaim direct-exit edge. Those ordered operations through successful
runtime-identity capture are by law the complete and exact pre-wrapper
bootstrap prefix: construction of the pinned phase domain, installation of
the direct no-allocation exit path, initialization of the current phase to
`bootstrap` and the lifecycle counter to zero, completion of boundary zero,
and capture of `runtime_process_start_identity.v1`. On successful completion,
no operation may be added to or interleaved with this prefix. It is provider-
call-free and consumes no lifecycle sequence. The kernel `_exit` syscall
primitive is available without bootstrap installation. A failure before a
valid current-phase state exists invokes that primitive immediately without a
phase transition; any later prefix failure takes the preclaim direct-exit
edge. These are the prefix's only alternate outcomes; both are terminal and
provider-call-free and enter no provider, cache, wrapper, audit-hook, callback,
finalizer, import, logging, or lifecycle-sequence action.

Immediately after successful completion of that prefix, with no intervening
operation, the bootstrap executes the fixed, non-interleavable bootstrap-
installation sequence: live provider call ledger, empty keyed-uniform
lifecycle cache, one wrapper per `rng_access_specs.v2.providers` row in
provider order, then the native audit hook. Ledger and cache creation are the
sole installation-internal prerequisites that precede wrapper activation.
These objects are exactly the §8.1 bootstrap identity rows and consume the
exact creation sequences specified there.

If creation or activation of any installation object fails, the sequence has
exactly one alternate outcome: it changes the already-initialized phase
directly from `bootstrap` to `process_exit` and invokes the installed direct
`_exit` path. That failure outcome is part of the installation sequence, is
terminal and provider-call-free, consumes no additional lifecycle sequence,
and performs no creation or activation after the failure.

After the hook is active, the
coordinator changes phase to `registration_prelaunch`; only then may any
action outside the prefix and installation sequence begin. This installation
is the start of the metered ceremony lifecycle and itself has no RNG/entropy
call. The bootstrap identities and complete
`rng_access_specs.v2` authority are pinned in the implementation tree; once
the configuration is strictly parsed, its full registered object must
deep-equal the already-active provider, phase, bootstrap-implementation, and
principal-authority identities and laws. A call before that comparison is
still metered, and an install, identity, or comparison failure aborts before
production access. The wrappers, call ledger, cache, runtime identity, phase
registry/state, principal authority, and lifecycle counter remain alive
across the initial attempt, incident publication, private receipt
mint/consumption, authorized retry, and final publication; they have exactly
one permitted `active_metering` →
`sealed_deny_all` transition under §8.1 and can never be uninstalled, reset,
or recreated. After that transition they reject and sticky-record every
request before provider dispatch while preserving the sealed ledger/cache
bytes. A new process cannot inherit the receipt or claim a continuation of
that ledger.

Every registration, input JSON, claim, retry-authority record, retry claim,
incident, primary, and sidecar is parsed directly from bounded bytes under the
repository's strict-input contract before any field is read. The parser:

1. decodes strict UTF-8 and rejects a leading U+FEFF BOM;
2. rejects duplicate object keys at every depth;
3. rejects `NaN`, `Infinity`, `-Infinity`, overflow, underflow-to-nonfinite,
   and every nonfinite result;
4. parses a float token only when
   `Decimal(token) == Decimal(str(float(token)))`, rejecting a lossy token;
5. preserves arbitrary-precision JSON integers for later schema bounds and
   never accepts a boolean as an integer; and
6. applies exact key/type/array-position schemas and canonical-byte equality
   wherever this section requires canonical bytes.

No preliminary permissive `json.loads` may extract a registration reference
or path. Registration is a bounded, single-link regular file directly under
`docs/registrations`, read through a root-to-leaf `O_NOFOLLOW` descriptor
chain with stable device/inode/stat metadata before and after, and may not be
a hardlink alias of a protected input.

Before any production claim or input open, Git runs with caller-supplied
`GIT_*` variables removed and proves: the reported toplevel is the sealed
repository root; no tracked path is modified; no tracked path has
assume-unchanged or skip-worktree; no ignored executable artifact exists
below `src` or `scripts`; the design-ratification and implementation commits
both exist and are ancestors of `HEAD`; the design blob at `HEAD`, at the
ratification commit, and in the configured blob digest is identical; the
`HEAD:src` and `HEAD:scripts` tree OIDs equal the corresponding
implementation-commit tree OIDs; and the registration path is tracked at
`HEAD` with `git show HEAD:<path>` bytes equal to the descriptor-read
configuration.

On the initial branch, every untracked path is forbidden and the checkout is
fully clean. On the authorized-retry branch, the coordinator derives—not
configures—the only permitted nontracked/ignored path set from the live
initial claim: exactly that claim, its triggering incident, its sealed
retry-authority file, and no other path; the retry claim must still be absent.
It enumerates the repository with both untracked and ignored files shown,
exact-compares the active ceremony set, and descriptor-revalidates every
allowed path's bytes, hash, device, inode, mode, and cross-reference. A
partial, extra, changed, executable, or implementation-bearing path fails
P01. Thus the records necessarily created by the initial attempt do not make
the sole retry impossible, while they create no general dirty-checkout
exception. Exact `HEAD == implementation_commit` is not required;
records-only descendant commits are allowed.

The primary output is the append-only
`runs/covered_earnings_correction_evaluation_v1.json`, with exact sidecar
`runs/covered_earnings_correction_evaluation_v1.json.env.json`. The primary
embeds the selected correction parameters, canonical model hash, complete
evaluation, and target-use trace. Both paths must be absent at launch. The
primary records SHA-256 of the exact sidecar bytes.

V1 does not publish person-level microdata as a third file. Instead the
primary binds the complete deterministic ledger-rematerialization identity in
§10.2: row schema, ordered support key-set hash, production-input hashes,
expected-ledger stream hash, and every projection×correction-draw stream
hash. A downstream consumer must rematerialize the canonical stable-key row
stream from the pinned inputs and selected model, reproduce the applicable
hash before consuming any row, and record that hash. This hash-checked
rematerialization—not an unbound aggregate report—is the immutable common
ledger contract.

The sidecar schema is
`covered_earnings_correction_evaluation_environment.v2` and has exactly
`schema_version`, `artifact_path`, `registration_reference`,
`configuration_sha256`, `implementation_commit`, `invocation`, `runtime`,
`attempt_evidence`, `input_hashes`, `dependency_versions`,
`substantive_model_sha256`, `evaluation_provenance_sha256`,
`selected_ledger_identity_sha256`,
`trusted_consumer_semantic_authority_sha256`,
`rng_access_results_sha256`,
and `trusted_consumer_evaluation_sha256`.
`artifact_path` is the exact primary path; registration, commit, invocation,
and configuration hash equal the primary/configuration. `runtime` and
`attempt_evidence` deep-equal the corresponding primary objects.
`input_hashes` is the exact ordered disjoint concatenation of
`production_input_manifest.inputs`, then literal IDs
`historical_coverage_rules`, `psid_source_field_inventory`,
`psid_covered_earnings_crosswalk`, and
`ssa_covered_earnings_calibration_targets`. Each row has exactly `input_id`,
`path`, and `actual_sha256`. These full-input hashes are evaluation
provenance and do not enter the substantive model identity.
`dependency_versions` is the
`environment_spec.package_order` expansion; each row has exactly nonempty
`name`, `version`, and `source`, all strings, and version/source exact-match
the registered environment lock. `substantive_model_sha256` and the selected
ledger and trusted-evaluation hashes are null exactly for the no-eligible
branch and otherwise equal the primary; `evaluation_provenance_sha256` and
`trusted_consumer_semantic_authority_sha256` and
`rng_access_results_sha256` are always nonnull and equal their primary
integrity namesakes.

The sidecar is canonical JSON under the function below and contains no
primary-file digest. It is constructed first in memory; the primary then
binds its exact SHA-256. This one-way edge is the sole pair-integrity hash and
cannot be circular. Independent validation exact-checks every sidecar key,
type, value, input digest, dependency row, runtime equality, and branch law
before either final-path rename.

The configuration schema is
`covered_earnings_correction_evaluation_configuration.v2` and contains
exactly this top-level key set:

1. `schema_version`;
2. `registration_reference`;
3. `design`;
4. `implementation_commit`;
5. `invocation`;
6. `production_input_manifest`;
7. `legal_rule_input`;
8. `psid_source_field_inventory_input`;
9. `psid_crosswalk_input`;
10. `calibration_target_input`;
11. `ledger_row_schema_specs`;
12. `coverage_state_dependence_specs`;
13. `historical_coverage_rule_specs`;
14. `verification_claim_specs`;
15. `verification_claim_results`;
16. `psid_questionnaire_slot_specs`;
17. `psid_structural_missing_consequence_specs`;
18. `psid_value_code_specs`;
19. `psid_annualization_rule_specs`;
20. `psid_reconciliation_rule_specs`;
21. `psid_job_spell_match_rule_specs`;
22. `psid_se_aggregation_group_rule_specs`;
23. `psid_coverage_state_group_rule_specs`;
24. `physical_source_cell_specs`;
25. `official_source_alias_specs`;
26. `official_source_arithmetic_rule_specs`;
27. `calibration_target_specs`;
28. `candidate_reference_era_specs`;
29. `substantive_production_input_specs`;
30. `candidate_specs`;
31. `selection_spec`;
32. `draw_spec`;
33. `replay_specs`;
34. `consumer_domain_derivation_specs`;
35. `benefit_gap_derivation_specs`;
36. `earnings_consumer_dependency_specs`;
37. `legal_rounding_rule_specs`;
38. `trusted_consumer_evaluation_specs`;
39. `gate_specs`;
40. `rng_access_specs`;
41. `weight_rescale_specs`;
42. `filesystem_isolation_specs`;
43. `heldout_noninterference_specs`;
44. `evaluation_specs`;
45. `sensitivity_specs`;
46. `attempt_history`; and
47. `output_paths`.

The nested schemas are exact:

- `schema_version` is the configuration-schema literal above, and
  `registration_reference` is a nonempty JSON string.
- `design` has exactly `path`, `ratification_commit`, `blob_sha256`, and
  `revision`.
  `path` is `docs/design/covered_earnings_correction.md`; the commit is 40
  lowercase hex; `blob_sha256` is the 64-lowercase-hex SHA-256 of the exact
  file bytes at that commit and at `HEAD`; and revision is JSON integer `2`,
  excluding booleans.
- `implementation_commit` is 40 lowercase hex.
- `invocation` has exactly `orig_argv`, `interpreter_identity`,
  `runner_identity`, and `pycache_sentinel`.
  `orig_argv` is an exact eight-string array. Index 0 is the concrete
  absolute interpreter path; indices 1–3 are literals `-I`, `-B`, and `-X`;
  index 4 is literal prefix `pycache_prefix=` concatenated with the concrete
  absolute registered sentinel path; index 5 is the concrete absolute runner
  path; index 6 is literal `--registration`; and index 7 is the concrete
  absolute registration path. Position, length, spelling, and
  no-extra-arguments are mandatory; no value is a shell expression,
  placeholder, or moving alias.
  `interpreter_identity` has exactly `path`, `st_dev`, `st_ino`, `mode`,
  `sha256`, and `environment_lock_sha256`. Its path equals index 0; the two
  stat fields are positive JSON integers, mode is a nonnegative JSON integer
  with an executable bit, SHA-256 binds the descriptor bytes of a non-symlink
  regular file, and the lock hash exact-matches the unique registered
  environment-lock input.
  `runner_identity` has exactly `repository_relative_path`, `absolute_path`,
  `st_dev`, `st_ino`, `mode`, `implementation_blob_oid`, `head_blob_oid`,
  and `sha256`. The relative path is the literal
  `scripts/run_covered_earnings_correction_evaluation.py`; the absolute path
  is its traversal-free canonical join under the sealed repository root and
  equals index 5. The two blob OIDs are the exact tracked blobs at
  `implementation_commit` and `HEAD` and must be equal; descriptor bytes at
  the registered positive device/inode and executable mode equal both Git
  blobs and the registered SHA-256. Thus P01's committed `scripts` tree is
  the code actually executing, not an unrelated proof beside an external
  runner.
  `pycache_sentinel` has exactly absolute `path`, positive JSON-integer
  `st_dev`, positive JSON-integer `st_ino`, and JSON integer `mode: 448`
  (octal 0700). Before committing the registration, the coordinator creates
  that exact path with one exclusive `mkdir`, mode 0700, proves it is a
  non-symlink empty directory, and records the descriptor's device and inode.
  At process entry the runner requires byte-for-byte equality of
  `list(sys.orig_argv)` and `orig_argv`, equality of
  `sys.pycache_prefix` and the registered path, the same descriptor identity
  and mode, and continued emptiness. It also descriptor-reopens and
  revalidates both invocation identities and both runner Git blobs before a
  claim. Any mismatch fails before a claim.
- `production_input_manifest` has exactly `schema_version`, `inputs`,
  `support_universe`, and `environment_spec`. Its schema literal is
  `covered_earnings_production_input_manifest.v2`. `inputs` is an ordered
  nonempty array; every object has exactly `input_id`, `path`,
  `schema_version`, `artifact_vintage_id`, `role`, and `sha256`, all strings,
  with a 64-lowercase-hex digest. It lists every permitted source byte other
  than the four separately keyed legal/inventory/crosswalk/target authority
  inputs below and permits no wildcard, directory input, moving alias,
  duplicate ID/path, or unlisted open. The exact allowed input domain is the
  disjoint concatenation of those two parts;
  duplicate IDs or paths across the two parts abort. `support_universe` has
  exactly `selector_id`,
  `required_calendar_years`, `required_roles`, `person_key`,
  `annual_presence_rule`, `age_rule`, `zero_earner_rule`, `weight_field`,
  `projection_draw_indices`, and `input_ids`. The year
  array is exactly 1968 through 2022; projection draws are exactly the JSON
  integers 0..19; the ordered roles exact-match the crosswalk's production
  roles; and every other value is a literal selector or an ordered reference
  to an `inputs` ID. It supplies immutable source coordinates, not a
  self-scoped consumer domain. The only benefit and revenue consumer domains
  are independently reconstructed under
  `consumer_domain_derivation_specs`; a missing key fails G01 and cannot
  revise this manifest.
  `environment_spec` has exactly `lock_input_id` and `package_order`;
  `lock_input_id` is literal `environment_lock`, whose unique input path is
  `requirements/covered_earnings_evaluation.lock`, schema is
  `python_environment_lock.v1`, artifact identity is
  `covered_earnings_evaluation_environment.v1`, and role is
  `environment_lock`. `package_order` is the exact ordered nonempty
  package-name array parsed and registered from that immutable lock.
- Each of `legal_rule_input`, `psid_source_field_inventory_input`,
  `psid_crosswalk_input`, and `calibration_target_input` has exactly `path`,
  `artifact_vintage_id`, `schema_version`, and `sha256`. The inventory is
  independent of the crosswalk; the target path and identity exact-match
  §6.1. Their immutable `(input_id,role)` pairs for the sidecar, static
  substantive-input closure, and primary validation are respectively
  `("historical_coverage_rules","legal_rule_authority")`,
  `("psid_source_field_inventory","source_field_inventory_authority")`,
  `("psid_covered_earnings_crosswalk","crosswalk_authority")`, and
  `("ssa_covered_earnings_calibration_targets",
  "calibration_target_authority")`. Those literals are implicit schema
  fields of the separately keyed objects, not configurable aliases; a
  manifest row with any of the four IDs or paths is a duplicate and aborts.
- Every `*_specs` top-level value is the exact registered deep copy of the
  correspondingly named frozen registry in §§3–8, with the versions declared
  there. They are neither digests nor implementation reconstructions.
  In particular `calibration_target_specs` is v2, `gate_specs` has exactly
  G01–G22, `replay_specs` has exactly six comparisons,
  `heldout_noninterference_specs` is nonempty, and none of the inventory,
  domain, alias, RNG, isolation, or adjudication-rule registries may be
  omitted.
- For each verified historical rule, before accepting the configuration or
  opening a production value, the coordinator strict-parses every
  covered/excluded binding, independently resolves each slot through the
  source inventory and affected-key attachment closure, derives the
  covered-then-excluded `required_micro_facts` array without consulting its
  configured value, and requires deep equality. A binding/slot/premise/
  derived-array mismatch or a fact-bearing constant transform aborts
  registration.
- The four named subregistries inside
  `earnings_consumer_dependency_specs` exact-match, respectively,
  `consumer_source_field_schema_specs.v1`,
  `consumer_literal_domain_specs.v1`,
  `consumer_evaluator_condition_reason_specs.v1`, and
  `consumer_semantic_recipe_specs.v1`; none is supplied by or derived from
  the configured evaluator. `legal_rounding_rule_specs` exact-matches the
  coordinator's source-derived registry before it can enter semantic
  reconstruction. The configured
  `trusted_consumer_evaluation_specs` deep copy is only a comparand: on every
  registration, regardless of the eventual selection branch, the coordinator
  first reconstructs the complete source/domain/rule/unit/root authority
  without reading it, then requires exact constituent and digest equality. A
  p25→p10 binding, wage↔SE source substitution, distinct-domain
  `same_key_choose`, altered source type/unit, unknown domain/reason/rule ID,
  or changed unit-algebra row aborts before production values or graph
  execution.
- `verification_claim_results` is the exact registered deep copy of the
  nine-row §4.1 result registry. Every `registration_required` row is
  `verified/pass`; every optional absent/conflict row binds its complete
  consequence hash; and the coordinator recomputes all nine rows from the
  pinned authorities and independent inventory before accepting the
  configuration.
- `attempt_history` has exactly `prior_incidents`,
  `prior_attempt_claims`, `prior_retry_authorities`, `prior_retry_claims`,
  and `prior_fresh_registration_adjudications`. Each is an ordered array of
  every prior record in that class, with objects containing exactly
  traversal-free `path`, 64-lowercase-hex raw-byte `sha256`, and
  `record_state`. `record_state` is `valid | partial_invalid`, except a
  retry-authority history row may also be `reserved_empty`. Incident and
  adjudication indices are contiguous and all cross-references close. The
  first registration has five empty arrays. Every later registration includes
  the complete history; a missing, extra, reordered, or digest-mismatched
  record aborts.
- `output_paths` has exactly `output_version`, `primary`, `sidecar`,
  `incident_prefix`, `attempt_claim_prefix`, `retry_authority_prefix`,
  `retry_claim_prefix`, and `fresh_registration_adjudication_prefix`.
  `output_version` is literal
  `covered_earnings_correction_evaluation_v1`; the next two are the exact
  paths above. The traversal-free prefixes are respectively
  `runs/covered_earnings_correction_evaluation_incident_`,
  `runs/covered_earnings_correction_evaluation_attempt_`,
  `runs/covered_earnings_correction_evaluation_retry_authority_`,
  `runs/covered_earnings_correction_evaluation_retry_`, and
  `runs/covered_earnings_correction_evaluation_fresh_registration_`.
  The three claim/authority paths are each that prefix plus the 64-lowercase-
  hex configuration SHA-256 and literal `.claim`; the fresh-registration
  adjudication uses its prefix plus the next positive canonical decimal index
  and `.json`. Thus a fresh configuration obtains a fresh durable namespace
  without putting its own hash inside its bytes.

Let `canonical_json_bytes` be UTF-8
`json.dumps(value, sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False) + "\n"`. Object insertion order has no
meaning; registered arrays retain their declared order. Registration
validation exact-checks every value, key set, JSON type, literal, path, and
array position, and requires `canonical_json_bytes(configuration_echo)` to
equal the complete registered configuration bytes. The sealed preparation
phase hashes actual bytes and requires every digest to match.

The claim preimages are frozen. `invocation_sha256` is SHA-256 of
`canonical_json_bytes(configuration.invocation)`.
`prior_history_sha256` is SHA-256 of
`canonical_json_bytes(configuration.attempt_history)`.
`prelaunch_checks_sha256` hashes
`covered_earnings_prelaunch_checks.v1`, an object with exactly
`schema_version`, `branch`, and `rows`; `branch` is
`initial | authorized_retry`, and `rows` is exactly six objects ordered P01
through P06, each with exactly `check_id`, `status: pass`, and the
nonempty `evidence_sha256` described in §10.4. `output_version` in a claim is
the exact configured literal above. None is a hash of a display string or an
implementation-selected subset.

On the initial-attempt branch only, after strict parsing, repository proof,
an exclusive coordinator lock, complete-history validation, and all six
value-blind pre-launch checks—but before opening a production manifest path,
target sidecar, projection input, or other production byte—the coordinator
executes exactly:

1. generates an in-memory 256-bit retry nonce and computes its SHA-256
   commitment;
2. reserves the configuration-derived retry-authority path with
   `O_CREAT|O_EXCL|O_NOFOLLOW`, verifies a new single-link regular file,
   records its descriptor device/inode, changes its mode to 000, fsyncs the
   empty file and parent, and retains the only writable descriptor;
3. creates the configuration-derived initial-attempt claim with
   `O_CREAT|O_EXCL|O_NOFOLLOW`; writes canonical
   `covered_earnings_correction_initial_attempt_claim.v1` bytes containing
   exactly `schema_version`, `registration_reference`,
   `configuration_sha256`, `claimed_at_utc`, `invocation_sha256`,
   `prelaunch_checks_sha256`, `pycache_sentinel`, `output_version`,
   `primary_path`, `sidecar_path`, `next_incident_index`,
   `retry_authority_path`, `retry_authority_st_dev`,
   `retry_authority_st_ino`, `retry_nonce_commitment_sha256`, and
   `prior_history_sha256`; then descriptor-`fchmod`s the claim to 0444,
   fsyncs that descriptor, fsyncs the parent directory, and
   descriptor-rereads the exact bytes and identity; and
4. only after that durable reread mints the production-I/O capability.

Item 1 is the sole authorized `coordinator_retry_nonce_entropy` call. The
authorized-retry branch executes none of items 1–3: in the same coordinator
process, with the original wrappers and ledger still active, it revalidates
the existing initial claim and sealed authority, reuses the private nonce
with zero new entropy calls, consumes the opaque receipt, and creates and
rereads only the retry claim under §10.3 before minting the retry
production-I/O capability. Re-reserving the authority, recreating the initial
claim, generating a replacement nonce, starting a fresh call ledger, or
entering from a new process is failure.

The claim binds the exact six-check record and complete prior-history object.
Every later production open, broker grant, output stage, or incident write
revalidates the live claim path, bytes, digest, device, and inode. Claims are
never removed, truncated, renamed, or overwritten. A kill after any value
exposure therefore leaves durable evidence that this registration's initial
attempt was consumed; absence of a result or incident never restores a
“first” attempt.

An interrupted O_EXCL write can leave a bounded `partial_invalid` claim,
authority, retry claim, incident, or adjudication. Such a path is consumed
and is never completed in place, repaired, removed, or treated as valid.
No production capability is minted from a partial claim; no receipt is minted
from a partial incident/authority; and a partial adjudication authorizes
nothing. The trusted coordinator may descriptor-hash its raw bytes without
parsing fields, publish the next indexed adjudication when applicable, and
bind every partial record in later `attempt_history`. This makes crash
recovery total without weakening strict parsing.

### 10.2 Sealed phases and result contract

The immutable `rng_lifecycle_phase_domain.v1` object in
`rng_access_specs.v2.lifecycle_phase_domain` has exactly `schema_version`,
`ordered_literals`, `canonical_order`, and `failure_disposition`. Its ordered
literals are exactly:

```json
[
  "bootstrap",
  "registration_prelaunch",
  "durable_attempt_claim",
  "preparation",
  "fitting",
  "selection",
  "substantive_lock",
  "preheldout_structural_verification",
  "evaluation",
  "lifecycle_closure",
  "publication",
  "incident_handling",
  "process_exit"
]
```

Schema version is the object literal, canonical order is
`ceremony-lifecycle-order`, and failure disposition is `abort_registration`.
The pinned bootstrap constructs this registry before configuration parsing;
the configured subregistry must later deep-equal it. A coordinator-owned
current-phase state is initialized to `bootstrap` before the first monitored
object is created. After all bootstrap identities exist it transitions to
`registration_prelaunch`. Numbered steps 1 through 7 below then use,
respectively, `registration_prelaunch`, `durable_attempt_claim`,
`preparation`, `fitting`, `selection`, `substantive_lock`, and
`preheldout_structural_verification`. Step 8's conditional held-out and
trusted-consumer work uses `evaluation`; immediately before its common
destroy/empty-set/seal tail the coordinator changes to `lifecycle_closure`.
Step 9 uses `publication`.

The exact normal transition chain is
`bootstrap → registration_prelaunch → durable_attempt_claim → preparation →
fitting → selection → substantive_lock →
preheldout_structural_verification → evaluation → lifecycle_closure →
publication → process_exit`. A no-eligible or early structural-failure path
still enters each skipped-work state in this chain and immediately leaves it
without creating a principal, opening a value, or consuming a provider or
lifecycle sequence. A failure before a valid current-phase state exists takes
§10.1's state-free, bootstrap-fatal direct `_exit` termination. After a valid
current-phase state exists and before the applicable initial or retry claim is
durably reread, any exception takes the exact preclaim-abort edge from the
current `bootstrap | registration_prelaunch | durable_attempt_claim` state to
`process_exit`. Neither path publishes an incident, receipt, lifecycle seal,
primary, or sidecar; a partial durable record retains §10.1's
`partial_invalid` law.
After the applicable claim is durably reread and before terminal durability,
any exception changes state to `incident_handling` before cleanup, incident
construction, or incident publication. Only a successfully popped and fully
revalidated private receipt permits
`incident_handling → registration_prelaunch`, immediately before the retry's
step 1. A terminal incident permits `incident_handling → process_exit`;
`process_exit` has no outgoing edge. The array above is canonical enum order,
not a claim that the authorized retry edge is monotone.

The bootstrap installs the no-allocation direct `_exit` system-call path
before boundary zero with Python `atexit`, finalizers, imports, logging,
callbacks, and signal handlers disabled. A preclaim abort changes state to
`process_exit` and invokes it immediately. Before either rename or a terminal
incident's final durability operation, the coordinator additionally blocks
catchable signals and reproves that the post-durability continuation is that
same path. Immediately after the second rename or terminal-incident fsync, it
changes state to `process_exit` and invokes the syscall; no provider, cache,
wrapper, or audit-hook entry point can run afterward. Thus the zero denial
trace serialized before rename remains the complete normal-run evidence
through process exit, and a terminal incident admits no unrecorded exit-tail
provider activity. Every pre-seal provider event and every post-seal denied-
request row copies the coordinator state at interception time; a worker
cannot report or select its phase. No other correction-run phase literal or
transition is valid; §12 defines the sole context-run normal-chain
substitution.

The isolated runner performs, in order:

1. **Registration and pre-launch.** With the process-entry provider wrappers
   and audit hook already active, strict-parse the committed configuration;
   prove repository ancestry/tree/blob and the branch-exact initial-clean or
   retry-active-ceremony checkout law, complete attempt history, exact
   `sys.orig_argv`, and the concrete fresh-empty sentinel; take the exclusive
   lock; retain the four configured evaluator comparands as bounded canonical
   parsed values without schema-validating or using their semantics; and
   perform the six value-blind checks. No production path or target sidecar
   is openable in this phase.
2. **Durable attempt claim.** On the initial branch, reserve the
   retry-authority inode and durably publish and reread the initial claim
   exactly as in §10.1. On an authorized retry, validate the existing
   authority/initial claim, consume the opaque coordinator receipt, and
   durably publish and reread the retry claim instead. Only the applicable
   live claim mints production-I/O capability.
3. **Preparation and target brokering.** Open and hash only registered inputs;
   exact-check identities, manifests, frozen registries, physical-cell and
   alias closure, inventory/crosswalk closure, full prior history, and output
   absence. Reconstruct the ledger/gap projections of the independently
   frozen `consumer_source_field_schema_specs.v1`, exact-check its
   primitive/legal authority rows, the complete
   `consumer_literal_domain_specs.v1` and
   `consumer_evaluator_condition_reason_specs.v1` registries, and every
   `consumer_semantic_recipe_specs.v1` row; descriptor-rederive the complete
   legal-rounding registry and every independent output domain;
   reconstruct the complete §8.1 source/domain/rule/unit/root authority
   without reading the quarantined evaluator comparands; only then
   schema-validate and exact-compare those four configured members and their
   expected authority digest. A capability-separated target validator may stream all target
   bytes but returns only schema/hash/cardinality/coverage proofs—never an
   observation, sign, rank, residual, or statistic. A fresh target broker
   converts verified, cell-scoped observations into role-specific packets.
   Candidate code receives no path or file-open capability. Before phase 4,
   the coordinator expands and executes the complete §4.1
   `direct_law_micro_fact_presence_ledger.v1` and
   `direct_law_action_trace.v1`, then descriptor-reopens the registered
   sources and independently constructs G06. Only the exact classified
   component stream validated by that comparison may be brokered onward. A
   domain, presence, action, or classified-byte mismatch freezes a
   pre-held-out structural gate failure and no fitting process is created.
   No evaluator source value is granted before that authority comparison.
4. **Fitting.** The broker exposes to each optimizer only positive-weight
   `train` cells with a fitting loss; run all three candidates and freeze
   their fitted parameter vectors. A capability-separated diagnostic
   evaluator then opens zero-weight train-role cells, records them, and
   cannot communicate a value or status back to an optimizer.
5. **Selection.** The broker newly exposes to the selector only
   `selection_eligible` validation cells and executes §7.2. After the
   selection decision is immutable, the separate diagnostic evaluator records
   zero-weight validation-role cells without communicating to the selector.
   If none is eligible, freeze the exact `no_eligible_candidate` branch, skip
   the production lock and selected-model evaluation, keep the held-out
   handle sealed, and continue to phase 7; no primary is yet constructed or
   published.
6. **Conditional substantive lock.** For an eligible selection, serialize the
   cell-scoped correction-model
   identity below, record its SHA-256, close all fitting/selection mutation
   capability, and record the exact `lock_event` result below. The
   no-eligible branch records no lock and proceeds with its already-frozen
   branch tag.
7. **Pre-held-out structural verification.** While held-out and vintage-1
   value handles remain unminted, run the exact six replay comparisons, exact
   four trusted weight-rescale executions, optimizer-bearing sandbox
   assertions, and coordinator-expanded synthetic mirrors of the complete
   registered noninterference key/fragment domain.
   On a selected branch, replay/rescale workers receive only the same
   cell-scoped model-choice packets. On both branches, including
   no-eligible, fresh baseline and mutant fit/selection workers rerun the
   complete three-candidate sequence; the mutation fixture changes every
   mirrored evaluation-only value and exclusive source-byte range required by
   §6.2 while preserving the model-choice closure.
   Each synthetic baseline and mutant independently constructs every
   reachable G01–G10/G12–G20/G22 row and exact not-evaluated rows for unreachable
   selected-model evidence, then serializes its branch-tagged canonical
   pre-G21 bundle. The coordinator compares those hashes, proves
   all three mutation-class counts/key ledgers and the required evaluation-
   provenance difference, freezes the shared acyclic G21 evidence/row, and
   only then freezes every conditions-1–6 input reachable before the
   lifecycle seal; the selected branch's condition-6 G11 component remains
   pending, while no-eligible condition 6 remains not evaluated for its other
   selected-model conjuncts. Neither
   final preconstruction eligibility nor a full-bundle hash feeds G21.
   Freeze every reachable G10/G14 row,
   G21's acyclic pre-G21/count/provenance evidence, and the
   pre-held-out prefix evidence for G11/G15; then destroy every optimizer, selector,
   replay, rescale, and diagnostic worker and every associated mount.
   Provider wrappers and the coordinator audit hook remain active.
   Independently evaluate every hard gate whose complete evidence is
   reachable while those handles are sealed, retaining a 22-row result with
   the remaining gates tagged not evaluated. G21 is always evaluated,
   including on `no_eligible_candidate`. If a selected branch has any
   reachable failed gate,
   seal held-out access permanently, mark the exact pre-held-out `gate_fail`
   branch, and continue to phase 8's common lifecycle closure; no failure can
   be “completed” by opening held-out values or skip G11 sealing.
8. **Conditional held-out evaluation and branch-general lifecycle
   closure.** On `no_eligible_candidate`, do not create a held-out or
   selected-consumer capability; retain the evaluated G21/noninterference
   evidence and enter the common tail below. A selected pre-held-out
   structural-failure branch likewise creates neither capability. On a
   selected branch without such a failure, only after those workers are destroyed, create
   the held-out evaluator and record first-exposure sequences. The trusted
   provenance validator may hash registered vintage-1 source bytes needed for
   physical-alias closure, but it never decodes or releases a 15-series value
   or computes a vintage-1 comparison; only §12 may do that. Complete target
   diagnostics, 10-versus-20 draw checks, downstream reductions, and Option C;
   independently materialize every authority-schema evaluator source,
   instantiate and execute the reconstructed §8.1 opcode chains, exact-compare
   the configured DAG closure, lock every authoritative root, normalize and
   compare the exact-schema complete runner proposal, and construct corrected
   result numbers only from those roots.

   In the common tail on every terminal branch, complete only that branch's
   already-authorized provider work, destroy every remaining provider-capable
   evaluator, coordinator delegate, proposal process, mount, descriptor, and
   callback at its authority-selected effective boundary, append every atomic
   actual event, and exact-compare the complete expected and actual principal
   event streams. Only after that equality and a complete destruction ledger
   may it consume the empty-set barrier. Then atomically seal the original
   provider ledger and keyed-uniform cache and transition the original
   wrappers to `sealed_deny_all` under §8.1. Construct the complete evaluated
   `rng_access_results`, including every nonce and forbidden row and
   `rng_provider_lifecycle_seal.v1`; finalize G11 from that sealed whole-
   process evidence and G15 from the complete lifecycle audit. Run or update
   all 22 gate rows using locked G10/G14 and G21 preimage evidence,
   with selected-model-dependent rows not evaluated only where the branch
   makes them unreachable, and construct the complete noninterference bundle.
   The coordinator then derives the final conditions-1–6 objects and compares
   the two full substantive bundles as the post-G21 assertion. The common
   outer-lifecycle seal is coordinator-supplied identically to the baseline
   and mutant G11/hard-gate projections and, where condition 6 is evaluated,
   its condition-6 projections; it remains structurally excluded from G21's
   acyclic preimage.
   No fitting/selection/provider-capable process or filesystem view exists.
9. **Publication.** Freeze the full substantive-bundle hashes and the
   conditions-1–6 object; while wrappers remain in deny-all state, construct
   the sidecar bytes and a complete primary candidate containing the derived
   final eligibility wrapper and full G11 lifecycle evidence; then perform
   §6.2's condition-7 validation with condition 7 excluded from every earlier
   comparison preimage. Stage both without occupying final paths. Immediately
   before the first rename, reconstruct semantic authority again from the
   frozen registries, exact-compare every source/domain/rule/unit/root closure,
   and reevaluate/bit-compare every branch-reachable authoritative root and
   corresponding primary field. In the same no-callback check, reconstruct
   the complete provider ledger/cache hashes and lifecycle-seal comparand from
   the live original objects; require the same wrapper registry, live
   wrapper-object identities, and audit-hook identity, `sealed_deny_all`,
   exact equality with serialized
   `rng_access_results` and its integrity/sidecar hashes, and zero post-seal,
   denied, and sticky counts. This check is mandatory on both selected and
   no-eligible branches.
   With no intervening callback, and with deny-all still active, rename the
   primary atomically, then rename the sidecar atomically. Deny-all remains
   active through process exit. The pair is not falsely
   described as one filesystem-atomic operation. A failure after the primary
   rename is the permitted partial state in §10.3.

Preparation's trusted validator is separate from the fit/selection process
and cannot communicate a target value, rank, sign, residual, or statistic.
Three noninterchangeable audit concepts are frozen. An **internal broker
release** is a decoded value packet granted inside the sealed stack and is
logged by increasing JSON-integer `exposure_sequence`; ordinary fitting may
have such releases. An **estimate-bearing external yield** is any target
value, parameter, prediction, loss, rank, residual, statistic, or
estimate-dependent bit that escapes the sealed coordinator through a log,
exception, file, IPC recipient, user-visible output, or other channel; the
retry criterion requires none. A **held-out/vintage exposure** is release of
a decoded held-out or 15-series value beyond the integrity-only validator;
its `none | possible | confirmed` state controls fresh-registration taint.
Streaming and hashing bytes inside the integrity validator is none of these
decoded-value releases. After the first held-out broker grant, the configuration,
candidate/model bytes, thresholds, seed/draw law, and selected identity are
immutable; the run may only complete or publish an incident.

The primary schema is the literal
`covered_earnings_correction_evaluation.v1` and has exactly these top-level
keys:

`schema_version`, `artifact_id`, `artifact_role`,
`registration_reference`, `configuration_echo`, `runtime_provenance`,
`attempt_evidence`, `evaluation_binding`, `status`,
`candidate_evidentiary_labels`, `selected_correction`, `results`,
`integrity`, and `certifies_nothing`.

`schema_version` and `artifact_id` are both
`covered_earnings_correction_evaluation.v1`;
`artifact_role` is `registered_correction_model_evaluation`; the registration
reference and configuration echo exact-match §10.1.
`candidate_evidentiary_labels` is always the exact ordered array
`["frame-relative","modeled-covered-earnings",
"aggregate-concept-calibrated-not-population-aligned"]`; it describes the
evaluated estimand and does not activate publication labels.
`runtime_provenance` has exactly `started_at_utc`, `completed_at_utc`,
`implementation_commit`, `python_version`, `platform`, `invocation`,
and `execution_attempt`.
Both timestamps satisfy §10.3's UTC grammar, the commit and invocation equal
configuration, and version/platform are nonempty strings.
`execution_attempt` is `initial | authorized_retry`.
`attempt_evidence` has exactly `initial_claim_path`,
`initial_claim_sha256`, `retry_authority_path`, `retry_authority_sha256`,
`retry_claim_path`, and `retry_claim_sha256`. The initial pair is always
nonnull. The other four fields are all null on the initial attempt and all
nonnull on an authorized retry. Paths, hashes, descriptor identities, and
cross-bindings revalidate against §10.3; a public JSON object without the
live one-shot receipt cannot create the retry branch.
`evaluation_binding` is always present, including on
`no_eligible_candidate`, and follows the exact full-provenance schema below.
The trusted validator constructs its cell commitments without releasing a
held-out decoded value.
`evaluation_provenance_sha256` is exactly SHA-256 of canonical bytes of
`evaluation_binding.full_calibration_evaluation_provenance`; the outer
binding, which contains that hash, is never its own preimage.
`certifies_nothing` is exactly
`["not-population-aligned",
"not-individual-administrative-covered-earnings-truth",
"not-ledger-entry-11-resolution"]`.

`selected_correction` is JSON null only for `no_eligible_candidate`.
Otherwise it has exactly `candidate_id`, `model_identity`,
`substantive_model_sha256`, `evaluation_provenance_sha256`, and
`ledger_identity`.
`model_identity` has exactly:

`schema_version`, `candidate_spec`, `parameter_vector`,
`fit_selection_cell_identity`, `ledger_row_schema_specs`,
`coverage_state_dependence_specs`,
`candidate_reference_era_specs`, `selection_spec`, `draw_spec`,
`substantive_production_input_specs`,
`substantive_production_input_identity`, and
`implementation_commit`.

Its schema literal is `covered_earnings_correction_model.v2`; the specs are
exact registered deep copies. `parameter_vector` is in registered parameter
order and each object has exactly `parameter_id` and
`ieee754_binary64_hex`; the latter is the lowercase 16-hex-digit encoding of
the finite binary64 bits. `substantive_production_input_specs` is the exact
registered §6.2 object. `substantive_production_input_identity` has exactly
`schema_version`, `inputs`, and `support_universe`; its input array is the
spec's value-blind, statically closed `included_input_ids` in exact order,
never a runtime-open trace. Each retained input omits `path` and keeps exactly
`input_id`, `schema_version`, `artifact_vintage_id`, `role`,
`content_scope`, and `scoped_sha256`. `content_scope` and the digest are the
exact registered whole-input or canonical fragment projection above, never
the full digest of a partly evaluation-only file. Its schema literal is
`covered_earnings_substantive_production_input_identity.v1`.
Evaluation-only projection inputs, vintage-1 inputs, the full calibration
artifact, complete official source documents, target sidecars, and any digest
whose byte domain includes held-out or zero-weight cells are excluded.
Every ID in the full disjoint allowed input domain must appear exactly once
in the specs' included or excluded array; legal, inventory, crosswalk,
model-weight, and PSID bytes in the static candidate/selector dependency
closure remain bound. G15 validates
that static closure and G21 mutation-tests its substantive boundary. No
whole-registry legal, inventory, or crosswalk digest is separately embedded
in `model_identity`; their exact model-affecting projections are already the
scoped identity rows, so excluded 2015–2023 inventory/crosswalk rows cannot
reseed the correction.
`coverage_state_dependence_specs` is the exact registered §3.1 object, so the
same fitted parameters cannot acquire a different joint-status law.
`ledger_row_schema_specs` is the exact registered §3.1 object, so an
identical parameter vector cannot acquire a different ledger row meaning or
encoding.
`fit_selection_cell_identity` is the exact canonical
`fit_selection_cell_identity.v1` object in §6.2. It contains only the
verified cell-scoped bytes and physical ancestry of positive-weight direct
train and selection-eligible direct/boundary validation cells. It excludes
whole-document/source/artifact hashes, all held-out and zero-weight
value-bearing payloads, vintage-1 bytes, configuration and incident history;
only §6.2's required value-blind structural closure is retained. A physical primitive
shared with model choice remains bound through its cell-scoped ancestry and
honest alias closure; an exclusive diagnostic byte does not.

`substantive_model_sha256` is SHA-256 of
`canonical_json_bytes(model_identity)` and becomes the immutable
`correction_version` and draw-namespace identity in §§3 and 5.4.
The primary's always-present `evaluation_binding` has exactly
`schema_version`, `artifact_id`,
`registration_reference`, `configuration_sha256`,
`full_calibration_evaluation_provenance`, and
`evaluation_provenance_sha256`. Its schema literal is
`covered_earnings_correction_evaluation_binding.v2`.
`full_calibration_evaluation_provenance` is the exact §6.2 v1 object and
contains the complete target artifact, complete source manifests and
document digests, all target specs and value commitments, all three complete
physical-source/alias/arithmetic registries, inventory/vintage identities, all evaluation-only
inputs, and configuration binding. A no-eligible primary therefore binds but
does not disclose held-out values.
Its canonical hash is `evaluation_provenance_sha256`. Neither the object nor
its hash enters the substantive model, a uniform, model-choice loss,
or selection. The sole gate use is the pair of baseline/mutant hashes in
G21's acyclic evidence to prove provenance inequality; eligibility condition
4 receives only that frozen boolean together with G21's pre-bundle and
mutation-completeness predicates, never either provenance hash or object.
Therefore a same-content retry or fresh registration cannot silently reseed
an identical substantive model, and replacing only evaluation bytes changes
provenance without changing any substantive output. No output,
invocation, registration, incident-history, pycache, timestamp, display
rounding, or row order enters the substantive identity.
For a selected correction,
`selected_correction.evaluation_provenance_sha256` exact-matches this binding;
the no-eligible branch has no selected correction but retains the complete
binding and hash.

`ledger_identity` has exactly `schema_version`, `canonical_stream_law`,
`row_schema_sha256`, `support_keyset_sha256`, `expected_ledger_streams`,
`realized_ledger_streams`, and `claim_context_gap_identity`. Its schema is
`covered_earnings_ledger_rematerialization.v1`.
`canonical_stream_law` is the literal
`stable_atomic_key_order_canonical_json_object_per_lf_terminated_line_v1`:
each complete §3.1 atomic row is serialized with `canonical_json_bytes`
without an enclosing array and concatenated in the declared atomic-key order.
`row_schema_sha256` is SHA-256 of
`canonical_json_bytes(model_identity.ledger_row_schema_specs)` and therefore
binds the exact downstream-readable field/type/unit registry;
`support_keyset_sha256` binds the union independently reconstructed from the
complete Stage A–D benefit and unsplit revenue domains under
`consumer_domain_derivation_specs`, not a configured selector.
`expected_ledger_streams` contains exactly 20 rows ordered by
`projection_draw_index=0..19`, each with exactly
`projection_draw_index`, `row_count`, and `sha256`.
`realized_ledger_streams` contains exactly 400 rows in projection-major,
correction-minor order, each with exactly `projection_draw_index`,
`correction_draw_index`, `row_count`, and `sha256`. Counts are positive JSON
integers excluding booleans; every hash is 64 lowercase hex. All streams must
have the independently reconstructed union key set and row count. G01, G08,
G10, and G22 recompute these hashes. A downstream benefit, revenue, context,
or W1 consumer must
reproduce and record the applicable stream hash before use.

`claim_context_gap_identity` has exactly `schema_version`,
`canonical_gap_stream_law`, `gap_derivation_specs_sha256`,
`gap_row_schema_sha256`, `gap_support_keyset_sha256`,
`expected_gap_streams`, and `realized_gap_streams`; its schema is
`covered_earnings_claim_context_gap_rematerialization.v1`.
`canonical_gap_stream_law` is the literal
`projection_context_then_correction_draw_canonical_gap_rows_v1`.
`gap_derivation_specs_sha256` hashes the complete registered
`benefit_gap_derivation_specs.v1`; `gap_row_schema_sha256` hashes
`benefit_gap_derivation_specs.gap_row_schema_specs` and therefore has one
closed preimage; and `gap_support_keyset_sha256` hashes the complete ordered
eight-field key stream derived below.
The canonical row key extends the complete §3.1 atomic component key and is
`(stable_person_id,gap_year,role,source_job_id,source_component_id,
derived_component_id,operative_claim_year,career_variant_id)`, after the
§8.1 independently derived benefit context order and
cutoff-before-imputation law. Distinct jobs, roles, and mixed-component
children can never collapse. `expected_gap_streams` has exactly one
row per independently derived
`(projection_draw_index,operative_claim_year,career_variant_id)` context,
ordered by projection draw then the frozen context order; each row has
exactly those three coordinates, `row_count`, `keyset_sha256`, and `sha256`.
`realized_gap_streams` expands each expected row by
`correction_draw_index=0..19` in projection/context/correction order and has
exactly the same fields plus that draw index. Empty streams are retained with
row count zero and the canonical empty-stream hash; missing contexts cannot
shrink the array. Every hash covers complete component channels, neighbor
years/hashes, operative claim year, provenance, the effective-year legal-rule
foreign key, channel-value status, and no-new-uniform proof under
`benefit_gap_derivation_specs.v1`; statutory outputs are subsequently
constructed only by the trusted evaluator.
G01, G10, G12, G18, and G22 recompute the entire nested identity.

`results` has exactly:

`input_validation`, `direct_law_micro_fact_presence_ledger`,
`direct_law_action_trace`, `candidate_dispositions`, `target_results`,
`lock_event`, `evaluation_completion`,
`hard_gate_results`, `replay_results`, `rng_access_results`,
`weight_rescale_results`, `isolation_results`,
`noninterference_results`, `trusted_consumer_evaluation`, `support_results`,
`distribution_results`, `downstream_results`, `before_context_results`,
`target_use_trace`, and `correction_model_eligibility`.

Their schemas and completeness laws are:

- `direct_law_micro_fact_presence_ledger` is the exact coordinator-owned
  §4.1 `direct_law_micro_fact_presence_ledger.v1` object over the complete
  independently derived applicable record×rule×fact domain. G06 consumes its
  rows and final classification/action trace; G17 independently reconstructs
  every covered/excluded binding and premise, derives the required-fact
  concatenation without reading its configured comparand, and exact-compares
  its count, keyset, source-purpose closure, premise results, and canonical
  hash. It is present on both selected and no-eligible branches and cannot be
  shortened by a candidate disposition.
- `direct_law_action_trace` is the exact §4.1
  `direct_law_action_trace.v1` object used by classification and independently
  reevaluated by G06. It is present on both selection branches; its complete
  rows/hash are the actual-side action preimage, not a runner-selected digest.
- `evaluation_completion` is exactly
  `complete | preheldout_structural_gate_fail | no_eligible_candidate`.
  It is `complete` for `pass` and for a gate failure found only after
  held-out release; the other two literals identify their exact sealed
  branches.

- `input_validation` is the same exact ordered input union as the sidecar.
  Each row has exactly
  `input_id`, `path`, `schema_version`, `artifact_vintage_id`,
  `expected_sha256`, `actual_sha256`, and `status`; all identities match and
  status is `pass`. Any mismatch emits a `preparation` incident before a
  primary is constructed, so no valid primary contains a failed input row.
- `candidate_dispositions` has exactly three rows in §5.3 complexity order.
  Each has exactly `candidate_id`, `fit_status`, `parameter_count`,
  `identification_status`, `training_loss`, `validation_status`,
  `validation_loss`, `selection_status`, and `reason_codes`. Status literals
  are respectively `success | failed`,
  `pass | fail | not_evaluated`,
  `pass | tolerance_fail | domain_fail | not_evaluated`, and
  `selected | eligible_not_selected | ineligible | not_evaluated`.
  `parameter_count` is a nonnegative JSON integer. Training loss is finite
  iff fit status is success; validation loss is finite iff validation status
  is `pass | tolerance_fail` and is null for `domain_fail | not_evaluated`.
  Reason codes are an ordered nonempty string array iff any disposition is
  `failed`, identification `fail`, validation `tolerance_fail | domain_fail`,
  selection `ineligible`, or not-evaluated because of an earlier failure;
  otherwise they are empty.
- `target_results` is ordered candidate, §6.2 family, then verified year.
  Every candidate has one slot for every train/validation spec; only the
  locked candidate has held-out slots. An evaluated, available slot has
  exactly `candidate_id`, `target_id`, `verified_calendar_year`,
  `effective_role`, `model_year_source_class`, `evaluation_status`,
  `observed`, `predicted`, `predicted_sample_sd`, `loss`,
  `diagnostic_error`, `tolerance`, `status`, `reason_code`, and
  `first_exposure_sequence`, with `evaluation_status: evaluated`.
  In the in-domain branch, `observed`, `predicted`,
  `predicted_sample_sd`, and every applicable loss/error are finite and the
  sample SD is nonnegative. A positive-weight train or
  selection-eligible validation cell alone may have nonnull `loss`; it has
  null `diagnostic_error` and status
  `fit_input | pass | tolerance_fail`. A zero-weight or held-out cell has
  `loss: null`, finite `diagnostic_error`, and status `diagnostic_only`.
  In the exact §6.2 domain-fail branch, `observed`, `predicted`, and
  `predicted_sample_sd` retain the finite unfavorable values, sample SD is
  nonnegative, `loss` and `diagnostic_error` are null, status is
  `domain_fail_diagnostic`, and `reason_code` is the exact registered
  domain-failure literal. `reason_code` is null in every in-domain branch.
  `tolerance` always exact-matches the tagged spec object.
  An unavailable structural-gap diagnostic has the same keys but exactly
  `predicted: null`, `predicted_sample_sd: null`, `loss: null`,
  `diagnostic_error: null`,
  `status: no_claim_independent_model_analogue`, and
  `reason_code: no_claim_independent_model_analogue`; its observed official
  value and exposure sequence remain nonnull. It cannot materialize or stand
  in for a claim-context benefit gap row.
  A slot made unreachable by the candidate's first fit, identification, or
  domain failure instead has exactly `candidate_id`, `target_id`,
  `verified_calendar_year`, `effective_role`, `model_year_source_class`,
  `evaluation_status`, `first_exposure_sequence`, and `reason_code`, with
  `evaluation_status: not_evaluated` and the exact disposition reason.
  Exposure sequence is a positive JSON integer iff the broker released that
  observation and is null otherwise.
  Held-out slots are always diagnostic, never directly cause `gate_fail`,
  and have exposure sequences strictly greater than the lock. A `pass` or
  complete-evaluation `gate_fail` report has exactly one for every held-out
  spec; a no-eligible or pre-held-out structural-failure report has none.
- `lock_event` is null exactly for `no_eligible_candidate`. Otherwise it has
  exactly `event_type`, `exposure_sequence`, and
  `substantive_model_sha256`, with literal
  event type `selected_model_lock`, positive JSON-integer sequence, and hash
  equal to `selected_correction.substantive_model_sha256`. Every held-out
  exposure follows it.
- `hard_gate_results`, `noninterference_results`, and `rng_access_results`
  are branch-general tagged objects. The first two always have exactly
  `{"evaluation_status":"evaluated","rows":[...]}`, including on
  `no_eligible_candidate`. They can never use a block-level not-evaluated
  branch. `rng_access_results` always has exactly
  `{"evaluation_status":"evaluated","lifecycle_seal":{...},"rows":[...]}`;
  its lifecycle seal is the complete §8.1 object and cannot be omitted on
  either terminal branch. The genuinely selected-only blocks are
  `replay_results`, `weight_rescale_results`, `isolation_results`,
  `trusted_consumer_evaluation`, `support_results`, `distribution_results`,
  `downstream_results`, and `before_context_results`. Their evaluated array
  branch has exactly
  `{"evaluation_status":"evaluated","rows":[...]}`; the trusted-evaluator
  branch instead has exactly
  `{"evaluation_status":"evaluated","result":<the §8.1 object>}`. Their
  unreachable branch has exactly
  `{"evaluation_status":"not_evaluated","reason":...}`, where reason is
  `no_eligible_candidate | preheldout_structural_gate_fail`. The following
  exact schemas and cardinalities apply; `rows: []` is invalid for every
  nonempty frozen registry:

  - `hard_gate_results` has exactly 22 rows, G01 through G22 in §8.1 order.
    Each has exactly `gate_id`, `status`, `observed`, `required`, and
    `evidence_sha256`. Status is `pass | fail | not_evaluated`. On a
    pre-held-out structural failure, every already decidable gate retains
    pass/fail, at least one already decidable gate is fail, and every gate
    whose evidence would require held-out release is `not_evaluated` with
    `observed: null` and the hash of the canonical
    `preheldout_structural_gate_fail` reason object. No row is omitted.
    On `no_eligible_candidate`, every gate reachable through fitting,
    selection, sandbox, and the synthetic mutation ceremony retains its
    actual pass/fail result; G11 and G21 are always `pass | fail`. On a
    selected pre-held-out structural-failure branch, G11 is likewise updated
    after the branch-general lifecycle seal rather than left not evaluated. A
    selected-model-dependent gate is `not_evaluated`, with
    `observed: null` and the hash of the canonical `no_eligible_candidate`
    reason object. Thus the branch has 22 rows rather than an omitted gate
    block.
  - `replay_results` has exactly the six `replay_specs.v1` rows in order.
    Each has exactly `test_id`, `left_run_id`, `right_run_id`,
    `left_expected_source_order_sha256`,
    `left_actual_source_order_sha256`,
    `right_expected_source_order_sha256`,
    `right_actual_source_order_sha256`,
    `left_fit_selection_bundle_sha256`,
    `right_fit_selection_bundle_sha256`,
    `left_substantive_model_sha256`,
    `right_substantive_model_sha256`,
    `left_ledger_identity_sha256`, `right_ledger_identity_sha256`, and
    `status`. All hashes are the actual independently constructed canonical
    object hashes. `status` is `pass` iff both actual source-order hashes
    equal their P/R/H expectations and all three output left/right hash pairs
    are equal; it is `fail` otherwise. A fail row retains every mismatching
    order or output hash and is not schema-invalid.
  - `rng_access_results.rows` has one row per `rng_access_specs.v2` provider in
    exact order, each with exactly `provider_id`, `authority_class`,
    `call_count`, `argument_trace_sha256`,
    `keyed_uniform_registry_sha256`, and `status`.
    `call_count` is the actual nonnegative JSON-integer count of that
    provider's pre-seal ledger events, including an intercepted forbidden
    request even though its underlying provider was not reached, and the trace
    hash binds actual complete terminal-branch/callsite/argument/phase/flow
    evidence from process entry through the atomic lifecycle seal. `lifecycle_seal`
    deep-equals the exact `rng_provider_lifecycle_seal.v1` object for the
    actual selected or no-eligible branch. Its status must pass in every
    valid primary, and its `pre_rename_recheck_sha256` is reconstructed from
    the same live objects immediately before the first rename. Its embedded
    principal lifecycle retains both complete event-stream preimages and
    passes only when the independently reconstructed expected stream and
    immutable actual coordinator stream deep-equal in every field and array
    position. A
    forbidden-provider row passes iff its count is zero and its trace is the
    canonical empty ledger; its keyed-registry hash is null. The correction
    midpoint row passes iff its count and trace exact-match the independently
    expanded one-call-per-key expected ledger across the whole process,
    `keyed_uniform_lifecycle_cache.v1` proves every repeated retry request was
    a hit with zero provider calls, and its nonnull exhaustive key→uniform
    registry hash matches. The coordinator retry-nonce row passes
    iff the whole same-process ceremony lifecycle from the §10.1 bootstrap
    contains exactly one metered 32-byte call at the pinned pre-production
    coordinator callsite, zero new calls on an authorized retry, and the exact
    private commitment-only flow; its keyed-registry hash is null. A row
    otherwise fails and retains the
    nonzero count or mismatching hashes. Fresh-generator state snapshots are
    not evidence. G11 passes iff every provider row and the lifecycle seal,
    including exact expected-versus-actual event-stream equality, pass;
    `rng_access_results` remains fully evaluated and serialized when G11
    itself fails. The G11 hard-gate row's `evidence_sha256` hashes this
    complete tagged object, never only the provider rows, a lifecycle summary,
    or a pre-held-out prefix.
  - `weight_rescale_results` has exactly four
    `weight_rescale_specs.v1` rows, each with exactly `comparison_id`,
    `expected_base_survey_weight_packet_sha256`,
    `actual_base_survey_weight_packet_sha256`,
    `expected_rescaled_survey_weight_packet_sha256`,
    `actual_rescaled_survey_weight_packet_sha256`,
    `base_survey_weight_grant_ledger_sha256`,
    `rescaled_survey_weight_grant_ledger_sha256`,
    `survey_weight_multiplier_trace_sha256`,
    `objective_weight_identity_comparison_sha256`,
    `base_bundle_sha256`, `rescaled_bundle_sha256`, and `status`. The first
    eight evidence fields prove the exact complete 1×/7× PSID survey packets,
    every broker read, the common exact multiplier, and bit-identical
    target-loss/objective weights; the last two bind the complete registered
    candidate or selection/model/ledger bundle. Status is `pass` iff both
    actual packet hashes equal their independently derived expectations,
    both grant ledgers cover every weight key exactly once wherever consumed,
    the multiplier trace proves exact common-rational use, the objective
    identity comparison proves no objective weight changed, and the two
    output bundles are equal; it is `fail` otherwise. Base and rescaled
    packet hashes are not required to equal each other. All actual unequal or
    incomplete hashes remain mandatory failure evidence.
  - `isolation_results` has exactly the 15
    `filesystem_isolation_specs.v1` assertion rows in order, each with exactly
    `assertion_id`, `worker_id`, `expected_grant_sha256`,
    `actual_grant_sha256`, `forbidden_access_count`, `audit_trace_sha256`,
    and `status`. Its cardinality and worker IDs are derived from the frozen
    worker/grant registry. Status is `pass` iff the grant hashes match, the
    actual nonnegative forbidden-access count is zero, and the audit trace
    satisfies that assertion; otherwise it is `fail` and retains every
    mismatching hash, nonzero count, and full trace hash.
  - `noninterference_results` has exactly one row per nonempty
    `heldout_noninterference_specs.v1` fixture, each with exactly
    `fixture_id`, `baseline_pre_g21_bundle_sha256`,
    `mutant_pre_g21_bundle_sha256`,
    `baseline_selection_branch`, `mutant_selection_branch`,
    `baseline_substantive_bundle_sha256`,
    `mutant_substantive_bundle_sha256`,
    `baseline_evaluation_provenance_sha256`,
    `mutant_evaluation_provenance_sha256`,
    `independently_mutable_value_count`,
    `shared_derived_diagnostic_poison_count`,
    `exclusive_source_fragment_count`, and `status`. The counts are actual
    nonnegative JSON integers, both branch literals are
    `selected_correction | no_eligible_candidate`, and the hashes bind the
    actual canonical objects. Status is `pass` iff all three counts exact-match the fixture,
    both pre-G21 hashes are equal, both full substantive-bundle hashes are
    equal, the branch literals are equal, and the full provenance hashes
    differ; it is `fail` otherwise and
    preserves the unequal/count-mismatched evidence. A sole full-bundle
    inequality after the acyclic G21 predicate passed is instead the
    pre-primary `invariant` incident above, so no valid primary can combine
    eligibility true with a failed publication-only assertion. Full-bundle hashes and
    this result row's status are publication-only and expressly excluded
    from G21's preimage. The two provenance hashes enter G21 only through the
    acyclic evidence object's inequality predicate; neither complete
    provenance object can enter a substantive bundle, eligibility object, or
    other gate. This block is fully evaluated on no-eligible; only its
    branch-tagged selected-model projections are not evaluated.
  - `trusted_consumer_evaluation.result` is the exact
    `trusted_consumer_evaluation.v1` object in §8.1 on the evaluated branch.
    Its semantic-authority hash is independently reconstructed, every
    source/domain/rule/unit/root comparison count is zero, and its graph-spec
    hash only proves that the registered comparand matched. Source, node, and
    root rows have the complete authority-derived cardinality/order; every
    root's expected/configured closure hashes match; the runner comparison
    retains all four actual mismatch counts and hashes; and G22 passes this
    conjunct only when its overall status is `pass`. The coordinator
    constructs every corrected distribution/downstream numeric field from
    the matching authoritative root summary and bit-compares it again
    immediately before publication. A selected correction can never use the
    `not_evaluated` tag or an empty stream.
  - `support_results` is independently expanded by projection draw,
    consumer, calendar year, source class, Stage disposition, operative claim
    year, and career variant from `consumer_domain_derivation_specs.v1`. Each
    row has
    exactly `projection_draw_index`, `consumer`, `calendar_year`,
    `year_source_class`, `stage_disposition`, `operative_claim_year`,
    `career_variant_id`, `expected_key_count`, `ledger_key_count`,
    `missing_key_count`, `extra_key_count`, `expected_keyset_sha256`,
    `ledger_keyset_sha256`, and `status`. Null context dimensions occur only
    where the derivation registry says not applicable. Source class is
    coordinator-derived from the exact support/domain row and cannot be
    inferred from availability. Every 2013 benefit row has
    `year_source_class: claim_specific_boundary_gap` and nonnull operative
    claim/career coordinates; revenue has only projected 2015–2022 rows and
    no 2013 key. Counts and hashes are actual evidence; status is `pass` iff
    missing and extra counts are zero, expected and ledger counts match, and
    keyset hashes are equal, and is `fail` otherwise. A support failure
    retains the actual positive counts and unequal hashes rather than
    violating the report schema.
  - `distribution_results` and `downstream_results` use the exact registered
    long schema `metric_id`,
    `stratum_id`, `calendar_year`, `year_source_class`,
    `operative_claim_year`, `career_variant_id`, `statistic`,
    `observation_count`, `mean`, `sample_sd`, `unit`, `status`, and
    `reason_code`. Each coordinate exact-matches the corresponding
    `evaluation_specs.v1` row and trusted root. Rows retain their exact
    `evaluation_specs.v1` array order. Every annual claim-context gap row has
    both context coordinates nonnull; specifically,
    every 2013 row has
    `year_source_class: claim_specific_boundary_gap` and nonnull
    coordinates. A nonannual row has `calendar_year`,
    `year_source_class`, `operative_claim_year`, and `career_variant_id` all
    null. Count is a nonnegative JSON integer. With positive count,
    means/SDs are finite, SD is nonnegative, and reason is null unless status
    is `fail`; a tolerance or empirical failure retains its finite
    unfavorable values and exact reason. With zero count, mean and SD are
    null: a diagnostic-only registered row has
    `status: not_applicable_empty_stratum` and that exact reason, while a
    gate-bearing row has `status: fail` and
    `reason_code: empty_registered_stratum`. Status is therefore
    `pass | fail | not_applicable_empty_stratum`; no empty row disappears or
    invents a finite statistic.
  - `before_context_results` is the sole typed raw-proxy/legacy-numeric family
    and uses exactly `metric_id`, `before_context_kind`, `stratum_id`,
    `calendar_year`,
    `year_source_class`, `operative_claim_year`, `career_variant_id`,
    `statistic`, `mean`, `sample_sd`, `observation_count`, `unit`,
    `evidence_role`, `status`, and `reason_code`. It is a tagged union.
    `before_context_kind: frozen_legacy` requires
    `evidence_role: fixed_legacy_before_context`; such a row carries an exact
    source class only when its frozen predecessor authority declares one,
    that class agrees with the §4.2 calendar-year map, and the class needs no
    claim-context coordinates; otherwise it is null. The branch never carries
    claim-context coordinates. A nonnull frozen class may not be
    `structural_gap_imputed` or `claim_specific_boundary_gap`, because those
    classes require the coordinates this branch forbids. In particular,
    calendar year 2013 has no permissible nonnull class in this branch and
    must be null.
    Any frozen unconditional legacy 2013 number therefore remains a
    null-class diagnostic rather than a corrected 2013 row.
    `before_context_kind: option_c_sensitivity` requires
    `evidence_role: raw_proxy_sensitivity_before_context`, exact
    `sensitivity_specs.v1` order, and the complete
    `annual_provenance_context_expansion` source-class/context coordinates.
    Its `metric_id` is the colon join of literal `option_c`, sensitivity ID,
    stratum ID, calendar year, year source class, operative claim year,
    career variant ID, and statistic, using literal `none` for every null;
    the resulting IDs are unique. Each frozen-legacy ID is the colon join of
    literal `frozen_legacy`, predecessor model-metric ID, stratum ID,
    calendar year, year source class, literal `none` operative-claim year,
    literal `none` career variant, and statistic, again using `none` for any
    other null coordinate. Registration proves uniqueness over the complete
    expanded predecessor result domain, so annual/stratum/statistic rows
    cannot collide. The two literal branch prefixes make the
    ID sets disjoint. Canonical array order is all frozen-legacy rows in
    predecessor evaluation order, followed by Option-C rows in
    `sensitivity_specs.v1` order ×
    `annual_provenance_context_expansion` order. No serializer sort or
    implementation discovery may change that order.
    The coordinator computes that openly raw-proxy number under §7.4; it is
    not a trusted corrected root. Ordinary numeric/cardinality/empty-row laws
    equal the corrected long blocks. The sole override is an Option-C
    diagnostic-proxy source failure under §7.4: the retained expected row has
    `observation_count: 0`, null mean and sample SD, `status: fail`, and
    `reason_code: missing_option_c_diagnostic_proxy`. This structural-input
    failure is distinct from and takes precedence over
    `not_applicable_empty_stratum`; no other reason may use the override.
    Both branches are diagnostic-only and cannot
    enter a candidate, gate, selection, corrected metric, ledger, condition,
    or certificate operand.
- `target_use_trace` is one row per expanded target spec in registry order,
  with exactly `target_id`, `verified_calendar_year`, `effective_role`,
  `model_year_source_class`, `source_cell_ids`, `physical_source_cell_ids`,
  `primitive_ancestry_ids`, `alias_group_ids`,
  `sibling_group_ids`, `sibling_assertion_scopes`,
  `effective_evidentiary_role`,
  `broker_packet_sha256`, `first_exposure_phase`,
  `first_exposure_sequence`, `used_for_fitting`, `used_for_selection`, and
  `used_for_diagnostic`. Year, source class, and all identity arrays are
  independently reconstructed by the trusted validator from physical source
  identities and exact-match the frozen target/alias closure; they are not
  accepted from worker self-report. The two sibling arrays are positionally parallel and
  retain `exact_published_value_equality | structural_dependence_only` for
  every sibling group in canonical alias order.
  `effective_evidentiary_role` applies
  `fit > selection > diagnostic` across the complete physical closure.
  `broker_packet_sha256` binds the only value packet that can reach a worker.
  An unopened held-out row has both exposure fields and packet hash null and
  all three booleans false, permitted only in `no_eligible_candidate` or
  `preheldout_structural_gate_fail`. In `pass` or a complete-evaluation
  `gate_fail`, every held-out row is opened only in evaluation and has
  diagnostic true; in a pre-held-out `gate_fail`, it remains unopened. A
  held-out physical closure can never have fitting or selection true. A
  nonnull phase is `fitting | selection | evaluation`; its
  sequence is a positive JSON integer, and phase, sequence, and applicable
  packet hash obey their exact branch law. Every evaluated target result
  points to the matching trace sequence. This three-literal target-exposure
  domain is distinct from `rng_lifecycle_phase_domain.v1`; the shared
  `fitting`, `selection`, and `evaluation` spellings do not join the two
  sequence namespaces.
- `correction_model_eligibility` is the exact
  `correction_model_eligibility.v2` object with exactly `preconstruction`,
  `condition_7`, and `eligible`. `preconstruction` is the exact
  `correction_model_preconstruction_eligibility.v1` object frozen before
  output construction and has exactly `condition_1` through `condition_6`
  plus `eligible`. Every condition is
  `pass | fail | not_evaluated`. Preconstruction eligibility is true iff a
  selected correction exists and all six conditions pass. Final eligibility
  is true iff preconstruction eligibility is true and condition 7 is `pass`.
  A `pass` report has six preconstruction passes and condition 7 pass. A
  complete-evaluation `gate_fail` has only pass/fail preconstruction values
  and at least one fail. A pre-held-out structural `gate_fail` has at least
  one fail and uses `not_evaluated` only where sealed held-out evidence made a
  selected-model condition unreachable.
  `no_eligible_candidate` has preconstruction condition 1 `pass`, condition 4
  `pass | fail` from the evaluated G21 battery, conditions 2, 3, 5, and 6
  `not_evaluated`, and preconstruction eligibility false; G11 nevertheless
  remains fully evaluated in `hard_gate_results` and `rng_access_results`.
  Every valid primary
  has final condition 7 `pass`; failure to establish it is an invariant
  incident, not a primary with condition 7 fail. These are recomputed and are
  not the §9 label certificate. Condition inputs exclude either run's
  `evaluation_provenance_sha256`; condition 4 consumes only G21's
  already-frozen boolean that the two hashes differ together with its
  mutation-completeness and pre-bundle-equality predicates. G21 proves that
  changing only held-out, zero-weight, or vintage-1-exclusive bytes cannot
  change any preconstruction condition. Condition 7 and final eligibility
  enter no G21 or substantive-bundle preimage.

`status` is an exact tagged-union discriminator:

- `pass` requires a nonnull selected correction, every selected-only block
  evaluated, branch-general `rng_access_results` evaluated with a passing
  lifecycle seal and G11, all correctness and registered validation
  conditions passing, `evaluation_completion: complete`, and
  `correction_model_eligibility.eligible: true`;
- `gate_fail` requires a nonnull selected correction, at least one declared
  failed condition, and eligibility false. With
  `evaluation_completion: complete`, selected-only evaluation is complete.
  With `preheldout_structural_gate_fail`, held-out slots are absent, every
  unreachable selected-only block has the exact not-evaluated reason, and no
  held-out/vintage exposure exists. In both cases `rng_access_results` is
  evaluated, its lifecycle seal passes, and G11 retains its actual pass/fail
  result. Both are normal publishes-regardless
  results, not incidents; and
- `no_eligible_candidate` requires selected correction null, all three
  candidate dispositions and all phase-reachable train/validation rows,
  null `lock_event`, `evaluation_completion: no_eligible_candidate`, no
  held-out exposure, evaluated 22-row hard-gate and complete noninterference
  blocks with G11 and G21 each `pass | fail`, complete evaluated
  `rng_access_results` with
  `lifecycle_seal.terminal_branch: no_eligible_candidate` and a passing
  lifecycle seal, every genuinely selected-only block in the exact
  `not_evaluated` branch, preconstruction condition 4 evaluated, final
  condition 7 pass, and both eligibility booleans false.

`integrity` has exactly `configuration_sha256`, `sidecar_sha256`,
`substantive_model_sha256`, `evaluation_provenance_sha256`,
`direct_law_fact_closure_sha256`,
`trusted_consumer_semantic_authority_sha256`,
`rng_access_results_sha256`,
`ledger_identity_sha256`, `expected_ledger_streams_sha256`,
`realized_ledger_streams_sha256`, `physical_alias_closure_sha256`,
`claim_context_gap_streams_sha256`, and
`trusted_consumer_evaluation_sha256`. Configuration, sidecar,
evaluation-provenance, direct-law-fact-closure, and physical-alias hashes are
always 64 lowercase hex, as are the trusted semantic-authority and
RNG-access hashes;
substantive-model, ledger, expected/realized-stream, and claim-gap hashes are
null exactly in the no-eligible branch, as is the trusted-evaluation hash.
`substantive_model_sha256` otherwise equals the selected correction;
`evaluation_provenance_sha256` always hashes only
`evaluation_binding.full_calibration_evaluation_provenance` under the exact
equation above. `direct_law_fact_closure_sha256` hashes a canonical object
with exactly `covered_fact_bindings`, `excluded_fact_bindings`,
`coordinator_derived_required_micro_facts`,
`direct_law_micro_fact_presence_ledger_sha256`, and
`direct_law_action_trace_sha256`; the first two are the complete rule-ordered
binding projections, the third is derived from them without reading the
configured comparand, and the last two hash the complete branch-general
result objects. It is nonnull on every branch.
`trusted_consumer_semantic_authority_sha256` is the complete coordinator-
reconstructed §8.1 authority digest and exact-matches both registration-time
and immediate-pre-rename reconstructions on every branch. It never hashes or
derives from the configured graph.
`rng_access_results_sha256` hashes the complete branch-general
`results.rng_access_results` tagged object, including all provider rows and
the lifecycle seal; it exact-matches the immediate-pre-rename reconstruction
on every branch.
`ledger_identity_sha256` otherwise hashes canonical
`selected_correction.ledger_identity`.
`expected_ledger_streams_sha256` and `realized_ledger_streams_sha256` hash
the corresponding complete canonical arrays;
`physical_alias_closure_sha256` hashes a canonical object with exactly the
complete `physical_source_cell_specs`, `official_source_alias_specs`, and
`official_source_arithmetic_rule_specs`; and
`claim_context_gap_streams_sha256` hashes the complete canonical
`claim_context_gap_identity`;
when nonnull, `trusted_consumer_evaluation_sha256` hashes the complete
canonical evaluated `results.trusted_consumer_evaluation.result`. The primary records
SHA-256 of the exact sidecar bytes. Results validation checks array positions
before lookup, recomputes selection, losses, gates, hashes, and status, and
rejects every missing, extra, duplicate, reordered, wrong-branch, wrong-type,
wrong-unit, wrong-role, wrong-year, nonfinite, or unjustified-null value. A
self-reported pass flag has no authority.

### 10.3 Incidents, opaque retry receipts, and fresh registration

Incident classification uses this exact precedence. A final path, output
write, stage, fsync, or rename failure maps to incident phase `publication`.
Otherwise a report/schema/recomputed-invariant failure or any failure in
`lifecycle_closure` maps to `invariant`. Otherwise an exception after the
applicable claim reread while lifecycle phase is
`durable_attempt_claim | preparation` maps to `preparation`; one in
`fitting | selection | substantive_lock |
preheldout_structural_verification | evaluation` maps to `compute`. No other
lifecycle phase can originate an incident: preclaim phases take the direct
abort edge, and `process_exit` has no fallible continuation. Candidate
ineligibility, validation-tolerance failure, or a hard-gate result is never
an incident. A failure while writing the incident or validating, popping, or
converting its private receipt publishes no nested incident: the triggering
incident or its `partial_invalid` record is terminal and the exact edge is
`incident_handling → process_exit`.

The writer uses the next contiguous append-only path
`runs/covered_earnings_correction_evaluation_incident_<n>.json`, where \(n\)
is canonical positive base 10 without a leading zero. The path is directly
under `runs/`, contains no traversal, and must not exist. It is created with
`O_CREAT|O_EXCL|O_NOFOLLOW`, descriptor-validated, written completely,
descriptor-`fchmod`ed to 0444, descriptor-fsynced, parent-directory-fsynced,
and descriptor-reread. Its object has exactly these keys:

- `schema_version`: JSON string literal
  `covered_earnings_correction_evaluation_incident.v1`;
- `incident_index`: JSON integer \(n\geq1\), excluding booleans, exactly
  equal to the filename suffix;
- `timestamp_utc`: a real UTC date/time JSON string in
  `YYYY-MM-DDTHH:MM:SSZ` form or with one through six fractional-second
  digits immediately before the literal `Z`;
- `phase`: JSON string enum
  `preparation | invariant | compute | publication`;
- `reason`: nonempty machine-readable JSON string;
- `reason_detail`: free-text JSON string;
- `registration_reference`: JSON string exactly equal to
  `configuration_echo.registration_reference`;
- `configuration_sha256`: the exact 64-lowercase-hex registered digest;
- `configuration_echo`: exact object equality with the registered
  configuration;
- `execution_attempt`: `initial | authorized_retry`;
- `initial_claim_path` and `initial_claim_sha256`: the live immutable initial
  claim;
- `retry_authority_path` and `retry_authority_sha256`: both null on an
  initial-attempt incident and both the sealed authority on a retry incident;
- `retry_claim_path` and `retry_claim_sha256`: both null on an
  initial-attempt incident and both the live retry claim on a retry incident;
- `last_entered_lifecycle_phase`: the exact
  `rng_lifecycle_phase_domain.v1` state immediately before the transition to
  `incident_handling`;
- `last_completed_boundary_id`: the exact frozen atomic coordinator boundary
  ID at the cutoff;
- `last_completed_boundary_order`: the nonnegative JSON integer, excluding
  booleans, that pairs with the boundary ID and marks the last fully completed
  boundary before that transition;
- `no_estimate_bearing_information_yielded`: a JSON boolean supplied by the
  trusted coordinator's grant/output audit; and
- `heldout_vintage_exposure_state`: `none | possible | confirmed`, derived
  from the complete broker-grant audit through incident publication;
- `heldout_vintage_exposure_audit_sha256`: the 64-lowercase-hex hash of that
  complete ordered audit; and
- `artifact_path`: JSON null except iff phase is `publication` and a partial
  primary exists, when it is exactly the traversal-free primary path in
  §10.1 and that file exists.

The incident object's four-literal `phase` is an error-classification domain,
not `rng_lifecycle_phase_domain.v1`. The coordinator atomically retains the
last-entered phase and exact last-completed cutoff ID/order before changing
lifecycle phase to `incident_handling`. Before constructing or publishing the
incident bytes, it enumerates every role of that attempt whose creation
boundary is no later than the cutoff and whose normal destruction boundary is
later. In cleanup-target boundary order, it destroys each such still-live
principal at the unique `incident_cleanup_boundaries` target selected by that
exact cutoff pair. Every destruction event atomically records lifecycle phase
`incident_handling`, the selected cleanup target ID/order, and its consumed
lifecycle sequence in the actual principal event stream and lifecycle row.
A target mapped from another cutoff is invalid even if it has the same phase
or callsite; no principal may be created during cleanup.

All selected cleanup destructions and their actual event rows must complete
and exact-match the cutoff-selected authority mappings before incident
construction, incident publication, retry-authority sealing, or receipt
minting. A cleanup or mapping mismatch is terminal, publishes no incident or
receipt, and takes the direct `incident_handling → process_exit` edge. The
complete expected-versus-actual stream equality remains mandatory when a
terminal primary is later sealed. Throughout cleanup, construction, and
publication, every provider or denial event likewise carries lifecycle phase
`incident_handling` regardless of the incident's classification literal.

For a receipt-authorized retry, the three durable lifecycle-cutoff fields are
the independently durable source for the initial attempt's
`attempt_lifecycle_cutoff_evidence.v1` values. The final role-domain object
must exact-match them and the triggering incident hash, and its effective
cleanup boundaries must be the cutoff-selected targets just recorded.

Existing incident suffixes must be exactly `1..n-1`; configured attempt
history must equal every incident and claim that predated registration by
path and digest; the writer uses \(n\), never overwrites, and a subsequent
fresh registration includes the complete ordered history. Publication always
renames the primary before the sidecar, so a sidecar-only partial state is
forbidden. A partial primary permanently consumes the append-only v1 path;
recovery requires a newly ratified schema/output version and fresh
registration. The runner never invents a v2 path.

There is no publicly constructible retry-authority JSON token. An unchanged-
configuration retry exists only inside the coordinator process that
published the initial incident. After the incident bytes and inode are
durable, the private incident-publication stack may continue only when the
phase is `preparation | compute`, `reason` begins literal `external_`, the
primary and sidecar remain absent, and the coordinator's grant/output audit
proves both `no_estimate_bearing_information_yielded: true` and
`heldout_vintage_exposure_state: none` with zero held-out/vintage broker
grants. It then:

1. revalidates the exact configuration, initial-claim bytes/inode, incident
   bytes/inode, reserved authority bytes/inode, nonce commitment, and absence
   of any retry claim;
2. writes through the retained reservation descriptor the canonical
   `covered_earnings_correction_retry_authority.v1` object with exactly
   `schema_version`, `registration_reference`, `configuration_sha256`,
   `triggering_incident_path`, `triggering_incident_sha256`,
   `initial_claim_path`, `initial_claim_sha256`, `sealed_at_utc`,
   `retry_nonce_sha256`, `no_estimate_bearing_information_yielded`,
   `heldout_vintage_exposure_state`, and
   `heldout_vintage_exposure_audit_sha256`,
   descriptor-`fchmod`s it to 0444, fsyncs that descriptor, fsyncs its parent
   directory, and descriptor-rereads its exact bytes and original inode;
   `retry_nonce_sha256` must equal the
   initial claim's commitment; the last three audit fields exact-match the
   triggering incident, the no-yield boolean is true, and exposure state is
   literal `none`; and
3. mints a private `_RetryReceipt` whose constructor and class identity are
   unavailable to runner/configuration code, stores it in an in-memory
   identity registry, and returns only that object to the coordinator's
   retry entry point.

The receipt is neither JSON nor serializable. It binds the repository root,
registration/configuration bytes, initial claim bytes/inode, triggering
incident bytes/inode, sealed authority bytes/inode, nonce, invocation, and
no-yield and no-held-out/vintage-exposure audits. The retry entry point
atomically pops it once, rechecks every
binding, and rejects a forged object, replay, second pop, changed byte,
different root or process, newer incident, or any intervening exposure.
Possessing or constructing byte-identical public records never authorizes a
retry.

The successful pop creates one coordinator-owned in-memory
`covered_earnings_retry_receipt_consumption.v1` event with exactly
`schema_version`, `coordinator_process_identity_sha256`,
`private_registry_slot_sha256`, `consumed_at_utc`,
`registration_reference`, `configuration_sha256`,
`initial_claim_sha256`, `triggering_incident_sha256`,
`retry_authority_sha256`, `heldout_vintage_exposure_audit_sha256`, and
`pop_sequence`. The exposure-audit hash exact-matches the incident and sealed
authority; `pop_sequence` is literal JSON
integer `1`; `coordinator_process_identity_sha256` is exactly SHA-256 of the
live §8.1 `runtime_process_start_identity.v1` object; and
`private_registry_slot_sha256` is the commitment created when the private
registry is initialized. Neither identity can be supplied by
runner/configuration code.
`receipt_consumption_sha256` is SHA-256 of that event's canonical bytes. The
event is audit evidence, not a serializable replacement for the receipt.

Before the retry may open a production byte, the coordinator creates the
configuration-derived retry-claim path with
`O_CREAT|O_EXCL|O_NOFOLLOW`. Its canonical
`covered_earnings_correction_retry_attempt_claim.v1` object has exactly
`schema_version`, `registration_reference`, `configuration_sha256`,
`claimed_at_utc`, `invocation_sha256`, `prelaunch_checks_sha256`,
`initial_claim_path`,
`initial_claim_sha256`, `triggering_incident_path`,
`triggering_incident_sha256`, `retry_authority_path`,
`retry_authority_sha256`, `retry_authority_st_dev`,
`retry_authority_st_ino`, `receipt_consumption_sha256`,
`heldout_vintage_exposure_audit_sha256`, `primary_path`, and `sidecar_path`.
The exposure audit hash exact-matches the incident, authority, and
consumed-receipt event.
After the complete write it is descriptor-`fchmod`ed to
0444, descriptor-fsynced, parent-directory-fsynced, and descriptor-reread
before minting the retry production-I/O capability. That
`prelaunch_checks_sha256` hashes the exact
`branch: authorized_retry` six-row object in §10.1. Every
retry operation revalidates both claims and the authority. A crash after
receipt consumption, loss of the in-memory receipt, or failure to publish
the retry claim consumes retry authority and requires fresh registration.

Incident validation enforces the exact key set and types, schema/status
literals, timestamp grammar, index/filename equality, canonical location,
contiguity, echo identity, canonical finite JSON, and the `artifact_path`
iff-rule. No incident field outside `configuration_echo` contains an
estimate, target value, fitted parameter, residual, rank, or production
statistic. The no-yield boolean is necessary but not sufficient for retry:
only the private publication stack can mint the receipt. A retry incident is
terminal and can never mint another receipt, even when it otherwise has an
eligible shape.

After any consumed configuration namespace—an authority reservation or an
initial claim—not followed by a complete report pair, a new configuration may
register only after the coordinator durably publishes the next append-only
`covered_earnings_correction_fresh_registration_adjudication.v1`. The
coordinator creates its canonical path with
`O_CREAT|O_EXCL|O_NOFOLLOW`, proves a new single-link regular file, writes
bounded strict canonical bytes, descriptor-`fchmod`s it to 0444, fsyncs the
descriptor, fsyncs the parent directory, and descriptor-rereads the same
bytes/device/inode before a new registration may cite it. It has exactly:

`schema_version`, `adjudication_index`, `adjudicated_at_utc`,
`prior_registration_reference`, `prior_configuration_sha256`,
`attempt_claim_path`, `attempt_claim_sha256`, `retry_authority_path`,
`retry_authority_sha256`, `retry_authority_st_dev`,
`retry_authority_st_ino`, `retry_authority_mode`,
`retry_claim_path`, `retry_claim_sha256`,
`terminal_incident_path`, `terminal_incident_sha256`, `exposure_state`,
`attempt_claim_state`, `retry_authority_state`, `retry_claim_state`,
`terminal_incident_state`, `output_path_state`, and `disposition`.

Claim and incident states are `absent | partial_invalid | valid`;
authority state is
`absent | reserved_empty | partial_invalid | valid`. Every path/hash pair is
null exactly for `absent` and otherwise binds the bounded raw descriptor
bytes, even when strict JSON parsing fails. A later registration may hash and
stat a `partial_invalid` record for adjudication but may never read a field
from it. Only `valid` records participate in semantic cross-references or
retry eligibility.
The three authority-stat fields are null exactly when authority state is
`absent`; otherwise device and inode are positive JSON integers and mode is
the descriptor-observed nonnegative permission integer. `reserved_empty`
additionally requires SHA-256 of the exact empty byte string, the original
reserved device/inode, and literal mode `0`; `valid` requires the same
reserved device/inode and literal mode `292` (octal 0444).
`attempt_claim_path`/hash is nonnull except in the sole
authority-reserved-before-claim crash branch, when it is null, the authority
state/path/hash/stat tuple identifies the exact empty mode-000 reserved inode, no
retry/incident exists, and coordinator audit proves that no production
capability was minted. `exposure_state` refers only to held-out/vintage
exposure—not an internal train/validation broker release—and is
`none | possible | confirmed`; `output_path_state` is
`absent | partial_primary | complete_pair`; and `disposition` is
`same_output_version_new_registration | new_output_version |
heldout_vintage_tainted`. The adjudicator reconstructs these states from
claims, broker grants, process/output audits, and durable paths; the failed
runner cannot declare them. A same-v1-output fresh registration is allowed
only when both final paths are absent and `exposure_state: none`.
Disposition precedence is deterministic: (1) possible or confirmed
held-out/vintage-1 exposure yields `heldout_vintage_tainted`; a simultaneous
partial primary additionally requires a new output version by its
`output_path_state`; (2) otherwise a partial primary yields
`new_output_version`; (3) otherwise absent final paths yield
`same_output_version_new_registration`. `complete_pair` is terminal and
rejects fresh-registration adjudication. Tainted evidence can never be
relabeled held out or regain fitting/selection eligibility. The new
registration's changed complete-history bytes produce a new configuration
SHA and therefore fresh claim namespaces. All prior claims, authorities,
incidents, and adjudications remain append-only.
If the process dies after reserving the authority inode but before the
initial claim becomes durable, no production capability or exposure exists,
but the old namespace is still consumed; the same fresh-registration
adjudication records `exposure_state: none` before a new registration.

### 10.4 Six pre-launch checks

The coordinator records:

1. the ratified design blob, committed configuration, implementation
   ancestor, branch-exact clean/active-ceremony checkout law, and exact
   implementation `src`/`scripts` tree identity under §10.1, including
   descriptor/Git-blob equality for the actual tracked runner and
   descriptor/environment-lock identity for the actual interpreter;
2. a fresh registration reference, complete prior-attempt history, and every
   required fresh-registration adjudication;
3. expected production paths, immutable IDs, and hashes compared only with
   the committed registration—without opening a production input, target
   sidecar, or output;
4. absence/state of the primary and sidecar, exact next incident and
   adjudication indices, and the registered sentinel's exclusive creation,
   absolute path, emptiness, mode, device, and inode. The initial branch
   requires this configuration's initial-claim, authority, and retry-claim
   paths all absent. The authorized-retry branch instead requires the exact
   live initial claim and sealed authority, the consumed receipt binding, and
   retry-claim absence until its exclusive creation;
5. byte equality of the registered concrete `invocation.orig_argv` with
   `sys.orig_argv`, including its absolute interpreter, literal isolation
   flags, actual absolute `pycache_prefix` token, exact runner, and exact
   registration path, plus revalidation of both invocation identity objects;
   and
6. acknowledgment of `publishes_regardless`, incident publication,
   durable-claim consumption, `no_self_rescue`, and the law below.

These are six exact registered records with nonempty evidence hashes, not six
self-reported booleans. Checks 1–5 precede the initial claim and production
capability. On the opaque retry entry, their explicit retry branches are
revalidated—including P01's exact three-path active-ceremony allowlist—and
receipt/authority evidence is appended before the retry claim is created; no
command placeholder, shell reconstruction, or new CLI argument exists.

### 10.5 Sole normative execution law

The correction evaluation has one registered configuration, one durably
claimed initial attempt, `publishes_regardless`, and `no_self_rescue`.
Its state machine is:

```text
REGISTERED_UNCLAIMED
  -> AUTHORITY_RESERVED
  -> INITIAL_CLAIMED
  -> COMPLETE_RESULT
   | PUBLISHED_TERMINAL_INCIDENT
   | PUBLISHED_RETRY_ELIGIBLE_INCIDENT
       -> LIVE_PRIVATE_RECEIPT
       -> RETRY_CLAIMED
       -> COMPLETE_RESULT
        | PUBLISHED_TERMINAL_INCIDENT
```

`AUTHORITY_RESERVED` has no production capability and may advance only to a
valid durable initial claim; a crash or partial claim from that state requires
fresh-registration adjudication.
`INITIAL_CLAIMED` exists iff the exact initial-claim bytes/inode are durable;
`RETRY_CLAIMED` exists iff both durable claims and the sealed authority
revalidate. `COMPLETE_RESULT` and every published terminal incident are
terminal for that configuration. A killed claimed process without an
incident, lost receipt, changed claim/authority/incident byte, noneligible
incident, or failed retry has no implicit transition: only the durable
fresh-registration adjudication above may authorize a new
`REGISTERED_UNCLAIMED` state under a different configuration hash.

The sole retry is possible only after the initial claim, a durably published
`preparation | compute` incident with `external_` reason, absent final paths,
and the coordinator's proof that no estimate-bearing information was yielded;
only the same-process opaque one-shot receipt authorizes it. The retry uses
the unchanged configuration and invocation and must publish its own durable
retry claim before any production access. Public records, a recreated
process, or an eligible-looking JSON object are never retry authority.

A complete `pass`, `gate_fail`, or `no_eligible_candidate` result; an
invariant or publication incident; any estimate-bearing external yield or
possible/confirmed held-out/vintage exposure; a partial primary; a changed
byte; a nonexternal incident; receipt loss; a killed claimed attempt without
an eligible incident; or a retry failure
cannot take this retry edge. It requires coordinator fresh-registration
adjudication, complete-history registration, and when the output path was
consumed, a newly ratified output version. A failed authorized retry does not
make fresh registration impossible. It makes that adjudication mandatory,
and exposed held-out evidence retains its taint. Claims are permanent, so no
state can return to `REGISTERED_UNCLAIMED`.

This paragraph is the sole normative execution law document-wide; every
other ceremony description, including §12, imports it without weakening it.
An empirical gate failure is a result, never an incident or retry
opportunity. Publication means committing the unaltered report pair or
incident/claim/adjudication evidence whether favorable or unfavorable; it
never means selecting which result to disclose.

## 11. Scope exclusions, degradation, unchanged state, and deviations

### 11.1 Normative no-go list

V1 forbids:

- W1 population nationalization, weight calibration, roster expansion, or
  level matching;
- deriving national “capture rates” from model/official total ratios;
- behavioral employment, earnings, claiming, or contribution responses;
- alternative taxable-maximum policy modeling;
- employer-specific cap accounting, multi-employer refunds, or trust-fund
  deposit timing;
- retraining the frozen earnings projection without a new projection gate;
- using later PSID waves as production information for earlier projected
  years;
- silently changing `runs/first_estimates_v1.json`,
  `runs/anchor_context_report_v1.json`, either sidecar, the vintage-1 official
  artifact, or any frozen registry;
- relabeling unrelated mismatches as resolved;
- a scalar correction, sector-only hard classification, career-only
  adjustment, or 2015–2022-only adjustment as the label-retiring production
  model;
- fitting any of the 15 vintage-1 series, a national payroll/worker level, a
  model weight, or the roster; and
- any circular dataflow in §8.3.

### 11.2 Revenue-only degradation path

If full historical support or any certificate condition fails, a later fresh
design and registration may authorize
`covered_earnings_revenue_window_experiment.v1` for 2015–2022 only. Corrected
revenue tables then carry the four exact labels

```json
[
  "frame-relative",
  "modeled-covered-earnings",
  "aggregate-concept-calibrated-not-population-aligned",
  "experimental-revenue-only-2015-2022"
]
```

Every benefit, AIME, PIA, and mixed benefit/revenue output retains the legacy
ordered labels `frame-relative`, `pre-alignment`, and `labor-income proxy`.
The experimental result cannot enter careers, splice into a historical path,
issue a label-retirement certificate, or resolve entry 11.

### 11.3 Unchanged limitations

The consolidated-person cap versus employer reporting; odd-year carry;
gross-versus-net accounting and contribution timing; the fixed frame and
weights; opening-stock imputation; mechanical claiming; annual
presence/December stock; benefit amount/outlay; OASI/OASDI program scope; and
absence of an OASI/DI allocation remain. Benefit-only deemed credits remain
zero and explicitly unsupported in v1. Wholly unreported positive earnings
with no source-supported component remain outside v1's zero-preserving
measurement law; §5.2 forbids claiming they were recovered.

### 11.4 Deviations

The scoping survey's blanket characterization of the 1976–1978 interview-
wave spouse series as wages-only is not ratified. The pinned 1976-wave
description for reference year 1975 (`V4379`) includes labor income from
unincorporated business, so v1 types that source as `mixed`. The 1977–1978
wave short labels alone do not establish wages-only; their exact reference-
year 1976–1977 concepts and value-code maps, together with the frozen
wave→reference-year mapping, are registration-required under V-B6. This
tightens the survey's source-concept characterization without changing a
coordinator ruling.

“Out-of-sample” for the post-correction context event is qualified in §12 as
structurally out of the fitting sample because the 2015–2022 cells have
already been viewed. That is an honesty clarification, not an additional
deviation.

No post-exposure context fresh-registration exception is ratified. The
previously considered same-output-version exception would have weakened
§10.5 and required disclosure as a real ceremony deviation; §12 instead
imports §10.3–§10.5 unchanged, including
`heldout_vintage_tainted`. There is therefore no such deviation in v1.

## 12. What this unlocks

1. **Post-correction context evidence.** After a `pass` correction report
   pair is published and its publication PR merges, a new fresh registration
   may bind that locked correction. Its append-only output is
   `runs/covered_earnings_context_report_v1.json`, its sidecar is the exact
   `runs/covered_earnings_context_report_v1.json.env.json`, and its schema is
   `covered_earnings_context_report.v1`.

   The exact `covered_earnings_context_configuration.v1` key set is
   `schema_version`, `registration_reference`, `design`,
   `implementation_commit`, `invocation`, `context_input_manifest`,
   `environment_spec`, `correction_input`, `first_estimates_input`,
   `predecessor_context_input`, `vintage_1_input`,
   `legacy_model_metric_specs`, `corrected_model_metric_specs`,
   `predecessor_pairings`, `successor_pairings`,
   `predecessor_comparison_specs`, `successor_comparison_specs`,
   `mismatch_transformation_specs`,
   `consumer_domain_derivation_specs`, `benefit_gap_derivation_specs`,
   `earnings_consumer_dependency_specs`,
   `legal_rounding_rule_specs`, `trusted_consumer_evaluation_specs`,
   `rng_access_specs`,
   `physical_source_cell_specs`,
   `official_source_alias_specs`, `official_source_arithmetic_rule_specs`,
   `analytic_worker_selector`,
   `context_domain_specs`, `attempt_history`, and `output_paths`.
   It uses §10.1's strict parser and exact committed-design,
   repository-ancestry/tree, branch-exact checkout,
   concrete invocation/sentinel, history, and path schemas.

   `rng_access_specs` is the exact
   `covered_earnings_context_rng_access_specs.v1` substitution of §8.1's
   `rng_access_specs.v2` and has the same exact six keys. Its `providers`
   retain the same three authority classes, provider identities,
   argument/flow laws, forbidden domain, coordinator-owned
   `keyed_uniform_lifecycle_cache.v1`, and one-provider-call-per-key/zero-
   repeat-call retry law. Its `lifecycle_phase_domain` deep-equals the full
   13-literal correction object; its bootstrap-implementation rows substitute
   the context coordinator paths/blobs; and its principal authority
   independently enumerates the context worker, coordinator-delegate, and
   proposal-process roles, atomic boundaries, and complete cutoff-specific
   incident-cleanup maps rather than correction-only roles, with the sole
   applicable terminal pair
   `context_evaluated/context_complete`. Canonical order remains
   `provider-order`. Its lifecycle seal embeds context-owned expected and
   actual `g15_worker_lifecycle_projection.v1` preimages reconstructed from
   that authority and the context mount/descriptor/IPC audit; it does not
   depend on correction G15 evidence or a missing context filesystem block.
   It also uses the exact §8.1 effective-boundary lifecycle-row schema and
   complete expected/actual principal event-stream construction and
   comparison, substituting only context authority members and paths.
   Unlike the correction seal, the context
   `rng_provider_lifecycle_seal.v1.status` is `pass` only when those two
   individually valid projections also deep-equal and the independently
   reconstructed expected principal event stream exactly deep-equals the
   immutable actual stream, because the context ceremony has no separate G15
   gate.
   The keyed-midpoint
   expected-call domain is independently expanded from the locked
   correction's complete support and draw namespace and must reproduce its
   exhaustive keyed-uniform registry. The sole ceremony substitution pins
   the coordinator retry-nonce callsite to the committed context coordinator
   implementation rather than the correction runner. Configuration cannot
   add a provider, weaken a forbidden row, shrink a key domain, or supply an
   expected count/hash.

   `context_input_manifest` is an exact ordered, disjoint, closed allowlist.
   Its order is correction primary/sidecar; then every row in the correction
   configuration's complete allowed input domain in its §10.1 sidecar order;
   then first-estimates primary/sidecar; then predecessor anchor
   registration/report/sidecar. The coordinator derives the middle segment
   from the validated correction's `configuration_echo`, not from a
   context-configured subset, and exact-compares every path, schema, vintage,
   role, size where registered, and actual SHA-256 against both the correction
   primary validation rows and sidecar. This segment includes all PSID,
   projection, legal-rule, source-inventory, crosswalk, target, vintage-1,
   and environment-lock bytes required to rematerialize unpublished ledger
   and claim-gap streams. The context `vintage_1_input` and
   `environment_spec` are foreign keys into those unique rows; they cannot
   add a duplicate or alternate file. Every manifest row has the §10.1
   immutable input identity fields and no wildcard, directory, moving alias,
   omitted correction input, duplicate ID/path, or implementation-discovered
   open is permitted. `environment_spec` has the exact §10.1
   lock/package-order schema and resolves to that unique correction-bound
   lock. These objects supply the context sidecar's exact `input_hashes` and
   `dependency_versions`.

   `first_estimates_input` has exactly `publication_commit`, `primary_path`,
   `primary_blob_oid`, `primary_sha256`, `primary_schema_version`,
   `sidecar_path`, `sidecar_blob_oid`, `sidecar_sha256`, and
   `sidecar_schema_version`; paths are the append-only entry-9 pair and every
   identity exact-matches the manifest, committed blobs, and validated bytes;
   the publication commit is an ancestor of `HEAD` and both blobs/bytes
   exact-match at that commit and `HEAD`.
   `vintage_1_input` has exactly `input_id`, `path`, `artifact_vintage_id`,
   `schema_version`, and `sha256`; `input_id` is the unique corresponding
   correction-manifest ID and all five fields exact-match that foreign row.

   `correction_input` has exactly `publication_commit`, `correction_status`,
   `primary_path`, `primary_blob_oid`, `primary_sha256`,
   `sidecar_path`, `sidecar_blob_oid`, `sidecar_sha256`,
   `substantive_model_sha256`,
   `fit_selection_cell_identity_sha256`,
   `evaluation_provenance_sha256`, `direct_law_fact_closure_sha256`,
   `ledger_identity_sha256`,
   `ledger_row_schema_sha256`, `support_keyset_sha256`,
   `expected_ledger_streams_sha256`, `realized_ledger_streams_sha256`,
   `physical_alias_closure_sha256`, `keyed_uniform_registry_sha256`,
   `claim_context_gap_streams_sha256`,
   `trusted_consumer_semantic_authority_sha256`,
   `rng_access_results_sha256`, and
   `trusted_consumer_evaluation_sha256`. `correction_status` is literal
   `pass`.
   `publication_commit` is the merged publication commit, exists, and is an
   ancestor of context `HEAD`; both paths are tracked at that commit and
   `HEAD`, their Git blob OIDs exact-match the configured OIDs, and
   descriptor bytes, `git show <commit>:<path>`, and `git show HEAD:<path>`
   are identical and have the configured SHA-256. Every other value is
   recomputed from that validator-passing pair and exact-matches it. Thus an
   ignored, uncommitted, unmerged, or gate-failing correction cannot start
   context. Full evaluation provenance is bound for audit, while the
   cell-scoped substantive hash remains the correction version.
   `direct_law_fact_closure_sha256` exact-matches the always-nonnull
   correction integrity field. Before rematerializing a ledger or evaluator
   source, the context coordinator independently rebuilds its complete
   preimage from the inherited legal-rule registry, independent inventory,
   coordinator-derived covered/excluded slot concatenations, and the
   correction's complete presence/premise/action results; it does not trust
   the configured `required_micro_facts` array or the stored hash.
   `trusted_consumer_semantic_authority_sha256` exact-matches the correction
   integrity field, but the context coordinator treats it only as a
   comparand: it rebuilds the complete source/domain/rule/unit/root object
   from the correction-bound underlying registries and independently
   extracted predecessor registries before any first-estimates,
   predecessor-result, vintage-1, evaluator-source-value, or
   `before_context` grant. An unequal stored hash or constituent fails
   context registration.
   `keyed_uniform_registry_sha256` is extracted from the unique passing
   correction-midpoint `results.rng_access_results.rows` member and independently
   recomputed from the correction support/draw law; a null or unequal value
   rejects context registration.
   `rng_access_results_sha256` exact-matches the correction's always-nonnull
   integrity and sidecar fields and hashes its complete provider rows plus
   selected-branch lifecycle seal; the context rejects an absent,
   no-eligible-tagged, nonpassing, or pre-rename-mismatched seal.

   `predecessor_context_input` has exactly `publication_commit`,
   `registration_path`, `registration_blob_oid`, `registration_sha256`,
   `report_path`, `report_blob_oid`, `report_sha256`, `sidecar_path`,
   `sidecar_blob_oid`, `sidecar_sha256`, `legacy_model_metric_specs_sha256`,
   `pairings_sha256`, and `comparison_specs_sha256`. The paths identify the
   committed entry-10 anchor registration/report pair. Its publication
   commit is an ancestor of `HEAD`, and the three commit/HEAD blob identities
   and bytes obey the same proof as the correction pair. The coordinator
   independently extracts the complete predecessor registries from those
   validated bytes and exact-compares their canonical hashes, IDs,
   cardinalities, and order; configuration arrays cannot define a smaller
   predecessor domain.

   The configuration pins `runs/first_estimates_v1.json` and sidecar, the
   immutable 15-series vintage-1 artifact, the complete predecessor
   `legacy_model_metric_specs`, exactly 14 predecessor pairings, exactly nine
   predecessor comparison specs, their separately named corrected successor
   registries, and the positional §9.2 transformation.
   Every independently extracted predecessor
   `legacy_model_metric_specs` row has exactly `model_metric_id`, `operands`,
   `operation`, and `unit`. Those strings and selectors are validated and
   retained as immutable `before_context` evidence; they are never executed
   to produce a corrected number. Each position instead produces one
   `corrected_model_metric_specs.v2` row with exactly
   `model_metric_id`, `predecessor_model_metric_id`, `root_node_id`,
   `result_key_fields`, `result_value_type`, `output_enum_domain_id`, `unit`,
   `draw_reduction`, and `dependency_dominator_id`.
   `predecessor_model_metric_id` is the extracted ID;
   `model_metric_id` is that ID plus literal
   `:covered_earnings_corrected_v1`; and `unit` exact-copies the predecessor.
   That copied unit must also equal the independently reconstructed root
   authority unit. `output_enum_domain_id` exact-matches the root authority
   and is nonnull exactly for an enum-valued result.
   The remaining fields exact-match the unique coordinator-reconstructed
   `root_authority_schemas` row; configured
   `trusted_consumer_evaluation_specs.v1.metric_roots` is separately required
   to match but is not the source. The root's complete authoritative typed
   opcode chain—not a formula string, configured DAG, selector callback, or
   runner number—is the operative corrected definition. Its result keys include
   `year_source_class` and include `operative_claim_year` plus
   `career_variant_id` for every claim-context benefit-gap coordinate,
   including every 2013 row.

   The coordinator expands the full predecessor dependency graph before
   deriving those roots. Every
   selector or intermediate whose transitive closure reaches a raw/proxy or
   legacy earnings operand—including benefit amounts, beneficiary or award
   counts, insured-status results, claim outputs, and other non-earnings-
   valued outputs affected by earnings—is represented by a root whose source
   closure contains only the five §8.1 source kinds. A leaf proven
   earnings-independent by the complete graph is reread from the
   correction-bound primitive input; it is not copied from a predecessor
   result. `draw_reduction` is the unique §5.4 corrected law and
   `dependency_dominator_id` is the matching G22 root. No predecessor report
   value, transitively earnings-dependent selector, legacy numeric
   intermediate, or runner-proposed value is a corrected operand.

   Before any decoded first-estimates, predecessor-result, vintage-1, or
   `before_context` value is granted, the coordinator independently rebuilds
   semantic authority from the frozen correction/predecessor registries,
   including the correction-bound
   `consumer_source_field_schema_specs.v1` and
   `consumer_literal_domain_specs.v1`,
   `consumer_evaluator_condition_reason_specs.v1`, and
   `consumer_semantic_recipe_specs.v1`,
   treats the correction's graph and stored authority hash only as
   comparands, rematerializes the correction ledger and claim-gap streams,
   materializes every authority-schema source relation, executes every
   reconstructed opcode chain/root, records
   `trusted_consumer_evaluation.v1`, and hash-locks the complete authoritative
   root stream. The evaluator code is part of the coordinator's pinned
   implementation tree; its mount/descriptor allowlist contains no context
   bytes, runner output, dynamic import, or extension operation. The runner's
   exact-schema complete proposal is normalized and compared, then its process and
   descriptors are destroyed. Context decoding is a separately minted,
   one-way capability. Corrected result JSON is later populated only from the
   locked trusted summaries and is bit-compared with them immediately before
   rename.

   `successor_pairings` and `successor_comparison_specs` are generated from
   the independently extracted predecessor arrays, point to the corrected
   metric IDs and trusted `root_node_id` values in their model-side fields,
   and apply §9.2 to their mismatch arrays while deep-copying every other
   unaffected field. A corrected model-side ratio is a
   `same_key_ratio_positive` root, not a free formula. After the corrected
   root stream is locked, the only context comparison operations are the
   predecessor registry's exact literals
   `model_value_over_official_value` and
   `model_intensity_over_official_intensity`: the coordinator respectively
   computes \(M/O\) or \((M_n/M_d)/(O_n/O_d)\) at identical keys, requires
   every denominator strictly positive, and then applies the registered
   draw reduction. No other operation, Cartesian combination, formula, or
   callback is accepted. The legacy arrays remain immutable
   `before_context` evidence.
   `analytic_worker_selector` is the sole literal
   `modeled_covered_worker_probability_analytic`; a draw indicator or
   20-draw grid fraction is rejected. The three domain/gap/dependency specs,
   the dependency spec's source-field/semantic-recipe subregistries, the
   legal-rounding specs, the trusted evaluator specs, and all three
   physical-source/alias/arithmetic registries exact-match the correction
   configuration.

   `mismatch_transformation_specs.v1` has exactly `schema_version`,
   `algorithm_id`, `retired_codes`, `replacements`, `new_codes`,
   `preserved_codes`, `expected_pairing_count`,
   `expected_comparison_count`, `predecessor_pairings_sha256`,
   `predecessor_comparison_specs_sha256`, and
   `expected_successor_mismatch_arrays_sha256`. Its code arrays/maps and
   algorithm are the literal §9.2 law, the counts are 14 and nine, and its
   predecessor hashes are independently extracted anchor hashes.
   `context_domain_specs.v1` has exactly `schema_version`,
   `corrected_metric_spec_domain_count`,
   `corrected_metric_spec_domain_sha256`,
   `corrected_metric_result_domain_count`,
   `corrected_metric_result_domain_sha256`, `consumer_domain_count`,
   `consumer_domain_sha256`, `claim_context_gap_domain_count`,
   `claim_context_gap_domain_sha256`, `pairing_domain_count`,
   `pairing_domain_sha256`, `comparison_domain_count`,
   `comparison_domain_sha256`, `context_row_domain_count`,
   `context_row_domain_sha256`, `domain_derivation_law`, and
   `failure_disposition`. Counts/hashes are expected comparands derived from
   the validated correction/vintage/anchor inputs; the law is the complete
   Cartesian expansion below and failure disposition is `gate_fail`.

   `context_domain_specs.v1` independently reconstructs the complete
   Stage A–D benefit and unsplit-revenue domains, the corrected metric-spec
   domain from the complete independently extracted predecessor metric
   registry, the expanded corrected metric-result domain, the 14-pairing and
   nine-comparison successor domains, and the complete context-row domain.
   Configured counts and hashes are expected comparands,
   never selectors. Missing, extra, duplicate, reordered, or difficult rows
   fail; ledger absence cannot shrink a domain. The runner rematerializes
   every expected and realized corrected stream and every operative-claim
   gap stream, verifies their hashes, and reruns the complete transitive
   dependency-dominator proof. Every final output or intermediate with any
   transitive earnings dependency must be downstream of the corrected-ledger
   accessor, regardless of its published unit; ledger-retained raw proxy is
   audit-only and every evaluable legacy/proxy numeric path is confined to
   typed `before_context`.

   The §9.2 mismatch transformation runs separately and positionally over all
   14 `successor_pairings[*].mismatch_codes` arrays and all nine
   `successor_comparison_specs[*].mismatch_codes` arrays. Successor registry
   row cardinality/order, predecessor IDs, and every unaffected field must
   deep-equal the independently extracted frozen predecessors;
   mismatch-array contents and cardinality obey only §9.2's positional
   transformation. No
   omitted metric, pairing, comparison, seam, opening-backfill context, or
   revenue row is allowed. Every certified worker denominator is recomputed
   from analytic probabilities within projection draw/year before the frozen
   ratio-then-mean reduction.

   This context run imports the complete §10 ceremony kernel, not a weaker
   analogue: fixture-only rehearsal; strict bytes; committed repository and
   `sys.orig_argv` proof; concrete fresh-empty pycache sentinel; exclusive
   coordinator lock; configuration-derived retry-authority reservation;
   durable read-only initial claim before any production read; claim
   revalidation on every access; append-only incidents; same-process opaque
   one-shot `_RetryReceipt`; durable retry claim; and complete-history
   fresh-registration adjudication after a killed attempt, receipt loss, or
   retry failure. Context-specific schema literals and path prefixes replace
   correction-specific ones under this exact substitution:
   `covered_earnings_context_initial_attempt_claim.v1`,
   `covered_earnings_context_retry_authority.v1`,
   `covered_earnings_context_retry_attempt_claim.v1`,
   `covered_earnings_context_incident.v1`, and
   `covered_earnings_context_fresh_registration_adjudication.v1`; their key
   sets, strict parsing, hash preimages, descriptor states, fsync/readback
   laws, and one-shot receipt bindings are otherwise §10-exact.
   The sole invocation substitution is
   `runner_identity.repository_relative_path:
   scripts/run_covered_earnings_context_report.py`, with `orig_argv[5]`,
   absolute path, descriptor identity, implementation/HEAD blob OIDs, and
   bytes bound exactly as in §10.1.
   `output_paths` has exact `output_version:
   covered_earnings_context_report_v1`, the primary/sidecar paths above, and
   traversal-free prefixes
   `runs/covered_earnings_context_report_incident_`,
   `runs/covered_earnings_context_report_attempt_`,
   `runs/covered_earnings_context_report_retry_authority_`,
   `runs/covered_earnings_context_report_retry_`, and
   `runs/covered_earnings_context_report_fresh_registration_`.
   §10.5's durable state transitions, exposure dispositions, and sole
   normative execution law apply with no context-specific weakening.

   It uses that same full `rng_lifecycle_phase_domain.v1` and the exact
   bootstrap identity/lifecycle-sequence schemas. Its operationally permitted
   lifecycle literals are
   exactly `bootstrap`, `registration_prelaunch`, `durable_attempt_claim`,
   `preparation`, `evaluation`, `lifecycle_closure`, `publication`,
   `incident_handling`, and `process_exit`; correction-only `fitting`,
   `selection`, `substantive_lock`, and
   `preheldout_structural_verification` are forbidden in context provider and
   denial traces. Its phases are exactly: `registration_prelaunch` for
   registration/pre-launch; `durable_attempt_claim` for the durable claim;
   `preparation` to validate and rematerialize the locked correction and
   independently derived domains; `evaluation` to reconstruct semantic
   authority anew, exact-compare the configured DAG, execute the authoritative
   chains, compare the exact-schema runner proposal, lock every corrected root
   and dependency proof, destroy every runner proposal capability, only then
   grant a separate context decoder access to the 15 vintage-1 series, and
   compute every registered context row; `lifecycle_closure` to destroy every
   delegated provider-capable context principal at its effective boundary,
   exact-compare the complete expected and actual event streams, consume the
   `delegated_provider_capable_set_empty` barrier and seal sequences, enter
   irreversible deny-all state, and freeze and validate the whole-lifecycle
   `rng_access_results`; and `publication` to publish. Its exact normal
   transition chain is
   `bootstrap → registration_prelaunch → durable_attempt_claim → preparation
   → evaluation → lifecycle_closure → publication → process_exit`.
   Exception, receipt-authorized retry, terminal-incident, and direct
   no-allocation exit transitions are exactly §10.2; no correction-only state
   may appear in a context provider, denial, principal, event-stream, barrier,
   or seal row.
   The trusted
   evaluator has no first-estimates, predecessor, vintage-1,
   `before_context`, fitting, selection, model
   mutation, threshold, seed, direction-based rejection, or alternate-ledger
   capability. The context decoder cannot change a locked corrected root.
   Immediately before the context primary rename, the coordinator again
   reconstructs semantic authority without the configured graph/hash,
   exact-compares every constituent and branch-reachable root byte, and
   reconstructs the provider ledger/cache and lifecycle-seal comparand from
   the same live bootstrap objects. It requires unchanged wrapper-registry,
   live wrapper-object, and audit-hook identities, deny-all state, exact
   serialized RNG evidence and hashes, and zero post-seal/sticky counts, with
   no intervening callback.
   The coordinator publishes every before/after diagnostic with no required
   direction and calls the event `structurally-out-of-fitting-sample`, never
   unseen: those 2015–2022 values have already been viewed.

   In the imported §10.3 schemas,
   `heldout_vintage_exposure_state`/`exposure_state` means decoded
   vintage-1/context exposure. An unchanged retry still requires the private
   same-process no-external-yield and no-exposure receipt. A fresh
   same-output-version registration is allowed only when both final paths are
   absent and exposure is `none`. Possible or confirmed exposure has
   disposition `heldout_vintage_tainted` and is terminal for context v1; a
   partial primary additionally requires a newly ratified output version, and
   a complete pair is terminal. Context therefore imports §10.5 without
   weakening it.

   The context primary has exactly `schema_version`, `artifact_id`,
   `registration_reference`, `configuration_echo`, `runtime_provenance`,
   `attempt_evidence`, `status`, `locked_correction`, `domain_results`,
   `corrected_metric_results`, `pairing_results`,
   `comparison_spec_results`, `dependency_results`,
   `trusted_consumer_evaluation`, `rng_access_results`, `context_rows`,
   `label_retirement_certificate`, `integrity`, and `certifies_nothing`.
   `schema_version` and `artifact_id` are both
   `covered_earnings_context_report.v1`; runtime and attempt evidence use
   §10's exact primary schemas with the context literals above; and
   `certifies_nothing` is the constant ordered array
   `["not-population-aligned",
   "not-individual-administrative-covered-earnings-truth",
   "not-ledger-entry-11-resolution-before-publication-pr-merge"]`.
   `locked_correction` deep-equals `correction_input`. Every result array has
   the independently derived exact cardinality/order and no empty success
   branch.

   `domain_results` has exactly `corrected_metric_spec_domain`,
   `corrected_metric_result_domain`, `consumer_domain`,
   `claim_context_gap_domain`, `pairing_domain`, `comparison_domain`, and
   `context_row_domain`. Each value has exactly `expected_count`,
   `actual_count`, `missing_count`, `extra_count`, `expected_sha256`,
   `actual_sha256`, and `status`; counts and hashes are actual evidence and
   status is `pass` iff counts/keysets exactly agree. The two registry
   transformation arrays have exactly 14 and nine rows. Each
   `pairing_results` or `comparison_spec_results` row has exactly `position`,
   `predecessor_row_sha256`, `successor_row_sha256`,
   `mismatch_transformation_sha256`, and `status`, preserving actual
   unfavorable hashes. `corrected_metric_results` is independently expanded
   over every corrected metric × applicable verified calendar year ×
   registered stratum × statistic under `domain_derivation_law`; its count
   and ordered key hash must equal
   `context_domain_specs.corrected_metric_result_domain_count` and
   `context_domain_specs.corrected_metric_result_domain_sha256`. Its exact
   order is corrected-metric position, ascending year with null career-year
   last, `year_source_class`, applicable operative-claim/career context order,
   stratum order, then statistic order. Each row has exactly
   `model_metric_id`, `calendar_year`, `year_source_class`,
   `operative_claim_year`, `career_variant_id`, `stratum_id`, `statistic`,
   `projection_draw_count`, `correction_draw_count`, `mean`, `sample_sd`,
   `unit`, `draw_reduction`, `dependency_dominator_id`, `status`, and
   `reason_code`. The two context coordinates are nonnull exactly for annual
   benefit rows whose class is
   `structural_gap_imputed | claim_specific_boundary_gap` and otherwise null
   where the independent domain says not applicable. Every 2013 row is the
   latter class and has both coordinates nonnull; no unconditional or revenue
   2013 row exists. A nonannual career row has `calendar_year`,
   `year_source_class`, `operative_claim_year`, and `career_variant_id` all
   null. Draw counts are the exact nonnegative cardinalities
   implied by the registered reduction and cannot choose the domain. Each
   `dependency_results` row has exactly `model_metric_id`,
   `root_node_id`, `dependency_dominator_id`, `graph_sha256`,
   `expected_root_semantic_closure_sha256`,
   `actual_root_semantic_closure_sha256`,
   `forbidden_legacy_path_count`, `dependency_pathset_sha256`,
   `analytic_denominator_trace_sha256`,
   `trusted_result_stream_sha256`, `runner_result_stream_sha256`,
   `runner_mismatch_count`, `evaluation_trace_sha256`, and `status`. There is
   exactly one
   dependency row per `corrected_model_metric_specs` row in identical order;
   all three IDs exact-match that spec/root, and every corresponding corrected
   result exact-matches the same ID pair. Both counts are nonnegative JSON
   integers. Dependency status passes iff both are zero, the path-set hash
   equals the independently expanded complete transitive path set, the graph
   and trace hashes equal the coordinator's complete evaluation, the actual
   root-semantic closure hash equals the expected coordinator-reconstructed
   authority hash, the trusted and normalized runner root streams match, and
   the analytic-denominator trace proves the registered selector/reduction
   wherever applicable; it fails otherwise and retains the unfavorable
   count/hashes.
   `trusted_consumer_evaluation` is the exact §8.1 object independently
   recomputed in this context run. Its semantic-authority object is rebuilt
   without the correction's graph/hash, all five semantic comparison counts
   are zero, and its graph spec merely exact-matches that authority and the
   locked correction comparand. Its authoritative root stream supplies every
   `corrected_metric_results` numeric bit, and its runner comparison has zero
   missing, extra, value-mismatched, and packet-schema-mismatched rows on a
   pass. Its own integrity hash is separate from the correction report's
   namesake input hash; both remain bound.
   `rng_access_results` has exactly `evaluation_status: evaluated`,
   `lifecycle_seal`, and `rows`; it has no not-evaluated branch.
   `lifecycle_seal` is the context variant of the exact §8.1 object with
   `terminal_branch: context_evaluated` and
   `evaluation_completion: context_complete`; every other field and
   pass/recheck law is unchanged. `rows` has exactly one row per context
   `rng_access_specs` provider in registered order and the exact §10.2 row
   schema: `provider_id`, `authority_class`, `call_count`,
   `argument_trace_sha256`, `keyed_uniform_registry_sha256`, and `status`.
   The keyed-midpoint row passes only when its complete context
   rematerialization call ledger exact-matches the independently expanded
   correction namespace and its nonnull registry hash equals
   `correction_input.keyed_uniform_registry_sha256`. The context
   lifecycle cache exact-matches the §8.1 miss/store/hit law across any
   authorized retry, so a partially populated first attempt never duplicates
   a midpoint-provider call. The context
   retry-nonce row passes only for the one process-lifecycle 32-byte call,
   exact context-coordinator callsite/flow, and zero new calls on an
   authorized retry; its registry hash is null. Every forbidden row passes
   only with zero calls, canonical empty trace, and null registry hash.
   Unequal counts/hashes and forbidden calls remain serialized as failures;
   every row and the lifecycle seal must pass for primary `status: pass`.
   Separately, a passing corrected metric row has finite output numbers,
   nonnegative SD, and null reason; an unevaluable failing metric has both
   numbers null and the exact structural reason; and an empirical failing
   metric retains finite numbers and its exact failure reason. Every row
   status is `pass | fail` under its independently registered comparator.

   `context_rows` is independently expanded—not selected—from the Cartesian
   registry of all 15 vintage-1 series, every applicable registered vintage
   year, every corrected successor metric/pairing/comparison that names that
   concept, and the registered overall/stratum statistics. Its immutable
   expected count, keyset SHA-256, and order (vintage-1 §6.3 order, ascending
   year, source class, applicable claim/career context, successor-registry
   position, statistic/stratum order) are stored in `context_domain_specs`
   and independently reconstructed from the validated vintage-1 and
   predecessor anchor registries; configuration counts are only comparands.
   A missing concept, hard year, predecessor row, or null observed value
   retains a row and fails.

   Each context row has exactly `row_id`, `vintage_1_series_id`,
   `calendar_year`, `year_source_class`, `operative_claim_year`,
   `career_variant_id`, `successor_registry_kind`,
   `successor_registry_position`, `corrected_metric_id`, `statistic`,
   `stratum_id`, `corrected_mean`, `corrected_sample_sd`, `vintage_1_value`,
   `difference`, `unit`, `draw_reduction`, `evidence_role`, `status`, and
   `reason_code`. These four year/context fields exact-match the corrected
   metric row. Registry-declared inapplicable coordinates alone are null.
   `evidence_role` is literal `structurally_out_of_fitting_sample`;
   `difference` is corrected minus vintage-1 under the registered common
   unit, with no directional criterion. A complete row has finite values and
   nonnegative SD; a structurally unavailable row has null affected values,
   `status: fail`, and the exact registered reason. No context-row value,
   sign, rank, or direction can enter its domain, threshold, inclusion, or
   certificate comparator.

   Primary `status` is `pass | gate_fail`. It is `pass` iff every domain,
   metric, transformation, dependency, trusted-evaluator, RNG-access, and
   context row passes and the
   positive certificate below is nonnull. It is `gate_fail` iff at least one
   row fails, all reachable evidence is nevertheless serialized, and the
   certificate is null. Empirical, completeness, dependency, or
   transformation failure is therefore a complete publishable result, not
   an incident or retry. A pre-seal provider-row failure likewise may publish
   as `gate_fail`, but a lifecycle-seal failure, nonzero post-seal/sticky
   value, or immediate pre-rename recheck mismatch is an invariant incident
   and permits no context rename.

   `integrity` has exactly `configuration_sha256`, `sidecar_sha256`,
   `correction_input_sha256`, `domain_results_sha256`,
   `corrected_metric_spec_domain_sha256`,
   `corrected_metric_result_domain_sha256`, `context_row_domain_sha256`,
   `corrected_metric_results_sha256`, `pairing_results_sha256`,
   `comparison_spec_results_sha256`, `dependency_results_sha256`,
   `trusted_consumer_semantic_authority_sha256`,
   `trusted_consumer_evaluation_sha256`, `rng_access_results_sha256`,
   `context_rows_sha256`, `attempt_evidence_sha256`, and
   `label_retirement_certificate_sha256`. Each is 64 lowercase hex and hashes
   the complete canonical named value, including canonical JSON null for a
   failed report's certificate. The three explicit domain hashes equal the
   corresponding `domain_results.*.actual_sha256` values; no configured
   expected hash is substituted.
   `trusted_consumer_semantic_authority_sha256` is the digest independently
   reconstructed in the context run and equals the authority digest inside
   the namesake evaluation object; it is not copied from
   `correction_input`.
   `trusted_consumer_evaluation_sha256` hashes the complete canonical
   namesake object, including actual runner mismatch evidence. It binds the
   exact context sidecar and all actual result streams through §10's acyclic
   sidecar-first law. `rng_access_results_sha256` likewise hashes the complete
   tagged object, including its lifecycle seal and every ordered provider row
   with unfavorable counts/traces.

   The context sidecar has exactly `schema_version`, `artifact_path`,
   `registration_reference`, `configuration_sha256`,
   `implementation_commit`, `invocation`, `runtime`, `attempt_evidence`,
   `input_hashes`, `dependency_versions`, `substantive_model_sha256`,
   `evaluation_provenance_sha256`, `ledger_identity_sha256`,
   `trusted_consumer_semantic_authority_sha256`,
   `trusted_consumer_evaluation_sha256`, `rng_access_results_sha256`, and
   `context_rows_sha256`. Its schema
   literal is
   `covered_earnings_context_environment.v1`; artifact path is the context
   primary; the three correction identities exact-match `correction_input`;
   inputs and dependencies are the complete manifest/lock expansions above;
   the semantic-authority and RNG-access hashes exact-match their primary
   integrity fields; and
   all shared fields deep-equal the primary/configuration. No primary digest
   enters it.

   On a `status: pass` result, `label_retirement_certificate` has exactly
   `status`, `correction_evaluation_path`,
   `primary_sha256`, `substantive_model_sha256`,
   `fit_selection_cell_identity_sha256`,
   `evaluation_provenance_sha256`,
   `correction_ledger_identity_sha256`, `context_report_schema`,
   `condition_8`, `condition_8_evidence`, `successor_labels`,
   `retired_codes`, `replacements`, `new_codes`, and `preserved_codes`.
   `status` is `eligible_on_publication_pr_merge`; `condition_8` is boolean
   true; `context_report_schema` is the literal
   `covered_earnings_context_report.v1`; and
   `correction_ledger_identity_sha256` equals
   `correction_input.ledger_identity_sha256`.
   `correction_evaluation_path` equals `correction_input.primary_path`;
   `primary_sha256`, the substantive-model SHA, fit/selection identity SHA,
   and evaluation-provenance SHA exact-match their namesake
   `correction_input` fields.
   `condition_8_evidence` has exactly
   `corrected_metric_spec_domain_count`,
   `corrected_metric_spec_domain_sha256`,
   `corrected_metric_result_domain_count`,
   `corrected_metric_result_domain_sha256`, `consumer_domain_count`,
   `consumer_domain_sha256`, `claim_context_gap_domain_count`,
   `claim_context_gap_domain_sha256`, `claim_context_gap_stream_count`,
   `claim_context_gap_streams_sha256`, `pairing_domain_count`,
   `pairing_domain_sha256`, `comparison_domain_count`,
   `comparison_domain_sha256`, `successor_pairings_sha256`,
   `successor_comparison_specs_sha256`, `dependency_results_sha256`,
   `trusted_consumer_semantic_authority_sha256`,
   `trusted_consumer_evaluation_sha256`, `rng_access_results_sha256`,
   `physical_alias_closure_sha256`, `analytic_denominator_trace_sha256`,
   `mismatch_transformation_sha256`, `context_row_domain_count`,
   `context_row_domain_sha256`, `context_row_count`, and
   `context_rows_sha256`. Pairing and comparison counts are exactly 14 and
   nine; successor hashes bind the complete generated arrays, not only their
   mismatch fields. Domain counts/hashes equal the corresponding actual
   `domain_results` values. `claim_context_gap_stream_count` is the exact sum
   of the lengths of the rematerialized
   `claim_context_gap_identity.expected_gap_streams` and
   `.realized_gap_streams`; its hash is the canonical complete identity hash
   already bound by `correction_input`.
   `dependency_results_sha256` hashes the complete ordered result array and
   equals `integrity.dependency_results_sha256`.
   `trusted_consumer_semantic_authority_sha256` equals its integrity
   namesake and binds the context coordinator's newly reconstructed complete
   source/domain/rule/unit/root authority rather than the correction's stored
   comparand.
   `trusted_consumer_evaluation_sha256` equals
   `integrity.trusted_consumer_evaluation_sha256`; the trusted root-stream
   hash inside that object supplies every corrected result byte.
   `rng_access_results_sha256` equals its integrity namesake and binds the
   context lifecycle seal plus all provider rows.
   `analytic_denominator_trace_sha256` hashes the canonical ordered array of
   every `dependency_results[*].analytic_denominator_trace_sha256` in metric
   order. `mismatch_transformation_sha256` hashes a canonical object with
   exactly `pairing_transformation_hashes` and
   `comparison_transformation_hashes`, the respective 14- and nine-element
   ordered arrays of result-row transformation hashes.
   `physical_alias_closure_sha256` exact-matches the correction input.
   `context_row_count` is the actual `context_rows` length and its hash
   equals `integrity.context_rows_sha256`; its domain pair equals the actual
   `context_row_domain` result. Successor pairing/comparison hashes cover the
   complete configuration arrays in registry order.
   Every other count is the positive independently derived cardinality.
   Labels are the exact §1 array and every code array/map
   exact-matches §9.2. A failed report carries JSON null instead, publishes
   its complete failure and structural evidence, and changes no label. The
   artifact cannot assert condition 9; only its publication-PR merge
   activates the certificate and resolves entry 11.

2. **W1 bridge on corrected earnings.** W1 can build the national population
   bridge on the immutable corrected ledger rather than the labor-income
   proxy. Roster, weights, population alignment, and national levels remain
   W1's authority, not this correction's. W1 must pin
   `substantive_model_sha256`, `fit_selection_cell_identity_sha256`,
   `evaluation_provenance_sha256`, `direct_law_fact_closure_sha256`,
   `trusted_consumer_semantic_authority_sha256`,
   `rng_access_results_sha256`, the physical alias closure,
   consumer-domain/gap/dependency registries, row schema, ledger identity,
   support key set, and applicable expected/realized stream hashes. It must
   independently reconstruct the applicable domain, rematerialize and verify
   every hash and the selected-branch lifecycle-seal status before bridging,
   and may not rewrite components.

3. **Orthogonal first-estimates successors.** Spouse/survivor entitlement
   adaptation, behavioral claiming, and the `FORWARD` production object
   remain separate subsequent work. Stronger covered-earnings evidence
   requires a later sealed official vintage registered before exposure or a
   separately authorized administrative micro link.

## 13. Complete VERIFY disposition

Every scoping `VERIFY` item appears exactly once below. A registration-time
verification supplies either exact registered bytes/rules or a failure; it
never supplies a default. Where one survey sentence joined a legal rule to an
aggregate-magnitude claim—state/local, student, or residual exclusions—the
two independently falsifiable claims are split once: the rule is in bucket B
and the outside-v1 magnitude is in bucket C. No atomic claim appears in two
buckets.

### 13.1 Bucket A — resolved in design from committed bytes

No survey fact literally tagged `VERIFY` is resolved solely by the committed
Supplement bytes, so this bucket is empty. The coordinator-required
committed-byte determination is recorded separately as **D-A1**: Table
4.B2/4.B11 component cells and 1968–2014 training-boundary rows exist, and
§6.1 cites their exact headers, boundary rows, notes, byte identity, and ten
cross-table discrepancies. D-A1 resolves an input/open decision, not an extra
survey `VERIFY`. The actual tagged “latter” clause—the covered-share
universe—is V-B7.

### 13.2 Bucket B — registration-time fail-closed verification

| ID | `verification_class` | VERIFY item | Required disposition and failure consequence |
|---|---|---|---|
| V-B1 | `registration_required` | Exact Section 218 and mandatory state/local coverage law and effective dates | Pin controlling primary legal-authority bytes and every effective-year rule in §4.1. A missing/conflicting authority byte or effective-year legal rule aborts. `state_of_residence`, `section_218_group`, `section_218_position`, and `public_retirement_system_participation` are exact inventory-backed purposes. An absent person-level fact is not a legal-authority gap; after authority verifies, the coordinator-derived absence takes the applicable rule's singular `unresolved_action` runtime branch. |
| V-B2 | `direct_only_optional` | Exact clergy, minister, church-employee, religious-order, and exemption rules | Missing/conflicting authority disables direct classification for the exact predeclared inventory rows and applies each row's frozen `optional_row_consequences` entry. `ministerial_service`, `clergy_remuneration`, `church_employee_service`, `religious_order_service`, and `clergy_or_religious_exemption` are exact inventory-backed purposes. After authority verifies, a coordinator-derived missing required microfact takes the applicable rule's singular `unresolved_action`. |
| V-B3 | `direct_only_optional` | Exact historical residual-exclusion rules for domestic/agricultural thresholds, election, family/casual, foreign-government/international-organization, nonresident-alien, and similar service | Missing/conflicting authority disables direct classification for the exact predeclared inventory rows and applies each row's frozen `optional_row_consequences` entry. `domestic_service`, `agricultural_service`, `election_work`, `family_service`, `casual_service`, `foreign_government_service`, `international_organization_service`, and `nonresident_alien_status`, together with the standard amount/unit/exposure purposes for thresholds, are exact inventory-backed inputs. After authority verifies, a coordinator-derived missing required microfact takes the applicable rule's singular `unresolved_action`. No runtime importance judgment exists. |
| V-B4 | `registration_required` | Historical pre-1990 SECA eligible-concept, net-earnings-factor, threshold, and coordination crosswalk | Pin every effective-year transform. Any year or transform gap aborts registration. |
| V-B5 | `registration_required` | Exact common 1968–1974 and spouse/secondary-job industry/occupation classifier availability and meaning | The independent inventory must cover every wave×role×job×component/context slot. Exact `structural_missing` is allowed; missing inventory/crosswalk evidence or a false common mapping aborts. |
| V-B6 | `registration_required` | Exact pre-modern spouse and secondary-job source concepts, self/other and incorporation support, and wave→reference-year mapping | Register the complete wave/reference map and every spouse/secondary-job source concept/code map. Reference-year 1975 field `V4379` is `mixed`; exact 1976–1977 concepts must register or abort. |
| V-B7 | `registration_required` | SSA covered-share publication, table, vintage, annual definition, numerator, denominator, duplicate-worker treatment, timing, and universe | Pin source bytes proving one exact numerator/denominator universe and the frame-relative model analogue. Any mismatch, including annual-unique versus point-in-time, aborts; no approximate 94-percent input exists. |
| V-B8 | `registration_required` | Earlier enrollment-field coverage and a stable cross-wave mapping | Inventory and stable mapping must register for every slot. Exact structural absence is allowed; missing inventory evidence aborts, and enrollment still cannot establish employer-school nexus. |
| V-B9 | `direct_only_optional` | Exact effective-year student-service exception and employer-school nexus rule | Missing/conflicting authority forbids direct exclusion for the exact predeclared rows and applies each row's frozen `optional_row_consequences` entry. `employer_school_nexus` and `statutory_student_service` are exact inventory-backed purposes. After authority verifies, a coordinator-derived missing required microfact takes the rule's singular `unresolved_action`. |

The legal registry also fail-closes CSRS/FERS/CSRS Offset through
`federal_retirement_system` and `federal_service`, and Railroad treatment
through `railroad_covered_employer` and `railroad_covered_service`; all four
are exact inventory-backed purposes even though those source-fact absences
were not separately tagged `VERIFY` in the survey.

### 13.3 Bucket C — explicitly outside v1

| ID | VERIFY item | Consequence |
|---|---|---|
| V-C1 | Roughly one-quarter of state/local workers or about six million are noncovered | No v1 magnitude prior, bound, tolerance, attribution, or sign claim uses it. |
| V-C2 | Railroad employment is well below one percent nationally | No v1 aggregate bound, candidate weight, or “too small” gate uses it. |
| V-C3 | Student-worker payroll/worker magnitude and its asserted worker-count-versus-payroll effect | No magnitude, relative-effect, prior, bound, tolerance, or sign claim is used. Exact law, separately, is V-B9. |
| V-C4 | Magnitudes of residual statutory exclusions | No aggregate bound or decomposition claim is made. Exact legal rules, separately, are V-B3. |
| V-C5 | Duncan and Hill (1985) bibliographic metadata | It supplies no coefficient, prior, bound, tolerance, or validation claim. |
| V-C6 | Bound and Krueger (1991) bibliographic metadata | Same consequence. |
| V-C7 | Rodgers, Brown, and Duncan (1993) bibliographic metadata | Same consequence. |
| V-C8 | Pischke (1995) bibliographic metadata | Same consequence. |
| V-C9 | Abowd and Stinson (2013) bibliographic metadata | Same consequence. |
| V-C10 | Existence, years, consented subsample, and accessibility of a restricted PSID–SSA link | V1 has no administrative micro target and makes no administrative-validation claim. Acquiring or using a link requires a new authority, correction vintage, and fresh registration. |

Any future use of a bucket-C fact requires a new design/registry version and
moves that fact into a byte-pinned, registration-time authority. No bucket-C
fact supplies a v1 rule, coefficient, target, field, tolerance, or claim.

## 14. Ratification and decision-closure checklist

### 14.1 Open-decision settlements

| Scoping open decision | Settlement |
|---|---|
| Exact estimands | §3 freezes uncapped covered wages, pre-SECA net earnings, SECA base, noncovered/unresolved amounts, person taxable payroll, benefit-creditable earnings, modeled worker incidence, and zero v1 deemed credits. |
| Full support feasibility | G01 independently reconstructs the complete Stage A–D benefit and unsplit 2015–2022 revenue domains; every base-ledger and operative-claim gap key must exist. Missing support fails rather than shrinking a configured selector; failure permits only §11.2 and retains benefit proxy labels. |
| Historical legal authority and named classes | §4.1 freezes authority precedence, a byte-pinned effective-year registry, schema-bound covered/excluded premises, the exact inventory-slot-derived required-fact array with empty iff both premise sets are empty, source-backed typed parsers, coordinator-evaluated presence/premise/action evidence, constant transforms only for unconditional rules, exact transform precedence/conflict law, and fail-closed treatment for every named class. |
| Complete PSID crosswalk and era seams | §4.2 requires an independently byte-pinned every-wave×role×job×component/context×35-purpose inventory—including state and every named direct-law microfact slot—with exact `present \| structural_missing` disposition, a separate all-key disposition stream and component-slot assembly, frozen structural-missing consequences, the full wave→reference-year/source-class map, first-class `mixed`, and executable value-code, annualization, reconciliation, job-match, SE-aggregation, and coverage-group registries. Reference-year 1975 is mixed; exact 1976–1977 concepts are registration-required. |
| Production cutoff, entrants, and odd years | Direct questionnaire lineage is 1968–1996 and even 1998–2012; structural odd gaps are derived per benefit career only after the operative-claim cutoff, including a claim-specific 2013; 2014 is the boundary and 2015–2022 are projected. Exact support/metric schemas carry source class, every annual gap result carries operative-claim/career coordinates, opening-backfill replacement precedes gap derivation, and revenue has no 2013 consumer row. |
| Probabilities, imputations, draws, nonlinear AIME/PIA | §§5.1 and 5.4 make expected mappings primary, require 20 keyed correction draws where nonlinear distribution matters, and compute benefits within career draw. |
| Target artifact, years, loss, partition, viewed cells | §6 creates immutable vintage 2 and requires target-ID, declared, resolved observation, operand, physical-cell, ancestry, selector, and result years to agree before deriving 1968–2008 train, 2009–2014 validation, and 2015–2022 diagnostic roles. Physical ancestry closes over cross-vintage aliases plus exact and structural siblings; structural dependence carries exposure without asserting displayed numeric equality or inferring a rounding interval. None of vintage 1 fits and viewed-cell honesty is explicit. |
| B2/B11 and covered-share extraction | §6 and D-A1 retain the pinned source hashes, literal ten-row discrepancy registry, and pre-2015 scale-free targets; V-B7 requires an exact covered-share universe. Model choice binds only `fit_selection_cell_identity.v1`; full evaluation provenance is separate, and G21 mutates every held-out/zero-weight/exclusive byte on both selected and no-eligible branches while requiring parameters, dispositions, selection branch, branch-tagged selected-model projection, gates, and conditions 1–6 to remain byte-identical. |
| Post-calibration label vocabulary | §1 freezes exactly `frame-relative`, `modeled-covered-earnings`, `aggregate-concept-calibrated-not-population-aligned`. |
| Cap, SE threshold/loss, incorporated owners, historical SECA | §§3.2 and 4.1 freeze component floors, within-SE-only loss netting, effective-year law, wage-first residual cap, incorporated salary, and excluded distributions. |
| Candidate set, thresholds, namespace, replay, certificate | §§5.3–5.4, 6.2, 7, 8, and 9 freeze candidates, cell-scoped namespace, exact six replays, all 22 gates, independent consumer/metric domains, corrected-only dependency domination, coordinator-reconstructed source identity/type/unit, domain, legal/operation-rule, exact unit-algebra, and root-opcode authority for the 17-op evaluator, an exact proposal schema, analytic certified denominators, and no post-hoc rescue. |
| Versioning, ceremony, and mismatch disposition | §§6, 9, 10, and 12 freeze separate substantive/evaluation identities, strict committed registration, durable claims, opaque one-shot retry authority, process-lifecycle nonce metering and exact-once keyed-uniform retry caching, branch-general provider-ledger/cache sealing, irreversible post-seal deny wrappers, immediate pre-rename rechecks, fresh-registration adjudication, no post-exposure same-output exception, and positional transformations of all 14 pairing plus nine comparison mismatch arrays. |

### 14.2 Ratification checklist

Ratification requires affirmative evidence for every item:

- [ ] The document settles every §14.1 decision with no contradictory rule.
- [ ] Every scoping `VERIFY` appears in exactly one §13 bucket and no
  unresolved VERIFY supplies a coefficient, rule, field, target, or claim.
- [ ] Every Bucket-B VERIFY has the exact `registration_required |
  direct_only_optional` class; required claims abort and optional claims have
  only predeclared source-inventory-row consequences; all nine rows
  exact-match `verification_claim_specs.v1` and its result registry.
- [ ] The legal registry and independent PSID source-field inventory have
  literal ordered IDs, exact key sets/types, effective/reference-year
  coverage, source hashes, every questionnaire slot, all 35 purposes
  including state and every named direct-law microfact, exact
  `present | structural_missing` dispositions, complete missing-token laws,
  and missing/duplicate/extra rejection.
- [ ] Every covered/excluded fact is an exact typed binding to one or more
  independent inventory slots; `required_micro_facts` deep-equals the
  coordinator's covered-then-excluded slot concatenation and is empty iff
  both binding arrays are empty. The coordinator alone derives typed
  presence/value commitments, premise booleans, and the action fold over the
  complete record×rule×fact domain. Fact-bearing constant transforms and the
  empty-required/uninventoried-premise/constant-`noncovered` attack fail
  registration; runner booleans or values are impossible; G06 exact-compares
  the runtime ledger; and G17 exact-compares all 15 domains.
- [ ] The crosswalk exact-matches that independent inventory and pins the
  all-key dispositions and component-slot assembly; it pins structural-
  missing consequences, the complete wave→reference-year/source-class map,
  `mixed` remuneration, value-code maps, annualization, reconciliation, job
  matching, SE-aggregation grouping, and coverage-state grouping as
  executable registries.
- [ ] Vintage 2 has immutable identity, exact source/cell provenance,
  canonical serialization, pinned hashes, offline reproduction, and an
  append-only refresh law.
- [ ] `calibration_target_specs.v2` proves equality of target-ID, target,
  source, observation, operand, physical-ancestry, selector, result, and trace
  years; recomputes role from verified year; and freezes every dependency,
  loss, weight, tolerance, transformation, unit, and selector before fitting.
- [ ] Physical source ancestry closes over the complete frozen cross-vintage,
  shared-primitive, republication, exact-arithmetic-sibling, and
  structural-formula-sibling registry with no role laundering or aliased
  held-out primitive; structural-only rows encode dependence and exposure
  without a displayed-value equality or inferred rounding interval.
- [ ] Model choice binds only the exact cell-scoped fit/selection identity;
  full evaluation provenance is separate, and the nonempty G21 fixture
  changes every held-out/zero-weight/exclusive source byte while parameters,
  losses, dispositions, selected/no-eligible branch, branch-tagged
  selected-model projection, gates, and conditions 1–6 remain
  byte-identical; the battery runs when no candidate is eligible.
- [ ] All 15 vintage-1 series are structurally inaccessible to fitting and
  selection and described as already viewed.
- [ ] Candidate, hyperparameter, convergence, selection, tie, Option-C, and
  candidate-failure laws exact-match registration; Option C is a
  singleton-dimension, diagnostic-only typed `before_context` branch with
  exact claim-context coordinates and failure serialization.
- [ ] The complete Stage A–D benefit and unsplit revenue domains are
  independently reconstructed; missing support cannot shrink them; every
  structural gap is derived only after the operative claim cutoff; and
  revenue has no 2013 row.
- [ ] Every exact support and corrected metric-result schema carries
  `year_source_class`; annual benefit gap rows carry nonnull
  `operative_claim_year` and `career_variant_id`, every 2013 row is
  claim-specific, nonannual coordinates are explicitly null, and no
  unconditional or revenue 2013 metric exists.
- [ ] Every final corrected earnings-dependent metric is transitively
  dominated by the corrected ledger; ledger-retained raw proxy is audit-only
  and legacy/proxy numeric operands occur only in typed before-context
  blocks. Before schema-validating or using the configured DAG beyond strict
  JSON syntax, the coordinator reconstructs every root's exact source
  identity/type/unit, record and output-enum domains, unavailable-reason
  closure, operation/legal-rule
  bindings, unit-algebra rows, opcode chain, and output schema from the frozen
  registries; configured sources/nodes/roots are comparands only. Registration
  rejects p25→p10, wage↔SE, altered source type/unit, unknown domain/rule ID,
  cross-domain enum choose (including equal-literal domains), and
  missing/extra/reordered/conflicting unit-algebra attacks. The exact
  `consumer_result_proposal.v1` wire envelope classifies every wholly unknown
  coordinate as extra and every malformed envelope as schema-invalid, then
  rejects missing, duplicate, or unequal recognized rows; every certified
  worker denominator uses analytic probabilities.
- [ ] `gate_specs.v3` contains exactly conjunctive G01–G22, including G10's
  six exact replay rows, G11's one row per frozen provider plus the complete
  lifecycle seal and boundary-attested expected/actual principal event
  streams on selected and no-eligible branches, G14's exact four trusted
  survey-weight rescale rows, G15's exact nonempty broker/sandbox assertions,
  and G17's exact 15-domain inventory/fact-binding/microfact closure; G22
  additionally requires zero source/domain/rule/unit/root semantic mismatches
  and zero proposal schema/value mismatches.
- [ ] Expected mappings, 20-draw namespace, nonlinear benefit propagation,
  frozen ledger-row schema, within-year dependence groups, byte replay,
  row-order invariance, exact-once process-lifecycle keyed-uniform caching,
  the exact bootstrap-to-exit phase registry, complete bootstrap identity
  records, one contiguous creation/destruction/seal sequence namespace,
  exact cutoff-specific incident-cleanup maps, complete boundary-bearing
  expected/actual principal event streams, complete nonce/forbidden-provider
  traces, post-seal deny-all enforcement, and immediate pre-rename RNG
  rechecks are executable on both terminal branches.
- [ ] Aggregate motivation states both high per-worker ratios and
  approximately 1.01→0.80 aggregate payroll, with no unconditional sign.
- [ ] Scope exclusions and the revenue-only degradation are exact and cannot
  retire report-wide proxy labels.
- [ ] The label certificate enumerates full conditions plus exact retired,
  replaced, new, and preserved mismatch literals.
- [ ] Configuration, correction-model identity, primary tagged unions,
  result rows, incident objects, target-exposure phases, and output paths
  exact-match §10's schemas and validators.
- [ ] Strict parsing rejects BOMs, duplicate keys, nonfinite/overflowed or
  lossy numbers, bad types, and noncanonical bytes before any field is used.
- [ ] Repository ancestry/blob/tree identity, initial-clean or retry-exact
  active-ceremony checkout state, the closed eight-token byte-exact
  `sys.orig_argv`, and the concrete absolute fresh-empty sentinel pass before
  the exclusive durable claim and any production access.
- [ ] The only retry authority is the same-process opaque one-shot receipt;
  the sole coordinator nonce call is metered, a retry publishes its durable
  claim first and reuses cached midpoint values without duplicate provider
  calls; the original wrappers/ledger/cache persist until their single
  irreversible seal/deny transition and cannot be reset; killed/lost/failed
  attempts use append-only fresh-registration adjudication and fresh claim
  namespaces.
- [ ] Consumer/gap domains, projection/correction reductions, corrected-only
  dependency proofs, and deterministic ledger-rematerialization hashes are
  complete and independently recomputed.
- [ ] §10.5 is the sole normative execution law and enforces durable claims,
  publishes-regardless, terminal results, append-only incidents, at most one
  receipt-authorized retry, and viable fresh registration afterward.
- [ ] The context event independently reconstructs every corrected metric,
  the separate metric-spec and expanded metric-result domains, all 14
  pairings, all nine comparison specs, both mismatch-array transformations,
  the context-row domain, and all analytic denominators under the same
  complete ceremony kernel, without calling already-viewed evidence unseen.
- [ ] W1 pins the substantive cell-scoped identity, separate evaluation
  provenance, independent domain/dependency/gap specs, and corrected stream
  identities before bridging.
- [ ] `Deviations` is accurate.

### 14.3 Staged ratification protocol

The authorized order is:

1. merge this referee-ratified design, with no authority artifact,
   implementation, or production result smuggled into the design commit;
2. merge a separate referee-gated authority/extraction PR containing the
   legal and verification-claim registries with structured direct-law
   covered/excluded fact bindings, derived microfact/presence-predicate
   authorities, independent PSID source-field
   inventory, questionnaire-slot/structural-missing/value-code/
   annualization/reconciliation/job-match/SE-aggregation/coverage-group
   registries, component-slot crosswalk, retained source captures, literal manifests,
   vintage-2 target artifact, physical-cell/alias registries, and the literal
   `ledger_row_schema_specs`, `coverage_state_dependence_specs`,
   `calibration_target_specs.v2`, candidate/era/selection/draw specs,
   replay, consumer-domain, claim-gap, dependency (including exact
   `consumer_source_field_schema_specs.v1` and
   `consumer_literal_domain_specs.v1`,
   `consumer_evaluator_condition_reason_specs.v1`, and
   `consumer_semantic_recipe_specs.v1` subregistries), legal-rounding, trusted
   typed consumer-evaluation comparand, RNG-access,
   weight-rescale, filesystem-isolation, held-out-noninterference,
   `gate_specs.v3`, evaluation, and sensitivity authorities, plus builders
   and offline reproduction/rejection tests, including wrong-purpose,
   uninventoried, runner-boolean, missing-ledger-row, and altered-action-fold
   microfact cases; free-text or uninventoried fact bindings; empty binding
   slot arrays; missing, extra, or reordered derived required facts;
   premise/slot mismatches; nonempty-fact constant-enum transforms; p25→p10
   and wage↔SE root poisoning; distinct-ID `same_key_choose` branches,
   including byte-identical literal arrays; changed source field/type/unit,
   domain, reason map, rule, or unit-algebra rows; and malformed-envelope,
   wholly unknown, missing, extra, or reordered
   `consumer_result_proposal.v1` rows with exact mismatch classification;
   omitted or selected-only
   `rng_access_results`; truncated no-eligible nonce/forbidden-provider
   evidence; missing/extra/reordered lifecycle phase literals; malformed or
   replaced bootstrap identity records; duplicate, gapped, reset, or
   cross-namespace creation/destruction/seal sequences; a reversed same-phase
   destruction order, wrong same-phase creation boundary, or incident cleanup
   boundary selected from another cutoff;
   wrapper/ledger/cache replacement; post-seal entropy requests during
   primary or sidecar construction; and ledger/cache/wrapper mutation
   immediately before either branch's first rename;
3. merge a separate referee-gated implementation PR whose rehearsals are
   fixture-only and structurally reject production paths;
4. obtain a fresh registered §10.1 configuration binding every preceding
   commit, artifact byte, registry, concrete invocation/sentinel, complete
   attempt history, fresh-registration adjudication, and output/claim
   namespace;
5. record all six §10.4 checks, durably claim the initial attempt, and launch
   the sealed §10.5 ceremony; only its private one-shot receipt may authorize
   the sole unchanged retry;
6. publish the complete report pair or incident unchanged in a
   publishes-regardless PR; only a validator-passing `pass` pair may become
   the correction input to §12;
7. after that pass PR merges, separately ratify and freshly register the
   §12 context-report configuration under the same strict parser,
   repository/argv/sentinel, durable-claim, opaque-retry, and
   fresh-registration kernel, then execute and publish its complete report or
   incident regardless; and
8. only merge of the validator-passing context-report PR activates the
   conditional certificate, retires the proxy label, and resolves forecast-
   ledger entry 11.

Changing any registered byte, registry member/order, source, target value or
role, candidate, tolerance, seed/draw law, implementation commit, invocation,
attempt history, or output path invalidates the evaluation registration. It
cannot be “noted” after launch; it requires the §10.3
fresh-registration/output-version disposition. However, changing only a
held-out, zero-weight, or vintage-1-exclusive byte changes full evaluation
provenance, registration, and G21's evidence SHA-256 because its evidence
object embeds both full-provenance hashes. It does not change
`fit_selection_cell_identity.v1`, `substantive_model_sha256`, a uniform, any
non-G21 gate row/evidence hash, G21's status, or correction eligibility. G21
enforces that noninterference.

Until every box is ratified and the later publication sequence completes,
the `first_estimates_report.md` §3.4 labor-income proxy label remains in
force.

## 15. AMENDMENT SECTION — Amendment 1: remove the unavailable covered-share target

### 15.1 Status, scope, and precedence

- **Status:** **PROSPECTIVE AMENDMENT — UNRATIFIED.** This section proposes
  revision 3 of the design. It authorizes no extraction, implementation,
  registration, fitting, evaluation, report run, or label change.
- **Base authority:** The immutable base is the complete revision-2 text at
  commit `59fd058b943c2b9960af9cb98ecdec97709cc2dd`, ratified after eleven
  adversarial referee rounds.
- **Change:** Amendment 1 removes
  `ssa_precisely_universed_covered_share` from the required calibration,
  fitting, validation, selection, and tolerance contract; makes literal SSA
  covered-share cells an empty optional-source block; reassigns the removed
  weight exactly pro rata across the four surviving positive-weight
  families; and re-points every affected base-law reference.
- **No implied repeal:** Original §§1–14 remain visible and are not edited in
  place. They remain controlling except for the exact clauses enumerated in
  §§15.3–15.6. Where an enumerated original clause conflicts with §15, §15 is
  its prospective replacement law. Silence in §15 leaves the original clause
  unchanged.

This section follows the first-estimates amendment discipline: identify the
ratified base, state the defect and why it requires design action, freeze the
replacement before implementation or output contact, carry the limitation
forward, and require a new referee-gated ratification and registration. The
append-only presentation here is stricter: the displaced law remains
readable, with this pointer, rather than being rewritten in place.

### 15.2 Established source absence and reason for amendment

The base §6.1/§6.2 contract requires one literal `as_published` SSA
covered-worker-incidence share observation per registered year, with an
unthinned era span reaching 1968–2014 and an exact numerator, denominator,
timing, unit, duplicate-worker rule, zero rule, universe, and frame-relative
model analogue. The captured and adversarially inspected SSA publication
corpus contains no series satisfying that contract:

- Supplement Table 4.B1's published percentage is a share of **earnings
  dollars**, not the incidence of workers with covered earnings.
- Supplement 4.C concerns insured status, a different estimand and
  denominator from annual covered-worker incidence.
- Trustees Table IV.B4 publishes worker counts and per-beneficiary ratios,
  not literal covered-worker-share cells.
- Dividing Table 4.B1 workers by IV.B4 workers would synthesize one value
  from two publications. It is also empirically incoherent as a subset
  share: the displayed quotient exceeds 1 in 31 of 55 years, is below 1 in
  24, and equals 1 in none. For 1978 it is exactly
  \(110{,}600/109{,}432=13{,}825/13{,}679>1\). The value check corroborates
  the independently decisive universe and artifact-shape failures; it is not
  the basis for changing weights.
- Table 4.B10 OASDI workers divided by Table 4.B12 HI workers is likewise a
  synthesized quotient, is available in the adjudicated candidate only for
  preliminary 2023, lies outside every registered fit/validation era, and
  has no registered HI-denominator model analogue. Table 4.B11
  \(T/(W+S)\), VI.G1 payroll/GDP quantities, maximum-earner shares, entrant
  shares, and IV.B4 worker/beneficiary ratios also answer different
  questions.

The one-observation law is independent and controlling: separately published
operands, even if their quotient happened to lie in \([0,1]\), are not one
published covered-share observation. No cross-publication quotient,
interpolation, clipping, reconciliation, B1 earnings percentage, insured-
status percentage, or approximate “94 percent” may fill the missing cells.
Definitional prose cannot cure either the artifact-shape failure or the
estimand failure.

The defect was established during authority extraction, before any fitting
and before any model target value, prediction, parameter, loss, ranking,
selection, gate result, or other model output existed. Some official source
values had necessarily been viewed to adjudicate their identities and
universes; they are not called unseen. The amendment responds to the
pre-output absence of a lawful source, not to whether a fitted model agreed
with an observed target. The minimal honest response is therefore removal of
the family from the required calibration contract, not replacement by
synthesis.

### 15.3 Exact §6.1 replacement — vintage-2 source artifact

This subsection replaces the base §6.1 artifact-shape law at base-ratification
lines 1826–1907, the covered-share-required-source paragraphs at lines
2026–2032, and only the covered-share portion of the prerequisite consequence
at lines 2013–2015. Because no authoritative vintage-2 artifact has ever been
minted, the append-only path and vintage ID remain
`data/external/ssa_covered_earnings_calibration_targets_vintage2.json` and
`ssa_covered_earnings_calibration_targets.vintage2`. The changed key meanings
require the new schema literal
`ssa_covered_earnings_calibration_targets.v2`.

The artifact has exactly these eleven top-level keys, in semantic order:

1. `schema_version`;
2. `artifact_vintage_id`;
3. `artifact_role`;
4. `year_basis`;
5. `required_calendar_years`;
6. `required_source_cell_ids`;
7. `optional_covered_share`;
8. `source_document_manifest`;
9. `observations`;
10. `cross_table_discrepancies`; and
11. `integrity`.

The unchanged literals and laws for `artifact_role`, `year_basis`,
`required_calendar_years`, `cross_table_discrepancies`, canonicalization, and
integrity continue to apply. `required_source_cell_ids` has exactly the two
underscore-form object keys `table4_b2` and `table4_b11`, with the exact
year-major arrays already frozen in base §6.1. It has no
`ssa_covered_share` key. At the manifest layer, the required table-ID domain
is exactly the dotted array `["table4.b2","table4.b11"]`.
`source_document_manifest` has exactly the one required Supplement object,
whose `table_ids` equals that array; no optional covered-share document may
appear in the required manifest.

Top-level `observations` contains exactly \(6\times55=330\) Table 4.B2 cells
and \(9\times55=495\) Table 4.B11 cells, for 825 cells total, in the original
order and with the original status, literal-token, unit, normalization,
rounding-tag, source-resolution, and uniqueness laws. Its IDs exact-match
only the two required arrays. An optional source cell may not leak into the
top-level observations, required ID arrays, required manifest, physical-cell
expansion, or discrepancy registry.

`optional_covered_share` has exactly these eight keys:

1. `status`;
2. `failure_reason`;
3. `covered_share_required_years`;
4. `ssa_covered_share`;
5. `source_document_manifest`;
6. `observations`;
7. `source_activation_condition_id`; and
8. `target_reactivation_condition_id`.

For vintage 2, its exact immutable value is:

```json
{
  "status": "unavailable_source_absent",
  "failure_reason": "no_qualifying_literal_as_published_ssa_worker_share_series_in_registered_sources",
  "covered_share_required_years": [],
  "ssa_covered_share": [],
  "source_document_manifest": [],
  "observations": [],
  "source_activation_condition_id": "literal_as_published_ssa_covered_worker_share_cells_v1",
  "target_reactivation_condition_id": "future_ratified_amendment_and_fresh_registration_required_v1"
}
```

This is an explicit empty-with-failure state, not successful empty
covered-share authority. It is valid for the amended required B2/B11 artifact
and does not abort that artifact merely because the optional source is
absent. The artifact's zeroed-field content hash and canonical-byte
reproduction bind the complete optional object, including its status and
reason. The empty block creates zero physical-source, alias, arithmetic,
target, result, provenance, or trace rows.

`literal_as_published_ssa_covered_worker_share_cells_v1` is satisfied only
by committed, hash-pinned primary SSA bytes containing **literal published
worker-incidence share cells—not separately published operands**. The series
must meet all of the following before a successor artifact may use the
alternate `source_verified_not_target_bound` status:

1. exactly one literal `as_published` covered-worker-share observation for
   each included calendar year, from one source-defined numerator/denominator
   universe; no quotient or other synthesized cell;
2. an unthinned inclusion of every available cell from the qualifying series
   over 1968–2014, including at least one cell in each of 1968–1974,
   1975–1977, 1978–1992, 1993–2001, and 2002–2008, and every available
   2009–2014 cell;
3. source bytes establishing the exact numerator and denominator sets,
   numerator-subset relation, OASDI scope, geography, annual timing, worker
   unit, duplicate-worker rule, same-type and dual-type treatment, zero rule,
   edition, cell status, literal token, and source identity; and
4. exact compliance with the manifest, observation, status, ordering,
   source-resolution, canonicalization, integrity, and append-only laws.

In that alternate source-only state, `failure_reason` is JSON null; the four
arrays are nonempty, ordered, mutually consistent, and one-to-one by year;
and the optional manifest and observations use the same exact nested schemas
as their required counterparts. A partial, ambiguous, synthesized,
cross-publication, thinned, wrong-universe, or otherwise nonconforming
attempt aborts optional-source activation and cannot fall back within the
same build to an asserted available state.

Source availability alone never reinstates a fitting target. A source-
verified block remains `not_target_bound`. Reactivating a covered-share
calibration family requires the separately exact
`future_ratified_amendment_and_fresh_registration_required_v1` condition: a
new prospective design amendment must freeze the model denominator and
universe concordance, target rows, dependency audit, weights, tolerances,
identities, and versioned registries; pass the full referee ceremony; mint a
new append-only artifact vintage; and receive a fresh registration before
any fitting or selection. There is no automatic weight reversal.

All base §6.1 B2/B11 methodology-byte prerequisites remain controlling.
Until primary methodology bytes settle every applicable zero, loss-only,
below-threshold, wage-capped, multiple-job, dual-type, and
multiple-component membership case, the corresponding B2 intensity or B11
worker-distribution family—and therefore the required amended calibration
contract—fails closed. Removing the optional share family does not supply an
alternative denominator or waive one prerequisite.

### 15.4 Exact §3.1 replacement — fields retained, target binding removed

The two base §3.1 rows at base-ratification lines 237–238 remain in the
frozen person-year output registry, with these exact replacement
definitions:

| Estimand ID | Amendment-1 definition |
|---|---|
| `registered_covered_share_denominator_indicator` | Deterministic zero/one membership in the frozen **model-only** annual population universe used for covered-worker-incidence gates and diagnostics. It resolves through the registered age, annual-presence, employee/SE/both-type, unique-worker, duplicate-worker, zero-earner, and denominator rules, but makes no concordance claim to an absent official share source. It is not an official-target universe, target denominator, earnings outcome, or coverage outcome. |
| `modeled_covered_worker_probability_analytic` | Analytic probability, under the registered joint wage/SE status mapping, that person taxable payroll is positive. It is the analytic selector for gates, evaluation diagnostics, and context comparisons; it is not target-bound and is not `proxy > 0`. |

The exact finite-joint-state law following the base table remains unchanged.
So do `modeled_covered_worker_draw_indicator` and
`modeled_covered_worker_draw_grid_fraction_20`, including their
diagnostic-only status.

The retained model-only annual diagnostic is
`model_covered_worker_incidence_diagnostic`. Within correction draw \(d\) and
verified calendar year \(y\), it is exactly

\[
\frac{\sum_i w_i\,
  \texttt{modeled_covered_worker_probability_analytic}_{i,y,d}}
{\sum_i w_i\,
  \texttt{registered_covered_share_denominator_indicator}_{i,y}},
\]

where both sums use the same registered model universe and weight field and
the denominator must be strictly positive. It has no official observation,
source cell, target row, loss, tolerance, evidentiary role, selection
eligibility, or candidate-rescue effect. It publishes in §8.2's `incidence`
diagnostic family. G01 independently reconstructs its complete annual
person-year domain, G20 applies only if its registered reduction mode is
`projection_cross_correction_draw`, and G22 verifies its selector,
denominator, weight, same-key ratio, and corrected-root dependency. Thus the
denominator indicator has an exact diagnostic consumer rather than a
dangling definition.

The existing retained uses of
`modeled_covered_worker_probability_analytic` remain controlling: every
certified modeled-worker denominator in the hard-gate law
(base-ratification lines 4140–4141), every modeled-incidence or denominator
metric in §8.2 (lines 5090–5095), and the context
`analytic_worker_selector` (lines 7421–7423) uses that analytic field, never
a draw indicator or 20-draw fraction. None of those uses confers target
status.

Base §5.2's zero-preserving measurement law also remains. Its sentence at
line 1485 is replaced by: **the optional covered-share diagnostic may be
unavailable, but its absence or value cannot produce
`no_eligible_candidate`; candidate eligibility is determined only by the
surviving required families and all unchanged candidate, B2/B11
methodology, domain, convergence, rank, and tolerance laws.**

### 15.5 Exact §6.2/§7 replacement — families, dependencies, and weights

The changed family domain, order, dependency assignments, and weight law
create `calibration_target_specs.v3`, `fit_selection_cell_identity.v2`, and
`selection_spec.v2`. Their predecessors remain historical. Except for the
changes stated here, the target object's exact 30-field shape, source/year/
role/ancestry checks, transformation and selector schemas, tolerance tags,
universe law, expansion law, and cell-scoped isolation law remain as ratified.

`calibration_target_specs.v3` expands exactly the following 14 families in
this order, then ascending verified calendar year. It creates no
`ssa_precisely_universed_covered_share` object or placeholder. An empty or
source-verified `optional_covered_share` block creates zero target objects
unless a later ratified amendment expressly reactivates a family.

| Target family | `dependency_group` | Exact official transformation and model selector | Loss | Raw family mass | Normalized effective weight | Role and selection law |
|---|---|---|---|---:|---:|---|
| `b2_wage_total_intensity` | `b2_component_system` | 4.B2 `c5/c11`; model `sum(covered_employee_wages_uncapped) / sum(b2_wage_worker_membership_probability_analytic)` | `squared_log_ratio` | 2 | \(1/3\) | Role is recomputed by verified year; positive-weight direct train cells fit; available direct/boundary validation cells select; gaps are zero-weight unavailable diagnostics; 2015–2022 is held out. |
| `b2_se_total_intensity` | `b2_component_system` | 4.B2 `c8/c12`; model `sum(covered_se_net_earnings_pre_seca) / sum(b2_se_worker_membership_probability_analytic)`, where the numerator is the expected signed within-`se_aggregation_group_id` net concept before SECA factor, threshold, or cap | `squared_log_ratio` | 2 | \(1/3\) | Same exact role and selection law as the preceding family. |
| `b11_se_only_worker_share` | `b11_worker_type_system` | 4.B11 `(T-W)/T`; model `sum(b11_se_only_worker_probability_analytic) / sum(b11_any_worker_probability_analytic)` | `squared_logit_error` | 1 | \(1/6\) | Same exact role and selection law. |
| `b11_dual_type_worker_share` | `b11_worker_type_system` | 4.B11 `(W+S-T)/T`; model `sum(b11_dual_type_worker_probability_analytic) / sum(b11_any_worker_probability_analytic)` | `squared_logit_error` | 1 | \(1/6\) | Same exact role and selection law. |
| `b11_wage_only_worker_share` | `b11_worker_type_system` | 4.B11 `(T-S)/T`; model `sum(b11_wage_only_worker_probability_analytic) / sum(b11_any_worker_probability_analytic)` | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight and selection-ineligible because algebraically dependent. |
| `b2_type_count_mix` | `b2_component_system` | 4.B2 `c12/(c11+c12)` and the analogous model marginal-count ratio | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight and selection-ineligible; overlapping marginal counts are never unique workers. |
| `b2_se_total_component_share` | `b2_component_system` | 4.B2 `c8/(c5+c8)` and the algebraically identical model component ratio | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight dependency check only. |
| `b2_wage_taxable_intensity` | `b2_component_system` | 4.B2 `c13/c11`; model consolidated taxable wage intensity | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight preserved employer-cap mismatch. |
| `b2_se_taxable_intensity` | `b2_component_system` | 4.B2 `c17/c12`; model consolidated taxable SE intensity | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight. |
| `b2_wage_taxable_fraction` | `b2_component_system` | 4.B2 `c13/c5`; model taxable/uncapped wage ratio | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight preserved employer-cap mismatch. |
| `b2_se_taxable_fraction` | `b2_component_system` | 4.B2 `c17/c8`; model taxable/uncapped SE ratio | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight. |
| `b11_taxable_earnings_component_reconciliation` | `b11_taxable_earnings_component_system` | Literal displayed 4.B11 taxable-earnings total minus displayed wage and SE taxable components under `structural_dependence_only`; model `sum(oasdi_person_taxable_payroll) - sum(oasdi_taxable_wages_person) - sum(oasdi_taxable_se_person)` | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight structural-formula-sibling diagnostic, never independent evidence; literal residual retained with `rounding_interval_unavailable`. |
| `b11_contributions_component_reconciliation` | `b11_contribution_component_system` | Literal displayed 4.B11 contribution total minus displayed wage and SE components under `structural_dependence_only`; model `sum(oasdi_taxable_wages_person * registered_wage_oasdi_combined_rate + oasdi_taxable_se_person * registered_se_oasdi_rate) - sum(oasdi_taxable_wages_person * registered_wage_oasdi_combined_rate) - sum(oasdi_taxable_se_person * registered_se_oasdi_rate)` | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight structural-formula-sibling diagnostic, never independent evidence; worker total is never summed because component worker counts overlap. |
| `b11_se_contribution_share` | `b11_contribution_component_system` | 4.B11 SE OASDI contributions/(wage+SE OASDI contributions); model `sum(oasdi_taxable_se_person * registered_se_oasdi_rate) / sum(oasdi_taxable_wages_person * registered_wage_oasdi_combined_rate + oasdi_taxable_se_person * registered_se_oasdi_rate)` | `no_fitting_loss` | 0 | 0 | Recomputed year role; zero-weight legal/accounting sibling diagnostic only. |

The four selection-eligible families and only those families have positive
mass. The active dependency-group masses and normalized weights are exactly:

| `dependency_group` | Raw group mass | Normalized group weight | Positive-weight family subweights |
|---|---:|---:|---|
| `b2_component_system` | 4 | \(4/6=2/3\) | \(1/2,1/2\) |
| `b11_worker_type_system` | 2 | \(2/6=1/3\) | \(1/2,1/2\) |

`b11_taxable_earnings_component_system` and
`b11_contribution_component_system` are exact zero-weight diagnostic groups.
The IDs `covered_share_system_disjoint_source` and
`covered_share_system_shared_source` are absent from every amendment-1
registry.

The reassignment is exact and pro rata. Before amendment, the surviving
families had weights \(1/4,1/4,1/8,1/8\), totaling \(3/4\). Normalizing their
unchanged ratio by \(4/3\) gives

\[
(1/4)(4/3)=1/3,\quad
(1/4)(4/3)=1/3,\quad
(1/8)(4/3)=1/6,\quad
(1/8)(4/3)=1/6.
\]

The respective increments are \(1/12,1/12,1/24,1/24\), and

\[
1/12+1/12+1/24+1/24=1/4,\qquad
1/3+1/3+1/6+1/6=1.
\]

No rounded decimal represents either \(1/3\) or \(1/6\). Accordingly, the
finite-JSON-number `loss_weight` field uses exact relative integer mass:
`2` for an available model-choice cell in either B2 intensity family, `1`
for such a cell in either B11 worker-share family, and `0` otherwise;
booleans are forbidden. “Model-choice cell” here means a positive-weight
direct train cell or a selection-eligible direct/boundary validation cell in
the applicable phase. All four families must have the same registered
positive cell count within a phase; a mismatch or thinned family aborts.
The phase objective is the weighted mean over its admitted cells, so
normalization by the total mass yields the exact effective weights above.
Equivalently, if \(L_F\) is each family's equal-cell arithmetic mean, both
training and validation use exactly

\[
\frac{
  2L_{\mathrm{b2,wage}}+
  2L_{\mathrm{b2,SE}}+
  L_{\mathrm{b11,SE-only}}+
  L_{\mathrm{b11,dual}}
}{6}.
\]

This integer-mass representation is normative in
`calibration_target_specs.v3`, `fit_selection_cell_identity.v2`, and
`selection_spec.v2`; a decimal approximation is a schema violation.

All other base tolerance and role laws remain. Intensity validation requires
RMS absolute log error no greater than
`0.04879016416943205` and every-cell absolute log error no greater than
`0.09531017980432493`. B11 worker-type validation requires RMS absolute
share error no greater than `0.015` and every-cell absolute share error no
greater than `0.03`. There is no covered-share tolerance. Every zero-weight
family remains incapable of fitting, selecting, failing, or rescuing a
candidate, and its original arithmetic/dependency disclosure remains in
force.
