"""Additional G3 invariants and adversarial inputs on INVENTED rows.

These unit tests open no microdata or outcome artifacts.  All rows and
amounts below are INVENTED; reference statistics are recomputed from those
same rows.  The tests cover per-dimension quintile populations, static
full-sample splits, disclosure propagation and explicit design refusals.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.estimates import cola_age_profile as a7
from populace_dynamics.estimates import group_breakdown as gb
from populace_dynamics.estimates import uniform_cut_tabulation as ut


def _scheme(base=gb.MINT8_SCHEME, keep=("total", "sex")):
    """An INVENTED test composition of captured category dimensions."""
    return gb.derive_scheme(
        base,
        scheme_id="invented_adversarial_test",
        title="INVENTED test composition",
        drop=[d.key for d in base.dimensions if d.key not in keep],
    )


def _rows(n=12, weights=None):
    """INVENTED static rows, with both sexes in each family unit."""
    rows = pd.DataFrame(
        {
            "person_id": np.arange(n),
            "family_unit_id": np.arange(n) // 2,
            "weight": np.ones(n) if weights is None else weights,
            "sex": ["female" if i % 2 == 0 else "male" for i in range(n)],
            "stratum": np.ones(n, dtype=int),
            "cluster": 1 + np.arange(n) % 2,
            "indicator": [i % 3 == 0 for i in range(n)],
            "poor_baseline": [i % 4 == 0 for i in range(n)],
            "poor_reform": [i % 3 == 0 for i in range(n)],
            "benefit_base": np.full(n, 100.0),
            "benefit_reform": [
                90.0 if i % 3 == 0 else 100.0 for i in range(n)
            ],
        }
    )
    rows.attrs["provenance_kind"] = gb.INVENTED
    return rows


def _assignment(rows):
    return gb.assign_groups(
        rows, _scheme(), {"sex": "sex"}, key_columns=("person_id",)
    )


def _static(rows, kind, **kwargs):
    options = {
        "design": pd.DataFrame({"stratum": [1, 1], "cluster": [1, 2]}),
        "data_provenance": gb.INVENTED,
        "floor_split_unit": gb.FAMILY_UNIT,
        **kwargs,
    }
    assignment = _assignment(rows)
    if kind == "share":
        return gb.tabulate_share_breakdown(
            rows, assignment, indicator_column="indicator", **options
        )
    if kind == "poverty":
        return gb.tabulate_poverty_breakdown(rows, assignment, **options)
    return gb.tabulate_static_benefit_breakdown(rows, assignment, **options)


@pytest.mark.parametrize("kind", ["share", "poverty", "benefit"])
@pytest.mark.parametrize("column", ["stratum", "cluster"])
def test_static_design_identifiers_refuse_fractional_values(kind, column):
    rows = _rows()
    rows[column] = rows[column].astype(float)
    rows.loc[0, column] = 1.5
    with pytest.raises(gb.GroupBreakdownError, match="integer|integral"):
        _static(rows, kind)


@pytest.mark.parametrize("column", ["stratum", "cluster"])
def test_full_design_frame_refuses_fractional_identifiers(column):
    design = pd.DataFrame({"stratum": [1.0, 1.0], "cluster": [1.0, 2.0]})
    design.loc[0, column] += 0.5
    with pytest.raises(gb.GroupBreakdownError, match="integer|integral"):
        _static(_rows(), "share", design=design)


@pytest.mark.parametrize("kind", ["share", "poverty", "benefit"])
def test_static_floor_requires_two_usable_seeds(kind):
    result = _static(_rows(), kind, floor_seeds=(0,))
    statistic = {
        "share": gb.SHARE,
        "poverty": gb.POVERTY_RATE_CHANGE,
        "benefit": gb.PERCENT_DECREASE,
    }[kind]
    floor = (
        result.cell("total", "total").statistic(statistic).uncertainty["floor"]
    )
    assert floor["n_seeds"] == 1
    assert not floor["defined"]
    assert floor["mean"] is None
    assert floor["sd"] is None


@settings(max_examples=25, deadline=None)
@given(
    st.lists(st.integers(1, 100), min_size=8, max_size=24).filter(
        lambda values: len(values) % 2 == 0
    )
)
def test_static_group_floor_restricts_the_full_family_split(weights):
    rows = _rows(len(weights), np.asarray(weights, dtype=float))
    result = _static(rows, "share")
    full = gb.half_split_masks(rows.family_unit_id.tolist(), (0, 1, 2, 3, 4))
    group = (rows.sex == "female").to_numpy()
    w = rows.weight.to_numpy()
    receiving = rows.indicator.to_numpy()

    def share(mask):
        denominator = math.fsum(w[mask].tolist())
        if denominator == 0:
            return None
        return 100.0 * math.fsum(w[mask & receiving].tolist()) / denominator

    gaps, dropped = [], []
    for seed, side in full.items():
        first, second = share(group & side), share(group & ~side)
        if first is None or second is None:
            dropped.append(seed)
        else:
            gaps.append(abs(first - second))
    floor = (
        result.cell("sex", "female").statistic(gb.SHARE).uncertainty["floor"]
    )
    assert floor == {**ut._floor_summary(gaps), "dropped_seeds": dropped}


def test_poverty_count_floors_use_the_same_raw_half_scale():
    rows = _rows(weights=np.arange(1.0, 13.0) * 1000)
    result = _static(rows, "poverty")
    split = gb.half_split_masks(rows.family_unit_id.tolist(), (0, 1, 2, 3, 4))
    w = rows.weight.to_numpy()
    poor = rows.poor_baseline.to_numpy()
    gaps = [
        abs(
            math.fsum(w[side & poor].tolist())
            - math.fsum(w[~side & poor].tolist())
        )
        / 1000.0
        for side in split.values()
    ]
    floor = (
        result.cell("total", "total")
        .statistic(gb.NUMBER_POOR_CURRENT_LAW)
        .uncertainty["floor"]
    )
    assert floor == {**ut._floor_summary(gaps), "dropped_seeds": []}
    assert result.conventions["uncertainty"]["scale"] == (
        "half sample; not rescaled"
    )


def test_numerator_disclosure_flag_suppresses_the_whole_subgroup():
    # INVENTED: 110 cases in each sex category, three decreases in Female.
    rows = _rows(220)
    rows["benefit_reform"] = 100.0
    rows.loc[[0, 2, 4], "benefit_reform"] = 50.0
    result = _static(rows, "benefit")
    sex = result.dimension("sex")
    decrease = sex.cell("female").statistic(gb.PERCENT_DECREASE)
    assert decrease.unweighted_n == 110
    assert not decrease.flags["ssa_disclosure_below_100"]
    assert decrease.flags["ssa_numerator_1_to_9"]
    assert sex.ssa_subgroup_suppressed
    assert sex.suppressed_by == ("Female",)
    assert len(sex.cells) == 2


def test_projection_ratio_flags_the_smaller_scenario_membership():
    # INVENTED: 120 current-law recipients, 20 proposal recipients.
    rows = pd.DataFrame(
        [
            {
                "draw": 0,
                "person_id": person,
                "family_unit_id": person // 2,
                "weight": 1.0,
                "birth_year": 1960,
                "beneficiary_base": True,
                "beneficiary_reform": person < 20,
                "benefit_base": 100.0,
                "benefit_reform": 110.0 if person < 20 else 0.0,
                "benefit_components": {
                    "retired_worker": {
                        "base": 100.0,
                        "reform": 110.0 if person < 20 else 0.0,
                    }
                },
            }
            for person in range(120)
        ]
    )
    rows.attrs["provenance_kind"] = gb.INVENTED
    assignment = gb.assign_groups(
        rows,
        _scheme(keep=("total",)),
        {},
        key_columns=("draw", "person_id"),
    )
    result = gb.tabulate_projection_breakdown(
        rows,
        assignment,
        data_provenance=gb.INVENTED,
        config=a7.ColaAgeProfileConfig(
            draw_indices=(0,),
            floor_seeds=(0, 1),
            allow_membership_difference=True,
        ),
    )
    cell = result.cell("total", "total")
    ratio = cell.statistic(gb.RATIO_OF_SCENARIO_MEANS)
    assert ratio.value == pytest.approx(10.0)
    assert cell.counts["unweighted_n_base_per_draw"] == [120]
    assert cell.counts["unweighted_n_reform_per_draw"] == [20]
    assert ratio.unweighted_n == 20
    assert ratio.flags["ssa_disclosure_below_100"]
    assert ratio.flags["below_30"]
    assert cell.flags["ssa_disclosure_below_100"]
    assert cell.flags["below_30"]
    assert result.dimension("total").ssa_subgroup_suppressed


def _quintile_rows(lower=0, upper=100):
    """INVENTED two draws, two birth cohorts, five distinct values each."""
    rows = pd.DataFrame(
        [
            {
                "draw": draw,
                "person_id": 10 * cohort + rank,
                "birth_cohort": cohort,
                "weight": 1.0,
                "household_income": offset + rank,
                "initial_aime": offset + rank,
                "expected_rank": rank,
            }
            for draw in (0, 1)
            for cohort, offset in enumerate((lower, upper))
            for rank in range(1, 6)
        ]
    )
    rows.attrs["provenance_kind"] = gb.INVENTED
    return rows


def _quintile_scheme():
    return _scheme(
        gb.MINT8_ANNUAL_WITH_LIFETIME_SCHEME,
        ("total", "household_income_quintile", "initial_aime_quintile"),
    )


def _assign_quintiles(rows, overrides):
    return gb.assign_groups(
        rows,
        _quintile_scheme(),
        {
            "household_income_quintile": "household_income",
            "initial_aime_quintile": "initial_aime",
        },
        key_columns=("draw", "person_id"),
        quintile_partition=("draw",),
        quintile_partitions=overrides,
    )


@settings(max_examples=20, deadline=None)
@given(st.integers(0, 100), st.integers(201, 1000))
def test_each_quintile_dimension_uses_its_own_population(lower, upper):
    rows = _quintile_rows(lower, upper)
    assignment = _assign_quintiles(
        rows, {"initial_aime_quintile": ("draw", "birth_cohort")}
    )
    for dimension in ("household_income_quintile", "initial_aime_quintile"):
        rank_by_category = {
            category.key: category.rank
            for category in assignment.scheme.dimension(dimension).categories
        }
        assigned = assignment.long[
            assignment.long.dimension == dimension
        ].sort_values("row_id")
        ranks = assigned.category.map(rank_by_category).to_numpy()
        if dimension == "initial_aime_quintile":
            np.testing.assert_array_equal(ranks, rows.expected_rank)
        else:
            for draw in (0, 1):
                mask = rows.draw == draw
                expected, _ = gb.weighted_quintile_ranks(
                    rows.household_income[mask], rows.weight[mask]
                )
                np.testing.assert_array_equal(ranks[mask], expected)
    assert assignment.as_dict()["quintile_partitions"] == {
        "household_income_quintile": ["draw"],
        "initial_aime_quintile": ["draw", "birth_cohort"],
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"total": ("draw",)},
        {"unknown_dimension": ("draw",)},
        {"initial_aime_quintile": ("missing_column",)},
        {"initial_aime_quintile": "draw"},
    ],
)
def test_invalid_quintile_partition_overrides_are_refused(overrides):
    with pytest.raises(gb.GroupBreakdownError):
        _assign_quintiles(_quintile_rows(), overrides)


def test_missing_per_dimension_partition_values_are_refused():
    rows = _quintile_rows()
    rows.loc[0, "birth_cohort"] = np.nan
    with pytest.raises(gb.GroupBreakdownError, match="missing"):
        _assign_quintiles(
            rows, {"initial_aime_quintile": ("draw", "birth_cohort")}
        )
