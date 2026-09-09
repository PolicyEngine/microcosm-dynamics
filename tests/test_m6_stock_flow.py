"""Tests for the experimental annual stock-flow accounting interface.

Every input here is built in memory.  The conservation tests state the
closing population and the expected identity components independently,
as hand-checked literals, rather than recomputing the module's own
formula and comparing it to itself.  The projection-engine tests drive
the real :class:`populace_dynamics.engine.loop.ProjectionEngine` with
synthetic adapters that record their own event declarations, so the
accountant is exercised against frames the engine actually produced.

No fitted model, survey extract, benefit calculation or benchmark value
is involved anywhere in this module.
"""

from __future__ import annotations

import json
import math
from dataclasses import FrozenInstanceError, dataclass, field
from inspect import signature

import numpy as np
import pandas as pd
import pytest

import populace_dynamics.engine.accounting as accounting
from populace_dynamics.engine.accounting import (
    ACCOUNTING_INTERFACE_VERSION,
    ENGINEERING_STATUS,
    AccountingDiscrepancy,
    DiscrepancyKind,
    PopulationAccountingInputError,
    PopulationEvent,
    PopulationEventKind,
    PopulationReconciliationError,
    reconcile_period,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    MaritalStepResult,
    PeriodModules,
    ProjectionEngine,
)

# ---------------------------------------------------------------------
# in-memory frame helpers
# ---------------------------------------------------------------------


def frame(year: int, rows: dict[int, float], **columns) -> pd.DataFrame:
    """Build a population frame from an ``{id: weight}`` mapping."""
    person_ids = list(rows)
    built = pd.DataFrame(
        {
            "person_id": np.asarray(person_ids, dtype=np.int64),
            "year": np.full(len(person_ids), year, dtype=np.int64),
            "weight": np.asarray(
                [rows[key] for key in person_ids], dtype=np.float64
            ),
        }
    )
    for name, values in columns.items():
        built[name] = values
    return built


def empty_frame() -> pd.DataFrame:
    """Build the naive spelling of an empty population."""
    return pd.DataFrame({"person_id": [], "year": [], "weight": []})


def death(person_id: int, year: int, **kwargs) -> PopulationEvent:
    return PopulationEvent(person_id, "death", year, **kwargs)


def birth(person_id: int, year: int, **kwargs) -> PopulationEvent:
    return PopulationEvent(person_id, "birth", year, **kwargs)


def entry(person_id: int, year: int, **kwargs) -> PopulationEvent:
    return PopulationEvent(person_id, "scheduled_entry", year, **kwargs)


def kinds(error: PopulationReconciliationError) -> list[DiscrepancyKind]:
    return [item.kind for item in error.discrepancies]


# ---------------------------------------------------------------------
# conservation, with independently specified expectations
# ---------------------------------------------------------------------


def test_hand_checked_year_reconciles_to_stated_totals():
    """A worked year whose every component is stated, not derived.

    Opening 2020 holds five people weighing 100, 200, 300, 400 and 500,
    so the opening stock is 1500.  Over the period person 5 dies, person
    3's weight rises from 300 to 350, and one child is born weighing
    100.  The closing frame is written out independently and sums to
    1150.  The identity a reader can check by hand is
    ``1500 - 500 + 100 + 50 = 1150``.
    """
    opening = frame(2020, {1: 100.0, 2: 200.0, 3: 300.0, 4: 400.0, 5: 500.0})
    closing = frame(
        2021, {1: 100.0, 2: 200.0, 3: 350.0, 4: 400.0, 1001: 100.0}
    )

    account = reconcile_period(
        opening,
        closing,
        opening_year=2020,
        closing_year=2021,
        additions=[birth(1001, 2021)],
        exits=[death(5, 2021)],
    )

    assert account.weights.opening == 1500.0
    assert account.weights.closing == 1150.0
    assert account.weights.exits_total == 500.0
    assert account.weights.additions_total == 100.0
    assert account.weights.revaluation.carried == 50.0
    assert account.weights.revaluation.total == 50.0
    assert account.reconstructed_closing_weight == 1150.0
    assert account.weight_residual == 0.0
    assert account.count_residual == 0
    assert account.counts.opening == 5
    assert account.counts.closing == 5
    assert account.counts.carried == 4
    assert account.counts.entered == 1
    assert account.counts.exited == 1
    assert account.counts.transient == 0
    assert account.carried_person_ids == (1, 2, 3, 4)
    assert account.entered_person_ids == (1001,)
    assert account.exited_person_ids == (5,)


def test_flows_split_by_declared_kind():
    """Two arrivals and two departures of different kinds stay apart.

    Opening 10 + 20 = 30.  A birth of 4 and a scheduled entry of 6
    arrive; a death of 10 and an emigration of 20 depart.  The closing
    frame holds only the two arrivals and weighs 10.
    """
    opening = frame(2030, {1: 10.0, 2: 20.0})
    closing = frame(2031, {50: 4.0, 60: 6.0})

    account = reconcile_period(
        opening,
        closing,
        opening_year=2030,
        closing_year=2031,
        additions=[birth(50, 2031), entry(60, 2031)],
        exits=[
            death(1, 2031),
            PopulationEvent(2, "emigration", 2031),
        ],
    )

    assert account.weights.closing == 10.0
    assert dict(account.weights.additions_by_kind) == {
        "birth": 4.0,
        "scheduled_entry": 6.0,
        "other_entry": 0.0,
    }
    assert dict(account.weights.exits_by_kind) == {
        "death": 10.0,
        "emigration": 20.0,
        "other_exit": 0.0,
    }
    assert dict(account.counts.additions_by_kind) == {
        "birth": 1,
        "scheduled_entry": 1,
        "other_entry": 0,
    }
    assert dict(account.counts.exits_by_kind) == {
        "death": 1,
        "emigration": 1,
        "other_exit": 0,
    }
    assert account.weight_residual == 0.0


def test_unchanged_survivors_produce_a_flat_account():
    """Nothing happens: every flow and every revaluation is zero."""
    rows = {7: 1.5, 8: 2.5, 9: 3.5}
    account = reconcile_period(
        frame(2040, rows),
        frame(2041, rows),
        opening_year=2040,
        closing_year=2041,
    )

    assert account.weights.opening == 7.5
    assert account.weights.closing == 7.5
    assert account.weights.additions_total == 0.0
    assert account.weights.exits_total == 0.0
    assert account.weights.revaluation.to_dict() == {
        "carried": 0.0,
        "entrant": 0.0,
        "exiting": 0.0,
        "transient": 0.0,
        "total": 0.0,
    }
    assert account.counts.carried == 3
    assert account.weight_residual == 0.0


def test_carried_weight_change_is_its_own_component():
    """A pure revaluation moves no person and is never a flow.

    Both people survive.  One weight rises by 3 and the other falls by
    1, so the stock moves from 30 to 32 with no arrival or departure.
    """
    account = reconcile_period(
        frame(2040, {1: 10.0, 2: 20.0}),
        frame(2041, {1: 13.0, 2: 19.0}),
        opening_year=2040,
        closing_year=2041,
    )

    assert account.weights.opening == 30.0
    assert account.weights.closing == 32.0
    assert account.weights.additions_total == 0.0
    assert account.weights.exits_total == 0.0
    assert account.weights.revaluation.carried == 2.0
    assert account.counts.additions_total == 0
    assert account.counts.exits_total == 0
    assert account.weight_residual == 0.0


def test_within_period_entry_and_exit_nets_out():
    """Someone who arrives and leaves inside the period holds no stock.

    Persons 1 and 2 carry 10 and 20 through unchanged.  Person 7
    scheduled-enters weighing 5 and emigrates the same year weighing 5.
    They appear in neither frame, yet both flows are booked and the
    closing stock is still 30.
    """
    account = reconcile_period(
        frame(2050, {1: 10.0, 2: 20.0}),
        frame(2051, {1: 10.0, 2: 20.0}),
        opening_year=2050,
        closing_year=2051,
        additions=[entry(7, 2051, weight=5.0)],
        exits=[PopulationEvent(7, "emigration", 2051, weight=5.0)],
    )

    assert account.counts.opening == 2
    assert account.counts.closing == 2
    assert account.counts.carried == 2
    assert account.counts.entered == 0
    assert account.counts.exited == 0
    assert account.counts.transient == 1
    assert account.counts.additions_total == 1
    assert account.counts.exits_total == 1
    assert account.transient_person_ids == (7,)
    assert account.added_person_ids == (7,)
    assert account.departed_person_ids == (7,)
    assert account.weights.additions_total == 5.0
    assert account.weights.exits_total == 5.0
    assert account.weights.revaluation.total == 0.0
    assert account.weights.closing == 30.0
    assert account.weight_residual == 0.0


def test_transient_weight_change_is_reported_not_absorbed():
    """A transient whose weight moved keeps the identity honest.

    Person 7 enters weighing 5 and leaves weighing 8.  The 3 is a
    transient revaluation, not a silent gap in the closing stock.
    """
    account = reconcile_period(
        frame(2050, {1: 10.0}),
        frame(2051, {1: 10.0}),
        opening_year=2050,
        closing_year=2051,
        additions=[entry(7, 2051, weight=5.0)],
        exits=[PopulationEvent(7, "emigration", 2051, weight=8.0)],
    )

    assert account.weights.additions_total == 5.0
    assert account.weights.exits_total == 8.0
    assert account.weights.revaluation.transient == 3.0
    assert account.weights.revaluation.carried == 0.0
    assert account.weights.closing == 10.0
    assert account.weight_residual == 0.0


def test_declared_exit_weight_differing_from_opening_is_a_component():
    """A departure priced away from its opening weight is visible.

    Person 2 opens at 20 but is declared to leave at 12.  The 8 lands
    in the ``exiting`` revaluation rather than vanishing.
    """
    account = reconcile_period(
        frame(2060, {1: 10.0, 2: 20.0}),
        frame(2061, {1: 10.0}),
        opening_year=2060,
        closing_year=2061,
        exits=[death(2, 2061, weight=12.0)],
    )

    assert account.weights.exits_total == 12.0
    assert account.weights.revaluation.exiting == -8.0
    assert account.weights.revaluation.carried == 0.0
    assert account.weights.closing == 10.0
    assert account.weight_residual == 0.0


def test_declared_entry_weight_differing_from_closing_is_a_component():
    """An arrival repriced after entry is visible too."""
    account = reconcile_period(
        frame(2060, {1: 10.0}),
        frame(2061, {1: 10.0, 9: 6.0}),
        opening_year=2060,
        closing_year=2061,
        additions=[entry(9, 2061, weight=4.0)],
    )

    assert account.weights.additions_total == 4.0
    assert account.weights.revaluation.entrant == 2.0
    assert account.weights.closing == 16.0
    assert account.weight_residual == 0.0


def test_complete_extinction_reconciles():
    """Everyone dies: the closing frame is empty and the stock is zero."""
    account = reconcile_period(
        frame(2070, {1: 10.0, 2: 20.0, 3: 30.0}),
        empty_frame(),
        opening_year=2070,
        closing_year=2071,
        exits=[death(person, 2071) for person in (1, 2, 3)],
    )

    assert account.counts.opening == 3
    assert account.counts.closing == 0
    assert account.counts.exited == 3
    assert account.weights.opening == 60.0
    assert account.weights.closing == 0.0
    assert account.weights.exits_total == 60.0
    assert account.weight_residual == 0.0


def test_empty_to_empty_reconciles():
    """An empty population that stays empty is a valid, flat account."""
    account = reconcile_period(
        empty_frame(),
        empty_frame(),
        opening_year=2080,
        closing_year=2081,
    )

    assert account.counts.to_dict()["opening"] == 0
    assert account.counts.closing == 0
    assert account.weights.opening == 0.0
    assert account.weights.closing == 0.0
    assert account.weights.revaluation.total == 0.0
    assert account.weight_residual == 0.0
    assert account.carried_person_ids == ()


def test_population_may_start_empty_and_be_repopulated():
    """Additions in a later period do not need an earlier stock."""
    account = reconcile_period(
        empty_frame(),
        frame(2081, {4: 2.0, 5: 3.0}),
        opening_year=2080,
        closing_year=2081,
        additions=[entry(4, 2081), entry(5, 2081)],
    )

    assert account.counts.opening == 0
    assert account.counts.entered == 2
    assert account.weights.additions_total == 5.0
    assert account.weights.closing == 5.0
    assert account.weight_residual == 0.0


def test_a_quiet_period_may_precede_one_with_additions():
    """Chaining periods: the closing frame becomes the next opening."""
    first_year = frame(2090, {1: 10.0, 2: 20.0})
    second_year = frame(2091, {1: 10.0, 2: 20.0})
    third_year = frame(2092, {1: 10.0, 2: 20.0, 30: 5.0})

    quiet = reconcile_period(
        first_year,
        second_year,
        opening_year=2090,
        closing_year=2091,
    )
    active = reconcile_period(
        second_year,
        third_year,
        opening_year=2091,
        closing_year=2092,
        additions=[entry(30, 2092)],
    )

    assert quiet.counts.additions_total == 0
    assert active.counts.additions_total == 1
    assert quiet.weights.closing == active.weights.opening == 30.0
    assert active.weights.closing == 35.0
    assert active.weight_residual == 0.0


def test_zero_weight_rows_stay_visible_as_people():
    """A zero weight is a person, not an absence.

    Three rows open, one of them weighing nothing.  The zero-weight
    person then dies.  Counts move by one; the stock does not move.
    """
    account = reconcile_period(
        frame(2100, {1: 0.0, 2: 5.0, 3: 7.0}),
        frame(2101, {2: 5.0, 3: 7.0}),
        opening_year=2100,
        closing_year=2101,
        exits=[death(1, 2101)],
    )

    assert account.counts.opening == 3
    assert account.counts.closing == 2
    assert account.counts.exited == 1
    assert account.exited_person_ids == (1,)
    assert account.provenance["opening_zero_weight_rows"] == 1
    assert account.provenance["closing_zero_weight_rows"] == 0
    assert account.weights.exits_total == 0.0
    assert account.weights.opening == 12.0
    assert account.weights.closing == 12.0
    assert account.weight_residual == 0.0


def test_a_zero_weight_arrival_is_still_an_arrival():
    """Arriving with no weight still books a person."""
    account = reconcile_period(
        frame(2100, {1: 5.0}),
        frame(2101, {1: 5.0, 2: 0.0}),
        opening_year=2100,
        closing_year=2101,
        additions=[birth(2, 2101)],
    )

    assert account.counts.entered == 1
    assert account.counts.closing == 2
    assert account.weights.additions_total == 0.0
    assert account.provenance["closing_zero_weight_rows"] == 1


# ---------------------------------------------------------------------
# stable summation and residual reporting
# ---------------------------------------------------------------------


def test_stable_summation_preserves_small_terms_in_this_example():
    """The stock is the exactly-rounded sum, which naive addition misses.

    ``1.0 + 1e16 + 1.0`` accumulated left to right loses both ones, and
    2.0 is representable at that magnitude, so the exactly-rounded
    answer is 10000000000000002.0.
    """
    weights = [1.0, 1e16, 1.0]
    naive = 0.0
    for value in weights:
        naive += value
    assert naive == 1e16

    rows = dict(zip((1, 2, 3), weights, strict=True))
    account = reconcile_period(
        frame(2110, rows),
        frame(2111, rows),
        opening_year=2110,
        closing_year=2111,
    )

    assert account.weights.opening == 10000000000000002.0
    assert account.weights.opening != naive
    assert account.weight_residual == 0.0


def test_totals_do_not_depend_on_row_order():
    """Reordering rows and declarations changes no reported number."""
    rows = {1: 0.1, 2: 0.2, 3: 0.3, 4: 1e15, 5: 0.7}
    closing_rows = {1: 0.1, 2: 0.2, 4: 1e15, 5: 0.7}
    forward = reconcile_period(
        frame(2120, rows),
        frame(2121, closing_rows),
        opening_year=2120,
        closing_year=2121,
        exits=[death(3, 2121)],
    )
    reversed_rows = dict(reversed(list(rows.items())))
    reversed_closing = dict(reversed(list(closing_rows.items())))
    backward = reconcile_period(
        frame(2120, reversed_rows),
        frame(2121, reversed_closing),
        opening_year=2120,
        closing_year=2121,
        exits=[death(3, 2121)],
    )

    assert forward.to_dict() == backward.to_dict()


def test_a_representable_residual_is_reported_and_not_gated():
    """The residual is a reported number, never a pass/fail verdict.

    Nothing in the module compares it to a tolerance, so the field is
    simply present and finite on a reconciled account.
    """
    account = reconcile_period(
        frame(2130, {1: 0.1, 2: 0.2}),
        frame(2131, {1: 0.1}),
        opening_year=2130,
        closing_year=2131,
        exits=[death(2, 2131)],
    )

    assert isinstance(account.weight_residual, float)
    assert math.isfinite(account.weight_residual)
    assert account.weight_residual != 0.0
    assert account.status == ENGINEERING_STATUS
    assert account.count_residual == 0


def test_the_module_defines_no_tolerance_or_acceptance_knob():
    """No threshold, tolerance or gate may creep into this interface."""
    banned = ("toler", "threshold", "atol", "rtol", "epsilon", "accept")
    offenders = [
        name
        for name in dir(accounting)
        if not name.startswith("_")
        and any(token in name.lower() for token in banned)
    ]
    assert offenders == []
    assert not any(
        any(token in name.lower() for token in banned)
        for name in signature(reconcile_period).parameters
    )


# ---------------------------------------------------------------------
# refusal to infer
# ---------------------------------------------------------------------


def test_a_disappearance_is_not_assumed_to_be_a_death():
    """An undeclared disappearance is refused, not booked as mortality."""
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2140, {1: 10.0, 2: 20.0}),
            frame(2141, {1: 10.0}),
            opening_year=2140,
            closing_year=2141,
        )

    assert kinds(caught.value) == [DiscrepancyKind.UNDECLARED_EXIT]
    assert caught.value.discrepancies[0].person_id == 2
    assert "will not assume the person died" in (
        caught.value.discrepancies[0].detail
    )


def test_a_new_identifier_is_not_assumed_to_be_an_immigrant():
    """A new identifier flagged synthetic is still refused.

    The closing frame marks the row ``synthetic_entry`` exactly as
    :func:`populace_dynamics.engine.steps.materialize_maternal_births`
    would.  The accountant ignores the flag: only a declaration counts.
    """
    closing = frame(2141, {1: 10.0, 999: 3.0}, synthetic_entry=[False, True])
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2140, {1: 10.0}),
            closing,
            opening_year=2140,
            closing_year=2141,
        )

    assert kinds(caught.value) == [DiscrepancyKind.UNDECLARED_ADDITION]
    assert caught.value.discrepancies[0].person_id == 999


def test_both_unexplained_directions_are_reported_together():
    """One refusal carries every finding, ordered deterministically."""
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2140, {1: 10.0, 2: 20.0}),
            frame(2141, {1: 10.0, 3: 30.0}),
            opening_year=2140,
            closing_year=2141,
        )

    assert kinds(caught.value) == [
        DiscrepancyKind.UNDECLARED_ADDITION,
        DiscrepancyKind.UNDECLARED_EXIT,
    ]
    assert [item.person_id for item in caught.value.discrepancies] == [3, 2]
    assert "undeclared_addition=1" in str(caught.value)
    assert "undeclared_exit=1" in str(caught.value)


def test_an_explicit_other_exit_is_accepted_when_the_caller_says_why():
    """The escape hatch is declaration, never inference."""
    account = reconcile_period(
        frame(2140, {1: 10.0, 2: 20.0}),
        frame(2141, {1: 10.0}),
        opening_year=2140,
        closing_year=2141,
        exits=[
            PopulationEvent(
                2,
                "other_exit",
                2141,
                reason="removed by the caller's own roster surgery",
            )
        ],
    )

    assert account.counts.exits_by_kind["other_exit"] == 1
    assert account.weights.exits_by_kind["other_exit"] == 20.0
    assert account.weight_residual == 0.0


def test_refusal_payload_is_serializable():
    """A refusal can be written down without parsing its message."""
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2140, {1: 10.0}),
            frame(2141, {2: 10.0}),
            opening_year=2140,
            closing_year=2141,
        )

    payload = json.loads(json.dumps(caught.value.to_dict()))
    assert payload["error"] == "population_reconciliation_error"
    assert payload["interface_version"] == ACCOUNTING_INTERFACE_VERSION
    assert {item["kind"] for item in payload["discrepancies"]} == {
        "undeclared_addition",
        "undeclared_exit",
    }


# ---------------------------------------------------------------------
# rejecting colliding, duplicated and impossible declarations
# ---------------------------------------------------------------------


def test_duplicate_addition_declarations_are_rejected():
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2150, {1: 10.0}),
            frame(2151, {1: 10.0, 2: 5.0}),
            opening_year=2150,
            closing_year=2151,
            additions=[birth(2, 2151), entry(2, 2151)],
        )

    assert DiscrepancyKind.DUPLICATE_ADDITION in kinds(caught.value)


def test_duplicate_exit_declarations_are_rejected():
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2150, {1: 10.0, 2: 5.0}),
            frame(2151, {1: 10.0}),
            opening_year=2150,
            closing_year=2151,
            exits=[
                death(2, 2151),
                PopulationEvent(2, "emigration", 2151),
            ],
        )

    assert DiscrepancyKind.DUPLICATE_EXIT in kinds(caught.value)


def test_an_addition_colliding_with_the_opening_roster_is_rejected():
    """Declaring an arrival for somebody already present is a collision."""
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2150, {1: 10.0, 2: 5.0}),
            frame(2151, {1: 10.0, 2: 5.0}),
            opening_year=2150,
            closing_year=2151,
            additions=[entry(2, 2151)],
        )

    assert kinds(caught.value) == [
        DiscrepancyKind.ADDITION_COLLIDES_WITH_OPENING
    ]


def test_an_exit_for_someone_never_present_is_rejected():
    """Leaving requires having been here: no exit before entry."""
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2150, {1: 10.0}),
            frame(2151, {1: 10.0}),
            opening_year=2150,
            closing_year=2151,
            exits=[death(404, 2151)],
        )

    assert kinds(caught.value) == [DiscrepancyKind.EXIT_WITHOUT_PRESENCE]
    assert caught.value.discrepancies[0].person_id == 404


def test_an_exit_contradicted_by_the_closing_frame_is_rejected():
    """Declaring a death for somebody still on the roster is refused."""
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2150, {1: 10.0, 2: 5.0}),
            frame(2151, {1: 10.0, 2: 5.0}),
            opening_year=2150,
            closing_year=2151,
            exits=[death(2, 2151)],
        )

    assert kinds(caught.value) == [
        DiscrepancyKind.EXIT_CONTRADICTED_BY_CLOSING
    ]


def test_an_arrival_that_never_lands_is_rejected():
    """A declared arrival absent at the close needs a declared exit."""
    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            frame(2150, {1: 10.0}),
            frame(2151, {1: 10.0}),
            opening_year=2150,
            closing_year=2151,
            additions=[birth(77, 2151, weight=1.0)],
        )

    assert kinds(caught.value) == [DiscrepancyKind.ADDITION_ABSENT_AT_CLOSE]
    assert caught.value.discrepancies[0].person_id == 77


def test_a_transient_without_declared_weights_is_rejected():
    """A person in neither frame must price both of their own events."""
    with pytest.raises(PopulationAccountingInputError, match="explicit"):
        reconcile_period(
            frame(2150, {1: 10.0}),
            frame(2151, {1: 10.0}),
            opening_year=2150,
            closing_year=2151,
            additions=[entry(7, 2151)],
            exits=[death(7, 2151, weight=1.0)],
        )


# ---------------------------------------------------------------------
# malformed declarations
# ---------------------------------------------------------------------


def test_an_unknown_event_kind_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="unknown"):
        PopulationEvent(1, "abduction", 2020)


def test_an_other_kind_without_a_reason_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="reason"):
        PopulationEvent(1, "other_exit", 2020)
    with pytest.raises(PopulationAccountingInputError, match="reason"):
        PopulationEvent(1, "other_entry", 2020, reason="   ")


def test_a_boolean_person_identifier_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="integer"):
        PopulationEvent(True, "death", 2020)


def test_a_float_person_identifier_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="integer"):
        PopulationEvent(1.0, "death", 2020)


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
def test_an_invalid_declared_weight_is_rejected(value):
    with pytest.raises(PopulationAccountingInputError, match="non-negative"):
        PopulationEvent(1, "death", 2020, weight=value)


def test_a_non_string_reason_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="string"):
        PopulationEvent(1, "death", 2020, reason=7)


def test_a_departure_declared_as_an_arrival_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="separately"):
        reconcile_period(
            frame(2160, {1: 10.0}),
            frame(2161, {1: 10.0}),
            opening_year=2160,
            closing_year=2161,
            additions=[death(1, 2161)],
        )


def test_an_arrival_declared_as_a_departure_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="separately"):
        reconcile_period(
            frame(2160, {1: 10.0}),
            frame(2161, {1: 10.0}),
            opening_year=2160,
            closing_year=2161,
            exits=[birth(1, 2161)],
        )


def test_an_event_booked_to_the_wrong_year_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="closing year"):
        reconcile_period(
            frame(2160, {1: 10.0, 2: 1.0}),
            frame(2161, {1: 10.0}),
            opening_year=2160,
            closing_year=2161,
            exits=[death(2, 2160)],
        )


def test_a_non_event_in_a_declaration_sequence_is_rejected():
    with pytest.raises(
        PopulationAccountingInputError, match="PopulationEvent"
    ):
        reconcile_period(
            frame(2160, {1: 10.0}),
            frame(2161, {1: 10.0}),
            opening_year=2160,
            closing_year=2161,
            exits=[{"person_id": 1, "kind": "death"}],
        )


def test_a_generator_of_declarations_is_rejected():
    """Declarations must be a re-readable sequence, not a one-shot stream."""
    with pytest.raises(PopulationAccountingInputError, match="sequence"):
        reconcile_period(
            frame(2160, {1: 10.0}),
            frame(2161, {1: 10.0}),
            opening_year=2160,
            closing_year=2161,
            exits=(event for event in ()),
        )


# ---------------------------------------------------------------------
# malformed frames and period coordinates
# ---------------------------------------------------------------------


def test_a_missing_column_is_rejected():
    opening = frame(2170, {1: 10.0}).drop(columns=["weight"])
    with pytest.raises(PopulationAccountingInputError, match="missing"):
        reconcile_period(
            opening,
            frame(2171, {1: 10.0}),
            opening_year=2170,
            closing_year=2171,
        )


def test_a_duplicate_person_row_is_rejected():
    opening = pd.DataFrame(
        {
            "person_id": [1, 1],
            "year": [2170, 2170],
            "weight": [10.0, 10.0],
        }
    )
    with pytest.raises(PopulationAccountingInputError, match="duplicate"):
        reconcile_period(
            opening,
            frame(2171, {1: 10.0}),
            opening_year=2170,
            closing_year=2171,
        )


def test_a_float_identifier_column_is_rejected():
    opening = frame(2170, {1: 10.0})
    opening["person_id"] = opening["person_id"].astype(np.float64)
    with pytest.raises(PopulationAccountingInputError, match="integer dtype"):
        reconcile_period(
            opening,
            frame(2171, {1: 10.0}),
            opening_year=2170,
            closing_year=2171,
        )


def test_a_null_identifier_is_rejected():
    opening = frame(2170, {1: 10.0})
    opening["person_id"] = pd.array([pd.NA], dtype="Int64")
    with pytest.raises(PopulationAccountingInputError, match="null"):
        reconcile_period(
            opening,
            frame(2171, {1: 10.0}),
            opening_year=2170,
            closing_year=2171,
        )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (float("nan"), "null"),
        (float("inf"), "non-finite"),
        (-0.5, "negative"),
    ],
)
def test_an_invalid_frame_weight_is_rejected(value, message):
    closing = frame(2171, {1: value})
    with pytest.raises(PopulationAccountingInputError, match=message):
        reconcile_period(
            frame(2170, {1: 10.0}),
            closing,
            opening_year=2170,
            closing_year=2171,
        )


def test_a_row_carrying_the_wrong_year_is_rejected():
    closing = frame(2171, {1: 10.0, 2: 5.0})
    closing.loc[1, "year"] = 2172
    with pytest.raises(PopulationAccountingInputError, match="must carry"):
        reconcile_period(
            frame(2170, {1: 10.0, 2: 5.0}),
            closing,
            opening_year=2170,
            closing_year=2171,
        )


def test_a_non_annual_period_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="annual"):
        reconcile_period(
            frame(2170, {1: 10.0}),
            frame(2172, {1: 10.0}),
            opening_year=2170,
            closing_year=2172,
        )


def test_a_non_frame_input_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="DataFrame"):
        reconcile_period(
            {"person_id": [1]},
            frame(2171, {1: 10.0}),
            opening_year=2170,
            closing_year=2171,
        )


def test_a_float_year_coordinate_is_rejected():
    with pytest.raises(PopulationAccountingInputError, match="integer year"):
        reconcile_period(
            frame(2170, {1: 10.0}),
            frame(2171, {1: 10.0}),
            opening_year=2170.0,
            closing_year=2171,
        )


# ---------------------------------------------------------------------
# purity, immutability and the serializable payload
# ---------------------------------------------------------------------


def test_input_frames_are_not_mutated():
    """The accountant reads; it never writes back.

    The rows are supplied deliberately out of identifier order and with
    a non-default index, so an in-place sort, a reindex or an added
    bookkeeping column would all show up here.
    """
    opening = frame(2180, {2: 20.0, 1: 10.0}, note=["b", "a"])
    closing = frame(2181, {3: 1.0, 2: 25.0}, note=["c", "b"])
    opening.index = pd.Index([11, 10], name="row")
    closing.index = pd.Index([13, 12], name="row")
    opening_before = opening.copy(deep=True)
    closing_before = closing.copy(deep=True)

    reconcile_period(
        opening,
        closing,
        opening_year=2180,
        closing_year=2181,
        additions=[birth(3, 2181)],
        exits=[death(1, 2181)],
    )

    pd.testing.assert_frame_equal(opening, opening_before)
    pd.testing.assert_frame_equal(closing, closing_before)
    assert list(opening["person_id"]) == [2, 1]
    assert list(closing["person_id"]) == [3, 2]
    assert list(opening.columns) == ["person_id", "year", "weight", "note"]
    assert list(closing.columns) == ["person_id", "year", "weight", "note"]
    assert list(opening.index) == [11, 10]
    assert list(closing.index) == [13, 12]


def test_the_account_is_immutable():
    account = reconcile_period(
        frame(2180, {1: 10.0}),
        frame(2181, {1: 10.0}),
        opening_year=2180,
        closing_year=2181,
    )

    with pytest.raises(FrozenInstanceError):
        account.weight_residual = 1.0
    with pytest.raises(TypeError):
        account.provenance["opening_rows"] = 99
    with pytest.raises(TypeError):
        account.counts.additions_by_kind["birth"] = 99


def test_the_account_payload_is_json_serializable_and_flat():
    account = reconcile_period(
        frame(2180, {1: 10.0, 2: 20.0}),
        frame(2181, {1: 10.0, 3: 4.0}),
        opening_year=2180,
        closing_year=2181,
        additions=[birth(3, 2181, source="synthetic.fertility")],
        exits=[death(2, 2181, source="synthetic.mortality")],
    )

    payload = account.to_dict()
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped == payload

    def leaves(value):
        if isinstance(value, dict):
            for item in value.values():
                yield from leaves(item)
        elif isinstance(value, list):
            for item in value:
                yield from leaves(item)
        else:
            yield value

    assert all(
        isinstance(leaf, (int, float, str, bool)) or leaf is None
        for leaf in leaves(payload)
    )
    assert payload["provenance"]["declaration_sources"] == [
        "synthetic.fertility",
        "synthetic.mortality",
    ]
    assert payload["provenance"]["inference"].startswith("none:")


def test_the_status_is_explicitly_engineering_only():
    account = reconcile_period(
        frame(2180, {1: 10.0}),
        frame(2181, {1: 10.0}),
        opening_year=2180,
        closing_year=2181,
    )

    assert account.status == ENGINEERING_STATUS
    assert account.status == "engineering-accounting-coherence-only"
    note = account.status_note.lower()
    assert "not scientific acceptance" in note
    assert "not a benchmark comparison" in note
    assert "not a gate outcome" in note


def test_a_discrepancy_record_is_serializable():
    record = AccountingDiscrepancy(
        kind=DiscrepancyKind.UNDECLARED_EXIT,
        person_id=5,
        detail="example",
    )
    assert json.loads(json.dumps(record.to_dict())) == {
        "kind": "undeclared_exit",
        "person_id": 5,
        "detail": "example",
    }


def test_an_event_record_is_serializable():
    event = birth(3, 2181, source="synthetic.fertility")
    assert json.loads(json.dumps(event.to_dict())) == {
        "person_id": 3,
        "kind": "birth",
        "year": 2181,
        "weight": None,
        "reason": "",
        "source": "synthetic.fertility",
    }
    assert event.is_addition is True
    assert death(3, 2181).is_addition is False
    assert set(PopulationEventKind) == (
        accounting.ADDITION_KINDS | accounting.EXIT_KINDS
    )


# ---------------------------------------------------------------------
# the real ProjectionEngine, driven by recording synthetic adapters
# ---------------------------------------------------------------------


@dataclass
class EventLog:
    """Declarations captured from the synthetic adapters themselves."""

    additions: list[PopulationEvent] = field(default_factory=list)
    exits: list[PopulationEvent] = field(default_factory=list)

    def for_year(self, year: int) -> tuple[list, list]:
        return (
            [item for item in self.additions if item.year == year],
            [item for item in self.exits if item.year == year],
        )


def _recording_modules(
    log: EventLog,
    deaths_by_year: dict[int, tuple[int, ...]],
    births_by_year: dict[int, tuple[int, ...]],
) -> PeriodModules:
    """Build eight adapters that record every presence change they make.

    These are deliberately trivial: no fitted component, no draw, no
    demography.  Their only job is to move people in and out of the
    roster through the engine's real seams and write down what they
    did.
    """

    def mortality(current, context, rng):
        del rng
        doomed = set(deaths_by_year.get(context.year, ()))
        leaving = current["person_id"].isin(doomed)
        for row in current.loc[leaving].to_dict("records"):
            log.exits.append(
                PopulationEvent(
                    person_id=int(row["person_id"]),
                    kind=PopulationEventKind.DEATH,
                    year=context.year,
                    weight=float(row["weight"]),
                    source="synthetic.mortality",
                )
            )
        return current.loc[~leaving].reset_index(drop=True)

    def aging(current, context, rng):
        del rng
        out = current.copy()
        out["year"] = context.year
        out["age"] = out["age"].to_numpy(dtype=np.int64) + 1
        return out

    def marital_core(current, context, rng):
        del current, context, rng
        return MaritalStepResult(
            sim_years=pd.DataFrame(), births=pd.DataFrame()
        )

    def fertility(current, context, marital, rng):
        del marital, rng
        parents = births_by_year.get(context.year, ())
        if not parents:
            return current
        weight_of = dict(
            zip(
                current["person_id"].tolist(),
                current["weight"].tolist(),
                strict=True,
            )
        )
        child_ids = context.synthetic_id_allocator.allocate(len(parents))
        children = pd.DataFrame(
            {
                "person_id": child_ids,
                "year": np.full(len(parents), context.year, dtype=np.int64),
                "age": np.zeros(len(parents), dtype=np.int64),
                "weight": np.asarray(
                    [weight_of[parent] for parent in parents],
                    dtype=np.float64,
                ),
            }
        )
        for child_id in child_ids.tolist():
            log.additions.append(
                PopulationEvent(
                    person_id=int(child_id),
                    kind=PopulationEventKind.BIRTH,
                    year=context.year,
                    source="synthetic.fertility",
                )
            )
        return pd.concat([current, children], ignore_index=True)

    def unchanged(current, context, rng):
        del context, rng
        return current

    def unchanged_reader(current, context, marital, rng):
        del context, marital, rng
        return current

    return PeriodModules(
        mortality=mortality,
        aging=aging,
        marital_core=marital_core,
        fertility=fertility,
        disability=unchanged,
        earnings=unchanged,
        claiming=unchanged,
        household_composition=unchanged_reader,
    )


def _run_projection() -> tuple[object, EventLog]:
    """Project 2020-2023 with a birth, a death and a transient entrant.

    The 2022 scheduled entrant is registered on the metadata seam the
    loop reads, joins the roster before mortality, and dies in the same
    wave -- so they appear in no projected slice at all.
    """
    log = EventLog()
    initial = frame(2020, {1: 10.0, 2: 20.0, 3: 30.0}, age=[40, 41, 42])
    entrants_2022 = frame(2021, {100: 7.0}, age=[50])
    schedule = {2022: entrants_2022}
    for year, entrant_frame in schedule.items():
        for row in entrant_frame.to_dict("records"):
            log.additions.append(
                PopulationEvent(
                    person_id=int(row["person_id"]),
                    kind=PopulationEventKind.SCHEDULED_ENTRY,
                    year=year,
                    weight=float(row["weight"]),
                    source="loop.m6_scheduled_entries_by_year",
                )
            )
    engine = ProjectionEngine(
        _recording_modules(
            log,
            deaths_by_year={2021: (3,), 2022: (100,)},
            births_by_year={2021: (1,)},
        )
    )
    result = engine.project(
        initial,
        end_year=2023,
        draw_index=0,
        metadata={SCHEDULED_ENTRIES_KEY: schedule},
    )
    return result, log


def test_projection_slices_reconcile_year_by_year():
    """Every wave of a real projection balances against its records.

    The projection is small enough to state outright: 2021 loses person
    3 (weight 30) and gains one child carrying the mother's weight 10,
    so the stock goes 60 -> 40.  2022 admits and then buries person 100
    (weight 7), leaving the stock at 40.  2023 does nothing.
    """
    result, log = _run_projection()
    assert [int(slice_.iloc[0]["year"]) for slice_ in result.slices] == [
        2020,
        2021,
        2022,
        2023,
    ]

    accounts = []
    for index in range(len(result.slices) - 1):
        opening_year = 2020 + index
        additions, exits = log.for_year(opening_year + 1)
        accounts.append(
            reconcile_period(
                result.slices[index],
                result.slices[index + 1],
                opening_year=opening_year,
                closing_year=opening_year + 1,
                additions=additions,
                exits=exits,
            )
        )

    first, second, third = accounts

    assert first.counts.opening == 3
    assert first.counts.closing == 3
    assert first.counts.entered == 1
    assert first.counts.exited == 1
    assert first.counts.transient == 0
    assert first.counts.additions_by_kind["birth"] == 1
    assert first.counts.exits_by_kind["death"] == 1
    assert first.weights.opening == 60.0
    assert first.weights.closing == 40.0
    assert first.weights.additions_total == 10.0
    assert first.weights.exits_total == 30.0
    assert first.weights.revaluation.total == 0.0
    assert first.exited_person_ids == (3,)

    assert second.counts.opening == 3
    assert second.counts.closing == 3
    assert second.counts.carried == 3
    assert second.counts.transient == 1
    assert second.transient_person_ids == (100,)
    assert second.counts.additions_by_kind["scheduled_entry"] == 1
    assert second.counts.exits_by_kind["death"] == 1
    assert second.weights.opening == 40.0
    assert second.weights.closing == 40.0
    assert second.weights.additions_total == 7.0
    assert second.weights.exits_total == 7.0
    assert second.weights.revaluation.total == 0.0

    assert third.counts.carried == 3
    assert third.counts.additions_total == 0
    assert third.counts.exits_total == 0
    assert third.weights.closing == 40.0

    assert [account.count_residual for account in accounts] == [0, 0, 0]
    assert [account.weight_residual for account in accounts] == [
        0.0,
        0.0,
        0.0,
    ]
    assert {account.status for account in accounts} == {ENGINEERING_STATUS}


def test_the_transient_entrant_never_appears_in_a_projected_slice():
    """The within-period arrival is invisible to the frames alone.

    Only the captured declarations show that person 100 was ever in the
    population. Endpoint frames cannot expose omission of both events;
    the accountant does not verify event-log completeness.
    """
    result, log = _run_projection()
    for slice_ in result.slices:
        assert 100 not in set(slice_["person_id"].tolist())
    assert [item.person_id for item in log.additions if item.year == 2022] == [
        100
    ]
    assert [item.person_id for item in log.exits if item.year == 2022] == [100]


def test_dropping_one_captured_death_makes_the_projection_refuse():
    """Omitting a real event is caught against real engine output."""
    result, log = _run_projection()
    additions, exits = log.for_year(2021)
    withheld = [item for item in exits if item.person_id != 3]
    assert len(withheld) == len(exits) - 1

    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            result.slices[0],
            result.slices[1],
            opening_year=2020,
            closing_year=2021,
            additions=additions,
            exits=withheld,
        )

    assert kinds(caught.value) == [DiscrepancyKind.UNDECLARED_EXIT]
    assert caught.value.discrepancies[0].person_id == 3


def test_dropping_one_captured_birth_makes_the_projection_refuse():
    """A synthetic identifier is never quietly accepted as a birth."""
    result, log = _run_projection()
    _, exits = log.for_year(2021)

    with pytest.raises(PopulationReconciliationError) as caught:
        reconcile_period(
            result.slices[0],
            result.slices[1],
            opening_year=2020,
            closing_year=2021,
            additions=[],
            exits=exits,
        )

    assert kinds(caught.value) == [DiscrepancyKind.UNDECLARED_ADDITION]


# Root regression cases to append after builder releases source ownership.


@pytest.mark.parametrize("column", ["person_id", "year"])
@pytest.mark.parametrize(
    "dtype,value",
    [(np.uint64, 2**64 - 1), (object, 2**63), (object, -(2**63) - 1)],
)
def test_frame_integer_domain_cannot_wrap(column, dtype, value):
    opening = frame(2020, {1: 1.0})
    opening[column] = pd.Series([value], dtype=dtype)
    with pytest.raises(PopulationAccountingInputError):
        reconcile_period(
            opening,
            frame(2021, {-1: 1.0}),
            opening_year=2020,
            closing_year=2021,
        )


@pytest.mark.parametrize("field_name", ["person_id", "year"])
@pytest.mark.parametrize("value", [2**63, -(2**63) - 1, np.uint64(2**64 - 1)])
def test_event_integer_domain_matches_frames(field_name, value):
    kwargs = {"person_id": 1, "kind": "death", "year": 2021}
    kwargs[field_name] = value
    with pytest.raises(PopulationAccountingInputError):
        PopulationEvent(**kwargs)


@pytest.mark.parametrize(
    "value,dtype",
    [
        ("2.0", None),
        (2 + 3j, None),
        (True, object),
        (np.bool_(True), object),
        (1 + 0j, object),
        (10**400, object),
    ],
)
def test_frame_weights_refuse_lossy_or_non_numeric_values(value, dtype):
    opening = frame(2020, {1: 1.0})
    opening["weight"] = pd.Series([value], dtype=dtype)
    with pytest.raises(PopulationAccountingInputError):
        reconcile_period(
            opening,
            frame(2021, {1: 1.0}),
            opening_year=2020,
            closing_year=2021,
        )


def test_unrepresentable_weight_total_has_typed_refusal():
    with pytest.raises(
        PopulationAccountingInputError, match="represent|overflow|finite"
    ):
        reconcile_period(
            frame(2020, {1: 1e308, 2: 1e308}),
            frame(2021, {1: 1e308, 2: 1e308}),
            opening_year=2020,
            closing_year=2021,
        )


def test_unrepresentable_event_weight_has_typed_refusal():
    with pytest.raises(PopulationAccountingInputError):
        PopulationEvent(1, "death", 2021, weight=10**400)


def test_serialized_provenance_cannot_mutate_original_or_other_payload():
    account = reconcile_period(
        empty_frame(),
        frame(2021, {1: 1.0}),
        opening_year=2020,
        closing_year=2021,
        additions=[birth(1, 2021, source="synthetic.birth")],
    )
    first, second = account.to_dict(), account.to_dict()
    first["provenance"]["declaration_sources"].append("invented")
    assert second["provenance"]["declaration_sources"] == ["synthetic.birth"]
    assert account.to_dict()["provenance"]["declaration_sources"] == [
        "synthetic.birth"
    ]
    assert account.provenance["declaration_sources"] == ("synthetic.birth",)


def test_omitting_both_transient_events_is_not_observable_at_endpoints():
    result, log = _run_projection()
    additions, exits = log.for_year(2022)
    assert additions and exits
    account = reconcile_period(
        result.slices[1],
        result.slices[2],
        opening_year=2021,
        closing_year=2022,
    )
    assert account.counts.transient == 0
    assert account.count_residual == 0
    assert account.provenance["event_log_completeness_verified"] is False


@pytest.mark.parametrize("person_id", [-(2**63), 2**63 - 1])
def test_signed_int64_boundary_ids_remain_exact(person_id):
    account = reconcile_period(
        frame(2020, {person_id: 1.0}),
        empty_frame(),
        opening_year=2020,
        closing_year=2021,
        exits=[death(person_id, 2021)],
    )
    assert account.exited_person_ids == (person_id,)
    assert account.weights.exits_total == 1.0


def test_nullable_integer_columns_and_real_object_weights_are_supported():
    opening = pd.DataFrame(
        {
            "person_id": pd.Series([1], dtype="Int64"),
            "year": pd.Series([2020], dtype="Int64"),
            "weight": pd.Series([np.float64(2.5)], dtype=object),
        }
    )
    account = reconcile_period(
        opening,
        frame(2021, {1: 2.5}),
        opening_year=2020,
        closing_year=2021,
    )
    assert account.carried_person_ids == (1,)
    assert account.weights.opening == 2.5


@pytest.mark.skipif(
    np.finfo(np.longdouble).minexp >= np.finfo(np.float64).minexp,
    reason="platform longdouble has no wider exponent range than binary64",
)
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("via", ["frame", "event"])
def test_extended_weight_cannot_lose_sign_or_mass_on_conversion(sign, via):
    weight = sign * np.nextafter(np.longdouble(0), np.longdouble(1))
    assert weight != 0
    assert float(weight) == 0.0
    with pytest.raises(PopulationAccountingInputError):
        if via == "event":
            death(1, 2021, weight=weight)
        else:
            opening = frame(2020, {1: 1.0})
            opening["weight"] = np.array([weight], dtype=np.longdouble)
            reconcile_period(
                opening,
                frame(2021, {1: 0.0}),
                opening_year=2020,
                closing_year=2021,
            )
