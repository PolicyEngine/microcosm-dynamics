# DYNASIM parity ledger

Microcosm Dynamics aims to answer the Social Security questions that
the Urban Institute's DYNASIM answers, with code, data and tests that
anyone can rerun. The goal is a model that follows a representative
population year by year, applies the program's rules to each life,
and reports what a reform does to benefits, poverty and the program's
finances, by cohort and group, decades ahead. This page lists what
full parity with DYNASIM for Social Security analysis requires, one
capability at a time, and where each piece stands.

*Statuses verified against the repository at commit `ad42ecc0` and
against the open pull requests and issues on 18 October 2026.*

## Bottom line

Parity with DYNASIM is not yet demonstrated. We test components
against pre-registered tests, which we call gates. Seven gates locked
in `gates.yaml` pass, four of them only under amendments we adopted
after an earlier attempt failed. An eighth, `gate_epuf_fill`, certifies
one learned career fill. The other fill it adopted improves on the
current rule but is not certified. A further pre-registered test, of
forward earnings, failed: B2, which carried the forward-earnings law
from 2010 to 2014, projected a zero-earnings rate about 35 percent
above the PSID's for adults aged 25 to 44, so the steps that depend on
it are blocked. The four blind comparisons with
DYNASIM3 use none of the components these gates certify, and the comparisons carry no
pass or fail threshold: each reports its gaps without grading them.
None involves DYNASIM4, Urban's current version.

What separates the model from DYNASIM today falls into three groups.
The two projections compared with DYNASIM3 draw no earnings,
marriages, divorces or births after 2010, check no one's insured
status and apply no retirement earnings test. The population is
effectively closed: no model of immigration or emigration runs on real
data, and the two comparison projections add no one after they start.
And the model produces no national cost estimate,
trust-fund balance or depletion date, and projects no SSI, wealth or
pension income.

## How to read the ledger

Each row is one capability. The columns say what DYNASIM does, where
Microcosm Dynamics stands, what test would show parity, which pull
request, issue or decision tracks the work, and the next step.

The status column uses six terms, and a row can carry more than one:

- *None*: no code in the repository does this.
- *Built, ungated*: code exists, but no pre-registered gate scores it.
- *Gate passed*: the component passes a gate whose terms are locked in
  `gates.yaml`, or a Track B gate registered on [#42][i42], and the
  scored run is committed under `runs/` (B1 v2's outputs are sealed
  outside the repository).
- *Gate failed*: a registered gate scored the component and it failed,
  and the failure is published. For Track B's B2, a failure means the
  component is not admitted and nothing that depends on it may rely on
  it.
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
| Earnings histories | Builds each person's lifetime earnings history from survey and administrative records ([overview][ov]; [DYNASIM4 fact sheet][d4]). | *Gate passed* for the generated earnings process: gate 1 passes (`runs/gate1_rank_knn_v5.json`), scoring 1998–2022 at ages 25–59, not whole careers. *Used in a blind test* for the recorded PSID careers that exercises 1, 3 and 4 read; the paper reports that about half of the career years through 2010 for the 7,486 cohort members who reach 62 between 1979 and 2030 hold imputed or zero values. Those careers' fill rules fail `gate_epuf_fill`, which scored them as its reference arm on 878,481 held-out people in SSA's Earnings Public-Use File: the odd-year neighbour mean fails 100 of 183 gating cells, and the zero pre-career rule fails 131 of 136 (`runs/epuf_fill_gate_test_v1.json`). The gate locked on 13 October ([#515][pr515]) and scored once ([#537][pr537]). *Gate passed, not used in a blind test*, for the learned pre-career fill, which fails 0 of 136 cells. The learned odd-year fill fails 8 of 183, so the gate adopts it as an improvement without certifying it. Both fills are opt-in, and no blind test uses them. | Whole careers set against SSA's Earnings Public-Use File by birth cohort and sex: years without covered earnings, low-earnings years, persistence and the 35-year AIME, including low earners and broken careers. | [#515][pr515], [#516][pr516], [#537][pr537]; d927, d929 (parked); [result][resepuf] | d929 decides whether exercises 1, 3 and 4 rerun with the learned fills. |
| Covered earnings and agreement with SSA records | Separates employment that Social Security covers from noncovered employment ([DYNASIM3 primer][d3]). | *None* for a covered/noncovered split: the projections and the Axiom bridge treat all PSID labor income as covered, and the correction design is a draft (`docs/design/covered_earnings_correction.md`). *Report-only* for the comparison of the PSID's own 1998–2004 earnings with SSA's public-use file: `gate_epuf` closed without locking and has scored no model output (`docs/amendments/gate_epuf_registration_proposal.md`). | A covered/noncovered split of PSID earnings, checked against SSA's totals of covered workers and taxable earnings, and a fresh gate on the public-use file with power beyond gate 1. | [#403][i403], open but idle: it belongs to the correction campaign, which stopped on 9 September 2026, and that campaign's last design PR, [#405][pr405], closed unmerged | Decide whether to restart the covered-earnings correction, now as a registered gate. |
| Forward earnings | Projects employment, hours, wages and pension coverage each year ([DYNASIM4 fact sheet][d4]). | *Gate passed* for gate m6; *Gate failed* for B2; not used in a blind test. The forward law, fitted on PSID earnings through 2014 at ages 25–64, passes gate m6 in 4 of 5 seeds (`runs/gate_m6_candidate3_v1.json`). In every seed, its two-year earnings growth at ages 25 to 44 runs below the PSID's. B2 carried the same law from the 2010 cohort to the earnings years 2012 and 2014, which the PSID collected in its 2013 and 2015 interviews, and failed on 18 October ([result][resb2]). Its projected zero-earnings rate for people aged 25 to 44 at those interviews is about 35 percent above the PSID's: the gap is 0.30 on a log scale against a tolerance of 0.20, and it exceeds the tolerance in all 5 of the test's household splits. Three of its four gated bounds also exceed their tolerances; only the 90th percentile of positive earnings at ages 25 to 44 passes every check (`runs/track_b_b2_score.json`). The law has no fitted distribution above 64, and both projection tests draw no earnings after 2010 (`src/populace_dynamics/cola_track_a/adapters.py`). | Track B's sequence: B1 v2 reproduces gate m6's histories; B2 tests the bridge from the 2010 cohort to the law's 2014 boundary on PSID earnings for 2012 and 2014. Under d1606 it gates four level cells, the 90th percentile and the zero-earnings rate by cohort, and reports twelve more, the medians among them. B3 refits ages 25–69 with gates at 62–64, 65–66 and 67–69; B3L backtests 2006 to 2022; an independent joint holdout comes before any 2030 claim. Because B2 gates levels only, growth and persistence need their own test. | [#505][pr505], [#526][pr526], [#545][pr545], [#547][pr547], [#548][pr548]; d515, d622, d693, d765, d781, d782, d1342, d1606, d1659; [B1 v2 registration][regb1], [B2 registration][regb2] | B1 v2 passed on 11 October ([result][resb1]). B2's failure is attempt 1 on Track B's cumulative attempt ledger (`docs/design/track_b_attempt_ledger.md`); two failed successors would pause the mechanism. Under d1659, the next step is a successor earnings law, designed first: its change must rest on evidence independent of B2's 2012 and 2014 result, and its design comes to the maintainer before any registration. |

### Disability, mortality and claiming

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Work limitation | Models work-limiting disability from demographic and economic characteristics ([DYNASIM3 primer][d3]). | *Gate passed, not used in a blind test.* Gate m4 passes in 5 of 5 seeds (`runs/gate_m4_hazard_v1.json`), and gate m6 also gates its incidence and recovery. Its SSA anchors test age shape and exit composition, not disability insurance (DI) levels. The blind projections use a separate DI component and read work-limitation reports only to classify people at the start. | Work limitation linked to employment and to DI awards in the same simulated people, checked against PSID reports and SSA award statistics. | None for the link; Track B's B4 sets limits on DI outcomes (d515), and B4 waits on a successor to B2 (d1659) | Decide whether projected DI awards should depend on work-limitation status; if so, register a joint gate. |
| Disability insurance entitlement | Models DI applications and awards and computes disability benefits ([DYNASIM3 primer][d3]). | *Used in a blind test, ungated.* Exercises 1 and 3 draw awards, recoveries and conversion at full retirement age from rates fitted on data through 2008, and never check insured status (`src/populace_dynamics/engine/di_entitlement.py`). A report-only check against SSA's 2023 statistics runs on a synthetic population (`runs/di_entitlement_asr2023_validation_v1.json`). The statutory DI computation-years rerun (Track A v2, `src/populace_dynamics/track_a_v2/`) is merged, has run only on invented data and is not registered. | Awards, recoveries, deaths, conversions, beneficiary counts and benefit amounts on the projected population against SSA statistics, with disability-insured status, statutory computation years and stocks that reconcile with flows. | d479, d513; [#42][i42] | Register Track A v2 on #42 and run it once. It computes delayed credits through the oracle, so its registration must use the statutory window or disclose the 48-month cap (see the row on a worker's own benefit). Then register a DI entitlement gate on the PSID cohort. |
| Mortality and its improvement over time | Projects deaths with trends over time, socioeconomic differences and a separate process for disabled workers ([DYNASIM3 primer][d3]), aligned to targets from SSA's actuaries ([DYNASIM4 fact sheet][d4]). | *Used in a blind test, ungated.* Exercises 1 and 3 scale SSA's 2004 period life table by two ratios from the 2008 Trustees Report, one under 65 and one at 65 and over, the same for men and women (`src/populace_dynamics/cola_track_a/mortality.py`); disabled workers die at DI rates. Gate m6 certifies nothing about mortality drift, and its SSA/NCHS mortality anchor is marked not supplied in the passing run. | Projected death probabilities and life expectancy by single year of age and sex against OACT's tables over held-out years; disabled-worker deaths against SSA counts; deaths kept apart from survey attrition at the oldest ages. | [#74][i74], [#113][i113] | Supply gate m6's mortality anchor, then replace the two-ratio method with OACT's single-age death probabilities, which the 2026 baseline already loads (`src/populace_dynamics/baselines/tr2026_intermediate.py`). |
| Mortality differences by income, education and race | Models mortality differences by socioeconomic characteristics ([DYNASIM3 primer][d3]). | *None.* No mortality model in the repository conditions on income, education or race. The general models use age and sex. Disabled workers die at DI rates by age and sex; under the optional select-and-ultimate basis those rates also depend on age at award and the years since, but the default and the blind tests use attained age only (`src/populace_dynamics/engine/di_entitlement_rates.py`). A comparison of PSID death rates with NCHS rates by age and sex is report-only (`runs/mortality_floors_v1.json`). | Survival gradients by lifetime earnings, education and race and ethnicity against published SSA and NCHS evidence, and the lifetime-benefit differences that follow. | None; [#74][i74] names "differential mortality" as a component but defines no socioeconomic gradient | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Claiming | Claiming depends on benefit amounts, spouse characteristics and policy parameters, with separate equations by earnings relative to the earnings test's exempt amount ([DYNASIM3 primer][d3]). | *Used in a blind test, ungated.* Exercises 1 and 3 draw a whole-year claim age from SSA's distribution of retired-worker awards by sex and year, reusing the 2008 distribution for later years (`src/populace_dynamics/engine/claiming.py`). No claim responds to a reform; exercise 3's two registered claiming alternatives are stylized delays. | A monthly claiming hazard on insured people who have not yet claimed, reproducing held-out SSA award flows (B6a); separately, a response to policy identified from real policy changes, with placebo tests (B6b). | d515 | Register a baseline claiming test on held-out years of SSA's award table once insured status exists. |

### Family and population

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Marriage, divorce and widowhood | Projects marriage, divorce, remarriage and widowhood ([DYNASIM4 fact sheet][d4]; [overview][ov]). | *Gate passed, not used in a blind test.* Gates 2, 2b and 2c pass in 4 of 5 seeds each, and gate m6 scores first-marriage, divorce and remarriage flows over 2015–2019. The blind projections draw no marriage or divorce: a person is widowed only when a spouse in the cohort dies (`src/populace_dynamics/cola_track_a/adapters.py`), so 552 married members of the 2011-wave cohort whose spouses are outside it, and 80 with no linked spouse, are never widowed (`runs/replication_urban2010_cola_v1.json`). | The gated marriage and divorce models inside the projection, with redrawn starting states and spouses outside the cohort simulated; flows, durations, spouse links and the resulting spouse and survivor benefits, scored by a registered projection gate (B4). | d515 | Register B4 once B3, B3L and the history recorder H exist. All three wait on a successor to B2 (d1659). |
| Education | Projects educational attainment from cross-tabulations by age, race, sex and parents' education, estimated on the NLSY and CPS ([DYNASIM3 primer][d3]). | *None* for transitions: the engine's eight modules (mortality, aging, marital core, fertility, disability, earnings, claiming and household composition; `src/populace_dynamics/engine/loop.py`) include no education step. Completed education is read from the PSID as a fixed attribute for group breakdowns (`src/populace_dynamics/data/group_attributes_psid.py`, from [#513][pr513]). | Projected attainment by birth cohort and sex against Census and ACS attainment tables, and its effect on later earnings and mortality where those depend on it. | None | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Births | Adds people through births and aligns fertility to targets from SSA's actuaries ([DYNASIM4 fact sheet][d4]). | *Gate passed* for fertility rates (gate 2). *Report-only* for newborns entering a projection: gate m6's engine adds them (316 in its reference draw) and scores none. The blind projections add no newborns. A newborn gets a link to the mother, her household and her weight, and no father link. An opt-in, report-only birth step can draw births from the 2026 Trustees' or CBO's fertility schedule (`src/populace_dynamics/baselines/fertility.py`); no registered test uses it, and nothing aligns the gated fertility model to those targets. | Projected births against vital statistics; newborns' links to both parents, households and starting states; their entry into later earnings, disability and benefit processes. | [#412][i412] | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Immigration and emigration | Adds immigrants and models emigration ([DYNASIM4 fact sheet][d4]). | *Built, ungated*, and never run on real data. A scheduled-entrant module labels itself report-only (`src/populace_dynamics/engine/entrant_schedule.py`), but its readers for arrival totals and donor records were not carried over, no committed run has added an immigrant, and entrants get no earnings, disability, claiming or entitlement processes (`src/populace_dynamics/engine/entrant_domains.py`). The US engine has no emigration. | Arrivals and departures sized to OACT's assumptions; entrants' covered-work histories and insured status; their benefit receipt against SSA statistics. | [#412][i412]; design PR [#218][pr218] closed unmerged | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Starting population | Starts from a representative sample built mainly from the Survey of Income and Program Participation, with histories drawn from survey and administrative records ([DYNASIM4 fact sheet][d4]; [overview][ov]). | *Used in a blind test* for closed PSID cohorts: all four comparisons start from PSID members with the PSID's own weights. *None* for a projection started from Microcosm's population: a plan and a draft registration exist (`docs/plans/microcosm-start.md`, `docs/plans/microcosm-start-registration-draft.md`), with no code. Registration 19 ran a static, report-only SSI analysis on Microcosm's frame and disclosed a frame defect; its code merged in [#511][pr511] (`runs/pe_us_depletion_cut_population_v1.json`). Microcosm fixed that defect in its build code ([microcosm#1186][mc1186]), and four more frame defects are open: [microcosm#1212][mc1212], [#1213][mc1213], [#1214][mc1214] and [#1215][mc1215]. | Starting earnings histories (H1), the starting population against SSA counts, gate 3's first-year cells, then an end-to-end projection and reform comparison started from Microcosm. | d947 (parked); [#511][pr511]; [microcosm#1178][mc1178], [microcosm#1186][mc1186] | Post the Microcosm-start registration (d947), then build the frame reader. |
| Alignment and a representative population | Aligns fertility, mortality, disability, immigration and labor force participation to targets from SSA's actuaries ([DYNASIM4 fact sheet][d4]). | *None* for alignment: the engine has no alignment step, and gate m6 records its alignment report as not computed. *Gate passed, not used in a blind test*, for transport: gate w1 places the PSID-fitted processes on Microcosm's CPS-based frame and matches 43 cross-sectional cells and one ordering check (`runs/gate_w1_candidate4_v1.json`, `runs/NOTES-gate_w1_candidate4.md`). It certifies no transition, and its SSA benefit cells are report-only. | An alignment step to the actuaries' demographic and labor targets that keeps households consistent, with its displacement from the unaligned path published; gated SSA benefit and payment totals. | [#151][i151]; design PR [#217][pr217] closed unmerged; [#531][i531], which reports that w1's family-A marital and household targets come from a frame that [microcosm#1212][mc1212] finds skewed toward couples, and d1406 (open) on how to amend them. w1's committed run is unchanged | See [known gaps](#known-gaps-without-a-tracking-issue). |

### Benefit rules and payments

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Insured status | Its benefit calculator checks whether each worker is insured ([DYNASIM3 primer][d3]). | *None.* No code decides fully, currently or disability insured status. The projections pay a retired-worker benefit to anyone whose career through 2010 yields a positive benefit, and DI awards never check it. Exercise 4 counts years of coverage for its minimum benefit (`src/populace_dynamics/min_benefit_track_m/coverage.py`), which is not an insured-status test. | The statute's insured-status rules checked against SSA's worked examples, then the share of projected claimants, survivors and DI awardees who would fail them. | None | See [known gaps](#known-gaps-without-a-tracking-issue). |
| A worker's own benefit and claiming adjustments | Computes benefits under historical and projected program rules from each person's lifetime record ([overview][ov]; [Five Democratic Approaches][fd]). | *Used in a blind test, ungated.* The Python oracle (`src/populace_dynamics/ss/`) computes AIME, PIA and early and delayed claiming adjustments; no gate scores it. The projection tests count a fixed 35 computation years; a statutory count exists (`src/populace_dynamics/ss/statutory_aime.py`) but they do not use it. Its delayed credits stop at age 70 or 48 months after full retirement age, whichever comes first, which leaves people born 1917–1942 2 to 12 months short of the law. [#532][pr532] added the statutory window beside the oracle (`src/populace_dynamics/ss/statutory_delayed_credit.py`), with a differential test against G; the oracle, and so the blind tests, still use the cap. A diagnostic under ruling d1408 ([#538][pr538]; [erratum note][errdc]) reproduced five registered results under the cap, recomputed them with the statutory window, and found that none of the values it published changes. It bounded the sixth, the first estimates, instead of recomputing it (`docs/errata/2026-10-11-delayed-credit-window.md`). | Statutory worked examples for every birth cohort, delayed credits included, and a differential test against Track B's gross-benefit layer and Axiom. | [#494][i494] (closed by #532), [#532][pr532], [#538][pr538]; d1408 | Any rerun or new registration that reaches the 1917–1942 window, Track A v2 among them, uses the statutory window or discloses the cap. |
| Spouse and survivor benefits, and dual entitlement | Computes spouse, survivor and divorced-spouse benefits from work and marriage histories ([DYNASIM3 primer][d3]). | *Used in a blind test, ungated*, for spouse and aged widow(er) benefits only. Exercises 1, 3 and 4 use the oracle's spouse and survivor formulas, which tests check against SSA's worked examples. No comparison computes divorced-spouse, child, or mother's or father's benefits, and in the projections a person receiving DI on their own record gets no spouse's benefit. The Track A v2 rerun adds that case and has run only on invented data. | SSA's worked examples, then counts and average amounts by beneficiary type against SSA's published tables, on a projection that links former spouses. | d479, d513; [#42][i42] | Register and run Track A v2, as in the DI row. |
| Family maximum and gross family benefits | The 2004 primer says DYNASIM3 left out children's benefits and the family maximum ([DYNASIM3 primer][d3]); we have not established how DYNASIM4 treats them. | *Built, ungated.* Track B's gross-benefit layer, G (`src/populace_dynamics/track_b/gross_benefits.py`, merged in [#492][pr492]), computes the family maximum, its redistribution, age reductions, dual-entitlement offsets and the whole-dollar payment for one worker's record in one month, and its tests check SSA's worked examples. It refuses some families, among them beneficiaries entitled on more than one record and cases the 1972 savings clause governs; ruling d1338 adopts SSA's operational reading of that clause, which is not yet built. The earnings-test ledger and recomputation modules in the next row build on G. No projection uses any of them. G v2 ([#530][pr530], open) says it computes five configurations G now refuses. | A registered conformance run reporting, over a defined population of families, the share computed and the share refused by reason; then monthly family payments against SSA's family-benefit statistics. | d515, d1338, d1418; [#495][i495]; [#530][pr530] | Merge G v2, then G part 2 (d1338's reading and R2 part (b)), then the monthly assembly (I) that would carry G into projections. |
| Retirement earnings test | Applies the earnings test when computing the benefits people actually receive ([DYNASIM3 primer][d3]). | *Built, ungated.* Track B's R1 pins SSA's exempt amounts for 2000–2026 and the 1/2 and 1/3 withholding rates, and projects later amounts by the statutory formula (`src/populace_dynamics/track_b/ret_params.py`). R2 part (a) ([#528][pr528]) computes one record's calendar-year test: excess earnings, charging, provisional suspension against final deduction and the partial monthly benefit, with grace years decided by a separate helper (`track_b/ret_ledger.py`, `track_b/ret_grace.py`). R3 ([#529][pr529]) adjusts the reduction factor at full retirement age and recomputes for later earnings (`track_b/arf.py`, `track_b/recompute.py`). Their tests check SSA, POMS and CFR worked examples. R2 part (b) is refused by name (`DEDUCTION_BEFORE_REDUCTION`): when an auxiliary beneficiary's earnings deduction would free room under a binding family maximum, the maximum would need readjusting. No projection applies the test. | R2 reproduces SSA's worked examples of suspension, deductions and the grace year, exact after rounding; R3 adjusts the reduction at full retirement age and recomputes for later earnings; then B5 runs the test inside a projection with forward earnings at ages 62 to 69. | d515, d1418; [#528][pr528], [#529][pr529] | Build R2 part (b) after G part 2. B5, the test inside a projection, also needs H, which waits on a successor to B2, and I. |
| Benefit rules run in Axiom | Uses rule-based calculators for Social Security and SSI ([overview][ov]; [DYNASIM4 fact sheet][d4]). | *Built, ungated.* Axiom reproduces the Python oracle's AIME for all 7,486 people tested, as the paper reports, on encodings that remain unaccepted candidates (`src/populace_dynamics/axiom_benefit_bridge.py`); no artifact in `runs/` pins that result yet. A committed artifact shows Axiom matching the oracle's PIA to the cent for 240 synthetic workers in the 2020 and 2026 eligibility cohorts (`runs/pia_cross_engine_v1.json`); on the PSID cohort, nothing beyond AIME has been compared. The blind tests that compute benefits use the Python oracle. PolicyEngine-US computes a worker's own AIME and PIA but has no spouse or survivor benefit formulas and takes those benefits as inputs (`src/populace_dynamics/ss/params.py`, `docs/technical-specifications.md`). | Cohort-wide differential checks of Axiom against the oracle and G for PIA, own, auxiliary and DI benefits, the family maximum, the earnings test and the monthly payment, on accepted encodings, each pinned by a committed artifact. | [#100][i100] (workstream W3) | Commit the AIME agreement as a `runs/` artifact with a reproduction test. |

### Income, poverty and groups

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Supplemental Security Income (SSI) | Applies SSI's income and resource rules and models eligibility, participation and benefits ([DYNASIM3 primer][d3]). | *Used in a blind test*, static. Exercise 2 offsets the cut for people who already report SSI and enrolls no one new (`src/populace_dynamics/estimates/adjusted_poverty.py`); in its committed run, the registered alternative SSI rules leave the headline unchanged. Registration 19 computed SSI's asset test on Microcosm's frame through PolicyEngine-US, static and report-only, with a disclosed frame defect; its code merged in [#511][pr511]. Microcosm fixed that defect in its build code ([microcosm#1186][mc1186]); Registration 19 has not been rerun. [microcosm#1215][mc1215], open, concerns resources on the same frame. Nothing projects SSI. | Eligibility, resource, deeming and state-supplement worked examples; participation against SSA caseloads by age and type; then projected caseloads, payments and the poverty effect of a Social Security cut. | [#511][pr511]; d905, d1414 (open); [microcosm#1178][mc1178], [microcosm#1186][mc1186], [microcosm#1215][mc1215] | Register and run the rerun once a rebuilt, certified frame exists, and settle d1414 on a Registration 19 addendum; see [known gaps](#known-gaps-without-a-tracking-issue) for projected SSI. |
| Wealth, pensions and other income | Projects pension coverage and benefits, retirement-account balances and withdrawals, asset income and wealth ([DYNASIM4 fact sheet][d4]; [overview][ov]). | *Used in a blind test* for reported wealth only: exercise 2 turns PSID-reported wealth into an annuity income (`src/populace_dynamics/estimates/adjusted_poverty.py`). *None* for projection: the model projects no wealth, pensions or asset income. | Projected pension coverage and benefits, account balances and drawdowns, asset income and wealth by cohort and lifetime-earnings group, first against later PSID waves the model did not see, then against DYNASIM's published tables. | None; [#45][i45] reserves balance-sheet state for capital gains and plans no wealth or pension projection | See [known gaps](#known-gaps-without-a-tracking-issue). |
| Poverty and income distribution | Reports poverty, adequacy and distributional effects of reforms from projected family income ([Five Democratic Approaches][fd]). | *Used in a blind test*, static. Exercise 2 computes adjusted poverty at 67 on incomes the PSID recorded: a 13 percent cut raises it 0.46 percentage points in the model and 2 points in DYNASIM3, a registered comparison with no pass or fail rule. Nothing projects family income. The follow-on test for the 1946–55 cohort (U2) is not registered yet. Its source loader now reports no blockers ([#524][pr524], [#540][pr540]), and its specification records steps 1 to 3 of its execution record as done ([#544][pr544]). Step 4, a structural pass that reads real PSID records and computes structural and reconciliation counts plus the named F17 component summaries, without computing poverty, is authorized to run once (d1649), after a check that the staged PSID inputs still match U1's pinned digest (d1597) and once [#546][pr546] adds the person count ruling d1242 calls for. | The comparator's income definition, unit, thresholds and ages, with uncertainty; for full parity, poverty and adequacy on projected family income by cohort and group. | [#524][pr524], [#525][pr525], [#539][pr539], [#540][pr540], [#542][pr542], [#544][pr544], [#546][pr546]; d637, d745, d1090, d1242, d1597, d1649 | Merge #546, run the d1597 check and the step-4 pass, then the specification's steps 5 to 8: the parameter block, ratification, a fresh forecast and the #42 registration. |
| Results by group | Urban's published DYNASIM output reports income for people 62 and older by age, sex, race and ethnicity, education and lifetime earnings ([Urban's DYNASIM output][out]); SSA's MINT adds rows by beneficiary type. | *Used in a blind test*, in part. Exercise 2 computes 15 of its source report's 36 rows and names the 21 it omits: race and ethnicity, education, labor-force experience, and own and shared lifetime earnings (`src/populace_dynamics/estimates/uniform_cut_tabulation.py`). Exercises 1 and 3 report by age and exercise 4 by sex. Rows by beneficiary type cannot be computed yet (`benchmarks/wall.md`). [#513][pr513], merged on 11 October, adds MINT's group categories as code only; no real-data group run is registered. | For each comparison, every cell DYNASIM or MINT publishes for that table, with the same definitions and denominators. | [#513][pr513]; [#367][i367] | Register group runs of the four tests on #42. |
| Behavioral responses to reform | Published DYNASIM4 analyses include assumed responses of wages, compensation and investment income to tax changes ([Five Democratic Approaches][fd]). | *None* for estimated responses. Exercise 3's registered claiming alternatives delay claims by the full rise in the retirement age, a stylized assumption with no quasi-experimental basis. | Claiming responses estimated from real policy changes and backtested against observed shifts after past increases in the retirement age; earnings and investment-income responses with their own registered estimates. | d515, which defers any claiming-response build until data identify one | Name, in a registration, the policy variation a claiming-response estimate would use. |

### Financing and the long horizon

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| National costs and financing | Reports trust-fund measures and the revenue and cost effects of reform plans ([Five Democratic Approaches][fd]). | *Report-only.* The first-estimates ledgers sum benefits and payroll taxes over the projected PSID sample, label them relative to that sample and estimate no national dollars (`src/populace_dynamics/estimates/publication.py`, `runs/first_estimates_v1.json`). Registration 18 compares the 2030 cost of a one-point COLA cut from December 2027 with the effects OACT and the Penn Wharton Budget Model publish, with a MINT5 row on benefits by age; it was posted on 30 September 2026, before any build code for it existed, and has not run. Nothing in the projections computes the income tax on benefits, part of which funds OASDI. | Per-provision changes in national OASDI cost and income by year against OACT and PWBM, with CBO second and DYNASIM one of several (d660), on a representative population with covered payroll. | [Registration 18][reg18]; d658, d660; [#113][i113] (M7) | Build and merge Registration 18's code, post the registered commit on #42, then run it once. |
| Trust funds and the 75-year balance | Reports long-run financing effects and trust-fund depletion dates ([Five Democratic Approaches][fd]; [Can Social Security Be Solvent?][solv]). | *None* for national measures. A report-only analogue on a closed PSID frame (`runs/m2_pseudo_projection_v1.json`) sets its starting reserve so that its baseline runs out in the year Urban's 2015 analysis reports, then reports how provisions shift that year; it is not a trust-fund projection. Annual OASI and DI trust-fund ratios cannot be computed (`benchmarks/wall.md`). | Annual OASI, DI and OASDI income, cost and reserves, the 75-year actuarial balance and the depletion year, at baseline and per provision, against OACT and PWBM first. | [#113][i113] (M7); d660 | Build M7's accounting on a representative, open population (see the critical path). |
| Projections beyond 2030 | Projects 75 years ahead ([DYNASIM4 fact sheet][d4]; [overview][ov]); Urban's published output tables run to 2065 ([Urban's DYNASIM output][out]). | *Built, ungated.* The engine accepts any end year (`src/populace_dynamics/engine/loop.py`), but no population projection runs past 2030 and gate 3 has no cells. The report-only M2 analogue computes benefits on a closed frame through 2057 and keeps its ledger to 2075 (`runs/m2_pseudo_projection_v1.json`). Gate m6 scores 2015–2019 (its earnings cells, 2016 and 2018), reports 2020–2022 as a diagnostic, and says it does not certify extrapolation to 2100. Assumption paths to 2100 exist for the 2026 Trustees and CBO baselines, and the code refuses to run them on real data. | Near-term gates first (gate 3); then matched 2050, 2065 and 2070 comparisons and 75-year sensitivity surfaces on named assumption paths, each registered before it runs. | [#113][i113] | Give gate 3 its cells and tolerances; see [known gaps](#known-gaps-without-a-tracking-issue). |

### Outside this ledger's scope

| Capability | What DYNASIM does | Our status | Test that would show parity | Tracking | Next step |
|-----------|----------------|------------------------|---------------|--------|-----------|
| Long-term services and supports, and detailed health | Projects health, limitations in daily activities, medical and long-term care spending, and who pays ([DYNASIM4 fact sheet][d4]; [Urban's 2020 LTSS analysis][ltss]). | *None*, and outside this ledger's scope. The roadmap places long-term care in a later, adjacent track (`docs/roadmap.md`). | None needed for Social Security parity. A Social Security analysis that depends on health would need its own extension. | None | None for this ledger. |

## The critical path

Two Track B workstreams are in progress. In forward earnings, B1 v2
passed and B2 failed on 18 October; a successor to B2 is being
designed (d1659). In payment rules, R1, G, R2 part (a), R3 and the fix
for [#494][i494] are built, and G v2 ([#530][pr530]), G part 2, R2
part (b) and I come next. The path to full parity runs through them and beyond, in this
order, and each step names what it waits on. The Track B milestones
and their dependencies come from revision 3 of the Track B design
(28 September 2026), which ruling d515 approved. The design itself is
kept outside this repository; `docs/design/track_b_b0_1_audit.md`,
`docs/design/track_b_b1_v2_amendment.md` and
`docs/design/track_b_g_gross_benefits.md` cite it.

1. **Settle the inputs every later test relies on.** The 11 October
   rulings set B2's design: a household half-sample refit arm (d765),
   gated level cells with the rest report-only (d781), and a standard
   error that resamples the PSID's design clusters within strata
   (d782); the B0.1 addendum in [#505][pr505] records them. On the
   PSID's real floor the six cells d781 named reached 0.557 power, so
   under d1342 B2 stopped at its floor build before any candidate
   result ([floor stop][stopb2]). Ruling d1606 then gated four cells,
   the 90th percentile and the zero-earnings rate by cohort, at the
   registered tolerance. The career-fill test `gate_epuf_fill` locked
   and scored once ([#537][pr537]); d929 decides whether the blind
   tests rerun with its fills. Microcosm fixed the defect Registration
   19 disclosed in its build code ([microcosm#1186][mc1186]), and four
   more frame defects are open ([microcosm#1212][mc1212] to
   [#1215][mc1215]); a projection started there needs a rebuilt,
   certified frame. B0.2, the source, exposure and power audit for
   every later empirical Track B gate, must freeze each gate's record
   before that gate registers; no B0.2 record is in the repository
   yet. B2's medians are an open item for B0.2.
2. **Bridge forward earnings to the projections.** B1 v2 reproduces
   gate m6's earnings histories by reconstruction, which d622 lets
   unlock B2 with a weaker label. It passed on 11 October
   ([result][resb1]). B2 tested the bridge from the 2010 cohort to the
   law's 2014 boundary on PSID earnings for 2012 and 2014, disclosing
   that those years already shaped the model, and failed on 18 October
   ([result][resb2]): the law projects too many prime-age adults with
   no earnings. Under d1659 a successor law is designed first, on
   evidence independent of that result, and comes to the maintainer
   before it registers; it would be attempt 2 on Track B's attempt
   ledger (`docs/design/track_b_attempt_ledger.md`), and two failed
   successors pause the mechanism. H, the history recorder, follows a
   passing B2 and keeps labor, covered and earnings-test earnings apart
   for 2010 to 2030.
3. **Build the payment rules in parallel.** R1 and G are built, and so
   are R2 part (a), the earnings-test ledger, and R3, the adjustment at
   full retirement age and recomputation ([#528][pr528], [#529][pr529]).
   The fix for #494 merged in [#532][pr532]. G v2 ([#530][pr530]) and G
   part 2, which carries ruling d1338 and R2 part (b), come next. H, R2
   and R3 feed I, the
   monthly calendar that assembles payments. Any claim that depends on
   the timing of events also needs I's observational timing gate.
4. **Extend earnings to older workers and run the family process in
   the projection.** B0.2 and H come before B3, which refits earnings
   for ages 25 to 69 with gates at 62–64, 65–66 and 67–69. A passing
   B2 and B3 come before B3L, a 2006-to-2022 backtest that counts as regression
   evidence on data already seen: required for a 2030 claim, but not
   enough on its own. B3, B3L and H come before B4, which composes the
   gated marriage and divorce models with widowhood from a spouse's
   death, redraws starting states, keeps mortality apart from survey
   attrition, and sets numerical limits on marital, DI and mortality
   outcomes. Only B0.2 in this step is independent of B2's result.
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
   engine from Microcosm's people once d947, now parked, posts its
   registration, with
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
   merges. National cost estimates need a representative population,
   covered payroll and complete payments. The actuarial balance also needs the open population and
   an admitted long horizon. Then come annual OASI and DI accounts and
   75-year summaries on named assumption paths, compared with OACT and
   PWBM first (d660; [#113][i113], M7).
9. **Claim parity only when every row above has its evidence.**

### Where this path differs from the draft 24-month plan

The draft 24-month plan shown at the NASI meeting on 1 October 2026,
which `docs/plans/microcosm-start.md` summarizes, puts forward
earnings in the projections in months 2 to 5 and the earnings test and
family maximum, as one item, in months 2 to 4. It leaves moving the
engine into Microcosm outside its 24 months. The plan predates the
11 October rulings. Applying the earnings test in a projection needs
R2 part (b), H and I as well as the built R2 part (a) and R3 (step 3
above), which the plan does not list as separate items.

## Known gaps without a tracking issue

No open issue or pull request in this repository plans a build or a
gate for these as of 18 October 2026. The roadmap issues [#74][i74]
and [#113][i113], and [#412][i412], name some of them as future work;
none has a registered gate or a build under way.
Issue drafts for each are with the maintainers.

- **Mortality differences by income, education and race.** No
  mortality model conditions on income, education or race.
- **Projected SSI.** SSI is computed only statically, on incomes
  already recorded.
- **Projected wealth, pensions and other income.** The model
  annuitizes reported wealth and projects none of these.
- **Complete group-output validation against DYNASIM and MINT.**
  [#513][pr513] added MINT's group categories as code; nothing yet
  registers or scores the full set of published group cells,
  lifetime-earnings groups or beneficiary types.
- **Admitting a joint projection past 2030.** No gate scores a
  projected year after 2019, and gate 3 has no cells.
- **Starting states and later processes for newborns and immigrants,
  and emigration.** Newborns get only a link to the mother, the
  immigrant-entry module has never run on real data, the earlier
  immigration design ([#218][pr218]) closed unmerged, and nothing
  models emigration.
- **Moving the engine into Microcosm as an operator.** A mortality and
  ageing prototype runs on synthetic data (`docs/population-graph.md`);
  [#412][i412] lists interface changes but is not a build plan.
- **Insured status.** No code decides whether a worker is insured.
- **Educational progression.** No engine step moves anyone through school;
  completed education is a fixed attribute read from the PSID.
- **Alignment to targets from SSA's actuaries.** The engine has no
  alignment step, and the earlier design ([#217][pr217]) closed
  unmerged.

## Rulings cited on this page

| Ruling | Date | What it decided | Public record |
|---------|----------|-----------------------------------------|--------------------|
| d479 | 27 September 2026 | Allows post hoc reruns, labeled as such; Track A v2 reruns exercises 1 and 3 with the statutory DI computation, and treats DI and spouse dual entitlement as a separate mechanism | `docs/design/urban2010_track_a_v2.md` |
| d513 | 28 September 2026 | Ratifies the Track A v2 specification | `docs/design/urban2010_track_a_v2.md` |
| d515 | 28 September 2026 | Approves revision 3 of the Track B design (forward earnings, the earnings test, claiming) with its recommended defaults; the design is kept outside the repository | `docs/design/track_b_b0_1_audit.md` |
| d622 | 30 September 2026 | Lets a B1 v2 reconstructed-reproduction pass unlock B2, with the weaker label carried | [#505][pr505] |
| d637 | 30 September 2026 | Ratifies amendments 1a–1c (confirmed by d745), 2–5 and 6 to U2's source registries, and held its blockers B1 and B2 until the PSID answered; [#540][pr540] applied them | `docs/design/boomers2004_1946_55_comparison.md` §16b |
| d658 | 30 September 2026 | Registers trust-fund test A-COLA as Registration 18, report-only | [Registration 18][reg18] |
| d660 | 30 September 2026 | Makes OACT and PWBM the primary comparators for the roadmap's trust-fund tests, CBO second and DYNASIM one of several | [#113][i113] |
| d693 | 30 September 2026 | Accepts the B0.1 audit's eight defaults for B2's registration | [#505][pr505] |
| d745 | 12 October 2026 | Confirms that ruling d637 ratified U2's amendments 1a–1c as written, which govern the 12 code-88 blockers | `docs/design/boomers2004_1946_55_comparison.md` §16b; [#540][pr540] |
| d765, d781, d782 | 11 October 2026 | Set B2's design: household half-sample refits, six gated level cells and ten report-only, and design-cluster standard errors | [#505][pr505] |
| d905 | 10 October 2026 | Releases Registration 19's results to #42 with the frame defect disclosed | [#511][pr511] |
| d927 | 10 October 2026 | Ratifies `gate_epuf_fill`'s tolerance and lets it lock as registered | [#515][pr515] |
| d929 | Parked, not ruled | Whether exercises 1, 3 and 4 rerun with learned career fills now that `gate_epuf_fill` has scored | [#516][pr516], [#537][pr537] |
| d947 | Parked, not ruled | Whether to post the registration for starting projections from Microcosm | `docs/plans/microcosm-start-registration-draft.md` |
| d1090 | 10 October 2026 | Settles two of the 1946–55 test's (U2) blockers | [#524][pr524] |
| d1242 | 16 October 2026 | U2 discloses, for blocker B2, the number of code-90 and code-92 persons in 2019–2023 family units that would otherwise supply a U2 observation; the count decides nothing | [#524][pr524], [#546][pr546] |
| d1338 | 12 October 2026 | G adopts SSA's operational reading of the family-payment saving clause in Social Security Act §203(a)(5), codified at 42 U.S.C. 403(a)(5) (POMS RS 00630.400), with the literal reading behind a switch; not yet built | [#530][pr530] (open) |
| d1342 | 11 October 2026 | B2 proceeds with its six cells: the floor build drops cells until power reaches 0.90, keeping at least four, and B2 stops before any candidate result if it cannot. It stopped at its floor build on 15 October | [#505][pr505]; [floor stop][stopb2] |
| d1406 | Open | How to amend gate w1's family-A marital and household targets | [#531][i531] |
| d1408 | 12 October 2026 | Authorizes a labeled diagnostic of #494's effect on registered results, with no rerun or replacement of any registered artifact | [#538][pr538]; [erratum note][errdc] |
| d1414 | Open | Whether to post a Registration 19 addendum for [microcosm#1214][mc1214] | [microcosm#1214][mc1214] |
| d1418 | 12 October 2026 | Keeps Track B's defaults for nine readings where POMS, the CFR and the Act disagree: three computed, six refused and counted, each reopened when a population target needs it | [#528][pr528], [#529][pr529], [#530][pr530] |
| d1597 | 16 October 2026 | Allows the optional structure-only U1 load that checks the staged PSID inputs against U1's pinned input digest before U2's step 4 | `docs/design/boomers2004_1946_55_comparison.md` §13 |
| d1606 | 16 October 2026 | B2 gates four cells, the 90th percentile and the zero-earnings rate by cohort, at its registered tolerance; the medians become report-only and an open item for B0.2 | [#545][pr545]; [B2 registration][regb2] |
| d1649 | 16 October 2026 | Authorizes U2's step-4 structural pass on real PSID records, once, after #546 and the d1597 check, computing structural and reconciliation counts and the named F17 component summaries, without computing poverty | `docs/design/boomers2004_1946_55_comparison.md` §20 |
| d1659 | 18 October 2026 | After B2's failure, design a successor earnings law first, on evidence independent of B2's result, and bring the design to the maintainer before any registration | [B2 result][resb2]; `docs/design/track_b_attempt_ledger.md` |

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
[regb1]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-6110674288
[resb1]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-6113379406
[regb2]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-6252388925
[resb2]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-6252752628
[stopb2]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-6200099988
[resepuf]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-6158562176
[errdc]: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-6206950071
[mc1178]: https://github.com/PolicyEngine/microcosm/issues/1178
[mc1186]: https://github.com/PolicyEngine/microcosm/pull/1186
[mc1212]: https://github.com/PolicyEngine/microcosm/issues/1212
[mc1213]: https://github.com/PolicyEngine/microcosm/issues/1213
[mc1214]: https://github.com/PolicyEngine/microcosm/issues/1214
[mc1215]: https://github.com/PolicyEngine/microcosm/issues/1215
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
[i531]: https://github.com/PolicyEngine/microcosm-dynamics/issues/531
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
[pr525]: https://github.com/PolicyEngine/microcosm-dynamics/pull/525
[pr526]: https://github.com/PolicyEngine/microcosm-dynamics/pull/526
[pr528]: https://github.com/PolicyEngine/microcosm-dynamics/pull/528
[pr529]: https://github.com/PolicyEngine/microcosm-dynamics/pull/529
[pr530]: https://github.com/PolicyEngine/microcosm-dynamics/pull/530
[pr532]: https://github.com/PolicyEngine/microcosm-dynamics/pull/532
[pr537]: https://github.com/PolicyEngine/microcosm-dynamics/pull/537
[pr538]: https://github.com/PolicyEngine/microcosm-dynamics/pull/538
[pr539]: https://github.com/PolicyEngine/microcosm-dynamics/pull/539
[pr540]: https://github.com/PolicyEngine/microcosm-dynamics/pull/540
[pr542]: https://github.com/PolicyEngine/microcosm-dynamics/pull/542
[pr544]: https://github.com/PolicyEngine/microcosm-dynamics/pull/544
[pr545]: https://github.com/PolicyEngine/microcosm-dynamics/pull/545
[pr546]: https://github.com/PolicyEngine/microcosm-dynamics/pull/546
[pr547]: https://github.com/PolicyEngine/microcosm-dynamics/pull/547
[pr548]: https://github.com/PolicyEngine/microcosm-dynamics/pull/548
