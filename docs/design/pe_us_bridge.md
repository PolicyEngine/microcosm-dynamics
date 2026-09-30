# Bridge to PolicyEngine-US

Microcosm's four DYNASIM3 comparisons report pre-tax benefit changes, and one
pre-tax poverty measure with a static SSI response. This bridge shows what a
benefit change becomes after federal and state taxes and means-tested
transfers. It passes Microcosm's Social Security amounts to PolicyEngine-US as
household inputs, runs the tax-benefit model in a separate interpreter, and
splits the change in PolicyEngine-US's `household_net_income` into components
that sum exactly to it.

The first use is exercise 4's headline minimum benefit on three illustrative
households in three states. **These are illustrative households, not survey
data.**

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
  membership. They refuse negative or non-finite amounts and any unit
  structure that does not place every person in exactly one unit of each kind.
  `to_situation` writes a PolicyEngine-US situation, with the state given as
  its FIPS code.
- **Run PolicyEngine-US out of process.** `run_policyengine_us` sends the
  situations as JSON to the interpreter named by
  `POPULACE_DYNAMICS_PE_US_PYTHON` (default
  `~/PolicyEngine/policyengine-us/.venv/bin/python`), the subprocess discipline
  of `scripts/build_aux_benefit_examples.py`. Cases that share parameter
  overrides run as one simulation, with names prefixed per case. An oracle test
  checks that a batched case equals the same case run alone. The child reads
  the component tree of `household_net_income` from the model and returns
  every node's household value. It also returns the state PolicyEngine-US
  derives from the FIPS code, and the bridge refuses a mismatch.
- **Decompose.** `decompose` checks every aggregate against the signed sum of
  its parts (within $0.50). It checks the root's parts against the definition
  the bridge was read against, and refuses drift. It then rounds each leaf to
  cents, so the leaf changes sum exactly to the net change.
  PolicyEngine-US's own float32 `household_net_income` is kept as a check. In
  every run here it agrees with the definition's sum to the cent.

It does not:

- compute any Social Security amount. The caller passes them; here they come
  from the Track M rule code and the Microcosm oracle.
- run over the projected population. It runs one household at a time, and
  applies no behavioral, take-up or claiming response to the reform.
- add `policyengine-us` to this repository's dependencies, or edit
  PolicyEngine-US.

## What `household_net_income` includes and excludes

All citations are to policyengine-us at `e4363903f3` (version 1.822.5), under
`policyengine_us/`.

- **Definition.** `household_net_income` adds `household_market_income`,
  `household_benefits` and `household_refundable_tax_credits`. It subtracts
  `household_tax_before_refundable_credits` and `household_health_costs`
  (`variables/household/income/household/household_net_income.py:10-18`).
- **Market income.** `gov.household.market_income_sources` includes wages,
  self-employment, pensions, interest, dividends and retirement distributions
  (`parameters/gov/household/market_income_sources.yaml`).
- **Benefits.** `household_benefits` lists `social_security`, `ssi`, `snap`,
  `wic`, school meals, `tanf`, unemployment compensation,
  `commodity_supplemental_food_program` and `spm_unit_capped_housing_subsidy`.
  It also lists `household_state_benefits` (state SSI supplements and other
  state programs) and `household_health_benefits`
  (`parameters/gov/household/household_benefits.yaml:32-57`). The housing
  subsidy drops out when `gov.hud.abolition` is set
  (`household_benefits.py:11-19`).
- **Taxes.** Taxes before refundable credits are:
  - employee payroll tax and self-employment tax;
  - federal income tax before refundable credits;
  - the flat tax;
  - state income tax plus the state use tax
    (`household_state_tax_before_refundable_credits.py:10`);
  - local income and occupational taxes

  (`household_tax_before_refundable_credits.py:11-19`). Refundable credits
  are the federal ones plus each state's
  (`household_refundable_tax_credits.py:10-13`).
- **Health coverage is excluded by default.** `household_health_benefits`
  (Medicaid valued at cost, Medicare Savings Programs, CHIP, premium tax
  credits and state premium help;
  `parameters/gov/household/household_health_benefits.yaml`) returns zero
  unless `gov.simulation.include_health_benefits_in_net_income` is true
  (`household_health_benefits.py:17-22`). The parameter's default is false
  (`parameters/gov/simulation/include_health_benefits_in_net_income.yaml`).
  The health-cost subtraction follows the same switch
  (`household_health_costs.py:16-20`). The script therefore reports Medicaid
  and Medicare Savings Program values as memo lines, and repeats every run
  with the switch on as a sensitivity.
- **Social Security is an input.** `social_security_retirement` has no formula
  (`variables/gov/ssa/ss/social_security_retirement.py:4-10`), and
  `social_security` adds its four types (`social_security.py:11-14`).

## How to run

```sh
cd <microcosm-dynamics checkout>
POPULACE_DYNAMICS_PE_US_PYTHON=~/PolicyEngine/policyengine-us/.venv/bin/python \
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
    scripts/pe_us_minimum_benefit_sample_households.py
```

The run takes about 30 seconds. It writes a JSON file of inputs and results, a
Markdown table, and one chart per household (PNG and SVG) to both output
folders. `POPULACE_DYNAMICS_PE_US_DIR` names the policyengine-us checkout
whose parameters Microcosm's oracle reads (default
`~/PolicyEngine/policyengine-us`).

Tests:

- `tests/bridge/test_policyengine_us_bridge.py` (unit tier, Hypothesis). It
  covers the situation builder, the decomposition identity and the COLA
  helpers.
- `tests/bridge/test_policyengine_us_bridge_oracle.py` (oracle tier). It
  skips unless the interpreter exists and imports `policyengine_us`.

## Provenance

Each output JSON records:

- the Microcosm Dynamics commit, and whether `src/`, `scripts/` or `tests/`
  were dirty;
- the policyengine-us checkout, its revision, and the `policyengine-us` and
  `policyengine-core` versions;
- the interpreter path and the payment year;
- every Microcosm parameter source, with its hash:
  - the Census threshold capture;
  - the quarter-of-coverage capture;
  - the committed COLA history;
  - the policyengine-us CPI-W file.

**Payment year.** The payment year is 2026. For the parameters on these
households' paths, the checkout has dated 2026 entries or holds earlier values:

- the SSI benefit rate, $994 (`parameters/gov/ssa/ssi/amount/individual.yaml:55`);
- the 2026 federal standard deduction, $16,100
  (`parameters/gov/irs/deductions/standard/amount.yaml:12`), and its
  additional amount for the aged, $2,050
  (`parameters/gov/irs/deductions/standard/aged_or_blind/amount.yaml:10`);
- the 2026 federal brackets (`parameters/gov/irs/income/bracket.yaml`, for
  example line 80);
- the 2026 poverty guideline, $15,960 (`parameters/gov/hhs/fpg.yaml:17`);
- the 2026 Medicare Part B premium.

There are two exceptions:

- **SNAP, October to December 2026.** SNAP amounts for those months are
  fiscal-2027 values. PolicyEngine-US projects them by its CPI-U uprating
  index (`parameters/gov/usda/snap/uprating.yaml`; the uprating metadata is
  at `max_allotment.yaml:942`). They are not USDA's published amounts.
- **California's payment standard.** The aged or disabled single payment
  standard has no entry after 2025 (`parameters/gov/states/ca/cdss/
  state_supplement/payment_standard/aged_or_disabled/amount/single.yaml:13`),
  so 2026 uses $1,206.94 a month.

## The minimum benefit as applied here

The rule and its parameters come from this repository's Track M code, called
unchanged. No parameter value is typed into the script.

**The worker.** She is ILLUSTRATIVE. Born in 1958, she had covered earnings of
25 percent of the national average wage index in each of the 22 years
1980-2001. She was first entitled to her retired-worker benefit in 2024, at
66.

**Years of coverage.** `coverage.count_coverage_years` counts 22 years with
four quarters of coverage, with no PSID gap-year imputation.

**PIA.** `rules.history_pia` computes it on the old-age basis. The history
runs through 2023, the year before entitlement. The bend points are those of
2020, the year she attained 62. The result is P = $613.80 (AIME $682).

**The minimum.** It is M = s(Y*) × T / 12 (`rules.monthly_minimum`).

- Exercise 4's headline cell is option 2 (`policy.HEADLINE_CELL`). That is
  the standard schedule: 55 percent at 10 years, rising to 100 percent at 40.
  At Y* = Y = 22, s = 0.73. The 10-year floor does not bind.
- T is the Census weighted-average threshold for one person aged 65 and over.
  It is taken for the threshold year, the year of attaining 62: $12,413 for
  2020, from the pinned capture.
- So M = $755.12.

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
- **Sources.** The 1979-2022 COLAs come from the committed SSA history
  (`estimates.parameters.load_cola_history`). The 2023-2025 COLAs come from
  the checkout's third-quarter CPI-W averages (`gov/ssa/uprating.yaml`), by
  415(i)(1)(D). The derived 2022 COLA equals the committed one, 8.7 percent.
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
| C | $30,000 private pension | The federal and state income-tax path |

The states were chosen for mechanism, each verified in the code:

- **California (a state SSI supplement).** The supplement is the payment
  standard less SSI less SSI countable income, floored at zero
  (`variables/gov/states/ca/cdss/state_supplement/ca_state_supplement.py:13-17`).
- **Montana (an income tax that reaches Social Security).** From 2024,
  Montana AGI starts from federal AGI, which includes taxable Social
  Security. The old Montana Social Security adjustment is off
  (`mt_agi_indiv.py:13-29`; `social_security/applies.yaml:16-18`). Montana's
  refundable elderly homeowner and renter credit counts all Social Security
  in gross household income
  (`mt_elderly_homeowner_or_renter_credit_gross_household_income.py:17-23`).
- **Florida (no income tax).** No Florida variable is in the state
  income-tax list
  (`parameters/gov/states/household/state_income_tax_before_refundable_credits.yaml`).
  Its optional state supplement requires a facility living arrangement
  (`fl_oss_eligible.py:58-76`), which defaults to none
  (`fl_oss_living_arrangement.py:21-37`, `fl_oss_community_care_type.py:18`). Its optional aged Medicaid pathway ends at 88
  percent of the poverty guideline
  (`parameters/gov/hhs/medicaid/eligibility/categories/senior_or_disabled/income/limit/individual.yaml:44-45`).

## Results

Annual 2026 dollars; change from current law to option 2.

| Household | State | Social Security | Net income | Share kept | Net income with health coverage |
|---|---|---:|---:|---:|---:|
| A | CA | +2,052 | 0 | 0% | 0 |
| A | MT | +2,052 | 0 | 0% | 0 |
| A | FL | +2,052 | 0 | 0% | 0 |
| B | CA | +2,052 | +349 | 17% | +349 |
| B | MT | +2,052 | +1,845 | 90% | +1,845 |
| B | FL | +2,052 | +1,128 | 55% | −2,737 |
| C | CA | +2,052 | +1,962 | 96% | +1,962 |
| C | MT | +2,052 | +1,885 | 92% | +1,885 |
| C | FL | +2,052 | +1,961 | 96% | +1,961 |

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
  (`parameters/gov/usda/snap/income/sources/unearned.yaml:6,14`), so it does
  not move.
- California's supplement does not move either, because SSI plus countable
  income stays at the federal rate.
- The minimum benefit replaces SSI dollar for dollar. Her net income, and her
  SSI-linked Medicaid, are unchanged.

**Household B.** She is already off SSI.

- **California.** She loses her state supplement ($1,007) because countable
  income passes the payment standard. CalFresh falls by $696. She keeps 17
  percent.
- **Florida.** SNAP falls by $924, 45 percent of the increase. SNAP subtracts
  30 percent of net income, and for an elderly household the shelter
  deduction is uncapped and shrinks by half of any income gain
  (`snap_excess_shelter_expense_deduction.py:19-38`, with
  `income_share_disregard` 0.5). So net income rises 1.5 times the increase.
- **Florida, health coverage.** The increase also ends her eligibility for
  Florida's optional aged Medicaid pathway (88 percent of the poverty
  guideline). That is outside default net income;
  the memo shows Medicaid at cost falling from $9,200 to 0 while the Medicare
  Savings Program (QMB) picks up $5,335. With health coverage counted, she
  loses $2,737.
- **Montana.** SNAP falls by $207.

**Household C.** Taxable Social Security rises from $4,847 to $5,761 under
IRC 86 (`tax_unit_taxable_social_security.py:13-80`). Federal income tax
rises $91 in every state. Montana adds $76: $43 more tax on the higher AGI,
and a $33 smaller refundable credit. The credit is the elderly homeowner and
renter credit (`mt_refundable_credits.py:12-15`). California's estimated use tax, a schedule
of California AGI (`variables/gov/states/ca/tax/income/use_tax/ca_use_tax.py:13-20`),
moves by $1.

## Invariants

The unit tests check these for every input, with Hypothesis:

- **Membership.** The situation builder places every person in exactly one
  tax unit, SPM unit, marital unit, family and household. Amounts, ages and
  the state round-trip. Negative, non-finite and non-numeric amounts are
  refused. Output is deterministic.
- **Decomposition identity.** Leaf changes sum exactly, in integer cents, to
  the net change, and the categories sum to the same total. When the reform
  equals the baseline, every change is zero. The result is deterministic and
  does not depend on the order of parts. An aggregate inconsistent with its
  parts is refused, and so is a drifted root definition.
- **COLA carry-forward.** It yields whole dimes and is monotone in the PIA.
  Truncation loses less than a dime a step, and carrying composes over split
  year ranges. CPI-W-derived COLAs are nonnegative tenths of a percent, and
  the base carries forward past a year without an increase.

The oracle tests check, against the live model:

- SSI never rises when Social Security does, and falls dollar for dollar
  while positive;
- SNAP does not move for household A and falls for household B;
- California's supplement is constant for A;
- taxes do not fall for household C;
- the live tree is the definition the bridge was read against;
- batched runs equal single runs, and all 51 FIPS codes resolve to their
  state.

The script checks every household-state pair before writing:

- the identity holds;
- the Social Security component equals the Microcosm benefit change;
- no means-tested benefit or tax contribution moves the wrong way;
- PolicyEngine-US's own net-income change is within a cent of the definition's
  sum.

## Caveats

- Illustrative households, not survey data. The worker was chosen so the
  minimum binds. A worker above the minimum would lose the 12.81 percent
  uniform cut instead.
- Take-up follows PolicyEngine-US's defaults: full take-up of SSI, SNAP and
  Medicaid (`takes_up_ssi_if_eligible.py:9`, `takes_up_snap_if_eligible.py:9`,
  `takes_up_medicaid_if_eligible.py:9`).
- California's payment standard for 2026 and SNAP's fiscal-2027 amounts are
  as described under Provenance.
- The CPI-W-derived COLAs are PolicyEngine-US's third-quarter averages. The
  committed history covers 1979-2022 only.
