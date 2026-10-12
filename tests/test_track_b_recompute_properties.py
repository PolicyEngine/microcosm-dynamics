"""R3 invariants and differentials over invented Hypothesis histories."""

import math
from dataclasses import replace
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.ss import benefits as oracle
from populace_dynamics.ss.statutory_aime import (
    aime_with_computation_years,
    benefit_computation_years,
)
from populace_dynamics.track_b import recompute as r
from populace_dynamics.track_b.gross_benefits import (
    FamilyTargetBlocked,
    InvalidFamilyInput,
    YearMonth,
    count_family_outcomes,
)
from tests.test_track_b_recompute import (
    PARAMS,
    annual,
    basis,
    death_annual,
    explicit_early_zeros,
)


@settings(deadline=None)
@given(st.integers(0, 100_000), st.integers(1983, 2026))
def test_exact_pia_matches_float_oracle_to_one_nanodollar(aime, year):
    """Same bends/factors, tolerance1e-9 for float representation only."""
    bends = r.eligibility_bend_points(year, PARAMS)
    assert bends == tuple(int(v) for v in PARAMS.bend_points(year))
    assert (
        abs(float(r.exact_pia(aime, bends)) - oracle.pia(aime, year, PARAMS))
        <= 1e-9
    )


@settings(deadline=None)
@given(
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
    st.integers(2, 3),
)
def test_complete_integer_aime_matches_reused_statutory_oracle(values, count):
    original = basis(computation_years=count)
    history = explicit_early_zeros(
        dict(zip(range(2018, 2021), values, strict=True))
    )
    assert r.earnings_aime(
        history, original, 2020, PARAMS
    ) == aime_with_computation_years(
        history, count, PARAMS, indexing_year=2018
    )


@settings(deadline=None)
@given(st.integers(1983, 2026))
def test_frozen_ordinary_year_count_matches_original_statutory_count(year):
    assert max(2, min(35, year - 1956)) == benefit_computation_years(year - 62)


@settings(max_examples=50, deadline=None)
@given(
    st.integers(1983, 2020),
    st.integers(0, 100_000),
    st.integers(0, 100_000),
    st.integers(0, 100_000),
    st.integers(1, 100_000),
)
def test_original_index_count_and_caps_against_independent_fraction_reference(
    year, early, later1, later2, cap
):
    from tests.track_b_gross_benefit_support import ssa_params

    params = ssa_params(wage_base={1951: cap})
    count = max(2, min(35, year - 1956))
    original = basis(
        eligibility_year=year,
        indexing_year=year - 2,
        computation_years=count,
        bend_points=r.eligibility_bend_points(year, params),
        entitlement_month=YearMonth(year, 6),
    )
    history = {base_year: 0 for base_year in range(1951, 2021)}
    history.update({1951: early, 2019: later1, 2020: later2})
    early_indexed = (
        min(early, cap)
        * F(str(params.nawi[year - 2]))
        / F(str(params.nawi[1951]))
    )
    expected = math.floor(
        (early_indexed + min(later1, cap) + min(later2, cap)) / (12 * count)
    )
    assert r.earnings_aime(history, original, 2020, params) == expected
    changed_future_nawi = replace(params, nawi=params.nawi | {2019: 1_000_000})
    assert (
        r.earnings_aime(history, original, 2020, changed_future_nawi)
        == expected
    )


@settings(deadline=None)
@given(st.integers(0, 50_000), st.integers(0, 50_000), st.integers(0, 50_000))
def test_ordinary_recomputed_pia_never_decreases(old_dimes, first, second):
    result = annual(
        history={2018: first, 2019: second, 2020: first + second},
        eligibility_pia_of_record=F(old_dimes, 10),
    )
    assert result.decision.pia_in_force >= result.decision.pia_of_record
    assert result.eligibility_pia_in_force >= F(old_dimes, 10)


@settings(deadline=None)
@given(
    st.lists(st.integers(0, 100_000), min_size=6, max_size=6),
    st.integers(0, 20),
)
def test_annual_fold_is_non_decreasing_and_matches_individual_steps(
    values, cola
):
    history = explicit_early_zeros(
        dict(zip(range(2018, 2024), values, strict=True))
    )
    results = r.recompute_sequence(
        basis(),
        history,
        [2020, 2021, 2022, 2023],
        0,
        PARAMS,
        {year: cola for year in range(2020, 2024)},
    )
    pia = 0
    last_current = 0
    for year, result in zip(range(2020, 2024), results, strict=True):
        independent = r.annual_recomputation(
            basis(),
            history,
            year,
            pia,
            PARAMS,
            {y: cola for y in range(2020, 2024)},
        )
        assert result == independent
        assert result.eligibility_pia_in_force >= pia
        assert result.decision.pia_in_force >= last_current
        pia = result.eligibility_pia_in_force
        last_current = result.decision.pia_in_force


@settings(deadline=None)
@given(
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
    st.integers(0, 10_000_000),
    st.integers(0, 10_000_000),
)
def test_later_earnings_never_change_earlier_results(values, later1, later2):
    prefix = dict(zip(range(2018, 2021), values, strict=True))
    first = annual(history=prefix | {2021: later1, 2022: later2})
    second = annual(history=prefix | {2021: later2, 2022: r.UNAVAILABLE})
    assert first == second


@settings(deadline=None)
@given(
    st.integers(2018, 2020),
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
    st.booleans(),
)
def test_unavailable_year_never_becomes_zero(year, values, omit):
    history = explicit_early_zeros(
        dict(zip(range(2018, 2021), values, strict=True))
    )
    if omit:
        del history[year]
    else:
        history[year] = r.UNAVAILABLE
    with pytest.raises(InvalidFamilyInput, match=str(year)):
        annual(history=history)


@settings(deadline=None)
@given(st.integers(1951, 2020), st.booleans())
def test_every_statutory_base_year_requires_explicit_availability(year, omit):
    history = {base_year: 0 for base_year in range(1951, 2021)}
    if omit:
        del history[year]
    else:
        history[year] = r.UNAVAILABLE
    with pytest.raises(InvalidFamilyInput, match=str(year)):
        r.annual_recomputation(basis(), history, 2020, 0, PARAMS, {2020: 0})


@settings(deadline=None)
@given(
    st.lists(st.integers(0, 100_000), min_size=3, max_size=3),
    st.integers(1, 100_000),
)
def test_aime_caps_each_year_before_selection(values, cap):
    from tests.track_b_gross_benefit_support import ssa_params

    params = ssa_params(wage_base={1951: cap})
    history = explicit_early_zeros(
        dict(zip(range(2018, 2021), values, strict=True))
    )
    capped = {year: min(value, cap) for year, value in history.items()}
    assert r.earnings_aime(history, basis(), 2020, params) == r.earnings_aime(
        capped, basis(), 2020, params
    )


@settings(deadline=None)
@given(st.integers(0, 100_000), st.integers(0, 100_000))
def test_pia_is_dime_multiple_monotone_and_nonnegative(aime, increment):
    first = r.exact_pia(aime, basis().bend_points)
    second = r.exact_pia(aime + increment, basis().bend_points)
    assert (first * 10).denominator == 1
    assert (second * 10).denominator == 1
    assert 0 <= first <= second


@settings(deadline=None)
@given(st.integers(0, 20_000), st.integers(0, 20_000), st.booleans())
def test_dollar_rule_exact_equivalence(old, candidate, earnings):
    decision = r.recomputation_decision(
        F(old, 10), F(candidate, 10), has_earnings=earnings
    )
    assert decision.applied == (earnings and candidate - old >= 10)
    assert decision.pia_in_force == F(
        candidate if decision.applied else old, 10
    )


@settings(deadline=None)
@given(st.lists(st.integers(0, 100_000), min_size=3, max_size=3))
def test_earnings_mapping_order_independent_and_deterministic(values):
    items = list(zip(range(2018, 2021), values, strict=True))
    forward = annual(history=dict(items))
    backward = annual(history=dict(reversed(items)))
    assert forward == backward == annual(history=dict(items))


@settings(deadline=None)
@given(st.integers(1, 100), st.integers(1, 100))
def test_refusals_retained_in_weighted_denominator(
    supported_weight, refused_weight
):
    supported = r.evaluate_recomputation("yes", supported_weight, annual)
    refused = r.evaluate_recomputation(
        "no",
        refused_weight,
        lambda: annual(basis=replace(basis(), formula=r.PIAFormula.OLD_START)),
    )
    counts = count_family_outcomes([supported, refused])
    assert counts.rows == 2
    assert counts.weight == supported_weight + refused_weight
    assert counts.supported_weight_share == F(
        supported_weight, supported_weight + refused_weight
    )
    with pytest.raises(FamilyTargetBlocked):
        r.weighted_recomputed_pia([supported, refused])


@settings(deadline=None)
@given(
    st.sampled_from(list(r.PIAFormula)[1:]),
    st.sampled_from([r.UNAVAILABLE, -1, "bad"]),
)
def test_input_error_is_never_classified_as_coverage(formula, bad):
    with pytest.raises(InvalidFamilyInput):
        r.evaluate_recomputation(
            "invalid",
            1,
            lambda: annual(
                basis=replace(basis(), formula=formula),
                history={2018: bad, 2019: 0, 2020: 0},
            ),
        )


@settings(max_examples=40, deadline=None)
@given(st.integers(7, 11), st.integers(0, 99))
def test_death_effective_month_excludes_later_cola(month, later_cola):
    result = death_annual(month, later_cola)
    assert result.effective_month == YearMonth(2026, month)
    assert result.decision.candidate_pia == 270
