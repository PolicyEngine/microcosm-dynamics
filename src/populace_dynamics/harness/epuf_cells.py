"""Cell statistics shared by EPUF, real PSID and candidate histories.

Two families of cells, each computed by ONE function whatever the
source, so a difference between sources can never be a difference of
definition.

**Window cells** (tranche G of the proposed EPUF gate). The support is
persons with earnings histories at the four even reference years
1998, 2000, 2002 and 2004, in EPUF's capped, disclosed units
(:mod:`populace_dynamics.harness.epuf_operator`), by sex and three
birth-cohort bands (1947-1955, 1956-1964, 1965-1973). The five
statistics:

- ``r6``: weighted Spearman rank correlation between 1998 and 2004
  earnings, among persons positive in both years.
- ``zint``: among persons positive in 1998 and in 2004, the weighted
  share with no earnings in 2000 or in 2002.
- ``d_anyzero``: among persons positive in 2004, the weighted share with
  no earnings in at least one of 1998, 2000 and 2002.
- ``q_atmax``: among positive person-years of the four years, the
  weighted share exactly at the year's wage base.
- ``mpers``: among persons at the wage base in 2004, the weighted share
  also at the wage base in 1998.

Each statistic conditions on covered earnings at one or both ends of
its span. EPUF records no deaths, departures or arrivals, so an EPUF
person-year with no earnings may be a year after death or abroad; a
person with earnings at the end of a span was alive and in covered work
then. A sex-level cell is the unweighted mean of its three cohort-band
values, which fixes the cohort composition at one-third each on every
side. ``q_sexratio`` is men's ``q_atmax`` over women's.

**Career cells** (tranche R, report only). The original four career
statistics, on annual capped histories from age 22 to 61 for birth
cohorts whose whole window lies inside 1951-2006: years without
earnings, 10-year rank correlations, the share at the wage base by age
band, and the AIME under the 35-year rule.
:func:`mask_as_career_assembler` rewrites an annual history the way the
repository's career assembler builds a PSID career
(:func:`populace_dynamics.estimates.career.build_career`): nothing
before 1968, and each odd year from 1997 filled with the mean of its
two neighbours.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = [
    "CAREER_AGES",
    "CAREER_COHORT_BANDS",
    "COHORT_BANDS",
    "CellValue",
    "METRIC_OF",
    "SEXES",
    "STATISTICS",
    "WINDOW_YEARS",
    "WindowArrays",
    "career_cells",
    "cell_ids",
    "mask_as_career_assembler",
    "metric",
    "transform",
    "weighted_spearman",
    "window_frame",
]

WINDOW_YEARS: tuple[int, ...] = (1998, 2000, 2002, 2004)
SEXES: tuple[str, ...] = ("men", "women")
COHORT_BANDS: dict[str, tuple[int, int]] = {
    "c0": (1947, 1955),
    "c1": (1956, 1964),
    "c2": (1965, 1973),
}
STATISTICS: tuple[str, ...] = (
    "r6",
    "zint",
    "d_anyzero",
    "q_atmax",
    "mpers",
)
#: How a cell's distance from EPUF is measured: the absolute gap of a
#: rank correlation, or the log ratio of a share.
METRIC_OF: dict[str, str] = {
    "r6": "abs_gap",
    "zint": "log_ratio",
    "d_anyzero": "log_ratio",
    "q_atmax": "log_ratio",
    "mpers": "log_ratio",
    "q_sexratio": "log_ratio",
}

CAREER_AGES: tuple[int, int] = (22, 61)
CAREER_COHORT_BANDS: dict[str, tuple[int, int]] = {
    "1930-1934": (1930, 1934),
    "1935-1939": (1935, 1939),
    "1940-1944": (1940, 1944),
}
_CAREER_PAIRS: tuple[tuple[int, int], ...] = ((1980, 1990), (1994, 2004))
_CAREER_AGE_BANDS: tuple[tuple[int, int], ...] = (
    (25, 34),
    (35, 44),
    (45, 54),
    (55, 61),
)
_COMPUTATION_YEARS = 35


@dataclass(frozen=True)
class CellValue:
    """One cell: its value on the natural scale and its event counts.

    ``events`` is the count the minimum-events rule reads: for a share,
    the smaller of the unweighted numerator and its complement; for a
    correlation, the number of pairs; for a ratio of two shares, the
    smaller of the two shares' events.
    """

    value: float
    events: int
    n: int


def cell_ids() -> list[str]:
    """Every window cell id: band-level, sex-level and the sex ratio."""
    ids = [
        f"{stat}.{sex}.{band}"
        for stat in STATISTICS
        for sex in SEXES
        for band in COHORT_BANDS
    ]
    ids += [f"{stat}.{sex}" for stat in STATISTICS for sex in SEXES]
    return [*ids, "q_sexratio"]


def metric(cell_id: str) -> str:
    """The metric of a cell id."""
    return METRIC_OF[cell_id.split(".")[0]]


def transform(cell_id: str, value: float) -> float:
    """Put a cell value on its metric's scale (log for shares)."""
    if metric(cell_id) == "abs_gap":
        return float(value)
    if not np.isfinite(value) or value <= 0.0:
        return float("nan")
    return float(np.log(value))


def _weighted_midranks(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    sorted_weights = weights[order]
    starts = np.flatnonzero(
        np.r_[True, sorted_values[1:] != sorted_values[:-1]]
    )
    group_weight = np.add.reduceat(sorted_weights, starts)
    below = np.cumsum(group_weight) - group_weight
    group_rank = below + 0.5 * group_weight
    counts = np.diff(np.r_[starts, len(sorted_values)])
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.repeat(group_rank, counts)
    return ranks


def weighted_spearman(
    x: np.ndarray, y: np.ndarray, weights: np.ndarray
) -> float:
    """Weighted Pearson correlation of weighted mid-ranks.

    With unit weights this is Spearman's rho with average ranks for ties.
    Returns NaN when either variable is constant or fewer than three
    pairs remain.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if len(x) < 3:
        return float("nan")
    rank_x = _weighted_midranks(x, weights)
    rank_y = _weighted_midranks(y, weights)
    total = weights.sum()
    dx = rank_x - (weights * rank_x).sum() / total
    dy = rank_y - (weights * rank_y).sum() / total
    var_x = (weights * dx * dx).sum()
    var_y = (weights * dy * dy).sum()
    if var_x <= 0.0 or var_y <= 0.0:
        return float("nan")
    return float((weights * dx * dy).sum() / np.sqrt(var_x * var_y))


def window_frame(
    earnings: pd.DataFrame,
    persons: pd.DataFrame,
    *,
    wage_bases: Mapping[int, float],
) -> pd.DataFrame:
    """One row per person: the four window years side by side.

    ``earnings`` is long (``person_id``, ``year``, ``earnings``), already
    in EPUF units; a person-year absent from it has zero earnings.
    ``persons`` has ``person_id``, ``sex`` (``"men"`` / ``"women"``),
    ``birth_year`` and ``weight`` and defines who is in the frame;
    persons outside the cohort bands are dropped. ``wage_bases`` maps
    each window year to its wage base.
    """
    lo = min(low for low, _ in COHORT_BANDS.values())
    hi = max(high for _, high in COHORT_BANDS.values())
    frame = persons.loc[
        persons["sex"].isin(SEXES) & persons["birth_year"].between(lo, hi),
        ["person_id", "sex", "birth_year", "weight"],
    ].copy()
    if frame["person_id"].duplicated().any():
        raise ValueError("persons has duplicate person_id")
    rows = earnings.loc[
        earnings["year"].isin(WINDOW_YEARS)
        & earnings["person_id"].isin(frame["person_id"])
    ]
    if rows.duplicated(["person_id", "year"]).any():
        raise ValueError("earnings has duplicate person-years")
    wide = rows.pivot(index="person_id", columns="year", values="earnings")
    frame = frame.set_index("person_id")
    for year in WINDOW_YEARS:
        column = (
            wide[year].reindex(frame.index)
            if year in wide.columns
            else pd.Series(np.nan, index=frame.index)
        )
        values = column.fillna(0.0).to_numpy(dtype=np.float64)
        cap = float(wage_bases[year])
        if (values < 0).any() or (values > cap).any():
            raise ValueError(
                f"{year} earnings fall outside [0, {cap:,.0f}]; apply "
                "epuf_measure first"
            )
        frame[f"e{year}"] = values
    return frame.reset_index()


class WindowArrays:
    """A window frame as arrays, for cells on any subset of its persons."""

    def __init__(
        self, frame: pd.DataFrame, *, wage_bases: Mapping[int, float]
    ) -> None:
        self.person_id = frame["person_id"].to_numpy()
        self.weight = frame["weight"].to_numpy(dtype=np.float64)
        if (self.weight <= 0).any():
            raise ValueError("window weights must be positive")
        sex = frame["sex"].to_numpy()
        self.sex = np.where(sex == SEXES[0], 0, 1)
        birth = frame["birth_year"].to_numpy()
        self.band = np.full(len(frame), -1)
        for index, (low, high) in enumerate(COHORT_BANDS.values()):
            self.band[(birth >= low) & (birth <= high)] = index
        if (self.band < 0).any():
            raise ValueError("a person lies outside the cohort bands")
        self.earnings = np.column_stack(
            [frame[f"e{year}"].to_numpy(np.float64) for year in WINDOW_YEARS]
        )
        caps = np.array([float(wage_bases[y]) for y in WINDOW_YEARS])
        self.positive = self.earnings > 0.0
        self.at_max = self.earnings == caps

    def __len__(self) -> int:
        return len(self.person_id)

    @staticmethod
    def _share(weight, numerator, denominator) -> CellValue:
        n = int(denominator.sum())
        hits = int((numerator & denominator).sum())
        total = weight[denominator].sum()
        value = (
            float(weight[numerator & denominator].sum() / total)
            if total > 0
            else float("nan")
        )
        return CellValue(value, min(hits, n - hits), n)

    def _band_cells(self, select: np.ndarray) -> dict[str, CellValue]:
        weight = self.weight
        positive = self.positive
        at_max = self.at_max
        both = select & positive[:, 0] & positive[:, 3]
        r6 = CellValue(
            weighted_spearman(
                self.earnings[both, 0], self.earnings[both, 3], weight[both]
            ),
            int(both.sum()),
            int(both.sum()),
        )
        interior_zero = ~positive[:, 1] | ~positive[:, 2]
        zint = self._share(weight, interior_zero, both)
        any_zero = ~positive[:, 0] | interior_zero
        d_anyzero = self._share(weight, any_zero, select & positive[:, 3])
        years = positive.shape[1]
        stacked_weight = np.tile(weight, years)
        q_atmax = self._share(
            stacked_weight,
            at_max.T.ravel(),
            (positive & select[:, None]).T.ravel(),
        )
        mpers = self._share(weight, at_max[:, 0], select & at_max[:, 3])
        return {
            "r6": r6,
            "zint": zint,
            "d_anyzero": d_anyzero,
            "q_atmax": q_atmax,
            "mpers": mpers,
        }

    def cells(self, mask: np.ndarray | None = None) -> dict[str, CellValue]:
        """Every window cell on the persons selected by ``mask``."""
        mask = np.ones(len(self), dtype=bool) if mask is None else mask
        out: dict[str, CellValue] = {}
        for sex_index, sex in enumerate(SEXES):
            by_band: dict[str, list[CellValue]] = {s: [] for s in STATISTICS}
            for band_index, band in enumerate(COHORT_BANDS):
                select = (
                    mask & (self.sex == sex_index) & (self.band == band_index)
                )
                for stat, cell in self._band_cells(select).items():
                    out[f"{stat}.{sex}.{band}"] = cell
                    by_band[stat].append(cell)
            for stat, cells in by_band.items():
                out[f"{stat}.{sex}"] = CellValue(
                    float(np.mean([cell.value for cell in cells])),
                    int(sum(cell.events for cell in cells)),
                    int(sum(cell.n for cell in cells)),
                )
        men = out[f"q_atmax.{SEXES[0]}"]
        women = out[f"q_atmax.{SEXES[1]}"]
        ratio = (
            men.value / women.value
            if women.value and np.isfinite(women.value)
            else float("nan")
        )
        out["q_sexratio"] = CellValue(
            float(ratio), min(men.events, women.events), men.n + women.n
        )
        return out


# --- career cells (tranche R, report only) -------------------------------


def mask_as_career_assembler(
    earnings: np.ndarray, years: Sequence[int], birth_year: np.ndarray
) -> np.ndarray:
    """Rewrite annual histories the way the career assembler builds one.

    ``earnings`` is persons by years. Each person's years before
    ``max(1968, birth_year + 22)`` become zero (the assembler's careers
    start there and count earlier years as zero), and each odd year from
    1997 becomes the mean of its two neighbours (the assembler's
    structural-gap rule, which fills the years the biennial PSID did not
    collect). A filled odd year whose neighbours are both zero stays
    zero.
    """
    years = np.asarray(years)
    birth_year = np.asarray(birth_year)
    out = np.asarray(earnings, dtype=np.float64).copy()
    start = np.maximum(1968, birth_year + 22)
    out[years[None, :] < start[:, None]] = 0.0
    position = {int(year): index for index, year in enumerate(years)}
    for year in years[(years >= 1997) & (years % 2 == 1)]:
        left = position.get(int(year) - 1)
        right = position.get(int(year) + 1)
        if left is None or right is None:
            raise ValueError(f"{year} lacks a neighbour year to fill from")
        out[:, position[int(year)]] = (out[:, left] + out[:, right]) / 2.0
    return out


def _quantiles(values: np.ndarray, qs=(0.25, 0.5, 0.75, 0.9)) -> dict:
    return {f"p{int(q * 100)}": float(np.quantile(values, q)) for q in qs}


def career_cells(
    earnings: np.ndarray,
    years: Sequence[int],
    birth_year: np.ndarray,
    *,
    wage_bases: Mapping[int, float],
    nawi: Mapping[int, float],
) -> dict[str, object]:
    """The four career statistics for one sex and cohort band.

    ``earnings`` is persons by years of capped annual earnings, unweighted
    (EPUF is a simple random sample; a weighted source passes replicated
    or pre-weighted rows). Every person's ages 22-61 must lie inside
    ``years``, which must start in 1951 or later; the AIME ranks every
    supplied year through age 61.
    """
    years = np.asarray(years)
    earnings = np.asarray(earnings, dtype=np.float64)
    birth_year = np.asarray(birth_year)
    n = len(birth_year)
    first_age, last_age = CAREER_AGES
    span = last_age - first_age + 1
    start = birth_year + first_age - years[0]
    if (start < 0).any() or (start + span > len(years)).any():
        raise ValueError("a career window falls outside the supplied years")
    columns = start[:, None] + np.arange(span)[None, :]
    rows = np.arange(n)[:, None]
    window = earnings[rows, columns]
    window_years = years[columns]
    caps = np.vectorize(lambda y: float(wage_bases[int(y)]))(window_years)
    positive = window > 0.0

    zero_years = (~positive).sum(axis=1)
    out: dict[str, object] = {
        "n_persons": int(n),
        "zero_years": {
            "mean": float(zero_years.mean()),
            **_quantiles(zero_years),
            "share_10_or_more": float((zero_years >= 10).mean()),
            "share_all_40": float((zero_years == span).mean()),
        },
    }

    position = {int(year): index for index, year in enumerate(years)}
    rank = {}
    for first, second in _CAREER_PAIRS:
        a = earnings[:, position[first]]
        b = earnings[:, position[second]]
        both = (a > 0) & (b > 0)
        rank[f"{first}_{second}"] = {
            "spearman": weighted_spearman(
                a[both], b[both], np.ones(int(both.sum()))
            ),
            "n_pairs": int(both.sum()),
        }
    out["rank_persistence_10yr"] = rank

    ages = first_age + np.arange(span)
    at_max = window == caps
    by_age = {}
    for low, high in _CAREER_AGE_BANDS:
        in_band = (ages >= low) & (ages <= high)
        denominator = positive[:, in_band].sum()
        by_age[f"{low}-{high}"] = {
            "share_at_max": (
                float(at_max[:, in_band].sum() / denominator)
                if denominator
                else float("nan")
            ),
            "n_positive_person_years": int(denominator),
        }
    out["at_max_by_age"] = by_age

    # The AIME ranks every year after 1950 through the cutoff (age 61),
    # including years before age 22 (42 USC 415(b)(2)); the number of
    # computation years is 35 for every cohort here (born 1929 or later).
    cutoff = birth_year + last_age
    through = years[None, :] <= cutoff[:, None]
    index_year = birth_year + 60
    index_value = np.vectorize(lambda y: float(nawi[int(y)]))(index_year)
    year_value = np.array([float(nawi[int(y)]) for y in years])
    factor = np.where(
        years[None, :] < index_year[:, None],
        index_value[:, None] / year_value[None, :],
        1.0,
    )
    indexed = np.where(through, earnings * factor, 0.0)
    top = np.sort(indexed, axis=1)[:, -_COMPUTATION_YEARS:]
    aime = np.floor(top.sum(axis=1) / (_COMPUTATION_YEARS * 12))
    out["aime_35yr_through_age_61"] = {
        **_quantiles(aime),
        "mean": float(aime.mean()),
        "share_zero": float((aime == 0).mean()),
    }
    return out
