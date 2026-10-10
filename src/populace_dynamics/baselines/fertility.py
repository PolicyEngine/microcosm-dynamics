"""Opt-in ASFR fertility for open-population projections (report-only).

NOT GATED, REPORT-ONLY.  This step draws births from a baseline's
single-age fertility schedule (:meth:`Baseline.asfr`).  It is a separate
path from the gated candidate-16 fertility law (``models/family_
transitions/components/fertility.py``, drawn by ``engine.marital`` and
materialized by ``engine.steps.apply_fertility``; gate 2 locks its
``asfr.*`` cells), which it neither imports nor changes.  Nothing
constructs it by default: the registered Track A and FRA-68 projections
are closed cohorts whose fertility slot draws no births
(``cola_track_a.adapters.adopt_marital_state``), and no registered test
uses this module.

The draw.  In projection year ``t`` every woman (``sex == "female"``)
whose ``age`` column, after step 2 (aging, which sets it to the age
attained in ``t``), is a key of ``asfr(t)`` gives birth with probability
``asfr(t)[age]``: one Bernoulli draw per woman-year.  ASFR is births per
woman, so using it as a probability needs every rate in [0, 1] (refused
otherwise); at most one birth per woman-year is drawn, so multiple
births in a year are not represented.  The expected number of births is
the sum of the rates over the exposed women.  Using the attained age for
the age at birth is a builder convention (a half-year average offset).

Randomness is the engine's: each woman's uniform comes from the RNG
registry's tagged child stream ``(period, FERTILITY, ASFR_STREAM_TAG,
person ordinal)``, so a woman's draw does not depend on who else is in
the frame, and the tag keeps it apart from the module stream and from
person streams.  Births become child rows through
:func:`populace_dynamics.engine.steps.materialize_maternal_births`
(imported read-only): new identifiers from the projection's allocator,
age 0, the mother's weight and household, and a 50/50 sex draw from the
module stream the loop passes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from populace_dynamics.engine.loop import (
    MaritalReaderStep,
    MaritalStepResult,
    PeriodContext,
)
from populace_dynamics.engine.rng import ProjectionModule
from populace_dynamics.engine.steps import materialize_maternal_births

__all__ = [
    "ASFR_FERTILITY_LABEL",
    "ASFR_STREAM_TAG",
    "AsfrFertilityStep",
    "draw_asfr_births",
    "expected_births",
]

ASFR_FERTILITY_LABEL = "not gated, report-only"
#: Component tag of the per-woman fertility streams ("AF").
ASFR_STREAM_TAG = 0x4146


def _validated_rates(rates: Mapping[int, float]) -> dict[int, float]:
    out = {}
    for age, rate in rates.items():
        value = float(rate)
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(
                f"ASFR at age {age} is {value!r}; the Bernoulli draw needs "
                "a rate in [0, 1]"
            )
        out[int(age)] = value
    return out


def _exposed(
    frame: pd.DataFrame, rates: Mapping[int, float]
) -> tuple[np.ndarray, np.ndarray]:
    """Row positions of exposed women and their rates."""
    missing = {"person_id", "age", "sex"} - set(frame.columns)
    if missing:
        raise ValueError(
            f"fertility frame is missing columns {sorted(missing)}"
        )
    age = frame["age"].to_numpy(dtype=np.int64)
    female = frame["sex"].astype(str).to_numpy() == "female"
    rate = np.array([rates.get(int(value), 0.0) for value in age])
    exposed = np.flatnonzero(female & np.isin(age, list(rates)))
    return exposed, rate[exposed]


def expected_births(frame: pd.DataFrame, rates: Mapping[int, float]) -> float:
    """Sum of the rates over the women the step exposes."""
    _, rate = _exposed(frame, _validated_rates(rates))
    return float(rate.sum())


def draw_asfr_births(
    frame: pd.DataFrame,
    context: PeriodContext,
    rates: Mapping[int, float],
) -> pd.DataFrame:
    """One Bernoulli birth draw per exposed woman; returns birth records.

    Columns ``parent_person_id`` and ``birth_year`` (the step-3 birth
    record shape :func:`materialize_maternal_births` reads).
    """
    if context.rng_registry is None:
        raise RuntimeError(
            "ASFR fertility needs the loop's RNG registry (person-keyed "
            "streams)"
        )
    exposed, rate = _exposed(frame, _validated_rates(rates))
    person_ids = frame["person_id"].to_numpy()[exposed]
    uniforms = np.array(
        [
            context.rng_registry.tagged_child_generator(
                context.period_index,
                ProjectionModule.FERTILITY,
                ASFR_STREAM_TAG,
                context.person_ordinals[person_id],
            ).random()
            for person_id in person_ids
        ],
        dtype=np.float64,
    )
    mothers = person_ids[uniforms < rate]
    return pd.DataFrame(
        {
            "parent_person_id": pd.Series(mothers, dtype="int64"),
            "birth_year": pd.Series(
                np.full(len(mothers), int(context.year)), dtype="int64"
            ),
        }
    )


@dataclass(frozen=True)
class AsfrFertilityStep:
    """A ``PeriodModules.fertility`` adapter drawing births from ASFR.

    ``asfr`` maps a year to ``{age: births per woman}`` (for example a
    baseline's :meth:`asfr`).  ``marital_reader``, when given, runs first
    on the frame (for example Track A's ``adopt_marital_state``, the
    merge point the fertility slot otherwise fills).  ``birth_log[year]``
    records the year's birth records, and ``expected_log[year]`` the
    expected number of births, when given.
    """

    asfr: Callable[[int], Mapping[int, float]]
    marital_reader: MaritalReaderStep | None = None
    birth_log: MutableMapping[int, pd.DataFrame] | None = None
    expected_log: MutableMapping[int, float] | None = None
    label: str = ASFR_FERTILITY_LABEL

    def __post_init__(self) -> None:
        if self.label != ASFR_FERTILITY_LABEL:
            raise ValueError(
                f"the ASFR fertility step is labelled {ASFR_FERTILITY_LABEL!r}"
            )

    def __call__(
        self,
        frame: pd.DataFrame,
        context: PeriodContext,
        marital: MaritalStepResult,
        rng: np.random.Generator,
    ) -> pd.DataFrame:
        current = frame
        if self.marital_reader is not None:
            current = self.marital_reader(frame, context, marital, rng)
        rates = self.asfr(int(context.year))
        births = draw_asfr_births(current, context, rates)
        if self.birth_log is not None:
            self.birth_log[int(context.year)] = births
        if self.expected_log is not None:
            self.expected_log[int(context.year)] = expected_births(
                current, rates
            )
        return materialize_maternal_births(current, births, context, rng)
