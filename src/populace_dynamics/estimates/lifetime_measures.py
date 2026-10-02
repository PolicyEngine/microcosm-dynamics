"""Lifetime-earnings measures and quintiles for the group breakdowns (G2).

Package G2 of the NASI follow-ups (2026-10-01): the lifetime-earnings
dimension of the group breakdowns of the four blind tests.  Every function
here is pure over cohort outputs and never opens a PSID file:

* ``careers``: one row per person-year, ``person_id``, ``year``,
  ``earnings`` (nominal labor earnings) and optionally ``provenance``
  (the cohort builders' career frame, e.g. ``psid2010._careers``);
* ``persons``: ``person_id`` and ``birth_year`` (one row per person);
* ``marriage_episodes``: the already-loaded marriage history in the shape
  of :func:`populace_dynamics.data.marriage.marriage_episodes`, optionally
  with ``separation_year`` alongside (as ``psid2010.marital_state_at``
  reads it);
* :class:`~populace_dynamics.ss.params.SSAParameters` (NAWI and the
  contribution and benefit base).

MINT8 definitions (SSA, MINT8 Table User Guide, dateCertified 2026-04-01,
captured 2026-10-01; verbatim in
``data/external/mint8_lifetime_quintile_definitions.json``).  MINT8's
annual beneficiary tables have no lifetime-earnings row group; its cohort
tables (benefit/tax ratios, initial replacement rates) have three, which
this module implements as the lifetime-earnings dimension:

* "Current-law initial AIME quintile": "Represents an individual's average
  indexed monthly earnings (AIME) under current law at age 62 ... We
  calculate the AIME quintiles for each birth cohort." ->
  :func:`initial_aime_at_62`;
* "Lifetime payroll tax quintile": "Represents the present value of an
  individual's current-law payroll taxes at age 62." ->
  :func:`lifetime_payroll_tax_pv_at_62` with ``shared=False``;
* "Lifetime payroll tax quintile (shared)": "For married couples, the
  payroll taxes paid while married are shared equally between them. For
  never-married individuals, this is the same as the lifetime payroll
  tax. In any year where an individual is not married, we count only
  their individual payroll taxes." -> ``shared=True``.

MINT8 says "We use the Social Security Trust Fund interest rate to adjust
benefits and taxes to their present values at age 62" and "The present
value of payroll taxes includes all the payroll taxes that the individual
paid over a lifetime."  It does not say which trust fund rate, which tax
rate, how a year is timed, how ties fall at quintile boundaries, or where
separated people go.  Every such choice below is a **registered builder
default**: an explicit, named parameter recorded in each result's
provenance, never a silent fallback.

The report scheme (Butrica and Uccello 2004, exercise 2).  The repository
records only that both of that Report's lifetime-earnings measures
"average wage-indexed earnings at ages 22-62, and the own measure includes
uncovered earnings and earnings above the taxable maximum"
(``docs/design/boomers2004_uniform_cut_comparison.md``, named omissions;
``estimates/uniform_cut_tabulation.py`` ``NOT_COMPUTED_REPORT_ROWS``).
:func:`report_average_indexed_earnings_22_62` implements exactly that and
names every unrecorded convention in :data:`REPORT_EARNINGS_BUILDER_DEFAULTS`.
That scheme stays unregistered (:func:`boomers2004_scheme`): the Report's
quintile order ("1st Quintile" lowest or highest) and quintile population
are not recorded, so it refuses to label.

Stated invariants (property-tested in ``tests/estimates/
test_lifetime_measures.py``):

1. Quintiles: within a cell with no tied values every quintile holds
   20 percent of the weight to within the largest row's weight share;
   labels are invariant to positive weight scaling within the documented
   floating-point boundary tolerance and to row
   order; a higher value never gets a lower quintile in the same cell;
   missing values get :data:`NOT_COMPUTED` and nothing else does.
2. Payroll tax present value: zero earnings give zero; doubling earnings
   that stay below the contribution and benefit base doubles it;
   earnings above the base do not change it; it is linear in the tax rate.
3. Sharing: for a couple married to each other in every year either
   spouse paid tax, with the same birth year, the two shared present
   values sum to the two own present values; year by year the shared taxes
   of the two sum exactly to their own taxes.
4. AIME: equals the repository oracle (``ss.statutory_aime.oracle_aime``)
   on the same truncated history, and under the exercise-4 convention it
   equals Track M's ``rules.history_pia`` AIME for an entitlement at 62.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Collection, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from populace_dynamics.ss import statutory_aime
from populace_dynamics.ss.params import SSAParameters
from populace_dynamics.ss.statutory_aime import ComputationYears

__all__ = [
    "AIME_CONVENTIONS",
    "COMPUTED",
    "MINT8_DEFINITIONS_PATH",
    "MINT8_DIMENSION_MEASURES",
    "MINT8_DEFINITIONS_SHA256",
    "NOT_COMPUTED",
    "OASDI_TAX_RATES_PATH",
    "OASDI_TAX_RATES_SHA256",
    "PAYROLL_TAX_BUILDER_DEFAULTS",
    "QUINTILE_LABELS",
    "REPORT_EARNINGS_BUILDER_DEFAULTS",
    "REPORT_EARNINGS_RECORDED",
    "SCHEMA_VERSION",
    "SCHEMES",
    "TRUST_FUND_INTEREST_RATES_PATH",
    "TRUST_FUND_INTEREST_RATES_SHA256",
    "AimeBasis",
    "AimeConvention",
    "AverageDivisor",
    "InterestSeries",
    "LifetimeEarningsScheme",
    "MeasureResult",
    "MissingRatePolicy",
    "MissingSpousePolicy",
    "OASDITaxRates",
    "QuintileDimension",
    "QuintileScope",
    "ReportEarningsConventions",
    "TaxRateBasis",
    "TrustFundInterestRates",
    "accumulation_factor",
    "annual_payroll_taxes",
    "boomers2004_scheme",
    "initial_aime_at_62",
    "lifetime_payroll_tax_pv_at_62",
    "load_mint8_definitions",
    "load_mint8_scheme",
    "load_oasdi_tax_rates",
    "load_trust_fund_interest_rates",
    "quintile_cells",
    "quintile_summary",
    "report_average_indexed_earnings_22_62",
    "ten_year_birth_cohort",
    "weighted_quintiles",
]

SCHEMA_VERSION = "lifetime_measures.v1"

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_EXTERNAL = _PROJECT_ROOT / "data" / "external"
#: SSA OACT "Social Security Tax Rates" (oasdiRates.html), captured
#: 2026-10-01 and extracted by scripts/extract_lifetime_measure_sources.py.
OASDI_TAX_RATES_PATH = _EXTERNAL / "ssa_oasdi_tax_rates_2026.json"
OASDI_TAX_RATES_SHA256 = (
    "63267c7e7596439224d0bb088290e5c0be92a1187091b448fdf4074aabcc1615"
)
#: SSA OACT "Average and Effective Interest Rates" (annualinterestrates
#: .html), 1940-2025, cross-checked against the per-fund pages.
TRUST_FUND_INTEREST_RATES_PATH = (
    _EXTERNAL / "ssa_trust_fund_interest_rates_2026.json"
)
TRUST_FUND_INTEREST_RATES_SHA256 = (
    "a55c4722caa80caf26a0442492492cebfc52b412535fff584617a35188812766"
)
#: Verbatim MINT8 Table User Guide definitions and the cohort-table labels.
MINT8_DEFINITIONS_PATH = _EXTERNAL / "mint8_lifetime_quintile_definitions.json"
MINT8_DEFINITIONS_SHA256 = (
    "857d82d78371483d69ffb1402df8f2229928629cf5e657dcb5ee497f853ffa74"
)

#: MINT8's quintile labels in its table order (always these five).
QUINTILE_LABELS: tuple[str, ...] = (
    "Highest",
    "Second highest",
    "Middle",
    "Second lowest",
    "Lowest",
)
#: The label of a person with no value (status ``not computed``).
NOT_COMPUTED = "not computed"
#: The status of a person whose measure was computed.
COMPUTED = "computed"

_N_QUINTILES = 5
# Snap a midpoint within this distance of an integer quintile boundary
# to that boundary. This prevents float multiplication from moving an
# exact boundary across quintiles when all weights are rescaled.
_QUINTILE_BOUNDARY_TOLERANCE = 1e-12
_RETIREMENT_AGE = 62
#: The age at which the career frames' coverage starts at the earliest
#: (estimates/career.py: max(1968, birth year + 22)); a later first row
#: flags a left-censored history.
_FIRST_AGE = 22
_AIME_INDEXING_AGE = 60
_FIRST_COMPUTATION_BASE_YEAR = 1951
_EN_DASH = "–"
_EPISODE_COLUMNS = (
    "person_id",
    "marriage_order",
    "start_year",
    "episode_end_year",
    "how_ended",
    "spouse_person_id",
)


# ---------------------------------------------------------------------------
# Conventions
# ---------------------------------------------------------------------------
class TaxRateBasis(str, Enum):
    """Which OASDI rate a year's payroll tax uses.

    ``TRUST_FUND_RECEIVED`` (registered builder default): twice the
    "Tax rate for employees and employers, each" total of SSA's table,
    which "reflect[s] the amounts received by the trust funds".
    ``EMPLOYEE_EMPLOYER_PAID``: the same, except the employee share in
    1984 (5.4 percent, footnote a) and 2011-2012 (4.2 percent, footnote c),
    when general revenue covered the difference.
    """

    TRUST_FUND_RECEIVED = "trust_fund_received"
    EMPLOYEE_EMPLOYER_PAID = "employee_employer_paid"


class InterestSeries(str, Enum):
    """Which SSA trust fund interest rate discounts and accumulates.

    ``EFFECTIVE_OASDI`` (registered builder default): "the interest earned
    in that year divided by the average level of assets held during the
    year" for the combined OASI and DI trust funds.
    ``AVERAGE_NEW_ISSUE``: "the average of the 12 monthly interest rates on
    new issues during the year".
    """

    EFFECTIVE_OASDI = "effective_oasdi"
    AVERAGE_NEW_ISSUE = "average_new_issue"


class MissingSpousePolicy(str, Enum):
    """A married year whose spouse has no career in the careers frame.

    ``OWN_ONLY`` (registered builder default): the year counts the
    person's own amount, and the year is counted in the result.
    ``NOT_COMPUTED``: the person's shared measure is not computed.
    """

    OWN_ONLY = "own_only"
    NOT_COMPUTED = "not_computed"


class MissingRatePolicy(str, Enum):
    """A year whose interest rate the series does not cover.

    ``REFUSE`` (default): raise, naming the years.  ``NOT_COMPUTED``: mark
    the affected persons not computed.  Coverage can be extended only by
    :meth:`TrustFundInterestRates.extended`, with a named source.
    """

    REFUSE = "refuse"
    NOT_COMPUTED = "not_computed"


class AimeBasis(str, Enum):
    """``AGE_62``: the person attains 62 by the analysis year.
    ``PROVISIONAL_THROUGH_LAST_OBSERVED``: younger than 62 in the analysis
    year; the AIME uses the history through the analysis year (flagged).
    """

    AGE_62 = "age_62"
    PROVISIONAL_THROUGH_LAST_OBSERVED = "provisional_through_last_observed"


class AverageDivisor(str, Enum):
    """The divisor of the report's average indexed earnings.

    ``COVERED_AGES`` (registered builder default): the ages 22-62 at which
    the careers frame has a row.  ``ALL_AGES``: all 41 ages (a missing
    age counts as zero earnings).
    """

    COVERED_AGES = "covered_ages"
    ALL_AGES = "all_ages"


class QuintileScope(str, Enum):
    """The population over which a quintile is cut.

    MINT8: "We calculate the AIME quintiles for each birth cohort", and it
    uses "10-year birth cohorts" (1960-1969, ...).  For an annual
    population both cuts are exposed.
    """

    TEN_YEAR_BIRTH_COHORT = "ten_year_birth_cohort"
    WHOLE_POPULATION = "whole_population"


@dataclass(frozen=True)
class AimeConvention:
    """How an initial AIME is computed: the oracle's computation-year
    convention and the last age whose earnings enter.

    ``last_earnings_age`` ``None`` passes the history as supplied (up to
    the analysis year), as Track A's ``_Calculator._level`` does.
    """

    name: str
    computation_years: ComputationYears
    last_earnings_age: int | None
    source: str


#: Named AIME conventions, one per way the repository computes an
#: old-age AIME.  Exercise 2 (Track U) computes no AIME: it reads
#: reported Social Security amounts.
AIME_CONVENTIONS: dict[str, AimeConvention] = {
    "mint8_initial_aime": AimeConvention(
        name="mint8_initial_aime",
        computation_years=ComputationYears.STATUTORY,
        last_earnings_age=61,
        source=(
            "MINT8: 'AIME under current law at age 62'. Statutory 415(b)(2) "
            "computation years; earnings through the year before the year "
            "of attaining 62 (registered builder default: the history an "
            "entitlement beginning at 62 uses under Track M's window-year-"
            "less-one cut, min_benefit_track_m/rules.py history_pia)."
        ),
    ),
    "exercise_1_cola": AimeConvention(
        name="exercise_1_cola",
        computation_years=ComputationYears.LEGACY_FIXED_35,
        last_earnings_age=None,
        source=(
            "cola_track_a/benefits.py TRACK_A_COMPUTATION_YEARS "
            "(LEGACY_FIXED_35, Registration 13); _Calculator._level passes "
            "the whole opening-year career to eligibility_pia_for_clock."
        ),
    ),
    "exercise_3_fra68": AimeConvention(
        name="exercise_3_fra68",
        computation_years=ComputationYears.LEGACY_FIXED_35,
        last_earnings_age=None,
        source=(
            "fra68_track/config.py MAX_RULINGS['benefit_computation_years'] "
            "(LEGACY_FIXED_35, d188 item (a): run exercise 3 exactly like "
            "Track A); benefits through the Track A calculator."
        ),
    ),
    "exercise_4_min_benefit": AimeConvention(
        name="exercise_4_min_benefit",
        computation_years=ComputationYears.STATUTORY,
        last_earnings_age=61,
        source=(
            "min_benefit_track_m/rules.py history_pia (old_age): "
            "ss.statutory_aime.aime over the history through the window "
            "year less one (record_years: computation base years end "
            "before the year of first entitlement); for an entitlement in "
            "the year of attaining 62 that is the year of attaining 61."
        ),
    ),
}


@dataclass(frozen=True)
class ReportEarningsConventions:
    """Conventions of :func:`report_average_indexed_earnings_22_62`.

    ``first_age``, ``last_age`` and, for the own measure,
    ``cap_at_taxable_maximum=False`` are recorded
    (:data:`REPORT_EARNINGS_RECORDED`); the rest are registered builder
    defaults (:data:`REPORT_EARNINGS_BUILDER_DEFAULTS`).
    """

    first_age: int = 22
    last_age: int = 62
    cap_at_taxable_maximum: bool = False
    index_age: int = 60
    divisor: AverageDivisor = AverageDivisor.COVERED_AGES
    separated_is_married: bool = True
    missing_spouse: MissingSpousePolicy = MissingSpousePolicy.OWN_ONLY


_REPORT_RECORD = (
    "docs/design/boomers2004_uniform_cut_comparison.md (named omissions); "
    "estimates/uniform_cut_tabulation.py NOT_COMPUTED_REPORT_ROWS"
)
#: What the repository records about the Report's measure, with locators.
REPORT_EARNINGS_RECORDED: dict[str, str] = {
    "measure": (
        "both measures 'average wage-indexed earnings at ages 22-62' "
        f"({_REPORT_RECORD})"
    ),
    "own_includes_above_taxable_maximum": (
        "'the own measure includes uncovered earnings and earnings above "
        f"the taxable maximum' ({_REPORT_RECORD}); so the own measure is "
        "not capped. PSID labor earnings do not separate covered from "
        "uncovered work, so 'includes uncovered earnings' holds trivially."
    ),
    "rows": (
        "Lifetime Earnings (Own) and (Shared), five rows each, '1st "
        "Quintile' to '5th Quintile' (uniform_cut_tabulation.py)"
    ),
}
#: Every convention the record leaves open, with this builder's default.
REPORT_EARNINGS_BUILDER_DEFAULTS: dict[str, str] = {
    "age_in_year": "age = calendar year - birth year (the oracle's rule)",
    "age_range_inclusive": "ages 22 through 62 inclusive (41 ages)",
    "wage_index": (
        "the SSA national average wage index (SSAParameters.nawi), each "
        "year's earnings times NAWI(index year) / NAWI(year), years at or "
        "after the index year nominal (ss.benefits.indexed_history's rule)"
    ),
    "index_age": "60, the AIME indexing age",
    "divisor": (
        "the ages 22-62 with a career row (COVERED_AGES); the PSID does "
        "not observe every age, so missing ages are not read as zeros"
    ),
    "shared_rule": (
        "in a year the person is married at year end, the mean of the two "
        "spouses' indexed earnings (both indexed to the person's index "
        "year); otherwise own earnings (MINT8's sharing rule, since the "
        "Report's is not recorded)"
    ),
    "shared_cap": "uncapped, as recorded for the own measure",
    "marital_state": (
        "psid2010.marital_state_at at the end of each year; separated "
        "counts as married (the repository's default)"
    ),
    "missing_spouse": "own earnings for that year, counted (OWN_ONLY)",
    "missing_spouse_year": (
        "a spouse with a career but no row in this year contributes zero; "
        "the year is counted as married_years_spouse_year_absent"
    ),
    "missing_own_year": (
        "COVERED_AGES uses only the person's own observed career years; "
        "spouse-only years are outside this report average"
    ),
    "reciprocal_history_disagreement": (
        "use each person's recorded spouse; disagreement with an available "
        "spouse history is counted and couple conservation is not promised"
    ),
    "multiple_marriages_in_force": (
        "use the latest-start marriage as marital_state_at does; count "
        "years_multiple_marriages_in_force"
    ),
    "quintile_order_and_population": (
        "not registered: whether '1st Quintile' is the lowest and over "
        "which population the quintiles are cut are unrecorded, so the "
        "scheme refuses to label (boomers2004_scheme)"
    ),
}

#: Registered builder defaults of the MINT8 payroll-tax measures.
PAYROLL_TAX_BUILDER_DEFAULTS: dict[str, str] = {
    "tax_rate": (
        "combined employee and employer OASDI rate by year (twice SSA's "
        "'each' total, the rate the trust funds received; TaxRateBasis), "
        "applied to earnings capped at the contribution and benefit base "
        "(SSAParameters.wage_base_for)"
    ),
    "self_employment": (
        "not separated: every dollar of career earnings is taxed at the "
        "employee-plus-employer rate"
    ),
    "interest_rate": (
        "SSA's effective annual interest rate of the combined OASI and DI "
        "trust funds (InterestSeries.EFFECTIVE_OASDI)"
    ),
    "timing": (
        "a year's tax is credited at the end of that year and the present "
        "value is taken at the end of the year of attaining 62: tax in "
        "year t is multiplied by the product of (1 + i_s) for s = t+1..Y, "
        "or divided by the product for s = Y+1..t when t > Y"
    ),
    "lifetime": (
        "every career year in the frame, before and after 62 ('all the "
        "payroll taxes that the individual paid over a lifetime')"
    ),
    "marital_state": (
        "psid2010.marital_state_at at the end of each tax year; separated "
        "counts as married (the repository's default)"
    ),
    "shared_years": (
        "every year in which either spouse has a career row while the "
        "person is married to that spouse; a spouse's missing year counts "
        "as zero tax (counted)"
    ),
    "missing_spouse": (
        "a married year whose spouse is not a joinable person in the "
        "careers frame counts the person's own tax (OWN_ONLY, counted)"
    ),
    "unknown_marital_state": (
        "a year whose marital state is 'unknown' counts own tax (counted)"
    ),
    "missing_spouse_year": (
        "a spouse with a career but no row in this year contributes zero; "
        "the year is counted as married_years_spouse_year_absent"
    ),
    "missing_own_year": (
        "share over the union of both spouses' career years while married; "
        "an absent own year contributes zero and is counted"
    ),
    "reciprocal_history_disagreement": (
        "use each person's recorded spouse; disagreement with an available "
        "spouse history is counted and couple conservation is not promised"
    ),
    "multiple_marriages_in_force": (
        "use the latest-start marriage as marital_state_at does; count "
        "years_multiple_marriages_in_force"
    ),
}


# ---------------------------------------------------------------------------
# Rate schedules
# ---------------------------------------------------------------------------
class _CombinedRateSource(Protocol):
    def combined_for(self, year: int) -> float: ...


class _InterestRateSource(Protocol):
    def rate_for(self, year: int) -> float: ...


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_pinned_json(
    path: Path, expected_sha256: str, schema: str
) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    digest = _sha256(raw)
    if digest != expected_sha256:
        raise ValueError(
            f"{path} sha256 {digest} != pinned {expected_sha256}; refusing "
            "a changed committed extraction."
        )
    document = json.loads(raw)
    if document.get("schema_version") != schema:
        raise ValueError(f"{path} schema_version is not {schema!r}.")
    return document, digest


def _year(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{label} must be an integer year, not {value!r}.")
    if isinstance(value, (int, np.integer)):
        return int(value)
    raise TypeError(f"{label} must be an integer year, not {value!r}.")


@dataclass(frozen=True)
class OASDITaxRates:
    """Combined employee-plus-employer OASDI tax rates by calendar year.

    ``combined_percent_by_year`` holds every year of the table's closed
    periods; years from ``open_ended_from`` take the "and later" row.  A
    year before the first period (1937) raises.
    """

    combined_percent_by_year: Mapping[int, float]
    open_ended_from: int
    open_ended_combined_percent: float
    basis: TaxRateBasis
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def combined_percent_for(self, year: int) -> float:
        """The combined rate in percent of taxable earnings."""
        year = _year(year, "year")
        if year >= self.open_ended_from:
            return float(self.open_ended_combined_percent)
        if year not in self.combined_percent_by_year:
            raise KeyError(f"No OASDI tax rate for {year}.")
        return float(self.combined_percent_by_year[year])

    def combined_for(self, year: int) -> float:
        """The combined rate as a fraction of taxable earnings.

        The same interface as ``estimates.parameters.PayrollRateLegs``.
        """
        return self.combined_percent_for(year) / 100.0

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        *,
        basis: TaxRateBasis = TaxRateBasis.TRUST_FUND_RECEIVED,
        provenance: Mapping[str, Any] | None = None,
    ) -> OASDITaxRates:
        """Build the schedule from an ``ssa_oasdi_tax_rates.v1`` document."""
        basis = TaxRateBasis(basis)
        by_year: dict[int, float] = {}
        open_from: int | None = None
        open_rate: float | None = None
        for row in document["rows"]:
            combined = 2.0 * float(row["employee_employer_each"]["total"])
            first = int(row["first_year"])
            if row["last_year"] is None:
                open_from, open_rate = first, combined
                continue
            for year in range(first, int(row["last_year"]) + 1):
                if year in by_year:
                    raise ValueError(f"OASDI tax year {year} listed twice.")
                by_year[year] = combined
        if open_from is None or open_rate is None:
            raise ValueError("The OASDI schedule has no open-ended row.")
        if basis is TaxRateBasis.EMPLOYEE_EMPLOYER_PAID:
            for adjustment in document["paid_rate_adjustments"]:
                year = int(adjustment["year"])
                if year not in by_year:
                    raise ValueError(f"Paid-rate year {year} not tabled.")
                by_year[year] = float(
                    adjustment["employee_effective_rate"]
                ) + float(adjustment["employer_rate"])
        return cls(
            combined_percent_by_year=by_year,
            open_ended_from=open_from,
            open_ended_combined_percent=open_rate,
            basis=basis,
            provenance=dict(provenance or {}),
        )


def load_oasdi_tax_rates(
    path: Path = OASDI_TAX_RATES_PATH,
    *,
    basis: TaxRateBasis = TaxRateBasis.TRUST_FUND_RECEIVED,
    expected_sha256: str = OASDI_TAX_RATES_SHA256,
) -> OASDITaxRates:
    """Load SSA's OASDI tax-rate schedule (pinned committed extraction)."""
    document, digest = _read_pinned_json(
        path, expected_sha256, "ssa_oasdi_tax_rates.v1"
    )
    basis = TaxRateBasis(basis)
    return OASDITaxRates.from_document(
        document,
        basis=basis,
        provenance={
            "file": _relative(path),
            "sha256": digest,
            "table": document["table"],
            "rates_reflect": document["rates_reflect"],
            "basis": basis.value,
        },
    )


@dataclass(frozen=True)
class TrustFundInterestRates:
    """Annual trust fund interest rates (percent) by calendar year.

    ``assumed_years`` are years added by :meth:`extended` under
    ``assumption_source``; every other year is SSA's published rate.
    """

    percent_by_year: Mapping[int, float]
    series: str
    assumed_years: frozenset[int] = frozenset()
    assumption_source: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def covers(self, year: int) -> bool:
        return _year(year, "year") in self.percent_by_year

    def rate_for(self, year: int) -> float:
        """The rate as a fraction; raises outside the series' coverage."""
        year = _year(year, "year")
        if year not in self.percent_by_year:
            raise KeyError(
                f"No {self.series} trust fund interest rate for {year}."
            )
        return float(self.percent_by_year[year]) / 100.0

    def extended(
        self, assumed_percent: Mapping[int, float], *, source: str
    ) -> TrustFundInterestRates:
        """A copy with assumed rates for uncovered years, named by source.

        Refuses to overwrite a covered year, an empty source, or a rate
        that is not finite and above -100 percent.
        """
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Assumed interest rates need a named source.")
        overlap = sorted(
            int(year) for year in assumed_percent if self.covers(int(year))
        )
        if overlap:
            raise ValueError(f"Years {overlap} already have rates.")
        added: dict[int, float] = {}
        for year, value in assumed_percent.items():
            rate = float(value)
            if not math.isfinite(rate) or rate <= -100.0:
                raise ValueError(f"Assumed rate {value!r} for {year}.")
            added[_year(year, "year")] = rate
        sources = [self.assumption_source, source.strip()]
        return TrustFundInterestRates(
            percent_by_year={**self.percent_by_year, **added},
            series=self.series,
            assumed_years=self.assumed_years | frozenset(added),
            assumption_source="; ".join(s for s in sources if s),
            provenance=dict(self.provenance),
        )


def load_trust_fund_interest_rates(
    path: Path = TRUST_FUND_INTEREST_RATES_PATH,
    *,
    series: InterestSeries = InterestSeries.EFFECTIVE_OASDI,
    expected_sha256: str = TRUST_FUND_INTEREST_RATES_SHA256,
) -> TrustFundInterestRates:
    """Load SSA's annual trust fund interest rates, 1940-2025."""
    document, digest = _read_pinned_json(
        path, expected_sha256, "ssa_trust_fund_interest_rates.v1"
    )
    series = InterestSeries(series)
    by_year = {}
    for year, row in document["data"].items():
        value = row[series.value]
        if value is None:
            raise ValueError(f"{series.value} has no value for {year}.")
        by_year[int(year)] = float(value)
    return TrustFundInterestRates(
        percent_by_year=by_year,
        series=series.value,
        provenance={
            "file": _relative(path),
            "sha256": digest,
            "table": document["table"],
            "series": series.value,
            "definition": document["series"][series.value].get(
                "definition", ""
            ),
            "latest_observation_year": document["latest_observation_year"],
        },
    )


def _relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(_PROJECT_ROOT))
    except ValueError:
        return str(path)


def accumulation_factor(
    tax_year: int, reference_year: int, interest: _InterestRateSource
) -> float:
    """Value at the end of ``reference_year`` of 1 paid at the end of
    ``tax_year``: the product of (1 + i_s) over s = tax_year+1 ..
    reference_year, or its reciprocal over s = reference_year+1 .. tax_year
    when the tax year is later."""
    tax_year = _year(tax_year, "tax_year")
    reference_year = _year(reference_year, "reference_year")
    if tax_year == reference_year:
        return 1.0
    low, high = sorted((tax_year, reference_year))
    growth = []
    for year in range(low + 1, high + 1):
        rate = float(interest.rate_for(year))
        if not math.isfinite(rate) or rate <= -1.0:
            raise ValueError(
                f"Interest rate for {year} must be finite and above -1."
            )
        growth.append(1.0 + rate)
    factor = math.prod(growth)
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("Interest accumulation is outside finite range.")
    return factor if tax_year < reference_year else 1.0 / factor


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MeasureResult:
    """One measure for every person, with JSON-ready provenance."""

    measure: str
    frame: pd.DataFrame
    provenance: dict[str, Any]


def _integral(series: pd.Series, label: str) -> np.ndarray:
    if series.isna().any():
        raise ValueError(f"{label} has missing values.")
    values = pd.to_numeric(series, errors="raise")
    as_float = values.astype("float64").to_numpy()
    if not np.all(np.isfinite(as_float)) or not np.all(
        as_float == np.floor(as_float)
    ):
        raise ValueError(f"{label} must hold integers.")
    return values.astype("int64").to_numpy()


def _careers_frame(careers: pd.DataFrame) -> pd.DataFrame:
    missing = {"person_id", "year", "earnings"} - set(careers.columns)
    if missing:
        raise ValueError(f"careers lacks columns {sorted(missing)}.")
    frame = pd.DataFrame(
        {
            "person_id": _integral(careers["person_id"], "person_id"),
            "year": _integral(careers["year"], "year"),
            "earnings": pd.to_numeric(careers["earnings"], errors="raise")
            .astype("float64")
            .to_numpy(),
        }
    )
    earnings = frame["earnings"].to_numpy()
    if not np.all(np.isfinite(earnings)) or (earnings < 0).any():
        raise ValueError("careers earnings must be finite and non-negative.")
    if "provenance" in careers.columns:
        frame["provenance"] = pd.array(
            careers["provenance"].astype("string").to_numpy(),
            dtype="string",
        )
    if frame.duplicated(["person_id", "year"]).any():
        raise ValueError("careers has duplicate (person_id, year) rows.")
    return frame


def _persons_frame(persons: pd.DataFrame) -> pd.DataFrame:
    missing = {"person_id", "birth_year"} - set(persons.columns)
    if missing:
        raise ValueError(f"persons lacks columns {sorted(missing)}.")
    frame = pd.DataFrame(
        {
            "person_id": _integral(persons["person_id"], "person_id"),
            "birth_year": _integral(persons["birth_year"], "birth_year"),
        }
    )
    if frame["person_id"].duplicated().any():
        raise ValueError("persons has duplicate person_id values.")
    return frame


def _histories(frame: pd.DataFrame) -> dict[int, dict[int, float]]:
    histories: dict[int, dict[int, float]] = {}
    for pid, year, earnings in zip(
        frame["person_id"].to_numpy(),
        frame["year"].to_numpy(),
        frame["earnings"].to_numpy(),
        strict=True,
    ):
        histories.setdefault(int(pid), {})[int(year)] = float(earnings)
    return histories


def _imputed_years(frame: pd.DataFrame) -> dict[int, set[int]] | None:
    """Years whose provenance is not ``observed``, by person."""
    if "provenance" not in frame.columns:
        return None
    flagged = frame[frame["provenance"].fillna("") != "observed"]
    out: dict[int, set[int]] = {}
    for pid, year in zip(flagged["person_id"], flagged["year"], strict=True):
        out.setdefault(int(pid), set()).add(int(year))
    return out


def _frame_sha256(frame: pd.DataFrame) -> str:
    return _sha256(
        frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    )


def _input_digests(
    careers: pd.DataFrame,
    persons: pd.DataFrame,
    episodes: pd.DataFrame | None = None,
    marriage_history_person_ids: Collection[int] | None = None,
) -> dict[str, str]:
    digests = {
        "careers_sha256": _frame_sha256(
            careers.sort_values(["person_id", "year"]).reset_index(drop=True)
        ),
        "persons_sha256": _frame_sha256(
            persons.sort_values("person_id").reset_index(drop=True)
        ),
    }
    if episodes is not None:
        digests["marriage_episodes_sha256"] = _frame_sha256(
            episodes.sort_values(["person_id", "marriage_order"])
            .astype("string")
            .reset_index(drop=True)
        )
    if marriage_history_person_ids is not None:
        digests["marriage_history_person_ids_sha256"] = _sha256(
            json.dumps(sorted(set(marriage_history_person_ids))).encode(
                "utf-8"
            )
        )
    return digests


def _counts(series: pd.Series) -> dict[str, int]:
    values = series.astype("object").where(series.notna(), "none")
    return {
        str(key): int(value)
        for key, value in sorted(values.value_counts().items())
    }


def _provenance(
    measure: str,
    frame: pd.DataFrame,
    params: SSAParameters,
    inputs: dict[str, str],
    conventions: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flag_columns = [
        column
        for column in frame.columns
        if pd.api.types.is_bool_dtype(frame[column].dtype)
        or column.startswith(("years_", "married_years_", "n_"))
    ]
    totals = {}
    for column in flag_columns:
        series = frame[column]
        if pd.api.types.is_bool_dtype(series.dtype):
            totals[column] = int(series.astype("boolean").fillna(False).sum())
        else:
            values = pd.to_numeric(series, errors="coerce")
            totals[column] = int(values.fillna(0).sum())
    record = {
        "schema_version": SCHEMA_VERSION,
        "measure": measure,
        "n_persons": len(frame),
        "status_counts": _counts(frame["status"]),
        "reason_counts": _counts(frame["reason"]),
        "flag_totals": totals,
        "conventions": conventions,
        "ssa_parameters": {
            "pe_us_revision": params.pe_us_revision,
            "nawi_sha256": _schedule_sha256(params.nawi),
            "wage_base_sha256": _schedule_sha256(params.wage_base),
        },
        "inputs": inputs,
        "output_sha256": _frame_sha256(frame),
        "pure_over_cohort_outputs": (
            "computed from careers, persons and marriage-episode frames "
            "only; no PSID file is opened"
        ),
    }
    if extra:
        record.update(extra)
    # A caller can edit its audit record without changing module defaults
    # or another call's provenance.
    return deepcopy(record)


def _schedule_sha256(schedule: Mapping[int, float]) -> str:
    """Pin supplied parameter values, including replaced projection paths."""
    return _sha256(
        json.dumps(
            {
                str(year): float(value)
                for year, value in sorted(schedule.items())
            },
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    )


def _nawi_missing(
    years: Collection[int], indexing_year: int, params: SSAParameters
) -> list[int]:
    needed = {indexing_year} | {year for year in years if year < indexing_year}
    for year in needed & params.nawi.keys():
        value = float(params.nawi[year])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"NAWI for {year} must be finite and positive.")
    return sorted(year for year in needed if year not in params.nawi)


def _wage_base(year: int, params: SSAParameters) -> float:
    """Validate the supplied contribution and benefit base before use."""
    base = float(params.wage_base_for(year))
    if not math.isfinite(base) or base < 0:
        raise ValueError(
            f"Wage base for {year} must be finite and non-negative."
        )
    return base


# ---------------------------------------------------------------------------
# 1. Initial AIME at 62
# ---------------------------------------------------------------------------
_AIME_COLUMNS = (
    "person_id",
    "birth_year",
    "aime",
    "status",
    "reason",
    "basis",
    "reaches_62_by_analysis_year",
    "history_cutoff_year",
    "first_earnings_year",
    "last_earnings_year",
    "history_starts_after_age_22",
    "history_ends_before_cutoff",
    "n_history_years",
    "n_history_years_after_age_61",
    "n_imputed_history_years",
    "years_before_1951_dropped",
    "computation_years",
    "indexing_year",
)


def initial_aime_at_62(
    careers: pd.DataFrame,
    persons: pd.DataFrame,
    params: SSAParameters,
    *,
    analysis_year: int,
    convention: AimeConvention,
) -> MeasureResult:
    """Current-law AIME at age 62 for every person (MINT8's initial AIME).

    The oracle's AIME (``ss.statutory_aime.oracle_aime``, unchanged) over
    the person's career cut at ``birth_year + convention.last_earnings_age``
    and never after ``analysis_year``.  A person who attains 62 by the
    analysis year has basis ``age_62``; a younger person's AIME uses the
    history through the analysis year (the last observed year; closed-
    cohort tests stop earnings in 2010) and has basis
    ``provisional_through_last_observed``.  The convention is required:
    :data:`AIME_CONVENTIONS` names how each blind test computes an AIME.

    Not computed, with a reason: no career rows; career rows only after
    the cutoff (earnings before 62 unobserved, not zero); a statutory AIME
    for a person attaining 62 before 1975 (the oracle refuses it); a NAWI
    value the indexing needs.  Years before 1951 cannot be computation
    base years and are dropped, counted.  Years inside the cutoff that the
    careers frame lacks count as zero, as in the oracle; a first row after
    age 22 (the PSID's first income year is 1967) is flagged
    ``history_starts_after_age_22``.
    """

    analysis_year = _year(analysis_year, "analysis_year")
    if not isinstance(convention, AimeConvention):
        raise TypeError("convention must be an AimeConvention.")
    if convention.last_earnings_age is not None:
        _year(convention.last_earnings_age, "last_earnings_age")
    convention_years = ComputationYears(convention.computation_years)
    careers_frame = _careers_frame(careers)
    persons_frame = _persons_frame(persons)
    histories = _histories(careers_frame)
    imputed = _imputed_years(careers_frame)
    rows = []
    for pid, birth in zip(
        persons_frame["person_id"], persons_frame["birth_year"], strict=True
    ):
        pid, birth = int(pid), int(birth)
        reaches = birth + _RETIREMENT_AGE <= analysis_year
        cutoff = analysis_year
        if convention.last_earnings_age is not None:
            cutoff = min(cutoff, birth + int(convention.last_earnings_age))
        history_all = histories.get(pid)
        kept = {
            year: value
            for year, value in (history_all or {}).items()
            if year <= cutoff
        }
        early = [year for year in kept if year < _FIRST_COMPUTATION_BASE_YEAR]
        for year in early:
            del kept[year]
        first_year = min(kept) if kept else None
        last_year = max(kept) if kept else None
        # The year of attaining 60: benefits.indexed_history's year and
        # statutory_aime.indexing_year's with no death or disability date.
        indexing = birth + _AIME_INDEXING_AGE
        n_years = (
            statutory_aime.LEGACY_FIXED_COMPUTATION_YEARS
            if convention_years is ComputationYears.LEGACY_FIXED_35
            else None
        )
        row = {
            "person_id": pid,
            "birth_year": birth,
            "aime": math.nan,
            "status": NOT_COMPUTED,
            "reason": None,
            "basis": (
                AimeBasis.AGE_62
                if reaches
                else AimeBasis.PROVISIONAL_THROUGH_LAST_OBSERVED
            ).value,
            "reaches_62_by_analysis_year": reaches,
            "history_cutoff_year": cutoff,
            "first_earnings_year": first_year,
            "last_earnings_year": last_year,
            "history_starts_after_age_22": (
                first_year is not None and first_year > birth + _FIRST_AGE
            ),
            "history_ends_before_cutoff": (
                last_year is not None and last_year < cutoff
            ),
            "n_history_years": len(kept),
            "n_history_years_after_age_61": sum(
                year > birth + 61 for year in kept
            ),
            "n_imputed_history_years": (
                None
                if imputed is None
                else len(imputed.get(pid, set()) & set(kept))
            ),
            "years_before_1951_dropped": len(early),
            "computation_years": n_years,
            "indexing_year": indexing,
        }
        if not history_all:
            row["reason"] = "no_career_rows"
        elif not kept:
            # Rows exist only after the cutoff (or before 1951): the
            # earnings before 62 are unobserved, not zero.
            row["reason"] = "no_career_rows_before_cutoff"
        elif (
            convention_years is ComputationYears.STATUTORY
            and birth + _RETIREMENT_AGE
            < statutory_aime.FIRST_AGE_62_YEAR_ENCODED
        ):
            row["reason"] = "statutory_oracle_refuses_attaining_62_before_1975"
        elif missing := _nawi_missing(kept, indexing, params):
            row["reason"] = f"nawi_unavailable:{missing[0]}"
        else:
            for year in kept:
                _wage_base(year, params)
            if convention_years is ComputationYears.STATUTORY:
                row["computation_years"] = (
                    statutory_aime.benefit_computation_years(birth)
                )
            row["aime"] = float(
                statutory_aime.oracle_aime(
                    kept, birth, params, computation_years=convention_years
                )
            )
            row["status"] = COMPUTED
        rows.append(row)
    frame = pd.DataFrame(rows, columns=list(_AIME_COLUMNS))
    frame = frame.astype(
        {
            "first_earnings_year": "Int64",
            "last_earnings_year": "Int64",
            "n_imputed_history_years": "Int64",
            "computation_years": "Int64",
        }
    )
    provenance = _provenance(
        "initial_aime_at_62",
        frame,
        params,
        _input_digests(careers_frame, persons_frame),
        {
            "analysis_year": analysis_year,
            "aime_convention": {
                "name": convention.name,
                "computation_years": convention_years.value,
                "last_earnings_age": convention.last_earnings_age,
                "source": convention.source,
            },
            "oracle": "ss.statutory_aime.oracle_aime (unchanged)",
            "legacy_history_window": (
                "last_earnings_age=None reproduces the blind-test oracle "
                "on supplied careers through analysis_year; post-61 years "
                "are counted explicitly, so this is a legacy career AIME "
                "rather than an initial-at-62 observation where present"
            ),
            "definition": "mint8:initial_aime_quintile",
        },
        {"basis_counts": _counts(frame["basis"])},
    )
    return MeasureResult("initial_aime_at_62", frame, provenance)


# ---------------------------------------------------------------------------
# 2. Lifetime payroll tax at 62
# ---------------------------------------------------------------------------
def annual_payroll_taxes(
    careers: pd.DataFrame,
    params: SSAParameters,
    rates: _CombinedRateSource,
) -> pd.DataFrame:
    """Each career year's OASDI payroll tax.

    ``taxable_earnings = min(earnings, wage_base_for(year))`` and
    ``tax = taxable_earnings * rates.combined_for(year)`` (the combined
    employee and employer rate).  Columns: ``person_id``, ``year``,
    ``earnings``, ``taxable_earnings``, ``combined_rate``, ``tax``.
    """

    frame = _careers_frame(careers)
    years = sorted(int(year) for year in frame["year"].unique())
    base = {year: _wage_base(year, params) for year in years}
    rate = {year: float(rates.combined_for(year)) for year in years}
    for year in years:
        if not math.isfinite(rate[year]) or rate[year] < 0:
            raise ValueError(
                f"Tax rate for {year} must be finite and non-negative."
            )
    taxable = np.minimum(
        frame["earnings"].to_numpy(), frame["year"].map(base).to_numpy()
    )
    combined = frame["year"].map(rate).to_numpy()
    out = frame[["person_id", "year", "earnings"]].copy()
    out["taxable_earnings"] = taxable
    out["combined_rate"] = combined
    out["tax"] = taxable * combined
    return out.reset_index(drop=True)


def _episodes_by_person(
    episodes: pd.DataFrame,
) -> dict[int, pd.DataFrame]:
    missing = set(_EPISODE_COLUMNS) - set(episodes.columns)
    if missing:
        raise ValueError(f"marriage_episodes lacks {sorted(missing)}.")
    frame = episodes.copy()
    frame["person_id"] = _integral(frame["person_id"], "episode person_id")
    for column in (
        "marriage_order",
        "start_year",
        "episode_end_year",
        "spouse_person_id",
        "separation_year",
    ):
        if column in frame:
            present = frame[column].notna()
            _integral(frame.loc[present, column], f"episode {column}")
    ordered = frame[frame["marriage_order"].notna()]
    if ordered.duplicated(["person_id", "marriage_order"]).any():
        raise ValueError("marriage_episodes has duplicate marriage orders.")
    return {
        int(pid): group.reset_index(drop=True)
        for pid, group in frame.groupby("person_id", sort=True)
    }


def _spouse_id(value: Any) -> int | None:
    return None if pd.isna(value) else int(value)


class _MaritalYears:
    """Year-end marital states through ``psid2010.marital_state_at``."""

    def __init__(
        self, episodes: pd.DataFrame, *, separated_is_married: bool
    ) -> None:
        from populace_dynamics.cohorts.psid2010 import marital_state_at

        self._state_at = marital_state_at
        self._by_person = _episodes_by_person(episodes)
        self._empty = episodes.iloc[0:0]
        self._separated_is_married = bool(separated_is_married)
        self._cache: dict[tuple[int, int], tuple[str, int | None]] = {}
        self._multiple_in_force: dict[tuple[int, int], bool] = {}

    def has_history(self, pid: int) -> bool:
        return pid in self._by_person

    def spouses_ever(self, pid: int) -> set[int]:
        group = self._by_person.get(pid)
        if group is None:
            return set()
        return {
            int(spouse)
            for spouse in group["spouse_person_id"]
            if not pd.isna(spouse)
        }

    def state(self, pid: int, year: int) -> tuple[str, int | None]:
        key = (pid, year)
        if key not in self._cache:
            state = self._state_at(
                self._by_person.get(pid, self._empty),
                year,
                separated_is_married=self._separated_is_married,
            )
            self._cache[key] = (
                str(state["status"]),
                _spouse_id(state["spouse_person_id"]),
            )
            self._multiple_in_force[key] = bool(state["multiple_in_force"])
        return self._cache[key]

    def multiple_in_force(self, pid: int, year: int) -> bool:
        self.state(pid, year)
        return self._multiple_in_force[(pid, year)]


@dataclass
class _ShareCounts:
    married_years_shared: int = 0
    married_years_spouse_unavailable: int = 0
    married_years_spouse_year_absent: int = 0
    married_years_spouse_record_disagrees: int = 0
    married_years_own_year_absent: int = 0
    years_multiple_marriages_in_force: int = 0
    years_marital_unknown: int = 0


def _shared_amounts(
    pid: int,
    own: Mapping[int, float],
    spouse_amounts: Mapping[int, Mapping[int, float]],
    marital: _MaritalYears,
    candidate_years: Collection[int],
) -> tuple[dict[int, float], _ShareCounts]:
    """Per-year amounts with married years shared equally (MINT8 rule).

    ``spouse_amounts`` maps a person to that person's amounts by year;
    a person absent from it has no career (unavailable).
    """

    counts = _ShareCounts()
    out: dict[int, float] = {}
    for year in sorted(candidate_years):
        status, spouse = marital.state(pid, year)
        counts.years_multiple_marriages_in_force += int(
            marital.multiple_in_force(pid, year)
        )
        own_value = own.get(year)
        if status == "married":
            spouse_years = (
                None if spouse is None else spouse_amounts.get(spouse)
            )
            if spouse_years is None:
                counts.married_years_spouse_unavailable += 1
                if own_value is not None:
                    out[year] = own_value
                continue
            if year not in spouse_years:
                counts.married_years_spouse_year_absent += 1
            if own_value is None:
                counts.married_years_own_year_absent += 1
            if marital.has_history(spouse):
                back_status, back_spouse = marital.state(spouse, year)
                if back_status != "married" or back_spouse != pid:
                    counts.married_years_spouse_record_disagrees += 1
            out[year] = (
                (0.0 if own_value is None else own_value)
                + spouse_years.get(year, 0.0)
            ) / 2.0
            counts.married_years_shared += 1
            continue
        if status == "unknown":
            counts.years_marital_unknown += 1
        if own_value is not None:
            out[year] = own_value
    return out, counts


_PV_COLUMNS = (
    "person_id",
    "birth_year",
    "pv_at_62",
    "status",
    "reason",
    "reference_year",
    "first_tax_year",
    "last_tax_year",
    "history_starts_after_age_22",
    "n_tax_years",
    "n_imputed_tax_years",
)
_SHARE_COLUMNS = (
    "married_years_shared",
    "married_years_spouse_unavailable",
    "married_years_spouse_year_absent",
    "married_years_spouse_record_disagrees",
    "married_years_own_year_absent",
    "years_multiple_marriages_in_force",
    "years_marital_unknown",
    "marriage_history_absent",
)


def lifetime_payroll_tax_pv_at_62(
    careers: pd.DataFrame,
    persons: pd.DataFrame,
    params: SSAParameters,
    *,
    shared: bool,
    rates: _CombinedRateSource,
    interest: _InterestRateSource,
    marriage_episodes: pd.DataFrame | None = None,
    separated_is_married: bool = True,
    missing_spouse: MissingSpousePolicy = MissingSpousePolicy.OWN_ONLY,
    missing_rate: MissingRatePolicy = MissingRatePolicy.REFUSE,
    marriage_history_person_ids: Collection[int] | None = None,
) -> MeasureResult:
    """Present value at age 62 of current-law OASDI payroll taxes (MINT8).

    Each career year's tax is the combined employee-plus-employer OASDI
    rate (``rates.combined_for``; :func:`load_oasdi_tax_rates`) times
    earnings capped at the contribution and benefit base
    (``params.wage_base_for``).  Taxes are accumulated (years before the
    year of attaining 62, ``Y = birth_year + 62``) or discounted (later
    years) to the end of year Y at the trust fund interest rate
    (``interest.rate_for``; :func:`load_trust_fund_interest_rates`) by
    :func:`accumulation_factor`, and summed with ``math.fsum``.

    ``shared=True`` applies MINT8's rule: in each year the person is
    married (year-end state from ``marriage_episodes`` through
    ``psid2010.marital_state_at``), the year's tax is half the sum of the
    two spouses' taxes, the spouse's from the spouse's own career rows; in
    any other year it is the person's own.  A married year whose spouse is
    not in the careers frame follows ``missing_spouse`` and is counted.
    The registered builder defaults are :data:`PAYROLL_TAX_BUILDER_DEFAULTS`.

    Not computed, with a reason: no career rows; an interest rate outside
    the series' coverage under ``missing_rate=NOT_COMPUTED`` (the default
    refuses); a missing spouse under ``missing_spouse=NOT_COMPUTED``.
    """

    if not isinstance(shared, bool):
        raise TypeError("shared must be a bool.")
    missing_spouse = MissingSpousePolicy(missing_spouse)
    missing_rate = MissingRatePolicy(missing_rate)
    if shared and marriage_episodes is None:
        raise ValueError("shared=True needs marriage_episodes.")
    careers_frame = _careers_frame(careers)
    persons_frame = _persons_frame(persons)
    taxes = annual_payroll_taxes(careers_frame, params, rates)
    tax_by_person: dict[int, dict[int, float]] = {}
    for pid, year, tax in zip(
        taxes["person_id"], taxes["year"], taxes["tax"], strict=True
    ):
        tax_by_person.setdefault(int(pid), {})[int(year)] = float(tax)
    imputed = _imputed_years(careers_frame)
    marital = (
        _MaritalYears(
            marriage_episodes, separated_is_married=separated_is_married
        )
        if shared
        else None
    )
    history_ids = (
        None
        if marriage_history_person_ids is None
        else {int(pid) for pid in marriage_history_person_ids}
    )

    rows = []
    uncovered: dict[int, list[int]] = {}
    required_interest_years: set[int] = set()
    for pid, birth in zip(
        persons_frame["person_id"], persons_frame["birth_year"], strict=True
    ):
        pid, birth = int(pid), int(birth)
        reference = birth + _RETIREMENT_AGE
        own = tax_by_person.get(pid, {})
        row: dict[str, Any] = {
            "person_id": pid,
            "birth_year": birth,
            "pv_at_62": math.nan,
            "status": NOT_COMPUTED,
            "reason": None,
            "reference_year": reference,
            "first_tax_year": min(own) if own else None,
            "last_tax_year": max(own) if own else None,
            "history_starts_after_age_22": bool(own)
            and min(own) > birth + _FIRST_AGE,
            "n_tax_years": len(own),
            "n_imputed_tax_years": (
                None if imputed is None else len(imputed.get(pid, set()))
            ),
        }
        amounts: dict[int, float] = dict(own)
        if shared:
            assert marital is not None
            spouses = marital.spouses_ever(pid)
            candidates = set(own)
            for spouse in spouses:
                candidates |= set(tax_by_person.get(spouse, {}))
            amounts, counts = _shared_amounts(
                pid, own, tax_by_person, marital, candidates
            )
            row.update(vars(counts))
            row["marriage_history_absent"] = (
                None if history_ids is None else pid not in history_ids
            )
        if not own:
            row["reason"] = "no_career_rows"
        elif (
            shared
            and missing_spouse is MissingSpousePolicy.NOT_COMPUTED
            and row["married_years_spouse_unavailable"] > 0
        ):
            row["reason"] = "spouse_career_unavailable"
        else:
            needed = set()
            for year in amounts:
                low, high = sorted((year, reference))
                needed.update(range(low + 1, high + 1))
            required_interest_years.update(needed)
            gaps = sorted(
                year for year in needed if not _covers(interest, year)
            )
            if gaps:
                uncovered[pid] = gaps
                row["reason"] = f"interest_rate_unavailable:{gaps[0]}"
            else:
                row["pv_at_62"] = math.fsum(
                    amount * accumulation_factor(year, reference, interest)
                    for year, amount in sorted(amounts.items())
                )
                row["status"] = COMPUTED
        rows.append(row)
    if uncovered and missing_rate is MissingRatePolicy.REFUSE:
        years = sorted({year for gaps in uncovered.values() for year in gaps})
        raise ValueError(
            f"{len(uncovered)} persons need trust fund interest rates for "
            f"years {years[0]}-{years[-1]} that the series does not cover; "
            "extend it with TrustFundInterestRates.extended(..., source=...) "
            "or pass missing_rate=MissingRatePolicy.NOT_COMPUTED."
        )
    columns = list(_PV_COLUMNS) + (list(_SHARE_COLUMNS) if shared else [])
    frame = pd.DataFrame(rows, columns=columns).astype(
        {
            "first_tax_year": "Int64",
            "last_tax_year": "Int64",
            "n_imputed_tax_years": "Int64",
        }
    )
    if shared:
        frame["marriage_history_absent"] = frame[
            "marriage_history_absent"
        ].astype("boolean")
    measure = (
        "lifetime_payroll_tax_pv_at_62_shared"
        if shared
        else "lifetime_payroll_tax_pv_at_62"
    )
    provenance = _provenance(
        measure,
        frame,
        params,
        _input_digests(
            careers_frame,
            persons_frame,
            marriage_episodes if shared else None,
            history_ids if shared else None,
        ),
        {
            "shared": shared,
            "builder_defaults": PAYROLL_TAX_BUILDER_DEFAULTS,
            "separated_is_married": bool(separated_is_married),
            "missing_spouse": missing_spouse.value,
            "missing_rate": missing_rate.value,
            "definition": (
                "mint8:lifetime_payroll_tax_quintile_shared"
                if shared
                else "mint8:lifetime_payroll_tax_quintile"
            ),
        },
        {
            "tax_rates": {
                **dict(getattr(rates, "provenance", {}) or {}),
                "basis": getattr(rates, "basis", None),
                "applied_rates_sha256": _schedule_sha256(
                    dict(
                        zip(taxes["year"], taxes["combined_rate"], strict=True)
                    )
                ),
            },
            "interest_rates": {
                **dict(getattr(interest, "provenance", {}) or {}),
                "assumed_years": sorted(
                    getattr(interest, "assumed_years", frozenset())
                ),
                "assumption_source": getattr(
                    interest, "assumption_source", None
                ),
                "series": getattr(interest, "series", None),
                "required_years": sorted(required_interest_years),
                "available_rates_sha256": _schedule_sha256(
                    {
                        year: interest.rate_for(year)
                        for year in required_interest_years
                        if _covers(interest, year)
                    }
                ),
            },
        },
    )
    return MeasureResult(measure, frame, provenance)


def _covers(interest: _InterestRateSource, year: int) -> bool:
    covers = getattr(interest, "covers", None)
    if covers is not None:
        return bool(covers(year))
    try:
        interest.rate_for(year)
    except KeyError:
        return False
    return True


# ---------------------------------------------------------------------------
# 3. The Report's average indexed earnings at ages 22-62
# ---------------------------------------------------------------------------
_REPORT_COLUMNS = (
    "person_id",
    "birth_year",
    "average_indexed_earnings",
    "status",
    "reason",
    "index_year",
    "n_ages_covered",
    "n_ages_window",
    "ages_complete",
    "n_imputed_years",
)


def report_average_indexed_earnings_22_62(
    careers: pd.DataFrame,
    persons: pd.DataFrame,
    params: SSAParameters,
    *,
    shared: bool,
    marriage_episodes: pd.DataFrame | None = None,
    conventions: ReportEarningsConventions | None = None,
    marriage_history_person_ids: Collection[int] | None = None,
) -> MeasureResult:
    """Butrica and Uccello (2004)'s lifetime earnings, as recorded.

    The average over ages ``first_age``-``last_age`` (22-62) of nominal
    earnings indexed by NAWI to the year of attaining ``index_age``,
    uncapped (the recorded own measure includes earnings above the taxable
    maximum).  ``shared=True`` averages, at each covered age the person is
    married, the mean of the two spouses' indexed earnings.  Every
    unrecorded convention is a registered builder default
    (:data:`REPORT_EARNINGS_BUILDER_DEFAULTS`), set in ``conventions``.

    Not computed, with a reason: no career row at ages 22-62; a NAWI value
    the indexing needs; a missing spouse under
    ``missing_spouse=NOT_COMPUTED``.
    """

    conventions = conventions or ReportEarningsConventions()
    if not isinstance(shared, bool):
        raise TypeError("shared must be a bool.")
    for name in ("first_age", "last_age", "index_age"):
        _year(getattr(conventions, name), name)
    if shared and marriage_episodes is None:
        raise ValueError("shared=True needs marriage_episodes.")
    if conventions.last_age < conventions.first_age:
        raise ValueError("last_age precedes first_age.")
    divisor = AverageDivisor(conventions.divisor)
    missing_spouse = MissingSpousePolicy(conventions.missing_spouse)
    careers_frame = _careers_frame(careers)
    persons_frame = _persons_frame(persons)
    histories = _histories(careers_frame)
    imputed = _imputed_years(careers_frame)
    marital = (
        _MaritalYears(
            marriage_episodes,
            separated_is_married=conventions.separated_is_married,
        )
        if shared
        else None
    )
    history_ids = (
        None
        if marriage_history_person_ids is None
        else {int(pid) for pid in marriage_history_person_ids}
    )
    window_length = conventions.last_age - conventions.first_age + 1

    def earnings_value(earnings: float, year: int) -> float:
        if conventions.cap_at_taxable_maximum:
            return min(earnings, _wage_base(year, params))
        return earnings

    rows = []
    for pid, birth in zip(
        persons_frame["person_id"], persons_frame["birth_year"], strict=True
    ):
        pid, birth = int(pid), int(birth)
        first_year = birth + conventions.first_age
        last_year = birth + conventions.last_age
        index_year = birth + conventions.index_age
        own = {
            year: earnings_value(value, year)
            for year, value in histories.get(pid, {}).items()
            if first_year <= year <= last_year
        }
        row: dict[str, Any] = {
            "person_id": pid,
            "birth_year": birth,
            "average_indexed_earnings": math.nan,
            "status": NOT_COMPUTED,
            "reason": None,
            "index_year": index_year,
            "n_ages_covered": len(own),
            "n_ages_window": window_length,
            "ages_complete": len(own) == window_length,
            "n_imputed_years": (
                None
                if imputed is None
                else len(imputed.get(pid, set()) & set(own))
            ),
        }
        amounts: dict[int, float] = dict(own)
        if shared:
            assert marital is not None
            spouse_amounts = {}
            for spouse in marital.spouses_ever(pid):
                if spouse in histories:
                    spouse_amounts[spouse] = {
                        year: earnings_value(value, year)
                        for year, value in histories[spouse].items()
                        if first_year <= year <= last_year
                    }
            amounts, counts = _shared_amounts(
                pid, own, spouse_amounts, marital, set(own)
            )
            row.update(vars(counts))
            row["marriage_history_absent"] = (
                None if history_ids is None else pid not in history_ids
            )
        if not own:
            row["reason"] = "no_career_rows_at_ages_22_62"
        elif (
            shared
            and missing_spouse is MissingSpousePolicy.NOT_COMPUTED
            and row["married_years_spouse_unavailable"] > 0
        ):
            row["reason"] = "spouse_career_unavailable"
        elif missing := _nawi_missing(amounts, index_year, params):
            row["reason"] = f"nawi_unavailable:{missing[0]}"
        else:
            base = params.nawi[index_year]
            indexed = [
                (
                    value * base / params.nawi[year]
                    if year < index_year
                    else value
                )
                for year, value in sorted(amounts.items())
            ]
            count = (
                len(own)
                if divisor is AverageDivisor.COVERED_AGES
                else (window_length)
            )
            row["average_indexed_earnings"] = math.fsum(indexed) / count
            row["status"] = COMPUTED
        rows.append(row)
    columns = list(_REPORT_COLUMNS) + (list(_SHARE_COLUMNS) if shared else [])
    frame = pd.DataFrame(rows, columns=columns).astype(
        {"n_imputed_years": "Int64"}
    )
    if shared:
        frame["marriage_history_absent"] = frame[
            "marriage_history_absent"
        ].astype("boolean")
    measure = (
        "report_average_indexed_earnings_22_62_shared"
        if shared
        else "report_average_indexed_earnings_22_62"
    )
    provenance = _provenance(
        measure,
        frame,
        params,
        _input_digests(
            careers_frame,
            persons_frame,
            marriage_episodes if shared else None,
            history_ids if shared else None,
        ),
        {
            "shared": shared,
            "conventions": {
                "first_age": conventions.first_age,
                "last_age": conventions.last_age,
                "cap_at_taxable_maximum": conventions.cap_at_taxable_maximum,
                "index_age": conventions.index_age,
                "divisor": divisor.value,
                "separated_is_married": conventions.separated_is_married,
                "missing_spouse": missing_spouse.value,
            },
            "recorded": REPORT_EARNINGS_RECORDED,
            "builder_defaults": REPORT_EARNINGS_BUILDER_DEFAULTS,
        },
    )
    return MeasureResult(measure, frame, provenance)


# ---------------------------------------------------------------------------
# 4. Weighted quintiles
# ---------------------------------------------------------------------------
def _quintile_ranks(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Rank 0 (lowest) to 4 (highest) for one cell, exactly.

    Rows sharing a value form one group and always share a rank.  Groups
    are ordered by value; a group whose cumulative weight span is
    [B, B + G] of the total W takes rank floor(5 * (B + G / 2) / W),
    capped at 4: the quintile holding the midpoint of its span. Weights
    are summed as exact fractions. A normalized midpoint within 1e-12
    of an integer boundary (in rank units, 0-5) takes the upper quintile.
    This tolerance absorbs float multiplication error during rescaling;
    exact sums keep the result independent of row order.
    """

    unique, inverse = np.unique(values, return_inverse=True)
    group_weights = [Fraction(0)] * len(unique)
    for group, weight in zip(inverse, weights, strict=True):
        group_weights[group] += Fraction(float(weight))
    total = sum(group_weights, Fraction(0))
    ranks = np.empty(len(unique), dtype=np.int64)
    below = Fraction(0)
    for index, weight in enumerate(group_weights):
        twice_midpoint = 2 * below + weight
        midpoint_rank = Fraction(_N_QUINTILES * twice_midpoint, 2 * total)
        nearest = round(midpoint_rank)
        if abs(midpoint_rank - nearest) <= _QUINTILE_BOUNDARY_TOLERANCE:
            rank = nearest
        else:
            rank = math.floor(midpoint_rank)
        ranks[index] = min(_N_QUINTILES - 1, rank)
        below += weight
    return ranks[inverse]


def weighted_quintiles(
    values: pd.Series,
    weights: pd.Series,
    *,
    by: pd.Series | None = None,
    labels: tuple[str, ...] = QUINTILE_LABELS,
) -> pd.Series:
    """Weighted quintile labels, in MINT order (``Highest`` .. ``Lowest``).

    ``values`` (NaN = no value), ``weights`` (finite and positive for
    every row with a value) and ``by`` (the cell key, e.g.
    :func:`ten_year_birth_cohort`; ``None`` cuts the whole population)
    must share one index.  Quintiles are cut separately within each cell.

    Ties: rows with the same value always share a label; the group takes
    the quintile holding the midpoint of its cumulative weight span
    (:func:`_quintile_ranks`).  So with no ties each quintile holds 20
    percent of the cell's weight to within the largest single weight's
    share.  MINT8 publishes no tie rule ("The dollar ranges are available
    upon request"); this is the builder's registered rule.
    A midpoint within 1e-12 rank units of a boundary takes the upper
    quintile, so floating-point weight rescaling preserves boundary labels.

    Returns a categorical Series named ``quintile`` with categories
    ``labels`` then :data:`NOT_COMPUTED`; a row without a value gets
    :data:`NOT_COMPUTED`.
    """

    labels = tuple(labels)
    if (
        len(labels) != _N_QUINTILES
        or len(set(labels)) != _N_QUINTILES
        or not all(isinstance(label, str) for label in labels)
    ):
        raise ValueError("labels must be five distinct strings.")
    if NOT_COMPUTED in labels:
        raise ValueError(f"{NOT_COMPUTED!r} cannot be a quintile label.")
    values = pd.Series(values)
    weights = pd.Series(weights)
    if not values.index.equals(weights.index):
        raise ValueError("values and weights must share one index.")
    if by is not None:
        by = pd.Series(by)
        if not by.index.equals(values.index):
            raise ValueError("by must share the index of values.")
    numeric = pd.to_numeric(values, errors="raise").astype("float64")
    present = numeric.notna().to_numpy()
    array = numeric.to_numpy()
    if np.isinf(array[present]).any():
        raise ValueError("values must be finite or missing.")
    weight_array = pd.to_numeric(weights, errors="raise").astype("float64")
    weight_array = weight_array.to_numpy()
    usable = weight_array[present]
    if not np.all(np.isfinite(usable)) or (usable <= 0).any():
        raise ValueError("weights must be finite and positive where valued.")
    out = np.full(len(array), NOT_COMPUTED, dtype=object)
    positions = np.flatnonzero(present)
    if len(positions):
        if by is None:
            cells = {None: positions}
        else:
            keys = by.iloc[positions]
            if keys.isna().any():
                raise ValueError("by is missing for a row with a value.")
            grouped = pd.Series(positions, index=keys.to_numpy()).groupby(
                level=0, sort=True
            )
            cells = {key: group.to_numpy() for key, group in grouped}
        label_array = np.array(labels, dtype=object)
        for cell_positions in cells.values():
            ranks = _quintile_ranks(
                array[cell_positions], weight_array[cell_positions]
            )
            out[cell_positions] = label_array[_N_QUINTILES - 1 - ranks]
    return pd.Series(
        pd.Categorical(out, categories=[*labels, NOT_COMPUTED]),
        index=values.index,
        name="quintile",
    )


def ten_year_birth_cohort(birth_years: pd.Series) -> pd.Series:
    """MINT8's 10-year birth cohort label, e.g. 1964 -> '1960–1969'."""
    series = pd.Series(birth_years)
    starts = (_integral(series, "birth_year") // 10) * 10
    return pd.Series(
        [f"{start}{_EN_DASH}{start + 9}" for start in starts],
        index=series.index,
        name="birth_cohort",
        dtype="string",
    )


def quintile_cells(
    birth_years: pd.Series, scope: QuintileScope
) -> pd.Series | None:
    """The ``by`` argument of :func:`weighted_quintiles` for a scope."""
    scope = QuintileScope(scope)
    if scope is QuintileScope.WHOLE_POPULATION:
        return None
    return ten_year_birth_cohort(birth_years)


def quintile_summary(
    labels: pd.Series,
    weights: pd.Series,
    *,
    by: pd.Series | None = None,
) -> pd.DataFrame:
    """Unweighted count, weight and weight share by cell and label.

    The unweighted counts are what MINT8's disclosure rule reads ("suppress
    an entire characteristic subgroup if the sample size for any row in
    that subgroup is less than 100 individuals").
    Categorical inputs retain empty label rows with zero cases, so an
    empty quintile remains visible to that rule. Zero total valued weight
    gives missing shares.
    """

    labels = pd.Series(labels)
    weights = pd.Series(weights)
    if not labels.index.equals(weights.index):
        raise ValueError("labels and weights must share one index.")
    if by is not None and not pd.Series(by).index.equals(labels.index):
        raise ValueError("by must share the index of labels.")
    numeric_weights = pd.to_numeric(weights).astype("float64")
    if not np.all(np.isfinite(numeric_weights)) or (numeric_weights < 0).any():
        raise ValueError("summary weights must be finite and non-negative.")
    cell = (
        pd.Series("all", index=labels.index, dtype="string")
        if by is None
        else pd.Series(by).astype("string")
    )
    frame = pd.DataFrame(
        {
            "cell": cell.to_numpy(),
            "label": labels.astype("string").to_numpy(),
            "weight": numeric_weights.to_numpy(),
        }
    )
    summary = frame.groupby(["cell", "label"], sort=True).agg(
        n=("weight", "size"), weight=("weight", "sum")
    )
    if isinstance(labels.dtype, pd.CategoricalDtype):
        cells = sorted(frame["cell"].dropna().unique())
        label_order = [str(label) for label in labels.cat.categories]
        complete = pd.MultiIndex.from_product(
            [cells, label_order], names=["cell", "label"]
        )
        summary = summary.reindex(complete, fill_value=0)
    summary = summary.reset_index()
    valued = summary[summary["label"] != NOT_COMPUTED]
    totals = valued.groupby("cell")["weight"].sum()
    summary["weight_share"] = [
        (
            weight / totals[cell]
            if label != NOT_COMPUTED and totals.get(cell, 0) > 0
            else math.nan
        )
        for cell, label, weight in zip(
            summary["cell"], summary["label"], summary["weight"], strict=True
        )
    ]
    return summary


# ---------------------------------------------------------------------------
# Schemes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class QuintileDimension:
    """One lifetime-earnings row group of a report's tables.

    ``labels_high_to_low`` or ``scope`` ``None`` means the source does not
    record it; :meth:`labels` and :meth:`cells` then refuse.
    """

    key: str
    section: str
    measure: str
    shared: bool
    scope: QuintileScope | None
    labels_high_to_low: tuple[str, ...] | None
    definition: str
    source: str

    def labels(self) -> tuple[str, ...]:
        if self.labels_high_to_low is None:
            raise ValueError(
                f"{self.key}: the source does not record which label is "
                "the highest quintile; register the order first."
            )
        return self.labels_high_to_low

    def cells(self, birth_years: pd.Series) -> pd.Series | None:
        if self.scope is None:
            raise ValueError(
                f"{self.key}: the source does not record the population "
                "the quintiles are cut over; register it first."
            )
        return quintile_cells(birth_years, self.scope)


@dataclass(frozen=True)
class LifetimeEarningsScheme:
    """A report's lifetime-earnings row groups (data, not code paths)."""

    name: str
    title: str
    source: str
    registered: bool
    dimensions: tuple[QuintileDimension, ...]

    def dimension(self, key: str) -> QuintileDimension:
        for dimension in self.dimensions:
            if dimension.key == key:
                return dimension
        raise KeyError(f"{self.name} has no dimension {key!r}.")


#: Measure function and sharing of each MINT8 cohort-table row group.
MINT8_DIMENSION_MEASURES: dict[str, tuple[str, bool]] = {
    "initial_aime_quintile": ("initial_aime_at_62", False),
    "lifetime_payroll_tax_quintile": ("lifetime_payroll_tax_pv_at_62", False),
    "lifetime_payroll_tax_quintile_shared": (
        "lifetime_payroll_tax_pv_at_62",
        True,
    ),
}


def load_mint8_definitions(
    path: Path = MINT8_DEFINITIONS_PATH,
    *,
    expected_sha256: str = MINT8_DEFINITIONS_SHA256,
) -> dict[str, Any]:
    """The committed verbatim MINT8 definitions (pinned)."""
    document, _ = _read_pinned_json(
        path, expected_sha256, "mint8_lifetime_quintile_definitions.v1"
    )
    return document


def load_mint8_scheme(
    path: Path = MINT8_DEFINITIONS_PATH,
    *,
    expected_sha256: str = MINT8_DEFINITIONS_SHA256,
) -> LifetimeEarningsScheme:
    """MINT8's cohort-table lifetime-earnings scheme, from the data file."""
    document = load_mint8_definitions(path, expected_sha256=expected_sha256)
    labels = tuple(document["quintile_labels_high_to_low"])
    if labels != QUINTILE_LABELS:
        raise ValueError("MINT8 quintile labels differ from QUINTILE_LABELS.")
    sections = document["cohort_table_row_groups"]
    if set(sections) != set(MINT8_DIMENSION_MEASURES):
        raise ValueError("MINT8 row groups differ from the measure map.")
    dimensions = tuple(
        QuintileDimension(
            key=key,
            section=sections[key],
            measure=measure,
            shared=shared,
            scope=QuintileScope.TEN_YEAR_BIRTH_COHORT,
            labels_high_to_low=labels,
            definition=document["definitions"][key]["text"],
            source=(
                f"{document['document']} (dateCertified "
                f"{document['date_certified']}), element id "
                f"{document['definitions'][key]['element_id']}"
            ),
        )
        for key, (measure, shared) in MINT8_DIMENSION_MEASURES.items()
    )
    return LifetimeEarningsScheme(
        name="mint8",
        title="MINT8 cohort tables (benefit/tax ratios, replacement rates)",
        source=f"{_relative(path)} (sha256 {expected_sha256})",
        registered=True,
        dimensions=dimensions,
    )


def boomers2004_scheme() -> LifetimeEarningsScheme:
    """Butrica and Uccello (2004)'s lifetime-earnings rows (unregistered).

    Section and row labels come from Track U's named omissions
    (``uniform_cut_tabulation.NOT_COMPUTED_REPORT_ROWS``).  The order of
    the quintile labels and the quintile population are not recorded, so
    both dimensions refuse to label until a registration records them.
    """

    from populace_dynamics.estimates.uniform_cut_tabulation import (
        NOT_COMPUTED_REPORT_ROWS,
    )

    dimensions = []
    for kind in ("own", "shared"):
        record = NOT_COMPUTED_REPORT_ROWS[f"lifetime_earnings_{kind}"]
        dimensions.append(
            QuintileDimension(
                key=f"lifetime_earnings_{kind}",
                section=record["section"],
                measure="report_average_indexed_earnings_22_62",
                shared=kind == "shared",
                scope=None,
                labels_high_to_low=None,
                definition=REPORT_EARNINGS_RECORDED["measure"],
                source=_REPORT_RECORD,
            )
        )
    return LifetimeEarningsScheme(
        name="boomers2004",
        title="Butrica and Uccello (2004), Tables 19 and 21",
        source=_REPORT_RECORD,
        registered=False,
        dimensions=tuple(dimensions),
    )


#: Scheme builders by name; add a report's scheme here as data.
SCHEMES: dict[str, Callable[[], LifetimeEarningsScheme]] = {
    "mint8": load_mint8_scheme,
    "boomers2004": boomers2004_scheme,
}
