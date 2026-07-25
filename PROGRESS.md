# PR #286 Fix Round 7 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `cd22ea2`
- Latest review/adjudication: round-7 FIX-FIRST with one confirmed item
- Local implementation: in progress
- Verification: pending
- Push state: pending
- Final report: pending

## Done

- Confirmed the requested worktree, branch, and clean starting tree.
- Retrieved and read the latest two PR #286 comments.
- Confirmed the single required change: run the tracked-drift and ignored
  executable guards inside the sealed launcher before adding `src` to
  `sys.path` or importing any `populace_dynamics` module.
- Confirmed the coordinator's post-import recheck must remain.
- Confirmed the two required regressions: an ignored coordinator ABI-extension
  shadow and a direct sourceless `src/subprocess.pyc` shadow must both be
  refused pre-import.
- Added the launcher-side full-porcelain and ignored-executable guard after the
  interpreter seal and before argument parsing, `src` path insertion, or any
  repository import.
- Made the guard fail closed on Git invocation errors and emit a stable,
  structured procedural refusal to stderr with no incident path.
- Documented in the launcher that these pre-import refusals cannot be incident
  records and that the fresh registration must restate the checks and handling.
- Left the coordinator's post-import source guard and rechecks unchanged.

## Next

1. Add the two pre-import shadow regressions.
2. Run focused and full verification and recount the test tiers.
3. Finalize progress, push if DNS permits, and write the final report.
