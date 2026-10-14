APPROVE

I found no high or medium findings, and three low ones. I met no reference-year 2012 or 2014 gate statistic, floor, truth moment or candidate outcome, and no 2008 or 2010 selector outcome. Every tool call I made named a path inside the root, and no pattern or file filter named a denied file.

## Findings

### High
None.

### Medium
None.

### Low

**L1. The read log flags a denied file only when a pattern contains its full path, not when it names the file by its basename.**
- **Where:** `scripts/track_b_b0_1_review_root.py:324-334` (`classify_pattern`), compared with the rule at `docs/design/track_b_b0_1_addendum.md:1365-1368`.
- **What is wrong:** A pattern counts as denied only if the whole denied path appears in it (`any(d in pattern for d in denied)`). The denied paths in the root record are full relative paths, such as `docs/design/m6_projection_engine.md` (`docs/design/track_b_b0_1_addendum_q6_root_r6.json:61`).
  - So a Glob such as `**/m6_projection_engine.md`, or a Grep file filter `*m6_candidate3_*`, is classed `inside_root`.
  - The tests miss this because their denied list holds the bare top-level name `gates.yaml` (`tests/test_track_b_b0_1_review_root.py:495`). For a top-level file the full path and the name are the same string.
- **Why it matters:** Section 15 voids a review whose pattern names a denied path "even if it only confirms the path's absence". That is the gap round 6's M1 set out to close, so a lane that confirms a file is absent by its name would still count.
  - No recorded round is affected. Round 5 is already void, and round 6's patterns name no denied file.
- **Smallest fix:** Also flag a pattern or file filter that contains any denied path's basename, or the codebook directory's last segment, as a path segment. Add a test with a nested denied path matched by basename.

**L2. Element 8 still has two leftover lines that contradict its own stratum rule.**
- **Where:** `docs/design/track_b_b0_1_addendum.md:329`, `:374-376`, and `scripts/track_b_b0_1_ruled_power.py:159`.
- **What is wrong:**
  - The bold heading "Only two-cluster strata are admitted (Q6 round 2)" (`:329`) contradicts `:336-358`, which admits every stratum: one-cluster strata by merging, and strata of three or more by exact Rao-Wu.
  - `:374-376` defines ν over the strata "so a stratum with one cluster adds nothing". But `:360` counts ν "after the merges". A one-cluster stratum merged into a stratum with n clusters raises that stratum's n_h − 1 by one, so it does add one degree of freedom.
  - The script docstring at `ruled_power.py:159` repeats the "adds nothing" wording. This is harmless at 2006, where every stratum had two clusters (`:326-327`, `:543-544`).
- **Why it matters:** ν sets t\*. These lines leave two readings that differ by the number of one-cluster strata. Both are fixed from design variables before any candidate outcome, so this is not a post-outcome freedom, but the record should give one reading. This is round 6's L1 again, in a smaller form.
- **Smallest fix:**
  - Retitle `:329` to "Arm D's rule is Rao-Wu only for two-cluster strata (Q6 round 2)".
  - At `:374`, write "over the strata after section 7's merges" and delete "so a stratum with one cluster adds nothing".

**L3. The sentence on context copies says too much for round 2.**
- **Where:** `:1353-1354` ("From round 2 the root also holds the d765, d781, d782 and d1342 ruling texts and d1342's decision aid, ten copies in all (round 2 had nine)").
- **What is wrong:** The d1342 ruling went in at round 4 (`:1552-1553`), after round 3 (`:1542-1543`). The sentence corrects itself in its parenthesis, but it reads as if round 2 held d1342's ruling.
- **Smallest fix:** "From round 2 the root also holds the d765, d781 and d782 ruling texts and d1342's decision aid (nine copies); from round 4, the d1342 ruling as well (ten)."

## Round-6 dispositions, checked in substance

- **M1 (read log): done, apart from my L1.**
  - Glob patterns and Grep file filters are now classified (`review_root.py:295-300`, `:324-341`).
  - Relative result lines are taken as paths and resolved against the root (`:222-244`, `:310-322`).
  - The tests cover a denied pattern, a `..` pattern, a relative denied result, a relative escaping result, and a Grep regex that only mentions a denied name (`tests/test_track_b_b0_1_review_root.py:401-497`).
  - The regenerated round-5 log now flags the brace Glob and records `review_counts: false` (`readlog_r5.json:81`, `:191-195`).
  - Section 15 states the rule (`:1365-1373`) and round 5's status (`:1592-1620`).
- **L1 (element 8's two rules side by side): done, apart from my L2.** Two-cluster strata follow arm D's rule and the others follow the stratum rule (`:316-324`). Round 2's row is marked superseded (`:1504`).
- **L2 (the one-cluster merge): done.** The target is the nearest stratum with two or more clusters, the lower code on a tie. If there is none, all one-cluster strata merge into one. Merges apply together, then the strata are counted (`:339-344`). A test pins it (`test_…_addendum_record.py:724-725`).
- **L3 (section 14's omissions): done.** Section 14 now lists the inventory reruns and root builds (`:1291-1296`), and a test pins them (`test_…_addendum_record.py:752-754`).

## Answers to the questions

**1. Completeness.**
- **Elements frozen.** All ten elements and the named power procedure are marked Frozen or Rule frozen (`:157-169`):
  - element 6 is d781's six, with the ladder run inside them (`:202-223`);
  - element 7 is at `:289-301`;
  - element 8 covers Rao-Wu, the stratum rule, ν and t\* (`:305-411`);
  - element 9 is at `:413-450`;
  - the procedure is in section 16, with the ruled binding evaluation at `:471-477`.
- **Post-outcome freedom.** None is left. `:447-450` forbids reruns, new seeds, a larger K, re-pruning, tolerance changes and rescoping once any candidate outcome exists.
- **What is left open.** Only choices made at floor build, before any candidate outcome: the ladder's order, the stratum counts, the merges and L, all published before any candidate run (`:360-361`, `:466-468`). My L2 is the one ambiguity among them.
- **Marking.** Section 13 marks every item as blocking B2's registration, not this addendum's merge, and records each as ruled or passed (`:929-961`).

**2. Fidelity to the rulings.**
- **Quotations.** d693 (`:81-86`), d622 (`:103-105`), d765, d781 and d782 (`:113-122`) and d1342 (`:142`) match `_review_context/*-ruling.md:5` word for word.
- **d693 riders.** The table at `:93-101` paraphrases them, and section 2 says so (`:88-89`).
- **d765.** Arm F and se_up stay a household bootstrap (`:364-368`).
- **d781 (a).** Carried at `:202-210` and `:1109-1110`: the six cells, the other ten report-only, a levels-only headline, and H and B3L relying on B2 for levels only. The words "not changes, dispersion, mobility or persistence" come from the option's own text (`:985-986`); they are not new scope.
- **d782.** The floor and gate-seed splits stay household (`:363`).
- **M2 rider.** The t value is at `:385-391`. Section 2 says d782's text does not name it and traces its authority to d1342's question, which states "t at 63 df" (`:130-133`; `d1342-ruling.md:3`).
- **d1342 (A).** Carried at `:144-148`, `:220-223` and `:1111-1115`.
- **Changes elsewhere.** I found nothing that changes what a ruling decided.

**3. Protocol and blindness.**
- **Arm D.** `design_multiplicities` (`scripts/track_b_b0_1_planning_values.py:966-998`) matches step 5 (`:1836-1841`).
- **Pins.** The protocol hash is pinned in both the script (`:108-110`) and the test (`test_…_addendum_record.py:32-34`). The test also requires the block to end the file (`:54-60`), and it does (`:2020`).
- **Reads and records.** The record's only post-2010 content is the disclosed presence counts (`:526-530`). A Grep of the planning record for 2011-2029 found only hashes, timestamps and the wave list. No level or gap appears.
- **Block untouched.** I could not compute the hash myself.

**4. Statistics.**
- **Planning-value arms and transport rule.** Sound. The half-sample caveat is disclosed (`:630-633`), the 97.5th-percentile upper limit is conservative, and f is 1 for every cell (`:607-609`).
- **Element 8.**
  - Arm D's two-cluster rule is Rao-Wu.
  - The exact Rao-Wu rule at scale L is correct: n_h − 1 draws, each weighted n_h/(n_h − 1), multiplied by L = lcm(n_h − 1) to give whole numbers.
  - Scaling every person's copies by L leaves the gated quantiles and rates unchanged (`:353-356`).
  - One edge case is unaddressed: a single stratum with one cluster after the merges would give ν = 0. It is implausible for PSID.
- **Student t with ν = Σ(n_h − 1).** This is the standard design degrees of freedom. t\* is 2.7241 against z\* 2.6383 (`ruled_power.json:7`, `:18`).
- **Ruled-power model** (`ruled_power.py:254-309`, `:383-402`). Coherent:
  - x ~ N(0, (rd)² + e), and the registered variance is (rd)²·W + a, with W ~ χ²_ν/ν;
  - the side-A seeds are spread by r, with a sensitivity that spreads them by r·d;
  - it reduces to protocol v2 at ν = ∞, d = 1 and z\* (0.952 at `:851`, tested at `test_…_ruled_power.py:110`, `:318`);
  - the ladder (`:456-512`) is M6's (`build_m6_holdout_floors_v2.py:330-371`).
  - One observation, not a finding: with uncapped tolerances, tolerance/σ is about 2.6 for every cell, so the ladder's order is close to arbitrary. The addendum discloses this honestly as "306 of 720 is a count, not a probability" (`:828-829`).

**5. Power.**
- **Original basis.** The verdict follows from the power record, which the CI-pinned tests recompute, and the tables are required verbatim (`test_…_addendum_record.py:398-400`).
- **Ruled configuration.** Every prose figure matches the record:
  - the evaluations: 0.813, 0.821, 0.854, 0.841, 0.852, 0.813, 0.907 and 0.952 (`ruled_power.json:839-881`);
  - the fixed surfaces (`:107-398`);
  - the ladder: 306 of 720 orders clear, and all 414 failures end on a three-cell surface (`:404-636`);
  - options B, C1, C2, D (k = 3.26) and the six, with their tolerance-scale rows (`:658-765`);
  - the weak cell's 0.892, with d's 95th percentile at 1.259 (`:769-770`);
  - the maximum correlation, 0.1795 (`:657`).
- **Verdict.** "Feasible, subject to B2's floor" follows from the four-cell surface at 0.964 (`:913-928`).

**6. Consistency.** The addendum, the records, the scripts and the tests agree. The exceptions are L2 (element 8's leftover wording and the script docstring) and L1 (the read-log rule against its implementation).

**7. Exposure.**
- **Sections 14 and 15.** They match the records I checked: the round-6 root record (head `0487adc`, 1,938 files, its denied list) and the regenerated round-5 log.
- **Gaps.** L3 is the only inaccuracy, and it is about wording.
- **Additions since round 1.** Nothing added since round 1 exposes a B2 outcome or a 2008/2010 selector outcome. The ruled-power record reads only the 2006 planning record. In `OPTIONS.md`, a year search returned a single line, its own statement that nothing in it comes from data after 2010.

## What I could not check from inside the root

- The protocol block's SHA-256, and whether CI passes. I ran no code.
- The context copies against their sources, and the design file's identity.
- The transcript exports behind the reads record and the read logs. That includes whether this round's read log will be generated correctly.
- The content of issue #42, B1's sealed output, the d1342 reviews and the B2 build lane.
- PSID's strata at B2's 2011 truth support.
- This round's root record and inventory rerun, which are not in the root.
- I wrote no plan file. This session has no write tool, and the review needed none.

## Read log (relative to the root)

- **Glob:**
  - `**/*` (returned the first 100 of 1,942 paths);
  - `**/*b0_1*`;
  - `_review_context/**`.
- **Read:**
  - `docs/design/track_b_b0_1_addendum.md`, in full, in three parts;
  - `docs/design/track_b_b0_1_addendum_q6_review_r6.md`;
  - `_review_context/d782-ruling.md`, `d781-ruling.md`, `d765-ruling.md`, `d1342-ruling.md`, `d693-ruling.md` and `d622-ruling.md`;
  - `scripts/track_b_b0_1_review_root.py` (lines 200-359);
  - `tests/test_track_b_b0_1_review_root.py` (lines 395-497);
  - `scripts/track_b_b0_1_ruled_power.py`, in full;
  - `scripts/build_m6_holdout_floors_v2.py` (lines 318-377);
  - `docs/design/track_b_b0_1_ruled_power.json` (lines 404-767);
  - `scripts/track_b_b0_1_planning_values.py` (lines 966-1005).
- **Grep:**
  - `scripts/track_b_b0_1_review_root.py`;
  - `docs/design/track_b_b0_1_addendum_q6_readlog_r5.json`;
  - `tests/test_track_b_b0_1_review_root.py`;
  - `docs/design/track_b_b0_1_addendum_q6_root_r6.json`;
  - `scripts/build_m6_holdout_floors_v2.py`;
  - `docs/design/track_b_b0_1_ruled_power.json`;
  - `tests/` with the file filter `test_track_b_b0_1_*.py`. Matches came back from `tests/test_track_b_b0_1_revision1_tools.py`, `tests/test_track_b_b0_1_audit_record.py`, `tests/test_track_b_b0_1_addendum_record.py` and `tests/test_track_b_b0_1_review_root.py`;
  - `tests/test_track_b_b0_1_addendum_record.py`;
  - `scripts/track_b_b0_1_planning_values.py`;
  - `tests/test_track_b_b0_1_ruled_power.py`;
  - `docs/design/track_b_b0_1_planning_values.json`;
  - `_review_context/OPTIONS.md`.