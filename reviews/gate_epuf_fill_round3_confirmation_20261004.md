**Verdict: LOCK AFTER LISTED FIXES**

Round 2's eight findings are fixed or disclosed. The v3 floors match v2's, and the TEST entry point is pinned and reads TEST only through the lock. Three things need fixing before lock, and none of them needs a new floor build:

- **New finding 1:** one round-2 fix widened the "improves" allowance on a cell where the best disclosed odd-year candidate was blocked. The proposal doesn't say so.
- **New finding 2:** the record of DEV scores isn't closed. A newer candidate has been checked against DEV and isn't logged.
- **New finding 3:** small gaps in the TEST entry point.

**What I could not do.** This session had file-reading tools only, with no shell. So:

- **Tests not run.** I did not run the three test files. What I say about tests comes from reading them.
- **No `git diff` or `git show`.** I took commit times from the reflog, read as plain files under `.git/logs`.
- **No EPUF microdata.** I read none, including the `cache/*.npz` files, and called no EPUF reader.

Each claim is marked **(V)** for verified (I read it, or did the arithmetic on stored values) or **(I)** for inferred.

## Round 2's findings

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Men's `q90` sits at the wage base | **Disclosed** | §10a discloses the 22-74, 30-44 and 60-74 bands and the "lower bound on the at-cap share" reading. It recommends computing `q90` below the cap in future. (V) The D3 sentence is corrected: v3's artifact names `odd.men.a22_74.q90` as D3's dose cell (`floors_v3.json:152851`). (V) |
| 2 | Odd fill scored on pre-career odd years | **Fixed** | `family_mask("odd")` is now `odd_mask & ~pre_career_mask` (`epuf_fill_gate.py:302-303`). (V) `score_candidate` uses it (`:1152`). (V) The perturbations restore every non-owned cell to its true value (`build_epuf_fill_gate_floors.py:211-212`), and O1 is masked to the family's own cells (`:445-453`). (V) Tests: `test_odd_family_owns_only_career_odd_years` and `test_score_candidate_scores_own_cells_and_keeps_the_rest_true` (V, read only). Bite, perturbations and oracles were rerun in v3. (V) |
| 3 | Undisclosed TRAIN dry run; unlogged DEV scoring | **Fixed, with a residual** | `runs/epuf_fill_gate_floors_train_dryrun_v2pre.json` is committed. Its header matches `.diag/.../floors_v2_train_dry.json` (commit `f91d43a1`, 05:48:03 UTC, 5 replicates). (V) It is in the forks ledger, with the paragraph in §12. (V) The time `quick_gaps.py` was written (06:18:42 UTC) is stated. (V) Eight events after `7061200d` are disclosed in `..._after_amendment_1.json`, and three in `..._after_round_2.jsonl`. The jsonl is identical to `.diag/epuf-fill/dev_events.jsonl`. (V) Residuals:<br>• "No change to the rules module or the builders is recorded" says nothing was recorded; it does not say nothing changed.<br>• The dry run used a different set of PSID counts (`psid_scale_v2_try.json`, SHA-256 `e2a175…`, not the registered `b35e12…`), and the disclosure doesn't mention it. (V)<br>• Later DEV checks are unlogged; see new finding 2. |
| 4 | No pinned TEST entry point | **Fixed** (minor gaps: new finding 3) | `score_registered` (`epuf_fill_scoring.py:83-154`) does each step round 2 asked for:<br>• loads v3 and checks it against a pinned SHA-256 (`d403a824…`), and requires `registered_build` and `lockable` (V);<br>• reads TEST through `g.test_part` (V);<br>• computes the truth with `family_cells` on that same matrix (V);<br>• scores `current_rule(family)` through `score_candidate` (V);<br>• returns the tiers and `adopt` (V).<br>`test_the_scoring_module_pins_the_registered_build` checks the hash. (V, read only) |
| 5 | Claims the artifact contradicts | **Fixed** | (a) D3 dose cell corrected (V). (b) §10a now says plainly that the AIME cells can't see a 10 percent pre-career bias, while `plevel`/`ylevel` can, and gives the AIME doses (12.5 and 13.5 percent, matching `:152854, 152862`) (V). (c) §5 now says matching units makes the gate stricter in every band (V). (d) §12 now admits the two loosenings (V). (e) The `current_odd_fill` docstring is corrected (V). |
| 6 | D1 copied capped dollars | **Fixed** | D1 now copies the share (`builder:233-239`). (V) No filled value above 1 remains in v3; v2 had 4. (V) D1 now fails 63 of 183 cells, down from 92. (V) |
| 7 | Tests and provenance | **Fixed** | (a) Pool equals the cells' `n` for cohort groups (`test_epuf_fill_gate_floors.py:151-159`). (b) `BOUND_FILES` now includes `epuf_cells.py` and `epuf_operator.py`. (c) Tests that the scored matrix keeps every non-owned cell true, and that a fill writing into the other family's cells is refused. (d) `test_a_masked_year_at_age_21_is_no_odd_unit`. (e) `bound_files_clean` is recorded and is `true` in v3. (f) The annual year range is asserted (`:1394-1397`). All (V) by reading. |
| 8 | Notes | **Recorded** | §13 records all of them. (V) |

## The floors are unchanged

- **Same structure (V).** Every top-level section of v3 spans exactly the same number of lines as in v2, shifted by one. The extra line is the new `bound_files_clean` key.
  - truth: 1,632 lines;
  - groups: 132,882 lines;
  - partition: 328 lines;
  - tolerance: 321 lines.
- **Tolerances (V).** I read both tolerance blocks in full: 319 entries, matching entry for entry by eye.
- **Partition (V).** The seven report-only cells and their reasons are identical.
- **Truth (V for samples).** The values I sampled are identical.
- **Group records (I).** I did not compare the replicates value by value. The identical extents and `test_registered_floors_equal_the_v2_floors_exactly` (read, not run) support equality.
- **Unchanged inputs (V).** The EPUF and PSID-scale hashes and the constants are unchanged.
- **What changed (V).** Only the fill scoring:
  - B1: 97 cells beyond two tolerances became 96, and 99 failing became 100;
  - D1-D3 counts moved;
  - B2, O1 (32 failing) and O2 (6 failing) are unchanged.

## New findings

### 1. MODERATE: the change to `CurrentOddFill` moved the current rule's gaps, and so the "improves" allowances, in the young bands. One loosened cell is where the best disclosed odd candidate was blocked.

**Evidence.**

- **The current rule's gaps moved between v2 and v3 (V).** In v2 the current rule averaged the true age-21 year at age 22. In v3 it is a fill that sees age 21 as unknown and copies `t+1`. Its gaps in tolerances:

  | Cell | v2 | v3 | Allowance effect |
  |---|---:|---:|---|
  | `odd.women.a22_29.level` | 0.11 | 1.23 | looser: 1.00 → 1.23 τ |
  | `odd.men.a22_29.level` | 0.31 | 1.09 | looser: 1.00 → 1.09 τ |
  | `odd.men.a22_29.q10` | 1.47 | 0.60 | tighter |
  | `odd.men.a22_29.q50` | 3.79 | 1.94 | tighter |
  | `odd.men.a22_29.q90` | 2.62 | 2.01 | tighter |
  | `odd.men.a22_29.r3` | 3.64 | 2.63 | tighter |
  | `odd.men.a22_29.zexit` | ∞ | 36.4 | none (still above 3) |

  The rows come from `floors_v2.json:135206-135294, 136049` and `floors_v3.json:135207-135295, 136050`.

- **Where the disclosed candidate stood.**
  - **When it was scored (V).** Event 8 (`odd_qrf_sex2`, 07:05 UTC) was scored against v2 tolerances. The round-2 fix commit `cb76ad15` came at 07:16:52 UTC (reflog epoch 1791098212), so these scores were known while the fixes were being written.
  - **The binding cell (V).** Event 8 fails `odd.women.a22_29.level` by +0.0203 against a tolerance of 0.0185, or 1.10 τ.
    - Under v2's current rule the allowance there is 1.00 τ, so the cell blocks "improves".
    - Under v3's it is 1.23 τ, so the cell no longer blocks.
  - **Its other binding cell (V).** `odd.women.b1966_1980.paime_p25` fails by 1.015 τ against a current gap of 0. Finding 2's fix touches exactly that cohort, so it may also move this cell. I can't tell from the record, because no odd candidate has been scored on DEV since the fixes.
- **Not clearly tailoring (I).**
  - The change follows from round 2's findings 4 and 5(e), and it is applied evenly.
  - Its effects go both ways: four cells are tighter and two looser.
  - It affects only the "improves" tier, not certification.
- **The "faithful" claim is only partly true (V).**
  - `build_career` takes any observed PSID year from 1968 on as a neighbour (`career.py:1010-1031, 968-969`), with no age filter.
  - `family_earnings_panel` keeps heads and spouses at any age (`data/family.py:790-800`).
  - So the assembler uses the two-sided mean at age 22 whenever the person was a PSID head or spouse at 21. It falls back to one neighbour only when that row is missing.
  - §3 and the `CurrentOddFill` docstring say the fallback is what `_impute_gap` does, without that qualification.

**Required fix (no rebuild).**

- In §12a, disclose:
  - the v2→v3 change in the current rule's young-band gaps (the table above);
  - its effect on the improves allowances;
  - that the change was made while event 8's cell-level failures were known.
- Qualify the faithfulness claim in §3 and the docstring.
- Then do one of these:
  - **(a)** Report the share of PSID-2010 age-22 filled units that have an observed age-21 year. This is computable from the PSID with no EPUF read. Have Max accept the always-fallback choice.
  - **(b)** Register a neutral rule: where the always-mean and always-fallback current rules differ, the improves allowance uses the smaller of the two current gaps.

### 2. MINOR (record): the DEV disclosure isn't closed

**Evidence.**

- **A newer candidate exists (V).** `.diag/epuf-fill/cache/pre_chain3.npz` is there.
- **It has been checked against DEV truth (V).** `.diag/epuf-fill/debug_chain.py` fills DEV persons (`part1`) with it and prints the fill's mean share and zero rate against the truth at ages 15-22. Those are the `ylevel`/`yzero` statistics, which gate.
- **It isn't logged (V).** Neither `dev_events.jsonl` nor the committed `..._after_round_2.jsonl` mentions it. Yet the header says every DEV score is disclosed.
- **Timing (I).** It probably ran after `7eab0914` (07:34:31 UTC).
- **Uncommitted code (V).** The disclosed `code_sha256` values point at `src/populace_dynamics/estimates/epuf_fill.py`, which is untracked, so those bytes can't be audited later.

DEV development is allowed, and the floors are frozen, so this threatens no floor (I). It matters only if the rules change again.

**Fix.**

- Log `pre_chain3` and every other DEV check up to lock, and close the log in the lock record with a timestamp.
- Make the header's claim "through <time>".
- Commit each candidate code version whose hash is cited, or keep its bytes.

### 3. MINOR: gaps in the TEST entry point

- **Constants not pinned (V).** `wage_bases` and `nawi` come from the caller and are neither pinned nor recorded (`epuf_fill_scoring.py:86-87`).
  - `CurrentOddFill` converts shares to dollars with `epuf_operator.wage_base` (`:365`).
  - `score_candidate` uses the caller's mapping (`:1149`).
  - So a different mapping would silently mix the two. Build both inside the module, as the builder does (`builder:347-348`), and record a hash.
- **No rule for an undefined TEST truth (V).** Nothing says what happens when a gating cell's TEST truth is undefined (non-finite, or zero for a log ratio). Its gap is NaN, so every fill fails it, the current rule included. Register a rule now, such as "report it and drop it from every score".
- **Scoring module not bound (V).** Its own bytes are bound nowhere. It isn't in `BOUND_FILES`, which predates it. The lock record should pin `7eab0914` or the file's SHA-256.
- **Candidates not checked (V).** It doesn't check the candidates against their registered commit and artifact SHA-256 (§7). That can be a step in the lock record instead.

### 4. NOTE for decision d927: "improves" lets an adopted fill sit outside the materiality bound

**Evidence (V).** The leading pre-career candidate on DEV (`pre_donor`, 07:22 UTC) is in the "improves" tier. It misses `pre.women.b1930_1945.aime_p10` by +0.333 log (about +40 percent), or 2.0 τ. That is the pooled cell the round-2 notes rely on to carry the AIME's materiality.

**Effect (I).** "Improves" allows up to 3 τ. At that level a fill adds up to √10 ≈ 3.2 times the PSID's own sampling error to the root mean square error, against √2 for a certified fill. §7.3 already says "improves" is uncertified. Max should ratify with this fact in view.

## What I verified

- **Code read in full:**
  - `epuf_fill_gate.py`: masks, current rules, cells, scoring, TEST read;
  - `epuf_fill_scoring.py`;
  - the floor builder;
  - `career._impute_gap` and `build_career`'s use of observed sources;
  - `psid2010._careers` and the `family_earnings_panel` docstring.
- **`CurrentOddFill`:**
  - It averages the neighbours in dollars, using each neighbour's own wage base, then divides by year `t`'s base and caps at 1. (V)
  - At age 22 it copies the known neighbour. (V)
  - The "both unknown" case can never happen. An owned year is at or after the career start, so `t+1` is recorded. (I, from the masks)
- **`CurrentPreFill`** zeroes exactly the family's own mask. That is faithful: the assembler counts nothing before the career start. (V)
- **Artifacts:**
  - the v2 and v3 tolerance blocks compared in full; the partitions and section extents compared;
  - the bite, perturbation, dose and oracle counts match §10a, including the O1 breakdown (8+10+9+3+1+1 = 32). (V)
- **Disclosure:** both disclosure files, `dev_score2.py`, `fit_by_sex.py`, `fit_pre.py`, `debug_chain.py`, and the `.diag` cache file names. I opened no `.npz`.
- **Chronology from the reflog (V):**
  - `f8623f4d` committed at 06:47:26 UTC;
  - `cb76ad15` committed at 07:16:52, pushed 07:16:54;
  - v3 built at 07:16:56;
  - DEV events at 07:22, 07:30 and 07:31;
  - `7eab0914` committed at 07:34:31.
- **Tests:** I read all three files. I did not run them, and I did not check that the bound files are byte-identical at `cb76ad15` and HEAD; `test_registered_build_is_bound_to_its_rules` checks that.