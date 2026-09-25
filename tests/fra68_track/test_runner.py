"""Exercise 3 (FRA to 68) on the Track A pipeline, INVENTED data only.

Every person, earnings amount, Social Security amount, weight, rate, life
table, DI probability, claim-age PMF, wage index and COLA below is
INVENTED (the Track A test fixtures of ``tests/cola_track_a/
test_assembly.py``), except the FRA schedule of the invented parameter
bundle, which is the statute's (42 USC 416(l), as the committed capture
holds it, transcribed here) so that the reform schedules have their real
baseline.  No test reads PSID or a comparator value, and no number here is
a model result.  The E1 specification document is read for its section 21
block, which the run checks against the code.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from collections import Counter
from dataclasses import replace
from functools import lru_cache
from types import SimpleNamespace

import pandas as pd
import pytest

from populace_dynamics import claiming
from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import (
    INVENTED_COHORT_LABEL,
    TrackAInputs,
    invented,
    prepare_track_a_cohort,
)
from populace_dynamics.cola_track_a import benefits as track_benefits
from populace_dynamics.cola_track_a import runner as track_runner
from populace_dynamics.cola_track_a.adapters import claiming_schedule
from populace_dynamics.cola_track_a.benefits import (
    BenefitContext,
    PiaRecord,
    StateLookups,
    reference_benefit_rows,
)
from populace_dynamics.cola_track_a.config import (
    REGISTERED_ROWS as TRACK_A_ROWS,
)
from populace_dynamics.cola_track_a.config import LevelPolicy
from populace_dynamics.engine.di_entitlement import (
    fra_schedule_from_parameters,
)
from populace_dynamics.estimates.cola_age_profile import INVENTED_DATA_LABEL
from populace_dynamics.fra68_track import (
    STATISTIC_ID,
    ClaimingResponse,
    FRA68Config,
    SurvivorRetirementAge,
    max_rulings,
    registered_rows,
    rulings_departures,
    run_fra68,
)
from populace_dynamics.fra68_track import runner as fra68_runner
from populace_dynamics.fra68_track.benefits import (
    CONVERSION_CLAIM_EXCESS,
    CONVERSION_CLAIM_MONTHS_EARLY,
    CREDITS_NOT_INHERITED,
    CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH,
    MovedClaimRecord,
    Scenario,
    ScenarioCalculator,
    scenario_benefits,
    union_benefit_rows,
)
from populace_dynamics.fra68_track.config import (
    E1_RATIFICATION,
    E1_RULINGS,
    MAX_RULINGS,
    STYLIZED_RESPONSE_LABEL,
    builder_defaults,
    row_labels,
)
from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    fra_increase_months,
    reform_parameters,
    spouse_excess_months_early,
    worker_factor_ratio,
)
from populace_dynamics.fra68_track.runner import (
    check_specification_for_registered_run,
    e1_parameter_block,
    projection_identity_record,
    specification_code_check,
)
from populace_dynamics.ss import benefits as ss_benefits
from populace_dynamics.ss.statutory_aime import ComputationYears
from tests.cola_track_a.test_assembly import (
    invented_cola,
    invented_di_rates,
    invented_mortality,
    invented_params,
)

#: 42 USC 416(l) by birth year in months, as the committed statutory
#: capture holds it (65 before 1938; 66 for 1943-1954; 67 from 1960).
STATUTE_FRA = [
    (1900, 780),
    (1938, 782),
    (1939, 784),
    (1940, 786),
    (1941, 788),
    (1942, 790),
    (1943, 792),
    (1955, 794),
    (1956, 796),
    (1957, 798),
    (1958, 800),
    (1959, 802),
    (1960, 804),
]
CONFIG = FRA68Config(draw_indices=(0, 1))
TRACK_CONFIG = CONFIG.track_a_config()
_DI_ONLY = {"disabled_worker"}


def statutory_params():
    """INVENTED wage and rate parameters with the statute's FRA schedule."""
    return dataclasses.replace(
        invented_params(), fra_months_by_birth_year=list(STATUTE_FRA)
    )


@lru_cache(maxsize=2)
def _cohort(anchor_wave: int):
    return prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(
            invented.invented_psid2010_inputs(seed=7, anchor_wave=anchor_wave),
            psid2010.Psid2010CohortSpec(anchor_wave=anchor_wave),
        ),
        data_provenance="invented",
        config=TRACK_CONFIG,
    )


def _inputs(**changes) -> TrackAInputs:
    values = {
        "cohort": _cohort(2011),
        "params": statutory_params(),
        "baseline": invented_cola(),
        "di_rates": invented_di_rates(),
        "population_mortality": invented_mortality(),
        "claiming_pmf": invented.invented_claiming_pmf(),
        "additional_cohorts": (_cohort(2009),),
    }
    values.update(changes)
    return TrackAInputs(**values)


@pytest.fixture(scope="module")
def result() -> dict:
    return run_fra68(_inputs(), config=CONFIG)


@pytest.fixture(scope="module")
def projection():
    """One invented draw of the 2011-wave population (Track A's projection)."""

    inputs = _inputs()
    config = FRA68Config(draw_indices=(0,))
    track_config = config.track_a_config()
    results, _ = track_runner._project_population(
        inputs.cohort,
        inputs,
        track_config,
        schedule=claiming_schedule(
            inputs.claiming_pmf, max_table_year=config.claim_table_max_year
        ),
        fra_schedule=fra_schedule_from_parameters(inputs.params),
        progress=None,
    )
    result = results[0]
    return SimpleNamespace(
        inputs=inputs,
        cohort=inputs.cohort,
        result=result,
        lookups=StateLookups(result, 2030),
        track_config=track_config,
        base=inputs.params,
        reforms={
            sid: reform_parameters(inputs.params, schedule)
            for sid, schedule in SCHEDULES.items()
        },
        cache={},
    )


def _people(projection, scenario: Scenario):
    context = BenefitContext(
        cohort=projection.cohort,
        params=scenario.params,
        baseline=projection.inputs.baseline,
        config=projection.track_config,
    )
    people, _ = scenario_benefits(
        projection.result,
        context=context,
        track_row=TRACK_A_ROWS["R0"],
        scenario=scenario,
        lookups=projection.lookups,
        pia_cache=projection.cache,
        assumed_birth_month=7,
    )
    return people


def _scenario(projection, name, sid=None, **changes) -> Scenario:
    params = projection.base if sid is None else projection.reforms[sid]
    return Scenario(
        name=name,
        params=params,
        baseline_params=projection.base,
        schedule_id=sid,
        **changes,
    )


def _union(projection, base_people, reform_people, sid):
    context = BenefitContext(
        cohort=projection.cohort,
        params=projection.base,
        baseline=projection.inputs.baseline,
        config=projection.track_config,
    )
    rows, counters = union_benefit_rows(
        base_people,
        reform_people,
        draw=0,
        context=context,
        lookups=projection.lookups,
        baseline_params=projection.base,
        reform_params=projection.reforms[sid],
    )
    return rows, counters


@pytest.fixture(scope="module")
def baseline_people(projection):
    return _people(projection, _scenario(projection, "baseline"))


@pytest.fixture(scope="module")
def f0_rows(projection, baseline_people):
    reform = _people(projection, _scenario(projection, "reform", "P3"))
    rows, counters = _union(projection, baseline_people, reform, "P3")
    return rows, counters, reform


# --------------------------------------------------------------------------
# Configuration and rows
# --------------------------------------------------------------------------
_ROW_FIELDS = {
    "fra_schedule": "schedule_id",
    "claiming_response": "claiming_response",
    "statistic": "headline_statistic",
    "components": "components",
    "survivor_retirement_age": "survivor_retirement_age",
    "population_and_vintage": "anchor_wave",
}


@pytest.mark.parametrize("primary", ["P1", "P2", "P3"])
def test_each_alternative_differs_from_f0_in_its_one_field(primary):
    rows = registered_rows(primary)
    assert list(rows) == [f"F{k}" for k in range(9)]
    f0 = rows["F0"]
    assert f0.schedule_id == primary
    for row_id, row in rows.items():
        differing = [
            name
            for name in _ROW_FIELDS.values()
            if getattr(row, name) != getattr(f0, name)
        ]
        if row_id == "F0":
            assert not differing and row.field_changed is None
        else:
            assert differing == [_ROW_FIELDS[row.field_changed]], row_id
    others = [sid for sid in ("P1", "P2", "P3") if sid != primary]
    assert [rows["F1"].schedule_id, rows["F2"].schedule_id] == others


def test_the_plan_row_map_under_the_proposed_primary():
    rows = registered_rows()
    assert rows["F0"].schedule_id == "P3"
    assert (rows["F1"].schedule_id, rows["F2"].schedule_id) == ("P1", "P2")
    assert rows["F3"].claiming_response is (
        ClaimingResponse.AT_OR_AFTER_ANCHOR_DELAY
    )
    assert rows["F4"].claiming_response is ClaimingResponse.ALL_DELAY
    assert rows["F7"].survivor_retirement_age is (
        SurvivorRetirementAge.UNCHANGED_FROM_BASELINE
    )
    assert rows["F8"].anchor_wave == 2009
    assert (
        rows["F0"].reform_key
        == rows["F5"].reform_key
        == (rows["F6"].reform_key)
    )
    with pytest.raises(ValueError, match="unknown primary"):
        registered_rows("P4")


def test_every_ruled_field_follows_maxs_ruling_by_default():
    rulings = max_rulings(CONFIG)
    assert [item["field"] for item in rulings] == list(MAX_RULINGS)
    assert all(item["follows_ruling"] for item in rulings)
    assert all(
        item["ruled_by"] == "Max, 2026-09-24 (E1 section 22)"
        for item in rulings
    )
    assert {item["decision_record"] for item in rulings} == {"d188", "d196"}
    assert rulings_departures(CONFIG) == []
    changed = replace(CONFIG, primary_schedule_id="P1")
    flags = {
        item["field"]: item["follows_ruling"] for item in max_rulings(changed)
    }
    assert flags["primary_schedule_id"] is False
    assert rulings_departures(changed) == ["primary_schedule_id"]
    assert rulings_departures(
        replace(CONFIG, di_benefit_level=LevelPolicy.EXCLUDE)
    ) == ["di_benefit_level"]
    assert {item["field"] for item in builder_defaults(CONFIG)} >= {
        "c1_anchor_age",
        "survivor_retirement_age_f0",
    }
    # A field is either ruled by Max or a builder default, never both.
    assert not {item["field"] for item in builder_defaults(CONFIG)} & set(
        MAX_RULINGS
    )


#: The choices E1 relies on that d188 as filed does not name (E1 referee
#: report, required change 7), with the record that rules on each: d196
#: by name, and d188 item (a) (run exactly like Track A) for the benefit
#: computation years.
_NOT_IN_D188_AS_FILED = {
    "survivor_reduction_span": ("exact_by_cohort_both_scenarios", "d196"),
    "oracle_cola_horizon_extension_to_2030": (True, "d196"),
    "opening_stock_basis": ("fixed_at_opening_year", "d196"),
    "benefit_computation_years": ("legacy_fixed_35", "d188"),
}


def test_choices_d188_as_filed_does_not_name_are_their_own_fields():
    flagged = {
        name
        for name, ruling in MAX_RULINGS.items()
        if ruling.get("named_in_d188_as_filed") is False
    }
    assert flagged == set(_NOT_IN_D188_AS_FILED)
    for name, (value, record) in _NOT_IN_D188_AS_FILED.items():
        assert MAX_RULINGS[name]["ruling"] == value
        assert MAX_RULINGS[name]["decision_record"] == record
        assert getattr(CONFIG, name) == value
    assert MAX_RULINGS["oracle_cola_horizon_extension_to_2030"][
        "carries_over"
    ] == ("d074 decision 2(a)")
    assert "d075" in MAX_RULINGS["opening_stock_basis"]["carries_over"]
    # The computation years are Track A's constant, not a setting.
    assert CONFIG.benefit_computation_years == (
        track_benefits.TRACK_A_COMPUTATION_YEARS.value
    )
    # No decision record put the statutory count to Max, so the ruling
    # records no declined alternative (regression: it listed one).
    assert MAX_RULINGS["benefit_computation_years"]["declined"] == []
    # The two exercise-1 carry-overs reach the Track A configuration the
    # shared projection runs under.
    track = CONFIG.track_a_config()
    assert track.oracle_cola_horizon_extension_to_2030 is True
    assert track.opening_stock_basis == "fixed_at_opening_year"
    # The configuration record carries the three settings; the computation
    # years, not a setting, are recorded under track_a_conventions and
    # max_rulings (test_run_records_parameters_and_checks).
    recorded = CONFIG.as_dict()
    for name, (value, _record) in _NOT_IN_D188_AS_FILED.items():
        if name != "benefit_computation_years":
            assert recorded[name] == value
    assert "benefit_computation_years" not in recorded


@pytest.mark.parametrize(
    "change",
    [
        {"claim_class": "hold_for_track_b"},
        {"oracle_fra_schedule_override": False},
        {"acceptance_rule": "within 1 point"},
        {"survivor_reduction_span": "track_a_fixed_84_months"},
        {"oracle_cola_horizon_extension_to_2030": False},
        {"opening_stock_basis": "rebased_on_later_simulated_events"},
    ],
)
def test_declined_alternatives_refuse_to_run(change):
    # Each refusal names Max's ruling it departs from (2026-09-24).
    with pytest.raises(ValueError, match=r"Max.*\(?d1(88|96) item"):
        replace(CONFIG, **change).check_runnable()
    with pytest.raises(ValueError):
        run_fra68(_inputs(), config=replace(CONFIG, **change))


def test_configuration_guards():
    with pytest.raises(ValueError, match="unknown rows"):
        FRA68Config(rows=("F0", "F9"))
    with pytest.raises(ValueError, match="unique"):
        FRA68Config(rows=("F0", "F0"))
    with pytest.raises(ValueError, match="c1_anchor_age"):
        FRA68Config(c1_anchor_age=61)
    assert FRA68Config(rows=("F0",)).track_a_config().rows == ("R0",)
    assert FRA68Config(rows=("F8",)).track_a_config().rows == ("R6",)
    assert CONFIG.track_a_config().rows == ("R0", "R6")


def test_stylized_rows_carry_their_own_label():
    labels = (INVENTED_COHORT_LABEL, "Python oracle (not Axiom)", "x")
    track_labels = (
        "PSID-seeded closed cohort",
        "Python oracle (not Axiom)",
        "fixed-path mechanical incidence",
    )
    rows = registered_rows()
    assert row_labels(rows["F0"], track_labels) == track_labels
    stylized = row_labels(rows["F4"], track_labels)
    assert stylized[2] == STYLIZED_RESPONSE_LABEL
    assert row_labels(rows["F3"], labels) == labels


# --------------------------------------------------------------------------
# The null-reform identity with Track A
# --------------------------------------------------------------------------
def test_null_reform_reproduces_track_a_baseline_bit_for_bit(projection):
    fixed = SurvivorRetirementAge.TRACK_A_FIXED_84
    base = _people(
        projection,
        _scenario(projection, "baseline", survivor_retirement_age=fixed),
    )
    context = BenefitContext(
        cohort=projection.cohort,
        params=projection.base,
        baseline=projection.inputs.baseline,
        config=projection.track_config,
    )
    track_rows, _ = reference_benefit_rows(
        projection.result,
        draw=0,
        row=TRACK_A_ROWS["R0"],
        context=context,
        lookups=projection.lookups,
    )
    assert track_rows
    positive = {pid for pid, person in base.items() if person.total > 0}
    assert positive == {row["person_id"] for row in track_rows}
    for row in track_rows:
        person = base[row["person_id"]]
        assert 12 * person.total == row["benefit_base"]
        assert {
            name: 12 * amount for name, amount in person.components.items()
        } == {
            name: value["base"]
            for name, value in row["benefit_components"].items()
        }
    # This invented draw pays no spouse's excess; the calculator-level
    # identities for the spouse's excess are
    # test_a_moved_spouse_claim_keeps_the_excess_reduction and
    # test_a_converted_spouse_keeps_its_excess_in_every_scenario.
    assert {
        name for row in track_rows for name in row["benefit_components"]
    } >= {"retired_worker", "disabled_worker", "aged_widow"}
    # A reform equal to the baseline changes nothing, under every claiming
    # response (no FRA increase, so no claim moves and the spouse's excess
    # is counted exactly as Track A counts it).
    for response in ClaimingResponse:
        same = Scenario(
            name="reform",
            params=projection.base,
            baseline_params=projection.base,
            survivor_retirement_age=fixed,
            claiming_response=response,
        )
        reform = _people(projection, same)
        for pid, person in base.items():
            assert reform[pid].components == person.components, response


#: Counters Track A's ``reference_benefit_rows`` keeps per row and
#: exercise 3 keeps in ``union_benefit_rows`` instead.
_ROW_COUNTERS = (
    "beneficiaries_",
    "opening_di_basis_ended_by_recovery",
    "opening_recipient_without_record",
)
#: Exercise-3 diagnostic counters Track A does not keep (they change no
#: amount): the named delta of credits not inherited (E1 section 12).
_EXERCISE_3_COUNTERS = ("fra68_",)


def test_null_reform_counts_each_person_once_as_track_a_does(projection):
    # Regression: scenario_benefits looked each projected person's own
    # record up a second time to label the row, and the calculator counts
    # an excluded or unavailable level on every lookup, so those counters
    # were inflated.  DI levels excluded (the d188 alternative) makes the
    # case occur on the invented cohort.
    config = replace(
        projection.track_config, di_benefit_level=LevelPolicy.EXCLUDE
    )
    context = BenefitContext(
        cohort=projection.cohort,
        params=projection.base,
        baseline=projection.inputs.baseline,
        config=config,
    )
    _, track = reference_benefit_rows(
        projection.result,
        draw=0,
        row=TRACK_A_ROWS["R0"],
        context=context,
        lookups=projection.lookups,
    )
    _, ours = scenario_benefits(
        projection.result,
        context=context,
        track_row=TRACK_A_ROWS["R0"],
        scenario=_scenario(
            projection,
            "baseline",
            survivor_retirement_age=SurvivorRetirementAge.TRACK_A_FIXED_84,
        ),
        lookups=projection.lookups,
        pia_cache={},
        assumed_birth_month=7,
    )
    assert track["level_excluded_di"] > 0

    def calculator_counts(counters):
        return {
            key: value
            for key, value in counters.items()
            if not key.startswith(_ROW_COUNTERS + _EXERCISE_3_COUNTERS)
        }

    assert calculator_counts(ours) == calculator_counts(track)


def _level_calculator(params, birth, history):
    """A bare ScenarioCalculator holding only what ``_level`` reads.

    INVENTED person 1 with the given birth year and covered earnings.
    """

    calculator = object.__new__(ScenarioCalculator)
    calculator.ctx = SimpleNamespace(
        params=params, cohort=SimpleNamespace(careers={1: history})
    )
    calculator.statics = pd.DataFrame({"birth_year": [birth]}, index=[1])
    calculator.counters = Counter()
    calculator.cache = {}
    return calculator


def test_exercise_3_levels_keep_exercise_1s_legacy_35_years(projection):
    # Exercise 3 must match exercise 1 path for path (E1 sections 11 and
    # 14).  Exercise 1's Registration 13 divided every oracle AIME by 35
    # years; since #457 the oracle also offers the 415(b)(2) count, which
    # differs for workers born before 1929 and is the default of
    # scenario_benefits.eligibility_pia_for_clock.  Exercise 3 computes
    # every level through Track A's inherited _Calculator._level, so its
    # levels are the legacy fixed 35 in every scenario.  INVENTED: born
    # 1925, covered earnings 1968-1986 (31 statutory computation years).
    assert ScenarioCalculator._level is track_benefits._Calculator._level
    assert (
        track_benefits.TRACK_A_COMPUTATION_YEARS
        is ComputationYears.LEGACY_FIXED_35
    )
    birth, history = 1925, {year: 30_000.0 for year in range(1968, 1987)}
    legacy = ss_benefits.pia(
        ss_benefits.aime(history, birth, projection.base),
        1987,
        projection.base,
    )
    statutory = track_benefits.sb.eligibility_pia_for_clock(
        track_benefits.sb.WorkerClock.at_age_62(birth),
        history=history,
        birth_year=birth,
        params=projection.base,
    )
    assert statutory > legacy
    di_legacy = ss_benefits.pia(
        ss_benefits.aime(
            {y: e for y, e in history.items() if y <= 1980},
            min(birth, 1980 - 62),
            projection.base,
        ),
        1980,
        projection.base,
    )
    for params in (projection.base, *projection.reforms.values()):
        calculator = _level_calculator(params, birth, history)
        level, basis = calculator._level(1, "retirement", 1987, None)
        assert (level, basis) == (legacy, "oracle_retirement_pia")
        di, _ = calculator._level(
            1, "di", 1980, LevelPolicy.DISCLOSED_ORACLE_APPROXIMATION
        )
        assert di == di_legacy


def test_the_specification_check_binds_the_computation_years(monkeypatch):
    # A registered run refuses a block whose computation years are not
    # Track A's, and the committed block once Track A's count changes.
    block = e1_parameter_block()
    assert block["amounts"]["benefit_computation_years"] == (
        ComputationYears.LEGACY_FIXED_35.value
    )
    assert specification_code_check(block, FRA68Config())["consistent"]
    edited = copy.deepcopy(block)
    edited["amounts"][
        "benefit_computation_years"
    ] = ComputationYears.STATUTORY.value
    check = specification_code_check(edited, FRA68Config())
    assert check["mismatches"] == ["amounts.benefit_computation_years"]
    monkeypatch.setattr(
        track_benefits,
        "TRACK_A_COMPUTATION_YEARS",
        ComputationYears.STATUTORY,
    )
    check = specification_code_check(block, FRA68Config())
    assert check["mismatches"] == ["amounts.benefit_computation_years"]
    # Max's ruling (covered by d188 item (a)) fixes the legacy fixed 35 as
    # a value, so the changed constant also departs from it.
    assert rulings_departures(FRA68Config()) == ["benefit_computation_years"]
    with pytest.raises(ValueError, match="departs from Max's rulings"):
        check_specification_for_registered_run(block, FRA68Config())


def test_the_exact_survivor_span_changes_only_early_survivors(
    projection, baseline_people
):
    fixed = _people(
        projection,
        _scenario(
            projection,
            "baseline",
            survivor_retirement_age=SurvivorRetirementAge.TRACK_A_FIXED_84,
        ),
    )
    statics = projection.cohort.persons_by_id
    for pid, person in baseline_people.items():
        if person.components != fixed[pid].components:
            assert "aged_widow" in person.components
            assert int(statics.at[pid, "birth_year"]) < 1962


# --------------------------------------------------------------------------
# Row F0 (P3, C0): the arithmetic of plan section 4
# --------------------------------------------------------------------------
def test_f0_never_raises_a_benefit_and_keeps_membership(f0_rows):
    rows, counters, _ = f0_rows
    assert rows
    for row in rows:
        assert row["beneficiary_base"] and row["beneficiary_reform"]
        assert row["benefit_reform"] <= row["benefit_base"] + 1e-9
    assert counters["baseline_only_beneficiaries"] == 0
    assert counters["reform_only_beneficiaries"] == 0


def test_f0_disabled_workers_and_unreached_cohorts_are_unchanged(f0_rows):
    rows, _, _ = f0_rows
    di = [row for row in rows if set(row["benefit_components"]) <= _DI_ONLY]
    old = [
        row
        for row in rows
        if row["birth_year"] <= 1947
        and "aged_widow" not in row["benefit_components"]
    ]
    assert di and old
    for row in di + old:
        assert row["benefit_reform"] == row["benefit_base"]


def test_f0_retired_workers_follow_the_factor_ratio(projection, f0_rows):
    rows, _, _ = f0_rows
    checked = 0
    for row in rows:
        if set(row["benefit_components"]) != {"retired_worker"}:
            continue
        if row["basis"] != "projected" or row["claim_age_base"] is None:
            continue
        ratio = worker_factor_ratio(
            12 * row["claim_age_base"],
            row["birth_year"],
            projection.base,
            projection.reforms["P3"],
        )
        # Dime flooring of each monthly amount: within 2 dimes a month.
        assert row["benefit_reform"] == pytest.approx(
            row["benefit_base"] * ratio, abs=12 * 0.2
        )
        if row["birth_year"] >= 1960:
            assert row["fra_increase_months"] == 12
        checked += 1
    assert checked > 10


def test_opening_stock_takes_the_factor_ratio(projection, f0_rows):
    rows, _, reform = f0_rows
    opening = [row for row in rows if row["basis"] == "opening_stock"]
    assert opening
    for row in opening:
        ratio = reform[row["person_id"]].opening_factor_ratio
        assert 0 < ratio <= 1
        assert row["benefit_reform"] == pytest.approx(
            row["benefit_base"] * ratio, rel=1e-12
        )
        if row["birth_year"] != 1948:
            assert ratio == 1.0


def test_schedules_order_every_benefit(projection, baseline_people):
    amounts = {}
    for sid in ("P1", "P2", "P3"):
        people = _people(projection, _scenario(projection, "reform", sid))
        amounts[sid] = {pid: person.total for pid, person in people.items()}
    # P1 and P2 bracket P3 in every cohort (plan section 3).
    for pid in baseline_people:
        assert amounts["P2"][pid] <= amounts["P3"][pid] + 1e-9
        assert amounts["P3"][pid] <= amounts["P1"][pid] + 1e-9
        assert amounts["P1"][pid] <= baseline_people[pid].total + 1e-9


def test_f7_differs_from_f0_only_for_widowers(projection):
    f0 = _people(projection, _scenario(projection, "reform", "P3"))
    f7 = _people(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            survivor_retirement_age=(
                SurvivorRetirementAge.UNCHANGED_FROM_BASELINE
            ),
        ),
    )
    differing = [pid for pid in f0 if f0[pid].components != f7[pid].components]
    for pid in differing:
        assert "aged_widow" in f7[pid].components
        assert f7[pid].total >= f0[pid].total


# --------------------------------------------------------------------------
# Rows F3 and F4 (C1, C2)
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "anchor"),
    [
        (ClaimingResponse.ALL_DELAY, 62),
        (ClaimingResponse.AT_OR_AFTER_ANCHOR_DELAY, 65),
    ],
)
def test_claiming_transforms_preserve_the_factor_or_leave_2030(
    projection, baseline_people, response, anchor
):
    reform = _people(
        projection,
        _scenario(projection, "reform", "P3", claiming_response=response),
    )
    rows, counters = _union(projection, baseline_people, reform, "P3")
    assert counters["reform_only_beneficiaries"] == 0
    moved = 0
    for row in rows:
        if set(row["benefit_components"]) != {"retired_worker"}:
            continue
        age = row["claim_age_base"]
        if row["basis"] != "projected" or age is None:
            continue
        if anchor <= age <= 69 and row["fra_increase_months"] == 12:
            # Months from the FRA are preserved: the same factor, or the
            # claim now falls after 2030.
            assert row["benefit_reform"] in (0.0, row["benefit_base"])
            moved += row["benefit_reform"] == 0.0
        elif age < anchor:
            ratio = worker_factor_ratio(
                12 * age,
                row["birth_year"],
                projection.base,
                projection.reforms["P3"],
            )
            assert row["benefit_reform"] == pytest.approx(
                row["benefit_base"] * ratio, abs=12 * 0.2
            )
    if response is ClaimingResponse.ALL_DELAY:
        assert counters["baseline_only_beneficiaries"] == moved > 0


def _person_born(projection, years, status="none"):
    persons = projection.cohort.persons
    chosen = persons[
        persons["birth_year"].isin(years)
        & (persons["opening_status"].astype(str) == status)
    ]
    assert len(chosen), (years, status)
    return int(chosen.iloc[0]["person_id"]), int(chosen.iloc[0]["birth_year"])


def _state(projection, person_id, **fields):
    template = projection.lookups.final.iloc[0].copy()
    statics = projection.cohort.persons_by_id.loc[person_id]
    values = {
        "person_id": person_id,
        "birth_year": int(statics["birth_year"]),
        "year": 2030,
        "di_entitled": False,
        "di_award_year": pd.NA,
        "di_conversion_year": pd.NA,
        "di_recovery_year": pd.NA,
        "claimed": False,
        "claim_year": pd.NA,
        "claim_age": pd.NA,
        **fields,
    }
    for name, value in values.items():
        template[name] = value
    return template


def _calculator(projection, scenario):
    context = BenefitContext(
        cohort=projection.cohort,
        params=scenario.params,
        baseline=projection.inputs.baseline,
        config=projection.track_config,
    )
    return ScenarioCalculator(
        context,
        TRACK_A_ROWS["R0"],
        projection.lookups,
        Counter(),
        {},
        scenario,
        assumed_birth_month=7,
    )


def test_c1_c2_move_a_projected_claim_and_keep_its_factor(projection):
    person, birth = _person_born(projection, range(1960, 1966))
    state = _state(projection, person, claimed=True, claim_year=birth + 64)
    base_record = _calculator(
        projection, _scenario(projection, "baseline")
    ).worker_record(person, state)
    c2 = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.ALL_DELAY,
        ),
    ).worker_record(person, state)
    c1 = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.AT_OR_AFTER_ANCHOR_DELAY,
        ),
    ).worker_record(person, state)
    assert base_record.entitlement_year == birth + 64
    assert c2.entitlement_year == birth + 65
    assert c2.baseline_entitlement_year == birth + 64
    assert c2.claim_age_factor == pytest.approx(base_record.claim_age_factor)
    # C1 (anchor 65): a claim at 64 keeps its age and takes the reduction.
    assert c1.entitlement_year == birth + 64
    assert c1.claim_age_factor == pytest.approx(
        claiming.benefit_factor(12 * 64, birth, projection.reforms["P3"])
    )
    # A claim at 70 is not moved; the credit shrinks (24 to 16 percent).
    late = _state(projection, person, claimed=True, claim_year=birth + 70)
    moved = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.ALL_DELAY,
        ),
    ).worker_record(person, late)
    assert moved.entitlement_year == birth + 70
    assert moved.claim_age_factor == pytest.approx(1.16)


def _spouse_case(projection, calculator, monkeypatch, spouse, claim_year):
    """An INVENTED married claimant whose worker was entitled in 2010.

    The worker is any rostered person in the draw's final state; its
    record is replaced by an INVENTED retired-worker record (PIA
    $10,000.00, entitled 2010), so the claimant's own claim starts the
    excess.
    """

    worker_id = int(
        next(
            pid for pid in projection.lookups.final.index if int(pid) != spouse
        )
    )
    invented_worker = PiaRecord(
        person_id=worker_id,
        kind="retired",
        component="retired_worker",
        basis=track_benefits.sb.EligibilityBasis.AGE_62,
        eligibility_year=2008,
        entitlement_year=2010,
        eligibility_pia=10000.0,
        claim_age_factor=1.0,
        level_basis="invented",
    )
    original = calculator.worker_record

    def worker_record(person_id, state):
        if person_id == worker_id:
            return invented_worker
        return original(person_id, state)

    monkeypatch.setattr(calculator, "worker_record", worker_record)
    monkeypatch.setattr(
        calculator,
        "lookups",
        SimpleNamespace(
            alive=lambda person_id: True,
            final=projection.lookups.final,
            death_year=projection.lookups.death_year,
        ),
    )
    state = _state(
        projection,
        spouse,
        claimed=True,
        claim_year=claim_year,
        marital_status="married",
        spouse_person_id=worker_id,
    )
    own = calculator.worker_record(spouse, state)
    return state, own


@pytest.mark.parametrize(("birth", "increase"), [(1951, 7), (1954, 13)])
def test_a_moved_spouse_claim_keeps_the_excess_reduction(
    projection, monkeypatch, birth, increase
):
    # Referee required change 1 (E1 sections 13 and 19): under C2 the
    # spouse's own claim at 62 moves by D months into the next year; the
    # excess is reduced for FRA' - m' = 48 months, as in the baseline, so
    # its 2030 amount is unchanged.  Track A's whole-year count on the
    # same record gives 48 - (12 - D) months instead.
    spouse, _ = _person_born(projection, [birth])
    base = _calculator(projection, _scenario(projection, "baseline"))
    c2 = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.ALL_DELAY,
        ),
    )
    base_state, base_own = _spouse_case(
        projection, base, monkeypatch, spouse, birth + 62
    )
    c2_state, c2_own = _spouse_case(
        projection, c2, monkeypatch, spouse, birth + 62
    )
    assert not isinstance(base_own, MovedClaimRecord)
    assert isinstance(c2_own, MovedClaimRecord)
    assert c2_own.reform_claim_month == 12 * 62 + increase
    assert c2_own.entitlement_year == birth + 63
    assert base.own_claim_month(base_own, birth + 62, birth) == 744
    assert c2.own_claim_month(c2_own, birth + 63, birth) == 744 + increase
    baseline = base._spouse_excess(spouse, base_state, base_own)
    moved = c2._spouse_excess(spouse, c2_state, c2_own)
    assert baseline is not None and moved is not None
    assert moved == baseline
    whole_year = track_benefits._Calculator._spouse_excess(
        c2, spouse, c2_state, c2_own
    )
    if increase < 12:
        assert whole_year[0] > moved[0]
    else:
        assert whole_year[0] < moved[0]
    # Without a moved claim (C0 on the reform bundle) the exercise-3 count
    # is Track A's, bit for bit.
    c0 = _calculator(projection, _scenario(projection, "reform", "P3"))
    c0_state, c0_own = _spouse_case(
        projection, c0, monkeypatch, spouse, birth + 62
    )
    assert not isinstance(c0_own, MovedClaimRecord)
    assert c0._spouse_excess(
        spouse, c0_state, c0_own
    ) == track_benefits._Calculator._spouse_excess(
        c0, spouse, c0_state, c0_own
    )


def _married_to_invented_worker(
    projection, calculator, monkeypatch, spouse, worker_year, **fields
):
    """An INVENTED married person whose worker was entitled in a given year.

    As :func:`_spouse_case`, with the worker's entitlement year and the
    person's state fields chosen by the test.  Returns the state, the
    person's own record and the worker's record.
    """

    worker_id = int(
        next(
            pid for pid in projection.lookups.final.index if int(pid) != spouse
        )
    )
    invented_worker = PiaRecord(
        person_id=worker_id,
        kind="retired",
        component="retired_worker",
        basis=track_benefits.sb.EligibilityBasis.AGE_62,
        eligibility_year=2008,
        entitlement_year=worker_year,
        eligibility_pia=10000.0,
        claim_age_factor=1.0,
        level_basis="invented",
    )
    original = calculator.worker_record

    def worker_record(person_id, state):
        if person_id == worker_id:
            return invented_worker
        return original(person_id, state)

    monkeypatch.setattr(calculator, "worker_record", worker_record)
    monkeypatch.setattr(
        calculator,
        "lookups",
        SimpleNamespace(
            alive=lambda person_id: True,
            final=projection.lookups.final,
            death_year=projection.lookups.death_year,
        ),
    )
    state = _state(
        projection,
        spouse,
        marital_status="married",
        spouse_person_id=worker_id,
        **fields,
    )
    own = calculator.worker_record(spouse, state)
    return state, own, invented_worker


def _converted_fields(birth, conversion):
    """INVENTED DI history: awarded at 60, converted at the baseline FRA.

    The claiming step records the conversion as the claim
    (``claim_year`` = the conversion year).
    """

    return {
        "di_award_year": birth + 60,
        "di_conversion_year": conversion,
        "claimed": True,
        "claim_year": conversion,
    }


def _track_a_calculator(projection):
    context = BenefitContext(
        cohort=projection.cohort,
        params=projection.base,
        baseline=projection.inputs.baseline,
        config=projection.track_config,
    )
    return track_benefits._Calculator(
        context, TRACK_A_ROWS["R0"], projection.lookups, Counter(), {}
    )


#: The review of ``e1-draft-4`` (E1 section 25): the change 070c59c7's
#: rule made to a converted spouse's months early, by (birth, schedule),
#: when the conversion starts the excess (tests/fra68_track/test_reform.py
#: holds the full grid).  Track A's baseline count: 2 (1955), 4 (1956).
_CONVERTED_CLASSES = {
    1948: {"P1": 0, "P2": 2, "P3": 2},
    1949: {"P1": 2, "P2": 4, "P3": 4},
    1950: {"P1": 4, "P2": 0, "P3": 0},
    1954: {"P1": 0, "P2": 2, "P3": 1},
    1955: {"P1": 0, "P2": 2, "P3": 1},
    1956: {"P1": 0, "P2": -4, "P3": 1},
}
_TRACK_A_CONVERSION_COUNT = {1955: 2, 1956: 4}


@pytest.mark.parametrize("birth", sorted(_CONVERTED_CLASSES))
def test_a_converted_spouse_keeps_its_excess_in_every_scenario(
    projection, monkeypatch, birth
):
    # The review of e1-draft-4: a converted disabled worker's own claim
    # for the spouse's excess was counted from the scenario's whole
    # conversion year, so the FRA increase changed its months early (the
    # leftover month).  42 USC 402(q)(1) (usc42_402.txt line 371) reduces
    # neither scenario's excess: it starts at FRA.  Now each reform keeps
    # the baseline count (the baseline start moved by D; E1 section 11),
    # so the amount is the baseline's under P1, P2 and P3 alike, and the
    # baseline is Track A's bit for bit.
    spouse, _ = _person_born(projection, [birth])
    base_calc = _calculator(projection, _scenario(projection, "baseline"))
    conversion = base_calc.conversion_year(birth)
    fields = _converted_fields(birth, conversion)
    expected_count = _TRACK_A_CONVERSION_COUNT.get(birth, 0)
    amounts, counts = {}, {}
    for sid in ("baseline", "P1", "P2", "P3"):
        scenario = (
            _scenario(projection, "baseline")
            if sid == "baseline"
            else _scenario(projection, "reform", sid)
        )
        calculator = (
            base_calc
            if sid == "baseline"
            else _calculator(projection, scenario)
        )
        state, own, worker = _married_to_invented_worker(
            projection, calculator, monkeypatch, spouse, 2010, **fields
        )
        assert own.kind == "converted", sid
        assert calculator.conversion_claim_year(own, state) == conversion
        own_claim = calculator._own_claim_year(own, state)
        assert own_claim == calculator.conversion_year(birth)
        counts[sid] = calculator.excess_months_early(
            own, state, own_claim, worker, birth
        )
        paid = calculator._spouse_excess(spouse, state, own)
        assert paid is not None and paid[0] > 0 and paid[0] == paid[1]
        amounts[sid] = paid
        # The counters of the named delta (E1 section 12), in every
        # scenario alike.
        assert calculator.counters[CONVERSION_CLAIM_EXCESS] == 1, sid
        assert calculator.counters[CONVERSION_CLAIM_MONTHS_EARLY] == (
            1 if expected_count else 0
        ), sid
        if sid == "baseline":
            continue
        # 070c59c7's rule: Track A's whole-year count on the scenario's own
        # conversion year (Track A's method reads this calculator's
        # _own_claim_year), which the review found.
        old = track_benefits._Calculator._spouse_excess(
            calculator, spouse, state, own
        )
        shift = _CONVERTED_CLASSES[birth][sid]
        if shift > 0:
            assert old[0] < amounts["baseline"][0], sid
        elif shift < 0:
            assert old[0] > amounts["baseline"][0], sid
        else:
            assert old == amounts["baseline"], sid
        # The moved conversion claim, 12 (y_conv_base - b) + D: the C1/C2
        # device gives the same count when the conversion starts the
        # excess.
        increase = fra_increase_months(
            projection.base, projection.reforms[sid], birth
        )
        assert counts[sid] == spouse_excess_months_early(
            own_claim_month=12 * (conversion - birth) + increase,
            worker_entitlement_year=2010,
            birth_year=birth,
            params=projection.reforms[sid],
        )
    assert set(counts.values()) == {expected_count}
    assert set(amounts.values()) == {amounts["baseline"]}
    # The per-person ordering of test_schedules_order_every_benefit holds
    # (with equality) for these people, the 1956 spouse under P2 included.
    assert (
        amounts["P2"][0]
        <= amounts["P3"][0]
        <= amounts["P1"][0]
        <= amounts["baseline"][0]
    )
    # The null-reform identity: Track A's own calculator gives the
    # baseline amount bit for bit (its first path is the baseline path).
    track = _track_a_calculator(projection)
    state, own, _ = _married_to_invented_worker(
        projection, track, monkeypatch, spouse, 2010, **fields
    )
    assert track._spouse_excess(spouse, state, own)[0] == (
        amounts["baseline"][0]
    )
    same = _calculator(
        projection,
        Scenario(
            name="reform",
            params=projection.base,
            baseline_params=projection.base,
        ),
    )
    state, own, _ = _married_to_invented_worker(
        projection, same, monkeypatch, spouse, 2010, **fields
    )
    assert same._spouse_excess(spouse, state, own) == amounts["baseline"]


@pytest.mark.parametrize("birth", [1955, 1956])
def test_a_later_worker_entitlement_keeps_a_converted_excess_unreduced(
    projection, monkeypatch, birth
):
    # The worker is first entitled the year after the spouse's baseline
    # conversion, so the worker starts the baseline excess (0 months
    # early).  Moving only the conversion claim by D would count FRA mod
    # 12 months (2 or 4) in every reform, a cut 402(q)(1) does not make;
    # moving the whole baseline start by D keeps 0.
    spouse, _ = _person_born(projection, [birth])
    base_calc = _calculator(projection, _scenario(projection, "baseline"))
    conversion = base_calc.conversion_year(birth)
    fields = _converted_fields(birth, conversion)
    amounts = {}
    for sid in ("baseline", "P1", "P2", "P3"):
        calculator = (
            base_calc
            if sid == "baseline"
            else _calculator(projection, _scenario(projection, "reform", sid))
        )
        state, own, worker = _married_to_invented_worker(
            projection,
            calculator,
            monkeypatch,
            spouse,
            conversion + 1,
            **fields,
        )
        own_claim = calculator._own_claim_year(own, state)
        assert (
            calculator.excess_months_early(
                own, state, own_claim, worker, birth
            )
            == 0
        )
        amounts[sid] = calculator._spouse_excess(spouse, state, own)
        assert calculator.counters[CONVERSION_CLAIM_EXCESS] == 1
        assert CONVERSION_CLAIM_MONTHS_EARLY not in calculator.counters
        if sid != "baseline":
            increase = fra_increase_months(
                projection.base, projection.reforms[sid], birth
            )
            literal = spouse_excess_months_early(
                own_claim_month=12 * (conversion - birth) + increase,
                worker_entitlement_year=conversion + 1,
                birth_year=birth,
                params=projection.reforms[sid],
            )
            assert literal == _TRACK_A_CONVERSION_COUNT[birth]
    assert set(amounts.values()) == {amounts["baseline"]}


def test_a_moved_worker_claim_leaves_a_converted_count_unchanged(
    projection, monkeypatch
):
    # Under C2 the worker's own claim can move past the spouse's baseline
    # conversion year.  The conversion claim's count reads the worker's
    # baseline entitlement year, so it stays Track A's (4 months for a
    # spouse born 1956); the moved year still gates the excess.
    birth = 1956
    spouse, _ = _person_born(projection, [birth])
    calculator = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.ALL_DELAY,
        ),
    )
    conversion = 2022
    state, own, worker = _married_to_invented_worker(
        projection,
        calculator,
        monkeypatch,
        spouse,
        conversion - 1,
        **_converted_fields(birth, conversion),
    )
    moved = MovedClaimRecord(
        **{
            item.name: getattr(worker, item.name)
            for item in dataclasses.fields(PiaRecord)
        },
        reform_claim_month=12 * 65 + 13,
        baseline_entitlement_year=conversion - 1,
    )
    moved = replace(moved, entitlement_year=conversion + 1)
    own_claim = calculator._own_claim_year(own, state)
    assert (
        calculator.excess_months_early(own, state, own_claim, moved, birth)
        == 4
    )
    # Without the baseline year (Track A's count on the moved year alone)
    # the worker would start the excess: 0 months early, a rise.
    unmoved_year = replace(moved, baseline_entitlement_year=None)
    assert (
        calculator.excess_months_early(
            own, state, own_claim, unmoved_year, birth
        )
        == 0
    )


def _moved_worker_case(projection, calculator, monkeypatch, spouse, worker):
    """An INVENTED married claimant whose worker's claim C1/C2 may move.

    ``worker`` is ``(birth year, claim year)`` of an INVENTED retired
    worker (PIA $10,000.00, factor 1.0); the scenario's claiming response
    decides, through ``_claim_response``, whether its claim moves.  The
    claimant claimed at 62.  Returns the state, the claimant's own record
    and the worker's scenario record.
    """

    worker_birth, worker_claim = worker
    state, own, invented = _married_to_invented_worker(
        projection,
        calculator,
        monkeypatch,
        spouse,
        worker_claim,
        claimed=True,
        claim_year=int(
            projection.cohort.persons_by_id.at[spouse, "birth_year"]
        )
        + 62,
    )
    invented = replace(invented, eligibility_year=worker_birth + 62)
    record = calculator._claim_response(
        invented, worker_birth, pd.Series({"claim_year": worker_claim})
    )
    original = calculator.worker_record

    def worker_record(person_id, person_state):
        if person_id == invented.person_id:
            return record
        return original(person_id, person_state)

    monkeypatch.setattr(calculator, "worker_record", worker_record)
    return state, own, record


@pytest.mark.parametrize(
    ("spouse_birth", "worker", "baseline", "exact", "whole_year"),
    [
        # E1 section 19 (the review of e1-draft-5): P3, the worker born
        # 1951 claims at 65 in 2016 and C1 moves the claim 7 months (to
        # month 787, entitled 2017); the spouse born 1953 claimed at 62 in
        # 2015 and is 763 months old when the worker's moved entitlement
        # starts.
        (1953, (1951, 2016), 36, 40, 35),
        # A move of 11 months (worker born 1953, D = 11) for a spouse born
        # 1954 (D = 13).
        (1954, (1953, 2018), 24, 26, 25),
        # A move of 2 months inside the year (worker born 1948, D = 2) for
        # a spouse born 1950 (D = 6).
        (1950, (1948, 2013), 36, 40, 42),
    ],
)
def test_a_moved_worker_claim_starts_the_spouse_excess_at_its_month(
    projection, monkeypatch, spouse_birth, worker, baseline, exact, whole_year
):
    # The review of e1-draft-5: the spouse's months early read the worker's
    # moved entitlement at its exact month (baseline year plus the months
    # C1 moved it), as they read the spouse's own moved claim.  b4d8732e
    # counted the whole year the moved claim falls in, which changed the
    # spouse's reduction by D(b_s) - 12 x months instead of D(b_s) - v_w
    # (the first case rose above the baseline under a 7-month delay).
    spouse, _ = _person_born(projection, [spouse_birth])
    worker_birth, worker_claim = worker
    base_calc = _calculator(projection, _scenario(projection, "baseline"))
    c1 = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.AT_OR_AFTER_ANCHOR_DELAY,
        ),
    )
    base_state, base_own, base_worker = _moved_worker_case(
        projection, base_calc, monkeypatch, spouse, worker
    )
    c1_state, c1_own, c1_worker = _moved_worker_case(
        projection, c1, monkeypatch, spouse, worker
    )
    increase = fra_increase_months(
        projection.base, projection.reforms["P3"], worker_birth
    )
    assert not isinstance(base_worker, MovedClaimRecord)
    assert not isinstance(c1_own, MovedClaimRecord)  # claimed at 62 < 65
    assert isinstance(c1_worker, MovedClaimRecord)
    assert c1_worker.baseline_entitlement_year == worker_claim
    assert c1_worker.claim_move_months == increase
    assert c1_worker.reform_claim_month == 12 * 65 + increase
    assert c1.worker_entitlement_start(c1_worker) == (worker_claim, increase)
    assert base_calc.worker_entitlement_start(base_worker) == (
        worker_claim,
        0,
    )
    base_claim = base_calc._own_claim_year(base_own, base_state)
    c1_claim = c1._own_claim_year(c1_own, c1_state)
    assert (
        base_calc.excess_months_early(
            base_own, base_state, base_claim, base_worker, spouse_birth
        )
        == baseline
    )
    assert (
        c1.excess_months_early(
            c1_own, c1_state, c1_claim, c1_worker, spouse_birth
        )
        == exact
    )
    base_paid = base_calc._spouse_excess(spouse, base_state, base_own)
    c1_paid = c1._spouse_excess(spouse, c1_state, c1_own)
    assert base_paid is not None and c1_paid is not None
    # More months early than the baseline: the reform cuts the excess.
    assert c1_paid[0] < base_paid[0]
    # The rule it replaces (Track A's whole-year count on the reform
    # bundle and the moved record's reform year).
    whole = track_benefits._Calculator._spouse_excess(
        c1, spouse, c1_state, c1_own
    )
    assert (
        spouse_excess_months_early(
            own_claim_month=12 * 62,
            worker_entitlement_year=c1_worker.entitlement_year,
            birth_year=spouse_birth,
            params=projection.reforms["P3"],
        )
        == whole_year
    )
    assert whole_year != exact
    if whole_year < exact:
        assert whole[0] > c1_paid[0]
    else:
        assert whole[0] < c1_paid[0]
    if whole_year < baseline:
        # The whole-year count raised the excess above the baseline.
        assert whole[0] > base_paid[0]
    # Under C0 nothing moves and the count is Track A's on the reform
    # bundle, bit for bit.
    c0 = _calculator(projection, _scenario(projection, "reform", "P3"))
    c0_state, c0_own, c0_worker = _moved_worker_case(
        projection, c0, monkeypatch, spouse, worker
    )
    assert not isinstance(c0_worker, MovedClaimRecord)
    assert c0._spouse_excess(
        spouse, c0_state, c0_own
    ) == track_benefits._Calculator._spouse_excess(
        c0, spouse, c0_state, c0_own
    )


def _scenario_totals(
    projection, monkeypatch, spouse, worker, fields, response
):
    """INVENTED converted spouse's 2030 amounts in each C0 or C1/C2 bundle.

    ``worker`` is ``(birth year, entitlement year)`` of an INVENTED retired
    worker, moved by ``_claim_response`` under C1/C2.  Returns, for the
    baseline and P1-P3, the person's total and spouse's excess (monthly).
    """

    out = {}
    for sid in ("baseline", "P1", "P2", "P3"):
        scenario = (
            _scenario(projection, "baseline")
            if sid == "baseline"
            else _scenario(
                projection, "reform", sid, claiming_response=response
            )
        )
        calculator = _calculator(projection, scenario)
        state, own, invented = _married_to_invented_worker(
            projection, calculator, monkeypatch, spouse, worker[1], **fields
        )
        invented = replace(invented, eligibility_year=worker[0] + 62)
        record = calculator._claim_response(
            invented, worker[0], pd.Series({"claim_year": worker[1]})
        )
        original = calculator.worker_record

        def worker_record(person_id, person_state, *, _r=record, _o=original):
            if person_id == _r.person_id:
                return _r
            return _o(person_id, person_state)

        monkeypatch.setattr(calculator, "worker_record", worker_record)
        components, _ = calculator.projected_person(spouse, state)
        out[sid] = (
            sum(value[0] for value in components.values()),
            components.get("spouse", (0.0, 0.0))[0],
        )
    return out


def _converted_cases(projection):
    """(label, spouse birth, worker, state fields) for the order test."""

    persons = projection.cohort.persons
    births = set(
        persons.loc[
            persons["opening_status"].astype(str) == "none", "birth_year"
        ].astype(int)
    )
    base_calc = _calculator(projection, _scenario(projection, "baseline"))
    cases = []
    for birth in sorted(births & set(range(1940, 1964))):
        conversion = base_calc.conversion_year(birth)
        if conversion > 2030:
            continue
        converted = _converted_fields(birth, conversion)
        cases += [
            (
                "conversion_starts",
                birth,
                (birth - 3, birth - 3 + 65),
                converted,
            ),
            ("later_worker", birth, (birth - 2, conversion + 1), converted),
            (
                "claim_before_conversion",
                birth,
                (birth - 3, birth - 3 + 65),
                {**converted, "claim_year": birth + 62},
            ),
        ]
    return cases


@pytest.mark.parametrize(
    "response",
    [ClaimingResponse.FIXED, ClaimingResponse.ALL_DELAY],
)
def test_constructed_converted_spouses_keep_the_schedule_order(
    projection, monkeypatch, response
):
    # Check 2 of the review of e1-draft-5: the per-person order P2 <= P3 <=
    # P1 <= baseline (test_schedules_order_every_benefit) holds for
    # INVENTED converted spouses built to stress the conversion-claim
    # rule: the conversion starts the excess, the worker is entitled the
    # year after the conversion, or (C0 only) a retirement claim preceded
    # the conversion.  Under C2 the worker's claim moves by its own D(b_w),
    # which a conversion claim's count ignores (E1 section 11 rule 3); a
    # claim before the conversion is not a conversion claim, so its count
    # follows D(b_s) - v_w (section 13), which need not keep the order
    # across schedules, and it is left out there.  Cohorts 1940-1963
    # present in the invented roster whose baseline conversion is by 2030.
    cases = _converted_cases(projection)
    assert len(cases) >= 30
    paid = 0
    for label, birth, worker, fields in cases:
        if (
            response is not ClaimingResponse.FIXED
            and label == "claim_before_conversion"
        ):
            continue
        spouse, _ = _person_born(projection, [birth])
        amounts = _scenario_totals(
            projection, monkeypatch, spouse, worker, fields, response
        )
        for index in (0, 1):  # total, spouse's excess
            ordered = [amounts[s][index] for s in ("P2", "P3", "P1")]
            ordered.append(amounts["baseline"][index])
            assert all(
                a <= b + 1e-9
                for a, b in zip(ordered, ordered[1:], strict=False)
            ), (
                label,
                birth,
                response,
                index,
                ordered,
            )
        paid += amounts["baseline"][1] > 0
        if label != "claim_before_conversion":
            # A conversion claim's excess is the baseline's wherever the
            # scenario pays it (ratio 1).
            for sid in ("P1", "P2", "P3"):
                assert amounts[sid][1] in (0.0, amounts["baseline"][1]), (
                    label,
                    birth,
                    sid,
                )
    assert paid >= 10


def test_a_moved_worker_record_without_its_move_is_refused(projection):
    calculator = _calculator(projection, _scenario(projection, "baseline"))
    record = MovedClaimRecord(
        person_id=1,
        kind="retired",
        component="retired_worker",
        basis=track_benefits.sb.EligibilityBasis.AGE_62,
        eligibility_year=2013,
        entitlement_year=2017,
        eligibility_pia=1000.0,
        claim_age_factor=1.0,
        level_basis="invented",
        reform_claim_month=787,
        baseline_entitlement_year=2016,
    )
    with pytest.raises(ValueError, match="lacks"):
        calculator.worker_entitlement_start(record)


def test_a_claim_before_the_conversion_is_not_a_conversion_claim(
    projection, monkeypatch
):
    # A retirement claim that preceded the conversion (Track A's rule)
    # stays the own claim: its excess follows the general count and the
    # conversion-claim counters stay at zero.
    birth = 1956
    spouse, _ = _person_born(projection, [birth])
    reform_calc = _calculator(
        projection, _scenario(projection, "reform", "P2")
    )
    conversion = reform_calc.conversion_year(birth)
    fields = {
        **_converted_fields(birth, 2022),
        "claim_year": birth + 62,
    }
    state, own, worker = _married_to_invented_worker(
        projection, reform_calc, monkeypatch, spouse, 2010, **fields
    )
    assert conversion == 2024
    assert own.kind == "converted"
    assert reform_calc.conversion_claim_year(own, state) is None
    own_claim = reform_calc._own_claim_year(own, state)
    assert own_claim == birth + 62
    assert reform_calc.excess_months_early(
        own, state, own_claim, worker, birth
    ) == spouse_excess_months_early(
        own_claim_month=12 * 62,
        worker_entitlement_year=2010,
        birth_year=birth,
        params=projection.reforms["P2"],
    )
    assert reform_calc._spouse_excess(spouse, state, own) is not None
    assert CONVERSION_CLAIM_EXCESS not in reform_calc.counters
    assert CONVERSION_CLAIM_MONTHS_EARLY not in reform_calc.counters


def test_claims_made_by_the_opening_year_keep_their_age(projection):
    person, birth = _person_born(projection, range(1941, 1949))
    state = _state(projection, person, claimed=True, claim_year=2010)
    record = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.ALL_DELAY,
        ),
    ).worker_record(person, state)
    assert record.entitlement_year == max(2010, birth + 62)


def test_a_conversion_after_the_state_year_is_still_a_disabled_worker(
    projection,
):
    person, birth = _person_born(projection, [1963])
    # Converted at 67 in 2030 under the baseline (July birth month).
    state = _state(
        projection,
        person,
        di_award_year=2020,
        di_conversion_year=2030,
        claimed=True,
        claim_year=2030,
    )
    base = _calculator(projection, _scenario(projection, "baseline"))
    reform = _calculator(projection, _scenario(projection, "reform", "P3"))
    assert base.conversion_year(birth) == 2030
    assert reform.conversion_year(birth) == 2031
    base_record = base.worker_record(person, state)
    reform_record = reform.worker_record(person, state)
    assert (base_record.kind, base_record.component) == (
        "converted",
        "retired_worker",
    )
    assert (reform_record.kind, reform_record.component) == (
        "disabled",
        "disabled_worker",
    )
    assert reform_record.claim_age_factor == base_record.claim_age_factor == 1
    assert reform_record.eligibility_pia == base_record.eligibility_pia
    # A converted worker's own claim for a spouse's excess enters the
    # scenario in its conversion year (the year that gates the excess);
    # its months early are Track A's baseline count in every scenario
    # (test_a_converted_spouse_keeps_its_excess_in_every_scenario).
    born_1960, birth_1960 = _person_born(projection, [1960])
    converted = _state(
        projection,
        born_1960,
        di_award_year=2015,
        di_conversion_year=2027,
        claimed=True,
        claim_year=2027,
    )
    own = reform.worker_record(born_1960, converted)
    assert own.kind == "converted"
    assert reform._own_claim_year(own, converted) == 2028
    assert (
        base._own_claim_year(
            base.worker_record(born_1960, converted), converted
        )
        == 2027
    )


def test_a_worker_who_dies_before_the_moved_claim_is_never_entitled(
    projection, monkeypatch
):
    person, birth = _person_born(projection, range(1960, 1966))
    calculator = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.ALL_DELAY,
        ),
    )
    record = PiaRecord(
        person_id=person,
        kind="retired",
        component="retired_worker",
        basis=track_benefits.sb.EligibilityBasis.AGE_62,
        eligibility_year=birth + 62,
        entitlement_year=2029,
        eligibility_pia=1000.0,
        claim_age_factor=0.8,
        level_basis="invented",
    )
    monkeypatch.setattr(
        track_benefits._Calculator,
        "deceased_record",
        lambda self, person_id: record,
    )
    calculator.lookups = SimpleNamespace(death_year=lambda person_id: 2029)
    undone = calculator.deceased_record(person)
    assert undone.kind == "deceased_unentitled"
    assert undone.entitlement_year is None
    assert undone.claim_age_factor == 1.0
    assert undone.eligibility_pia == 1000.0
    calculator.lookups = SimpleNamespace(death_year=lambda person_id: 2030)
    assert calculator.deceased_record(person) is record


def _unentitled(person_id, birth):
    """An INVENTED never-entitled decedent record (factor 1.0)."""

    return PiaRecord(
        person_id=person_id,
        kind="deceased_unentitled",
        component="retired_worker",
        basis=track_benefits.sb.EligibilityBasis.AGE_62,
        eligibility_year=birth + 62,
        entitlement_year=None,
        eligibility_pia=1500.0,
        claim_age_factor=1.0,
        level_basis="invented",
    )


def test_survivors_of_workers_who_died_unclaimed_are_counted(projection):
    # E1 section 12 (referee required change 2): 402(e)(2)(C) and
    # 402(f)(2)(C) pass delayed credits to the survivor of a worker who
    # died unclaimed after retirement age; the model's never-entitled
    # decedent carries factor 1.0, so the run counts the survivors this
    # touches (a diagnostic; no amount changes).
    person, birth = _person_born(projection, [1954])
    base = _calculator(projection, _scenario(projection, "baseline"))
    reform = _calculator(projection, _scenario(projection, "reform", "P3"))
    # FRA 66 (baseline) and 67y1m (P3), July birth month.
    assert base.conversion_year(birth) == birth + 66
    assert reform.conversion_year(birth) == birth + 67
    record = _unentitled(person, birth)
    for calculator in (base, reform):
        # Died before the year of attaining retirement age: no credits
        # were due, nothing is counted.
        calculator._count_credits_not_inherited(
            record, person, birth + 65, False
        )
        # A claimed decedent's factor carries its credits: not counted.
        calculator._count_credits_not_inherited(
            replace(record, kind="retired", entitlement_year=birth + 66),
            person,
            birth + 69,
            False,
        )
        assert CREDITS_NOT_INHERITED not in calculator.counters
    # Died unclaimed in the baseline attainment year: counted there, not
    # under the reform, whose retirement age is attained a year later.
    base._count_credits_not_inherited(record, person, birth + 66, False)
    reform._count_credits_not_inherited(record, person, birth + 66, False)
    assert base.counters[CREDITS_NOT_INHERITED] == 1
    assert CREDITS_NOT_INHERITED not in reform.counters
    # A claim C1 or C2 moved past a death after the reform retirement age:
    # counted in both counters.
    reform._count_credits_not_inherited(record, person, birth + 68, True)
    assert reform.counters[CREDITS_NOT_INHERITED] == 1
    assert reform.counters[CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH] == 1
    assert CREDITS_NOT_INHERITED_CLAIM_MOVED_PAST_DEATH not in base.counters


def test_the_widow_excess_reports_whether_a_moved_claim_was_undone(
    projection, monkeypatch
):
    person, birth = _person_born(projection, range(1960, 1966))
    calculator = _calculator(
        projection,
        _scenario(
            projection,
            "reform",
            "P3",
            claiming_response=ClaimingResponse.ALL_DELAY,
        ),
    )
    moved = MovedClaimRecord(
        person_id=person,
        kind="retired",
        component="retired_worker",
        basis=track_benefits.sb.EligibilityBasis.AGE_62,
        eligibility_year=birth + 62,
        entitlement_year=2029,
        eligibility_pia=1000.0,
        claim_age_factor=0.8,
        level_basis="invented",
        reform_claim_month=12 * 64 + 12,
    )
    monkeypatch.setattr(
        track_benefits._Calculator,
        "deceased_record",
        lambda self, person_id: moved,
    )
    calculator.lookups = SimpleNamespace(death_year=lambda person_id: 2029)
    record, undone = calculator._decedent(person)
    assert (record.kind, undone) == ("deceased_unentitled", True)
    assert calculator.deceased_record(person) == record
    calculator.lookups = SimpleNamespace(death_year=lambda person_id: 2030)
    assert calculator._decedent(person) == (moved, False)


def test_a_scenario_calculator_needs_its_own_bundle(projection):
    scenario = _scenario(projection, "reform", "P3")
    context = BenefitContext(
        cohort=projection.cohort,
        params=projection.base,
        baseline=projection.inputs.baseline,
        config=projection.track_config,
    )
    with pytest.raises(ValueError, match="bundle"):
        ScenarioCalculator(
            context,
            TRACK_A_ROWS["R0"],
            projection.lookups,
            Counter(),
            {},
            scenario,
            assumed_birth_month=7,
        )


# --------------------------------------------------------------------------
# The end-to-end run
# --------------------------------------------------------------------------
def test_run_tabulates_every_row_under_exercise_3(result):
    assert result["schema_version"] == "populace_dynamics.fra68_track.run.v1"
    assert result["data_provenance"] == "invented"
    assert result["labels"][0] == INVENTED_COHORT_LABEL
    assert list(result["rows"]) == [f"F{k}" for k in range(9)]
    for row_id, row in result["rows"].items():
        tabulation = row["tabulation"]
        assert tabulation is not None, row["status"]
        assert row["status"].startswith("tabulated")
        assert tabulation["statistic_id"] == STATISTIC_ID
        assert tabulation["labels"][0] == INVENTED_DATA_LABEL
        assert tabulation["config"]["membership_basis"] == "scenario_specific"
        assert tabulation["config"]["allow_membership_difference"] is True
        stylized = row_id in ("F3", "F4")
        assert (STYLIZED_RESPONSE_LABEL in row["labels"]) is stylized
        if not stylized:
            assert tabulation["input_summary"]["memberships_identical"]
    assert set(result["draws"]) == {"2009", "2011"}
    json.dumps(result, allow_nan=False)


def test_run_records_parameters_and_checks(result):
    assert result["specification_check"]["consistent"], result[
        "specification_check"
    ]
    assert result["specification_check"]["specification_status"] == (
        "ratified_frozen"
    )
    assert result["specification_check"]["specification_version"] == (
        "e1-ratified-1"
    )
    assert "pending_decisions" not in result
    assert [item["field"] for item in result["max_rulings"]] == list(
        MAX_RULINGS
    )
    assert all(item["follows_ruling"] for item in result["max_rulings"])
    record = result["age_factor_parameters"]
    assert set(record["schedules"]) == {"P1", "P2", "P3"}
    for sid, schedule in record["schedules"].items():
        assert schedule["schedule_sha256"] == SCHEDULES[sid].sha256()
    assert result["cola_paths"]["identical_in_both_scenarios"] is True
    assert result["projection_identity_with_exercise_1"]["applicable"] is (
        False
    )
    window = result["di_window_diagnostic"]
    assert set(window["by_wave_schedule_draw_year"]) == {"2009", "2011"}
    assert set(window["incidence_at_start_ages"]) == {"female", "male"}
    assert result["track_a_conventions"]["config"]["rows"] == ["R0", "R6"]
    assert result["track_a_conventions"]["benefit_computation_years"] == (
        ComputationYears.LEGACY_FIXED_35.value
    )


def test_run_diagnostics_are_reported_per_row(result):
    for row in result["rows"].values():
        by_group = row["diagnostics"]["by_group"]
        assert set(by_group) == {"50-61", "62-64", "65-69", "70-79", "80+"}
        for cell in by_group.values():
            for draw in cell["union_by_draw"].values():
                assert draw["n_union"] >= max(draw["n_base"], draw["n_reform"])
    f0 = result["rows"]["F0"]["diagnostics"]["by_group"]
    # Everyone aged 62-69 in 2030 faces a 12-month increase (plan s. 3).
    for group in ("62-64", "65-69"):
        assert f0[group]["mean_fra_increase_months_weighted"] == (
            pytest.approx(12)
        )


def test_c0_rows_share_the_baseline_across_rows(result):
    def baseline_means(row_id):
        return [
            [cell["mean_benefit_base"] for cell in group["cells"]]
            for group in result["rows"][row_id]["tabulation"]["groups"]
        ]

    reference = baseline_means("F0")
    for row_id in ("F1", "F2", "F3", "F4", "F7"):
        assert baseline_means(row_id) == reference


# --------------------------------------------------------------------------
# Governance interlock
# --------------------------------------------------------------------------
def _ratified(block):
    ratified = copy.deepcopy(block)
    ratified["status"] = "ratified_frozen"
    ratified["version"] = "e1-ratified-1"
    return ratified


def _unratified(block):
    # INVENTED: the committed block under the last draft's header.
    draft = copy.deepcopy(block)
    draft["status"] = "draft_refereed_not_ratified"
    draft["version"] = "e1-draft-7"
    return draft


def test_the_committed_e1_is_ratified_with_every_ruling():
    block = e1_parameter_block()
    assert _ratified(block) == block
    assert "decisions_awaiting_max" not in block
    for name, ruling in MAX_RULINGS.items():
        assert block["decisions"][name]["ruling"] == ruling["ruling"], name
    check_specification_for_registered_run(block, FRA68Config())


def test_registered_real_needs_a_pointer_and_a_ratified_ruled_spec():
    real = replace(_cohort(2011), data_provenance="registered_real")
    real_2009 = replace(_cohort(2009), data_provenance="registered_real")
    inputs = _inputs(cohort=real, additional_cohorts=(real_2009,))
    with pytest.raises(ValueError, match="registration"):
        run_fra68(inputs, config=CONFIG)
    pointer = "INVENTED-POINTER"
    ruled = e1_parameter_block()
    with pytest.raises(ValueError, match="authorizes no real-data run"):
        run_fra68(
            inputs,
            config=CONFIG,
            registration_pointer=pointer,
            specification=_unratified(ruled),
        )
    with pytest.raises(ValueError, match="awaiting Max"):
        run_fra68(
            inputs,
            config=CONFIG,
            registration_pointer=pointer,
            specification={
                **ruled,
                "decisions_awaiting_max": {"primary_schedule_id": {}},
            },
        )
    unruled = {
        key: value for key, value in ruled.items() if key != "decisions"
    }
    with pytest.raises(ValueError, match="records no ruling"):
        run_fra68(
            inputs,
            config=CONFIG,
            registration_pointer=pointer,
            specification=unruled,
        )
    # A ruling that covers only what d188 as filed names leaves the
    # survivor span, the two exercise-1 carry-overs (d196) and the
    # computation years (covered by d188 item (a), not named) unruled.
    as_filed = {
        **ruled,
        "decisions": {
            name: value
            for name, value in ruled["decisions"].items()
            if name not in _NOT_IN_D188_AS_FILED
        },
    }
    with pytest.raises(ValueError, match="records no ruling") as refused:
        run_fra68(
            inputs,
            config=CONFIG,
            registration_pointer=pointer,
            specification=as_filed,
        )
    for name in _NOT_IN_D188_AS_FILED:
        assert name in str(refused.value)
    with pytest.raises(ValueError, match="departs from Max's rulings"):
        run_fra68(
            inputs,
            config=replace(CONFIG, primary_schedule_id="P1"),
            registration_pointer=pointer,
            specification=ruled,
        )
    with pytest.raises(ValueError, match="departs from Max's rulings"):
        run_fra68(
            inputs,
            config=CONFIG,
            registration_pointer=pointer,
            specification={
                **ruled,
                "decisions": {
                    **ruled["decisions"],
                    "di_benefit_level": {"ruling": "exclude"},
                },
            },
        )
    # A block edited to another ruling, with a configuration that follows
    # it, differs from the code's record of Max's rulings.
    reruled = copy.deepcopy(ruled)
    reruled["decisions"]["primary_schedule_id"]["ruling"] = "P1"
    with pytest.raises(ValueError, match="differ from the code's record"):
        run_fra68(
            inputs,
            config=replace(CONFIG, primary_schedule_id="P1"),
            registration_pointer=pointer,
            specification=reruled,
        )
    # The committed block (ratified, ruled, consistent) reaches the
    # committed-value checks, which the invented parameters fail.
    with pytest.raises(ValueError, match="differ from the parameters"):
        run_fra68(
            inputs,
            config=CONFIG,
            registration_pointer=pointer,
            specification=ruled,
        )


def test_every_row_records_the_e1_specification_not_a1(result):
    # Regression: the runner called A7 without a specification, so every
    # exercise-3 row recorded pending_rulings as specification_not_supplied
    # awaiting "A1 specification ratification" with A1 sections.  Each row
    # now records the E1 block header against E1's own table; the
    # committed E1 is ratified, so each convention is fixed by an E1
    # section.
    block = e1_parameter_block()
    header = {
        "specification": "urban2010_fra68_exercise3",
        "version": "e1-ratified-1",
        "status": "ratified_frozen",
        "ratified": True,
    }
    assert block["version"] == header["version"]
    assert block["status"] == header["status"]
    parameters = [ruling["parameter"] for ruling in E1_RULINGS.rulings]
    by_row = {}
    for row_id, row in result["rows"].items():
        tabulation = row["tabulation"]
        assert tabulation["specification"] == header, row_id
        entries = tabulation["pending_rulings"]
        assert [entry["parameter"] for entry in entries] == parameters
        for entry in entries:
            assert entry["status"] == "fixed_by_ratified_specification"
            assert entry["awaiting"] is None
            assert entry["fixed_by"] == (
                "E1 specification urban2010_fra68_exercise3 e1-ratified-1 "
                f"(ratified_frozen), {entry['e1_section']}"
            )
            assert "a1_section" not in entry
            assert entry["e1_section"].startswith("section ")
            assert "A1 specification" not in json.dumps(entry)
        by_row[row_id] = {entry["parameter"]: entry for entry in entries}
    # CONFIG runs two draws, not E1's K = 20; every other F0 convention is
    # E1's proposed primary, including scenario-specific membership.
    for name, entry in by_row["F0"].items():
        assert entry["is_proposed_primary"] is (name != "draw_indices"), name
    assert by_row["F0"]["allow_membership_difference"]["chosen"] is True
    assert by_row["F5"]["headline_statistic"]["is_registered_alternative"]
    assert by_row["F6"]["components"]["is_registered_alternative"]
    assert not by_row["F0"]["benefit_period"]["registered_alternatives"]


_ONE_ROW = FRA68Config(draw_indices=(0,), rows=("F0",))


def test_an_unratified_e1_header_leaves_each_convention_awaiting():
    # INVENTED un-ratification: the committed block under the last
    # draft's header.  Each convention then awaits E1's ratification,
    # which cites E1's own ruling (d188 item (c)), not A1's.
    draft = _unratified(e1_parameter_block())
    run = run_fra68(_inputs(), config=_ONE_ROW, specification=draft)
    tabulation = run["rows"]["F0"]["tabulation"]
    assert tabulation["specification"]["ratified"] is False
    awaiting = (
        f"{E1_RATIFICATION}; the E1 specification supplied is version "
        "'e1-draft-7', status 'draft_refereed_not_ratified'"
    )
    assert "d188 item (c)" in E1_RATIFICATION
    for entry in tabulation["pending_rulings"]:
        assert entry["status"] == "awaiting_ratification"
        assert entry["awaiting"] == awaiting
        assert entry["fixed_by"] is None


def test_e1s_referee_marker_binds_the_recorded_status_and_the_preflight():
    # The preflight and each row's recorded status apply one test: A7's,
    # with E1's extra "referee" marker.  A status that says "ratified"
    # but names the referee is refused by both.
    referee = {
        **_ratified(e1_parameter_block()),
        "status": "ratified_after_referee",
    }
    assert E1_RULINGS.unratified_fields(referee) == ["status"]
    run = run_fra68(_inputs(), config=_ONE_ROW, specification=referee)
    tabulation = run["rows"]["F0"]["tabulation"]
    assert tabulation["specification"]["ratified"] is False
    assert {entry["status"] for entry in tabulation["pending_rulings"]} == {
        "awaiting_ratification"
    }
    with pytest.raises(ValueError, match="authorizes no real-data run"):
        check_specification_for_registered_run(referee, FRA68Config())


def test_a_block_of_another_specification_leaves_each_row_refused():
    # An invented run records the mismatch; A7 refuses to record an A1
    # identifier against E1's sections, so the row carries no tabulation.
    block = {
        **e1_parameter_block(),
        "specification": "urban2010_cola_exercise1",
    }
    run = run_fra68(_inputs(), config=_ONE_ROW, specification=block)
    assert run["specification_check"]["mismatches"] == ["specification"]
    row = run["rows"]["F0"]
    assert row["tabulation"] is None
    assert row["status"].startswith(
        "refused: ColaTabulationError: the specification header names "
        "'urban2010_cola_exercise1'"
    )


@pytest.mark.parametrize(
    "dropped",
    [("specification", "pending_rulings"), ("pending_rulings",)],
    ids=["post-merge-call", "table-dropped"],
)
def test_a_tabulation_without_e1s_rulings_table_is_refused(
    monkeypatch, dropped
):
    # Regression: after the #454 merge (c81a2ae7) the runner passed
    # exercise 3's statistic_id but no specification and no rulings table,
    # and A7 recorded A1's conventions, sections and ratification under
    # the exercise-3 statistic without complaint.  A7 now binds the
    # statistic to the rulings table, so that call shape is refused (the
    # row records why) instead of silently recorded against A1.
    tabulate = fra68_runner.tabulate_cola_age_profile

    def without_e1_table(*args, **kwargs):
        for name in dropped:
            kwargs.pop(name)
        return tabulate(*args, **kwargs)

    monkeypatch.setattr(
        fra68_runner, "tabulate_cola_age_profile", without_e1_table
    )
    run = run_fra68(_inputs(), config=_ONE_ROW)
    row = run["rows"]["F0"]
    assert row["tabulation"] is None
    assert row["status"].startswith(
        f"refused: ColaTabulationError: statistic_id {STATISTIC_ID!r} is "
        "not the A1 specification's statistic"
    )


def test_the_specification_check_names_each_mismatch():
    block = e1_parameter_block()
    assert specification_code_check(block, FRA68Config())["consistent"]
    edited = copy.deepcopy(block)
    edited["schedules"]["P3"]["months_by_year_turning_62"]["2013"] = 800
    edited["rows"]["F6"]["components"] = ["retired_worker"]
    check = specification_code_check(edited, FRA68Config())
    assert check["mismatches"] == ["schedule_P3", "F6.components"]


@pytest.mark.parametrize(
    ("row_id", "key", "value"),
    [
        ("F0", "benefit_period", "december_2030_monthly_amount"),
        ("F0", "benefit_scale", "monthly"),
        ("F4", "behavior", "fixed_paths_shared_draws"),
        ("F0", "membership_basis", "identical"),
    ],
)
def test_the_specification_check_binds_every_row_entry(row_id, key, value):
    # E1 referee optional suggestion 7: section 21 says a registered run
    # refuses a mismatch in "the rows"; the check compared six keys per
    # row, so the benefit period, scale, behavior and membership basis the
    # block declares were not bound to the code.
    edited = copy.deepcopy(e1_parameter_block())
    edited["rows"][row_id][key] = value
    mismatches = specification_code_check(edited, FRA68Config())["mismatches"]
    if row_id == "F0":
        # F0's entries are inherited by every row that does not set them.
        assert f"F0.{key}" in mismatches
        assert all(item.endswith(f".{key}") for item in mismatches)
    else:
        assert mismatches == [f"{row_id}.{key}"]


def test_the_c1_anchor_age_is_bound_to_the_block():
    # Regression: the check compared F3's claiming-response label but not
    # the anchor age that defines it, so a ratified block and a
    # configuration with different anchors ran without a mismatch.
    block = e1_parameter_block()
    assert specification_code_check(block, FRA68Config())["consistent"]
    moved = copy.deepcopy(block)
    moved["claiming"]["C1"]["anchor_age"] = 66
    assert specification_code_check(moved, FRA68Config())["mismatches"] == [
        "claiming.C1.anchor_age"
    ]
    assert specification_code_check(moved, FRA68Config(c1_anchor_age=66))[
        "consistent"
    ]
    assert specification_code_check(block, FRA68Config(c1_anchor_age=66))[
        "mismatches"
    ] == ["claiming.C1.anchor_age"]
    ruled = copy.deepcopy(block)
    ruled["claiming"] = moved["claiming"]
    with pytest.raises(ValueError, match="claiming.C1.anchor_age"):
        check_specification_for_registered_run(ruled, FRA68Config())


def test_projection_identity_record(tmp_path):
    draws = {"2011": {"0": {"alive": 3}}, "2009": {"0": {"alive": 4}}}
    artifact = tmp_path / "exercise1.json"
    artifact.write_text(
        json.dumps({"draws": {"2011": {"0": {"alive": 3}}}}), encoding="utf-8"
    )
    record = projection_identity_record(
        draws, data_provenance="registered_real", artifact_path=artifact
    )
    assert record["matching"] == ["2011/0"]
    assert record["absent_from_exercise_1"] == ["2009/0"]
    assert record["identical"] is False
    missing = projection_identity_record(
        draws,
        data_provenance="registered_real",
        artifact_path=tmp_path / "none.json",
    )
    assert missing["compared"] is False


def test_fra_increase_is_zero_before_the_option(projection):
    assert (
        fra_increase_months(projection.base, projection.reforms["P3"], 1947)
        == 0
    )
    assert (
        fra_increase_months(projection.base, projection.reforms["P1"], 1948)
        == 0
    )
    assert (
        fra_increase_months(projection.base, projection.reforms["P3"], 1966)
        == 12
    )
