# Entry 8 Implementation Progress

## State

Implementation started from design commit `6586b92` on branch
`sol/entry8-impl`. The required external lane status file could not be
created because the execution sandbox does not permit writes outside the
worktree. The COLA extraction and independent full-actual parameter loaders
are complete and locally validated. The one-shot publication contracts and
non-executed candidate-3 projection driver are also implemented. The
person-level statutory join and ledgers are in progress; no projection has
been run.

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
- Added the candidate-3 driver with pre-fit CandidateSpec hash assertions,
  the full fit/preflight/materialization prefix, unsplit population, and exact
  draw indices 0-19 mapped to frozen root seeds 5200-5219.
- Extended the exclusive artifact helper to accept exact precomputed sidecar
  bytes, then added the integrity-bound `first_estimates_v1` writer and
  validator with the frozen evidence labels, gap block, scope statements, and
  execution rule.
- Added the append-only exact-nine-key incident writer/validator, including
  filename/index, ISO-8601-Z, partial-artifact iff, configuration-identity,
  numeric-array, and retry-class rules.
- Verified the publication/driver milestone with 18 focused tests (including
  the existing artifact contract tests), Black (79 columns), Ruff, and
  `git diff --check`.
- Tightened table-schema validation so every table must carry all registered
  draw indices, nonempty mean/sample-SD aggregate rows, and a nonempty
  biennial companion for annual output.

## Next

- Implement the career join and four-stage inclusion law.
- Implement both statutory ledgers and artifact assembly from their results.
- Run the required quality checks, push, and open the draft PR.

## Design question for the PR

- The resumed brief explicitly requires SSA first-payment-year values through
  2022, while design §7.4 calls the extraction determination-year keyed. The
  implementation obeys the newer explicit spot checks. The benefit ledger
  will preserve the frozen statutory compounding by translating each
  post-1982 determination year to the following payment-year source row.
