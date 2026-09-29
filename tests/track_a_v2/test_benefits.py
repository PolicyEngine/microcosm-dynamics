"""INVENTED D/S levels, integration, replay and differentials (§12)."""

import dataclasses
import math

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a import benefits as legacy
from populace_dynamics.cola_track_a.config import REGISTERED_ROWS, LevelPolicy
from populace_dynamics.cola_track_a.opening import OpeningStockRecord
from populace_dynamics.fra68_track import benefits as fra
from populace_dynamics.min_benefit_track_m.rules import history_pia
from populace_dynamics.ss import benefits as ss
from populace_dynamics.ss import statutory_aime as statutory
from populace_dynamics.track_a_v2.benefits import (
    collect_reference_benefit_rows,
    scenario_benefits,
    statutory_di_aime,
    statutory_di_pia,
)
from tests.track_a_v2._invented import build, calculator, parameters


class NonflatParameters(type(parameters())):
    def bend_points(self, year):
        return (400.0, 2000.0) if year == 1990 else (800.0, 4000.0)


def nonflat():
    base = parameters(
        nawi={1987: 100.0, 1988: 200.0},
        wage_base={1987: 6000.0, 1988: 1e9},
        pia_factors=(0.9, 0.32, 0.15),
    )
    return NonflatParameters(**dataclasses.asdict(base))


@pytest.mark.parametrize(
    "elapsed", [0, 1, 2, 4, 5, 9, 10, 14, 15, 19, 20, 24, 25, 29, 30, 40]
)
def test_statutory_boundaries(elapsed):
    """Computation years equal elapsed less capped fifth, with minimum two."""
    e = 1960 + 22 + elapsed
    assert statutory.elapsed_years(1960, disability_year=e) == elapsed
    assert statutory.benefit_computation_years(1960, disability_year=e) == max(
        2, elapsed - min(5, elapsed // 5)
    )


def test_original_statutory_fixtures():
    """D selects N highest values with ties/zero padding; levels keep floors."""
    params = parameters()
    assert statutory.elapsed_years(1960, disability_year=1990) == 8
    assert statutory.benefit_computation_years(1960, disability_year=1990) == 7
    assert statutory.indexing_year(1960, disability_year=1990) == 1988
    assert statutory.benefit_computation_years(1960, death_year=1990) == 3
    assert statutory.elapsed_years(1960) == 40
    assert statutory.benefit_computation_years(1960) == 35
    history = {year: 12000.0 for year in range(1983, 1991)}
    assert (
        statutory_di_aime(
            history, birth_year=1960, eligibility_year=1990, params=params
        )
        == 1000
    )
    assert ss.aime(history, 1928, params) == 228
    assert (
        statutory_di_aime(
            {1990: 12000},
            birth_year=1960,
            eligibility_year=1990,
            params=params,
        )
        == 142
    )
    assert statutory.elapsed_years(1950, disability_year=2014) == 40
    assert (
        statutory.benefit_computation_years(1950, disability_year=2014) == 35
    )
    assert statutory_di_pia(
        history, birth_year=1950, eligibility_year=2014, params=params
    ) == legacy.approximate_pia(
        history,
        birth_year=1950,
        eligibility_year=2014,
        computation_end_year=2014,
        params=params,
    )


@pytest.mark.parametrize(
    "birth,onset,history",
    [
        (1912, 1990, {}),
        (1960, 1959, {}),
        (1960, 1990, {1950: 10}),
    ],
)
def test_helper_refusals(birth, onset, history):
    """Intended unsupported dates/base years refuse instead of falling back."""
    with pytest.raises(ValueError):
        statutory_di_aime(
            history,
            birth_year=birth,
            eligibility_year=onset,
            params=parameters(),
        )
    with pytest.raises(ValueError):
        statutory.aime(
            {}, 1960, parameters(), disability_year=1990, death_year=1991
        )


def test_nonflat_ceiling_cutoff_indexing_and_bendpoints():
    """Cap then index; inclusive cutoff and e bend points produce 428/368.9."""
    params = nonflat()
    history = {1987: 12000, 1988: 6000, 1989: 6000, 1990: 12000, 1991: 999999}
    assert (
        statutory_di_aime(
            history, birth_year=1960, eligibility_year=1990, params=params
        )
        == 428
    )
    assert (
        statutory_di_pia(
            history, birth_year=1960, eligibility_year=1990, params=params
        )
        == 368.9
    )
    kept = {y: v for y, v in history.items() if y <= 1990}
    assert (
        statutory.aime(
            {y: v for y, v in kept.items() if y < 1990},
            1960,
            params,
            disability_year=1990,
        )
        == 285
    )
    assert statutory.aime(history, 1960, params, disability_year=1990) == 12333
    assert (
        statutory.aime(
            kept,
            1960,
            dataclasses.replace(params, wage_base={1987: 1e9}),
            disability_year=1990,
        )
        == 571
    )
    assert (
        statutory.aime(
            kept,
            1960,
            dataclasses.replace(params, nawi={1987: 200.0, 1988: 200.0}),
            disability_year=1990,
        )
        == 357
    )
    assert ss.aime(kept, 1928, params) == 85
    assert (
        statutory.aime_with_computation_years(
            kept, 7, params, indexing_year=1987
        )
        == 357
    )
    with pytest.raises(KeyError):
        statutory.aime_with_computation_years(
            kept, 7, params, indexing_year=1989
        )
    assert ss.pia(428, 2022, params) != 368.9


@settings(deadline=None)
@given(
    st.lists(st.integers(0, 1000000), max_size=40),
    st.integers(2, 35),
    st.integers(0, 1000000),
)
def test_highest_years_bounds_monotonicity_cutoff(values, count, increment):
    """Nonnegative earnings monotonicity, D>=L, N bounds and frozen cutoff."""
    params = parameters()
    history = {1951 + i: float(v) for i, v in enumerate(values)}
    short = statutory.aime_with_computation_years(
        history, count, params, indexing_year=1988
    )
    long = statutory.aime_with_computation_years(
        history, 35, params, indexing_year=1988
    )
    assert short >= long
    raised = {**history, 1951: history.get(1951, 0) + increment}
    assert (
        statutory.aime_with_computation_years(
            raised, count, params, indexing_year=1988
        )
        >= short
    )
    before = statutory_di_aime(
        history, birth_year=1960, eligibility_year=1990, params=params
    )
    assert (
        statutory_di_aime(
            {**history, 2030: 1e9},
            birth_year=1960,
            eligibility_year=1990,
            params=params,
        )
        == before
    )
    assert (
        2
        <= statutory.benefit_computation_years(
            1960, disability_year=1960 + count
        )
        <= 35
    )
    assert (
        statutory_di_aime(
            {y: 0 for y in history},
            birth_year=1960,
            eligibility_year=1990,
            params=params,
        )
        == 0
    )


@pytest.mark.parametrize("fixture", ["nonflat", "one_dollar", "after62"])
def test_track_m_cutoff_differential(fixture):
    """Same-e AIME difference equals the difference of floors, not dollars."""
    if fixture == "nonflat":
        params, e = nonflat(), 1990
        history = {1987: 12000, 1988: 6000, 1989: 6000, 1990: 12000}
        total, delta, count, expected = 24000, 12000, 7, (428, 285, 143)
    elif fixture == "one_dollar":
        params, e, history = parameters(), 1990, {1990: 1}
        total, delta, count, expected = 0, 1, 7, (0, 0, 0)
    else:
        params, e = parameters(), 2022
        history = {2022: 4200, 2023: 8400, 2024: 16800}
        total, delta, count, expected = 0, 4200, 35, (10, 0, 10)
    d = statutory_di_aime(
        history, birth_year=1960, eligibility_year=e, params=params
    )
    m = history_pia(
        history,
        birth_year=1960,
        params=params,
        basis="disability",
        onset_year=e,
    )
    difference = math.floor((total + delta) / (12 * count)) - math.floor(
        total / (12 * count)
    )
    assert (d, m.aime, d - m.aime) == expected
    assert d - m.aime == difference
    assert m.computation_end_year == e - 1 and m.eligibility_year == e
    if fixture == "after62":
        raw = history_pia(
            history,
            birth_year=1960,
            params=params,
            basis="disability",
            onset_year=2024,
        )
        assert raw.aime == 30
        assert (
            raw.computation_end_year == 2023 and raw.eligibility_year == 2024
        )
        assert statutory.indexing_year(1960, disability_year=e) == 2020
    else:
        assert statutory_di_pia(
            history, birth_year=1960, eligibility_year=e, params=params
        ) == ss.pia(d, m.eligibility_year, params)


@pytest.mark.parametrize("exercise", [1, 3])
@pytest.mark.parametrize(
    "relation",
    ["spouse", "widow_converted", "widow_active", "standalone_death"],
)
def test_changed_own_offsets_unchanged_ordinary_record(exercise, relation):
    """Own plus excess accounting conserves total against an unchanged worker."""
    active = relation in ("widow_active", "standalone_death")
    own = dict(
        id=1,
        birth=1965 if active else 1960,
        awards=(2022 if active else 2017,),
        conversion=None if active else 2027,
        claim=None if active else 2027,
    )
    worker = dict(
        id=2,
        birth=1970 if relation == "standalone_death" else 1960,
        claim=None if relation == "standalone_death" else 2027,
    )
    if relation == "spouse":
        own.update(marital="married", spouse=2)
        worker_history = 840000
    else:
        own.update(marital="widowed", late_spouse=2, widowhood=2030)
        worker["death"] = 2030
        worker_history = 672000
    cohort, result = build(
        [own, worker], careers={1: {1987: 252000}, 2: {1987: worker_history}}
    )
    values, records = [], []
    for mechanism in ("L", "D"):
        calc = calculator(
            cohort, result, mechanism=mechanism, exercise=exercise
        )
        values.append(calc.projected_person(1, calc.lookups.final.loc[1])[0])
        records.append(
            calc.worker_record(2, calc.lookups.final.loc[2])
            if relation == "spouse"
            else calc.deceased_record(2)
        )
    component = "disabled_worker" if active else "retired_worker"
    excess = "spouse" if relation == "spouse" else "aged_widow"
    assert [v[component][0] for v in values] == [600, 700]
    assert [v[excess][0] for v in values] == (
        [400, 300] if relation == "spouse" else [1000, 900]
    )
    assert records[0] == records[1]
    assert [sum(pair[0] for pair in v.values()) for v in values] == (
        [1000, 1000] if relation == "spouse" else [1600, 1600]
    )


@pytest.mark.parametrize("exercise", [1, 3])
@pytest.mark.parametrize(
    "dead,opening",
    [(False, False), (True, False), (False, True), (True, True)],
)
def test_linked_di_levels_and_intact_opening(exercise, dead, opening):
    """Linked DI inputs may change auxiliaries; intact observed own stays fixed."""
    worker = dict(
        id=2,
        birth=1960,
        awards=() if opening else (2017,),
        conversion=2027,
        claim=2027,
        death=2030 if dead else 9999,
        opening_di=opening,
        opening_status="disabled_worker" if opening else "nonrecipient",
    )
    own = dict(
        id=1,
        birth=1960,
        claim=2027,
        marital="widowed" if dead else "married",
        spouse=2,
        late_spouse=2 if dead else None,
        widowhood=2030 if dead else None,
    )
    opening_records = (
        {
            2: OpeningStockRecord(
                2,
                "disabled_worker",
                "disabled_worker",
                12000,
                1990,
                "receipt",
                1990,
                False,
            )
        }
        if opening
        else {}
    )
    cohort, result = build(
        [own, worker], careers={2: {1987: 252000}}, opening=opening_records
    )
    values = []
    for mechanism in ("L", "D"):
        calc = calculator(
            cohort, result, mechanism=mechanism, exercise=exercise
        )
        values.append(calc.projected_person(1, calc.lookups.final.loc[1])[0])
        if opening and not dead:
            observed = calc.opening_person(
                opening_records[2], calc.lookups.final.loc[2]
            )
            assert observed[0]["retired_worker"] == (1000, 1000)
    component = "aged_widow" if dead else "spouse"
    assert values[1][component][0] > values[0][component][0]


@pytest.mark.parametrize("exercise", [1, 3])
def test_legacy_replay_cache_isolation_and_projection_identity(exercise):
    """L replays v1 exactly; shared caches and invocation order cannot leak D."""
    cohort, result = build(
        [
            dict(
                id=1,
                awards=(2017,),
                conversion=2027,
                claim=2027,
                marital="married",
                spouse=2,
            ),
            dict(id=2, claim=2027),
            dict(id=3, birth=1980),
        ],
        careers={1: {1987: 252000}, 2: {1987: 840000}},
    )
    before = tuple(frame.copy(deep=True) for frame in result.slices)
    cache, outputs = {}, {}
    for order in (
        ("L", "D", "S", "DS"),
        ("DS", "S", "D", "L"),
        ("D", "L", "DS", "S", "D"),
    ):
        for mechanism in order:
            calc = calculator(
                cohort,
                result,
                mechanism=mechanism,
                exercise=exercise,
                cache=cache,
            )
            value = calc.projected_person(1, calc.lookups.final.loc[1])
            assert mechanism not in outputs or outputs[mechanism] == value
            outputs[mechanism] = value
    legacy_d = calculator(
        cohort,
        result,
        mechanism="D",
        exercise=exercise,
        cache=cache,
        di_computation="legacy_fixed_35",
    )
    assert (
        legacy_d.projected_person(1, legacy_d.lookups.final.loc[1])
        == outputs["L"]
    )
    assert outputs["L"] == outputs["S"]
    assert outputs["D"] == outputs["DS"]
    for old, now in zip(before, result.slices, strict=True):
        pd.testing.assert_frame_equal(old, now)
    for row_id in (f"R{i}" for i in range(6)):
        calc = calculator(cohort, result, row=row_id)
        kwargs = dict(draw=0, row=REGISTERED_ROWS[row_id], context=calc.ctx)
        old, old_counts = legacy.reference_benefit_rows(result, **kwargs)
        new, new_counts = collect_reference_benefit_rows(result, **kwargs)
        assert old == [r for r in new if r["benefit_base"] > 0]
        assert old_counts == new_counts
    for response in (
        "fixed",
        "at_or_after_anchor_delay",
        "all_projected_delay",
    ):
        calc = calculator(cohort, result, exercise=3, response=response)
        kwargs = dict(
            context=calc.ctx,
            track_row=calc.row,
            scenario=calc.scenario,
            lookups=calc.lookups,
            pia_cache={},
            assumed_birth_month=7,
        )
        old, counts = fra.scenario_benefits(result, **kwargs)
        new, new_counts = scenario_benefits(result, **kwargs)
        assert old == new and counts == new_counts


def test_level_policy_floor_and_death_argument_isolation(monkeypatch):
    """D retains eligibility/policy exclusions and never passes death with DI."""
    cohort, result = build(
        [
            dict(id=1, awards=(2017,), death=2030),
            dict(id=2, birth=1970, death=2030),
            dict(id=3),
        ]
    )
    calc = calculator(cohort, result, mechanism="D")
    assert calc._level(1, "di", 1978, None)[0] is None
    assert calc._level(1, "di", 2017, LevelPolicy.EXCLUDE)[0] is None
    calls = []
    original = statutory.aime

    def capture(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(statutory, "aime", capture)
    calc.deceased_record(1)
    calc.deceased_record(2)
    assert calls == [{"disability_year": 2017}]


def test_pia_cache_binds_every_relevant_parameter_input():
    """Shared caches bind AWI, wage bases, factors and evaluated bend points."""
    cohort, result = build(
        [dict(id=1, awards=(2017,))], careers={1: {1987: 252000}}
    )
    original = parameters(pia_factors=(0.9, 0.32, 0.15))
    changed_index = {**original.nawi, 2015: 150.0}
    changed_history_index = {**original.nawi, 1987: 50.0}
    changed_bends = {**original.nawi, 1977: 50.0}
    variants = [
        original,
        dataclasses.replace(original, nawi=changed_index),
        dataclasses.replace(original, nawi=changed_history_index),
        dataclasses.replace(original, nawi=changed_bends),
        dataclasses.replace(original, wage_base={1951: 100000}),
        dataclasses.replace(original, pia_factors=(1.0, 0.5, 0.2)),
    ]
    cache = {}
    for mechanism in ("D", "L", "DS", "S"):
        for params in variants:
            shared = calculator(
                cohort, result, mechanism=mechanism, params=params, cache=cache
            )
            fresh = calculator(
                cohort, result, mechanism=mechanism, params=params
            )
            assert shared.worker_record(1, shared.lookups.final.loc[1]) == (
                fresh.worker_record(1, fresh.lookups.final.loc[1])
            )
    assert len(cache) == 12


@settings(deadline=None, max_examples=25)
@given(st.integers(0, 1000000), st.integers(0, 2000000), st.integers(0, 24))
def test_c0_individual_amounts_never_rise_and_worker_rows_match(
    own_earnings, worker_earnings, increase
):
    """C0 nonincrease, worker-only S identity, and DS D-level/S-time composition."""
    cohort, result = build(
        [
            dict(
                id=1,
                awards=(2017,),
                conversion=2027,
                claim=2027,
                marital="married",
                spouse=2,
            ),
            dict(id=2, claim=2027),
        ],
        careers={1: {1987: own_earnings}, 2: {1987: worker_earnings}},
    )
    base = parameters()
    reform = dataclasses.replace(
        base, fra_months_by_birth_year=[(1900, 804 + increase)]
    )
    outputs = {}
    for mechanism in ("L", "D", "S", "DS"):
        pairs = []
        for params in (base, reform):
            calc = calculator(
                cohort,
                result,
                mechanism=mechanism,
                exercise=3,
                params=params,
                baseline_params=base,
            )
            components, _ = calc.projected_person(1, calc.lookups.final.loc[1])
            pairs.append(components)
            assert all(value[0] >= 0 for value in components.values())
            assert not (
                "retired_worker" in components
                and "disabled_worker" in components
            )
        outputs[mechanism] = pairs
        assert sum(v[0] for v in pairs[1].values()) <= sum(
            v[0] for v in pairs[0].values()
        )
    for scenario in (0, 1):

        def worker_only(data):
            return sum(
                value[0]
                for name, value in data.items()
                if name in ("retired_worker", "disabled_worker")
            )

        assert worker_only(outputs["S"][scenario]) == worker_only(
            outputs["L"][scenario]
        )
        assert worker_only(outputs["DS"][scenario]) == worker_only(
            outputs["D"][scenario]
        )
        own = worker_only(outputs["D"][scenario])
        expected = (
            math.floor(
                max(0, worker_earnings // 420 / 2 - own)
                * (
                    1
                    - ss.spousal_early_reduction(
                        increase if scenario else 0, base
                    )
                )
                * 10
                + 1e-9
            )
            / 10
        )
        assert outputs["DS"][scenario].get("spouse", (0, 0))[0] == expected


@pytest.mark.parametrize("row_id", [f"F{i}" for i in range(8)])
def test_l_replays_every_fra_row_and_union_pair(row_id):
    """Every frozen F row's L scenarios and paired union inputs replay v1."""
    from populace_dynamics.fra68_track.config import registered_rows
    from populace_dynamics.fra68_track.reform import (
        SCHEDULES,
        reform_parameters,
    )

    cohort, result = build(
        [
            dict(
                id=1,
                awards=(2017,),
                conversion=2027,
                claim=2027,
                marital="married",
                spouse=2,
            ),
            dict(id=2, claim=2027),
            dict(
                id=3,
                birth=1965,
                claim=2027,
                marital="widowed",
                late_spouse=4,
                widowhood=2030,
            ),
            dict(id=4, claim=2027, death=2030),
            dict(id=5, birth=1980),
        ],
        careers={
            1: {1987: 252000},
            2: {1987: 840000},
            3: {1987: 100000},
            4: {1987: 672000},
        },
    )
    params = parameters(fra_months_by_birth_year=[(1900, 780), (1960, 804)])
    row = registered_rows()[row_id]
    reform = reform_parameters(params, SCHEDULES[row.schedule_id])
    calc = calculator(cohort, result, exercise=3, params=params)
    context = calc.ctx
    outputs = []
    for scenario_params, response in (
        (params, "c0_fixed_claim_ages"),
        (reform, row.claiming_response),
    ):
        scenario = fra.Scenario(
            row_id,
            scenario_params,
            params,
            survivor_retirement_age=row.survivor_retirement_age,
            claiming_response=response,
        )
        kwargs = dict(
            context=dataclasses.replace(context, params=scenario_params),
            track_row=calc.row,
            scenario=scenario,
            lookups=calc.lookups,
            pia_cache={},
            assumed_birth_month=7,
        )
        old = fra.scenario_benefits(result, **kwargs)
        new = scenario_benefits(result, **kwargs)
        assert old == new
        outputs.append((old[0], new[0]))
    pairing = dict(
        draw=0,
        context=context,
        lookups=calc.lookups,
        baseline_params=params,
        reform_params=reform,
    )
    assert fra.union_benefit_rows(outputs[0][0], outputs[1][0], **pairing) == (
        fra.union_benefit_rows(outputs[0][1], outputs[1][1], **pairing)
    )
