# PR #286 Fix Round 5 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `f6a986d`
- Latest review/adjudication: round-5 FIX-FIRST with two confirmed items
- Local implementation: in progress
- Verification: pending
- Push state: pending
- Final report: `scratch/pr286-round5-final-report.md`

## Done

- Confirmed the requested worktree, branch, and clean starting state.
- Retrieved the latest two PR #286 comments.
- Confirmed the required ignored-executable seal and registration-reference
  structural bound without expanding scope.
- Hardened the shared preparation/publication source seal with explicit
  porcelain-v1 all-untracked status and NUL-safe ignored executable
  enumeration under `src` and `scripts`.
- Set `PYTHONDONTWRITEBYTECODE=1` and `sys.dont_write_bytecode` before project
  imports in both the coordinator and its production CLI.
- Added a production-path mutation using a real unchecked-hash cache compiled
  from a temporary source and placed under `scripts/__pycache__`; it produces
  a preparation incident before any compute operation.
- Verified all 52 coordinator tests after the ignored-executable change.

## Next

1. Bound registration references to 1,024 characters in structural validation
   inside the preparation incident boundary, then test rejection at 1,025 and
   claim creation at 1,024.
2. Run focused and full validation, write the final report, commit each
   coherent step, and push if DNS permits.
