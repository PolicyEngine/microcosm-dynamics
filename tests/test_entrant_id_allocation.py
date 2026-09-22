"""Projection metadata must not let an in-loop allocation reuse a known ID.

Every fixture here is SYNTHETIC: the survival and birth events are scripted
by the test, not drawn from a fitted law.  What is real is the projection
loop, the entrant schedule builder, and the maternal-birth materializer that
takes child IDs from ``context.synthetic_id_allocator``.

The failure these tests pin: ``M6RealizedPopulation.projection_metadata``
places a fresh ``SyntheticPersonIdAllocator(synthetic_id_start, reserved)`` in
the metadata on every call.  A schedule built from any *other* allocator that
starts at the same ``synthetic_id_start`` holds the same IDs the loop will
later hand to newborns.  When the entrant has already died, the birth takes
its ID silently, so one ``person_id`` names two different people (and shares
one stable RNG ordinal).

``engine/loop.py`` sits inside the birth-evidence reducer's reviewed
implementation identity, so the guard lives in
``entrant_schedule.validate_projection_allocator`` and callers run it on the
exact metadata they project with.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.engine import entrant_schedule as esm
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    MaritalStepResult,
    PeriodModules,
    ProjectionEngine,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.steps import (
    advance_age,
    materialize_maternal_births,
)

RESERVED = frozenset({1, 2, 3})
SYNTHETIC_ID_START = max(RESERVED) + 1  # the m6_population.py rule


def _donor() -> pd.DataFrame:
    """One SYNTHETIC 60-year-old male donor row."""
    return pd.DataFrame(
        {
            "person_id": [900],
            "weight": [1.0],
            "entry_age": [60],
            "is_female": [False],
            "source_year": [2024],
            "peinusyr": [28],
            "prcitshp": [4],
            "penatvty": [300],
            "foreign_born": [True],
        }
    )


def _initial() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "person_id": [1, 2, 3],
            "year": [2025, 2025, 2025],
            "age": [30, 40, 50],
            "sex": ["female", "male", "male"],
            "weight": [1.0, 1.0, 1.0],
        }
    )


def _modules(calls: list[int]) -> PeriodModules:
    """SYNTHETIC events: the entrant dies in 2027; person 1 gives birth in
    2028.  The birth itself goes through the real materializer."""

    def mortality(frame, context, rng):
        del rng
        calls.append(context.year)
        if context.year == 2027 and esm.ENTRY_KIND_COLUMN in frame:
            frame = frame.loc[frame[esm.ENTRY_KIND_COLUMN].isna()]
        return frame.sort_values("person_id").reset_index(drop=True)

    def marital(frame, context, rng):
        del context, rng
        births = pd.DataFrame(
            {
                "parent_person_id": [1],
                "birth_year": pd.array([2028], dtype="Int64"),
            }
        )
        return MaritalStepResult(frame.copy(), births)

    def fertility(frame, context, marital_result, rng):
        return materialize_maternal_births(
            frame, marital_result.births, context, rng
        )

    def passthrough(frame, context, rng):
        del context, rng
        return frame.copy()

    return PeriodModules(
        mortality=mortality,
        aging=advance_age,
        marital_core=marital,
        fertility=fertility,
        disability=passthrough,
        earnings=passthrough,
        claiming=passthrough,
        household_composition=lambda frame, context, result, rng: frame.copy(),
    )


def _split_allocator_metadata():
    """The reviewer's scenario: a schedule built with one allocator, the
    projection carrying a second allocator at the same start."""
    schedule = esm.build_entrant_schedule(
        _donor(),
        {2026: 1.0},
        allocator=SyntheticPersonIdAllocator(SYNTHETIC_ID_START, RESERVED),
    )
    assert schedule.frames[2026]["person_id"].tolist() == [4]
    projection_allocator = SyntheticPersonIdAllocator(
        SYNTHETIC_ID_START, RESERVED
    )
    return projection_allocator, {
        "synthetic_id_allocator": projection_allocator,
        SCHEDULED_ENTRIES_KEY: schedule.as_metadata(),
    }


def test_a_second_allocator_at_the_same_start_is_refused():
    projection_allocator, metadata = _split_allocator_metadata()
    with pytest.raises(
        ValueError,
        match=r"next_id 4 can reach initial or scheduled person_id \[4\]",
    ):
        esm.validate_projection_allocator(
            _initial()["person_id"], metadata
        )
    assert projection_allocator.next_id == SYNTHETIC_ID_START


def test_the_unvalidated_loop_still_reuses_the_id():
    """Pins why validation is required: the sealed loop does not check, and
    without the validator person 4 is both an immigrant and a newborn."""
    _, metadata = _split_allocator_metadata()
    result = ProjectionEngine(_modules([])).project(
        _initial(), end_year=2028, draw_index=0, metadata=metadata
    )
    rows = result.panel.loc[result.panel["person_id"] == 4]
    assert sorted(rows["year"].tolist()) == [2026, 2028]


def test_the_shared_allocator_gives_the_birth_a_fresh_id():
    """The supported path: build the schedule with the same allocator object
    the projection uses, so the cursor is already past the entrant."""
    allocator = SyntheticPersonIdAllocator(SYNTHETIC_ID_START, RESERVED)
    schedule = esm.build_entrant_schedule(
        _donor(), {2026: 1.0}, allocator=allocator
    )
    metadata = {
        "synthetic_id_allocator": allocator,
        SCHEDULED_ENTRIES_KEY: schedule.as_metadata(),
    }
    esm.validate_projection_allocator(_initial()["person_id"], metadata)
    calls: list[int] = []
    result = ProjectionEngine(_modules(calls)).project(
        _initial(), end_year=2028, draw_index=0, metadata=metadata
    )
    assert calls == [2026, 2027, 2028]
    panel = result.panel
    entrant = panel.loc[panel["person_id"] == 4]
    assert entrant["year"].tolist() == [2026]
    assert entrant[esm.ENTRY_KIND_COLUMN].tolist() == [
        esm.ENTRY_KIND_IMMIGRANT
    ]
    newborn = result.slices[-1].loc[lambda f: f["parent_person_id"].notna()]
    assert newborn["person_id"].tolist() == [5]
    assert newborn["parent_person_id"].tolist() == [1]
    assert allocator.next_id == 6


def test_an_initial_roster_id_at_or_above_the_cursor_is_refused():
    """The same collision class without a schedule."""
    initial = _initial()
    initial.loc[2, "person_id"] = 50
    with pytest.raises(ValueError, match=r"person_id \[50\]"):
        esm.validate_projection_allocator(
            initial["person_id"],
            {"synthetic_id_allocator": SyntheticPersonIdAllocator(10)},
        )


@pytest.mark.parametrize(
    "allocator",
    [
        SyntheticPersonIdAllocator(51),
        SyntheticPersonIdAllocator(np.int64(51)),
        # A real ID above the cursor is safe when it is reserved: allocate()
        # raises rather than hand it out (the large-native-ID fixture shape).
        SyntheticPersonIdAllocator(10, frozenset({1, 2, 50})),
    ],
    ids=["above", "numpy-above", "reserved-above-cursor"],
)
def test_a_cursor_that_cannot_reach_a_known_id_is_accepted(allocator):
    initial = _initial()
    initial.loc[2, "person_id"] = 50
    esm.validate_projection_allocator(
        initial["person_id"], {"synthetic_id_allocator": allocator}
    )


def test_metadata_without_an_allocator_is_accepted():
    esm.validate_projection_allocator(_initial()["person_id"], {})


def test_a_non_allocator_is_refused():
    with pytest.raises(TypeError, match="SyntheticPersonIdAllocator"):
        esm.validate_projection_allocator(
            _initial()["person_id"], {"synthetic_id_allocator": object()}
        )
