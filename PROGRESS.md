# Unit 2 Fix Round Progress

## State

Implementation and verification are complete on
`claude/ce-psid-inventory`. The referee verdict is `SHIP WITH EDITS`; all
five required-before-merge items are implemented and committed.

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
- Black 25.11.0 reports all 16 branch-modified Python files unchanged at line
  length 79.
- Both committed PSID artifacts reproduce byte-for-byte from the staged source
  data.
- The complete PSID/referee suite passed: 107 passed and 3 skipped.
- The literal full suite produced 4,215 passes and 95 skips; its only failure
  was the expected tier-count drift from the newly added tests. The manifest
  is now updated to the collected 4,311-test domain, and the tier-policy gate
  passes with 4,310 tests deselected.
- Rebuilt dictionary-audit file SHA-256:
  `e06eec5de5fd0215dbea40bba49366e3ef940cc253a11c7da8109133bfb7dcb0`.
- Rebuilt physical-reader registry file SHA-256:
  `22b9d773f935a713ec63fd93fcbc6367a6f4047d962270d48471fdb39cbcbb17`.

## Next

Ready for review and merge; no push was performed.
