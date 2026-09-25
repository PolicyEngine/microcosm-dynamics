"""Years of coverage from an earnings history (plan field G6).

Python rules (not Axiom).  The plan's field G6 (revision 2, section 7,
restating v1's): *Y* counts the years before the entitlement year with
covered earnings of at least four times the quarter-of-coverage amount
(1978 on; before 1978 the 1978 amount scaled back by the average wage
index); all ages; unobserved years count as zero and are flagged.  Table 5
of the Report defines a work year as a year with four covered quarters
("work year = 4 CQ", cleared extract).

The **covered-earnings convention** (d219 item 4, pending): the PSID has
no covered/noncovered split, so the caller passes PSID labor income and it
is treated as covered earnings.  That is a named delta (noncovered public
employment counts), not a statute reading.

What this module does not do:

* It does not capture the statute; plan item M2 captures 42 USC
  413(a)-(d).  The pre-1978 rule is a parameter
  (``TrackMPolicy.pre_1978_coverage_rule``) whose default is the plan's
  convention, the 1978 amount scaled back by the average wage index.  The
  statute differs (read by the independent review of 2026-09-24 from
  law.cornell.edu, copies in ``EV/track-m-review-20260924/``): before
  1978, 413(a)(2)(A)(i) and 20 CFR 404.141(b) credit a quarter of coverage
  for $50 of wages paid in it or $100 of self-employment income credited
  to it, and a year's wages at the annual limitation credit all four.  The
  alternative ``statute_413_a_50_per_quarter`` reads that as $200 a year
  (wages spread over the four quarters); it does not separate
  self-employment income ($400 a year) or agricultural wages.  From 1978
  on, 413(a)(2)(A)(ii) and 20 CFR 404.143(a) credit one quarter for each
  quarter-of-coverage amount of the year's wages and self-employment
  income, at most four, so four quarters' amount is the annual test.
* It does not compute quarters within a year: a year counts when its
  covered earnings reach four quarters' amount (the annual test the plan
  proposes), never three or fewer.
* It does not decide the entitlement year; the caller passes
  ``through_year`` (the year before entitlement, G6) from the cohort.

**Biennial gap years.**  The earnings panel (``data/family.py``) carries
labor income for every year through 1996 and for even years from 1998; it
has no odd income year from 1997.  By the family files' labels, the labor
income of 1997 and 1999 was never asked, while that of each odd year
2001-2021 was asked one wave later as the reference person's and the
spouse's labor income of the year before last (for example ER85328 and
ER85376 in 2023, each with a time unit and an accuracy code), items no
reader here reads yet (``structure.verify_prior_year_labor_income_labels``;
plan items M3 and M5).  The plan lists "odd-year gap imputation from 1997
on" among its named deltas and M5's "odd-year gap law", while G6 counts
unobserved years as zero.  The builder reading (``gap_year_rule``,
pending the specification freeze) fills a gap year with the
immediate-neighbor law of ``estimates.career`` (``_impute_gap``: the mean
of the two neighboring years, or the one neighbor that exists) before the
count, and G6's zero then applies to years still unobserved; the
alternative ``zero`` reads G6 literally.  A neighbor after ``through_year``
is never used, as ``estimates.career`` never uses one after the claim.

The quarter-of-coverage amounts load from the policyengine-us checkout the
oracle already reads (``quarters_of_coverage_threshold.yaml``, which cites
42 USC 413(d)(2), 20 CFR 404.143 and SSA's QC table), with the checkout's
revision and the file's SHA-256 recorded.  That is a read of the local
parameter tree, not the committed capture plan item M2 calls for.
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
    "PRE_1978_WAGES_PER_QUARTER",
    "PSID_BIENNIAL_GAP_YEARS",
    "QC_PARAMETER_PATH",
    "CoverageCount",
    "QuarterOfCoverageAmounts",
    "annual_coverage_amount",
    "count_coverage_years",
    "load_qc_amounts",
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
    ``pre_1978_coverage_rule``: the plan's G6 convention (the default), the
    1978 amount scaled back by the average wage index,
    ``QC(1978) * AWI(year) / AWI(1978)``; or the statute's $50 a quarter,
    $200 a year (``statute_413_a_50_per_quarter``).
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
) -> CoverageCount:
    """Count the work years in ``history`` through ``through_year`` (G6).

    ``history`` maps a calendar year to that year's covered earnings (PSID
    labor income under the default convention).  A year absent from the
    mapping, or whose value is missing (NaN), is unobserved.  Under
    ``gap_year_rule`` ``immediate_neighbor_mean`` an unobserved year in
    ``gap_years`` takes its neighbors' mean (or the one neighbor); every
    other unobserved year counts as zero.  Every year through
    ``through_year`` is eligible, whatever the age (G6: all ages).
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
    imputed: list[int] = []
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
        observed_years=tuple(sorted(observed)),
        imputed_years=tuple(imputed),
        unobserved_years=unobserved,
        through_year=through_year,
    )
