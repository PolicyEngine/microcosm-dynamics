"""Tests for B2's named power procedure (the B0.1 addendum).

The procedure reads no data. These tests check it four ways:

- differential: the quadrature equals a brute-force simulation of the same
  Gaussian model;
- reproduction: in its limits it returns the frozen audit's bound-rule
  figures and M6's own operating characteristic;
- properties: probabilities lie in [0, 1], the joint probability respects
  the Frechet bounds, and power falls with the shared-anchor ratio, the
  estimation variance and the family size and rises with the tolerance;
- the ladder: it never prunes the last cell of a concept family, it stops
  at the first power at or above 0.90, and it flags the vacuity guard.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_addendum_power as power  # noqa: E402
import track_b_b0_1_review_power as review_power  # noqa: E402

TAU = power.TAU_UNCAPPED


def test_uncapped_tolerance_matches_the_audit_basis():
    assert power.FLOOR_RATIO == pytest.approx(2.6063, abs=5e-5)
    assert TAU == pytest.approx(
        review_power.tol_over_gap_se("full_support"), rel=1e-12
    )
    assert TAU == pytest.approx(5.0870, abs=5e-5)


@pytest.mark.parametrize(
    ("m", "expected"), [(1, 0.9982), (4, 0.9621), (6, 0.9170), (16, 0.5844)]
)
def test_bound_rule_only_reproduces_the_q2_correction(m, expected):
    term = power.cell_terms(TAU, 1.0, 0.0, 0.0, m)
    assert term.bound == pytest.approx(
        review_power.bound_rule_pass("full_support", m), rel=1e-10
    )
    gate = power.gate_probabilities([term] * m)
    assert gate["p_bound_rule_only"] == pytest.approx(expected, abs=5e-5)


def test_gate_level_room_is_about_three_percent_at_six_cells():
    record = power.structural_record()["by_family_size"]
    assert record["6"]["estimation_room_per_cell"] == pytest.approx(
        review_power.estimation_headroom("full_support", 6), rel=1e-10
    )
    assert record["6"]["estimation_room_gate_bound_only"] == pytest.approx(
        0.0284, abs=5e-5
    )
    assert record["5"]["estimation_room_gate_bound_only"] == pytest.approx(
        0.0838, abs=5e-5
    )
    assert record["4"]["estimation_room_gate_bound_only"] == pytest.approx(
        0.1596, abs=5e-5
    )
    assert record["16"]["estimation_room_gate_bound_only"] < 0


@pytest.mark.parametrize(
    ("m", "expected"), [(1, 0.9992), (6, 0.9742), (16, 0.8590)]
)
def test_m6_convention_reproduces_the_audit(m, expected):
    assert power.m6_convention_gate(m) == pytest.approx(expected, abs=5e-5)


def _simulate(cells, n, seed):
    rng = np.random.default_rng(seed)
    m = len(cells)
    bound_ok = np.ones(n, dtype=bool)
    seeds_ok = np.ones((n, power.N_SEEDS), dtype=bool)
    for tau, r, e_true, e_reg in cells:
        x = rng.normal(0.0, math.sqrt(r**2 + e_true), n)
        c = tau - power.z_star(m) * math.sqrt(r**2 + e_reg)
        bound_ok &= np.abs(x) <= c
        side = x[:, None] + r * rng.normal(size=(n, power.N_SEEDS))
        seeds_ok &= np.abs(side) <= tau
    seeds = seeds_ok.sum(axis=1) >= power.SEEDS_REQUIRED
    return {
        "p_gate": float(np.mean(bound_ok & seeds)),
        "p_bound_rule_only": float(np.mean(bound_ok)),
        "p_seed_conjunction_only": float(np.mean(seeds)),
    }


@pytest.mark.parametrize(
    "cells",
    [
        [(TAU, 1.0, 0.0, 0.0)] * 6,
        [(TAU, 0.6, 0.1, 0.15), (4.5, 0.9, 0.05, 0.05), (TAU, 0.3, 0.0, 0.02)],
        [(3.0, 1.2, 0.2, 0.2), (2.5, 0.8, 0.0, 0.1)],
    ],
)
def test_quadrature_matches_brute_force_simulation(cells):
    n = 400_000
    simulated = _simulate(cells, n, seed=len(cells))
    m = len(cells)
    exact = power.gate_probabilities(
        [power.cell_terms(t, r, e, g, m) for t, r, e, g in cells]
    )
    for key, value in simulated.items():
        se = math.sqrt(max(value * (1.0 - value), 1e-6) / n)
        assert exact[key] == pytest.approx(value, abs=5.0 * se)


_cell = st.tuples(
    st.floats(min_value=1.0, max_value=8.0),
    st.floats(min_value=0.05, max_value=1.5),
    st.floats(min_value=0.0, max_value=0.5),
    st.floats(min_value=0.0, max_value=0.5),
)


@settings(max_examples=40, deadline=None)
@given(st.lists(_cell, min_size=1, max_size=5))
def test_probabilities_are_bounded_and_respect_frechet(cells):
    m = len(cells)
    gate = power.gate_probabilities(
        [power.cell_terms(t, r, e, g, m) for t, r, e, g in cells]
    )
    eps = 1e-9
    for key in ("p_gate", "p_bound_rule_only", "p_seed_conjunction_only"):
        assert -eps <= gate[key] <= 1 + eps
    joint = gate["p_gate"]
    bound = gate["p_bound_rule_only"]
    seeds = gate["p_seed_conjunction_only"]
    assert joint <= min(bound, seeds) + eps
    assert joint >= bound + seeds - 1 - eps


@settings(max_examples=40, deadline=None)
@given(_cell, st.floats(min_value=0.01, max_value=0.5))
def test_power_falls_with_estimation_variance(cell, extra):
    tau, r, e_true, e_reg = cell
    base = power.cell_terms(tau, r, e_true, e_reg, 6)
    more = power.cell_terms(tau, r, e_true + extra, e_reg + extra, 6)
    assert more.bound <= base.bound + 1e-12
    assert more.a4 <= base.a4 + 1e-9


@settings(max_examples=40, deadline=None)
@given(_cell, st.floats(min_value=0.01, max_value=0.5))
def test_power_falls_with_the_shared_anchor_ratio(cell, extra):
    tau, r, e_true, e_reg = cell
    base = power.cell_terms(tau, r, e_true, e_reg, 6)
    more = power.cell_terms(tau, r + extra, e_true, e_reg, 6)
    assert more.bound <= base.bound + 1e-12
    assert more.a5 <= base.a5 + 1e-9


@settings(max_examples=40, deadline=None)
@given(_cell, st.floats(min_value=0.01, max_value=2.0))
def test_power_rises_with_the_tolerance(cell, extra):
    tau, r, e_true, e_reg = cell
    base = power.cell_terms(tau, r, e_true, e_reg, 6)
    wider = power.cell_terms(tau + extra, r, e_true, e_reg, 6)
    assert wider.bound >= base.bound - 1e-12
    assert wider.a5 >= base.a5 - 1e-9
    assert wider.b5 >= base.b5 - 1e-9


@settings(max_examples=30, deadline=None)
@given(_cell, st.integers(min_value=1, max_value=15))
def test_bound_pass_falls_with_family_size(cell, m):
    tau, r, e_true, e_reg = cell
    assume(tau > power.z_star(m + 1) * math.sqrt(r**2 + e_reg))
    assert (
        power.cell_terms(tau, r, e_true, e_reg, m + 1).bound
        <= power.cell_terms(tau, r, e_true, e_reg, m).bound + 1e-12
    )


def test_seed_conjunction_rarely_binds_on_the_upper_bound_basis():
    for m in (1, 6, 16):
        record = power.structural_record()["by_family_size"][str(m)]
        assert record["p_seeds_fail_given_bound_passes"] < 1e-3


def _cells(r=1.0, e=0.0, ratios=None):
    names = sorted(power.CONCEPT_FAMILY_CELLS)
    ratios = ratios or {}
    return [
        power.PlanningCell(
            name,
            r,
            e,
            e,
            tol_over_sigma=ratios.get(name, power.FLOOR_RATIO),
        )
        for name in names
    ]


def test_ladder_keeps_one_cell_per_family_and_stops_at_the_target():
    result = power.ladder(_cells())
    families = {power.concept(name) for name in result["retained"]}
    assert families == set(power.CONCEPT_FAMILY.values())
    pruned = [row for row in result["log"] if row["action"] == "pruned"]
    if result["p_gate"] >= power.POWER_TARGET:
        # the last prune is the first to reach the target
        before = [row["p_gate_after"] for row in pruned[:-1]]
        assert all(value < power.POWER_TARGET for value in before)
    assert len(result["retained"]) + len(result["pruned"]) == 16


def test_ladder_prunes_largest_tolerance_over_sigma_first():
    ratios = {"earn_p90.older": 3.1, "earn_p50.prime": 2.9}
    result = power.ladder(_cells(r=1.0, e=0.05, ratios=ratios))
    first = [row["cell"] for row in result["log"]][:2]
    assert first == ["earn_p90.older", "earn_p50.prime"]


def test_ladder_reports_weak_power_when_six_families_cannot_clear():
    result = power.ladder(_cells(r=1.0, e=0.3))
    assert len(result["retained"]) == 6
    assert result["clears"] is False
    assert result["p_gate"] < power.POWER_TARGET


def test_admissible_surfaces_cover_every_family():
    names = sorted(power.CONCEPT_FAMILY_CELLS)
    surfaces = list(power.admissible_surfaces(names))
    # 1 + one or more cells from each family: (2^6 - 1) * (2^2 - 1)^5.
    assert len(surfaces) == (2**6 - 1) * (2**2 - 1) ** 5
    assert all(
        {power.concept(name) for name in surface}
        == set(power.CONCEPT_FAMILY.values())
        for surface in surfaces
    )


# --------------------------------------------------------------------------
# Binding basis, verdicts and the seed-conjunction statement
# --------------------------------------------------------------------------
def _planning(r=0.8, e=0.01, e_ucl=0.02, factor=1.1, cross=False):
    e_b2 = max(0.0, e_ucl) * factor
    s2 = r**2 + factor * max(0.0, e)
    s2_ucl = r**2 + e_b2
    return {
        "design_rule": {"household_resampling_stands": True, "limit": 1.10},
        "cells": {
            name: {
                "defined": True,
                "shared_anchor_ratio": {"r": r, "ci": [r * 0.97, r * 1.03]},
                "estimation_variance": {
                    "e": e,
                    "e_ucl": e_ucl,
                    "e_b2": e_b2,
                },
                "gap_variance": {
                    "s2": s2,
                    "s2_ucl": s2_ucl,
                    "cross_term_resolved_positive": cross,
                    "s2_gate": s2_ucl,
                },
                "design_ratio": {
                    "d": 1.0,
                    "ci": [0.95, 1.05],
                    "within_limit": True,
                },
            }
            for name in power.CONCEPT_FAMILY_CELLS
        },
    }


def test_binding_basis_is_the_joint_upper_limit_on_gap_variance():
    planning = _planning()
    cell = power.planning_cells(planning, "binding")["earn_p10.prime"]
    assert cell.r == 0.8
    assert cell.r**2 + cell.e_true == pytest.approx(0.64 + 0.02 * 1.1)
    assert cell.e_true == cell.e_reg
    central = power.planning_cells(planning, "central")["earn_p10.prime"]
    assert central.r**2 + central.e_true == pytest.approx(0.64 + 0.011)
    assert central.e_reg == pytest.approx(0.022)
    upper = power.planning_cells(planning, "audit_upper_bound")
    assert upper["earn_p10.prime"].r == 1.0
    with pytest.raises(ValueError, match="unknown basis"):
        power.planning_cells(planning, "other")


def test_power_record_names_one_binding_basis_and_the_flags():
    planning = _planning(r=0.7, e_ucl=0.05)
    planning["cells"]["earn_p90.older"] = {"defined": False}
    record = power.power_record(planning)
    assert [b for b, v in record["bases"].items() if v["binding"]] == [
        "binding"
    ]
    flags = record["planning_flags"]
    assert flags["cells_without_planning_values"] == ["earn_p90.older"]
    assert flags["household_resampling_stands"] is True
    binding = record["bases"]["binding"]
    assert "earn_p90.older" not in binding["per_cell"]
    assert binding["verdict"]["feasible"] is True
    assert binding["m6_retained_6"]["p_gate"] > 0.90


def test_undefined_planning_cells_cannot_gate():
    planning = _planning()
    planning["cells"]["earn_p10.prime"] = {"defined": False}
    assert "earn_p10.prime" not in power.planning_cells(planning, "binding")


def test_verdict_feasible_when_cancellation_leaves_room():
    verdict = power.feasibility_verdict(
        power.planning_cells(_planning(r=0.7, e_ucl=0.05), "binding")
    )
    assert verdict["feasible"] and not verdict["d693_flip_fires"]


def test_verdict_flip_fires_when_four_cells_cannot_clear():
    verdict = power.feasibility_verdict(
        power.planning_cells(
            _planning(r=1.0, e_ucl=0.3, factor=1.0), "binding"
        )
    )
    assert verdict["d693_flip_fires"] and not verdict["feasible"]


def test_verdict_flags_the_family_floor_conflict_for_max():
    # At r = 1 the four-cell room is 0.160 and the six-cell room 0.028.
    verdict = power.feasibility_verdict(
        power.planning_cells(
            _planning(r=1.0, e_ucl=0.08, factor=1.0), "binding"
        )
    )
    assert not verdict["d693_flip_fires"]
    assert verdict["family_floor_blocks"] and not verdict["feasible"]
    assert verdict["best_four_cell_surface"]["p_gate"] >= 0.90
    assert verdict["best_family_surface_p_gate"] < 0.90


@settings(max_examples=40, deadline=None)
@given(
    st.floats(min_value=0.2, max_value=1.3),
    st.floats(min_value=0.0, max_value=0.3),
    st.integers(min_value=1, max_value=16),
)
def test_seed_failures_given_a_bound_pass_respect_the_structural_bound(
    r, e, m
):
    term = power.cell_terms(TAU, r, e, e, m)
    assume(term.bound > 1e-6)
    gate = power.gate_probabilities([term] * m)
    assert gate["p_seeds_fail_given_bound_passes"] <= (
        power.seed_conjunction_bound(m) + 1e-9
    )


def test_m6_seed_convention_sensitivity_reproduces_its_6_cell_value():
    record = power.structural_record()["by_family_size"]["6"]
    assert record["m6_seed_convention_with_bound_rule"] == pytest.approx(
        0.9170 * 0.9742, abs=2e-4
    )
    assert record["m6_seed_convention_with_bound_rule"] < 0.90
    assert record["p_gate_joint"] > 0.90


@pytest.mark.parametrize("rho", [0.3, 0.6])
def test_independence_understates_the_bound_rule_pass(rho):
    rng = np.random.default_rng(int(rho * 10))
    m, n, r, e = 6, 300_000, 1.0, 0.02
    s = math.sqrt(r**2 + e)
    common = rng.normal(size=(n, 1))
    x = s * (
        math.sqrt(rho) * common + math.sqrt(1 - rho) * rng.normal(size=(n, m))
    )
    c = TAU - power.z_star(m) * math.sqrt(r**2 + e)
    correlated = float(np.mean(np.all(np.abs(x) <= c, axis=1)))
    independent = power.cell_terms(TAU, r, e, e, m).bound ** m
    assert correlated >= independent - 3 * math.sqrt(
        independent * (1 - independent) / n
    )


# --------------------------------------------------------------------------
# Post-run illustrations for Max's decisions (they decide nothing)
# --------------------------------------------------------------------------
def _named_cells(spec):
    return {
        name: power.PlanningCell(name, r, e, e)
        for name, (r, e) in spec.items()
    }


SMALL = {
    "earn_p90.prime": (0.69, 0.08),
    "earn_zero_rate.older": (0.71, 0.10),
    "earn_autocorr_lag2": (0.98, 0.42),
    "earn_dlog_sd.older": (1.01, 1.24),
    "earn_mob_h2_diag": (1.06, 0.67),
}


def test_surface_scan_agrees_with_the_named_procedure_on_every_size():
    cells = _named_cells(SMALL)
    scan = power.surfaces_reaching(cells, target=0.0)
    best = {
        m: power.best_surface_of_size(cells, m)
        for m in range(1, len(cells) + 1)
    }
    assert scan["largest_surface"]["cells"] == best[len(cells)]["cells"]
    assert scan["largest_surface"]["p_gate"] == pytest.approx(
        best[len(cells)]["p_gate"], rel=1e-12
    )
    for slot in scan["by_family_count"].values():
        m = len(slot["cells"])
        subset = [cells[n] for n in slot["cells"]]
        assert slot["p_gate"] == pytest.approx(
            power.surface_power(subset)["p_gate"], rel=1e-12
        )
        assert slot["p_gate"] <= best[m]["p_gate"] + 1e-12


def test_surface_scan_reports_only_surfaces_at_the_target():
    cells = _named_cells(SMALL)
    scan = power.surfaces_reaching(cells)
    largest = scan["largest_surface"]
    assert largest["p_gate"] >= 0.90
    bigger = power.best_surface_of_size(cells, len(largest["cells"]) + 1)
    assert bigger is None or bigger["p_gate"] < 0.90
    for k, slot in scan["by_family_count"].items():
        assert slot["p_gate"] >= 0.90
        assert len(slot["families"]) == int(k)
        assert slot["families"] == sorted(
            {power.concept(n) for n in slot["cells"]}
        )


def test_design_inflation_scales_r_only_over_the_limit():
    planning = _planning(r=0.7, e_ucl=0.05)
    planning["cells"]["earn_p50.older"]["design_ratio"]["ci"] = [1.2, 1.26]
    binding = power.planning_cells(planning, "binding")
    inflated = power.design_inflated(planning, binding)
    for name, cell in inflated.items():
        factor = 1.26 if name == "earn_p50.older" else 1.0
        assert cell.r == pytest.approx(binding[name].r * factor)
        assert cell.e_true == binding[name].e_true
        assert cell.e_reg == binding[name].e_reg


def test_power_record_carries_the_illustrations_and_labels_them():
    planning = _planning(r=0.7, e_ucl=0.05)
    illus = power.power_record(planning)["decision_illustrations"]
    assert illus["decides_nothing"] is True and illus["basis"] == "binding"
    pruned = illus["families_may_be_pruned"]
    # No cell is over the limit, so inflation changes nothing.
    assert pruned["as_measured"] == pruned["design_inflated"]
    assert pruned["as_measured"]["largest_surface"]["p_gate"] >= 0.90
