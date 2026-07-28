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
`(stable_person_id, calendar_year, role, source_job_id, source_component_id)`.
The complete key is stable across input row order. `source_job_id` may be a
registered synthetic identifier for an aggregate questionnaire component,
but never a row number.

Every atomic record carries the following fields or the run aborts:

| Field | Frozen meaning |
|---|---|
| `proxy_labor_income_raw` | Original signed proxy amount, unchanged and recoverable. |
| `adjudicated_source_amount` | Signed annualized amount after the §4 crosswalk, before the Option-B measurement transform. |
| `measurement_adjusted_gain_amount` | Finite, nonnegative Option-B gain or wage amount. It is zero for an admissible SE loss. |
| `measurement_adjusted_se_loss_magnitude` | Finite, nonnegative magnitude of an admissible SE loss; zero for wages, gains, and a negative non-SE anomaly. |
| `measurement_adjusted_net_amount` | Exactly `measurement_adjusted_gain_amount - measurement_adjusted_se_loss_magnitude`; it may be signed only for an admissible SE concept. |
| `measurement_delta` | Exactly `measurement_adjusted_net_amount - adjudicated_source_amount`; it may be signed. |
| `status_probabilities` | Ordered four-value vector for `covered_wage`, `covered_self_employment`, `noncovered`, `unresolved`; finite, in `[0,1]`, and summing to one within \(10^{-12}\). |
| `status` | Deterministic class when one probability is exactly one; otherwise `modeled_distribution`. Draw rows carry one of the four realized classes. |
| `classification_reason_codes` | Ordered, nonempty registered reason-code array. |
| `source_provenance` | Source wave, role, job/component, `se_aggregation_group_id`, reference year, raw field IDs, unit, missing-code disposition, observed/imputed/projected status, and admissible-information date. |
| `correction_version` | Immutable selected correction identity and canonical SHA-256. |
| `uncertainty_provenance` | `expected_value` or the exact §5.4 correction-draw namespace and index. |

All ledger money is canonical signed integer microdollars after one registered
round-half-even conversion at the Option-B boundary. For each atomic
expected-value record, the four status-allocated nonnegative gain amounts
equal `measurement_adjusted_gain_amount` with literal zero integer residual,
and the four nonnegative loss magnitudes separately equal
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
| `positive_covered_se_worker_probability_analytic` | Analytic probability of positive covered SECA base in the registered annual worker universe. |
| `modeled_covered_worker_probability_analytic` | Analytic probability, under the registered joint wage/SE status mapping, that person taxable payroll is positive. This is the covered-share calibration selector and is not `proxy > 0`. |
| `modeled_covered_worker_draw_indicator` | Zero/one indicator within one correction draw that taxable payroll is positive. |
| `modeled_covered_worker_draw_grid_fraction_20` | Arithmetic mean of the 20 draw indicators. It is a finite-grid approximation, never renamed an exact probability. |

For analytically independent homogeneous derived components with positive-base
probabilities \(p_k\), unique-worker probability is
\(1-\prod_k(1-p_k)\). Any registered dependence from a shared mixed-allocation
variate replaces that product with its exact joint formula in
`candidate_output_selector`; summing wage and SE probabilities is forbidden
because a person may have both.

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

The canonical component ledger is written or materialized once per correction
version and draw. Career assembly and revenue receive its canonical hash and
typed views. They may apply benefit or contribution rates after the common
ledger, but may not alter classification, measurement, annualization,
nonnegativity, wage/SE ordering, or correction draws. For every
`(projection_draw, correction_draw, person, year)`, the component bytes
consumed by the two paths must be identical. A career-only correction,
revenue-only correction, or independently sampled pair fails.

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
literature is not legal authority. Missing bytes, source-hash drift,
overlapping effective dates, a year gap, conflicting same-rank rules, an
unregistered transform, or absent required micro facts aborts direct
classification. The record then follows its predeclared modeled or
`unresolved` action; it never takes a guessed legal status.

The treatment of named risk classes is frozen:

| Risk class | V1 disposition |
|---|---|
| State/local | Government level alone never proves coverage or noncoverage. Direct classification requires the registered Section 218 group/position and public-retirement-system facts. Otherwise use the registered expected mapping or `unresolved`. |
| Federal | Federal status alone never identifies CSRS, FERS, or CSRS Offset. Direct treatment requires the registered system/service facts; otherwise modeled or unresolved. |
| Railroad | Industry/occupation alone never proves Railroad-covered employer or service. Directly supported Railroad remuneration is non-OASDI; separately covered jobs remain separate. Unsupported cases are modeled or unresolved. |
| Clergy/religious | Occupation alone never proves a ministerial concept or approved exemption. Direct treatment requires the registered remuneration and exemption facts. |
| Student | Enrollment and education industry never prove the employer-school nexus or statutory student exception. Absent that nexus, no direct exclusion is allowed. |
| Residual statutory exclusions | Domestic/agricultural thresholds, election work, family/casual service, foreign-government or international-organization service, nonresident-alien rules, and any other class require an effective-year registered rule and its required facts. |

### 4.2 Complete source crosswalk

The implementation must create an immutable, literal, fully expanded
`psid_covered_earnings_crosswalk.v1`. Every object has exactly:

`interview_wave`, `earnings_reference_year`, `role`, `job_slot`,
`source_component_id`, `raw_field_ids`, `label_text`, `reporting_unit`,
`periodicity`, `month_presence_fields`, `assignment_fields`,
`self_other_field`, `incorporation_field`, `government_level_field`,
`industry_field`, `occupation_field`, `enrollment_field`, `missing_codes`,
`structural_missing`, `admissible_information_date`, `annualization_rule_id`,
`reconciliation_rule_id`, `job_spell_match_rule_id`, and
`era_seam_reason_codes`.

The registry contains exactly one disposition for every
`earnings_reference_year = 1968..2022` × admissible role × source job/component
in the production input domain. A structural absence is an explicit value,
not an omitted row. Duplicate keys; an unregistered role transition; a
missing field label, unit, code, or source column; or a field that does not
exist in the pinned input schema aborts registration.

The era law is:

| Reference-year era | Frozen adjudication |
|---|---|
| 1968–1974 | Preserve role labor totals. Context fields not verified as common across the era are structural missing and use registered expected allocation or remain unresolved. |
| 1975 | Admit only the self/other and broad-government fields whose exact role coverage is verified in the crosswalk; do not extrapolate head fields to spouse or secondary jobs. |
| 1976–1978 | Carry the spouse wages-only seam explicitly. Any spouse farm/business amount is appended only from a separately verified source component; otherwise its missing component is modeled or unresolved, never assumed zero. |
| 1979–1993 | Edited labor totals include farm/business labor parts. Separate business/farm fields may split or validate the total but are never added a second time. |
| 1994–2002 | Edited labor totals and separately carried business/farm labor amounts are combined exactly once under the registered role allocation; changing code systems and job support remain explicit strata. |
| 2003–2013 | Modern multi-job blocks are reconciled to role totals. Reporting units require the registered annualization rule and month presence; current-job timing may not be treated as prior-year income without the registered match. |
| 2014 | Consume the frozen `boundary_2014` proxy row and initialize the §4.3 synthetic projected-component path. It is not relabeled as an observed job row. |
| 2015–2022 | Consume the frozen projected labor proxy and the §4.3 annual component/status path. No realized post-boundary PSID job fact is admissible. |

Direct role/job annual amounts have first source precedence. Role totals and
separate components have second precedence and must reconcile under the era
law. Underidentified mixed employee/self-employed amounts use the registered
conditional expected allocation; distributional allocation uses §5.4 draws.
A combined family farm amount is never silently assigned to a person. It
uses verified role labor/ownership information, a registered expected
allocation, or `unresolved`.

Annualization is a named pure rule over the literal reporting unit,
reference-period definition, and admissible month/week/hour exposure. A
missing exposure field cannot be replaced by an unregistered full-year
assumption. Business/farm values are survey concepts, not asserted Schedule
C/F or partnership net profit.

### 4.3 Production information cutoff and status evolution

The micro-information cutoff is the frozen 2014 projection boundary:
observed reference-year facts through 2013 and only attributes already
present in the registered pre-mortality 2014 seed domain are admissible.
Official pre-2015 aggregate calibration targets are calibration evidence, not
person facts. No realized job, industry, occupation, government,
self-employment, incorporation, enrollment, or earnings answer with
reference year after 2013 may enter a 2014–2022 production component/status
path.

Longitudinal observed jobs match only under the literal
`job_spell_match_rule_id`: same role, verified job identifier where present,
and compatible interview/reference-year timing. Ambiguous or unmatched jobs
close the old spell and create a new stable component ID; row proximity never
matches a spell. `gap_imputed` source years and `boundary_2014` retain those
literal provenance states and never masquerade as direct questionnaire
observations.

For an incumbent, the last admissible wage/SE expected shares initialize two
stable synthetic aggregate IDs, `projected#wage` and
`projected#self_employment`, at the 2014 boundary. In every 2014–2022 year,
the selected candidate's registered mixed-allocation logit divides the frozen
nonnegative person-total proxy between those IDs; the two pre-measurement
gains sum exactly to the nonnegative proxy. A negative projected person total
is preserved as a non-SE source anomaly and produces zero gain unless a
separate admissible source identifies it as an SE loss. V1 models no
projected employer count or job birth/death and makes no job-level projection
claim.

The candidate's calendar-year/component functions in §5.3 then produce the
annual deterministic coverage-probability path. A scheduled entrant
initializes the same two synthetic IDs at first modeled presence using only
its frozen proxy total and attributes already admissible to the projection.
Later realized answers are forbidden even if they exist in a staged file.
The two synthetic component gains plus published measurement deltas reconcile
to the frozen person total each year.

The status law advances annually, including odd years. The underlying frozen
earnings projection's odd-year amount carry is not altered or claimed
resolved. `odd_year_earnings_carry` therefore remains in §9.2.

## 5. Classification, measurement, and uncertainty

### 5.1 Option A: component/status classification

Direct statutory classification occurs only when §4.1's required facts are
present. Every other in-domain record receives either:

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

### 5.2 Option B: measurement layer

Option B runs after source-component adjudication and before status amounts
are aggregated. It represents adjusted gains and admissible SE-loss
magnitudes as separate nonnegative channels. Gain mappings are
component-specific, extensive-margin preserving, and monotonically
nondecreasing in a positive source amount within a registered stratum. A loss
mapping may operate only on a source component that the historical legal
registry admits to SE netting. Exact zeros remain a separately modeled mass.
Stable-person-ID tie-breaking, never row order, governs ranks.

The layer may:

- recover separately reported business/farm labor components exactly once;
- allocate a mixed source component across employee and SE concepts;
- apply a registered deterministic conditional-mean or monotone rank mapping;
  and
- draw a residual only where the selected candidate explicitly declares a
  distributional estimand.

It may not turn an aggregate target into observed individual coverage, erase
the raw proxy, fit a national level, or force an unconditional sign.
Assignment flags describe source imputation, not administrative agreement.

A mixed component is split before coverage classification into stable derived
atomic IDs `<source_component_id>#wage` and
`<source_component_id>#self_employment`. Their gain and loss channels
reconcile exactly to the parent source under the registered mixed-allocation
law. The four-class status draw then operates on each homogeneous derived
component. It may not assign an entire mixed parent to one type. Uncertainty
in the split uses a separately named `mixed_allocation_share` variate; it is
not smuggled into the coverage-status CDF.

### 5.3 Frozen selectable candidate set

Aggregate component moments cannot identify worker-level industry,
occupation, government, or persistence effects. V1 therefore uses no fitted
risk-stratum coefficient and no fitted person-specific transition parameter.
Observed self/other, incorporation, and direct component labels adjudicate
remuneration type under §4; they are not coverage labels. Direct legal rules
remain fixed and are never estimated.

The five calibration eras are exactly `1968-1975`, `1976-1978`,
`1979-1993`, `1994-2002`, and `2003-2014`. Within records not directly
classified by law, a candidate may estimate only:

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
| `ab_era_constant_expected_v1` | One constant parameter of each permitted kind in each of the five calibration eras. | Carry every fitted 2003–2014 parameter at its 2014 value. |
| `ab_era_linear_expected_v1` | Intercept and calendar-year slope of each permitted kind within each multi-year era; the 1976–1978 slope is permitted, and no singleton era exists. | Extrapolate the registered 2003–2014 linear predictor annually through 2022. Coverage uses the logistic link; positive multipliers use the exponential link constrained to `[0.25, 4.0]`. |
| `ab_pooled_seam_expected_v1` | One component-specific global calendar-year slope plus registered intercept shifts at 1976, 1979, 1994, and 2003 for each permitted kind. | Continue the global slope and last seam intercept annually through 2022, with the same links and multiplier bound. |

Every uncertain incumbent and scheduled entrant receives the selected
candidate's calendar-year/component probability; direct classifications
override it. This is the exact annual status-evolution rule. Draw realizations
are conditionally independent across years given that probability path; v1
does not pretend that aggregate targets identify latent legal-status
persistence.

The literal `candidate_specs.v1` objects expand only the parameter indices
implied above and freeze link functions, bounds, exact model-side target
formulas, float64 arithmetic, deterministic optimizer, starting vector,
maximum iterations, gradient and objective convergence tolerances, and
failure disposition. A candidate is eligible only if the train-cell Jacobian
with respect to its free parameters has full column rank, its registered
condition number is no greater than \(10^8\), and the optimum is unique under
the registered \(10^{-10}\) parameter-distance and objective-distance tests.
Regularization cannot substitute for identification. Failure of any test
makes the candidate ineligible and publishes its disposition; parameters or
optimizer settings may not be changed after fitting starts. Registered
profile-loss intervals for every free parameter publish as identification
diagnostics and are never described as administrative uncertainty intervals.

### 5.4 Deterministic-first draw law and nonlinear benefits

The canonical expected-value ledger is always emitted. Distributional
treatment is required for any nondegenerate historical coverage/status
uncertainty that can change top-35 membership or a candidate's explicitly
distributional measurement residual. The fixed correction draw grid is
`draw_index = 0..19`.

The namespace input is the exact ordered tuple

```text
(
  "covered_earnings.v1",
  correction_version,
  stable_person_id,
  calendar_year,
  role,
  source_job_id,
  source_component_id,
  derived_component_id,
  variate_name,
  correction_draw_index
)
```

encoded as canonical JSON UTF-8 bytes. The generator takes SHA-256 of those
bytes, interprets the first eight digest bytes as an unsigned big-endian
integer \(h\), and sets \(u=(h+0.5)/2^{64}\). Fixed CDF order is
`covered_wage`, `covered_self_employment`, `noncovered`, `unresolved`.
Additional residual variates use a registered final counter field and a
distinct literal namespace suffix. Process hash functions, mutable seeds,
row indices, wall clock, and global RNG are forbidden.

Correction draws consume no projection, mortality, claiming, marriage, or
other model RNG stream. Calibration and selection use analytic conditional
means and analytic worker probabilities only; no capped quantity or
finite-draw fraction is a fitting target. The same correction draw feeds both consumers. For
nonlinear career outcomes, each projection draw is crossed with all 20
correction draws; top-35 selection, AIME, PIA, and benefit outputs are
computed within each complete career draw before reduction. Computing
`PIA(expected career)` and calling it `expected PIA` is forbidden.

The evaluation reports finite-grid error honestly. For each registered
nonlinear downstream metric it compares the means from draw prefixes `0..9`
and `0..19`; absolute differences must be no greater than the operational
stability tolerance frozen in `draw_spec.v1`. This is a deterministic
resolution check, not a confidence interval. Failure blocks
`correction_model_eligible`; it cannot trigger draw shopping.

Canonical input sorting, fixed key order, fixed reduction order, canonical
finite JSON, and the hash generator above make byte-identical replay and
row-order invariance hard gates.

## 6. New immutable calibration-target vintage

### 6.1 Identity and source evidence

The new logical artifact is
`ssa_covered_earnings_calibration_targets.vintage2`, with schema
`ssa_covered_earnings_calibration_targets.v1`. Its eventual literal
versioned filename must include the exact covered-share source vintage
verified under §13; this design does not guess that publication identity.
The artifact identity binds the logical ID, schema, canonical artifact
SHA-256, extraction implementation commit, source-document manifest, and
every source-byte digest. A moving alias is forbidden.

The committed Supplement snapshot already establishes:

- Table 4.B2's exact title and wage/SE headers at
  [lines 964–995](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L964);
- its 1968 component row at
  [lines 1254–1266](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1254)
  and 2014 boundary row at
  [lines 1944–1956](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L1944);
- its component-count overlap and earnings definitions at
  [lines 2120–2129](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L2120);
- Table 4.B11's exact title and component headers at
  [lines 14838–14861](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L14838);
- its 1968 row at
  [lines 15118–15127](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15118)
  and 2014 row at
  [lines 15670–15679](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15670);
  and
- its overlap, taxable-component, and contribution-accounting notes at
  [lines 15803–15822](../../data/external/snapshots/ssa_level_anchors_vintage1/supplement2025_4b.html#L15803).

The 1968 SE taxable amount is published as 27,340 in 4.B2 and 27,300 in 4.B11;
rounded arithmetic siblings are not interchangeable or independent evidence.
The extraction records each literal cell and never averages them.

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

### 6.2 Frozen `calibration_target_specs`

The registry schema is `calibration_target_specs.v1`. It is a literal ordered
array, expanded cell by cell before fitting. Table 4.B2 and 4.B11 expand
exactly over calendar years 1968–2022 in ascending order. The covered-share
objects expand over the exact year array frozen when V-B7 is resolved; that
array must contain at least one train cell in each of `1968-1975`,
`1976-1978`, `1979-1993`, `1994-2002`, and `2003-2008`, and every available
2009–2014 cell. It is frozen before fitting and may not be thinned after
values are exposed. Every object contains exactly:

`target_id`, `dependency_group`, `source_artifact_vintage_id`,
`source_cell_ids`, `source_year`, `source_status`, `universe`,
`transformation`, `stored_unit`, `published_rounding_interval`,
`model_universe_id`, `model_weight_field`, `model_weight_source_sha256`,
`universe_concordance`, `role`, `loss`, `loss_weight`, `cell_tolerance`,
`family_tolerance`, `selection_eligible`, and `candidate_output_selector`.

`model_universe_id` resolves through a frozen selector containing exact age,
annual-presence, employee/SE/both-type, unique-worker, duplicate-worker,
zero-earner, and denominator rules. `model_weight_field` and its input hash
are literal. `universe_concordance` maps every official scope element to the
model selector and has no `approximately_same` branch. If the closed model
input cannot construct the registered denominator, target registration
aborts rather than making coverage absorb a frame mismatch.

Roles are exactly `train`, `validation`, or `held_out_diagnostic`.
The target families are frozen as follows:

| Target family | Exact official transformation and model selector | Loss | Role and selection law |
|---|---|---|---|
| `b2_wage_total_intensity` | 4.B2 `c5/c11`; model `sum(weight*covered_employee_wages_uncapped)/sum(weight*covered_wage_worker_probability_analytic)` in the exact registered worker universe | squared log ratio | 1968–2008 train; 2009–2014 validation; 2015–2022 held-out diagnostic; selection-eligible |
| `b2_se_total_intensity` | 4.B2 `c8/c12`; model `sum(weight*covered_se_net_earnings_pre_seca)/sum(weight*positive_covered_se_worker_probability_analytic)` in the exact registered worker universe | squared log ratio | same; selection-eligible |
| `b2_type_count_mix` | 4.B2 `c12/(c11+c12)`; model `sum(weight*positive_covered_se_worker_probability_analytic)/(sum(weight*covered_wage_worker_probability_analytic)+sum(weight*positive_covered_se_worker_probability_analytic))` | squared logit error | same; selection-eligible; a marginal type-count mix whose overlapping counts are never called unique workers |
| `ssa_precisely_universed_covered_share` | exact registered numerator/denominator; model uses the exact registered population selector, timing, duplicate-worker rule, and `modeled_covered_worker_probability_analytic` | squared logit error | available 1968–2008 cells train; every available 2009–2014 cell validation; 2015–2022 held-out diagnostic; selection-eligible |
| `b2_se_total_component_share` | 4.B2 `c8/(c5+c8)` and the algebraically identical model component ratio | no fitting loss | all 1968–2022 cells held-out diagnostic; dependency check only |
| `b2_wage_taxable_intensity` | 4.B2 `c13/c11`; model consolidated taxable wage intensity | no fitting loss | all 1968–2022 cells held-out diagnostic; preserved employer-cap mismatch |
| `b2_se_taxable_intensity` | 4.B2 `c17/c12`; model consolidated taxable SE intensity | no fitting loss | all 1968–2022 cells held-out diagnostic |
| `b2_wage_taxable_fraction` | 4.B2 `c13/c5`; model taxable/uncapped wage ratio | no fitting loss | all 1968–2022 cells held-out diagnostic; preserved employer-cap mismatch |
| `b2_se_taxable_fraction` | 4.B2 `c17/c8`; model taxable/uncapped SE ratio | no fitting loss | all 1968–2022 cells held-out diagnostic |
| `b11_component_reconciliation` | 4.B11 taxable-earnings total versus wage+SE rounded residual, separately contributions total versus wage+SE; worker total is never summed because component worker counts overlap | no fitting loss | all 1968–2022 cells held-out diagnostic |
| `b11_se_contribution_share` | 4.B11 SE OASDI contributions/(wage+SE OASDI contributions) | no fitting loss | all 1968–2022 cells held-out diagnostic; legal/accounting diagnostic only |

`dependency_group` is operational. The four selection-eligible families are
the only independent objective groups and each receives family weight 0.25;
annual cells within a group have equal weight. Every other family receives
zero fitting and selection weight and may only test an arithmetic,
reconciliation, legal-rate, or preserved-mismatch disclosure. Positive
intensity validation requires both RMS absolute log error no greater than
`log(1.05)` and every-cell absolute log error no greater than `log(1.10)`.
B2 type-count-mix validation requires RMS absolute share error no greater than
0.015 and every-cell absolute share error no greater than 0.03. Covered-share
validation requires RMS absolute share error no greater than 0.01 and every
cell no greater than 0.02. These are precommitted operational acceptance
thresholds, not sampling confidence intervals.

For positive \(m,o\), squared log-ratio loss is
\((\log m-\log o)^2\); a nonpositive operand aborts that candidate cell.
For \(m,o\) strictly between zero and one, squared logit error is
\((\operatorname{logit}m-\operatorname{logit}o)^2\); an endpoint or
out-of-domain value aborts. RMS is the square root of the equal-weighted
arithmetic mean of the registered cell errors, never a ratio of aggregate
means. B11 arithmetic siblings and dependent B2 transformations cannot rescue
or reject a candidate except when they reveal an extraction, legal-rate, or
reconciliation correctness failure. Published B2 averages and percentages
that duplicate registered transformations are diagnostics, never separately
weighted evidence.

“Stored value” means the full-precision deterministic transformation of the
literal published rounded cells, not recovery of unpublished precision. Every
source cell carries its exact published rounding interval, and diagnostics
publish whether a residual is distinguishable from that interval.

The expansion order is target-family order above, then ascending year. Source
cell IDs are the literal table/row/header-path identities; model selectors are
the literal formulas above with their exact support-universe selector supplied
by the registered input manifest. Object key insertion order is irrelevant;
arrays have the semantic order just declared and canonical JSON sorts object
keys. Changing a cell, source, year, role, dependency group, formula, loss, weight,
tolerance, selector, target order, or selection eligibility creates a new
registry version and requires fresh registration. Exact deep equality,
including array order, is mandatory.

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

## 7. Fitting and candidate-selection law

### 7.1 Isolation and objective

Only `train` cells estimate parameters. Only registered `validation` cells
select among the frozen candidates. A `held_out_diagnostic` value cannot
affect a parameter, optimizer, convergence decision, candidate eligibility,
candidate order, threshold, draw, tie-break, or publication decision.
Selection code is structurally unable to open either vintage-1 production
input or the held-out branch of the target API.

All model-side targets are weight-scale invariant: shares, per-component
intensities, or distributions. Multiplying every PSID weight by a positive
constant must leave every fitted target and loss byte-identical. A hidden
intercept, offset, target weight, or post-fit factor that matches a national
worker or payroll total is a forbidden level fit.

The registered training objective is the §6.2 equal-dependency-group-weighted
mean over the four independent selection-eligible families. There is no
regularization term and no candidate-specific target deletion. Full-rank and
unique-optimum tests in §5.3 are candidate eligibility conditions, not
penalties.

### 7.2 Exact selection sequence

Selection is the following lexicographic procedure:

1. run all frozen candidates and publish every success/failure disposition;
2. discard any candidate with a hard correctness violation, nonconvergence
   under its registered rule, missing output, or nonfinite parameter;
3. discard any candidate failing any validation cell or family tolerance in
   §6.2;
4. among eligible candidates, choose minimum equal-family-weighted validation
   loss;
5. if losses differ by at most \(10^{-12}\), choose minimum training loss;
6. if still tied within \(10^{-12}\), choose the earliest complexity order in
   §5.3; and
7. if still tied, choose lexicographically smallest candidate ID.

If no candidate is eligible, the complete evaluation result is `fail` and no
production correction or label certificate exists. Human adjudication,
candidate/seed shopping, threshold relaxation, target removal, or choosing a
visually preferable held-out path is forbidden. A changed candidate or rule
requires a new design/registry version and fresh registration.

### 7.3 PSID-side validation

PSID cross-validation holds out complete people/households and complete
questionnaire eras, never random person-wave rows. It evaluates parsing,
annualization, reconciliation, transition prediction, and observable
self-employment/sector fields. It is explicitly internal validation, not
administrative covered-earnings validation. Any literature quantity used as
a prior or fitting bound is training evidence and cannot reappear as
independent validation.

### 7.4 Option C sensitivity

The only Option-C ID is `aggregate_share_scale_sensitivity_v1`, labeled
`aggregate-scaled-labor-income-proxy`. For each year through 2014 it multiplies
`max(proxy_labor_income_raw, 0)` by the most recent registered pre-2015
`ssa_precisely_universed_covered_share` cell in the same §5.3 calibration era;
years before that era's first cell use its first cell. The 2014 scalar is
carried unchanged through 2022. This deterministic, deliberately crude rule
publishes aggregate movement only. It cannot enter careers, AIME, PIA, production revenue,
candidate selection, tolerance adjudication, the label certificate, or a
held-out claim. It is emitted solely to show how the production Option-A+B
model differs from a minimal scalar benchmark.

## 8. Normative gates and prohibited circularity

### 8.1 Hard correctness gates

Every gate below is conjunctive. One violating record is failure:

1. Every required 1968–2022 person-year has a unique complete ledger
   disposition, and the benefits and revenue key sets equal the registered
   union exactly.
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
8. The exact same underlying component bytes and correction draws feed
   benefits and revenue.
9. Raw proxy, raw fields, source wave/role/job, annualization, separate gain
   and loss channels, classification reasons, probabilities, measurement
   delta, and uncertainty provenance remain recoverable.
10. Two in-memory executions inside the sealed run produce byte-identical
    canonical ledger/model-result bytes, and the exact registered input
    permutations do likewise. Timestamps, runtime provenance, incident
    metadata, and sidecar bytes are outside this comparison.
11. No mortality, claiming, projection, marriage, or other RNG stream is
    consumed or changed.
12. No micro fact after §4.3's boundary enters an earlier projected year.
13. Career data-completeness and modeled OASDI coverage are separately named
    and computed.
14. The selected correction is invariant to global weight rescaling and fits
    no national payroll, worker, benefit, or contribution level.
15. The fitting/selection dependency trace contains no vintage-1 series,
    anchor report, post-2014 held-out target, benefit total, or Option-C
    output.
16. Every unresolved amount follows the registered missing-fact policy and
    reason code. No objective term or gate rewards moving unknown mass from
    `unresolved` to covered or noncovered. Weighted unresolved gain/loss
    shares, person-year shares, and status entropy publish overall and by era
    × role, but v1 imposes no evidence-free magnitude cutoff.
17. Zero/positive incidence, component identity, source status, and every
    required target/evaluation year are complete; a missing cell is never
    dropped from a reduction.
18. Nonlinear AIME/PIA results are computed within each complete correction
    career draw before reduction.
19. Each candidate passes the parameter-count, full-rank Jacobian,
    condition-number, and unique-optimum identification law in §5.3.
20. Every nonlinear downstream metric passes the registered 10-versus-20
    correction-draw stability tolerance.

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
- leaking realized 2017–2023 PSID job facts into the 2015–2022 projection;
- calling PSID-internal prediction administrative validation;
- double-weighting B2 and B11 rounded arithmetic siblings; or
- allowing Option C or a post-hoc scalar to rescue a failed production
  candidate.

## 9. Evidentiary labels and the label-retirement certificate

### 9.1 Exact certificate conditions

The §3.4 proxy label is retirement-eligible only when one complete report
proves all of the following:

1. the immutable legal, crosswalk, target, candidate, selection, draw, gate,
   and evaluation registries exact-match their registered bytes;
2. every 1968–2022 person-year used by benefits or revenue has full common
   ledger support;
3. every §8.1 hard gate and every registered calibration/validation tolerance
   passes;
4. the selected-model identity was locked before any held-out diagnostic was
   opened and no vintage-1 series was a fitting/selection input;
5. all raw inputs, deltas, status probabilities/draws, reasons, and component
   outputs are recoverable and reconcile;
6. byte-identical replay, row-order invariance, RNG isolation, information
   cutoff, and nonlinear-draw propagation pass;
7. the sealed §10 ceremony publishes a complete validator-passing correction
   evaluation artifact and integrity-bound sidecar;
8. a separately registered post-correction context report in §12 opens the 15
   vintage-1 series only after correction-model lock, publishes regardless,
   preserves all applicable legacy formulas and mismatch masks, and validates;
   and
9. the publication PR containing that context report and its positive
   certificate merges.

Before condition 9, a passing artifact is only
`label_retirement_eligible: true`; published labels do not change. If any
condition fails, `label_retirement_eligible` is false, the complete failure
publishes, and §11.2 governs any later revenue-only work.

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

The exact replacements are:

```text
positive_proxy_vs_workers_with_taxable_earnings
  -> modeled_coverage_vs_workers_with_taxable_earnings

positive_proxy_vs_trustees_covered_workers
  -> modeled_coverage_vs_trustees_covered_workers
```

The model side is the fixed-frame weighted sum of registered coverage
probabilities or draw indicators. The official side keeps its publication
universe. The legacy metric is retained only as
`positive_proxy_earner_count`; the corrected metric is a separate
`modeled_covered_worker_count`.

The successor adds
`modeled_covered_earnings_not_individual_administrative_truth` wherever an
official administrative earnings history or payroll is paired with the
modeled ledger. This is a new mismatch, not a renamed claim that the proxy
defect persists.

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
`aggregate-concept-calibrated-not-population-aligned` labels; a successor may
add `frame_composition_not_population_aligned`, but must identify it as new.
No claiming, accounting, consolidated-cap, odd-year, frame, or
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

### 10.1 Fixture-only rehearsal and frozen identities

Pre-registration rehearsal is fixture-only. It is structurally unable to
open production PSID inputs, the frozen projection inputs, the vintage-2
target values, the 15 vintage-1 series, or any production output path. Tests
use committed synthetic fixtures and rejection cases. Reading any production
value or computing any production statistic counts as a production execution
and is forbidden before fresh registration.

The primary output is the append-only
`runs/covered_earnings_correction_evaluation_v1.json`, with exact sidecar
`runs/covered_earnings_correction_evaluation_v1.json.env.json`. The primary
embeds the selected correction parameters, canonical model hash, complete
evaluation, and target-use trace. Both paths must be absent at launch. The
primary records SHA-256 of the exact sidecar bytes.

The configuration schema is
`covered_earnings_correction_evaluation_configuration.v1` and contains
exactly these ordered top-level keys:

1. `schema_version`;
2. `registration_reference`;
3. `design`;
4. `implementation_commit`;
5. `invocation`;
6. `production_input_manifest`;
7. `legal_rule_input`;
8. `psid_crosswalk_input`;
9. `calibration_target_input`;
10. `calibration_target_specs`;
11. `candidate_specs`;
12. `selection_spec`;
13. `draw_spec`;
14. `gate_specs`;
15. `evaluation_specs`;
16. `sensitivity_specs`; and
17. `output_paths`.

`design` pins this path, ratification commit, and revision. Every input object
pins literal path, immutable identity, schema, and SHA-256. The production
manifest lists every permitted input path/hash and no wildcard. Registry keys
are exact deep copies, not digests or reconstructions. `invocation` is the
complete ordered argument vector with no shell interpolation. `output_paths`
contains only the two exact paths above.

Canonical JSON bytes are UTF-8
`json.dumps(value, sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False) + "\n"`. The complete registered
configuration bytes must equal the canonical configuration echo.

### 10.2 Sealed phases and result contract

The isolated runner performs, in order:

1. preparation: open and hash only registered production inputs; exact-check
   schemas, identities, manifests, registries, and empty output paths;
2. fitting: expose only `train` target cells to candidate estimators;
3. selection: expose only `validation` cells and execute §7.2;
4. lock: serialize selected model parameters canonically and irrevocably
   record their SHA-256 before opening any held-out diagnostic;
5. evaluation: run every hard gate, replay/permutation test, complete
   registered diagnostic, and Option-C sensitivity; and
6. publication: atomically publish the primary then its integrity-bound
   sidecar, or publish an incident under §10.3.

The report has exactly these result blocks:
`input_validation`, `candidate_dispositions`, `target_results`,
`selected_model`, `hard_gate_results`, `replay_results`,
`support_results`, `distribution_results`, `downstream_results`,
`sensitivity_results`, `target_use_trace`, and
`label_retirement_eligibility`. Each registry and target array is complete
and in registered order. Missing, extra, duplicate, reordered, null,
nonfinite, wrong-unit, wrong-role, or wrong-year content aborts validation.
Gate outcomes are recomputed from result values; a self-reported pass flag is
not authority.

### 10.3 Incidents and fresh-registration law

Any preparation, invariant, compute, or publication failure writes the next
contiguous append-only
`runs/covered_earnings_correction_evaluation_incident_<n>.json`, where \(n\)
is canonical positive base 10 without a leading zero. The incident contains
exactly:

`schema_version`, `incident_index`, `timestamp_utc`, `phase`, `reason`,
`reason_detail`, `registration_reference`, `configuration_echo`, and
`artifact_path`.

The schema literal is
`covered_earnings_correction_evaluation_incident.v1`; phase is
`preparation | invariant | compute | publication`; the configuration echo
exactly equals registration. `artifact_path` is null except for a publication
failure after a partial primary exists, when it is the exact primary path.
No field outside the echo contains an estimate-bearing value. Existing
suffixes must be exactly `1..n-1`; no overwrite is possible. A partial primary
permanently consumes the v1 path.

### 10.4 Six pre-launch checks

The coordinator records:

1. ratified design and implementation commits, and proof no production
   execution occurred;
2. fresh registration reference and byte-exact configuration;
3. expected input paths, immutable IDs, and hashes compared to registration
   without opening production inputs;
4. absence of both output paths and the next contiguous incident index;
5. exact isolated invocation
   `python -I -B -X pycache_prefix=<fresh-empty-sentinel-directory>
   scripts/run_covered_earnings_correction_evaluation.py
   --registration <registered-configuration-path>`; and
6. acknowledgment of `publishes_regardless`, incident publication,
   `no_self_rescue`, and the law below.

### 10.5 Sole normative execution law

The correction evaluation has one registered run; `publishes_regardless`;
`no_self_rescue`; and at most one coordinator-adjudicated,
unchanged-configuration retry solely after a published incident whose phase
is `preparation` or `compute`, whose machine reason begins `external_`, and
before any estimate-bearing information was yielded. The incident publishes
before adjudication. A complete pass or fail, an invariant or publication
failure, any estimate exposure, a partial primary, a changed configuration
byte, a nonexternal failure, or a second failure of any kind requires fresh
registration and, where a path was consumed, a newly ratified output version.
An empirical gate failure is a result, never a retry-eligible incident. This
paragraph is the sole normative execution law document-wide; every other
ceremony description defers to it.

The no-retry sequence is fresh registration → one sealed run → complete
report pair or incident → publication regardless. The only retry branch is
eligible incident → incident publication → coordinator adjudication → one
unchanged retry → complete report pair or second incident → publication
regardless.

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
ordered labels `frame-relative`, `pre-alignment`, and `labor-income-proxy`.
The experimental result cannot enter careers, splice into a historical path,
issue a label-retirement certificate, or resolve entry 11.

### 11.3 Unchanged limitations

The consolidated-person cap versus employer reporting; odd-year carry;
gross-versus-net accounting and contribution timing; the fixed frame and
weights; opening-stock imputation; mechanical claiming; annual
presence/December stock; benefit amount/outlay; OASI/OASDI program scope; and
absence of an OASI/DI allocation remain. Benefit-only deemed credits remain
zero and explicitly unsupported in v1.

### 11.4 Deviations

None. “Out-of-sample” for the post-correction context event is qualified in
§12 as structurally out of the fitting sample because the 2015–2022 cells
have already been viewed. This is an honesty clarification, not a deviation
from the coordinator ruling.

## 12. What this unlocks

First, the selected correction is locked and a separately registered
`covered_earnings_context_report.v1` becomes the structurally
out-of-fitting-sample evidence event. It carries unchanged applicable legacy
comparison formulas, new corrected metric selectors, exact target-use masks,
the §9 mismatch disposition, complete before/after diagnostics, and
`publishes_regardless`. It never describes the already-viewed 2015–2022
anchors as unseen.

Second, W1 can build the national population bridge on corrected earnings
rather than on the labor-income proxy: roster, weights, and levels remain
W1's authority, not this correction's.

The orthogonal first-estimates successors remain in order after those steps:
spouse/survivor entitlement adaptation, behavioral claiming, and the
`FORWARD` production object. Stronger covered-earnings evidence requires a
later sealed official vintage registered before exposure or a separately
authorized administrative micro link.

## 13. Complete VERIFY disposition

Every scoping `VERIFY` item appears exactly once below. A registration-time
verification supplies either exact registered bytes/rules or a failure; it
never supplies a default.

### 13.1 Bucket A — resolved in design from committed bytes

| ID | VERIFY item | Resolution |
|---|---|---|
| V-A1 | Whether Table 4.B2/4.B11 component cells will be newly extracted and whether pre-2015 cells exist | **Resolved yes.** §6.1 cites exact committed headers, 1968 rows, 2014 rows, overlap/definition notes, and contribution caveat. The new vintage-2 extraction is mandatory. The covered-share half of the same scoping sentence is V-B7, not a second item. |

### 13.2 Bucket B — registration-time fail-closed verification

| ID | VERIFY item | Required disposition and failure consequence |
|---|---|---|
| V-B1 | Exact Section 218 and mandatory state/local coverage law and effective dates | Pin controlling primary bytes and effective-year rules in §4.1. Missing/conflicting years abort legal-registry ratification and full correction. |
| V-B2 | Exact clergy, minister, church-employee, religious-order, and exemption rules | Pin primary bytes and required facts. Failure forbids direct clergy exclusion and blocks any candidate relying on it. |
| V-B3 | Exact historical residual-exclusion rules for domestic/agricultural thresholds, election, family/casual, foreign-government/international-organization, nonresident-alien, and similar service | Pin effective-year rules. An unverified class is modeled/unresolved and cannot be directly classified; a load-bearing gap aborts full certification. |
| V-B4 | Historical pre-1990 SECA eligible-concept, net-earnings-factor, threshold, and coordination crosswalk | Pin every effective-year transform. A year gap aborts registration. |
| V-B5 | Exact common 1968–1974 and spouse/secondary-job industry/occupation classifier availability and meaning | Verify each raw field/label/code in the expanded crosswalk. Structural absence is recorded explicitly; a false common mapping aborts. |
| V-B6 | Exact pre-modern spouse and secondary-job self/other and incorporation support | Verify every role/job/year source. Missing support cannot be extrapolated and follows the modeled/unresolved rule. |
| V-B7 | SSA covered-share publication, table, vintage, annual definition, numerator, denominator, duplicate-worker treatment, timing, and universe | Pin exact same-universe source bytes under §6.1. Any mismatch, including annual-unique versus point-in-time, aborts target-artifact registration; no approximate 94-percent input exists. |
| V-B8 | Earlier enrollment-field coverage and a stable cross-wave mapping | Verify the literal fields and meanings. Structural absence is explicit; enrollment still cannot establish the student/employer nexus. |

The legal registry also fail-closes CSRS/FERS/CSRS Offset,
Railroad-covered employer/service, and the student/employer nexus even though
those source-fact absences were not separately tagged `VERIFY` in the survey.

### 13.3 Bucket C — explicitly outside v1

| ID | VERIFY item | Consequence |
|---|---|---|
| V-C1 | Roughly one-quarter of state/local workers or about six million are noncovered | No v1 magnitude prior, bound, tolerance, attribution, or sign claim uses it. |
| V-C2 | Railroad employment is well below one percent nationally | No v1 aggregate bound, candidate weight, or “too small” gate uses it. |
| V-C3 | Student-worker payroll/worker magnitude | No magnitude prior is used; enrollment cannot determine exclusion. |
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
| Production cutoff, entrants, and odd years | §4.3 admits observed reference-year facts through 2013 plus only frozen seed attributes; annual modeled transitions govern incumbents/entrants; odd-year earnings carry remains. |
| Probabilities, imputations, draws, nonlinear AIME/PIA | §§5.1 and 5.4 make expected mappings primary, require 20 keyed correction draws where nonlinear distribution matters, and compute benefits within career draw. |
| Target artifact, years, loss, partition, viewed cells | §6 creates immutable vintage 2; 1968–2008 trains, 2009–2014 validates, 2015–2022 diagnoses; losses/tolerances are literal; none of the 15 series fits; viewed-cell honesty is explicit. |
| B2/B11 and covered-share extraction | §6 and V-A1 require B2/B11 extraction; V-B7 requires exact covered-share universe or aborts. |
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
  byte replay, row-order invariance, and RNG isolation are executable.
- [ ] Aggregate motivation states both high per-worker ratios and
  approximately 1.01→0.80 aggregate payroll, with no unconditional sign.
- [ ] Scope exclusions and the revenue-only degradation are exact and cannot
  retire report-wide proxy labels.
- [ ] The label certificate enumerates full conditions plus exact retired,
  replaced, new, and preserved mismatch literals.
- [ ] §10.5 is the sole normative evaluation execution law and enforces
  one-shot, publishes-regardless, incidents, and fresh registration.
- [ ] The post-correction context event and W1-on-corrected-earnings successor
  are named without claiming already-viewed evidence is unseen.
- [ ] `Deviations` is accurate.

Until every box is ratified and the later publication sequence completes,
the §3.4 labor-income proxy label remains in force.
