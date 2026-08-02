# Amendment 7 round-1 fix report

## Decisive V-B6 classification

All four references are class (a), so this round implements the referee's
option 2 semantic/physical authority boundary:

| Reference | Classification | Ratified §18 relationship |
|---|---|---|
| `[1976,"V4519"]` | (a), codebook-semantic | no direct §18.2 member; transitive semantic occupation reference |
| `[1976,"V4902"]` | (a), codebook-semantic | sole direct reference: authenticated page-180 variable membership and occupation/self-employment meaning |
| `[1977,"V5429"]` | (a), codebook-semantic | no direct §18.2 member; transitive semantic occupation reference |
| `[1978,"V5916"]` | (a), codebook-semantic | no direct §18.2 member; transitive semantic occupation reference |

The audit enumerates and classifies all 13 top-level §18.2 projection members
and the complete nested inputs for members 4–8. No raw fixed-width data token,
parsing layout, padding/profile rule, numeric grammar or DFA, parsed numeric
value, executable mapping, or raw-data observation count enters the favorable
path. Whole era_fact hashes are audit-only and cannot hide physical members.

The permitted field projection has exactly 19 members per row. Each row has
28 two-member semantic code-map entries, 112 total. Independent reconstruction
reproduced all four row hashes and the exact 16,933-byte array with SHA-256
`a152aa03e61498550696e5e9ad0ba1e6e144ab375945b0452234cff0611c3b75`.

## Blocker resolutions

V-B6 now has a first-class §21.4.2 disposition separating independently
ratified semantic_code_map_registration from
physical_numeric_grammar_registration. The favorable predicate admits only
the exact semantic projection and requires an exact-empty eleven-key
source_adjudication_forbidden_dependency_rows diagnostic. A7-R10 executes the
complete source-projection-to-verified/pass path. A7-R11 tests 32 field/class
mutations plus a four-reference aggregate in both the source-boundary arm and
an ordinary nine-key physical-consumer guard arm. The §21.2 supersession list,
§21.6 ledger and closure, every fresh 22-row evaluation, bundle, and §21.9
build/lifecycle step now carry that boundary explicitly.

DC-39 now anchors §§21.1.1, 21.2, and 21.8.1 plus §21.9.2 steps 2–3. It
expressly exact-compares the accepted candidate bytes to the future same-path
D7 raw Git blob and independently checks the D6-prefix equality. The full
comparator search and consumer walk remain one same-family row: DC-01 through
DC-43, exactly 43 rows, with 21 replaced and 22 unchanged.

## Precision repairs

- Both ambiguous `§21.9 step 3` references now name `§21.9.2 step 3`.
- The A7 member listing is explicitly semantic schema order; its canonical
  artifact serializes sorted keys. The core remains exactly 6,117 bytes with
  SHA-256
  `68697967ddf8f065b051acef17c87afae7b033600d502bc1207890b253f2b1e0`.

## Final verification

- Design document: 2,247,088 bytes; SHA-256
  `4c631be85577ef71d4c48976c343e7c0824f5e9ea01a7ad47f7d88aa3d6f77c2`.
- Revision-8 prefix: first 2,049,769 bytes byte-identical to the ratified
  document; SHA-256
  `ade1a757c0b29226e7ba12f13dbe9fed7192bc85ffd67b4081bd297107e6cf4c`.
- Section 21: all 11 JSON fences parse; all 13 Markdown tables are
  rectangular; all 40 closure seeds are unique.
- Comparator census: 43 rows, 21 replaced, 22 unchanged.
- Work is Markdown-only; `git diff --check` passes; nothing was pushed.

## Commits

The exact substantive fix range is
`f0237f1857162c087a2c5e3c38f536377227e54f..1d0512e9305b13735f5308578a4024319948d336`:

1. `1b1cf30d39ff1864ac95c7d76a40e3993d581dcf` — Start Amendment 7 round-one fix ledger
2. `ef9bb27302dba98a76f32f494bcf15fe3c8cd58a` — Anchor Amendment 7 comparator identity
3. `72daec72196a68350b24331b76a6cc9b4c3a2991` — Separate V-B6 semantic and physical authority
4. `1d0512e9305b13735f5308578a4024319948d336` — Close V-B6 boundary regressions and lifecycle

The committed report/ledger closure immediately follows that range. The full
handoff range is `f0237f1857162c087a2c5e3c38f536377227e54f..HEAD` at handoff.
