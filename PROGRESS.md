# PR #286 Fix Round 6 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `0c12e85`
- Latest review/adjudication: round-6 FIX-FIRST with two confirmed items
- Local implementation: in progress
- Verification: complete
- Push state: pending
- Final report: pending

## Done

- Confirmed the requested worktree, branch, and review anchor.
- Retrieved and read the latest two PR #286 comments.
- Confirmed the two required changes: a pre-import self-re-exec seal and a
  canonical-serialized 1,024-byte registration-reference bound.
- Added the pre-import launcher self-re-exec under `-I -B -X
  pycache_prefix=<fresh-empty-directory>` with an explicit sentinel and
  worktree-local source resolution.
- Added the coordinator-entry runtime assertion as a preparation incident and
  retained the durable attempt claim before refusal.
- Added exact exec-argument, unsealed-refusal, and crafted unchecked-cache miss
  tests; all 56 coordinator tests pass.
- Restated the sealed invocation in the launcher procedure and future
  registration text.
- Replaced the character limit with a shared 1,024-byte bound over the
  canonical serialized registration-reference string.
- Applied the byte validator before both attempt- and retry-claim payload
  construction, leaving the 4,096-byte claim cap unchanged but unreachable.
- Added multibyte boundary assertions at exactly 1,024 and 1,025 bytes; the
  largest valid reference produces a 1,097-byte attempt claim.
- Verified all 56 coordinator tests, including sealed acceptance from the
  worktree-local coordinator source.
- Verified the full focused first-estimates scope: 180 passed.
- Recounted the enforced tiers: unit 829, artifact 1,295, integration 804,
  reproduction 520, and oracle 159; full collection is 3,607 tests.
- Verified the executable tiers: unit 824 passed and 5 skipped; artifact 1,255
  passed and 40 skipped. The tier-policy assertion passes.
- Black accepts all 486 Python files; Ruff and `git diff --check` are clean.
- Removed generated executable caches under `src` and `scripts`; the ignored
  executable inventory is empty.

## Next

1. Commit the verification ledger and tier recount.
2. Re-run the production source guards on the committed-clean tree.
3. Push `sol/entry8-impl` if DNS allows and write the final response.
