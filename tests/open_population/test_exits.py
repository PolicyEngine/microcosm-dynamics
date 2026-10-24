"""Check OP1 death coupling and survivor-only exits on invented rosters."""

from functools import partial

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a.adapters import widowhood_marital_step
from populace_dynamics.engine.accounting import PopulationEventKind
from populace_dynamics.engine.loop import (
    PeriodContext,
    PeriodModules,
    ProjectionEngine,
)
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import advance_age
from populace_dynamics.open_population.errors import (
    AccountingIdentityError,
    EmigrationMaritalIncompatibility,
    IdOrStreamCollision,
)
from populace_dynamics.open_population.events import EventLedger
from populace_dynamics.open_population.exits import (
    ExitAdapter,
    no_marital_transitions,
    require_emigration_compatible,
)


def roster(size=8):
    return pd.DataFrame(
        {
            "person_id": np.arange(1, size + 1),
            "year": 2025,
            "age": 30,
            "sex": "female",
            "weight": np.arange(1, size + 1, dtype=float),
        }
    )


def context(frame, draw=0):
    return PeriodContext(
        period_index=1,
        year=2026,
        draw_index=draw,
        metadata={},
        rng_registry=ProjectionRNGRegistry(draw, 1),
        person_ordinals={
            person_id: ordinal
            for ordinal, person_id in enumerate(sorted(frame["person_id"]))
        },
    )


def mortality(frame, coordinates, rng):
    del rng
    ordered = frame.sort_values("person_id", kind="stable")
    die = np.asarray(
        [
            coordinates.person_generator(
                ProjectionModule.MORTALITY, person_id
            ).random()
            < 0.3
            for person_id in ordered["person_id"]
        ],
        dtype=bool,
    )
    return ordered.loc[~die].reset_index(drop=True)


def unchanged(frame, coordinates, rng):
    return frame


def unchanged_reader(frame, coordinates, marital, rng):
    return frame


def modules(mortality_step):
    return PeriodModules(
        mortality=mortality_step,
        aging=advance_age,
        marital_core=no_marital_transitions,
        fertility=unchanged_reader,
        disability=unchanged,
        earnings=unchanged,
        claiming=unchanged,
        household_composition=unchanged_reader,
    )


def ids(ledger, kind):
    return {event.person_id for event in ledger.events if event.kind == kind}


def test_mortality_receives_original_arguments_and_generator():
    frame = roster()
    coordinates = context(frame)
    rng = np.random.default_rng(17)
    expected_rng = np.random.default_rng(17)
    expected_rng.random(4)
    seen = []

    def wrapped(actual, actual_context, actual_rng):
        assert actual is frame
        assert actual_context is coordinates
        assert actual_rng is rng
        seen.append(True)
        actual_rng.random(4)
        return actual.iloc[1:]

    ledger = EventLedger()
    out = ExitAdapter(wrapped, ledger, lambda f, c: np.zeros(len(f)))(
        frame, coordinates, rng
    )
    pd.testing.assert_frame_equal(out, frame.iloc[1:])
    assert seen == [True]
    assert rng.random() == expected_rng.random()
    assert ids(ledger, PopulationEventKind.DEATH) == {1}


def test_off_returns_exact_mortality_object_without_rng_registry():
    frame = roster()
    survivors = frame.iloc[2:]
    coordinates = PeriodContext(1, 2026, 0, {})
    ledger = EventLedger()
    out = ExitAdapter(lambda f, c, r: survivors, ledger)(
        frame, coordinates, np.random.default_rng(1)
    )
    assert out is survivors
    assert ids(ledger, PopulationEventKind.DEATH) == {1, 2}


def test_in_place_mortality_preserves_pre_call_death_weight():
    frame = roster(3)
    coordinates = context(frame)

    def mutate(actual, coordinates, rng):
        actual.drop(index=actual.index[0], inplace=True)
        return actual

    ledger = EventLedger()
    ExitAdapter(mutate, ledger)(frame, coordinates, np.random.default_rng(1))
    assert [(event.person_id, event.weight) for event in ledger.events] == [
        (1, 1.0)
    ]


@given(size=st.integers(1, 20), draw=st.integers(0, 30))
@settings(max_examples=15, deadline=None)
def test_off_matches_closed_projection_slice_by_slice(size, draw):
    frame = roster(size)
    ledger = EventLedger()
    closed = ProjectionEngine(modules(mortality)).project(
        frame, end_year=2030, draw_index=draw
    )
    opened = ProjectionEngine(modules(ExitAdapter(mortality, ledger))).project(
        frame, end_year=2030, draw_index=draw
    )
    for a, b in zip(closed.slices, opened.slices, strict=True):
        pd.testing.assert_frame_equal(a, b)
    assert all(
        event.kind == PopulationEventKind.DEATH for event in ledger.events
    )
    assert len({event.person_id for event in ledger.events}) == len(
        ledger.events
    )


@given(
    size=st.integers(1, 30),
    draw=st.integers(0, 30),
    probabilities=st.tuples(
        st.floats(0, 1, allow_nan=False, allow_infinity=False),
        st.floats(0, 1, allow_nan=False, allow_infinity=False),
    ),
)
@settings(max_examples=25, deadline=None)
def test_same_year_coupling_exclusivity_and_order(size, draw, probabilities):
    frame = roster(size)
    coordinates = context(frame, draw)
    low, high = sorted(probabilities)
    ledgers = []
    outputs = []
    for probability, current in (
        (low, frame),
        (high, frame),
        (low, frame.iloc[::-1]),
    ):
        ledger = EventLedger()
        outputs.append(
            ExitAdapter(
                mortality,
                ledger,
                lambda f, c, p=probability: np.full(len(f), p),
            )(current, coordinates, np.random.default_rng(draw))
        )
        ledgers.append(ledger)
    a, b, shuffled = ledgers
    assert ids(a, PopulationEventKind.DEATH) == ids(
        b, PopulationEventKind.DEATH
    )
    assert ids(a, PopulationEventKind.EMIGRATION).issubset(
        ids(b, PopulationEventKind.EMIGRATION)
    )
    assert not ids(a, PopulationEventKind.DEATH) & ids(
        a, PopulationEventKind.EMIGRATION
    )
    assert a.events == shuffled.events
    assert outputs[0].to_json(orient="split") == outputs[2].to_json(
        orient="split"
    )
    assert len(a.events) + len(outputs[0]) == size


def test_hazard_sees_only_survivors_and_cannot_mutate_output():
    frame = roster(3)
    coordinates = context(frame)

    def hazard(survivors, actual_context):
        assert survivors["person_id"].tolist() == [2, 3]
        assert actual_context is coordinates
        survivors.loc[:, "weight"] = 999
        return [1.0, 0.0]

    ledger = EventLedger()
    out = ExitAdapter(lambda f, c, r: f.iloc[1:], ledger, hazard)(
        frame, coordinates, np.random.default_rng(2)
    )
    assert out["person_id"].tolist() == [3]
    assert out["weight"].tolist() == [3.0]
    assert ids(ledger, PopulationEventKind.DEATH) == {1}
    assert ids(ledger, PopulationEventKind.EMIGRATION) == {2}


@pytest.mark.parametrize(
    "probabilities", [[0.1], [-0.1] * 3, [np.nan] * 3, [1.1] * 3]
)
def test_invalid_hazard_probabilities_are_refused(probabilities):
    frame = roster(3)
    with pytest.raises(ValueError, match="emigration"):
        ExitAdapter(unchanged, EventLedger(), lambda f, c: probabilities)(
            frame, context(frame), np.random.default_rng(1)
        )


def test_non_null_hazard_needs_person_streams():
    frame = roster(3)
    with pytest.raises(IdOrStreamCollision, match="ID_OR_STREAM_COLLISION"):
        ExitAdapter(unchanged, EventLedger(), lambda f, c: [0.0] * len(f))(
            frame, PeriodContext(1, 2026, 0, {}), np.random.default_rng(1)
        )


@pytest.mark.parametrize("defect", ["new_id", "duplicate_id", "weight"])
def test_invalid_mortality_output_is_refused(defect):
    frame = roster(3)

    def invalid(actual, coordinates, rng):
        out = actual.copy()
        if defect == "new_id":
            out.loc[0, "person_id"] = 99
        elif defect == "duplicate_id":
            out.loc[0, "person_id"] = 2
        else:
            out.loc[0, "weight"] = 99.0
        return out

    with pytest.raises(
        AccountingIdentityError, match="ACCOUNTING_IDENTITY_FAIL"
    ):
        ExitAdapter(invalid, EventLedger())(
            frame, context(frame), np.random.default_rng(1)
        )


def test_emigration_refuses_widowhood_adapter_including_partial():
    def hazard(frame, coordinates):
        return np.zeros(len(frame))

    for marital in (
        widowhood_marital_step,
        partial(widowhood_marital_step, roster_ids=frozenset({1, 2})),
        lambda f, c, r: no_marital_transitions(f, c, r),
    ):
        require_emigration_compatible(marital, None)
        with pytest.raises(
            EmigrationMaritalIncompatibility,
            match="EMIGRATION_MARITAL_INCOMPATIBLE",
        ):
            require_emigration_compatible(marital, hazard)
    require_emigration_compatible(no_marital_transitions, hazard)


def test_two_person_counterexample_spouse_absence_becomes_widowhood():
    frame = roster(2).assign(
        marital_status="married",
        spouse_person_id=pd.array([2, 1], dtype="Int64"),
        widowhood_year=pd.array([pd.NA, pd.NA], dtype="Int64"),
        late_spouse_person_id=pd.array([pd.NA, pd.NA], dtype="Int64"),
        widowed_in_projection=False,
    )
    after_emigration = frame.iloc[:1].assign(year=2026)
    result = widowhood_marital_step(
        after_emigration,
        context(frame),
        np.random.default_rng(1),
        roster_ids=frozenset({1, 2}),
    )
    assert result.sim_years["marital_status"].tolist() == ["widowed"]
    assert result.sim_years["late_spouse_person_id"].tolist() == [2]
