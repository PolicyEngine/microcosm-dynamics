"""Rules of gate_epuf_fill: career fills scored on held-out EPUF careers.

A gate here is a pass-or-fail test whose rules and thresholds are fixed
and published before anything is scored against it.

The career assembler (:func:`populace_dynamics.estimates.career.build_career`)
fills the years the PSID did not record with two fixed rules: each odd
income year from 1997 is the mean of its two neighbours, and nothing
counts before ``max(1968, birth_year + 22)``. This gate scores a
replacement for each rule on SSA's 2006 Earnings Public-Use File (EPUF;
:mod:`populace_dynamics.data.epuf`), which records every year's capped
taxable earnings from 1951 to 2006:

1. **Split.** EPUF persons are split once, by a salted SHA-256 of the
   person id, into TRAIN (60 percent; fills learn from it), DEV (20
   percent; floors and the checks on bite are built on it before lock)
   and TEST (20 percent; scored once per registered candidate, after
   lock). The split is person-disjoint and depends on nothing else.
2. **Mask.** Two families, masked separately, as the PSID would leave
   them: the odd years 1997-2005 (family ``odd``), and every year before
   ``max(1968, birth_year + 22)`` (family ``pre``).
3. **Impute and score.** A fill rewrites the masked years from the
   unmasked ones. Each cell is computed once on the true matrix and once
   on the filled matrix of the same persons; the gap is their difference
   on the cell's scale (:func:`gap`).
4. **Floor.** A cell's tolerance is ``K_TOLERANCE`` times the sampling
   standard error the cell carries at the PSID's size: the root mean
   square of ``[m(A) - m(B)] / sqrt(2)`` over replicate pairs of disjoint
   real DEV samples, each the size of the PSID's cell
   (:func:`floor_sigma`).

The masks, universes and statistics are defined here once and used for
the truth, every fill, the floors and the checks on bite, so a gap can
never be a difference of definition.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from populace_dynamics.harness.epuf_cells import CellValue, weighted_spearman

__all__ = [
    "AIME_QUANTILES",
    "DEV",
    "FIRST_YEAR",
    "K_TOLERANCE",
    "LAST_YEAR",
    "MASKED_ODD_YEARS",
    "ODD_AGE_BANDS",
    "ODD_AIME_COHORTS",
    "ODD_OBSERVED_YEARS",
    "PRE_CAREER_COHORTS",
    "REGISTRATION_ID",
    "SPLIT_SALT",
    "TEST",
    "TRAIN",
    "YEARS",
    "YOUTH_COHORTS",
    "aime_35",
    "cell_metric",
    "current_odd_fill",
    "current_pre_career_fill",
    "floor_sigma",
    "gap",
    "odd_cells",
    "odd_mask",
    "pre_career_cells",
    "pre_career_mask",
    "split_part",
]

REGISTRATION_ID = "2026-10-03-epuf-career-fill"

FIRST_YEAR = 1951
LAST_YEAR = 2006
YEARS: tuple[int, ...] = tuple(range(FIRST_YEAR, LAST_YEAR + 1))

#: The split: a person's position ``u`` in [0, 1) is the first eight bytes
#: of SHA-256(SPLIT_SALT + decimal person id), big-endian, over 2**64.
SPLIT_SALT = b"populace_dynamics.epuf_fill.split.v1|"
TRAIN, DEV, TEST = 0, 1, 2
_TRAIN_BELOW = 0.6
_DEV_BELOW = 0.8

#: The PSID's structural gap years that EPUF can score (the assembler also
#: fills 2007-2011 and the 2013 seam, past EPUF's last year).
MASKED_ODD_YEARS: tuple[int, ...] = (1997, 1999, 2001, 2003, 2005)
#: The even years around them, which the PSID records.
ODD_OBSERVED_YEARS: tuple[int, ...] = (1996, 1998, 2000, 2002, 2004, 2006)
#: Age at the masked year.
ODD_AGE_BANDS: dict[str, tuple[int, int]] = {
    "a18_29": (18, 29),
    "a30_44": (30, 44),
    "a45_59": (45, 59),
    "a60_74": (60, 74),
}
#: Cohorts whose AIME (35 years through age 61) includes masked odd years
#: and lies wholly inside 1951-2006.
ODD_AIME_COHORTS: dict[str, tuple[int, int]] = {
    "b1936_1940": (1936, 1940),
    "b1941_1945": (1941, 1945),
}
#: Cohorts whose masked pre-career years are 1951-1967 and whose AIME
#: lies wholly inside 1951-2006.
PRE_CAREER_COHORTS: dict[str, tuple[int, int]] = {
    "b1930_1934": (1930, 1934),
    "b1935_1939": (1935, 1939),
    "b1940_1945": (1940, 1945),
}
#: Cohorts for whom the rule removes only the years before age 22. The
#: PSID-2010 cohort's youngest members were born in 1980.
YOUTH_COHORTS: dict[str, tuple[int, int]] = {
    "b1946_1955": (1946, 1955),
    "b1956_1965": (1956, 1965),
    "b1966_1980": (1966, 1980),
}
AIME_QUANTILES: tuple[float, ...] = (0.25, 0.5, 0.75)
SEXES: dict[str, int] = {"men": 1, "women": 2}

#: The tolerance is K_TOLERANCE times the cell's PSID-scale sampling
#: standard error: a fill may move a cell by no more than the PSID sample's
#: own sampling error already does.
K_TOLERANCE = 1.0

_CAREER_FIRST_YEAR = 1968
_CAREER_START_AGE = 22
_AIME_LAST_AGE = 61
_AIME_INDEX_AGE = 60
_COMPUTATION_YEARS = 35
_PRE_ADULT_AGE = 18
_YOUTH_AGES = (15, 21)
_PRE_PAIR_IN = (1962, 1967)
_PRE_PAIR_CROSS = (1965, 1970)
_YOUTH_PAIR_AGES = (21, 24)

#: Cells measured as an absolute gap; every other cell is a log ratio.
_CORRELATIONS = frozenset({"r1", "r2", "r4", "pr_in", "pr_cross", "yr_cross"})


def _column(year: int) -> int:
    return int(year) - FIRST_YEAR


def split_part(person_ids: Iterable[int]) -> np.ndarray:
    """TRAIN (0), DEV (1) or TEST (2) for each person id, by the salted hash."""

    parts = []
    for person_id in person_ids:
        digest = hashlib.sha256(SPLIT_SALT + str(int(person_id)).encode())
        position = int.from_bytes(digest.digest()[:8], "big") / 2.0**64
        if position < _TRAIN_BELOW:
            parts.append(TRAIN)
        elif position < _DEV_BELOW:
            parts.append(DEV)
        else:
            parts.append(TEST)
    return np.asarray(parts, dtype=np.int8)


def _check_matrix(earnings: np.ndarray, birth_year: np.ndarray) -> None:
    if earnings.ndim != 2 or earnings.shape[1] != len(YEARS):
        raise ValueError(
            f"earnings must be persons by the {len(YEARS)} years "
            f"{FIRST_YEAR}-{LAST_YEAR}"
        )
    if len(birth_year) != earnings.shape[0]:
        raise ValueError("birth_year must have one entry per person")


def odd_mask(n_persons: int) -> np.ndarray:
    """Persons by years: True on the masked odd years 1997-2005."""

    mask = np.zeros((n_persons, len(YEARS)), dtype=bool)
    mask[:, [_column(year) for year in MASKED_ODD_YEARS]] = True
    return mask


def pre_career_mask(birth_year: np.ndarray) -> np.ndarray:
    """Persons by years: True before ``max(1968, birth_year + 22)``."""

    birth_year = np.asarray(birth_year, dtype=np.int64)
    start = np.maximum(_CAREER_FIRST_YEAR, birth_year + _CAREER_START_AGE)
    return np.asarray(YEARS)[None, :] < start[:, None]


def current_odd_fill(earnings: np.ndarray) -> np.ndarray:
    """The assembler's rule: each masked odd year is its neighbours' mean.

    On EPUF both neighbours are always recorded, so the single-neighbour
    fallback of ``career._impute_gap`` never applies.
    """

    out = np.asarray(earnings, dtype=np.float64).copy()
    for year in MASKED_ODD_YEARS:
        out[:, _column(year)] = (
            out[:, _column(year - 1)] + out[:, _column(year + 1)]
        ) / 2.0
    return out


def current_pre_career_fill(
    earnings: np.ndarray, birth_year: np.ndarray
) -> np.ndarray:
    """The assembler's rule: every year before its career start is zero."""

    out = np.asarray(earnings, dtype=np.float64).copy()
    out[pre_career_mask(birth_year)] = 0.0
    return out


def aime_35(
    earnings: np.ndarray,
    birth_year: np.ndarray,
    nawi: Mapping[int, float],
) -> np.ndarray:
    """AIME under the 35-year rule, through age 61, for capped histories.

    Every year from 1951 through the year of age 61 is ranked, including
    years before age 22 (42 USC 415(b)(2)); years before age 60 are
    indexed by NAWI at age 60 over NAWI in the year; the top 35 are summed
    and floored over 420 months. Inputs must already be capped, and each
    person's year of age 61 must lie inside 1951-2006 (born 1929-1945).
    The statutory oracle is ``ss.statutory_aime.aime``; a test pins the two
    together.
    """

    earnings = np.asarray(earnings, dtype=np.float64)
    birth_year = np.asarray(birth_year, dtype=np.int64)
    _check_matrix(earnings, birth_year)
    cutoff = birth_year + _AIME_LAST_AGE
    if (cutoff > LAST_YEAR).any() or (birth_year < 1929).any():
        raise ValueError("AIME needs birth years 1929-1945 inside 1951-2006")
    years = np.asarray(YEARS)
    index_year = birth_year + _AIME_INDEX_AGE
    index_value = np.array([float(nawi[int(year)]) for year in index_year])
    year_value = np.array([float(nawi[int(year)]) for year in years])
    factor = np.where(
        years[None, :] < index_year[:, None],
        index_value[:, None] / year_value[None, :],
        1.0,
    )
    indexed = np.where(
        years[None, :] <= cutoff[:, None], earnings * factor, 0.0
    )
    top = np.sort(indexed, axis=1)[:, -_COMPUTATION_YEARS:]
    return np.floor(top.sum(axis=1) / (_COMPUTATION_YEARS * 12))


def _share(numerator: np.ndarray, denominator: np.ndarray) -> CellValue:
    total = int(denominator.sum())
    hits = int((numerator & denominator).sum())
    value = hits / total if total else float("nan")
    return CellValue(float(value), min(hits, total - hits), total)


def _spearman_mean(
    pairs: Sequence[tuple[np.ndarray, np.ndarray]],
) -> CellValue:
    values = []
    counts = []
    for left, right in pairs:
        both = (left > 0) & (right > 0)
        counts.append(int(both.sum()))
        values.append(
            weighted_spearman(
                left[both], right[both], np.ones(int(both.sum()))
            )
        )
    finite = [value for value in values if np.isfinite(value)]
    value = float(np.mean(finite)) if len(finite) == len(values) else np.nan
    return CellValue(float(value), min(counts) if counts else 0, sum(counts))


def odd_cells(
    earnings: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    wage_bases: Mapping[int, float],
    nawi: Mapping[int, float],
) -> dict[str, CellValue]:
    """Every cell of family ``odd`` for one matrix (true or filled).

    The universe is persons of known sex with positive earnings in at
    least one recorded even year 1996-2006; it reads no masked year, so
    the true and the filled matrix of the same persons share it. Per sex
    and band of age at the masked year ``t`` (units are person-years):

    - ``r1``: Spearman of ``t`` against ``t-1`` and against ``t+1``, among
      units positive in both years; the mean of the ten.
    - ``r2`` / ``r4``: Spearman of ``t`` against ``t+2`` (four pairs) or
      ``t+4`` (three pairs), both masked, positive in both; the mean.
    - ``zint``: zero at ``t`` among units positive at ``t-1`` and ``t+1``.
    - ``zexit``: zero at ``t`` among units positive at exactly one of
      ``t-1`` and ``t+1`` (a career starting or stopping).
    - ``wint``: positive at ``t`` among units zero at ``t-1`` and ``t+1``.
    - ``atcap``: at the year's wage base among units positive at ``t``.
    - ``level``: mean earnings over the wage base at ``t``, zeros included.

    Per sex and the cohorts of :data:`ODD_AIME_COHORTS` (universe: positive
    in at least one unmasked year 1968-2006): ``aime_p25``, ``aime_p50``
    and ``aime_p75`` (:func:`aime_35`).
    """

    earnings = np.asarray(earnings, dtype=np.float64)
    birth_year = np.asarray(birth_year, dtype=np.int64)
    sex = np.asarray(sex)
    _check_matrix(earnings, birth_year)
    observed = earnings[:, [_column(year) for year in ODD_OBSERVED_YEARS]]
    universe = np.isin(sex, list(SEXES.values())) & (observed > 0).any(axis=1)
    cap = {year: float(wage_bases[year]) for year in YEARS}
    out: dict[str, CellValue] = {}
    for sex_label, sex_code in SEXES.items():
        member = universe & (sex == sex_code)
        for band, (low, high) in ODD_AGE_BANDS.items():
            prefix = f"odd.{sex_label}.{band}"
            units = {
                year: member
                & (year - birth_year >= low)
                & (year - birth_year <= high)
                for year in MASKED_ODD_YEARS
            }

            def column(year: int, rows: np.ndarray) -> np.ndarray:
                return earnings[rows, _column(year)]

            out[f"{prefix}.r1"] = _spearman_mean(
                [
                    (
                        column(year, units[year]),
                        column(year + side, units[year]),
                    )
                    for year in MASKED_ODD_YEARS
                    for side in (-1, 1)
                ]
            )
            for lag in (2, 4):
                out[f"{prefix}.r{lag}"] = _spearman_mean(
                    [
                        (
                            column(year, units[year]),
                            column(year + lag, units[year]),
                        )
                        for year in MASKED_ODD_YEARS
                        if year + lag in MASKED_ODD_YEARS
                    ]
                )
            left = np.concatenate(
                [column(year - 1, units[year]) for year in MASKED_ODD_YEARS]
            )
            centre = np.concatenate(
                [column(year, units[year]) for year in MASKED_ODD_YEARS]
            )
            right = np.concatenate(
                [column(year + 1, units[year]) for year in MASKED_ODD_YEARS]
            )
            centre_cap = np.concatenate(
                [
                    np.full(int(units[year].sum()), cap[year])
                    for year in MASKED_ODD_YEARS
                ]
            )
            out[f"{prefix}.zint"] = _share(
                centre == 0, (left > 0) & (right > 0)
            )
            out[f"{prefix}.zexit"] = _share(
                centre == 0, (left > 0) ^ (right > 0)
            )
            out[f"{prefix}.wint"] = _share(
                centre > 0, (left == 0) & (right == 0)
            )
            out[f"{prefix}.atcap"] = _share(centre >= centre_cap, centre > 0)
            positive = int((centre > 0).sum())
            out[f"{prefix}.level"] = CellValue(
                float((centre / centre_cap).mean()) if len(centre) else np.nan,
                positive,
                len(centre),
            )
    unmasked_career = [
        _column(year)
        for year in range(_CAREER_FIRST_YEAR, LAST_YEAR + 1)
        if year not in MASKED_ODD_YEARS
    ]
    career_universe = np.isin(sex, list(SEXES.values())) & (
        earnings[:, unmasked_career] > 0
    ).any(axis=1)
    out.update(
        _aime_cells(
            "odd",
            earnings,
            birth_year,
            sex,
            career_universe,
            ODD_AIME_COHORTS,
            nawi,
        )
    )
    return out


def _aime_cells(
    family: str,
    earnings: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    universe: np.ndarray,
    cohorts: Mapping[str, tuple[int, int]],
    nawi: Mapping[int, float],
) -> dict[str, CellValue]:
    out: dict[str, CellValue] = {}
    for sex_label, sex_code in SEXES.items():
        for cohort, (low, high) in cohorts.items():
            rows = (
                universe
                & (sex == sex_code)
                & (birth_year >= low)
                & (birth_year <= high)
            )
            aime = aime_35(earnings[rows], birth_year[rows], nawi)
            for quantile in AIME_QUANTILES:
                value = (
                    float(np.quantile(aime, quantile)) if len(aime) else np.nan
                )
                out[
                    f"{family}.{sex_label}.{cohort}.aime_p{int(quantile * 100)}"
                ] = CellValue(value, int((aime > 0).sum()), len(aime))
    return out


def pre_career_cells(
    earnings: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    wage_bases: Mapping[int, float],
    nawi: Mapping[int, float],
) -> dict[str, CellValue]:
    """Every cell of family ``pre`` for one matrix (true or filled).

    The universe is persons of known sex with positive earnings in at
    least one year from their career start, ``max(1968, birth_year + 22)``,
    through 2006 (the years the PSID can record); it reads no masked year.

    Per sex and the cohorts of :data:`PRE_CAREER_COHORTS` (masked years
    1951-1967): ``aime_p25``, ``aime_p50``, ``aime_p75``; ``pzero``, the
    share of masked person-years at ages 18 and over with no earnings;
    ``plevel``, their mean earnings over the wage base; ``pr_in``, the
    Spearman of 1962 against 1967 (both masked); and ``pr_cross``, of 1965
    against 1970 (masked against recorded), positive in both years.

    Per sex and the cohorts of :data:`YOUTH_COHORTS` (masked years: ages
    up to 21): ``yzero`` and ``ylevel`` over ages 15-21, and ``yr_cross``,
    the Spearman of earnings at age 21 against age 24, positive in both.
    """

    earnings = np.asarray(earnings, dtype=np.float64)
    birth_year = np.asarray(birth_year, dtype=np.int64)
    sex = np.asarray(sex)
    _check_matrix(earnings, birth_year)
    years = np.asarray(YEARS)
    masked = pre_career_mask(birth_year)
    recorded = ~masked & (years[None, :] <= LAST_YEAR)
    universe = np.isin(sex, list(SEXES.values())) & (
        (earnings > 0) & recorded
    ).any(axis=1)
    caps = np.array([float(wage_bases[year]) for year in YEARS])
    share_of_cap = earnings / caps[None, :]
    age = years[None, :] - birth_year[:, None]
    out = _aime_cells(
        "pre", earnings, birth_year, sex, universe, PRE_CAREER_COHORTS, nawi
    )
    for sex_label, sex_code in SEXES.items():
        for cohort, (low, high) in PRE_CAREER_COHORTS.items():
            rows = (
                universe
                & (sex == sex_code)
                & (birth_year >= low)
                & (birth_year <= high)
            )
            prefix = f"pre.{sex_label}.{cohort}"
            adult = masked[rows] & (age[rows] >= _PRE_ADULT_AGE)
            values = earnings[rows][adult]
            out[f"{prefix}.pzero"] = _share(
                values == 0, np.ones(len(values), dtype=bool)
            )
            out[f"{prefix}.plevel"] = CellValue(
                (
                    float(share_of_cap[rows][adult].mean())
                    if len(values)
                    else np.nan
                ),
                int((values > 0).sum()),
                len(values),
            )
            for name, (first, second) in (
                ("pr_in", _PRE_PAIR_IN),
                ("pr_cross", _PRE_PAIR_CROSS),
            ):
                out[f"{prefix}.{name}"] = _spearman_mean(
                    [
                        (
                            earnings[rows, _column(first)],
                            earnings[rows, _column(second)],
                        )
                    ]
                )
        for cohort, (low, high) in YOUTH_COHORTS.items():
            rows = (
                universe
                & (sex == sex_code)
                & (birth_year >= low)
                & (birth_year <= high)
            )
            prefix = f"pre.{sex_label}.{cohort}"
            young = (
                masked[rows]
                & (age[rows] >= _YOUTH_AGES[0])
                & (age[rows] <= _YOUTH_AGES[1])
            )
            values = earnings[rows][young]
            out[f"{prefix}.yzero"] = _share(
                values == 0, np.ones(len(values), dtype=bool)
            )
            out[f"{prefix}.ylevel"] = CellValue(
                (
                    float(share_of_cap[rows][young].mean())
                    if len(values)
                    else np.nan
                ),
                int((values > 0).sum()),
                len(values),
            )
            first_age, second_age = _YOUTH_PAIR_AGES
            person_rows = np.flatnonzero(rows)
            out[f"{prefix}.yr_cross"] = _spearman_mean(
                [
                    (
                        earnings[
                            person_rows,
                            birth_year[person_rows] + first_age - FIRST_YEAR,
                        ],
                        earnings[
                            person_rows,
                            birth_year[person_rows] + second_age - FIRST_YEAR,
                        ],
                    )
                ]
            )
    return out


def cell_metric(cell_id: str) -> str:
    """``abs_gap`` for a rank correlation, ``log_ratio`` for every other cell."""

    return (
        "abs_gap"
        if cell_id.rsplit(".", 1)[-1] in _CORRELATIONS
        else ("log_ratio")
    )


def gap(cell_id: str, filled: float, truth: float) -> float:
    """The filled value's distance from the truth on the cell's scale.

    A correlation's gap is the difference; any other cell's is the log
    ratio, which is minus or plus infinity when exactly one side is zero
    and NaN when both are.
    """

    if cell_metric(cell_id) == "abs_gap":
        return float(filled - truth)
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.log(filled) - np.log(truth))


@dataclass(frozen=True)
class FloorResult:
    """One cell's floor: replicate errors and their root mean square."""

    cell_id: str
    replicates: tuple[float, ...]
    sigma: float
    sample_size: int


def floor_sigma(
    cell_id: str,
    statistic: Callable[[np.ndarray], float],
    pool: np.ndarray,
    sample_size: int,
    *,
    n_replicates: int,
    seed: int,
) -> FloorResult:
    """The cell's sampling standard error at ``sample_size`` persons.

    Each replicate draws two disjoint samples of ``sample_size`` persons
    from ``pool`` (row indices of real DEV persons eligible for the cell)
    and records ``[m(A) - m(B)] / sqrt(2)`` on the cell's scale, where
    ``statistic`` maps row indices to the cell's value. ``sigma`` is the
    replicates' root mean square: for two independent samples it estimates
    the standard error of one.
    """

    pool = np.asarray(pool)
    if 2 * sample_size > len(pool):
        raise ValueError(
            f"{cell_id}: two samples of {sample_size} exceed the pool of "
            f"{len(pool)}"
        )
    rng = np.random.default_rng([seed, n_replicates, sample_size])
    replicates = []
    for _ in range(n_replicates):
        drawn = rng.choice(pool, size=2 * sample_size, replace=False)
        first = statistic(np.sort(drawn[:sample_size]))
        second = statistic(np.sort(drawn[sample_size:]))
        replicates.append(gap(cell_id, first, second) / np.sqrt(2.0))
    values = np.asarray(replicates, dtype=np.float64)
    finite = values[np.isfinite(values)]
    sigma = (
        float(np.sqrt(np.mean(finite**2)))
        if len(finite) == len(values)
        else float("nan")
    )
    return FloorResult(cell_id, tuple(map(float, values)), sigma, sample_size)
