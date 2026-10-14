APPROVE

The fixes for round 9's two low findings and two observations are in place, and the B2 record is unchanged in everything it registers on. I found no high or medium finding. I found one new low finding, and it bears on the review tooling only. I met no reference-year 2012 or 2014 gate statistic, floor, truth moment or candidate outcome, and no 2008 or 2010 selector outcome.

## Findings

### High
None.

### Medium
None.

### Low

**L1. A character class that contains a comma or a brace hides a whole denied stem from the new wildcard rule.** *(Review tooling only. It should not hold the merge.)*
- **Where:** `scripts/track_b_b0_1_review_root.py:325` (every text is cut at `[/{},]`) and `:335-339` (the stem-and-`fnmatchcase` test runs on those cut pieces). The disclosure at `docs/design/track_b_b0_1_addendum.md:1388-1392` says only a wildcard holding part of a stem stays unclassified.
- **What is wrong:** Round 9's L1 fix cuts every text at any comma or brace, and that cut also runs inside `[...]` classes. Take `**/deep_denied[.,]md`, `deep_denied[!,]md` or `deep_denied[{.]md`:
  - There is no balanced group, so the only alternative is the pattern itself.
  - The cut leaves pieces like `deep_denied[.` and `]md`.
  - Python's `fnmatch` reads an unclosed `[` as a literal, so neither piece matches the denied name.
  - The pattern is therefore classed `inside_root`. A glob engine that treats `[.,]` as a class (globset, minimatch) would match the denied file.
  - These patterns hold the whole stem, so the disclosure does not cover them.
- **Tests:** the property test at `tests/test_track_b_b0_1_review_root.py:765-784` only tries one-character classes `[c]`, so it never reaches this case.
- **Why it matters:** this is the next simplest form after the ones round 9's L2 closed. It is contrived, and the review prompt forbids it. No recorded round's pattern has this shape: round 8's only class is `r[567]` (`readlog_r8.json:28`), and the patterns of rounds 5, 6, 7 and 9 have none (`readlog_r5.json:76-81`, `readlog_r6.json:77-81`, `readlog_r7.json:78-81`, `readlog_r9.json:49-50`).
- **Smallest fix:** run the wildcard test at `:335-339` on each alternative's `/`-segments as well, not cut at commas or braces. Add the three patterns above as `denied` cases.

**Observations (not findings; neither holds the merge):**
- **Codebook files and code-map tables by basename (pre-existing, unchanged since round 9).** The read log's `denied` list is only the root record's `denied_paths` (`review_root.py:740-742`).
  - The six codebook files are caught only through the directory's path or name (`:317`, `:328`), not by their own basenames.
  - The four removed code-map tables are not checked at all.
  - So a pattern that names one of these by basename would pass. If the rule should cover every file removed from the root, pass in `removed` and `removed_codebook_tables` too.
- **Section 5's new sentence and the "no rescoped registration" line.** Section 5 (`addendum.md:266-267`) still says only that no *rescoped* registration is written before Max rules. Read literally, that does not cover a registration that changes how the critical value is set when ν is 0. The timing still holds, because the stop comes at floor build. Changing "rescoped" to "amended" would close the gap.

## Answers

**1. Dispositions: all four are resolved in substance.**
- **L1 (unbalanced brace): resolved.**
  - When a `{` has no closing brace, the scan moves on to the next `{` (`review_root.py:278-293`).
  - The docstring says so (`:257-259`).
  - Every alternative is now cut at any brace or comma left in it (`:324-325`).
  - Round 9's own example is a test case (`tests/test_track_b_b0_1_review_root.py:566-577`), along with expansion checks (`:688-690`) and a property test (`:787-801`).
- **L2 (whole stem with a wildcard): resolved,** apart from my L1 above.
  - The rule is at `review_root.py:335-339`.
  - Round 9's three forms are test cases g18-g20 (`tests/...review_root.py:579-613`), and there is a property test (`:765-784`).
  - The cases that should still count, `**/*`, `**/*deep*` and `deep_denied_notes.md`, still pass (`:614-637`).
  - The disclosure is widened (`addendum.md:1388-1392`).
- **Observation, schema version: resolved.**
  - The read log is now `track_b_b0_1_review_read_log.v6` (`review_root.py:433`), and the plan says a log's version records its rule (`addendum.md:1393-1394`).
  - The logs of rounds 5-9 are all v6. Round 5 stays void and rounds 6-9 count (`readlog_r5.json:195,197`, `readlog_r6.json:133,135`, `readlog_r7.json:195,197`, `readlog_r8.json:41,43`, `readlog_r9.json:58,60`).
  - A test pins this (`tests/test_track_b_b0_1_addendum_record.py:820-832`).
- **Observation, rescoping cannot cure ν = 0: resolved.** Section 5 now says so (`addendum.md:265-266`), and a test pins the sentence (`test_..._addendum_record.py:810-812`).

**2. The frozen record: unchanged.**
- The only change outside the tooling is the one sentence at `addendum.md:265-266`. It changes no rule's trigger, timing or outcome, no figure and no exposure label.
- It is consistent with the other sections:
  - Section 7 stops B2 at floor build when ν is 0 (`:380-383`).
  - Section 8 allows that route only at floor build, before any candidate outcome (`:454-457`).
  - Section 9's step 4 stops before any candidate run (`:473-476`).
  - The "To B2" list says the same (`:1115-1118`).
- It is consistent with the rulings:
  - d1342 ruled the t value at ν = 63 (`:395-397`). Queuing how the critical value is set when ν is 0 is a question for Max, not a change to that ruling.
  - d781's six-cell surface and d782's design-cluster standard error are untouched (`:225-226`, `:314-318`).

**3. Protocol and blindness: untouched, and nothing exposed.**
- Every changed passage lies before section 16, which starts at `addendum.md:1813`. The protocol block runs from `:1822` to `:2156`.
- The new tests use invented paths (`tests/...review_root.py:667`, `:674`).
- The file names in `root_r9.json:50-110` are the committed exclusion record, not outcomes.
- Of `inventory_r9.json` I saw only its `n_blocks` counts and schema line, and no statistic.

**4. Records: section 15 matches round 9's records (`addendum.md:1772-1807`).**

| Section 15 says | Records say |
|---|---|
| Head `266dd96`, 1,950 files, manifest `103a6f11174bef67…` | `root_r9.json:73-75` |
| Same 27 files removed, four code-map tables, ten context copies | `root_r9.json:76-104`, `:105-110`, `:8-48` |
| 20 tool calls; the review counts | `readlog_r9.json:3`, `:58`; I counted the 20 entries at `:61-151` |
| `APPROVE`, no high or medium finding, two low | `review_r9.md:1-37` |
| L1 and L2 as round 9 stated them; both tooling only | `review_r9.md:15-37` |
| Schema observation | `review_r9.md:39` |
| ν = 0 observation | `review_r9.md:61` |

- Round 9's own read-log list matches its log: two Greps of `addendum.md` (`readlog_r9.json:80-89`) and four Reads of it (`:90-101`, `:147-149`).
- The tier counts add up to 12,682 in both `tests/tier_counts.json:4-8` and `tests/README-tiers.md:42-47`. That is 15 more than round 9's 12,667.

## What I could not check from inside the root
- I ran no code, so I could not check:
  - the protocol block's SHA-256;
  - whether CI passes;
  - whether the tier counts match the collected tests;
  - the claim that "four mutants fail the two fixes' tests".
- Which glob engine the Glob and Grep tools use, and so whether my L1's patterns would actually match there. The same question decides whether matching is case-insensitive on this macOS file system.
- Round 9's transcript, model attestation, prompt and run times (22:59-23:04 UTC).
- That `inventory_r9.json` "flagged nothing new". I did not read its body.
- Whether the round 5-8 logs were regenerated with this head's tool. Their v6 schema is consistent with it.
- This round's own root record and read log.
- The session gave me no Write tool, so I wrote no plan file and edited nothing.

## Read log (relative to the root)
- **Read:**
  - `docs/design/track_b_b0_1_addendum_q6_review_r9.md`
  - `scripts/track_b_b0_1_review_root.py` (lines 150-509, 700-757)
  - `docs/design/track_b_b0_1_addendum.md` (lines 225-504, 1108-1121, 1370-1829)
  - `docs/design/track_b_b0_1_addendum_q6_root_r9.json`
  - `docs/design/track_b_b0_1_addendum_q6_readlog_r9.json`
  - `tests/test_track_b_b0_1_review_root.py` (lines 540-802)
  - `tests/test_track_b_b0_1_addendum_record.py` (lines 815-839)
  - `tests/tier_counts.json`
- **Grep:**
  - `docs/design/track_b_b0_1_addendum.md` (twice)
  - `docs/design/track_b_b0_1_addendum_q6_inventory_r9.json`
  - `tests/test_track_b_b0_1_review_root.py`
  - `scripts/track_b_b0_1_review_root.py`
  - `tests/test_track_b_b0_1_addendum_record.py`
  - `docs/design` with the filter `track_b_b0_1_addendum_q6_readlog_r*.json`. Matches came from `readlog_r1.json` through `readlog_r9.json`.
  - `tests/README-tiers.md`
- **Glob:**
  - `docs/design/track_b_b0_1_addendum*`
  - `scripts/track_b_b0_1_review_root.py`