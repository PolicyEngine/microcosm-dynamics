"""Invented-input invariants for d1408's local diagnostic helpers."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.ss import benefits
from populace_dynamics.ss.statutory_delayed_credit import delayed_credit
from scripts.d1408_common import (
    aggregate_group,
    credit_convention,
    flagged,
    safe_relative,
)
from tests.track_b_gross_benefit_support import ssa_params

PARAMS = ssa_params()


@settings(deadline=None)
@given(st.integers(1900, 2000), st.integers(-24, 180))
def test_flagged_region_is_exact(birth, late):
    expected = late > (0 if birth < 1917 else 48) and birth <= 1942
    assert flagged(late, birth) == expected


@pytest.mark.parametrize(
    "birth,late,expected",
    [
        (1916, 0, False),
        (1916, 1, True),
        (1917, 48, False),
        (1917, 49, True),
        (1942, 49, True),
        (1943, 60, False),
    ],
)
def test_flagged_region_boundaries(birth, late, expected):
    assert flagged(late, birth) is expected


@settings(deadline=None)
@given(st.integers(1917, 2000), st.integers(-12, 150))
def test_statutory_differential_matches_isolated_reference(birth, late):
    expected = delayed_credit(late, birth, PARAMS)
    original = benefits.delayed_credit
    with credit_convention(statutory=True):
        assert benefits.delayed_credit(late, birth, PARAMS) == expected
    assert benefits.delayed_credit is original


@settings(deadline=None)
@given(st.integers(1900, 2000), st.integers(-12, 150))
def test_legacy_context_is_identical_and_restores_on_failure(birth, late):
    original = benefits.delayed_credit
    expected = original(late, birth, PARAMS)
    with pytest.raises(RuntimeError):
        with credit_convention(statutory=False):
            assert benefits.delayed_credit(late, birth, PARAMS) == expected
            raise RuntimeError("invented failure")
    assert benefits.delayed_credit is original


@settings(deadline=None)
@given(st.integers(1900, 1916), st.integers(1, 150))
def test_pre1917_is_only_a_legacy_placeholder(birth, late):
    expected = benefits.delayed_credit(late, birth, PARAMS)
    with credit_convention(statutory=True):
        assert benefits.delayed_credit(late, birth, PARAMS) == expected
    with pytest.raises(ValueError, match=r"402\(w\)\(6\)\(A\)"):
        delayed_credit(late, birth, PARAMS)


@settings(deadline=None)
@given(st.integers(1, 9))
def test_small_cell_suppresses_every_quantity(n):
    ids = list(range(n))
    result = aggregate_group(ids, ids, dict.fromkeys(ids, 1.5), 100)
    assert set(result.values()) == {"<10"}


@settings(deadline=None)
@given(st.lists(st.integers(0, 30), min_size=10, max_size=100))
def test_aggregate_deduplication_order_independence_and_weight_identity(ids):
    weights = {person: person + 0.5 for person in ids}
    original = aggregate_group(ids, ids, weights, 1000)
    assert original == aggregate_group(ids[::-1] * 2, ids * 3, weights, 1000)
    if len(set(ids)) >= 10:
        assert original["people"] == len(set(ids))
        assert original["weight"] == sum(weights.values())
        assert original["admitted_weight_share"] == original["weight"] / 1000


@settings(deadline=None)
@given(st.floats(1, 1e12, allow_nan=False, allow_infinity=False))
def test_empty_group_stays_in_denominator(denominator):
    assert aggregate_group([], [], {}, denominator) == {
        "people": 0,
        "worker_records": 0,
        "weight": 0,
        "admitted_weight_share": 0,
    }


@pytest.mark.parametrize(
    "name", ["comparison", "comparator", "seal", "dynasim"]
)
def test_restricted_path_names_are_refused(name):
    assert not safe_relative(f"src/{name.upper()}/input.py")
    assert safe_relative("src/populace_dynamics/ss/benefits.py")


@settings(deadline=None)
@given(
    st.sampled_from(["comparison", "comparator", "seal", "dynasim"]),
    st.text(alphabet="abcDEF012._/", max_size=30),
    st.booleans(),
)
def test_restricted_names_are_refused_in_any_path_position(
    name, suffix, upper
):
    word = name.upper() if upper else name
    assert not safe_relative(f"src/{suffix}{word}/input.py")
