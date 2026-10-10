"""INVENTED DATA - NOT A COMPARISON: nontrivial §12.6/12.9 composition."""

import math
from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.cola_track_a.config import REGISTERED_ROWS
from populace_dynamics.estimates.parameters import COLASeries
from populace_dynamics.ss.benefits import spousal_benefit
from populace_dynamics.track_a_v2.benefits import (
    collect_reference_benefit_rows,
    scenario_benefits,
)
from populace_dynamics.track_a_v2.estimands import (
    pair_scenarios,
    tabulate_rows,
)
from populace_dynamics.track_a_v2.matrix import get_row
from tests.track_a_v2._invented import build, calculator, parameters


def mixed_fixture(own=252000, worker=840000, award=2022):
    return build(
        [
            dict(
                id=1,
                birth=1965,
                claim=2008,
                opening_receipt=True,
                awards=(award,),
                marital="married",
                spouse=2,
            ),
            dict(id=2, birth=1960, claim=2027),
            dict(id=3, birth=1963, claim=2025),
            dict(id=4, birth=1964, claim=2026),
        ],
        careers={
            1: {1987: own},
            2: {1987: worker},
            3: {1987: 210000},
            4: {1987: 210000},
        },
    )


def amounts(calc):
    return calc.projected_person(1, calc.lookups.final.loc[1])[0]


@pytest.mark.parametrize("exercise", (1, 3))
@settings(max_examples=12, deadline=None)
@given(own=st.integers(420, 300000), worker=st.integers(420, 1000000))
def test_ds_combines_d_levels_with_fixed_s_timing(exercise, own, worker):
    """DS uses D own PIA and S's fixed age-62 timing, with one own payment."""
    cohort, result = mixed_fixture(own, worker)
    values = {
        mechanism: amounts(
            calculator(cohort, result, mechanism=mechanism, exercise=exercise)
        )
        for mechanism in ("L", "D", "S", "DS")
    }
    own_d = values["D"]["disabled_worker"][0]
    assert values["DS"]["disabled_worker"][0] == own_d
    assert values["S"]["disabled_worker"] == values["L"]["disabled_worker"]
    expected = (
        math.floor(
            10
            * spousal_benefit(
                own_d, math.floor(worker / 420), 60, parameters()
            )
            + 1e-9
        )
        / 10
    )
    assert values["DS"].get("spouse", (0, 0))[0] == expected
    for components in values.values():
        assert not (
            "retired_worker" in components and "disabled_worker" in components
        )
        assert all(min(pair) >= 0 for pair in components.values())
        assert all(base == reform for base, reform in components.values())


def test_nontrivial_d_and_s_effects_compose_in_one_recipient():
    """Both mechanisms change this fixture; DS composition is nonvacuous."""
    cohort, result = mixed_fixture()
    values = {
        mechanism: amounts(calculator(cohort, result, mechanism=mechanism))
        for mechanism in ("L", "D", "S", "DS")
    }
    assert values["L"]["disabled_worker"] == (600, 600)
    assert values["D"]["disabled_worker"] == (700, 700)
    assert values["S"]["spouse"] == (260, 260)
    assert values["DS"]["spouse"] == (195, 195)


@pytest.mark.parametrize("row_id", ("R5", "F6"))
def test_workers_only_full_tabulations_are_identical_under_s(row_id):
    """S/L and DS/D workers-only cells, ratios, SDs and floors are identical."""
    cohort, result = mixed_fixture()
    outputs = {}
    for mechanism in ("L", "D", "S", "DS"):
        if row_id == "R5":
            calc = calculator(
                cohort,
                result,
                mechanism=mechanism,
                row="R5",
                annual_reduction=0.01,
            )
            rows, _ = collect_reference_benefit_rows(
                result,
                draw=0,
                row=REGISTERED_ROWS["R5"],
                context=replace(
                    calc.ctx,
                    baseline=COLASeries(
                        {year: 0.02 for year in range(1970, 2051)},
                        {"invented": True},
                    ),
                ),
                mechanism=mechanism,
            )
        else:
            people = []
            for fra in (804, 816):
                calc = calculator(
                    cohort,
                    result,
                    mechanism=mechanism,
                    exercise=3,
                    params=parameters(fra_months_by_birth_year=[(1900, fra)]),
                    baseline_params=parameters(),
                )
                scenario, _ = scenario_benefits(
                    result,
                    context=calc.ctx,
                    track_row=calc.row,
                    scenario=calc.scenario,
                    lookups=calc.lookups,
                    pia_cache={},
                    mechanism=mechanism,
                )
                people.append(
                    {
                        pid: {
                            "weight": 1,
                            "birth_year": int(
                                cohort.persons_by_id.at[pid, "birth_year"]
                            ),
                            "family_unit_id": pid,
                            "components": scenario[pid].components,
                        }
                        for pid in scenario
                    }
                )
            rows = pair_scenarios(*people, draw=0)
        outputs[mechanism] = tabulate_rows(
            rows, get_row(mechanism, row_id), draw_indices=(0,)
        )["groups"]
    assert outputs["S"] == outputs["L"]
    assert outputs["DS"] == outputs["D"]


@pytest.mark.parametrize("exercise", (1, 3))
def test_genuinely_draw_interleaved_shared_cache_order(exercise):
    """Shared caches isolate mechanisms and award years in interleaved draws."""
    paths = [mixed_fixture(award=year) for year in (2015, 2022)]
    keys = [(m, draw) for m in ("L", "D", "S", "DS") for draw in (0, 1)]
    expected = {}
    for mechanism, draw in keys:
        cohort, result = paths[draw]
        expected[mechanism, draw] = amounts(
            calculator(cohort, result, mechanism=mechanism, exercise=exercise)
        )
    shared = {}
    interleaved = [
        ("DS", 1),
        ("S", 0),
        ("D", 1),
        ("L", 0),
        ("D", 0),
        ("L", 1),
        ("DS", 0),
        ("S", 1),
    ]
    for mechanism, draw in interleaved + list(reversed(interleaved)):
        cohort, result = paths[draw]
        actual = amounts(
            calculator(
                cohort,
                result,
                mechanism=mechanism,
                exercise=exercise,
                cache=shared,
            )
        )
        assert actual == expected[mechanism, draw]
