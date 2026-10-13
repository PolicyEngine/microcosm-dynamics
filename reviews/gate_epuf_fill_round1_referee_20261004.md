# Referee report: `gate_epuf_fill` registration, round 1

Branch `epuf-career-fill-20261003`, head `01966003`. Independent adversarial referee.

**What I could not do.** This session had no shell. I could only read files, so I ran neither test file and no `git log/show/diff`. Three things are therefore unverified:
- the push-time chronology;
- whether `test_bound_files_are_unchanged_since_the_build` still passes after `7a49b520` ("tier counts");
- whether the dry-run commit `61ade83a` is an ancestor of `14045be4`.

All the evidence below comes from reading the code and doing arithmetic by hand on the committed artifacts. I read no EPUF microdata and called nothing that reads EPUF.

## Verdict: AMEND BEFORE LOCK

Most of the machinery is sound: the split, the masks, `aime_35`, the floor algebra, the partition rule, the oracles' permutation logic and the scoring arithmetic. The artifact also confirms the operating-characteristic claim. But three findings change a floor or a cell definition, so lock-after-fixes is not possible:
- **Finding 1:** the floor pool for the odd-family AIME groups is a different population from the one the cell scores.
- **Finding 2:** the 18-29 band scores ages 18-21, which the assembler never fills with the neighbour mean.
- **Finding 3:** per-cell tolerances leave common-direction bias across cells unchecked. That matters most for the AIME distribution, which Max asked about.

Several more rule fixes do not touch floors (findings 4-7). One record problem must be fixed before any amendment: candidates already exist (finding 7).

---

## Findings

### 1. BLOCKING: the floor pool for the odd-family AIME groups differs from the population the cell scores

**Evidence (verified).**
- The cell's population: `odd_cells` computes the AIME quartiles over `career_universe`, persons positive in any unmasked year 1968-2006 (`epuf_fill_gate.py:425-443`).
- The floor's pool: `group_eligible` builds it from `family_universe("odd")`, persons positive in an even year 1996-2006 (`epuf_fill_gate.py:684`, `:653-654`).
- Every pool member is in the career universe, but the reverse fails. People born 1936-45 who stopped working before 1996 are in the cell but never in a floor sample.
- The PSID count, 145 for men born 1936-40, uses the career-universe definition (`build_epuf_fill_psid_scale.py:63-64, 81-92`).
- The artifact shows the gap between the two populations:

| Group | Cell `n` (truth) | Floor `pool_size` |
|---|---:|---:|
| `odd.men.b1936_1940` | 13,101 | 8,868 |
| `odd.women.b1936_1940` | 12,064 | 7,627 |
| `odd.men.b1941_1945` | 15,958 | 12,103 |
| `odd.women.b1941_1945` | 15,125 | 11,245 |

**Effect (inferred).**
- The `pre` groups for nearly the same cohorts use the same universe for pool and cell, at similar `n`.
- Their median tolerances are 0.087 (men 1935-39, n=131), 0.125 (women 1935-39), 0.066 (men 1940-45) and 0.096 (women 1940-45).
- The odd-family medians are 0.051, 0.088, 0.051 and 0.070, roughly 60-75 percent of those.
- So the 12 odd-family AIME tolerances are priced on the wrong population, probably too tight. The `noise_ratio` for these groups also uses the wrong N.

**Required fix.**
- Make `group_eligible` return exactly the population the cell counts: for odd cohort groups, the career universe intersected with sex and cohort.
- Rebuild the four groups' floors.
- Add a test that, for every group, the pool equals the set of persons the group's cells count. Pool ⊆ universe is not enough.

### 2. MAJOR: the `a18_29` band scores ages 18-21, which the assembler never fills with the neighbour mean

**Evidence (verified).**
- `build_career` emits years only from `coverage_start = max(1968, birth_year + 22)` (`career.py:1004, 1070-1077`).
- The PSID careers frame is built from `record.years` (`psid2010.py:2005-2012`). So every PSID `gap_imputed` unit behind `odd.*.a18_29` is at age 22-29.
- EPUF's `a18_29` units run from 18 to 29 with no career-start restriction (`epuf_fill_gate.py:119-124, 363-368`).
- At ages 18-21 the assembler's actual rule is "zero" (family `pre`, which `yzero`/`ylevel` already score), not "neighbour mean". So these units are scored twice, under two different current rules.
- The pool and the per-person unit rate behind `n = 1,321` and `n = 1,778` are measured on a different age range from the PSID count they are scaled to.

**Effect (inferred).**
- The band's truth values and sigmas are driven by teenagers' entry dynamics, which are exactly where O1 fails (`wint` and `zexit` at 18-29).
- An odd-year candidate is judged on units it will never fill in deployment.

**Required fix.**
- Restrict odd units to `t >= birth_year + 22`, making the band `a22_29`.
- Rebuild the `odd.men.a18_29` and `odd.women.a18_29` floors, the sample sizes and the partition for those 14 cells.
- Optionally do the same for post-claim units in 60-74. The PSID fills no years after claiming (`career.py:1003, 1051-1053`), while EPUF fills all of them.

### 3. MAJOR: per-cell `K = 1` leaves common-direction bias unchecked, including bias in the AIME distribution

**Evidence (verified from `runs/epuf_fill_gate_floors_v1.json`).**
- The `pre` AIME tolerances are wide:
  - median: 0.066-0.125 log;
  - 25th percentile: 0.129-0.192 log, that is, 14-21 percent.
- A fill that understates every pre-1946 cohort's median AIME by 6 percent passes all six median cells.
- The current pre-career rule itself passes `pre.men.b1940_1945.aime_p75` (gap −0.033, 0.88 tolerances; artifact line 57404). It sits at only 1.26 tolerances on that cohort's median, an 8 percent understatement (line 57395).
- The odd-family AIME cells cannot bind. The current rule's gaps there are at most 0.25 percent against tolerances of 3.3-13.7 percent. This is because they cover cohorts whose AIME window holds only 1-5 masked years, at ages 57-61.

**Effect (inferred).**
- PSID-based estimates are pooled across cohorts and sexes; the DYNASIM comparisons use the whole cohort. Their sampling error is about `1/sqrt(k)` of the per-cell error.
- A bias of 0.9 cell-sigma in the same direction in all six `pre` cohort-sex cells is therefore about 2 sigma on a pooled 1930-1945 estimate. The PSID would detect it, yet the gate passes it.
- "A fill within the tolerance is never the larger source of error" holds cell by cell, not for aggregates.

**Required fix (truth-side, so it can be done before seeing any candidate).**
- Add pooled gating cells, each with its floor at the pooled PSID size:
  - per family and sex, pooled over cohorts: the AIME quartiles for 1930-45, plus `pzero`/`plevel` and `yzero`/`ylevel`;
  - per sex, pooled over bands: `r1`, `r2`, `level`, `zexit`.
- Alternatively, register a sign rule: for example, the mean standardized gap over a statistic's cells must lie within `1/sqrt(k)`.
- Also consider AIME p10 and p90 cells. The current pre-career rule hits the lower tail hardest: −63 percent at p25 for women born 1930-34 (gap −0.84 log).

### 4. MAJOR: in family `pre`, the fill reads true odd years 1997-2005, which the PSID never records

**Evidence (verified).**
- The two families are masked separately (§3), so a `pre` fill is handed the true odd years.
- The candidate `PreDonorFill.donors` matches on `_first_recorded(readable, …)`, where `readable` hides only `fill_mask`, the pre mask (`estimates/epuf_fill.py:994-995`).
- O2 matches the same way (`epuf_fill_gate.py:995-1006`).
- For people born after about 1970 the career starts in 1992 or later, so the "first five recorded years" include 1997, 1999 and so on. On the PSID those years are neighbour means or learned fills.
- `yr_cross` at age 24 falls on an odd year for half of the people born 1973-1981, and is read as truth.

**Effect (inferred).** The `b1966_1980` cells, and partly `b1956_1965`, score a fill with information it will not have in deployment. The gate overstates its quality there.

**Required fix.**
- Register that each family's fill receives the union of both masks as unknown (NaN) inputs, while the cells score only the family's own mask.
- Floors and partition do not change, because truth cells are unaffected. O2 should be rerun under the same rule.

### 5. MAJOR (ceremony): no registered scoring path, and the fill-validity invariants are unenforced

**Evidence (verified).**
- `epuf_fill_gate.py` scores matrices handed to it. Nothing in the registered code:
  - hides masked values from a candidate;
  - checks that unmasked cells come back unchanged;
  - checks that filled values are finite and lie in `[0, wage base]`.
- The claim that the true and filled matrices share every universe (§4) holds only if the fill leaves the even years alone. `odd_cells` recomputes the universe, and reads `t±1`, from the filled matrix (`:355-356, 370-401`).
- A fill that edits recorded years could move `r1`, `zint`, `zexit` and `wint`.
- The working-tree DEV scorer overwrites unmasked cells (`.diag/epuf-fill/dev_score.py:27`), but it is unregistered.
- The candidates receive the full true matrix and rely on `known = … & ~fill_mask` (`epuf_fill.py:619, 757`).
- The prior round flagged the same problem (`reviews/gate_epuf_round1_referee_20261002.md` finding 7).

**Required fix.**
- Add a registered `score_candidate(fill, part)` that:
  1. passes NaN in every cell of the union mask;
  2. asserts that the output is finite, `0 <= x <= cap`, and equal to the input on unmasked cells;
  3. reads TEST through a single audited call.
- Pin it in `BOUND_FILES` and in the lock record. Test each assertion.

### 6. MAJOR: the "improves" tier is nearly vacuous wherever the current rule's gap is non-finite

**Evidence (verified).**
- `adoption_tier` allows `|gap| <= max(|current gap| or inf, tau)` (`epuf_fill_gate.py:878-883`).
- The current rules have non-finite gaps in 21 gating `odd` cells (`zint`, `zexit`, `wint`) and in 30 gating `pre` cells (`plevel`, `pr_in`, `pr_cross`, `ylevel`, `yr_cross`). In all 51, any finite gap is "no larger".
- The current pre-career rule's `pzero`/`yzero` gaps are 0.6-1.5 log.
- The current rule fails 59 of 60 `pre` cells (line 57802). So in family `pre`, "improves" reduces to: no non-finite gap, and AIME quartiles no worse than zeroing.
- A pre-career fill missing `pr_cross` by five tolerances would be adopted as an "uncertified improvement".

**Forking path.** This tier was added after the TRAIN dry run showed an oracle failing `r2`/`r4` (§9). It does not change certification, so it is not a self-rescue of the gate. It is a loosening of adoption, made after seeing results that stand in for candidates.

**Required fix (no floor change).** Cap the allowance at `max(tau, min(|current gap|, M * tau))` with `M` fixed now, for example 3. Alternatively, require `|gap| <= max(tau, |oracle gap| + tau)` using the stored DEV oracle gaps. Either makes "improves" mean near-oracle performance.

### 7. MAJOR (record and forking paths): candidates already exist, contrary to the proposal

**Evidence (verified).**
- The proposal header says: "No candidate has been fitted" (line 10).
- The working tree contains:
  - all four registered fills, implemented in the untracked `src/populace_dynamics/estimates/epuf_fill.py`;
  - fitted blobs in `.diag/epuf-fill/cache/{odd_quantile,odd_knn,pre_donor,pre_chain}.npz`;
  - `dev_fit.py`, which fits on TRAIN;
  - `dev_score.py`, which scores on DEV against the registered tolerances.
- No DEV score output is present, and no TEST cache exists: only `part0.npz` and `part1.npz`.
- Developing candidates on DEV is allowed (§2). But any amendment from this round will now be written with candidate behaviour knowable.
- The implementation also departs from §7.1:
  - it uses an AR(1) copula, not a "person-level" one;
  - it adds context at offsets 5-9 (`epuf_fill.py:233, 249-281`).

**Required fix.**
- Correct the ceremony stage.
- Before amending, commit (or hash into the record) any DEV candidate scores already produced, so the next referee can check that the amendments do not favour them.
- Justify every amendment on truth-side grounds only.
- Align §7 with the code, or state that §7 describes candidates loosely and the registered commit plus SHA-256 governs.

### 8. MAJOR: the bite checks hold only through degenerate failures; the AIME cells have no dosed demonstration

**Evidence (verified).**
- B1's 48 failures include 21 infinite ones (filled zero shares).
- B2's 54 include 30 NaN or infinite ones and 12 infinite-ratio `pzero`/`yzero` ones.
- B1 and B2 show that the gate rejects the current rules, which is what Max asked for. They say nothing about the cells' detection point for realistic errors. The prior round's central flaw was exactly a bite with no operating characteristic.
- The oracles help only in part, because O1 and O2 preserve several cells exactly by construction:
  - O1's strata nest inside the 30-44, 45-59 and 60-74 bands, so `zint`, `zexit`, `wint`, `atcap` and `level` there have gap 0.0 (lines 57880-58092).
  - O2 preserves `pzero`, `plevel`, `pr_in`, `yzero` and `ylevel` exactly.

**Required fix.** Before lock, register and report truth-side dosed bites with their gap in tolerances. For example:
- O2 with blocks scaled by 0.90 and by 0.95: an AIME and `plevel` level bias;
- O1 with draws shrunk toward the stratum median: dispersion;
- "copy `t+1`";
- marginal draws within sex and age.

Report each one's dose at 1 and 2 tolerances, as in the prior round's finding 3. Report only; no new pass condition is needed.

### 9. MINOR: unmeasured failure modes

The failure modes named in the prompt are caught (inferred from the cell definitions):
- **"Copy `t+1`":** gives `zint` and `wint` of 0, an infinite gap, and pushes `r1` up.
- **Marginal draws:** `r1` collapses.
- **Right levels, wrong ranks:** `r1` catches it.

Not measured:
- the marginal dispersion of the share at `t`, since only the mean (`level`) and `atcap` are scored;
- persistence from a masked year to recorded years beyond ±1;
- any AIME effect for cohorts born 1946 and later. For most of the PSID-2010 cohort the gate's AIME coverage is nil.

Consider the following, gating or report-only:
- p10, p50 and p90 of the positive share at `t`;
- a partial-AIME proxy for people born 1946-65: top-k indexed earnings through 2006.

### 10. MINOR: claims not supported as written

- **§4, "No universe or conditioning denominator reads a masked year".** The universes do not, but:
  - `atcap`'s denominator is `centre > 0` (`:418`);
  - every correlation subset is "positive in both", which reads `t`.

  Reword, and note that zero-selection error moves `atcap` and the `r` cells.
- **§9's AIME table reports log points as percentages.** Men 1930-34: the DEV log gap is −0.384, a 32 percent fall, not 38 (line 57270). In percent the table should read 32/20/8 and 34/25/13.
- **§10, "1.3 to 5.1 tolerances at the median".** The medians run 1.26-4.56; 5.1 is women 1930-34 at p25 (line 57537).
- **§10, "(infinite)" for `pr_in`, `pr_cross` and `yr_cross`.** These are NaN: there are no positive pairs.
- **§10, "Young workers' re-entry (`wint`) needs more than the neighbours too".** This is unsupported. O1's 15-19 age stratum straddles the band's age-18 edge (`_ORACLE_AGE_EDGES`, `:170`). Its `wint`/`zexit` failures appear only in the one band whose strata do not nest (inferred).
- **§8, "That module is listed in the reducer's `POST_REVIEW_SOURCE_EXCLUSIONS`".** It is not. Only `harness/epuf_fill_gate.py` is (`first_estimates_birth_evidence.py:356`), and `epuf_fill.py` is untracked under `src/`.
- **Scope.** A pass certifies the fill on EPUF's administrative, capped, disclosure-perturbed earnings. In deployment the conditioning years are PSID survey reports of uncapped labour income. Say so in "What this gate is".

### 11. MINOR: the "conservative" sample-size claim

Three things affect the size behind the age-band floors:
- the PSID count includes filled years 2007-2013 (`_STRUCTURAL_GAP_YEARS = 1997..2011` plus 2013; `career.py:35, 1058-1062`);
- it includes single-neighbour copies;
- matching units rather than persons gives EPUF samples more units per person in some bands: 2.99 against the PSID's 2.70 at 18-29.

Most of this, together with unweighted counts and the PSID's clustering by family, makes the gate stricter. The person-clustering effect runs slightly the other way. State the claim as "stricter on balance".

The "unweighted counts are stricter" claim holds (inferred): the Kish design effect is at least 1, so the effective n is at most the count.

### 12. MINOR: §12 conflates two rejected alternatives; Max should ratify the reading of "floor"

- With same-person scoring, the house formula applied to full-DEV halves gives a tolerance of roughly `4.5 * sqrt(2n/N) * sigma`, about 0.55-1.35 sigma (inferred from the stored noise ratios of 0.087-0.212). That is the same order as `K = 1` and is tied to the comparison's real noise.
- The proposal's PSID-size sigma is a defensible materiality yardstick. It matches the house's deployment-scale floor (`gates.yaml:22-30`). But it is not "the noise of the comparison" in the sense other gates use.
- Required: record this alternative in §12, and have Max explicitly ratify that the tolerance is a materiality threshold.

### 13. MINOR: code robustness

- **`epuf_matrix` (`:1066-1072`).** The `searchsorted` join assumes every annual `person_id` is in the demographic file. The reader does not validate this (`data/epuf.py`). A missing id would write its earnings into a neighbouring person's row, possibly a DEV row; an id past the end would raise. Assert `ids[position] == annual ids` and no duplicate (person, year) rows. If the assertion ever fires, rebuild the floors.
- **`atcap` uses `centre >= cap`.** Require candidates to emit exactly `share * cap` at the cap, or compare with a tolerance.

### 14. MINOR: provenance of the dry run

- `.diag/epuf-fill/floors_train_dry.json` was built at `61ade83a` (04:52 UTC). The DEV build was at `d21aa659` (05:04 UTC).
- `61ade83a` is not in the listed branch history, and I could not check whether it is reachable.
- Commit the dry-run artifact as lineage and state its commit relationship to `14045be4`.

### 15. MINOR: tests

The existing tests are good for what they cover. Add:
1. pool equals the cell's counted population (finding 1);
2. fill-validity and masked-input tests for the scoring path (finding 5);
3. the `epuf_matrix` join assertion (finding 13);
4. a universe-invariance test for `career_universe` and the AIME cells;
5. a test that the `odd` units exclude ages under 22 after finding 2's fix.

---

## What I verified

- **Split, masks, current rules.** `split_part` matches the stated hash and thresholds. `odd_mask`, `pre_career_mask`, `current_odd_fill` and `current_pre_career_fill` match `career.py`'s rules on EPUF; the one-neighbour fallback is moot there.
- **`aime_35`.** It follows the statute for people born 1929-1945: 35 computation years, every year from 1951 through age 61, indexing to NAWI at age 60, later years nominal, and a floor over 420 months. The test pins it to `ss.statutory_aime.aime`. I could not run that test.
- **Cell helpers.** `_share`, `_spearman_mean` (events = smallest pair-year) and `weighted_spearman` (mid-ranks for ties) are correct. The `r1`/`r2`/`r4` pair counts are 10/4/3.
- **Floor, partition, scoring, oracles.** `floor_group` is correct: disjoint samples, `/sqrt 2`, RMS, seeds. `partition` follows the stated order. `score` and `adopt` match the text. The O1/O2 key packing has no collisions, and `_permute_within` permutes only within keys.
- **Counts.** The artifact has 136 cells and 24 groups. 130 gate: 70 `odd`, 60 `pre`. The six report-only cells are as listed.
- **Tolerances.** Every range in §10's table matches the artifact.
- **Sample sizes and noise ratios.** They recompute; for example, men 18-29 gives 3,949 / 2.989 = 1,321 and `sqrt(1321/80398)` = 0.128. The range is 0.087-0.212.
- **Bite counts.**
  - B1: 48 of 70. `r1` 7.0-16.9 tolerances, `r2` 3.7-12.8, `r4` 6 of 8, `atcap` 8.1-17.2.
  - B2: 54 of 60, with 12 of 18 AIME quartiles beyond 2 tolerances.
  - O1: 16 failures (7 `r2`, 6 `r4`, 2 `wint`, 1 `zexit`), with gaps of 0.015-0.043.
  - O2: 4 `yr_cross` failures at 1.11-1.20 tolerances.
  - The TRAIN dry run's 131 gating cells, 49/71 and 55/60 match §9.
- **Operating characteristic.** A faithful fill's gap has SD of at most about `sqrt(1 + 1/20) * sqrt(n/N) * sigma`. The artifact supports this: O1's per-seed SD over sigma is about 0.10 for men 30-44 `r2` and about 0.13 for women 60-74 `r4`, both below their noise ratios. So with K = 1, the chance that a zero-bias fill fails any of 130 cells is negligible, and the verdict is close to a step at `|bias| = sigma`.
- **Leakage.** No TEST value reaches a floor, a tolerance, the partition or the oracles. The builders accept only TRAIN or DEV, and the PSID builder reads no EPUF. In `.diag`, candidate fitting uses TRAIN (`part0`) and scoring uses DEV (`part1`); there is no TEST cache.
- **The two dry-run rule changes.** Universe membership in the oracle strata affects report-only output, so it is harmless. The "improves" tier changes adoption, not certification; see finding 6.