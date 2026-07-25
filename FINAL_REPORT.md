# Amendment 2 Birth Evidence Reducer — Final Report

## Result

The measurement reducer is complete and committed. It reads registered inputs
without mutating them, uses the production candidate-3 and career/ledger paths,
fails closed on repository and parameter identity, and writes one canonical
JSON artifact.

| Identity | Value |
|---|---|
| Production master | `daf3ff5978de5137ba50490f78ac52890291a399` |
| Draw | `0` |
| Root seed | `5200` |
| Artifact schema | `first_estimates_birth_evidence.v1` |
| Artifact bytes | `23,392` |
| Artifact SHA-256 | `d818a36ba6ed5d7dbb45e1f0a92f5d2c3ac6577744c0df35df22b2d11ca03cad` |
| policyengine-us | `1.752.2` |
| Parameter bundle SHA-256 | `6b350ba5c1fd30fd9272545fa2a145b068a776cb30e2b0bcb6498e0505bf2782` |
| Consumed policyengine-us SHA-256 | `e89a1fa01c3348d68f2c10eee0d572a62495b3e524dc1d39b30bc4f0d6ecec9d` |
| Parameter-tree Git revision | `955c6cb` |

Produced files:

- `scripts/first_estimates_birth_evidence.py`
- `runs/first_estimates_birth_evidence_draw0.json`

No requested measurement section was impossible. The permitted, hash-checked
diagnostic pickle was used for the committed artifact. The approximately
55-minute cache-free regeneration path is implemented but was not executed;
it calls `coordinator._load_registered_input_plan`, resolves the registered
contract, holds `coordinator._registered_scripts_path` over the production
candidate-3 prefix, runs the requested real draw, and supplies clones only to
satisfy the production driver's 20-wrapper contract.

## Verified source law

The corrected clause-3 coordinate is:

```text
birth_year = seed.year - seed.age
           = (anchor_wave - 1) - collection-wave age
```

This is not `anchor_wave - age`. In `m6_cells.py`, `SEED_WAVE` is 2015 and
`EARN_ANCHOR_YEAR` is 2014. In `m6_population.py`, the seed builder states that
`year` is the reference year immediately before the anchor interview while
`age` is the realized collection-wave age, then assigns
`year = anchor_wave - 1`. It explicitly resets the initial 2015 slice to
`EARN_ANCHOR_YEAR` 2014. Therefore:

- the initial 2015 anchor uses `2014 - age`;
- scheduled 2017 entrants use `2016 - age`;
- scheduled 2019 entrants use `2018 - age`.

`anchor_wave` is the person's earliest gated start-wave interview with
presence and positive weight. PSID age codes 2–125 are treated as actual
collection-wave ages; code 1 is the coarse newborn category and remains
unresolved; 999 or missing remains unresolved. Derived birth years span
1914–2016 and all satisfy the asserted [1889, 2022] bound.

Clause 3 is draw-invariant by construction: it reads the initial and scheduled
seed frames built before projection mortality and RNG and never reads a
trajectory row.

### Source counts

| Population | exact_marriage | inferred_period_age | synthetic_native | derived_projection_age | unresolved | Total |
|---|---:|---:|---:|---:|---:|---:|
| Initially unresolved by clauses 1–2 plus synthetic | 0 | 0 | 0 | 4,077 | 2,315 | 6,392 |
| Whole report population | 9,673 | 13,727 | 690 | 4,077 | 2,315 | 30,482 |

The 6,392-person seed-code disposition is 4,077 codes in 2–125, 2,298
code-1 infants, and 17 code-999-or-missing sentinels.

## Stage-A-respecting funnel

Among the 276 raw claim-year carriers that were unresolved before clause 3,
the production Stage-A partition is:

| DI class | Count |
|---|---:|
| `di_conversion` | 0 |
| `di_unknown` | 190 |
| `non_di` | 86 |

Only the 86 `non_di` people are true Stage-B candidates. Their production
origin split is 69 `opening_backfill` and 17 `modeled_award`. All 86 are
outside the earnings domain and land at the first ordered Stage-D outcome,
`excluded_domain_incomplete`.

The canonical funnel contains 3,083 candidates, of whom 2,784 are
domain-resident. Candidate births comprise 2,806 clause-2 inferred, 191 exact,
and 86 clause-3 derived people. Canonical origins comprise 1,588 opening
backfills and 1,495 modeled awards.

## Birth ±1 inclusion sensitivity

Only imprecise age-derived birth coordinates were perturbed:
`inferred_period_age` and `derived_projection_age`. Exact and synthetic birth
coordinates were held fixed. Each coordinate reruns the production inclusion
path, including the opening-stock PMF lookup at `birth + 62`, person-keyed
draw, operative claim year, career assembly, and ordered Stage D.

| Ordered Stage-D outcome | Baseline | Birth−1 | Birth+1 |
|---|---:|---:|---:|
| Included | 1,514 | 1,520 | 1,240 |
| Domain incomplete | 299 | 299 | 299 |
| Pre-1979 eligibility | 1 | 1 | 0 |
| Empty span | 0 | 0 | 0 |
| Chronology inconsistent | 67 | 23 | 623 |
| Low coverage | 1,202 | 1,240 | 921 |

Stage-C coordinate changes confirm that the opening-stock path was actually
rerun:

| Coordinate changed from baseline | Birth−1 | Birth+1 |
|---|---:|---:|
| Operative claim age | 81 | 88 |
| Operative claim year | 1,488 | 1,488 |
| Schedule year | 1,133 | 1,057 |

Predicate flips are counted only if both the baseline and alternative
coordinates reach that predicate in ordered Stage D.

| Predicate | Birth−1 flips | Birth+1 flips | Flip directions | Inclusion-changing | Distinct people | Source of all nonzero effects |
|---|---:|---:|---:|---:|---:|---|
| Domain | 0 | 0 | 0 | 0 | 0 | — |
| Eligibility era | 0 | 1 | 1 | 1 | 1 | clause 2 |
| Nonempty span | 0 | 0 | 0 | 0 | 0 | — |
| Chronology | 44 | 556 | 600 | 294 | 600 | clause 2 |
| Coverage | 10 | 5 | 15 | 15 | 15 | clause 2 |

Final inclusion changes total 26 directions under birth−1 and 284 under
birth+1: 310 directions across 304 distinct people, all clause-2 dated.

## Benefit-ledger sensitivity

The dollar cohort is fixed at the 1,440 claimants who are included at the
unperturbed coordinate and consume a clause-2 birth. Each variant uses its
production inclusion rerun, filters back to that fixed cohort, and calls
`ledgers.build_benefit_ledger` with the validated full-actual parameter stack.
A cohort member excluded under a perturbation has an empty payment window and
zero variant contribution; newly included people outside the baseline cohort
do not enter.

| Metric | Birth−1 | Birth+1 |
|---|---:|---:|
| Retained after inclusion rerun | 1,430 | 1,161 |
| Excluded after inclusion rerun | 10 | 279 |
| Payment-window membership changed | 10 | 285 |
| Benefit factor changed at fixed baseline claim age | 489 | 523 |
| Weighted annualized benefit delta | -48,719,150,245.19971 | -318,199,228,631.9995 |

Across both directions, 289 distinct people change payment-window membership
and 598 distinct people change benefit factor at fixed claim age.

Per-year weighted annualized nominal-dollar deltas, summed across both
production origin rows:

| Year | Birth−1 delta | Birth+1 delta |
|---|---:|---:|
| 2015 | -5,774,126,794.799988 | -6,462,970,631.999939 |
| 2016 | -5,770,825,302.0 | -13,040,277,794.399963 |
| 2017 | -5,890,085,196.0 | -25,631,953,778.399963 |
| 2018 | -5,886,225,273.599976 | -35,250,566,970.0 |
| 2019 | -6,206,463,500.400024 | -41,470,382,637.599976 |
| 2020 | -6,549,720,176.400024 | -54,951,360,816.0 |
| 2021 | -6,296,796,430.799988 | -63,639,868,833.599976 |
| 2022 | -6,344,907,571.200073 | -77,751,847,170.0 |

The reported total delta is perturbed aggregate total minus baseline aggregate
total. Summing the eight independently subtracted annual deltas gives
-48,719,150,245.20007 and -318,199,228,631.9998, respectively. The JSON
records the binary-float reconciliation residuals exactly:
-0.0003662109375 and -0.00030517578125 dollars.

## Oracle reconciliation

All 21 explicit oracle rows match. There is no delta to explain.

| Row | Ours | Oracle | Match |
|---|---:|---:|:---:|
| Clauses 1–2 plus synthetic unresolved | 6,392 | 6,392 | yes |
| Seed age codes 2–125 | 4,077 | 4,077 | yes |
| Seed age code 1 | 2,298 | 2,298 | yes |
| Seed age 999 or missing | 17 | 17 | yes |
| Corrected derived class | 4,077 | 4,077 | yes |
| Corrected unresolved class | 2,315 | 2,315 | yes |
| Raw claim-year carriers | 276 | 276 | yes |
| Raw carriers classified `di_unknown` | 190 | 190 | yes |
| New true Stage-B candidates | 86 | 86 | yes |
| New opening backfills | 69 | 69 | yes |
| New modeled awards | 17 | 17 | yes |
| Canonical candidates | 3,083 | 3,083 | yes |
| Canonical domain residents | 2,784 | 2,784 | yes |
| Era flip directions | 1 | 1 | yes |
| Empty-span flip directions | 0 | 0 | yes |
| Chronology flip directions | 600 | 600 | yes |
| Chronology inclusion-changing directions | 294 | 294 | yes |
| Coverage flip directions | 15 | 15 | yes |
| Overall inclusion flip directions | 310 | 310 | yes |
| Overall distinct people affected | 304 | 304 | yes |
| Baseline-included clause-2 claimants | 1,440 | 1,440 | yes |

## Judgment calls

1. **Seed coordinate.** I used `seed.year - seed.age`, not
   `anchor_wave - age`, because the production population builder explicitly
   places the seed frame in the reference year before the collection wave
   while retaining collection-wave age.
2. **Production inclusion transport.** The 2,315 residual unresolved people
   are noncandidates, but the master whole-population birth guard correctly
   rejects them. I therefore filtered trajectory and roster to the exact
   canonical 3,083-candidate universe, injected explicit candidate births via
   a two-column marriage frame, and called unmodified
   `career.build_career_inclusion`. Every candidate has a birth. Source labels
   are kept externally because this transport appears internally as exact.
3. **Perturbation scope.** Birth ±1 applies only to age-derived imprecise
   sources. Perturbing exact births would answer a different question and
   would add 45 chronology flips.
4. **Ordered predicates.** A predicate flip is counted only when both
   coordinates reach it. The extracted predicate sequence reconstructs each
   production outcome exactly for every candidate and all three coordinates;
   the reducer asserts this before counting.
5. **Dollar cohort.** The prompt says “included claimants of the unperturbed
   baseline,” so the 1,440-person cohort is fixed. Perturbed exclusions
   contribute zero and newly included outsiders are not added.
6. **Fixed-age factor.** The factor diagnostic holds each baseline claim age
   fixed and calls production `claiming.benefit_factor` at the perturbed birth
   year. It intentionally does not substitute an opening-stock claim-age
   redraw.
7. **Float totals.** Rather than hide a sub-mill summation-order difference
   behind a tolerance, the artifact records aggregate-total subtraction, the
   sum of annual deltas, and their exact residual.
8. **Cache and regeneration.** The artifact records that it came from the
   7,133,539,989-byte diagnostic cache with SHA-256
   `3ba147f7666ad77d8f7735969e4329fa7180cef091ad4ee326f35b2834a72068`.
   Cache-free regeneration is implemented and documented as approximately
   55 minutes, but was not run because the prompt expressly permits this
   cache.

## Commands and real output

The network fetch was attempted first and failed only because DNS was
unavailable:

```text
$ git -C /Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-entry8-impl fetch origin || true
fatal: unable to access 'https://github.com/PolicyEngine/populace-dynamics.git/': Could not resolve host: github.com
```

The cached reference and starting commit were then verified:

```text
$ git rev-parse origin/master
daf3ff5978de5137ba50490f78ac52890291a399
```

The reducer was run from this worktree with only the interpreter and parameter
files taken from the runner venv:

```text
$ POPULACE_DYNAMICS_PE_US_DIR=/Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-c3-runner/.venv/lib/python3.14/site-packages /Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-c3-runner/.venv/bin/python scripts/first_estimates_birth_evidence.py
WROTE runs/first_estimates_birth_evidence_draw0.json bytes=23392
DATA_PATH diagnostic_pickle_cache
ORACLE matched rows=21
A unresolved=6392 derived=4077 residual=2315
B raw_carriers=276 stage_b=86 canonical=3083 domain=2784
C chronology_flips=600 chronology_inclusion=294 coverage_flips=15 overall_directions=310 distinct_people=304
D cohort=1440 birth_minus_1_delta=-48719150245.199707 birth_plus_1_delta=-318199228631.99951
```

The final artifact was regenerated and compared to its prior bytes:

```text
WROTE runs/first_estimates_birth_evidence_draw0.json bytes=23392
DATA_PATH diagnostic_pickle_cache
ORACLE matched rows=21
A unresolved=6392 derived=4077 residual=2315
B raw_carriers=276 stage_b=86 canonical=3083 domain=2784
C chronology_flips=600 chronology_inclusion=294 coverage_flips=15 overall_directions=310 distinct_people=304
D cohort=1440 birth_minus_1_delta=-48719150245.199707 birth_plus_1_delta=-318199228631.99951
REPRODUCIBLE sha256=d818a36ba6ed5d7dbb45e1f0a92f5d2c3ac6577744c0df35df22b2d11ca03cad
CANONICAL exact=True trailing_newline=True bytes=23392
```

Formatting and lint:

```text
$ /Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-c3-runner/.venv/bin/python -m black --check -l 79 scripts/first_estimates_birth_evidence.py
All done! ✨ 🍰 ✨
1 file would be left unchanged.
$ /Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-c3-runner/.venv/bin/python -m ruff check scripts/first_estimates_birth_evidence.py
All checks passed!
```

The first pytest command accidentally resolved the runner venv's editable
source tree, as its traceback showed
`../sol-c3-runner/src/populace_dynamics/estimates/career.py`; it was not a
test of this branch:

```text
$ POPULACE_DYNAMICS_PE_US_DIR=... /Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-c3-runner/.venv/bin/python -m pytest -q tests/estimates/test_career.py tests/estimates/test_ledgers.py tests/estimates/test_sealed_preparation.py
5 failed, 28 passed in 5.79s
```

Binding `PYTHONPATH` to this worktree, which is also what the reducer does with
`sys.path`, produced the valid result:

```text
$ PYTHONPATH=/Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-entry8-impl/src POPULACE_DYNAMICS_PE_US_DIR=/Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-c3-runner/.venv/lib/python3.14/site-packages /Users/maxghenis/PolicyEngine/social-security-model-worktrees/sol-c3-runner/.venv/bin/python -m pytest -q tests/estimates/test_career.py tests/estimates/test_ledgers.py tests/estimates/test_sealed_preparation.py
.................................                                        [100%]
33 passed in 5.21s
```

The coherent implementation commits through the canonical artifact were:

```text
a5c9859 Add canonical birth evidence artifact
811aa54 Add production birth sensitivity reduction
cf4bf7c Add birth source and candidate evidence reducer
d33fa48 Record reducer path investigation
13ff214 Document birth evidence reducer progress
```

Every commit used `--no-verify`, and its message was immediately checked with
`git log -1 --format=%B`. Nothing was pushed.
