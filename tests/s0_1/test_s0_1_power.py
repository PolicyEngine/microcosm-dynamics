"""S0.1 power procedures on invented data (``scripts/s0_1_power.py``).

Every population and estimate here is invented. The invariants:

* the decision rule is three-way, and only a bound wholly inside the
  tolerance passes;
* continuous normal estimates with positive standard errors control the
  boundary pass rate at the nominal level, within Monte Carlo error;
  sparse discrete estimates and zero-width bounds need separate checks;
* power is nondecreasing in sample size and in the margin between the
  true error and the tolerance;
* Bonferroni bounds cover at least nominally across a registered family;
* fixed seeds give identical results and leave global random state alone;
* malformed inputs are refused.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "s0_1_power", ROOT / "scripts/s0_1_power.py"
)
power = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = power
SPEC.loader.exec_module(power)

RESULTS = ROOT / "docs/design/s0_1_power_results.json"
TAU = power.SM3_TOLERANCE
GRADIENT = (0.45, 0.15, 0.0, -0.2, -0.45)


def _mc_band(p: float, n: int, k: float = 3.0) -> float:
    return k * math.sqrt(p * (1 - p) / n)


# --------------------------------------------------------------------------
# Decision rule
# --------------------------------------------------------------------------
def test_bonferroni_z_matches_normal_quantiles():
    assert power.bonferroni_z(1) == pytest.approx(1.959964, abs=1e-6)
    assert power.bonferroni_z(20) == pytest.approx(3.023341, abs=1e-6)
    values = [power.bonferroni_z(m) for m in range(1, 60)]
    assert all(b > a for a, b in zip(values, values[1:], strict=False))


def test_classify_bounds_is_three_way():
    est = np.array([0.0, 0.0, 0.5, -0.5, 0.1, np.nan])
    half = np.array([0.1, 0.2, 0.1, 0.1, 0.1, 0.1])
    out = power.classify_bounds(est, half, TAU)
    assert list(out) == [
        "pass",
        "inconclusive",
        "fail",
        "fail",
        "inconclusive",
        "inconclusive",
    ]


@pytest.mark.parametrize(
    "estimate, expected",
    [
        (0.0, "pass"),
        (-TAU, "pass"),
        (TAU, "pass"),
        (np.nextafter(-TAU, -np.inf), "fail"),
        (np.nextafter(TAU, np.inf), "fail"),
        (np.nan, "inconclusive"),
    ],
)
def test_zero_width_bounds_include_the_equivalence_endpoints(
    estimate, expected
):
    """The closed tolerance interval admits degenerate endpoint bounds."""
    assert power.classify_bounds([estimate], [0.0], TAU)[0] == expected


def test_conjunction_needs_every_cell():
    assert power.conjunction(["pass", "pass"]) == "pass"
    assert power.conjunction(["pass", "inconclusive"]) == "inconclusive"
    assert power.conjunction(["inconclusive", "fail"]) == "fail"


# --------------------------------------------------------------------------
# Type-I error at the equivalence boundary
# --------------------------------------------------------------------------
def test_normal_boundary_pass_rate_matches_nominal_level():
    """Positive-SE normal estimates approach alpha / 2 at the boundary."""
    rng = np.random.default_rng(11)
    n, se = 40_000, 0.01
    est = rng.normal(TAU, se, size=n)
    z = power.bonferroni_z(1)
    passed = np.mean(
        power.classify_bounds(est, np.full(n, z * se), TAU) == "pass"
    )
    nominal = power.ALPHA / 2
    assert abs(passed - nominal) <= _mc_band(nominal, n)


@pytest.mark.parametrize("m", [4, 20])
def test_normal_family_boundary_pass_rate_is_at_most_nominal(m):
    """Positive-SE normals with one boundary cell: alpha / (2m)."""
    rng = np.random.default_rng(29 + m)
    n, se = 60_000, 0.01
    z = power.bonferroni_z(m)
    centres = np.zeros(m)
    centres[0] = TAU
    est = centres + rng.normal(0, se, size=(n, m))
    outcomes = power.classify_bounds(est, np.full(est.shape, z * se), TAU)
    passed = np.mean((outcomes == "pass").all(axis=1))
    nominal = power.ALPHA / (2 * m)
    assert passed <= nominal + _mc_band(nominal, n)
    assert abs(passed - nominal) <= _mc_band(nominal, n)


def test_sm3_nonsparse_boundary_matches_the_normal_reference():
    """Check the normal boundary reference for this nonsparse fixture."""
    stratum = power.InventedStratum(
        n_clusters=3_000,
        group_shares=(0.1, 0.9),
        unclassified_share=0.0,
        mean_risk=0.3,
        weight_cv=0.3,
    )
    misfit = power.misfit_for_target_log_ratio(stratum, 0, TAU)
    boundary = power.InventedStratum(
        **{**asdict(stratum), "true_log_misfit": misfit}
    )
    truth = power._population_log_ratio(boundary, seed=1)
    assert truth[0] == pytest.approx(TAU, abs=1e-12)
    result = power.simulate_sm3_family([boundary], n_sims=300, seed=5)
    nominal = power.ALPHA / 4
    assert result.pass_rate <= nominal + _mc_band(nominal, 300)


# --------------------------------------------------------------------------
# Monotonicity of power
# --------------------------------------------------------------------------
@settings(max_examples=80, deadline=None)
@given(
    m=st.integers(1, 60),
    delta=st.floats(0.0, 0.9),
    d_small=st.floats(20.0, 5_000.0),
    factor=st.floats(1.0, 10.0),
)
def test_power_nondecreasing_in_sample_size(m, delta, d_small, factor):
    d_large = d_small * factor
    shift = delta * TAU
    small = power.family_power([shift] * m, [math.sqrt(1 / d_small)] * m, TAU)
    large = power.family_power([shift] * m, [math.sqrt(1 / d_large)] * m, TAU)
    assert large >= small - 1e-12


@settings(max_examples=80, deadline=None)
@given(
    m=st.integers(1, 60),
    se=st.floats(0.005, 0.2),
    a=st.floats(0.0, 0.99),
    b=st.floats(0.0, 0.99),
)
def test_power_nondecreasing_in_margin(m, se, a, b):
    """A smaller true error (a larger margin) never lowers power."""
    near, far = sorted((a, b))
    p_near = power.family_power([near * TAU] * m, [se] * m, TAU)
    p_far = power.family_power([far * TAU] * m, [se] * m, TAU)
    assert p_near >= p_far - 1e-12


@settings(max_examples=40, deadline=None)
@given(m=st.integers(1, 60), share=st.floats(0.0, 0.5))
def test_min_effective_deaths_is_minimal(m, share):
    d = power.min_effective_deaths_per_cell(m, group_share=share)
    at = power.family_power_lower_bound(
        [0.0] * m, [math.sqrt((1 - share) / d)] * m, TAU
    )
    below = power.family_power_lower_bound(
        [0.0] * m, [math.sqrt((1 - share) / max(d - 1, 1))] * m, TAU
    )
    assert at >= power.POWER_CRITERION
    assert below < power.POWER_CRITERION + 1e-6


@settings(max_examples=40, deadline=None)
@given(m=st.integers(1, 40), share=st.floats(0.05, 0.6))
def test_min_effective_model_n_is_minimal(m, share):
    n = power.min_effective_n_per_cell(m, share=share)
    se_at = power.share_difference_se(share, n, 1e18)
    at = power.family_power_lower_bound(
        [0.0] * m, [se_at] * m, power.ED2_TOLERANCE
    )
    assert at >= power.POWER_CRITERION


def test_unreachable_ed2_target_is_none():
    assert (
        power.min_effective_n_per_cell(20, share=0.3, n_target_eff=500) is None
    )


# --------------------------------------------------------------------------
# Coverage of Bonferroni bounds
# --------------------------------------------------------------------------
@settings(max_examples=25, deadline=None)
@given(m=st.integers(2, 40), rho=st.floats(-0.02, 0.9))
def test_bonferroni_bounds_cover_correlated_families(m, rho):
    rng = np.random.default_rng(m * 1_000 + int(rho * 997))
    n = 6_000
    cov = np.full((m, m), rho) + np.eye(m) * (1 - rho)
    eigen = np.linalg.eigvalsh(cov)
    if eigen.min() <= 0:
        return
    draws = rng.multivariate_normal(np.zeros(m), cov, size=n)
    z = power.bonferroni_z(m)
    covered = np.mean((np.abs(draws) <= z).all(axis=1))
    nominal = 1 - power.ALPHA
    assert covered >= nominal - _mc_band(nominal, n)


def test_engine_bounds_cover_the_population_ratio():
    stratum = power.InventedStratum(
        n_clusters=2_000,
        group_shares=(0.2,) * 5,
        mean_risk=0.2,
        model_log_rr=GRADIENT,
        frailty_variance=0.0,
    )
    result = power.simulate_sm3_family([stratum], n_sims=200, seed=3)
    nominal = 1 - power.ALPHA
    assert result.extra["diagnostic_coverage"] >= nominal - _mc_band(
        nominal, 200
    )
    assert result.inconclusive_rate == 1.0


def test_linearized_se_matches_simulated_spread():
    stratum = power.InventedStratum(
        n_clusters=1_500,
        group_shares=(0.2,) * 5,
        mean_risk=0.2,
        model_log_rr=GRADIENT,
    )
    rng = np.random.default_rng(17)
    estimates, ses = [], []
    for _ in range(150):
        obs, exp_, design = power._simulate_cluster_totals(stratum, rng)
        estimates.append(power.log_ratio_estimates(obs, exp_))
        ses.append(power.linearized_se(obs, exp_, design))
    spread = np.nanstd(np.array(estimates), axis=0, ddof=1)
    mean_se = np.nanmean(np.array(ses), axis=0)
    analytic = power.stratum_analytic_ses(stratum)
    np.testing.assert_allclose(mean_se, spread, rtol=0.2)
    np.testing.assert_allclose(analytic, spread, rtol=0.2)


def test_bootstrap_se_matches_linearized_se():
    stratum = power.InventedStratum(
        n_clusters=2_000,
        group_shares=(0.2,) * 5,
        mean_risk=0.2,
        model_log_rr=GRADIENT,
    )
    rng = np.random.default_rng(23)
    obs, exp_, design = power._simulate_cluster_totals(stratum, rng)
    lin = power.linearized_se(obs, exp_, design)
    boot = power.bootstrap_se(obs, exp_, design, 400, rng)
    np.testing.assert_allclose(boot, lin, rtol=0.2)


def test_stratified_variance_matches_direct_sum():
    rng = np.random.default_rng(31)
    z = rng.normal(size=(50, 3))
    design = np.arange(50) % 7
    direct = np.zeros(3)
    for h in range(7):
        rows = z[design == h]
        n_h = rows.shape[0]
        direct += n_h / (n_h - 1) * ((rows - rows.mean(0)) ** 2).sum(0)
    np.testing.assert_allclose(
        power._stratified_cluster_variance(z, design), direct, rtol=1e-12
    )


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------
def test_fixed_seed_is_deterministic_and_leaves_global_state():
    stratum = power.InventedStratum(
        n_clusters=600, group_shares=(0.5, 0.5), mean_risk=0.2
    )
    cell = power.InventedSharesCell(
        shares=(0.3, 0.7), n_model=400, n_target=600, replicates=3
    )
    state = np.random.get_state()[1].copy()
    first = power.simulate_sm3_family([stratum], n_sims=20, seed=99)
    second = power.simulate_sm3_family([stratum], n_sims=20, seed=99)
    e1 = power.simulate_ed2_family([cell], n_sims=15, seed=7)
    e2 = power.simulate_ed2_family([cell], n_sims=15, seed=7)
    assert first == second
    assert e1 == e2
    np.testing.assert_array_equal(np.random.get_state()[1], state)


def test_ed2_engine_covers_true_difference():
    cell = power.InventedSharesCell(
        shares=(0.1, 0.3, 0.6),
        n_model=3_000,
        n_target=5_000,
        replicates=4,
        bias=(0.01, -0.005, -0.005),
    )
    result = power.simulate_ed2_family([cell], n_sims=120, seed=13)
    nominal = 1 - power.ALPHA
    assert result.coverage >= nominal - _mc_band(nominal, 120)


def test_cumulative_risk_bound_on_invented_q():
    def flat(year, sex):
        return np.full(120, 0.01)

    bound = power.cumulative_risk_bound(flat, (50, 64), range(2012, 2024), 2)
    assert bound == pytest.approx(1 - (1 - 0.02) ** 12, rel=1e-12)
    short = power.cumulative_risk_bound(flat, (60, 62), range(2012, 2024), 1)
    assert short == pytest.approx(1 - 0.99**3, rel=1e-12)


def test_misfit_hits_requested_population_ratio():
    stratum = power.InventedStratum(
        n_clusters=100,
        group_shares=(0.2, 0.3, 0.5),
        unclassified_share=0.2,
        model_log_rr=(0.3, 0.0, -0.3),
    )
    for target in (-0.1, 0.0, 0.14):
        misfit = power.misfit_for_target_log_ratio(stratum, 1, target)
        shifted = power.InventedStratum(
            **{**asdict(stratum), "true_log_misfit": misfit}
        )
        truth = power._population_log_ratio(shifted, seed=0)
        assert truth[1] == pytest.approx(target, abs=1e-12)


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "call",
    [
        lambda: power.bonferroni_z(0),
        lambda: power.bonferroni_z(2.5),
        lambda: power.bonferroni_z(True),
        lambda: power.bonferroni_z(3, alpha=0.0),
        lambda: power.bonferroni_z(3, alpha=1.0),
        lambda: power.classify_bounds([0.0], [0.1, 0.2], TAU),
        lambda: power.classify_bounds([0.0], [-0.1], TAU),
        lambda: power.classify_bounds([0.0], [0.1], float("nan")),
        lambda: power.conjunction([]),
        lambda: power.conjunction(["maybe"]),
        lambda: power.cell_pass_probability(0.0, 0.0, TAU, 2.0),
        lambda: power.cell_pass_probability(float("inf"), 0.1, TAU, 2.0),
        lambda: power.family_power([0.0], [0.1, 0.1], TAU),
        lambda: power.sm3_log_ratio_se(100, 50),
        lambda: power.sm3_log_ratio_se(-1, 50),
        lambda: power.share_difference_se(1.2, 100, 100),
        lambda: power.min_effective_deaths_per_cell(5, delta=TAU),
        lambda: power.min_effective_deaths_per_cell(5, group_share=1.0),
        lambda: power.min_effective_n_per_cell(5, share=0.0),
        lambda: power.bootstrap_replicates_for_mc_error(2.0, -0.1, TAU),
        lambda: power.projection_replicates_for_mc_error(0.0, 0.02),
        lambda: power.InventedStratum(n_clusters=3, group_shares=(0.5, 0.5)),
        lambda: power.InventedStratum(n_clusters=100, group_shares=(0.4, 0.4)),
        lambda: power.InventedStratum(n_clusters=100, group_shares=(1.0,)),
        lambda: power.InventedStratum(
            n_clusters=100, group_shares=(0.5, 0.5), unclassified_share=1.0
        ),
        lambda: power.InventedStratum(
            n_clusters=100, group_shares=(0.5, 0.5), n_design_strata=80
        ),
        lambda: power.InventedStratum(
            n_clusters=100, group_shares=(0.5, 0.5), mean_risk=0.9
        ),
        lambda: power.InventedStratum(
            n_clusters=100,
            group_shares=(0.5, 0.5),
            model_log_rr=(0.1, float("nan")),
        ),
        lambda: power.InventedSharesCell(
            shares=(0.5, 0.5), n_model=100, n_target=100, bias=(0.1, 0.1)
        ),
        lambda: power.InventedSharesCell(
            shares=(0.5, 0.5), n_model=5, n_target=100
        ),
        lambda: power.InventedSharesCell(
            shares=(0.5, 0.5), n_model=100, n_target=100, icc=1.0
        ),
        lambda: power.simulate_sm3_family([], n_sims=1, seed=0),
        lambda: power.cumulative_risk_bound(
            lambda y, s: np.zeros(120), (70, 60), [2012], 1.0
        ),
    ],
)
def test_malformed_inputs_are_refused(call):
    with pytest.raises((ValueError, TypeError)):
        call()


# --------------------------------------------------------------------------
# The committed results the record quotes
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def committed():
    return json.loads(RESULTS.read_text())


def test_committed_analytic_sections_reproduce(committed):
    fresh = power._jsonable(
        {
            "sm3_analytic": power.sm3_analytic_grid(),
            "sm3_power_curve": power.sm3_power_curve(),
            "ed2_analytic": power.ed2_analytic_grid(),
        }
    )
    for key, value in fresh.items():
        assert committed[key] == value, key
    assert committed["invented_data_only"] is True
    assert committed["design_commit"] == power.DESIGN_COMMIT


def test_committed_monte_carlo_respects_conservative_power_bound(committed):
    for point in committed["validation"]:
        mc = point["mc"]
        assert 0 <= mc["pass_rate"] <= 1
        lower = point["normal_power_lower_bound"]
        band = 4 * math.sqrt(max(lower * (1 - lower), 1e-4) / mc["n_sims"])
        assert mc["pass_rate"] >= lower - band
        assert mc["mc_se"] < power.ED2_TOLERANCE / 10
        assert mc["extra"]["mc_95_halfwidth"] < power.ED2_TOLERANCE / 10
        assert mc["extra"]["mc_precision_sufficient"] is True
        assert mc["extra"]["mc_95_lower"] <= mc["pass_rate"]
        assert mc["pass_rate"] <= mc["extra"]["mc_95_upper"]


def test_committed_assumed_grid_contains_no_real_count_input(committed):
    grid = committed["sm3_assumed_count_grid"]
    assert grid["assumed_person_grid"] == list(power.ASSUMED_PERSON_GRID)
    assert grid["assumed_window_death_probabilities"] == list(
        power.ASSUMED_WINDOW_RISKS
    )
    for row in grid["rows"]:
        n = row["persons_per_group_sex_band_cell"]
        risk = row["window_death_probability"]
        deff = row["design_effect"]
        assert row["effective_deaths_per_cell"] == pytest.approx(
            n * risk / deff
        )
        assert (row["condition"] is None) == (
            row["family_power_lower_bound"] >= 0.90
        )
    assert committed["real_structural_power_status"].startswith("open")


def test_shared_denominator_uses_entire_cohort_and_unclassified():
    first = (
        np.array([[10.0, 20.0, 5.0], [10.0, 20.0, 5.0]]),
        np.array([[10.0, 20.0, 5.0], [10.0, 20.0, 5.0]]),
        np.array([0, 0]),
    )
    second = (
        np.array([[20.0, 40.0, 10.0], [20.0, 40.0, 10.0]]),
        np.array([[10.0, 20.0, 5.0], [10.0, 20.0, 5.0]]),
        np.array([0, 0]),
    )
    observed, expected, design = power._join_sm3_strata([first, second])
    ratio = power.log_ratio_estimates(observed, expected)
    np.testing.assert_allclose(ratio[:2], -math.log(1.5))
    np.testing.assert_allclose(ratio[2:], math.log(2 / 1.5))
    assert observed[:, -1].sum() == 30.0
    assert set(design) == {0, 1}


@settings(max_examples=60, deadline=None)
@given(m=st.integers(2, 60), se=st.floats(0.005, 0.2))
def test_union_bound_never_exceeds_independence_power(m, se):
    lower = power.family_power_lower_bound([0.0] * m, [se] * m, TAU)
    independent = power.family_power([0.0] * m, [se] * m, TAU)
    assert 0 <= lower <= independent + 1e-12


def test_full_family_normal_simulations_are_deterministic_and_cover():
    first = power.simulate_sm3_normal_family(5, 3200.0, n_sims=12000, seed=3)
    second = power.simulate_sm3_normal_family(5, 3200.0, n_sims=12000, seed=3)
    ed = power.simulate_ed2_normal_family(
        50000.0, 20000.0, n_sims=12000, seed=9
    )
    assert first == second
    assert first.extra["family_size"] == 20
    assert ed.extra["family_size"] == 100
    for result in (first, ed):
        assert result.coverage >= 0.95 - _mc_band(0.95, 12000)


def test_unestimated_singleton_cluster_precision_is_refused():
    with pytest.raises(ValueError, match="two clusters"):
        power._stratified_cluster_variance(np.zeros((3, 2)), np.arange(3))


def test_projection_mc_noise_prevents_a_pass():
    cell = power.InventedSharesCell(
        shares=(0.5, 0.5),
        n_model=10,
        n_target=5000,
        model_cluster_size=1.0,
        target_cluster_size=1.0,
        icc=0.0,
        weight_cv=0.0,
        replicates=1,
    )
    result = power.simulate_ed2_family(
        [cell], n_sims=10, seed=13, tolerance=1.0
    )
    assert result.extra["max_projection_mc_se"] > 0.1
    assert result.pass_rate == 0.0


@pytest.mark.parametrize("bias", [0.0, power.ED2_TOLERANCE])
def test_ed2_precise_balanced_estimates_have_power_and_coverage(bias):
    """Check a nonsparse design whose intervals can fit inside tolerance."""
    cell = power.InventedSharesCell(
        shares=(0.5, 0.5),
        n_model=20000,
        n_target=20000,
        model_cluster_size=1.0,
        target_cluster_size=1.0,
        icc=0.0,
        weight_cv=0.0,
        replicates=20,
        bias=(bias, -bias),
    )
    se = power.ed2_cell_analytic_ses(cell)[0]
    weight, cluster = np.ones(cell.n_model), np.arange(cell.n_model)
    half = power.ed2_cluster_half_width(weight, cluster, weight, cluster, 2)
    assert half < power.ED2_TOLERANCE
    # The two balanced category differences are exact negatives, so the
    # family conjunction has the same normal approximation as one cell.
    expected = power.cell_pass_probability(
        bias, se, power.ED2_TOLERANCE, half / se
    )
    result = power.simulate_ed2_family([cell], n_sims=100, seed=44)
    assert result.extra["max_projection_mc_se"] < power.ED2_TOLERANCE / 10
    assert abs(result.pass_rate - expected) <= _mc_band(expected, 100)
    nominal_coverage = 1 - power.ALPHA
    assert result.coverage >= nominal_coverage - _mc_band(
        nominal_coverage, 100
    )
    if bias == 0:
        assert result.pass_rate > 0
    else:
        nominal = power.ALPHA / 4
        assert result.pass_rate <= nominal + _mc_band(nominal, 100)


@pytest.mark.parametrize("n, mc_sufficient", [(46875, False), (46876, True)])
def test_sparse_ed2_boundary_needs_nonzero_bounds(n, mc_sufficient):
    """The projection veto and sampling bound are independent requirements."""
    cell = power.InventedSharesCell(
        shares=(1e-12, 0.25, 0.25, 0.25, 0.25 - 1e-12),
        n_model=n,
        n_target=n,
        model_cluster_size=1.0,
        target_cluster_size=1.0,
        icc=0.0,
        weight_cv=0.0,
        replicates=1,
        bias=(0.02, -0.005, -0.005, -0.005, -0.005),
    )
    result = power.simulate_ed2_family([cell], n_sims=1, seed=0)
    assert result.pass_rate == 0.0
    assert (
        result.extra["max_projection_mc_se"] < power.ED2_TOLERANCE / 10
    ) == mc_sufficient


def test_ed2_single_realized_cluster_counts_as_inconclusive():
    cell = power.InventedSharesCell(
        shares=(0.5, 0.5),
        n_model=10,
        n_target=10,
        model_cluster_size=20.0,
        target_cluster_size=20.0,
        icc=0.0,
        weight_cv=0.0,
        replicates=1,
    )
    result = power.simulate_ed2_family([cell], n_sims=1, seed=0)
    assert result.n_sims == 1
    assert result.inconclusive_rate == 1.0
    assert result.extra["unestimable_realizations"] == 1
    with pytest.raises(power.UnestimableRealization, match="two realized"):
        power._share_and_var(np.ones((10, 2)), np.ones(10), np.zeros(10, int))


@pytest.mark.parametrize(
    "call",
    [
        lambda: power.log_ratio_estimates(np.ones((3, 3)), np.ones((3, 2))),
        lambda: power.log_ratio_estimates(-np.ones((3, 3)), np.ones((3, 3))),
        lambda: power.log_ratio_estimates(
            np.full((3, 3), np.inf), np.ones((3, 3))
        ),
        lambda: power.linearized_se(np.ones((3, 3)), np.ones((3, 3)), [0, 1]),
        lambda: power.min_effective_n_per_cell(
            5, share=0.3, n_target_eff=-math.inf
        ),
        lambda: power.InventedSharesCell(
            shares=(0.5, 0.5),
            n_model=100,
            n_target=100,
            weight_cv=float("inf"),
        ),
        lambda: power.simulate_sm3_normal_family(5, 100, n_sims=True, seed=1),
        lambda: power.simulate_ed2_normal_family(-100, 200, n_sims=1, seed=1),
        lambda: power.build_results(1000, 1, anchors=False),
    ],
)
def test_additional_malformed_inputs_are_refused(call):
    with pytest.raises((ValueError, TypeError)):
        call()


def test_imprecise_diagnostics_cannot_claim_power_criterion():
    result = power._summarize([power.PASS] * 40)
    assert result.extra["mc_95_lower"] >= power.POWER_CRITERION
    assert result.extra["mc_precision_sufficient"] is False
    assert result.extra["mc_lower_reaches_power_criterion"] is False
    precise = power._summarize([power.PASS] * 300000)
    assert precise.extra["mc_precision_sufficient"] is True
    assert precise.extra["mc_lower_reaches_power_criterion"] is True


def test_undefined_bootstrap_replicates_stay_inconclusive():
    observed = np.array(
        [[1.0, 2.0, 0.0], [0.0, 2.0, 0.0], [0.0, 2.0, 0.0], [0.0, 2.0, 0.0]]
    )
    expected = np.ones((4, 3))
    se = power.bootstrap_se(
        observed, expected, np.zeros(4), 100, np.random.default_rng(4)
    )
    assert np.isnan(se[0])
    outcome = power.classify_bounds(
        power.log_ratio_estimates(observed, expected),
        power.bonferroni_z(2) * se,
        TAU,
    )
    assert outcome[0] == power.INCONCLUSIVE
