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

## Next

1. Audit the implementation, fixtures, tests, and all §24 generated/pinned data.
2. Define and execute the source-wide title/header denotation census, including
   explicit defeat adjudications and V31 as a negative control.
3. Regenerate the authority/vector/pins/floors/fixtures and A10-R01..R05.
4. Repair the cumulative food count and three-act pin history.
5. Synchronize A10-R04's document contract and regenerated pins with the
   committed transactional implementation.
6. Run focused and full verification, recheck the protected prefix, write the
   final report output, then remove `PROGRESS.md` in the final commit.
