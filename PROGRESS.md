# Amendment 10 authoring lane — progress

Branch `claude/ce-design-amendment10`, worktree `e11-amend10`, based on
origin/master revision 11 (`9934c51`).

Target: append §24 to `docs/design/covered_earnings_correction.md` after the
byte-identical 2,653,817-byte revision-11 prefix. Subject: a ratified source
for `typed_value_unit` (the prose-to-unit extraction law) plus the honest
successor census with the unit test evaluated.

## State

- [x] Read both source reports (A9 round-2 verdict; codebook derivation lane)
- [x] Worktree identity: 2,653,817 bytes, SHA-256
      `4f6219ba7162bcc53d390a107e8db2ebe289565c6776fbda2c4acdffd0ba4609`,
      Git blob `bb11f807e7683086b55703ea28346dacec9d192e`, ratified at
      `3941e2eec27ca9c8c986c74742eb43dd62a3f830`
- [x] Task 1 — complete free-prose census from the frozen derivation
- [x] Classifier extension committed as source with 42 tests
- [x] Successor census run and cross-validated against the ratified census
- [ ] Task 2 — draft §24
- [ ] Verification and final attestation

## Established figures

- Statement census: 2,476 distinct value-denotation statements over 8,340
  fields; 1,229 name a unit; 53-row clause table; 5,096 fields take a unit.
- Successor census: `[4491, 121, 42, 0, 67316, 1145, 0, 1, 421, 16062]`,
  15,249 movements, denominator unchanged.
- §22.4.5 recompute: 4,654 compiled fields / 4,709 range entries /
  263,613,602,038 members; row floor 85,674,104,100,325 bytes
  (77.920… TiB, 59.75× capacity) — the artifact stays unconstructible.

## Next

Write §24 subsections 24.1–24.10 via the scratchpad generator, append after
the frozen prefix, verify prefix bytes before and after.

## Done

- `2e3f0b5` lane ledger; `HEAD` §24 machinery (module, runner, tests).
