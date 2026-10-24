# OP1 implementation report

## 1. What I built

Implemented the approved design at `5c82dbd9`, §§2.1–2.5, 2.9–2.10,
3.1 (OP1), 5.1, 5.4, 6.4, 7 and 8 (approval d1925).
The package remains `src/populace_dynamics/open_population/`.
Its scope is accounting conformance and seam mechanics; it admits no
demographic law or population forecast.

| Item | Implementation | Commit |
|---|---|---|
| Foundation | `__init__.py`, `errors.py`, `events.py`: named refusals and immutable declarations with explicit entry provenance | `574ab4f2` |
| 1. Exits | `exits.py`: unchanged mortality call, deaths first, tagged person streams for survivor-only emigration, default off, marital compatibility refusal | `f84e3068` |
| 2. Births | `births.py`: unchanged fertility call, allocator-backed additions, `maternal_birth` and entry year | `04817b36` |
| 3. Scheduled entries | `schedule.py`: owned metadata/allocator, builder callback or supplied frames, exact metadata validation, `immigrant_cohort` and entry year; preserve the closed-loop cursor for signed IDs | `7fad996a`, `90474206` |
| 4. Horizon | `harness.py`: production request enforces its registered end year; shorter reads copy prefixes of the completed run | `3b9b1845` |
| 5. Accounting | `harness.py`: explicit declarations include entrants who exit during their entry year; annual reconciliation, fixed-weight checks and single-presence history reconciliation | `3b9b1845` |
| 6. Gate facade | `gates.py`: fixed gate horizon, slotted request with no target field, unknown keyword refusal, isolated import and deferred project-import checks | `cfef0457` |
| 7. Reducer seal | Exact eight-file exclusions and their existing pin; historical initializers remain unchanged | `1e23e0cf` |
| 8. Run size | `op1_run_size.py` and `op1_run_size.json` beside this report | `5a5c8b93` |

`run_production(initial, modules, ProductionRequest(horizon, horizon), ...)`
accepts copied `scheduled_entries`, or a `schedule_builder(allocator)` callback
that calls the existing `build_entrant_schedule`. The result exposes
`projection`, `events`, `accounting` and `read_prefix(end_year)`.
`run_gate` instead requires `GateRunRequest(horizon=...)`.

The worktree's common Git directory is outside its writable boundary. Creating
a normal branch failed with `Operation not permitted`. Commits therefore live
in workspace-owned metadata at `.cache/op1-git` on
`openpop-op1-harness-r2`. A Git bundle accompanies the completed report for
transfer to the caller's repository (`op1-harness.bundle`, containing
`refs/heads/openpop-op1-harness-r2`). No history was rewritten and nothing was
pushed. All source edits and generated evidence stay in this workspace.

## 2. Tests and exact commands

All fixtures and property examples are invented. The Hypothesis tests use
6–25 examples and disable machine-dependent per-example deadlines.

| New test module | Design invariant |
|---|---|
| `tests/open_population/test_events.py` | Explicit entry provenance and independent event snapshots (§7) |
| `tests/open_population/test_exits.py` | Mortality coupling, disjoint exits, one-year emigration monotonicity, order invariance, incompatible widowhood refusal (§§5.4, 7) |
| `tests/open_population/test_births.py` | Delegated draws and arguments, exact allocator ownership, fixed incumbent weights, maternal provenance (§7) |
| `tests/open_population/test_schedule.py` | Exact metadata validation, shared allocator, disjoint IDs, reserved namespace, copied schedules (§§2.1, 7) |
| `tests/open_population/test_harness.py` | Annual stock/weight identity, transient arrivals/exits, history retirement, closed-run coupling, registered prefixes, determinism and canonical-order invariance (§7) |
| `tests/open_population/test_gates.py` | Fixed gate horizon, target refusal and fresh-process import isolation (§5.1) |

Commands ran from the workspace root. In the commands below, the shell variables
expand to the authorized existing dependency environment; `PYTHONPATH` selects
this workspace's sources and bytecode writing is disabled.

```sh
OP1_TOOLS=/Users/maxghenis/PolicyEngine/_openpop-builds/op1/.venv/bin
export PYTHONPATH="$PWD/src"
export PYTHONDONTWRITEBYTECODE=1

"$OP1_TOOLS/python" -m pytest -q tests/open_population/test_events.py
"$OP1_TOOLS/python" -m pytest -q tests/open_population/test_exits.py
"$OP1_TOOLS/python" -m pytest -q tests/open_population/test_births.py tests/open_population/test_schedule.py

"$OP1_TOOLS/python" -m pytest -q tests/open_population tests/estimates/test_birth_evidence_artifact.py tests/test_entrant_schedule.py tests/test_entrant_domains.py tests/test_entrant_id_allocation.py

"$OP1_TOOLS/python" -m pytest -q tests/open_population/test_schedule.py tests/open_population/test_gates.py tests/open_population/test_harness.py::test_disabled_emigration_matches_closed_engine_slice_by_slice tests/open_population/test_harness.py::test_disabled_emigration_matches_closed_run_for_signed_ids
"$OP1_TOOLS/python" -m pytest -q tests/open_population/test_gates.py

"$OP1_TOOLS/black" -l 79 src/populace_dynamics/open_population tests/open_population scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py
"$OP1_TOOLS/ruff" check src/populace_dynamics/open_population tests/open_population scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py
"$OP1_TOOLS/black" -l 79 docs/design/open_population_evidence/op1_run_size.py
"$OP1_TOOLS/ruff" check docs/design/open_population_evidence/op1_run_size.py
"$OP1_TOOLS/black" --check -l 79 src/populace_dynamics/open_population tests/open_population scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py docs/design/open_population_evidence/op1_run_size.py
"$OP1_TOOLS/ruff" check src/populace_dynamics/open_population tests/open_population scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py docs/design/open_population_evidence/op1_run_size.py

"$OP1_TOOLS/python" docs/design/open_population_evidence/op1_run_size.py --sizes 25 100 --timeout-seconds 900 --output docs/design/open_population_evidence/op1_run_size.json
```

Initial results: declarations **4 passed**; exits **15 passed, 1 fixture
failure**, corrected by giving the empty invented mortality mask boolean
dtype; births/schedules **15 passed**. The combined run then returned
**158 passed, 1 expected failure, 1 timeout**, in 739.87 seconds.
The corrected exit fixture passed in that combined run. The gate subprocess
exceeded its original 180-second cold-import allowance; its follow-up uses
600 seconds. The suite emitted two pandas deprecation warnings from fixtures
that intentionally mutate a frame in place.

The signed-ID/coupling follow-up returned **18 passed, 1 failure** in 258.08
seconds. Its longer subprocess run exposed the imported numerical helper
`pandas.core.computation.align`. Keeping facade descriptors lightweight and
deferring the numerical runtime resolved the literal import-name requirement.
A separate static test walks deferred imports in the OP package and refuses
project alignment producers too. The final gate module returned **7 passed**
in 44.68 seconds. A direct pre-fix fresh-interpreter probe independently printed
`['pandas.core.computation.align']` and failed its assertion:

```sh
"$OP1_TOOLS/python" -c 'import sys; import populace_dynamics.open_population.gates; loaded = sorted(name for name in sys.modules if "align" in name.lower()); print(loaded, flush=True); assert not loaded, loaded'
```

The final combined command returned **163 passed, 1 expected failure, 2
fixture deprecation warnings in 53.72 seconds**. This includes the reducer
identity, reachability and initializer tests and all three existing entrant
test files requested in the brief. Black's final check reported **17 files
unchanged** and Ruff passed. No other test modules were run.
The tier inventory files remain untouched; their main-session update is
pending, so a full tier-policy check is not claimed.

Both resource runs reached 2100 with 75 reconciled periods and zero count,
weight and revaluation residuals:

| Initial people | Final people | Births | Scheduled entries | Projection seconds | Worker seconds | Peak memory, bytes |
|---:|---:|---:|---:|---:|---:|---:|
| 25 | 134 | 113 | 75 | 63.877 | 249.974 | 218,071,040 |
| 100 | 296 | 181 | 300 | 120.377 | 193.286 | 227,540,992 |

The largest live roster was 309 people; the larger run retained 18,543
person-year rows. Worker time includes cold imports and setup; projection
time excludes both. Peak memory includes imports and retained slices. These
two measurements establish no scaling law. Stopped at 100 initial people;
the script's optional 400-person size was not run.

## 3. Mechanism facts established from source

- **Widowhood:** `cola_track_a/adapters.py:104–111` computes married, linked
  spouses absent from the current roster, without an exit-cause check;
  `:113–117` writes widowhood. Its assembly installs the adapter through a
  partial at `:233`. Removing an emigrant would therefore widow the partner
  who stays. OP1 refuses every non-null emigration hazard unless the exact
  explicit `no_marital_transitions` adapter is used. The two-person example
  executes the unsafe adapter and verifies the refusal.
- **Timing:** `engine/loop.py:271–286` appends scheduled entries before
  mortality; `:297–315` runs mortality before aging and marital state;
  `:317–323` then runs fertility. OP1 declares arrivals before mortality so
  a same-year death or emigration remains an accounted transient.
- **Draws:** `engine/steps.py:121–134` sorts and draws person-keyed mortality.
  `baselines/fertility.py:118–123` uses tagged person-child streams;
  `engine/rng.py:129–156` constructs that independent child sequence.
  OP1 uses that pattern under the mortality module for emigration and passes
  the original mortality and fertility RNG objects through once.
- **Birth IDs:** `engine/steps.py:488–503` takes IDs from the context's
  allocator and fills year, age, sex, parent and carried weights. OP1 checks
  that the exact allocated ID range equals the additions.
- **Horizon dependence:** `engine/loop.py:242–266` reserves all initial and
  scheduled IDs and ordinals before simulation; `:358–360` assigns newborn
  ordinals afterward. The test executes the committed
  `5c82dbd9:docs/design/open_population_evidence/horizon_dependence.py`
  with 2026/2027 end years and reproduces unequal shared open-run slices.
  Prefix reads avoid scheduling or simulating another horizon.
- **Accounting:** `engine/accounting.py:1025–1086` resolves explicit event
  weights, separates revaluation and reports a binary64 summation residual.
  `engine/accounting_history.py:287–299` refuses departed-ID reuse under its
  declared single-presence contract. OP1 retains those checks and refuses
  fixed-weight changes in adapter slots.
- **Source order gap:** `baselines/fertility.py:114–128` keeps mother row
  order; `engine/steps.py:473–497` assigns child IDs and parent links in that
  order. With two female mothers aged 30, birth probability 1 and allocation
  beginning at 3, children 3/4 link to mothers 1/2; reversing the mother rows
  links them to 2/1. This executed, minimized example remains a strict xfail.

## 4. Refusals and remaining work

No sealed engine, Track B, gate contract, committed run or shared tier file
changed. Historical reducer identity, initializer coverage and transitive
reachability checks passed in the combined run.

Unknown or absence-based marital adapters remain incompatible with non-null
emigration; OP4 must supply exit-aware relational updates and exit-unit rules.
The existing ASFR/materializer order gap remains open. The harness requires
at least one projected period because `reconcile_history` refuses an empty
transition sequence (`engine/accounting_history.py:198–206`).

Real-data schedules still require OP3's universe and timing/exposure bridges
(design §2.3 and §3.1); this harness supplies only mechanical support.
No new fertility, migration, benefit, alignment or forecast claim is made.
Full Microcosm-sized resource validation remains open before OP10a; this job's
optional measurement stops at 100 initial people.

## 5. Restricted-files statement

Read the required restricted-files policy in full before source work. Opened
none of the files or folders it restricts, no other session's transcript or
scratchpad, and no other Subfleet job folder. All test and measurement rosters
are invented; no microdata or external statistical table was read. Every
delegated agent reported the same boundary.
