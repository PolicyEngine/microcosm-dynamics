# INVENTED DATA - NOT A COMPARISON, NOT THE US

Phase 0: **permitted** — **option A: invented data only, per d479**.

PR: https://github.com/PolicyEngine/microcosm-dynamics/pull/498 (against `master`).
Head: [pe-us-population-min-benefit-20260930](https://github.com/PolicyEngine/microcosm-dynamics/tree/pe-us-population-min-benefit-20260930).
Execution/code head: `4b6efb990e6315b6b4aec7197f1572320ca93bcf`; code clean at execution. The artifact/report commit follows that execution commit; its SHA is recorded on the PR and in the delivery message.

Completed the population implementation and round-1 review fixes. Before evaluation, benefit conversion or mapping, the guard checks the invented provenance of the inputs, cohort, frames and structural inputs, and matches the records' person ids, family units and weights to the cohort. Benefit conversion takes the checked cohort and explicitly refuses an own benefit without an evaluated own record. Current anchor members must match the universe exactly. See `invented_population.py:303,328,360,413,439,728` and the [design](../../design/pe_us_population_run.md).

Headline results below are **INVENTED**, weighted annual 2026 dollars. Default net income excludes health coverage.

| INVENTED families | People | Population Social Security change | Population net income change |
|---|---:|---:|---:|
| 300 | 427 | $-4,305,018,628.80 | $-4,233,447,704.13 |
| 3,000 | 4,305 | $-43,477,342,954.80 | $-42,268,124,104.67 |

**Share of an increase taken back:** the following groups contain only households whose Social Security rises. This is distinct from the mixed population ratio (`population_summary.py:122-154,182-196`).

| INVENTED families in full run | Households with an increase | Their weighted Social Security increase | Their weighted net income increase | Taken back |
|---|---:|---:|---:|---:|
| 300 | 2 | $39,361,042.80 | $17,821,915.20 | 54.72% |
| 3,000 | 10 | $65,913,304.80 | $38,487,978.34 | 41.61% |

Option 2 also imposes a 12.81% uniform cut, so most affected households lose (`min_benefit_track_m/rules.py:358-388`). Population-wide mixed ratios are 1.66% and 2.78%; the cuts-only cushioning shares are 2.14% and 2.84%. These are invented outcomes, with invented expansion weights, not US totals.

| INVENTED families | Final wall seconds | Final peak RSS GiB | Bound seconds / GiB |
|---|---:|---:|---|
| 300 | 784.9 | 3.13 | 1200 / 8 |
| 3,000 | 492.7 | 6.48 | 2400 / 12 |

Both sizes pass their bounds. Two regenerations of both sizes reproduce every outcome and check; every outcome and prior check also matches the pre-review artifacts. The Social Security check now compares the household's sum of four frame inputs with PolicyEngine-US's output in both scenarios and both variants, including retained 2022 amounts carried forward. Every exported leaf/category/government fraction sums exactly to net change, and every SSI-status/decile/direction partition sums to the population (`population_summary.py:310`; `test_pe_us_population_artifact.py:201`). Rounded display dollars can differ by cents when added.

Caveats:

- All people, weights, states, incomes, assets and rents are invented. These results provide no US inference and no comparator result. The real-data version still needs registration under d727; no PSID file, restricted file or comparator value was opened and no registered-run guard was altered or bypassed.
- Household Medicaid valuation is pinned to the standalone-household convention: state spending divided by state enrollment, times the person's filled cost index divided by their household's positive-index average, which falls back to 1 (`population.py:919-958`; `medicaid_cost_if_enrolled.py:11-22`). Default take-up and the documented retained 2022 benefits are modeling choices; there is no behavioral or claiming response.
- Health memo cost splits retain PolicyEngine-US float32 rounding. Their largest per-person gap is recorded separately and can magnify under invented weights; federal plus state memo costs need not equal the displayed total to the cent. The exact net-income decomposition is unaffected (`population_summary.py:388-450`).
- No county or municipality input is drawn; both runs show zero local change (`population.py:616-666`). The real-data analysis needs local geography. Direction anomalies and small leaf changes are recorded; there is no population-wide float32 trace guard (`scripts/pe_us_population_invented.py:263-337`).

Validation (targeted only; `OMP_NUM_THREADS=1`, required dynamics interpreter/PYTHONPATH, and `POPULACE_DYNAMICS_PE_US_PYTHON` pointing to the pinned release):

- Population validation and summary checks, including swapped cohort/frames, missing own records, exact anchor membership and a Hypothesis provenance property: **38 passed**. Existing bridge regressions: **136 passed**.
- Live PolicyEngine-US differentials/native Medicaid checks: **7 passed**. Live committed 300-family reproduction: **1 passed**. This covers all **8** population oracle tests.
- Exported artifact labels (including this report), footnote placement, market-income wording, provenance, exact identities and both scale bounds: **12 passed**.
- Required `pytest -p no:xdist tests -k test__given_collected_suite__then_tiers_match_policy_manifest`: **1 passed, 11,084 deselected**. Manifest and README total: **11,085**.
- Black `-l 79` and ruff passed for all changed Python files. Both regenerated charts were inspected visually, and both PNGs and both SVGs are byte-identical across the two regenerations. No full suite was run on the host.

Outputs: [full tables](pe_us_population_invented.md), [machine-readable results](pe_us_population_invented.json), [300-family chart](pe_us_population_invented_300_by_level.png), [3,000-family chart](pe_us_population_invented_3000_by_level.png), and matching SVGs.
