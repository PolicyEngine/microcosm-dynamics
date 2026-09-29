"""Invented-data tests for the Track B B0.1 structural count script.

The script must never let an earnings level, sign or zero indicator into
a count, and its accounting must partition the B2 domain exactly. These
tests use invented frames only; they read no staged survey file.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.harness.m6_cells import oc_4of5

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_counts as script  # noqa: E402

WAVES = (2011, 2013, 2015)
SENTINEL = 9_999_998
SEQUENCES = (0, 1, 2, 3, 20, 51, 71, 81)
RELATIONSHIPS = (10, 20, 22, 30, 33)


# --------------------------------------------------------------------------
# Invented inputs
# --------------------------------------------------------------------------
@st.composite
def invented_panel(draw):
    """Invented person-wave rows plus family labor frames per wave."""
    n_people = draw(st.integers(min_value=1, max_value=30))
    n_households = draw(st.integers(min_value=1, max_value=8))
    rows = []
    for index in range(n_people):
        base_age = draw(st.integers(min_value=18, max_value=80))
        for offset, wave in enumerate(WAVES):
            weight = draw(
                st.one_of(
                    st.just(0.0),
                    st.floats(min_value=1.0, max_value=5_000.0),
                )
            )
            rows.append(
                {
                    "person_id": 1_000 + index,
                    "period": wave,
                    "age": base_age + 2 * offset,
                    "sequence": draw(st.sampled_from(SEQUENCES)),
                    "relationship": draw(st.sampled_from(RELATIONSHIPS)),
                    "weight": weight,
                    "interview": draw(
                        st.integers(min_value=1, max_value=n_households)
                    ),
                }
            )
    person_wave = pd.DataFrame(rows)
    labor = {}
    for wave in WAVES:
        records = []
        for household in range(1, n_households + 1):
            if not draw(st.booleans()) and household > 1:
                continue  # an interview with no family record
            records.append(
                {
                    "interview": household,
                    "head_labor": draw(_labor_value()),
                    "spouse_labor": draw(_labor_value()),
                    "head_acc": draw(st.integers(min_value=0, max_value=9)),
                    "spouse_acc": draw(st.integers(min_value=0, max_value=9)),
                }
            )
        labor[wave] = pd.DataFrame(records)
    return person_wave, labor


def _labor_value():
    return st.one_of(
        st.just(float(SENTINEL)),
        st.just(0.0),
        st.floats(min_value=1.0, max_value=900_000.0),
    )


def _validity(labor):
    return {
        wave: script.validity_frame(frame) for wave, frame in labor.items()
    }


def _counts(person_wave, labor):
    return script.structural_counts(person_wave, _validity(labor))


# --------------------------------------------------------------------------
# Outcome blindness
# --------------------------------------------------------------------------
@settings(max_examples=60, deadline=None)
@given(invented_panel(), st.randoms(use_true_random=False))
def test_counts_are_invariant_to_valid_earnings_values(panel, rng):
    """Replacing every valid earnings level leaves every output unchanged."""
    person_wave, labor = panel
    perturbed = {}
    for wave, frame in labor.items():
        frame = frame.copy()
        for column in ("head_labor", "spouse_labor"):
            frame[column] = [
                (
                    value
                    if value >= SENTINEL
                    else rng.choice([0.0, 1.0, rng.uniform(1, 9e5)])
                )
                for value in frame[column]
            ]
        perturbed[wave] = frame
    original = _counts(person_wave, labor)
    changed = _counts(person_wave, perturbed)
    assert original == changed
    assert script.power_record(original) == script.power_record(changed)


def test_validity_frame_carries_no_labor_level():
    labor = pd.DataFrame(
        {
            "interview": [1, 2],
            "head_labor": [52_000.0, SENTINEL],
            "spouse_labor": [0.0, 12.0],
            "head_acc": [0, 3],
            "spouse_acc": [1, 0],
        }
    )
    out = script.validity_frame(labor)
    assert list(out.columns) == [
        "interview",
        "head_valid",
        "spouse_valid",
        "head_acc_flag",
        "spouse_acc_flag",
    ]
    assert out["head_valid"].tolist() == [True, False]
    assert out["spouse_valid"].tolist() == [True, True]
    for column in out.columns[1:]:
        assert out[column].dtype == bool


def test_validity_frame_rejects_duplicate_interviews():
    labor = pd.DataFrame(
        {
            "interview": [1, 1],
            "head_labor": [1.0, 2.0],
            "spouse_labor": [1.0, 2.0],
            "head_acc": [0, 0],
            "spouse_acc": [0, 0],
        }
    )
    with pytest.raises(ValueError, match="duplicate"):
        script.validity_frame(labor)


# --------------------------------------------------------------------------
# Accounting identities
# --------------------------------------------------------------------------
@settings(max_examples=80, deadline=None)
@given(invented_panel())
def test_dispositions_partition_the_domain(panel):
    counts = _counts(*panel)
    assert counts["domain_persons"] <= counts["full_anchor_persons"]
    assert sum(counts["domain_by_role"].values()) == counts["domain_persons"]
    assert (
        sum(counts["domain_by_anchor_wave_age"].values())
        == counts["domain_persons"]
    )
    for year, labels in counts["domain_dispositions"].items():
        assert set(labels) == set(script.DISPOSITIONS)
        assert sum(labels.values()) == counts["domain_persons"]
        assert (
            labels["scored"] == counts["scored_support"][year]["scored_rows"]
        )


@settings(max_examples=80, deadline=None)
@given(invented_panel())
def test_support_totals_add_up(panel):
    counts = _counts(*panel)
    total = 0
    for record in counts["scored_support"].values():
        assert sum(record["rows_by_cohort"].values()) == record["scored_rows"]
        assert record["assigned_or_edited_rows"] <= record["scored_rows"]
        total += record["scored_rows"]
    assert total == counts["scored_rows_total"]
    level = counts["level_cells"]
    assert level["pooled"]["rows"] == sum(
        level[name]["rows"] for name, _, _ in script.EARN_COHORTS
    )
    horizon = sum(
        counts["scored_support"][str(year)]["scored_rows"]
        for year in script.HORIZON_YEARS
    )
    assert level["pooled"]["rows"] == horizon
    change = counts["change_pairs"]
    assert change["pooled_one_step"]["rows"] >= sum(
        change[name]["rows"] for name, _, _ in script.EARN_COHORTS
    )


@settings(max_examples=40, deadline=None)
@given(invented_panel(), st.randoms(use_true_random=False))
def test_counts_are_row_order_invariant(panel, rng):
    person_wave, labor = panel
    order = list(range(len(person_wave)))
    rng.shuffle(order)
    shuffled_people = person_wave.iloc[order].reset_index(drop=True)
    shuffled_labor = {
        wave: frame.sample(frac=1.0, random_state=rng.randint(0, 999))
        for wave, frame in labor.items()
    }
    assert _counts(person_wave, labor) == _counts(
        shuffled_people, shuffled_labor
    )


def test_worked_example():
    """Five invented people with hand-derived dispositions."""
    rows = []

    def add(person, wave, age, sequence, relationship, weight, interview):
        rows.append(
            {
                "person_id": person,
                "period": wave,
                "age": age,
                "sequence": sequence,
                "relationship": relationship,
                "weight": weight,
                "interview": interview,
            }
        )

    # 1: head throughout, valid, in support -> scored both years.
    add(1, 2011, 40, 1, 10, 100.0, 1)
    add(1, 2013, 42, 1, 10, 100.0, 1)
    add(1, 2015, 44, 1, 10, 100.0, 1)
    # 2: spouse at 2011; dies before 2013.
    add(2, 2011, 60, 2, 20, 50.0, 1)
    add(2, 2013, 62, 81, 20, 0.0, 1)
    add(2, 2015, 64, 0, 0, 0.0, 0)
    # 3: head at 2011, ages out of support at 2015 (age 66).
    add(3, 2011, 62, 1, 10, 80.0, 2)
    add(3, 2013, 64, 1, 10, 80.0, 2)
    add(3, 2015, 66, 1, 10, 80.0, 2)
    # 4: child in 2011 (not in the domain), head by 2013 -> entrant.
    add(4, 2011, 22, 3, 30, 20.0, 1)
    add(4, 2013, 24, 1, 10, 20.0, 3)
    add(4, 2015, 26, 1, 10, 20.0, 3)
    # 5: head at 2011 whose 2013 earnings are missing, then moves out.
    add(5, 2011, 30, 1, 10, 60.0, 2)
    add(5, 2013, 32, 1, 10, 60.0, 4)
    add(5, 2015, 34, 71, 10, 0.0, 0)
    person_wave = pd.DataFrame(rows)
    labor = {
        2011: pd.DataFrame(
            {
                "interview": [1, 2],
                "head_labor": [1.0, 2.0],
                "spouse_labor": [3.0, 0.0],
                "head_acc": [0, 0],
                "spouse_acc": [0, 0],
            }
        ),
        2013: pd.DataFrame(
            {
                "interview": [1, 2, 3, 4],
                "head_labor": [1.0, 2.0, 5.0, float(SENTINEL)],
                "spouse_labor": [0.0, 0.0, 0.0, 0.0],
                "head_acc": [1, 0, 0, 0],
                "spouse_acc": [0, 0, 0, 0],
            }
        ),
        2015: pd.DataFrame(
            {
                "interview": [1, 2, 3],
                "head_labor": [1.0, 2.0, 7.0],
                "spouse_labor": [0.0, 0.0, 0.0],
                "head_acc": [0, 0, 0],
                "spouse_acc": [0, 0, 0],
            }
        ),
    }
    counts = _counts(person_wave, labor)
    assert counts["full_anchor_persons"] == 5
    assert counts["domain_persons"] == 4  # persons 1, 2, 3, 5
    assert counts["domain_by_role"] == {"head": 3, "spouse": 1}
    assert counts["domain_dispositions"]["2012"] == {
        **{name: 0 for name in script.DISPOSITIONS},
        "scored": 2,
        "died": 1,
        "head_or_spouse_earnings_missing": 1,
    }
    assert counts["domain_dispositions"]["2014"] == {
        **{name: 0 for name in script.DISPOSITIONS},
        "scored": 1,
        "valid_row_age_outside_support": 1,
        "not_in_responding_family": 1,
        "moved_out": 1,
    }
    assert counts["scored_support"]["2012"]["rows_by_cohort"] == {
        "prime": 1,
        "older": 1,
    }
    assert counts["scored_support"]["2012"]["assigned_or_edited_rows"] == 1
    assert (
        counts["scored_support"]["2014"][
            "valid_domain_rows_outside_age_support"
        ]
        == 1
    )
    assert counts["entrants_not_scored"]["2014"] == {
        "in_2011_anchor_without_valid_boundary_row": {
            "prime": 1,
            "older": 0,
        },
        "outside_2011_anchor": {"prime": 0, "older": 0},
    }
    # Person 4 is 24 at the 2013 wave, below the support: not an entrant.
    assert counts["entrants_not_scored"]["2012"][
        "in_2011_anchor_without_valid_boundary_row"
    ] == {"prime": 0, "older": 0}
    # Person 1 carries prime rows at 2010 and 2012 and 2014.
    assert counts["change_pairs"]["prime"]["rows"] == 2
    assert counts["change_pairs"]["pooled_two_step"]["rows"] == 1


# --------------------------------------------------------------------------
# Effective sizes
# --------------------------------------------------------------------------
@settings(max_examples=200, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.floats(min_value=0.1, max_value=1e4),
            st.integers(min_value=0, max_value=6),
        ),
        min_size=1,
        max_size=40,
    )
)
def test_effective_size_bounds(pairs):
    weights = np.array([weight for weight, _ in pairs])
    clusters = np.array([cluster for _, cluster in pairs])
    kish = script.kish_n_eff(weights)
    worst = script.cluster_worst_n_eff(weights, clusters)
    assert worst <= kish * (1 + 1e-12)
    assert kish <= len(weights) * (1 + 1e-12)
    assert worst >= 1.0 - 1e-12
    singletons = script.cluster_worst_n_eff(weights, np.arange(len(weights)))
    assert math.isclose(singletons, kish, rel_tol=1e-12)


def test_effective_size_rejects_nonpositive_weights():
    with pytest.raises(ValueError):
        script.kish_n_eff(np.array([1.0, 0.0]))
    with pytest.raises(ValueError):
        script.cluster_worst_n_eff(np.array([1.0, -1.0]), np.array([1, 2]))


# --------------------------------------------------------------------------
# Design-based power
# --------------------------------------------------------------------------
def test_half_normal_floor_ratio_matches_simulation():
    rng = np.random.default_rng(20260929)
    scores = np.abs(rng.normal(0.0, 1.0, 2_000_000))
    empirical = scores.mean() + 3 * scores.std(ddof=1)
    analytic = script.half_normal_floor_ratio(3)
    assert math.isclose(analytic, 2.606315, abs_tol=1e-6)
    assert abs(empirical - analytic) < 0.005


@settings(max_examples=100, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.floats(min_value=0.01, max_value=1.0),
            st.floats(min_value=0.5, max_value=4.0),
        ),
        min_size=1,
        max_size=16,
    )
)
def test_p_gate_matches_the_m6_operating_characteristic(cells):
    floor = {
        f"c{i}": {"realized_sigma": sigma}
        for i, (sigma, _) in enumerate(cells)
    }
    tolerances = {
        f"c{i}": sigma * ratio for i, (sigma, ratio) in enumerate(cells)
    }
    reference = oc_4of5(floor, tolerances, sorted(floor))
    p_seed = math.prod(
        script.cell_pass_probability(ratio) for _, ratio in cells
    )
    assert math.isclose(
        round(script.p_gate(p_seed), 4),
        reference["p_gate_pass_4_of_5"],
        abs_tol=1e-4,
    )


@settings(max_examples=100, deadline=None)
@given(
    st.floats(min_value=0.0, max_value=1.0),
    st.floats(min_value=0.0, max_value=1.0),
)
def test_p_gate_is_monotone_and_bounded(a, b):
    low, high = sorted((a, b))
    assert 0.0 <= script.p_gate(low) <= script.p_gate(high) <= 1.0 + 1e-12
    assert script.p_gate(1.0) == pytest.approx(1.0)
    assert script.p_gate(0.0) == pytest.approx(0.0)


def test_max_uncapped_surface_is_the_boundary():
    ratio = script.half_normal_floor_ratio(3)
    p_cell = script.cell_pass_probability(ratio)
    m = script.max_uncapped_surface(ratio)
    assert script.p_gate(p_cell**m) >= 0.90
    assert script.p_gate(p_cell ** (m + 1)) < 0.90


@settings(max_examples=60, deadline=None)
@given(st.integers(min_value=1, max_value=40))
def test_bound_rule_round_trip_and_monotonicity(m):
    ratio = script.bound_rule_ratio(m)
    assert script.bound_rule_pass_probability(ratio, m) == pytest.approx(
        0.90, abs=1e-9
    )
    assert script.bound_rule_ratio(m + 1) > ratio
    assert script.bound_rule_pass_probability(ratio - 1e-3, m) < 0.90


def test_bound_rule_pass_probability_matches_simulation():
    rng = np.random.default_rng(7)
    m, ratio = 6, 5.0
    z_star = script.bonferroni_z(m)
    gap = rng.normal(0.0, 1.0, 1_000_000)
    simulated = np.mean(np.abs(gap) + z_star <= ratio)
    analytic = script.bound_rule_pass_probability(ratio, m)
    assert abs(simulated - analytic) < 4 * math.sqrt(
        analytic * (1 - analytic) / gap.size
    )


@settings(max_examples=100, deadline=None)
@given(
    st.floats(min_value=0.005, max_value=0.2),
    st.floats(min_value=0.005, max_value=0.2),
    st.integers(min_value=1, max_value=20),
)
def test_required_sizes_fall_with_tolerance(tol_a, tol_b, m):
    low, high = sorted((tol_a, tol_b))
    assert script.required_n_eff_proportion(
        high, m
    ) <= script.required_n_eff_proportion(low, m)
    assert script.required_n_eff_correlation(
        high, m
    ) <= script.required_n_eff_correlation(low, m)
    assert script.required_n_eff_proportion(
        low, m + 1
    ) > script.required_n_eff_proportion(low, m)


@settings(max_examples=100, deadline=None)
@given(
    st.floats(min_value=0.01, max_value=0.5),
    st.sampled_from((0.1, 0.5, 0.9)),
    st.floats(min_value=10.0, max_value=1e6),
    st.integers(min_value=1, max_value=20),
)
def test_quantile_dispersion_threshold_round_trip(tol, q, n_eff, m):
    sigma = script.max_log_sd_for_quantile(tol, q, n_eff, m)
    z_q = float(script.norm.ppf(q))
    se = sigma * math.sqrt(q * (1 - q) / n_eff) / float(script.norm.pdf(z_q))
    inflation = math.sqrt(1 + 1 / script.M6_DRAWS)
    assert se * inflation * script.bound_rule_ratio(m) == pytest.approx(tol)
    assert script.max_log_sd_for_quantile(tol, q, 4 * n_eff, m) == (
        pytest.approx(2 * sigma)
    )


@settings(max_examples=100, deadline=None)
@given(st.floats(min_value=0.5, max_value=20.0))
def test_min_draws_for_mc_is_the_smallest_sufficient_count(ratio):
    k = script.min_draws_for_mc(ratio)
    assert 1 / math.sqrt(k) < 0.1 * ratio
    if k > 1:
        assert not 1 / math.sqrt(k - 1) < 0.1 * ratio


def test_power_record_structure_on_worked_counts():
    counts = {
        "level_cells": {
            "prime": {"kish_n_eff": 9_000.0, "cluster_worst_n_eff": 5_000.0},
            "older": {"kish_n_eff": 6_000.0, "cluster_worst_n_eff": 3_500.0},
        },
        "change_pairs": {
            "pooled_one_step": {
                "kish_n_eff": 12_000.0,
                "cluster_worst_n_eff": 7_000.0,
            },
            "pooled_two_step": {
                "kish_n_eff": 5_000.0,
                "cluster_worst_n_eff": 3_000.0,
            },
        },
    }
    record = script.power_record(counts)
    rule = record["m6_floor_rule"]
    assert rule["floor_ratio_tol_over_sigma_half"] == pytest.approx(2.606315)
    assert rule["max_uncapped_cells_at_0_90"] >= 6
    six = record["section_5_2_bound_rule"]["6"]
    assert six["pass_probability_at_m6_floor_tolerance_gap_sigma_half"] < 0.5
    assert six["k_needed_for_floor_tolerance"] > 3
    limits = record["section_5_3_limits_on_b2_support"]["6"]
    assert set(limits["by_cohort"]) == {"prime", "older"}
    assert set(limits["persistence"]) == {
        "lag1_pooled_one_step",
        "lag2_pooled_two_step",
    }


def test_empty_support_records_no_share_instead_of_dividing_by_zero():
    """Minimized Hypothesis counterexample: nobody present at the anchor."""
    person_wave = pd.DataFrame(
        {
            "person_id": [1000, 1000, 1000],
            "period": list(WAVES),
            "age": [18, 20, 22],
            "sequence": [0, 0, 0],
            "relationship": [10, 10, 10],
            "weight": [0.0, 0.0, 0.0],
            "interview": [1, 1, 1],
        }
    )
    labor = {
        wave: pd.DataFrame(
            {
                "interview": [1],
                "head_labor": [float(SENTINEL)],
                "spouse_labor": [float(SENTINEL)],
                "head_acc": [0],
                "spouse_acc": [0],
            }
        )
        for wave in WAVES
    }
    counts = _counts(person_wave, labor)
    assert counts["domain_persons"] == 0
    record = script.power_record(counts)
    persistence = record["section_5_3_limits_on_b2_support"]["6"][
        "persistence"
    ]
    for value in persistence.values():
        assert value["min_positive_share_kish"] is None
        assert value["min_positive_share_cluster_worst"] is None


# --------------------------------------------------------------------------
# Output guards (exercised before any staged file is opened)
# --------------------------------------------------------------------------
def test_main_refuses_to_overwrite(tmp_path):
    existing = tmp_path / "counts.json"
    existing.write_text("{}")
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        script.main(["--out", str(existing)])


def test_main_refuses_the_committed_evidence_directory():
    target = script.RUNS_DIR / "track_b_b0_1_counts_should_not_exist.json"
    assert not target.exists()
    with pytest.raises(SystemExit, match="writes no file"):
        script.main(["--out", str(target)])
