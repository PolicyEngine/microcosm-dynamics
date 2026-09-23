"""Track A assembly for DynaSim scorecard exercise 1 (plan item A5).

Exercise 1 is the change in average Social Security benefits by age group
in 2030 when every annual COLA from the first reformed increase is one
percentage point lower.  This package wires the six Track A work items
together on the unmodified ``engine.loop.ProjectionEngine``:

* A3 ``cohorts.psid2010`` supplies the opening states: the 2011 wave
  (opening 2010) of R0-R5 and the 2009 wave (opening 2008) of R6
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
* A1's specification defines the registered rows
  (:mod:`~populace_dynamics.cola_track_a.config`);
* committed sources bind the realized COLA history and the oracle's
  statutory parameters in a registered run
  (:mod:`~populace_dynamics.cola_track_a.statutory`).

Every output is labelled *Python oracle (not Axiom)* and *fixed-path
mechanical incidence*; outputs on the PSID cohort also carry *PSID-seeded
closed cohort*, and outputs on the invented cohort
(:mod:`~populace_dynamics.cola_track_a.invented`) carry the invented-data
labels instead.  Every convention is a
:class:`~populace_dynamics.cola_track_a.config.TrackAConfig` field: Max
ruled the plan's section 6 decisions and A1 referee question 11 on
2026-09-23 (:func:`~populace_dynamics.cola_track_a.config.max_rulings`,
decision records d074 and d075); the other
conventions are builder defaults
(:func:`~populace_dynamics.cola_track_a.config.builder_defaults`), fixed
only by A1 ratification and the issue #42 registration.

The package is opt-in.  Nothing in the historical projection, estimates
or evidence reducers imports it.
"""

from populace_dynamics.cola_track_a.config import (
    DRY_RUN_HEADER,
    INVENTED_COHORT_LABEL,
    MAX_RULINGS,
    POPULATIONS,
    REGISTERED_ROWS,
    ROWS_NOT_BUILT,
    TRACK_A_LABELS,
    TrackAConfig,
    builder_defaults,
    max_rulings,
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
    "MAX_RULINGS",
    "POPULATIONS",
    "REGISTERED_ROWS",
    "ROWS_NOT_BUILT",
    "TRACK_A_LABELS",
    "TrackACohort",
    "TrackAConfig",
    "TrackAInputs",
    "builder_defaults",
    "max_rulings",
    "prepare_track_a_cohort",
    "run_track_a",
]
