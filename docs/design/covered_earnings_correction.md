# The covered-earnings correction: a common component ledger for benefits and revenue

- **Status:** DRAFT revision 1 for adversarial ratification. This document
  authorizes no extraction, implementation, registration, fitting, evaluation,
  report run, or label change.
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
| `source_provenance` | Source wave, role, job/component, `se_aggregation_group_id`, verified reference year, exact `year_source_class`, raw field IDs, unit, missing-code disposition, admissible-information date, and—on a benefit gap view—operative claim year plus adjacent base-row hashes. |
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
hashes, and is never reusable across claim contexts. A career-only
correction, revenue-only correction, omitted opening-backfill/difficult row,
self-shrunk support set, or independently sampled pair fails G01/G08/G22.

## 4. Immutable authorities, PSID crosswalk, and information boundary

### 4.1 Historical legal-rule authority

Before any fitting, a new immutable `historical_coverage_rule_specs.v1`
registry and source manifest must be ratified. Each ordered rule object
contains exactly:

`rule_id`, `status_family`, `effective_start`, `effective_end`,
`jurisdiction`, `authority_rank`, `source_document_id`, `source_sha256`,
`exact_citation`, `covered_facts`, `excluded_facts`, `required_micro_facts`,
`transform`, `reason_code`, and `unresolved_action`.

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
  effective-year gap, conflicting same-rank rules, or an unregistered
  transform aborts the whole registration. The complete Section 218 and
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

The treatment of named risk classes is frozen:

| Risk class | V1 disposition |
|---|---|
| State/local | Government level alone never proves coverage or noncoverage. Direct classification requires the registered Section 218 group/position and public-retirement-system facts. Otherwise use the registered expected mapping or `unresolved`. |
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
inventory domain. It expands every staged family wave
`1968..1997,1999,2001,...,2023`, both questionnaire roles
`head_or_reference_person` and `spouse_or_partner`, every
questionnaire-defined job slot plus the role-total, farm, and business
aggregate slots, and each of these ordered field purposes:

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
  "job_identifier"
]
```

The slot registry is derived from and cites the complete questionnaire/layout
domain, not from fields already used by `family.py`. A source inventory that
contains only the current role totals is therefore incomplete by construction.
For every slot-purpose key, the inventory has exactly one row with:

`interview_wave`, `earnings_reference_year`, `role`, `job_slot`,
`slot_kind`, `field_purpose`, `disposition`, `raw_field_ids`,
`exact_label_texts`, `full_source_descriptions`, `value_code_map`,
`reporting_unit`, `source_file_ids`, `source_byte_sha256s`,
`layout_coordinates`, and `absence_proof`.

`earnings_reference_year` is always the JSON integer
`interview_wave - 1`. `disposition` is exactly `present` or
`structural_missing`. A present row has nonempty field IDs, complete labels
and descriptions, an exact raw-code-to-meaning map where the field is coded,
and null `absence_proof`. A structural-missing row has empty field IDs and a
nonempty absence proof that binds the complete searched label/layout domain
and search implementation. “Not used by the existing reader,” a short label,
or the crosswalk's declaration is not an absence proof. Duplicate or missing
slot-purpose keys, an unscanned layout column, a raw code without a
disposition, source drift, or a wave/reference-year mismatch aborts inventory
ratification.

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
production earnings source. Every crosswalk, support row, candidate basis,
target selector, Option-C row, evaluation stratum, and result row carries the
literal `year_source_class`; it may never be inferred from row availability.

The reference-year seams, not interview-year aliases, are:

| Reference years | Frozen source-concept adjudication |
|---|---|
| 1968–1974 | Preserve role totals. Unsupported job/context slots are explicit inventory absences. |
| 1975–1977 | These are interview waves 1976–1978. The spouse-source concept is determined from the pinned full descriptions and value structure under V-B6. The short labels do not establish `wages_only`; where employee wages and unincorporated-business labor cannot be separated, `remuneration_type` is `mixed` or the row is unresolved under its predeclared rule. |
| 1978–1992 | Pre-ER edited totals include the applicable farm/business labor parts. Separate fields split or validate the total and are never added twice. |
| 1993–2001 | The farm/business concept seam is reference year 1992/1993: wave 1994 describes 1993. ER role totals and separately carried farm/business labor components combine exactly once. Direct years and biennial structural gaps retain distinct source classes. |
| 2002–2012 | Modern job blocks begin with interview wave 2003 and therefore describe reference year 2002, then 2004, …, 2012. Job amounts, units, and timing reconcile to the appropriate prior-year role total; odd reference years remain structural gaps. |
| 2013 | Claim-specific benefit gap only; no unconditional person-level source row exists. |
| 2014 | Frozen boundary row only. |
| 2015–2022 | Projected path only. |

The implementation must then publish a separate immutable, fully expanded
`psid_covered_earnings_crosswalk.v1`. Each source-backed object contains
exactly:

`source_inventory_key`, `interview_wave`, `earnings_reference_year`,
`year_source_class`, `role`, `job_slot`, `source_component_id`,
`remuneration_type`, `raw_field_ids`, `value_code_map_id`,
`reporting_unit`, `periodicity`, `month_presence_fields`,
`assignment_fields`, `self_other_field`, `incorporation_field`,
`government_level_field`, `industry_field`, `occupation_field`,
`enrollment_field`, `missing_codes`, `source_disposition`,
`admissible_information_date`, `annualization_rule_id`,
`reconciliation_rule_id`, `job_spell_match_rule_id`,
`se_aggregation_group_id`, `coverage_state_group_rule_id`,
`era_seam_reason_codes`, `direct_classification_rule_ids`, and
`coverage_unknown_action`.

`remuneration_type` is exactly
`employee | self_employment | mixed | nonremuneration`; `mixed` is a
first-class source concept, not an implementation guess. `source_disposition`
exactly equals the inventory's `present | structural_missing` value.
Every raw field and value-code map exact-matches the independently pinned
inventory row. The crosswalk contains one row for every inventory key and no
other key. It may map a structural absence only to a predeclared
`modelable | unresolved` consequence; it may not invent a field or call an
absence zero.

Five separately frozen executable registries close every referenced rule:

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
- `psid_coverage_state_group_rule_specs.v1` declares which same-service
  components co-move and which must remain separate.

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

G17 exact-compares the inventory key stream, crosswalk key stream, value-code
maps, all five rule-ID closures, and the frozen wave/reference/source-class
map. Missing support fails the gate; it never shrinks a domain.

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
benefit cutoff and inherits `structural_gap_imputed`, never
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

Direct statutory classification occurs only when §4.1's applicable
`registration_required` authority is complete and every
`direct_only_optional` fact required by that row is present. Every other
in-domain homogeneous record receives exactly one of:

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

`coverage_unknown_action` is exactly `modelable` or `unresolved`. For a
modelable wage component with candidate coverage probability \(q\), the
status vector is exactly `[q,0,1-q,0]`; for modelable SE it is
`[0,q,1-q,0]`. For an unresolved wage component it is `[0,0,0,1]` with a
wage type reason code; for unresolved SE it is the same vector with an SE
type reason code. Direct legal classification remains a one-hot vector.
There is no fitted unresolved share and no third complement-allocation
branch in v1. Changing `modelable` to `unresolved` or vice versa changes the
crosswalk artifact and requires fresh registration.

The crosswalk—not the runtime—freezes which branch applies to every inventory
key. Registration exact-compares each optional verification failure with its
enumerated affected-key set. No missing optional source can widen a modelable
domain, and no candidate may convert an unresolved row to improve a target or
gate.

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
| `ry2002_2014_modern_boundary` | 2002–2014 | Direct even 2002–2012 rows estimate parameters; odd gaps 2003–2013 are derived and selection-ineligible; 2014 is a separately labeled boundary validation row. |

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
absolute difference must be at most 0.005. For a signed corrected-minus-
baseline currency or count, stability is applied to the two nonnegative
corrected level means using the same 0.01 symmetric rule; the fixed baseline
is then subtracted only for reporting the delta. `draw_spec.v1` assigns every
registered metric to exactly one of these three unit families; an unassigned or
multiply assigned metric fails. This is a deterministic resolution check,
not a confidence interval. Failure blocks correction-model eligibility; it
cannot trigger draw shopping.

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

Every pair must byte-match the full fit/selection bundle, substantive model
hash, expected-ledger identity, and all 400 realized-ledger identities.
Exactly six result rows are required; an empty, partial, duplicated, or
reordered registry fails G10. G14 separately performs a trusted second
fit/selection execution after multiplying every model weight by the exact
binary64 value `7.0`; all parameter bits, predictions, losses, candidate
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

Two source-identity registries are frozen before target specs.
`physical_source_cell_specs.v1` assigns each cell in the vintage-1 and
vintage-2 official artifacts exactly one physical identity containing:

`physical_cell_id`, `publication_family_id`, `edition_id`,
`source_document_id`, `table_id`, `row_path`,
`nested_column_header_path`, `calendar_year`, `as_published_token_sha256`,
`normalized_semantic_sha256`, and `full_source_sha256`.

The physical ID is the publication/edition/table/row/header/year/cell-token
identity, not a logical series or target ID. `full_source_sha256` proves the
production extraction but is evaluation provenance; it is excluded from the
cell-scoped substantive projection below.

`official_source_alias_specs.v1` is the complete frozen registry of
cross-vintage physical aliases, republications, shared primitives, and
arithmetic siblings. Each ordered row has exactly
`alias_group_id`, `left_physical_cell_id`, `right_physical_cell_id`,
`relation`, `effective_calendar_year`, `arithmetic_rule_id`, and
`adjudication`. `relation` is
`same_physical_cell | cross_vintage_republication | shared_primitive |
arithmetic_sibling`; `arithmetic_rule_id` is nonnull exactly for the last
relation. Registered arithmetic rules include the taxable-earnings/gross-
contribution rate relationship and every extracted total/component or
ratio/share sibling. The registry is built from both artifacts and all
extracted formula registries, never from declared target roles. An omitted
known relation, a cycle with inconsistent physical identity, or a
cross-vintage relation without exact source proof aborts registration.

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

`declared_role` must equal it byte-for-byte. The validator then takes the
transitive closure through `official_source_alias_specs.v1`. Every physical
alias, shared primitive, and arithmetic sibling receives the same honest
exposure classification for that year, even when its own target has
`no_fitting_loss` and zero weight. A model-choice closure containing a
post-2014 physical cell, a different-year operand, or a vintage-1 held-out
alias aborts registration. An arithmetic sibling may publish a zero-weight
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
| `b11_taxable_earnings_component_reconciliation` | 4.B11 taxable-earnings total minus wage and SE taxable components; model `sum(oasdi_person_taxable_payroll) - sum(oasdi_taxable_wages_person) - sum(oasdi_taxable_se_person)`; report interval consistency only when its rounding tag is `source_verified` | no fitting loss | Recomputed year role; zero-weight arithmetic-sibling diagnostic, never independent evidence. |
| `b11_contributions_component_reconciliation` | 4.B11 contribution total minus wage and SE contribution components; model `sum(oasdi_taxable_wages_person * registered_wage_oasdi_combined_rate + oasdi_taxable_se_person * registered_se_oasdi_rate) - sum(oasdi_taxable_wages_person * registered_wage_oasdi_combined_rate) - sum(oasdi_taxable_se_person * registered_se_oasdi_rate)`; worker total is never summed because component worker counts overlap | no fitting loss | Recomputed year role; zero-weight arithmetic-sibling diagnostic, never independent evidence. |
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
`verified_calendar_year`, direct physical ancestry, alias group IDs,
arithmetic-sibling group IDs, and effective evidentiary role. Every required
4.B2 primitive is
referenced by at least one B2 family; every required 4.B11 worker primitive
is referenced by the worker-distribution families, every taxable primitive by
its reconciliation, and every contribution primitive by its reconciliation
or contribution-share family. A zero-weight transform sharing a primitive
with model choice is marked train/validation in 1968–2014 even though it
cannot enter loss or selection; it is never presented as held-out evidence in
those years. Its 2015–2022 expansion is held out. The B11
taxable/contribution diagnostics receive their verified train/validation role
before 2015 even though their loss weight is zero; their arithmetic closure
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
means. B11 arithmetic siblings and dependent B2 transformations cannot rescue
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
precision claim.

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

This identity expressly excludes full source-document SHA/size/capture
entries, artifact-wide content hashes, whole-document `source_sha256` fields,
held-out and zero-weight values/spec payloads, vintage-1 bytes, registration,
invocation, incident, configuration, and any digest whose byte domain includes
non-model-choice cells. `substantive_model_sha256` binds this canonical
object; the complete artifact, source manifests, alias registry, target
registry, and values remain mandatory in
`full_calibration_evaluation_provenance.v1`, whose hash is
`evaluation_provenance_sha256`. The latter enters input validation, sidecar,
primary integrity, and evaluation binding only. It cannot enter a parameter,
loss, selection decision, model hash, uniform, gate evidence hash, or
eligibility decision.

`heldout_noninterference_specs.v1` is a nonempty frozen fixture registry. It
provides a baseline and a structurally valid mutant in which:

1. every value not used by a positive-weight train cell or
   selection-eligible validation cell—including every held-out and
   zero-weight value—is replaced by a distinct domain-valid literal;
2. every source fragment exclusively owned by those cells, including every
   vintage-1-exclusive byte, is replaced;
3. all affected document, artifact, manifest, and evaluation-provenance
   hashes are recomputed; and
4. every model-choice cell and shared interpretation fragment remains
   byte-identical.

The fixture freezes every replacement and exact expected cardinality; an empty
mutation array fails. Baseline and mutant must produce byte-identical
parameter bit vectors, model-choice predictions and losses, candidate
dispositions, selection, model identity/hash, all expected and realized
substantive ledger hashes, the exhaustive keyed-uniform registry hash, every
hard-gate row and evidence hash, and
`correction_model_eligibility`. Only full evaluation provenance and the
changed diagnostic observations/residuals may differ. G21 enforces this
noninterference; a whole-document digest in the model/RNG path necessarily
fails it.

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
or label certificate exists. Human adjudication,
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
certificate. Making it load-bearing requires a new registered target family
with exact labels, partitions, losses, and tolerances before exposure.

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

`sensitivity_specs.v1` is a one-object ordered array. Its object has exactly
`sensitivity_id`, `label`, `input_selector`, `scalar_selector`,
`reference_era_specs`, `year_source_class_rule`, `pre_2015_rule`,
`post_2014_rule`, `allowed_outputs`, and `forbidden_uses`; every value is the
literal law in the preceding paragraph.
`allowed_outputs` is exactly `["sensitivity_results"]`, and
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
`rng_rule`, `provenance_literal`, and `failure_disposition`.
`gap_years` is exactly
`[1997,1999,2001,2003,2005,2007,2009,2011,2013]`; context keys are
`projection_draw_index`, `correction_draw_index`, `stable_person_id`,
`operative_claim_year`, and `career_variant_id`. Sources after the operative
claim year are discarded before neighbor lookup. If the gap is after the
claim year, no row is emitted. Otherwise each corrected, pre-statutory
covered-wage, covered-SE-gain, covered-SE-loss, noncovered, and unresolved
channel uses the exact rational mean when both adjacent years are admissible,
carries the only admissible neighbor when one exists, and receives the
registered `unknown` disposition when neither exists. The effective-gap-year
SECA factor/threshold and wage-first cap run only after that component vector
is derived. Already capped totals are never averaged, and gap derivation
consumes no new uniform. Neighbor years/hashes, operative claim year, draw,
and `structural_gap_imputed` provenance publish.

`earnings_consumer_dependency_specs.v1` has exactly `schema_version`,
`complete_final_metric_inventory`, `allowed_corrected_ledger_fields`,
`allowed_non_earnings_operands`, `forbidden_direct_earnings_operands`,
`required_ledger_dominator`, `legacy_before_block_exceptions`, and
`failure_disposition`. Its metric inventory is independently reconstructed
from the frozen Stage A–D benefit surface, unsplit revenue surface,
model-metric registry, every pairing, and every comparison spec. Every
earnings-valued leaf of a certified corrected metric must be dominated by the
hash-verified corrected-ledger accessor. Raw proxy and legacy first-estimates
numbers are permitted only in the typed `before_context` block and are
forbidden as corrected operands.

`gate_specs.v2` is the ordered 22-object registry corresponding positionally
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
   treatment, and other legal rules apply only to registered years and facts.
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
    provider; every projection, mortality, claiming, marriage, Python,
    NumPy, OS-entropy, or other forbidden provider has zero calls, and the
    exhaustive correction key→uniform registry independently recomputes.
12. No post-boundary questionnaire fact enters production; every gap right
    neighbor is no later than the operative claim year; opening-backfill
    adjudication precedes gap derivation; and no universal 2013 row is reused
    across claim contexts. Revenue has no 2013 key.
13. Career data-completeness and modeled OASDI coverage are separately named
    and computed.
14. A coordinator-owned second execution with every weight multiplied by the
    exact binary64 value `7.0` byte-matches each candidate's parameter bits,
    predictions, losses, identification/disposition, selected candidate,
    tie result, and substantive model hash; no level target is granted.
15. Broker grants, worker IPC hashes, physical ancestry/alias closure, and
    sandbox audit exact-match the derived allowlist. Fit/selection workers
    have no path, descriptor, network, subprocess, or content-alias access to
    vintage-1, anchor, held-out, benefit-total, Option-C, repository data,
    runs, or docs bytes.
16. Every unresolved amount follows the registered missing-fact policy and
    reason code. No objective term or gate rewards moving unknown mass from
    `unresolved` to covered or noncovered. Weighted unresolved gain/loss
    shares, person-year shares, and status entropy publish overall and by era
    × role, but v1 imposes no evidence-free magnitude cutoff.
17. The independently byte-pinned PSID inventory and crosswalk key streams and
    dispositions match positionally; every value-code/adjudication rule ID
    resolves once; the wave/reference/source-lineage map is exact; and every
    target/evaluation key is present. A missing job field or cell never
    shrinks the registry.
18. Nonlinear AIME/PIA results are computed within each complete correction
    career draw before reduction.
19. The selected candidate passes the parameter-count, full-rank Jacobian,
    condition-number, and deterministic solution-agreement law in §5.3, and every losing or
    failed candidate has its complete registered disposition. A losing
    candidate need not pass.
20. Every registered metric that uses correction draws passes the
    10-versus-20 correction-draw stability tolerance.
21. The complete held-out/zero-weight/exclusive-source-byte mutant in §6.2
    leaves parameters, model-choice losses, selection, substantive model
    hash, uniforms, ledger identities, every gate row/evidence hash, and
    eligibility byte-identical.
22. Every final corrected earnings-dependent metric in the complete
    independently reconstructed benefit, revenue, pairing, and comparison
    domains is transitively dominated by corrected ledger fields; raw proxy
    or legacy numeric earnings appear only in `before_context`. Every
    certified modeled-worker denominator uses
    `modeled_covered_worker_probability_analytic`, never a draw indicator or
    finite-grid fraction.

`rng_access_specs.v1` freezes the sole allowed provider—the §5.4 SHA-256
midpoint function—and every forbidden provider in the pinned environment:
all `ProjectionRNGRegistry` seed/factory methods, Python `random`,
`secrets`/`os.urandom`, NumPy `random`/`Generator`/`SeedSequence` entry
points, and discovered aliases. Before correction imports, the trusted
coordinator installs provider-level counting wrappers and an audit hook;
cached aliases, native-library, FFI, and subprocess bypasses are forbidden by
the implementation/source closure. Candidate code cannot write the ledger.
This detects a request for a fresh generator even though `rng.py` returns a
new object per call; before/after generator-state hashes are not evidence.

`weight_rescale_specs.v1` freezes exactly four comparison rows: one for each
of the three candidates' complete fit bundles and one for the selected
candidate/tie/model identity. The coordinator, not candidate code, supplies
identical packets twice and applies the exact `7.0` rescale to the second.
Registration also proves every positive-weight target is a share, ratio, or
intensity and the broker's level-target grant ledger is empty.

`filesystem_isolation_specs.v1` freezes the supported isolation backend,
worker executable/code hash, mount and descriptor allowlists, IPC schemas,
broker grant registry, forbidden physical/path/content-alias registry, and
audit policy. One fresh fit worker per candidate and a separate selector
worker see only preloaded cell-scoped packets and pinned runtime libraries;
repository `data`, `runs`, and `docs` are not mounted, non-IPC descriptors
are closed, and network, subprocess, late import, `open`, `os.open`,
`pathlib`, symlink, hardlink, and inherited-descriptor bypasses are denied.
Zero-weight diagnostics run separately; the held-out evaluator is created
only after model lock. An unavailable isolation backend aborts registration.

The executable selector/comparator map is:

| Gate | `evidence_selector` | `comparator` / `required_value` |
|---|---|---|
| G01 | `independently_derived_consumer_domain_and_support_results` | `exact_derived_domain_law / true` |
| G02 | `final_component_domain_scan` | `all_records_true / true` |
| G03 | `se_loss_offset_trace` | `all_records_true / true` |
| G04 | `atomic_and_person_year_reconciliation_residuals` | `all_exact_zero / true` |
| G05 | `unknown_disposition_trace` | `all_records_true / true` |
| G06 | `effective_year_legal_rule_trace` | `all_records_true / true` |
| G07 | `wage_first_combined_cap_trace` | `all_records_true / true` |
| G08 | `benefit_revenue_component_hash_pairs` | `all_hash_pairs_equal / true` |
| G09 | `recoverable_provenance_scan` | `all_records_true / true` |
| G10 | `replay_registry_results` | `exact_six_rows_all_hashes_equal / true` |
| G11 | `trusted_rng_provider_call_ledger` | `exact_forbidden_counts_zero_and_uniforms_recompute / true` |
| G12 | `information_cutoff_and_claim_context_gap_evidence` | `all_records_true / true` |
| G13 | `semantic_field_registry_scan` | `all_records_true / true` |
| G14 | `trusted_weight_rescale_reexecution_results` | `exact_four_rows_all_hashes_equal / true` |
| G15 | `broker_and_sandbox_access_evidence` | `exact_grants_and_forbidden_access_zero / true` |
| G16 | `unresolved_policy_and_disclosure_scan` | `all_records_true / true` |
| G17 | `inventory_crosswalk_lineage_and_required_cell_closure` | `all_exact_nonempty_registries_equal / true` |
| G18 | `nonlinear_draw_reduction_trace` | `all_records_true / true` |
| G19 | `selected_identification_and_candidate_dispositions` | `all_records_true / true` |
| G20 | `draw_prefix_stability_results` | `all_tolerances_pass / true` |
| G21 | `heldout_noninterference_results` | `all_substantive_bytes_equal / true` |
| G22 | `complete_consumer_dependency_dominator_results` | `all_corrected_paths_and_analytic_denominators / true` |

The selector strings are reserved result-builder entry points; each emits a
canonical evidence object whose SHA-256 is recorded in the hard-gate row.
Changing a selector, comparator, or required value is a gate-registry version
change and requires fresh registration.

### 8.2 Empirical evaluation

Hard correctness is necessary but not sufficient. The complete evaluation
also publishes:

- every train and validation target, prediction, residual, loss, tolerance,
  and pass/fail result;
- held-out target diagnostics only after selected-model bytes are locked;
- wage/SE composition, zero/positive incidence, quantiles, tail shares, cap
  exposure, unresolved shares, and modeled covered-worker incidence;
- changes in taxable payroll, contributions, top-35 composition, AIME, and
  PIA, reduced within projection and correction draws in the registered
  order; and
- Option C in a visually and structurally separate sensitivity block.

`evaluation_specs.v1` is an ordered expanded array. Each object has exactly
`metric_id`, `result_block`, `source_fields`, `population_selector`,
`weight_field`, `stratum_id`, `reference_era_id`, `year_source_class`,
`role`, `calendar_year`, `statistic`, `unit`, `draw_reduction`,
`stability_family`, and `gate_role`. Expansion order is the family order
below, listed source-field order, listed statistic order, overall then
reference-era × source-class × role strata, and ascending verified reference
year; IDs are the colon-joined components of that position. Every registered
combination has a row even when its count is zero.

| Family | Exact expansion |
|---|---|
| `composition` | Wage share and SE share of nonnegative covered gains; overall annual 1968–2022 and all registered reference-era×source-class×role aggregates. |
| `incidence` | Positive wage, positive SECA base, modeled covered worker, and combined-cap exposure weighted shares; same strata/years. |
| `distribution` | Weighted `p10,p25,p50,p75,p90,p95,p99` and top-`10,5,1` percent amount shares for `covered_employee_wages_uncapped`, `covered_seca_base_uncapped`, and `oasdi_person_taxable_payroll`; overall annual 1968–2022. Stable-person ID breaks weighted-quantile boundary ties. |
| `unresolved` | Weighted gain amount, SE-loss magnitude, and person-year incidence shares; overall annual and every reference-era×source-class×role aggregate, plus mean status entropy over modelable records. |
| `downstream_annual` | Corrected-minus-frozen-proxy taxable payroll, modeled contributions under frozen rates, and covered-worker incidence; overall annual 1968–2022. |
| `downstream_career` | Corrected-minus-proxy AIME, PIA, and top-35 membership-change share; `calendar_year: null`, overall registered career universe only. |

`population_selector`, weight, roles, rate fields, and
proxy-baseline fields are literal references into registered input/crosswalk
objects, not implementation defaults. Statistics use exact rational
accumulation and stable-key weighted algorithms. `draw_reduction` is
`analytic_linear_within_projection_draw` for a linear annual quantity,
`analytic_joint_state_within_projection_draw` for an annual composition,
incidence, SE-threshold, wage-first-cap, taxable-payroll, contribution, or
worker-indicator statistic under §§3.1–3.2, and
`projection_cross_correction_draw` for every distribution quantile, tail
share, and nonlinear career statistic. Each mode publishes the mean and
sample SD under §5.4's exact projection/correction reduction law. Applying
an annual threshold or cap to marginal expected components, computing a
quantile of expected person amounts, or reducing before the complete
within-draw statistic is forbidden. `stability_family` is exactly one §5.4
unit family for every `projection_cross_correction_draw` metric and
`not_applicable` otherwise. `gate_role` is `G20` exactly for those
correction-draw metrics and `diagnostic_only` otherwise. Any omitted expansion
row is failure.

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
  cross-vintage republication, shared denominator, or arithmetic sibling;
- leaking realized 2017–2023 PSID job facts into the 2015–2022 projection;
- calling PSID-internal prediction administrative validation;
- double-weighting B2 and B11 rounded arithmetic siblings; or
- allowing Option C or a post-hoc scalar to rescue a failed production
  candidate.

## 9. Evidentiary labels and the label-retirement certificate

### 9.1 Exact certificate conditions

The §3.4 proxy label retires only after a two-artifact proof and an external
merge event. The correction evaluation proves conditions 1–7:

1. the immutable legal, source-inventory, crosswalk, value-code/adjudication,
   wave/reference-lineage, gap-derivation, physical-cell/alias,
   ledger-schema/dependence, target, candidate, selection, draw, replay, RNG,
   isolation, domain, dependency, gate, and evaluation registries exact-match
   their registered bytes;
2. the common base ledger and operative-claim-year gap views exactly support
   the independently reconstructed complete Stage A–D benefit and unsplit
   revenue domains;
3. all 22 §8.1 hard gates and every registered model-choice validation
   tolerance pass;
4. `substantive_model_sha256` was locked before held-out release; its
   cell-scoped ancestry contains no vintage-1 or post-2014 primitive; and the
   full held-out/zero-weight/exclusive-byte noninterference mutation passes;
5. all raw inputs, deltas, source classes, status probabilities/draws,
   reasons, claim-context gap neighbors, and component outputs are recoverable
   and reconcile;
6. the exact six-row replay registry, row-order invariance, provider-call RNG
   isolation, cutoff-before-imputation, sandbox access, analytic-denominator,
   and nonlinear-draw laws pass; and
7. the sealed §10 runner has constructed and validator-accepted complete
   primary and sidecar bytes, with the primary binding the exact sidecar hash,
   before either final-path rename.

A `pass` correction report emits the exact
`correction_model_eligibility` object in §10.2 with conditions 1–7 equal to
`pass`.
That object is not a label-retirement certificate and cannot change a
published label or prove that both final paths now exist. A `gate_fail` or
`no_eligible_candidate` report emits it with `eligible: false`.

The separately registered context report then proves condition 8:

8. after correction-model lock it independently reconstructs the complete
   frozen corrected model-metric domain, all 14 pairings, and all nine
   comparison specs; rematerializes and hash-checks every applicable common
   ledger and claim-context gap stream; computes every corrected
   earnings-dependent metric exclusively through corrected ledger fields;
   confines legacy numeric values to the typed `before_context` block;
   transforms both `pairings[*].mismatch_codes` and
   `comparison_specs[*].mismatch_codes` positionally with unchanged
   cardinality/order and unaffected fields; uses analytic modeled-worker
   probabilities for every certified denominator; only then opens all 15
   vintage-1 series as context; publishes every required row regardless; and
   validates.

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
repository root; the entire tracked and untracked checkout is clean; no
tracked path has assume-unchanged or skip-worktree; no ignored executable
artifact exists below `src` or `scripts`; the design-ratification and
implementation commits both exist and are ancestors of `HEAD`; the design
blob at `HEAD`, at the ratification commit, and in the configured blob digest
is identical; the `HEAD:src` and `HEAD:scripts` tree OIDs equal the
corresponding implementation-commit tree OIDs; and the registration path is
tracked at `HEAD` with `git show HEAD:<path>` bytes equal to the
descriptor-read configuration. Exact `HEAD == implementation_commit` is not
required; records-only descendant commits are allowed.

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
`substantive_model_sha256`, `evaluation_provenance_sha256`, and
`selected_ledger_identity_sha256`.
`artifact_path` is the exact primary path; registration, commit, invocation,
and configuration hash equal the primary/configuration. `runtime` and
`attempt_evidence` deep-equal the corresponding primary objects.
`input_hashes` is the exact ordered union of
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
ledger hash are null exactly for the no-eligible branch and otherwise equal
the primary; `evaluation_provenance_sha256` is always nonnull and equals the
primary's full evaluation-provenance hash.

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
14. `psid_questionnaire_slot_specs`;
15. `psid_value_code_specs`;
16. `psid_annualization_rule_specs`;
17. `psid_reconciliation_rule_specs`;
18. `psid_job_spell_match_rule_specs`;
19. `psid_coverage_state_group_rule_specs`;
20. `physical_source_cell_specs`;
21. `official_source_alias_specs`;
22. `calibration_target_specs`;
23. `candidate_reference_era_specs`;
24. `candidate_specs`;
25. `selection_spec`;
26. `draw_spec`;
27. `replay_specs`;
28. `consumer_domain_derivation_specs`;
29. `benefit_gap_derivation_specs`;
30. `earnings_consumer_dependency_specs`;
31. `gate_specs`;
32. `rng_access_specs`;
33. `weight_rescale_specs`;
34. `filesystem_isolation_specs`;
35. `heldout_noninterference_specs`;
36. `evaluation_specs`;
37. `sensitivity_specs`;
38. `attempt_history`; and
39. `output_paths`.

The nested schemas are exact:

- `schema_version` is the configuration-schema literal above, and
  `registration_reference` is a nonempty JSON string.
- `design` has exactly `path`, `ratification_commit`, and `revision`.
  `path` is `docs/design/covered_earnings_correction.md`; the commit is 40
  lowercase hex; and revision is JSON integer `2`, excluding booleans.
- `implementation_commit` is 40 lowercase hex.
- `invocation` has exactly `orig_argv` and `pycache_sentinel`.
  `orig_argv` is the nonempty ordered JSON-string array containing every
  actual isolated-run argument: an absolute interpreter path, literal
  isolation flags `-I`, `-B`, and `-X`, the concrete
  `pycache_prefix=<absolute-path>` token, the exact runner path, and the exact
  registration path, with no shell interpolation or placeholder.
  `pycache_sentinel` has exactly absolute `path`, positive JSON-integer
  `st_dev`, positive JSON-integer `st_ino`, and JSON integer `mode: 448`
  (octal 0700). Before committing the registration, the coordinator creates
  that exact path with one exclusive `mkdir`, mode 0700, proves it is a
  non-symlink empty directory, and records the descriptor's device and inode.
  At process entry the runner requires byte-for-byte equality of
  `list(sys.orig_argv)` and `orig_argv`, equality of
  `sys.pycache_prefix` and the registered path, the same descriptor identity
  and mode, and continued emptiness. Any mismatch fails before a claim.
- `production_input_manifest` has exactly `schema_version`, `inputs`,
  `support_universe`, and `environment_spec`. Its schema literal is
  `covered_earnings_production_input_manifest.v2`. `inputs` is an ordered
  nonempty array; every object has exactly `input_id`, `path`,
  `schema_version`, `artifact_vintage_id`, `role`, and `sha256`, all strings,
  with a 64-lowercase-hex digest. It lists every permitted source byte and
  permits no wildcard, directory input, moving alias, duplicate ID/path, or
  unlisted open. `support_universe` has exactly `selector_id`,
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
  §6.1. Their input IDs for sidecar and primary validation are respectively
  the four literals declared above.
- Every `*_specs` top-level value is the exact registered deep copy of the
  correspondingly named frozen registry in §§3–8, with the versions declared
  there. They are neither digests nor implementation reconstructions.
  In particular `calibration_target_specs` is v2, `gate_specs` has exactly
  G01–G22, `replay_specs` has exactly six comparisons,
  `heldout_noninterference_specs` is nonempty, and none of the inventory,
  domain, alias, RNG, isolation, or adjudication-rule registries may be
  omitted.
- `attempt_history` has exactly `prior_incidents`,
  `prior_attempt_claims`, `prior_retry_authorities`, `prior_retry_claims`,
  and `prior_fresh_registration_adjudications`. Each is an ordered array of
  every prior record in that class, with objects containing exactly
  traversal-free `path` and 64-lowercase-hex `sha256`; incident and
  adjudication indices are contiguous and all cross-references close. The
  first registration has five empty arrays. Every later registration includes
  the complete history; a missing, extra, reordered, or digest-mismatched
  record aborts.
- `output_paths` has exactly `primary`, `sidecar`, `incident_prefix`,
  `attempt_claim_prefix`, `retry_authority_prefix`, `retry_claim_prefix`,
  and `fresh_registration_adjudication_prefix`. The first two are the exact
  paths above. The traversal-free literals are respectively
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

After strict parsing, repository proof, an exclusive coordinator lock,
complete-history validation, and all six value-blind pre-launch checks—but
before opening a production manifest path, target sidecar, projection input,
or other production byte—the coordinator:

1. generates an in-memory 256-bit retry nonce and computes its SHA-256
   commitment;
2. reserves the configuration-derived retry-authority path with
   `O_CREAT|O_EXCL|O_NOFOLLOW`, verifies a new single-link regular file,
   records its descriptor device/inode, fsyncs the empty file and parent, and
   retains the only writable descriptor;
3. creates the configuration-derived initial-attempt claim with
   `O_CREAT|O_EXCL|O_NOFOLLOW`; writes canonical
   `covered_earnings_correction_initial_attempt_claim.v1` bytes containing
   exactly `schema_version`, `registration_reference`,
   `configuration_sha256`, `claimed_at_utc`, `invocation_sha256`,
   `prelaunch_checks_sha256`, `pycache_sentinel`, `output_version`,
   `primary_path`, `sidecar_path`, `next_incident_index`,
   `retry_authority_path`, `retry_authority_st_dev`,
   `retry_authority_st_ino`, `retry_nonce_commitment_sha256`, and
   `prior_history_sha256`; then fsyncs, changes the claim to mode 0444,
   fsyncs the parent, and descriptor-rereads the exact bytes and identity; and
4. only after that durable reread mints the production-I/O capability.

The claim binds the exact six-check record and complete prior-history object.
Every later production open, broker grant, output stage, or incident write
revalidates the live claim path, bytes, digest, device, and inode. Claims are
never removed, truncated, renamed, or overwritten. A kill after any value
exposure therefore leaves durable evidence that this registration's initial
attempt was consumed; absence of a result or incident never restores a
“first” attempt.

### 10.2 Sealed phases and result contract

The isolated runner performs, in order:

1. **Registration and pre-launch.** Strict-parse the committed configuration;
   prove repository ancestry/tree/blob/cleanliness, complete attempt history,
   exact `sys.orig_argv`, and the concrete fresh-empty sentinel; take the
   exclusive lock; and perform the six value-blind checks. No production path
   or target sidecar is openable in this phase.
2. **Durable attempt claim.** Reserve the retry-authority inode and durably
   publish and reread the initial claim exactly as in §10.1. On an authorized
   retry, consume the opaque coordinator receipt and durably publish and
   reread the retry claim instead. Only the live claim mints production-I/O
   capability.
3. **Preparation and target brokering.** Open and hash only registered inputs;
   exact-check identities, manifests, frozen registries, physical-cell and
   alias closure, inventory/crosswalk closure, full prior history, and output
   absence. A capability-separated target validator may stream all target
   bytes but returns only schema/hash/cardinality/coverage proofs—never an
   observation, sign, rank, residual, or statistic. A fresh target broker
   converts verified, cell-scoped observations into role-specific packets.
   Candidate code receives no path or file-open capability.
4. **Fitting.** The broker exposes to each optimizer only positive-weight
   `train` cells with a fitting loss; run all three candidates and freeze
   their fitted parameter vectors. A capability-separated diagnostic
   evaluator then opens zero-weight train-role cells, records them, and
   cannot communicate a value or status back to an optimizer.
5. **Selection.** The broker newly exposes to the selector only
   `selection_eligible` validation cells and executes §7.2. After the
   selection decision is immutable, the separate diagnostic evaluator records
   zero-weight validation-role cells without communicating to the selector.
   If none is eligible, skip lock and selected-model evaluation, keep the
   held-out handle sealed, and publish the valid `no_eligible_candidate`
   branch below.
6. **Substantive lock.** For an eligible selection, serialize the
   cell-scoped correction-model
   identity below, record its SHA-256, close all fitting/selection mutation
   capability, and record the exact `lock_event` result below.
7. **Held-out evaluation.** Destroy every fitting/selection worker and its
   mounts before creating a held-out evaluator. Only after lock, open the
   held-out/vintage-1/evaluation handles and record first-exposure sequences.
   Compute full evaluation provenance; run all 22 hard gates, the exact six
   replays, exact four trusted weight-rescale executions, provider-call and
   sandbox audits, the noninterference fixture, complete diagnostics,
   10-versus-20 draw checks, downstream reductions, and Option C.
   Fit/selection workers never coexist with held-out filesystem visibility.
8. **Publication.** Construct and validate the complete primary and sidecar
   bytes. Stage both without occupying final paths, rename the primary
   atomically, then rename the sidecar atomically. The pair is not falsely
   described as one filesystem-atomic operation. A failure after the primary
   rename is the permitted partial state in §10.3.

Preparation's trusted validator is separate from the fit/selection process
and cannot communicate a target value, rank, sign, residual, or statistic.
“Exposure” document-wide means release of a decoded observation value beyond
that integrity-only validator; streaming bytes inside the validator is not
value exposure.
The broker logs every grant as an increasing JSON-integer
`exposure_sequence`. After the first held-out grant, the configuration,
candidate/model bytes, thresholds, seed/draw law, and selected identity are
immutable; the run may only complete or publish an incident.

The primary schema is the literal
`covered_earnings_correction_evaluation.v1` and has exactly these top-level
keys:

`schema_version`, `artifact_id`, `artifact_role`,
`registration_reference`, `configuration_echo`, `runtime_provenance`,
`attempt_evidence`, `status`, `candidate_evidentiary_labels`,
`selected_correction`, `results`, `integrity`, and `certifies_nothing`.

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
`certifies_nothing` is exactly
`["not-population-aligned",
"not-individual-administrative-covered-earnings-truth",
"not-ledger-entry-11-resolution"]`.

`selected_correction` is JSON null only for `no_eligible_candidate`.
Otherwise it has exactly `candidate_id`, `model_identity`,
`substantive_model_sha256`, `ledger_identity`, and `evaluation_binding`.
`model_identity` has exactly:

`schema_version`, `candidate_spec`, `parameter_vector`,
`historical_coverage_rule_sha256`, `psid_source_field_inventory_sha256`,
`psid_crosswalk_sha256`, `fit_selection_cell_identity`,
`ledger_row_schema_specs`, `coverage_state_dependence_specs`,
`candidate_reference_era_specs`, `selection_spec`, `draw_spec`,
`substantive_production_input_identity`, and
`implementation_commit`.

Its schema literal is `covered_earnings_correction_model.v2`; the specs are
exact registered deep copies. `parameter_vector` is in registered parameter
order and each object has exactly `parameter_id` and
`ieee754_binary64_hex`; the latter is the lowercase 16-hex-digit encoding of
the finite binary64 bits. `substantive_production_input_identity` has exactly
`schema_version`, `inputs`, and `support_universe`; it is derived
from the configured manifest's source bytes actually consumed to construct
candidate features, positive-weight train predictions, and
selection-eligible validation predictions. Each retained input omits `path`
and keeps exactly `input_id`, `schema_version`, `artifact_vintage_id`, `role`,
and `sha256`. Its schema literal is
`covered_earnings_substantive_production_input_identity.v1`.
Evaluation-only projection inputs, vintage-1 inputs, the full calibration
artifact, complete official source documents, target sidecars, and any digest
whose byte domain includes held-out or zero-weight cells are excluded.
Legal, inventory, crosswalk, and PSID bytes required by candidate construction
remain bound. The ordered inclusion/exclusion proof is itself registered and
G21 mutation-tests it.
`coverage_state_dependence_specs` is the exact registered §3.1 object, so the
same fitted parameters cannot acquire a different joint-status law.
`ledger_row_schema_specs` is the exact registered §3.1 object, so an
identical parameter vector cannot acquire a different ledger row meaning or
encoding.
`fit_selection_cell_identity` is the exact canonical
`fit_selection_cell_identity.v1` object in §6.2. It contains only the
verified cell-scoped bytes and physical ancestry of positive-weight direct
train and selection-eligible direct/boundary validation cells. It excludes
whole-document/source/artifact hashes, all held-out and zero-weight payloads,
vintage-1 bytes, configuration and incident history. A physical primitive
shared with model choice remains bound through its cell-scoped ancestry and
honest alias closure; an exclusive diagnostic byte does not.

`substantive_model_sha256` is SHA-256 of
`canonical_json_bytes(model_identity)` and becomes the immutable
`correction_version` and draw-namespace identity in §§3 and 5.4.
`evaluation_binding` has exactly `schema_version`, `artifact_id`,
`registration_reference`, `configuration_sha256`,
`full_calibration_evaluation_provenance`, and
`evaluation_provenance_sha256`. Its schema literal is
`covered_earnings_correction_evaluation_binding.v2`.
`full_calibration_evaluation_provenance` is the exact §6.2 v1 object and
contains the complete target artifact, complete source manifests and
document digests, all target specs/values, alias registry, inventory,
vintage-1 bytes, all evaluation-only inputs, and configuration binding.
Its canonical hash is `evaluation_provenance_sha256`. Neither the object nor
its hash enters the substantive model, a uniform, model-choice loss,
selection, gate evidence, or eligibility. Therefore a same-content retry or
fresh registration cannot silently reseed an identical substantive model,
and replacing only evaluation bytes changes provenance without changing any
substantive output. No output,
invocation, registration, incident-history, pycache, timestamp, display
rounding, or row order enters the substantive identity.

`ledger_identity` has exactly `schema_version`, `canonical_stream_law`,
`row_schema_sha256`, `support_keyset_sha256`, `expected_ledger_streams`, and
`realized_ledger_streams`. Its schema is
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

`results` has exactly:

`input_validation`, `candidate_dispositions`, `target_results`,
`lock_event`,
`hard_gate_results`, `replay_results`, `rng_access_results`,
`weight_rescale_results`, `isolation_results`,
`noninterference_results`, `support_results`,
`distribution_results`, `downstream_results`, `sensitivity_results`,
`target_use_trace`, and `correction_model_eligibility`.

Their schemas and completeness laws are:

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
  `pass | fail | not_evaluated`, `pass | fail | not_evaluated`, and
  `selected | eligible_not_selected | ineligible | not_evaluated`.
  `parameter_count` is a nonnegative JSON integer. Training loss is finite
  iff fit status is success; validation loss is finite iff validation status
  is pass or fail; otherwise the applicable loss is null. Reason codes are an
  ordered nonempty string array iff any disposition is failed, fail,
  ineligible, or not-evaluated because of an earlier failure; otherwise they
  are empty.
- `target_results` is ordered candidate, §6.2 family, then verified year.
  Every candidate has one slot for every train/validation spec; only the
  locked candidate has held-out slots. An evaluated, available slot has
  exactly `candidate_id`, `target_id`, `verified_calendar_year`,
  `effective_role`, `model_year_source_class`, `evaluation_status`,
  `observed`, `predicted`, `predicted_sample_sd`, `loss`,
  `diagnostic_error`, `tolerance`, `status`, `reason_code`, and
  `first_exposure_sequence`, with `evaluation_status: evaluated`.
  Numeric values are finite and `predicted_sample_sd` is nonnegative.
  A positive-weight train or selection-eligible validation cell alone may
  have nonnull `loss`; it has null `diagnostic_error` and status
  `fit_input | pass | fail`. A zero-weight or held-out cell always has
  `loss: null`, uses finite `diagnostic_error` when its operands are in
  domain, and has status `diagnostic_only | domain_fail_diagnostic`.
  `reason_code` is nonnull only for the exact §6.2 domain-fail branch.
  `tolerance` exact-matches the tagged spec object.
  An unavailable structural-gap diagnostic has the same keys but exactly
  `predicted: null`, `predicted_sample_sd: null`, `loss: null`,
  `diagnostic_error: null`,
  `status: no_claim_independent_model_analogue`, and
  `reason_code: no_claim_independent_model_analogue`; its observed official
  value and exposure sequence remain nonnull. It cannot materialize or stand
  in for a claim-context benefit gap row.
  A slot made unreachable by the candidate's first fit, identification, or
  domain failure instead has exactly `candidate_id`, `target_id`,
  `verified_calendar_year`, `effective_role`, `evaluation_status`,
  `first_exposure_sequence`, and `reason_code`, with
  `evaluation_status: not_evaluated` and the exact disposition reason.
  Exposure sequence is a positive JSON integer iff the broker released that
  observation and is null otherwise.
  Held-out slots are always diagnostic, never directly cause `gate_fail`,
  and have exposure sequences strictly greater than the lock. A `pass` or
  `gate_fail` report has exactly one for every held-out spec; a no-eligible
  report has none.
- `lock_event` is null exactly for `no_eligible_candidate`. Otherwise it has
  exactly `event_type`, `exposure_sequence`, and
  `substantive_model_sha256`, with literal
  event type `selected_model_lock`, positive JSON-integer sequence, and hash
  equal to `selected_correction.substantive_model_sha256`. Every held-out
  exposure follows it.
- Each selected-only results object is
  a tagged object. The evaluated branch has exactly
  `{"evaluation_status":"evaluated","rows":[...]}`. The unselected branch has
  exactly
  `{"evaluation_status":"not_evaluated",
  "reason":"no_eligible_candidate"}`. The following exact schemas and
  cardinalities apply; `rows: []` is invalid for every nonempty frozen
  registry:

  - `hard_gate_results` has exactly 22 rows, G01 through G22 in §8.1 order.
    Each has exactly `gate_id`, `status`, `observed`, `required`, and
    `evidence_sha256`.
  - `replay_results` has exactly the six `replay_specs.v1` rows in order.
    Each has exactly `test_id`, `left_run_id`, `right_run_id`,
    `left_fit_selection_bundle_sha256`,
    `right_fit_selection_bundle_sha256`,
    `left_substantive_model_sha256`,
    `right_substantive_model_sha256`,
    `left_ledger_identity_sha256`, `right_ledger_identity_sha256`, and
    `status`; every paired hash is equal.
  - `rng_access_results` has one row per `rng_access_specs.v1` provider in
    exact order, each with exactly `provider_id`, `call_count`,
    `argument_trace_sha256`, `uniform_registry_sha256`, and `status`.
    Forbidden providers have zero calls. The sole allowed provider's complete
    call ledger and the independently recomputed exhaustive key→uniform
    registry have the expected hashes. Fresh-generator state snapshots are
    not evidence.
  - `weight_rescale_results` has exactly four
    `weight_rescale_specs.v1` rows, each with exactly `comparison_id`,
    `base_bundle_sha256`, `rescaled_bundle_sha256`, and `status`; the hashes
    bind the registered parameter, prediction, loss, disposition, selection,
    tie, and substantive-model fields and must be equal.
  - `isolation_results` has exactly one row per
    `filesystem_isolation_specs.v1` assertion, each with exactly
    `assertion_id`, `worker_id`, `expected_grant_sha256`,
    `actual_grant_sha256`, `forbidden_access_count`, `audit_trace_sha256`,
    and `status`. Its cardinality and worker IDs are derived from the frozen
    worker/grant registry; every grant hash matches and every forbidden count
    is zero.
  - `noninterference_results` has exactly one row per nonempty
    `heldout_noninterference_specs.v1` fixture, each with exactly
    `fixture_id`, `baseline_substantive_bundle_sha256`,
    `mutant_substantive_bundle_sha256`,
    `baseline_evaluation_provenance_sha256`,
    `mutant_evaluation_provenance_sha256`, `mutation_count`, and `status`.
    Mutation count exact-matches the positive registered cardinality;
    substantive bundle hashes are equal and full provenance hashes differ.
  - `support_results` is independently expanded by projection draw,
    consumer, calendar year, Stage disposition, operative claim year, and
    career variant from `consumer_domain_derivation_specs.v1`. Each row has
    exactly `projection_draw_index`, `consumer`, `calendar_year`,
    `stage_disposition`, `operative_claim_year`, `career_variant_id`,
    `expected_key_count`, `ledger_key_count`, `missing_key_count`,
    `extra_key_count`, `expected_keyset_sha256`,
    `ledger_keyset_sha256`, and `status`. Null context dimensions occur only
    where the derivation registry says not applicable; missing and extra
    counts must be zero and hashes equal.
  - `distribution_results`, `downstream_results`, and
    `sensitivity_results` use the exact registered long schema `metric_id`,
    `stratum_id`, `calendar_year`, `statistic`, `mean`, `sample_sd`, `unit`,
    and `status`. A nonannual row has `calendar_year: null`; means/SDs are
    finite and SDs nonnegative.
- `target_use_trace` is one row per expanded target spec in registry order,
  with exactly `target_id`, `verified_calendar_year`, `effective_role`,
  `source_cell_ids`, `physical_source_cell_ids`,
  `primitive_ancestry_ids`, `alias_group_ids`,
  `arithmetic_sibling_group_ids`, `effective_evidentiary_role`,
  `broker_packet_sha256`, `first_exposure_phase`,
  `first_exposure_sequence`, `used_for_fitting`, `used_for_selection`, and
  `used_for_diagnostic`. Year and all identity arrays are independently
  reconstructed by the trusted validator from physical source identities and
  exact-match the frozen target/alias closure; they are not accepted from
  worker self-report. `effective_evidentiary_role` applies
  `fit > selection > diagnostic` across the complete physical closure.
  `broker_packet_sha256` binds the only value packet that can reach a worker.
  An unopened held-out row has both exposure fields and packet hash null and
  all three booleans false, permitted only in `no_eligible_candidate`. In
  `pass` or `gate_fail`, every held-out row is opened only in evaluation and
  has diagnostic true. A held-out physical closure can never have fitting or
  selection true. A nonnull phase is `fitting | selection | evaluation`; its
  sequence is a positive JSON integer, and phase, sequence, and applicable
  packet hash obey their exact branch law. Every evaluated target result
  points to the matching trace sequence.
- `correction_model_eligibility` has exactly `condition_1`, `condition_2`,
  `condition_3`, `condition_4`, `condition_5`, `condition_6`, `condition_7`,
  and `eligible`. Each condition is the string
  `pass | fail | not_evaluated`; `eligible` is a JSON boolean, true iff a
  selected correction exists and every condition is `pass`. A `pass` report
  has seven passes. A `gate_fail` has only pass/fail values and at least one
  fail. `no_eligible_candidate` has condition 1 `pass`, conditions 2–6
  `not_evaluated`, condition 7 `pass` for the validator-accepted failure
  report bytes, and eligibility false. These are recomputed and are not the
  §9 label certificate. Condition inputs exclude
  `evaluation_provenance_sha256`; G21 proves that changing only held-out,
  zero-weight, or vintage-1-exclusive bytes cannot change any condition.

`status` is an exact tagged-union discriminator:

- `pass` requires a nonnull selected correction, every selected-only block
  evaluated, all correctness and registered validation conditions passing,
  and `correction_model_eligibility.eligible: true`;
- `gate_fail` requires a nonnull selected correction, complete selected-only
  evaluation, at least one declared failed condition, and eligibility false;
  it is a normal publishes-regardless result, not an incident; and
- `no_eligible_candidate` requires selected correction null, all three
  candidate dispositions and all phase-reachable train/validation rows,
  null `lock_event`, no held-out exposure, every selected-only block in the
  exact `not_evaluated` branch, and eligibility false.

`integrity` has exactly `configuration_sha256`, `sidecar_sha256`,
`substantive_model_sha256`, `evaluation_provenance_sha256`, and
`ledger_identity_sha256`. Configuration, sidecar, and evaluation-provenance
hashes are always 64 lowercase hex; substantive-model and ledger hashes are
null exactly in the no-eligible branch.
`substantive_model_sha256` otherwise equals the selected correction;
`evaluation_provenance_sha256` always hashes the full evaluation binding; and
`ledger_identity_sha256` otherwise hashes canonical
`selected_correction.ledger_identity`. The primary records
SHA-256 of the exact sidecar bytes. Results validation checks array positions
before lookup, recomputes selection, losses, gates, hashes, and status, and
rejects every missing, extra, duplicate, reordered, wrong-branch, wrong-type,
wrong-unit, wrong-role, wrong-year, nonfinite, or unjustified-null value. A
self-reported pass flag has no authority.

### 10.3 Incidents, opaque retry receipts, and fresh registration

An exception in preparation maps to incident phase `preparation`; an
exception in fitting, selection, lock, or evaluation maps to `compute`; a
report/schema/recomputed-invariant failure maps to `invariant`; and a final
path/write/rename failure maps to `publication`. Candidate ineligibility,
validation-tolerance failure, or a hard-gate result is never an incident.

The writer uses the next contiguous append-only path
`runs/covered_earnings_correction_evaluation_incident_<n>.json`, where \(n\)
is canonical positive base 10 without a leading zero. The path is directly
under `runs/`, contains no traversal, and must not exist. It is created with
`O_CREAT|O_EXCL|O_NOFOLLOW`, descriptor-validated, fsynced with its parent,
made read-only, and descriptor-reread. Its object has exactly these keys:

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
- `no_estimate_bearing_information_yielded`: a JSON boolean supplied by the
  trusted coordinator's grant/output audit; and
- `artifact_path`: JSON null except iff phase is `publication` and a partial
  primary exists, when it is exactly the traversal-free primary path in
  §10.1 and that file exists.

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
proves `no_estimate_bearing_information_yielded: true`. It then:

1. revalidates the exact configuration, initial-claim bytes/inode, incident
   bytes/inode, reserved authority bytes/inode, nonce commitment, and absence
   of any retry claim;
2. writes through the retained reservation descriptor the canonical
   `covered_earnings_correction_retry_authority.v1` object with exactly
   `schema_version`, `registration_reference`, `configuration_sha256`,
   `triggering_incident_path`, `triggering_incident_sha256`,
   `initial_claim_path`, `initial_claim_sha256`, `sealed_at_utc`,
   `retry_nonce_sha256`, and `no_estimate_bearing_information_yielded`,
   fsyncs it and its parent, changes it to mode 0444, and descriptor-rereads
   its exact bytes and original inode; and
3. mints a private `_RetryReceipt` whose constructor and class identity are
   unavailable to runner/configuration code, stores it in an in-memory
   identity registry, and returns only that object to the coordinator's
   retry entry point.

The receipt is neither JSON nor serializable. It binds the repository root,
registration/configuration bytes, initial claim bytes/inode, triggering
incident bytes/inode, sealed authority bytes/inode, nonce, invocation, and
no-yield audit. The retry entry point atomically pops it once, rechecks every
binding, and rejects a forged object, replay, second pop, changed byte,
different root or process, newer incident, or any intervening exposure.
Possessing or constructing byte-identical public records never authorizes a
retry.

Before the retry may open a production byte, the coordinator creates the
configuration-derived retry-claim path with
`O_CREAT|O_EXCL|O_NOFOLLOW`. Its canonical
`covered_earnings_correction_retry_attempt_claim.v1` object has exactly
`schema_version`, `registration_reference`, `configuration_sha256`,
`claimed_at_utc`, `invocation_sha256`, `initial_claim_path`,
`initial_claim_sha256`, `triggering_incident_path`,
`triggering_incident_sha256`, `retry_authority_path`,
`retry_authority_sha256`, `retry_authority_st_dev`,
`retry_authority_st_ino`, `receipt_consumption_sha256`, `primary_path`, and
`sidecar_path`. It is fsynced, made mode 0444, parent-fsynced, and
descriptor-reread before minting the retry production-I/O capability. Every
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

After any consumed initial claim not followed by a complete report pair, a
new configuration may register only after the coordinator durably publishes
the next append-only
`covered_earnings_correction_fresh_registration_adjudication.v1`. It has
exactly:

`schema_version`, `adjudication_index`, `adjudicated_at_utc`,
`prior_registration_reference`, `prior_configuration_sha256`,
`attempt_claim_path`, `attempt_claim_sha256`, `retry_authority_path`,
`retry_authority_sha256`, `retry_claim_path`, `retry_claim_sha256`,
`terminal_incident_path`, `terminal_incident_sha256`, `exposure_state`,
`output_path_state`, and `disposition`.

Authority, retry-claim, and terminal-incident path/hash pairs are each both
null or both nonnull as history requires. `exposure_state` is
`none | possible | confirmed`; `output_path_state` is
`absent | partial_primary | complete_pair`; and `disposition` is
`same_output_version_new_registration | new_output_version |
heldout_vintage_tainted`. The adjudicator reconstructs these states from
claims, broker grants, process/output audits, and durable paths; the failed
runner cannot declare them. A same-v1-output fresh registration is allowed
only when both final paths are absent and the exposure consequence permits
it. A partial primary requires a newly ratified output version. Possible or
confirmed held-out/vintage-1 exposure permanently taints that evidence for
later fitting/selection and cannot be relabeled held out by a fresh
registration. The new registration's changed complete-history bytes produce
a new configuration SHA and therefore fresh claim namespaces. All prior
claims, authorities, incidents, and adjudications remain append-only.
If the process dies after reserving the authority inode but before the
initial claim becomes durable, no production capability or exposure exists,
but the old namespace is still consumed; the same fresh-registration
adjudication records `exposure_state: none` before a new registration.

### 10.4 Six pre-launch checks

The coordinator records:

1. the ratified design blob, committed configuration, implementation
   ancestor, clean checkout, and exact implementation `src`/`scripts` tree
   identity under §10.1;
2. a fresh registration reference, complete prior-attempt history, and every
   required fresh-registration adjudication;
3. expected production paths, immutable IDs, and hashes compared only with
   the committed registration—without opening a production input, target
   sidecar, or output;
4. absence/state of the primary and sidecar, exact next incident and
   adjudication indices, absence of this configuration's claim paths, and the
   registered sentinel's exclusive creation, absolute path, emptiness, mode,
   device, and inode;
5. byte equality of the registered concrete `invocation.orig_argv` with
   `sys.orig_argv`, including its absolute interpreter, literal isolation
   flags, actual absolute `pycache_prefix` token, exact runner, and exact
   registration path; and
6. acknowledgment of `publishes_regardless`, incident publication,
   durable-claim consumption, `no_self_rescue`, and the law below.

These are six exact registered records with nonempty evidence hashes, not six
self-reported booleans. Checks 1–5 precede the initial claim and production
capability. On the opaque retry entry, the same six records are revalidated
and receipt/authority/claim evidence is appended; no command placeholder,
shell reconstruction, or new CLI argument exists.

### 10.5 Sole normative execution law

The correction evaluation has one registered configuration, one durably
claimed initial attempt, `publishes_regardless`, and `no_self_rescue`.
Its state machine is:

```text
REGISTERED_UNCLAIMED
  -> INITIAL_CLAIMED
  -> COMPLETE_RESULT
   | PUBLISHED_TERMINAL_INCIDENT
   | PUBLISHED_RETRY_ELIGIBLE_INCIDENT
       -> LIVE_PRIVATE_RECEIPT
       -> RETRY_CLAIMED
       -> COMPLETE_RESULT
        | PUBLISHED_TERMINAL_INCIDENT
```

The sole retry is possible only after the initial claim, a durably published
`preparation | compute` incident with `external_` reason, absent final paths,
and the coordinator's proof that no estimate-bearing information was yielded;
only the same-process opaque one-shot receipt authorizes it. The retry uses
the unchanged configuration and invocation and must publish its own durable
retry claim before any production access. Public records, a recreated
process, or an eligible-looking JSON object are never retry authority.

A complete `pass`, `gate_fail`, or `no_eligible_candidate` result; an
invariant or publication incident; any possible/confirmed estimate exposure;
a partial primary; a changed byte; a nonexternal incident; receipt loss; a
killed claimed attempt without an eligible incident; or a retry failure
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

None. “Out-of-sample” for the post-correction context event is qualified in
§12 as structurally out of the fitting sample because the 2015–2022 cells
have already been viewed. This is an honesty clarification, not a deviation
from the coordinator ruling.

## 12. What this unlocks

1. **Post-correction context evidence.** After a `pass` correction report
   pair is published and its publication PR merges, a new fresh registration
   pins that primary's exact path, file SHA-256, sidecar SHA-256, and
   `selected_correction.model_sha256`, plus SHA-256 of
   `selected_correction.ledger_identity`. Its append-only output is
   `runs/covered_earnings_context_report_v1.json`, its sidecar is the exact
   `<primary>.env.json`, and its schema is
   `covered_earnings_context_report.v1`. The configuration also pins
   `runs/first_estimates_v1.json`, the immutable 15-series vintage-1
   artifact, unchanged applicable legacy comparison formulas, corrected
   metric selectors, target-use masks, the §9.2 transformation, and the exact
   §10.2 ledger stream hashes it must rematerialize before comparison.

   That runner is fixture-only before registration, one-shot,
   `publishes_regardless`, `no_self_rescue`, incident-bearing, and governed by
   a separately ratified entry-8/10-style execution law. It cannot mutate,
   refit, reselect, or reject the locked correction. Its sealed report opens
   the 15 series only as context evidence and publishes every registered
   before/after diagnostic with no required direction. It calls the event
   `structurally-out-of-fitting-sample`, never unseen: those 2015–2022 values
   have already been viewed.

   On a validator-passing result, `label_retirement_certificate` has exactly
   `status`, `correction_evaluation_path`,
   `correction_evaluation_sha256`, `correction_model_sha256`,
   `correction_ledger_identity_sha256`, `context_report_schema`,
   `condition_8`, `successor_labels`,
   `retired_codes`, `replacements`, `new_codes`, and `preserved_codes`.
   `status` is `eligible_on_publication_pr_merge`; `condition_8` is boolean
   true; labels are the exact §1 array; and every code array/map exact-matches
   §9.2. A failed report carries JSON null instead, publishes its complete
   failure, and changes no label. The artifact cannot assert condition 9;
   only its publication-PR merge activates the certificate and resolves
   entry 11.

2. **W1 bridge on corrected earnings.** W1 can build the national population
   bridge on the immutable corrected ledger rather than the labor-income
   proxy. Roster, weights, population alignment, and national levels remain
   W1's authority, not this correction's. W1 must pin the correction-model
   hash, production-input identity, row schema, and applicable expected/draw
   ledger stream hashes; it must rematerialize and verify them before
   bridging and may not rewrite components.

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
and the non-load-bearing magnitude is in bucket C. No atomic claim appears in
two buckets.

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

| ID | VERIFY item | Required disposition and failure consequence |
|---|---|---|
| V-B1 | Exact Section 218 and mandatory state/local coverage law and effective dates | Pin controlling primary bytes and effective-year rules in §4.1. Missing/conflicting years abort legal-registry ratification and full correction. |
| V-B2 | Exact clergy, minister, church-employee, religious-order, and exemption rules | Pin primary bytes and required facts. Failure forbids direct clergy exclusion and blocks any candidate relying on it. |
| V-B3 | Exact historical residual-exclusion rules for domestic/agricultural thresholds, election, family/casual, foreign-government/international-organization, nonresident-alien, and similar service | Pin effective-year rules. An unverified class is modeled/unresolved and cannot be directly classified; a load-bearing gap aborts full certification. |
| V-B4 | Historical pre-1990 SECA eligible-concept, net-earnings-factor, threshold, and coordination crosswalk | Pin every effective-year transform. A year gap aborts registration. |
| V-B5 | Exact common 1968–1974 and spouse/secondary-job industry/occupation classifier availability and meaning | Verify each raw field/label/code in the expanded crosswalk. Structural absence is recorded explicitly; a false common mapping aborts. |
| V-B6 | Exact pre-modern spouse and secondary-job self/other and incorporation support | Verify every role/job/year source. Missing support cannot be extrapolated and follows the modeled/unresolved rule. |
| V-B7 | SSA covered-share publication, table, vintage, annual definition, numerator, denominator, duplicate-worker treatment, timing, and universe | Pin source bytes proving that the official numerator and denominator share one exact universe, then freeze the frame-relative model analogue under §6.2. Any mismatch, including annual-unique versus point-in-time, aborts target-artifact registration; no approximate 94-percent input exists. |
| V-B8 | Earlier enrollment-field coverage and a stable cross-wave mapping | Verify the literal fields and meanings. Structural absence is explicit; enrollment still cannot establish the student/employer nexus. |
| V-B9 | Exact effective-year student-service exception and employer-school nexus rule | Pin controlling primary bytes and required enrollment, regular-attendance, employer, and service facts. Missing law or facts forbids direct student exclusion; a candidate that depends on such exclusion is ineligible. |

The legal registry also fail-closes CSRS/FERS/CSRS Offset,
and Railroad-covered employer/service even though those source-fact absences
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
fact is load-bearing in v1.

## 14. Ratification and decision-closure checklist

### 14.1 Open-decision settlements

| Scoping open decision | Settlement |
|---|---|
| Exact estimands | §3 freezes uncapped covered wages, pre-SECA net earnings, SECA base, noncovered/unresolved amounts, person taxable payroll, benefit-creditable earnings, modeled worker incidence, and zero v1 deemed credits. |
| Full support feasibility | Full 1968–2022 support for both consumers is a demonstrated gate; failure permits only §11.2 and retains benefit proxy labels. |
| Historical legal authority and named classes | §4.1 freezes authority precedence, byte-pinned effective-year registry, required facts, and fail-closed treatment for every named class. |
| Complete PSID crosswalk and era seams | §4.2 freezes the expanded key/schema, source precedence, business/farm reconciliation, annualization, mixed-job handling, missingness, and era laws. |
| Production cutoff, entrants, and odd years | §4.3 preserves direct observed lineage through 2012, the frozen gap-imputed 2013 seam, and only frozen 2014 seed attributes thereafter; annual modeled transitions govern incumbents/entrants; odd-year earnings carry remains. |
| Probabilities, imputations, draws, nonlinear AIME/PIA | §§5.1 and 5.4 make expected mappings primary, require 20 keyed correction draws where nonlinear distribution matters, and compute benefits within career draw. |
| Target artifact, years, loss, partition, viewed cells | §6 creates immutable vintage 2; 1968–2008 trains, 2009–2014 validates, 2015–2022 diagnoses; losses/tolerances are literal; none of the 15 series fits; viewed-cell honesty is explicit. |
| B2/B11 and covered-share extraction | §6 and D-A1 require B2/B11 extraction, literal discrepancy preservation, and pre-2015 scale-free targets; V-B7 requires an exact official covered-share universe or aborts. |
| Post-calibration label vocabulary | §1 freezes exactly `frame-relative`, `modeled-covered-earnings`, `aggregate-concept-calibrated-not-population-aligned`. |
| Cap, SE threshold/loss, incorporated owners, historical SECA | §§3.2 and 4.1 freeze component floors, within-SE-only loss netting, effective-year law, wage-first residual cap, incorporated salary, and excluded distributions. |
| Candidate set, thresholds, namespace, replay, certificate | §§5.3–5.4, 6.2, 7, 8, and 9 freeze all of them and prohibit post-hoc rescue. |
| Versioning and mismatch disposition | §§6, 9, 10, and 12 freeze distinct artifact/report identities and exact retired, replaced, new, and preserved mismatch treatment. |

### 14.2 Ratification checklist

Ratification requires affirmative evidence for every item:

- [ ] The document settles every §14.1 decision with no contradictory rule.
- [ ] Every scoping `VERIFY` appears in exactly one §13 bucket and no
  unresolved VERIFY supplies a coefficient, rule, field, target, or claim.
- [ ] The legal and crosswalk registries have literal ordered IDs, exact key
  sets/types, effective-year coverage, source hashes, and missing/duplicate/
  extra rejection.
- [ ] Vintage 2 has immutable identity, exact source/cell provenance,
  canonical serialization, pinned hashes, offline reproduction, and an
  append-only refresh law.
- [ ] `calibration_target_specs` freezes every cell's role, dependency group,
  loss, weight, tolerance, transformation, unit, and selector before fitting.
- [ ] All 15 vintage-1 series are structurally inaccessible to fitting and
  selection and described as already viewed.
- [ ] Candidate, hyperparameter, convergence, selection, tie, Option-C, and
  candidate-failure laws exact-match registration.
- [ ] Full 1968–2022 support and identical benefit/revenue components are
  executable assertions, not prose claims.
- [ ] All scoping hard-correctness gates and circularity prohibitions are
  normative and conjunctive.
- [ ] Expected mappings, 20-draw namespace, nonlinear benefit propagation,
  frozen ledger-row schema, within-year dependence groups, byte replay,
  row-order invariance, and RNG isolation are executable.
- [ ] Aggregate motivation states both high per-worker ratios and
  approximately 1.01→0.80 aggregate payroll, with no unconditional sign.
- [ ] Scope exclusions and the revenue-only degradation are exact and cannot
  retire report-wide proxy labels.
- [ ] The label certificate enumerates full conditions plus exact retired,
  replaced, new, and preserved mismatch literals.
- [ ] Configuration, correction-model identity, primary tagged unions,
  result rows, incident objects, target-exposure phases, and output paths
  exact-match §10's schemas and validators.
- [ ] Consumer domains, projection/correction reductions, and deterministic
  ledger-rematerialization hashes are complete and independently recomputed.
- [ ] §10.5 is the sole normative evaluation execution law and enforces
  one-shot, publishes-regardless, incidents, and fresh registration.
- [ ] The post-correction context event and W1-on-corrected-earnings successor
  are named without claiming already-viewed evidence is unseen.
- [ ] `Deviations` is accurate.

### 14.3 Staged ratification protocol

The authorized order is:

1. merge this referee-ratified design, with no authority artifact,
   implementation, or production result smuggled into the design commit;
2. merge a separate referee-gated authority/extraction PR containing the
   legal registry, PSID crosswalk, retained source captures, literal
   manifests, vintage-2 target artifact, and the literal
   `ledger_row_schema_specs`, `coverage_state_dependence_specs`,
   `calibration_target_specs`, `candidate_specs`, `selection_spec`,
   `draw_spec`, `gate_specs`, `evaluation_specs`, and `sensitivity_specs`
   authorities, plus builders and offline reproduction/rejection tests;
3. merge a separate referee-gated implementation PR whose rehearsals are
   fixture-only and structurally reject production paths;
4. obtain a fresh registered §10.1 configuration binding every preceding
   commit, artifact byte, registry, invocation, incident history, and output
   path;
5. record all six §10.4 checks and launch the sealed §10.5 ceremony exactly
   once;
6. publish the complete report pair or incident unchanged in a
   publishes-regardless PR; only a validator-passing `pass` pair may become
   the correction input to §12;
7. after that pass PR merges, separately ratify and freshly register the
   context-report configuration, then execute and publish its complete
   report or incident regardless; and
8. only merge of the validator-passing context-report PR activates the
   conditional certificate, retires the proxy label, and resolves forecast-
   ledger entry 11.

Changing any registered byte, registry member/order, source, target value or
role, candidate, tolerance, seed/draw law, implementation commit, invocation,
incident history, or output path invalidates the registration. It cannot be
“noted” after launch; it requires a fresh registration and, if an append-only
path was consumed, a newly ratified version.

Until every box is ratified and the later publication sequence completes,
the §3.4 labor-income proxy label remains in force.
