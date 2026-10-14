"""Rules of gate_epuf_fill: career fills scored on held-out EPUF careers.

A gate here is a pass-or-fail test whose rules and thresholds are fixed
and published before anything is scored against it.

The career assembler (:func:`populace_dynamics.estimates.career.build_career`)
fills the years the PSID did not record with two fixed rules: each odd
income year from 1997 is the mean of its two neighbours, and nothing
counts before ``max(1968, birth_year + 22)``. This gate scores a
replacement for each rule on SSA's 2006 Earnings Public-Use File (EPUF;
:mod:`populace_dynamics.data.epuf`), which records every year's capped
taxable earnings from 1951 to 2006
(``docs/amendments/gate_epuf_fill_registration_proposal.md``):

1. **Split.** EPUF persons are split once, by a salted SHA-256 of the
   person id, into TRAIN (60 percent; fills learn from it), DEV (20
   percent; floors and the checks on bite are built on it before lock)
   and TEST (20 percent; read only through :func:`test_part`, after lock).
2. **Mask.** Two families of years, as the PSID would leave a career: the
   odd years 1997-2005 (family ``odd``), and every year before
   ``max(1968, birth_year + 22)`` (family ``pre``). A fill receives both
   families' years as unknown and fills its own family's
   (:func:`score_candidate`).
3. **Score.** Each cell is computed once on the true matrix and once on
   the matrix whose own-family masked cells the fill replaced; the gap is
   their difference on the cell's scale (:func:`gap`).
4. **Floor.** A cell's tolerance is ``K_TOLERANCE`` times the sampling
   standard error the cell carries at the PSID's size: the root mean
   square of ``[m(A) - m(B)] / sqrt(2)`` over replicate pairs of disjoint
   real DEV samples of the cell's floor group, each the size of the
   PSID's (:func:`floor_group`).

Every cell belongs to one floor group, and :func:`group_rows` defines the
persons a group counts; the cells and the floors both draw their persons
from it, so a floor is always priced on the population its cells score.
The masks, populations and statistics are defined here once and used for
the truth, every fill, the floors and the checks on bite, so a gap can
never be a difference of definition.

Amendment 1 (referee round 1, ``reviews/gate_epuf_fill_round1_referee_20261004.md``)
moved the youngest odd band to ages 22-29, gave each group exactly the
population its cells count, added pooled groups, the AIME's 10th and
90th percentiles, a partial AIME through 2006 for later cohorts, the
``r3`` and positive-share quantile statistics, the union-mask scoring
path with its validity checks, the audited TEST read and a cap on the
"improves" tier. Referee round 2 (``reviews/gate_epuf_fill_round2_verification_20261004.md``)
moved pre-career odd years out of the odd family's mask and made the
current rules fills on the scoring path; neither changes a floor.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from populace_dynamics.harness.epuf_cells import CellValue, weighted_spearman

__all__ = [
    "ADOPTION_TIERS",
    "AIME_QUANTILES",
    "BITE_MULTIPLE",
    "CurrentOddFill",
    "CurrentPreFill",
    "DEV",
    "DRAW_SEEDS",
    "EPUFMatrix",
    "EVENTS_SHARE",
    "FIRST_YEAR",
    "FLOOR_SEED_BASE",
    "FillOutputInvalid",
    "FloorGroup",
    "IMPROVES_CAP",
    "K_TOLERANCE",
    "LAST_YEAR",
    "MASKED_ODD_YEARS",
    "MIN_EVENTS",
    "N_FLOOR_REPLICATES",
    "ODD_AGE_BANDS",
    "ODD_AIME_COHORTS",
    "ODD_OBSERVED_YEARS",
    "ORACLE_SEEDS",
    "PARTIAL_AIME_COHORTS",
    "PRE_CAREER_COHORTS",
    "REGISTRATION_ID",
    "SEXES",
    "SPLIT_SALT",
    "TEST",
    "TRAIN",
    "TestPartLocked",
    "YEARS",
    "YOUTH_COHORTS",
    "adopt",
    "adoption_tier",
    "aime_35",
    "cell_metric",
    "current_odd_fill",
    "current_pre_career_fill",
    "current_rule",
    "earnings_from_shares",
    "epuf_matrix",
    "family_cells",
    "family_mask",
    "floor_group",
    "gap",
    "group_of",
    "group_rows",
    "groups",
    "odd_cells",
    "odd_mask",
    "odd_oracle_fill",
    "partial_aime",
    "partition",
    "pre_career_cells",
    "pre_career_mask",
    "pre_career_oracle_fill",
    "score",
    "score_candidate",
    "share_bin_edges",
    "split_part",
    "test_part",
    "union_mask",
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
#: Age at the masked year. The assembler fills odd years only inside the
#: career, from age 22; ``a22_74`` pools the four bands.
ODD_AGE_BANDS: dict[str, tuple[int, int]] = {
    "a22_29": (22, 29),
    "a30_44": (30, 44),
    "a45_59": (45, 59),
    "a60_74": (60, 74),
    "a22_74": (22, 74),
}
#: Cohorts whose AIME (35 years through age 61) includes masked odd years
#: and lies wholly inside 1951-2006; ``b1936_1945`` pools them.
ODD_AIME_COHORTS: dict[str, tuple[int, int]] = {
    "b1936_1940": (1936, 1940),
    "b1941_1945": (1941, 1945),
    "b1936_1945": (1936, 1945),
}
#: Cohorts whose masked pre-career years are 1951-1967 and whose AIME lies
#: wholly inside 1951-2006; ``b1930_1945`` pools them.
PRE_CAREER_COHORTS: dict[str, tuple[int, int]] = {
    "b1930_1934": (1930, 1934),
    "b1935_1939": (1935, 1939),
    "b1940_1945": (1940, 1945),
    "b1930_1945": (1930, 1945),
}
#: Cohorts for whom the pre-career rule removes only the years before age
#: 22 (the PSID-2010 cohort's youngest were born in 1980); ``b1946_1980``
#: pools them.
YOUTH_COHORTS: dict[str, tuple[int, int]] = {
    "b1946_1955": (1946, 1955),
    "b1956_1965": (1956, 1965),
    "b1966_1980": (1966, 1980),
    "b1946_1980": (1946, 1980),
}
#: Cohorts scored on the partial AIME through 2006 in family ``odd``.
PARTIAL_AIME_COHORTS: dict[str, tuple[int, int]] = dict(YOUTH_COHORTS)
AIME_QUANTILES: tuple[float, ...] = (0.10, 0.25, 0.50, 0.75, 0.90)
SHARE_QUANTILES: tuple[float, ...] = (0.10, 0.50, 0.90)
SEXES: dict[str, int] = {"men": 1, "women": 2}

#: The tolerance is K_TOLERANCE times the cell's PSID-scale sampling
#: standard error: a materiality threshold under which a fill moves a cell
#: by no more than the PSID sample's own sampling error already does.
K_TOLERANCE = 1.0
#: A cell gates only if its events (``CellValue.events``) number at least
#: MIN_EVENTS in the smaller sample of a floor pair, in at least
#: EVENTS_SHARE of the replicates.
MIN_EVENTS = 20
EVENTS_SHARE = 0.95
#: Each check on bite must fail a gating cell of its family by more than
#: BITE_MULTIPLE tolerances.
BITE_MULTIPLE = 2.0
#: An "improves" candidate may miss a gating cell by at most the larger of
#: one tolerance and the smaller of the current rule's gap and IMPROVES_CAP
#: tolerances.
IMPROVES_CAP = 3.0
N_FLOOR_REPLICATES = 200
FLOOR_SEED_BASE = 5000
#: A candidate's filled value in a cell is the mean over these draw seeds.
DRAW_SEEDS: tuple[int, ...] = tuple(range(7100, 7120))
#: The oracles' permutation seeds.
ORACLE_SEEDS: tuple[int, ...] = tuple(range(7200, 7220))
#: Bins of a positive share of the wage base below it (the oracles).
N_SHARE_BINS = 20
#: Five-year age bands for the odd-year oracle, 15-19 through 80-84 (85
#: joins the last).
_ORACLE_AGE_EDGES = tuple(range(20, 85, 5))

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
_CORRELATIONS = frozenset(
    {"r1", "r2", "r3", "r4", "pr_in", "pr_cross", "yr_cross"}
)
_ODD_BAND_STATISTICS = (
    "r1",
    "r2",
    "r3",
    "r4",
    "zint",
    "zexit",
    "wint",
    "atcap",
    "level",
    "q10",
    "q50",
    "q90",
)


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


# --------------------------------------------------------------------------
# Masks and the current rules
# --------------------------------------------------------------------------
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


def family_mask(family: str, birth_year: np.ndarray) -> np.ndarray:
    """The cells a family's fill replaces.

    ``odd``: the masked odd years inside the career (from ``max(1968,
    birth_year + 22)``); an odd year before the career start belongs to the
    pre-career rule, which fills it in use (round 2, finding 2). ``pre``:
    every year before the career start.
    """

    if family == "odd":
        return odd_mask(len(birth_year)) & ~pre_career_mask(birth_year)
    if family == "pre":
        return pre_career_mask(birth_year)
    raise ValueError(f"unknown family {family!r}")


def union_mask(birth_year: np.ndarray) -> np.ndarray:
    """Every cell the PSID would not record: both families' masks."""

    return odd_mask(len(birth_year)) | pre_career_mask(birth_year)


def current_odd_fill(
    earnings: np.ndarray, birth_year: np.ndarray | None = None
) -> np.ndarray:
    """The assembler's rule on a complete matrix: odd years are neighbour means.

    Each masked odd year inside the career (all of them when
    ``birth_year`` is not given) becomes the mean of the true years around
    it. On the gate's scoring path the rule is :class:`CurrentOddFill`,
    which sees pre-career years as unknown and so falls back to the single
    known neighbour for a unit at age 22, as ``career._impute_gap`` does.
    """

    out = np.asarray(earnings, dtype=np.float64).copy()
    own = (
        odd_mask(len(out))
        if birth_year is None
        else family_mask("odd", birth_year)
    )
    for year in MASKED_ODD_YEARS:
        column = _column(year)
        mean = (out[:, column - 1] + out[:, column + 1]) / 2.0
        out[:, column] = np.where(own[:, column], mean, out[:, column])
    return out


def current_pre_career_fill(
    earnings: np.ndarray, birth_year: np.ndarray
) -> np.ndarray:
    """The assembler's rule: every year before its career start is zero."""

    out = np.asarray(earnings, dtype=np.float64).copy()
    out[pre_career_mask(birth_year)] = 0.0
    return out


class CurrentOddFill:
    """The assembler's odd-year rule as a fill on the scoring path.

    Each owned cell becomes the mean of its two neighbouring years'
    earnings, in dollars (shares times each year's wage base), as a share
    of its own year's wage base, capped at 1; with one neighbour unknown,
    that neighbour's earnings; with both unknown, zero
    (``career._impute_gap`` leaves such a year unfilled, and an unfilled
    career year counts as zero).
    """

    name = "current_odd_rule"

    def fill(self, shares, years, birth_year, sex, person_key, mask, seed):
        years = np.asarray(years)
        caps = np.array([_wage_base(int(year)) for year in years])
        given = np.asarray(shares, dtype=np.float64)
        dollars = given * caps[None, :]
        out = given.copy()
        for column in np.flatnonzero(mask.any(axis=0)):
            left = dollars[:, column - 1] if column > 0 else np.nan
            right = (
                dollars[:, column + 1] if column + 1 < len(years) else np.nan
            )
            mean = np.where(
                np.isnan(left),
                right,
                np.where(np.isnan(right), left, (left + right) / 2.0),
            )
            share = np.minimum(
                np.nan_to_num(mean, nan=0.0) / caps[column], 1.0
            )
            rows = mask[:, column]
            out[rows, column] = share[rows]
        return out


class CurrentPreFill:
    """The assembler's pre-career rule as a fill: every owned cell is zero."""

    name = "current_pre_career_rule"

    def fill(self, shares, years, birth_year, sex, person_key, mask, seed):
        out = np.asarray(shares, dtype=np.float64).copy()
        out[mask] = 0.0
        return out


def current_rule(family: str):
    """The current rule of a family, as a fill for :func:`score_candidate`."""

    if family == "odd":
        return CurrentOddFill()
    if family == "pre":
        return CurrentPreFill()
    raise ValueError(f"unknown family {family!r}")


# --------------------------------------------------------------------------
# AIME
# --------------------------------------------------------------------------
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


def partial_aime(
    earnings: np.ndarray, nawi: Mapping[int, float]
) -> np.ndarray:
    """The AIME formula applied to every year through 2006.

    For cohorts whose age-61 year is after 2006: each year 1951-2005 is
    indexed by NAWI in 2006 over NAWI in the year, the top 35 years are
    summed and the sum is floored over 420 months. It is not a statutory
    AIME; it measures how a fill moves the AIME's ingredients for cohorts
    EPUF cannot follow to 61.
    """

    earnings = np.asarray(earnings, dtype=np.float64)
    years = np.asarray(YEARS)
    year_value = np.array([float(nawi[int(year)]) for year in years])
    factor = float(nawi[LAST_YEAR]) / year_value
    top = np.sort(earnings * factor[None, :], axis=1)[:, -_COMPUTATION_YEARS:]
    return np.floor(top.sum(axis=1) / (_COMPUTATION_YEARS * 12))


# --------------------------------------------------------------------------
# Populations
# --------------------------------------------------------------------------
def _coded(sex: np.ndarray) -> np.ndarray:
    return np.isin(np.asarray(sex), list(SEXES.values()))


def _career_start(birth_year: np.ndarray) -> np.ndarray:
    return np.maximum(
        _CAREER_FIRST_YEAR,
        np.asarray(birth_year, dtype=np.int64) + _CAREER_START_AGE,
    )


def family_universe(
    family: str, earnings: np.ndarray, birth_year: np.ndarray, sex: np.ndarray
) -> np.ndarray:
    """Persons of coded sex with a positive recorded career year.

    ``odd`` (age-band groups): positive in a recorded even year 1996-2006.
    ``odd_career`` (the odd family's cohort groups): positive in a year
    from ``max(1968, birth_year + 22)`` through 2006 that is not a masked
    odd year. ``pre``: positive in a year from ``max(1968, birth_year +
    22)`` through 2006. None reads a cell its own family masks.
    """

    earnings = np.asarray(earnings)
    birth_year = np.asarray(birth_year, dtype=np.int64)
    coded = _coded(sex)
    if family == "odd":
        observed = earnings[:, [_column(year) for year in ODD_OBSERVED_YEARS]]
        return coded & (observed > 0).any(axis=1)
    recorded = ~pre_career_mask(birth_year)
    if family == "odd_career":
        recorded = recorded & ~odd_mask(len(birth_year))
        return coded & ((earnings > 0) & recorded).any(axis=1)
    if family == "pre":
        return coded & ((earnings > 0) & recorded).any(axis=1)
    raise ValueError(f"unknown family {family!r}")


def groups() -> list[str]:
    """Every floor group id, sorted: ``<family>.<sex>.<stratum>``."""

    out = []
    for sex_label in SEXES:
        for band in ODD_AGE_BANDS:
            out.append(f"odd.{sex_label}.{band}")
        for cohort in {**ODD_AIME_COHORTS, **PARTIAL_AIME_COHORTS}:
            out.append(f"odd.{sex_label}.{cohort}")
        for cohort in {**PRE_CAREER_COHORTS, **YOUTH_COHORTS}:
            out.append(f"pre.{sex_label}.{cohort}")
    return sorted(out)


def group_of(cell_id: str) -> str:
    """A cell's floor group: its id without the statistic."""

    return cell_id.rsplit(".", 1)[0]


def group_rows(
    group: str, earnings: np.ndarray, birth_year: np.ndarray, sex: np.ndarray
) -> np.ndarray:
    """Persons by flag: exactly the persons a group's cells count.

    Age-band groups (family ``odd``): ``odd`` universe members of the sex
    with a masked odd year at an age in the band. The odd family's cohort
    groups: ``odd_career`` universe members of the sex born in the cohort.
    The pre family's cohort groups: ``pre`` universe members of the sex
    born in the cohort. The cells and the floors both take their persons
    from here.
    """

    family, sex_label, stratum = group.split(".")
    birth_year = np.asarray(birth_year, dtype=np.int64)
    of_sex = np.asarray(sex) == SEXES[sex_label]
    if family == "odd" and stratum in ODD_AGE_BANDS:
        low, high = ODD_AGE_BANDS[stratum]
        ages = np.asarray(MASKED_ODD_YEARS)[None, :] - birth_year[:, None]
        in_band = ((ages >= low) & (ages <= high)).any(axis=1)
        member = family_universe("odd", earnings, birth_year, sex)
        return member & of_sex & in_band
    if family == "odd":
        cohorts = {**ODD_AIME_COHORTS, **PARTIAL_AIME_COHORTS}
        member = family_universe("odd_career", earnings, birth_year, sex)
    elif family == "pre":
        cohorts = {**PRE_CAREER_COHORTS, **YOUTH_COHORTS}
        member = family_universe("pre", earnings, birth_year, sex)
    else:
        raise ValueError(f"unknown family {family!r}")
    low, high = cohorts[stratum]
    return member & of_sex & (birth_year >= low) & (birth_year <= high)


# --------------------------------------------------------------------------
# Cell statistics
# --------------------------------------------------------------------------
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
    value = (
        float(np.mean(finite))
        if values and len(finite) == len(values)
        else np.nan
    )
    return CellValue(float(value), min(counts) if counts else 0, sum(counts))


def _quantile_cells(
    prefix: str, values: np.ndarray, name: str, quantiles
) -> dict[str, CellValue]:
    out = {}
    for quantile in quantiles:
        value = float(np.quantile(values, quantile)) if len(values) else np.nan
        out[f"{prefix}.{name}_p{int(round(quantile * 100))}"] = CellValue(
            value, int((values > 0).sum()), len(values)
        )
    return out


def _odd_band_cells(
    prefix: str,
    earnings: np.ndarray,
    birth_year: np.ndarray,
    rows: np.ndarray,
    band: tuple[int, int],
    caps: Mapping[int, float],
) -> dict[str, CellValue]:
    """The band statistics over units (person in ``rows``, masked year t)."""

    low, high = band
    units = {
        year: rows & (year - birth_year >= low) & (year - birth_year <= high)
        for year in MASKED_ODD_YEARS
    }

    def column(year: int, take: np.ndarray) -> np.ndarray:
        return earnings[take, _column(year)]

    out: dict[str, CellValue] = {}
    out[f"{prefix}.r1"] = _spearman_mean(
        [
            (column(year, units[year]), column(year + side, units[year]))
            for year in MASKED_ODD_YEARS
            for side in (-1, 1)
        ]
    )
    out[f"{prefix}.r3"] = _spearman_mean(
        [
            (column(year, units[year]), column(year + side, units[year]))
            for year in MASKED_ODD_YEARS
            for side in (-3, 3)
            if FIRST_YEAR <= year + side <= LAST_YEAR
        ]
    )
    for lag in (2, 4):
        out[f"{prefix}.r{lag}"] = _spearman_mean(
            [
                (column(year, units[year]), column(year + lag, units[year]))
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
            np.full(int(units[year].sum()), float(caps[year]))
            for year in MASKED_ODD_YEARS
        ]
    )
    share = centre / np.where(centre_cap > 0, centre_cap, 1.0)
    out[f"{prefix}.zint"] = _share(centre == 0, (left > 0) & (right > 0))
    out[f"{prefix}.zexit"] = _share(centre == 0, (left > 0) ^ (right > 0))
    out[f"{prefix}.wint"] = _share(centre > 0, (left == 0) & (right == 0))
    out[f"{prefix}.atcap"] = _share(centre >= centre_cap, centre > 0)
    out[f"{prefix}.level"] = CellValue(
        float(share.mean()) if len(share) else np.nan,
        int((centre > 0).sum()),
        len(share),
    )
    positive = share[centre > 0]
    for quantile in SHARE_QUANTILES:
        value = (
            float(np.quantile(positive, quantile)) if len(positive) else np.nan
        )
        out[f"{prefix}.q{int(round(quantile * 100))}"] = CellValue(
            value, len(positive), len(share)
        )
    return out


def odd_cells(
    earnings: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    wage_bases: Mapping[int, float],
    nawi: Mapping[int, float],
) -> dict[str, CellValue]:
    """Every cell of family ``odd`` for one matrix (true or filled).

    Per sex and age band at the masked year ``t`` (units are person-years
    of the group's persons, :func:`group_rows`, at an age in the band):

    - ``r1``: Spearman of ``t`` against ``t-1`` and against ``t+1``; ``r3``
      against ``t-3`` and ``t+3`` (recorded); ``r2`` / ``r4`` against
      ``t+2`` / ``t+4`` (masked). Among units positive in both years; the
      mean over the year pairs.
    - ``zint``: zero at ``t`` among units positive at ``t-1`` and ``t+1``;
      ``zexit``: zero at ``t`` among units positive at exactly one of them;
      ``wint``: positive at ``t`` among units zero at both.
    - ``atcap``: at the year's wage base among units positive at ``t``.
    - ``level``: mean earnings over the wage base at ``t``, zeros included.
    - ``q10`` / ``q50`` / ``q90``: quantiles of the positive shares of the
      wage base at ``t``.

    Per sex and cohort: ``aime_p10`` ... ``aime_p90`` (:func:`aime_35`) for
    the cohorts born 1936-1945, and ``paime_p10`` ... ``paime_p90``
    (:func:`partial_aime`) for those born 1946-1980.
    """

    earnings = np.asarray(earnings, dtype=np.float64)
    birth_year = np.asarray(birth_year, dtype=np.int64)
    sex = np.asarray(sex)
    _check_matrix(earnings, birth_year)
    caps = {year: float(wage_bases[year]) for year in YEARS}
    out: dict[str, CellValue] = {}
    for sex_label in SEXES:
        for band, bounds in ODD_AGE_BANDS.items():
            group = f"odd.{sex_label}.{band}"
            rows = group_rows(group, earnings, birth_year, sex)
            out.update(
                _odd_band_cells(
                    group, earnings, birth_year, rows, bounds, caps
                )
            )
        for cohort in ODD_AIME_COHORTS:
            group = f"odd.{sex_label}.{cohort}"
            rows = group_rows(group, earnings, birth_year, sex)
            aime = aime_35(earnings[rows], birth_year[rows], nawi)
            out.update(_quantile_cells(group, aime, "aime", AIME_QUANTILES))
        for cohort in PARTIAL_AIME_COHORTS:
            group = f"odd.{sex_label}.{cohort}"
            rows = group_rows(group, earnings, birth_year, sex)
            value = partial_aime(earnings[rows], nawi)
            out.update(_quantile_cells(group, value, "paime", AIME_QUANTILES))
    return out


def pre_career_cells(
    earnings: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    wage_bases: Mapping[int, float],
    nawi: Mapping[int, float],
) -> dict[str, CellValue]:
    """Every cell of family ``pre`` for one matrix (true or filled).

    Per sex and the cohorts born 1930-1945 (masked years 1951-1967):
    ``aime_p10`` ... ``aime_p90``; ``pzero``, the share of masked
    person-years at ages 18 and over with no earnings; ``plevel``, their
    mean earnings over the wage base; ``pr_in``, the Spearman of 1962
    against 1967 (both masked); ``pr_cross``, of 1965 against 1970 (masked
    against recorded).

    Per sex and the cohorts born 1946-1980 (masked years: ages to 21):
    ``yzero`` and ``ylevel`` over ages 15-21; ``yr_cross``, the Spearman of
    earnings at age 21 against age 24; ``paime_p10`` ... ``paime_p90``.

    Correlations are among persons positive in both years.
    """

    earnings = np.asarray(earnings, dtype=np.float64)
    birth_year = np.asarray(birth_year, dtype=np.int64)
    sex = np.asarray(sex)
    _check_matrix(earnings, birth_year)
    years = np.asarray(YEARS)
    masked = pre_career_mask(birth_year)
    caps = np.array([float(wage_bases[year]) for year in YEARS])
    share_of_cap = earnings / caps[None, :]
    age = years[None, :] - birth_year[:, None]
    out: dict[str, CellValue] = {}
    for sex_label in SEXES:
        for cohort in PRE_CAREER_COHORTS:
            group = f"pre.{sex_label}.{cohort}"
            rows = group_rows(group, earnings, birth_year, sex)
            aime = aime_35(earnings[rows], birth_year[rows], nawi)
            out.update(_quantile_cells(group, aime, "aime", AIME_QUANTILES))
            adult = masked[rows] & (age[rows] >= _PRE_ADULT_AGE)
            values = earnings[rows][adult]
            out[f"{group}.pzero"] = _share(
                values == 0, np.ones(len(values), dtype=bool)
            )
            out[f"{group}.plevel"] = CellValue(
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
                out[f"{group}.{name}"] = _spearman_mean(
                    [
                        (
                            earnings[rows, _column(first)],
                            earnings[rows, _column(second)],
                        )
                    ]
                )
        for cohort in YOUTH_COHORTS:
            group = f"pre.{sex_label}.{cohort}"
            rows = group_rows(group, earnings, birth_year, sex)
            young = (
                masked[rows]
                & (age[rows] >= _YOUTH_AGES[0])
                & (age[rows] <= _YOUTH_AGES[1])
            )
            values = earnings[rows][young]
            out[f"{group}.yzero"] = _share(
                values == 0, np.ones(len(values), dtype=bool)
            )
            out[f"{group}.ylevel"] = CellValue(
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
            out[f"{group}.yr_cross"] = _spearman_mean(
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
            value = partial_aime(earnings[rows], nawi)
            out.update(_quantile_cells(group, value, "paime", AIME_QUANTILES))
    return out


def family_cells(
    family: str,
    earnings: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    wage_bases: Mapping[int, float],
    nawi: Mapping[int, float],
) -> dict[str, CellValue]:
    """:func:`odd_cells` for ``"odd"``, :func:`pre_career_cells` for ``"pre"``."""

    if family == "odd":
        return odd_cells(earnings, birth_year, sex, wage_bases, nawi)
    if family == "pre":
        return pre_career_cells(earnings, birth_year, sex, wage_bases, nawi)
    raise ValueError(f"unknown family {family!r}")


def cell_metric(cell_id: str) -> str:
    """``abs_gap`` for a rank correlation, ``log_ratio`` for every other cell."""

    statistic = cell_id.rsplit(".", 1)[-1]
    return "abs_gap" if statistic in _CORRELATIONS else "log_ratio"


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


# --------------------------------------------------------------------------
# Floors and partition
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class FloorGroup:
    """One floor group: per-cell replicate errors, sigma and events.

    ``replicates[cell]`` holds ``[m(A) - m(B)] / sqrt(2)`` on the cell's
    scale for each replicate pair; ``sigma[cell]`` is their root mean
    square (NaN if any replicate is not finite); ``min_events[cell]`` holds
    the smaller of the pair's events for each replicate.
    """

    group: str
    sample_size: int
    pool_size: int
    seed: tuple[int, ...]
    replicates: dict[str, tuple[float, ...]]
    sigma: dict[str, float]
    min_events: dict[str, tuple[int, ...]]


def floor_group(
    group: str,
    cells: Callable[[np.ndarray], Mapping[str, CellValue]],
    pool: np.ndarray,
    sample_size: int,
    *,
    group_index: int,
    n_replicates: int = N_FLOOR_REPLICATES,
) -> FloorGroup:
    """The group's cells' sampling standard errors at ``sample_size`` persons.

    Each replicate draws two disjoint samples of ``sample_size`` persons
    from ``pool`` (row indices of the group's persons on DEV,
    :func:`group_rows`) with the stream ``default_rng([FLOOR_SEED_BASE,
    group_index, n_replicates, sample_size])``, computes the group's cells
    on each (``cells`` maps row indices to cell values and may return other
    cells, which are ignored), and records ``[m(A) - m(B)] / sqrt(2)``.
    For two independent samples the root mean square estimates one
    sample's standard error.
    """

    pool = np.asarray(pool)
    if 2 * sample_size > len(pool):
        raise ValueError(
            f"{group}: two samples of {sample_size} exceed the pool of "
            f"{len(pool)}"
        )
    seed = (
        FLOOR_SEED_BASE,
        int(group_index),
        int(n_replicates),
        int(sample_size),
    )
    rng = np.random.default_rng(list(seed))
    replicates: dict[str, list[float]] = {}
    events: dict[str, list[int]] = {}
    for _ in range(n_replicates):
        drawn = rng.choice(pool, size=2 * sample_size, replace=False)
        first = cells(np.sort(drawn[:sample_size]))
        second = cells(np.sort(drawn[sample_size:]))
        for cell_id, value in first.items():
            if group_of(cell_id) != group:
                continue
            replicates.setdefault(cell_id, []).append(
                gap(cell_id, value.value, second[cell_id].value) / np.sqrt(2.0)
            )
            events.setdefault(cell_id, []).append(
                min(value.events, second[cell_id].events)
            )
    if not replicates:
        raise ValueError(f"{group}: the cell function returned no cell of it")
    sigma = {}
    for cell_id, values in replicates.items():
        array = np.asarray(values, dtype=np.float64)
        sigma[cell_id] = (
            float(np.sqrt(np.mean(array**2)))
            if np.isfinite(array).all()
            else float("nan")
        )
    return FloorGroup(
        group=group,
        sample_size=int(sample_size),
        pool_size=len(pool),
        seed=seed,
        replicates={k: tuple(map(float, v)) for k, v in replicates.items()},
        sigma=sigma,
        min_events={k: tuple(map(int, v)) for k, v in events.items()},
    )


def partition(
    truth: Mapping[str, CellValue], floors: Mapping[str, FloorGroup]
) -> dict[str, str]:
    """``"gates"`` or the reason a cell is report-only, for every DEV cell.

    A cell gates if its true DEV value is finite (and positive, for a log
    ratio), its floor sigma is finite and positive, and the smaller sample
    of a floor pair has at least MIN_EVENTS events in at least EVENTS_SHARE
    of the replicates. The reasons are checked in that order.
    """

    out = {}
    for cell_id, value in truth.items():
        floor = floors.get(group_of(cell_id))
        sigma = np.nan if floor is None else floor.sigma.get(cell_id, np.nan)
        if not np.isfinite(value.value) or (
            cell_metric(cell_id) == "log_ratio" and value.value <= 0
        ):
            out[cell_id] = "truth_undefined"
        elif not np.isfinite(sigma) or sigma <= 0:
            out[cell_id] = "floor_undefined"
        elif (
            np.mean(np.asarray(floor.min_events[cell_id]) >= MIN_EVENTS)
            < EVENTS_SHARE
        ):
            out[cell_id] = "too_few_events"
        else:
            out[cell_id] = "gates"
    return out


# --------------------------------------------------------------------------
# Scoring and adoption
# --------------------------------------------------------------------------
def score(
    truth: Mapping[str, CellValue],
    filled: Sequence[Mapping[str, CellValue]],
    tolerance: Mapping[str, float],
    gating: Iterable[str],
) -> dict[str, object]:
    """Score filled cells (one mapping per draw seed) against the truth.

    A cell's filled value is the mean of its values over the draws; its
    gap is :func:`gap` of that mean against the truth. A gating cell passes
    if its gap is finite and ``|gap| <= tolerance``; the family passes if
    every gating cell passes. Report-only cells get a gap and no verdict.
    """

    gating = set(gating)
    cells = {}
    for cell_id, value in sorted(truth.items()):
        values = np.asarray([draw[cell_id].value for draw in filled])
        filled_value = float(values.mean()) if len(values) else np.nan
        distance = gap(cell_id, filled_value, value.value)
        row = {
            "truth": float(value.value),
            "filled": filled_value,
            "gap": distance,
            "seed_sd": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        }
        if cell_id in gating:
            row["tolerance"] = float(tolerance[cell_id])
            row["passes"] = bool(
                np.isfinite(distance) and abs(distance) <= tolerance[cell_id]
            )
        cells[cell_id] = row
    verdicts = [row["passes"] for row in cells.values() if "passes" in row]
    return {
        "cells": cells,
        "n_gating": len(verdicts),
        "n_failing": int(sum(not passed for passed in verdicts)),
        "passes": bool(verdicts) and all(verdicts),
    }


def adoption_tier(
    candidate: Mapping[str, object], current: Mapping[str, object]
) -> str:
    """A scored candidate's tier against the current rule's score.

    ``"certified"``: the candidate passes the gate (every gating cell within
    tolerance). ``"improves"``: it fails, but in every gating cell its gap
    is finite and at most ``max(tau, min(|current gap|, IMPROVES_CAP *
    tau))`` (a non-finite current gap counts as infinite), and it fails
    strictly fewer gating cells than the current rule. ``"not_adopted"``
    otherwise. Both scores are :func:`score` results on the same persons
    and family.
    """

    if candidate["passes"]:
        return "certified"
    if candidate["n_failing"] >= current["n_failing"]:
        return "not_adopted"
    for cell_id, row in candidate["cells"].items():
        if "passes" not in row:
            continue
        own = float(row["gap"])
        tau = float(row["tolerance"])
        baseline = float(current["cells"][cell_id]["gap"])
        baseline = abs(baseline) if np.isfinite(baseline) else np.inf
        allowed = max(tau, min(baseline, IMPROVES_CAP * tau))
        if not np.isfinite(own) or abs(own) > allowed:
            return "not_adopted"
    return "improves"


#: Tiers in order of preference.
ADOPTION_TIERS: tuple[str, ...] = ("certified", "improves", "not_adopted")


def adopt(primary_tier: str, alternative_tier: str) -> str | None:
    """``"primary"``, ``"alternative"`` or None (the current rule stays).

    The candidate in the better tier is adopted; on a tie the primary is.
    Nothing is adopted when both are ``"not_adopted"``.
    """

    rank = {tier: index for index, tier in enumerate(ADOPTION_TIERS)}
    if primary_tier == alternative_tier == "not_adopted":
        return None
    if rank[alternative_tier] < rank[primary_tier]:
        return "alternative"
    return "primary"


def earnings_from_shares(shares: np.ndarray) -> np.ndarray:
    """Capped earnings from shares of the wage base, exact at the cap."""

    caps = np.array([float(_wage_base(year)) for year in YEARS])
    shares = np.asarray(shares, dtype=np.float64)
    return np.where(shares >= 1.0, caps[None, :], shares * caps[None, :])


def _wage_base(year: int) -> float:
    from populace_dynamics.harness.epuf_operator import wage_base

    return float(wage_base(year))


class FillOutputInvalid(ValueError):
    """A candidate's output broke a fill-validity invariant."""


def score_candidate(
    fill,
    family: str,
    matrix: EPUFMatrix,
    truth: Mapping[str, CellValue],
    tolerance: Mapping[str, float],
    gating: Iterable[str],
    *,
    seeds: Sequence[int] = DRAW_SEEDS,
    wage_bases: Mapping[int, float],
    nawi: Mapping[int, float],
) -> dict[str, object]:
    """Score one candidate fill on one part, under the registered protocol.

    ``fill.fill(shares, years, birth_year, sex, person_key, fill_mask,
    seed)`` receives shares of the wage base with NaN in every cell of the
    union mask (both families' masked years) and fills the cells of its
    own family's mask. Each draw must leave every other cell exactly as
    given and return finite shares in [0, 1] on the masked cells
    (:class:`FillOutputInvalid` otherwise). The filled cells replace the
    truth's own-family masked cells; every other cell stays true. The
    score is :func:`score` over ``seeds``, with the truth's cells passed in.
    """

    years = np.asarray(YEARS)
    caps = np.array([float(wage_bases[year]) for year in YEARS])
    shares = matrix.earnings / caps[None, :]
    hidden = union_mask(matrix.birth_year)
    own = family_mask(family, matrix.birth_year)
    given = np.where(hidden, np.nan, shares)
    draws = []
    for seed in seeds:
        out = fill.fill(
            given.copy(),
            years,
            matrix.birth_year,
            matrix.sex,
            matrix.person_id,
            own.copy(),
            int(seed),
        )
        out = np.asarray(out, dtype=np.float64)
        if out.shape != given.shape:
            raise FillOutputInvalid("the fill changed the matrix's shape")
        filled = out[own]
        if not np.isfinite(filled).all():
            raise FillOutputInvalid("a masked cell came back not finite")
        if (filled < 0).any() or (filled > 1).any():
            raise FillOutputInvalid("a masked cell came back outside [0, 1]")
        others = ~own
        same = (out[others] == given[others]) | (
            np.isnan(out[others]) & np.isnan(given[others])
        )
        if not same.all():
            raise FillOutputInvalid("the fill changed a cell it does not own")
        earnings = np.where(
            own,
            np.where(out >= 1.0, caps[None, :], out * caps[None, :]),
            matrix.earnings,
        )
        draws.append(
            family_cells(
                family,
                earnings,
                matrix.birth_year,
                matrix.sex,
                wage_bases,
                nawi,
            )
        )
    family_truth = {
        cell_id: value
        for cell_id, value in truth.items()
        if cell_id.startswith(f"{family}.")
    }
    return score(family_truth, draws, tolerance, gating)


# --------------------------------------------------------------------------
# Oracles (report-only)
# --------------------------------------------------------------------------
def _share_bins(shares: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """0 zero, 1..N positive below the cap, N+1 at it, N+2 unknown."""

    bins = np.searchsorted(edges, shares, side="right") + 1
    bins = np.where(shares <= 0, 0, bins)
    bins = np.where(shares >= 1.0, N_SHARE_BINS + 1, bins)
    return np.where(np.isnan(shares), N_SHARE_BINS + 2, bins)


def share_bin_edges(shares: np.ndarray) -> np.ndarray:
    """The N_SHARE_BINS - 1 quantile edges of positive shares below the cap."""

    shares = np.asarray(shares, dtype=np.float64).ravel()
    inside = shares[(shares > 0) & (shares < 1.0)]
    return np.quantile(inside, np.linspace(0, 1, N_SHARE_BINS + 1)[1:-1])


def _permute_within(keys: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """A permutation of positions that moves each only within its key."""

    order = np.lexsort((rng.random(len(keys)), keys))
    target = np.argsort(keys, kind="stable")
    out = np.empty(len(keys), dtype=np.int64)
    out[target] = order
    return out


def odd_oracle_fill(
    earnings: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    wage_bases: Mapping[int, float],
    seed: int,
) -> np.ndarray:
    """Oracle O1: each masked odd year's true value, permuted within strata.

    For each masked year ``t`` the persons are grouped by sex, membership
    of the ``odd`` universe, five-year age band at ``t``, and the bins
    (:func:`share_bin_edges`, from the supplied persons' recorded even
    years 1996-2006; a neighbour inside the pre-career mask is unknown) of
    their shares of the wage base at ``t-1`` and ``t+1``; within a group
    the true values at ``t`` are permuted. It is a fill with no model error
    given that conditioning set; it is reported, never gated.
    """

    earnings = np.asarray(earnings, dtype=np.float64)
    birth_year = np.asarray(birth_year, dtype=np.int64)
    caps = np.array([float(wage_bases[year]) for year in YEARS])
    share = np.where(
        pre_career_mask(birth_year), np.nan, earnings / caps[None, :]
    )
    edges = share_bin_edges(
        np.nan_to_num(
            share[:, [_column(year) for year in ODD_OBSERVED_YEARS]], nan=0.0
        )
    )
    rng = np.random.default_rng([seed, 1])
    member = family_universe("odd", earnings, birth_year, sex).astype(np.int64)
    out = earnings.copy()
    for year in MASKED_ODD_YEARS:
        age_band = np.digitize(year - birth_year, _ORACLE_AGE_EDGES)
        key = (
            (np.asarray(sex, dtype=np.int64) * 2 + member) * 100 + age_band
        ) * 10_000 + _share_bins(share[:, _column(year - 1)], edges) * 100
        key = key + _share_bins(share[:, _column(year + 1)], edges)
        positions = _permute_within(key, rng)
        out[:, _column(year)] = earnings[positions, _column(year)]
    return out


def pre_career_oracle_fill(
    earnings: np.ndarray,
    birth_year: np.ndarray,
    sex: np.ndarray,
    wage_bases: Mapping[int, float],
    seed: int,
) -> np.ndarray:
    """Oracle O2: whole masked pre-career blocks permuted within strata.

    Persons are grouped by sex, birth year, membership of the ``pre``
    universe, the number of positive years among their first five years
    from ``max(1968, birth_year + 22)`` that the PSID records (a masked odd
    year is unknown), and the quintile, within sex and birth year, of their
    mean share of the wage base over those positive years (0 when none is
    positive). Within a group the masked blocks, which cover the same
    calendar years, are permuted whole. Reported, never gated.
    """

    earnings = np.asarray(earnings, dtype=np.float64)
    birth_year = np.asarray(birth_year, dtype=np.int64)
    sex = np.asarray(sex, dtype=np.int64)
    caps = np.array([float(wage_bases[year]) for year in YEARS])
    share = np.where(
        odd_mask(len(birth_year)), np.nan, earnings / caps[None, :]
    )
    start = _career_start(birth_year)
    columns = (start - FIRST_YEAR)[:, None] + np.arange(5)[None, :]
    inside = columns <= _column(LAST_YEAR)
    first_five = np.where(
        inside,
        share[
            np.arange(len(share))[:, None],
            np.minimum(columns, _column(LAST_YEAR)),
        ],
        np.nan,
    )
    known = np.nan_to_num(first_five, nan=0.0)
    positive = (known > 0).sum(axis=1)
    mean_share = np.where(
        positive > 0,
        np.where(known > 0, known, 0.0).sum(axis=1) / np.maximum(positive, 1),
        0.0,
    )
    quintile = np.zeros(len(share), dtype=np.int64)
    stratum = sex * 10_000 + birth_year
    for value in np.unique(stratum):
        rows = (stratum == value) & (positive > 0)
        if rows.sum() >= 5:
            edges = np.quantile(mean_share[rows], [0.2, 0.4, 0.6, 0.8])
            quintile[rows] = np.searchsorted(edges, mean_share[rows]) + 1
        else:
            quintile[rows] = 1
    member = family_universe("pre", earnings, birth_year, sex)
    key = ((stratum * 2 + member) * 10 + positive) * 10 + quintile
    rng = np.random.default_rng([seed, 2])
    positions = _permute_within(key, rng)
    mask = pre_career_mask(birth_year)
    out = earnings.copy()
    out[mask] = earnings[positions][mask]
    return out


# --------------------------------------------------------------------------
# EPUF as a matrix, and the audited TEST read
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class EPUFMatrix:
    """EPUF as persons by years 1951-2006 of capped earnings (float64)."""

    person_id: np.ndarray
    birth_year: np.ndarray
    sex: np.ndarray
    earnings: np.ndarray


class TestPartLocked(PermissionError):
    """TEST may be read only through :func:`test_part`, after lock."""


_TEST_TOKEN = object()


def epuf_matrix(
    part: int | None = None,
    *,
    data_dir: Path | None = None,
    _token: object = None,
) -> EPUFMatrix:
    """Read the pinned EPUF and return TRAIN or DEV as a matrix.

    A person-year with no row in the annual file is zero. Rows follow the
    demographic file's order of person ids. Reading verifies the pinned
    SHA-256 of both members (:mod:`populace_dynamics.data.epuf`) and that
    every annual row joins one demographic person, once per year. TEST (and
    the whole file, ``part=None``) are refused here; read TEST through
    :func:`test_part`.
    """

    if (part is None or int(part) == TEST) and _token is not _TEST_TOKEN:
        raise TestPartLocked(
            "TEST is read only through epuf_fill_gate.test_part(), after the "
            "gate locks"
        )
    from populace_dynamics.data import epuf

    demographic = epuf.read_demographic(data_dir=data_dir)
    annual = epuf.read_annual(data_dir=data_dir)
    ids = demographic["person_id"].to_numpy()
    order = np.argsort(ids, kind="stable")
    ids = ids[order]
    if (np.diff(ids) <= 0).any():
        raise ValueError("EPUF demographic person ids are not unique")
    annual_ids = annual["person_id"].to_numpy()
    position = np.searchsorted(ids, annual_ids)
    if (position >= len(ids)).any() or (
        ids[np.minimum(position, len(ids) - 1)] != annual_ids
    ).any():
        raise ValueError("an EPUF annual row has no demographic person")
    annual_years = annual["year"].to_numpy().astype(np.int64)
    if (annual_years < FIRST_YEAR).any() or (annual_years > LAST_YEAR).any():
        raise ValueError(
            f"an EPUF annual row lies outside {FIRST_YEAR}-{LAST_YEAR}"
        )
    pair = position.astype(np.int64) * 100 + (annual_years - FIRST_YEAR)
    if len(np.unique(pair)) != len(pair):
        raise ValueError("EPUF has two annual rows for one person-year")
    keep = (
        np.ones(len(ids), dtype=bool)
        if part is None
        else split_part(ids) == int(part)
    )
    row_of = np.full(len(ids), -1, dtype=np.int64)
    row_of[np.flatnonzero(keep)] = np.arange(int(keep.sum()))
    rows = row_of[position]
    inside = rows >= 0
    earnings = np.zeros((int(keep.sum()), len(YEARS)), dtype=np.float64)
    earnings[rows[inside], annual_years[inside] - FIRST_YEAR] = annual[
        "earnings"
    ].to_numpy()[inside]
    return EPUFMatrix(
        person_id=ids[keep],
        birth_year=demographic["birth_year"]
        .to_numpy()[order][keep]
        .astype(np.int64),
        sex=demographic["sex"].to_numpy()[order][keep].astype(np.int64),
        earnings=earnings,
    )


def _gate_lock_status(gates_path: Path) -> dict[str, object]:
    import yaml

    document = yaml.safe_load(gates_path.read_text())
    block = (document.get("gates") or {}).get("gate_epuf_fill") or {}
    thresholds = block.get("thresholds") or {}
    return {
        "locked": bool(block.get("locked")) and bool(thresholds.get("locked")),
        "registration_id": block.get("registration_id"),
    }


def test_part(
    *, gates_path: Path | None = None, data_dir: Path | None = None
) -> EPUFMatrix:
    """The audited TEST read: refused unless ``gates.yaml`` locks this gate.

    ``gates.gate_epuf_fill`` must carry ``locked: true`` with locked
    thresholds and this module's registration id.
    """

    gates_path = (
        Path(__file__).resolve().parents[3] / "gates.yaml"
        if gates_path is None
        else Path(gates_path)
    )
    status = _gate_lock_status(gates_path)
    if not status["locked"] or status["registration_id"] != REGISTRATION_ID:
        raise TestPartLocked(
            f"gate_epuf_fill is not locked in {gates_path}; TEST stays unread"
        )
    return epuf_matrix(TEST, data_dir=data_dir, _token=_TEST_TOKEN)


test_part.__test__ = False  # not a pytest test despite its name
