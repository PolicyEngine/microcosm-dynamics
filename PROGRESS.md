# Amendment 10 round-3 fix progress

## State

Active on `claude/ce-design-amendment10` from audited base
`4a71b8f2cf37c8b336334aec577d5f590ae035ae`. Both round-3 verdicts are
binding. The worktree began clean, and the revision-11 2,653,817-byte prefix
was verified against blob `bb11f807e7683086b55703ea28346dacec9d192e` before
any amendment edit.

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
- Completed the pre-regeneration source-wide title/header audit over all
  89,599 fields. The independent closed scanner finds 4,055 maximal candidate
  starts in 3,978 fields: 2,261 positive starts, 1,794 explicit defeats, and
  zero unknowns. At field level this is 2,193 positive title denotations,
  1,785 defeat-only titles, and 85,621 no-match titles; 2,185 positives are
  beyond the eight referee witnesses.
- Added the contextual `TITLE_START_AUTHORITY`, title-priority field law,
  all-title audit relation, fail-closed mutation and defeat regressions, and
  rebuilt `SEGMENT_START_AUTHORITY` from the clean pre-title vector plus the
  extended adjudication. The one shared segment/start is retained as a
  contextual overlay. Exact selection cover is zero unselected/overselected;
  195 focused authority tests pass.
- Made title priority precise: subordinate construction/subrange prose cannot
  veto a direct whole-field title, the 19 exact `hours a/per week` headers
  refine subordinate bare-hour statements, and every other positive
  title/statement unit conflict fails closed.
- Integrated the complete title audit into A10-R04: the payload and gate bind
  every title count plus raw/canonical identities for both the 89,599-row
  audit and `TITLE_START_AUTHORITY`; optional `--titles` output participates
  in collision preflight, staging, validation, atomic replacement, and
  rollback. The expanded focused runner suite passes (100 tests).
- Corrected §24.2.3 to the complete two-wave food reclassification: 10/29
  followed by 108/124, cumulatively 118 predicates, 153 occurrences, and 139
  independently positive fields.
- Replaced §24.4.2's euphemistic pin-history wording with the explicit
  `148c58a` correct claim, `49ae3cb` false correction/manual-transfer story,
  and `bd5a071` evidence-route reversal.

## Next

1. Regenerate every census/authority/payload pin from the lawful raw relation.
2. Regenerate downstream floors, fixtures, and A10-R01..R05.
3. Synchronize A10-R04's document contract and regenerated pins with the
   committed transactional implementation.
4. Run focused and full verification, recheck the protected prefix, write the
   final report output, then remove `PROGRESS.md` in the final commit.
