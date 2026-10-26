"""Run OP1 around the sealed annual loop with declared stock-flow checks.

Implement ``docs/design/open_population.md`` §§2.1, 2.9–2.10, 3.1 (OP1),
5.4 and 7–8, approved in ruling d1925. ``engine/loop.py:271–286`` appends
scheduled entries before mortality; ``:297–350`` fixes the eight adapter
slots. Wrappers declare causes at those boundaries without changing draws.
``engine/accounting.py:1044–1086`` reports revaluations separately from
summation residuals; OP1 refuses revaluation because its identity fixes weights.
``engine/accounting_history.py:172–187`` supplies the single-presence contract.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from functools import wraps
from types import MappingProxyType
from typing import Any, Literal

import pandas as pd

from populace_dynamics.engine.accounting import (
    ADDITION_KINDS,
    PopulationAccountingError,
    PopulationEventKind,
    reconcile_period,
)
from populace_dynamics.engine.accounting_history import (
    SINGLE_PRESENCE_EPISODE,
    AnnualTransition,
    HistoryAccount,
    reconcile_history,
)
from populace_dynamics.engine.entrant_schedule import (
    ENTRY_KIND_IMMIGRANT,
    EntrantSchedule,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    PeriodModules,
    ProjectionEngine,
    ProjectionResult,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.open_population.births import BirthEntryAdapter
from populace_dynamics.open_population.errors import (
    AccountingIdentityError,
    IdOrStreamCollision,
)
from populace_dynamics.open_population.events import EventLedger, FlowEvent
from populace_dynamics.open_population.exits import (
    EmigrationHazard,
    _ExitAdapter,
    require_emigration_compatible,
)
from populace_dynamics.open_population.schedule import (
    prepare_scheduled_entries,
)

REGISTERED_PRODUCTION_HORIZONS = MappingProxyType(
    {"tr2026_intermediate": 2100}
)


def _registered_horizon(scenario: str) -> int:
    """Resolve the single production horizon from design §2.9."""
    try:
        return REGISTERED_PRODUCTION_HORIZONS[scenario]
    except KeyError as error:
        raise IdOrStreamCollision(
            f"unknown production scenario {scenario!r}"
        ) from error


@dataclass(frozen=True, slots=True)
class ProductionRequest:
    """Bind production to a scenario's horizon (design §§2.9, 7)."""

    scenario: str
    draw_index: int = 0
    start_year: int | None = None

    def __post_init__(self) -> None:
        if type(self.scenario) is not str:
            raise TypeError("production scenario must be a string")
        if type(self.draw_index) is not int:
            raise TypeError("production draw_index must be an integer")
        if self.start_year is not None and type(self.start_year) is not int:
            raise TypeError("production start_year must be an integer or None")
        _registered_horizon(self.scenario)

    @property
    def end_year(self) -> int:
        """Read the scenario horizon; callers cannot supply it (§2.9)."""
        return _registered_horizon(self.scenario)


@dataclass(frozen=True)
class OpenPopulationResult:
    """Expose accounted slices and declarations from one completed run."""

    projection: ProjectionResult
    accounting: HistoryAccount
    events: tuple[FlowEvent, ...]
    start_year: int
    horizon: int
    kind: Literal["production", "gate"]
    scenario: str | None

    def read_prefix(self, end_year: int) -> ProjectionResult:
        """Copy a prefix of this run without scheduling or simulating again."""
        if type(end_year) is not int or not (
            self.start_year <= end_year <= self.horizon
        ):
            raise ValueError("prefix end_year lies outside this run")
        length = end_year - self.start_year
        return ProjectionResult(
            slices=tuple(
                frame.copy() for frame in self.projection.slices[: length + 1]
            ),
            traces=self.projection.traces[:length],
            draw_index=self.projection.draw_index,
        )


def _stock(frame: pd.DataFrame) -> pd.Series:
    if not isinstance(frame, pd.DataFrame) or {"person_id", "weight"} - set(
        frame.columns
    ):
        raise AccountingIdentityError(
            "adapter returned a malformed stock frame"
        )
    if frame["person_id"].duplicated().any():
        raise AccountingIdentityError("adapter produced duplicate IDs")
    return frame.set_index("person_id")["weight"].sort_index().copy()


def _fixed_stock(step: Callable, *, marital: bool = False) -> Callable:
    """Check slots that cannot declare arrivals, exits or weight changes."""

    @wraps(step)
    def checked(frame, *args):
        before = _stock(frame)
        result = step(frame, *args)
        after = _stock(frame if marital else result)
        if (
            not before.index.equals(after.index)
            or not (before.to_numpy() == after.to_numpy()).all()
        ):
            raise AccountingIdentityError(
                "a non-flow adapter changed person IDs or fixed weights"
            )
        return result

    return checked


def _project(
    initial_slice: pd.DataFrame,
    modules: PeriodModules,
    *,
    end_year: int,
    draw_index: int,
    start_year: int | None = None,
    scheduled_entries: Mapping[int, pd.DataFrame] | None = None,
    schedule_builder: (
        Callable[
            [SyntheticPersonIdAllocator],
            EntrantSchedule | Mapping[int, pd.DataFrame],
        ]
        | None
    ) = None,
    metadata: Mapping[str, Any] | None = None,
    emigration_hazard: EmigrationHazard | None = None,
    reserved_real_ids: Iterable[int] = (),
    kind: Literal["production", "gate"],
    scenario: str | None,
) -> OpenPopulationResult:
    """Wrap the sealed loop and reconcile every transition (design §§5.4, 7)."""
    require_emigration_compatible(modules.marital_core, emigration_hazard)
    ProjectionEngine._validate_slice(initial_slice, "initial_slice")
    # Run the initializer exactly once, before constructing allocator metadata.
    # The sealed loop does the same before any RNG draw (loop.py:203–217).
    current = initial_slice.copy()
    if modules.initialize is not None:
        current = modules.initialize(current)
    ProjectionEngine._validate_slice(current, "initialized initial_slice")
    if set(current["person_id"]) != set(initial_slice["person_id"]):
        raise AccountingIdentityError("initializer changed the starting IDs")
    # Match engine/loop.py:284–286, which canonicalizes years with entrants.
    current = current.sort_values("person_id", kind="stable").reset_index(
        drop=True
    )
    if current.empty:
        if start_year is None:
            raise ValueError("empty initial_slice requires start_year")
    else:
        years = current["year"].unique()
        if len(years) != 1 or (
            start_year is not None and years[0] != start_year
        ):
            raise ValueError("initial_slice must carry its starting year")
        start_year = int(years[0])
        if set(initial_slice["year"].unique()) != {start_year}:
            raise AccountingIdentityError(
                "initializer changed the starting year"
            )
    if end_year <= start_year:
        raise ValueError("OP1 requires at least one projected year")

    shared = prepare_scheduled_entries(
        current,
        frames=scheduled_entries,
        schedule_builder=schedule_builder,
        metadata=metadata,
        reserved_real_ids=reserved_real_ids,
    )
    ledger = EventLedger()
    exit_step = _ExitAdapter(modules.mortality, ledger, emigration_hazard)
    transitions: list[AnnualTransition] = []
    # The accountants read only these columns (accounting.py:690–703;
    # accounting_history.py:152–159). Retain only their stock snapshots.
    stock_columns = ["person_id", "year", "weight"]
    opening = current[stock_columns].copy()

    def mortality(frame, context, rng):
        entries = shared[SCHEDULED_ENTRIES_KEY].get(context.year)
        if entries is not None:
            ledger.record(
                entries,
                year=context.year,
                kind=PopulationEventKind.SCHEDULED_ENTRY,
                entry_kind=ENTRY_KIND_IMMIGRANT,
            )
        return exit_step(frame, context, rng)

    household_step = _fixed_stock(modules.household_composition)

    def close_period(frame, context, marital, rng):
        nonlocal opening
        closing = household_step(frame, context, marital, rng)
        events = ledger.events_for_year(context.year)
        transition = AnnualTransition(
            opening_year=context.year - 1,
            closing_year=context.year,
            opening=opening,
            closing=closing[stock_columns].copy(),
            additions=tuple(
                event.as_accounting_event()
                for event in events
                if event.kind in ADDITION_KINDS
            ),
            exits=tuple(
                event.as_accounting_event()
                for event in events
                if event.kind not in ADDITION_KINDS
            ),
        )
        try:
            account = reconcile_period(
                opening,
                closing,
                opening_year=transition.opening_year,
                closing_year=transition.closing_year,
                additions=transition.additions,
                exits=transition.exits,
            )
        except PopulationAccountingError as error:
            raise AccountingIdentityError(str(error)) from error
        if account.weights.revaluation.total != 0:
            raise AccountingIdentityError("fixed person weights changed")
        transitions.append(transition)
        opening = transition.closing
        return closing

    wrapped = replace(
        modules,
        initialize=None,
        mortality=mortality,
        aging=_fixed_stock(modules.aging),
        marital_core=_fixed_stock(modules.marital_core, marital=True),
        fertility=BirthEntryAdapter(modules.fertility, ledger),
        disability=_fixed_stock(modules.disability),
        earnings=_fixed_stock(modules.earnings),
        claiming=_fixed_stock(modules.claiming),
        household_composition=close_period,
    )
    try:
        projection = ProjectionEngine(wrapped).project(
            current,
            end_year=end_year,
            draw_index=draw_index,
            start_year=start_year,
            metadata=shared,
        )
        history = reconcile_history(
            transitions, identity_contract=SINGLE_PRESENCE_EPISODE
        )
    except PopulationAccountingError as error:
        raise AccountingIdentityError(str(error)) from error
    return OpenPopulationResult(
        projection=projection,
        accounting=history,
        events=tuple(ledger.events),
        start_year=start_year,
        horizon=end_year,
        kind=kind,
        scenario=scenario,
    )


def run_production(
    initial_slice: pd.DataFrame,
    modules: PeriodModules,
    request: ProductionRequest,
    **kwargs: Any,
) -> OpenPopulationResult:
    """Execute the registered production horizon through the sealed loop."""
    if type(request) is not ProductionRequest:
        raise TypeError("run_production requires a ProductionRequest")
    return _project(
        initial_slice,
        modules,
        end_year=request.end_year,
        draw_index=request.draw_index,
        start_year=request.start_year,
        kind="production",
        scenario=request.scenario,
        **kwargs,
    )
