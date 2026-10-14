REQUEST CHANGES

I found no high finding, one medium and three low. I met no reference-year 2012 or 2014 gate statistic, floor, truth moment or candidate outcome, and no 2008 or 2010 selector outcome. Every tool call I made named a path inside the root, and none named a denied path. My first `**/*` Glob timed out and returned nothing.

## Findings

### Medium

**M1. The Claude read log does not check what section 15 says it checks, and round 5, the review of record, has an unflagged call that names denied paths.**
- **Where:**
  - `docs/design/track_b_b0_1_addendum.md:1346-1353` (the rule: "every path a tool call names and every path a Glob or Grep result returns");
  - `:1589-1592` (round 5: "Every path named or returned lies inside the root, none is denied … so the review counts");
  - `scripts/track_b_b0_1_review_root.py:58-59, 279-281, 222-235`;
  - `docs/design/track_b_b0_1_addendum_q6_readlog_r5.json:197-200, 31, 33`;
  - `tests/test_track_b_b0_1_review_root.py:194-195`.
- **What is wrong:**
  - **Patterns are not classified.** `PATH_FIELDS` records `pattern` and `glob`, but `read_log` only classifies `file_path` and `path`.
    - Round 5's Glob at `readlog_r5.json:198` has a pattern that names `gates.yaml`, `paper/paper.qmd`, `docs/design/m6_projection_engine.md`, the codebook directory and other paths on the root record's denied list.
    - The log still records `paths_outside_root_or_denied: []` and `review_counts: true`.
  - **Returned paths are effectively never checked.** `_result_paths` keeps only result lines that begin with `/`.
    - In this harness, Glob and Grep return paths relative to the root. My own results came back as `docs/design/…` and `src/…`.
    - So in practice nothing a Glob or Grep returns is checked. Round 5's log lists only the absolute `file_path` and `path` arguments (`readlog_r5.json:4-30`). No result path appears in it.
    - The only test of this branch feeds an absolute result (`test_…_review_root.py:194-195`), so it does not catch the gap.
- **Why it matters:**
  - **Exposure was nil.** The denied files are absent from the root, so that Glob returned nothing, and a Glob only lists names.
  - **The record is still wrong.** Section 15's rule, and the rule this round runs under, void a review whose calls *name* a denied path. Section 15 then says round 5's calls named none, and the review of record rests on that claim.
  - **Escapes through patterns would go unseen.** A pattern that leaves the root (for example `../…`) would not be flagged, and neither would relative result paths. This round's log will have the same blind spot.
- **Smallest fix:**
  - Classify `pattern` and `glob` too. Void on an absolute pattern or a `..` segment. For a denied name, either void or state explicitly that a Glob that only confirms absence and returns nothing is not a touch. The rule needs to make that call, not the extractor by omission.
  - Resolve relative result lines against the root.
  - Add tests for both cases, regenerate the round-5 log, and restate `:1589-1592` with whatever the decision on the absence check is.

### Low

**L1. Element 8 still gives two rules for strata that do not have two clusters.**
- **Where:** `:314-324` against `:333-353`; also `:1484`.
- **What is wrong:**
  - `:314-318` says the multiplicities "follow arm D's `design_multiplicities` rule". The sub-bullets then restate arm D's treatment of one-cluster strata (kept once) and strata with three or more clusters (n draws with replacement).
  - `:333-353` replaces both cases with merging and exact Rao-Wu at scale L.
  - Section 15's round-2 row (`:1484`) still says the builder "stops before any candidate run if any stratum has one cluster or three or more". Round 5's L3 superseded that.
- **Why it matters:** A builder who reads `:314-324` alone gets the rule that `:326-331` calls wrong.
- **Fix:**
  - At `:314-318`, say "arm D's rule for two-cluster strata; other strata by the rule below".
  - Add "(superseded by round 5's L3)" to the `:1484` row.

**L2. The singleton-merge rule is ambiguous when one-cluster strata are adjacent.**
- **Where:** `:336-339`.
- **What is wrong:** "Nearest stratum code" does not say three things:
  - whether the target may itself be a one-cluster stratum;
  - whether merges apply at once or one after another;
  - whether the merges are closed transitively.
- **Example:** with codes 3, 4 and 5 each holding one cluster, 3 merges into 4, 4 into 3 (a tie broken to the lower code) and 5 into 4. Applied one after another, the strata that result depend on order.
- **Why it matters:** ν, L and t\* follow from the merges. They are fixed before any candidate outcome, from design variables alone, so this is not post-outcome freedom. But it is the one floor-time choice left unspecified.
- **Fix:** One sentence, for example: "Nearest among strata with two or more clusters. If none, merge all one-cluster strata transitively by nearest code. Merges are applied together, then counted."

**L3. Section 14 omits some of the revision session's mechanical scans of excluded files.**
- **Where:** `:1279-1285` against `:1495-1497`, `:1529-1531` and `:1575-1577`.
- **What is wrong:**
  - Section 14 lists pytest collection, `git diff` and the reads-extractor rerun as the calls that took in excluded files.
  - Section 15 records three more exposure-inventory reruns (r3-r5) and four root builds. Both read every tracked file's bytes: the inventory script at `scripts/track_b_b0_1_exposure_inventory.py:515`, and the root builder's token scan as described at `:1331-1333`.
- **Why it matters:** Question 7 asks whether section 14 is complete.
- **Fix:** Add one bullet covering the inventory reruns and root builds, both mechanical and printing only names and counts.

## Round-5 dispositions, checked in substance

- **M1.** Done.
  - `:1287-1318` now covers each item round 5 listed:
    - the #42 comments 6110674288 and 6113379406, and that no other #42 comment was read;
    - the session's role in B1's run;
    - that no B1 raw output, evidence file or sealed log was opened;
    - the d1342 aid and its two Sol reviews, on roots holding no §15.4 file;
    - the absence of an extractor record.
  - A test pins it (`test_…_addendum_record.py:727-730`).
- **L1.** Done at `:70-72` and `:795-796`. The test phrase still matches after whitespace normalisation (`:674`).
- **L2.** Done at `:130-133`. It matches `d1342-ruling.md:3`.
- **L3.** Done, apart from the edge cases in my L1 and L2.
  - The exact Rao-Wu arithmetic is right. With n_h − 1 draws each weighted n_h/(n_h − 1), L·n_h/(n_h − 1) is a whole number exactly when (n_h − 1) divides L, and L is the least common multiple.
  - Scale invariance holds for the gated cells. `m6_cells._wquantile` (`src/populace_dynamics/harness/m6_cells.py:467-474`) is a lower-convention cumulative-weight quantile. Scaling every person's copies by L leaves it unchanged, and leaves `_rate` unchanged. Only the midpoint-rank binning in `moments.py:85-94` is affected, as `:350-351` says.
- **L4.** Done at `:255-259` and `:1336-1343`.
- **L5.** Done at `:519-530`.

## Answers to the seven questions

**1. Completeness.**
- **Elements frozen.** All ten elements and the named power procedure are marked Frozen or Rule frozen (`:157-169`), and a test pins the table (`test_…_addendum_record.py:153-165`).
  - Element 6 is d781's six, with the ladder run inside them on B2's floor (`:202-223`).
  - Element 7 is at `:289-301`.
  - Element 8 is Rao-Wu, the stratum rule, ν and t (`:305-406`).
  - Element 9 is at `:410-445`.
- **Post-outcome freedom.** None. `:442-445` forbids reruns, new seeds, a larger K, re-pruning, tolerance changes and rescoping, and the seeds are named at `:400-406`.
- **What remains open.** Only floor-time choices, all made before any candidate outcome: the ladder's order and the stratum counts, with my L2 gap.
- **Marking.** Section 13 marks every open item as blocking B2's registration, not this addendum's merge (`:924-956`), and records each as ruled or passed.

**2. Fidelity to the rulings.**
- **Quotations.** The quotations of d693 (`:81-86`), d622 (`:103-105`), d765, d781 and d782 (`:113-122`) and d1342 (`:142`) match `_review_context/*-ruling.md` word for word.
- **d693 riders.** The table at `:93-101` matches `d693-RECOMMENDATION.md:26-60`.
- **d622.** The weaker label is carried at `:940-944` and `:1111-1113`.
- **d765.** Arm F stays a household bootstrap, and se_up stays household (`:359-363`).
- **d781 (a).** The headline and the levels-only reliance are carried at `:206-210` and `:1104-1105`.
- **d782.** The floor and gate-seed splits stay household (`:358`).
- **M2 rider.** The t value is at `:380-386`, with its authority traced through d1342's question (`:130-133`).
- **d1342 (A).** Carried exactly at `:144-148` and `:1106-1110`.
- **Changes elsewhere.** I found nothing the rulings decided that is changed elsewhere.

**3. Protocol and blindness.**
- **Arm D.** `design_multiplicities` (`scripts/track_b_b0_1_planning_values.py:966-998`) matches protocol step 5 (`:1771-1776`).
- **Pins.** The tests pin the constants, stream words and power constants (`test_…_addendum_record.py:63-135`), the script's hash (`:281-292`), and the block's hash, and they require the block to end the file (`:54-60`).
- **Reads and records.** The run read nothing dated after 2010 (`:296-322`). The only post-2010 content in the record is the presence counts disclosed at `:519-525`. Nothing reveals a level or gap.
- **Block untouched.** I could not compute the hash myself. The block (`:1621-1955`) is still the last text in the file.

**4. Statistics.**
- **Planning arms.** Sound. The half-sample caveat is disclosed at `:625-628`, and the 97.5th-percentile upper limit is conservative.
- **Transport rule.** Sound. f = 1 for every cell (`:602-604`).
- **Element 8.** Admitting only two-cluster strata was correct, and the round-5 extension is correct Rao-Wu, with L1 and L2 as the remaining gaps.
- **Student t.** ν = Σ(n_h − 1) is the standard design degrees of freedom. The record's t\* is 2.7241 against z\* 2.6383 (`track_b_b0_1_ruled_power.json:7, 18`). Giving the whole of se_c ν degrees of freedom is conservative.
- **Ruled-power model.** Coherent.
  - x ~ N(0, (rd)² + e). The registered variance is (rd)²W + a, with W ~ χ²_ν/ν independent of x (`ruled_power.py:280-300`). The side-A seeds are spread by r (`:391`).
  - It reduces to protocol v2's evaluation with ν = ∞, d = 1 and z\*, at 0.952.
  - The ladder (`:456-512`) never prunes a family's last cell, as M6's does.

**5. Power.**
- **Original basis.** The verdict follows from the power record, which CI recomputes (`test_…_addendum_record.py:360-400`).
- **Ruled configuration.** I checked section 11's ruled figures against `ruled_power.json:580-929`:
  - the evaluations: 0.813, 0.821, 0.854, 0.841, 0.852, 0.813, 0.907 and 0.952;
  - options B, C1, C2 and D, with their tolerance-scale rows;
  - 306 and 720 orders clearing;
  - the weak cell's 0.892, with d's 95th percentile at 1.259;
  - the maximum correlation, 0.1795;
  - the maximum seed failure, 2.24e-7, below 10⁻⁶.
- **Verdict.** "Feasible, subject to B2's floor" follows from the four-cell surface at 0.964 (`:905-928`).

**6. Consistency.**
- The addendum, the records, the scripts, the tests and `OPTIONS.md` agree. `OPTIONS.md`'s 2006 design-ratio range, 0.95-1.21 with 95th percentiles up to 1.26, matches the per-cell record.
- The exceptions are my L1 (element 8's internal tension) and M1 (the read-log rule against its implementation).

**7. Exposure.**
- **Sections 14 and 15.** The round-5 root record matches section 15: 27 files removed, ten context copies, head `046480a` (`q6_root_r5.json:8-104`). Round 5's log holds 45 calls.
- **Gaps.** The inaccuracies are M1 and L3.
- **Additions since round 1.** Nothing added since round 1 that I read exposes a B2 outcome or a 2008/2010 selector outcome. The ruled-power record and `OPTIONS.md` are functions of the 2006 planning record alone. The B1 statements are statuses only.

## What I could not check from inside the root

- The protocol block's SHA-256, and whether CI passes. I ran no code.
- The context copies' hashes against their sources, and the design file's identity.
- The transcript exports behind the reads record and the review read logs. That includes whether round 5's Glob results really came back relative; I inferred it from this harness's behaviour.
- The content of #42, B1's sealed output, the d1342 reviews and the B2 build lane.
- PSID's strata at B2's 2011 truth support.
- This round's root record and read log, which do not exist yet.

## Read log (relative to the root)

- **Glob:**
  - `**/*` (timed out, returned nothing);
  - `docs/design/track_b_b0_1*`;
  - `_review_context/*`;
  - `scripts/track_b*`;
  - `tests/test_track_b_b0_1*`.
- **Read in full:**
  - `docs/design/track_b_b0_1_addendum.md` (three parts);
  - `docs/design/track_b_b0_1_addendum_q6_review_r5.md`;
  - `_review_context/d1342-ruling.md`, `d782-ruling.md`, `d781-ruling.md`, `d765-ruling.md`, `d693-ruling.md`, `d622-ruling.md`, `d693-RECOMMENDATION.md` and `OPTIONS.md`;
  - `scripts/track_b_b0_1_ruled_power.py`;
  - `tests/test_track_b_b0_1_addendum_record.py`;
  - `docs/design/track_b_b0_1_addendum_q6_root_r5.json`.
- **Read in part:**
  - `docs/design/track_b_b0_1_ruled_power.json` (lines 580-929), after a Grep of it;
  - `docs/design/track_b_b0_1_addendum_q6_readlog_r5.json` (lines 1-36 and 186-215), after three Greps of it;
  - `scripts/track_b_b0_1_review_root.py` (lines 215-318), after a Grep of it;
  - `src/populace_dynamics/harness/m6_cells.py` (lines 460-519), after a Grep of it.
- **Grep only:**
  - `docs/design/track_b_b0_1_addendum.md`;
  - `src/`, for weighted-quantile definitions. Matches returned from `src/populace_dynamics/data/couple_earnings.py`, `src/populace_dynamics/harness/metrics.py`, `src/populace_dynamics/harness/moments.py`, `src/populace_dynamics/data/cps_tenure.py`, `src/populace_dynamics/uniform_cut_track_u/diagnostics.py` and `src/populace_dynamics/data/deployment_frame.py`;
  - `tests/test_track_b_b0_1_review_root.py`;
  - `scripts/track_b_b0_1_planning_values.py` (it returned lines 966-1010);
  - `_review_context/trackb-design-20260928.md`;
  - `scripts/track_b_b0_1_exposure_inventory.py`.