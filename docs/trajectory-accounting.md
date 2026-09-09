# Accounting for annual mortality transitions

The optional `populace_dynamics.graph.trajectory_accounting` module adds one
accounting node per year to the existing synthetic mortality/ageing graph.
It executes the real Microcosm DAG with the same reviewed graph/Frame pin.
It does not change fitted laws, draws, population frames, weights, scientific
gates, or the historical projection engine.

```python
from populace_dynamics.graph.trajectory_accounting import (
    run_accounted_mortality_trajectory,
)

result = run_accounted_mortality_trajectory(
    training="synthetic-training.json",
    rates="synthetic-rates.json",
    initial="synthetic-initial.json",
    holdouts={2015: "synthetic-annual-2015.json"},
    end_year=2015,
    output_dir="synthetic-accounting-output",
)
```

These paths must contain the exact synthetic contracts documented in
[the population graph and mortality trajectory](population-graph.md).
The optional module
requires Python 3.13 or later and the reviewed graph dependencies. Importing
the ordinary `populace_dynamics.graph` package remains lazy and unchanged.
`build_accounted_trajectory_graph` also exposes the declaration and kernel
registry for callers using the executor directly.

## Declared events and frozen snapshots

Each `account_YEAR` node reads only the corresponding typed mortality
transition and frozen population snapshot. It runs against the graph's
separate training population version without reading that population's
columns. It has no holdout, model, source, or RNG input. Accounting is not a
prerequisite of any subsequent mortality transition.

The adapter validates the transition's person and observation bindings and
the snapshot's year, row, period, and weight structure. It copies the opening
and closing rows, preserving the supported columns and weight positions.
Only transition records declaring `survives=false` produce death events.
Missing or additional endpoint people cannot supply their own event causes.
No births, migration, or other entry/exit events are assumed.

Completed transitions call the
[annual stock-flow accountant](stock-flow-accounting.md). Count conservation
is exact; weight residuals and revaluation components are reported without
an acceptance threshold. A changed survivor weight can therefore produce a
complete account while the original mortality evaluation independently
fails its unchanged-weight check. Accounting completion establishes neither
scientific acceptance nor completeness or truth of the declared event log.
The adapter cannot detect an arbitrary same-length rearrangement of supplied
weights without independent binding evidence; it accounts for the supplied,
content-addressed snapshot.

After complete extinction, subsequent completed empty periods receive explicit
zero-to-zero accounts even though the population contains no new period
groups. A failed or blocked mortality transition instead produces
`account=null` and `accounting_status=not_evaluated`, retaining its diagnostic
and last completed year. It never turns a stale snapshot into deaths.
Malformed inputs or reconciliation refusals produce a separate failed
accounting artifact; original mortality and evaluation receipts remain intact.

The runner writes `accounting-report.json` and the actual `manifest.json`.
Its `AccountedTrajectoryRun` contains those accounting summaries and the
manifest. It does not rewrite the original runner's `report.json`, model, or
trajectory exports. The manifest retains original application/evaluation
receipts and artifact references; an accounting status is not their rollup.
Source hashes cover the accountant and the reused snapshot/transition helpers.

## Household and location contract still required

The current initial source accepts exactly `person_id`, `age`, `sex`, and
`weight`. Its snapshot accepts only the existing person-period identity,
age, sex, period, and weight structure. Additional atomic-location or
household-link columns are refused, not silently discarded. This integration
does not yet transport household location or membership.

A separate extension must preserve household atomic-location columns **and
household/member links** in both source and snapshot contracts. Microcosm
assigns the household anchor once **before support clones are created**;
clones and Dynamics inherit it. Larger geographies must derive from that
anchor through the **same versioned mapping**. Location may change only
through a separate declared mobility or migration event. Accounting must not
allocate locations, create independent geography assignments, or infer a move
from a roster difference. That extension needs its own schema, lineage,
membership, mapping-version, and declared-event tests.
