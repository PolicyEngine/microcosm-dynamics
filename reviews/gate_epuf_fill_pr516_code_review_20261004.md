**Verdict: REQUEST CHANGES**

The registration itself holds up. The candidates are fitted on TRAIN only, nothing reads a masked cell, the files are pinned by SHA-256, and the DEV numbers in the document match the log. But the opt-in PSID path has a real correctness bug (finding 1), and two robustness hazards (findings 2 and 3) should be fixed before lock.

Most fixes touch `epuf_fill.py`. That file is pinned by `test_the_fill_code_is_unchanged_since_the_fit`, so changing it means re-fitting at a new commit and updating `code_commit`. None of the fixes below changes the bytes `to_bytes` writes (finding 4 is the one exception, flagged there).

**I could not run git or pytest in this session**: only read and search tools were available. So I have not checked `git diff 70553e70 940ad6f1`, whether `career.py`, `cohorts/psid2010.py` and the registered runs are untouched, the test results, or the manifest's SHA-256. Everything below comes from reading the files at the PR head.

## Findings

**1. Medium — learned odd fills break or diverge on real PSID gap years** (`psid2010_epuf_fill.py:120-128`, `epuf_fill.py:983-1003`, `epuf_fill.py:652-698`)
- **What goes wrong:** `fill_careers` builds the shares the fills see from `observed` rows only. But `career._impute_gap` (`career.py:964-978`) also fills a gap from other neighbours: a pre-career observed year, or `boundary_2014` for the 2013 seam (`career.py:1059-1062`). So a `gap_imputed` year can have no neighbour the fill can see. Two examples:
  - the 2013 seam when 2012 is unknown;
  - a person whose career starts in 1997, whose 1996 is pre-career, and whose 1998 is missing.
- **What each fill does with such a year:**
  - `OddKnnFill` leaves it NaN, because `take` requires a finite `left`. `drawn()` then raises "a learned fill returned an invalid share", so the registered alternative crashes on real data.
  - `OddForestFill` silently writes a zero where the assembler wrote the neighbour's value.
- **Out-of-range years:** the module docstring (`:11-12`) says *every* `gap_imputed` year gets a draw. That includes 2007-2013, which lie outside the fills' training years (1991-2005) and outside anything the gate scores (`epuf_fill_gate.py:141-143`).
- **Tests miss it:** neither test's data has the seam, `boundary_2014`, or a gap with no visible neighbour.
- **Fix (in `psid2010_epuf_fill.py`, which is not pinned):**
  - leave gap rows with no visible neighbour as `gap_imputed`, or route them through an explicit fallback;
  - then either limit the learned odd fill to the scored years (≤2005) or state the extrapolation in the docstring and the registration;
  - add a seam case to the test.

**2. Medium — the nearest-donor cache is keyed by `id(self)`, not by content** (`epuf_fill.py:1212-1220`)
- **What goes wrong:** the cache key includes `str((id(self), self.k))`. CPython reuses addresses, so if one `PreDonorFill` is garbage-collected and another with a different bank but the same `k` lands at the same address, the same inputs hit the cache. That returns the old bank's donor indices for the new bank: wrong blocks, or an index out of range.
- **Registered path:** not affected, because the fills are loaded once and stay alive.
- **Fix:** key on a digest of `bank_match`, `bank_sex`, `bank_birth_year` and `k`, computed once. Add a test with two fills fitted on different banks.

**3. Medium-low — the fit script overwrites the registered files before it refuses** (`scripts/fit_epuf_fills.py:178-179, 207`)
- **What goes wrong:** `path.write_bytes(blob)` replaces `~/…/fills/{name}_v1.npz` unconditionally. `write_new` only refuses an existing manifest at the very end. The manifest's note invites a refit to reproduce the bytes; doing that at a different commit or in a different environment would destroy the staged registered files, and only then fail.
- **Fix:** check that the manifest does not exist before fitting. Write each file with `open(path, "xb")`, or write to a temporary path and compare against the existing file.

**4. Low — tree thresholds are stored as float32, so traversal can differ from scikit-learn's** (`epuf_fill.py:531, 544, 822, 840`)
- **What goes wrong:** scikit-learn's threshold is a float64 midpoint of two float32 values, compared as `float64(x) <= thr`. Casting that midpoint to float32 rounds half-to-even when the two values are one ulp apart, which can give `Xf[p]`. Then `x == Xf[p]` goes left here and right in scikit-learn.
- **Effect:** the stored model is self-consistent, since the fit and the draws use the same traversal. But leaf membership can differ from `estimator.apply`, and an empty leaf makes `_value` (`:636`) read `leaf_values[start-1]`, the neighbouring leaf's value.
- **Tests:** no test compares the traversal with `apply`.
- **Fix:** add a test asserting every leaf has a count of at least 1 and that `_tree_leaves` matches `apply`. Keeping the thresholds in float64 would change the artifacts' bytes, so do that only if you re-register.

**5. Low — persons of uncoded sex get no copula** (`epuf_fill.py:678`, `:1601-1604`)
- **What goes wrong:** `BySexFill` sends sex 3 to the men's part. That part looks up `rho[3, band]`, which is 0.0 because calibration only sets the row of its own sex (manifest: the men's part has `rho` rows 0, 2 and 3 all zero). So these persons' masked years are drawn independently.
- **Fix:** in `BySexFill.fill`, pass `sex = value` for the rows it routes there.

**6. Low — "byte-reproducible" depends on the environment** (`epuf_fill.py:184-206`, `fit_epuf_fills.py:197-201`)
- **What goes wrong:** the deflate output depends on the zlib build (for example zlib against zlib-ng), and `ZipInfo.create_system` depends on the platform. The manifest records the numpy, scipy and scikit-learn versions, but not the Python version, the zlib runtime version or the platform.
- **Fix:** record `zlib.ZLIB_RUNTIME_VERSION`, the Python version and the platform, or use `ZIP_STORED`. Qualify the reproducibility claim in the registration document.

**7. Low — provenance gaps in what the scripts record** (`scripts/score_epuf_fill_test.py:59-81`, `fit_epuf_fills.py:43-46`)
- **Score script:**
  - It refuses before lock (through `test_part`, `epuf_fill_gate.py:1450-1453`) and refuses an existing output — both fine.
  - But it accepts any `--manifest` and only records that manifest's SHA. Pin the registered `8d42153…` and refuse others.
  - It does not record whether the working tree was clean. Record that, as the fit script does.
  - It writes an absolute local path (including the home directory) into a JSON file that will be published.
  - If the run crashes after the TEST read, nothing is written. Consider writing a "started" record first.
- **Fit script:** `CODE_FILES` leaves out `harness/epuf_fill_gate.py` and `harness/epuf_operator.py`, which the fit depends on (TRAIN split, `YEARS`, `wage_base`). So the "code unchanged" test does not cover them.

**8. Nits**
- `PreDonorFill`'s class docstring is stale (`epuf_fill.py:1124-1136`). It says 2,000 donors, `k` of 10, five match years and "scaled by five". The code matches on `MATCH_DIMS = 7`, and the registered fill uses a bank of 100,000 and `k` of 3.
- `start_year` in `fill_careers` is really the *last* year (`psid2010_epuf_fill.py:87, 99`). If it is set below 2013, later gap rows silently keep the assembler's value.
- `bank_block` is cast to `uint16` without clipping (`:1200`). A share above 1 would wrap. EPUF is capped so it is safe today, but the forest clips and this should too.
- `ok` in `PreChainFill.fill` is always True (`:1497`).
- For PSID recipients, `match_vector`'s career summaries (`:1080`) cover years past 2006, while the bank's stop at 2006. Consider limiting them to ≤2006.
- `test_the_forest_copula_is_calibrated_by_band` only checks shape and range. Assert that the coded-sex row of each part is nonzero.
- The `n_units` registered as 3,000,000 applies per sex: the diagnostics show 3M for each part. Say so in the registration document.

## What I verified (by reading)

- **Leakage:**
  - `fit_epuf_fills` reads only `epuf_matrix(TRAIN)`.
  - The copula's calibration persons are TRAIN persons held out of the forests.
  - Every fill reads only cells it is allowed to read: `known = isfinite & ~mask`, or the masked cells set to NaN.
  - The scoring path hides the union mask (`epuf_fill_gate.py:1151-1153`).
  - The forest's training contexts exclude pre-career years.
- **`hash_uniform`:** keyed by stream, seed, person and year; values strictly inside (0, 1); broadcasting is correct.
- **The draws:**
  - The forest: zero below `p0`, otherwise the rescaled quantile; one `eta` per person; one `epsilon` per unit; a separate uniform picks the tree.
  - kNN and the chain: draws do not depend on the persons' order.
  - The donor draw: each group's donors are stored contiguously, so the fallback random donor is correct.
- **Loading:** `load_fill` checks the SHA-256 before parsing, and nested `BySexFill` files round-trip.
- **`fill_careers`:**
  - observed rows are untouched;
  - gap rows are relabelled `gap_epuf_drawn`;
  - pre-career rows are only added (`pre_mask & ~in_career`) as `pre_career_epuf_donor`;
  - shares are converted to dollars at each year's base;
  - wage bases past 2006 come from the captured step function (`ss/params.py:151-160`).
- **Birth-evidence reducer:** both new modules are excluded in `scripts/first_estimates_birth_evidence.py:358-361`, with the reachability assertions in `tests/estimates/test_birth_evidence_artifact.py:217-220, 476-482`.
- **Claims:**
  - The registration document's SHAs, sizes, library versions and `code_commit` match `runs/epuf_fill_candidates_v1.json`.
  - The manifest SHA `8d42153…` matches the one in the DEV dry-run log (line 17).
  - The dry run's tier counts match the document's tables: odd primary 7 of 183 failing ("improves"), odd alternative 46, current odd rule 100 and 99; pre primary 0 of 136 ("certified"), pre alternative 50, current pre rule 131.