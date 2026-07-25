# PR #286 Fix Round 6 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `0c12e85`
- Latest review/adjudication: round-6 FIX-FIRST with two confirmed items
- Local implementation: in progress
- Verification: seal-focused checks pass
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

## Next

1. Run focused and tiered verification, update counts, and push if DNS allows.
