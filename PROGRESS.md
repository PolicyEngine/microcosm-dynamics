# Amendment 10 round-3 fix progress

## State

Active on `claude/ce-design-amendment10` from audited base
`4a71b8f2cf37c8b336334aec577d5f590ae035ae`. Both round-3 verdicts are
binding. The worktree began clean, and the revision-11 2,653,817-byte prefix
was verified against blob `bb11f807e7683086b55703ea28346dacec9d192e` before
any amendment edit. A final independent audit invalidated the first expanded
title census before release: generic unit tokens in question-style titles
were still suppressed. The title census, successor vector, storage floors,
and all derived pins below are therefore being rebuilt from the clean
pre-title authority rather than treated as final.

## Done

- Read both verdicts in full and reconciled their union into four work items.
- Reproduced the starting document length (3,435,048 bytes) and SHA-256
  (`ab4f132b6ba655054f4dbd64672b5275f99fe822406df4103c9dff70df84ca72`).
- Confirmed the requested branch and starting commit exactly.
- Implemented A10-R04 transactional emission in commit `1f1c80c`: all outputs
  are staged, byte-count/SHA-256 validated, atomically replaced, and rolled
  back together on replacement failure. Added second-replacement failure
  injection and changed CLI stdout from truncated to complete JSON. The
  focused runner suite passes (78 tests).
- Added the first contextual `TITLE_START_AUTHORITY`, title-priority field
  law, all-title audit relation, fail-closed mutation and defeat regressions.
  Its 4,055-start census is retained only as an intermediate checkpoint: it
  is not an acceptable final totality proof because the discovery grammar
  omitted clear question-title denotations including miles, hours, days,
  months, and dollar-cost fields.
- Made title priority precise: subordinate construction/subrange prose cannot
  veto a direct whole-field title, the 19 exact `hours a/per week` headers
  refine subordinate bare-hour statements, and every other positive
  title/statement unit conflict fails closed.
- Integrated the complete title audit into A10-R04: the payload and gate bind
  every title count plus raw/canonical identities for both the 89,599-row
  audit, the 12-row title-literal grammar, and `TITLE_START_AUTHORITY`;
  optional `--titles` output participates in collision preflight, staging,
  validation, atomic replacement, and rollback. The expanded focused runner
  suite passes (105 tests).
- Corrected §24.2.3 to the complete two-wave food reclassification: 10/29
  followed by 108/124, cumulatively 118 predicates, 153 occurrences, and 139
  independently positive fields.
- Replaced §24.4.2's euphemistic pin-history wording with the explicit
  `148c58a` correct claim, `49ae3cb` false correction/manual-transfer story,
  and `bd5a071` evidence-route reversal.
- Proved the first schema-v3 production gate transactional and streaming:
  it emitted and reparsed all requested outputs with peak RSS 1,163,018,240
  bytes, and complete stdout was byte-identical to the payload file. Its
  census, vector, and derived pins are now deliberately superseded by the
  reopened exhaustive audit.

## Next

1. Expand first-line discovery to the complete closed title-unit grammar,
   using exact ASCII word boundaries and no question-title suppression.
2. Adjudicate every discovered start over all 89,599 fields, prove zero
   unknowns, and rebuild `SEGMENT_START_AUTHORITY` from the clean pre-title
   baseline.
3. Regenerate the successor vector, all pins, storage floors, fixtures, and
   §24 claims; run focused and full verification and recheck the prefix.
4. Write the final report output and remove `PROGRESS.md` in the final commit.
