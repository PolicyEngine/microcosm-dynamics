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

Base: `7e635bba`, branch `openpop-op1-harness-20261024`. `daa1f58d` merged
master `4e20c6e4` into the branch, and `fa862935` merged master `d8302233`
for the coordinator's tier slot.

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
registry for every module and adapter draw. (This section measures OP1 as
merged in #566. Since the injection follow-up, §6, the adapters' person and
tagged draws come from `DirectRNGStreams` by default; the script now
compares three stream modes. §6 reports its host run, kept in
`op1_run_size_injection.json`; `op1_run_size.json` keeps this section's
run.)

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

With emigration on the direct path, building the registry's sequences for the
sealed loop's own draws takes **45%, 64% and 80%** of profiled runtime at 25,
100 and 400 initial people, and the share grows with the roster. Here the loop
draws 1.16–1.33 person-level registry streams per person-year (a mortality
person stream for everyone, and a fertility tagged child for women of
childbearing age), plus 600 module generators per run. Person-stream setup
alone takes 32%, 53% and 72%. Adapters that do more non-random work would lower
these shares, and adapters that draw more person streams would raise them.
cProfile inflates call-heavy code, so the shares are indicative; the unprofiled
timings below are the cleaner comparison.

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

The fast-path invariant is: **at every valid stream address, the direct stream
equals `ProjectionRNGRegistry`**. `open_population/streams.py:122–138`
constructs the same entropy and spawn keys as `engine/rng.py:61–100` and
`:102–156`; its tagged period-zero cases preserve the separate root and
spawned-child convention. Tests compare entropy and spawn key (values and
element types), pool size, eight state words and four draws across the
specified exhaustive grid and 24 generated examples. The exact emigration test
independently uses the sealed registry, rather than the fast class.

A second invariant covers refusals: **for arguments of built-in and NumPy
types, wherever the registry returns or raises, the direct class does the
same, with the same stream or the same exception type and message**. The
direct class therefore repeats the registry's steps in its order, without
building the children:

1. the module (`engine/rng.py:73`), then the period interval (`:62–65`);
2. the root seed (`:66`). The draw seed is recomputed on every call, as the
   registry's is, so NumPy's overflow handling under `np.errstate` applies each
   time. Only an exact `int` seed's root is kept, and it is rebuilt when the
   seed changes (`open_population/streams.py:93–113`). Any other seed's root is
   rebuilt on every call, as the registry's is, so a draw changed in place to
   an equal value of another type gets the registry's outcome. A refused seed
   is never kept, so a non-integer draw, or a negative `int` seed from a draw
   changed after construction, fails at this step on every call, ahead of a
   malformed horizon or period. Each returned sequence gets its own copy of the
   root's entropy list, as the registry's fresh root gives it;
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
`__int__` or `__radd__`, or a stateful `__index__`, can be served by one class
and refused by the other, or served a different stream by each. The engine
passes none of them: periods and ordinals come from `enumerate`
(`engine/loop.py:263–270`), and production draws must be exact `int`s
(`open_population/harness.py:86–87`).

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
examples over all of these. Nine tests pin the root's state:
- `test_returned_sequences_do_not_share_the_cached_root` and
  `test_returned_generators_do_not_share_the_cached_root`: every method,
  including the tagged child emigration draws from and the period-zero
  tagged cases, hands out its own entropy list;
- `test_root_follows_the_draw_seed_as_the_registry_does`: 0-d draws of
  NumPy and object type mutated in place, including to a seed whose hash
  equals the cached one's, and an overflowing `np.uint64` draw under
  `np.errstate(over="raise")`;
- `test_cached_root_follows_exact_int_seeds_compared_exactly` and
  `test_cached_root_follows_generated_exact_int_walks`: exact `int` draws
  past `int64`, past float precision and past float range, seeds that match
  an earlier one in their low 64 or 1,100 bits, and a draw whose seed is the
  cached seed's negative, through every method. The second walks generated
  draws by fresh values, one-bit flips, one-bit steps and negations;
- `test_root_ignores_an_equal_seed_of_another_type` and
  `test_root_ignores_an_equal_seed_set_on_the_frozen_field`: a draw changed
  in place to an equal float, `Fraction`, `Decimal`, complex, NumPy
  integer, `np.True_` or `np.ma.masked`, and a field replaced through
  `object.__setattr__` with an equal float, `Decimal`, NumPy integer,
  `int` or `True`;
- `test_refused_seed_is_refused_on_every_call` and
  `test_refused_int_seed_is_refused_on_every_call`: a non-integer draw,
  whose seed never reaches the cache, and a negative `int` seed, the one
  refused seed that does.

`test_negative_position_wraps_as_the_list_lookup_does` wraps positions
inside and below the spawned range. Every comparison checks the element
types of the entropy and the spawn key as well as their values.

Reviews r3, r4 and r5 probed further. Their probes, rerun on the current
code, give:
- no difference in 2,352 addresses (negative floats, ±inf, NaN,
  `np.uint64`, 2^64, strings, `Fraction`, complex and more);
- no difference in 17,544 comparisons over integers of every NumPy width at
  their edges, `np.bool_`, a period equal to the horizon and draws up to
  2^200;
- no difference in 2,640 comparisons over other built-in, NumPy and pandas
  types;
- no difference in 1,440 comparisons of draws changed between calls on one
  instance, including equal values of other types, NaN, and `np.errstate`
  toggled between calls;
- no difference for a 0-d draw whose dtype is reassigned, or one changed to
  `pd.NA` or `np.ma.masked`, and none in 968 comparisons of negative
  indices of every NumPy width;
- agreement with the registry on aliasing, a mutated draw and the
  `np.errstate` overflow. Returned entropy lists are distinct, and after
  320 calls with every returned list edited the cached root is unchanged;
- 29,880 valid-address identities, 12,320 three-way identities with
  `dee1e1b7` (including `bit_generator.state`) and 4,556 period-zero
  tagged-child identities.

The 78 differences left are all user-defined types of the kinds named
above. Equality, hashing, `repr`, `dataclasses.replace` and pickling at
protocols 0 to 5 behave as before; a used instance's pickle carries its
cached root and unpickles to the same streams.

On this host the direct path costs 8.3 µs per draw at period 5 and horizon
75, against 8.0 µs at `3d69b1fc`, 8.3 µs at `6361b4c0` and 265 µs on the
registry (process CPU time, seven interleaved repetitions of 2,000 draws;
one run at a one-minute load of 176, not in `op1_run_size.json`). At a load
of 10 to 20 the review r4 fix measured 6.6, 6.2 and 212 µs. The ratios
agree: the direct path costs 1.04 to 1.07 times `3d69b1fc`'s, and the
registry about 32 times the direct path.

## 3. Tests, collection, style and scope

All tests and mutation checks ran in one process at a time, with modest
Hypothesis budgets and no xdist. The build ran its checks inside its
sandbox, so the main session reran them on the committed code. The timings
in this section are pytest's own reported wall times, not measurements in
`op1_run_size.json`. The build's sandboxed run of the required command
reported 231 passed in 660.26 s, with the 2100 test dropped. On this host,
runs by the author and reviews r8 to r10 took 8 to 20 s, varying with host
load.

The build dropped its production run to 2100 because its sandboxed pytest
run reported 62 s for it. On this host, `pytest --durations` reports
0.59 s, so
`test_registered_scenario_projects_to_its_horizon_on_inventions` keeps it
(`0d0c073c`): a three-person invented roster with emigration on projects to
TR2026's `LAST_YEAR`, and a 2030 prefix equals the run's leading slices.

The required command gives **341 passed and 1 strict xfail, with 2 existing
fixture warnings**: OP1's 334, and the 7 OP0.1 record tests that master
keeps in `tests/open_population/test_op0_1_records.py`, which the tier-slot
merge `fa862935` brought in. Its time varies with host load: runs by the
author and reviews r8 to r10 took 8 to 20 s by pytest's report, r10's
20.06 s at a one-minute load of 98. At
`0d0c073c` OP1's part gave 232 passed in about 8 s; review r2's refusal tests
added 37, review r3's fix 30, review r4's fix 3, review r5's fix 20, review
r6's fix 10, review r7's fix 1 and review r9's fix 1. It covers the
self-contained horizon test, the reversed-roster example, the gate metadata
refusals and every reducer identity, reachability and initializer check.

```sh
.venv/bin/python -m pytest -q tests/open_population tests/estimates/test_birth_evidence_artifact.py tests/test_entrant_schedule.py tests/test_entrant_domains.py tests/test_entrant_id_allocation.py
.venv/bin/python -m pytest --collect-only -q tests/open_population --ignore=tests/open_population/test_op0_1_records.py | tail -1
```

OP1's collection gives **231 tests**, all classified as `unit` (seven
modules, including the original six); without the `--ignore`, the folder
gives 238. That is 171 more than the 60 reviewed at r1,
102 more than the 129 reviewed at r2, 65 more than the 166 reviewed at r3,
35 more than the 196 reviewed at r4, 32 more than the 199 reviewed at r5,
12 more than the 219 reviewed at r6, 2 more than the 229 reviewed at r7 and
1 more than the 230 reviewed at r8 and r9.

Black and Ruff pass over every touched Python file, and `git diff --check`
is clean.

```sh
.venv/bin/black --check -l 79 src/populace_dynamics/open_population tests/open_population scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py docs/design/open_population_evidence/op1_run_size.py
.venv/bin/ruff check src/populace_dynamics/open_population tests/open_population scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py docs/design/open_population_evidence/op1_run_size.py
git diff --check
git diff --stat d8302233
git diff --quiet d8302233 -- src/populace_dynamics/engine src/populace_dynamics/baselines src/populace_dynamics/cola_track_a src/populace_dynamics/track_b gates.yaml runs
git diff d8302233 -- tests/tier_counts.json tests/README-tiers.md
```

Against master `d8302233`, merged at `fa862935`, the sealed paths are
unchanged: `git diff --quiet` exits 0. It prints nothing whether or not a
file differs, so its exit status is the check. The shared tier files
change only by the recount below.
Before review r9's fix these commands named `7e635bba`, the base before the
first master merge, against which they show master's own changes; the r9
fix named master `4e20c6e4`, and the tier-slot recount names `d8302233`. The
three new files, `open_population/streams.py`,
`tests/open_population/__init__.py` and
`tests/open_population/test_streams.py`, lie within the allowed scope.
The test modules, including the new stream module, classify as `unit` under
the repository's `_classify_test_module`.

The tier-slot commit recounts the shared tier inventories without
collecting the whole repository. Against `d8302233`, the only test modules
that differ are OP1's seven new modules with their `__init__.py`, and
`tests/estimates/test_birth_evidence_artifact.py`, whose only change adds
OP1's nine module paths to a tuple. Collected tier by tier, OP1's modules
give 231 `unit` tests and none in any other tier. The changed module gives
13 `artifact` tests at master's version and at the merge, and master's
`tests/open_population/test_op0_1_records.py` collects 7 with and without
OP1's `__init__.py`. So `tests/tier_counts.json` and `tests/README-tiers.md`
move `unit` from 18,549 to 18,780 and the total from 25,119 to 25,350. CI's
tier-policy test, which collects the whole suite, checks them.

No sealed engine, baseline, Track A, Track B, gate contract or committed
run changed, and the shared tier files change only by that recount. The
only other changes outside OP1 sources, tests and
`docs/design/open_population_evidence/op1_*` add OP1's nine modules,
`streams.py` among them, to `POST_REVIEW_SOURCE_EXCLUSIONS` and its exact
pin.

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

The stream rechecks ran the actual three new tests against copied exit modules.
The live source stayed byte-identical, and test bindings were restored.

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

Review r4 (Opus 5.5 delta check at `dee1e1b7`) approved, with three minor findings and a nit. It also confirmed that the merge tree still equals `git merge-tree 1647a4ba 4e20c6e4`, and that the counts changed only by 30 new unit tests: 24 in the refusal grid and 6 in the draw test.

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

### Review r5

Review r5 (Opus 5.5 delta check at `6361b4c0`) approved, with three minor findings and a nit. It also confirmed the coordinator's four checks:
- the sealed and shared paths are unchanged from `4e20c6e4`;
- 12,320 three-way identities hold across the registry, `dee1e1b7` and `6361b4c0`;
- the merge tree still equals `git merge-tree 1647a4ba 4e20c6e4`;
- the counts changed only by the three new tests.

| Finding | Fix and test that pins it |
|---|---|
| 1: the cache compared seeds by value. A draw changed in place to an equal value of another type (`3.0`, `Decimal(3)`, `np.int64(3)`, `np.ma.masked`, or a 0-d array whose dtype is reassigned) was served from the cached `int` root, where the registry refuses it or types its entropy differently: 240 of 1,440 comparisons | Only an exact `int` seed's root is kept, and any other seed's root is built on every call. Both identity helpers compare entropy element types. Pinned by `test_root_ignores_an_equal_seed_of_another_type`, which `6361b4c0`'s code fails in all 10 of its cases. |
| 2: the entropy-copy test covered `seed_sequence` only, so r5's mutants C12 and C13 survived | `test_returned_generators_do_not_share_the_cached_root` pins every method, including the period-zero tagged cases. |
| 3: "a refused seed is never kept" and wraps below `-length` were unpinned (C2, C18 and C19 survived), and the wrap test's tagged-child case never reached the wrap | `test_refused_seed_is_refused_on_every_call` pins a non-integer draw and kills C2 without the `int` check. The wrap test now tries −1, −8, −9 and −20, and its tagged-child case is labelled as the child check's refusal. This row first said C2 itself was now equivalent. Review r6 showed that was wrong: a negative `int` seed is refused and still reaches the cache (see review r6). |
| Nit: two wordings | The user-defined paragraph adds "or served a different stream by each", and the r4 paragraph splits its 30 tests into 24 and 6. |

| Mutation of the r5 fix (stream and exit tests, 153) | Result |
|---|---|
| `streams.py` at `6361b4c0`; at `dee1e1b7` | Killed (10; 18) |
| `int` check dropped; `int` check returns the cached root | Killed (10; 9) |
| `int` check dropped and the refused seed cached | Killed (13, 3 of them by the refused-seed test) |
| Root never rebuilt; cache keyed on the draw object; seed not recomputed; old root returned | Killed (1; 1; 10; 1) |
| Entropy shared; shared for tailed streams; shared in the tagged child only; entropy as a tuple | Killed (6; 4; 1; 22) |
| Wrap dropped; bound check before the wrap; wrap without the lower bound; wrap at `<= 0`; wrap by `length - 1`; no wrap on the probe path | Killed (1; 1; 1; 44; 1; 1) |
| r4's B17; key holds the raw period; root after the lookup; period-zero tagged child shares the cached root | Killed (12 or 13; 13 or 14, as Hypothesis draws; 6 or 7; 1) |
| Negative-count check removed; length bound removed; `ssize_t` re-raise removed; r3's A12; period-zero lookup skipped | Killed (15 or 16; 7 or 8; 10; 54 or 55; 10 or 11) |
| No cache, or seeds compared with `is not` | Survive as intended: they change cost only |
| `not cached[0] == seed`; entropy rebuilt from the seed; default pool size (always 4); wrap by modulo | Survive: equivalent |
| A refused seed cached | Survived. This row first called it equivalent, which was wrong: a negative `int` seed reaches the cache (review r6). It is now killed |
| `isinstance(seed, int)` for the exact check | Survives: equivalent, since `5200 + True` is an `int` and no built-in or NumPy seed is an `int` subclass |
| A typed cache key without the `int` check | Survives: r5's alternative fix |

### Review r6

Review r6 (Opus 5.5 delta check at `3fda5862`) approved, with two minor findings and a nit, and found the code correct. It confirmed the coordinator's four checks and 22,176 four-way identities across the registry, `dee1e1b7`, `6361b4c0` and `3fda5862`. It found no difference in 472,392 comparisons of draws whose type changes in every order, against 35,910 at `6361b4c0`.

| Finding | Fix and test that pins it |
|---|---|
| 1: this report called mutant C2, a refused seed kept in the cache, equivalent "since a refused seed is never an `int`". That was wrong. A draw changed after construction can make the seed a negative `int`, which NumPy refuses and which reaches the cache. C2 then raises `AttributeError` on later calls where the registry raises `ValueError`, and no test caught it | `test_refused_int_seed_is_refused_on_every_call` changes a draw to −5201 or −2^70, as a 0-d array's element or through `object.__setattr__`, and compares two rounds of calls to every method. It kills C2 and r6's M9. The r5 rows above are corrected. |
| 2: the equal-seed fix was pinned only for a 0-d array changed in place, not for a field replaced through `object.__setattr__`. r6's mutant M13 (`type(seed) is not type(self.draw_index)`) passed every test | `test_root_ignores_an_equal_seed_set_on_the_frozen_field` (6 cases). `6361b4c0`'s code fails 5 of them; the sixth, `True` after 1, gives an equal exact `int` seed. It kills M13. |
| Nit: four prose lines not re-wrapped, and two kill counts that depend on Hypothesis given as single numbers | Those paragraphs and three older over-long ones are re-wrapped, and the r5 table gives "15 or 16" and "12 or 13". |

r6 also showed that a cache keyed by the seed's hash (its M16) passed every test, because seeds 2^61 − 1 apart share a hash. `test_root_follows_the_draw_seed_as_the_registry_does` now moves a draw by 2^61 − 1, which kills it. `streams.py` is unchanged from `3fda5862`, so every stream, probe and cost figure above still holds.

| Mutation (r6's harness; stream and exit tests, 163) | Result |
|---|---|
| `streams.py` at `6361b4c0`; at `dee1e1b7` | Killed (15; 27) |
| r6's four non-equivalent survivors: a refused seed cached (C2); only a negative `int` cached as refused (M9); the check against the draw's type (M13); a cache keyed by hash (M16) | Killed (4; 4; 5; 1) |
| `int` check dropped; check returns the cached root; check dropped and the refused seed cached | Killed (15; 13; 22) |
| NumPy integers also cached; non-`int` seeds also stored; `int(seed)` in the bypass; check only before the first cache; only floats bypass; check after the cache hit; only `bool` bypasses; entropy coerced to `int`; an `int` seed's root typed `np.int64` | Killed (6; 2; 24; 13; 11; 12; 15; 11 or 12; 48) |
| Root never rebuilt; keyed on the draw object; seed not recomputed; old root returned | Killed (5; 3; 18; 1) |
| Entropy shared; shared for tailed streams; shared in the tagged child only; entropy as a tuple | Killed (6; 4; 1; 22) |
| Wrap dropped; bound check before the wrap; wrap without the lower bound; wrap at `<= 0`; wrap by `length - 1`; no wrap on the probe path | Killed (1; 1; 1; 44; 1; 1) |
| r4's B17; key holds the raw period; root after the lookup; period-zero tagged child shares the cached root | Killed (12 or 13; 13 or 14; 6 or 7; 1) |
| Negative-count check removed; length bound removed; `ssize_t` re-raise removed; r3's A12; period-zero lookup skipped | Killed (15 or 16; 7 or 8; 10; 54 or 55; 10 or 11) |
| No cache; seeds compared with `is not`; a non-`int` seed clears the cache | Survive as intended: they change cost only |
| `not ==`; key compared by subtraction; default pool size; wrap by modulo; a negative `int` also bypasses; `isinstance` for the exact check; a typed key without the `int` check | Survive: equivalent, as r6 found with its probes |
| Entropy rebuilt from the seed | Survives: equivalent for streams and refusals, as r6 found; it emits a second overflow warning under `np.errstate(over="warn")` |

### Review r7

Review r7 (Opus 5.5 delta check at `3cd74630`) approved, with one minor finding and two nits, and found the code correct. It confirmed the coordinator's four checks and 22,176 four-way identities across the registry, `dee1e1b7`, `6361b4c0` and `3cd74630`. It reproduced every count in the r6 table except two that depend on Hypothesis, and tried 32 new mutants: 15 were killed, 13 survived as equivalents, and 4 survived without being equivalent.

| Finding | Fix and test that pins it |
|---|---|
| 1: no test used a valid exact-`int` draw past `int64`, or two exact-`int` seeds equal as floats, though those are the seeds the cache keeps. The production harness accepts any non-negative exact `int` draw, 2^63 included. The code was correct on all of these inputs, but four contrived mutants passed every test: the cached root built from `int(np.int64(seed))` for non-negative seeds (S8), and the cached seed compared as a float (R4), by absolute value (R2) or as a string (R5) | `test_cached_root_follows_exact_int_seeds_compared_exactly`, r7's verified candidate, changes an object draw to 0, 2^53, 2^53 + 1, 2^64, 2^64 + 1, 0 and −10400 and compares every method with the registry. It kills S8, R4 and R2. R5 differs from the registry only for a seed past CPython's 4,300-digit limit on converting an `int` to a string, which is a process-wide setting, so it stays unpinned. |
| Nit: two kill counts that depend on Hypothesis given as single numbers | The r6 table gives "11 or 12" for entropy coerced to `int`, and both tables give "6 or 7" for the root after the lookup. |
| Nit: the r6 nit row said four older over-long lines were re-wrapped | It now says three. The fourth, a one-line bullet in the review r5 section, follows that section's one line per paragraph. |

| Mutation (r7's harnesses; stream and exit tests, 164) | Result |
|---|---|
| `streams.py` at `6361b4c0`; at `dee1e1b7` | Killed (15; 28). The new test passes at `6361b4c0` and fails at `dee1e1b7` |
| r7's three non-equivalent survivors that the test targets: root from `int64` words for non-negative seeds (S8); key as a float (R4); key by absolute value (R2) | Killed (1; 1; 1) |
| Key as a string (R5) | Survives: it differs from the registry only past the 4,300-digit limit |
| r7's 15 killed mutants | Still killed. Seven gain the new test as a kill: `<` for `!=` (R1, 6), the key reduced mod 2^32 (R7, 3) or cast to `np.int64` (R8, 3), `setdefault` for the store (S4, 2), only small negative seeds cached as refused (S6, 3), the root from `int64` words for every seed (S7, 3), and the entropy as an array (E3, 57). The other eight keep r7's counts |
| r7's 13 equivalent survivors: the key by xor; the root stored only once, stored on the class, or popped on read; the exact check made on the draw's type, by `isinstance` without `bool`, only below 2^63, or by the type's name; the entropy sliced, deep-copied or rebuilt from the seed; the period-zero tagged entropy copied; the period-zero tagged call also building the root | Survive: equivalent for streams and refusals, as r7 found with its probes |
| r6's 50 mutants (r6's harness): 39 killed and 11 equivalent survivors | The same 39 are killed and the same 11 survive. Eight gain the new test as a kill: C2 and M9 (5 each), the root never rebuilt (C3, 6), the cache keyed on the draw object (C4, 4), the seed not recomputed (C5, 19), the old root returned (C6, 2), the check dropped with the refused seed cached (N3, 23) and an `int` seed's root typed `np.int64` (M12, 49). The Hypothesis-dependent counts stay within the ranges above |
| The new test run alone | Fails at `dee1e1b7` and under 18 of the 82 mutants, and passes at `6361b4c0` |

### Review r8

Review r8 (Opus 5.5 delta check at `42be3231`) approved, with one minor finding, and found the code correct. It confirmed the coordinator's four checks and 22,176 four-way identities across the registry, `dee1e1b7`, `6361b4c0` and `42be3231`. It closed r7's finding and both nits, and reproduced every count and kill count in the review r7 section and the two Hypothesis ranges. It tried 18 new mutants: 11 were killed, 2 survived as equivalents, and 5 survived without being equivalent.

| Finding | Fix and test that pins it |
|---|---|
| 1: the new test never moved between two seeds that agree in their low 64 bits, and never went past 2^64 + 5201. The code was correct on all of these inputs, but five contrived mutants passed every test: the cached seed compared by its sign and low 64 bits (K6) or modulo 2^72 (K1), stored as a float (S9) or, when large, reduced modulo 2^64 (S14), and the root built from the seed modulo 2^128 for non-negative seeds (S13) | r8's verified fix adds a draw of 2^1100 before the second 0. Seeds 2^1100 + 5200 and 5200 agree in their low 1,100 bits, and 2^1100 is past float range. It kills all five and loses no kill. It pins a key or root that goes wrong on any single seed up to 2^1100 + 5200. A key that compares two large seeds loosely, or drops a large seed's sign, could still pass; review r9 found such keys (see below). |

| Mutation (r6's, r7's and r8's harnesses; stream and exit tests, 164) | Result |
|---|---|
| r8's five non-equivalent survivors: K6; K1; S9; S14; S13 | Killed (1 each) |
| r8's 11 killed mutants: the key without its low bit (K2), by bit length (K3), not compared past 2^63 (K4), by `math.isclose` (K5), only by bit length past 2^64 (K7) or by its low 32 bits and bits from 64 up (K8); a memo keyed by hash (S11); the root from the seed modulo 2^64 for non-negative seeds (S12); the previous seed stored with the new root (S15); the cached root reused when the seed moves by 1 past 2^53 (S16); large seeds reusing a large cached root (X9) | Killed (1; 2; 1; 1; 1; 1; 1; 1; 2; 1; 1) |
| r8's equivalent survivors: an unbounded memo per seed (S10); seeds past 2^64 bypass the cache (X8) | Survive: they change memory or cost only, as r8 found with its probes |
| r7's 32 mutants and r6's 50 | Every verdict above holds. The key masked to 64 bits (R3) gains the new test as a kill (3). R5, r7's 13 equivalents and r6's 11 still survive, the `6361b4c0` and `dee1e1b7` files still fail 15 and 28 tests, and the Hypothesis-dependent counts stay within their ranges |

### Review r9

Review r9 (Opus 5.5 delta check at `5f276453`; its review names its model) approved, with one minor finding and four nits, and found the code correct. It confirmed the coordinator's four checks and 22,176 four-way identities across the registry, `dee1e1b7`, `6361b4c0` and `5f276453`, closed r8's finding, and reproduced every author mutant output. It tried 12 new mutants: 4 were killed, 6 survived without being equivalent, and 2 differed from the registry only past 2^1101, beyond the committed draws.

| Finding | Fix and test that pins it |
|---|---|
| 1: lossy cache keys that go wrong for seeds below 2^1100 still passed every test. Six contrived mutants survived: the cached seed compared modulo 3 (K9) or modulo 2^89 − 1 (K10), by its low 64 bits when both seeds pass 2^64 (K11), by bit length and low 64 bits (K12), by bit length when a seed passes 2^1024 (K13), and without its sign when the seed passes 2^64 (G1). No finite list of draws can rule out every lossy key | Both of r9's verified options. The draws 2^64 and 2^64 + 1 swap places, so the walk moves from seed 2^64 + 5200 to 2^1100 + 5200: they agree in their low 64 bits and differ by a multiple of 3. And `test_cached_root_follows_generated_exact_int_walks`, r9's candidate unchanged, is a Hypothesis property test of the invariant itself: any walk of an exact `int` draw, by fresh values, one-bit flips, one-bit steps and negations, gets the registry's streams. Together they kill five of the six, K9 and K11 by both tests and K12, K13 and G1 by the property test alone, with no kill lost across 114 mutants. K10 survives (below). |
| Nit: the r8 finding said "agree in their low bits", which the step from 0 to 2^53 already did | It says low 64 bits. |
| Nit: S12 and S13 were described without "for non-negative seeds"; as worded, they fail five tests | Both rows say it. |
| Nit: "raises that size from 2^64 to 2^1100" claimed more than the draw pins | The r8 row says what the draw pins and what it leaves. |
| Nit: the timing range was the author's unrecorded observation, and one of r9's runs fell outside it | The required-command paragraph gives the range over the author's and reviews' runs and says it varies with host load. §3's opening paragraph, which said "under 10 s", gives the same range. |

Rerunning §3's commands for this fix, the author found that its scope commands still named `7e635bba`, the base before the master merge `daa1f58d`. Against it the sealed and shared paths show master's own changes to `track_b/holdout_registry.py` and the two tier files. The fix named the merge in §1 and pointed §3's commands at master `4e20c6e4`, which reviews r3 to r9 used for the coordinator's sealed-path check; against it they were empty. The tier-slot merge below moves them to master `d8302233`.

| Mutation (r6's, r7's, r8's and r9's harnesses; stream and exit tests, 165) | Result |
|---|---|
| r9's K9 and K11 | Killed (2 each): the reordered draws and the property test |
| r9's K12, K13 and G1 | Killed (1 each), by the property test alone |
| r9's K10, the key modulo 2^89 − 1 | Survives. A one-bit flip or step moves a seed by a power of two, never by a multiple of an odd modulus, and a fresh value almost never matches the cached seed modulo 2^89 − 1. Only the exact comparison in `streams.py` rules this key out |
| r9's K14, the key modulo 2^1101 | Survives the full run. A walk catches it only by flipping or stepping a bit from 1,101 up; the property test alone killed it in 7 of 10 seeded runs |
| r9's S18, the root from the seed modulo 2^1101 for non-negative seeds | Killed (1), by the property test alone, whose draws reach 2^1200 |
| r9's four killed mutants: the key modulo 2^1100 (K16) or by popcount and bit length (K18); the root from the seed modulo 2^1100 for non-negative seeds (S17); a seed past 2^1024 keeping the previous root (S22) | Still killed (1; 2; 2; 2). K18, S17 and S22 gain the property test. In this run K16 fails only the old test; the property test alone killed it in 7 of 10 seeded runs |
| S12 and S13 for every seed (r9's S12u and S13u) | Killed (6 each): the five r9 found and the property test |
| r8's 18 mutants | Every verdict above holds. Ten killed mutants gain the property test in every seeded run: K1, K3 to K7, S9, S12, S13 and X9. K2, K8, S14, S15 and S16 gain it on some draws: in this run K2, K8, S14 and S15 did, and in review r10's 40 seeded runs they did 29, 22, 14, 25 and 20 times. The memo keyed by hash (S11) keeps its one kill, and S10 and X8 survive |
| r7's 32 mutants and the two revisions | Every verdict above holds. Twelve killed mutants gain the property test: R1, R2, R3, R4, R7, R8, S4, S5, S6, S7, S8 and E3. R5 and r7's 13 equivalents survive. `6361b4c0` still fails 15 tests and passes the property test; `dee1e1b7` fails 29, the property test among them |
| r6's 50 mutants | The same 39 are killed and the same 11 survive. Eight gain the property test: C2, C3, C4, C5, C6, M9, M12 and N3. Eight counts have varied with Hypothesis's draws, and the r6 table gives each as a range. Four are in the row of five: the negative-count check removed (A1), the length bound removed (A2), r3's A12 (A4) and the period-zero lookup skipped (A5). In this run A5 failed `test_generated_malformed_addresses_match_registry` for the first time, 11 against 10, so the r5 and r6 tables give "10 or 11". Review r10's run gave A2 8 and A4 55, so they also give "7 or 8" and "54 or 55" |
| The property test alone, with a fresh Hypothesis database, seeds 1 to 10 | Passes at the head in 10 of 10 runs, in 0.5 to 0.8 s. Kills K9, K11, K12, K13, K18, G1, S17, S18 and S22 in 10 of 10, K14 and K16 in 7 of 10, and K10 in none |

### Tier-slot merge

`fa862935` merges master `d8302233` into the branch on top of review r9's fix `78c6c2d1`, without conflicts. Its tree equals `git merge-tree --write-tree 78c6c2d1 d8302233`. Git auto-merged `scripts/first_estimates_birth_evidence.py` and `tests/estimates/test_birth_evidence_artifact.py`; against master, each adds only OP1's nine module paths, to `POST_REVIEW_SOURCE_EXCLUSIONS` and to its pin. The merge brings in master's 7 OP0.1 record tests under `tests/open_population/`, so the OP1 command gives 341 passed and the seven-path regression command 556 passed, 2 skipped and 1 strict xfail.

The next commit recounts the tier inventories (§3). It also points §3's scope commands at `d8302233`, and makes the sealed-path check `git diff --quiet`, the form the coordinator's check uses, so it prints nothing even if a sealed file changed. `streams.py` and every other OP1 source are unchanged from `78c6c2d1`.

### Review r10

Review r10 (Opus 5.5 delta check of `78c6c2d1` and the tier-slot head `88b5df28`; its review names its model) approved at `88b5df28`, with one minor finding and four nits, all in this report. It found the merge clean, with OP1's diff against master limited to OP1's 20 files, the two exclusion pins and the recount, and reproduced every count its brief asked for. It closed r9's finding as r9 asked: K9 and K11 fall to both new tests, K12, K13 and G1 fall to the property test in 40 of 40 seeded runs, and K10 survives. It tried 11 new mutants of `streams.py`. Five were killed and six survived, none equivalent. The six fall in r9's classes: two odd-factor moduli (7·2^64 and 2^64 + 1, like K10); two size keys (modulo 2^1150, which the property test killed in 9 of r10's 20 seeded runs, and bit length past 2^1201, which it killed in none of them); and two modulo 2^1203 that the strategy almost never reaches. One differs from the registry only for seeds of 2^1203 or more, which the strategy never draws. The other differs only for two seeds a multiple of 2^1203 apart; within the strategy's range that means exactly 2^1203, which takes one exact fresh value. The exact comparison `cached[0] != seed` (`streams.py:108`) rules out every lossy key. Its weakened strategies show that the negations, and the one-bit flips and steps past bit 64, carry the property test. Its variants of the deterministic test's draws (`test_cached_root_follows_exact_int_seeds_compared_exactly`) show that the swap matters: r9's order loses K9 and K11.

| Finding | Fix |
|---|---|
| 1 (minor): the r9 table's r8-harness row gave one run's property-test gains as fixed. Which r8 mutants the property test kills depends on Hypothesis's draws: r10's run gained 12 where the author's gained 14 | The row names the ten mutants that gain it in each of r10's 40 seeded runs, and the five that gain it on some draws, with their counts and the author's run. |
| Nit: two cells of the r5 and r6 tables, the length bound removed (A2) and r3's A12 (A4), were single values; r10's run gave 8 and 55 | Both tables give "7 or 8" and "54 or 55". The r9 table's r6 row says eight counts have varied and names the four in that row. |
| Nit: "`git diff --quiet` exits 0 and prints nothing, even if a sealed file differed" could be read as exiting 0 when a file differs | §3 says the command prints nothing either way, so its exit status is the check. |
| Nit: §3 said the tier-slot merge names `d8302233`, and its list of "the only test files that differ" left out the two tier files | The recount commit names it, and §3 says test modules. |
| Nit: §3's opening paragraph gave 8 to 15 s as a property of the host; r10's run took 20.06 s at a one-minute load of 98 | Both §3 paragraphs give 8 to 20 s over the author's and reviews r8 to r10's runs, varying with host load. |

r10 also noted that OP1's exit and harness tests import `baselines/asfr.py` through the `baselines` package. §5 now says so.

## 5. Remaining work and restricted-files statement

Scheduled entrants can emigrate in their entry year by default: the seam
appends them before the exit adapter (`engine/loop.py:271–297`). OP0.1 and
OP3's timing bridge own that convention (design §5.4, OP4). A supplied hazard
can return 0 for rows where `entry_year == context.year` to disable entry-year
emigration; production schedules still need OP3's timing bridge.

OP4 must supply exit-aware relational updates before a non-null hazard can
be composed with another marital adapter (`open_population/exits.py:64–72`).
Full-size resource validation remains due before OP10a. Host variability
prevented a reliable marginal-runtime estimate; §2 retains raw fits and a
labelled engineering extrapolation. No other implementation work is deferred.

Read `RESTRICTED-FILES.md` in full before source work. Opened nothing it
restricts, no other session's transcript or scratchpad and no other Subfleet
job folder. The expressly authorized coordinator RNG-check folder and OP1
review/scratch folder were the only external evidence folders used. No
session or agent displayed or searched the three named NCHS source files
or opened an OP0.1 review folder. One of the three, `baselines/asfr.py`, is
imported through the `baselines` package by OP1's exit and harness tests
(`test_exits.py:11`, `test_harness.py:20–21`), as by other test modules on
master, so runs of those tests load it without displaying it (review r10).
All tests, probes, mutation checks and measurements use invented inputs;
no microdata or external statistical table was read and no real-data
statistic was computed. Every delegated agent reports the same boundary.

## 6. Injection follow-up: direct streams for the adapters' draws

The coordinator approved this follow-up as option 2 on 24 October 2026 and
dispatched it, at revision 3 of its brief, on 26 October. Base: master
`0f69bbb2`; branch `openpop-op1-rng-inject-20261026`. `4431486d` adds the
injection and `tests/open_population/test_stream_injection.py`; `be6843f7`
extends `tests/open_population/test_streams.py`; later commits extend
`op1_run_size.py` and add this section. On 26 October the coordinator ruled
on the build's four open questions. The branch then merged master
`9cced8ff`, a docs-only ledger update, and applied the rulings: the
observer's refusal stays, with a clearer OP1 refusal under the default; the
2100 identity grid is the full product; and the scan skips the depletion-cut
modules by path. Review inject-r1 then asked for revisions at `8634858c`;
its subsection, below, gives the findings and the fixes.

### Mechanism

`ProjectionEngine.project()` takes no registry. The loop builds one,
`streams = ProjectionRNGRegistry(draw_index, n_periods)`
(`engine/loop.py:216–217`), puts it on each period's `PeriodContext`
(`:287–294`) and passes each slot a module generator positionally
(`:297–350`). So the substitution lives in OP1's wrapper,
`_AdapterStreams` (`open_population/harness.py:180–264`):

- At the first period it keeps the loop's registry and builds one
  `DirectRNGStreams(registry.draw_index, registry.n_periods)` (`:215–221`).
  Every later period must carry the same registry object, or the run is
  refused with `ID_OR_STREAM_COLLISION` (`:222–225`). A context without a
  registry is refused the same way (`:211–214`).
- Every slot of a period receives one
  `dataclasses.replace(context, rng_registry=<direct>)`, built once per
  period (`:228–234`), just as the loop gives its eight slots one context.
  Metadata, the person ordinals and every other field are the loop's own
  objects.
- All eight slots are bound (`:393–405`): the mortality wrapper, and through
  it `_ExitAdapter` and the mortality adapter; aging; the marital core; the
  birth-entry adapter, and through it fertility; disability; earnings;
  claiming; and `close_period`, and through it household composition.
- The positional generator each slot receives is the loop's, unchanged. So
  are the loop's 600 module generators per 75-year run.
- `rng_streams="registry"` passes the loop's context through unchanged,
  which is OP1's behavior before this follow-up.
- Under `"direct"`, each slot's wrapper re-raises one error as an OP1
  refusal: a plain `ValueError` whose only argument is the sealed
  observer's refusal text, `"existing RNG registry required"`
  (`mortality_observer.py:382`). It becomes `IdOrStreamCollision` naming
  `rng_streams="registry"`, chained from the original (see the observer
  below). Every other error passes through as the object raised.
- Emigration draws from `DirectRNGStreams` in both modes. `_ExitAdapter`
  builds its own from the context's draw and horizon
  (`open_population/exits.py:149–152`, unchanged), and
  `test_exact_emigration_stream` still checks it against the sealed registry
  itself.

`_project`, `run_production` and `run_gate` take
`rng_streams: Literal["registry", "direct"] = "direct"`
(`open_population/harness.py:286`, `:439`; `open_population/gates.py:60`).
Any other value is refused before the initializer or any adapter runs
(`harness.py:191–194`, `:294`). `OpenPopulationResult` records
`rng_streams` and `rng_stream_class`, the qualified name of the class that
served the slots (`:129–130`, `:200–206`, `:429–430`). No module was added,
so `POST_REVIEW_SOURCE_EXCLUSIONS` and its pin are unchanged.

### Invariants

1. **OP1's projection is identical whichever stream class serves the
   adapters' person and tagged draws**: every slice, every declared flow and
   the accounting history.
2. At every valid stream address the direct stream equals the registry's
   (seed identity, `bit_generator.state` and draws), and at every bad
   address both refuse with the same exception type and message (§2 states
   the user-defined-type limit).
3. Within a run there is one direct instance and one context per period;
   the generator each slot receives equals the loop's module generator for
   its period and module.
4. The two classes share the registry's public surface, and no sealed code
   checks the registry's type except the one check recorded below, which
   refuses rather than diverges.

### The coordinator's conditions and their evidence

**1. No sealed code changes.** Against master `9cced8ff`, the master it
merged, the branch changes only `open_population/harness.py` and `gates.py`,
OP1's two stream test modules and three files in this folder: this report,
`op1_run_size.py` and `op1_run_size_injection.json` (§3's commands, with
`9cced8ff` as the base). No engine or baselines attribute is patched, and
`DirectRNGStreams` is not a registry subclass:
- `test_a_direct_run_patches_no_sealed_module_attribute` compares every
  attribute of `engine/rng.py`, `engine/loop.py`, `ProjectionRNGRegistry`
  and `PeriodContext`, by identity, before and after a direct run;
- `test_direct_streams_are_not_a_registry_subclass`;
- `test_each_period_gives_every_slot_one_context_and_the_loop_generators`,
  in both modes, checks the state of the generator each of the eight slots
  receives against the loop's module generator, and that one context, one
  stream instance, one metadata mapping and one ordinal map serve the run.
  It also records the loop's own context where the harness receives it and
  compares every other `PeriodContext` field of each slot's context with
  it: equal values, the requested draw index, and the loop's own metadata
  and ordinal objects. Only `rng_registry` differs, and only in direct mode.
  A replacement context with a changed draw index, or with copied metadata
  or ordinals, fails it.

`op1_run_size.py` patches registry methods, as it did at OP1's merge, but
only inside its measurement worker, to time them. The harness patches
nothing.

**2. Interface parity, and no type check on the registry.**
`test_direct_streams_share_the_registry_public_surface` derives the
registry's surface by introspection: its dataclass fields (name, annotation,
default, `init`, `kw_only`); every public member by kind and full signature
(`draw_seed` as a read-only property; `seed_sequence`, `generator`,
`child_generator`, `tagged_generator`, `tagged_child_generator` and
`person_generator` as methods); the constructor signature; and the dataclass
parameters. The direct class must match each. The expected names are also
pinned, so a member added to the registry fails the test until the direct
class matches it.

`test_sealed_code_holds_only_the_known_registry_type_check` runs an AST scan
of `src/populace_dynamics/` outside `open_population/`: 302 modules at
`9cced8ff`, once the five excluded modules below are dropped.
- **What it reads.** The project's data-access record keeps two modules out
  of automated reads: `estimates/adjusted_poverty.py` and
  `uniform_cut_track_u/rows.py`. The scan also skips the depletion-cut
  modules, every path matching `src/populace_dynamics/bridge/depletion_cut*.py`,
  so that what it reads does not depend on who runs it. At `9cced8ff` the
  pattern matches three: `bridge/depletion_cut.py`,
  `bridge/depletion_cut_population.py` and
  `bridge/depletion_cut_population_child.py`. The walk decides from each
  path alone and drops all five before anything opens, reads, parses,
  hashes or stats them.
  - `test_closed_module_exclusions_are_pinned_exactly` pins the two closed
    paths, the pattern and the three paths it matches, and checks five
    neighbouring paths the rule must not drop.
  - `test_the_tree_excludes_exactly_the_pinned_modules` lists the tree by
    directory listing alone and checks that the excluded set is exactly
    those five, so a new match fails it and comes back for a decision.
  - `test_scan_walk_skips_excluded_modules_without_opening_them` records
    every read on an invented tree with decoys at all five paths and at one
    more name the pattern matches.

  Every other module is read, `baselines/asfr.py` included.
- **Closing the gap at run time.** In a fresh interpreter,
  `test_projection_runs_import_no_excluded_module` runs a 2100 production
  projection and two 2027 gate runs, one in each mode, with person-stream,
  tagged-stream and emigration draws. It then checks that neither closed
  module and no module whose name contains `depletion_cut` is in
  `sys.modules`. Code a projection never imports can't check its
  registry's type.
- **Two layers.** Specific checks name the kind of each type check they
  find. Under them, a catch-all reports every other mention of the class,
  or of its name or its module's name as text, outside a benign place.
  Benign places are imports, string statements (docstrings among them),
  `__all__` listings, annotations other than dispatch hints, and the callee
  of a construction such as `ProjectionRNGRegistry(draw_index, n_periods)`.
  So a static spelling the specific checks miss still fails the pin, as a
  `class-reference`, `class-name-string` or `module-name-string` hit on its
  line.
- **What the specific checks catch.**
  - `isinstance` and `issubclass`, also through aliases such as
    `check = isinstance` or `from builtins import issubclass as check`.
  - `type(x)` or `x.__class__` compared with the class, by any comparison
    operator, alone or in a chain; and any other comparison against the
    class or class info.
  - Comparisons with the class's name as text: `__name__` or
    `__qualname__` against a string, a string held in a name or a
    container, or `ProjectionRNGRegistry.__name__`. Comparisons with its
    module's name count the same way.
  - `match` class and value patterns.
  - `__instancecheck__` and `__subclasscheck__`.
  - `singledispatch` registration by argument or by hint, quoted hints
    included.
  - Private names found on only one class, whether read as an attribute,
    probed with `hasattr` or `getattr`, or held as a string.
- **How it follows the class.** Directly; through an import alias; as a
  module attribute (`rng.ProjectionRNGRegistry`, the dotted path, or an
  aliased module); and through relative imports, local assignment chains,
  class and instance attributes, default arguments, loop variables, named
  expressions, `type(ProjectionRNGRegistry(...))` and `getattr` on the
  module. It also follows the class inside class info: tuples, lists,
  sets, unions written with `|` or `typing.Union`, tuples joined with `+`,
  mappings, subscripts of any of these, and anything rebuilt or read from
  them, such as `tuple(KINDS)` or `KINDS.get(key)`. Re-exports are followed
  across modules to a fixed point. Bindings only accumulate, so the fixed
  point ends even on a binding cycle such as `a = b.c; b = a`. The scan
  over-approximates on purpose: a binding anywhere in a module counts
  everywhere in it, and an attribute counts wherever a name spelled like it
  is bound.
- **Text as the parser sees it.** Every module is parsed, with no text
  filter first. The build's filter parsed a module only if its text held a
  tracked name, and an escaped literal such as `"\x50rojectionRNGRegistry"`
  passed it, though the parser decodes it to the class's name. The scan
  reads strings after the parser has joined adjacent literals and decoded
  escapes, and it folds `+` and f-strings made only of literals. It sees
  identifiers after the parser's NFKC normalization, so a fullwidth first
  letter still names the class.
- **Cost.** Right after parsing, each literal container of constants whose
  strings hold none of the class's name, its module's name or a probe name
  is replaced by `None`. No check can report or bind anything from such a
  container. The generated data modules of 18.5, 11.1 and 1.6 MB are almost
  all such containers: pruning leaves 178, 78 and 7 of their 706,994,
  251,826 and 85,417 syntax-tree nodes, and 930,518 of the 2,007,887 in all
  302 modules. `test_pruning_leaves_every_invented_scan_unchanged`
  and `test_pruning_leaves_scans_unchanged_for_any_literal` (200 Hypothesis
  literals, each placed in eight positions) check that pruning changes no
  result. On the host the real-tree test takes 6.5 s, and its process peaks
  near 1.3 GB, mostly while parsing the largest data module.
- **Its own tests.**
  - `test_scan_catches_every_spelling_of_a_registry_type_check` covers 58
    invented spellings. Each gives exactly the hits its markers ask for:
    one of its kind on its check line, plus one on each line that binds
    the class or holds its name. All twelve of review inject-r1's misses
    are among them.
  - `test_every_spelling_tells_the_two_classes_apart` runs 56 of them and
    checks that each answers differently for the two classes. The other
    two cannot run: a relative import, and an alias chain written in
    reverse order.
  - `test_scan_follows_re_exports_across_modules` is unchanged: aliases one
    and two modules away, a star import, a module alias, and a same-named
    local class that is not caught.
  - `test_scan_ignores_unrelated_checks_and_ordinary_registry_use` has 16
    negatives. They include `__all__` listings, docstrings, annotations, a
    keyword-only hint on a dispatch registration, a module function that
    shares a probe's name, another use of the registry's module and pruned
    literal tables.
- **Its messages.** A hit carries only a module path, line number and node
  kind. `test_scan_messages_never_show_source_text` plants a distinctive
  literal in an invented snippet and checks that it is absent from the
  hits, their `repr` and the assertion message, and from the refusal raised
  for unparsable source, whose original exception is suppressed.
- **Limits.** The scan does not see:
  - names built at run time: concatenation with computed values, `chr`,
    decoding, formatting, or `getattr` with a computed string;
  - part of the class's or module's name, such as a prefix test or a
    regular expression;
  - the type of another value: `type(a) is type(b)`,
    `isinstance(x, type(y))`, and the dataclass-generated `==` between a
    registry and a direct instance, which is false across the two classes;
  - annotations read at run time by anything but a `register` decorator.
    Searching `src/` outside the excluded modules and `baselines/asfr.py`,
    `typing.get_type_hints` appears only in `track_b/_provenance.py`, whose
    schemas read the hints of the Track B classes and calls it decorates.
    The one registry hint in Track B, on `track_b/replay.py`'s private
    `_rng_signature`, carries no decorator;
  - code it does not read: the excluded modules, OP1's own package,
    scripts, tests and third-party code.

  Over-approximation can also give false hits. Any hit, false or not,
  fails the pin and comes back for a decision.

**The scan finds one check in sealed code.**
`src/populace_dynamics/mortality_observer.py:381` is a `type-compare`: the
opt-in mortality observer refuses any context whose registry is not exactly
a `ProjectionRNGRegistry` (present since `e4e512e1`, before `3d69b1fc`,
where the coordinator's search for `isinstance` found none). It raises
`ValueError` before drawing, so it fails loudly rather than diverging.
- `test_pinned_sealed_check_refuses_direct_streams_loudly` shows it accepts
  the registry, giving `apply_mortality`'s survivors, and refuses the direct
  class.
- `test_pinned_sealed_check_refuses_a_direct_op1_run_loudly` composes it
  into OP1. The registry mode completes, with the observer called in both
  years. Under the direct default, `run_gate` and `run_production` both
  refuse in the first projected year, before the observer draws, with
  `IdOrStreamCollision`: "a composed step requires the projection's own
  ProjectionRNGRegistry (observe_mortality does, mortality_observer.py:381);
  pass rng_streams="registry"". The sealed `ValueError` is its cause.
- `test_only_the_sealed_refusal_under_direct_streams_is_re_raised` checks
  that only that error is re-raised. Four errors pass through unchanged
  under the default: another `ValueError`, the refusal text with a second
  argument, a `ValueError` subclass with the same text and a `TypeError`.
  So does the refusal itself under the registry.

The coordinator's ruling of 26 October keeps this disposition. An OP1 run
that composes `observe_mortality` must pass `rng_streams="registry"`, and
the harness does not switch modes for it. The docstrings of `run_production`
and `run_gate` say so. No entry point on this branch composes the observer.
Searching `src/`, the excluded modules aside, no module imports or calls
`observe_mortality` outside its own module; OP1's harness and gates name it
only in docstrings and in the refusal. The harness can't tell at setup that a
slot wraps the observer, since a slot is any callable. It therefore
re-raises the sealed refusal at the observer's first call, which comes
before any draw.

Condition 2, as the coordinator amended it, requires the scan's set of
registry type checks in scanned sealed code to equal an exact pinned set.
Today that set is one entry: `mortality_observer.py`, line 381,
`type-compare`. The scan test compares the sorted hits with the sorted pin,
so a new hit, a moved line or a removed hit fails it, and any such change to
sealed code comes back for a decision.

**3. Stream identity.**
- `test_every_method_matches_registry_at_every_period` covers every period
  from 0 to the horizon, all eight modules and all six methods, at
  horizons 0, 1, 7 and 75 and draws 0, 1 and 9.
- Both generator comparisons in `test_streams.py` now also check
  `bit_generator.state`. `_assert_generators_equal`, which the exhaustive
  grid and its Hypothesis test use, checks it before and after four draws.
  `_generator_identity`, which the refusal-grid comparisons use, records it
  before two draws.
- `test_bad_addresses_on_injection_horizons_match_registry` crosses periods
  just outside each horizon, an unknown module and negative children and
  tags with valid values, on the same horizons and draws, and compares
  exception type and message.
- `test_generated_addresses_on_injection_horizons_match_registry` adds 60
  Hypothesis examples, valid or not.

**4. End-to-end identity.**
`test_projection_hash_is_identical_for_both_stream_classes` runs each
configuration in both modes and compares:
- the SHA-256 over every slice, computed as `op1_run_size.py` does;
- every slice, frame by frame;
- the declared flows and the accounting history.

The grid is sizes 1, 3 and 6 by draws 0, 3 and 17, in full, at both 2027
(gate runs) and 2100 (production runs at the registered horizon): 18
configurations. The build had zipped the 2100 runs to three; the
coordinator's ruling asked for the full product. The nine 2100 pairs took
0.76 to 0.97 s each on the host.

Each run draws:
- a mortality person stream for everyone;
- an ASFR tagged child for women of childbearing age;
- an emigration tagged child for each survivor;
- scheduled entrants in two distinct years for the 2027 runs (2026 and
  2027) and in three for the 2100 runs (2026, 2063 and 2100);
- through an invented probe in the earnings slot, every method the context
  exposes, from `context.rng_registry` and `context.person_generator`, kept
  as a column.

The test also checks that the adapters received `DirectRNGStreams` in
direct mode and `ProjectionRNGRegistry` in registry mode.
`test_projection_identity_holds_on_generated_runs` adds 10 Hypothesis
examples: rosters of 0 to 8, death, birth and emigration rates of 0 to 1,
and horizons of one to four years.

`op1_run_size.py` compares three modes:
- `registry`: everything on the registry;
- `direct_emigration`: OP1's behavior before this follow-up;
- `direct`: the default.

Each record names the stream classes the adapters and the exit adapter were
observed to receive, the SHA-256 of `open_population/streams.py`, `harness.py`
and `exits.py`, and the process CPU time. The script stops if a mode runs
another class, or if the three modes' projection hashes differ for any
size. In the build's sandbox, one 10-person worker per mode completed, with
identical projection hashes across the three.

The main session then ran the script on the host at `441b9f77`, from
07:50 to 07:52 UTC on 26 October, with one-minute loads of 76 to 92 at the
projection starts:

```sh
.venv/bin/python docs/design/open_population_evidence/op1_run_size.py --sizes 25 100 400 --output docs/design/open_population_evidence/op1_run_size_injection.json
```

`op1_run_size_injection.json` holds that run, and `op1_run_size.json`
keeps §2's two-mode run of `0d0c073c`. All nine workers reconciled 75
periods with zero count and weight residuals and zero revaluations. Each
record's source hashes match the files at `441b9f77`. For each size the
three modes give the same projection hash, and it is §2's hash for that
size.

| Initial people | Mortality person-years | Projection seconds, `registry` | `direct_emigration` | `direct` | Peak RSS (MB), `direct` |
|---:|---:|---:|---:|---:|---:|
| 25 | 4,299 | 4.87 | 3.40 | 1.40 | 194.4 |
| 100 | 11,936 | 8.03 | 5.00 | 1.77 | 194.9 |
| 400 | 43,793 | 26.50 | 17.60 | 3.13 | 203.0 |

- Process CPU time over each projection is 94 to 99% of its wall time.
- At 400 people the direct default takes 12% of the `registry` mode's time
  and 18% of the time OP1 took before this follow-up (`direct_emigration`).
- Peak RSS over the nine workers ranges from 192.3 to 203.0 MB. At each size
  the direct mode is within 1.4 MB of the `registry` mode.
- The microbenchmark's median cost per address (one tagged-child generator
  and one draw) is 6.7 µs at horizon 7 and 7.4 µs at horizon 75 on the
  direct class, against 52.3 and 216.7 µs on the registry.

These are single runs on a loaded host, so the ratios are indicative, not
bounds. The full-size measurement is still due before OP10a.

**5. Seal bookkeeping.** No module was added, so the exclusion tuple and its
pin are unchanged. `tests/track_u2/test_u2_isolation.py` was not run, and CI
gives its result. `tests/tier_counts.json` and `tests/README-tiers.md` are
untouched, for the main session's recount.

**Tier.** Every new test is in `tests/open_population/test_streams.py` or
`test_stream_injection.py`, and `_classify_test_module` classifies both
modules as `unit`. The stream differential and the hash identity therefore
run on every CI push.

### Review inject-r1

Review inject-r1, a hard-tier Subfleet review on a Codex lane, read the
branch at `8634858c` and returned REVISE, with one major and three minor
findings. It confirmed the harness, the re-raise, the coordinator's
sealed-path and file checks, the evidence audit and the six mutants below.

1. **Major: static type checks escaped the scan.** Twelve invented checks,
   each true for the registry and false for the direct class, gave no hit:
   class info bound to a name (a tuple and a union), aliases of
   `isinstance` and `issubclass`, the class's name in a tuple,
   `ProjectionRNGRegistry.__name__`, an escaped name literal (which also
   passed the text filter), a class attribute, a subscript of a literal, a
   named expression, dictionary dispatch and a quoted dispatch hint.
   **Fix:** the two-layer scan under condition 2, with the text filter
   removed. All twelve are among the invented spellings, and the scan still
   finds exactly the one pinned check in sealed code.
2. **Minor: the binding test did not show that only `rng_registry`
   changes.** A replacement context with `draw_index + 1` survived it.
   **Fix:** the test now compares every other field with the loop's own
   context (condition 1). That mutant fails it, and so do copies of the
   metadata or the ordinals.
3. **Minor: the RSS gap at 25 people is 1,359,872 bytes,** so "within
   1.3 MB" understated it. **Fix:** "within 1.4 MB".
4. **Minor: evidence wording.** **Fix:** condition 1 names base `9cced8ff`
   and the three files in this folder. The stream-identity text describes
   the two generator helpers separately, the entrant years are given per
   horizon, and this section's source line references match the current
   files.

### Commands and results

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider tests/open_population tests/estimates/test_birth_evidence_artifact.py tests/test_entrant_schedule.py tests/test_entrant_domains.py tests/test_entrant_id_allocation.py
.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider -m unit tests/open_population
.venv/bin/black --check -l 79 src/populace_dynamics/open_population tests/open_population docs/design/open_population_evidence/op1_run_size.py
.venv/bin/ruff check src/populace_dynamics/open_population tests/open_population docs/design/open_population_evidence/op1_run_size.py
git diff --check 9cced8ff
git diff --stat 9cced8ff
git diff --quiet 9cced8ff -- src/populace_dynamics/engine src/populace_dynamics/baselines src/populace_dynamics/cola_track_a src/populace_dynamics/track_b scripts tests/estimates tests/tier_counts.json tests/README-tiers.md
```

The build ran the required command in its sandbox in five chunks of named
modules, one process each, because the sandbox could not finish it within
one tool call. Together they gave **442 passed and 1 strict xfail, with the
2 existing warnings**: 339 in `tests/open_population`, which are OP1's 238
and the 101 tests this follow-up adds (76 in the new module and 25 in
`test_streams.py`), and 104 in the other four modules. After the new
module's last change (`d49d0813`: the binding-cycle fix and the chained
comparison), all 76 of its tests ran again and passed. `--collect-only -m
unit` collected all 339, none deselected. Black, Ruff and `git diff --check`
were clean, `git diff --stat` listed only the build's six files, and the
sealed-path `git diff --quiet` exited 0.

The sandbox's wall times are not usable, so the build timed the new tests
by process CPU time. In the sandbox, the existing 2100 production test took
1.67 CPU seconds, against the 0.59 s §3 reports for this host. The slowest
new tests took 12.7 (the hash grid), 6.8 (the every-period differential) and
2.3 (the scan) sandbox CPU seconds. The main session's host rerun gives the
times that count.

On the host, at `441b9f77`, the main session first ran the required
command with the real-tree scan test deselected, pending the ruling on
which modules the scan reads: 337 passed and 1 strict xfail in
`tests/open_population`, and 104 passed in the other four modules.

After the rulings were applied, it ran the required command again, in two
named-module processes at one-minute loads under 8:
- `tests/open_population`: **346 passed and 1 strict xfail** in 18.15 s,
  the real-tree scan test included. These are OP1's 238 and the 109 tests
  this follow-up adds: 84 in `test_stream_injection.py` and 25 in
  `test_streams.py`.
- The other four modules: 104 passed in 0.86 s.
- Peak RSS was 340 MB.
- `--collect-only -m unit tests/open_population` collects all 347, none
  deselected.
- Black, Ruff and `git diff --check` are clean. `git diff --stat 9cced8ff`
  lists this branch's seven files: the build's six and
  `op1_run_size_injection.json`. The sealed-path `git diff --quiet` exits 0.

The slowest tests took 1.16 s (the fresh-interpreter import check), 0.99 s
(the real-tree scan) and 0.76 to 0.97 s for each 2100 hash pair.

Six mutants of the new code each fail the tests aimed at them:
- re-raising under both modes;
- accepting `ValueError` subclasses;
- matching the refusal text as a substring;
- never re-raising;
- re-raising without the chain;
- ignoring the depletion-cut pattern. This mutant ran only against the
  pin and decoy tests, never against the real tree.

After the fixes for review inject-r1, the main session ran the same
commands on the host from 10:53 to 10:58 UTC on 26 October, at one-minute
loads of 18 to 25, each process under the load-check plugin:
- `tests/open_population`: **437 passed and 1 strict xfail** in 34.13 s.
  These are OP1's 238 and the 200 tests this follow-up adds: 175 in
  `test_stream_injection.py` and 25 in `test_streams.py`.
- The other four modules: 104 passed in 1.00 s.
- The required command plus the two Track B holdout-registry modules: 756
  passed, 2 skipped and 1 strict xfail.
- Peak RSS was 1.33 GB, against 340 MB before; the real-tree scan's parse
  of the largest data module accounts for most of the rise.
- The slowest tests took 6.54 s (the real-tree scan), 2.04 s (the
  fresh-interpreter import check) and 1.45 to 1.55 s for each 2100 hash
  pair.
- No file under a bar was opened, the pattern line named only
  `baselines/asfr.py` (read by the scan, never displayed), and neither
  barred function was called.
- `--collect-only -m unit tests/open_population` collects all 438. Black,
  Ruff and `git diff --check` are clean. `git diff --stat 9cced8ff` still
  lists the seven files, and the sealed-path `git diff --quiet` exits 0.

Thirteen more mutants each fail the tests aimed at them. Three change the
replacement context's draw index, metadata or ordinals. Ten disable a part
of the scan: the catch-all, checking-function aliases, container names,
pruning's check for tracked strings, `+` folding, parsing of quoted hints,
module-name comparisons, the benign `__all__` listing, private-attribute
reads and loop bindings. None ran against the real tree.

### Restricted-files statement

The build read `RESTRICTED-FILES.md` at its pinned hash and the
coordinator's three pending entries in full before any source work. It
opened no file they list, no other session's transcript or scratchpad and
no other Subfleet job folder. It displayed no line of any file under a
display bar. Its code reads the scanned modules without displaying them,
`baselines/asfr.py` included, as the ruling on the scan allows. No code it
wrote or ran imports the two closed modules, loads either by path, or reads
the committed MINT8 guide. Twice, a shell search or byte count over `src/`
in the build's own session did not apply its exclusions, because of how the
shell expanded them. Neither printed a line from any excluded file, and the
build's report to the main session lists both. Since then, every scripted
search by the main session takes an explicit file list from `git ls-files`,
minus the excluded files, never a shell glob with exclusions. The main
session ran the real-tree scan test only after the depletion-cut exclusion
was in. With an audit hook on file opens, that run opened no excluded file,
and no projection run imported a closed or depletion-cut module. Every
test, probe and measurement uses invented inputs. No microdata or external
statistical table was read, and no real-data statistic was computed.

The fixes for review inject-r1 followed the same rules. The main session's
measurement scripts read the scanned modules only through the test
module's own walk, and printed module paths, line numbers, node kinds and
counts. Its searches over `src/` took their file lists from the helper.
