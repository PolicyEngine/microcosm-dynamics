"""Check OP1 stock-flow, coupling, prefixes and reproducibility on inventions.

Cover ``docs/design/open_population.md`` §§2.9, 3.1 (OP1), 5.4 and 7,
approved in ruling d1925. Use the sealed adapters at ``engine/steps.py:113–166``
and ``baselines/fertility.py:163–181`` without supplying any observed data.
"""

from __future__ import annotations

import math
import subprocess
from dataclasses import replace
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.baselines.fertility import AsfrFertilityStep
from populace_dynamics.engine.accounting import PopulationEventKind
from populace_dynamics.engine.entrant_schedule import (
    validate_projection_allocator,
)
from populace_dynamics.engine.loop import (
    PeriodContext,
    PeriodModules,
    ProjectionEngine,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.rng import ProjectionRNGRegistry
from populace_dynamics.engine.steps import advance_age, apply_mortality
from populace_dynamics.open_population.errors import (
    AccountingIdentityError,
    IdOrStreamCollision,
)
from populace_dynamics.open_population.exits import no_marital_transitions
from populace_dynamics.open_population.harness import (
    ProductionRequest,
    run_production,
)

ROOT = Path(__file__).resolve().parents[2]
START = 2025


def _roster(weights=(1.0, 1.5, 2.0)):
    size = len(weights)
    return pd.DataFrame(
        {
            "person_id": np.arange(1, size + 1, dtype=np.int64),
            "year": START,
            "age": 25,
            "sex": np.where(np.arange(size) % 2, "male", "female"),
            "birth_year": START - 25,
            "weight": np.asarray(weights, dtype=float),
            "start_weight": np.asarray(weights, dtype=float),
        }
    )


def _scheduled(years):
    frames = {}
    for offset, year in enumerate(years):
        frame = _roster((0.7, 1.3))
        frame["person_id"] = 1001 + offset * 2 + np.arange(2)
        frame["year"] = year - 1
        frame["birth_year"] = year - 26
        frames[year] = frame
    return frames


def _unchanged(frame, context, rng):
    return frame


def _composition(frame, context, marital, rng):
    return frame


class _ConstantMortality:
    def __init__(self, probability):
        self.probability = probability

    def probabilities(self, frame):
        return np.full(len(frame), self.probability)


def _modules(death_probability=0.15, birth_probability=0.5):
    return PeriodModules(
        mortality=partial(
            apply_mortality, model=_ConstantMortality(death_probability)
        ),
        aging=advance_age,
        marital_core=no_marital_transitions,
        fertility=AsfrFertilityStep(
            asfr=lambda year: {age: birth_probability for age in range(18, 45)}
        ),
        disability=_unchanged,
        earnings=_unchanged,
        claiming=_unchanged,
        household_composition=_composition,
    )


def _hazard(probability):
    return lambda frame, context: np.full(len(frame), probability)


def _canonical(frame):
    return frame.sort_values("person_id").reset_index(drop=True)


@settings(max_examples=8, deadline=None)
@given(
    weights=st.lists(
        st.integers(min_value=0, max_value=100).map(lambda x: x / 10),
        min_size=1,
        max_size=6,
    ),
    death_probability=st.sampled_from([0.0, 0.25, 1.0]),
    emigration_probability=st.sampled_from([0.0, 0.35, 1.0]),
    birth_probability=st.sampled_from([0.0, 0.5, 1.0]),
    draw=st.integers(min_value=0, max_value=8),
)
def test_stock_flow_and_identity_history(
    weights,
    death_probability,
    emigration_probability,
    birth_probability,
    draw,
):
    initial = _roster(weights)
    captured_metadata = []
    modules = _modules(death_probability, birth_probability)
    actual_mortality = modules.mortality

    def capture(frame, context, rng):
        captured_metadata.append(context.metadata)
        return actual_mortality(frame, context, rng)

    modules = replace(modules, mortality=capture)
    result = run_production(
        initial,
        modules,
        ProductionRequest(2028, 2028, draw_index=draw),
        scheduled_entries=_scheduled(range(2026, 2029)),
        emigration_hazard=_hazard(emigration_probability),
    )
    assert len(result.accounting.periods) == 3
    seen = set(initial["person_id"])
    exited = set()
    for index, account in enumerate(result.accounting.periods):
        year = START + index + 1
        events = [event for event in result.events if event.year == year]
        additions = [event for event in events if event.entry_kind]
        exits = [event for event in events if not event.entry_kind]
        deaths = [event for event in exits if event.kind == "death"]
        emigrants = [event for event in exits if event.kind == "emigration"]
        assert len(result.projection.slices[index + 1]) == (
            len(result.projection.slices[index])
            - len(deaths)
            - len(emigrants)
            + len(additions)
        )
        assert len(exits) == len(deaths) + len(emigrants)
        assert account.count_residual == 0
        expected_weight = math.fsum(
            [
                account.weights.opening,
                account.weights.additions_total,
                -account.weights.exits_total,
            ]
        )
        assert account.weights.revaluation.total == 0
        assert (
            math.fsum([account.weights.closing, -expected_weight])
            == account.weight_residual
        )
        assert {event.entry_kind for event in additions} <= {
            "maternal_birth",
            "immigrant_cohort",
        }
        added_ids = [event.person_id for event in additions]
        exit_ids = [event.person_id for event in exits]
        assert len(added_ids) == len(set(added_ids))
        assert len(exit_ids) == len(set(exit_ids))
        assert not seen.intersection(added_ids)
        assert not exited.intersection(exit_ids)
        seen.update(added_ids)
        exited.update(exit_ids)
    assert set(result.accounting.seen_person_ids) == seen
    assert set(result.accounting.retired_person_ids) == exited
    assert all(item is captured_metadata[0] for item in captured_metadata)
    validate_projection_allocator(initial["person_id"], captured_metadata[0])


def test_records_all_four_flow_kinds_including_same_year_transients():
    initial = _roster()
    initial["sex"] = ["male", "male", "female"]

    def mortality(frame, context, rng):
        return frame.loc[~frame["person_id"].isin([1, 1001])].copy()

    def emigration(frame, context):
        return frame["person_id"].isin([2, 1002]).astype(float).to_numpy()

    result = run_production(
        initial,
        replace(_modules(birth_probability=1), mortality=mortality),
        ProductionRequest(2026, 2026),
        scheduled_entries=_scheduled([2026]),
        emigration_hazard=emigration,
    )
    assert {event.kind for event in result.events} == {
        PopulationEventKind.BIRTH,
        PopulationEventKind.SCHEDULED_ENTRY,
        PopulationEventKind.DEATH,
        PopulationEventKind.EMIGRATION,
    }
    period = result.accounting.periods[0]
    assert period.transient_person_ids == (1001, 1002)
    assert period.counts.additions_total == 3
    assert period.counts.exits_total == 4
    assert period.counts.closing == 2
    assert all(event.year == 2026 for event in result.events)


@settings(max_examples=6, deadline=None)
@given(draw=st.integers(min_value=0, max_value=12))
def test_disabled_emigration_matches_closed_engine_slice_by_slice(draw):
    initial = _roster((0.1, 0.7, 1.3, 2.0))
    modules = _modules()
    closed = ProjectionEngine(modules).project(
        initial, end_year=2028, draw_index=draw
    )
    result = run_production(
        initial,
        modules,
        ProductionRequest(2028, 2028, draw_index=draw),
    )
    for expected, actual in zip(
        closed.slices, result.projection.slices, strict=True
    ):
        columns = list(expected.columns)
        pd.testing.assert_frame_equal(expected, actual[columns])
    assert not any(event.kind == "emigration" for event in result.events)


@pytest.mark.parametrize("person_ids", [(-2, -1), (0, 1), (7, 8)])
def test_disabled_emigration_matches_closed_run_for_signed_ids(person_ids):
    initial = _roster((1.0, 1.0))
    initial["person_id"] = person_ids
    initial["sex"] = "female"
    modules = _modules(death_probability=0, birth_probability=1)
    closed = ProjectionEngine(modules).project(
        initial, end_year=2026, draw_index=0
    )
    actual = run_production(initial, modules, ProductionRequest(2026, 2026))
    for expected, observed in zip(
        closed.slices, actual.projection.slices, strict=True
    ):
        pd.testing.assert_frame_equal(expected, observed[expected.columns])


@settings(max_examples=6, deadline=None)
@given(
    shorter=st.integers(min_value=2025, max_value=2028),
    longer=st.integers(min_value=2025, max_value=2028),
)
def test_prefix_reads_keep_identical_shared_slices(shorter, longer):
    result = run_production(
        _roster(),
        _modules(death_probability=0, birth_probability=1),
        ProductionRequest(2028, 2028),
        scheduled_entries=_scheduled(range(2026, 2029)),
    )
    first = result.read_prefix(shorter)
    second = result.read_prefix(longer)
    assert len(first.slices) == shorter - START + 1
    assert len(first.traces) == shorter - START
    for a, b in zip(first.slices, second.slices, strict=False):
        pd.testing.assert_frame_equal(a, b)
    first.slices[0].loc[0, "weight"] = 999
    assert result.projection.slices[0].loc[0, "weight"] != 999


@settings(max_examples=8, deadline=None)
@given(
    end=st.integers(min_value=2025, max_value=2030).filter(
        lambda year: year != 2028
    )
)
def test_production_refuses_an_unregistered_end_year(end):
    with pytest.raises(IdOrStreamCollision, match="ID_OR_STREAM_COLLISION"):
        ProductionRequest(registered_horizon=2028, end_year=end)


def test_committed_evidence_reproduces_unsafe_independent_horizons():
    source = subprocess.run(
        [
            "git",
            "show",
            "5c82dbd9:docs/design/open_population_evidence/"
            "horizon_dependence.py",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    namespace = {"__name__": "op1_horizon_evidence"}
    exec(compile(source, "committed_horizon_dependence.py", "exec"), namespace)
    project = namespace["project"]
    closed_short = project(2026, with_entrants=False)
    closed_long = project(2027, with_entrants=False)
    pd.testing.assert_frame_equal(
        closed_short.slices[1], closed_long.slices[1]
    )
    open_short = project(2026, with_entrants=True)
    open_long = project(2027, with_entrants=True)
    assert not open_short.slices[1][["person_id", "age"]].equals(
        open_long.slices[1][["person_id", "age"]]
    )


@settings(max_examples=6, deadline=None)
@given(
    draw=st.integers(min_value=0, max_value=8),
    permutation=st.permutations((0, 1, 2, 3)),
)
def test_determinism_and_order_with_canonical_mortality(draw, permutation):
    initial = _roster((0.1, 0.7, 1.3, 2.0))
    modules = _modules()
    request = ProductionRequest(2027, 2027, draw_index=draw)

    def run(frame):
        return run_production(
            frame, modules, request, emigration_hazard=_hazard(0.2)
        )

    first = run(initial)
    repeated = run(initial)
    shuffled = run(initial.iloc[list(permutation)].reset_index(drop=True))
    assert first.projection.panel.to_json(orient="table").encode() == (
        repeated.projection.panel.to_json(orient="table").encode()
    )
    assert first.events == repeated.events == shuffled.events
    assert first.accounting.to_dict() == repeated.accounting.to_dict()
    for expected, actual in zip(
        first.projection.slices, shuffled.projection.slices, strict=True
    ):
        pd.testing.assert_frame_equal(_canonical(expected), _canonical(actual))


@pytest.mark.parametrize("slot", ["aging", "disability", "earnings"])
def test_undeclared_population_change_raises_named_accounting_error(slot):
    def drops_person(frame, *args):
        return frame.iloc[1:].copy()

    modules = replace(_modules(death_probability=0), **{slot: drops_person})
    with pytest.raises(
        AccountingIdentityError, match="ACCOUNTING_IDENTITY_FAIL"
    ):
        run_production(_roster(), modules, ProductionRequest(2026, 2026))


def test_fixed_weight_change_raises_named_accounting_error():
    def changes_weight(frame, context, rng):
        out = frame.copy()
        out["weight"] *= 2
        return out

    with pytest.raises(
        AccountingIdentityError, match="ACCOUNTING_IDENTITY_FAIL"
    ):
        run_production(
            _roster(),
            replace(_modules(death_probability=0), earnings=changes_weight),
            ProductionRequest(2026, 2026),
        )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known sealed gap: fertility.py:114–128 retains mother row order; "
        "steps.py:473–497 assigns child IDs to that order"
    ),
)
def test_known_gap_asfr_child_parent_ids_follow_mother_row_order():
    initial = _roster((1.0, 1.0))
    initial["sex"] = "female"
    initial["age"] = 30
    initial["year"] = 2026

    def materialize(frame):
        context = PeriodContext(
            period_index=1,
            year=2026,
            draw_index=0,
            metadata={"synthetic_id_allocator": SyntheticPersonIdAllocator(3)},
            rng_registry=ProjectionRNGRegistry(0, 1),
            person_ordinals={1: 0, 2: 1},
        )
        step = AsfrFertilityStep(asfr=lambda year: {30: 1.0})
        result = step(
            frame,
            context,
            no_marital_transitions(frame, context, np.random.default_rng(0)),
            np.random.default_rng(0),
        )
        return _canonical(result.loc[result["age"] == 0])[
            ["person_id", "parent_person_id"]
        ]

    pd.testing.assert_frame_equal(
        materialize(initial), materialize(initial.iloc[::-1])
    )


def test_initializer_cannot_hide_an_invalid_starting_year():
    initial = _roster()
    initial.loc[0, "year"] = 2024

    def hides_invalid_year(frame):
        result = frame.copy()
        result["year"] = 2025
        return result

    with pytest.raises((ValueError, AccountingIdentityError)):
        run_production(
            initial,
            replace(_modules(), initialize=hides_invalid_year),
            ProductionRequest(2026, 2026),
        )


def test_missing_weight_after_adapter_raises_named_accounting_error():
    def loses_weight(frame, context, rng):
        return frame.drop(columns="weight")

    with pytest.raises(
        AccountingIdentityError, match="ACCOUNTING_IDENTITY_FAIL"
    ):
        run_production(
            _roster(),
            replace(_modules(), earnings=loses_weight),
            ProductionRequest(2026, 2026),
        )
