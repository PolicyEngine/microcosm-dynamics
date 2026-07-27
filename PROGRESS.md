# Progress

## State

The resolver now aborts unless every selected value coordinate resolves to a
physical 1x1 data cell. The exact re-pinned 6.A1 2015 colspan-collapse attack
passes its fail-closed regression test after failing pre-fix with
`Failed: DID NOT RAISE <class 'ValueError'>`.

## Done

- Read the extraction referee report in full.
- Confirmed finding 1: span expansion can let two logical value coordinates
  resolve to one physical `td`.
- Confirmed finding 2 is fixed by coordinator commit `b3c51f4`.
- Added the exact attack using the referee's replacement and pinned its
  attacked snapshot SHA-256 (`94e78a97...`).
- Re-pinned the prospective capture manifest itself to SHA-256
  `fa9a2cdc...`.
- Captured the pre-fix targeted pytest output: one test failed because the
  full build accepted the attack.
- Added the selected-value-cell 1x1 invariant; the targeted attack test now
  passes.

## Next

- Run Black, Ruff, the relevant test tier, and byte-identical artifact checks.
- Commit each coherent step, push, and write the final lane report.
