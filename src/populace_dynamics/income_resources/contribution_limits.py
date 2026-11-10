"""Published retirement contribution ceilings and statutory projections.

This module fits nothing and reads no survey records. Published dollar ceilings
cover 2002--2026, with earlier observations only where the captured IRS table
states them. These are dollar ceilings, before compensation limits, income
phase-outs, employer-plan availability and special service-based catch-ups.

Invariants, tested beside the statutory examples:
* Published ceilings from 2002 are nonnegative and nondecreasing in year.
* Nondecreasing caller index paths give nondecreasing projected ceilings.
* Projections round the increase down in statutory units, never compound a
  previously rounded ceiling; the ages-60--63 base is $11,250, so its increases
  (rather than its total) are multiples of $500.
* Section 415(d) ceilings retain their high-water value during deflation
  (IRS Notice 2009-94); IRA ceilings use the section 1(f)(3) base-year ratio.
* A projection path must reproduce its published 2026 ceiling before use;
  nonnegative inflation cannot lower a ceiling across that boundary.
* Catch-up eligibility uses age at the end of the year; ages 60--63 receive the
  enhanced employer catch-up beginning in 2025.
* Unpublished observations, missing indices and unsupported inputs raise.

Authority: 26 U.S.C. 402(g)(1),(4), 414(v)(2),(5), 415(c)(1),(d),
219(b)(5), and 1(f)(3)--(6). Captures, transcriptions and the base amounts are
versioned under ``retirement_rules_v1/contributions``. The caller supplies the
appropriate CPI-U and chained CPI-U averages, including their historical bases;
the module never silently equates these different inflation series.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from fractions import Fraction
from functools import lru_cache
from pathlib import Path


class ContributionRuleError(ValueError):
    """A contribution rule or its required inflation inputs are not covered."""


class ContributionLimit(str, Enum):
    """Dollar ceilings; SIMPLE and service-based catch-ups are not included."""

    ELECTIVE_DEFERRAL = "elective_deferral"
    EMPLOYER_CATCH_UP = "employer_catch_up"
    ANNUAL_ADDITIONS = "annual_additions"
    IRA = "ira"
    IRA_CATCH_UP = "ira_catch_up"
    EMPLOYER_CATCH_UP_60_63 = "employer_catch_up_60_63"


@dataclass(frozen=True)
class ContributionCostOfLiving:
    """Caller-supplied index levels, not annual percentage increases.

    ``q3_cpi_u[y]`` is the average CPI-U for July--September of year y,
    as required by 415(d). ``annual_cpi_u`` and ``annual_chained_cpi_u``
    use the 12 months ending August 31, per 1(f)(4),(6). The chained
    series must use the vintage specified by 1(f)(6)(A). For the IRA's
    pre-2016 base, 1(f)(3)(B) splices the series using both 2016 levels.
    """

    q3_cpi_u: Mapping[int, Decimal | float | str]
    annual_cpi_u: Mapping[int, Decimal | float | str]
    annual_chained_cpi_u: Mapping[int, Decimal | float | str]


@dataclass(frozen=True)
class ContributionLimits:
    """Age-adjusted dollar ceilings, excluding compensation/AGI restrictions.

    Catch-ups are separate from basic ceilings. In particular, 414(v)(3)
    excludes employer catch-up contributions from the 415(c) additions cap.
    """

    year: int
    age_at_year_end: int
    elective_deferral: int
    employer_catch_up: int
    annual_additions: int
    ira: int
    ira_catch_up: int


_PARAMETERS = (
    Path(__file__).resolve().parents[3]
    / "data/external/income_resources/retirement_rules_v1/contributions"
    / "parameters.json"
)
LAST_PUBLISHED_CONTRIBUTION_YEAR = 2026


@lru_cache(maxsize=1)
def _parameters() -> dict:
    return json.loads(_PARAMETERS.read_text())


def _year(year: int) -> None:
    if type(year) is not int or not 1 <= year <= 9999:
        raise ContributionRuleError("year must be an integer from 1 to 9999")


def _kind(kind: ContributionLimit | str) -> ContributionLimit:
    try:
        return ContributionLimit(kind)
    except (ValueError, TypeError) as exc:
        raise ContributionRuleError("unsupported contribution limit") from exc


def _level(values: Mapping, year: int, label: str) -> Decimal:
    if not isinstance(values, Mapping):
        raise ContributionRuleError(f"{label} levels must be a mapping")
    try:
        raw = values[year]
        if isinstance(raw, bool):
            raise ValueError
        result = Decimal(str(raw))
    except (KeyError, InvalidOperation, ValueError, TypeError) as exc:
        raise ContributionRuleError(
            f"missing or invalid {label} level for {year}"
        ) from exc
    if not result.is_finite() or result <= 0:
        raise ContributionRuleError(f"{label} levels must be positive/finite")
    return result


def _ratio(year: int, base: dict, path: ContributionCostOfLiving) -> Fraction:
    """Use exact fractions so division cannot move a rounding boundary."""
    base_year = base["base_year"]
    if base["index"] == "q3_cpi_u":
        denominator = Fraction(_level(path.q3_cpi_u, base_year, "Q3 CPI-U"))
        numerator = Fraction(_level(path.q3_cpi_u, year - 1, "Q3 CPI-U"))
    else:
        numerator = Fraction(
            _level(path.annual_chained_cpi_u, year - 1, "annual C-CPI-U")
        )
        if base_year > 2016:
            denominator = Fraction(
                _level(path.annual_chained_cpi_u, base_year, "annual C-CPI-U")
            )
        else:
            denominator = (
                Fraction(_level(path.annual_cpi_u, base_year, "annual CPI-U"))
                * Fraction(
                    _level(path.annual_chained_cpi_u, 2016, "annual C-CPI-U")
                )
                / Fraction(_level(path.annual_cpi_u, 2016, "annual CPI-U"))
            )
    return max(Fraction(1), numerator / denominator)


def _indexed_amount(
    year: int, base: dict, path: ContributionCostOfLiving
) -> int:
    amount = base["amount"]
    unit = base["rounding_unit"]
    increase = amount * (_ratio(year, base, path) - 1)
    return int(amount + (increase // unit) * unit)


def contribution_limit(
    year: int,
    kind: ContributionLimit | str,
    *,
    cost_of_living: ContributionCostOfLiving | None = None,
) -> int:
    """Return a published ceiling or project from its unrounded statutory base.

    Published figures take precedence. Beyond 2026, provide the relevant
    statutory base, the 2025 index and the target-year index. The 2025 index
    and bases must reproduce the 2026 published ceiling after rounding;
    inconsistent historical paths raise. Section 415(d) projections also
    require every index level from 2026 through year-1 to preserve ceilings
    already reached during deflation (Notice 2009-94, p. 1). Section 219 IRA
    projections instead use the section 1(f)(3) ratio for the target year.
    Pre-2025 enhanced catch-ups and gaps in the earlier table are refused.
    """
    _year(year)
    kind = _kind(kind)
    params = _parameters()
    published = params["published_limits"]
    if str(year) in published and kind.value in published[str(year)]:
        return published[str(year)][kind.value]
    if year <= LAST_PUBLISHED_CONTRIBUTION_YEAR:
        raise ContributionRuleError(
            f"no published {kind.value} ceiling covered for {year}"
        )
    if not isinstance(cost_of_living, ContributionCostOfLiving):
        raise ContributionRuleError("unpublished year requires an index path")
    base = params["projection_bases"][kind.value]
    ceiling = published[str(LAST_PUBLISHED_CONTRIBUTION_YEAR)][kind.value]
    if (
        _indexed_amount(LAST_PUBLISHED_CONTRIBUTION_YEAR, base, cost_of_living)
        != ceiling
    ):
        raise ContributionRuleError(
            "index bases and 2025 level contradict the published 2026 ceiling"
        )
    projected_years = range(LAST_PUBLISHED_CONTRIBUTION_YEAR + 1, year + 1)
    if base["index"] == "section_1f":
        projected_years = (year,)
        ceiling = base["amount"]
    for projected_year in projected_years:
        ceiling = max(
            ceiling, _indexed_amount(projected_year, base, cost_of_living)
        )
    return ceiling


def contribution_limits(
    year: int,
    age_at_year_end: int,
    *,
    cost_of_living: ContributionCostOfLiving | None = None,
) -> ContributionLimits:
    """Return ordinary employer-plan and IRA ceilings for an age/year.

    The supported age domain is 0--120 inclusive. The function does not
    establish eligibility to contribute, deductibility or an employer's
    decision to offer catch-ups. 402(g) here covers ordinary employer plans;
    SIMPLE plans have their separate statutory limits and are not covered.
    """
    _year(year)
    if type(age_at_year_end) is not int or not 0 <= age_at_year_end <= 120:
        raise ContributionRuleError("age at year end must be 0--120")

    def limit(kind: ContributionLimit) -> int:
        return contribution_limit(year, kind, cost_of_living=cost_of_living)

    catch_up_kind = ContributionLimit.EMPLOYER_CATCH_UP
    if year >= 2025 and 60 <= age_at_year_end <= 63:
        catch_up_kind = ContributionLimit.EMPLOYER_CATCH_UP_60_63
    # Validate every underlying ceiling even when age disallows a catch-up.
    employer_catch_up = limit(catch_up_kind)
    ira_catch_up = limit(ContributionLimit.IRA_CATCH_UP)
    return ContributionLimits(
        year=year,
        age_at_year_end=age_at_year_end,
        elective_deferral=limit(ContributionLimit.ELECTIVE_DEFERRAL),
        employer_catch_up=employer_catch_up if age_at_year_end >= 50 else 0,
        annual_additions=limit(ContributionLimit.ANNUAL_ADDITIONS),
        ira=limit(ContributionLimit.IRA),
        ira_catch_up=ira_catch_up if age_at_year_end >= 50 else 0,
    )
