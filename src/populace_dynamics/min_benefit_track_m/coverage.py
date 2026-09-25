"""Years of coverage from an earnings history (plan field G6).

Python rules (not Axiom).  *Y* counts the years through the last year of
the record's basis (the M1 specification's section 4a) whose covered
earnings reach four quarters of coverage; all ages; unobserved years count
as zero and are flagged.  Table 5 of the Report defines a work year as a
year with four covered quarters ("work year = 4 CQ", cleared extract).

The **covered-earnings convention** (cos decision d280, ruled 2026-09-25:
"same shared assumption, disclosed in the spec and every result"): the
PSID has no covered/noncovered split, so the caller passes PSID labor
income and it is treated as covered earnings, as exercises 1 and 3 and
Track C do.  That is a named delta (noncovered public employment counts),
not a statute reading.

**Quarters of coverage** (frozen in ``m1-draft-2``; referee R6).  From 1978
on, 42 USC 413(a)(2)(A)(ii) and 20 CFR 404.143(a) credit one quarter for
each quarter-of-coverage amount of the year's wages and self-employment
income, at most four, so four quarters' amount is the annual test.  Before
1978, 413(a)(2)(A)(i) and 20 CFR 404.141(b) credit a quarter of coverage
for $50 of wages paid in it or $100 of self-employment income credited to
it; with annual amounts and wages taken as spread over the year, a year
counts at $200 (``statute_413_a_50_per_quarter``, the default).  This
reading does not separate self-employment income ($400 a year) or
agricultural wages (413(a)(2)(B)(iv); 20 CFR 404.141(c)), and it credits
four quarters to a year whose $200 was paid in fewer quarters (a named
delta).  413(a)(2)(B)(ii) and 20 CFR 404.141(d)(1) credit all four quarters
when a year's wages reach the annual limitation.  The statute and
regulation were read from law.cornell.edu copies saved in
``EV/track-m-review-20260924/`` (413: SHA-256 ``7d226c0a…``; 404.141:
``7b1b195c…``).  The plan's G6 convention (the 1978 amount scaled back by
the average wage index) has no statutory basis and is not registered; it
stays selectable (``qc_1978_scaled_back_by_awi``) only for the Table 2
formula check that shows the difference.

What this module does not do:

* It does not compute quarters within a year: a year counts when its
  covered earnings reach four quarters' amount, never three or fewer.
* It does not decide the section 4a years; the caller passes
  ``through_year`` (the last year of *Y*) from the cohort.

**One history per worker** (frozen in ``m1-draft-2``; referee R7).  The
earnings panel (``data/family.py``) carries labor income for every year
through 1996 and for even years from 1998; it has no odd income year from
1997.  By the family files' labels, the labor income of 1997 and 1999 was
never asked, while that of each odd year 2001-2021 was asked one wave
later as the reference person's and the spouse's labor income of the year
before last (for example ER85328 and ER85376 in 2023, each with a time
unit and an accuracy code; ``structure.verify_prior_year_labor_income_
labels``).  :func:`one_history` builds the one history that both *Y* and
the PIA read: the observed years, then those next-wave items
(``odd_year_source = "next_wave_reference_person_and_spouse"``; plan item
M3 reads them), then, for an odd year 1997-2021 still unobserved, the
immediate-neighbor law of ``estimates.career`` (``_impute_gap``: the mean
of the two neighboring years, or the one neighbor that exists; never a
neighbor after the count's end year).  A year still unobserved after that
counts as zero in both and is flagged.

The quarter-of-coverage amounts load from the policyengine-us checkout the
oracle already reads (``quarters_of_coverage_threshold.yaml``, which cites
42 USC 413(d)(2), 20 CFR 404.143 and SSA's QC table), with the checkout's
revision and the file's SHA-256 recorded.  That is a read of the local
parameter tree, not a committed capture.
"""

from __future__ import annotations

import hashlib
import math
import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from populace_dynamics.min_benefit_track_m.policy import (
    GAP_YEARS_NEIGHBOR,
    PRE_1978_SCALED_BY_AWI,
    PRE_1978_STATUTE_50_PER_QUARTER,
    TrackMPolicy,
)

__all__ = [
    "FIRST_QC_YEAR",
    "NEXT_WAVE_ODD_YEARS",
    "PRE_1978_WAGES_PER_QUARTER",
    "PSID_BIENNIAL_GAP_YEARS",
    "QC_PARAMETER_PATH",
    "CoverageCount",
    "OneHistory",
    "QuarterOfCoverageAmounts",
    "annual_coverage_amount",
    "count_coverage_years",
    "load_qc_amounts",
    "one_history",
]

#: The first year of the annual quarter-of-coverage amount (the
#: policyengine-us series starts in 1978, when annual reporting began).
FIRST_QC_YEAR = 1978
#: Odd income years the earnings panel does not carry (waves 1999-2023
#: report the prior even year as last year's income; the 1997 wave was the
#: last annual one).  1997 and 1999 were never asked; 2001-2021 were asked
#: one wave later (module docstring).  The neighbor law fills only those of
#: them a caller leaves unobserved.
PSID_BIENNIAL_GAP_YEARS: tuple[int, ...] = tuple(range(1997, 2022, 2))
#: The odd income years the next wave asks as labor income of the year
#: before last (reference person and spouse): 2001-2021.
NEXT_WAVE_ODD_YEARS: tuple[int, ...] = tuple(range(2001, 2022, 2))
#: Before 1978, 42 USC 413(a)(2)(A)(i): a quarter of coverage for $50 of
#: wages paid in the quarter.
PRE_1978_WAGES_PER_QUARTER = 50.0
#: The policyengine-us parameter file (relative to the checkout root).
QC_PARAMETER_PATH = Path(
    "policyengine_us/parameters/gov/ssa/social_security/"
    "quarters_of_coverage_threshold.yaml"
)
#: The environment variable and default checkout that
#: ``populace_dynamics.ss.params.load_ssa_parameters`` reads (repeated
#: here, not imported, because the oracle keeps them private).
_PE_US_ENV = "POPULACE_DYNAMICS_PE_US_DIR"
_PE_US_DEFAULT = Path("~/PolicyEngine/policyengine-us").expanduser()


@dataclass(frozen=True)
class QuarterOfCoverageAmounts:
    """The amount that credits one quarter of coverage, by year.

    ``amounts`` maps a calendar year (1978 on) to dollars.  ``source``
    records where they came from (the policyengine-us revision and the
    file's SHA-256, or ``"invented"`` in tests).
    """

    amounts: Mapping[int, float]
    source: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.amounts:
            raise ValueError("no quarter-of-coverage amounts")
        for year, amount in self.amounts.items():
            if isinstance(year, bool) or not isinstance(year, int):
                raise TypeError(f"year {year!r} must be an integer")
            if not (math.isfinite(float(amount)) and amount > 0):
                raise ValueError(f"amount for {year} must be positive")

    def amount(self, year: int) -> float:
        if year not in self.amounts:
            raise KeyError(f"no quarter-of-coverage amount for {year}")
        return float(self.amounts[year])


def _resolve_pe_us(pe_us_dir: Path | None) -> Path:
    if pe_us_dir is not None:
        return Path(pe_us_dir).expanduser()
    env = os.environ.get(_PE_US_ENV)
    return Path(env).expanduser() if env else _PE_US_DEFAULT


def load_qc_amounts(pe_us_dir: Path | None = None) -> QuarterOfCoverageAmounts:
    """Read the quarter-of-coverage amounts from policyengine-us.

    Each ``values`` key is a date; its year keys the amount.  The file's
    SHA-256 and the checkout's short revision are recorded.
    """

    root = _resolve_pe_us(pe_us_dir)
    path = root / QC_PARAMETER_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"policyengine-us quarter-of-coverage parameter not found at "
            f"{path}; set {_PE_US_ENV} or clone policyengine-us"
        )
    raw = path.read_bytes()
    document = yaml.safe_load(raw.decode("utf-8"))
    amounts: dict[int, float] = {}
    for key, value in document["values"].items():
        year = int(str(key)[:4])
        if year in amounts:
            raise ValueError(f"two quarter-of-coverage amounts for {year}")
        amounts[year] = float(value)
    try:
        revision = subprocess.run(
            ["git", "log", "-1", "--format=%h"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        revision = "unknown"
    return QuarterOfCoverageAmounts(
        amounts=amounts,
        source={
            "kind": "policyengine_us_checkout",
            "path": str(QC_PARAMETER_PATH),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "pe_us_revision": revision,
        },
    )


def annual_coverage_amount(
    year: int,
    qc: QuarterOfCoverageAmounts,
    nawi: Mapping[int, float],
    policy: TrackMPolicy | None = None,
) -> float:
    """Covered earnings a year needs to count as a work year.

    ``policy.quarters_per_work_year`` (4) times the year's
    quarter-of-coverage amount from 1978 on.  Before 1978,
    ``pre_1978_coverage_rule``: the statute's $50 a quarter, $200 a year
    (``statute_413_a_50_per_quarter``, the default); or, unregistered and
    kept for the Table 2 check only, the plan's G6 convention, the 1978
    amount scaled back by the average wage index,
    ``QC(1978) * AWI(year) / AWI(1978)``.
    """

    policy = policy or TrackMPolicy()
    quarters = policy.quarters_per_work_year
    if year >= FIRST_QC_YEAR:
        return quarters * qc.amount(year)
    if policy.pre_1978_coverage_rule == PRE_1978_STATUTE_50_PER_QUARTER:
        return quarters * PRE_1978_WAGES_PER_QUARTER
    if policy.pre_1978_coverage_rule != PRE_1978_SCALED_BY_AWI:
        raise ValueError(policy.pre_1978_coverage_rule)
    for needed in (year, FIRST_QC_YEAR):
        if needed not in nawi:
            raise KeyError(f"no average wage index for {needed}")
    scaled = qc.amount(FIRST_QC_YEAR) * nawi[year] / nawi[FIRST_QC_YEAR]
    return quarters * scaled


@dataclass(frozen=True)
class CoverageCount:
    """Years of coverage and the flags G6 asks for.

    ``years`` is *Y*: the number of years through ``through_year`` whose
    covered earnings (observed, or imputed for a biennial gap year) reach
    :func:`annual_coverage_amount`.  ``imputed_years`` are the gap years
    the neighbor law filled; ``unobserved_years`` are the years of the flag
    window (from the year of attaining ``unobserved_window_start_age``
    through ``through_year``) that are neither observed nor imputed; they
    count as zero.  ``flagged`` is true when either exists.
    """

    years: int
    counted_years: tuple[int, ...]
    observed_years: tuple[int, ...]
    imputed_years: tuple[int, ...]
    unobserved_years: tuple[int, ...]
    through_year: int

    @property
    def flagged(self) -> bool:
        return bool(self.unobserved_years or self.imputed_years)

    def as_dict(self) -> dict[str, Any]:
        return {
            "years": self.years,
            "counted_years": list(self.counted_years),
            "observed_years": list(self.observed_years),
            "imputed_years": list(self.imputed_years),
            "unobserved_years": list(self.unobserved_years),
            "through_year": self.through_year,
            "flagged": self.flagged,
        }


def _neighbor_value(
    year: int, observed: Mapping[int, float], through_year: int
) -> float | None:
    """The immediate-neighbor law of ``estimates.career._impute_gap``."""

    left = observed.get(year - 1)
    right = observed.get(year + 1) if year + 1 <= through_year else None
    if left is not None and right is not None:
        return (left + right) / 2.0
    if left is not None:
        return left
    return right


def count_coverage_years(
    history: Mapping[int, float],
    *,
    birth_year: int,
    through_year: int,
    qc: QuarterOfCoverageAmounts,
    nawi: Mapping[int, float],
    policy: TrackMPolicy | None = None,
    gap_years: tuple[int, ...] = PSID_BIENNIAL_GAP_YEARS,
    imputed_years: tuple[int, ...] = (),
) -> CoverageCount:
    """Count the work years in ``history`` through ``through_year`` (G6).

    ``history`` maps a calendar year to that year's covered earnings (PSID
    labor income treated as covered, d280).  A year absent from the
    mapping, or whose value is missing (NaN), is unobserved.  Under
    ``gap_year_rule`` ``immediate_neighbor_mean`` an unobserved year in
    ``gap_years`` takes its neighbors' mean (or the one neighbor); every
    other unobserved year counts as zero.  Every year through
    ``through_year`` (section 4a's last year of *Y*) is eligible, whatever
    the age (G6: all ages).  A caller that has built the one history
    (:func:`one_history`) passes its ``values`` with ``gap_years=()`` and
    its ``imputed_years``, so *Y* and the PIA read the same years.
    """

    policy = policy or TrackMPolicy()
    for label, value in (
        ("birth_year", birth_year),
        ("through_year", through_year),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{label} must be an integer year, not {value!r}")
    observed: dict[int, float] = {}
    for raw_year, raw_value in history.items():
        year = int(raw_year)
        if year > through_year:
            continue
        earnings = float(raw_value)
        if math.isnan(earnings):
            continue
        if earnings < 0:
            raise ValueError(f"negative covered earnings in {year}")
        observed[year] = earnings
    values = dict(observed)
    imputed: list[int] = sorted(
        year for year in imputed_years if year in observed
    )
    if policy.gap_year_rule == GAP_YEARS_NEIGHBOR:
        for year in sorted(gap_years):
            if year > through_year or year in observed:
                continue
            value = _neighbor_value(year, observed, through_year)
            if value is not None:
                values[year] = value
                imputed.append(year)
    counted = [
        year
        for year in sorted(values)
        if values[year] >= annual_coverage_amount(year, qc, nawi, policy)
    ]
    window_start = birth_year + policy.unobserved_window_start_age
    unobserved = tuple(
        year
        for year in range(window_start, through_year + 1)
        if year not in values
    )
    return CoverageCount(
        years=len(counted),
        counted_years=tuple(counted),
        observed_years=tuple(
            sorted(year for year in observed if year not in imputed)
        ),
        imputed_years=tuple(sorted(imputed)),
        unobserved_years=unobserved,
        through_year=through_year,
    )


@dataclass(frozen=True)
class OneHistory:
    """The one history *Y* and the PIA read (section 4a; referee R7).

    ``values`` maps each year through ``last_year`` that is observed,
    reported one wave later, or imputed to its covered earnings;
    ``observed_years``, ``next_wave_years`` and ``imputed_years`` say which.
    A year in none of them is unobserved and counts as zero in both.
    """

    values: Mapping[int, float]
    observed_years: tuple[int, ...]
    next_wave_years: tuple[int, ...]
    imputed_years: tuple[int, ...]
    last_year: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "values": {
                str(year): v for year, v in sorted(self.values.items())
            },
            "observed_years": list(self.observed_years),
            "next_wave_years": list(self.next_wave_years),
            "imputed_years": list(self.imputed_years),
            "last_year": self.last_year,
        }


def _clean(history: Mapping[int, float], last_year: int) -> dict[int, float]:
    out: dict[int, float] = {}
    for raw_year, raw_value in history.items():
        year = int(raw_year)
        if year > last_year:
            continue
        value = float(raw_value)
        if math.isnan(value):
            continue
        if value < 0:
            raise ValueError(f"negative covered earnings in {year}")
        out[year] = value
    return out


def one_history(
    observed: Mapping[int, float],
    next_wave: Mapping[int, float] | None = None,
    *,
    last_year: int,
    policy: TrackMPolicy | None = None,
    gap_years: tuple[int, ...] = PSID_BIENNIAL_GAP_YEARS,
) -> OneHistory:
    """Observed years, then next-wave odd years, then the gap rule (R7).

    ``observed`` is the earnings panel's labor income by year; ``next_wave``
    the next wave's year-before-last labor income for odd years 2001-2021
    (:data:`NEXT_WAVE_ODD_YEARS`), annualized by the reader (plan item M3).
    A next-wave year the panel also observes is refused, as is a next-wave
    year outside 2001-2021.  Under ``gap_year_rule``
    ``immediate_neighbor_mean`` an odd year in ``gap_years`` still
    unobserved takes the mean of its two neighbors, or the one that exists,
    never a neighbor after ``last_year``.  Missing values (NaN) are
    unobserved; negative ones are refused.
    """

    policy = policy or TrackMPolicy()
    if isinstance(last_year, bool) or not isinstance(last_year, int):
        raise TypeError(f"last_year must be an integer year, not {last_year}")
    panel = _clean(observed, last_year)
    reported = _clean(next_wave or {}, last_year)
    outside = sorted(set(reported) - set(NEXT_WAVE_ODD_YEARS))
    if outside:
        raise ValueError(
            f"next-wave labor income exists for 2001-2021 only, not {outside}"
        )
    both = sorted(set(reported) & set(panel))
    if both:
        raise ValueError(f"years {both} are both observed and next-wave")
    values = {**panel, **reported}
    imputed: list[int] = []
    if policy.gap_year_rule == GAP_YEARS_NEIGHBOR:
        for year in sorted(gap_years):
            if year > last_year or year in values:
                continue
            value = _neighbor_value(year, values, last_year)
            if value is not None:
                values[year] = value
                imputed.append(year)
    return OneHistory(
        values=values,
        observed_years=tuple(sorted(panel)),
        next_wave_years=tuple(sorted(reported)),
        imputed_years=tuple(imputed),
        last_year=last_year,
    )
