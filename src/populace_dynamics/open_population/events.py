"""Declare OP1 flows at adapter boundaries, including transient entrants.

Implement ``docs/design/open_population.md`` §§3.1 (OP1), 5.4 and 7,
approved in ruling d1925. ``engine/accounting.py:284–369`` accepts explicit
event weights, which preserve scheduled entrants who exit before year-end.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from populace_dynamics.engine.accounting import (
    ADDITION_KINDS,
    PopulationEvent,
    PopulationEventKind,
)
from populace_dynamics.engine.entrant_schedule import (
    ENTRY_KIND_BIRTH,
    ENTRY_KIND_IMMIGRANT,
)
from populace_dynamics.open_population.errors import AccountingIdentityError

ENTRY_KINDS = {
    PopulationEventKind.BIRTH: ENTRY_KIND_BIRTH,
    PopulationEventKind.SCHEDULED_ENTRY: ENTRY_KIND_IMMIGRANT,
}


@dataclass(frozen=True)
class FlowEvent:
    """Keep one cause and, for additions, one explicit entry kind."""

    person_id: int
    year: int
    kind: PopulationEventKind
    weight: float
    entry_kind: str | None = None

    def __post_init__(self) -> None:
        event = self.as_accounting_event()
        object.__setattr__(self, "kind", event.kind)
        if event.kind in ADDITION_KINDS:
            if self.entry_kind != ENTRY_KINDS.get(event.kind):
                raise AccountingIdentityError(
                    "addition has unknown entry_kind"
                )
        elif self.entry_kind is not None:
            raise AccountingIdentityError("exit cannot carry an entry_kind")

    def as_accounting_event(self) -> PopulationEvent:
        """Translate provenance into the existing accounting interface."""
        return PopulationEvent(
            person_id=self.person_id,
            kind=self.kind,
            year=self.year,
            weight=self.weight,
            source="open_population",
            reason=self.entry_kind or "",
        )


@dataclass
class EventLedger:
    """Collect declarations within one run; never share a ledger across runs."""

    events: list[FlowEvent] = field(default_factory=list)
    _by_year: dict[int, list[FlowEvent]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        for event in self.events:
            self._by_year.setdefault(event.year, []).append(event)

    def events_for_year(self, year: int) -> tuple[FlowEvent, ...]:
        """Read that year's declarations for design §7's annual identity."""
        return tuple(self._by_year.get(year, ()))

    def record(
        self,
        frame: pd.DataFrame,
        *,
        year: int,
        kind: PopulationEventKind,
        entry_kind: str | None = None,
    ) -> None:
        """Snapshot IDs and weights where an adapter declares their cause."""
        declared = [
            FlowEvent(
                person_id=person_id,
                year=year,
                kind=kind,
                weight=weight,
                entry_kind=entry_kind,
            )
            for person_id, weight in frame.sort_values("person_id")[
                ["person_id", "weight"]
            ].itertuples(index=False, name=None)
        ]
        self.events.extend(declared)
        self._by_year.setdefault(year, []).extend(declared)
