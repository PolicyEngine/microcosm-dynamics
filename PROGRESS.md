# Progress

## State

The exact 6.A1 2015 colspan-collapse attack is reproduced by an in-memory
prospective capture with its manifest entry re-pinned. Against the unmodified
builder, the regression test fails with
`Failed: DID NOT RAISE <class 'ValueError'>`, confirming the blocker.

## Done

- Read the extraction referee report in full.
- Confirmed finding 1: span expansion can let two logical value coordinates
  resolve to one physical `td`.
- Confirmed finding 2 is fixed by coordinator commit `b3c51f4`.
- Added the exact attack using the referee's replacement and pinned its
  attacked snapshot SHA-256 (`94e78a97...`).
- Captured the pre-fix targeted pytest output: one test failed because the
  full build accepted the attack.

## Next

- Require selected value coordinates to resolve to unique physical 1x1 cells.
- Run Black, Ruff, the relevant test tier, and byte-identical artifact checks.
- Commit each coherent step, push, and write the final lane report.
