# Amendment 2, round 8 progress

## State

Active on `claude/ce-design-amendment2` from
`c036a56abf60dadb410ca3e6ed8d28f0907e85e3`. The round-6 document is
19,612 lines. All design changes in this round will be appended after that
byte-for-byte preserved prefix. Work is in progress on the four critical
round-7 findings and the ratification-blocking namespace sweep gap.

## Done

- Confirmed the requested branch, clean worktree, and starting commit.
- Confirmed the existing progress ledger and the prior report-removal commit.
- Started independent read-only analyses of the V-B predicates and authority
  maps, the namespace/receipt dependency graph, and the closure sweep.
- Defined cross-registry equality as complete deep equality between each
  branch's own spec/result arrays and the corresponding named source-row
  projections, plus complete cross-branch equality at the eight shared claim
  positions, with explicit envelope statuses and construction order.

## Next

- Restore the base-design V-B1/V-B4 authorities and close the authenticated
  source matching semantics.
- Replace the future namespace parent with phase-correct existing commits.
- Cut the receipt/configuration digest cycle and state one total construction
  order.
- Add the ten omitted namespace-prefix atoms, regenerate the table and totals,
  and validate the complete amendment.
