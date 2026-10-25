"""INVENTED categories and coefficients; no empirical gradient claims."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.mortality_ses.specification import (
    DIMENSIONS,
    HoldLastCoefficientPath,
    RelativeRiskSpec,
    RiskDimension,
    UnclassifiedValueError,
)


def invented_dimensions():
    return tuple(
        RiskDimension(
            name,
            name,
            ("invented_reference", "invented_higher_risk"),
            "invented_reference",
            ("invented_unclassified",),
        )
        for name in DIMENSIONS
    )


def invented_table(years=(2020, 2022), risks=(2.0, 3.0)):
    return pd.DataFrame(
        [
            {
                "year": year,
                "dimension": dimension.name,
                "category": category,
                "sex": sex,
                "age_lower": 0,
                "age_upper": 120,
                "log_relative_risk": (
                    0.0 if category == dimension.reference else np.log(risk)
                ),
            }
            for year, risk in zip(years, risks, strict=True)
            for dimension in invented_dimensions()
            for category in dimension.categories
            for sex in ("female", "male")
        ]
    )


def invented_frame():
    return pd.DataFrame(
        {
            "sex": ["female", "male"],
            **{
                name: ["invented_reference", "invented_higher_risk"]
                for name in DIMENSIONS
            },
        }
    )


def test_invented_bands_log_addition_and_hold_last():
    spec = RelativeRiskSpec(
        invented_dimensions(), HoldLastCoefficientPath(invented_table())
    )
    frame = invented_frame()
    risk, counts = spec.relative_risks(frame, 2020, np.array([0, 120]))
    np.testing.assert_allclose(risk, [1, 8])
    assert not counts["unclassified_reference"].any()
    np.testing.assert_array_equal(
        spec.relative_risks(frame, 2022, np.array([0, 120]))[0],
        spec.relative_risks(frame, 2100, np.array([0, 120]))[0],
    )
    with pytest.raises(ValueError, match="precedes"):
        spec.relative_risks(frame, 2019, np.array([0, 120]))


def test_pluggable_path_changes_only_named_year():
    primary = HoldLastCoefficientPath(invented_table())

    class InventedAlternative:
        years = primary.years

        def coefficients(self, year):
            table = primary.coefficients(year)
            if year == 2025:
                table["log_relative_risk"] *= 2
            return table

    first = RelativeRiskSpec(invented_dimensions(), primary)
    other = replace(first, path=InventedAlternative())
    for year in (2020, 2022, 2024, 2026, 2100):
        np.testing.assert_array_equal(
            first.relative_risks(invented_frame(), year, [20, 20])[0],
            other.relative_risks(invented_frame(), year, [20, 20])[0],
        )
    assert other.relative_risks(invented_frame(), 2025, [20, 20])[0][1] > (
        first.relative_risks(invented_frame(), 2025, [20, 20])[0][1]
    )


@given(st.sampled_from([None, "invented_unclassified"]))
@settings(deadline=None)
def test_unclassified_rules_are_counted(value):
    frame = invented_frame()
    frame.loc[0, DIMENSIONS[0]] = value
    spec = RelativeRiskSpec(
        invented_dimensions(), HoldLastCoefficientPath(invented_table())
    )
    with pytest.raises(UnclassifiedValueError) as raised:
        spec.relative_risks(frame, 2020, [20, 20])
    assert raised.value.unclassified_counts["unclassified_refuse"].sum() == 1
    risk, counts = replace(spec, unclassified_rule="reference").relative_risks(
        frame, 2020, [20, 20]
    )
    assert risk[0] == 1
    assert counts["unclassified_reference"].sum() == 1


@pytest.mark.parametrize("rule", ["refuse", "reference"])
def test_unknown_category_always_refused(rule):
    spec = RelativeRiskSpec(
        invented_dimensions(),
        HoldLastCoefficientPath(invented_table()),
        rule,
    )
    frame = invented_frame()
    frame.loc[0, DIMENSIONS[0]] = "invented_unknown"
    with pytest.raises(ValueError, match="unknown category"):
        spec.relative_risks(frame, 2020, [20, 20])


@pytest.mark.parametrize("log_risk", [np.nan, np.inf, -np.inf, 1000, -1000])
def test_nonfinite_nonpositive_or_overflowed_risk_refused(log_risk):
    table = invented_table()
    table.loc[1, "log_relative_risk"] = log_risk
    with pytest.raises(ValueError, match="finite and positive"):
        RelativeRiskSpec(invented_dimensions(), HoldLastCoefficientPath(table))


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "duplicate", "reference"]
)
def test_table_coverage_and_reference_refused(mutation):
    table = invented_table()
    if mutation == "missing":
        table = table.iloc[1:]
    elif mutation == "extra":
        table.loc[0, "category"] = "invented_unknown"
    elif mutation == "duplicate":
        table = pd.concat([table, table.iloc[[0]]])
    else:
        table.loc[0, "log_relative_risk"] = 0.5
    with pytest.raises(ValueError):
        RelativeRiskSpec(invented_dimensions(), HoldLastCoefficientPath(table))


def test_missing_columns_and_malformed_specification_refused():
    path = HoldLastCoefficientPath(invented_table())
    spec = RelativeRiskSpec(invented_dimensions(), path)
    with pytest.raises(ValueError, match="missing"):
        spec.relative_risks(
            invented_frame().drop(columns="education"), 2020, [20, 20]
        )
    with pytest.raises(ValueError, match="three dimensions"):
        RelativeRiskSpec(invented_dimensions()[:2], path)
    with pytest.raises(ValueError, match="unclassified rule"):
        replace(spec, unclassified_rule="silent")
    with pytest.raises(ValueError, match="unique"):
        replace(
            invented_dimensions()[0], categories=("duplicate", "duplicate")
        )


def test_empty_custom_path_and_out_of_range_year_refused():
    class InventedEmptyPath:
        years = (2020,)

        def coefficients(self, year):
            return invented_table().drop(columns="year").iloc[:0]

    with pytest.raises(ValueError, match="coverage"):
        RelativeRiskSpec(invented_dimensions(), InventedEmptyPath())
    table = invented_table()
    table["year"] = 1e30
    with pytest.raises(ValueError, match="finite integers"):
        HoldLastCoefficientPath(table)


@given(
    st.floats(min_value=-100, max_value=100, allow_nan=False),
    st.integers(min_value=0, max_value=120),
)
@settings(max_examples=30, deadline=None)
def test_single_age_and_bands_are_equivalent(log_risk, age):
    table = invented_table(years=(2020,), risks=(1,))
    table.loc[
        table["category"] != "invented_reference", "log_relative_risk"
    ] = log_risk
    expanded = pd.DataFrame(
        [
            {**row, "age": a}
            for row in table.drop(columns=["age_lower", "age_upper"]).to_dict(
                "records"
            )
            for a in range(121)
        ]
    )
    band_spec = RelativeRiskSpec(
        invented_dimensions(), HoldLastCoefficientPath(table)
    )
    age_spec = RelativeRiskSpec(
        invented_dimensions(), HoldLastCoefficientPath(expanded)
    )
    np.testing.assert_array_equal(
        band_spec.relative_risks(invented_frame(), 2020, [age, age])[0],
        age_spec.relative_risks(invented_frame(), 2020, [age, age])[0],
    )
