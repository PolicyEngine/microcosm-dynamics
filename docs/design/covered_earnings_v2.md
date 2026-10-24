# Covered earnings v2: a lean successor to the correction campaign

- **Status:** design note CE0, revision 2, 24 October 2026. Revision 1 applies review round 1's six findings and revision 2 applies round 2's three (§10). It authorizes no registration, real-data run or label change. Nothing in it has run.
- **Authority:** Max approved Tier 1 of the income-and-resources design on 2026-10-23 (decision d1923). His answer to that design's decision 1 was to retire the covered-earnings correction campaign for CE v2, with the same estimands; his answer to decision 8 was that CE's projected-coverage sensitivity treats all projected wages as covered.
- **Parent design:** `docs/design/income_and_resources.md` at commit `ee62046fbb985a63f8f2a67c4b329b2e4dc0a465` (PR #559), §3.1 and the CE rows of §4.1. This note is its milestone CE0. Prices and dependencies are the parent's and are not restated as new estimates.
- **Supersedes, as a campaign:** `docs/design/covered_earnings_correction.md` (56,304 lines: a base design in §§1–14 and amendments in §§15–33). That document stays in the repository, byte for byte, as the record of the campaign and the source of the estimands below; a test pins its bytes at HEAD (`tests/estimates/test_covered_earnings_correction_registry.py`, lines 1392–1403), so this note adds no pointer to it. Its ratification, registration and amendment protocols no longer govern any work.

Every citation of the old design is to `docs/design/covered_earnings_correction.md` at master `4fc2b9f4`, read in this run.

## 1. What carries over and what does not

### 1.1 Kept

| Element | Where in the old design | How CE v2 uses it |
|---|---|---|
| The four statuses `covered_wage`, `covered_self_employment`, `noncovered`, `unresolved` | §1 (lines 30–34), §3.1 | Unchanged. Every component-year carries a probability for each, and they sum to one exactly (§4). |
| The person-year estimand registry | §3.1, the table "The frozen person-year output registry" (lines 211–240) | All 26 estimand IDs are kept with their definitions (§2.5). One channel is added, RET-countable earnings, which the earnings test needs and the old registry did not carry, with its refusal diagnostics (§2.3). |
| Unresolved earnings are never silently counted as covered | §3.1, `unresolved_earnings` (line 222) | Unchanged, and strengthened: a record with no direct resolution and no sourced prior stays `unresolved` (§2.3). |
| Statutory ordering | §3.2 (lines 286–321) | Kept: self-employment losses offset only self-employment gains and never wages; the self-employment threshold applies to the aggregated self-employment concept before the cap; wages consume the taxable maximum first and self-employment only the remainder; one consolidated maximum per person-year; an unverified incorporation or remuneration distinction never defaults to self-employment. CE v2 states the statutory units of aggregation explicitly: church employee income is computed apart from other net earnings from self-employment, with its own threshold (§2.3; 42 U.S.C. 411(i)). |
| Nonlinear fields from the joint state, never from expected components | §3.1 (lines 242–252) and §3.2 (lines 303–307) | Unchanged: capped and creditable fields, and worker probabilities, are computed inside each joint coverage outcome and then weighted. Benefits use keyed draws. |
| One ledger for benefits and revenue | §3.3 (lines 323–346) | Unchanged in substance: one ledger is materialized; consumers may apply rates and caps but may not reclassify, resample or re-correct it. |
| Fitting nothing to official totals | Amendment 2, §16.1 (lines 9210–9216) and §16.7.1 (lines 13753–13775) | Unchanged in principle: no official target, fitted coefficient, optimizer, candidate comparison or model-choice loss. CE v2 adds sourced priors that are not the gate's truth (§2.3, §6). |
| The frame-relative label | §1 (lines 36–44); §16.7.1 | Kept as the first token of the label array (§2.5). |
| Existing code | — | `src/populace_dynamics/data/psid_covered_earnings_registry.py` (the frozen PSID reference-year law), `src/populace_dynamics/data/historical_coverage_rule_validation.py` (the fact vocabulary, `FIELD_PURPOSES`, lines 66–102), and `src/populace_dynamics/data/psid_job_context.py` (raw BC/DE job-context tokens, never trimmed or interpreted, lines 1–8) are reused. `src/populace_dynamics/covered_wage_history.py` stays an opt-in sidecar that records declarations and "never infers wages from labor income" (lines 1–6); CE5's table is a separate artifact. |

### 1.2 Dropped

- **The exact-encoding ceremony.** Reduced dyadic probability objects, rational-microdollar amounts and their canonical JSON laws (§3.1, lines 143–204) give way to two plain integer encodings (§4).
- **The nested ratification oracles and sealed ceremony** of §§8.1, 9 and 10 (the G-gate catalog, the label-retirement certificate, sealed phases and opaque retry receipts). CE-G is admitted the way every Track B gate is: a record IR0 freezes, a registration on issue #42, a truth-only floor built after registration, a bite check, then one scored run (parent §7.3).
- **The calibrated path** (§§6–7). Amendment 1 had already removed its covered-share target because no SSA publication supplies one (§15.2, lines 8177–8222).
- **Amendments 3–19** (source identity, grammar and partition laws, consumer-boundary guards). Their substance survives where CE v2 needs it, in CE2's per-wave label verification and CE5's schema tests.
- **Amendment 2's uninformative default.** On the fitting-free path, a modelable employee record without a direct resolution took the status vector [½, 0, ½, 0], and a self-employment record [0, ½, ½, 0] (§16.3, lines 11054–11082). CE v2 does not use a uniform default. A record is resolved by a rule, assigned a sourced prior, or left `unresolved` (§2.3).
- **The 2014 projection boundary and its fitted calendar functions** (§4.3, lines 1323–1380). Projected years follow §3 instead.

## 2. Components

### 2.1 CE1: the coverage-rule registry

A versioned table of coverage rules, each row with:

- an identifier, its citation (statute, regulation or POMS section) and its effective start and end dates;
- its family: the exclusions of 42 U.S.C. 410(a), the self-employment rules of 42 U.S.C. 411, and the thresholds;
- the facts that trigger it, drawn from the existing fact vocabulary (`historical_coverage_rule_validation.py`, `FIELD_PURPOSES`, lines 66–102: government level, Section 218 group and position, retirement-system participation, federal service and retirement system, railroad service, ministerial and religious-order service and exemptions, domestic, agricultural, election, family and casual service, student service with an employer-school nexus, and others);
- its consequence: covered, noncovered, or covered above a threshold;
- its **identification class** for the PSID, set by CE2's evidence: `identified` (the data's facts decide it), `prior` (a registered external source gives its probability, §2.3), or `unidentified` (neither);
- worked examples from SSA's published guidance, each a conformance test.

It starts from the rules in the parent's §2.5 and adds each rule's history before its current text. Among the research items CE1 settles from primary sources before use: the cash-pay thresholds for domestic, agricultural and election work by year; the dates federal, nonprofit and state and local coverage changed; and the definition of net earnings from self-employment over time, including how the $400 threshold of 42 U.S.C. 411(b)(2) and exempt ministers' earnings enter, and from which year church employee income has been computed separately under 42 U.S.C. 411(i). A year with no rule for a family is refused.

### 2.2 CE2: the PSID job-context and earnings-component crosswalk

- **Job context, 1968–2023.** It extends `psid_job_context.py`, which reads interview waves 2003–2023 (`psid_job_context_registry.py`), to every earlier wave, and adjudicates the value codes of the government-employer, industry, occupation, self-employment, incorporation and state items in every wave from the codebooks and setup files, with the repository's label-verification discipline. Raw tokens are kept; adjudicated codes sit beside them.
- **Earnings components.** For each wave and role, it lists the labor-income components the questionnaire records (for example wages and salaries, bonuses, overtime, tips and commissions, the labor part of business and farm income, professional practice) and assigns each a remuneration type: wage, self-employment, mixed or unknown. Where a wave reports a `mixed` component's wage and self-employment parts separately, CE2 records that; otherwise the parts are not established. For the earnings test, a `mixed` or `unknown` component whose parts are not established blocks the RET channel (§2.3).
- **Reference years.** Every component is placed in its income year by the frozen reference-year law in `psid_covered_earnings_registry.py`. Income years the biennial questionnaire does not observe keep a `structural_gap` provenance and inherit their status from the adjacent observed years by a registered rule; they never become direct observations.
- **What it reads.** Codebooks, setup files and questionnaires only. Its tests run on invented files. It computes no statistic from PSID microdata.

The covered-earnings campaign's sweep found 46 of 818 official prompts that broke a single-field rule (#403), so CE2 is priced at the upper end of its range in the parent.

### 2.3 CE3: the classifier

The classifier is a pure function from a component-year's facts (remuneration type, amount, year, state, government level, industry, occupation, self-employment and incorporation status, age, and, where a wave records them, place of work and armed-forces service) to its four status probabilities, with reason codes. It applies, in order:

1. **Direct rules.** A CE1 rule whose trigger facts the record identifies decides the status, one-hot. Private-sector employment is covered unless an exclusion applies (42 U.S.C. 410(a)), so a private-sector wage record with every applicable exclusion resolved is `covered_wage`.
2. **Component thresholds.** CE1 records, for each threshold, whether it applies to one component's remuneration or to an aggregate over a person-year. Where the facts identify a category with a component-level threshold, the year's threshold decides the component's status. Aggregate thresholds are not applied here. Among them are the self-employment thresholds of 42 U.S.C. 411(b)(2) and 411(i)(2), which apply to a taxable year's net earnings in each statutory unit; they are applied inside each joint outcome (statutory order, below). For a self-employment component, this step classifies service coverage only.
3. **Sourced priors.** Where coverage turns on facts the data do not record, chiefly state and local government workers, whose coverage depends on a Section 218 agreement and on membership in a public retirement system, the record takes a probability of noncoverage by state, government level, occupation group and era from a prior source registered at IR0: the Census Annual Survey of Public Pensions, SSA's Section 218 references and, if D5 admits it in this role, the SIPP Synthetic Beta's noncovered earnings. The Synthetic Beta's codebook places its earnings records' government-employment and self-employment indicators on the Gold Standard File only, so in this role it can inform cells by state and era but not by government level. A cell with no prior source leaves the record `unresolved`.
4. **Everything else** to which an `unidentified` exclusion could apply stays `unresolved`.

**One question this note does not settle** (§8, question 1): some exclusions can almost never be identified in a household survey and are rare, such as a child under 18 working for a parent (42 U.S.C. 410(a)(3)). Read strictly, step 4 leaves every young worker's wages `unresolved`. The alternative is a `negligible` class: an exclusion whose prevalence a cited source bounds below a registered threshold is treated as not applying, with a reason code on every affected record and the bounded mass reported. That is a methodology choice, and the review round and Max decide it.

**Statutory order.** Within each joint coverage outcome of a person-year, CE3 computes self-employment in statutory units, each aggregated only with what the law lets it absorb. CE1 records the units and, for each year, each unit's eligible concept, net-earnings factor and threshold. The captured 42 U.S.C. 411(i) fixes two units:

- **Church employee income**, the gross income for services described in 42 U.S.C. 410(a)(8)(B) and not in 410(a)(8)(A) (411(i)(4)). It is not reduced by any deduction, and neither it nor its deductions enter other net earnings from self-employment (411(i)(1)). So no loss enters this unit. Paragraph (1) does not reach the deduction allowable under 411(a)(11), which is determined after it (411(i)(3)). The threshold of 411(b)(2) applies to this unit separately, with $100 in place of $400 (411(i)(2)). A wage component that a CE1 rule identifies as church employee income takes the status `covered_self_employment` and enters this unit; its remuneration type stays the one CE2 recorded. Whether an employer is an electing church is a fact CE2 looks for; where no wave records it, the rule is `unidentified` and step 4 applies.
- **Other net earnings from self-employment.** The outcome's other covered self-employment gains and the losses admissible to this unit are aggregated, and the year's rules and the $400 threshold (411(b)(2)) apply to the aggregate.

CE1 adds any further unit a year's law requires. Each unit's eligible base is zero if the unit fails its threshold. The units' eligible bases are then summed into the person-year's self-employment base (the old registry's `covered_seca_base_uncapped`, line 219), and §3.2's equations of the old design compute taxable wages, taxable self-employment and taxable payroll, with wages consuming the maximum first. Two $300 components of other net earnings in one outcome therefore clear the threshold together, and $200 of church employee income with no other self-employment clears the $100 threshold on its own. Components that share one statutory coverage fact (one job, one year) share one coverage-state group and co-move; distinct groups are independent, a declared assumption (old design §3.1, lines 254–284). Expected values are exact probability-weighted sums over joint outcomes, computed by a dynamic program that a fixture test checks against brute-force enumeration.

**RET-countable earnings.** The earnings test has its own earnings concept. An individual's earnings for a taxable year are the sum of wages for services rendered in the year and net earnings from self-employment, minus any net loss from self-employment (42 U.S.C. 403(f)(5)(A)). Net earnings from self-employment are determined as 42 U.S.C. 411 provides, except that paragraphs (1), (4) and (5) of 411(c) do not apply (403(f)(5)(B)(i)); so a minister's exemption does not remove earnings from the test. Wages are computed without the remuneration limits of 42 U.S.C. 409(a)(1), (6)(B), (6)(C), (7)(B) and (8). Service that is not employment under 42 U.S.C. 410 is deemed employment if two conditions hold. First, it was performed in the United States by the individual as an employee, or outside it in the active military or naval service of the United States. Second, its remuneration is not included in net earnings or net loss from self-employment. Payments on account of retirement are not wages (403(f)(5)(C)(i) and (ii); parent §2.5). The consequences for CE v2:

- A covered wage component counts toward the test. So does a wage component that is noncovered only because of one of the 409(a) limits above; CE1 reads those paragraphs and records which component thresholds they are.
- A noncovered or `unresolved` wage component counts only when its facts establish both conditions of the deeming rule. CE2 records, by wave, which of the needed facts the questionnaire carries: place of work, armed-forces service, and whether the remuneration entered self-employment.
- No payment on account of retirement, and no pension payment, counts.
- A net self-employment loss reduces RET-countable earnings, although it never offsets wages in the taxable-payroll ordering above.
- The $400 and $100 thresholds define self-employment income (42 U.S.C. 411(b)(2) and (i)(2)), a different concept from the net earnings the test uses, so they do not apply here.

**When the channel is produced.** Every component of a person-year must have an established RET contribution: either an amount that counts, or a reasoned exclusion. A reasoned exclusion is a component whose facts establish that it does not count, such as a payment on account of retirement, or noncovered service whose facts establish that a condition of the deeming rule fails. It carries its own reason code and does not block the channel. CE3 produces `ret_countable_earnings` only when every component's contribution is established. Otherwise the field is absent, never zero, and each component whose contribution is not established carries one refusal entry (component ID, reason code, amount):

- `RET_WAGE_ELIGIBILITY_UNRESOLVED`: a wage component whose deeming-rule facts are not established;
- `RET_REMUNERATION_TYPE_UNRESOLVED`: a `mixed` or `unknown` component whose wage and self-employment parts CE2 has not established. Its coverage status does not settle its RET contribution: an `unknown` labor component for work abroad could be foreign employee service outside the deeming rule, which does not count, or own-account business whose net earnings do;
- `RET_SE_FACTS_UNRESOLVED`: a self-employment component whose net earnings or net loss under 403(f)(5)(B) the facts do not determine, for example where 411(c)(4) or (5) would matter.

The refused amounts sum to `ret_unresolved_amount`; the first reason's share of it is `ret_eligibility_unresolved_wages`. A refused component is neither counted nor dropped.

CE1 reads the rest of 403(f)(5), including subparagraph (D)'s exclusions from gross income, and records how church employee income enters the test's net earnings, before CE3 encodes the channel.

### 2.4 CE4: the gate CE-G

The parent design (§3.1, part 4; §7.3) fixes the gate's structure; IR0 freezes its cells, tolerances, pass conjunction and bite rule before it registers.

- **Truth.** EPUF by birth cohort, sex and age band for 1968–2006: the share of person-years with positive covered earnings, capped covered-earnings quantiles, and years without covered earnings. If IR0 powers them, two more cell families: covered workers and taxable earnings by state against the Annual Statistical Supplement's Table 4.B10, and the SIPP Synthetic Beta's covered and noncovered earnings once Census staff validate the results on the Gold Standard File.
- **Order.** Registration on #42 pins a commit; then the truth-only floor; then the all-covered proxy, scored against the floor before any CE v2 output. If the proxy passes the registered bite-check conjunction, the gate stops as `WEAK_POWER_OR_VACUITY`.
- **Exposure already on file.** `gate_epuf`'s committed floors and bridges for 1998–2004 (`runs/epuf_gate_floors_v1.json`) and `gate_epuf_fill`'s published all-covered reference arm (parent §7.2). IR0 records both.

### 2.5 CE5: the person-year handoff table

One versioned table, one row per person, role and income year from 1968, with:

- **the old registry's 26 estimands, by their IDs and definitions** (old design §3.1, lines 211–240), as the table below gives them. Each field is an exact expectation over the person-year's joint coverage outcomes, except the draw fields.
- **Availability.** A field the old design tied to a published table's membership rule (Table 4.B2's `c11` and `c12`, Table 4.B11's worker counts, V-B7's covered-share denominator) is produced only where CE1 has verified that definition from the table's source bytes. Otherwise it is absent with the reason `TABLE_DEFINITION_UNVERIFIED`, not approximated.

| Estimand ID | Definition in CE v2 |
|---|---|
| `covered_employee_wages_uncapped` | Sum of nonnegative amounts classified as OASDI-covered employee wages before the person-level maximum. |
| `covered_se_gains_pre_loss` | Nonnegative sum of amounts classified as covered self-employment gains before statutory self-employment aggregation. |
| `covered_se_loss_magnitude` | Nonnegative magnitude of losses classified as covered self-employment and admissible to the same statutory aggregation unit. |
| `covered_se_net_earnings_pre_seca` | Signed intermediate `covered_se_gains_pre_loss − covered_se_loss_magnitude`. It never offsets wages and is not a final taxable component. |
| `covered_seca_base_uncapped` | Nonnegative sum, over the statutory units of §2.3, of each unit's base after the year's eligible-concept, net-earnings-factor and threshold rules, before wage-first cap coordination. |
| `noncovered_earnings` | Sum assigned noncovered, by a direct rule or a sourced prior. |
| `noncovered_se_loss_magnitude` | Separately reported nonnegative self-employment loss magnitude assigned noncovered. It never enters an OASDI base. |
| `unresolved_earnings` | Sum left outside a defensible covered or noncovered allocation. It is never silently counted as covered. |
| `unresolved_se_loss_magnitude` | Separately reported nonnegative self-employment loss magnitude left unresolved. |
| `oasdi_taxable_wages_person` | Covered employee wages after the person-year maximum. |
| `oasdi_taxable_se_person` | Self-employment base remaining after wages consume the person-year maximum. |
| `oasdi_person_taxable_payroll` | Sum of the two preceding fields: the revenue tax-base view. |
| `benefit_only_deemed_credits` | Literal zero, as in v1. No military or other deemed credit is invented without a separate source and legal registry. |
| `benefit_creditable_earnings` | Creditable wage plus self-employment amount under the same combined maximum. It equals `oasdi_person_taxable_payroll` while deemed credits are zero, but stays a separate typed view. |
| `covered_wage_worker_probability_analytic` | Probability of positive covered employee wages in the registered annual worker universe. |
| `b2_wage_worker_membership_probability_analytic` | Probability of meeting Table 4.B2's `c11` worker-membership rule. It equals the preceding field only if source bytes prove that equivalence. Available only as above. |
| `positive_covered_se_worker_probability_analytic` | Probability of a positive covered self-employment base in the registered annual worker universe. |
| `b2_se_worker_membership_probability_analytic` | Probability of meeting Table 4.B2's `c12` worker-membership rule. It equals the preceding field only if source bytes prove that equivalence. Available only as above. |
| `b11_wage_only_worker_probability_analytic` | Probability of membership in the wage-only cell implied by Table 4.B11's total, wage and self-employment worker-count definitions. Available only as above. |
| `b11_se_only_worker_probability_analytic` | Probability of membership in Table 4.B11's implied self-employment-only cell. Available only as above. |
| `b11_dual_type_worker_probability_analytic` | Probability of membership in both of Table 4.B11's wage and self-employment counts. Available only as above. |
| `b11_any_worker_probability_analytic` | Sum of the three preceding mutually exclusive probabilities: the analogue of Table 4.B11's unduplicated total-worker cell. Available only as above. |
| `registered_covered_share_denominator_indicator` | Deterministic zero-or-one membership in the model analogue of V-B7's verified covered-share denominator: a population-universe field, not an earnings or coverage outcome. Available only as above. It serves no calibration, since the calibrated path is dropped (§1.2). |
| `modeled_covered_worker_probability_analytic` | Probability, under the joint wage and self-employment status law, that person taxable payroll is positive. It is not `proxy > 0`, and in CE v2 it selects nothing. |
| `modeled_covered_worker_draw_indicator` | Zero-or-one indicator, within one realized draw, that taxable payroll is positive. |
| `modeled_covered_worker_draw_grid_fraction_20` | Arithmetic mean of the 20 draw indicators. It is a finite-grid approximation and is never called an exact probability. |

- **Worker probabilities** are sums of joint-outcome weights, never sums of marginals (old design lines 242–252).
- **Coverage status, per component.** Each row lists its components, each with:
  - its component ID, remuneration type and adjudicated amount;
  - its `coverage_state_group_id`;
  - its four status numerators (§4) and reason codes.
- **The unresolved share.** `unresolved_share` is the expected unresolved amount (`unresolved_earnings` plus `unresolved_se_loss_magnitude`) over the sum of the person-year's component amount magnitudes. It is absent when that sum is zero. Parent §8.1 requires it.
- **Coverage-state groups.** Group keys and memberships follow the old design's `coverage_state_dependence_specs.v1` (lines 254–273):
  - one person-year and one remuneration type per group;
  - components with one statutory coverage fact share a group;
  - members of a group carry identical probability vectors;
  - distinct groups are independent, a declared assumption;
  - a missing or inconsistent group aborts.
- **The realization contract.** Consumers that need realized coverage states, chiefly benefits, use one shared contract. Each nondegenerate group has one keyed uniform per draw, keyed by person, year, `coverage_state_group_id` and draw index through the counter-based hash of §4. That uniform realizes the group's categorical status. Benefits and revenue therefore see the same realization, and no consumer resamples. The draw count is 20, as in the registry; IR0 may register more.
- **the added channels** `ret_countable_earnings`, `ret_unresolved_amount` and `ret_eligibility_unresolved_wages`, with the per-component RET refusal entries and exclusion reason codes (§2.3);
- labor income as adjudicated, so every row reconciles: covered wages, covered self-employment, noncovered and unresolved amounts sum to it, with self-employment losses in their own channels as in the old design;
- provenance per row (`direct`, `structural_gap` or `projected`; source wave, role and component identifiers; the rule and prior versions applied);
- **the label array**, proposed: `["frame-relative", "modeled-covered-earnings", "prior-informed-uncalibrated"]`. The third token says that registered statutory rules and registered prior sources informed the model, and that no official covered-earnings total, gate truth, loss or optimizer did. Amendment 2's token, `deterministic-uncalibrated`, would misdescribe sourced priors (§8, question 3).

**Consumers, each through this table or the classifier's contract, never by reclassifying:**

- Track B's H, whose labor, covered and RET-countable channels stay separate (`src/populace_dynamics/track_b/README.md:125`). Until CE5 passes, H's covered channel keeps the label "labor-income proxy". Track B's insured-status rule reads covered earnings through H.
- B5, the earnings test, which reads `ret_countable_earnings` where it is produced. Where it is absent, B5 carries the refusal entries and `ret_unresolved_amount` into its own output for that person-year and never treats the absence as zero earnings.
- The lifetime-earnings groups (`src/populace_dynamics/estimates/lifetime_measures.py`), which use the capped covered channels.
- National payroll for Registration 18 and M7, which uses `oasdi_person_taxable_payroll`.
- The mortality, groups and financing lane's F2b (PR #558, `docs/design/mortality_groups_financing.md` §7.4, line 783), which needs "each earnings component classified as covered wages, covered self-employment, noncovered or unresolved" on the certified frame's start year. F2b calls the classifier on the frame's records through the same fact contract; facts the frame lacks give `unresolved` or a refusal, never a guess.

## 3. Projected years

The forward-earnings law has no job identity (parent §3.1), so a projected year cannot be reclassified from a new job.

- **Primary rule.** Each person's last observed coverage-state distribution, by remuneration type, carries forward to every projected year. The wage and self-employment split of a projected amount follows the forward-earnings law's own components where it has them, and the person's last observed shares otherwise, as the old design's synthetic `projected#wage` and `projected#self_employment` components did (§4.3, lines 1347–1355).
- **Registered sensitivity (Max, d1923):** all projected wages are covered. The sensitivity changes wages only. Projected self-employment keeps the primary rule's carried coverage distribution and keyed draws, so its gains, losses and uncapped base are the primary run's; §2.3's statutory rules (aggregation and thresholds within each statutory unit of each joint outcome) apply to it as in the primary run. Capped self-employment and taxable payroll are recomputed after the sensitivity's covered wages consume the maximum, so taxable self-employment can be lower than in the primary run. For example, with projected wages equal to the maximum, all noncovered under the primary rule, and a $10,000 covered self-employment base, taxable self-employment is $10,000 in the primary run and zero under the sensitivity.
- **No reset on a job change.** A reset conditioned on a job change waits for a separately sourced, priced and admitted job process, which no plan contains.
- **People with no observed status.** Under the primary rule, a person who enters the projection without an observed coverage state (an entrant of the open-population lane) carries `unresolved` wages; under the sensitivity, covered wages. Max's ruling on pre-entry covered earnings (d1925: censored, unknown to insured status, with zero as a labelled sensitivity) governs years before entry; this rule governs years after it.

## 4. Representation

- **Source money** in integer cents (64-bit integers). Every conservation identity over adjudicated amounts then holds exactly.
- **Component probabilities** as integer numerators over the fixed denominator 2^20. A sourced prior is rounded to that grid once, by a registered rule, when the prior table is built. The four numerators of every component sum to 2^20 exactly.
- **Joint probabilities.**
  - For a person-year with k nondegenerate coverage-state groups, a joint outcome's probability is the product of k numerators: an integer over 2^(20k).
  - It is held in an arbitrary-precision integer and never rounded back to the 2^20 grid.
  - The probabilities of a person-year's joint outcomes sum to one exactly.
- **Rule arithmetic.** Any rounding a statute or regulation prescribes, for example for the net-earnings factor, is part of that rule in CE1, and CE3 applies it to each outcome's amounts. Where no rounding is prescribed, an outcome's amounts are exact rationals.
- **Expected amounts and probabilities** are sums of each outcome's amount, or indicator, times its probability. They are held as exact rationals (an arbitrary-precision numerator and denominator) and are never rounded inside the computation.
- **Floating point** appears only at the declared reporting boundary, through one registered round-to-nearest-even binary64 conversion, as in the old design (§3.1, lines 205–209).
- **Draws** are keyed by person, year, coverage-state group and draw index through a counter-based hash, so results do not depend on row order.

## 5. Invariants

Each is stated in the PR that builds its component and tested with Hypothesis beside example tests (parent §9).

- Every component's four status numerators are nonnegative integers that sum to 2^20, and a person-year's joint-outcome probabilities are exact and sum to one.
- Conservation: covered wages, covered self-employment, noncovered and unresolved amounts sum to the component-year's adjudicated labor income, with self-employment losses reported in their own channels.
- Statutory order: taxable wages = min(wages, cap); taxable self-employment = min(self-employment base, max(0, cap − taxable wages)); no self-employment loss offsets wages; no capped amount exceeds the year's taxable maximum.
- Nothing is covered while an applicable exclusion is unresolved, unless a registered `negligible` class applies (§2.3) and the record carries its reason code.
- If every adjudicated component amount is zero, all monetary earnings channels are zero. Self-employment gains and losses stay in separate channels even when their signed sum is zero.
- Raising a component's noncoverage probability never raises its expected covered taxable amount.
- Where produced, RET-countable earnings equal the RET-eligible wage components (§2.3) plus net earnings from self-employment, minus any net self-employment loss, as 42 U.S.C. 403(f)(5) defines them. They never include a payment on account of retirement or a pension payment.
- `ret_countable_earnings` is produced if and only if every component's RET contribution is established, as a counted amount or a reasoned exclusion. When it is absent, each unestablished component has exactly one refusal entry, the entries' amounts sum to `ret_unresolved_amount`, and the `RET_WAGE_ELIGIBILITY_UNRESOLVED` entries sum to `ret_eligibility_unresolved_wages`. Adding a component with an unestablished contribution to a person-year never leaves the field produced, and B5 never reads an absent field as zero.
- Self-employment thresholds apply to each statutory unit's aggregate in a joint outcome, never to a single component: splitting one amount into several components of the same unit, in one coverage-state group, leaves every channel unchanged. Each unit's eligible base is zero if the unit fails its threshold, and `covered_seca_base_uncapped` is the sum of the units' eligible bases. Church employee income is never reduced by a loss from another unit.
- Expected nonlinear fields from the dynamic program equal brute-force enumeration on every registered dependence pattern.
- Determinism under keyed draws, and invariance to row order.
- Under the sensitivity, projected covered wages are at least those of the primary rule, person by person and in every keyed draw. Projected self-employment coverage distributions, draws and uncapped channels (`covered_se_gains_pre_loss`, `covered_se_loss_magnitude`, `covered_se_net_earnings_pre_seca` and `covered_seca_base_uncapped`) equal the primary rule's. Capped fields are recomputed by the statutory-order equation, so `oasdi_taxable_se_person` is at most the primary rule's and `oasdi_person_taxable_payroll` at least the primary rule's: taxable payroll equals min(covered wages + self-employment base, cap), which never falls as covered wages rise.

## 6. Information boundary

- **Roles of sources.** A source serves one role per cell: a classifier input, or gate truth, never both. EPUF and Table 4.B10 are gate truth and are never classifier inputs. The Synthetic Beta may be one or the other, by cells IR0 assigns. SSA's national covered-worker and taxable-earnings totals in the Supplement's section 4 (Tables 4.B1, 4.B2 and 4.B11) are reported beside CE v2's output, frame-relative, and are not classifier inputs. This settles a wording in the parent's §5, whose row for CE3 lists those tables as "classifier inputs; report-only context": under the parent's §3.1 ("it fits nothing to the SSA totals it is later checked against"), they are report-only context.
- **No real-PSID statistic** is computed before CE-G registers (parent §7.1). CE1–CE3 are built on invented data and sources; CE2 reads metadata only.
- **Publication** of CE4 and CE5 follows the parent's U2 sequencing rule (§7.2): no PSID statistic for the 1946–55 birth cohorts before U2's one-shot result is posted, unless the orchestrator first lists the outputs for U2's forecaster and checker in `RESTRICTED-FILES.md`.

## 7. Milestones

Unchanged from the parent's §4.1 and §4.3, and estimates there: CE1 (4–6 d), CE2 (6–9 d), CE3 (5–7 d), CE4 (6–9 d) and CE5 (2–3 d), with D4, D5 and IR0 on the data lane. This note is CE0 (2–4 d). CE1 and CE2 can start once this note passes its review round.

## 8. Open questions

1. **Unidentified rare exclusions.** Strict `unresolved`, or the `negligible` class with a cited prevalence bound and a reported mass (§2.3)? Recommended: the `negligible` class, limited to exclusions whose bound CE1 cites, because strict treatment would leave most young workers' wages unresolved for a reason the data can never cure. It changes how the parent's "covered only after every applicable exclusion is resolved" is applied, so it goes to Max through the coordinator.
2. **Ministers' exemptions.** The occupation item identifies clergy, but not who holds an exemption under 26 U.S.C. 1402(e). CE1 looks for a published source on the exemption's prevalence; without one, ministers' earnings stay `unresolved`.
3. **The label's third token.** `prior-informed-uncalibrated` is proposed (§2.5). It is a new evidentiary label, so the review round checks its definition.
4. **The old campaign's records.** The old design cannot carry a pointer here without breaking its byte pin (the status lines above). The parity ledger's covered-earnings row is the natural place for one; whether to add it now, and whether to close issue #403 with a pointer here, is the coordinator's call.

## 9. Files read for this note

At master `4fc2b9f4`: `docs/design/covered_earnings_correction.md` lines 1–346 (for revision 1, lines 205–284 again), 1323–1380, 8145–8222, 9193–9245, 10805–10918, 11054–11110 and 13751–13800, and its section headings; the module docstrings of `psid_covered_earnings_registry.py`, `covered_wage_history.py` and `psid_job_context.py`, and `historical_coverage_rule_validation.py` lines 1–30 and 60–105; `tests/estimates/test_covered_earnings_correction_registry.py` lines 1390–1415; `src/populace_dynamics/track_b/README.md` (searched for covered and RET-countable channels; line 125); and the parent design in full. From PR #558 at `2c19f5b6`: `docs/design/mortality_groups_financing.md`, lines found by a search for covered payroll and F2b, and lines 778–800 and 924–934. The captured texts of 42 U.S.C. 403 and 410 in `~/microcosm-launch-evidence/dynasim-parity-20260909/income-resources-20261021/sources/` (`MANIFEST.md` lists their hashes): 403(f)(5), including all of subparagraph (C), and 410(a)(3). For revision 1, round 1's review report and the SIPP Synthetic Beta codebook captured for D5 (its variable-availability entries). Decision records d1923 and d1925 in `~/chief-of-staff/state/decisions/decisions.jsonl`. For revision 2: round 2's review report; the captured text of 42 U.S.C. 411(b) and 411(i) in the same folder; and the parent's §2.5 (line 75) at master `f8ffc7d9`. No PSID, SIPP or EPUF data file was opened; no restricted file was opened.

## 10. Review history

| Round 1 finding | Revision 1 |
|---|---|
| 1. The self-employment threshold was applied per component, before aggregation | §2.3 step 2 now applies only component-level thresholds and classifies a self-employment component's service coverage only. The statutory-order paragraph applies the eligible-concept, net-earnings-factor and $400 rules to each joint outcome's aggregate. §5 adds the splitting invariant. |
| 2. RET's wage rule was broader than 42 U.S.C. 403(f)(5)(C) | §2.3 now states the 409(a) limits, the deeming rule's two conditions and the retirement-payment exclusions. It names the facts CE2 records, and refuses a person-year's RET channel with a reason code where eligibility is not established. §5 is qualified to match. |
| 3. CE5 did not carry the complete registry and coverage probabilities | §2.5 lists all 26 IDs with definitions and availability, and adds per-component status numerators, the unresolved share, coverage-state group keys and the shared realization contract. |
| 4. The encodings could not represent the exact outputs | §4 keeps source money in cents and component probabilities on the 2^20 grid. Joint probabilities are arbitrary-precision integers over 2^(20k), and expectations are exact rationals. Statutory rounding belongs to rules, and there is one conversion at the reporting boundary. |
| 5. "Zero labor income" did not imply zero channels | §5 now uses the reviewer's invariant, keeping gains and losses separate. |
| 6. The sensitivity changed self-employment coverage | §3: the sensitivity changes wages only. §5 added that projected self-employment channels are equal under both runs; round 2's finding 1 narrowed that to the uncapped channels. |
| Author's addition | §2.3 step 3 notes that the Synthetic Beta's government-employment indicator is on the Gold Standard File only. |

| Round 2 finding | Revision 2 |
|---|---|
| 1. The sensitivity invariant contradicted wage-first cap coordination | §3 and §5: coverage distributions, draws, gains, losses and uncapped bases are unchanged; capped self-employment and taxable payroll are recomputed after the sensitivity's wages consume the maximum. §5 states the resulting bounds, and §3 gives the reviewer's example. |
| 2. The aggregation and $400 threshold omitted the separate church-employee computation | §2.3 computes self-employment in statutory units: church employee income, unreduced by deductions, with the $100 threshold (42 U.S.C. 411(i)), and other net earnings with $400. The units' eligible bases are summed before cap coordination. §1.1, §2.1, step 2, the `covered_seca_base_uncapped` definition and §5 follow. |
| 3. RET availability did not cover unknown remuneration or other self-employment facts | §2.3 produces the RET channel only when every component's contribution is established, with three refusal reasons, per-component refusal entries and `ret_unresolved_amount`; established ineligibility is a reasoned exclusion. §2.2 records when a `mixed` component's parts are established. B5 propagates the refusal (§2.5), and §5 states the availability invariant. |
