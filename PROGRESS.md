# Amendment 8 round-2 repair progress

## State

In progress: independently review and mechanically attest the committed A8-R04 correction.

## Done

- Confirmed the clean `claude/ce-design-amendment8` checkout at audited HEAD `b635f84ac6ff45d6c49e03bc54d633c64b7c854d`.
- Read the complete round-2 referee verdict.
- Located the A8-R04 fact table and direct textual dependents.
- Reauthenticated the 176-document source manifest, including all 43 raw fixed-width files, and reproduced the 89,599-field census pins.
- Re-derived the per-relation §22.2.2 partition: 820,709,179,087 total members = 4,736,892 explicit-arm members + 820,704,442,195 analytic-arm members.
- Derived the 325-byte shortest lawful seven-key row and exact 266,728,943,713,375-byte / 242.5885611168041577911935746669769287109375-TiB product.
- Verified the 2,423,590-byte revision-9 prefix byte-for-byte before the document edit.
- Corrected only the A8-R04 fact table and its direct provenance and lower-bound prose in commit `2e0dde6c4f0179ff010cb732623d9e1bb6d70eb4`.
- Reverified the locked prefix byte-for-byte after the document edit; the corrected document is 2,519,313 bytes with SHA-256 `28120452f301e291518029b6e7ca52c40ccc20583aba7ad80f822716c794ac42`.

## Next

- Complete independent review and mechanical validation.
- Record final verification, remove this temporary ledger, and report the exact commit range without pushing.
