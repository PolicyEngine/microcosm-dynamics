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
    pending_decisions,
    registered_rows,
    run_fra68,
)
from populace_dynamics.fra68_track import runner as fra68_runner
from populace_dynamics.fra68_track.benefits import (
    Scenario,
    ScenarioCalculator,
    scenario_benefits,
    union_benefit_rows,
)
from populace_dynamics.fra68_track.config import (
    E1_RATIFICATION,
    E1_RULINGS,
    PENDING_DECISIONS,
    STYLIZED_RESPONSE_LABEL,
    builder_defaults,
    row_labels,
)
from populace_dynamics.fra68_track.reform import (
    SCHEDULES,
    fra_increase_months,
    reform_parameters,
    worker_factor_ratio,
)
from populace_dynamics.fra68_track.runner import (
    check_specification_for_registered_run,
    e1_parameter_block,
    projection_identity_record,
    specification_code_check,
)
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


def test_every_d188_decision_is_pending_at_its_proposed_default():
    decisions = pending_decisions(CONFIG)
    assert [item["field"] for item in decisions] == list(PENDING_DECISIONS)
    assert all(item["ruled"] is False for item in decisions)
    assert all(item["is_proposed_default"] for item in decisions)
    assert all("d188" in item["awaiting"] for item in decisions)
    changed = pending_decisions(replace(CONFIG, primary_schedule_id="P1"))
    flags = {item["field"]: item["is_proposed_default"] for item in changed}
    assert flags["primary_schedule_id"] is False
    assert {item["field"] for item in builder_defaults(CONFIG)} >= {
        "c1_anchor_age",
        "survivor_reduction_span",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"claim_class": "hold_for_track_b"},
        {"oracle_fra_schedule_override": False},
        {"acceptance_rule": "within 1 point"},
    ],
)
def test_declined_alternatives_refuse_to_run(change):
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
    # A reform equal to the baseline changes nothing.
    same = Scenario(
        name="reform",
        params=projection.base,
        baseline_params=projection.base,
        survivor_retirement_age=fixed,
    )
    reform = _people(projection, same)
    for pid, person in base.items():
        assert reform[pid].components == person.components


#: Counters Track A's ``reference_benefit_rows`` keeps per row and
#: exercise 3 keeps in ``union_benefit_rows`` instead.
_ROW_COUNTERS = (
    "beneficiaries_",
    "opening_di_basis_ended_by_recovery",
    "opening_recipient_without_record",
)


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
            if not key.startswith(_ROW_COUNTERS)
        }

    assert calculator_counts(ours) == calculator_counts(track)


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
    # A converted worker's own claim for a spouse's excess moves with the
    # scenario's conversion year.
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
        "draft_for_referee_not_ratified"
    )
    assert all(item["ruled"] is False for item in result["pending_decisions"])
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


def test_registered_real_needs_a_pointer_and_a_ratified_ruled_spec():
    real = replace(_cohort(2011), data_provenance="registered_real")
    real_2009 = replace(_cohort(2009), data_provenance="registered_real")
    inputs = _inputs(cohort=real, additional_cohorts=(real_2009,))
    with pytest.raises(ValueError, match="registration"):
        run_fra68(inputs, config=CONFIG)
    pointer = "INVENTED-POINTER"
    block = e1_parameter_block()
    with pytest.raises(ValueError, match="authorizes no real-data run"):
        run_fra68(inputs, config=CONFIG, registration_pointer=pointer)
    ratified = _ratified(block)
    with pytest.raises(ValueError, match="awaiting Max"):
        run_fra68(
            inputs,
            config=CONFIG,
            registration_pointer=pointer,
            specification=ratified,
        )
    unruled = {**ratified, "decisions_awaiting_max": {}}
    with pytest.raises(ValueError, match="records no ruling"):
        run_fra68(
            inputs,
            config=CONFIG,
            registration_pointer=pointer,
            specification=unruled,
        )
    ruled = {
        **unruled,
        "decisions": {
            name: {"ruling": value["proposed_default"]}
            for name, value in PENDING_DECISIONS.items()
        },
    }
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
    reruled = copy.deepcopy(ruled)
    reruled["decisions"]["primary_schedule_id"]["ruling"] = "P1"
    with pytest.raises(ValueError, match="differ"):
        run_fra68(
            inputs,
            config=replace(CONFIG, primary_schedule_id="P1"),
            registration_pointer=pointer,
            specification=reruled,
        )
    # A ratified, ruled, consistent block reaches the committed-value
    # checks, which the invented parameters fail.
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
    # now records the E1 block header against E1's own table.
    block = e1_parameter_block()
    header = {
        "specification": "urban2010_fra68_exercise3",
        "version": block["version"],
        "status": block["status"],
        "ratified": False,
    }
    awaiting = (
        f"{E1_RATIFICATION}; the E1 specification supplied is version "
        f"{block['version']!r}, status {block['status']!r}"
    )
    parameters = [ruling["parameter"] for ruling in E1_RULINGS.rulings]
    by_row = {}
    for row_id, row in result["rows"].items():
        tabulation = row["tabulation"]
        assert tabulation["specification"] == header, row_id
        entries = tabulation["pending_rulings"]
        assert [entry["parameter"] for entry in entries] == parameters
        for entry in entries:
            assert entry["status"] == "awaiting_ratification"
            assert entry["awaiting"] == awaiting
            assert entry["fixed_by"] is None
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


def test_a_ratified_e1_header_fixes_the_conventions_by_e1_sections():
    # INVENTED ratification: the committed E1 is a draft.
    ratified = _ratified(e1_parameter_block())
    run = run_fra68(_inputs(), config=_ONE_ROW, specification=ratified)
    tabulation = run["rows"]["F0"]["tabulation"]
    assert tabulation["specification"]["ratified"] is True
    for entry in tabulation["pending_rulings"]:
        assert entry["status"] == "fixed_by_ratified_specification"
        assert entry["awaiting"] is None
        assert entry["fixed_by"] == (
            "E1 specification urban2010_fra68_exercise3 e1-ratified-1 "
            f"(ratified_frozen), {entry['e1_section']}"
        )


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
    ruled = {
        **_ratified(block),
        "decisions_awaiting_max": {},
        "decisions": {
            name: {"ruling": value["proposed_default"]}
            for name, value in PENDING_DECISIONS.items()
        },
    }
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
