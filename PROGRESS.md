# PR #286 Fix Round 5 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `f6a986d`
- Latest review/adjudication: round-5 FIX-FIRST with two confirmed items
- Local implementation: complete
- Verification: complete
- Push state: attempted and blocked by DNS (`Could not resolve host: github.com`)
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
- Removed 382 generated ignored executable cache files under `src` and
  `scripts`; no matching ignored artifacts remain.
- Two final production source-guard invocations pass on an empty explicit
  all-untracked porcelain state.
- Attempted to push `sol/entry8-impl`; the host could not resolve `github.com`.
- Wrote the requested final report outside tracked repository state.

## Next

1. Retry `git push origin sol/entry8-impl` when DNS is available.
2. No local implementation or verification work remains.
