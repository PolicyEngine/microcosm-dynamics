"""Properties of the mean-preserving monotone ungrouping (INVENTED data).

Every band edge and band total below is INVENTED or drawn by Hypothesis;
nothing is read from a committed file.

Invariants (``baselines.interpolation`` module docstring):

* band sums are preserved: the single-year values of every band add up
  to its total;
* every single-year value is non-negative;
* homogeneity: scaling every total by ``c >= 0`` scales every value by
  ``c``;
* bands with equal per-year means give a flat schedule.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.baselines.interpolation import ungroup_band_totals

TOTAL = st.floats(
    min_value=0.0, max_value=1e3, allow_nan=False, allow_infinity=False
)


@st.composite
def banded_schedules(draw):
    """INVENTED bands: 1-12 widths of 1-10 years and their totals."""
    widths = draw(st.lists(st.integers(1, 10), min_size=1, max_size=12))
    start = draw(st.integers(-20, 60))
    edges = np.concatenate(([start], start + np.cumsum(widths))).tolist()
    totals = draw(st.lists(TOTAL, min_size=len(widths), max_size=len(widths)))
    return edges, totals


def _band_sums(edges, values):
    return [
        float(values[lower - edges[0] : upper - edges[0]].sum())
        for lower, upper in zip(edges[:-1], edges[1:], strict=True)
    ]


@settings(max_examples=300, deadline=None)
@given(schedule=banded_schedules())
def test_band_sums_are_preserved_and_values_are_nonnegative(schedule):
    edges, totals = schedule
    values = ungroup_band_totals(edges, totals)
    assert values.shape == (edges[-1] - edges[0],)
    assert np.all(np.isfinite(values))
    assert np.all(values >= 0.0)
    scale = max(max(totals), 1.0)
    np.testing.assert_allclose(
        _band_sums(edges, values), totals, rtol=1e-12, atol=1e-12 * scale
    )
    for lower, upper, total in zip(edges[:-1], edges[1:], totals, strict=True):
        if total == 0.0:
            band = values[lower - edges[0] : upper - edges[0]]
            assert np.all(band == 0.0)


@settings(max_examples=150, deadline=None)
@given(
    schedule=banded_schedules(),
    factor=st.floats(min_value=0.0, max_value=1e3, allow_nan=False),
)
def test_ungrouping_is_homogeneous_of_degree_one(schedule, factor):
    edges, totals = schedule
    base = ungroup_band_totals(edges, totals)
    scaled = ungroup_band_totals(edges, [factor * t for t in totals])
    scale = max(max(totals), 1.0) * max(factor, 1.0)
    np.testing.assert_allclose(
        scaled, factor * base, rtol=1e-9, atol=1e-9 * scale
    )


@settings(max_examples=100, deadline=None)
@given(
    widths=st.lists(st.integers(1, 10), min_size=1, max_size=10),
    mean=st.floats(min_value=1e-6, max_value=1e3, allow_nan=False),
)
def test_equal_per_year_means_give_a_flat_schedule(widths, mean):
    edges = np.concatenate(([0], np.cumsum(widths))).tolist()
    values = ungroup_band_totals(edges, [mean * w for w in widths])
    np.testing.assert_allclose(values, mean, rtol=1e-9)


def test_invented_five_year_hump_is_smooth_and_band_exact():
    # INVENTED rates per woman in five-year bands 15-19 ... 40-44.
    rates = [0.01, 0.06, 0.09, 0.09, 0.05, 0.01]
    edges = list(range(15, 46, 5))
    totals = [5 * rate for rate in rates]
    values = ungroup_band_totals(edges, totals)
    np.testing.assert_allclose(_band_sums(edges, values), totals, rtol=1e-12)
    # Smoother than the uniform spread: no jump between adjacent single
    # years is as large as the largest jump between band means.
    assert np.abs(np.diff(values)).max() < max(np.abs(np.diff(rates)))


@pytest.mark.parametrize(
    ("edges", "totals", "match"),
    [
        ([0], [], "at least two"),
        ([0, 5, 5], [1.0, 1.0], "strictly increasing"),
        ([0.0, 5.0], [1.0], "integers"),
        ([0, 5], [1.0, 2.0], "one value per band"),
        ([0, 5], [-1.0], "non-negative"),
        ([0, 5], [float("nan")], "finite"),
    ],
)
def test_invalid_schedules_are_refused(edges, totals, match):
    with pytest.raises(ValueError, match=match):
        ungroup_band_totals(edges, totals)


def test_all_zero_totals_return_zeros():
    assert np.all(ungroup_band_totals([0, 5, 10], [0.0, 0.0]) == 0.0)


def test_a_band_absorbed_by_the_cumulative_is_spread_uniformly():
    # Hypothesis counterexample: 1.0 + 4.675e-208 == 1.0 in the
    # cumulative, so the tiny band's interpolated values were all zero.
    tiny = 4.675152378505037e-208
    values = ungroup_band_totals([0, 1, 3], [1.0, tiny])
    assert values[0] == 1.0
    np.testing.assert_allclose(values[1:], tiny / 2, rtol=1e-12)
