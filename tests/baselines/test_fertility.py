"""The opt-in ASFR fertility step (not gated, report-only).

Every person, age, weight and fertility rate below is INVENTED for
testing; no baseline file, PSID file or outcome is read.

Stated invariants (Hypothesis property tests unless noted):

1. The expected number of births is the sum of the rates over the
   exposed women (``sex == "female"`` at an age the schedule keys).
2. Zero rates give zero births; unit rates give every exposed woman one
   birth; men and women at unkeyed ages never give birth.
3. Over many draws the mean number of births equals the expected number
   within Monte Carlo tolerance (five standard errors).
4. A woman's draw depends only on the draw, the period and her own RNG
   ordinal, not on who else is in the frame; the same inputs give the
   same births.
5. Births materialize through ``engine.steps.materialize_maternal_births``
   as age-0 child rows with the mother's weight and household and fresh
   identifiers (example tests, including a multi-year projection).
6. The module does not import or call the gated candidate-16 fertility
   law (a static check).
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.baselines import fertility
from populace_dynamics.baselines.fertility import (
    ASFR_FERTILITY_LABEL,
    ASFR_STREAM_TAG,
    AsfrFertilityStep,
    draw_asfr_births,
    expected_births,
)
from populace_dynamics.engine.loop import (
    MaritalStepResult,
    PeriodContext,
    PeriodModules,
    ProjectionEngine,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import advance_age

FERTILE = range(14, 50)


# --------------------------------------------------------------------------
# INVENTED frames, rates and contexts
# --------------------------------------------------------------------------
def invented_frame(ages, sexes, *, year=2030, first_id=1) -> pd.DataFrame:
    """INVENTED persons: one household per person, weight 100 + id."""
    ids = np.arange(first_id, first_id + len(ages), dtype=np.int64)
    return pd.DataFrame(
        {
            "person_id": ids,
            "year": year,
            "age": np.asarray(ages, dtype=np.int64),
            "sex": list(sexes),
            "weight": 100.0 + ids,
            "household_id": 1_000 + ids,
        }
    )


def invented_context(frame, *, year=2030, period=1, draw=0, ordinals=None):
    """A period context with the loop's registry and roster ordinals."""
    ids = sorted(frame["person_id"].tolist())
    return PeriodContext(
        period_index=period,
        year=year,
        draw_index=draw,
        metadata={
            "synthetic_id_allocator": SyntheticPersonIdAllocator(
                int(max(ids, default=0)) + 1
            )
        },
        rng_registry=ProjectionRNGRegistry(draw, max(period, 1)),
        person_ordinals=(
            {pid: index for index, pid in enumerate(ids)}
            if ordinals is None
            else ordinals
        ),
    )


def empty_marital(frame) -> MaritalStepResult:
    return MaritalStepResult(
        sim_years=frame[["person_id"]].copy(),
        births=pd.DataFrame(columns=["parent_person_id", "birth_year"]),
    )


rates_strategy = st.dictionaries(
    st.sampled_from(list(FERTILE)),
    st.floats(0.0, 0.6, allow_nan=False),
    min_size=1,
    max_size=36,
)


@st.composite
def frames(draw, max_size=30):
    size = draw(st.integers(1, max_size))
    ages = draw(st.lists(st.integers(0, 70), min_size=size, max_size=size))
    sexes = draw(
        st.lists(
            st.sampled_from(["female", "male"]), min_size=size, max_size=size
        )
    )
    return invented_frame(ages, sexes)


def exposed_rates(frame, rates):
    female = frame["sex"].to_numpy() == "female"
    return [
        rates[int(age)] if is_female and int(age) in rates else None
        for age, is_female in zip(frame["age"], female, strict=True)
    ]


# --------------------------------------------------------------------------
# 1-2. Expected births, zero and unit rates
# --------------------------------------------------------------------------
@settings(max_examples=60, deadline=None)
@given(frame=frames(), rates=rates_strategy)
def test_expected_births_is_the_sum_over_exposed_women(frame, rates):
    observed = expected_births(frame, rates)
    expected = sum(r for r in exposed_rates(frame, rates) if r is not None)
    assert observed == pytest.approx(expected, abs=1e-12)


@settings(max_examples=40, deadline=None)
@given(frame=frames(), draw_index=st.integers(0, 50))
def test_zero_rates_give_zero_births(frame, draw_index):
    context = invented_context(frame, draw=draw_index)
    births = draw_asfr_births(frame, context, dict.fromkeys(FERTILE, 0.0))
    assert births.empty
    assert list(births.columns) == ["parent_person_id", "birth_year"]


@settings(max_examples=40, deadline=None)
@given(frame=frames(), draw_index=st.integers(0, 50))
def test_unit_rates_give_every_exposed_woman_one_birth(frame, draw_index):
    context = invented_context(frame, draw=draw_index)
    births = draw_asfr_births(frame, context, dict.fromkeys(FERTILE, 1.0))
    female = frame["sex"] == "female"
    fertile = frame["age"].between(14, 49)
    mothers = set(frame.loc[female & fertile, "person_id"])
    assert set(births["parent_person_id"]) == mothers
    assert len(births) == len(mothers)
    assert (births["birth_year"] == context.year).all()


# --------------------------------------------------------------------------
# 3. Monte Carlo: mean births equal expected births
# --------------------------------------------------------------------------
@settings(max_examples=8, deadline=None)
@given(
    rates=st.dictionaries(
        st.sampled_from(list(FERTILE)),
        st.floats(0.02, 0.5),
        min_size=5,
        max_size=36,
    ),
    seed=st.integers(0, 2**16),
)
def test_mean_births_equal_expected_births(rates, seed):
    rng = np.random.default_rng(seed)
    ages = rng.integers(10, 60, size=40)
    sexes = np.where(rng.random(40) < 0.7, "female", "male")
    frame = invented_frame(ages, sexes)
    exposed = [r for r in exposed_rates(frame, rates) if r is not None]
    expected = sum(exposed)
    variance = sum(r * (1.0 - r) for r in exposed)
    draws = 150
    counts = [
        len(draw_asfr_births(frame, invented_context(frame, draw=k), rates))
        for k in range(draws)
    ]
    tolerance = 5.0 * math.sqrt(variance / draws) + 1e-12
    assert abs(np.mean(counts) - expected) <= tolerance


# --------------------------------------------------------------------------
# 4. Person-keyed, deterministic draws
# --------------------------------------------------------------------------
@settings(max_examples=30, deadline=None)
@given(
    frame=frames(),
    rates=rates_strategy,
    draw_index=st.integers(0, 20),
    keep=st.data(),
)
def test_a_womans_draw_does_not_depend_on_the_rest_of_the_frame(
    frame, rates, draw_index, keep
):
    full_context = invented_context(frame, draw=draw_index)
    full = set(
        draw_asfr_births(frame, full_context, rates)["parent_person_id"]
    )
    mask = keep.draw(
        st.lists(st.booleans(), min_size=len(frame), max_size=len(frame))
    )
    subset = frame.loc[mask].reset_index(drop=True)
    # The loop's ordinals are projection-wide, so the subset keeps them.
    sub_context = invented_context(
        subset, draw=draw_index, ordinals=full_context.person_ordinals
    )
    sub = set(draw_asfr_births(subset, sub_context, rates)["parent_person_id"])
    assert sub == full & set(subset["person_id"])
    again = draw_asfr_births(frame, full_context, rates)
    assert set(again["parent_person_id"]) == full


def test_the_stream_is_the_registry_tagged_child_of_the_fertility_module():
    frame = invented_frame([30], ["female"])
    context = invented_context(frame, draw=3)
    uniform = context.rng_registry.tagged_child_generator(
        1, ProjectionModule.FERTILITY, ASFR_STREAM_TAG, 0
    ).random()
    below = draw_asfr_births(frame, context, {30: min(1.0, uniform + 1e-9)})
    above = draw_asfr_births(frame, context, {30: max(0.0, uniform - 1e-9)})
    assert len(below) == 1 and above.empty


# --------------------------------------------------------------------------
# 5. Materialized births
# --------------------------------------------------------------------------
def test_the_step_materializes_age_zero_children_of_the_mothers():
    frame = invented_frame(
        [25, 30, 35, 60, 30], ["female", "female", "female", "female", "male"]
    )
    context = invented_context(frame)
    births_log, expected_log = {}, {}
    step = AsfrFertilityStep(
        asfr=lambda year: dict.fromkeys(FERTILE, 1.0),
        birth_log=births_log,
        expected_log=expected_log,
    )
    out = step(frame, context, empty_marital(frame), np.random.default_rng(0))
    children = out[out["synthetic_entry"].astype(bool)]
    assert len(children) == 3 == len(births_log[2030])
    assert expected_log[2030] == 3.0
    assert set(children["parent_person_id"]) == {1, 2, 3}
    assert (children["age"] == 0).all() and (children["year"] == 2030).all()
    assert (children["birth_year"] == 2030).all()
    assert children["person_id"].tolist() == [6, 7, 8]
    mothers = frame.set_index("person_id")
    for _, child in children.iterrows():
        mother = mothers.loc[child["parent_person_id"]]
        assert child["weight"] == mother["weight"]
        assert child["household_id"] == mother["household_id"]
    assert set(children["sex"]) <= {"female", "male"}
    assert len(out) == len(frame) + 3


def test_a_marital_reader_runs_before_the_draw():
    frame = invented_frame([30], ["female"])
    seen = []

    def reader(frame, context, marital, rng):
        seen.append(len(frame))
        return frame.assign(marital_status="single")

    step = AsfrFertilityStep(
        asfr=lambda year: {30: 0.0}, marital_reader=reader
    )
    out = step(
        frame,
        invented_context(frame),
        empty_marital(frame),
        np.random.default_rng(0),
    )
    assert seen == [1] and (out["marital_status"] == "single").all()


def test_a_multi_year_projection_grows_by_the_logged_births():
    """INVENTED open population projected 2031-2040 with the step."""
    ages = np.tile(np.arange(10, 50), 3)
    sexes = np.where(np.arange(ages.size) % 2 == 0, "female", "male")
    initial = invented_frame(ages, sexes, year=2030)
    births_log, expected_log = {}, {}

    def keep(frame, context, rng):
        return frame

    def marital(frame, context, rng):
        return empty_marital(frame)

    def household(frame, context, marital, rng):
        return frame

    modules = PeriodModules(
        mortality=keep,
        aging=advance_age,
        marital_core=marital,
        fertility=AsfrFertilityStep(
            asfr=lambda year: dict.fromkeys(FERTILE, 0.08),
            birth_log=births_log,
            expected_log=expected_log,
        ),
        disability=keep,
        earnings=keep,
        claiming=keep,
        household_composition=household,
    )
    result = ProjectionEngine(modules).project(
        initial, end_year=2040, draw_index=4
    )
    sizes = [len(frame) for frame in result.slices]
    for index, year in enumerate(range(2031, 2041), start=1):
        assert sizes[index] == sizes[index - 1] + len(births_log[year])
        assert expected_log[year] > 0.0
    final = result.slices[-1]
    born = final[final["synthetic_entry"].astype(bool)]
    assert (born["age"] == 2040 - born["birth_year"]).all()
    assert born["person_id"].is_unique
    assert sum(len(b) for b in births_log.values()) == len(born) > 0


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------
def test_rates_outside_the_unit_interval_are_refused():
    frame = invented_frame([30], ["female"])
    context = invented_context(frame)
    for bad in (1.2, -0.1, float("nan")):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            draw_asfr_births(frame, context, {30: bad})


def test_the_step_needs_the_registry_and_its_columns():
    frame = invented_frame([30], ["female"])
    bare = PeriodContext(period_index=1, year=2030, draw_index=0, metadata={})
    with pytest.raises(RuntimeError, match="RNG registry"):
        draw_asfr_births(frame, bare, {30: 0.1})
    with pytest.raises(ValueError, match="missing columns"):
        expected_births(frame.drop(columns="sex"), {30: 0.1})
    with pytest.raises(ValueError, match="report-only"):
        AsfrFertilityStep(asfr=lambda year: {}, label="gated")
    assert AsfrFertilityStep(asfr=lambda year: {}).label == (
        ASFR_FERTILITY_LABEL
    )
    assert ASFR_FERTILITY_LABEL == "not gated, report-only"


# --------------------------------------------------------------------------
# 6. The gated candidate-16 law is untouched
# --------------------------------------------------------------------------
def test_the_step_does_not_reach_the_gated_fertility_law():
    source = Path(fertility.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module)
            imported.update(f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    forbidden = (
        "populace_dynamics.models",
        "populace_dynamics.engine.marital",
        "populace_dynamics.engine.steps.apply_fertility",
    )
    assert not [
        name
        for name in imported
        if name and any(name.startswith(bad) for bad in forbidden)
    ]
    assert (
        "populace_dynamics.engine.steps.materialize_maternal_births"
        in imported
    )
