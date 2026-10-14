APPROVE

I found no high or medium findings and two low ones. All three of round 7's findings are fixed in substance. I met no reference-year 2012 or 2014 gate statistic, floor, truth moment or candidate outcome, and no 2008 or 2010 selector outcome. Every tool call I made named a path inside the root, and no pattern or file filter named a denied file.

## Findings

### High
None.

### Medium
None.

### Low

**L1. The read log misses a denied file named by its stem inside braces, with the extension outside them.**
- **Where:** `scripts/track_b_b0_1_review_root.py:343-347`.
- **What is wrong:**
  - The classifier splits a pattern at `/`, `{`, `}` and `,`. It then flags a piece only if the piece is a denied basename, or a denied stem followed by a dot.
  - In `**/{<stem>,x}.md`, the pieces are `<stem>`, `x` and `.md`. The bare stem matches neither test, so the pattern counts as `inside_root` even though it names the denied `<stem>.md`.
  - `**/<stem>.{md,json}` is caught, because one piece is `<stem>.`. The tests cover only that brace form (`tests/test_track_b_b0_1_review_root.py:485`).
- **Why it matters:** Section 15 says a pattern that names a denied path voids the review (`docs/design/track_b_b0_1_addendum.md:1369-1377`). This is a plain way to name a file, not a wildcard fragment, so it is not covered by the stated exception for fragments.
  - No recorded round is affected. The patterns of rounds 5-7 are at `readlog_r5.json:76-81`, `readlog_r6.json:77-81` and `readlog_r7.json:78-81`. Round 5's brace Glob is already flagged.
- **Smallest fix:** Expand brace groups before splitting the pattern, or also flag a piece equal to a bare denied stem. Add a test case `**/{deep_denied,x}.md` that expects the review not to count.

**L2. Section 5 does not list the new ν = 0 trigger for `WEAK_POWER_OR_VACUITY`.**
- **Where:** `addendum.md:261-265`, compared with `:378-380`.
- **What is wrong:** Section 7 now stops B2 at floor build with `WEAK_POWER_OR_VACUITY` when ν = 0. Section 5 still gives the triggers as only "If the ladder ends below 0.90 or a guard fails". Section 9's step 4 (`:470-472`) and the "To B2" list (`:1111-1112`) don't mention it either.
- **Why it matters:** The outcome and the timing are the same: floor build, before any candidate run. So this is not a new freedom, and section 8's note (`:451-454`) covers it. But a floor-builder author reading section 5 or section 9 alone would not find the trigger.
- **Smallest fix:** At `:261`, write "If the ladder ends below 0.90, a guard fails, or ν is 0 after section 7's merges".

**Observation, not a finding.** The read log treats Grep context prefixes as paths (`"--"`, `"30-"`, `"396-"` at `readlog_r7.json:5`, `:21-28`). They resolve inside the root, so this only adds noise.

## Answers

**1. Dispositions**
- **L1: resolved in substance, with L1 above left over.**
  - **Implementation.** `classify_pattern` now flags a piece equal to a denied basename, a denied stem followed by a dot, or the codebook directory's last segment (`review_root.py:325-348`). The docstring states the new rule (`:256-259`).
  - **Tests.** New cases cover a nested denied file by basename (`tests/test_track_b_b0_1_review_root.py:466-478`) and by stem (`:479-489`), and the codebook directory (`:490-500`). Broad patterns and wildcard fragments still count (`:501-524`). The nested denied file is set up at `:554`.
  - **Wildcard fragments.** Round 7's `*name_part*` example stays unclassified. That matches the fix round 7 proposed, and section 15 discloses it (`addendum.md:1376-1377`).
- **L2: resolved.**
  - **The heading** is retitled (`addendum.md:329`).
  - **One reading of ν.** The addendum counts ν after the merges, where a merged one-cluster stratum adds one degree of freedom (`:360`, `:374-377`). `design_degrees_of_freedom` does the same: `twos + ones`, or `ones − 1` when no stratum has two clusters, and it raises when ν ≤ 0 (`ruled_power.py:156-175`).
  - **Tests.** The test checks 63, 64, 2, and the raise (`tests/test_track_b_b0_1_ruled_power.py:79-108`). The old wording is pinned as absent and the new wording as present (`tests/test_track_b_b0_1_addendum_record.py:767-773`, `:788-789`).
  - **No 2006 figure moves.** The 2006 record has 0 one-cluster strata and 63 two-cluster strata (`planning_values.json:1323-1325`), so ν stays 63 (`ruled_power.json:4`, pinned at `test_…_ruled_power.py:357`).
- **L3: resolved.** The sentence now reads "nine copies… from round 4… ten" (`addendum.md:1356-1358`). That matches round 2's nine copies (`:1476-1482`) and round 4's ten (`:1561-1562`). The old wording is pinned as absent (`test_…_addendum_record.py:790`).

**2. New problems**
- **Inconsistency.** Only my L2 above.
- **The ν = 0 stop rule is correct.** After the merges, ν = 0 needs exactly one stratum with one cluster. Two or more one-cluster strata merge into one stratum with ν ≥ 1. So "needs every truth-support person in one cluster" is right.
- **Fit with sections 5 and 8.** The rule is fixed from design variables before any candidate outcome. It uses the existing `WEAK_POWER_OR_VACUITY` route, which section 8 limits to floor build (`:451-454`).
- **Freedom or rulings.** I found no new freedom after a candidate outcome and no change to what a ruling decided. d782's Rao-Wu requirement and the household floor splits are unchanged (`:311-315`, `:363`).

**3. Protocol and blindness**
- **Protocol block.** The listed changes are all outside section 16. Its arm D text (`:1879-1880`) is the frozen description the addendum quotes. I could not recompute the hash.
- **Exposure.** Nothing I read exposes a B2 outcome or a 2008/2010 selector outcome. The new tests use invented inputs and the 2006 record's design counts.

**4. Records: they match.**

| Section 15 says (`addendum.md:1683-1712`) | Records say |
|---|---|
| Head `05dbd5b`, 1,942 files, manifest `a999c4d27cf77146…` | `root_r7.json:73-75` |
| 27 files removed whole: 21 denied plus 6 codebook files | `root_r7.json:50-104` |
| Four code-map tables removed | `root_r7.json:105-110` |
| Ten context copies | `root_r7.json:8-47` |
| 32 tool calls; the review counts | `readlog_r7.json:3`, `:193-195` |
| `APPROVE`, no high or medium finding, three low | `review_r7.md:1-38` |

- The four patterns in the round-7 read log (`readlog_r7.json:78-81`) match the review's own read log (`review_r7.md:126-147`).
- In the regenerated logs, round 5 stays void (`readlog_r5.json:81`, `:195`) and round 6 still counts (`readlog_r6.json:133`).
- The tier counts add up to 12,652 (`tests/tier_counts.json:4-8`, `tests/README-tiers.md:42-47`).

## What I could not check from inside the root
- The protocol block's SHA-256, whether CI passes, and whether the tier counts match the collected tests. I ran no code.
- The "four mutants" and "two mutants" claims.
- Round 7's transcript and prompt, so I could not check the prompt's added sentence (`:1694-1696`). I also could not match the 32 calls one by one against the review's grouped read log.
- The contents of the round-7 inventory rerun beyond its structure, and whether it flagged nothing new.
- This round's root record and read log.
- I wrote no plan file. This session has no write tool, and the review needed none.

## Read log (relative to the root)
- **Read:**
  - `docs/design/track_b_b0_1_addendum_q6_review_r7.md`
  - `docs/design/track_b_b0_1_addendum.md` (lines 200-499, 1100-1117, 1335-1724)
  - `scripts/track_b_b0_1_review_root.py` (245-374)
  - `tests/test_track_b_b0_1_review_root.py` (390-557)
  - `scripts/track_b_b0_1_ruled_power.py` (140-209)
  - `tests/test_track_b_b0_1_ruled_power.py` (74-109)
  - `docs/design/track_b_b0_1_addendum_q6_root_r7.json` (48-113)
  - `docs/design/track_b_b0_1_addendum_q6_readlog_r7.json` (1-80)
  - `tests/tier_counts.json`
- **Grep:**
  - `docs/design/track_b_b0_1_addendum.md` (twice)
  - `scripts/track_b_b0_1_review_root.py`
  - `tests/test_track_b_b0_1_review_root.py`
  - `scripts/track_b_b0_1_ruled_power.py`
  - the root with the file filter `*.{py,json}`. Matches came from `scripts/track_b_b0_1_planning_values.py`, `tests/test_track_b_b0_1_planning_values.py`, `scripts/track_b_b0_1_ruled_power.py`, `tests/test_track_b_b0_1_ruled_power.py`, `tests/test_track_b_b0_1_addendum_record.py`, `docs/design/track_b_b0_1_addendum_q6_readlog_r7.json`, `docs/design/track_b_b0_1_ruled_power.json` and `docs/design/track_b_b0_1_planning_values.json`
  - `tests/test_track_b_b0_1_addendum_record.py`
  - `docs/design` with the filter `track_b_b0_1_addendum_q6_{root,readlog,inventory}_r7.json`. Matches came from `root_r7.json`, `readlog_r7.json` and `inventory_r7.json`
  - `docs/design` with the filter `track_b_b0_1_addendum_q6_readlog_r[567].json`
  - `tests` with the filter `{tier_counts.json,README-tiers.md}`, which returned no matches
  - `tests/README-tiers.md`