"""Cross-rule examples on INVENTED owners and balances, without microdata.

The RMD helper reads pinned parameters under ``"data" / "external"``.
"""

from datetime import date

import pytest

from populace_dynamics.income_resources.early_distribution import (
    early_distribution_tax,
)
from populace_dynamics.income_resources.retirement_resources import (
    AdditionalTaxTreatment,
    assess_retirement_fund,
)
from populace_dynamics.income_resources.retirement_rules import (
    AccountType,
    required_minimum_distribution,
)


@pytest.mark.parametrize(
    "reading,expected",
    [
        (AdditionalTaxTreatment.DEDUCT_AS_EARLY_WITHDRAWAL_PENALTY, 9000),
        (AdditionalTaxTreatment.DO_NOT_DEDUCT_TAX, 10_000),
    ],
)
def test_statutory_tax_can_feed_both_ssi_readings(reading, expected):
    """IRC72(t)(1) feeds the unresolved POMS SI01120.210 A.3 readings."""
    invented_tax = early_distribution_tax(
        10_000,
        birth_date=date(1976, 1, 1),
        distribution_date=date(2026, 6, 1),
        account_type=AccountType.TRADITIONAL_IRA,
    )
    assert invented_tax == 1000
    assessment = assess_retirement_fund(
        balance=10_000,
        lump_sum_available=True,
        periodic_payment_status="not_eligible",
        owner_age=50,
        separated_from_employer=True,
        withdrawal_requires_separation=False,
        early_withdrawal_penalty=0,
        additional_tax_amount=invented_tax,
        additional_tax_treatment=reading,
        owner="eligible_individual",
    )
    assert assessment.countable_value == expected


def test_lifetime_rmd_exemption_does_not_imply_ssi_resource_exclusion():
    """IRC408A(c)(5) and POMS SI01120.210 B ask different questions."""
    assert (
        required_minimum_distribution(
            10_000, 75, 2026, AccountType.ROTH_IRA, birth_date=date(1951, 1, 1)
        )
        == 0
    )
    assert (
        assess_retirement_fund(
            balance=10_000,
            lump_sum_available=True,
            periodic_payment_status="not_eligible",
            owner_age=75,
            separated_from_employer=True,
            withdrawal_requires_separation=False,
            early_withdrawal_penalty=0,
            additional_tax_amount=0,
            additional_tax_treatment="do_not_deduct_tax",
            owner="eligible_individual",
        ).countable_value
        == 10_000
    )
