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
- Replaced the sealed preparation stub with a three-person, twenty-wrapper
  batch that runs real seed construction, real C.5, real benefit/revenue
  preparation, and all three complete-set sensitivity scenarios. The
  unresolved opening-stock candidate is asserted to stop at C.5.
- Split the reducer's historical cache-input identity from its reviewed
  implementation identity, pinned the latter to the final production-source
  commit `9cb4b2a8bb95a3e636d225fe96b2030967043a02`, and adapted both absent
  legacy and explicit-unresolved upstream records.
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
- Full focused suite: `85 passed in 5.40s`; the six named referee regressions
  passed individually in `4.78s`.
- Full unit tier: `843 passed, 5 skipped, 2805 deselected` in `62.25s`;
  the only warning was the existing joblib physical-core fallback.
- Full artifact tier: `1284 passed, 38 skipped, 2331 deselected` in `68.49s`.
- Applied Black's sole requested mechanical wrap in the seed assertion and
  advanced the reviewed production-source pin to that formatting commit.
- Identified the lane report target as
  `/Users/maxghenis/m6-sol-lanes/sol-impl-fix.out`.
- Preserved the pre-existing untracked `FINAL_REPORT.md`.

## Next

- Run the full focused/unit/artifact, formatting, lint, tier-policy, bytecode,
  and repository-integrity verification matrix.
- Finalize this ledger and report, commit each coherent step, and push
  `sol/entry8-birth-impl`.
