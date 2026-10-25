# S1: frozen specification (d1803)

Max ruled d1803 on 2026-10-21: develop **S1**, the wage-relative participation gate, with P2 in reserve, on invented data only, with no PSID read. The text below is copied verbatim from the successor memo (`trackb-b2-successor-20261018/DESIGN.md`, sha256 `ebaeda29dbf74813d16800d5c19519d312d710fa60c4f8041169178733938f76`), sections "The defect, and the hypothesis S1 tests" (code facts and hypothesis only) and "Development, if approved". Nothing in it may change during development; a change is a new specification, recorded as such.

## The defect, and the hypothesis S1 tests

**What the code shows.**
- Candidate 3 decides whether a person has positive earnings at t+2 with two gradient-boosted classifiers.
  - Both are fitted on `["earnings", "age_tp2"]` (`src/populace_dynamics/engine/forward_earnings.py:1074-1091`; the classifier is in pinned `populace/fit/qrf.py:219-227`).
  - The earnings input is **nominal** labor income, with no calendar-year predictor. The training pairs are same-person t,t+2 pairs through the boundary, at ages 25-64, with positive weights, from people observed at the boundary.
  - For a 2010 boundary, the permitted years are 1968-2010. The support actually retained was not inspected.
- At projection the gates are queried with nominal `current_level` (`:1780-1803`), and gate assignment is fixed by the person's 2010 zero-earnings status.
  - Positive draws are scaled by the projected wage index (`:1470-1485`).
  - Odd years carry earnings unchanged (`:1694-1717`).
- These components of the law are NAWI-normalized:
  - the positive-earnings age marginals (`:496-503`);
  - the donor ranks and permanent-score inputs (`:536-546`, `:702-723`, `:780-805`);
  - the dispatch between historical and projected normalization (`:422-432`).
- The participation gate is not.

**The hypothesis.**
- If participation depends on earnings *relative to* the wage level, a gate pooled over four decades in nominal dollars mixes eras. Projection then moves people along the nominal axis as wages grow, even when their relative position is unchanged. S1 assumes that conditional stationarity.
- The code establishes the inconsistency. **It does not establish that participation depends on relative rather than nominal earnings.** The GPT-6.1 Sol proposer calls this "a conditional-stationarity hypothesis, not a demonstrated empirical error".
- **Choosing NAWI as the scale is a substantive restriction,** even though S1 adds no fitted parameter. If participation really responds to a fixed nominal threshold, S1 can do worse than v1. That is the counterexample S1's tests must include.

## Development, if approved

**The build.** A PR adding a new candidate ID and versioned module. `m6_candidate3_engine_v1` and the protected engine files do not change.

**S1's transformation, frozen now:**
- **Fitting.** For each historical source year t, the gate's earnings predictor is `Y_t / NAWI_t`, using realized NAWI. This happens only on a separate gate-fitting view.
- **Unchanged.** The raw targets, sign labels (the pinned classifier's 1e-6 zero tolerance on the raw target), weights, estimator settings and donor inputs.
- **Querying.** At an even projection year y, carried earnings belong to y−2, so the query divides by `wage_index.normalization_index(y − 2)`. That is realized boundary NAWI at the first step, and the origin-frozen projected index after it, never later realized NAWI.
- **Consistency.** Both query paths and the feature signatures are updated to match.
- **Fixed form.** The transformation is the simple ratio: no log, clipping, other deflator or search.

**Tests**, on invented panels only, each with a mutation check. Exact invariants are kept separate from recovery experiments.

| Test | Kind | What it checks |
|---|---|---|
| T1 | Exact | With NAWI equal to one throughout, S1's gate features, probabilities and draws equal v1's |
| T2 | Exact, scoped | Under a period-specific rescaling of historical earnings and NAWI, with factors that are powers of two and target earnings kept away from the 1e-6 tolerance, S1's transformed gate features and gate probabilities are unchanged. Not the full law: the wage path is refitted by trailing-decade OLS |
| T3 | Recovery | On a process stationary in relative terms with nominal wage growth, S1 recovers the conditional participation probabilities. The statistical criteria, with fitting and Monte Carlo error, are declared before the run |
| T4 | Exact, scoped | The fitted objects outside the gate (marginals, permanent scores, donor pools, wage index) and their fixed conditioning inputs equal v1's. Generated ranks and donor choices may differ once participation histories differ |
| T5 | Exact | Changing inputs after the boundary changes neither the fit nor the draws |
| T6 | Counterexample | Participation driven by a fixed nominal threshold. S1 is expected to do worse, and the size of that loss is reported |
| T7 | Exact | On a panel with NAWI growth, the first-step query features equal Y_b/NAWI_b, and later queries divide by `normalization_index(y − 2)`. Restarting a projection reproduces it exactly. Its mutation check swaps y − 2 for y |

No PSID data is read in development.
