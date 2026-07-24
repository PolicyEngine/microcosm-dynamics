# Entry 8 Implementation Progress

## State

Implementation started from design commit `6586b92` on branch
`sol/entry8-impl`. The required external lane status file could not be
created because the execution sandbox does not permit writes outside the
worktree. The COLA extraction and independent full-actual parameter loaders
are complete and locally validated. The one-shot publication contracts,
non-executed candidate-3 projection driver, and both statutory ledgers are
also implemented. The person-level statutory join and pure artifact assembly
are complete. The production-output adapter and committed-fixture rebuild are
also complete. Standalone artifact-schema and invariant hardening is complete;
final repository validation is in progress. No projection has been run.

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
- Added the statutory benefit ledger with claim-year information cutoffs,
  AIME/PIA/claim-age adjustment, stepwise dime-floored COLAs, actual-presence
  payments, separate modeled-flow and opening-stock rows, and an explicit
  no-recomputation diagnostic.
- Added the nominal payroll-revenue ledger over every realized in-window
  projection person-year, using the actual wage base and separate employee
  and employer rate legs, plus annual and biennial presentations.
- Added exact registered-draw aggregation with arithmetic means and sample
  standard deviations, and verified the ledger milestone with 7 focused
  tests, Black (79 columns), Ruff, and `git diff --check`.
- Added the all-person population roster and exact/inferred/synthetic-native
  birth-year precedence with fully reconciled weighted and unweighted source
  counts.
- Added annual career construction with the information cutoff before
  imputation, post-biennial gap law, corrected 2013/2014 seam, exhaustive
  provenance, coverage diagnostics, and pre-1968 top-35 warnings.
- Added the canonical Stage A-D inclusion pipeline: whole-trajectory DI
  precedence; any-slice claimant detection and both nonclaimant paths;
  disjoint modeled/opening origins; person-keyed, strictly truncated opening
  imputation; and first-failure-only ordered exclusions.
- Added actual-presence, post-claim-earnings, endpoint-snap, and explicit-row
  entrant diagnostics, and verified the career milestone together with its
  ledger adapter using 21 focused tests, Black (79 columns), Ruff, and
  `git diff --check`.
- Added exact twenty-draw post-compute assembly for the modeled-award flow,
  imputed opening stock, and nominal payroll-revenue tables, including wide
  per-draw rows, flattened means/sample SDs, and per-draw plus aggregate
  biennial companions.
- Added comprehensive inclusion, origin, birth-source, endpoint, entrant,
  career-provenance, odd-year, positive-post-claim, and no-recomputation
  diagnostics to the immutable artifact envelope.
- Kept the unregistered SSA award context ratio explicitly `not_computed`
  rather than fabricating a level series; the missing statistic/source/vintage
  is recorded as a design question in the artifact.
- Verified artifact assembly together with the statutory ledgers and
  publication contracts using 18 focused tests, Black (79 columns), Ruff, and
  `git diff --check`.
- Added the pure adapter from the exact twenty unsplit candidate-3 projection
  outputs to the population roster, returned-slice trajectory, synthetic
  birth-year map, independently reconstructed claiming schedule, inclusion
  result, and both statutory ledgers.
- Required the adapter to consume hash-bound full-actual report parameters,
  never `phase.bundle`, and bound the artifact configuration's parameter
  provenance back to the exact bundle used for its ledger computations.
- Verified the complete parameter/career/ledger/preparation/assembly path with
  41 focused tests, Black (79 columns), Ruff, and `git diff --check`.
- Added a committed raw-input fixture that rebuilds the full roster and all
  birth sources, Stage-A classes, Stage-B paths, claim origins, opening-stock
  endpoint snaps, ordered Stage-D reasons, career provenance, and both
  statutory ledgers without PSID or a projection run.
- Pinned golden benefit and payroll-revenue arithmetic, including an
  any-slice claimant removed before the final slice, scheduled seed metadata
  that is never treated as presence, strict opening-PMF truncation,
  odd-year diagnostics, and the no-recomputation invariant.
- Verified the fixture together with the career and ledger suites using 22
  focused tests, Black (79 columns), Ruff, JSON parsing, and
  `git diff --check`.
- Hardened standalone artifact validation around the exact three-table schema,
  annual and biennial draw grids, origins, identity, sidecar path, count and
  diagnostic shapes, and included-career correspondence.
- Added reader-side recomputation of every table/count/diagnostic mean,
  observation count, and sample SD, plus population, origin, Stage-D,
  opening-stock denominator, and endpoint weighted-share reconciliations.
- Verified validation both before writing and after a JSON round trip,
  including all-null benefit means and valid all-zero included-career draws,
  with 18 focused tests, Black (79 columns), Ruff, and `git diff --check`.

## Next

- Complete final repository validation, push, and open the draft PR.
- Run the required quality checks, push, and open the draft PR.

## Design question for the PR

- The resumed brief explicitly requires SSA first-payment-year values through
  2022, while design §7.4 calls the extraction determination-year keyed. The
  implementation obeys the newer explicit spot checks. The benefit ledger
  will preserve the frozen statutory compounding by translating each
  post-1982 determination year to the following payment-year source row.
