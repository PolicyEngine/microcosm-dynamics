"""SSDI disabled-worker entitlement adapters for the projection loop.

Track A item A4 of ``critical-path-cola-20260922.md``.  The certified M4
component (:mod:`populace_dynamics.engine.disability`) models self-reported
work limitation, which is a different concept from Social Security Disability
Insurance awards.  This module adds an entitlement component with the engine's
``FrameStep`` signature ``(frame, context, rng) -> frame``:

* :func:`apply_di_entitlement` is the step-5 (``PeriodModules.disability``)
  adapter.  Each projected year it draws, for every surviving person, at most
  one transition: disabled workers entitled at the start of the year convert
  to retired-worker status in the calendar year they attain the full
  retirement age (no draw) or otherwise face a recovery termination; every
  other person below FRA is exposed to award incidence per non-entitled
  population by age and sex.  The exposed set matches the fit's
  denominator: it includes previously recovered workers and retired-worker
  claimants below FRA, and it never consults insured status.  Converted
  workers are never exposed again.
* :func:`apply_di_aware_mortality` is the step-1 (``PeriodModules.mortality``)
  adapter.  It uses exactly the person-keyed uniform that
  :func:`populace_dynamics.engine.steps.apply_mortality` uses, so people who
  are not of disabled-worker origin die exactly as they would without it,
  while disabled workers (and, by default, converted former disabled workers)
  die at disabled-worker rates.  Deaths are the "death" termination; they
  happen in step 1 because the loop removes decedents there.  In the
  default multiplier death mode the NCHS 2000 base is averaged over the
  population model's own age bands, so a banded population model does not
  reshape the disabled-worker age profile within a band.
* :func:`prepare_opening_di_state` validates the opening disabled-worker
  stock (supplied by the A3 cohort builder) and can be the loop's
  ``initialize`` hook.
* :func:`di_stock_flow` reconciles ``stock_end = stock_start + awards +
  entrants - deaths - recoveries - conversions`` year by year.

Timing conventions (explicit, not ratified):

* Every rate is looked up at the start-of-year age ``year - 1 - birth_year``
  (the same age the mortality step sees before step 2 advances age).
* Mortality runs before the DI step, so a person awarded in year ``t`` first
  faces disabled-worker mortality in ``t + 1``.  A worker converted in ``t``
  is a converted (``di_origin``) person from ``t + 1``.
* FRA comes from the statute's birth-year schedule (42 USC 416(l)), injected
  as ``fra_schedule`` (for example :meth:`SSAParameters.fra_months`, which
  reads the pinned policyengine-us parameter tree); it is never re-typed
  here.  FRA is attained in calendar year
  ``birth_year + (birth_month - 1 + fra_months) // 12``, with
  ``spec.assumed_birth_month`` when the frame has no ``birth_month``.
  Nobody is exposed to award incidence in or after that year.
* ``di_award_year`` is the calendar year the model adds the award; SSA's
  entitlement (onset plus the five-month waiting period, often retroactive)
  can precede it.  ``di_award_age`` is ``di_award_year - birth_year``, the
  select age of the select-and-ultimate basis.  The exposure-clock choice for
  COLA credits belongs to the A6 benefit calculator, which reads these
  columns.
* ``di_converted`` is a one-year event flag, like the M4 flag that
  :func:`populace_dynamics.engine.claiming.apply_claiming` reads to mark a
  conversion as claimed; ``di_conversion_year`` persists.  A claiming step
  that should not draw retirement plans for entitled disabled workers must
  exclude ``di_entitled`` rows itself; this module does not change claiming.

Random numbers: step 5 draws one uniform per exposed or entitled person from
``ProjectionRNGRegistry.tagged_child_generator(period, DISABILITY,
DI_ENTITLEMENT_COMPONENT_TAG, ordinal)``, a stable person-keyed stream (the
ordinal is the canonical ``person_id`` rank the loop assigns), so one
person's draw does not depend on anyone else's state.  Without a registry the
injected generator is consumed once per row in ``person_id`` order.
"""

from __future__ import annotations

from collections.abc import (
    Callable,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence,
)
from typing import Any, Protocol

import numpy as np
import pandas as pd

from populace_dynamics.engine.di_entitlement_rates import (
    SEXES,
    DIEntitlementRates,
    validate_age_bands,
)
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import ProjectionModule

__all__ = [
    "DI_ENTITLEMENT_COMPONENT_TAG",
    "DI_EVENTS",
    "DI_STATE_COLUMNS",
    "FraSchedule",
    "apply_di_aware_mortality",
    "apply_di_entitlement",
    "di_prevalence",
    "di_stock_flow",
    "fra_attainment_year",
    "fra_schedule_from_parameters",
    "prepare_opening_di_state",
]

#: Component tag for the DI entitlement draw below the DISABILITY stream.
DI_ENTITLEMENT_COMPONENT_TAG = 0xD1E1
DI_STATE_COLUMNS = (
    "di_entitled",
    "di_award_year",
    "di_award_age",
    "di_recovery_year",
    "di_conversion_year",
    "di_converted",
    "di_event",
)
DI_EVENTS = (
    "opening",
    "none",
    "continuing",
    "award",
    "recovery",
    "conversion",
)
_SEX_INDEX = {sex: index for index, sex in enumerate(SEXES)}

FraSchedule = Callable[[int], int]
"""Birth year -> full retirement age in months (42 USC 416(l))."""


class _HasFraMonths(Protocol):
    def fra_months(self, birth_year: int) -> int: ...


class PopulationMortality(Protocol):
    def probabilities(self, frame: pd.DataFrame) -> np.ndarray: ...


def fra_schedule_from_parameters(params: _HasFraMonths) -> FraSchedule:
    """Adapt :class:`populace_dynamics.ss.params.SSAParameters`."""
    return params.fra_months


def _require(frame: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing columns {missing}")


def _int_array(frame: pd.DataFrame, column: str) -> np.ndarray:
    series = frame[column]
    if series.isna().any():
        raise ValueError(f"column {column!r} has missing values")
    return series.to_numpy(dtype=np.int64)


def _sex_index(frame: pd.DataFrame) -> np.ndarray:
    labels = frame["sex"].astype(str).to_numpy()
    out = np.full(len(labels), -1, dtype=np.int64)
    for label, index in _SEX_INDEX.items():
        out[labels == label] = index
    if (out < 0).any():
        unknown = sorted(set(labels[out < 0]))
        raise ValueError(f"unknown sex labels {unknown}; expected {SEXES}")
    return out


def _nullable_years(frame: pd.DataFrame, column: str) -> pd.array:
    if column in frame:
        return pd.array(frame[column], dtype="Int64")
    return pd.array([pd.NA] * len(frame), dtype="Int64")


def _bool_column(frame: pd.DataFrame, column: str) -> np.ndarray:
    series = frame[column]
    if series.isna().any():
        raise ValueError(f"column {column!r} has missing values")
    if not (
        pd.api.types.is_bool_dtype(series.dtype)
        or series.isin([True, False]).all()
    ):
        raise ValueError(f"column {column!r} must be boolean")
    return series.to_numpy(dtype=bool)


def fra_attainment_year(
    birth_year: np.ndarray,
    fra_schedule: FraSchedule | _HasFraMonths,
    *,
    birth_month: np.ndarray | None = None,
    assumed_birth_month: int = 7,
) -> np.ndarray:
    """Calendar year in which each person attains full retirement age."""
    schedule = (
        fra_schedule.fra_months
        if hasattr(fra_schedule, "fra_months")
        else fra_schedule
    )
    births = np.asarray(birth_year, dtype=np.int64)
    unique, inverse = np.unique(births, return_inverse=True)
    unique_months = np.empty(len(unique), dtype=np.int64)
    for position, value in enumerate(unique):
        months = int(schedule(int(value)))
        if not 12 * 62 <= months <= 12 * 70:
            raise ValueError(
                f"FRA of {months} months for birth year {value} is outside "
                "the statutory range"
            )
        unique_months[position] = months
    fra_months = unique_months[inverse.reshape(-1)]
    if birth_month is None:
        month = np.full(len(births), int(assumed_birth_month), dtype=np.int64)
    else:
        month = np.asarray(birth_month, dtype=np.int64)
        if ((month < 1) | (month > 12)).any():
            raise ValueError("birth_month must lie in [1, 12]")
    return births + (month - 1 + fra_months) // 12


def _birth_months(frame: pd.DataFrame) -> np.ndarray | None:
    if "birth_month" not in frame:
        return None
    return _int_array(frame, "birth_month")


def _check_age(
    frame: pd.DataFrame,
    birth_year: np.ndarray,
    expected_age_year: int,
    rates: DIEntitlementRates,
    label: str,
) -> None:
    if not rates.spec.validate_age_column or "age" not in frame:
        return
    age = _int_array(frame, "age")
    expected = expected_age_year - birth_year
    if (age != expected).any():
        bad = int(np.flatnonzero(age != expected)[0])
        raise ValueError(
            f"{label}: age {age[bad]} disagrees with {expected_age_year} - "
            f"birth_year {birth_year[bad]}; the DI component keys every rate "
            "on birth year (set validate_age_column=False to override)"
        )


def _check_year(frame: pd.DataFrame, year: int, label: str) -> None:
    if "year" in frame and len(frame):
        years = set(frame["year"].astype(int).unique())
        if years != {year}:
            raise ValueError(f"{label} expects year {year}, got {years}")


def _select_inputs(
    frame: pd.DataFrame, year: int, mask: np.ndarray, rates: DIEntitlementRates
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Select age and duration for rows of ``mask`` under the select basis."""
    if rates.spec.termination_basis != "select_and_ultimate":
        return None, None
    award_year = _nullable_years(frame, "di_award_year")
    award_age = _nullable_years(frame, "di_award_age")
    missing = mask & (
        np.asarray(pd.isna(award_year)) | np.asarray(pd.isna(award_age))
    )
    if missing.any():
        raise ValueError(
            "select-and-ultimate termination rates need di_award_year and "
            f"di_award_age for every disabled-worker-origin person; "
            f"{int(missing.sum())} are missing"
        )
    select_age = np.zeros(len(frame), dtype=np.int64)
    duration = np.zeros(len(frame), dtype=np.int64)
    rows = np.flatnonzero(mask)
    select_age[rows] = award_age[rows].to_numpy(dtype=np.int64)
    duration[rows] = year - 1 - award_year[rows].to_numpy(dtype=np.int64)
    if (duration[rows] < 0).any():
        raise ValueError("an award year lies after the projection year")
    return select_age, duration


def prepare_opening_di_state(
    frame: pd.DataFrame,
    *,
    rates: DIEntitlementRates,
    fra_schedule: FraSchedule | _HasFraMonths,
) -> pd.DataFrame:
    """Validate the opening DI stock and add the derived DI columns.

    Required: ``person_id``, ``year`` (one start year), ``sex``,
    ``birth_year`` and a boolean ``di_entitled`` (the A3 opening stock; the
    component refuses to guess it).  Optional: ``di_award_year`` (award year
    of an entitled person, at or before the start year) and
    ``di_conversion_year`` (a person converted from disabled-worker to
    retired-worker status before the start year, for DI-origin mortality).
    Use with :func:`functools.partial` as ``PeriodModules.initialize``.
    """
    _require(
        frame,
        ("person_id", "year", "sex", "birth_year", "di_entitled"),
        "opening DI frame",
    )
    out = frame.copy()
    if out.empty:
        for column in DI_STATE_COLUMNS:
            if column not in out:
                out[column] = pd.Series(dtype="object")
        return out
    years = set(out["year"].astype(int).unique())
    if len(years) != 1:
        raise ValueError("the opening DI frame must carry one start year")
    start_year = years.pop()
    birth_year = _int_array(out, "birth_year")
    _sex_index(out)
    _check_age(out, birth_year, start_year, rates, "opening DI frame")
    entitled = _bool_column(out, "di_entitled")
    award_year = _nullable_years(out, "di_award_year")
    conversion_year = _nullable_years(out, "di_conversion_year")
    recovery_year = _nullable_years(out, "di_recovery_year")
    has_award = ~np.asarray(pd.isna(award_year))
    converted = ~np.asarray(pd.isna(conversion_year))
    recovered = ~np.asarray(pd.isna(recovery_year))
    if (has_award & ~(entitled | converted | recovered)).any():
        raise ValueError(
            "an opening award year is given for a person who is not "
            "entitled, converted, or recovered"
        )
    award_values = award_year.fillna(start_year).to_numpy(dtype=np.int64)
    if (award_values > start_year).any():
        raise ValueError("an opening award year lies after the start year")
    if (entitled & converted).any():
        raise ValueError("a person cannot be both entitled and converted")
    for label, values in (
        ("conversion", conversion_year),
        ("recovery", recovery_year),
    ):
        filled = values.fillna(start_year).to_numpy(dtype=np.int64)
        if (filled > start_year).any():
            raise ValueError(
                f"an opening {label} year lies after the start year"
            )
    fra_year = fra_attainment_year(
        birth_year,
        fra_schedule,
        birth_month=_birth_months(out),
        assumed_birth_month=rates.spec.assumed_birth_month,
    )
    past_fra = entitled & (fra_year <= start_year)
    if past_fra.any():
        raise ValueError(
            f"{int(past_fra.sum())} opening disabled workers have already "
            "attained FRA; they should enter as converted, not entitled"
        )
    out["di_entitled"] = entitled
    out["di_award_year"] = award_year
    award_age = pd.array([pd.NA] * len(out), dtype="Int64")
    award_age[has_award] = award_values[has_award] - birth_year[has_award]
    out["di_award_age"] = award_age
    out["di_recovery_year"] = recovery_year
    out["di_conversion_year"] = conversion_year
    out["di_converted"] = np.zeros(len(out), dtype=bool)
    out["di_event"] = np.full(len(out), "opening", dtype=object)
    di_origin = entitled | converted
    _select_inputs(out, start_year + 1, di_origin, rates)
    return out


def _normalize_new_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Give loop-created synthetic children a not-entitled DI state."""
    missing = [column for column in DI_STATE_COLUMNS if column not in frame]
    if missing:
        raise ValueError(
            f"DI state columns {missing} are absent; run "
            "prepare_opening_di_state on the opening slice"
        )
    unset = frame["di_entitled"].isna().to_numpy()
    if not unset.any():
        return frame
    synthetic = (
        frame.get("synthetic_entry", pd.Series(False, index=frame.index))
        .fillna(False)
        .to_numpy(dtype=bool)
    )
    if (unset & ~synthetic).any():
        raise ValueError(
            "persons without a DI state entered the frame; only loop-created "
            "synthetic entrants are initialized automatically"
        )
    out = frame.copy()
    out["di_entitled"] = out["di_entitled"].astype(object)
    out.loc[unset, "di_entitled"] = False
    out["di_entitled"] = out["di_entitled"].astype(bool)
    out["di_converted"] = out["di_converted"].fillna(False).astype(bool)
    out.loc[unset, "di_event"] = "none"
    return out


def _person_uniforms(
    person_ids: np.ndarray,
    needed: np.ndarray,
    context: PeriodContext,
    rng: np.random.Generator,
    module: ProjectionModule,
    component_tag: int | None,
) -> np.ndarray:
    """One uniform per row (``person_ids`` sorted), NaN where not needed."""
    if context.rng_registry is None:
        return rng.random(len(person_ids))
    out = np.full(len(person_ids), np.nan)
    for index in np.flatnonzero(needed):
        person_id = person_ids[index]
        if component_tag is None:
            generator = context.person_generator(module, person_id)
        else:
            try:
                ordinal = context.person_ordinals[person_id]
            except KeyError as error:
                raise KeyError(
                    f"no stable RNG ordinal for person {person_id!r}"
                ) from error
            generator = context.rng_registry.tagged_child_generator(
                context.period_index, module, component_tag, ordinal
            )
        out[index] = generator.random()
    return out


def apply_di_entitlement(
    frame: pd.DataFrame,
    context: PeriodContext,
    rng: np.random.Generator,
    *,
    rates: DIEntitlementRates,
    fra_schedule: FraSchedule | _HasFraMonths,
) -> pd.DataFrame:
    """Step-5 adapter: conversion, recovery, and award incidence."""
    _require(
        frame,
        ("person_id", "year", "sex", "birth_year"),
        "DI entitlement frame",
    )
    if frame["person_id"].duplicated().any():
        raise ValueError("DI entitlement frame has duplicate person_id rows")
    year = int(context.year)
    if frame.empty:
        return frame.copy()
    _check_year(frame, year, "DI entitlement step (run after aging)")
    frame = _normalize_new_rows(frame)
    order = np.argsort(frame["person_id"].to_numpy(), kind="stable")
    ordered = frame.iloc[order].reset_index(drop=True)
    person_ids = ordered["person_id"].to_numpy()
    birth_year = _int_array(ordered, "birth_year")
    _check_age(ordered, birth_year, year, rates, "DI entitlement step")
    sex = _sex_index(ordered)
    start_age = year - 1 - birth_year
    entitled = _bool_column(ordered, "di_entitled")
    conversion_year = _nullable_years(ordered, "di_conversion_year")
    converted_before = ~np.asarray(pd.isna(conversion_year))
    if (entitled & converted_before).any():
        raise ValueError("a person is both entitled and already converted")
    fra_year = fra_attainment_year(
        birth_year,
        fra_schedule,
        birth_month=_birth_months(ordered),
        assumed_birth_month=rates.spec.assumed_birth_month,
    )
    overdue = entitled & (fra_year < year)
    if overdue.any():
        raise ValueError(
            f"{int(overdue.sum())} entitled disabled workers passed FRA "
            "without conversion"
        )

    convert = entitled & (fra_year == year)
    continuing = entitled & ~convert
    exposed = (
        ~entitled
        & ~converted_before
        & (start_age >= rates.spec.min_award_age)
        & (year < fra_year)
    )
    uniform = _person_uniforms(
        person_ids,
        continuing | exposed,
        context,
        rng,
        ProjectionModule.DISABILITY,
        DI_ENTITLEMENT_COMPONENT_TAG,
    )

    recovery_probability = np.zeros(len(ordered))
    if continuing.any():
        select_age, duration = _select_inputs(ordered, year, continuing, rates)
        rows = np.flatnonzero(continuing)
        recovery_probability[rows] = rates.recovery_probability(
            start_age[rows],
            sex[rows],
            select_age=None if select_age is None else select_age[rows],
            duration=None if duration is None else duration[rows],
        )
    incidence_probability = np.zeros(len(ordered))
    if exposed.any():
        rows = np.flatnonzero(exposed)
        incidence_probability[rows] = rates.incidence_probability(
            start_age[rows], sex[rows]
        )
    recover = continuing & (uniform < recovery_probability)
    award = exposed & (uniform < incidence_probability)

    award_year = _nullable_years(ordered, "di_award_year")
    award_age = _nullable_years(ordered, "di_award_age")
    recovery_year = _nullable_years(ordered, "di_recovery_year")
    award_year[award] = year
    award_age[award] = year - birth_year[award]
    recovery_year[recover] = year
    conversion_year[convert] = year
    event = np.full(len(ordered), "none", dtype=object)
    event[continuing & ~recover] = "continuing"
    event[recover] = "recovery"
    event[convert] = "conversion"
    event[award] = "award"

    ordered["di_entitled"] = (continuing & ~recover) | award
    ordered["di_award_year"] = award_year
    ordered["di_award_age"] = award_age
    ordered["di_recovery_year"] = recovery_year
    ordered["di_conversion_year"] = conversion_year
    ordered["di_converted"] = convert
    ordered["di_event"] = event
    inverse = np.empty_like(order)
    inverse[order] = np.arange(len(order))
    out = ordered.iloc[inverse].reset_index(drop=True)
    out.index = frame.index
    return out


def _population_probabilities(
    population_model: (
        PopulationMortality
        | Callable[[pd.DataFrame, PeriodContext], np.ndarray]
    ),
    frame: pd.DataFrame,
    context: PeriodContext,
) -> np.ndarray:
    if hasattr(population_model, "probabilities"):
        values = population_model.probabilities(frame)
    elif callable(population_model):
        values = population_model(frame, context)
    else:
        raise TypeError("population_model has no probabilities method")
    values = np.asarray(values, dtype=np.float64)
    if values.shape != (len(frame),):
        raise ValueError("population mortality returned the wrong shape")
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("population mortality must lie in [0, 1]")
    return values


def _population_age_bands(
    population_model: object,
    declared: Sequence[tuple[int, int]] | None,
) -> tuple[tuple[int, int], ...]:
    """The population model's age resolution for the multiplier base."""
    if declared is not None:
        return validate_age_bands(declared)
    bands = getattr(population_model, "bands", None)
    if bands is None:
        raise ValueError(
            "the multiplier death mode divides by NCHS 2000 mortality at the "
            "population model's age resolution; this population model has "
            "no 'bands', so pass population_age_bands (SINGLE_YEAR_AGE_BANDS "
            "for a single-year-of-age model)"
        )
    return validate_age_bands(bands)


def apply_di_aware_mortality(
    frame: pd.DataFrame,
    context: PeriodContext,
    rng: np.random.Generator,
    *,
    population_model: (
        PopulationMortality
        | Callable[[pd.DataFrame, PeriodContext], np.ndarray]
    ),
    rates: DIEntitlementRates,
    death_log: MutableMapping[int, pd.DataFrame] | None = None,
    population_age_bands: Sequence[tuple[int, int]] | None = None,
) -> pd.DataFrame:
    """Step-1 adapter: population mortality with DI-origin death rates.

    Returns the period's survivors sorted by ``person_id``, like
    :func:`populace_dynamics.engine.steps.apply_mortality`.  When
    ``death_log`` is given, ``death_log[year]`` records every decedent.

    In the ``multiplier`` death mode the NCHS 2000 base is taken at the
    population model's age resolution: ``population_age_bands`` when given,
    otherwise the model's ``bands`` attribute (as on
    :class:`populace_dynamics.engine.steps.AgeSexMortalityModel`).  A model
    with neither is refused rather than assumed to be single-age.
    """
    multiplier_bands = (
        _population_age_bands(population_model, population_age_bands)
        if rates.spec.death_mode == "multiplier"
        else None
    )
    _require(
        frame,
        (
            "person_id",
            "sex",
            "birth_year",
            "di_entitled",
            "di_conversion_year",
        ),
        "DI-aware mortality frame",
    )
    year = int(context.year)
    ordered = frame.sort_values("person_id", kind="stable").reset_index(
        drop=True
    )
    if ordered.empty:
        if death_log is not None:
            death_log[year] = pd.DataFrame(
                columns=[
                    "person_id",
                    "sex",
                    "start_age",
                    "di_entitled",
                    "di_origin_converted",
                    "q_population",
                    "q_applied",
                ]
            )
        return ordered
    _check_year(ordered, year - 1, "DI-aware mortality (run before aging)")
    ordered = _normalize_new_rows(ordered)
    birth_year = _int_array(ordered, "birth_year")
    _check_age(ordered, birth_year, year - 1, rates, "DI-aware mortality")
    sex = _sex_index(ordered)
    start_age = year - 1 - birth_year
    entitled = _bool_column(ordered, "di_entitled")
    converted = ~np.asarray(
        pd.isna(_nullable_years(ordered, "di_conversion_year"))
    )
    di_origin = entitled | (
        converted & (rates.spec.post_conversion_mortality == "di_origin")
    )
    person_ids = ordered["person_id"].to_numpy()
    uniform = _person_uniforms(
        person_ids,
        np.ones(len(ordered), dtype=bool),
        context,
        rng,
        ProjectionModule.MORTALITY,
        None,
    )
    q_population = _population_probabilities(
        population_model, ordered, context
    )
    q = q_population.copy()
    if di_origin.any():
        rows = np.flatnonzero(di_origin)
        select_age, duration = _select_inputs(ordered, year, di_origin, rates)
        reference = rates.reference_death_probability(
            start_age[rows],
            sex[rows],
            select_age=None if select_age is None else select_age[rows],
            duration=None if duration is None else duration[rows],
        )
        if multiplier_bands is not None:
            base = rates.population_reference_probability(
                start_age[rows], sex[rows], age_bands=multiplier_bands
            )
            reference = reference * q_population[rows] / base
        q[rows] = np.clip(reference, 0.0, 1.0)
    death = uniform < q
    if death_log is not None:
        death_log[year] = pd.DataFrame(
            {
                "person_id": person_ids[death],
                "sex": ordered["sex"].to_numpy()[death],
                "start_age": start_age[death],
                "di_entitled": entitled[death],
                "di_origin_converted": (converted & ~entitled)[death],
                "q_population": q_population[death],
                "q_applied": q[death],
            }
        )
    return ordered.loc[~death].reset_index(drop=True)


def _weights(
    frame: pd.DataFrame, weight_column: str | None
) -> dict[Any, float]:
    ids = frame["person_id"].tolist()
    if weight_column is None:
        return dict.fromkeys(ids, 1.0)
    values = frame[weight_column].to_numpy(dtype=np.float64)
    return dict(zip(ids, values, strict=True))


def di_stock_flow(
    slices: Iterable[pd.DataFrame],
    *,
    weight_column: str | None = None,
    death_log: Mapping[int, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Reconcile the disabled-worker stock year by year.

    One row per projected year with the stock at the start and end and each
    flow.  Deaths are entitled persons of the prior slice who are absent from
    the current one; with ``death_log`` they must match exactly the logged
    entitled decedents who were in the prior slice.  A logged decedent who
    was not in the prior slice is a scheduled entrant who died in its entry
    year (the loop adds scheduled entrants before mortality); it never
    enters the stock, and it must be absent from the current slice.
    Weighted flows use each person's prior-slice weight (current-slice
    weight for entrants), so the identity also holds weighted.  Raises
    ``ValueError`` if any identity fails.
    """
    frames = list(slices)
    rows: list[dict[str, Any]] = []
    for previous, current in zip(frames[:-1], frames[1:], strict=True):
        if current.empty:
            year = int(previous["year"].iloc[0]) + 1 if len(previous) else 0
        else:
            year = int(current["year"].iloc[0])
        weights = _weights(current, weight_column)
        weights.update(_weights(previous, weight_column))
        prior_entitled = set(
            previous.loc[previous["di_entitled"].astype(bool), "person_id"]
        )
        current_ids = set(current["person_id"])
        previous_ids = set(previous["person_id"])
        deaths = prior_entitled - current_ids
        if death_log is not None:
            logged = death_log.get(year)
            logged_ids = (
                set()
                if logged is None or logged.empty
                else set(logged.loc[logged["di_entitled"], "person_id"])
            )
            if logged_ids & previous_ids != deaths:
                raise ValueError(
                    f"{year}: entitled persons leaving the frame differ "
                    "from the logged entitled decedents"
                )
            if (logged_ids - previous_ids) & current_ids:
                raise ValueError(
                    f"{year}: a logged decedent entrant is still in the frame"
                )
        events = current.set_index("person_id")["di_event"]
        entitled_now = current.set_index("person_id")["di_entitled"].astype(
            bool
        )
        awards = set(events.index[events == "award"])
        recoveries = set(events.index[events == "recovery"])
        conversions = set(events.index[events == "conversion"])
        if (recoveries | conversions) - prior_entitled:
            raise ValueError(f"{year}: a termination has no prior entitlement")
        if awards & prior_entitled:
            raise ValueError(f"{year}: an award went to an entitled person")
        entrants = set(entitled_now.index[entitled_now]) - previous_ids
        entrants -= awards
        stock_end_ids = set(entitled_now.index[entitled_now])
        flows = {
            "stock_start": prior_entitled,
            "awards": awards,
            "entrants_entitled": entrants,
            "deaths": deaths,
            "recoveries": recoveries,
            "conversions": conversions,
            "stock_end": stock_end_ids,
        }
        expected = (
            (prior_entitled - deaths - recoveries - conversions)
            | awards
            | entrants
        )
        if expected != stock_end_ids:
            raise ValueError(
                f"{year}: disabled-worker stock does not reconcile"
            )
        row: dict[str, Any] = {"year": year}
        for name, ids in flows.items():
            row[name] = len(ids)
            row[f"{name}_weighted"] = float(sum(weights[i] for i in ids))
        rows.append(row)
    return pd.DataFrame(rows)


def di_prevalence(
    frame: pd.DataFrame,
    *,
    age_groups: Iterable[tuple[str, int, int | None]],
    weight_column: str | None = None,
    age_column: str = "age",
) -> pd.DataFrame:
    """Entitled disabled workers by age group and sex in one slice.

    ``age_groups`` are ``(label, lower, upper)`` with inclusive bounds and
    ``upper=None`` for an open top group.  Returns counts, weighted counts,
    and each group's share of the sex's entitled stock.
    """
    groups = list(age_groups)
    entitled = frame["di_entitled"].astype(bool).to_numpy()
    age = frame[age_column].to_numpy(dtype=np.int64)
    weight = (
        np.ones(len(frame))
        if weight_column is None
        else frame[weight_column].to_numpy(dtype=np.float64)
    )
    sex = frame["sex"].astype(str).to_numpy()
    rows = []
    for sex_label in SEXES:
        in_sex = entitled & (sex == sex_label)
        total = float(weight[in_sex].sum())
        for label, lower, upper in groups:
            in_group = in_sex & (age >= lower)
            if upper is not None:
                in_group &= age <= upper
            weighted = float(weight[in_group].sum())
            rows.append(
                {
                    "sex": sex_label,
                    "age_group": label,
                    "count": int(in_group.sum()),
                    "weighted": weighted,
                    "share_of_sex_stock": (
                        weighted / total if total > 0 else float("nan")
                    ),
                }
            )
    return pd.DataFrame(rows)
