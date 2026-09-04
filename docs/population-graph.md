# First population graph: mortality and ageing

The optional `populace_dynamics.graph` package fits the existing M6 mortality
model on a historical synthetic panel, applies the fitted artifact to a
separate starting population, and adds surviving observations for the next
year. It produces an engineering report and a content-addressed execution
manifest. It does not change the existing projection loop, candidate
registries, scientific gates, or committed evidence.

## Dependencies and execution

The graph example requires Python **3.13 or 3.14**, NumPy 2+, pandas 2.3+,
and the Microcosm graph/frame revisions containing typed artifact edges and
`microcosm.graph.randomness.keyed_uniform`. The default Dynamics installation
continues to support Python 3.10–3.14 without importing Microcosm. The entry
point checks capabilities and gives installation guidance when they are absent.

The `graph` extra pins both graph and Frame to core commit
`3ff92b0aea14407d09479bff5623dc7d1a92d008`. An older package merely sharing
the version number `0.1.0` is insufficient. In an isolated Python 3.13 or 3.14
environment, install with `uv pip install '.[graph]'`. The core change must be
reviewed before this dependent integration is released; replace the Git pins
with a compatible published release when one exists. CI installs this exact
extra, refuses missing capabilities, and runs the integration on both supported
Python versions. Do not modify the existing scientific gate environment. No
rules engine, restricted microdata, or optional forest fitter is needed here.

Run from that environment, choosing an output directory:

```sh
python -m populace_dynamics.graph --synthetic --output-dir ./mortality-example
```

The command creates small synthetic inputs under `mortality-example/inputs`.
It preserves existing input files so that edits can test cache invalidation.
Repeated execution reuses the verified store under `mortality-example/store`.
The report, manifest, fitted JSON model, entity tables, and next-period slice
are written inside the chosen output directory. A failed engineering or
fixture verdict exits nonzero while retaining the diagnostics.

Four explicit source paths can replace the generated inputs:

```sh
python -m populace_dynamics.graph \
  --training ./inputs/training.json --rates ./inputs/rates.json \
  --initial ./inputs/initial.json --holdout ./inputs/holdout.json \
  --boundary-year 2014 --external-vintage-year 2014 \
  --experiment-id comparison-a --replicate 0 --base-seed 0 \
  --output-dir ./mortality-example
```

These inputs still exercise the synthetic engineering contract. The example
does not confer validity on a real-population projection. Source JSON rejects
duplicate members and nonfinite values. Each source is declared separately;
holdout bytes are available only to evaluation. Domain kernels read the
content-verified JSON directly: the registered source marker deliberately
does not pretend an external rate table or a holdout report is a population.

## Executable ownership

The graph has two CREATE roots, each carrying a `person_period` observation
entity and `person` and `period` groups. `person` retains stable identities;
`period.period` is the immutable mass-partition label. The training root
contains exposure records; the initial root contains recipients. Their only
connection is the explicitly typed mortality-model artifact.

The fit node calls `prepare_mortality_refit_inputs` and
`fit_mortality_model`. Event year, required interview year, and declared
external vintage retain the existing cutoff checks. The JSON model contains
validated contiguous age bands, sex-specific probabilities, fit boundary,
external vintage, and retained row count. The manifest binds its producer
to source identities and implementation digests. The fitter's external-rate
factor cancels in its fitted-window level, so this is not evidence of
independent external calibration.

Application calls `apply_mortality` with a graph-specific context. Every
uniform is keyed by the original person identity, process, year, and draw
index under the chosen experiment/replicate/seed. It does not use the legacy
ID-sorted ordinal registry. Reordering, splitting, or adding unrelated
people preserves the existing people's draws. Fit and application declare
platform-specific bitwise numeric behavior conservatively; cross-platform
equality is not claimed.

EXPAND calls `advance_age` on survivors, adds their next-period observations
with lineage to the original observations, and attaches them to one newly
admitted period group. A same-version rewrite node claims the materialized
age values. Historical ages and memberships remain unchanged. The temporary
`year` returned by `advance_age` is never written over a carried observation
column. No new person, birth, or immigrant is implied by admission of the
period group.

Typed person-period weights are the single authority. Every survivor carries
the same trajectory weight into the new period. The declared mass receipt
shows historical mass unchanged and new-period mass equal to surviving
weight. Total stored observation mass therefore grows by the additional
period. If everyone dies, the graph adds no observations and no orphan period
group; the report explicitly records next-period mass zero.

## Evaluation and limits

The report separates `engineering_verdict` (survivor/age parity and population
structure) from `fixture_verdict` (the independently sourced synthetic
death-rate and age expectations). It records weighted expected, observed,
and generated deaths, row counts, period mass, node/model identities, and
cache reuse. The fixture death-rate tolerance is an input named
`fixture_max_abs_death_rate_gap`; it is not a scientific acceptance threshold.
Changing all held-out outcomes to deaths fails that fixture check while
leaving fitting, application, draws, and accounting unchanged.

Household accounting is explicitly unsupported and refused by the Python
entry point. Household weight sharing, marriage, births, immigration,
alignment replay, repeated years, and the full M6 loop remain later work.
No certified data release or scientific candidate is produced by this graph.

## Tests

```sh
python -m pytest -q tests/test_graph_mortality.py \
  tests/test_m6_engine_refit.py tests/test_m6_engine_steps.py
```

The integration tests cover direct execution with an independently injected
uniform vector, JSON validation, cutoff and holdout isolation, fitted-artifact
reuse, changed fitting weights, row/chunk/person invariance, cold/warm stores,
and zero/all-survivor expansion. They skip the optional runtime cases when
the required core capabilities are unavailable; the JSON and dependency
boundary tests still run. Importing `populace_dynamics.graph` remains safe
under Python 3.10–3.12.
