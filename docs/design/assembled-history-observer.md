# Histories from assembled projections

`observe_assembled_history` retrospectively composes a
`ClosedCohortEarningsHistory` from an initialized 2014 slice, consecutive
assembled projection slices through at most 2022, and the existing
`mortality_slices` collector. It calls no model, generator or RNG method.
Every original person retains their recorded earnings before removal;
removal before the target year's earnings step creates no earnings row or
post-death zero. The underlying history validators remain unchanged.

This is an opt-in engineering interface, not an execution or acceptance of a
registered population projection. Caller-supplied source and realization
labels remain declarations. No coverage inference, benefit calculation,
source admission or accepted Axiom bridge is provided.

## Observe the original population explicitly

The caller must choose one of two modes:

- `strict_full_roster` permits mortality attrition but refuses scheduled
  entrants and materialized births anywhere in the supplied projection.
- `original_2014_view` follows exactly the initialized 2014 population while
  retaining the full projection. Before selecting that cohort, it reconciles
  all deaths, scheduled entrants and materialized children. Its separate
  exclusion ledger identifies every later person, their entry kind/year,
  native parent when applicable, and any subsequent observed removal year.
  This mode does not call the full population closed or construct complete
  earnings histories for later entrants.

Supply the entire scheduled-entry mapping, reserved real-ID namespace and
synthetic allocator start used by the projection. The initialized slice must
match the complete declared original cohort. Each next mortality input must
equal the previous full roster plus that year's declared scheduled entries.
Each final slice must equal mortality survivors plus evidenced newborns.
Unknown disappearance, resurrection, repeated identity, unexplained
additions, incomplete mortality evidence and changed demographics refuse.
An entrant who dies immediately remains in the exclusion ledger. Complete
cohort extinction can coexist with a continuing noncohort population.

Native `person_id` columns must retain NumPy signed `int64` dtype. Exact
source identities map to private history keys only on copied observation
views; native IDs and RNG ordinals are never replaced in the projection.
Registry ordinals are derived from the numerically sorted union of original
and all scheduled IDs, including future entries, matching assembly setup.
They are distinct from dense private keys. Canonical audit IDs must also fit
signed `int64`, including excluded people.

The full mortality pre-roster must match the preceding slice's age, sex and
weight, including the first step's initialized baseline. Scheduled entries
must supply the immediately preceding year. Survivors must advance age by
one and retain sex/weight. Exact integer scalar ages and years in native
object columns are accepted and converted to `int64` only on copied cohort
views; floating ages/years are refused. Every pre-mortality age must lie
within the supplied snapshot's supported domain.

## Capture the actual fertility boundary when births occur

The current `PeriodTrace.authoritative_marital_state.births` is empty in
assembled runs. Maternal births occur in the subsequent fertility callback;
its private draw records are not returned by the collector. Therefore the
trace and a final `synthetic_entry` marker cannot alone substantiate an added
child. Observation without additional evidence refuses materialized births.

`capture_fertility(modules)` supplies the bounded additional seam:

```python
instrumented_modules, capture = capture_fertility(assembled_modules)
# Execute the normal ProjectionEngine once with instrumented_modules.
# Retain its ProjectionResult and the existing assembly draw collector.
```

The adapter replaces only the `PeriodModules.fertility` callable. It copies
the callback's input values, invokes the original exactly once with the
identical frame/context/marital/RNG objects, copies its output values, and
returns that original output object by identity. All other callbacks and
the initializer retain identity. In particular, the assembled mortality
callback still owns `ensure_draw`, RNG consumption and mortality collection.
The adapter neither calculates fertility nor exposes private maternal draws.

Create a fresh adapter/capture for each projection invocation. Out-of-order
calls, attempted reuse, mixed draw/horizon, callback exceptions or incomplete
capture make it unusable. `capture.to_json()` archives complete copied
boundary records for an external execution receipt. There is no standalone
capture loader in this prototype.

The observer requires the captured input to equal the aged mortality
survivors, and captured output to match the final full roster and its
demographics. Newborn metadata must agree between capture and final slice,
with age zero, target birth year, synthetic marker, consecutive allocator
ID, no reserved collision and a surviving parent. Native concatenation can
promote parent IDs to float. Only finite integral floats with absolute value
strictly below `2**53` and a unique exact native-parent match are supported;
larger/ambiguous floating parents refuse. This does not reconstruct a lost
integer ID. Exact integer parent columns retain signed-int64 support.

Using this adapter creates a separately instrumented execution. Its adapter,
source versions and boundary evidence require a new execution identity even
though the existing engine, assembly and generator source files remain
byte-identical. It must not be presented as the old registered artifact.

## API and persistence

```python
observation = observe_assembled_history(
    projection, draw_outputs,
    mode="original_2014_view",
    identity_map=original_identity_map,
    realization_id=realization_id,
    generator_digest=generator_digest,
    earnings_source_contract_digest=earnings_contract_digest,
    mortality_snapshot=before_model_snapshot,
    mortality_snapshot_after=after_model_snapshot,
    mortality_source_contract_digest=mortality_contract_digest,
    unit=unit, price_basis=price_basis,
    lineage_by_year=annual_lineage_digests,
    initial_native_ids=initial_native_ids,
    scheduled_entries_by_year=scheduled_entries,
    reserved_real_ids=reserved_real_ids,
    synthetic_id_start=synthetic_id_start,
    fertility_capture=capture,
)
person_history = observation.history.for_person(original_identity)
restored = AssembledHistoryObservation.from_json(
    observation.to_json(),
    baseline=trusted_initial_history,
    expected_digest=observation.digest,
)
```

The immutable result binds the cohort history to a canonical selection audit.
Loading requires a trusted whole-envelope digest and external baseline,
rejects unknown/duplicate fields and noncanonical JSON, and rechecks full
roster transitions, exclusions, ordinal bindings and cohort consistency.
Even a recomputed digest cannot permit an internally inconsistent audit or
an ID outside the native type. A trusted digest remains necessary to reject
other valid-looking substitutions; hashes alone do not authenticate a run.

`input_digests` binds precisely the following supplied evidence:

| Key | Hashed content |
|---|---|
| `projection` | All slice column names, dtype strings, row order and scalar values |
| `mortality` | The same representation for every supplied mortality slice |
| `traces` | Each trace's year, ordered step names and authoritative marital `births` frame |
| `entry_metadata` | Initial IDs, reserved real IDs, synthetic start and full scheduled-entry frames |
| `mortality_model` | The immutable effective probability snapshot's digest |
| `fertility_capture` | Capture coordinates and copied boundary frame representations, or explicit absence |

Frame encodings do not include pandas indices or attributes. The `traces`
digest does not bind the rest of authoritative marital state; no digest here
binds other collector outputs, fitted-model files or the execution command.
These representations are input-value bindings, not original-file hashes.
An actual execution receipt must separately bind source files, commands,
all relevant model/input artifacts and pre/post effective parameters. Equal
supplied mortality snapshots are required here, but the observer does not
itself establish when they were obtained. It adds no exposure values and
infers no death date from a step's target year.

## Verification and remaining scope

Tests execute the actual eight assembly callbacks with invented fixtures.
Mortality, aging, earnings and claiming execute normally. The fitted marital,
fertility, disability and household simulation cores are stubbed at bounded
test seams; native fertility materialization still runs. This verifies
wiring, not a fully fitted eight-model or registered-input projection.

Ordinary and correlated earnings fixtures compare all annual frames,
collector outputs and registry-stream end states with and without capture.
They exercise repeated same-draw reset, exact callback arguments/results,
one-call behavior, no observation-time model/RNG calls, no source mutation,
large IDs, unsafe parent refusal, immediate entrant death, extinction and
tampered persistence. An all-real-core rehearsal would be a separate
reviewed task; none is performed by these tests.

The implementation favors auditable composition over population-scale
storage: boundary JSON copies full frames, and nested per-person histories
repeat metadata. Birth linkage is callback-boundary evidence, not private
maternal draw provenance. The existing historical reducer excludes this new
module explicitly, with a transitive reachability test. Historical gates,
inputs and evidence artifacts remain unchanged.
