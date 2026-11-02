"""Check OP1 stock-flow, coupling, prefixes and reproducibility on inventions.

Cover ``docs/design/open_population.md`` §§2.9, 3.1 (OP1), 5.4 and 7,
approved in ruling d1925. Use the sealed adapters at ``engine/steps.py:113–166``
and ``baselines/fertility.py:163–181`` without supplying any observed data.
"""

from __future__ import annotations

import math
from dataclasses import replace
from functools import partial

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.baselines.fertility import AsfrFertilityStep
from populace_dynamics.baselines.tr2026_intermediate import LAST_YEAR
from populace_dynamics.engine.accounting import PopulationEventKind
from populace_dynamics.engine.entrant_schedule import (
    validate_projection_allocator,
)
from populace_dynamics.engine.loop import (
    SCHEDULED_ENTRIES_KEY,
    PeriodContext,
    PeriodModules,
    ProjectionEngine,
    SyntheticPersonIdAllocator,
)
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import advance_age, apply_mortality
from populace_dynamics.open_population.errors import (
    AccountingIdentityError,
    IdOrStreamCollision,
)
from populace_dynamics.open_population.exits import no_marital_transitions
from populace_dynamics.open_population.harness import (
    REGISTERED_PRODUCTION_HORIZONS,
    ProductionRequest,
    run_production,
)

START = 2025


@pytest.fixture(autouse=True)
def _invented_horizons(monkeypatch):
    from populace_dynamics.open_population import harness

    original = harness._registered_horizon
    horizons = {
        "invented_2026": 2026,
        "invented_2027": 2027,
        "invented_2028": 2028,
    }

    def lookup(scenario):
        return (
            horizons[scenario] if scenario in horizons else original(scenario)
        )

    monkeypatch.setattr(harness, "_registered_horizon", lookup)


def _request(end_year, **kwargs):
    return ProductionRequest(f"invented_{end_year}", **kwargs)


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


@example(
    weights=[1.0, 1.5, 2.0],
    death_probability=0.25,
    emigration_probability=0.35,
    birth_probability=1.0,
    draw=0,
)
@example(
    weights=[0.1, 0.7],
    death_probability=0.25,
    emigration_probability=0.35,
    birth_probability=0.5,
    draw=4,
)
@settings(max_examples=12, deadline=None)
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
        _request(2028, draw_index=draw),
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
        _request(2026),
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
    initial = _canonical(_roster((0.1, 0.7, 1.3, 2.0)).iloc[::-1])
    modules = _modules()
    scheduled = _scheduled(range(2026, 2029))
    closed = ProjectionEngine(modules).project(
        initial,
        end_year=2028,
        draw_index=draw,
        metadata={SCHEDULED_ENTRIES_KEY: scheduled},
    )
    result = run_production(
        initial,
        modules,
        _request(2028, draw_index=draw),
        scheduled_entries=scheduled,
    )
    for expected, actual in zip(
        closed.slices, result.projection.slices, strict=True
    ):
        columns = list(expected.columns)
        pd.testing.assert_frame_equal(expected, actual[columns])
    assert result.kind == "production"
    assert result.scenario == "invented_2028"
    assert not any(event.kind == "emigration" for event in result.events)


@pytest.mark.parametrize("person_ids", [(-2, -1), (0, 1), (7, 8)])
def test_disabled_emigration_matches_closed_run_for_signed_ids(person_ids):
    initial = _roster((1.0, 1.0))
    initial["person_id"] = person_ids
    initial["sex"] = "female"
    modules = _modules(death_probability=0, birth_probability=1)
    initial = _canonical(initial)
    closed = ProjectionEngine(modules).project(
        initial, end_year=2026, draw_index=0
    )
    actual = run_production(initial, modules, _request(2026))
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
        _request(2028),
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


def test_registered_production_horizon_matches_baseline():
    assert dict(REGISTERED_PRODUCTION_HORIZONS) == {
        "tr2026_intermediate": LAST_YEAR
    }
    with pytest.raises(TypeError):
        REGISTERED_PRODUCTION_HORIZONS["another"] = 2026


def test_registered_scenario_projects_to_its_horizon_on_inventions():
    result = run_production(
        _roster(),
        _modules(death_probability=0, birth_probability=0),
        ProductionRequest("tr2026_intermediate"),
        emigration_hazard=_hazard(0.02),
    )
    assert (result.kind, result.scenario, result.horizon) == (
        "production",
        "tr2026_intermediate",
        LAST_YEAR,
    )
    assert len(result.projection.slices) == LAST_YEAR - START + 1
    for year, frame in enumerate(result.projection.slices, start=START):
        assert set(frame["year"]) <= {year}
    prefix = result.read_prefix(2030)
    for short, full in zip(
        prefix.slices, result.projection.slices, strict=False
    ):
        pd.testing.assert_frame_equal(short, full)


@settings(max_examples=12, deadline=None)
@given(
    scenario=st.sampled_from(tuple(REGISTERED_PRODUCTION_HORIZONS)),
    draw=st.integers(),
    start=st.one_of(st.none(), st.integers()),
)
def test_production_horizon_is_bound_to_scenario(scenario, draw, start):
    request = ProductionRequest(scenario, draw_index=draw, start_year=start)
    assert request.end_year == REGISTERED_PRODUCTION_HORIZONS[scenario]


def test_conflicting_production_end_years_cannot_be_constructed():
    for end in (2027, 2029):
        for keyword in ("end_year", "registered_horizon"):
            with pytest.raises(TypeError, match="unexpected keyword"):
                ProductionRequest("tr2026_intermediate", **{keyword: end})
    request = ProductionRequest("tr2026_intermediate")
    with pytest.raises((AttributeError, TypeError)):
        request.end_year = 2027


def test_unknown_production_scenario_is_named():
    with pytest.raises(
        IdOrStreamCollision, match="ID_OR_STREAM_COLLISION.*missing"
    ):
        ProductionRequest("missing")


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"scenario": 2100}, "scenario must be a string"),
        (
            {"scenario": "tr2026_intermediate", "draw_index": 1.5},
            "draw_index must be an integer",
        ),
        (
            {"scenario": "tr2026_intermediate", "start_year": "2025"},
            "start_year must be an integer or None",
        ),
    ],
)
def test_production_field_type_errors_are_accurate(kwargs, message):
    with pytest.raises(TypeError, match=message):
        ProductionRequest(**kwargs)


def test_independent_horizons_change_open_but_not_closed_shared_slices():
    # Provenance: docs/design/open_population_evidence/horizon_dependence.py.
    initial = _roster((1.0, 1.0))
    initial["sex"] = "female"
    modules = _modules(death_probability=0, birth_probability=1)

    def project(end_year, with_entrants):
        metadata = {}
        if with_entrants:
            metadata[SCHEDULED_ENTRIES_KEY] = _scheduled(
                range(2026, end_year + 1)
            )
        return ProjectionEngine(modules).project(
            initial, end_year=end_year, draw_index=0, metadata=metadata
        )

    for with_entrants in (False, True):
        short = project(2026, with_entrants)
        long = project(2027, with_entrants)
        if with_entrants:
            assert not short.slices[1].equals(long.slices[1])
        else:
            pd.testing.assert_frame_equal(short.slices[1], long.slices[1])


@settings(max_examples=6, deadline=None)
@given(
    draw=st.integers(min_value=0, max_value=8),
    permutation=st.permutations((0, 1, 2, 3)),
)
def test_determinism_and_order_with_canonical_mortality(draw, permutation):
    initial = _roster((0.1, 0.7, 1.3, 2.0))
    modules = _modules()
    request = _request(2027, draw_index=draw)

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
        run_production(_roster(), modules, _request(2026))


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
            _request(2026),
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
            _request(2026),
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
            _request(2026),
        )


@example(permutation=(3, 2, 1, 0))
@settings(max_examples=6, deadline=None)
@given(permutation=st.permutations((0, 1, 2, 3)))
def test_non_sorting_person_mortality_is_order_invariant(permutation):
    def mortality(frame, context, rng):
        keep = [
            context.person_generator(
                ProjectionModule.MORTALITY, person
            ).random()
            >= 0.1
            for person in frame["person_id"]
        ]
        return frame.loc[np.asarray(keep, dtype=bool)].copy()

    initial = _roster((1.0, 1.5, 2.0, 2.5))
    initial["sex"] = "female"
    modules = replace(_modules(birth_probability=1), mortality=mortality)

    def run(frame):
        return run_production(frame, modules, _request(2027))

    expected = run(initial)
    actual = run(initial.iloc[list(permutation)].reset_index(drop=True))
    for a, b in zip(
        expected.projection.slices, actual.projection.slices, strict=True
    ):
        pd.testing.assert_frame_equal(_canonical(a), _canonical(b))


@pytest.mark.parametrize(
    "slot",
    [
        "aging",
        "marital_core",
        "disability",
        "earnings",
        "claiming",
        "household_composition",
    ],
)
def test_offsetting_weight_swaps_are_refused_in_every_fixed_slot(slot):
    modules = _modules(death_probability=0, birth_probability=0)
    original = getattr(modules, slot)

    def swaps_weights(frame, *args):
        # Net stock weight is unchanged, so only the per-person check detects it.
        frame = frame.copy() if slot != "marital_core" else frame
        frame["weight"] = frame["weight"].to_numpy()[::-1]
        return original(frame, *args)

    with pytest.raises(
        AccountingIdentityError, match="ACCOUNTING_IDENTITY_FAIL"
    ):
        run_production(
            _roster((1.0, 1.5)),
            replace(modules, **{slot: swaps_weights}),
            _request(2026),
        )


def test_annual_transitions_retain_only_accounting_columns(monkeypatch):
    from populace_dynamics.open_population import harness

    original = harness.reconcile_history
    captured = []

    def check(transitions, **kwargs):
        for transition in transitions:
            assert list(transition.opening.columns) == [
                "person_id",
                "year",
                "weight",
            ]
            assert list(transition.closing.columns) == [
                "person_id",
                "year",
                "weight",
            ]
        captured.extend(transitions)
        return original(transitions, **kwargs)

    monkeypatch.setattr(harness, "reconcile_history", check)
    run_production(_roster(), _modules(), _request(2027))
    assert len(captured) == 2
