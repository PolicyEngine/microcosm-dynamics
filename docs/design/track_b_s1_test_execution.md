# S1 test execution disclosure

The frozen declaration is `docs/design/track_b_s1_tests.md`, SHA-256
`1c4593da34a9d760e63bb7f3336566779ed45329fd7d6a3a3d9ef4f69211fe8f`.
That hash was announced before T3 and T6 ran. The declaration and its
criteria remain unchanged. This document discloses an execution change in
how T3 and T6 reached the production participation gates.

## Initial full-refit failure

As reported in the revision request, the first build ran the declared T3
and T6 panels through the full earnings refit before any statistical
evaluation. The full fitter
`forward_earnings.fit_forward_earnings` calls `_fit_u_w` after fitting age
marginals and before fitting either participation gate. `_fit_u_w` calls
`_pooled_autocovariances`, whose non-finite autocovariance guard at
`src/populace_dynamics/engine/forward_earnings.py:620` raises:

```text
ValueError: u_w fit needs positive observations at every 0--10 year lag
```

The permanent-score estimator requires positive same-person earnings
observations at all six biennial lags from zero through ten years. The
declared panels supply independent two-year episodes plus separate 2020
anchors; they supply no positive same-person pairs at four, six, or eight
years. Their permanent-score fit cannot form those autocovariances. This
failure precedes gate fitting, probability evaluation, Monte Carlo draws,
and expected Brier-loss evaluation, so it yielded no T3 or T6 statistical
result.

This revision reproduced the same failure through both v1's and S1's
`refit_earnings_chained_generator` entry points on each declared panel.
The reproduction corroborates the reported failure; it does not supply
an original first-build execution log. Positive-observation counts at
zero lag and pair counts at the remaining lags in the reproduction were:

| Panel | 0 years | 2 years | 4 years | 6 years | 8 years | 10 years |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T3 | 30,048 | 8,915 | 0 | 0 | 0 | 1,222 |
| T6 | 27,706 | 6,621 | 0 | 0 | 0 | 1,612 |

## Disclosed execution change

T3 and T6 then ran on the production gate-fitting component, as implemented
by `_fit_gates` in `tests/test_track_b_s1_experiments.py`. This component
uses the production forward-pair builder, the pinned default QRF factory,
the unchanged production fitting keywords and, for S1, its production
`_GateFittingModel`. It fits the shared gate and the zero-boundary-anchor
gate without requiring a permanent-score fit.

Both declared panels retain 19,200 people, 57,600 rows, 19,200 forward
pairs, and 9,600 zero-anchor forward pairs. Panel definitions, boundary,
NAWI, weights, query grids, seeds, estimator defaults, and pass criteria
were unchanged. T3 uses data seed 7301, fit seed 7311, and Monte Carlo seeds
7321 and 7322, with 20,000 draws per cell. T6 uses data seed 7401 and fit
seed 7411. Neither experiment adds positive-history rows or alters the
declaration to make the full fitter succeed.

This is a disclosed execution change: T3 and T6 establish results for the
participation-gate component on the declared invented panels. They do not
establish successful complete refits of those panels. T4 separately checks
the full refit on an invented history with the required positive-history
support.

## Observed results

The revised-build T3 rerun produced:

| Gate | Maximum absolute probability error | Probability RMSE | Maximum absolute draw-frequency error |
| --- | ---: | ---: | ---: |
| Shared | 0.04775595813426481 | 0.019912773651345424 | 0.04635 |
| Zero anchor | 0.06666885700108316 | 0.026132065104395853 | 0.06695000000000007 |

The aggregate probability RMSE across all 64 cells was
0.023231480593260734. The maximum probability error was
0.06666885700108316 against the declared 0.15 ceiling; aggregate RMSE was
below 0.075; and the maximum draw-frequency error was
0.06695000000000007 against the declared ceiling
`0.15 + sqrt(log(2*64/0.001)/(2*20000))` (approximately 0.16715). All three
T3 criteria passed.

The revised-build T6 rerun produced the following population expected
Brier losses on the 64 equally weighted query cells:

| Quantity | Observed value |
| --- | ---: |
| v1 expected Brier loss | 0.12806565307694395 |
| S1 expected Brier loss | 0.3778389611618991 |
| S1 minus v1 | 0.24977330808495513 |
| S1 divided by v1 | 2.950353604450736 |

The excess loss exceeded the unchanged 0.05 criterion, so the nominal-law
counterexample passed. These measurements concern the declared invented
processes and do not establish a law for observed people.

Both experiment tests passed in the serial rerun. Its exact command was:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-s1/bin/python -u -m pytest -p no:cacheprovider -q -s --basetemp=/private/tmp/s1-revised-experiments-serial tests/test_track_b_s1_experiments.py
```

Final line:

```text
2 passed in 90.68s (0:01:30)
```
