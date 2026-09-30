"""The population path against a live policyengine-us interpreter.

Skipped unless the interpreter exists and imports ``policyengine_us``: the
one named by ``POPULACE_DYNAMICS_PE_US_PYTHON``, else
:data:`bridge.DEFAULT_PE_US_PYTHON` (policyengine-us 2.18.0 from PyPI).
The runner refuses any other release (the pinned RECORD digest).

**The differential.**  The merged bridge ran three ILLUSTRATIVE households
(not survey data) in three states, one household per simulation, and
committed every situation and result to
``docs/analysis/pe_us_bridge_20260930/``.  Here the nine households are
read back from those situations and run as one population: one
``Microsimulation`` per scenario (baseline, reform) and variant (health
coverage outside and inside net income).  Every household's decomposition
must equal the committed one in integer cents: every leaf, category and
net figure, and policyengine-us's own float32 net income.  So must the
Medicaid and Medicare Savings Program memo values.

**Multi-person households.**  The committed households each hold one
person, so a second differential takes INVENTED multi-person households
from the invented population (couples filing jointly, other members filing
alone, in states chosen for their mechanisms) and runs each through the
bridge alone, one ``Simulation`` per household, and all of them through
the population path, one ``Microsimulation`` per scenario.  Every
household's decomposition and memo values must agree exactly.

**Reproduction and scale.**  The committed outputs of
``scripts/pe_us_population_invented.py`` are rebuilt live at 300 family
units: every result must equal the committed one, and the run must stay
within the script's stated bounds.

**Population-level formulas.**  policyengine-us 2.18.0 values Medicaid at
cost as the state's spending times the person's cost index over a
denominator (``variables/gov/hhs/medicaid/costs/
medicaid_cost_if_enrolled.py:11-22``).  Over a dataset the denominator is
the weighted sum of the index over every enrollee of the state in the
simulation (``medicaid_slcsp_state_denominator.py:21-26``); for one
household it is the state's enrollment times the state-average index
(``:28-33``), itself a weighted average over the simulation's people in
the state (``medicaid_slcsp_state_average_cost_index.py:14-29``).  So
without care a household's Medicaid value in a population depends on the
other households.  The population path pins both to the one-household
values (``medicaid_valuation="household"``, the default), which the
differential shows reproduces the bridge; the native dataset formulas
instead allocate each state's whole spending across the simulated
enrollees, which the last test shows.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from populace_dynamics.bridge import invented_population as invented
from populace_dynamics.bridge import policyengine_us as bridge
from populace_dynamics.bridge import population as pop
from populace_dynamics.min_benefit_track_m import invented as track_m_invented

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "docs" / "analysis" / "pe_us_bridge_20260930"
STEM = "pe_us_minimum_benefit_sample_households"
POPULATION = ROOT / "docs" / "analysis" / "pe_us_population_invented_20260930"
sys.path.insert(0, str(ROOT / "scripts"))

import pe_us_minimum_benefit_sample_households as sample  # noqa: E402
import pe_us_population_invented as population_script  # noqa: E402

YEAR = 2026
SCENARIOS = ("baseline", "reform")
MEMO = ("medicaid_cost", "msp_cost", "taxable_social_security")


def _interpreter() -> Path:
    env = os.environ.get(bridge.PE_US_PYTHON_ENV)
    return (
        Path(env).expanduser()
        if env
        else bridge.DEFAULT_PE_US_PYTHON.expanduser()
    )


pytestmark = pytest.mark.skipif(
    not _interpreter().is_file(),
    reason=f"no policyengine-us interpreter at {_interpreter()}",
)


@pytest.fixture(scope="module")
def interpreter() -> Path:
    path = _interpreter()
    probe = subprocess.run(
        [str(path), "-c", "import policyengine_us"],
        capture_output=True,
        timeout=300,
    )
    if probe.returncode != 0:
        pytest.skip(f"{path} cannot import policyengine_us")
    return path


@pytest.fixture(scope="module")
def committed():
    return json.loads((ANALYSIS / f"{STEM}.json").read_text())


@pytest.fixture(scope="module")
def parameter_root(interpreter) -> Path:
    installation, _ = sample.pinned_release(str(interpreter))
    return Path(installation.location)


@pytest.fixture(scope="module")
def overrides(parameter_root, committed):
    """The population-wide overrides: California's 2026 standard only.

    The bridge applied it to the California cases; one population
    simulation holds every state, so it applies to all, which is safe
    only because no other state reads a ``gov.states.ca.`` parameter
    (``population_script.parameter_overrides`` refuses any other).
    """

    overrides = population_script.parameter_overrides(
        sample.parameter_updates(parameter_root)
    )
    for row in committed["results"]:
        expected = row["parameter_overrides"]["default"]
        if row["state"] == "CA":
            assert expected == overrides
        else:
            assert expected == {}
    return overrides


@pytest.fixture(scope="module")
def frames(committed):
    """The committed situations as one population per scenario."""

    out = {}
    for scenario in SCENARIOS:
        households = [
            pop.household_from_situation(row["situations"][scenario], YEAR)
            for row in committed["results"]
        ]
        out[scenario] = pop.PopulationFrame.from_households(households)
    assert out["baseline"].same_structure(out["reform"])
    return out


@pytest.fixture(scope="module")
def run(interpreter, frames, overrides):
    return pop.run_population(
        frames,
        year=YEAR,
        variants={
            "default": overrides,
            "with_health": {**overrides, **sample.HEALTH_OVERRIDE},
        },
        household_memo=MEMO,
        python=interpreter,
        expected_package_record_digest=sample.PE_US_RELEASE[
            "package_record_digest"
        ],
    )


def _decomposition(run, variant):
    return pop.decompose_population(
        run.trees[variant],
        run.values[variant]["baseline"],
        run.values[variant]["reform"],
        reform_tree=run.trees[variant],
    )


def test__nine_households_in_one_simulation__then_each_matches_the_bridge(
    run, committed
):
    """Every leaf, category and net figure equals the committed result."""

    decomposition = _decomposition(run, "default")
    assert decomposition.n_households == len(committed["results"]) == 9
    for h, row in enumerate(committed["results"]):
        got = decomposition.household(h).as_dict()
        expected = row["decomposition"]
        for key in (
            "net_change",
            "baseline_net_income",
            "reform_net_income",
            "reported_baseline_net_income",
            "reported_reform_net_income",
            "reported_gap",
            "categories",
            "components",
        ):
            assert got[key] == expected[key], (row["household"], key)


def test__with_health_coverage__then_each_household_matches_the_bridge(
    run, committed
):
    decomposition = _decomposition(run, "with_health")
    for h, row in enumerate(committed["results"]):
        got = decomposition.household(h).as_dict()
        expected = row["with_health_benefits_in_net_income"]
        for key in (
            "net_change",
            "baseline_net_income",
            "reform_net_income",
            "categories",
        ):
            assert got[key] == expected[key], (row["household"], key)


def test__memo_values__then_each_household_matches_the_bridge(run, committed):
    """Medicaid at cost, the MSP and taxable benefits, exactly (float32)."""

    for scenario in SCENARIOS:
        memo = run.household_memo["default"][scenario]
        for h, row in enumerate(committed["results"]):
            for name in MEMO:
                assert float(memo[name][h]) == row["memo"][scenario][name], (
                    row["household"],
                    row["state"],
                    scenario,
                    name,
                )


def test__the_run__then_it_records_the_release_and_one_simulation_each(
    run, frames
):
    assert run.policyengine_us_version == sample.PE_US_RELEASE["version"]
    assert run.source["published"] is True
    assert run.source["record_check"]["package_record_digest"] == (
        sample.PE_US_RELEASE["package_record_digest"]
    )
    assert run.medicaid_valuation == "household"
    assert set(run.timings) == {"default", "with_health"}
    for variant in run.timings.values():
        assert set(variant) == set(SCENARIOS)
    assert run.peak_rss_bytes > 0
    for variant in run.values.values():
        for values in variant.values():
            for array in values.values():
                assert len(array) == frames["baseline"].n_households


def test__native_medicaid__then_state_spending_is_spread_over_enrollees(
    interpreter, frames, overrides, parameter_root, committed
):
    """Why the population path pins Medicaid (module docstring).

    With policyengine-us's dataset formulas, a state's Medicaid cost sums
    over its simulated enrollees (weight 1 here) to the state's whole
    calibrated spending, so each enrollee's value depends on how many
    others the simulation holds, and differs from the one-household value
    the bridge reports.
    """

    native = pop.run_population(
        {"baseline": frames["baseline"]},
        year=YEAR,
        variants={"with_health": {**overrides, **sample.HEALTH_OVERRIDE}},
        household_memo=("medicaid_cost",),
        medicaid_valuation="native",
        python=interpreter,
        expected_package_record_digest=sample.PE_US_RELEASE[
            "package_record_digest"
        ],
    )
    cost = native.household_memo["with_health"]["baseline"]["medicaid_cost"]
    per_enrollee = sample.medicaid_per_enrollee(parameter_root)
    states = frames["baseline"].state
    for state in sorted(set(states)):
        rows = [
            h
            for h, row in enumerate(committed["results"])
            if states[h] == state and row["memo"]["baseline"]["medicaid_cost"]
        ]
        assert rows, state
        spending = per_enrollee[state]["spending"]
        total = float(np.sum(cost[rows]))
        assert total == pytest.approx(spending, rel=1e-6), state
        for h in rows:
            household = committed["results"][h]["memo"]["baseline"]
            assert abs(cost[h] - household["medicaid_cost"]) > 1_000.0


# ---------------------------------------------------------------------------
# Multi-person INVENTED households: the population path against the bridge
# ---------------------------------------------------------------------------
#: States for the chosen households, each for a mechanism: California's SSI
#: supplement, Minnesota's supplemental aid, Alabama's deduction of federal
#: income tax, Montana's income tax and elderly credit, New York, Florida.
MECHANISM_STATES = ("CA", "MN", "AL", "MT", "NY", "FL")
MULTI_MEMO = ("medicaid_cost", "msp_cost", "ssi", "snap")


def _invented_households():
    """Twelve INVENTED households: every one with an other member, then
    couples and singles, in :data:`MECHANISM_STATES` by turn.  Two lose
    every non-Social Security income and asset (toward SSI and SNAP)."""

    parameters, cola = track_m_invented.invented_parameters()
    rates = {**cola, **{year: 0.025 for year in range(2022, 2026)}}
    cohort = invented.build_invented_cohort(
        seed=7, n_family_units=300, params=parameters.params, cola_rates=cola
    )
    result = invented.evaluate_headline(cohort.inputs, parameters)
    table = invented.person_benefits(
        cohort.inputs,
        result,
        parameters,
        rates,
        persons=cohort.cohort.persons,
    )
    population = invented.build_population(cohort, table, seed=7)
    frame = population.frames["current_law"]
    sizes = np.bincount(frame.units["household"])
    changed = [
        h
        for h in range(frame.n_households)
        if not np.array_equal(
            *(
                population.frames[s].amounts["social_security_retirement"][
                    frame.units["household"] == h
                ]
                for s in invented.SIMULATED_SCENARIOS
            )
        )
    ]
    threes = [h for h in range(len(sizes)) if sizes[h] == 3][:4]
    twos = [h for h in changed if sizes[h] == 2][:4]
    ones = [h for h in changed if sizes[h] == 1][:4]
    chosen = threes + twos + ones
    assert len(chosen) == 12, (len(threes), len(twos), len(ones))
    out = {}
    for scenario in invented.SIMULATED_SCENARIOS:
        part = population.frames[scenario].subset(chosen)
        fields = {
            name: getattr(part, name)
            for name in pop.PopulationFrame.__dataclass_fields__
        }
        fields["state"] = tuple(
            MECHANISM_STATES[h % len(MECHANISM_STATES)]
            for h in range(part.n_households)
        )
        poor = np.isin(part.units["household"], (2, 9))
        amounts = dict(part.amounts)
        for name in (
            "employment_income",
            "taxable_private_pension_income",
            "interest_income",
            "bank_account_assets",
        ):
            amounts[name] = np.where(poor, 0.0, amounts[name])
        fields["amounts"] = amounts
        out[scenario] = pop.PopulationFrame(**fields)
    return out


@pytest.fixture(scope="module")
def invented_frames():
    return _invented_households()


@pytest.fixture(scope="module")
def invented_runs(interpreter, invented_frames, overrides):
    variants = {
        "default": overrides,
        "with_health": {**overrides, **sample.HEALTH_OVERRIDE},
    }
    together = pop.run_population(
        invented_frames,
        year=YEAR,
        variants=variants,
        household_memo=MULTI_MEMO,
        python=interpreter,
        expected_package_record_digest=sample.PE_US_RELEASE[
            "package_record_digest"
        ],
    )
    cases = []
    for scenario, frame in invented_frames.items():
        for h, household in enumerate(frame.to_households()):
            for variant in variants:
                state_overrides = dict(
                    overrides if household.state == "CA" else {}
                )
                if variant == "with_health":
                    state_overrides.update(sample.HEALTH_OVERRIDE)
                cases.append(
                    bridge.RunCase(
                        case_id=f"{variant}/{scenario}/{h}",
                        situation=bridge.to_situation(household, YEAR),
                        expected_state=household.state,
                        memo=MULTI_MEMO,
                        parameter_overrides=state_overrides,
                    )
                )
    alone = bridge.run_policyengine_us(
        cases,
        year=YEAR,
        python=interpreter,
        expected_package_record_digest=sample.PE_US_RELEASE[
            "package_record_digest"
        ],
    )
    return together, alone


@pytest.mark.parametrize("variant", ("default", "with_health"))
def test__invented_multi_person_households__then_each_matches_it_alone(
    invented_runs, invented_frames, variant
):
    together, alone = invented_runs
    base, reform = invented.SIMULATED_SCENARIOS
    decomposition = pop.decompose_population(
        together.trees[variant],
        together.values[variant][base],
        together.values[variant][reform],
        reform_tree=together.trees[variant],
    )
    frame = invented_frames[base]
    assert frame.n_people > frame.n_households  # couples and others
    moved = 0
    for h in range(frame.n_households):
        one = alone.runs[f"{variant}/{base}/{h}"]
        other = alone.runs[f"{variant}/{reform}/{h}"]
        assert one.tree == together.trees[variant]
        expected = bridge.decompose(one.tree, one.values, other.values)
        got = decomposition.household(h).as_dict()
        want = expected.as_dict()
        got.pop("max_aggregate_gap")
        want.pop("max_aggregate_gap")
        assert got == want, (h, frame.state[h])
        for scenario, run in ((base, one), (reform, other)):
            memo = together.household_memo[variant][scenario]
            for name in MULTI_MEMO:
                assert float(memo[name][h]) == run.memo[name], (
                    h,
                    scenario,
                    name,
                )
        moved += int(expected.net_change_cents != 0)
    assert moved  # the reform moves some households


# ---------------------------------------------------------------------------
# Reproduction and scale: the committed outputs, rebuilt live at 300 units
# ---------------------------------------------------------------------------
REPRODUCED = (
    "label",
    "track_m",
    "households",
    "results",
    "changed_leaves",
    "health_split",
    "checks",
)


@pytest.fixture(scope="module")
def committed_population():
    return json.loads(
        (POPULATION / f"{population_script.OUTPUT_STEM}.json").read_text()
    )


def test__the_committed_300_unit_run__then_a_live_rebuild_reproduces_it(
    interpreter, committed_population
):
    document, _ = population_script.build(
        (300,),
        seed=population_script.DEFAULT_SEED,
        python=str(interpreter),
    )
    live = document["sizes"]["300"]
    committed = committed_population["sizes"]["300"]
    for key in REPRODUCED:
        assert live[key] == committed[key], key
    scale = live["scale"]
    assert scale["within_bounds"] is True
    bounds = population_script.SCALE_BOUNDS[300]
    assert scale["pe_wall_seconds"] <= bounds["pe_wall_seconds"]
    assert scale["peak_rss_bytes"] <= bounds["peak_rss_bytes"]
    assert set(scale["pe_simulations"]) == set(population_script.VARIANTS)
