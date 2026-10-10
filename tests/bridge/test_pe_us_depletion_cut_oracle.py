"""The depletion-cut analysis against a live policyengine-us interpreter.

Skipped unless the interpreter exists: the one named by
``POPULACE_DYNAMICS_PE_US_PYTHON``, else
:data:`bridge.DEFAULT_PE_US_PYTHON` (policyengine-us 2.18.0 from PyPI).
ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA; 2026 law and prices.

* **Benefits.**  The low earner's baseline benefit, derived live as #496
  derives it, equals #496's committed current-law benefit; the medium
  earner's derivation and the Track B gross-benefit layer agree on the
  couple's worker benefit (a differential check), and the family maximum
  does not bind.
* **A zero cut changes nothing.**  Household A in Florida built with a
  payable share of 1 and run as its own case decomposes, against the
  separately run baseline, to zero changes, with no offset share.
* **Directions read in policyengine-us 2.18.0 before they were asserted**
  (paths under ``policyengine_us/``): SSI is the benefit rate less
  countable income (``variables/gov/ssa/ssi/uncapped_ssi.py:13-16``), and
  Social Security is countable unearned income
  (``parameters/gov/ssa/ssi/income/sources/unearned.yaml:6``), so while
  SSI stays positive it rises dollar for dollar with a cut (household A in
  Florida); taxable Social Security follows IRC 86
  (``tax_unit_taxable_social_security.py:13-85``), so a cut lowers it and
  federal income tax does not rise (household D in Montana).
"""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from populace_dynamics.bridge import depletion_cut as dc
from populace_dynamics.bridge import policyengine_us as bridge

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import pe_us_depletion_cut_sample_households as script  # noqa: E402


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

YEAR = script.PAYMENT_YEAR
SHARES = {
    "baseline": Decimal(1),
    "oasi": Decimal("0.78"),
    "oasdi": Decimal("0.83"),
}


@pytest.fixture(scope="module")
def parameter_root():
    installation = bridge.inspect_installation(None)
    assert installation.version == "2.18.0"
    return Path(installation.location)


@pytest.fixture(scope="module")
def benefits(parameter_root):
    rates, _ = script.minimum.cola_rates(YEAR, parameter_root)
    out = {"low_earner": script.low_earner_benefit(parameter_root)}
    out["medium_earner"] = script.medium_earner_benefit(parameter_root, rates)
    out["couple"] = script.couple_benefits(
        parameter_root, rates, out["medium_earner"]
    )
    return out


def test__live__then_the_low_earner_is_496s_committed_benefit(benefits):
    committed = json.loads(
        (
            ROOT
            / "docs"
            / "analysis"
            / "pe_us_bridge_20260930"
            / "pe_us_minimum_benefit_sample_households.json"
        ).read_text()
    )
    assert benefits["low_earner"]["current_law"] == (
        committed["worker"]["current_law"]
    )
    assert benefits["low_earner"]["monthly_benefit"] == 743


def test__live__then_track_b_agrees_with_the_medium_earner(benefits):
    medium = benefits["medium_earner"]
    couple = benefits["couple"]
    assert medium["pia_record"]["pia"] == 1_735.8
    assert medium["monthly_benefit"] == couple["worker_monthly"] == 2_351
    assert couple["spouse_monthly"] == 1_175
    assert couple["result"]["family_maximum_binding"] is False


def _case(spec_key, state, scenario, benefits):
    spec = next(s for s in script.HOUSEHOLDS if s["key"] == spec_key)
    if scenario == "zero":
        # A payable share of 1, cut and rounded like the reforms.
        cuts = dc.cut_household(
            script.scheduled_benefits(spec, benefits), Decimal(1)
        )
    else:
        cuts = script.household_cuts(spec, benefits, SHARES)[scenario]
    annual = {p: float(c.annual_payable) for p, c in cuts.items()}
    built = script.build_household(spec, state, annual, benefits)
    return bridge.RunCase(
        case_id=f"{spec_key}_{state}_{scenario}",
        situation=bridge.to_situation(built, YEAR),
        expected_state=state,
    )


@pytest.fixture(scope="module")
def runs(benefits):
    cases = [
        _case("A", "FL", "baseline", benefits),
        _case("A", "FL", "zero", benefits),
        _case("A", "FL", "oasi", benefits),
        _case("D", "MT", "baseline", benefits),
        _case("D", "MT", "oasi", benefits),
    ]
    return bridge.run_policyengine_us(
        cases,
        year=YEAR,
        expected_package_record_digest=(
            script.minimum.PE_US_RELEASE["package_record_digest"]
        ),
    ).runs


def _decompose(runs, before, after):
    return bridge.decompose(
        runs[before].tree,
        runs[before].values,
        runs[after].values,
        reform_tree=runs[after].tree,
    )


def test__live__then_a_zero_cut_changes_nothing(runs):
    d = _decompose(runs, "A_FL_baseline", "A_FL_zero")
    levels = dc.by_level(d.components)
    assert d.net_change_cents == 0
    assert all(level["change"] == 0 for level in levels.values())
    assert dc.offset_share(0, levels["social_security"]["change"]) is None


def test__live__then_ssi_offsets_the_cut_dollar_for_dollar(runs):
    d = _decompose(runs, "A_FL_baseline", "A_FL_oasi")
    categories = d.by_category()
    assert categories["social_security"]["change"] == -196_800
    assert categories["ssi"]["change"] == 196_800
    assert d.net_change_cents == 0
    levels = dc.by_level(d.components)
    assert dc.offset_shares_by_level(levels)["federal"] == 1


def test__live__then_taxes_offset_part_of_the_medium_earners_cut(runs):
    d = _decompose(runs, "D_MT_baseline", "D_MT_oasi")
    categories = d.by_category()
    assert categories["social_security"]["change"] == -621_600
    assert categories["federal_income_tax"]["change"] > 0
    assert categories["state_income_tax"]["change"] >= 0
    levels = dc.by_level(d.components)
    share = dc.offset_share(
        d.net_change_cents, levels["social_security"]["change"]
    )
    assert 0 < share < 1
    shares = dc.offset_shares_by_level(levels)
    assert shares["federal"] + shares["state"] + shares["joint"] == share
    assert dc.changed_outside_groups(d.components) == []
