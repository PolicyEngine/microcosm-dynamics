"""Section 72(t) conformance and properties; all account data are invented.

Fixtures and generated inputs describe no actual account or survey record.
Source citations identify statutory rules or IRS guidance, not observed data.
"""

from datetime import date, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.early_distribution import (
    EARLY_DISTRIBUTION_ACCOUNT_TYPES,
    UNMODELLED_EARLY_DISTRIBUTION_EXCEPTIONS,
    EarlyDistributionException,
    early_distribution_tax,
)

INVENTED_BASE = {
    "birth_date": date(1970, 12, 15),
    "distribution_date": date(2025, 2, 1),
    "account_type": "traditional_ira",
}
INVENTED_AMOUNT = 10_000


def test_includible_amount_only():
    """72(t)(1): 10% of includible income, independent of gross withdrawal."""
    assert early_distribution_tax(4_000, **INVENTED_BASE) == 400
    assert early_distribution_tax(0, **INVENTED_BASE) == 0


def test_exact_half_birthday():
    """72(t)(2)(A)(i): exemption begins on the date of attaining 59½."""
    kwargs = {**INVENTED_BASE, "birth_date": date(1965, 8, 1)}
    assert early_distribution_tax(10_000, **kwargs) == 0
    kwargs["distribution_date"] = date(2025, 1, 31)
    assert early_distribution_tax(10_000, **kwargs) == 1_000


@pytest.mark.parametrize(
    "account_type", sorted(EARLY_DISTRIBUTION_ACCOUNT_TYPES)
)
@pytest.mark.parametrize("exception", ["death", "disability"])
def test_death_and_disability_override_simple_rate(account_type, exception):
    """72(t)(2)(A)(ii), (iii), (6): these exemptions also cover SIMPLE."""
    kwargs = {**INVENTED_BASE, "account_type": account_type}
    if account_type == "simple_ira":
        kwargs["simple_participation_date"] = date(2024, 1, 1)
    assert (
        early_distribution_tax(INVENTED_AMOUNT, exception=exception, **kwargs)
        == 0
    )


@pytest.mark.parametrize("account_type", ["roth_ira", "designated_roth"])
def test_roth_is_not_blanket_early_tax_exemption(account_type):
    """72(t)(1): an includible Roth amount still requires its tax test."""
    assert (
        early_distribution_tax(
            2_000, **{**INVENTED_BASE, "account_type": account_type}
        )
        == 200
    )


def test_simple_two_year_boundary():
    """72(t)(6)(A); IRS exceptions page, SIMPLE footnote: first two years."""
    kwargs = {
        **INVENTED_BASE,
        "account_type": "simple_ira",
        "simple_participation_date": date(2023, 2, 1),
    }
    assert early_distribution_tax(INVENTED_AMOUNT, **kwargs) == 1_000
    kwargs["distribution_date"] = date(2025, 1, 31)
    assert early_distribution_tax(INVENTED_AMOUNT, **kwargs) == 2_500


@pytest.mark.parametrize("account_type", ["employer_plan", "designated_roth"])
def test_separation_during_threshold_birthday_year(account_type):
    """IRS exceptions table, Separation from service: during/after age55 year."""
    kwargs = {
        **INVENTED_BASE,
        "account_type": account_type,
        "separation_date": date(2025, 1, 1),
        "exception": "separation_age_55",
    }
    # Born December 1970: age 54 at separation and payment, but turns 55
    # during 2025. Waiting until 2025 does not rescue a 2024 separation.
    assert early_distribution_tax(INVENTED_AMOUNT, **kwargs) == 0
    kwargs["separation_date"] = date(2024, 12, 31)
    with pytest.raises(ValueError, match="birthday year"):
        early_distribution_tax(INVENTED_AMOUNT, **kwargs)


def test_public_safety_separation_year():
    """72(t)(10)(A), IRS separation row: public safety substitutes age50."""
    assert (
        early_distribution_tax(
            INVENTED_AMOUNT,
            **{
                **INVENTED_BASE,
                "birth_date": date(1975, 12, 15),
                "account_type": "employer_plan",
                "exception": "public_safety_separation_age_50",
                "separation_date": date(2025, 1, 1),
                "governmental_plan": True,
            },
        )
        == 0
    )


def test_public_safety_2006_enactment_boundary():
    """Pub. L. 109-280 §828(b): governmental DB after Aug. 17, 2006."""
    kwargs = {
        **INVENTED_BASE,
        "birth_date": date(1956, 12, 15),
        "distribution_date": date(2006, 8, 18),
        "account_type": "employer_plan",
        "exception": "public_safety_separation_age_50",
        "separation_date": date(2006, 1, 1),
        "governmental_plan": True,
        "public_safety_plan_type": "defined_benefit",
    }
    assert early_distribution_tax(INVENTED_AMOUNT, **kwargs) == 0
    kwargs["distribution_date"] = date(2006, 8, 17)
    with pytest.raises(ValueError, match="after August 17, 2006"):
        early_distribution_tax(INVENTED_AMOUNT, **kwargs)


def test_public_safety_dc_extension_boundary():
    """Pub. L. 114-26 §2(b), (d): DC eligibility starts January 1, 2016."""
    kwargs = {
        **INVENTED_BASE,
        "birth_date": date(1965, 12, 15),
        "distribution_date": date(2016, 1, 1),
        "account_type": "employer_plan",
        "exception": "public_safety_separation_age_50",
        "separation_date": date(2015, 12, 1),
        "governmental_plan": True,
        "public_safety_plan_type": "defined_contribution",
    }
    assert early_distribution_tax(INVENTED_AMOUNT, **kwargs) == 0
    kwargs["distribution_date"] = date(2015, 12, 31)
    with pytest.raises(ValueError, match="before 2016"):
        early_distribution_tax(INVENTED_AMOUNT, **kwargs)


def test_ira_sepp_does_not_require_separation():
    """72(t)(2)(A)(iv), (3)(B): employer separation condition excludes IRA."""
    assert (
        early_distribution_tax(
            INVENTED_AMOUNT,
            **INVENTED_BASE,
            exception="substantially_equal_periodic_payments",
            periodic_payments_start_date=date(2024, 1, 1),
        )
        == 0
    )


def test_employer_sepp_begins_after_separation():
    """72(t)(3)(B): employer SEPP series must begin after separation."""
    assert (
        early_distribution_tax(
            INVENTED_AMOUNT,
            **{**INVENTED_BASE, "account_type": "employer_plan"},
            exception="substantially_equal_periodic_payments",
            separation_date=date(2024, 1, 1),
            periodic_payments_start_date=date(2024, 1, 2),
        )
        == 0
    )


@settings(deadline=None)
@given(
    amount=st.floats(min_value=0, max_value=1e12, allow_nan=False),
    scale=st.floats(min_value=0, max_value=10, allow_nan=False),
    account_type=st.sampled_from(sorted(EARLY_DISTRIBUTION_ACCOUNT_TYPES)),
)
def test_tax_bounds_and_linearity(amount, scale, account_type):
    """72(t)(1), (6): bounds and linearity in the includible amount."""
    kwargs = {**INVENTED_BASE, "account_type": account_type}
    if account_type == "simple_ira":
        kwargs["simple_participation_date"] = date(2024, 1, 1)
    value = early_distribution_tax(amount, **kwargs)
    assert 0 <= value <= amount * 0.25
    assert early_distribution_tax(amount * scale, **kwargs) == pytest.approx(
        value * scale
    )


@settings(deadline=None)
@given(
    amount=st.floats(min_value=0, max_value=1e12, allow_nan=False),
    birth_year=st.integers(min_value=1910, max_value=1966),
    month=st.integers(min_value=1, max_value=12),
    day=st.integers(min_value=1, max_value=28),
    account_type=st.sampled_from(sorted(EARLY_DISTRIBUTION_ACCOUNT_TYPES)),
)
def test_age_59_half_exempts_every_covered_account(
    amount, birth_year, month, day, account_type
):
    """72(t)(2)(A)(i): age exemption covers each supported account."""
    kwargs = {
        **INVENTED_BASE,
        "birth_date": date(birth_year, month, day),
        "distribution_date": date(2026, 12, 31),
        "account_type": account_type,
    }
    if account_type == "simple_ira":
        kwargs["simple_participation_date"] = date(2026, 1, 1)
    assert early_distribution_tax(amount, **kwargs) == 0


@settings(deadline=None)
@given(
    amount=st.floats(min_value=0, max_value=1e12, allow_nan=False),
    exception=st.sampled_from(
        [item.value for item in EarlyDistributionException if item != "none"]
    ),
    account_type=st.sampled_from(sorted(EARLY_DISTRIBUTION_ACCOUNT_TYPES)),
)
def test_covered_exceptions_zero(amount, exception, account_type):
    """72(t)(2)(A)(ii)–(v), (10): eligible exceptions dominate both rates."""
    kwargs = {**INVENTED_BASE, "account_type": account_type}
    if account_type == "simple_ira":
        kwargs["simple_participation_date"] = date(2024, 1, 1)
    if exception in {
        "separation_age_55",
        "public_safety_separation_age_50",
    }:
        kwargs["account_type"] = "employer_plan"
        kwargs.pop("simple_participation_date", None)
        kwargs["separation_date"] = date(2025, 1, 1)
        if exception == "public_safety_separation_age_50":
            kwargs["birth_date"] = date(1975, 12, 15)
            kwargs["governmental_plan"] = True
    elif exception == "substantially_equal_periodic_payments":
        kwargs["periodic_payments_start_date"] = date(2024, 1, 2)
        if account_type in {"employer_plan", "designated_roth"}:
            kwargs["separation_date"] = date(2024, 1, 1)
    assert early_distribution_tax(amount, exception=exception, **kwargs) == 0


@settings(deadline=None)
@given(
    amount=st.floats(min_value=0, max_value=1e12, allow_nan=False),
    participation_year=st.integers(min_value=2002, max_value=2024),
    month=st.integers(min_value=1, max_value=12),
    day=st.integers(min_value=1, max_value=28),
)
def test_simple_rate_changes_on_second_anniversary(
    amount, participation_year, month, day
):
    """72(t)(6)(A): exactly 25% before, and 10% at, two calendar years."""
    anniversary = date(participation_year + 2, month, day)
    kwargs = {
        **INVENTED_BASE,
        "birth_date": date(1980, 1, 1),
        "distribution_date": anniversary,
        "account_type": "simple_ira",
        "simple_participation_date": date(participation_year, month, day),
    }
    assert early_distribution_tax(amount, **kwargs) == amount * 0.10
    kwargs["distribution_date"] = anniversary - timedelta(days=1)
    assert early_distribution_tax(amount, **kwargs) == amount * 0.25


@settings(deadline=None)
@given(
    birth_year=st.integers(min_value=1947, max_value=1971),
    birth_month=st.integers(min_value=1, max_value=12),
    birth_day=st.integers(min_value=1, max_value=28),
)
def test_separation_birthday_year_rule(birth_year, birth_month, birth_day):
    """IRS separation row: eligibility is nondecreasing in separation year."""
    kwargs = {
        **INVENTED_BASE,
        "birth_date": date(birth_year, birth_month, birth_day),
        "distribution_date": date(birth_year + 55, 12, 31),
        "account_type": "employer_plan",
        "exception": "separation_age_55",
        "separation_date": date(birth_year + 55, 1, 1),
    }
    assert early_distribution_tax(INVENTED_AMOUNT, **kwargs) == 0
    kwargs["separation_date"] = date(birth_year + 54, 12, 31)
    with pytest.raises(ValueError, match="birthday year"):
        early_distribution_tax(INVENTED_AMOUNT, **kwargs)


@pytest.mark.parametrize(
    "exception", list(UNMODELLED_EARLY_DISTRIBUTION_EXCEPTIONS)
)
def test_named_unmodelled_exception_refuses(exception):
    """Each registry entry names its statute; no unmodelled route defaults."""
    with pytest.raises(NotImplementedError, match="unmodelled"):
        early_distribution_tax(
            INVENTED_AMOUNT, **INVENTED_BASE, exception=exception
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"account_type": "governmental_457b"},
        {"account_type": "sep_ira"},
        {"account_type": "unknown"},
        {"account_type": None},
        {"account_type": []},
        {"distribution_date": date(2001, 1, 1)},
        {
            "account_type": "designated_roth",
            "distribution_date": date(2005, 12, 31),
        },
        {"distribution_date": date(2027, 1, 1)},
        {"distribution_date": "2025-01-01"},
        {"distribution_date": datetime(2025, 1, 1)},
        {"birth_date": date(2026, 1, 1)},
        {"birth_date": date(1904, 1, 1)},
        {"birth_date": "1970-01-01"},
        {"exception": "invented_exception"},
        {"exception": []},
        {"governmental_plan": 1},
        {"sepp_modified": 0},
        {"governmental_plan": True},
        {"public_safety_plan_type": "defined_benefit"},
        {"public_safety_plan_type": "invented_plan_type"},
        {"public_safety_plan_type": []},
        {
            "account_type": "designated_roth",
            "exception": "public_safety_separation_age_50",
            "public_safety_plan_type": "defined_benefit",
            "separation_date": date(2025, 1, 1),
            "governmental_plan": True,
        },
        {"separation_date": "2024-01-01"},
        {"separation_date": date(1969, 1, 1)},
        {"separation_date": date(2025, 2, 2)},
        {"periodic_payments_start_date": "2024-01-01"},
        {"periodic_payments_start_date": date(1969, 1, 1)},
        {"periodic_payments_start_date": date(2025, 2, 2)},
        {"periodic_payments_start_date": date(2024, 1, 1)},
        {"account_type": "simple_ira"},
        {
            "account_type": "simple_ira",
            "simple_participation_date": "2024-01-01",
        },
        {
            "account_type": "simple_ira",
            "simple_participation_date": date(1969, 1, 1),
        },
        {
            "account_type": "simple_ira",
            "simple_participation_date": date(2026, 1, 1),
        },
        {"simple_participation_date": date(2024, 1, 1)},
        {
            "exception": "separation_age_55",
            "separation_date": date(2025, 1, 1),
        },
        {"exception": "separation_age_55", "account_type": "employer_plan"},
        {
            "exception": "public_safety_separation_age_50",
            "account_type": "employer_plan",
            "separation_date": date(2025, 1, 1),
        },
        {
            "exception": "public_safety_separation_age_50",
            "account_type": "employer_plan",
            "separation_date": date(2014, 1, 1),
            "distribution_date": date(2015, 1, 1),
            "governmental_plan": True,
        },
        {"exception": "substantially_equal_periodic_payments"},
        {
            "exception": "substantially_equal_periodic_payments",
            "account_type": "employer_plan",
            "periodic_payments_start_date": date(2024, 1, 1),
        },
        {
            "exception": "substantially_equal_periodic_payments",
            "account_type": "employer_plan",
            "periodic_payments_start_date": date(2024, 1, 1),
            "separation_date": date(2024, 1, 1),
        },
        {
            "exception": "substantially_equal_periodic_payments",
            "account_type": "employer_plan",
            "periodic_payments_start_date": date(2024, 1, 1),
            "separation_date": date(2024, 1, 2),
        },
    ],
)
def test_incomplete_or_uncovered_facts_refuse(changes):
    """Unsupported inputs and unsatisfied statutory prerequisites raise."""
    with pytest.raises(ValueError):
        early_distribution_tax(INVENTED_AMOUNT, **{**INVENTED_BASE, **changes})


@pytest.mark.parametrize(
    "amount", [-1, float("nan"), float("inf"), True, "100"]
)
def test_invalid_includible_amount_refuses(amount):
    """72(t)(1): a missing, nonfinite or negative tax base is not zero."""
    with pytest.raises(ValueError, match="finite and nonnegative"):
        early_distribution_tax(amount, **INVENTED_BASE)


def test_modified_sepp_requires_recapture_model():
    """72(t)(4): recapture is explicitly outside the annual-rate helper."""
    with pytest.raises(NotImplementedError, match="recapture"):
        early_distribution_tax(
            INVENTED_AMOUNT, **INVENTED_BASE, sepp_modified=True
        )


def test_enum_and_named_exception_are_equivalent():
    """Differential interface check for the two accepted option forms."""
    assert early_distribution_tax(
        INVENTED_AMOUNT,
        **INVENTED_BASE,
        exception=EarlyDistributionException.DEATH,
    ) == early_distribution_tax(
        INVENTED_AMOUNT, **INVENTED_BASE, exception="death"
    )
