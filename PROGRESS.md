# Context report implementation progress

## State

Fixture-first implementation is in progress. Repository and ceremony
reconnaissance is complete; no production input has been opened.

## Done

- Verified the worktree was clean and on the requested branch and commit.
- Attempted to fetch `origin/master`; DNS is unavailable in the execution
  environment, and the locally recorded `origin/master` already equals the
  requested base commit.
- Verified the working design bytes equal the `origin/master` design bytes.
- Read all of `docs/design/anchor_context_extraction.md`, including the
  frozen registries, exact-complete result schema, fixture-only rehearsal
  law, and ceremony contract.
- Mapped the reusable first-estimates canonical JSON, sidecar, sealing,
  coordinator, and incident machinery.
- Added a red test for the §5.2 requirement that a sidecar publication
  failure permanently retain the partial primary report.
- Extended the shared exclusive writer with an opt-in preserve-primary mode;
  its existing rollback behavior remains the default. All 10 contract
  identity/writer tests pass.
- Added canonical, visibly fixture-only model and anchor inputs. Independent
  checks confirm exact 20-draw-by-8-year model grids, all 15 ordered
  8-year anchor series, normalized synthetic values, positive denominators,
  and pinned fixture hashes.
- Encoded the frozen 15-series, 7-metric, 14-pairing, and 9-comparison
  registries with deep-copy accessors and strict type-aware equality.
  An independent parser confirmed exact equality to the four design
  registries (15/7/14/9); ruff and diff checks pass.
- Implemented the pure comparison engine and exact-complete results
  validator. It resolves all nine operands, requires ordered 20x8 grids,
  joins flow and opening stock within draw/year, reduces ratios only after
  per-draw evaluation, and emits 56 evaluated comparison rows, two
  unavailable disclosures, 120 official levels, and 56 model levels.
- Added 21 fixture-only unit tests, including three independent formula
  recomputations and omission, duplicate, reordering, extra-ID, wrong-value,
  mismatch-array, and level-only OASI cash forgeries. All 21 pass.
- Added the canonical report configuration, artifact, input hash-gate, and
  typed append-only incident contracts. The production loader is
  registration-token gated; the fixture loader rejects either production
  path, hash, or vintage before opening any input.
- Added 43 fixture-only publication tests covering exact schemas and canonical
  bytes, hash-gate aborts, sidecar publication semantics, incident validation,
  and malformed or non-contiguous incident histories. All 43 pass.
- Implemented the fail-closed coordinator with six prelaunch checks, exact
  registered-versus-actual invocation comparison, the four ceremony phases,
  append-only incident publication, and the one-retry preparation/compute
  rule. It reuses the first-estimates lock and result/failure types.
- Added 17 fixture-only artifact-tier coordinator tests covering phase
  routing, both invariant boundaries, hash failure before engine entry,
  production-identity rejection before reads, output-absence gates,
  canonical invocation matching, frozen incident echoes, and retry law.
  All 17 pass.

## Next

- Finish and test the sealed runner and the fixture-only end-to-end rehearsal.
- Run formatting, lint, and the full estimates/publication suites.
- Commit each coherent step, update this ledger, and push the completed
  branch.
