# Progress

## State

Finding 1 from the extraction referee is under investigation on
`claude/anchor-extraction-v1`. The local and GitHub branch heads are both
`b3c51f4`, which includes the coordinator's `.gitattributes` fix. Shell
`git fetch` and `git pull --ff-only` were attempted first but could not
resolve `github.com`; GitHub's branch comparison confirms the heads are
identical.

## Done

- Read the extraction referee report in full.
- Confirmed finding 1: span expansion can let two logical value coordinates
  resolve to one physical `td`.
- Confirmed finding 2 is fixed by coordinator commit `b3c51f4`.

## Next

- Add the exact re-pinned 6.A1 2015 `colspan="2"` collapse attack as a
  fail-closed regression test and capture its pre-fix output.
- Require selected value coordinates to resolve to unique physical 1x1 cells.
- Run Black, Ruff, the relevant test tier, and byte-identical artifact checks.
- Commit each coherent step, push, and write the final lane report.
