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
- Bound the six non-PSID base V-B results to the existing four-projection
  historical-rules identity verifier, carried that projection in v2
  adjudication-verifier preimages and v3 noncapture evidence, and replaced
  the conflicting source-projection status order with one total construction.
- Split the branch-total seven-key namespace core from the selected-only
  configuration core, froze adjudication-to-receipt core/history equalities,
  serialized the receipt-time calibrated scan as acceptance evidence, and
  replaced the chronology with a complete selected-only 12-step order.
- Closed each V-B legal-binding digest equation and overrode the outer
  V-B1/V-B4 availability mapping so inherited methodology availability is
  authenticated lineage evidence but never substantive legal authority.
- Added the missing calibrated registration filename grammar, complete
  Tree(X) history/least-absent suffix projection, namespace-preimage binding,
  and exact B-star/J equality.

## Next

- Validate the complete amendment, re-review the dependency graph, and
  finalize the progress ledger and report.
