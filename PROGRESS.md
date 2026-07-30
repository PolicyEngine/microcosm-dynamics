# Progress

## State

The canonical artifact has been regenerated and repinned at 57,125 bytes
with SHA-256 `7306c898...f1abb14`. Its structured diff changes only the four
locator bindings and integrity digest; fact classifications, evidence-ID
lists, vintage bytes, and fail-closed dispositions are unchanged. The
focused adjudication suite passes.

## Done

- Loaded the PolicyEngine fix, model-development, and standards workflows.
- Confirmed the requested branch and local-only/no-push scope.
- Recorded the bounded fix plan in `/tmp/fix-pr-plan.md`.
- Completed independent read-only inspection of the referee verdict,
  locator implementation, and repository-specific verification commands.
- Added and formatted the direct zlib-decoding semantic regression checks.
- Confirmed the new test fails against the incorrect committed locator.
- Corrected the four B10/B11 locator tuples, which repoints all 14 affected
  fact rows through their existing semantic locator IDs.
- Added semantic anchors for every captured PDF stream and explicit B12
  rejection in `_pdf_locator`.
- Confirmed the corrected builder renders and validates in memory.
- Regenerated the adjudication artifact and updated its pinned test digest.
- Verified the artifact diff is limited to the four corrected locator
  objects/ranges/hashes plus the derived integrity digest.
- Passed all 14 membership-adjudication tests.

## Next

- Run formatting, focused tests, estimates suites, and independent
  verification.
