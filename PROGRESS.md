# Unit 2 Fix Round Progress

## State

Implementation is in progress on `claude/ce-psid-inventory`. The referee
verdict is `SHIP WITH EDITS`; all five required-before-merge items are
implemented and under verification.

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
- Removed caller-supplied registry/audit paths from the public evidence and
  reader APIs, so self-sealed alternate authority artifacts cannot bypass the
  committed identities.
- Registered path, size, and SHA-256 for all 43 staged raw family `.txt`
  files and made every physical-field row cite its raw source.
- Production reads now validate both dictionary and raw-file identity before
  parsing or slicing, with same-size SHA and raw-path adversarial coverage.
- Dictionary parsing and raw slicing now consume the same validated immutable
  byte snapshots, closing the hash-then-reopen race.
- `SOURCE_CONCEPT_SEAMS` rows are immutable mapping proxies, and the complete
  seam registry has an independent canonical SHA-256 checked by
  `validate_frozen_registry`.
- Added direct immutability coverage and a V4379 `mixed` to `wages_only`
  mutation that must fail the frozen-registry hash check.
- Parsed and preserved all 3,212 (2021) and 3,078 (2023) field-bound Stata
  format maps, including their 25,263 and 23,374 exact code-label rows.
- Cross-checked every preserved map against the SPSS field/code domain and
  physical layout, independently hashed each wave's maps, and retained both
  format-document identities.
- Independently pinned the path, size, SHA-256, role, and encoding of all four
  2021/2023 format sources.
- The audit validator now rejects resealed attempts to discard positive map
  evidence, forge its source identities, or claim ratification/source-byte
  reproduction while V-B5/V-B6/V-B8 remain unresolved.
- Added RP, spouse, enrollment, parser-grammar, fail-close, nested-integrity,
  and 210-of-281 modern-reader map-coverage tests.
- Renamed the 3,123-row assertion as the declared physical-reader subset and
  explicitly distinguished it from `psid_questionnaire_slot_specs.v1`.
- Added real default-identity reads for all eleven modern waves, a static
  reachability proof for the four birth-identity exclusions, and a public-API
  signature guard.
- Person attachment now fails before joining when the raw family-interview
  token disagrees with the typed family interview; the synthetic 7-to-9
  mismatch is covered.
- The exact ER21146 cache-poison regression now also pins
  `reader_field_id=occupation_raw` and `raw_token_hex=202030`.

## Next

1. Run Black and the relevant/full test suites.
2. Record the final artifact hash and test disposition.
