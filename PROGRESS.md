# Vintage-1 Anchor Extraction Progress

## State

Implementation and verification are complete. The builder, canonical
artifact, and 22-test reproduction/fail-closed suite are committed and
independently audited; push is blocked by the managed environment's disabled
GitHub DNS/network path.

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
- Strengthened the global pre-parse source-hash test by mutating the sixth
  snapshot without changing its size, pinned the two reviewed status-evidence
  literals, and exact-checked every manifest path and per-series table title.
- Confirmed all 22 focused tests pass and updated the unit tier from 848 to
  870; collection now reports the expected 3,680 total tests.
- Confirmed the complete unit tier passes with 865 passed, 5 skipped, and
  2,810 deselected; the tier-policy manifest test passes against the complete
  collected inventory.
- Confirmed repository-wide `black -l 79 --check` leaves all 491 Python files
  unchanged, repository-wide Ruff passes, and `git diff --check` is clean.
- Completed two independent current-HEAD compliance audits with no remaining
  correctness findings and reconfirmed the canonical artifact SHA-256 as
  `adc782a1a11c50969103c125a82b1539a7017241662d545d86bc6fc9227730c1`.
- Attempted the requested push; Git failed with `Could not resolve host:
  github.com`. The GitHub connector confirmed that the remote branch remains
  at snapshot commit `130694b` and does not contain the local HEAD object, so
  it cannot move the ref without replacing the committed local history.

## Next

- Push `claude/anchor-extraction-v1` when GitHub network access is available.
