# PR 303 referee fixes

## State

- Branch: `sol/entry8-birth-impl`
- Referee verdict read in full.
- PR #304 is open, so the branch remains on revision 10 and does not yet
  receive the revision-10.1 `GAP_BLOCK` correction.

## Done

- Confirmed the requested branch and existing branch head.
- Read the accepted PR #303 disposition and confirmed that all ten referee
  findings were accepted, including dropping the unratified preflight.
- Confirmed through the GitHub connector that PR #304 is open, not merged.
- Confirmed local `origin/master` is the canonical amendment squash
  `4104d3d`, and that commit is an ancestor of itself.
- Pinned the runner and literal test to `4104d3d`.
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
- Identified the lane report target as
  `/Users/maxghenis/m6-sol-lanes/sol-impl-fix.out`.
- Preserved the pre-existing untracked `FINAL_REPORT.md`.

## Next

- Implement findings 2 through 10, plus finding 1 when revision 10.1 is
  available; finding 1 is currently deferred by the explicit open-PR path.
- Run focused, formatting, lint, tier-policy, unit, artifact, replay, and
  draw-0 oracle checks.
- Update this ledger, write the final report, commit each coherent step, and
  push `sol/entry8-birth-impl`.
