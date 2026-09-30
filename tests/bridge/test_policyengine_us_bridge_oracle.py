"""The PolicyEngine-US bridge against a live policyengine-us interpreter.

Skipped unless the interpreter exists and imports ``policyengine_us``: the
one named by ``POPULACE_DYNAMICS_PE_US_PYTHON``, else the checkout's
virtual environment at ``~/PolicyEngine/policyengine-us/.venv/bin/python``.
The path is resolved and checked, not just the variable read (another test
module sets policyengine-us variables at import).

Each directional fact below was read in policyengine-us at ``e4363903f3``
before it was asserted (paths under ``policyengine_us/``):

* SSI is the benefit rate less countable income (``variables/gov/ssa/ssi/
  uncapped_ssi.py:13-16``, floored at zero in ``ssi_if_takes_up.py:20-23``);
  ``social_security`` is countable unearned income (``parameters/gov/ssa/
  ssi/income/sources/unearned.yaml:6``) and the $20 general exclusion comes
  off unearned income first (``eligibility/income/_apply_ssi_exclusions.py:
  28-30``).  So SSI cannot rise when Social Security rises, and while SSI
  stays positive it falls dollar for dollar.
* SNAP counts ``ssi`` and ``social_security`` as unearned income
  (``parameters/gov/usda/snap/income/sources/unearned.yaml:6,14``), so
  their constant sum leaves SNAP unchanged, and SNAP is the maximum
  allotment less 30 percent of net income (``snap_normal_allotment.py:
  19-23``; ``snap_expected_contribution.py:17-32``), so more income never
  raises it.
* California's supplement is the payment standard less SSI less countable
  income (``variables/gov/states/ca/cdss/state_supplement/
  ca_state_supplement.py:13-17``), constant while SSI is positive.
* Taxable Social Security follows IRC 86 (``tax_unit_taxable_social_
  security.py:13-80``), nondecreasing in benefits here.

The amounts are ILLUSTRATIVE (the annual benefits of the worker in
``scripts/pe_us_minimum_benefit_sample_households.py``).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from populace_dynamics.bridge import policyengine_us as bridge

_DEFAULT_PE_US_PYTHON = Path(
    "~/PolicyEngine/policyengine-us/.venv/bin/python"
).expanduser()


def _interpreter() -> Path:
    env = os.environ.get(bridge.PE_US_PYTHON_ENV)
    return Path(env).expanduser() if env else _DEFAULT_PE_US_PYTHON


pytestmark = pytest.mark.skipif(
    not _interpreter().is_file(),
    reason=f"no policyengine-us interpreter at {_interpreter()}",
)

YEAR = 2026
BASELINE_SS = 8_916.0
REFORM_SS = 10_968.0
TOLERANCE = 0.05


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


def _household(key: str, state: str, ss: float, pension: float):
    person = bridge.BridgePerson(
        "worker",
        68,
        social_security_retirement=ss,
        taxable_private_pension_income=pension,
        bank_account_assets=1_500.0,
        pre_subsidy_rent=9_600.0,
        medicare_quarters_of_coverage=88,
    )
    return bridge.BridgeHousehold(
        f"{key}_{state}".lower(),
        state,
        (person,),
        (("worker",),),
        (("worker",),),
        (("worker",),),
        has_heating_cooling_expense=True,
    )


CASES = {
    ("A", "FL", "baseline"): ("A", "FL", BASELINE_SS, 0.0),
    ("A", "FL", "reform"): ("A", "FL", REFORM_SS, 0.0),
    ("A", "CA", "baseline"): ("A", "CA", BASELINE_SS, 0.0),
    ("A", "CA", "reform"): ("A", "CA", REFORM_SS, 0.0),
    ("B", "FL", "baseline"): ("B", "FL", BASELINE_SS, 4_800.0),
    ("B", "FL", "reform"): ("B", "FL", REFORM_SS, 4_800.0),
    ("C", "MT", "baseline"): ("C", "MT", BASELINE_SS, 30_000.0),
    ("C", "MT", "reform"): ("C", "MT", REFORM_SS, 30_000.0),
}


def _case_id(key) -> str:
    return "_".join(key)


@pytest.fixture(scope="module")
def result(interpreter):
    cases = [
        bridge.RunCase(
            _case_id(key),
            bridge.to_situation(_household(*spec), YEAR),
            expected_state=spec[1],
            memo=("ssi_countable_income",),
        )
        for key, spec in CASES.items()
    ]
    return bridge.run_policyengine_us(cases, year=YEAR, python=interpreter)


def _pair(result, household, state):
    baseline = result.runs[_case_id((household, state, "baseline"))]
    reform = result.runs[_case_id((household, state, "reform"))]
    return baseline, reform


def _decompose(result, household, state):
    baseline, reform = _pair(result, household, state)
    return bridge.decompose(
        baseline.tree,
        baseline.values,
        reform.values,
        reform_tree=reform.tree,
    )


def test__live_tree__then_net_income_definition_is_the_one_read(result):
    for run in result.runs.values():
        assert run.tree.children[bridge.ROOT_VARIABLE] == (
            bridge.NET_INCOME_DEFINITION
        )
    assert result.policyengine_us_version


@pytest.mark.parametrize("state", ["FL", "CA"])
def test__household_a__then_ssi_absorbs_the_benefit_increase(result, state):
    baseline, reform = _pair(result, "A", state)
    ss_change = reform.values["social_security"] - (
        baseline.values["social_security"]
    )
    assert ss_change == pytest.approx(REFORM_SS - BASELINE_SS)
    assert reform.values["ssi"] <= baseline.values["ssi"]
    # SSI stays positive in both runs, so it falls dollar for dollar.
    assert baseline.values["ssi"] > 0 and reform.values["ssi"] > 0
    assert reform.values["ssi"] - baseline.values["ssi"] == pytest.approx(
        -ss_change, abs=TOLERANCE
    )
    assert reform.values["snap"] == pytest.approx(
        baseline.values["snap"], abs=TOLERANCE
    )
    result_ = _decompose(result, "A", state)
    assert abs(result_.net_change_cents) <= round(100 * TOLERANCE)


def test__household_a_in_california__then_the_supplement_is_unchanged(
    result,
):
    baseline, reform = _pair(result, "A", "CA")
    assert baseline.values["ca_state_supplement"] > 0
    assert reform.values["ca_state_supplement"] == pytest.approx(
        baseline.values["ca_state_supplement"], abs=TOLERANCE
    )


@pytest.mark.parametrize(
    ("household", "state"),
    [("A", "FL"), ("A", "CA"), ("B", "FL"), ("C", "MT")],
)
def test__live_runs__then_components_sum_exactly_to_net_change(
    result, household, state
):
    decomposition = _decompose(result, household, state)
    assert (
        sum(c.change_cents for c in decomposition.components)
        == decomposition.net_change_cents
    )
    assert abs(decomposition.reported_gap_cents) <= 1
    assert decomposition.max_aggregate_gap < TOLERANCE


def test__household_b__then_snap_falls_and_ssi_stays_zero(result):
    baseline, reform = _pair(result, "B", "FL")
    assert baseline.values["ssi"] == 0 and reform.values["ssi"] == 0
    assert reform.values["snap"] <= baseline.values["snap"]
    assert reform.values["snap"] < baseline.values["snap"]


def test__household_c__then_taxes_do_not_fall(result):
    baseline, reform = _pair(result, "C", "MT")
    categories = _decompose(result, "C", "MT").by_category()
    # Taxes enter net income negatively: a nonpositive change means the
    # liability did not fall.
    assert categories["federal_income_tax"]["change"] <= 0
    assert categories["state_income_tax"]["change"] <= 0
    assert reform.values["income_tax_before_refundable_credits"] >= (
        baseline.values["income_tax_before_refundable_credits"]
    )


def test__batched_cases__then_values_equal_a_single_case_run(
    interpreter, result
):
    key = ("A", "FL", "baseline")
    alone = bridge.run_policyengine_us(
        [
            bridge.RunCase(
                "alone",
                bridge.to_situation(_household(*CASES[key]), YEAR),
                expected_state="FL",
            )
        ],
        year=YEAR,
        python=interpreter,
    ).runs["alone"]
    batched = result.runs[_case_id(key)]
    assert alone.tree == batched.tree
    assert alone.values == batched.values


def test__state_fips_table__then_every_code_resolves_to_its_state(
    interpreter,
):
    cases = [
        bridge.RunCase(
            state,
            bridge.to_situation(_household("fips", state, 0.0, 0.0), YEAR),
            expected_state=state,
        )
        for state in sorted(bridge.STATE_FIPS)
    ]
    # A small root keeps the run cheap: only the state code is under test.
    out = bridge.run_policyengine_us(
        cases,
        year=YEAR,
        python=interpreter,
        root="household_market_income",
        expand=("household_market_income",),
    )
    assert {run.state_code for run in out.runs.values()} == set(
        bridge.STATE_FIPS
    )
    for state, run in out.runs.items():
        assert run.state_code == state
