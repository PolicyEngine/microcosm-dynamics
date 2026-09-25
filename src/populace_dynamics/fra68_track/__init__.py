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
* :mod:`~populace_dynamics.fra68_track.config`: rows F0-F8, Max's
  rulings of 2026-09-24 (decision records d188 and d196;
  ``MAX_RULINGS``), each an explicit field that defaults to the ruling,
  and ``E1_RULINGS``, the A7 tabulation conventions E1 fixes, which every
  exercise-3 tabulation records against the E1 block header;
* :mod:`~populace_dynamics.fra68_track.runner`: the run, with Track A's
  provenance, value checks and registration-pointer guard.

The specification is E1, ``docs/design/urban2010_fra68_comparison.md``
(version ``e1-ratified-2``, status ``ratified_frozen``), which records
Max's rulings; merging ``e1-ratified-1`` under his authorization (d188
item (c)) ratified it.  ``e1-ratified-2`` amends only the C0 membership
guard (E1 sections 7, 12 and 27), after Registration 14's refusal and
before any statistic was recorded or the comparator seal opened; no
ruled field changes.
Every output is labelled *Python oracle (not Axiom)*; outputs on the
invented cohort carry the invented-data labels.  The package is opt-in:
nothing in the historical projection, the estimates or the evidence
reducers imports it.
"""

from populace_dynamics.fra68_track.config import (
    DRY_RUN_HEADER,
    E1_RULINGS,
    MAX_RULINGS,
    SPECIFICATION_ID,
    STATISTIC_ID,
    ClaimingResponse,
    FRA68Config,
    FRA68Row,
    SurvivorRetirementAge,
    builder_defaults,
    max_rulings,
    registered_rows,
    rulings_departures,
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
    "E1_RULINGS",
    "MAX_RULINGS",
    "SCHEDULES",
    "SPECIFICATION_ID",
    "STATISTIC_ID",
    "ClaimingResponse",
    "FRA68Config",
    "FRA68Row",
    "FRASchedule",
    "SurvivorRetirementAge",
    "builder_defaults",
    "max_rulings",
    "reform_parameters",
    "registered_rows",
    "rulings_departures",
    "run_fra68",
    "survivor_parameters",
]
