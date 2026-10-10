"""Unit tests with INVENTED probability schedules, never microdata.

The independent forward-column and backward-recursion implementations
must agree wherever survivors are numerically positive.  Structural
invariants apply to arbitrary schedules, rather than assuming that
conditional remaining lifetime decreases with attained age.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data.life_table import (
    RADIX,
    life_expectancy,
    life_expectancy_profile,
    period_life_table,
)

PROBABILITY = st.floats(min_value=0.0, max_value=0.95, allow_subnormal=False)
SEPARATION = st.floats(min_value=0.0, max_value=1.0, allow_subnormal=False)


@st.composite
def probability_schedules(draw):
    """INVENTED schedules with a positive final probability."""
    q = draw(st.lists(PROBABILITY, min_size=2, max_size=120))
    q[-1] = draw(
        st.floats(min_value=0.05, max_value=1.0, allow_subnormal=False)
    )
    return np.asarray(q)


def test_invented_closed_table_with_known_columns():
    table = period_life_table([0.1, 0.2, 1.0], f0=0.25, radix=1000)
    np.testing.assert_allclose(table.lx, [1000, 900, 720])
    np.testing.assert_allclose(table.dx, [100, 180, 720])
    np.testing.assert_allclose(table.Lx, [975, 810, 360])
    np.testing.assert_allclose(table.Tx, [2145, 1170, 360])
    np.testing.assert_allclose(table.ex, [2.145, 1.3, 0.5])
    np.testing.assert_allclose(
        life_expectancy_profile(table.qx, f0=0.25), table.ex
    )


@pytest.mark.parametrize("q", [0.1, 0.25, 0.5, 1.0])
def test_invented_constant_probability_has_geometric_lifetime(q):
    # Geometric waiting time to death, less a half-year separation.
    expected = 1.0 / q - 0.5
    profile = life_expectancy_profile([q] * 120, f0=0.5)
    np.testing.assert_allclose(profile, expected)
    assert life_expectancy([q] * 120, 119) == pytest.approx(expected)


def test_invented_open_closure_matches_explicit_long_geometric_tail():
    q = np.array([0.1, 0.2, 0.25])
    table = period_life_table(q, f0=0.25, radix=1000)
    survivors = table.lx[-1]
    tail_person_years = []
    for _ in range(500):
        tail_person_years.append(survivors * 0.875)
        survivors *= 0.75
    assert table.Lx[-1] == pytest.approx(sum(tail_person_years))
    assert table.Tx[-1] == table.Lx[-1]
    assert life_expectancy(q, 2) == pytest.approx(3.5)


def test_invented_deathless_initial_years_add_whole_years():
    assert life_expectancy([0, 0, 1], 0, f0=0.3) == 2.5
    assert life_expectancy([0, 0, 1], 1) == 1.5


def test_invented_early_extinction_preserves_conditional_recursion():
    q = [1, 0.3, 0.7, 1]
    table = period_life_table(q, f0=0.2)
    np.testing.assert_array_equal(table.lx[1:], 0)
    assert table.ex[0] == pytest.approx(0.8)
    assert np.isnan(table.ex[1:]).all()
    profile = life_expectancy_profile(q, f0=0.2)
    assert np.isfinite(profile).all()
    assert profile[0] == pytest.approx(0.8)
    assert profile[-1] == 0.5


def test_invented_survivorship_underflow_keeps_recursion_defined():
    q = np.full(120, 0.999)
    table = period_life_table(q, f0=0.5)
    assert table.lx[-1] == 0
    assert np.isnan(table.ex[-1])
    profile = life_expectancy_profile(q, f0=0.5)
    assert np.isfinite(profile).all()
    np.testing.assert_allclose(profile, 1 / 0.999 - 0.5)


def test_infant_separation_is_required_only_at_birth():
    q = [0.1, 0.2, 1]
    profile = life_expectancy_profile(q)
    assert np.isnan(profile[0])
    assert np.isfinite(profile[1:]).all()
    assert life_expectancy(q, 1) == pytest.approx(1.3)
    with pytest.raises(ValueError, match="needs the separation"):
        life_expectancy(q, 0)


def test_columns_are_read_only_and_input_is_copied():
    q = np.array([0.1, 0.2, 1])
    table = period_life_table(q, f0=0.25)
    q[0] = 0.9
    assert table.qx[0] == 0.1
    for field in ("qx", "lx", "dx", "Lx", "Tx", "ex"):
        column = getattr(table, field)
        assert not column.flags.writeable
        with pytest.raises(ValueError, match="read-only"):
            column[0] = 0
    with pytest.raises(FrozenInstanceError):
        table.f0 = 0.5
    assert not life_expectancy_profile(table.qx).flags.writeable
    assert table.radix == RADIX


@pytest.mark.parametrize(
    "q",
    [
        [],
        [0.5],
        [[0.1, 1]],
        [np.nan, 1],
        [np.inf, 1],
        [-0.01, 1],
        [1.01, 1],
        [0.1, 0],
    ],
)
def test_invalid_probability_schedules_are_refused(q):
    with pytest.raises(ValueError):
        period_life_table(q, f0=0.5)
    with pytest.raises(ValueError):
        life_expectancy_profile(q)
    with pytest.raises(ValueError):
        life_expectancy(q, 1)


@pytest.mark.parametrize("f0", [-0.1, 1.1, np.nan, np.inf])
def test_invalid_infant_separation_is_refused(f0):
    q = [0.1, 1]
    with pytest.raises(ValueError, match="f0"):
        period_life_table(q, f0=f0)
    with pytest.raises(ValueError, match="f0"):
        life_expectancy_profile(q, f0=f0)
    with pytest.raises(ValueError, match="f0"):
        life_expectancy(q, 0, f0=f0)


@pytest.mark.parametrize("radix", [0, -1, np.nan, np.inf])
def test_invalid_radix_is_refused(radix):
    with pytest.raises(ValueError, match="radix"):
        period_life_table([0.1, 1], f0=0.5, radix=radix)


@pytest.mark.parametrize(
    "age", [-1, 3, 0.5, True, None, np.nan, np.inf, -np.inf, "one"]
)
def test_invalid_age_is_refused(age):
    with pytest.raises(ValueError, match="age"):
        life_expectancy([0.1, 0.2, 1], age, f0=0.5)


@settings(max_examples=60, deadline=None)
@given(q=probability_schedules(), f0=SEPARATION)
def test_survivorship_person_years_and_deaths_obey_invariants(q, f0):
    table = period_life_table(q, f0=f0)
    assert np.all(table.lx >= 0)
    assert np.all(np.diff(table.lx) <= 0)
    assert np.all(table.dx >= 0)
    assert np.all(table.Lx >= 0)
    assert np.all(table.Tx >= 0)
    assert np.all(np.diff(table.Tx) <= 0)
    np.testing.assert_allclose(
        table.lx[1:], table.lx[:-1] * (1 - q[:-1]), rtol=2e-13
    )
    np.testing.assert_allclose(
        table.lx[:-1] - table.lx[1:], table.dx[:-1], atol=2e-11
    )
    np.testing.assert_allclose(
        table.Tx[:-1] - table.Tx[1:], table.Lx[:-1], atol=2e-9
    )


@settings(max_examples=60, deadline=None)
@given(
    q=probability_schedules(),
    f0=SEPARATION,
    radix=st.floats(min_value=0.01, max_value=1e9, allow_subnormal=False),
)
def test_implementations_agree_and_expectancy_is_radix_independent(
    q, f0, radix
):
    standard = period_life_table(q, f0=f0)
    scaled = period_life_table(q, f0=f0, radix=radix)
    profile = life_expectancy_profile(q, f0=f0)
    np.testing.assert_allclose(standard.ex, profile, rtol=2e-12)
    np.testing.assert_allclose(scaled.ex, profile, rtol=2e-12)
    for field in ("lx", "dx", "Lx", "Tx"):
        np.testing.assert_allclose(
            getattr(scaled, field),
            getattr(standard, field) * radix / RADIX,
            rtol=2e-12,
        )
    for age in (0, len(q) // 2, len(q) - 1):
        assert life_expectancy(q, age, f0=f0) == profile[age]


@settings(max_examples=60, deadline=None)
@given(
    q=probability_schedules(),
    f0=SEPARATION,
    increase=SEPARATION,
)
def test_higher_mortality_cannot_increase_life_expectancy(q, f0, increase):
    higher_q = q + (1 - q) * increase
    initial = life_expectancy_profile(q, f0=f0)
    higher = life_expectancy_profile(higher_q, f0=f0)
    assert np.all(higher <= initial + 2e-13)


@settings(max_examples=40, deadline=None)
@given(q=probability_schedules(), first_f0=SEPARATION, second_f0=SEPARATION)
def test_separation_changes_only_birth_expectancy(q, first_f0, second_f0):
    first = life_expectancy_profile(q, f0=first_f0)
    second = life_expectancy_profile(q, f0=second_f0)
    np.testing.assert_array_equal(first[1:], second[1:])
    assert second[0] - first[0] == pytest.approx(
        (first_f0 - second_f0) * q[0], abs=2e-13
    )
