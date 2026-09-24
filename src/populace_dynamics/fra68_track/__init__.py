"""DynaSim exercise 3 (full retirement age to 68) on the Track A pipeline.

Exercise 3 is the change in average Social Security benefits by age group
in 2030 when the full retirement age rises to 68 (Urban Institute 2010,
Table 1: "Gradually increase FRA beginning in 2010 until it reaches 68 for
those turning 62 in 2022 and later").  It reuses Track A (exercise 1)
whole: the same populations, projection, TR2008 inputs, COLA path, benefit
paths and A7 statistic.  What this package adds:

* :mod:`~populace_dynamics.fra68_track.reform`: the reform switch, an
  override of the oracle's FRA schedule (three frozen phase-in readings,
  P1-P3) and of the widow(er)'s reduction span, adding no statutory rule
  coverage;
* :mod:`~populace_dynamics.fra68_track.benefits`: baseline and reform
  amounts per person from one projected state (fixed claim ages under the
  primary convention C0; the C1/C2 claiming transforms);
* :mod:`~populace_dynamics.fra68_track.config`: rows F0-F8 and the
  decisions awaiting Max (decision record d188), each an explicit field
  whose default is the plan's recommendation;
* :mod:`~populace_dynamics.fra68_track.runner`: the run, with Track A's
  provenance, value checks and registration-pointer guard.

The specification is the E1 draft
``docs/design/urban2010_fra68_comparison.md``, which is not ratified.
Every output is labelled *Python oracle (not Axiom)*; outputs on the
invented cohort carry the invented-data labels.  The package is opt-in:
nothing in the historical projection, the estimates or the evidence
reducers imports it.
"""

from populace_dynamics.fra68_track.config import (
    DRY_RUN_HEADER,
    PENDING_DECISIONS,
    STATISTIC_ID,
    ClaimingResponse,
    FRA68Config,
    FRA68Row,
    SurvivorRetirementAge,
    builder_defaults,
    pending_decisions,
    registered_rows,
)
from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    FRASchedule,
    reform_parameters,
    survivor_parameters,
)
from populace_dynamics.fra68_track.runner import run_fra68

__all__ = [
    "DRY_RUN_HEADER",
    "PENDING_DECISIONS",
    "SCHEDULES",
    "STATISTIC_ID",
    "ClaimingResponse",
    "FRA68Config",
    "FRA68Row",
    "FRASchedule",
    "SurvivorRetirementAge",
    "builder_defaults",
    "pending_decisions",
    "reform_parameters",
    "registered_rows",
    "run_fra68",
    "survivor_parameters",
]
