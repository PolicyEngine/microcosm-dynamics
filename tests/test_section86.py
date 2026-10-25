"""Invented units exercise §86 independently of any tax interpreter."""

from decimal import Decimal, localcontext

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.section86 import section86_inclusions


@pytest.mark.parametrize(
    ("benefits", "modified_agi", "status", "pre_1993", "current"),
    [
        # Combined income at the general base, between tiers, and at the
        # adjusted base, respectively: $25,000, $30,000 and $34,000.
        (20000, 15000, "SINGLE", "0", "0"),
        (20000, 20000, "SINGLE", "2500", "2500"),
        (20000, 24000, "SINGLE", "4500", "4500"),
        # $40,000 combined: .5 * (40000 - 25000) = 7500;
        # .85 * (40000 - 34000) + 4500 = 9600.
        (20000, 30000, "SINGLE", "7500", "9600"),
        (20000, 30000, "HEAD_OF_HOUSEHOLD", "7500", "9600"),
        # Joint $50,000 combined: .5 * (50000 - 32000) = 9000;
        # .85 * (50000 - 44000) + 6000 = 11100.
        (30000, 35000, "JOINT", "9000", "11100"),
        (30000, 17000, "JOINT", "0", "0"),
        (30000, 23000, "JOINT", "3000", "3000"),
        (30000, 29000, "JOINT", "6000", "6000"),
        (40000, 190000, "SINGLE", "20000", "34000"),
        # Half-of-benefits and 85%-of-benefits caps bind.
        (1000, 100000, "SINGLE", "500", "850"),
        (20000, -5000, "SINGLE", "0", "0"),
        (0, 100000, "SINGLE", "0", "0"),
        # Upper tier retains min(paragraph 1, half the threshold gap).
        (100, 33975, "SINGLE", "50", "71.25"),
    ],
)
def test_hand_derived_tiers(benefits, modified_agi, status, pre_1993, current):
    result = section86_inclusions(benefits, modified_agi, status)
    assert result.pre_1993 == Decimal(pre_1993)
    assert result.current == Decimal(current)
    assert result.combined_income == (
        Decimal(str(modified_agi)) + Decimal(str(benefits)) / 2
    )


def test_separate_lived_apart_all_year_uses_general_thresholds():
    result = section86_inclusions(
        20000, 30000, "SEPARATE", lived_apart_all_year=True
    )
    assert result == section86_inclusions(20000, 30000, "SINGLE")


@pytest.mark.parametrize(
    ("combined_income", "pre_1993", "current"),
    [
        ("24999.99", "0", "0"),
        ("25000", "0", "0"),
        ("25000.01", "0.005", "0.005"),
        ("33999.99", "4499.995", "4499.995"),
        ("34000", "4500", "4500"),
        ("34000.01", "4500.005", "4500.0085"),
    ],
)
@pytest.mark.parametrize("status", ["SINGLE", "HEAD_OF_HOUSEHOLD", "SEPARATE"])
def test_general_thresholds_on_both_sides(
    combined_income, pre_1993, current, status
):
    # Benefits of $20,000 supply $10,000 to §86(b)(1)(A). The first
    # $9,000 above the base contributes half; above $34,000, paragraph
    # (2) retains $4,500 and adds 85% of the remaining excess.
    result = section86_inclusions(
        20000,
        Decimal(combined_income) - Decimal("10000"),
        status,
        lived_apart_all_year=True,
    )
    assert result.pre_1993 == Decimal(pre_1993)
    assert result.current == Decimal(current)


@pytest.mark.parametrize(
    ("combined_income", "pre_1993", "current"),
    [
        ("31999.99", "0", "0"),
        ("32000", "0", "0"),
        ("32000.01", "0.005", "0.005"),
        ("43999.99", "5999.995", "5999.995"),
        ("44000", "6000", "6000"),
        ("44000.01", "6000.005", "6000.0085"),
    ],
)
def test_joint_thresholds_on_both_sides(combined_income, pre_1993, current):
    # Joint benefits of $30,000 supply $15,000 of combined income;
    # the retained half of the $12,000 threshold gap is $6,000.
    result = section86_inclusions(
        30000, Decimal(combined_income) - Decimal("15000"), "JOINT"
    )
    assert result.pre_1993 == Decimal(pre_1993)
    assert result.current == Decimal(current)


def test_paragraph_one_amount_is_not_the_upper_tier_retained_amount():
    result = section86_inclusions(20000, 30000, "SINGLE")
    assert result.pre_1993 == Decimal("7500")
    assert result.pre_1993 != Decimal("4500")
    assert result.current == Decimal("4500") + Decimal("0.85") * 6000


@pytest.mark.parametrize("status", ["WIDOW", "UNKNOWN", "single", "", None])
def test_unsupported_status_is_named(status):
    with pytest.raises(ValueError, match="Unsupported filing status") as error:
        section86_inclusions(0, 0, status)
    assert repr(status) in str(error.value)


def test_separate_lived_together_is_refused_by_name():
    with pytest.raises(ValueError, match="SEPARATE.*lived together"):
        section86_inclusions(
            20000, 30000, "SEPARATE", lived_apart_all_year=False
        )


@pytest.mark.parametrize("declaration", [None, 1, "yes"])
def test_separate_requires_explicit_lived_apart_declaration(declaration):
    with pytest.raises(ValueError, match="lived_apart_all_year=True"):
        section86_inclusions(
            20000, 30000, "SEPARATE", lived_apart_all_year=declaration
        )


@pytest.mark.parametrize(
    "benefits", [-1, "-0.01", "NaN", "Infinity", "-Infinity", "bad", None]
)
def test_invalid_benefits_are_refused(benefits):
    with pytest.raises(ValueError, match="benefits must be"):
        section86_inclusions(benefits, 0, "SINGLE")


@pytest.mark.parametrize(
    "modified_agi", ["NaN", "Infinity", "-Infinity", "bad", None]
)
def test_invalid_modified_agi_is_refused(modified_agi):
    with pytest.raises(
        ValueError,
        match="modified_adjusted_gross_income must be finite|"
        "modified_adjusted_gross_income must be a finite",
    ):
        section86_inclusions(0, modified_agi, "SINGLE")


def test_exact_decimals_and_caller_context():
    expected = section86_inclusions("20000.02", "30000.03", "SINGLE")
    with localcontext() as context:
        context.prec = 4
        result = section86_inclusions(20000.02, 30000.03, "SINGLE")
    assert result == expected
    assert result.pre_1993 == Decimal("7500.020")
    assert result.current == Decimal("9600.0340")


def test_small_benefit_cap_near_upper_threshold():
    # Combined income $34,100: min(85, .85 * 100 + min(50, 4500))
    # is $85. Paragraph (1) remains the full $50 half-benefit cap.
    result = section86_inclusions(100, 34050, "SINGLE")
    assert result.pre_1993 == Decimal("50")
    assert result.current == Decimal("85")


_BENEFITS = st.decimals(
    min_value="0", max_value="1000000", places=2, allow_nan=False
)
_MODIFIED_AGI = st.decimals(
    min_value="-1000000", max_value="1000000", places=2, allow_nan=False
)
_STATUSES = st.sampled_from(
    ["SINGLE", "JOINT", "HEAD_OF_HOUSEHOLD", "SEPARATE"]
)


@given(benefits=_BENEFITS, modified_agi=_MODIFIED_AGI, status=_STATUSES)
@settings(deadline=None)
def test_statutory_bounds_and_determinism(benefits, modified_agi, status):
    result = section86_inclusions(
        benefits, modified_agi, status, lived_apart_all_year=True
    )
    assert 0 <= result.pre_1993 <= result.current <= Decimal("0.85") * benefits
    assert result == section86_inclusions(
        benefits, modified_agi, status, lived_apart_all_year=True
    )


@given(modified_agi=_MODIFIED_AGI, status=_STATUSES)
@settings(deadline=None)
def test_zero_benefits(modified_agi, status):
    result = section86_inclusions(
        0, modified_agi, status, lived_apart_all_year=True
    )
    assert result.pre_1993 == result.current == 0


@given(benefits=_BENEFITS, modified_agi=_MODIFIED_AGI, status=_STATUSES)
@settings(deadline=None)
def test_below_adjusted_base_current_equals_paragraph_one(
    benefits, modified_agi, status
):
    adjusted_base = Decimal("44000" if status == "JOINT" else "34000")
    result = section86_inclusions(
        benefits, modified_agi, status, lived_apart_all_year=True
    )
    if result.combined_income <= adjusted_base:
        assert result.current == result.pre_1993
