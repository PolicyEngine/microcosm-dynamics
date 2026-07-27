# Progress

## State

The resolver now aborts unless every selected value coordinate resolves to a
physical 1x1 data cell. The exact re-pinned 6.A1 2015 colspan-collapse attack
passes its fail-closed regression test after failing pre-fix with
`Failed: DID NOT RAISE <class 'ValueError'>`. Implementation and scoped
validation are complete locally. Push is externally blocked: shell Git
cannot resolve `github.com`, and direct GitHub connector writes are canceled
before execution.

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
- Rebuilt the real artifact byte-identically: 87,432 bytes and SHA-256
  `adc782a1a11c50969103c125a82b1539a7017241662d545d86bc6fc9227730c1`,
  with no artifact diff.
- Black leaves both changed Python files unchanged; repository-wide Ruff
  passes.
- The complete anchor-builder module passes in the unit tier (`23 passed`);
  the full tier-policy inventory passes (`1 passed, 3680 deselected`).
- The full unit tier passes with sandbox-safe explicit core limits:
  `866 passed, 5 skipped, 2810 deselected` in 215.15 seconds.
- Attempted `git push origin claude/anchor-extraction-v1`; it failed at DNS
  resolution. GitHub connector upload attempts were canceled without remote
  mutation, and remote comparison confirms the branch remains at `b3c51f4`.

## Next

- From a network-enabled coordinator environment, push the committed range
  `b3c51f4..HEAD` on `claude/anchor-extraction-v1`, then hand the evidence
  back to the extraction referee.
