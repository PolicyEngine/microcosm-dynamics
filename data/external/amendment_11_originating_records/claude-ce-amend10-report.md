# Amendment 10 authoring lane — the derived unit authority and the honest successor census

Repository-external authoring record. Branch `claude/ce-design-amendment10`,
worktree `e11-amend10`, based on origin/master revision 11 (`9934c51`).
Commit range `9934c51..80d3a5d` (nine commits). Nothing pushed. No
`PROGRESS.md` in the tree at completion.

```
docs/design/covered_earnings_correction.md        2744 +
src/populace_dynamics/data/psid_unit_authority.py  687 +
tests/data/test_psid_unit_authority.py             425 +
scripts/build_amendment10_successor_census.py      119 +
```

The three source files are the §24-specified machinery, committed separately
from the doc commits. No PSID raw data was committed.

## 0. Identity, verified before and after the append

| | |
|---|---|
| revision-11 base `D9` | commit `3941e2eec27ca9c8c986c74742eb43dd62a3f830`, Git blob `bb11f807e7683086b55703ea28346dacec9d192e`, **2,653,817** bytes, SHA-256 `4f6219ba7162bcc53d390a107e8db2ebe289565c6776fbda2c4acdffd0ba4609` |
| prefix check | candidate `[0,2653817)` **byte-compared against the complete raw blob** (`git cat-file blob`), equal, both before and after the append. Not a digest, not ancestry. |
| appended | 305,143 bytes, §24 only; appended-region SHA-256 `fd1ecb242b8dd36c95bcb408395bc47807adbfba1d7e5fd962d9534d3060cd0d` |
| candidate | **2,958,960** bytes, SHA-256 `28eccfddcb996466f08dda5cee92fd487cdacd24a99abac2e38786bafc34e57b` |

§24 spans document bytes `[2653817, 2958960)`, holds one `##`, ten `###`
matching its ten section-map rows, and 34 `####`. Zero trailing whitespace,
zero tab bytes, zero CR bytes, zero multi-blank runs, all hex lowercase; every
prose heading has a preceding blank line, and the whole document still has
zero such defects — the F9 class Amendment 9 was blocked on does not recur.
`git diff --check` clean.

## 1. Task 1 — the empirical unit-coverage census

Every figure below is derived from the frozen sources: the committed 176/176
derivations at `claude/ce-v3-source-compiler` tip `961ee22`, the 43 registered
family codebook PDFs under `pdftotext 26.04.0`, and the six pinned evidence
artifacts. Nothing is read from a report.

### The absence is total, and I verified it directly

| Claim | Measured |
|---|---|
| `declared_typed_value_unit` nonnull on any canonical dictionary row | **0 of 179,198** |
| codebook rows with an empty normalized-entry array (the `fixed_width_numeric` escape) | **0 of 89,599** |
| case-insensitive `unit` in `psid_source_compiler.py` (1,330 lines) | **0** |
| case-insensitive `unit` in `psid_source_classifier.py` (1,421 lines) | **0** |
| distinct value-block header lines across all 43 codebook PDFs | **1**, occurring **89,599** times — once per denominator field |
| nonnull `typed_value_unit` on any of the four value-label documents' 12,580 rows | **0** |

The two zero-`unit` grep rows are §24.2.3's whole argument: the ratified
census was produced by an implementation that never evaluated §19.3.2's unit
precondition, so it is not evidence that a unit exists. The last two rows
close the two places a unit could otherwise have hidden.

### The complete free-prose statement census

The census unit is the **value-denotation statement**: a maximal substring
opened by one of seven closed anchors (`The values for this variable `,
`Values for this variable `, `values for this variable `, `The value for this
variable `, `the value for this variable `, `This variable represents `,
`this variable represents `) and closed at the first `.` followed by a space
or ending the description.

| Quantity | Value |
|---|---:|
| fields in the denominator | 89,599 |
| fields carrying ≥1 value-denotation statement | 8,340 |
| **distinct statement byte strings (the spelling table)** | **2,476** |
| statement-field occurrences | 8,377 |
| codebook PDFs contributing ≥1 statement | 37 of 43 |
| distinct derived pages carrying ≥1 statement | 5,740 |
| ordered `[document,page,page-text-sha256]` locator digest | `aa93e2a2ffedf85fa4d8954d0c3b6cd17b6fc8dca5e6a4ac93f48ce65789fd32` |
| **statements naming a unit** | **1,227** |
| statements with no derivable unit | 1,249 |
| **fields taking a unit** | **5,094** |
| fields taking none | 84,505 |

### Intersection with the 19,903 compiled fields

| | Fields |
|---|---:|
| compiled fields with a prose-derivable unit | **4,652** |
| compiled fields with none | **15,251** |
| non-compiled fields carrying a unit (harmless, censused) | 442 |

The 15,251 split by reason: 12,378 carry no denotation statement at all;
2,873 carry one or more and none names a unit. Zero carry two statements
naming different units — measured, not assumed.

### The spelling→disposition machinery

The operative law is a closed **55-row clause table** mapping verbatim byte
strings to a closed **14-identifier unit vocabulary** (`count`, `day`, `hour`,
`hour_per_week`, `hour_per_year`, `mile`, `mile_per_year`, `minute`, `month`,
`percent`, `united_states_dollar`, `united_states_dollar_per_hour`, `week`,
`year`) or to `no_unit_derivable`. Matching is exact byte occurrence under
maximal munch; two distinct units, a defeating clause, or no clause all fail
closed. Eight defeating clauses exist, each grounded: `the last two digits`,
`ID number of`, `interview number of`, `marginal tax rate`, `value per room`,
`income/needs ratio`, `the ratio of`, `persons per room`, and
`number of Wife/"Wife" missed`.

Both the clause table with its per-clause grounding (55 lines, witness
statement plus document/page/page-text digest) and the complete unit-bearing
statement relation (1,227 lines, 184,780 bytes, SHA-256
`a613bf1fbdfe4110fdb87be0d9a12668dd9187137325bd24bfb1b26f2d71fd92`) are
published verbatim in `~~~text` fences in §24.3.

### What the law refuses, and why that is the point

84,505 of 89,599 fields get no unit. The refusals, in size order:

1. **81,259 fields carry no denotation statement at all.** Silence is not a
   unit.
2. **946 distinct statements are subrange-scoped** — `The values for this
   variable in the range 00001-99998 represent … in whole dollars` names a
   unit for a stated subrange and cannot discharge §19.3.2's requirement of
   one unit common to *every* member of `R`. This is the single largest
   fail-closed refusal and it costs 2,480 statement-field occurrences.
3. **166 distinct statements name no measure** — `overall income profits or
   losses`, `the annual amount contributed`, `the actual wage rate`, `the
   actual age of the Head`, and every calendar-year spelling. Several are
   obviously money or obviously years to a reader; the law does not take
   obviously.
4. **136 are defeated**, 1 conflicts.

The contrast that proves the discipline is internal to the corpus: `the actual
age in years (45-96) at which Head may retire with full benefits` takes `year`
because it writes `in years`; `the actual age (01-97) of the householder`
takes nothing because it does not.

**On the predecessor lane's 5,469 / 577.** Those figures were reported without
a stated selector and I could not reproduce them under any selector I tried.
§24 supersedes them with numbers that carry a stated, closed, reproducible
selector, and takes no position on the predecessor's arithmetic.

## 2. The successor census

`§20.3.5` prospectively **replaced** §19.3.2's failure mapping with three
mutually exclusive precedence classes — conflict, then unsupported, then
incomplete — and §20.3.7 step 5 applies that order. An unresolved unit is an
*incomplete*-class predicate, so it reaches exactly the four passing compiled
terminals and nothing else.

**This corrects the A9 round-2 referee estimate.** That review predicted six
of ten counts moving, on the reading that §19.3.2's "Satisfying more than one
failure predicate also uses `conflicting_source_numeric_format`" would promote
range-carrying members of the 421 unsupported rows. Under §20.3.5's
replacement they do not move, and the corpus confirms it in both directions:
`ER6974`/1995 is unsupported and derives no unit — stays; `V22506`/1993 is
unsupported and *does* derive `united_states_dollar` — also stays. **Five of
ten counts move, not six.**

| Terminal | Ratified | Successor | Delta |
|---|---:|---:|---:|
| `compiled_source_numeric_grammar` | 17,329 | **4,491** | −12,838 |
| `…_padding_underdetermined_exact_replay` | 1,853 | **119** | −1,734 |
| `…_finite_domain_arm_ambiguous_exact_replay` | 674 | **42** | −632 |
| `…_partial_range_exact_replay` | 47 | **0** | −47 |
| `value_code_domain_no_numeric_grammar` | 67,316 | 67,316 | 0 |
| `value_code_range_physical_rendering_unestablished` | 1,145 | 1,145 | 0 |
| `nonnumeric_source_field_outside_numeric_grammar` | 0 | 0 | 0 |
| `conflicting_source_numeric_format` | 1 | 1 | 0 |
| `unsupported_source_numeric_format` | 421 | 421 | 0 |
| `incomplete_source_numeric_authority` | 813 | **16,064** | **+15,251** |

- denominator digest **unchanged and recomputed**:
  `7e497f20e05cbdad384daece86d4aa08b16587b83cb6290193b6fdc28705b764`
- count array: `421105ab…` → `b3f8305d9b259deac6fb2cfc7ed0d1713861fa9dd8a720c09c69574a4615b19a`
- ordered assignment: `5c9020ad…` → `7ccdbda9a13c3a428a9f48dd7fd57b0d72956c8ad2b1705fbb6667d7907ed90d`
- failure-reason artifact: 7 rows / 21,034 bytes / `66a88e6f…` → **8 rows /
  272,300 bytes** / `6e575eaf9b2585ba4fcfc5365a77331dbffe41b4440e561b058154587feaee4e`
- movement relation: 15,251 rows,
  `5d33f37ffacc05061354227e4358f8a81a4055afcb26557acc5675471031c8ac`
- complete §24 census payload:
  `b70259e92b4b0e69247845265d35b6d4f71cc83605fd311202fdb18d0fba15d5`

The full status-by-artifact matrix with all ten per-status field-key digests
is in §24.4.3. The eighth failure reason is
`unresolved_typed_value_unit_no_source_authority`; all seven inherited rows
are identical in reason literal *and* field-key membership.

**The extension is a post-pass and §24 proves it is exactly equivalent.** The
unit precondition is an input to no other gate — not literal disposition, not
missing registration, not token-form or padding-arm selection, not range
partitioning, renderability, DFA construction, replay, or collision detection
— and §20.3.5 places it in the last precedence class. Its input relation is
pinned at
`563b1eaede9dcb5a085d8014dd3a4aacb2d3419ce7d0a0eb65063753b375ca6e`.

## 3. Downstream supersession

**Yes, the 56,480 moved: 56,480 → 13,303.** The arm-ambiguous branch
Amendment 9 spent an entire section settling drops from 674 fields / 1,433
range entries / 384,135 members to **42 / 42 / 120,098**, and A9-R03's third
equation `0 / 0 / 327,655 / 56,480` becomes `0 / 0 / 106,795 / 13,303`. Both
zeros survive, so §23.2.2's derivation is neither falsified nor weakened —
but **both of A9's named F2 witnesses leave the compiled relation**:
`V117`/1968 (96 range members) and `V5092`/1976 (28) each derive no unit and
take `incomplete_source_numeric_authority`. Neither is a member-row field
under §24. A6-R07's `V945`/1969 witness moves too.

The §22.4.5 fact table, recomputed:

| Fact | Ratified | Successor |
|---|---:|---:|
| compiled fields / range entries / members | 19,903 / 33,786 / 820,709,179,087 | **4,652 / 4,707 / 263,613,601,928** |
| explicit-arm members | 4,736,892 | 973,927 |
| analytic-arm members | 820,704,442,195 | 263,612,628,001 |
| analytic renderable / unrenderable containers | 9,019 / 36 | **1,500 / 0** |
| `3N+2` empty-object floor | 2,462,127,537,263 B (2.239 TiB) | 790,840,805,786 B (0.719 TiB) |
| shortest lawful row floor | 266,728,784,621,000 B (242.588… TiB) | **85,674,104,100,325 B (77.9201437583878941950388252735137939453125 TiB)** |
| multiple of ~1.304 TiB capacity | above 185 | **above 59** |
| rejected counterfactual pair | 4,753,875 / 820,704,425,212 | 975,036 / 263,612,627,002 |
| first-seven / T-minus | 88,364 / 1,235 | **73,113 / 16,486** |

**The ratified column is a recomputation, not a quotation.** The same code
that produced the successor column reproduces §22.4.5 exactly — including
4,736,892, 820,704,442,195, 9,019/36, 56,480, 327,655, the 242.588…-TiB
quotient, and the counterfactual pair 4,753,875 / 820,704,425,212, which
required getting the counterfactual's scope right (it applies only to the
arm-ambiguous branch). That reproduction is what licenses the supersession,
and it is A10-R05's second limb.

The successor analytic `unrenderable_member_rows` arm is *empty* because all
36 of its containers sat inside `…_partial_range_exact_replay`, and every one
of that terminal's 47 fields moves. The 260-byte multiplier reaches zero
members.

## 4. What Amendment 10 does not repair — stated, not buried

**A9-R04 step 5's census-reconciliation limb becomes satisfiable** and is
satisfied in fact: before §24 the step could only fail, because §23.3.1 and
A9-R04 step 3 require evaluating the precondition and no conformant
implementation that does so can reproduce the ratified counts. The
reconciliation target is now §24.4.3's census.

**The artifact remains physically unconstructible.** Shrinking the compiled
relation by 76.6 per cent of its fields takes the floor from 242.588 TiB to
77.920 TiB against ~1.304 TiB of capacity — still above 59×. Amendment 8's
unsatisfiable-law finding is about the explicit-array requirement and the
surviving member population, not about the unit, and §24 says so in terms.
A10-R05 passes only by reproducing both fact tables, publishing the expected
populations, and **refusing to emit**. The §23.9.1 V-B6 authority blocker is
untouched.

`missing_reason_code` — the second member the codebook lane found
under-determined — is **escalated, not resolved**. §24.7.1 gives it the
disposition `escalated-unresolved-by-§24.10` and §24.10.1 recommends opening
that successor now.

## 5. Verification

- prefix byte-compared against the complete raw blob before *and* after the
  append: equal.
- 155 independent figure checks: every digest, count, matrix cell, movement
  figure, downstream row, and floor in §24 recomputed from the frozen
  artifacts and found in the section's bytes. The ```json count-array fence
  re-hashes to the pinned `count_array_sha256`; the `~~~text` unit-statement
  fence body byte-equals the artifact it pins.
- all eleven quoted governing sentences confirmed verbatim in the
  byte-identical prefix (whitespace-normalized comparison).
- successor census reproduced byte-identically from a fresh process.
- `tests/data/test_psid_unit_authority.py`: **44 passed**.
  `tests/estimates/test_covered_earnings_correction_registry.py` +
  the unit-authority suite: **264 passed**. That registry suite is the only
  test in the repository that reads
  `docs/design/covered_earnings_correction.md`, so it is the one that could
  have been broken by the append; it was not. A whole-repository
  `pytest tests/` run was launched as a belt-and-braces check and was still
  executing when this record was written — its outcome is independent of this
  lane except through the three new files, whose own suite passes.
- `ruff check` clean, `black -l 79 --check` clean on all three source files.
- section structure: 1 `##`, 10 `###` matching the ten section-map rows, 34
  `####`; 58-row comparator census (30 replaced / 28 unchanged, exact cover);
  19-name successor inventory, every name absent from the revision-11 prefix
  and present in §24.
- `git diff --check` clean. Nothing pushed. Commits only on
  `claude/ce-design-amendment10` in this worktree.

## 6. One correction made mid-lane, recorded

The first assembled draft had two clause defects that a fence audit caught:
the generic `number of` clause read `the number of persons per room` as a
`count` (a density is not a count), and the typo variant `dollar and cents`
captured `dollar and cents amount per hour` before its per-hour tail. Both
were fixed by adding closed clauses — the defeater `persons per room` and
`dollar and cents amount per hour` → `united_states_dollar_per_hour` — taking
the table from 53 to 55 rows, and **every dependent figure in §24 was
regenerated** rather than patched. The census moved from
`[4491, 121, 42, 0, …, 16062]` to `[4491, 119, 42, 0, …, 16064]` and the
movement from 15,249 to 15,251. Commit `150e3ea` records it. Every numeric
figure in §24 is now emitted by a generator reading the computed artifacts, so
the class of drift that produced this cannot recur silently.

## 7. What a referee should attack first

1. **The anchor set's closure.** Seven anchors, chosen to be value-denotation
   openers. `This variable is/was/contains` is excluded as provenance rather
   than denotation. The exclusion is fail-closed — it can only withhold a unit
   — but it is a judgement, and it is the widest one in §24.3.
2. **The subrange refusal.** 946 statements and 2,480 occurrences are refused
   because they scope to a stated range. A successor could lawfully compare
   the stated bounds to `R` and admit the ones that cover it. §24 declines to
   author that second derivation over prose numerals; a referee may reasonably
   argue it should.
3. **Two vocabulary decisions.** A denominator enters the unit only when the
   prose writes `per <period>` (so `hours per week` → `hour_per_week` but
   `annual hours` → `hour`), and no calendar-year coordinate is in the
   vocabulary. Both withhold rather than grant; both are visible in the clause
   table with their counts.
4. **The post-pass equivalence argument** at §24.4.2. It is a claim about
   which gates the unit precondition feeds. It is checkable against §19.3.2's
   compile block and §20.3.5's precedence, and it is the load-bearing step
   that lets §24 supersede the census without re-running every gate.
