# P2: frozen specification

Frozen on 2026-10-22 under ruling d1803. This specifies development on invented panels; it does not register a real-data attempt. Choices below follow the proposer’s section 2, independently of B2’s cell outcomes. No development tests were run in this review.

Code citations beginning `engine/` are relative to `src/populace_dynamics/`. Report citations are relative to `_review_context/`.

## 1. Feature set and scale

P2 uses **one shared participation gate with four ordered numeric predictors**:

| Position | Fitting column | Meaning | Projection value at even target year \(y\) |
|---|---|---|---|
| 1 | `earnings` | Raw nominal source earnings | `frame["earnings"]`, representing earnings at \(y-2\) |
| 2 | `age_tp2` | Target age | `frame["age"]` at \(y\) |
| 3 | `prior_positive` | Participation at the preceding biennial observation | Derived from `gen_earn_w4`, representing \(y-4\) |
| 4 | `prior_missing` | That preceding observation is unavailable | Derived from the same lag |

All four predictors are `float64`; indicators take `0.0` or `1.0`. There are no additional predictors, manually constructed interactions, transformations, clipping, normalization, or feature selection.

**Source earnings remain nominal. P2 is a standalone alternative built on v1, without S1’s transformation.** The proposer explicitly specifies nominal earnings and treats combination with S1 as another law requiring its own justification (`p4-proposer-sol-out.md:117–132`, `:12`).

P2’s hypothesis concerns information in recent participation history and the estimand implied by retrospective anchor routing. Neither argument selects wage-relative earnings. Retaining v1’s nominal predictor isolates those proposed changes (`p4-proposer-sol-out.md:134–157`).

The independent support is limited:

- The mechanism report identifies v1’s two-feature gate and immutable anchor routing (`p1-mechanism-out.md:11–19`, `:25–45`).
- Evidence item 8 supports documented age and anchor restrictions, with its chronology qualification; it does not establish a causal forecasting defect (`p2-evidence-out.md:12`, `:45`).
- MINT7 uses recent work histories; FAM uses evolving lagged labor status in biennial transitions. These support history dependence, without establishing P2’s particular state or equating labor status with annual earnings (`p3-literature-out.md:63–75`, `:146–158`).

## 2. Lag count

Use **one prior biennial participation indicator beyond the source earnings observation**: two observed earnings states in total.

For a historical \(t\rightarrow t+2\) pair, those states are \(Y_t\) and participation derived from \(Y_{t-2}\). At projection year \(y\), they are carried \(Y_{y-2}\) and participation derived from \(Y_{y-4}\).

There is no longer history, zero-spell count, annual interpolation, or latent participation effect. This fixes the proposer’s explicit one-lag proposal and uses the existing lag state (`p4-proposer-sol-out.md:126–128`, `:177`, `:191`). The literature supports recent-history dynamics but does not establish that two states suffice; that remains P2’s substantive restriction (`p4-proposer-sol-out.md:155`, `:195`).

## 3. Indicator definitions

For an available, valid raw earnings value \(h\), define

\[
\operatorname{positive}(h)=\mathbf 1\{h>10^{-6}\}.
\]

Thus exact zero, positive values below \(10^{-6}\), and exactly \(10^{-6}\) have indicator zero. Values strictly above \(10^{-6}\) have indicator one. The indicator describes **positive annual earnings**, not labor-force membership, employment at interview, or annual spell duration.

This matches the positive class implied by the pinned classifier’s raw-value zero tolerance. The dependency-source finding is supplied by the mechanism report; the external `qrf.py` was unavailable inside this copy and its outside-workspace link was not followed (`p1-mechanism-out.md:49`, `:195`). Raw target earnings and the classifier’s existing sign-label rule remain unchanged.

**Historical construction.** First construct exactly v1’s source–target pairs. Left-join the same person’s observation at exactly `period - 2`, using the pre-boundary, positive-weight `cutoff_panel`, before its age restriction. Use the joined raw `earnings` value to construct the indicators. Preserve pair order and validate the history lookup as many-to-one. Existing pairs are exact two-year joins, followed by the boundary-person restriction (`engine/forward_earnings.py:562–589`, `:1021–1035`, `:1067–1068`).

**Projection construction.** Read raw older earnings from `gen_earn_w4`; read current nominal earnings from `earnings`. Do not derive the older indicator from `gen_earn_w2`, the immutable anchor, or an observed future record. The generator reads these fields separately (`engine/forward_earnings.py:1733–1737`, `:1916–1922`).

The proposer’s initialization reference is substantively correct but imprecise: line 1459 assigns the boundary field; **line 1463 assigns `gen_earn_w4`**. Initialization sets:

```text
earnings    = Y_b
gen_earn_w2  = Y_b
gen_earn_w4  = Y_(b−2), or NaN when unavailable
```

The older map comes from `cutoff_panel` at \(b-2\) (`engine/forward_earnings.py:1111–1117`, `:1437–1463`).

The cited biennial roll is also correct. After an even-year draw, `steps.py` assigns `gen_earn_w4` from the **pre-draw** `gen_earn_w2`, then assigns `gen_earn_w2` from generated earnings. Odd years do not perform that roll (`engine/steps.py:337–355`). Consequently:

| Query | Current source | Older state |
|---|---|---|
| \(b+2\) | \(Y_b\) | Observed \(Y_{b-2}\), possibly unavailable |
| \(b+4\) | Generated \(Y_{b+2}\) | \(Y_b\) |
| \(b+6\) | Generated \(Y_{b+4}\) | Generated \(Y_{b+2}\) |

## 4. Missing-history coding

Use this encoding in both fitting and querying:

| Older history | `prior_positive` | `prior_missing` |
|---|---:|---:|
| Valid observed \(0\le h\le10^{-6}\) | 0 | 0 |
| Valid observed \(h>10^{-6}\) | 1 | 0 |
| No eligible exact prior observation, or its earnings are NaN | 0 | 1 |

A negative or infinite supplied older earnings value **aborts with `P2_INVALID_HISTORY_VALUE`**. It is neither imputed nor handled by deleting a pair. Applying this refusal during historical feature construction is a frozen P2 validation choice, consistent with v1’s projection-state rejection of negative/infinite older lags (`engine/forward_earnings.py:1753–1771`).

Unavailable history includes all these cases:

| Reason | Treatment |
|---|---|
| Prior year precedes the supplied panel or an available collection wave | Missing |
| Exact prior wave is absent, including intermittent nonresponse or an irregular observation gap | Missing; no nearest-wave substitution |
| No prior person record, or person not present under the upstream sequence rule | Missing |
| No matching prior family record | Missing |
| Prior relationship is outside the upstream head/reference-person and spouse/partner coverage | Missing |
| Prior labor earnings were removed as missing/sentinel values upstream | Missing |
| Prior weight fails the existing `weight > 0` filter | Missing |
| Prior row exists but its earnings are NaN in a directly supplied invented panel | Missing |
| Prior age is outside 25–64, while the row otherwise survives `cutoff_panel` | **Observed**, using its raw earnings |

These upstream exclusions follow the present-person filter, family merge, relationship selection, earnings assignment, and earnings/weight filter (`scripts/select_m6_qstar_train_only.py:449–485`). That filter is exactly `earnings < family._MISSING` and `weight > 0`; this specification does not claim it removes every invalid numeric value (`:479–485`).

Using `cutoff_panel` for history is deliberate: initialization already obtains \(b-2\) history before the age restriction (`engine/forward_earnings.py:1030–1035`, `:1111–1117`). Using the age-filtered estimation panel would manufacture missingness for otherwise available histories.

At the first even projection step, unavailable \(Y_{b-2}\) becomes `(0,1)`. After that draw, rolling supplies \(Y_b\) as the older state. Retain v1’s refusal of NaN older state from \(b+4\) onward; such a NaN indicates a corrupted supported-person state, rather than an ordinary missing historical wave (`engine/forward_earnings.py:1756–1767`; `engine/steps.py:337–355`).

Persons outside the existing fitted domain are not newly admitted through missing-history coding. Existing domain handling leaves their chain fields unavailable and supplies its administrative earnings treatment (`engine/earnings_domain.py:71–87`, `:161–208`; `engine/steps.py:330–336`).

**No existing source–target pair is dropped.** On every valid input, P2’s raw pair keys, order, raw values, and weights must equal v1’s on that same input. History is added on a separate gate view by left join. Missing-history handling never changes the estimator or donor pair population.

## 5. What is removed and retained

| Component | Frozen treatment and code basis |
|---|---|
| Zero-anchor gate fitting | Remove the second fit at `engine/forward_earnings.py:1081–1091`. Do not fit v1 first and replace a gate afterward. |
| Participation anchor routing | Remove the branches at `engine/forward_earnings.py:1783–1803` and `:1964–1984`. Every modeled person uses the same four-feature gate. |
| `q0` | Retain exact `anchor_level == 0` for donor and refresh mechanisms (`engine/forward_earnings.py:1780–1782`, `:1841–1876`). It is not a gate feature. |
| Anchor rank and donor coordinates | Retain boundary rank construction and the `q0`-dependent donor coordinate: `u_A` for `q0`; otherwise `.1*u_w + .9*u_A` (`engine/forward_earnings.py:1509–1533`). |
| Pair population | Retain pre-boundary, positive-weight rows; ages 25–64 at both pair endpoints; exact same-person two-year pairs; boundary-observed persons (`engine/forward_earnings.py:1021–1035`, `:1055–1072`). |
| Weights | Retain gate target-row `weight_tp2` and donor target-row weights. Marginals retain observation-row weights (`engine/forward_earnings.py:1074–1080`, `:771–778`, `:506–527`). |
| Estimator | Retain the same pinned `RegimeGatedQRF` build and defaults, called with only `seed=seed`; change only its predictor list and training population as specified. No hyperparameter search or dependency upgrade (`engine/forward_earnings.py:979–987`; `engine/refit.py:77–90`). Pinned classifier weighting and tolerance details are report-supported (`p1-mechanism-out.md:19`, `:49`, `:195`). |
| Gate-contained magnitude forests | Retain the wrapper’s normal fitting behavior with the four predictors. These forests belong to the changed gate object and remain unused for projected amounts (`p1-mechanism-out.md:13`, `:216`; runtime sign extraction: `engine/forward_earnings.py:1173–1179`). |
| Donor inputs | Retain the original nominal estimation panel, raw pairs, anchors, marginals, historical index, and permanent scores. Never pass a filtered history-complete frame into donor construction (`engine/forward_earnings.py:1092–1105`). |
| Donor law | Retain pair, triple, and re-entry pools; \(k=25\); distance weights `1,.5,.25`; `.1/.9` coordinate blend; target-weighted selection; existing branch ramp (`engine/forward_earnings.py:73–77`, `:753–905`, `:1182–1206`, `:1527–1587`, `:1829–1863`). |
| Marginals | Retain eight five-year age bins, historical NAWI normalization, empirical positive quantiles, zero masses, and existing interpolation/clamps (`engine/forward_earnings.py:64–71`, `:386–406`, `:486–533`). |
| Permanent scores | Retain autocovariances, NNLS, AR grid `.50,.51,…,.95`, and person shrinkage (`engine/forward_earnings.py:79–80`, `:592–750`). |
| Wage index | Retain trailing-decade unweighted log-linear OLS, pre-boundary actual values, and origin-frozen projected values afterward. P2 introduces no gate deflation (`engine/forward_earnings.py:422–483`, `:1038–1048`). |
| Refresh | Retain candidate 3’s `q=.55`, `rho=−.60`, operation IDs, reset behavior, and donor support rules (`engine/candidates.py:122–151`; `engine/forward_earnings.py:1864–1887`). |
| Timing and randomness | Retain odd-year nominal carry, even-year updates, person sorting, existing RNG addressing, and inner stream codes 1–5. Generate the same gate-uniform array and consume no additional randomness (`engine/forward_earnings.py:82–88`, `:1156–1158`, `:1694–1717`, `:1725–1731`, `:1773–1782`). |

Retaining selected v1 parameters is inheritance, not new independent evidence for their values. Their historical selection exposure remains disclosed (`p2-evidence-out.md:13`, `:46`).

## 6. Signatures and versioning

Freeze these new identities:

```text
Candidate ID:       m6_candidate3_p2_history_engine_v1
Contract revision:  p2_frozen_2026_10_22
Module:              src/populace_dynamics/engine/forward_earnings_p2_v1.py
Fitter:              fit_forward_earnings_p2_v1
Generator:           P2ForwardEarningsGeneratorV1
```

The sibling module owns P2’s fit orchestration, four-feature query helper, generator participation block, refit metadata, and signatures. Its candidate declaration retains candidate 3’s refresh operation payloads exactly. Existing candidate declarations and v1 dispatch remain unchanged; candidate metadata already supports an ID, contract revision, immutable operations, and canonical hash (`engine/candidates.py:79–119`, `:140–151`).

Set `zero_anchor_gate=None`, record `zero_anchor_gate_removed=true`, and record zero fitted zero-anchor pairs. These are changed gate metadata, not unchanged structural objects. Existing fields and provenance locations are `engine/forward_earnings.py:998`, `:1149` and `engine/refit.py:814–817`.

The query helper must construct all four columns and use the fitted classifier’s recorded column order, probabilities, class order, and existing cumulative-`>=` selection rule. It must not call the legacy three-argument `draw_sign` path, which accepts only current earnings, age, and uniforms (`engine/forward_earnings.py:1168–1179`). Both generation interfaces must implement the same feature rule.

Feature and fit signatures must record:

- Candidate identity, specification revision, dependency/source identities, resolved estimator parameters, seed, and boundary.
- Ordered column names and `float64` feature bytes.
- Nominal earnings scale; \(10^{-6}\) threshold; one exact two-year history lag; missing encoding; invalid-history refusal; lookup before age filtering.
- Canonical pair keys, history lookup year, availability mask, and joined historical values, using a canonical zero placeholder for unavailable values plus the explicit mask.
- Raw target and weight checksums, fitted classes, probabilities on every canonical training query, and serialized fitted-gate state.
- Exactly one shared gate and explicit absence of the zero-anchor gate.
- Separate unchanged-component checksums for the non-gate objects.

Canonical gate rows are sorted by person and target period, following the existing signature convention (`engine/forward_earnings.py:1210–1259`). P2 must supply its four-feature gate view. The overall signature changes; component equality is checked separately because the current total signature includes participation gates (`engine/forward_earnings.py:1281–1343`).

`m6_candidate3_engine_v1`, `engine/forward_earnings.py`, `engine/loop.py`, and `engine/steps.py` remain unchanged. Existing `gates.yaml` and committed run artifacts also remain unchanged, as required by the design (`trackb-design-20260928.md:275–279`).

## 7. Tests on invented panels

Every test includes the stated mutation check. A mutation must make its designated assertion fail. Exact equality means equal numeric values, array shapes, ordering, and missing-value masks under the same pinned environment.

### Fixed fixtures and statistical protocol

For full-law exact tests, use boundary \(b=2000\), persons `i=0,…,639`, and waves \(b-2k\), `k=0,…,8`. Set:

```text
boundary age = 25 + i % 40
wave age     = boundary age − 2*k
weight       = 1 + (i % 3)/4
sex          = 1 + i % 2
```

Draw `Z[i,k]` in row-major order from NumPy PCG64 seed `20261022`. Positive amounts are `100*(1+i%13)*exp(.2*Z[i,k])`. In the mixed fixture, set earnings to zero when `(i+k)%7 == 0`. Supply invented NAWI `exp(.02*(year-b))` for years `b−25,…,b+8`. Use fit seed `5200`, projection roots `6200,…,6219`, full-anchor sorted ordinals, eight original annual period coordinates, and compare through \(b+8\). These values are fixture choices fixed here.

For T2, T3, and T7, use **gate recovery experiments**, avoiding unrelated donor-support requirements:

- 32 independent panels of 8,192 persons; constant age 40, weight 1, positive amount 100, zero amount 0, and NAWI 1.
- Use the actual gate-view constructor and pinned estimator. Do not substitute an oracle estimator.
- PCG64 panel seed is `20261022 + 1000*c + r`, with `r=0,…,31` and `c=2,3,7`. T3 additionally adds `100*j` for its three lengths, `j=0,1,2`.
- Estimator seed is `5200+r`, shared between laws within a replicate.
- For every asserted oracle probability, require mean absolute fitted error across panels ≤`.015`, at least 31 of 32 absolute errors ≤`.04`, and every absolute error ≤`.08`.
- Additionally, each signed mean-error confidence interval must lie within `[-.02,.02]`. Use Student-t intervals with 31 degrees of freedom and Bonferroni allocation of total two-sided error `.01` across the 36 oracle probability assertions: four in T2, eight for each T3 length, and eight in T7.
- Report signed mean error, between-panel SD, RMSE, range, and confidence interval. Independent generated panels measure fitting variability; do not bootstrap copied person rows.
- For each of the eight prescribed probes per scenario—four P2 history states and four v1 current-state/anchor-route states—draw 65,536 fresh gate uniforms. Use `SeedSequence([panel_seed+1000000, probe_index])`, with probes ordered P2 `(00,01,10,11)`, then v1 `(current=0,q0=0)`, `(0,1)`, `(1,0)`, `(1,1)`.
- Require every simulated positive frequency to be within `.01` of its fitted probability. There are 40 probes per replicate across the five scenarios. Hoeffding’s union bound is \(2560e^{-2(65536)(.01)^2}<.01\). Monte Carlo error is thus checked separately from fitting error.

No seed replacement, sample-size escalation, tolerance relaxation, estimator change, or alternative search follows a failure. Invented resampling leakage is an admissible reason to use independent panels rather than copied-row bootstrap fits (`p2-evidence-out.md:16`, `:48`).

### T1 — Exact feature, history, and pair-retention contract

Check the four ordered features against hand-calculated tables, including raw values `0`, `5e-7`, `1e-6`, and `nextafter(1e-6,+inf)`.

Exercise every missing-history reason in section 4, an available prior outside ages 25–64, and first-step initialization. Absent-history reasons may be represented by omission from the invented supplied panel; no PSID reader is invoked. Check invalid negative/infinite histories refuse. Compare all raw pair keys, order, values, and weights with v1 on the same input.

**Mutations:** inner-join prior history; encode missing as `(0,0)`; use age-filtered history; change `>` to `>=` at the threshold. Each must fail its corresponding exact assertion.

**Prediction:** all correct assertions pass exactly; no pair disappears through the new history join.

### T2 — Second-order recovery and exact representational distinction

Generate the proposer’s process:

| Current positive | Previous positive | Next-positive probability |
|---|---|---:|
| 1 | 1 | .90 |
| 1 | 0 | .60 |
| 0 | 1 | .70 |
| 0 | 0 | .20 |

Start with two independent Bernoulli(`.5`) states, burn in 256 transitions, then retain nine consecutive waves, ending at the boundary. Everyone has a boundary observation. Probe all four complete-history states.

Apply the recovery criteria to P2’s four oracle probabilities. Separately require v1 to give exactly equal probabilities to matched queries with the same current earnings, target age, and anchor route but different older participation.

**Mutation:** remove the older-participation predictor and supply zero in its query position.

**Prediction:** P2 meets recovery criteria. The mutation fails recovery; v1 cannot represent the matched-history distinctions. This implements the proposer’s first development case (`p4-proposer-sol-out.md:161–170`).

### T3 — Retrospective-selection recovery

Generate stationary first-order chains with

\[
P=\begin{pmatrix}.6&.4\\.1&.9\end{pmatrix},
\qquad \Pr(Z_0=1)=.8.
\]

Use lengths \(L=4,8,16\) transitions. Everyone is observed at the terminal boundary. P2’s four complete-history probabilities and v1’s two shared-gate probabilities have ordinary-transition oracles `.4` and `.9`.

The two v1 zero-anchor probabilities have pooled endpoint-selected oracles

\[
r_L(s)=P_{s1}
\frac{\sum_{k=0}^{L-1}(P^k)_{10}}
{\sum_{k=0}^{L-1}(P^{k+1})_{s0}}.
\]

Apply the fitting criteria to all eight probabilities for each length. Report ordinary-minus-selected contrasts for each source state and length.

**Mutation:** fit and route P2 using only zero-anchor persons.

**Prediction:** correct P2 recovers the ordinary transition law; v1’s zero-anchor gate recovers different endpoint-selected probabilities, with smaller discrepancies for longer histories. The mutation fails ordinary-transition recovery. This tests retrospective selection, without calling it forecasting leakage (`p4-proposer-sol-out.md:142–146`, `:172`).

### T4 — Exact always-positive neutrality

Use the full-law fixture with every amount positive and NAWI equal to one. Additionally omit the \(b-2\) row for persons with `i%8 == 0`, identically in both laws’ inputs.

Require equality between P2 and v1 of participation probabilities, signs, and complete earnings paths under common draws.

**Mutation:** force nonparticipation whenever `prior_missing==1`.

**Prediction:** correct implementations agree exactly; the mutation breaks first-step equality for affected persons. This covers the proposer’s always-positive case (`p4-proposer-sol-out.md:173`).

### T5 — Exact isolation outside the gate

On the mixed full-law fixture, compare v1 and P2 exactly for:

- Estimation rows, original nominal pairs, anchors, and boundary/history maps.
- Every marginal field and array.
- Permanent scores and diagnostics.
- Every pair, triple, re-entry, and stable-pool array and its conditioning inputs.
- Refresh audit and fixed refresh settings.
- Wage-index actual mapping, coefficients, and boundary.

Exclude the entire changed `RegimeGatedQRF` object, including its unused within-sign forests, and changed gate metadata. This matches the component structure of the existing signatures (`engine/forward_earnings.py:1281–1343`).

**Mutation:** construct donor pools after filtering the gate view to complete histories.

**Prediction:** correct P2 equals v1 outside the gate; the mutation loses donor inputs and fails. Subsequent generated donor choices need not equal v1 once participation paths differ.

### T6 — Exact clock, no-look-ahead, and restart

Use the mixed full-law fixture, including an unavailable first-step lag.

1. Assert runtime features against hand-built expected values at \(b+2,b+4,b+6\), including missing flags and even-year rolling.
2. Exercise both generator interfaces with identical applicable state.
3. Independently alter, append, delete, and reorder earnings input rows dated after \(b\); change post-boundary realized NAWI values and separate evaluation truth. Require unchanged fitted objects, admitted-state signatures, features, signs, frame updates, and full generated paths.
4. Checkpoint after every annual step through \(b+7\), restore, and compare the resumed suffix exactly with uninterrupted execution.

Restart preserves the fitted object, complete materialized frame, original boundary, full-anchor ordinals, draw index, eight-period registry, and original period indices. It uses a sibling resume adapter, without calling boundary initialization again. Existing `ProjectionEngine.run` initializes its input, whereas earnings initialization requires the original boundary (`engine/loop.py:203–206`; `engine/forward_earnings.py:1411–1420`). Original period/person addressing follows `engine/rng.py:61–83`, `:158–169` and `scripts/select_m6_qstar_train_only.py:1574–1609`.

A manifest hashing an entire altered input container may change; it is distinct from the admitted fitted-state signature.

**Mutations:** read `gen_earn_w2` as older history; admit post-boundary fit rows or realized NAWI; omit `gen_earn_w4` at restart or reset period indices. Each must fail its designated assertion.

**Prediction:** all correct comparisons pass exactly. This implements the required information-boundary and restart invariants (`trackb-design-20260928.md:397–399`) and the proposer’s missing-history case (`p4-proposer-sol-out.md:174`).

### T7 — Persistent-heterogeneity counterexample

Run the construction and loss criteria in section 8.

**Mutation:** make the v1 benchmark use its shared gate for zero-anchor persons too.

**Prediction:** correct P2 has the declared positive loss; the mutation reverses that comparison and fails the loss assertion. This guards against benchmarking an invented version of v1.

## 8. Its counterexample

P2 is expected to do worse when **the anchor conveys enduring attachment beyond the two recent states**, as the proposer explicitly warns (`p4-proposer-sol-out.md:146`, `:175`, `:195`, `:205`).

Use equally prevalent latent types H and L. At ordinary dates, participation observations are conditionally independent Bernoulli draws with probabilities `.9` and `.1`, respectively. Positive earnings equal 100.

Retain nine ordinary historical waves \(b-20,b-18,\ldots,b-4\), omit \(b-2\), and observe everyone at \(b\). Make boundary participation reveal type perfectly: H is positive; L is zero. No existing fitted pair touches that exceptional boundary transition. Preserve every pair v1 constructs from this invented panel.

Evaluate one-step gate probabilities on the eight analytically weighted `(type,current,previous)` combinations at conceptual target \(b+6\). The two recent states are ordinary draws; the original anchor is legitimate older information. This is a conditional gate experiment, not substitution of future observations into a boundary-origin projection.

The oracle probabilities are:

| Law | Oracle |
|---|---|
| v1 shared gate, used for H | `.82` when currently positive; `.18` when currently zero |
| v1 zero-anchor gate, used for L | `.1` |
| P2, recent states `11` | `.8902439024390244` |
| P2, recent states `10` or `01` | `.5` |
| P2, recent states `00` | `.1097560975609756` |

This honors v1’s actual asymmetric routing: positive-anchor persons use the all-person shared gate (`engine/forward_earnings.py:1780–1803`).

The analytic expected Brier risks are:

```text
v1:                 0.1188
P2:                 0.1251219512195122
P2 minus v1 loss:    0.0063219512195122
```

For each of the 32 paired fits, calculate expected Brier risk by exact enumeration, including Bernoulli outcome variance. Report each law’s mean risk and the paired loss’s mean, SD, range, and 99% two-sided Student-t interval.

Require:

- A one-sided 99% Student-t lower bound for mean P2-minus-v1 loss above zero.
- Mean loss within `.003` of `.0063219512195122`.
- The section 7 probability-recovery and Monte Carlo criteria.

Any additional full-path loss is reported separately; it does not inherit this conditional-gate oracle. P2 is not modified to eliminate this counterexample.

## 9. Reserve position

**Priority is S1, then this frozen P2.** Development is not permission to register; every registration returns separately to Max (`d1803.md:3–8`; `registration-commitments.md:45`).

| Event | Fixed action |
|---|---|
| Both pass their frozen development requirements | Bring S1 first. Keep P2 in reserve. |
| Any frozen S1 development requirement fails | Publish the failure. S1 is ineligible under that implementation. Bring P2 to Max only if P2 passes all its own frozen requirements. |
| Max declines to register S1 | Bring qualified P2 separately, unless Max’s ruling also stops successor registration generally. |
| S1 registration remains undecided | Do not register P2 in parallel or bypass that decision. |
| Registered S1 receives published terminal **FAIL** on its earnings admission gate | Bring qualified, unchanged P2 to Max as the next successor. Use only that published terminal outcome to trigger the reserve. |
| Registered S1 receives published **PASS** | Leave P2 in reserve. Do not register it to seek a better score. |
| S1 is invalid, inconclusive, withdrawn, or blocked | No automatic switch. Bring the published status to Max for an explicit ruling. Do not infer failure or exhaustion from diagnostics. |
| P2 fails its own development requirements | Publish that failure; it is not eligible for registration under this specification. |

Same-specification implementation repairs may correct demonstrated bugs, with failures and repairs recorded. They cannot change features, estimators, fixtures, seeds, statistical criteria, or the reserve ordering. No stochastic reruns are selected to obtain a pass. Once the P2 reserve trigger has brought it to Max, a repaired S1 does not silently reverse that decision.

**Attempt accounting:**

- Original v1 remains cumulative attempt 1.
- If S1 is the first registered successor, it is attempt 2.
- A registered S1 failure is **one failed registered successor**.
- P2 registered afterward is attempt 3. If it also fails, two independently justified registered successors have failed: declare `SUCCESSOR_EXHAUSTED` and pause the mechanism program.
- If S1 fails development or is declined before registration, P2 would instead be attempt 2 and the first registered successor. Development failures and declined registrations consume no registered attempt.
- Renaming, withdrawing a failed law, or changing a module name never resets the cumulative count.

These distinctions follow `registration-commitments.md:8–12` and `trackb-design-20260928.md:464–469`.

The reserve trigger may inspect only the published overall gate status. It may not inspect cells, gaps, directional discrepancies, diagnostic rankings, comparator distances, or partially completed results to choose or revise P2.

A future P2 registration must preserve v1, identify this dated hypothesis and specification, freeze the implementation commit and provenance, perform applicable seal rechecks, and carry **“Registered, one-shot, post hoc, not blind.”** Report all variants and attempts (`registration-commitments.md:14–20`; `trackb-design-20260928.md:378–388`).

P2’s default registration route retains the existing pinned floor and surface, explicitly disclosing untested transport of planning-dependent quantities. Recomputation would require separately prospective rescoping, rather than an adjustment after successor results (`registration-commitments.md:22–35`).

Candidate 3’s M6 certification does not transfer to P2. Before dependent admissions, Max must separately ratify P2’s M6-style validation sequence, criteria, and authorization. Exposed-window replay is regression evidence; no validation result may modify this law (`registration-commitments.md:37–43`; `p4-proposer-sol-out.md:189`).

**No choice in sections 1–8 changes before P2 registration. A substantive change is a newly recorded specification, not completion of this one.**

## 10. Degrees of freedom

The remaining prospective implementation and design choices are fixed as follows:

| Element | Fixed value |
|---|---|
| Relationship to S1 | Standalone on v1; no composition |
| Source scale | Raw nominal earnings |
| Gate population | Existing eligible boundary-observed pairs |
| Number of gates | One shared gate |
| Ordered predictors | `earnings`, `age_tp2`, `prior_positive`, `prior_missing` |
| Extra covariates/interactions | None constructed |
| Older lag | Exactly two years before source; one extra biennial state |
| Participation definition | Raw earnings strictly greater than `1e-6` |
| History lookup | Exact person/year left join from pre-age-filter `cutoff_panel` |
| Observed zero/tolerance-zero | `(0,0)` |
| Unavailable/NaN history | `(0,1)` |
| Available positive history | `(1,0)` |
| Negative/infinite older history | Whole-operation refusal; no row deletion |
| Outside-age prior | Use if otherwise available |
| Forward filling/interpolation | None |
| Pair dropping for history | None |
| First-step older field | `gen_earn_w4`, initialized from \(b-2\) |
| Later missing supported-person state | Preserve v1 refusal from \(b+4\) |
| Target labels and weights | Unchanged raw target and `weight_tp2` |
| Estimator/build/defaults | Exactly v1’s pinned factory/build; no upgrade or tuning |
| Gate draw | Four-feature classifier probabilities and existing cumulative selection rule |
| Legacy two-feature helper | Not used by P2 |
| Anchor participation routing | Removed |
| Anchor donor information/`q0` | Retained unchanged |
| Positive-law objects and settings | All unchanged, as enumerated in section 5 |
| Refresh | `q=.55`, `rho=−.60`, inherited operations |
| Random streams/timing | Inherited; no additional stream |
| Candidate/module/revision | Exactly section 6 |
| Signatures | Four-feature gate, history provenance, separate non-gate components |
| Development panels, seeds, sizes | Exactly section 7 |
| Recovery criteria and uncertainty | Exactly section 7; counterexample additions in section 8 |
| Counterexample and loss measure | Section 8; paired expected Brier loss |
| Registration priority and triggers | Exactly section 9 |
| Real-data development audit | None authorized here |
| Changes after results | None under this specification |

Mechanical coding choices must implement these semantics and pass the exact tests. Any choice that changes fitted populations, features, probabilities, randomness, support, or acceptance criteria requires a new specification.

## Declarations

I met **no B2 cell result or 2012/2014 gap**. The supplied brief’s overall non-admission statement was the only B2 outcome information used. No PSID microdata, prohibited score/ledger file, other checkout, prohibited evidence directory, or project issue/PR was accessed. No models or development tests were run, and no files were written.

The inventory below includes delegated reads and, conservatively, every file scanned by a delegated dependency-text search. Most search-only files were not substantively reviewed. Directory headings plus basenames identify every file.

Additional files outside the grouped source inventory:

```text
/Users/maxghenis/.agents/skills/gitnexus-exploring/SKILL.md
scripts/select_m6_qstar_train_only.py
pyproject.toml
```

```text
_review_context/:
b2-registration-rescoped.md, brief.md, d1803.md, p1-mechanism-out.md,
p2-evidence-out.md, p3-literature-out.md, p4-proposer-sol-out.md,
p4-proposer.md, registration-commitments.md, s1-spec.md,
trackb-design-20260928.md

src/populace_dynamics/:
__init__.py, artifacts.py, assembled_history_observer.py,
axiom_benefit_bridge.py, claiming.py, closed_cohort_history.py,
compact_cohort_history.py, contract.py, covered_wage_history.py,
disability_conversion.py, evaluation.py, forward_earnings_history.py,
household.py, mortality_observer.py, person_identity.py,
scenario_benefits.py

src/populace_dynamics/baselines/:
__init__.py, asfr.py, base.py, cbo2026_long_term.py, claim_tables.py,
common2026.py, fertility.py, interpolation.py, legacy.py, realized.py,
tr2026_intermediate.py, track_a.py

src/populace_dynamics/bridge/:
__init__.py, depletion_cut.py, depletion_cut_population.py,
depletion_cut_population_child.py, invented_population.py,
policyengine_us.py, population.py, population_summary.py

src/populace_dynamics/cohorts/:
__init__.py, age67.py, group_attributes.py, psid2010.py,
psid2010_epuf_fill.py

src/populace_dynamics/cola_track_a/:
__init__.py, adapters.py, benefits.py, config.py, invented.py,
mortality.py, opening.py, runner.py, statutory.py

src/populace_dynamics/data/:
__init__.py, asec_firm_size.py, births.py, cbo2026.py,
couple_earnings.py, cps_tenure.py, deaths.py, deployment_frame.py,
disability.py, employer_dc.py, epuf.py, family.py, family_income.py,
group_attributes_psid.py, historical_coverage_rule_validation.py,
household_composition.py, life_table.py, marriage.py, panels.py,
prior_year_labor_income.py, psid.py, psid_codebook_extraction.py,
psid_covered_earnings_registry.py, psid_job_context.py,
psid_job_context_registry.py, psid_missing_reason_authority.py,
psid_unit_authority.py, psid_unit_predicate_authority.py,
psid_unit_title_authority.py, relmap.py, sipp_jobs.py,
social_security_income.py, social_security_receipt.py, tr2008.py,
tr2026.py, transitions.py, u2_source_registry.py, ukhls.py

src/populace_dynamics/engine/:
__init__.py, accounting.py, accounting_history.py, assembly.py,
candidates.py, claiming.py, composition.py, di_entitlement.py,
di_entitlement_rates.py, disability.py, earnings_domain.py,
entrant_domains.py, entrant_schedule.py, forward_earnings.py,
loop.py, marital.py, panel_builders.py, refit.py, rng.py, steps.py,
support.py

src/populace_dynamics/estimates/:
__init__.py, adjusted_poverty.py, anchor_context_coordinator.py,
anchor_context_publication.py, anchor_context_registry.py,
anchor_context_rehearsal.py, anchor_context_report.py, career.py,
cola_age_profile.py, coordinator.py, epuf_fill.py, first_report.py,
group_breakdown.py, ledgers.py, lifetime_measures.py, parameters.py,
preparation.py, publication.py, runner.py, uniform_cut_tabulation.py

src/populace_dynamics/firms/:
__init__.py, banding.py, targets.py

src/populace_dynamics/fra68_track/:
__init__.py, benefits.py, config.py, reform.py, runner.py

src/populace_dynamics/graph/:
__init__.py, __main__.py, _compat.py, model.py, runtime.py,
synthetic.py, trajectory.py, trajectory_accounting.py

src/populace_dynamics/group_breakdowns/:
__init__.py, cola.py, common.py, fra68.py, min_benefit.py,
uniform_cut.py

src/populace_dynamics/harness/:
__init__.py, epuf_cells.py, epuf_fill_gate.py, epuf_fill_scoring.py,
epuf_gate.py, epuf_operator.py, epuf_run.py, holdout.py,
m6_candidate2_runner.py, m6_candidate3_runner.py, m6_cells.py,
m6_inputs.py, m6_population.py, m6_preflight.py, m6_projection.py,
m6_reporting.py, m6_runner.py, m6_schema_audit.py, m6_scoring.py,
metrics.py, moments.py, panel.py, views.py

src/populace_dynamics/min_benefit_track_m/:
__init__.py, careers.py, cohort.py, coverage.py, evaluation.py,
invented.py, invented_psid.py, pipeline.py, policy.py, rules.py,
specification.py, structure.py, tabulation.py, thresholds.py

src/populace_dynamics/models/:
__init__.py, couple_formation_sim_v1.py, couple_formation_sim_v2.py,
disability_hazard_sim.py, household_composition_sim.py,
household_composition_sim_v2.py, household_composition_sim_v3.py,
household_composition_sim_v4.py, household_composition_sim_v5.py,
household_composition_sim_v6.py, household_composition_sim_v7.py,
household_composition_sim_v8.py, household_composition_sim_v9.py,
transport_deployment_v1.py, transport_deployment_v2.py,
transport_deployment_v3.py

src/populace_dynamics/models/family_transitions/:
__init__.py, common.py, compatibility.py, evaluation.py, fitted.py,
registry.py, simulator.py

src/populace_dynamics/models/family_transitions/components/:
__init__.py, divorce.py, fertility.py, first_marriage.py,
first_marriage_support_aware.py, initial_states.py, remarriage.py,
spousal_age_gap.py, widowhood.py

src/populace_dynamics/models/household_composition/:
__init__.py, base_simulator.py, common.py, compatibility.py,
data.py, evaluation.py, fitted.py, registry.py, simulator.py

src/populace_dynamics/models/household_composition/components/:
__init__.py, child_attribution.py, cohabitation_overlay.py,
fertility_core_lift.py, household_size.py, legal_spouse_residual.py,
marital_core_adapter.py, multigenerational_occupancy.py,
nonfamily_bridge.py, parental_home_exit.py, skip_generation_state.py

src/populace_dynamics/ss/:
__init__.py, benefits.py, params.py, statutory_aime.py,
statutory_delayed_credit.py

src/populace_dynamics/track_a_v2/:
__init__.py, benefits.py, estimands.py, filing.py, histories.py,
invented.py, manifest.py, matrix.py, membership.py, protocol.py,
runner.py, structural.py, structural_inputs.py

src/populace_dynamics/track_b/:
README.md, __init__.py, arf.py, b2.py, equality.py,
gross_benefits.py, recompute.py, reconstructed.py, replay.py,
ret_grace.py, ret_ledger.py, ret_params.py, runner.py

src/populace_dynamics/track_b/parameters/:
__init__.py, ret_v1.yaml

src/populace_dynamics/uk/:
__init__.py, advance_year.py, dataset.py, demographic_ageing.py,
household_transitions.py, ons_rates.py

src/populace_dynamics/uniform_cut_track_u/:
__init__.py, diagnostics.py, invented.py, rows.py, runner.py

src/populace_dynamics/uniform_cut_track_u2/:
__init__.py, cohort.py, diagnostics.py, estimator.py, identity.py,
invented.py, loader.py, memo.py, parameters.py, rows.py, runner.py,
sources.py, tabulation.py
```