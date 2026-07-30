# Progress

## State

The builder now binds all PDF locators to zlib-decoded table semantics,
uses the four corrected B10/B11 streams, and rejects the exact B12
fingerprint and any decoded B12 content. An in-memory render validates at
57,125 bytes with SHA-256 `7306c898...f1abb14`; the committed artifact still
needs regeneration and repinning.

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

## Next

- Regenerate and repin the adjudication artifact.
- Run formatting, focused tests, estimates suites, and independent
  verification.
