"""The modelled part of the additional tax in 26 U.S.C. 72(t).

This rule consumes an already determined *includible* amount, never a
gross distribution or survey record. It does not determine Roth ordering,
conversion recapture, disability, public-safety occupational status, or
whether a payment series satisfies the actuarial requirements for SEPPs.
The caller certifies those facts when selecting a modelled exception.
Ordinary income tax and the SSI treatment of this additional tax belong
to their respective rule layers.

Coverage: distributions in 2002--2026, from traditional, SIMPLE or Roth
IRAs, qualified employer plans (401(a), 403(a), 403(b)) and their designated
Roth accounts (from 2006). Governmental 457(b) accounts require
rollover-source detail under section 72(t)(9) and are refused. The
public-safety age-50 route
covers state/local governmental defined-benefit plans after August 17,
2006, and governmental defined-benefit and defined-contribution plans
from 2016. The caller certifies occupational eligibility under the law
in force on the distribution date.

Invariants, checked beside statutory examples with invented inputs:

* The additional tax is between zero and 25 percent of the includible
  amount and is linear in that amount for fixed eligibility facts.
* Attaining 59 years and six calendar months eliminates this tax.
* A covered exception eliminates the tax, including the SIMPLE rate.
* Employer separation exemptions never apply to IRAs; separation in the
  threshold birthday's calendar year suffices, even before that birthday.
* A SIMPLE account's rate changes from 25 to 10 percent on the second
  participation anniversary, never before it.
* Unsupported years, dates, accounts, exceptions and incomplete or
  inconsistent eligibility facts raise rather than implying eligibility.

Sources: 26 U.S.C. 72(t)(1), (2)(A)(i)--(v), (3), (4), (6), (9), (10);
402A and its effective-date note; 408A(d)(3)(F);
IRS, "Retirement topics -- Exceptions to tax on early distributions";
Pub. L. 109-280 section 828; and Pub. L. 114-26 section 2. Captures and the
named unmodelled routes are recorded in the
retirement_rules_v1/early_distribution research note.
"""

from __future__ import annotations

import math
from calendar import monthrange
from datetime import date
from enum import Enum
from types import MappingProxyType

__all__ = [
    "EarlyDistributionException",
    "EARLY_DISTRIBUTION_ACCOUNT_TYPES",
    "UNMODELLED_EARLY_DISTRIBUTION_EXCEPTIONS",
    "early_distribution_tax",
]


class EarlyDistributionException(str, Enum):
    """Exception whose required factual predicates this layer can check."""

    NONE = "none"
    DEATH = "death"
    DISABILITY = "disability"
    SEPARATION_AGE_55 = "separation_age_55"
    PUBLIC_SAFETY_SEPARATION_AGE_50 = "public_safety_separation_age_50"
    SUBSTANTIALLY_EQUAL_PERIODIC_PAYMENTS = (
        "substantially_equal_periodic_payments"
    )


EARLY_DISTRIBUTION_ACCOUNT_TYPES = frozenset(
    {
        "traditional_ira",
        "simple_ira",
        "roth_ira",
        "employer_plan",
        "designated_roth",
    }
)
_EMPLOYER_ACCOUNTS = frozenset({"employer_plan", "designated_roth"})

# This registry describes routes; selecting any of them raises. The
# applicable dates and dollar ceilings of these routes are not modelled.
UNMODELLED_EARLY_DISTRIBUTION_EXCEPTIONS = MappingProxyType(
    {
        "esop_dividends": "72(t)(2)(A)(vi)",
        "irs_levy": "72(t)(2)(A)(vii)",
        "federal_phased_retirement": "72(t)(2)(A)(viii)",
        "returned_ira_contribution_earnings": "72(t)(2)(A)(ix)",
        "medical_expenses": "72(t)(2)(B)",
        "qualified_domestic_relations_order": "72(t)(2)(C)",
        "unemployed_health_insurance": "72(t)(2)(D)",
        "higher_education": "72(t)(2)(E)",
        "first_home_purchase": "72(t)(2)(F)",
        "qualified_reservist": "72(t)(2)(G)",
        "birth_or_adoption": "72(t)(2)(H)",
        "emergency_personal_expense": "72(t)(2)(I)",
        "pension_linked_emergency_savings": "72(t)(2)(J)",
        "domestic_abuse": "72(t)(2)(K)",
        "terminal_illness": "72(t)(2)(L)",
        "qualified_disaster_recovery": "72(t)(2)(M), (11)",
        "qualified_long_term_care": "72(t)(2)(N)",
        "public_safety_25_years_service": "72(t)(10)(A)",
        "private_sector_firefighter": "72(t)(10)(A)",
        "simple_plan_conversion_rollover": "72(t)(6)(B)",
        "sepp_modification_recapture": "72(t)(4)",
        "roth_conversion_recapture": "408A(d)(3)(F)",
        "automatic_enrollment_withdrawal": "414(w)(1)(B)",
        "corrective_employer_distribution": (
            "401(k)(8)(D), 401(m)(7)(A), 402(g)(2)(C)"
        ),
        "rollover": "402(c), 403(a)(4), 403(b)(8), 408(d)(3)",
        "returned_ira_contribution": "408(d)(4)",
        "coronavirus_related_distribution": (
            "Pub. L. 116-136 section 2202(a)(1)"
        ),
    }
)


def _months_after(value: date, months: int) -> date:
    """Add calendar months, clamping an absent day to the month's end."""
    month_number = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_number, 12)
    month = zero_based_month + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _require_date(value: object, name: str) -> date:
    if type(value) is not date:
        raise ValueError(f"{name} must be a datetime.date, not a datetime")
    return value


def early_distribution_tax(
    includible_amount: float,
    *,
    birth_date: date,
    distribution_date: date,
    account_type: str,
    exception: EarlyDistributionException | str = (
        EarlyDistributionException.NONE
    ),
    separation_date: date | None = None,
    simple_participation_date: date | None = None,
    periodic_payments_start_date: date | None = None,
    governmental_plan: bool = False,
    public_safety_plan_type: str | None = None,
    sepp_modified: bool = False,
) -> float:
    """Return only the section 72(t) additional tax, in input money units.

    ``includible_amount`` excludes nonincludible basis and qualified Roth
    distributions. Roth conversion recapture requires separate history
    and is an explicitly unmodelled route. ``death`` and ``disability``
    certify the conditions in section 72(t)(2)(A)(ii), (iii), including
    disability under section 72(m)(7). A SEPP selection certifies the
    life-expectancy and payment-frequency tests; an employer series must
    also begin after the supplied separation date. Subsequent SEPP
    recapture is refused, not estimated.

    A public-safety selection certifies qualified employee status under
    section 72(t)(10)(B) as effective on the payment date; it also requires
    ``governmental_plan=True``. Before 2016 it requires
    ``public_safety_plan_type="defined_benefit"`` and state/local
    occupational eligibility under Pub. L. 109-280 section 828.
    Separation-age tests use the year of separation, never the later
    distribution year. A later withdrawal cannot cure an earlier
    separation below the threshold.
    """
    if (
        isinstance(includible_amount, bool)
        or not isinstance(includible_amount, (int, float))
        or not math.isfinite(includible_amount)
        or includible_amount < 0
    ):
        raise ValueError("includible_amount must be finite and nonnegative")
    birth_date = _require_date(birth_date, "birth_date")
    distribution_date = _require_date(distribution_date, "distribution_date")
    if not 2002 <= distribution_date.year <= 2026:
        raise ValueError("early-distribution coverage is 2002 through 2026")
    if (
        not birth_date
        <= distribution_date
        <= _months_after(birth_date, 120 * 12)
    ):
        raise ValueError("age must be between zero and 120 years")
    if (
        not isinstance(account_type, str)
        or account_type not in EARLY_DISTRIBUTION_ACCOUNT_TYPES
    ):
        raise ValueError(f"uncovered account type: {account_type!r}")
    if account_type == "designated_roth" and distribution_date.year < 2006:
        raise ValueError("designated Roth accounts begin in 2006")
    if not isinstance(exception, str):
        raise ValueError(f"unknown exception: {exception!r}")
    if exception in UNMODELLED_EARLY_DISTRIBUTION_EXCEPTIONS:
        raise NotImplementedError(f"unmodelled exception: {exception}")
    try:
        selected = EarlyDistributionException(exception)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unknown exception: {exception!r}") from exc
    if type(governmental_plan) is not bool or type(sepp_modified) is not bool:
        raise ValueError("governmental_plan and sepp_modified must be bool")
    if governmental_plan and account_type not in _EMPLOYER_ACCOUNTS:
        raise ValueError("an IRA cannot be a governmental employer plan")
    if public_safety_plan_type is not None:
        if not isinstance(
            public_safety_plan_type, str
        ) or public_safety_plan_type not in {
            "defined_benefit",
            "defined_contribution",
        }:
            raise ValueError("unknown public-safety plan type")
        if selected != selected.PUBLIC_SAFETY_SEPARATION_AGE_50:
            raise ValueError(
                "a public-safety plan type requires its exception"
            )
        if (
            public_safety_plan_type == "defined_benefit"
            and account_type == "designated_roth"
        ):
            raise ValueError(
                "designated Roth accounts are not defined benefit"
            )
    if sepp_modified:
        raise NotImplementedError("SEPP modification recapture is unmodelled")
    if separation_date is not None:
        separation_date = _require_date(separation_date, "separation_date")
        if not birth_date <= separation_date <= distribution_date:
            raise ValueError("separation must fall between birth and payment")
    if periodic_payments_start_date is not None:
        periodic_payments_start_date = _require_date(
            periodic_payments_start_date, "periodic_payments_start_date"
        )
        if not birth_date <= periodic_payments_start_date <= distribution_date:
            raise ValueError(
                "series start must fall between birth and payment"
            )
        if selected != selected.SUBSTANTIALLY_EQUAL_PERIODIC_PAYMENTS:
            raise ValueError("a series start requires the SEPP exception")
    if account_type == "simple_ira":
        if simple_participation_date is None:
            raise ValueError("a SIMPLE account requires first participation")
        simple_participation_date = _require_date(
            simple_participation_date, "simple_participation_date"
        )
        if not birth_date <= simple_participation_date <= distribution_date:
            raise ValueError("SIMPLE participation must precede payment")
    elif simple_participation_date is not None:
        raise ValueError("SIMPLE participation applies only to SIMPLE IRAs")

    separation_exceptions = {
        selected.SEPARATION_AGE_55,
        selected.PUBLIC_SAFETY_SEPARATION_AGE_50,
    }
    if selected in separation_exceptions:
        if account_type not in _EMPLOYER_ACCOUNTS:
            raise ValueError("the separation exception does not cover IRAs")
        if separation_date is None:
            raise ValueError("the separation exception requires separation")
        threshold = 55
        if selected == selected.PUBLIC_SAFETY_SEPARATION_AGE_50:
            if distribution_date <= date(2006, 8, 17):
                raise ValueError(
                    "public-safety coverage begins after August 17, 2006"
                )
            if not governmental_plan:
                raise ValueError("public safety requires a governmental plan")
            if distribution_date.year < 2016 and (
                public_safety_plan_type != "defined_benefit"
            ):
                raise ValueError(
                    "before 2016 public safety requires a defined-benefit plan"
                )
            threshold = 50
        if separation_date.year < birth_date.year + threshold:
            raise ValueError("separation precedes the threshold birthday year")
    elif selected == selected.SUBSTANTIALLY_EQUAL_PERIODIC_PAYMENTS:
        if periodic_payments_start_date is None:
            raise ValueError(
                "a SEPP exception requires its first payment date"
            )
        if account_type in _EMPLOYER_ACCOUNTS and (
            separation_date is None
            or periodic_payments_start_date <= separation_date
        ):
            raise ValueError("employer SEPPs must begin after separation")

    if selected != selected.NONE or distribution_date >= _months_after(
        birth_date, 59 * 12 + 6
    ):
        return 0.0
    rate = 0.10
    if account_type == "simple_ira" and distribution_date < _months_after(
        simple_participation_date, 24
    ):
        rate = 0.25
    return includible_amount * rate
