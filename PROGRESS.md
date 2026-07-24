# Entry 8 Implementation Progress

## State

Implementation started from design commit `6586b92` on branch
`sol/entry8-impl`. The required external lane status file could not be
created because the execution sandbox does not permit writes outside the
worktree. The COLA extraction is complete and locally validated.

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

## Next

- Implement and test the full-actuals parameter, rate-leg, and COLA loaders.
- Implement the career join and four-stage inclusion law.
- Implement both ledgers, artifact/incident writers, and projection driver.
- Run the required quality checks, push, and open the draft PR.

## Design question for the PR

- The resumed brief explicitly requires SSA first-payment-year values through
  2022, while design §7.4 calls the extraction determination-year keyed. The
  implementation obeys the newer explicit spot checks. The benefit ledger
  will preserve the frozen statutory compounding by translating each
  post-1982 determination year to the following payment-year source row.
