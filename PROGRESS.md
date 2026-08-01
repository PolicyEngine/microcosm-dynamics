# Amendment 5 fix round 1 progress

## State

Findings 1–3 are closed; finding 4 is next. The worktree starts from
unratified Amendment 5
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
- Closed finding 2 with a fixed 51-jurisdiction PSID-code vocabulary
  authenticated by the committed PSID/FIPS state-code source rows, exact
  source-table extraction, inclusive numeric range expansion, exhaustive
  inventory-domain mapping, source-labeled alias normalization, and explicit
  missing/duplicate/overlap/ambiguity aborts.
- Closed finding 3 with independent disposition/attachment-cell and
  rule-major effective-cell source relations; exact family/claim joins;
  official-order unique affected keys and registry-order unique governing
  rules; explicit V-B3 family and state/local jurisdiction aggregation;
  nonempty behavior; and exact branch-identical JSON-array serialization.

## Next

1. Close finding 4 by freezing joint overlap fact assignments and total
   per-vector authority evaluation.
2. Close findings 5–10 in referee order, committing each separately.
3. Recompute identities, sweep stale literals, rerun all satisfiability
   walks, and write the round-2 referee report.
