"""Frozen P2 exact contracts T1, amended T4, T5, and T6.

All full-law panels, roots, periods, and fit seeds below are fixed by the
frozen specification.  The always-positive reference is an independent
copy of v1's correlated generation body with deterministic positive signs.
Supplemental query-boundary checks beside T1 are outside frozen T1-T7.
"""

from __future__ import annotations

import pickle
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from functools import cache

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import populace_dynamics.engine.forward_earnings as fe
import populace_dynamics.engine.forward_earnings_p2_v1 as p2
from populace_dynamics.engine.candidates import CANDIDATE_3
from populace_dynamics.engine.earnings_domain import wrap_earnings_domain
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
    seed_from_generator,
)
from populace_dynamics.engine.steps import advance_age, apply_earnings

# P2 fits through populace-fit, which pins scikit-learn below 1.9 and lives
# in its own environment; without it these tests skip, as the repository's
# other populace-fit tests do.
pytest.importorskip("populace.fit")

BOUNDARY = 2000
ROOTS = tuple(range(6200, 6220))
ORDINALS = {person_id: person_id for person_id in range(640)}
FEATURES = ("earnings", "age_tp2", "prior_positive", "prior_missing")


class _DirectAlwaysPositive(fe.ForwardEarningsGenerator):
    """Evaluate the inherited positive law without any fitted sign helper."""

    def generate_with_frame_updates(
        self, frame: pd.DataFrame, year: int, rng: np.random.Generator
    ) -> fe.EarningsGenerationResult:
        """Draw the correlated prototype and return its generated-lag state."""
        if self.rank_refresh_rho is None:
            raise ValueError(
                "frame-update generation requires a bound rank-refresh rho"
            )
        year = int(year)
        if year % fe.PERIOD_STEP:
            fe._require_columns(
                frame,
                ("earnings", "age", fe.REFRESH_STATE_COLUMN),
                "forward earnings frame",
            )
            state = frame[fe.REFRESH_STATE_COLUMN].to_numpy(
                dtype=np.float64, copy=True
            )
            fe._correlated_refresh_threshold(
                float(self.rank_refresh_q),
                self.rank_refresh_rho,
                state,
            )
            age = frame["age"].to_numpy(dtype=np.float64)
            level = frame["earnings"].to_numpy(dtype=np.float64, copy=True)
            state[(level <= 0.0) | (age < fe.AGE_MIN) | (age > fe.AGE_MAX)] = (
                np.nan
            )
            return fe.EarningsGenerationResult(
                earnings=level,
                frame_updates={fe.REFRESH_STATE_COLUMN: state},
            )
        if year <= self.boundary_year:
            raise ValueError("forward earnings even draws begin after 2014")
        fe.validate_rank_refresh_fit(self)
        fe._require_columns(
            frame,
            (*fe.FRAME_COLUMNS, fe.REFRESH_STATE_COLUMN),
            "forward earnings frame",
        )

        conditioning = frame.loc[
            :, [*fe.FRAME_COLUMNS, fe.REFRESH_STATE_COLUMN]
        ]
        order = np.argsort(
            conditioning["person_id"].to_numpy(dtype=np.int64), kind="stable"
        )
        inverse = np.empty(len(order), dtype=np.int64)
        inverse[order] = np.arange(len(order))
        sorted_frame = conditioning.iloc[order]
        current_age = sorted_frame["age"].to_numpy(dtype=np.float64)
        current_level = sorted_frame["earnings"].to_numpy(dtype=np.float64)
        lag_level = sorted_frame["gen_earn_w2"].to_numpy(dtype=np.float64)
        prior_level = sorted_frame["gen_earn_w4"].to_numpy(dtype=np.float64)
        anchor_level = sorted_frame["realized_earn_2014"].to_numpy(
            dtype=np.float64
        )
        previous_state = sorted_frame[fe.REFRESH_STATE_COLUMN].to_numpy(
            dtype=np.float64
        )
        fe._correlated_refresh_threshold(
            float(self.rank_refresh_q),
            self.rank_refresh_rho,
            previous_state,
        )
        target_u_w = sorted_frame["u_w"].to_numpy(dtype=np.float64)
        if (
            not np.isfinite(target_u_w).all()
            or sorted_frame["sex"].isna().any()
        ):
            raise ValueError("forward earnings frame has invalid u_w or sex")
        required_numeric = np.column_stack(
            (current_age, current_level, lag_level, anchor_level)
        )
        prior_invalid = (
            np.any(prior_level < 0)
            or np.isinf(prior_level).any()
            or (
                year >= self.boundary_year + 2 * fe.PERIOD_STEP
                and np.isnan(prior_level).any()
            )
        )
        if (
            not np.isfinite(required_numeric).all()
            or np.any(required_numeric[:, 1:] < 0)
            or prior_invalid
        ):
            raise ValueError(
                "forward earnings frame has invalid numeric state"
            )

        seed = seed_from_generator(rng)
        gate_rng = fe._substream(seed, "gate")
        donor_rng = fe._substream(seed, "donor-draw")
        reentry_rng = fe._substream(seed, "re-entry-draw")
        refresh_gate_rng = fe._substream(seed, "memory-refresh-gate")
        refresh_rank_rng = fe._substream(seed, "memory-refresh-rank")

        anchor_rank = self._anchor_ranks(anchor_level, current_age, year)
        q0 = anchor_level == 0
        gate_uniform = gate_rng.random(len(sorted_frame))
        assert gate_uniform.shape == (len(sorted_frame),)
        signs = np.ones(len(sorted_frame), dtype=np.int64)

        generated = np.zeros(len(sorted_frame), dtype=np.float64)
        next_state = np.full(len(sorted_frame), np.nan, dtype=np.float64)
        participating = np.flatnonzero(signs == 1)
        if len(participating):
            current_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            current_positive = lag_level > 0
            current_indices = np.flatnonzero(current_positive)
            if len(current_indices):
                current_rank[current_indices] = self.level_to_rank(
                    lag_level[current_indices],
                    current_age[current_indices] - fe.PERIOD_STEP,
                    year - fe.PERIOD_STEP,
                )

            prior_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            prior_positive = prior_level > 0
            prior_indices = np.flatnonzero(prior_positive)
            if len(prior_indices):
                prior_rank[prior_indices] = self.level_to_rank(
                    prior_level[prior_indices],
                    current_age[prior_indices] - 2 * fe.PERIOD_STEP,
                    year - 2 * fe.PERIOD_STEP,
                )

            output_rank = np.full(len(sorted_frame), np.nan, dtype=np.float64)
            reentry = participating[~current_positive[participating]]
            triple = participating[
                current_positive[participating]
                & prior_positive[participating]
                & (year >= self.boundary_year + 2 * fe.PERIOD_STEP)
            ]
            pair = participating[
                current_positive[participating]
                & ~np.isin(participating, triple)
            ]

            self._draw_reentry(
                reentry, q0, anchor_rank, reentry_rng, output_rank
            )
            self._draw_transition(
                triple,
                q0,
                current_rank,
                prior_rank,
                anchor_rank,
                donor_rng,
                output_rank,
                triple=True,
            )
            self._draw_transition(
                pair,
                q0,
                current_rank,
                prior_rank,
                anchor_rank,
                donor_rng,
                output_rank,
                triple=False,
            )
            continuers = participating[current_positive[participating]]
            effective_state = previous_state.copy()
            in_support = (current_age >= fe.AGE_MIN) & (
                current_age <= fe.AGE_MAX
            )
            effective_state[~in_support] = np.nan
            refreshed = self._draw_correlated_rank_refresh(
                continuers,
                q0,
                anchor_rank,
                current_age,
                effective_state,
                refresh_gate_rng,
                refresh_rank_rng,
                output_rank,
            )
            carried = in_support[continuers]
            next_state[continuers[carried]] = refreshed[carried].astype(
                np.float64
            )
            generated[participating] = self.rank_to_level(
                output_rank[participating], current_age[participating], year
            )
        return fe.EarningsGenerationResult(
            earnings=generated[inverse],
            frame_updates={fe.REFRESH_STATE_COLUMN: next_state[inverse]},
        )


def _full_panel(*, positive: bool, missing: bool = False) -> pd.DataFrame:
    rng = np.random.Generator(np.random.PCG64(20261022))
    z = rng.standard_normal((640, 9))
    people = np.arange(640, dtype=np.int64)
    rows = []
    for person_id in people:
        for k in range(9):
            if missing and k == 1 and person_id % 8 == 0:
                continue
            amount = (
                100.0 * (1 + person_id % 13) * np.exp(0.2 * z[person_id, k])
            )
            if not positive and (person_id + k) % 7 == 0:
                amount = 0.0
            rows.append(
                {
                    "person_id": int(person_id),
                    "period": BOUNDARY - 2 * k,
                    "age": 25 + person_id % 40 - 2 * k,
                    "earnings": amount,
                    "weight": 1.0 + (person_id % 3) / 4,
                    "sex": 1 + person_id % 2,
                }
            )
    return pd.DataFrame(rows)


def _nawi(*, positive: bool) -> dict[int, float]:
    return {
        year: 1.0 if positive else float(np.exp(0.02 * (year - BOUNDARY)))
        for year in range(BOUNDARY - 25, BOUNDARY + 9)
    }


@cache
def _fitted(*, positive: bool, missing: bool = False):
    panel = _full_panel(positive=positive, missing=missing)
    nawi = _nawi(positive=positive)
    legacy = fe.fit_forward_earnings(
        panel,
        nawi,
        seed=5200,
        boundary_year=BOUNDARY,
        candidate_spec=CANDIDATE_3,
    )
    fitted = p2.fit_forward_earnings_p2_v1(
        panel, nawi, seed=5200, boundary_year=BOUNDARY
    )
    return legacy, fitted


def _initial(generator, *, truth: float | None = None) -> pd.DataFrame:
    people = np.arange(640, dtype=np.int64)
    frame = pd.DataFrame(
        {
            "person_id": people,
            "year": BOUNDARY,
            "age": 25 + people % 40,
            "sex": 1 + people % 2,
        }
    )
    if truth is not None:
        frame["separate_evaluation_truth"] = truth
    return wrap_earnings_domain(generator).materialize_initial_frame(frame)


def _assert_exact(actual, expected) -> None:
    """Compare all numeric values, masks, shapes, ordering, and fields."""
    if isinstance(actual, pd.DataFrame):
        pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    elif isinstance(actual, np.ndarray):
        assert actual.shape == expected.shape
        assert actual.dtype == expected.dtype
        np.testing.assert_array_equal(actual, expected)
    elif is_dataclass(actual):
        assert [field.name for field in fields(actual)] == [
            field.name for field in fields(expected)
        ]
        for field in fields(actual):
            _assert_exact(
                getattr(actual, field.name), getattr(expected, field.name)
            )
    elif hasattr(actual, "__slots__"):
        assert type(actual) is type(expected)
        for name in actual.__slots__:
            _assert_exact(getattr(actual, name), getattr(expected, name))
    elif isinstance(actual, Mapping):
        assert list(actual) == list(expected)
        for key in actual:
            _assert_exact(actual[key], expected[key])
    elif isinstance(actual, (tuple, list)):
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected, strict=True):
            _assert_exact(left, right)
    elif isinstance(actual, float) and np.isnan(actual):
        assert np.isnan(expected)
    else:
        assert actual == expected


def _direct_reference(legacy) -> _DirectAlwaysPositive:
    return _DirectAlwaysPositive(
        **{
            field.name: getattr(legacy.generator, field.name)
            for field in fields(fe.ForwardEarningsGenerator)
        }
    )


def _project(generator, root, *, initial=None):
    registry = ProjectionRNGRegistry(draw_index=root - 5200, n_periods=8)
    model = wrap_earnings_domain(generator)
    frame = _initial(generator) if initial is None else initial.copy(deep=True)
    snapshots = [frame.copy(deep=True)]
    queries = []
    for period_index in range(1, 9):
        year = BOUNDARY + period_index
        context = PeriodContext(
            period_index=period_index,
            year=year,
            draw_index=root - 5200,
            metadata={},
            rng_registry=registry,
            person_ordinals=ORDINALS,
        )
        earnings_rng = registry.generator(
            period_index, ProjectionModule.EARNINGS
        )
        frame = advance_age(frame, context, earnings_rng)
        if year % 2 == 0:
            queries.append(frame.copy(deep=True))
        frame = apply_earnings(frame, context, earnings_rng, model=model)
        snapshots.append(frame.copy(deep=True))
    return snapshots, queries


def _query_signs(generator, frame, root):
    """Observe the exact person-addressed sign draw without consuming it."""
    year = int(frame["year"].iloc[0])
    registry = ProjectionRNGRegistry(root - 5200, 8)
    classes, probabilities = p2.query_gate_probabilities(
        generator.shared_gate,
        frame["earnings"].to_numpy(dtype=np.float64),
        frame["age"].to_numpy(dtype=np.float64),
        frame["gen_earn_w4"].to_numpy(dtype=np.float64),
    )
    uniforms = []
    for person_id in frame["person_id"]:
        rng = registry.person_generator(
            year - BOUNDARY, ProjectionModule.EARNINGS, ORDINALS[person_id]
        )
        seed = seed_from_generator(rng)
        uniforms.append(fe._substream(seed, "gate").random())
    uniforms = np.asarray(uniforms, dtype=np.float64)
    signs = p2.draw_p2_sign(
        generator.shared_gate,
        frame["earnings"].to_numpy(dtype=np.float64),
        frame["age"].to_numpy(dtype=np.float64),
        frame["gen_earn_w4"].to_numpy(dtype=np.float64),
        uniforms,
    )
    return classes, probabilities, signs


def _hand_gate_case(history, *, prior_age=30, include=True, weight=1.0):
    rows = [
        {
            "person_id": 7,
            "period": 1998,
            "age": 32.0,
            "earnings": 100.0,
            "weight": 1.0,
        },
        {
            "person_id": 7,
            "period": 2000,
            "age": 34.0,
            "earnings": 0.0,
            "weight": 1.0,
        },
    ]
    if include:
        rows.insert(
            0,
            {
                "person_id": 7,
                "period": 1996,
                "age": prior_age,
                "earnings": history,
                "weight": weight,
            },
        )
    panel = pd.DataFrame(rows)
    cutoff = panel.loc[
        (panel["period"] <= BOUNDARY) & (panel["weight"] > 0)
    ].copy()
    estimation = cutoff.loc[cutoff["age"].between(25, 64)]
    pairs = fe._forward_pairs(estimation)
    pairs = pairs.loc[pairs["period"] == 1998].reset_index(drop=True)
    return p2.construct_gate_view(pairs, cutoff), pairs


@pytest.mark.parametrize(
    ("history", "positive", "missing"),
    [
        (0.0, 0.0, 0.0),
        (5e-7, 0.0, 0.0),
        (1e-6, 0.0, 0.0),
        (np.nextafter(1e-6, np.inf), 1.0, 0.0),
        (np.nan, 0.0, 1.0),
    ],
)
def test_t1_exact_feature_table(history, positive, missing):
    gate, pairs = _hand_gate_case(history)
    assert tuple(gate.loc[:, list(FEATURES)].columns) == FEATURES
    assert all(gate[name].dtype == np.dtype("float64") for name in FEATURES)
    np.testing.assert_array_equal(
        gate.loc[:, list(FEATURES)].to_numpy(),
        np.asarray([[100.0, 34.0, positive, missing]], dtype=np.float64),
    )
    assert gate["prior_year"].tolist() == [1996]
    assert gate["history_available"].tolist() == [not bool(missing)]
    pd.testing.assert_frame_equal(
        gate.loc[:, pairs.columns], pairs, check_exact=True
    )


@pytest.mark.parametrize(
    ("history", "positive", "missing"),
    [
        (0.0, 0.0, 0.0),
        (5e-7, 0.0, 0.0),
        (1e-6, 0.0, 0.0),
        (np.nextafter(1e-6, np.inf), 1.0, 0.0),
        (np.nan, 0.0, 1.0),
    ],
)
def test_supplemental_runtime_gate_feature_table(history, positive, missing):
    """Supplemental to T1-T7: apply T1's hand table to runtime features."""
    features = p2.gate_features(
        np.asarray([100.0]), np.asarray([34.0]), np.asarray([history])
    )
    assert tuple(features.columns) == FEATURES
    assert all(
        features[name].dtype == np.dtype("float64") for name in FEATURES
    )
    np.testing.assert_array_equal(
        features.to_numpy(),
        np.asarray([[100.0, 34.0, positive, missing]], dtype=np.float64),
    )


def test_supplemental_sign_draw_cumulative_boundary(monkeypatch):
    """Supplemental to T1-T7: section 6's >= selects the boundary class."""
    classes = np.asarray([0, 1], dtype=np.int64)
    probabilities = np.asarray([[0.25, 0.75]], dtype=np.float64)
    monkeypatch.setattr(
        p2, "query_gate_probabilities", lambda *_: (classes, probabilities)
    )
    signs = p2.draw_p2_sign(
        None,
        np.asarray([100.0]),
        np.asarray([34.0]),
        np.asarray([0.0]),
        np.asarray([0.25]),
    )
    np.testing.assert_array_equal(signs, np.asarray([0], dtype=np.int64))


@pytest.mark.parametrize(
    "reason",
    [
        "before_supplied_panel",
        "absent_collection_wave",
        "intermittent_nonresponse",
        "irregular_gap",
        "no_prior_person",
        "upstream_sequence_rule",
        "no_family_record",
        "excluded_relationship",
        "upstream_missing_sentinel",
    ],
)
def test_t1_every_absent_history_reason_retains_pair(reason):
    gate, pairs = _hand_gate_case(None, include=False)
    assert reason
    assert len(gate) == len(pairs) == 1
    assert gate["prior_positive"].tolist() == [0.0]
    assert gate["prior_missing"].tolist() == [1.0]
    assert gate["history_available"].tolist() == [False]
    pd.testing.assert_frame_equal(
        gate.loc[:, pairs.columns], pairs, check_exact=True
    )


def test_t1_weight_exclusion_and_outside_age_history():
    absent, _ = _hand_gate_case(100.0, weight=0.0)
    assert absent["prior_missing"].tolist() == [1.0]
    observed, _ = _hand_gate_case(100.0, prior_age=23.0)
    assert observed["prior_positive"].tolist() == [1.0]
    assert observed["prior_missing"].tolist() == [0.0]
    assert observed["history_available"].tolist() == [True]


@pytest.mark.parametrize("history", [-1.0, -np.inf, np.inf])
def test_t1_invalid_history_refuses_whole_operation(history):
    with pytest.raises(ValueError, match="P2_INVALID_HISTORY_VALUE"):
        _hand_gate_case(history)
    frame = pd.DataFrame(
        {"earnings": [100.0], "age": [40.0], "gen_earn_w4": [history]}
    )
    with pytest.raises(ValueError, match="P2_INVALID_HISTORY_VALUE"):
        p2.runtime_gate_features(frame)


@settings(deadline=None)
@given(
    st.one_of(
        st.none(),
        st.floats(min_value=0.0, allow_nan=False, allow_infinity=False),
    )
)
def test_t1_history_encoding_property(history):
    gate, pairs = _hand_gate_case(history, include=history is not None)
    expected = (0.0, 1.0) if history is None else (float(history > 1e-6), 0.0)
    np.testing.assert_array_equal(
        gate[["prior_positive", "prior_missing"]].to_numpy(),
        np.asarray([expected], dtype=np.float64),
    )
    assert len(gate) == len(pairs)


def test_t1_full_pair_retention_and_first_step_initialization():
    legacy, fitted = _fitted(positive=False, missing=True)
    pd.testing.assert_frame_equal(
        fitted.forward_pairs, legacy.forward_pairs, check_exact=True
    )
    frame = _initial(fitted.generator)
    source = _full_panel(positive=False, missing=True)
    boundary = source.loc[source["period"] == BOUNDARY].set_index("person_id")
    previous = source.loc[source["period"] == BOUNDARY - 2].set_index(
        "person_id"
    )
    np.testing.assert_array_equal(
        frame["earnings"], boundary.loc[frame["person_id"], "earnings"]
    )
    np.testing.assert_array_equal(frame["gen_earn_w2"], frame["earnings"])
    np.testing.assert_array_equal(
        frame["gen_earn_w4"], previous["earnings"].reindex(frame["person_id"])
    )
    query = frame.copy()
    query["age"] += 2
    features = p2.runtime_gate_features(query)
    missing = np.asarray(
        [person_id % 8 == 0 for person_id in frame["person_id"]]
    )
    np.testing.assert_array_equal(
        features["prior_missing"], missing.astype(np.float64)
    )


@pytest.mark.parametrize("root", ROOTS)
def test_t4_always_positive_direct_law_neutrality(root):
    legacy, fitted = _fitted(positive=True, missing=True)
    direct = _direct_reference(legacy)
    expected, reference_queries = _project(direct, root)
    # Check the effective gate law before drawing any candidate path. This
    # exposes wrong signs directly before they can trigger donor failures.
    for frame in reference_queries:
        classes, probabilities, signs = _query_signs(
            fitted.generator, frame, root
        )
        assert classes.tolist() == [1]
        np.testing.assert_array_equal(probabilities, np.ones((len(frame), 1)))
        np.testing.assert_array_equal(
            signs, np.ones(len(frame), dtype=np.int64)
        )
    actual, queries = _project(fitted.generator, root)
    _assert_exact(actual, expected)
    assert (
        queries[0]
        .loc[queries[0]["person_id"] % 8 == 0, "gen_earn_w4"]
        .isna()
        .all()
    )


def test_t5_exact_all_non_gate_components():
    legacy, fitted = _fitted(positive=False)
    for name in (
        "estimation_panel",
        "forward_pairs",
        "anchors",
        "u_w_diagnostics",
        "rank_refresh_fit_audit",
    ):
        _assert_exact(getattr(fitted, name), getattr(legacy, name))
    for field in fields(fe.ForwardEarningsGenerator):
        if field.name not in {"shared_gate", "zero_anchor_gate"}:
            _assert_exact(
                getattr(fitted.generator, field.name),
                getattr(legacy.generator, field.name),
            )
    assert fitted.generator.zero_anchor_gate is None
    assert fitted.n_zero_anchor_pairs == 0
    assert fitted.generator.rank_refresh_q == 0.55
    assert fitted.generator.rank_refresh_rho == -0.60
    assert fitted.fit_signature[
        "component_checksums"
    ] == p2.unchanged_component_checksums(
        legacy.generator,
        legacy.estimation_panel,
        legacy.forward_pairs,
        legacy.anchors,
        legacy.u_w_diagnostics,
    )
    assert (
        fitted.q_invariant_fit_signature_sha256
        != legacy.q_invariant_fit_signature_sha256
    )
    # The historical map is constructed before age filtering, including age 23.
    cutoff = _full_panel(positive=False)
    cutoff = cutoff.sort_values(["person_id", "period"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(
        fitted.cutoff_panel, cutoff, check_exact=True
    )


def _expected_runtime(frame, older):
    older = np.asarray(older, dtype=np.float64)
    return pd.DataFrame(
        {
            "earnings": frame["earnings"].to_numpy(dtype=np.float64),
            "age_tp2": frame["age"].to_numpy(dtype=np.float64),
            "prior_positive": (older > 1e-6).astype(np.float64),
            "prior_missing": np.isnan(older).astype(np.float64),
        },
        index=frame.index,
    )


@pytest.mark.parametrize("root", ROOTS)
def test_t6_clock_features_interfaces_and_restart(root):
    _, fitted = _fitted(positive=False, missing=True)
    generator = fitted.generator
    snapshots, queries = _project(generator, root)
    for frame in queries:
        _, _, signs = _query_signs(generator, frame, root)
        generated = snapshots[int(frame["year"].iloc[0]) - BOUNDARY][
            "earnings"
        ]
        np.testing.assert_array_equal(signs == 1, generated.to_numpy() > 0.0)
    for index, frame in enumerate(queries[:3]):
        source_period = (2 * (index + 1)) - 4
        if source_period == -2:
            older = snapshots[0]["gen_earn_w4"]
        elif source_period == 0:
            older = snapshots[0]["earnings"]
        else:
            older = snapshots[source_period]["earnings"]
        expected = _expected_runtime(frame, older)
        pd.testing.assert_frame_equal(
            p2.runtime_gate_features(frame), expected, check_exact=True
        )
        np.testing.assert_array_equal(frame["gen_earn_w4"], np.asarray(older))
    for period_index in range(1, 9):
        if period_index % 2:
            np.testing.assert_array_equal(
                snapshots[period_index]["gen_earn_w2"],
                snapshots[period_index - 1]["gen_earn_w2"],
            )
            np.testing.assert_array_equal(
                snapshots[period_index]["gen_earn_w4"],
                snapshots[period_index - 1]["gen_earn_w4"],
            )
        else:
            np.testing.assert_array_equal(
                snapshots[period_index]["gen_earn_w4"],
                snapshots[period_index - 1]["gen_earn_w2"],
            )
            np.testing.assert_array_equal(
                snapshots[period_index]["gen_earn_w2"],
                snapshots[period_index]["earnings"],
            )

    # The non-stateful interface has its supported rho=None binding; q, donors,
    # four features, current state, and person/period addressing remain identical.
    class RecordingP2(p2.P2ForwardEarningsGeneratorV1):
        def _draw_participation(self, current, age, older, uniforms):
            self.recorded.append(
                (current.copy(), age.copy(), older.copy(), uniforms.copy())
            )
            return super()._draw_participation(current, age, older, uniforms)

    def recording_model(model):
        recording = RecordingP2(
            **{
                field.name: getattr(model, field.name)
                for field in fields(model)
            }
        )
        object.__setattr__(recording, "recorded", [])
        return recording

    iid = recording_model(replace(generator, rank_refresh_rho=None))
    correlated = recording_model(generator)
    for frame in queries:
        before = frame.copy(deep=True)
        registry = ProjectionRNGRegistry(root - 5200, 8)
        year = int(frame["year"].iloc[0])
        for model, stateful in ((correlated, True), (iid, False)):
            recorded = p2.runtime_gate_features(frame)
            pd.testing.assert_frame_equal(
                recorded,
                _expected_runtime(frame, frame["gen_earn_w4"]),
                check_exact=True,
            )
            rng = registry.generator(
                year - BOUNDARY, ProjectionModule.EARNINGS
            )
            if stateful:
                result = model.generate_with_frame_updates(frame, year, rng)
                assert result.earnings.shape == (640,)
                assert set(result.frame_updates) == {fe.REFRESH_STATE_COLUMN}
            else:
                assert model.generate(frame, year, rng).shape == (640,)
            current, age, older, uniforms = model.recorded[-1]
            np.testing.assert_array_equal(current, frame["earnings"])
            np.testing.assert_array_equal(age, frame["age"])
            np.testing.assert_array_equal(older, frame["gen_earn_w4"])
            assert uniforms.shape == (640,)
        pd.testing.assert_frame_equal(frame, before, check_exact=True)
    corrupted = queries[1].copy(deep=True)
    corrupted.loc[0, "gen_earn_w4"] = np.nan
    with pytest.raises(ValueError, match="invalid numeric state"):
        generator.generate_with_frame_updates(
            corrupted,
            BOUNDARY + 4,
            registry.generator(4, ProjectionModule.EARNINGS),
        )
    for completed_period in range(1, 8):
        checkpoint = pickle.dumps(
            (
                generator,
                snapshots[completed_period],
                BOUNDARY,
                ORDINALS,
                root - 5200,
                8,
                completed_period,
            ),
            protocol=pickle.HIGHEST_PROTOCOL,
        )
        (
            restored,
            materialized,
            boundary,
            ordinals,
            draw_index,
            n_periods,
            completed,
        ) = pickle.loads(checkpoint)
        assert restored.boundary_year == boundary == BOUNDARY
        suffix = p2.resume_p2_projection(
            restored,
            materialized,
            draw_index=draw_index,
            completed_period=completed,
            person_ordinals=ordinals,
            n_periods=n_periods,
        )
        _assert_exact(list(suffix), snapshots[completed_period + 1 :])


def _nominal_future_panel():
    panel = _full_panel(positive=False, missing=True)
    boundary = panel.loc[panel["period"] == BOUNDARY].copy()
    futures = []
    for delta in (2, 4):
        future = boundary.copy()
        future["period"] += delta
        future["age"] += delta
        futures.append(future)
    return pd.concat([panel, *futures], ignore_index=True)


@cache
def _nominal_future_fitted():
    _, admitted = _fitted(positive=False, missing=True)
    baseline = p2.fit_forward_earnings_p2_v1(
        _nominal_future_panel(),
        _nawi(positive=False),
        seed=5200,
        boundary_year=BOUNDARY,
    )
    assert baseline.fit_signature == admitted.fit_signature
    assert pickle.dumps(baseline.generator, protocol=5) == pickle.dumps(
        admitted.generator, protocol=5
    )
    _assert_exact(baseline.estimation_panel, admitted.estimation_panel)
    _assert_exact(baseline.forward_pairs, admitted.forward_pairs)
    _assert_exact(baseline.gate_view, admitted.gate_view)
    return baseline


def test_t6_nominal_future_baseline_structural_identity():
    baseline = _nominal_future_fitted()
    _, admitted = _fitted(positive=False, missing=True)
    _assert_exact(_initial(baseline.generator), _initial(admitted.generator))
    _assert_exact(
        _initial(baseline.generator, truth=0.0).drop(
            columns="separate_evaluation_truth"
        ),
        _initial(admitted.generator),
    )


def _future_variants():
    panel = _full_panel(positive=False, missing=True)
    boundary = panel.loc[panel["period"] == BOUNDARY].copy()
    base = _nominal_future_panel()
    altered = base.copy(deep=True)
    altered.loc[altered["period"] > BOUNDARY, "earnings"] += 100.0
    appended = boundary.copy()
    appended["period"] = BOUNDARY + 6
    appended["age"] += 6
    reordered = pd.concat(
        [base.loc[base["period"] > BOUNDARY].iloc[::-1], panel],
        ignore_index=True,
    )
    return {
        "alter_future_earnings": altered,
        "append_future_rows": pd.concat([base, appended], ignore_index=True),
        "delete_future_rows": panel,
        "reorder_future_rows": reordered,
        "future_realized_nawi": base,
        "separate_evaluation_truth": base,
    }


@pytest.mark.parametrize("variant", tuple(_future_variants()))
def test_t6_no_look_ahead_fitted_state_and_complete_paths(variant):
    fitted = _nominal_future_fitted()
    nawi = _nawi(positive=False)
    if variant == "future_realized_nawi":
        nawi = {
            year: amount * 100.0 if year > BOUNDARY else amount
            for year, amount in nawi.items()
        }
    altered = p2.fit_forward_earnings_p2_v1(
        _future_variants()[variant], nawi, seed=5200, boundary_year=BOUNDARY
    )
    assert altered.fit_signature == fitted.fit_signature
    assert pickle.dumps(altered.generator, protocol=5) == pickle.dumps(
        fitted.generator, protocol=5
    )
    _assert_exact(altered.estimation_panel, fitted.estimation_panel)
    _assert_exact(altered.forward_pairs, fitted.forward_pairs)
    _assert_exact(altered.gate_view, fitted.gate_view)
    for root in ROOTS:
        expected_initial = (
            _initial(fitted.generator, truth=0.0)
            if variant == "separate_evaluation_truth"
            else None
        )
        expected, expected_queries = _project(
            fitted.generator, root, initial=expected_initial
        )
        initial = _initial(
            altered.generator,
            truth=100.0 if variant == "separate_evaluation_truth" else None,
        )
        actual, queries = _project(altered.generator, root, initial=initial)
        if variant == "separate_evaluation_truth":
            expected = [
                frame.drop(columns="separate_evaluation_truth")
                for frame in expected
            ]
            expected_queries = [
                frame.drop(columns="separate_evaluation_truth")
                for frame in expected_queries
            ]
            actual = [
                frame.drop(columns="separate_evaluation_truth")
                for frame in actual
            ]
            queries = [
                frame.drop(columns="separate_evaluation_truth")
                for frame in queries
            ]
        _assert_exact(actual, expected)
        _assert_exact(queries, expected_queries)
        for frame, expected_frame in zip(
            queries, expected_queries, strict=True
        ):
            _assert_exact(
                p2.runtime_gate_features(frame),
                p2.runtime_gate_features(expected_frame),
            )
            _assert_exact(
                _query_signs(altered.generator, frame, root),
                _query_signs(fitted.generator, expected_frame, root),
            )


def test_t1_frozen_candidate_fit_and_signature_contract():
    import hashlib

    from populace_dynamics.engine.candidates import REGISTRY

    _, fitted = _fitted(positive=False, missing=True)
    spec = p2.P2_CANDIDATE_SPEC
    assert spec.candidate_id == "m6_candidate3_p2_history_engine_v1"
    assert spec.contract_revision == "p2_frozen_2026_10_22"
    assert spec.operations == CANDIDATE_3.operations
    assert all(
        candidate.candidate_id != spec.candidate_id
        for candidate in REGISTRY.values()
    )
    assert fitted.zero_anchor_gate_removed is True
    assert fitted.generator.zero_anchor_gate is None
    assert fitted.n_zero_anchor_pairs == 0
    signature = fitted.fit_signature
    assert signature["candidate"] == spec.canonical_dict()
    assert signature["seed"] == 5200
    assert signature["boundary"] == BOUNDARY
    assert signature["features"] == list(FEATURES)
    assert signature["dtype"] == "float64"
    assert signature["gate_count"] == 1
    assert signature["zero_anchor_gate"] is None
    assert signature["zero_anchor_gate_removed"] is True
    assert signature["n_zero_anchor_pairs"] == 0
    assert signature["history_rule"] == {
        "earnings_scale": "nominal",
        "positive_threshold": 1e-6,
        "comparison": ">",
        "lag_years_from_source": 2,
        "history_join": "exact person/year left join; many_to_one",
        "lookup_before_age_filter": True,
        "missing_encoding": [0.0, 1.0],
        "invalid_refusal": "P2_INVALID_HISTORY_VALUE",
    }
    canonical = fitted.gate_view.sort_values(
        ["person_id", "period_tp2"], kind="stable"
    )
    older = canonical["prior_earnings"].to_numpy(dtype=np.float64)
    available = canonical["history_available"].to_numpy(dtype=bool)
    target = fitted.generator.shared_gate._target_models["earnings_tp2"]
    assert tuple(target.columns) == FEATURES
    classes = np.asarray(target.gate.classes_)
    probabilities = target.gate.predict_proba(
        canonical.loc[:, list(target.columns)].to_numpy(dtype=np.float64)
    )
    payloads = {
        "canonical_feature_sha256": (canonical[list(FEATURES)], "<f8"),
        "pair_keys_sha256": (
            canonical[["person_id", "period", "period_tp2"]],
            "<i8",
        ),
        "lookup_year_sha256": (canonical["period"] - 2, "<i8"),
        "availability_sha256": (available, "|b1"),
        "history_values_sha256": (np.where(available, older, 0.0), "<f8"),
        "raw_target_sha256": (canonical["earnings_tp2"], "<f8"),
        "target_weights_sha256": (canonical["weight_tp2"], "<f8"),
        "probabilities_sha256": (probabilities, "<f8"),
    }
    for key, (array, dtype) in payloads.items():
        values = np.ascontiguousarray(np.asarray(array, dtype=dtype))
        digest = hashlib.sha256()
        digest.update(dtype.encode())
        digest.update(np.asarray(values.shape, dtype="<i8").tobytes())
        digest.update(values.tobytes())
        assert signature[key] == digest.hexdigest()
    assert signature["classes"] == classes.tolist()
    assert signature["probability_shape"] == list(probabilities.shape)
    assert signature["serialized_gate_protocol"] == 5
    assert (
        signature["serialized_gate_sha256"]
        == hashlib.sha256(
            pickle.dumps(fitted.generator.shared_gate, protocol=5)
        ).hexdigest()
    )
    assert signature["estimator_parameters"] == vars(
        fe._default_qrf_factory(seed=5200)
    )
    assert signature["classifier_parameters"] == target.gate.get_params()
    assert signature["dependencies"]
    assert signature["sources"]
    assert signature[
        "component_checksums"
    ] == p2.unchanged_component_checksums(
        fitted.generator,
        fitted.estimation_panel,
        fitted.forward_pairs,
        fitted.anchors,
        fitted.u_w_diagnostics,
    )
    refit = p2.refit_earnings_chained_generator_p2_v1(
        _full_panel(positive=False, missing=True),
        _nawi(positive=False),
        seed=5200,
        boundary_year=BOUNDARY,
    )
    assert refit.engine_candidate_id == spec.candidate_id
    assert refit.engine_candidate_spec_sha256 == spec.sha256
    assert refit.zero_anchor_gate is None
    assert refit.zero_anchor_gate_removed is True
    assert refit.n_zero_anchor_pairs == 0
    assert refit.contract_revision == spec.contract_revision
    assert refit.fit_signature == signature
    assert refit.generator.rank_refresh_q == 0.55
    assert refit.generator.rank_refresh_rho == -0.60


def test_t1_exact_prior_key_order_and_many_to_one_validation():
    probes = (0.0, 5e-7, 1e-6, np.nextafter(1e-6, np.inf))
    pairs = (
        pd.concat(
            [
                _hand_gate_case(value)[1].assign(person_id=index)
                for index, value in enumerate(probes)
            ],
            ignore_index=True,
        )
        .iloc[[3, 1, 0, 2]]
        .reset_index(drop=True)
    )
    history = pd.DataFrame(
        {
            "person_id": range(4),
            "period": 1996,
            "earnings": probes,
            "age": [23.0, 30.0, 30.0, 30.0],
            "weight": 1.0,
        }
    )
    gate = p2.construct_gate_view(pairs, history)
    pd.testing.assert_frame_equal(
        gate.loc[:, pairs.columns], pairs, check_exact=True
    )
    np.testing.assert_array_equal(gate["prior_positive"], [1.0, 0.0, 0.0, 0.0])
    np.testing.assert_array_equal(gate["prior_missing"], np.zeros(4))
    irregular = history.assign(period=1995)
    absent = p2.construct_gate_view(pairs, irregular)
    np.testing.assert_array_equal(absent["prior_missing"], np.ones(4))
    duplicated = pd.concat([history, history.iloc[[0]]], ignore_index=True)
    with pytest.raises(pd.errors.MergeError, match="not a many-to-one"):
        p2.construct_gate_view(pairs, duplicated)
