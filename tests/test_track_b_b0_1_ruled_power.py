"""Tests for B2's power on the configuration Max ruled (d765, d781, d782).

The procedure reads no data. These tests check it four ways:

- differential: with infinite degrees of freedom, d = 1 and the normal
  critical value it equals protocol v2's terms (adaptive quadrature), its
  expectation over the estimated standard error equals nested adaptive
  quadrature, and the whole gate equals a brute-force simulation of the
  same model;
- properties: probabilities lie in [0, 1] and respect the Frechet bounds;
  power falls with the design ratio and the critical value and rises with
  the tolerance and, for a known standard error, with the degrees of
  freedom;
- reproduction: on household resampling it returns the 0.952 that d781
  cites;
- the record: it recomputes from the planning record, and its verdict
  follows from the binding evaluation.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st
from scipy import integrate
from scipy.stats import chi2, norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import track_b_b0_1_addendum_power as power  # noqa: E402
import track_b_b0_1_ruled_power as ruled  # noqa: E402

PLANNING = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"
POWER = ROOT / "docs" / "design" / "track_b_b0_1_addendum_power.json"
RECORD = ROOT / "docs" / "design" / "track_b_b0_1_ruled_power.json"
TAU = power.TAU_UNCAPPED


@pytest.fixture(scope="module")
def planning():
    return json.loads(PLANNING.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


# Critical values and degrees of freedom.


def test_t_critical_value_at_six_cells_and_63_df():
    assert ruled.t_star(6, 63) == pytest.approx(2.7241, abs=5e-5)
    assert power.z_star(6) == pytest.approx(2.6383, abs=5e-5)
    assert ruled.t_star(6, None) == power.z_star(6)
    assert ruled.t_star(6, math.inf) == power.z_star(6)
    with pytest.raises(ValueError):
        ruled.t_star(0, 63)
    with pytest.raises(ValueError):
        ruled.t_star(6, 0)


@settings(max_examples=50, deadline=None)
@given(st.integers(1, 16), st.integers(2, 400), st.integers(1, 400))
def test_t_critical_value_exceeds_z_and_falls_with_df(m, nu, extra):
    assert ruled.t_star(m, nu) > power.z_star(m)
    assert ruled.t_star(m, nu + extra) < ruled.t_star(m, nu)


def test_degrees_of_freedom_come_from_the_record_s_strata(planning):
    design = planning["counts"]["design"]
    assert ruled.design_degrees_of_freedom(design) == 63
    assert design["strata"] == design["strata_with_two_clusters"] == 63
    with pytest.raises(ValueError):
        ruled.design_degrees_of_freedom(
            {**design, "strata_with_three_or_more_clusters": 1}
        )
    with pytest.raises(ValueError):
        ruled.design_degrees_of_freedom({**design, "strata": 64})
    one = {
        **design,
        "strata": 64,
        "strata_with_one_cluster": 1,
    }
    assert ruled.design_degrees_of_freedom(one) == 63


# Differential checks.

_cell = st.tuples(
    st.floats(min_value=1.5, max_value=8.0),  # tau
    st.floats(min_value=0.1, max_value=1.4),  # r
    st.floats(min_value=0.0, max_value=0.6),  # e
)


@settings(max_examples=60, deadline=None)
@given(_cell, st.integers(1, 12))
# A seed spread small against the gap's: p(x) falls steeply at x = tau.
@example((2.0, 0.109375, 0.5), 1)
def test_known_se_normal_critical_d1_equals_protocol_v2(cell, m):
    tau, r, e = cell
    mine = ruled.ruled_cell_terms(tau, r, r**2, e, m, None, "z", False)
    theirs = power.cell_terms(tau, r, e, e, m)
    for field in ("bound", "a4", "a5", "b4", "b5"):
        assert getattr(mine, field) == pytest.approx(
            getattr(theirs, field), abs=1e-9
        ), field


def _nested_reference(tau, r_seed, samp, e, m, nu):
    """E over W of protocol v2's slab integrals, by adaptive quadrature."""
    s = math.sqrt(samp + e)
    crit = ruled.t_star(m, nu)
    dist = chi2(nu, scale=1.0 / nu)

    def slab(c, j):
        if c <= 0:
            return 0.0
        return integrate.quad(
            lambda x: power._seed_pass(x, tau, r_seed) ** j
            * norm.pdf(x, scale=s),
            -c,
            c,
            epsabs=1e-12,
            epsrel=1e-10,
            limit=200,
        )[0]

    def over_w(j):
        return integrate.quad(
            lambda w: slab(tau - crit * math.sqrt(samp * w + e), j)
            * dist.pdf(w),
            dist.ppf(1e-12),
            dist.ppf(1 - 1e-12),
            epsabs=1e-10,
            limit=200,
        )[0]

    return over_w(4), over_w(5)


@pytest.mark.parametrize(
    ("tau", "r", "d", "e", "m", "nu"),
    [
        (TAU, 0.737, 1.259, 0.510, 6, 63),
        (TAU, 0.686, 1.069, 0.300, 6, 63),
        (4.0, 1.0, 1.2, 0.2, 3, 10),
    ],
)
def test_expectation_over_the_estimated_se_matches_adaptive_quadrature(
    tau, r, d, e, m, nu
):
    terms = ruled.ruled_cell_terms(tau, r, (r * d) ** 2, e, m, nu)
    a4, a5 = _nested_reference(tau, r, (r * d) ** 2, e, m, nu)
    assert terms.a4 == pytest.approx(a4, abs=2e-8)
    assert terms.a5 == pytest.approx(a5, abs=2e-8)


def _simulate(cells, nu, n, seed, critical="t"):
    """Brute force: x, the estimated SE and five seeds, per cell."""
    rng = np.random.default_rng(seed)
    m = len(cells)
    crit = ruled.t_star(m, nu) if critical == "t" else power.z_star(m)
    bound_ok = np.ones(n, dtype=bool)
    seeds_ok = np.ones((n, power.N_SEEDS), dtype=bool)
    for tau, r, d, e in cells:
        samp = (r * d) ** 2
        x = rng.normal(0.0, math.sqrt(samp + e), n)
        w = rng.chisquare(nu, n) / nu
        bound_ok &= np.abs(x) + crit * np.sqrt(samp * w + e) <= tau
        side = x[:, None] + r * rng.normal(size=(n, power.N_SEEDS))
        seeds_ok &= np.abs(side) <= tau
    seeds = seeds_ok.sum(axis=1) >= power.SEEDS_REQUIRED
    return {
        "p_gate": float(np.mean(bound_ok & seeds)),
        "p_bound_rule_only": float(np.mean(bound_ok)),
        "p_seed_conjunction_only": float(np.mean(seeds)),
    }


@pytest.mark.parametrize(
    ("cells", "nu"),
    [
        (
            [
                (TAU, 0.737, 1.259, 0.510),
                (TAU, 0.754, 1.167, 0.323),
                (TAU, 0.660, 1.069, 0.404),
                (TAU, 0.686, 1.069, 0.300),
                (TAU, 0.706, 1.210, 0.300),
                (TAU, 0.787, 0.986, 0.389),
            ],
            63,
        ),
        ([(4.0, 0.9, 1.3, 0.3), (3.5, 0.5, 1.0, 0.1)], 8),
    ],
)
def test_gate_matches_brute_force_simulation(cells, nu):
    n = 400_000
    simulated = _simulate(cells, nu, n, seed=len(cells))
    m = len(cells)
    exact = power.gate_probabilities(
        [
            ruled.ruled_cell_terms(t, r, (r * d) ** 2, e, m, nu)
            for t, r, d, e in cells
        ]
    )
    for key, value in simulated.items():
        se = math.sqrt(max(value * (1.0 - value), 1e-6) / n)
        assert exact[key] == pytest.approx(value, abs=5.0 * se), key


# Properties.

_ruled = st.tuples(
    st.floats(min_value=1.5, max_value=8.0),  # tau
    st.floats(min_value=0.1, max_value=1.4),  # r
    st.floats(min_value=0.8, max_value=1.4),  # d
    st.floats(min_value=0.0, max_value=0.6),  # e
)


@settings(max_examples=40, deadline=None)
@given(st.lists(_ruled, min_size=1, max_size=6), st.integers(2, 200))
def test_probabilities_are_bounded_and_respect_frechet(cells, nu):
    m = len(cells)
    gate = power.gate_probabilities(
        [
            ruled.ruled_cell_terms(t, r, (r * d) ** 2, e, m, nu)
            for t, r, d, e in cells
        ]
    )
    eps = 1e-9
    for key in ("p_gate", "p_bound_rule_only", "p_seed_conjunction_only"):
        assert -eps <= gate[key] <= 1 + eps
    joint, bound = gate["p_gate"], gate["p_bound_rule_only"]
    seeds = gate["p_seed_conjunction_only"]
    assert joint <= min(bound, seeds) + eps
    assert joint >= bound + seeds - 1 - eps


@settings(max_examples=40, deadline=None)
@given(_ruled, st.floats(min_value=0.01, max_value=0.5), st.integers(2, 200))
def test_power_falls_with_the_design_ratio(cell, extra, nu):
    tau, r, d, e = cell
    base = ruled.ruled_cell_terms(tau, r, (r * d) ** 2, e, 6, nu)
    more = ruled.ruled_cell_terms(tau, r, (r * (d + extra)) ** 2, e, 6, nu)
    assert more.bound <= base.bound + 1e-12
    assert more.a4 <= base.a4 + 1e-9
    assert more.a5 <= base.a5 + 1e-9


@settings(max_examples=40, deadline=None)
@given(_ruled, st.integers(2, 200), st.integers(1, 200))
def test_known_se_power_rises_with_df_and_t_never_beats_z(cell, nu, extra):
    tau, r, d, e = cell
    samp = (r * d) ** 2
    fewer = ruled.ruled_cell_terms(tau, r, samp, e, 6, nu, "t", False)
    more = ruled.ruled_cell_terms(tau, r, samp, e, 6, nu + extra, "t", False)
    normal = ruled.ruled_cell_terms(tau, r, samp, e, 6, nu, "z", False)
    assert fewer.a4 <= more.a4 + 1e-9 <= normal.a4 + 2e-9
    assert fewer.bound <= more.bound + 1e-12 <= normal.bound + 2e-12


@settings(max_examples=40, deadline=None)
@given(_ruled, st.floats(min_value=0.01, max_value=2.0), st.integers(2, 200))
def test_power_rises_with_the_tolerance(cell, extra, nu):
    tau, r, d, e = cell
    base = ruled.ruled_cell_terms(tau, r, (r * d) ** 2, e, 6, nu)
    wider = ruled.ruled_cell_terms(tau + extra, r, (r * d) ** 2, e, 6, nu)
    assert wider.bound >= base.bound - 1e-12
    assert wider.a5 >= base.a5 - 1e-9
    assert wider.b5 >= base.b5 - 1e-9


# The record.


def test_record_recomputes_from_the_planning_record(planning, record):
    assert (
        record["planning_values_sha256"]
        == hashlib.sha256(PLANNING.read_bytes()).hexdigest()
    )
    fresh = json.loads(json.dumps(ruled.ruled_record(planning)))

    def close(a, b, path=""):
        if isinstance(a, dict):
            assert set(a) == set(b), path
            for key in a:
                close(a[key], b[key], f"{path}/{key}")
        elif isinstance(a, list):
            assert len(a) == len(b), path
            for index, (x, y) in enumerate(zip(a, b, strict=True)):
                close(x, y, f"{path}[{index}]")
        elif isinstance(a, float) and isinstance(b, float):
            assert a == pytest.approx(b, rel=1e-9, abs=1e-12), path
        else:
            assert a == b, path

    close(
        {k: v for k, v in record.items() if k != "planning_values_sha256"},
        fresh,
    )


def test_household_basis_reproduces_d781_s_figure(record):
    """d781 cites 0.952: the six level cells on household resampling."""
    illustration = json.loads(POWER.read_text(encoding="utf-8"))[
        "decision_illustrations"
    ]["families_may_be_pruned"]["as_measured"]["largest_surface"]
    assert sorted(illustration["cells"]) == sorted(ruled.LEVEL_CELLS)
    household = record["six_level_cells"]["household_as_measured"]["p_gate"]
    assert household == pytest.approx(illustration["p_gate"], rel=1e-9)
    assert household == pytest.approx(
        record["cross_checks"]["household_six_protocol_v2"], rel=1e-9
    )
    assert round(household, 3) == 0.952


def test_binding_evaluation_is_the_ruled_one(record):
    evaluations = record["evaluations"]
    assert [k for k, v in evaluations.items() if v["binding"]] == ["binding"]
    assert evaluations["binding"] == {
        "design": "d95",
        "critical": "t",
        "random_se": True,
        "seeds": "household",
        "binding": True,
    }
    assert record["constants"]["design_degrees_of_freedom"] == 63
    assert record["constants"]["gated_cells"] == 6
    assert set(record["per_cell"]) == set(ruled.LEVEL_CELLS)
    assert set(record["rulings"]) == {"d765", "d781", "d782"}


def test_verdict_follows_the_binding_evaluation(record):
    six = record["six_level_cells"]
    verdict = record["verdict"]
    target = record["constants"]["power_target"]
    assert verdict["ruled_six_reach_target"] is (
        six["binding"]["p_gate"] >= target
    )
    assert verdict["b2_stops"] is not verdict["ruled_six_reach_target"]
    assert verdict["every_evaluation_of_the_six_below_target"] is all(
        v["p_gate"] < target
        for k, v in six.items()
        if k != "household_as_measured"
    )
    # The finding the decision rests on.
    assert verdict["b2_stops"]
    assert verdict["every_evaluation_of_the_six_below_target"]
    assert round(six["binding"]["p_gate"], 3) == 0.813
    assert round(six["most_lenient"]["p_gate"], 3) == 0.886


def test_more_gate_seeds_cannot_help(record):
    """Given a bound-rule pass, the seed conjunction almost never fails."""
    for value in record["six_level_cells"].values():
        assert value["p_seeds_fail_given_bound_passes"] < 1e-6


def test_options_are_consistent(record):
    target = record["constants"]["power_target"]
    surfaces = record["fixed_surfaces"]
    assert sorted(map(int, surfaces), reverse=True) == [6, 5, 4]
    assert surfaces["6"]["n_surfaces"] == 1
    assert surfaces["5"]["n_surfaces"] == 6
    assert surfaces["4"]["n_surfaces"] == 14
    for slot in surfaces.values():
        assert slot["n_reaching_target"] == sum(
            row["p_gate"] >= target for row in slot["surfaces"]
        )
        for row in slot["surfaces"]:
            assert row["p_gate_most_lenient"] >= row["p_gate"]
            assert len(row["cells"]) + len(row["dropped"]) == 6
    ladder = record["ladder_inside_the_six"]
    assert ladder["orders"] == 720
    assert ladder["orders_clearing"] == sum(
        row["orders"] for row in ladder["end_surfaces"] if row["clears"]
    )
    assert sum(row["orders"] for row in ladder["end_surfaces"]) == 720
    option = record["tolerance_option"]
    assert option["k"] >= record["tolerance_for_target"]["binding"]["k"]
    assert option["p_gate"] >= target
    assert option["p_gate_most_lenient"] >= option["p_gate"]
    assert record["level_cell_gap_correlation_max"] < 0.2
