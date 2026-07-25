# PR #286 Fix Round 8 Progress

## State

- Branch: `sol/entry8-impl`
- Starting tip: `8172e7c`
- Review/adjudication: read and reconciled
- Implementation: complete
- Verification: required local suites complete and green
- Push: pending
- Final report: this file

## Done

- Confirmed the requested worktree, branch, clean starting tree, and starting tip.
- Loaded the PR review-comment workflow.
- Read the latest two PR #286 comments: the round-8 FIX-FIRST review and its
  accepted adjudication.
- Confirmed the two required work areas:
  - bind both guards to the sealed repository while scrubbing all inherited
    `GIT_*` routing variables and refusing lowercase `git ls-files -v` flags;
  - isolate the CLI success test in a temporary repository and audit every
    other test for unmocked access to the live guard.
- Hardened the launcher-side and coordinator-side Git helpers to:
  - remove every inherited `GIT_*` variable from the child environment;
  - invoke `git -C <sealed-root> --git-dir=<sealed-root>/.git`;
  - verify `rev-parse --show-toplevel` resolves to the sealed root.
- Made both guards reject every lowercase `git ls-files -v` tag and the
  uppercase `S` tag that Git uses for skip-worktree alone.
- Confirmed the explicit Git route accepts this linked worktree's `.git`
  gitfile and both hardened helpers accept its ordinary index flags.
- Added an exact subprocess contract test proving both helpers use explicit
  root/git-dir arguments, preserve non-Git environment, omit `cwd`, and pass
  no `GIT_*` variable to Git.
- Added root-mismatch coverage for both the launcher guard and coordinator
  recheck.
- Strengthened the ABI-shadow sealed-process regression with a real clean-repo
  `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` redirection attempt; the sealed
  repository is still refused before import.
- Added a sealed-process regression proving an assume-unchanged tracked
  coordinator edit is absent from porcelain status but refused before import.
- Added coordinator recheck regressions for redirected Git state,
  assume-unchanged (`h`), and skip-worktree (`S`) tracked edits.
- Moved the CLI success test's guard target to the established committed
  temporary-repository fixture while continuing to load the live launcher
  code, so ordinary pytest cache minting cannot affect the guarded root.
- Audited every launcher test: only the repaired CLI success test previously
  ran the full guard against the live checkout; the two intentional live Git
  tests perform read-only `show`/`rev-parse` queries, not cleanliness guards.
- Verified all 64 coordinator tests pass and re-ran the repaired CLI success
  test under ordinary pytest settings.
- Recounted 3,615 tests: unit 829, artifact 1,303, integration 804,
  reproduction 520, and oracle 159.
- Verified the complete focused first-estimates scope: 188 passed.
- Verified the complete executable fast tiers:
  - unit: 824 passed and 5 skipped;
  - artifact: 1,263 passed and 40 skipped.
- Verified repository-wide Black leaves all 486 Python files unchanged, Ruff
  accepts the repository, and `git diff --check` is clean.
- Confirmed an ordinary all-tier pytest run no longer fails at the repaired CLI
  success test. Its remaining failure is the pre-round-7 import-time
  `PYTHONDONTWRITEBYTECODE` assertion that the round-8 review explicitly
  identified as pre-existing and excluded from this fix round.
- Removed all 182 generated ignored `.pyc` files under `src/` and `scripts`;
  zero ignored files remain in either guarded code root.
- Verified the real launcher pre-import guard and coordinator source recheck
  both accept the committed-clean linked worktree under the isolated,
  no-bytecode, fresh-empty-sentinel interpreter; the sentinel remained empty.

## Next

1. Attempt to push `sol/entry8-impl`.
2. Record the push outcome and remove this lane progress file as required.

## Final report

- `scripts/run_first_estimates.py`: the pre-import guard now strips every
  `GIT_*` child variable, supplies explicit `-C` and `--git-dir` routing,
  verifies the sealed top-level, and refuses hidden index flags before checking
  porcelain status or ignored executable artifacts.
- `src/populace_dynamics/estimates/coordinator.py`: the post-import recheck uses
  the same hardened Git route, top-level equality check, and lowercase/`S`
  index-flag refusal; all HEAD-byte checks also use the sanitized route.
- `tests/estimates/test_coordinator.py`: the sealed launcher refuses a
  `GIT_DIR`-redirected ABI shadow and an assume-unchanged tracked coordinator
  edit before import; coordinator coverage pins redirection,
  assume-unchanged, skip-worktree, exact child environment/argv, and root
  mismatch. The CLI success test guards a committed temporary repository.
- Audit: no test now invokes either full cleanliness guard against the live
  checkout. Two retained live Git tests are limited to read-only source/root
  identity queries.
- Counts: coordinator 64 passed; focused 188 passed; collection 3,615; unit
  824 passed and 5 skipped; artifact 1,263 passed and 40 skipped; Black 486
  files; zero ignored guarded-root files. The required local suites are green.
