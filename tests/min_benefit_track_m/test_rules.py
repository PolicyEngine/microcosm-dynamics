"""The Track M minimum-benefit rules on INVENTED data.

Every threshold, wage index, PIA and history here is **INVENTED**: no
Census value, PSID value, model output or comparator value.  The schedules
and cuts are Table 5's (cleared extract; ruling C1: policy inputs used as
printed).  Each expected number is computed by hand in the comment beside
it; the worked cases are the blind plan's INVENTED cases (revision 2,
section 7), which its author computed independently of this code.
"""

from __future__ import annotations

import math

import pytest

from populace_dynamics.min_benefit_track_m import policy as pol
from populace_dynamics.min_benefit_track_m import rules
from populace_dynamics.ss import benefits, statutory_aime
from populace_dynamics.ss.params import SSAParameters

#: INVENTED one-person aged threshold of $10,000 a year (plan section 1).
INVENTED_T = 10_000.0
THRESHOLDS = rules.AgedThresholds(
    {year: INVENTED_T for year in range(1990, 2031)}, {"kind": "INVENTED"}
)
#: INVENTED average wage index: 40,000 in 2002 rising 1,000 a year.
NAWI = {year: 40_000.0 + 1_000.0 * (year - 2002) for year in range(1951, 2031)}


def invented_params() -> SSAParameters:
    """INVENTED oracle parameters (4 percent wage growth from 1951)."""

    return SSAParameters(
        nawi={
            year: 2_800.0 * 1.04 ** (year - 1951) for year in range(1951, 2061)
        },
        wage_base={1937: 3_000.0, 1975: 14_100.0, 1990: 51_300.0},
        pia_factors=(0.9, 0.32, 0.15),
        fra_months_by_birth_year=[(1900, 792), (1955, 804)],
        early_monthly_rates=(5 / 900, 5 / 1200),
        early_first_bracket_months=36,
        pe_us_revision="INVENTED",
        delayed_credit_by_birth_year=[(1900, 0.08)],
    )


def worker(pia, years, *, onset=None, first=2010, threshold_year=2010):
    return rules.WorkerInputs(
        pia=pia,
        work_years=years,
        first_pia_year=first,
        threshold_year=threshold_year,
        birth_year=1948,
        di_onset_year=onset,
    )


def evaluate(record, option, **policy_changes):
    return rules.evaluate_worker(
        record,
        option,
        thresholds=THRESHOLDS,
        nawi=NAWI,
        policy=pol.TrackMPolicy(**policy_changes),
    )


# ---------------------------------------------------------------------------
# Table 5 schedules and cuts
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("years", "standard", "generous"),
    [
        (9, 0.0, 0.0),  # below the 10-year floor
        (10, 0.55, 0.80),
        (11, 0.565, 0.82),  # +1.5 points; +2.0 points
        (20, 0.70, 1.00),  # 0.55 + 10 x 0.015; 0.80 + 10 x 0.02
        (30, 0.85, 1.10),  # 0.55 + 20 x 0.015; 1.00 + 10 x 0.01
        (40, 1.00, 1.20),
        (45, 1.00, 1.20),  # held at 40
    ],
)
def test_schedules_follow_table_5(years, standard, generous):
    assert pol.STANDARD.share(years) == pytest.approx(standard)
    assert pol.GENEROUS.share(years) == pytest.approx(generous)


def test_options_carry_table_5_as_printed():
    assert {n: o.uniform_cut for n, o in pol.OPTIONS.items()} == {
        1: 0.1245,
        2: 0.1281,
        3: 0.1427,
        4: 0.1364,
        5: 0.1862,
    }
    assert pol.OPTIONS[1].schedule is None
    assert pol.OPTIONS[2].schedule is pol.OPTIONS[3].schedule is pol.STANDARD
    assert pol.OPTIONS[4].schedule is pol.OPTIONS[5].schedule is pol.GENEROUS
    assert [pol.OPTIONS[n].indexing for n in (2, 3, 4, 5)] == [
        "price",
        "wage",
        "price",
        "wage",
    ]


def test_schedule_rejects_malformed_points():
    with pytest.raises(ValueError):
        pol.Schedule("bad", ((20, 0.6), (10, 1.0)))
    with pytest.raises(ValueError):
        pol.Schedule("bad", ((10, 1.0), (20, 0.5)))
    with pytest.raises(ValueError):
        pol.STANDARD.share(math.nan)


# ---------------------------------------------------------------------------
# The plan's INVENTED worked cases (section 7), T = $10,000 a year
# ---------------------------------------------------------------------------
#: (case, P, Y, onset, M option 2, option 2 flag G10/MS2, option 4 flag
#: G10/MS2, option 2 benefit against option 1, in percent)
PLAN_CASES = [
    # A: M2 = 0.85 x 10,000 / 12 = 708.33 > 0.8719 x 600 = 523.14 and > 600.
    #    708.33 / (0.8755 x 600 = 525.30) - 1 = +34.84%.
    ("A", 600.0, 30, None, 708.33, (1, 1), (1, 1), 34.84),
    # B: 9 years, no minimum. 523.14 / 525.30 - 1 = -0.41%.
    ("B", 600.0, 9, None, 0.0, (0, 0), (0, 0), -0.41),
    # C: 833.33 > 0.8719 x 900 = 784.71 but not > 900: the cut moves the
    #    worker onto the minimum. 833.33 / 787.95 - 1 = +5.76%.
    ("C", 900.0, 40, None, 833.33, (1, 0), (1, 1), 5.76),
    # D: DI, 15 years of 22 possible: Y* = 15 x 40 / 22 = 27.27;
    #    M2 = (0.55 + 0.015 x 17.27) x 10,000 / 12 = 674.24.
    #    674.24 / (0.8755 x 500 = 437.75) - 1 = +54.02%.
    ("D", 500.0, 15, 1948 + 22 + 22, 674.24, (1, 1), (1, 1), 54.02),
    # H: 833.33 > 0.8719 x 953 = 830.92, yet 833.33 < 0.8755 x 953 = 834.35:
    #    on the minimum and worse off than under option 1 (fn. 33).
    ("H", 953.0, 40, None, 833.33, (1, 0), (1, 1), -0.12),
    # I: M2 = 583.33 < 0.8719 x 700 = 610.33; M4 = 833.33 > 0.8636 x 700.
    ("I", 700.0, 20, None, 583.33, (0, 0), (1, 1), -0.41),
]


@pytest.mark.parametrize(
    ("case", "pia", "years", "onset", "m2", "flag2", "flag4", "vs_option_1"),
    PLAN_CASES,
    ids=[case[0] for case in PLAN_CASES],
)
def test_plan_invented_cases(
    case, pia, years, onset, m2, flag2, flag4, vs_option_1
):
    record = worker(pia, years, onset=onset)
    primary2 = evaluate(record, 2)
    reverse2 = evaluate(record, 2, order=pol.ORDER_CUT_AFTER_FLOOR)
    primary4 = evaluate(record, 4)
    reverse4 = evaluate(record, 4, order=pol.ORDER_CUT_AFTER_FLOOR)
    option1 = evaluate(record, 1)
    assert round(primary2.minimum, 2) == m2
    assert (int(primary2.on_minimum), int(reverse2.on_minimum)) == flag2
    assert (int(primary4.on_minimum), int(reverse4.on_minimum)) == flag4
    relative = 100 * rules.relative_to_option_1(primary2, option1)
    assert round(relative, 2) == vs_option_1


def test_the_binding_bound_of_plan_section_1():
    # P < M / (1 - c): 833.33 / 0.8719 = 955.77 (option 2, Y = 40) and
    # 1,000 / 0.8636 = 1,157.94 (option 4, Y = 40).
    assert (INVENTED_T / 12) / (1 - 0.1281) == pytest.approx(955.77, abs=5e-3)
    assert (1.2 * INVENTED_T / 12) / (1 - 0.1364) == pytest.approx(
        1157.94, abs=5e-3
    )
    for option, bound in ((2, 955.77), (4, 1157.94)):
        assert evaluate(worker(bound - 0.01, 40), option).on_minimum
        assert not evaluate(worker(bound + 0.01, 40), option).on_minimum


def test_option_pia_under_each_order():
    record = worker(900.0, 40)
    # G10: max(0.8719 x 900 = 784.71, 833.33) = 833.33.
    assert evaluate(record, 2).option_pia == pytest.approx(833.3333)
    # MS2: max(900, 833.33) x 0.8719 = 784.71.
    reverse = evaluate(record, 2, order=pol.ORDER_CUT_AFTER_FLOOR)
    assert reverse.option_pia == pytest.approx(784.71)
    # Option 1: 0.8755 x 900 = 787.95, never a minimum.
    option1 = evaluate(record, 1)
    assert option1.option_pia == pytest.approx(787.95)
    assert option1.reason == "no_minimum_option"
    assert not option1.on_minimum


# ---------------------------------------------------------------------------
# Scope window (G4, MS4)
# ---------------------------------------------------------------------------
def test_window_in_or_after_the_policy_year():
    assert not rules.in_window(2003)
    assert rules.in_window(2004)
    assert not rules.in_window(
        2004, pol.TrackMPolicy(window_rule=pol.WINDOW_AFTER)
    )
    assert rules.in_window(
        2005, pol.TrackMPolicy(window_rule=pol.WINDOW_AFTER)
    )
    report = pol.policy_for_row("MS1")
    assert report.policy_year == 2007
    assert not rules.in_window(2006, report)
    assert rules.in_window(2007, report)


def test_a_pia_before_the_window_is_untouched_under_every_option():
    record = worker(300.0, 40, first=2003)
    for option in range(1, 6):
        outcome = evaluate(record, option)
        assert not outcome.on_minimum
        assert outcome.option_pia == outcome.cut_pia == 300.0
        assert outcome.reason == "pia_before_window"


# ---------------------------------------------------------------------------
# DI proration (G12)
# ---------------------------------------------------------------------------
def test_proration_elapsed_years_from_22():
    # Onset at 44: D = 1994 - 1972 = 22; Y* = 15 x 40 / 22.
    assert rules.prorated_work_years(
        15, birth_year=1950, onset_year=1994
    ) == pytest.approx(600 / 22)
    floor = pol.TrackMPolicy(
        di_prorated_years_rounding=pol.PRORATED_YEARS_FLOOR
    )
    assert (
        rules.prorated_work_years(
            15, birth_year=1950, onset_year=1994, policy=floor
        )
        == 27.0
    )


def test_proration_bounds():
    # Onset in the year of attaining 22: D = 0, bounded to 1; Y* = 2 x 40,
    # capped at 40.
    assert rules.prorated_work_years(2, birth_year=1950, onset_year=1972) == 40
    # Onset at 70: D = 48, bounded to 40; Y* = Y.
    assert rules.prorated_work_years(
        30, birth_year=1950, onset_year=2020
    ) == pytest.approx(30)
    # Onset at 32: D = 10; 3 years -> 12 years, over the 10-year floor.
    assert rules.prorated_work_years(
        3, birth_year=1950, onset_year=1982
    ) == pytest.approx(12)
    with pytest.raises(ValueError):
        rules.prorated_work_years(-1, birth_year=1950, onset_year=1990)


def test_a_prorated_worker_can_cross_the_floor():
    # 6 years of 20 possible (onset at 42): Y* = 12 >= 10.
    record = rules.WorkerInputs(
        pia=300.0,
        work_years=6,
        first_pia_year=2010,
        threshold_year=2010,
        birth_year=1968,
        di_onset_year=2010,
    )
    outcome = evaluate(record, 2)
    assert outcome.work_years_star == pytest.approx(12)
    # M = (0.55 + 0.015 x 2) x 10,000 / 12 = 483.33 > 0.8719 x 300.
    assert outcome.minimum == pytest.approx(483.3333)
    assert outcome.on_minimum
    # Without proration (a retired worker with 6 years): below the floor.
    assert evaluate(worker(300.0, 6), 2).reason == "below_floor_years"


# ---------------------------------------------------------------------------
# Threshold and indexing (G8, G9)
# ---------------------------------------------------------------------------
def test_price_and_wage_indexing():
    thresholds = rules.AgedThresholds(
        {2004: 10_000.0, 2007: 10_600.0, 2010: 11_000.0},
        {"kind": "INVENTED"},
    )
    # Price: the threshold of the year itself.
    assert rules.minimum_threshold(
        2010, pol.OPTIONS[2], thresholds, NAWI
    ) == pytest.approx(11_000.0)
    # Wage: T(2004) x AWI(2008) / AWI(2002) = 10,000 x 46,000 / 40,000.
    assert rules.minimum_threshold(
        2010, pol.OPTIONS[3], thresholds, NAWI
    ) == pytest.approx(11_500.0)
    # MS1 moves the base: T(2007) x AWI(2008) / AWI(2005)
    #   = 10,600 x 46,000 / 43,000.
    assert rules.minimum_threshold(
        2010, pol.OPTIONS[5], thresholds, NAWI, pol.policy_for_row("MS1")
    ) == pytest.approx(10_600.0 * 46_000.0 / 43_000.0)
    # At the base year the wage-indexed minimum equals the price-indexed.
    for price, wage in ((2, 3), (4, 5)):
        assert rules.minimum_threshold(
            2004, pol.OPTIONS[wage], thresholds, NAWI
        ) == pytest.approx(
            rules.minimum_threshold(2004, pol.OPTIONS[price], thresholds, NAWI)
        )
    with pytest.raises(rules.ThresholdYearMissingError):
        rules.minimum_threshold(2011, pol.OPTIONS[2], thresholds, NAWI)
    with pytest.raises(ValueError):
        rules.minimum_threshold(2010, pol.OPTIONS[1], thresholds, NAWI)


def test_monthly_minimum_rounding():
    # 0.85 x 10,000 / 12 = 708.333...; a dime floor gives 708.30.
    assert rules.monthly_minimum(pol.OPTIONS[2], 30, INVENTED_T) == (
        pytest.approx(708.3333, abs=1e-4)
    )
    dime = pol.TrackMPolicy(minimum_rounding=pol.MINIMUM_ROUNDING_DIME)
    assert rules.monthly_minimum(pol.OPTIONS[2], 30, INVENTED_T, dime) == (
        pytest.approx(708.3)
    )
    assert rules.monthly_minimum(pol.OPTIONS[1], 30, INVENTED_T) == 0.0


def test_thresholds_load_from_the_census_capture():
    # the capture itself is tested in test_threshold_capture.py
    loaded = rules.load_aged_thresholds()
    assert sorted(loaded.annual) == list(range(2003, 2023))
    assert loaded.source["kind"] == "census_capture"


# ---------------------------------------------------------------------------
# Nesting (plan section 1): deductions used as unit tests, not results
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "order", [pol.ORDER_FLOOR_AFTER_CUT, pol.ORDER_CUT_AFTER_FLOOR]
)
def test_flag_sets_are_nested_within_an_indexing_method(order):
    thresholds = rules.AgedThresholds(
        {year: 10_000.0 + 150.0 * (year - 2004) for year in range(2004, 2023)},
        {"kind": "INVENTED"},
    )
    for year in (2004, 2010, 2020):
        for years in (9, 10, 15, 20, 27, 35, 40, 44):
            for pia in range(100, 1_600, 25):
                record = worker(
                    float(pia), years, first=year, threshold_year=year
                )
                flags = {
                    option: rules.evaluate_worker(
                        record,
                        option,
                        thresholds=thresholds,
                        nawi=NAWI,
                        policy=pol.TrackMPolicy(order=order),
                    ).on_minimum
                    for option in (2, 3, 4, 5)
                }
                assert flags[4] or not flags[2]
                assert flags[5] or not flags[3]


def test_price_flag_implies_wage_flag_when_the_wage_threshold_is_higher():
    # Invented AWI grows faster than the invented thresholds here, so from
    # the base year on the wage-indexed threshold is at least the price
    # one; with c3 > c2, a worker on option 2's minimum is on option 3's.
    thresholds = rules.AgedThresholds(
        {year: 10_000.0 + 100.0 * (year - 2004) for year in range(2004, 2023)},
        {"kind": "INVENTED"},
    )
    for year in range(2004, 2023, 3):
        wage = rules.minimum_threshold(year, pol.OPTIONS[3], thresholds, NAWI)
        price = rules.minimum_threshold(year, pol.OPTIONS[2], thresholds, NAWI)
        assert wage >= price
        for pia in range(200, 1_300, 10):
            record = worker(float(pia), 30, first=year, threshold_year=year)
            two = rules.evaluate_worker(
                record, 2, thresholds=thresholds, nawi=NAWI
            )
            three = rules.evaluate_worker(
                record, 3, thresholds=thresholds, nawi=NAWI
            )
            assert three.on_minimum or not two.on_minimum


# ---------------------------------------------------------------------------
# Auxiliaries and who counts as receiving (G13, G23, MS3)
# ---------------------------------------------------------------------------
def test_auxiliary_benefits_are_decided_by_the_oracle():
    params = invented_params()
    # Spouse with no own PIA: 0.5 x 833.33 > 0 -> paid.
    assert rules.spouse_excess_paid(0.0, 833.33, 0, params)
    # Own PIA 500 >= 0.5 x 833.33 = 416.67 -> no excess.
    assert not rules.spouse_excess_paid(500.0, 833.33, 0, params)
    assert benefits.spousal_benefit(500.0, 833.33, 0, params) == 0.0
    # Survivor: max(700, 833.33) exceeds the own 700 -> paid; own 900 not.
    assert rules.survivor_excess_paid(700.0, 833.33, 0, 1.0, params)
    assert not rules.survivor_excess_paid(900.0, 833.33, 0, 1.0, params)


def test_receipt_counting_rules():
    spouse = rules.LinkedBenefit("spouse", worker_on_minimum=True, paid=True)
    unpaid = rules.LinkedBenefit(
        "survivor", worker_on_minimum=True, paid=False
    )
    unflagged = rules.LinkedBenefit(
        "spouse", worker_on_minimum=False, paid=True
    )
    own = rules.receives_minimum(
        own_on_minimum=True, paid_own_worker_benefit=True
    )
    assert own == rules.Receipt(True, "own_worker_pia")
    # Plan case F: the spouse of A with no own benefit counts under G23 ...
    assert rules.receives_minimum(
        own_on_minimum=False, paid_own_worker_benefit=False, linked=[spouse]
    ) == rules.Receipt(True, "linked_worker_pia")
    # ... and not under MS3.
    assert rules.receives_minimum(
        own_on_minimum=False,
        paid_own_worker_benefit=False,
        linked=[spouse],
        policy=pol.policy_for_row("MS3"),
    ) == rules.Receipt(False, "none")
    for link in (unpaid, unflagged):
        assert not rules.receives_minimum(
            own_on_minimum=False, paid_own_worker_benefit=True, linked=[link]
        ).receives
    assert rules.receives_minimum(
        own_on_minimum=False,
        paid_own_worker_benefit=False,
        unlinked_auxiliary=True,
    ) == rules.Receipt(False, "unlinked_auxiliary")
    with pytest.raises(ValueError):
        rules.LinkedBenefit("child", True, True)


# ---------------------------------------------------------------------------
# The PIA through the oracle (G5, MS5, MS6)
# ---------------------------------------------------------------------------
def _flat_history(birth_year, last_year, amount=20_000.0):
    return {
        year: amount
        for year in range(max(1968, birth_year + 22), last_year + 1)
    }


def test_old_age_pia_calls_the_oracle_unchanged():
    params = invented_params()
    history = _flat_history(1948, 2012)
    record = rules.history_pia(history, birth_year=1948, params=params)
    kept = {year: value for year, value in history.items() if year <= 2009}
    expected_aime = statutory_aime.aime(kept, 1948, params)
    assert expected_aime == benefits.aime(kept, 1948, params)
    assert record.aime == expected_aime
    assert record.pia == benefits.pia(expected_aime, 2010, params)
    assert record.eligibility_year == 2010
    assert record.computation_end_year == 2009


def test_di_pia_approximation_and_ms6():
    params = invented_params()
    history = _flat_history(1960, 2003)
    approx = rules.history_pia(
        history,
        birth_year=1960,
        params=params,
        basis="disability",
        onset_year=2004,
    )
    statutory = rules.history_pia(
        history,
        birth_year=1960,
        params=params,
        basis="disability",
        onset_year=2004,
        policy=pol.policy_for_row("MS6"),
    )
    assert approx.method == "cola_track_a.benefits.approximate_pia"
    assert statutory.eligibility_year == approx.eligibility_year == 2004
    # Elapsed years 1982-2003 = 22; less 22 // 5 = 4 -> 18 computation
    # years against the approximation's 35: the statutory PIA is higher.
    assert (
        statutory_aime.benefit_computation_years(1960, disability_year=2004)
        == 18
    )
    assert statutory.pia > approx.pia


def test_death_basis_and_bad_bases():
    params = invented_params()
    history = _flat_history(1960, 2007)
    record = rules.history_pia(
        history, birth_year=1960, params=params, basis="death", death_year=2008
    )
    assert record.eligibility_year == 2008
    with pytest.raises(ValueError):
        rules.history_pia(history, birth_year=1960, params=params, basis="x")
    with pytest.raises(ValueError):
        rules.history_pia(
            history, birth_year=1960, params=params, basis="disability"
        )


def test_benefit_implied_pia():
    # 750 / (0.75 x 1.25) = 800.
    assert rules.benefit_implied_pia(
        750.0, claim_factor=0.75, cola_factor=1.25
    ) == pytest.approx(800.0)
    with pytest.raises(ValueError):
        rules.benefit_implied_pia(750.0, claim_factor=0.0, cola_factor=1.0)


def test_worker_inputs_are_validated():
    with pytest.raises(ValueError):
        worker(-1.0, 10)
    with pytest.raises(TypeError):
        rules.WorkerInputs(
            pia=1.0,
            work_years=1,
            first_pia_year=2010.0,
            threshold_year=2010,
            birth_year=1948,
        )
    with pytest.raises(ValueError):
        evaluate(worker(500.0, 20), 6)
