# Mortality, groups and financing: staged milestones

*Design, revision 2, 23 October 2026. For approval. Revision 1 applied
the round-1 review's fifteen findings (section 12); revision 2 applies the
round-2 review's four findings (section 13).*

- **Status.** This document proposes milestones, gates and prices for one
  lane of the DYNASIM-parity plan. It authorizes no build, registration,
  real-data run, comparator access or change to any shared module. Max
  authorized the lane on 21 October 2026 (decision d1802); nothing is
  built before Max approves this design.
- **Scope.** Five rows of `docs/parity-ledger.md`: mortality differences by
  income, education and race; education; results by group; national costs
  and financing (Registration 18's 2030 COLA-cut cost test, covered payroll
  and the income tax on benefits); and trust funds and the 75-year balance
  (M7, [#113][i113], decision d660).
- **Format.** It follows revision 3 of the Track B design (28 September
  2026, approved under d515), which is kept outside this repository: a
  milestone table, verification classes, admission rules, invariants,
  risks and kill criteria, and staffing assumptions.
- **Evidence.** Every mechanism claim below cites code or a document read
  in this run, at `origin/master` `1e739d32` unless a path or commit says
  otherwise. Section 11 lists every file read and what this run was
  exposed to.

**Every effort figure in this document is an estimate.** The figures are
engineering judgments, not demonstrated throughput, under the staffing
assumptions in section 9. "d" means engineer-days and "lw" means agent-lane
weeks at 4 engineer-days a week, so lw = d ÷ 4 exactly in every cell.

## 1. Purpose

The lane builds three things the parity ledger marks as missing or
incomplete:

1. **Mortality that differs by lifetime earnings, education and race and
   ethnicity**, with the education transitions that feed it and the
   lifetime-benefit differences that follow.
2. **Complete group definitions**, so every cell that DYNASIM or MINT
   publishes for a compared table can be computed with the same definition
   and denominator.
3. **National financing**: Registration 18's cost test, covered payroll,
   the income tax on benefits, national annual cost and income, and the
   OASI, DI and OASDI trust-fund accounts through the 75-year actuarial
   balance.

Five rules bind every milestone:

- **Simulated, never scaled.** A national figure comes from running the
  microsimulation on a representative population. No national number is
  produced by scaling, interpolating or extrapolating the closed PSID
  cohort's results, or from a side model (PolicyEngine's contributing
  guidelines, PolicyEngine/.github#8). Registration 18's statistic is a
  percent change on the closed cohort and is reported as such.
- **Comparator order.** OACT and PWBM are the primary comparators, CBO is
  second and DYNASIM is one of several (d660). No comparator value selects
  structure, parameters, denominators or rows, and agreement with DYNASIM
  never rescues a failed gate.
- **Data discipline.** Builds and tests use invented data. Real PSID
  statistics are computed only inside an authorized, registered step, and
  no small-cell PSID count goes on GitHub (section 5.4).
- **Shared code stays untouched.** No milestone edits
  `src/populace_dynamics/track_b/`, `engine/loop.py`, `engine/steps.py`,
  `engine/rng.py`, `gates.yaml` or a committed `runs/*.json`. Track B's
  outputs are consumed through the interfaces in section 7.1.
- **Blindness for Registration 18.** Until Registration 18's comparator
  seal opens, nobody who builds or runs it opens a source the restricted
  list names for it, including every Trustees Report table that prints
  cost, income or balance rates, in any vintage, and the whole of PWBM's
  data bucket (`RESTRICTED-FILES.md`, A-COLA section). Section 4.1 says
  which later milestones that sequencing affects.

## 2. What exists now

### 2.1 Mortality

- **The blind projections use a two-ratio method.** `cola_track_a/mortality.py`
  scales SSA's 2004 period life table by TR 2008's age-sex-adjusted death
  rate in the projection year over its rate in a base year, for the group
  under 65 and the group 65 and over (`:117`). The ratio pair is indexed by
  year only, so men and women get the same two ratios (`:60–68`, `:99`).
  It conditions on age and sex only. Exercise 1's runner checks that its
  mortality is this substitute (`cola_track_a/runner.py:420–461`), and the
  Track A adapters pass it to `apply_di_aware_mortality`
  (`cola_track_a/adapters.py:210–238`).
- **Single-age OACT probabilities are loaded but unused by the blind
  tests.** `baselines/tr2026_intermediate.py` exposes OACT's TR 2026
  period q by single age and sex, historical through 2023 and
  Alternative II from 2024 to 2100 (`:135–159`), through the pinned
  accessor `data/tr2026.death_probability`. Its model,
  `BaselineYearAwareMortality` (`baselines/base.py:160–198`), is a
  single-year-of-age table by year and sex.
- **Disabled workers die at their own rates.** `engine/di_entitlement_rates.py`
  fits award, recovery and death rates from inputs dated 2008 or earlier
  (`:108`). Its default death mode is `multiplier` (`:185`): a disabled
  worker's probability is the Actuarial Study No. 118 rate times the
  population model's probability over the NCHS 2000 probability at the
  population model's age resolution (`engine/di_entitlement.py:844–849`).
  The default termination basis is attained age (`:195`); the
  select-and-ultimate basis is optional.
- **A cell-preserving netting step already exists.** By default
  (`non_di_mortality="net_of_di_origin"`, `di_entitlement_rates.py:206`)
  `_net_of_di_origin` (`engine/di_entitlement.py:653–723`) scales every
  non-DI-origin person's probability within each age band and sex by one
  factor, so the cell's weighted expected deaths equal the population
  model's. DI origin covers entitled disabled workers and, by default,
  those converted at full retirement age (`:815–821`). When disabled-worker deaths alone exceed the cell's total, the
  cell is logged as infeasible and its other persons get zero. The
  population model is called as `population_model(frame, context)` when it
  has no `probabilities` attribute (`:575–594`), and the adapter needs its
  `bands` (`:597–613`).
- **The engine's mortality slot takes any frame step.**
  `PeriodModules.mortality` is a `FrameStep` (`engine/loop.py:121`), called
  first in each period (`:297`). The eight module streams are fixed in
  `engine/rng.py:20–33`; the DI component draws under its own component
  tag on an existing stream (`engine/di_entitlement.py:65–73`).
- **PSID deaths and life tables.** `data/deaths.py` reads the PSID's
  cross-year year of death (`ER32050`, `:85–91`) and decodes its range and
  sentinel codes (`:115`). `data/life_table.py` implements OACT's period
  life-table equations, with a builder-default constant-terminal-q closing
  rule that awaits ratification (`:17–37`).
  `runs/mortality_floors_v1.json` is a report-only comparison of PSID death
  hazards by age band and sex with NCHS 2023 rates, with a half-split floor
  and an unratified proposal for a future gate.
- **What the audited code does not do.** The mortality implementations
  above do not condition on income, education or race, and a search of
  `src/` this run found no other model that does; the parity ledger's
  mortality-differences row says the same.

### 2.2 Education and group attributes

- **Education is a fixed attribute.** `data/group_attributes_psid.py` reads
  the individual file's years of completed education for heads, wives and
  other family-unit members aged 16 or older, race and Hispanic origin for
  heads and wives only (`ROLES`, `:124`), and country of birth for heads and
  wives from 2013. `cohorts/group_attributes.py` resolves one value per
  person: race and country of birth from the most recent complete report,
  education as of the population's last anchor wave, and an explicit status
  (for example `never_head_or_spouse`) instead of a guess (module docstring,
  `:13–40`).
- **The engine has no dedicated schooling slot.** Its eight slots are
  mortality, aging, marital core, fertility, disability, earnings, claiming
  and household composition (`engine/loop.py:121–128`).
- **MINT categories exist as code.** `estimates/group_breakdown.py`
  (from [#513][pr513]) holds `MINT8_SCHEME` (`:1393`) and
  `MINT8_COHORT_SCHEME` (`:1432`), built from a committed labels-only
  extract and verbatim quotes of SSA's MINT8 Table User Guide. It assigns
  each row to one category per dimension and counts unclassified rows by
  reason (`assign_groups`, `:2177`), and cuts weighted quintiles
  (`:1876`). `estimates/lifetime_measures.py` computes the lifetime
  measures MINT's cohort tables use (initial AIME quintile and lifetime
  payroll-tax quintiles, own and shared). No real-data group run is
  registered.
- **Exercise 2 omits 21 rows by name.** `estimates/uniform_cut_tabulation.py`
  lists them (`NOT_COMPUTED_REPORT_ROWS`, `:225–278`, 21 rows in five
  sections): race and ethnicity,
  education, labor-force experience, and own and shared lifetime-earnings
  quintiles. Its reasons include that the source report does not define
  labor-force experience, does not say whether "High school graduate"
  includes some college, and does not say over which population the
  lifetime-earnings quintiles are cut.
- **The post hoc group design for exercises 1 and 3** is
  `docs/design/nasi_projection_groups_posthoc.md`. It derives current-law
  benefit type from the frozen benefit components, leaves household income
  and official poverty "not computed" for the closed projection, and flags
  subgroups under SSA's disclosure minimum.
- **The Microcosm frame has no education.** No Microcosm US release checked
  carries educational attainment, and its ages are top-coded at 80 and 85
  (`docs/plans/microcosm-start.md:489–491`).

### 2.3 Financing

- **The first-estimates ledgers are frame-relative.** For each projected
  person-year, `_revenue_annual_row` takes `min(earnings, wage_base)` and
  multiplies the weighted sum by the employee, employer and combined OASDI
  rates (`estimates/ledgers.py:926–972`, `:949`). Every PSID labor-income
  dollar counts as covered. The publication contract labels the revenue
  table "nominal frame-relative OASDI payroll contributions on the
  labor-income proxy" (`estimates/publication.py:564–573`) and states "This
  report does not estimate national dollars" (`:240–247`).
- **The M2 analogue is not a trust-fund projection.**
  `runs/m2_pseudo_projection_v1.json` runs a closed frame of 1,549 careers
  born 1943–1957. Its outlays are own-record retired-worker benefits only,
  with no DI or auxiliary benefits; its revenue is the combined rate on the
  same frame's taxable payroll; its balance is a present-value analogue at
  a 2.9 percent discount rate; and its starting reserve is calibrated so
  that the baseline exhausts in the year an Urban analysis reports. The
  file says itself that levels are frame-relative.
- **Registration 18 is posted and half built.** Its specification
  ([#42 comment][reg18]) registers a report-only, one-shot test of OACT
  provision A1's 2030 cost effect on R0's closed cohort, against OACT and
  PWBM, with a MINT5 sub-row. Its statistic P is the percent change in
  weighted 2030 benefit totals, with the OASI and DI split, MINT5's band
  statistics and the spec-only nulls; it estimates no national dollars.
  The build's stage 1 (config, runner, statistics, nulls, the TR 2026
  Table V.C1 capture, entry script and guards, 26 files, 5,050 lines) is
  commit `9de858d0` on branch `acola-reg18-build-20260930`. That branch
  exists only in the local clone `~/PolicyEngine/social-security-model`,
  was never pushed, and sits on `75cd3524`, 461 commits behind master. The
  coordinator backed it up on 21 October 2026 as a verified bundle,
  `EV/acola-reg18-build-20260930-9de858d0.bundle` (SHA-256 `7ed36c75…`). Its
  build notes (`EV/acola-build-20260930/stage1-lane-notes.md`) list the
  remaining stage-2 work: the comparison script, the design note, and the
  source-exclusion entries with their exact-tuple test. Stage 1 edited
  `tests/tier_counts.json`, so the rebase also needs a fresh tier recount.
  Between the registration's code commit `dd222b9` and master, the only
  change under `cola_track_a/`, `scenario_benefits.py`,
  `estimates/cola_age_profile.py`, `track_a_v2/`, `fra68_track/`, `ss/`,
  `claiming.py`, `engine/` and the registered-run script is the new
  `ss/statutory_delayed_credit.py` from [#532][pr532], which sits beside
  the oracle and changes no existing function (a `git diff --stat` run this
  session).
- **PolicyEngine-US computes the income tax on benefits and its split.**
  In the local `policyengine-us` checkout (`cae6fc26ce`, 20 October 2026),
  `variables/gov/ssa/revenue/tob_revenue_total.py` takes income tax with
  and without taxable benefits. PE-US's `income_tax` adds the net
  investment income tax and other taxes outside Chapter 1 of the Internal
  Revenue Code (`variables/gov/irs/tax/federal_income/
  income_tax_before_refundable_credits.py:18–27`), so all three revenue
  variables count any such tax that taxable benefits trigger, although the
  transfer provision below covers Chapter 1 liabilities only. `tob_revenue_oasdi.py` credits OASDI with
  the tax on `min(taxable benefits, 0.5 × gross benefits)` against none, and
  `tob_revenue_medicare_hi.py` credits HI with the rest. These were added on
  30 October 2025 (`299f5657b7`). A different variable,
  `taxable_social_security_tier_1.py`, also labeled as OASDI's, returns the
  §86(a)(1) amount below the adjusted base and only the "bracket amount"
  above it. The statute credits OASDI with the tax increase attributable to
  section 86 less the increase attributable to the 1993 amendments, and HI
  with the latter, on the basis of Treasury's estimates (42 U.S.C. 401 note;
  Pub. L. 98-21 §121(e)(1)(A)–(B), as amended by Pub. L. 103-66 §13215(c)).
  The two PE-US readings disagree. Take a single filer with $20,000 of
  benefits and $40,000 of combined income, with PE-US's thresholds ($25,000
  and $34,000) and rates (0.5 and 0.85). Current law makes $9,600 of the
  benefits taxable. `tob_revenue_oasdi` credits OASDI with the tax on all
  $9,600, because its cap of half the benefits ($10,000) does not bind.
  `taxable_social_security_tier_1` assigns OASDI $4,500, the bracket
  amount. PE-US's own §86(a)(1) amount (`amount_under_paragraph_1`) is
  $7,500. Running PE-US at `cae6fc26ce` on that invented filer for 2026
  (taxable interest of $30,000, age 70) gives $1,021 of tax on benefits,
  all of it credited to OASDI by `tob_revenue_oasdi` and none to HI. Tax
  with taxable benefits set to the §86(a)(1) amount, minus tax with none,
  gives $769 for OASDI and leaves $252 for HI; the tier-1 amount gives
  $450. For a filer whose half-of-benefits limit binds ($30,000 of
  benefits, $60,000 of interest), `tob_revenue_oasdi` and the §86(a)(1)
  reading agree at $1,845. None of the three filers reaches the net
  investment income tax threshold, so these are Chapter 1 amounts. The
  script and its output are
  `EV/mortality-groups-financing-20261021/tob_split_check.py` and
  `tob_split_check.out.json`. PE-US chose its current split on purpose in
  December 2025 (issue PolicyEngine/policyengine-us#6998, fixed by #6999).
  The issue describes it as the "first 50%" of gross benefits, but the code
  credits OASDI with the tax on the smaller of current-law taxable benefits
  and half of gross benefits, as above; it is not a flat half of gross. The
  note's text subtracts the increase attributable to the 1993 amendments,
  which points to the pre-1993 §86 amount, PE-US's §86(a)(1) amount. That
  amount falls below PE-US's whenever the second tier applies and half of
  gross benefits does not bind. On 21 October 2026 the US and core hub,
  which owns PE-US, confirmed the discrepancy from the code and planned a
  fix (branch `hub-tob-oldlaw-split`). The fix first checks the law and
  OACT's or Treasury's method, and logs a ruling instead if either
  supports a different split. F1 cites that pull request and builds on its
  result.
- **The bridge.** `bridge/policyengine_us.py` runs PolicyEngine-US in a
  separate interpreter, writes situations from Microcosm amounts, and
  returns every node of the `household_net_income` tree (module docstring).
  It cites policyengine-us 2.18.0; whether that version carries the three
  revenue variables was not checked this run.
- **Older trust-fund inputs exist and were not opened.** [#219][pr219]
  committed 2014 Trustees Report pages and extracts
  (`data/external/ssa_tr_2014_ii_c1.source.html`,
  `ssa_tr_2014_vi_g8.source.html`, `ssa_trust_fund_opening_reserve_2014.json`,
  `ssa_effective_interest_rates_2014.json`,
  `ssa_tr_ultimate_assumptions_2014.json`). The unmerged branch
  `m7-design` holds a 927-line M7 design from July 2026. Trustees Report
  cost, income and balance tables of every vintage are restricted for
  Registration 18's builders until its seal opens, so this run opened
  neither; S0.2 reads them once that restriction is lifted (section 4.1).
  `estimates/lifetime_measures.py` already loads SSA's OASDI tax rates and
  trust-fund interest rates from pinned files (`:153–160`, `:673–760`).

### 2.4 What is missing

| Capability | Missing piece |
|---|---|
| Differential mortality | Any model of mortality by lifetime earnings, education or race; loaders for OACT, NCHS and linked-mortality gradient sources; a gate |
| Education | A transition step; education in the Microcosm frame |
| Groups | Definitions for labor-force experience and Butrica–Uccello's lifetime-earnings quintiles; DYNASIM output's row definitions; beneficiary type and household income for projections; registered group runs |
| Registration 18 | Stage 2 of the build, a rebase, review, the second registration comment and the one shot |
| Covered payroll | A covered/noncovered split, self-employment, and a national payroll on a representative population |
| Income tax on benefits | A settled OASDI/HI split, tax-unit income for projected beneficiaries, and a national total |
| National cost | Complete payments on a representative population; administrative expenses and the Railroad Retirement interchange as labeled exogenous paths |
| Trust funds | Accounts for OASI, DI and OASDI; interest crediting; trust-fund ratios; depletion with scheduled and payable paths; the 75-year actuarial balance |

## 3. Staged milestones

### 3.1 Milestone table

Every effort cell is an estimate under section 9's assumptions, and
lw = d ÷ 4 exactly.

| Id | Deliverable | Verification or gate | Effort estimate (d / lw) | Depends on | Unlocks |
|---|---|---|---|---|---|
| **F0** | Registration 18 build, stage 2 and close-out: rebase stage 1 onto master; `scripts/compare_acola.py`; the design note; exclusion-tuple entries and test; tier recount; a mechanism-L equivalence test against `dd222b9`; a cross-check that the stage-1 Table V.C1 capture and master's `data/tr2026` COLA path give the same increases for December 2027–2029 | Conformance to the registration and to the cleared builder brief's section 6 invariants; independent review returns APPROVE; CI green; no real-data statistic computed | 3–5 / 0.75–1.25 | A fresh blind builder lane under the cleared brief; the coordinator's tier-count slot | F0R |
| **F0R** | Registration 18's one shot: the second registration comment, the launchd run at the registered commit, the artifact PR, the seal opening and the posted result | Registered one-shot comparison, report-only, under the registration's rules | 1–2 / 0.25–0.5, excluding queues | F0; Max posts the second comment | S0.2, through the orchestrator's ruling on the A-COLA restrictions |
| **S0.1** | Source, exposure, access and power audit for SM2, SM3, SM4, ED1, ED2 and GR1 to GR4 | A frozen record per gate (section 5.2) before that gate registers; a blinded review of feasibility and power | 4–6 / 1–1.5 | Nothing | SM2, ED1, GR1 |
| **S0.2** | The same audit for F1 to F5, run by a validation-only source auditor, who reads the Trustees Report's financing tables, OACT's provision pages and PWBM's data and hands builders only values-scanned definitions, access metadata and cleared model inputs | As S0.1 | 3–5 / 0.75–1.25 | F0R; the orchestrator's ruling that lifts the A-COLA restrictions; a validation-only lane | F2b, F3a, F3b, F4's replication check, F5 |
| **SM1** | Differential-mortality mechanism on invented data: relative risks by lifetime-earnings rank, education and race and Hispanic origin, normalized within each single age, sex and year cell to the baseline's expected deaths; disabled-worker-origin persons left to the DI adapter | Accounting conformance (section 6): cell conservation, identity, bounds, composition with `apply_di_aware_mortality`, determinism | 4–6 / 1–1.5 | Nothing | SM2 |
| **SM2** | Gradient inputs and their calibration: loaders for OACT's mortality by career-average earnings, NCHS life tables by Hispanic origin and race, NCHS death rates by education, and a public linked-mortality file for joint structure and ages 65 and over; a registered gradient path over time | External-target conformance: the fitted relative risks reproduce the targets they were fitted to. A source not used in fitting is reported beside them. Labeled "calibrated, not validated" | 8–12 / 2–3 | SM1, S0.1 | SM3, SM4 |
| **SM3** | Mortality-gradient gate on the PSID 2010 cohort's recorded deaths, 2011–2023, by lifetime-earnings quintile, education and race and Hispanic origin | Registered gate (held-out prediction): each group's observed-to-expected death ratio, relative to the cohort's overall ratio, within the S0.1 tolerance under simultaneous bounds; inconclusive admits nothing | 5–8 / 1.25–2 | SM2, S0.1, an authorized registered real-data step | SM4's population claims; differential mortality inside Track B projections |
| **SM4** | Lifetime-benefit consequences: lifetime benefits and benefit-to-tax ratios by lifetime-earnings quintile, with and without differential mortality | Registered comparison, report-only, with OACT and PWBM first, CBO second and DYNASIM one of several | 4–6 / 1–1.5 | SM3, or SM2 with the calibrated label; admitted payment and covered-earnings histories (Track B's G, I and H); admitted entrant initialization; an admitted horizon covering the registered lifetime measure. National comparisons also need the representative population | The ledger row's lifetime-benefit cells |
| **ED1** | Education transitions: attainment from age 16 to 35 by birth cohort, sex, race and Hispanic origin, and parents' education where a child is linked to a parent; fitted on public CPS microdata | Fit conformance on invented data; the fitted schedule reproduces its training tables | 5–8 / 1.25–2 | S0.1; Microcosm's pinned CPS person files | ED2; education for projected people in SM and GR |
| **ED2** | Education gate | Registered held-out prediction: projected attainment at ages 25–34 by birth cohort and sex against later Census CPS and ACS tables than the fit used | 3–5 / 0.75–1.25 | ED1, S0.1; the open-population lane's young and newborn people | The education row |
| **GR1** | Group-definition registry: every dimension, row label, definition and denominator that each compared table publishes (MINT8, Butrica–Uccello, DYNASIM's published output, and OACT's or PWBM's distributional tables where S0 finds them), as labels-only extracts cleared by a validation lane's values scan, with a crosswalk to our attribute codes | Definitional conformance: labels match the captured extracts exactly and in order, quotes match after whitespace normalization, and source hashes match, as `verify_mint8_sources` does today (`estimates/group_breakdown.py:1710–1715`) | 4–6 / 1–1.5 | S0.1; a validation lane for the scans | GR2a |
| **GR2a** | Closed-cohort constructors for the missing dimensions: labor-force experience, lifetime-earnings quintiles own and shared under Butrica–Uccello's description, education rows with the "some college" alternatives, and race and ethnicity rows | Definitional conformance plus partition and quintile invariants on invented data; a definition a source leaves open becomes a named alternative, never a silent choice | 4–6 / 1–1.5 | GR1 | GR3 |
| **GR2b** | Projection constructors: beneficiary type from Track B's payment outputs, and household income and poverty from the income lane, through the interfaces in section 7 | As GR2a | 2–3 / 0.5–0.75 | GR2a; Track B's G and I; the income lane's projected incomes | Projection rows of the results-by-group row |
| **GR3** | Registered group runs of the four blind tests: every cell of every compared table that GR2a's constructors can compute, with small-cell suppression before anything is published. Cells that need GR2b are GR4's | One registered post hoc run per test on [#42][i42], report-only, publishing regardless | 6–10 / 1.5–2.5 for the four | GR2a; Max posts each registration | GR4; the results-by-group row |
| **GR4** | Deferred group runs: the cells that need GR2b's projection constructors (beneficiary type, household income, poverty), on registered projections | Before each real-data run, its payment and income inputs, estimands and disclosure rules are frozen under its own authorization and registration, or as an explicitly registered prospective phase of GR3's. Report-only, post hoc, publishing regardless. A deferred cell stays incomplete until it is published or reported unsupported | 3–5 / 0.75–1.25 | GR2b, GR3; the registered projections that supply the cells; Max posts each registration | The results-by-group row's projection rows |
| **F1** | Income tax on benefits: the OASDI and HI split of the tax on benefits, settled against the statute with worked examples, computed per tax unit through policyengine.py (the existing bridge is the transitional adapter), consuming the US and core hub's PE-US conformance fix and its Axiom mirror. Every counterfactual uses Chapter 1 income-tax liability only, so the net investment income tax and other taxes outside Chapter 1 enter neither the total nor either fund's share | Statutory conformance: worked examples of §86's tiers and of the 42 U.S.C. 401 note split, including an invented investment-income case that crosses the net investment income tax threshold; OASDI + HI = total; differential tests against PE-US's existing variables, with intended differences labeled | 4–7 / 1–1.75 | Nothing for the build; the hub's PE-US fix for the final split | F3a, F3b |
| **F2a** | Covered-payroll arithmetic: taxable payroll from covered wages and self-employment income on the taxable maximum, with noncovered earnings excluded through a frozen covered-status interface, on invented people | Statutory conformance on invented people | 3–5 / 0.75–1.25 | Nothing | F2b |
| **F2b** | Covered payroll on the certified frame's start year: the covered-status classification applied to the frame's earnings, and a report-only check against SSA's Annual Statistical Supplement Tables 4.B, which no fit may target. Projected years' payroll uses H's covered earnings inside F3b | Report-only check | 3–4 / 0.75–1 | F2a, S0.2; a covered-status classification (section 7.4); the certified frame | F3a |
| **F3a** | National cost and income for the Microcosm start year, from the frame's benefits and covered earnings, with a scope matrix naming each missing rule. Projected years wait for F3b, because they need forward earnings | Report-only; every refusal stays in the denominators and its share is published | 4–6 / 1–1.5 | F1, F2b, S0.2; the Microcosm start (open-population lane); Track B's G | F3b |
| **F3b** | National cost gate: annual OASI and DI benefit payments and payroll-tax income on the projected population against SSA's realized trust-fund operations in years after the frame's information date; then per-provision changes in national cost and income against OACT and PWBM, CBO second, DYNASIM one of several | Registered gate on the realized years; the per-provision comparisons are registered and report-only, as Registration 18 is | 6–10 / 1.5–2.5 | F3a; Track B through J and B7 for the projected payments, and H for projected covered earnings; insured status | F5; the national-costs row |
| **F4** | Trust-fund accounting engine (M7's accounts): annual OASI, DI and OASDI income, cost and reserves; interest crediting; trust-fund ratios; scheduled and payable paths and the depletion year; summarized rates and the 75-year actuarial balance as the Trustees Report defines them | Accounting conformance on invented flows; after S0.2, an arithmetic replication of OACT's published long-range summary from OACT's own published annual figures, labeled "arithmetic replication, not a model test" | 6–9 / 1.5–2.25 | Nothing for the build; S0.2 for the replication | F5 |
| **F5** | M7: the baseline 75-year projection on the representative open population and per-provision balances | #113's gate: the baseline's annual cost and income rates, actuarial balance and depletion year within pre-registered tolerances of the matching Trustees Report baseline; per-provision balances in levels against OACT and PWBM first, CBO second, DYNASIM one of several | 10–15 / 2.5–3.75 | F3b, F4; the open-population lane's entrants, emigration, alignment and an admitted horizon to 2100 | The trust-funds row |

### 3.2 Verification class and admitted scope per milestone

The classes are Track B's: source audit, reproduction, statutory
conformance, accounting conformance, retrospective regression, held-out
prediction and causal identification. This lane adds **external-target
conformance**, for a model fitted to published targets: it admits that the
targets are reproduced, never that the model predicts.

| Id | Verification class | Admitted scope on success |
|---|---|---|
| F0 | Statutory and accounting conformance of a registered build | That the code implements Registration 18 as posted. Nothing empirical |
| F0R | Registered one-shot comparison, report-only | Registration 18's published gaps and nulls, on the closed cohort, at 2030 only |
| S0.1, S0.2 | Source audit | Nothing scientific. Each frozen record authorizes its gate's registration |
| SM1 | Accounting conformance | The mechanism's identities. No gradient claim |
| SM2 | External-target conformance | Gradient inputs for the registered sources and years. "Calibrated, not validated" |
| SM3 | Held-out prediction on recorded PSID deaths | The gradient for the registered groups, ages and years on the PSID cohort. An inconclusive dimension admits nothing. PSID deaths by age and sex have been inspected before (the mortality floors run and gate m6); by group they have not, which S0.1 must confirm before SM3 can claim this class |
| SM4 | Registered comparison, report-only | Gaps against the named comparators. Not a gate |
| ED1 | Fit conformance | The fitted schedule. No projection claim |
| ED2 | Held-out prediction | Attainment for the registered cohorts, sexes and ages only |
| GR1, GR2a, GR2b | Definitional conformance | Definitions and constructors. No result |
| GR3, GR4 | Registered post hoc analysis, report-only | Group cells of the four tests (GR3) and of the registered projections (GR4), labeled post hoc |
| F1 | Statutory conformance | The tax-unit split for supported filing configurations |
| F2a | Statutory conformance | Taxable-payroll arithmetic for the classified components |
| F2b | Report-only check | The frame's start-year taxable payroll. The check is a benchmark, not a gate |
| F3a | Report-only | National totals with a published scope matrix. No admission |
| F3b | Held-out prediction on realized years; registered comparisons | National cost and income for the registered years and population |
| F4 | Accounting conformance; arithmetic replication | The accounting identities and the summary arithmetic. No projection claim |
| F5 | Conformance to OACT's baseline under OACT's assumptions; registered comparisons | That the projected population, benefit rules and accounts reproduce the baseline balance within tolerance under the same assumptions. It is not forecast accuracy, and per-provision agreement is not mechanism evidence |

**Downstream consequence.** SM4, F3b and F5 rest on SM3, ED2 and Track B's
admissions as evidence. If one of those passes only on exposed data, or
only as external-target conformance, the later milestone carries that
label and cannot claim independent prediction.

### 3.3 Ledger rows each milestone closes

| Ledger row | Today | Milestones | Status once they pass |
|---|---|---|---|
| Mortality differences by income, education and race | *None* | SM1, SM2, SM3, SM4 | *Built, ungated* after SM1–SM2; *Gate passed* after SM3; the lifetime-benefit cells *Report-only* after SM4. The row closes when SM3 passes and SM4's comparisons are published on the representative population |
| Education | *None* for transitions | ED1, ED2 | *Built, ungated* after ED1; *Gate passed* after ED2. Education's effect on earnings belongs to the earnings lane (section 7.4); its effect on mortality comes through SM |
| Results by group | *Used in a blind test*, in part | GR1, GR2a, GR2b, GR3, GR4 | Every group cell of the four compared tables that GR2a can compute is *Report-only, registered post hoc* after GR3. Existing components keep their earlier blind-test status. Projection-only rows (beneficiary type, household income, poverty) are published by GR4 once GR2b, Track B and the income lane supply them; the row closes when every cell is published or reported unsupported |
| National costs and financing | *Report-only* | F0, F0R, F1, F2a, F2b, F3a, F3b | Registration 18's result *Report-only* after F0R; income tax on benefits and covered-payroll arithmetic *Built, ungated* after F1 and F2a; start-year national totals *Report-only* after F2b and F3a; *Gate passed* after F3b |
| Trust funds and the 75-year balance | *None* for national measures | F4, F5 | *Built, ungated* after F4; *Gate passed* after F5 |

### 3.4 What can be built now and what waits

| Group | Milestones | Effort (d) | Waits on |
|---|---|---|---|
| **Now** | F0, F0R, S0.1, SM1, SM2, ED1, GR1, GR2a (closed-cohort constructors), F1, F2a (arithmetic on invented inputs under frozen interfaces), F4 (build), and S0.2 on a validation-only lane once F0R lifts the restrictions | 49–77 | Max's approval; the coordinator's tier-count slot (F0); Max's second Registration 18 comment (F0R) |
| **After a ruling, not Track B** | SM3 (an authorized real-data step), GR3 (four #42 registrations) | 11–18 | Max's rulings |
| **After the Microcosm start** | ED2, F2b, F3a | 10–15 | The certified frame and the Microcosm-start registration (d947, parked); the open-population lane's entrants (ED2); a covered-status classification (F2b) |
| **After Track B through B7 and an admitted long horizon** | SM4, GR2b, GR4, F3b, F5 | 25–39 | Track B's G v2, G part 2, R2 part (b), H, I, B3–B7 and J; insured status; the income lane's projected incomes (GR2b); entrant initialization and the open-population lane's horizon admission |

The final financing leg, F3b and F5, needs complete payments from Track B,
a representative population from the Microcosm start and an admitted
horizon to 2100. So does SM4, because lifetime benefits need payments and
covered-earnings histories over the whole registered lifetime. None of
those exists, and two depend on forward earnings, which waits on a
successor to B2 (d1659). Everything in the first row of the table depends
on none of them: GR2a and F2a build against frozen interfaces on the
closed cohort and invented inputs, and their projection and population
phases are the separate GR2b and F2b.

### 3.5 Totals, lanes and critical path (all estimates)

- **All rows:** 95–149 engineer-days, or 23.75–37.25 lane-weeks. The
  coordinator's order-of-magnitude estimates of 21 October for the same
  rows came to 48–82 days; the difference is the two source audits,
  Registration 18's close-out, the gates and the registered comparisons,
  which that estimate did not separate. Splitting GR2 and F2 into their
  closed-cohort and population phases added 2 d at each end of the range,
  and GR4, the deferred group runs, added 3–5 d.
- **Two build lanes and a validation lane, from approval.**
  - Lane M (mortality and education): SM1 (4–6) → S0.1 (4–6) → SM2 (8–12)
    → ED1 (5–8) → SM3 (5–8) = 26–40 d, about 6.5–10 weeks.
  - Lane F (financing and groups): F0 (3–5) → F0R (1–2) → F1 (4–7) → GR1
    (4–6) → GR2a (4–6) → F2a (3–5) → F4 (6–9) → GR3 (6–10) = 31–50 d,
    about 7.75–12.5 weeks.
  - S0.2 (3–5 d) runs on a validation-only lane after F0R, so no builder
    on lane F reads the financing outcome sources (section 5.4).
  - GR1 needs S0.1, which lane M finishes after 8–12 d. Lane F reaches GR1
    after 8–14 d, so a fast lane F waits at most 4 d.
- **Calendar.** From Monday 26 October 2026 at 0.8 engineer-days per
  working day, counting 26 October as the first working day, lane M
  finishes its chain between 9 December 2026 and 1 January 2027, and lane F
  between 17 December 2026 and 20 January 2027. Each chain ends with a
  milestone that waits on Max (SM3's real-data step, GR3's registrations),
  and registration and review queues, holidays and Max's rulings are
  additional.
- **The waiting legs.** ED2, F2b and F3a take 10–15 d once the Microcosm
  start exists. After the later of Track B's B7 and the open-population
  lane's horizon admission, F3b → F5 runs serially on lane F, 16–25 d,
  while SM4, GR2b and GR4 (9–14 d) run on lane M. At the coordinator's central B7
  date (around August 2027), F5's first attempt would end about four to six
  and a half weeks after that later date.
- **Rework.** The coordinator's forecast of 21 October counts 5 of 8 gated
  first attempts failed so far. This lane has four gates (SM3, ED2, F3b,
  F5). At that rate, plan for two or three retries. Each costs its gate's
  effort, 6–9.5 d on average across the four, plus about a week (4 d) of
  design and review, so the allowance is 20–41 engineer-days. It is not in
  the totals above.

**Still unpriced:**
- loaders and access for any restricted-use linked-mortality file, if S0.1
  finds the public files inadequate;
- education, race and Hispanic origin, nativity and self-employment
  columns in the Microcosm frame (a Microcosm task);
- a covered-earnings classification (section 7.4);
- insured status, which nobody owns today and which F3b needs through
  Track B's B6a;
- the long-horizon extension itself (the Track B design's design B priced
  2032/2050 and the population extension at 40–70 d; that figure is design
  B's estimate).

## 4. Data sources and access for each gate

### 4.1 Comparator order and the Registration 18 constraint

d660 makes OACT and PWBM the primary comparators for the trust-fund tests,
CBO second and DYNASIM one of several. This design applies the same order
to every gate here where OACT or PWBM publishes a matching quantity, and
says so where neither does.

Until Registration 18's seal opens, the restricted list closes, for anyone
who builds or runs it: every Trustees Report table that prints OASDI, OASI
or DI cost, income or balance rates, in any vintage; OACT's solvency
provision pages; the whole of PWBM's data bucket and its model
documentation; and MINT's policy-option tables. F0 runs entirely inside
that boundary. The milestones that need those sources (S0.2, F2b, F3a,
F3b, F4's replication and F5) start only after F0R and an orchestrator
ruling that lifts the A-COLA restrictions for this lane, with the FRA-68
rows' sources kept closed while their registration is pending. SM, ED and
GR need none of those sources, so they start now.

Lifting the A-COLA restrictions does not make anyone blind for a later
comparison. So a validation-only source auditor, who builds nothing,
conducts S0.2's review of outcome sources. F3b's and F5's builders receive
only values-scanned definitions, access metadata and cleared model inputs,
and no per-provision outcome value before their artifact merges. Nobody
exposed to a comparator's values builds or forecasts a comparison claimed
as blind, and a comparison affected by earlier exposure is labeled post
hoc. F5's baseline conformance is a different kind of test: its target,
the Trustees Report baseline, is openly specified in the registration, and
it claims no blindness.

### 4.2 Sources per gate

The external locators below were found by web searches on 21 October 2026,
which returned titles, addresses and short summaries; none was opened in
full. S0 reads each one, records its vintage, variables and exposure, and
fixes it before any registration.

| Gate | OACT and PWBM (primary) | CBO (second) | DYNASIM (one of several) | SSA, NCHS, Census and other | Access |
|---|---|---|---|---|---|
| SM2 calibration, SM3 gate | OACT Actuarial Study No. 124, *Mortality by Career-Average Earnings Level* (Bosley, Morris and Glenn, April 2018, `ssa.gov/OACT/NOTES/pdf_studies/study124.pdf`), and the update OACT presented on 14 January 2025 (S0.1 settles its study number); OACT's TR 2026 single-age q in the repository as the baseline. PWBM: its mortality documentation, located at S0.2 because PWBM's site is closed until then | Cristia (2007), CBO Working Paper 2007-11, *The Empirical Relationship Between Lifetime Earnings and Mortality*; CBO, *Growing Disparities in Life Expectancy* (2008, publication 41681); CBO's 2014 presentation on differential mortality (49659) | The DYNASIM3 primer's description of its mortality process, as a definition only. DYNASIM results by education or lifetime earnings are restricted for the NASI comparisons' builders | NCHS, *United States Life Tables, 2022* (NVSR 74(2)), by Hispanic origin, race and sex; NCHS "Deaths: Final Data" education tables (S0.1 confirms the ages they cover); NCHS public-use linked mortality files for the NHIS; the PSID death file through `data/deaths.py` (SM3 only) | Public downloads; the PSID only inside SM3's authorized step; restricted-use linked files excluded unless S0.1 shows the public files cannot identify the gradient |
| SM4 comparison | OACT's lifetime-benefit or internal-rate-of-return work by earnings level, located at S0.1; PWBM's lifetime measures, located at S0.2 | CBO's lifetime-benefit analyses by earnings, located at S0.1 | Urban's lifetime-benefit results by group, through a validation lane only | — | As above |
| ED2 gate | S0.1 records whether OACT or PWBM publishes attainment projections. If neither does, Census is primary and the design says so | — | The DYNASIM3 primer's description of its education process, as a definition only | Census, *Educational Attainment in the United States* CPS detailed tables (Tables 1–3) and the CPS historical time series (Tables A-1, A-2); ACS attainment tables | Public |
| GR1–GR4 | OACT's and PWBM's distributional tables, where they exist, as labels only | CBO's distributional tables, as labels only | Urban's published DYNASIM output and the four tests' reports, as labels-only extracts cleared by a validation lane | MINT8's labels and Table User Guide (already committed); the cleared exercise-2 and exercise-4 definitions extracts | Labels only; values never enter a builder's context |
| F1 | OACT's projected income from taxation of benefits and PWBM's, read at S0.2 | CBO's, at S0.2 | DYNASIM's, at S0.2 | 26 U.S.C. 86; 42 U.S.C. 401 note; IRS Statistics of Income tables of taxable Social Security benefits by income, as a report-only benchmark | Public, after F0R for the Trustees and PWBM figures |
| F2b | OACT's taxable payroll, read at S0.2 | CBO's taxable payroll, at S0.2 | — | SSA Annual Statistical Supplement Table 4.B (workers with taxable earnings and amounts by age and sex) | Public |
| F3b | OACT (Trustees Report) and PWBM per-provision cost and income, sealed by a validation lane | CBO's long-term projections | DYNASIM's published per-provision results | SSA's realized trust-fund operations (Annual Statistical Supplement 4.A) for the held-out years | Public, after F0R |
| F4 replication, F5 gate | OACT's long-range Trustees Report tables and per-provision balances; PWBM's baseline and per-provision balances | CBO's long-term projections | Urban's published solvency analyses and the *Five Democratic Approaches* tables, through a validation lane only | — | Public, after F0R; per-provision values sealed |

### 4.3 PSID use

- F0R and GR3 compute PSID statistics under their own #42 registrations:
  Registration 18's one shot on R0's cohort, and GR3's runs on the four
  tests' existing populations.
- SM3 needs its own authorization and registration. It runs once, on
  staged files whose digest S0.1 pins.
- S0.1 works from published inputs and invented-data power calculations.
  Any actual PSID structural count or power summary it needs requires a
  separately authorized, registered step first.
- ED1 fits on public CPS microdata, not the PSID, so it needs no real-PSID
  step.
- Every published PSID cell carries its unweighted count. A cell below the
  suppression threshold that S0.1 freezes (at least SSA's disclosure
  minimum, which the post hoc group design already flags) is suppressed in
  every file that reaches GitHub, together with any cell from which it
  could be recovered by subtraction.

## 5. Admission criteria and registration discipline

### 5.1 General rules

- Each milestone uses a new module and a new registered version.
- Source hashes, module versions, seeds, populations, estimands,
  tolerances and alternatives are frozen before any real-data outcome is
  computed. Output paths are exclusive, and abort records are published.
- Every milestone reports its verification class and admitted scope
  (section 3.2).
- Any national figure produced by scaling, interpolation or a side model is
  withdrawn (`SCALED_NOT_SIMULATED`, section 8).

### 5.2 What S0 freezes

S0 follows the Track B design's B0. For each gate it freezes the source
release, variables, population, exposure history, holdout partition,
critical cells, numerical tolerances, uncertainty treatment and pass
conjunction, and names the power procedure. The structural-audit protocol
is frozen before any count or power summary is computed. Each critical
cell's simultaneous 95 percent bound, Bonferroni over a registered cell
family, must lie within its tolerance. Resampling respects the survey
design and family clusters. Monte Carlo error must be below one-tenth of the
tolerance. **Insufficient precision is inconclusive, never a pass.**

S0 also freezes the prediction origin and the reference, interview and
publication-availability dates of every training, calibration, frame and
covariate input, as the Track B design's B0 requires: "later" or
"external" does not establish an unused holdout. A gate that claims
prospective prediction uses only attributes available at its registered
prediction boundary. Any use of later reports is labeled a retrospective
conditional analysis, with correspondingly restricted admission. This
matters for SM3 in particular: the existing group-attribute code resolves
race and Hispanic origin from every head and wife report 1985–2023,
whatever the anchor (`cohorts/group_attributes.py:15–25`), so a person's
classification and missingness can depend on later reports and on having
survived to give them. The same availability and exposure audit applies
to ED2 and F3b.

S0.1 records the exposure already on the record: the PSID death hazards by
age band and sex in `runs/mortality_floors_v1.json`, and this run's
exposure in section 11. S0.2's validation-only auditor records which
financing sources it opened, and when; builders open none of them.

### 5.3 Proposed numerical limits

These are proposals, subject to S0's prospective feasibility and power
review. That review may rescope a limit before any candidate result; it may
never loosen one after.

| Gate | Proposed limits |
|---|---|
| SM2 (conformance) | Fitted period life expectancy at 65 by earnings group within 0.1 year of each target it was fitted to |
| SM3 | Each group's observed-to-expected death ratio, divided by the cohort's overall ratio, within a factor of 1.15 (an absolute log ratio of 0.14), by sex and by the age bands 50–64 and 65–84 |
| ED2 | Each attainment category's share at ages 25–34, by birth cohort and sex: 2 percentage points |
| F3b | Realized annual benefit payments: 3 percent for OASI and 5 percent for DI; payroll-tax income: 3 percent; income from taxation of benefits: 10 percent |
| F5 | The 75-year actuarial balance within 0.30 percent of taxable payroll; summarized cost and income rates within 3 percent; the depletion year within one year |

SM3's limit divides by the overall ratio because the PSID undercounts
deaths at the oldest ages, as `runs/mortality_floors_v1.json` reports; the
ratio tests the gradient, not the level. The level belongs to the
mortality-improvement row.

### 5.4 Stage-specific rules

- **F0.** A fresh blind builder lane continues stage 1 under the cleared
  brief and a stage-2 addendum. The builder reads `RESTRICTED-FILES.md`
  first: its entries of 30 September and 1 October list the A-COLA
  comparator sources and every FRA-68 source. The coordinator, who has
  seen A-COLA design material, lands F0 and does not shape the build. Two
  additions to the brief:
  - **Delayed credits.** R0 includes people born 1917–1942 who can be
    alive in 2030. Mechanism L computes the retirement factor through the
    oracle's `claiming.benefit_factor` (`cola_track_a/benefits.py:345`),
    and the sealed oracle caps delayed credits at 48 months
    (`docs/errata/2026-10-11-delayed-credit-window.md`). The ledger asks
    every new registration that reaches those cohorts to use the statutory
    window or disclose the cap. Mechanism L cannot change without a new
    registration, so the second comment discloses the cap and cites the
    d1408 diagnostic.
  - **Equivalence.** A test shows that mechanism L's outputs on invented
    data are identical at the build commit and at `dd222b9`. A difference
    stops the build (`REG18_MECHANISM_DRIFT`).
  The builder reads only Table V.C1's COLA rows from master's
  `data/tr2026` accessor, and prints nothing else from that file.
- **F0R.** Registration 18's own rules apply unchanged: one shot under
  launchd, one disclosed re-execution only for an external failure before
  any value is scored, the artifact merged by its own PR before the seal
  opens, and the result posted whatever it shows.
- **SM1.** A new package (proposed: `src/populace_dynamics/mortality_ses/`)
  wraps a baseline mortality model and exposes `bands` and the
  `(frame, context) -> probabilities` call that `apply_di_aware_mortality`
  uses. It returns the baseline probability for every disabled-worker-origin
  person and normalizes the others, so the DI adapter's multiplier sees the
  baseline rate and its netting preserves the relative gradient among
  everyone else. It consumes no random numbers. Its call matches
  `BaselineYearAwareMortality.__call__` (`baselines/base.py:232–235`).
  `apply_mortality` asks its model for `probabilities(frame)` with no year
  (`engine/steps.py:113–132`), so a projection that runs without the DI
  adapter gets a new frame step that draws the same person-keyed mortality
  uniforms and leaves `engine/steps.py` unchanged.
- **SM2.** The joint model is log-additive across the three dimensions,
  with age-varying coefficients, normalized per cell. The primary dimension
  and the gradient's path over time (constant at the last observed level as
  the proposed primary, a widening path as the registered alternative) are
  Max's methodology rulings (section 10).
- **SM3.** Registered on #42 before any death is counted by group. Persons
  with an unclassified attribute enter the overall ratio and no group cell.
  Under `WEAK_POWER_OR_VACUITY` a dimension is reported, not gated. Its
  group attributes come only from reports available at its registered
  prediction boundary (section 5.2); if S0.1 cannot build them that way,
  SM3 is registered as a retrospective conditional analysis instead.
- **ED1.** Draws use a component tag under an existing module stream, as
  the DI component does, and enter the loop by composition inside an
  existing slot, so `engine/loop.py` and `engine/rng.py` stay unchanged.
- **GR3.** Each registration is post hoc and says so. It quotes the cleared
  definitions it uses. Before registering, this lane checks with the
  session that built #513 and supplies GR1 and GR2a to any registration
  that session already holds, rather than drafting a second one. Its cells
  are *Report-only, registered post hoc*, never a new blind-test status.
- **F1.** The statutory reading is fixed by worked examples before any
  population run. Until it is settled, every OASDI figure carries both
  readings as an interval (`TOB_SPLIT_UNRESOLVED`). Every tax counterfactual
  uses Chapter 1 liability only.
- **F3b and F5.** Per-provision comparisons follow Registration 18's
  protocol: a validation lane seals the comparator before any builder
  run; two independent transcriptions; a values scan on anything builders
  read; the seal opens after the artifact merges. Builders are unexposed to
  the comparators' values (section 4.1); a comparison that cannot meet that
  is registered as post hoc. F5's baseline conformance is registered
  openly, with its tolerances and its conjunction of annual and summarized
  checks fixed at S0.2; agreement on summarized rates cannot replace the
  annual checks.

## 6. Invariants and tests per component

Every load-bearing component states these in its PR and tests them with
Hypothesis property tests alongside example tests. Counterexamples are
executed and minimized before anyone calls them bugs, and intended
violations are labeled.

- **Differential mortality (SM1)**
  - *Cell conservation*: within each single age, sex and year cell,
    Σ w·q equals Σ w·q_baseline, exactly up to the clipping residual, which
    is logged; a cell whose fixed rates alone exceed the baseline total is
    flagged infeasible, as `_net_of_di_origin` flags its cells.
  - *Identity*: with every relative risk equal to 1, every probability
    equals the baseline's bit for bit, and a projection draws the same
    deaths as with the baseline model.
  - *Bounds*: every probability lies in [0, 1].
  - *Composition with the DI adapter*: after `apply_di_aware_mortality`,
    each feasible cell's expected deaths equal the baseline's up to a
    logged clipping residual within the frozen tolerance. (The adapter
    clips non-DI-origin probabilities at one and flags a cell infeasible
    only when DI-origin deaths alone exceed its target, so a cell can be
    feasible and still fall short after clipping.) The ratio of any two
    non-DI-origin persons' probabilities in a cell is unchanged wherever
    neither is clipped.
  - *Monotonicity (intended)*: where the registered relative risks are
    ordered by earnings rank or education, probabilities are ordered the
    same way within a cell.
  - *Invariance*: permuting rows or scaling every weight by a constant
    changes no probability; a cell holding one group gets the baseline
    probability.
  - *Differential test*: with one group held at fixed rates and everyone
    else scaled by one factor per cell, the module's normalization
    reproduces `_net_of_di_origin`'s arithmetic.
- **Gradient fit (SM2)**: fitted life tables satisfy `data/life_table.py`'s
  invariants; period life expectancy at 65 is ordered by earnings group as
  registered; refitting on permuted inputs gives the same coefficients.
- **Education (ED1)**: attainment never falls within a person; category
  shares sum to one in every cell; attainment is absorbing after 35;
  identical seeds give identical draws.
- **Groups (GR1–GR4)**: within each dimension, classified plus unclassified
  equals the total in counts and weights; every label matches its
  captured extract exactly and in order, and every quote matches after
  whitespace normalization; quintile ranks follow the existing invariants;
  the public writer refuses any artifact holding an unsuppressed small
  cell.
- **Income tax on benefits (F1)**
  - OASDI + HI = total, exactly when no zero floor binds, and reported
    otherwise; both parts are nonnegative; zero benefits give zero.
  - Total revenue is nondecreasing in benefits with other income fixed.
  - The OASDI part equals the tax with taxable benefits set to the
    §86(a)(1) amount minus the tax with none, if F1's worked examples
    confirm that reading.
  - Differential tests against `tob_revenue_total`, `tob_revenue_oasdi` and
    `taxable_social_security_tier_1`, with each difference labeled.
  - Every counterfactual tax is Chapter 1 liability: an invented
    investment-income case above the net investment income tax threshold
    shows that tax excluded from the total and from both shares.
- **Covered payroll (F2a, F2b)**: taxable earnings never exceed the taxable
  maximum or covered earnings; noncovered earnings are never taxed;
  employee plus employer equals combined (the existing assertion,
  `estimates/ledgers.py:936–942`); with every dollar covered and no
  self-employment, the new ledger equals `build_revenue_ledger`.
- **National cost (F3)**: component totals sum to the fund totals and OASI
  plus DI equals OASDI; identical-policy baseline and reform runs are equal
  under shared draws; refused families stay in the denominators; on the
  closed cohort, F3's cost change for provision A1 reproduces Registration
  18's P on the same invented frame.
- **Trust-fund accounts (F4)**: reserves roll forward exactly; payable
  benefits never exceed scheduled; raising income in any year never lowers
  the balance or brings depletion earlier; the actuarial balance equals the
  summarized income rate minus the summarized cost rate; results are
  deterministic.
- **M7 (F5)**: an identical-policy reform reproduces the baseline exactly;
  no provision's effect is assumed additive with another's unless a
  registration says so.

## 7. Interfaces

### 7.1 Track B

This lane consumes Track B's outputs and edits none of its code. The rows
below describe Track B's milestones as its design and README specify them;
of the outputs listed, only G, R2 part (a) and R3 exist as code.

| This lane needs | Track B output | Status on master | Used by |
|---|---|---|---|
| Gross monthly family benefits, with refusals named | G: `household_benefits`, `FAMILY_CONFIG_UNSUPPORTED`, refused families kept in denominators (`track_b/README.md`) | Merged; G v2 ([#530][pr530]) open; G part 2 not started | F3a, F3b, F5, SM4, GR2b |
| Earnings-test deductions | R2's ledger and R3's adjustment and recomputation | R2 part (a) and R3 merged; part (b) not built | F3b, F5 |
| Dated deaths, awards and conversions, with decedents' partial-year payments | I, the monthly calendar | Not built | F3b, F5, SM4, GR2b |
| Covered earnings kept apart from labor and earnings-test earnings | H, the history recorder | Not built; waits on a B2 successor | F3b's projected payroll, SM4, F5 |
| Admitted earnings, family, claiming and DI processes in the projection | B3–B6a, J and B7, with B7's scope matrix | Not built | F3b, F5 |

Rules for the other direction:
- SM's mortality enters a Track B projection only after SM3 passes. It
  preserves weighted expected deaths within each feasible input cell,
  subject to logged clipping residuals. That does not preserve realized
  outcomes: with person-keyed uniforms, different individual probabilities
  draw different deaths, so cumulative survival, widowhood and DI stocks
  can all change. (An invented case: probabilities (0.2, 0.2) and
  (0.1, 0.3) have the same sum, but uniforms (0.15, 0.35) draw one death
  under the first and none under the second.) Even with equal realized
  deaths, who dies changes payments: under uniforms (0.15, 0.25) both
  models draw one death, but if the two people receive benefits of 1,000
  and 3,000, surviving payments fall from 3,000 to 1,000. So before SM is
  used in an admitted Track B projection, a change-admission protocol is
  frozen that names every admission affected by changed deaths, risk sets
  and survivor pathways. The required B4 mortality, marital and DI checks
  (the Track B design's limits include 2 percentage points on cumulative
  survival and 10 percent on deaths), J's joint payment, recipient
  denominator and survivor-pathway checks, and the affected timing checks
  are completed or rerun on the changed model stack. Earlier J or B7
  evidence does not transfer automatically, and any further target
  comparison needs its own prospective registration and exposure label. A
  failed or inconclusive required check blocks the affected admission and
  its dependants (`MORTALITY_CHANGE_UNADMITTED`).
- National cost and the 75-year balance report Track B's refused share in
  every year. If refusals exceed the share S0.2 freezes, totals are
  report-only (`PAYMENT_SCOPE_INCOMPLETE`).
- If Track B pauses a mechanism under `SUCCESSOR_EXHAUSTED`, SM4, GR2b,
  GR4, F3b and F5 have no date, and F3a and F4 stay report-only.

### 7.2 Open-population lane

| This lane needs | Why | Used by |
|---|---|---|
| The Microcosm start: a certified frame, the frame reader, starting histories (H1) and gate 3's first cells (d947) | Every national figure | F2b, F3a, F3b, F5, ED2, SM4 |
| Frame columns: educational attainment (absent from every release checked), race and Hispanic origin, nativity and year of entry, class of worker and self-employment income, and single-year ages above 80 | Mortality groups, education starts, group rows and covered payroll. Whether the frame carries race and Hispanic-origin columns was not checked this run | SM, ED, GR, F2b |
| Entrants with attributes: newborns' race and Hispanic origin under a registered inheritance rule; immigrants' nativity, education and a lifetime-earnings rank | Mortality groups and group rows for people the frame does not hold | SM, ED2, GR, F5 |
| Emigration kept apart from death | Deaths and departures are separate decrements | SM, F5 |
| An alignment layer that leaves deaths alone | SM normalizes deaths to the chosen baseline's q; aligning deaths a second time would double-count. Proposed: SM owns death alignment, and the alignment layer either skips mortality or targets the same q and checks equality | SM, F5 |
| An admitted horizon to 2100 | The 75-year balance | F5 |

### 7.3 Income lane

| This lane needs | Why | Used by |
|---|---|---|
| Each tax unit's other income: wages of every member, pensions and account withdrawals, interest including tax-exempt interest, dividends and capital gains, and filing status | The income tax on benefits depends on combined income | F1's population runs, F3, F5 |
| Household income and official poverty in projections | MINT's household income quintile and poverty rows | GR2b |
| Projected SSI | Poverty rows by group | GR2b |

### 7.4 Earnings and covered-earnings work

F2b needs each earnings component classified as covered wages, covered
self-employment, noncovered or unresolved. The draft correction in
`docs/design/covered_earnings_correction.md` proposes exactly that
classification but authorizes nothing, and its campaign stopped on
9 September 2026 ([#403][i403]). H keeps covered earnings separate in the
Track B design. Which lane owns the classification is the coordinator's
call (section 10). Education's effect on projected earnings is the earnings
lane's decision; this lane supplies the attribute.

### 7.5 PolicyEngine-US and Axiom

F1 computes the tax through policyengine.py. If policyengine.py does not
expose the revenue variables, F1 uses `bridge/policyengine_us.py` as the
transitional adapter and records that. The US and core hub owns any fix
to PE-US's split; the coordinator routed it there on 21 October 2026.
Under PolicyEngine's contributing guidelines, that fix also settles the
Axiom side: the provision is shown correct in an existing rulespec-us
module, encoded through the signed encoder, or queued as a dispatch-ready
rulespec-us issue labeled `pe-parity`.

### 7.6 Validation lane and the coordinator

Validation-only lanes seal comparators, write labels-only extracts, run
values scans and open seals; builders in this lane never do. The
coordinator queues every #42 registration, ruling and public post for Max,
and assigns the tier-count slot for any PR that edits
`tests/tier_counts.json`.

## 8. Risks and kill criteria

### Blocking rule

Track B's rule applies here unchanged: required-source unavailability,
unresolved exposure, inadequate precision, unsupported critical
configurations, or a failed gate or required regression test block the
corresponding admission and everything that depends on it. Fallback
populations and estimands are registered before candidate outcomes. Failed
or unsupported cells remain reported; removing them cannot manufacture a
pass.

### Named conditions and what each stops

| Condition | Trigger | Stops |
|---|---|---|
| `REG18_MECHANISM_DRIFT` | Mechanism L's outputs at the build commit differ from `dd222b9`'s | F0 and F0R, pending a new registration |
| `ACOLA_EXPOSURE` | A member of this lane opens a Registration 18 source before its seal opens | That member's role in F0 and F0R; the exposure is recorded |
| `SOURCE_UNAVAILABLE` / `EXPOSURE_UNRESOLVED` | S0 cannot establish access or an unused holdout | That gate and its dependants; a registered fallback runs only with its own narrower scope |
| `WEAK_POWER_OR_VACUITY` | Power below 0.90 on the named operating characteristic, or uninformative tolerances | That gate's admission, pending prospective rescoping |
| `GRADIENT_SOURCES_INCONSISTENT` | Published gradients disagree beyond SM2's fit tolerance | Nothing is tuned to agree; OACT's source is primary and the others are registered sensitivities |
| `CELL_CONSERVATION_BROKEN` | Cell deaths depart from the baseline beyond the clipping tolerance | SM1's admission |
| `FRAME_ATTRIBUTE_MISSING` | The frame lacks education, race and Hispanic origin, nativity or self-employment | SM, ED, GR and F2b on the Microcosm start; closed-cohort work continues, labeled |
| `MORTALITY_CHANGE_UNADMITTED` | Any required change-admission check (B4, J or timing) fails or is inconclusive under SM | SM's use in the affected Track B admission and its dependants |
| `TOB_SPLIT_UNRESOLVED` | The worked examples cannot settle the statutory split | OASDI and HI figures publish as intervals |
| `PAYMENT_SCOPE_INCOMPLETE` | Track B refusals exceed the frozen share | F3b and F5 admissions; totals are report-only |
| `SMALL_CELL_DISCLOSURE` | A public artifact would hold an unsuppressed small PSID cell | Publication of that artifact |
| `SCALED_NOT_SIMULATED` | A national figure comes from scaling or a side model | That figure, which is withdrawn |
| `HORIZON_NOT_LICENSED` | No admitted horizon to 2100 | F5 |
| `SUCCESSOR_EXHAUSTED` | Track B pauses a mechanism | SM4, GR2b, GR4, F3b and F5 |
| `GATE_FAIL_OR_REGRESSION_FAIL` | Any registered gate fails | That admission and its dependants; published with no seed selection or tolerance relief |

### Kill criteria

- **SM.** If S0.1 finds no source pair that supports a held-out gradient
  test at 0.90 power on any dimension, SM3 is not registered, and the
  mortality-differences row stays *Built, ungated*, labeled calibrated, not
  validated. Two failed, independently justified SM3 successors pause the
  mechanism, as Track B's attempt ledger would.
- **ED.** If the Microcosm frame still lacks education when ED2 would run,
  ED2 waits; it never runs on imputed starting education without its own
  registration.
- **GR.** A dimension a source leaves undefined is computed only under a
  named alternative, reported beside the source's label, and never
  presented as the source's definition.
- **F.** No 75-year figure is published without F5's admission. Until then
  F4's accounts publish only invented-flow tests and the arithmetic
  replication.

### Attempt ledger

This lane keeps a cumulative attempt ledger by mechanism and gate family,
as the Track B design does. Renaming a module or registration does not
reset it.

### Risks most likely to slip

- **SM3's power.** In gate m6, no admissible pooling of the 25–84
  mortality surface cleared its cap, the 85+ stratum is confounded with
  survey attrition, and widowhood cleared nothing under any pooling
  (`gates.yaml:5395–5410`). Group cells are smaller still, so an
  inconclusive SM3 is the likely outcome for race and Hispanic origin, and
  SM3's bands stop at 84.
- **The OASDI/HI split** if the statute and Treasury's practice diverge.
- **The Microcosm frame**, whose certified build failed its terminal gates
  on 20 October, as the coordinator's forecast of 21 October reports, and
  which lacks education.
- **F0's rebase**, 461 commits, mostly the tier manifest and the exclusion
  tuple.
- **Track B's tail**, which sets F3b's and F5's dates.

## 9. Staffing and scope assumptions behind every estimate

- **Unit of effort.** One engineer-day is one day of reviewed output; one
  agent lane delivers about 4 engineer-days a week, as the Track B design
  assumes.
- **Two build lanes**, M and F (section 3.5), run as Subfleet builds with
  independent review, and a validation-only lane runs S0.2. Delegation-scale
  work goes through Subfleet.
- **All ranges are engineering judgments.** Every figure in section 3.1 is
  this design's own estimate. Where the coordinator's forecast or the
  Track B design priced a related item, section 3.5 says so.
- **Excluded:** review, registration and ruling queues; access time for any
  restricted-use data; work after a failed gate; validation-lane work other
  than S0.2 (seals, extracts, values scans); the Microcosm frame columns; the
  covered-earnings classification; insured status; the long-horizon
  extension.
- **Data.** The PSID inputs that SM3 and GR3 need are assumed staged
  locally under their pinned digests. This run did not check that.

## 10. Open questions for Max

1. **Approve the milestone plan and start the built-now set (49–77 d) on
   two build lanes and a validation lane?** Recommended: yes. Approve first
   attempts only, and price the waiting legs again at S0.2.
2. **Registration 18.** Finish stage 2 under F0 with the delayed-credit
   disclosure and the equivalence test, then post the second registration
   comment? Recommended: yes. The comment is yours.
3. **Lift the A-COLA restrictions for this lane after F0R** (an
   orchestrator ruling), keeping the FRA-68 rows' sources closed?
   Recommended: yes; S0.2 and the financing gates cannot start otherwise.
4. **Mortality mechanism (methodology).** Relative risks normalized within
   each age, sex and year cell to the baseline's deaths, so differential
   mortality redistributes deaths rather than adding them? Recommended:
   yes. It preserves expected deaths within each feasible input cell, so
   OACT's aggregate mortality holds in expectation. Track B's affected
   admissions still require the checks in section 7.1.
5. **Primary mortality dimension.** Lifetime earnings, with education and
   race and Hispanic origin as further dimensions of the same model?
   Recommended: yes. OACT's study is by career-average earnings, and d660
   puts OACT first.
6. **Gradient over time.** Hold the gradient at its last observed level as
   the primary path, with a widening path as a registered alternative?
   Recommended: yes.
7. **Authorize SM3's real-PSID step** once S0.1 freezes its record?
   Recommended: decide at S0.1, when its power is known.
8. **Covered-earnings ownership.** Which lane restarts the covered/noncovered
   classification F2b needs (#403)? Recommended: the earnings or income
   lane, registered as a gate.
9. **Group runs.** Should this lane register the four tests' group runs,
   or supply definitions to the session that built #513? Recommended:
   supply GR1 and GR2a to that session if it holds drafts; register
   otherwise. The same choice applies later to GR4's projection runs.
10. **Education source.** Fit ED1 on public CPS microdata rather than the
    PSID? Recommended: yes. It avoids a real-PSID step and matches the
    Microcosm frame's source.
11. **Who owns death alignment** between SM and the open-population lane's
    alignment layer? Recommended: SM.
12. **Approve a complete budget for the lane now?** Recommended: no.
    Approve the built-now first attempts and require the unpriced items in
    section 3.5 to be priced at S0.2.

The OASDI/HI split of the income tax on benefits is not on this list. It
is a statute-conformance fix to PE-US, which the coordinator routed to the
US and core hub, and under Max's standing rule such fixes need no ruling
even when they move aggregates. F1 reports PE-US's current reading beside
the fixed one until the fix lands.

## 11. Files read, exposure and disclosure

`EV` means `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909`.
Repository paths are at `origin/master` `1e739d32` unless noted.

**Read in this run:**
- *Instructions and plans:* `EV/RESTRICTED-FILES.md` (first, in full);
  the repository's and the parent folder's `CLAUDE.md`; `CONTRIBUTING.md`;
  `docs/parity-ledger.md`; `EV/trackb-design-20260928.md` (sections 1–10);
  `EV/coordinator/parity-forecast-20261021.md`; `docs/plans/microcosm-start.md`
  (headings and the lines that mention mortality, education, groups,
  payroll and trust funds).
- *Registration 18:* `EV/acola-builder-brief-cleared-20260930.md` (cleared,
  SHA-256 `7ee9822d…`, verified); `EV/acola-build-20260930/stage1-lane-notes.md`;
  the registration text, as committed on branch `acola-reg18-build-20260930`
  at `docs/design/acola_registration18.md`; the branch's file list and
  merge base; a `git diff --stat` of the mechanism-L paths. The cleared
  code map's hash was verified; its body was not read.
- *Code:* `cola_track_a/mortality.py` (all); `engine/di_entitlement_rates.py`
  (all); `engine/di_entitlement.py` (lines 1–135 and 575–904);
  `engine/loop.py` (lines 116–140 and a search); `engine/steps.py`
  (lines 95–130); `engine/rng.py` (lines 20–34);
  `estimates/publication.py` (lines 1–260, 526–720 and a search);
  `estimates/ledgers.py` (lines 1–90, 829–1080);
  `estimates/uniform_cut_tabulation.py` (lines 1–330);
  `data/group_attributes_psid.py` (lines 1–160 and an outline);
  `cohorts/group_attributes.py` (lines 1–40 and an outline);
  `estimates/group_breakdown.py` (lines 1–120 and a search);
  `estimates/lifetime_measures.py` (lines 673–700 and a search);
  `baselines/tr2026_intermediate.py` (lines 1–160); `baselines/base.py`
  (lines 160–200); `data/tr2026.py` (lines 1–80); `data/life_table.py`
  (lines 1–40); `data/deaths.py` (lines 1–50); `bridge/policyengine_us.py`
  (lines 1–60); `track_b/README.md` (to the B2 section) and
  `track_b/gross_benefits.py` (outline); `cola_track_a/benefits.py`
  (lines 340–350 and a search); `claiming.py` (a search of
  `benefit_factor`); `pyproject.toml` (a search).
- *Errata:* `docs/errata/2026-10-11-delayed-credit-window.md` (lines 1–30).
- *Design documents:* `docs/design/covered_earnings_correction.md`
  (lines 1–60); `docs/design/nasi_projection_groups_posthoc.md`
  (lines 90–218); the headings of `docs/design/nasi_g1_group_attributes.md`
  and `docs/design/lifetime_measures.md`; `gates.yaml` (lines 5393–5411).
- *Run artifacts:* `runs/m2_pseudo_projection_v1.json` (its keys and
  scalar fields, and its provision and floor records);
  `runs/mortality_floors_v1.json` (its keys and string fields).
- *Outside the repository:* the PolicyEngine-US files named in section 2.3,
  `tax_unit_ss_combined_income_excess.py`, the parameters under
  `gov/irs/social_security/taxability/threshold/` and `.../rate/`, and
  `gov/ssa/revenue/oasdi_share_of_gross_ss.yaml` (local checkout
  `cae6fc26ce`); PolicyEngine/policyengine-us#6998 (its body);
  issue #113's body and comment index; the Cornell LII page for
  42 U.S.C. 401 (its statutory notes); web searches for the sources in
  section 4.2.
- *Executed:* `EV/mortality-groups-financing-20261021/tob_split_check.py`,
  which runs PE-US on three invented single filers and writes
  `tob_split_check.out.json`. No other model run was made.

**Not opened:** anything `EV/RESTRICTED-FILES.md` lists; the 2014 Trustees
Report pages and extracts in `data/external/`; the `m7-design` branch's
design; the stage-1 branch's Table V.C1 capture; any other session's
transcript; any PWBM, OACT solvency-provision or MINT policy-option page.
No real-PSID statistic was computed.

**Exposure, recorded for S0.1 and the coordinator:**
- `runs/m2_pseudo_projection_v1.json` and #113's body print a published
  DYNASIM3 analysis's baseline exhaustion year and its solvency-year
  changes for five provisions, one of them a rise in the full retirement
  age to 72. This run read them.
- `benchmarks/wall.md`, opened by a search, printed published DYNASIM
  winner-and-loser shares by marital status and sex for one reform
  package, CBO's trust-fund ratios for 2015 and 2016, CBO's projected
  beneficiary trajectory, and a frame-relative per-worker taxable-earnings
  benchmark. This run read those lines.
- Web-search summaries printed NCHS life expectancies for 2022, a
  published total of 2025 taxable earnings, NCHS decedent counts by
  education for 2022, and dated CBO figures on life-expectancy gaps by
  earnings.
- None of these is a Registration 18 comparator or a Trustees Report cost,
  income or balance rate. Neither repository file above was on the
  restricted list when this run read them. Both transcribe DYNASIM results
  of kinds the list's NASI section restricts for those comparisons'
  builders. The coordinator listed both on 21 October 2026, with #113's
  body, for the builders, forecasters and checkers of DYNASIM or Urban
  comparisons of exhaustion or solvency effects, any rise in the full
  retirement age or results by group, and recorded this session's
  exposure. This session may not build, forecast or check DYNASIM or Urban
  comparisons of exhaustion or solvency effects, any rise in the full
  retirement age, or results by group. Fresh unexposed lanes perform those
  roles for the affected comparisons.

**Read for revision 1 (23 October 2026):** the round-1 review
(`EV/mortality-groups-financing-20261021/review-r1-out.md`, Subfleet job
`20261021-103326-mgf-design-r1e`); `cola_track_a/runner.py` (lines
420–461); `cola_track_a/adapters.py` (lines 210–238);
`estimates/group_breakdown.py` (lines 1710–1715 and 1764–1767);
`cohorts/group_attributes.py` (lines 15–25); `data/life_table.py`
(lines 17–37); and PE-US's `income_tax.py` and
`income_tax_before_refundable_credits.py` (local checkout `cae6fc26ce`).
Nothing on the restricted list was opened, and no model was run.

**Read for revision 2 (23 October 2026):** the round-2 review
(`EV/mortality-groups-financing-20261021/review-r2-out.md`, Subfleet job
`20261023-062236-mgf-design-r2`). PSID use follows the project's
data-access record. No PSID file was opened, no PSID statistic was
computed, and no model was run.

## 12. Review item → where resolved (revision 1)

The round-1 review (GPT-6.1 Sol, hard tier) returned REVISE with one high,
seven medium and seven low findings. Each was checked against the code it
cites before it was applied.

| Finding | Severity | Resolution |
|---|---|---|
| 1. Conserving expected deaths does not preserve Track B's realized outcomes | High | §7.1 rule replaced with the review's text and its invented counterexample; B4's mortality, marital and DI checks rerun under a change-admission protocol frozen in advance; new condition `MORTALITY_CHANGE_UNADMITTED` (§8); question 4 (§10) revised |
| 2. "Now" included GR2's projection rows and F2's population integration | Medium | GR2 split into GR2a (closed cohort, now) and GR2b (projections, after Track B and the income lane); F2 split into F2a (arithmetic on invented inputs, now) and F2b (the frame's start year, after the Microcosm start). F3a narrowed to the start year. §3.1, §3.2, §3.3, §3.4 and §3.5 repriced: 92–144 d in all, 49–77 d now |
| 3. SM4 lacked payment, history and horizon dependencies | Medium | SM4's dependency cell replaced with the review's text; SM4 moved to the group after Track B and an admitted horizon (§3.4, §3.5) |
| 4. F1's counterfactuals must be Chapter 1 liability | Medium | Confirmed: PE-US's `income_tax` adds the net investment income tax (`income_tax_before_refundable_credits.py:18–27`). §2.3 says so and notes the executed check's filers stay below that tax's threshold; F1's deliverable, verification, stage rule and invariants exclude non-Chapter-1 taxes and add a case above the threshold |
| 5. S0.2 could expose future comparison builders | Medium | S0.2 moved to a validation-only source auditor; builders receive only scanned definitions, access metadata and cleared inputs; exposed people do not build blind comparisons; affected comparisons are labeled post hoc; F5's openly specified baseline conformance distinguished (§3.1, §3.5, §4.1, §5.2, §5.4) |
| 6. The exposure disqualification was narrower than the restricted list | Medium | §11's conclusion replaced with the review's text |
| 7. SM3 needed an information-boundary rule | Medium | §5.2 adds the freeze of prediction origins and reference, interview and availability dates, with the group-attribute resolution as the motivating case; §5.4 SM3 and §3.2 follow; applied to ED2 and F3b |
| 8. New post hoc group cells should not get a blind-test status | Medium | §3.3 and §5.4 GR3 replaced with the review's text |
| 9. Which registered steps compute PSID statistics | Low | §4.3 replaced with the review's text |
| 10. "Non-disabled" named the wrong mask | Low | §2.1 now says non-DI-origin and cites the mask (`engine/di_entitlement.py:815–821`) |
| 11. The life-table closing rule was undisclosed | Low | §2.1 discloses the builder-default constant-terminal-q rule |
| 12. Quote verification is not byte for byte | Low | §3.1 GR1 and §6 now say quotes match after whitespace normalization |
| 13. Citation scope | Low | §2.1 adds the runner and adapter citations and narrows the absence claim; §2.2 says there is no dedicated schooling slot |
| 14. Lane M's earliest completion | Low | §3.5 gives working-day dates for both lanes, recomputed for the new lane F chain |
| 15. "Six rows" should be five | Low | Preamble corrected |

## 13. Review item → where resolved (revision 2)

The round-2 review (GPT-6.1 Sol, hard tier, at `7955f280`) found all
fifteen round-1 findings resolved and section 12's account accurate. It
returned REVISE with two new medium and two low findings:

| Finding | Severity | Resolution |
|---|---|---|
| 1. Mortality change admission stopped at B4 | Medium | §7.1 now freezes a change-admission protocol naming every affected admission and reruns B4's checks, J's joint payment, recipient-denominator and survivor-pathway checks, and the affected timing checks; earlier J or B7 evidence does not transfer. The review's second invented case (equal deaths, different payments) is added. `MORTALITY_CHANGE_UNADMITTED` (§8) now covers any required check |
| 2. Deferred projection group cells had no registered run | Medium | New milestone GR4 (3–5 d), the deferred group runs on registered projections, with its own frozen inputs and registration; GR3 is the early phase. §3.1, §3.2, §3.3, §3.4, §3.5, §8 and §10 updated; the total is now 95–149 d |
| 3. The monthly-calendar row omitted two consumers | Low | §7.1's I row now lists F3b, F5, SM4 and GR2b |
| 4. Post-DI conservation needed the clipping qualification | Low | §6's invariant now holds up to a logged clipping residual, and explains why a feasible cell can fall short |

The round-3 review (GPT-6.1 Sol, hard tier, at `24e020f3`) found all four
resolved, round 1's fifteen resolutions intact and the arithmetic correct,
and returned **APPROVE**. Its one low finding, that three group-scope
references ended at GR3, is applied with its exact replacements (§3.1
S0.1, §4.2 and §6 now say GR1 to GR4).

**PSID use.** PSID use follows the project's data-access record. The
PSID rules in section 4.3 apply unchanged.

[i42]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42
[i113]: https://github.com/PolicyEngine/microcosm-dynamics/issues/113
[i403]: https://github.com/PolicyEngine/microcosm-dynamics/issues/403
[pr219]: https://github.com/PolicyEngine/microcosm-dynamics/pull/219
[pr513]: https://github.com/PolicyEngine/microcosm-dynamics/pull/513
[pr530]: https://github.com/PolicyEngine/microcosm-dynamics/pull/530
[pr532]: https://github.com/PolicyEngine/microcosm-dynamics/pull/532
[reg18]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-5919983573
