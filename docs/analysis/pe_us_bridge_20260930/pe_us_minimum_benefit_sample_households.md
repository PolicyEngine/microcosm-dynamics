# The minimum benefit after taxes and transfers: sample households

**Illustrative household, not survey data.** Three households built around one illustrative worker, run through PolicyEngine-US for payment year 2026. Amounts are annual 2026 dollars. Taxes and costs enter as negative contributions, so each column sums to net income (PolicyEngine-US's `household_net_income`, which by default excludes health coverage). Each amount is rounded to the dollar on its own, with half-dollars rounded up in magnitude, so a total can differ by a dollar from the sum of its rounded parts.

- Microcosm Dynamics commit `a915b96e293cc141331c8b02196bbbcbdc8da44d`
- PolicyEngine-US 2.18.0 from PyPI (wheel SHA-256 `28e32bc1339e8ffc1ed676ac1c9ecd468d191685608039643915f63e1357085f`), with policyengine-core 3.32.11. All 17,551 installed `policyengine_us/` files match the wheel's RECORD.
- Reform: a minimum benefit set at 73% of the aged poverty threshold for 22 years of work (Favreault, Mermin and Steuerle 2006, option 2), compared with current-law scheduled benefits
- Social Security: 8,916 a year under current law, 10,968 under the reform
- Parameter update (CA): `gov.states.ca.cdss.state_supplement.payment_standard.aged_or_disabled.amount.single` is set to 1,233.94 dollars a month for 2026, from California Department of Social Services, "SSI Total Monthly Payment Amounts 2026" (Rev. 1/26, effective 2026-01-01; https://cdss.ca.gov/Portals/13/SHD/ParaRegIndex/SSI%20Monthly%20Payment%20Amounts%202026.pdf, retrieved 2026-09-30). PolicyEngine-US 2.18.0 has no 2026 entry and would hold 1,206.94 from 2025-01-01.

## Summary

| Household | State | Social Security | Net income | Share of the benefit increase kept | Net income with health coverage |
|---|---|---:|---:|---:|---:|
| A | CA | +2,052 | 0 | 0% | 0 |
| A | MT | +2,052 | 0 | 0% | 0 |
| A | FL | +2,052 | 0 | 0% | 0 |
| B | CA | +2,052 | +397 | 19% | +397 |
| B | MT | +2,052 | +1,845 | 90% | +1,845 |
| B | FL | +2,052 | +1,128 | 55% | −2,737 |
| C | CA | +2,052 | +1,942 | 95% | +1,942 |
| C | MT | +2,052 | +1,887 | 92% | +1,887 |
| C | FL | +2,052 | +1,942 | 95% | +1,942 |

Medicaid is valued as policyengine-us 2.18.0 values it for one household: the state's 2023 Medicaid spending divided by its October 2024 Medicaid and CHIP enrollment, an average over enrollees of all ages, not uprated to 2026. It is not a same-year average and not specific to aged enrollees, so it could overstate or understate what covering an aged enrollee costs. It values coverage at average program cost; it is not a cash loss. The years do not match: with the release's 2023 enrollment entry, the spending's own year, it would be $7,034 in Florida (not $9,200), $8,751 in California (not $9,236) and $7,223 in Montana (not $10,799).

## Household A

The worker alone: no income besides Social Security, $1,500 in the bank (under the SSI resource limit), renting for $800 a month.

### Household A, California

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 3,252 | 1,200 | −2,052 |
| State benefits (incl. SSI supplements) | 2,879 | 2,879 | 0 |
| SNAP | 3,228 | 3,228 | 0 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 0 | 0 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −1 | −1 | 0 |
| **Net income** | **18,925** | **18,925** | **0** |

Memo (outside default net income): Medicaid at cost 9,236 → 9,236; Medicare Savings Program 0 → 0 (QMB-eligible in every month of both runs; counted only without full Medicaid). Net income with health coverage counted changes by 0.

### Household A, Montana

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 3,252 | 1,200 | −2,052 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 3,600 | 3,600 | 0 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 0 | 0 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 1,150 | 1,150 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **17,569** | **17,569** | **0** |

Memo (outside default net income): Medicaid at cost 10,799 → 10,799; Medicare Savings Program 0 → 0 (QMB-eligible in every month of both runs; counted only without full Medicaid). Net income with health coverage counted changes by 0.

### Household A, Florida

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 3,252 | 1,200 | −2,052 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 3,600 | 3,600 | 0 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 0 | 0 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **16,419** | **16,419** | **0** |

Memo (outside default net income): Medicaid at cost 9,200 → 9,200; Medicare Savings Program 0 → 0 (QMB-eligible in every month of both runs; counted only without full Medicaid). Net income with health coverage counted changes by 0.

## Household B

The same worker with a $4,800-a-year ($400-a-month) private pension, which puts her countable income above the federal SSI benefit rate.

### Household B, California

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 0 | 0 | 0 |
| State benefits (incl. SSI supplements) | 1,331 | 0 | −1,331 |
| SNAP | 3,228 | 2,904 | −324 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −1 | −1 | 0 |
| **Net income** | **18,925** | **19,322** | **+397** |

Memo (outside default net income): Medicaid at cost 9,236 → 9,236; Medicare Savings Program 0 → 0 (QMB-eligible in every month of both runs; counted only without full Medicaid). Net income with health coverage counted changes by +397.

### Household B, Montana

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 0 | 0 | 0 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 3,600 | 3,393 | −207 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 1,150 | 1,150 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **19,117** | **20,962** | **+1,845** |

Memo (outside default net income): Medicaid at cost 0 → 0; Medicare Savings Program 5,335 → 5,335 (QMB-eligible in every month of both runs; counted only without full Medicaid). Net income with health coverage counted changes by +1,845.

### Household B, Florida

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 0 | 0 | 0 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 2,988 | 2,064 | −924 |
| Commodity Supplemental Food Program | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| Federal income tax before refundable credits | 0 | 0 | 0 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **17,355** | **18,483** | **+1,128** |

Memo (outside default net income): Medicaid at cost 9,200 → 0; Medicare Savings Program 0 → 5,335 (QMB-eligible in every month of both runs; counted only without full Medicaid). Net income with health coverage counted changes by −2,737.

## Household C

The same worker with a $31,200-a-year ($2,600-a-month) private pension, enough for part of her Social Security to be taxable.

### Household C, California

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 0 | 0 | 0 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −1,302 | −1,412 | −110 |
| State income tax before refundable credits | −21 | −21 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −3 | −3 | 0 |
| **Net income** | **38,790** | **40,732** | **+1,942** |

Memo (outside default net income): Medicaid at cost 0 → 0; Medicare Savings Program 0 → 0 (not QMB-eligible in any month of either run; counted only without full Medicaid). Net income with health coverage counted changes by +1,942.

### Household C, Montana

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 0 | 0 | 0 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −1,302 | −1,412 | −110 |
| State income tax before refundable credits | −341 | −384 | −43 |
| State refundable tax credits | 13 | 0 | −13 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **38,486** | **40,372** | **+1,887** |

Memo (outside default net income): Medicaid at cost 0 → 0; Medicare Savings Program 0 → 0 (not QMB-eligible in any month of either run; counted only without full Medicaid). Net income with health coverage counted changes by +1,887.

### Household C, Florida

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 0 | 0 | 0 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 0 | 0 | 0 |
| Commodity Supplemental Food Program | 0 | 0 | 0 |
| Market income | 31,200 | 31,200 | 0 |
| Federal income tax before refundable credits | −1,302 | −1,412 | −110 |
| State income tax before refundable credits | 0 | 0 | 0 |
| State refundable tax credits | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **38,814** | **40,756** | **+1,942** |

Memo (outside default net income): Medicaid at cost 0 → 0; Medicare Savings Program 0 → 0 (not QMB-eligible in any month of either run; counted only without full Medicaid). Net income with health coverage counted changes by +1,942.

## Health coverage

- In Florida, the increase raises her countable income for the optional aged Medicaid pathway from $13,476 to $15,528, past the limit of 88% of the poverty guideline ($14,045), so Medicaid ends (PolicyEngine-US 2.18.0, is_optional_senior_or_disabled_income_eligible.py:23-32; parameters/gov/hhs/medicaid/eligibility/categories/senior_or_disabled/income/limit/individual.yaml:44-45). She is QMB-eligible in every month of both runs, and PolicyEngine-US counts the Medicare Savings Program only once full Medicaid ends (msp_cost.py:28), so that benefit appears in the reform.

## Float32 guard

Every changed leaf of the 18 comparisons (nine household-state pairs, with and without health coverage; 44 leaves) was traced through PolicyEngine-US's own calculation (65,907 traced variable-periods). No variable changed by a cent or more (from a cent less one float32 step at its size, never under half a cent) while every variable it read held within float noise (a cent, or four float32 steps at the read's size where that is more), the signature of a float32 step at a bracket edge. No leaf changed by a nonzero amount under $2.

## Notes

- Illustrative households, not survey data: one worker, chosen so the minimum binds, in three living situations.
- The bridge passes Microcosm's Social Security amounts to PolicyEngine-US as inputs; it does not run over the projected population and applies no behavioral response.
- The reform is a minimum benefit set at 73% of the aged poverty threshold for 22 years of work (Favreault, Mermin and Steuerle 2006, option 2): exercise 4's headline option, the standard price-indexed minimum with its printed 12.81 percent uniform cut for new entitlees. The worker is on the minimum, so the cut does not reach her; a worker above the minimum would lose 12.81 percent.
- The baseline is current-law scheduled benefits. Against option 1 (reduced current law, the Report's own benchmark) her gain would be larger; that PIA is in the JSON as a memo, not run through PolicyEngine-US.
- Net income is PolicyEngine-US's household_net_income, which by default excludes health coverage (Medicaid at cost, Medicare Savings Programs); the with-health sensitivity and the memo lines report it. Medicaid is valued as policyengine-us 2.18.0 values it for one household: the state's 2023 Medicaid spending divided by its October 2024 Medicaid and CHIP enrollment, an average over enrollees of all ages, not uprated to 2026. It is not a same-year average and not specific to aged enrollees, so it could overstate or understate what covering an aged enrollee costs. It values coverage at average program cost; it is not a cash loss. The years do not match: with the release's 2023 enrollment entry, the spending's own year, it would be $7,034 in Florida (not $9,200), $8,751 in California (not $9,236) and $7,223 in Montana (not $10,799).
- SNAP for October-December 2026 uses USDA's fiscal-2027 maximum allotment ($306 a month for one person) and standard deduction ($217) as policyengine-us 2.18.0 encodes them (gov/usda/snap/max_allotment.yaml:33, income/deductions/standard.yaml:17). The state standard utility allowances have no fiscal-2027 entry there, so those months use the fiscal-2026 amounts (California $663, Florida $430 and Montana $799 a month; income/deductions/utility/standard/main.yaml:112, 179 and 387).
- In policyengine-us 2.18.0 SNAP counts California's SSI supplement as unearned income (gov/usda/snap/income/sources/unearned_spm_unit.yaml:13), so losing the supplement lowers the income SNAP counts, and SNAP falls by less.
- Take-up is PolicyEngine-US's default: full for SSI, SNAP and Medicaid (takes_up_ssi_if_eligible.py:9, takes_up_snap_if_eligible.py:9, takes_up_medicaid_if_eligible.py:9). The Commodity Supplemental Food Program has no take-up input: every eligible person gets USDA's cost per caseload slot, $651 in 2026 (commodity_supplemental_food_program.py:10-11, gov/usda/csfp/amount.yaml:11), though the program is caseload-limited and serves far fewer people than are eligible. Housing assistance is switched off because vouchers are rationed, and the household can prepare food at home.
- California's 2026 aged or disabled payment standard is set to the published $1,233.94 a month (California Department of Social Services, SSI Total Monthly Payment Amounts 2026, Rev. 1/26); policyengine-us 2.18.0 has no 2026 entry and would hold $1,206.94 from 2025-01-01.
- COLAs for 2023-2025 are derived from policyengine-us 2.18.0's third-quarter CPI-W averages under 42 USC 415(i)(1)(D); the derived 2022 COLA equals the committed SSA history's.
- Household C's pension is $31,200, clear of every bracket and eligibility edge on her path. At a round $30,000, California AGI sat on the $30,000 edge of the use-tax table and float32 noise moved the use tax by $1; the float32 guard now refuses such a run.
