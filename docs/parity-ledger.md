# DYNASIM parity ledger

Microcosm Dynamics aims to answer the Social Security questions that
the Urban Institute's DYNASIM answers, with code, data and tests that
anyone can rerun. It follows a representative population year by
year, applies the program's rules to each life, and reports what a
reform does to benefits, poverty and the program's finances, by
cohort and group, decades ahead. This page lists what full parity
with DYNASIM for Social Security analysis requires, one capability at
a time, and where each piece stands.

*Statuses verified against the repository at commit `216acab1` and
against the open pull requests and issues on 11 October 2026.*

## Bottom line

Parity with DYNASIM is not yet demonstrated. The model's components
that face pre-registered tests, which we call gates, pass them: seven
gates in all, four of them only under amendments we adopted after an
earlier attempt failed. But the four blind comparisons with DYNASIM3
use none of those components, and the comparisons carry no pass or
fail threshold: each reports its gaps without grading them. None
involves DYNASIM4, Urban's current version.

What separates the model from DYNASIM today falls into three groups.
The two projections compared with DYNASIM3 draw no earnings,
marriages, divorces or births after 2010, check no one's insured
status and apply no retirement earnings test. The projected
population is closed: no newborns, immigrants or emigrants enter or
leave it. And the model produces no national cost estimate,
trust-fund balance or depletion date, and projects no SSI, wealth or
pension income.

## How to read the ledger

Each row is one capability. The columns say what DYNASIM does, where
Microcosm Dynamics stands, what test would show parity, which pull
request, issue or decision tracks the work, and the next step.

The status column uses five terms, and a row can carry more than one:

- *None*: no code in the repository does this.
- *Built, ungated*: code exists, but no pre-registered gate scores it.
- *Gate passed*: the component passes a gate whose terms are locked in
  `gates.yaml`, and the scored run is committed under `runs/`.
- *Used in a blind test*: at least one of the four blind comparisons
  with DYNASIM3 uses it. Exercise 1 cuts each cost-of-living
  adjustment (COLA) by one percentage point and exercise 3 raises the
  full retirement age to 68; both project a closed cohort of PSID
  members to 2030. Exercise 2 cuts every benefit by 13 percent and
  exercise 4 adds a minimum benefit; both apply the reform to incomes
  the PSID recorded. The [paper](https://microcosm.institute/dynamics/paper)
  reports all four.
- *Report-only*: the model produces and publishes it, with no pass or
  fail.

The DYNASIM column summarizes Urban's public documentation, listed
under [sources](#sources-on-dynasim). It says what those documents
describe; this page does not test DYNASIM itself. Where we have not
established a DYNASIM4 detail, the row says so.

In the tracking column, `#` numbers link to pull requests and issues in
this repository. A `d` number identifies a ruling in the maintainer's
decision log, which is not public; [rulings cited](#rulings-cited-on-this-page)
says what each decided and where GitHub or the repository records it.
Names such as B2, R2 and G are milestones of the Track B design that
ruling d515 approved; the [critical path](#the-critical-path) explains
them. Paths are relative to the repository root.

## The ledger

### Earnings

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Earnings histories | Builds each person's lifetime earnings history from survey and administrative records ([overview][ov]; [DYNASIM4 fact sheet][d4]). | *Gate passed* for the generated earnings process: gate 1 passes (`runs/gate1_rank_knn_v5.json`), scoring 1998–2022 at ages 25–59, not whole careers. *Used in a blind test, ungated* for the recorded PSID careers that exercises 1, 3 and 4 read; the paper reports that about half of the career years through 2010 for the 7,486 cohort members who reach 62 between 1979 and 2030 hold imputed or zero values. A test of learned fills, `gate_epuf_fill`, had its tolerance ratified on 10 October (d927); its lock sits in [#515][pr515], is not yet in `gates.yaml`, and no held-out person has been read. | Whole careers set against SSA's Earnings Public-Use File by birth cohort and sex: years without covered earnings, low-earnings years, persistence and the 35-year AIME, including low earners and broken careers. | [#515][pr515], [#516][pr516]; d927, d929 | Merge #515 and #516 and score `gate_epuf_fill` once; d929 then decides whether exercises 1, 3 and 4 rerun with the learned fills. |
| Covered earnings and agreement with SSA records | Separates employment that Social Security covers from noncovered employment ([DYNASIM3 primer][d3]). | *None* for a covered/noncovered split: the projections and the Axiom bridge treat all PSID labor income as covered, and the correction design is a draft (`docs/design/covered_earnings_correction.md`). *Report-only* for the comparison of the PSID's own 1998–2004 earnings with SSA's public-use file: `gate_epuf` closed without locking and has scored no model output (`docs/amendments/gate_epuf_registration_proposal.md`). | A covered/noncovered split of PSID earnings, checked against SSA's totals of covered workers and taxable earnings, and a fresh gate on the public-use file with power beyond gate 1. | [#403][i403], open but idle: it belongs to the correction campaign, which stopped on 9 September 2026, and that campaign's last design PR, [#405][pr405], closed unmerged | Decide whether to restart the covered-earnings correction, now as a registered gate. |
| Forward earnings | Projects employment, hours, wages and pension coverage each year ([DYNASIM4 fact sheet][d4]). | *Gate passed, not used in a blind test.* The forward law, fitted on PSID earnings through 2014 at ages 25–64, passes gate m6 in 4 of 5 seeds (`runs/gate_m6_candidate3_v1.json`). It has no fitted distribution above 64, and both projection tests draw no earnings after 2010 (`src/populace_dynamics/cola_track_a/adapters.py`). In every seed, its two-year earnings growth at ages 25 to 44 runs below the PSID's. | Track B's sequence: B1 v2 reproduces gate m6's histories; B2 tests the bridge from the 2010 cohort to the law's 2014 boundary on PSID 2012 and 2014, gating six level cells (median, 90th percentile and zero rate by cohort) and reporting ten more (d781); B3 refits ages 25–69 with gates at 62–64, 65–66 and 67–69; B3L backtests 2006 to 2022; an independent joint holdout comes before any 2030 claim. Because B2 gates levels only, growth and persistence need their own test. | [#505][pr505]; d515, d622, d693, d765, d781, d782, d1342 (open) | Settle d1342, which holds B2 because its six cells reach 0.813 power on the ruled design, short of the 0.952 d781 assumed; merge #505; then post and run B1 v2, and register B2. |

### Disability, mortality and claiming

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Work limitation | Models work-limiting disability from demographic and economic characteristics ([DYNASIM3 primer][d3]). | *Gate passed, not used in a blind test.* Gate m4 passes in 5 of 5 seeds (`runs/gate_m4_hazard_v1.json`), and gate m6 also gates its incidence and recovery. Its SSA anchors test age shape and exit composition, not disability insurance (DI) levels. The blind projections use a separate DI component and read work-limitation reports only to classify people at the start. | Work limitation linked to employment and to DI awards in the same simulated people, checked against PSID reports and SSA award statistics. | None for the link; Track B's B4 sets limits on DI outcomes (d515) | Decide whether projected DI awards should depend on work-limitation status; if so, register a joint gate. |
| Disability insurance entitlement | Models DI applications and awards and computes disability benefits ([DYNASIM3 primer][d3]). | *Used in a blind test, ungated.* Exercises 1 and 3 draw awards, recoveries and conversion at full retirement age from rates fitted on data through 2008, and never check insured status (`src/populace_dynamics/engine/di_entitlement.py`). A report-only check against SSA's 2023 statistics runs on a synthetic population (`runs/di_entitlement_asr2023_validation_v1.json`). The statutory DI computation-years rerun (Track A v2, `src/populace_dynamics/track_a_v2/`) is merged, has run only on invented data and is not registered. | Awards, recoveries, deaths, conversions, beneficiary counts and benefit amounts on the projected population against SSA statistics, with disability-insured status, statutory computation years and stocks that reconcile with flows. | d479, d513; [#42][i42] | Register Track A v2 on #42 and run it once; then register a DI entitlement gate on the PSID cohort. |
| Mortality and its improvement over time | Projects deaths with trends over time, socioeconomic differences and a separate process for disabled workers ([DYNASIM3 primer][d3]), aligned to targets from SSA's actuaries ([DYNASIM4 fact sheet][d4]). | *Used in a blind test, ungated.* Exercises 1 and 3 scale SSA's 2004 period life table by two ratios from the 2008 Trustees Report, one under 65 and one at 65 and over, the same for men and women (`src/populace_dynamics/cola_track_a/mortality.py`); disabled workers die at DI rates. Gate m6 certifies nothing about mortality drift, and its SSA/NCHS mortality anchor is marked not supplied in the passing run. | Projected death probabilities and life expectancy by single year of age and sex against OACT's tables over held-out years; disabled-worker deaths against SSA counts; deaths kept apart from survey attrition at the oldest ages. | [#74][i74], [#113][i113] | Supply gate m6's mortality anchor, then replace the two-ratio method with OACT's single-age death probabilities, which the 2026 baseline already loads (`src/populace_dynamics/baselines/tr2026_intermediate.py`). |
| Mortality differences by income, education and race | Models mortality differences by socioeconomic characteristics ([DYNASIM3 primer][d3]). | *None.* Every mortality model in the repository uses age and sex only. The one difference it models is that disabled workers die at higher DI rates (`src/populace_dynamics/engine/di_entitlement.py`). A comparison of PSID death rates with NCHS rates by age and sex is report-only (`runs/mortality_floors_v1.json`). | Survival gradients by lifetime earnings, education and race and ethnicity against published SSA and NCHS evidence, and the lifetime-benefit differences that follow. | None; [#74][i74] names "differential mortality" as a component but defines no socioeconomic gradient | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Claiming | Claiming depends on benefit amounts, spouse characteristics and policy parameters, with separate equations by earnings relative to the earnings test's exempt amount ([DYNASIM3 primer][d3]). | *Used in a blind test, ungated.* Exercises 1 and 3 draw a whole-year claim age from SSA's distribution of retired-worker awards by sex and year, reusing the 2008 distribution for later years (`src/populace_dynamics/engine/claiming.py`). No claim responds to a reform; exercise 3's two registered claiming alternatives are stylized delays. | A monthly claiming hazard on insured people who have not yet claimed, reproducing held-out SSA award flows (B6a); separately, a response to policy identified from real policy changes, with placebo tests (B6b). | d515 | Register a baseline claiming test on held-out years of SSA's award table once insured status exists. |

### Family and population

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Marriage, divorce and widowhood | Projects marriage, divorce, remarriage and widowhood ([DYNASIM4 fact sheet][d4]; [overview][ov]). | *Gate passed, not used in a blind test.* Gates 2, 2b and 2c pass in 4 of 5 seeds each, and gate m6 scores first-marriage, divorce and remarriage flows over 2015–2019. The blind projections draw no marriage or divorce: a person is widowed only when a spouse in the cohort dies (`src/populace_dynamics/cola_track_a/adapters.py`), so 552 married members of the 2011-wave cohort whose spouses are outside it, and 80 with no linked spouse, are never widowed (`runs/replication_urban2010_cola_v1.json`). | The gated marriage and divorce models inside the projection, with redrawn starting states and spouses outside the cohort simulated; flows, durations, spouse links and the resulting spouse and survivor benefits, scored by a registered projection gate (B4). | d515 | Register B4 once B3, B3L and the history recorder H exist. |
| Births | Adds people through births and aligns fertility to targets from SSA's actuaries ([DYNASIM4 fact sheet][d4]). | *Gate passed* for fertility rates (gate 2). *Report-only* for newborns entering a projection: gate m6's engine adds them (316 in its reference draw) and scores none. The blind projections add no newborns. A newborn gets a link to the mother, her household and her weight, and no father link. An opt-in, report-only birth step can draw births from the 2026 Trustees' or CBO's fertility schedule (`src/populace_dynamics/baselines/fertility.py`); no registered test uses it, and nothing aligns the gated fertility model to those targets. | Projected births against vital statistics; newborns' links to both parents, households and starting states; their entry into later earnings, disability and benefit processes. | [#412][i412] | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Immigration and emigration | Adds immigrants and models emigration ([DYNASIM4 fact sheet][d4]). | *Built, ungated*, and never run on real data. A scheduled-entrant module labels itself report-only (`src/populace_dynamics/engine/entrant_schedule.py`), but its readers for arrival totals and donor records were not carried over, no committed run has added an immigrant, and entrants get no earnings, disability, claiming or entitlement processes (`src/populace_dynamics/engine/entrant_domains.py`). The US engine has no emigration. | Arrivals and departures sized to OACT's assumptions; entrants' covered-work histories and insured status; their benefit receipt against SSA statistics. | [#412][i412]; design PR [#218][pr218] closed unmerged | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Starting population | Starts from a representative sample built mainly from the Survey of Income and Program Participation, with histories drawn from survey and administrative records ([DYNASIM4 fact sheet][d4]; [overview][ov]). | *Used in a blind test* for closed PSID cohorts: all four comparisons start from PSID members with the PSID's own weights. *None* for a projection started from Microcosm's population: a plan and a draft registration exist (`docs/plans/microcosm-start.md`, `docs/plans/microcosm-start-registration-draft.md`), with no code. Registration 19 ran a static, report-only SSI analysis on Microcosm's frame and disclosed a frame defect; its code is in draft [#511][pr511]. | Starting earnings histories (H1), the starting population against SSA counts, gate 3's first-year cells, then an end-to-end projection and reform comparison started from Microcosm. | d947 (open); [#511][pr511]; [microcosm#1178][mc1178] | Post the Microcosm-start registration (d947), then build the frame reader. |
| Alignment and a representative population | Aligns fertility, mortality, disability, immigration and labor force participation to targets from SSA's actuaries ([DYNASIM4 fact sheet][d4]). | *None* for alignment: the engine has no alignment step, and gate m6 records its alignment report as not computed. *Gate passed, not used in a blind test*, for transport: gate w1 places the PSID-fitted processes on Microcosm's CPS-based frame and matches 43 cross-sectional cells and one ordering check (`runs/gate_w1_candidate4_v1.json`, `runs/NOTES-gate_w1_candidate4.md`). It certifies no transition, and its SSA benefit cells are report-only. | An alignment step to the actuaries' demographic and labor targets that keeps households consistent, with its displacement from the unaligned path published; gated SSA benefit and payment totals. | [#151][i151]; design PR [#217][pr217] closed unmerged | See [known gaps](#known-gaps-without-a-tracking-issue). |

### Benefit rules and payments

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Insured status | Its benefit calculator checks whether each worker is insured ([DYNASIM3 primer][d3]). | *None.* No code decides fully, currently or disability insured status. The projections pay a retired-worker benefit to anyone whose career through 2010 yields a positive benefit, and DI awards never check it. Exercise 4 counts years of coverage for its minimum benefit (`src/populace_dynamics/min_benefit_track_m/coverage.py`), which is not an insured-status test. | The statute's insured-status rules checked against SSA's worked examples, then the share of projected claimants, survivors and DI awardees who would fail them. | None | See [known gaps](#known-gaps-without-a-tracking-issue). |
| A worker's own benefit and claiming adjustments | Computes benefits under historical and projected program rules from each person's lifetime record ([overview][ov]; [Five Democratic Approaches][fd]). | *Used in a blind test, ungated.* The Python oracle (`src/populace_dynamics/ss/`) computes AIME, PIA and early and delayed claiming adjustments; no gate scores it. The projection tests count a fixed 35 computation years; a statutory count exists (`src/populace_dynamics/ss/statutory_aime.py`) but they do not use it. Delayed credits stop at age 70 or 48 months after full retirement age, whichever comes first, which leaves people born 1917–1942 2 to 12 months short of the law; no one has yet checked whether any committed result is affected ([#494][i494]). | Statutory worked examples for every birth cohort, delayed credits included, and a differential test against Track B's gross-benefit layer and Axiom. | [#494][i494] | Fix #494 in a new module beside the oracle, as `src/populace_dynamics/ss/statutory_aime.py` did for computation years, and add a differential test against G. |
| Spouse and survivor benefits, and dual entitlement | Computes spouse, survivor and divorced-spouse benefits from work and marriage histories ([DYNASIM3 primer][d3]). | *Used in a blind test, ungated*, for spouse and aged widow(er) benefits only. Exercises 1, 3 and 4 use the oracle's spouse and survivor formulas, which tests check against SSA's worked examples. No comparison computes divorced-spouse, child, or mother's or father's benefits, and in the projections a person receiving DI on their own record gets no spouse's benefit. The Track A v2 rerun adds that case and has run only on invented data. | SSA's worked examples, then counts and average amounts by beneficiary type against SSA's published tables, on a projection that links former spouses. | d479, d513; [#42][i42] | Register and run Track A v2, as in the DI row. |
| Family maximum and gross family benefits | The 2004 primer says DYNASIM3 left out children's benefits and the family maximum ([DYNASIM3 primer][d3]); we have not established how DYNASIM4 treats them. | *Built, ungated.* Track B's gross-benefit layer, G (`src/populace_dynamics/track_b/gross_benefits.py`, merged in [#492][pr492]), computes the family maximum, its redistribution, age reductions, dual-entitlement offsets and the whole-dollar payment for one worker's record in one month, and its tests check SSA's worked examples. It refuses some families, among them beneficiaries entitled on more than one record and cases the 1972 savings clause governs. It has no payment timing, earnings test or recomputation, and no projection uses it. | A registered conformance run reporting, over a defined population of families, the share computed and the share refused by reason; then monthly family payments against SSA's family-benefit statistics. | d515; [#495][i495] | Build R2, then the monthly assembly (I) that would carry G into projections. |
| Retirement earnings test | Applies the earnings test when computing the benefits people actually receive ([DYNASIM3 primer][d3]). | *Built, ungated*: parameters only. Track B's R1 pins SSA's exempt amounts for 2000–2026 and the 1/2 and 1/3 withholding rates, and projects later amounts by the statutory formula (`src/populace_dynamics/track_b/ret_params.py`). Nothing computes deductions, the grace year, the adjustment at full retirement age or recomputation, and no projection applies the test. | R2 reproduces SSA's worked examples of suspension, deductions and the grace year, exact after rounding; R3 adjusts the reduction at full retirement age and recomputes for later earnings; then B5 runs the test inside a projection with forward earnings at ages 62 to 69. | d515 | Build R2 against captured SSA worked examples. |
| Benefit rules run in Axiom | Uses rule-based calculators for Social Security and SSI ([overview][ov]; [DYNASIM4 fact sheet][d4]). | *Built, ungated.* Axiom reproduces the Python oracle's AIME for all 7,486 people tested, as the paper reports, on encodings that remain unaccepted candidates (`src/populace_dynamics/axiom_benefit_bridge.py`); no artifact in `runs/` pins that result yet. A committed artifact shows Axiom matching the oracle's PIA to the cent for 240 synthetic workers in the 2020 and 2026 eligibility cohorts (`runs/pia_cross_engine_v1.json`); on the PSID cohort, nothing beyond AIME has been compared. The blind tests that compute benefits use the Python oracle. PolicyEngine-US computes a worker's own AIME and PIA but has no spouse or survivor benefit formulas and takes those benefits as inputs (`src/populace_dynamics/ss/params.py`, `docs/technical-specifications.md`). | Cohort-wide differential checks of Axiom against the oracle and G for PIA, own, auxiliary and DI benefits, the family maximum, the earnings test and the monthly payment, on accepted encodings, each pinned by a committed artifact. | [#100][i100] (workstream W3) | Commit the AIME agreement as a `runs/` artifact with a reproduction test. |

### Income, poverty and groups

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Supplemental Security Income (SSI) | Applies SSI's income and resource rules and models eligibility, participation and benefits ([DYNASIM3 primer][d3]). | *Used in a blind test*, static. Exercise 2 offsets the cut for people who already report SSI and enrolls no one new (`src/populace_dynamics/estimates/adjusted_poverty.py`); in its committed run, the registered alternative SSI rules leave the headline unchanged. Registration 19 computed SSI's asset test on Microcosm's frame through PolicyEngine-US, static and report-only, with a disclosed frame defect; its code is in draft [#511][pr511]. Nothing projects SSI. | Eligibility, resource, deeming and state-supplement worked examples; participation against SSA caseloads by age and type; then projected caseloads, payments and the poverty effect of a Social Security cut. | [#511][pr511]; d905; [microcosm#1178][mc1178] | Merge #511, then register and run the rerun on the corrected frame; see [known gaps](#known-gaps-without-a-tracking-issue) for projected SSI. |
| Wealth, pensions and other income | Projects pension coverage and benefits, retirement-account balances and withdrawals, asset income and wealth ([DYNASIM4 fact sheet][d4]; [overview][ov]). | *Used in a blind test* for reported wealth only: exercise 2 turns PSID-reported wealth into an annuity income (`src/populace_dynamics/estimates/adjusted_poverty.py`). *None* for projection: the model projects no wealth, pensions or asset income. | Projected pension coverage and benefits, account balances and drawdowns, asset income and wealth by cohort and lifetime-earnings group, first against later PSID waves the model did not see, then against DYNASIM's published tables. | None; [#45][i45] reserves balance-sheet state for capital gains and plans no wealth or pension projection | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Poverty and income distribution | Reports poverty, adequacy and distributional effects of reforms from projected family income ([Five Democratic Approaches][fd]). | *Used in a blind test*, static. Exercise 2 computes adjusted poverty at 67 on incomes the PSID recorded: a 13 percent cut raises it 0.46 percentage points in the model and 2 points in DYNASIM3, a registered comparison with no pass or fail rule. Nothing projects family income. The follow-on test for the 1946–55 cohort (U2) is not registered: [#524][pr524] applies ruling d1090, d1242 is open, and the test's loader still refuses to run. | The comparator's income definition, unit, thresholds and ages, with uncertainty; for full parity, poverty and adequacy on projected family income by cohort and group. | [#524][pr524]; d1090, d1242 (open) | Merge #524, settle d1242, clear the loader's remaining blockers, then register U2 on #42. |
| Results by group | Urban's published DYNASIM output reports income for people 62 and older by age, sex, race and ethnicity, education and lifetime earnings ([Urban's DYNASIM output][out]); SSA's MINT adds rows by beneficiary type. | *Used in a blind test*, in part. Exercise 2 computes 15 of its source report's 36 rows and names the 21 it omits: race and ethnicity, education, labor-force experience, and own and shared lifetime earnings (`src/populace_dynamics/estimates/uniform_cut_tabulation.py`). Exercises 1 and 3 report by age and exercise 4 by sex. Rows by beneficiary type cannot be computed yet (`benchmarks/wall.md`). [#513][pr513] adds MINT's group categories as code only. | For each comparison, every cell DYNASIM or MINT publishes for that table, with the same definitions and denominators. | [#513][pr513]; [#367][i367] | Merge #513, then register group runs of the four tests on #42. |
| Behavioral responses to reform | Published DYNASIM4 analyses include assumed responses of wages, compensation and investment income to tax changes ([Five Democratic Approaches][fd]). | *None* for estimated responses. Exercise 3's registered claiming alternatives delay claims by the full rise in the retirement age, a stylized assumption with no quasi-experimental basis. | Claiming responses estimated from real policy changes and backtested against observed shifts after past increases in the retirement age; earnings and investment-income responses with their own registered estimates. | d515, which defers any claiming-response build until data identify one | Name, in a registration, the policy variation a claiming-response estimate would use. |

### Financing and the long horizon

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| National costs and financing | Reports trust-fund measures and the revenue and cost effects of reform plans ([Five Democratic Approaches][fd]). | *Report-only.* The first-estimates ledgers sum benefits and payroll taxes over the projected PSID sample, label them relative to that sample and estimate no national dollars (`src/populace_dynamics/estimates/publication.py`, `runs/first_estimates_v1.json`). Registration 18 compares the 2030 cost of a one-point COLA cut from December 2027 with the effects OACT and the Penn Wharton Budget Model publish, with a MINT5 row on benefits by age; it was posted on 30 September 2026, before any build code for it existed, and has not run. Nothing in the projections computes the income tax on benefits, part of which funds OASDI. | Per-provision changes in national OASDI cost and income by year against OACT and PWBM, with CBO second and DYNASIM one of several (d660), on a representative population with covered payroll. | [Registration 18][reg18]; d658, d660; [#113][i113] (M7) | Build and merge Registration 18's code, post the registered commit on #42, then run it once. |
| Trust funds and the 75-year balance | Reports long-run financing effects and trust-fund depletion dates ([Five Democratic Approaches][fd]; [Can Social Security Be Solvent?][solv]). | *None* for national measures. A report-only analogue on a closed PSID frame (`runs/m2_pseudo_projection_v1.json`) sets its starting reserve so that its baseline runs out in the year Urban's 2015 analysis reports, then reports how provisions shift that year; it is not a trust-fund projection. Annual OASI and DI trust-fund ratios cannot be computed (`benchmarks/wall.md`). | Annual OASI, DI and OASDI income, cost and reserves, the 75-year actuarial balance and the depletion year, at baseline and per provision, against OACT and PWBM first. | [#113][i113] (M7); d660 | Build M7's accounting on a representative, open population (see the critical path). |
| Projections beyond 2030 | Projects 75 years ahead ([DYNASIM4 fact sheet][d4]; [overview][ov]); Urban's published output tables run to 2065 ([Urban's DYNASIM output][out]). | *Built, ungated.* The engine accepts any end year (`src/populace_dynamics/engine/loop.py`), but no run goes past 2030 and gate 3 has no cells. Gate m6 scores 2015–2019 (its earnings cells, 2016 and 2018), reports 2020–2022 as a diagnostic, and says it does not certify extrapolation to 2100. Assumption paths to 2100 exist for the 2026 Trustees and CBO baselines, and the code refuses to run them on real data. | Near-term gates first (gate 3); then matched 2050, 2065 and 2070 comparisons and 75-year sensitivity surfaces on named assumption paths, each registered before it runs. | [#113][i113] | Give gate 3 its cells and tolerances; see [known gaps](#known-gaps-without-a-tracking-issue). |

### Outside this ledger's scope

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Long-term services and supports, and detailed health | Projects health, limitations in daily activities, medical and long-term care spending, and who pays ([DYNASIM4 fact sheet][d4]; [Urban's 2020 LTSS analysis][ltss]). | *None*, and outside this ledger's scope. The roadmap places long-term care in a later, adjacent track (`docs/roadmap.md`). | None needed for Social Security parity. A Social Security analysis that depends on health would need its own extension. | None | None for this ledger. |

## The critical path

Two Track B workstreams are in progress: forward earnings
([#505][pr505], then B1 v2, then the B2 registration) and payment
rules (R1 and G are built; R2, R3 and the fix for [#494][i494] come
next). The path to full parity runs through them and beyond, in this
order, and each step names what it waits on. The Track B milestones
and their dependencies come from revision 3 of the Track B design
(28 September 2026), which ruling d515 approved. The design itself is
kept outside this repository; `docs/design/track_b_b0_1_audit.md`,
`docs/design/track_b_b1_v2_amendment.md` and
`docs/design/track_b_g_gross_benefits.md` cite it.

1. **Settle the inputs every later test relies on.** The 11 October
   rulings set B2's design: a household half-sample refit arm (d765),
   six gated level cells with ten report-only (d781), and a standard
   error that resamples the PSID's design clusters within strata
   (d782). The B0.1 addendum in [#505][pr505] records them and finds
   that on this design the six cells reach 0.813 power, short of the
   0.952 the ruling assumed, so B2 is held until ruling d1342 settles
   its cells or tolerance. #505 is still a draft. The career-fill test `gate_epuf_fill` has to lock and
   score its held-out persons once ([#515][pr515], [#516][pr516],
   d927). Microcosm's frame needs the fix for the defect Registration
   19 disclosed ([microcosm#1178][mc1178]) before any projection starts
   there. B0.2, the source, exposure and power audit for every later
   empirical Track B gate, must freeze each gate's record before that
   gate registers; no B0.2 record is in the repository yet.
2. **Bridge forward earnings to the projections.** B1 v2 reproduces
   gate m6's earnings histories by reconstruction, which d622 lets
   unlock B2 with a weaker label. B2 then tests the bridge from the
   2010 cohort to the law's 2014 boundary on PSID 2012 and 2014 and
   discloses that those waves already shaped the model. H, the history
   recorder, follows B2 and keeps labor, covered and earnings-test
   earnings apart for 2010 to 2030.
3. **Build the payment rules in parallel.** R1 and G, both built, feed
   R2, the earnings-test ledger. R3, the
   adjustment at full retirement age and recomputation, follows R2.
   The fix for #494 belongs on this branch. H, R2 and R3 feed I, the
   monthly calendar that assembles payments. Any claim that depends on
   the timing of events also needs I's observational timing gate.
4. **Extend earnings to older workers and run the family process in
   the projection.** B0.2 and H come before B3, which refits earnings
   for ages 25 to 69 with gates at 62–64, 65–66 and 67–69. B2 and B3
   come before B3L, a 2006-to-2022 backtest that counts as regression
   evidence on data already seen: required for a 2030 claim, but not
   enough on its own. B3, B3L and H come before B4, which composes the
   gated marriage and divorce models with widowhood from a spouse's
   death, redraws starting states, keeps mortality apart from survey
   attrition, and sets numerical limits on marital, DI and mortality
   outcomes.
5. **Apply the earnings test and baseline claiming, then validate
   jointly.** B5 runs the earnings test with fixed claiming and reruns
   exercise 3's earnings-test hypothesis as a labeled post hoc test;
   it needs R2, R3, B3, B4, H and I. B6a, a monthly claiming hazard on
   insured people who have not yet claimed, needs B5 and I, and an
   insured-status rule the repository does not have. B6b, a claiming
   response to policy, proceeds only if data identify one (d515). J,
   joint validation on an independent holdout, needs B4, B5 and B6a.
   The first comparison on a projected population (B7) follows J.
6. **Open the population and start from Microcosm.** Run the existing
   engine from Microcosm's people once d947's registration posts, with
   starting earnings histories (H1) and gate 3's first cells. Give
   newborns and immigrants starting states and admitted processes, and
   add emigration. Moving the engine into Microcosm as an operator
   comes after.
7. **Add the outputs DYNASIM publishes.** Projected SSI, wealth,
   pensions and other income; mortality differences by income,
   education and race; complete group definitions; and projections
   past 2030. Each needs registered comparisons against DYNASIM's and
   MINT's income, poverty, replacement-rate and lifetime-benefit
   tables.
8. **Estimate national financing, then the 75-year balance.**
   Registration 18's 2030 cost test comes first, once its build code
   merges. National cost estimates
   need a representative population, covered payroll and complete
   payments. The actuarial balance also needs the open population and
   an admitted long horizon. Then come annual OASI and DI accounts and
   75-year summaries on named assumption paths, compared with OACT and
   PWBM first (d660; [#113][i113], M7).
9. **Claim parity only when every row above has its evidence.**

### Where this path differs from the draft 24-month plan

The draft 24-month plan shown at the NASI meeting on 1 October 2026,
which `docs/plans/microcosm-start.md` summarizes, puts forward
earnings in the projections in months 2 to 5 and the earnings test and
family maximum, as one item, in months 2 to 4. It leaves moving the
engine into Microcosm outside its 24 months. This path is longer in
two of those places: B1 v2, the B0.1 addendum and B2 come before
forward earnings enters a projection, and R2, R3, H and I come between
the payment rules and the projections.

## Known gaps without a tracking issue

No open issue or pull request in this repository plans a build or a
gate for these as of 11 October 2026. The roadmap issues [#74][i74]
and [#113][i113], and [#412][i412], name some of them without a plan.
Issue drafts for each are with the maintainers.

- **Mortality differences by income, education and race.** Every
  mortality model uses age and sex only.
- **Projected SSI.** SSI is computed only statically, on incomes
  already recorded.
- **Projected wealth, pensions and other income.** The model
  annuitizes reported wealth and projects none of these.
- **Complete group-output validation against DYNASIM and MINT.**
  [#513][pr513] adds MINT's group categories as code; nothing yet
  registers or scores the full set of published group cells,
  lifetime-earnings groups or beneficiary types.
- **Admitting a joint projection past 2030.** No gate scores any year
  after 2019, and gate 3 has no cells.
- **Starting states and later processes for newborns and immigrants,
  and emigration.** The entrant module has never run on real data, and
  the earlier design ([#218][pr218]) closed unmerged.
- **Moving the engine into Microcosm as an operator.** A mortality and
  ageing prototype runs on synthetic data (`docs/population-graph.md`);
  [#412][i412] lists interface changes but is not a build plan.
- **Insured status.** No code decides whether a worker is insured.
- **Alignment to targets from SSA's actuaries.** The engine has no
  alignment step, and the earlier design ([#217][pr217]) closed
  unmerged.

## Rulings cited on this page

| Ruling | Date | What it decided | Public record |
|---------|----------|-----------------------------------------|--------------------|
| d479 | 27 September 2026 | Allows post hoc reruns, labeled as such; Track A v2 reruns exercises 1 and 3 with the statutory DI computation, and treats DI and spouse dual entitlement as a separate mechanism | `docs/design/urban2010_track_a_v2.md` |
| d513 | 28 September 2026 | Ratifies the Track A v2 specification | `docs/design/urban2010_track_a_v2.md` |
| d515 | 28 September 2026 | Approves the Track B design (forward earnings, the earnings test, claiming) with its recommended defaults, among them no claiming-response build until data identify one | `docs/design/track_b_b0_1_audit.md` |
| d622 | 30 September 2026 | Lets a B1 v2 reconstructed-reproduction pass unlock B2, with the weaker label carried | [#505][pr505] |
| d658 | 30 September 2026 | Registers trust-fund test A-COLA as Registration 18, report-only | [Registration 18][reg18] |
| d660 | 30 September 2026 | Makes OACT and PWBM the primary comparators for the roadmap's trust-fund tests, CBO second and DYNASIM one of several | [#113][i113] |
| d693 | 30 September 2026 | Accepts the B0.1 audit's eight defaults for B2's registration | [#505][pr505] |
| d765, d781, d782 | 11 October 2026 | Set B2's design: household half-sample refits, six gated level cells and ten report-only, and design-cluster standard errors | [#505][pr505] |
| d1342 | Open | Whether B2 proceeds at 0.813 power or changes its cells or tolerance | [#505][pr505] |
| d905 | 10 October 2026 | Releases Registration 19's results to #42 with the frame defect disclosed | [#511][pr511] |
| d927 | 10 October 2026 | Ratifies `gate_epuf_fill`'s tolerance and lets it lock as registered | [#515][pr515] |
| d929 | Pending | Whether exercises 1, 3 and 4 rerun with learned career fills once `gate_epuf_fill` scores | Not yet public |
| d947 | Open | Whether to post the registration for starting projections from Microcosm | `docs/plans/microcosm-start-registration-draft.md` |
| d1090 | 10 October 2026 | Settles two of the 1946–55 test's (U2) blockers | [#524][pr524] |
| d1242 | Open | How U2 counts and discloses one blocker's exclusions | [#524][pr524] |

## Sources on DYNASIM

- Favreault, Melissa, and Karen E. Smith. 2004. [*A Primer on the
  Dynamic Simulation of Income Model (DYNASIM3)*][d3]. Urban Institute.
- Favreault, Melissa M., Karen E. Smith, and Richard W. Johnson. 2015.
  [*The Dynamic Simulation of Income Model (DYNASIM): An
  Overview*][ov]. Urban Institute.
- Cosic, Damir, Richard W. Johnson, and Karen E. Smith. 2024.
  [*Urban's Dynamic Simulation of Income Model 4*][d4]. Urban Institute
  fact sheet.
- Smith, Karen E. 2015. [*Can Social Security Be Solvent?*][solv]
  Urban Institute.
- Smith, Karen E., Richard W. Johnson, and Melissa M. Favreault. 2020.
  [*Five Democratic Approaches to Social Security Reform: Estimated
  Impact of Plans from the 2020 Presidential Campaign*][fd]. Urban
  Institute.
- Urban Institute. 2018. [*dynasim-shiny1: R Shiny Visualizations of
  Projections of Social Security under Different Reforms*][out].
  GitHub repository of DYNASIM output.
- Favreault, Melissa M. 2020. [*Incorporating Long-Term
  Services and Supports in Health Care Proposals: Cost and
  Distributional Considerations*][ltss]. Urban Institute.

## Keeping this page current

Update a row when a gate locks, passes or fails, when a registration
posts or runs, or when a ruling changes the plan. Check each status
against `gates.yaml`, `runs/` and the code before changing it, and
cite repository paths, pull requests, issues and public URLs only.

[d3]: https://www.urban.org/sites/default/files/publication/71226/410961-A-Primer-on-the-Dynamic-Simulation-of-Income-Model-DYNASIM-.PDF
[ov]: https://www.urban.org/research/publication/dynamic-simulation-income-model-dynasim-overview
[d4]: https://www.urban.org/research/publication/urbans-dynamic-simulation-income-model-4
[solv]: https://www.urban.org/research/publication/can-social-security-be-solvent
[fd]: https://www.urban.org/research/publication/five-democratic-approaches-social-security-reform-estimated-impact-plans-2020-presidential-campaign
[out]: https://github.com/UrbanInstitute/dynasim-shiny1
[ltss]: https://www.urban.org/research/publication/incorporating-long-term-services-and-supports-health-care-proposals
[reg18]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-5919983573
[mc1178]: https://github.com/PolicyEngine/microcosm/issues/1178
[i42]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42
[i45]: https://github.com/PolicyEngine/microcosm-dynamics/issues/45
[i74]: https://github.com/PolicyEngine/microcosm-dynamics/issues/74
[i100]: https://github.com/PolicyEngine/microcosm-dynamics/issues/100
[i113]: https://github.com/PolicyEngine/microcosm-dynamics/issues/113
[i151]: https://github.com/PolicyEngine/microcosm-dynamics/issues/151
[i367]: https://github.com/PolicyEngine/microcosm-dynamics/issues/367
[i403]: https://github.com/PolicyEngine/microcosm-dynamics/issues/403
[i412]: https://github.com/PolicyEngine/microcosm-dynamics/issues/412
[i494]: https://github.com/PolicyEngine/microcosm-dynamics/issues/494
[i495]: https://github.com/PolicyEngine/microcosm-dynamics/issues/495
[pr217]: https://github.com/PolicyEngine/microcosm-dynamics/pull/217
[pr218]: https://github.com/PolicyEngine/microcosm-dynamics/pull/218
[pr405]: https://github.com/PolicyEngine/microcosm-dynamics/pull/405
[pr492]: https://github.com/PolicyEngine/microcosm-dynamics/pull/492
[pr505]: https://github.com/PolicyEngine/microcosm-dynamics/pull/505
[pr511]: https://github.com/PolicyEngine/microcosm-dynamics/pull/511
[pr513]: https://github.com/PolicyEngine/microcosm-dynamics/pull/513
[pr515]: https://github.com/PolicyEngine/microcosm-dynamics/pull/515
[pr516]: https://github.com/PolicyEngine/microcosm-dynamics/pull/516
[pr524]: https://github.com/PolicyEngine/microcosm-dynamics/pull/524
