"""The exercise-3 reform switch: schedules, guards and worked cases.

Every PIA amount below is INVENTED ($1,000.00, $1,500.00, $2,000.00); the
rates are the committed statutory capture's
(``data/external/track_a_statutory_parameters.json`` through
``cola_track_a.statutory.captured_ssa_parameters``) and the COLA path is
the A1 section 21 TR2008 path.  No PSID value, model output or comparator
value is read.  Expected values are transcribed from the plan
(``critical-path-fra68-20260923.md`` sections 3, 4 and 7), which computed
them from the statute's fractions; the E1 specification (section 19)
carries the same table.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

import numpy as np
import pytest

from populace_dynamics import claiming
from populace_dynamics import scenario_benefits as sb
from populace_dynamics.cola_track_a.runner import a1_parameter_block
from populace_dynamics.cola_track_a.statutory import captured_ssa_parameters
from populace_dynamics.engine.di_entitlement import fra_attainment_year
from populace_dynamics.fra68_track import reform
from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    FRASchedule,
    opening_stock_factor_ratio,
    reform_parameters,
    spouse_age_factor,
    survivor_parameters,
    survivor_retirement_age_months,
    worker_factor_ratio,
)
from populace_dynamics.ss import benefits

#: Plan section 3 table: FRA in months by year turning 62 (birth + 62).
PLAN_TABLE = {
    # Y: (baseline, P1, P2, P3)
    2009: (792, 792, 792, 792),
    2010: (792, 792, 794, 794),
    2011: (792, 794, 796, 796),
    2012: (792, 796, 798, 798),
    2013: (792, 798, 800, 799),
    2014: (792, 800, 802, 801),
    2015: (792, 802, 804, 803),
    2016: (792, 804, 806, 805),
    2017: (794, 806, 808, 807),
    2018: (796, 808, 810, 809),
    2019: (798, 810, 812, 810),
    2020: (800, 812, 814, 812),
    2021: (802, 814, 816, 814),
    2022: (804, 816, 816, 816),
}


@pytest.fixture(scope="module")
def base():
    return captured_ssa_parameters()


@pytest.fixture(scope="module")
def reforms(base):
    return {sid: reform_parameters(base, s) for sid, s in SCHEDULES.items()}


class _A1Path:
    """The A1 section 21 TR2008 rate path (determination years 2008-2030)."""

    def __init__(self) -> None:
        block = a1_parameter_block()
        self.rates = {
            int(year): float(value) / 100.0
            for year, value in block["rate_path"]["baseline"].items()
        }

    def rate_for_determination_year(self, year: int) -> float:
        return self.rates[year]


@pytest.fixture(scope="module")
def cola():
    return _A1Path()


# --------------------------------------------------------------------------
# Schedules
# --------------------------------------------------------------------------
def test_schedules_are_the_plans_section_3_table(base, reforms):
    for year, (baseline, *values) in PLAN_TABLE.items():
        birth = year - 62
        assert base.fra_months(birth) == baseline
        for sid, expected in zip(("P1", "P2", "P3"), values, strict=True):
            assert reforms[sid].fra_months(birth) == expected, (sid, year)


def test_p3_is_the_nearest_whole_month_with_no_tie():
    for year in range(2010, 2022):
        exact = Fraction(24 * (year - 2009), 13)
        assert exact.denominator == 13
        assert exact - int(exact) != Fraction(1, 2)
        nearest = int(exact + Fraction(1, 2))
        assert (
            SCHEDULES["P3"].months_for_year_turning_62(year) == 792 + nearest
        )


def test_every_schedule_meets_table_1_endpoints(base, reforms):
    for params in reforms.values():
        for birth in range(1960, 2031):
            assert params.fra_months(birth) == 816
        for birth in range(1900, 1948):
            assert params.fra_months(birth) == base.fra_months(birth)
        for birth in range(1900, 2031):
            assert params.fra_months(birth) >= base.fra_months(birth)
    # The first affected cohort: 2010 (P2, P3) or 2011 (P1).
    assert reforms["P1"].fra_months(1948) == 792
    assert reforms["P2"].fra_months(1948) == 794
    assert reforms["P3"].fra_months(1948) == 794


def test_the_override_changes_the_fra_schedule_only(base, reforms):
    for params in reforms.values():
        for item in dataclasses.fields(base):
            if item.name in ("fra_months_by_birth_year", "pe_us_revision"):
                continue
            assert getattr(params, item.name) == getattr(base, item.name)
        assert params.pe_us_revision.startswith(base.pe_us_revision + "+")


def test_schedule_records_are_canonical_and_hashed():
    digests = {sid: s.sha256() for sid, s in SCHEDULES.items()}
    assert len(set(digests.values())) == 3
    record = SCHEDULES["P3"].as_dict()
    assert record["months_by_year_turning_62"]["2013"] == 799
    assert record["months_from_year_turning_62"] == {"2022": 816}
    assert SCHEDULES["P3"].months_for_year_turning_62(2009) is None
    assert SCHEDULES["P3"].months_for_year_turning_62(2040) == 816


@pytest.mark.parametrize(
    ("table", "match"),
    [
        ({year: 800 for year in range(2010, 2022)}, "every year"),
        (
            {**{year: 800 for year in range(2010, 2022)}, 2022: 810},
            "68 for those",
        ),
        (
            {
                **{year: 800 for year in range(2010, 2022)},
                2010: 790,
                2022: 816,
            },
            "between 66 and 68",
        ),
        (
            {
                **{year: 806 for year in range(2010, 2022)},
                2015: 800,
                2022: 816,
            },
            "must not fall",
        ),
    ],
)
def test_malformed_schedules_are_refused(table, match):
    with pytest.raises(ValueError, match=match):
        FRASchedule("X", "invented", table)


def test_a_reform_below_the_baseline_is_refused(base):
    # INVENTED baseline whose FRA is already 67 for the 1948 cohort.
    high = dataclasses.replace(
        base, fra_months_by_birth_year=[(1900, 780), (1948, 804)]
    )
    with pytest.raises(ValueError, match="below the baseline"):
        reform_parameters(high, SCHEDULES["P3"])


def test_a_reform_that_changes_nothing_is_refused(base):
    already = dataclasses.replace(
        base, fra_months_by_birth_year=[(1900, 780), (1943, 816)]
    )
    with pytest.raises(ValueError):
        reform_parameters(already, SCHEDULES["P1"])


# --------------------------------------------------------------------------
# Survivors (416(l)(2) mapping)
# --------------------------------------------------------------------------
def test_survivor_retirement_age_is_the_worker_schedule_two_cohorts_earlier(
    base, reforms
):
    for birth in range(1962, 2000):
        assert survivor_retirement_age_months(base, birth) == 804
    assert survivor_retirement_age_months(reforms["P3"], 1950) == 794
    assert survivor_retirement_age_months(reforms["P3"], 1962) == 816
    assert survivor_retirement_age_months(base, 1961) == 802
    # The span the oracle reads: retirement age minus 60 years.
    assert survivor_parameters(
        base, 1961
    ).survivor_reduction_period_months == (82)
    assert survivor_parameters(
        reforms["P3"], 1965
    ).survivor_reduction_period_months == (96)
    # F7: the reform bundle with survivors on the baseline schedule.
    unchanged = survivor_parameters(reforms["P3"], 1965, schedule=base)
    assert unchanged.survivor_reduction_period_months == 84
    assert unchanged.fra_months(1965) == 816
    # The oracle's 84-month default is exact from 1962: no new bundle.
    assert survivor_parameters(base, 1970) is base


# --------------------------------------------------------------------------
# Plan section 4 arithmetic, through the oracle
# --------------------------------------------------------------------------
def test_worker_factor_change_for_a_twelve_month_increase(base, reforms):
    expected = [-7.14, -6.67, -6.25, -7.69, -7.14, -6.67, -7.41, -6.90, -6.45]
    observed = [
        round(
            100
            * (worker_factor_ratio(12 * age, 1966, base, reforms["P3"]) - 1),
            2,
        )
        for age in range(62, 71)
    ]
    assert observed == expected
    # Maximum reductions and credits.
    assert claiming.benefit_factor(744, 1960, base) == pytest.approx(
        0.70, abs=1e-6
    )
    assert claiming.benefit_factor(744, 1960, reforms["P3"]) == pytest.approx(
        0.65, abs=1e-6
    )
    assert claiming.benefit_factor(840, 1960, base) == pytest.approx(1.24)
    assert claiming.benefit_factor(840, 1960, reforms["P3"]) == pytest.approx(
        1.16
    )


#: Plan section 4, phase-in cohorts: change at claim age 62 / 65 (%).
PHASE_IN = {
    1948: {"P1": (0.0, 0.0), "P2": (-1.11, -1.19), "P3": (-1.11, -1.19)},
    1949: {"P1": (-1.11, -1.19), "P2": (-2.22, -2.38), "P3": (-2.22, -2.38)},
    1950: {"P1": (-2.22, -2.38), "P2": (-3.33, -3.57), "P3": (-3.33, -3.57)},
    1951: {"P1": (-3.33, -3.57), "P2": (-4.44, -4.76), "P3": (-3.89, -4.17)},
    1952: {"P1": (-4.44, -4.76), "P2": (-5.56, -5.95), "P3": (-5.00, -5.36)},
    1953: {"P1": (-5.56, -5.95), "P2": (-6.67, -7.14), "P3": (-6.11, -6.55)},
    1954: {"P1": (-6.67, -7.14), "P2": (-7.78, -8.33), "P3": (-7.22, -7.74)},
}


def test_phase_in_cohort_factor_changes(base, reforms):
    for birth, by_schedule in PHASE_IN.items():
        for sid, (at_62, at_65) in by_schedule.items():
            observed = tuple(
                round(
                    100
                    * (
                        worker_factor_ratio(months, birth, base, reforms[sid])
                        - 1
                    ),
                    2,
                )
                + 0.0
                for months in (744, 780)
            )
            assert observed == (at_62, at_65), (birth, sid)


def test_spouse_and_widow_factor_changes(base, reforms):
    p3 = reforms["P3"]
    spouse = [
        round(
            100
            * (
                spouse_age_factor(12 * age, 1966, p3)
                / spouse_age_factor(12 * age, 1966, base)
                - 1
            ),
            2,
        )
        + 0.0
        for age in range(62, 69)
    ]
    assert spouse == [-7.69, -7.14, -6.67, -10.0, -9.09, -8.33, 0.0]
    widow = []
    for age in range(60, 69):
        factors = []
        for params in (base, p3):
            bundle = survivor_parameters(params, 1965)
            early = max(
                0, bundle.survivor_reduction_period_months - 12 * (age - 60)
            )
            factors.append(1 - benefits.survivor_reduction(early, bundle))
        widow.append(round(100 * (factors[1] / factors[0] - 1), 2) + 0.0)
    assert widow == [0.0, -0.67, -1.28, -1.82, -2.32, -2.77, -3.18, -3.56, 0.0]


def test_conversion_moves_from_67_to_68(base, reforms):
    births = np.array([1958, 1960, 1966])
    # A4's July birth month: birth year + (6 + FRA months) // 12.
    assert list(fra_attainment_year(births, base)) == [2025, 2027, 2033]
    assert list(fra_attainment_year(births, reforms["P3"])) == [
        2026,
        2028,
        2034,
    ]


# --------------------------------------------------------------------------
# Plan section 7 / E1 section 19 worked cases (INVENTED amounts)
# --------------------------------------------------------------------------
def _worker(cola, birth, age, params, pia=1000.0):
    factor = claiming.benefit_factor(12 * age, birth, params)
    amount = sb.monthly_benefit_path(
        eligibility_pia=pia,
        claim_age_factor=factor,
        eligibility_year=birth + 62,
        cola=cola,
        horizon_year=2030,
    )[2030]
    return amount, factor


def _pct(new, old):
    return round(100 * (new / old - 1), 4) + 0.0


@pytest.mark.parametrize(
    ("birth", "age", "sid", "baseline", "reformed", "change", "unrounded"),
    [
        (1966, 62, "P3", 739.60, 686.80, -7.1390, -7.1429),
        (1963, 67, "P3", 1147.80, 1071.20, -6.6736, -6.6667),
        (1954, 66, "P1", 1471.10, 1373.00, -6.6685, -6.6667),
        (1954, 66, "P2", 1471.10, 1356.60, -7.7833, -7.7778),
        (1954, 66, "P3", 1471.10, 1364.80, -7.2259, -7.2222),
        (1950, 62, "P1", 1232.00, 1204.60, -2.2240, -2.2222),
        (1950, 62, "P2", 1232.00, 1190.90, -3.3360, -3.3333),
        (1950, 62, "P3", 1232.00, 1190.90, -3.3360, -3.3333),
    ],
)
def test_worked_cases_workers(
    base, reforms, cola, birth, age, sid, baseline, reformed, change, unrounded
):
    old, old_factor = _worker(cola, birth, age, base)
    new, new_factor = _worker(cola, birth, age, reforms[sid])
    assert (old, new) == (pytest.approx(baseline), pytest.approx(reformed))
    assert _pct(new, old) == change
    assert _pct(new_factor, old_factor) == unrounded


def test_worked_case_spouse(base, reforms, cola):
    worker = sb.increased_pia_path(
        eligibility_pia=2000.0,
        eligibility_year=2026,
        cola=cola,
        horizon_year=2030,
    )
    amounts = []
    for params in (base, reforms["P3"]):
        early = max(0, params.fra_months(1966) - 12 * 62)
        amounts.append(
            sb.spouse_excess_path(
                worker_pia_by_year=worker,
                own_pia_by_year=None,
                months_early=early,
                entitlement_year=2028,
                params=params,
                horizon_year=2030,
            )[2030]
        )
    assert amounts == [pytest.approx(725.80), pytest.approx(670.00)]
    assert _pct(amounts[1], amounts[0]) == -7.6881


@pytest.mark.parametrize(
    ("entitled_at", "baseline", "reformed", "change"),
    [(63, 1441.40, 1415.10, -1.8246), (60, 1231.10, 1231.10, 0.0)],
)
def test_worked_case_widow(
    base, reforms, cola, entitled_at, baseline, reformed, change
):
    deceased = sb.increased_pia_path(
        eligibility_pia=1500.0,
        eligibility_year=2025,
        cola=cola,
        horizon_year=2030,
    )
    amounts = []
    for params in (base, reforms["P3"]):
        bundle = survivor_parameters(params, 1965)
        early = max(
            0,
            bundle.survivor_reduction_period_months - 12 * (entitled_at - 60),
        )
        amounts.append(
            sb.widow_benefit_path(
                deceased_pia_by_year=deceased,
                own_amount_by_year=None,
                survivor_months_early=early,
                deceased_claim_age_factor=1.0,
                entitlement_year=1965 + entitled_at,
                params=bundle,
                horizon_year=2030,
            )[2030]
        )
    assert amounts == [pytest.approx(baseline), pytest.approx(reformed)]
    assert _pct(amounts[1], amounts[0]) == change


def test_worked_case_opening_stock_and_di(base, reforms):
    p3 = reforms["P3"]
    assert claiming.benefit_factor(744, 1948, base) == pytest.approx(
        0.75, abs=1e-6
    )
    assert claiming.benefit_factor(744, 1948, p3) == pytest.approx(
        0.741667, abs=1e-6
    )
    ratio = opening_stock_factor_ratio("retired_worker", 744, 1948, base, p3)
    assert round(100 * (ratio - 1), 4) == -1.1111
    spouse = opening_stock_factor_ratio("spouse", 744, 1948, base, p3)
    assert round(100 * (spouse - 1), 2) == -1.19
    # Every other record, a claim before 62 or an unknown age: ratio 1.
    for component in ("disabled_worker", "aged_widow", "disabled_widow"):
        assert (
            opening_stock_factor_ratio(component, 744, 1948, base, p3) == 1.0
        )
    assert opening_stock_factor_ratio("spouse", 700, 1948, base, p3) == 1.0
    assert (
        opening_stock_factor_ratio("retired_worker", None, 1948, base, p3)
        == 1.0
    )
    # A cohort the schedule does not reach: exactly 1.
    assert (
        opening_stock_factor_ratio("retired_worker", 744, 1947, base, p3)
        == 1.0
    )
    # P1 does not reach the 1948 cohort.
    assert (
        opening_stock_factor_ratio(
            "retired_worker", 744, 1948, base, reforms["P1"]
        )
        == 1.0
    )


def test_the_parameter_record_changes_with_the_schedule(base, reforms):
    digests = {
        reform.parameters_fra_sha256(params)
        for params in (base, *reforms.values())
    }
    assert len(digests) == 4
