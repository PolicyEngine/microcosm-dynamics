"""Declared participation-gate experiments on invented panels.

These experiments use the production gate-fitting seam. Their independent
historical pairs do not supply the long positive histories needed for the
unrelated permanent-score estimator; T4 checks complete refits separately.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from populace_dynamics.engine import forward_earnings as v1
from populace_dynamics.engine import forward_earnings_s1_v1 as s1

BOUNDARY = 2020
SOURCE_YEARS = (2000, 2004, 2008)
SOURCE_AGES = np.arange(25, 65, 5, dtype=np.float64)
TARGET_AGES = SOURCE_AGES + 2
RELATIVE_LEVELS = np.asarray([0.0, 0.5, 1.0, 2.0])
RELATIVE_PROBABILITIES = np.asarray([0.15, 0.35, 0.65, 0.85])
REPLICATIONS = 100
FIT_ABSOLUTE_ALLOWANCE = 0.15
FIT_RMSE_ALLOWANCE = 0.075
MC_DRAWS_PER_CELL = 20_000
MC_FAMILY_ERROR = 0.001
N_RECOVERY_CELLS = 2 * len(RELATIVE_LEVELS) * len(TARGET_AGES)
MC_ALLOWANCE = np.sqrt(
    np.log(2 * N_RECOVERY_CELLS / MC_FAMILY_ERROR) / (2 * MC_DRAWS_PER_CELL)
)


def _invented_panel(
    *, seed: int, nominal_threshold: bool
) -> tuple[pd.DataFrame, dict[int, float]]:
    """Make independent historical pairs with separate boundary anchors."""
    rng = np.random.default_rng(seed)
    nawi = {
        year: float(2 ** ((year - 2000) / 2))
        for year in range(1998, BOUNDARY + 1)
    }
    rows: list[dict[str, float | int]] = []
    person_id = 0
    for source_year in SOURCE_YEARS:
        for source_age in SOURCE_AGES:
            for level, relative_probability in zip(
                RELATIVE_LEVELS, RELATIVE_PROBABILITIES, strict=True
            ):
                source_earnings = float(level * nawi[source_year])
                probability = (
                    (0.85 if source_earnings >= 8.0 else 0.15)
                    if nominal_threshold
                    else float(relative_probability)
                )
                for positive_anchor in (False, True):
                    participating = rng.random(REPLICATIONS) < probability
                    for positive in participating:
                        rows.extend(
                            [
                                {
                                    "person_id": person_id,
                                    "period": source_year,
                                    "earnings": source_earnings,
                                    "age": float(source_age),
                                    "weight": 1.0,
                                },
                                {
                                    "person_id": person_id,
                                    "period": source_year + 2,
                                    "earnings": (
                                        nawi[source_year + 2]
                                        if positive
                                        else 0.0
                                    ),
                                    "age": float(source_age + 2),
                                    "weight": 1.0,
                                },
                                {
                                    "person_id": person_id,
                                    "period": BOUNDARY,
                                    "earnings": (
                                        nawi[BOUNDARY]
                                        if positive_anchor
                                        else 0.0
                                    ),
                                    "age": float(
                                        source_age + BOUNDARY - source_year
                                    ),
                                    "weight": 1.0,
                                },
                            ]
                        )
                        person_id += 1
    return pd.DataFrame(rows), nawi


def _positive_probability(
    gate, earnings: np.ndarray, ages: np.ndarray
) -> np.ndarray:
    target = gate._target_models["earnings_tp2"]
    features = pd.DataFrame({"earnings": earnings, "age_tp2": ages})
    values = features.loc[:, list(target.columns)].to_numpy(dtype=np.float64)
    classes = np.asarray(target.gate.classes_)
    probability = target.gate.predict_proba(values)
    return np.asarray(probability[:, classes == 1]).reshape(-1)


def _fit_gates(
    panel: pd.DataFrame,
    nawi: dict[int, float],
    *,
    seed: int,
    successor: bool,
) -> dict[str, object]:
    """Fit the production gate seam without unrelated score estimation."""
    cutoff = panel.loc[
        (panel["period"] <= BOUNDARY) & (panel["weight"] > 0)
    ].copy()
    estimation = cutoff.loc[cutoff["age"].between(25, 64)].sort_values(
        ["person_id", "period"]
    )
    anchors = cutoff.loc[cutoff["period"] == BOUNDARY]
    anchor_ids = set(anchors["person_id"].astype(int))
    zero_ids = set(
        anchors.loc[anchors["earnings"] == 0, "person_id"].astype(int)
    )
    pairs = v1._forward_pairs(estimation)
    pairs = pairs.loc[pairs["person_id"].isin(anchor_ids)].reset_index(
        drop=True
    )
    assert len(pairs) == 19_200
    zero_pairs = pairs.loc[pairs["person_id"].isin(zero_ids)].reset_index(
        drop=True
    )
    assert len(zero_pairs) == 9_600
    kwargs = {
        "predictors": ["earnings", "age_tp2"],
        "targets": ["earnings_tp2"],
        "weights": "weight_tp2",
    }
    gates = {}
    for name, selected in (("shared", pairs), ("zero_anchor", zero_pairs)):
        model = v1._default_qrf_factory(seed=seed)
        if successor:
            gates[name] = (
                s1._GateFittingModel(model, nawi)
                .fit(selected, **kwargs)
                .fitted
            )
        else:
            gates[name] = model.fit(selected, **kwargs)
    return gates


def test_t3_relative_stationary_participation_recovery():
    panel, nawi = _invented_panel(seed=7301, nominal_threshold=False)
    gates = _fit_gates(panel, nawi, seed=7311, successor=True)
    wage_index = v1.ProjectedWageIndex(
        actual=nawi, intercept=0.0, slope=0.0, boundary_year=BOUNDARY
    )
    levels = np.tile(RELATIVE_LEVELS, len(TARGET_AGES))
    ages = np.repeat(TARGET_AGES, len(RELATIVE_LEVELS))
    expected = np.tile(RELATIVE_PROBABILITIES, len(TARGET_AGES))
    results = {}
    probability_errors = []
    for name, mc_seed in (("shared", 7321), ("zero_anchor", 7322)):
        gate = gates[name]
        assert gate is not None
        probability = _positive_probability(gate, levels, ages)
        error = np.abs(probability - expected)
        rmse = float(np.sqrt(np.mean((probability - expected) ** 2)))
        assert float(error.max()) <= FIT_ABSOLUTE_ALLOWANCE
        probability_errors.append(probability - expected)
        uniforms = np.random.default_rng(mc_seed).random(
            len(levels) * MC_DRAWS_PER_CELL
        )
        signs = v1._gate_sign_draw(
            s1._GateQuery(gate, wage_index, BOUNDARY + 2),
            np.repeat(levels * nawi[BOUNDARY], MC_DRAWS_PER_CELL),
            np.repeat(ages, MC_DRAWS_PER_CELL),
            uniforms,
        ).reshape(len(levels), MC_DRAWS_PER_CELL)
        frequency = (signs == 1).mean(axis=1)
        assert (
            np.max(np.abs(frequency - expected))
            <= FIT_ABSOLUTE_ALLOWANCE + MC_ALLOWANCE
        )
        results[name] = {
            "max_absolute_probability_error": float(error.max()),
            "probability_rmse": rmse,
            "max_absolute_draw_frequency_error": float(
                np.max(np.abs(frequency - expected))
            ),
            "max_monte_carlo_error": float(
                np.max(np.abs(frequency - probability))
            ),
        }
    aggregate_rmse = float(
        np.sqrt(np.mean(np.concatenate(probability_errors) ** 2))
    )
    assert aggregate_rmse <= FIT_RMSE_ALLOWANCE
    results["aggregate_probability_rmse"] = aggregate_rmse
    print("T3 recovery: " + json.dumps(results, sort_keys=True))


def test_t6_fixed_nominal_threshold_counterexample():
    panel, nawi = _invented_panel(seed=7401, nominal_threshold=True)
    baseline = _fit_gates(panel, nawi, seed=7411, successor=False)
    successor = _fit_gates(panel, nawi, seed=7411, successor=True)
    nominal_levels = np.asarray([2.0, 4.0, 8.0, 16.0])
    levels = np.tile(nominal_levels, len(TARGET_AGES))
    ages = np.repeat(TARGET_AGES, len(nominal_levels))
    expected = np.where(levels >= 8.0, 0.85, 0.15)
    losses: dict[str, list[float]] = {"v1": [], "s1": []}
    for gate_name in ("shared", "zero_anchor"):
        for name, fitted, query_levels in (
            ("v1", baseline, levels),
            ("s1", successor, levels / nawi[BOUNDARY]),
        ):
            gate = fitted[gate_name]
            assert gate is not None
            probability = _positive_probability(gate, query_levels, ages)
            expected_brier = (
                expected * (1.0 - expected) + (probability - expected) ** 2
            )
            losses[name].extend(expected_brier.tolist())
    v1_loss = float(np.mean(losses["v1"]))
    s1_loss = float(np.mean(losses["s1"]))
    excess_loss = s1_loss - v1_loss
    print(
        "T6 expected Brier loss: "
        + json.dumps(
            {
                "v1": v1_loss,
                "s1": s1_loss,
                "s1_minus_v1": excess_loss,
                "s1_over_v1": s1_loss / v1_loss,
                "equal_weight_query_cells": len(losses["s1"]),
            },
            sort_keys=True,
        )
    )
    assert excess_loss > 0.05
