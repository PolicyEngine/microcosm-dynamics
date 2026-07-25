# PR #286 Fix Round 5 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `f6a986d`
- Latest review/adjudication: round-5 FIX-FIRST with two confirmed items
- Local implementation: complete
- Verification: complete except final committed-tree source seals
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
- Bounded registration references at 1,024 characters in the canonical
  structural parser inside the preparation incident boundary.
- Added a production-path boundary test proving that 1,025 characters refuse
  before compute while 1,024 characters mint a sub-4-KiB claim and publish.
- Verified all 53 coordinator tests after both round-5 changes.
- Recounted the two new coordinator tests in the enforced artifact tier: 1,292
  collected.
- Full collection passes: 3,604 tests.
- Full focused first-estimates verification passes: 177 tests.
- Unit tier passes in the repository-main environment: 824 passed, 5 skipped.
- Artifact tier passes: 1,252 passed, 40 skipped.
- The full-collection tier-policy assertion passes.
- Black accepts all 486 Python files; Ruff and `git diff --check` are clean.

## Next

1. Commit verification bookkeeping.
2. Remove only Git-enumerated ignored executable caches under `src` and
   `scripts`, then confirm two clean production source seals.
3. Write the final report, commit the completed progress state, and push if
   DNS permits.
