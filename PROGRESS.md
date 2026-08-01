# Amendment 5 fix round 1 progress

## State

Active on finding 1 of 10. The worktree starts from unratified Amendment 5
commit `6f2b1a4068cf2036d8b51de8df1cf6624fcd9562` on
`claude/ce-design-amendment5`. All work is documentation-only and preserves
the ratified 1,376,610-byte prefix exactly.

## Done

- Read the complete round-1 referee verdict, including all ten required
  rewrites and the three satisfiability walks.
- Confirmed the starting worktree is clean.
- Recomputed the frozen-prefix SHA-256 as
  `6e6995483d8cf144703bc3c6ed9645af5c25b44303685a5c2dac4465587c94d8`.
- Identified `docs/design/covered_earnings_correction.md` §19 as the sole
  normative amendment surface.

## Next

1. Close finding 1 by defining and plumbing the complete v2 legal-authority
   successor chain through every retained consumer.
2. Close findings 2–10 in referee order, committing each separately.
3. Recompute identities, sweep stale literals, rerun all satisfiability
   walks, and write the round-2 referee report.
