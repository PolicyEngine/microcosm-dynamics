# Anchor context extraction revision 3 progress

## State

- Revision 3 is complete and committed locally as `e1e4b5e`.
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
- Resolved the exact seven-entry model metric registry against the artifact's
  literal `per_draw` arrays and verified all nine operand selectors across
  160 rows.
- Froze the intended nine-entry comparison registry, including the two
  explicitly unavailable entries, the exact OACT five-code mismatch law, and
  OASI cash's official-level-only status.
- Chose and documented the verdict's open implementation judgments:
  ratio-of-intensities operation, tagged nulls for unavailable official
  series, and Trustees covered workers as the OASDI cash denominator.
- Applied all six finding dispositions, including the exact configuration
  echo and incident schemas, in the document-only substantive commit.
- Parsed all frozen JSON registries, exact-checked their key sets and
  cross-references, revalidated every artifact pointer/value/unit label and
  the 160-row grids, confirmed the pinned hash, and passed `git diff --check`.
- Completed three independent read-only audits; their concrete unit,
  net-cash mismatch, retry-law, sidecar-path, and partial-publication findings
  were corrected before the substantive commit.

## Next

- Commit this final ledger state, remove the temporary ledger so no scaffold
  remains, push the branch, and write the external handoff report.
