# Amendment 5 fix round 1 progress

## State

Finding 1 is closed in the working tree; finding 2 is next. The worktree starts from unratified Amendment 5
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
- Closed finding 1 with the complete typed successor chain: legal result v2,
  base projection v2, adjudication preimages v3, noncapture objects v4, and
  authority cutoff v4. Replaced the retained §16.13.8/§16.14.4 equations and
  every construction, bundle, ledger, closure-sweep, successor-inventory,
  and DC-29 consumer.

## Next

1. Close finding 2 with a source-authenticated, exact-cover jurisdiction
   mapping and fail-closed alias/range law.
2. Close findings 3–10 in referee order, committing each separately.
3. Recompute identities, sweep stale literals, rerun all satisfiability
   walks, and write the round-2 referee report.
