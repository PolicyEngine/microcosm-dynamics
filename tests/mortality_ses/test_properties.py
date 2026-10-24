"""Accounting properties using only invented populations and coefficients.

All categories, coefficients, probability tables and DI rates below are
INVENTED. These tests establish mechanism identities, not an empirical
mortality gradient. Conservation uses absolute and relative tolerance 1e-12
for finite double-precision products, sums and the adapter's cell arithmetic.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
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
        if not row.clipped_persons and not row.infeasible:
            assert row.clipping_residual == 0


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


@PROPERTY
@given(invented_adapter_cells())
def test_unit_risk_matches_adapter_on_every_unclipped_cell(inputs):
    """Includes zero weights, infeasible cells and weightless free rows."""
    base, fixed, prescribed, weights, sex, age = inputs
    cells = [(2021, SEXES[s], int(a)) for s, a in zip(sex, age, strict=True)]
    q, log = normalize_probabilities(
        base, np.ones(len(base)), fixed, prescribed, cells, weights
    )
    old, _ = _net_of_di_origin(
        prescribed, base, fixed, sex, age, weights, SINGLE_YEAR_AGE_BANDS
    )
    for row in log.itertuples(index=False):
        if row.clipped_persons:
            continue  # Intended: iterative capping versus one-pass clipping.
        mask = np.asarray(
            [cell == (row.year, row.sex, row.age) for cell in cells]
        )
        np.testing.assert_allclose(q[mask], old[mask], rtol=RTOL, atol=ATOL)


def test_weightless_free_rows_in_infeasible_cells_keep_unit_weights():
    """Fixed rows carry the weight; no free factor can conserve the cell."""
    cells = [(2021, "female", 50)] * 3
    fixed = np.asarray([True, False, False])
    for prescribed_q, sign in ((0.6, -1), (0.1, 1)):
        base = np.asarray([0.3, 0.2, 0.4])
        prescribed = np.asarray([prescribed_q, 0.2, 0.4])
        weights = np.asarray([2.0, 0.0, 0.0])
        q, log = normalize_probabilities(
            base,
            np.asarray([1.0, 1.0, 3.0]),
            fixed,
            prescribed,
            cells,
            weights,
        )
        unit, _ = normalize_probabilities(
            base, np.asarray([1.0, 1.0, 3.0]), fixed, base, cells, np.ones(3)
        )
        assert log.loc[0, "infeasible"]
        assert np.sign(log.loc[0, "clipping_residual"]) == sign
        assert q[0] == prescribed_q
        np.testing.assert_array_equal(q[1:], unit[1:])
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
    model = DifferentialMortality(
        invented_baseline(0.2), invented_spec(), weight_column="weight"
    )
    unit = model(frame, context)
    weightless = model(frame.assign(weight=0.0), context)
    np.testing.assert_array_equal(weightless, unit)
    assert (weightless > 0).all()
    assert len(np.unique(weightless)) > 1


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
