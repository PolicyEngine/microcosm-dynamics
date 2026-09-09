# Opt-in claiming state successor

`populace_dynamics.engine.claiming.apply_claiming` corrects the existing
behavioral no-draw contract for observed disability conversions and previously
claimed people. It is available through an explicit module import. The
registered historical function in `engine.steps` and its assembly remain
unchanged.

## State contract

The adapter draws a behavioral plan only when all four conditions hold:

- `claim_age` is missing.
- Age is at least 50.
- `di_converted` is false.
- The person has not already claimed.

As in the historical adapter, absent or null conversion and claiming flags
are treated as false. This preserves the existing missing-value disposition;
it does not establish that an unknown upstream event was observed not to occur.
The `age` and `sex` columns are still required for all input frames.

`claim_age` represents a planned behavioral age. A conversion with no existing
plan retains a null age, becomes claimed, and receives the current year as its
claim year if it was not already claimed. Existing plans are preserved. A
previously claimed person's claim year is preserved, including a missing year.
Persisted `claimed=True` prevents a new plan from being drawn after the annual
conversion event flag clears. No placeholder age or new lifetime conversion
field is introduced.

## Explicit injection

The successor reuses `ClaimingSchedule` and the `PeriodModules.claiming`
interface:

```python
from dataclasses import replace
from functools import partial

from populace_dynamics.engine.claiming import apply_claiming
from populace_dynamics.engine.loop import ProjectionEngine

# Supply an existing set of period modules and a caller-owned schedule.
successor_modules = replace(
    modules,
    claiming=partial(apply_claiming, schedule=schedule),
)
engine = ProjectionEngine(successor_modules)
```

The opt-in module must remain outside the historical registered call graph.
It does not promote or replay a scientific candidate, change a locked gate,
or establish benefit-level acceptance. The integration test uses the actual
annual loop and its registry with explicitly synthetic injections for the
other steps; it does not run all eight fitted models.

## Random streams and scope

The PMFs, sex grouping, nearest-reference-year rule (including earlier-year
tie breaking), age-50 threshold, and `ProjectionModule.CLAIMING` stream are
unchanged. Under `ProjectionRNGRegistry`, each eligible person's draw agrees
with the historical adapter when the same stable ordinal is retained.
Removing an ineligible row or changing row order does not change another
person's keyed draw. Converted and previously claimed rows do not need a
claiming PMF for their sex or a claiming ordinal.

Without a registry, the injected batch generator draws fewer values. This
can shift same-seed realizations for other people and subsequent sex groups.
The successor remains reproducible for the same input and seed; cross-version
bitwise parity is not claimed for this fallback. It does not burn discarded
draws to mimic the historical bug.

The adapter consumes the conversion event supplied by the disability step.
It does not infer statutory conversion timing, insured status, quarters of
coverage, PIA, or benefits. A changed upstream conversion definition or
promotion into registered historical execution requires separate work.
