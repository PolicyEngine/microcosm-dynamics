# INVENTED DATA - NOT A COMPARISON, NOT THE US

Phase 0: **permitted** — **option A: invented data only, per d479**.

PR: https://github.com/PolicyEngine/microcosm-dynamics/pull/498 (against `master`).
Head: [pe-us-population-min-benefit-20260930](https://github.com/PolicyEngine/microcosm-dynamics/tree/pe-us-population-min-benefit-20260930).
Execution/code head: `2718dda95e87561048ff929f05bfbcc5b5d221d3`; code clean at execution. The final artifact/report commit follows that execution commit; its SHA is recorded on the PR and in the delivery message.

Completed the existing implementation, kept the seeded invented cohort/careers and MS0 benefit calculations, hardened validation, removed extra simulation construction, exported exact rational totals, and generated the two sizes with JSON, Markdown and PNG/SVG charts. The design documents mechanisms with file:line references and requirements for registered real-data work. See `invented_population.py:271,296,384,609`, `population.py:980,1522,1639` and `population_summary.py:61,310`.

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
| 300 | 47.5 | 3.19 | 1200 / 8 |
| 3,000 | 86.0 | 6.56 | 2400 / 12 |

Both sizes pass their bounds; both full runs reproduce all outcomes and checks exactly across repeated execution. Every exported leaf/category/government fraction sums exactly to net change, and every SSI-status/decile/direction partition sums to the population (`population_summary.py:310-363`; `test_pe_us_population_artifact.py:122`). Rounded display dollars can differ by cents when added.

Caveats:

- All people, weights, states, incomes, assets and rents are invented. These results provide no US inference and no comparator result. The real-data version still needs registration under d727; no PSID file, restricted file or comparator value was opened and no registered-run guard was altered or bypassed.
- Household Medicaid valuation is pinned to the standalone-household convention (`population.py:919-958`). Default take-up and the documented retained 2022 benefits are modeling choices; there is no behavioral or claiming response (`docs/design/pe_us_population_run.md:103,462`; `population.py:996`).
- Health memo cost splits retain PolicyEngine-US float32 rounding. Their largest per-person gap is recorded separately and can magnify under invented weights; federal plus state memo costs need not equal the displayed total to the cent. The exact net-income decomposition is unaffected (`population_summary.py:388-450`).
- No county or municipality input is drawn; both runs show zero local change (`population.py:616-666`). The real-data analysis needs local geography. Direction anomalies and small leaf changes are recorded; there is no population-wide float32 trace guard (`scripts/pe_us_population_invented.py:257-320`).

Validation (targeted only; `OMP_NUM_THREADS=1`, required dynamics interpreter/PYTHONPATH, and `POPULACE_DYNAMICS_PE_US_PYTHON` pointing to the pinned release):

- Initial mapper + existing bridge: **168 passed**. Hardened mapper suite: **33 passed**; the strengthened cancelling-change check also passed.
- Live PolicyEngine-US differentials/native Medicaid checks: **7 passed**. Live committed 300-family reproduction: **1 passed**. This covers all **8** population oracle tests.
- Exported artifact labels, provenance, exact identities and both scale bounds: **9 passed**.
- Required `pytest -p no:xdist tests -k test__given_collected_suite__then_tiers_match_policy_manifest`: **1 passed, 11,076 deselected**. Manifest and README total: **11,077**.
- Black `-l 79` and ruff passed for all changed Python files; both charts inspected visually after correcting clipping and legend overlap. No full suite was run on the host.

Outputs: [full tables](pe_us_population_invented.md), [machine-readable results](pe_us_population_invented.json), [300-family chart](pe_us_population_invented_300_by_level.png), [3,000-family chart](pe_us_population_invented_3000_by_level.png), and matching SVGs.

Workspace Git note: the ordinary worktree metadata is outside the sandbox writable root and remains at its original head. Commits were created using workspace-local metadata in `.cache/pe-us-population-git` and pushed normally to the assigned branch, preserving the two prior commits. In this workspace, use `GIT_DIR="$PWD/.cache/pe-us-population-git" git status` or `git log` with that same environment variable to inspect the completed branch. No history was rewritten and no main/master branch was pushed.
