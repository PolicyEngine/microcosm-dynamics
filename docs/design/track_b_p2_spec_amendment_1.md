# P2: specification amendment 1

Dated 2026-10-23. This records a new development-test specification version amending **only T4** of `_review_context/P2-SPEC.md`, whose verified SHA-256 is `df5df7f2de3992a95d24ae49cbc2924c6c415d9316472c7bdb0d75f254769681`.

Below, `engine/` means `src/populace_dynamics/engine/`, and `review/` means `_review_context/`.

## 1. T4 finding

**The stop report’s finding is verified.**

T4 prescribes all-positive earnings and demands exact equality of P2 and unchanged-v1 participation probabilities, signs, and complete paths (`review/P2-SPEC.md:247–255`).

The conflict follows from the code:

1. v1 constructs its estimator with only `seed`, retaining its defaults, and fits raw target earnings (`engine/forward_earnings.py:979–987`, `:1074–1080`).
2. The pinned estimator’s zero tolerance is `1e-6`. All-positive target support above that threshold produces `POSITIVE_ONLY`; fitting that regime stores `gate=None` (`review/pinned-populace-fit-qrf.py:89`, `:134–147`, `:1360–1368`).
3. The pinned fitted wrapper has no `draw_sign` method. Consequently, v1’s helper takes its `_target_models` branch and unconditionally calls `model.gate.predict_proba(...)` ([`forward_earnings.py:1168–1179`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/src/populace_dynamics/engine/forward_earnings.py:1168)).
4. Both v1 generation interfaces reach that helper for positive-anchor persons (`engine/forward_earnings.py:1780–1791`, `:1961–1972`).

Thus unchanged v1 raises `AttributeError` at its first even-year participation query. Its ordinary complete reference path does not exist on this fixture.

I choose **the direct-law reference**, retaining exact probability, sign, and complete-path comparisons. The pinned model’s ordinary prediction explicitly handles `POSITIVE_ONLY` without a classifier (`review/pinned-populace-fit-qrf.py:980–990`). Its participation probability is therefore exactly one. Separately fitted v1 non-gate objects remain available: its fit-signature code explicitly tolerates `gate=None` (`engine/forward_earnings.py:1235–1239`).

Adding a zero target could make v1 fit a classifier, but would change the all-positive premise. It would also leave exact equality between two-feature and four-feature fitted classifiers unestablished. The direct-law reference preserves T4’s purpose without changing its fixture or replacing exact equality with statistical agreement.

## 2. Full replacement text

Replace the entire existing T4 subsection with:

### T4 — Exact always-positive neutrality

Use the full-law fixture with every amount positive and NAWI equal to one. Additionally omit the \(b-2\) row for persons with `i%8 == 0`. Retain the fixed persons, waves, amounts, fit seed, projection roots, full-anchor sorted ordinals, eight original annual period coordinates, and comparison horizon through \(b+8\).

Fit P2 with the frozen pinned estimator. Separately fit unchanged v1 on the identical input to obtain reference non-gate objects. For this all-positive target support, the pinned estimator records `POSITIVE_ONLY` and fits no participation classifier. Its effective participation distribution is the point mass on sign `+1`.

Require P2’s effective positive-participation probability to equal exactly `1.0` and its sign to equal exactly `+1` at every modeled even-year query, including first-step queries with unavailable older history.

Require exact equality of complete earnings paths under common draws against a test-local direct evaluator of the inherited always-positive law. Construct that reference from the separately fitted v1 non-gate objects. Preserve the inherited initialization, domain treatment, odd-year carry, person and period addressing, substreams, donor calculations and branch order, marginal mapping, wage index, candidate 3 refresh settings and frame updates, and even-year lag rolling. Generate the prescribed gate-uniform array, then use deterministic positive signs. Obtain no expected path, probability, or sign from P2’s generator or query helper.

This reference evaluates the law directly; it does not call unchanged v1’s unsupported `gate=None` sign-query path or replace either fitted estimator. Compare complete earnings paths and applicable frame updates exactly, including shapes, ordering, and missing-value masks.

**Mutation:** force nonparticipation whenever `prior_missing==1`.

**Prediction:** correct P2 agrees exactly with the direct-law probabilities, signs, and complete paths. The mutation breaks first-step probability, sign, and path equality for affected persons. This covers the proposer’s always-positive case (`p4-proposer-sol-out.md:173`).

## 3. Audit of every test and mutation

“Runs as written” means the requirement is executable by the prospective implementation. It does **not** mean its assertions have passed.

The unchanged recovery protocol is internally consistent: `4 + 3×8 + 8 = 36` oracle assertions, five scenarios supply 40 probes per replicate, and `32×40×2 = 2560` matches its Hoeffding factor (`review/P2-SPEC.md:179–191`). The pinned wrapper accepts the specified weights, retains its default forests and classifier, and supports the stated estimator seeds (`review/pinned-populace-fit-qrf.py:219–227`, `:1032–1097`, `:1370–1379`, `:1427–1428`).

| Test or mutation | Status | Reason and citations |
|---|---|---|
| **T1** | runs as written | Hand-table and refusal cases can exercise feature construction directly. Existing cutoff, exact pair construction, and initial history maps provide the references. Invalid-history refusal is distinct from pair equality on valid inputs. `review/P2-SPEC.md:195–201`; `engine/forward_earnings.py:562–589`, `:1021–1035`, `:1067–1068`, `:1111–1117`. |
| **T2** | runs as written | The actual constructor and pinned wrapper can fit the gate experiment without donor construction. Within one v1 anchor route, matched current-earnings/age queries have identical predictor arrays, so their probabilities can be compared exactly. `review/P2-SPEC.md:179–220`; `engine/forward_earnings.py:1074–1091`, `:1173–1179`; `review/pinned-populace-fit-qrf.py:1332–1379`. |
| **T3** | runs as written | Constant age 40 is admitted; all persons have boundary observations. The shared and zero-anchor fits use the prescribed pairs and weights. The stated endpoint-selected oracle matches pooled exact two-year transitions for each length. `review/P2-SPEC.md:222–245`; `engine/forward_earnings.py:562–589`, `:1021–1035`, `:1055–1091`. |
| **T4** | **amended** | Unchanged v1 cannot query its absent classifier. The replacement retains the fixture and exact comparisons using the direct-law reference. `engine/forward_earnings.py:1168–1179`; `review/pinned-populace-fit-qrf.py:1360–1368`. |
| **T5** | runs as written | The mixed fixture supplies both target classes in both v1 gates and positive-pair support in every age bin. Non-gate construction and component signatures support the requested exact comparisons. `engine/forward_earnings.py:1050–1053`, `:1081–1117`, `:1281–1343`. |
| **T6** | runs as written | Missing first-step history and future-row perturbations are expressly requested. Cutoff and NAWI construction exclude future information; initialization, rolling, and the already-specified sibling resume adapter permit the clock and restart checks. Interface applicability is explained below. `review/P2-SPEC.md:276–287`; `engine/forward_earnings.py:1021–1048`, `:1437–1463`; `engine/steps.py:337–355`; `engine/rng.py:61–83`, `:158–169`. |
| **T7** | runs as written | This is a conditional gate experiment with v1’s actual asymmetric routing. Its benchmark mutation is executable. `review/P2-SPEC.md:291–297`, `:303–335`; `engine/forward_earnings.py:1780–1803`. |
| **Section 8 counterexample** | runs as written | Omitting \(b-2\) prevents the exceptional boundary transition from entering the exact pair join. Ordinary histories train the gates; the anchor identifies v1’s routing population. Invented-input enumeration reproduces the stated risks and loss. `review/P2-SPEC.md:303–335`; `engine/forward_earnings.py:562–589`, `:1081–1091`, `:1780–1803`. |
| T1: inner-join prior history | runs as written | Required absent-history cases expose deleted pairs against the separately constructed v1 pair population. `review/P2-SPEC.md:197–199`; `engine/forward_earnings.py:562–589`. |
| T1: encode missing as `(0,0)` | runs as written | The required hand tables distinguish unavailable history from observed zero. `review/P2-SPEC.md:74–80`, `:195–199`. |
| T1: use age-filtered history | runs as written | The expressly required available outside-age observation distinguishes lookup before and after age filtering. `review/P2-SPEC.md:197–199`; `engine/forward_earnings.py:1021–1035`. |
| T1: change `>` to `>=` | runs as written | The exact-threshold and `nextafter` probes distinguish the operators. The pinned positive label uses strict `>`. `review/P2-SPEC.md:195–199`; `review/pinned-populace-fit-qrf.py:1381–1386`. |
| T2: remove older participation | runs as written | The estimator can omit that predictor while the query constructor supplies its unused zero position. This removes distinctions required by the four recovery assertions. `review/P2-SPEC.md:207–218`; `review/pinned-populace-fit-qrf.py:1332–1354`, `:1373–1379`. |
| T3: fit and route P2 using only zero-anchor persons | runs as written | This constructs the endpoint-selected population against ordinary-transition assertions. `review/P2-SPEC.md:231–245`; `engine/forward_earnings.py:1081–1090`. |
| T4: force missing-history nonparticipation | runs as written | The instruction is retained unchanged within amended T4. Its prescribed omissions create first-step queries whose required probability is exactly one. `review/P2-SPEC.md:249–253`; `engine/forward_earnings.py:1444–1463`. |
| T5: history-complete donor inputs | runs as written | The oldest supplied source wave lacks preceding history. Filtering it removes genuine donor rows; the original fixture already discriminates this mutation. `review/P2-SPEC.md:168–177`, `:270`; `engine/forward_earnings.py:771–808`, `:847–900`. |
| T6: read `gen_earn_w2` as older history | runs as written | Mixed and unavailable-history cases distinguish these fields. `engine/forward_earnings.py:1733–1737`, `:1916–1922`; `engine/steps.py:337–355`. |
| T6: admit post-boundary fit rows | runs as written | Step 3 explicitly supplies future-row perturbations, including additions. Correct fitting excludes them before constructing fitted state. `review/P2-SPEC.md:280`; `engine/forward_earnings.py:1021–1048`. |
| T6: admit realized future NAWI | runs as written | Step 3 explicitly changes post-boundary values. Correct normalization uses the frozen projection afterward. `review/P2-SPEC.md:280`; `engine/forward_earnings.py:422–483`. |
| T6: omit restart `gen_earn_w4` | runs as written | The older field is required and read by both interfaces; its loss causes refusal or unequal resumed behavior. `engine/forward_earnings.py:1719–1735`, `:1905–1919`. |
| T6: reset period indices | runs as written | Original period coordinates enter the RNG address and are already required in the restart state. `review/P2-SPEC.md:283`; `engine/rng.py:61–83`. |
| T7: use v1’s shared gate for zero anchors | runs as written | This removes actual asymmetric routing. Analytic enumeration gives mutated-v1 risk `.1476`, making P2-minus-mutated-v1 loss approximately `−.0224780487804878`, reversing the required comparison. `engine/forward_earnings.py:1780–1803`; `review/P2-SPEC.md:295–297`, `:303–335`. |

Three execution details require care but no amendment:

- **T1’s special histories:** construct feature-level cases without requiring invalid inputs to complete an estimator fit. Missing upstream reasons may already be represented by omission, as T1 states.
- **T6’s interfaces:** `generate` requires `rho=None`, whereas `generate_with_frame_updates` requires bound rho (`engine/forward_earnings.py:1686–1693`, `:1890–1897`). “Identical applicable state” permits testing the same feature rule under each interface’s supported binding. It does not require interchangeable calls or equal full-law outputs across bindings. Candidate 3’s full-path and restart checks retain `q=.55`, `rho=−.60`.
- **Projection roots:** the registry uses `draw_seed = 5200 + draw_index`; roots `6200,…,6219` therefore correspond to draw indices `1000,…,1019` (`engine/rng.py:57–67`). This preserves the specified seeds.

Small invented-input checks confirmed structural support for the mixed fixture and the section 8 arithmetic. No fitted development experiment was run. Any subsequent recovery, loss, exact-equality, or mutation failure remains a test failure; it does not authorize changed seeds, sizes, tolerances, or estimators.

## 4. Unchanged specification and law

**Sections 1–6 and 9–10 are unchanged. P2’s law is unchanged.**

Section 8, T1–T3, T5–T7, and every mutation instruction are unchanged. Only T4’s unavailable executable-v1 reference is replaced. Its fixture, seeds, sizes, horizon, exactness requirement, and mutation are retained.

## 5. Declarations

I met **no B2 cell result or 2012/2014 gap**, including through delegated review. No PSID microdata, prohibited checkout or evidence directory, prohibited score/ledger file, project issue/PR, or web source was accessed. No files were written.

Every file opened, including delegated reads:

- [`_review_context/P2-SPEC.md`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/_review_context/P2-SPEC.md)
- [`_review_context/p2-build-stop-report.md`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/_review_context/p2-build-stop-report.md)
- [`_review_context/pinned-populace-fit-qrf.py`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/_review_context/pinned-populace-fit-qrf.py)
- [`_review_context/d1803.md`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/_review_context/d1803.md)
- [`pyproject.toml`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/pyproject.toml)
- [`src/populace_dynamics/engine/forward_earnings.py`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/src/populace_dynamics/engine/forward_earnings.py)
- [`src/populace_dynamics/engine/candidates.py`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/src/populace_dynamics/engine/candidates.py)
- [`src/populace_dynamics/engine/earnings_domain.py`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/src/populace_dynamics/engine/earnings_domain.py)
- [`src/populace_dynamics/engine/steps.py`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/src/populace_dynamics/engine/steps.py)
- [`src/populace_dynamics/engine/rng.py`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/src/populace_dynamics/engine/rng.py)
- [`src/populace_dynamics/engine/loop.py`](/Users/maxghenis/PolicyEngine/_trackb-reviews/b2-successor-p2-amend1-20261023/root/src/populace_dynamics/engine/loop.py)
- [`/Users/maxghenis/.agents/skills/gitnexus-exploring/SKILL.md`](/Users/maxghenis/.agents/skills/gitnexus-exploring/SKILL.md)