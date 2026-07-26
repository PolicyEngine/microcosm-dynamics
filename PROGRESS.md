# PR #303 round-3 fixes

## State

- Branch: `sol/entry8-birth-impl`
- Starting HEAD: `02ab472a04ae6d7fa78af08027dfd3bd0629a4e1`
- The round-2 verdict was read in full.
- The pre-existing untracked `FINAL_REPORT.md` is output scaffolding and remains
  outside the branch.
- Implementation changes have not started.

## Done

- Confirmed the requested branch, starting HEAD, and clean tracked worktree.
- Confirmed `b10e13c8dba21f314e3d50f693bd1a28f596ef95` exists as a commit
  on this branch and is an ancestor of HEAD.
- Confirmed the replacement and pre-rebase reviewed-implementation commits
  have the identical tree `359a4bcc6c55a9eace34819d8c62fd00c36279c8`.
- Identified the three narrow findings: replay identity guard coverage,
  weighted birth-source reconciliation, and count-plus-weight claim-origin
  reconciliation.

## Next

- Repin the reviewed implementation identity and add a cheap direct guard test.
- Add career weights and weighted birth-source reconciliation with a
  weighted-only forgery regression.
- Add claim-origin count and weight reconciliation with an origin-forgery
  regression.
- Run the requested focused and full verification, update this ledger, push,
  and write the final report to the output file.
