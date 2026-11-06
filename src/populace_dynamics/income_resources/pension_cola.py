"""Federal DB pension COLAs, with explicitly named research assumptions.

Invariants: no CPI increase gives no COLA; rates never exceed rounded
positive CPI growth; FERS ordinary retirement gets no increase before
age 62; statutory exceptions preserve the age-independent rule; a first
COLA cannot exceed a full COLA; increases round to one tenth of a
percentage point. Invalid years, ages, plan types and unmodelled annuity
categories raise. An amount adjustment never reduces an existing
annuity; the CSRS cap limits increases; a positive adjustment rounds
monthly dollars down but gives at least $1 where the cap permits.
State/local and private options are assumptions for later registration,
not encoded plan law or selected defaults.

Coverage is adjustment years 2002-2026 and ages 0-120. CPI input means
growth in average third-quarter CPI-W since the last adjustment base,
not necessarily growth from the immediately preceding year (5 U.S.C.
8340(a)-(b), 8462(a)-(b)). Rates are effective December 1. The caller
tracks the base and the annuity's commencement and statutory category.
The first-increase month count includes any fraction of a month.

The rate helper does not compute disability benefit components, survivor
benefit inheritance or CSRS offsets. It covers the disability component
under 8452(a) only after its initial 60-percent period; that period gets
no COLA under 8452(a)(1)(B). Other disability component computations are
refused. The amount helper requires an explicit CSRS cap under 8340(g).
Sources and versioned parameters live in the ``ssi_cola`` source folder.
"""

from __future__ import annotations

import json
import math
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from enum import Enum
from numbers import Real
from pathlib import Path


class FederalPensionPlan(str, Enum):
    CSRS = "csrs"
    FERS = "fers"


class FederalAnnuityCategory(str, Enum):
    """Exact coverage categories; unsupported categories do not default."""

    ORDINARY_RETIREMENT = "ordinary_retirement"
    SPECIAL_8412_D1_OR_E = "special_8412_d1_or_e"
    MILITARY_TECHNICIAN_DISABILITY_8414_C = (
        "military_technician_disability_8414_c"
    )
    SURVIVOR_OTHER_THAN_CHILD = "survivor_other_than_child"
    DISABILITY_8452_A_INITIAL_PERIOD = "disability_8452_a_initial_period"
    DISABILITY_8452_A_AFTER_INITIAL_PERIOD = (
        "disability_8452_a_after_initial_period"
    )


class PensionColaAssumption(str, Enum):
    """Proposals requiring a later model registration; no default."""

    STATE_LOCAL_CPI_CAPPED_AT_THREE_PERCENT = (
        "state_local_cpi_capped_at_three_percent"
    )
    PRIVATE_FIXED_NOMINAL = "private_fixed_nominal"


_PARAMETER_PATH = (
    Path(__file__).resolve().parents[3]
    / "data/external/income_resources/retirement_rules_v1/ssi_cola"
    / "pension_cola_parameters.json"
)


def _parameters() -> dict:
    with _PARAMETER_PATH.open() as stream:
        parameters = json.load(stream)
    if parameters["version"] != "retirement_rules_v1":
        raise ValueError("unsupported pension COLA parameter version")
    return parameters


def _finite_number(value: float, name: str) -> Decimal:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite number")
    return Decimal(str(value))


def federal_pension_cola_rate(
    *,
    year: int,
    plan: FederalPensionPlan,
    price_index_change: float,
    age: float,
    annuity_category: FederalAnnuityCategory,
    first_increase_months: int = 12,
) -> float:
    """Return a fractional COLA rate from statutory CPI and annuity state.

    ``first_increase_months`` is 0-12 for the first increase, and 12 for
    subsequent increases. It is the statutory month count, not an age
    fraction. ``age`` is age on December 1, the increase's effective date
    (8462(c)(3)(A)), rather than age at the end of the calendar year.
    The FERS three-percent breakpoint uses the unrounded CPI
    change before rounding, as 8462(b)(1) requires.
    """
    parameters = _parameters()
    if (
        type(year) is not int
        or not parameters["first_year"] <= year <= parameters["last_year"]
    ):
        raise ValueError("year outside federal COLA coverage [2002, 2026]")
    try:
        plan = FederalPensionPlan(plan)
        category = FederalAnnuityCategory(annuity_category)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "unsupported federal plan or annuity category"
        ) from exc
    growth = _finite_number(price_index_change, "price_index_change")
    owner_age = _finite_number(age, "age")
    if not 0 <= owner_age <= parameters["maximum_age"]:
        raise ValueError("age outside federal COLA coverage [0, 120]")
    if (
        type(first_increase_months) is not int
        or not 0 <= first_increase_months <= 12
    ):
        raise ValueError("first_increase_months must be an integer in [0, 12]")
    if plan == FederalPensionPlan.CSRS and category not in (
        FederalAnnuityCategory.ORDINARY_RETIREMENT,
        FederalAnnuityCategory.SURVIVOR_OTHER_THAN_CHILD,
    ):
        raise ValueError("FERS-specific category cannot describe CSRS")
    if (
        plan == FederalPensionPlan.FERS
        and owner_age >= 62
        and category
        in (
            FederalAnnuityCategory.DISABILITY_8452_A_INITIAL_PERIOD,
            FederalAnnuityCategory.DISABILITY_8452_A_AFTER_INITIAL_PERIOD,
        )
    ):
        raise ValueError(
            "disability annuity must be redetermined at 62 (8452(b))"
        )
    if growth <= 0:
        return 0.0
    rate_unit = Decimal(parameters["rate_rounding_unit"])
    rounded_growth = growth.quantize(rate_unit, rounding=ROUND_HALF_UP)
    if plan == FederalPensionPlan.CSRS:
        rate = rounded_growth
    else:
        if (
            category == FederalAnnuityCategory.ORDINARY_RETIREMENT
            and owner_age < parameters["fers"]["ordinary_minimum_age"]
        ):
            return 0.0
        if category == (
            FederalAnnuityCategory.DISABILITY_8452_A_INITIAL_PERIOD
        ):
            return 0.0
        plateau = Decimal(parameters["fers"]["plateau_rate"])
        breakpoint = Decimal(parameters["fers"]["raw_growth_breakpoint"])
        reduction = Decimal(parameters["fers"]["high_growth_reduction"])
        rate = (
            min(rounded_growth, plateau)
            if growth <= breakpoint
            else rounded_growth - reduction
        )
    rate = (rate * first_increase_months / 12).quantize(
        rate_unit, rounding=ROUND_HALF_UP
    )
    return float(rate)


def cola_adjusted_monthly_annuity(
    *,
    monthly_annuity: int,
    cola_rate: float,
    plan: FederalPensionPlan,
    csrs_statutory_cap: int | None = None,
) -> int:
    """Apply rate, dollar rounding and minimum increase (8340(e), 8462(d)).

    CSRS requires the caller's monthly whole-dollar cap from 8340(g):
    the annual statutory cap divided by twelve and floored. That cap
    is the greater of its GS-15 and indexed-final-pay amounts, converted
    to monthly dollars. That cap limits an increase; it does
    not reduce the already payable annuity. The helper covers ordinary
    annuities, not additional annuities purchased by voluntary CSRS
    contributions, which 8340(d) excludes from increases.
    """
    if type(monthly_annuity) is not int or monthly_annuity < 0:
        raise ValueError("monthly_annuity must be whole nonnegative dollars")
    rate = _finite_number(cola_rate, "cola_rate")
    if rate < 0:
        raise ValueError("cola_rate must be nonnegative")
    try:
        plan = FederalPensionPlan(plan)
    except (TypeError, ValueError) as exc:
        raise ValueError("unsupported federal pension plan") from exc
    if plan == FederalPensionPlan.CSRS:
        if type(csrs_statutory_cap) is not int or csrs_statutory_cap < 0:
            raise ValueError("CSRS requires a whole-dollar statutory cap")
    elif csrs_statutory_cap is not None:
        raise ValueError("CSRS cap does not apply to FERS")
    if rate == 0 or monthly_annuity == 0:
        return monthly_annuity
    adjusted = max(
        monthly_annuity + 1,
        int(
            (monthly_annuity * (1 + rate)).to_integral_value(
                rounding=ROUND_FLOOR
            )
        ),
    )
    if plan == FederalPensionPlan.CSRS:
        adjusted = max(monthly_annuity, min(adjusted, csrs_statutory_cap))
    return adjusted


def assumed_pension_cola_rate(
    *, assumption: PensionColaAssumption, price_index_change: float
) -> float:
    """Evaluate an explicitly selected proposed assumption, not plan law."""
    try:
        assumption = PensionColaAssumption(assumption)
    except (TypeError, ValueError) as exc:
        raise ValueError("unsupported pension COLA assumption") from exc
    growth = _finite_number(price_index_change, "price_index_change")
    if assumption == PensionColaAssumption.PRIVATE_FIXED_NOMINAL:
        return 0.0
    cap = Decimal(_parameters()["proposed_state_local_cap"])
    return float(min(max(Decimal(0), growth), cap))
