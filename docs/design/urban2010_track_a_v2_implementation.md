# Track A v2 implementation record

INVENTED DATA - NOT A COMPARISON

This implements the D/S calculations and reporting of `a2-ratified-1` in new
modules. [Max's d603 ruling, 2026-09-28](urban2010_track_a_v2_rulings.md)
clarifies that the structural path may run the unchanged projection, including
weighted DI transitions, while emitting only the frozen §16.7 counts and
protocol/attempt metadata. Its separate frozen protocol and pre-execution
record remain required. Outcome artifacts carry
“registered, one-shot, post hoc, not blind”, “PSID-seeded closed cohort” and
“Python oracle (not Axiom)”; invented artifacts additionally carry the heading
above. The implemented matrix has 68 rows, with fixed D×R0 and D×F0 headlines.
No PSID or real-population input was read. No real-population projection,
benefit computation, structural count or registered outcome execution was
performed in this job.

The newly added tests and all D/S computations used invented fixtures. The
requested pre-existing unit tier also traversed its published SSA Case A/B
illustration fixtures, which its helper labels `synthetic=False`
(`tests/test_axiom_benefit_bridge.py:1049`). Their source transports were read
and external engine files were hashed; the actual-engine examples refused
on a changed provenance receipt before invoking Axiom. These existing
source-fixture reads are disclosed below and in the ledger, rather than
being represented as newly invented fixtures.

## Files and contract map

New package: `src/populace_dynamics/track_a_v2/` contains `__init__.py`,
`benefits.py`, `histories.py`, `filing.py`, `matrix.py`, `estimands.py`,
`membership.py`, `runner.py`, `invented.py`, `protocol.py`, `structural.py`,
`manifest.py` and `structural_inputs.py`.

New entry scripts: `scripts/track_a_v2_dry_run.py`,
`scripts/track_a_v2_registered.py`, `scripts/track_a_v2_structural_count.py`
and `scripts/track_a_v2_hash_manifest.py`.

New test package: `tests/track_a_v2/` contains `__init__.py`, `_invented.py`,
`test_benefits.py`, `test_histories.py`, `test_filing.py`,
`test_matrix_estimands.py`, `test_membership.py`, `test_cross_cutting.py`,
`test_runner.py`, `test_runner_contract.py`, `test_protocol.py`,
`test_structural.py`, `test_structural_inputs.py`, `test_manifest.py` and
`test_dry_run_protocol.py`.

This report, `urban2010_track_a_v2_invariants.md` and
`urban2010_track_a_v2_reads.txt` are the three new delivery records under
`docs/design/`.

Supporting changes are limited to the historical-source exclusion registry
in `scripts/first_estimates_birth_evidence.py`, its reachability assertions in
`tests/estimates/test_birth_evidence_artifact.py`, the legacy convention pin
in `tests/ss/test_statutory_aime.py`, and the recollected tier documentation.
No protected v1 module, engine loop/steps, gate or committed run was edited.

| Specification | New implementation | Invented tests |
|---|---|---|
| §3 | `runner.py`: one ensemble, baseline schedules, exact slice hashes | `test_runner.py`, `test_cross_cutting.py` |
| §4 | `benefits.py`, `histories.py`: DI-only levels, proxies, S1–S6/O1–O5, isolated caches | `test_benefits.py`, `test_histories.py` |
| §5 | `filing.py`, `benefits.py`: immutable H, gates, ordering, fixed reform application | `test_filing.py`, `test_cross_cutting.py` |
| §6 | `manifest.py`, `protocol.py`: immutable specification and source provenance; no outcome selection | `test_manifest.py`, `test_protocol.py` |
| §7 | `estimands.py`: A7 normalization, R/U definedness, draw summaries and family splits | `test_matrix_estimands.py` |
| §8 | `matrix.py`: exact order, components, labels and two fixed headlines | `test_matrix_estimands.py`, `test_runner.py` |
| §9 | `membership.py`, `runner.py`: unfiltered R checks and exact F/U guards | `test_membership.py`, `test_runner_contract.py` |
| §10 | `runner.py`, `protocol.py`: six stages, joint stop and cumulative counters | `test_runner.py`, `test_runner_contract.py`, `test_protocol.py` |
| §11 | `protocol.py`, three frozen-entry/manifest scripts | `test_protocol.py`, `test_manifest.py` |
| §12 | all new calculator/reporting modules | all `tests/track_a_v2/test_*.py` |
| §17 | invented dry-run script, manifest generator, frozen entry points | `test_runner.py`, `test_manifest.py`, `test_structural.py`; 20-draw dry run |

## Invariants

The complete test-function docstring inventory is in
[urban2010_track_a_v2_invariants.md](urban2010_track_a_v2_invariants.md).
It includes:

- E/N/indexing formulas, N between 2 and 35, highest-N selection, ties, zero
  padding, dollar and dime floors, inclusive eligibility cutoff and unchanged
  results from later earnings.
- Zero histories remain zero; larger retained earnings cannot lower AIME;
  smaller selected-year counts cannot lower the highest-year average;
  D AIME is at least legacy AIME for identical cutoff/indexing, equal at N=35.
- Continuous event/state agreement, overwritten-award detection, no recovery
  or unsupported conversion accepted, and no combined death/DI helper call.
- DI conversion retains its PIA; ordinary retirement/death levels and intact
  opening amounts are unchanged; linked and own DI offsets reconcile.
- H is fixed across scenarios and mechanisms; null claims use scheduled
  conversion; latest-date gates and exact moved months apply; unsupported
  orderings and earlier spells refuse; own DI stays unreduced.
- Own plus auxiliary accounting, nonnegative components, no duplicate own
  payment, null-reform identity and C0 individual nonincrease.
- DS combines D levels and S timing; worker-only estimates, draw SDs and
  sampling floors satisfy S=L and DS=D; cache and computation ordering
  cannot change benefits.
- Exact v1 L replay; D configured with legacy computation equals L; full
  parameter and history cache separation; all projection slices unchanged.
- Both R membership directions are checked before filtering; only the exact
  L/D legacy C0 predicate is admitted; S/DS and F6 receive no exception;
  C1/C2 differences are counted; dime-floor differences still refuse.
- U/R zero and denominator definedness, arithmetic draw means/sample SD,
  undefined draws propagated, undefined split seeds excluded, fewer than two
  usable seeds undefined, and no pooled-ratio substitution.
- U equals the all-alive mean ratio and tolerates added double zeros;
  mismatched persons, weights and fixed metadata refuse.
- Frozen 68-row order/headlines, deterministic row-order behavior, every
  refusal preceding tabulation, and retention of all uncomputed rows/counters.
- D/Track M differential uses the difference of floored averages and only
  aligned eligibility years; positive displacement can round to zero;
  post-62 raw awards keep their distinct cutoff and bend-point years.
- Frozen preflight exactness, source integrity, exclusive artifacts,
  deterministic manifests, and strictly unweighted permitted structural
  outputs, with no benefit or tabulation calls.

## Conservative readings

1. §3.2 does not define unknown extension scalars: serialization refuses them
   instead of hashing a lossy representation. Supported floats use exact hex.
2. §4.4 does not define proxy deduplication: benefit counters count requests
   per row/scenario, including cache hits; history counters deduplicate each
   person/eligibility within a draw. Label-only inherited rereads are uncounted.
3. §4.6 event/state integrity checks every intermediate persistent date field,
   not only final dates, refusing an inconsistency later overwritten.
4. §4.3 assumes fixed birth/history. Cache namespaces additionally bind both,
   preventing leakage across invented cohorts sharing a cache.
5. §5.4's earlier-spell refusal applies on reaching S spouse scope before
   link/payment gates. Its amount-stage restriction applies to ordering-class
   counters. Structural counts follow the same boundary.
6. §7.2 names person/weight mismatch: paired birth-year and family metadata
   mismatches also refuse because these define cells and split units.
7. §7.2 requires empty cells undefined: the adapter supplies empty normalized
   arrays when A7 would reject an empty table, and preserves missing draws as
   undefined instead of adding people or dropping draws.
8. §10 does not specify simultaneous-failure ties: membership uses ascending
   draw and string person ID for reproducible first-failure selection.
9. §7.3 does not separately specify the family universe for S/DS worker-only
   floors. To satisfy §§9/12.9's explicit identities while retaining exact L
   replay, S/DS use the corresponding L/D worker-only floor inputs. Positive
   selected-worker person-draw amounts, weights and fixed metadata are checked
   before tabulation. The inherited split algorithm and seeds are unchanged.
   An executed counterexample with an added spouse-only family exposed the
   need for this rule; the earlier point-estimates-only reading was withdrawn.
10. §§11/17 prescribe no transport schema: frozen entry points require a
    canonical protocol digest, complete frozen package, coverage of every v2
    implementation module and entry script, and explicit input roots
    (`src/populace_dynamics/track_a_v2/protocol.py:232`). Runtime validation
    requires equality of loaded source/parameter identities
    (`src/populace_dynamics/track_a_v2/protocol.py:74`).
11. §17.6 and Appendix B distinguish records from archived bytes: historical
    POMS hashes remain provenance marked not independently rehashed. Supplied
    source bytes must match the pins. Registered manifests require the actual
    statute bytes; invented manifests can retain its source record
    (`src/populace_dynamics/track_a_v2/manifest.py:185`).
12. §16.7 does not define count deduplication: D-unsupported, S-earlier-spell
    and opening proxies are distinct person-draw counts; ordering classes
    retain row/scenario detail. Units are explicit in structural output.
13. [Max's d603 ruling](urban2010_track_a_v2_rulings.md) clarifies §16.7's
    restriction as an output boundary. The structural entry uses the identical
    engine/modules, including weighted DI transitions, omitting weighted
    diagnostics in the v1 wrapper
    (`src/populace_dynamics/cola_track_a/runner.py:624`).
    New input preparation also omits A3/A5 summaries
    (`src/populace_dynamics/cohorts/psid2010.py:1342`,
    `src/populace_dynamics/cohorts/psid2010.py:2166` and
    `src/populace_dynamics/cola_track_a/opening.py:599`). Existing SS helpers
    select or copy observed amounts
    (`src/populace_dynamics/cohorts/psid2010.py:1638` and
    `src/populace_dynamics/cola_track_a/opening.py:364`); input preparation
    calculates no scenario benefit. Weighted arithmetic inside the engine is
    unchanged. Real structural execution requires its own frozen protocol and
    pre-execution record; development runs use invented inputs only.
14. §17's complete invented fixture deliberately uses zero recovery to supply
    supported continuous spells. Separate intended violations exercise
    refusals; registered inputs are never changed to obtain completion.
15. Invented test ensembles may use fewer draws. Registered execution requires
    all twenty draws and the frozen split/matrix protocol.
16. §10 does not define person attribution for a whole-slice hash mismatch.
    Report the first mismatching draw and a null person, instead of inventing
    a person identity. Hash each mechanism as required by §3.2, but raise its
    mutation refusal at step 4 after all step-3 checks.
17. §17.4 does not authorize overwriting invented attempts. The dry-run entry
    reserves a new output directory, retaining returned attempts before
    checking expected completion/refusal and retaining unexpected failures.
18. §17.6 does not define source edits during an invented run. The dry-run
    entry records the implementation at start and refuses a manifest if any
    implementation file is added, removed or changed during execution.
19. §11 requires binding the structural check if authorized, and §16.7 records
    that authorization. Registered preflight therefore requires the prior
    frozen protocol, attempt and permitted counts; an explicit declaration
    that the check was not performed refuses. The specification does not
    require the prior check to share the outcome implementation commit. Its
    historical protocol and artifact are bound by their hashes rather than
    replaying their preflight against the current checkout
    (`src/populace_dynamics/track_a_v2/protocol.py:109`). Both binding and
    emission enforce the exact structural artifact schema, including attempt
    metadata and count units
    (`src/populace_dynamics/track_a_v2/structural.py:294`).

## Exposure and reads

The complete inspected-path ledger is
[urban2010_track_a_v2_reads.txt](urban2010_track_a_v2_reads.txt).
All agents read the binding common rules, restricted-file list and full
ratified specification. Public hypothesis passages in that specification and
A1/E1 design excerpts were seen. E1 membership-discussion excerpts and the
existing invented tests' introductory diagnostic discussion were inspected.
The public T/F/P memos, scorecard, restricted comparator files, underlying
real-data diagnostic records and raw population files were not opened.
No earlier-session exposure is known within this job.

Existing unit-test exposure additionally includes the public SSA illustrative
Case A/B transport fixtures and the reviewed Axiom binding's source,
artifact and provenance files. The helper reads the source transport at
`tests/test_axiom_benefit_bridge.py:1063`. The binding checks every pinned
file at `src/populace_dynamics/axiom_benefit_bridge.py:955`, and its changed
external provenance receipt caused refusal at line 987. The execution
boundary at line 1316 occurs before the engine call at line 1325. The exact
Case B test was replayed once to isolate that refusal; it did not invoke the
engine. No external pin, receipt, source or artifact was changed. These SSA
illustration files are not listed as restricted comparator files in the
binding restricted-file index; no phase-2 comparator was opened or used.

## Validation and remaining execution prerequisites

Final command summaries and dry-run head are recorded below. Initial failures
were fixture setup errors, a pytest filename collision
resolved by a test-package initializer,
and minimized Hypothesis timing fluctuations. Timing deadlines were disabled
for affected new properties; no arithmetic counterexample was discarded.

This job does not post issue #42 registration, prepare participant forecasts,
run a real structural check or outcome exercise, publish CI evidence, recheck
seals or produce a comparison memo. Those remain subsequent §17 prerequisites
and are outside this invented-data implementation assignment.

The original implementation refused structural execution pending a ruling on
weighted projection arithmetic. [Max's d603 ruling, 2026-09-28](urban2010_track_a_v2_rulings.md)
resolved that question: weighted transitions run unchanged, and the §16.7
restriction applies to the pre-registration check's outputs. The script,
loader and structural runner no longer impose that refusal. The projection's
weighted expected-death aggregates and diagnostic totals remain unchanged
(`src/populace_dynamics/engine/di_entitlement.py:690–717`); structural artifacts
emit only D-unsupported histories, S ordering classes, S-refused earlier
spells and opening-proxy applications, with protocol/attempt metadata.
They emit no benefit amounts, weight sums, weighted totals or tabulations.
The count-only output restriction does not prohibit registered weighted
estimates or budget totals.

The separate protocol/hash preflight, explicit authorization, input bindings
and exclusive attempt record remain required before a real structural run.
Preflight hash verification can read frozen source files; no real preflight,
population load or structural execution was performed for the d603 change.
Invented end-to-end projection and output-schema tests cover the newly
reachable path. The validation and exposure records below describe the
original implementation and are preserved as historical records.

Final new-suite validation completed:

```text
.venv/bin/python -m pytest tests/track_a_v2 -q --basetemp=.cache/a2-release-new-temp
456 passed in 148.25s (0:02:28)
Black: 32 files would be left unchanged.
Ruff: All checks passed!
Historical-source checks: 7 passed, 6 deselected in 67.02s (0:01:07)
```

The source pin/new-history subset also passed (3 tests). Focused final suites
passed 99 calculator/history/filing, 285 reporting/runner, 55 protocol/structural
and 12 dry-protocol cases. Tier recollection records 4,120 unit, 3,152 artifact,
930 integration, 520 legacy reproduction and 182 oracle tests, 8,904 total.

An earlier new-suite pass covered 418 cases before final audit additions. A
later full new-suite run exposed 12 fixture-path failures, with 444 passes.
The fixture placed output outside its mocked allowed root when pytest used a
workspace-cache basetemp. The minimized fixture was corrected without relaxing
the production guard; the final 456-case run above passed.

Two unit-tier executions were deliberately stopped as audit changes and then
that fixture correction were frozen: 1,469 passed/4 skipped and 112 passed,
respectively. Neither had a test failure before interruption. A third full
execution was stopped after an existing C2ST test took over eight minutes
and another native-threaded fit stalled. Its exact summary was
`1 failed, 1508 passed, 4 skipped, 4784 deselected, 1 warning in 1770.07s (0:29:30)`.
The failure was the existing subprocess timeout described below. The isolated
C2ST test passed with six native thread limits set to one:
`1 passed in 11.40s`. The final unit execution uses those limits with
the corrected, frozen source and tests; no estimator, fixture or assertion
was changed to improve timing.

The six limits are `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS` and
`OMP_THREAD_LIMIT`, each set to `1`. The temporary `a2_recount` pytest plugin
recollects the complete tier inventory and records test progress; it changes
no test selection, fixture or assertion. Host load exceeded 180 during the
final run. After 37:58, its passing prefix was retained and its remainder
scheduled in three disjoint shards to complete validation under that
contention. The prefix contains 1,602 passes and four skips; each remaining
shard contains 838 tests. The temporary `a2_unit_shard` plugin checks the
identical 4,120-test collection before selecting its portion. The interrupted
test starts the remainder; no test is omitted. A separate verifier checks
every finished node ID, each shard exit status and exact once-only coverage.
This scheduling changes neither test bodies nor acceptance criteria. Pytest's
progress percentages retain the pre-shard denominator; finished node IDs and
final summaries establish coverage.
The completed inventory accounts for **3,983 passed, 131 skipped and six
failed**, exactly 4,120 unit tests. Its exact pytest summary lines are:

```text
1602 passed, 4 skipped, 4784 deselected in 2278.04s (0:37:58)
1 failed, 795 passed, 42 skipped, 8066 deselected in 5870.18s (1:37:50)
2 failed, 794 passed, 42 skipped, 8066 deselected in 5820.32s (1:37:00)
3 failed, 792 passed, 43 skipped, 8066 deselected in 7114.85s (1:58:34)
```

`.cache/a2-unit-completion.json` verifies exact, nonoverlapping coverage and
records `all_passed: false`. An independent per-node progress audit in
`.cache/a2-v2-unit-status.json` verifies that all 456 new v2 tests also passed
once in this unit execution, with no skips. The six failures were:

- `tests/test_axiom_benefit_bridge.py:782`: the invented executable fake
  engine exceeded its existing 60-second timeout; the bridge reports
  `AxiomExecutionError` at `src/populace_dynamics/axiom_benefit_bridge.py:1329`.
- `tests/test_axiom_benefit_bridge.py:1096` and `:1143`, and
  `tests/test_track_c_aime_agreement.py:1113`: Case A, Case B and the invented
  Track C career test refused the changed external engine provenance-receipt
  hash at `src/populace_dynamics/axiom_benefit_bridge.py:987`, before engine
  invocation. The single exact Case B replay reproduced that refusal:
  `1 failed in 850.29s (0:14:10)`.
- `tests/test_m6_accounting_history.py:303` and
  `tests/test_m6_stock_flow.py:753`: the existing process-pool refusal tests
  exceeded `future.result(timeout=120)` and raised `TimeoutError`.

All four containing test files are byte-identical to the base commit. These
are unresolved failures in unchanged tests, not claimed arithmetic bugs or
waived acceptance checks. Host load reached approximately 294; no existing
timeout, test assertion, engine pin or external provenance file was changed.
No further actual-engine replay was attempted after isolating the pin refusal.

A separate Polars-thread hypothesis was ruled out because Polars is
not installed; its diagnostic subprocess was stopped during imports, before
test collection, and made no test or source changes.

An earlier invented full dry run was superseded and interrupted during benefit
construction (step 3), with all 68 rows uncomputed. Its pre-fix handler lost
in-memory counters; `.cache/a2-superseded-attempt.json` records that limitation
without reconstructing amounts or counts. This exposed a missing
`KeyboardInterrupt` handler. The follow-up preserves partial attempts for
keyboard interruption and unexpected infrastructure exceptions, with focused
invented regression tests. No parameter or row choice was based on outputs.

A subsequent 20-draw development run completed all 68 rows and the step-2
forced refusal. It overlapped audit edits, so its completion-time manifest
does not prove the loaded implementation and is explicitly superseded.
`.cache/a2-development-attempts.json` records these attempts and the one-draw
integration exercise. The final dry run reserves a distinct directory and
checks unchanged implementation hashes before publishing its manifest.

Final invented execution:

```text
.venv/bin/python -u scripts/track_a_v2_dry_run.py --output-dir .cache/track_a_v2_frozen
INVENTED DATA - NOT A COMPARISON
registered, one-shot, post hoc, not blind
PSID-seeded closed cohort; Python oracle (not Axiom)
68 tabulations; 5 age cells each; 20 shared invented draws
Fixed headlines: D×R0 and D×F0
Forced refusal: step 2; 68 uncomputed rows; no tabulations
```

Independent artifact verification passed: exact row/age/draw order and seeds,
unchanged projection hashes after each mechanism, exact worker-only means/SDs/
floors, the step-2 refusal, all output headings, and manifest/source-byte identity.
The generated manifest SHA-256 is
`61717a68141e54abe61d5d338e02a0dab7436cc46a9d77d6a63dd790f99668c3`;
the result SHA-256 is
`bd5842138faf26f0c3ce4736f400f5df4247891ec1475efcb48cb49d87921aec`.
These were calculated by `.cache/a2_verify_final_dry.py`, not entered into the
manifest by hand. Final artifacts are under `.cache/track_a_v2_frozen/`.

The full unit run exposed an existing sealed-rehearsal timeout. Its unchanged
test sets a 60-second subprocess limit
(`tests/estimates/test_anchor_context_rehearsal.py:389`). The isolated module
reproduced it: `1 failed, 20 passed in 164.75s (0:02:44)`. The same unchanged,
invented fixture-only child completed with a 300-second diagnostic limit in
96.36 seconds: return code 0, all five checks passed, empty stderr and an empty
sentinel. The inspected test, launcher and ceremony files match base commit
`d978d966270f`; no unrelated code or timeout was changed. Evidence is retained
in `.cache/a2-existing-rehearsal-diagnostic.json`.

## Delivery

Shared Git metadata was not writable. The coherent implementation and report
commits therefore use workspace-local Git metadata at `.cache/a2-git`, branch
`dynamics-a2-impl-20260928`. Each commit uses `--no-verify` and ends with the
requested co-author trailer. Nothing was pushed or history-rewritten.

The delivery bundle is `a2-impl.bundle` in the workspace root, with prerequisite
base commit `d978d966270f22569692c4f47d6ebe204c08284d`. The finalization utility
checks clean committed state, unchanged protected paths and every trailer,
then verifies the bundle, fetches it into separate local Git metadata and
checks object connectivity. The final commit SHA and verification result are
recorded in `.cache/a2-bundle-verification.json` after this report is committed.
The generated dry-run artifacts and detailed command logs remain in `.cache/`;
the bundle contains the committed implementation, tests and delivery records.
