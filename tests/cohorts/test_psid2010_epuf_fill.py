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
        odd_years=None,
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

    result = fill_module.fill_careers(
        cohort, odd_fill=Spy(), seed=1, odd_years=None
    )
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


def test_by_default_only_the_scored_gap_years_are_filled():
    cohort = _cohort()

    class Constant:
        name = "constant"

        def fill(self, shares, years, birth, sex, key, mask, seed):
            out = shares.copy()
            out[mask] = 0.25
            return out

    result = fill_module.fill_careers(cohort, odd_fill=Constant(), seed=1)
    after = result.careers.set_index(["person_id", "year"])
    before = cohort.careers.set_index(["person_id", "year"])
    gaps = before.index[before["provenance"] == "gap_imputed"]
    for key in gaps:
        if key[1] in fill_module.SCORED_ODD_YEARS:
            assert after.loc[key, "provenance"] == "gap_epuf_drawn"
        else:
            # 2007 and 2009 keep the assembler's value and provenance.
            assert after.loc[key, "provenance"] == "gap_imputed"
            assert after.loc[key, "earnings"] == before.loc[key, "earnings"]


def test_a_gap_with_no_visible_neighbour_keeps_the_assemblers_value():
    cohort = _cohort()
    careers = cohort.careers
    # Person 3 (born 1975) starts in 1997; drop 1998 so 1997's only
    # neighbours are pre-career (1996) or missing.
    careers = careers[~((careers.person_id == 3) & (careers.year == 1998))]
    # Person 1 gets a 2013 seam filled from a 2014 boundary year, with no
    # 2012 row: neither neighbour is visible to a fill.
    extra = pd.DataFrame(
        [
            (1, 2013, 30_000.0, "gap_imputed"),
            (1, 2014, 30_000.0, "boundary_2014"),
        ],
        columns=careers.columns,
    )
    cohort = SimpleNamespace(
        persons=cohort.persons,
        careers=pd.concat([careers, extra], ignore_index=True),
    )

    class Constant:
        name = "constant"

        def fill(self, shares, years, birth, sex, key, mask, seed):
            out = shares.copy()
            out[mask] = 0.25
            return out

    result = fill_module.fill_careers(
        cohort, odd_fill=Constant(), seed=1, odd_years=None
    )
    after = result.careers.set_index(["person_id", "year"])
    assert after.loc[(3, 1997), "provenance"] == "gap_imputed"
    assert after.loc[(1, 2013), "provenance"] == "gap_imputed"
    assert after.loc[(1, 2013), "earnings"] == 30_000.0
    assert after.loc[(1, 2014), "provenance"] == "boundary_2014"
    assert after.loc[(1, 1999), "provenance"] == "gap_epuf_drawn"
