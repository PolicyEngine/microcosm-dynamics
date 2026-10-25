"""Public-interface oracle checks on invented households only.

POPULACE_DYNAMICS_PE_US_PYTHON_SSI0 deliberately contains the static oracle
tier substring without reusing the older bridge environment variable.
"""

import ast
import json
import os
import re
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
from .test_ssi_inventory import (
    ADMITTED_FORMS,
    REFUSED_FORMS,
    invented_enum_module,
    read_members,
)
from .test_ssi_inventory import inventory as inventory_script


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


# Runs in the pinned interpreter. It loads the country model as the engine
# does and reads each enum variable's class from it, so code anywhere in the
# release that rebinds or changes a class shows here.
ENUM_CHILD = """
import hashlib, inspect, json, sys
from pathlib import Path
from policyengine_us import CountryTaxBenefitSystem

system = CountryTaxBenefitSystem()
observed = []
for name in json.load(sys.stdin):
    variable = system.variables[name]
    cls = variable.possible_values
    path = Path(inspect.getsourcefile(cls))
    observed.append({
        "name": name,
        "path": path.as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bases": [
            f"{base.__module__}.{base.__qualname__}" for base in cls.__bases__
        ],
        "members": list(cls.__members__),
        "canonical": [member.name for member in cls],
        "indices": [member.index for member in cls],
        "default": variable.default_value.name,
    })
json.dump(observed, sys.stdout)
"""


def test_inventory_enum_members_match_the_pinned_enum_classes():
    """Differential: the static members against the classes the pinned
    engine loads."""
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
        input=json.dumps([r["name"] for r in records]),
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    observed = json.loads(completed.stdout)
    assert [r["name"] for r in observed] == [r["name"] for r in records]
    for record, pinned in zip(records, observed, strict=True):
        # The class the engine loads comes from the pinned file and subclasses
        # policyengine_core's Enum, and its members, with no aliases, agree.
        assert pinned["path"].endswith("/policyengine_us/" + record["path"])
        assert pinned["sha256"] == record["sha256"]
        assert pinned["bases"] == ["policyengine_core.enums.enum.Enum"]
        assert pinned["members"] == pinned["canonical"]
        assert pinned["members"] == record["enum_members"]
        assert pinned["default"] == record["default"]
        # Each member encodes as its position, as the engine's Enum numbers
        # them; a store through a member could change that and not the
        # membership.
        assert pinned["indices"] == list(range(len(pinned["members"])))


# Runs in the pinned interpreter: what the engine gives each named variable.
ATTRIBUTE_CHILD = """
import json, sys
from policyengine_us import CountryTaxBenefitSystem

system = CountryTaxBenefitSystem()
observed = []
for name in json.load(sys.stdin):
    variable = system.variables[name]
    default = variable.default_value
    observed.append({
        "name": name,
        "value_type": variable.value_type.__name__,
        "default": getattr(default, "name", default),
        "entity": variable.entity.key,
        "period": variable.definition_period,
    })
json.dump(observed, sys.stdout)
"""


def test_inventory_attributes_match_the_pinned_engine():
    """Differential: each inventoried variable's value_type, default, entity
    and period against what the pinned engine gives it. The static read
    names them by spelling, which reflection could change."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    inventory = json.loads(
        CONTRACT_PATH.with_name("inventory.json").read_text()
    )
    records = [r for key in ("inputs", "variables") for r in inventory[key]]
    completed = subprocess.run(
        [str(python), "-I", "-c", ATTRIBUTE_CHILD],
        input=json.dumps([r["name"] for r in records]),
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    observed = json.loads(completed.stdout)
    assert {r["value_type"] for r in records} == {
        "bool",
        "float",
        "int",
        "Enum",
    }
    for record, pinned in zip(records, observed, strict=True):
        assert pinned["name"] == record["name"]
        assert pinned["value_type"] == record["value_type"]
        assert pinned["default"] == record["default"]
        # The source spells the entity's class and the period's constant.
        entity = re.sub(r"(?<!^)(?=[A-Z])", "_", record["entity"]).lower()
        assert pinned["entity"] == entity
        assert pinned["period"] == record["period"].lower()


# Runs in the pinned interpreter. It loads each invented module through the
# engine's own loader, one new variable each, and reports what the engine
# reads, or the error that stopped the load.
INVENTED_MODULE_CHILD = """
import json, sys, tempfile
from pathlib import Path
from policyengine_us import CountryTaxBenefitSystem

system = CountryTaxBenefitSystem()
observed = []
with tempfile.TemporaryDirectory() as folder:
    for index, source in enumerate(json.load(sys.stdin)):
        path = Path(folder) / f"invented_module_{index}.py"
        path.write_text(source)
        before = set(system.variables)
        try:
            system.add_variables_from_file(str(path))
            (name,) = set(system.variables) - before
            variable = system.variables[name]
            cls = variable.possible_values
            observed.append({
                "members": list(cls.__members__),
                "canonical": [member.name for member in cls],
                "indices": [member.index for member in cls],
                "default": variable.default_value.name,
            })
        except Exception as error:
            observed.append({"error": type(error).__name__})
json.dump(observed, sys.stdout)
"""
INVENTED_ENGINE_PREFIX = (
    "from policyengine_us.model_api import *\n\n\n"
    "class InventedOtherEnum(Enum):\n"
    '    INVENTED_OTHER = "other"\n\n\n'
)
INVENTED_TWO_MEMBERS = ["INVENTED_ONE", "INVENTED_TWO"]


def invented_engine_module(kinds):
    """An invented two-member module with the named forms, for the engine,
    which requires a label."""
    forms = [("body_head", 'label = "Invented status"')] + [
        (place, text.format(name="InventedEnum", member="INVENTED_TWO"))
        for kind in kinds
        for place, text, _ in [(ADMITTED_FORMS | REFUSED_FORMS)[kind]]
    ]
    class_source = "class InventedEnum(Enum):\n" + "".join(
        f'    {member} = "{member.lower()}"\n'
        for member in INVENTED_TWO_MEMBERS
    )
    return INVENTED_ENGINE_PREFIX + invented_enum_module(
        class_source, "InventedEnum", "INVENTED_ONE", forms
    )


def test_invented_modules_load_in_the_engine_as_the_reader_reads_them():
    """Differential: the static reader against the pinned engine's loader,
    including forms the harness's stand-in Variable cannot show."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    admitted = [[], *([kind] for kind in sorted(ADMITTED_FORMS))]
    admitted.append(sorted(ADMITTED_FORMS))
    # The engine calls a variable's own set to read its attributes, even one
    # bound beside an engine attribute, and a store through a member
    # renumbers it: all load without an error.
    silent = [
        ["variable_method"],
        ["chained_method", "set_function"],
        ["member_store"],
    ]
    sources = [
        invented_engine_module(kinds).replace(
            "invented_status", f"invented_status_{index}"
        )
        for index, kinds in enumerate(admitted + silent)
    ]
    completed = subprocess.run(
        [str(python), "-I", "-c", INVENTED_MODULE_CHILD],
        input=json.dumps(sources),
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    observed = json.loads(completed.stdout)
    plain = {
        "members": INVENTED_TWO_MEMBERS,
        "canonical": INVENTED_TWO_MEMBERS,
        "indices": [0, 1],
        "default": "INVENTED_ONE",
    }
    for kinds, engine in zip(admitted + silent, observed, strict=True):
        read = read_members(invented_engine_module(kinds))
        if kinds in silent:
            assert read is None
            assert "error" not in engine and engine != plain
        else:
            assert read == INVENTED_TWO_MEMBERS
            assert engine == plain


def test_engine_attributes_are_those_the_pinned_variable_reads():
    """The reader's allowed variable attributes against the pinned core's
    Variable constructor, read statically."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    completed = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "import policyengine_core.variables.variable as module; "
            "print(module.__file__)",
        ],
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    tree = ast.parse(Path(completed.stdout.strip()).read_bytes())
    variable = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Variable"
    )
    constructor = next(
        node
        for node in variable.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    # The names it passes to self.set, and those it pops from attr itself.
    read = set()
    for call in ast.walk(constructor):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
        ):
            continue
        owner, method = call.func.value.id, call.func.attr
        position = {("self", "set"): 1, ("attr", "pop"): 0}.get(
            (owner, method)
        )
        if position is not None:
            argument = call.args[position]
            assert isinstance(argument, ast.Constant)
            read.add(argument.value)
    assert read == inventory_script.ENGINE_ATTRIBUTES
