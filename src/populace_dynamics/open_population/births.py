"""Declare maternal additions around the unchanged fertility adapter.

Implement ``docs/design/open_population.md`` §§2.1, 2.2, 3.1 (OP1) and 7,
approved in ruling d1925. ``engine/loop.py:317–322`` supplies the fertility
adapter's frame, context, marital state and generator unchanged. The existing
materializer takes child IDs from that context's allocator
(``engine/steps.py:485–503``); this wrapper verifies that allocation and adds
provenance without drawing randomness.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from populace_dynamics.engine.accounting import PopulationEventKind
from populace_dynamics.engine.entrant_schedule import (
    ENTRY_KIND_BIRTH,
    ENTRY_KIND_COLUMN,
)
from populace_dynamics.engine.loop import (
    MaritalReaderStep,
    MaritalStepResult,
    PeriodContext,
)
from populace_dynamics.open_population.errors import (
    AccountingIdentityError,
    IdOrStreamCollision,
)
from populace_dynamics.open_population.events import EventLedger


@dataclass(frozen=True)
class BirthEntryAdapter:
    """Call fertility once and declare only its allocator-backed new rows."""

    step: MaritalReaderStep
    ledger: EventLedger

    def __call__(
        self,
        frame: pd.DataFrame,
        context: PeriodContext,
        marital: MaritalStepResult,
        rng: np.random.Generator,
    ) -> pd.DataFrame:
        """Declare allocator-backed births without new draws (design §7)."""
        # Snapshot before the delegated call, including adapters that mutate
        # their input in place. An ID alone cannot identify a reused child.
        before = frame[["person_id", "weight"]].copy(deep=True)
        if before["person_id"].duplicated().any():
            raise AccountingIdentityError("fertility input has duplicate IDs")
        allocator = context.synthetic_id_allocator
        cursor = allocator.next_id
        output = self.step(frame, context, marital, rng)
        if not isinstance(output, pd.DataFrame):
            raise AccountingIdentityError("fertility must return a frame")
        if {"person_id", "weight"} - set(output.columns):
            raise AccountingIdentityError("fertility lost roster columns")
        if output["person_id"].duplicated().any():
            raise AccountingIdentityError("fertility output has duplicate IDs")
        if context.synthetic_id_allocator is not allocator:
            raise IdOrStreamCollision("fertility replaced the run allocator")

        previous_ids = set(before["person_id"])
        current_ids = set(output["person_id"])
        if previous_ids - current_ids:
            raise AccountingIdentityError("fertility removed incumbent IDs")
        before_weights = before.set_index("person_id")["weight"]
        after_weights = output.set_index("person_id")["weight"]
        if not before_weights.eq(
            after_weights.reindex(before_weights.index)
        ).all():
            raise AccountingIdentityError(
                "fertility changed incumbent weights"
            )

        added_ids = current_ids - previous_ids
        allocated_count = allocator.next_id - cursor
        if allocated_count != len(added_ids) or added_ids != set(
            range(cursor, allocator.next_id)
        ):
            raise IdOrStreamCollision(
                "fertility additions do not match the projection allocation"
            )
        if not added_ids:
            return output

        out = output.copy()
        added = out["person_id"].isin(added_ids)
        if ENTRY_KIND_COLUMN not in out:
            out[ENTRY_KIND_COLUMN] = pd.Series(
                pd.NA, index=out.index, dtype=object
            )
        else:
            out[ENTRY_KIND_COLUMN] = out[ENTRY_KIND_COLUMN].astype(object)
        if "entry_year" not in out:
            out["entry_year"] = pd.Series(
                pd.NA, index=out.index, dtype="Int64"
            )
        out.loc[added, ENTRY_KIND_COLUMN] = ENTRY_KIND_BIRTH
        out.loc[added, "entry_year"] = context.year
        self.ledger.record(
            out.loc[added],
            year=context.year,
            kind=PopulationEventKind.BIRTH,
            entry_kind=ENTRY_KIND_BIRTH,
        )
        return out
