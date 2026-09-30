"""The PolicyEngine-US bridge against a live policyengine-us interpreter.

Skipped unless the interpreter exists and imports ``policyengine_us``: the
one named by ``POPULACE_DYNAMICS_PE_US_PYTHON``, else
:data:`bridge.DEFAULT_PE_US_PYTHON`, a virtual environment holding
policyengine-us 2.18.0 from PyPI.  The path is resolved and checked, not
just the variable read (another test module sets policyengine-us variables
at import).  The bridge refuses an interpreter whose ``policyengine-us`` is
not a published source, so these tests fail loudly on an unpushed checkout.

Each directional fact below was read in policyengine-us 2.18.0 before it
was asserted (paths under ``policyengine_us/``):

* SSI is the benefit rate less countable income (``variables/gov/ssa/ssi/
  uncapped_ssi.py:13-16``, floored at zero in ``ssi_if_takes_up.py:20-23``);
  ``social_security`` is countable unearned income (``parameters/gov/ssa/
  ssi/income/sources/unearned.yaml:6``) and the $20 general exclusion comes
  off unearned income first (``eligibility/income/_apply_ssi_exclusions.py:
  28-30``).  So SSI cannot rise when Social Security rises, and while SSI
  stays positive it falls dollar for dollar.
* SNAP counts ``ssi`` and ``social_security`` as unearned income
  (``parameters/gov/usda/snap/income/sources/unearned.yaml:6,63``), so
  their constant sum leaves SNAP unchanged, and SNAP is the maximum
  allotment less 30 percent of net income (``snap_normal_allotment.py:
  19-23``; ``snap_expected_contribution.py:17-32``), so more income never
  raises it.
* California's supplement is the payment standard less SSI less countable
  income (``variables/gov/states/ca/cdss/state_supplement/
  ca_state_supplement.py:13-17``), constant while SSI is positive.  Its
  single aged or disabled payment standard has no entry after 2025-01-01
  (``parameters/gov/states/ca/cdss/state_supplement/payment_standard/
  aged_or_disabled/amount/single.yaml:12-13``).
* Taxable Social Security follows IRC 86 (``tax_unit_taxable_social_
  security.py:13-85``), nondecreasing in benefits here.
* California's use tax is a step schedule of California AGI in $10,000
  brackets (``variables/gov/states/ca/tax/income/ca_use_tax.py:13-20``;
  ``parameters/gov/states/ca/tax/income/use_tax/main.yaml:19-28``).

The amounts are ILLUSTRATIVE (the annual benefits of the worker in
``scripts/pe_us_minimum_benefit_sample_households.py``).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from populace_dynamics.bridge import policyengine_us as bridge


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

YEAR = 2026
BASELINE_SS = 8_916.0
REFORM_SS = 10_968.0
PENSION_B = 4_800.0
PENSION_C = 31_200.0
TOLERANCE = 0.05
#: California's 2026 payment standard, single aged person living
#: independently: CDSS, "SSI Total Monthly Payment Amounts 2026" (Rev. 1/26,
#: effective 2026-01-01), $1,233.94 a month.  policyengine-us 2.18.0 holds
#: 2025's $1,206.94.
CA_STANDARD = "gov.states.ca.cdss.state_supplement.payment_standard." + (
    "aged_or_disabled.amount.single"
)
CA_2026 = 1_233.94
CA_2025 = 1_206.94


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
    ("B", "FL", "baseline"): ("B", "FL", BASELINE_SS, PENSION_B),
    ("B", "FL", "reform"): ("B", "FL", REFORM_SS, PENSION_B),
    ("C", "MT", "baseline"): ("C", "MT", BASELINE_SS, PENSION_C),
    ("C", "MT", "reform"): ("C", "MT", REFORM_SS, PENSION_C),
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


def test__live_interpreter__then_its_source_is_published_and_intact(
    interpreter, result
):
    """Finding 3: the run records a published policyengine-us source."""

    installation = bridge.inspect_installation(interpreter)
    assert result.installation == installation
    assert result.source["published"] is True
    assert result.source["kind"] in ("index", "path")
    assert result.policyengine_us_version == installation.version
    if installation.source_kind == "index":
        record = bridge.verify_record(installation)
        assert record["files_checked"] > 1_000
        assert record["mismatched"] == [] and record["missing"] == []


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


def test__california_payment_standard_override__then_it_sets_the_supplement(
    interpreter,
):
    """Finding 1: the 2026 override reaches the supplement's formula.

    Household B's SSI countable income is $743 + $400 - $20 = $1,123 a
    month and her SSI is zero, so the supplement is the payment standard
    less $1,123: $110.94 a month under CDSS's $1,233.94, $83.94 under the
    release's held $1,206.94.
    """

    situation = bridge.to_situation(
        _household("B", "CA", BASELINE_SS, PENSION_B), YEAR
    )
    out = bridge.run_policyengine_us(
        [
            bridge.RunCase("held", situation, expected_state="CA"),
            bridge.RunCase(
                "published",
                situation,
                expected_state="CA",
                parameter_overrides={CA_STANDARD: CA_2026},
            ),
        ],
        year=YEAR,
        python=interpreter,
    )
    countable = 743 + 400 - 20
    assert out.runs["held"].values["ca_state_supplement"] == pytest.approx(
        12 * (CA_2025 - countable), abs=TOLERANCE
    )
    assert out.runs["published"].values[
        "ca_state_supplement"
    ] == pytest.approx(12 * (CA_2026 - countable), abs=TOLERANCE)


@pytest.mark.parametrize(
    ("pension", "flagged"),
    [(30_000.0, ["ca_use_tax@2026"]), (PENSION_C, [])],
)
def test__use_tax_at_a_bracket_edge__then_the_float32_guard_flags_it(
    interpreter, pension, flagged
):
    """Finding 2, live: at a $30,000 pension California AGI sits on the
    $30,000 use-tax edge and float32 noise steps the tax by $1; at the
    script's $31,200 nothing changes without a cause."""

    variables = ["state_use_tax", "income_tax_before_refundable_credits"]
    traces = bridge.trace_policyengine_us(
        [
            (
                scenario,
                bridge.to_situation(_household("C", "CA", ss, pension), YEAR),
                variables,
            )
            for scenario, ss in (
                ("baseline", BASELINE_SS),
                ("reform", REFORM_SS),
            )
        ],
        year=YEAR,
        python=interpreter,
    )
    found = bridge.uncaused_changes(
        traces["baseline"],
        traces["reform"],
        [f"{name}@{YEAR}" for name in variables],
    )
    assert [item["variable"] for item in found] == flagged
    # Federal income tax rises with the benefit in both: a caused change.
    federal = f"income_tax_before_refundable_credits@{YEAR}"
    assert traces["reform"][federal].value[0] > (
        traces["baseline"][federal].value[0]
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
