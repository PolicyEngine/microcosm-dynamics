"""Synthetic supplied-history accounting; no data or fitted models."""

import json
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.engine import accounting
from populace_dynamics.engine.accounting_history import (
    SINGLE_PRESENCE_EPISODE,
    AnnualTransition,
    HistoryAccountingError,
    HistoryErrorKind,
    reconcile_history,
)


def _frame(year, rows=()):
    return pd.DataFrame(
        {
            "person_id": [person_id for person_id, _ in rows],
            "year": [year] * len(rows),
            "weight": [weight for _, weight in rows],
        }
    )


def _steady(year, rows=((1, 1.0),)):
    return AnnualTransition(
        year, year + 1, _frame(year, rows), _frame(year + 1, rows)
    )


def _event(person_id, kind, year, weight=None):
    return accounting.PopulationEvent(
        person_id,
        kind,
        year,
        weight=weight,
        reason="supplied synthetic event",
        source="synthetic fixture",
    )


def _reconcile(transitions):
    return reconcile_history(
        transitions, identity_contract=SINGLE_PRESENCE_EPISODE
    )


def _history():
    first = AnnualTransition(
        2020,
        2021,
        _frame(2020, [(1, 0), (2, 2), (3, 3)]),
        _frame(2021, [(1, 1), (2, 2), (4, 4)]),
        additions=[
            _event(4, "birth", 2021, 5),
            _event(8, "scheduled_entry", 2021, 2),
        ],
        exits=[
            _event(3, "death", 2021),
            _event(8, "other_exit", 2021, 1),
        ],
    )
    second = AnnualTransition(
        2021,
        2022,
        _frame(2021, [(4, 4), (2, 2), (1, 1)]),
        _frame(2022, [(2, 2), (4, 4)]),
        additions=[_event(9, "other_entry", 2022, 3)],
        exits=[
            _event(1, "emigration", 2022),
            _event(9, "death", 2022, 3),
        ],
    )
    return [first, second, _steady(2022, [(4, 4), (2, 2)])]


def test_accounts_are_unchanged_annual_results_in_supplied_order(monkeypatch):
    transitions = _history()
    expected = tuple(
        accounting.reconcile_period(
            item.opening,
            item.closing,
            opening_year=item.opening_year,
            closing_year=item.closing_year,
            additions=item.additions,
            exits=item.exits,
        )
        for item in transitions
    )
    calls = []
    original = accounting.reconcile_period

    def record(*args, **kwargs):
        calls.append(kwargs["closing_year"])
        return original(*args, **kwargs)

    monkeypatch.setattr(accounting, "reconcile_period", record)
    result = _reconcile(transitions)
    assert calls == [2021, 2022, 2023]
    assert result.periods == expected
    assert result.seen_person_ids == (1, 2, 3, 4, 8, 9)
    assert result.retired_person_ids == (1, 3, 8, 9)
    assert result.periods[0].counts.transient == 1
    assert result.periods[0].weights.revaluation.transient == -1.0
    assert result.provenance["event_log_completeness_verified"] is False
    assert result.provenance["event_truth_verified"] is False


def test_contract_keyword_is_required():
    with pytest.raises(TypeError, match="identity_contract"):
        reconcile_history([_steady(2020)])


@pytest.mark.parametrize("contract", [None, "", "general_reentry", True, []])
def test_unsupported_identity_contract_is_a_typed_refusal(contract):
    with pytest.raises(HistoryAccountingError) as caught:
        reconcile_history([_steady(2020)], identity_contract=contract)
    assert caught.value.kind is HistoryErrorKind.INPUT
    assert caught.value.period_index is None
    json.dumps(caught.value.to_dict(), allow_nan=False)


@pytest.mark.parametrize("transitions", [[], (), None, "history", iter(())])
def test_nonempty_sequence_is_required(transitions):
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile(transitions)
    assert caught.value.kind is HistoryErrorKind.INPUT


@pytest.mark.parametrize("second_year", [2019, 2020, 2022])
def test_reversal_duplicate_and_gap_are_rejected(second_year):
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([_steady(2020), _steady(second_year)])
    assert caught.value.kind is HistoryErrorKind.NONCONTIGUOUS
    assert caught.value.period_index == 1
    assert caught.value.opening_year == second_year
    assert caught.value.closing_year == second_year + 1


def test_nonannual_period_preserves_accountant_input_error():
    transition = AnnualTransition(2020, 2022, _frame(2020), _frame(2022))
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([transition])
    error = caught.value
    assert error.kind is HistoryErrorKind.PERIOD
    assert error.period_index == 0
    assert (error.opening_year, error.closing_year) == (2020, 2022)
    assert isinstance(
        error.__cause__, accounting.PopulationAccountingInputError
    )
    assert "annual" in str(error.__cause__)


def test_invalid_descriptor_preserves_period_index_and_cause():
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([_steady(2020), object()])
    error = caught.value
    assert error.period_index == 1
    assert error.opening_year is None
    assert error.closing_year is None
    assert isinstance(
        error.__cause__, accounting.PopulationAccountingInputError
    )


def test_annual_discrepancies_remain_available_on_original_cause():
    broken = AnnualTransition(2021, 2022, _frame(2021, [(1, 1)]), _frame(2022))
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([_steady(2020), broken])
    error = caught.value
    assert error.kind is HistoryErrorKind.PERIOD
    assert error.period_index == 1
    assert (error.opening_year, error.closing_year) == (2021, 2022)
    assert isinstance(
        error.__cause__, accounting.PopulationReconciliationError
    )
    assert (
        error.__cause__.discrepancies[0].kind
        is accounting.DiscrepancyKind.UNDECLARED_EXIT
    )
    payload = error.to_dict()
    assert payload["cause"]["type"] == "PopulationReconciliationError"
    assert (
        payload["cause"]["details"]["discrepancies"][0]["kind"]
        == "undeclared_exit"
    )
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    payload["person_ids"].append(999)
    payload["cause"]["details"]["discrepancies"].clear()
    assert error.to_dict()["person_ids"] == []
    assert len(error.to_dict()["cause"]["details"]["discrepancies"]) == 1


def test_boundary_person_sets_must_match_even_at_equal_counts_and_mass():
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([_steady(2020), _steady(2021, [(2, 1)])])
    assert caught.value.kind is HistoryErrorKind.BOUNDARY_PERSON_IDS
    assert caught.value.person_ids == (1, 2)
    assert caught.value.period_index == 1


def test_boundary_weights_are_compared_per_person_not_in_aggregate():
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile(
            [_steady(2020, [(1, 2), (2, 3)]), _steady(2021, [(1, 3), (2, 2)])]
        )
    assert caught.value.kind is HistoryErrorKind.BOUNDARY_WEIGHTS
    assert caught.value.person_ids == (1, 2)


def test_boundary_weight_comparison_has_no_tolerance():
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile(
            [_steady(2020), _steady(2021, [(1, np.nextafter(1.0, 2.0))])]
        )
    assert caught.value.kind is HistoryErrorKind.BOUNDARY_WEIGHTS


def test_boundary_comparison_uses_accountant_binary64_domain():
    first = _steady(2020, [(1, 2**53 + 1)])
    second = _steady(2021, [(1, float(2**53))])
    result = _reconcile([first, second])
    assert (
        result.periods[0].weights.closing == result.periods[1].weights.opening
    )


def test_boundary_order_and_opaque_columns_do_not_imply_other_continuity():
    first = _steady(2020, [(1, 0), (2, 3)])
    second = _steady(2021, [(2, 3), (1, 0)])
    first.closing["opaque"] = ["earlier", "earlier"]
    second.opening["opaque"] = ["later", "later"]
    before = [
        frame.copy(deep=True) for frame in (first.closing, second.opening)
    ]
    result = _reconcile([first, second])
    assert result.periods[0].counts.closing == 2
    assert result.provenance["other_column_continuity_verified"] is False
    for frame, original in zip(
        (first.closing, second.opening), before, strict=True
    ):
        pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("exit_kind", ["death", "emigration", "other_exit"])
@pytest.mark.parametrize("return_is_transient", [False, True])
def test_departed_id_return_is_unsupported_under_selected_contract(
    exit_kind, return_is_transient
):
    departure = AnnualTransition(
        2020,
        2021,
        _frame(2020, [(1, 1)]),
        _frame(2021),
        exits=[_event(1, exit_kind, 2021)],
    )
    returning = AnnualTransition(
        2022,
        2023,
        _frame(2022),
        _frame(2023, [] if return_is_transient else [(1, 1)]),
        additions=[_event(1, "scheduled_entry", 2023, 1)],
        exits=[_event(1, "death", 2023, 1)] if return_is_transient else (),
    )
    with pytest.raises(
        HistoryAccountingError, match="same-person return"
    ) as caught:
        _reconcile([departure, _steady(2021, []), returning])
    assert caught.value.kind is HistoryErrorKind.RETIRED_PERSON_ID
    assert caught.value.period_index == 2
    assert caught.value.person_ids == (1,)


def test_transient_id_is_seen_and_retired_before_any_endpoint_presence():
    first = AnnualTransition(
        2020,
        2021,
        _frame(2020),
        _frame(2021),
        additions=[_event(10, "other_entry", 2021, 0)],
        exits=[_event(10, "other_exit", 2021, 0)],
    )
    result = _reconcile([first])
    assert result.seen_person_ids == result.retired_person_ids == (10,)
    second = AnnualTransition(
        2021,
        2022,
        _frame(2021),
        _frame(2022, [(10, 0)]),
        additions=[_event(10, "birth", 2022)],
    )
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([first, second])
    assert caught.value.kind is HistoryErrorKind.RETIRED_PERSON_ID


def test_extinction_empty_years_and_fresh_ids_remain_supported():
    first = AnnualTransition(
        2020,
        2021,
        _frame(2020, [(1, 0)]),
        _frame(2021),
        exits=[_event(1, "death", 2021)],
    )
    third = AnnualTransition(
        2022,
        2023,
        _frame(2022),
        _frame(2023, [(2, 0)]),
        additions=[_event(2, "scheduled_entry", 2023)],
    )
    result = _reconcile([first, _steady(2021, []), third])
    assert (
        result.periods[1].counts.opening
        == result.periods[1].counts.closing
        == 0
    )
    assert result.seen_person_ids == (1, 2)
    assert result.retired_person_ids == (1,)


def test_omitting_both_transient_declarations_remains_undetectable():
    result = _reconcile([_steady(2020, []), _steady(2021, [])])
    assert result.seen_person_ids == result.retired_person_ids == ()
    assert result.provenance["event_log_completeness_verified"] is False
    assert all(period.counts.transient == 0 for period in result.periods)


def test_first_opening_has_no_inferred_prehistory():
    result = _reconcile([_steady(2020, [(100, 1)])])
    assert result.seen_person_ids == (100,)
    assert result.retired_person_ids == ()
    assert "no prehistory" in result.provenance["scope"]


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("person_id", True),
        ("person_id", "1"),
        ("person_id", 2**64 - 1),
        ("year", 2021.0),
        ("weight", True),
        ("weight", "1.0"),
        ("weight", float("inf")),
    ],
)
def test_malformed_boundary_values_are_not_coerced_before_validation(
    column, value
):
    second = _steady(2021)
    second.opening[column] = pd.Series([value], dtype=object)
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([_steady(2020), second])
    assert caught.value.kind is HistoryErrorKind.PERIOD
    assert caught.value.period_index == 1
    assert isinstance(
        caught.value.__cause__, accounting.PopulationAccountingInputError
    )
    json.dumps(caught.value.to_dict(), allow_nan=False)


@pytest.mark.parametrize("year", [True, "2020", 2020.0, 2**64 - 1])
def test_malformed_period_years_are_wrapped_without_unsafe_coordinates(year):
    transition = AnnualTransition(year, 2021, _frame(2020), _frame(2021))
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([transition])
    assert caught.value.opening_year is None
    assert caught.value.closing_year is None
    json.dumps(caught.value.to_dict(), allow_nan=False)


def test_ids_at_signed_int64_limits_remain_exact():
    rows = [(np.int64(-(2**63)), 0), (np.int64(2**63 - 1), 1)]
    result = _reconcile([_steady(2020, rows), _steady(2021, rows[::-1])])
    assert result.seen_person_ids == (-(2**63), 2**63 - 1)
    assert "seen_person_ids" not in result.to_dict()


def test_result_and_serialization_are_isolated_from_caller_mutation():
    transitions = _history()
    result = _reconcile(transitions)
    expected = result.to_dict()
    for transition in transitions:
        transition.opening["weight"] = 999
        transition.closing["person_id"] = 999
    transitions[0].additions.clear()
    transitions.clear()
    assert result.to_dict() == expected
    with pytest.raises(FrozenInstanceError):
        result.identity_contract = "changed"
    with pytest.raises(FrozenInstanceError):
        result.periods[0].opening_year = 1999
    with pytest.raises(TypeError):
        result.provenance["scope"] = "changed"
    with pytest.raises(TypeError):
        result.periods[0].counts.additions_by_kind["birth"] = 100
    payload = result.to_dict()
    payload["provenance"]["scope"] = "changed"
    payload["periods"][0]["provenance"]["declaration_sources"].append(
        "changed"
    )
    payload["periods"][0]["counts"]["opening"] = 999
    assert result.to_dict() == expected
    json.dumps(result.to_dict(), allow_nan=False)


def test_descriptor_freezes_fields_but_does_not_own_input_frames():
    transition = _steady(2020)
    with pytest.raises(FrozenInstanceError):
        transition.opening_year = 2000
    transition.opening.loc[0, "weight"] = 2
    assert transition.opening.loc[0, "weight"] == 2


@pytest.mark.parametrize("events", ["events", iter(()), [object()]])
def test_malformed_declaration_containers_stay_accountant_errors(events):
    transition = AnnualTransition(
        2020, 2021, _frame(2020), _frame(2021), additions=events
    )
    with pytest.raises(HistoryAccountingError) as caught:
        _reconcile([transition])
    assert caught.value.kind is HistoryErrorKind.PERIOD
    assert isinstance(
        caught.value.__cause__, accounting.PopulationAccountingInputError
    )
