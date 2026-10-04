"""Learned EPUF fills applied to a PSID-2010-shaped cohort (synthetic)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from populace_dynamics.cohorts import psid2010_epuf_fill as fill_module
from populace_dynamics.harness import epuf_fill_gate as g

BIRTHS = {1: (1950, "male"), 2: (1960, "female"), 3: (1975, "male")}


def _cohort():
    caps = fill_module._wage_bases(np.arange(1951, 2011))
    rows = []
    for pid, (birth, _) in BIRTHS.items():
        start = max(1968, birth + 22)
        for year in range(start, 2011):
            cap = caps[year - 1951]
            if year >= 1997 and year % 2 == 1:
                continue
            rows.append((pid, year, 0.3 * cap * (1 + 0.01 * pid), "observed"))
        for year in range(max(start, 1997), 2011):
            if year % 2 == 1:
                left = [r for r in rows if r[0] == pid and r[1] == year - 1]
                right = [r for r in rows if r[0] == pid and r[1] == year + 1]
                if left and right:
                    mean = (left[0][2] + right[0][2]) / 2
                else:
                    mean = (left or right)[0][2]
                rows.append((pid, year, mean, "gap_imputed"))
    careers = pd.DataFrame(
        rows, columns=["person_id", "year", "earnings", "provenance"]
    ).sort_values(["person_id", "year"])
    persons = pd.DataFrame(
        {
            "person_id": list(BIRTHS),
            "birth_year": [b for b, _ in BIRTHS.values()],
            "sex": [s for _, s in BIRTHS.values()],
        }
    )
    return SimpleNamespace(persons=persons, careers=careers)


class _MeanFill:
    """The assembler's neighbour mean, in dollars, on SSA's wage bases."""

    name = "neighbour_mean"

    def fill(self, shares, years, birth, sex, key, mask, seed):
        caps = fill_module._wage_bases(np.asarray(years))
        dollars = shares * caps[None, :]
        out = shares.copy()
        for column in np.flatnonzero(mask.any(axis=0)):
            left = dollars[:, column - 1]
            right = dollars[:, column + 1]
            mean = np.where(
                np.isnan(left),
                right,
                np.where(np.isnan(right), left, (left + right) / 2),
            )
            rows = mask[:, column]
            out[rows, column] = np.minimum(
                np.nan_to_num(mean[rows]) / caps[column], 1.0
            )
        return out


def test_current_rule_fills_reproduce_the_assembler():
    cohort = _cohort()
    result = fill_module.fill_careers(
        cohort,
        odd_fill=_MeanFill(),
        pre_fill=g.CurrentPreFill(),
        seed=7100,
    )
    careers = result.careers
    before = cohort.careers.set_index(["person_id", "year"])
    after = careers.set_index(["person_id", "year"])
    gap = before["provenance"] == "gap_imputed"
    # Neighbours below the cap: the learned path's neighbour mean (in
    # dollars, capped) is the assembler's mean.
    np.testing.assert_allclose(
        after.loc[before.index[gap], "earnings"],
        before.loc[gap, "earnings"],
        rtol=1e-9,
    )
    assert (
        after.loc[before.index[gap], "provenance"]
        == fill_module.EPUFFillProvenance.GAP_EPUF_DRAWN.value
    ).all()
    observed = before["provenance"] == "observed"
    pd.testing.assert_series_equal(
        after.loc[before.index[observed], "earnings"],
        before.loc[observed, "earnings"],
        check_names=False,
    )
    pre = careers[
        careers["provenance"]
        == fill_module.EPUFFillProvenance.PRE_CAREER_EPUF_DONOR.value
    ]
    for pid, (birth, _) in BIRTHS.items():
        years = pre.loc[pre["person_id"] == pid, "year"].tolist()
        assert years == list(range(1951, max(1968, birth + 22)))
    assert (pre["earnings"] == 0).all()
    assert result.fills == {
        "odd": "neighbour_mean",
        "pre": "current_pre_career_rule",
    }


def test_fills_see_no_pre_career_or_gap_year():
    cohort = _cohort()
    seen = {}

    class Spy:
        name = "spy"

        def fill(self, shares, years, birth, sex, key, mask, seed):
            seen["shares"] = shares.copy()
            seen["mask"] = mask.copy()
            out = shares.copy()
            out[mask] = 0.25
            return out

    result = fill_module.fill_careers(cohort, odd_fill=Spy(), seed=1)
    years = np.arange(1951, 2011)
    birth = np.array([b for b, _ in BIRTHS.values()])
    pre = years[None, :] < np.maximum(1968, birth + 22)[:, None]
    assert np.isnan(seen["shares"][pre]).all()
    assert np.isnan(seen["shares"][seen["mask"]]).all()
    assert (seen["shares"][~pre & ~seen["mask"]] <= 1).all()
    drawn = result.careers[result.careers["provenance"] == "gap_epuf_drawn"]
    caps = fill_module._wage_bases(drawn["year"].to_numpy())
    np.testing.assert_allclose(drawn["earnings"], 0.25 * caps)
    assert len(result.content_sha256) == 64


def test_an_invalid_fill_is_refused():
    class Bad:
        def fill(self, shares, years, birth, sex, key, mask, seed):
            out = shares.copy()
            out[mask] = 1.5
            return out

    with pytest.raises(ValueError, match="invalid share"):
        fill_module.fill_careers(_cohort(), odd_fill=Bad(), seed=1)


def test_no_fill_keeps_the_careers():
    cohort = _cohort()
    result = fill_module.fill_careers(cohort, seed=1)
    assert len(result.careers) == len(cohort.careers)
    assert result.fills == {}
