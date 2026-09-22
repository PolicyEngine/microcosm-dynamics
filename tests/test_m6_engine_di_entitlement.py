"""Invented-data checks for the SSDI entitlement component (Track A A4).

Every rate, population, FRA schedule, and SSA-like table in this module is
INVENTED for testing the accounting, timing, random-stream, and refusal
behavior.  None is an SSA, Census, or DYNASIM value.
"""

from __future__ import annotations

from functools import partial

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.engine.di_entitlement import (
    DI_ENTITLEMENT_COMPONENT_TAG,
    DI_STATE_COLUMNS,
    apply_di_aware_mortality,
    apply_di_entitlement,
    di_prevalence,
    di_stock_flow,
    fra_attainment_year,
    fra_schedule_from_parameters,
    prepare_opening_di_state,
)
from populace_dynamics.engine.di_entitlement_rates import (
    INCIDENCE_BANDS,
    MAX_AGE,
    SINGLE_YEAR_AGE_BANDS,
    DIEntitlementRates,
    DIEntitlementSpec,
    SelectUltimateTable,
    fit_di_entitlement_rates,
    load_di_entitlement_rates,
    pending_decisions,
    validate_age_bands,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    MaritalStepResult,
    PeriodContext,
    PeriodModules,
    ProjectionEngine,
)
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import (
    AgeSexMortalityModel,
    advance_age,
    apply_mortality,
)

SHAPE = (2, MAX_AGE + 1)


def invented_fra(birth_year: int) -> int:
    """INVENTED test schedule: 66 years before 1955, then 67 years."""
    return 792 if birth_year < 1955 else 804


def invented_rates(
    *,
    incidence: float = 0.0,
    recovery: float = 0.0,
    death: float = 0.0,
    population_reference: float = 0.01,
    spec: DIEntitlementSpec | None = None,
    death_select: SelectUltimateTable | None = None,
    recovery_select: SelectUltimateTable | None = None,
) -> DIEntitlementRates:
    """INVENTED flat rates on the award-age range 18-69."""
    incidence_array = np.zeros(SHAPE)
    incidence_array[:, 18:70] = incidence
    return DIEntitlementRates(
        spec=spec or DIEntitlementSpec(),
        incidence=incidence_array,
        recovery_attained=np.full(SHAPE, recovery),
        death_attained=np.full(SHAPE, death),
        population_reference_death=np.full(SHAPE, population_reference),
        recovery_select=recovery_select,
        death_select=death_select,
        recovery_level_factor=1.0,
        death_level_factor=1.0,
    )


def opening(
    rows: list[tuple[int, str, int, bool]], *, year: int = 2010
) -> pd.DataFrame:
    """INVENTED opening slice from (person_id, sex, birth_year, entitled)."""
    frame = pd.DataFrame(
        rows, columns=["person_id", "sex", "birth_year", "di_entitled"]
    )
    frame["year"] = year
    frame["age"] = year - frame["birth_year"]
    return frame


def keyed_context(person_ids, *, year: int, period: int = 1, draw: int = 0):
    return PeriodContext(
        period,
        year,
        draw,
        {},
        rng_registry=ProjectionRNGRegistry(draw, 25),
        person_ordinals={
            person_id: ordinal
            for ordinal, person_id in enumerate(sorted(person_ids))
        },
    )


def aged(frame: pd.DataFrame, year: int) -> pd.DataFrame:
    out = frame.copy()
    out["year"] = year
    out["age"] = year - out["birth_year"]
    return out


def flat_mortality(probability: float) -> AgeSexMortalityModel:
    bands = ((0, 120),)
    return AgeSexMortalityModel(
        bands,
        {("0+", sex): probability for sex in ("female", "male")},
    )


class NoDraw:
    def random(self, *args, **kwargs):
        raise AssertionError("no batch draw was expected")


# --- specification and pending decisions --------------------------------


def test_spec_defaults_are_the_proposed_primaries():
    spec = DIEntitlementSpec()
    assert spec.incidence_basis == "per_population_non_entitled"
    assert spec.death_mode == "multiplier"
    assert spec.fit_year == "2008"
    assert spec.termination_basis == "attained_age"
    assert spec.non_di_mortality == "net_of_di_origin"
    fields = {row["field"] for row in pending_decisions()}
    assert {
        "incidence_basis",
        "death_mode",
        "fit_year",
        "recovery_level",
        "termination_basis",
        "post_conversion_mortality",
        "non_di_mortality",
        "death_level",
    } == fields


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fit_year": "2009"},
        {"incidence_basis": "per_worker"},
        {"death_mode": "life_table"},
        {"death_mode": "multiplier", "death_level": "asr_fitted"},
        {"termination_basis": "duration"},
        {"post_conversion_mortality": "none"},
        {"non_di_mortality": "none"},
        {"min_award_age": 70},
        {"min_award_age": 17},
        {"assumed_birth_month": 13},
    ],
)
def test_spec_refuses_unknown_or_incoherent_choices(kwargs):
    with pytest.raises(ValueError):
        DIEntitlementSpec(**kwargs)


def test_rates_refuse_out_of_range_probabilities():
    bad = np.full(SHAPE, 1.5)
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        DIEntitlementRates(
            spec=DIEntitlementSpec(),
            incidence=bad,
            recovery_attained=np.zeros(SHAPE),
            death_attained=np.zeros(SHAPE),
            population_reference_death=np.full(SHAPE, 0.01),
            recovery_select=None,
            death_select=None,
            recovery_level_factor=1.0,
            death_level_factor=1.0,
        )


def test_select_basis_needs_select_tables():
    with pytest.raises(ValueError, match="select tables"):
        invented_rates(
            spec=DIEntitlementSpec(termination_basis="select_and_ultimate")
        )


# --- FRA attainment -------------------------------------------------------


def test_fra_attainment_year_uses_birth_month_or_the_assumed_month():
    births = np.array([1950, 1960, 1957])

    def schedule(birth_year):  # INVENTED: 66y, 67y, 66y6m
        return {1950: 792, 1960: 804, 1957: 798}[birth_year]

    assumed = fra_attainment_year(births, schedule, assumed_birth_month=7)
    assert assumed.tolist() == [2016, 2027, 2024]
    january = fra_attainment_year(births, schedule, assumed_birth_month=1)
    assert january.tolist() == [2016, 2027, 2023]
    observed = fra_attainment_year(
        births, schedule, birth_month=np.array([12, 12, 6])
    )
    assert observed.tolist() == [2016, 2027, 2023]


def test_fra_schedule_accepts_a_parameters_object():
    class Params:
        def fra_months(self, birth_year):
            return 800

    schedule = fra_schedule_from_parameters(Params())
    assert fra_attainment_year(np.array([1958]), schedule).tolist() == [2025]
    assert fra_attainment_year(np.array([1958]), Params()).tolist() == [2025]


def test_fra_outside_the_statutory_range_is_refused():
    with pytest.raises(ValueError, match="statutory range"):
        fra_attainment_year(np.array([1960]), lambda birth_year: 12 * 50)


# --- opening stock ----------------------------------------------------------


def test_opening_state_requires_an_explicit_entitlement_column():
    frame = opening([(1, "male", 1960, False)]).drop(columns="di_entitled")
    with pytest.raises(ValueError, match="di_entitled"):
        prepare_opening_di_state(
            frame, rates=invented_rates(), fra_schedule=invented_fra
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda f: f.assign(di_entitled=[True, None]), "missing"),
        (lambda f: f.assign(di_entitled=["yes", "no"]), "boolean"),
        (lambda f: f.assign(sex=["male", "other"]), "sex"),
        (lambda f: f.assign(age=[1, 2]), "disagrees"),
        (lambda f: f.assign(year=[2010, 2011]), "one start year"),
        (
            lambda f: f.assign(di_award_year=pd.array([2011, pd.NA])),
            "after the start year",
        ),
        (
            lambda f: f.assign(di_award_year=pd.array([pd.NA, 2005])),
            "not entitled",
        ),
        (
            lambda f: f.assign(di_conversion_year=pd.array([2009, pd.NA])),
            "both entitled and converted",
        ),
        # Person 2 (born 1970) cannot have converted at FRA by 2010.
        (
            lambda f: f.assign(di_conversion_year=pd.array([pd.NA, 2008])),
            "precede the earliest possible FRA",
        ),
    ],
)
def test_opening_state_refuses_inconsistent_inputs(mutate, message):
    frame = opening([(1, "male", 1960, True), (2, "female", 1970, False)])
    with pytest.raises(ValueError, match=message):
        prepare_opening_di_state(
            mutate(frame), rates=invented_rates(), fra_schedule=invented_fra
        )


def test_opening_conversion_year_is_checked_against_fra():
    """INVENTED FRA 66y0m (born 1944): FRA attained in 2010.

    Regression: an opening conversion year before FRA was accepted, leaving a
    person who could not have converted outside incidence for good.  With no
    birth month the earliest possible year is the one a birth on January 1
    gives (a person attains an age the day before the birthday): 2009.
    """

    def schedule(birth_year):
        return 792

    def frame(conversion_year, **columns):
        out = opening([(1, "male", 1944, False)], year=2011)
        out["di_conversion_year"] = pd.array([conversion_year], dtype="Int64")
        for name, value in columns.items():
            out[name] = value
        return out

    rates = invented_rates()
    for accepted in (2009, 2010, 2011):
        prepare_opening_di_state(
            frame(accepted), rates=rates, fra_schedule=schedule
        )
    with pytest.raises(ValueError, match="earliest possible FRA"):
        prepare_opening_di_state(
            frame(2008), rates=rates, fra_schedule=schedule
        )
    # A known birth month moves the earliest year: born in March 1944, FRA
    # is attained in February or March 2010.
    prepare_opening_di_state(
        frame(2010, birth_month=3), rates=rates, fra_schedule=schedule
    )
    with pytest.raises(ValueError, match="earliest possible FRA"):
        prepare_opening_di_state(
            frame(2009, birth_month=3), rates=rates, fra_schedule=schedule
        )


def test_opening_state_refuses_entitled_workers_past_fra():
    frame = opening([(1, "male", 1940, True)])
    with pytest.raises(ValueError, match="attained FRA"):
        prepare_opening_di_state(
            frame, rates=invented_rates(), fra_schedule=invented_fra
        )


def test_opening_state_adds_every_di_column():
    frame = opening([(1, "male", 1960, True), (2, "female", 1970, False)])
    frame["di_award_year"] = pd.array([2004, pd.NA], dtype="Int64")
    out = prepare_opening_di_state(
        frame, rates=invented_rates(), fra_schedule=invented_fra
    )
    assert set(DI_STATE_COLUMNS) <= set(out.columns)
    assert out["di_award_age"].tolist()[0] == 44
    assert pd.isna(out["di_award_age"].tolist()[1])
    assert out["di_event"].tolist() == ["opening", "opening"]
    assert not out["di_converted"].any()


def test_select_basis_refuses_an_opening_stock_without_award_years():
    table = SelectUltimateTable(
        select=np.full((2, 49, 10), 0.01), ultimate=np.full(SHAPE, 0.01)
    )
    rates = invented_rates(
        spec=DIEntitlementSpec(termination_basis="select_and_ultimate"),
        death_select=table,
        recovery_select=table,
    )
    frame = opening([(1, "male", 1960, True)])
    with pytest.raises(ValueError, match="di_award_year"):
        prepare_opening_di_state(frame, rates=rates, fra_schedule=invented_fra)


# --- step 5: conversion, recovery, incidence -----------------------------


def _prepared(rows, rates, *, year=2010, **columns):
    frame = opening(rows, year=year)
    for name, values in columns.items():
        frame[name] = values
    return prepare_opening_di_state(
        frame, rates=rates, fra_schedule=invented_fra
    )


def test_certain_incidence_awards_every_exposed_person_once():
    rates = invented_rates(incidence=1.0)
    start = _prepared(
        [
            (1, "male", 1970, False),  # start age 40: exposed
            (2, "female", 1995, False),  # start age 15: below minimum
            (3, "male", 1945, False),  # FRA already attained: not exposed
        ],
        rates,
    )
    out = apply_di_entitlement(
        aged(start, 2011),
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(0),
        rates=rates,
        fra_schedule=invented_fra,
    )
    assert out["di_entitled"].tolist() == [True, False, False]
    assert out["di_event"].tolist() == ["award", "none", "none"]
    assert out["di_award_year"].tolist()[0] == 2011
    assert out["di_award_age"].tolist()[0] == 41


def test_no_award_in_the_calendar_year_fra_is_attained():
    rates = invented_rates(incidence=1.0)
    # Born 1944 with an invented 66-year FRA: FRA year 2010 + 0 -> 2010.
    start = _prepared(
        [(1, "male", 1944, False), (2, "male", 1945, False)], rates, year=2009
    )
    out = apply_di_entitlement(
        aged(start, 2010),
        PeriodContext(1, 2010, 0, {}),
        np.random.default_rng(0),
        rates=rates,
        fra_schedule=invented_fra,
    )
    assert out["di_entitled"].tolist() == [False, True]


def test_certain_recovery_terminates_every_continuing_worker():
    rates = invented_rates(recovery=1.0, incidence=1.0)
    start = _prepared(
        [(1, "male", 1960, True), (2, "female", 1962, True)], rates
    )
    out = apply_di_entitlement(
        aged(start, 2011),
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(0),
        rates=rates,
        fra_schedule=invented_fra,
    )
    assert not out["di_entitled"].any()
    assert out["di_event"].tolist() == ["recovery", "recovery"]
    assert out["di_recovery_year"].tolist() == [2011, 2011]


def test_recovered_workers_are_exposed_again_the_next_year():
    rates = invented_rates(recovery=1.0, incidence=1.0)
    start = _prepared([(1, "male", 1960, True)], rates)
    first = apply_di_entitlement(
        aged(start, 2011),
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(0),
        rates=rates,
        fra_schedule=invented_fra,
    )
    second = apply_di_entitlement(
        aged(first, 2012),
        PeriodContext(2, 2012, 0, {}),
        np.random.default_rng(1),
        rates=rates,
        fra_schedule=invented_fra,
    )
    assert second["di_event"].tolist() == ["award"]
    assert second["di_award_year"].tolist() == [2012]
    assert second["di_recovery_year"].tolist() == [2011]


def test_conversion_at_fra_consumes_no_draw_and_flags_the_event():
    rates = invented_rates(recovery=1.0, incidence=1.0)
    # Invented 67-year FRA for 1955+: born 1955, July -> FRA year 2022.
    start = _prepared([(10, "female", 1955, True)], rates, year=2021)
    # An empty ordinal map would fail if the converting person were drawn.
    context = keyed_context([], year=2022)
    out = apply_di_entitlement(
        aged(start, 2022),
        context,
        NoDraw(),
        rates=rates,
        fra_schedule=invented_fra,
    )
    assert out["di_event"].tolist() == ["conversion"]
    assert out["di_converted"].tolist() == [True]
    assert out["di_conversion_year"].tolist() == [2022]
    assert not out["di_entitled"].any()
    later = apply_di_entitlement(
        aged(out, 2023),
        keyed_context([], year=2023, period=2),
        NoDraw(),
        rates=rates,
        fra_schedule=invented_fra,
    )
    assert later["di_converted"].tolist() == [False]
    assert later["di_event"].tolist() == ["none"]
    assert later["di_conversion_year"].tolist() == [2022]


def test_an_entitled_worker_past_fra_is_refused():
    rates = invented_rates()
    start = _prepared([(1, "male", 1955, True)], rates, year=2021)
    with pytest.raises(ValueError, match="without conversion"):
        apply_di_entitlement(
            aged(start, 2023),
            PeriodContext(1, 2023, 0, {}),
            np.random.default_rng(0),
            rates=rates,
            fra_schedule=invented_fra,
        )


def test_step_five_refuses_frames_without_di_state_or_before_aging():
    rates = invented_rates()
    bare = opening([(1, "male", 1960, False)])
    with pytest.raises(ValueError, match="prepare_opening_di_state"):
        apply_di_entitlement(
            aged(bare, 2011).drop(columns="di_entitled"),
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(0),
            rates=rates,
            fra_schedule=invented_fra,
        )
    start = _prepared([(1, "male", 1960, False)], rates)
    with pytest.raises(ValueError, match="after aging"):
        apply_di_entitlement(
            start,
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(0),
            rates=rates,
            fra_schedule=invented_fra,
        )
    with pytest.raises(ValueError, match="missing columns"):
        apply_di_entitlement(
            aged(start, 2011).drop(columns="birth_year"),
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(0),
            rates=rates,
            fra_schedule=invented_fra,
        )


def test_synthetic_children_enter_not_entitled_but_others_are_refused():
    rates = invented_rates(incidence=1.0)
    start = _prepared([(1, "male", 1970, False)], rates)
    frame = aged(start, 2011)
    child = pd.DataFrame(
        {
            "person_id": [2],
            "year": [2011],
            "sex": ["female"],
            "birth_year": [2011],
            "age": [0],
            "synthetic_entry": [True],
        }
    )
    combined = pd.concat([frame, child], ignore_index=True)
    out = apply_di_entitlement(
        combined,
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(0),
        rates=rates,
        fra_schedule=invented_fra,
    )
    assert out["di_entitled"].tolist() == [True, False]
    unflagged = combined.assign(synthetic_entry=[False, False])
    with pytest.raises(ValueError, match="without a DI state"):
        apply_di_entitlement(
            unflagged,
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(0),
            rates=rates,
            fra_schedule=invented_fra,
        )


def test_step_five_preserves_row_order_and_index():
    rates = invented_rates(incidence=1.0)
    start = _prepared(
        [(3, "male", 1970, False), (1, "female", 1971, False)], rates
    )
    start.index = [7, 4]
    out = apply_di_entitlement(
        aged(start, 2011),
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(0),
        rates=rates,
        fra_schedule=invented_fra,
    )
    assert out["person_id"].tolist() == [3, 1]
    assert out.index.tolist() == [7, 4]


def test_incidence_draw_is_person_keyed_and_tagged():
    rates = invented_rates(incidence=0.5)
    ids = [5, 6, 7, 8]
    start = _prepared(
        [(pid, "male", 1970, False) for pid in ids], rates, year=2011
    )
    context = keyed_context(ids, year=2012, period=2, draw=3)
    out = apply_di_entitlement(
        aged(start, 2012),
        context,
        NoDraw(),
        rates=rates,
        fra_schedule=invented_fra,
    )
    expected = [
        ProjectionRNGRegistry(3, 25)
        .tagged_child_generator(
            2, ProjectionModule.DISABILITY, DI_ENTITLEMENT_COMPONENT_TAG, i
        )
        .random()
        < 0.5
        for i in range(len(ids))
    ]
    assert out["di_entitled"].tolist() == expected


# --- step 1: DI-aware mortality -------------------------------------------


def _mortality_frame(rates):
    rows = [
        (pid, "male" if pid % 2 else "female", 1950 + pid % 20, pid % 3 == 0)
        for pid in range(1, 61)
    ]
    return _prepared(rows, rates)


def test_non_di_people_die_exactly_as_under_apply_mortality():
    """Under ``population_total`` non-DI people keep the population rates."""
    rates = invented_rates(
        death=1.0,
        spec=DIEntitlementSpec(
            death_mode="explicit", non_di_mortality="population_total"
        ),
    )
    frame = _mortality_frame(rates)
    ids = frame["person_id"].tolist()
    model = flat_mortality(0.3)
    context = keyed_context(ids, year=2011)
    log = {}
    survivors = apply_di_aware_mortality(
        frame,
        context,
        np.random.default_rng(0),
        population_model=model,
        rates=rates,
        death_log=log,
    )
    baseline = apply_mortality(
        frame, context, np.random.default_rng(0), model=model
    )
    non_di_survivors = set(baseline.loc[~baseline["di_entitled"], "person_id"])
    assert set(survivors["person_id"]) == non_di_survivors
    logged = log[2011]
    assert set(logged.loc[logged["di_entitled"], "person_id"]) == set(
        frame.loc[frame["di_entitled"], "person_id"]
    )


def test_multiplier_probability_is_clipped_to_one():
    # q_DI = 0.03 * 0.5 / 0.01 = 1.5, clipped to 1: certain death.
    rates = invented_rates(death=0.03, population_reference=0.01)
    frame = _prepared(
        [(1, "male", 1960, True), (2, "male", 1960, False)], rates
    )
    log = {}
    survivors = apply_di_aware_mortality(
        frame,
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(0),
        population_model=lambda f, context: np.full(len(f), 0.5),
        rates=rates,
        death_log=log,
        population_age_bands=SINGLE_YEAR_AGE_BANDS,
        weight_column=None,
    )
    assert 1 not in set(survivors["person_id"])
    applied = log[2011].set_index("person_id")["q_applied"]
    assert applied[1] == pytest.approx(1.0)


def test_multiplier_probability_is_recorded_for_each_decedent():
    rates = invented_rates(death=0.02, population_reference=0.01)
    frame = _prepared(
        [(pid, "male", 1960, True) for pid in range(1, 401)], rates
    )
    log = {}
    apply_di_aware_mortality(
        frame,
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(4),
        population_model=lambda f, context: np.full(len(f), 0.1),
        rates=rates,
        death_log=log,
        population_age_bands=SINGLE_YEAR_AGE_BANDS,
        weight_column=None,
    )
    logged = log[2011]
    assert len(logged) > 0
    assert np.allclose(logged["q_applied"], 0.2)
    assert np.allclose(logged["q_population"], 0.1)


def test_converted_workers_keep_di_origin_mortality_only_when_chosen():
    frame_rates = invented_rates(
        death=1.0, spec=DIEntitlementSpec(death_mode="explicit")
    )
    frame = _prepared([(1, "male", 1944, False)], frame_rates)
    frame["di_conversion_year"] = pd.array([2009], dtype="Int64")
    for choice, dies in (("di_origin", True), ("population", False)):
        rates = invented_rates(
            death=1.0,
            spec=DIEntitlementSpec(
                death_mode="explicit", post_conversion_mortality=choice
            ),
        )
        survivors = apply_di_aware_mortality(
            frame,
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(0),
            population_model=flat_mortality(0.0),
            rates=rates,
            weight_column=None,
        )
        assert survivors.empty is dies


def test_population_mortality_output_is_validated():
    rates = invented_rates()
    frame = _prepared([(1, "male", 1960, False)], rates)
    for bad, message in (
        (np.array([1.2]), r"\[0, 1\]"),
        (np.array([0.1, 0.2]), "wrong shape"),
    ):
        with pytest.raises(ValueError, match=message):
            apply_di_aware_mortality(
                frame,
                PeriodContext(1, 2011, 0, {}),
                np.random.default_rng(0),
                population_model=lambda f, context, bad=bad: bad,
                rates=rates,
                population_age_bands=SINGLE_YEAR_AGE_BANDS,
                weight_column=None,
            )
    with pytest.raises(ValueError, match="before aging"):
        apply_di_aware_mortality(
            aged(frame, 2011),
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(0),
            population_model=flat_mortality(0.0),
            rates=rates,
            weight_column=None,
        )


class ZeroDraw:
    """Batch generator whose uniforms are all zero: every q > 0 dies."""

    def random(self, size):
        return np.zeros(size)


#: INVENTED banding shaped like the PSID-fitted engine mortality bands.
PSID_LIKE_BANDS = (
    (0, 24),
    (25, 34),
    (35, 44),
    (45, 54),
    (55, 64),
    (65, 74),
    (75, 84),
    (85, 120),
)


def _rising_reference() -> np.ndarray:
    """INVENTED population reference rising 8 percent per year of age."""
    q = np.minimum(0.0005 * 1.08 ** np.arange(MAX_AGE + 1), 0.6)
    return np.vstack([q, np.minimum(q * 1.2, 0.7)])


def _stationary_band_mean(q: np.ndarray, lower: int, upper: int) -> float:
    """Independent l_x-weighted mean of ``q`` over one inclusive band."""
    survivors = 1.0
    numerator = denominator = 0.0
    for age in range(lower, upper + 1):
        numerator += survivors * float(q[age])
        denominator += survivors
        survivors *= 1.0 - float(q[age])
    return numerator / denominator


def _banded_rates(spec=None) -> DIEntitlementRates:
    """INVENTED DI death profile over an INVENTED rising population table."""
    death = np.tile(0.02 + 0.001 * np.arange(MAX_AGE + 1), (2, 1))
    return DIEntitlementRates(
        spec=spec or DIEntitlementSpec(),
        incidence=np.zeros(SHAPE),
        recovery_attained=np.zeros(SHAPE),
        death_attained=death,
        population_reference_death=_rising_reference(),
        recovery_select=None,
        death_select=None,
        recovery_level_factor=1.0,
        death_level_factor=1.0,
    )


def test_population_reference_base_follows_the_population_bands():
    rates = _banded_rates()
    reference = rates.population_reference_death
    ages = np.arange(MAX_AGE + 1)
    for sex in (0, 1):
        sexes = np.full(len(ages), sex)
        single = rates.population_reference_probability(
            ages, sexes, age_bands=SINGLE_YEAR_AGE_BANDS
        )
        assert np.array_equal(single, reference[sex])
        banded = rates.population_reference_probability(
            ages, sexes, age_bands=PSID_LIKE_BANDS
        )
        for lower, upper in PSID_LIKE_BANDS:
            expected = _stationary_band_mean(reference[sex], lower, upper)
            assert banded[lower : upper + 1] == pytest.approx(
                np.full(upper - lower + 1, expected), rel=1e-12
            )


@pytest.mark.parametrize("level", [1.0, 1.5])
def test_multiplier_keeps_the_di_age_profile_under_banded_mortality(level):
    """Regression: a banded population model must not reshape DI deaths.

    The population model is the INVENTED reference averaged over 10-year
    bands, times ``level``.  Dividing by the single-age reference (the
    earlier behavior) inflated DI mortality at the bottom of each band and
    deflated it at the top; the band-consistent base leaves the DI profile
    intact and carries only the level.
    """
    rates = _banded_rates()
    reference = rates.population_reference_death
    probability = {}
    for lower, upper in PSID_LIKE_BANDS:
        label = AgeSexMortalityModel.band_label(lower, upper)
        for index, sex in enumerate(("female", "male")):
            probability[(label, sex)] = level * _stationary_band_mean(
                reference[index], lower, upper
            )
    model = AgeSexMortalityModel(PSID_LIKE_BANDS, probability)
    rows = [
        (pid, "male" if pid % 2 else "female", 2010 - (45 + pid // 2), True)
        for pid in range(40)
    ]
    frame = _prepared(rows, rates)
    log = {}
    survivors = apply_di_aware_mortality(
        frame,
        PeriodContext(1, 2011, 0, {}),
        ZeroDraw(),
        population_model=model,
        rates=rates,
        death_log=log,
        weight_column=None,
    )
    assert survivors.empty
    logged = log[2011]
    assert sorted(logged["start_age"].unique()) == list(range(45, 65))
    sex_index = np.where(logged["sex"] == "male", 1, 0)
    expected = level * rates.death_attained[sex_index, logged["start_age"]]
    assert logged["q_applied"].to_numpy() == pytest.approx(expected, rel=1e-12)


def test_multiplier_mode_needs_the_population_age_resolution():
    rates = invented_rates(death=0.02)
    frame = _prepared([(1, "male", 1960, True)], rates)

    def unbanded(f, context):
        return np.full(len(f), 0.01)

    with pytest.raises(ValueError, match="age resolution"):
        apply_di_aware_mortality(
            frame,
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(0),
            population_model=unbanded,
            rates=rates,
        )
    for bad in (((1, 120),), ((0, 10), (12, 120)), ((0, 100),)):
        with pytest.raises(ValueError, match="age bands"):
            apply_di_aware_mortality(
                frame,
                PeriodContext(1, 2011, 0, {}),
                np.random.default_rng(0),
                population_model=unbanded,
                rates=rates,
                population_age_bands=bad,
            )
    assert validate_age_bands(((0, 60), (61, 150))) == ((0, 60), (61, 120))
    # Explicit death rates never divide by the reference, so without the
    # net-of-DI cells an unbanded model is accepted ...
    explicit = invented_rates(
        death=0.02,
        spec=DIEntitlementSpec(
            death_mode="explicit", non_di_mortality="population_total"
        ),
    )
    apply_di_aware_mortality(
        _prepared([(1, "male", 1960, True)], explicit),
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(0),
        population_model=unbanded,
        rates=explicit,
    )
    # ... but net_of_di_origin needs the bands for its cells.
    explicit_net = invented_rates(
        death=0.02, spec=DIEntitlementSpec(death_mode="explicit")
    )
    with pytest.raises(ValueError, match="age resolution"):
        apply_di_aware_mortality(
            _prepared([(1, "male", 1960, True)], explicit_net),
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(0),
            population_model=unbanded,
            rates=explicit_net,
            weight_column=None,
        )


# --- non-DI mortality net of DI-origin deaths ----------------------------

#: INVENTED two-band population model: 0.01 below 50, 0.04 from 50.
TWO_BANDS = ((0, 49), (50, 120))


def _two_band_model() -> AgeSexMortalityModel:
    return AgeSexMortalityModel(
        TWO_BANDS,
        {
            (AgeSexMortalityModel.band_label(lower, upper), sex): value
            for (lower, upper), value in zip(
                TWO_BANDS, (0.01, 0.04), strict=True
            )
            for sex in ("female", "male")
        },
    )


def _net_frame(rates):
    """INVENTED weighted frame: three band-sex cells with DI-origin rows."""
    rows = [
        (1, "male", 1950, True),  # start age 60, band 50+
        (2, "male", 1952, False),
        (3, "male", 1955, False),
        (4, "male", 1980, True),  # start age 30, band 0-49
        (5, "male", 1981, False),
        (6, "female", 1954, True),
        (7, "female", 1953, False),
        (8, "female", 1985, False),  # female 0-49: no DI-origin row
    ]
    frame = _prepared(rows, rates)
    frame["weight"] = [2.0, 10.0, 6.0, 1.0, 19.0, 3.0, 5.0, 4.0]
    return frame


def _all_deaths(rates, frame, **kwargs):
    log, cells = {}, {}
    apply_di_aware_mortality(
        frame,
        PeriodContext(1, 2011, 0, {}),
        ZeroDraw(),
        population_model=_two_band_model(),
        rates=rates,
        death_log=log,
        cell_log=cells,
        **kwargs,
    )
    return log[2011].set_index("person_id")["q_applied"], cells.get(2011)


def test_net_of_di_origin_keeps_each_cells_expected_deaths():
    """Regression: DI-origin deaths used to be added to all-person mortality.

    INVENTED explicit DI death probability 0.10.  Male 50+ cell: the
    population model expects 0.04 * (2 + 10 + 6) = 0.72 deaths; the DI row
    takes 0.10 * 2 = 0.20, so the other rows are scaled by
    (0.72 - 0.20) / (0.04 * 16) = 0.8125.
    """
    rates = invented_rates(
        death=0.10, spec=DIEntitlementSpec(death_mode="explicit")
    )
    frame = _net_frame(rates)
    q, cells = _all_deaths(rates, frame, weight_column="weight")
    assert q[1] == pytest.approx(0.10)
    assert q[2] == pytest.approx(0.04 * 0.8125)
    assert q[3] == pytest.approx(0.04 * 0.8125)
    # Male 0-49: (0.01 * 20 - 0.10 * 1) / (0.01 * 19).
    assert q[5] == pytest.approx(0.01 * (0.20 - 0.10) / 0.19)
    # Female 50+: (0.04 * 8 - 0.10 * 3) / (0.04 * 5).
    assert q[7] == pytest.approx(0.04 * (0.32 - 0.30) / 0.20)
    # A cell with no DI-origin person is untouched.
    assert q[8] == pytest.approx(0.01)
    cells = cells.set_index(["sex", "band_lower"])
    assert len(cells) == 4
    assert not cells["infeasible"].any()
    assert cells["expected_deaths_applied"].to_numpy() == pytest.approx(
        cells["expected_deaths_population_model"].to_numpy()
    )
    assert cells.loc[("male", 50), "non_di_factor"] == pytest.approx(0.8125)
    assert cells.loc[("male", 50), "di_origin_weight"] == pytest.approx(2.0)
    assert cells.loc[("female", 0), "non_di_factor"] == 1.0

    # population_total: non-DI rows keep 0.04, so the cell's expected deaths
    # exceed the population model's by the DI excess, 2 * (0.10 - 0.04).
    total = invented_rates(
        death=0.10,
        spec=DIEntitlementSpec(
            death_mode="explicit", non_di_mortality="population_total"
        ),
    )
    q_total, no_cells = _all_deaths(total, _net_frame(total))
    assert no_cells is None
    assert q_total[2] == pytest.approx(0.04)
    weight = frame.set_index("person_id")["weight"]
    male_50 = [1, 2, 3]
    excess = float((weight[male_50] * q_total[male_50]).sum()) - 0.72
    assert excess == pytest.approx(2 * (0.10 - 0.04))


def test_net_of_di_origin_uses_the_declared_weights():
    rates = invented_rates(
        death=0.10, spec=DIEntitlementSpec(death_mode="explicit")
    )
    frame = _net_frame(rates)
    with pytest.raises(ValueError, match="needs weight_column"):
        _all_deaths(rates, frame)
    q, _ = _all_deaths(rates, frame, weight_column=None)
    # Unweighted male 50+: (0.04 * 3 - 0.10) / (0.04 * 2).
    assert q[2] == pytest.approx(0.04 * (0.12 - 0.10) / 0.08)
    with pytest.raises(ValueError, match="finite"):
        _all_deaths(rates, frame.assign(weight=np.nan), weight_column="weight")
    with pytest.raises(ValueError, match="missing columns"):
        _all_deaths(rates, frame, weight_column="no_such_column")


def test_net_of_di_origin_flags_an_infeasible_cell():
    """INVENTED: DI-origin expected deaths alone exceed the cell's total."""
    rates = invented_rates(
        death=0.50, spec=DIEntitlementSpec(death_mode="explicit")
    )
    frame = _net_frame(rates)
    q, cells = _all_deaths(rates, frame, weight_column="weight")
    # Male 0-49: 0.50 * 1 > 0.01 * 20, so the non-DI row gets zero.
    assert q.get(5, 0.0) == 0.0
    cells = cells.set_index(["sex", "band_lower"])
    assert bool(cells.loc[("male", 0), "infeasible"])
    assert cells.loc[("male", 0), "non_di_factor"] == 0.0
    assert cells.loc[("male", 0), "expected_deaths_applied"] == (
        pytest.approx(0.50)
    )


def test_net_of_di_origin_multiplier_keeps_a_banded_models_total():
    """INVENTED rising reference and 10-year bands, default multiplier mode.

    Every band-sex cell's expected deaths equal the banded population
    model's, whatever the DI-origin share of the cell.
    """
    rates = _banded_rates()
    reference = rates.population_reference_death
    probability = {}
    for lower, upper in PSID_LIKE_BANDS:
        label = AgeSexMortalityModel.band_label(lower, upper)
        for index, sex in enumerate(("female", "male")):
            probability[(label, sex)] = 1.3 * _stationary_band_mean(
                reference[index], lower, upper
            )
    model = AgeSexMortalityModel(PSID_LIKE_BANDS, probability)
    rng = np.random.default_rng(8)
    n = 600
    # Start ages 40-63 (three bands); one in twelve of each sex is DI-origin.
    rows = [
        (
            pid,
            "male" if pid % 2 else "female",
            int(2010 - rng.integers(41, 65)),
            pid % 24 in (0, 13),
        )
        for pid in range(1, n + 1)
    ]
    frame = _prepared(rows, rates)
    frame["weight"] = rng.uniform(0.2, 3.0, n)
    cells = {}
    apply_di_aware_mortality(
        frame,
        PeriodContext(1, 2011, 0, {}),
        np.random.default_rng(0),
        population_model=model,
        rates=rates,
        weight_column="weight",
        cell_log=cells,
    )
    logged = cells[2011]
    assert (logged["di_origin_persons"] > 0).all()
    assert not logged["infeasible"].any()
    assert logged["expected_deaths_applied"].to_numpy() == pytest.approx(
        logged["expected_deaths_population_model"].to_numpy(), rel=1e-12
    )
    assert (logged["non_di_factor"] < 1).all()


# --- select-and-ultimate --------------------------------------------------


def test_select_table_lookup_uses_select_then_ultimate():
    select = np.zeros((2, 49, 10))
    select[1, 44 - 16, 0] = 0.25
    select[1, 44 - 16, 9] = 0.5
    ultimate = np.zeros(SHAPE)
    ultimate[1, 60] = 0.75
    table = SelectUltimateTable(select=select, ultimate=ultimate)
    values = table.lookup(
        np.array([1, 1, 1]),
        np.array([44, 44, 44]),
        np.array([0, 9, 16]),
        np.array([44, 53, 60]),
    )
    assert values.tolist() == [0.25, 0.5, 0.75]
    with pytest.raises(ValueError):
        table.lookup(np.array([1]), np.array([44]), np.array([-1]), [44])


def test_select_basis_uses_award_age_and_duration_in_step_five():
    select = np.zeros((2, 49, 10))
    select[0, 41 - 16, 2] = 1.0  # certain recovery at select 41, duration 2
    table = SelectUltimateTable(select=select, ultimate=np.zeros(SHAPE))
    rates = invented_rates(
        spec=DIEntitlementSpec(termination_basis="select_and_ultimate"),
        recovery_select=table,
        death_select=table,
    )
    frame = opening([(1, "female", 1968, True), (2, "female", 1968, True)])
    frame["di_award_year"] = pd.array([2009, 2008], dtype="Int64")
    start = prepare_opening_di_state(
        frame, rates=rates, fra_schedule=invented_fra
    )
    out = apply_di_entitlement(
        aged(start, 2012),
        PeriodContext(2, 2012, 0, {}),
        np.random.default_rng(0),
        rates=rates,
        fra_schedule=invented_fra,
    )
    # Person 1: select 41, duration 2012 - 1 - 2009 = 2 -> recovers.
    # Person 2: select 40, duration 3 -> zero rate.
    assert out["di_event"].tolist() == ["recovery", "continuing"]


# --- whole-loop accounting and determinism --------------------------------


def _passthrough(frame, context, rng):
    return frame


def _marital(frame, context, rng):
    return MaritalStepResult(sim_years=pd.DataFrame(), births=pd.DataFrame())


def _reader(frame, context, marital, rng):
    return frame


def _modules(rates, log, mortality=0.02, weight_column=None):
    return PeriodModules(
        mortality=partial(
            apply_di_aware_mortality,
            population_model=flat_mortality(mortality),
            rates=rates,
            death_log=log,
            weight_column=weight_column,
        ),
        aging=advance_age,
        marital_core=_marital,
        fertility=_reader,
        disability=partial(
            apply_di_entitlement, rates=rates, fra_schedule=invented_fra
        ),
        earnings=_passthrough,
        claiming=_passthrough,
        household_composition=_reader,
        initialize=partial(
            prepare_opening_di_state, rates=rates, fra_schedule=invented_fra
        ),
    )


def _cohort(n=400, seed=11):
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "person_id": np.arange(1, n + 1),
            "year": 2010,
            "sex": rng.choice(["female", "male"], n),
            "birth_year": rng.integers(1948, 1992, n),
            "weight": rng.uniform(0.5, 2.0, n),
        }
    )
    frame["age"] = 2010 - frame["birth_year"]
    frame["di_entitled"] = (rng.random(n) < 0.1) & (frame["age"] < 60)
    return frame


def _loop_rates(spec=None):
    return invented_rates(
        incidence=0.02,
        recovery=0.05,
        death=0.06,
        population_reference=0.02,
        spec=spec,
    )


def test_stock_flow_identity_holds_through_the_projection_loop():
    rates = _loop_rates()
    log = {}
    result = ProjectionEngine(
        _modules(rates, log, weight_column="weight")
    ).project(_cohort(), end_year=2030, draw_index=0)
    flows = di_stock_flow(result.slices, weight_column="weight", death_log=log)
    assert flows["year"].tolist() == list(range(2011, 2031))
    for suffix in ("", "_weighted"):
        reconciled = (
            flows[f"stock_start{suffix}"]
            + flows[f"awards{suffix}"]
            + flows[f"entrants_entitled{suffix}"]
            - flows[f"deaths{suffix}"]
            - flows[f"recoveries{suffix}"]
            - flows[f"conversions{suffix}"]
        )
        assert np.allclose(reconciled, flows[f"stock_end{suffix}"])
    assert flows["awards"].sum() > 0
    assert flows["deaths"].sum() > 0
    assert flows["recoveries"].sum() > 0
    assert flows["conversions"].sum() > 0
    final = result.slices[-1]
    converted = final.loc[final["di_conversion_year"].notna()]
    fra_year = fra_attainment_year(
        converted["birth_year"].to_numpy(), invented_fra
    )
    assert (converted["di_conversion_year"].to_numpy() == fra_year).all()


def test_stock_flow_refuses_an_unreconciled_history():
    rates = _loop_rates()
    log = {}
    result = ProjectionEngine(_modules(rates, log)).project(
        _cohort(), end_year=2013, draw_index=0
    )
    slices = [frame.copy() for frame in result.slices]
    tampered = slices[2]
    target = tampered.index[~tampered["di_entitled"]][0]
    tampered.loc[target, "di_entitled"] = True
    with pytest.raises(ValueError, match="does not reconcile"):
        di_stock_flow(slices)
    with pytest.raises(ValueError, match="logged"):
        di_stock_flow(result.slices, death_log={2011: log[2012]})


def test_stock_flow_accepts_an_entitled_entrant_who_dies_on_entry():
    """INVENTED: a scheduled entitled entrant dies in its entry year.

    The loop adds scheduled entrants before mortality, so such a person is
    logged as an entitled decedent without ever being in a slice.
    Regression: the death-log cross-check used to refuse this history.
    """
    rates = invented_rates(
        death=1.0, spec=DIEntitlementSpec(death_mode="explicit")
    )
    entrant = prepare_opening_di_state(
        opening([(50, "male", 1975, True)], year=2011),
        rates=rates,
        fra_schedule=invented_fra,
    )
    log = {}
    result = ProjectionEngine(_modules(rates, log, mortality=0.0)).project(
        opening([(1, "male", 1970, False), (2, "female", 1972, True)]),
        end_year=2013,
        draw_index=0,
        metadata={SCHEDULED_ENTRIES_KEY: {2012: entrant}},
    )
    assert set(log[2011].loc[log[2011]["di_entitled"], "person_id"]) == {2}
    assert set(log[2012].loc[log[2012]["di_entitled"], "person_id"]) == {50}
    flows = di_stock_flow(result.slices, death_log=log).set_index("year")
    assert flows.loc[2011, "deaths"] == 1
    assert flows.loc[
        2012, ["stock_start", "deaths", "stock_end"]
    ].tolist() == [
        0,
        0,
        0,
    ]
    # A logged decedent entrant who is still in the frame is refused.
    revived = entrant.assign(year=2012, age=37, di_entitled=False)
    revived["di_event"] = "none"
    current = pd.concat([result.slices[2], revived], ignore_index=True)
    with pytest.raises(ValueError, match="decedent entrant"):
        di_stock_flow([result.slices[1], current], death_log={2012: log[2012]})


def test_stock_flow_accepts_entrants_who_recover_or_convert_on_entry():
    """INVENTED: a scheduled entitled entrant leaves the stock on entry.

    Regression: an entrant who recovered or converted in its entry year was
    refused as "a termination has no prior entitlement".  It counts as an
    entrant and as the termination, so the stock is unchanged.
    """
    for event, rates, birth_year in (
        (
            "recovery",
            invented_rates(
                recovery=1.0, spec=DIEntitlementSpec(death_mode="explicit")
            ),
            1975,
        ),
        (
            # INVENTED FRA 66 for 1946: attained in 2012, the entry year.
            "conversion",
            invented_rates(spec=DIEntitlementSpec(death_mode="explicit")),
            1946,
        ),
    ):
        entrant = prepare_opening_di_state(
            opening([(50, "male", birth_year, True)], year=2011),
            rates=rates,
            fra_schedule=invented_fra,
        )
        entrant["weight"] = 3.0
        log = {}
        cohort = opening([(1, "male", 1970, False), (2, "female", 1972, True)])
        cohort["weight"] = 1.0
        result = ProjectionEngine(
            _modules(rates, log, mortality=0.0, weight_column="weight")
        ).project(
            cohort,
            end_year=2013,
            draw_index=0,
            metadata={SCHEDULED_ENTRIES_KEY: {2012: entrant}},
        )
        entered = result.slices[2].set_index("person_id").loc[50]
        assert entered["di_event"] == event
        flows = di_stock_flow(
            result.slices, weight_column="weight", death_log=log
        ).set_index("year")
        row = flows.loc[2012]
        assert row["entrants_entitled"] == 1
        assert row["entrants_entitled_weighted"] == 3.0
        terminated = "recoveries" if event == "recovery" else "conversions"
        assert row[terminated] == 1
        assert row["stock_end"] == row["stock_start"] + row["awards"]


def test_projection_is_deterministic_by_draw_and_person_keyed():
    # population_total: a non-DI person's probability does not depend on the
    # cell's DI share, so adding one person changes nobody else's path.
    rates = _loop_rates(DIEntitlementSpec(non_di_mortality="population_total"))
    cohort = _cohort()
    first = ProjectionEngine(_modules(rates, {})).project(
        cohort, end_year=2020, draw_index=2
    )
    second = ProjectionEngine(_modules(rates, {})).project(
        cohort, end_year=2020, draw_index=2
    )
    other = ProjectionEngine(_modules(rates, {})).project(
        cohort, end_year=2020, draw_index=3
    )
    for left, right in zip(first.slices, second.slices, strict=True):
        pd.testing.assert_frame_equal(left, right)
    assert not all(
        left.equals(right)
        for left, right in zip(first.slices, other.slices, strict=True)
    )
    extra = pd.concat(
        [
            cohort,
            pd.DataFrame(
                {
                    "person_id": [10_000],
                    "year": [2010],
                    "sex": ["male"],
                    "birth_year": [1975],
                    "weight": [1.0],
                    "age": [35],
                    "di_entitled": [True],
                }
            ),
        ],
        ignore_index=True,
    )
    widened = ProjectionEngine(_modules(rates, {})).project(
        extra, end_year=2020, draw_index=2
    )
    for left, right in zip(first.slices, widened.slices, strict=True):
        kept = right[right["person_id"] != 10_000].reset_index(drop=True)
        pd.testing.assert_frame_equal(
            left.reset_index(drop=True), kept, check_dtype=False
        )


def test_batch_path_is_deterministic_for_a_seeded_generator():
    rates = invented_rates(incidence=0.3, recovery=0.3)
    start = _prepared(
        [(pid, "male", 1970, pid % 2 == 0) for pid in range(1, 51)], rates
    )
    runs = [
        apply_di_entitlement(
            aged(start, 2011),
            PeriodContext(1, 2011, 0, {}),
            np.random.default_rng(99),
            rates=rates,
            fra_schedule=invented_fra,
        )
        for _ in range(2)
    ]
    pd.testing.assert_frame_equal(runs[0], runs[1])


def test_prevalence_shares_sum_to_one_per_sex():
    rates = _loop_rates()
    result = ProjectionEngine(_modules(rates, {})).project(
        _cohort(), end_year=2015, draw_index=0
    )
    groups = [("under 50", 0, 49), ("50-59", 50, 59), ("60+", 60, None)]
    table = di_prevalence(
        result.slices[-1], age_groups=groups, weight_column="weight"
    )
    for _, rows in table.groupby("sex"):
        assert rows["share_of_sex_stock"].sum() == pytest.approx(1.0)


# --- fitting arithmetic on invented inputs ---------------------------------

_GROUPS = [label for _, _, label in INCIDENCE_BANDS]


def invented_inputs(**overrides):
    """INVENTED inputs with the extracted-table schema."""
    select = {
        "select_ages": list(range(16, 65)),
        "durations": list(range(10)),
        "select": [[0.01] * 10 for _ in range(49)],
        "ultimate": [0.02] * 49,
        "ultimate_attained_ages": list(range(26, 75)),
    }
    inputs = {
        "schema_version": "di_entitlement_inputs.v1",
        "information_boundary_year": 2008,
        "sources": {"invented": {"data_year": "2008"}},
        "asr": {
            "2008": {
                "awards_workers": {
                    "age_groups": _GROUPS,
                    "male": [10.0 * (i + 1) for i in range(10)],
                    "female": [5.0 * (i + 1) for i in range(10)],
                },
                "stock_workers_december": {
                    "age_groups": _GROUPS,
                    "male": [100.0] * 10,
                    "female": [50.0] * 10,
                },
                "stock_distribution": {
                    "men": {
                        "2007": {"number_thousands": 1.0},
                        "2008": {"number_thousands": 1.0},
                    },
                    "women": {
                        "2007": {"number_thousands": 3.0},
                        "2008": {"number_thousands": 1.0},
                    },
                },
                "terminations_workers_by_reason": {
                    "does_not_meet_medical_standards": 60.0,
                    "death": 90.0,
                },
            }
        },
        "census_resident_population_july1": {
            "2008": {
                "ages": list(range(101)),
                "male": [1000] * 101,
                "female": [2000] * 101,
            }
        },
        "as118": {
            "death": {
                "aggregate_by_attained_age": {
                    "ages": list(range(16, 75)),
                    "male": [0.04] * 59,
                    "female": [0.02] * 59,
                },
                "ultimate_75_plus": {
                    "ages": list(range(75, 111)),
                    "male": [0.1] * 36,
                    "female": [0.08] * 36,
                },
                "select_ultimate": {"male": select, "female": select},
            },
            "recovery": {
                "aggregate_by_attained_age": {
                    "ages": list(range(16, 65)),
                    "male": [0.02] * 49,
                    "female": [0.01] * 49,
                },
                "select_ultimate": {"male": select, "female": select},
            },
        },
    }
    inputs.update(overrides)
    return inputs


def invented_life_table():
    """INVENTED population life table with the NCHS schema."""
    return {
        "vintage_year": 2000,
        "tables": {
            sex: [{"age": age, "qx": 0.01} for age in range(100)]
            + [{"age": 100, "qx": 1.0}]
            for sex in ("female", "male")
        },
    }


def test_fit_arithmetic_on_invented_inputs():
    rates = fit_di_entitlement_rates(invented_inputs(), invented_life_table())
    # Band 55-59, male: awards 80 over 5 ages x 1000 people minus 100.
    assert rates.incidence[1, 57] == pytest.approx(80 / (5000 - 100))
    # Under 25 uses ages 18-24; 65-FRA uses age 65 only.
    assert rates.incidence[0, 20] == pytest.approx(5 / (7 * 2000 - 50))
    assert rates.incidence[0, 66] == pytest.approx(50 / (2000 - 50))
    assert rates.incidence[:, :18].sum() == 0
    # Exposure scale: men (1 + 1) / 2 = 1; women (3 + 1) / 2 = 2.
    expected_recoveries = 1000 * 0.02 + 500 * 2 * 0.01
    factor = 60 / expected_recoveries
    assert rates.recovery_level_factor == pytest.approx(factor)
    assert rates.recovery_attained[1, 40] == pytest.approx(0.02 * factor)
    expected_deaths = 1000 * 0.04 + 1000 * 0.02
    diagnostic = rates.diagnostics["death_level"]
    assert diagnostic["fitted_factor"] == pytest.approx(90 / expected_deaths)
    # Multiplier mode keeps the published level.
    assert rates.death_level_factor == 1.0
    assert rates.death_attained[1, 40] == pytest.approx(0.04)
    assert rates.death_attained[1, 80] == pytest.approx(0.1)
    # The open 100+ row is dropped from the multiplier base.
    assert rates.population_reference_death[1, 100] == pytest.approx(0.01)
    explicit = fit_di_entitlement_rates(
        invented_inputs(),
        invented_life_table(),
        DIEntitlementSpec(death_mode="explicit", death_level="asr_fitted"),
    )
    assert explicit.death_attained[1, 40] == pytest.approx(
        0.04 * 90 / expected_deaths
    )


@pytest.mark.parametrize(
    ("inputs", "spec", "message"),
    [
        (
            invented_inputs(schema_version="other"),
            None,
            "schema",
        ),
        (
            invented_inputs(information_boundary_year=2010),
            None,
            "boundary",
        ),
        (
            invented_inputs(sources={"late": {"data_year": "2009"}}),
            None,
            "after 2008",
        ),
        (
            invented_inputs(),
            DIEntitlementSpec(incidence_basis="per_insured"),
            "per-insured",
        ),
        (
            invented_inputs(),
            DIEntitlementSpec(fit_year="2007"),
            "missing from the inputs",
        ),
    ],
)
def test_fit_refuses_bad_or_missing_inputs(inputs, spec, message):
    with pytest.raises(ValueError, match=message):
        fit_di_entitlement_rates(inputs, invented_life_table(), spec)


def test_fit_refuses_a_non_2000_multiplier_base():
    table = invented_life_table()
    table["vintage_year"] = 2010
    with pytest.raises(ValueError, match="NCHS 2000"):
        fit_di_entitlement_rates(invented_inputs(), table)


def test_loader_refuses_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="refuses to run"):
        load_di_entitlement_rates(inputs_path=tmp_path / "absent.json")
