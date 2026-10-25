"""Native entity IDs and enums against an explicitly configured interpreter.

All situations are invented. The oracle is opt-in through
``POPULACE_DYNAMICS_PE_US_PYTHON``; no default interpreter is used here.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

from populace_dynamics.bridge import policyengine_us as bridge


@pytest.fixture(scope="module")
def named_result():
    configured = os.environ.get("POPULACE_DYNAMICS_PE_US_PYTHON")
    if not configured or not Path(configured).expanduser().is_file():
        pytest.skip("no explicitly configured policyengine-us interpreter")
    household = bridge.BridgeHousehold(
        "native",
        "TX",
        (bridge.BridgePerson("older", 70), bridge.BridgePerson("younger", 40)),
        (("older",), ("younger",)),
        (("older", "younger"),),
        (("older",), ("younger",)),
    )
    situation = bridge.to_situation(household, 2026)
    first = (101.25, -20.5)
    second = (11.0, 12.0)
    for entry, value in zip(
        situation["tax_units"].values(), first, strict=True
    ):
        entry["income_tax"] = {"2026": value}
        entry["filing_status"] = {"2026": "SINGLE"}
    other = copy.deepcopy(situation)
    for entry, value in zip(other["tax_units"].values(), second, strict=True):
        entry["income_tax"] = {"2026": value}
    result = bridge.run_policyengine_us_variables(
        [
            bridge.RunCase("first", situation, expected_state="TX"),
            bridge.RunCase("second", other, expected_state="TX"),
        ],
        year=2026,
        variables=("income_tax", "filing_status", "age"),
        python=configured,
        required_version="2.61.0",
    )
    return result, situation, first, second


def test_native_outputs_preserve_tax_unit_order_and_enum_names(named_result):
    result, situation, first, _ = named_result
    run = result.runs["first"]
    assert run.values["income_tax"] == first
    assert run.values["filing_status"] == ("SINGLE", "SINGLE")
    assert run.values["age"] == (70.0, 40.0)
    assert run.entity_ids["tax_units"] == tuple(situation["tax_units"])
    assert run.entity_ids["people"] == ("older", "younger")
    assert run.variable_entities == {
        "income_tax": "tax_units",
        "filing_status": "tax_units",
        "age": "people",
    }


def test_cases_have_fresh_simulations_when_system_is_shared(named_result):
    result, _, first, second = named_result
    assert result.runs["first"].values["income_tax"] == first
    assert result.runs["second"].values["income_tax"] == second
    assert result.installation.version == "2.61.0"
    assert result.source["record_check"]["mismatched"] == 0
