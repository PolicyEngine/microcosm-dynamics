# Amendment 5 round-3 progress

## State

- Branch: `claude/ce-design-amendment5`
- Starting HEAD: `407590844d9673ef14f69750f38c76f791736fe3`
- Scope: documentation-only repair of R3-1 in §19.
- Status: R3-1 rewrite, verification, and final report complete.

## Done

- Confirmed the starting branch, HEAD, and clean worktree.
- Read `sol-ce-amend5-r3-verdict.md` in full.
- Recorded the six mandatory rewrite requirements and the immutable revision-6 prefix constraint.
- Replaced the all-assertions-agree rule with an exact-covered, source-ordered assertion-occurrence relation and the closed dispositions `selecting_system_reference | nonselecting_historical_provenance`.
- Froze the actual page-23 V93 GSA occurrence as byte-pinned nonselecting historical provenance without asserting a GSA-to-PSID equivalence.
- Put complete occurrence rows and dispositions in the declaration-ID preimage and added omitted, unknown, competing, overlapping, and multiply-disposed aborts.
- Replayed the complete 579-byte V93 block and expanded the hostile-vector set from five to seven with recognized-plus-unsupported and conflicting-reference attacks.
- Corrected and stated Walks A and B, extended G17-C05 and the replacement ledger, and added four closure-sweep seeds.
- Reproduced the three V93 assertion spans and hashes, the 130-seed/3,114-variant closure vocabulary, six strict JSON blocks, the 33-row comparator census, and the seven-vector census.
- Ran the focused source-reproduction tests: 6 passed. The pre-commit required suite reached 239 passed and its expected in-flight design-binding guard; it will be rerun after this coherent-step commit.
- Committed the normative repair as `4f5e490f871c81c6a514a6ccc84d5f5f4ad3519d` after the revision-6 prefix and stale-literal guards.
- Reran the required tests against committed design bytes: 240 passed; reran the focused source tests: 6 passed.
- Reran the closure expansion (130 seeds, 3,114 unique variants), inspected all 11 new-term passages and their transitive consumers, and found no unresolved R3-1 passage.
- Reran satisfiability Walks A, B, and C. The V93 and ER21004 local replays pass; the unrelated prospective-authority and Class-C blockers remain honest global aborts.
- Wrote `FINAL_REPORT.md` with the passage inventory, identity table, closure/consumer results, all three walks, hostile-vector census, and test output.

## Next

1. Commit this completed progress ledger and `FINAL_REPORT.md` after the revision-6 prefix guard.
2. Submit the exact amended design blob for the next adversarial referee round.
3. Do not treat this authoring result as D5 ratification or begin source/authority construction before an affirmative verdict and the prescribed ratification step.
