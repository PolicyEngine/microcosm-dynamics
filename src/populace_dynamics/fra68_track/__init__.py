"""DynaSim exercise 3 (full retirement age to 68) on the Track A pipeline.

Exercise 3 is the change in average Social Security benefits by age group
in 2030 when the full retirement age rises to 68 (Urban Institute 2010,
Table 1: "Gradually increase FRA beginning in 2010 until it reaches 68 for
those turning 62 in 2022 and later").  It reuses Track A (exercise 1).
:mod:`~populace_dynamics.fra68_track.reform` is the reform switch: an
override of the oracle's FRA schedule (three frozen phase-in readings,
P1-P3) and of the widow(er)'s reduction span, adding no statutory rule
coverage.

The package is opt-in: nothing in the historical projection, the
estimates or the evidence reducers imports it.
"""

from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    FRASchedule,
    reform_parameters,
    survivor_parameters,
)

__all__ = [
    "SCHEDULES",
    "FRASchedule",
    "reform_parameters",
    "survivor_parameters",
]
