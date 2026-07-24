# Entry 8 Implementation Progress

## State

Implementation started from design commit `6586b92` on branch
`sol/entry8-impl`. The required external lane status file could not be
created because the execution sandbox does not permit writes outside the
worktree. The COLA extraction and independent full-actual parameter loaders
are complete and locally validated. Statutory-pipeline implementation is in
progress; no projection has been run.

## Done

- Confirmed the branch starts at the ratified revision-9 design commit.
- Created this committed progress ledger before implementation work.
- Read the complete implementation brief and ratified design.
- Added the deterministic offline SSA COLA-history extractor, committed JSON
  anchor, and reader-free rebuild/transcription tests.
- Corrected the recovered WIP to the required first-payment-year series,
  including `2009=5.8`, the 2010/2011/2016 zero-COLA years, `2022=5.9`, and
  the 1983 timing-transition zero.
- Verified the COLA milestone with 11 focused tests, Black (79 columns), Ruff,
  and `git diff --check`.
- Added hash-pinned loaders for the seven consumed SSA files and the separate
  employee and employer OASDI rate legs from policyengine-us 1.752.2.
- Bound production loading to the installed distribution's version and
  parameter directory, while retaining a hash-gated explicit seam for small
  synthetic tests.
- Added full-actual NAWI and wage-base assertions, 6.2% + 6.2% = 12.4%
  preparation assertions with no fallback, exact COLA runtime coverage, and
  JSON-ready path/hash provenance for the complete parameter bundle.
- Verified the parameter milestone together with the COLA extraction: 19
  focused tests passed; Black (79 columns), Ruff, and `git diff --check`
  passed.

## Next

- Implement the career join and four-stage inclusion law.
- Implement both ledgers, artifact/incident writers, and projection driver.
- Run the required quality checks, push, and open the draft PR.

## Design question for the PR

- The resumed brief explicitly requires SSA first-payment-year values through
  2022, while design §7.4 calls the extraction determination-year keyed. The
  implementation obeys the newer explicit spot checks. The benefit ledger
  will preserve the frozen statutory compounding by translating each
  post-1982 determination year to the following payment-year source row.
