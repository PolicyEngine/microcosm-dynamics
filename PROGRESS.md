# Unit 2 Fix Round Progress

## State

Implementation is in progress on `claude/ce-psid-inventory`. The referee
verdict is `SHIP WITH EDITS`; all five required-before-merge items remain
open at this baseline.

## Done

- Read the complete referee report.
- Confirmed the worktree is clean and on the requested branch.
- Recorded the required implementation, artifact rebuild, formatting, and
  test work in the active plan.

## Next

1. Fix cached extraction-evidence poisoning and add the exact ER21146
   coordinate-poisoning regression.
2. Make dictionary and raw fixed-width source identity mandatory at public
   reader boundaries.
3. Freeze and independently hash `SOURCE_CONCEPT_SEAMS`.
4. Preserve field-bound Stata format maps for 2021 and 2023 and rebuild the
   audit artifact.
5. Clarify the modern reader-subset test and add the remaining adversarial,
   reachability, all-wave, and person-attachment assertions.
6. Run Black and the relevant/full test suites.
