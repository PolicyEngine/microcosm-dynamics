# Mortality step observer

`populace_dynamics.mortality_observer.observe_mortality` is an opt-in,
single-step helper around the existing `engine.steps.apply_mortality`. It
returns that function's survivor frame and an immutable
`MortalityStepObservation`. Registered projection and assembly code remain
unchanged; this is not automatically installed in `ProjectionEngine`.

```python
survivors, record = observe_mortality(
    frame, context, rng,
    model=mortality_model,
    identity_map=identity_map,
    realization_id="caller-supplied-realization",
    source_contract_digest=source_contract_digest,
)
restored = MortalityStepObservation.from_json(
    record.to_json(), identity_map=identity_map,
    expected_digest=record.digest,
)
```

The caller supplies an existing `AgeSexMortalityModel`, `PeriodContext` and
NumPy generator. Input `person_id`, `age` and `year` columns must have NumPy
`int64` dtype; floating ages such as `30.0` are deliberately rejected rather
than cast. Each private ID must be unique and already present in the explicit
`PersonIdentityMap`. Reverse mapping preserves typed signed/unsigned source
integers beyond `2**53` and textual identities without numeric coercion.

Every frame year must immediately precede the target year. Ages must lie
between zero and the actual final inclusive model bound, and sex must be
`female` or `male`. The final band's `+` label does not imply an infinite
upper bound. The helper rejects unsupported ages before any draw; the
underlying model otherwise casts ages and leaves unmatched rows at zero
probability. It preserves deliberately supplied zero-probability cells,
including the registered model's separately documented under-25 pad.

Registry-backed calls validate the draw index, period bounds, required
person ordinals and uniqueness of all supplied ordinals before requesting
any generator. Empty, correctly typed frames remain valid. Period indices
start at one; draw indices start at zero. The helper snapshots the model's
effective float probabilities and invokes the actual mortality function
exactly once with detached parameters. It does not fit a model or implement
an alternative mortality calculation. For valid inputs, survivor values,
ordering, index, dtypes and random draws match a direct call.

The record contains pre-aging age and sex, the actual survived/died outcome
for every input person, target year, period and draw indices, registry size
and active-person ordinals when applicable, realization label, source
contract digest, effective model cells and identity-map binding. Its
`pre_keys` and `post_keys` properties derive the exact before/after ID sets.
Deceased identities remain reversible after the survivor frame drops them.
The model and observations are detached from mutable inputs. Model floats
use canonical hexadecimal strings; integer JSON fields use decimal strings.
The loader checks the external identity map before constructing rows and
rejects duplicate fields, extra fields, invalid types and inconsistent
model digests. Detecting otherwise valid edits requires a trusted expected
record digest. These digests establish identity, not source admission,
empirical validity or complete RNG replay provenance. Realization and source
contract labels are supplied by the caller, not verified against a whole run.

A death outcome means removal at the mortality step targeting the recorded
projection year. It does not establish a death date, birthday, within-year
timing or exposure. The existing assembly already has an optional
`M6_DRAW_OUTPUTS_KEY` collector with mortality slices and a conventional
0.5 death exposure. That callback also manages `ensure_draw` state; replacing
it directly with this helper would discard that behavior. Assembly-aware
integration is separate work.

This record neither changes a fixed-roster earnings history nor fills
post-death earnings with zero. A future longitudinal observer can retain
earlier histories for deceased persons and explicitly handle new entrants
and births. This slice provides no coverage inference, statutory arithmetic,
Axiom bridge, benefit or population-parity claim. Its explicit exclusion
from the historical source inventory is guarded by the transitive import
reachability test.
