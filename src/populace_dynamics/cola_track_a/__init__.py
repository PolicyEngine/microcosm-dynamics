"""Track A assembly for DynaSim scorecard exercise 1 (plan item A5).

Exercise 1 is the change in average Social Security benefits by age group
in 2030 when every annual COLA from the first reformed increase is one
percentage point lower.  This package wires the six Track A work items
together on the unmodified ``engine.loop.ProjectionEngine``:

* A3 ``cohorts.psid2010`` supplies the 2010 opening state
  (:mod:`~populace_dynamics.cola_track_a.opening`);
* A2 ``data.tr2008`` supplies the year-aware mortality substitute
  (:mod:`~populace_dynamics.cola_track_a.mortality`), the COLA path and
  the AWI;
* A4 ``engine.di_entitlement`` supplies DI incidence, recovery,
  conversion and DI-aware mortality
  (:mod:`~populace_dynamics.cola_track_a.adapters`);
* A6 ``scenario_benefits`` supplies the per-PIA scenario paths
  (:mod:`~populace_dynamics.cola_track_a.benefits`);
* A7 ``estimates.cola_age_profile`` tabulates the five-group statistic
  (:mod:`~populace_dynamics.cola_track_a.runner`);
* A1's draft specification defines the registered rows
  (:mod:`~populace_dynamics.cola_track_a.config`).

Every output is labelled *Python oracle (not Axiom)* and *fixed-path
mechanical incidence*; outputs on the PSID cohort also carry *PSID-seeded
closed cohort*, and outputs on the invented cohort
(:mod:`~populace_dynamics.cola_track_a.invented`) carry the invented-data
labels instead.  Nothing here is ratified: every open choice is a
:class:`~populace_dynamics.cola_track_a.config.TrackAConfig` field.

The package is opt-in.  Nothing in the historical projection, estimates
or evidence reducers imports it.
"""

from populace_dynamics.cola_track_a.config import (
    DRY_RUN_HEADER,
    INVENTED_COHORT_LABEL,
    REGISTERED_ROWS,
    ROWS_NOT_BUILT,
    TRACK_A_LABELS,
    TrackAConfig,
    pending_decisions,
)
from populace_dynamics.cola_track_a.opening import (
    TrackACohort,
    prepare_track_a_cohort,
)
from populace_dynamics.cola_track_a.runner import (
    TrackAInputs,
    run_track_a,
)

__all__ = [
    "DRY_RUN_HEADER",
    "INVENTED_COHORT_LABEL",
    "REGISTERED_ROWS",
    "ROWS_NOT_BUILT",
    "TRACK_A_LABELS",
    "TrackACohort",
    "TrackAConfig",
    "TrackAInputs",
    "pending_decisions",
    "prepare_track_a_cohort",
    "run_track_a",
]
