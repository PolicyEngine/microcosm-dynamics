# Amendment 9 — fix round 1 (referee verdict: REWRITE, four blocking findings)

## State

Branch `claude/ce-design-amendment9`, worktree `e11-amend9`. Base HEAD `4380589`.
Doc-only lane. All fixes are prose-only: no fixture, digest, count, floor, or
row-shape moves.

Identity at lane start (verified):

| | |
|---|---|
| candidate | 2,637,363 bytes, SHA-256 `8fca3354a3e2efdbfe1ab0a806bc660b9492a819b08b89ca7d5173e312011968` |
| revision-10 prefix `[0,2521700)` | byte-compared against the full blob at `bea8b43` — EQUAL |
| prefix SHA-256 | `4101260b94b019fc9392898059138b90386784b60ea40b9039562d364592718a` |

## Done

- [x] Read the round-1 verdict in full (`~/m6-sol-lanes/e8-ops/sol-ce-amend9-r1-verdict.md`)
- [x] Prefix law verified BEFORE edits (byte comparison, not digest)

## Next

- [ ] F1 — restate §23.2.2's derivation in the TRUE gate structure of §20.3.3
- [ ] F2 — §23.2.1 leg 4: drop or narrow to the explicit-arm law
- [ ] F3 — scope the "674 fields" serialization claim (`:39245`, `:40562`)
- [ ] F4 — "serialized exactly once" (`:39251-39254`, `:39379-39381`)
- [ ] F5 — `I` notation for implied-decimal forms
- [ ] F6 — §23.6.1 row for `candidate_arm_results[*].complete_domain_member_results`
- [ ] F7/F8 — report corrections: seven digests (not eight), 77 seeds (not 78)
- [ ] Concurrent-lane flag: two normalized-entry members with no source-determined
      value — does it bear on A9-R04's field-closure gate?
- [ ] Prefix law verified AFTER edits; `git diff --check` clean; remove PROGRESS.md
