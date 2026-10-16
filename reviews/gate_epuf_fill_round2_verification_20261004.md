# Referee report: `gate_epuf_fill` amendment 1, round 2 (verification)

Branch `epuf-career-fill-20261003`, head `f8623f4d`. Independent referee, read-only.

**What I could not do.** This session had file-read and search tools but no shell. So:

- **Tests not run.** I ran neither test file. Every statement below about the tests comes from reading them.
- **No `git diff`.** I could not diff `7061200d` against `23bee82c`, so I have not checked that the rules files are byte-identical at the two commits. `test_registered_build_is_bound_to_its_rules` would check it, but I could not run that test.
- **Chronology from git's logs.** I got the commit order from the reflog and the remote-tracking log, read as plain files under `.git/`.
- **No EPUF microdata.** I read none, including the `.diag/epuf-fill/cache/*.npz` part caches, and called no EPUF reader.

Claims are marked **(V)** for verified (I read it, or did the arithmetic on stored values) or **(I)** for inferred.

## Verdict: LOCK AFTER LISTED FIXES

Amendment 1 genuinely fixes round 1's three blocking or cell-defining findings:

- **Finding 1:** each group's floor is now priced on exactly the population its cells score.
- **Finding 2:** the youngest band now starts at age 22.
- **Finding 3:** pooled groups now gate same-direction bias.

The v2 artifact recomputes wherever I checked it. Both bite checks hold by a wide margin. No amendment looks tailored to the disclosed DEV scores.

Two things stop me saying lock as-is:

- **A scoring defect of the same kind as round 1's finding 2.** The odd-year fill is scored on pre-career odd years that it never fills in use (new finding 2). Fixing this changes no floor, tolerance or partition, because floors are built from true data only.
- **Gaps in the record.**
  - An amended-rules dry run on TRAIN, from 16 minutes before the rules commit, is not disclosed (new finding 3).
  - Candidate scoring on DEV since the rules commit has no log.

New finding 1, the three men's `q90` cells that sit at the wage base, is a real definitional flaw. But it changes almost no verdict, so I ask for disclosure rather than a rebuild.

## Round 1's findings

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Odd-family AIME floors priced on the wrong population | **Fixed** | Cells and floors both use `group_rows` (`epuf_fill_gate.py:450-481, 645-659`; builder `:316-321`). (V) The floor `pool_size` equals the truth cell's `n` in all 30 cohort groups. For example, `odd.men.b1936_1940` is 13,101 in both, against 8,868 in v1. (V) The test checks the cell side only (new finding 7). |
| 2 | 18-29 band scored ages the assembler never fills with the mean | **Fixed** | `ODD_AGE_BANDS` now starts at 22 (`:142-148`). (V) The PSID count stays at 3,949, as it should: the PSID never filled below 22. DEV units per person are now 2.454. (V) The optional post-claim part was not done; that is acceptable. A residual of the same kind remains: new finding 2. |
| 3 | Same-direction bias across cells unchecked | **Fixed** | Pooled groups (`a22_74`, `b1936_1945`, `b1930_1945`, `b1946_1980`) and AIME p10/p90 cells added. (V) The pooled median-AIME tolerance for men is 0.042, against 0.075-0.088 for the single cohorts. (V) Pooling is within sex only; see note 8. |
| 4 | Pre fill read true odd years | **Fixed** | `score_candidate` puts NaN on the union of both masks (`:1071-1073`). (V) A test asserts it (`test_epuf_fill_gate.py:543-547`). (V) O2 treats odd years as unknown (`:1217-1219`). (V) |
| 5 | No registered scoring path or validity checks | **Partly fixed** | Added:<br>• `score_candidate` checks finiteness, `[0, 1]` and that other cells are unchanged (`:1086-1098`) (V);<br>• TEST is read only through `test_part()` (V);<br>• the module is in `BOUND_FILES` (V).<br>Still missing: a registered TEST entry point that ties the truth, tolerances and partition to the v2 artifact by hash (new finding 4). |
| 6 | "Improves" tier nearly vacuous | **Fixed** | `allowed = max(tau, min(baseline, 3 tau))` (`:1001`), with tests for the cap (`:428-461`). (V) |
| 7 | Candidates existed, contrary to the record | **Fixed for the earlier scores; record still incomplete** | The disclosure was committed in `f91d43a1` (05:40:24 UTC) and pushed (05:40:27), before the rules commit `7061200d` (06:04:18). (V, reflog) Still undisclosed: the v2 dry run on TRAIN, and the scoring on DEV since `7061200d` (new finding 3). |
| 8 | Bite checks only through degenerate failures | **Partly fixed** | D1-D6 are run and stored, and the table in §10a matches the artifact. (V) But:<br>• both summary doses are driven by trivial or degenerate cells, and one is attributed to the wrong cell;<br>• no AIME dose is reported;<br>• D1 has a cap artefact.<br>See new findings 1, 5 and 6. |
| 9 | Unmeasured failure modes | **Fixed, with a new flaw** | `r3`, `q10`/`q50`/`q90` and `partial_aime` added. (V) Three men's `q90` cells are degenerate (new finding 1). |
| 10 | Claims not supported as written | **Fixed** | Section 4.1 reworded. The AIME table now reads 32/20/8 and 34/25/13. The "1.3 to 5.1" claim and the young-worker `wint` claim are gone. The section 8 exclusion claim is true (`first_estimates_birth_evidence.py:356`). The scope sentence is added. (V) |
| 11 | "Conservative" sample size | **Fixed, but one new sentence is now false** | The sentence "Matching units rather than persons works slightly the other way in some bands" no longer holds; see new finding 5(c). |
| 12 | Tolerance as materiality | **Fixed** (recorded in section 13.1; Max's ratification still pending) | (V) |
| 13 | `epuf_matrix` join; `atcap` exactness | **Fixed** | Join and duplicate checks at `:1305-1316`, with a test. The share-of-1 rule maps to exactly the wage base (`:1101`). (V) Minor gap: the annual year range is not asserted (new finding 7). |
| 14 | Dry-run provenance | **Fixed for v0** | `61ade83a` is the parent of `14045be4` in the reflog. (V) The v2 dry run is the same problem again (new finding 3). |
| 15 | Tests | **Mostly fixed** | All five requested tests exist. Several are weaker than their names suggest (new finding 7). |

## New findings

### 1. MODERATE: three men's `q90` cells gate while their true value sits at the wage base

**Evidence.**

- **True values and tolerances (V).**

  | Cell | Truth | Tolerance | True `atcap` |
  |---|---:|---:|---:|
  | `odd.men.a22_74.q90` | 1.0 | 0.00345 | 0.1037 |
  | `odd.men.a30_44.q90` | 1.0 | 0.00374 | 0.1057 |
  | `odd.men.a60_74.q90` | 1.0 | 0.0407 | 0.1002 |

  Truth values are at `floors_v2.json:106, 166, 286`.

- **The floors are point masses (V).** Most replicates of `odd.men.a22_74.q90` are exactly `0.0`, with occasional jumps of 0.003-0.016 (lines 8792-8993). Sigma here measures how often a sample's at-cap share crosses 10 percent. It is not a sampling error in any useful sense.
- **The cell is a cliff at 10 percent (I).** While more than 10 percent of positive shares are at the cap, `q90` is exactly 1. It measures nothing about the men's upper tail, which is what round 1's finding 9 asked for. Once the share drops below 10 percent, the gap jumps to several tolerances.
- **D2 sits next to the cliff (V).** D2 (marginal draws) lands at `atcap` = 0.1005 for men 22-74, 0.05 points above it, and gets `q90` gap 0 (lines 142900-142943).
- **It drives a reported dose (V).** The stored D3 dose at one tolerance, 0.0035252 (line 152849), equals 0.25 / 70.917. The 70.917 is `odd.men.a22_74.q90` under λ = 0.75 (line 144646). So §10a's sentence "That cell is `atcap`" is wrong: the cell is this degenerate `q90`.

**Effect on verdicts (I).** Small.

- **Men 22-74:** the `atcap` cell's own lower bound is 0.1037 · e^−0.0369 = 0.0999. That is the same cliff, so `q90` duplicates `atcap` here.
- **Men 30-44:** the `atcap` bound is 0.1007, above the cliff, so `q90` never binds alone.
- **Men 60-74:** the tolerance of 0.0407 reflects real crossings in samples of 834.
- **A faithful fill:** passes, because its at-cap share tracks the truth's to within about 0.1 points (I).

The same feature already made `odd.men.a45_59.q90` report-only. It was visible in the undisclosed dry run on TRAIN (new finding 3), and is not tailoring.

**Required fix (no floor change).**

- In §10a, disclose next to the `a45_59` note that men's `q90` sits at the cap in the other three bands. In those bands it gates only as a lower bound on the at-cap share near 10 percent, and the gate measures no upper-tail dispersion for men.
- Correct the D3 sentence.
- Recommended for future registrations: compute `q90` among positive shares below the cap.

### 2. MODERATE: the odd-year fill is scored on pre-career odd years that it never fills in use

**Evidence.**

- **The odd fill owns every odd year (V).** `family_mask("odd")` returns every person's five odd years (`:290-291`), and `score_candidate` makes the odd fill own all of them (`:1072, 1088-1092`).
- **That includes pre-career years (I).** People born 1976-1980 have one to three odd years before age 22. For those born 1978-1980, the neighbouring even years are pre-career too, so they are also NaN to the fill.
- **Those values enter gating cells (V).** `partial_aime` sums every year through 2006 (`:385`). So the odd fill's guesses for those years feed `odd.{men,women}.b1966_1980.paime_*` and `.b1946_1980.paime_*`: 20 gating cells. Their tolerances are 0.018-0.078.
- **In use, those years are zero (V).** The assembler fills them under the pre-career rule.

This is the class of problem behind round 1's finding 2: a fill judged on cells it will never fill in use. The size is probably well under one tolerance (I), but the direction penalises a fill for not imitating the pre-career fill. B1, O1 and D1-D3 have the same scope.

**Required fix.**

- Make the odd family's own mask `odd_mask & ~pre_career_mask`, both in `score_candidate` and in the current-rule, oracle and perturbation paths.
- Rerun the bite, oracle and perturbation sections on DEV. Floors, tolerances and partition do not change, because `floor_group` samples true data only.
- Add a test that pre-career odd cells come back NaN and are scored at their true values.

### 3. MAJOR (record): an undisclosed dry run on TRAIN before the rules commit, and unlogged candidate scoring on DEV since then

**Evidence.**

- **The dry run (V).** `.diag/epuf-fill/floors_v2_train_dry.json` has `code_commit` `f91d43a1`, `built_at_utc` 05:48:03, 5 replicates, and uses `psid_scale_v2_try.json`. It was built from an uncommitted working tree 16 minutes before the rules commit `7061200d` (06:04:18, pushed 06:04:21). Its partition already showed `odd.men.a45_59.q90` as `floor_undefined` and the other men's `q90` cells gating.
- **The forks ledger (§12) omits it (V).** Round 1's finding 14 established that dry runs are disclosed as lineage.
- **No log of DEV scoring since the rules commit (V).**
  - `dev_score2.py` appends events to `.diag/epuf-fill/dev_events.jsonl`, which does not exist.
  - `quick_gaps.py`, `fit_by_sex.py` and `o1_from_train.py` score candidates or oracles on DEV (`part1`) and only print.
  - `quick_gaps.py` calls `g.score_candidate`, which exists only in amendment 1's code, with no tolerances. When it first ran is not recorded. If it ran before 06:04, candidate gaps on the new cells were known while the rules were still open (I, unresolved).

**Required fix, before applying any other fix in this report.**

- Commit the v2 dry run as lineage and add it to the forks ledger.
- State any rule difference between its working tree and `7061200d`.
- State when `quick_gaps.py` first ran.
- Disclose every candidate DEV score since `7061200d`, as round 1's finding 7 did. The fixes above would otherwise be written with v2 candidate scores knowable.

### 4. MINOR: no pinned entry point for scoring on TEST (round 1's finding 5, residual)

**Evidence (V).**

- `score_candidate` takes `truth`, `tolerance` and `gating` from the caller (`:1044-1055`). Nothing ties them to `runs/epuf_fill_gate_floors_v2.json`.
- Nothing scores the current rule through the same path.
- The test passes empty tolerances and an empty gating list (`test_epuf_fill_gate.py:532-542`).

**Required fix.** Add a registered `score_test(fill, family)`, or an equivalent lock-record procedure, that:

1. reads the matrix through `test_part()`;
2. computes the truth with `family_cells` on that same matrix;
3. loads the tolerances and partition from the v2 artifact, checked against a pinned SHA-256;
4. scores the current rule as a fill on the same persons;
5. returns `adoption_tier`.

Test it on synthetic matrices.

### 5. MINOR: claims in the proposal that the artifact contradicts

- **(a) D3 dose.** It comes from `odd.men.a22_74.q90`, not from `atcap` (finding 1). (V)
- **(b) D4 dose and the AIME.**
  - The "1.4 percent" dose is `pre.men.b1946_1980.ylevel`: |log 0.9| / 0.01521 = 6.93 tolerances, matching `max_gap_in_tolerances` at line 149139. That is trivially the scale factor. (V)
  - A 10 percent cut to every pre-career block moves the pooled median AIME for men by −2.2 percent, or 0.53 tolerances. No AIME cell moves more than 0.61 tolerances (lines 149142-149266). (V)
  - Say plainly that the AIME cells cannot see a 10 percent pre-career level bias, and that `plevel`/`ylevel` can. This bears on Max's AIME question.
- **(c) Matching units rather than persons.** Section 5 says it "works slightly the other way in some bands". In v2, DEV has fewer units per person than the PSID in every band, so the matching makes the gate stricter everywhere. (V) Examples:
  - men 22-29: 2.45 against 3,949 / 1,462 = 2.70;
  - men 22-74: 4.51 against 5.89;
  - men 60-74: about equal, 3.20 against 3.19.
- **(d) "None loosens a cell those scores failed" (§12).** This is overstated in two ways. (V) Both changes are forced by round 1's findings and the pre-set events rule, and neither rescues a candidate. Say so.
  - The men's young-band `wint` cell gated in v1 (as 18-29), and `odd_knn v0` failed it by 4.1 tolerances. It is now report-only (`too_few_events`). The pooled `a22_74` `wint` still gates.
  - The odd-family AIME tolerances widened, as round 1 predicted. For men born 1936-40, the median went from 0.051 to 0.082.
- **(e) `current_odd_fill` docstring.** "The single-neighbour fallback … never applies" is false for units at age 22, whose `t-1` is pre-career. (V)

### 6. MINOR: D1 copies capped earnings across years with different wage bases

**Evidence (V).** Copying year `t+1`'s capped earnings into `t` creates shares above 1. The filled `q90` is 1.0103 (line 141235). The scoring path would reject such a fill. This inflates D1's `atcap`, `q90` and `level` failures.

**Fix.** Copy the share, `x[t+1] / cap[t+1] · cap[t]`. Report-only.

### 7. MINOR: tests and provenance

- **(a) No test ties the builder's pool to `group_rows`.** The artifact agrees in all 30 cohort groups (V). Add `pool_size == truth["<group>.*_p50"].n` to `test_sizes_seeds_and_sigmas_recompute`.
- **(b) `BOUND_FILES` is incomplete.** It omits `harness/epuf_cells.py` (`weighted_spearman`, `CellValue`) and `harness/epuf_operator.py` (`wage_base`). Both shape every cell. Add them.
- **(c) The `score_candidate` tests miss the scoring.** They check inputs only. Nothing checks that the scored matrix has the fill's own cells replaced and every other cell true. Nothing checks that a fill writing into the other family's NaN cells is refused. The code does refuse it (`:1093-1098`) (V).
- **(d) A test that checks a constant.** `test_odd_units_start_at_age_22_and_bands_pool` asserts `min(low) == 22` rather than excluding a unit at age 21.
- **(e) No dirty-tree flag.** The builder records `HEAD` but not whether the bound files were dirty at run time.
- **(f) Year range not asserted.** `epuf_matrix` does not check that annual years lie in 1951-2006. A year outside that range would index negatively at `:1327`.

### 8. NOTES (no fix required)

- **Floor seeds depend on the order of `groups()`.** Adding groups re-rolled every floor: v1 → v2 tolerances moved by up to about 7 percent. For example, `odd.men.a60_74.atcap` went from 0.1168 to 0.1247 (V). No disclosed result flipped (V). Future amendments should key seeds by group name.
- **Pooled floors sample EPUF's cohort mix.** For men born 1930-45, the pooled DEV pool is 28/29/43 percent across the three cohorts. The PSID's mix is 18/26/55 (V). This is harmless.
- **No pooling across sexes.** A 0.9 sigma bias in the same direction in both sexes' pooled cells is about 1.3 sigma on a both-sex estimate (I). This is a residual limit on the materiality claim, and section 5 does not overclaim it.

## Ruling on the record (item 4)

**Chronology (V, reflog and remote log).**

- Disclosure `f91d43a1`: 05:40:24 UTC.
- Rules `7061200d`: 06:04:18, pushed 06:04:21.
- PSID v2 counts: built at `7061200d` (artifact `code_commit`).
- `23bee82c`: committed 06:09:30, pushed 06:09:52.
- v2 floor build: started 06:10:08 at `23bee82c`.
- `f8623f4d`: pushed 06:47:36.
- The candidates branch `epuf-career-fill-candidates-20261004` has no commits.

I could not check that the rules are identical at `7061200d` and `23bee82c` (I).

**Tailoring.** No amendment looks tailored to the disclosed scores.

- **They mostly work against the disclosed candidates.**
  - `pre_donor v1`'s `yr_cross` gaps are positive in all six cohort-sex cells, +0.018 to +0.028. The new pooled tolerances are 0.0146 (men) and 0.0157 (women). (V) So it would probably fail the pooled cells (I).
  - Its one failure, women 1940-45 `pzero`, now has a tighter tolerance: 0.0515 → 0.0470 (V).
  - The union mask removes the true odd years it used to read.
  - The cap on "improves" demotes `odd_quantile v1`, whose `r2` gaps were about 5.7 tolerances (I).
- **The loosenings were forced.** The odd-family AIME tolerances and the young men's `wint` cell changed because of round 1's findings 1 and 2. The candidates' odd AIME gaps were at most 0.004 (V).
- **The record still needs new finding 3.**

## Ruling on the tolerance (item 5)

**`tau = 1 * sigma` at the PSID's size is acceptable to lock as a materiality threshold.**

- **The verdict is close to a step at sigma.** The comparison's own noise is at most sqrt(1.05) times 0.087-0.212 sigma (stored noise ratios, V). So a fill with no bias fails essentially never, and a fill with bias near sigma can go either way.
- **The materiality bound is correct.** At the boundary, the root mean square error of a PSID-sized estimate built on the fill is √2 times the PSID's own sampling error.
- **The floors are strict.** They use unweighted counts, so they are tighter than the PSID's real sampling error.
- **The pooled groups carry the bound to aggregates** across cohorts and bands, within each sex.

Max should ratify with three facts in view:

1. **√2 means up to 41 percent more error.** At the boundary, the fill can add up to 41 percent to the root mean square error.
2. **Single-cohort AIME tail tolerances are very wide.** `pre.women.b1930_1934.aime_p10` has a tolerance of 0.391 log, so a 48 percent overstatement passes. The pooled groups carry the AIME materiality: their p10 tolerances are 0.17.
3. **Estimates pooled across both sexes are not gated directly.**

## What I verified

- **Rules code.** I read all of `epuf_fill_gate.py`:
  - the masks, union mask, universes and `group_rows`;
  - the band, `r3`, quantile, AIME and partial-AIME cells;
  - `floor_group`, `partition`, `score`, `adoption_tier`, `score_candidate`;
  - the oracles, `epuf_matrix` and `test_part`.

  `r3` uses only recorded even years (2008 excluded). Universes are invariant to their own family's fill.
- **Builders.** Sample sizes, pools, seeds and bite logic. The dose algebra takes the smallest linear dose over finite cells.
- **PSID scale v2 additivity.**
  - Men's bands: 3,949 + 11,148 + 9,472 + 2,670 = 27,239.
  - Women's bands: 5,318 + 13,927 + 10,663 + 2,773 = 32,681.
  - Every pooled cohort count equals the sum of its parts.
- **v2 floors recomputed by hand.**
  - All 40 groups: n = PSID count / units per person, for example 3,949 / 2.4543 = 1,609.
  - All 30 cohort groups: `pool_size` equals the truth's `n`.
  - Spot-checked noise ratios, e.g. sqrt(1,609 / 65,387) = 0.1569; the range is 0.087-0.212.
- **Partition.** 326 cells: 190 `odd`, 136 `pre`. 319 gate. The 7 report-only cells match §10a. Against v1, the report-only changes are men's young-band `atcap` (now gates) and men's young-band `wint` (now report-only).
- **Bite and results counts.** B1 97/183, B2 112/136. B2's pooled median AIME: men 1,813 / 2,266 (−20 percent, 5.27 tolerances), women 601 / 771 (−22 percent, 4.01). O1 32, O2 6. D1-D6 failing and beyond-two counts all match §10a. The total of `"passes": false` across all scored results, 822, is consistent.
- **Disclosure file.** All five events, and the v1-vs-v2 tolerance comparison for every cell a disclosed candidate failed.
- **Leakage.** There is no TEST read path besides `test_part` (searched with grep). The cache holds only `part0`/`part1`. The candidate module reads no EPUF.
- **Tests.** I read both files in full. I did not run them.