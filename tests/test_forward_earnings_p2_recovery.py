"""Frozen P2 gate recovery and counterexample on independent invented panels."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from scipy.stats import t

from populace_dynamics.engine.forward_earnings import (
    _default_qrf_factory,
    _forward_pairs,
    _gate_sign_draw,
)
from populace_dynamics.engine.forward_earnings_p2_v1 import (
    construct_gate_view,
    draw_p2_sign,
    fit_p2_gate,
    query_gate_probabilities,
)

# P2 fits through populace-fit, which pins scikit-learn below 1.9 and lives
# in its own environment; without it these tests skip, as the repository's
# other populace-fit tests do.
pytest.importorskip("populace.fit")

BOUNDARY = 2000
PERSONS = 8192
PANELS = 32
GATE_UNIFORMS = 65536
PROBE_CURRENT = np.asarray([0.0, 0.0, 100.0, 100.0])
PROBE_OLDER = np.asarray([0.0, 100.0, 0.0, 100.0])
PROBE_NAMES = (
    "p2_00",
    "p2_01",
    "p2_10",
    "p2_11",
    "v1_current0_q0false",
    "v1_current0_q0true",
    "v1_current1_q0false",
    "v1_current1_q0true",
)
TRANSITION = np.asarray([[0.6, 0.4], [0.1, 0.9]])


def _rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


def _panel(states: np.ndarray, years: np.ndarray) -> pd.DataFrame:
    """Materialize the fixed persons, nominal amounts, ages and weights."""
    return pd.DataFrame(
        {
            "person_id": np.repeat(np.arange(PERSONS), len(years)),
            "period": np.tile(years, PERSONS),
            "earnings": 100.0 * states.astype(np.float64).ravel(),
            "age": 40.0,
            "weight": 1.0,
            "nawi": 1.0,
        }
    )


def _second_order_panel(seed: int) -> pd.DataFrame:
    generator = _rng(seed)
    initial = generator.random((PERSONS, 2)) < 0.5
    previous, current = initial[:, 0], initial[:, 1]
    probability = np.asarray([[0.20, 0.70], [0.60, 0.90]])
    for _ in range(256):
        following = (
            generator.random(PERSONS)
            < probability[current.astype(int), previous.astype(int)]
        )
        previous, current = current, following
    states = [current.copy()]
    for _ in range(8):
        following = (
            generator.random(PERSONS)
            < probability[current.astype(int), previous.astype(int)]
        )
        previous, current = current, following
        states.append(current.copy())
    return _panel(
        np.column_stack(states), np.arange(BOUNDARY - 16, BOUNDARY + 1, 2)
    )


def _first_order_panel(seed: int, length: int) -> pd.DataFrame:
    generator = _rng(seed)
    current = generator.random(PERSONS) < 0.8
    states = [current.copy()]
    for _ in range(length):
        current = (
            generator.random(PERSONS) < TRANSITION[current.astype(int), 1]
        )
        states.append(current.copy())
    return _panel(
        np.column_stack(states),
        np.arange(BOUNDARY - 2 * length, BOUNDARY + 1, 2),
    )


def _heterogeneity_panel(seed: int) -> pd.DataFrame:
    generator = _rng(seed)
    high_type = np.arange(PERSONS) % 2 == 0
    probability = np.where(high_type, 0.9, 0.1)
    ordinary = generator.random((PERSONS, 9)) < probability[:, None]
    return _panel(
        np.column_stack([ordinary, high_type]),
        np.append(np.arange(BOUNDARY - 20, BOUNDARY - 3, 2), BOUNDARY),
    )


def _fit_gates(
    panel: pd.DataFrame, *, seed: int, selected_population_probe: bool
) -> tuple[Any, Any, Any]:
    """Construct exactly v1's admitted pairs before adding the P2 view."""
    cutoff = panel.loc[
        (panel["period"] <= BOUNDARY) & (panel["weight"] > 0)
    ].sort_values(["person_id", "period"], ignore_index=True)
    estimation = cutoff.loc[cutoff["age"].between(25, 64)].copy()
    estimation = estimation.sort_values(
        ["person_id", "period"], ignore_index=True
    )
    anchors = cutoff.loc[cutoff["period"] == BOUNDARY]
    pairs = _forward_pairs(estimation)
    pairs = pairs.loc[
        pairs["person_id"].isin(anchors["person_id"])
    ].reset_index(drop=True)
    gate_view = construct_gate_view(pairs, cutoff)
    pd.testing.assert_frame_equal(
        gate_view.loc[:, pairs.columns], pairs, check_exact=True
    )
    zero_ids = set(anchors.loc[anchors["earnings"] == 0, "person_id"])
    if selected_population_probe:
        # This column is provenance for the specified T3 population mutation.
        gate_view["anchor_zero"] = gate_view["person_id"].isin(zero_ids)
    p2_gate = fit_p2_gate(gate_view, seed=seed)
    fit_kwargs = {
        "predictors": ["earnings", "age_tp2"],
        "targets": ["earnings_tp2"],
        "weights": "weight_tp2",
    }
    shared_gate = _default_qrf_factory(seed=seed).fit(pairs, **fit_kwargs)
    zero_pairs = pairs.loc[pairs["person_id"].isin(zero_ids)].reset_index(
        drop=True
    )
    zero_gate = _default_qrf_factory(seed=seed).fit(zero_pairs, **fit_kwargs)
    return p2_gate, shared_gate, zero_gate


def _v1_gate_for_probe(
    shared_gate: Any, zero_gate: Any, anchor_zero: bool
) -> Any:
    # Frozen T7 mutation: use shared_gate for zero-anchor persons as well.
    gate = zero_gate if anchor_zero else shared_gate
    return gate


def _v1_probability(gate: Any, current: np.ndarray) -> np.ndarray:
    model = gate._target_models["earnings_tp2"]
    features = pd.DataFrame({"earnings": current, "age_tp2": 40.0})
    values = features.loc[:, list(model.columns)].to_numpy(dtype=np.float64)
    probabilities = np.asarray(model.gate.predict_proba(values))
    positive = np.flatnonzero(np.asarray(model.gate.classes_) == 1)
    return probabilities[:, positive[0]]


def _probabilities(
    p2_gate: Any, shared_gate: Any, zero_gate: Any
) -> np.ndarray:
    classes, probabilities = query_gate_probabilities(
        p2_gate, PROBE_CURRENT, np.full(4, 40.0), PROBE_OLDER
    )
    positive = np.flatnonzero(np.asarray(classes) == 1)
    p2_probability = probabilities[:, positive[0]]
    v1_probability = [
        _v1_probability(
            _v1_gate_for_probe(shared_gate, zero_gate, anchor_zero),
            np.asarray([float(100 * current)]),
        )[0]
        for current in (0, 1)
        for anchor_zero in (False, True)
    ]
    return np.append(p2_probability, v1_probability)


def _monte_carlo_errors(
    panel_seed: int,
    gates: tuple[Any, Any, Any],
    probabilities: np.ndarray,
) -> np.ndarray:
    p2_gate, shared_gate, zero_gate = gates
    errors = []
    ages = np.full(GATE_UNIFORMS, 40.0)
    for probe_index in range(8):
        generator = np.random.Generator(
            np.random.PCG64(
                np.random.SeedSequence([panel_seed + 1000000, probe_index])
            )
        )
        uniforms = generator.random(GATE_UNIFORMS)
        if probe_index < 4:
            signs = draw_p2_sign(
                p2_gate,
                np.full(GATE_UNIFORMS, PROBE_CURRENT[probe_index]),
                ages,
                np.full(GATE_UNIFORMS, PROBE_OLDER[probe_index]),
                uniforms,
            )
        else:
            current, anchor_zero = divmod(probe_index - 4, 2)
            gate = _v1_gate_for_probe(
                shared_gate, zero_gate, bool(anchor_zero)
            )
            signs = _gate_sign_draw(
                gate,
                np.full(GATE_UNIFORMS, float(100 * current)),
                ages,
                uniforms,
            )
        errors.append(float(np.mean(signs == 1) - probabilities[probe_index]))
    return np.asarray(errors)


def _summary(values: np.ndarray, *, critical: float) -> dict[str, Any]:
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1))
    half_width = critical * sd / np.sqrt(PANELS)
    return {
        "mean": mean,
        "between_panel_sd": sd,
        "rmse": float(np.sqrt(np.mean(values**2))),
        "range": [float(np.min(values)), float(np.max(values))],
        "confidence_interval": [mean - half_width, mean + half_width],
    }


def _recovery_summary(
    fitted: np.ndarray, oracle: np.ndarray
) -> list[dict[str, Any]]:
    critical = float(t.ppf(1 - 0.01 / (2 * 36), PANELS - 1))
    summaries = []
    for index, expected in enumerate(oracle):
        errors = fitted[:, index] - expected
        summary = _summary(errors, critical=critical)
        summary.update(
            {
                "probe": PROBE_NAMES[index],
                "oracle": float(expected),
                "mean_absolute_error": float(np.mean(np.abs(errors))),
                "absolute_errors_at_most_0.04": int(
                    np.count_nonzero(np.abs(errors) <= 0.04)
                ),
                "maximum_absolute_error": float(np.max(np.abs(errors))),
            }
        )
        summaries.append(summary)
    return summaries


def _assert_recovery(report: dict[str, Any]) -> None:
    for summary in report["probability_recovery"]:
        assert summary["mean_absolute_error"] <= 0.015, summary
        assert summary["absolute_errors_at_most_0.04"] >= 31, summary
        assert summary["maximum_absolute_error"] <= 0.08, summary
        lower, upper = summary["confidence_interval"]
        assert lower >= -0.02 and upper <= 0.02, summary
    assert report["maximum_absolute_monte_carlo_error"] <= 0.01, report


def _experiment(
    *,
    panel_factory: Callable[[int], pd.DataFrame],
    scenario: str,
    seed_offset: int,
    oracle: np.ndarray,
    selected_population_probe: bool = False,
    exact_v1_distinction: bool = False,
) -> tuple[dict[str, Any], np.ndarray]:
    fitted = []
    monte_carlo = []
    seeds = []
    for replicate in range(PANELS):
        panel_seed = 20261022 + seed_offset + replicate
        seeds.append(panel_seed)
        gates = _fit_gates(
            panel_factory(panel_seed),
            seed=5200 + replicate,
            selected_population_probe=selected_population_probe,
        )
        probabilities = _probabilities(*gates)
        fitted.append(probabilities)
        monte_carlo.append(
            _monte_carlo_errors(panel_seed, gates, probabilities)
        )
        if exact_v1_distinction:
            for gate in gates[1:]:
                matched = _v1_probability(gate, PROBE_CURRENT)
                assert matched[0] == matched[1]
                assert matched[2] == matched[3]
    fitted_array = np.asarray(fitted)
    monte_carlo_array = np.asarray(monte_carlo)
    return (
        {
            "scenario": scenario,
            "panels": PANELS,
            "persons_per_panel": PERSONS,
            "panel_seeds": seeds,
            "estimator_seeds": list(range(5200, 5200 + PANELS)),
            "probe_names": list(PROBE_NAMES),
            "fitted_probabilities": fitted_array.tolist(),
            "probability_recovery": _recovery_summary(fitted_array, oracle),
            "monte_carlo_errors": monte_carlo_array.tolist(),
            "maximum_absolute_monte_carlo_error": float(
                np.max(np.abs(monte_carlo_array))
            ),
            "uniforms_per_probe": GATE_UNIFORMS,
        },
        fitted_array,
    )


def _write_report(tmp_path: Path, report: dict[str, Any]) -> None:
    destination = tmp_path / f"{report['scenario']}.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"P2 recovery report: {destination}")
    for summary in report["probability_recovery"]:
        print(f"{report['scenario']} {summary}")
    print(
        f"{report['scenario']} maximum absolute Monte Carlo error: "
        f"{report['maximum_absolute_monte_carlo_error']}"
    )


def test_t2_second_order_recovery_and_exact_v1_distinction(
    tmp_path: Path,
) -> None:
    report, _ = _experiment(
        panel_factory=_second_order_panel,
        scenario="t2_second_order",
        seed_offset=1000 * 2,
        oracle=np.asarray([0.20, 0.70, 0.60, 0.90]),
        exact_v1_distinction=True,
    )
    _write_report(tmp_path, report)
    _assert_recovery(report)


def _selected_oracle(length: int, source: int) -> float:
    numerator = sum(
        np.linalg.matrix_power(TRANSITION, power)[1, 0]
        for power in range(length)
    )
    denominator = sum(
        np.linalg.matrix_power(TRANSITION, power + 1)[source, 0]
        for power in range(length)
    )
    return float(TRANSITION[source, 1] * numerator / denominator)


@pytest.mark.parametrize("length", [4, 8, 16])
def test_t3_retrospective_selection_recovery(
    tmp_path: Path, length: int
) -> None:
    selected_zero = _selected_oracle(length, 0)
    selected_one = _selected_oracle(length, 1)
    oracle = np.asarray(
        [0.4, 0.4, 0.9, 0.9, 0.4, selected_zero, 0.9, selected_one]
    )
    report, fitted = _experiment(
        panel_factory=lambda seed: _first_order_panel(seed, length),
        scenario=f"t3_selection_L{length}",
        seed_offset=1000 * 3 + 100 * [4, 8, 16].index(length),
        oracle=oracle,
        selected_population_probe=True,
    )
    report["ordinary_minus_selected_contrasts"] = {
        "source_zero": 0.4 - selected_zero,
        "source_one": 0.9 - selected_one,
    }
    report["observed_ordinary_minus_selected_contrasts"] = {
        name: {
            "mean": float(np.mean(values)),
            "between_panel_sd": float(np.std(values, ddof=1)),
            "range": [float(np.min(values)), float(np.max(values))],
        }
        for name, values in (
            ("source_zero", fitted[:, 4] - fitted[:, 5]),
            ("source_one", fitted[:, 6] - fitted[:, 7]),
        )
    }
    _write_report(tmp_path, report)
    _assert_recovery(report)


def _counterexample_risks(fitted: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p2_risk = np.zeros(PANELS)
    v1_risk = np.zeros(PANELS)
    for probability, anchor_zero in ((0.9, False), (0.1, True)):
        for current in (0, 1):
            current_weight = probability if current else 1 - probability
            for previous in (0, 1):
                previous_weight = probability if previous else 1 - probability
                weight = 0.5 * current_weight * previous_weight
                variance = probability * (1 - probability)
                p2_forecast = fitted[:, 2 * current + previous]
                v1_forecast = fitted[:, 4 + 2 * current + int(anchor_zero)]
                p2_risk += weight * (
                    variance + (p2_forecast - probability) ** 2
                )
                v1_risk += weight * (
                    variance + (v1_forecast - probability) ** 2
                )
    return p2_risk, v1_risk


def test_t7_persistent_heterogeneity_counterexample(tmp_path: Path) -> None:
    report, fitted = _experiment(
        panel_factory=_heterogeneity_panel,
        scenario="t7_persistent_heterogeneity",
        seed_offset=1000 * 7,
        oracle=np.asarray(
            [
                0.1097560975609756,
                0.5,
                0.5,
                0.8902439024390244,
                0.18,
                0.1,
                0.82,
                0.1,
            ]
        ),
    )
    p2_risk, v1_risk = _counterexample_risks(fitted)
    paired_loss = p2_risk - v1_risk
    critical = float(t.ppf(0.995, PANELS - 1))
    loss = _summary(paired_loss, critical=critical)
    loss["one_sided_99pct_lower_bound"] = float(
        np.mean(paired_loss)
        - t.ppf(0.99, PANELS - 1)
        * np.std(paired_loss, ddof=1)
        / np.sqrt(PANELS)
    )
    report["counterexample"] = {
        "measurement": (
            "Exact enumeration of eight (type,current,previous) states; "
            "equal type prevalence, independent ordinary recent states, "
            "and Bernoulli outcome variance included."
        ),
        "p2_risks": p2_risk.tolist(),
        "v1_risks": v1_risk.tolist(),
        "paired_losses": paired_loss.tolist(),
        "mean_p2_risk": float(np.mean(p2_risk)),
        "mean_v1_risk": float(np.mean(v1_risk)),
        "paired_loss": loss,
        "analytic_loss": 0.0063219512195122,
    }
    _write_report(tmp_path, report)
    print(
        f"T7 expected Brier risk and paired loss: {report['counterexample']}"
    )
    assert loss["one_sided_99pct_lower_bound"] > 0, loss
    assert abs(loss["mean"] - 0.0063219512195122) <= 0.003, loss
    _assert_recovery(report)
