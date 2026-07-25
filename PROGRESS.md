# PR #286 Fix Round 7 Progress

## State

- Branch: `sol/entry8-impl`
- Review anchor: `cd22ea2`
- Latest review/adjudication: round-7 FIX-FIRST with one confirmed item
- Local implementation: complete
- Verification: complete
- Push state: attempted and blocked by DNS (`Could not resolve host: github.com`)
- Final report: this file

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
- Added isolated temporary-repository regressions for an ignored
  `coordinator.<ABI>.so` extension shadow and a direct sourceless
  `src/subprocess.pyc` shadow.
- Verified both regressions refuse before repository import, emit exactly one
  structured stderr record, create no claim or incident, execute neither
  hostile payload, and leave the sealed cache sentinel empty.
- Verified all 58 coordinator tests pass.
- Recounted the enforced tiers after the two artifact-class regressions: unit
  829, artifact 1,297, integration 804, reproduction 520, and oracle 159;
  full collection is 3,609 tests.
- Verified the full focused first-estimates scope: 182 passed.
- Verified the executable tiers: unit 824 passed and 5 skipped; artifact 1,257
  passed and 40 skipped. The tier-policy assertion passes in the full unit-tier
  collection.
- Ruff accepts the repository, Black leaves all 486 Python files unchanged,
  and `git diff --check` is clean.
- Verified the committed worktree has empty full porcelain and zero ignored
  executable artifacts under `src/` and `scripts/`.
- Verified the launcher-side guard accepts the clean tree under the real
  isolated/no-bytecode/empty-prefix interpreter.
- Verified the retained coordinator post-import recheck accepts the same clean
  tree under that sealed interpreter.
- Attempted to push `sol/entry8-impl`; DNS could not resolve `github.com`.

## Next

1. Retry `git push origin sol/entry8-impl` when DNS is available.
2. No local implementation or verification work remains.

## Final report

- `scripts/run_first_estimates.py`: the sealed launcher now runs the complete
  tracked-drift and ignored-executable guard before argument parsing,
  `sys.path` mutation, or repository import; violations produce the documented
  procedural stderr refusal without an incident.
- `tests/estimates/test_coordinator.py`: two real sealed-process regressions
  prove pre-import refusal of an ABI-specific coordinator extension shadow and
  a direct sourceless `src/subprocess.pyc`.
- Counts: coordinator 58 passed; focused 182 passed; full collection 3,609;
  unit 824 passed and 5 skipped; artifact 1,257 passed and 40 skipped.
