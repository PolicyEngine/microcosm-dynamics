# Amendment 7 round-1 fix progress

## State

The round-1 rewrite is in progress. The comparator blocker and precision
repairs are drafted; the exact V-B6 source-to-result dependency audit is
finishing the option-2 semantic/physical authority boundary.

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

## Next

- Ratify the resulting exact semantic/physical boundary or guarded fallback
  throughout §21.2, §21.4, regressions, ledger, fresh evaluation, and build order.
- Reverify document structure, comparator coverage, immutable prefix, bytes,
  digest, and commit history; write the final report file.
