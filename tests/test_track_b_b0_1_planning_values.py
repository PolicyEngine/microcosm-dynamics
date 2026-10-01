"""Invented-data tests for the B0.1 addendum's planning-value script.

No PSID file, committed result cell or boundary ledger is read. The fit uses
an injected stochastic sign gate instead of populace-fit, so these tests run
on CI. They check the script's pieces against the protocol-v2 block in
``docs/design/track_b_b0_1_addendum.md`` and its invariants:

- copying a person c times is the bootstrap's duplication, and every cell
  on the copied frame is computed by the unchanged M6 reducer;
- the signed gap is M6's score before the absolute value;
- the paired arms see identical truth statistics;
- multiplicities are deterministic per replicate and stratum, and each
  stratum's multiplicities sum to its cluster count;
- the written record can hold no level or gap key;
- the loader refuses any collection wave after 2011.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import select_m6_qstar_train_only as selector  # noqa: E402
import track_b_b0_1_planning_values as pv  # noqa: E402

HEAD_CODES = (10,)
SPOUSE_CODES = (20, 22)


def _codes(_wave: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return HEAD_CODES, SPOUSE_CODES


class _StochasticGate:
    """Participation depends on the current level; no populace-fit needed."""

    def draw_sign(self, current_level, target_age, uniforms):
        p_zero = np.where(np.asarray(current_level) > 0, 0.08, 0.55)
        return (np.asarray(uniforms) >= p_zero).astype(np.int64)


class _StochasticFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *, seed: int):
        owner = self

        class Model:
            def fit(self, frame, **kwargs):
                owner.calls += 1
                return _StochasticGate()

        return Model()


def _invented_fields(n_households: int = 160, seed: int = 7):
    """An invented individual file and family labor fields, waves 1993-2011."""
    rng = np.random.default_rng(seed)
    waves = [wave for wave in pv.COLLECTION_WAVES if wave >= 1993]
    people: list[dict] = []
    labor: dict[int, list[dict]] = {wave: [] for wave in waves}
    for household in range(1, n_households + 1):
        size = 1 + int(rng.random() < 0.6)
        last_wave = (
            int(rng.choice(waves[-6:])) if rng.random() < 0.15 else 2011
        )
        births = [int(rng.integers(1942, 1982)) for _ in range(size)]
        levels = [float(rng.normal(10.2, 0.6)) for _ in range(size)]
        for wave in waves:
            if wave > last_wave:
                continue
            interview = wave * 10_000 + household
            row_labor = {"interview": interview}
            for member in range(size):
                person_id = household * 1000 + member + 1
                age = wave - births[member]
                people.append(
                    {
                        "person_id": person_id,
                        "period": wave,
                        "age": age,
                        "sequence": member + 1,
                        "relationship": (HEAD_CODES + SPOUSE_CODES)[member],
                        "weight": float(1.0 + household % 5),
                        "interview": interview,
                    }
                )
                zero = rng.random() < (0.35 if age > 60 else 0.12)
                level = (
                    0.0
                    if zero
                    else float(np.exp(levels[member] + rng.normal(0, 0.45)))
                )
                key = "head_labor" if member == 0 else "spouse_labor"
                row_labor[key] = level
            row_labor.setdefault("spouse_labor", 0.0)
            labor[wave].append(row_labor)
    person_wave = pd.DataFrame(people)
    labor_frames = {wave: pd.DataFrame(rows) for wave, rows in labor.items()}
    return person_wave, labor_frames


@pytest.fixture(scope="module")
def pipeline():
    person_wave, labor = _invented_fields()
    sources = pv.build_sources(person_wave, labor, _codes)
    earnings = sources.earnings
    fit_input = pv.truncate_estimation_frame(
        earnings,
        boundary_year=pv.PSEUDO_ORIGIN,
        year_column="period",
        flow=False,
        label="invented",
    )
    nawi = {
        year: 30_000.0 * 1.03 ** (year - 1990) for year in range(1960, 2007)
    }
    full_anchor = pv.anchor_frame(sources.person_wave, pv.ANCHOR_WAVE)
    factory = _StochasticFactory()
    fitted = pv.fit_law(fit_input, nawi, qrf_factory=factory)
    context = pv.build_context(fitted, earnings, full_anchor)
    draws = pv.project_draws(fitted.generator, context)
    clusters = pv.cluster_table(
        sources.person_wave, fit_input["person_id"].unique(), full_anchor
    )
    return {
        "sources": sources,
        "earnings": earnings,
        "fit_input": fit_input,
        "nawi": nawi,
        "full_anchor": full_anchor,
        "fitted": fitted,
        "context": context,
        "draws": draws,
        "clusters": clusters,
        "factory": factory,
    }


# --------------------------------------------------------------------------
# Geometry and source caps
# --------------------------------------------------------------------------
def test_geometry_is_b2_moved_back_four_years():
    assert pv.PSEUDO_ORIGIN == 2006 and pv.ANCHOR_WAVE == 2007
    assert pv.LEVEL_YEARS == (2008, 2010)
    assert pv.CHANGE_YEARS == (2006, 2008, 2010)
    assert max(pv.COLLECTION_WAVES) == 2011
    assert all(wave - 1 <= 2010 for wave in pv.COLLECTION_WAVES)
    assert pv.K == 20 and pv.DRAW_SEEDS == tuple(range(6200, 6220))
    assert pv.FIT_SEED == 5200


def test_the_sixteen_gateable_cells():
    assert len(pv.CELLS) == 16
    assert set(pv.CELL_METRICS.values()) == {
        "log_ratio",
        "abs_gap_log",
        "abs_gap_corr",
    }
    assert {name.split(".")[0] for name in pv.CELLS} == {
        "earn_p10",
        "earn_p50",
        "earn_p90",
        "earn_zero_rate",
        "earn_dlog_sd",
        "earn_dlog_mean",
        "earn_mob_h1_diag",
        "earn_mob_h2_diag",
        "earn_autocorr_lag1",
        "earn_autocorr_lag2",
    }


def test_build_sources_refuses_a_post_2011_wave():
    person_wave, labor = _invented_fields(n_households=4)
    labor[2013] = labor[2011].copy()
    with pytest.raises(AssertionError, match="after 2011"):
        pv.build_sources(person_wave, labor, _codes)


def test_build_sources_refuses_post_2011_individual_rows():
    person_wave, labor = _invented_fields(n_households=4)
    late = person_wave[person_wave.period == 2011].assign(period=2013)
    with pytest.raises(AssertionError, match="after 2011"):
        pv.build_sources(pd.concat([person_wave, late]), labor, _codes)


def test_sources_are_dated_2010_or_earlier(pipeline):
    assert int(pipeline["earnings"]["period"].max()) == 2010
    assert int(pipeline["fit_input"]["period"].max()) == 2006


# --------------------------------------------------------------------------
# Copying, gaps and multiplicities
# --------------------------------------------------------------------------
@settings(max_examples=60, deadline=None)
@given(
    st.lists(st.integers(min_value=0, max_value=4), min_size=1, max_size=12)
)
def test_copy_persons_is_the_bootstrap_duplication(counts):
    frame = pd.DataFrame(
        {
            "person_id": np.repeat(np.arange(1, len(counts) + 1), 2),
            "period": np.tile([2006, 2008], len(counts)),
            "earnings": np.arange(2 * len(counts), dtype=float),
        }
    )
    mult = {index + 1: count for index, count in enumerate(counts)}
    copied = pv.copy_persons(frame, mult)
    assert len(copied) == 2 * sum(counts)
    assert not copied.duplicated(["person_id", "period"]).any()
    original = copied["person_id"] // pv.ID_SCALE
    copy = copied["person_id"] % pv.ID_SCALE
    for person, count in mult.items():
        assert int((original == person).sum()) == 2 * count
        assert set(copy[original == person]) == set(range(count))
    merged = copied.assign(original=original).merge(
        frame, left_on=["original", "period"], right_on=["person_id", "period"]
    )
    assert np.array_equal(merged["earnings_x"], merged["earnings_y"])


def test_copy_persons_refuses_the_identifier_scale():
    frame = pd.DataFrame({"person_id": [1], "period": [2006]})
    with pytest.raises(AssertionError, match="identifier scale"):
        pv.copy_persons(frame, {1: pv.ID_SCALE})


@settings(max_examples=200, deadline=None)
@given(
    st.sampled_from(sorted(set(pv.CELL_METRICS.values()))),
    st.lists(
        st.floats(min_value=0.01, max_value=5.0), min_size=1, max_size=20
    ),
    st.floats(min_value=0.01, max_value=5.0),
)
def test_signed_gap_is_m6_score_before_absolute_value(metric, draws, truth):
    gap = pv.signed_gap(metric, draws, truth)
    score = selector._score(
        float(np.mean(draws)), {"value": truth, "metric": metric}
    )
    assert gap is not None and score is not None
    assert math.isclose(abs(gap), score, rel_tol=1e-12, abs_tol=1e-15)


def test_signed_gap_is_undefined_where_m6_is():
    assert pv.signed_gap("log_ratio", [1.0, None], 1.0) is None
    assert pv.signed_gap("log_ratio", [1.0], None) is None
    assert pv.signed_gap("log_ratio", [0.0], 1.0) is None
    assert pv.signed_gap("abs_gap_corr", [0.2, 0.4], 0.1) == pytest.approx(0.2)


def test_multiplicities_are_deterministic_and_sum_to_the_stratum(pipeline):
    clusters = pipeline["clusters"]
    for stratum, word in (("anchor", 0), ("other", 1)):
        first = pv.stratum_multiplicities(clusters, stratum, 3, word)
        again = pv.stratum_multiplicities(clusters, stratum, 3, word)
        other = pv.stratum_multiplicities(clusters, stratum, 4, word)
        n = clusters.loc[clusters.stratum == stratum, "cluster"].nunique()
        assert first == again
        assert sum(first.values()) == n
        if n > 1:
            assert first != other


def test_every_full_anchor_person_is_in_the_anchor_stratum(pipeline):
    clusters = pipeline["clusters"].set_index("person_id")
    anchor_ids = pipeline["full_anchor"]["person_id"].astype(int)
    assert (clusters.loc[anchor_ids, "stratum"] == "anchor").all()
    assert set(pipeline["context"].domain_ids) <= set(anchor_ids)


# --------------------------------------------------------------------------
# End-to-end on invented data
# --------------------------------------------------------------------------
def _reference(pipeline):
    truth = pipeline["context"].truth_support
    return {
        name: cell["value"] for name, cell in pv.cell_values(truth).items()
    }


def test_projection_matches_the_truth_support(pipeline):
    truth = pipeline["context"].truth_support
    for frame in pipeline["draws"]:
        assert frame[["person_id", "period"]].equals(
            truth[["person_id", "period"]]
        )


def _arm_f(pipeline, replicate, draws=None):
    return pv.arm_f_replicate(
        replicate,
        pipeline["clusters"],
        pipeline["context"].truth_support,
        pipeline["draws"] if draws is None else draws,
        _reference(pipeline),
    )


def _arm_r(pipeline, replicate):
    return pv.arm_r_replicate(
        replicate,
        pipeline["clusters"],
        pipeline["fit_input"],
        pipeline["earnings"],
        pipeline["full_anchor"],
        pipeline["nawi"],
        pipeline["context"].truth_support,
        pipeline["draws"],
        qrf_factory=_StochasticFactory(),
    )


def test_arm_f_returns_gaps_and_centered_truth_deviations(pipeline):
    result = _arm_f(pipeline, 0)
    assert set(result) == {"replicate", "gaps", "tdev"}
    assert set(result["gaps"]) == set(result["tdev"]) == set(pv.CELLS)
    defined = [name for name in pv.CELLS if result["gaps"][name] is not None]
    assert len(defined) >= 12
    # A deviation is centered on the full sample: over replicates its mean
    # is small next to its spread.
    devs = np.asarray(
        [_arm_f(pipeline, b)["tdev"]["earn_p50.prime"] for b in range(40)]
    )
    assert abs(devs.mean()) < 3 * devs.std(ddof=1) / np.sqrt(len(devs)) + 1e-9


def test_arm_r_pairs_with_arm_f_on_the_same_frame(pipeline, monkeypatch):
    for scheme in ("copies", "half"):
        monkeypatch.setattr(pv, "REFIT_SCHEME", scheme)
        result = _arm_r(pipeline, 0)
        assert set(result) == {
            "replicate",
            "gap_refit",
            "gap_fixed",
            "effect",
            "truth_agreement",
        }
        assert result["truth_agreement"] == {
            "same_definedness": True,
            "within_rtol": True,
        }
        defined = [n for n in pv.CELLS if result["effect"][n] is not None]
        assert len(defined) >= 12
        for name in defined:
            assert set(result["effect"][name]) == {"delta", "w", "wcov"}
            assert result["effect"][name]["w"] >= 0
    # Under copies, arm R's fixed-law gap is arm F's gap for the replicate.
    monkeypatch.setattr(pv, "REFIT_SCHEME", "copies")
    paired = _arm_r(pipeline, 1)["gap_fixed"]
    fixed = _arm_f(pipeline, 1)["gaps"]
    for name in pv.CELLS:
        if fixed[name] is not None:
            assert paired[name] == pytest.approx(fixed[name], rel=1e-9)


def test_replicates_are_deterministic(pipeline):
    assert _arm_f(pipeline, 5) == _arm_f(pipeline, 5)
    assert _arm_f(pipeline, 5) != _arm_f(pipeline, 6)


def test_truth_agreement_flags_disagreement():
    base = {name: 1.0 for name in pv.CELLS}
    assert pv.truth_agreement(base, dict(base)) == {
        "same_definedness": True,
        "within_rtol": True,
    }
    moved = {**base, pv.CELLS[0]: 1.0 + 1e-6}
    assert pv.truth_agreement(base, moved)["within_rtol"] is False
    missing = {**base, pv.CELLS[0]: None}
    assert pv.truth_agreement(base, missing)["same_definedness"] is False


# --------------------------------------------------------------------------
# Resampling schemes
# --------------------------------------------------------------------------
@settings(max_examples=100, deadline=None)
@given(
    st.integers(min_value=1, max_value=60),
    st.integers(min_value=0, max_value=500),
)
def test_half_sample_takes_half_without_replacement(n, replicate):
    ids = np.arange(100, 100 + n)
    chosen = pv.half_sample(ids, replicate, 2)
    assert set(chosen) == set(ids.tolist())
    assert set(chosen.values()) <= {0, 1}
    assert sum(chosen.values()) == n // 2
    assert chosen == pv.half_sample(ids[::-1], replicate, 2)


def test_refit_multiplicities_by_scheme(pipeline, monkeypatch):
    clusters = pipeline["clusters"]
    monkeypatch.setattr(pv, "REFIT_SCHEME", "copies")
    copies = pv.refit_multiplicities(clusters, 3)
    anchor = pv.anchor_multiplicities(clusters, 3)
    anchor_people = clusters.loc[clusters.stratum == "anchor", "person_id"]
    assert all(copies[int(p)] == anchor[int(p)] for p in anchor_people)
    monkeypatch.setattr(pv, "REFIT_SCHEME", "half")
    half = pv.refit_multiplicities(clusters, 3)
    assert set(half.values()) <= {0, 1}
    by_cluster = clusters.assign(m=clusters.person_id.map(half)).groupby(
        ["stratum", "cluster"]
    )["m"]
    assert (by_cluster.nunique() == 1).all()
    kept = by_cluster.first().groupby("stratum").agg(["sum", "size"])
    assert (kept["sum"] == kept["size"] // 2).all()
    monkeypatch.setattr(pv, "REFIT_SCHEME", "other")
    with pytest.raises(ValueError, match="unknown refit scheme"):
        pv.refit_multiplicities(clusters, 3)


def _invented_design(n_strata=12, per_cluster=5):
    rows, person = [], 0
    for stratum in range(1, n_strata + 1):
        n_clusters = 1 if stratum == 1 else 3 if stratum == 2 else 2
        for cluster in range(1, n_clusters + 1):
            for _ in range(per_cluster):
                person += 1
                rows.append(
                    {
                        "person_id": person,
                        "stratum": stratum,
                        "cluster": cluster,
                    }
                )
    return pd.DataFrame(rows)


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=0, max_value=2000))
def test_design_multiplicities_are_rao_wu_within_strata(replicate):
    design = _invented_design()
    mult = pv.design_multiplicities(design, replicate)
    frame = design.assign(m=design.person_id.map(mult))
    per_secu = frame.groupby(["stratum", "cluster"])["m"]
    assert (per_secu.nunique() == 1).all()
    by_stratum = per_secu.first().groupby("stratum").apply(sorted)
    assert by_stratum.loc[1] == [1]
    assert sum(by_stratum.loc[2]) == 3
    for stratum in range(3, 13):
        assert by_stratum.loc[stratum] == [0, 2]
    # Each stratum keeps its cluster count, so its expected total is kept.
    assert (
        per_secu.first().groupby("stratum").sum()
        == design.groupby("stratum")["cluster"].nunique()
    ).all()
    assert pv.design_summary(design) == {
        "strata": 12,
        "strata_with_one_cluster": 1,
        "strata_with_two_clusters": 10,
        "strata_with_three_or_more_clusters": 1,
        "persons": 120,
    }


def test_arm_d_replicate_reuses_the_fixed_paths(pipeline):
    truth = pipeline["context"].truth_support
    persons = np.sort(truth["person_id"].unique())
    design = pd.DataFrame(
        {
            "person_id": persons,
            "stratum": (persons // 1000) % 8 + 1,
            "cluster": (persons // 1000) % 2 + 1,
        }
    )
    result = pv.arm_d_replicate(2, design, truth, pipeline["draws"])
    assert set(result) == {"replicate", "gaps"}
    assert result == pv.arm_d_replicate(2, design, truth, pipeline["draws"])


# --------------------------------------------------------------------------
# The refit effect and its simulation correction
# --------------------------------------------------------------------------
@settings(max_examples=100, deadline=None)
@given(
    st.sampled_from(sorted(set(pv.CELL_METRICS.values()))),
    st.lists(
        st.floats(min_value=0.5, max_value=2.0), min_size=20, max_size=20
    ),
    st.floats(min_value=0.5, max_value=2.0),
)
def test_refit_effect_of_identical_draws_is_zero(metric, draws, scale):
    same = pv.refit_effect(metric, draws, draws)
    assert same["delta"] == pytest.approx(0.0, abs=1e-12)
    assert same["w"] == pytest.approx(0.0, abs=1e-12)
    shifted = pv.refit_effect(metric, [scale * v for v in draws], draws)
    if metric == "log_ratio":
        # A pure rescaling moves delta by ln(scale) and adds no noise.
        assert shifted["delta"] == pytest.approx(math.log(scale), abs=1e-9)
        assert shifted["w"] == pytest.approx(0.0, abs=1e-12)


def test_refit_effect_is_undefined_where_a_draw_is():
    assert pv.refit_effect("log_ratio", [1.0, None], [1.0, 1.0]) is None
    assert pv.refit_effect("log_ratio", [-1.0, -1.0], [1.0, 1.0]) is None
    assert pv.refit_effect("abs_gap_log", [1.0], [1.0]) is None


def _simulated_arms(rng, r, e, n_f=3000, n_r=400, sim=0.05):
    """Invented replicate values with known r and e (se_up = 1)."""
    inflate = 1.0 + 1.0 / pv.K
    truth_sd = 1.0 / math.sqrt(inflate)
    tdev = rng.normal(0, truth_sd, n_f)
    gap = rng.normal(0, r, n_f)
    arm_f = list(zip(gap.tolist(), tdev.tolist(), strict=True))
    arm_r = []
    for _ in range(n_r):
        effect = rng.normal(0, math.sqrt(e))
        draws_f = rng.normal(0, math.sqrt(sim * pv.K), pv.K)
        draws_r = effect + rng.normal(0, math.sqrt(sim * pv.K), pv.K)
        row = pv.refit_effect("abs_gap_log", draws_r, draws_f)
        fixed = rng.normal(0, r)
        arm_r.append(
            {**row, "gap_fixed": fixed, "gap_refit": fixed + row["delta"]}
        )
    return arm_f, arm_r


def test_summary_recovers_known_r_and_e_net_of_simulation_noise():
    rng = np.random.default_rng(11)
    arm_f, arm_r = _simulated_arms(rng, r=0.8, e=0.04)
    design = list(rng.normal(0, 0.8, 500))
    summary = pv.summarize_cell(arm_f, arm_r, design, 1.0, rng)
    assert summary["defined"]
    ratio = summary["shared_anchor_ratio"]
    assert ratio["r"] == pytest.approx(0.8, rel=0.05)
    assert ratio["ci"][0] <= ratio["r"] <= ratio["ci"][1]
    est = summary["estimation_variance"]
    # Uncorrected, Var(delta) would be e + 2 * sim = 0.14.
    assert est["e"] == pytest.approx(0.04, abs=0.015)
    assert est["ci"][0] <= est["e"] <= est["ci"][1] <= est["e_ucl"]
    assert summary["diagnostics"][
        "simulation_share_of_refit_variance"
    ] == pytest.approx(0.10 / 0.14, abs=0.08)
    gap = summary["gap_variance"]
    assert gap["s2"] == pytest.approx(0.64 + 0.04, abs=0.05)
    assert gap["s2_ucl"] >= gap["s2"]
    assert summary["design_ratio"]["d"] == pytest.approx(1.0, abs=0.08)
    assert pv.key_paths(summary) <= pv.CELL_RECORD_PATHS
    pv.assert_record_is_variance_only(summary)


def test_summary_floors_a_negative_estimate_and_applies_transport():
    rng = np.random.default_rng(5)
    arm_f, arm_r = _simulated_arms(rng, r=0.9, e=1e-9, n_r=80)
    summary = pv.summarize_cell(arm_f, arm_r, [], 1.3, rng)
    est = summary["estimation_variance"]
    assert est["e_b2"] == pytest.approx(max(0.0, est["e_ucl"]) * 1.3)
    assert est["e_b2"] >= 0
    assert est["e_ucl_negative"] == (est["e_ucl"] < 0)
    assert "design_ratio" not in summary


def test_summary_needs_nearly_every_replicate_defined():
    rng = np.random.default_rng(0)
    arm_f, arm_r = _simulated_arms(rng, r=0.8, e=0.04, n_f=200, n_r=30)
    holes = [(None, None)] * 3 + arm_f[3:]
    assert pv.summarize_cell(holes, arm_r, [], 1.0, rng)["defined"] is False
    one_hole = [(None, None)] + arm_f[1:]
    assert pv.summarize_cell(one_hole, arm_r, [], 1.0, rng)["defined"]
    missing = [None] + arm_r[1:]
    assert pv.summarize_cell(arm_f, missing, [], 1.0, rng)["defined"] is False


@settings(max_examples=200, deadline=None)
@given(
    st.floats(min_value=-5, max_value=5, allow_nan=False),
    st.floats(min_value=1.0, max_value=3.0),
)
def test_registered_estimation_bound_is_never_negative(e_ucl, factor):
    value = pv.e_for_b2(e_ucl, factor)
    assert value >= 0
    assert value == pytest.approx(max(0.0, e_ucl) * factor)
    # Element 8's standard error never falls below the bootstrap's.
    se_boot, se_up = 0.7, 1.0
    assert math.sqrt(se_boot**2 + value * se_up**2) >= se_boot


@settings(max_examples=200, deadline=None)
@given(
    st.integers(min_value=100, max_value=30_000),
    st.integers(min_value=100, max_value=30_000),
    st.integers(min_value=1_000, max_value=400_000),
    st.integers(min_value=1_000, max_value=400_000),
)
def test_transport_factor_never_scales_down(n_b2, n_origin, p_origin, p_b2):
    factor = pv.transport_factor(n_b2, n_origin, p_origin, p_b2)
    assert factor >= 1.0
    assert factor == pytest.approx(
        max(1.0, (n_b2 / n_origin) * (p_origin / p_b2))
    )


def test_every_cell_has_a_support_key_in_the_frozen_record():
    assert set(pv.CELL_SUPPORT) == set(pv.CELLS)
    b2 = pv.b2_support_counts()
    for group, key in pv.CELL_SUPPORT.values():
        assert b2[group][key] > 0
    assert b2["level_cells"]["prime"] == 10_420
    assert b2["change_pairs"]["pooled_two_step"] == 8_639


def test_support_counts_match_a_direct_count(pipeline):
    truth = pipeline["context"].truth_support
    counts = pv.support_counts(truth)
    level = truth[truth.period.isin(pv.LEVEL_YEARS)]
    assert counts["level_cells"]["prime"] == int(
        (level.cohort == "prime").sum()
    )
    wide = truth.pivot(index="person_id", columns="period", values="cohort")
    origin, first, last = pv.CHANGE_YEARS
    one_step = int(wide[[origin, first]].notna().all(axis=1).sum()) + int(
        wide[[first, last]].notna().all(axis=1).sum()
    )
    assert counts["change_pairs"]["pooled_one_step"] == one_step
    assert counts["change_pairs"]["pooled_two_step"] == int(
        wide[[origin, last]].notna().all(axis=1).sum()
    )
    same = sum(
        int(((wide[a] == "older") & (wide[b] == "older")).sum())
        for a, b in ((origin, first), (first, last))
    )
    assert counts["change_pairs"]["older"] == same


def test_anchor_forward_pairs_equal_the_fit_s_own(pipeline):
    assert pv.anchor_forward_pairs(
        pipeline["earnings"], pv.PSEUDO_ORIGIN
    ) == len(pipeline["fitted"].forward_pairs)


def test_protocol_block_hash_needs_unique_markers():
    text = f"a\n{pv.PROTOCOL_BEGIN}\nbody\n{pv.PROTOCOL_END}\nz"
    digest = pv.protocol_block_sha256(text)
    assert (
        digest
        == pv.hashlib.sha256(
            f"{pv.PROTOCOL_BEGIN}\nbody\n{pv.PROTOCOL_END}".encode()
        ).hexdigest()
    )
    with pytest.raises(AssertionError, match="unique"):
        pv.protocol_block_sha256(text + text)


# --------------------------------------------------------------------------
# The replicate driver
# --------------------------------------------------------------------------
def test_driver_counts_failures_resumes_and_keeps_order(tmp_path):
    identity = {"head": "abc", "protocol_v2_sha256": "def"}
    pv.open_checkpoint(tmp_path, identity)
    results, status = pv.run_replicates(
        "toy", 12, _toy_replicate, {}, 2, tmp_path
    )
    assert [r is None for r in results] == [
        index % 5 == 3 for index in range(12)
    ]
    assert status["failed"] == 2 and status["void"] is True
    assert status["failure_classes"] == ["ValueError"]
    assert status["resumed_from_checkpoint"] == 0
    again, status = pv.run_replicates(
        "toy", 12, _toy_replicate, {}, 2, tmp_path
    )
    assert status["resumed_from_checkpoint"] == 12
    assert again == results
    with pytest.raises(RuntimeError, match="another run"):
        pv.open_checkpoint(tmp_path, {**identity, "head": "zzz"})


def test_driver_keeps_the_completed_prefix_at_the_deadline(tmp_path):
    results, status = pv.run_replicates(
        "slow",
        6,
        _slow_replicate,
        {},
        1,
        tmp_path,
        deadline=pv.time.time() + 20.0,
    )
    assert status["stopped_at_deadline"] is True
    assert status["used"] < 6
    assert len(results) == status["used"]
    assert [r["replicate"] for r in results] == list(range(status["used"]))


def _toy_body(b):
    if b % 5 == 3:
        raise ValueError("invented failure")
    return {"replicate": b, "gaps": {"x": float(b)}}


def _toy_replicate(index):
    return pv._guarded(_toy_body, index)


def _slow_replicate(index):
    pv.time.sleep(0.5 if index < 2 else 30.0)
    return {"replicate": index, "gaps": {"x": float(index)}}


@pytest.mark.parametrize("key", sorted(pv.FORBIDDEN_RECORD_KEYS))
def test_record_guard_refuses_levels_and_gaps(key):
    with pytest.raises(AssertionError, match="forbidden"):
        pv.assert_record_is_variance_only({"cells": {"x": [{key: 1.0}]}})


def test_household_floor_splits_by_household(pipeline):
    floor = pv.household_floor(
        pipeline["full_anchor"], pipeline["context"].truth_support
    )
    assert set(floor) == set(pv.CELLS)
    for record in floor.values():
        assert record["n_defined_seeds"] <= 100
        assert record["realized_sigma"] >= 0


# --------------------------------------------------------------------------
# The forest-free refit is the same law (needs the real populace-fit stack)
# --------------------------------------------------------------------------
def test_skipping_the_forests_leaves_gates_and_projections_identical():
    pytest.importorskip("populace.fit.qrf")
    person_wave, labor = _invented_fields(n_households=90, seed=3)
    sources = pv.build_sources(person_wave, labor, _codes)
    fit_input = pv.truncate_estimation_frame(
        sources.earnings,
        boundary_year=pv.PSEUDO_ORIGIN,
        year_column="period",
        flow=False,
        label="invented",
    )
    nawi = {
        year: 30_000.0 * 1.03 ** (year - 1990) for year in range(1960, 2007)
    }
    full_anchor = pv.anchor_frame(sources.person_wave, pv.ANCHOR_WAVE)
    full = pv.fit_law(fit_input, nawi)
    lean = pv.fit_law(fit_input, nawi, skip_forests=True)
    target_full = full.generator.shared_gate._target_models["earnings_tp2"]
    target_lean = lean.generator.shared_gate._target_models["earnings_tp2"]
    assert target_full.positive is not None
    assert target_lean.positive is None
    assert pv.gate_surfaces(lean) == pv.gate_surfaces(full)
    context = pv.build_context(full, sources.earnings, full_anchor)
    draws_full = pv.project_draws(full.generator, context)
    draws_lean = pv.project_draws(lean.generator, context)
    for a, b in zip(draws_full, draws_lean, strict=True):
        assert np.array_equal(
            a["earnings"].to_numpy(), b["earnings"].to_numpy()
        )
    check = pv.forest_skip_check(full, fit_input, nawi, context, draws_full)
    assert check["gate_states_and_surfaces_equal"] is True


# --------------------------------------------------------------------------
# Checkpoint log, budget, read guard, record shape and metamorphic checks
# --------------------------------------------------------------------------
def test_checkpoint_logs_every_start_and_unlogged_terminations(tmp_path):
    identity = {"head": "abc", "protocol_v2_sha256": "def"}
    first = pv.open_checkpoint(tmp_path, identity)
    assert [e["event"] for e in first["events"]] == ["process_start"]
    # The process died without logging (for example a SIGKILL).
    second = pv.open_checkpoint(tmp_path, identity)
    assert [e["event"] for e in second["events"]] == [
        "process_start",
        "unlogged_termination",
        "process_start",
    ]


def test_arm_r_budget_runs_across_resumes(tmp_path):
    identity = {"head": "abc", "protocol_v2_sha256": "def"}
    manifest = pv.open_checkpoint(tmp_path, identity)
    deadline = pv.arm_r_deadline(tmp_path, manifest)
    resumed = pv.open_checkpoint(tmp_path, identity)
    assert pv.arm_r_deadline(tmp_path, resumed) == deadline
    assert deadline - resumed["arm_r_started_epoch"] == pv.ARM_R_BUDGET_SECONDS


@settings(max_examples=200, deadline=None)
@given(st.integers(min_value=1960, max_value=2030))
def test_psid_read_set_is_waves_through_2011(wave):
    allowed = pv.psid_path_allowed(Path("family") / str(wave) / "FAM.txt")
    assert allowed == (1969 <= wave <= 2011)
    assert pv.psid_path_allowed(Path("ind2023er/IND2023ER.txt"))
    assert not pv.psid_path_allowed(Path("ind2023er/other.txt"))
    assert not pv.psid_path_allowed(Path("README.md"))


def test_read_guard_refuses_a_2013_family_file(tmp_path):
    late = tmp_path / "family" / "2013"
    late.mkdir(parents=True)
    (late / "FAM2013ER.txt").write_text("x", encoding="utf-8")
    early = tmp_path / "family" / "2011"
    early.mkdir(parents=True)
    (early / "FAM2011ER.txt").write_text("x", encoding="utf-8")
    with pv.psid_read_guard(tmp_path):
        assert (early / "FAM2011ER.txt").read_text(encoding="utf-8") == "x"
        with pytest.raises(PermissionError, match="forbids"):
            (late / "FAM2013ER.txt").read_text(encoding="utf-8")
    assert (late / "FAM2013ER.txt").read_text(encoding="utf-8") == "x"


def test_cell_records_hold_only_listed_keys():
    rng = np.random.default_rng(5)
    floor_ok = {
        "n_defined_seeds": 100,
        "min_events_weaker_half": 40,
        "realized_sigma": 2.0,
    }
    arm_f, arm_r = _simulated_arms(rng, r=0.8, e=0.04, n_f=400, n_r=60)
    design = list(rng.normal(0, 0.8, 100))
    args = ("earn_p10.prime", floor_ok, arm_f, arm_r, design, 1.1, False, rng)
    defined = pv.cell_record(*args)
    assert defined["defined"] is True
    assert pv.key_paths(defined) <= pv.CELL_RECORD_PATHS
    pv.assert_record_is_variance_only(defined)
    assert defined["estimation_variance"]["e_b2"] >= 0
    # The floor sigma enters only as a ratio to the bootstrap's truth SD.
    assert defined["diagnostics"][
        "floor_sigma_over_twice_truth_sd"
    ] == pytest.approx(1.0 / (1.0 / math.sqrt(1.05)), rel=0.1)
    ineligible = pv.cell_record(
        "earn_p10.prime",
        {**floor_ok, "n_defined_seeds": 99},
        *args[2:],
    )
    assert ineligible == {
        "metric": "log_ratio",
        "floor_household_eligible": False,
        "defined": False,
        "undefined_reason": "pseudo_origin_floor_ineligible",
    }
    void = pv.cell_record(*args[:6], True, rng)
    assert void["undefined_reason"] == "arm_void"


@pytest.mark.parametrize("scale", [0.5, 3.0])
def test_scaling_projections_moves_gaps_but_no_recorded_value(pipeline, scale):
    """A level shift reaches the gaps but not one recorded ratio."""
    scaled = [
        frame.assign(earnings=frame["earnings"] * scale)
        for frame in pipeline["draws"]
    ]
    plain = [_arm_f(pipeline, b) for b in range(8)]
    moved = [_arm_f(pipeline, b, draws=scaled) for b in range(8)]
    for name in ("earn_p10.prime", "earn_p50.older", "earn_p90.prime"):
        for a, b in zip(plain, moved, strict=True):
            if a["gaps"][name] is not None:
                assert b["gaps"][name] == pytest.approx(
                    a["gaps"][name] + math.log(scale)
                )
    for name in (
        "earn_zero_rate.prime",
        "earn_dlog_sd.older",
        "earn_dlog_mean.prime",
        "earn_mob_h1_diag",
        "earn_autocorr_lag2",
    ):
        for a, b in zip(plain, moved, strict=True):
            if a["gaps"][name] is not None:
                assert b["gaps"][name] == pytest.approx(
                    a["gaps"][name], abs=1e-9
                )
    for name in pv.CELLS:
        sd = [
            np.std(
                [r["gaps"][name] for r in arm if r["gaps"][name] is not None],
                ddof=1,
            )
            for arm in (plain, moved)
        ]
        assert sd[0] == pytest.approx(sd[1], rel=1e-9, abs=1e-12)
        assert [r["tdev"][name] for r in plain] == [
            r["tdev"][name] for r in moved
        ]


def test_monte_carlo_error_and_gap_correlation_are_variance_only():
    rng = np.random.default_rng(2)
    draws = list(np.exp(rng.normal(0, 0.1, 20)))
    log_error = pv.monte_carlo_error("log_ratio", draws)
    assert log_error == pytest.approx(
        np.std(np.log(draws), ddof=1) / math.sqrt(20)
    )
    scaled = pv.monte_carlo_error("log_ratio", [7.0 * v for v in draws])
    assert scaled == pytest.approx(log_error)
    assert pv.monte_carlo_error("log_ratio", [1.0, None]) is None
    assert pv.monte_carlo_error("log_ratio", [1.0, -1.0]) is None
    results = [
        {"gaps": {name: float(rng.normal()) for name in pv.CELLS}}
        for _ in range(50)
    ] + [None]
    record = pv.gap_correlation(results)
    assert record["cells"] == list(pv.CELLS) and record["replicates"] == 50
    matrix = np.asarray(record["matrix"])
    assert matrix.shape == (16, 16)
    assert np.allclose(np.diag(matrix), 1.0)
    assert np.allclose(matrix, matrix.T)
    pv.assert_record_is_variance_only(record)


# --------------------------------------------------------------------------
# The whole run sequence on invented data (needs the real fitting stack)
# --------------------------------------------------------------------------
def test_run_sequence_end_to_end_on_invented_data(tmp_path, monkeypatch):
    """Rehearse ``_run``: full fit, forest-skip check, floor, the three
    arms through the process pool, and record assembly. Only the PSID
    readers and the runtime pin are replaced."""
    pytest.importorskip("populace.fit.qrf")
    person_wave, labor = _invented_fields(n_households=220, seed=21)
    sources = pv.build_sources(person_wave, labor, _codes)
    persons = np.sort(person_wave["person_id"].unique())
    design = pd.DataFrame(
        {
            "person_id": persons,
            "stratum": (persons // 1000) % 20 + 1,
            "cluster": (persons // 1000 // 20) % 2 + 1,
        }
    )
    nawi = {
        year: 30_000.0 * 1.03 ** (year - 1990) for year in range(1960, 2007)
    }
    monkeypatch.setattr(pv, "runtime_record", lambda: {"invented": True})
    monkeypatch.setattr(pv, "load_sources", lambda _dir: sources)
    monkeypatch.setattr(
        pv,
        "source_checks",
        lambda src: {
            "equal": True,
            "anchor_forward_pairs_2010": pv.anchor_forward_pairs(
                src.earnings, pv.B2_BOUNDARY
            ),
        },
    )
    monkeypatch.setattr(pv, "nawi_2006", lambda _dir: (nawi, {"invented": 1}))
    monkeypatch.setattr(pv, "read_design_variables", lambda **_: design)
    monkeypatch.setattr(pv, "B_F", 40)
    monkeypatch.setattr(pv, "B_D", 12)
    monkeypatch.setattr(pv, "B_R_MAX", 4)
    monkeypatch.setattr(pv, "B_R_MIN", 2)
    monkeypatch.setattr(pv, "N_CI_RESAMPLES", 200)
    monkeypatch.setenv("POPULACE_DYNAMICS_PSID_DIR", str(tmp_path / "psid"))
    monkeypatch.setenv("POPULACE_DYNAMICS_PE_US_DIR", str(tmp_path / "pe"))
    (tmp_path / "psid").mkdir()
    (tmp_path / "pe").mkdir()
    checkpoint = tmp_path / "checkpoint"
    manifest = pv.open_checkpoint(
        checkpoint, {"head": "h", "protocol_v2_sha256": "p"}
    )

    class Args:
        workers_f = 2
        workers_r = 2

    record = pv._run(Args, checkpoint, manifest, "h", "p", pv.time.time())
    record["freeze_push"] = {}
    record["checkpoint_events"] = manifest["events"]
    pv.assert_record_shape(record)
    assert set(record) == pv.RECORD_KEYS
    assert set(record["cells"]) == set(pv.CELLS)
    assert record["bootstrap"]["arm_f"]["used"] == 40
    assert record["bootstrap"]["arm_r"]["used"] == 4
    assert record["bootstrap"]["refit_scheme"] == "half"
    assert record["forest_skip_check"]["gate_states_and_surfaces_equal"]
    defined = [c for c in record["cells"].values() if c["defined"]]
    assert defined, "no cell had planning values on the invented panel"
    for cell in defined:
        assert cell["estimation_variance"]["e_b2"] >= 0
        assert cell["gap_variance"]["s2_gate"] >= 0
        assert cell["shared_anchor_ratio"]["r"] > 0
    # The checkpoint holds gap-type values only.
    for path in checkpoint.rglob("replicate-*.json"):
        stored = pv.json.loads(path.read_text(encoding="utf-8"))
        assert set(stored) <= {
            "replicate",
            "gaps",
            "tdev",
            "gap_refit",
            "gap_fixed",
            "effect",
            "truth_agreement",
            "failed",
            "exception_class",
        }


def test_thread_settings_must_be_explicit(monkeypatch):
    for name in pv.THREAD_ENV:
        monkeypatch.setenv(name, "1")
    monkeypatch.delenv("OMP_NUM_THREADS")
    with pytest.raises(RuntimeError, match="OMP_NUM_THREADS"):
        pv.thread_settings()
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    assert pv.thread_settings() == {
        **{name: "1" for name in pv.THREAD_ENV},
        "OMP_NUM_THREADS": "2",
    }


def test_load_sources_requests_no_wave_after_2011(monkeypatch, tmp_path):
    """Spy on the two readers: the loader asks for waves 1969-2011 only."""
    person_wave, labor = _invented_fields(n_households=6)
    requested: dict[str, list[int]] = {"individual": [], "family": []}

    def fake_individual(concepts, *, data_dir, waves):
        requested["individual"] = list(waves)
        assert set(concepts) == {
            "age",
            "sequence",
            "relationship",
            "weight",
            "interview",
        }
        return person_wave

    def fake_family(wave, *, data_dir):
        requested["family"].append(wave)
        return labor.get(wave, labor[2011].iloc[:0])

    monkeypatch.setattr(pv.panels, "ind_person_period", fake_individual)
    monkeypatch.setattr(pv.selector, "_read_family_labor_levels", fake_family)
    monkeypatch.setattr(pv.family, "_relationship_codes", _codes)
    pv.load_sources(tmp_path)
    assert requested["individual"] == list(pv.COLLECTION_WAVES)
    assert requested["family"] == list(pv.COLLECTION_WAVES)
    assert max(requested["individual"]) == 2011
    assert min(requested["individual"]) == 1969
