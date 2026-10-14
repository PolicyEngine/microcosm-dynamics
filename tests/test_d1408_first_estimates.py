"""Invented support-bound invariants; no PSID file is opened."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from d1408_first_estimates import (  # noqa: E402
    complete_stock_support,
    publish_replay_group,
    window_probability,
    window_support,
)


def test_window_support_uses_strict_48_month_boundary():
    assert window_support([69, 70], 1935, 780) == [False, True]
    assert window_support([69, 70], 1942, 790) == [False, True]


@given(st.integers(1917, 1942), st.integers(780, 790))
def test_window_support_is_only_age70_on_registered_pmf(birth, fra):
    assert window_support(list(range(62, 71)), birth, fra) == [False] * 8 + [
        True
    ]


@given(
    st.one_of(st.integers(1800, 1916), st.integers(1943, 2020)),
    st.integers(0, 100),
    st.integers(780, 804),
)
def test_window_support_excludes_production_ineligible_cohorts(
    birth, age, fra
):
    assert window_support([age], birth, fra) == [False]


@given(st.integers(0, 1000))
def test_expected_mass_keeps_unaffected_probability_in_denominator(numerator):
    probability = numerator / 1000
    assert window_probability(
        [62, 70], [1 - probability, probability], 1935, 780
    ) == pytest.approx(probability, abs=1e-12)


@given(st.lists(st.integers(0, 1000), min_size=9, max_size=9))
def test_expected_mass_is_bounded_and_order_independent(mass):
    total = sum(mass)
    if total == 0:
        mass = [1] * 9
        total = 9
    ages = list(range(62, 71))
    probabilities = [value / total for value in mass]
    actual = window_probability(ages, probabilities, 1935, 780)
    reversed_actual = window_probability(
        list(reversed(ages)), list(reversed(probabilities)), 1935, 780
    )
    assert 0 <= actual <= 1
    assert actual == reversed_actual
    assert actual == window_probability(ages, probabilities, 1935, 780)
    assert actual == pytest.approx(probabilities[-1], abs=1e-12)


@given(st.lists(st.integers(62, 70), min_size=1, max_size=9, unique=True))
def test_stock_replay_requires_strict_complete_support(ages):
    boundary = max(ages)
    assert not complete_stock_support(boundary, ages)
    assert complete_stock_support(boundary + 1, ages)
    assert complete_stock_support(boundary + 1, list(reversed(ages)))


@given(st.integers(0, 200))
def test_empty_stock_support_cannot_be_replayed(exposure):
    assert not complete_stock_support(exposure, [])


@given(st.integers(0, 30))
def test_small_complementary_cell_withholds_replay_subtotal(difference):
    original = {
        "people": 20,
        "worker_records": None,
        "weight": 1000.0,
        "roster_weight_share": 0.1,
    }
    result = publish_replay_group(original, difference)
    assert original["people"] == 20
    assert result == publish_replay_group(original, difference)
    if 0 < difference < 10:
        assert all(
            result[key] == "suppressed_complementary"
            for key in (
                "people",
                "worker_records",
                "weight",
                "roster_weight_share",
            )
        )
    else:
        assert result == original


@pytest.mark.parametrize(
    "ages, probability",
    [
        ([62, 70], [1]),
        ([62, 70], [-0.1, 1.1]),
        ([62, 70], [0.1, 0.1]),
        ([62, 70], [float("nan"), 1]),
        ([62, 70], [0, float("inf")]),
    ],
)
@given(birth=st.integers(1800, 2020), fra=st.integers(780, 804))
def test_invalid_distribution_refuses_before_computing_mass(
    ages, probability, birth, fra
):
    with pytest.raises(ValueError):
        window_probability(ages, probability, birth, fra)
