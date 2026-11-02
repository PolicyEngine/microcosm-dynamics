"""Invented-data tests of Registration 18 estimands and the A7 floor."""

import json
import math
import statistics
from copy import deepcopy
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from populace_dynamics import scenario_benefits as sb
from populace_dynamics.acola_track import statistics as ac
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    reference_benefit_rows,
)
from populace_dynamics.cola_track_a.config import (
    INVENTED_COHORT_LABEL,
    RegisteredRow,
    TrackAConfig,
)
from populace_dynamics.cola_track_a.opening import (
    OpeningStockRecord,
    TrackACohort,
)
from populace_dynamics.engine.loop import ProjectionResult
from populace_dynamics.estimates import cola_age_profile as a7
from populace_dynamics.ss import benefits as ss_benefits
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.track_a_v2 import estimands as v2
from populace_dynamics.track_a_v2.matrix import UNION_STATISTIC


def record(
    person_id=1,
    *,
    draw=0,
    age=65,
    weight=1.0,
    base=100.0,
    reform=90.0,
    component="retired_worker",
    family=None,
    spouse_class="unclassified",
):
    return {
        "draw": draw,
        "person_id": person_id,
        "family_unit_id": person_id if family is None else family,
        "weight": float(weight),
        "birth_year": 2030 - age,
        "beneficiary_base": base > 0,
        "beneficiary_reform": reform > 0,
        "benefit_base": float(base),
        "benefit_reform": float(reform),
        "benefit_components": {
            component: {"base": float(base), "reform": float(reform)}
        },
        "spouse_worker_class": spouse_class,
    }


def panel():
    return [
        record(
            i + 1,
            draw=draw,
            age=age,
            weight=i + 1,
            base=100 * (i + 1),
            reform=100 * (i + 1) * (0.9 - i * 0.1),
            component=component,
            spouse_class="entitled_unconverted_di_worker",
        )
        for draw in (0, 1)
        for i, (age, component) in enumerate(
            zip((65, 75, 85, 95, 60), a7.PRIMARY_COMPONENTS, strict=True)
        )
    ]


def normalized(records, draws=(0, 1)):
    config = a7.ColaAgeProfileConfig(
        age_groups=(a7.AgeGroup("all", 0, None),),
        draw_indices=draws,
        allow_membership_difference=True,
    )
    return a7._normalize(records, config), config


def invented_params() -> SSAParameters:
    """INVENTED oracle parameters: 4 percent wage growth from 1951.

    A copy of ``tests.cola_track_a.test_assembly.invented_params``, kept
    here so this module does not import that legacy test module, which
    blind roles may not run (its tests read a closed design document).
    """
    return SSAParameters(
        nawi={
            year: 2_800.0 * 1.04 ** (year - 1951) for year in range(1951, 2061)
        },
        wage_base={1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


def invented_baseline():
    """INVENTED uniform 2.8 percent COLA path; every reform rate stays >0."""
    return sb.COLASeries(
        by_determination_year={year: 0.028 for year in range(1979, 2031)},
        provenance={"invented": True},
    )


@pytest.mark.parametrize(
    "values,weights,expected",
    [
        ([0, 10], [1, 1], 5),
        ([0, 10, 20], [1, 2, 1], 10),
        ([0, 10, 20], [1, 0, 1], 10),
        ([10, 0, 20], [0, 1, 1], 10),
        ([10, 20, 30], [0, 0, 0], None),
        ([], [], None),
        ([-10, -2, 0], [1, 1, 1], -2),
    ],
)
def test_registered_exact_weighted_median(values, weights, expected):
    assert ac.weighted_median(values, weights) == expected


def test_near_half_weight_uses_exact_binary_fraction():
    above = math.nextafter(1.0, math.inf)
    below = math.nextafter(1.0, 0.0)
    assert ac.weighted_median([0, 10], [above, 1]) == 0
    assert ac.weighted_median([0, 10], [below, 1]) == 10
    # Decimal-looking floats are interpreted as their supplied binary values.
    assert Fraction(0.1) + Fraction(0.2) != Fraction(0.3)
    assert ac.weighted_median([0, 1, 2], [0.1, 0.2, 0.3]) == 1


def test_midpoint_does_not_overflow_or_lose_subnormal_values():
    assert ac.weighted_median([1e308, 1e308], [1, 1]) == 1e308
    smallest = math.ulp(0.0)
    expected = float((Fraction(smallest) + Fraction(2 * smallest)) / 2)
    assert ac.weighted_median([smallest, 2 * smallest], [1, 1]) == expected


@pytest.mark.parametrize(
    "values,weights,ids",
    [
        ([1], [-1], None),
        ([math.inf], [1], None),
        ([1], [math.nan], None),
        ([1], [], None),
        ([1], [1], []),
        ([1, 2], [1, 1], [1, "a"]),
    ],
)
def test_median_refuses_invalid_input(values, weights, ids):
    with pytest.raises(a7.ColaTabulationError):
        ac.weighted_median(values, weights, ids)


@given(st.lists(st.integers(-10000, 10000), min_size=1, max_size=31))
@settings(deadline=None)
def test_equal_positive_weights_match_ordinary_median(values):
    assert ac.weighted_median(values, [1] * len(values)) == statistics.median(
        values
    )


@given(
    st.lists(
        st.tuples(st.integers(-10000, 10000), st.integers(1, 100)),
        min_size=1,
        max_size=30,
    ),
    st.integers(1, 100),
)
@settings(deadline=None)
def test_median_bounds_permutation_and_weight_scale(atoms, scale):
    values, weights = zip(*atoms, strict=True)
    ids = list(range(len(values)))
    median = ac.weighted_median(values, weights, ids)
    assert min(values) <= median <= max(values)
    assert median == ac.weighted_median(values[::-1], weights[::-1], ids[::-1])
    assert median == ac.weighted_median(values, [w * scale for w in weights])


def test_component_accounting_and_spouse_three_classes():
    records = panel()
    cost = ac.summarize_cost(records, draw_indices=(0, 1))
    cell = cost["per_draw"][0]
    assert cell["T_base"] == 5500
    assert cell["T_reform"] == pytest.approx(3250)
    assert cell[ac.P] == pytest.approx(100 * (3250 / 5500 - 1))
    for scenario in ("base", "reform"):
        assert sum(
            totals[scenario] for totals in cell["component_totals"].values()
        ) == pytest.approx(cell[f"T_{scenario}"])
    assert sum(cell["group_shares"].values()) == pytest.approx(1)
    assert cell[ac.P] == pytest.approx(
        cell["group_shares"]["OASI"] * cell[ac.P_OASI]
        + cell["group_shares"]["DI"] * cell[ac.P_DI]
    )
    assert cell["n_base"] == cell["n_reform"] == 5
    assert cell["weight_base"] == cell["weight_reform"] == 15
    classes = cell["spouse_worker_classes"]
    assert (
        classes["entitled_unconverted_di_worker"]["weighted_count_base"] == 3
    )
    assert classes["entitled_unconverted_di_worker"]["dollars_base"] == 900
    assert classes["entitled_unconverted_di_worker"]["dollars_reform"] == 630
    assert classes["another_worker"]["n_base"] == 0
    assert classes["unclassified"]["n_base"] == 0
    assert cost["statistic_additions"] == [
        ac.P_OASI,
        ac.P_DI,
        ac.RATIO_OF_SCENARIO_MEANS,
    ]


def test_spouse_memo_counts_positive_component_by_scenario():
    rows = [
        record(
            i,
            component="spouse",
            base=50,
            reform=(0 if i == 1 else 40),
            spouse_class=label,
            weight=i,
        )
        for i, label in enumerate(ac.SPOUSE_WORKER_CLASSES, 1)
    ]
    result = ac.summarize_cost(rows, draw_indices=(0,))
    classes = result["per_draw"][0]["spouse_worker_classes"]
    assert classes[ac.SPOUSE_WORKER_CLASSES[0]]["n_reform"] == 0
    assert classes[ac.SPOUSE_WORKER_CLASSES[1]]["weighted_count_base"] == 2
    assert classes["unclassified"]["dollars_reform"] == 120


def test_three_mint_estimands_are_distinct_and_memos_have_floors():
    rows = [
        record(i + 1, base=base, reform=reform)
        for i, (base, reform) in enumerate(((100, 50), (200, 190), (300, 200)))
    ]
    total = ac.summarize_mint(rows, draw_indices=(0,))["bands"]["Total"]
    cell = total["per_draw"][0]
    assert cell[ac.RATIO_OF_SCENARIO_MEANS] == pytest.approx(
        100 * (440 / 600 - 1)
    )
    assert cell[ac.MEDIAN_INDIVIDUAL_PCT_CHANGE] == pytest.approx(-100 / 3)
    assert cell[ac.DIFFERENCE_OF_WEIGHTED_MEDIANS_PCT] == pytest.approx(-5)
    assert cell[ac.MEDIAN_BENEFIT_BASE] == 200
    assert cell[ac.MEDIAN_BENEFIT_REFORM] == 190
    assert cell[ac.BASELINE_FALLING_SHARE] == 1
    for key in ac.MINT_STATISTICS:
        summary = total["statistics"][key]
        assert "floor" in summary
        assert summary["sd"] is None
        assert summary["undefined_reasons"]["sd"] == "fewer_than_two_draws"


def test_mint_uses_scenario_specific_sets_and_intersection_for_changes():
    rows = [
        record(1, base=100, reform=90, weight=2),
        record(2, base=400, reform=0, weight=3),
        record(3, base=0, reform=500, weight=4),
    ]
    cell = ac.summarize_mint(rows, draw_indices=(0,))["bands"]["Total"][
        "per_draw"
    ][0]
    assert cell["n_base"] == cell["n_reform"] == 2
    assert cell["weight_base"] == 5
    assert cell["weight_reform"] == 6
    assert cell["n_alternative"] == 1
    assert cell[ac.MEDIAN_INDIVIDUAL_PCT_CHANGE] == pytest.approx(-10)
    assert cell[ac.RATIO_OF_SCENARIO_MEANS] == pytest.approx(
        100 * ((2180 / 6) / (1400 / 5) - 1)
    )
    assert cell[ac.BASELINE_FALLING_SHARE] == 1
    cost = ac.summarize_cost(rows, draw_indices=(0,))["per_draw"][0]
    assert cost[ac.P] != pytest.approx(cost[ac.RATIO_OF_SCENARIO_MEANS])


def test_band_boundaries_and_m4_age_offset():
    ages = (61, 62, 69, 70, 79, 80, 89, 90)
    rows = [record(i, age=age) for i, age in enumerate(ages)]
    mint = ac.summarize_mint(rows, draw_indices=(0,))["bands"]
    assert [
        mint[label]["per_draw"][0]["n_base"] for label, _, _ in ac.MINT_BANDS
    ] == [7, 2, 2, 2, 1]
    m4 = ac.summarize_mint(
        rows,
        draw_indices=(0,),
        age_rule="reference_year_minus_birth_year_minus_one",
    )["bands"]
    assert [
        m4[label]["per_draw"][0]["n_base"] for label, _, _ in ac.MINT_BANDS
    ] == [6, 2, 2, 2, 0]


def test_zero_weights_are_excluded_and_counted_for_each_median():
    rows = [record(1, weight=0, base=100, reform=50), record(2, weight=2)]
    cell = ac.summarize_mint(rows, draw_indices=(0,))["bands"]["Total"][
        "per_draw"
    ][0]
    assert cell["median_zero_weight_exclusions"] == {
        "base": 1,
        "reform": 1,
        "alt": 1,
    }
    assert cell[ac.MEDIAN_INDIVIDUAL_PCT_CHANGE] == pytest.approx(-10)
    assert cell["n_base"] == 2
    assert cell["weight_base"] == 2


def test_draw_sample_sd_and_weight_variation_are_reported():
    rows = [
        record(1, draw=0, reform=90),
        record(1, draw=1, reform=80, weight=2),
    ]
    result = ac.summarize_cost(rows, draw_indices=(0, 1))
    summary = result["statistics"][ac.P]
    assert summary["mean"] == pytest.approx(-15)
    assert summary["sample_sd"] == pytest.approx(math.sqrt(50))
    assert summary["sd"] == summary["sample_sd"]
    assert result["input_summary"]["n_persons_weight_varies_across_draws"] == 1


def test_zero_reform_has_exact_zero_changes_share_and_floors():
    rows = panel()
    for row in rows:
        row["benefit_reform"] = row["benefit_base"]
        for component in row["benefit_components"].values():
            component["reform"] = component["base"]
    cost = ac.summarize_cost(rows, draw_indices=(0, 1))
    assert all(cell[ac.P] == 0 for cell in cost["per_draw"])
    mint = ac.summarize_mint(rows, draw_indices=(0, 1))
    change_statistics = ac.MINT_STATISTICS[:4]
    for band in mint["bands"].values():
        for cell in band["per_draw"]:
            assert all(cell[key] == 0 for key in change_statistics)
        for key in change_statistics:
            summary = band["statistics"][key]
            assert summary["mean"] == summary["sample_sd"] == 0
            if summary["floor"]["defined"]:
                assert summary["floor"]["mean"] == 0
    # Median benefit levels are memo levels, and remain positive at zero cut.
    assert (
        mint["bands"]["Total"]["statistics"][ac.MEDIAN_BENEFIT_BASE]["mean"]
        > 0
    )


def test_empty_band_and_undefined_floor_serialize_with_reasons():
    result = ac.summarize_mint([record()], draw_indices=(0,))
    band = result["bands"]["90+"]
    for key in ac.MINT_STATISTICS:
        assert band["per_draw"][0][key] is None
        assert band["per_draw"][0]["undefined_reasons"][key]
        assert band["statistics"][key]["floor"]["defined"] is False
        assert band["statistics"][key]["floor"]["mean"] is None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("summarizer", [ac.summarize_cost, ac.summarize_mint])
def test_entirely_empty_table_publishes_every_draw_as_undefined(summarizer):
    result = summarizer([], draw_indices=(0, 1))
    bands = result.get("bands", {"all": result})
    for band in bands.values():
        assert [c["draw"] for c in band["per_draw"]] == [0, 1]
        for summary in band["statistics"].values():
            assert summary["mean"] is None
            assert summary["undefined_draws"]
            assert summary["floor"]["undefined_reason"] == "no usable seed"
    json.dumps(result, allow_nan=False)


def test_missing_draw_in_nonempty_input_is_refused():
    with pytest.raises(a7.ColaTabulationError, match="draws present"):
        ac.summarize_cost([record()], draw_indices=(0, 1))


@pytest.mark.parametrize("summarizer", [ac.summarize_cost, ac.summarize_mint])
def test_certified_empty_recipient_draw_preserves_valid_draw(summarizer):
    result = summarizer(
        [record()], draw_indices=(0, 1), certified_draw_indices=(0, 1)
    )
    band = result.get("bands", {"Total": result})["Total"]
    key = (
        ac.P if summarizer is ac.summarize_cost else ac.RATIO_OF_SCENARIO_MEANS
    )
    assert band["per_draw"][0][key] == pytest.approx(-10)
    assert band["per_draw"][1][key] is None
    assert band["per_draw"][1]["n_base"] == 0
    assert band["statistics"][key]["n_defined_draws"] == 1
    assert band["statistics"][key]["mean"] is None
    assert result["certified_projection_draws"] == [0, 1]


@pytest.mark.parametrize("summarizer", [ac.summarize_cost, ac.summarize_mint])
def test_refused_draw_preserves_valid_data_and_marks_every_memo(summarizer):
    result = summarizer(
        [record()],
        draw_indices=(0, 1),
        certified_draw_indices=(0, 1),
        refused_draws={1: "REFUSE: negative reformed increase"},
    )
    band = result.get("bands", {"Total": result})["Total"]
    key = (
        ac.P if summarizer is ac.summarize_cost else ac.RATIO_OF_SCENARIO_MEANS
    )
    assert band["per_draw"][0][key] == pytest.approx(-10)
    refused = band["per_draw"][1]
    assert refused["status"] == "refused"
    assert refused["n_base"] is None
    assert refused["weight_base"] is None
    assert refused["undefined_reasons"][key] == refused["refusal_reason"]
    assert refused["not_registered"]["mean_benefit_base"] is None
    assert (
        refused["not_registered"]["undefined_reasons"]["mean_benefit_base"]
        == refused["refusal_reason"]
    )
    if summarizer is ac.summarize_cost:
        assert refused["T_base"] is None
        assert refused["component_totals"]["spouse"]["base"] is None
        assert refused["undefined_reasons"]["component_totals.spouse.base"]
        assert (
            refused["spouse_worker_classes"]["unclassified"]["n_base"] is None
        )
    else:
        assert refused["median_zero_weight_exclusions"]["alt"] is None
        assert refused["undefined_reasons"][
            "median_zero_weight_exclusions.alt"
        ]
    summary = band["statistics"][key]
    assert summary["n_defined_draws"] == 1
    assert summary["per_draw"][0] == pytest.approx(-10)
    assert summary["per_draw"][1] is None
    assert summary["floor"]["n_seeds"] == 0
    for seed in band["floor_per_seed"]:
        assert seed["absolute_gaps"][key] is None
        assert seed["undefined_reasons"][key]
        undefined = {
            item["draw"]: item["reason"]
            for item in seed["side_a"][key]["undefined_draws"]
        }
        assert undefined[1] == refused["refusal_reason"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "certified,records,refused",
    [
        ((0,), [record()], None),
        ((0, 1, 1), [record()], None),
        ((0, 1), [record(draw=2)], None),
        ((0, 1), [record()], {2: "error"}),
        ((0, 1), [record()], {1: ""}),
    ],
)
def test_certification_and_refusal_inventory_are_checked(
    certified, records, refused
):
    with pytest.raises(a7.ColaTabulationError):
        ac.summarize_cost(
            records,
            draw_indices=(0, 1),
            certified_draw_indices=certified,
            refused_draws=refused,
        )


def test_undefined_group_is_null_with_reason_and_zero_share():
    cell = ac.summarize_cost([record()], draw_indices=(0,))["per_draw"][0]
    assert cell[ac.P_DI] is None
    assert cell["undefined_reasons"][ac.P_DI] == "nonpositive_baseline_total"
    assert cell["group_shares"]["DI"] == 0


def test_unregistered_mean_of_individual_ratios_never_appears():
    for result in (
        ac.summarize_cost(panel(), draw_indices=(0, 1)),
        ac.summarize_mint(panel(), draw_indices=(0, 1)),
    ):
        assert a7.MEAN_OF_INDIVIDUAL_RATIOS not in json.dumps(result)
        bands = result.get("bands", {"all": result})
        for band in bands.values():
            for cell in band["per_draw"]:
                assert "mean_benefit_base" not in cell
                assert "mean_benefit_base" in cell["not_registered"]
                if cell["not_registered"]["mean_benefit_base"] is None:
                    assert cell["not_registered"]["undefined_reasons"][
                        "mean_benefit_base"
                    ]


def test_cost_and_mint_order_independent_including_every_floor():
    rows = panel()
    for summarizer in (ac.summarize_cost, ac.summarize_mint):
        assert summarizer(rows, draw_indices=(0, 1)) == summarizer(
            rows[::-1], draw_indices=(0, 1)
        )


def test_ratio_means_and_union_differential_against_existing_functions():
    records = panel()
    rows, config = normalized(records)
    masks = a7._membership_masks(rows, config.membership_basis)
    cost = ac.summarize_cost(records, draw_indices=(0, 1))
    for cell in cost["per_draw"]:
        selected = rows.draw == cell["draw"]
        expected = v2._cell(rows, selected, masks, cell["draw"])
        assert cell[ac.P] == expected[UNION_STATISTIC]
        assert (
            cell[ac.RATIO_OF_SCENARIO_MEANS]
            == expected[a7.RATIO_OF_SCENARIO_MEANS]
        )


def test_cost_floor_matches_v2_and_ratio_means_floor_matches_a7():
    records = panel()
    rows, config = normalized(records)
    result = ac.summarize_cost(records, draw_indices=(0, 1))
    _, floors = v2._floors(rows, config, UNION_STATISTIC)
    assert result["statistics"][ac.P]["floor"] == floors["all"]
    _, a7_floors = a7._floors(rows, config)
    assert (
        result["statistics"][ac.RATIO_OF_SCENARIO_MEANS]["floor"]
        == a7_floors["all"][a7.RATIO_OF_SCENARIO_MEANS]
    )


def test_mint_floor_splits_full_table_including_people_below_62():
    # Excluding the first family would shift all RNG draws on the remaining
    # sorted families. Every MINT statistic must use the full row table.
    records = [
        record(i, age=(50 if i == 0 else 65), reform=100 - i) for i in range(8)
    ]
    rows, config = normalized(records, (0,))
    result = ac.summarize_mint(records, draw_indices=(0,))["bands"]["Total"]
    frame = a7.pd.DataFrame({a7.FAMILY_UNIT: rows.family_unit_id.tolist()})
    masks = a7._membership_masks(rows, config.membership_basis)
    for seed in result["floor_per_seed"]:
        left, _ = a7.split_panel_by_person(
            frame, a7.FAMILY_UNIT, seed=seed["seed"]
        )
        in_a = np.zeros(rows.n, dtype=bool)
        in_a[left.index.to_numpy()] = True
        for key, selected in (("side_a", in_a), ("side_b", ~in_a)):
            selected &= rows.age >= 62
            expected = a7._cell(rows, selected, masks, 0)
            assert (
                seed[key][ac.RATIO_OF_SCENARIO_MEANS]["mean"]
                == expected[a7.RATIO_OF_SCENARIO_MEANS]
            )


def test_floor_with_only_one_usable_seed_is_undefined():
    result = ac.summarize_cost(
        [record(i, reform=90 - i) for i in range(10)],
        draw_indices=(0,),
        floor_seeds=(0,),
    )
    floor = result["statistics"][ac.P]["floor"]
    assert floor["n_seeds"] == 1
    assert floor["defined"] is False
    assert floor["undefined_reason"] == "fewer than 2 usable seeds"
    assert floor["mean"] is None


@given(
    st.lists(
        st.tuples(
            st.integers(1, 10000), st.integers(1, 10000), st.integers(1, 100)
        ),
        min_size=1,
        max_size=20,
    ),
    st.integers(0, 1000),
)
@settings(max_examples=50, deadline=None)
def test_accounting_identity_and_cut_bound_on_invented_components(atoms, cut):
    factor = 1 - cut / 1000
    records = []
    for pid, (oasi, di, weight) in enumerate(atoms):
        row = record(
            pid, weight=weight, base=oasi + di, reform=(oasi + di) * factor
        )
        row["benefit_components"] = {
            "retired_worker": {"base": oasi, "reform": oasi * factor},
            "disabled_worker": {"base": di, "reform": di * factor},
        }
        records.append(row)
    # Floors are separately differential-tested; two seeds keeps this property fast.
    result = ac.summarize_cost(records, draw_indices=(0,), floor_seeds=(0, 1))
    assert result == ac.summarize_cost(
        records[::-1], draw_indices=(0,), floor_seeds=(0, 1)
    )
    cell = result["per_draw"][0]
    assert -cut / 10 - 1e-12 <= cell[ac.P] <= 1e-12
    assert cell[ac.P] == pytest.approx(
        cell["group_shares"]["OASI"] * cell[ac.P_OASI]
        + cell["group_shares"]["DI"] * cell[ac.P_DI],
        abs=1e-11,
    )
    if factor > 0:
        assert cell[ac.P] == pytest.approx(
            cell[ac.RATIO_OF_SCENARIO_MEANS], abs=1e-11
        )
    # Both groups are positive, so T_base = T_base,OASI + T_base,DI makes
    # their shares sum to one, and the component totals reproduce T_s.
    assert sum(cell["group_shares"].values()) == pytest.approx(1, rel=1e-12)
    for scenario in ("base", "reform"):
        assert sum(
            totals[scenario] for totals in cell["component_totals"].values()
        ) == pytest.approx(cell[f"T_{scenario}"], rel=1e-12)


@given(
    st.lists(
        st.tuples(
            st.integers(1, 10000),
            st.integers(0, 1000),
            st.integers(0, 100),
            st.integers(60, 100),
        ),
        min_size=1,
        max_size=10,
    )
)
@settings(max_examples=40, deadline=None)
def test_mint_order_falling_share_and_individual_cut_bounds(atoms):
    records = [
        record(
            pid, base=base, reform=base * factor / 1000, weight=weight, age=age
        )
        for pid, (base, factor, weight, age) in enumerate(atoms)
    ]
    kwargs = {"draw_indices": (0,), "floor_seeds": (0, 1)}
    result = ac.summarize_mint(records, **kwargs)
    assert result == ac.summarize_mint(records[::-1], **kwargs)
    for band in result["bands"].values():
        cell = band["per_draw"][0]
        falling = cell[ac.BASELINE_FALLING_SHARE]
        if falling is not None:
            assert 0 <= falling <= 1
        change = cell[ac.MEDIAN_INDIVIDUAL_PCT_CHANGE]
        if change is not None:
            assert -100 <= change <= 0
    json.dumps(result, allow_nan=False)


def code_benefit_records(people, reduction, first_year):
    """Annual 2030 benefits that the scenario code computes for people.

    Each INVENTED person holds one benefit from the code's own path
    functions: an old-age or DI worker, or a spouse or widow(er) with no
    own record, so nobody is dually entitled. The fixture does no benefit
    arithmetic beyond the annual factor of 12.
    """
    params, baseline = invented_params(), invented_baseline()
    reform = sb.COLAReform(
        annual_reduction=reduction,
        first_reduced_determination_year=first_year,
    )
    records = []
    for pid, (kind, eligible, lag, pia, factor, weight) in enumerate(
        people, 1
    ):
        entitled = min(2030, eligible + lag)
        if kind in ("retired_worker", "disabled_worker"):
            clock = (
                sb.WorkerClock.at_age_62(
                    eligible - 62, entitlement_year=entitled
                )
                if kind == "retired_worker"
                else sb.WorkerClock.at_di_onset(
                    eligible, entitlement_year=entitled
                )
            )
            path = sb.worker_scenario_paths(
                eligibility_pia=pia,
                claim_age_factor=(
                    factor / 100 if kind == "retired_worker" else 1.0
                ),
                clock=clock,
                baseline=baseline,
                reform=reform,
            )
        else:
            worker = sb.WorkerClock.at_age_62(
                eligible - 62, entitlement_year=eligible
            )
            shared = {
                "entitlement_year": entitled,
                "params": params,
                "baseline": baseline,
                "reform": reform,
            }
            path = (
                sb.spouse_scenario_paths(
                    worker_eligibility_pia=pia,
                    worker_clock=worker,
                    own=None,
                    months_early=4 * lag,
                    **shared,
                )
                if kind == "spouse"
                else sb.widow_scenario_paths(
                    deceased_eligibility_pia=pia,
                    deceased_clock=worker,
                    deceased_claim_age_factor=factor / 100,
                    own=None,
                    survivor_months_early=4 * lag,
                    **shared,
                )
            )
        records.append(
            record(
                pid,
                weight=weight,
                base=12 * path.baseline_monthly_by_payment_year[2030],
                reform=12 * path.reform_monthly_by_payment_year[2030],
                component=kind,
            )
        )
    return records


INVENTED_PERSON = st.tuples(
    st.sampled_from(
        ("retired_worker", "disabled_worker", "spouse", "aged_widow")
    ),
    st.integers(1990, 2030),  # eligibility year
    st.integers(0, 9),  # years to entitlement; a quarter of months early
    st.integers(100, 4000),  # eligibility PIA
    st.integers(70, 100),  # claim-age factor, percent
    st.integers(1, 100),  # weight
)


@given(
    people=st.lists(INVENTED_PERSON, min_size=1, max_size=6),
    cuts=st.tuples(st.integers(0, 200), st.integers(0, 200)),
    firsts=st.tuples(
        st.sampled_from((2010, 2011, 2027)),
        st.sampled_from((2010, 2011, 2027)),
    ),
)
@settings(max_examples=40, deadline=None)
def test_larger_or_earlier_cut_weakly_lowers_p_and_every_benefit(
    people, cuts, firsts
):
    """Monotonicity on the code's own per-person output (review r1b, 4).

    A larger annual reduction, or an earlier first reduced determination
    year, weakly lowers every individual 2030 benefit that the scenario
    code computes, outside dual entitlement, and P with it.
    """
    smaller, larger = (cut / 10_000 for cut in sorted(cuts))
    earlier, later = sorted(firsts)
    runs = {
        "smaller": code_benefit_records(people, smaller, later),
        "larger": code_benefit_records(people, larger, later),
        "earlier": code_benefit_records(people, smaller, earlier),
    }
    for stronger in ("larger", "earlier"):
        for weak, strong in zip(runs["smaller"], runs[stronger], strict=True):
            assert strong["benefit_base"] == weak["benefit_base"] > 0
            assert (
                strong["benefit_reform"]
                <= weak["benefit_reform"]
                <= weak["benefit_base"]
            )
    p = {
        name: ac.summarize_cost(rows, draw_indices=(0,), floor_seeds=(0, 1))[
            "per_draw"
        ][0][ac.P]
        for name, rows in runs.items()
    }
    assert p["larger"] <= p["smaller"] <= 0
    assert p["earlier"] <= p["smaller"]


OWN_COMPONENTS = frozenset(("retired_worker", "disabled_worker"))
AUXILIARY_COMPONENTS = frozenset(("spouse", "aged_widow", "disabled_widow"))


def emitter_inputs(people):
    """An INVENTED cohort and 2030 projected state for the emitter.

    Built from public classes only (``TrackACohort``,
    ``OpeningStockRecord``, ``ProjectionResult``). Each spec is (kind,
    birth year, earnings level, claim age, partner's level, year offset,
    opening component). Kinds: an unmarried retired worker; an entitled
    or a converted disabled worker; a married couple of retired workers,
    whose lower earner can draw a spouse's excess; a widow(er) without or
    with an own claim, whose late spouse dies after the opening; and an
    opening-stock recipient of any component, born 15 years after the
    drawn year. Nobody here is real.
    """
    persons, careers, opening = [], {}, {}
    initial, departed, final = [], [], []

    def add(birth, level, rows=final, status="none", **state):
        pid = len(persons) + 1
        persons.append(
            {
                "person_id": pid,
                "family_unit_id": pid,
                "birth_year": birth,
                "opening_status": status,
                "ss_receipt_opening": status != "none",
            }
        )
        careers[pid] = {
            year: float(level)
            for year in range(max(1951, birth + 22), min(2011, birth + 62))
        }
        row = {
            "person_id": pid,
            "year": 2030,
            "birth_year": birth,
            "weight": float(pid),
            "di_entitled": False,
            "di_award_year": pd.NA,
            "di_conversion_year": pd.NA,
            "di_recovery_year": pd.NA,
            "claimed": False,
            "claim_year": pd.NA,
            "marital_status": "never_married",
            "spouse_person_id": pd.NA,
            "late_spouse_person_id": pd.NA,
            "widowhood_year": pd.NA,
        }
        row.update(state)
        rows.append(row)
        initial.append({**row, "year": 2010})
        return row

    def claim(birth, age):
        year = birth + age
        return {"claimed": True, "claim_year": year} if year <= 2030 else {}

    for kind, birth, level, age, other, offset, component in people:
        award = min(2030, max(1979, birth + 40 + offset))
        if kind == "worker":
            add(birth, level, **claim(birth, age))
        elif kind == "disabled_worker":
            add(birth, level, di_entitled=True, di_award_year=award)
        elif kind == "converted_worker" and birth + 66 <= 2030:
            add(
                birth,
                level,
                claimed=True,
                claim_year=birth + 66,
                di_award_year=min(award, birth + 66),
                di_conversion_year=birth + 66,
            )
        elif kind == "converted_worker":
            add(birth, level, di_entitled=True, di_award_year=award)
        elif kind == "couple":
            first = add(
                birth, level, marital_status="married", **claim(birth, age)
            )
            partner_birth = min(1965, birth + offset % 5)
            second = add(
                partner_birth,
                other,
                marital_status="married",
                spouse_person_id=first["person_id"],
                **claim(partner_birth, 62 + offset % 9),
            )
            first["spouse_person_id"] = second["person_id"]
        elif kind in ("widow", "working_widow"):
            death = 2011 + offset
            late_birth = max(1917, birth - 2)
            late = add(
                late_birth,
                other,
                rows=departed,
                marital_status="married",
                **(claim(late_birth, age) if late_birth + age < death else {}),
            )
            late["year"] = death - 1
            add(
                birth,
                level,
                marital_status="widowed",
                late_spouse_person_id=late["person_id"],
                widowhood_year=death,
                **(claim(birth, age) if kind == "working_widow" else {}),
            )
        else:
            # Fifteen years later, so an opening disabled widow(er) can
            # still be under 60 in 2030 and keep that component.
            status = "survivor" if "widow" in component else component
            row = add(birth + 15, level, status=status)
            if component == "disabled_worker":
                row.update(di_entitled=True, di_award_year=2008)
            opening[row["person_id"]] = OpeningStockRecord(
                person_id=row["person_id"],
                status=status,
                component=component,
                observed_annual_amount=float(level),
                clock_year=2008,
                clock_rule="INVENTED fixed opening clock",
                entitlement_year=2009,
                entitlement_clamped=False,
            )
    cohort = TrackACohort(
        persons=pd.DataFrame(persons),
        careers=careers,
        initial_slice=pd.DataFrame(initial),
        opening=opening,
        data_provenance="invented",
        labels=(INVENTED_COHORT_LABEL,),
        diagnostics={},
    )
    slices = [pd.DataFrame(initial)]
    if departed:
        slices.append(pd.DataFrame(departed))
    slices.append(pd.DataFrame(final))
    return cohort, ProjectionResult(
        slices=tuple(slices), traces=(), draw_index=0
    )


def emitter_rows(cohort, result, reduction, first, clock, period, cache):
    """``reference_benefit_rows`` for one invented cut, keyed by person."""
    context = BenefitContext(
        cohort,
        invented_params(),
        invented_baseline(),
        TrackAConfig(
            rows=("R0",), draw_indices=(0,), annual_reduction=reduction
        ),
    )
    row = RegisteredRow(
        row_id="INVENTED",
        field_changed=None,
        first_reduced_determination_year=first,
        exposure_clock=clock,
        benefit_period=period,
        components=a7.PRIMARY_COMPONENTS,
        headline_statistic="ratio_of_scenario_means",
    )
    rows, _ = reference_benefit_rows(
        result, draw=0, row=row, context=context, pia_cache=cache
    )
    return {person["person_id"]: person for person in rows}


EMITTER_PERSON = st.tuples(
    st.sampled_from(
        (
            "worker",
            "disabled_worker",
            "converted_worker",
            "couple",
            "widow",
            "working_widow",
            "opening",
        )
    ),
    st.integers(1917, 1965),  # birth year
    st.integers(1_000, 90_000),  # earnings level, or opening amount
    st.integers(62, 70),  # claim age
    st.integers(1_000, 90_000),  # partner's earnings level
    st.integers(0, 19),  # year offset for DI awards and deaths
    st.sampled_from(a7.PRIMARY_COMPONENTS),  # opening-stock component
)
#: One INVENTED person of every kind, with a dually entitled spouse and
#: widow(er), and one opening-stock recipient of each component.
EMITTER_COVERAGE_PEOPLE = [
    ("worker", 1950, 40_000, 66, 1_000, 0, "spouse"),
    ("disabled_worker", 1960, 30_000, 62, 1_000, 5, "spouse"),
    ("converted_worker", 1955, 30_000, 62, 1_000, 0, "spouse"),
    ("couple", 1950, 2_000, 66, 80_000, 2, "spouse"),
    ("widow", 1952, 1_000, 66, 60_000, 9, "spouse"),
    ("working_widow", 1952, 2_000, 66, 70_000, 9, "spouse"),
    *(
        ("opening", 1960, 12_000, 62, 1_000, 0, component)
        for component in a7.PRIMARY_COMPONENTS
    ),
]
#: The same people without the two dually entitled kinds, so P is checked.
SINGLY_ENTITLED_PEOPLE = [
    person
    for person in EMITTER_COVERAGE_PEOPLE
    if person[0] not in ("couple", "working_widow")
]


@given(
    people=st.lists(EMITTER_PERSON, min_size=1, max_size=6),
    cuts=st.tuples(st.integers(0, 200), st.integers(0, 200)),
    firsts=st.tuples(
        st.sampled_from((2010, 2011, 2027)),
        st.sampled_from((2010, 2011, 2027)),
    ),
    clock=st.sampled_from(tuple(sb.ExposureClock)),
    period=st.sampled_from(tuple(sb.BenefitPeriod)),
)
@example(
    people=EMITTER_COVERAGE_PEOPLE,
    cuts=(50, 150),
    firsts=(2010, 2027),
    clock=sb.ExposureClock.ELIGIBILITY,
    period=sb.BenefitPeriod.CALENDAR_YEAR,
)
@example(
    people=SINGLY_ENTITLED_PEOPLE,
    cuts=(50, 150),
    firsts=(2010, 2027),
    clock=sb.ExposureClock.ENTITLEMENT,
    period=sb.BenefitPeriod.DECEMBER,
)
@settings(max_examples=40, deadline=None)
def test_registered_emitter_is_monotone_in_the_cut_outside_dual_entitlement(
    people, cuts, firsts, clock, period
):
    """Monotonicity on ``reference_benefit_rows`` itself (review r2, 2).

    INVENTED cohorts (:func:`emitter_inputs`) go through the registered
    emitter under a smaller and a larger ``TrackAConfig.annual_reduction``,
    and an earlier and a later ``RegisteredRow``
    ``first_reduced_determination_year``. Membership and baseline amounts
    do not move. Every person's benefit, and every component, weakly
    falls under the stronger cut, and so does P. Dual entitlement is the
    intended exception: an auxiliary excess paid beside the person's own
    worker benefit (``spouse`` or ``aged_widow``) can rise, so it, the
    person's total and P go unasserted when a dually entitled person is
    present. Their own worker component still weakly falls. Two explicit
    examples run every time: the coverage cohort, and the same people
    without dual entitlement, so P is checked.
    """
    smaller, larger = (cut / 10_000 for cut in sorted(cuts))
    earlier, later = sorted(firsts)
    cohort, result = emitter_inputs(people)
    cache = {}
    runs = {
        name: emitter_rows(
            cohort, result, reduction, first, clock, period, cache
        )
        for name, reduction, first in (
            ("smaller", smaller, later),
            ("larger", larger, later),
            ("earlier", smaller, earlier),
        )
    }
    dual = {
        pid
        for pid, person in runs["smaller"].items()
        if OWN_COMPONENTS & set(person["benefit_components"])
        and AUXILIARY_COMPONENTS & set(person["benefit_components"])
    }
    for stronger in ("larger", "earlier"):
        assert set(runs[stronger]) == set(runs["smaller"])
        for pid, weak in runs["smaller"].items():
            strong = runs[stronger][pid]
            assert strong["benefit_base"] == weak["benefit_base"] > 0
            components = weak["benefit_components"]
            assert set(strong["benefit_components"]) == set(components)
            for name, amounts in components.items():
                if pid in dual and name in AUXILIARY_COMPONENTS:
                    continue  # the intended dual-entitlement exception
                assert (
                    strong["benefit_components"][name]["reform"]
                    <= amounts["reform"]
                    <= amounts["base"]
                )
            if pid not in dual:
                assert (
                    strong["benefit_reform"]
                    <= weak["benefit_reform"]
                    <= weak["benefit_base"]
                )
    if runs["smaller"] and not dual:
        p = {
            name: ac.summarize_cost(
                list(rows.values()), draw_indices=(0,), floor_seeds=(0, 1)
            )["per_draw"][0][ac.P]
            for name, rows in runs.items()
        }
        assert p["larger"] <= p["smaller"] <= 0
        assert p["earlier"] <= p["smaller"]


def test_emitter_cohort_reaches_every_path_and_dual_entitlement():
    """The invented cohort builder reaches each emitter path it names.

    The coverage cohort (one INVENTED person of every kind) gives
    benefits on every primary component, a projected and an opening-stock
    basis, and a dually entitled person, so the property above, whose
    explicit example it is, is not vacuous. Without the dually entitled
    kinds, nobody is dually entitled, so that example checks P.
    """
    cohort, result = emitter_inputs(EMITTER_COVERAGE_PEOPLE)
    rows = emitter_rows(
        cohort,
        result,
        0.01,
        2027,
        sb.ExposureClock.ELIGIBILITY,
        sb.BenefitPeriod.CALENDAR_YEAR,
        {},
    )
    components = set().union(
        *(person["benefit_components"] for person in rows.values())
    )
    assert components == set(a7.PRIMARY_COMPONENTS)
    assert {person["basis"] for person in rows.values()} == {
        "projected",
        "opening_stock",
    }
    assert any(
        OWN_COMPONENTS & set(person["benefit_components"])
        and AUXILIARY_COMPONENTS & set(person["benefit_components"])
        for person in rows.values()
    )
    cohort, result = emitter_inputs(SINGLY_ENTITLED_PEOPLE)
    single = emitter_rows(
        cohort,
        result,
        0.01,
        2027,
        sb.ExposureClock.ENTITLEMENT,
        sb.BenefitPeriod.DECEMBER,
        {},
    )
    assert single
    assert not any(
        OWN_COMPONENTS & set(person["benefit_components"])
        and AUXILIARY_COMPONENTS & set(person["benefit_components"])
        for person in single.values()
    )


def test_component_membership_can_disappear_without_refusing_cost_split():
    row = record(base=150, reform=100)
    row["benefit_components"] = {
        "disabled_worker": {"base": 100, "reform": 100},
        "aged_widow": {"base": 50, "reform": 0},
    }
    result = ac.summarize_cost([row], draw_indices=(0,))
    cell = result["per_draw"][0]
    assert cell[ac.P_OASI] == -100
    assert cell[ac.P_DI] == 0
    assert cell[ac.P] == pytest.approx(-100 / 3)


def test_a7_validation_is_preserved_for_duplicates_and_component_sum():
    row = record()
    with pytest.raises(a7.ColaTabulationError, match="duplicate"):
        ac.summarize_cost([row, row], draw_indices=(0,))
    wrong = deepcopy(row)
    wrong["benefit_base"] += 1
    with pytest.raises(a7.ColaTabulationError, match="sum"):
        ac.summarize_mint([wrong], draw_indices=(0,))


def late_spouse_records(reduction, first_year=2027):
    """Two invented living spouses; the later excess has no age reduction.

    The claimant claims own retirement at 62 in 2025 and spouse excess at
    67 in 2030. The linked worker first claims at 62 in 2030. These are
    valid eligibility and entitlement clocks; all paths retain dime floors.
    """
    params = invented_params()
    baseline = sb.COLASeries(
        by_determination_year={year: 0.028 for year in range(1979, 2031)},
        provenance={"invented": True},
    )
    reform = sb.COLAReform(
        annual_reduction=reduction,
        first_reduced_determination_year=first_year,
    )
    own_clock = sb.WorkerClock.at_age_62(1963, entitlement_year=2025)
    linked_clock = sb.WorkerClock.at_age_62(1968, entitlement_year=2030)
    own_factor = 1 - ss_benefits.early_reduction(
        params.fra_months(1963) - 62 * 12, params
    )
    own = sb.OwnBenefit(100, own_factor, own_clock)
    own_path = sb.worker_scenario_paths(
        eligibility_pia=own.eligibility_pia,
        claim_age_factor=own.claim_age_factor,
        clock=own.clock,
        baseline=baseline,
        reform=reform,
    )
    linked_path = sb.worker_scenario_paths(
        eligibility_pia=260,
        claim_age_factor=own_factor,
        clock=linked_clock,
        baseline=baseline,
        reform=reform,
    )
    spouse_path = sb.spouse_scenario_paths(
        worker_eligibility_pia=260,
        worker_clock=linked_clock,
        own=own,
        months_early=max(0, params.fra_months(1963) - 67 * 12),
        entitlement_year=2030,
        params=params,
        baseline=baseline,
        reform=reform,
    )
    base_own = own_path.baseline_monthly_by_payment_year[2030]
    reform_own = own_path.reform_monthly_by_payment_year[2030]
    base_spouse = spouse_path.baseline_monthly_by_payment_year[2030]
    reform_spouse = spouse_path.reform_monthly_by_payment_year[2030]
    claimant = record(
        1,
        family=1,
        age=67,
        base=12 * (base_own + base_spouse),
        reform=12 * (reform_own + reform_spouse),
        spouse_class="another_worker",
    )
    claimant["benefit_components"] = {
        "retired_worker": {"base": 12 * base_own, "reform": 12 * reform_own},
        "spouse": {"base": 12 * base_spouse, "reform": 12 * reform_spouse},
    }
    linked = record(
        2,
        family=1,
        age=62,
        base=12 * linked_path.baseline_monthly_by_payment_year[2030],
        reform=12 * linked_path.reform_monthly_by_payment_year[2030],
    )
    assert own_path.reduced_increases_by_payment_year[2030] >= 3
    assert linked_path.reduced_increases_by_payment_year[2030] == 0
    assert base_spouse > 0  # the legacy baseline-only excess gate keeps it
    return [claimant, linked]


def test_valid_dual_entitlement_can_raise_benefits_under_registered_cut():
    records = late_spouse_records(0.01)
    claimant, linked = records
    assert claimant["benefit_reform"] > claimant["benefit_base"]
    assert linked["benefit_reform"] == linked["benefit_base"]
    result = ac.summarize_cost(records, draw_indices=(0,))
    assert result["per_draw"][0][ac.P] > 0
    assert result["intended_bound_violations"] == list(
        ac.INTENDED_BOUND_VIOLATIONS
    )
    mint = ac.summarize_mint(records, draw_indices=(0,))
    assert (
        mint["bands"]["Total"]["per_draw"][0][ac.MEDIAN_INDIVIDUAL_PCT_CHANGE]
        > 0
    )
    assert mint["intended_bound_violations"] == list(
        ac.INTENDED_BOUND_VIOLATIONS
    )
    earlier = ac.summarize_cost(
        late_spouse_records(0.01, 2026), draw_indices=(0,)
    )
    assert earlier["per_draw"][0][ac.P] > result["per_draw"][0][ac.P]
    json.dumps(result, allow_nan=False)


@given(st.integers(3, 20))
@settings(max_examples=20, deadline=None)
def test_dual_entitlement_bound_violation_is_structural_under_dime_floors(
    mills,
):
    smaller = late_spouse_records(mills / 1000)
    larger = late_spouse_records((mills + 1) / 1000)
    assert smaller[0]["benefit_reform"] > smaller[0]["benefit_base"]
    assert larger[0]["benefit_reform"] >= smaller[0]["benefit_reform"]
    for rows in (smaller, larger):
        result = ac.summarize_cost(rows, draw_indices=(0,), floor_seeds=(0, 1))
        assert result["per_draw"][0][ac.P] > 0
