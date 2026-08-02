# Amendment 7 round-1 fix progress

## State

The round-1 rewrite is in progress. The ratified prefix is verified, and the
V-B6 source-to-result dependency audit is deciding between the required
semantic/physical authority boundary and the guarded non-passing fallback.

## Done

- Read the complete round-1 referee verdict.
- Confirmed branch `claude/ce-design-amendment7` starts at
  `f0237f1857162c087a2c5e3c38f536377227e54f` with a clean worktree.
- Verified the current document's first 2,049,769 bytes exactly equal the
  complete revision-8 document at `e6866bfa`, with SHA-256
  `ade1a757c0b29226e7ba12f13dbe9fed7192bc85ffd67b4081bd297107e6cf4c`.
- Began an exact inventory of every ratified §18 V-B6 projection input and
  the §13.2 registration-or-abort scope.

## Next

- Complete and independently cross-check the class-(a)/(b) V-B6 inventory.
- Ratify the resulting exact semantic/physical boundary or guarded fallback
  throughout §21.2, §21.4, regressions, ledger, fresh evaluation, and build order.
- Repair and rerun the comparator census, then apply the two precision fixes.
- Reverify document structure, comparator coverage, immutable prefix, bytes,
  digest, and commit history; write the final report file.
