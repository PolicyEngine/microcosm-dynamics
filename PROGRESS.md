# PR 303 referee fixes

## State

- Branch: `sol/entry8-birth-impl`
- Referee verdict read in full.
- PR #304 merged as `f771b49e5a38aa25cd676f2a37b7683c964a3f2d`
  while verification was running, activating the revision-10.1 path.
- The implementation and requested verification are complete.
- Exact-master synchronization and push are externally blocked: every direct
  fetch fails with `Could not resolve host: github.com`, while the connected
  GitHub API does not expose the signed Git object needed to import the merge
  commit locally. The installed `gh` client also reports that its active
  `MaxGhenis` credential is invalid.
- The branch is therefore rebased onto local
  PR-head `c38dcb7`, whose tree is byte-identical to the merged master tree
  `5c8a10a164ae7c5bdb802e7ee257475099518a80`; exact-master ancestry remains
  required before push. This is a content-equivalent temporary base, not an
  exact rebase onto `origin/master`.

## Done

- Confirmed the requested branch and existing branch head.
- Read the accepted PR #303 disposition and confirmed that all ten referee
  findings were accepted, including dropping the unratified preflight.
- Initially confirmed through the GitHub connector that PR #304 was open,
  then rechecked after verification and observed its merge.
- Confirmed local `origin/master` is the canonical amendment squash
  `4104d3d`, and that commit is an ancestor of itself.
- Initially pinned the runner and literal test to `4104d3d`; after revision
  10.1 merged, advanced the current normative amendment identity to
  `f771b49`.
- Deleted the preflight script/tests and removed their seven unit tests from
  the tier manifest.
- Restructured Stage C into candidate-total origin classification, global
  C.5, and survivor-only operative-state passes.
- Added a two-candidate barrier regression. The former loop reaches candidate
  1's source lookup before candidate 2's origin classification, so the new
  test's first global-barrier assertion necessarily fails on that version.
- Required exact normalized holdout/seed ID equality and retained the
  separate missing-upstream-real-seed abort.
- Added tests for both seed aborts and integer-like holdout normalization.
- Career/preparation focused suite: `41 passed in 0.98s`.
- Tier-policy collection check after this step: `1 passed, 3649 deselected`.
- Publication validation now reconciles every draw's unweighted career rows
  by birth source against the included-source count surface.
- Added the referee's exact source-forgery regression and literal,
  test-owned 66-key count and 19-key sensitivity inventories.
- Made the one-claimant publication fixture internally coherent and removed
  its contradictory all-zero acceptance branch.
- Published the evidence artifact's exact complete-scenario pricing sentence
  under the evidence-matching `included_set` semantics key.
- Publication/first-report focused suite: `31 passed in 1.02s`.
- Black check and Ruff pass for the publication step; tier-policy collection
  check: `1 passed, 3650 deselected`.
- Replaced the sealed preparation stub with a three-person, twenty-wrapper
  batch that runs real seed construction, real C.5, real benefit/revenue
  preparation, and all three complete-set sensitivity scenarios. The
  unresolved opening-stock candidate is asserted to stop at C.5.
- Split the reducer's historical cache-input identity from its reviewed
  implementation identity, made the latter advance with the final reviewed
  production-source commit, and adapted both absent legacy and
  explicit-unresolved upstream records.
- Added a no-write `--implementation-replay` mode that runs current production
  preparation on the pinned draw-0 cache and compares six frozen artifact
  rows.
- Added cheap CI replay coverage for the explicit-unresolved adapter and for
  production clause-3 preparation of the artifact's 4,077 derived plus 2,315
  unresolved rows without loading the 7 GB cache.
- Sealed/replay artifact tests: `5 passed in 4.78s`; updated tier-policy
  collection check: `1 passed, 3652 deselected`.
- Draw-0 implementation replay: status `matched`, with 4,077 derived, 2,315
  unresolved, 3,083 candidates, and included sets 1,514 / 1,520 / 1,240.
- Pre-revision-10.1 full focused suite: `85 passed in 5.40s`; the six named
  referee regressions passed individually in `4.78s`.
- Pre-revision-10.1 full unit tier: `843 passed, 5 skipped, 2805 deselected`
  in `62.25s`;
  the only warning was the existing joblib physical-core fallback.
- Pre-revision-10.1 full artifact tier: `1284 passed, 38 skipped, 2331
  deselected` in `68.49s`.
- Applied Black's sole requested mechanical wrap in the seed assertion and
  advanced the reviewed production-source pin to that formatting commit.
- Updated `GAP_BLOCK` and its byte/SHA fixture to revision 10.1's exact
  corrected sentence.
- Added an artifact-derived test recomputing
  `(2,806 + 86) / 3,083 = 2,892 / 3,083 = 93.8%` and matching the published
  statement.
- Revision-10.1 runner/GAP/artifact focused suite: `44 passed in 1.11s`;
  tier policy: `1 passed, 3653 deselected`.
- The current reviewed production-source identity is
  `634baabff7966057ac4eea13c95f23844564b7eb`.
- Post-revision-10.1 draw-0 replay: status `matched` for all six frozen
  rows.
- Post-revision-10.1 focused suite: `86 passed in 5.59s`.
- Post-revision-10.1 unit tier: `843 passed, 5 skipped, 2806 deselected`
  in `53.54s`; only the existing joblib physical-core warning.
- Post-revision-10.1 artifact tier: `1285 passed, 38 skipped, 2331
  deselected` in `66.06s`.
- All 15 changed Python files pass Black and Ruff; compilation succeeds,
  `git diff --check` passes, and `src/`/`scripts/` remain bytecode-free.
- Final tier-policy inventory check: `1 passed, 3653 deselected`.
- Repeated the prior integration-tier attempt: `169 passed, 3 skipped`,
  then the known order-dependent `populace.fit` import assertion failed.
  The affected module passes alone: `13 passed in 3.92s`.
- Confirmed PR #303 remains open and GitHub currently reports it mergeable;
  its remote head remains `efa5e662d60d885c654419871b002987dc2f3ac5`.
- Verified all 21 local commit subjects, `git fsck --no-dangling`,
  `git diff --check`, and a clean tracked worktree.
- Retried `git fetch origin master` after all implementation and verification
  work; it still failed at DNS resolution.
- Ran the publishing prerequisite checks: `gh` 2.96.0 is installed, but
  `gh auth status` reports an invalid active token, so the publishing workflow
  correctly stopped before any remote mutation.
- Identified the lane report target as
  `/Users/maxghenis/m6-sol-lanes/sol-impl-fix.out`.

## Next

- From a network-enabled environment, fetch `origin/master`, replace
  `c38dcb7` with exact `f771b49` ancestry, and advance
  `REVIEWED_IMPLEMENTATION_COMMIT` to the rewritten production-source commit.
- Rerun the draw-0 replay plus focused/static checks, commit the pin and final
  ledger update, then push the rebased `sol/entry8-birth-impl` branch (using
  lease protection because the required rebase rewrites the existing PR
  branch).
