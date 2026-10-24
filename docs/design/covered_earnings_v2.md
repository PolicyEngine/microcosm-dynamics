# Covered earnings v2: a lean successor to the correction campaign

- **Status:** design note CE0, revision 0, 24 October 2026, for one review round. It authorizes no registration, real-data run or label change. Nothing in it has run.
- **Authority:** Max approved Tier 1 of the income-and-resources design on 2026-10-23 (decision d1923). His answer to that design's decision 1 was to retire the covered-earnings correction campaign for CE v2, with the same estimands; his answer to decision 8 was that CE's projected-coverage sensitivity treats all projected wages as covered.
- **Parent design:** `docs/design/income_and_resources.md` at commit `ee62046fbb985a63f8f2a67c4b329b2e4dc0a465` (PR #559), §3.1 and the CE rows of §4.1. This note is its milestone CE0. Prices and dependencies are the parent's and are not restated as new estimates.
- **Supersedes, as a campaign:** `docs/design/covered_earnings_correction.md` (56,304 lines: a base design in §§1–14 and amendments in §§15–33). That document stays in the repository, byte for byte, as the record of the campaign and the source of the estimands below; a test pins its bytes at HEAD (`tests/estimates/test_covered_earnings_correction_registry.py`, lines 1392–1403), so this note adds no pointer to it. Its ratification, registration and amendment protocols no longer govern any work.

Every citation of the old design is to `docs/design/covered_earnings_correction.md` at master `4fc2b9f4`, read in this run.

## 1. What carries over and what does not

### 1.1 Kept

| Element | Where in the old design | How CE v2 uses it |
|---|---|---|
| The four statuses `covered_wage`, `covered_self_employment`, `noncovered`, `unresolved` | §1 (lines 30–34), §3.1 | Unchanged. Every component-year carries a probability for each, and they sum to one exactly (§4). |
| The person-year estimand registry | §3.1, the table "The frozen person-year output registry" (lines 211–240) | Every estimand ID is kept with its definition (§2.5). One channel is added, RET-countable earnings, which the earnings test needs and the old registry did not carry. |
| Unresolved earnings are never silently counted as covered | §3.1, `unresolved_earnings` (line 222) | Unchanged, and strengthened: a record with no direct resolution and no sourced prior stays `unresolved` (§2.3). |
| Statutory ordering | §3.2 (lines 286–321) | Unchanged: self-employment losses offset only self-employment gains and never wages; the self-employment threshold applies to the aggregated self-employment concept before the cap; wages consume the taxable maximum first and self-employment only the remainder; one consolidated maximum per person-year; an unverified incorporation or remuneration distinction never defaults to self-employment. |
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

It starts from the rules in the parent's §2.5 and adds each rule's history before its current text. Among the research items CE1 settles from primary sources before use: the cash-pay thresholds for domestic, agricultural and election work by year; the dates federal, nonprofit and state and local coverage changed; and the definition of net earnings from self-employment over time, including how the $400 threshold of 42 U.S.C. 411(b)(2) and exempt ministers' earnings enter. A year with no rule for a family is refused.

### 2.2 CE2: the PSID job-context and earnings-component crosswalk

- **Job context, 1968–2023.** It extends `psid_job_context.py`, which reads interview waves 2003–2023 (`psid_job_context_registry.py`), to every earlier wave, and adjudicates the value codes of the government-employer, industry, occupation, self-employment, incorporation and state items in every wave from the codebooks and setup files, with the repository's label-verification discipline. Raw tokens are kept; adjudicated codes sit beside them.
- **Earnings components.** For each wave and role, it lists the labor-income components the questionnaire records (for example wages and salaries, bonuses, overtime, tips and commissions, the labor part of business and farm income, professional practice) and assigns each a remuneration type: wage, self-employment, mixed or unknown.
- **Reference years.** Every component is placed in its income year by the frozen reference-year law in `psid_covered_earnings_registry.py`. Income years the biennial questionnaire does not observe keep a `structural_gap` provenance and inherit their status from the adjacent observed years by a registered rule; they never become direct observations.
- **What it reads.** Codebooks, setup files and questionnaires only. Its tests run on invented files. It computes no statistic from PSID microdata.

The covered-earnings campaign's sweep found 46 of 818 official prompts that broke a single-field rule (#403), so CE2 is priced at the upper end of its range in the parent.

### 2.3 CE3: the classifier

The classifier is a pure function from a component-year's facts (remuneration type, amount, year, state, government level, industry, occupation, self-employment and incorporation status, and age) to its four status probabilities, with reason codes. It applies, in order:

1. **Direct rules.** A CE1 rule whose trigger facts the record identifies decides the status, one-hot. Private-sector employment is covered unless an exclusion applies (42 U.S.C. 410(a)), so a private-sector wage record with every applicable exclusion resolved is `covered_wage`.
2. **Thresholds.** Where the facts identify a threshold category (self-employment, church employees, domestic, agricultural or election work), the year's threshold decides the status.
3. **Sourced priors.** Where coverage turns on facts the data do not record, chiefly state and local government workers, whose coverage depends on a Section 218 agreement and on membership in a public retirement system, the record takes a probability of noncoverage by state, government level, occupation group and era from a prior source registered at IR0: the Census Annual Survey of Public Pensions, SSA's Section 218 references and, if D5 admits it in this role, the SIPP Synthetic Beta's noncovered earnings. A cell with no prior source leaves the record `unresolved`.
4. **Everything else** to which an `unidentified` exclusion could apply stays `unresolved`.

**One question this note does not settle** (§8, question 1): some exclusions can almost never be identified in a household survey and are rare, such as a child under 18 working for a parent (42 U.S.C. 410(a)(3)). Read strictly, step 4 leaves every young worker's wages `unresolved`. The alternative is a `negligible` class: an exclusion whose prevalence a cited source bounds below a registered threshold is treated as not applying, with a reason code on every affected record and the bounded mass reported. That is a methodology choice, and the review round and Max decide it.

**Statutory order.** Within each joint coverage outcome of a person-year, §3.2's equations of the old design compute taxable wages, taxable self-employment and taxable payroll. Components that share one statutory coverage fact (one job, one year) share one coverage-state group and co-move; distinct groups are independent, a declared assumption (old design §3.1, lines 254–284). Expected values are exact probability-weighted sums over joint outcomes, computed by a dynamic program that a fixture test checks against brute-force enumeration.

**RET-countable earnings.** The earnings test has its own earnings concept. An individual's earnings for a taxable year are the sum of wages for services rendered in the year and net earnings from self-employment, minus any net loss from self-employment (42 U.S.C. 403(f)(5)(A)). Net earnings from self-employment are determined as 42 U.S.C. 411 provides, except that paragraphs (1), (4) and (5) of 411(c) do not apply (403(f)(5)(B)(i)); so a minister's exemption does not remove earnings from the test. Wages include noncovered service performed in the United States as an employee, and exclude payments on account of retirement (403(f)(5)(C); parent §2.5). Three consequences for CE v2:

- a wage component counts toward the test whether it is covered, noncovered or `unresolved`; only its remuneration type matters;
- a net self-employment loss reduces RET-countable earnings, although it never offsets wages in the taxable-payroll ordering above;
- the $400 threshold defines self-employment income (42 U.S.C. 411(b)(2)), a different concept from the net earnings the test uses, so it does not apply here.

Pension income never enters. CE1 reads the rest of 403(f)(5), including subparagraph (D)'s exclusions from gross income, before CE3 encodes the channel.

### 2.4 CE4: the gate CE-G

The parent design (§3.1, part 4; §7.3) fixes the gate's structure; IR0 freezes its cells, tolerances, pass conjunction and bite rule before it registers.

- **Truth.** EPUF by birth cohort, sex and age band for 1968–2006: the share of person-years with positive covered earnings, capped covered-earnings quantiles, and years without covered earnings. If IR0 powers them, two more cell families: covered workers and taxable earnings by state against the Annual Statistical Supplement's Table 4.B10, and the SIPP Synthetic Beta's covered and noncovered earnings once Census staff validate the results on the Gold Standard File.
- **Order.** Registration on #42 pins a commit; then the truth-only floor; then the all-covered proxy, scored against the floor before any CE v2 output. If the proxy passes the registered bite-check conjunction, the gate stops as `WEAK_POWER_OR_VACUITY`.
- **Exposure already on file.** `gate_epuf`'s committed floors and bridges for 1998–2004 (`runs/epuf_gate_floors_v1.json`) and `gate_epuf_fill`'s published all-covered reference arm (parent §7.2). IR0 records both.

### 2.5 CE5: the person-year handoff table

One versioned table, one row per person, role and income year from 1968, with:

- **the old registry's estimands, by their IDs and definitions** (old design §3.1, lines 211–240): `covered_employee_wages_uncapped`, `covered_se_gains_pre_loss`, `covered_se_loss_magnitude`, `covered_se_net_earnings_pre_seca`, `covered_seca_base_uncapped`, `noncovered_earnings`, `noncovered_se_loss_magnitude`, `unresolved_earnings`, `unresolved_se_loss_magnitude`, `oasdi_taxable_wages_person`, `oasdi_taxable_se_person`, `oasdi_person_taxable_payroll`, `benefit_only_deemed_credits` (zero, as in v1), `benefit_creditable_earnings`, and the worker-probability fields. The fields that the old design tied to Table 4.B2's and 4.B11's worker-membership rules are reported only where CE1 has verified the table's definition; otherwise they are absent, not approximated;
- **the added channel** `ret_countable_earnings` (§2.3);
- labor income as adjudicated, so every row reconciles: covered wages, covered self-employment, noncovered and unresolved amounts sum to it, with self-employment losses in their own channels as in the old design;
- provenance per row (`direct`, `structural_gap` or `projected`; source wave, role and component identifiers; the rule and prior versions applied);
- **the label array**, proposed: `["frame-relative", "modeled-covered-earnings", "prior-informed-uncalibrated"]`. The third token says that registered statutory rules and registered prior sources informed the model, and that no official covered-earnings total, gate truth, loss or optimizer did. Amendment 2's token, `deterministic-uncalibrated`, would misdescribe sourced priors (§8, question 3).

**Consumers, each through this table or the classifier's contract, never by reclassifying:**

- Track B's H, whose labor, covered and RET-countable channels stay separate (`src/populace_dynamics/track_b/README.md:125`). Until CE5 passes, H's covered channel keeps the label "labor-income proxy". Track B's insured-status rule reads covered earnings through H.
- B5, the earnings test, which reads `ret_countable_earnings`.
- The lifetime-earnings groups (`src/populace_dynamics/estimates/lifetime_measures.py`), which use the capped covered channels.
- National payroll for Registration 18 and M7, which uses `oasdi_person_taxable_payroll`.
- The mortality, groups and financing lane's F2b (PR #558, `docs/design/mortality_groups_financing.md` §7.4, line 783), which needs "each earnings component classified as covered wages, covered self-employment, noncovered or unresolved" on the certified frame's start year. F2b calls the classifier on the frame's records through the same fact contract; facts the frame lacks give `unresolved` or a refusal, never a guess.

## 3. Projected years

The forward-earnings law has no job identity (parent §3.1), so a projected year cannot be reclassified from a new job.

- **Primary rule.** Each person's last observed coverage-state distribution, by remuneration type, carries forward to every projected year. The wage and self-employment split of a projected amount follows the forward-earnings law's own components where it has them, and the person's last observed shares otherwise, as the old design's synthetic `projected#wage` and `projected#self_employment` components did (§4.3, lines 1347–1355).
- **Registered sensitivity (Max, d1923):** all projected wages are covered; projected self-employment is covered subject to the year's threshold.
- **No reset on a job change.** A reset conditioned on a job change waits for a separately sourced, priced and admitted job process, which no plan contains.
- **People with no observed status.** Under the primary rule, a person who enters the projection without an observed coverage state (an entrant of the open-population lane) carries `unresolved` wages; under the sensitivity, covered wages. Max's ruling on pre-entry covered earnings (d1925: censored, unknown to insured status, with zero as a labelled sensitivity) governs years before entry; this rule governs years after it.

## 4. Representation

- **Money** in integer cents (64-bit integers). Every conservation identity then holds exactly.
- **Probabilities** as integer numerators over the fixed denominator 2^20. A sourced prior is rounded to that grid once, by a registered rule, when the prior table is built; the four numerators of every record sum to 2^20 exactly.
- **Expected values** of nonlinear fields are exact sums over joint outcomes, converted to floating point only at a reporting boundary.
- **Draws** are keyed by person, year, coverage-state group and draw index through a counter-based hash, so results do not depend on row order.

## 5. Invariants

Each is stated in the PR that builds its component and tested with Hypothesis beside example tests (parent §9).

- The four status numerators are nonnegative integers that sum to 2^20.
- Conservation: covered wages, covered self-employment, noncovered and unresolved amounts sum to the component-year's adjudicated labor income, with self-employment losses reported in their own channels.
- Statutory order: taxable wages = min(wages, cap); taxable self-employment = min(self-employment base, max(0, cap − taxable wages)); no self-employment loss offsets wages; no capped amount exceeds the year's taxable maximum.
- Nothing is covered while an applicable exclusion is unresolved, unless a registered `negligible` class applies (§2.3) and the record carries its reason code.
- Zero labor income gives zero in every channel.
- Raising a component's noncoverage probability never raises its expected covered taxable amount.
- RET-countable earnings equal all wage components (covered, noncovered and unresolved) plus net earnings from self-employment minus any net self-employment loss, as 42 U.S.C. 403(f)(5) defines them, and never include pension payments.
- Expected nonlinear fields from the dynamic program equal brute-force enumeration on every registered dependence pattern.
- Determinism under keyed draws, and invariance to row order.
- Under the sensitivity, projected covered wages are at least those of the primary rule, person by person.

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

At master `4fc2b9f4`: `docs/design/covered_earnings_correction.md` lines 1–346, 1323–1380, 8145–8222, 9193–9245, 10805–10918, 11054–11110 and 13751–13800, and its section headings; the module docstrings of `psid_covered_earnings_registry.py`, `covered_wage_history.py` and `psid_job_context.py`, and `historical_coverage_rule_validation.py` lines 1–30 and 60–105; `tests/estimates/test_covered_earnings_correction_registry.py` lines 1390–1415; `src/populace_dynamics/track_b/README.md` (searched for covered and RET-countable channels; line 125); and the parent design in full. From PR #558 at `2c19f5b6`: `docs/design/mortality_groups_financing.md`, lines found by a search for covered payroll and F2b, and lines 778–800 and 924–934. The captured texts of 42 U.S.C. 403 and 410 in `~/microcosm-launch-evidence/dynasim-parity-20260909/income-resources-20261021/sources/` (`MANIFEST.md` lists their hashes): 403(f)(5) and 410(a)(3). Decision records d1923 and d1925 in `~/chief-of-staff/state/decisions/decisions.jsonl`. No PSID, SIPP or EPUF data file was opened; no restricted file was opened.
