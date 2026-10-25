# OP1 implementation report

## 1. Changes and design

The review fixes implement `docs/design/open_population.md` on master,
revision 14, SHA-256
`ca67cbfdb7c94d0de10ad304f4bb9744da90af076f54061a146a45a870ecf339`.
`git diff 5c82dbd9 origin/master -- docs/design/open_population.md` confirms
that OP1's milestone row, horizon rule and stock-flow properties did not
change since revision 12. Revision 14 clarifies §7's alignment death property:
mortality receives the previous year's roster plus that year's scheduled
entrants. The seam appends entrants before mortality
(`src/populace_dynamics/engine/loop.py:271–297`), and OP1 declares their
arrivals before delegating the call
(`src/populace_dynamics/open_population/harness.py:226–235`).

Base: `7e635bba`, branch `openpop-op1-harness-20261024`.

The build's sandbox could not write `.git`, so the main session committed
its tree in logical steps on this branch: `7d321aef` (the fast path, its
tests and the reducer exclusions), `a8c627a8` (the review fixes) and
`0d0c073c` (a production test at the registered 2100 horizon). The
measurement and this report followed in `3d69b1fc`. Review r2's three minor
findings are fixed in `1647a4ba`, and review r3's minor finding in the commit
after the master merge `daa1f58d` (§4). No history was rewritten.

`run_production(initial, modules,
ProductionRequest("tr2026_intermediate"), ...)` projects to 2100.
Shorter reads use `result.read_prefix(year)`. Production results carry
`kind="production"` and their scenario; gates carry `kind="gate"` and
`scenario=None` (`open_population/harness.py:301–328`,
`open_population/gates.py:76–88`). Production metadata stays open for OP6.

The scope remains accounting conformance and seam mechanics. The build
admits no demographic law or population forecast.

## 2. Resource measurements and stream cost

Measurements use invented rosters, emigration probability 0.02 and 75
projected years, 2026–2100. The script and the detailed results are
`op1_run_size.py` and `op1_run_size.json` beside this report. Each roster
size and emigration stream runs in its own worker process, one at a time.
Each measurement records the host load, wall time, peak RSS, retained
snapshot bytes and the leading cProfile costs. The main session ran it on
the committed code (`0d0c073c`), outside the build's sandbox. The JSON's
load triples, taken at each worker and projection boundary, give one-minute
load averages of 120.2–136.4 and five-minute averages of 86.6–96.5. The
build's own sandboxed run is not used: the sandbox ran the build's tests far
slower than this host (§3), and its timings distorted ratios as well.

Mortality uses `apply_mortality`, which draws person streams
(`engine/steps.py:125–131`); fertility uses `AsfrFertilityStep` with invented
rates and tagged person streams (`baselines/fertility.py:114–126`).
`advance_age` draws nothing (`engine/steps.py:142–148`). The marital step is
`no_marital_transitions`, required for nonzero emigration
(`open_population/exits.py:64–67`). The sealed loop retains its original
registry for every module and adapter draw.

All six runs reconciled 75 periods with zero count and weight residuals and
zero revaluations. For each roster size, the direct and registry runs give
the same projection hash, so the fast path changes no draw.

| Initial people | Mortality person-years | Emigrants | Profiled seconds, registry emigration | Profiled seconds, direct emigration | Peak RSS (MB), direct |
|---:|---:|---:|---:|---:|---:|
| 25 | 4,299 | 82 | 5.46 | 4.36 | 191.0 |
| 100 | 11,936 | 248 | 9.35 | 6.62 | 194.7 |
| 400 | 43,793 | 848 | 26.85 | 16.85 | 200.2 |

The RNG shares are shares of profiled projection time, measured by disjoint
wrappers (`op1_run_size.py:57`, `:208`). "Sequences" covers root, period and
module construction; "full setup" adds the leaf sequence and the generator.
The two overlap and must not be added.

| Initial people | Emigration stream | Sealed loop, sequences | Sealed loop, full setup | Emigration, full setup |
|---:|---|---:|---:|---:|
| 25 | Registry | 34.77% | 37.06% | 24.49% |
| 25 | Direct | 45.34% | 48.57% | 1.34% |
| 100 | Registry | 42.70% | 44.95% | 35.04% |
| 100 | Direct | 64.45% | 68.13% | 2.02% |
| 400 | Registry | 47.95% | 50.30% | 42.15% |
| 400 | Direct | 80.44% | 84.63% | 2.62% |

With emigration on the direct path, building the registry's sequences for
the sealed loop's own draws takes **45%, 64% and 80%** of profiled runtime
at 25, 100 and 400 initial people, and the share grows with the roster.
Here the loop draws 1.16–1.33 person-level registry streams per person-year
(a mortality person stream for everyone, and a fertility tagged child for
women of childbearing age), plus 600 module generators per run. Person-stream setup
alone takes 32%, 53% and 72%. Adapters that do more non-random work would
lower these shares, and adapters that draw more person streams would raise
them. cProfile inflates call-heavy code, so the shares are indicative; the
unprofiled timings below are the cleaner comparison.

The unprofiled microbenchmark interleaves five repetitions of 400
tagged-child draws (`op1_run_size.py:376`; the raw samples and loads are in
the JSON's `rng_microbenchmark`).

| Stream | Median µs per draw, 7 periods | Median µs per draw, 75 periods |
|---|---:|---:|
| Registry | 49.1 | 201.0 |
| Direct | 6.1 | 6.2 |

The registry's cost per draw grows about fourfold from 7 to 75 periods,
because `_period_sequence` spawns n_periods + 1 children on every call
(`engine/rng.py:61–67`). The direct path's cost does not depend on the
horizon. At 75 periods and about 1.2 registry draws per person-year, the
sealed loop's registry setup alone comes to roughly 240 seconds per million
person-years unprofiled, against about 7 seconds on the direct path.

Average profiled cost per mortality person-year is 0.38–1.01 ms with direct
emigration and 0.61–1.27 ms with registry emigration. It falls as the roster
grows, because fixed per-year costs spread out. The JSON marks a two-point
marginal fit as unusable under varying host load. These are engineering
extrapolations that include fixed and profiling overhead, not bounds.

The 150 annual-frame references share 76 three-column snapshots. Retained
snapshot bytes are **117,656**, **300,732** and **1,050,396** at 25, 100 and
400 people, against full-copy totals of **4,058,725**, **11,067,075** and
**40,445,014**. Peak RSS across the six workers ranges from 191.0 to
202.5 MB. The snapshot totals measure retained frame bytes; they do not
predict an equal fall in RSS.

```sh
.venv/bin/python docs/design/open_population_evidence/op1_run_size.py --sizes 25 100 400 --output docs/design/open_population_evidence/op1_run_size.json
```

Only `person_id`, `year` and `weight` are retained in `AnnualTransition`:
`engine/accounting.py:690–703` reads these three columns, and
`engine/accounting_history.py:152–159` calls that reader and reconstructs
those same columns. OP1 stores one snapshot per boundary and shares it
between adjacent transitions (`open_population/harness.py:221–247`, `:273`).
The ledger indexes declarations by year
(`open_population/events.py:68–79`, `:102–103`), and `close_period` reads
that year's tuple (`open_population/harness.py:242`), avoiding a scan of all
prior events.

The full Microcosm-sized measurement remains an **open OP1 item before
OP10a**, as design §8 requires. The open-population lane runs it locally,
under `heavy`, in a quiet window, on invented data; otherwise it waits for
OP10a. The small-run figures above are planning estimates, not a
demonstrated scaling law.

The fast-path invariant is: **at every valid stream address, the direct
stream equals `ProjectionRNGRegistry`**. `open_population/streams.py:117–133`
constructs the same entropy and spawn keys as `engine/rng.py:61–100` and
`:102–156`; its tagged period-zero cases preserve the separate root and
spawned-child convention. Tests compare entropy, spawn key, pool size,
eight state words and four draws across the specified exhaustive grid and
24 generated examples. The exact emigration test independently uses the
sealed registry, rather than the fast class.

A second invariant covers refusals: **for arguments of built-in and NumPy
types, wherever the registry returns or raises, the direct class does the
same, with the same stream or the same exception type and message**. The
direct class therefore repeats the registry's steps in its order, without
building the children:

1. the module (`engine/rng.py:73`), then the period interval (`:62–65`);
2. the root seed (`:66`). The draw seed is recomputed on every call, as the
   registry's is, so NumPy's overflow handling under `np.errstate` applies
   each time. The root built from it is kept per instance and rebuilt only
   when the seed changes, as a 0-d array draw mutated in place can make it
   (`open_population/streams.py:93–108`). A refused seed is never kept, so
   a non-integer draw fails at this step on every call, ahead of a
   malformed horizon or period. Each returned sequence gets its own copy of
   the root's entropy list, as the registry's fresh root gives it;
3. `spawn(n_periods + 1)` (`:67`). `_spawned_length` refuses a negative
   count with spawn's `ValueError`, then takes `len(range(count))`, which
   refuses a non-integer or a count past `ssize_t` with spawn's own message;
4. the list lookup (`:67`). `_spawned_position` indexes an empty list, so a
   non-index type or an index past `ssize_t` gets CPython's own message. It
   then wraps a negative position and checks it against the spawned length,
   as the list lookup does. The spawn key holds the Python `int` position,
   as the registry's does.

A tagged child at period zero repeats the tagged root, its
`spawn(child_index + 1)` and its lookup (`engine/rng.py:142–144`).

The one exception is a spawn count the registry cannot complete. `spawn`
returns a list of `count` children, so its time and memory grow with the
count. On this host `spawn(10**6)` took 2.45 s and reached a peak RSS of
412 MiB, against 0.26 s and 72 MiB for `spawn(10**5)`. At that rate a count
near 2^32 would need hours and terabytes, so the registry never finishes,
while the direct class returns at once. The engine's counts are
`n_periods + 1`, where `n_periods = end_year - start_year`
(`engine/loop.py:216`): 76 in the measured runs to 2100. The loop numbers
periods from 1 (`engine/loop.py:268–270`), so it never asks for a
period-zero tagged child.

User-defined argument types are outside the claim. NumPy's `spawn` adds the
count to an integer and converts the sum through `__int__`, and the direct
class calls a period's or child's `__index__` twice. So a count type without
`__int__` or `__radd__`, or a stateful `__index__`, can be served by one
class and refused by the other. The engine passes none of them: periods and
ordinals come from `enumerate` (`engine/loop.py:263–270`), and production
draws must be exact `int`s (`open_population/harness.py:86–87`).

`test_combined_and_malformed_refusals_match_registry` tries every
combination, for all six methods, of:
- 18 periods: −1, past the horizon, 0.0, 1.5, 7.0, `np.int64`, `True`,
  `None`, `np.float64`, `np.float32`, `np.bool_`, two `Decimal`s, a 0-d
  array and a one-element array, besides valid ones;
- three modules, one of them unknown;
- nine tail values, including −1, 1.5, `np.bool_`, a 0-d array and NumPy
  integers that wrap on `+ 1`;
- ten horizons: 7.0, 7.5, `np.float64`, counts past `ssize_t`, and NumPy
  integers whose count wraps negative or to zero.

`test_non_integer_draw_refusals_match_registry` adds four non-integer draws
and an `np.int64` one against malformed horizons and periods, and
`test_generated_malformed_addresses_match_registry` adds 80 Hypothesis
examples over all of these. Three more tests pin the root's state:
`test_returned_sequences_do_not_share_the_cached_root`,
`test_root_follows_the_draw_seed_as_the_registry_does` (a mutated 0-d draw,
and an overflowing `np.uint64` draw under `np.errstate(over="raise")`) and
`test_negative_position_wraps_as_the_list_lookup_does`. Every comparison
checks spawn-key element types as well as values.

Reviews r3 and r4 probed further. Their probes, rerun on the current code,
give:
- no difference in 2,352 addresses (negative floats, ±inf, NaN,
  `np.uint64`, 2^64, strings, `Fraction`, complex and more);
- no difference in 17,544 comparisons over integers of every NumPy width at
  their edges, `np.bool_`, a period equal to the horizon and draws up to
  2^200;
- no difference in 2,640 comparisons over other built-in, NumPy and pandas
  types;
- agreement with the registry on aliasing, a mutated draw and the
  `np.errstate` overflow;
- 29,880 valid-address identities and 4,556 period-zero tagged-child
  identities.

The 78 differences left are all user-defined types of the kinds named
above. On this host the direct path costs 6.6 µs per draw at period 5 and
horizon 75, against 6.2 µs at `3d69b1fc` and 212 µs on the registry (process
CPU time, seven interleaved repetitions of 2,000 draws; one run, not in
`op1_run_size.json`).

## 3. Tests, collection, style and scope

All tests and mutation checks ran in one process at a time, with modest
Hypothesis budgets and no xdist. The build ran its checks inside its
sandbox, so the main session reran them on the committed code. The timings
in this section are pytest's own reported wall times, not measurements in
`op1_run_size.json`. The build's sandboxed run of the required command
reported 231 passed in 660.26 s, with the 2100 test dropped; on this host
the command takes under 10 s.

The build dropped its production run to 2100 because its sandboxed pytest
run reported 62 s for it. On this host, `pytest --durations` reports
0.59 s, so
`test_registered_scenario_projects_to_its_horizon_on_inventions` keeps it
(`0d0c073c`): a three-person invented roster with emigration on projects to
TR2026's `LAST_YEAR`, and a 2030 prefix equals the run's leading slices.

The required command gives **302 passed and 1 strict xfail, with 2 existing
fixture warnings**, in 14 s by pytest's report (one-minute load 11). At
`0d0c073c` it gave 232 passed in about 8 s; review r2's refusal tests added
37, review r3's fix 30 and review r4's fix 3. It covers the self-contained
horizon test, the reversed-roster example, the gate metadata refusals and
every reducer identity, reachability and initializer check.

```sh
.venv/bin/python -m pytest -q tests/open_population tests/estimates/test_birth_evidence_artifact.py tests/test_entrant_schedule.py tests/test_entrant_domains.py tests/test_entrant_id_allocation.py
.venv/bin/python -m pytest --collect-only -q tests/open_population | tail -1
```

Collection gives **199 tests**, all classified as `unit` (seven modules,
including the original six). That is 139 more than the 60 reviewed at r1,
70 more than the 129 reviewed at r2, 33 more than the 166 reviewed at r3 and
3 more than the 196 reviewed at r4.

Black and Ruff pass over every touched Python file, and `git diff --check`
is clean.

```sh
.venv/bin/black --check -l 79 src/populace_dynamics/open_population tests/open_population scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py docs/design/open_population_evidence/op1_run_size.py
.venv/bin/ruff check src/populace_dynamics/open_population tests/open_population scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py docs/design/open_population_evidence/op1_run_size.py
git diff --check
git diff --stat 7e635bba
git diff --exit-code 7e635bba -- src/populace_dynamics/engine src/populace_dynamics/baselines src/populace_dynamics/cola_track_a src/populace_dynamics/track_b gates.yaml runs tests/tier_counts.json tests/README-tiers.md
```

The scope comparison over the sealed and shared paths is empty. The three
new files, `open_population/streams.py`, `tests/open_population/__init__.py`
and `tests/open_population/test_streams.py`, lie within the allowed scope.
The test modules, including the new stream module, classify as `unit` under
the repository's `_classify_test_module`. The shared tier inventories are
unchanged; their update waits for the coordinator's slot.

No sealed engine, baseline, Track A, Track B, gate contract, committed run
or shared tier file changed. The only changes outside OP1 sources, tests
and `docs/design/open_population_evidence/op1_*` add `streams.py` to
`POST_REVIEW_SOURCE_EXCLUSIONS` and its exact pin.

Closed-run equality means equality with the sealed loop run on the
canonical initialized slice, with the same scheduled frames and draw.
OP1 canonicalizes after initialization (`open_population/harness.py:190–193`),
matching the sealed loop's entrant-year sort (`engine/loop.py:284–286`).
The underlying two-mother ASFR/materializer gap remains a strict xfail:
`baselines/fertility.py:114–128` keeps mother row order and
`engine/steps.py:473–497` assigns child IDs and parents in that order.

The runtime gate closure test admits third-party helpers and refuses project
alignment modules. `pandas.core.computation.align` is a third-party helper
loaded at run time; it is outside the `populace_dynamics` namespace.

## 4. Review r1 and fixes

Paths below are relative to `src/populace_dynamics/` for source and
`tests/open_population/` for test names. The build's sandbox could not
commit, so the main session committed its tree (§1).

| Finding | Severity | Fix and test that pins it | Commit |
|---|---|---|---|
| 1 | Major | `open_population/harness.py:60–95` freezes the TR2026→2100 lookup, derives the read-only request end year and gives accurate field-type errors. Tests `test_registered_production_horizon_matches_baseline`, `test_production_horizon_is_bound_to_scenario`, `test_conflicting_production_end_years_cannot_be_constructed`, unknown-scenario/type tests and result-kind tests pin the boundary. | `a8c627a8`, `0d0c073c` |
| 2 | Major | `test_exact_emigration_stream` compares the ledger against the sealed registry; `test_emigration_marginal_and_non_degenerate` checks 4,000 invented people at q=.5/p=.25; `test_emigration_uniform_distinct_from_other_person_streams` checks mortality and ASFR independence. | `a8c627a8` |
| 3 | Major | `open_population/gates.py:28`, `:44–89` uses explicit keyword-only arguments and a frozen two-key metadata allow-list. `GateTargetRefused` rejects unlisted metadata before adapters run. `test_gate_refuses_unlisted_metadata_before_any_adapter` and `test_gate_allowed_metadata_reaches_advance_age` pin both sides. Request target keywords and runner unknown keywords are rejected by their explicit signatures. | `a8c627a8` |
| 4 | Minor | `test_independent_horizons_change_open_but_not_closed_shared_slices` runs the sealed loop on invented frames without git, exec or file reads; it cites the design evidence script as provenance. | `a8c627a8` |
| 5 | Minor | Stable canonical sorting follows initialization (`open_population/harness.py:190–193`). Closed-run comparisons use that canonical slice; `test_non_sorting_person_mortality_is_order_invariant` pins non-sorting mortality. The sealed-function xfail stays. | `a8c627a8` |
| 6 | Minor | `open_population/exits.py:77–83` makes `_ExitAdapter` harness-only; `_project` constructs it after compatibility validation. `test_package_exposes_no_public_exit_adapter` pins the public surface. | `a8c627a8` |
| 7 | Minor | Three-column snapshots, shared adjacent boundaries and year-indexed events reduce retained state and ledger scans. `test_annual_transitions_retain_only_accounting_columns` and `test_year_index_preserves_declarations_and_returns_a_snapshot` pin them. §2 records nonzero-emigration profiles, draw timings and the open full-size item. | `a8c627a8` |
| 8 | Minor | `test_running_gate_loads_no_project_alignment_module` executes a complete one-person gate in a fresh process and checks the loaded project namespace. | `a8c627a8` |
| 9 | Minor | Scheduled entrants join closed-run differential tests; six fixed slots have offsetting weight-swap tests, including marital mutation in place. Two explicit stock-flow examples pin q=.25/p=.35 with entrants; the property budget rises from 8 to 12. | `a8c627a8` |
| 10 | Minor | Source imports shared entry-kind constants, removes the duplicate allocator check and adds the requested docstrings. The schedule seam's exact-object validation test stays. A test package marker prevents top-level collisions. §1 cites revision 14 and below states the entry-year convention. | `a8c627a8` |
| 11 | Coordinator addition | `open_population/streams.py` directly constructs all required registry addresses, preserves period-zero tagged streams and matches refusals. `test_streams.py` covers the exhaustive grid, generated addresses and invalid addresses. Only emigration uses the fast class (`open_population/exits.py:145–161`). Both reducer exclusions include the new module. | `7d321aef`, `a8c627a8` |

The stream rechecks ran the actual three new tests against copied exit
modules. The live source stayed byte-identical, and test bindings were restored.

| Mutation | Recheck result |
|---|---|
| M03: mortality person stream reused | Killed: exact stream, marginal and independence tests fail (3/3) |
| M04: one shared emigration uniform | Killed: exact stream and marginal tests fail (2/3) |
| M05: fertility tagged stream reused | Killed: exact stream and independence tests fail (2/3) |
| M12: per-slot fixed-stock fence removed | Killed: all six offsetting weight-swap tests fail with DID NOT RAISE AccountingIdentityError (6/6); live source stayed byte-identical |

M20's redundant harness allocator check was deliberately removed; the seam's
check remains pinned by `test_validator_receives_the_exact_returned_metadata`
(the test that killed M21 in review r1). No new M21 mutation run is claimed.

### Review r2

Review r2 (delta review at `3d69b1fc`) approved with three minor findings.

| Finding | Fix and test that pins it |
|---|---|
| 1: the report's load range and unsupported timing figures | §2 now gives the JSON's load ranges. §3 labels each timing as a pytest wall time, outside the JSON, and gives the host figures from a rerun. |
| 2: refusal precedence lacked a test; mutant N10 survived | `test_combined_and_malformed_refusals_match_registry` and `test_generated_malformed_addresses_match_registry` compare type and message at combined invalid addresses (§2). N10 now fails them. |
| 3: a non-integer horizon was accepted where the registry refuses it | `1647a4ba` added integer checks for the registry's spawn and list lookup, in its order, and built the period-zero tagged root before its spawn count. Review r3's fix replaced those checks with exact mirrors (below). Float and `np.float64` horizons, float periods and float children are in the refusal grid. |

| Mutation of the r2 fix | Result |
|---|---|
| Pre-fix `streams.py` (`3d69b1fc`) | Killed by the refusal grid |
| N10: module and period checks reversed | Killed |
| Spawn-count check removed | Killed |
| List-index check removed | Killed |
| Spawn-count and list-index checks swapped | Killed |
| Period-zero child spawn-count check removed | Killed |

### Review r3

Review r3 (Opus 5.5 delta check at `daa1f58d`, which merged master `4e20c6e4`) approved. Its 16 mutants of the r2 fix were killed except one equivalent on every input the engine passes. It had one minor finding.

| Finding | Fix and test that pins it |
|---|---|
| 1: the refusal invariant was stated too broadly. 288 of 2,352 exotic addresses differed: NumPy float, bool and `Decimal` periods got a differently spelled message; a 0-d integer array period was served by the registry and refused here; a non-integer draw failed at a later step; a period-zero `np.True_` child failed differently; and spawn counts of 2^64 or more were refused only by the registry | `_spawned_length`, `_spawned_position` and the cached root (§2) repeat the registry's steps exactly. The report states the invariant wherever the registry returns or raises, and names the one exception, counts it cannot complete. The refusal grid adds every input class above, NumPy integers that wrap, counts past `ssize_t` and malformed draws. The probe's 2,352 addresses now agree. |

| Mutation of the r3 fix | Result |
|---|---|
| `streams.py` at `1647a4ba` | Killed |
| Root built after the spawn and lookup | Killed |
| Negative-count check removed | Killed |
| Spawn length by `operator.index` instead of `len(range(...))` | Killed |
| Length bound check removed | Killed by the horizon `np.uint64(2**64 - 1)`, whose count wraps to zero |
| `ssize_t` re-raise removed | Killed |
| Spawn key holds the raw period | Killed |
| Period-zero child key holds the raw child | Killed |
| Period-zero child lookup skipped | Killed |
| Lookup by `operator.index`, no list probe | Killed |
| Period-zero spawn before its tagged root | Killed |
| Review r3's A12: spawn count `n_periods` instead of `n_periods + 1` | Killed (it survived r3) |
| Root rebuilt on every call instead of cached | Survives as intended: it changes cost only |

### Review r4

Review r4 (Opus 5.5 delta check at `dee1e1b7`) approved, with three minor findings and a nit. It also confirmed that the merge tree still equals `git merge-tree 1647a4ba 4e20c6e4`, and that the counts changed only by the grid's 30 new unit tests.

| Finding | Fix and test that pins it |
|---|---|
| 1: the invariant still failed for user-defined types (150 of 806 such comparisons), and the cached root missed a mutated 0-d draw and a later `np.errstate(over="raise")` | Negative positions wrap as the list lookup does. The draw seed is recomputed per call, and the root is rebuilt when it changes. The invariant is scoped to built-in and NumPy types, and the paragraph above names the user-defined cases left. Pinned by `test_negative_position_wraps_as_the_list_lookup_does` and `test_root_follows_the_draw_seed_as_the_registry_does`. |
| 2: every returned sequence shared the cached root's entropy list | Each call passes a fresh copy. Pinned by `test_returned_sequences_do_not_share_the_cached_root`. |
| 3: no test pinned spawn-key element types (r4's mutant B17 survived) | Both identity helpers compare element types. B17 now fails 13 tests. |
| Nit: two counts in this report | The `1647a4ba` mutant row no longer cites a count. The draw test is described as four non-integer draws and an `np.int64` one. |

| Mutation of the r4 fix (stream and exit tests) | Result |
|---|---|
| `streams.py` at `dee1e1b7` | Killed (3 tests) |
| Negative wrap removed | Killed |
| Entropy list shared, not copied | Killed |
| r4's B17: `isinstance` fast path | Killed (13) |
| Root never rebuilt | Killed |
| Seed not recomputed per call | Killed |
| Root after the spawn and lookup | Killed (7) |
| Spawn key holds the raw period | Killed (14) |
| Negative-count check removed | Killed (15) |
| Length bound removed | Killed (6) |
| `ssize_t` re-raise removed | Killed (10) |
| r3's A12: spawn count `n_periods` | Killed (54) |
| Period-zero child lookup skipped | Killed (10) |
| Root rebuilt on every call, no cache | Survives as intended: it changes cost only |

## 5. Remaining work and restricted-files statement

Scheduled entrants can emigrate in their entry year by default: the seam appends them
before the exit adapter (`engine/loop.py:271–297`). OP0.1 and OP3's timing
bridge own that convention (design §5.4, OP4). A supplied hazard can return
0 for rows where `entry_year == context.year` to disable entry-year
emigration; production schedules still need OP3's timing bridge.

OP4 must supply exit-aware relational updates before a non-null hazard can
be composed with another marital adapter (`open_population/exits.py:64–72`).
Full-size resource validation remains due before OP10a. Host variability
prevented a reliable marginal-runtime estimate; §2 retains raw fits and a
labelled engineering extrapolation. No other implementation work is deferred.

Read `RESTRICTED-FILES.md` in full before source work. Opened nothing it
restricts, no other session's transcript or scratchpad and no other Subfleet
job folder. The expressly authorized coordinator RNG-check folder and OP1
review/scratch folder were the only external evidence folders used. The
three named NCHS source files and every OP0.1 review folder stayed unopened.
All tests, probes, mutation checks and measurements use invented inputs;
no microdata or external statistical table was read and no real-data
statistic was computed. Every delegated agent reports the same boundary.
