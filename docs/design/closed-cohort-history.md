# Closed-cohort earnings histories

`ClosedCohortEarningsHistory` links observed mortality steps to annual
earnings for an original 2014 cohort through at most 2022. It composes the
existing `ForwardEarningsHistory` and `MortalityStepObservation` classes. It
does not call a generator or change the registered projection engine.

```python
cohort = ClosedCohortEarningsHistory.start(initial_history, draw_index=3)
cohort = cohort.append(
    mortality=mortality_record,
    earnings_frame=actual_post_earnings_frame,
    lineage_digest=annual_frame_digest,
)
person_history = cohort.for_person(original_typed_identity)
state = cohort.amount_state(original_typed_identity, year=2016)
death = cohort.death_step(original_typed_identity)
restored = ClosedCohortEarningsHistory.from_json(
    cohort.to_json(), baseline=initial_history,
    expected_digest=cohort.digest, previous=previous_cohort,
)
```

## Composition and observation order

The initial history must end at 2014. The wrapper retains that baseline and
one existing fixed-roster history per original person. This reuses the
existing amount, nominal unit, provenance, domain and odd-year carry
validation. Each survivor's history appends the actual output for exactly
the next year; deceased persons' earlier rows remain unchanged. The
original identity map and cohort remain fixed even as the active roster
shrinks. `active_keys` reports the current survivors; `last_year` reports the
last explicitly observed transition, including empty post-extinction years.

The caller first executes the existing mortality step, then aging and the
actual earnings step on survivors, preserving all private generator state.
It supplies those observations to `append`; recording neither repeats the
generator nor replaces lag state with stored annual amounts. Tests compare
this minimal sequence with and without the observer using the actual
ordinary and correlated-refresh generators on invented fixtures, with
registry streams and fallback RNGs.

The survivor frame requires unique `person_id`, `year`, `age`, `sex`,
`earnings` and `earnings_domain` columns. IDs, years and ages must have NumPy
`int64` dtype, earnings `float64`, and domain `bool`. Sex must have a
string-compatible dtype and contain the recorded mortality labels. These
type requirements also apply to empty frames. No float-ID conversion is
performed; exact original signed/unsigned integers and textual IDs remain
reversible through the baseline identity map.

Mortality input IDs must equal the previous active roster. Earnings output
IDs must equal mortality survivors exactly. Target years advance one at a
time, with period index `year - 2014`, unchanged draw/realization/identity,
and the same mortality model, mortality source contract and RNG mode/horizon
throughout. Continuing registry ordinals cannot change. Mortality and
earnings source contracts remain distinct.

Each survivor's output age must equal its pre-mortality age plus one, with
unchanged sex. The actual survivor demographic tuples are retained in each
transition alongside mortality and annual lineage. Consecutive mortality
records must also advance pre-ages by one and preserve sex and RNG ordinals.
The first mortality record establishes demographics: the initial earnings
history has no age or sex evidence against which to verify it.

## Death, zero and unavailable amounts

Removal by the mortality step targeting year Y means no Y earnings row was
generated for that person, including when Y would otherwise carry the prior
amount. The person's history ends at Y−1. `amount_state` returns the existing
`known_amount`, `known_zero` or `unavailable` state for recorded years, and
`not_generated_after_mortality_step` for observed years after removal.
`death_step` returns the first removal record, or `None`; its target year and
digest identify the event without inventing a death date.

This distinguishes a supported zero from an outside-domain control zero,
death before generation, and an unobserved future year. Future queries and
years before 2014 refuse. Absence of generated earnings is not a factual
claim about income earned during a real person's death year. No post-death
zero or outside-domain row is created.

If all persons die, histories remain intact. Explicit empty mortality and
correctly typed empty earnings frames can continue the observed envelope.
Their year is established by the mortality transition. Ending observation
early does not establish any later year.

## Persistence and limits

Canonical JSON composes existing history and mortality documents and binds
the exact external baseline by digest. Loading invokes those validators,
then rechecks mortality continuity, survivor demographics, original cohort,
each person's final year and annual lineage. Unknown/duplicate fields and
inconsistent envelopes refuse. A trusted whole-record digest detects other
valid-looking edits; `previous` enforces preservation of earlier transitions
and amounts. Caller-supplied realization and source labels remain declarations,
not source admission, model acceptance or proof of a full execution.

`CoveredWageHistory` sidecars remain unchanged and bound to their original
history prefixes. The wrapper does not widen them, infer coverage, or erase
independently sourced wages after a modeled death. Further source attachments
need their own explicit contract. No statutory arithmetic or accepted Axiom
bridge is provided.

This prototype refuses births, entrants, resurrection, unrecorded attrition,
domain changes, mortality-model changes and extension beyond 2022. It retains
per-person nested history metadata for simplicity; this is not a population
storage format or a demonstration of the full registered projection.

The existing assembly mortality callback also performs the first-period
`ensure_draw` reset and writes its optional collector. Replacing it with the
standalone observer loses that behavior; calling both mortality paths draws
twice. Assembly-aware integration remains separate work. Frozen engine
code, gates, inputs and historical evidence are unchanged. The new module's
explicit historical-source exclusion is guarded by the transitive import
reachability test.
