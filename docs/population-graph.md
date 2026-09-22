# First population graph: mortality and ageing

The optional `populace_dynamics.graph` package fits the existing M6 mortality
model on a historical synthetic panel, applies the fitted artifact to a
separate starting population, and adds surviving observations for the next
year, or repeats those transitions through an explicit end year. It produces
an engineering report and a content-addressed execution
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

If malformed held-out input prevents evaluation, the executor records a failed
`evaluate` gate. The command exports that manifest and a diagnostic report with
the gate's name, outcome and original exception evidence on both cold and warm
runs, then exits nonzero. The report marks `engineering_verdict` and
`fixture_verdict` as `not_evaluated`; it does not invent evaluated deaths or
mass metrics. Successful evaluation retains the existing report fields.

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
alignment replay, and the full M6 loop remain later work.
No certified data release or scientific candidate is produced by this graph.

## Annual trajectories

The optional `run_mortality_trajectory` Python entry point builds one graph
with a single mortality fit and separate application, expansion, age-ownership,
snapshot, and evaluation nodes for each year. It uses the same exact
graph/Frame pin as the one-year example. The fit cutoff stays fixed while the
application year
advances. This extends execution of the existing age/sex law; it does not add
a calendar-year mortality improvement model or establish long-horizon validity.

Each application reads only the preceding period's observations. A typed
transition artifact binds each probability and survival decision to its
person and observation identities. EXPAND appends survivor observations with
lineage to that preceding period. Earlier ages, memberships, and trajectory
weights stay unchanged. The mass receipt covers every historical period,
not just the newest pair. After extinction, later years contain no at-risk
people and add no orphan period groups.

Declare one aggregate synthetic holdout for each application year. For example:

```python
import json
from pathlib import Path

from populace_dynamics.graph import run_mortality_trajectory
from populace_dynamics.graph.synthetic import write_synthetic_inputs

root = Path("mortality-trajectory")
sources = write_synthetic_inputs(root / "inputs")
sources.pop("holdout")
holdouts = {}
for year in range(2015, 2018):
    path = root / "inputs" / f"aggregate-{year}.json"
    path.write_text(json.dumps({
        "scope": "synthetic_engineering",
        "year": year,
        "expected_death_rate": 0.2,
        "fixture_max_abs_death_rate_gap": 0.25,
    }))
    holdouts[year] = path

result = run_mortality_trajectory(
    **sources, holdouts=holdouts, end_year=2017, output_dir=root,
)
print(result.report)
```

These small aggregate fixtures are deliberately artificial, with input
tolerances used only for engineering tests. They contain no empirical
acceptance targets. Each evaluation reads a typed snapshot of the actual
materialized population on a separate population version. This keeps the
evaluation outside the next expansion's dependencies under the pinned core.
An annual evaluation depends on its own holdout; changing
or failing that evaluation does not alter later simulation. Extending the
horizon reuses the existing fit and annual nodes in the same verified store.
Changing experiment, replicate, or seed changes application identities while
reusing the fit. All sources remain declared and content-hashed by the executor,
including evaluation sources whose kernels are subsequently guarded.

The output directory contains `trajectory.csv`, `model.json`, `report.json`,
and `manifest.json`. The trajectory includes the initial period and every
completed survivor period, with person identity, age, year, and weight.
Annual reports keep expected and generated deaths, survivor counts, and
period mass separate from fixture and engineering verdicts.

Application ages outside the fitted bands must fail explicitly. In particular,
a survivor aged 120 can be advanced to 121, but cannot enter another mortality
draw under a law with support ending at 120. The graph does not silently assign
such people a zero death probability. A typed failure outcome guards later
applications and expansions, preserving the latest valid population and the
original diagnostic. Blocked application status is reported separately from
the core's execution/cache receipts: this pinned executor still runs guarded
nodes and does not provide native `unreached` receipts. A failed evaluation
does not propagate this application block.

Snapshots include the full materialized history, so their storage grows with
both population size and horizon. This synthetic integration has not been
benchmarked for national-scale projection. Root creation, fitting, store
corruption, and unexpected structural failures can still abort execution;
the retained diagnostic path covers application and evaluation failures.

## Tests

```sh
python -m pytest -q tests/test_graph_mortality.py \
  tests/test_graph_mortality_trajectory.py \
  tests/test_m6_engine_refit.py tests/test_m6_engine_steps.py
```

The integration tests cover direct execution with an independently injected
uniform vector, JSON validation, cutoff and holdout isolation, fitted-artifact
reuse, changed fitting weights, row/chunk/person invariance, cold/warm stores,
and zero/all-survivor expansion. Independent graph-to-direct model parity and
future-event/late-interview mutations protect cutoff mapping. Nondefault
experiment, replicate and seed tests independently derive draw coordinates and
check direct-step parity, fit reuse and changed application identity. They skip
the optional runtime cases when the required core capabilities are unavailable;
the JSON and dependency
boundary tests still run. Importing `populace_dynamics.graph` remains safe
under Python 3.10–3.12.

The annual tests independently repeat the existing fit, mortality, ageing,
and keyed-draw operations; compare every retained person-period and weighted
diagnostic; and exercise horizon reuse, stream changes, holdout isolation,
extinction, and retained support-failure evidence.
