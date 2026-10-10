"""EPUF's measurement operator: status invariants on every input."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.harness.epuf_operator import (
    disclosure_constants,
    epuf_measure,
    rounding_base,
    wage_base,
)

YEARS = sorted(disclosure_constants())
year_strategy = st.sampled_from(YEARS)
earnings_strategy = st.lists(
    st.floats(min_value=-1e5, max_value=5e5, allow_nan=False),
    min_size=1,
    max_size=40,
)


def test_constants_cover_1951_to_2006():
    assert YEARS == list(range(1951, 2007))
    assert wage_base(1951) == 3_600
    assert wage_base(2006) == 94_200
    with pytest.raises(ValueError, match="1951-2006"):
        wage_base(2007)


def test_worked_values_for_1998():
    # 1998: wage base 68,400, bottom code 57, band (67,400, 68,400) -> 68,001.
    values = np.array(
        [-5, 0, 50, 99.9, 100, 112, 990, 1049, 1050, 49_960, 67_400]
    )
    assert epuf_measure(values, 1998).tolist() == [
        0,
        0,
        57,
        57,
        100,
        100,
        1_000,
        1_000,
        1_100,
        50_000,
        67_000,
    ]
    band = epuf_measure(np.array([67_401, 68_000, 68_399]), 1998)
    assert band.tolist() == [68_001, 68_001, 68_001]
    assert epuf_measure(np.array([68_400, 1e6]), 1998).tolist() == [
        68_400,
        68_400,
    ]


def test_missing_earnings_and_unknown_years_are_refused():
    with pytest.raises(ValueError, match="missing"):
        epuf_measure(np.array([1.0, np.nan]), 1998)
    with pytest.raises(ValueError, match="1951-2006"):
        epuf_measure(np.array([1.0]), 2010)


@settings(max_examples=300, deadline=None)
@given(values=earnings_strategy, year=year_strategy)
def test_output_stays_between_zero_and_the_wage_base(values, year):
    out = epuf_measure(np.array(values), year)
    assert (out >= 0).all()
    assert (out <= wage_base(year)).all()


@settings(max_examples=300, deadline=None)
@given(values=earnings_strategy, year=year_strategy)
def test_positive_status_is_preserved(values, year):
    values = np.array(values)
    out = epuf_measure(values, year)
    assert ((out > 0) == (values > 0)).all()


@settings(max_examples=300, deadline=None)
@given(values=earnings_strategy, year=year_strategy)
def test_at_maximum_status_is_preserved(values, year):
    values = np.array(values)
    out = epuf_measure(values, year)
    assert ((out == wage_base(year)) == (values >= wage_base(year))).all()


@settings(max_examples=300, deadline=None)
@given(values=earnings_strategy, year=year_strategy)
def test_values_land_on_the_grid_or_a_disclosure_constant(values, year):
    row = disclosure_constants()[year]
    out = epuf_measure(np.array(values), year)
    special = np.isin(
        out, [0, row["bottom_code"], row["band_mean"], row["wage_base"]]
    )
    on_grid = np.mod(out, rounding_base(out)) == 0
    assert (special | on_grid).all()


@pytest.mark.parametrize("year", YEARS)
def test_operator_is_weakly_increasing_in_every_year(year):
    grid = np.arange(0, wage_base(year) + 50, 1.0)
    assert (np.diff(epuf_measure(grid, year)) >= 0).all()


@settings(max_examples=200, deadline=None)
@given(values=earnings_strategy, year=year_strategy)
def test_rounding_moves_a_value_by_at_most_half_a_base(values, year):
    row = disclosure_constants()[year]
    values = np.clip(np.array(values), 0, row["wage_base"])
    ordinary = (values >= 100) & (
        values <= row["wage_base"] - row["band_base"]
    )
    out = epuf_measure(values, year)
    assert (
        np.abs(out[ordinary] - values[ordinary])
        <= rounding_base(values[ordinary]) / 2
    ).all()
