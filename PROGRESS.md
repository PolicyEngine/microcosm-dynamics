# Progress

## State

Regression assertions now encode the corrected B10/B11 tuples, decoded
semantic anchors, and exact B12 exclusion. The targeted test is red against
the old locator artifact, failing first on B10 object `48 0 R` versus the
required `46 0 R`.

## Done

- Loaded the PolicyEngine fix, model-development, and standards workflows.
- Confirmed the requested branch and local-only/no-push scope.
- Recorded the bounded fix plan in `/tmp/fix-pr-plan.md`.
- Completed independent read-only inspection of the referee verdict,
  locator implementation, and repository-specific verification commands.
- Added and formatted the direct zlib-decoding semantic regression checks.
- Confirmed the new test fails against the incorrect committed locator.

## Next

- Correct the four locator tuples and all directed fact-row mappings.
- Regenerate and repin the adjudication artifact.
- Run formatting, focused tests, estimates suites, and independent
  verification.
