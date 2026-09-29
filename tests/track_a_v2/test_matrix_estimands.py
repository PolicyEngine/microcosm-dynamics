"""INVENTED DATA - NOT A COMPARISON: §§7–8, 12.8–12.9 invariants."""

from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.estimates import cola_age_profile as a7
from populace_dynamics.track_a_v2.estimands import (
    pair_scenarios,
    tabulate_rows,
)
from populace_dynamics.track_a_v2.matrix import (
    ARTIFACT_LABELS,
    HEADLINES,
    HISTORICAL_ROWS,
    MATRIX,
    MECHANISMS,
    ROW_IDS,
    UNION_STATISTIC,
    a7_config,
    get_row,
)


def item(base, reform, *, person=1, draw=0, weight=1.0, family=None):
    return {
        "draw": draw,
        "person_id": person,
        "family_unit_id": person if family is None else family,
        "birth_year": 1963,
        "weight": weight,
        "beneficiary_base": base > 0,
        "beneficiary_reform": reform > 0,
        "benefit_base": base,
        "benefit_reform": reform,
        "benefit_components": {
            "retired_worker": {"base": base, "reform": reform}
        },
    }


def summary(rows, row_id="U0", draws=(0,), seeds=(0, 1, 2, 3, 4)):
    row = get_row("D", row_id)
    result = tabulate_rows(rows, row, draw_indices=draws, floor_seeds=seeds)
    return result["groups"][2][row.statistic]


def test_matrix_order_headlines_labels_and_inherited_fields():
    """Exactly 68 immutable rows retain fixed headlines and inherited fields."""
    assert len(MATRIX) == 68
    expected_ids = (
        tuple(f"R{i}" for i in range(6))
        + tuple(f"F{i}" for i in range(8))
        + ("U0", "U1", "U2")
    )
    assert ROW_IDS == expected_ids
    assert [r.key for r in MATRIX] == [
        f"{mechanism}×{row_id}"
        for mechanism in ("L", "D", "S", "DS")
        for row_id in expected_ids
    ]
    assert tuple(r.key for r in MATRIX if r.headline) == HEADLINES
    assert HEADLINES == ("D×R0", "D×F0")
    for row in MATRIX:
        assert row.labels[:3] == ARTIFACT_LABELS
        response = row.row_id in ("F3", "F4", "U1", "U2")
        assert row.labels[-1] == (
            "fixed paths; stylized claiming response (registered sensitivity)"
            if response
            else "fixed-path mechanical incidence"
        )
        assert row.source_row.anchor_wave == 2011
        assert [g["label"] for g in row.as_dict()["age_groups"]] == [
            "50-61",
            "62-64",
            "65-69",
            "70-79",
            "80+",
        ]
    for union, fra in zip(("U0", "U1", "U2"), ("F0", "F3", "F4"), strict=True):
        assert get_row("L", union).source_row == get_row("L", fra).source_row
        assert get_row("L", union).statistic == UNION_STATISTIC
    assert set(HISTORICAL_ROWS) == {"R6", "F8"}
    assert set(HISTORICAL_ROWS.values()) == {
        "not rerun: requires a second population"
    }
    assert get_row("D", "F0").source_row.schedule_id == "P3"
    assert get_row("D", "F1").source_row.schedule_id == "P1"
    assert get_row("D", "F2").source_row.schedule_id == "P2"
    assert get_row("D", "R5").components == a7.WORKERS_ONLY_COMPONENTS
    assert get_row("D", "F6").components == a7.WORKERS_ONLY_COMPONENTS
    assert get_row("D", "R3").statistic == a7.MEAN_OF_INDIVIDUAL_RATIOS
    assert get_row("D", "F5").statistic == a7.MEAN_OF_INDIVIDUAL_RATIOS
    with pytest.raises(ValueError, match="unregistered"):
        get_row("D", "R6")


@pytest.mark.parametrize(
    "base,reform,union,recipient",
    [(10, 0, -100, None), (0, 10, None, None), (0, 0, None, None)],
)
def test_definedness_table(base, reform, union, recipient):
    """U needs positive baseline totals; R also needs both recipient bases."""
    rows = [item(base, reform)]
    assert summary(rows)["mean"] == union
    assert summary(rows, "F0")["mean"] == recipient


def test_empty_population_and_empty_draws_are_undefined():
    """Empty cells and missing draws are undefined rather than discarded."""
    for row_id in ("U0", "F0", "R0"):
        assert summary([], row_id)["mean"] is None
        result = summary([item(10, 9)], row_id, draws=(0, 1))
        assert result["mean"] is result["sample_sd"] is None
        assert result["n_defined_draws"] == 1
        assert result["undefined_draws"][0]["draw"] == 1


def test_only_union_cells_publish_all_alive_diagnostics():
    """Only U's retained double-zero frame reports all-alive denominators."""
    records = [item(10, 9), item(0, 0, person=2, weight=3)]
    for row_id in ("R0", "F0", "U0"):
        row = get_row("D", row_id)
        result = tabulate_rows(
            records if row_id == "U0" else records[:1],
            row,
            draw_indices=(0,),
        )
        cell = result["groups"][2]["cells"][0]
        if row_id == "U0":
            assert cell["all_alive_count"] == 2
            assert cell["all_alive_weight"] == 4
            assert cell["all_alive_mean_base"] == 2.5
            assert cell["all_alive_mean_reform"] == 2.25
        else:
            assert not any(key.startswith("all_alive_") for key in cell)
        assert result["groups"][2][row.statistic]["mean"] == pytest.approx(-10)


def test_mean_of_draw_statistics_and_sample_sd_are_not_pooled():
    """Draw summaries average percentages and use the K−1 SD divisor."""
    rows = [item(10, 9), item(1000, 800, draw=1)]
    result = summary(rows, draws=(0, 1))
    assert result["mean"] == pytest.approx(-15)
    assert result["sample_sd"] == pytest.approx(50**0.5)
    assert result["mean"] != pytest.approx(100 * (809 / 1010 - 1))


def test_undefined_half_excludes_seed_and_two_seed_minimum():
    """Either undefined half drops the seed; fewer than two never means zero."""
    result = summary([item(10, 9)])
    assert result["floor"]["n_seeds"] == 0
    assert result["floor"]["mean"] is None
    assert result["floor"]["dropped_seeds"] == [0, 1, 2, 3, 4]
    rows = [item(10, 9), item(20, 16, person=2)]
    result = summary(rows, seeds=(0,))
    assert result["floor"]["n_seeds"] == 1
    assert result["floor"]["mean"] is None
    assert result["floor"]["sd"] is None
    result = summary(rows, seeds=(0, 8))
    assert result["floor"]["n_seeds"] == 2
    assert result["floor"]["mean"] == pytest.approx(10)


@given(
    st.lists(
        st.tuples(
            st.integers(1, 10000),
            st.integers(1, 10000),
            st.integers(1, 100),
        ),
        min_size=1,
        max_size=12,
    )
)
@settings(max_examples=25, deadline=None)
def test_union_accounting_equal_membership_and_double_zero_property(values):
    """U conserves totals, equals all-alive mean change, and ignores double zeros."""
    rows = [
        item(b, r, weight=w, person=p) for p, (b, r, w) in enumerate(values)
    ]
    total_b = sum(b * w for b, _, w in values)
    total_r = sum(r * w for _, r, w in values)
    population_weight = sum(w for _, _, w in values)
    expected = 100 * (
        (total_r / population_weight) / (total_b / population_weight) - 1
    )
    result = summary(rows)
    assert result["mean"] == pytest.approx(expected)
    assert result["mean"] == pytest.approx(summary(rows, "F0")["mean"])
    assert summary(rows + [item(0, 0, person=100)])["mean"] == pytest.approx(
        result["mean"]
    )
    cells = tabulate_rows(
        rows + [item(0, 0, person=100)],
        get_row("D", "U0"),
        draw_indices=(0,),
    )["groups"][2]["cells"]
    assert cells[0]["weighted_total_base"] == total_b
    assert cells[0]["weighted_total_reform"] == total_r
    assert cells[0]["all_alive_weight"] == population_weight + 1
    assert cells[0]["all_alive_mean_base"] == total_b / (population_weight + 1)


@pytest.mark.parametrize("row_id", ("R0", "R3", "F0", "F5"))
def test_differential_against_a7_recipient_estimates_and_floors(row_id):
    """Retained R/F statistics and half-split floors reproduce A7 exactly."""
    rows = [
        item(10 + p, 6 + p + d, person=p, draw=d, weight=p + 1)
        for d in (0, 1)
        for p in range(6)
    ]
    row = get_row("L", row_id)
    config = a7_config(row, draw_indices=(0, 1))
    legacy = a7.tabulate_cola_age_profile(
        rows, config=config, data_provenance="invented"
    )
    result = tabulate_rows(rows, row, draw_indices=(0, 1))
    for old, new in zip(legacy["groups"], result["groups"], strict=True):
        assert old[row.statistic] == new[row.statistic]


@given(st.permutations(list(range(8))))
@settings(max_examples=12, deadline=None)
def test_person_row_order_determinism(order):
    """Per-person input order cannot change statistics or family split floors."""
    rows = [item(10 + p, 8 + p, person=p) for p in range(8)]
    assert summary([rows[p] for p in order]) == summary(rows)


@pytest.mark.parametrize("mechanism", MECHANISMS)
@pytest.mark.parametrize("row_id", ("R0", "R3", "F0", "F5", "U0"))
def test_null_reform_statistic_identity(mechanism, row_id):
    """A null reform has exactly zero incidence under each mechanism."""
    result = tabulate_rows(
        [item(10, 10), item(500, 500, person=2)],
        get_row(mechanism, row_id),
        draw_indices=(0,),
    )
    assert (
        result["groups"][2][get_row(mechanism, row_id).statistic]["mean"] == 0
    )


def test_pairing_refuses_person_weight_and_fixed_metadata_mismatches():
    """Scenario pairing preserves people, weights and fixed cohort attributes."""
    base = {
        1: {
            "weight": 2,
            "birth_year": 1963,
            "family_unit_id": 1,
            "components": {"retired_worker": 0},
        }
    }
    assert len(pair_scenarios(base, base, draw=0)) == 1
    with pytest.raises(ValueError, match="different persons"):
        pair_scenarios(base, {}, draw=0)
    for field in ("weight", "birth_year", "family_unit_id"):
        reform = deepcopy(base)
        reform[1][field] += 1
        with pytest.raises(ValueError, match=field):
            pair_scenarios(base, reform, draw=0)


@pytest.mark.parametrize("bad", (-1, float("inf"), float("nan")))
def test_invalid_components_are_refused_by_a7_normalization(bad):
    """Nonnegative finite components and exact accounting are required."""
    rows = [item(10, bad)]
    with pytest.raises(ValueError):
        summary(rows)
    rows = [item(10, 9)]
    rows[0]["benefit_base"] = 11
    with pytest.raises(ValueError, match="sum"):
        summary(rows)


def test_f5_uses_only_common_positive_recipients():
    """F5 uses individual ratios on the intersection, not scenario means."""
    rows = [item(10, 9), item(10, 0, person=2), item(0, 5, person=3)]
    assert summary(rows, "F5")["mean"] == pytest.approx(-10)
    assert summary(rows, "F0")["mean"] == pytest.approx(-30)


def test_twenty_draw_count_and_fixed_sampling_protocol():
    """Registered defaults are twenty draws and five family half-split seeds."""
    row = get_row("D", "U0")
    config = a7_config(row)
    assert config.draw_indices == tuple(range(20))
    assert config.floor_seeds == (0, 1, 2, 3, 4)
    assert config.floor_split_unit == a7.FAMILY_UNIT
    rows = [item(10, 9, draw=d) for d in range(20)]
    result = tabulate_rows(rows, row)["groups"][2][row.statistic]
    assert result["n_defined_draws"] == 20
    assert result["mean"] == pytest.approx(-10)


@pytest.mark.parametrize("row_id", ("R5", "F6"))
@pytest.mark.parametrize("mechanism,reference", (("S", "L"), ("DS", "D")))
def test_workers_only_paired_floor_preserves_identity_and_legacy_replay(
    row_id, mechanism, reference
):
    """Extra zero-worker spouse families cannot change paired worker floors."""
    # Minimal fixture: two positive worker families plus one S-only spouse
    # family. §§9/12.9 require equal uncertainty as well as point statistics;
    # preserve the corresponding L/D family frame and A1 §16 split rule.
    legacy = [item(100, 90, person=3), item(100, 80, person=4)]
    spouse = item(0, 0, person=1)
    spouse.update(
        beneficiary_base=True,
        beneficiary_reform=True,
        benefit_base=100,
        benefit_reform=90,
    )
    spouse["benefit_components"]["spouse"] = {"base": 100, "reform": 90}
    old_row = get_row(reference, row_id)
    new_row = get_row(mechanism, row_id)
    old = tabulate_rows(legacy, old_row, draw_indices=(0,))
    new = tabulate_rows(
        [spouse, *legacy], new_row, draw_indices=(0,), floor_records=legacy
    )
    for old_group, new_group in zip(old["groups"], new["groups"], strict=True):
        assert old_group[old_row.statistic] == new_group[new_row.statistic]
    assert old["floor_per_seed"] == new["floor_per_seed"]
    selected = old["groups"][2][old_row.statistic]
    assert selected["mean"] == pytest.approx(-15)
    assert selected["floor"]["n_seeds"] == 1
    assert selected["floor"]["mean"] is None
    inherited = a7._normalize(legacy, a7_config(old_row, draw_indices=(0,)))
    _, legacy_floors = a7._floors(
        inherited, a7_config(old_row, draw_indices=(0,))
    )
    assert selected["floor"] == legacy_floors["65-69"][old_row.statistic]


@pytest.mark.parametrize("field", ("benefit", "weight", "family", "birth"))
def test_paired_worker_floor_refuses_changed_selected_inputs(field):
    """Pairing floors refuses changed worker amounts, weights or fixed cells."""
    legacy = [item(100, 90)]
    changed = deepcopy(legacy)
    if field == "benefit":
        changed[0] = item(100, 89)
    else:
        changed[0][
            {
                "weight": "weight",
                "family": "family_unit_id",
                "birth": "birth_year",
            }[field]
        ] += 1
    with pytest.raises(ValueError, match="worker-only amounts or population"):
        tabulate_rows(
            changed,
            get_row("S", "R5"),
            draw_indices=(0,),
            floor_records=legacy,
        )
