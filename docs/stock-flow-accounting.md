# Annual population stock-flow accounting

`populace_dynamics.engine.accounting.reconcile_period` checks whether one
annual transition's opening population, declared arrivals and departures,
and closing population reconcile. It reports person counts, weight flows,
weight changes, and arithmetic residuals without altering either frame.

This interface is experimental and opt-in. It does not change the historical
projection engine, generate demographic events, or establish an admitted
population. Its status is `engineering-accounting-coherence-only`, and its
interface version is `stock-flow-accounting/0.1.0-experimental`. No scientific
tolerance or acceptance gate is added.

## Input contract

```python
reconcile_period(
    opening,
    closing,
    *,
    opening_year,
    closing_year,
    additions=(),
    exits=(),
)
```

Both pandas frames require `person_id`, `year`, and `weight` columns.
Identifiers are unique within each frame; IDs and years must be integers
within the signed int64 range. Floats and booleans are rejected as IDs or
years. These are the accountant's own validation rules, which are stricter
than the historical loop's slice check.

Weights must be real numeric, finite and nonnegative. Strings, complex
values, and booleans are rejected before conversion to binary64. Negative
weights are checked before conversion; nonzero values that underflow to zero
in binary64 are rejected. Zero-weight
rows remain visible in counts. Empty frames still require the three columns,
but empty columns may have any dtype. Each nonempty frame must carry its
stated year, and `closing_year` must equal `opening_year + 1`.

`additions` and `exits` are sequences of `PopulationEvent` declarations.
Each event has an integer `person_id`, `kind`, closing `year`, optional
`weight`, and optional string `reason` and `source`.

| Addition kinds | Exit kinds |
|---|---|
| `birth` | `death` |
| `scheduled_entry` | `emigration` |
| `other_entry` | `other_exit` |

The two `other_*` kinds require a nonempty reason. At most one addition and
one exit are supported for a person in a period, with arrival before exit.
There is no finer event-timing model. An addition cannot collide with the
opening roster, and a declared departure cannot remain in the closing roster.
Unexplained changes in endpoint membership and duplicate declarations fail.
The accountant never infers that a disappearing person died or that a new
identifier represents an immigrant.

## Counts and weights

Counts reconcile exactly:

```text
closing = opening + additions_total - exits_total
```

People who arrive and depart in the same period are counted in both flows.
These transients appear in neither endpoint frame and must have explicit
weights on both declarations. Otherwise, an omitted arrival weight uses the
closing-frame weight; an omitted departure weight uses the opening-frame
weight. These conventions are recorded in provenance through the counts of
explicit event weights.

Weight accounting reports:

```text
reconstructed_closing = opening + additions_total - exits_total + revaluation
weight_residual = closing - reconstructed_closing
```

| Revaluation component | Difference summed over the relevant people |
|---|---|
| `carried` | Closing weight minus opening weight for survivors |
| `entrant` | Closing weight minus declared arrival weight |
| `exiting` | Declared departure weight minus opening weight |
| `transient` | Declared departure weight minus declared arrival weight |

Weights are never rebalanced. Sums use `math.fsum` over binary64 components;
subtraction and component totals still involve rounding. Nonzero arithmetic
residuals are reported without a tolerance-based verdict. An intermediate or
summary that cannot be represented with finite binary64 arithmetic raises a
`PopulationAccountingInputError`.

## Example

```python
import pandas as pd
from populace_dynamics.engine.accounting import PopulationEvent, reconcile_period

opening = pd.DataFrame({
    "person_id": [1, 2, 3], "year": [2020] * 3,
    "weight": [10.0, 20.0, 30.0],
})
closing = pd.DataFrame({
    "person_id": [1, 2, 90], "year": [2021] * 3,
    "weight": [11.0, 20.0, 5.0],
})
account = reconcile_period(
    opening, closing, opening_year=2020, closing_year=2021,
    additions=[PopulationEvent(90, "birth", 2021, source="synthetic.birth")],
    exits=[PopulationEvent(3, "death", 2021, source="synthetic.mortality")],
)
assert account.weights.closing == 36.0
assert account.weights.revaluation.carried == 1.0
assert account.count_residual == 0
assert account.weight_residual == 0.0
```

The weight identity is `60 + 5 - 30 + 1 = 36`. `account.to_dict()` returns
JSON-serializable counts, weights, residuals, and provenance. Person-ID tuples
are available as attributes and are omitted from this summary. Serialized
provenance is isolated from the immutable account and other serializations.

Malformed inputs raise `PopulationAccountingInputError`. Well-formed inputs
whose declarations conflict with the frames raise
`PopulationReconciliationError`, with typed `.discrepancies` and a `.to_dict()`
representation. Validation stops at the first failing stage: frames,
declarations, reconciliation, then weights.

## Projection-loop integration and limits

The caller must capture declarations from its adapters or supplied schedule.
The loop activates scheduled entries before mortality in the wave ending in
`Y`, while entry frames carry `Y - 1`. Their declarations must use `Y` and
explicit weights so an entrant who dies in the same wave can be accounted for.
Birth and mortality declarations should come from the operations that perform
those transitions. An endpoint difference alone cannot establish their cause.

Tests in `tests/test_m6_stock_flow.py` drive the real `ProjectionEngine` with
synthetic recording adapters, then reconcile adjacent output slices. They
include a birth, a death, and a scheduled entrant who dies before the wave
closes. No fitted transition law or native population is used.

Accounting coherence does not verify event-log completeness. If both records
for a transient are omitted, the endpoint frames cannot reveal the omission;
provenance records `event_log_completeness_verified=False`. Event reasons are
also caller assertions. The accountant has no cross-period memory, so a past
ID explicitly declared as a new addition can be reused without detection.
Only `weight` is reconciled; `start_weight` and other frame columns are ignored.

The module directly imports only the standard library, NumPy, and pandas.
Normal package import also executes the historical engine initializer and its
broader source dependencies. The historical source-identity test verifies that
this new module remains unreachable from the sealed projection roots; the
static guard covers ordinary imports and explicitly listed dynamic roots, not
arbitrary runtime imports. This page is not added to the Quarto chapter list.
