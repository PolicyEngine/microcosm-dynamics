# S1 invented-data test declaration

Declared before running T3 or T6. This document's criteria are frozen for
this development run. The sole law specification is `track_b_s1_spec.md`;
this declaration does not amend it. No survey observations or gate outcomes
inform these tests.

## Exact invariants

The common invented history has 64 people, eight people at each of the eight
five-year age bins (ages 27, 32, ..., 62), observed biennially from 1988 through
the 2000 boundary. Positive earnings are a power-of-two relative level times
invented NAWI; a periodic person/wave pattern supplies zeros. Positive integer
weights vary by person. Hypothesis varies seeds, level scales, rescaling
factors, projection modes, or future contamination as applicable. Exact
comparisons use array/frame equality, not statistical tolerances. The pinned
QRF's default factory is used unless a recording factory is needed to inspect
the exact fitting inputs; such a factory delegates to the pinned QRF.

* **T1:** With every historical and projected NAWI equal to one, compare v1
  and S1 fitting feature arrays, fitted gate probabilities, and generated
  earnings/state arrays using identical seeds. Exercise both the ordinary
  generation method and the correlated frame-update method, both boundary
  anchor groups, and odd-year carries. Hypothesis varies the invented history
  and draw seeds.
* **T2 (scoped):** Multiply each historical period's raw earnings and NAWI by
  the same independently chosen power of two (exponents -4 through 4).
  Nonzero targets remain well above 1e-6. Compare S1's transformed features
  and fitted gate probabilities exactly, including both anchor groups. Do
  not assert full-law or wage-OLS invariance. Hypothesis varies period factors.
* **T4 (scoped):** Fit v1 and S1 to the same growth history. Compare raw
  estimation rows, raw forward pairs, anchors, targets, target sign labels,
  weights, fit keywords/seeds/default estimator settings, age marginals,
  permanent-score maps and diagnostics, donor pools, stable pools and audits,
  wage index, realized-history maps, and initial fixed conditioning frame.
  Only the earnings column in the separate gate-fitting copy may differ.
  Include raw targets on both sides of the pinned 1e-6 tolerance in a
  separate check. Hypothesis varies the invented history. Generated ranks
  and donor choices are outside this invariant after participation differs.
* **T5:** Append/alter invented post-boundary panel rows and change only
  post-boundary NAWI entries. Compare all fitting surfaces, signatures and
  draws exactly. Hypothesis varies future earnings and future NAWI values,
  including several projection years and both query methods.
* **T7:** On the growth history, record the actual features reaching both
  gates through each generation method. At the first even step assert
  earnings/realized-boundary-NAWI; at later even steps assert earnings divided
  by the origin-frozen `normalization_index(y - 2)`. Supply conflicting later
  realized NAWI to distinguish it from the projected index. Preserve the
  boundary-zero gate assignment even after current participation changes.
  Check odd-year carry and serialize/restore the fitted generator, frame and
  RNG mid-projection, then require identical remaining earnings, state and
  RNG position. Hypothesis varies seeds, order, modes and horizons. Its
  production mutation replaces `y - 2` by `y`.

Feature-signature checks independently reconstruct canonical gate surfaces
from the transformed full forward-pair view and require S1's signature to
include them. Registry/refit tests check that S1 dispatches explicitly and
that candidate 3 retains its registered hash and v1 generator class.

## T3: conditional recovery experiment

Boundary: 2020. Invented realized NAWI is `2**((t - 2000)/2)` for each year
1998 through 2020. There are three independent episode eras, with source
years 2000, 2004 and 2008. Each person has a source row, a row two years later,
and a separate boundary anchor; no other adjacent pairs are introduced.
Source ages are `25 + 5*b` for the eight age bins; target and anchor ages
advance by elapsed years. Source relative earnings are `[0, .5, 1, 2]`, with
true conditional participation probabilities `[.15, .35, .65, .85]`.
Targets are independent Bernoulli draws times target-year NAWI, so all
nonzero targets are above 1e-6. Equal weights and independently balanced
positive/zero boundary anchor groups give 100 replications per
era/age/level/anchor-status cell: 19,200 people, 57,600 rows and 19,200 pairs.
The data seed is 7301 and fit seed is 7311. Production's pinned default QRF
estimator settings are used unchanged.

Evaluate each of the two gates at four relative levels and eight target
ages (64 cells in total). Pass criteria, declared before the run:

1. Every absolute fitted probability error is at most .15.
2. The root mean squared probability error across all 64 cells is at most
   .075.
3. For each cell, use 20,000 fresh uniform draws, with seed 7321 for the
   shared gate and 7322 for the zero-anchor gate. The absolute positive-draw
   frequency error from the true probability is at most
   `.15 + sqrt(log(2*64/.001)/(2*20000))` (approximately .1672).

The .15 cellwise fitting allowance admits finite training-sample error and
the default histogram boosting approximation. The .075 aggregate requirement
limits systematic fitting error. The additional Hoeffding allowance controls
the union probability of Monte Carlo error beyond the fitted probabilities
at .001 across the 64 cells. Report the observed maximum probability error,
RMSE, maximum draw-frequency error, and the declared thresholds. This is an
invented-process recovery experiment, not a statement about observed people.

## T6: fixed nominal threshold counterexample

Use the same episode structure, sizes, NAWI, ages, weights, relative source
levels and independent boundary-anchor assignment as T3. Replace the true
participation law by .15 when source nominal earnings are below 8 and .85
when source nominal earnings are at least 8. Use data seed 7401 and fit seed
7411. Fit both v1 and S1 using unchanged pinned QRF defaults.

Evaluate a uniformly weighted held-out nominal query grid `[2, 4, 8, 16]`
at source year 2020 across eight target ages and both gates (64 cells).
S1 queries use nominal earnings divided by the source-year normalization
index; v1 uses nominal earnings. Measure loss as population expected Brier
loss, `mean(p*(1-p) + (q-p)**2)`, where p is the known nominal-law probability
and q the fitted participation probability. Report v1's loss, S1's loss,
the absolute excess `S1 - v1`, and their ratio. The counterexample passes
when S1's excess is greater than .05. This deterministic conditional
expectation avoids a further held-out Bernoulli sampling error.

## Mutation protocol

For each T1-T7, replace one production line, run its targeted test and
require a test failure, then restore the original bytes before proceeding.
Record exact replacement text, command, exit status, failed node IDs and
restored SHA-256 in `track_b_s1_mutations.json`. No criterion above may be
changed after its SHA-256 is announced and T3/T6 are run. An unworkable
criterion must be reported unchanged.
