# P2 execution change, disclosed

The supplied environment description calls `.venv-p2/bin/python` CPython
3.14.4. During the first recovery run, pytest reported that this exact
interpreter is CPython 3.14.7. The requested path was used throughout;
nothing was installed or upgraded. No alternative interpreter was chosen.

Thus the environment cannot be described as the stated CPython 3.14.4.
The execution change is use of the supplied `.venv-p2/bin/python` at its
actual version, 3.14.7, with its existing pinned packages. Every fixture,
seed, panel size, estimator, criterion and tolerance remains unchanged.
This discrepancy was discovered after the initial regression and recovery
runs had begun; this note was written immediately upon discovery, before
any further commands were run. Exact equality checks compare objects in
that same supplied environment.

The initial exact-test run also exposed an implementation bug in P2's
signature serializer (`vars()` on a slots-based marginal object). Explicit
field serialization repaired that bug without changing the specification
or any test fixture or criterion. Its result was 2 failed, 19 passed,
46 deselected; the failed tests were the full-pair/initialization test and
the non-gate isolation test. These were implementation failures, rather
than a change to the declared test procedure.

Amendment 1's direct-law T4 reference is part of the supplied specification.
It is not an additional execution change. Gate recovery uses the actual
P2 gate-view constructor and pinned estimator, as prescribed. No full-law
refit is substituted for the specified conditional gate experiments.

A delegated audit initially used system `python3` for byte comparisons and
AST inspection only. That departed from the requested interpreter/thread
house rule; it performed no fitting or simulation and read no data. Those
guard and AST checks were repeated with `.venv-p2/bin/python` and all six
thread variables for the final evidence. Every fit, projection and pytest
run used the specified interpreter path and thread environment.

The complete initial exact suite finished with `1 failed, 67 passed in
2550.01s (0:42:30)`. The sole failure was
`test_t1_history_encoding_property`: Hypothesis reported
`DeadlineExceeded: Test took 284.12ms, which exceeds the deadline of
200.00ms`. This is Hypothesis's unfrozen default runtime deadline, not a
failed feature/history invariant or a frozen numerical criterion. All
other exact cases completed successfully, including all paths, restarts
and future-input perturbations. The repair disables only that runtime
deadline (`deadline=None`); the property, input strategy, default example
count, fixtures, seeds and every numerical criterion remain unchanged.
The complete original failure traceback is retained in
`/private/tmp/p2-exact-full.log`. This note precedes the repaired test run.

The first T4 mutation execution exited 1 with `ValueError: forward
earnings selected an empty donor pool`, before its designated neutrality
assertion. Forcing first-step missing-history nonparticipation creates a
later re-entry on an all-positive fixture that has no re-entry donors.
This run is retained as an unsuccessful mutation check and is not counted
as the required designated-assertion failure. The test execution order is
repaired to check P2's effective probabilities and signs on the independent
direct-reference query frames before generating its complete path. Thus
the frozen missing-history mutation reaches the prescribed first-step
sign assertion. The same fixture, roots, complete-path comparison and all
exact criteria are retained; the failed mutation execution is disclosed.

The repaired mutation rerun reached that designated assertion and finished
with `1 failed in 48.82s`, exit code 1. Its exact command, replacement,
failed test ID, log and restored-source hash are retained in
`track_b_p2_mutations.json`. The initial unrelated refusal remains in the
ledger with `designated_check_failed: false`; it is not counted among the
14 required successful mutation checks.

### Original exact-suite output, unchanged

```text
bringing up nodes...
bringing up nodes...

..................F.................................................     [100%]
=================================== FAILURES ===================================
______________________ test_t1_history_encoding_property _______________________
[gw0] darwin -- Python 3.14.7 /Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/.venv-p2/bin/python
  + Exception Group Traceback (most recent call last):
  |   File "/Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/tests/test_forward_earnings_p2_exact.py", line 508, in test_t1_history_encoding_property
  |     st.one_of(
  |     
  |   File "/Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/.venv-p2/lib/python3.14/site-packages/hypothesis/core.py", line 2294, in wrapped_test
  |     raise the_error_hypothesis_found
  | hypothesis.errors.FlakyFailure: Hypothesis test_t1_history_encoding_property(history=5.109342075247125e+16) produces unreliable results: Failed on the first call but did not on a subsequent one (1 sub-exception)
  | Failing test case: test_t1_history_encoding_property(
  |     history=5.109342075247125e+16,
  | )
  | Unreliable test timings! On an initial run, this test took 284.12ms, which exceeded the deadline of 200.00ms, but on a subsequent run it took 23.15 ms, which did not. If you expect this sort of variability in your test timings, consider turning deadlines off for this test by setting deadline=None.
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "/Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/.venv-p2/lib/python3.14/site-packages/hypothesis/core.py", line 1222, in _execute_once_for_engine
    |     result = self.execute_once(data)
    |   File "/Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/.venv-p2/lib/python3.14/site-packages/hypothesis/core.py", line 1160, in execute_once
    |     result = self.test_runner(data, run)
    |   File "/Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/.venv-p2/lib/python3.14/site-packages/hypothesis/core.py", line 827, in default_executor
    |     return function(data)
    |   File "/Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/.venv-p2/lib/python3.14/site-packages/hypothesis/core.py", line 1117, in run
    |     return test(*args, **kwargs)
    |   File "/Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/tests/test_forward_earnings_p2_exact.py", line 508, in test_t1_history_encoding_property
    |     st.one_of(
    |     
    |   File "/Users/maxghenis/PolicyEngine/_trackb-p2-dev/microcosm-dynamics/.venv-p2/lib/python3.14/site-packages/hypothesis/core.py", line 1049, in test
    |     raise DeadlineExceeded(
    |         datetime.timedelta(seconds=runtime), self.settings.deadline
    |     )
    | hypothesis.errors.DeadlineExceeded: Test took 284.12ms, which exceeds the deadline of 200.00ms. If you expect test cases to take this long, you can use @settings(deadline=...) to either set a higher deadline, or to disable it with deadline=None.
    +------------------------------------
=========================== short test summary info ============================
FAILED tests/test_forward_earnings_p2_exact.py::test_t1_history_encoding_property
1 failed, 67 passed in 2550.01s (0:42:30)
```

### Exact-contract rerun after the deadline-only repair

The final exact test source disables only Hypothesis's unfrozen per-example
wall-clock deadline. Its strategy, default example count, assertions, frozen
full-law fixtures, estimator seed, projection roots, and numerical criteria
are unchanged. No production source changed for this repair.

The test source additionally states the no-look-ahead comparison against a
nominal future-input baseline explicitly. Its helper verifies identical
serialized fitted-generator bytes, fit signatures, admitted raw rows, pairs,
gate view, and materialized state against the originally executed baseline.
The separate evaluation-truth comparison is expressed as `0` to `100`; the
original complete run compared absence of that unused column with `100`.
The generator selects only its fixed conditioning columns. These assertion
clarifications preserve the fitted state and all original random addresses;
the original complete generated-path comparisons remain applicable. The new
structural baseline assertion and all changed T1/T5/structural contract
assertions ran below. The final T4 and future-path run is recorded separately
below.

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest tests/test_forward_earnings_p2_exact.py -k 't1 or t5 or nominal_future_baseline' -p no:cacheprovider --basetemp=/private/tmp/p2-exact-final-contract -q
```

Final output, exit code `0`:

```text
........................                                                 [100%]
24 passed, 46 deselected in 50.02s
```

Formatting and lint of the final exact test source:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m black -l 79 tests/test_forward_earnings_p2_exact.py
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m ruff check tests/test_forward_earnings_p2_exact.py
```

```text
All done! ✨ 🍰 ✨
1 file left unchanged.
All checks passed!
```

### Initial checksum implementation repair

Before the complete exact run, the first T1/T5 check encountered an
implementation error while constructing P2's component checksum metadata:
`vars(cell)` was applied to v1's `CellMarginal`, which has `__slots__` and no
`__dict__`. Both affected tests stopped with the unchanged exception:

```text
TypeError: vars() argument must have __dict__ attribute
FAILED tests/test_forward_earnings_p2_exact.py::test_t1_full_pair_retention_and_first_step_initialization
FAILED tests/test_forward_earnings_p2_exact.py::test_t5_exact_all_non_gate_components
2 failed, 19 passed, 46 deselected in 58.95s
```

The command was:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest tests/test_forward_earnings_p2_exact.py -k 't1 or t5' -p no:cacheprovider --basetemp=/private/tmp/p2-exact-t1-t5 -q
```

The checksum implementation was repaired to enumerate the inherited marginal
fields explicitly. No law, fitted population, fixture, seed, estimator,
probability, or acceptance criterion changed. The full exact run above then
passed T1's pair/initialization assertions and T5's non-gate equality; the
final 24-case contract rerun also passed those tests and the strengthened
checksum assertions. This was an implementation repair, not an alternative
test procedure.

### Final T4 and future-path revalidation

After every mutation was restored and the final source formatted, the final
T4 assertion order and all six clarified future-input comparisons were run
end to end. The fixtures, estimator seed, all 20 roots, full paths and exact
criteria were retained:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest -n 4 -p no:cacheprovider --basetemp=/private/tmp/p2-exact-final-paths -q tests/test_forward_earnings_p2_exact.py -k 't4 or no_look_ahead' > /private/tmp/p2-exact-final-paths.log 2>&1
```

Final output, exit code 0:

```text
..........................                                               [100%]
26 passed in 7220.79s (2:00:20)
```

Together with the final 24-case contract/property/structural run and the 20
unchanged T6 clock/restart cases that passed in the original full run, these
results cover all 70 final exact cases. The five recovery cases passed in
their separate run. No single clean 70-case invocation is claimed, and no
failure in this document has been erased or reclassified as a pass.
