# Supplied annual accounting history

`populace_dynamics.engine.accounting_history` is an optional wrapper around
the unchanged [annual accountant](stock-flow-accounting.md). It accepts
already supplied frames and declarations. It does not run a projection,
generate events, or establish scientific acceptance.

```python
from populace_dynamics.engine.accounting_history import (
    AnnualTransition,
    reconcile_history,
)

history = reconcile_history(
    [
        AnnualTransition(
            opening_year=2020,
            closing_year=2021,
            opening=people_2020,
            closing=people_2021,
            additions=declared_2021_additions,
            exits=declared_2021_exits,
        ),
        AnnualTransition(
            opening_year=2021,
            closing_year=2022,
            opening=people_2021,
            closing=people_2022,
            additions=declared_2022_additions,
            exits=declared_2022_exits,
        ),
    ],
    identity_contract="single_presence_episode",
)
```

The keyword `identity_contract` is required. Its only supported value is
`single_presence_episode`: within the supplied history, every person ID
may have one presence episode. Every declared departure retires that ID
under this explicitly selected constraint, including a transient who
arrives and departs between endpoints. Declaring that ID again is refused,
even after empty intervening years or as another transient. New, distinct
IDs remain supported after extinction; the wrapper never allocates IDs.

This contract does not assert that emigration or another departure is
permanent in reality. Same-person return needs a separately reviewed typed
linkage to its earlier departure and explicit return semantics. The current
event kinds do not supply that contract. Changing a returnee's ID to evade
the check would not model their identity correctly. Within a single year,
the annual accountant still supports only an arrival followed by a departure,
not exit followed by return.

Periods must form a nonempty sequence in chronological order, each one year
long, with no gaps or repeated periods. At a shared boundary the previous
closing frame and next opening frame must have the same person-ID set and
the same weight for each ID, regardless of row order. The wrapper reuses the
accountant's signed-int64 ID/year and finite nonnegative binary64 weight
validation before constructing snapshots. Weight equality is exact in that
binary64 domain, with no tolerance. A discrepancy between two representations
of the same boundary is refused; weight changes within an annual transition
retain the accountant's separate revaluation components and residuals.
Zero-weight people remain in the roster.

Each returned `HistoryAccount.periods` item is the unchanged annual account.
The result, its nested mappings, and its ID tuples are immutable; `to_dict()`
creates fresh summary containers and omits identifier rosters. The supplied
`AnnualTransition` descriptors freeze field assignment but do not make
caller-owned DataFrames or declaration lists immutable. Reconciliation does
not mutate those inputs or retain their containers in the result. Callers
must not mutate inputs concurrently while they are being read.

`HistoryAccountingError` identifies the failure kind and zero-based period
index, with validated year coordinates when available. Annual failures keep
their original typed exception in `__cause__`, including reconciliation
discrepancies. Its `to_dict()` returns fresh JSON-safe diagnostic containers.
A failure raises without returning a completed or partial history account.

The first opening roster establishes no prior lifecycle history. This wrapper
checks only the supplied periods and declarations: it cannot establish event
truth, cause, completeness, or behavior outside that interval. A transient
omitted from both declaration lists is still unobservable. No horizon totals,
family behavior, benefit calculations, benchmark comparison, acceptance gate,
or population admission claim is introduced.

Only person IDs, years, and person weights enter this accounting interface.
Other frame columns are ignored and their continuity is not checked; this is
not household or geographic context transport. The separately proposed
[mortality graph](https://github.com/PolicyEngine/microcosm-dynamics/pull/436)
keeps its age/sex source and snapshots at their exact schemas and rejects
extra columns; this wrapper does not extend those schemas.
A future separate context contract must preserve household/member links and
household atomic-location anchors assigned by Microcosm once before support
cloning. Dynamics must inherit those anchors, derive larger geographies with
the same versioned mapping, and allow location changes only through separately
declared mobility or migration events. No context adapter, household-weight
mapping, partial-household lifecycle, or group-quarters lifecycle is supplied
here. Canonical export fields and provenance still require parent contract
verification.

The module is not re-exported by the engine initializer and is not called by
the historical engine. Integration into the separately proposed graph is not
included. Direct imports also execute the existing engine initializer and
its broader source dependencies; this wrapper adds only stdlib, pandas, and
the existing accountant to that path.
