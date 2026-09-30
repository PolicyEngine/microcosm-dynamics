# Bridge to PolicyEngine-US

Microcosm's four DYNASIM3 comparisons report pre-tax benefit changes, and one
pre-tax poverty measure with a static SSI response. This bridge shows what a
benefit change becomes after federal and state taxes and means-tested
transfers. It passes Microcosm's Social Security amounts to PolicyEngine-US as
household inputs, runs the tax-benefit model in a separate interpreter, and
splits the change in PolicyEngine-US's `household_net_income` into components
that sum exactly to it.

The first use is exercise 4's headline minimum benefit on three illustrative
households in three states: a minimum benefit set at 73% of the aged poverty
threshold for 22 years of work (Favreault, Mermin and Steuerle 2006, option
2). **These are illustrative households, not survey data.**

Code: `src/populace_dynamics/bridge/policyengine_us.py` (pure Python; no
`policyengine_us` import) and
`scripts/pe_us_minimum_benefit_sample_households.py`. Outputs:
`docs/analysis/pe_us_bridge_20260930/` and
`~/microcosm-launch-evidence/dynasim-parity-20260909/pe-us-bridge-20260930/`.

## What the bridge does and does not do

It does:

- **Build situations.** `BridgePerson` and `BridgeHousehold` hold age, Social
  Security by type, earnings, pension and interest income, liquid assets,
  rent, and tax-unit, SPM-unit, marital-unit, family and household
  membership. They refuse negative or non-finite amounts, a bare string
  where a group of ids belongs, and any unit structure that does not place
  every person in exactly one unit of each kind. `to_situation` writes a
  PolicyEngine-US situation, with the state given as its FIPS code.
- **Check the PolicyEngine-US source.** `inspect_installation` asks the
  interpreter which `policyengine-us` it imports and where it came from
  (package metadata only). `check_published_source` accepts two sources:
  - **an install by name.** There is no `direct_url.json`. Metadata cannot
    tell a package index from a local wheel found with `--find-links`, so
    the runner hashes every installed `policyengine_us/` file against the
    RECORD (`verify_record`). That catches changed, missing and added files;
    policyengine-core loads every parameter YAML and variable module on
    disk. The runner can also require a pinned `package_record_digest`,
    which ties the install to one published wheel. The script pins 2.18.0's.
  - **a git checkout imported in place.** Some branch of `origin` must
    contain its `HEAD`, asked of `origin` now (`git ls-remote`), not of
    local remote-tracking refs that can outlive a deleted branch. It must
    have no modified tracked file and no untracked package file, ignored
    ones included. `origin` must be a GitHub repository.

  Everything else is refused, including an unreachable `origin` and a VCS,
  local-directory or direct-URL archive install. `run_policyengine_us` and
  `trace_policyengine_us` run the checks first.
- **Run PolicyEngine-US out of process.** `run_policyengine_us` sends the
  situations as JSON to the interpreter named by
  `POPULACE_DYNAMICS_PE_US_PYTHON` (default
  `~/.venvs/policyengine-us-2.18.0/bin/python`), the subprocess discipline of
  `scripts/build_aux_benefit_examples.py`.
  - **One simulation per case.** Some 2.18.0 formulas aggregate over a
    whole simulation's population (Medicaid's state-average cost index,
    `medicaid_slcsp_state_average_cost_index.py:14-29`), so households
    batched into one simulation would not be independent.
  - **Shared systems.** Cases with the same parameter overrides share one
    reformed tax-benefit system, passed as `tax_benefit_system`
    (`spm.py:830-834`). An oracle test checks that a case run with others
    equals the case run alone.
  - **Tree and state.** The child reads the component tree of
    `household_net_income` from the model and returns every node's
    household value. It also returns the state PolicyEngine-US derives from
    the FIPS code, and the bridge refuses a mismatch.
- **Decompose.** `decompose` checks every aggregate against the signed sum of
  its parts (within $0.50), and refuses any value that is not finite. It
  checks the root's parts against the definition the bridge was read
  against, and refuses drift. It then rounds each leaf to cents, so the leaf
  changes sum exactly to the net change. PolicyEngine-US's own float32
  `household_net_income` is kept as a check. In every run here its change
  agrees with the definition's sum within a cent.
- **Guard against float32 steps.** `trace_policyengine_us` reruns cases with
  PolicyEngine-US's tracer on (`Simulation(..., trace=True)`) and returns
  every variable the calculation read. Nodes of a branch simulation (2.18.0
  computes federal tax in `itemizing` and `not_itemizing` branches) are
  keyed apart from the main calculation.
  - **What it reports.** `uncaused_changes` walks each changed component's
    calculation. It reports any variable that changed by a cent or more
    although no variable it read changed by more than float noise.
  - **Noise.** Float noise is a cent or four float32 steps at the read's
    size, whichever is larger. Above $131,072 one float32 step is more than
    a cent.
  - **Why a report means an artifact.** A genuine change always has a
    changed input beneath it, here the Social Security amount. A reported
    variable is therefore a step at a bracket or eligibility edge taken on
    float32 noise.
  - **What it cannot see.** The rule is local, so it cannot see a noise
    step in a variable that also read a genuinely changed input.
  - **Small changes.** `small_changes` lists the components that changed by
    a nonzero amount under $2.

It does not:

- compute any Social Security amount. The caller passes them; here they come
  from the Track M rule code and the Microcosm oracle.
- run over the projected population. It runs one household at a time, and
  applies no behavioral, take-up or claiming response to the reform.
- add `policyengine-us` to this repository's dependencies, or edit
  PolicyEngine-US.

## The PolicyEngine-US release

Every result here comes from **policyengine-us 2.18.0 from PyPI**, uploaded
2026-09-30, with policyengine-core 3.32.11. Provenance:

- **Wheel.** `policyengine_us-2.18.0-py3-none-any.whl`, SHA-256
  `28e32bc1339e8ffc1ed676ac1c9ecd468d191685608039643915f63e1357085f` (PyPI's
  digest; a downloaded copy matched it).
- **Installed files.** All 17,551 `policyengine_us/` files in the virtual
  environment match their RECORD hashes. The sorted RECORD lines for those
  files have SHA-256 `9f9f0908…`, the same as the wheel's RECORD. The
  installer adds its own RECORD lines, so the whole-file hashes differ.
- **Refusal.** The script refuses to run on any other version or source.

The earlier draft ran on a local checkout at `e4363903f3` (1.822.5). That
revision is not on GitHub, and `check_published_source` now refuses it.

**What changed in 2.x that matters here.** The bridge ran on 2.18.0 with one
change to the runner: under `gov.hud.abolition`, `household_benefits` now
drops `housing_assistance` (`household_benefits.py:11-17`), where 1.822.5
dropped `spm_unit_capped_housing_subsidy`. Holding the inputs fixed, two
changes in the release move the results:

- **SNAP counts California's SSI supplement as unearned income**
  (`parameters/gov/usda/snap/income/sources/unearned_spm_unit.yaml:13`).
  The 1.822.5 checkout's SNAP income-source lists
  (`parameters/gov/usda/snap/income/sources/`) name no state supplement.
  - **Household B in California.** Its change moves (below).
  - **Household A in California.** Its SNAP level falls from $3,607.57 to
    $3,228, while its change stays zero.
- **SNAP's fiscal-2027 amounts are encoded.** The maximum allotment is $306
  for one person (`max_allotment.yaml:33`) and the standard deduction $217
  (`income/deductions/standard.yaml:17`), both from October 2026.
  - **Levels.** These move SNAP by under $8 a year, for example household
    A in Florida from $3,607.57 to $3,600.
  - **Changes.** The SNAP changes outside California are as they were
    ($207 in Montana, $924 in Florida).

Household C's results also differ from the first draft's because her pension
moved from $30,000 to $31,200 (below).

## What `household_net_income` includes and excludes

All citations are to policyengine-us 2.18.0, under `policyengine_us/`.

- **Definition.** `household_net_income` adds `household_market_income`,
  `household_benefits` and `household_refundable_tax_credits`. It subtracts
  `household_tax_before_refundable_credits` and `household_health_costs`
  (`variables/household/income/household/household_net_income.py:10-18`).
- **Market income.** `gov.household.market_income_sources` includes, among
  others, wages, self-employment, pensions, interest, dividends and
  retirement distributions
  (`parameters/gov/household/market_income_sources.yaml`).
- **Benefits.** `household_benefits` sums the 24 variables of
  `gov.household.household_benefits` (`parameters/gov/household/
  household_benefits.yaml:33-59`, in force from 2024):
  - cash, food and income-replacement benefits: `social_security`, `ssi`,
    `snap`, `wic`, `free_school_meals`, `reduced_price_school_meals`,
    `tanf`, `commodity_supplemental_food_program`,
    `unemployment_compensation`;
  - other transfers and income: `acp`, `ebb`,
    `high_efficiency_electric_home_rebate`,
    `residential_efficiency_electrification_rebate`,
    `child_support_received`, `workers_compensation`,
    `educational_assistance`, `financial_assistance`, `survivor_benefits`,
    `household_head_start_benefits`, `basic_income`, `trump_dividend`,
    `housing_assistance`;
  - the two aggregates `household_state_benefits` (state SSI supplements and
    other state programs; `ca_state_supplement` is in the 2026 list at
    `household_state_benefits.yaml:339`) and `household_health_benefits`.

  The housing assistance drops out when `gov.hud.abolition` is set
  (`household_benefits.py:11-17`). Every run's JSON records the full tree
  (`net_income_tree`).
- **Taxes.** Taxes before refundable credits are:
  - employee payroll tax and self-employment tax;
  - federal income tax before refundable credits;
  - the flat tax;
  - state income tax plus the state use tax
    (`household_state_tax_before_refundable_credits.py:10`);
  - local income and occupational taxes

  (`household_tax_before_refundable_credits.py:11-19`). Refundable credits
  are the federal ones plus each state's
  (`household_refundable_tax_credits.py:10-13`). The tables show taxes
  before refundable credits and refundable credits as separate rows, so a
  refundable credit on a zero liability reads as a credit, not a negative
  tax.
- **Health coverage is excluded by default.** `household_health_benefits`
  returns zero unless `gov.simulation.include_health_benefits_in_net_income`
  is true (`household_health_benefits.py:17-22`). Its list includes Medicaid
  valued at cost, Medicare Savings Programs, CHIP, premium tax credits and
  state premium programs (`parameters/gov/household/
  household_health_benefits.yaml`). The parameter's default is false
  (`parameters/gov/simulation/include_health_benefits_in_net_income.yaml:3`).
  The health-cost subtraction follows the same switch
  (`household_health_costs.py:16-20`). The script therefore reports Medicaid
  and Medicare Savings Program values as memo lines, and repeats every run
  with the switch on as a sensitivity.
- **Social Security is an input.** `social_security_retirement` has no formula
  (`variables/gov/ssa/ss/social_security_retirement.py:4-10`), and
  `social_security` adds its four types (`social_security.py:11-14`).

## How to run

```sh
uv venv --python 3.13 ~/.venvs/policyengine-us-2.18.0
uv pip install --python ~/.venvs/policyengine-us-2.18.0/bin/python \
    policyengine-us==2.18.0
cd <microcosm-dynamics checkout>
POPULACE_DYNAMICS_PE_US_PYTHON=~/.venvs/policyengine-us-2.18.0/bin/python \
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
    scripts/pe_us_minimum_benefit_sample_households.py
```

The run takes about six minutes on a loaded machine, most of it building the
reformed tax-benefit systems and tracing. It writes a JSON file of inputs and
results, a Markdown table, and one chart per household (PNG and SVG) to both
output folders. Microcosm's oracle reads its SSA parameters (the wage index,
bend-point factors, the full retirement age and the CPI-W) from the same
installed release, so both sides use one version.

Tests:

- `tests/bridge/test_policyengine_us_bridge.py` (unit tier, Hypothesis). It
  covers:
  - the situation builder;
  - the decomposition identity and its refusals;
  - the source check, on temporary git repositories and invented
    distributions;
  - RECORD verification;
  - the float32 guard, including the review's use-tax case as traced;
  - the COLA helpers.
- `tests/bridge/test_pe_us_sample_households_script.py` (unit tier). It
  checks the script's own logic on invented inputs, with the runner replaced
  by fakes:
  - parameter updates and overrides;
  - the release pin;
  - the invariants;
  - the traced-versus-untraced check;
  - the Medicaid text;
  - the refusal of local paths.
- `tests/bridge/test_pe_us_bridge_artifact.py` (unit tier). It checks the
  committed JSON and Markdown:
  - the pinned release and a clean source check;
  - the California override;
  - a clean float32 guard;
  - the identity;
  - no local path;
  - the rows and the reform's name.
- `tests/bridge/test_policyengine_us_bridge_oracle.py` (oracle tier). It
  skips unless the interpreter exists and imports `policyengine_us`.

## Provenance

Each output JSON records:

- the Microcosm Dynamics commit, and whether `src/`, `scripts/` or `tests/`
  were dirty;
- the pinned release and the installed one:
  - version, wheel hash and policyengine-core version;
  - the source check and the RECORD check (files verified, mismatches,
    missing files);
  - the installer and Python version;
- every parameter update, with its source;
- every Microcosm parameter source, with its hash:
  - the Census threshold capture;
  - the quarter-of-coverage capture;
  - the committed COLA history;
  - the release's CPI-W file.

Paths are repository-relative or release-relative. The script refuses to
write an absolute or home path.

**Payment year.** The payment year is 2026. The parameters below set the
results shown; the list is not every parameter the model reads. They fall
into four groups.

**Dated 2026 entries in the release:**

- the SSI benefit rate, $994 (`parameters/gov/ssa/ssi/amount/individual.yaml:55`);
- the 2026 federal standard deduction, $16,100
  (`parameters/gov/irs/deductions/standard/amount.yaml:12`), and its
  additional amount for the aged, $2,050
  (`parameters/gov/irs/deductions/standard/aged_or_blind/amount.yaml:10`);
- the 2026 federal brackets; the 10 percent bracket ends at $12,400 for a
  single filer (`parameters/gov/irs/income/bracket.yaml:80`);
- the 2026 poverty guideline, $15,960 (`parameters/gov/hhs/fpg.yaml:17`);
- the 2026 Medicare Part B premium, $202.90
  (`parameters/gov/hhs/medicare/part_b/base_premium.yaml:25`);
- the Commodity Supplemental Food Program amount, $651
  (`parameters/gov/usda/csfp/amount.yaml:11`).

**Earlier entries that stay in force.** These carry into 2026 unchanged:

- the federal senior deduction, $6,000 from 2025
  (`parameters/gov/irs/deductions/senior_deduction/amount.yaml:5`). With the
  standard and aged amounts it takes household C's AGI of $37,067.30 to
  taxable income of $12,917.30;
- the SSI resource limit, $2,000
  (`parameters/gov/ssa/ssi/eligibility/resources/limit/individual.yaml:8`);
- Florida's aged Medicaid limit, 88 percent of the guideline, from 2018
  (`individual.yaml:44-45`);
- the Commodity Supplemental Food Program's income limit, 150 percent of
  the guideline, from 2025 (`gov/usda/csfp/fpg_limit.yaml:4`).

**Uprated by the release.** California's income-tax brackets and standard
deduction end at 2025. The release extends them to 2026 by California's
CPI (`parameters/gov/states/ca/tax/income/rates/single.yaml`,
`deductions/standard/amount.yaml`, `uprating: gov.states.ca.cpi`). They set
household C's $21 of California income tax, which the reform does not
change.

**Not updated for 2026:**

- **SNAP's state utility allowances, October to December 2026.** SNAP
  amounts for those months are fiscal-2027 values. The release encodes
  USDA's fiscal-2027 maximum allotment and standard deduction, but the
  state standard utility allowances have no fiscal-2027 entry. Those months
  use the fiscal-2026 amounts: California $663, Florida $430 and Montana
  $799 a month (`parameters/gov/usda/snap/income/deductions/utility/
  standard/main.yaml:112`, `:179` and `:387`).
- **Medicaid's cost per enrollee (health sensitivity only).** For one
  household, Medicaid at cost is the state's Medicaid spending over its
  enrollment (`medicaid_cost_if_enrolled.py:11-22`). The single-household
  denominator is `medicaid_slcsp_state_denominator.py:28-33`, so the
  person's cost index cancels. The calibration totals end at 2023 spending
  and October 2024 enrollment
  (`parameters/calibration/gov/hhs/medicaid/totals/spending.yaml`,
  `enrollment.yaml`) and are not uprated. The $9,200 (Florida), $9,236
  (California) and $10,799 (Montana) figures are those ratios: averages
  over enrollees of all ages, not 2026 amounts and not specific to an aged
  enrollee.
- **California's payment standard (overridden).** The aged or disabled
  single payment standard has no entry after 2025 (`parameters/gov/states/
  ca/cdss/state_supplement/payment_standard/aged_or_disabled/amount/
  single.yaml:12-13`), so 2026 would use 2025's $1,206.94 a month.
  - **The published amount.** The California Department of Social Services
    publishes $1,233.94 for a single aged person living independently: the
    federal $994 plus the state's $239.94. The source is "SSI Total Monthly
    Payment Amounts 2026" (Rev. 1/26, effective 2026-01-01;
    <https://cdss.ca.gov/Portals/13/SHD/ParaRegIndex/SSI%20Monthly%20Payment%20Amounts%202026.pdf>,
    retrieved 2026-09-30, SHA-256 `75a99370…`).
  - **How the script applies it.** It passes the amount as a 2026 parameter
    override for the California cases (`PARAMETER_UPDATES`). It refuses to
    run if the installed release has a different 2026 value, and drops the
    override once the release has the same one.
  - **Where it shows.** The JSON, the Markdown header and every chart
    footer show the override.
  - **Upstream.** Fixing the parameter in PolicyEngine-US is a separate
    task.

## The minimum benefit as applied here

The rule and its parameters come from this repository's Track M code, called
unchanged. No parameter value is typed into the script.

**The worker.** She is ILLUSTRATIVE. Born in 1958, she had covered earnings of
25 percent of the national average wage index in each of the 22 years
1980-2001. She was first entitled to her retired-worker benefit in 2024, at
66. Her history is invented, so the JSON keeps only the count of covered
years, not the PSID observation fields (observed, imputed and unobserved
years).

**Years of coverage.** `coverage.count_coverage_years` counts 22 years with
four quarters of coverage, with no PSID gap-year imputation.

**PIA.** `rules.history_pia` computes it on the old-age basis. The history
runs through 2023, the year before entitlement. The bend points are those of
2020, the year she attained 62. The result is P = $613.80 (AIME $682).

**The minimum.** It is M = s(Y*) × T / 12 (`rules.monthly_minimum`).

- Exercise 4's headline cell is option 2 (`policy.HEADLINE_CELL`) of
  Favreault, Mermin and Steuerle (2006). That is the standard schedule: 55
  percent at 10 years, rising to 100 percent at 40. At Y* = Y = 22, s = 0.73.
  The 10-year floor does not bind.
- T is the Census weighted-average threshold for one person aged 65 and over.
  It is taken for the threshold year, the year of attaining 62: $12,413 for
  2020, from the pinned capture.
- So M = $755.12: a minimum benefit set at 73% of the aged poverty
  threshold for 22 years of work.

**Floor after the cut.** Option 2 pays max((1 − 0.1281) P, M) =
max($535.17, $755.12) = $755.12, so she is on the minimum.

**Window and policy year.** The minimum reaches only a PIA first calculated
in the window. The window is 2004 or later in the headline row MS0, which
moved every date back three years for the PSID snapshot. It is 2007 or later
in the Report's own dating (MS1), and after the policy year under MS4. Her
PIA is first calculated in 2024, so it is in the window under all three. The
script evaluates the rule under MS0, MS1 and MS4 and refuses to continue
unless the outcomes are identical. For a price-indexed option, the policy
year changes nothing else.

**Baseline.** The baseline is current-law scheduled benefits: P with no cut.
Against option 1 (reduced current law, P × (1 − 0.1245) = $537.38), her gain
would be larger. That PIA is in the JSON as a memo and is not run through
PolicyEngine-US.

**COLAs to 2026.** Track M compares M with the cut PIA only at first
calculation. Carrying both PIAs forward with statutory COLAs is this bridge's
assumption:

- **Which COLAs.** Under 42 USC 415(i)(2)(A)(iii), the COLAs from the year of
  eligibility (2020) onward apply. Payments in 2026 reflect those determined
  through 2025.
- **Rounding.** Each step is floored to a dime (415(i)(2)(A)(ii)).
  `carry_pia_forward` refuses an empty year range, which would return the
  PIA untruncated.
- **Sources.** The 1979-2022 COLAs come from the committed SSA history
  (`estimates.parameters.load_cola_history`). The 2023-2025 COLAs come from
  the release's third-quarter CPI-W averages (`gov/ssa/uprating.yaml:3-8`,
  marked "Actuals"), by 415(i)(1)(D). The derived 2022 COLA equals the
  committed one, 8.7 percent.
- **Result.** P becomes $777.80 and M becomes $957.20.
- **Claim factor.** `rules.claim_factor` gives 0.9556, for 8 months before
  her full retirement age of 66 and 8 months.
- **Monthly benefits.** Rounded down to the dollar, they are $743 and $914:
  $8,916 and $10,968 a year, a difference of $2,052.

## Households and states

Every household is the same worker, aged 68 in 2026, living alone. She rents
for $800 a month and pays heating or cooling costs. She has $1,500 in the
bank, which is under the SSI resource limit of $2,000
(`parameters/gov/ssa/ssi/eligibility/resources/limit/individual.yaml:8`). She
has 88 Medicare quarters of coverage. Housing-voucher take-up is switched off:
PolicyEngine-US defaults it on for every income-eligible renter
(`variables/gov/hud/takes_up_housing_assistance_if_eligible.py:9`). She can
prepare food at home.

| Household | Other income | Purpose |
|---|---|---|
| A | None | SSI-eligible at baseline and under the reform |
| B | $4,800 private pension | SSI-ineligible: the SNAP and state-supplement path |
| C | $31,200 private pension ($2,600 a month) | The federal and state income-tax path |

**Household C's pension sits off every bracket edge.** The first draft gave
her a round $30,000. That put California AGI, which excludes Social
Security, exactly on the $30,000 edge of California's use-tax table
(`variables/gov/states/ca/tax/income/ca_use_tax.py:13-20`;
`parameters/gov/states/ca/tax/income/use_tax/main.yaml:19-28`).
- **What went wrong.** Float32 subtraction put the reform run one float32
  step below the edge: `ca_agi` was 30,000.0 at baseline and
  29,999.998046875 in the reform (35,761.3984 − 5,761.3999). The use tax
  fell from $3 to $2.
- **What it was.** A rounding artifact, not a mechanism. The first draft
  described it as one; it was wrong.
- **Where the pension sits now.** At $31,200 the checks show:
  - **California AGI** is $1,200 above the $30,000 edge.
  - **A finite-difference scan** of pensions from $31,000 to $31,400 (in
    $50 steps, all three states, baseline and reform) finds every component
    linear except one (`review/fix1-pension-edge-scan.json` and `.py` in the
    evidence folder).
  - **The exception** is Montana's baseline elderly homeowner and renter
    credit. Its gross-income multiplier drops from 0.3 to 0.2 at $40,001
    (`parameters/gov/states/mt/tax/income/credits/elderly_homeowner_or_renter/
    multiplier.yaml`). Her gross household income is the pension plus all
    of her Social Security: $40,116 at baseline, $115 above that edge, and
    $42,168 in the reform, $333 below the next edge at $42,501.
  - **The federal bracket.** Her taxable income is $12,917 at baseline and
    $13,831 in the reform, both in the 12 percent bracket that starts at
    $12,400.
  - **The float32 guard** reports nothing.

The states were chosen for mechanism, each verified in the code:

- **California (a state SSI supplement).** The supplement is the payment
  standard less SSI less SSI countable income, floored at zero
  (`variables/gov/states/ca/cdss/state_supplement/ca_state_supplement.py:13-17`).
  SNAP counts it as unearned income (`unearned_spm_unit.yaml:13`).
- **Montana (an income tax that reaches Social Security).** Montana AGI
  starts from federal AGI, which includes taxable Social Security
  (`mt_agi_indiv.py:13-16`). From 2024 the Montana Social Security
  adjustment is off (`mt_agi_indiv.py:20-29`;
  `social_security/applies.yaml:16-18`).
  Montana's refundable elderly homeowner and renter credit is countable rent
  (15 percent of rent) less net household income, capped and multiplied by a
  schedule of gross household income
  (`mt_elderly_homeowner_or_renter_credit.py:19-42`). Gross household income
  counts all Social Security
  (`mt_elderly_homeowner_or_renter_credit_gross_household_income.py:17-23`).
- **Florida (no income tax).** None of the 46 entries in the state
  income-tax list is Florida's
  (`parameters/gov/states/household/state_income_tax_before_refundable_credits.yaml`).
  Its optional state supplement requires a facility living arrangement
  (`fl_oss_eligible.py:58-60,71-76`), which defaults to none
  (`fl_oss_living_arrangement.py:21-37`, `fl_oss_community_care_type.py:18`).
  Its optional aged Medicaid pathway ends at 88 percent of the poverty
  guideline
  (`parameters/gov/hhs/medicaid/eligibility/categories/senior_or_disabled/income/limit/individual.yaml:44-45`).

## Results

Annual 2026 dollars; change from current law to the reform.

| Household | State | Social Security | Net income | Share kept | Net income with health coverage |
|---|---|---:|---:|---:|---:|
| A | CA | +2,052 | 0 | 0% | 0 |
| A | MT | +2,052 | 0 | 0% | 0 |
| A | FL | +2,052 | 0 | 0% | 0 |
| B | CA | +2,052 | +397 | 19% | +397 |
| B | MT | +2,052 | +1,845 | 90% | +1,845 |
| B | FL | +2,052 | +1,128 | 55% | −2,737 |
| C | CA | +2,052 | +1,942 | 95% | +1,942 |
| C | MT | +2,052 | +1,886 | 92% | +1,886 |
| C | FL | +2,052 | +1,942 | 95% | +1,942 |

The last column values Medicaid at the state's Medicaid spending per
enrollee: 2023 spending over October 2024 enrollment, an average over
enrollees of all ages, not uprated to 2026 (see Payment year). It values
coverage at average program cost, which may understate what covering an
aged enrollee costs; it is not a cash loss.

What the components show (full tables in
`docs/analysis/pe_us_bridge_20260930/pe_us_minimum_benefit_sample_households.md`):

**Household A.** Federal SSI falls by exactly the benefit increase, $3,252 to
$1,200, in every state.

- SSI is the benefit rate less countable income
  (`variables/gov/ssa/ssi/uncapped_ssi.py:13-16`). Social Security counts as
  unearned income (`parameters/gov/ssa/ssi/income/sources/unearned.yaml:6`),
  and her $20 general exclusion is already used
  (`_apply_ssi_exclusions.py:28-30`).
- SNAP counts SSI and Social Security alike
  (`parameters/gov/usda/snap/income/sources/unearned.yaml:6,63`), so it does
  not move.
- California's supplement does not move either, because SSI plus countable
  income stays at the federal rate. Her state benefit is $2,879 in both runs
  ($239.94 a month).
- The minimum benefit replaces SSI dollar for dollar. Her net income, and her
  SSI-linked Medicaid, are unchanged.

**Household B.** She is already off SSI.

- **California.** Her SSI countable income ($743 + $400 − $20 = $1,123 a
  month) sits under the $1,233.94 payment standard at baseline, so she gets
  a $110.94 supplement ($1,331 a year). The increase lifts countable income
  past the standard and she loses all of it.
  - **SNAP.** SNAP falls by $324. SNAP counts the supplement as income, so
    the income SNAP sees rises by only $2,052 − $1,331 = $721, and SNAP falls
    by 45 percent of that (see Florida).
  - **Net.** She keeps $397, 19 percent.
  - **The review's +$25.** The review estimated that she keeps $25 (1
    percent), from a run on 1.822.5 with the same override. That release
    did not count the supplement as SNAP income, and there SNAP fell by
    $696 rather than $324: $2,052 − $1,331 − $696 = $25.
- **Florida.** SNAP falls by $924, 45 percent of the increase.
  - **Why 45 percent.** SNAP's contribution is 30 percent of net income
    (`snap_expected_contribution.py:17-32`, with the rate at
    `parameters/gov/usda/snap/expected_contribution.yaml:4`).
  - **The shelter deduction.** For an elderly household it is uncapped and
    shrinks by half of any income gain
    (`snap_excess_shelter_expense_deduction.py:19-38`, with
    `income_share_disregard.yaml:4` at 0.5), so net income rises 1.5 times
    the increase.
- **Florida, health coverage.** Her countable income for Florida's optional
  aged Medicaid pathway rises from $13,476 to $15,528. That passes the limit
  of 88 percent of the poverty guideline, $14,045, so Medicaid ends
  (`is_optional_senior_or_disabled_income_eligible.py:23-32`;
  `individual.yaml:44-45`).
  - **Coverage values.** That is outside default net income. The memo shows
    Medicaid at cost falling from $9,200 to 0.
  - **The Medicare Savings Program.** She is QMB-eligible in every month
    of both runs (`is_qmb_eligible`, a monthly variable, read for all 12
    months). PolicyEngine-US counts the Medicare Savings Program
    only for people not enrolled in full Medicaid (`msp_cost.py:28`), so its
    $5,335 appears once Medicaid ends.
  - **Net.** With health coverage counted, she loses $2,737. Medicaid is
    valued at Florida's spending per enrollee of all ages: the coverage
    she loses at average program cost, not a cash loss.
- **Montana.** SNAP falls by $207.

**Household C.** Taxable Social Security rises from $5,867 to $6,781 under
IRC 86 (`tax_unit_taxable_social_security.py:13-85`).

- **Federal.** Federal income tax rises $110 in every state, 12 percent of
  the $914 of newly taxable benefits.
- **Montana.** Montana income tax rises $43, 4.7 percent of the same $914.
  Her refundable elderly homeowner and renter credit falls from $13 to zero
  (`mt_refundable_credits.py:12-15`). Countable rent is $1,440, 15 percent
  of $9,600. Net household income rises from $1,376 to $1,478, so the
  credit, (countable rent − net household income) × 0.2, reaches zero.
- **California.** California AGI excludes Social Security, so California's
  income tax ($21) and use tax ($3) do not move.
- **Florida.** Only federal tax changes.

## Invariants

The unit tests check these for every input, with Hypothesis:

- **Membership.** The situation builder places every person in exactly one
  tax unit, SPM unit, marital unit, family and household. Amounts, ages and
  the state round-trip. Negative, non-finite and non-numeric amounts are
  refused, and so is a bare string passed as a group. Output is
  deterministic.
- **Decomposition identity.** Leaf changes sum exactly, in integer cents, to
  the net change, and the categories sum to the same total. When the reform
  equals the baseline, every change is zero. The result is deterministic and
  does not depend on the order of parts. An aggregate inconsistent with its
  parts is refused, and so is a drifted root definition. So is any
  non-finite value, including the review's minimal counterexample (root →
  mid → (x, y) with mid = NaN).
- **COLA carry-forward.** It yields whole dimes and is monotone in the PIA.
  Truncation loses less than a dime a step, and carrying composes over split
  year ranges. An empty range is refused. CPI-W-derived COLAs are
  nonnegative tenths of a percent, and the base carries forward past a year
  without an increase.
- **Source check.**
  - An install by name is published.
  - A clone whose commit a branch of `origin` contains now, and whose files
    are clean, is published.
  - These are refused:
    - a local commit not on `origin`;
    - a branch deleted on `origin` whose remote-tracking ref remains;
    - an unreachable `origin`, or one that is not on GitHub;
    - a modified, untracked or git-ignored package file (bytecode aside);
    - a package outside any checkout;
    - a VCS, archive or local-directory install.
- **RECORD.** Verification flags each changed, missing or added file. The
  package digest ignores installer lines (pip's bytecode rows included) and
  line order.
- **Float32 guard.**
  - Always reported: a step over a sub-cent read, including above $131,072,
    where float32 steps exceed a cent.
  - Never reported: a change through a chain of changed variables down to
    an input, a branch taken in one run only, or two identical runs.
- **The script's own checks.** On invented inputs, with the runner
  replaced by fakes:
  - parameter updates are applied, dropped when the release already
    matches, or refused when it differs;
  - overrides go to the right states;
  - a local path is refused;
  - the release pin refuses any other version, file or RECORD;
  - the invariants raise (never `assert`) on a wrong-way change or a guard
    finding;
  - the traced-versus-untraced differential refuses a mismatch;
  - the Medicaid text is refused when its pattern does not hold.

The oracle tests check, against the live model:

- SSI never rises when Social Security does, and falls dollar for dollar
  while positive;
- SNAP does not move for household A and falls for household B;
- California's supplement is constant for A;
- the 2026 payment-standard override reaches the supplement: $110.94 a month
  for household B, against $83.94 under the release's held value;
- taxes do not fall for household C;
- the float32 guard flags `ca_use_tax` at a $30,000 pension and nothing at
  $31,200, and keys the `itemizing` and `not_itemizing` branches' nodes
  apart;
- the interpreter's source is published and its installed files match the
  RECORD, with none added, and a run pinned to another RECORD digest is
  refused;
- the live tree is the definition the bridge was read against;
- a case run with others equals the case run alone;
- all 51 FIPS codes resolve to their state.

The script checks every household-state pair, with and without health
coverage, before writing:

- the identity holds;
- the Social Security component equals the Microcosm benefit change;
- no means-tested benefit, income tax or credit contribution listed in
  `check_invariants` moves the wrong way;
- PolicyEngine-US's own net-income change is within a cent of the definition's
  sum;
- **the float32 guard.** Every changed component is traced: 44 leaves in 18
  comparisons, 65,907 traced variable-periods (branch simulations' nodes
  counted apart).
  - Each traced component, from its traced simulation, equals its
    untraced value within a cent.
  - The per-case runner reproduces the first draft's batched runner exactly
    for every decomposition (all 18). Only Medicaid-at-cost memo values
    move, by one float32 step, for example $9,236.4785 to $9,236.4795. That
    is the cross-case aggregation per-case simulations remove.
  - No variable changed without a changed input.
  - No component changed by a nonzero amount under $2.

## Caveats

- Illustrative households, not survey data. The worker was chosen so the
  minimum binds. A worker above the minimum would lose the 12.81 percent
  uniform cut instead.
- Take-up follows PolicyEngine-US's defaults: full take-up of SSI, SNAP and
  Medicaid (`takes_up_ssi_if_eligible.py:9`, `takes_up_snap_if_eligible.py:9`,
  `takes_up_medicaid_if_eligible.py:9`).
- **The Commodity Supplemental Food Program** (the $651 line) has no take-up
  input. Every eligible person, aged 60 or more with income at or under 150
  percent of the poverty guideline, gets USDA's cost per caseload slot
  (`commodity_supplemental_food_program.py:10-11`;
  `commodity_supplemental_food_program_eligible.py:17-18,42`;
  `gov/usda/csfp/amount.yaml:11`, `fpg_limit.yaml:4`). The program is
  caseload-limited and serves far fewer people than are eligible. It does
  not change here.
- California's payment standard for 2026 and SNAP's utility allowances for
  fiscal 2027 are as described under Provenance.
- The CPI-W-derived COLAs are the release's third-quarter averages. The
  committed history covers 1979-2022 only.
