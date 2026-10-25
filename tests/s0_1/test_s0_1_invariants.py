"""Accounting and supported coverage on invented sparse/clustered samples."""

import math
from dataclasses import asdict

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from .test_s0_1_power import power


def assert_accounted(result, n):
    counts = result.extra["outcome_counts"]
    assert result.n_sims == sum(counts.values()) == n
    for name in (power.PASS, power.FAIL, power.INCONCLUSIVE):
        assert counts[name] >= 0
        assert getattr(result, name + "_rate") == counts[name] / n
    assert math.isclose(
        result.pass_rate + result.fail_rate + result.inconclusive_rate, 1.0
    )


@settings(max_examples=60, deadline=None)
@given(st.lists(st.sampled_from(["pass", "fail", "inconclusive"]), min_size=1))
def test_summary_counts_every_trial_once(outcomes):
    assert_accounted(power._summarize(outcomes), len(outcomes))


@st.composite
def accepted_ed_cells(draw):
    k = draw(st.integers(2, 5))
    raw = draw(st.lists(st.integers(1, 30), min_size=k, max_size=k))
    return power.InventedSharesCell(
        shares=tuple(value / sum(raw) for value in raw),
        n_model=draw(st.integers(10, 150)),
        n_target=draw(st.integers(10, 150)),
        model_cluster_size=draw(st.sampled_from([1.0, 2.0, 20.0])),
        target_cluster_size=draw(st.sampled_from([1.0, 2.0, 20.0])),
        icc=draw(st.sampled_from([0.0, 0.2, 0.9])),
        weight_cv=draw(st.sampled_from([0.0, 0.6, 2.0])),
        replicates=draw(st.integers(1, 5)),
    )


@settings(max_examples=30, deadline=None)
@given(
    cells=st.lists(accepted_ed_cells(), min_size=1, max_size=3),
    n=st.integers(1, 5),
    seed=st.integers(0, 65535),
)
def test_accepted_ed_realizations_never_abort_and_are_deterministic(
    cells, n, seed
):
    first = power.simulate_ed2_family(cells, n_sims=n, seed=seed)
    second = power.simulate_ed2_family(cells, n_sims=n, seed=seed)
    assert first == second
    assert_accounted(first, n)
    assert first.extra["interval_method"] == "household_hoeffding_bonferroni"
    # These small samples cannot establish equivalence. A rare uncovered
    # interval may still fail; the coverage property controls its probability.
    assert first.pass_rate == 0.0


@settings(max_examples=20, deadline=None)
@given(
    clusters=st.integers(4, 30),
    groups=st.integers(2, 5),
    seed=st.integers(0, 65535),
    method=st.sampled_from(["linearized", "bootstrap"]),
    risk=st.sampled_from([0.01, 0.2, 0.5]),
)
def test_accepted_sm3_diagnostics_count_and_refuse_unsupported_precision(
    clusters, groups, seed, method, risk
):
    stratum = power.InventedStratum(
        n_clusters=clusters,
        group_shares=(1 / groups,) * groups,
        n_design_strata=1,
        mean_risk=risk,
    )
    kwargs = dict(n_sims=3, seed=seed, method=method, bootstrap_replicates=3)
    first = power.simulate_sm3_family([stratum], **kwargs)
    assert first == power.simulate_sm3_family([stratum], **kwargs)
    assert_accounted(first, 3)
    assert first.inconclusive_rate == 1.0
    assert first.coverage is None
    assert first.extra["diagnostic_only"] is True


@settings(max_examples=50, deadline=None)
@given(
    nm=st.integers(10, 100),
    nt=st.integers(10, 100),
    pm=st.sampled_from([1e-12, 0.001, 0.02, 0.5, 0.99]),
    pt=st.sampled_from([1e-12, 0.001, 0.02, 0.5, 0.99]),
    alpha=st.sampled_from([0.01, 0.05, 0.2, 0.8]),
    m=st.integers(2, 100),
)
def test_hoeffding_coverage_by_exact_binomial_enumeration(
    nm, nt, pm, pt, alpha, m
):
    """Sum the exact sampling law, including zero counts; no MC allowance."""
    half = power.ed2_cluster_half_width(
        np.ones(nm), np.arange(nm), np.ones(nt), np.arange(nt), m, alpha
    )

    def masses(n, p):
        return np.array(
            [math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(n + 1)]
        )

    error = np.arange(nm + 1)[:, None] / nm - np.arange(nt + 1) / nt
    law = masses(nm, pm)[:, None] * masses(nt, pt)
    missed = law[np.abs(error - (pm - pt)) > half].sum()
    # Bonferroni remains valid for dependent categories and blocks.
    assert m * missed <= alpha + 1e-12
    assert half > 0


@settings(max_examples=10, deadline=None)
@given(groups=st.integers(2, 5), seed=st.integers(0, 65535))
def test_supported_normal_sm3_family_covers_and_counts(groups, seed):
    result = power.simulate_sm3_normal_family(
        groups, 3200, n_sims=4000, seed=seed
    )
    assert_accounted(result, 4000)
    # Known-SE normal coverage is stochastic; allow four MC standard errors.
    assert result.coverage >= 0.95 - 4 * math.sqrt(0.95 * 0.05 / 4000)


def sparse_cell():
    eps = 1e-12
    return power.InventedSharesCell(
        shares=(0.0201, 0.9799 - 3 * eps, eps, eps, eps),
        n_model=100,
        n_target=100,
        model_cluster_size=1.0,
        target_cluster_size=1.0,
        icc=0.0,
        weight_cv=0.0,
        replicates=50,
        bias=(-0.02001, 0.02001, 0.0, 0.0, 0.0),
    )


def test_review_sparse_outside_tolerance_has_coverage_and_no_false_passes():
    result = power.simulate_ed2_family([sparse_cell()], n_sims=1000, seed=0)
    assert_accounted(result, 1000)
    assert result.extra["max_projection_mc_se"] < power.ED2_TOLERANCE / 10
    assert result.pass_rate == 0.0
    assert result.coverage >= 0.95


@pytest.mark.parametrize("blocks", [1, 20])
def test_review_minimized_sparse_family_cannot_pass(blocks):
    cell = sparse_cell()
    eps = 1e-12
    neutral = power.InventedSharesCell(
        **{
            **asdict(cell),
            "shares": (eps, 1 - 4 * eps, eps, eps, eps),
            "bias": None,
        }
    )
    result = power.simulate_ed2_family(
        [cell] + [neutral] * (blocks - 1), n_sims=1, seed=2
    )
    assert result.extra["family_size"] == 5 * blocks
    assert result.inconclusive_rate == result.coverage == 1.0


def test_mixed_singleton_draws_are_counted_without_retry_or_redraw():
    cell = power.InventedSharesCell(
        shares=(0.5, 0.5),
        n_model=10,
        n_target=10,
        model_cluster_size=10,
        target_cluster_size=10,
        icc=0,
        weight_cv=0,
        replicates=1,
    )
    result = power.simulate_ed2_family([cell], n_sims=40, seed=0)
    assert_accounted(result, 40)
    assert 0 < result.extra["unestimable_realizations"] < 40
    assert result.inconclusive_rate == 1.0


def test_sm3_minimized_unsupported_interval_is_diagnostic_only():
    stratum = power.InventedStratum(
        n_clusters=4,
        group_shares=(0.5, 0.5),
        unclassified_share=0,
        mean_cluster_size=1,
        n_design_strata=1,
        mean_risk=0.5,
        weight_cv=0,
        true_log_misfit=(0.1, -0.1),
    )
    result = power.simulate_sm3_family([stratum], n_sims=1, seed=9)
    assert result.extra["diagnostic_coverage"] == 0
    assert result.extra["diagnostic_outcome_counts"][power.PASS] == 1
    assert result.inconclusive_rate == 1.0


@settings(max_examples=20, deadline=None)
@given(
    cv=st.sampled_from([1e155, 1e200, 1e308]),
    seed=st.integers(0, 65535),
    n=st.integers(1, 5),
)
def test_accepted_numeric_endpoints_are_counted_inconclusive(cv, seed, n):
    cell = power.InventedSharesCell(
        shares=(0.5, 0.5), n_model=10, n_target=10, weight_cv=cv
    )
    stratum = power.InventedStratum(
        n_clusters=4,
        group_shares=(0.5, 0.5),
        n_design_strata=1,
        mean_cluster_size=1,
        weight_cv=cv,
    )
    for simulate, inputs in (
        (power.simulate_ed2_family, [cell]),
        (power.simulate_sm3_family, [stratum]),
    ):
        result = simulate(inputs, n_sims=n, seed=seed)
        assert_accounted(result, n)
        assert result.inconclusive_rate == 1.0
        assert result.coverage is None
        assert result == simulate(inputs, n_sims=n, seed=seed)


@pytest.mark.parametrize(
    "fields",
    [
        {"model_cluster_size": 1e20},
        {"shares": (5e-324, 1.0), "icc": 0.9},
        {"icc": 5e-324},
        {"n_model": 10**12},
    ],
)
def test_accepted_unavailable_sampler_precision_is_inconclusive(fields):
    cell = power.InventedSharesCell(
        **{**dict(shares=(0.5, 0.5), n_model=10, n_target=10), **fields}
    )
    result = power.simulate_ed2_family([cell], n_sims=3, seed=0)
    assert_accounted(result, 3)
    assert result.inconclusive_rate == 1.0
    assert result.extra["unestimable_realizations"] == 3
