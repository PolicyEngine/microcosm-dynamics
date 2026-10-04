"""gate_epuf_fill rules: worked cases and invariants on synthetic careers."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.harness import epuf_fill_gate as g
from populace_dynamics.harness.epuf_cells import CellValue
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


@pytest.mark.parametrize("family", ["odd", "pre"])
def test_populations_read_no_cell_their_family_masks(family):
    earnings, birth, sex = _careers(5)
    rng = np.random.default_rng(1)
    mask = g.family_mask(family, birth)
    scrambled = earnings.copy()
    scrambled[mask] = rng.permutation(scrambled[mask])
    scrambled[mask & (rng.random(mask.shape) < 0.3)] = 0.0
    for group in g.groups():
        if not group.startswith(f"{family}."):
            continue
        assert np.array_equal(
            g.group_rows(group, earnings, birth, sex),
            g.group_rows(group, scrambled, birth, sex),
        ), group
    first = g.family_cells(family, earnings, birth, sex, WAGE_BASES, NAWI)
    second = g.family_cells(family, scrambled, birth, sex, WAGE_BASES, NAWI)
    for cell_id in first:
        statistic = cell_id.rsplit(".", 1)[1]
        if statistic.startswith(("aime", "paime", "pzero", "plevel")) or (
            statistic in ("yzero", "ylevel", "zint", "zexit", "wint", "level")
        ):
            assert first[cell_id].n == second[cell_id].n, cell_id


@pytest.mark.parametrize("family", ["odd", "pre"])
def test_each_group_counts_exactly_its_group_rows(family):
    earnings, birth, sex = _careers(11)
    cells = g.family_cells(family, earnings, birth, sex, WAGE_BASES, NAWI)
    for group in g.groups():
        if not group.startswith(f"{family}."):
            continue
        rows = g.group_rows(group, earnings, birth, sex)
        stratum = group.split(".")[2]
        if stratum in g.ODD_AGE_BANDS:
            low, high = g.ODD_AGE_BANDS[stratum]
            ages = np.asarray(g.MASKED_ODD_YEARS)[None, :] - birth[:, None]
            units = int(
                (((ages >= low) & (ages <= high)) & rows[:, None]).sum()
            )
            assert cells[f"{group}.level"].n == units, group
        else:
            name = "aime" if f"{group}.aime_p50" in cells else "paime"
            assert cells[f"{group}.{name}_p50"].n == int(rows.sum()), group


def test_odd_units_start_at_age_22_and_bands_pool():
    earnings, birth, sex = _careers(12)
    rows = g.group_rows("odd.men.a22_29", earnings, birth, sex)
    ages = np.asarray(g.MASKED_ODD_YEARS)[None, :] - birth[rows][:, None]
    assert (((ages >= 22) & (ages <= 29)).any(axis=1)).all()
    assert min(low for low, _ in g.ODD_AGE_BANDS.values()) == 22
    cells = g.odd_cells(earnings, birth, sex, WAGE_BASES, NAWI)
    for sex_label in g.SEXES:
        bands = [
            cells[f"odd.{sex_label}.{band}.level"].n
            for band in ("a22_29", "a30_44", "a45_59", "a60_74")
        ]
        assert cells[f"odd.{sex_label}.a22_74.level"].n == sum(bands)


def test_partial_aime_indexes_to_2006():
    history = np.zeros((1, len(g.YEARS)))
    history[0, 2006 - g.FIRST_YEAR] = 42_000.0
    history[0, 2000 - g.FIRST_YEAR] = 30_000.0
    expected = np.floor((42_000.0 + 30_000.0 * NAWI[2006] / NAWI[2000]) / 420)
    assert g.partial_aime(history, NAWI)[0] == expected


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


@settings(max_examples=20, deadline=None)
@given(seed=st.integers(0, 1_000), size=st.integers(200, 800))
def test_floor_group_estimates_the_standard_error_of_a_mean(seed, size):
    rng = np.random.default_rng(seed)
    values = rng.normal(5.0, 2.0, size=20_000)
    pool = np.arange(len(values))

    def cells(rows):
        return {
            "pre.men.b1930_1934.plevel": CellValue(
                float(values[rows].mean()), len(rows), len(rows)
            ),
            "pre.men.b1935_1939.plevel": CellValue(1.0, 0, 0),
        }

    floor = g.floor_group(
        "pre.men.b1930_1934",
        cells,
        pool,
        size,
        group_index=seed,
        n_replicates=1_000,
    )
    # Only the group's own cell is kept; on the log scale the standard
    # error of a mean of 5 with sd 2 is about (2 / sqrt(size)) / 5.
    assert set(floor.sigma) == {"pre.men.b1930_1934.plevel"}
    expected = 2.0 / np.sqrt(size) / 5.0
    assert floor.sigma["pre.men.b1930_1934.plevel"] == pytest.approx(
        expected, rel=0.15
    )
    assert len(floor.replicates["pre.men.b1930_1934.plevel"]) == 1_000
    assert floor.seed == (g.FLOOR_SEED_BASE, seed, 1_000, size)


def test_floor_refuses_a_pool_too_small_for_two_samples():
    with pytest.raises(ValueError, match="exceed the pool"):
        g.floor_group(
            "odd.men.a18_29",
            lambda rows: {},
            np.arange(10),
            6,
            group_index=0,
            n_replicates=2,
        )


def test_groups_and_group_of():
    assert g.group_of("odd.men.a22_29.r1") == "odd.men.a22_29"
    assert (
        g.group_of("pre.women.b1930_1934.aime_p50") == "pre.women.b1930_1934"
    )
    earnings, birth, sex = _careers(7)
    cells = {
        **g.odd_cells(earnings, birth, sex, WAGE_BASES, NAWI),
        **g.pre_career_cells(earnings, birth, sex, WAGE_BASES, NAWI),
    }
    assert sorted({g.group_of(cell) for cell in cells}) == g.groups()
    assert len(g.groups()) == 40
    for group in g.groups():
        rows = g.group_rows(group, earnings, birth, sex)
        sex_label = group.split(".")[1]
        assert (sex[rows] == g.SEXES[sex_label]).all()


def test_partition_reasons_in_order():
    floor = g.FloorGroup(
        group="odd.men.a18_29",
        sample_size=10,
        pool_size=100,
        seed=(0,),
        replicates={},
        sigma={
            "odd.men.a18_29.r1": 0.01,
            "odd.men.a18_29.zint": np.nan,
            "odd.men.a18_29.zexit": 0.1,
            "odd.men.a18_29.wint": 0.1,
        },
        min_events={
            "odd.men.a18_29.r1": (50,) * 20,
            "odd.men.a18_29.zint": (50,) * 20,
            "odd.men.a18_29.zexit": (50,) * 18 + (5,) * 2,
            "odd.men.a18_29.wint": (50,) * 19 + (5,),
        },
    )
    truth = {
        "odd.men.a18_29.r1": CellValue(0.8, 50, 100),
        "odd.men.a18_29.zint": CellValue(0.02, 50, 100),
        "odd.men.a18_29.zexit": CellValue(0.4, 50, 100),
        "odd.men.a18_29.wint": CellValue(0.1, 50, 100),
        "odd.men.a18_29.level": CellValue(0.0, 0, 100),
    }
    reasons = g.partition(truth, {"odd.men.a18_29": floor})
    assert reasons == {
        "odd.men.a18_29.r1": "gates",
        "odd.men.a18_29.zint": "floor_undefined",
        "odd.men.a18_29.zexit": "too_few_events",
        "odd.men.a18_29.wint": "gates",
        "odd.men.a18_29.level": "truth_undefined",
    }


def test_score_uses_the_mean_over_draws_and_every_gating_cell():
    truth = {
        "odd.men.a18_29.r1": CellValue(0.80, 100, 100),
        "odd.men.a18_29.zint": CellValue(0.02, 100, 100),
        "odd.men.a18_29.level": CellValue(0.30, 100, 100),
    }
    draws = [
        {
            "odd.men.a18_29.r1": CellValue(0.81, 1, 1),
            "odd.men.a18_29.zint": CellValue(0.0, 1, 1),
            "odd.men.a18_29.level": CellValue(0.30, 1, 1),
        },
        {
            "odd.men.a18_29.r1": CellValue(0.79, 1, 1),
            "odd.men.a18_29.zint": CellValue(0.04, 1, 1),
            "odd.men.a18_29.level": CellValue(0.90, 1, 1),
        },
    ]
    tolerance = {"odd.men.a18_29.r1": 0.005, "odd.men.a18_29.zint": 0.1}
    result = g.score(truth, draws, tolerance, tolerance)
    assert result["cells"]["odd.men.a18_29.r1"]["gap"] == pytest.approx(0.0)
    assert result["cells"]["odd.men.a18_29.zint"]["gap"] == pytest.approx(0.0)
    assert "passes" not in result["cells"]["odd.men.a18_29.level"]
    assert result["passes"] is True and result["n_gating"] == 2
    result = g.score(truth, draws[:1], tolerance, tolerance)
    assert result["passes"] is False and result["n_failing"] == 2


@pytest.mark.parametrize("seed", [0, 1])
def test_odd_oracle_permutes_true_values_within_strata(seed):
    earnings, birth, sex = _careers(8)
    filled = g.odd_oracle_fill(earnings, birth, sex, WAGE_BASES, seed)
    others = ~g.odd_mask(len(birth))
    assert np.array_equal(filled[others], earnings[others])
    for year in g.MASKED_ODD_YEARS:
        column = year - g.FIRST_YEAR
        assert np.array_equal(
            np.sort(filled[:, column]), np.sort(earnings[:, column])
        )
    # A unit whose neighbours are both zero and whose stratum's true values
    # are all zero keeps zero.
    assert (filled[:, 1997 - g.FIRST_YEAR] >= 0).all()


def test_pre_oracle_moves_whole_blocks_within_birth_year():
    earnings, birth, sex = _careers(9)
    filled = g.pre_career_oracle_fill(earnings, birth, sex, WAGE_BASES, 0)
    masked = g.pre_career_mask(birth)
    assert np.array_equal(filled[~masked], earnings[~masked])
    blocks = {tuple(row[m]) for row, m in zip(earnings, masked, strict=True)}
    for row, m in zip(filled, masked, strict=True):
        assert tuple(row[m]) in blocks
    for year in np.unique(birth):
        rows = birth == year
        assert np.array_equal(
            np.sort(filled[rows][:, :17].sum(axis=1)),
            np.sort(earnings[rows][:, :17].sum(axis=1)),
        )


def _scored(gaps, tolerance=0.01):
    cells = {
        f"odd.men.a18_29.c{i}": {
            "gap": gap,
            "tolerance": tolerance,
            "passes": bool(np.isfinite(gap) and abs(gap) <= tolerance),
        }
        for i, gap in enumerate(gaps)
    }
    failing = sum(not row["passes"] for row in cells.values())
    return {"cells": cells, "n_failing": failing, "passes": failing == 0}


def test_adoption_tiers():
    current = _scored([0.05, -np.inf, 0.001])
    assert g.adoption_tier(_scored([0.005, 0.0, -0.009]), current) == (
        "certified"
    )
    # Fails one cell, but within min(current gap, 3 tolerances) there.
    assert g.adoption_tier(_scored([0.025, 0.0, 0.0]), current) == ("improves")
    # The allowance is capped at three tolerances even where the current
    # rule is far worse, or infinitely worse.
    assert g.adoption_tier(_scored([0.04, 0.0, 0.0]), current) == (
        "not_adopted"
    )
    assert g.adoption_tier(_scored([0.0, 0.029, 0.0]), current) == ("improves")
    assert g.adoption_tier(_scored([0.0, 0.031, 0.0]), current) == (
        "not_adopted"
    )
    # Worse than both the current rule and the tolerance in a cell.
    assert g.adoption_tier(_scored([0.06, 0.0, 0.0]), current) == (
        "not_adopted"
    )
    assert g.adoption_tier(_scored([0.0, 0.0, 0.02]), current) == (
        "not_adopted"
    )
    # A non-finite gap is never adopted as an improvement.
    assert g.adoption_tier(_scored([0.04, -np.inf, 0.0]), current) == (
        "not_adopted"
    )
    # Smaller gaps everywhere but not strictly fewer failing cells.
    assert g.adoption_tier(_scored([0.04, 0.03]), _scored([0.05, 0.05])) == (
        "not_adopted"
    )
    assert g.adoption_tier(_scored([0.025, 0.0]), _scored([0.05, 0.05])) == (
        "improves"
    )


@pytest.mark.parametrize(
    ("primary", "alternative", "expected"),
    [
        ("certified", "certified", "primary"),
        ("improves", "certified", "alternative"),
        ("certified", "improves", "primary"),
        ("not_adopted", "improves", "alternative"),
        ("improves", "not_adopted", "primary"),
        ("not_adopted", "not_adopted", None),
    ],
)
def test_adopt_prefers_the_better_tier_then_the_primary(
    primary, alternative, expected
):
    assert g.adopt(primary, alternative) == expected


class _RecordingFill:
    """A neighbour-mean fill that records what it was given."""

    def __init__(self, tamper=None):
        self.tamper = tamper
        self.seen = []

    def fill(self, shares, years, birth_year, sex, person_key, mask, seed):
        self.seen.append((shares.copy(), mask.copy(), seed))
        out = shares.copy()
        for column in np.flatnonzero(mask.any(axis=0)):
            left = np.nan_to_num(shares[:, column - 1]) if column else 0.0
            right = (
                np.nan_to_num(shares[:, column + 1])
                if column + 1 < shares.shape[1]
                else 0.0
            )
            rows = mask[:, column]
            out[rows, column] = ((left + right) / 2.0)[rows]
        if self.tamper == "unmasked":
            free = np.argwhere(~mask & np.isfinite(shares))[0]
            out[tuple(free)] = 0.123
        elif self.tamper == "nan":
            out[np.argwhere(mask)[0][0], np.argwhere(mask)[0][1]] = np.nan
        elif self.tamper == "above_cap":
            out[np.argwhere(mask)[0][0], np.argwhere(mask)[0][1]] = 1.5
        return out


def _matrix(seed=13):
    earnings, birth, sex = _careers(seed, n=1_500)
    return g.EPUFMatrix(
        person_id=np.arange(len(birth)) + 1,
        birth_year=birth,
        sex=sex,
        earnings=earnings,
    )


@pytest.mark.parametrize("family", ["odd", "pre"])
def test_score_candidate_hides_the_union_mask_and_scores_own_family(family):
    matrix = _matrix()
    truth = g.family_cells(
        family,
        matrix.earnings,
        matrix.birth_year,
        matrix.sex,
        WAGE_BASES,
        NAWI,
    )
    fill = _RecordingFill()
    result = g.score_candidate(
        fill,
        family,
        matrix,
        truth,
        {},
        [],
        seeds=(7100, 7101),
        wage_bases=WAGE_BASES,
        nawi=NAWI,
    )
    union = g.union_mask(matrix.birth_year)
    for shares, mask, _ in fill.seen:
        assert np.isnan(shares[union]).all()
        assert np.isfinite(shares[~union]).all()
        assert np.array_equal(mask, g.family_mask(family, matrix.birth_year))
    assert [seed for _, _, seed in fill.seen] == [7100, 7101]
    assert set(result["cells"]) == set(truth)


@pytest.mark.parametrize("tamper", ["unmasked", "nan", "above_cap"])
def test_score_candidate_refuses_invalid_output(tamper):
    matrix = _matrix()
    with pytest.raises(g.FillOutputInvalid):
        g.score_candidate(
            _RecordingFill(tamper),
            "odd",
            matrix,
            {},
            {},
            [],
            seeds=(7100,),
            wage_bases=WAGE_BASES,
            nawi=NAWI,
        )


def test_earnings_from_shares_is_exact_at_the_cap():
    shares = np.ones((1, len(g.YEARS)))
    assert np.array_equal(g.earnings_from_shares(shares)[0], CAPS)


def test_test_part_is_refused_until_the_gate_locks(tmp_path):
    with pytest.raises(g.TestPartLocked):
        g.epuf_matrix(g.TEST)
    with pytest.raises(g.TestPartLocked):
        g.epuf_matrix(None)
    unlocked = tmp_path / "gates.yaml"
    unlocked.write_text("gates:\n  gate_epuf_fill:\n    locked: false\n")
    with pytest.raises(g.TestPartLocked):
        g.test_part(gates_path=unlocked)
    wrong = tmp_path / "wrong.yaml"
    wrong.write_text(
        "gates:\n  gate_epuf_fill:\n    locked: true\n"
        "    registration_id: other\n    thresholds:\n      locked: true\n"
    )
    with pytest.raises(g.TestPartLocked):
        g.test_part(gates_path=wrong)


def _fake_epuf(monkeypatch, annual_rows):
    import pandas as pd

    from populace_dynamics.data import epuf

    demographic = pd.DataFrame(
        {
            "person_id": np.arange(1, 41, dtype=np.int32),
            "birth_year": np.full(40, 1950, dtype=np.int16),
            "sex": np.ones(40, dtype=np.int8),
        }
    )
    annual = pd.DataFrame(
        annual_rows, columns=["person_id", "year", "earnings"]
    )
    monkeypatch.setattr(epuf, "read_demographic", lambda **_: demographic)
    monkeypatch.setattr(epuf, "read_annual", lambda **_: annual)


def test_epuf_matrix_places_rows_and_refuses_bad_joins(monkeypatch):
    _fake_epuf(monkeypatch, [(3, 1970, 1000), (3, 1971, 2000), (40, 2006, 5)])
    parts = g.split_part(np.arange(1, 41))
    for part in (g.TRAIN, g.DEV):
        matrix = g.epuf_matrix(part)
        assert matrix.person_id.tolist() == [
            i + 1 for i in range(40) if parts[i] == part
        ]
        for person, year, value in ((3, 1970, 1000), (40, 2006, 5)):
            if parts[person - 1] == part:
                row = matrix.person_id.tolist().index(person)
                assert matrix.earnings[row, year - g.FIRST_YEAR] == value
        assert matrix.earnings.sum() == sum(
            value
            for person, _, value in (
                (3, 1970, 1000),
                (3, 1971, 2000),
                (40, 2006, 5),
            )
            if parts[person - 1] == part
        )
    _fake_epuf(monkeypatch, [(41, 1970, 1000)])
    with pytest.raises(ValueError, match="no demographic person"):
        g.epuf_matrix(g.DEV)
    _fake_epuf(monkeypatch, [(3, 1970, 1000), (3, 1970, 5)])
    with pytest.raises(ValueError, match="two annual rows"):
        g.epuf_matrix(g.DEV)


def test_odd_family_owns_only_career_odd_years():
    birth = np.array([1950, 1976, 1979, 1980])
    own = g.family_mask("odd", birth)
    pre = g.pre_career_mask(birth)
    odd = g.odd_mask(len(birth))
    assert np.array_equal(own, odd & ~pre)
    # Born 1979: 1997 and 1999 are before age 22 and belong to the
    # pre-career rule; 2001-2005 are the odd family's.
    owned = [g.YEARS[c] for c in np.flatnonzero(own[2])]
    assert owned == [2001, 2003, 2005]
    assert (g.union_mask(birth) == (odd | pre)).all()


def test_current_fills_match_the_assembler_rules():
    earnings, birth, sex = _careers(21, n=400)
    shares = earnings / CAPS[None, :]
    own = g.family_mask("odd", birth)
    given = np.where(g.union_mask(birth), np.nan, shares)
    out = g.CurrentOddFill().fill(
        given, np.asarray(g.YEARS), birth, sex, None, own, 0
    )
    expected = np.minimum(
        g.current_odd_fill(earnings, birth) / CAPS[None, :], 1.0
    )
    # Where both neighbours are known the rule is the mean of the truth.
    both = own.copy()
    for column in np.flatnonzero(own.any(axis=0)):
        both[:, column] &= np.isfinite(given[:, column - 1]) & np.isfinite(
            given[:, column + 1]
        )
    np.testing.assert_allclose(out[both], expected[both])
    # A unit at age 22 has its pre-career neighbour unknown: the rule takes
    # the known one.
    one = own & ~both
    for row, column in np.argwhere(one)[:20]:
        known = given[row, column + 1] * CAPS[column + 1] / CAPS[column]
        assert out[row, column] == pytest.approx(
            min(np.nan_to_num(known), 1.0)
        )
    pre = g.family_mask("pre", birth)
    zeroed = g.CurrentPreFill().fill(given, None, birth, sex, None, pre, 0)
    assert (zeroed[pre] == 0).all()
    assert g.current_rule("odd").name == "current_odd_rule"
    with pytest.raises(ValueError):
        g.current_rule("other")


def test_score_candidate_scores_own_cells_and_keeps_the_rest_true(
    monkeypatch,
):
    matrix = _matrix(22)
    seen = []
    original = g.family_cells

    def spy(family, earnings, *args):
        seen.append(earnings.copy())
        return original(family, earnings, *args)

    monkeypatch.setattr(g, "family_cells", spy)

    class Constant:
        def fill(self, shares, years, birth_year, sex, key, mask, seed):
            out = shares.copy()
            out[mask] = 0.5
            return out

    g.score_candidate(
        Constant(),
        "odd",
        matrix,
        {},
        {},
        [],
        seeds=(7100,),
        wage_bases=WAGE_BASES,
        nawi=NAWI,
    )
    (scored,) = seen
    own = g.family_mask("odd", matrix.birth_year)
    rows, columns = own.nonzero()
    np.testing.assert_allclose(scored[rows, columns], 0.5 * CAPS[columns])
    assert np.array_equal(scored[~own], matrix.earnings[~own])


def test_score_candidate_refuses_writes_into_the_other_familys_cells():
    matrix = _matrix(23)

    class Trespass:
        def fill(self, shares, years, birth_year, sex, key, mask, seed):
            out = shares.copy()
            out[mask] = 0.1
            other = g.pre_career_mask(birth_year) & ~mask
            out[other] = 0.2
            return out

    with pytest.raises(g.FillOutputInvalid):
        g.score_candidate(
            Trespass(),
            "odd",
            matrix,
            {},
            {},
            [],
            seeds=(7100,),
            wage_bases=WAGE_BASES,
            nawi=NAWI,
        )


def test_a_masked_year_at_age_21_is_no_odd_unit():
    earnings = np.zeros((2, len(g.YEARS)))
    birth = np.array([1976, 1976])
    sex = np.array([1, 1])
    for year in (1998, 2000, 2002, 2004, 2006):
        earnings[:, year - g.FIRST_YEAR] = 20_000.0
    cells = g.odd_cells(earnings, birth, sex, WAGE_BASES, NAWI)
    # Born 1976: 1997 is age 21 (outside every band); 1999-2005 are ages
    # 23-29, four units each.
    assert cells["odd.men.a22_29.level"].n == 2 * 4
    assert cells["odd.men.a22_74.level"].n == 2 * 4


def test_epuf_matrix_refuses_years_outside_the_file(monkeypatch):
    _fake_epuf(monkeypatch, [(3, 2007, 1000)])
    with pytest.raises(ValueError, match="outside 1951-2006"):
        g.epuf_matrix(g.DEV)
