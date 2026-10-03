# Baseline assumptions

A policy result depends on the world the policy lands in. That world
includes how fast prices and wages grow, how long people live, when they
claim benefits, who becomes disabled, how many children are born and who
immigrates. Taken together, these assumptions make up the *baseline*.
This page lists the baseline behind each result Microcosm Dynamics has
published and shows where the code sets each assumption. It also
describes the selectable baselines now being added, and records known
discrepancies and corrections.

Code paths are relative to `src/populace_dynamics/` unless they start
with `scripts/`, `data/`, `docs/` or `paper/`, or name `gates.yaml`;
those are relative to the repository root. Line numbers refer to commit
`75cd3524` on `master` (1 October 2026).

## Terms used on this page

- **Gate.** A pass/fail test registered before its scored run. Before
  that run, `gates.yaml` fixes which statistics the test scores and the
  tolerance on each one. The model passes only if every statistic stays
  within its tolerance. This page uses the word for nothing else.
- **Benchmark.** A comparison between the model's results and another
  model's published results, here DYNASIM3's. A benchmark has no pass
  mark: it reports the gaps and does not grade them. The four blind
  tests against DYNASIM3 are benchmarks.
- **Registration.** The plan for a run, posted as a comment on issue
  [#42](https://github.com/PolicyEngine/microcosm-dynamics/issues/42)
  before the run starts.
- **Trustees Report.** The annual report of Social Security's trustees.
  Its *intermediate* assumptions are the trustees' central path. On this
  page TR2008 means the 2008 Report and TR2026 the 2026 Report. OACT is
  SSA's Office of the Chief Actuary, which prepares the Report's
  projections.
- **COLA.** The cost-of-living adjustment: the yearly percentage
  increase in benefits already being paid. SSA sets it from the consumer
  price index for urban wage earners and clerical workers (CPI-W).
- **AWI.** The national average wage index. SSA uses it to index each
  worker's past earnings and to set the dollar thresholds, called bend
  points, of the benefit formula.
- **Published or derived.** A *published* value is printed in its
  source. A *derived* value is one we compute from published values by a
  rule we state. A derived value is our number, not the source's.

## The baseline behind each published result

Exercises 1 and 3 and Registration 18 share every baseline input, so
they share one column.

| | Exercises 1 and 3, Registration 18 | Exercise 2 | Exercise 4 | Gates m6, 2, 2b, 2c and w1 |
|---|---|---|---|---|
| **What it is** | The projection tests. A closed PSID cohort from the 2011 wave is aged to 2030 in 20 random draws. Exercise 1's alternative R6 uses the 2009 wave instead. Exercise 1 cuts each COLA by one percentage point, and exercise 3 raises the full retirement age to 68. Registration 18 (A-COLA) applies a one-point cut from December 2027. It is registered but had not run by 1 October 2026. | A static calculation on realized PSID incomes at age 67. It covers people born in the odd years 1937 to 1945, so the income years run from 2004 to 2012. | A static calculation on the PSID's 2023 wave: 2022 incomes and benefits, plus earnings histories for 1968–2022. The reform's policy dates move back to 2004. | Fitted components scored three ways: against held-out PSID records (2, 2b, 2c); against the PSID's 2015–2019 records after a fit on data through 2014 (m6); or against the CPS frame (w1). |
| **Assumption vintage** | TR2008, intermediate (`cola_track_a/config.py:264`; `fra68_track/config.py:628`). Registration 18 keeps TR2008 and names the gap from OACT's 2026 Report basis as a delta. | No projection: realized 2004–2012. Named delta: "realized COLAs versus 2002 Trustees assumptions" (`uniform_cut_track_u/runner.py:102`). | No projection: realized 2022. Named deltas: "realized 2022 against DYNASIM's projected 2025" and "realized AWI and CPI against the 2005 Trustees paths" (`min_benefit_track_m/pipeline.py:112`, `:115`). | No Trustees vintage. m6 admits only data dated 2014 or earlier (`engine/refit.py:70`). It binds policyengine-us 1.752.2 parameters, the 2014 Statistical Supplement and the NCHS 2010 life tables (`scripts/registered_m6_inputs.py:14-44`). w1's frame has a 2024 reference period. |
| **COLA path** | SSA's realized COLAs for determination years 1979–2007 (`data/external/ssa_cola_history.json`). TR2008 Table V.C1 (intermediate) for 2008–2017. From 2018, the intermediate ultimate CPI growth of 2.8 percent, a derived value. The path stops at 2030 (`cola_track_a/runner.py:231-258`; `data/tr2008.py:707-735`; `cola_track_a/config.py:258`, `:268`). | None applied. Realized COLAs are already inside the benefits people reported. | SSA's realized COLA history through the COLA determined in 2021. Only alternative MS5 uses it (`min_benefit_track_m/rules.py:133-138`; `scripts/run_track_m_registered.py:352`). | None. No gated cell scores a benefit amount. |
| **AWI** | TR2008 from 1975: Table V.C1 (historical rows 1975–2006, intermediate estimates 2007–2017), then SSA's single-year Table VI.F6 for 2018–2085. Before 1975, SSA's realized series as policyengine-us records it (`cola_track_a/runner.py:193-228`; `data/tr2008.py:750-767`). The registered-run check covers 1975–2030 (`cola_track_a/runner.py:342-344`). | Not used. | SSA's realized series, read from policyengine-us's `nawi.yaml` (pinned at `estimates/parameters.py:56`; loaded at `scripts/run_track_m_registered.py:294`). | m6 only: realized values through 2014, then a log-linear trend fitted to 2005–2014 (`scripts/registered_m6_inputs.py:26-31`; `engine/forward_earnings.py:435-460`). |
| **Mortality** | SSA's 2004 period life table by single year of age and sex. Each year it is multiplied by the ratio of TR2008's intermediate age-sex-adjusted death rate for that year to the 2004 rate. There is one ratio for ages under 65 and one for 65 and older, and each is the same for men and women (`cola_track_a/mortality.py:105-118`, `:126-181`; `data/tr2008.py:949-980`). | Used only to price the wealth annuity. The primary uses NCHS 2000 U.S. life tables by sex, and alternative U9 uses SSA's 2004 period table. Both use a 3 percent real interest rate (`estimates/adjusted_poverty.py:404-415`, `:763-819`). | None. Survival is observed. | m6: PSID death rates by age band and sex, set against NCHS 2010 rates and held constant over time (`engine/refit.py:1059-1119`). The other gates project no mortality. No gate certifies how mortality changes over time. |
| **Claiming** | SSA's distribution of retired-worker awards by age (2014 Statistical Supplement, Table 6.B5.1), with rows through 2008. Every later year reuses the 2008 row, and no claim responds to a reform (`cohorts/psid2010.py:161-166`; `cola_track_a/adapters.py:161-175`; `engine/steps.py:367-376`). | None. Receipt is observed. | None. Entitlement years are read from observed receipt. | m6: the same 2014 Supplement table, rows through 2014 (`engine/refit.py:991-1014`). |
| **Disability insurance** | Award, recovery and death rates fit on 2008 data and held constant in every year. Disabled workers' death rates move with population mortality through a multiplier (`engine/di_entitlement_rates.py:1-56`, `:163-213`). | None. | None projected. Records of benefits that began as disability benefits are observed. | No SSDI entitlement. m6 runs the work-limitation disability module that gate m4 scores. |
| **Fertility** | None. The cohort is closed and no births are drawn (`cola_track_a/adapters.py:19-22`). | None. | None. | Births come from a PSID-fit table by the mother's single year of age (15–49), her number of earlier births (capped at 3) and her birth decade (candidate 16). Gate 2 scores births, and m6 projections draw them (`models/family_transitions/components/fertility.py:26-31`; `engine/marital.py:338-401`). |
| **Earnings** | None after 2010. The benefit formula counts every later year as zero (`cola_track_a/adapters.py:25-27`). | Realized, as reported. | Realized, as reported, 1968–2022. | m6 uses the forward rank-chain law fitted on PSID earnings through 2014 at ages 25–64. |
| **Immigration** | None. No entrants are scheduled (`cola_track_a/runner.py:11-16`). | None. Named delta: immigrant under-coverage (`uniform_cut_track_u/runner.py:103-105`). | None. | None. The entrant schedule is report-only (`engine/entrant_schedule.py:1-6`). |
| **Other inputs** | Statutory parameters from policyengine-us, captured in `data/external/track_a_statutory_parameters.json`. Bend points come from the TR2008 AWI (`cola_track_a/statutory.py:13-25`). | Census weighted-average poverty thresholds for 2004–2012, and SSI parameters captured from policyengine-us (`estimates/adjusted_poverty.py:953-975`, `:1085-1097`). | The Census weighted-average poverty threshold for one person aged 65 and over, captured for 1982, 1986, 1988–1992 and 1994–2022 (`min_benefit_track_m/rules.py:47-53`). | — |

: The baseline behind each published result. Exercise 1 is the one-point COLA cut, exercise 3 the full retirement age of 68, exercise 2 the uniform 13 percent cut and exercise 4 the minimum benefit. {#tbl-baselines}

## How the projection tests set each assumption

Exercise 3's configuration copies exercise 1's baseline settings
(`fra68_track/config.py:627-632`) and passes them to the Track A
configuration (`fra68_track/config.py:707-711`). The two registered
runners build the same inputs
(`scripts/run_track_a_registered.py:302-340`;
`scripts/run_fra68_registered.py:222-259`). The Track A v2 rerun code,
which has not yet run on real data, calls the same constructors
(`track_a_v2/protocol.py:318-385`).

### Assumption vintage

DYNASIM3's run for *Details Matter* used the 2008 Trustees assumptions,
so the projection tests use the same vintage: TR2008's intermediate
alternative (`cola_track_a/config.py:264`). The specification that fixed
this choice is A1 §4 (`docs/design/urban2010_cola_comparison.md:160-167`).
Where TR2008 publishes no series a test needs, the code names a
substitute and records it as a gap (`data/tr2008.py:285-411`).

### Cost-of-living adjustments

The projection tests need a COLA for every year from each benefit's
start to 2030.

- **Before 2008.** SSA's realized COLAs, from
  `data/external/ssa_cola_history.json` (OACT's COLA series page). The
  runtime series covers determination years 1979–2022
  (`estimates/parameters.py:42`, `:406-505`), and the TR2008 path
  replaces every year from 2008 on (`scenario_benefits.py:311-330`). So
  the realized values the tests read run from 1979 to 2007.
- **2008 to 2017.** TR2008 Table V.C1 prints one intermediate COLA per
  year: 2.7 percent for 2008, 2.5 for 2009 and 2.8 for each year
  2010–2017 (`docs/design/urban2010_cola_comparison.md:177-181`;
  `data/tr2008.py:639-654`).
- **2018 onward.** TR2008 prints no COLA after 2017, so the code uses
  the intermediate ultimate CPI growth rate from Table II.C1, 2.8
  percent (`data/tr2008.py:33-41`, `:707`, `:730-735`). This value is
  derived. TR2008's CPI rates are annual averages, while the statute
  measures the COLA from one third quarter to the next
  (`data/external/tr2008/provenance.md`, caveat on V.B1).
- **The path stops at 2030.** The accessor could supply COLAs through
  2085, the last year TR2008 projects (`data/tr2008.py:155`,
  `:725-729`). The tests request the path only through their reference
  year, 2030 (`cola_track_a/config.py:258`;
  `scripts/run_track_a_registered.py:324-329`). Any test that needs a
  COLA after 2030 needs a new path.

TR2008's rates for 2008, 2009 and 2010 differ from the COLAs SSA
actually paid: 5.8, 0 and 0 percent. The A1 specification bars realized
values from any year that enters a reform ratio
(`docs/design/urban2010_cola_comparison.md:247-259`). People already
receiving benefits when the projection opens keep their observed 2010
amounts, which include the realized increases of December 2008 and
December 2009. The specification lists that as a named delta
(`docs/design/urban2010_cola_comparison.md:260-271`).

### Average wage index

From 1975, the AWI is TR2008's (`cola_track_a/runner.py:193-228`):

- **1975–2006:** the values TR2008 Table V.C1 prints as historical
  data.
- **2007–2017:** TR2008's intermediate estimates in V.C1.
- **2018–2085:** the single-year Table VI.F6 that SSA published with
  the Report (`data/tr2008.py:29-32`, `:750-767`). Where both exist,
  its values equal the printed VI.F6 values for 2020, 2025 and 2030
  (`data/external/tr2008/provenance.md`, §2).

The constructor loads the series through 2085
(`cola_track_a/runner.py:197`). A registered run compares it with the
committed TR2008 capture for 1975–2030 (`cola_track_a/runner.py:342-344`).
Before 1975, TR2008 prints no AWI, so those years keep SSA's realized
series as policyengine-us records it (`cola_track_a/runner.py:215-220`).
The bend points follow from the TR2008 AWI
(`cola_track_a/statutory.py:23-25`). The contribution and benefit base
keeps its realized values, because no earnings after 2010 enter
(`cola_track_a/runner.py:205-206`).

### Mortality

TR2008 prints no projected death probabilities by single year of age and
sex (`data/tr2008.py:285-306`). The code therefore builds a substitute
(`cola_track_a/mortality.py:1-33`). For projection year $t$, single age
$x$ and sex $s$:

$$
q_t(x, s) = \min\left(1,\; q_{2004}(x, s) \times
\frac{A_t(g)}{A_{2004}(g)}\right)
$$

- $q_{2004}$ is SSA's period life table for 2004, ages 0–119, posted in
  2008 (`data/tr2008.py:1020-1038`). Ages above 119 use the age-119 row
  (`cola_track_a/mortality.py:141-143`).
- $A_t(g)$ is TR2008's intermediate age-sex-adjusted death rate in
  single-year Table V.A1 for group $g$: under 65, or 65 and over
  (`data/tr2008.py:928-980`).
- One ratio applies to every age in the group and to men and women
  alike (`cola_track_a/mortality.py:117-118`).
- The ratios are loaded for 2009–2030
  (`scripts/run_track_a_registered.py:335-340`). The 2011-wave cohort
  uses them from 2011, and only exercise 1's alternative R6, which opens
  in 2008, uses 2009 and 2010.

Because the base year is 2004, the 65-and-over ratio exceeds 1 from 2005
through 2012 (1.0127 in 2010). V.A1's 2004 rate at 65 and over is below
its estimates for 2005–2007, and this is recorded where the base year is
chosen (`data/tr2008.py:255-270`). So in 2011 and 2012, and in 2009 and
2010 for R6, death probabilities at 65 and over sit slightly above the
2004 table's.
The substitute is a builder default, fixed by the A1 ratification and
the registration, not a ruling (`data/tr2008.py:174-184`).

Disabled workers die at rates from SSA's Actuarial Study 118, multiplied
by the ratio of this year's population probability to the NCHS 2000
probability, so they inherit the TR2008 improvement
(`engine/di_entitlement_rates.py:29-43`). Everyone else's probabilities
are scaled so that each cell's expected deaths stay equal to the
population table's (`engine/di_entitlement_rates.py:44-52`).

### Claiming

The claim-age table is the 2014 Statistical Supplement's Table 6.B5.1,
pinned by SHA-256 (`cohorts/psid2010.py:161-166`;
`cola_track_a/runner.py:167-190`). That table is SSA's distribution of
retired-worker awards by age at entitlement, by sex and entitlement
year, 1998–2013.

- Conversions from disability benefits at full retirement age are
  dropped, because they are not claims. The published 67–69 band is
  split evenly across ages 67, 68 and 69 (`claiming.py:90-99`,
  `:262-303`).
- The projection tests keep the rows through 2008
  (`cola_track_a/config.py:274`; `cola_track_a/adapters.py:161-175`).
  The schedule takes the nearest available year
  (`engine/steps.py:367-376`), so every projection year uses the 2008
  row.
- Disabled workers who convert at full retirement age count as
  claimants without a draw (`cola_track_a/adapters.py:28-34`).
- No claim responds to a reform. Exercise 3 holds each person's
  projected claim age fixed when the full retirement age rises.

### Disability insurance

The disability insurance rates have fit year 2008, which uses 2008 data
published in July 2009 (`engine/di_entitlement_rates.py:172-176`):

- **Awards.** Awards by age at entitlement (DI Annual Statistical
  Report 2008, Table 36), divided by the July 1 resident population
  minus the December stock of disabled workers (Table 20). The
  denominator is the whole non-entitled population, so the model never
  encodes insured status (`engine/di_entitlement_rates.py:8-17`).
- **Recovery.** Actuarial Study 118's age and sex profile (1996–2000
  experience), rescaled to the 2008 recoveries in the Annual
  Statistical Report's Table 50 (`engine/di_entitlement_rates.py:18-28`).
- **Death.** Actuarial Study 118's profile, multiplied by the
  population mortality ratio described above
  (`engine/di_entitlement_rates.py:29-43`).

The fitted arrays are indexed by sex and age only, with no year
(`engine/di_entitlement_rates.py:421-450`). The 2008 award and recovery
rates therefore apply unchanged in every year from 2009 to 2030, and
only death rates move, through the mortality multiplier. TR2008
publishes no disability rates by age, which is why the 2008 fit stands
in (`data/tr2008.py:11-16`, `:319-366`).

### Fertility, earnings and immigration

The projection tests draw no births, no earnings after 2010 and no
immigrants. Everyone aged 50 or older in 2030 was alive in 2010, so the
closed cohort needs no births (`cola_track_a/adapters.py:19-28`). No
entrants are scheduled (`cola_track_a/runner.py:11-16`). TR2008 does
publish a total fertility rate, captured in
`data/external/tr2008/tr2008_single_year.json`, but no accessor reads it
(`data/tr2008.py:940-945`). The only field read from TR2008's ultimate
assumptions is the CPI (`data/tr2008.py:445-447`, `:707`).

### Registration 18

Registration 18 (A-COLA) compares a one-point COLA cut from December
2027 with the 2030 cost effects that OACT and the Penn Wharton Budget
Model publish for that provision. Its "Baseline COLA path" line states
that "the realized series runs through 2007", that TR2008 intermediate
rates apply from 2008, and that the path stops at 2030, "so 2030 is the
only year this test can read". Its population is exercise 1's R0. Its
"Baseline vintage" line names TR2008, set against OACT's 2026 Report
basis, as a delta
([issue #42, comment 5919983573](https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-5919983573)).
When it runs, it reads the same baseline inputs as exercise 1.

## Exercises 2 and 4: realized incomes

Exercises 2 and 4 project nothing. They apply a reform to incomes the
PSID already recorded. DYNASIM3's figures for the same reforms came from
projections on older Trustees assumptions, so part of any gap can come
from the vintage of the population and the economy, not from the rules.
Each exercise names that as a delta.

### Exercise 2: the 13 percent cut

- **Incomes.** The sample member's family income in the year they
  turned 67, income years 2004–2012. Reported Social Security is cut by
  13 percent from 2004 (`estimates/adjusted_poverty.py:404-415`).
  Realized COLAs are inside those reported benefits. The named delta
  says DYNASIM3 projected them from the 2002 Trustees assumptions
  (`uniform_cut_track_u/runner.py:98-102`).
- **Poverty line.** The Census weighted-average threshold of the income
  year, using the 65-and-over column for one- and two-person units
  (`estimates/adjusted_poverty.py:71-75`, `:953-975`).
- **SSI.** A static Supplemental Security Income offset, using SSI
  parameters captured from policyengine-us
  (`estimates/adjusted_poverty.py:1085-1097`).
- **Wealth annuity.** Eighty percent of the family's wealth excluding
  home equity, divided by the price of a level real annuity. The
  annuity pays at the end of each year the annuitant survives, at a 3
  percent real interest rate with no load. A head with a co-resident
  spouse gets a joint annuity that pays half to the survivor; anyone
  else gets a single-life annuity
  (`estimates/adjusted_poverty.py:49-70`, `:404-415`).
  - The primary prices the annuity on the NCHS 2000 U.S. life tables by
    sex. Alternative U9 uses SSA's 2004 period table
    (`estimates/adjusted_poverty.py:295-301`, `:763-819`;
    `uniform_cut_track_u/runner.py:199-213`).
  - Both are period tables. A named delta notes that DYNASIM3's
    mortality follows the 2002 Trustees projections, and that period
    tables overstate the annuity when mortality is falling
    (`uniform_cut_track_u/runner.py:144-148`).

### Exercise 4: the minimum benefit

- **Incomes and careers.** 2022 incomes and benefits from the PSID's
  2023 wave, with earnings histories for 1968–2022. The named deltas
  set "realized 2022 against DYNASIM's projected 2025" and "realized
  AWI and CPI against the 2005 Trustees paths"
  (`min_benefit_track_m/pipeline.py:110-115`).
- **AWI.** SSA's realized series, read from policyengine-us's
  `nawi.yaml` and pinned by SHA-256 (`estimates/parameters.py:56`;
  `scripts/run_track_m_registered.py:294`). The AWI enters the PIA and
  the wage-indexed options (`min_benefit_track_m/rules.py:12-14`). It
  also scales the quarters of coverage before 1978
  (`min_benefit_track_m/coverage.py:229-254`).
  - In the pinned file, the values through 2024 are SSA's published
    series. The later entries are projections, which the file derives
    from CBO's projected taxable maximum.
  - Exercise 4's records reach entitlement year 2022, whose indexing
    year is 2020 under 42 U.S.C. 415(b)(3), so they read only
    published values.
- **COLA.** SSA's realized COLA history through the COLA determined in
  2021, used only by alternative MS5. That alternative takes the PIA
  from the benefit the person receives
  (`min_benefit_track_m/rules.py:133-138`;
  `min_benefit_track_m/careers.py:27-38`).
- **Threshold.** The Census weighted-average threshold for one person
  aged 65 and over, in the worker's threshold year
  (`min_benefit_track_m/rules.py:47-53`;
  `min_benefit_track_m/thresholds.py:71-72`).
- **Mortality.** Exercise 4 uses no life table.

## The gated components

The gates score fitted components. None of them scores a benefit amount,
uses a COLA path or has a Trustees vintage, and none certifies how
mortality changes over time.

- **m6** (`gates.yaml:5324`). The temporal holdout fits the whole engine
  on data dated 2014 or earlier and projects 2015–2019 against the
  PSID's records. Its inputs are fixed to sources dated 2014 or earlier
  (`scripts/registered_m6_inputs.py:14-44`):
  - policyengine-us 1.752.2, with the AWI realized through 2014 and
    then a log-linear trend fitted to 2005–2014;
  - the 2014 Supplement claim table, rows through 2014;
  - PSID death rates by age band and sex, set against the NCHS 2010
    life table, with no change over time (`engine/refit.py:1059-1119`).

  Births come from the candidate-16 table, and earnings from the
  forward rank-chain law.
- **2, 2b and 2c** (`gates.yaml:634`, `:1325`, `:2022`). Family
  transitions, household composition and the joint of marital status
  and earnings, each scored on PSID persons held out of the fit.
  - Gate 2 scores birth rates by five-year maternal age band and
    completed fertility (`gates.yaml:1242-1254`).
  - NCHS birth rates serve only as an anchor for the noise floor
    (`scripts/build_gate2_floors.py:684-712`).
- **w1** (`gates.yaml:3701`). Transport of the PSID-estimated processes
  onto the CPS frame, scored on cross-sectional joint distributions.
  The frame's reference period is 2024.

Gates 1 and m4, which the table does not list, also score fitted
components against PSID records. Gate m4 is also scored against the age
shape of SSA's 2023 disability statistics. A gate's result is its
committed file under `runs/`, so choosing a baseline changes no gate
result.

## Choosing a baseline

The baselines package (`src/populace_dynamics/baselines/`) lets a
projection name the baseline it runs on. `get_baseline(name)` returns
one of three:

- **`tr2008_intermediate`** reproduces today's inputs exactly. It is
  the default.
- **`tr2026_intermediate`** follows the 2026 Trustees Report's
  intermediate assumptions.
- **`cbo2026_long_term`** follows CBO's 2026 long-term projections.

**Every registered result keeps `tr2008_intermediate`, and no
published number changes.** A registered run is a one-shot run whose
inputs the registration fixes in advance. A rerun on another baseline
would be a new run and would need its own registration on issue #42.
The code enforces this: `build_track_a_inputs` refuses a real-data run
under any baseline other than `tr2008_intermediate`
(`baselines/track_a.py`), and `project_track_a` runs the new baselines
only on invented or unregistered cohorts. Each baseline's own
provenance records, not this page, are the authority for every
derivation rule. `scripts/describe_baseline.py --baseline <name>
--years 2026-2035` prints a baseline's input paths, which are inputs
only and no model output.

Both 2026 baselines splice realized values before any projected or
derived one: COLAs through determination year 2025 and the AWI through
2024.

| Assumption | `tr2008_intermediate` (default) | `tr2026_intermediate` | `cbo2026_long_term` |
|---|---|---|---|
| COLA | As in @tbl-baselines. Published through 2017, derived after. | Published: Table V.C1 intermediate, 2025–2035; the 2025 value is an actual amount. Derived: from 2036, the annual change in the CPI-W from single-year Table V.B1. | Derived: CBO publishes no COLA and no CPI-W. Builder default: the CPI-W and the COLA grow at CBO's annual CPI-U growth (ten-year levels through 2036, long-term growth after), not a statutory third-quarter calculation. |
| AWI | As in @tbl-baselines. Published (V.C1 and single-year VI.F6). | Published: single-year Table VI.G1, historical 1970–2024 and intermediate 2025–2100. | Derived: from the actual 2024 AWI, 2025–2026 grow at CBO's real earnings per worker growth times CPI-U growth; from 2027, at the growth of covered earnings per covered worker from CBO's September 2026 Social Security inputs (to 2100). CBO publishes no AWI. |
| Mortality | The 2004 table scaled by two TR2008 ratios. Derived. | Published: OACT's projected probabilities of death by single year of age (0–119) and sex, historical through 2023 and intermediate for 2024–2100. | Published: CBO's mortality rates by single year of age (0–119) and sex, 2021–2099. CBO labels them deaths per 1,000 people without saying which kind. Read as probabilities of death, they reproduce every life expectancy CBO publishes for 2026–2099 within 0.0011 years; read as central death rates, they do not. The baseline therefore treats them as probabilities. |
| Fertility | None. TR2008 publishes a total rate only, and no accessor reads it. | Published: the total fertility rate in single-year Table V.A1 (historical 1940–2025, projected 2026–2100). Derived: rates by single year of age, scaling the NCHS 2024 age shape to each year's total (see the next section). | Published: rates by single year of age, 14–49, for 2021–2099. |
| Other economic series | None beyond the COLA path. | Single-year Table V.B1 (historical 1960–2025, projected 2026–2100) supplies the CPI-W change after 2035. | CBO's February 2026 long-term economics: CPI-U growth and growth of real earnings per worker, 1996–2056. Later years need an extension rule. |
| Claiming | The 2014 Supplement, rows through 2008. | The 2026 Statistical Supplement's Table 6.B5.1 (entitlement years through 2025), with its last row reused for later years. | Same as `tr2026_intermediate`. |
| Disability insurance | 2008 fit, held constant. | 2008 fit, held constant: a named gap. | 2008 fit, held constant: a named gap. |
| Immigration | None (closed cohort). | None in a closed cohort. Single-year Table V.A2 publishes inflows, outflows and net change, for lawful permanent residents and for temporary or unlawfully present immigrants. | None in a closed cohort. CBO publishes gross migration by age, sex, status and flow. |

: What each selectable baseline draws from its sources. "Published" marks a series printed in the source; "derived" marks one we compute from published values. {#tbl-selectable}

### Notes on each assumption

**COLA after 2035 under the 2026 Report.** V.C1 prints COLAs only
through 2035. Later years take the annual change in the CPI-W from
single-year Table V.B1. That change is an annual average, so it only
approximates the third-quarter-to-third-quarter change the statute
uses. TR2008's derived ultimate rate carries the same caveat.

**CBO's prices and wages.** CBO publishes neither the CPI-W nor the
AWI. Its long-term economic projections stop in 2056, while its Social
Security inputs run to 2100 and its demographic files to 2099. A CBO
baseline therefore needs four stated rules: one that turns the CPI-U
into a CPI-W, one that turns covered earnings per covered worker into
an AWI stand-in, and extension rules for the years after 2056 and after
2099. Covered earnings per covered worker is a different series from
the AWI, not a version of it.

**Mortality.** Both new baselines replace TR2008's substitute, a 2004
table scaled by two broad ratios, with probabilities that vary by single
year of age, sex and year. Disabled workers' death rates are a multiple
of the population probability, so they move with whichever mortality
the baseline supplies (`engine/di_entitlement_rates.py:29-43`).

**Claiming.** Under the new baselines, claiming uses Table 6.B5.1 of
SSA's 2026 *Annual Statistical Supplement*, which covers entitlement
years through 2025 (`data/external/ssa_claim_ages_2026supplement.json`).
Nearest-year selection reuses its last row for later years
(`engine/steps.py:367-376`). Claiming still does not respond to a
reform.

**Disability rates stay 2008-fit under every baseline.** Neither source
publishes disability incidence or termination rates by age. The 2026
Trustees materials give age-sex-adjusted summary measures, plus charts
by age group, in the disability assumptions memorandum. None of the CBO
files listed below contains disability rates by age. The model's award,
recovery and death profiles therefore keep the 2008 fit described
above. Only disabled workers' death rates change, through the mortality
multiplier. This is a named gap.

### Sources

The 2026 Trustees Report pages, as of 1 October 2026:

- Table V.C1: <https://www.ssa.gov/oact/TR/2026/V_C_prog.html>
- Single-year Tables V.A1, V.B1 and VI.G1:
  <https://www.ssa.gov/oact/TR/2026/lr5a1.html>,
  <https://www.ssa.gov/oact/TR/2026/lr5b1.html> and
  <https://www.ssa.gov/oact/TR/2026/lr6g1.html>
- OACT's projected probabilities of death:
  <https://www.ssa.gov/OACT/Downloadables/CY/DeathProbsE_M_Alt2_TR2026.csv>
  and its `_F_` counterpart for women, with `_Hist_` files for history
- *2026 Long-Range OASDI Projection Model Documentation*:
  <https://www.ssa.gov/oact/TR/2026/2026_LR_Model_Documentation.pdf>
  (SHA-256 `e3a73c80db785bf38aa334ac7315cc7372906e5dbae627ed2bb7d473cb8073f2`)
- *The Long-Range Disability Assumptions for the 2026 Trustees Report*:
  <https://www.ssa.gov/oact/TR/2026/2026_Long-Range_Disability_Assumptions.pdf>

OACT's `CY` folder always holds the current year's files. Earlier
Reports' files sit under year folders, such as
<https://www.ssa.gov/OACT/Downloadables/2025/TR2025.html>, and the 2026
files should move to the same pattern once the 2027 Report appears.

CBO's files. cbo.gov blocks automated downloads, so the copies we
examined came from Internet Archive captures:

| File | SHA-256 |
|---|---|
| Demographic projections, January 2026, supplementing *The Demographic Outlook: 2026 to 2056*: <https://www.cbo.gov/system/files/2026-01/57059-2026-01-Demographic-Projections.zip> | `083ea91701c1af901cd378211a34c8c8a941c8833c2507564af89551d63392bf` |
| Long-term economic projections, February 2026: <https://www.cbo.gov/system/files/2026-02/57054-2026-02-LTBO-econ.xlsx> | `6f6e66d7e2aaf187e0d13aa90767a39e682a6a5ab2be87b0cc2221b7370e6929` |
| Projections underlying Social Security estimates, September 2026: <https://www.cbo.gov/system/files/2026-09/62556-2026-Additional-Info.xlsx> | `7a7247651f3ae6820c9263a16f11b9cc9cf24cd7dcb9e18bb76e44711924d73b` |

## Fertility by age

No registered result draws a birth, so nothing in this section affects
a published number. Fertility matters for the open-population
projections that the new baselines make possible. The package's opt-in
birth step (`baselines/fertility.py`) draws births to women aged 14–49
at their single-age rates. It is not gated, it is report-only, and it
does not touch the gated fertility law that gate m6's projections use.

### Why rates by age and not one total rate

The number of births in a year equals the sum, over each age, of the
number of women at that age times the birth rate at that age. The
total fertility rate (TFR) adds up one year's birth rates across ages.
It reads as the number of children a woman would have if she lived
through her childbearing years at that year's rates. It does not say at
which ages those births happen.

That matters in two ways:

- **Age structure.** Two populations with the same TFR produce
  different numbers of births in a year if their women are spread
  differently across ages. A large cohort of women in their late
  twenties produces more births than the same number in their early
  forties.
- **Timing.** A shift toward later childbearing changes births year by
  year even while the TFR holds steady.

A projection that knows only the TFR still needs an age pattern to
place births. The model's own birth step already works by the mother's
single year of age (`models/family_transitions/components/fertility.py:26-31`),
so any outside baseline has to supply rates by single year of age to
plug into the same structure.

### What each source publishes

- **CBO** publishes rates by single year of age, 14 to 49, for every
  year 2021–2099. They are in births per 1,000 women, for all women and
  separately for native-born and foreign-born women (file
  `CSV Files/fertilityRates_byYearAgePlace.csv` in the January 2026
  demographic projections). These are published rates and need no
  derivation.
- **The 2026 Trustees Report** publishes only the total fertility rate,
  in single-year Table V.A1. OACT's downloadable files for the 2026
  Report hold life tables, death probabilities and population, but no
  fertility file.
  - OACT does project birth rates by single year of age 14 to 49
    internally. Its 2026 model documentation (§1.1, Demography pages
    2–4) describes the method. OACT projects each age's rate as a ratio
    to the age-30 rate, carrying forward the average year-to-year
    change in those ratios, and moves each age to its ultimate rate on
    its own schedule (age 30 reaches its ultimate in 2037). The age-30
    rate is chosen to hit the ultimate cohort TFR, which the 2026
    Report sets at 1.75 from the cohort born in 2012.
  - Those single-year rates are not published.
- **TR2008** likewise publishes a total rate only
  (`data/tr2008.py:445-447`, `:940-945`).

### A Trustees-consistent age schedule

The `tr2026_intermediate` baseline derives rates by age. It scales a
documented age shape to the V.A1 total fertility rate each year. The
default shape is NCHS's final 2024 rates in five-year bands
(`data/external/nchs_asfr_2024.json`), spread to single ages by a
mean-preserving interpolation that keeps each band's total
(`baselines/interpolation.py`, `baselines/asfr.py`). CBO's 2026
single-age pattern is the registered alternative shape. With $s(a)$ the
shape's share at single age $a$:

$$
f_t(a) = \mathrm{TFR}_t \times s(a), \qquad \sum_{a=14}^{49} s(a) = 1,
$$

so that $\sum_a f_t(a) = \mathrm{TFR}_t$ in every year: the schedule
reproduces the published total exactly. Rates here are births per
woman. CBO's rates, in births per 1,000 women, are divided by 1,000 to
compare.

The schedule is derived, not published, in two respects:

- **The shape is an assumption.** The default is the NCHS 2024 shape;
  the choice is a builder default awaiting ratification, and every
  derived rate carries its shape's tag.
- **The shape does not change over time.** OACT's internal method moves
  each age toward its own ultimate rate on its own schedule. The derived
  schedule therefore matches the Trustees' totals but not their timing
  of births across ages.

CBO's published schedule needs neither step.

## Known discrepancies

1. **The A1 specification's AWI wording.** A1 §15 says the AWI for
   2018–2029 is a "geometric interpolation between published points"
   (`docs/design/urban2010_cola_comparison.md:638`). The code instead
   reads the single-year Table VI.F6 that SSA published with TR2008
   (`data/tr2008.py:29-32`, `:761-767`). Where both exist, that table's
   values equal the printed VI.F6 points for 2020, 2025 and 2030
   (`data/external/tr2008/provenance.md`, §2). Between those points the
   two methods can differ. The A1 specification is frozen, so this page
   records the mismatch and the specification stays as ratified.
2. **Which edition of the claiming table.** The paper and A1 §15 point
   to `claiming.py`, whose default table is the 2023 Supplement
   (`claiming.py:81-83`). The projection tests pass the 2014 Supplement
   instead (`cohorts/psid2010.py:161-166`;
   `cola_track_a/runner.py:167-190`). The two editions' 2008 rows agree
   in every cell but one: men claiming at 67–69 are 1.3 percent of
   awards in the 2014 edition and 1.4 percent in the 2023 edition
   (`data/external/ssa_claim_ages_2014supplement.json`;
   `data/external/ssa_claim_ages_2023supplement.json`).
3. **"2008" disability rates.** The paper calls the disability rates
   "2008-vintage" and says they were "observed through 2008"
   (`paper/paper.qmd:139`, `:192`). The fit uses 2008 data, published in
   July 2009 (`engine/di_entitlement_rates.py:172-176`). Both phrases
   describe the data year correctly. This page states the publication
   date so that no one reads "2008-vintage" as "published by 2008".
4. **The AWI's span.** The code loads TR2008's AWI through 2085
   (`cola_track_a/runner.py:197`), while the paper says the tests take
   it "for 1975–2030" (`paper/paper.qmd:192`). The registered-run check
   covers exactly 1975–2030 (`cola_track_a/runner.py:342-344`), and the
   tests compute nothing after 2030. The paper's statement is right and
   stays as written.
5. **Planning documents.** Two planning documents describe mechanisms
   no registered result uses:
   - `docs/methodology.md` describes fertility predictors aligned to
     national vital statistics (lines 392–396), differential mortality
     by earnings and education (lines 430–434), alignment to Trustees
     demographic rates (line 480) and new cohorts entering from the CPS
     at age 18 (lines 488–497);
   - `docs/operationalizing-mortality-and-projection-drift.md` says the
     first phase should not reduce mortality to age and sex alone (lines
     212–222), which is exactly what the projection tests do.

   Both describe plans, not the code.

## Corrections made with this page

- **Projected death probabilities.** The paper said that "The Trustees
  Report publishes no projected death probabilities by single year of
  age and sex" (`paper/paper.qmd:141`). That holds for the 2008 Report
  as printed, but not in general. OACT publishes projected death
  probabilities by single year of age and sex with each Report, as
  downloadable files. Those files start with the 2014 Report. For 2026
  the men's intermediate file is
  <https://www.ssa.gov/OACT/Downloadables/CY/DeathProbsE_M_Alt2_TR2026.csv>.
  The sentence now limits the claim to the 2008 Report and says where
  the later files are. No number in the paper changed.

These are corrections to prose, not to any committed artifact, so
nothing is filed under `docs/errata/`.
