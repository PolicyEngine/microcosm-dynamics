"""Invented-data differential and property tests for Track B B1."""

from __future__ import annotations

import copy
import pickle

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.engine.candidates import CANDIDATE_3
from populace_dynamics.engine.forward_earnings import (
    REFRESH_STATE_COLUMN,
    fit_forward_earnings,
)
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import apply_earnings
from populace_dynamics.harness import m6_projection
from populace_dynamics.harness.m6_projection import (
    project_earnings_on_realized_support,
)
from populace_dynamics.track_b import replay as replay_module
from populace_dynamics.track_b.replay import (
    RNG_N_PERIODS,
    earnings_rng_signature,
    replay_earnings_on_realized_support,
)
from tests.test_m6_engine_forward_earnings import (
    _fit_panel,
    _RecordingQRFFactory,
)

HARNESS_N_PERIODS = m6_projection.PROJECTION_END_YEAR - 2014


def _inputs(seed: int = 0) -> dict[str, object]:
    """Fit the real candidate-3 earnings law with an invented QRF sign gate."""
    panel = _fit_panel()
    # The always-positive invented sign gate needs an observed invented
    # zero-to-positive transition to supply its re-entry donor pool.
    panel.loc[
        (panel["person_id"] == 1) & (panel["period"] == 2006), "earnings"
    ] = 0.0
    generator = fit_forward_earnings(
        panel,
        {year: 100.0 for year in range(2002, 2019)},
        seed=seed,
        qrf_factory=_RecordingQRFFactory(),
        candidate_spec=CANDIDATE_3,
    ).generator
    anchor = panel.loc[panel["period"] == 2014].copy()
    initial = anchor[["person_id", "age"]].assign(
        year=2014, sex="female", earnings_domain=True
    )
    initial = pd.concat(
        [
            initial,
            pd.DataFrame(
                {
                    "person_id": [9999],
                    "age": [30],
                    "year": [2014],
                    "sex": ["male"],
                    "earnings_domain": [False],
                }
            ),
        ],
        ignore_index=True,
    )
    # Neither the original loop nor the copy may pass realized NAWI onward.
    initial["nawi"] = object()
    truth = pd.concat(
        [
            anchor[["person_id", "age", "earnings", "weight"]].assign(
                period=year, cohort="prime"
            )
            for year in (2014, 2016, 2018)
        ],
        ignore_index=True,
    )
    # Realized absence affects scored support, never the fixed history roster.
    truth = truth.loc[
        ~((truth["person_id"] == 2) & (truth["period"] == 2018))
    ].reset_index(drop=True)
    return {
        "initial_slice": initial,
        "truth_support": truth,
        "generator": generator,
        "domain_person_ids": set(anchor["person_id"]),
        "all_person_ids": list(initial["person_id"]),
    }


def _frame_bytes(frame: pd.DataFrame) -> bytes:
    """Preserve numeric bits, schema, index and text without object pointers."""
    columns = []
    for name in frame.columns:
        array = frame[name].to_numpy()
        payload = (
            pickle.dumps(array.tolist(), protocol=5)
            if array.dtype.hasobject
            else array.tobytes()
        )
        columns.append((name, str(array.dtype), payload))
    return pickle.dumps((frame.index.tolist(), columns), protocol=5)


def _canonical(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(["person_id", "period"]).reset_index(drop=True)


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("draw_index", [0, 19])
def test_copied_loop_matches_original_scored_bytes(seed, draw_index):
    inputs = _inputs(seed)
    incumbent = project_earnings_on_realized_support(
        **copy.deepcopy(inputs), draw_index=draw_index
    )
    replay = replay_earnings_on_realized_support(
        **copy.deepcopy(inputs), draw_index=draw_index
    )
    pd.testing.assert_frame_equal(replay.scored, incumbent, check_exact=True)
    assert _frame_bytes(replay.scored) == _frame_bytes(incumbent)
    assert replay.rng_signature == earnings_rng_signature(
        all_person_ids=inputs["all_person_ids"],
        draw_index=draw_index,
        n_periods=HARNESS_N_PERIODS,
    )
    assert replay.history["year"].unique().tolist() == list(range(2014, 2019))
    for _, annual in replay.history.groupby("year"):
        assert set(annual["person_id"]) == inputs["domain_person_ids"]
        assert not annual["person_id"].duplicated().any()
    assert len(replay.history) == 5 * len(inputs["domain_person_ids"])
    assert "nawi" not in replay.history
    assert REFRESH_STATE_COLUMN in replay.history
    assert replay.scored.query("person_id == 2 and period == 2018").empty
    assert len(replay.history.query("person_id == 2 and period == 2018")) == 1
    for even, odd in ((2014, 2015), (2016, 2017)):
        even_earnings = replay.history.loc[
            replay.history["year"] == even, "earnings"
        ]
        odd_earnings = replay.history.loc[
            replay.history["year"] == odd, "earnings"
        ]
        assert (
            even_earnings.to_numpy().tobytes()
            == odd_earnings.to_numpy().tobytes()
        )


@settings(max_examples=16, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=4),
    draw_index=st.integers(min_value=0, max_value=19),
    order=st.permutations(tuple(range(11))),
)
def test_seed_draw_row_order_property(seed, draw_index, order):
    inputs = _inputs(seed)
    original_inputs = copy.deepcopy(inputs)
    first = replay_earnings_on_realized_support(
        **inputs, draw_index=draw_index
    )
    repeated = replay_earnings_on_realized_support(
        **copy.deepcopy(inputs), draw_index=draw_index
    )
    assert _frame_bytes(first.history) == _frame_bytes(repeated.history)
    assert _frame_bytes(first.scored) == _frame_bytes(repeated.scored)
    assert first.rng_signature == repeated.rng_signature
    assert _frame_bytes(inputs["initial_slice"]) == _frame_bytes(
        original_inputs["initial_slice"]
    )
    assert _frame_bytes(inputs["truth_support"]) == _frame_bytes(
        original_inputs["truth_support"]
    )

    inputs["initial_slice"] = inputs["initial_slice"].iloc[list(order)]
    inputs["truth_support"] = inputs["truth_support"].iloc[::-1]
    inputs["all_person_ids"] = inputs["all_person_ids"][::-1]
    reordered = replay_earnings_on_realized_support(
        **copy.deepcopy(inputs), draw_index=draw_index
    )
    incumbent = project_earnings_on_realized_support(
        **copy.deepcopy(inputs), draw_index=draw_index
    )
    assert _frame_bytes(reordered.scored) == _frame_bytes(incumbent)
    assert _frame_bytes(_canonical(first.history)) == _frame_bytes(
        _canonical(reordered.history)
    )
    assert _frame_bytes(_canonical(first.scored)) == _frame_bytes(
        _canonical(reordered.scored)
    )
    assert first.rng_signature == reordered.rng_signature
    # Caller-owned frames and scored output do not alias history snapshots.
    before = _frame_bytes(first.scored)
    first.history.loc[:, "earnings"] = -1.0
    assert _frame_bytes(first.scored) == before


def test_rng_signature_preserves_registry_and_substream_coordinates():
    signature = earnings_rng_signature(
        all_person_ids=[20, 1, 10], draw_index=7, n_periods=HARNESS_N_PERIODS
    )
    assert signature["n_periods"] == 8
    assert signature["draw_seed"] == 5207
    assert signature["person_ordinals"] == [
        {"person_id": 1, "ordinal": 0},
        {"person_id": 10, "ordinal": 1},
        {"person_id": 20, "ordinal": 2},
    ]
    assert signature["earnings_substream_codes"] == {
        "gate": 1,
        "donor-draw": 2,
        "re-entry-draw": 3,
        "memory-refresh-gate": 4,
        "memory-refresh-rank": 5,
    }
    registry = ProjectionRNGRegistry(7, 8)
    assert [row["period_index"] for row in signature["periods"]] == [
        1,
        2,
        3,
        4,
    ]
    for row in signature["periods"]:
        sequence = registry.seed_sequence(
            row["period_index"], ProjectionModule.EARNINGS
        )
        assert row["spawn_key"] == list(sequence.spawn_key)
        assert row["entropy"] == list(sequence.entropy)
        for ordinal in (0, 1, 2):
            expected = np.random.default_rng(
                np.random.SeedSequence(
                    entropy=row["entropy"],
                    spawn_key=(*row["spawn_key"], ordinal),
                    pool_size=row["pool_size"],
                )
            ).bytes(64)
            observed = registry.person_generator(
                row["period_index"], ProjectionModule.EARNINGS, ordinal
            ).bytes(64)
            assert expected == observed


def test_replay_registry_size_equals_the_harness_constant():
    assert RNG_N_PERIODS == m6_projection.PROJECTION_END_YEAR - 2014


class _RecordingPandas:
    """Delegate to pandas, recording each ``concat`` input list."""

    def __init__(self):
        self.concatenated = []

    def __getattr__(self, name):
        return getattr(pd, name)

    def concat(self, frames, *args, **kwargs):
        frames = list(frames)
        self.concatenated.append(frames)
        return pd.concat(frames, *args, **kwargs)


def _buffer_sharing_step(frame, context, rng, *, model):
    """The engine step, but untouched columns share the input's buffers."""
    stepped = apply_earnings(frame, context, rng, model=model)
    changed = {
        column: stepped[column]
        for column in stepped.columns
        if column not in frame or not stepped[column].equals(frame[column])
    }
    return frame.assign(**changed)[list(stepped.columns)]


@pytest.mark.parametrize("step", ["engine", "buffer_sharing"])
def test_2014_history_snapshot_shares_no_memory_with_later_snapshots(
    monkeypatch, step
):
    # apply_earnings returns a copy, so the "buffer_sharing" step checks
    # that replay.py's own copies detach the snapshots. Any one of its three
    # copies suffices; this pins the property, not a particular copy.
    if step == "buffer_sharing":
        monkeypatch.setattr(
            replay_module, "apply_earnings", _buffer_sharing_step
        )
    recorder = _RecordingPandas()
    monkeypatch.setattr(replay_module, "pd", recorder)
    replay_earnings_on_realized_support(**_inputs(), draw_index=0)

    snapshots = next(
        frames for frames in recorder.concatenated if len(frames) == 5
    )
    assert [frame["period"].unique().tolist() for frame in snapshots] == [
        [year] for year in range(2014, 2019)
    ]
    anchor, later = snapshots[0], snapshots[1:]
    # Extension-dtype to_numpy() always allocates, so only NumPy dtypes can
    # witness shared buffers.
    numeric = [
        column
        for column in anchor.columns
        if isinstance(anchor[column].dtype, np.dtype)
        and anchor[column].dtype.kind in "biuf"
    ]
    assert {"person_id", "age", "earnings", "period"} <= set(numeric)
    for snapshot in later:
        for column in numeric:
            assert not np.shares_memory(
                anchor[column].to_numpy(), snapshot[column].to_numpy()
            ), column
