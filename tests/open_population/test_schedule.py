"""Invented schedule ownership examples and design §7 identity properties."""

from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal

from populace_dynamics.engine.entrant_schedule import (
    build_entrant_schedule,
    validate_projection_allocator,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.open_population.errors import IdOrStreamCollision
from populace_dynamics.open_population.schedule import (
    prepare_scheduled_entries,
)


def _initial():
    return pd.DataFrame({"person_id": [1, 2], "year": 2025, "weight": 1.0})


def _donor():
    return pd.DataFrame(
        {
            "person_id": [701, 702],
            "weight": [1.0, 3.0],
            "entry_age": [25, 30],
            "is_female": [True, False],
            "source_year": 2024,
            "peinusyr": 1,
            "prcitshp": 4,
            "penatvty": 100,
            "foreign_born": [True, True],
        }
    )


@settings(max_examples=20, deadline=None)
@given(controls=st.lists(st.integers(0, 5), min_size=1, max_size=5))
def test_schedule_uses_the_exact_owned_allocator_without_reusing_ids(controls):
    """Design §§2.3 and 7: all future additions precede the birth cursor."""
    given_allocator = []

    def build(allocator):
        given_allocator.append(allocator)
        return build_entrant_schedule(
            _donor(),
            {
                2026 + index: control / 1000
                for index, control in enumerate(controls)
            },
            allocator=allocator,
        )

    metadata = prepare_scheduled_entries(
        _initial(), schedule_builder=build, reserved_real_ids=[900]
    )
    allocator = metadata["synthetic_id_allocator"]
    assert given_allocator == [allocator]
    assert allocator.reserved_real_ids == frozenset({900})
    validate_projection_allocator(_initial()["person_id"], metadata)
    scheduled = metadata[SCHEDULED_ENTRIES_KEY]
    ids = []
    for year, cohort in scheduled.items():
        ids.extend(cohort["person_id"])
        assert set(cohort["entry_kind"]) == {"immigrant_cohort"}
        assert set(cohort["entry_year"]) == {year}
        assert set(cohort["year"]) == {year - 1}
    assert len(ids) == 2 * sum(control > 0 for control in controls)
    assert len(set(ids)) == len(ids)
    assert set(allocator.allocate(3)).isdisjoint({1, 2, *ids})


def test_prebuilt_frames_are_copied_and_the_birth_cursor_skips_them():
    frame = pd.DataFrame(
        {"person_id": [101, 100], "year": 2025, "weight": 2.0}
    )
    before = frame.copy(deep=True)
    metadata = prepare_scheduled_entries(_initial(), frames={2026: frame})
    assert_frame_equal(frame, before)
    assert metadata["synthetic_id_allocator"].next_id == 102
    cohort = metadata[SCHEDULED_ENTRIES_KEY][2026]
    assert cohort["person_id"].tolist() == [100, 101]
    assert cohort["entry_kind"].tolist() == ["immigrant_cohort"] * 2
    assert cohort["entry_year"].tolist() == [2026] * 2


def test_validator_receives_the_exact_returned_metadata(monkeypatch):
    calls = []

    def validate(ids, metadata):
        calls.append(metadata)
        validate_projection_allocator(ids, metadata)

    monkeypatch.setattr(
        "populace_dynamics.open_population.schedule.validate_projection_allocator",
        validate,
    )
    original = {"scenario": "invented"}
    metadata = prepare_scheduled_entries(_initial(), metadata=original)
    assert calls[0] is metadata
    assert original == {"scenario": "invented"}


@pytest.mark.parametrize(
    "key", [SCHEDULED_ENTRIES_KEY, "synthetic_id_allocator"]
)
def test_metadata_cannot_smuggle_a_separate_schedule_or_allocator(key):
    with pytest.raises(IdOrStreamCollision, match="ID_OR_STREAM_COLLISION"):
        prepare_scheduled_entries(_initial(), metadata={key: None})


def test_builder_cannot_substitute_a_separate_allocator():
    def build(allocator):
        separate = SyntheticPersonIdAllocator(3)
        return build_entrant_schedule(
            _donor(), {2026: 0.001}, allocator=separate
        )

    with pytest.raises(IdOrStreamCollision, match="projection allocator"):
        prepare_scheduled_entries(_initial(), schedule_builder=build)


@pytest.mark.parametrize("ids", [[1], [3, 3]])
def test_repeated_initial_or_scheduled_ids_are_named_collisions(ids):
    frames = {
        2026: pd.DataFrame({"person_id": ids, "year": 2025, "weight": 1.0})
    }
    with pytest.raises(IdOrStreamCollision, match="ID_OR_STREAM_COLLISION"):
        prepare_scheduled_entries(_initial(), frames=frames)


def test_prebuilt_entrant_cannot_take_a_reserved_real_id():
    frame = pd.DataFrame({"person_id": [100], "year": 2025, "weight": 1.0})
    with pytest.raises(IdOrStreamCollision, match="reserved real IDs"):
        prepare_scheduled_entries(
            _initial(), frames={2026: frame}, reserved_real_ids=[100]
        )
