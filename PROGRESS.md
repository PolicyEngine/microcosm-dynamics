# Benchmark harness round 2 progress

## State

All six verdict edits and the diagnostic compatibility follow-up are complete.
The full final gate matrix is green; only ledger removal and the external final
report remain.

## Done

- Confirmed the requested branch, worktree, and clean starting state.
- Recorded all six required edit groups and their named regressions.
- Confirmed that no pull-request actions are authorized.
- Froze the merged matrix's exact 42-row ID prefix.
- Scoped historical Mermin partition and locator rules to that prefix.
- Decoupled legacy reconstruction from later verified and unverified rows.
- Decoupled the registry generator's frozen matrix and seed census from the
  live append order while preserving current registry bytes.
- Added stable `b102e6fe...` round-trip regressions for both 43rd-row cases.
- Passed the targeted benchmark tests, Ruff 0.15.0, Black 25.11.0, and
  Black 26.5.1 for the touched Python files.
- Replaced preliminary prose matching with a closed status enum resolved from
  SHA-pinned accepted publisher observations.
- Added missing-marker, false-marker, and negated-prose regressions while
  retaining the existing structured-positive SSA case.
- Split staged append preflight from committed builder/CI artifact checks.
- Made both Git paths literal, NUL-delimited, exact-cardinality, returned-path
  checked, and bound to the selected blob's exact bytes.
- Added staged-new, staged-modified, and literal-wildcard regressions.
- Bound the retained legacy label note to deterministic prose derived from the
  SHA-verified per-row embedded-array result.
- Added a public append-check regression for fabricated label prose.
- Required exact public history keys before loader offset injection and exact
  public-or-paired-offset shapes in the in-memory validator.
- Added public `_foo`, `_byte_start`, and `_byte_end` rejection regressions.
- Moved rollback-size capture after acquisition of both append locks.
- Added a two-process regression where appender 2 fails after writing and must
  preserve appender 1's successful bytes.
- Preserved the established append-mostly reorder diagnostic by checking the
  prior row-ID prefix before standalone frozen-prefix validation of the new
  registry.
- Passed the targeted compatibility test plus Ruff 0.15.0, Black 25.11.0, and
  Black 26.5.1 on the follow-up schema change.
- Passed the full benchmark module: 9 tests.
- Passed tier-manifest synchronization: 1 test with 4,479 deselected from the
  4,480-item collected suite.
- Passed registry, history, and wall builders with `--check` under normal and
  optimized Python, plus an optimized loader/validator smoke check.
- Passed Ruff 0.15.0 and both Black 25.11.0 and 26.5.1 on all four touched
  Python files.
- Confirmed the registry, history, run manifest, wall, and seed-run artifact
  bytes are unchanged from `9204bfa`; no pin advancement is required.
- Confirmed the cumulative diff is whitespace-clean and reviewed the ordered
  commit subjects and full SHAs.

## Next

1. Commit these final verification results.
2. Remove this ledger in the final tree-cleanup commit.
3. Write the final closure report outside the worktree.
