# Vintage-1 Anchor Extraction Progress

## State

The builder, canonical artifact, and 20-test reproduction/fail-closed suite
are implemented; final repository-wide verification remains.

## Done

- Confirmed the requested branch and worktree.
- Confirmed the six committed SSA source snapshots and
  `capture_manifest.txt` are present.
- Read the ratified design's sections 2–3 and recorded every identity,
  locator, status, provenance, canonicalization, and fail-closed requirement.
- Mapped the exact eight table captions and nested row/column header paths.
- Confirmed the reproduction-test and tier-manifest conventions.
- Independently cross-checked all 120 snapshot cells against the scoping
  survey: 120 exact matches and no divergence.
- Implemented the offline builder with manifest and six-snapshot hash gates,
  exact nested cell locators, source-status evidence, complete schema
  validation, and a canonical determinations-value pin.
- Generated the 120-cell compact canonical artifact at SHA-256
  `adc782a1a11c50969103c125a82b1539a7017241662d545d86bc6fc9227730c1`.
- Confirmed byte-identical reconstruction on Python 3.10, 3.11, 3.13, and
  3.14 and confirmed tampered sources, reordered IDs, and wrong-cell locators
  abort.
- Completed an independent builder audit; retained VI.G1's published caption
  subtitle in its exact title and bound source/build/validation metadata
  directly back to the verified manifest and frozen literals.
- Added a full-file SHA/canonical rebuild pin, the independent 15-by-8 survey
  literal grid, unit/scale/status/locator/source assertions, and negative
  tests for every fail-closed requirement class.
- Confirmed all 20 focused tests pass and updated the unit tier from 848 to
  868; collection now reports the expected 3,678 total tests.

## Next

- Run the focused and full checks, write the final report, and push the
  completed branch.
