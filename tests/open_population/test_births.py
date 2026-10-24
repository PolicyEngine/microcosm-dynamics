"""Invented birth-adapter examples and design §7 addition invariants."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal

from populace_dynamics.engine.accounting import PopulationEventKind
from populace_dynamics.engine.loop import (
    MaritalStepResult,
    PeriodContext,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.steps import materialize_maternal_births
from populace_dynamics.open_population.births import BirthEntryAdapter
from populace_dynamics.open_population.errors import (
    AccountingIdentityError,
    IdOrStreamCollision,
)
from populace_dynamics.open_population.events import EventLedger


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "person_id": [1, 2],
            "year": [2026, 2026],
            "age": [28, 29],
            "sex": ["female", "female"],
            "weight": [1.25, 3.5],
            "household_id": [10, 20],
        }
    )


def _context() -> PeriodContext:
    return PeriodContext(
        period_index=1,
        year=2026,
        draw_index=0,
        metadata={"synthetic_id_allocator": SyntheticPersonIdAllocator(100)},
    )


def _marital(parents: list[int]) -> MaritalStepResult:
    return MaritalStepResult(
        sim_years=pd.DataFrame(),
        births=pd.DataFrame(
            {
                "parent_person_id": pd.Series(parents, dtype="int64"),
                "birth_year": pd.Series([2026] * len(parents), dtype="int64"),
            }
        ),
    )


def _fertility(frame, context, marital, rng):
    return materialize_maternal_births(frame, marital.births, context, rng)


@settings(max_examples=20, deadline=None)
@given(
    parents=st.lists(st.sampled_from([1, 2]), max_size=8),
    seed=st.integers(0, 99),
)
def test_births_preserve_draws_ids_weights_and_known_entry_kind(parents, seed):
    """Design §§2.2 and 7: label the same allocator-backed birth outcome."""
    frame = _frame()
    marital = _marital(parents)
    direct_context = _context()
    context = _context()
    direct_rng = np.random.default_rng(seed)
    rng = np.random.default_rng(seed)
    expected = _fertility(frame, direct_context, marital, direct_rng)
    ledger = EventLedger()
    actual = BirthEntryAdapter(_fertility, ledger)(
        frame, context, marital, rng
    )

    assert_frame_equal(actual[expected.columns], expected)
    assert rng.random() == direct_rng.random()
    assert context.synthetic_id_allocator.next_id == 100 + len(parents)
    assert len(ledger.events) == len(parents)
    for event, parent in zip(ledger.events, parents, strict=True):
        assert event.kind is PopulationEventKind.BIRTH
        assert event.year == 2026
        assert event.entry_kind == "maternal_birth"
        assert (
            event.weight == frame.set_index("person_id").loc[parent, "weight"]
        )
    if parents:
        added = actual.loc[actual["person_id"] >= 100]
        assert set(added["person_id"]) == set(range(100, 100 + len(parents)))
        assert set(added["entry_kind"]) == {"maternal_birth"}
        assert set(added["entry_year"]) == {2026}


def test_fertility_receives_the_exact_supplied_arguments_once():
    frame, context, marital = _frame(), _context(), _marital([])
    rng = np.random.default_rng(0)
    calls = []

    def step(*args):
        calls.append(args)
        return args[0]

    assert (
        BirthEntryAdapter(step, EventLedger())(frame, context, marital, rng)
        is frame
    )
    assert len(calls) == 1
    assert all(
        a is b
        for a, b in zip(calls[0], (frame, context, marital, rng), strict=True)
    )


@pytest.mark.parametrize("action", ["remove", "reweight", "duplicate"])
def test_birth_boundary_refuses_incumbent_changes_even_in_place(action):
    def step(frame, context, marital, rng):
        if action == "remove":
            frame.drop(index=frame.index[0], inplace=True)
        elif action == "reweight":
            frame.loc[0, "weight"] = 999.0
        else:
            frame.loc[1, "person_id"] = 1
        return frame

    with pytest.raises(
        AccountingIdentityError, match="ACCOUNTING_IDENTITY_FAIL"
    ):
        BirthEntryAdapter(step, EventLedger())(
            _frame(), _context(), _marital([]), np.random.default_rng(0)
        )


@pytest.mark.parametrize("allocate", [False, True])
def test_birth_boundary_refuses_ids_outside_the_allocator_range(allocate):
    def step(frame, context, marital, rng):
        if allocate:
            context.synthetic_id_allocator.allocate(2)
        added = frame.iloc[:1].copy()
        added["person_id"] = 100
        return pd.concat([frame, added], ignore_index=True)

    with pytest.raises(IdOrStreamCollision, match="ID_OR_STREAM_COLLISION"):
        BirthEntryAdapter(step, EventLedger())(
            _frame(), _context(), _marital([]), np.random.default_rng(0)
        )
