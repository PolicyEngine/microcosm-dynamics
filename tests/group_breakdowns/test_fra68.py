"""Exercise-3 replay invariants and differential checks on INVENTED data.

The existing FRA fixture supplies invented persons, earnings, weights,
probabilities and rates. No real-data reader or outcome pipeline runs.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a import runner as track_runner
from populace_dynamics.fra68_track import FRA68Config, run_fra68
from populace_dynamics.group_breakdowns.fra68 import reproduce_fra68
from tests.fra68_track.test_runner import _inputs


def _normal(result):
    return json.loads(json.dumps(result, default=str, allow_nan=False))


@pytest.fixture(scope="module")
def pair():
    """All nine registered rows and both waves, with INVENTED data."""
    inputs = _inputs()
    config = FRA68Config(draw_indices=(0, 1))
    return (
        reproduce_fra68(inputs, config=config),
        run_fra68(inputs, config=config),
        config,
    )


def test_complete_artifact_matches_frozen_runner(pair):
    replay, reference, _ = pair
    # Entire payload: five age cells, per-draw diagnostics, counters,
    # membership mechanisms, schedules, floors and provenance.
    assert _normal(replay.result) == _normal(reference)


def test_all_registered_rows_and_waves_are_retained(pair):
    replay, _, config = pair
    assert replay.exercise == "fra68"
    assert tuple(replay.benefit_rows) == config.rows
    assert set(replay.states) == {2011, 2009}
    for wave, frame in replay.states.items():
        assert not frame.duplicated(["draw", "person_id"]).any()
        assert set(frame["draw"]) == set(config.draw_indices)
        assert set(frame["year"]) == {config.reference_year}
        assert set(frame["sex"]) <= {"female", "male"}
        assert "marital_status" in frame
        for row_id in config.rows_for_wave(wave):
            rows = replay.benefit_rows[row_id]
            assert not rows.duplicated(["draw", "person_id"]).any()
            joined = rows.merge(
                frame[["draw", "person_id"]],
                on=["draw", "person_id"],
                how="left",
                indicator=True,
                validate="one_to_one",
            )
            assert joined["_merge"].eq("both").all()
            assert (
                rows["benefit_base"].gt(0) | rows["benefit_reform"].gt(0)
            ).all()
            assert rows["age_reference"].equals(
                config.reference_year - rows["birth_year"]
            )


def test_components_preserve_current_law_amounts(pair):
    replay, _, _ = pair
    for rows in replay.benefit_rows.values():
        for row in rows.itertuples(index=False):
            for scenario in ("base", "reform"):
                amount = sum(
                    component[scenario]
                    for component in row.benefit_components.values()
                )
                assert amount == pytest.approx(
                    getattr(row, f"benefit_{scenario}"), rel=1e-12
                )


def test_projection_collection_does_not_mutate_frozen_slices(monkeypatch):
    original = track_runner._project_population
    observed = []

    def collect(*args, **kwargs):
        output = original(*args, **kwargs)
        observed.extend(result.slices[-1] for result in output[0].values())
        return output

    monkeypatch.setattr(track_runner, "_project_population", collect)
    replay = reproduce_fra68(
        _inputs(), config=FRA68Config(rows=("F0",), draw_indices=(0,))
    )
    assert len(observed) == 1
    assert "draw" not in observed[0]
    before = observed[0].copy(deep=True)
    replay.states[2011]["sex"] = "INVENTED mutation"
    pd.testing.assert_frame_equal(observed[0], before)


@settings(max_examples=6, deadline=None)
@given(
    row_id=st.sampled_from(("F0", "F3", "F4", "F7", "F8")),
    draw=st.integers(min_value=0, max_value=5),
)
def test_replay_matches_frozen_semantics_for_draw_and_row(row_id, draw):
    """Changing the retained row/draw cannot change frozen semantics."""
    config = FRA68Config(rows=(row_id,), draw_indices=(draw,))
    inputs = _inputs()
    replay = reproduce_fra68(inputs, config=config)
    reference = run_fra68(inputs, config=config)
    assert _normal(replay.result) == _normal(reference)
    assert set(replay.benefit_rows[row_id]["draw"]) == {draw}
