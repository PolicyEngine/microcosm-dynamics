"""Mean-preserving ungrouping of banded schedules into single years.

A five-year age-specific fertility rate is the mean of its five single
ages' rates in a population with equal exposure at every age, so the
band's *total* (width times rate) is the sum of the single-age rates the
band contains.  :func:`ungroup_band_totals` spreads band totals over the
single years of each band so that

1. every band's single-year values sum exactly to the band total
   (mean preservation), and
2. every single-year value is non-negative,

using a monotone piecewise-cubic interpolation of the cumulative schedule
(Fritsch and Carlson, 1980, "Monotone piecewise cubic interpolation",
*SIAM Journal on Numerical Analysis* 17(2):238-246; SciPy's
``PchipInterpolator``, whose derivative estimates follow Fritsch and
Butland, 1984).  The cumulative ``C(x)``, the sum of every band total
below edge ``x``, is known exactly at the band edges and is
non-decreasing because no total is negative.  A monotone interpolant of
those points never decreases, so its first differences over single
years, the single-year values, are never negative; and because it passes
through ``C`` at every edge, each band's differences telescope to the
band total.  The implied single-year density (the interpolant's
derivative) is piecewise quadratic and continuous.  This is the
cumulative monotone-spline graduation that demographers use to split
grouped counts (for example DemoTools' ``graduate_mono``); it is chosen
over Beers or Sprague multipliers, which preserve band sums but can
return negative values at the edges of a schedule.

Floating-point differences can leave values of order ``1e-16`` below
zero or a band's sum off by a few ulps.  Values below ``-1e-12`` times
the largest band total are refused as a defect; smaller ones are set to
zero, and each band with a positive total is then rescaled so its values
sum to the total (to rounding).  A band whose total is zero returns
zeros.  A positive total below the cumulative's floating-point
resolution (about ``1e-16`` of the running sum, for example ``1e-208``
after a band of ``1.0``) is absorbed when the cumulative is formed, so
its interpolated values are all zero; such a band takes its total
spread uniformly over its years, which keeps both invariants.  No
fertility schedule comes near this case (Hypothesis found it).

Invariants (property-tested in ``tests/baselines/test_interpolation.py``):
band sums preserved, every value non-negative, homogeneity of degree one
(scaling every total by ``c >= 0`` scales every value by ``c``), and a
schedule whose bands have equal per-year means is returned flat.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy.interpolate import PchipInterpolator

__all__ = [
    "NEGATIVE_TOLERANCE",
    "ungroup_band_totals",
]

#: Relative size of a negative single-year value that is treated as
#: floating-point noise rather than a defect.
NEGATIVE_TOLERANCE = 1e-12


def _validated(
    edges: Sequence[int], totals: Sequence[float]
) -> tuple[np.ndarray, np.ndarray]:
    edge_array = np.asarray(edges)
    if edge_array.ndim != 1 or edge_array.size < 2:
        raise ValueError("edges must list at least two band edges")
    if not np.issubdtype(edge_array.dtype, np.integer):
        raise ValueError("edges must be integers (single-year boundaries)")
    edge_array = edge_array.astype(np.int64)
    if np.any(np.diff(edge_array) <= 0):
        raise ValueError("edges must be strictly increasing")
    total_array = np.asarray(totals, dtype=np.float64)
    if total_array.shape != (edge_array.size - 1,):
        raise ValueError("totals must have one value per band")
    if not np.all(np.isfinite(total_array)):
        raise ValueError("band totals must be finite")
    if np.any(total_array < 0.0):
        raise ValueError("band totals must be non-negative")
    return edge_array, total_array


def ungroup_band_totals(
    edges: Sequence[int], totals: Sequence[float]
) -> np.ndarray:
    """Single-year values for bands ``[edges[k], edges[k+1])``.

    ``totals[k]`` is the sum of the single-year values of band ``k``
    (for a rate schedule, the band width times the band rate).  Returns
    one value per single year from ``edges[0]`` to ``edges[-1] - 1``.
    See the module docstring for the method and its invariants.
    """
    edge_array, total_array = _validated(edges, totals)
    cumulative = np.concatenate(([0.0], np.cumsum(total_array)))
    single_edges = np.arange(edge_array[0], edge_array[-1] + 1)
    if total_array.max(initial=0.0) == 0.0:
        return np.zeros(single_edges.size - 1)
    # Subnormal slopes overflow SciPy's harmonic-mean derivative to an
    # infinite reciprocal, i.e. a zero derivative, which is the intended
    # flat limit; the band fallback below handles the absorbed totals.
    with np.errstate(over="ignore", divide="ignore"):
        interpolant = PchipInterpolator(
            edge_array.astype(np.float64), cumulative, extrapolate=False
        )
        values = np.diff(interpolant(single_edges.astype(np.float64)))
    scale = float(total_array.max())
    if not np.all(np.isfinite(values)):
        raise ValueError("ungrouping produced a non-finite value")
    if values.min() < -NEGATIVE_TOLERANCE * scale:
        raise ValueError(
            "ungrouping produced a negative single-year value "
            f"({values.min()!r}); the monotone interpolant should not"
        )
    values = np.maximum(values, 0.0)
    for lower, upper, total in zip(
        edge_array[:-1], edge_array[1:], total_array, strict=True
    ):
        start, stop = lower - edge_array[0], upper - edge_array[0]
        band = values[start:stop]
        band_sum = float(band.sum())
        if total == 0.0:
            values[start:stop] = 0.0
        elif band_sum > 0.0:
            values[start:stop] = band * (total / band_sum)
        else:
            # Absorbed by the cumulative's rounding (module docstring).
            values[start:stop] = total / (upper - lower)
    return values
