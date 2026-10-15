APPROVE

The B2 record is sound, and both of round 8's findings are fixed in substance. I found no high or medium finding and two low ones. Both are gaps in the read log's pattern classifier and bear only on the review tooling. I met no reference-year 2012 or 2014 gate statistic, floor, truth moment or candidate outcome, and no 2008 or 2010 selector outcome.

## Findings

### High
None.

### Medium
None.

### Low

**L1. An unbalanced `{` placed before a brace group stops that group from being expanded.** *(Review tooling only.)*
- **Where:** `scripts/track_b_b0_1_review_root.py:276-277`, and the cut of the pattern as written at `:316-318`.
- **What is wrong:**
  - `brace_expansions` scans from the first `{`. If that brace never closes, it returns the whole pattern unchanged, so any balanced group later in the pattern is never expanded.
  - The docstring (`:256-257`) and the test comment (`tests/test_track_b_b0_1_review_root.py:553-554`) both say an unbalanced brace is literal text. Under that reading, a later group should still expand: bash and minimatch would turn `{,<stem-head>{<stem-tail>,y}.md` into a literal `{,`-prefixed form of `<stem>.md`.
  - The fallback cut at `[/{},]` does not rescue it either. It splits the name into its head, its tail and `.md`, and no piece is a denied basename or a stem followed by a dot.
  - So a pattern built this way is classed `inside_root`.
- **Tests:** `:639` checks only `{a,b`, and `:555-565` only an unbalanced group that holds the whole basename. No test covers an unbalanced brace before a balanced group.
- **Why it matters:** Section 15 (`docs/design/track_b_b0_1_addendum.md:1382-1383`) says a name split across a group is read whole. That claim does not hold for this shape.
  - The risk is small: ripgrep's globset rejects an unclosed `{`, so Grep filters would probably fail rather than match. I could not confirm which glob engine the Glob tool uses.
  - No recorded round is affected. The patterns of rounds 5-8 hold no unbalanced brace (`readlog_r5.json:76-81`, `readlog_r6.json:77-81`, `readlog_r7.json:78-81`, `readlog_r8.json:27-30`).
- **Smallest fix:** When the `{` at `start` is unbalanced, keep it as literal text and continue scanning from `start + 1`, the same way the no-comma branch does at `:293`. Add a test that `{,deep_{denied,y}.md` is classed `denied`.

**L2. A whole denied stem followed by a wildcard instead of a dot still passes.** *(Review tooling only.)*
- **Where:** `scripts/track_b_b0_1_review_root.py:325-327`; the disclosure at `addendum.md:1380-1381`.
- **What is wrong:** The stem rule only flags a segment that starts with `<stem>.`. These forms all pass as `inside_root`, and each matches the denied file:
  - `**/<stem>?md`
  - `**/<stem>[.]md`
  - `**/<stem>*`

  Section 15 discloses only "a wildcard fragment of a name, such as `*name_part*`". These are not fragments: each holds the whole stem, and they are the plainest wildcard ways to name the file. The review prompt forbids putting a stem in a pattern at all, but the log does not enforce that.
- **Why it matters:** This is the remaining answer to Question 1's "does any plain way still pass". No recorded round's pattern has this shape (same citations as L1).
- **Smallest fix:** Within each alternative, also flag a segment that `fnmatch`es a denied basename and contains that basename's stem literally. That catches the three forms above, and `**/*`, `**/*deep*` and `deep_denied_notes.md` (`tests/...review_root.py:567-588`) still count. If you keep the current rule instead, widen the disclosure at `addendum.md:1380-1381` to name these forms.

**Observation, not a finding.** The read-log schema is still `track_b_b0_1_review_read_log.v5` (`review_root.py:422`) even though round 8 changed the classifier. A log made before the fix cannot be told apart from one made after it. Bumping the schema to v6 would record which rule a log was made under.

## Answers

**1. Dispositions**
- **L1: resolved in substance, apart from the two gaps above.**
  - **Nested groups** expand correctly: depth tracking, commas counted only at depth 1, and recursion on each alternative (`review_root.py:262-292`). The test checks `a{b,{c,d}}e` → `abe, ace, ade` (`tests/...review_root.py:633`).
  - **Groups with no comma** are kept as literal text, and scanning moves on to the next `{` (`:293`). `{a{b,c}}` → `{ab}, {ac}` matches bash (`:638`).
  - **Unbalanced braces** are literal, but they also stop any later expansion (my L1).
  - **The 4,096 limit** gives `unclassified`, which voids the review (`:290-291`, `:311-314`, `:420`). The tests cover the limit and one over it (`:641-644`).
  - **Tests:** a property test cuts a denied basename or the codebook directory at any two points under four prefixes (`:662-678`); a no-false-positive invariant (`:681-690`); a differential test showing the new rule is no weaker than round 7's (`:693-711`); and transcript cases g12-g16 (`:503-565`), including round 8's own `**/{deep_denied,x}.md`.
  - **Splits across `/`** are caught, because each alternative is checked against the full denied paths (`:322`).
- **L2: resolved.**
  - Section 5 now reads "If the ladder ends below 0.90, a guard fails, or ν is 0 after section 7's merges" (`addendum.md:261-262`).
  - Section 7 gives the cause and the stop (`:378-381`).
  - Section 9's step 4 stops at floor build and points to sections 5 and 7 (`:471-474`).
  - The "To B2" list does the same (`:1113-1116`).
  - All four agree on the outcome (`WEAK_POWER_OR_VACUITY`), the timing (floor build, before any candidate run) and the quantity (ν after the merges). The new wording is pinned (`tests/test_track_b_b0_1_addendum_record.py:785-800`). The `prose` fixture collapses whitespace (`:43-44`), so the line breaks at `addendum.md:261-263` still match.

**2. New problems**
- **Inconsistency:** none in the B2 record.
  - Section 5's closing line, "This covers every case d693's Q2 flip names" (`addendum.md:266`), is still true, because the triggers are now a superset.
  - One minor point, not a finding: section 5 queues "the rescoping options" for Max (`:264-265`). Rescoping the surface or the tolerance cannot cure ν = 0, because t\* stays undefined. The stop itself is correct.
- **Freedom after a candidate outcome:** none. The ν = 0 stop is fixed from design variables before any candidate run, and section 8 limits rescoping to floor build (`:452-455`).
- **Rulings:** what d781, d782 and d1342 decided is unchanged. The household floor splits are unchanged (`:364`), and so is the ruled six-cell surface (`:202-223`).

**3. Protocol and blindness**
- Every changed passage lies before section 16, which starts at `addendum.md:1764`. The protocol block's hash is pinned by `tests/test_track_b_b0_1_addendum_record.py:54-56`, but I could not recompute it.
- The new tests use invented paths (`DENIED`, `tests/...review_root.py:626`). The changes expose no B2 outcome and no 2008/2010 selector outcome. The denied file names in `root_r8.json:50-104` are the committed exclusion record, not outcomes.

**4. Records: they match.**

| Section 15 says (`addendum.md:1725-1755`) | Records say |
|---|---|
| Head `1e4d226`, 1,946 files, manifest `73c0d9c2f409eaaa…` | `root_r8.json:73-75` |
| 27 files removed whole (21 denied plus 6 codebook files) | `root_r8.json:50-72`, `:76-104` |
| Four code-map tables removed | `root_r8.json:105-110` |
| Ten context copies | `root_r8.json:8-48` |
| 22 tool calls; the review counts | `readlog_r8.json:3`, `:39-41`; I counted the 22 entries at `:44-147` |
| `APPROVE`, no high or medium finding, two low | `review_r8.md:1-31` |
| L1 and L2 as round 8 stated them | `review_r8.md:15-29` |
| Its Grep-prefix observation is left as it is | `review_r8.md:31`; the prefixes show at `readlog_r8.json:5`, `:33`, `:37` |
| Rounds 5-8 regenerated: round 5 stays void, rounds 6-8 count | `readlog_r5.json:81`, `:195`; `readlog_r6.json:133`; `readlog_r7.json:195`; `readlog_r8.json:41` |

- The four patterns in round 8's log (`readlog_r8.json:27-30`) match the filters its review lists (`review_r8.md:96-100`).
- The tier counts add up to 12,667 in both `tests/tier_counts.json:4-8` and `tests/README-tiers.md:42-47`, 15 more than round 8's 12,652.

## What I could not check from inside the root
- The protocol block's SHA-256, whether CI passes, whether the tier counts match the collected tests, and the "six mutants" claim. I ran no code.
- Which glob engine the Glob tool uses, and so whether L1's pattern would actually match there.
- Round 8's transcript, prompt and run times (22:11-22:14 UTC), and whether the inventory rerun (`inventory_r8.json`) flagged nothing new beyond its existence.
- Whether the round 5-7 logs were regenerated with this head's tool. The unchanged v5 schema cannot show it.
- This round's root record and read log.
- I wrote no plan file: this session has no write tool, and the review needed none.

## Read log (relative to the root)
- **Read:**
  - `scripts/track_b_b0_1_review_root.py` (lines 150-479)
  - `tests/test_track_b_b0_1_review_root.py` (lines 440-729)
  - `docs/design/track_b_b0_1_addendum.md` (lines 200-499, 980-1059, 1090-1129, 1339-1773)
  - `docs/design/track_b_b0_1_addendum_q6_review_r8.md`
  - `docs/design/track_b_b0_1_addendum_q6_readlog_r8.json`
  - `docs/design/track_b_b0_1_addendum_q6_root_r8.json`
  - `tests/test_track_b_b0_1_addendum_record.py` (lines 750-819)
  - `tests/tier_counts.json`
- **Grep:**
  - `scripts/track_b_b0_1_review_root.py`
  - `tests/test_track_b_b0_1_review_root.py`
  - `docs/design/track_b_b0_1_addendum.md` (twice)
  - `docs/design` with the filter `track_b_b0_1_addendum_q6_readlog_r*.json`. Matches came from `readlog_r1.json` through `readlog_r8.json`.
  - `tests/test_track_b_b0_1_addendum_record.py` (twice)
  - `tests/README-tiers.md`
- **Glob:**
  - `docs/design/track_b_b0_1_addendum_q6_*`, which returned the 30 round-record files listed under `docs/design`.
