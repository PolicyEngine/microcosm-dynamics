"""The EPUF gate's algebra: tolerances, intervals, partition and scoring."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.harness import epuf_gate as gate
from populace_dynamics.harness.epuf_cells import cell_ids, transform

bridges = st.floats(-0.5, 0.5, allow_nan=False)
sigmas = st.floats(1e-4, 0.2, allow_nan=False)


def _floor(cell_id="r6.men", **overrides):
    values = dict(
        cell_id=cell_id,
        defined=True,
        min_events=100,
        bridge=0.0,
        t=0.03,
        sigma=0.01,
        epuf_sampling_sd=0.0005,
    )
    values.update(overrides)
    return gate.CellFloor(**values)


def test_constants_are_the_house_values():
    assert gate.K_TOLERANCE == 4.0
    assert gate.CAPS == {"log_ratio": math.log(1.5), "abs_gap": 0.15}
    assert gate.MIN_EVENTS == 20
    assert gate.GATE_SEEDS == tuple(range(20))
    assert gate.N_FLOOR_REPLICATES == 100
    assert gate.OC_PAUSE == 0.90


def test_floor_split_seeds_never_reuse_a_gate_seed():
    seeds = {
        gate.holdout_split_seed(b, j)
        for b in range(gate.N_FLOOR_REPLICATES)
        for j in range(len(gate.GATE_SEEDS))
    }
    assert len(seeds) == gate.N_FLOOR_REPLICATES * len(gate.GATE_SEEDS)
    assert min(seeds) == 1000
    assert not seeds & set(gate.GATE_SEEDS)


def test_tolerance_is_mean_plus_four_sd_of_the_magnitudes():
    replicates = [0.01, -0.02, 0.03, -0.005, 0.0]
    magnitude = np.abs(replicates)
    assert gate.tolerance(replicates) == round(
        magnitude.mean() + 4 * magnitude.std(ddof=1), 3
    )
    assert gate.realized_sigma(replicates) == pytest.approx(
        math.sqrt(np.mean(np.square(replicates)))
    )


def test_pooled_estimate_averages_before_the_log():
    values = [0.02, 0.08]
    assert gate.pooled_estimate("zint.men", values) == pytest.approx(
        math.log(0.05)
    )
    assert gate.pooled_estimate("r6.men", [0.6, 0.8]) == pytest.approx(0.7)
    assert math.isnan(gate.pooled_estimate("r6.men", [0.6, float("nan")]))


def test_floor_replicate_combines_the_common_and_averaging_terms():
    value = gate.floor_replicate(
        "zint.men", 0.06, 0.04, [0.05, 0.07], [0.05, 0.05]
    )
    expected = (math.log(0.06) - math.log(0.04)) / 2 + (
        math.log(0.06) - math.log(0.05)
    )
    assert value == pytest.approx(expected)
    assert gate.floor_replicate(
        "r6.men", 0.7, 0.7, [0.7] * 3, [0.7] * 3
    ) == pytest.approx(0.0)


@settings(max_examples=300, deadline=None)
@given(bridge=bridges, t=st.floats(0.001, 0.2))
def test_interval_contains_zero_and_the_bridge(bridge, t):
    lower, upper = gate.hull(bridge, t)
    assert lower <= min(0.0, bridge) - t + 1e-12
    assert upper >= max(0.0, bridge) + t - 1e-12
    assert lower <= 0.0 <= upper
    assert lower <= bridge <= upper
    # Rounded outward by less than one unit of the third decimal.
    assert min(0.0, bridge) - t - lower < 1e-3
    assert upper - max(0.0, bridge) - t < 1e-3


@settings(max_examples=300, deadline=None)
@given(bridge=bridges, t=st.floats(0.001, 0.2))
def test_interval_never_extends_past_epuf_by_more_than_t(bridge, t):
    lower, upper = gate.hull(bridge, t)
    if bridge >= 0:
        assert lower >= -t - 1e-3
    else:
        assert upper <= t + 1e-3


@settings(max_examples=300, deadline=None)
@given(bridge=bridges, sigma=sigmas)
def test_faithful_pass_probability_is_at_least_its_no_bridge_value(
    bridge, sigma
):
    t = 3.2 * sigma
    with_bridge = gate.faithful_pass_probability(
        bridge, sigma, *gate.hull(bridge, t)
    )
    without = gate.faithful_pass_probability(0.0, sigma, *gate.hull(0.0, t))
    assert 0.0 <= with_bridge <= 1.0
    # A bridge only widens the side facing EPUF. Outward rounding of the
    # interval (at most 1e-3) can move either probability slightly.
    assert with_bridge >= without - 1e-3 / sigma * 0.4


@settings(max_examples=300, deadline=None)
@given(bridge=bridges, sigma=sigmas, k=st.floats(2.5, 5))
def test_a_gated_cell_always_certifies_within_the_cap(bridge, sigma, k):
    cell = _floor(bridge=bridge, t=round(k * sigma, 3), sigma=sigma)
    if gate.demotion_reason(cell) is None:
        lower, upper = gate.hull(cell.bridge, cell.t)
        cap = gate.CAPS["abs_gap"]
        assert max(abs(lower), abs(upper)) <= cap
        assert gate.minimum_detectable_gap(bridge, cell.t, sigma) <= cap


def test_demotion_reasons_fire_in_their_registered_order():
    assert gate.demotion_reason(_floor()) is None
    assert (
        gate.demotion_reason(_floor(defined=False, min_events=0))
        == "undefined_on_some_split"
    )
    assert (
        gate.demotion_reason(_floor(min_events=19, sigma=1.0))
        == "below_20_events"
    )
    assert (
        gate.demotion_reason(_floor(epuf_sampling_sd=0.002))
        == "epuf_sampling_not_negligible"
    )
    assert (
        gate.demotion_reason(_floor(t=0.14, sigma=0.04, bridge=0.5))
        == "noise_exceeds_cap"
    )
    assert (
        gate.demotion_reason(_floor(bridge=-0.12)) == "bridge_exceeds_budget"
    )
    # log-ratio cells use the ln(1.5) cap
    assert gate.demotion_reason(_floor("zint.men", bridge=0.3)) is None
    assert (
        gate.demotion_reason(_floor("zint.men", bridge=0.4))
        == "bridge_exceeds_budget"
    )


def _reasons(**overrides):
    reasons = dict.fromkeys(cell_ids())
    reasons.update(overrides)
    return reasons


def test_ladder_gates_the_cohort_rung_when_all_six_r6_cells_qualify():
    gated, report = gate.adopt_ladder(_reasons())
    assert {c for c in gated if c.startswith("r6")} == {
        f"r6.{sex}.{band}"
        for sex in ("men", "women")
        for band in ("c0", "c1", "c2")
    }
    assert report["r6.men"] == "superseded_by_cohort_rung"
    assert "zint.men" in gated and report["d_anyzero.men"] == (
        "superseded_by_zint"
    )
    assert {"q_atmax.men", "mpers.women", "q_sexratio"} <= set(gated)
    assert report["zint.men.c0"] == "reported_by_cohort"
    assert set(gated) | set(report) == set(cell_ids())
    assert not set(gated) & set(report)


def test_ladder_falls_back_to_sex_level_cells_one_sex_at_a_time():
    gated, report = gate.adopt_ladder(
        _reasons(
            **{
                "r6.men.c2": "bridge_exceeds_budget",
                "r6.women": "noise_exceeds_cap",
                "zint.men": "below_20_events",
                "zint.women": "below_20_events",
                "d_anyzero.women": "bridge_exceeds_budget",
                "q_sexratio": "noise_exceeds_cap",
            }
        )
    )
    assert "r6.men" in gated and "r6.women" not in gated
    assert report["r6.men.c0"] == "cohort_rung_not_adopted"
    assert report["r6.men.c2"] == "bridge_exceeds_budget"
    assert report["r6.women"] == "noise_exceeds_cap"
    assert "d_anyzero.men" in gated
    assert report["zint.men"] == "below_20_events"
    assert report["d_anyzero.women"] == "bridge_exceeds_budget"
    assert "q_sexratio" not in gated


def test_ladder_can_gate_nothing():
    gated, report = gate.adopt_ladder(
        dict.fromkeys(cell_ids(), "bridge_exceeds_budget")
    )
    assert gated == []
    assert set(report) == set(cell_ids())


def _registered():
    return {
        "r6.men": {
            "epuf_value": 0.70,
            "psid_value": 0.66,
            "lower": -0.07,
            "upper": 0.03,
        },
        "zint.women": {
            "epuf_value": 0.065,
            "psid_value": 0.060,
            "lower": -0.2,
            "upper": 0.12,
        },
    }


def _run(r6, zint):
    return {
        seed: {"r6.men": r6, "zint.women": zint} for seed in gate.GATE_SEEDS
    }


def test_score_run_passes_between_epuf_and_the_psid_and_fails_beyond():
    assert gate.score_run(_run(0.66, 0.060), _registered())["pass"]
    assert gate.score_run(_run(0.70, 0.065), _registered())["pass"]
    too_low = gate.score_run(_run(0.60, 0.060), _registered())
    assert not too_low["pass"]
    assert not too_low["cells"]["r6.men"]["pass"]
    assert too_low["cells"]["zint.women"]["pass"]
    overshoot = gate.score_run(_run(0.75, 0.060), _registered())
    assert not overshoot["cells"]["r6.men"]["pass"]


def test_score_run_decomposes_the_gap_into_model_and_source_terms():
    scored = gate.score_run(_run(0.64, 0.060), _registered())
    cell = scored["cells"]["r6.men"]
    assert cell["gap_from_epuf"] == pytest.approx(-0.06)
    assert cell["source_term_psid_minus_epuf"] == pytest.approx(-0.04)
    assert cell["model_term_candidate_minus_psid"] == pytest.approx(-0.02)
    share = scored["cells"]["zint.women"]
    assert share["source_term_psid_minus_epuf"] == pytest.approx(
        transform("zint.women", 0.060) - transform("zint.women", 0.065)
    )


def test_score_run_requires_exactly_the_gate_seeds():
    partial = {seed: {"r6.men": 0.7, "zint.women": 0.06} for seed in range(5)}
    with pytest.raises(ValueError, match="seeds 0-19"):
        gate.score_run(partial, _registered())


def test_a_run_with_no_gated_cells_does_not_pass():
    empty = {seed: {} for seed in gate.GATE_SEEDS}
    assert gate.score_run(empty, {})["pass"] is False


def test_an_undefined_estimate_fails_its_cell():
    scored = gate.score_run(_run(float("nan"), 0.06), _registered())
    assert not scored["cells"]["r6.men"]["pass"]


def test_floor_terms_sum_to_the_replicate():
    args = ("zint.men", 0.06, 0.04, [0.05, 0.07], [0.05, 0.05])
    common, averaging = gate.floor_terms(*args)
    assert common == pytest.approx((math.log(0.06) - math.log(0.04)) / 2)
    assert gate.floor_replicate(*args) == pytest.approx(common + averaging)


def _spearman(x, y):
    from populace_dynamics.harness.epuf_cells import weighted_spearman

    return weighted_spearman(x, y, np.ones(len(x)))


def test_floor_prices_a_faithful_generator():
    """The two-term floor matches a faithful generator's 20-seed spread.

    A population where earnings rank ``y`` depends on an anchor ``x`` with
    correlation 0.6. A faithful generator redraws ``y`` for each 20%
    holdout from the true conditional law. Its 20-seed mean correlation
    differs from the realised sample's by noise the seeds share, which a
    floor built from 20%/80% splits alone cannot see.
    """
    rho, n, n_seeds = 0.6, 1500, 20
    rng = np.random.default_rng(20261002)

    def draw_y(x, generator):
        return rho * x + math.sqrt(1 - rho**2) * generator.normal(size=len(x))

    faithful = []
    two_term, one_term = [], []
    for replication in range(160):
        x = rng.normal(size=n)
        y = draw_y(x, rng)
        real = _spearman(x, y)
        per_seed = []
        for _ in range(n_seeds):
            held = rng.random(n) < gate.HOLDOUT_FRACTION
            per_seed.append(_spearman(x[held], draw_y(x[held], rng)))
        faithful.append(float(np.mean(per_seed)) - real)
        if replication < 60:
            half = rng.random(n) < gate.HALF_FRACTION
            holdouts, complements = [], []
            for _ in range(n_seeds):
                held = rng.random(n) < gate.HOLDOUT_FRACTION
                holdouts.append(_spearman(x[held], y[held]))
                complements.append(_spearman(x[~held], y[~held]))
            common, averaging = gate.floor_terms(
                "r6.men",
                _spearman(x[half], y[half]),
                _spearman(x[~half], y[~half]),
                holdouts,
                complements,
            )
            two_term.append(common + averaging)
            one_term.append(averaging)
    spread = float(np.std(faithful, ddof=1))
    sigma = gate.realized_sigma(two_term)
    naive = gate.realized_sigma(one_term)
    assert 0.75 <= spread / sigma <= 1.25
    assert spread / naive > 1.5
