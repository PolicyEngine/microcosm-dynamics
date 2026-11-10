"""SSI retirement-fund valuation under POMS SI 01120.210.

Invariants: values lie between zero and the balance; no current lump-sum
access gives zero; a fund reachable only by leaving the current job gives
zero; ineligible spouse/parent funds give zero for deeming; increasing a
deductible penalty cannot increase value; ordinary taxes never reduce
value. Invalid inputs and unresolved periodic-payment cases raise.

The caller supplies current access, including any change after electing
periodic payments, and handles month-of-availability timing (B and C.3).
Periodic eligibility alone does not prove exclusion: B says the fund
"may not" be countable, while D.2 counts the currently available amount.
E.1 requires an eligible owner to apply and choose periodic benefits.
This layer reports that obligation and refuses unresolved elections when
a lump sum remains accessible. It does not decide SSI eligibility.

Authority: POMS SI 01120.210 A.3, B, C.1, C.3, D.2, E.1 and E.4.

Whether section 72(t)'s additional tax is a deductible early-withdrawal
penalty under A.3 remains open for SSI2. Both named readings are required
caller choices; neither is a default. Sources are pinned beside the
versioned retirement-rule parameters in the ``ssi_cola`` source folder.
All functions use caller inputs only and read no person records.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from numbers import Real


class AdditionalTaxTreatment(str, Enum):
    """Unresolved readings of POMS A.3; neither is selected here."""

    DEDUCT_AS_EARLY_WITHDRAWAL_PENALTY = "deduct_as_early_withdrawal_penalty"
    DO_NOT_DEDUCT_TAX = "do_not_deduct_tax"


class RetirementFundOwner(str, Enum):
    """Owner's role in this resource determination (POMS E.4)."""

    ELIGIBLE_INDIVIDUAL = "eligible_individual"
    INELIGIBLE_SPOUSE = "ineligible_spouse"
    INELIGIBLE_PARENT = "ineligible_parent"
    INELIGIBLE_PARENTS_SPOUSE = "ineligible_parents_spouse"


class PeriodicPaymentStatus(str, Enum):
    """Periodic-payment eligibility and disposition, established by caller."""

    NOT_ELIGIBLE = "not_eligible"
    ELIGIBLE_ELECTION_UNRESOLVED = "eligible_election_unresolved"
    RECEIVING = "receiving"
    DENIED = "denied"


@dataclass(frozen=True)
class RetirementFundAssessment:
    """Current resource value and the periodic-benefit obligation."""

    countable_value: float
    must_apply_for_periodic_benefits: bool
    must_choose_periodic_over_lump_sum: bool
    reason: str


def _nonnegative_amount(value: float, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{name} must be a finite nonnegative amount")
    return float(value)


def assess_retirement_fund(
    *,
    balance: float,
    lump_sum_available: bool,
    periodic_payment_status: PeriodicPaymentStatus,
    owner_age: float,
    separated_from_employer: bool,
    withdrawal_requires_separation: bool,
    early_withdrawal_penalty: float,
    additional_tax_amount: float,
    additional_tax_treatment: AdditionalTaxTreatment,
    owner: RetirementFundOwner,
    maximum_lump_sum: float | None = None,
    ordinary_taxes_due: float = 0,
) -> RetirementFundAssessment:
    """Value currently accessible funds without deducting ordinary taxes.

    ``maximum_lump_sum`` is the gross currently withdrawable portion; when
    omitted it is the balance. Penalty amounts apply to that portion,
    not to an imagined full liquidation. ``additional_tax_amount`` comes
    from the statutory distribution-tax layer, with age and exceptions
    already applied. Owner age coverage is 0 through 120 inclusive.

    Access is measured before plan penalties and taxes. Set
    ``withdrawal_requires_separation`` only when *any* payment requires
    leaving the current job (C.1). That excludes the fund only while the
    owner remains employed.
    Receiving periodic benefits does not by itself erase a separately
    retained lump-sum right; provide current rights after the election.
    A denied periodic claim follows C.3; the caller applies next-month
    timing. The two obligation flags express E.1, not a separate resource
    deduction or an SSI award decision.
    """
    balance = _nonnegative_amount(balance, "balance")
    penalty = _nonnegative_amount(
        early_withdrawal_penalty, "early_withdrawal_penalty"
    )
    additional_tax = _nonnegative_amount(
        additional_tax_amount, "additional_tax_amount"
    )
    _nonnegative_amount(ordinary_taxes_due, "ordinary_taxes_due")
    age = _nonnegative_amount(owner_age, "owner_age")
    if age > 120:
        raise ValueError("owner_age outside coverage [0, 120]")
    for name, value in (
        ("lump_sum_available", lump_sum_available),
        ("separated_from_employer", separated_from_employer),
        ("withdrawal_requires_separation", withdrawal_requires_separation),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a boolean")
    try:
        status = PeriodicPaymentStatus(periodic_payment_status)
        treatment = AdditionalTaxTreatment(additional_tax_treatment)
        owner_role = RetirementFundOwner(owner)
    except (TypeError, ValueError) as exc:
        raise ValueError("unsupported retirement-fund option") from exc
    gross = (
        balance
        if maximum_lump_sum is None
        else _nonnegative_amount(maximum_lump_sum, "maximum_lump_sum")
    )
    if gross > balance:
        raise ValueError("maximum_lump_sum exceeds balance")

    periodic_eligible = status in (
        PeriodicPaymentStatus.ELIGIBLE_ELECTION_UNRESOLVED,
        PeriodicPaymentStatus.RECEIVING,
    )
    must_apply = status == PeriodicPaymentStatus.ELIGIBLE_ELECTION_UNRESOLVED

    def assessment(value: float, reason: str) -> RetirementFundAssessment:
        return RetirementFundAssessment(
            value, must_apply, periodic_eligible, reason
        )

    if owner_role != RetirementFundOwner.ELIGIBLE_INDIVIDUAL:
        return RetirementFundAssessment(0.0, False, False, "deeming_exclusion")
    if withdrawal_requires_separation and not separated_from_employer:
        return assessment(0.0, "requires_termination_of_current_employment")
    if not lump_sum_available or gross == 0:
        return assessment(0.0, "no_current_lump_sum_access")
    if status == PeriodicPaymentStatus.ELIGIBLE_ELECTION_UNRESOLVED:
        raise ValueError(
            "periodic-payment election unresolved: establish current "
            "lump-sum rights after the required election (POMS E.1)"
        )
    deductible = penalty
    if treatment == (
        AdditionalTaxTreatment.DEDUCT_AS_EARLY_WITHDRAWAL_PENALTY
    ):
        deductible += additional_tax
    return assessment(max(0.0, gross - deductible), "available_lump_sum")


def retirement_fund_countable_value(**kwargs: object) -> float:
    """Return only the numeric value from :func:`assess_retirement_fund`."""
    return assess_retirement_fund(**kwargs).countable_value
