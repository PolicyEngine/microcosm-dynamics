# Amendment 7 round-1 fix progress

## State

The substantive round-1 rewrite is complete and entering final mechanical
verification. Both blockers, both precision repairs, the regressions, and
all required lifecycle/build consumers are now closed in the document.

## Done

- Read the complete round-1 referee verdict.
- Confirmed branch `claude/ce-design-amendment7` starts at
  `f0237f1857162c087a2c5e3c38f536377227e54f` with a clean worktree.
- Verified the current document's first 2,049,769 bytes exactly equal the
  complete revision-8 document at `e6866bfa`, with SHA-256
  `ade1a757c0b29226e7ba12f13dbe9fed7192bc85ffd67b4081bd297107e6cf4c`.
- Began an exact inventory of every ratified §18 V-B6 projection input and
  the §13.2 registration-or-abort scope.
- Reran the full revision-9 comparator search and consumer walk. The
  candidate-bytes/future-D7-blob equality is part of DC-39, so the census
  remains 43 rows with 21 replaced and 22 unchanged.
- Extended DC-39 through §21.2 and §21.9.2 steps 2–3, corrected both
  ambiguous §21.9 step references, and distinguished A7 semantic schema
  order from canonical sorted-key serialization without changing its bytes.
- Verified all four V-B6 references are class (a). Only V4902 is a direct
  §18.2 input; V4519, V5429, and V5916 are transitive semantic references.
- Added the exact four-row, 19-member semantic projection and the first-class
  §21.4.2 boundary. Semantic and physical registration are non-conflatable;
  every forbidden physical dependency still invokes the atomic abort guard.
- Enumerated and classified all 13 §18.2 projection members and their nested
  inputs; whole era_fact hashes are audit-only, so physical coordinates cannot
  enter the favorable semantic predicate through a digest.
- Added A7-R10's complete §18-projection-to-verified/pass regression and
  A7-R11's 32 per-field physical mutations plus four-reference aggregate
  abort. The negative vector proves both the exact eleven-key source-boundary
  diagnostic and the ordinary nine-key physical-consumer guard, without
  changing the exact nine-row A7 core payload.
- Updated §21.6's explicit V-B6 dispositions and closure seeds, the V-B6
  result in every fresh 22-row evaluation and bundle, and every §21.9 build,
  ratification, receipt, registration, and production step.
- Removed the compiler/vector circularity: §21.3 accepts only after unchanged
  A6, then A7-R01–R11 gate Q5; complete preliminary/final 22-row domains remain
  in their §21.8/§21.9 lifecycle positions.

## Next

- Reverify document structure, comparator coverage, immutable prefix, bytes,
  digest, and commit history; write the final report file.
