# Amendment 2, round 8 progress

## State

Complete on `claude/ce-design-amendment2`, based on
`c036a56abf60dadb410ca3e6ed8d28f0907e85e3`. The round-6 document is
19,612 lines. The final document is 20,953 lines, with all 1,341 round-8
lines appended after that byte-for-byte preserved prefix. All four critical
round-7 findings and the ratification-blocking namespace sweep gap are
closed.

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
- Received independent PASS dispositions for findings 1–2, findings 3–4,
  and the corrected closure sweep after the final controlling clauses.
- Confirmed the original 19,612-line prefix still has SHA-256
  `6e3397901475fc66d2e2d69bd0f2dc72598d63afeb7e6211b9af0f74a8e4aeb7`
  and byte-equals the document at `c036a56`.
- Confirmed the final 20,953-line document has SHA-256
  `5c6d9a0e215438936127babce86ec54bfee7d283b572b3200ec5bfd94d656602`,
  all 53 §16 JSON fences strict-parse without duplicate keys, and
  `git diff c036a56 --check` passes.
- Confirmed the corrected sweep remains 628 distinct byte-sorted tokens with
  LF-list SHA-256
  `1b6e24552a42240aa952e73a3e313977ef60c139c4827c1c61a428be659aab7b`.
- Ran `pytest -q tests/test_forecast_ledger.py`: 5 passed. The full suite
  remains unavailable in this checkout because collection raises 73
  `ModuleNotFoundError: populace_dynamics` errors before tests run.

## Next

- No round-8 design work remains. Hand off the committed branch for
  ratification review; do not push.
