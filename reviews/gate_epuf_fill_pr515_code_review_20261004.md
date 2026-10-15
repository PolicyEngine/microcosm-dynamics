**Verdict: APPROVE WITH NITS.** This is provisional: several checks you asked for need `git` and `pytest`, and this session only had file read, search and web fetch tools. Those checks are listed under "Not verified" with the exact commands.

I found no correctness bugs in the gate rules, the scripts or the TEST guard. The proposal's v3 numbers match the artifact. The findings are about provenance and test strength.

## Findings

1. **Medium: a run with injected inputs produces the same record as the registered run.** `src/populace_dynamics/harness/epuf_fill_scoring.py:181-182, 197-223`
   - **Evidence:**
     - When `fills=` is passed, the loader is skipped (`:198-200`), so no candidate's SHA-256 is checked. The record still writes each spec's `path` and `sha256` under `"candidates"` as if they had been loaded.
     - When `matrix=` is passed, `test_part` and the lock check are skipped. The record still carries `registration_id`.
     - Nothing in the output says either input was injected. A test-style run cannot be told apart from the one registered TEST scoring.
     - `epuf_fill.load_fill(..., sha256=None)` also skips its hash check silently (`estimates/epuf_fill.py:1657`), so a spec with a `None` hash goes through unverified.
   - **Fix:**
     - Add `"injected": {"matrix": matrix_given, "fills": fills_given}` to the record, or leave out `registration_id` when either is set.
     - Refuse a spec whose SHA-256 is `None` or not 64 hex characters.
   - This should land before the TEST run; it does not need to block the merge.

2. **Low: #515's TEST entry point imports a module that, by every sign, first appears in #516.** `epuf_fill_scoring.py:201`
   - **Evidence:**
     - `populace_dynamics.estimates.epuf_fill` is imported lazily.
     - The proposal (§8) says the candidate fills "will live in a new opt-in module".
     - Its exclusion lines (`scripts/first_estimates_birth_evidence.py:358-361`) sit in a separate block whose comment matches #516's commit message.
     - `test_registered_candidates_are_hash_checked` uses `importorskip`, so on #515 alone that test is skipped.
   - **Effect:** at `70553e70`, calling `score_registered` without `fills` raises `ModuleNotFoundError`.
   - **Fix:** say in #515's description that #516 must merge before the TEST run. Confirm with `git show 70553e70:src/populace_dynamics/estimates/epuf_fill.py`.

3. **Low: `test_registered_candidates_are_hash_checked` never reaches a hash check.** `tests/harness/test_epuf_fill_scoring.py:150-159`
   - **Evidence:** it points at a file that does not exist and accepts `FileNotFoundError`. `load_fill` reads the bytes before it compares hashes, so the mismatch branch never runs.
   - **Fix:** write a real file and pass a wrong SHA-256. Expect `ValueError` matching `"SHA-256"`, and drop `FileNotFoundError` from the accepted errors.

4. **Low: nothing tests round 3's "smaller of the two readings" rule end to end.** `tests/harness/test_epuf_fill_scoring.py:72-117`
   - **Evidence:**
     - The tolerance is 10 and the chosen cells all have finite gaps, so every score passes.
     - `primary.n_failing == fallback.n_failing` is therefore just `0 == 0`.
     - The `two_sided` reading never changes a tier.
     - `test_combined_current_takes_the_smaller_gap_per_cell` tests only the helper.
   - **Fix:** add a case where `fallback` and `two_sided` differ in a gating cell (young-band `level`, at a tight tolerance). Assert that `adoption_tier(candidate, combined_current(...))` returns `improves` where the fallback reading alone would give `not_adopted`. Also compare gaps cell by cell, not only failing counts.

5. **Nit: the odd-oracle test does not check what its name says.** `tests/harness/test_epuf_fill_gate.py:383-396`
   - **Evidence:**
     - The test checks only that each column keeps the same set of values. Nothing checks that values move only within a stratum.
     - The last assertion, `filled >= 0`, is always true, and its comment describes a different property.
   - **Fix:** check that each moved value's source row has the same oracle key.

6. **Nit: a malformed `gates.yaml` raises the wrong error.** `epuf_fill_gate.py:1424-1433`
   - **Evidence:** an empty file, or `thresholds` that is not a mapping, raises `AttributeError` instead of `TestPartLocked`. TEST still stays unread, so this only affects the error message.
   - **Fix:** use `document = yaml.safe_load(...) or {}` and guard with `isinstance` checks.

7. **Nit: the tolerance table in the proposal rounds a few bounds inconsistently.** `docs/amendments/gate_epuf_fill_registration_proposal.md:541-549`
   - **Evidence:**
     - The `q50` upper bound is 0.074465 in the artifact; the table says 0.075.
     - The `pzero` upper bound is 0.128484; the table says 0.129.
     - The `r1` lower bound is 0.002476; the table says 0.0025.
   - **Fix:** round to nearest throughout.

8. **Nit: the D-series count hardcodes the bite multiple.** `scripts/build_epuf_fill_gate_floors.py:228`
   - **Evidence:** `n_beyond_two` uses the literal `2` instead of `g.BITE_MULTIPLE`. The output does not change, because the constant is 2.0.

## What I verified (by reading the code and the committed JSON)

- **Rules module:**
  - **Masks and current rules:**
    - `family_mask("odd")` is the odd years minus pre-career years.
    - `CurrentOddFill` falls back to the one known neighbour at age 22, with no out-of-range neighbour (2005 + 1 = 2006).
  - **Universes and units:**
    - Each universe reads no cell its own family fills, so group membership does not change when a fill is scored.
    - Band units start at age 22, so every unit is a cell the odd family owns.
  - **Year indexing:**
    - `yr_cross` indexes stay within 1967–2004.
    - `pr_in` compares two masked years and `pr_cross` a masked year with a recorded one, for 1930–1945.
    - `r3` drops 2008.
  - **Scoring path:**
    - `score_candidate` refuses non-finite values, values outside [0, 1], and writes to cells the fill does not own, including the other family's cells.
    - A share of 1 becomes exactly the wage base.
  - **Partition and adoption:** the partition checks its reasons in the documented order, and `adoption_tier` and `adopt` match §7.3.
  - **Oracles:** the permutation keys cannot collide, and `_permute_within` is correct.
  - **TEST guard:** `epuf_matrix` refuses both `TEST` and `None` without the token. `test_part` needs both `locked` flags and the registration id.
  - **Join checks:** the EPUF join assertions and the `pair` encoding (offset under 100) are sound.
- **Scoring module:**
  - Undefined gating cells are dropped from the candidates' scores and both current-rule readings alike.
  - `combined_current` takes the smaller gap and the smaller failing count, as round 3 specified.
  - `_ROOT` and `parents[3]` resolve to the repository root.
- **Scripts:**
  - The age-band sample size counts units the same way the cells do.
  - Each perturbation and oracle replaces only its own family's cells.
  - `registered_build` is true only for a DEV build with 200 replicates and all oracle seeds.
  - The build records whether the bound files were clean.
- **Exclusions:** both new `src/` modules appear in `POST_REVIEW_SOURCE_EXCLUSIONS` (`:356-357`). The exact-tuple test and the reachability test both list them (`test_birth_evidence_artifact.py:217-218, 476-477`).
- **Claims against `runs/epuf_fill_gate_floors_v3.json`:**
  - **Build and partition:**
    - The build ran at `cb76ad15` with clean bound files.
    - 319 of 326 cells gate (183 odd, 136 pre), and the 7 report-only cells and their reasons match §10a.
    - Men's `q90` is exactly 1 in the 22–74, 30–44, 45–59 and 60–74 bands.
  - **Checks on bite and perturbations:**
    - The bite checks fail 96/183 and 112/136 cells by more than two tolerances.
    - B2's pooled median-AIME falls work out to 5.3 and 4.0 tolerances.
    - D1–D6 failing and beyond-two counts all match.
    - The doses match: λ ≈ 0.9965 at `odd.men.a22_74.q90`; 12.5% at `paime_p90`; 1.4% at `ylevel`; 13.5% at `paime_p25`.
  - **Oracles:** O1 fails 32/183 and O2 fails 6/136.
  - **Ranges:** the noise ratio runs 0.087–0.212. All tolerance ranges match apart from finding 7. `pre.women.b1930_1934.aime_p10` is 0.391, and the pooled p10 tolerances are about 0.17.
- **Expected tier-count change from static counting** (the conftest rules classify by path and source):
  - `test_epuf_fill_gate.py`: 47 tests, unit tier.
  - `test_epuf_fill_scoring.py`: 6 tests, unit tier.
  - `test_epuf_fill_gate_floors.py`: 27 tests, artifact tier (it names `"runs"` and `.json`). That is 21 tests run once for each of 3 builds, plus 6 that run only on the registered build.
  - If all three files are new in #515, expect +53 unit and +27 artifact.
- **CI history:** CI checks out with `fetch-depth: 0`, so `test_registered_build_is_bound_to_its_rules` really runs there rather than skipping.

## Not verified (needs `git` or `pytest`)

```
git diff --stat 5129ac32 70553e70
git diff --name-only 5129ac32 70553e70 -- src/populace_dynamics/estimates/career.py   # expect empty
git diff --diff-filter=M --name-only 5129ac32 70553e70 -- 'runs/*.json'               # expect empty
git diff 5129ac32 70553e70 -- tests/tier_counts.json                                  # expect unit +53, artifact +27
git diff --name-only cb76ad15 70553e70 -- src/populace_dynamics/harness/epuf_fill_gate.py src/populace_dynamics/harness/epuf_cells.py src/populace_dynamics/harness/epuf_operator.py scripts/build_epuf_fill_gate_floors.py scripts/build_epuf_fill_psid_scale.py   # expect empty, or the bound-file test fails
git show 70553e70:src/populace_dynamics/estimates/epuf_fill.py                         # finding 2
PYTHONPATH=src .venv/bin/python -m pytest tests/harness/test_epuf_fill_gate.py tests/harness/test_epuf_fill_scoring.py tests/test_epuf_fill_gate_floors.py tests/estimates/test_birth_evidence_artifact.py -q -p no:cacheprovider
```

- **CI shard 1:** I could not confirm that the inherited depletion-cut pin is the only failure. The PR checks page did not load its results, and `gh` was not available.
- **Sealed files:** the proposal (§8) says `career.py` stays byte-identical, but I could not diff it.
- **Bound files:** nothing in `epuf_fill_gate.py` mentions round 3, which suggests it is unchanged since `cb76ad15`. Only the diff above can confirm it.