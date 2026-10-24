"""Does a projection's early years depend on its end year?

INVENTED DATA ONLY.  No PSID, frame or survey record is read.

``docs/design/open_population.md`` section 2.9 cites this script.  It runs
the existing engine loop (``engine/loop.py``) twice on the same invented
roster, once to ``SHORT_END`` and once to ``LONG_END``, and compares the
person-year slices the two runs share.  It does this twice:

* closed: births only (``baselines/fertility.py``'s ASFR step);
* open: the same, plus immigrant cohorts scheduled for every year through
  the run's end year with ``engine/entrant_schedule.py``.

Run from the repository root with the package importable::

    python docs/design/open_population_evidence/horizon_dependence.py

The output this script printed for the design is committed beside it as
``horizon_dependence.txt``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from populace_dynamics.baselines.fertility import AsfrFertilityStep
from populace_dynamics.engine.entrant_schedule import build_entrant_schedule
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    MaritalStepResult,
    PeriodModules,
    ProjectionEngine,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.rng import ProjectionModule
from populace_dynamics.engine.steps import advance_age

START = 2025
SHORT_END = 2035
LONG_END = 2045
N_PEOPLE = 400
#: Invented constant hazards: 5 percent die each year; women 18-44 give
#: birth with probability 0.15 a year.
DEATH_PROBABILITY = 0.05
BIRTH_RATE = 0.15
#: Invented immigrant control, in thousands of weighted persons a year.
INFLOW_THOUSANDS = 0.003


def mortality(frame, context, rng):
    """Person-keyed deaths, as ``steps.apply_mortality`` draws them."""
    del rng
    uniform = np.array(
        [
            context.person_generator(
                ProjectionModule.MORTALITY, person_id
            ).random()
            for person_id in frame["person_id"]
        ]
    )
    return frame.loc[uniform >= DEATH_PROBABILITY].reset_index(drop=True)


def unchanged(frame, context, rng):
    return frame


def no_marriages(frame, context, rng):
    return MaritalStepResult(sim_years=frame.iloc[0:0], births=pd.DataFrame())


def no_composition(frame, context, marital, rng):
    return frame


MODULES = PeriodModules(
    mortality=mortality,
    aging=advance_age,
    marital_core=no_marriages,
    fertility=AsfrFertilityStep(
        asfr=lambda year: {age: BIRTH_RATE for age in range(18, 45)}
    ),
    disability=unchanged,
    earnings=unchanged,
    claiming=unchanged,
    household_composition=no_composition,
)

INITIAL = pd.DataFrame(
    {
        "person_id": np.arange(1, N_PEOPLE + 1),
        "year": START,
        "age": np.random.default_rng(1).integers(18, 40, N_PEOPLE),
        "sex": np.where(np.arange(N_PEOPLE) % 2 == 0, "female", "male"),
        "weight": 1.0,
        "start_weight": 1.0,
    }
)

DONOR = pd.DataFrame(
    {
        "person_id": [9001, 9002, 9003],
        "weight": [1.0, 2.0, 1.0],
        "entry_age": [25, 30, 5],
        "is_female": [True, False, True],
        "source_year": 2024,
        "peinusyr": 1,
        "prcitshp": 4,
        "penatvty": 100,
        "foreign_born": [True, True, True],
    }
)


def project(end_year: int, *, with_entrants: bool):
    allocator = SyntheticPersonIdAllocator(
        N_PEOPLE + 1, reserved_real_ids=frozenset(range(1, N_PEOPLE + 1))
    )
    metadata = {"synthetic_id_allocator": allocator}
    if with_entrants:
        schedule = build_entrant_schedule(
            DONOR,
            {
                year: INFLOW_THOUSANDS
                for year in range(START + 1, end_year + 1)
            },
            allocator=allocator,
            roster_columns=list(INITIAL.columns),
        )
        metadata[SCHEDULED_ENTRIES_KEY] = schedule.as_metadata()
    return ProjectionEngine(MODULES).project(
        INITIAL, end_year=end_year, draw_index=0, metadata=metadata
    )


def compare(with_entrants: bool) -> None:
    short = project(SHORT_END, with_entrants=with_entrants)
    long = project(LONG_END, with_entrants=with_entrants)
    label = (
        "open (births and scheduled entrants)"
        if with_entrants
        else ("closed (births only)")
    )
    print(f"== {label}: end year {SHORT_END} against {LONG_END}")
    for offset, year in enumerate(range(START + 1, SHORT_END + 1), start=1):
        a = short.slices[offset][["person_id", "age"]].reset_index(drop=True)
        b = long.slices[offset][["person_id", "age"]].reset_index(drop=True)
        verdict = "identical" if a.equals(b) else "different"
        print(f"{year}: rows {len(a)} and {len(b)}; slices {verdict}")


if __name__ == "__main__":
    compare(with_entrants=False)
    compare(with_entrants=True)
