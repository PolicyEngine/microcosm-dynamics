"""Typed accessors for 2008 Trustees Report (TR2008) parameters.

The data live in ``data/external/tr2008/`` and are built by
``scripts/extract_tr2008_parameters.py``; ``provenance.md`` there records
page locators, capture ids, hashes and the transcription check.  Every file
this module reads is pinned by SHA-256 below and verified on first load.

These are model *inputs* for DynaSim scorecard exercise 1 (TR2008 information
vintage).  Nothing here is a DYNASIM comparator value.

TR2008 publishes no DI rates by age.  Its section V.C.6.b cites Actuarial
Study 118 (June 2005) as the 1996-2000 base of its long-range termination
rates by age, sex and duration; ``di_termination_probability``,
``di_incidence_by_age``, ``di_terminations_by_reason`` and
``di_workers_by_age`` read that study's tables (``actuarial_study_118.json``).
They are the published base, not TR2008's projected rates.

Value provenance classes
------------------------
Each accessor that assembles a path returns entries tagged with one of:

``tr2008_v_c1_historical``
    Table V.C1 historical rows (1975-2006), as printed in the report.
``tr2008_v_c1_actual``
    Table V.C1 2007 COLA (footnote 7: actual amount under the
    automatic-adjustment provisions).
``tr2008_v_c1_projected``
    Table V.C1 projected rows (2008-2017) under the chosen alternative.
``tr2008_single_year_vi_f6``
    AWI for 2018-2085 from the single-year VI.F6 table SSA published with
    the report (the printed VI.F6 shows only 2020, 2025, ...; those printed
    values equal the single-year table, see ``transcription_check.json``).
``derived_ultimate_cpi``
    COLA for determination years 2018-2085.  TR2008 prints COLAs only
    through 2017; this is the alternative's ultimate CPI assumption (Table
    II.C1).  The single-year V.B1 CPI change is constant at that ultimate
    value in every year 2018-2082 of each alternative, and the single-year
    VI.F6 adjusted CPI grows at it in every year 2018-2085 (both tested),
    but these are annual-average rates, not the statutory third-quarter
    COLA basis, so the value is derived rather than published.  TR2008
    projects nothing after 2085, so later years are refused.
``realized_splice``
    Supplied by the caller through the ``realized`` argument.

Builder-default choices
-----------------------
The choices this module exposes are keyword arguments;
``PENDING_RULINGS`` lists each one with its default and whether the
default is the plan's named proposal or this module's proposal.  No
ruling of Max's covers them (his 2026-09-23 rulings are plan section 6
decisions 1-3 and A1 referee questions 10 and 11): A1 section 22 lists
the A2 substitutes as builder defaults that the A1 ratification and the
issue #42 registration fix.  A1 section 4 takes the intermediate rate
path, and A1 section 15 freezes mortality to the substitute A2/A4 name
(:data:`MORTALITY_SUBSTITUTE_STANDING`).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "ALTERNATIVES",
    "AwiEntry",
    "ColaEntry",
    "DATA_DIR",
    "DiBeneficiaries",
    "DiIncidenceByAge",
    "DiRate",
    "DiTerminationsByReason",
    "DiWorkersByAge",
    "FILE_SHA256",
    "GAPS",
    "Gap",
    "LifeTableRow",
    "MORTALITY_SUBSTITUTE",
    "MORTALITY_SUBSTITUTE_STANDING",
    "PENDING_RULINGS",
    "PendingRuling",
    "STUDY_118_AGE_GROUPS",
    "TextAssumption",
    "UltimateAssumptions",
    "VerbatimTable",
    "adjusted_cpi",
    "age_sex_adjusted_death_rate",
    "awi",
    "awi_path",
    "cohort_life_expectancy",
    "WageBaseEntry",
    "cola_path",
    "cola_percent",
    "contribution_benefit_base_path",
    "di_beneficiaries",
    "di_conversion_ratios",
    "di_incidence_by_age",
    "di_rates",
    "di_termination_probability",
    "di_terminations_by_reason",
    "di_workers_by_age",
    "economic_assumptions",
    "mortality_improvement_ratio",
    "period_life_expectancy",
    "period_life_table_2004",
    "ssa_2008_table",
    "text_assumption",
    "ultimate_assumptions",
    "verify_files",
]

Alternative = Literal["intermediate", "low_cost", "high_cost"]
Sex = Literal["male", "female"]
AsadrGroup = Literal["total", "under_65", "65_and_over"]
DiRateKind = Literal["incidence", "termination", "prevalence"]
DiRateBasis = Literal["gross", "age_sex_adjusted"]

ALTERNATIVES: tuple[Alternative, ...] = (
    "intermediate",
    "low_cost",
    "high_cost",
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = _PROJECT_ROOT / "data" / "external" / "tr2008"

FILE_SHA256: Mapping[str, str] = {
    "tr2008_report.json": (
        "c16161f1ee99d94d97648da078d686325fb05a0d44653b76bc609158e63f6d62"
    ),
    "tr2008_single_year.json": (
        "6ada61d3f8a3b693939763cbe142d191d81468f73022fb3450ab69f817ab596e"
    ),
    "ssa_2008_vintage.json": (
        "78c5e55b29615e21f60dc6345572ab06206245246394e2a2791d82358c45d7d7"
    ),
    "actuarial_study_118.json": (
        "0cff75e67257f75630f1fb2cbdf7e6b266f47109b5c95e56a976a195f161aa9b"
    ),
    "transcription_check.json": (
        "18066387c4879135978608c53a2f5309e083a2fc89acc7469399712f2ec9b45d"
    ),
    "sources.json": (
        "ac09e00eadb5935f36a6a52a808b0a49bd5c76dac0d594e0fb820bbb3373fbc5"
    ),
}

# Last determination year with a COLA printed in Table V.C1.
LAST_PRINTED_COLA_YEAR = 2017
# Last year of any TR2008 projection (VI.F6, V.A1, V.C5 end in 2085).
LAST_PROJECTION_YEAR = 2085
# Accepted ``post_2017`` values for cola_path / cola_percent.
POST_2017_CHOICES: tuple[str, ...] = ("ultimate_cpi", "none")
# Last year of AWI printed in Table V.C1; later years come from VI.F6.
LAST_V_C1_AWI_YEAR = 2017
# Last row of V.C1's historical section (COLA and AWI); 2007 onward are
# TR2008 estimates, except the footnote-7 actual 2007 COLA.
LAST_HISTORICAL_V_C1_YEAR = 2006


#: The A2 mortality substitute (:func:`mortality_improvement_ratio` applied
#: to :func:`period_life_table_2004`), described once so that every record
#: of it (this module, the Track A mortality provenance and the Track A
#: gaps) reads the same.
MORTALITY_SUBSTITUTE = (
    "SSA 2004 period life table x TR2008 V.A1 age-sex-adjusted death-rate "
    "ratio (projection year / base year) for the under-65 or 65-and-over "
    "group"
)
#: Its standing under the A1 specification.  A1 section 15 freezes
#: mortality by age and sex to the "substitute named by A2/A4"; A1 section
#: 22 lists the A2 substitutes (``PENDING_RULINGS``) as builder defaults,
#: which no ruling of Max's covers, fixed only by the A1 ratification and
#: the issue #42 registration.
MORTALITY_SUBSTITUTE_STANDING = (
    "a builder default, not a ruling: A1 section 15 freezes mortality to "
    "the substitute A2/A4 name, and A1 section 22 lists it among the "
    "builder defaults that the A1 ratification and the issue #42 "
    "registration fix"
)


@dataclass(frozen=True)
class PendingRuling:
    """A builder-default choice exposed as a parameter (no ruling covers it).

    The name is historical: these were listed while the A1 specification
    awaited ratification, and A1 section 22 cites them by this name.
    """

    parameter: str
    accessor: str
    default: str
    alternatives: tuple[str, ...]
    default_basis: str


PENDING_RULINGS: tuple[PendingRuling, ...] = (
    PendingRuling(
        parameter="alternative",
        accessor="cola_path, cola_percent, awi, awi_path and all projected series",
        default="intermediate",
        alternatives=("low_cost", "high_cost"),
        default_basis=(
            "Plan section 4 A1 table, 'Rate path': proposed primary is the "
            "TR2008 intermediate path, which A1 section 4 takes (no "
            "alternative row)."
        ),
    ),
    PendingRuling(
        parameter="post_2017",
        accessor="cola_path, cola_percent",
        default="ultimate_cpi",
        alternatives=("none",),
        default_basis=(
            "Plan section 4 A1 table, 'Rate path': 'V.C1 through 2017, then "
            "2.8% ultimate'. 'none' refuses years TR2008 does not print."
        ),
    ),
    PendingRuling(
        parameter="realized / last_realized_year",
        accessor="cola_path, awi_path",
        default="None (pure TR2008 information set)",
        alternatives=(
            "caller-supplied realized series through a chosen year",
        ),
        default_basis=(
            "For COLAs the plan's proposed primary is the TR2008 path, so no "
            "splice. For the AWI the plan names no choice; the pure-TR2008 "
            "default is this module's proposal by analogy (DYNASIM run 614 "
            "used 2008 Trustees assumptions per the plan). A splice would "
            "change AIME weights. The realized 2008-2010 COLAs in "
            "data/external/ssa_cola_history.json (5.8, 0.0, 0.0) differ "
            "from TR2008's (2.7, 2.5, 2.8), and the plan's floor analysis "
            "assumes the TR2008 path."
        ),
    ),
    PendingRuling(
        parameter="basis (mortality substitute)",
        accessor="mortality_improvement_ratio",
        default="asadr_broad_age_group",
        alternatives=("none: A5 supplies its own substitute",),
        default_basis=(
            "TR2008 does not publish age-specific projected death rates. "
            "Plan A1 row 'Parameters where TR2008 is unavailable: named "
            "substitute, each listed'. This scaling is this module's "
            f"substitute ({MORTALITY_SUBSTITUTE}): "
            f"{MORTALITY_SUBSTITUTE_STANDING}."
        ),
    ),
    PendingRuling(
        parameter="base_year",
        accessor="mortality_improvement_ratio",
        default="2004",
        alternatives=("2007 (last TR2008 estimated historical year)",),
        default_basis=(
            "2004 is the last year of TR2008's historical death rates "
            "(V.A.2) and the year of the 2008-vintage SSA period life table. "
            "Consequence to weigh: V.A1's 2004 rate at 65 and over "
            "(4,940.6) is below TR2008's 2003 value and its 2005-2007 "
            "estimates, so with base 2004 the 65-and-over ratio exceeds 1 "
            "in 2005-2012 under the intermediate path (1.0127 in 2010), in "
            "2005-2024 under low cost and in 2005-2009 under high cost; the "
            "under-65 ratio is below 1 in every year after 2004."
        ),
    ),
)


@dataclass(frozen=True)
class Gap:
    """A series Track A needs that TR2008 does not publish."""

    series: str
    needed_for: str
    in_tr2008: str
    substitute: str
    status: str


GAPS: tuple[Gap, ...] = (
    Gap(
        series="Projected death probabilities by single age, sex and year",
        needed_for="A5 year-aware mortality 2010-2030",
        in_tr2008=(
            "Only age-sex-adjusted death rates (total, under 65, 65+), "
            "period and cohort life expectancy at birth and 65, and summary "
            "average reductions. The age-group/sex/cause reductions are "
            "described (V.A.2) but not published."
        ),
        substitute=(
            "SSA period life table 2004 (captured; equals Supplement 2008 "
            "Table 4.C6) scaled by the published broad-age-group ASADR path "
            "(mortality_improvement_ratio); or Actuarial Study 120 (located, "
            "not transcribed; 2005 Trustees assumptions, a different "
            "vintage). SSA's TR2008 long-range methods documentation "
            "(documentation_2008.pdf) is located by CDX digest but was not "
            "downloaded; whether it tabulates age-sex rates is unknown "
            "(sources.json located_not_committed)."
        ),
        status=f"substitute named: {MORTALITY_SUBSTITUTE_STANDING}",
    ),
    Gap(
        series="COLA for determination years 2018-2030",
        needed_for="A6 scenario COLA series to 2030",
        in_tr2008="V.C1 prints COLAs through 2017 only.",
        substitute=(
            "Ultimate CPI (II.C1), matching the plan's proposed rate path."
        ),
        status=(
            "derived; A1 section 4 sets 2018-2030 at 2.8 percent, the "
            "intermediate ultimate CPI rate"
        ),
    ),
    Gap(
        series="DI incidence rates by age and sex",
        needed_for="A4 DI award incidence",
        in_tr2008=(
            "Ultimate age-sex-adjusted rate (text), annual gross and "
            "age-sex-adjusted aggregate rates (Figure V.C3 plot points). "
            "No age profile, historical or projected."
        ),
        substitute=(
            "Actuarial Study 118 Table 4: awards per 1,000 exposed by "
            "five-year age group and sex, 1980-2004 (parsed; "
            "di_incidence_by_age). For 2005-2008: DI ASR 2008 awards by "
            "sex and age (Tables 36, 39) over Supplement 2008 Table 4.C2 "
            "disability-insured counts (verbatim; rates not computed "
            "here). The age profile behind TR2008's projected incidence "
            "is not published in any source examined; the TR2008 "
            "long-range methods documentation is located but not "
            "examined (sources.json located_not_committed)."
        ),
        status=(
            "historical age profile captured; projected age profile not "
            "found in any source examined; A4 chooses"
        ),
    ),
    Gap(
        series="DI termination (death, recovery) by age, sex and duration",
        needed_for="A4 DI duration",
        in_tr2008=(
            "Aggregate age-sex-adjusted death and recovery rates in text "
            "(2007, 2017, ultimate, 2085) and annual total termination "
            "rates (Figure V.C4 plot points). V.C.6.b says long-range "
            "rates are projected relative to 1996-2000 rates by age, sex "
            "and duration, citing Actuarial Study 118."
        ),
        substitute=(
            "Actuarial Study 118 Tables 7A-7C (death) and 14A-14B "
            "(recovery): 1996-2000 select-and-ultimate probabilities by "
            "select age, sex and duration, the base TR2008 names (parsed; "
            "di_termination_probability). How TR2008 moves from that base "
            "to its projected rates is stated only in aggregate "
            "(text_assumption) in the sources examined; the TR2008 "
            "long-range methods documentation is located but not "
            "examined."
        ),
        status=(
            "published base captured; TR2008's projected rates by age, sex "
            "and duration not found in any source examined"
        ),
    ),
    Gap(
        series="DI terminations by age and sex, 2005-2008",
        needed_for="A4 validation of termination by age",
        in_tr2008="None.",
        substitute=(
            "DI ASR 2008 Table 57 (captured verbatim) gives terminations "
            "by sex and age only for successful return to work; Table 53 "
            "(same capture, not extracted) gives those terminations by "
            "diagnostic group and age; Tables 49-50 give terminations by "
            "beneficiary type and by reason, with no age or sex. "
            "Actuarial Study 118 Table 5 gives "
            "terminations by reason and sex, without age, for 1980-2004 "
            "(di_terminations_by_reason)."
        ),
        status=(
            "death and recovery terminations by age and sex not found in "
            "the DI ASR 2008 (all 68 tables in its expanded contents) or "
            "Supplement 2008 section 6.F"
        ),
    ),
    Gap(
        series="DI prevalence by age and sex",
        needed_for="A4 opening stock and validation",
        in_tr2008="Aggregate gross and age-sex-adjusted prevalence (V.C5).",
        substitute=(
            "Actuarial Study 118 Table 6: disabled workers by age group "
            "and sex, 1980-2004 (parsed; di_workers_by_age). DI ASR 2008 "
            "Tables 19-20 (disabled workers by sex and age) and Table 2 "
            "(all disabled beneficiaries by basis of entitlement, age and "
            "sex), captured verbatim, with Supplement 2008 Table 4.C2."
        ),
        status="inputs captured",
    ),
    Gap(
        series="AWI before 1975",
        needed_for="AIME indexing for earnings before 1975",
        in_tr2008="V.C1 starts in 1975.",
        substitute=(
            "Realized SSA series (e.g. the oracle's NAWI) through a splice "
            "year via awi_path(realized=..., last_realized_year=...)."
        ),
        status="not captured here",
    ),
)


@dataclass(frozen=True)
class ColaEntry:
    """One automatic benefit increase."""

    determination_year: int
    percent: float
    source: str
    effective_month: Literal["June", "December"]


@dataclass(frozen=True)
class AwiEntry:
    """One national average wage index value."""

    year: int
    amount: float
    source: str


@dataclass(frozen=True)
class WageBaseEntry:
    """One OASDI contribution and benefit base (V.C1), in dollars."""

    year: int
    amount: float
    source: str


@dataclass(frozen=True)
class UltimateAssumptions:
    """Table II.C1 ultimate values for one alternative."""

    alternative: Alternative
    total_fertility_rate: float
    death_rate_reduction_2032_2082: float
    net_immigration_thousands_2008_82: float
    productivity: float
    average_covered_wage: float
    cpi: float
    real_wage_differential: float
    unemployment_rate: float
    real_interest_rate: float


@dataclass(frozen=True)
class EconomicAssumptions:
    """One single-year V.B1 row (annual percentage changes)."""

    year: int
    productivity: float
    earnings_to_compensation: float
    average_hours_worked: float
    gdp_price_index: float
    average_covered_wage: float
    cpi: float
    real_wage_differential: float
    source: str


@dataclass(frozen=True)
class LifeTableRow:
    """One age of the 2004 period life table for one sex."""

    age: int
    qx: float
    lx: int
    ex: float


@dataclass(frozen=True)
class DiRate:
    """One year of an aggregate DI rate (figure plot points)."""

    year: int
    value: float
    projected: bool


@dataclass(frozen=True)
class DiBeneficiaries:
    """One end-of-year V.C5 row (single-year table)."""

    year: int
    disabled_workers_thousands: int
    spouses_thousands: int
    children_thousands: int
    total_thousands: int
    prevalence_gross_per_1000: int
    prevalence_age_sex_adjusted_per_1000: int


@dataclass(frozen=True)
class TextAssumption:
    """An assumption stated in TR2008 prose, with its page locator."""

    id: str
    values: Mapping[str, float]
    unit: str
    meaning: str
    pdf_pages: tuple[int, ...]
    printed_pages: tuple[int, ...]
    quote: str


@dataclass(frozen=True)
class VerbatimTable:
    """A 2008-vintage SSA table kept as verbatim cell text."""

    key: str
    caption: str
    source: str
    rows: tuple[tuple[str, ...], ...]


# Actuarial Study 118 age groups (Tables 4 and 6), as printed.
STUDY_118_AGE_GROUPS: tuple[str, ...] = (
    "15-19",
    "20-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
    "65 or older",
)
_STUDY_118_AGE_KEYS = tuple(
    f"age_{label.replace('-', '_').replace(' or older', '_plus')}"
    for label in STUDY_118_AGE_GROUPS
)
Study118Sex = Literal["male", "female", "total"]


@dataclass(frozen=True)
class DiIncidenceByAge:
    """Study 118 Table 4: disabled-worker awards per 1,000 exposed.

    Exposed: disability-insured persons not receiving benefits.  ``adjusted``
    is age-adjusted (by sex) or age-sex-adjusted (total) to the calendar
    2000 exposure.
    """

    year: int
    sex: Study118Sex
    by_age: Mapping[str, float]
    gross: float
    adjusted: float
    source: str


@dataclass(frozen=True)
class DiTerminationsByReason:
    """Study 118 Table 5: disabled-worker terminations and rates per 1,000."""

    year: int
    sex: Study118Sex
    numbers: Mapping[str, int]
    rates_per_1000: Mapping[str, float]
    source: str


@dataclass(frozen=True)
class DiWorkersByAge:
    """Study 118 Table 6: disabled workers in current-payment status."""

    year: int
    sex: Study118Sex
    by_age: Mapping[str, int]
    total: int
    source: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_files(data_dir: Path = DATA_DIR) -> None:
    """Raise unless every consumed file matches its pinned SHA-256."""
    for name, expected in FILE_SHA256.items():
        observed = _sha256(data_dir / name)
        if observed != expected:
            raise ValueError(
                f"{name} sha256 {observed} != pinned {expected}; rebuild "
                "with scripts/extract_tr2008_parameters.py and re-pin"
            )


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    verify_files()
    return {
        name: json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
        for name in FILE_SHA256
    }


def _report() -> dict[str, Any]:
    return _data()["tr2008_report.json"]


def _single() -> dict[str, Any]:
    return _data()["tr2008_single_year.json"]


def _check_alternative(alternative: str) -> None:
    if alternative not in ALTERNATIVES:
        raise ValueError(
            f"alternative must be one of {ALTERNATIVES}, got {alternative!r}"
        )


def _v_c1_rows(alternative: Alternative) -> dict[int, dict[str, Any]]:
    sections = _report()["tables"]["V.C1"]["sections"]
    rows = {row["year"]: row for row in sections["historical"]}
    rows.update({row["year"]: row for row in sections[alternative]})
    return rows


# --------------------------------------------------------------------------
# COLA
# --------------------------------------------------------------------------


def _printed_cola(year: int, alternative: Alternative) -> ColaEntry | None:
    row = _v_c1_rows(alternative).get(year)
    if row is None:
        return None
    if year <= LAST_HISTORICAL_V_C1_YEAR:
        source = "tr2008_v_c1_historical"
    elif row.get("footnotes", {}).get("cola_percent") == "7":
        source = "tr2008_v_c1_actual"
    else:
        source = "tr2008_v_c1_projected"
    return ColaEntry(
        determination_year=year,
        percent=float(row["cola_percent"]),
        source=source,
        effective_month="June" if year <= 1982 else "December",
    )


def cola_percent(
    determination_year: int,
    *,
    alternative: Alternative = "intermediate",
    post_2017: Literal["ultimate_cpi", "none"] = "ultimate_cpi",
) -> float:
    """TR2008 automatic benefit increase (percent) for one year.

    ``determination_year`` follows V.C1 footnote 1: effective with benefits
    payable for June in 1975-82 and for December in each later year (so the
    increase for determination year ``t > 1982`` is first paid in January of
    ``t + 1``).
    """
    (entry,) = cola_path(
        determination_year,
        determination_year,
        alternative=alternative,
        post_2017=post_2017,
    )
    return entry.percent


def cola_path(
    first_year: int,
    last_year: int,
    *,
    alternative: Alternative = "intermediate",
    post_2017: Literal["ultimate_cpi", "none"] = "ultimate_cpi",
    realized: Mapping[int, float] | None = None,
    last_realized_year: int | None = None,
) -> tuple[ColaEntry, ...]:
    """TR2008 COLA path for determination years ``first_year..last_year``.

    Defaults give the plan's proposed primary rate path: V.C1 through 2017,
    then the ultimate CPI assumption through 2085, the last year TR2008
    projects (later years raise ``KeyError``).  ``post_2017="none"`` refuses
    years TR2008 does not print.  ``realized`` with ``last_realized_year``
    replaces years up to and including that year with caller-supplied values
    (a builder-default choice, ``PENDING_RULINGS``; A1's section 21 block
    forbids a realized-series substitution in the rate path).
    """
    _check_alternative(alternative)
    if post_2017 not in POST_2017_CHOICES:
        raise ValueError(
            f"post_2017 must be one of {POST_2017_CHOICES}, got {post_2017!r}"
        )
    if first_year > last_year:
        raise ValueError("first_year must not exceed last_year")
    if (realized is None) != (last_realized_year is None):
        raise ValueError("pass realized and last_realized_year together")
    ultimate = ultimate_assumptions(alternative).cpi
    out = []
    for year in range(first_year, last_year + 1):
        if realized is not None and year <= last_realized_year:
            if year not in realized:
                raise KeyError(f"realized COLA missing for {year}")
            out.append(
                ColaEntry(
                    year,
                    float(realized[year]),
                    "realized_splice",
                    "June" if year <= 1982 else "December",
                )
            )
            continue
        entry = _printed_cola(year, alternative)
        if entry is not None:
            out.append(entry)
        elif year > LAST_PROJECTION_YEAR:
            raise KeyError(
                f"TR2008 projects nothing after {LAST_PROJECTION_YEAR}; no "
                f"COLA for {year}"
            )
        elif year > LAST_PRINTED_COLA_YEAR and post_2017 == "ultimate_cpi":
            out.append(
                ColaEntry(
                    year, float(ultimate), "derived_ultimate_cpi", "December"
                )
            )
        elif year > LAST_PRINTED_COLA_YEAR and post_2017 == "none":
            raise KeyError(
                f"TR2008 prints no COLA for {year} (post_2017='none')"
            )
        else:
            raise KeyError(f"TR2008 V.C1 has no COLA for {year}")
    return tuple(out)


# --------------------------------------------------------------------------
# Average wage index
# --------------------------------------------------------------------------


def _tr2008_awi(year: int, alternative: Alternative) -> AwiEntry:
    if year <= LAST_V_C1_AWI_YEAR:
        row = _v_c1_rows(alternative).get(year)
        if row is None:
            raise KeyError(f"TR2008 V.C1 has no AWI for {year}")
        source = (
            "tr2008_v_c1_historical"
            if year <= LAST_HISTORICAL_V_C1_YEAR
            else "tr2008_v_c1_projected"
        )
        return AwiEntry(year, float(row["awi"]), source)
    rows = _single()["tables"]["VI.F6"]["sections"][alternative]
    for row in rows:
        if row["year"] == year:
            return AwiEntry(
                year, float(row["awi"]), "tr2008_single_year_vi_f6"
            )
    raise KeyError(f"TR2008 VI.F6 has no AWI for {year}")


def awi(year: int, *, alternative: Alternative = "intermediate") -> float:
    """TR2008 national average wage index for ``year`` (1975-2085)."""
    _check_alternative(alternative)
    return _tr2008_awi(year, alternative).amount


def awi_path(
    first_year: int,
    last_year: int,
    *,
    alternative: Alternative = "intermediate",
    realized: Mapping[int, float] | None = None,
    last_realized_year: int | None = None,
) -> tuple[AwiEntry, ...]:
    """AWI path under TR2008, optionally spliced onto a realized series.

    Default: TR2008 levels throughout (historical through 2006, TR2008
    estimates from 2007).  With ``realized`` and ``last_realized_year`` = Y,
    years up to Y use the realized values and each later year ``t`` is
    ``realized[Y] * AWI_TR2008(t) / AWI_TR2008(Y)``, i.e. TR2008 growth
    chained onto the last realized level.  No splice is the builder
    default (``PENDING_RULINGS``).
    """
    _check_alternative(alternative)
    if first_year > last_year:
        raise ValueError("first_year must not exceed last_year")
    if (realized is None) != (last_realized_year is None):
        raise ValueError("pass realized and last_realized_year together")
    out = []
    for year in range(first_year, last_year + 1):
        if realized is not None and year <= last_realized_year:
            if year not in realized:
                raise KeyError(f"realized AWI missing for {year}")
            out.append(
                AwiEntry(year, float(realized[year]), "realized_splice")
            )
            continue
        entry = _tr2008_awi(year, alternative)
        if realized is not None:
            anchor = _tr2008_awi(last_realized_year, alternative).amount
            amount = (
                float(realized[last_realized_year]) * entry.amount / anchor
            )
            entry = AwiEntry(
                year, amount, f"{entry.source}_growth_on_realized"
            )
        out.append(entry)
    return tuple(out)


def contribution_benefit_base_path(
    first_year: int,
    last_year: int,
    *,
    alternative: Alternative = "intermediate",
) -> tuple[WageBaseEntry, ...]:
    """TR2008 V.C1 OASDI contribution and benefit base, 1975-2017.

    ``source`` is ``tr2008_v_c1_historical`` through 2006,
    ``tr2008_v_c1_actual`` where footnote 7 marks the printed amount as
    determined under the automatic-adjustment provisions, and
    ``tr2008_v_c1_projected`` otherwise.  V.C1 prints nothing before 1975
    or after 2017 (``KeyError``).
    """
    _check_alternative(alternative)
    if first_year > last_year:
        raise ValueError("first_year must not exceed last_year")
    rows = _v_c1_rows(alternative)
    out = []
    for year in range(first_year, last_year + 1):
        row = rows.get(year)
        if row is None or row.get("contribution_benefit_base") is None:
            raise KeyError(
                f"TR2008 V.C1 prints no contribution and benefit base for "
                f"{year}"
            )
        if year <= LAST_HISTORICAL_V_C1_YEAR:
            source = "tr2008_v_c1_historical"
        elif row.get("footnotes", {}).get("contribution_benefit_base") == "7":
            source = "tr2008_v_c1_actual"
        else:
            source = "tr2008_v_c1_projected"
        out.append(
            WageBaseEntry(
                year, float(row["contribution_benefit_base"]), source
            )
        )
    return tuple(out)


# --------------------------------------------------------------------------
# Economic assumptions
# --------------------------------------------------------------------------


def ultimate_assumptions(
    alternative: Alternative = "intermediate",
) -> UltimateAssumptions:
    """Table II.C1 ultimate values (report page 6)."""
    _check_alternative(alternative)
    rows = _report()["tables"]["II.C1"]["rows"]
    return UltimateAssumptions(
        alternative=alternative,
        **{key: float(values[alternative]) for key, values in rows.items()},
    )


def economic_assumptions(
    year: int, *, alternative: Alternative = "intermediate"
) -> EconomicAssumptions:
    """Single-year V.B1 row: historical 1960-2007, projected 2008-2082.

    The 2007 row is an estimate: the table's footnote says full-year data
    were not available and that the estimates "vary slightly by
    alternative and are shown for the intermediate alternative".  It is
    returned for every alternative with the source tag
    ``tr2008_single_year_v_b1/historical_estimate_intermediate_only``.
    """
    _check_alternative(alternative)
    sections = _single()["tables"]["V.B1"]["sections"]
    section = "historical" if year <= 2007 else alternative
    for row in sections[section]:
        if row["year"] == year:
            source = f"tr2008_single_year_v_b1/{section}"
            if section == "historical" and row.get("footnote"):
                source += "_estimate_intermediate_only"
            values = {
                key: float(row[key])
                for key in (
                    "productivity",
                    "earnings_to_compensation",
                    "average_hours_worked",
                    "gdp_price_index",
                    "average_covered_wage",
                    "cpi",
                    "real_wage_differential",
                )
            }
            return EconomicAssumptions(year=year, source=source, **values)
    raise KeyError(f"TR2008 single-year V.B1 has no {section} row for {year}")


def adjusted_cpi(
    year: int, *, alternative: Alternative = "intermediate"
) -> float:
    """VI.F6 adjusted CPI (CPI-W, calendar 2008 = 100), 2007-2085."""
    _check_alternative(alternative)
    for row in _single()["tables"]["VI.F6"]["sections"][alternative]:
        if row["year"] == year:
            return float(row["adjusted_cpi"])
    raise KeyError(f"TR2008 VI.F6 has no adjusted CPI for {year}")


# --------------------------------------------------------------------------
# Mortality
# --------------------------------------------------------------------------


def age_sex_adjusted_death_rate(
    year: int,
    *,
    alternative: Alternative = "intermediate",
    group: AsadrGroup = "total",
) -> float:
    """Single-year V.A1 age-sex-adjusted death rate per 100,000.

    Adjusted to the April 1, 2000 enumerated population (V.A1 footnote 2).
    Historical through 2007 (2005-2007 estimated), projected 2008-2085.
    """
    _check_alternative(alternative)
    column = f"asadr_{group}"
    sections = _single()["tables"]["V.A1"]["sections"]
    section = "historical" if year <= 2007 else alternative
    for row in sections[section]:
        if row["year"] == year:
            return float(row[column])
    raise KeyError(f"TR2008 single-year V.A1 has no row for {year}")


def mortality_improvement_ratio(
    year: int,
    age: int,
    *,
    alternative: Alternative = "intermediate",
    base_year: int = 2004,
    basis: Literal["asadr_broad_age_group"] = "asadr_broad_age_group",
) -> float:
    """The A2 substitute for TR2008's unpublished age-specific mortality.

    Returns ``ASADR(year, g) / ASADR(base_year, g)`` where ``g`` is the V.A1
    group containing ``age`` (under 65, or 65 and over).  Multiplying the
    2004 period ``qx`` by this ratio is one way to make a year-aware table;
    it is a derivation from published aggregates, not a TR2008 assumption,
    and :data:`MORTALITY_SUBSTITUTE_STANDING` states its standing under A1
    (``PENDING_RULINGS``).  With the default
    ``base_year=2004`` the 65-and-over ratio is above 1 in 2005-2012
    (intermediate), because V.A1's 2004 rate is below its 2005-2007
    estimates; the ``base_year`` entry of ``PENDING_RULINGS`` records this.
    """
    if basis != "asadr_broad_age_group":
        raise ValueError(f"unknown mortality substitute basis {basis!r}")
    if age < 0:
        raise ValueError("age must be non-negative")
    group: AsadrGroup = "under_65" if age < 65 else "65_and_over"
    numerator = age_sex_adjusted_death_rate(
        year, alternative=alternative, group=group
    )
    denominator = age_sex_adjusted_death_rate(
        base_year, alternative=alternative, group=group
    )
    return numerator / denominator


def _life_expectancy(
    table: str, year: int, alternative: Alternative, sex: Sex, age: int
) -> float:
    _check_alternative(alternative)
    if age not in (0, 65):
        raise ValueError("TR2008 publishes life expectancy at 0 and 65 only")
    label = "at_birth" if age == 0 else "at_65"
    for row in _single()["tables"][table]["rows"]:
        if row["year"] == year:
            if row.get("historical"):
                return float(row[f"intermediate_{label}_{sex}"])
            return float(row[f"{alternative}_{label}_{sex}"])
    raise KeyError(f"TR2008 single-year {table} has no row for {year}")


def period_life_expectancy(
    year: int,
    *,
    sex: Sex,
    age: Literal[0, 65],
    alternative: Alternative = "intermediate",
) -> float:
    """Single-year V.A3 period life expectancy (historical rows: one series)."""
    return _life_expectancy("V.A3", year, alternative, sex, age)


def cohort_life_expectancy(
    year: int,
    *,
    sex: Sex,
    age: Literal[0, 65],
    alternative: Alternative = "intermediate",
) -> float:
    """Single-year V.A4 cohort life expectancy (born, or 65, on Jan 1)."""
    return _life_expectancy("V.A4", year, alternative, sex, age)


def period_life_table_2004(sex: Sex) -> tuple[LifeTableRow, ...]:
    """SSA period life table for 2004 (ages 0-119), as posted 2008-03-27.

    A 2008-vintage SSA source, not a TR2008 table: TR2008's historical
    death rates run through 2004 (V.A.2), and this table's e0 and e65 round
    to the V.A3 2004 values.  It equals Supplement 2008 Table 4.C6.
    """
    if sex not in ("male", "female"):
        raise ValueError("sex must be 'male' or 'female'")
    rows = _data()["ssa_2008_vintage.json"]["period_life_table_2004"]["rows"]
    return tuple(
        LifeTableRow(
            age=row["age"],
            qx=float(row[f"{sex}_qx"]),
            lx=int(row[f"{sex}_lx"]),
            ex=float(row[f"{sex}_ex"]),
        )
        for row in rows
    )


# --------------------------------------------------------------------------
# Disability insurance
# --------------------------------------------------------------------------

_DI_FIGURES = {
    "incidence": "V.C3",
    "termination": "V.C4",
    "prevalence": "V.C6",
}


def di_rates(
    kind: DiRateKind,
    *,
    alternative: Alternative = "intermediate",
    basis: DiRateBasis = "age_sex_adjusted",
) -> tuple[DiRate, ...]:
    """Aggregate DI rates 1970-2085 from the TR2008 figure plot points.

    Incidence: awards per 1,000 disability exposed (Figure V.C3).
    Termination: terminations per 1,000 disabled-worker beneficiaries
    (Figure V.C4; death and recovery combined).  Prevalence: per 1,000
    disability insured (Figure V.C6).  Historical rows (1970-2007) are one
    series; projected rows (2008-2085) are per alternative.  TR2008 does
    not publish these rates by age.
    """
    _check_alternative(alternative)
    if basis not in ("gross", "age_sex_adjusted"):
        raise ValueError(f"unknown basis {basis!r}")
    figure = _single()["figures"][_DI_FIGURES[kind]]
    out = [
        DiRate(row["year"], float(row[basis]), False)
        for row in figure["historical"]
    ]
    out.extend(
        DiRate(row["year"], float(row[basis][alternative]), True)
        for row in figure["projected"]
    )
    return tuple(out)


def di_conversion_ratios(
    basis: DiRateBasis = "age_sex_adjusted",
) -> tuple[DiRate, ...]:
    """Conversions at NRA per 1,000 disabled workers (Figure V.C5).

    Intermediate assumptions only; 1970-2007 historical, 2008+ projected.
    """
    if basis not in ("gross", "age_sex_adjusted"):
        raise ValueError(f"unknown basis {basis!r}")
    key = f"conversion_{basis}"
    return tuple(
        DiRate(row["year"], float(row[key]), row["year"] >= 2008)
        for row in _single()["figures"]["V.C5"]["rows"]
    )


def di_beneficiaries(
    year: int, *, alternative: Alternative = "intermediate"
) -> DiBeneficiaries:
    """Single-year V.C5 DI beneficiaries (thousands) and prevalence.

    Covers 1975-2085.  The printed table's 1960, 1965 and 1970 rows are in
    ``tr2008_report.json`` only; the single-year table starts in 1975.
    """
    _check_alternative(alternative)
    sections = _single()["tables"]["V.C5"]["sections"]
    section = "historical" if year <= 2007 else alternative
    for row in sections[section]:
        if row["year"] == year:
            return DiBeneficiaries(
                year=year,
                **{
                    key: int(row[key])
                    for key in (
                        "disabled_workers_thousands",
                        "spouses_thousands",
                        "children_thousands",
                        "total_thousands",
                        "prevalence_gross_per_1000",
                        "prevalence_age_sex_adjusted_per_1000",
                    )
                },
            )
    raise KeyError(f"TR2008 single-year V.C5 has no row for {year}")


# --------------------------------------------------------------------------
# Actuarial Study 118 (TR2008's base for DI rates by age, sex, duration)
# --------------------------------------------------------------------------

_STUDY_118_GRIDS = {
    ("death", "male"): "7A",
    ("death", "female"): "7B",
    ("recovery", "male"): "14A",
    ("recovery", "female"): "14B",
}
STUDY_118_FIRST_SELECT_AGE = 16
STUDY_118_LAST_SELECT_AGE = 64
STUDY_118_LAST_ATTAINED_AGE = 110


def _study_118() -> dict[str, Any]:
    return _data()["actuarial_study_118.json"]


def _study_118_row(table: str, sex: str, year: int) -> dict[str, Any]:
    if sex not in ("male", "female", "total"):
        raise ValueError("sex must be 'male', 'female' or 'total'")
    for row in _study_118()["tables"][table]["sections"][sex]:
        if row["year"] == year:
            return row
    raise KeyError(f"Actuarial Study 118 Table {table} covers 1980-2004")


def di_termination_probability(
    cause: Literal["death", "recovery"],
    *,
    sex: Sex,
    select_age: int,
    duration: int,
) -> float | None:
    """Study 118 1996-2000 DI termination probability for one year.

    The probability that a disabled worker entitled at ``select_age`` (age
    last birthday at entitlement, 16-64) dies, or recovers, during year
    ``duration + 1`` of entitlement, in the study's multiple-decrement
    setting (Tables 7A/7B death, 14A/14B recovery; notes quoted in
    ``actuarial_study_118.json``).  Following note 3, durations 0-10 are
    read across the select row and longer durations down the ultimate
    column at attained age ``select_age + duration``; deaths beyond
    attained age 74 come from Table 7C (to 110).

    Returns ``None`` where the study tabulates nothing: recovery at
    attained ages of 65 and over ("Recovery is not considered beyond
    normal retirement age").  This is the base TR2008 names for its
    long-range rates, not TR2008's projected rates.
    """
    if (cause, sex) not in _STUDY_118_GRIDS:
        raise ValueError(
            "cause must be 'death' or 'recovery' and sex 'male' or 'female'"
        )
    first, last = STUDY_118_FIRST_SELECT_AGE, STUDY_118_LAST_SELECT_AGE
    if not first <= select_age <= last:
        raise ValueError("Actuarial Study 118 tabulates select ages 16-64")
    if duration < 0:
        raise ValueError("duration must be non-negative")
    tables = _study_118()["tables"]
    rows = {
        row["select_age"]: row["by_duration"]
        for row in tables[_STUDY_118_GRIDS[(cause, sex)]]["rows"]
    }
    if duration <= 10:
        return rows[select_age][duration]
    attained = select_age + duration
    if attained - 10 <= STUDY_118_LAST_SELECT_AGE:
        return rows[attained - 10][10]
    if cause == "recovery":
        return None
    if attained > STUDY_118_LAST_ATTAINED_AGE:
        raise KeyError(
            "Actuarial Study 118 tabulates death probabilities to attained "
            "age 110"
        )
    for row in tables["7C"]["rows"]:
        if row["attained_age"] == attained:
            return row[sex]
    raise KeyError(f"Actuarial Study 118 Table 7C has no age {attained}")


def di_incidence_by_age(
    year: int, *, sex: Study118Sex = "total"
) -> DiIncidenceByAge:
    """Study 118 Table 4 DI incidence by age group, 1980-2004."""
    row = _study_118_row("4", sex, year)
    return DiIncidenceByAge(
        year=year,
        sex=sex,
        by_age={
            label: float(row[key])
            for label, key in zip(
                STUDY_118_AGE_GROUPS, _STUDY_118_AGE_KEYS, strict=True
            )
        },
        gross=float(row["total_gross"]),
        adjusted=float(row["total_adjusted"]),
        source="actuarial_study_118_table_4",
    )


def di_terminations_by_reason(
    year: int, *, sex: Study118Sex = "total"
) -> DiTerminationsByReason:
    """Study 118 Table 5 terminations by reason (no age), 1980-2004.

    Reasons: death, recovery, other, conversion (at normal retirement
    age) and total; rates are per 1,000 exposed disabled workers.
    """
    row = _study_118_row("5", sex, year)
    reasons = ("death", "recovery", "other", "conversion", "total")
    return DiTerminationsByReason(
        year=year,
        sex=sex,
        numbers={reason: int(row[f"{reason}_number"]) for reason in reasons},
        rates_per_1000={
            reason: float(row[f"{reason}_rate"]) for reason in reasons
        },
        source="actuarial_study_118_table_5",
    )


def di_workers_by_age(
    year: int, *, sex: Study118Sex = "total"
) -> DiWorkersByAge:
    """Study 118 Table 6 disabled workers by age at end of year, 1980-2004."""
    row = _study_118_row("6", sex, year)
    return DiWorkersByAge(
        year=year,
        sex=sex,
        by_age={
            label: int(row[key])
            for label, key in zip(
                STUDY_118_AGE_GROUPS, _STUDY_118_AGE_KEYS, strict=True
            )
        },
        total=int(row["total"]),
        source="actuarial_study_118_table_6",
    )


# --------------------------------------------------------------------------
# Text assumptions and verbatim 2008-vintage tables
# --------------------------------------------------------------------------


def text_assumption(assumption_id: str) -> TextAssumption:
    """An assumption TR2008 states in prose, with page locators and quote."""
    for entry in _report()["text_values"]:
        if entry["id"] == assumption_id:
            return TextAssumption(
                id=entry["id"],
                values={k: float(v) for k, v in entry["values"].items()},
                unit=entry["unit"],
                meaning=entry["meaning"],
                pdf_pages=tuple(entry["pdf_pages"]),
                printed_pages=tuple(entry["printed_pages"]),
                quote=entry["quote"],
            )
    raise KeyError(f"no TR2008 text assumption {assumption_id!r}")


def ssa_2008_table(
    publication: Literal["di_asr_2008", "supplement_2008"], table: str
) -> VerbatimTable:
    """A captured 2008-vintage SSA table as verbatim cell text.

    ``publication="di_asr_2008"``: Tables 2, 19, 20, 35, 36, 39, 49, 50,
    57.  (SSA's page prints Table 57's caption after the next section's
    heading, "Reinstatement Status for Disabled Workers"; the caption is
    kept verbatim.)
    ``publication="supplement_2008"``: Tables 4.C2, 4.C6.
    """
    tables = _data()["ssa_2008_vintage.json"][publication]
    key = table if table.startswith("Table ") else f"Table {table}"
    entry = tables[key]
    return VerbatimTable(
        key=key,
        caption=entry["caption"],
        source=entry["source"],
        rows=tuple(
            tuple(line.split("\t")) for line in entry["tsv"].splitlines()
        ),
    )
