"""Invented declarations for OP1's explicit stock-flow contract (§7)."""

import pandas as pd
import pytest

from populace_dynamics.engine.accounting import PopulationEventKind as Kind
from populace_dynamics.open_population.errors import AccountingIdentityError
from populace_dynamics.open_population.events import EventLedger, FlowEvent


def test_events_snapshot_weights_and_provenance():
    frame = pd.DataFrame({"person_id": [2, 1], "weight": [0.0, 2.5]})
    ledger = EventLedger()
    ledger.record(
        frame, year=2026, kind=Kind.BIRTH, entry_kind="maternal_birth"
    )
    frame["weight"] = 8.0
    assert [event.person_id for event in ledger.events] == [1, 2]
    assert [event.weight for event in ledger.events] == [2.5, 0.0]
    assert ledger.events[0].as_accounting_event().reason == "maternal_birth"


@pytest.mark.parametrize("kind", [Kind.BIRTH, Kind.SCHEDULED_ENTRY])
def test_addition_requires_correct_entry_kind(kind):
    with pytest.raises(AccountingIdentityError, match="entry_kind"):
        FlowEvent(1, 2026, kind, 1.0, "invented_unknown_kind")


def test_exit_carries_only_exit_kind():
    with pytest.raises(AccountingIdentityError, match="exit"):
        FlowEvent(1, 2026, Kind.EMIGRATION, 1.0, "maternal_birth")
    assert FlowEvent(1, 2026, Kind.DEATH, 1.0).entry_kind is None


def test_year_index_preserves_declarations_and_returns_a_snapshot():
    first = FlowEvent(1, 2026, Kind.DEATH, 1.0)
    ledger = EventLedger([first])
    before = ledger.events_for_year(2026)
    ledger.record(
        pd.DataFrame({"person_id": [3], "weight": [2.0]}),
        year=2027,
        kind=Kind.EMIGRATION,
    )
    ledger.record(
        pd.DataFrame({"person_id": [2], "weight": [1.5]}),
        year=2026,
        kind=Kind.DEATH,
    )
    assert before == (first,)
    assert ledger.events_for_year(2026) == (first, ledger.events[2])
    assert ledger.events_for_year(2027) == (ledger.events[1],)
    assert ledger.events_for_year(2028) == ()
