"""Public-interface oracle checks on invented households only.

POPULACE_DYNAMICS_PE_US_PYTHON_SSI0 deliberately contains the static oracle
tier substring without reusing the older bridge environment variable.
"""

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.estimates.adjusted_poverty import (
    AdjustedPovertySpec,
    SsiParameters,
    _ssi_response,
)
from populace_dynamics.income_resources.ssi.contract import CONTRACT_PATH
from populace_dynamics.income_resources.ssi.pinning import load_pin
from populace_dynamics.income_resources.ssi.records import (
    CountedRefusal,
    SSIResult,
)
from populace_dynamics.income_resources.ssi.runner import (
    DEFAULT_PYTHON,
    PYTHON_ENV,
    SSIRunner,
)

from .ssi_invented import invented_case


def invented_runner():
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    return SSIRunner(python, timeout=1800)


def accepted(batch):
    assert all(
        isinstance(outcome, SSIResult) for outcome in batch.outcomes
    ), batch.outcomes
    return batch.outcomes


def test_identical_policy_and_overrides():
    runner = invented_runner()
    base = invented_case("INVENTED_BASE")
    same = replace(base, case_id="INVENTED_IDENTICAL")
    higher = replace(
        base,
        case_id="INVENTED_HIGHER",
        parameter_overrides={
            **base.parameter_overrides,
            "gov.ssa.ssi.amount.individual": 1100,
        },
    )
    first, second, changed = accepted(runner.run_many([base, same, higher]))
    assert first.federal_ssi == second.federal_ssi
    assert first.intermediate == second.intermediate
    assert first.total == pytest.approx(12000)
    assert changed.total == pytest.approx(13200)
    assert runner.accounting.attempted == runner.accounting.accepted == 3


@settings(deadline=None, max_examples=2)
@given(
    unearned=st.integers(500, 5000),
    earned=st.integers(1500, 6000),
    resources=st.integers(0, 2200),
)
def test_federal_invariants(unearned, earned, resources):
    # Batch cases share import/version checks; inputs are annual dollars.
    runner = invented_runner()
    cases = [
        invented_case("INVENTED_U", social_security=unearned),
        invented_case("INVENTED_U1", social_security=unearned + 12),
        invented_case("INVENTED_E", employment_income=earned),
        invented_case("INVENTED_E1", employment_income=earned + 12),
        invented_case("INVENTED_R", bank_account_assets=resources),
        invented_case("INVENTED_R1", bank_account_assets=resources + 1),
        invented_case("INVENTED_COUPLE", couple=True),
    ]
    u, u1, e, e1, r, r1, couple = accepted(runner.run_many(cases))
    for outcome in (u, u1, e, e1, r, r1):
        assert 0 <= outcome.total <= 12000
    assert 0 <= couple.total <= 18000
    assert u.total - u1.total == pytest.approx(12, abs=0.02)
    assert e.total - e1.total == pytest.approx(6, abs=0.02)
    assert r1.total <= r.total
    assert r.total == pytest.approx(12000 if resources <= 2000 else 0)
    assert r1.total == pytest.approx(12000 if resources + 1 <= 2000 else 0)
    assert (
        u1.intermediate["ssi_countable_income"][0]
        >= u.intermediate["ssi_countable_income"][0]
    )
    assert (
        r1.intermediate["ssi_countable_resources"][0]
        >= r.intermediate["ssi_countable_resources"][0]
    )


def test_static_offset_differential():
    runner = invented_runner()
    amounts = (120, 240, 250, 2400, 6000)
    cases = []
    for index, amount in enumerate(amounts):
        cases.extend(
            [
                invented_case(
                    f"INVENTED_BEFORE_{index}", social_security=amount
                ),
                invented_case(
                    f"INVENTED_AFTER_{index}", social_security=amount * 0.87
                ),
            ]
        )
    results = accepted(runner.run_many(cases))
    rows = pd.DataFrame(
        [
            dict(
                income_year=2026,
                head_ssi=results[2 * i].total,
                wife_ssi=0,
                head_ss=amount,
                wife_ss=0,
                ofum_ssi=0,
            )
            for i, amount in enumerate(amounts)
        ]
    )
    parameters = SsiParameters(
        {2026: 1000},
        {2026: 1500},
        20,
        65,
        0.5,
        2000,
        3000,
        {"source": "INVENTED_POLICY"},
    )
    offset, newly_eligible = _ssi_response(
        rows,
        AdjustedPovertySpec(),
        {"fu": np.zeros(len(rows), dtype=bool)},
        parameters,
        np.full(len(rows), 0.13),
    )
    expected = np.array(
        [
            results[2 * i + 1].total - results[2 * i].total
            for i in range(len(amounts))
        ]
    )
    np.testing.assert_allclose(offset, expected, atol=0.02, rtol=0)
    np.testing.assert_array_equal(newly_eligible, 0)


def test_refused_input_and_deeming_are_counted():
    runner = invented_runner()
    case = invented_case()
    missing = dict(case.household.people[0].inputs)
    del missing["social_security"]
    person = replace(case.household.people[0], inputs=missing)
    case = replace(case, household=replace(case.household, people=(person,)))
    with pytest.raises(CountedRefusal, match="INPUT_CONTRACT_GAP"):
        runner.run(case)
    couple = invented_case(couple=True)
    young = replace(
        couple.household.people[1],
        inputs={**couple.household.people[1].inputs, "age": 50},
    )
    couple = replace(
        couple,
        household=replace(
            couple.household, people=(couple.household.people[0], young)
        ),
    )
    with pytest.raises(CountedRefusal, match="RULES_ENGINE_GAP"):
        runner.run(couple)
    assert runner.accounting.attempted == runner.accounting.refused == 2


def test_installed_pin_mismatch_refuses_before_calculation(monkeypatch):
    runner = invented_runner()
    pin = load_pin()
    pin["versions"]["policyengine"] = "0.0.0-INVENTED-MISMATCH"
    monkeypatch.setattr(
        "populace_dynamics.income_resources.ssi.runner.load_pin", lambda: pin
    )
    with pytest.raises(CountedRefusal, match="pinned"):
        runner.run(invented_case())
    assert runner.accounting.attempted == runner.accounting.refused == 1


# Runs in the pinned interpreter. Each enum class is executed alone from the
# installed source, under that release's own Enum base, without importing
# the country model.
ENUM_CHILD = """
import ast, hashlib, importlib.util, json, sys
from pathlib import Path
from policyengine_core.enums import Enum

spec = importlib.util.find_spec("policyengine_us")
package = Path(spec.submodule_search_locations[0])
observed = []
for record in json.load(sys.stdin):
    path = package / record["path"]
    text = path.read_text()
    tree = ast.parse(text)
    variable = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == record["name"]
    )
    possible = next(
        ast.unparse(item.value) for item in variable.body
        if isinstance(item, ast.Assign)
        and any(getattr(t, "id", None) == "possible_values" for t in item.targets)
    )
    source = next(
        ast.get_source_segment(text, node) for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == possible
    )
    namespace = {"Enum": Enum}
    exec(source, namespace)
    observed.append({
        "name": record["name"],
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "members": list(namespace[possible].__members__),
    })
json.dump(observed, sys.stdout)
"""


def test_inventory_enum_members_match_the_pinned_enum_classes():
    """Differential: the static members against the pinned Enum's own."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    inventory = json.loads(
        CONTRACT_PATH.with_name("inventory.json").read_text()
    )
    # The contract reads the input records, so both lists are checked.
    records = [
        r
        for key in ("inputs", "variables")
        for r in inventory[key]
        if r["value_type"] == "Enum"
    ]
    assert any(r in inventory["inputs"] for r in records)
    completed = subprocess.run(
        [str(python), "-I", "-c", ENUM_CHILD],
        input=json.dumps(records),
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    observed = json.loads(completed.stdout)
    assert [r["name"] for r in observed] == [r["name"] for r in records]
    for record, pinned in zip(records, observed, strict=True):
        # The source read is the pinned file, and its members agree.
        assert pinned["sha256"] == record["sha256"]
        assert pinned["members"] == record["enum_members"]
        assert record["default"] in record["enum_members"]
