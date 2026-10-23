# P2 source and preservation audit

This audit reads `track_b_p2_spec.md` together with amendment 1. The
specification is unchanged. The amendment replaces only T4's executable
reference. All data constructed for this audit are invented.

## Candidate 3 law and refit path

`engine/candidates.py:140` declares candidate 3 by inheriting candidate 2's
rank-refresh operation (`:122`) and adding correlated refresh. The payloads
are `q=0.55`, substreams 4 and 5, and `rho=-0.60`. Candidate identity resolves
through `harness/m6_candidate3_runner.py:460`; `_fit_candidate3` passes that
explicit engine spec to `refit_m6_components` (`:1417`). The latter calls
`refit_earnings_chained_generator` (`engine/refit.py:1153`), which calls
`fit_forward_earnings` (`:799`) and returns its generator, estimation
surfaces, provenance, candidate hash, fit signature and refresh audit.

The forward fitter builds the admitted panel, two gates, wage index,
marginals, permanent scores and donor pools. Initialization materializes
boundary earnings plus the exact preceding biennial observation. Odd years
carry earnings. Even years draw participation, choose re-entry/pair/triple
donors, optionally refresh ranks, and map ranks through the inherited
nominal marginal. Both v1 generation interfaces use immutable zero-anchor
routing for participation. `steps.apply_earnings` supplies person-addressed
streams and rolls the biennial fields after the draw.

The existing refit entry point directly calls the imported v1 fitter and
records v1's two-feature adapter specification. It cannot be reused for P2
without changing existing source or patching globals. P2 therefore needs
its own orchestration and provenance entry point, as section 6 requires.

## Verification of code citations in frozen sections 1–6

All `engine/` paths below mean `src/populace_dynamics/engine/`. Each cited
range was read in the assigned worktree. No mismatch or unimplementable
requirement was found. Report references beginning `p1-`, `p2-`, `p3-`,
`p4-`, or `trackb-design-` are frozen design provenance, not source-code
citations; no external review checkout or linked outside-workspace file was
opened.

| Frozen point | Verified source and meaning |
|---|---|
| Sections 1–2: existing predictor scale and available older state | `forward_earnings.py:1074–1080` passes raw nominal earnings and target age; `:1733–1737` and `:1916–1922` separately read current, two-year and four-year earnings fields. |
| Section 3: exact pairs and boundary-person restriction | `forward_earnings.py:562–589` joins each person at exactly two years; `:1021–1035` creates the positive-weight pre-boundary panel before age restriction; `:1067–1068` retains boundary-observed persons. |
| Section 3: initialization | `forward_earnings.py:1111–1117` makes the prior map from the unfiltered cutoff panel; `:1437–1463` initializes current earnings and `gen_earn_w2` from boundary earnings and `gen_earn_w4` from the prior map, leaving unavailable history NaN. |
| Section 3: clock | `steps.py:337–355` copies pre-draw `gen_earn_w2` to `gen_earn_w4` only in even years and stores the generated level in `gen_earn_w2`. |
| Section 4: invalid and later-missing state | `forward_earnings.py:1753–1771` rejects negative/infinite older state and NaN from the second even step onward; the non-correlated interface has the same validation at `:1936–1954`. |
| Section 4: upstream unavailable records | `scripts/select_m6_qstar_train_only.py:449–485` filters present-person sequences, inner-merges family records, selects head/spouse relationships, assigns labor earnings and applies exactly `earnings < family._MISSING` and `weight > 0`. Reading this code invokes no reader. |
| Section 4: supported domain | `earnings_domain.py:71–87` forms the realized-state/permanent-score intersection; `:161–208` initializes supported persons, sets other persons' earnings to zero and leaves their chain fields unavailable. `steps.py:330–336` preserves unavailable chain fields outside the domain. |
| Section 5: removed gate fit and routing | `forward_earnings.py:1081–1091` fits the zero-anchor subset; `:1783–1803` and `:1964–1984` route anchors to different gates. These are the P2-specific blocks to replace in its sibling module. |
| Section 5: retained q0 and anchor coordinates | `forward_earnings.py:1780–1782` defines exact zero-anchor `q0`; `:1509–1533` constructs boundary ranks and uses `u_A` for zero anchors, otherwise `.1*u_w+.9*u_A`; `:1841–1876` retains q0-dependent donor and refresh behavior. |
| Section 5: pair population and weights | `forward_earnings.py:1021–1035`, `:1055–1072` implement cutoff, positive weights, ages 25–64 and boundary-observed pairs; `:1074–1080` uses `weight_tp2`; `:771–778` extracts donor target weights; `:506–527` uses observation weights for marginals. |
| Section 5: pinned estimator | `forward_earnings.py:979–987` constructs `RegimeGatedQRF(seed=seed)` only; `refit.py:77–90` records its default build and the incumbent predictors. |
| Section 5: amount forests unused by generator | `forward_earnings.py:1173–1179` reads classifier probabilities and class labels directly; generated amounts come from donor ranks and marginals, rather than those fitted amount forests. |
| Section 5: unchanged donor inputs | `forward_earnings.py:1092–1105` passes original estimation rows, raw pairs, anchors, marginals, historical wage index and permanent scores to donor construction and raw pairs to stable pools. |
| Section 5: donor law | `forward_earnings.py:73–77` defines k and coordinate weights; `:753–905` builds ordered pair, triple and re-entry arrays; `:1182–1206` implements weighted stable KNN draws; `:1527–1587` defines coordinates and transition distances; `:1829–1863` implements the branch ramp. |
| Section 5: marginals | `forward_earnings.py:64–71` defines age bins and rank clamps; `:386–406` interpolates/clamps weighted empirical positive quantiles; `:486–533` normalizes historical earnings by NAWI and fits all eight age bins. |
| Section 5: permanent scores | `forward_earnings.py:79–80` fixes autocovariance lags and rho grid; `:592–750` estimates pooled moments, NNLS components and person shrinkage. |
| Section 5: wage index | `forward_earnings.py:422–483` fits trailing-decade unweighted log-linear OLS and dispatches pre-boundary actual/post-boundary projected values; `:1038–1048` freezes the admitted index at fitting. |
| Section 5: refresh | `candidates.py:122–151` fixes q, rho, operation IDs and substream codes; `forward_earnings.py:1864–1887` carries/reset states and applies correlated refresh under inherited support. |
| Section 5: randomness and timing | `forward_earnings.py:82–88` fixes stream codes 1–5; `:1156–1158` builds addressed streams; `:1694–1717` handles odd-year carry and even-year restriction; `:1725–1731` sorts persons; `:1773–1782` creates all inherited substreams and the full gate-uniform array. |
| Section 6: owned candidate identity | `candidates.py:79–119` defines immutable candidate operations, canonical payloads and SHA-256; `:140–151` is unchanged candidate 3. A sibling candidate may reuse its exact operation payloads without entering `REGISTRY`. |
| Section 6: changed gate metadata | `forward_earnings.py:998`, `:1149` hold zero-anchor pair counts; `refit.py:814–817` records those counts in provenance. P2 must instead record no gate and zero fitted zero-anchor pairs. |
| Section 6: query contract | `forward_earnings.py:1168–1179` shows the legacy three-argument path, recorded column order, classifier class order and cumulative-`>=` selection. P2 requires its own four-column helper. |
| Section 6: signatures and unchanged components | `forward_earnings.py:1210–1259` records serialized gate state and canonical training-query probabilities sorted by person/target period; `:1281–1343` separately records raw surfaces, marginals, permanent scores, wage index, donor arrays, stable pools, diagnostics and participation gates. P2 needs its own feature/history metadata and separate non-gate checksums. |

The permitted pinned dependency was also read at
`/Users/maxghenis/PolicyEngine/_trackb-p2-dev/populace-pinned/packages/populace-fit/src/populace/fit/qrf.py`.
Its `:89` fixes `DEFAULT_ZERO_ATOL=1e-6`; `:1332–1386` records target
columns, leaves `gate=None` for positive-only support and uses strict `>`
for positive labels; `:1388–1428` fits the classifier directly with sample
weights. Its ordinary positive-only prediction (`:980–990`) has effective
participation probability one, confirming amendment 1's T4 reference.

All additional code citations in T6 and section 8 were checked too:

| Citation | Verified meaning |
|---|---|
| `engine/loop.py:203–206` | `ProjectionEngine.run` invokes the initialization hook on its starting slice. |
| `engine/forward_earnings.py:1411–1420` | Earnings initialization requires the fitted original boundary year, motivating a sibling resume adapter. |
| `engine/rng.py:61–83` | The registry preserves the `5200+draw_index` seed convention, original total-period count, original period index and module address. |
| `engine/rng.py:158–169` | Person RNG addresses use the original canonical ordinal rather than a re-sorted current subset. |
| `scripts/select_m6_qstar_train_only.py:1574–1609` | The registered earnings projection wraps the domain, materializes once, sorts state, constructs ordinals from the full anchor and uses original annual period coordinates. The frozen development fixture extends that same addressing to eight periods. |
| `engine/forward_earnings.py:1780–1803` (section 8) | Positive-anchor persons use the all-person shared gate; exact zero anchors use the zero-anchor gate when fitted. |

Amendment 1's dependency citations were checked against the permitted
pinned dependency itself: `qrf.py:134–147` detects `POSITIVE_ONLY`,
`:219–227` builds `HistGradientBoostingClassifier(random_state=seed)` with
its defaults, and `:1032–1097` retains defaults, accepts explicit weights
and column order, and derives seeded fit randomness. Its `:1360–1368`,
`:1370–1379`, `:1381–1386` and `:1427–1428` confirm the absent classifier
for positive-only support, unchanged normal amount forests, strict labels,
and direct classifier sample weights. No linked review copy was opened.

## Source guards and direct v1 snapshot

`track_b/runner.py:79–97` lists 17 baseline sources and its `:411–419`
compares source bytes. `track_b/reconstructed.py:84–87` adds
`ss/params.py` and `contract.py`. All 19 current files were read only after
confirming that their paths exist in this sparse worktree. Their bytes
equal both `2ef10532` and B1's baseline
`f10cca5457b16d12b9284d00628e7331871f23e7`.
The detailed hashes are saved at `/private/tmp/p2_guard_before.json`.
Only these present, explicitly named source paths were read through git.
The final pinned-interpreter rerun also passes, with detailed hashes saved
at `/private/tmp/p2_guard_after.json`.

An independent AST comparison of both P2 generation methods against the
incumbent also passes: after removing only P2's added older-history
validation and changed participation blocks, both method bodies are
identical, including all RNG, validation, donor and frame-update branches.
The P2-owned `_draw_participation` seam lies wholly inside that changed
participation block and directly delegates to `draw_p2_sign`.
The reproducible source-only check is `/private/tmp/p2_source_checks.py`;
it uses only present source paths and fits no model.

Routine command deviation: the first guard-byte and AST-only inspection
scripts used system `python3`. They fitted no model and read no data.
Both inspections were repeated successfully with `.venv-p2/bin/python`
and all six required thread variables. Every fitted model, projection,
formatter and linter run in this delegated audit used that pinned
interpreter and environment. This is separate from a frozen-test execution
change; no frozen procedure was substituted in this audit.

The standalone script `/private/tmp/p2_v1_equality_snapshot.py` runs the
unchanged candidate-3 refit before any P2 import. It constructs exactly the
mixed full-law fixture, with fit seed 5200, all roots 6200–6219, complete
materialized frames, full-anchor sorted ordinals and the eight original
annual period coordinates through 2008. It uses the existing domain
adapter, `PeriodContext`, RNG registry and `steps.apply_earnings`. It saves
the protocol-5 full-fit serialization and raw little-endian float64 frame
path bytes at `/private/tmp/p2_v1_equality/`. The after run repeats the same
procedure and requires direct equality of both byte strings. Hashes and
final comparison results are:

| Surface | Bytes | Before/after SHA-256 | Direct byte equality |
|---|---:|---|---|
| Complete protocol-5 candidate-3 refit | 127,346,166 | `4dfa5cb4cbb3cb414386b338ce055b0770d624dd1a18e720a45a42f5b32b2fbf` | `True` |
| Complete materialized frame paths, shape `(20,9,640,12)` | 11,059,200 | `ba1ae25b946d48a746d2cb3c6e08052f3c3b72cd84c07fda35b966da2f67b7a3` | `True` |

The unchanged v1 fit signature is
`bbe1f8c5232a767109f6a836c5d7e50239fe20ad16d8a4c659de77d00d2275ac`.
Both model commands exited zero. The after run explicitly imports P2
before fitting candidate 3; the pre-run does not import P2.

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python /private/tmp/p2_v1_equality_snapshot.py before
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python /private/tmp/p2_v1_equality_snapshot.py after
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python /private/tmp/p2_source_checks.py
git diff --exit-code 2ef10532 -- src/populace_dynamics ':(exclude)src/populace_dynamics/engine/forward_earnings_p2_v1.py'
```

The source-diff command exited zero and printed nothing. The source-only
script exited zero; its final line was:

```text
generate_with_frame_updates: inherited validation, RNG, donor and frame-update AST exactly equal after removing only P2 history validation and changed participation block
```

Both temporary Python scripts were checked with:

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m black -l 79 /private/tmp/p2_v1_equality_snapshot.py
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m ruff check /private/tmp/p2_v1_equality_snapshot.py
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m black -l 79 /private/tmp/p2_source_checks.py
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m ruff check /private/tmp/p2_source_checks.py
```

Each final Black invocation exited zero with `1 file left unchanged.`;
each final ruff invocation exited zero with `All checks passed!`.

## Audit read inventory outside src/ and tests/

Explicit reads made by this delegated source audit:

- `docs/design/track_b_p2_spec.md`
- `docs/design/track_b_p2_spec_amendment_1.md`
- `docs/design/track_b_p2_review_notes.md`
- `CLAUDE.md`
- `pyproject.toml`
- `scripts/select_m6_qstar_train_only.py` (only cited source sections)
- `scripts/registered_m6_inputs.py` (byte comparison only)
- `scripts/registered_m6_candidate2_inputs.py` (byte comparison only)
- `scripts/registered_m6_candidate3_inputs.py` (byte comparison only)
- `/Users/maxghenis/.agents/skills/gitnexus-exploring/SKILL.md`
- `/Users/maxghenis/PolicyEngine/_trackb-p2-dev/populace-pinned/packages/populace-fit/src/populace/fit/qrf.py` (only pinned implementation sections)
- `/private/tmp/p2_v1_equality_snapshot.py` (created audit script; interpreter,
  Black and ruff read it)
- `/private/tmp/p2_source_checks.py` (created source-only guard and AST script;
  interpreter, Black and ruff read it)

Files created or written outside `src/` and `tests/` by this audit, in
addition to the two temporary scripts:

- `docs/design/track_b_p2_source_audit.md`
- `/private/tmp/p2_guard_before.json`
- `/private/tmp/p2_guard_after.json`
- `/private/tmp/p2_v1_equality/before.fit.pickle`
- `/private/tmp/p2_v1_equality/before.paths.f64`
- `/private/tmp/p2_v1_equality/before.json`
- `/private/tmp/p2_v1_equality/after.json`

The after run additionally reads its own pre-run byte artifacts
`/private/tmp/p2_v1_equality/before.fit.pickle` and
`/private/tmp/p2_v1_equality/before.paths.f64`. No B2 cell result or
2012/2014 gap, survey record, prohibited checkout, prohibited evidence
directory, network source, or sparse-hidden file was read.


## P2 implementation of frozen sections 1–6

All line references in this section are to
`src/populace_dynamics/engine/forward_earnings_p2_v1.py` unless otherwise
specified. The frozen specification and amendment were not edited.

| Section | Implementation |
|---|---|
| 1: feature set and nominal scale | `:55` freezes ordered `earnings, age_tp2, prior_positive, prior_missing`; `:121` constructs float64 queries without transformation, normalization, clipping, interactions or feature selection. `:104` fits only those predictors with the unchanged seed-only factory. |
| 2: one extra biennial state | `:79` joins exactly source period minus two; `:142` reads the runtime older value from `gen_earn_w4`. Current nominal `earnings` remains separate. No other history enters participation. |
| 3: participation indicator and clock | `:69` uses strict raw `>1e-6`; `:79` left-joins many-to-one, retaining pair order. `:377` constructs cutoff before age restriction and pairs exactly as v1; `:466` constructs boundary/history maps. Inherited initialization `engine/forward_earnings.py:1411` and rolling `engine/steps.py:337` preserve the specified source/older states. |
| 4: missing/invalid history and retention | `:69` encodes valid zero `(0,0)`, positive `(1,0)`, NaN/unavailable `(0,1)` and rejects negative/infinite values with `P2_INVALID_HISTORY_VALUE`. `:608` and `:772` apply this refusal in both generator interfaces, retaining the inherited later-NaN refusal. `:79` uses pre-age-filter cutoff history. Raw pairs remain separate from the gate view; no history filter reaches donors. The inherited domain wrapper remains unchanged. |
| 5: removed and inherited components | `:448` fits one shared gate directly, with `zero_anchor_gate=None` and zero fitted zero-anchor pairs. `:636` and `:803` use it for every modeled person; q0 remains exact anchor zero in the donor/refresh blocks. `:377` reproduces fit orchestration and calls unchanged marginal, permanent-score, donor, stable-pool and wage-index helpers. The generator inherits rank/donor/refresh methods and preserves original stream creation, uniform-array length, branch order, odd carry, even updates, sorting and frame updates. Candidate operations at `:47` retain q=.55, rho=-.60 and the exact operation IDs/payloads. The source/AST and T5 audits cover every retained object enumerated in frozen section 5. |
| 6: identities, query and signatures | `:47` owns the frozen candidate/revision, built with unchanged CandidateSpec/OperationSpec and absent from REGISTRY. `:151` uses recorded classifier columns/probabilities/classes and handles the pinned no-classifier point masses; `:170` uses cumulative >= selection without the legacy draw_sign path. `:284` records candidate, seed/boundary, dependency versions/source hashes, wrapper/classifier parameters, ordered float64 feature bytes, canonical pair/history/availability/value checksums, raw labels/weights, fitted classes/probabilities and protocol-5 fitted state. `:205` separately checksums every non-gate component. `:888` and `:928` own P2 refit metadata and expose the detailed signature. `:1001` resumes materialized state with original boundary, ordinals, draw index, registry and period indices; it never initializes again. |

## Frozen tests and recovery observations

| Test | Test function(s) |
|---|---|
| T1 | `test_t1_exact_feature_table`, `test_t1_every_absent_history_reason_retains_pair`, `test_t1_weight_exclusion_and_outside_age_history`, `test_t1_invalid_history_refuses_whole_operation`, `test_t1_history_encoding_property` (Hypothesis), `test_t1_full_pair_retention_and_first_step_initialization`, `test_t1_frozen_candidate_fit_and_signature_contract`, `test_t1_exact_prior_key_order_and_many_to_one_validation` in `tests/test_forward_earnings_p2_exact.py`. |
| T2 | `test_t2_second_order_recovery_and_exact_v1_distinction` in `tests/test_forward_earnings_p2_recovery.py`. |
| T3 | `test_t3_retrospective_selection_recovery[4]`, `[8]`, `[16]` in the recovery module. |
| T4, amended | `test_t4_always_positive_direct_law_neutrality[6200..6219]` in the exact module; the test-local `_DirectAlwaysPositive` evaluator uses separately fitted v1 non-gate objects, retains the gate uniforms, and substitutes only deterministic positive signs. |
| T5 | `test_t5_exact_all_non_gate_components` in the exact module. |
| T6 | `test_t6_clock_features_interfaces_and_restart[6200..6219]`, `test_t6_no_look_ahead_fitted_state_and_complete_paths` (six independent perturbations), and `test_t6_nominal_future_baseline_structural_identity` in the exact module. |
| T7 | `test_t7_persistent_heterogeneity_counterexample` in the recovery module. |

The full-law fixture has exactly the frozen 640 persons, nine waves,
row-major PCG64 seed 20261022, amounts/ages/weights/sex, seed 5200, roots
6200–6219, original eight annual coordinates and full-anchor ordinals.
Missing-first-lag cases use the prescribed i%8 omission. Recovery uses the
frozen 32 independent 8192-person panels per scenario, estimator seeds,
65,536 fresh uniforms per probe and five scenarios. No fixtures, fitting
parameters, seeds, sample sizes, tolerances or probability criteria were
changed after results.

All 36 probability assertions pass. Every one has 32/32 absolute errors
<=.04 (required >=31); worst MAE=.007975116818856253 (limit .015);
worst absolute error=.027865645194005417 (limit .08). Every Bonferroni-36,
31-df Student-t signed-error interval is inside [-.02,.02]; their outer
endpoints are [-.007037850274516028,.010937815665856953]. Across all 1,280
probes the largest absolute frequency-minus-fitted-probability error is
.005928201141176814 (limit .01). MC error is separate from fitting error.

The table reports signed fitted-minus-oracle errors. Intervals are the
specified Bonferroni intervals. Raw panel probabilities, errors, seeds and
risk arrays are retained in `docs/design/track_b_p2_recovery.json`.

| Scenario/probe | Oracle | Signed mean | SD | RMSE | Error range | CI | MAE | n<=.04 |
|---|---:|---:|---:|---:|---|---|---:|---:|
| t2_second_order/p2_00 | 0.200000000 | 0.001384810 | 0.004030464 | 0.004201749 | [-0.005601593, 0.012210839] | [-0.001535179, 0.004304799] | 0.003209309 | 32 |
| t2_second_order/p2_01 | 0.700000000 | -0.000805045 | 0.005638229 | 0.005607521 | [-0.013758070, 0.009486564] | [-0.004889826, 0.003279737] | 0.004129856 | 32 |
| t2_second_order/p2_10 | 0.600000000 | 0.001311100 | 0.005742780 | 0.005802405 | [-0.012743220, 0.013164675] | [-0.002849427, 0.005471627] | 0.004654556 | 32 |
| t2_second_order/p2_11 | 0.900000000 | -0.000536126 | 0.001923570 | 0.001967720 | [-0.004687669, 0.002448648] | [-0.001929712, 0.000857461] | 0.001474481 | 32 |
| t3_selection_L16/p2_00 | 0.400000000 | 0.002635430 | 0.003371865 | 0.004237885 | [-0.003316263, 0.010407224] | [0.000192583, 0.005078277] | 0.003521008 | 32 |
| t3_selection_L16/p2_01 | 0.400000000 | -0.000421863 | 0.004596074 | 0.004543318 | [-0.010374706, 0.008334765] | [-0.003751625, 0.002907899] | 0.003673941 | 32 |
| t3_selection_L16/p2_10 | 0.900000000 | -0.001286894 | 0.003087201 | 0.003299859 | [-0.006342539, 0.004323225] | [-0.003523509, 0.000949720] | 0.002894991 | 32 |
| t3_selection_L16/p2_11 | 0.900000000 | -0.000467966 | 0.000994270 | 0.001084745 | [-0.002881693, 0.001810696] | [-0.001188294, 0.000252362] | 0.000853019 | 32 |
| t3_selection_L16/v1_current0_q0false | 0.400000000 | 0.001292605 | 0.002602942 | 0.002869566 | [-0.004872125, 0.007832456] | [-0.000593174, 0.003178383] | 0.002189314 | 32 |
| t3_selection_L16/v1_current0_q0true | 0.280001465 | 0.002382158 | 0.005822862 | 0.006206516 | [-0.009133120, 0.013141423] | [-0.001836387, 0.006600703] | 0.004943581 | 32 |
| t3_selection_L16/v1_current1_q0false | 0.900000000 | -0.000547256 | 0.000879465 | 0.001024098 | [-0.002517829, 0.001184420] | [-0.001184410, 0.000089899] | 0.000795188 | 32 |
| t3_selection_L16/v1_current1_q0true | 0.840000977 | -0.001151824 | 0.002480282 | 0.002699306 | [-0.006586167, 0.003542914] | [-0.002948738, 0.000645090] | 0.002294226 | 32 |
| t3_selection_L4/p2_00 | 0.400000000 | 0.004166870 | 0.009345944 | 0.010098509 | [-0.016863297, 0.027809917] | [-0.002604075, 0.010937816] | 0.007975117 | 32 |
| t3_selection_L4/p2_01 | 0.400000000 | 0.001018422 | 0.010140893 | 0.010033007 | [-0.026231984, 0.020091792] | [-0.006328448, 0.008365292] | 0.007711974 | 32 |
| t3_selection_L4/p2_10 | 0.900000000 | 0.000454072 | 0.007248943 | 0.007149214 | [-0.015343184, 0.017643119] | [-0.004797639, 0.005705783] | 0.005777826 | 32 |
| t3_selection_L4/p2_11 | 0.900000000 | -0.000917559 | 0.002782485 | 0.002888286 | [-0.007266617, 0.003492943] | [-0.002933413, 0.001098294] | 0.002343415 | 32 |
| t3_selection_L4/v1_current0_q0false | 0.400000000 | 0.002815482 | 0.006363638 | 0.006867120 | [-0.015923451, 0.013128992] | [-0.001794844, 0.007425808] | 0.005571337 | 32 |
| t3_selection_L4/v1_current0_q0true | 0.109677419 | 0.001338824 | 0.006127395 | 0.006177713 | [-0.014239239, 0.014827398] | [-0.003100348, 0.005777997] | 0.004884141 | 32 |
| t3_selection_L4/v1_current1_q0false | 0.900000000 | -0.000498978 | 0.002378201 | 0.002393340 | [-0.005787313, 0.002915202] | [-0.002221936, 0.001223980] | 0.001913480 | 32 |
| t3_selection_L4/v1_current1_q0true | 0.624489796 | 0.000437593 | 0.004031568 | 0.003992130 | [-0.010468851, 0.007857864] | [-0.002483196, 0.003358382] | 0.003190598 | 32 |
| t3_selection_L8/p2_00 | 0.400000000 | 0.001054244 | 0.006460071 | 0.006445139 | [-0.014032452, 0.013849098] | [-0.003625945, 0.005734434] | 0.004942478 | 32 |
| t3_selection_L8/p2_01 | 0.400000000 | 0.002542825 | 0.008681527 | 0.008915133 | [-0.010760758, 0.027865645] | [-0.003746764, 0.008832415] | 0.006378048 | 32 |
| t3_selection_L8/p2_10 | 0.900000000 | 0.000320640 | 0.004350922 | 0.004294386 | [-0.008266880, 0.008819898] | [-0.002831514, 0.003472794] | 0.003581070 | 32 |
| t3_selection_L8/p2_11 | 0.900000000 | -0.000296575 | 0.001562897 | 0.001566612 | [-0.003093583, 0.003618934] | [-0.001428862, 0.000835713] | 0.001247513 | 32 |
| t3_selection_L8/v1_current0_q0false | 0.400000000 | 0.001837796 | 0.004799227 | 0.005068561 | [-0.008071074, 0.013237990] | [-0.001639146, 0.005314739] | 0.003775168 | 32 |
| t3_selection_L8/v1_current0_q0true | 0.200521512 | 0.004322388 | 0.007493258 | 0.008548527 | [-0.010417780, 0.018487937] | [-0.001106324, 0.009751101] | 0.007015534 | 32 |
| t3_selection_L8/v1_current1_q0false | 0.900000000 | -0.000244612 | 0.001402880 | 0.001402285 | [-0.002798808, 0.002475430] | [-0.001260970, 0.000771746] | 0.001139977 | 32 |
| t3_selection_L8/v1_current1_q0true | 0.772002231 | -0.000845488 | 0.002992839 | 0.003064641 | [-0.007818210, 0.004495744] | [-0.003013738, 0.001322763] | 0.002597941 | 32 |
| t7_persistent_heterogeneity/p2_00 | 0.109756098 | 0.000991485 | 0.002340732 | 0.002508156 | [-0.002792220, 0.005681384] | [-0.000704327, 0.002687298] | 0.002013647 | 32 |
| t7_persistent_heterogeneity/p2_01 | 0.500000000 | -0.000340874 | 0.006683988 | 0.006587547 | [-0.012689805, 0.013180266] | [-0.005183287, 0.004501539] | 0.005298207 | 32 |
| t7_persistent_heterogeneity/p2_10 | 0.500000000 | -0.001943365 | 0.007031924 | 0.007188837 | [-0.016532891, 0.014615635] | [-0.007037850, 0.003151121] | 0.005238840 | 32 |
| t7_persistent_heterogeneity/p2_11 | 0.890243902 | -0.000430216 | 0.001962025 | 0.001978466 | [-0.003885809, 0.004726337] | [-0.001851663, 0.000991231] | 0.001641990 | 32 |
| t7_persistent_heterogeneity/v1_current0_q0false | 0.180000000 | 0.001167172 | 0.002227085 | 0.002483385 | [-0.004153252, 0.006201898] | [-0.000446306, 0.002780649] | 0.001933191 | 32 |
| t7_persistent_heterogeneity/v1_current0_q0true | 0.100000000 | 0.000482272 | 0.001842695 | 0.001876700 | [-0.003272744, 0.003167942] | [-0.000852723, 0.001817268] | 0.001601769 | 32 |
| t7_persistent_heterogeneity/v1_current1_q0false | 0.820000000 | -0.001301968 | 0.002078769 | 0.002425152 | [-0.006628694, 0.003637939] | [-0.002807994, 0.000204058] | 0.001899296 | 32 |
| t7_persistent_heterogeneity/v1_current1_q0true | 0.100000000 | -0.000857445 | 0.004674042 | 0.004679655 | [-0.010876108, 0.007519604] | [-0.004243693, 0.002528803] | 0.003460858 | 32 |

T3 ordinary-minus-selected fitted contrasts (zero/positive source) are
L4=(.2917992382,.2745736332), L8=(.1969938957,.1285986449), and
L16=(.1189089821,.0606035915). The report also retains their analytic
oracles and per-panel summaries.

T7 measures expected Brier risk by exact enumeration of all eight
(type,current,previous) states, with type weight .5, conditional independent
recent-state weights, and Bernoulli outcome variance included. Mean P2
risk=.12513469210540787; mean v1 risk=.11881534017752164. Paired loss
mean=.006319351927886229, SD=.00009046575748456187, range=
[.006064202444579211,.00650793528804737], 99% two-sided t interval=
[.00627546855740331,.006363235298369147]. The one-sided 99% lower bound
is .006280125780482388>0. Distance from the frozen analytic loss
.0063219512195122 is .000002599291625971 (limit .003). This conditional
gate experiment is not a claimed full-path loss comparison.


## Test commands, results and disclosed repairs

Each model, projection and pytest command used `.venv-p2/bin/python` and
all six required thread variables. Nothing was installed. Actual versions
are Python 3.14.7, populace-fit 0.1.0, NumPy 2.5.1, pandas 3.0.3, SciPy
1.18.0, scikit-learn 1.8.0, Black 26.5.1, ruff 0.15.22, pytest 8.4.2 and
Hypothesis 6.169.0. The supplied Python path reports 3.14.7 rather than the
brief's 3.14.4; this execution discrepancy is disclosed in
`docs/design/track_b_p2_test_execution.md`.

Exact commands (commands producing logs redirected only stdout/stderr to
the named temporary logs):

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest -n 4 -p no:cacheprovider --basetemp /private/tmp/track_b_p2_recovery_20261023 -s tests/test_forward_earnings_p2_recovery.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest tests/test_forward_earnings_p2_exact.py -n 4 -p no:cacheprovider --basetemp=/private/tmp/p2-exact-full -q > /private/tmp/p2-exact-full.log 2>&1
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest tests/test_forward_earnings_p2_exact.py -k 't1 or t5 or nominal_future_baseline' -p no:cacheprovider --basetemp=/private/tmp/p2-exact-final-contract -q
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest -n 4 -p no:cacheprovider --basetemp=/private/tmp/track_b_p2_regression_20261023 -q tests/test_m6_engine_forward_earnings.py tests/test_m6_engine_correlated_refresh.py tests/test_m6_engine_rank_refresh.py tests/test_forward_earnings_history.py tests/estimates/test_birth_evidence_artifact.py > /private/tmp/track_b_p2_regression.log 2>&1
```

| Run | Exit | Final output line |
|---|---:|---|
| T2, T3 L4/L8/L16, T7 | 0 | `5 passed in 541.27s (0:09:01)` |
| Complete initial exact suite | 1 | `1 failed, 67 passed in 2550.01s (0:42:30)` |
| Final repaired contract/property and structural cases | 0 | `24 passed, 46 deselected in 50.02s` |
| Final T4 and six future-input cases | 0 | `26 passed in 7220.79s (2:00:20)` |
| All five requested regression modules, including seal/reachability | 0 | `93 passed in 31.97s` |
| Final repeated five-module regression/seal run | 0 | `93 passed in 47.51s` |

The sole complete-suite failure was Hypothesis's unfrozen default 200 ms
runtime deadline, with 284.12 ms observed and 23.15 ms on its own identical
rerun. It was not a failed history/feature invariant. The complete original
failure is preserved verbatim in the execution document and log. Only
`@settings(deadline=None)` was added; input strategy, default example
count, every fixture/seed and every numerical criterion are unchanged.
No numerical or statistical criterion was relaxed.

An earlier implementation-only signature serializer error (`vars()` on a
slots-based marginal) produced 2 failed, 19 passed, 46 deselected. Explicit
field serialization repaired it. This incident and the corrected checks
are also recorded in the execution document.

After the long run, exact tests clarified the nominal-future reference:
a fast structural test proves it has byte-identical complete fitted
objects, admitted signatures and initial state to the already-executed
reference. The final 24-case run validates this proof, all repaired T1/T5
assertions and the new structural assertions. Test-local evaluation truth now explicitly uses
0-to-100 rather than absent-to-100; both changes are excluded by the
unchanged pinned conditioning surface. Every frozen full path and restart
comparison already completed on the same production source bytes. The final
T4 and six future-input cases are additionally rerun as recorded below;
the unchanged 20 T6 clock/restart cases retain their complete-run results.
The recovery report's
observed contrasts were computed from its saved probabilities without
refitting, and its raw pair comparison was made explicitly exact.

The 24 final contract/property/structural cases, the 26 final T4/future-input
cases and the 20 unchanged T6 clock/restart cases that passed in the original
complete run account for the 70-case final exact test inventory. The five
recovery cases also passed.
There is no claim of a single clean 70-case pytest
summary. T4 covers all 20 roots. T6 covers 140 checkpoint/restores and 560
resumed annual frames, both supported generator interfaces, all three
specified history clocks, and six independent future perturbations over
all 20 roots.

The amended direct-law T4 reference is part of the supplied specification.
It is not an additional execution change. The initial source-only audit's
system-Python deviation was corrected by a required-environment rerun.
See the execution document for the complete disclosure.


## Frozen mutation checks

`docs/design/track_b_p2_mutations.json` follows the R2 ledger format and
retains every old/new replacement, exact command, exit code, failed test
ID, log location and restored-source SHA-256. All 14 named mutations made
their designated checks fail. There are 15 executions: T4's first attempt
failed before the designated assertion and is explicitly excluded from
the successful-check count. Its original log is preserved as
`/private/tmp/track_b_p2_mutation_7_initial.log`. Reordering existing T4
probability/sign assertions before P2 path generation exposed the intended
first-step sign failure; no fixture or criterion changed.

| Mutation | Designated check | Result |
|---|---|---|
| T1 change strict threshold > to >= | T1 exact 1e-6 threshold row | Exit 1; 1 failed, 4 passed in 15.64s |
| T1 encode missing history as (0,0) | T1 exact missing indicator table | Exit 1; 1 failed, 4 passed in 11.12s |
| T1 inner-join prior history | T1 raw pair retention / absent history | Exit 1; 9 failed in 35.24s |
| T1 use age-filtered history | T1 observed outside-age prior | Exit 1; 1 failed in 10.17s |
| T2 remove older participation and zero its query position | T2 recovery MAE .20087483984143373 > .015 | Exit 1; 1 failed in 222.64s (0:03:42) |
| T3 fit and route P2 only on zero-anchor persons | T3 recovery MAE .3229788911156376 > .015 | Exit 1; 1 failed in 181.06s (0:03:01) |
| T4 force missing-history nonparticipation | T4 first-step positive-sign equality | Exit 1; 1 failed in 48.82s |
| T5 build donors from history-complete gate rows | T5 non-gate equality (audit count 240 != 275) | Exit 1; 1 failed in 21.10s |
| T6 admit post-boundary gate-fit rows | T6 admitted-state signature equality | Exit 1; 1 failed in 56.06s |
| T6 admit realized future NAWI | T6 admitted-state signature equality | Exit 1; 1 failed in 53.27s |
| T6 omit gen_earn_w4 at restart | T6 required restart-state refusal (amendment 1 permits refusal) | Exit 1; 1 failed in 64.81s (0:01:04) |
| T6 read gen_earn_w2 as older history | T6 exact runtime history/clock | Exit 1; 1 failed in 83.51s (0:01:23) |
| T6 reset resumed period indices | T6 exact resumed suffix | Exit 1; 1 failed in 79.00s (0:01:19) |
| T7 route v1 zero anchors to its shared gate | T7 one-sided positive-loss lower bound | Exit 1; 1 failed in 230.42s (0:03:50) |

The T7 benchmark mutation reverses the comparison: mutated v1 mean risk
.1476060242817251; P2-minus-mutated-v1 mean loss=-.022471332176317214;
one-sided 99% lower bound=-.022477489684556172. This fails the designated
positive-loss assertion before probability recovery assertions.

Restored hashes match final files after every check and after the suite:

- P2 production module:
  `58fbb3d58847d1ab168fa7b2b33c013694bcf8c680c6b37f48e8c8067e3bf234`.
- Recovery test source (T7's benchmark mutation):
  `7ca6710e813066d56d5dc5bb1d68669f4a1c8544bab728f1bf53d6cc60e8995f`.

Mutation orchestration commands used the same required interpreter/thread
environment; every child pytest command is recorded verbatim in the JSON:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python /private/tmp/p2_mutation_runner.py 14 > /private/tmp/track_b_p2_mutation_runner_14.log 2>&1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python /private/tmp/p2_mutation_runner.py 1 2 3 4 5 6 7 8 9 10 11 12 13 > /private/tmp/track_b_p2_mutation_runner_1_13.log 2>&1
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python /private/tmp/p2_mutation_runner.py 7 > /private/tmp/track_b_p2_mutation_runner_7_assertion.log 2>&1
```

The orchestrator exited zero in all three invocations, because each
expected pytest failure was observed and the original bytes were restored.
The first T4 execution's unrelated donor-pool refusal was identified by
manual assertion-level review and retained as an unsuccessful check.


## Final formatting, source and seal verification

Final project-Python commands (exit 0):

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m black -l 79 src/populace_dynamics/engine/forward_earnings_p2_v1.py tests/test_forward_earnings_p2_exact.py tests/test_forward_earnings_p2_recovery.py scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m ruff check src/populace_dynamics/engine/forward_earnings_p2_v1.py tests/test_forward_earnings_p2_exact.py tests/test_forward_earnings_p2_recovery.py scripts/first_estimates_birth_evidence.py tests/estimates/test_birth_evidence_artifact.py
```

Final output:

```text
All done! ✨ 🍰 ✨
5 files left unchanged.
All checks passed!
```

Logs are `/private/tmp/p2_black_final.log` and
`/private/tmp/p2_ruff_final.log`. Black was 26.5.1. The retained temporary
audit/mutation scripts also passed Black and ruff; no draft is retained.

After every mutation was restored, the source-only guard/AST command was
repeated with the required interpreter and environment and exited 0.
`/private/tmp/p2_source_checks_final.log` confirms all 19 guarded files
equal both baseline commits, and both generator bodies preserve the
inherited validation, RNG, donor and frame-update AST apart from the
explicit P2 changes. The required existing-src diff again exited 0 with
no output. The spec and amendment SHA-256 remain respectively
`df5df7f2de3992a95d24ae49cbc2924c6c415d9316472c7bdb0d75f254769681`
and `b1c7c99313a2c50b815a8de8afba36fa901ea4b94a51f59711ef50697cd9374e`.

The final requested regression/seal run also exited 0:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest -n 4 -p no:cacheprovider --basetemp=/private/tmp/track_b_p2_regression_final -q tests/test_m6_engine_forward_earnings.py tests/test_m6_engine_correlated_refresh.py tests/test_m6_engine_rank_refresh.py tests/test_forward_earnings_history.py tests/estimates/test_birth_evidence_artifact.py > /private/tmp/track_b_p2_regression_final.log 2>&1
```

Final line: `93 passed in 47.51s`. This includes the historical source
identity seal, its exact exclusion tuple and import-unreachability check.
Only the new P2 module is added under src/. Its exclusion and the two
expected-test entries preserve the preparatory working-tree changes.

## Files and working-tree delivery

Added:

- `src/populace_dynamics/engine/forward_earnings_p2_v1.py`.
- `tests/test_forward_earnings_p2_exact.py`.
- `tests/test_forward_earnings_p2_recovery.py`.
- `docs/design/track_b_p2_source_audit.md` (this report).
- `docs/design/track_b_p2_recovery.json`.
- `docs/design/track_b_p2_mutations.json`.
- `docs/design/track_b_p2_test_execution.md`.
- `docs/design/track_b_p2_access_inventory.json`.

Changed only the already-prepared seal entries in
`scripts/first_estimates_birth_evidence.py` and
`tests/estimates/test_birth_evidence_artifact.py`. The unfinished
`docs/design/.p2_refit_snippet.py` was folded into the P2-owned refit and
deleted. No existing src file, frozen specification, gates.yaml, committed
run artifact or tier count was changed. No commit, history rewrite or push
was performed; all changes remain in the assigned branch's working tree.


## Final path revalidation

After restoring all mutation bytes and formatting the final test source,
the revised T4 and six future-input cases are revalidated end to end with:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 OMP_WAIT_POLICY=PASSIVE .venv-p2/bin/python -m pytest -n 4 -p no:cacheprovider --basetemp=/private/tmp/p2-exact-final-paths -q tests/test_forward_earnings_p2_exact.py -k 't4 or no_look_ahead' > /private/tmp/p2-exact-final-paths.log 2>&1
```

Final result, exit code 0:

```text
..........................                                               [100%]
26 passed in 7220.79s (2:00:20)
```

All 20 revised T4 roots and all six final future-input cases completed
successfully on the restored production source. This closes the final
reference/truth clarification and T4 assertion-order repair. The exact
suite's final 70-case coverage is partitioned explicitly above; the original
failed Hypothesis runtime-deadline check remains disclosed.

The final read-only closure check confirmed the production and both test
source hashes, the two frozen-document hashes, all 15 restored mutation
records, valid evidence JSON, absence of the unfinished draft, and the
unit-tier source-string restriction. The exact existing-src diff again
exited 0 without output. The final access inventory contains 190 individual
file entries. The assigned branch remains `trackb-p2-dev-20261021`; no
commit or push was made.

## Declarations

I met no B2 cell result or 2012/2014 gap, including through delegated
work. I read no survey data, used no network or GitHub, opened no
prohibited checkout/evidence directory or sparse-hidden file, and ran no
fetch, pull or push. Candidate 3 and its registry remain unchanged. This
is invented-data development; no real-data gate or registration was run.

Every project source/artifact opened outside src/ and tests/, including
delegated reads, authorized automated regression reads, generated evidence,
removed helpers and conservative scratch-file inventories, is listed in
`docs/design/track_b_p2_access_inventory.json`. The full list includes:

- `CLAUDE.md`, `pyproject.toml`, the frozen spec, amendment and review notes;
  the removed refit draft; the R2 mutation-ledger format; and all five new
  P2 evidence documents.
- `scripts/first_estimates_birth_evidence.py`,
  `scripts/select_m6_qstar_train_only.py`,
  `scripts/build_mortality_floors.py`,
  `scripts/registered_m6_inputs.py`,
  `scripts/registered_m6_candidate2_inputs.py`,
  `scripts/registered_m6_candidate3_inputs.py`, and
  `scripts/smoke_m6_rank_refresh_engine.py`.
- Authorized automated regression reads of
  `docs/analysis/m6_rank_refresh_engine_synthetic.json` and
  `runs/first_estimates_birth_evidence_draw0.json`; neither artifact was
  reopened merely to prepare the inventory.
- `/Users/maxghenis/.agents/skills/gitnexus-exploring/SKILL.md` and the
  explicitly permitted pinned `populace/fit/qrf.py` source at the full
  path recorded in the inventory.
- Every named temporary audit/helper script, guard/v1 byte artifact,
  recovery scenario JSON, mutation log, test/format log and conservatively
  enumerated file in the dedicated test temporary directories and local
  Hypothesis/ruff caches. The JSON lists individual paths, including
  removed helpers, rather than relying on directory wildcards.

No spec choice, fixture, seed, size, estimator, numerical tolerance,
acceptance criterion or reserve ordering changed. Implementation and test
execution repairs, their original failures and exact reruns are preserved
in `track_b_p2_test_execution.md` and the mutation ledger. Changes remain
uncommitted in the assigned workspace and branch.
