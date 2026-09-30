# The minimum benefit after taxes and transfers: sample households

**Illustrative household, not survey data.** Three households built around one illustrative worker, run through PolicyEngine-US for payment year 2026. Amounts are annual 2026 dollars. Taxes and costs enter as negative contributions, so each column sums to net income (PolicyEngine-US's `household_net_income`, which by default excludes health coverage).

- Microcosm Dynamics commit `212a9667b8472156a0a6140d1c6776cb9f0948fb`
- PolicyEngine-US 1.822.5 at `e4363903f3a545e69e10b563a46a52d1f1ce609d`
- Reform: exercise 4, option 2 (Standard price-indexed minimum benefit), compared with current-law scheduled benefits
- Social Security: 8,916 a year under current law, 10,968 under the reform

## Summary

| Household | State | Social Security | Net income | Share of the benefit increase kept | Net income with health coverage |
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

## Household A

The worker alone: no income besides Social Security, $1,500 in the bank (under the SSI resource limit), renting for $800 a month.

### Household A, California

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 3,252 | 1,200 | −2,052 |
| State benefits (incl. SSI supplements) | 2,555 | 2,555 | 0 |
| SNAP | 3,608 | 3,608 | 0 |
| Other benefits | 651 | 651 | 0 |
| State income tax | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −1 | −1 | 0 |
| **Net income** | **18,981** | **18,981** | **0** |

Memo (outside default net income): Medicaid at cost 9,236 → 9,236; Medicare Savings Program 0 → 0. Net income with health coverage counted changes by 0.

### Household A, Montana

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 3,252 | 1,200 | −2,052 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 3,608 | 3,608 | 0 |
| Other benefits | 651 | 651 | 0 |
| State income tax | 1,150 | 1,150 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **17,577** | **17,577** | **0** |

Memo (outside default net income): Medicaid at cost 10,799 → 10,799; Medicare Savings Program 0 → 0. Net income with health coverage counted changes by 0.

### Household A, Florida

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| SSI (federal) | 3,252 | 1,200 | −2,052 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 3,608 | 3,608 | 0 |
| Other benefits | 651 | 651 | 0 |
| State income tax | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **16,427** | **16,427** | **0** |

Memo (outside default net income): Medicaid at cost 9,200 → 9,200; Medicare Savings Program 0 → 0. Net income with health coverage counted changes by 0.

## Household B

The same worker with a $4,800-a-year ($400-a-month) private pension, which puts her countable income above the federal SSI benefit rate.

### Household B, California

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| State benefits (incl. SSI supplements) | 1,007 | 0 | −1,007 |
| SNAP | 3,608 | 2,912 | −696 |
| Other benefits | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| State income tax | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −1 | −1 | 0 |
| **Net income** | **18,981** | **19,330** | **+349** |

Memo (outside default net income): Medicaid at cost 9,236 → 9,236; Medicare Savings Program 0 → 0. Net income with health coverage counted changes by +349.

### Household B, Montana

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 3,608 | 3,401 | −207 |
| Other benefits | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| State income tax | 1,150 | 1,150 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **19,125** | **20,970** | **+1,845** |

Memo (outside default net income): Medicaid at cost 0 → 0; Medicare Savings Program 5,335 → 5,335. Net income with health coverage counted changes by +1,845.

### Household B, Florida

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| State benefits (incl. SSI supplements) | 0 | 0 | 0 |
| SNAP | 2,996 | 2,072 | −924 |
| Other benefits | 651 | 651 | 0 |
| Market income | 4,800 | 4,800 | 0 |
| State income tax | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **17,363** | **18,491** | **+1,128** |

Memo (outside default net income): Medicaid at cost 9,200 → 0; Medicare Savings Program 0 → 5,335. Net income with health coverage counted changes by −2,737.

## Household C

The same worker with a $30,000-a-year private pension, enough for part of her Social Security to be taxable.

### Household C, California

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| Market income | 30,000 | 30,000 | 0 |
| Federal income tax | −1,070 | −1,161 | −91 |
| State income tax | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | −3 | −2 | +1 |
| **Net income** | **37,843** | **39,805** | **+1,962** |

Memo (outside default net income): Medicaid at cost 0 → 0; Medicare Savings Program 0 → 0. Net income with health coverage counted changes by +1,962.

### Household C, Montana

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| Market income | 30,000 | 30,000 | 0 |
| Federal income tax | −1,070 | −1,161 | −91 |
| State income tax | −199 | −275 | −76 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **37,647** | **39,531** | **+1,885** |

Memo (outside default net income): Medicaid at cost 0 → 0; Medicare Savings Program 0 → 0. Net income with health coverage counted changes by +1,885.

### Household C, Florida

| Component | Baseline | Reform | Change |
|---|---:|---:|---:|
| Social Security | 8,916 | 10,968 | +2,052 |
| Market income | 30,000 | 30,000 | 0 |
| Federal income tax | −1,070 | −1,161 | −91 |
| State income tax | 0 | 0 | 0 |
| Other taxes (payroll, use, local) | 0 | 0 | 0 |
| **Net income** | **37,846** | **39,807** | **+1,961** |

Memo (outside default net income): Medicaid at cost 0 → 0; Medicare Savings Program 0 → 0. Net income with health coverage counted changes by +1,961.

## Notes

- Illustrative households, not survey data: one worker, chosen so the minimum binds, in three living situations.
- The bridge passes Microcosm's Social Security amounts to PolicyEngine-US as inputs; it does not run over the projected population and applies no behavioral response.
- The reform is option 2 of exercise 4 (the standard price-indexed minimum with its printed 12.81 percent uniform cut for new entitlees). The worker is on the minimum, so the cut does not reach her; a worker above the minimum would lose 12.81 percent.
- The baseline is current-law scheduled benefits. Against option 1 (reduced current law, the Report's own benchmark) her gain would be larger; that PIA is in the JSON as a memo, not run through PolicyEngine-US.
- Net income is PolicyEngine-US's household_net_income, which by default excludes health coverage (Medicaid at cost, Medicare Savings Programs); the with-health sensitivity and the memo lines report it.
- SNAP amounts for October-December 2026 are PolicyEngine-US's CPI-U projection of fiscal-2027 values (gov/usda/snap/uprating.yaml; max_allotment.yaml carries uprating metadata), not USDA's published figures; every other 2026 parameter on these paths has a dated 2026 entry or holds an earlier one.
- California's aged or disabled payment standard has no 2026 entry in this checkout, so 2026 uses the 2025 value (1,206.94 a month).
- Take-up is PolicyEngine-US's default (full) for SSI, SNAP and Medicaid; housing assistance is switched off because vouchers are rationed, and the household can prepare food at home.
- COLAs for 2023-2025 are derived from PolicyEngine-US's third-quarter CPI-W averages under 42 USC 415(i)(1)(D); the derived 2022 COLA equals the committed SSA history's.
