"""The learned EPUF career fills, on synthetic careers."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from populace_dynamics.estimates import epuf_fill as F
from populace_dynamics.harness import epuf_fill_gate as g

YEARS = np.asarray(g.YEARS)


def _shares(seed: int, n: int = 3_000):
    rng = np.random.default_rng(seed)
    birth = rng.integers(1925, 1981, size=n)
    sex = rng.choice([1, 2], size=n)
    level = rng.normal(-1.3, 0.7, size=n)
    walk = rng.normal(0, 0.25, size=(n, len(YEARS))).cumsum(axis=1) * 0.3
    shares = np.minimum(np.exp(level[:, None] + walk), 1.0)
    work = rng.random((n, len(YEARS))) < 0.85
    age = YEARS[None, :] - birth[:, None]
    shares = np.where(work & (age >= 15) & (age <= 85), shares, 0.0)
    return np.round(shares, 6), birth, sex, np.arange(n) + 1


def test_hash_uniform_is_keyed_and_order_free():
    keys = np.arange(1, 10_001)
    u = F.hash_uniform("s", 7, keys, 1999)
    assert ((u > 0) & (u < 1)).all()
    assert abs(u.mean() - 0.5) < 0.02
    np.testing.assert_array_equal(
        F.hash_uniform("s", 7, keys[::-1], 1999)[::-1], u
    )
    assert not np.array_equal(u, F.hash_uniform("s", 8, keys, 1999))
    assert not np.array_equal(u, F.hash_uniform("t", 7, keys, 1999))
    assert not np.array_equal(u, F.hash_uniform("s", 7, keys, 2001))


@pytest.fixture(scope="module")
def fitted():
    shares, birth, sex, key = _shares(1)
    unit_years = tuple(range(1991, 2006))
    return {
        "odd_forest": F.BySexFill.fit(
            F.OddForestFill,
            shares,
            YEARS,
            birth,
            sex,
            unit_years,
            key,
            n_units=40_000,
            n_trees=3,
            min_leaf=10,
            n_jobs=1,
        )[0],
        "odd_knn": F.OddKnnFill.fit(shares, YEARS, birth, sex, unit_years)[0],
        "pre_donor": F.PreDonorFill.fit(
            shares, YEARS, birth, sex, key, k=3, bank_size=500
        )[0],
        "pre_chain": F.PreChainFill.fit(
            shares, YEARS, birth, sex, tuple(range(1951, 2006))
        )[0],
    }


def _given(seed=2, n=800):
    shares, birth, sex, key = _shares(seed, n)
    given = np.where(g.union_mask(birth), np.nan, shares)
    return given, birth, sex, key + 10_000_000


@pytest.mark.parametrize(
    ("name", "family"),
    [
        ("odd_forest", "odd"),
        ("odd_knn", "odd"),
        ("pre_donor", "pre"),
        ("pre_chain", "pre"),
    ],
)
def test_fills_obey_the_scoring_contract(fitted, name, family):
    fill = fitted[name]
    given, birth, sex, key = _given()
    mask = g.family_mask(family, birth)
    out = fill.fill(given.copy(), YEARS, birth, sex, key, mask.copy(), 7100)
    assert np.isfinite(out[mask]).all()
    assert ((out[mask] >= 0) & (out[mask] <= 1)).all()
    same = (out[~mask] == given[~mask]) | (
        np.isnan(out[~mask]) & np.isnan(given[~mask])
    )
    assert same.all()
    again = fill.fill(given.copy(), YEARS, birth, sex, key, mask.copy(), 7100)
    np.testing.assert_array_equal(np.nan_to_num(out), np.nan_to_num(again))
    other = fill.fill(given.copy(), YEARS, birth, sex, key, mask.copy(), 7101)
    assert not np.array_equal(np.nan_to_num(out), np.nan_to_num(other))
    # A person's draw does not depend on the other persons' order.
    order = np.random.default_rng(0).permutation(len(birth))
    permuted = fill.fill(
        given[order].copy(),
        YEARS,
        birth[order],
        sex[order],
        key[order],
        mask[order].copy(),
        7100,
    )
    np.testing.assert_allclose(
        np.nan_to_num(permuted), np.nan_to_num(out[order])
    )


@pytest.mark.parametrize(
    "name", ["odd_forest", "odd_knn", "pre_donor", "pre_chain"]
)
def test_artifacts_round_trip_with_reproducible_bytes(fitted, name, tmp_path):
    fill = fitted[name]
    blob = fill.to_bytes()
    assert blob == fill.to_bytes()
    path = tmp_path / f"{name}.npz"
    path.write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    loaded = F.load_fill(path, sha256=sha)
    assert type(loaded) is type(fill)
    assert loaded.to_bytes() == blob
    with pytest.raises(ValueError, match="SHA-256"):
        F.load_fill(path, sha256="0" * 64)


def test_donor_blocks_come_from_the_bank(fitted):
    fill = fitted["pre_donor"]
    given, birth, sex, key = _given(3)
    mask = g.family_mask("pre", birth)
    out = fill.fill(given.copy(), YEARS, birth, sex, key, mask, 7100)
    donors = fill.donors(given, YEARS, birth, sex, key, mask, 7100)
    for row in np.flatnonzero(donors >= 0)[:50]:
        donor = donors[row]
        assert fill.bank_birth_year[donor] == birth[row]
        assert fill.bank_sex[donor] == sex[row]
        first = int(F.block_first_year(birth[row : row + 1])[0])
        block = fill.bank_block[donor].astype(float) / 65_535
        for offset in range(F.BLOCK_WIDTH):
            year = first + offset
            if year in YEARS and mask[row, year - YEARS[0]]:
                assert out[row, year - YEARS[0]] == pytest.approx(
                    block[offset]
                )
        early = (YEARS < first) & mask[row]
        assert (out[row, early] == 0).all()


def test_the_forest_copula_is_calibrated_by_band(fitted):
    for part in fitted["odd_forest"].parts.values():
        rho = part.rho
        assert rho.shape == (4, 6)
        assert ((rho >= 0) & (rho <= 0.9)).all()
