# Unit 2 Fix Round Progress

## State

Implementation is in progress on `claude/ce-psid-inventory`. The referee
verdict is `SHIP WITH EDITS`; items 1 through 3 are implemented and under
verification.

## Done

- Read the complete referee report.
- Confirmed the worktree is clean and on the requested branch.
- Recorded the required implementation, artifact rebuild, formatting, and
  test work in the active plan.
- Cached extraction evidence is now held as immutable bytes and decoded into
  fresh dictionaries for every caller.
- Added the exact regression that poisons the 2003 job-1 occupation row with
  ER21146's industry coordinates before a default-SHA read.
- Removed `require_dictionary_sha` from all public reader APIs; synthetic
  tests use only a private identity-validation seam.
- Registered path, size, and SHA-256 for all 43 staged raw family `.txt`
  files and made every physical-field row cite its raw source.
- Production reads now validate both dictionary and raw-file identity before
  parsing or slicing, with same-size SHA and raw-path adversarial coverage.
- `SOURCE_CONCEPT_SEAMS` rows are immutable mapping proxies, and the complete
  seam registry has an independent canonical SHA-256 checked by
  `validate_frozen_registry`.
- Added direct immutability coverage and a V4379 `mixed` to `wages_only`
  mutation that must fail the frozen-registry hash check.

## Next

1. Preserve field-bound Stata format maps for 2021 and 2023 and rebuild the
   audit artifact.
2. Clarify the modern reader-subset test and add the remaining adversarial,
   reachability, all-wave, and person-attachment assertions.
3. Run Black and the relevant/full test suites.
