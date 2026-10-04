"""gate_epuf_fill rules: worked cases and invariants on synthetic careers."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness.epuf_operator import disclosure_constants
from populace_dynamics.ss import statutory_aime

WAGE_BASES = {
    year: float(row["wage_base"])
    for year, row in disclosure_constants().items()
}
NAWI = captured_ssa_parameters().nawi
CAPS = np.array([WAGE_BASES[year] for year in g.YEARS])


def _careers(seed: int, n: int = 3_000) -> tuple[np.ndarray, ...]:
    """Synthetic capped careers with persistence, zeros and caps."""

    rng = np.random.default_rng(seed)
    birth = rng.integers(1925, 1981, size=n)
    sex = rng.choice([1, 2], size=n)
    level = rng.normal(0.0, 0.8, size=n)
    shocks = rng.normal(0.0, 0.35, size=(n, len(g.YEARS)))
    log_share = level[:, None] - 1.2 + np.cumsum(shocks, axis=1) * 0.3
    earnings = np.minimum(np.exp(log_share), 1.0) * CAPS[None, :]
    working = rng.random((n, len(g.YEARS))) < 0.8
    age = np.asarray(g.YEARS)[None, :] - birth[:, None]
    earnings = np.where(working & (age >= 15) & (age <= 85), earnings, 0.0)
    return np.round(earnings), birth, sex


def test_split_is_the_salted_hash_and_partitions_ids():
    ids = np.arange(1, 20_001)
    parts = g.split_part(ids)
    assert set(np.unique(parts)) == {g.TRAIN, g.DEV, g.TEST}
    for person_id in (1, 777, 20_000):
        digest = hashlib.sha256(g.SPLIT_SALT + str(person_id).encode())
        position = int.from_bytes(digest.digest()[:8], "big") / 2.0**64
        expected = (
            g.TRAIN if position < 0.6 else g.DEV if position < 0.8 else g.TEST
        )
        assert parts[person_id - 1] == expected
    shares = np.bincount(parts) / len(parts)
    assert shares == pytest.approx([0.6, 0.2, 0.2], abs=0.015)
    # A person's part depends only on their id, never on the batch.
    assert (g.split_part(ids[::-1])[::-1] == parts).all()


def test_current_odd_fill_is_the_neighbour_mean_and_touches_nothing_else():
    earnings, _, _ = _careers(1, n=200)
    filled = g.current_odd_fill(earnings)
    for year in g.MASKED_ODD_YEARS:
        column = year - g.FIRST_YEAR
        expected = (earnings[:, column - 1] + earnings[:, column + 1]) / 2
        assert np.array_equal(filled[:, column], expected)
    others = ~g.odd_mask(len(earnings))
    assert np.array_equal(filled[others], earnings[others])


def test_pre_career_mask_starts_at_1968_or_age_22():
    birth = np.array([1930, 1945, 1946, 1960])
    mask = g.pre_career_mask(birth)
    first_unmasked = np.array([g.YEARS[int(np.argmin(row))] for row in mask])
    assert first_unmasked.tolist() == [1968, 1968, 1968, 1982]
    earnings, birth, _ = _careers(2, n=200)
    zeroed = g.current_pre_career_fill(earnings, birth)
    masked = g.pre_career_mask(birth)
    assert (zeroed[masked] == 0).all()
    assert np.array_equal(zeroed[~masked], earnings[~masked])


@settings(max_examples=60, deadline=None)
@given(seed=st.integers(0, 10_000), birth=st.integers(1929, 1945))
def test_aime_matches_the_statutory_oracle(seed, birth):
    rng = np.random.default_rng(seed)
    history = np.where(
        rng.random(len(g.YEARS)) < 0.25,
        0.0,
        np.minimum(rng.lognormal(9.0, 1.0, size=len(g.YEARS)), CAPS),
    )
    params = captured_ssa_parameters()
    through_61 = {
        int(year): float(value)
        for year, value in zip(g.YEARS, history, strict=True)
        if year <= birth + 61
    }
    expected = statutory_aime.aime(through_61, birth, params)
    assert g.aime_35(history[None, :], np.array([birth]), NAWI)[0] == expected


def test_aime_refuses_cohorts_outside_the_file():
    with pytest.raises(ValueError, match="1929-1945"):
        g.aime_35(np.zeros((1, len(g.YEARS))), np.array([1946]), NAWI)


@pytest.mark.parametrize("family", ["odd", "pre"])
def test_truth_against_itself_has_zero_gap_in_every_cell(family):
    earnings, birth, sex = _careers(3)
    cells = g.odd_cells if family == "odd" else g.pre_career_cells
    truth = cells(earnings, birth, sex, WAGE_BASES, NAWI)
    assert truth
    for cell_id, value in truth.items():
        if np.isfinite(value.value) and value.value != 0:
            assert g.gap(cell_id, value.value, value.value) == 0.0


@pytest.mark.parametrize("family", ["odd", "pre"])
def test_cells_ignore_row_order(family):
    earnings, birth, sex = _careers(4)
    order = np.random.default_rng(0).permutation(len(birth))
    cells = g.odd_cells if family == "odd" else g.pre_career_cells
    first = cells(earnings, birth, sex, WAGE_BASES, NAWI)
    second = cells(earnings[order], birth[order], sex[order], WAGE_BASES, NAWI)
    for cell_id, value in first.items():
        assert second[cell_id].n == value.n
        assert second[cell_id].events == value.events
        np.testing.assert_allclose(
            second[cell_id].value, value.value, rtol=1e-12, equal_nan=True
        )


def test_universes_read_no_masked_year():
    earnings, birth, sex = _careers(5)
    scrambled = earnings.copy()
    rng = np.random.default_rng(1)
    odd = g.odd_mask(len(birth))
    scrambled[odd] = rng.permutation(scrambled[odd])
    first = g.odd_cells(earnings, birth, sex, WAGE_BASES, NAWI)
    second = g.odd_cells(scrambled, birth, sex, WAGE_BASES, NAWI)
    for cell_id in first:
        if cell_id.endswith(("zint", "zexit", "wint", "level")):
            assert first[cell_id].n == second[cell_id].n
    pre = g.pre_career_mask(birth)
    scrambled = earnings.copy()
    scrambled[pre] = 0.0
    first = g.pre_career_cells(earnings, birth, sex, WAGE_BASES, NAWI)
    second = g.pre_career_cells(scrambled, birth, sex, WAGE_BASES, NAWI)
    for cell_id in first:
        if cell_id.endswith(("pzero", "plevel", "yzero", "ylevel")):
            assert first[cell_id].n == second[cell_id].n


def test_current_odd_rule_removes_interior_and_exit_zeros():
    earnings, birth, sex = _careers(6)
    truth = g.odd_cells(earnings, birth, sex, WAGE_BASES, NAWI)
    filled = g.odd_cells(
        g.current_odd_fill(earnings), birth, sex, WAGE_BASES, NAWI
    )
    for cell_id, value in filled.items():
        if cell_id.endswith(("zint", "zexit")) and value.n:
            assert value.value == 0.0
            assert truth[cell_id].value > 0.0
            assert g.gap(cell_id, value.value, truth[cell_id].value) == (
                -np.inf
            )


def test_worked_odd_cells():
    # Three persons born 1960 (ages 37-45 at the masked years: band 30-44
    # for 1997-2003, 45-59 for 2005), all men.
    earnings = np.zeros((3, len(g.YEARS)))
    column = {year: year - g.FIRST_YEAR for year in g.YEARS}
    for year in range(1996, 2007):
        earnings[0, column[year]] = 10_000.0  # always working
    for year in (1996, 1998, 2000, 2002, 2004, 2006):
        earnings[1, column[year]] = 20_000.0  # works only in even years
    earnings[2, column[1996]] = 5_000.0  # stops after 1996
    birth = np.full(3, 1960)
    sex = np.ones(3, dtype=int)
    cells = g.odd_cells(earnings, birth, sex, WAGE_BASES, NAWI)
    band = "odd.men.a30_44"
    # 1997-2003: person 0 positive both sides and at t; person 1 positive
    # both sides, zero at t: interior zero share 4 / 8.
    assert cells[f"{band}.zint"].value == pytest.approx(0.5)
    assert cells[f"{band}.zint"].n == 8
    # Person 2 in 1997: positive in 1996 only, zero in 1997: an exit zero.
    assert cells[f"{band}.zexit"].value == 1.0
    assert cells[f"{band}.zexit"].n == 1
    # Person 2 from 1999: zero on both sides, zero at t.
    assert cells[f"{band}.wint"].value == 0.0
    assert cells[f"{band}.wint"].n == 3


def test_gap_scales():
    assert g.cell_metric("odd.men.a18_29.r1") == "abs_gap"
    assert g.cell_metric("pre.women.b1930_1934.pr_cross") == "abs_gap"
    assert g.cell_metric("odd.men.a18_29.zint") == "log_ratio"
    assert g.cell_metric("pre.men.b1930_1934.aime_p50") == "log_ratio"
    assert g.gap("odd.men.a18_29.r2", 0.8, 0.75) == pytest.approx(0.05)
    assert g.gap("odd.men.a18_29.zint", 0.02, 0.01) == pytest.approx(
        np.log(2.0)
    )
    assert g.gap("odd.men.a18_29.zint", 0.0, 0.01) == -np.inf


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(0, 1_000), size=st.integers(200, 800))
def test_floor_sigma_estimates_the_standard_error_of_a_mean(seed, size):
    rng = np.random.default_rng(seed)
    pool_values = rng.normal(5.0, 2.0, size=20_000)
    pool = np.arange(len(pool_values))
    floor = g.floor_sigma(
        "pre.men.b1930_1934.plevel",
        lambda rows: float(pool_values[rows].mean()),
        pool,
        size,
        n_replicates=300,
        seed=seed,
    )
    # On the log scale the standard error of a mean of 5 with sd 2 is
    # about (2 / sqrt(size)) / 5.
    expected = 2.0 / np.sqrt(size) / 5.0
    assert floor.sigma == pytest.approx(expected, rel=0.15)
    assert len(floor.replicates) == 300


def test_floor_refuses_a_pool_too_small_for_two_samples():
    with pytest.raises(ValueError, match="exceed the pool"):
        g.floor_sigma(
            "odd.men.a18_29.r1",
            lambda rows: 0.0,
            np.arange(10),
            6,
            n_replicates=2,
            seed=0,
        )
