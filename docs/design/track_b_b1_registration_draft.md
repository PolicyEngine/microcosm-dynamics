# Track B B1: fixed-roster candidate-3 replay registration draft

**Status: draft; no real-data computation has been performed for this build.**
Post this text as a new comment on issue #42 before invoking the command.
The verification class is **reproduction attempted, not validation**. This
registration freezes an earnings-only replay of M6 candidate 3, with annual
histories for 2014–2018. It changes no model law, fit boundary, population,
support rule, weight, threshold, or RNG address. It does not re-run the M6
acceptance gate or admit any new scientific claim.

## Exact command and source identity

Run from the clean B1 checkout with the candidate-3 fitting environment
installed at `.venv`. Substitute only the new registration comment ID and the
reviewed B1 build commit below:

```bash
env OMP_WAIT_POLICY=ACTIVE \
  LOKY_MAX_CPU_COUNT=8 POPULACE_FIT_N_JOBS=8 \
  POPULACE_FIT_PREDICT_WORKERS=8 OMP_NUM_THREADS=8 \
  OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 \
  VECLIB_MAXIMUM_THREADS=8 NUMEXPR_NUM_THREADS=8 \
  .venv/bin/python scripts/run_track_b_b1.py \
  --registration-id <NEW_ISSUE42_COMMENT_ID> \
  --expected-commit <B1_BUILD_COMMIT> \
  --out scratch/track_b/b1_v1
```

The command sets the original thread environment. The inherited
runtime/source guard verifies these conditions before the input factory reads
PSID. The inherited factory also requires `POPULACE_DYNAMICS_PE_US_DIR` to
resolve to the installed, metadata-versioned policyengine-us `1.752.2`
parameter tree; the environment's package and source-tree pins must already
match the committed candidate-3 sidecar.

The output is an exclusive new directory. An existing output, a destination
under `runs/`, or a destination outside the checkout is not an alternative
output location for this registration. Publish the result and any abort or
mismatch diagnostics regardless of outcome; do not overwrite a result or
choose a new seed, draw, fit, population, or tolerance to rescue it.

The inherited source commit is
`f10cca5457b16d12b9284d00628e7331871f23e7`. Candidate 3 was registered under
issue #42 comment `5064153427`. That consumed comment ID is not the new B1
registration. The new runner records the B1 commit and its source hash
manifest and checks the frozen original source against the inherited commit.
The baseline artifact and source bindings include:

| Input or original source | SHA-256 |
|---|---|
| `runs/gate_m6_candidate3_v1.json` | `caf254925f44b27c1bd1131336055e27fbc311daec00b0050b2f9293a74e82cf` |
| `runs/gate_m6_candidate3_v1.json.env.json` | `6a2559d053ef9da9abbcfc710f9d45b91b749c918b4e48a0fbee3c54003cb38f` |
| `runs/m6_holdout_floors_v4.json` | `4cd2d01a9fd76064e701ae77a9226208cbae94d743f76f502d3d0a5f657d9523` |
| `scripts/registered_m6_candidate3_inputs.py` | `5ec52e487f8a2ce9bba45c895f619292565d3cbfb7777fc70e80d68380cf4b6a` |
| `scripts/registered_m6_candidate2_inputs.py` | `acb46989f0f412292e7ea4fb1a15acc5b3001ab6d45067d611e4d49f9d55ddbf` |
| `scripts/registered_m6_inputs.py` | `4b8e1e7d45f3a59db51c0ffcb728c1f41acd2b3dc53689ba104af2db54503a57` |
| `src/populace_dynamics/harness/m6_projection.py` | `49ff7ccc5e7e9d59e7b7e324e08e81c23e7ee433ca7b14fc5c9e71013658e569` |
| `src/populace_dynamics/engine/loop.py` | `936c11438f466f33d85e6033ae1d63f358a964f61942821ccbb5ec4aa10e639d` |
| `src/populace_dynamics/engine/steps.py` | `eedbf0d54b00e078c81c973a2b550c65648ea4941b755cfc85c4bc2421e5dfd0` |
| `src/populace_dynamics/engine/rng.py` | `5695c8e1d82bbde4ff3c81011524c453d9626be0aa500c560b462c73d1d3c747` |

The locked `gates.yaml`, `engine/loop.py`, `engine/steps.py`, and existing
`runs/*.json` remain unchanged. B1 has its own module, copied earnings loop,
runner, and output directory.

## Inputs, population, fit, and RNG

The sole input factory is
`registered_m6_candidate3_inputs:build_input_plan`; it is fixed in the runner
and has no CLI override. It delegates to the committed candidate-2 and M6
input adapters, retaining their dating and external-vintage restrictions:

- The staged PSID at `~/PolicyEngine/psid-data` supplies the inherited panels.
  Fit information is bounded at 2014. The registered exception for the 2015
  collection wave retains labor fields measuring reference-year 2014 and
  their registered family-panel covariates. Full inputs supply realized
  scoring support; they do not introduce future earnings into fitting.
- The earnings fit seed is `5200`, the engine candidate is
  `m6_candidate3_engine_v1`, and the family candidate is
  `m6_candidate2_registry_v1`. The earnings settings remain `q=0.55` and
  `rho=-0.6`.
- External inputs retain policyengine-us `1.752.2`, SSA-parameter vintage
  2014, the committed 2014-Supplement claiming reference, and the NCHS 2010
  mortality reference. Post-2014 realized NAWI is replaced with the
  inherited boundary projection.
- The reference runtime is the committed candidate-3 environment sidecar:
  Python `3.14.4`, NumPy `2.5.1`, pandas `3.0.3`, scipy `1.18.0`, scikit-learn
  `1.8.0`, quantile-forest `1.4.2`, populace-fit/frame `0.1.0`, and the pinned
  source trees and thread settings recorded there. This build's invented-data
  test environment is not evidence that those runtime pins have been met.
- Every gate seed `[0, 1, 2, 3, 4]` and draw index `0` through `19` is included:
  100 seed/draw pairs. Splitting remains the inherited 50% person-level
  side-A split. No failing seed or draw may be omitted.
- The registry retains **eight periods**, even though the recorder stops in
  2018. Period indices are 1–4 for 2015–2018; person ordinals are assigned
  across all side-A holdout IDs, including IDs outside the earnings domain.
  Candidate-3 module and substream codes remain unchanged.
- Each annual history retains the 2014 anchor and every 2015–2018 generated
  value on the fixed 2014 earnings roster. No mortality process removes
  people from this earnings replay. The original scored slice uses only
  2014/2016/2018 realized domain support and original F6 start weights.
  Intermediate annual records carry no newly admitted empirical scope.

## Exact equality and the historical-reference limitation

The B1 pass rule is exact equality, for every registered seed and draw, of
the **original per-person scored earnings, person-period support, F6 weights,
fit signatures, and RNG signatures**. Canonical person-period ordering makes
row order immaterial; numeric values must match exactly, without tolerances
or rounding. A single person's changed earnings, weight, support key, or
signature is a mismatch. Empty or missing references cannot pass. Aggregate
agreement alone cannot satisfy this conjunction.

The build reconstructs the original scored path with the unchanged original
loop and compares its full person-level output with the copied loop. It also
compares fit signatures and all six committed earnings cells for every seed
and draw. It records the original and replay RNG address signatures. These
are explicitly **reconstructed-original differential diagnostics**.

**The committed candidate-3 artifact does not contain archived person-level
scored earnings, support, weights, or original-run RNG signatures.** It
contains aggregate per-draw cells, fit signatures, and source/runtime
provenance. It also does not provide an archived raw-PSID hash manifest.
Reconstructing the original loop today does not establish equality to
unavailable historical person-level bytes: multiple different person-level
outputs can have the same aggregate cells.

Consequently, the command above records `BASELINE_REPLAY_MISMATCH` with
`historical_person_level_reference_unavailable` even if every available
differential, fit, and aggregate diagnostic agrees. A fresh computation
cannot silently become its own historical reference. B1 remains unadmitted
until an authenticated original-run person-level reference and RNG record
are recovered and bound in a prospective registration. Any amendment to
that evidentiary requirement must be explicit and reviewed before outcomes;
it is not an alternative pass rule in this registration.

The runner also implements optional paired flags `--historical-reference`
and `--historical-reference-sha256`. They are **not part of the command
registered here**. If original-run records are recovered, a prospective
registration must freeze their path, SHA-256, and evidence of historical
custody before using those flags. The supported manifest is
`track_b_b1_historical_reference.v1`, bound to the candidate-3 artifact hash,
with origin `historical_candidate3_run` and one record per seed/draw carrying
typed scored columns, fit signatures, and RNG signatures. An asserted
origin string is not evidence of historical custody. Exact agreement with
that reference, the original-loop differential, committed per-draw cells,
committed fit signatures, and input provenance is the pass conjunction;
missing, duplicate, extra, or altered references cannot pass.

Other mismatches retain full available diagnostics identifying the seed,
draw, person-period key, component, and expected/observed values or byte
signatures. The output never labels a mismatch, absent reference, or
incomplete run a reproduction. Output includes the annual histories,
per-seed/per-person comparison record, and provenance; mismatch records
admit no downstream B1 scope.

## Inherited certification boundary: full disclosure

> **Candidate 3 records a valid M6 pass; it certifies nothing about mortality drift.** The artifact records four passing seeds, q=0.55 and rho=−0.6. Fits use data through 2014; gated demographic flows cover 2015–2019 and earnings cover 2016/2018. The 2020–2022 window is diagnostic only. Certification is conditional on prior structural and same-holdout surface selection. The v4 point estimate `p_gate=0.9018301` clears 0.90 by 0.0018301, but its clearance is not statistically resolved: the reported jackknife SE is approximately 0.013–0.019. Synthesized support, redrawn initial states and endogenous widowhood require the decision-5 successor gate.

B1 supplies no new validation, no mortality certification, no 2030 forecast,
no ages-65–69 extension, no RET effect, and no validated monthly timing. The
full disclosure above accompanies every inherited-pass claim.

## Build-only verification

One additional provenance risk is retained without normalization: the inherited
SSA parameter loader obtains `pe_us_revision` using Git from the installed
parameter package directory. When that package lives inside a checkout's
virtual environment, Git may discover the containing dynamics checkout. The
registered artifact records `external_details.ssa_revision=f10cca5`; a B1
checkout may instead report its new commit. B1 compares the full recorded
input provenance exactly and will retain that discrepancy as
`BASELINE_REPLAY_MISMATCH`, even if the fitted earnings signature agrees.
Resolving this source-identity issue requires an explicit prospective
registration decision; the build does not change the frozen loader.

The delivery lane runs only invented-input pytest/Hypothesis checks: copied
versus original loop equality at the same addresses, row-order invariance,
single-person perturbation detection, determinism, and exclusive output
paths. It does not invoke the staged-PSID factory. This file is a draft for
the later registered real-data attempt, not a record of an executed replay.
