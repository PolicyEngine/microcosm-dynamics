"""Owner lifetime RMD rules, without fitted parameters or population data.

Invariants: RMDs lie between zero and the prior year-end balance; the
reciprocal divisor never falls with age within a table except for the
explicitly named, disputed literal-CFR cell at owner 97/spouse 20;
the IRS-publication reading restores monotonicity there; applicable age
never falls with birth year; lifetime-exempt accounts always owe zero;
unsupported years, ages, account types and unresolved choices raise.

Coverage: distribution years 2003 onward under the captured law, owner
ages 0--120, table owner ages 70--120 before 2022 (72--120 thereafter),
and Joint spouse ages 0--120. Beneficiary and
DB-annuity RMDs, special pre-1987 403(b) balances and QLAC adjustments
are outside coverage: callers must supply an ordinary DC/IRA balance.
The result belongs to the distribution year, even when the first payment
is deferred to April 1 of the following year. It does not add that deferred
payment to the following year's obligation. See the versioned research
note for the 2017--2023 holdout history and the unresolved 1959 cohort.

Sources: 26 USC 401(a)(9)(C), (I); SECURE Act section 114; SECURE 2.0
sections 107 and 325; 26 CFR 1.401(a)(9)-9 (TD 8987 and TD 9930).
"""

from __future__ import annotations

import calendar
import json
import math
from datetime import date
from enum import Enum
from functools import lru_cache
from pathlib import Path


class AccountType(str, Enum):
    """Ordinary owner-held DC accounts; inherited accounts are excluded."""

    TRADITIONAL_IRA = "traditional_ira"
    SIMPLE_IRA = "simple_ira"
    ROTH_IRA = "roth_ira"
    EMPLOYER_PLAN = "employer_plan"
    DESIGNATED_ROTH = "designated_roth"


class Birth1959Rule(str, Enum):
    """Unresolved overlap: proposed IRS interpretation and statutory rival."""

    IRS_PROPOSED_73 = "irs_proposed_73"
    STATUTORY_75 = "statutory_75"


class HistoricalJointTableReading(str, Enum):
    """Conflicting pre-2022 joint cell: CFR and IRS Publication 590."""

    CFR_LITERAL_60_3 = "cfr_literal_60_3"
    IRS_PUBLICATION_63_0 = "irs_publication_63_0"


def _integer(value: int, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def _flag(value: bool, name: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name} must be bool")


def _dob(value: date) -> None:
    if type(value) is not date or not 1800 <= value.year <= 9878:
        raise ValueError("birth_date must be a date in 1800..9878")


def _add_months(value: date, months: int) -> date:
    year, month = divmod(value.year * 12 + value.month - 1 + months, 12)
    month += 1
    return date(
        year, month, min(value.day, calendar.monthrange(year, month)[1])
    )


def applicable_age(
    birth_date: date, *, birth1959: Birth1959Rule | str | None = None
) -> float:
    """Return 70.5, 72, 73 or 75; 1959 requires an explicit named reading.

    Current 26 CFR 1.401(a)(9)-2(b)(2)(v) remains reserved. Proposed
    REG-103529-23, 89 FR 58644 (2024), chooses 73. Neither choice here
    represents a final resolution of the statutory overlap.
    """
    _dob(birth_date)
    if birth1959 is not None:
        birth1959 = Birth1959Rule(birth1959)
    if birth_date < date(1949, 7, 1):
        return 70.5
    if birth_date.year <= 1950:
        return 72.0
    if birth_date.year <= 1958:
        return 73.0
    if birth_date.year == 1959:
        if birth1959 is None:
            raise ValueError("1959 birth requires an explicit Birth1959Rule")
        return 73.0 if birth1959 == Birth1959Rule.IRS_PROPOSED_73 else 75.0
    return 75.0


def lifetime_rmd_exempt(year: int, account_type: AccountType | str) -> bool:
    """Apply Roth IRA exemption and SECURE 2.0 section 325 from 2024."""
    _integer(year, "year", 2003, 9998)
    account = AccountType(account_type)
    if account == AccountType.DESIGNATED_ROTH and year < 2006:
        raise ValueError("designated Roth accounts begin in 2006")
    return account == AccountType.ROTH_IRA or (
        account == AccountType.DESIGNATED_ROTH and year >= 2024
    )


def required_beginning_date(
    birth_date: date,
    account_type: AccountType | str,
    *,
    retirement_year: int | None = None,
    still_working: bool = False,
    five_percent_owner: bool = False,
    plan_requires_age_start: bool = False,
    birth1959: Birth1959Rule | str | None = None,
    distribution_year: int = 2026,
) -> date | None:
    """Return statutory April 1, or None for exemption/continued work.

    Still working means with the employer maintaining this account, not
    another employer. A private employer plan may require an earlier age
    start; pass plan_requires_age_start=True when it does. The caller
    supplies five-percent-owner status for the statutory applicable year.
    """
    _dob(birth_date)
    for name, value in (
        ("still_working", still_working),
        ("five_percent_owner", five_percent_owner),
        ("plan_requires_age_start", plan_requires_age_start),
    ):
        _flag(value, name)
    if retirement_year is not None:
        _integer(retirement_year, "retirement_year", birth_date.year, 9998)
    if still_working and retirement_year is not None:
        raise ValueError("still_working conflicts with retirement_year")
    account = AccountType(account_type)
    exempt = lifetime_rmd_exempt(distribution_year, account)
    if birth1959 is not None:
        Birth1959Rule(birth1959)
    if exempt:
        return None
    age = applicable_age(birth_date, birth1959=birth1959)
    age_year = _add_months(birth_date, int(age * 12)).year
    employer = account in (
        AccountType.EMPLOYER_PLAN,
        AccountType.DESIGNATED_ROTH,
    )
    if employer and not five_percent_owner and not plan_requires_age_start:
        if still_working:
            return None
        if retirement_year is None:
            raise ValueError(
                "employer plan requires retirement_year or still_working"
            )
        age_year = max(age_year, retirement_year)
    return date(age_year + 1, 4, 1)


@lru_cache(maxsize=1)
def _tables() -> dict:
    path = (
        Path(__file__).resolve().parents[3]
        / "data/external/income_resources/retirement_rules_v1/rmd/parameters.json"
    )
    tables = json.loads(path.read_text())
    if tables.get("schema_version") != 1:
        raise ValueError("unsupported RMD parameter schema")
    return tables


def rmd_divisor(
    year: int,
    age: int,
    *,
    spouse_age: int | None = None,
    sole_spouse_beneficiary: bool = False,
    historical_joint_table_reading: (
        HistoricalJointTableReading | str | None
    ) = None,
) -> float:
    """Read the applicable Uniform or Joint and Last Survivor divisor.

    Ages are the ages attained on birthdays in the distribution year.
    Joint applies only if the spouse is sole beneficiary and more than
    ten years younger, using the regulation's calendar-age comparison.
    """
    _integer(year, "year", 2003, 9998)
    _integer(age, "age", 0, 120)
    _flag(sole_spouse_beneficiary, "sole_spouse_beneficiary")
    if spouse_age is not None:
        _integer(spouse_age, "spouse_age", 0, 120)
    if sole_spouse_beneficiary and spouse_age is None:
        raise ValueError("sole spouse beneficiary requires spouse_age")
    if historical_joint_table_reading is not None:
        historical_joint_table_reading = HistoricalJointTableReading(
            historical_joint_table_reading
        )
    minimum = 72 if year >= 2022 else 70
    if age < minimum:
        raise ValueError(
            f"covered owner table begins at age {minimum} for {year}"
        )
    table = _tables()["2022" if year >= 2022 else "2003"]
    if sole_spouse_beneficiary and age - spouse_age > 10:
        if year < 2022 and (age, spouse_age) == (97, 20):
            if historical_joint_table_reading is None:
                raise ValueError(
                    "disputed historical joint cell requires an explicit "
                    "HistoricalJointTableReading"
                )
            return _tables()["disputed_historical_joint_cell"][
                historical_joint_table_reading.value
            ]
        return table["joint"][str(age)][str(spouse_age)]
    return table["uniform"][str(age)]


def required_minimum_distribution(
    prior_year_end_balance: float,
    age: int,
    year: int,
    account_type: AccountType | str,
    *,
    birth_date: date,
    spouse_age: int | None = None,
    sole_spouse_beneficiary: bool = False,
    retirement_year: int | None = None,
    still_working: bool = False,
    five_percent_owner: bool = False,
    plan_requires_age_start: bool = False,
    birth1959: Birth1959Rule | str | None = None,
    historical_joint_table_reading: (
        HistoricalJointTableReading | str | None
    ) = None,
) -> float:
    """Compute the owner's distribution-year obligation without rounding.

    The 2009 and 2020 statutory DC/IRA waivers return zero. This function
    covers the obligation for the specified distribution year; the 2020
    waiver of unpaid first-2019 RMDs due April 2020 is a payment-timing
    matter and does not retroactively change the 2019 obligation here.
    """
    _integer(year, "year", 2003, 9998)
    _integer(age, "age", 0, 120)
    _dob(birth_date)
    if age != year - birth_date.year:
        raise ValueError(
            "age must equal birthday age in the distribution year"
        )
    if isinstance(prior_year_end_balance, bool) or not isinstance(
        prior_year_end_balance, (int, float)
    ):
        raise ValueError("balance must be a finite nonnegative number")
    if not math.isfinite(prior_year_end_balance) or prior_year_end_balance < 0:
        raise ValueError("balance must be a finite nonnegative number")
    # Validate even arguments that an exemption or waiver will render unused.
    _flag(sole_spouse_beneficiary, "sole_spouse_beneficiary")
    if spouse_age is not None:
        _integer(spouse_age, "spouse_age", 0, 120)
    if sole_spouse_beneficiary and spouse_age is None:
        raise ValueError("sole spouse beneficiary requires spouse_age")
    if historical_joint_table_reading is not None:
        HistoricalJointTableReading(historical_joint_table_reading)
    beginning = required_beginning_date(
        birth_date,
        account_type,
        retirement_year=retirement_year,
        still_working=still_working,
        five_percent_owner=five_percent_owner,
        plan_requires_age_start=plan_requires_age_start,
        birth1959=birth1959,
        distribution_year=year,
    )
    if beginning is None or year < beginning.year - 1 or year in (2009, 2020):
        return 0.0
    divisor = rmd_divisor(
        year,
        age,
        spouse_age=spouse_age,
        sole_spouse_beneficiary=sole_spouse_beneficiary,
        historical_joint_table_reading=historical_joint_table_reading,
    )
    return prior_year_end_balance / divisor
