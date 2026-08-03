# Amendment 8 fix round 3 — progress

## State

Branch `claude/ce-design-amendment8`, base HEAD `83688b8b`.
Round-3 verdict: REWRITE. Blocker B1 (single 325-byte product applied to a
heterogeneous analytic arm), non-blocking B2 (arm-ambiguous placement not
dispositioned).

Doc at base: 2,519,313 bytes, SHA-256
`28120452f301e291518029b6e7ca52c40ccc20583aba7ad80f822716c794ac42`.
Revision-9 prefix (first 2,423,590 bytes) SHA-256
`2064f47b181ec21ec9b786b9a17a7a489e3b4732751edf794d6bd545bd9546b9` — verified
at start.

## Done

- Read the round-3 verdict in full.
- Verified base doc bytes, SHA, and revision-9 prefix.
- Re-derived the whole census from the 43 raw sources with the pinned
  classifier at `b78e4b5d0878dfd192a3d6060f2f801d2bfe2b0d` (clean worktree,
  classifier SHA-256
  `35d62535ddaf9293da4b3b382412c5deb7bf349475ddd2d0ddc2f19e93a40f37`):
  - 89,599 fields; `7e497f20…`, `421105ab…`, `5c9020ad…`, `66a88e6f…`;
    ten counts 17,329 / 1,853 / 674 / 47 / 67,316 / 1,145 / 0 / 1 / 421 / 813.
  - Census rows and subtotals: 19,903 fields / 33,786 entries /
    820,709,179,087 members.
  - Threshold arms, published reading: explicit 4,736,892 (4,715,043
    renderable + 21,849 unrenderable); analytic 820,704,442,195 =
    820,701,994,620 in 9,019 `renderable_member_rows` containers +
    2,447,575 in 36 `unrenderable_member_rows` containers, all 36 inside
    `..._partial_range_exact_replay`.
  - Alternative §20.3.2 reading: 4,753,875 / 820,704,425,212 (56,480
    arm-ambiguous renderable members move; net 16,983 across the threshold).
  - All 36 unrenderable analytic containers are `rational` ranges of step
    `1/100`, so each member's four-key floor is 260 bytes (the 264-byte
    `json_integer` arm does not apply to any of them).
- Recomputed the lawful minima directly: seven-key renderable row 325 bytes
  in both type arms; four-key unrenderable row 264 (`json_integer`) /
  260 (`rational`).
- Corrected floor: 820,701,994,620 × 325 = 266,728,148,251,500 plus
  2,447,575 × 260 = 636,369,500, total 266,728,784,621,000 bytes =
  242.5884164231320028193295001983642578125 TiB (186.03× the 1.304 TiB lane).

## Next

1. Rewrite the fact-table product row as the per-shape floor sum.
2. Fix the dependent sentences after the table.
3. Add the settling clause for arm-ambiguous renderable members.
4. Re-verify prefix, bytes, SHA; commit; drop this ledger; report.
