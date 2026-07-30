# Unit 2 Fix Round Progress

## State

Implementation is in progress on `claude/ce-psid-inventory`. The referee
verdict is `SHIP WITH EDITS`; item 1 is implemented and under verification.

## Done

- Read the complete referee report.
- Confirmed the worktree is clean and on the requested branch.
- Recorded the required implementation, artifact rebuild, formatting, and
  test work in the active plan.
- Cached extraction evidence is now held as immutable bytes and decoded into
  fresh dictionaries for every caller.
- Added the exact regression that poisons the 2003 job-1 occupation row with
  ER21146's industry coordinates before a default-SHA read.

## Next

1. Make dictionary and raw fixed-width source identity mandatory at public
   reader boundaries.
2. Freeze and independently hash `SOURCE_CONCEPT_SEAMS`.
3. Preserve field-bound Stata format maps for 2021 and 2023 and rebuild the
   audit artifact.
4. Clarify the modern reader-subset test and add the remaining adversarial,
   reachability, all-wave, and person-attachment assertions.
5. Run Black and the relevant/full test suites.
