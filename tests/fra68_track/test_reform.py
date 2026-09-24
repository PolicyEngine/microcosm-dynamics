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


def _spouse_factor(months_early, params):
    return 1 - benefits.spousal_early_reduction(months_early, params)


@pytest.mark.parametrize(
    ("birth", "increase", "moved_month", "entitled", "whole_year_factor"),
    [
        # E1 section 19 (referee required change 1): the spouse's own
        # claim at 62 starts the excess; C2 moves it by D months.
        (1951, 7, 751, 2014, 0.720833),
        (1954, 13, 757, 2017, 0.695833),
    ],
)
def test_a_moved_spouse_excess_keeps_its_months_early(
    base, reforms, birth, increase, moved_month, entitled, whole_year_factor
):
    p3 = reforms["P3"]
    assert p3.fra_months(birth) - base.fra_months(birth) == increase
    claim_month = 12 * 62 + increase
    assert claim_month == moved_month
    # A4's July birth month: the moved claim falls in the next year.
    assert birth + (6 + claim_month) // 12 == entitled
    # The worker was entitled earlier, so the spouse's own claim starts
    # the excess in both scenarios.
    worker_year = birth + 60
    baseline = reform.spouse_excess_months_early(
        own_claim_month=12 * 62,
        worker_entitlement_year=worker_year,
        birth_year=birth,
        params=base,
    )
    moved = reform.spouse_excess_months_early(
        own_claim_month=claim_month,
        worker_entitlement_year=worker_year,
        birth_year=birth,
        params=p3,
    )
    assert baseline == moved == 48
    assert _spouse_factor(baseline, base) == pytest.approx(0.70)
    assert _spouse_factor(moved, p3) == pytest.approx(0.70)
    # The rule it replaces counted from the whole moved year (Track A's
    # count on the reform bundle), which changed the reduction by
    # D - 12 months with no response behind it.
    whole_year = max(0, p3.fra_months(birth) - 12 * (entitled - birth))
    assert whole_year == 48 - (12 - increase)
    assert _spouse_factor(whole_year, p3) == pytest.approx(
        whole_year_factor, abs=1e-6
    )


def test_the_spouse_excess_rule_is_track_as_without_a_moved_claim(base):
    # Null-reform identity: with an unmoved claim (12 times the claim
    # year minus the birth year) the rule is Track A's whole-year count,
    # FRA - 12 (max(own claim year, worker entitlement year) - birth).
    for birth in range(1938, 1972):
        for claim_year in range(birth + 62, birth + 72):
            for worker_year in range(birth + 55, birth + 75):
                track_a = max(
                    0,
                    base.fra_months(birth)
                    - 12 * (max(claim_year, worker_year) - birth),
                )
                assert (
                    reform.spouse_excess_months_early(
                        own_claim_month=12 * (claim_year - birth),
                        worker_entitlement_year=worker_year,
                        birth_year=birth,
                        params=base,
                    )
                    == track_a
                )
    # A worker entitled after the moved claim starts the excess at the
    # whole year, as in Track A.
    assert (
        reform.spouse_excess_months_early(
            own_claim_month=751,
            worker_entitlement_year=2016,
            birth_year=1951,
            params=base,
        )
        == 792 - 12 * 65
    )


def _moved_claim(age, increase):
    """INVENTED C1/C2 move of a claim at integer age ``age`` (E1 s. 13).

    Returns the reform claim month ``min(12 a + D, 840)``, the year shift
    under A4's July birth month and the months moved.
    """

    age = min(age, 70)
    if increase <= 0:
        return 12 * age, 0, 0
    month = min(12 * age + increase, 840)
    return month, (6 + month) // 12 - age, month - 12 * age


def test_a_moved_worker_claim_starts_the_excess_at_its_exact_month(
    base, reforms
):
    # The review of e1-draft-5: when C1 or C2 moved the worker's claim and
    # the worker's entitlement starts the spouse's excess, the spouse's
    # reduction starts the month the moved entitlement does.  402(b)(1)
    # (usc42_402.txt line 58) entitles a wife only as the wife of an
    # individual entitled to old-age benefits, and the reduction period
    # starts with her first month of entitlement (402(q)(5)(C), (6)(A)(ii);
    # lines 399 and 404).  Independent check: calendar months, both
    # spouses born in July (A4), the worker claiming at month m'_w of age.
    for sid, params in reforms.items():
        for spouse_birth in range(1946, 1967):
            spouse_increase = params.fra_months(
                spouse_birth
            ) - base.fra_months(spouse_birth)
            for spouse_age in (62, 63, 64):
                for worker_birth in range(1944, 1967):
                    worker_increase = params.fra_months(
                        worker_birth
                    ) - base.fra_months(worker_birth)
                    for worker_age in range(62, 71):
                        worker_year = worker_birth + worker_age
                        month, shift, moved = _moved_claim(
                            worker_age, worker_increase
                        )
                        # Calendar month index of the worker's moved
                        # claim, minus the spouse's birth month index.
                        spouse_age_at_worker = (
                            12 * worker_birth + 6 + month
                        ) - (12 * spouse_birth + 6)
                        for own_month in (
                            12 * spouse_age,
                            _moved_claim(spouse_age, spouse_increase)[0],
                        ):
                            exact = max(
                                0,
                                params.fra_months(spouse_birth)
                                - max(own_month, spouse_age_at_worker),
                            )
                            assert (
                                reform.spouse_excess_months_early(
                                    own_claim_month=own_month,
                                    worker_entitlement_year=worker_year,
                                    birth_year=spouse_birth,
                                    params=params,
                                    worker_claim_move_months=moved,
                                )
                                == exact
                            ), (sid, spouse_birth, worker_birth, worker_age)
                        assert (
                            worker_year + shift
                            == worker_birth + (6 + month) // 12
                        )
    # A negative move is refused.
    with pytest.raises(ValueError, match="negative"):
        reform.spouse_excess_months_early(
            own_claim_month=744,
            worker_entitlement_year=2016,
            birth_year=1953,
            params=base,
            worker_claim_move_months=-1,
        )


@pytest.mark.parametrize(
    (
        "spouse_birth",
        "worker_birth",
        "worker_age",
        "baseline",
        "exact",
        "whole_year",
    ),
    [
        # E1 section 19: P3, D(1953) = 11, D(1951) = 7.  The worker's
        # claim at 65 in 2016 moves 7 months (month 787, entitled 2017);
        # the spouse, who claimed at 62 in 2015, is 756 + 7 = 763 months
        # old when the worker's moved entitlement starts: 803 - 763 = 40
        # months early.  The whole moved year counted 803 - 768 = 35,
        # fewer than the baseline's 36: a rise the worker's 7-month delay
        # does not give.
        (1953, 1951, 65, 36, 40, 35),
        # P3, D(1954) = 13, D(1953) = 11: the worker claims at 65 in 2018
        # and moves 11 months.  Exact 805 - (768 + 11) = 26; whole year
        # 805 - 780 = 25; baseline 792 - 768 = 24.
        (1954, 1953, 65, 24, 26, 25),
        # P3, D(1950) = 6, D(1948) = 2: the worker's claim at 65 in 2013
        # moves 2 months within the year.  Exact 798 - (756 + 2) = 40; the
        # whole year (unchanged) counted 798 - 756 = 42.
        (1950, 1948, 65, 36, 40, 42),
    ],
)
def test_a_moved_worker_claim_cases(
    base,
    reforms,
    spouse_birth,
    worker_birth,
    worker_age,
    baseline,
    exact,
    whole_year,
):
    p3 = reforms["P3"]
    worker_year = worker_birth + worker_age
    increase = p3.fra_months(worker_birth) - base.fra_months(worker_birth)
    month, shift, moved = _moved_claim(worker_age, increase)
    assert moved == increase
    own_month = 12 * 62
    assert (
        reform.spouse_excess_months_early(
            own_claim_month=own_month,
            worker_entitlement_year=worker_year,
            birth_year=spouse_birth,
            params=base,
        )
        == baseline
    )
    assert (
        reform.spouse_excess_months_early(
            own_claim_month=own_month,
            worker_entitlement_year=worker_year,
            birth_year=spouse_birth,
            params=p3,
            worker_claim_move_months=moved,
        )
        == exact
    )
    # The rule it replaces: the whole year the moved claim falls in.
    assert (
        reform.spouse_excess_months_early(
            own_claim_month=own_month,
            worker_entitlement_year=worker_year + shift,
            birth_year=spouse_birth,
            params=p3,
        )
        == whole_year
    )


#: The cohort classes whose conversion-claim count 070c59c7's rule (the
#: scenario's own whole conversion year) changed, by (birth year,
#: schedule): its months early minus the baseline's, when the conversion
#: starts the excess (the review of ``e1-draft-4``; E1 section 25).  The
#: review listed 1948 (P3), 1949 (P1, P3), 1954-1956 (P2, P3); the full
#: grid below adds 1948 and 1949 under P2 and 1950 under P1.
OLD_CONVERSION_RULE_SHIFT = {
    (1948, "P2"): 2,
    (1948, "P3"): 2,
    (1949, "P1"): 2,
    (1949, "P2"): 4,
    (1949, "P3"): 4,
    (1950, "P1"): 4,
    (1954, "P2"): 2,
    (1954, "P3"): 1,
    (1955, "P2"): 2,
    (1955, "P3"): 1,
    (1956, "P2"): -4,
    (1956, "P3"): 1,
}


def _conversion_year(birth, params):
    return int(fra_attainment_year(np.array([birth]), params)[0])


def test_a_conversion_claim_keeps_track_as_baseline_count(base, reforms):
    # 42 USC 402(q)(1) (usc42_402.txt line 371): a spouse's benefit is
    # reduced only when its first month of entitlement precedes the month
    # of attaining retirement age.  A converted worker's excess starts at
    # the conversion (at FRA) or later, so the statute's count is 0 in
    # both scenarios and the reform ratio is 1.  The rule keeps Track A's
    # baseline count (a whole-year artifact) in every scenario.
    shifts = {}
    for birth in range(1938, 1972):
        conversion = _conversion_year(birth, base)
        for worker_year in range(conversion - 12, conversion + 4):
            track_a = max(
                0,
                base.fra_months(birth)
                - 12 * (max(conversion, worker_year) - birth),
            )
            # Null reform: the baseline bundle gives Track A's count.
            assert (
                reform.conversion_claim_excess_months_early(
                    conversion_claim_year=conversion,
                    worker_entitlement_year=worker_year,
                    birth_year=birth,
                    baseline=base,
                    params=base,
                )
                == track_a
            )
            for sid, params in reforms.items():
                count = reform.conversion_claim_excess_months_early(
                    conversion_claim_year=conversion,
                    worker_entitlement_year=worker_year,
                    birth_year=birth,
                    baseline=base,
                    params=params,
                )
                assert count == track_a, (birth, sid, worker_year)
                increase = params.fra_months(birth) - base.fra_months(birth)
                device = reform.spouse_excess_months_early(
                    own_claim_month=12 * (conversion - birth) + increase,
                    worker_entitlement_year=worker_year,
                    birth_year=birth,
                    params=params,
                )
                if worker_year <= conversion:
                    # The conversion starts the excess: the conversion
                    # claim moved by exactly D months (the C1/C2 device).
                    assert count == device, (birth, sid, worker_year)
                    old = max(
                        0,
                        params.fra_months(birth)
                        - 12 * (_conversion_year(birth, params) - birth),
                    )
                    if old != track_a:
                        shifts[(birth, sid)] = old - track_a
                elif device != count:
                    # The worker's later entitlement starts the baseline
                    # excess (count 0); moving the conversion claim alone
                    # would count FRA mod 12 months, 2 or 4.
                    assert worker_year == conversion + 1
                    assert (birth, count, device) in {
                        (1955, 0, 2),
                        (1956, 0, 4),
                    }, (birth, sid)
    assert shifts == OLD_CONVERSION_RULE_SHIFT


def test_track_as_whole_year_conversion_count(base):
    # The named delta of E1 section 12: with A4's July birth month the
    # conversion year stands for month 12 (b + (6 + FRA) // 12 - b), which
    # is FRA mod 12 months before the FRA when that is below 6.  Under the
    # statute's schedule that is 2 months for 1938 and 1955 and 4 for 1939
    # and 1956; of these, only 1955 and 1956 convert after 2008, the
    # earlier opening year (row F8), so only they can convert in a
    # projection.
    positive = {}
    for birth in range(1900, 2000):
        conversion = _conversion_year(birth, base)
        count = reform.conversion_claim_excess_months_early(
            conversion_claim_year=conversion,
            worker_entitlement_year=conversion - 5,
            birth_year=birth,
            baseline=base,
            params=base,
        )
        assert count == max(
            0, base.fra_months(birth) - 12 * (conversion - birth)
        )
        if count:
            positive[birth] = (count, conversion)
    assert positive == {
        1938: (2, 2003),
        1939: (4, 2004),
        1955: (2, 2021),
        1956: (4, 2022),
    }


def test_the_1956_spouse_under_p2_keeps_its_factor(base, reforms):
    # The review's probe case: a converted spouse born 1956 whose
    # conversion starts the excess.  The baseline counts 796 - 792 = 4
    # months early (factor 1 - 4 x 25/36 percent); 070c59c7's rule counted
    # none under P2 (conversion in 2024 at month 816, FRA 810), raising the
    # excess above the baseline and above P3.  Now every scenario counts 4.
    birth, conversion = 1956, 2022
    assert _conversion_year(birth, base) == conversion
    assert _conversion_year(birth, reforms["P2"]) == 2024
    assert _conversion_year(birth, reforms["P3"]) == 2023
    factors = {}
    for sid, params in {"baseline": base, **reforms}.items():
        months = reform.conversion_claim_excess_months_early(
            conversion_claim_year=conversion,
            worker_entitlement_year=2010,
            birth_year=birth,
            baseline=base,
            params=params,
        )
        assert months == 4, sid
        factors[sid] = _spouse_factor(months, params)
    assert factors["baseline"] == pytest.approx(1 - 4 * 25 / 3600)
    assert factors["P2"] == factors["P3"] == factors["P1"]
    assert factors["P1"] == factors["baseline"]
    old_p2 = _spouse_factor(0, reforms["P2"])
    assert 100 * (old_p2 / factors["baseline"] - 1) == pytest.approx(
        2.857143, abs=1e-6
    )


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
