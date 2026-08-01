# Benchmark harness round 2 progress

## State

Edit 1 is implemented and verified. Work is moving to the structured
preliminary-source predicate.

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

## Next

1. Replace prose-based preliminary-source detection with structured evidence.
2. Split index-bound append preflight from HEAD-bound committed checks.
3. Bind label prose to the evidence-backed array result.
4. Enforce exact public and internal history key shapes.
5. Move rollback-size capture under both append locks.
6. Run format, lint, targeted, builder, tier-sync, and full benchmark gates.
