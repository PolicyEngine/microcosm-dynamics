"""Synthetic opt-in claiming checks; no fitted objects or external inputs."""

from __future__ import annotations

from functools import partial

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.engine.claiming import apply_claiming
from populace_dynamics.engine.loop import (
    MaritalStepResult,
    PeriodContext,
    PeriodModules,
    ProjectionEngine,
)
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import ClaimingSchedule, advance_age
from populace_dynamics.engine.steps import (
    apply_claiming as historical_apply_claiming,
)


class NoDraw:
    def choice(self, *args, **kwargs):
        raise AssertionError("ineligible people must not consume a draw")


class NoDistribution:
    def distribution(self, sex, year):
        raise AssertionError("ineligible people must not query a PMF")


def _context(person_ids=None, *, year=2020, period=1):
    if person_ids is None:
        return PeriodContext(period, year, 0, {})
    return PeriodContext(
        period,
        year,
        0,
        {},
        rng_registry=ProjectionRNGRegistry(0, 2),
        person_ordinals={
            person_id: ordinal
            for ordinal, person_id in enumerate(sorted(person_ids))
        },
    )


def _schedule():
    return ClaimingSchedule(
        {
            ("female", 2014): {62: 0.3, 65: 0.2, 70: 0.5},
            ("male", 2014): {62: 0.2, 66: 0.6, 70: 0.2},
        }
    )


@pytest.mark.parametrize("keyed", [False, True])
def test_converted_and_previously_claimed_people_never_draw(keyed):
    frame = pd.DataFrame(
        {
            "person_id": [10, 20],
            "age": [67, 68],
            "sex": ["male", "female"],
            "di_converted": [True, False],
            "claimed": [False, True],
            "claim_year": pd.array([pd.NA, 2018], dtype="Int64"),
        }
    )
    original = frame.copy(deep=True)
    # An empty ordinal map rejects even constructing a keyed person stream.
    context = _context([] if keyed else None)
    result = apply_claiming(
        frame, context, NoDraw(), schedule=NoDistribution()
    )

    assert result["claim_age"].isna().all()
    assert str(result["claim_age"].dtype) == "Int64"
    assert result["claimed"].tolist() == [True, True]
    assert result["claim_year"].tolist() == [2020, 2018]
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("keyed", [False, True])
def test_conversion_event_reset_does_not_cause_a_later_plan(keyed):
    frame = pd.DataFrame(
        {"age": [67], "sex": ["male"], "di_converted": [True]}
    )
    first = apply_claiming(
        frame,
        _context([] if keyed else None),
        NoDraw(),
        schedule=NoDistribution(),
    )
    second_input = first.assign(age=68, di_converted=False)
    second = apply_claiming(
        second_input,
        _context([] if keyed else None, year=2021, period=2),
        NoDraw(),
        schedule=NoDistribution(),
    )

    assert second["claim_age"].isna().all()
    assert second["claimed"].tolist() == [True]
    assert second["claim_year"].tolist() == [2020]


def test_supplied_plans_and_previously_claimed_years_are_preserved():
    frame = pd.DataFrame(
        {
            "age": [67, 68, 68, 63, 63, 70],
            "sex": ["male"] * 6,
            "di_converted": [True, True, False, False, False, False],
            "claimed": pd.array(
                [False, True, True, False, False, True], dtype="boolean"
            ),
            "claim_age": pd.array(
                [70, pd.NA, pd.NA, 64, 62, 60], dtype="Int64"
            ),
            "claim_year": pd.array(
                [pd.NA, 2018, 2017, pd.NA, pd.NA, 2010], dtype="Int64"
            ),
        },
        index=[9, 7, 5, 3, 1, 0],
    )
    original = frame.copy(deep=True)
    result = apply_claiming(
        frame, _context([]), NoDraw(), schedule=NoDistribution()
    )

    pd.testing.assert_series_equal(result["claim_age"], frame["claim_age"])
    assert result["claimed"].tolist() == [True, True, True, False, True, True]
    pd.testing.assert_series_equal(
        result["claim_year"],
        pd.Series(
            pd.array([2020, 2018, 2017, pd.NA, 2020, 2010], dtype="Int64"),
            index=frame.index,
            name="claim_year",
        ),
    )
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize(
    "year, expected_age", [(2019, 62), (2020, 62), (2021, 70)]
)
def test_age_50_threshold_and_nearest_year_selection(year, expected_age):
    schedule = ClaimingSchedule(
        {
            ("female", 2018): {62: 1.0},
            ("female", 2022): {70: 1.0},
        }
    )
    frame = pd.DataFrame(
        {"person_id": [10, 20], "age": [49, 50], "sex": ["male", "female"]}
    )
    # No male PMF or ordinal is needed for the under-50 person.
    result = apply_claiming(
        frame, _context([20], year=year), NoDraw(), schedule=schedule
    )

    assert pd.isna(result.loc[0, "claim_age"])
    assert result.loc[1, "claim_age"] == expected_age
    assert not result["claimed"].any()
    assert result["claim_year"].isna().all()


def test_converted_only_sex_needs_no_pmf_or_person_ordinal():
    frame = pd.DataFrame(
        {
            "person_id": [10, 20, 30],
            "age": [67, 62, 68],
            "sex": ["male", "female", "male"],
            "di_converted": [True, False, False],
            "claimed": [False, False, True],
        }
    )
    result = apply_claiming(
        frame,
        _context([20]),
        NoDraw(),
        schedule=ClaimingSchedule({("female", 2014): {62: 1.0}}),
    )

    assert result["claim_age"].isna().tolist() == [True, False, True]
    assert result.loc[1, "claim_age"] == 62
    assert result["claimed"].all()
    assert pd.isna(result.loc[result["person_id"] == 30, "claim_year"].iloc[0])


@pytest.mark.parametrize("flags", ["absent", "null"])
def test_missing_flags_retain_historical_nonconversion_behavior(flags):
    frame = pd.DataFrame(
        {
            "person_id": [10, 20, 30, 40],
            "age": [62, 68, 51, 49],
            "sex": ["female", "male", "female", "male"],
        }
    )
    if flags == "null":
        frame["di_converted"] = pd.array([pd.NA] * 4, dtype="boolean")
        frame["claimed"] = pd.array([pd.NA] * 4, dtype="boolean")
    context = _context(frame["person_id"])
    successor = apply_claiming(frame, context, NoDraw(), schedule=_schedule())
    historical = historical_apply_claiming(
        frame, context, NoDraw(), schedule=_schedule()
    )

    pd.testing.assert_frame_equal(successor, historical)


def test_keyed_nonentrant_draws_match_history_and_ignore_row_order():
    frame = pd.DataFrame(
        {
            "person_id": [60, 10, 40, 30, 20, 50],
            "age": [62, 67, 69, 66, 52, 63],
            "sex": ["female", "female", "male", "male", "female", "male"],
            "di_converted": [False, True, False, True, False, False],
            "claimed": [False, False, True, False, False, False],
        }
    )
    context = _context(frame["person_id"])
    successor = apply_claiming(frame, context, NoDraw(), schedule=_schedule())
    historical = historical_apply_claiming(
        frame, context, NoDraw(), schedule=_schedule()
    )
    eligible = ~frame["di_converted"] & ~frame["claimed"]
    pd.testing.assert_frame_equal(
        successor.loc[eligible], historical.loc[eligible]
    )
    for subset in (frame.iloc[[2, 5, 0, 3, 1, 4]], frame.loc[eligible]):
        replay = apply_claiming(
            subset, context, NoDraw(), schedule=_schedule()
        )
        pd.testing.assert_frame_equal(
            replay.sort_index(), successor.loc[subset.index].sort_index()
        )


def test_batch_fallback_is_reproducible_but_same_seed_can_shift_draws():
    frame = pd.DataFrame(
        {
            "age": [67, 51, 51, 51, 67, 51],
            "sex": ["female", "female", "male", "female", "male", "male"],
            "di_converted": [True, False, False, False, True, False],
        }
    )
    eligible = ~frame["di_converted"]
    first_rng = np.random.default_rng(21)
    replay_rng = np.random.default_rng(21)
    first = apply_claiming(frame, _context(), first_rng, schedule=_schedule())
    replay = apply_claiming(
        frame, _context(), replay_rng, schedule=_schedule()
    )
    pd.testing.assert_frame_equal(first, replay)
    assert first_rng.bytes(32) == replay_rng.bytes(32)

    # Exactly the eligible sex groups consume draws; there is no draw burning.
    eligible_rng = np.random.default_rng(21)
    eligible_only = apply_claiming(
        frame.loc[eligible], _context(), eligible_rng, schedule=_schedule()
    )
    pd.testing.assert_frame_equal(first.loc[eligible], eligible_only)
    # The preceding state comparison consumed 32 bytes from first_rng.
    eligible_rng.bytes(32)
    assert first_rng.bytes(32) == eligible_rng.bytes(32)

    historical = historical_apply_claiming(
        frame, _context(), np.random.default_rng(21), schedule=_schedule()
    )
    assert not first.loc[eligible, "claim_age"].equals(
        historical.loc[eligible, "claim_age"]
    )


def test_empty_frame_retains_nullable_claim_state_without_draws():
    frame = pd.DataFrame(
        {"age": pd.Series(dtype="int64"), "sex": pd.Series(dtype="str")}
    )
    result = apply_claiming(
        frame, _context([]), NoDraw(), schedule=NoDistribution()
    )

    assert result.empty
    assert result.dtypes.astype(str).to_dict() == {
        "age": "int64",
        "sex": str(frame["sex"].dtype),
        "claim_age": "Int64",
        "claimed": "bool",
        "claim_year": "Int64",
    }


@pytest.mark.parametrize("missing", ["age", "sex"])
def test_required_columns_are_validated_even_for_conversions(missing):
    frame = pd.DataFrame(
        {"age": [67], "sex": ["male"], "di_converted": [True]}
    ).drop(columns=missing)
    with pytest.raises(ValueError, match=f"missing columns.*{missing}"):
        apply_claiming(frame, _context(), NoDraw(), schedule=NoDistribution())


def test_successor_in_real_projection_loop_preserves_conversion_history():
    initial = pd.DataFrame(
        {
            "person_id": [30, 10, 20],
            "year": [2019] * 3,
            "age": [60, 66, 60],
            "sex": ["female", "male", "female"],
        }
    )
    schedule = ClaimingSchedule({("female", 2014): {62: 1.0}})

    def passthrough(frame, context, rng):
        return frame

    def marital(frame, context, rng):
        return MaritalStepResult(frame.copy(), pd.DataFrame())

    def marital_reader(frame, context, marital, rng):
        return frame

    def disability(frame, context, rng):
        return frame.assign(
            di_converted=(frame["person_id"] == 10) & (context.year == 2020)
        )

    modules = PeriodModules(
        mortality=passthrough,
        aging=advance_age,
        marital_core=marital,
        fertility=marital_reader,
        disability=disability,
        earnings=passthrough,
        claiming=partial(apply_claiming, schedule=schedule),
        household_composition=marital_reader,
    )
    result = ProjectionEngine(modules).project(
        initial, end_year=2021, draw_index=0
    )
    first, second = result.slices[1:]
    for projected in (first, second):
        converter = projected.set_index("person_id").loc[10]
        assert pd.isna(converter["claim_age"])
        assert converter["claimed"]
        assert converter["claim_year"] == 2020
    assert first.set_index("person_id").loc[10, "di_converted"]
    assert not second["di_converted"].any()
    assert not first.loc[first["person_id"] != 10, "claimed"].any()
    assert second["claimed"].all()
    assert second.loc[second["person_id"] != 10, "claim_year"].tolist() == [
        2021,
        2021,
    ]
    assert result.traces[0].steps == tuple(
        module.value for module in ProjectionModule
    )
    reordered = ProjectionEngine(modules).project(
        initial.iloc[::-1], end_year=2021, draw_index=0
    )
    pd.testing.assert_frame_equal(
        result.panel.sort_values(["year", "person_id"]).reset_index(drop=True),
        reordered.panel.sort_values(["year", "person_id"]).reset_index(
            drop=True
        ),
    )
