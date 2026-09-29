# Track B B1 v2: reconstructed reproduction registration draft

**Status: draft; no real-data computation has been performed for this build.**
**Prospective rule under Max's d571 ruling, dated 2026-09-28.** Post this
text as a new comment on issue #42 before invoking the command, with every
TO FILL field completed and the build and environment frozen.
The verification class is **reproduction**, with success restricted to
**reconstructed reproduction (weaker than bit-for-bit)**. This
registration freezes an earnings-only replay of M6 candidate 3, with annual
histories for 2014–2018. It changes no model law, fit boundary, population,
support rule, weight, threshold, or RNG address. It does not re-run the M6
acceptance gate or admit any new scientific claim.

## Exact command and source identity

Run from the clean B1 checkout with the candidate-3 fitting environment
installed at `scratch/track_b/baseline-f10cca5/.venv` under the separate
clean baseline checkout specified in "SSA revision: pinned environment".
Install this B1 checkout editable into that environment so its imported
runner resolves to the registered B1 source. Substitute only the two
placeholders below, both
**TO FILL**:

- `<NEW_ISSUE42_COMMENT_ID>` (**TO FILL**): the ID of the new issue #42
  comment that posts this registration.
- `<B1_BUILD_COMMIT>` (**TO FILL**): the full 40-character SHA of the
  reviewed B1 build commit.

```bash
env OMP_WAIT_POLICY=ACTIVE \
  LOKY_MAX_CPU_COUNT=8 POPULACE_FIT_N_JOBS=8 \
  POPULACE_FIT_PREDICT_WORKERS=8 OMP_NUM_THREADS=8 \
  OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 \
  VECLIB_MAXIMUM_THREADS=8 NUMEXPR_NUM_THREADS=8 \
  scratch/track_b/baseline-f10cca5/.venv/bin/python \
  scripts/run_track_b_b1.py \
  --registration-id <NEW_ISSUE42_COMMENT_ID> \
  --expected-commit <B1_BUILD_COMMIT> \
  --baseline-version reconstructed \
  --out scratch/track_b/b1_v2
```

The command sets the original thread environment. The inherited
runtime/source guard verifies these conditions before the input factory reads
PSID. The inherited factory also requires `POPULACE_DYNAMICS_PE_US_DIR` to
resolve to the installed, metadata-versioned policyengine-us `1.752.2`
parameter tree inside that baseline environment; the environment's package
and source-tree pins must already match the committed candidate-3 sidecar.
This prospective replay command preserves its registered thread settings.
Build-only pytest commands instead always set `OMP_NUM_THREADS=1` and
`POLARS_MAX_THREADS=1`; the delivery lane must not invoke this replay.

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
The baseline artifact and source bindings include the table below. Its eight
source and floor rows are the blobs at `f10cca5`. The two
`runs/gate_m6_candidate3_v1.json*` rows do not exist at `f10cca5`: they are
the blobs added by the candidate-3 verdict commit `65d151b0` (#283), a
descendant of `f10cca5`. All ten are unchanged at `81eee7b5`, the B1
build the review read, and in this revision. B1 checks the artifact and
sidecar hashes, and byte-compares the seven source rows with `f10cca5`.
**B1 does not check the `runs/m6_holdout_floors_v4.json` hash**: no code in
`src/populace_dynamics/track_b/` or `scripts/run_track_b_b1.py` reads it, so
that row records the value only.

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

## Exact equality and the distinct v1 historical-reference path

The v1 bit-for-bit pass rule requires exact equality for every seed and draw of
the **original per-person scored earnings, person-period support, F6 weights,
fit signatures, and RNG signatures**. Keyed person-period matching makes row
and column order immaterial; numeric values must match exactly, without
tolerances or rounding. Signature mapping keys match by exact type, so `1`
and `True` are different keys. A single person's changed earnings, weight,
support key, or signature is a mismatch. Empty or missing references cannot
pass. Aggregate agreement alone cannot satisfy this conjunction.

The build reconstructs the original scored path with the unchanged original
loop and compares its full person-level output with the copied loop. It also
compares fit signatures and all six committed earnings cells for every seed
and draw. It records the original and replay RNG address signatures. The
original side's RNG signature is sized by the harness's own
`PROJECTION_END_YEAR - 2014`, and its fit signature is the committed
candidate-3 lineage. The replay side uses `replay.RNG_N_PERIODS` and the
refit. Both loops receive the same fitted generator, so the fit comparison
repeats the registered-fit check rather than distinguishing the loops.
These are explicitly **reconstructed-original differential diagnostics**.

**The committed candidate-3 artifact does not contain archived person-level
scored earnings, support, weights, or original-run RNG signatures.** It
contains aggregate per-draw cells, fit signatures, and source/runtime
provenance. It also does not provide an archived raw-PSID hash manifest.
Reconstructing the original loop today does not establish equality to
unavailable historical person-level bytes: multiple different person-level
outputs can have the same aggregate cells.

**v1 rule.** Without an authenticated historical person-level reference, the
attempt records `BASELINE_REPLAY_MISMATCH` with reason
`historical_person_level_reference_unavailable`, whatever the differential,
fit, and aggregate diagnostics show. A fresh computation cannot become its
own historical reference. This build commits no reference hash, so the rule
governs the default `--baseline-version bit-for-bit` mode. That mode has no
route to admission until an authenticated original-run person-level reference
and RNG record are recovered and bound in a prospective registration. The
separately selected v2 rule below changes neither that requirement nor v1's
reported status. Its weaker admission must never be described as equality
to historical person-level output.

The runner also implements an optional `--historical-reference` flag. It is
**not part of the command registered here**, and v2 rejects the flag. The
v1 runner admits a reference
only if its bytes hash to `HISTORICAL_REFERENCE_SHA256`, a constant committed
in `src/populace_dynamics/track_b/runner.py`, and no command-line hash can
override it. This build commits `None`, so every reference is refused: the
attempt records the supplied path and the committed value and aborts with
`BASELINE_REPLAY_MISMATCH`. No operation can publish `REPRODUCED` without an
admitted reference. If original-run records are recovered, a new B1 build
commit must set that constant, and a prospective registration must pin that
commit and freeze the reference path and evidence of historical custody
before the flag is used. The supported manifest is
`track_b_b1_historical_reference.v1`, bound to the candidate-3 artifact hash,
with origin `historical_candidate3_run` and one record per seed/draw carrying
typed scored columns, fit signatures, and RNG signatures. An asserted
origin string is not evidence of historical custody. Exact agreement with
that reference, the original-loop differential, committed per-draw cells,
committed fit signatures, and input provenance is the pass conjunction;
missing, duplicate, extra, or altered references cannot pass.

Other mismatches retain full available diagnostics identifying the seed,
draw, person-period key, component, and expected/observed values or byte
signatures. The output never labels a mismatch or incomplete run a
reproduction, and v1 never admits an absent reference. Output includes the
annual histories,
per-seed/per-person comparison record, and provenance; mismatch records
admit no downstream B1 scope.

## Baseline definition: ruled v2 reconstructed reproduction

Max's ruling d571, **2026-09-28**, as supplied in the build brief:

> A new registered B1 version, **v2, "reconstructed reproduction"**, labelled weaker than §3.2's bit-for-bit. Its baseline is exact equality, with no tolerances, on four things:
>
> 1. **All 600 committed per-draw cells** (5 registered seeds × 20 draws × 6 cells) in `runs/gate_m6_candidate3_v1.json`, compared with the replay's per-draw cells.
> 2. **The committed fit lineage.**
> 3. **The original loop against the copy, person by person.**
> 4. **Provenance.** All registered provenance fields must be equal.

This registration adopts that rule only for the explicit
`--baseline-version reconstructed` mode, schema `track_b_b1.v2`:

1. `per_draw_cells`: compare each committed earnings cell with the copied
   loop's corresponding cell and the unchanged original loop's cell. Cover
   exactly seeds 0–4, draws 0–19, and the six registered earnings cells.
   Match by `(seed, draw, cell)`; compare floating-point bits without
   rounding or tolerances. Cell order is immaterial; missing, extra,
   duplicate or mistyped registered entries fail.
2. `fit_lineage`: compare the entire committed `lineage` record with the
   refit's lineage, including the original gate's `floor_run` and
   `floor_sha256` binding. Matching only selected fit signatures is
   insufficient. The floor binding records the pinned contract; it does not
   add a read or hash check of the floor artifact itself.
3. `person_level_differential`: run the unchanged `m6_projection` loop and
   the copied `track_b/replay.py` loop on the same population and fitted
   generator for each seed and draw. Require exact equality of scored
   person-period earnings, support, F6 weights, fit signatures and RNG
   signatures. Preserve the eight-period RNG registry. Keyed rows and
   named columns make their order immaterial; no person-period discrepancy
   is excused by aggregate agreement.
4. `provenance`: compare every field of the committed artifact's
   `provenance` and `runtime_identity` records and the environment sidecar's
   `environment.candidate3_gate_freeze` record. Require the separately
   checked SSA revision environment below, with no rewrite or mapping of
   `ssa_revision`.

Only the conjunction of these four exact checks, with no historical
person-level reference used, may produce `RECONSTRUCTED_REPRODUCTION` and
`admitted_scope = "reconstructed reproduction (weaker than bit-for-bit)"`.
Any failed or unevaluated condition requires `BASELINE_REPLAY_MISMATCH`,
`admitted_scope = "none"`, and diagnostics naming the affected condition.
Publish aborts and partial evidence too. The no-reference guard must
rederive the checks from the registered records and published evidence;
reported pass booleans alone cannot authorize this claim. It must refuse
`REPRODUCED` and every other admission without an authenticated historical
reference. Only v1's distinct committed-hash path may yield `REPRODUCED`.

The implementation is in `track_b/reconstructed.py:183` (cells), `:302`
(lineage), `:843` (original/copy pair), `:887` (person-level differential),
`:555` and `:635` (registered provenance), `:757` (conjunction), and `:1166`
(guard), under `src/populace_dynamics/`. These are rules for a prospective
attempt; this draft reports no real-data pass or mismatch.

The [v2 amendment](track_b_b1_v2_amendment.md) records the chosen reading of
the design: v2 substitutes a weaker, explicitly labelled replay prerequisite
for B2 under d571; it does not satisfy the design's literal bit-for-bit B1
claim. A v2 mismatch still stops B2 and all work built on that replay.

## Inherited certification boundary: full disclosure

> **Candidate 3 records a valid M6 pass; it certifies nothing about mortality drift.** The artifact records four passing seeds, q=0.55 and rho=−0.6. Fits use data through 2014; gated demographic flows cover 2015–2019 and earnings cover 2016/2018. The 2020–2022 window is diagnostic only. Certification is conditional on prior structural and same-holdout surface selection. The v4 point estimate `p_gate=0.9018301` clears 0.90 by 0.0018301, but its clearance is not statistically resolved: the reported jackknife SE is approximately 0.013–0.019. Synthesized support, redrawn initial states and endogenous widowhood require the decision-5 successor gate.

B1 supplies no new validation, no mortality certification, no 2030 forecast,
no ages-65–69 extension, no RET effect, and no validated monthly timing. The
full disclosure above accompanies every inherited-pass claim.

## SSA revision: pinned environment

V2 chooses ruling option **(a): run in the pinned environment where the
unchanged loader itself reports `f10cca5`**. There is no committed mapping,
normalization, truncation of a different abbreviation, or override of the
recorded provenance value.

The exact calculation is `subprocess.run(["git", "log", "-1",
"--format=%h"], cwd=root, capture_output=True, text=True,
check=True).stdout.strip()`. The loader resolves `root` from the explicit
argument, `POPULACE_DYNAMICS_PE_US_DIR`, or its default, and records
`"unknown"` if Git fails. It stores the result as `pe_us_revision`
(`src/populace_dynamics/ss/params.py:187–193`, `:218`, `:308–326`).
`src/populace_dynamics/harness/m6_inputs.py:391` and `:417` copy that value
into `external_details.ssa_revision`. Thus the recorded value identifies
the Git repository discovered from the parameter directory. An installed
wheel beneath a dynamics checkout can report that checkout's abbreviated
HEAD; the value is not a policyengine-us package commit obtained from
package metadata.

Before registration, construct the prospective environment as follows:

1. Create a separate, workspace-local clone at
   `scratch/track_b/baseline-f10cca5`, checked out at the full commit
   `f10cca5457b16d12b9284d00628e7331871f23e7`. Keep tracked files and the
   index clean. Set that clone's local `core.abbrev` to `7`.
2. Install the frozen candidate-3 runtime and policyengine-us `1.752.2`
   into a virtual environment physically inside that clone at `.venv`.
   Install the reviewed B1 checkout editable in that environment; leave the
   baseline clone's tracked source unchanged. Retain every runtime,
   source-tree, package-location and thread pin of the original environment
   guard (`harness/m6_candidate3_runner.py:619–725`). This setup changes no
   inherited source or environment-comparison rule.
3. Set `POPULACE_DYNAMICS_PE_US_DIR` to the installed distribution's parent
   directory containing `policyengine_us`, inside that environment. The
   inherited factory requires its resolved SSA tree to be the tree from
   metadata-versioned policyengine-us `1.752.2`
   (`scripts/registered_m6_inputs.py:133–178`). Use no `GIT_*` environment
   variables, so repository discovery cannot be redirected.
4. Before any input factory or PSID access, require the unchanged Git
   command to return exactly `f10cca5`, its discovered full HEAD to equal
   the full baseline SHA above, and its tracked worktree and index to be
   clean. Record the resolved package root, discovered repository,
   abbreviation configuration and empty Git environment. A different
   abbreviation, including `f10cca54`, fails; do not shorten it after the
   fact. Reprobe before accepting a result and require the recorded probe
   to remain identical.

The v2 checks are `track_b/reconstructed.py:584–632`, `:698–739`,
`:947–954`, and `:1127–1146`, under `src/populace_dynamics/`. The frozen
environment check still runs first. This resolves how `ssa_revision` must
be reproduced; it makes no claim that a real replay has met this or any
other condition.

## Build-only verification

The delivery lane runs only invented-input pytest/Hypothesis checks. These
include independent mutations of a cell, lineage field, person-period value
and provenance field; conjunction success; detection of any one changed
cell among all 600; cell-order invariance; unchanged v1 behavior; and refusal
of forged no-reference claims. Existing checks cover original/copy equality,
person-period ordering, determinism, exclusive outputs, the committed
historical-reference hash, typed signatures and fallback publication. Run
all Track B tests and the birth-evidence seal with `OMP_NUM_THREADS=1
POLARS_MAX_THREADS=1`. Minimize and execute counterexamples before calling
them bugs. The delivery lane does not invoke the staged-PSID factory. This
file is a draft for the later registered real-data attempt, not a record of
an executed replay.
