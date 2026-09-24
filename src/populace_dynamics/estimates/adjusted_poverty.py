"""Adjusted family income and poverty status under a uniform benefit cut.

DynaSim scorecard exercise 2 compares the change in the *adjusted* poverty
rate at age 67 when all Social Security benefits are cut by 13 percent
(Butrica and Uccello 2004, *How Will Boomers Fare at Retirement?*, the
methods section, printed pages 19-24).  This module is Track U work item
U6 of ``critical-path-uniform-cut-20260923.md``: the income concept, the
asset annuity, the threshold assignment, the cut and the SSI response.
It is a **Python income concept (not Axiom)**: nothing here is an Axiom
encoding or a statutory oracle.

Income concept (plan section 7; each choice is a field of
:class:`AdjustedPovertySpec` whose default is the plan's proposed
primary, and :func:`pending_decisions` lists them):

* **Money income** (F3). ``family_unit``: PSID ``TOTAL FAMILY INCOME`` of
  the member's family unit (FU), the sum of head and wife taxable and
  transfer income, OFUM taxable and transfer income and head, wife and
  OFUM Social Security.  ``head_wife`` (row U4): head and wife taxable and
  transfer income and head and wife Social Security, with size = the
  member plus a co-resident wife/partner; OFUM members keep the FU basis.
* **Asset income** (F4).  ``replace``: the reported asset income of the
  unit (head and wife rent, dividends, interest, trusts/royalties and the
  asset part of business income; the OFUM asset total under the FU basis)
  is removed and the annuity added.  ``keep`` (row U5): the annuity is
  added and reported asset income kept, and nothing below is removed.
  Under ``replace`` two more items go (specification section 4):
  ``retirement_account_income_rule="remove_head"`` (F4a) removes the
  head's income from annuities and IRAs (``HEAD ANNUITIES``, "Head's
  Income from Annuities and IRAs" in the 2005-2011 codebooks; ``HEAD
  ANNUITIES`` plus ``HEAD IRAS`` in 2013), because WEALTH1 holds the
  balances that produce it (W22, "private annuities or IRAs") and they
  are annuitized; ``keep`` leaves it in income.  The wife's and the
  OFUMs' combined retirement items stay in every wave.
  ``farm_asset_share`` (F4b, 0.5) imputes the asset part of farm income
  by the PSID's business convention: that share of positive farm income,
  and the whole of a farm loss when the share is positive, is removed;
  0 keeps farm income whole.
* **Annuity** (F5-F9).  ``annuitized_share`` (0.8) times the FU's
  imputed wealth excluding home equity (WEALTH1), floored at zero (F9),
  divided by the price of a real, level annuity of 1 per year:
  annuity-immediate (payments at the end of each year the annuitant
  survives) at ``real_interest_rate`` (3 percent: the real return on
  government bonds after 2001 that the Report assumes for DC and IRA
  accumulation, p. 22; the same paragraph subtracts 1 percentage point
  for administrative costs, so 2 percent is a reported sensitivity;
  neither is stated to be DYNASIM's annuity-pricing rate), no load, on
  the NCHS 2000 life tables by sex (``mortality_basis``; row U9 the SSA
  period life table for 2004).
  ``annuity_lives="fu_head_rule"`` (default, the referee's Q1 answer)
  prices the family's WEALTH1 on the lives of its main owners: a joint
  annuity on the family head and the head's co-resident legal spouse
  (code 20 or 90) that pays 1 while both live and ``survivor_share``
  (0.5) to the survivor, a single life on the head otherwise, so every
  member of a family unit gets the same annuity.  ``member_rule`` prices
  it on the member and a co-resident legal spouse (joint) or the member
  alone.  Under independent lives the joint price is
  ``s*a_x + s*a_y + (1-2s)*a_xy`` (``0.5*(a_x + a_y)`` at s = 0.5).
  Ages are the builder's income-year ages
  (:mod:`populace_dynamics.cohorts.age67`, ``annuitant_age_source``).
* **Threshold** (F10).  ``census_weighted_average_65plus``: the Census
  weighted-average poverty threshold of the income year for the unit's
  size, using the "65 years and over" column for sizes 1 and 2 (the
  plan quotes the Report: "We use the 65-and-over poverty threshold").
  Row U10: the detailed size-by-related-children matrix (65-and-over
  rows for sizes 1 and 2; PSID "# CHILDREN IN FU" stands in for related
  children).  Row
  U8: PSID's own ``CENSUS NEEDS STANDARD`` for the income year.  The
  Census thresholds are **not captured** in this repository yet (see
  :func:`load_poverty_thresholds`).
* **Cut** (F11).  Reform income subtracts ``cut_rate`` (0.13) times all
  Social Security of the unit; there is no behavioural response.
  ``cut_start_year`` (default ``None``: every observation is cut, the F11
  primary) is row U6's parameter: with a start year, an observation is
  cut only when the year its member turns 67 (birth year + 67) is at or
  after it, so with 2004 the 1936 birth year (67 in 2003, observed at 68
  under U1) is uncut.  The plan defines U6 on U1 with the scorecard's
  "from 2004", which has no source the builder could read (plan section
  10, decision 8); the start year is pending that ruling.
* **SSI response** (F13, pending Max, decision record d189).
  ``offset_existing_recipients`` (proposed primary): for each SSI unit
  with baseline SSI, SSI rises by the fall in countable Social Security
  income (after the $20 monthly general income exclusion), capped so SSI
  does not exceed the federal benefit rate (FBR); nobody newly enrols.
  ``none`` (row U2).  ``full_static_recomputation`` (row U3, an upper
  bound): the offset, plus every head/wife unit that the cut makes newly
  income-eligible and whose resource proxy passes the resource limit
  takes up SSI.
* **Poverty**: poor when income is below the threshold (Census
  convention); baseline and reform status per row.

SSI units, a builder approximation: the head and wife form one unit (a
couple unit when both receive SSI, else an individual unit) whose
countable Social Security includes the spouse's (deeming approximated by
full attribution, ``ssi_deeming``); all OFUMs together form one
individual unit (``ofum_ssi_unit``).  The ``full_static_recomputation``
income test counts head and wife transfer income other than SSI, TANF and
other welfare as unearned income, excludes asset income (interest and
dividends on countable resources are excluded from SSI income), treats
labor, farm and business-labor income as earned income, and uses
``max(0, WEALTH1 - vehicles)`` as the resource proxy; it treats a unit
with a wife present as a couple.  OFUMs are never newly enrolled.

Provenance guard: :func:`adjusted_incomes` refuses rows built from staged
PSID files (``rows.attrs["provenance_kind"] == "psid_files"``) unless the
caller passes ``data_provenance="registered_real"`` with the issue #42
registration pointer; it refuses ``registered_real`` without one, and
``registered_real`` on rows not built from recorded PSID files.  No
registration exists for exercise 2, so the real-data path is closed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from populace_dynamics.data import family_income

__all__ = [
    "ANNUITY_LIVES",
    "ASSET_INCOME_RULES",
    "CUT_START_YEAR_RULE",
    "FARM_LOSS_RULE",
    "RETIREMENT_ACCOUNT_INCOME_CONCEPTS",
    "RETIREMENT_ACCOUNT_INCOME_RULES",
    "DATA_PROVENANCES",
    "INCOME_UNITS",
    "INVENTED",
    "INVENTED_LIFE_TABLE",
    "MORTALITY_BASES",
    "NCHS_2000_PATH",
    "NCHS_2000_SHA256",
    "OUTPUT_LABELS",
    "REGISTERED_REAL",
    "SSI_PARAMETERS_PATH",
    "SSI_PARAMETERS_SHA256",
    "SSI_RULES",
    "THRESHOLDS_PATH",
    "THRESHOLDS_SHA256",
    "THRESHOLD_RULES",
    "THRESHOLD_ROW_KEYS",
    "AdjustedPovertyError",
    "AdjustedPovertySpec",
    "LifeTable",
    "PendingDecision",
    "PovertyThresholds",
    "SsiParameters",
    "ThresholdsNotCapturedError",
    "adjusted_incomes",
    "annuity_factor_joint",
    "annuity_factor_single",
    "countable_income",
    "cut_applies",
    "load_life_table",
    "load_nchs_2000_life_table",
    "load_poverty_thresholds",
    "load_ssa_period_2004_life_table",
    "load_ssi_parameters",
    "pending_decisions",
    "survival_curve",
    "threshold_for",
]

_ROOT = Path(__file__).resolve().parents[3]
_EXTERNAL = _ROOT / "data" / "external"

#: The committed NCHS 2000 life tables (Arias 2002, NVSR 51(3)).
NCHS_2000_PATH = _EXTERNAL / "nchs_life_tables_2000.json"
NCHS_2000_SHA256 = (
    "067ac331d26a56f5f6c120e361771be1c890e74c412b5561ca45c87302059142"
)
#: The SSI parameter capture (``scripts/capture_track_u_parameters.py``).
SSI_PARAMETERS_PATH = _EXTERNAL / "track_u_ssi_parameters.json"
SSI_PARAMETERS_SHA256 = (
    "79e641a10d95afba81c8d831852fb52ef0a801e7175e06df17e6cc7cc3e3c523"
)
SSI_SCHEMA_VERSION = "populace_dynamics.track_u_ssi_parameters.v1"
#: The Census poverty-threshold capture.  It does not exist yet: the Census
#: files have not been downloaded (the capture script parses them once
#: staged), so there is no pin and :func:`load_poverty_thresholds` refuses.
THRESHOLDS_PATH = _EXTERNAL / "census_poverty_thresholds_2004_2012.json"
THRESHOLDS_SHA256: str | None = None
THRESHOLDS_SCHEMA_VERSION = "populace_dynamics.census_poverty_thresholds.v1"

INVENTED = "invented"
REGISTERED_REAL = "registered_real"
#: The name an invented (test or dry-run) life table must carry.
INVENTED_LIFE_TABLE = "invented"
DATA_PROVENANCES = (INVENTED, REGISTERED_REAL)

#: The labels every Track U output carries (plan section 10, item 1).
OUTPUT_LABELS: tuple[str, ...] = (
    "PSID-realized outcomes (not a projection)",
    "Python income concept (not Axiom)",
    "mechanical incidence",
)

ASSET_INCOME_RULES: dict[str, str] = {
    "replace": (
        "remove reported asset income and add the annuity (F4 primary; "
        "the plan reads Report p. 24 as contrasting the annuity with the "
        "Census measure's "
        "interest and dividends)"
    ),
    "keep": "keep reported asset income and add the annuity (row U5)",
}
INCOME_UNITS: dict[str, str] = {
    "family_unit": (
        "PSID family unit: all FU money income and FU size (F3 primary)"
    ),
    "head_wife": (
        "head and wife income only, size = member plus a co-resident "
        "wife/partner; OFUM members keep the FU basis (row U4)"
    ),
}
ANNUITY_LIVES: dict[str, str] = {
    "fu_head_rule": (
        "joint-and-survivor on the FU head and the head's co-resident legal "
        "spouse (code 20 or 90) if present, else single life on the head: "
        "the family's wealth priced on its main owners (referee Q1)"
    ),
    "member_rule": (
        "joint-and-survivor on the member and a co-resident legal spouse "
        "if married, else single life on the member (F6 as the plan wrote "
        "it)"
    ),
}
RETIREMENT_ACCOUNT_INCOME_RULES: dict[str, str] = {
    "remove_head": (
        "under asset_income_rule 'replace', remove the head's income from "
        "annuities and IRAs (HEAD ANNUITIES; plus HEAD IRAS in 2013), whose "
        "balances WEALTH1 annuitizes (F4a, referee R3)"
    ),
    "keep": "keep the head's annuity and IRA income (u1-draft-3 behaviour)",
}
#: The head's annuity and IRA income items (``head_iras`` exists in the
#: 2013 family file only; earlier files fold IRA income into
#: ``head_annuities``, "Head's Income from Annuities and IRAs").
RETIREMENT_ACCOUNT_INCOME_CONCEPTS: tuple[str, ...] = (
    "head_annuities",
    "head_iras",
)
#: How a farm loss is treated under ``farm_asset_share`` (F4b).
FARM_LOSS_RULE = "removed_whole_when_share_positive"
#: The rule ``cut_start_year`` applies (row U6).
CUT_START_YEAR_RULE = "cut_when_birth_year_plus_67_at_or_after_start"
#: Income years whose family file carries ``head_iras``.
_HEAD_IRA_INCOME_YEARS: frozenset[int] = frozenset(
    wave - 1
    for wave in family_income.INCOME_WAVES
    if "head_iras" in family_income.income_variables(wave)
)
MORTALITY_BASES: dict[str, str] = {
    "nchs_2000": "NCHS United States Life Tables, 2000, by sex (F8)",
    "ssa_period_2004": (
        "SSA period life table for 2004 (2008 vintage; data/external/"
        "tr2008/ssa_2008_vintage.json) (row U9)"
    ),
}
THRESHOLD_RULES: dict[str, str] = {
    "census_weighted_average_65plus": (
        "Census weighted-average threshold of the income year by unit "
        "size; the 65-and-over column for sizes 1 and 2 (F10 primary)"
    ),
    "census_matrix_65plus": (
        "Census size-by-related-children matrix; householder 65-and-over "
        "rows for sizes 1 and 2; PSID '# CHILDREN IN FU' as related "
        "children (row U10)"
    ),
    "psid_census_needs_standard": (
        "PSID CENSUS NEEDS STANDARD for the income year (row U8)"
    ),
}
SSI_RULES: dict[str, str] = {
    "offset_existing_recipients": (
        "baseline SSI recipients: SSI rises by the fall in countable "
        "Social Security income, capped at the FBR; no new enrolment "
        "(F13 proposed primary; pending Max, d189)"
    ),
    "none": "no SSI response (row U2)",
    "full_static_recomputation": (
        "the offset plus take-up by every newly income- and "
        "resource-eligible head/wife unit (row U3: the largest SSI "
        "response of the three registered rules, not a bound on "
        "DYNASIM's simulation)"
    ),
}
SSI_DEEMING: dict[str, str] = {
    "spouse_social_security_counted": (
        "the head/wife unit's countable Social Security includes the "
        "spouse's (deeming approximated by full attribution)"
    ),
    "recipients_only": (
        "only the Social Security of the unit's SSI recipients counts"
    ),
}
OFUM_SSI_UNITS: dict[str, str] = {
    "single_individual": (
        "all OFUMs' SSI and Social Security form one individual unit"
    ),
}
ANNUITY_TIMINGS: dict[str, str] = {
    "immediate": "payments at the end of each year survived (F7 primary)",
    "due": "payments at the start of each year survived (sensitivity)",
}
NEGATIVE_WEALTH_RULES: dict[str, str] = {
    "annuity_floored_at_zero": (
        "negative WEALTH1 buys no annuity and is not subtracted (F9)"
    ),
}
TERMINAL_CLOSURES: dict[str, str] = {
    "table_end": (
        "survival ends with the table: NCHS 2000's open interval "
        "'100 years and over' (qx = 1) is treated as death within the "
        "year at 100; the SSA 2004 table ends at 119"
    ),
}

#: Threshold row keys (weighted averages and matrix rows).
THRESHOLD_ROW_KEYS: tuple[str, ...] = (
    "one_under_65",
    "one_65_plus",
    "two_under_65",
    "two_65_plus",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine_plus",
)
_SIZE_KEYS: dict[int, str] = {
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
}
#: The matrix's last children column is "Eight or more".
_MAX_CHILD_COLUMN = 8
_MONTHS = 12


class AdjustedPovertyError(ValueError):
    """The rows or the specification cannot yield the income concept."""


class ThresholdsNotCapturedError(FileNotFoundError):
    """The Census poverty thresholds have not been captured."""


def _choice(value: Any, allowed: Mapping[str, str], name: str) -> None:
    if value not in allowed:
        raise AdjustedPovertyError(
            f"{name}={value!r} is not one of {sorted(allowed)}"
        )


@dataclass(frozen=True)
class AdjustedPovertySpec:
    """Every income-concept choice; defaults are the plan's primary."""

    cut_rate: float = 0.13
    cut_start_year: int | None = None
    annuitized_share: float = 0.8
    real_interest_rate: float = 0.03
    annuity_timing: str = "immediate"
    annuity_load: float = 0.0
    survivor_share: float = 0.5
    mortality_basis: str = "nchs_2000"
    terminal_closure: str = "table_end"
    asset_income_rule: str = "replace"
    income_unit: str = "family_unit"
    retirement_account_income_rule: str = "remove_head"
    farm_asset_share: float = 0.5
    annuity_lives: str = "fu_head_rule"
    negative_wealth_rule: str = "annuity_floored_at_zero"
    threshold_rule: str = "census_weighted_average_65plus"
    ssi_rule: str = "offset_existing_recipients"
    ssi_deeming: str = "spouse_social_security_counted"
    ofum_ssi_unit: str = "single_individual"

    def __post_init__(self) -> None:
        for name, low, high in (
            ("cut_rate", 0.0, 1.0),
            ("annuitized_share", 0.0, 1.0),
            ("survivor_share", 0.0, 1.0),
            ("annuity_load", 0.0, 1.0),
            ("farm_asset_share", 0.0, 1.0),
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not (low <= float(value) <= high):
                raise AdjustedPovertyError(
                    f"{name} must lie in [{low}, {high}]"
                )
        rate = self.real_interest_rate
        if isinstance(rate, bool) or not (-0.5 < float(rate) < 1.0):
            raise AdjustedPovertyError("real_interest_rate out of range")
        start = self.cut_start_year
        if start is not None and (
            isinstance(start, bool)
            or not isinstance(start, int)
            or not 1990 <= start <= 2030
        ):
            raise AdjustedPovertyError(
                "cut_start_year must be None or an integer year in "
                "1990-2030"
            )
        _choice(self.annuity_timing, ANNUITY_TIMINGS, "annuity_timing")
        _choice(self.mortality_basis, MORTALITY_BASES, "mortality_basis")
        _choice(self.terminal_closure, TERMINAL_CLOSURES, "terminal_closure")
        _choice(
            self.asset_income_rule, ASSET_INCOME_RULES, "asset_income_rule"
        )
        _choice(self.income_unit, INCOME_UNITS, "income_unit")
        _choice(
            self.retirement_account_income_rule,
            RETIREMENT_ACCOUNT_INCOME_RULES,
            "retirement_account_income_rule",
        )
        _choice(self.annuity_lives, ANNUITY_LIVES, "annuity_lives")
        _choice(
            self.negative_wealth_rule,
            NEGATIVE_WEALTH_RULES,
            "negative_wealth_rule",
        )
        _choice(self.threshold_rule, THRESHOLD_RULES, "threshold_rule")
        _choice(self.ssi_rule, SSI_RULES, "ssi_rule")
        _choice(self.ssi_deeming, SSI_DEEMING, "ssi_deeming")
        _choice(self.ofum_ssi_unit, OFUM_SSI_UNITS, "ofum_ssi_unit")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PendingDecision:
    """One open choice: its default, alternatives, basis and owner."""

    field: str
    default: Any
    alternatives: tuple[Any, ...]
    default_basis: str
    awaiting: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "default": self.default,
            "alternatives": list(self.alternatives),
            "default_basis": self.default_basis,
            "awaiting": self.awaiting,
        }


_PLAN = "plan proposal (critical-path-uniform-cut-20260923.md section 7)"
_BUILDER = "builder choice; the plan is silent"
_REFEREE = "referee (boomers2004-referee-20260924.md)"
_MAX_D189 = "Max (cos decision d189, open)"
_FREEZE = "U1 specification freeze (Max's ratification by merge)"


def pending_decisions() -> tuple[PendingDecision, ...]:
    """Every open choice of :class:`AdjustedPovertySpec`, with its default.

    None of these is ratified.  ``awaiting`` names who decides.
    """

    spec = AdjustedPovertySpec()
    return (
        PendingDecision(
            "ssi_rule",
            spec.ssi_rule,
            ("none", "full_static_recomputation"),
            f"{_PLAN} F13; plan section 10 decision 5",
            _MAX_D189,
        ),
        PendingDecision(
            "cut_rate",
            spec.cut_rate,
            (),
            "Report p. 22 (OCACT estimates 'that benefits would need to be "
            "reduced immediately by 13 percent'); the scenario's start "
            "year and coverage are not in the methods (plan section 10 "
            "decisions 2 and 8)",
            _FREEZE,
        ),
        PendingDecision(
            "cut_start_year",
            spec.cut_start_year,
            (2004,),
            "plan F11: the primary cuts every observation (None); row U6 "
            "(on U1) leaves an observation uncut when its member turned 67 "
            "before the start year, 2004 being the scorecard's 'from 2004', "
            "which has no source the builder could read; under U0 every "
            "age-67 year is 2004 or later, so only U1's 1936 birth year "
            "moves",
            "Max (plan section 10 decision 8: the scenario's start year; "
            "not yet on a decision card)",
        ),
        PendingDecision(
            "income_unit",
            spec.income_unit,
            ("head_wife",),
            f"{_PLAN} F3 (the plan cites Report p. 19: co-resident income "
            "counts); U4",
            _FREEZE,
        ),
        PendingDecision(
            "asset_income_rule",
            spec.asset_income_rule,
            ("keep",),
            f"{_PLAN} F4; U5",
            _FREEZE,
        ),
        PendingDecision(
            "retirement_account_income_rule",
            spec.retirement_account_income_rule,
            ("keep",),
            f"{_REFEREE} R3: HEAD ANNUITIES is 'Head's Income from "
            "Annuities and IRAs' in the 2005-2011 codebooks (HEAD "
            "ANNUITIES plus HEAD IRAS in 2013); WEALTH1 includes the "
            "balances ('private annuities or IRAs', W22) and annuitizes "
            "them, and the Report contrasts its annuity with Census "
            "income, which counts withdrawals (p. 24); applies only under "
            "asset_income_rule 'replace'",
            _FREEZE,
        ),
        PendingDecision(
            "farm_asset_share",
            spec.farm_asset_share,
            (0.0,),
            f"{_REFEREE} Q2/R4: the Report's financial assets include farm "
            "equity (p. 22); the PSID reports one farm item with labor and "
            "asset portions and splits a working owner's business income "
            "equally, coding a loss wholly as asset income (codebook text "
            "for ER52216); the same convention imputes the asset part of "
            "farm income (0 keeps farm income whole, the u1-draft-3 "
            "behaviour); applies only under asset_income_rule 'replace'",
            _FREEZE,
        ),
        PendingDecision(
            "annuitized_share",
            spec.annuitized_share,
            (),
            "plan section 2, citing Report p. 24 (80 percent of financial "
            "assets)",
            _FREEZE,
        ),
        PendingDecision(
            "real_interest_rate",
            spec.real_interest_rate,
            (0.02,),
            f"{_PLAN} F7: Report p. 22 assumes a 3.0 percent real return "
            "on government bonds after 2001 for DC and IRA accumulation, "
            "and the same paragraph subtracts 1 percentage point from "
            "stock and bond returns for administrative costs (net 2 "
            "percent); neither is stated to be DYNASIM's annuity-pricing "
            f"rate; 0.02 is a reported, unscored sensitivity ({_REFEREE} "
            "R6)",
            _FREEZE,
        ),
        PendingDecision(
            "annuity_timing",
            spec.annuity_timing,
            ("due",),
            f"{_PLAN} F7 (annuity-immediate; a builder convention)",
            _FREEZE,
        ),
        PendingDecision(
            "annuity_load",
            spec.annuity_load,
            (),
            f"{_PLAN} F7 (no load)",
            _FREEZE,
        ),
        PendingDecision(
            "survivor_share",
            spec.survivor_share,
            (),
            "plan section 2, citing Report p. 24 fn. 10 (married couples: "
            "50 percent survivor "
            "annuity); reduction on either death is a builder reading",
            _FREEZE,
        ),
        PendingDecision(
            "mortality_basis",
            spec.mortality_basis,
            ("ssa_period_2004",),
            f"{_PLAN} F8; U9",
            _FREEZE,
        ),
        PendingDecision(
            "terminal_closure",
            spec.terminal_closure,
            (),
            f"{_BUILDER} (survival beyond the table's last age)",
            _FREEZE,
        ),
        PendingDecision(
            "annuity_lives",
            spec.annuity_lives,
            ("member_rule",),
            f"{_REFEREE} Q1/R7: WEALTH1 is the family unit's wealth, "
            "which the head and the head's spouse mostly own, so it is "
            "priced on their lives (joint on the head and a co-resident "
            "legal spouse, code 20 or 90, else the head); the rules "
            "coincide for heads and legal wives and differ for OFUMs and "
            "cohabiting partners; member_rule is plan F6 as written",
            _FREEZE,
        ),
        PendingDecision(
            "negative_wealth_rule",
            spec.negative_wealth_rule,
            (),
            f"{_PLAN} F9 (builder choice flagged by the plan)",
            _FREEZE,
        ),
        PendingDecision(
            "threshold_rule",
            spec.threshold_rule,
            ("census_matrix_65plus", "psid_census_needs_standard"),
            f"{_PLAN} F10 (Report p. 24 wording as the plan quotes it); "
            "U10, U8",
            _FREEZE,
        ),
        PendingDecision(
            "ssi_deeming",
            spec.ssi_deeming,
            ("recipients_only",),
            f"{_BUILDER} (PSID reports SSI and Social Security by head, "
            "wife and OFUM total, not by SSI unit); endorsed as the "
            f"default by the {_REFEREE} (Q3): under 20 CFR 416.1163 "
            "nothing is deemed when the ineligible spouse's income after "
            "allocations is at most the couple-minus-individual FBR, so "
            "full attribution can only overstate the offset; "
            "recipients_only errs the other way, and the two bracket the "
            "rule",
            _FREEZE,
        ),
        PendingDecision(
            "ofum_ssi_unit",
            spec.ofum_ssi_unit,
            (),
            f"{_BUILDER} (PSID reports one OFUM total)",
            _FREEZE,
        ),
    )


# =========================================================================
# Life tables and annuity factors
# =========================================================================
@dataclass(frozen=True)
class LifeTable:
    """One-year death probabilities by sex from age 0 to the last age.

    ``qx[sex][age]`` for ``sex`` in ``("male", "female")``.  Survival past
    the last age is zero (``terminal_closure="table_end"``).
    """

    name: str
    qx: Mapping[str, tuple[float, ...]]
    source: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if set(self.qx) != {"male", "female"}:
            raise AdjustedPovertyError("a life table needs male and female")
        lengths = {len(values) for values in self.qx.values()}
        if len(lengths) != 1:
            raise AdjustedPovertyError("sexes cover different ages")
        for values in self.qx.values():
            if not all(0.0 <= float(q) <= 1.0 for q in values):
                raise AdjustedPovertyError("qx must lie in [0, 1]")

    @property
    def last_age(self) -> int:
        return len(self.qx["male"]) - 1


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_nchs_2000_life_table(
    path: Path = NCHS_2000_PATH, *, expected_sha256: str = NCHS_2000_SHA256
) -> LifeTable:
    """The committed NCHS 2000 life tables, refused unless hash-pinned."""

    observed = _sha256(path)
    if observed != expected_sha256:
        raise AdjustedPovertyError(
            f"{path} sha256 {observed} != pinned {expected_sha256}"
        )
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    qx: dict[str, tuple[float, ...]] = {}
    for sex in ("male", "female"):
        rows = data["tables"][sex]
        ages = [int(row["age"]) for row in rows]
        if ages != list(range(len(rows))):
            raise AdjustedPovertyError(f"NCHS {sex} ages are not 0..n")
        qx[sex] = tuple(float(row["qx"]) for row in rows)
    return LifeTable(
        name="nchs_2000",
        qx=qx,
        source={
            "path": (
                str(Path(path).relative_to(_ROOT))
                if Path(path).is_relative_to(_ROOT)
                else str(path)
            ),
            "sha256": observed,
            "citation": data["report"]["nvsr_citation"],
            "terminal_age": int(data["terminal_age"]),
        },
    )


def load_ssa_period_2004_life_table() -> LifeTable:
    """The SSA period life table for 2004 (row U9), hash-verified.

    Read through :func:`populace_dynamics.data.tr2008.period_life_table_2004`,
    which verifies the committed TR2008-vintage files' SHA-256.
    """

    from populace_dynamics.data import tr2008

    tr2008.verify_files()
    qx = {
        sex: tuple(row.qx for row in tr2008.period_life_table_2004(sex))
        for sex in ("male", "female")
    }
    return LifeTable(
        name="ssa_period_2004",
        qx=qx,
        source={
            "reader": "populace_dynamics.data.tr2008.period_life_table_2004",
            "file": "data/external/tr2008/ssa_2008_vintage.json",
            "sha256": tr2008.FILE_SHA256["ssa_2008_vintage.json"],
        },
    )


def load_life_table(basis: str) -> LifeTable:
    """The life table named by ``AdjustedPovertySpec.mortality_basis``."""

    _choice(basis, MORTALITY_BASES, "mortality_basis")
    if basis == "nchs_2000":
        return load_nchs_2000_life_table()
    return load_ssa_period_2004_life_table()


def survival_curve(table: LifeTable, sex: str, age: int) -> np.ndarray:
    """``t_p_x`` for ``t = 0 .. last_age - age + 1`` (the last is 0).

    ``t_p_x = prod_{k<t} (1 - q_{x+k})``; survival past the table's last
    age is zero because the curve stops there.
    """

    if sex not in table.qx:
        raise AdjustedPovertyError(f"sex must be male or female, not {sex!r}")
    age = int(age)
    if not 0 <= age <= table.last_age:
        raise AdjustedPovertyError(
            f"age {age} is outside the table's 0-{table.last_age}"
        )
    q = np.asarray(table.qx[sex][age:], dtype=np.float64)
    survival = np.concatenate([[1.0], np.cumprod(1.0 - q)])
    survival[-1] = 0.0
    return survival


def _annuity_from_payments(
    payments: np.ndarray, rate: float, timing: str, load: float
) -> float:
    """Price of a payment stream indexed by ``t = 0..n-1`` survival."""

    t = np.arange(len(payments), dtype=np.float64)
    v = (1.0 + float(rate)) ** -t
    if timing == "immediate":
        value = float(np.sum(v[1:] * payments[1:]))
    else:
        value = float(np.sum(v[:-1] * payments[:-1]))
    return value * (1.0 + float(load))


def annuity_factor_single(
    table: LifeTable,
    sex: str,
    age: int,
    *,
    rate: float = 0.03,
    timing: str = "immediate",
    load: float = 0.0,
) -> float:
    """Price of a level real life annuity of 1 per year.

    ``immediate``: ``sum_{t>=1} v^t t_p_x``; ``due``:
    ``sum_{t>=0} v^t t_p_x``; ``v = 1/(1+rate)``; times ``1 + load``.
    """

    _choice(timing, ANNUITY_TIMINGS, "timing")
    return _annuity_from_payments(
        survival_curve(table, sex, age), rate, timing, load
    )


def annuity_factor_joint(
    table: LifeTable,
    sex_1: str,
    age_1: int,
    sex_2: str,
    age_2: int,
    *,
    survivor_share: float = 0.5,
    rate: float = 0.03,
    timing: str = "immediate",
    load: float = 0.0,
) -> float:
    """Price of a joint annuity: 1 while both live, ``s`` to the survivor.

    With independent lives the expected payment at ``t`` is
    ``s*t_p_x + s*t_p_y + (1-2s)*t_p_x*t_p_y``.
    """

    _choice(timing, ANNUITY_TIMINGS, "timing")
    first = survival_curve(table, sex_1, age_1)
    second = survival_curve(table, sex_2, age_2)
    n = max(len(first), len(second))
    first = np.pad(first, (0, n - len(first)))
    second = np.pad(second, (0, n - len(second)))
    s = float(survivor_share)
    payments = s * first + s * second + (1.0 - 2.0 * s) * first * second
    return _annuity_from_payments(payments, rate, timing, load)


# =========================================================================
# Poverty thresholds
# =========================================================================
@dataclass(frozen=True)
class PovertyThresholds:
    """Census poverty thresholds by income year.

    ``weighted_average[year][row]`` for each row key in
    :data:`THRESHOLD_ROW_KEYS`; ``matrix[year][row][children]`` with
    ``children`` 0-8 (8 = "Eight or more").  ``provenance`` records the
    source; invented tables must say so.
    """

    weighted_average: Mapping[int, Mapping[str, float]]
    matrix: Mapping[int, Mapping[str, Mapping[int, float]]]
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        for year, rows in self.weighted_average.items():
            missing = set(THRESHOLD_ROW_KEYS) - set(rows)
            if missing:
                raise AdjustedPovertyError(
                    f"{year} weighted averages lack rows {sorted(missing)}"
                )
            if any(float(value) <= 0 for value in rows.values()):
                raise AdjustedPovertyError("thresholds must be positive")
        for year, rows in self.matrix.items():
            missing = set(THRESHOLD_ROW_KEYS) - set(rows)
            if missing:
                raise AdjustedPovertyError(
                    f"{year} matrix lacks rows {sorted(missing)}"
                )
        if not self.provenance.get("kind"):
            raise AdjustedPovertyError(
                "thresholds need a provenance kind (captured or invented)"
            )


def load_poverty_thresholds(
    path: Path = THRESHOLDS_PATH,
    *,
    expected_sha256: str | None = THRESHOLDS_SHA256,
) -> PovertyThresholds:
    """The committed Census threshold capture, refused unless pinned.

    No capture exists yet.  The Census tables for 2004-2012 are
    spreadsheets on www2.census.gov (``thresh04.xlsx`` ... ``thresh12.xlsx``
    under ``programs-surveys/cps/tables/time-series/historical-poverty-
    thresholds/``, as listed on the Census historical thresholds page);
    they have not been downloaded.  Once staged locally,
    ``scripts/capture_track_u_parameters.py --census-dir DIR`` writes the
    capture, and the pin here must be set to its SHA-256.
    """

    if expected_sha256 is None or not Path(path).is_file():
        raise ThresholdsNotCapturedError(
            f"Census poverty thresholds are not captured: {path} "
            f"{'is missing' if not Path(path).is_file() else 'has no pin'}. "
            "Stage the Census threshold spreadsheets for income years "
            "2004-2012 (thresh04.xlsx ... thresh12.xlsx from www2.census.gov "
            "programs-surveys/cps/tables/time-series/historical-poverty-"
            "thresholds/) and run scripts/capture_track_u_parameters.py "
            "--census-dir <dir>, then pin THRESHOLDS_SHA256."
        )
    observed = _sha256(path)
    if observed != expected_sha256:
        raise AdjustedPovertyError(
            f"{path} sha256 {observed} != pinned {expected_sha256}"
        )
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != THRESHOLDS_SCHEMA_VERSION:
        raise AdjustedPovertyError(f"unexpected threshold schema in {path}")
    return PovertyThresholds(
        weighted_average={
            int(year): {row: float(v) for row, v in rows.items()}
            for year, rows in data["weighted_average"].items()
        },
        matrix={
            int(year): {
                row: {int(k): float(v) for k, v in cells.items()}
                for row, cells in rows.items()
            }
            for year, rows in data["matrix"].items()
        },
        provenance={"kind": "census_capture", "sha256": observed},
    )


def threshold_for(
    thresholds: PovertyThresholds | None,
    year: int,
    size: int,
    n_children: int,
    rule: str,
    *,
    needs_standard: float | None = None,
) -> tuple[float, str]:
    """The threshold for one unit, and the cell it came from."""

    _choice(rule, THRESHOLD_RULES, "threshold_rule")
    size = int(size)
    if size < 1:
        raise AdjustedPovertyError(f"unit size {size} < 1")
    if rule == "psid_census_needs_standard":
        if needs_standard is None or not float(needs_standard) > 0:
            raise AdjustedPovertyError("needs standard missing or <= 0")
        return float(needs_standard), "psid_census_needs_standard"
    if thresholds is None:
        raise ThresholdsNotCapturedError(
            f"threshold rule {rule} needs Census thresholds"
        )
    year = int(year)
    if size == 1:
        row = "one_65_plus"
    elif size == 2:
        row = "two_65_plus"
    else:
        row = _SIZE_KEYS.get(size, "nine_plus")
    if rule == "census_weighted_average_65plus":
        if year not in thresholds.weighted_average:
            raise AdjustedPovertyError(f"no weighted averages for {year}")
        return float(thresholds.weighted_average[year][row]), row
    if year not in thresholds.matrix:
        raise AdjustedPovertyError(f"no threshold matrix for {year}")
    children = int(n_children)
    if children < 0:
        raise AdjustedPovertyError("negative number of children")
    column = min(children, size - 1, _MAX_CHILD_COLUMN)
    cells = thresholds.matrix[year][row]
    if column not in cells:
        raise AdjustedPovertyError(
            f"{year} matrix row {row} has no column for {column} children"
        )
    return float(cells[column]), f"{row}:{column}"


# =========================================================================
# SSI parameters and countable income
# =========================================================================
@dataclass(frozen=True)
class SsiParameters:
    """Federal SSI parameters by income year (monthly dollars)."""

    fbr_individual_monthly: Mapping[int, float]
    fbr_couple_monthly: Mapping[int, float]
    general_income_exclusion_monthly: float
    earned_income_exclusion_monthly: float
    earned_income_share_excluded: float
    resource_limit_individual: float
    resource_limit_couple: float
    provenance: Mapping[str, Any]

    def fbr_annual(self, year: int, couple: bool) -> float:
        rates = (
            self.fbr_couple_monthly if couple else self.fbr_individual_monthly
        )
        if int(year) not in rates:
            raise AdjustedPovertyError(f"no FBR for {year}")
        return _MONTHS * float(rates[int(year)])

    def resource_limit(self, couple: bool) -> float:
        return float(
            self.resource_limit_couple
            if couple
            else self.resource_limit_individual
        )


def load_ssi_parameters(
    path: Path = SSI_PARAMETERS_PATH,
    *,
    expected_sha256: str = SSI_PARAMETERS_SHA256,
) -> SsiParameters:
    """The committed SSI parameter capture, refused unless hash-pinned."""

    observed = _sha256(path)
    if observed != expected_sha256:
        raise AdjustedPovertyError(
            f"{path} sha256 {observed} != pinned {expected_sha256}; "
            "regenerate it with scripts/capture_track_u_parameters.py "
            "and re-pin"
        )
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != SSI_SCHEMA_VERSION:
        raise AdjustedPovertyError(f"unexpected SSI schema in {path}")
    fbr = data["federal_benefit_rate_monthly"]
    return SsiParameters(
        fbr_individual_monthly={
            int(y): float(v) for y, v in fbr["individual"].items()
        },
        fbr_couple_monthly={
            int(y): float(v) for y, v in fbr["couple"].items()
        },
        general_income_exclusion_monthly=float(
            data["general_income_exclusion_monthly"]
        ),
        earned_income_exclusion_monthly=float(
            data["earned_income_exclusion_monthly"]
        ),
        earned_income_share_excluded=float(
            data["earned_income_share_excluded"]
        ),
        resource_limit_individual=float(data["resource_limit"]["individual"]),
        resource_limit_couple=float(data["resource_limit"]["couple"]),
        provenance={"kind": "policyengine_us_capture", "sha256": observed},
    )


def countable_income(
    unearned: float, earned: float, ssi: SsiParameters
) -> float:
    """Annual SSI countable income (20 CFR 416.1112 and 416.1124 order).

    The $20 monthly general exclusion applies to unearned income first and
    any remainder to earned income; then the $65 monthly earned exclusion
    and one half of the rest of earned income are excluded.  Annual
    amounts are twelve times the monthly exclusions.
    """

    general = _MONTHS * ssi.general_income_exclusion_monthly
    earned_flat = _MONTHS * ssi.earned_income_exclusion_monthly
    unearned = max(0.0, float(unearned))
    earned = max(0.0, float(earned))
    countable_unearned = max(0.0, unearned - general)
    leftover = max(0.0, general - unearned)
    countable_earned = max(0.0, earned - leftover - earned_flat) * (
        1.0 - ssi.earned_income_share_excluded
    )
    return countable_unearned + countable_earned


def _countable_ss_fall(ss: float, cut_rate: float, general: float) -> float:
    before = max(0.0, ss - general)
    after = max(0.0, (1.0 - cut_rate) * ss - general)
    return before - after


# =========================================================================
# The income concept
# =========================================================================
_HW_ASSETS = tuple(
    c for c in family_income.ASSET_INCOME_CONCEPTS if c != "ofum_asset"
)
REQUIRED_COLUMNS: tuple[str, ...] = (
    "observation_id",
    "family_unit_id",
    "income_year",
    "birth_year",
    "member_role",
    "member_age",
    "member_sex",
    "member_married_coresident",
    "spouse_age",
    "spouse_sex",
    "fu_head_age",
    "fu_head_sex",
    "fu_head_spouse_present",
    "fu_head_spouse_age",
    "fu_head_spouse_sex",
    "wife_present",
    "fu_size",
    "n_children",
    "total_family_income",
    "hw_taxable",
    "hw_transfer",
    *family_income.ASSET_INCOME_CONCEPTS,
    *family_income.SOCIAL_SECURITY_CONCEPTS,
    *family_income.SSI_CONCEPTS,
    *family_income.HW_EARNED_CONCEPTS,
    "head_tanf",
    "wife_tanf",
    "head_other_welfare",
    "wife_other_welfare",
    "head_annuities",
    "census_needs_standard",
    "wealth1",
    "vehicles",
)
MEMBER_ROLES = ("head", "wife", "ofum")


def _validate_provenance(
    rows: pd.DataFrame, data_provenance: str, registration_pointer: Any
) -> None:
    if data_provenance not in DATA_PROVENANCES:
        raise AdjustedPovertyError(
            f"data_provenance must be one of {DATA_PROVENANCES}"
        )
    kind = rows.attrs.get("provenance_kind")
    if data_provenance == REGISTERED_REAL:
        if not isinstance(registration_pointer, str) or not (
            registration_pointer.strip()
        ):
            raise AdjustedPovertyError(
                "registered_real requires the issue #42 registration "
                "pointer, which must exist before any real-data run"
            )
        # As Track A's opening: a registered run needs rows built from
        # recorded PSID files, so invented or caller-built rows cannot
        # leave with a real-data label.
        if kind != "psid_files":
            raise AdjustedPovertyError(
                f"data_provenance 'registered_real' contradicts the rows' "
                f"provenance {kind!r}: a registered run needs rows built "
                "from recorded PSID files (age67.income_rows on inputs "
                "sealed by load_age67_inputs)"
            )
    elif kind == "psid_files":
        raise AdjustedPovertyError(
            "rows built from staged PSID files cannot be processed as "
            "invented data; a real-data run needs the #42 registration"
        )


def _head_retirement_account_income(rows: pd.DataFrame) -> np.ndarray:
    """The head's annuity and IRA income per row (F4a).

    ``head_annuities`` in every wave plus ``head_iras`` where the wave's
    family file carries it (2013, income year 2012); a row of such a year
    without it, or a row of another year with it nonzero, is refused.
    """

    total = rows["head_annuities"].to_numpy(dtype=np.float64)
    years = rows["income_year"].astype("int64").to_numpy()
    with_iras = np.isin(years, sorted(_HEAD_IRA_INCOME_YEARS))
    if "head_iras" in rows.columns:
        iras = pd.to_numeric(rows["head_iras"], errors="raise")
        missing = iras.isna().to_numpy()
        if (missing & with_iras).any():
            raise AdjustedPovertyError(
                "head_iras missing for an income year whose family file "
                "carries HEAD IRAS"
            )
        iras = iras.fillna(0.0).to_numpy(dtype=np.float64)
        if ((iras != 0) & ~with_iras).any():
            raise AdjustedPovertyError(
                "head_iras nonzero for an income year whose family file "
                "has no HEAD IRAS item"
            )
        total = total + iras
    elif with_iras.any():
        raise AdjustedPovertyError(
            "rows of income year 2012 need head_iras (HEAD IRAS-2012)"
        )
    return total


def _farm_asset_income(
    rows: pd.DataFrame, spec: AdjustedPovertySpec
) -> np.ndarray:
    """The imputed asset part of head and wife farm income (F4b).

    ``farm_asset_share`` of positive farm income; the whole of a farm
    loss when the share is positive (the PSID codes a business loss wholly
    in the asset part, codebook text for ER52216); nothing at share 0.
    """

    farm = rows["head_farm"].to_numpy(dtype=np.float64)
    share = float(spec.farm_asset_share)
    if share == 0.0:
        return np.zeros(len(rows), dtype=np.float64)
    return np.where(farm > 0, share * farm, farm)


def _unit_frame(rows: pd.DataFrame, spec: AdjustedPovertySpec) -> dict:
    ofum_member = rows["member_role"].eq("ofum").to_numpy()
    fu = np.ones(len(rows), dtype=bool)
    if spec.income_unit == "head_wife":
        fu = ofum_member
    hw_money = (
        rows["hw_taxable"]
        + rows["hw_transfer"]
        + rows["head_ss"]
        + rows["wife_ss"]
    ).to_numpy(dtype=np.float64)
    fu_money = rows["total_family_income"].to_numpy(dtype=np.float64)
    hw_assets = rows[list(_HW_ASSETS)].sum(axis=1).to_numpy(np.float64)
    fu_assets = hw_assets + rows["ofum_asset"].to_numpy(np.float64)
    hw_ss = (rows["head_ss"] + rows["wife_ss"]).to_numpy(np.float64)
    fu_ss = hw_ss + rows["ofum_ss"].to_numpy(np.float64)
    wife = rows["wife_present"].astype(bool).to_numpy()
    return {
        "fu": fu,
        "money": np.where(fu, fu_money, hw_money),
        "asset_income": np.where(fu, fu_assets, hw_assets),
        "social_security": np.where(fu, fu_ss, hw_ss),
        "size": np.where(
            fu, rows["fu_size"].to_numpy(np.int64), 1 + wife.astype(np.int64)
        ),
        "children": np.where(fu, rows["n_children"].to_numpy(np.int64), 0),
    }


def _annuity_factors(
    rows: pd.DataFrame, spec: AdjustedPovertySpec, table: LifeTable
) -> tuple[np.ndarray, list[str]]:
    factors = np.zeros(len(rows), dtype=np.float64)
    bases: list[str] = []
    cache: dict[tuple, float] = {}
    kwargs = {
        "rate": spec.real_interest_rate,
        "timing": spec.annuity_timing,
        "load": spec.annuity_load,
    }
    for i, row in enumerate(rows.itertuples(index=False)):
        if spec.annuity_lives == "member_rule":
            joint = bool(row.member_married_coresident)
            lives = (
                (str(row.member_sex), int(row.member_age)),
                (str(row.spouse_sex), _int_or_none(row.spouse_age)),
            )
        else:
            joint = bool(row.fu_head_spouse_present)
            lives = (
                (str(row.fu_head_sex), _int_or_none(row.fu_head_age)),
                (
                    str(row.fu_head_spouse_sex),
                    _int_or_none(row.fu_head_spouse_age),
                ),
            )
        (sex_1, age_1), (sex_2, age_2) = lives
        if age_1 is None or (joint and age_2 is None):
            raise AdjustedPovertyError(
                f"observation {row.observation_id}: annuitant age missing"
            )
        key = (
            (joint, sex_1, age_1, sex_2, age_2)
            if joint
            else (joint, sex_1, age_1)
        )
        if key not in cache:
            cache[key] = (
                annuity_factor_joint(
                    table,
                    sex_1,
                    age_1,
                    sex_2,
                    age_2,
                    survivor_share=spec.survivor_share,
                    **kwargs,
                )
                if joint
                else annuity_factor_single(table, sex_1, age_1, **kwargs)
            )
        factors[i] = cache[key]
        bases.append(
            f"joint:{sex_1}{age_1}+{sex_2}{age_2}"
            if joint
            else f"single:{sex_1}{age_1}"
        )
    return factors, bases


def _int_or_none(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def cut_applies(rows: pd.DataFrame, spec: AdjustedPovertySpec) -> np.ndarray:
    """Whether the cut reaches each observation (``cut_start_year``).

    Every observation when ``cut_start_year`` is ``None``; otherwise
    those whose member turns 67 (``birth_year + 67``) in or after the
    start year.
    """

    if spec.cut_start_year is None:
        return np.ones(len(rows), dtype=bool)
    age67_year = rows["birth_year"].to_numpy(dtype=np.int64) + 67
    return age67_year >= int(spec.cut_start_year)


def _ssi_response(
    rows: pd.DataFrame,
    spec: AdjustedPovertySpec,
    units: dict,
    ssi: SsiParameters | None,
    cut_rates: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n = len(rows)
    offset = np.zeros(n, dtype=np.float64)
    new = np.zeros(n, dtype=np.float64)
    if spec.ssi_rule == "none":
        return offset, new
    if ssi is None:
        raise AdjustedPovertyError(f"ssi_rule {spec.ssi_rule} needs SSI data")
    general = _MONTHS * ssi.general_income_exclusion_monthly
    for i, row in enumerate(rows.itertuples(index=False)):
        cut = float(cut_rates[i])
        year = int(row.income_year)
        head_ssi, wife_ssi = float(row.head_ssi), float(row.wife_ssi)
        hw_ssi = head_ssi + wife_ssi
        if hw_ssi > 0:
            couple = head_ssi > 0 and wife_ssi > 0
            if spec.ssi_deeming == "spouse_social_security_counted":
                ss = float(row.head_ss) + float(row.wife_ss)
            else:
                ss = float(row.head_ss) * (head_ssi > 0) + float(
                    row.wife_ss
                ) * (wife_ssi > 0)
            cap = max(0.0, ssi.fbr_annual(year, couple) - hw_ssi)
            offset[i] += min(_countable_ss_fall(ss, cut, general), cap)
        elif spec.ssi_rule == "full_static_recomputation":
            couple = bool(row.wife_present)
            fbr = ssi.fbr_annual(year, couple)
            ss = float(row.head_ss) + float(row.wife_ss)
            unearned = max(
                0.0,
                float(row.hw_transfer)
                - hw_ssi
                - float(row.head_tanf)
                - float(row.wife_tanf)
                - float(row.head_other_welfare)
                - float(row.wife_other_welfare),
            )
            earned = sum(
                max(0.0, float(getattr(row, concept)))
                for concept in family_income.HW_EARNED_CONCEPTS
            )
            before = countable_income(unearned + ss, earned, ssi)
            after = countable_income(unearned + (1.0 - cut) * ss, earned, ssi)
            resources = max(0.0, float(row.wealth1) - float(row.vehicles))
            if (
                before >= fbr
                and after < fbr
                and resources <= ssi.resource_limit(couple)
            ):
                new[i] += fbr - after
        if units["fu"][i] and float(row.ofum_ssi) > 0:
            cap = max(0.0, ssi.fbr_annual(year, False) - float(row.ofum_ssi))
            offset[i] += min(
                _countable_ss_fall(float(row.ofum_ss), cut, general), cap
            )
    return offset, new


def adjusted_incomes(
    rows: pd.DataFrame,
    spec: AdjustedPovertySpec | None = None,
    *,
    data_provenance: str,
    life_table: LifeTable,
    thresholds: PovertyThresholds | None,
    ssi: SsiParameters | None,
    registration_pointer: str | None = None,
) -> pd.DataFrame:
    """Baseline and reform adjusted income and poverty status per row.

    ``rows`` holds one row per cohort-member observation with the columns
    of :data:`REQUIRED_COLUMNS`: the member's family income and wealth
    (family-level concepts of :mod:`populace_dynamics.data.family_income`)
    and the annuitant and threshold attributes.  Returns one row per input
    row with ``observation_id``, ``family_unit_id``, ``income_basis``
    (``family_unit`` or ``head_wife``), ``money_income``,
    ``asset_income_reported``, ``retirement_account_income_removed``,
    ``farm_asset_income_removed``, ``asset_income_removed`` (their sum
    with the reported asset income under ``replace``),
    ``financial_assets``, ``annuity_basis``, ``annuity_factor``,
    ``annuity``, ``baseline_income``, ``social_security``,
    ``cut_applies``, ``cut``,
    ``ssi_offset``, ``ssi_new``, ``reform_income``, ``unit_size``,
    ``threshold``, ``threshold_cell``, ``poor_baseline`` and
    ``poor_reform``.

    ``data_provenance`` is ``"invented"`` for tests and dry runs;
    ``"registered_real"`` needs ``registration_pointer`` and rows marked
    as built from staged PSID files, which are refused as invented.
    """

    spec = AdjustedPovertySpec() if spec is None else spec
    if not isinstance(spec, AdjustedPovertySpec):
        raise AdjustedPovertyError("spec must be an AdjustedPovertySpec")
    if not isinstance(rows, pd.DataFrame):
        raise AdjustedPovertyError("rows must be a DataFrame")
    _validate_provenance(rows, data_provenance, registration_pointer)
    missing = [c for c in REQUIRED_COLUMNS if c not in rows.columns]
    if missing:
        raise AdjustedPovertyError(f"rows lack columns {missing}")
    if rows["observation_id"].duplicated().any():
        raise AdjustedPovertyError("duplicate observation_id")
    roles = set(rows["member_role"].astype(str))
    if not roles <= set(MEMBER_ROLES):
        raise AdjustedPovertyError(
            f"member_role outside {MEMBER_ROLES}: {sorted(roles)}"
        )
    if life_table.name == INVENTED_LIFE_TABLE:
        if data_provenance == REGISTERED_REAL:
            raise AdjustedPovertyError(
                "a registered_real run cannot use an invented life table"
            )
    elif life_table.name != spec.mortality_basis:
        raise AdjustedPovertyError(
            f"life table {life_table.name!r} is not the spec's "
            f"{spec.mortality_basis!r}"
        )
    for name, value in (("thresholds", thresholds), ("ssi", ssi)):
        kind = getattr(value, "provenance", {}).get("kind")
        if data_provenance == REGISTERED_REAL and kind == INVENTED:
            raise AdjustedPovertyError(
                f"a registered_real run cannot use invented {name}"
            )
    rows = rows.reset_index(drop=True)
    units = _unit_frame(rows, spec)
    assets = rows["wealth1"].to_numpy(dtype=np.float64)
    annuitized = spec.annuitized_share * np.maximum(assets, 0.0)
    factors, bases = _annuity_factors(rows, spec, life_table)
    if not np.all(factors > 0):
        raise AdjustedPovertyError("non-positive annuity factor")
    annuity = annuitized / factors
    replace = spec.asset_income_rule == "replace"
    zeros = np.zeros(len(rows), dtype=np.float64)
    retirement_removed = (
        _head_retirement_account_income(rows)
        if replace and spec.retirement_account_income_rule == "remove_head"
        else zeros
    )
    farm_removed = _farm_asset_income(rows, spec) if replace else zeros
    removed = (
        (units["asset_income"] if replace else zeros)
        + retirement_removed
        + farm_removed
    )
    baseline = units["money"] - removed + annuity
    applies = cut_applies(rows, spec)
    cut_rates = np.where(applies, spec.cut_rate, 0.0)
    cut = cut_rates * units["social_security"]
    offset, new = _ssi_response(rows, spec, units, ssi, cut_rates)
    reform = baseline - cut + offset + new
    thresholds_out = np.zeros(len(rows), dtype=np.float64)
    cells: list[str] = []
    for i, row in enumerate(rows.itertuples(index=False)):
        value, cell = threshold_for(
            thresholds,
            int(row.income_year),
            int(units["size"][i]),
            int(units["children"][i]),
            spec.threshold_rule,
            needs_standard=float(row.census_needs_standard),
        )
        thresholds_out[i] = value
        cells.append(cell)
    for name, values in (
        ("baseline_income", baseline),
        ("reform_income", reform),
        ("annuity", annuity),
        ("threshold", thresholds_out),
    ):
        if not np.all(np.isfinite(values)):
            raise AdjustedPovertyError(f"non-finite {name}")
    out = pd.DataFrame(
        {
            "observation_id": rows["observation_id"],
            "family_unit_id": rows["family_unit_id"],
            "income_basis": np.where(units["fu"], "family_unit", "head_wife"),
            "money_income": units["money"],
            "asset_income_reported": units["asset_income"],
            "retirement_account_income_removed": retirement_removed,
            "farm_asset_income_removed": farm_removed,
            "asset_income_removed": removed,
            "financial_assets": assets,
            "annuity_basis": bases,
            "annuity_factor": factors,
            "annuity": annuity,
            "baseline_income": baseline,
            "social_security": units["social_security"],
            "cut_applies": applies,
            "cut": cut,
            "ssi_offset": offset,
            "ssi_new": new,
            "reform_income": reform,
            "unit_size": units["size"],
            "threshold": thresholds_out,
            "threshold_cell": cells,
        }
    )
    out["poor_baseline"] = out["baseline_income"] < out["threshold"]
    out["poor_reform"] = out["reform_income"] < out["threshold"]
    out.attrs["provenance_kind"] = rows.attrs.get("provenance_kind")
    out.attrs["data_provenance"] = data_provenance
    out.attrs["spec"] = spec.as_dict()
    out.attrs["life_table"] = life_table.name
    return out
