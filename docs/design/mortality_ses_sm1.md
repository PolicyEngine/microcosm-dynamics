# SM1: differential mortality mechanism

SM1 implements accounting conformance on invented inputs. It admits the
mechanism's identities only, with no empirical gradient claim. Authority:
the SM1 row of section 3.1, section 5.4, section 6 and section 7.1 of
design #558 at `2c19f5b6856b9da62924706067ef96f00f55012d`, approved with
its methodology by decision d1922 (23 October 2026). Q4 fixes baseline
expected deaths within age-sex-year cells, Q5 makes lifetime earnings the
primary dimension, Q6 holds the last observed gradient, and Q11 assigns
death alignment to SM.

The package is opt-in. No runner, registered run, configuration, baseline,
engine module or gate is changed. The coefficients and categories in every
new test are explicitly invented. SM2 supplies empirical definitions and
coefficients.

## Interfaces

All public objects are exported from `populace_dynamics.mortality_ses`.

- `RiskDimension(name, column, categories, reference,
  unclassified_values=())` declares one of `lifetime_earnings`, `education`
  and `race_hispanic_origin`. Categories are ordered, unique strings; the
  reference is one of them. All three dimensions must appear in the spec.
- `RelativeRiskSpec(dimensions, path, unclassified_rule="refuse")` validates
  complete category × sex × single-age coverage for every named table
  year. Coefficient tables contain `dimension`, `category`, `sex`, `age`
  and `log_relative_risk`. Inclusive `age_lower`/`age_upper` bands may
  replace `age`; expansion must cover ages 0–120 exactly once. The reference
  coefficient is zero. Each exponentiated coefficient and each combined
  log-additive risk must be finite and strictly positive.
- `CoefficientPath` requires ordered integer `years` and
  `coefficients(year) -> DataFrame`. `HoldLastCoefficientPath(table)` takes
  an additional `year` column, holds between named observations and after
  the final observation, and refuses years before the first. A custom
  path can supply a registered widening alternative without mechanism
  changes; every returned table is revalidated.
- `normalize_probabilities(q_base, relative_risk, fixed_mask,
  fixed_probabilities, cell_ids, weights, *, unclassified_counts=None)`
  returns `(probabilities, cell_log)`. Inputs are matching row vectors;
  cell IDs are `(year, sex, age)` triples. Weights are finite and
  nonnegative; zero-weight rows use the same factor but cannot determine
  it, and a cell whose positive-q free rows all weigh zero sets its
  factor with unit weights (see "Normalization and tolerance"). Inputs
  are never mutated.
- `DifferentialMortality(baseline, specification, *, weight_column,
  di_configuration=None)` exposes single-year `bands` and
  `__call__(frame, context) -> ndarray`. `evaluate(frame, context)` also
  returns its cell log. `weight_column=None` explicitly means equal
  person weights. The baseline must be callable with context, have
  single-year bands, and have no `probabilities` attribute. Neither does
  the new model: the DI adapter would otherwise call it without the year.
- `apply_differential_mortality(frame, context, rng, *, model,
  weight_column, death_log=None, cell_log=None)` is the frame step for a
  projection without the DI adapter. Its weight declaration must match
  the model's. It draws in stable `person_id` order using exactly
  `engine.steps.apply_mortality`'s batch or person-keyed mortality streams,
  then returns survivors in that order. Logs are keyed by projection year.

## Cells, fixed persons and unclassified attributes

Age must be a finite, nonnegative integer. When `birth_year` is present,
SM1 always refuses a row unless its uncapped `age` is exactly
`context.year - 1 - birth_year`, even when the DI spec disables its own
optional check. The cell uses `min(age, 120)`, the frame's sex and
`context.year`. This agrees with the baseline's age cap and with the DI
adapter's single-year cells, including ages over 120. Without birth year,
the supplied age is authoritative.

DI origin is exactly `di_entitled | (di_conversion_year.notna() &
(post_conversion_mortality == "di_origin"))`. The model accepts the
adapter's `DIEntitlementRates` or `DIEntitlementSpec`; callers must pass
the same setting to both. A frame with neither DI columns nor DI
configuration fixes no person. DI columns without configuration, or an
missing configured origin columns, refuse. The adapter separately requires
its complete DI state. Origin rows get the baseline q
bit for bit, so the adapter's multiplier sees the baseline probability.
Under `non_di_mortality="net_of_di_origin"`, the adapter then scales
non-origin probabilities by one cell factor, preserving their ratios
wherever clipping does not bind.

Missing attributes and each dimension's declared `unclassified_values`
use the named rule. `refuse` is the default. Its
`UnclassifiedValueError.cell_log` records per-cell refusal counts, using
baseline probabilities for diagnostics; no applied gradient is returned.
`reference` contributes zero log risk for that dimension. Unknown ordinary
categories always refuse. Logs include aggregate `unclassified_refuse`
and `unclassified_reference` counts and separate counts for each
dimension. Counts are dimension contributions: a person unclassified in
two dimensions contributes two to the aggregate. Thus neither substitution
nor refusal is silent.

## Normalization and tolerance

For each cell, the target is `sum(weight * q_base)`. Fixed rows retain
their prescribed probabilities. Free rows receive
`min(1, q_base * relative_risk * factor)`: after a set reaches one, its
deaths are subtracted and the factor is recalculated on the remaining
rows. Fixed deaths above the target make the cell infeasible and give
all free rows zero. Arbitrary fixed probabilities can also leave a target
above free positive-q support; the normalizer saturates that support and
flags infeasibility. Neither case can arise with fixed rows at baseline q.
Both rules apply when that support carries weight; the weightless case
follows.

Weights decide the factor only when they can. If every free row with
positive baseline q has zero weight, no factor changes the cell's weighted
deaths, so the weighted target says nothing about it. The cell then sets
the factor as if each person had weight one: its free rows' unweighted
expected deaths equal their unweighted baseline total, and they keep their
relative risks. A factor of zero would instead make those persons
immortal. With unit risks the rule reproduces the DI adapter, which leaves
the factor at one when the other rows carry no expected deaths. If the
weighted target is nonzero in such a cell, because fixed probabilities
differ from baseline, no allocation conserves it: the cell is still
flagged infeasible and the residual records the gap. On the model's path
the fixed rows sit at baseline, so the target is zero and the cell is
feasible.

The exact baseline path bypasses multiply/divide rounding for unit risks
and for a common free-row risk with fixed rows at baseline. Stable sums
reduce order sensitivity; Decimal arithmetic handles extreme magnitudes
that would underflow or overflow ordinary products. Probabilities returned
are float64; the log accounts for those returned values.

The cell log contains year, sex, age, persons, fixed persons, total weight,
fixed weight, baseline expected deaths, applied expected deaths, factor,
clipped persons, signed clipping residual and infeasibility, plus the
unclassified counts. `clipping_residual = baseline - applied`. In a
feasible cell without capping it is explicitly zero; ordinary rounding
is handled by the tolerance, rather than labeled a clipping loss.

Conservation checks use `rtol=1e-12, atol=1e-12` in expected-death units.
This allows float64 product, summation and multiply/divide roundoff and
the existing adapter's separate reductions; it is an accounting tolerance,
not an empirical admission threshold. Identity checks use exact array
equality. Permutation checks are exact where supported by stable sums;
weight scaling and adapter comparisons use the stated tolerance.

Intended monotonicity applies among free rows with the same baseline q in
a cell, holding other dimensions constant. This is the setting supplied
by the age-sex-year baseline and exercised by the ordering properties.
Fixed DI-origin probabilities are prescribed baseline values and are
outside that gradient ordering check.

The existing DI adapter caps once. Its feasible cells can consequently
fall short of the target; its residual is computed from
`expected_deaths_population_model - expected_deaths_applied` in its
existing cell log. The SM1 log describes normalization before that step.
Tests label the normalizer's iterative redistribution versus the
adapter's one-pass clipping as an intended difference. No shared-module
change is required.

## Design and build traceability

Paths below are relative to `src/populace_dynamics/mortality_ses/` for code
and `tests/mortality_ses/` for tests.

| Design or build element | Code | Tests |
|---|---|---|
| Design 3.1 SM1: three-dimensional, normalized mechanism | `specification.py`, `normalizer.py`, `model.py` | `test_specification.py`, `test_properties.py` |
| Design 5.4 SM1: context interface, fixed DI origin, no RNG, new step | `model.py`, `step.py` | `test_model_step.py`, `test_properties.py` |
| Design 6 SM1: accounting invariants | All package modules | All four test modules; properties below |
| Design 7.1: no wiring; later change admission | Package-only implementation, historical exclusions | Exclusion tuple and transitive reachability in `tests/estimates/test_birth_evidence_artifact.py` |
| Brief 2.1: categories, coefficients, time path, refusals | `specification.py` | `test_specification.py`, path and refusal properties |
| Brief 2.2: pure normalizer and cell diagnostics | `normalizer.py` | `test_normalizer.py`, normalizer properties |
| Brief 2.3: baseline wrapper and age/DI/weight rules | `model.py` | `test_model_step.py`, model properties |
| Brief 2.4: non-DI projection step | `step.py` | Step death-identity examples and properties |
| Brief 2.5: no wiring | Diff review: only package, tests and housekeeping edits | Historical reducer reachability test |
| Brief 2.6: design note | This document | Traceability and invariant evidence below |

## Invariant evidence

Every generated property uses invented values, alongside explicit examples.
Hypothesis deadlines are disabled because these are accounting tests, not
performance benchmarks. Any failing generated value is rerun and minimized
before being characterized as a mechanism defect.

| Invariant | Implementation | Example and property coverage |
|---|---|---|
| Cell conservation and zero uncapped residual | Iterative cap in `normalizer.py` | `test_invented_uncapped_cell_conserves_and_logs_counts`, `test_cell_conservation_bounds_and_baseline_fixed_feasibility` |
| Feasibility with baseline fixed q; arbitrary excess flagged | Fixed target calculation | `test_fixed_deaths_above_invented_target_are_infeasible`, `test_fixed_deaths_above_target_are_flagged`, baseline-fixed property |
| Unit-risk bit identity | Exact common-risk baseline path | `test_equal_risks_preserve_baseline_bits_with_fixed_baseline_rows`, `test_identity_is_bit_for_bit_and_normalizer_is_deterministic` |
| Same deaths with/without registry, ordinary and DI steps | `step.py` and context-only wrapper | `test_identity_probabilities_and_step_deaths`, `test_di_adapter_identity`, corresponding generated death-identity properties |
| Bounds | Capping and input validation | Conservation/bounds property and extreme-risk examples |
| DI composition, ratios and baseline origin q | Fixed origin in `model.py`, existing adapter | Composition examples and `test_composition_conserves_cells_preserves_ratios_and_fixes_di_q` |
| Intended monotonicity by earnings and education | Positive cell factor, log-additive risks | `test_ordered_earnings_and_education_risks_preserve_probability_order` |
| Row/weight invariance and one-risk cells | Stable reductions, exact common-risk path | Permutation/scaling examples and properties; `test_one_free_risk_group_returns_baseline_probability` |
| Weightless free support: unit-weight factor, never factor zero | Unit-weight allocation in both arithmetic paths of `normalizer.py` | `test_weightless_support_counts_persons_equally`, `test_weightless_support_uses_unit_weights_on_the_decimal_path`, `test_weightless_free_rows_in_infeasible_cells_keep_unit_weights`, `test_weightless_cells_count_persons_equally`, `test_model_gives_weightless_cells_their_unit_weight_probabilities`; the normalizer properties draw zero weights |
| Differential adapter arithmetic; intended clipping difference | Same uncapped algebra, iterative cap | Private-adapter differential examples and properties, including `test_unit_risk_matches_adapter_on_every_unclipped_cell` over zero weights, infeasible cells and arbitrary fixed probabilities; named intended capping divergence |
| Time path and alternative path isolation | Path protocol and hold-last default | `test_pluggable_path_changes_only_named_year`, generated hold-last/refusal property |
| Determinism and no RNG consumption | Pure `evaluate` | Repeated-call examples, generator state and patched-generator property |
| Refusals | Specification, frame and interface validation | Nonfinite/nonpositive risks, missing columns, unknown/unclassified values, age mismatch and `probabilities` attribute examples and properties |

## What remains outside SM1

SM2 owes source-audited category definitions, lifetime-earnings construction,
empirical joint coefficients, input provenance and calibration, and registered
primary/alternative paths. Its admitted scope is external-target conformance,
labeled "calibrated, not validated". SM1 supplies none of those inputs.

SM3 owes the authorized, prospectively registered mortality-gradient gate,
prediction-boundary attributes, death alignment, power checks, simultaneous
bounds and the S0.1 exposure audit. An inconclusive dimension admits nothing.
Before any Track B projection uses SM mortality, SM3 must pass and the
section 7.1 change-admission protocol must be frozen. Affected mortality,
marital, DI, joint-payment, recipient-denominator, survivor-pathway and timing
checks must be completed or rerun; earlier J/B7 evidence does not transfer.
This build changes no registered projection and admits no population,
gradient, lifetime-benefit or national financing claim.
