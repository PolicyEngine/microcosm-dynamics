# v3 compiler continuation: the 47 codebook derivations — lane report

Repository-external authoring record. Branch `claude/ce-v3-source-compiler`,
worktree `e11-v3compiler`. Commit range `04035dd..961ee22` (five commits).
Nothing pushed. No `PROGRESS.md` in the tree at completion.

Files changed, all additions — `git diff --stat 04035dd..HEAD`:

```
scripts/verify_v3_document_derivations.py               228 +
src/populace_dynamics/data/psid_codebook_extraction.py  994 +
tests/data/test_psid_codebook_extraction.py             360 +
3 files changed, 1582 insertions(+)
```

## 0. Revision-10 identity, verified first

`docs/design/covered_earnings_correction.md` is 2,521,700 bytes with SHA-256
`4101260b94b019fc9392898059138b90386784b60ea40b9039562d364592718a`;
`covered_earnings_correction_registry.design_binding()` returns revision 10
and ratification commit `bea8b43078ea6260beab368ee59e70ea53dff02b`.
Poppler `pdftotext` is `26.04.0`, the version §19.3.3 pins.

## 1. 176/176 attestation

`scripts/verify_v3_document_derivations.py` reconstructs the complete
§19.3.2 `document_derivations` relation from the registered documents and
prints:

```
document_derivation_count 176
  dictionary_layout:      86 documents, 179,198 rows
  codebook:               47 documents, 102,179 rows
  raw_fixed_width_data:   43 documents,  89,599 rows
document_derivation_domain_sha256
  cd49d8e1777ad0e5d0df6bdcc73ace87ff0917d695397130dbf890159b0876d7
document_derivation_keyset_sha256
  c5eed4953903f247239a5c037257d6d3f91472d81b28efa1cb67aad39ac69ca7
codebook_fields 89,599   normalized entries 479,345
```

The 47 codebook documents are 43 family codebook PDFs under the pinned
page-text derivation (89,599 canonical rows, one per §20.3.7 denominator
key) plus the four 2021/2023 value-label files (3,212 + 3,212 + 3,078 +
3,078 = 12,580 rows). 179,198 dictionary rows is exactly 2 × 89,599: both
setup languages cover every field.

479,345 normalized entries is, independently, exactly the total
`code_map` row count across all six committed evidence artifacts.

### The parse

`psid_family_codebook_pages_v1` reads the pinned `-layout` page strings.
Page furniture is removed positionally, not lexically: a page's first
nonblank line is a running head exactly when it folds to the document's
modal first nonblank line, and its last nonblank line is dropped exactly
when it matches `Page n of m` or is the one page carrying no such footer.
Across the 43 documents that law is exactly regular — every page has the
banner (modulo `-layout` centering whitespace) and exactly one page per
document carries the derivation timestamp instead of a footer.

A field statement is `<id> "<label>" <format>` where the declaration is
inside §19.3.2's closed syntax (`NUM(w.d) | Fw.d | CHR(w)`). Tightening the
header to that closed set is what stops description prose such as
`Wife's/ "Wife's" brothers.` from being read as a field.

A value row is `<count> <percent> <value-or-range> <meaning>` where count is
a comma-grouped integer or the suppressed-cell dash, percent is a
two-decimal fraction or that same dash, and — the load-bearing constraint —
the two cells are dashes together or numeric together. That coupling holds
for all 479,345 committed code-map rows and is what stops a meaning
continuation such as `3 - 6` from being read as a data row.

Two source shapes need explicit handling, and both are places where the
committed evidence's `code_map` carries a column-split artifact that this
derivation resolves at source level:

- **Wrapped value cell.** V22506/1993 renders as
  `-99,997.99 - -` / `.01`, with the range separator *and* the upper
  bound's own sign left on the first line and the magnitude on the next.
  The retained lexeme is `-99,997.99 - -.01`.
- **Bracket label.** V922/1969 renders as `4 - 4 to + 4%`, which is literal
  `4` with meaning `- 4 to + 4%`, not a one-member range. §19.3.2's
  "minimum is no greater than maximum" plus the meaning's own continuation
  settle it; all nine V922 entries are literals.

`psid_stata_setup_statements_v1` handles `///` continuation, `forvalues`
loops (which compress a value span into one `numeric_range` entry), the
`label values` binding from label set to field, Stata's compound `` `"…"' ``
quoting, and the `` `=char(n)' `` escape.
`psid_spss_setup_statements_v1` handles the `VALUE LABELS` block, the
truncation comment on 2,460 of 3,212 variable lines, doubled `''`, and the
single terminal `EXECUTE.`.

## 2. Independent reproduction, not evidence laundering

§20.2.3 requires the implementation to reproduce every document derivation
independently before reading a candidate row. Three checks, all over the
complete 89,599-field denominator:

| Check | Result |
|---|---|
| V93 page-text digest under `pdftotext 26.04.0` | `22ea3467…` — byte-equal to the pinned locator |
| literal domains vs the validated classifier | **89,599 / 89,599 equal** |
| range domains (lexeme, bounds, step) | **89,599 / 89,599 equal** |
| literal-missing sets | **89,599 / 89,599 equal** |
| complete census reclassified from the derived relation | **0 fields move** |

The last row is the decisive one. Feeding the source-derived codebook
relation into the §20 classifier in place of the committed evidence
reproduces every ratified identity in §21.3.2 requirement 3:

```
counts                     [17329, 1853, 674, 47, 67316, 1145, 0, 1, 421, 813]
denominator_sha256          7e497f20e05cbdad384daece86d4aa08b16587b83cb6290193b6fdc28705b764
count_array_sha256          421105abb63991c3cc1d14d15c98ff68803f7e50dd992107fd797a01ec346624
ordered_assignment_sha256   5c9020ad92ced4916dd1152f0ce06cc276878a0ca312cd34f9d25c3c3977e72e
failure_reason_rows_sha256  66a88e6f1138c738892eeb80af22458d57c11a8033315ceba591534ce6908324
```

So requirement 8's derivations now demonstrably feed requirement 3's counts,
and the codebook relation is no longer laundered through the evidence
artifacts.

### The 2021/2023 dual-language pair

The two value-label languages are a real independent reproduction: Stata
compresses spans into `forvalues` loops, SPSS enumerates every member.
Both yield 3,212 fields for 2021 (3,078 for 2023) with identical field sets
and identical value domains after expansion. Of the 25,263 (2021)
field×value pairs, meanings agree outright on 22,653 and the remaining
2,610 fall into exactly three source-encoding differences and no others:
2,524 SPSS labels truncated at the source cap, 84 Stata apostrophes written
through `` `=char(146)' `` (whose windows-1252 expansion is U+2019 where the
SPSS file and the codebook page both carry U+0027), and 2 SPSS labels with
an outer space. All three are asserted by count in the test suite.

### Two deliberate divergences from the committed evidence

Both are recorded rather than silently absorbed.

1. **Descriptions.** 11,324 of 89,599 `full_source_description` values
   differ from the evidence, every one of them purely by internal
   whitespace folding. This derivation preserves the pinned page bytes and
   strips only leading and trailing ASCII space/tab per line, matching
   §19.3.2's exactness posture. No pinned digest depends on the choice.
2. **Meanings on 33 wrapped-cell ranges.** Where the sign is consumed into
   the upper bound, this derivation does not also retain it at the head of
   the meaning (`Actual amount of loss`, not `- Actual amount of loss`).
   The bounds are identical either way, which is why the census is
   unchanged.

## 3. The member-row field question — answered

§22 member rows need `source_entry_ref`, `value_type`, and
`typed_value_unit`. The prior lane's blocker was that the committed
evidence's `code_map_columns` are exactly
`["frequency","percent","raw_value_or_range","source_meaning"]`. That is
true, and it is also the wrong place to look: §20.2.3 forbids the evidence
from supplying a canonical row at all. The question is whether the
**derivation** supplies them. Two of the three do.

### `source_entry_ref` — derivable

§19.3.2 (design line 26479): "An entry reference is literal
`<codebook-field-row-id>:entry:<zero-based-position>` and resolves one
source entry." The codebook field row ID is itself fixed by §19.3.2 line
25805 as `<source-document-id>#row:<zero-based-source-row-position>`.
§22.2.1 line 37788 closes the loop: "The reference exact-matches the
normalized entry," and §20.3.2 line 30944 states that for a range-partition
row "the normalized range, bounds, step, type, unit, meaning, and entry
reference remain unchanged."

Derivation path, end to end: `extract_codebook_rows` fixes the document ID
and the zero-based source row position → row ID → entry position in
complete source value-list order → `entry_ref` → copied verbatim into the
range-partition row's `source_entry_ref`. This lane produces all 479,345 of
them; the V93 vector asserts the three exact strings.

### `value_type` — derivable

§19.3.2 line 26491: "A numeric range has type and disposition
`rational | json_integer`, a nonempty unit, null missing reason, and bounds
and positive step of that exact canonical type/unit." The type is therefore
fixed by the retained bounds and step, which are themselves fixed by the
source lexeme: step is `1/10^max(decimals(lower), decimals(upper))`, and the
entry is `json_integer` exactly when bounds and step are all integral.

§20.3.2 line 30938 carries it into the member row — `source_value` "is the
exact range-derived `typed_disposition`, `value_type`, `typed_value_unit`,
`canonical_value`, and `source_meaning`" — and §22.2.2 line 37810 consumes
it: "An interval numeric atom follows the normalized entry's retained value
type." The step law is not this lane's invention; it is the law whose member
counts are pinned by §22.4.5 (the 36 partial-range containers are `rational`
ranges of step `1/100`), and the derived relation reproduces the census
exactly.

### `typed_value_unit` — genuinely absent

§19.3.2 line 26058 requires that on a value-code range branch "every member
of `R` must have one common `rational | json_integer` type and one common
nonempty unit," and line 25785 says where it must come from: "a value-code
range obtains type/unit from the complete codebook domain and does not fill
a silent dictionary member by default." Line 26135 repeats it: "the
authenticated fixed-width declarations or complete codebook range domain fix
scale, output type, and unit."

The complete codebook domain does not contain a unit. Measured over all 47
registered documents:

- A codebook value block displays exactly four columns — `Count`, `%`,
  `Value/Range Code`, `Value/Range Text`. There is no unit column in any of
  the 43 PDFs, in any era.
- The two value-label documents display value and meaning only.
- The 86 setup documents declare coordinates, variable labels, and numeric
  formats. `declared_typed_value_unit` on every one of the 179,198 canonical
  dictionary rows is null, and §19.3.2 line 25782 makes that correct:
  those members "exact-normalize an express source value and otherwise are
  null."

The fixed-width escape hatch is closed empirically. `derived_parse_kind` is
`value_code_map` exactly when `C` is nonempty, and **all 89,599 fields have
a nonempty normalized-entry array** — zero fields have an empty one. So no
field is on the `fixed_width_numeric` branch, and no unit can arrive from a
coalesced dictionary declaration. 21,400 of the 89,599 fields carry at least
one numeric range and therefore assert a common nonempty unit under line
26058.

The design also fixes no unit vocabulary and no text-to-unit function
anywhere in its 39,000 lines.

The nearest thing the source has is free prose in the field description —
"The values for this variable represent dollars and cents." That is present
on only 5,469 of 89,599 fields, in 577 distinct spellings, and covers barely
a quarter of the range-bearing fields. There is no design rule that
normalizes it, and inventing one would be authoring a design identifier.

**Why this is a genuine under-determination rather than a lane failure.**
§19.3.2 line 26090 and §20.3.5 line 31309 both map an unresolved unit to
`incomplete_source_numeric_authority` — "on the value-code range branch, an
untyped or nonunitized `R` is incomplete", "unresolved
width/decimal/type/unit/scale". But the ratified §21.1.2 seven-row
closed-failure artifact contains no such resolution reason; its seven
reasons are `conflict:overlapping_numeric_ranges`,
`character_raw_replay_unknown_token`,
`observed_token_outside_all_candidate_forms_or_semantics`,
`selected_space_literal_unrenderable`,
`selected_space_range_zero_renderable`,
`finite_no_arm_no_lawful_complete_disposition`, and
`literal_only_zero_diagnostic_padding_capacity`. The ratified relation
therefore asserts that 17,329 rows compiled with a common nonempty unit
while naming no source that supplies one. Applying the design's own failure
mapping would move every range-bearing compiled row to
`incomplete_source_numeric_authority` and break the pinned count array —
which is precisely why this cannot be resolved by an implementation choice.

**This is an Amendment-9 companion issue.** It needs the same treatment the
arm-ambiguous image bytes are getting in the parallel lane: a ratified rule
naming the unit's source (a registered unit table keyed by field, a
normalization of the description prose with its own exhaustive census, or an
explicit declaration that the unit is a registration value carried outside
the source derivation), plus whatever consequential change the count array
needs.

### A second member in the same position

`missing_reason_code` fails for the same reason and should travel with it.
§19.3.2 line 26489 requires a missing literal to carry "a nonempty
source-backed reason", but the design fixes no `missing_reason_code`
vocabulary anywhere and no codebook document states one. The *disposition*
is derivable — §4.2's closed categories (blank, missing, refused, unknown,
inapplicable) are lexically stated in the meaning, and this lane's
classification reproduces the committed literal-missing sets on 89,599 of
89,599 fields — but the reason code itself has no source.

Both members are declared by
`psid_codebook_extraction.undetermined_entry_members()`, emitted as JSON
null, and `validate_document_derivation` asserts they are null rather than
letting an invented default through. That function is the single place a
future authority flips to the positive nonempty-string check §19.3.2
actually wants.

## 4. What was deliberately not done

No `pass_with_closed_failures` artifact was emitted, per the lane
instruction and independently because §21.3.2 requirement 2 still needs
`codebook_field_row_ids` resolving through complete member rows, which
requires both undetermined members plus the 56,480 arm-ambiguous image bytes
the parallel amendment is settling. Nothing in this lane makes a §21 claim;
`scripts/verify_v3_document_derivations.py` prints an attestation and writes
no file.

## 5. Verification

- `tests/data/test_psid_codebook_extraction.py`: **17 passed** (6s).
- `tests/data/` excluding the corpus suite: **585 passed, 3 skipped** (7m13s).
- `tests/data/test_psid_source_compiler_corpus.py`: **4 passed** (5m07s).
- `scripts/verify_v3_document_derivations.py`: 176/176, 221s, peak RSS
  2,915,155,968 bytes.
- `scripts/verify_v3_document_derivations.py --census`: all four ratified
  digests and the exact ten-terminal count array reproduced, 520s, peak RSS
  3,878,551,552 bytes.
- `ruff check` clean on every file touched; `black -l 79 --check` clean.
- `git diff --check` clean. No PSID raw data committed. Nothing pushed.
- Peak RSS across the lane: **3,878,551,552 bytes**, under the 8 GB ceiling.
  The extractor streams one document at a time and never materializes an
  analytic member sequence.
