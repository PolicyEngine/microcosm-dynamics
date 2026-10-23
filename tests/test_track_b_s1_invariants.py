"""Exact S1 invariants on invented earnings histories."""

from __future__ import annotations

import hashlib
import pickle
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace

import numpy as np
import pandas as pd
import pytest
from hypothesis import Phase, given, settings
from hypothesis import strategies as st
from populace.fit.qrf import DEFAULT_ZERO_ATOL, RegimeGatedQRF

from populace_dynamics.engine import forward_earnings as v1
from populace_dynamics.engine import forward_earnings_s1_v1 as s1
from populace_dynamics.engine.candidates import (
    CANDIDATE_3,
    REGISTRY,
)
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.refit import (
    EARNINGS_SPEC_SHA256,
    refit_earnings_chained_generator,
)
from populace_dynamics.engine.steps import apply_earnings

BOUNDARY = 2000
YEARS = tuple(range(1988, BOUNDARY + 1, 2))
PROPERTY = settings(
    max_examples=4,
    deadline=None,
    database=None,
    derandomize=True,
    phases=(Phase.generate,),
)


class _RecordingFactory:
    """Observe fitting views while using the pinned QRF defaults."""

    def __init__(self):
        self.calls = []

    def __call__(self, *, seed):
        owner = self
        model = RegimeGatedQRF(seed=seed)

        class Fitter:
            def fit(self, frame, **kwargs):
                owner.calls.append((seed, frame.copy(deep=True), kwargs))
                return model.fit(frame, **kwargs)

        return Fitter()


def _history(seed=0, *, unit=False, scale=1):
    nawi = {
        year: 1.0 if unit else 128.0 * 2.0 ** ((year - 1988) // 2)
        for year in range(1988, BOUNDARY + 9)
    }
    rows = []
    for person in range(64):
        for wave, year in enumerate(YEARS):
            relative = scale * 2.0 ** ((person + wave + seed) % 4 - 1)
            if (person + wave + seed) % 5 == 0:
                relative = 0.0
            rows.append(
                (
                    person,
                    year,
                    relative * nawi[year],
                    27 + 5 * (person // 8),
                    1.0 + person % 3,
                )
            )
    return (
        pd.DataFrame(
            rows, columns=["person_id", "period", "earnings", "age", "weight"]
        ),
        nawi,
    )


def _fit(panel, nawi, *, successor=True, factory=None):
    fitter = s1.fit_forward_earnings if successor else v1.fit_forward_earnings
    return fitter(
        panel,
        nawi,
        seed=37,
        boundary_year=BOUNDARY,
        qrf_factory=factory,
        candidate_spec=s1.CANDIDATE_S1 if successor else CANDIDATE_3,
    )


def _initial(fitted, *, correlated=True):
    generator = fitted.generator
    if not correlated:
        generator = replace(generator, rank_refresh_rho=None)
    frame = fitted.anchors[["person_id", "age"]].copy()
    frame["sex"] = "female"
    frame["year"] = BOUNDARY
    return generator, generator.materialize_initial_frame(frame)


def _advance(generator, frame, year, rng):
    frame = frame.copy(deep=True)
    frame["age"] += 1.0
    frame = apply_earnings(
        frame,
        PeriodContext(year - BOUNDARY, year, 0, {}),
        rng,
        model=generator,
    )
    frame["year"] = year
    return frame


def _non_gate_signature(fitted):
    return v1._q_invariant_fit_signature(
        replace(fitted.generator, shared_gate=None, zero_anchor_gate=None),
        fitted.estimation_panel,
        fitted.forward_pairs,
        fitted.anchors,
        fitted.u_w_diagnostics,
    )


def _probabilities(gate, features):
    target = gate._target_models["earnings_tp2"]
    return target.gate.predict_proba(
        features.loc[:, list(target.columns)].to_numpy(dtype=np.float64)
    )


def _assert_frames(left, right):
    pd.testing.assert_frame_equal(left, right, check_exact=True)


def _assert_exact_state(left, right):
    """Compare every nested fitted field, including array dtypes and slots."""
    assert type(left) is type(right)
    if isinstance(left, pd.DataFrame):
        _assert_frames(left, right)
    elif isinstance(left, np.ndarray):
        np.testing.assert_array_equal(left, right, strict=True)
    elif isinstance(left, Mapping):
        assert left.keys() == right.keys()
        for key in left:
            _assert_exact_state(left[key], right[key])
    elif is_dataclass(left):
        for field in fields(left):
            _assert_exact_state(
                getattr(left, field.name), getattr(right, field.name)
            )
    elif isinstance(left, list | tuple):
        assert len(left) == len(right)
        for before, after in zip(left, right, strict=True):
            _assert_exact_state(before, after)
    elif isinstance(left, v1.CellMarginal):
        for name in left.__slots__:
            _assert_exact_state(getattr(left, name), getattr(right, name))
    else:
        np.testing.assert_equal(left, right)


def _observe_queries(monkeypatch):
    calls = []
    original = v1._gate_sign_draw

    def record(gate, level, age, uniforms):
        # The outer adapter is observed again when it delegates to its model.
        if not isinstance(gate, s1._GateQuery):
            calls.append((gate, level.copy(), age.copy(), uniforms.copy()))
        return original(gate, level, age, uniforms)

    monkeypatch.setattr(v1, "_gate_sign_draw", record)
    return calls


@PROPERTY
@given(seed=st.integers(0, 100), scale=st.integers(1, 8))
def test_t1_unit_index_features_probabilities_and_draws_equal_v1(seed, scale):
    panel, nawi = _history(seed, unit=True, scale=scale)
    old_factory, new_factory = _RecordingFactory(), _RecordingFactory()
    old = _fit(panel, nawi, successor=False, factory=old_factory)
    new = _fit(panel, nawi, factory=new_factory)
    for old_call, new_call in zip(
        old_factory.calls, new_factory.calls, strict=True
    ):
        assert old_call[0] == new_call[0]
        assert old_call[2] == new_call[2]
        _assert_frames(old_call[1], new_call[1])
    for name in ("shared_gate", "zero_anchor_gate"):
        np.testing.assert_array_equal(
            _probabilities(getattr(old.generator, name), old.forward_pairs),
            _probabilities(getattr(new.generator, name), new.forward_pairs),
        )
    for correlated in (False, True):
        old_gen, old_frame = _initial(old, correlated=correlated)
        new_gen, new_frame = _initial(new, correlated=correlated)
        old_rng = np.random.default_rng(seed)
        new_rng = np.random.default_rng(seed)
        with pytest.MonkeyPatch.context() as patch:
            calls = _observe_queries(patch)
            for year in range(BOUNDARY + 1, BOUNDARY + 7):
                calls.clear()
                old_frame = _advance(old_gen, old_frame, year, old_rng)
                old_calls = list(calls)
                calls.clear()
                new_frame = _advance(new_gen, new_frame, year, new_rng)
                _assert_frames(old_frame, new_frame)
                assert (
                    old_rng.bit_generator.state == new_rng.bit_generator.state
                )
                for left, right in zip(old_calls, calls, strict=True):
                    for a, b in zip(left[1:], right[1:], strict=True):
                        np.testing.assert_array_equal(a, b)


@PROPERTY
@given(exponents=st.lists(st.integers(-4, 4), min_size=7, max_size=7))
def test_t2_period_rescaling_preserves_gate_features_and_probabilities(
    exponents,
):
    panel, nawi = _history()
    factors = dict(zip(YEARS, (2.0**e for e in exponents), strict=True))
    scaled_panel = panel.copy(deep=True)
    scaled_panel["earnings"] *= scaled_panel["period"].map(factors)
    scaled_nawi = {
        year: value * factors.get(year, 1.0) for year, value in nawi.items()
    }
    first_factory, second_factory = _RecordingFactory(), _RecordingFactory()
    first = _fit(panel, nawi, factory=first_factory)
    second = _fit(scaled_panel, scaled_nawi, factory=second_factory)
    for one, two in zip(
        first_factory.calls, second_factory.calls, strict=True
    ):
        np.testing.assert_array_equal(
            one[1][["earnings", "age_tp2"]], two[1][["earnings", "age_tp2"]]
        )
        assert np.all(
            two[1].loc[two[1]["earnings_tp2"] > 0, "earnings_tp2"] > 1e-6
        )
    features = first.forward_pairs.copy(deep=True)
    features["earnings"] /= features["period"].map(nawi)
    for name in ("shared_gate", "zero_anchor_gate"):
        np.testing.assert_array_equal(
            _probabilities(getattr(first.generator, name), features),
            _probabilities(getattr(second.generator, name), features),
        )


@PROPERTY
@given(seed=st.integers(0, 100))
def test_t4_only_gate_fitting_predictor_changes(seed):
    panel, nawi = _history(seed)
    untouched = panel.copy(deep=True)
    old_factory, new_factory = _RecordingFactory(), _RecordingFactory()
    old = _fit(panel, nawi, successor=False, factory=old_factory)
    new = _fit(panel, nawi, factory=new_factory)
    _assert_frames(panel, untouched)
    assert _non_gate_signature(old) == _non_gate_signature(new)
    for name in ("estimation_panel", "forward_pairs", "anchors"):
        _assert_frames(getattr(old, name), getattr(new, name))
    for before, after in zip(
        old_factory.calls, new_factory.calls, strict=True
    ):
        assert before[0] == after[0] == 37
        assert (
            before[2]
            == after[2]
            == {
                "predictors": ["earnings", "age_tp2"],
                "targets": ["earnings_tp2"],
                "weights": "weight_tp2",
            }
        )
        expected = before[1].copy(deep=True)
        expected["earnings"] /= expected["period"].map(nawi)
        _assert_frames(expected, after[1])
    _assert_frames(_initial(old)[1], _initial(new)[1])
    for name in ("shared_gate", "zero_anchor_gate"):
        old_target = getattr(old.generator, name)._target_models[
            "earnings_tp2"
        ]
        new_target = getattr(new.generator, name)._target_models[
            "earnings_tp2"
        ]
        assert old_target.gate.get_params() == new_target.gate.get_params()
    expected_surface = new.forward_pairs.copy(deep=True)
    expected_surface["earnings"] /= expected_surface["period"].map(nawi)
    record = {
        "non_gate_fit_sha256": _non_gate_signature(new),
        "participation_gate": s1.PARTICIPATION_GATE_SPEC,
        "participation_gates": {},
    }
    for key, name in (
        ("shared", "shared_gate"),
        ("zero_anchor", "zero_anchor_gate"),
    ):
        gate = getattr(new.generator, name)
        actual = v1._gate_fit_signature(gate, expected_surface)
        target = gate._target_models["earnings_tp2"]
        ordered = expected_surface.sort_values(
            ["person_id", "period_tp2"], kind="stable"
        )
        features = ordered[list(target.columns)].to_numpy(dtype="<f8")
        digest = hashlib.sha256()
        for array in (
            features,
            np.asarray(target.gate.classes_, dtype="<i8"),
            np.asarray(target.gate.predict_proba(features), dtype="<f8"),
        ):
            digest.update(np.asarray(array.shape, dtype="<i8").tobytes())
            digest.update(np.ascontiguousarray(array).tobytes())
        assert actual["canonical_surface_sha256"] == digest.hexdigest()
        record["participation_gates"][key] = actual
    assert new.q_invariant_fit_signature_sha256 == v1._canonical_sha256(record)


def test_t4_raw_target_zero_tolerance_is_preserved():
    panel, nawi = _history()
    positions = (panel["person_id"] == 0) & (
        panel["period"].isin([1990, 1992, 1994])
    )
    panel.loc[positions, "earnings"] = [0.5e-6, 1e-6, 2e-6]
    before_factory, after_factory = _RecordingFactory(), _RecordingFactory()
    _fit(panel, nawi, successor=False, factory=before_factory)
    _fit(panel, nawi, factory=after_factory)
    model = RegimeGatedQRF(seed=37)
    assert DEFAULT_ZERO_ATOL == 1e-6
    assert model._sign_labels(np.asarray([0.5e-6, 1e-6, 2e-6])).tolist() == [
        0,
        0,
        1,
    ]
    for before, after in zip(
        before_factory.calls, after_factory.calls, strict=True
    ):
        np.testing.assert_array_equal(
            before[1]["earnings_tp2"], after[1]["earnings_tp2"]
        )
        np.testing.assert_array_equal(
            model._sign_labels(before[1]["earnings_tp2"].to_numpy()),
            model._sign_labels(after[1]["earnings_tp2"].to_numpy()),
        )


@PROPERTY
@given(
    future_earnings=st.integers(1, 10**9), future_nawi=st.integers(1, 10**9)
)
def test_t5_post_boundary_inputs_cannot_change_fit_or_draws(
    future_earnings, future_nawi
):
    panel, nawi = _history()
    future = panel[panel["period"] == BOUNDARY].copy(deep=True)
    future["period"] = BOUNDARY + 2
    future["age"] += 2
    future["earnings"] = float(future_earnings)
    contaminated = pd.concat([panel, future], ignore_index=True)
    altered_nawi = {
        year: value if year <= BOUNDARY else float(future_nawi)
        for year, value in nawi.items()
    }
    original = _fit(panel, nawi)
    changed = _fit(contaminated, altered_nawi)
    assert _non_gate_signature(original) == _non_gate_signature(changed)
    assert (
        original.q_invariant_fit_signature_sha256
        == changed.q_invariant_fit_signature_sha256
    )
    for correlated in (False, True):
        left_gen, left = _initial(original, correlated=correlated)
        right_gen, right = _initial(changed, correlated=correlated)
        left_rng, right_rng = np.random.default_rng(71), np.random.default_rng(
            71
        )
        for year in range(BOUNDARY + 1, BOUNDARY + 7):
            left = _advance(left_gen, left, year, left_rng)
            right = _advance(right_gen, right, year, right_rng)
            _assert_frames(left, right)
            assert (
                left_rng.bit_generator.state == right_rng.bit_generator.state
            )


@PROPERTY
@given(
    seed=st.integers(0, 100),
    correlated=st.booleans(),
    horizon=st.integers(4, 8),
)
def test_t7_source_year_query_features_and_exact_restart(
    seed, correlated, horizon
):
    panel, nawi = _history(seed)
    # Later realized values deliberately contradict the frozen projection.
    nawi.update({year: 3.0 for year in range(BOUNDARY + 1, BOUNDARY + 9)})
    fitted = _fit(panel, nawi)
    generator, frame = _initial(fitted, correlated=correlated)
    frame = frame.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    rng = np.random.default_rng(seed)
    restart = None
    saw_current_status_switch = False
    with pytest.MonkeyPatch.context() as patch:
        calls = _observe_queries(patch)
        for offset in range(1, horizon + 1):
            year = BOUNDARY + offset
            calls.clear()
            previous = frame.copy(deep=True)
            frame = _advance(generator, frame, year, rng)
            if year % 2:
                assert calls == []
                np.testing.assert_array_equal(
                    frame["earnings"], previous["earnings"]
                )
            else:
                ordered = previous.sort_values("person_id", kind="stable")
                divisor = generator.wage_index.normalization_index(year - 2)
                if year == BOUNDARY + 2:
                    assert divisor == nawi[BOUNDARY]
                else:
                    assert divisor == generator.wage_index.projected(year - 2)
                    assert divisor != nawi[year - 2]
                assert len(calls) == 2
                for call, zero_anchor in zip(
                    calls, (False, True), strict=True
                ):
                    mask = (
                        ordered["realized_earn_2014"] == 0
                    ).to_numpy() == zero_anchor
                    expected_gate = (
                        generator.zero_anchor_gate
                        if zero_anchor
                        else generator.shared_gate
                    )
                    assert call[0] is expected_gate
                    np.testing.assert_array_equal(
                        call[1],
                        ordered.loc[mask, "earnings"].to_numpy() / divisor,
                    )
                    np.testing.assert_array_equal(
                        call[2], ordered.loc[mask, "age"].to_numpy() + 1
                    )
                saw_current_status_switch |= bool(
                    np.any(
                        (ordered["earnings"] == 0)
                        != (ordered["realized_earn_2014"] == 0)
                    )
                )
            if restart is not None:
                restored_gen, restored_frame, restored_rng = restart
                restored_frame = _advance(
                    restored_gen, restored_frame, year, restored_rng
                )
                _assert_frames(frame, restored_frame)
                assert (
                    rng.bit_generator.state == restored_rng.bit_generator.state
                )
                restart = restored_gen, restored_frame, restored_rng
            if offset == 2:
                restart = pickle.loads(
                    pickle.dumps((generator, frame, rng), protocol=5)
                )
    assert saw_current_status_switch


def test_s1_owns_its_refit_and_preserves_registered_candidate3():
    panel, nawi = _history()
    assert set(REGISTRY) == {2, 3}
    assert REGISTRY[3] is CANDIDATE_3
    assert s1.CANDIDATE_S1.operations[:-1] == CANDIDATE_3.operations
    old = refit_earnings_chained_generator(
        panel,
        nawi,
        seed=37,
        boundary_year=BOUNDARY,
        candidate_spec=REGISTRY[3],
    )
    new = s1.refit_earnings_chained_generator(
        panel,
        nawi,
        seed=37,
        boundary_year=BOUNDARY,
    )
    assert type(old.generator) is v1.ForwardEarningsGenerator
    assert type(new.generator) is s1.ForwardEarningsGenerator
    assert old.adapter_spec_sha256 == EARNINGS_SPEC_SHA256
    assert new.adapter_spec_sha256 == s1.adapter_spec_sha256(
        EARNINGS_SPEC_SHA256
    )
    assert old.engine_candidate_id == CANDIDATE_3.candidate_id
    assert old.engine_candidate_spec_sha256 == CANDIDATE_3.sha256
    assert new.engine_candidate_id == s1.CANDIDATE_S1.candidate_id
    assert new.engine_candidate_spec_sha256 == s1.CANDIDATE_S1.sha256
    assert new.spec_registration == s1.SPEC_REGISTRATION
    for entry_point in (
        s1.fit_forward_earnings,
        s1.refit_earnings_chained_generator,
    ):
        with pytest.raises(ValueError, match="exact frozen candidate"):
            entry_point(panel, nawi, seed=37, candidate_spec=CANDIDATE_3)


def test_s1_refit_every_non_gate_field_equals_v1_for_identical_inputs():
    panel, nawi = _history()
    inputs = {
        "seed": 37,
        "boundary_year": BOUNDARY,
        "candidate_spec": s1.CANDIDATE_S1,
    }
    # The unchanged v1 fitter ignores the additional participation operation.
    # Identical declarations keep candidate id/spec metadata comparable too.
    old = refit_earnings_chained_generator(panel, nawi, **inputs)
    new = s1.refit_earnings_chained_generator(panel, nawi, **inputs)
    own_identity = {
        "spec_registration": s1.SPEC_REGISTRATION,
        "adapter_spec_sha256": s1.adapter_spec_sha256(EARNINGS_SPEC_SHA256),
    }
    gate_fields = {"shared_gate", "zero_anchor_gate"}
    assert fields(old.generator) == fields(new.generator)
    for field in fields(old):
        before, after = getattr(old, field.name), getattr(new, field.name)
        if field.name in own_identity:
            assert after == own_identity[field.name]
        elif field.name in gate_fields:
            assert before is getattr(old.generator, field.name)
            assert after is getattr(new.generator, field.name)
            assert before is not after
        elif field.name == "generator":
            assert type(before) is v1.ForwardEarningsGenerator
            assert type(after) is s1.ForwardEarningsGenerator
            for component in fields(before):
                if component.name not in gate_fields:
                    _assert_exact_state(
                        getattr(before, component.name),
                        getattr(after, component.name),
                    )
        elif field.name == "q_invariant_fit_signature_sha256":
            # This hash contains the participation-gate fingerprint. Check
            # each complete digest and its exactly equal non-gate component.
            assert before == v1._q_invariant_fit_signature(
                old.generator,
                old.estimation_panel,
                old.forward_pairs,
                old.anchors,
                old.u_w_diagnostics,
            )
            assert after == s1._fit_signature(new)
            assert _non_gate_signature(old) == _non_gate_signature(new)
        else:
            _assert_exact_state(before, after)
    assert new.engine_candidate_id == old.engine_candidate_id
    assert new.engine_candidate_spec_sha256 == old.engine_candidate_spec_sha256
