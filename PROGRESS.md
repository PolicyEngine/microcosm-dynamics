# PR #286 Fix Round 4 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `d2b94b6`
- Latest review/adjudication: round-4 FIX-FIRST and all three dispositions confirmed
- Active task: commit verification bookkeeping, seal the final tree, and push

## Done

- Confirmed the requested worktree, branch, and review-anchor commit.
- Confirmed `git status --porcelain` is empty repo-wide.
- Retrieved the latest two PR #286 comments and confirmed there are no inline review threads.
- Changed the shared preparation/publication source guard to require exact, repo-wide `git status --porcelain` cleanliness, including untracked files.
- Added the requested production-path mutation for an untracked `scripts/registered_m6_candidate2_inputs/__init__.py` import-shadow package.
- Added the exact ignore rule required for the ceremony-created attempt claim so the seal does not reject its own durable control file.
- Added `runs/first_estimates_retry.claim` with canonical registration/incident binding, exclusive creation, file fsync, and parent-directory fsync.
- Placed retry consumption after exact incident-history authorization and before source validation or any retry work, inside preparation incident accounting.
- Added the requested production hard-crash-state test: a durable marker with no retry artifact/incident refuses the next retry to fresh registration.
- Ignored only the ceremony-owned attempt/retry controls and incident records that can legitimately predate a seal; arbitrary untracked files remain visible to full porcelain status.
- Replaced path-level claim reads with `O_NOFOLLOW | O_NONBLOCK` descriptor reads, `fstat`/`S_ISREG` validation, and a 4 KiB payload bound.
- Added the platform-gated production FIFO mutation and pinned the safe open flags, special-file refusal, and unchanged fresh-adjudication reason.
- Focused coordinator verification passes: 51 tests.
- Recounted the three new coordinator tests in the enforced artifact tier: 1,290 collected.
- Full collection passes: 3,602 tests collected.
- Full focused first-estimates verification passes: 175 tests.
- Unit tier passes: 824 passed, 5 skipped.
- Artifact tier passes: 1,250 passed, 40 skipped.
- Black accepts all 486 Python files; Ruff and `git diff --check` are clean.

## Next

1. Commit the final tier recount, formatting, and this progress ledger.
2. Confirm two empty full-porcelain repository seals.
3. Push if DNS permits and write the final report to the requested output file.
