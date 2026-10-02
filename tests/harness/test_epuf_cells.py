"""Window and career cell statistics: worked cases and invariants."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.stats import spearmanr

from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.harness import epuf_cells as ec
from populace_dynamics.harness.epuf_operator import disclosure_constants
from populace_dynamics.ss import statutory_aime

WAGE_BASES = {
    year: float(row["wage_base"])
    for year, row in disclosure_constants().items()
}
CAP = {year: WAGE_BASES[year] for year in ec.WINDOW_YEARS}


def _frame(rows):
    """rows: (sex, birth_year, weight, e1998, e2000, e2002, e2004)."""
    frame = pd.DataFrame(
        rows,
        columns=["sex", "birth_year", "weight", *_columns()],
    )
    frame.insert(0, "person_id", np.arange(len(frame)) + 1)
    return frame


def _columns():
    return [f"e{year}" for year in ec.WINDOW_YEARS]


def _random_frame(rng, n=600):
    sex = rng.choice(ec.SEXES, size=n)
    birth = rng.integers(1947, 1974, size=n)
    weight = rng.uniform(0.5, 3.0, size=n)
    earnings = {}
    for year in ec.WINDOW_YEARS:
        draw = rng.lognormal(10.3, 0.9, size=n)
        draw[rng.random(n) < 0.12] = 0.0
        earnings[f"e{year}"] = np.minimum(np.round(draw, -2), CAP[year])
    return pd.DataFrame(
        {
            "person_id": np.arange(n) + 1,
            "sex": sex,
            "birth_year": birth,
            "weight": weight,
            **earnings,
        }
    )


def _cells(frame, mask=None):
    return ec.WindowArrays(frame, wage_bases=WAGE_BASES).cells(mask)


# --- weighted Spearman ----------------------------------------------------


@settings(max_examples=150, deadline=None)
@given(
    data=st.lists(
        st.tuples(st.integers(0, 12), st.integers(0, 12), st.integers(1, 4)),
        min_size=4,
        max_size=40,
    )
)
def test_unit_weight_spearman_matches_scipy(data):
    x = np.array([row[0] for row in data], dtype=float)
    y = np.array([row[1] for row in data], dtype=float)
    ours = ec.weighted_spearman(x, y, np.ones(len(x)))
    theirs = spearmanr(x, y).statistic
    if np.isnan(theirs):
        assert np.isnan(ours)
    else:
        assert ours == pytest.approx(theirs, abs=1e-12)


@settings(max_examples=150, deadline=None)
@given(
    data=st.lists(
        st.tuples(st.integers(0, 12), st.integers(0, 12), st.integers(1, 4)),
        min_size=4,
        max_size=30,
    )
)
def test_integer_weights_equal_repeated_rows(data):
    x = np.array([row[0] for row in data], dtype=float)
    y = np.array([row[1] for row in data], dtype=float)
    w = np.array([row[2] for row in data])
    weighted = ec.weighted_spearman(x, y, w.astype(float))
    repeated = ec.weighted_spearman(
        np.repeat(x, w), np.repeat(y, w), np.ones(int(w.sum()))
    )
    if np.isnan(repeated):
        assert np.isnan(weighted)
    else:
        assert weighted == pytest.approx(repeated, abs=1e-12)


@settings(max_examples=100, deadline=None)
@given(seed=st.integers(0, 10_000))
def test_spearman_is_bounded_and_invariant_to_increasing_transforms(seed):
    rng = np.random.default_rng(seed)
    x, y = rng.normal(size=50), rng.normal(size=50)
    w = rng.uniform(0.5, 2, size=50)
    rho = ec.weighted_spearman(x, y, w)
    assert -1 <= rho <= 1
    assert ec.weighted_spearman(np.exp(x), 3 * y + 7, w) == pytest.approx(
        rho, abs=1e-12
    )
    assert ec.weighted_spearman(x, y, 5 * w) == pytest.approx(rho, abs=1e-12)


def test_spearman_is_nan_without_variation_or_pairs():
    ones = np.ones(5)
    assert np.isnan(ec.weighted_spearman(ones, np.arange(5.0), ones))
    assert np.isnan(ec.weighted_spearman(ones[:2], ones[:2], ones[:2]))


# --- window cells ---------------------------------------------------------


def test_worked_window_cells_for_one_band():
    cap98, cap04 = CAP[1998], CAP[2004]
    frame = _frame(
        [
            # positive throughout, at the maximum in 1998 and 2004
            ("men", 1950, 1.0, cap98, 50_000, 50_000, cap04),
            # an interior zero
            ("men", 1950, 2.0, 30_000, 0, 20_000, 40_000),
            # zero in 1998, positive in 2004
            ("men", 1950, 1.0, 0, 10_000, 10_000, 20_000),
            # at the maximum in 2004 only
            ("men", 1950, 1.0, 40_000, 40_000, 40_000, cap04),
            # no earnings in 2004
            ("men", 1950, 5.0, 10_000, 10_000, 10_000, 0),
        ]
    )
    cells = _cells(frame)
    # positive in 1998 and 2004: persons 1, 2, 4 (weights 1, 2, 1)
    assert cells["zint.men.c0"].value == pytest.approx(2 / 4)
    assert cells["zint.men.c0"].n == 3
    assert cells["zint.men.c0"].events == 1
    # positive in 2004: persons 1-4 (weights 1, 2, 1, 1); any earlier zero: 2, 3
    assert cells["d_anyzero.men.c0"].value == pytest.approx(3 / 5)
    # positive person-years: 4 + 3 + 3 + 4 + 3 = 17; at max: 2 + 1 = 3
    assert cells["q_atmax.men.c0"].n == 17
    # weights: at max 1 + 1 + 1 = 3 over 4*1 + 3*2 + 3*1 + 4*1 + 3*5 = 32
    assert cells["q_atmax.men.c0"].value == pytest.approx(3 / 32)
    # at max in 2004: persons 1 and 4; also at max in 1998: person 1
    assert cells["mpers.men.c0"].value == pytest.approx(1 / 2)
    assert cells["r6.men.c0"].n == 3


def test_sex_level_cell_is_the_mean_of_its_three_bands():
    frame = _random_frame(np.random.default_rng(1))
    cells = _cells(frame)
    for stat in ec.STATISTICS:
        for sex in ec.SEXES:
            bands = [cells[f"{stat}.{sex}.{band}"] for band in ec.COHORT_BANDS]
            assert cells[f"{stat}.{sex}"].value == pytest.approx(
                np.mean([cell.value for cell in bands])
            )
            assert cells[f"{stat}.{sex}"].events == sum(
                cell.events for cell in bands
            )
    assert cells["q_sexratio"].value == pytest.approx(
        cells["q_atmax.men"].value / cells["q_atmax.women"].value
    )


def test_cell_ids_match_what_is_computed():
    cells = _cells(_random_frame(np.random.default_rng(2)))
    assert sorted(cells) == sorted(ec.cell_ids())
    assert len(ec.cell_ids()) == 5 * 2 * 3 + 5 * 2 + 1
    assert {ec.metric(cell_id) for cell_id in cells} == {
        "abs_gap",
        "log_ratio",
    }


@settings(max_examples=40, deadline=None)
@given(seed=st.integers(0, 10_000), scale=st.floats(0.1, 50))
def test_cells_ignore_weight_scale_and_row_order(seed, scale):
    rng = np.random.default_rng(seed)
    frame = _random_frame(rng, n=300)
    base = _cells(frame)
    scaled = frame.assign(weight=frame["weight"] * scale)
    shuffled = frame.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    for other in (_cells(scaled), _cells(shuffled)):
        for cell_id, cell in base.items():
            if np.isnan(cell.value):
                assert np.isnan(other[cell_id].value)
            else:
                assert other[cell_id].value == pytest.approx(
                    cell.value, rel=1e-9, abs=1e-12
                )
            assert other[cell_id].events == cell.events


@settings(max_examples=40, deadline=None)
@given(seed=st.integers(0, 10_000))
def test_shares_and_correlations_stay_in_range(seed):
    cells = _cells(_random_frame(np.random.default_rng(seed), n=300))
    for cell_id, cell in cells.items():
        if np.isnan(cell.value) or cell_id == "q_sexratio":
            continue
        low = -1.0 if cell_id.startswith("r6") else 0.0
        assert low <= cell.value <= 1.0
        assert 0 <= cell.events <= cell.n


def test_mask_selects_persons():
    frame = _random_frame(np.random.default_rng(3))
    mask = np.arange(len(frame)) % 2 == 0
    masked = _cells(frame, mask)
    subset = _cells(frame[mask].reset_index(drop=True))
    for cell_id, cell in subset.items():
        assert masked[cell_id].events == cell.events
        if not np.isnan(cell.value):
            assert masked[cell_id].value == pytest.approx(cell.value)


def test_window_frame_fills_absent_years_with_zero_and_checks_units():
    persons = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4],
            "sex": ["men", "women", "men", None],
            "birth_year": [1950, 1960, 1930, 1950],
            "weight": [1.0, 1.0, 1.0, 1.0],
        }
    )
    earnings = pd.DataFrame(
        {
            "person_id": [1, 1, 2, 3],
            "year": [1998, 2004, 2000, 1998],
            "earnings": [100.0, 200.0, 300.0, 400.0],
        }
    )
    frame = ec.window_frame(earnings, persons, wage_bases=WAGE_BASES)
    assert frame["person_id"].tolist() == [1, 2]  # 3 out of band, 4 uncoded
    assert frame.loc[0, _columns()].tolist() == [100.0, 0.0, 0.0, 200.0]
    assert frame.loc[1, _columns()].tolist() == [0.0, 300.0, 0.0, 0.0]
    over = earnings.assign(earnings=1e6)
    with pytest.raises(ValueError, match="epuf_measure"):
        ec.window_frame(over, persons, wage_bases=WAGE_BASES)


def test_transform_is_log_for_shares_and_identity_for_correlations():
    assert ec.transform("r6.men", 0.7) == 0.7
    assert ec.transform("zint.men", 0.05) == pytest.approx(np.log(0.05))
    assert np.isnan(ec.transform("zint.men", 0.0))
    assert np.isnan(ec.transform("q_sexratio", float("nan")))


# --- career cells ---------------------------------------------------------

YEARS = np.arange(1951, 2007)


def test_mask_zeroes_before_1968_and_fills_odd_years_from_1997():
    history = np.arange(1.0, len(YEARS) + 1)[None, :] * 100
    masked = ec.mask_as_career_assembler(history, YEARS)
    assert (masked[0, YEARS < 1968] == 0).all()
    untouched = (YEARS >= 1968) & ~((YEARS >= 1997) & (YEARS % 2 == 1))
    assert (masked[0, untouched] == history[0, untouched]).all()
    for year in (1997, 1999, 2001, 2003, 2005):
        index = year - 1951
        assert (
            masked[0, index]
            == (history[0, index - 1] + history[0, index + 1]) / 2
        )


def test_career_zero_years_and_at_max_shares():
    birth = np.array([1940, 1940])
    histories = np.zeros((2, len(YEARS)))
    # person 0: at the wage base every year of ages 22-61 (1962-2001)
    for year in range(1962, 2002):
        histories[0, year - 1951] = WAGE_BASES[year]
    # person 1: earnings only at ages 30-39
    histories[1, 1970 - 1951 : 1980 - 1951] = 1_000.0
    cells = ec.career_cells(
        histories,
        YEARS,
        birth,
        wage_bases=WAGE_BASES,
        nawi=captured_ssa_parameters().nawi,
    )
    assert cells["zero_years"]["mean"] == pytest.approx((0 + 30) / 2)
    assert cells["zero_years"]["share_10_or_more"] == 0.5
    assert cells["zero_years"]["share_all_40"] == 0.0
    assert cells["at_max_by_age"]["35-44"]["share_at_max"] == pytest.approx(
        10 / 15
    )
    assert cells["at_max_by_age"]["45-54"]["share_at_max"] == 1.0


@settings(max_examples=60, deadline=None)
@given(seed=st.integers(0, 10_000), birth=st.integers(1930, 1944))
def test_career_aime_matches_the_statutory_oracle(seed, birth):
    rng = np.random.default_rng(seed)
    history = np.where(
        rng.random(len(YEARS)) < 0.25,
        0.0,
        np.minimum(
            rng.lognormal(9.0, 1.0, size=len(YEARS)),
            [WAGE_BASES[year] for year in YEARS],
        ),
    )
    params = captured_ssa_parameters()
    cells = ec.career_cells(
        history[None, :],
        YEARS,
        np.array([birth]),
        wage_bases=WAGE_BASES,
        nawi=params.nawi,
    )
    through_61 = {
        int(year): float(value)
        for year, value in zip(YEARS, history, strict=True)
        if birth + 22 <= year <= birth + 61
    }
    expected = statutory_aime.aime(through_61, birth, params)
    assert cells["aime_35yr_through_age_61"]["p50"] == expected


def test_career_window_outside_the_years_is_refused():
    with pytest.raises(ValueError, match="outside the supplied years"):
        ec.career_cells(
            np.zeros((1, len(YEARS))),
            YEARS,
            np.array([1920]),
            wage_bases=WAGE_BASES,
            nawi=captured_ssa_parameters().nawi,
        )
