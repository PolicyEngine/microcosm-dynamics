"""Exercise-1 replay invariants on INVENTED data, with no PSID reads.

Every person, career, benefit, weight, rate and probability comes from the
existing invented Track A fixture. Differential checks compare only two
implementations run on those invented inputs, never comparator values.
"""

from __future__ import annotations

import json
from collections import Counter

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import invented, prepare_track_a_cohort
from populace_dynamics.cola_track_a import runner as legacy
from populace_dynamics.cola_track_a.config import TrackAConfig
from populace_dynamics.group_breakdowns.cola import reproduce_cola
from tests.cola_track_a.test_assembly import _inputs


def _invented_inputs():
    """The inherited INVENTED fixture, including both registered waves."""
    cohort = prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(
            invented.invented_psid2010_inputs(seed=7)
        ),
        data_provenance="invented",
        config=TrackAConfig(draw_indices=(0, 1)),
    )
    return _inputs(cohort)


def _normal(result):
    return json.loads(json.dumps(result, default=str, allow_nan=False))


@pytest.fixture(scope="module")
def pair():
    """All seven registered rows, both waves, and two INVENTED draws."""
    inputs = _invented_inputs()
    config = TrackAConfig(draw_indices=(0, 1))
    project = legacy._project_population
    benefit_rows = legacy.reference_benefit_rows
    populations = []
    paths = {}
    retained_slices = []
    initial = {
        wave: cohort.initial_slice.copy(deep=True)
        for wave, cohort in inputs.cohorts_by_wave().items()
    }

    def collect_population(*args, **kwargs):
        output = project(*args, **kwargs)
        populations.append(args[0].anchor_wave)
        retained_slices.extend(
            result.slices[-1] for result in output[0].values()
        )
        return output

    def collect_rows(result, **kwargs):
        key = (kwargs["context"].cohort.anchor_wave, kwargs["draw"])
        paths.setdefault(key, []).append(id(result))
        return benefit_rows(result, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(legacy, "_project_population", collect_population)
        patch.setattr(legacy, "reference_benefit_rows", collect_rows)
        replay = reproduce_cola(inputs, config=config)
    reference = legacy.run_track_a(inputs, config=config)
    return (
        replay,
        reference,
        config,
        inputs,
        {
            "populations": populations,
            "paths": paths,
            "retained_slices": retained_slices,
            "initial": initial,
        },
    )


def test_complete_artifact_matches_frozen_runner(pair):
    replay, reference, *_ = pair
    # Entire payload: five age cells, per-draw diagnostics, counters,
    # component shares, reduced-increase summaries, floors and provenance.
    assert _normal(replay.result) == _normal(reference)


def test_one_population_projection_shared_by_registered_rows(pair):
    _, _, config, _, observed = pair
    assert Counter(observed["populations"]) == {2011: 1, 2009: 1}
    for (wave, _), paths in observed["paths"].items():
        assert len(paths) == len(config.rows_for_wave(wave))
        assert len(set(paths)) == 1


def test_every_benefit_row_has_unique_reference_year_state(pair):
    replay, _, config, _, _ = pair
    assert replay.exercise == "cola"
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
            assert rows["benefit_base"].gt(0).all()
            assert rows["benefit_reform"].gt(0).all()
            assert rows["beneficiary_base"].all()
            assert rows["beneficiary_reform"].all()
            assert rows["age_reference"].equals(
                config.reference_year - rows["birth_year"]
            )


def test_components_preserve_scenario_amounts(pair):
    replay, *_ = pair
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


def test_replay_retention_preserves_projection_and_opening_frames(pair):
    replay, _, _, inputs, observed = pair
    for wave, cohort in inputs.cohorts_by_wave().items():
        pd.testing.assert_frame_equal(
            cohort.initial_slice, observed["initial"][wave]
        )
    for frame in observed["retained_slices"]:
        assert "draw" not in frame
    frame = observed["retained_slices"][0]
    before = frame.copy(deep=True)
    saved = replay.states[2011]["sex"].copy()
    try:
        replay.states[2011]["sex"] = "INVENTED mutation"
        pd.testing.assert_frame_equal(frame, before)
    finally:
        replay.states[2011]["sex"] = saved


@settings(max_examples=3, deadline=None)
@given(
    row_id=st.sampled_from(("R0", "R1", "R2", "R3", "R4", "R5", "R6")),
    draw=st.integers(min_value=0, max_value=5),
)
def test_replay_matches_frozen_semantics_for_draw_and_row(row_id, draw):
    """Row selection and draw selection leave the frozen semantics intact."""
    config = TrackAConfig(rows=(row_id,), draw_indices=(draw,))
    inputs = _invented_inputs()
    replay = reproduce_cola(inputs, config=config)
    reference = legacy.run_track_a(inputs, config=config)
    assert _normal(replay.result) == _normal(reference)
    assert set(replay.benefit_rows[row_id]["draw"]) == {draw}
