"""INVENTED populations, categories, coefficients and death probabilities."""

from copy import deepcopy
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.baselines.base import BaselineYearAwareMortality
from populace_dynamics.engine import di_entitlement
from populace_dynamics.engine.di_entitlement import apply_di_aware_mortality
from populace_dynamics.engine.di_entitlement_rates import (
    MAX_AGE,
    SINGLE_YEAR_AGE_BANDS,
    DIEntitlementRates,
    DIEntitlementSpec,
)
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import ProjectionRNGRegistry
from populace_dynamics.engine.steps import (
    AgeSexMortalityModel,
    apply_mortality,
)
from populace_dynamics.mortality_ses.model import DifferentialMortality
from populace_dynamics.mortality_ses.specification import (
    DIMENSIONS,
    HoldLastCoefficientPath,
    RelativeRiskSpec,
    RiskDimension,
    UnclassifiedValueError,
)
from populace_dynamics.mortality_ses.step import apply_differential_mortality


def invented_specification(risk=1.0, rule="refuse"):
    dimensions = tuple(
        RiskDimension(
            name,
            name,
            ("invented_reference", "invented_higher_risk"),
            "invented_reference",
            ("invented_unclassified",),
        )
        for name in DIMENSIONS
    )
    table = pd.DataFrame(
        [
            {
                "year": 2020,
                "dimension": dimension.name,
                "category": category,
                "sex": sex,
                "age_lower": 0,
                "age_upper": MAX_AGE,
                "log_relative_risk": (
                    np.log(risk) if category == "invented_higher_risk" else 0.0
                ),
            }
            for dimension in dimensions
            for category in dimension.categories
            for sex in ("female", "male")
        ]
    )
    return RelativeRiskSpec(dimensions, HoldLastCoefficientPath(table), rule)


def invented_baseline(q=0.2):
    return BaselineYearAwareMortality(
        "invented_baseline",
        {2020: {sex: np.full(MAX_AGE + 1, q) for sex in ("female", "male")}},
    )


def invented_frame(*, di=False):
    frame = pd.DataFrame(
        {
            "person_id": [8, 2, 5, 1, 9, 3],
            "age": [40] * 6,
            "sex": ["female"] * 6,
            "birth_year": [1979] * 6,
            "year": [2019] * 6,
            "weight": [1.0, 2.0, 1.0, 3.0, 1.0, 2.0],
            **{name: ["invented_reference"] * 6 for name in DIMENSIONS},
        }
    )
    frame.loc[[1, 2, 4], "lifetime_earnings"] = "invented_higher_risk"
    if di:
        frame["di_entitled"] = [True, False, False, False, False, False]
        frame["di_conversion_year"] = pd.array(
            [None, 2018, None, None, None, None], dtype="Int64"
        )
        for column in ("di_award_year", "di_award_age", "di_recovery_year"):
            frame[column] = pd.array([None] * len(frame), dtype="Int64")
        frame["di_converted"] = [False, True, False, False, False, False]
        frame["di_event"] = "none"
    return frame


def invented_context(frame, *, registry=False):
    return PeriodContext(
        1,
        2020,
        0,
        {},
        rng_registry=ProjectionRNGRegistry(19, 25) if registry else None,
        person_ordinals={
            person: index
            for index, person in enumerate(sorted(frame["person_id"]))
        },
    )


def invented_rates(death=0.1, q=0.2):
    shape = (2, MAX_AGE + 1)
    return DIEntitlementRates(
        spec=DIEntitlementSpec(),
        incidence=np.zeros(shape),
        recovery_attained=np.zeros(shape),
        death_attained=np.full(shape, death),
        population_reference_death=np.full(shape, q),
        recovery_select=None,
        death_select=None,
        recovery_level_factor=1.0,
        death_level_factor=1.0,
    )


@pytest.mark.parametrize("registry", [False, True])
def test_identity_probabilities_and_step_deaths(registry):
    frame = invented_frame()
    context = invented_context(frame, registry=registry)
    baseline = invented_baseline()
    model = DifferentialMortality(
        baseline, invented_specification(), weight_column="weight"
    )
    np.testing.assert_array_equal(
        model(frame, context), baseline(frame, context)
    )
    assert not hasattr(model, "probabilities")
    equivalent = AgeSexMortalityModel(
        SINGLE_YEAR_AGE_BANDS,
        {
            (AgeSexMortalityModel.band_label(a, b), sex): 0.2
            for a, b in SINGLE_YEAR_AGE_BANDS
            for sex in ("female", "male")
        },
    )
    first_rng = np.random.default_rng(72)
    second_rng = np.random.default_rng(72)
    deaths, cells = {}, {}
    actual = apply_differential_mortality(
        frame,
        context,
        first_rng,
        model=model,
        weight_column="weight",
        death_log=deaths,
        cell_log=cells,
    )
    expected = apply_mortality(frame, context, second_rng, model=equivalent)
    pd.testing.assert_frame_equal(actual, expected)
    assert first_rng.bit_generator.state == second_rng.bit_generator.state
    assert set(actual["person_id"]) | set(deaths[2020]["person_id"]) == set(
        frame["person_id"]
    )
    assert cells[2020]["clipping_residual"].eq(0).all()


@pytest.mark.parametrize("registry", [False, True])
def test_di_adapter_identity(registry):
    frame = invented_frame(di=True)
    context = invented_context(frame, registry=registry)
    baseline = invented_baseline()
    rates = invented_rates()
    model = DifferentialMortality(
        baseline,
        invented_specification(),
        weight_column="weight",
        di_configuration=rates,
    )
    actual_log, expected_log = {}, {}
    actual_cells, expected_cells = {}, {}
    first_rng, second_rng = np.random.default_rng(5), np.random.default_rng(5)
    actual = apply_di_aware_mortality(
        frame,
        context,
        first_rng,
        population_model=model,
        rates=rates,
        weight_column="weight",
        death_log=actual_log,
        cell_log=actual_cells,
    )
    expected = apply_di_aware_mortality(
        frame,
        context,
        second_rng,
        population_model=baseline,
        rates=rates,
        weight_column="weight",
        death_log=expected_log,
        cell_log=expected_cells,
    )
    pd.testing.assert_frame_equal(actual, expected)
    pd.testing.assert_frame_equal(actual_log[2020], expected_log[2020])
    pd.testing.assert_frame_equal(actual_cells[2020], expected_cells[2020])
    assert first_rng.bit_generator.state == second_rng.bit_generator.state


def test_model_pure_and_no_randomness(monkeypatch):
    frame = invented_frame()
    original = frame.copy(deep=True)
    context = invented_context(frame, registry=True)
    rng = np.random.default_rng(5)
    state = deepcopy(rng.bit_generator.state)

    def refuse_generator(*args, **kwargs):
        raise AssertionError("pure model touched a generator")

    monkeypatch.setattr(PeriodContext, "person_generator", refuse_generator)
    monkeypatch.setattr(np.random, "default_rng", refuse_generator)
    model = DifferentialMortality(
        invented_baseline(), invented_specification(3), weight_column="weight"
    )
    first, first_log = model.evaluate(frame, context)
    second, second_log = model.evaluate(frame, context)
    np.testing.assert_array_equal(first, second)
    pd.testing.assert_frame_equal(first_log, second_log)
    pd.testing.assert_frame_equal(frame, original)
    assert rng.bit_generator.state == state


def test_age_check_always_precedes_cap_even_if_di_check_disabled():
    frame = invented_frame(di=True)
    context = invented_context(frame)
    model = DifferentialMortality(
        invented_baseline(),
        invented_specification(),
        weight_column=None,
        di_configuration=DIEntitlementSpec(validate_age_column=False),
    )
    frame.loc[0, "age"] += 1
    with pytest.raises(ValueError, match="context.year - 1 - birth_year"):
        model(frame, context)
    frame["age"] = 130
    frame["birth_year"] = 1889
    _, cells = model.evaluate(frame, context)
    assert cells["age"].tolist() == [120]


@pytest.mark.parametrize("post_conversion", ["di_origin", "population"])
def test_fixed_origin_matches_configured_adapter_rule(post_conversion):
    frame = invented_frame(di=True)
    context = invented_context(frame)
    model = DifferentialMortality(
        invented_baseline(),
        invented_specification(3),
        weight_column="weight",
        di_configuration=DIEntitlementSpec(
            post_conversion_mortality=post_conversion
        ),
    )
    q, cells = model.evaluate(frame, context)
    assert q[0] == 0.2
    if post_conversion == "di_origin":
        assert q[1] == 0.2
        assert cells["fixed_persons"].tolist() == [2]
    else:
        assert q[1] > 0.2
        assert cells["fixed_persons"].tolist() == [1]
    assert not cells["infeasible"].any()


def test_composition_preserves_unclipped_ratios_and_baseline_origin(
    monkeypatch,
):
    frame = invented_frame(di=True)
    context = invented_context(frame)
    rates = invented_rates()
    model = DifferentialMortality(
        invented_baseline(),
        invented_specification(3),
        weight_column="weight",
        di_configuration=rates,
    )
    captured = {}
    original = di_entitlement._net_of_di_origin

    def capture(q, population, fixed, sex, age, weight, bands):
        out, cells = original(q, population, fixed, sex, age, weight, bands)
        captured.update(population=population, fixed=fixed, out=out)
        return out, cells

    monkeypatch.setattr(di_entitlement, "_net_of_di_origin", capture)
    cells = {}
    apply_di_aware_mortality(
        frame,
        context,
        np.random.default_rng(6),
        population_model=model,
        rates=rates,
        weight_column="weight",
        cell_log=cells,
    )
    ordered = frame.sort_values("person_id")
    q_base = model.baseline(ordered, context)
    fixed = captured["fixed"]
    np.testing.assert_array_equal(captured["population"][fixed], q_base[fixed])
    other = ~fixed
    factor = captured["out"][other] / captured["population"][other]
    np.testing.assert_allclose(factor, factor[0], rtol=1e-13, atol=1e-13)
    log = cells[2020]
    np.testing.assert_allclose(
        log["expected_deaths_applied"],
        log["expected_deaths_population_model"],
        rtol=1e-12,
        atol=1e-12,
    )


def test_adapter_clipping_residual_is_derived_from_its_logged_totals(
    monkeypatch,
):
    """Intended: the unchanged adapter clips once after SES normalization."""
    frame = invented_frame(di=True)
    context = invented_context(frame)
    rates = invented_rates(death=0.1, q=0.6)
    model = DifferentialMortality(
        invented_baseline(q=0.6),
        invented_specification(3),
        weight_column="weight",
        di_configuration=rates,
    )
    captured = {}
    original = di_entitlement._net_of_di_origin

    def capture(q, population, fixed, sex, age, weight, bands):
        out, cells = original(q, population, fixed, sex, age, weight, bands)
        captured.update(out=out, population=population, weight=weight)
        return out, cells

    monkeypatch.setattr(di_entitlement, "_net_of_di_origin", capture)
    cells = {}
    apply_di_aware_mortality(
        frame,
        context,
        np.random.default_rng(6),
        population_model=model,
        rates=rates,
        weight_column="weight",
        cell_log=cells,
    )
    logged = cells[2020]
    residual = (
        logged["expected_deaths_population_model"]
        - logged["expected_deaths_applied"]
    )
    assert not logged["infeasible"].any()
    assert residual.gt(0).all()
    assert (captured["out"] == 1).any()
    np.testing.assert_allclose(
        np.dot(captured["weight"], captured["out"]),
        np.dot(captured["weight"], captured["population"]) - residual.sum(),
        rtol=1e-12,
        atol=1e-12,
    )


def test_unclassified_cell_counts_on_reference_and_refusal():
    frame = invented_frame()
    frame.loc[[0, 1], "education"] = "invented_unclassified"
    model = DifferentialMortality(
        invented_baseline(), invented_specification(), weight_column="weight"
    )
    with pytest.raises(UnclassifiedValueError) as raised:
        model(frame, invented_context(frame))
    assert raised.value.cell_log["unclassified_refuse"].sum() == 2
    reference = replace(
        model,
        specification=replace(
            model.specification, unclassified_rule="reference"
        ),
    )
    _, cells = reference.evaluate(frame, invented_context(frame))
    assert cells["unclassified_reference"].sum() == 2


@pytest.mark.parametrize("age", [-1, 1.5, np.nan, np.inf])
def test_invalid_age_refused(age):
    frame = invented_frame().drop(columns="birth_year")
    frame["age"] = frame["age"].astype(float)
    frame.loc[0, "age"] = age
    model = DifferentialMortality(
        invented_baseline(), invented_specification(), weight_column=None
    )
    with pytest.raises(ValueError):
        model(frame, invented_context(frame))


def test_missing_columns_and_ambiguous_di_refused():
    frame = invented_frame()
    model = DifferentialMortality(
        invented_baseline(), invented_specification(), weight_column="weight"
    )
    for column in ("age", "sex", "weight", "education"):
        with pytest.raises(ValueError, match="missing"):
            model(frame.drop(columns=column), invented_context(frame))
    with pytest.raises(ValueError, match="DI columns require"):
        model(invented_frame(di=True), invented_context(frame))
    configured = replace(model, di_configuration=DIEntitlementSpec())
    with pytest.raises(ValueError, match="missing columns"):
        configured(frame, invented_context(frame))


@pytest.mark.parametrize(
    "column,value",
    [
        ("di_entitled", None),
        ("di_entitled", "yes"),
        ("di_conversion_year", 2018.5),
    ],
)
def test_invalid_di_state_refused(column, value):
    frame = invented_frame(di=True)
    frame[column] = frame[column].astype(object)
    frame.loc[0, column] = value
    model = DifferentialMortality(
        invented_baseline(),
        invented_specification(),
        weight_column=None,
        di_configuration=DIEntitlementSpec(),
    )
    with pytest.raises(ValueError):
        model(frame, invented_context(frame))


def test_model_probability_attribute_and_wrong_interfaces_refused():
    class InventedYearlessBaseline:
        bands = SINGLE_YEAR_AGE_BANDS
        probabilities = None

        def __call__(self, frame, context):
            return np.zeros(len(frame))

    with pytest.raises(ValueError, match="probabilities attribute"):
        DifferentialMortality(
            InventedYearlessBaseline(),
            invented_specification(),
            weight_column=None,
        )

    class InventedBadSubclass(DifferentialMortality):
        probabilities = None

    with pytest.raises(ValueError, match="probabilities attribute"):
        InventedBadSubclass(
            invented_baseline(), invented_specification(), weight_column=None
        )
    with pytest.raises(TypeError):
        DifferentialMortality(invented_baseline(), invented_specification())

    class InventedWrongBands:
        bands = ((0, 120),)

        def __call__(self, frame, context):
            return np.zeros(len(frame))

    with pytest.raises(ValueError, match="SINGLE_YEAR"):
        DifferentialMortality(
            InventedWrongBands(),
            invented_specification(),
            weight_column=None,
        )


def test_step_weight_must_match_model():
    frame = invented_frame()
    model = DifferentialMortality(
        invented_baseline(), invented_specification(), weight_column="weight"
    )
    with pytest.raises(ValueError, match="weight_column must match"):
        apply_differential_mortality(
            frame,
            invented_context(frame),
            np.random.default_rng(1),
            model=model,
            weight_column=None,
        )
