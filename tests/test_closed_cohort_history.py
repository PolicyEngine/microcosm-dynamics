"""Invented closed-cohort records using actual mortality and earnings steps."""

import json
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from populace_dynamics.closed_cohort_history import ClosedCohortEarningsHistory
from populace_dynamics.covered_wage_history import (
    CoveredWageHistory,
    CoveredWageObservation,
    SourceAmount,
)
from populace_dynamics.engine.earnings_domain import EarningsDomainAdapter
from populace_dynamics.engine.loop import PeriodContext
from populace_dynamics.engine.rng import ProjectionRNGRegistry
from populace_dynamics.engine.steps import (
    AgeSexMortalityModel,
    advance_age,
    apply_earnings,
    apply_mortality,
)
from populace_dynamics.forward_earnings_history import ForwardEarningsHistory
from populace_dynamics.mortality_observer import observe_mortality
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap
from tests.test_m6_engine_correlated_refresh import _correlated
from tests.test_m6_engine_forward_earnings import _generator


def setup(*, death_year=2016, correlated=False):
    mapping = PersonIdentityMap.from_identities(
        [
            PersonIdentity("int64", -(2**63)),
            PersonIdentity("string", "001"),
            *(PersonIdentity("uint64", 2**64 - 1 - i) for i in range(19)),
        ]
    )
    generator = EarningsDomainAdapter(
        _correlated(rho=-0.5) if correlated else _generator()
    )
    initial = pd.DataFrame(
        {
            "person_id": np.array([20, 10, 1, 0], dtype="int64"),
            "year": np.full(4, 2014, dtype="int64"),
            "age": np.array(
                [32, 35 - ((death_year or 2016) - 2015), 31, 30], dtype="int64"
            ),
            "sex": ["female", "male", "female", "female"],
        }
    )
    frame = generator.materialize_initial_frame(initial)
    history = ForwardEarningsHistory.start(
        mapping,
        frame,
        realization_id="invented-cohort",
        generator_digest="a" * 64,
        source_contract_digest="b" * 64,
        lineage_digest="c" * 64,
        unit="XTS",
        price_basis="nominal",
    )
    mortality = AgeSexMortalityModel(
        ((0, 34), (35, 120)),
        {
            ("0-34", "female"): 0.0,
            ("0-34", "male"): 0.0,
            ("35+", "female"): 0.0,
            ("35+", "male"): float(death_year is not None),
        },
    )
    return frame, generator, history, mortality


def step(frame, year, generator, baseline, model, *, registry=True):
    context = PeriodContext(
        year - 2014,
        year,
        3,
        {},
        rng_registry=ProjectionRNGRegistry(3, 8) if registry else None,
        person_ordinals={0: 0, 1: 1, 10: 2, 20: 3},
    )
    rng = np.random.default_rng(year)
    survivors, mortality = observe_mortality(
        frame,
        context,
        rng,
        model=model,
        identity_map=baseline.identity_map,
        realization_id=baseline.realization_id,
        source_contract_digest="d" * 64,
    )
    aged = advance_age(survivors, context, rng)
    earnings = apply_earnings(aged, context, rng, model=generator)
    return earnings, mortality, context, rng


@pytest.mark.parametrize("death_year", [2015, 2016, 2022, None])
@pytest.mark.parametrize("correlated", [False, True])
@pytest.mark.parametrize("registry", [False, True])
def test_actual_steps_preserve_frames_rng_and_history(
    death_year, correlated, registry
):
    frame, generator, baseline, model = setup(
        death_year=death_year, correlated=correlated
    )
    cohort = ClosedCohortEarningsHistory.start(baseline, draw_index=3)
    baseline_json = baseline.to_json()
    control = frame.copy(deep=True)
    snapshots = [cohort]
    for year in range(2015, 2023):
        frame, mortality, context, rng = step(
            frame, year, generator, baseline, model, registry=registry
        )
        direct_rng = np.random.default_rng(year)
        control = apply_mortality(control, context, direct_rng, model=model)
        control = advance_age(control, context, direct_rng)
        control = apply_earnings(control, context, direct_rng, model=generator)
        before = frame.copy(deep=True)
        cohort = cohort.append(
            mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
        )
        snapshots.append(cohort)
        assert_frame_equal(frame, control)
        assert_frame_equal(frame, before)
        assert rng.bit_generator.state == direct_rng.bit_generator.state
        assert cohort.active_keys == tuple(sorted(frame.person_id))
        cohort.require_extension_of(snapshots[-2])
    dead_identity = baseline.identity_map.reverse_rows([10])[0]
    dead_history = cohort.for_person(dead_identity)
    assert dead_history.last_year == (death_year - 1 if death_year else 2022)
    assert (
        dead_history.observations[0] == baseline.for_person(dead_identity)[0]
    )
    if death_year:
        assert (
            cohort.amount_state(dead_identity, year=death_year)
            == "not_generated_after_mortality_step"
        )
        assert cohort.death_step(dead_identity).target_year == death_year
        assert all(row.year < death_year for row in dead_history.observations)
    else:
        assert cohort.death_step(dead_identity) is None
    assert baseline.to_json() == baseline_json
    for key in (1, 20):
        history = cohort.for_person(
            baseline.identity_map.reverse_rows([key])[0]
        )
        assert len(history.observations) == 9
        for prior, row in zip(
            history.observations[:-1], history.observations[1:], strict=True
        ):
            if row.year % 2:
                assert row.amount_hex == prior.amount_hex
    outside = baseline.identity_map.reverse_rows([0])[0]
    assert cohort.amount_state(outside, year=2022) == "unavailable"
    restored = ClosedCohortEarningsHistory.from_json(
        cohort.to_json(),
        baseline=baseline,
        expected_digest=cohort.digest,
        previous=snapshots[3],
    )
    assert restored == cohort
    assert restored.to_json() == cohort.to_json()


def test_extinction_preserves_all_past_rows_and_observes_empty_years():
    frame, generator, baseline, model = setup()
    model = replace(model, probability=dict.fromkeys(model.probability, 1.0))
    cohort = ClosedCohortEarningsHistory.start(baseline, draw_index=3)
    initial_histories = cohort.histories
    for year in range(2015, 2023):
        frame, mortality, _, _ = step(frame, year, generator, baseline, model)
        assert frame.empty
        cohort = cohort.append(
            mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
        )
        assert cohort.histories == initial_histories
        assert cohort.active_keys == ()
        assert cohort.last_year == year
    assert len(cohort.transitions) == 8
    assert (
        ClosedCohortEarningsHistory.from_json(
            cohort.to_json(), baseline=baseline
        )
        == cohort
    )
    with pytest.raises(ValueError, match="2022"):
        cohort.append(
            mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
        )


@pytest.fixture
def first():
    frame, generator, baseline, model = setup()
    cohort = ClosedCohortEarningsHistory.start(baseline, draw_index=3)
    frame, mortality, _, _ = step(frame, 2015, generator, baseline, model)
    return cohort, frame, mortality, generator, model


@pytest.mark.parametrize(
    "column,values",
    [
        ("age", [32, 35, 33, 31]),
        ("age", [31.0, 32.0, 35.0, 33.0]),
        ("sex", ["male"] * 4),
        ("year", [2016] * 4),
        ("person_id", [0, 1, 10, 10]),
        ("person_id", [0, 1, 10, 19]),
        ("person_id", [0.0, 1.0, 10.0, 20.0]),
        ("earnings_domain", [True] * 4),
        ("earnings", [0.0] * 4),
    ],
)
def test_bad_survivor_frame_refuses(first, column, values):
    cohort, frame, mortality, _, _ = first
    frame[column] = values
    with pytest.raises(ValueError):
        cohort.append(
            mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
        )
    assert cohort.last_year == 2014


def test_missing_survivor_and_dead_reintroduced_refuse(first):
    cohort, frame, mortality, generator, model = first
    with pytest.raises(ValueError, match="survivor"):
        cohort.append(
            mortality=mortality,
            earnings_frame=frame.iloc[:-1],
            lineage_digest="e" * 64,
        )
    cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    next_frame, next_mortality, _, _ = step(
        frame, 2016, generator, cohort.baseline, model
    )
    extra = frame.loc[frame.person_id == 10].copy()
    extra["year"], extra["age"] = 2016, 36
    with pytest.raises(ValueError, match="survivor"):
        cohort.append(
            mortality=next_mortality,
            earnings_frame=pd.concat([next_frame, extra]),
            lineage_digest="e" * 64,
        )
    fixed = cohort.baseline.append(frame, lineage_digest="e" * 64)
    with pytest.raises(ValueError, match="roster"):
        fixed.append(next_frame, lineage_digest="e" * 64)


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_year", 2016),
        ("period_index", 2),
        ("draw_index", 4),
        ("realization_id", "other"),
    ],
)
def test_wrong_initial_mortality_binding_refuses(first, field, value):
    cohort, frame, mortality, _, _ = first
    with pytest.raises(ValueError):
        cohort.append(
            mortality=replace(mortality, **{field: value}),
            earnings_frame=frame,
            lineage_digest="e" * 64,
        )


@pytest.mark.parametrize(
    "change", ["age", "sex", "ordinal", "source", "model", "horizon"]
)
def test_consecutive_mortality_drift_refuses(first, change):
    cohort, frame, mortality, generator, model = first
    cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    frame, next_mortality, _, _ = step(
        frame, 2016, generator, cohort.baseline, model
    )
    rows = list(next_mortality.rows)
    if change in ("age", "sex", "ordinal"):
        row = rows[0]
        field, value = {
            "age": ("age", row.age + 2),
            "sex": ("sex", "male"),
            "ordinal": ("person_ordinal", 99),
        }[change]
        rows[0] = replace(row, **{field: value})
        next_mortality = replace(next_mortality, rows=tuple(rows))
        if change in ("age", "sex"):
            # Even a matching altered output must not evade cross-step checks.
            frame.loc[frame.person_id == row.dynamics_person_key, field] = (
                value + 1 if field == "age" else value
            )
    elif change == "source":
        next_mortality = replace(
            next_mortality, source_contract_digest="f" * 64
        )
    elif change == "horizon":
        next_mortality = replace(next_mortality, registry_n_periods=9)
    else:
        cells = list(next_mortality.model.cells)
        cells[0] = (*cells[0][:2], (0.1).hex(), cells[0][3])
        next_mortality = replace(
            next_mortality,
            model=replace(next_mortality.model, cells=tuple(cells)),
        )
    with pytest.raises(ValueError):
        cohort.append(
            mortality=next_mortality,
            earnings_frame=frame,
            lineage_digest="e" * 64,
        )


def test_frame_order_and_source_sidecar_remain_independent(first):
    cohort, frame, mortality, _, _ = first
    sidecar = CoveredWageHistory(
        cohort.baseline,
        "f" * 64,
        tuple(
            CoveredWageObservation(
                key, 2014, SourceAmount("decimal", "7.00"), None, "a" * 64
            )
            for key in cohort.baseline.roster_keys
        ),
    )
    before = sidecar.to_json()
    next_cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    permuted = cohort.append(
        mortality=mortality,
        earnings_frame=frame.iloc[::-1],
        lineage_digest="e" * 64,
    )
    assert next_cohort == permuted
    assert sidecar.to_json() == before
    assert sidecar.history.digest == cohort.baseline.digest
    assert sidecar.history.last_year == 2014
    with pytest.raises(FrozenInstanceError):
        next_cohort.draw_index = 9


@pytest.mark.parametrize(
    "change",
    [
        "drop_history",
        "drop_transition",
        "demographics",
        "lineage",
        "old_amount",
        "extra",
        "last_year",
    ],
)
def test_persistence_refuses_inconsistent_composition(first, change):
    cohort, frame, mortality, _, _ = first
    cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    doc = json.loads(cohort.to_json())
    if change == "drop_history":
        doc["histories"].pop()
    elif change == "drop_transition":
        doc["transitions"].clear()
    elif change == "demographics":
        doc["transitions"][0]["survivor_demographics"][0][1] = "99"
    elif change == "lineage":
        doc["transitions"][0]["lineage_digest"] = "f" * 64
    elif change == "old_amount":
        doc["histories"][1]["observations"][0]["amount_hex"] = (13.0).hex()
        doc["histories"][1]["observations"][1]["amount_hex"] = (13.0).hex()
    elif change == "last_year":
        doc["last_year"] = "2016"
    else:
        doc["accepted"] = True
    with pytest.raises(ValueError):
        ClosedCohortEarningsHistory.from_json(
            json.dumps(doc), baseline=cohort.baseline
        )


def test_external_baseline_digest_prefix_and_query_bounds(first):
    cohort, frame, mortality, _, _ = first
    next_cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    with pytest.raises(ValueError, match="baseline"):
        ClosedCohortEarningsHistory.from_json(
            next_cohort.to_json(),
            baseline=replace(cohort.baseline, realization_id="other"),
        )
    with pytest.raises(ValueError, match="digest"):
        ClosedCohortEarningsHistory.from_json(
            next_cohort.to_json(),
            baseline=cohort.baseline,
            expected_digest="0" * 64,
        )
    with pytest.raises(ValueError):
        ClosedCohortEarningsHistory.from_json(
            cohort.to_json(), baseline=cohort.baseline, previous=next_cohort
        )
    duplicate = next_cohort.to_json().replace("{", '{"schema":"duplicate",', 1)
    with pytest.raises(ValueError, match="duplicate"):
        ClosedCohortEarningsHistory.from_json(
            duplicate, baseline=cohort.baseline
        )
    identity = cohort.baseline.identity_map.reverse_rows([1])[0]
    for year in (2013, 2016, True, 2014.0):
        with pytest.raises(ValueError):
            next_cohort.amount_state(identity, year=year)
    with pytest.raises(ValueError):
        next_cohort.for_person(
            cohort.baseline.identity_map.reverse_rows([2])[0]
        )


@pytest.mark.parametrize(
    "column,dtype",
    [
        ("person_id", "float64"),
        ("age", "float64"),
        ("year", "float64"),
        ("earnings", "int64"),
        ("earnings_domain", "float64"),
        ("sex", "float64"),
    ],
)
def test_empty_frame_still_requires_exact_types(first, column, dtype):
    cohort, frame, mortality, _, _ = first
    mortality = replace(
        mortality,
        rows=tuple(replace(row, survived=False) for row in mortality.rows),
    )
    frame = frame.iloc[:0].copy()
    frame[column] = frame[column].astype(dtype)
    with pytest.raises(ValueError):
        cohort.append(
            mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
        )


@pytest.mark.parametrize("change", ["age", "sex", "death"])
def test_loaded_cross_step_demographics_and_death_extents_refuse(
    first, change
):
    cohort, frame, mortality, generator, model = first
    cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    frame, mortality, _, _ = step(
        frame, 2016, generator, cohort.baseline, model
    )
    cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    document = json.loads(cohort.to_json())
    transition = document["transitions"][1]
    if change == "death":
        dead = next(
            row
            for row in transition["mortality"]["rows"]
            if row["dynamics_person_key"] == "10"
        )
        dead["survived"] = True
        transition["survivor_demographics"].insert(2, ["10", "36", "male"])
    else:
        row = transition["mortality"]["rows"][0]
        if change == "age":
            row["age"] = "70"
            transition["survivor_demographics"][0][1] = "71"
        else:
            row["sex"] = "male"
            transition["survivor_demographics"][0][2] = "male"
    with pytest.raises(ValueError):
        ClosedCohortEarningsHistory.from_json(
            json.dumps(document), baseline=cohort.baseline
        )


def test_closed_roster_does_not_allow_new_or_resurrected_mortality_rows(first):
    cohort, frame, mortality, generator, model = first
    cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    next_frame, next_mortality, _, _ = step(
        frame, 2016, generator, cohort.baseline, model
    )
    cohort = cohort.append(
        mortality=next_mortality,
        earnings_frame=next_frame,
        lineage_digest="e" * 64,
    )
    # Reusing the earlier cohort as a 2017 input resurrects key 10.
    resurrected_frame = frame.copy()
    resurrected_frame["year"] = 2016
    resurrected_frame["age"] += 1
    final_frame, resurrected, _, _ = step(
        resurrected_frame, 2017, generator, cohort.baseline, model
    )
    with pytest.raises(ValueError, match="roster"):
        cohort.append(
            mortality=resurrected,
            earnings_frame=final_frame,
            lineage_digest="e" * 64,
        )
    # Even a previously known identity outside the original cohort is an entrant.
    rows = list(mortality.rows)
    rows.insert(2, replace(rows[0], dynamics_person_key=2, person_ordinal=99))
    entrant = replace(mortality, rows=tuple(rows))
    extra = frame.iloc[[0]].copy()
    extra["person_id"] = 2
    with pytest.raises(ValueError, match="roster"):
        ClosedCohortEarningsHistory.start(
            cohort.baseline, draw_index=3
        ).append(
            mortality=entrant,
            earnings_frame=pd.concat([frame, extra]),
            lineage_digest="e" * 64,
        )


def test_zero_missing_death_and_unobserved_are_distinct(first):
    cohort, _, _, _, _ = first
    baseline = replace(
        cohort.baseline,
        observations=tuple(
            (
                replace(row, amount_hex=(0.0).hex())
                if row.dynamics_person_key == 1
                else row
            )
            for row in cohort.baseline.observations
        ),
    )
    cohort = ClosedCohortEarningsHistory.start(baseline, draw_index=3)
    zero, unknown = (
        baseline.identity_map.reverse_rows([key])[0] for key in (1, 0)
    )
    assert cohort.amount_state(zero, year=2014) == "known_zero"
    assert cohort.amount_state(unknown, year=2014) == "unavailable"
    assert cohort.death_step(zero) is None
    with pytest.raises(ValueError):
        cohort.amount_state(zero, year=2015)


def test_append_is_detached_and_cannot_skip_or_repeat(first):
    cohort, frame, mortality, _, _ = first
    result = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    original_json = result.to_json()
    frame.loc[:, "age"] += 10
    frame.loc[:, "earnings"] = 123.0
    assert result.to_json() == original_json
    assert cohort.last_year == 2014
    with pytest.raises(ValueError):
        result.append(
            mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
        )
    with pytest.raises(ValueError, match="2014"):
        ClosedCohortEarningsHistory.start(result.histories[0], draw_index=3)


def test_fallback_rng_records_are_supported_and_mode_switch_refuses(first):
    cohort, frame, mortality, generator, model = first
    mortality = replace(
        mortality,
        registry_n_periods=None,
        rows=tuple(
            replace(row, person_ordinal=None) for row in mortality.rows
        ),
    )
    cohort = cohort.append(
        mortality=mortality, earnings_frame=frame, lineage_digest="e" * 64
    )
    assert (
        ClosedCohortEarningsHistory.from_json(
            cohort.to_json(), baseline=cohort.baseline
        )
        == cohort
    )
    frame, registry_mortality, _, _ = step(
        frame, 2016, generator, cohort.baseline, model
    )
    with pytest.raises(ValueError, match="RNG mode"):
        cohort.append(
            mortality=registry_mortality,
            earnings_frame=frame,
            lineage_digest="e" * 64,
        )
