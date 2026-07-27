# Anchor context extraction revision 3 progress

## State

- In progress: translate every round-2 referee finding into an exact,
  executable revision of `docs/design/anchor_context_extraction.md`.
- Required branch `claude/anchor-extraction-design` is clean at requested
  starting HEAD `774e9549f69928b01223a65717e80bf807f80165`.
- The full 77-line referee verdict has been read through its final checks.

## Done

- Verified the published `runs/first_estimates_v1.json` bytes in the
  worktree equal `origin/master` and have the pinned SHA-256
  `719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977`.
- Confirmed its actual table inventory is
  `tables.modeled_award_flow`, `tables.opening_stock`, and `tables.revenue`,
  each with a 160-row `per_draw` grid over 20 draws × 8 years.
- Identified the six ranked findings and the registered-estimates incident
  schema assertions that finding 6 requires.

## Next

- Freeze and exact-validate the model metric and comparison registries.
- Correct OACT sequencing, mismatch inventory, schema-version law, and
  ceremony schemas.
- Validate the revised document finding-by-finding, commit with dispositions,
  remove this temporary ledger, push, and write the external handoff report.
