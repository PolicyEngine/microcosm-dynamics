"""Statutory examples and properties; balances and owners are invented.

These tests read the pinned ``"data" / "external"`` RMD tables through
the rule API.
IRS examples retain their published dollar amounts; all other fixtures
are invented and contain no population observations.
"""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from populace_dynamics.income_resources.retirement_rules import (
    AccountType,
    Birth1959Rule,
    HistoricalJointTableReading,
    applicable_age,
    lifetime_rmd_exempt,
    required_beginning_date,
    required_minimum_distribution,
    rmd_divisor,
)


@pytest.mark.parametrize(
    "birth,expected",
    [
        (date(1949, 6, 30), 70.5),
        (date(1949, 7, 1), 72),
        (date(1950, 12, 31), 72),
        (date(1951, 1, 1), 73),
        (date(1958, 12, 31), 73),
        (date(1960, 1, 1), 75),
    ],
)
def test_regulatory_birth_cohorts(birth, expected):
    """26 CFR 1.401(a)(9)-2(b)(2)(ii)--(vi), TD 10001."""
    assert applicable_age(birth) == expected


def test_1959_requires_named_reading():
    """TD 10001 reserves (b)(2)(v); REG-103529-23 proposes 73."""
    with pytest.raises(ValueError, match="explicit"):
        applicable_age(date(1959, 1, 1))
    assert (
        applicable_age(
            date(1959, 1, 1), birth1959=Birth1959Rule.IRS_PROPOSED_73
        )
        == 73
    )
    assert (
        applicable_age(date(1959, 1, 1), birth1959=Birth1959Rule.STATUTORY_75)
        == 75
    )


@pytest.mark.parametrize(
    "birth,expected",
    [
        (date(1942, 6, 30), date(2013, 4, 1)),
        (date(1942, 7, 1), date(2014, 4, 1)),
        (date(1949, 7, 1), date(2022, 4, 1)),
        (date(1950, 12, 31), date(2023, 4, 1)),
        (date(1951, 1, 1), date(2025, 4, 1)),
        (date(1960, 1, 1), date(2036, 4, 1)),
    ],
)
def test_beginning_date_all_regimes(birth, expected):
    """IRC 401(a)(9)(C)(i); SECURE §114 and SECURE 2.0 §107."""
    assert required_beginning_date(birth, "traditional_ira") == expected


def test_employer_retirement_and_owner_rules():
    """IRC 401(a)(9)(C)(i)--(ii); current-employer exception."""
    invented_birth = date(1951, 8, 20)
    assert (
        required_beginning_date(
            invented_birth, "employer_plan", still_working=True
        )
        is None
    )
    assert required_beginning_date(
        invented_birth, "employer_plan", retirement_year=2030
    ) == date(2031, 4, 1)
    for keyword in ("five_percent_owner", "plan_requires_age_start"):
        assert required_beginning_date(
            invented_birth,
            "employer_plan",
            still_working=True,
            **{keyword: True},
        ) == date(2025, 4, 1)
    assert required_beginning_date(
        invented_birth, "traditional_ira", still_working=True
    ) == date(2025, 4, 1)


@pytest.mark.parametrize(
    "year,spouse,divisor,rounded",
    [
        (2014, 69, 22.9, 4367),
        (2014, 64, 23.6, 4237),
        (2026, 69, 24.6, 4065),
        (2026, 64, 25.3, 3953),
    ],
)
def test_irs_owner_examples(year, spouse, divisor, rounded):
    """Pub 590 (2013) p36 and Pub 590-B, 'Which Table Do You Use'.

    Both publications give the $100,000, age-75 examples, first with a
    sole spouse six years younger and then eleven years younger.
    The API leaves rounding to the caller; the IRS prints whole dollars.
    """
    result = required_minimum_distribution(
        100_000,
        75,
        year,
        "traditional_ira",
        birth_date=date(year - 75, 5, 1),
        spouse_age=spouse,
        sole_spouse_beneficiary=True,
    )
    assert result == 100_000 / divisor
    assert round(result) == rounded


def test_irs_2013_justin_example():
    """Pub 590 (2013) p40, 'More than minimum received', Justin."""
    assert (
        round(
            required_minimum_distribution(
                38_400,
                70,
                2013,
                "traditional_ira",
                birth_date=date(1943, 6, 15),
            )
        )
        == 1401
    )
    assert (
        round(
            required_minimum_distribution(
                34_800,
                71,
                2014,
                "traditional_ira",
                birth_date=date(1943, 6, 15),
            )
        )
        == 1313
    )


def test_ten_year_spouse_boundary():
    """26 CFR 1.401(a)(9)-5(d): spouse must be >10 years younger."""
    assert rmd_divisor(
        2026, 75, spouse_age=65, sole_spouse_beneficiary=True
    ) == rmd_divisor(2026, 75)
    assert rmd_divisor(
        2026, 75, spouse_age=64, sole_spouse_beneficiary=False
    ) == rmd_divisor(2026, 75)
    assert (
        rmd_divisor(2026, 75, spouse_age=64, sole_spouse_beneficiary=True)
        == 25.3
    )


def test_disputed_historical_joint_cell_requires_named_reading():
    """2020 CFR vol6 table4 vs Pub590 (2013) Appendix C, ages97/20."""
    invented_args = dict(
        year=2019, age=97, spouse_age=20, sole_spouse_beneficiary=True
    )
    with pytest.raises(ValueError, match="disputed"):
        rmd_divisor(**invented_args)
    assert (
        rmd_divisor(
            **invented_args,
            historical_joint_table_reading=HistoricalJointTableReading.CFR_LITERAL_60_3,
        )
        == 60.3
    )
    assert (
        rmd_divisor(
            **invented_args,
            historical_joint_table_reading=HistoricalJointTableReading.IRS_PUBLICATION_63_0,
        )
        == 63.0
    )
    with pytest.raises(ValueError, match="disputed"):
        required_minimum_distribution(
            100_000,
            account_type="traditional_ira",
            birth_date=date(1922, 1, 1),
            **invented_args,
        )


def test_literal_cfr_monotonicity_counterexample_is_explicit():
    """The captured CFR's sole covered adjacent-age reversal is explicit."""
    kwargs = dict(
        spouse_age=20,
        sole_spouse_beneficiary=True,
        historical_joint_table_reading="cfr_literal_60_3",
    )
    assert 1 / rmd_divisor(2019, 97, **kwargs) > 1 / rmd_divisor(
        2019, 98, **kwargs
    )


@pytest.mark.parametrize("year", [2009, 2020])
def test_statutory_waivers(year):
    """Pub L 110-458 §201 and CARES Act §2203 waive owner DC RMDs."""
    assert (
        required_minimum_distribution(
            100_000,
            80,
            year,
            "traditional_ira",
            birth_date=date(year - 80, 1, 1),
        )
        == 0
    )


def test_designated_roth_transition_preserves_2023_obligation():
    """SECURE 2.0 §325(b)(2) preserves unpaid first-2023 RMDs."""
    assert (
        required_minimum_distribution(
            100_000,
            73,
            2023,
            "designated_roth",
            birth_date=date(1950, 1, 1),
            retirement_year=2023,
        )
        > 0
    )
    assert (
        required_minimum_distribution(
            100_000,
            74,
            2024,
            "designated_roth",
            birth_date=date(1950, 1, 1),
            retirement_year=2023,
        )
        == 0
    )


@given(
    st.floats(min_value=0, max_value=1e15, allow_nan=False),
    st.integers(2003, 2100),
    st.integers(0, 120),
    st.sampled_from(list(AccountType)),
    st.integers(0, 120),
    st.booleans(),
)
def test_rmd_bounded_and_exempt(
    invented_balance, year, age, account, spouse, sole
):
    if account == AccountType.DESIGNATED_ROTH and year < 2006:
        with pytest.raises(ValueError):
            lifetime_rmd_exempt(year, account)
        return
    result = required_minimum_distribution(
        invented_balance,
        age,
        year,
        account,
        birth_date=date(year - age, 1, 1),
        retirement_year=year,
        birth1959="irs_proposed_73",
        spouse_age=spouse,
        sole_spouse_beneficiary=sole,
        historical_joint_table_reading="irs_publication_63_0",
    )
    assert 0 <= result <= invented_balance
    if lifetime_rmd_exempt(year, account):
        assert result == 0


@given(st.integers(1900, 2100), st.sampled_from(list(Birth1959Rule)))
def test_applicable_age_monotone(birth_year, reading):
    assert applicable_age(
        date(birth_year, 1, 1), birth1959=reading
    ) <= applicable_age(date(birth_year + 1, 1, 1), birth1959=reading)


@given(st.sampled_from([2019, 2022]), st.integers(70, 119))
def test_uniform_fraction_monotone(year, age):
    if year >= 2022 and age < 72:
        with pytest.raises(ValueError):
            rmd_divisor(year, age)
        return
    assert 1 / rmd_divisor(year, age) <= 1 / rmd_divisor(year, age + 1)


@given(
    st.sampled_from([2019, 2022]),
    st.integers(70, 119),
    st.integers(0, 58),
)
def test_joint_fraction_monotone(year, age, spouse):
    if year >= 2022 and age < 72:
        with pytest.raises(ValueError):
            rmd_divisor(
                year, age, spouse_age=spouse, sole_spouse_beneficiary=True
            )
        return
    assert 1 / rmd_divisor(
        year,
        age,
        spouse_age=spouse,
        sole_spouse_beneficiary=True,
        historical_joint_table_reading="irs_publication_63_0",
    ) <= 1 / rmd_divisor(
        year,
        age + 1,
        spouse_age=spouse,
        sole_spouse_beneficiary=True,
        historical_joint_table_reading="irs_publication_63_0",
    )


@given(st.integers(2003, 2100), st.integers(72, 120))
def test_balance_divisor_differential(year, age):
    """The direct table formula agrees with owner obligation when due."""
    invented_balance = 100_000
    result = required_minimum_distribution(
        invented_balance,
        age,
        year,
        "traditional_ira",
        birth_date=date(year - age, 1, 1),
        birth1959="irs_proposed_73",
    )
    beginning = required_beginning_date(
        date(year - age, 1, 1),
        "traditional_ira",
        birth1959="irs_proposed_73",
        distribution_year=year,
    )
    if year >= beginning.year - 1 and year not in (2009, 2020):
        assert result == invented_balance / rmd_divisor(year, age)
    else:
        assert result == 0


@pytest.mark.parametrize("year", [2002, 9999, True, 2022.0])
def test_year_refusals(year):
    for rule in (
        lambda: rmd_divisor(year, 75),
        lambda: lifetime_rmd_exempt(year, "roth_ira"),
    ):
        with pytest.raises(ValueError):
            rule()


@pytest.mark.parametrize("age", [-1, 121, True, 73.5, "75"])
def test_age_refusals(age):
    with pytest.raises(ValueError):
        rmd_divisor(2026, age)


@pytest.mark.parametrize("year,age", [(2021, 69), (2022, 71)])
def test_table_coverage_refusal(year, age):
    for spouse in (None, 0):
        with pytest.raises(ValueError):
            rmd_divisor(
                year,
                age,
                spouse_age=spouse,
                sole_spouse_beneficiary=spouse is not None,
            )


@pytest.mark.parametrize("account", ["inherited_ira", "457b", "", None])
def test_account_refusals(account):
    with pytest.raises(ValueError):
        lifetime_rmd_exempt(2026, account)


@pytest.mark.parametrize(
    "change",
    [
        {"prior_year_end_balance": -1},
        {"prior_year_end_balance": float("inf")},
        {"prior_year_end_balance": float("nan")},
        {"prior_year_end_balance": True},
        {"prior_year_end_balance": "100"},
        {"age": 74},
        {"birth_date": "1951-01-01"},
        {"birth_date": date(1799, 1, 1)},
        {"spouse_age": -1},
        {"sole_spouse_beneficiary": True},
        {"sole_spouse_beneficiary": 1},
        {"still_working": 1},
        {"five_percent_owner": 1},
        {"plan_requires_age_start": 1},
        {"retirement_year": 1900},
        {"still_working": True, "retirement_year": 2025},
        {"account_type": "employer_plan"},
        {"birth1959": "pick_73_silently"},
        {"historical_joint_table_reading": "silently_smooth"},
    ],
)
def test_rmd_invalid_arguments_refuse(change):
    invented = dict(
        prior_year_end_balance=100_000,
        age=75,
        year=2026,
        account_type="traditional_ira",
        birth_date=date(1951, 1, 1),
    )
    with pytest.raises(ValueError):
        required_minimum_distribution(**(invented | change))


def test_exemption_does_not_hide_invalid_inputs():
    with pytest.raises(ValueError):
        required_minimum_distribution(
            100,
            75,
            2026,
            "roth_ira",
            birth_date=date(1951, 1, 1),
            spouse_age=-1,
        )
