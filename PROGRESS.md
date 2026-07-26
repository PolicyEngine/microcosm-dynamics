# PR #303 round-3 fixes

## State

- Branch: `sol/entry8-birth-impl`
- Starting HEAD: `02ab472a04ae6d7fa78af08027dfd3bd0629a4e1`
- The round-2 verdict was read in full.
- The pre-existing untracked `FINAL_REPORT.md` is output scaffolding and remains
  outside the branch.
- All three round-3 findings are implemented and locally verified; final
  cross-suite verification and identity advancement remain.

## Done

- Confirmed the requested branch, starting HEAD, and clean tracked worktree.
- Confirmed `b10e13c8dba21f314e3d50f693bd1a28f596ef95` exists as a commit
  on this branch and is an ancestor of HEAD.
- Confirmed the replacement and pre-rebase reviewed-implementation commits
  have the identical tree `359a4bcc6c55a9eace34819d8c62fd00c36279c8`.
- Identified the three narrow findings: replay identity guard coverage,
  weighted birth-source reconciliation, and count-plus-weight claim-origin
  reconciliation.
- Repinned `REVIEWED_IMPLEMENTATION_COMMIT` from the pre-rebase SHA to the
  verified tree-identical branch ancestor
  `b10e13c8dba21f314e3d50f693bd1a28f596ef95`.
- Added a CI-cheap test that directly invokes `_assert_input_identity`.
- Guard regression: `1 passed in 1.43s`.
- Tier policy after adding the artifact test:
  `1 passed, 3655 deselected in 4.69s`.
- Black and Ruff pass for the reducer and guard-test changes.
- Added claimant weight to every published career diagnostic row and to its
  exact schema; validation requires the value to be finite and nonnegative.
- Accumulated career-row weights per draw and birth source and reconciled all
  weighted `included_birth_source` surfaces with `math.fsum` and the existing
  count-invariant tolerance.
- Added the referee's weighted-only forgery: unweighted surfaces and career
  rows remain exact-marriage while weighted population/included mass moves to
  derived-projection-age.
- Weighted-only forgery regression: `1 passed in 1.60s`.
- Publication plus first-report suites after the weighted fix:
  `32 passed in 1.90s`.
- Tier policy: `1 passed, 3656 deselected in 2.17s`.
- Black and Ruff pass for the weighted-reconciliation files.
- Accumulated career-row counts and weights per draw and claim origin and
  reconciled both unweighted and weighted `included_origin` surfaces.
- Added the referee's origin forgery: every career row changes to
  `opening_backfill` while count and table surfaces remain untouched.
- Both new forgery regressions together: `2 passed in 0.71s`.
- Publication plus first-report suites after origin reconciliation:
  `33 passed in 1.01s`.
- Tier policy: `1 passed, 3657 deselected in 1.29s`; the three new tests are
  all artifact-tier and the manifest now records 1,327 artifact tests.
- Black and Ruff pass for the origin-reconciliation files.
- After first repinning the rebased reviewed tree to `b10e13c`, advanced the
  identity to final production-source commit
  `1057cf55d5fed6b69254bb5215a3978bfb5ec1bc`; it exists, is an ancestor of
  HEAD, and exactly matches HEAD across every guarded production path.

## Next

- Run the three named new tests, full estimates and publication suites,
  tier policy, Black, Ruff, and the CI-cheap replay test.
- Run the requested focused and full verification, update this ledger, push,
  and write the final report to the output file.
