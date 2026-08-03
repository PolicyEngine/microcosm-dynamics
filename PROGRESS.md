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

## Next

1. Re-derive the analytic-arm shape decomposition from the 43 raw sources
   (renderable seven-key vs unrenderable four-key containers and members).
2. Derive the lawful minimum for the unrenderable four-key row per member
   domain (264 json_integer / 260 rational) and state the selection rule.
3. Rewrite the fact-table product row as a per-shape floor sum with both
   addends, exact total, full TiB expansion.
4. Fix every dependent sentence, including the "more than 242.588 TiB" claim.
5. Add the one settling clause for arm-ambiguous renderable members.
6. Verify prefix + census under the settled clause; commit; report.
