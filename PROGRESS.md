# PR #286 Fix Round 4 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `d2b94b6`
- Latest review/adjudication: round-4 FIX-FIRST and all three dispositions confirmed
- Active task: harden attempt-claim reads

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
- Focused coordinator verification passes: 50 tests.

## Next

1. Harden attempt-claim reads and test special-file refusal where supported.
2. Run final verification, push if DNS permits, and write the final report to the requested output file.
