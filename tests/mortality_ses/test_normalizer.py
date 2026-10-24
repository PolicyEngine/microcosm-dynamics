"""Cell accounting tests using invented probabilities, risks and weights."""

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.engine.di_entitlement import _net_of_di_origin
from populace_dynamics.mortality_ses.normalizer import (
    CELL_LOG_COLUMNS,
    normalize_probabilities,
)


def normalize(
    base, risks, fixed=None, prescribed=None, weights=None, cells=None
):
    size = len(base)
    return normalize_probabilities(
        np.asarray(base),
        np.asarray(risks),
        np.zeros(size, dtype=bool) if fixed is None else np.asarray(fixed),
        np.asarray(base if prescribed is None else prescribed),
        [(2030, "male", 70)] * size if cells is None else cells,
        np.ones(size) if weights is None else np.asarray(weights),
    )


def test_invented_uncapped_cell_conserves_and_logs_counts():
    q, log = normalize_probabilities(
        np.array([0.2, 0.2, 0.2]),
        np.array([1.0, 2.0, 3.0]),
        np.array([True, False, False]),
        np.array([0.2, 0.2, 0.2]),
        [(2030, "female", 70)] * 3,
        np.array([1.0, 2.0, 1.0]),
        unclassified_counts={"unclassified_reference": np.array([0, 1, 2])},
    )
    np.testing.assert_allclose(q, [0.2, 0.2 * 2 * 3 / 7, 0.2 * 3 * 3 / 7])
    assert log.columns.tolist() == list(CELL_LOG_COLUMNS)
    cell = log.iloc[0]
    assert (cell.year, cell.sex, cell.age) == (2030, "female", 70)
    assert cell.persons == 3
    assert cell.fixed_persons == 1
    assert cell.weight == 4
    assert cell.fixed_weight == 1
    assert cell.baseline_expected_deaths == pytest.approx(0.8)
    assert cell.applied_expected_deaths == pytest.approx(0.8)
    assert cell.factor == pytest.approx(3 / 7)
    assert cell.clipped_persons == 0
    assert cell.clipping_residual == 0
    assert not cell.infeasible
    assert cell.unclassified_reference == 3
    assert cell.unclassified_refuse == 0


def test_iterative_capping_reallocates_invented_remaining_deaths():
    q, log = normalize([0.9, 0.9, 0.9], [1, 10, 100])
    np.testing.assert_allclose(q, [0.7, 1, 1], rtol=1e-12, atol=1e-12)
    assert log.iloc[0].clipped_persons == 2
    assert log.iloc[0].factor == pytest.approx(7 / 9)
    assert log.iloc[0].clipping_residual == pytest.approx(0, abs=1e-12)
    assert not log.iloc[0].infeasible


def test_fixed_deaths_above_invented_target_are_infeasible():
    q, log = normalize(
        [0.1, 0.1], [1, 3], fixed=[True, False], prescribed=[0.5, 0.1]
    )
    np.testing.assert_array_equal(q, [0.5, 0])
    assert log.iloc[0].infeasible
    assert log.iloc[0].clipping_residual == pytest.approx(-0.3)


def test_invented_target_beyond_free_positive_support_is_logged():
    q, log = normalize(
        [1, 0.1, 0],
        [1, 2, 10],
        fixed=[True, False, False],
        prescribed=[0, 0.1, 0],
    )
    np.testing.assert_array_equal(q, [0, 1, 0])
    assert log.iloc[0].infeasible
    assert log.iloc[0].clipping_residual == pytest.approx(0.1)


def test_equal_risks_preserve_baseline_bits_with_fixed_baseline_rows():
    baseline = np.array([0.0, 0.003, 0.25, 1.0])
    for risks in ([1] * 4, [1e-308] * 4, [1e308] * 4):
        q, log = normalize(
            baseline,
            risks,
            fixed=[True, False, False, True],
            weights=[0.0, 2.0, 7.0, 0.25],
        )
        np.testing.assert_array_equal(
            q.view(np.uint64), baseline.view(np.uint64)
        )
        assert not log.iloc[0].infeasible
        assert log.iloc[0].clipping_residual == 0


def test_finite_extreme_risks_do_not_underflow_positive_support():
    q, log = normalize([0.9, 0.9], [1e-308, 1e308])
    np.testing.assert_allclose(q, [0.8, 1], rtol=1e-12, atol=1e-12)
    assert not log.iloc[0].infeasible
    assert np.isfinite(log.iloc[0].factor)
    assert log.iloc[0].clipping_residual == pytest.approx(0, abs=1e-12)


def test_extreme_invented_products_retain_positive_probability_support():
    # The first free row's q*RR underflows float64, but its probability is
    # needed after the second free row caps.  Fixed rows fund the target.
    q, log = normalize(
        [0.8, 1e-300, 0.8],
        [1, 1e-300, 1e300],
        fixed=[True, False, False],
        prescribed=[0, 1e-300, 0.8],
    )
    np.testing.assert_allclose(q, [0, 0.6, 1], rtol=1e-12, atol=1e-12)
    assert not log.iloc[0].infeasible
    assert log.iloc[0].clipping_residual == pytest.approx(0, abs=1e-12)


def test_zero_baselines_and_zero_weights_remain_bounded():
    q, log = normalize([0, 0.4, 0.4], [9, 1, 3], weights=[1, 0, 1])
    np.testing.assert_allclose(q, [0, 0.4 / 3, 0.4])
    assert log.iloc[0].baseline_expected_deaths == pytest.approx(0.4)
    assert not log.iloc[0].infeasible
    zero_q, zero_log = normalize([0.2, 0.6], [1, 2], weights=[0, 0])
    assert np.all((zero_q >= 0) & (zero_q <= 1))
    assert zero_log.iloc[0].weight == 0
    assert zero_log.iloc[0].clipping_residual == 0


def test_weightless_support_counts_persons_equally():
    # With no weight on the free rows that can die, conservation says
    # nothing about the factor; zero would make these persons immortal.
    unit_q, unit_log = normalize([0.2, 0.6], [1, 2], weights=[1, 1])
    zero_q, zero_log = normalize([0.2, 0.6], [1, 2], weights=[0, 0])
    np.testing.assert_array_equal(zero_q, unit_q)
    np.testing.assert_allclose(zero_q, [0.8 / 7, 4.8 / 7])
    assert zero_log.iloc[0].factor == unit_log.iloc[0].factor
    assert zero_log.iloc[0].applied_expected_deaths == 0
    assert not zero_log.iloc[0].infeasible
    # Positive-weight rows with q_base = 0 leave the weightless row free.
    mixed_q, mixed_log = normalize([0, 0.2], [1, 2], weights=[1, 0])
    np.testing.assert_array_equal(mixed_q, [0, 0.2])
    assert mixed_log.iloc[0].factor == pytest.approx(0.5)
    # Positive-weight support still sets the factor alone.
    q, _ = normalize([0.2, 0.2], [1, 2], weights=[1, 0])
    np.testing.assert_allclose(q, [0.2, 0.4])


def test_weightless_support_uses_unit_weights_on_the_decimal_path():
    risks = [1e-90, 2e-90]
    unit_q, _ = normalize([0.2, 0.2], risks, weights=[1, 1])
    zero_q, zero_log = normalize([0.2, 0.2], risks, weights=[0, 0])
    np.testing.assert_array_equal(zero_q, unit_q)
    np.testing.assert_allclose(zero_q, [0.4 / 3, 0.8 / 3])
    assert not zero_log.iloc[0].infeasible


def test_cells_are_separate_and_sorted_and_inputs_are_unchanged():
    baseline = np.array([0.3, 0.1, 0.3, 0.1])
    risks = np.array([1.0, 1.0, 2.0, 2.0])
    fixed = np.zeros(4, dtype=bool)
    weights = np.array([2.0, 1.0, 2.0, 1.0])
    cells = [(2031, "male", 71), (2030, "female", 70)] * 2
    before = [x.copy() for x in (baseline, risks, fixed, weights)]
    q, log = normalize_probabilities(
        baseline, risks, fixed, baseline, cells, weights
    )
    np.testing.assert_allclose(q, [0.2, 1 / 15, 0.4, 2 / 15])
    assert log[["year", "sex", "age"]].values.tolist() == [
        [2030, "female", 70],
        [2031, "male", 71],
    ]
    for actual, original in zip(
        (baseline, risks, fixed, weights), before, strict=True
    ):
        np.testing.assert_array_equal(actual, original)


def test_empty_input_has_declared_log_schema():
    q, log = normalize([], [])
    assert q.shape == (0,)
    assert log.empty
    assert list(log.columns) == list(CELL_LOG_COLUMNS)


@pytest.mark.parametrize("bad_risk", [0, -1, np.nan, np.inf, -np.inf])
def test_refuses_nonpositive_or_nonfinite_invented_risks(bad_risk):
    with pytest.raises(ValueError, match="relative risks"):
        normalize([0.2], [bad_risk])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("q_base", [1.1], "baseline probabilities"),
        ("fixed_probabilities", [-0.1], "fixed probabilities"),
        ("weights", [-1], "weights"),
        ("weights", [np.inf], "weights"),
        ("fixed_mask", [1], "boolean"),
        ("cell_ids", [], "cell_ids"),
        ("cell_ids", [(2030, "male")], "triples"),
        ("cell_ids", [(2030, None, 70)], "missing"),
        ("relative_risk", [[1]], "one-dimensional"),
    ],
)
def test_refuses_invalid_accounting_inputs(field, value, message):
    arguments = dict(
        q_base=[0.2],
        relative_risk=[1],
        fixed_mask=np.array([False]),
        fixed_probabilities=[0.2],
        cell_ids=[(2030, "male", 70)],
        weights=[1],
    )
    arguments[field] = value
    with pytest.raises(ValueError, match=message):
        normalize_probabilities(**arguments)


@pytest.mark.parametrize(
    "counts", [{"weight": [1]}, {"missing": [-1]}, {"missing": [0.5]}]
)
def test_refuses_invalid_unclassified_counts(counts):
    with pytest.raises(ValueError, match="count"):
        normalize_probabilities(
            [0.2],
            [1],
            np.array([False]),
            [0.2],
            [(2030, "male", 70)],
            [1],
            unclassified_counts=counts,
        )


def test_matches_di_netting_arithmetic_without_capping():
    baseline = np.array([0.2, 0.2, 0.2, 0.1, 0.1])
    fixed = np.array([True, False, False, True, False])
    prescribed = np.array([0.3, 0.2, 0.2, 0.05, 0.1])
    weights = np.array([1, 2, 3, 2, 4])
    sexes = np.array([0, 0, 0, 1, 1])
    ages = np.array([70, 70, 70, 71, 71])
    actual, log = normalize(
        baseline,
        np.ones(5),
        fixed=fixed,
        prescribed=prescribed,
        weights=weights,
        cells=list(zip([2030] * 5, sexes, ages, strict=True)),
    )
    expected, _ = _net_of_di_origin(
        prescribed, baseline, fixed, sexes, ages, weights, [(70, 70), (71, 71)]
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
    assert not log.infeasible.any()
    assert not log.clipped_persons.any()


def test_intended_iterative_capping_differs_from_adapters_single_clip():
    # Invented heterogeneous baselines make the adapter's single clip bind.
    baseline = np.array([0.9, 0.9, 0.1])
    fixed = np.array([True, False, False])
    prescribed = np.array([0.1, 0.9, 0.1])
    actual, log = normalize(
        baseline, [1, 1, 1], fixed=fixed, prescribed=prescribed
    )
    expected, _ = _net_of_di_origin(
        prescribed,
        baseline,
        fixed,
        np.zeros(3, dtype=int),
        np.full(3, 70),
        np.ones(3),
        [(70, 70)],
    )
    np.testing.assert_allclose(actual, [0.1, 1, 0.8], atol=1e-12)
    assert np.sum(actual) == pytest.approx(np.sum(baseline), abs=1e-12)
    assert np.sum(expected) < np.sum(baseline)
    assert log.iloc[0].clipped_persons == 1


def test_repeat_calls_are_deterministic_in_probabilities_and_log():
    arguments = ([0.8, 0.8, 0.8], [1, 3, 20])
    first_q, first_log = normalize(*arguments)
    second_q, second_log = normalize(*arguments)
    np.testing.assert_array_equal(first_q, second_q)
    pd.testing.assert_frame_equal(first_log, second_log)
