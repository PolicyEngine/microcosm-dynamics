# Benchmark harness round 2 progress

## State

Implementation is starting from clean HEAD `9204bfa` on
`claude/benchmark-harness`. The round-two verdict has been read in full.

## Done

- Confirmed the requested branch, worktree, and clean starting state.
- Recorded all six required edit groups and their named regressions.
- Confirmed that no pull-request actions are authorized.

## Next

1. Freeze and decouple the 42-row legacy migration prefix.
2. Replace prose-based preliminary-source detection with structured evidence.
3. Split index-bound append preflight from HEAD-bound committed checks.
4. Bind label prose to the evidence-backed array result.
5. Enforce exact public and internal history key shapes.
6. Move rollback-size capture under both append locks.
7. Run format, lint, targeted, builder, tier-sync, and full benchmark gates.
