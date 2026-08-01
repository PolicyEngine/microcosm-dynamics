# Benchmark harness round 2 progress

## State

Edits 1 through 4 are implemented. Evidence-bound label-note validation is
under its final public-check, targeted, and lint gates.

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

## Next

1. Enforce exact public and internal history key shapes.
2. Move rollback-size capture under both append locks.
3. Run format, lint, targeted, builder, tier-sync, and full benchmark gates.
