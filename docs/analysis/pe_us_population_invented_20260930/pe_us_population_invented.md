# INVENTED DATA - NOT A COMPARISON, NOT THE US

PolicyEngine-US over an invented population: exercise 4's headline minimum benefit

**INVENTED DATA - NOT A COMPARISON, NOT THE US.** Exercise 4's headline option: option 2, standard price-indexed minimum benefit (Favreault, Mermin and Steuerle 2006), with its 12.81% uniform cut, against current-law benefits (the PIA with no cut), under Track M row MS0. Payment year 2026; annual dollars, weighted by the invented household weights.

Code: `scripts/pe_us_population_invented.py`, `src/populace_dynamics/bridge/population.py`. Design: `docs/design/pe_us_population_run.md`.

Phase 0: **permitted** — option A: invented data only, per d479.

Mechanism references below use repository-relative paths; `policyengine_us/` and `policyengine_core/` paths refer to the pinned interpreter's installed source.

| Mechanism | Source (file:line) |
|---|---|
| invented-only guard | `src/populace_dynamics/bridge/invented_population.py:296` |
| cohort and careers | `src/populace_dynamics/bridge/invented_population.py:271` |
| benefit carry and auxiliary mapping | `src/populace_dynamics/bridge/invented_population.py:384` |
| invented distributions and income conventions | `src/populace_dynamics/bridge/invented_population.py:140` |
| family-to-household mapper | `src/populace_dynamics/bridge/invented_population.py:609` |
| release pin and California override | `scripts/pe_us_minimum_benefit_sample_households.py:407` |
| dataset layout | `src/populace_dynamics/bridge/population.py:616; policyengine_core/simulations/simulation.py:405` |
| one simulation per scenario | `src/populace_dynamics/bridge/population.py:980` |
| household Medicaid valuation | `src/populace_dynamics/bridge/population.py:919` |
| income deciles | `policyengine_us/variables/household/income/household/household_income_decile.py:12` |
| exact weighted decomposition | `src/populace_dynamics/bridge/population_summary.py:310` |
| take-back by government level | `src/populace_dynamics/bridge/population_summary.py:122` |
| health federal/state cost split | `src/populace_dynamics/bridge/population_summary.py:365` |
| uniform cut and minimum | `src/populace_dynamics/min_benefit_track_m/rules.py:358` |

Dollar tables are rounded for display. JSON's `*_exact` fields preserve rational dollar totals for the exact identities; independently rounded entries can differ by cents when added (`population_summary.py:61-73,264-302`).

## 300 invented family units (INVENTED DATA - NOT A COMPARISON, NOT THE US)

300 households, 427 people, 51 states; weighted 1,504,372 households and 2,154,052 people (invented weights).

Track M (row MS0): 253 people have an own or linked worker record in the policy window; 8 receive the minimum under option 2; Social Security rises for 2 people and falls for 237. 14 unlinked auxiliaries and 16 people whose records hold no observed covered earnings keep their 2022 amount, carried by the COLAs, in both scenarios.

| Total | Change |
|---|---:|
| Social Security | −4,305,018,629 |
| Net income | −4,233,447,704 |
| Net income, with health coverage | −4,175,757,172 |
| Share of the Social Security change taken back | 1.7% † |

### By level of government

| Level | Baseline | Reform | Change | Share taken back |
|---|---:|---:|---:|---:|
| Federal | 53,588,394,138 | 49,352,822,408 | −4,235,571,730 | 1.6% |
| State | 26,764,882 | 28,888,908 | +2,124,026 | 0.0% |
| Local | 0 | 0 | 0 | 0.0% |
| Market income | 13,391,644,057 | 13,391,644,057 | 0 | 0.0% |

Federal includes Social Security; its share taken back excludes it. Shares sum exactly to the total share.

### By component

| Component | Level | Baseline | Reform | Change |
|---|---|---:|---:|---:|
| `employment_income` | market_income | 4,182,487,342 | 4,182,487,342 | 0 |
| `interest_income` | market_income | 700,359,170 | 700,359,170 | 0 |
| `pension_income` | market_income | 8,508,797,546 | 8,508,797,546 | 0 |
| `ak_permanent_fund_dividend` | state | 57,104,800 | 57,104,800 | 0 |
| `social_security` | federal | 53,726,648,993 | 49,421,630,364 | −4,305,018,629 |
| `ssi` | federal | 46,581,350 | 39,586,544 | −6,994,806 |
| `snap` | federal | 510,235,811 | 522,202,400 | +11,966,589 |
| `nj_property_tax_relief` | state | 13,404,370 | 13,404,370 | 0 |
| `commodity_supplemental_food_program` | federal | 235,461,818 | 266,726,939 | +31,265,121 |
| `az_refundable_credits` | state | 3,854,760 | 3,854,760 | 0 |
| `ca_refundable_credits` | state | 1,501,372 | 1,501,372 | 0 |
| `co_refundable_credits` | state | 896,757 | 896,757 | 0 |
| `dc_refundable_credits` | state | 50,830,765 | 50,830,765 | 0 |
| `hi_refundable_credits` | state | 5,438,214 | 5,438,214 | 0 |
| `id_refundable_credits` | state | 7,239,368 | 7,239,368 | 0 |
| `il_refundable_credits` | state | 335,169 | 335,169 | 0 |
| `in_refundable_credits` | state | 657,074 | 657,074 | 0 |
| `me_refundable_credits` | state | 508,946 | 725,842 | +216,896 |
| `mi_refundable_credits` | state | 13,420,555 | 13,497,063 | +76,509 |
| `mt_refundable_credits` | state | 1,909,046 | 2,978,821 | +1,069,775 |
| `nm_refundable_credits` | state | 2,230,323 | 2,432,773 | +202,450 |
| `nj_refundable_credits` | state | 2,768,581 | 2,768,581 | 0 |
| `ok_refundable_credits` | state | 375,928 | 965,716 | +589,788 |
| `wi_refundable_credits` | state | 1,650,261 | 1,650,261 | 0 |
| `employee_payroll_tax` | federal | −329,979,748 | −329,979,748 | 0 |
| `income_tax_before_refundable_credits` | federal | −600,554,086 | −567,344,092 | +33,209,994 |
| `state_income_tax_before_refundable_credits` | state | −135,534,408 | −135,572,295 | −37,887 |
| `state_use_tax` | state | −1,826,999 | −1,820,504 | +6,495 |

### By SSI receipt

| Group | Households | Mean Social Security change | Mean net change | Federal | State | Local | Taken back |
|---|---:|---:|---:|---:|---:|---:|---:|
| SSI in both | 12 | −2,141 | −2,153 | −173,833,563 | 0 | 0 | -0.6% † |
| no SSI | 288 | −2,903 | −2,852 | −4,061,738,167 | +2,124,026 | 0 | 1.8% † |

Federal, state and local are weighted total changes; the means are per weighted household. † The group's Social Security rises for some households and falls for others, so its share taken back is a ratio of net sums, not a share of either direction.

### By baseline net income decile

| Group | Households | Mean Social Security change | Mean net change | Federal | State | Local | Taken back |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 39 | −62 | −141 | −29,312,170 | +76,509 | 0 | -128.0% † |
| 2 | 45 | −935 | −790 | −174,488,496 | 0 | 0 | 15.5% |
| 3 | 44 | −2,151 | −2,110 | −428,074,248 | +419,346 | 0 | 1.9% |
| 4 | 33 | −2,858 | −2,823 | −513,812,626 | +1,069,775 | 0 | 1.2% |
| 5 | 21 | −2,273 | −2,269 | −270,144,959 | 0 | 0 | 0.2% |
| 6 | 25 | −3,143 | −3,080 | −394,987,205 | +591,984 | 0 | 2.0% |
| 7 | 32 | −3,889 | −3,828 | −522,867,509 | −37,887 | 0 | 1.6% |
| 8 | 18 | −5,478 | −5,478 | −535,013,176 | 0 | 0 | 0.0% |
| 9 | 19 | −6,738 | −6,737 | −671,477,167 | +2,545 | 0 | 0.0% |
| 10 | 24 | −6,454 | −6,233 | −695,394,175 | +1,754 | 0 | 3.4% |

Federal, state and local are weighted total changes; the means are per weighted household. † The group's Social Security rises for some households and falls for others, so its share taken back is a ratio of net sums, not a share of either direction.

### By direction of Social Security

| Group | Households | Mean Social Security change | Mean net change | Federal | State | Local | Taken back |
|---|---:|---:|---:|---:|---:|---:|---:|
| Social Security rises | 2 | +2,893 | +1,310 | +17,821,915 | 0 | 0 | 54.7% |
| Social Security falls | 175 | −5,131 | −5,021 | −4,253,393,646 | +2,124,026 | 0 | 2.1% |
| Social Security unchanged | 123 | 0 | 0 | 0 | 0 | 0 | n/a |

Federal, state and local are weighted total changes; the means are per weighted household. † The group's Social Security rises for some households and falls for others, so its share taken back is a ratio of net sums, not a share of either direction.

### Medicaid, CHIP and Medicare Savings Programs: federal and state cost

From policyengine-us 2.18.0's own cost-share variables, in the default simulations (Medicaid at the release's spending over enrollment per enrollee).

| Program | Scenario | Total | Federal | State |
|---|---|---:|---:|---:|
| Medicaid | current law | 1,161,545,460 | 693,699,790 | 467,845,878 |
| Medicaid | option 2 | 1,206,578,842 | 716,216,481 | 490,362,569 |
| Medicaid | change | +45,033,382 | +22,516,691 | +22,516,691 |
| CHIP | current law | 0 | 0 | 0 |
| CHIP | option 2 | 0 | 0 | 0 |
| CHIP | change | 0 | 0 | 0 |
| MSP | current law | 418,392,043 | 322,992,825 | 95,399,263 |
| MSP | option 2 | 431,049,194 | 330,770,911 | 100,278,327 |
| MSP | change | +12,657,150 | +7,778,086 | +4,879,064 |

### Runtime and memory

- Track M and the population: track m cohort 0.3 s, track m evaluate 0.0 s, benefits 0.0 s, population 0.0 s.
- policyengine-us child: 48 s wall (import 8 s), peak resident memory 3.19 GiB; stated bounds: 1200 s and 8 GiB.
- default, current_law: one simulation, built in 0.1 s, calculated in 6.4 s.
- default, option_2: one simulation, built in 0.0 s, calculated in 4.1 s.
- with_health, current_law: one simulation, built in 0.1 s, calculated in 7.0 s.
- with_health, option_2: one simulation, built in 0.0 s, calculated in 4.1 s.

### Checks

- Every household's leaves sum exactly (in cents) to its net change; weighted, the leaves, categories and levels each sum exactly to the weighted net change, and each grouping's groups to the population's.
- PolicyEngine-US's `social_security` equals the Track M benefits in every household and scenario.
- Households whose Social Security does not change do not change at all (no result leaks between households).
- Deciles equal policyengine-us's `household_income_decile` in all 300 households.
- Means-tested benefits, income taxes or refundable credits moving the same way as Social Security: 1 household-category pairs (AL 1; recorded, not refused). Leaf changes under $2: 3.

## 3,000 invented family units (INVENTED DATA - NOT A COMPARISON, NOT THE US)

3,000 households, 4,305 people, 51 states; weighted 15,136,532 households and 21,723,881 people (invented weights).

Track M (row MS0): 2,523 people have an own or linked worker record in the policy window; 39 receive the minimum under option 2; Social Security rises for 10 people and falls for 2,295. 150 unlinked auxiliaries and 122 people whose records hold no observed covered earnings keep their 2022 amount, carried by the COLAs, in both scenarios.

| Total | Change |
|---|---:|
| Social Security | −43,477,342,955 |
| Net income | −42,268,124,105 |
| Net income, with health coverage | −41,449,530,119 |
| Share of the Social Security change taken back | 2.8% † |

### By level of government

| Level | Baseline | Reform | Change | Share taken back |
|---|---:|---:|---:|---:|
| Federal | 536,597,152,880 | 494,263,183,121 | −42,333,969,759 | 2.6% |
| State | 29,870,475 | 95,716,130 | +65,845,654 | 0.2% |
| Local | 0 | 0 | 0 | 0.0% |
| Market income | 157,901,637,314 | 157,901,637,314 | 0 | 0.0% |

Federal includes Social Security; its share taken back excludes it. Shares sum exactly to the total share.

### By component

| Component | Level | Baseline | Reform | Change |
|---|---|---:|---:|---:|
| `employment_income` | market_income | 45,477,868,838 | 45,477,868,838 | 0 |
| `interest_income` | market_income | 7,388,626,120 | 7,388,626,120 | 0 |
| `pension_income` | market_income | 105,035,142,356 | 105,035,142,356 | 0 |
| `ak_permanent_fund_dividend` | state | 424,703,500 | 424,703,500 | 0 |
| `social_security` | federal | 540,464,425,651 | 496,987,082,696 | −43,477,342,955 |
| `ssi` | federal | 406,677,550 | 402,935,708 | −3,741,841 |
| `snap` | federal | 4,262,558,683 | 4,764,349,787 | +501,791,104 |
| `me_ssp` | state | 1,101,828 | 1,101,828 | 0 |
| `ma_state_supplement` | state | 26,426,599 | 26,426,599 | 0 |
| `mi_ssp` | state | 3,581,676 | 3,581,676 | 0 |
| `mn_msa` | state | 985,034 | 7,342,231 | +6,357,197 |
| `co_oap` | state | 7,982,052 | 7,982,052 | 0 |
| `ak_ssp` | state | 15,341,875 | 15,341,875 | 0 |
| `wa_ssp` | state | 5,321,209 | 5,321,209 | 0 |
| `nj_property_tax_relief` | state | 77,735,560 | 77,735,560 | 0 |
| `commodity_supplemental_food_program` | federal | 2,036,389,910 | 2,288,744,527 | +252,354,617 |
| `az_refundable_credits` | state | 22,613,888 | 22,613,888 | 0 |
| `ca_refundable_credits` | state | 7,291,366 | 7,682,081 | +390,716 |
| `co_refundable_credits` | state | 8,684,781 | 8,490,462 | −194,319 |
| `dc_refundable_credits` | state | 241,273,272 | 242,363,210 | +1,089,938 |
| `hi_refundable_credits` | state | 94,587,477 | 95,074,851 | +487,374 |
| `id_refundable_credits` | state | 50,168,509 | 50,168,509 | 0 |
| `il_refundable_credits` | state | 1,213,875 | 1,213,875 | 0 |
| `in_refundable_credits` | state | 22,461,624 | 23,052,672 | +591,048 |
| `ma_refundable_credits` | state | 32,203,891 | 38,932,289 | +6,728,397 |
| `me_refundable_credits` | state | 38,866,133 | 47,898,653 | +9,032,520 |
| `md_refundable_credits` | state | 5,976,330 | 6,347,995 | +371,665 |
| `mi_refundable_credits` | state | 143,321,496 | 153,975,664 | +10,654,168 |
| `mo_refundable_credits` | state | 13,111,749 | 13,990,875 | +879,126 |
| `mt_refundable_credits` | state | 58,496,975 | 61,833,911 | +3,336,936 |
| `nm_refundable_credits` | state | 14,012,057 | 15,598,807 | +1,586,750 |
| `nj_refundable_credits` | state | 12,146,539 | 12,146,539 | 0 |
| `ny_refundable_credits` | state | 1,500,825 | 1,500,825 | 0 |
| `ok_refundable_credits` | state | 10,283,920 | 10,619,024 | +335,104 |
| `ri_refundable_credits` | state | 20,778,304 | 28,056,107 | +7,277,803 |
| `wi_refundable_credits` | state | 13,992,178 | 19,072,065 | +5,079,887 |
| `employee_payroll_tax` | federal | −3,549,161,542 | −3,549,161,542 | 0 |
| `income_tax_before_refundable_credits` | federal | −7,023,737,372 | −6,630,768,056 | +392,969,316 |
| `state_income_tax_before_refundable_credits` | state | −1,334,215,957 | −1,322,717,992 | +11,497,965 |
| `state_use_tax` | state | −12,078,088 | −11,734,709 | +343,379 |

### By SSI receipt

| Group | Households | Mean Social Security change | Mean net change | Federal | State | Local | Taken back |
|---|---:|---:|---:|---:|---:|---:|---:|
| SSI in both | 99 | −1,933 | −1,926 | −928,326,550 | +1,279,867 | 0 | 0.3% † |
| SSI under the reform only | 1 | −2,568 | −1,311 | −6,127,352 | 0 | 0 | 48.9% |
| no SSI | 2,900 | −2,903 | −2,821 | −41,399,515,857 | +64,565,787 | 0 | 2.8% † |

Federal, state and local are weighted total changes; the means are per weighted household. † The group's Social Security rises for some households and falls for others, so its share taken back is a ratio of net sums, not a share of either direction.

### By baseline net income decile

| Group | Households | Mean Social Security change | Mean net change | Federal | State | Local | Taken back |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 416 | −390 | −343 | −741,655,019 | +851,577 | 0 | 12.1% † |
| 2 | 437 | −1,205 | −1,028 | −2,152,298,354 | +11,051,175 | 0 | 14.7% † |
| 3 | 390 | −2,347 | −2,252 | −4,394,517,417 | +6,005,149 | 0 | 4.0% |
| 4 | 345 | −2,375 | −2,324 | −3,999,380,409 | +13,133,829 | 0 | 2.2% † |
| 5 | 316 | −2,923 | −2,890 | −4,509,139,491 | +12,021,632 | 0 | 1.1% |
| 6 | 238 | −3,133 | −3,111 | −4,054,914,474 | +2,242,152 | 0 | 0.7% |
| 7 | 234 | −4,049 | −4,023 | −4,780,135,576 | +7,296,955 | 0 | 0.6% |
| 8 | 213 | −4,950 | −4,921 | −5,368,649,095 | +1,953,855 | 0 | 0.6% † |
| 9 | 208 | −5,751 | −5,705 | −6,070,344,471 | +1,204,620 | 0 | 0.8% |
| 10 | 203 | −6,333 | −6,067 | −6,262,935,452 | +10,084,712 | 0 | 4.2% |

Federal, state and local are weighted total changes; the means are per weighted household. † The group's Social Security rises for some households and falls for others, so its share taken back is a ratio of net sums, not a share of either direction.

### By direction of Social Security

| Group | Households | Mean Social Security change | Mean net change | Federal | State | Local | Taken back |
|---|---:|---:|---:|---:|---:|---:|---:|
| Social Security rises | 10 | +1,220 | +712 | +38,489,360 | −1,381 | 0 | 41.6% |
| Social Security falls | 1,698 | −5,050 | −4,906 | −42,372,459,119 | +65,847,036 | 0 | 2.8% |
| Social Security unchanged | 1,292 | 0 | 0 | 0 | 0 | 0 | n/a |

Federal, state and local are weighted total changes; the means are per weighted household. † The group's Social Security rises for some households and falls for others, so its share taken back is a ratio of net sums, not a share of either direction.

### Medicaid, CHIP and Medicare Savings Programs: federal and state cost

From policyengine-us 2.18.0's own cost-share variables, in the default simulations (Medicaid at the release's spending over enrollment per enrollee).

| Program | Scenario | Total | Federal | State |
|---|---|---:|---:|---:|
| Medicaid | current law | 8,273,433,295 | 4,911,732,438 | 3,361,700,971 |
| Medicaid | option 2 | 8,578,248,690 | 5,088,399,277 | 3,489,849,442 |
| Medicaid | change | +304,815,396 | +176,666,839 | +128,148,471 |
| CHIP | current law | 0 | 0 | 0 |
| CHIP | option 2 | 0 | 0 | 0 |
| CHIP | change | 0 | 0 | 0 |
| MSP | current law | 4,861,349,237 | 3,431,200,164 | 1,430,149,377 |
| MSP | option 2 | 5,375,127,870 | 3,762,651,531 | 1,612,476,859 |
| MSP | change | +513,778,633 | +331,451,367 | +182,327,482 |

### Runtime and memory

- Track M and the population: track m cohort 2.5 s, track m evaluate 0.3 s, benefits 0.4 s, population 0.4 s.
- policyengine-us child: 86 s wall (import 9 s), peak resident memory 6.56 GiB; stated bounds: 2400 s and 12 GiB.
- default, current_law: one simulation, built in 0.1 s, calculated in 8.9 s.
- default, option_2: one simulation, built in 0.0 s, calculated in 8.3 s.
- with_health, current_law: one simulation, built in 0.1 s, calculated in 9.5 s.
- with_health, option_2: one simulation, built in 0.0 s, calculated in 6.3 s.

### Checks

- Every household's leaves sum exactly (in cents) to its net change; weighted, the leaves, categories and levels each sum exactly to the weighted net change, and each grouping's groups to the population's.
- PolicyEngine-US's `social_security` equals the Track M benefits in every household and scenario.
- Households whose Social Security does not change do not change at all (no result leaks between households).
- Deciles equal policyengine-us's `household_income_decile` in all 3,000 households.
- Means-tested benefits, income taxes or refundable credits moving the same way as Social Security: 14 household-category pairs (AL 5, CO 4, MO 1, OK 1, OR 3; recorded, not refused). Leaf changes under $2: 30.

## Invented inputs

The invented generator draws no state, income other than Social Security, assets or rent. Each is drawn here from the distribution below (seed stream [20260930, 20260930]), rounded to the dollar. None is a survey, Census or program value.

| Item | Label | Distribution |
|---|---|---|
| `state` | INVENTED | uniform over the 50 states and DC (bridge.STATE_FIPS) (per family unit) |
| `renter` | INVENTED | drawn with probability 0.4 (per family unit) |
| `monthly_rent` | INVENTED | lognormal, median $900, log sigma 0.35 (per family unit (renters)) |
| `wealth1` | INVENTED | with probability 0.3 uniform on $0-$3,000; otherwise lognormal, median $60,000, log sigma 1.4 (per family unit) |
| `vehicles` | INVENTED | drawn with probability 0.75; lognormal, median $9,000, log sigma 0.7 (per family unit) |
| `labor` | INVENTED | drawn with probability 0.1 (reference_person), 0.1 (spouse), 0.05 (other_member); lognormal, median $12,000, log sigma 0.9 (per person) |
| `annuities` | INVENTED | drawn with probability 0.35; lognormal, median $9,000, log sigma 0.9 (per person) |
| `interest` | INVENTED | drawn with probability 0.45; lognormal, median $300, log sigma 1.3 (per person) |

| Invented item | PolicyEngine-US input | Label | Convention |
|---|---|---|---|
| labor | `employment_income` | INVENTED | earned income: the PSID labor items of family_income.HW_EARNED_CONCEPTS (data/family_income.py:1148-1154), which estimates.adjusted_poverty treats as earned income (adjusted_poverty.py:118, 1463-1466) |
| interest | `interest_income` | INVENTED | asset income: an item of family_income.ASSET_INCOME_CONCEPTS (data/family_income.py:1131-1143) |
| annuities | `taxable_private_pension_income` | INVENTED | income from annuities and IRAs (HEAD ANNUITIES; adjusted_poverty.py:28-33), drawn for every person here, entered as a taxable private pension as the bridge enters its households' pensions |
| max(0, wealth1 - vehicles) | `bank_account_assets` | INVENTED | adjusted_poverty's resource proxy (adjusted_poverty.py:118-119, 1469), on the reference person; policyengine-us 2.18.0 counts bank_account_assets as an SSI resource (parameters/gov/ssa/ssi/eligibility/resources/countable.yaml:7) |
| 12 x monthly_rent | `pre_subsidy_rent` | INVENTED | no adjusted_poverty analog; renters only, on the reference person, as the bridge enters its households' rent |

Flags set for every household: `has_heating_cooling_expense` = True, `takes_up_housing_assistance_if_eligible` = False, `living_arrangements_allow_for_food_preparation` = True.

## Notes

- INVENTED DATA - NOT A COMPARISON, NOT THE US. Every person, family, weight, state, income, asset and rent amount is invented; the totals describe that invented population and nothing else. They are not estimates for the US, not a comparison with DYNASIM3 and not a registered result.
- The population is invented by design until the registered real-data analysis (cos decision d727, under Max's d479).
- Social Security amounts come from Track M's rules on invented records (row MS0), carried to 2026 with statutory COLAs as the bridge carries them. Every own worker benefit enters as social_security_retirement, spouse's excesses as social_security_dependents and widow(er)'s excesses as social_security_survivors; a disability-origin record's benefit is not entered as disability benefits (a mapping choice; everyone is 66 or older in 2026, so aged for SSI and Medicare either way).
- Two groups keep their invented 2022 amount, carried by the COLAs, in both scenarios, because Track M computes no benefit for them: unlinked auxiliaries, and people paid an own benefit whose records hold no observed covered earnings (the invented generator, like the PSID panel, has labor income for reference persons and spouses only). The reform cannot reach them here.
- The reform cuts every in-window PIA by the option's uniform cut unless the minimum is higher, so most in-window people lose against current-law benefits; the share taken back therefore mostly measures how much of a cut other programs and taxes cushion. The groupings split rises from falls.
- Each family unit is one household, SPM unit and family. The reference person and spouse form one marital unit and file one joint return; any other member is a single filer in a marital unit of their own, never a dependent. Medicare quarters of coverage are policyengine-us's default of 40 for everyone, since every person receives OASDI.
- Default net income excludes health coverage. The with-health sensitivity counts Medicaid at the release's state spending over enrollment per enrollee (as for one household alone), not policyengine-us's dataset allocation of each state's calibrated spending across the simulated enrollees, which is meaningless for an invented population.
- No behavioral, claiming or take-up response to the reform. No float32 trace guard runs over the population (the bridge traces one household at a time); leaf changes under $2 are counted instead.
- Where Social Security changes, a means-tested benefit, income tax or refundable credit that moves the same way is recorded, not refused: some are mechanisms (Alabama deducts federal income tax, so a lower federal tax raises Alabama's), and the JSON lists every case with its state.
- SNAP for October-December 2026 uses USDA's fiscal-2027 maximum allotment ($306 a month for one person in the contiguous states) and standard deduction ($217) as policyengine-us 2.18.0 encodes them (gov/usda/snap/max_allotment.yaml:33, income/deductions/standard.yaml:17). No state's standard utility allowance has a fiscal-2027 entry there (income/deductions/utility/standard/main.yaml has none dated 2026-10-01), so those months use each state's fiscal-2026 amount.
- In policyengine-us 2.18.0 SNAP counts California's SSI supplement as unearned income (gov/usda/snap/income/sources/unearned_spm_unit.yaml:13).
- Take-up is PolicyEngine-US's default: full for SSI, SNAP and Medicaid (takes_up_ssi_if_eligible.py:9, takes_up_snap_if_eligible.py:9, takes_up_medicaid_if_eligible.py:9). The Commodity Supplemental Food Program has no take-up input: every eligible person gets USDA's cost per caseload slot, $651 in 2026 (commodity_supplemental_food_program.py:10-11, gov/usda/csfp/amount.yaml:11), though the program is caseload-limited and serves far fewer people than are eligible; its change here is a notch at 150 percent of the poverty guideline. As in the bridge, housing-voucher take-up is switched off (vouchers are rationed), and every household pays heating or cooling costs and can prepare food at home.
- California's 2026 aged or disabled payment standard is set to the published $1,233.94 a month for the whole population (policyengine-us 2.18.0 holds $1,206.94 from 2025-01-01). Only CA's households read it: every variable that reads the parameter is under variables/gov/states/ca/ (ca_state_supplement is defined for California only, ca_state_supplement.py:10).
