# Progress

## State

- Branch `claude/bench-rows-tranche2` starts clean at
  `e6866bfaef5fc81771236ce58b9b6d166fb3aaf9`, matching `origin/master`.
- The audited inventory is 997 logical lines (996 newline terminators) / 43,614
  bytes with SHA-256
  `43cec7d1ff2373f70d661f4557e9eecbc9be041a939882a3ee209918a7d5d029`.
- Its complete tranche is 30 CBO model-triangulation rows, 19 MINT
  model-triangulation rows, and 11 SSA 4.B7 admin-truth rows.
- The audited 60-row tranche is not yet added to the registry.
- GitNexus repository resources are unavailable in this session; harness
  behavior will be verified from repository source and tests.
- The current history validator rejects null model measurements and numeric-free
  missing-module deviations, so it must be narrowed to permit those only for
  `module_missing` records while retaining fail-closed behavior elsewhere.

## Done

- Confirmed the requested branch and clean starting point.
- Loaded the applicable codebase-exploration workflow and checked for its
  repository resources.
- Read the audited inventory completely, including both standing corrections:
  CBO 55038 has replacement-rate rather than benefit/tax PV material, and the
  MINT pages supply neither beneficiary-type denominators, dual-only numerators,
  nor taxpayer birth cohorts.
- Recorded the seven verified capture identities and manifest SHA-256
  `72c180e8d162d9cc09017c355214ba0f9e1175b2d79f294ec2de96ee28cb2e1a`.
- Traced schema v4 registry validation, append-mostly revision law, exact source
  pin requirements, one-sentence gap-note alarm, complete-prefix history sets,
  append-only run manifests, staged-artifact checks, and committed-HEAD binding.
- Confirmed benchmark tests live in `tests/test_benchmarks.py`; their frozen seed
  prefix identities stay fixed while current registry/history/wall identities
  and census expectations must advance with the tranche.
- Verified the staging manifest before reading it: 12,042 bytes, 30 canonical
  entries, SHA-256 `72c180e8d162d9cc09017c355214ba0f9e1175b2d79f294ec2de96ee28cb2e1a`.
- Verified all seven audited capture hashes before parsing: CBO 55038
  supplemental, all three CBO 60392 workbooks, both MINT table pages, and the
  committed SSA Supplement 4.B snapshot all match the inventory exactly.
- Independently reproduced every omitted selector/transform value: the 15 MINT
  percentile-shape trajectories, 11 SSA 4.B7 same-panel band shares, and six CBO
  annual/indexed panels all agree with the audited locators and corrections.
- Added a deterministic SSA 4.B7 extractor that verifies both the committed HTML
  snapshot and its local capture manifest before emitting a 14,840-byte JSON
  extraction with SHA-256
  `c856acfc7d5fad8cb4143134f10fa48471255c87848194276ac8a9c46ec07bcb`.
- Resolved the nonduplication note as 59 new IDs plus one revision of the legacy
  CBO tax-revenue row; the final registry should therefore contain 101 rows.

## Next

- Add focused schema tests for null model values restricted to missing modules.
- Add and validate all 60 rows, append one history evaluation, and bind the run
  manifest to the final registry commit.
- Remove this ledger before final delivery while preserving its committed
  history.
