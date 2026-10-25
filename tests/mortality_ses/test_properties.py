"""Accounting properties using only invented populations and coefficients.

All categories, coefficients, probability tables and DI rates below are
INVENTED. These tests establish mechanism identities, not an empirical
mortality gradient. Conservation uses absolute and relative tolerance 1e-12
for finite double-precision products, sums and the adapter's cell arithmetic.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics.baselines.base import BaselineYearAwareMortality
from populace_dynamics.engine.di_entitlement import (
    _net_of_di_origin,
    apply_di_aware_mortality,
)
from populace_dynamics.engine.di_entitlement_rates import (
    SINGLE_YEAR_AGE_BANDS,
    DIEntitlementRates,
    DIEntitlementSpec,
)
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import apply_mortality
from populace_dynamics.mortality_ses.model import DifferentialMortality
from populace_dynamics.mortality_ses.normalizer import normalize_probabilities
from populace_dynamics.mortality_ses.specification import (
    DIMENSIONS,
    HoldLastCoefficientPath,
    RelativeRiskSpec,
    RiskDimension,
    UnclassifiedValueError,
)
from populace_dynamics.mortality_ses.step import apply_differential_mortality

RTOL = ATOL = 1e-12
PROPERTY = settings(max_examples=35, deadline=None)
# The exact oracle is cheap on these small cells and is the main check
# of the arithmetic, so it gets more examples.
ORACLE_PROPERTY = settings(max_examples=150, deadline=None)
ORACLE_RTOL = 1e-11
REF = "invented_ref"
OTHER = "invented_other"
UNCLASSIFIED = "invented_unclassified"
SEXES = ("female", "male")
POSITIVE = st.floats(0.05, 20, allow_nan=False, allow_infinity=False)
PROBABILITY = st.floats(0, 1, allow_nan=False, allow_infinity=False)
WEIGHT = st.one_of(st.just(0.0), POSITIVE)


def invented_dimensions():
    return tuple(
        RiskDimension(name, name, (REF, OTHER), REF, (UNCLASSIFIED,))
        for name in DIMENSIONS
    )


def invented_table(*, years=(2020,), risk=2.0):
    """Invented full-coverage age bands, with zero reference coefficients."""
    return pd.DataFrame(
        [
            dict(
                year=year,
                dimension=name,
                category=category,
                sex=sex,
                age_lower=0,
                age_upper=120,
                log_relative_risk=(0.0 if category == REF else np.log(risk)),
            )
            for year in years
            for name in DIMENSIONS
            for category in (REF, OTHER)
            for sex in SEXES
        ]
    )


def invented_spec(*, risk=2.0, rule="refuse", path=None):
    return RelativeRiskSpec(
        invented_dimensions(),
        path or HoldLastCoefficientPath(invented_table(risk=risk)),
        unclassified_rule=rule,
    )


def invented_baseline(q=0.1, *, years=(2021,)):
    return BaselineYearAwareMortality(
        "invented_sm1",
        {year: {sex: np.full(121, q) for sex in SEXES} for year in years},
    )


def invented_frame(size=8, *, year=2021, di=False):
    frame = pd.DataFrame(
        {
            "person_id": np.arange(size, 0, -1),
            "age": np.full(size, 50),
            "birth_year": np.full(size, year - 1 - 50),
            "year": np.full(size, year - 1),
            "sex": [SEXES[i % 2] for i in range(size)],
            "weight": np.ones(size),
            **{
                name: [REF if i % 3 else OTHER for i in range(size)]
                for name in DIMENSIONS
            },
        }
    )
    if di:
        frame["di_entitled"] = [i % 6 == 0 for i in range(size)]
        frame["di_conversion_year"] = pd.array(
            [year - 2 if i % 6 == 1 else pd.NA for i in range(size)],
            dtype="Int64",
        )
        for column in ("di_award_year", "di_award_age", "di_recovery_year"):
            frame[column] = pd.array([pd.NA] * size, dtype="Int64")
        frame["di_converted"] = False
        frame["di_event"] = "invented_opening"
    return frame


def invented_context(frame, *, seed=0, registry=False, year=2021):
    return PeriodContext(
        1,
        year,
        seed,
        {},
        rng_registry=ProjectionRNGRegistry(seed, 2) if registry else None,
        person_ordinals={
            person_id: index
            for index, person_id in enumerate(sorted(frame["person_id"]))
        },
    )


def invented_rates(*, multiplier=1.5, post_conversion="di_origin"):
    shape = (2, 121)
    return DIEntitlementRates(
        spec=DIEntitlementSpec(post_conversion_mortality=post_conversion),
        incidence=np.zeros(shape),
        recovery_attained=np.zeros(shape),
        death_attained=np.full(shape, multiplier * 0.1),
        population_reference_death=np.full(shape, 0.1),
        recovery_select=None,
        death_select=None,
        recovery_level_factor=1.0,
        death_level_factor=1.0,
    )


def assert_conserved(q, base, cells, weights, log):
    """Feasible cells conserve outright; only infeasible ones log a gap."""
    for row in log.itertuples(index=False):
        mask = np.asarray(
            [cell == (row.year, row.sex, row.age) for cell in cells]
        )
        target = np.sum(weights[mask] * base[mask])
        applied = np.sum(weights[mask] * q[mask])
        assert applied + row.clipping_residual == pytest.approx(
            target, rel=RTOL, abs=ATOL
        )
        assert row.baseline_expected_deaths == pytest.approx(
            target, rel=RTOL, abs=ATOL
        )
        assert row.applied_expected_deaths == pytest.approx(
            applied, rel=RTOL, abs=ATOL
        )
        if not row.infeasible:
            assert row.clipping_residual == 0
            assert applied == pytest.approx(target, rel=RTOL, abs=ATOL)


def exact_cell(base, risk, fixed, prescribed, weights):
    """An independent exact reading of the normalization rule.

    It uses rational arithmetic and finds the capped rows by trying each
    count of largest-q*RR rows in turn, rather than iterating the factor
    as the normalizer does.  Returns probabilities, the infeasible flag,
    the normalization basis and the number of free rows clipped at one.
    """
    b, r, p, w = (
        [Fraction(float(x)) for x in values]
        for values in (base, risk, prescribed, weights)
    )
    rows = range(len(b))
    free = [i for i in rows if not fixed[i]]
    q = [p[i] if fixed[i] else Fraction(0) for i in rows]
    target = sum((w[i] * b[i] for i in rows), Fraction(0)) - sum(
        (w[i] * p[i] for i in rows if fixed[i]), Fraction(0)
    )
    support = [i for i in free if b[i] > 0]
    allocation, basis = w, "weights"
    if target == 0 and support and not any(w[i] for i in support):
        allocation, basis = [Fraction(1)] * len(b), "persons"
        target = sum(b[i] for i in support)
    capacity = sum((allocation[i] for i in support), Fraction(0))
    if target <= 0:
        return [float(x) for x in q], target < 0, basis, 0
    if target > capacity:
        for i in support:
            q[i] = Fraction(1)
        return [float(x) for x in q], True, basis, len(support)
    raw = [b[i] * r[i] for i in rows]

    def clipped(factor):
        return sum(raw[i] * factor > 1 for i in free)

    if target == capacity:
        # Every weighted row must reach one; zero-allocation rows take the
        # smallest factor that does that.
        factor = max(1 / raw[i] for i in support if allocation[i] > 0)
        for i in free:
            q[i] = min(Fraction(1), raw[i] * factor)
        return [float(x) for x in q], False, basis, clipped(factor)
    ranked = sorted(
        (i for i in support if allocation[i] > 0),
        key=lambda i: raw[i],
        reverse=True,
    )
    for count in range(len(ranked)):
        top, rest = ranked[:count], ranked[count:]
        factor = (target - sum(allocation[i] for i in top)) / sum(
            allocation[i] * raw[i] for i in rest
        )
        if all(raw[i] * factor <= 1 for i in rest):
            break
    else:  # pragma: no cover - a target below capacity always stops
        raise AssertionError("no capped set satisfies the cell")
    for i in free:
        q[i] = min(Fraction(1), raw[i] * factor)
    return [float(x) for x in q], False, basis, clipped(factor)


def wide(low, high):
    """Invented magnitudes spread evenly in log10 between the bounds."""
    return st.floats(low, high).map(lambda exponent: 10.0**exponent)


@st.composite
def invented_wide_cells(draw):
    """Cells across float magnitudes, near-one q and arbitrary fixed q."""
    size = draw(st.integers(1, 9))
    rows = dict(min_size=size, max_size=size)
    base = draw(
        st.lists(
            st.one_of(
                st.sampled_from((0.0, 1.0)), PROBABILITY, st.floats(0.9, 1)
            ),
            **rows,
        )
    )
    risk = draw(
        st.lists(
            st.one_of(wide(-30, 30), st.sampled_from((1e-100, 1e100))),
            **rows,
        )
    )
    weights = draw(st.lists(st.one_of(st.just(0.0), wide(-8, 16)), **rows))
    fixed = draw(st.lists(st.booleans(), **rows))
    prescribed = list(base)
    if draw(st.booleans()):
        prescribed = [
            draw(PROBABILITY) if is_fixed else q
            for q, is_fixed in zip(base, fixed, strict=True)
        ]
    return tuple(
        np.asarray(values, dtype=dtype)
        for values, dtype in (
            (base, float),
            (risk, float),
            (fixed, bool),
            (prescribed, float),
            (weights, float),
        )
    )


@ORACLE_PROPERTY
@given(invented_wide_cells())
@example(  # Float roundoff once emptied the remaining target here.
    (
        np.array([0.5, 0.5, 0.5]),
        np.array([20, 1, 1e-25]),
        np.zeros(3, dtype=bool),
        np.array([0.5, 0.5, 0.5]),
        np.array([1, 0.1, 1.1]),
    )
)
@example(  # A rounded target-capacity tie once saturated both rows.
    (
        np.array([1, 0.5]),
        np.array([1, 1e-20]),
        np.zeros(2, dtype=bool),
        np.array([1, 0.5]),
        np.array([1e16, 1]),
    )
)
@example(  # An exactly filled weighted support beside weightless rows.
    (
        np.array([1, 2.2691957742722138e-77, 1, 1, 0.05303249588052529]),
        np.array(
            [1e30, 4.0259657179840314e17, 4.0259657179840314e17, 1e30, 1e30]
        ),
        np.array([False, True, True, False, False]),
        np.array([1, 2.2691957742722138e-77, 1, 1, 0.05303249588052529]),
        np.array([0, 0, 131.91017397114445, 1.000000137244776, 0]),
    )
)
@example(  # The same tie with unequal risks, on the Decimal path.
    (
        np.array([1, 0.5, 0.2]),
        np.array([1, 3, 2]),
        np.zeros(3, dtype=bool),
        np.array([1, 0.5, 0.2]),
        np.array([2, 0, 0]),
    )
)
@example(  # Fixed excess with weightless free rows.
    (
        np.array([0.25, 0.25]),
        np.array([1, 2]),
        np.array([True, False]),
        np.array([0.5, 0.25]),
        np.array([1, 0]),
    )
)
@example(  # A scaled probability rounded to exactly one once capped nothing.
    (
        np.array([0.5, 0.5, 0.5]),
        np.array([20, 1e-26, 1]),
        np.zeros(3, dtype=bool),
        np.array([0.5, 0.5, 0.5]),
        np.array([1, 1, 1e-20]),
    )
)
@example(  # Fixed-death and capping cancellation once compounded.
    (
        np.array([0.5, 0.5, 0.5]),
        np.array([1, 1e12, 1]),
        np.array([True, False, False]),
        np.array([0.49950165, 0.5, 0.5]),
        np.array([1, 0.0009989, 0.0000044]),
    )
)
@example(  # A weightless row at one once went uncounted as clipped.
    (
        np.array([0.25, 0.5, 0.5]),
        np.array([1, 3, 14 / 3]),
        np.zeros(3, dtype=bool),
        np.array([0.25, 0.5, 0.5]),
        np.array([1, 1, 0]),
    )
)
def test_normalizer_matches_an_exact_oracle_across_magnitudes(inputs):
    assert_matches_oracle(*inputs)


def assert_matches_oracle(base, risk, fixed, prescribed, weights):
    """The normalizer agrees with ``exact_cell`` within its error bound.

    The float path's bound is about 1.3e-12 relative (see
    ``normalizer._FLOAT_MARGIN``), and the Decimal path is exact up to the
    final float64 rounding, so ``ORACLE_RTOL`` leaves headroom of about
    seven times.
    """
    cells = [(2021, "female", 50)] * len(base)
    q, log = normalize_probabilities(
        base, risk, fixed, prescribed, cells, weights
    )
    expected, infeasible, basis, clipped = exact_cell(
        base, risk, fixed, prescribed, weights
    )
    np.testing.assert_allclose(q, expected, rtol=ORACLE_RTOL, atol=1e-15)
    assert bool(log.loc[0, "infeasible"]) == infeasible
    assert log.loc[0, "normalization_basis"] == basis
    assert log.loc[0, "clipped_persons"] == clipped
    assert ((0 <= q) & (q <= 1)).all()
    if not infeasible:
        applied = sum(
            Fraction(x) * Fraction(y) for x, y in zip(weights, q, strict=True)
        )
        target = sum(
            Fraction(x) * Fraction(y)
            for x, y in zip(weights, base, strict=True)
        )
        assert float(abs(applied - target)) <= RTOL * max(float(target), ATOL)
        assert log.loc[0, "clipping_residual"] == 0


@st.composite
def invented_cap_boundary_cells(draw):
    """Cells whose dominant row sits at the cap, beside tiny weights.

    Row 0's weight equals the target that rows 0 and 1 (and an optional
    fixed row) supply, so its scaled probability is one up to rounding,
    nudged a few units either way.  Row 1 adds target but almost no
    scaled mass, and the other rows carry tiny positive weights, so
    whether row 0 caps decides their probabilities.
    """
    q0 = draw(st.floats(0.05, 0.95))
    q1 = draw(st.floats(0.05, 1))
    w0 = draw(wide(-3, 6))
    share = w0 * (1 - q0)
    base, risk, fixed, prescribed, weights = [], [], [], [], []
    if draw(st.booleans()):
        # A fixed row off baseline moves part of row 1's target into a
        # cancellation of baseline and fixed deaths.
        qf = draw(st.floats(0.05, 0.95))
        pf = draw(st.floats(0.05, 0.95).filter(lambda p: abs(p - qf) > 0.01))
        moved = draw(st.floats(-0.9, 0.9)) * share
        wf = abs(moved / (qf - pf))
        share -= wf * (qf - pf)
        base, risk, fixed = [qf], [draw(wide(-2, 2))], [True]
        prescribed, weights = [pf], [wf]
    w1 = share / q1
    nudge = draw(st.integers(-3, 3))
    for _ in range(abs(nudge)):
        w0 = float(np.nextafter(w0, np.inf if nudge > 0 else 0.0))
    extra = draw(st.integers(1, 4))
    rows = dict(min_size=extra, max_size=extra)
    base += [q0, q1] + draw(st.lists(st.floats(0.01, 1), **rows))
    risk += [draw(wide(0, 3)), draw(wide(-60, -12))] + draw(
        st.lists(wide(-2, 2), **rows)
    )
    # Relative to row 0, from below one unit in the last place upward.
    weights += [w0, w1] + [
        w0 * tiny for tiny in draw(st.lists(wide(-40, -8), **rows))
    ]
    fixed += [False] * (2 + extra)
    prescribed = prescribed + base[len(prescribed) :]
    order = draw(st.permutations(range(len(base))))
    return tuple(
        np.asarray([values[i] for i in order], dtype=dtype)
        for values, dtype in (
            (base, float),
            (risk, float),
            (fixed, bool),
            (prescribed, float),
            (weights, float),
        )
    )


@ORACLE_PROPERTY
@given(invented_cap_boundary_cells())
def test_cap_boundaries_beside_tiny_weights_match_the_oracle(inputs):
    assert_matches_oracle(*inputs)


@st.composite
def invented_near_margin_cells(draw):
    """Ordinary magnitudes with cancellation near the float margin.

    A fixed row's deaths cancel all but a drawn share of the cell's
    deaths, near the margin on either side, and large risks cap free rows,
    so capping cancels much of the rest.  Most such cells stay on the
    float path, where the error bound is tightest.
    """
    size = draw(st.integers(1, 7))
    rows = dict(min_size=size, max_size=size)
    free_base = np.asarray(draw(st.lists(st.floats(0.01, 1), **rows)))
    free_risk = draw(st.lists(st.one_of(wide(-3, 0), wide(0, 6)), **rows))
    free_weights = np.asarray(draw(st.lists(wide(-4, 4), **rows)))
    q0 = draw(st.floats(0.01, 0.5))
    free_deaths = float(np.sum(free_weights * free_base))
    # Large enough that the prescribed probability below stays in [0, 1].
    w0 = free_deaths * draw(st.floats(1, 3)) / (1 - q0)
    keep = draw(wide(-3.5, -1))
    p0 = min(1.0, (w0 * q0 + free_deaths) * (1 - keep) / w0)
    return (
        np.r_[q0, free_base],
        np.r_[draw(wide(-2, 2)), free_risk],
        np.r_[True, np.zeros(size, dtype=bool)],
        np.r_[p0, free_base],
        np.r_[w0, free_weights],
    )


@ORACLE_PROPERTY
@given(invented_near_margin_cells())
def test_cancellation_near_the_margin_matches_the_oracle(inputs):
    assert_matches_oracle(*inputs)


@st.composite
def invented_weightless_cap_cells(draw):
    """Weightless rows within a few units of rounding of one.

    Weighted rows set the factor, optionally after a first round that caps
    one dominant row; none of the others caps.  Their exact factor is a
    ratio of rational sums, so each weightless row's risk can be placed a
    drawn number of float steps from where its scaled probability is
    exactly one, on either side.  The rows take that factor without
    setting it, so they test only the clipped count and their own
    probabilities.
    """
    size = draw(st.integers(1, 5))
    rows = dict(min_size=size, max_size=size)
    base = draw(st.lists(st.floats(0.01, 0.2), **rows))
    risk = draw(st.lists(st.floats(0.5, 2), **rows))
    weights = draw(st.lists(st.floats(0.1, 10), **rows))
    deaths = sum(
        Fraction(w) * Fraction(b) for w, b in zip(weights, base, strict=True)
    )
    scaled = sum(
        Fraction(w) * Fraction(b) * Fraction(r)
        for w, b, r in zip(weights, base, risk, strict=True)
    )
    if draw(st.booleans()):
        # This row caps in the first round; the rest share what remains.
        dominant = float(deaths) * draw(st.floats(0.1, 1.5))
        base, risk = [0.5, *base], [1000.0, *risk]
        weights = [dominant, *weights]
        deaths -= Fraction(dominant) / 2
    factor = deaths / scaled
    for _ in range(draw(st.integers(1, 3))):
        q0 = draw(st.floats(0.05, 0.95))
        r0 = float(1 / (Fraction(q0) * factor))
        for _ in range(abs(steps := draw(st.integers(-4, 4)))):
            r0 = float(np.nextafter(r0, np.inf if steps > 0 else 0))
        base, risk, weights = [*base, q0], [*risk, r0], [*weights, 0.0]
    base = np.asarray(base)
    return (
        base,
        np.asarray(risk),
        np.zeros(len(base), dtype=bool),
        base,
        np.asarray(weights),
    )


@ORACLE_PROPERTY
@given(invented_weightless_cap_cells())
def test_weightless_rows_at_one_match_the_oracle(inputs):
    assert_matches_oracle(*inputs)


def test_cascading_caps_match_the_oracle():
    """Each capping round pushes the next row over one."""
    base = np.full(6, 0.9)
    risk = np.asarray([1, 1.1, 1.3, 1.7, 2.5, 5.0])
    weights = np.asarray([3.0, 1.0, 2.0, 1.0, 0.5, 1.0])
    fixed = np.zeros(6, dtype=bool)
    cells = [(2021, "male", 90)] * 6
    q, log = normalize_probabilities(base, risk, fixed, base, cells, weights)
    expected, infeasible, _, clipped = exact_cell(
        base, risk, fixed, base, weights
    )
    np.testing.assert_allclose(q, expected, rtol=1e-12, atol=1e-15)
    assert log.loc[0, "clipped_persons"] == clipped >= 3
    assert not infeasible
    assert_conserved(q, base, cells, weights, log)


@PROPERTY
@given(
    st.lists(st.floats(0.01, 1), min_size=3, max_size=6),
    st.lists(POSITIVE, min_size=3, max_size=6),
    st.floats(0, 1),
    st.lists(POSITIVE, min_size=2, max_size=5),
    st.booleans(),
)
def test_weightless_cells_take_the_vanishing_weight_limit(
    base, risk, fixed_q, free_weights, equal
):
    """Infeasible cells: the limit is unique.  Feasible: unit weights."""
    size = min(len(base), len(risk), len(free_weights) + 1)
    base, risk = np.asarray(base[:size]), np.asarray(risk[:size])
    fixed = np.arange(size) == 0
    prescribed = base.copy()
    prescribed[0] = fixed_q
    cells = [(2021, "female", 50)] * size
    vanishing = np.asarray(free_weights[: size - 1])
    if equal:
        vanishing = np.full(size - 1, vanishing[0])
    zero, zero_log = normalize_probabilities(
        base, risk, fixed, prescribed, cells, np.r_[1.0, np.zeros(size - 1)]
    )
    small, _ = normalize_probabilities(
        base, risk, fixed, prescribed, cells, np.r_[1.0, 1e-60 * vanishing]
    )
    if zero_log.loc[0, "infeasible"]:
        np.testing.assert_array_equal(zero, small)
    elif equal:
        assert zero_log.loc[0, "normalization_basis"] == "persons"
        np.testing.assert_allclose(zero, small, rtol=RTOL, atol=ATOL)


@st.composite
def invented_normalizer_inputs(draw):
    size = draw(st.integers(1, 16))
    base = np.asarray(
        draw(st.lists(PROBABILITY, min_size=size, max_size=size))
    )
    risk = np.asarray(draw(st.lists(POSITIVE, min_size=size, max_size=size)))
    weights = np.asarray(draw(st.lists(WEIGHT, min_size=size, max_size=size)))
    fixed = np.asarray(
        draw(st.lists(st.booleans(), min_size=size, max_size=size))
    )
    groups = draw(st.lists(st.integers(0, 3), min_size=size, max_size=size))
    cells = [(2021, SEXES[group % 2], 50 + group // 2) for group in groups]
    return base, risk, fixed, cells, weights


@PROPERTY
@given(invented_normalizer_inputs())
def test_cell_conservation_bounds_and_baseline_fixed_feasibility(inputs):
    base, risk, fixed, cells, weights = inputs
    q, log = normalize_probabilities(base, risk, fixed, base, cells, weights)
    assert ((0 <= q) & (q <= 1)).all()
    np.testing.assert_array_equal(q[fixed], base[fixed])
    assert not log["infeasible"].any()
    assert_conserved(q, base, cells, weights, log)


@PROPERTY
@given(invented_normalizer_inputs())
def test_identity_is_bit_for_bit_and_normalizer_is_deterministic(inputs):
    base, _, fixed, cells, weights = inputs
    q, log = normalize_probabilities(
        base, np.ones(len(base)), fixed, base, cells, weights
    )
    repeated, repeated_log = normalize_probabilities(
        base, np.ones(len(base)), fixed, base, cells, weights
    )
    np.testing.assert_array_equal(q, base)
    np.testing.assert_array_equal(q, repeated)
    pd.testing.assert_frame_equal(log, repeated_log)


@PROPERTY
@given(invented_normalizer_inputs(), POSITIVE, st.integers(0, 10000))
def test_permutation_and_common_weight_scaling_preserve_probabilities(
    inputs, scale, seed
):
    base, risk, fixed, cells, weights = inputs
    q, _ = normalize_probabilities(base, risk, fixed, base, cells, weights)
    permutation = np.random.default_rng(seed).permutation(len(base))
    permuted, _ = normalize_probabilities(
        base[permutation],
        risk[permutation],
        fixed[permutation],
        base[permutation],
        [cells[i] for i in permutation],
        weights[permutation],
    )
    scaled, _ = normalize_probabilities(
        base, risk, fixed, base, cells, weights * scale
    )
    np.testing.assert_array_equal(permuted, q[permutation])
    np.testing.assert_allclose(scaled, q, rtol=RTOL, atol=ATOL)


@PROPERTY
@given(invented_normalizer_inputs())
def test_weightless_cells_count_persons_equally(inputs):
    """Zero weight leaves the factor to unit weights, never to zero."""
    base, risk, fixed, cells, _ = inputs
    zero, zero_log = normalize_probabilities(
        base, risk, fixed, base, cells, np.zeros(len(base))
    )
    unit, unit_log = normalize_probabilities(
        base, risk, fixed, base, cells, np.ones(len(base))
    )
    np.testing.assert_array_equal(zero, unit)
    np.testing.assert_array_equal(zero_log["factor"], unit_log["factor"])
    assert not zero_log["infeasible"].any()
    assert (zero_log["clipping_residual"] == 0).all()
    assert (unit_log["normalization_basis"] == "weights").all()
    for row in zero_log.itertuples(index=False):
        mask = np.asarray(
            [cell == (row.year, row.sex, row.age) for cell in cells]
        )
        support = mask & ~fixed & (base > 0)
        if support.any():
            assert row.normalization_basis == "persons"
            assert row.persons_target == pytest.approx(
                np.sum(base[support]), rel=RTOL, abs=ATOL
            )
        else:
            assert row.normalization_basis == "weights"


@PROPERTY
@given(PROBABILITY, POSITIVE, st.integers(1, 15))
def test_one_free_risk_group_returns_baseline_probability(q_base, risk, size):
    base = np.full(size, q_base)
    q, _ = normalize_probabilities(
        base,
        np.full(size, risk),
        np.arange(size) % 3 == 0,
        base,
        [(2021, "female", 50)] * size,
        np.arange(1, size + 1, dtype=float),
    )
    np.testing.assert_array_equal(q, base)


@PROPERTY
@given(st.floats(0.01, 0.4), st.floats(0.01, 0.4), POSITIVE)
def test_fixed_deaths_above_target_are_flagged(base_q, excess, weight):
    base = np.full(2, base_q)
    prescribed = np.asarray([min(1.0, 2 * base_q + excess), base_q])
    q, log = normalize_probabilities(
        base,
        np.ones(2),
        np.asarray([True, False]),
        prescribed,
        [(2021, "female", 50)] * 2,
        np.full(2, weight),
    )
    assert log.loc[0, "infeasible"]
    assert q[0] == prescribed[0]
    assert q[1] == 0
    assert log.loc[0, "clipping_residual"] < 0


@PROPERTY
@given(st.floats(0.02, 0.15), st.floats(0.5, 1.75), WEIGHT)
def test_unit_risk_reproduces_adapter_arithmetic_without_clipping(
    baseline_q, multiplier, weight_scale
):
    base = np.full(8, baseline_q)
    fixed = np.arange(8) % 4 == 0
    prescribed = base.copy()
    prescribed[fixed] *= multiplier
    sex = np.arange(8) % 2
    age = np.full(8, 50)
    weights = np.arange(1, 9, dtype=float) * weight_scale
    cells = [(2021, SEXES[s], 50) for s in sex]
    q, log = normalize_probabilities(
        base, np.ones(8), fixed, prescribed, cells, weights
    )
    old, _ = _net_of_di_origin(
        prescribed, base, fixed, sex, age, weights, SINGLE_YEAR_AGE_BANDS
    )
    assert not log["clipped_persons"].any()
    np.testing.assert_allclose(q, old, rtol=RTOL, atol=ATOL)


@st.composite
def invented_adapter_cells(draw):
    size = draw(st.integers(1, 10))
    rows = st.lists(PROBABILITY, min_size=size, max_size=size)
    base, prescribed = np.asarray(draw(rows)), np.asarray(draw(rows))
    fixed = np.asarray(
        draw(st.lists(st.booleans(), min_size=size, max_size=size))
    )
    prescribed[~fixed] = base[~fixed]
    weights = np.asarray(draw(st.lists(WEIGHT, min_size=size, max_size=size)))
    groups = np.asarray(
        draw(st.lists(st.integers(0, 3), min_size=size, max_size=size))
    )
    return base, fixed, prescribed, weights, groups % 2, 50 + groups // 2


def exact_adapter_cell(base, fixed, prescribed, weights):
    """The adapter's formula for one cell, in exact arithmetic.

    ``_net_of_di_origin`` multiplies a cell's free rows by
    ``max(P - D, 0) / E`` and clips at one, where ``P`` is the cell's
    baseline deaths, ``D`` its fixed rows' deaths and ``E`` its free rows'
    baseline deaths; with no fixed row or no free deaths the factor is one.
    Also returns whether the adapter's float64 factor is unreliable: when
    ``P - D`` or ``E`` is within a hundredth of ``max(P, D)``, the
    subtraction can cancel, absorb ``E`` or overflow the division; when
    ``max(P, D)`` is below ``2**-1000``, float64 rounds its products
    absolutely, not relatively.  Elsewhere a first-order error bound keeps
    the adapter within ``RTOL`` and ``ATOL`` (the design note's intended
    differences).  Exact sums keep an ``E`` that would underflow in float64.
    """
    weight = [Fraction(w) for w in weights]
    population = sum(
        w * Fraction(b) for w, b in zip(weight, base, strict=True)
    )
    fixed_deaths = sum(
        weight[i] * Fraction(prescribed[i]) for i in np.flatnonzero(fixed)
    )
    free_deaths = sum(
        weight[i] * Fraction(base[i]) for i in np.flatnonzero(~fixed)
    )
    factor, unreliable = Fraction(1), False
    if fixed.any():
        largest = max(population, fixed_deaths)
        gap = abs(population - fixed_deaths)
        unreliable = (
            0 < free_deaths <= largest / 100
            or 0 < gap <= largest / 100
            or 0 < largest < Fraction(2) ** -1000
        )
        if free_deaths > 0:
            factor = max(population - fixed_deaths, 0) / free_deaths
    q = [
        p if f else float(min(1, Fraction(b) * factor))
        for b, f, p in zip(base, fixed, prescribed, strict=True)
    ]
    return np.asarray(q, dtype=float), unreliable


TINY = 5e-324  # The smallest subnormal float64.


@PROPERTY
@given(invented_adapter_cells())
@example(  # Subnormal sums round absolutely: the factor errs by percents.
    (
        np.array([12 * TINY, 0.5, 41 * TINY]),
        np.array([True, False, False]),
        np.array([0.0, 0.5, 41 * TINY]),
        np.array([1.0, 0.0, 0.3]),
        np.zeros(3, dtype=int),
        np.full(3, 50),
    )
)
@example(  # The same with single subnormal rows.
    (
        np.array([TINY, 0.5, TINY]),
        np.array([True, False, False]),
        np.array([0.0, 0.5, TINY]),
        np.array([0.3, 0.0, 1.7]),
        np.zeros(3, dtype=int),
        np.full(3, 50),
    )
)
@example(  # Equal subnormal P and D, which leave no gap to flag.
    (
        np.array([0.0, 0.0, 0.5, 2 * TINY]),
        np.array([True, True, False, False]),
        np.array([TINY, TINY, 0.5, 2 * TINY]),
        np.array([0.3, 0.3, 0.0, 0.3]),
        np.zeros(4, dtype=int),
        np.full(4, 50),
    )
)
@example(  # The adapter's factor overflows on a subnormal free row.
    (
        np.array([2.225073858507e-311, 0.5]),
        np.array([False, True]),
        np.array([2.225073858507e-311, 0.0]),
        np.array([1.0, 1.0]),
        np.zeros(2, dtype=int),
        np.full(2, 50),
    )
)
@example(  # Its baseline deaths absorb the free deaths: factor zero.
    (
        np.array([0.5, 0.8, 3e-301]),
        np.array([False, True, False]),
        np.array([0.5, 0.8, 3e-301]),
        np.array([0.0, 4.0, 16.0]),
        np.zeros(3, dtype=int),
        np.full(3, 50),
    )
)
@example(  # The same with subnormal free deaths, beside a weightless row.
    (
        np.array([5e-324, 0.5074563290805952, 0.5537272658366658]),
        np.array([False, False, True]),
        np.array([5e-324, 0.5074563290805952, 0.5537272658366658]),
        np.array([1.6873477097608718, 0.0, 18.517829151607195]),
        np.zeros(3, dtype=int),
        np.full(3, 50),
    )
)
@example(  # Its subtraction cancels to an error above the tolerance.
    (
        np.array([0.9, 1.192092896e-07, 0.5543192935511442]),
        np.array([False, False, True]),
        np.array([0.9, 1.192092896e-07, 0.5543192935511442]),
        np.array([0.0, 2.00001, 0.05000000000000001]),
        np.zeros(3, dtype=int),
        np.full(3, 50),
    )
)
def test_unit_risk_matches_adapter_on_every_unclipped_cell(inputs):
    """Includes zero weights, infeasible cells and weightless free rows.

    Besides clipping, one intended exception skips the cell: an
    infeasible cell whose free support weighs nothing.  Every other cell
    matches the adapter's formula evaluated exactly, at the oracle's
    tolerance, and the adapter's float64 result except where that is
    unreliable (``exact_adapter_cell``), a second intended exception.
    """
    base, fixed, prescribed, weights, sex, age = inputs
    cells = [(2021, SEXES[s], int(a)) for s, a in zip(sex, age, strict=True)]
    q, log = normalize_probabilities(
        base, np.ones(len(base)), fixed, prescribed, cells, weights
    )
    # The adapter's intended overflow, and the 0 * inf it can then form.
    with np.errstate(over="ignore", invalid="ignore"):
        old, _ = _net_of_di_origin(
            prescribed, base, fixed, sex, age, weights, SINGLE_YEAR_AGE_BANDS
        )
    for row in log.itertuples(index=False):
        if row.clipped_persons:
            continue  # Intended: iterative capping versus one-pass clipping.
        mask = np.asarray(
            [cell == (row.year, row.sex, row.age) for cell in cells]
        )
        support = mask & ~fixed & (base > 0)
        if row.infeasible and support.any() and not weights[support].any():
            # Intended: the adapter leaves weightless rows at factor one,
            # while the brief's infeasible-cell rules hold for any weight.
            continue
        exact, unreliable = exact_adapter_cell(
            base[mask], fixed[mask], prescribed[mask], weights[mask]
        )
        np.testing.assert_allclose(
            q[mask], exact, rtol=ORACLE_RTOL, atol=1e-15
        )
        if unreliable:
            # Intended: the adapter's float64 factor cancels, absorbs the
            # free deaths, overflows or rounds subnormal sums here; SM1
            # meets the exact formula.
            continue
        np.testing.assert_allclose(q[mask], old[mask], rtol=RTOL, atol=ATOL)


def test_weightless_infeasible_cells_follow_the_weighted_rules():
    """Unit weights apply only where the weighted target is zero."""
    cells = [(2021, "female", 50)] * 3
    fixed = np.asarray([True, False, False])
    base = np.asarray([0.3, 0.2, 0.4])
    weights = np.asarray([2.0, 0.0, 0.0])
    for prescribed_q, free_q, sign in ((0.6, 0, -1), (0.1, 1, 1)):
        prescribed = np.asarray([prescribed_q, 0.2, 0.4])
        q, log = normalize_probabilities(
            base,
            np.asarray([1.0, 1.0, 3.0]),
            fixed,
            prescribed,
            cells,
            weights,
        )
        assert log.loc[0, "infeasible"]
        assert log.loc[0, "normalization_basis"] == "weights"
        assert np.sign(log.loc[0, "clipping_residual"]) == sign
        np.testing.assert_array_equal(q, [prescribed_q, free_q, free_q])
        assert_conserved(q, base, cells, weights, log)


def test_iterative_capping_intentionally_differs_from_adapter_one_pass():
    """Intended difference: reallocate the one-pass clipping shortfall."""
    base = np.asarray([0.8, 0.8, 0.1])
    fixed = np.asarray([True, False, False])
    prescribed = np.asarray([0.0, 0.8, 0.1])
    weights = np.ones(3)
    cells = [(2021, "female", 50)] * 3
    q, log = normalize_probabilities(
        base, np.ones(3), fixed, prescribed, cells, weights
    )
    old, _ = _net_of_di_origin(
        prescribed,
        base,
        fixed,
        np.zeros(3, dtype=int),
        np.full(3, 50),
        weights,
        SINGLE_YEAR_AGE_BANDS,
    )
    np.testing.assert_allclose(q, [0, 1, 0.7], rtol=RTOL, atol=ATOL)
    assert old.sum() < base.sum()
    assert not np.array_equal(q, old)
    assert_conserved(q, base, cells, weights, log)


class InventedYearlessBaseline:
    """Equivalent invented baseline for the engine's yearless interface."""

    def __init__(self, baseline, context):
        self.baseline = baseline
        self.context = context

    def probabilities(self, frame):
        return self.baseline(frame, self.context)


@PROPERTY
@given(st.integers(0, 10000), st.booleans(), PROBABILITY)
def test_step_unit_risks_draw_identical_deaths_with_or_without_registry(
    seed, registry, q_base
):
    frame = invented_frame(12)
    context = invented_context(frame, seed=seed, registry=registry)
    baseline = invented_baseline(q_base)
    model = DifferentialMortality(
        baseline, invented_spec(risk=1), weight_column=None
    )
    np.testing.assert_array_equal(
        model(frame, context), baseline(frame, context)
    )
    expected_rng = np.random.default_rng(seed)
    applied_rng = np.random.default_rng(seed)
    expected = apply_mortality(
        frame,
        context,
        expected_rng,
        model=InventedYearlessBaseline(baseline, context),
    )
    deaths, cells = {}, {}
    actual = apply_differential_mortality(
        frame,
        context,
        applied_rng,
        model=model,
        weight_column=None,
        death_log=deaths,
        cell_log=cells,
    )
    pd.testing.assert_frame_equal(actual, expected)
    assert actual["person_id"].is_monotonic_increasing
    assert applied_rng.bit_generator.state == expected_rng.bit_generator.state
    assert set(deaths[2021]["person_id"]) == set(frame["person_id"]) - set(
        actual["person_id"]
    )
    assert not cells[2021]["infeasible"].any()


@PROPERTY
@given(
    st.integers(0, 10000),
    st.booleans(),
    st.sampled_from(("di_origin", "population")),
    st.floats(0.02, 0.4),
)
def test_di_adapter_unit_risks_draw_identical_deaths(
    seed, registry, post_conversion, q_base
):
    frame = invented_frame(24, di=True)
    context = invented_context(frame, seed=seed, registry=registry)
    baseline = invented_baseline(q_base)
    rates = invented_rates(post_conversion=post_conversion)
    model = DifferentialMortality(
        baseline,
        invented_spec(risk=1),
        weight_column="weight",
        di_configuration=rates,
    )
    np.testing.assert_array_equal(
        model(frame, context), baseline(frame, context)
    )
    expected_deaths, expected_cells = {}, {}
    actual_deaths, actual_cells = {}, {}
    expected_rng = np.random.default_rng(seed)
    actual_rng = np.random.default_rng(seed)
    kwargs = dict(rates=rates, weight_column="weight")
    expected = apply_di_aware_mortality(
        frame,
        context,
        expected_rng,
        population_model=baseline,
        death_log=expected_deaths,
        cell_log=expected_cells,
        **kwargs,
    )
    actual = apply_di_aware_mortality(
        frame,
        context,
        actual_rng,
        population_model=model,
        death_log=actual_deaths,
        cell_log=actual_cells,
        **kwargs,
    )
    pd.testing.assert_frame_equal(actual, expected)
    pd.testing.assert_frame_equal(actual_deaths[2021], expected_deaths[2021])
    pd.testing.assert_frame_equal(actual_cells[2021], expected_cells[2021])
    assert actual_rng.bit_generator.state == expected_rng.bit_generator.state


class InventedZeroUniforms:
    """Expose every positive applied probability through the death log."""

    def random(self, size):
        return np.zeros(size)


@PROPERTY
@given(
    st.floats(0.02, 0.15),
    st.floats(1.0, 2.5),
    st.floats(1.0, 1.75),
    st.sampled_from(("di_origin", "population")),
    POSITIVE,
)
def test_composition_conserves_cells_preserves_ratios_and_fixes_di_q(
    q_base, risk, multiplier, post_conversion, weight_scale
):
    # Each cell has one entitled, one converted, and four other persons.
    frame = pd.concat(
        [
            invented_frame(6, di=True).assign(sex=sex, age=age)
            for sex in SEXES
            for age in (50, 70)
        ],
        ignore_index=True,
    )
    frame["person_id"] = np.arange(len(frame))
    frame["birth_year"] = 2020 - frame["age"]
    frame["weight"] = weight_scale
    frame["education"] = REF
    frame["race_hispanic_origin"] = REF
    context = invented_context(frame)
    baseline = invented_baseline(q_base)
    rates = invented_rates(
        multiplier=multiplier, post_conversion=post_conversion
    )
    model = DifferentialMortality(
        baseline,
        invented_spec(risk=risk),
        weight_column="weight",
        di_configuration=rates,
    )
    q_population, mechanism_cells = model.evaluate(frame, context)
    deaths, cells = {}, {}
    apply_di_aware_mortality(
        frame,
        context,
        InventedZeroUniforms(),
        population_model=model,
        rates=rates,
        weight_column="weight",
        death_log=deaths,
        cell_log=cells,
    )
    logged = deaths[2021].set_index("person_id").loc[frame["person_id"]]
    q_applied = logged["q_applied"].to_numpy()
    fixed = frame["di_entitled"].to_numpy() | (
        frame["di_conversion_year"].notna().to_numpy()
        & (post_conversion == "di_origin")
    )
    np.testing.assert_array_equal(
        q_population[fixed], baseline(frame, context)[fixed]
    )
    np.testing.assert_array_equal(
        logged["q_population"].to_numpy()[fixed],
        baseline(frame, context)[fixed],
    )
    assert not cells[2021]["infeasible"].any()
    for row in mechanism_cells.itertuples(index=False):
        cell = (frame["sex"] == row.sex) & (frame["age"] == row.age)
        assert np.sum(
            frame.loc[cell, "weight"] * q_applied[cell]
        ) == pytest.approx(
            row.baseline_expected_deaths - row.clipping_residual,
            rel=RTOL,
            abs=ATOL,
        )
        free = cell.to_numpy() & ~fixed
        assert np.all(q_applied[free] < 1)
        ratios_before = q_population[free] / q_population[free][0]
        ratios_after = q_applied[free] / q_applied[free][0]
        np.testing.assert_allclose(
            ratios_after, ratios_before, rtol=RTOL, atol=ATOL
        )


def composed_accounting(q_base, risk, multiplier, weights):
    """Run the model under the DI adapter and check each accounting link.

    A multiplier below one gives DI-origin persons less than their share
    of deaths, so the adapter scales everyone else up and can clip.
    """
    frame = pd.concat(
        [
            invented_frame(6, di=True).assign(sex=sex, age=age)
            for sex in SEXES
            for age in (50, 70)
        ],
        ignore_index=True,
    )
    frame["person_id"] = np.arange(len(frame))
    frame["birth_year"] = 2020 - frame["age"]
    frame["weight"] = weights
    context = invented_context(frame)
    baseline = invented_baseline(q_base)
    rates = invented_rates(multiplier=multiplier)
    retained = {}
    model = DifferentialMortality(
        baseline,
        invented_spec(risk=risk),
        weight_column="weight",
        di_configuration=rates,
        cell_log=retained,
    )
    deaths, cells = {}, {}
    apply_di_aware_mortality(
        frame,
        context,
        InventedZeroUniforms(),
        population_model=model,
        rates=rates,
        weight_column="weight",
        death_log=deaths,
        cell_log=cells,
    )
    # The adapter keeps only probabilities; the model's own log survives.
    _, mechanism = model.evaluate(frame, context)
    pd.testing.assert_frame_equal(retained[2021], mechanism)
    logged = deaths[2021].set_index("person_id").loc[frame["person_id"]]
    q_population = logged["q_population"].to_numpy()
    q_applied = logged["q_applied"].to_numpy()
    w = frame["weight"].to_numpy()
    fixed = (
        frame["di_entitled"].to_numpy()
        | frame["di_conversion_year"].notna().to_numpy()
    )
    np.testing.assert_array_equal(
        q_population[fixed], baseline(frame, context)[fixed]
    )
    adapter = cells[2021].set_index(["sex", "band_lower"])
    for row in mechanism.itertuples(index=False):
        cell = ((frame["sex"] == row.sex) & (frame["age"] == row.age)).values
        # Fixed rows sit at baseline, so SM1 conserves the baseline cell.
        assert not row.infeasible
        assert row.clipping_residual == 0
        assert np.sum(w[cell] * q_population[cell]) == pytest.approx(
            row.baseline_expected_deaths, rel=RTOL, abs=ATOL
        )
        # The adapter starts from SM1's deaths and logs its own result.
        netted = adapter.loc[(row.sex, row.age)]
        assert netted.expected_deaths_population_model == pytest.approx(
            row.applied_expected_deaths, rel=RTOL, abs=ATOL
        )
        assert np.sum(w[cell] * q_applied[cell]) == pytest.approx(
            netted.expected_deaths_applied, rel=RTOL, abs=ATOL
        )
        # Baseline deaths reach applied deaths through two separate gaps:
        # SM1's residual and the adapter's own clipping gap, its
        # population-model deaths minus its applied deaths.
        adapter_gap = (
            netted.expected_deaths_population_model
            - netted.expected_deaths_applied
        )
        assert np.sum(w[cell] * q_applied[cell]) == pytest.approx(
            row.baseline_expected_deaths - row.clipping_residual - adapter_gap,
            rel=RTOL,
            abs=ATOL,
        )
        free = cell & ~fixed
        if not (q_applied[free] == 1).any():
            # Without the adapter's one-pass clip, the composition conserves.
            assert netted.expected_deaths_applied == pytest.approx(
                row.baseline_expected_deaths, rel=RTOL, abs=ATOL
            )
        kept = free & (q_population < 1) & (q_applied < 1)
        if kept.sum() >= 2:
            np.testing.assert_allclose(
                q_applied[kept] / q_applied[kept][0],
                q_population[kept] / q_population[kept][0],
                rtol=RTOL,
                atol=ATOL,
            )
    return mechanism, q_applied, fixed, cells[2021]


@PROPERTY
@given(
    st.floats(0.3, 0.9),
    st.floats(1.0, 4.0),
    st.floats(0.05, 1.0),
    st.lists(st.floats(0.1, 10), min_size=24, max_size=24),
)
def test_composition_with_unequal_weights_keeps_every_accounting_link(
    q_base, risk, multiplier, weights
):
    composed_accounting(q_base, risk, multiplier, weights)


def test_composition_accounts_for_clipping_in_both_steps():
    weights = np.linspace(0.5, 6, 24)
    mechanism, q_applied, fixed, adapter = composed_accounting(
        0.8, 3.0, 0.1, weights
    )
    assert mechanism["clipped_persons"].sum() > 0
    assert (q_applied[~fixed] == 1).any()
    # SM1 conserves, but the adapter's one-pass clip loses deaths in a
    # feasible cell: the composition does not conserve there.
    gap = (
        adapter["expected_deaths_population_model"]
        - adapter["expected_deaths_applied"]
    )
    assert (gap > 1e-6).any()
    assert not adapter["infeasible"].any()
    assert (mechanism["clipping_residual"] == 0).all()


@PROPERTY
@given(st.floats(1, 20), st.sampled_from(("lifetime_earnings", "education")))
def test_ordered_earnings_and_education_risks_preserve_probability_order(
    risk, dimension
):
    frame = invented_frame(10).assign(sex="female")
    for name in DIMENSIONS:
        frame[name] = REF
    frame[dimension] = [REF] * 5 + [OTHER] * 5
    model = DifferentialMortality(
        invented_baseline(0.5), invented_spec(risk=risk), weight_column=None
    )
    q, _ = model.evaluate(frame, invented_context(frame))
    assert q[:5].max() <= q[5:].min()


@PROPERTY
@given(POSITIVE, st.integers(0, 10000))
def test_model_permutation_scaling_and_no_randomness(scale, seed):
    frame = invented_frame(12)
    frame["weight"] = np.arange(1, 13, dtype=float)
    context = invented_context(frame, seed=seed, registry=True)
    model = DifferentialMortality(
        invented_baseline(), invented_spec(), weight_column="weight"
    )
    rng = np.random.default_rng(seed)
    rng_before = deepcopy(rng.bit_generator.state)
    person_rng = context.person_generator(ProjectionModule.MORTALITY, 1)
    person_before = deepcopy(person_rng.bit_generator.state)
    with (
        patch.object(
            PeriodContext,
            "person_generator",
            side_effect=AssertionError("model requested a person generator"),
        ),
        patch(
            "numpy.random.default_rng",
            side_effect=AssertionError("model constructed a generator"),
        ),
    ):
        q, log = model.evaluate(frame, context)
        repeated, repeated_log = model.evaluate(frame, context)
    permutation = np.random.default_rng(seed).permutation(len(frame))
    permuted = model(frame.iloc[permutation], context)
    scaled = model(frame.assign(weight=frame["weight"] * scale), context)
    np.testing.assert_array_equal(q, repeated)
    pd.testing.assert_frame_equal(log, repeated_log)
    np.testing.assert_array_equal(permuted, q[permutation])
    np.testing.assert_allclose(scaled, q, rtol=RTOL, atol=ATOL)
    assert rng.bit_generator.state == rng_before
    assert person_rng.bit_generator.state == person_before


def test_model_gives_weightless_cells_their_unit_weight_probabilities():
    frame = invented_frame(12)
    context = invented_context(frame)
    logs = {}
    model = DifferentialMortality(
        invented_baseline(0.2),
        invented_spec(),
        weight_column="weight",
        cell_log=logs,
    )
    unit = model(frame, context)
    assert (logs[2021]["normalization_basis"] == "weights").all()
    weightless = model(frame.assign(weight=0.0), context)
    np.testing.assert_array_equal(weightless, unit)
    assert (weightless > 0).all()
    assert len(np.unique(weightless)) > 1
    assert (logs[2021]["normalization_basis"] == "persons").all()
    assert (logs[2021]["persons_target"] > 0).all()


def test_model_cell_log_must_be_a_mapping():
    with pytest.raises(TypeError, match="cell_log"):
        DifferentialMortality(
            invented_baseline(),
            invented_spec(),
            weight_column=None,
            cell_log=[],
        )


class InventedWideningPath:
    """A separately registered invented path changing only named years."""

    def __init__(self, base, changed_year):
        self.base = base
        self.changed_year = changed_year

    @property
    def years(self):
        return tuple(sorted(set(self.base.years) | {self.changed_year}))

    def coefficients(self, year):
        table = self.base.coefficients(year)
        if year == self.changed_year:
            table["log_relative_risk"] *= 2
        return table


@PROPERTY
@given(st.integers(2021, 2100), st.floats(1.1, 4))
def test_hold_last_refuse_before_first_and_pluggable_named_year(year, risk):
    frame = invented_frame(6, year=year)
    path = HoldLastCoefficientPath(invented_table(risk=risk))
    spec = invented_spec(path=path)
    ages = frame["age"].to_numpy()
    held, _ = spec.relative_risks(frame, year, ages)
    observed, _ = spec.relative_risks(frame, 2020, ages)
    np.testing.assert_array_equal(held, observed)
    with pytest.raises(ValueError, match="precedes"):
        spec.relative_risks(frame, 2019, ages)
    alternative = invented_spec(path=InventedWideningPath(path, year))
    changed, _ = alternative.relative_risks(frame, year, ages)
    unchanged, _ = alternative.relative_risks(frame, year + 1, ages)
    np.testing.assert_allclose(changed, held**2, rtol=RTOL, atol=ATOL)
    np.testing.assert_array_equal(unchanged, held)


@PROPERTY
@given(st.sampled_from((np.nan, np.inf, -np.inf, -1000.0, 1000.0)))
def test_invalid_coefficients_are_refused(value):
    table = invented_table()
    table.loc[table["category"] == OTHER, "log_relative_risk"] = value
    with pytest.raises(ValueError, match="finite and positive"):
        invented_spec(path=HoldLastCoefficientPath(table))


@PROPERTY
@given(st.sampled_from((0.0, -1.0, np.nan, np.inf, -np.inf)))
def test_invalid_relative_risks_are_refused(value):
    with pytest.raises(ValueError, match="relative risks"):
        normalize_probabilities(
            np.asarray([0.2]),
            np.asarray([value]),
            np.asarray([False]),
            np.asarray([0.2]),
            [(2021, "female", 50)],
            np.ones(1),
        )


@PROPERTY
@given(st.sampled_from(("age", "sex", "weight", *DIMENSIONS)))
def test_missing_model_columns_are_refused(column):
    frame = invented_frame().drop(columns=column)
    model = DifferentialMortality(
        invented_baseline(), invented_spec(), weight_column="weight"
    )
    with pytest.raises(ValueError, match="missing"):
        model(frame, invented_context(frame))


@PROPERTY
@given(st.sampled_from(DIMENSIONS), st.sampled_from((None, UNCLASSIFIED)))
def test_unclassified_refusal_and_reference_counts_are_explicit(
    dimension, value
):
    frame = invented_frame()
    frame.loc[0, dimension] = value
    context = invented_context(frame)
    refusing = DifferentialMortality(
        invented_baseline(), invented_spec(), weight_column=None
    )
    with pytest.raises(UnclassifiedValueError) as raised:
        refusing(frame, context)
    assert raised.value.cell_log["unclassified_refuse"].sum() == 1
    reference = DifferentialMortality(
        invented_baseline(),
        invented_spec(rule="reference"),
        weight_column=None,
    )
    q, log = reference.evaluate(frame, context)
    substituted = frame.copy()
    substituted.loc[0, dimension] = REF
    np.testing.assert_array_equal(q, reference(substituted, context))
    assert log["unclassified_reference"].sum() == 1
    assert log[f"{dimension}_unclassified_reference"].sum() == 1
    assert log["unclassified_refuse"].sum() == 0


@PROPERTY
@given(st.sampled_from(DIMENSIONS))
def test_unknown_categories_are_refused_even_under_reference_rule(dimension):
    frame = invented_frame()
    frame.loc[0, dimension] = "invented_unknown"
    model = DifferentialMortality(
        invented_baseline(),
        invented_spec(rule="reference"),
        weight_column=None,
    )
    with pytest.raises(ValueError, match="unknown category"):
        model(frame, invented_context(frame))


@PROPERTY
@given(st.integers(1, 10), st.booleans())
def test_age_cell_mismatch_is_refused_even_when_adapter_validation_off(
    offset, validate_age
):
    frame = invented_frame(di=True)
    frame.loc[0, "age"] += offset
    spec = DIEntitlementSpec(validate_age_column=validate_age)
    model = DifferentialMortality(
        invented_baseline(),
        invented_spec(),
        weight_column=None,
        di_configuration=spec,
    )
    with pytest.raises(ValueError, match="before capping"):
        model(frame, invented_context(frame))


def test_probability_attribute_is_refused_and_model_has_context_only_api():
    frame = invented_frame()
    context = invented_context(frame)
    baseline = invented_baseline()
    spec = invented_spec()
    model = DifferentialMortality(baseline, spec, weight_column=None)
    assert not hasattr(model, "probabilities")
    with pytest.raises(ValueError, match="probabilities"):
        DifferentialMortality(
            InventedYearlessBaseline(baseline, context),
            spec,
            weight_column=None,
        )

    class InventedInvalidInterface(DifferentialMortality):
        probabilities = True

    with pytest.raises(ValueError, match="probabilities"):
        InventedInvalidInterface(baseline, spec, weight_column=None)


def test_capped_age_cells_match_the_single_year_di_adapter_cells():
    frame = invented_frame(6, di=True).assign(age=125, birth_year=1895)
    context = invented_context(frame)
    rates = invented_rates()
    model = DifferentialMortality(
        invented_baseline(),
        invented_spec(),
        weight_column=None,
        di_configuration=rates,
    )
    _, log = model.evaluate(frame, context)
    cells = {}
    apply_di_aware_mortality(
        frame,
        context,
        np.random.default_rng(1),
        population_model=model,
        rates=rates,
        weight_column=None,
        cell_log=cells,
    )
    assert set(log["age"]) == {120}
    assert set(cells[2021]["band_lower"]) == {120}
    assert set(cells[2021]["band_upper"]) == {120}
    assert set(log["sex"]) == set(cells[2021]["sex"])


def test_model_requires_explicit_weights_and_matching_di_configuration():
    with pytest.raises(TypeError):
        DifferentialMortality(invented_baseline(), invented_spec())
    frame = invented_frame(di=True)
    context = invented_context(frame)
    model = DifferentialMortality(
        invented_baseline(), invented_spec(), weight_column=None
    )
    with pytest.raises(ValueError, match="di_configuration"):
        model(frame, context)
    configured = replace(model, di_configuration=DIEntitlementSpec())
    with pytest.raises(ValueError, match="missing"):
        configured(frame.drop(columns="di_conversion_year"), context)
