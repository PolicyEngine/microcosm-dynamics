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
- Limited the authenticated PSID role-map replacements to V-B5/V-B6/V-B8,
  retained the base V-B1/V-B4 legal authority, limited serialized PSID
  source rows to those three claims, and froze the other claims' source-row
  and disposition domains as explicitly empty rather than unmatched.
- Bound every adjudication's namespace roots to its already existing
  first-add parent, reserved the later receipt parent for newly constructed
  receipt-phase projections, and prohibited any artifact/self-commit edge.
- Replaced final-configuration hashes inside receipt-core namespace scans
  with pre-reference configuration-core hashes, moved full-SHA paths to an
  outer post-reference scan, and froze a 12-step acyclic construction order.
- Re-derived the original appendix corpus as 2,187 pre-§16 atoms, 693
  candidates, 65 overlaps, and 628 introduced tokens; added the ten omitted
  terminal-colon prefix rows with exact definitions, positions, and hash.

## Next

- Validate the complete amendment, re-review the dependency graph, and
  finalize the progress ledger and report.
