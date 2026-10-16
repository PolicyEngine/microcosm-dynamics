"""Tests of B2's shared rules (``populace_dynamics.track_b.b2``).

No PSID file and no selection ledger is read. Each rule of the B0.1
addendum's sections 5-8 is pinned by a truth table, its load-bearing
properties by Hypothesis, and every copy of planning or selector code by a
differential test against the original:

- the root-parameterised multiplicities equal the planning functions at
  protocol v2's root for replicates 0-99, and nothing of B2's reads that
  root;
- each household stratum's multiplicities sum to its cluster count, and a
  two-cluster stratum always resamples to [0, 2];
- the bound rule is monotone in the gap, the standard error and the
  tolerance;
- the outcome follows section 8's order: INVALID, FAIL, PASS,
  INCONCLUSIVE;
- the ladder never prunes a family's last cell, stops at the target, keeps
  its guards and matches the ruled-power module's ladder on every order.
"""

from __future__ import annotations

import ast
import hashlib
import itertools
import json
import math
import subprocess
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
import track_b_b0_1_addendum_power as addendum_power  # noqa: E402
import track_b_b0_1_planning_values as pv  # noqa: E402
import track_b_b0_1_ruled_power as ruled  # noqa: E402
import track_b_b2_floor as floor_builder  # noqa: E402
import track_b_b2_score as scorer  # noqa: E402

from populace_dynamics.harness import m6_cells  # noqa: E402
from populace_dynamics.track_b import b2  # noqa: E402

PLANNING = ROOT / "docs" / "design" / "track_b_b0_1_planning_values.json"
PROTOCOL_V2_ROOT = 20260930


@pytest.fixture(scope="module")
def planning():
    return json.loads(PLANNING.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Constants against the addendum and the code they copy
# --------------------------------------------------------------------------
def test_geometry_seeds_and_streams_are_section_7s():
    assert b2.ORIGIN == 2010 and b2.ANCHOR_WAVE == 2011
    assert b2.LEVEL_YEARS == (2012, 2014)
    assert b2.CHANGE_YEARS == (2010, 2012, 2014)
    assert b2.COLLECTION_WAVE_OF == {2010: 2011, 2012: 2013, 2014: 2015}
    assert b2.FIT_SEED == 5200 == selector.FIT_SEED
    assert b2.DRAW_SEEDS == tuple(range(6200, 6220)) == pv.DRAW_SEEDS
    assert b2.K == 20
    assert b2.FLOOR_SEEDS == tuple(range(100)) == m6_cells.FLOOR_SEEDS
    assert b2.GATE_SEEDS == (0, 1, 2, 3, 4) == m6_cells.GATE_SEEDS
    assert b2.ROOT_SEED == 20261002 != pv.BOOTSTRAP_ROOT_SEED
    assert (b2.HOUSEHOLD_WORD, b2.DESIGN_WORD) == (0, 4)
    assert b2.B_HOUSEHOLD == b2.B_DESIGN == 4000
    assert b2.ID_SCALE == pv.ID_SCALE
    assert b2.MAX_UNDEFINED_SHARE == 0.01
    assert b2.MONTE_CARLO_DIVISOR == 10
    assert b2.POWER_TARGET == 0.90 == ruled.POWER_TARGET
    assert b2.MIN_GATED_CELLS == 4 == addendum_power.MIN_GATED_CELLS
    assert b2.ALPHA == ruled.ALPHA


def test_cells_families_and_surfaces_match_their_sources():
    assert b2.CELL_METRICS == pv.CELL_METRICS
    assert b2.CELLS == pv.CELLS
    assert b2.CONCEPT_FAMILY == addendum_power.CONCEPT_FAMILY
    assert b2.LEVEL_CELLS == ruled.LEVEL_CELLS
    assert b2.M6_RETAINED == addendum_power.M6_RETAINED
    assert set(b2.M6_RETAINED) == set(selector.SELECTED_CELLS)
    assert b2.METRIC_CAP == m6_cells.METRIC_CAP
    assert {b2.concept(cell) for cell in b2.LEVEL_CELLS} == {
        "log_quantiles",
        "zero_rate",
    }


def test_gate_surface_is_d1606_option_c1():
    """d1606 ruled option C1: the six level cells less both medians, at the
    registered k = 3. It keeps both of the six's families and exactly the
    four cells the four-cell guard needs."""
    assert b2.GATE_SURFACE == (
        "earn_p90.older",
        "earn_p90.prime",
        "earn_zero_rate.older",
        "earn_zero_rate.prime",
    )
    assert set(b2.GATE_SURFACE) < set(b2.LEVEL_CELLS)
    assert set(b2.LEVEL_CELLS) - set(b2.GATE_SURFACE) == {
        "earn_p50.older",
        "earn_p50.prime",
    }
    assert {b2.concept(cell) for cell in b2.GATE_SURFACE} == {
        b2.concept(cell) for cell in b2.LEVEL_CELLS
    }
    assert len(b2.GATE_SURFACE) == b2.MIN_GATED_CELLS
    assert b2.TOLERANCE_K == 3


@settings(max_examples=200, deadline=None)
@given(
    cleared=st.booleans(),
    retained=st.sets(st.sampled_from(b2.GATE_SURFACE), min_size=1),
    defined=st.dictionaries(st.sampled_from(b2.CELLS), st.booleans()),
    eligible=st.dictionaries(st.sampled_from(b2.CELLS), st.booleans()),
)
def test_the_published_surface_gates_only_gate_surface_cells(
    cleared, retained, defined, eligible
):
    """For any ladder end and any eligibility flags, the floor publishes
    every gateable cell exactly once, gates only cells of the gate surface,
    and reports both medians as outside the rescoped surface."""
    cells = {
        name: {
            "metric": metric,
            "family": b2.concept(name),
            "tolerance": 0.1,
            "plain_units": "invented",
            "exposure_label": b2.exposure_label(name),
            "planning_values_defined": defined.get(name, True),
            "floor_eligible": eligible.get(name, True),
        }
        for name, metric in b2.CELL_METRICS.items()
    }
    record = {
        "outcome": (
            b2.LADDER_CLEARED if cleared else b2.WEAK_POWER_OR_VACUITY
        ),
        "ladder": {
            "retained": sorted(retained),
            "p_gate": 0.95,
            "evaluation": "invented",
        },
        "design": {"design_degrees_of_freedom": 10},
    }
    out = floor_builder.finish(record, cells)
    surface = out["surface"]
    gated = [entry["cell"] for entry in surface["gated"]]
    published = gated + [entry["cell"] for entry in surface["report_only"]]
    assert len(published) == len(set(published)) == len(b2.CELLS)
    assert set(published) == set(b2.CELLS)
    report = {
        entry["cell"]: entry["reason"] for entry in surface["report_only"]
    }
    assert set(gated) <= set(b2.GATE_SURFACE)
    assert gated == (sorted(retained) if cleared else [])
    for name in b2.CELLS:
        if name not in b2.LEVEL_CELLS:
            assert report[name] == "outside the ruled surface (d781 (a))"
        elif name not in b2.GATE_SURFACE:
            assert report[name] == (
                "outside the rescoped surface (d1606 option C1)"
            )
    assert out["candidate_runs_permitted"] is cleared
    assert surface["headline"]["gated_cells"] == len(gated)
    assert sum(surface["headline"]["gated_by_exposure_label"].values()) == (
        len(gated)
    )


def test_exposure_labels_are_section_5s():
    for cell in b2.CELLS:
        expected = (
            b2.EXPOSURE_PUBLISHED_OUTCOMES
            if cell in b2.M6_RETAINED
            else b2.EXPOSURE_FLOOR_DETAIL
        )
        assert b2.exposure_label(cell) == expected
    labels = [b2.exposure_label(cell) for cell in b2.LEVEL_CELLS]
    assert labels.count(b2.EXPOSURE_PUBLISHED_OUTCOMES) == 1
    assert b2.exposure_label("earn_zero_rate.older") == (
        "published candidate-3-law outcomes at boundaries 2008 and 2010"
    )
    assert b2.exposure_label("earn_p50.prime") == (
        "published five-seed floor detail, no published candidate outcome"
    )
    with pytest.raises(KeyError):
        b2.exposure_label("earn_dlog_skew.prime")


# --------------------------------------------------------------------------
# Copies of selector helpers
# --------------------------------------------------------------------------
_json_leaf = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(-(10**9), 10**9),
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(max_size=6),
)
_json_values = st.recursive(
    _json_leaf,
    lambda inner: st.one_of(
        st.lists(inner, max_size=4),
        st.dictionaries(st.text(max_size=5), inner, max_size=4),
    ),
    max_leaves=20,
)


@settings(max_examples=300, deadline=None)
@given(_json_values)
def test_canonical_sha256_is_the_selectors(value):
    assert b2.canonical_sha256(value) == selector._canonical_sha256(value)


def test_canonical_sha256_handles_numpy_scalars_like_the_selectors():
    value = {
        "a": np.float64(0.25),
        "b": np.int64(7),
        "c": np.bool_(True),
        "d": [np.float32(1.5), float("nan")],
        "e": np.arange(3),
    }
    assert b2.canonical_sha256(value) == selector._canonical_sha256(value)
    assert b2.plain(value) == selector._plain(value)


@settings(max_examples=300, deadline=None)
@given(
    st.sampled_from(["log_ratio", "abs_gap_log", "abs_gap_corr"]),
    st.one_of(st.none(), st.floats(allow_nan=True, allow_infinity=True)),
    st.booleans(),
)
def test_cell_value_is_the_selectors(metric, raw, as_rate):
    record = {"metric": metric, ("rate" if as_rate else "value"): raw}
    assert b2.cell_value(record) == selector._selection_cell_value(record)


@settings(max_examples=200, deadline=None)
@given(st.one_of(st.none(), st.integers(0, 120)))
def test_cohort_is_the_selectors(age):
    assert b2.cohort(age) == selector._cohort(age)


@settings(max_examples=100, deadline=None)
@given(st.lists(st.integers(0, 10**9), max_size=30))
def test_id_sha256_is_the_selectors(values):
    assert b2.id_sha256(values) == selector._id_checksum(values)


def _invented_detail(cells):
    return [
        {
            "seed": seed,
            "cells": {
                name: {
                    "score": round(0.01 * (seed + index), 6),
                    "n_events_a": 30 + seed,
                    "n_events_b": 31 + index,
                }
                for index, name in enumerate(cells)
            },
        }
        for seed in b2.GATE_SEEDS
    ]


def test_six_cell_restrictions_keep_only_the_retained_cells():
    every = list(b2.CELLS) + ["earn_dlog_skew.prime", "earn_autocorr_lag5"]
    floor = {name: {"mean": 0.1, "sd": 0.05} for name in every}
    block = b2.six_cell_floor_block(floor)
    assert list(block) == list(b2.M6_RETAINED)
    detail = _invented_detail(every)
    restricted = b2.six_cell_seed_detail(detail)
    assert [entry["seed"] for entry in restricted] == list(b2.GATE_SEEDS)
    for entry, original in zip(restricted, detail, strict=True):
        assert set(entry["cells"]) == set(b2.M6_RETAINED)
        for name in b2.M6_RETAINED:
            assert entry["cells"][name] == original["cells"][name]


# --------------------------------------------------------------------------
# Root-parameterised multiplicities (section 13, "To B2")
# --------------------------------------------------------------------------
def _invented_anchor(n_households=37, seed=3):
    rng = np.random.default_rng(seed)
    rows, person = [], 0
    for household in range(1, n_households + 1):
        for _ in range(int(rng.integers(1, 4))):
            person += 1
            rows.append(
                {
                    "person_id": 1000 * household + person,
                    "household_id": 7 * household + 3,
                    "weight": 1.0 + household % 4,
                }
            )
    return pd.DataFrame(rows)


def _invented_design(two_cluster_strata=9, extra=()):
    rows, person = [], 0
    sizes = [2] * two_cluster_strata + list(extra)
    for stratum, n_clusters in enumerate(sizes, start=1):
        for cluster in range(1, n_clusters + 1):
            for _ in range(3):
                person += 1
                rows.append(
                    {
                        "person_id": person,
                        "stratum": stratum,
                        "cluster": cluster,
                    }
                )
    return pd.DataFrame(rows)


def test_anchor_multiplicities_equal_the_planning_function_at_its_root():
    clusters = b2.household_clusters(_invented_anchor(), anchor_wave=2007)
    for replicate in range(100):
        assert b2.anchor_multiplicities(
            clusters, replicate, root=PROTOCOL_V2_ROOT
        ) == pv.anchor_multiplicities(clusters, replicate)


def test_anchor_multiplicities_equal_on_the_planning_cluster_table():
    """The planning script's own cluster table, both strata present."""
    anchor = _invented_anchor(n_households=20)
    others = pd.DataFrame(
        {
            "person_id": [10**7 + index for index in range(15)],
            "cluster": [2003 * 100_000 + index % 6 for index in range(15)],
            "stratum": "other",
        }
    )
    clusters = pd.concat(
        [b2.household_clusters(anchor, anchor_wave=2007), others],
        ignore_index=True,
    )
    for replicate in range(100):
        assert b2.anchor_multiplicities(
            clusters, replicate, root=PROTOCOL_V2_ROOT
        ) == pv.anchor_multiplicities(clusters, replicate)


def test_design_multiplicities_equal_the_planning_function_at_its_root():
    design = _invented_design()
    for replicate in range(100):
        assert b2.design_multiplicities(
            design, replicate, root=PROTOCOL_V2_ROOT
        ) == pv.design_multiplicities(design, replicate)


def test_b2_root_gives_other_draws_than_protocol_v2s():
    clusters = b2.household_clusters(_invented_anchor())
    design = _invented_design()
    differ_anchor = differ_design = 0
    for replicate in range(20):
        differ_anchor += b2.anchor_multiplicities(
            clusters, replicate, root=b2.ROOT_SEED
        ) != pv.anchor_multiplicities(clusters, replicate)
        differ_design += b2.design_multiplicities(
            design, replicate, root=b2.ROOT_SEED
        ) != pv.design_multiplicities(design, replicate)
    assert differ_anchor == 20 and differ_design >= 15


def test_streams_are_root_b_word():
    for replicate in (0, 1, 3999):
        expected = np.random.default_rng(
            np.random.SeedSequence([b2.ROOT_SEED, replicate, b2.DESIGN_WORD])
        ).random(4)
        got = b2.stream(b2.ROOT_SEED, replicate, b2.DESIGN_WORD).random(4)
        assert np.array_equal(expected, got)


def test_root_is_a_required_keyword():
    clusters = b2.household_clusters(_invented_anchor())
    with pytest.raises(TypeError):
        b2.anchor_multiplicities(clusters, 0)
    with pytest.raises(TypeError):
        b2.design_multiplicities(_invented_design(), 0)


def _names_used(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


@pytest.mark.parametrize(
    "relative",
    [
        "src/populace_dynamics/track_b/b2.py",
        "scripts/track_b_b2_floor.py",
        "scripts/track_b_b2_score.py",
        "scripts/track_b_b2_compare_floor.py",
    ],
)
def test_b2_never_reads_protocol_v2s_root(relative):
    names = _names_used(ROOT / relative)
    assert "BOOTSTRAP_ROOT_SEED" not in names
    assert "_stream" not in names
    for pinned in (
        "anchor_multiplicities",
        "design_multiplicities",
        "stratum_multiplicities",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert f"planning.{pinned}" not in source
        assert f"pv.{pinned}" not in source


def test_moving_protocol_v2s_root_changes_nothing_of_b2s(monkeypatch):
    clusters = b2.household_clusters(_invented_anchor())
    design = _invented_design()
    before = [
        (
            b2.anchor_multiplicities(clusters, b, root=b2.ROOT_SEED),
            b2.design_multiplicities(design, b, root=b2.ROOT_SEED),
        )
        for b in range(5)
    ]
    monkeypatch.setattr(pv, "BOOTSTRAP_ROOT_SEED", 12345)
    after = [
        (
            b2.anchor_multiplicities(clusters, b, root=b2.ROOT_SEED),
            b2.design_multiplicities(design, b, root=b2.ROOT_SEED),
        )
        for b in range(5)
    ]
    assert before == after


@settings(max_examples=60, deadline=None)
@given(
    st.integers(min_value=1, max_value=40),
    st.integers(min_value=0, max_value=10_000),
    st.integers(min_value=0, max_value=2**31),
)
def test_household_multiplicities_total_the_household_count(
    n_households, replicate, root
):
    anchor = _invented_anchor(n_households=n_households, seed=n_households)
    clusters = b2.household_clusters(anchor)
    by_cluster = b2.stratum_multiplicities(
        clusters, "anchor", replicate, b2.HOUSEHOLD_WORD, root=root
    )
    assert sum(by_cluster.values()) == n_households
    assert set(by_cluster) == set(clusters["cluster"])
    persons = b2.anchor_multiplicities(clusters, replicate, root=root)
    assert set(persons) == set(anchor["person_id"])
    # Every person in a household shares its multiplicity.
    shared = anchor.assign(m=anchor["person_id"].map(persons)).groupby(
        "household_id"
    )["m"]
    assert (shared.nunique() == 1).all()
    assert persons == b2.anchor_multiplicities(clusters, replicate, root=root)


@settings(max_examples=60, deadline=None)
@given(
    st.integers(min_value=1, max_value=12),
    st.lists(st.integers(1, 5), max_size=3),
    st.integers(min_value=0, max_value=10_000),
)
def test_design_multiplicities_keep_each_stratums_cluster_count(
    two_cluster, extra, replicate
):
    design = _invented_design(two_cluster, tuple(extra))
    mult = b2.design_multiplicities(design, replicate, root=b2.ROOT_SEED)
    merged, _ = b2.merge_design_strata(design)
    scale = b2.design_summary(design)["scale_l"]
    frame = merged.assign(m=merged["person_id"].map(mult))
    per_secu = frame.groupby(["stratum", "cluster"])["m"]
    assert (per_secu.nunique() == 1).all()
    totals = per_secu.first().groupby("stratum").sum()
    sizes = merged.groupby("stratum")["cluster"].nunique()
    assert (totals == scale * sizes).all()
    for stratum in sizes.index[sizes == 2]:
        assert sorted(per_secu.first().loc[stratum]) == [0, 2 * scale]
    assert mult == b2.design_multiplicities(
        design, replicate, root=b2.ROOT_SEED
    )


# --------------------------------------------------------------------------
# Stratum census, merges and nu (section 7)
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "extra, merged_sizes",
    [
        ((), [2] * 5),
        ((1,), [2] * 4 + [3]),
        ((3,), [2] * 5 + [3]),
        ((4, 1), [2] * 5 + [5]),
    ],
)
def test_summary_records_the_merged_cluster_counts(extra, merged_sizes):
    design = _invented_design(5, extra)
    summary = b2.design_summary(design)
    merged, merges = b2.merge_design_strata(design)
    assert summary["merges"] == merges
    assert summary["before_merges"] == b2.stratum_census(design)
    assert summary["after_merges"] == b2.stratum_census(merged)
    assert sorted(merged.groupby("stratum")["cluster"].nunique()) == (
        sorted(merged_sizes)
    )


def test_census_extends_the_planning_design_summary():
    design = _invented_design(6, (1, 3, 5))
    census = b2.stratum_census(design)
    summary = pv.design_summary(design)
    assert {key: census[key] for key in summary} == summary
    assert census["strata_by_cluster_count"] == {
        "1": 1,
        "2": 6,
        "3": 1,
        "5": 1,
    }
    assert census["clusters"] == 1 + 12 + 3 + 5
    assert census["design_degrees_of_freedom"] == 0 + 6 + 2 + 4


def test_nu_equals_the_ruled_power_count_on_two_cluster_designs(planning):
    design = _invented_design(63)
    census = b2.stratum_census(design)
    assert census["design_degrees_of_freedom"] == 63
    assert census["design_degrees_of_freedom"] == (
        ruled.design_degrees_of_freedom(pv.design_summary(design))
    )
    assert ruled.design_degrees_of_freedom(planning["counts"]["design"]) == 63


@settings(max_examples=100, deadline=None)
@given(st.lists(st.integers(1, 6), min_size=1, max_size=20))
def test_nu_is_clusters_minus_strata(sizes):
    design = _invented_design(0, tuple(sizes))
    census = b2.stratum_census(design)
    assert census["design_degrees_of_freedom"] == sum(sizes) - len(sizes)
    assert census["strata"] == len(sizes)
    assert sum(
        int(n) * count
        for n, count in census["strata_by_cluster_count"].items()
    ) == sum(sizes)


def test_census_refuses_an_empty_or_repeating_design():
    with pytest.raises(ValueError, match="empty"):
        b2.stratum_census(_invented_design(0))
    design = _invented_design(2)
    with pytest.raises(ValueError, match="repeats"):
        b2.stratum_census(pd.concat([design, design.iloc[:1]]))


# --------------------------------------------------------------------------
# t*, the registered standard error and the bound rule (section 7)
# --------------------------------------------------------------------------
def test_t_star_is_section_7s_value():
    assert b2.t_star(6, 63) == pytest.approx(2.724, abs=5e-4)
    assert b2.t_star(6, None) == pytest.approx(2.638, abs=5e-4)
    assert b2.t_star(6, math.inf) == b2.t_star(6, None)
    for bad in (0, -1, 2.5):
        with pytest.raises(ValueError):
            b2.t_star(bad, 63)
    with pytest.raises(ValueError):
        b2.t_star(4, 0)


@settings(max_examples=200, deadline=None)
@given(
    st.integers(min_value=1, max_value=16),
    st.one_of(st.none(), st.integers(min_value=1, max_value=500)),
)
def test_t_star_is_the_ruled_power_modules(m, nu):
    assert b2.t_star(m, nu) == pytest.approx(ruled.t_star(m, nu), abs=1e-12)


@settings(max_examples=200, deadline=None)
@given(
    st.integers(min_value=1, max_value=15),
    st.integers(min_value=1, max_value=300),
)
def test_t_star_rises_with_m_and_falls_with_nu(m, nu):
    assert b2.t_star(m + 1, nu) > b2.t_star(m, nu)
    assert b2.t_star(m, nu + 1) < b2.t_star(m, nu)
    assert b2.t_star(m, nu) > b2.t_star(m, None)


def test_registered_estimation_ratio_is_e_b2_plus_a_resolved_cross_term(
    planning,
):
    for name in b2.CELLS:
        cell = planning["cells"][name]
        assert cell["gap_variance"]["cross_term_resolved_positive"] is False
        assert b2.registered_estimation_ratio(cell) == (
            cell["estimation_variance"]["e_b2"]
        )
    cell = json.loads(json.dumps(planning["cells"]["earn_p50.older"]))
    cell["gap_variance"]["cross_term_resolved_positive"] = True
    cell["diagnostics"]["cross_term"] = 0.2
    cell["estimation_variance"]["transport_factor"] = 1.5
    assert b2.registered_estimation_ratio(cell) == pytest.approx(
        cell["estimation_variance"]["e_b2"] + 0.3
    )
    with pytest.raises(ValueError, match="no planning values"):
        b2.registered_estimation_ratio({"defined": False})


@settings(max_examples=300, deadline=None)
@given(
    st.floats(min_value=0, max_value=10),
    st.floats(min_value=0, max_value=5),
    st.floats(min_value=0, max_value=10),
)
def test_registered_se_is_at_least_se_boot(se_boot, a_c, se_up):
    se = b2.registered_se(se_boot, a_c, se_up)
    assert se == pytest.approx(math.sqrt(se_boot**2 + a_c * se_up**2))
    assert se >= se_boot
    assert b2.registered_se(se_boot, a_c + 1.0, se_up) >= se
    assert b2.registered_se(se_boot, a_c, se_up + 1.0) >= se


def test_registered_se_truth_table():
    assert b2.registered_se(0.3, 0.0, 0.5) == pytest.approx(0.3)
    assert b2.registered_se(0.3, 1.0, 0.4) == pytest.approx(0.5)
    assert b2.registered_se(None, 1.0, 0.4) is None
    assert b2.registered_se(0.3, 1.0, None) is None
    assert b2.registered_se(math.nan, 1.0, 0.4) is None
    with pytest.raises(ValueError):
        b2.registered_se(0.3, -0.1, 0.4)


_gap = st.floats(min_value=-1, max_value=1)
_se = st.floats(min_value=0, max_value=0.5)
_tol = st.floats(min_value=0.001, max_value=1)
_crit = st.floats(min_value=1.0, max_value=4.0)


@settings(max_examples=400, deadline=None)
@given(_gap, _gap, _se, _se, _tol, _tol, _crit)
def test_the_bound_rule_is_monotone(g1, g2, s1, s2, t1, t2, crit):
    """Passing survives a smaller |gap|, a smaller se and a wider tol."""
    small_g, big_g = sorted((abs(g1), abs(g2)))
    small_s, big_s = sorted((s1, s2))
    small_t, big_t = sorted((t1, t2))
    if b2.bound_passes(big_g, big_s, small_t, crit):
        assert b2.bound_passes(small_g, big_s, small_t, crit)
        assert b2.bound_passes(big_g, small_s, small_t, crit)
        assert b2.bound_passes(big_g, big_s, big_t, crit)
        assert b2.bound_passes(-big_g, big_s, small_t, crit)


@settings(max_examples=300, deadline=None)
@given(_gap, _se, _tol, _crit)
def test_the_bound_is_gap_plus_t_star_se(gap, se, tol, crit):
    value = b2.bound_value(gap, se, crit)
    assert value == pytest.approx(abs(gap) + crit * se)
    assert b2.bound_passes(gap, se, tol, crit) == (value <= tol)
    assert value >= abs(gap)


def test_bound_truth_table():
    assert b2.bound_passes(0.1, 0.05, 0.2, 2.0) is True  # 0.2 <= 0.2
    assert b2.bound_passes(0.1, 0.0501, 0.2, 2.0) is False
    assert b2.bound_passes(-0.1, 0.05, 0.2, 2.0) is True
    assert b2.bound_passes(None, 0.05, 0.2, 2.0) is False
    assert b2.bound_passes(0.1, None, 0.2, 2.0) is False
    assert b2.bound_passes(math.nan, 0.05, 0.2, 2.0) is False


def test_monte_carlo_and_undefined_rules():
    assert b2.monte_carlo_passes(0.0199, 0.2) is True
    assert b2.monte_carlo_passes(0.02, 0.2) is False  # must be below
    assert b2.monte_carlo_passes(None, 0.2) is False
    assert b2.monte_carlo_passes(math.inf, 0.2) is False
    assert b2.undefined_share_ok(40, 4000) is True
    assert b2.undefined_share_ok(41, 4000) is False
    assert b2.undefined_share_ok(0, 0) is False


def test_se_upper_is_the_inflated_truth_sd():
    rng = np.random.default_rng(4)
    deviations = list(rng.normal(0, 0.3, 500))
    record = b2.se_upper(deviations + [None] * 5)
    assert record["se_up"] == pytest.approx(
        np.std(deviations, ddof=1) * math.sqrt(1.05)
    )
    assert record["undefined"] == 5 and record["replicates"] == 505
    assert record["undefined_share_ok"] is True
    assert b2.se_upper([0.1] * 5)["se_up"] is None
    assert b2.se_upper([0.1, None])["se_up"] is None
    assert b2.se_upper([0.1] * 90 + [None] * 2)["undefined_share_ok"] is False


@settings(max_examples=200, deadline=None)
@given(
    st.floats(min_value=-1, max_value=1),
    st.floats(min_value=0.001, max_value=1),
    st.integers(min_value=1, max_value=200),
)
def test_report_interval_is_the_unadjusted_t_interval(gap, se, nu):
    low, high = b2.report_interval(gap, se, nu)
    assert (low + high) / 2 == pytest.approx(gap)
    assert (high - low) / 2 == pytest.approx(b2.t_star(1, nu) * se)
    assert b2.t_star(1, nu) == pytest.approx(
        float(ruled.student_t.ppf(0.975, nu))
    )
    assert b2.report_interval(None, se, nu) is None


# --------------------------------------------------------------------------
# Validity and the pass conjunction (section 8)
# --------------------------------------------------------------------------
def test_validity_truth_table():
    assert b2.frame_valid(1.0, [1.0, 1.1]) is True
    assert b2.frame_valid(1.0, [1.0, 1.0]) is False  # not regenerated
    assert b2.frame_valid(1.0, [1.0, None]) is False
    assert b2.frame_valid(None, [1.0, 1.1]) is False
    assert b2.frame_valid(1.0, []) is False
    assert b2.frame_valid(1.0, [math.nan, 1.0]) is False


def _cell(name="earn_p50.older", **changes):
    base = {
        "name": name,
        "tolerance": 0.10,
        "full_valid": True,
        "full_gap": 0.01,
        "side_a_valid": (True,) * 5,
        "side_a_gap": (0.02,) * 5,
        "se": 0.02,
        "mc_error": 0.005,
        "design_undefined": 0,
        "design_replicates": 4000,
        "household_undefined": 0,
        "household_replicates": 4000,
    }
    base.update(changes)
    return b2.GatedCell(**base)


CRIT = 2.724


def test_pass_needs_every_condition():
    result = b2.gate_outcome([_cell(), _cell("earn_p90.prime")], CRIT)
    assert result["outcome"] == b2.PASS
    assert result["n_seeds_passed"] == 5


@pytest.mark.parametrize(
    "changes, outcome",
    [
        ({"full_valid": False}, b2.INVALID),
        ({"side_a_valid": (True, True, True, True, False)}, b2.INVALID),
        ({"full_gap": 0.11}, b2.FAIL),
        ({"full_gap": -0.11}, b2.FAIL),
        ({"side_a_gap": (0.2, 0.2, 0.0, 0.0, 0.0)}, b2.FAIL),
        ({"side_a_gap": (0.2, 0.0, 0.0, 0.0, 0.0)}, b2.PASS),
        ({"side_a_gap": (0.1, 0.1, 0.1, 0.1, 0.1)}, b2.PASS),  # within
        ({"se": 0.04}, b2.INCONCLUSIVE),  # 0.01 + 2.724 * 0.04 > 0.1
        ({"se": None}, b2.INCONCLUSIVE),
        ({"mc_error": None}, b2.INCONCLUSIVE),
        ({"mc_error": 0.01}, b2.INCONCLUSIVE),  # not below tol / 10
        ({"design_undefined": 41}, b2.INCONCLUSIVE),
        ({"design_undefined": 40}, b2.PASS),
        ({"household_undefined": 41}, b2.INCONCLUSIVE),
        ({"full_gap": 0.1, "se": 0.0}, b2.PASS),
    ],
)
def test_outcome_truth_table(changes, outcome):
    result = b2.gate_outcome([_cell(**changes), _cell("earn_p90.prime")], CRIT)
    assert result["outcome"] == outcome


def test_invalid_comes_before_fail_and_fail_before_inconclusive():
    both = _cell(full_valid=False, side_a_gap=(0.5,) * 5)
    assert b2.gate_outcome([both], CRIT)["outcome"] == b2.INVALID
    fail_and_wide = _cell(full_gap=0.2, se=None)
    assert b2.gate_outcome([fail_and_wide], CRIT)["outcome"] == b2.FAIL
    # A seed fails because another cell's side A is outside tolerance.
    other = _cell("earn_p90.prime", side_a_gap=(0.3, 0.3, 0.0, 0.0, 0.0))
    assert b2.gate_outcome([_cell(), other], CRIT)["outcome"] == b2.FAIL


def test_outcome_refuses_malformed_gates():
    with pytest.raises(ValueError):
        b2.gate_outcome([], CRIT)
    with pytest.raises(ValueError, match="repeated"):
        b2.gate_outcome([_cell(), _cell()], CRIT)
    with pytest.raises(ValueError, match="side A"):
        b2.gate_outcome([_cell(side_a_gap=(0.0,) * 4)], CRIT)
    with pytest.raises(ValueError, match="no gap"):
        b2.gate_outcome([_cell(full_gap=None)], CRIT)
    with pytest.raises(ValueError, match="tolerance"):
        b2.gate_outcome([_cell(tolerance=0.0)], CRIT)


_maybe_gap = st.one_of(st.none(), st.floats(min_value=-0.3, max_value=0.3))


@st.composite
def _gated_cells(draw):
    n = draw(st.integers(min_value=1, max_value=6))
    cells = []
    for index in range(n):
        full_valid = draw(st.booleans())
        side_valid = tuple(draw(st.booleans()) for _ in range(5))
        cells.append(
            _cell(
                f"cell{index}",
                tolerance=draw(st.floats(min_value=0.01, max_value=0.3)),
                full_valid=full_valid,
                full_gap=draw(st.floats(min_value=-0.3, max_value=0.3)),
                side_a_valid=side_valid,
                side_a_gap=tuple(
                    draw(st.floats(min_value=-0.3, max_value=0.3))
                    for _ in range(5)
                ),
                se=draw(st.one_of(st.none(), st.floats(0, 0.2))),
                mc_error=draw(st.one_of(st.none(), st.floats(0, 0.05))),
                design_undefined=draw(st.integers(0, 60)),
                household_undefined=draw(st.integers(0, 60)),
            )
        )
    return cells


@settings(max_examples=400, deadline=None)
@given(_gated_cells(), st.floats(min_value=1.0, max_value=4.0))
def test_outcome_properties(cells, critical):
    result = b2.gate_outcome(cells, critical)
    outcome = result["outcome"]
    assert outcome in b2.OUTCOMES
    any_invalid = any(
        not c.full_valid or not all(c.side_a_valid) for c in cells
    )
    assert (outcome == b2.INVALID) == any_invalid
    if outcome == b2.PASS:
        for c in cells:
            assert abs(c.full_gap) <= c.tolerance
            assert abs(c.full_gap) + critical * c.se <= c.tolerance
            assert c.mc_error < c.tolerance / 10
        assert result["n_seeds_passed"] >= 4
    if outcome == b2.INCONCLUSIVE:
        assert all(abs(c.full_gap) <= c.tolerance for c in cells)
        assert result["n_seeds_passed"] >= 4
    # A wider critical value can only move PASS to INCONCLUSIVE.
    wider = b2.gate_outcome(cells, critical + 1.0)["outcome"]
    if outcome != b2.PASS:
        assert wider == outcome
    else:
        assert wider in (b2.PASS, b2.INCONCLUSIVE)
    assert (
        b2.gate_outcome(list(reversed(cells)), critical)["outcome"] == outcome
    )


# --------------------------------------------------------------------------
# Tolerances, plain units and eligibility (sections 5 and 6)
# --------------------------------------------------------------------------
@settings(max_examples=300, deadline=None)
@given(
    st.floats(min_value=0, max_value=0.3),
    st.floats(min_value=0, max_value=0.2),
    st.sampled_from(["log_ratio", "abs_gap_log", "abs_gap_corr"]),
)
def test_tolerance_is_m6s_capped_k3_rule(mean, sd, metric):
    record = b2.tolerance(mean, sd, metric)
    uncapped = m6_cells._tol(mean, sd, 3)
    cap = m6_cells.METRIC_CAP[metric]
    assert record["uncapped"] == uncapped
    assert record["tolerance"] == min(uncapped, cap)
    assert record["at_cap"] == (uncapped >= cap)
    assert record["tolerance"] <= cap


def test_tolerance_rounds_half_even_at_three_places():
    assert b2.tolerance(0.0105, 0.0, "log_ratio")["tolerance"] == 0.010
    assert b2.tolerance(0.0115, 0.0, "log_ratio")["tolerance"] == 0.012
    assert b2.tolerance(0.1, 0.05, "abs_gap_corr")["tolerance"] == 0.15
    assert b2.tolerance(0.1, 0.05, "abs_gap_corr")["at_cap"] is True
    capped = b2.tolerance(0.3, 0.1, "log_ratio")
    assert capped["tolerance"] == math.log(1.5) and capped["at_cap"]


def test_plain_units_are_section_6s():
    assert b2.plain_units("log_ratio", 0.1) == (
        "within a factor of e^0.1 = 1.1052, that is within 10.5% above "
        "or 9.5% below"
    )
    assert b2.plain_units("abs_gap_log", 0.042) == (
        "mean two-year log change within ±0.042"
    )
    assert b2.plain_units("abs_gap_corr", 0.15) == ("correlation within ±0.15")
    with pytest.raises(ValueError):
        b2.plain_units("report_only_shape", 0.1)


@pytest.mark.parametrize(
    "n_defined, events, sigma, eligible",
    [
        (100, 20, 0.1, True),
        (100, 19, 0.1, False),
        (99, 40, 0.1, False),
        # Section 5 lists no sigma condition: a zero sigma is eligible and
        # then stops B2 as an uninformative tolerance (the floor builder).
        (100, 40, 0.0, True),
    ],
)
def test_floor_eligibility_truth_table(n_defined, events, sigma, eligible):
    record = {
        "n_defined_seeds": n_defined,
        "min_events_weaker_half": events,
        "realized_sigma": sigma,
    }
    assert b2.floor_eligible(record) is eligible
    assert b2.floor_eligible(record, n_seeds=99) is (
        n_defined == 99 and events >= 20
    )


@settings(max_examples=300, deadline=None)
@given(
    st.integers(min_value=90, max_value=100),
    st.integers(min_value=0, max_value=40),
    st.floats(min_value=0, max_value=1),
)
def test_floor_eligibility_is_the_planning_rule_without_sigma(
    n_defined, events, sigma
):
    """Differential: B2's rule is the planning script's ``floor_eligible``
    less its positive-sigma condition, which section 5 does not list."""
    record = {
        "n_defined_seeds": n_defined,
        "min_events_weaker_half": events,
        "realized_sigma": sigma,
    }
    assert (b2.floor_eligible(record) and sigma > 0) == pv.floor_eligible(
        record
    )
    assert b2.floor_eligible(record) == (n_defined == 100 and events >= 20)


# --------------------------------------------------------------------------
# The ladder (section 5, d1342)
# --------------------------------------------------------------------------
def _ladder_cells(ratios, capped=()):
    return [
        b2.LadderCell(name, ratio, 1.0, name in capped)
        for name, ratio in ratios.items()
    ]


def _table_power(table, default=0.0):
    calls = []

    def power(names):
        calls.append(tuple(names))
        return table.get(tuple(sorted(names)), default)

    return power, calls


SIX = b2.LEVEL_CELLS


def test_ladder_stops_at_exactly_the_target():
    """Section 5, step 3: stop when the power is at least 0.90."""
    power, calls = _table_power({tuple(sorted(SIX)): 0.90})
    result = b2.ladder(_ladder_cells(dict.fromkeys(SIX, 2.5)), power)
    assert result["outcome"] == b2.LADDER_CLEARED
    assert result["log"] == [] and calls == [tuple(sorted(SIX))]
    power, _ = _table_power({tuple(sorted(SIX)): 0.8999999})
    below = b2.ladder(_ladder_cells(dict.fromkeys(SIX, 2.5)), power)
    assert below["log"] and below["outcome"] == b2.WEAK_POWER_OR_VACUITY


def test_ladder_stops_at_once_when_the_six_clear():
    power, calls = _table_power({tuple(sorted(SIX)): 0.95})
    result = b2.ladder(_ladder_cells(dict.fromkeys(SIX, 2.5)), power)
    assert result["outcome"] == b2.LADDER_CLEARED
    assert result["retained"] == sorted(SIX) and result["log"] == []
    assert calls == [tuple(sorted(SIX))]


def test_ladder_prunes_in_descending_ratio_and_stops_at_the_target():
    ratios = {
        "earn_p50.older": 2.9,
        "earn_p50.prime": 2.8,
        "earn_p90.older": 2.5,
        "earn_p90.prime": 2.4,
        "earn_zero_rate.older": 2.7,
        "earn_zero_rate.prime": 2.6,
    }
    five = tuple(sorted(set(SIX) - {"earn_p50.older"}))
    four = tuple(sorted(set(five) - {"earn_p50.prime"}))
    power, calls = _table_power(
        {tuple(sorted(SIX)): 0.81, five: 0.88, four: 0.93}
    )
    result = b2.ladder(_ladder_cells(ratios), power)
    assert result["order"][:3] == [
        "earn_p50.older",
        "earn_p50.prime",
        "earn_zero_rate.older",
    ]
    assert [entry["cell"] for entry in result["log"]] == [
        "earn_p50.older",
        "earn_p50.prime",
    ]
    assert result["retained"] == list(four)
    assert result["p_gate"] == 0.93
    assert result["outcome"] == b2.LADDER_CLEARED
    assert calls == [tuple(sorted(SIX)), five, four]


def test_ladder_keeps_a_familys_last_cell():
    ratios = {
        "earn_zero_rate.older": 3.0,
        "earn_zero_rate.prime": 2.9,
        "earn_p50.older": 2.0,
        "earn_p50.prime": 1.9,
        "earn_p90.older": 1.8,
        "earn_p90.prime": 1.7,
    }
    power, _ = _table_power({})
    result = b2.ladder(_ladder_cells(ratios), power)
    actions = {entry["cell"]: entry["action"] for entry in result["log"]}
    assert actions["earn_zero_rate.older"] == "pruned"
    assert actions["earn_zero_rate.prime"] == "kept_last_in_concept"
    assert actions["earn_p90.prime"] == "kept_last_in_concept"
    assert result["retained"] == ["earn_p90.prime", "earn_zero_rate.prime"]
    assert result["outcome"] == b2.WEAK_POWER_OR_VACUITY
    assert result["guards"]["at_least_four_cells"] is False


def test_ladder_guards_fail_on_three_cells_or_every_tolerance_capped():
    three = ("earn_p50.prime", "earn_p90.older", "earn_zero_rate.prime")
    power, _ = _table_power({tuple(sorted(three)): 0.99})
    result = b2.ladder(_ladder_cells(dict.fromkeys(three, 2.0)), power)
    assert result["p_gate"] == 0.99
    assert result["outcome"] == b2.WEAK_POWER_OR_VACUITY
    four = (*three, "earn_p90.prime")
    power, _ = _table_power({tuple(sorted(four)): 0.99})
    capped = b2.ladder(
        _ladder_cells(dict.fromkeys(four, 2.0), capped=four), power
    )
    assert capped["guards"]["not_every_tolerance_at_cap"] is False
    assert capped["outcome"] == b2.WEAK_POWER_OR_VACUITY
    one_free = b2.ladder(
        _ladder_cells(dict.fromkeys(four, 2.0), capped=four[:3]), power
    )
    assert one_free["outcome"] == b2.LADDER_CLEARED
    empty = b2.ladder([], power)
    assert empty["outcome"] == b2.WEAK_POWER_OR_VACUITY


@st.composite
def _ladder_case(draw):
    names = draw(
        st.lists(
            st.sampled_from(b2.CELLS), min_size=1, max_size=8, unique=True
        )
    )
    ratios = {
        name: draw(st.floats(min_value=0.5, max_value=4.0)) for name in names
    }
    capped = tuple(name for name in names if draw(st.booleans()))
    seed = draw(st.integers(0, 2**32 - 1))
    target = draw(st.floats(min_value=0.5, max_value=0.99))
    return names, ratios, capped, seed, target


@settings(max_examples=300, deadline=None)
@given(_ladder_case())
def test_ladder_invariants(case):
    names, ratios, capped, seed, target = case

    def power(surface):
        digest = hashlib.sha256(f"{seed}:{sorted(surface)}".encode())
        return int(digest.hexdigest()[:8], 16) / 2**32

    cells = _ladder_cells(ratios, capped)
    result = b2.ladder(cells, power, target=target)
    retained, pruned = result["retained"], result["pruned"]
    assert set(retained) | set(pruned) == set(names)
    assert not set(retained) & set(pruned)
    assert {b2.concept(n) for n in retained} == {b2.concept(n) for n in names}
    assert result["p_gate"] == power(tuple(retained))
    assert result["order"] == sorted(names, key=lambda n: (-ratios[n], n))
    # Pruning follows the order and stops at the first power at target.
    log_cells = [entry["cell"] for entry in result["log"]]
    assert log_cells == result["order"][: len(log_cells)]
    for entry in result["log"][:-1]:
        if entry["action"] == "pruned":
            assert entry["p_gate_after"] < target
    assert result["clears"] == (
        result["p_gate"] >= target
        and len(retained) >= 4
        and not all(name in capped for name in retained)
    )
    assert b2.ladder(cells, power, target=target) == result


def _ruled_cells(planning):
    return ruled.ruled_cells(planning, ruled.BINDING)


def test_ladder_matches_the_ruled_power_ladder_on_every_order(planning):
    """Section 11 ran the ladder over all 720 orders of the six; with each
    order as B2's tolerance/sigma order, b2.ladder ends where it does."""
    cells = _ruled_cells(planning)
    nu = ruled.design_degrees_of_freedom(planning["counts"]["design"])

    def power(names):
        return ruled.surface_power(
            [cells[name] for name in names], nu, ruled.BINDING
        )["p_gate"]

    expected = ruled.ladder_outcomes(cells, nu, ruled.BINDING)
    ends: dict[tuple[str, ...], int] = {}
    cleared = 0
    for order in itertools.permutations(sorted(cells)):
        ratios = {name: 10.0 - index for index, name in enumerate(order)}
        result = b2.ladder(_ladder_cells(ratios), power)
        assert result["order"] == list(order)
        cleared += result["clears"]
        key = tuple(result["retained"])
        ends[key] = ends.get(key, 0) + 1
    assert cleared == expected["orders_clearing"] == 306
    assert {
        tuple(entry["cells"]): entry["orders"]
        for entry in expected["end_surfaces"]
    } == ends


# --------------------------------------------------------------------------
# Plumbing: read guard, opened-file check, exclusive writes, git checks
# --------------------------------------------------------------------------
def test_read_guard_refuses_a_file_outside_the_read_set(tmp_path):
    allowed_file = tmp_path / "family" / "2013" / "FAM2013ER.txt"
    other = tmp_path / "family" / "2017" / "FAM2017ER.txt"
    for path in (allowed_file, other):
        path.parent.mkdir(parents=True)
        path.write_text("x", encoding="utf-8")
    with b2.psid_read_guard(
        tmp_path, frozenset({"family/2013/FAM2013ER.txt"})
    ):
        assert allowed_file.read_text(encoding="utf-8") == "x"
        with pytest.raises(PermissionError, match="read set"):
            other.read_text(encoding="utf-8")
    assert other.read_text(encoding="utf-8") == "x"


def test_check_opened_needs_pinned_names_and_hashes():
    pinned = {"a.txt": "1", "b.txt": "2"}
    assert b2.check_opened({"b.txt": "2"}, pinned) == {"b.txt": "2"}
    with pytest.raises(AssertionError, match="outside"):
        b2.check_opened({"c.txt": "3"}, pinned)
    with pytest.raises(AssertionError, match="pinned hashes"):
        b2.check_opened({"a.txt": "9"}, pinned)


def test_write_exclusive_refuses_to_overwrite(tmp_path):
    path = tmp_path / "out" / "record.json"
    digest = b2.write_exclusive(path, {"b": np.float64(1.5), "a": [1]})
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "a": [1],
        "b": 1.5,
    }
    with pytest.raises(FileExistsError):
        b2.write_exclusive(path, {"a": 2})
    assert json.loads(path.read_text(encoding="utf-8"))["b"] == 1.5
    # Non-finite values are written as null, as the selectors write them.
    b2.write_exclusive(tmp_path / "nan.json", {"a": float("nan")})
    assert json.loads((tmp_path / "nan.json").read_text()) == {"a": None}


def _git_repo(tmp_path):
    def run(*args):
        return subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    run("init", "-q")
    run("config", "user.email", "test@example.org")
    run("config", "user.name", "Test")
    (tmp_path / "artifact.json").write_text("{}\n", encoding="utf-8")
    run("add", "artifact.json")
    run("commit", "-q", "-m", "artifact")
    return run


def test_repository_checks(tmp_path):
    run = _git_repo(tmp_path)
    head = run("rev-parse", "HEAD")
    assert b2.require_clean_head(tmp_path, head) == head
    with pytest.raises(RuntimeError, match="expected commit"):
        b2.require_clean_head(tmp_path, "0" * 40)
    with pytest.raises(RuntimeError, match="required"):
        b2.require_clean_head(tmp_path, "")
    pin = b2.committed_sha256(tmp_path, tmp_path / "artifact.json")
    assert pin == {
        "path": "artifact.json",
        "sha256": hashlib.sha256(b"{}\n").hexdigest(),
        "commit": head,
    }
    (tmp_path / "artifact.json").write_text("{ }\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not clean"):
        b2.require_clean_head(tmp_path, head)
    with pytest.raises(RuntimeError, match="differs"):
        b2.committed_sha256(tmp_path, tmp_path / "artifact.json")
    (tmp_path / "new.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not committed"):
        b2.committed_sha256(tmp_path, tmp_path / "new.json")


def test_registration_and_thread_settings(monkeypatch):
    assert b2.require_registration(" 6200000000 ") == "6200000000"
    for bad in (None, "", "  ", "two words"):
        with pytest.raises(RuntimeError, match="registration"):
            b2.require_registration(bad)
    # BLAS, OpenMP and numexpr (which pandas uses) are all pinned.
    assert b2.THREAD_VARIABLES == (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    )
    for name in b2.THREAD_VARIABLES:
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("OMP_WAIT_POLICY", "PASSIVE")
    monkeypatch.setenv("POPULACE_FIT_N_JOBS", "4")
    settings = b2.thread_settings()
    assert all(settings[name] == "1" for name in b2.THREAD_VARIABLES)
    assert settings["POPULACE_FIT_N_JOBS"] == "4"
    # populace-fit's forest jobs: unset means every core, so 1 to 4 only.
    assert b2.FIT_JOBS_VARIABLE == "POPULACE_FIT_N_JOBS"
    for value in ("1", "2", "3"):
        monkeypatch.setenv("POPULACE_FIT_N_JOBS", value)
        assert b2.thread_settings()["POPULACE_FIT_N_JOBS"] == value
    for value in ("0", "5", "-1", "4.0", ""):
        monkeypatch.setenv("POPULACE_FIT_N_JOBS", value)
        with pytest.raises(RuntimeError, match="POPULACE_FIT_N_JOBS"):
            b2.thread_settings()
    monkeypatch.delenv("POPULACE_FIT_N_JOBS")
    with pytest.raises(RuntimeError, match="POPULACE_FIT_N_JOBS"):
        b2.thread_settings()
    monkeypatch.setenv("POPULACE_FIT_N_JOBS", "4")
    # Every variable must be exactly 1, as registered (b2.thread_settings
    # says why), and an unset one is refused too.
    for name in b2.THREAD_VARIABLES:
        for value in ("2", "4", "0", ""):
            monkeypatch.setenv(name, value)
            with pytest.raises(RuntimeError, match=name):
                b2.thread_settings()
        monkeypatch.delenv(name)
        with pytest.raises(RuntimeError, match=name):
            b2.thread_settings()
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("OMP_WAIT_POLICY", "ACTIVE")
    with pytest.raises(RuntimeError, match="PASSIVE"):
        b2.thread_settings()


def _square(index):
    return {"replicate": index, "value": index * b2.worker_payload()["k"]}


def _raise_on_odd(index):
    if index % 2:
        raise ValueError("invented")
    return {"replicate": index}


def test_replicate_driver_orders_results_and_counts_failures():
    results = b2.run_replicates(_square, 5, {"k": 3}, 1)
    assert [r["value"] for r in results] == [0, 3, 6, 9, 12]
    assert b2.worker_payload() == {}
    failed = b2.run_replicates(_raise_on_odd, 4, {}, 1)
    assert [r.get("failed", False) for r in failed] == [
        False,
        True,
        False,
        True,
    ]
    assert failed[1]["exception_class"] == "ValueError"


def _design_counts(index):
    payload = b2.worker_payload()
    copies = b2.design_multiplicities(
        payload["design"], index, root=payload["root"]
    )
    return {"replicate": index, "copies": sorted(copies.items())}


@pytest.mark.parametrize("workers", [2, 3])
def test_replicates_are_the_same_in_worker_processes(workers):
    """Determinism across the process pool: the replicates are a function
    of the index and the payload alone, so serial and pooled runs agree
    and come back in index order."""
    design = _invented_design(two_cluster_strata=5, extra=(3, 1))
    payload = {"design": design, "root": b2.ROOT_SEED}
    serial = b2.run_replicates(_design_counts, 9, payload, 1)
    pooled = b2.run_replicates(_design_counts, 9, payload, workers)
    assert pooled == serial
    assert [r["replicate"] for r in pooled] == list(range(9))
    assert b2.run_replicates(_square, 7, {"k": 5}, workers) == (
        b2.run_replicates(_square, 7, {"k": 5}, 1)
    )


def test_registered_settings_are_enforced(monkeypatch):
    with pytest.raises(AssertionError, match="4,000"):
        floor_builder.assert_registered(floor_builder.FloorConfig(8, 1))
    with pytest.raises(AssertionError, match="4,000"):
        scorer.assert_registered(scorer.ScoreConfig(4, 1))
    monkeypatch.setattr(m6_cells, "FLOOR_SEEDS", tuple(range(5)))
    with pytest.raises(AssertionError, match="0-99"):
        floor_builder.assert_registered(floor_builder.FloorConfig())
    monkeypatch.setattr(pv, "DRAW_SEEDS", (6200, 6201, 6202))
    with pytest.raises(AssertionError, match="6200-6219"):
        scorer.assert_registered(scorer.ScoreConfig())


def test_registered_settings_hold_unpatched():
    floor_builder.assert_registered(floor_builder.FloorConfig())
    scorer.assert_registered(scorer.ScoreConfig())
