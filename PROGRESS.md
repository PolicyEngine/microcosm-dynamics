# Benchmark harness round 2 progress

## State

All six verdict edits are implemented. A full-suite compatibility failure in
the append-mostly reorder diagnostic is fixed and passing its targeted gate.

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

## Next

1. Rerun format, lint, builder, tier-sync, and full benchmark gates.
2. Record final artifact hashes and commit inventory, then remove this ledger.
