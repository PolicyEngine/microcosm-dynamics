# Amendment 9 authoring lane — progress

## State

Branch `claude/ce-design-amendment9`, worktree `e11-amend9`, based on
origin/master at revision 10.

Revision-10 base identity (verified from Git, not assumed):
`docs/design/covered_earnings_correction.md`, mode `100644`, ratification
commit `bea8b43078ea6260beab368ee59e70ea53dff02b`, Git blob
`91fb14f3d79c28bd86217d94743d3eeeb2454a83`, 2,521,700 raw bytes, SHA-256
`4101260b94b019fc9392898059138b90386784b60ea40b9039562d364592718a`.
Inherited illustrative fence re-verified at `[241728,241899)`, 171 bytes,
SHA-256 `82118279750eea3f5f84f7dc7a458d8a0030d897d262dc756d1b635d513c4f34`,
one-based line 3,834.

## Analysis (settled)

The pull is four-way, not three-way, and revision 10 is self-blocking:

1. §20.3.2 (line 30948): "an arm-ambiguous member is unrenderable under the
   authoritative relation even when each nonauthoritative candidate has its
   own exact image" — places them in `unrenderable_member_rows`.
2. §22.4.5 (line 38269): renderable iff the renderer returns an exact-width
   image; "whether the image is arm-invariant or arm-ambiguous never moves a
   member between the two relations" — places them in
   `renderable_member_rows` (the 56,480). Later and more specific; ratified.
3. §20.3.2 (line 30952) seven-key renderable row demands ONE image, a
   DFA-path action array, a parsed scalar, and byte-equal replay.
4. §20.3.4 (line 31128) + §22.3.2 (line 38019): on this branch the DFA is
   built ONLY from `arm_invariant_member_rows`; "Candidate-specific unequal
   zero/space images are proof rows only and cannot enlarge the
   authoritative language."

Therefore the seven-key row is not merely under-determined in one key: three
of its seven keys are UNCONSTRUCTIBLE for an arm-ambiguous member. And
§22.2.3's closing sentence ("If the surrounding source/profile/arm/DFA values
do not determine one unique full row, the analytic arm is lossy and invalid")
makes any container holding such a member invalid. Fourth unsatisfiable law.

Derived lemma (confirmed twice by the ratified V117/1968 and V5092/1976
witnesses): padding is arm-independent in width, so a member renders at
exactly `w` under both candidates or neither; equal renderings are
arm-invariant. Hence **arm-ambiguous ⇒ renderable**, `arm_ambiguous_no_
authoritative_image` is unreachable as an unrenderable reason, and §22.4.5's
count rule is well-defined.

Settlement: one new six-key arm-ambiguous renderable row —
`source_member_index`, `source_value`, `physical_image_raw_token_hex` (null),
`rendered_decimal_places` (arm-invariant), `authoritative_image_disposition`,
`if_encountered`. Candidate bytes are NOT duplicated; they stay serialized
exactly once in `arm_ambiguous_member_rows`, bound by the
(`source_entry_ref`, `source_member_index`) key already present.
Lawful minimum 377 bytes > 325, so §22.4.5's floor stays a valid lower bound
and no count in the fact table moves.

Second gap RESOLVED, not escalated: §19 line 25785 ("a value-code range
obtains type/unit from the complete codebook domain"), line 26057 (common
type/unit across `R`), line 28653 ("value-code numeric ranges use
codebook-derived type/unit"), and line 25805 (`<source-document-id>#row:<pos>`
row IDs) already make the 47 codebook derivations the sole lawful source of
`source_entry_ref`, `value_type`/`typed_disposition`, and `typed_value_unit`.
Absence takes `incomplete_source_numeric_authority`; disagreement takes
`conflicting_source_numeric_format`.

## Computed fixtures (all reproduced with the repo interpreter)

- vector relation 897 B / `996ea2be…`; ID array 38 B / `6e715131…`
- A9-R01 renderable relation 38,401 B / `6496ffd0…`
- A9-R02 negative relation 38,366 B / `149ce86e…`

## Done

- Read the implementation-lane report and all governing passages.
- Fixed the analysis and computed every pinned figure.

## Next

- Draft §23 append-only; verify prefix + digest before and after.
