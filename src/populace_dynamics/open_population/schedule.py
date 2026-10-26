"""Build scheduled-entry metadata and its allocator as one owned bundle.

Implement ``docs/design/open_population.md`` §§2.1, 2.3, 3.1 (OP1) and 7,
approved in ruling d1925. ``engine/loop.py:226–250`` validates schedule
coordinates and repeated IDs, and ``:271–286`` activates entrants before
mortality. ``engine/entrant_schedule.py:457–507`` requires validation on the
exact projection metadata because the sealed loop does not check allocator
reachability. Entries are declared by the harness when activated, so an
entrant who exits that year retains both explicit events.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from numbers import Integral
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.engine.entrant_schedule import (
    ENTRY_KIND_COLUMN,
    ENTRY_KIND_IMMIGRANT,
    EntrantSchedule,
    validate_projection_allocator,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.open_population.errors import IdOrStreamCollision

ScheduleBuilder = Callable[
    [SyntheticPersonIdAllocator], EntrantSchedule | Mapping[int, pd.DataFrame]
]
_INT64_MAX = np.iinfo(np.int64).max
_INT64_MIN = np.iinfo(np.int64).min


def _ids(values: Iterable[object]) -> list[int]:
    """Validate signed IDs for the design §§2.1 and 7 allocator contract."""
    result = []
    for value in values:
        if (
            isinstance(value, (bool, np.bool_))
            or not isinstance(value, Integral)
            or not _INT64_MIN <= int(value) <= _INT64_MAX
        ):
            raise IdOrStreamCollision(
                "person IDs must be signed int64 integers"
            )
        result.append(int(value))
    return result


def _frames(
    frames: Mapping[int, pd.DataFrame],
) -> dict[int, pd.DataFrame]:
    """Copy and label scheduled cohorts under design §§2.3 and 7."""
    if not isinstance(frames, Mapping):
        raise TypeError("scheduled entries must be a mapping")
    result = {}
    for raw_year, frame in frames.items():
        if isinstance(raw_year, (bool, np.bool_)) or not isinstance(
            raw_year, Integral
        ):
            raise ValueError("scheduled entry years must be integers")
        year = int(raw_year)
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("scheduled entries must be pandas frames")
        if {"person_id", "year", "weight"} - set(frame.columns):
            raise ValueError(
                "scheduled entries need person_id, year and weight"
            )
        _ids(frame["person_id"])
        if frame.empty:
            continue
        if set(frame["year"]) != {year - 1}:
            raise ValueError(
                "scheduled entries must carry activation year - 1"
            )
        if (
            ENTRY_KIND_COLUMN in frame
            and not frame[ENTRY_KIND_COLUMN].eq(ENTRY_KIND_IMMIGRANT).all()
        ):
            raise ValueError("scheduled entries require immigrant_cohort kind")
        if "entry_year" in frame and not frame["entry_year"].eq(year).all():
            raise ValueError(
                "scheduled entry_year differs from activation year"
            )
        copied = frame.copy(deep=True)
        copied[ENTRY_KIND_COLUMN] = ENTRY_KIND_IMMIGRANT
        copied["entry_year"] = year
        result[year] = copied.sort_values(
            "person_id", kind="stable"
        ).reset_index(drop=True)
    return dict(sorted(result.items()))


def prepare_scheduled_entries(
    initial_slice: pd.DataFrame,
    *,
    frames: Mapping[int, pd.DataFrame] | None = None,
    schedule_builder: ScheduleBuilder | None = None,
    metadata: Mapping[str, Any] | None = None,
    reserved_real_ids: Iterable[int] = (),
) -> dict[str, Any]:
    """Return fresh metadata owning one allocator and copied entrant frames.

    A builder receives the exact allocator placed in the returned metadata;
    it can call ``build_entrant_schedule`` unchanged. Already-built frames
    retain their IDs, and the fresh allocation cursor starts above them.
    """
    if frames is not None and schedule_builder is not None:
        raise ValueError("provide frames or schedule_builder, not both")
    prepared = dict(metadata or {})
    if {SCHEDULED_ENTRIES_KEY, "synthetic_id_allocator"} & prepared.keys():
        raise IdOrStreamCollision(
            "metadata cannot supply a separate schedule or allocator"
        )
    initial_ids = _ids(initial_slice["person_id"])
    reserved = frozenset(_ids(reserved_real_ids))
    normalized = _frames(frames) if frames is not None else {}
    known = list(initial_ids)
    known.extend(
        person_id
        for cohort in normalized.values()
        for person_id in _ids(cohort["person_id"])
    )
    if len(known) != len(set(known)):
        raise IdOrStreamCollision("initial and scheduled person IDs overlap")
    if (set(known) - set(initial_ids)) & reserved:
        raise IdOrStreamCollision("scheduled IDs overlap reserved real IDs")
    # Match the sealed loop's signed-ID convention (loop.py:251–253).
    cursor = max([*known, *reserved], default=0) + 1
    if cursor > _INT64_MAX:
        raise IdOrStreamCollision(
            "no signed-int64 ID remains above the roster"
        )
    allocator = SyntheticPersonIdAllocator(cursor, reserved_real_ids=reserved)
    if schedule_builder is not None:
        built = schedule_builder(allocator)
        normalized = _frames(
            built.frames if isinstance(built, EntrantSchedule) else built
        )
        known = list(initial_ids)
        known.extend(
            person_id
            for cohort in normalized.values()
            for person_id in _ids(cohort["person_id"])
        )
        if len(known) != len(set(known)):
            raise IdOrStreamCollision(
                "initial and scheduled person IDs overlap"
            )
        scheduled_ids = set(known) - set(initial_ids)
        if allocator.next_id - cursor != len(
            scheduled_ids
        ) or scheduled_ids != set(range(cursor, allocator.next_id)):
            raise IdOrStreamCollision(
                "schedule builder did not use the projection allocator"
            )
    prepared[SCHEDULED_ENTRIES_KEY] = normalized
    prepared["synthetic_id_allocator"] = allocator
    try:
        validate_projection_allocator(initial_ids, prepared)
    except (TypeError, ValueError) as error:
        raise IdOrStreamCollision(str(error)) from error
    return prepared
