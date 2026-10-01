# UK State Pension dynamics: plan for the triple lock costing

**Status:** proposal, 1 October 2026. The rulings it needs are listed under [Decisions needed](#decisions-needed). Tracking issue: [PolicyEngine/microcosm-dynamics#501](https://github.com/PolicyEngine/microcosm-dynamics/issues/501).

**Driving use case:** [PolicyEngine/uk-triple-lock](https://github.com/PolicyEngine/uk-triple-lock), the costing of the Prime Minister's plan to adjust the triple lock from April 2030 (the "Burnham plan"), with DWP's published £15bn as a single-path comparator.

## Summary

PolicyEngine UK's basic plus new State Pension bill is 12.8% below DWP's in 2026-27 and 23.3% below in 2030-31. This plan projects the UK State Pension population and its entitlements to 2050-51 and hands PolicyEngine UK a per-year input file that every uprating path can run on.

- **The comparator.** uk-triple-lock's expected gross saving from the Burnham plan in 2039-40 is £8.41bn, a weighted mean over 198 full model runs. DWP's £15bn is a single-path comparator from its Pensim3 dynamic microsimulation, on a path DWP has not published. An expected value and one path are different quantities, so this plan compares the £15bn only with single-path runs (R3). Our central run's basic plus new State Pension bill in 2039-40 is £169.6bn. Scaling the OBR's July 2026 long-term path by the OBR's GDP path gives £281.2bn for all State Pension.
- **Verified contributors.** The Enhanced FRS holds survey ages fixed (top-coded at 80) and adds no new pensioners; policyengine-uk pays £0 to anyone reaching State Pension age after the survey year; uk-triple-lock pins State Pension types; and nobody abroad is modelled. Each is verified in code. Their sizes have not been isolated by runs, and this plan's decomposition does that.
- **Phase 1 (recommended first).** Reweight the survey's fixed age slots each year to ONS 2024-based single-age projections. Give each slot the entitlement of the birth cohort it represents that year, from a cohort entitlement model that runs Stat-Xplore's March 2026 stock forward with mortality, State Pension age by date of birth, qualifying-year accrual to the transitional rate and protected payments, migration, and a country-of-residence stock with frozen and uprated pensions. Deliver the result as a path-independent sidecar that PolicyEngine UK pins per year. Pensioners abroad run through the engine as a second, synthetic dataset built only from published aggregates.
- **Phase 2.** Person-level trajectories (ageing, death, migration, widowhood, labour histories) emit version 2 of the same contract and replace the cohort layer only if they beat it on held-out facts.
- **Engine.** Seven changes in policyengine-uk. The largest is a per-year flat-rate share and an add-on base grown by an uprating index, so entitlements can differ by year while each path's uprating still moves amounts. It consumes the open State Pension pull requests #1899, #1904, #1922 and #1939 and issue #1941, and it needs every horizon-bound builder extended past 2039.
- **Benchmarks.** Four gates to be pre-registered (DWP Spring 2026 caseloads and spending by type in 2030-31, a held-out Stat-Xplore accrual check, and an abroad backcast); registered comparisons with the OBR's July 2026 path, with DWP's forecast for each year to 2029-30, and with DWP's £15bn and £50bn as a single-path comparator; and diagnostics.
- **Cost and time (estimates).** Phase 1: about 26-41 agent-days and 10.5-14.5 human review days; 4-7 weeks elapsed if rulings and upstream merges come promptly, 8-12 if the gate ceremony stalls. Phase 2: a further 25-38 agent-days for the version that needs no licensed data, and 12-20 more for the licensed-panel version after data access.
- **The expected-value build on Phase 1.** About 456 PolicyEngine UK path jobs to 2049-50, estimated at 70-140 seconds and 2-4 GB each: 3-6 hours on three workers.

## Why

### The figures

| Figure | Value | Kind |
|---|---|---|
| uk-triple-lock expected gross saving, 2039-40 | £8.411bn (standard error £0.042bn); net £5.392bn | weighted mean of 198 full model runs ([results](https://github.com/PolicyEngine/uk-triple-lock/blob/f6f5505e6f1b734f03b5e75170267fea4c81b887/data/results.json)) |
| Same, OBR central path alone | £0.659bn gross | model run |
| Central run's basic plus new State Pension bill, 2039-40 | £169.63bn (basic £113.44bn, new £56.19bn) | model run |
| DWP saving from the adjusted triple lock | £15bn (2039-40) and £50bn (2049-50) nominal; £11bn and £30bn in 2025-26 prices; rounded to £1bn | single-path comparator: Pensim3, one path, Great Britain ([DWP, 29 September 2026](https://www.gov.uk/government/publications/state-pension-uprating-analysis-2026/state-pension-uprating)) |
| OBR all-State Pension spending, 2039-40 and 2049-50 | 5.4379% and 6.0852% of GDP; £281.2bn and £459.2bn | published share ([OBR, July 2026](https://obr.uk/frs/fiscal-risks-and-sustainability-july-2026/), chart 3.11); cash derived with the OBR's own GDP path |
| Basic plus new on OBR-based numbers, 2039-40 | £249.3-281.2bn | derived bounds; the OBR does not split by type. Upper bound: all State Pension. Lower bound: the basic plus new share stays at its 2030-31 DWP value of 88.65%; it has risen every year since 2024-25 |
| Model against DWP, basic plus new | £114.3bn against £131.0bn in 2026-27 (−12.8%); £122.9bn against £160.2bn (−23.3%) in 2030-31 | model runs against [DWP Spring 2026](https://www.gov.uk/government/publications/benefit-expenditure-and-caseload-tables-2026) (DWP's rows include pensioners abroad) |

uk-triple-lock [#13](https://github.com/PolicyEngine/uk-triple-lock/issues/13) estimates how much a smaller State Pension bill and the missing population move the costing. Its own heading calls those splits "estimates, not model runs", and the independent check on that issue says the bill and driver splits "need a reproducible projection or counterfactual runs". This plan produces those runs. The like-for-like comparison with DWP's single-path £15bn is R3.

The statutory floor for the basic and full new State Pension rates is earnings growth ([Social Security Administration Act 1992 s.150A](https://www.legislation.gov.uk/ukpga/1992/5/section/150A)). The triple lock and its April 2030 adjustment are policy.

### What the static survey misses

Each mechanism is verified in code at the commits linked; the figures come from the sources named.

1. **Ages never advance.** `age` is an input with no formula; survey ages are top-coded at 80.
2. **Weights grow by one total-population index.** From 2024 to 2039 that index grows 6.5%, while the ONS projects GB's population at legislated State Pension age to grow 22.9%.
3. **New pensioners get £0.** `basic_state_pension` and `new_state_pension` read `state_pension_reported` only at the dataset's first year ([basic_state_pension.py](https://github.com/PolicyEngine/policyengine-uk/blob/44240bd8d7d7e97f2980ccc8134e76e61541966f/policyengine_uk/variables/gov/dwp/basic_state_pension.py#L15-L25)), so anyone reaching State Pension age later has no award.
4. **Types are pinned.** uk-triple-lock holds each person's survey-year type, so the shift from basic to new State Pension never happens. DWP forecasts new State Pension recipients rising from 41.9% of the basic-plus-new caseload in 2026-27 to 56.8% in 2030-31.
5. **No pensioners abroad.** 1,093,218 recipients lived abroad in March 2026 (Stat-Xplore), with £5.63bn paid outside the UK in 2025-26 (DWP).
6. **The model covers the UK; the benchmarks cover GB.** The model includes Northern Ireland; DWP's and the OBR's figures cover Great Britain plus pensioners abroad.

### Pensioners abroad

GOV.UK's rule: "Your State Pension will only increase each year if you live in" the EEA, Gibraltar, Switzerland or "countries that have a social security agreement with the UK (but you cannot get increases in Canada or New Zealand)" ([GOV.UK](https://www.gov.uk/state-pension-if-you-retire-abroad)).

The legal basis has three layers.

- **Payability.** [Social Security Contributions and Benefits Act 1992 s.113](https://www.legislation.gov.uk/ukpga/1992/4/section/113) disqualifies a person absent from Great Britain from benefits under that Act, and the Social Security Benefit (Persons Abroad) Regulations 1975 (SI 1975/563) reg 4 lifts that for retirement pensions. The new State Pension, under Pensions Act 2014 Part 1, falls outside s.113.
- **The freeze.** [SI 1975/563 reg 5](https://www.legislation.gov.uk/uksi/1975/563/regulation/5) withholds each up-rating of a pre-2016 retirement pension (people who reached State Pension age before 6 April 2016) from a recipient not ordinarily resident in Great Britain immediately before the up-rating date. For the new State Pension it is [Pensions Act 2014 s.20](https://www.legislation.gov.uk/ukpga/2014/19/section/20) with [SI 2015/173 reg 21](https://www.legislation.gov.uk/uksi/2015/173/regulation/21); the protected payment's increase is frozen too. Each year's up-rating regulations switch both on ([SI 2026/218](https://www.legislation.gov.uk/uksi/2026/218/made) reg 3).
- **The exceptions.** Reciprocal orders under Social Security Administration Act 1992 s.179, the Withdrawal Agreement (articles 30-31), the UK-EU Trade and Cooperation Agreement's Protocol on Social Security Coordination, and the conventions with Switzerland and with Iceland, Liechtenstein and Norway.

In March 2026, Stat-Xplore counted 419,562 recipients resident in frozen-rate countries across all residence categories (419,386 within the Abroad residence group), at a mean of £66.69 a week. Australia, Canada and New Zealand hold 355,128 of them (84.6%). By inference from reg 21, a legislated change to the uprating rule changes nothing for people already frozen; it changes the starting amount of anyone who reaches State Pension age in, or moves to, a frozen country during the horizon.

## Scope

**In scope.** The UK-resident State Pension population and its entitlements, and UK State Pension recipients abroad, from 2025-26 to 2050-51:

- mortality, from ONS 2024-based projections;
- State Pension age by date of birth, under the law and under the OBR's assumed timetable;
- qualifying-year accrual to new State Pension starting amounts, including the transitional rate and protected payments;
- pre-2016 basic and additional State Pension;
- emigration and immigration at and near State Pension age;
- country of residence abroad, with a frozen or uprated status and the year a pension froze;
- an artifact PolicyEngine UK loads, and the engine changes it needs;
- the benchmarks and gates that score it, and what the uk-triple-lock expected-value build needs to run on it.

**Not in scope.**

- Behavioural responses: claiming, deferral, labour supply and migration do not respond to the uprating rule or the macro path.
- Labour-market, earnings, private-pension and household dynamics in Phase 1. Non-pension incomes stay with the same-age records.
- Re-encoding any rule in Microcosm or microcosm-dynamics. State Pension age, the transitional rate and the frozen-country rule live in policyengine-uk (or [rulespec-uk](https://github.com/TheAxiomFoundation/rulespec-uk)), called through a bridge.
- Any pound figure computed outside a PolicyEngine UK run. Pensioners abroad run through the engine.
- UK tax on State Pension paid abroad.
- Edits to uk-triple-lock. Its maintainers own its plan and code; this plan specifies what the consumer needs.

## Relation to existing work

| Work | What it covers | Boundary |
|---|---|---|
| uk-triple-lock's proposed interim fix ([#13](https://github.com/PolicyEngine/uk-triple-lock/issues/13): "age the survey and put new pensioners on the new State Pension") | a static ageing of the survey | if it lands first, it is a comparator for the population-and-date-of-birth layer of Phase 1's decomposition. By construction it gives 2030s retirees the amounts of today's same-age survey records. This plan replaces it when gated |
| [microcosm#1069](https://github.com/PolicyEngine/microcosm/issues/1069) | calibrates the UK cross-section's State Pension, Pension Credit and contributions to resident administrative facts; migrates Microcosm off the State Pension age parameters that #1899 deletes | this plan is its deferred "Multi-year runs, to be a separate piece". Phase 1 starts from its calibrated base and duplicates none of its rows |
| microcosm static aging ([#957](https://github.com/PolicyEngine/microcosm/pull/957), [#333](https://github.com/PolicyEngine/microcosm/issues/333)) | reweights one base cross-section per year to demographic cells; US only; "the package does not yet include a UK projection reader" | Phase 1 adds the UK reader and a UK annual builder |
| microcosm-dynamics UK layer ([#139](https://github.com/PolicyEngine/microcosm-dynamics/pull/139), [ADR 0002](https://github.com/PolicyEngine/microcosm-dynamics/blob/dd222b9af926c773a0f92732e2d08be507793378/docs/adr/0002-uk-extension-ukhls.md)) | a port of a UK panel pipeline; "carries **no gate certification**"; ADR 0002 is Proposed pending [microcosm#148](https://github.com/PolicyEngine/microcosm/issues/148) | not reused: it fixes State Pension age at 66, uses placeholder mortality rates by default (its ONS loader holds the latest period table fixed), sets net migration to zero at 65+, and deletes emigrants. Left untouched |
| policyengine-uk [#1899](https://github.com/PolicyEngine/policyengine-uk/pull/1899), [#1904](https://github.com/PolicyEngine/policyengine-uk/pull/1904), [#1922](https://github.com/PolicyEngine/policyengine-uk/pull/1922), [#1939](https://github.com/PolicyEngine/policyengine-uk/pull/1939), [#1941](https://github.com/PolicyEngine/policyengine-uk/issues/1941) | State Pension age by date of birth; a `date_of_birth` input (in a pull request titled for child cutoffs); the additional State Pension double count; the triple lock from statutory inputs; CPI uprating of add-ons (an issue) | consumed, never duplicated |
| policyengine-uk [#1929](https://github.com/PolicyEngine/policyengine-uk/issues/1929) | the engine-side statement of this problem | related; it closes from the data side when Phase 1 lands |
| [rulespec-uk#369](https://github.com/TheAxiomFoundation/rulespec-uk/issues/369) | the Axiom encoding of the State Pension age timetable | the differential check for the engine's State Pension age |
| [chronicle#305](https://github.com/PolicyEngine/chronicle/pull/305) | GB-resident State Pension facts, DWP Spring 2026 tables, and DfC Northern Ireland State Pension statistics for May 2026 | excludes pensioners abroad at source; Phase 1 adds the abroad, projection and long-term packages |
| The live US Social Security tracks in this repo | US only; none touch `uk/`, the engine loop, `gates.yaml` or mortality | the UK gate goes in its own file; no edits in place to `engine/loop.py`, `engine/steps.py`, `gates.yaml` or committed `runs/*.json` |

## Design

### Architecture

| Id | Component | Repo and module | Produces |
|---|---|---|---|
| C1 | Base cross-section | microcosm UK build, with #1069's calibration, at about the Enhanced FRS's size (exact-count household selection) | a private single-year dataset |
| C2 | UK static aging, weights only | microcosm `microcosm.calibrate.static_aging`, with a new ONS 2024-based reader and a UK annual builder that maps no monetary series | per-year household weights |
| C3 | Cohort entitlement model | microcosm-dynamics, new `uk/state_pension/` and a policyengine-uk bridge | entitlement distributions per year, cohort, sex and residence; the abroad stock; a cell-level stock-flow ledger |
| C4 | Assignment and bundle writer | microcosm, next to the annual builder | the sidecar, the abroad dataset, a manifest and a scorecard |
| C5 | Engine contract | policyengine-uk: inputs E1-E4, horizon E5, guards E6-E7 | a loadable contract |
| C6 | Scoring and registration | microcosm-dynamics harness, a UK gate file, a registration, and ADR 0005 | gate verdicts |
| C7 | Consumer | uk-triple-lock, by its maintainers | results by scope |
| C8 | Source packages | chronicle | pinned facts |

The placement follows the repo boundary recorded on [microcosm-dynamics#412](https://github.com/PolicyEngine/microcosm-dynamics/issues/412) (open): kernels, transition models, generators and gates in microcosm-dynamics; the population model and structural deltas in microcosm. C4's rank assignment is a generator; decision 1 places it in microcosm, next to the annual builder that writes the records it assigns to.

```
FRS 2024-25 ─► C1 base (#1069 calibration, ~53k households)
                 │
ONS NPP 2024 ───►├─► C2 household weights per year (demographic cells only)
                 │
Stat-Xplore Mar-26 stock ─┐
ONS qx and migration ─────┼─► C3 cohort entitlement model ─► entitlement distributions,
DWP and GAD aggregates ───┘      ▲ (State Pension age, transitional rate and    abroad stock
                                 │   frozen-country rule through the engine bridge)
                 C4 assignment ◄─┘─► sidecar + abroad dataset + manifest + scorecard
                                            │
policyengine-uk (E1-E7) ─────────────────────┴─► uk-triple-lock expected-value build:
  base loads as today, so each path's uprating applies; the sidecar is pinned per year;
  the abroad dataset runs under each rule; totals by GB, Northern Ireland and abroad
```

### Population and mortality

- **Weights.** C2 reads the ONS 2024-based national population projections ([ONS, released 28 April 2026](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections/bulletins/nationalpopulationprojections/2024based)): single ages 0-104 and sex, by year to 2124, for each UK nation. Cells are single ages 60-89 by sex for GB, 90+ pooled, five-year bands below 60, and Northern Ireland separately.
- **Doctrine.** Survey weights carry demographics only: in projected years no program count or amount is a weight target for survey records ([microcosm#333](https://github.com/PolicyEngine/microcosm/issues/333)). The abroad dataset is the exception by construction. Its population is defined by receipt, so its March 2026 weights equal Stat-Xplore's caseload as an initial condition, and every later year's weight is C3's prediction, scored by gates G1 and G4. Its cells are aggregate cohorts whose per-year weights are survivor counts; they make no claim about individual trajectories.
- **Anchoring.** The base year's weights equal the base dataset's weights. Each later year's target for a cell is the base's weighted count times the ONS growth of that cell, with a cap on weight ratios. ONS levels are reported beside the targets as a diagnostic.
- **Fiscal years.** The growth for fiscal year Y uses 0.75 × mid-Y + 0.25 × mid-(Y+1), because PolicyEngine UK reads age at 6 October under #1899. This is a computed target, declared on the Microcosm side.
- **The age-cell trap.** Static aging matches cells by exact equality, and the UK build stores drawn ages 80-97 for the top-coded tail. The build writes an explicit age-cell column.
- **No monetary series.** C2 maps no monetary series, a deliberate departure from static aging's factor step: factors would fix one macro path into every job. PolicyEngine UK inputs uprated by a national total will therefore not match that total under age-reweighted weights, and the scorecard reports each such series against its index.
- **Mortality.** C3 uses the projections' own mid-year death rates (`Mortality_assumptions`, ages to 125), which match the deaths behind C2's totals and close the gap above age 100 that the life tables leave. microcosm-dynamics' certified mortality step has no calendar-year dimension, so C3 adds a new year-indexed class and leaves the engine's step untouched.
- **Variants.** The principal projection is the baseline. Zero net migration and the low and high life-expectancy variants are sensitivities, each its own artifact vintage. Across the principal and the 13 variants, the UK population aged 67+ in mid-2039 ranges from 15.10m to 15.41m, around a principal of 15.24m.
- **Pensioners abroad** take GB mortality, as the Government Actuary does when it runs off overseas basic State Pension as a closed population. This is an assumption, tested by the abroad backcast (gate G4).

### State Pension age by date of birth

- **The law.** The timetable is [Pensions Act 1995 Schedule 4 paragraph 1](https://www.legislation.gov.uk/ukpga/1995/26/schedule/4), as amended by the Pensions Acts 2007, 2011 and 2014 (the rise to 67 is [Pensions Act 2014 s.26](https://www.legislation.gov.uk/ukpga/2014/19/section/26)).
  - 66 for births from 6 October 1954 to 5 April 1960;
  - 66 and 1 to 11 months for births from 6 April 1960 to 5 March 1961, reaching State Pension age between 6 May 2026 and 5 February 2028;
  - 67 for births from 6 March 1961 to 5 April 1977;
  - fixed dates from 6 May 2044 to 6 March 2046 for births from 6 April 1977 to 5 April 1978;
  - 68 for births after 5 April 1978.

  Northern Ireland has parallel provisions: the [Pensions (Northern Ireland) Order 1995 Schedule 2](https://www.legislation.gov.uk/nisi/1995/3213/schedule/2) for State Pension age and the [Pensions Act (Northern Ireland) 2015](https://www.legislation.gov.uk/nia/2015/5/contents) Part 1 for the new State Pension.
- **The engine computes it.** policyengine-uk [#1899](https://github.com/PolicyEngine/policyengine-uk/pull/1899) encodes the timetable. The sidecar fixes each record's `months_since_last_birthday` once, so the engine's age and type are stable for a given record and year. C3 asks the engine for State Pension age on a grid of birth months through the bridge. The check on the engine is a differential test against rulespec-uk#369's encoding; this repo adds no State Pension age implementation.
- **Two timetables.** The baseline is the law. The OBR's July 2026 projections assume 68 is reached over 2037-39, which the Treasury confirmed as "the Government's current policy position" before the July 2026 change of government. On 22 September 2026 DWP answered (HL3233, HL3234) that "The first chance this government will have to consider this issue will be via the State Pension age Review"; that review has published no report or decision as of 30 September 2026, and [Pensions Act 2014 s.27](https://www.legislation.gov.uk/ukpga/2014/19/section/27) sets the cycle for its report.
- **The OBR timetable is a registered scenario**, run as a reform of #1899's date-of-birth parameters with its own sidecar vintage, because State Pension age timing changes accrual windows and award years. The OBR publishes years only, so the date-of-birth mapping is an assumption fixed at registration. It matters in 2039-40: GB's population aged 68+ in mid-2039 is 0.80m (5.4%) below its population aged 67+.

### Accrual, new State Pension amounts and protected payments

**The law** ([Pensions Act 2014 Part 1](https://www.legislation.gov.uk/ukpga/2014/19/part/1)):

- 35 qualifying years give the full rate (£241.30 a week in 2026-27); fewer give years/35 of it; fewer than 10 give nothing ([SI 2015/173 reg 13](https://www.legislation.gov.uk/uksi/2015/173/regulation/13)).
- Anyone with at least one qualifying year before 6 April 2016 and at least 10 in all gets the transitional rate ([s.4](https://www.legislation.gov.uk/ukpga/2014/19/section/4) and [Schedule 1](https://www.legislation.gov.uk/ukpga/2014/19/schedule/1)). The foundation amount F is the higher of the old-rules amount and the new-rules amount (pre-2016 years/35 × £155.65, less the contracted-out deduction).
- In closed form, checked against a literal implementation of Schedule 1 on 216,128 cases (the check ships with WP2's tests):
  - if F ≤ £155.65, the starting rate is the full rate at State Pension age × min(1, F/155.65 + min(post-2016 years, 35)/35);
  - otherwise the starting rate is the full rate plus the excess (F − £155.65), revalued by prices, and post-2016 years add nothing.
- The excess over the full rate is the protected payment. After State Pension age the part up to the full rate rises with the full rate and the excess by the prices percentage (3.8% in 2026-27, against 4.8% on the full rate).

Two consequences shape the design. A rule that changes how the full rate is uprated changes every new transitional pensioner's starting amount, so entitlements must enter as a share of the full rate. And, by inference, nearly every new pensioner to 2050 has pre-2016 years (anyone whose working life began before 6 April 2016), so the transitional rate governs the whole horizon.

**The data problem.** No public source gives qualifying years or 2016 starting amounts for people below State Pension age. DWP stopped publishing qualifying-year statistics in 2013. The Lifetime Labour Market Database needs a DWP sponsor and DWP premises; ADR UK's page for RAPID says its access instructions will appear "soon". Understanding Society and ELSA have work histories under UK Data Service licences. ELSA also offers consent-based linkage to National Insurance records under restricted access; no linked study is listed by the UK Data Service, and whether Understanding Society offers an equivalent was not checked.

**What exists publicly**, and is enough for a cohort model:

- Stat-Xplore's new State Pension awards as a share of the full rate (the total award, including any protected payment and extra State Pension, divided by the full rate), by single age, sex, protected payment and residence, quarterly from May 2018. In March 2026, 60.7% of GB new State Pension recipients were at or above the full rate; by single age the share rises from 46.3% (men aged 74) to 74.8% (age 66). A group below 75% of the full rate stays at 4-7% of each cohort. 20.2% of all new State Pension recipients receive a protected payment (21.1% in GB).
- DWP's protected-payment inflows at State Pension age to 2030-31 (Autumn Budget 2025 forecast vintage).
- Written answers giving qualifying years by route (contributions, credits, both, none) by sex and age for 2011-12 and 2018-19.
- DWP's 2016 cohort projections of the full-rate share (81% in 2030, 84% in 2040, 87% in 2050), as a diagnostic.

**Phase 1 method: a cohort-cell accrual model** (the Government Actuary's approach, made distributional). Persons carry no histories.

- The pre-2016 share distribution by cohort and sex is estimated on State Pension age cohorts 2016-17 to 2022-23 (ages 69-74 in March 2026; State Pension age differed by sex and rose over 2016-20, so cohort and age are not one-to-one), after removing their short post-2016 accrual. For younger cohorts it is structural: years available from age 16, an attainment rate, and a contracted-out deduction that scales with contracted-out years, fitted to how the observed bands move across cohorts.
- Annual post-2016 attainment by age and sex comes from the written answers, with the ONS population as the denominator (an assumption, registered).
- The short-record tail is an explicit parameter per cohort; migrants arriving before State Pension age feed it.
- Deferral is not modelled; the Government Actuary assumes about 6% defer. It is a limitation and a diagnostic.
- State becomes money only inside the engine: C3 converts cohort states to a share and a protected payment by running PolicyEngine UK's transitional-rate formulas (E3) on its cell grid.
- **Held out:** State Pension age cohorts 2023-24 to 2025-26 (ages 66-68 in March 2026) are excluded from estimation and scored (gate G3).

**Phase 2 upgrade.** Person-level accrual: first from fitted propensities (no licensed data), then from Understanding Society, BHPS and ELSA work histories run through the engine's qualifying-year rules. Each merges only if it beats the incumbent on held-out facts. A DWP table of starting amounts or protected payments by cohort would improve either; requesting it is an outside send and so a decision.

### Pre-2016 pensioners

People who reached State Pension age before 6 April 2016 carry a basic State Pension share (30 qualifying years for the full £184.90 if they reached State Pension age from 2010) and an additional-pension base (SERPS, S2P and graduated retirement benefit). The initial state comes from Stat-Xplore's March 2026 stock by age, sex, category and amount band. The additional pension rises by CPI, the measure in use for the law's prices floor; the OBR's assumption that it is triple-locked after 2030-31 is used only in the OBR replication run, as an engine reform.

### Migration

- **UK residents.** ONS emigration by age and sex moves cells into the abroad stock; immigration adds to UK cells. The flows are small: the principal projection has 12,380 arrivals and 8,261 departures a year at ages 66+ (net +4,119), and the latest admin-based estimate for ages 65+ is about −2,000 net (year to December 2025, provisional, rounded to 1,000, excluding Irish nationals). C2's totals already embed the projection's net migration.
- **Entries to the abroad stock arise mainly at State Pension age**, from people who left the UK earlier in life. The stock itself is falling (1,189,015 in May 2018 to 1,093,218 in March 2026) while its new State Pension part grows (45,068 to 314,992). Following the Government Actuary's 2020 quinquennial review, new awards abroad are a ratio to new GB awards, by sex and frozen or uprated status, estimated from Stat-Xplore's abroad series.
- **Destinations** of new emigrants follow the recent mix of new State Pension recipients abroad, by country (an assumption).
- **The EU sunset.** The Trade and Cooperation Agreement's social security protocol ceases to apply fifteen years after the Agreement entered into force on 1 May 2021, so on 1 May 2036 (computed). A lapse would reach only people who moved to an EU state after 31 December 2020: the Withdrawal Agreement covers those in scope at that date for as long as their situation continues, and the Swiss and EEA-EFTA conventions have no sunset. Whether domestic savings would protect later increases is unresolved. The lapse is a scenario, run as an engine parameter reform that freezes only post-2020 movers to EU states.

### Pensioners abroad by country

- **Target source, verified.** DWP Stat-Xplore dataset `SP_New` ("State Pension - Data from May 2018"; 100% administrative; Accredited Official Statistics; 32 quarters to March 2026; next annual release 21 September 2027). Its Worldwide Geography folder holds 256 countries, a three-way Frozen Rate status (frozen, not frozen, unknown) and EEA, EU and Commonwealth groupings. It splits pre-2016 and new State Pension by country, with a mean weekly amount. The coverage label says "Great Britain", but the caseload includes "claimants residing abroad"; GB rows exclude Northern Ireland.
- **Cross-checks.** The March 2026 abroad caseload times its mean weekly amount gives £5,628m a year, against DWP's £5,629.1m paid outside the UK in 2025-26. The same calculation on the May points of 2018 to 2025 falls 1.4-7.5% below DWP's outturn, so the March agreement is partly coincidence, and DWP advises against estimating expenditure from Stat-Xplore means. DWP's 2024-25 spending by country splits overseas spending into £1,510m frozen and £3,842m non-frozen. A 194-row rule table built from GOV.UK's country list, published with WP5, agrees with Stat-Xplore's status on all 184 countries where both can be read.
- **Access.** Guest web access works and is the reproducible path: every extract the build uses is saved and pinned by sha256. The Open Data API needs a per-user key, and DWP's terms say "Your API key is for your own use only: please do not share it with others, or disseminate it on public platforms where other users or AI agents could access it", so the API is used only in a step its holder runs.
- **One definition.** The residence hierarchy at March 2026: Great Britain 12,207,303; Abroad 1,093,218; Unknown 7,278. Within Abroad: frozen 419,386; not frozen 657,806; unknown status 16,026. The country-code cut gives slightly different totals, so the project fixes the residence hierarchy. Unknown residence is carried as its own cell.
- **What the model carries.** Each abroad cell has a country (or country group), a frozen status read from the engine's country parameter (E4), and either a frozen weekly amount (frozen before the base year) or the year it freezes, its share and its add-on base. No public table gives the date or rate at which existing pensions froze, so frozen amounts come from Stat-Xplore means and amount bands by country and category. Cell weights are stocks at 31 March; fiscal-year comparisons use the mean of the opening and closing stocks.
- **An open legal point.** For someone already abroad at State Pension age, a starting amount at that year's rates rests on reading Schedule 1 paragraph 6 and SI 2015/173 reg 21; DWP's guidance states the rule for the pre-2016 system only. Decision 8 asks DWP to confirm it.
- **Crown Dependencies** (about 18,400 uprated cases) sit inside the abroad figures and stay in the abroad dataset with their own codes. 497 DWP-administered Northern Ireland cases appear in Stat-Xplore's country-code cut. WP7 checks where the residence hierarchy places them, and they enter the abroad dataset only if they fall in its Abroad group, so A3 stays exact.

### Targets and predictions

| Quantity | Role |
|---|---|
| ONS population by single age, sex and nation | weight target (demographic) |
| DWP and Stat-Xplore State Pension caseloads by age and type, base year | base-year targets, owned by #1069 |
| Stat-Xplore March 2026 stock by age, sex, residence, country (or country group) and amount band | initial condition of C3 |
| Stat-Xplore full-rate bands, cohorts 2016-17 to 2022-23 | estimation data |
| The same, cohorts 2023-24 to 2025-26 | held out and scored |
| DWP Spring 2026 caseloads and spending by type to 2030-31 | predictions, scored |
| OBR July 2026 path; DWP £15bn and £50bn (a single-path comparator, used only in R3) | registered comparisons |
| FRS-reported State Pension | rank predictor in C4 only; never a target |
| HBAI pensioner poverty | holdout only |

### Assigning cohort states to records

For each year after the base, each age slot represents the cohort born that many years earlier. Within each age, sex and nation, records are ranked by a predictor (their own reported share of the full rate if they were over State Pension age in the base; otherwise earnings, self-employment and benefit indicators), and the weighted ranks map to the cohort's entitlement distribution. This keeps the link between a low State Pension and low other income that drives Pension Credit.

This is an imputation and needs an explicit ruling (decision 2). Its invariant: for every year after the base, and every age, sex and nation, the weighted distribution of assigned states equals C3's distribution exactly. In the base year each record keeps its own reported state, and the scorecard reports the change in the State Pension distribution from the base year to the first projected year as a seam diagnostic. A record's rows across years are age slots holding different cohorts; they describe no individual trajectory. Reported State Pension is used only as a predictor here, and the assigned value never re-enters a build stage.

## Output artifact and PolicyEngine UK interface

### Why a sidecar

uk-triple-lock computes 13 fiscal years inside one simulation per policy, on one fixed record set, with every monetary input uprated by that path's own macro series. Any artifact holding projected money fixes one uprating path into all 199 path jobs.

| Form | Keeps each path's uprating? | Verdict |
|---|---|---|
| One single-year file per year (the US annual export) | no: monetary inputs are pre-scaled on one path | rejected for the expected-value build |
| A multi-year dataset | no: loaded as given, with no uprating | rejected |
| A sidecar on a single-year base | yes: the base loads as today, and the sidecar holds no path-dependent money (shares of the full rate, and base-year pounds the engine grows by each path's index) | **adopted** |

### The bundle (contract `uk_sp_projection.v1`)

| File | Visibility | Content |
|---|---|---|
| `base.h5` | private | the single-year base, loaded exactly as today |
| `slots.h5` | private | per year: household weights (0 = absent); per person: `months_since_last_birthday`, fixed per record (or, once #1904 merges, a per-year `date_of_birth` consistent with the slot's fixed age on 6 October), `state_pension_flat_share` in [0, 1], and `state_pension_addon_weekly_base` in base-year pounds (additional pension and graduated retirement benefit for the old system; protected payment for the new). Years from the base to 2050-51 |
| `abroad.h5`, `abroad.years.h5` | publishable on ruling: built only from published aggregates, with no survey records | single-person cohort-cell households with residence country, frozen amount or freeze year, share and add-on base; per-year weights and `age`, with a fixed date of birth, because these cells are cohorts |
| `manifest.json` | private, with a public aggregate copy | contract version, base name and sha256, sidecar sha256, producer commits, environment lock, projection variant, State Pension age timetable, Stat-Xplore extract hashes, years, GB and Northern Ireland flags |
| `scorecard.csv` | public | aggregates only, against every benchmark below, with vintages |

The sidecar is independent of path and rule. It is built once per vintage and shared by every path job. uk-triple-lock loads datasets only by name through policyengine.py's managed loader, so the bundle also needs a policyengine.py release that registers the base, sidecar and abroad datasets by name and sha256 and pins the engine release carrying the changes below (WP8b).

### Engine changes (policyengine-uk)

| Id | Change | Why |
|---|---|---|
| E1 | `state_pension_flat_share` (person, year), read at the period by `basic_state_pension` and `new_state_pension`; its default reproduces today's behaviour | entitlement can differ by year: new cohorts, slots that change cohort, widowhood |
| E2 | `state_pension_addon_weekly_base` (person, year) in base-year prices; `additional_state_pension` = base × the ratio of an add-on uprating index, which is a parameter: by default the September CPI series that #1939 adds (with #1941) | add-ons rise each April by the previous September's CPI under both rules, per path; new cohorts' protected payments exist; the OBR replication run can set the index to the triple lock |
| E3 | transitional-rate formulas (Schedule 1 closed form) from foundation share, protected excess, post-2016 years and total qualifying years (the 10-year minimum) | the producer's state-to-share step is a real engine evaluation |
| E4 | a dated parameter listing the countries where the State Pension is uprated (the GOV.UK list, each entry with its legal instrument), a `state_pension_residence_country` input, and a formula giving frozen status from them; `state_pension_freeze_year` and `state_pension_frozen_weekly_amount` inputs; flat rates and the add-on index read at the freeze year when frozen | the frozen-country rule lives in the engine; the Trade and Cooperation Agreement lapse and an "unfreeze" are reforms of the parameter |
| E5 | every horizon-bound builder to at least 2051: the index loop (it stops at 2039, [create_economic_assumption_indices.py](https://github.com/PolicyEngine/policyengine-uk/blob/44240bd8d7d7e97f2980ccc8134e76e61541966f/policyengine_uk/parameters/gov/economic_assumptions/create_economic_assumption_indices.py#L41)), fiscal-year conversion, the triple-lock series (or #1939's), private-pension uprating and dataset extension, with a test that every index and every parameter uprated by one changes in every year to 2051 | a 2049-50 horizon. Work to extend the index loop has started without a pull request and needs an owner (decision 4) |
| E6 | consume microcosm#1069's guard against datasets that carry a `state_pension` column | a column of that name overrides the formula in every year |
| E7 | a contract version and a fail-closed applier that checks variables, ids, order and years, then pins inputs before any calculation | the engine skips unknown dataset columns silently, so a sidecar on an old engine would be ignored |

### How each uprating path still changes amounts

| Person-year | Engine amount | Moves with the rule? | Moves with the path? |
|---|---|---|---|
| UK resident, new or basic | share × full rate(Y) | yes | yes |
| UK resident reaching State Pension age in year S | share × full rate(S) at award, then full rate(Y) | yes, including the starting amount | yes |
| Add-on (additional pension, protected payment) | base × add-on index(Y)/index(base) | no: both rules use CPI, the measure for the law's prices floor | yes |
| Abroad, uprated | as a UK resident | yes | yes |
| Abroad, frozen before the base | frozen amount | no | no |
| Abroad, freezing in year e | share × full rate(e) + add-on at e, fixed after e | yes | yes |
| Household with no recipient | no State Pension | no | incomes follow the path |

Only three formulas read the flat-rate parameters on policyengine-uk main, so households without a recipient have identical taxes, benefits and net income under both rules.

### Pensioners abroad in the engine

Each path job loads the abroad dataset under the triple lock and the plan, with the same scenario and flat rates, and reads only its State Pension variables. Its tax and means tests are never summed, which matches DWP's gross spending concept. A separate simulation keeps abroad households out of HBAI, poverty and decile groupings, keeps the survey sidecar private and the abroad file publishable, and costs two small builds per job.

### Invariants (property and differential tests)

| Id | Invariant |
|---|---|
| I1 | with no contract inputs, every variable equals the previous release on the Enhanced FRS |
| I2 | share in [0, 1]; components non-negative; State Pension non-decreasing in share and in each flat rate |
| I3 | the closed-form transitional rate equals the literal Schedule 1 steps |
| I4 | for uprated recipients, flat amounts under two rules are in the ratio of their full rates; add-ons are identical across rules |
| I5 | pensions frozen before the base are identical under every rule and path |
| I6 | households without a recipient have identical taxes, benefits and net income under both rules |
| I7 | base-year weights equal the base weights; base-year totals with and without the sidecar agree to £0.01bn |
| I8 | every cell meets its anchored target within the calibrator's reported tolerance, and any cell where the weight-ratio cap binds is listed; a byte-identical rebuild from the same inputs |
| I9 | C3's cell-level ledger closes per cell and year: start + awards + arrivals − deaths − departures ± transfers between cells = end |
| I10 | for every year after the base, assigned marginals equal C3's distributions |
| I11 | the sidecar takes no path input |
| I12 | a changed sidecar byte changes the consumer's job key; no weight or record value reaches published results |

## Acceptance benchmarks

**Classes.** A gate locks before the one-shot scored run through this repo's ceremony. A registered comparison is configured in advance and reports its gap, with an "investigate" band that triggers diagnosis. A diagnostic has no threshold.

**Tolerances.** The figures below are proposals. This repo's half-versus-half noise floor measures sampling noise in panel moments and does not apply to comparisons with administrative aggregates. WP9's amendment therefore defines a floor for each gate, with a machine-checked derivation: base-sample noise from replicate bases for every gate; DWP's revision between forecast vintages for G1 and G2 (caseloads unchanged, spending within 0.30%, from Autumn Budget 2025 to Spring 2026); Stat-Xplore's disclosure noise and quarter-to-quarter variation for G3 and G4.

**Blindness.** G1 to G4's targets were published before registration and were read in scoping. They are held out from estimation, and the registration says they are not blind. G1 and G2 test agreement with DWP's forecast, itself a model output; they are acceptance gates because the use case asks for them, and R8 and DWP's later outturn are the cells that resolve.

**Scope adjustments.** DWP's and the OBR's figures cover Great Britain plus UK State Pension paid abroad and exclude Northern Ireland; DWP's spending rows by type include pensioners abroad, and its caseload rows by type are not additive. Our comparator is the UK simulation's GB households plus the abroad dataset, with Northern Ireland reported separately. DWP and the OBR use fiscal-year averages, Stat-Xplore point-in-time counts, and the ONS mid-year populations.

| Id | Source | Figure | Comparator | Tolerance (proposed) | Class |
|---|---|---|---|---|---|
| A1 | base-year reproduction | base totals without the sidecar | the same run with it | £0.01bn | identity |
| A2 | [ONS 2024-based projections](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections/bulletins/nationalpopulationprojections/2024based) | for every year and cell, the anchored target (base weighted count × ONS growth) | weighted persons | the calibrator's reported tolerance | identity; ONS levels (GB 66+ mid-2024 12,061,579; GB 67+ mid-2039 14,819,804) beside them as a diagnostic |
| A3 | Stat-Xplore March 2026 abroad stock | 1,093,218 in total, by country or country group; frozen 419,386; not frozen 657,806; unknown status 16,026 | the abroad dataset at March 2026 | exact | identity |
| G1 | [DWP Spring 2026](https://www.gov.uk/government/publications/benefit-expenditure-and-caseload-tables-2026), caseloads in 2030-31 | total 13,697k; basic 5,907k; new 7,775k; new with protected payment 1,358k; abroad 1,005k; GB-resident 12,692k | GB recipients plus abroad cells | total and GB-resident ±3%; basic and new ±5%; protected payment ±10%; abroad ±7.5% | gate |
| G2 | DWP Spring 2026, spending in 2030-31, on the forecast's own macro path | basic + new £160,181.4m; GB-resident total £174,064.7m; S2P £16,960.6m; protected payments £1,723.8m; abroad £6,630.5m | engine run on the OBR March 2026 central path, GB plus abroad | basic + new and GB-resident ±3%; S2P and protected payments ±10%; abroad ±7.5% | gate |
| G3 | Stat-Xplore March 2026 full-rate bands, held-out cohorts | GB share at or above the full rate: 74.8% at 66, 71.2% at 67, with all bands by sex | C3's predicted bands for cohorts excluded from estimation | ±3 points per band | gate |
| G4 | Stat-Xplore abroad backcast, May 2022 to March 2026 | 1,124,449 to 1,093,218; frozen 469,069 to 419,386; new State Pension 148,688 to 314,992 | the abroad model started in May 2022 with earlier information only | total ±2%; frozen ±3%; new State Pension ±5% | gate; the window spans documented series breaks in late 2024 and 2025, disclosed in the registration |
| R1 | [OBR July 2026](https://obr.uk/frs/fiscal-risks-and-sustainability-july-2026/), chart 3.11 baseline | 4.9754% of GDP (2030-31), 5.4379% (2039-40), 6.0852% (2049-50); £281.2bn and £459.2bn derived | an OBR-replication run: flat-rate uprating set directly to the OBR long-term "Triple Lock" row, the OBR long-term CPI and earnings path for everything else, State Pension age 68 over 2037-39, the add-on index set to the same row after 2030-31 | report; investigate beyond ±7.5% | registered comparison |
| R2 | OBR chart 3.11, triple lock minus earnings uprating | £11.99bn (2039-40), £42.50bn (2049-50), derived | the same configuration, with the triple-lock and earnings rows each set directly | report | registered comparison |
| R3 | [DWP's adjusted triple lock saving](https://www.gov.uk/government/publications/state-pension-uprating-analysis-2026/state-pension-uprating): **single-path comparator** | £15bn (2039-40) and £50bn (2049-50) nominal; £11bn and £30bn in 2025-26 prices; Pensim3; Great Britain; gross; rounded to £1bn; path unpublished | single-path runs with rates set directly: the triple lock at earnings plus 0.6 points from April 2030 and the plan at its earnings link, on the OBR long-term earnings path (consistent with DWP's figures, not identified from them), and the OBR's own ramped row; reported GB-resident and GB plus abroad, because DWP does not say whether its figure includes pensioners abroad. The expected value is not shown in this comparison | none: report gaps | registered comparison |
| R4 | DWP protected-payment inflows (Autumn Budget 2025 forecast vintage) | 105.2k (2025-26) to 71.3k (2030-31) | C3's new awards with a protected payment | investigate beyond ±15% | registered comparison |
| R5 | DWP Spring 2026, Pension Credit | £5,821.8m; 1,133k (2030-31) | engine, GB, central path | investigate beyond ±10% | registered comparison |
| R6 | DWP's cost of unfreezing (July 2023) | £930m a year, 2025-26 to 2027-28 | an engine reform of the uprated-country parameter on the abroad dataset | report | registered comparison |
| R7 | DfC Northern Ireland State Pension, May 2026 (chronicle#305) | 335,540 recipients; 152,970 on new State Pension | Northern Ireland recipients in the UK simulation | investigate beyond ±5% | registered comparison |
| R8 | Stat-Xplore September 2027 release, registered before it exists | caseloads by type, age band and residence at the next March point | Phase 1's prediction, frozen at registration | report | blind comparison |
| R9 | DWP Spring 2026, caseloads and spending by type, each year 2025-26 to 2029-30 | the State Pension sheet's rows by type, including the 2027-28 dip and the 2029-30 crossover of basic and new | as G1 and G2 | investigate beyond the G1 and G2 tolerances | registered comparison |
| D1-D3 | DWP spending by country (2024-25); Government Actuary up-rating report (January 2026); DWP 2016 cohort projections | as published | engine and C3 outputs | none | diagnostics |

The £15bn and £50bn are compared with model output only in R3, against single-path runs; wherever else they appear, they are labelled a single-path comparator.

## Running the uk-triple-lock expected-value build on it

**Today.** About 250 jobs. One path job builds four simulations (a reference, the unreformed run, the triple lock and the plan) over 13 fiscal years. From uk-triple-lock's build logs of 29 September 2026 (unpublished): the 199 Enhanced FRS jobs take a median of 41 seconds on main's engine and 61 seconds on the open engine pull request, at about 2 GB each; the 40 paired Microcosm jobs take a median of 338-392 seconds at 22.5-35 GB. The 199 paths are a stratified sample of 50,000 monthly draws that run to December 2039, with means calibrated to the central path for 2027-2039 and strata on the 2039-40 gap.

**On the Phase 1 bundle** (estimates):

| Block | Jobs | Purpose |
|---|---|---|
| Central, coverage and trajectory runs | about 11 | as today; coverage by type 2025-26 to 2030-31 |
| Primary expected value | 199 | the headline, to 2049-50 |
| Decomposition on the 40 paired draws | 200 | five layers: today's method on the Enhanced FRS and the new engine; today's method on the new base; plus population and date of birth; plus cohort entitlements; plus pensioners abroad. This bridges from £8.41bn and measures the bill driver in #13 by runs |
| OBR State Pension age timetable on the 40 paired draws | 40 | the 2037-39 scenario |
| Single-path comparisons R1-R3 and R6 | about 6 | benchmarks |
| Optional: ONS life-expectancy variants on the paired draws | 80 | demographic sensitivity |
| Optional: full-size Microcosm paired sensitivity | 40 | base-population sensitivity |

- **Per job:** 70-140 seconds and 2-4 GB, from today's medians, a horizon of 23 years instead of 13 (×1.5-1.8), two small abroad builds and the sidecar pins.
- **Total:** about 456 core jobs, 9-18 job-hours, 3-6 hours on three workers. The optional variants add 0.5-1 hour. A full-size Microcosm sensitivity to 2049-50 would need about 35 GB × 1.8 per process if memory scales with the horizon (assumed), so one worker (5.6-7.8 hours) or Modal.
- **Consumer changes** (for its maintainers):
  - apply the sidecar through E7; drop the type pin and the hard-coded State Pension age of 67, which the engine then derives from date of birth;
  - set the September CPI series per path from its statutory CPI, as the add-on pin does today, and keep the pin until a differential test agrees to £0.01 a year per person;
  - extend the horizon to 2049-50: run the monthly path model to December 2049, calibrate its means to an OBR long-term central path for 2031-2049, and re-stratify on both the 2039-40 and 2049-50 gaps. The redraw changes the 2039-40 sample, so the 2039-40 estimate is reported on both samples once;
  - retire the horizon patch once E5 ships (its hash checks against policyengine-uk 2.90.2 raise on any newer engine);
  - add a job option that takes each policy's per-year flat-rate uprating directly, for R1-R3;
  - add the sidecar, abroad and contract hashes to the job key (today the dataset enters only by name);
  - report GB, Northern Ireland and abroad separately; extend the test that no weight reaches published results.

**What changes in the headline.**

1. The saving is for a projected population (ONS principal, the law's State Pension age, modelled entitlements), conditional on one demographic projection and one accrual model. Demographic variants are sensitivities.
2. UK State Pension paid abroad is added and shown separately. The headline's geography is stated (decision 6).
3. Future retirees' starting amounts respond to the rule through the full rate at State Pension age. Under the survey method they received £0.
4. Existing frozen pensions are untouched by either rule; new freezes differ by rule.
5. The frozen-survey result becomes a labelled comparator, and the five-layer decomposition, measured by runs, replaces #13's estimated split.
6. 2049-50 becomes available for the OBR comparisons and for R3's single-path comparison with DWP's £50bn.
7. Non-pension incomes at pension ages are still same-age cross-sections uprated by the path, a limitation carried from the interim method until Phase 2.

## Phasing, work packages, cost and timeline

**Basis** (all estimates). One agent-day is one agent lane working a day on a package, including its review lanes; human days are review and rulings. Evidence from these repos:

- US static aging went from proposal to merged operator and annual exporter in about a day.
- This repo's UK layer port (+6,325 lines, unscored) merged in 1 hour 35 minutes. This repo's first code produced Social Security numbers in 8 hours 19 minutes; its projection engine passed certification on day 20.
- Microcosm's UK pull requests merge in a median 1.12 days.
- Ceremony is slower: gate pull requests have been drafts since July, and one exercise's median completion date slid nearly twelve weeks.
- Of this repo's 434 merged pull requests, 359 carry the Claude Code footer; people rule on decisions.

No money figure is estimated: the evidence holds no rate basis for agent or staff time. Machine time is in the expected-value section.

### Phase 1

| WP | Title | Repo | Depends on | Agent-days | Human days |
|---|---|---|---|---|---|
| WP0 | ADR 0005, the #148 multi-year resolution, registration skeleton | microcosm-dynamics; microcosm#148 | none | 1 | 0.5 |
| WP1 | Engine: flat-share and add-on inputs (E1, E2) | policyengine-uk | #1899, #1922, #1939, #1941 | 2-3 | 1 |
| WP2 | Engine: transitional-rate formulas (E3); uprated-country parameter, residence and frozen inputs (E4) | policyengine-uk | WP1 | 1.5-2.5 | 0.5-1 |
| WP3 | Engine horizons to 2051 (E5) | policyengine-uk | an owner | 1-2 | 0.5 |
| WP4 | Engine applier and contract version (E7) | policyengine-uk | WP1, WP2 | 1-1.5 | 0.5 |
| WP5 | Source packages: ONS projections to 2051 with mortality and migration sheets and variants; Stat-Xplore extracts (abroad by age, country, frozen status and category; amount bands); the country rule table; OBR July 2026 chart 3.11 and long-term determinants; DWP spending by country; the feed re-pin with chronicle#305 | chronicle; microcosm | decisions 5 and 7 | 3-5 | 1-2 |
| WP6 | UK static aging, weights only: ONS reader, fiscal-year alignment, age-cell column, UK annual builder | microcosm | WP5; #1069 base | 2-3 | 0.5-1 |
| WP7 | Cohort entitlement model: state space, initial conditions, year-indexed mortality, accrual, migration, abroad stock, engine bridge, backcast harness | microcosm-dynamics | WP5; WP2 for the bridge | 5-8 | 2 |
| WP8 | Assignment, bundle writer, abroad dataset, manifest, scorecard, private publication | microcosm | WP6, WP7, WP4 | 2-3 | 1 |
| WP8b | Register the base, sidecar and abroad datasets by name and sha256, and release a bundle pinning the engine release with #1899, #1922, #1904 and E1-E7 | policyengine.py | WP4, WP8 | 0.5-1 | 0.5 |
| WP9 | UK gate file through the amendment process; floors; referee round; registration; one-shot scored run, published whatever the result | microcosm-dynamics | WP8; an engine release with WP1-WP4 | 1-2, plus 1-3 weeks elapsed | 1-2 |
| WP10 | Consumer integration, including the path model to 2049-50 (proposed to uk-triple-lock's maintainers) | uk-triple-lock | WP4, WP8b | 5-8 | 1-2 |
| WP11 | Expected-value build, decomposition and write-up | uk-triple-lock | WP9, WP10; after the 28 October 2026 OBR forecast | 0.5-1, plus machine time | 0.5 |
| | **Total** | | | **25.5-41** | **10.5-14.5** |

**Critical path.** The engine lane (WP1, WP2, WP4) and the data lane (WP5, WP6) run in parallel. WP7 builds its state space, accrual and migration on pinned source copies and joins the engine lane at WP2 for its bridge. After WP8 and WP8b, WP9 and WP10 run in parallel, then WP11. Along that path the table sums to about 13-21 agent working days, or 17-27 if WP7 cannot start before WP2 merges.

Upstream work outside this plan is on the same path: the #1069 calibrated base and its migration off the State Pension age parameters, merges of #1899, #1922 and #1904, and a policyengine-uk release.

- With rulings inside a few days and the upstream items landing within three weeks: **4-7 weeks elapsed**, so November 2026, after the OBR's 28 October forecast.
- If the gate ceremony stalls as earlier exercises did: **8-12 weeks**.
- Unscored first-light bundles (WP6-WP8 before WP9) can feed internal, labelled diagnostic runs about 2-3 weeks in. Published figures wait for the gated run: unscored machinery merges freely, and scored claims go through ceremony.

### Phase 2

| WP | Title | Repo | Agent-days | Human days |
|---|---|---|---|---|
| P2.1 | Population kernels: year-indexed mortality on persons, ageing from date of birth, event alignment to ONS components, draws keyed by person identity | microcosm-dynamics | 8-12 | 2 |
| P2.2 | Residence kernels: emigration as a state change, returns, immigrant entrants, overseas flows | microcosm-dynamics | 5-8 | 1-2 |
| P2.3 | Person-level accrual from fitted propensities, needing no licensed data | microcosm-dynamics | 4-6 | 1-2 |
| P2.4 | Labour, partnership, widowhood and claiming kernels | microcosm-dynamics | 8-12 | 2-3 |
| P2.5 | Accrual from Understanding Society, BHPS and ELSA histories, after licences | microcosm-dynamics | 12-20 | 3-5 |

Phase 2 needs contract version 2: per-year `age` with a fixed date of birth, entrant and exit rows (household weight 0 outside residence), base-plus-clone records where household composition changes, and earnings held as path-independent ratios to average earnings. It runs on the Microcosm graph runtime, with `person_period` produced by an EXPAND node with lineage and period household weights owned by a REWEIGHT node, as ruled on microcosm-dynamics#412 on 2 September 2026, and with draws keyed by person identity. It does not use this repo's M6 projection engine, whose draws come from an ID-sorted ordinal registry. Each candidate registers as a challenger and merges only on held-out improvement.

Without P2.5 it is 25-38 agent-days and 6-9 human days, about 4-6 weeks after Phase 1. P2.5 is 12-20 agent-days plus licence onboarding and a challenger registration, about 8-14 weeks.

## Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Accrual for 2030s cohorts is weakly identified: no public qualifying-year or starting-amount distributions below State Pension age | bill and protected-payment inflows biased | held-out cohorts (G3); protected-payment inflows (R4); DWP types (G1, G2, R9); a data request (decision 8); sensitivity on the short-record tail |
| microcosm#1069 (the C1 base, and the migration off the deleted State Pension age parameters) has no assignee or pull request as of 30 September 2026 | C1, WP6 and WP8 wait on it | name its owner (decision 4); run first light on an interim base by ruling (decision 3) |
| The engine chain (as of 30 September 2026): #1899 has no reviews; #1922 and #1939 await rulings; #1941 is an issue; the horizon work has no owner or pull request | WP1-WP4 blocked | name owners (decision 4); the consumer keeps its add-on pin until E2 |
| Thin samples at single ages: an effective sample size of 2,303 among people aged 66+ on #1069's head | noisy weights | pooled cells, a weight-ratio cap, effective sample size by age in every scorecard |
| Abroad flows are unobserved; the Government Actuary calls migration over State Pension age "immaterial" to the overseas basic State Pension total | abroad bill off | the backcast gate (G4); R6; an age-by-country extract (WP5) |
| DWP's £15bn, a single-path comparator: unknown path and unknown treatment of pensioners abroad | comparator ambiguous | report both scopes; never compare with the expected value; ask DWP (decision 8) |
| Slots fix household composition at the base year's patterns: no widowhood trend, no care-home shift | net saving and couple mix drift | stated limitation; the Pension Credit comparison (R5); Phase 2 |
| The assignment is an imputation | methodological objection | an explicit ruling (decision 2); labelled; invariant I10 |
| The engine skips unknown dataset columns silently | the sidecar ignored on an old engine | E7 fails closed |
| Microcosm pins policyengine-uk 2.100.0, and its take-up stage breaks when #1899 deletes the State Pension age parameters | the base cannot be rebuilt on the new engine | #1069 owns the migration; this plan does not touch that stage |
| Vintages move: the OBR on 28 October 2026, DWP tables around December, the Government Actuary's 2025 review, 2026-based projections | benchmarks shift | every benchmark keyed by vintage; one re-run per vintage |
| `gates.yaml` is shared with the live US work | conflicts | the UK gate goes in its own file, as ADR 0002 requires ("No change to gates.yaml"); ADR 0005 records the choice |
| The sidecar is record-level survey data | licence breach if leaked | private storage only; aggregates-only scorecard and results; the abroad dataset carries no survey records |

## Decisions needed

1. **Direction and placement.** Phase 1 (reweighted slots, cohort entitlements and the sidecar contract) first, with person-level trajectories as Phase 2 challengers; ADR 0005 in this repo; record this as the multi-year answer on microcosm#148 while ADR 0002 stays Proposed for general UK panel work; C4's assignment in microcosm. *Recommended: yes.*
2. **The entitlement assignment as a labelled imputation**, conditional on the held-out gate G3 and invariant I10. *Recommended: yes.*
3. **Primary base for the producer.** A Microcosm base at about the Enhanced FRS's size, or a sidecar keyed to the Enhanced FRS; and whether first light may run on an interim base. *Recommended: Microcosm, with an interim base for first light.* Microcosm's UK migration epic rules out importing `policyengine_uk_data`. uk-triple-lock's maintainers choose their own primary dataset.
4. **Owners.** One policyengine-uk owner for E1-E7, including the horizon work; an owner for microcosm#1069; uk-triple-lock's maintainers for WP10-WP11.
5. **Sources.** Every target that C2 or C4 fits, and every shipped bundle, comes from pinned Chronicle packages, as Microcosm's UK invariants require; sha256-pinned files serve only C3's inputs and unscored first-light runs that never ship. *Recommended: as stated.*
6. **Baseline conventions.** The law's State Pension age, with the OBR's 2037-39 timetable as a scenario; additional pension by CPI, at the law's prices floor; a headline of UK residents plus pensioners abroad, gross, shown in parts. *Recommended: as stated.*
7. **Data access.** A Stat-Xplore account for extracts its holder runs personally, with every extract pinned by sha256; UK Data Service access to Understanding Society and ELSA for Phase 2; and whether to seek Digital Economy Act accreditation for ELSA linked to National Insurance records. *Recommended: guest extracts now; the rest when Phase 2 starts.*
8. **Ask DWP** whether its £15bn, a single-path comparator, includes pensioners abroad, its uprating path, its State Pension age timetable, the starting-amount rule for people abroad at State Pension age, and whether it can publish starting-amount or protected-payment distributions by cohort. This is a send to an outside party. *Recommended: draft for Max to send.*
9. **Timing.** The gated expected-value build after the OBR's 28 October 2026 forecast.

## Alternatives considered

- **Static ageing alone** (uk-triple-lock's proposed interim fix, or #1069's multi-year piece without the cohort layer). It fixes counts and types but gives 2030s retirees the amounts of today's same-age survey records, and it has no mortality by entitlement, migration or pensioners abroad. It is a comparator for the population layer of Phase 1's decomposition.
- **Person-level trajectories first.** About 58-92 agent-days for a first scored version, with an unscored bundle in about five weeks and a registered one in eight to ten. `person_period` keying is ruled but unbuilt, emigration has no graph node yet, and the net-saving gain from widowhood and labour dynamics needs household clones that multiply job time. It becomes Phase 2.
- **Per-year files or a multi-year dataset.** Both fix one macro path into every path job; see the artifact table.
- **An aggregate module for pensioners abroad** (caseload × rate outside the engine). That is a side model; every number here comes from a PolicyEngine UK run.
- **Ageing survey records forward** ([policyengine-uk#1351](https://github.com/PolicyEngine/policyengine-uk/pull/1351), closed with the comment "closing, this is incorrect"). The pull request added a year to every age in a closed population, with monetary inputs still uprated: no deaths, migration or new awards. Ageing records also carries each person's base-year income forward, so a 61-year-old's earnings would sit on a 75-year-old in 2039.

## Sources

Every figure above was read on 30 September 2026 from the source named or from the PolicyEngine repositories at the commits linked, except where marked unpublished (uk-triple-lock's build logs; the Schedule 1 check and the country rule table, which ship with WP2 and WP5).

- DWP, [State Pension uprating analysis 2026](https://www.gov.uk/government/publications/state-pension-uprating-analysis-2026/state-pension-uprating), 29 September 2026.
- DWP, [Benefit expenditure and caseload tables 2026](https://www.gov.uk/government/publications/benefit-expenditure-and-caseload-tables-2026): Spring Forecast 2026 outturn and forecast tables (the downloaded workbook is byte-identical to uk-triple-lock's committed copy).
- DWP, [Benefit expenditure and caseload tables 2025](https://www.gov.uk/government/publications/benefit-expenditure-and-caseload-tables-2025): State Pension by country 2024-25; protected-payment inflows 2016-17 to 2030-31 (Autumn Budget 2025 forecast vintage).
- DWP, [Stat-Xplore](https://stat-xplore.dwp.gov.uk), dataset `SP_New`, March 2026 and the May 2018 to March 2026 series, guest extracts; [Open Data API](https://stat-xplore.dwp.gov.uk/webapi/online-help/Open-Data-API.html).
- DWP, [Analysis of future pension incomes 2025](https://www.gov.uk/government/statistics/analysis-of-future-pension-incomes-2025/analysis-of-future-pension-incomes-2025); [Impact of the new State Pension: longer-term research](https://assets.publishing.service.gov.uk/media/5a803fde40f0b62302692669/impact-of-new-state-pension-longer-term-reserach.pdf) (2016).
- OBR, [Fiscal risks and sustainability, July 2026](https://obr.uk/frs/fiscal-risks-and-sustainability-july-2026/), chapter 3 charts and tables; long-term economic determinants and public finances databank.
- ONS, [National population projections: 2024-based](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections/bulletins/nationalpopulationprojections/2024based) (28 April 2026), with the mortality and migration assumptions; [Past and projected period and cohort life tables: 2024-based](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/lifeexpectancies/bulletins/pastandprojecteddatafromtheperiodandcohortlifetables/2024baseduk1981to2074) (15 May 2026); [Long-term international migration, provisional, year ending December 2025](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/internationalmigration/bulletins/longterminternationalmigrationprovisional/yearendingdecember2025).
- Government Actuary's Department, [up-rating report, January 2026](https://assets.publishing.service.gov.uk/media/69666e391f94f51fd079cbbc/E03471795_Un_Act_GAD_NIF_Uprating_Report_Jan26_Web_Accessible.pdf); [quinquennial review of the National Insurance Fund as at April 2020](https://assets.publishing.service.gov.uk/media/62331075e90e070a53f689b0/QR_2020_Report_17_Mar_2022.pdf).
- GOV.UK, [State Pension if you retire abroad](https://www.gov.uk/state-pension-if-you-retire-abroad); [countries where we pay an annual increase](https://www.gov.uk/government/publications/state-pensions-annual-increases-if-you-live-abroad/countries-where-we-pay-an-annual-increase-in-the-state-pension); DWP, [estimated cost of uprating State Pensions in frozen-rate countries](https://www.gov.uk/government/statistics/estimated-cost-of-uprating-uk-state-pensions-in-frozen-rate-countries-2024-to-2028); House of Commons Library, [Frozen overseas pensions](https://commonslibrary.parliament.uk/research-briefings/sn01457/) (metadata and excerpts read; the page blocks automated fetches).
- Legislation: [Pensions Act 1995 Schedule 4](https://www.legislation.gov.uk/ukpga/1995/26/schedule/4); [Pensions Act 2014](https://www.legislation.gov.uk/ukpga/2014/19) Part 1, s.20, s.26, s.27 and Schedule 1; [Social Security Administration Act 1992 s.150A](https://www.legislation.gov.uk/ukpga/1992/5/section/150A); [Social Security Contributions and Benefits Act 1992 s.113](https://www.legislation.gov.uk/ukpga/1992/4/section/113); [SI 1975/563 reg 5](https://www.legislation.gov.uk/uksi/1975/563/regulation/5); SI 2015/173 [reg 13](https://www.legislation.gov.uk/uksi/2015/173/regulation/13) and [reg 21](https://www.legislation.gov.uk/uksi/2015/173/regulation/21); [SI 2026/218](https://www.legislation.gov.uk/uksi/2026/218/made); [Pensions (Northern Ireland) Order 1995 Schedule 2](https://www.legislation.gov.uk/nisi/1995/3213/schedule/2); [Pensions Act (Northern Ireland) 2015](https://www.legislation.gov.uk/nia/2015/5/contents).
- PolicyEngine: [policyengine-uk at 44240bd8](https://github.com/PolicyEngine/policyengine-uk/tree/44240bd8d7d7e97f2980ccc8134e76e61541966f); [uk-triple-lock at f6f5505](https://github.com/PolicyEngine/uk-triple-lock/tree/f6f5505e6f1b734f03b5e75170267fea4c81b887) and its issues [#9](https://github.com/PolicyEngine/uk-triple-lock/issues/9) and [#13](https://github.com/PolicyEngine/uk-triple-lock/issues/13); [microcosm at af98853e6](https://github.com/PolicyEngine/microcosm/tree/af98853e62e1ae8c23fea355d8f757042e5c85be); this repository at [dd222b9](https://github.com/PolicyEngine/microcosm-dynamics/tree/dd222b9af926c773a0f92732e2d08be507793378).
