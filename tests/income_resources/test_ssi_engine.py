"""Public-interface oracle checks on invented households only.

POPULACE_DYNAMICS_PE_US_PYTHON_SSI0 deliberately contains the static oracle
tier substring without reusing the older bridge environment variable.
"""

import ast
import copy
import hashlib
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.ssi.contract import CONTRACT_PATH
from populace_dynamics.income_resources.ssi.pinning import load_pin
from populace_dynamics.income_resources.ssi.records import (
    CountedRefusal,
    SSIResult,
)
from populace_dynamics.income_resources.ssi.runner import (
    DEFAULT_PYTHON,
    OVERRIDABLE_PARAMETERS,
    PYTHON_ENV,
    SSIRunner,
)

from .ssi_invented import INVENTED_INPUTS, INVENTED_POLICY, invented_case
from .test_ssi_inventory import (
    ADMITTED_AGE_FORMS,
    ADMITTED_FORMS,
    ADMITTED_NAMING_FORMS,
    ATTRIBUTE_ROUTES,
    CORE_DEFAULT_BINDINGS,
    CORE_DEFAULT_CHANGES,
    DEFINED_FOR_GATES,
    ENUM_ALIAS_LAYOUTS,
    INPUT_RULE_FORMS,
    INVENTED_AGE_RECORD,
    INVENTED_AMOUNT,
    INVENTED_AMOUNT_PATH,
    INVENTED_EMPLOYMENT_INCOME,
    INVENTED_ENCODE_MEMBER_CLASS,
    INVENTED_TWIN,
    MIXED_MODE_FORMS,
    NAMING_ATTRIBUTE_FORMS,
    REFUSED_FORMS,
    REFUSED_NAMING_FORMS,
    SINGLE_MODE_FORMS,
    core_default_module,
    invented_age_module,
    invented_enum_module,
    invented_package,
    package_with_layout,
    package_with_named_lines,
    package_with_trigger,
    read_attributes,
    read_members,
    trigger_module,
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


# Runs in the pinned interpreter: what the engine gives each named variable,
# with its entity and period in every spelling the model API binds them to,
# as the inventory records them; whether it holds the variable to be an
# input; and the adds, subtracts and defined_for it holds, with the names
# each dated value of a parameter that a string adds or subtracts names.
ATTRIBUTE_CHILD = """
import enum, json, sys
import policyengine_us.model_api as model_api
from policyengine_core.entities import Entity
from policyengine_core.parameters import get_parameter
from policyengine_us import CountryTaxBenefitSystem

spellings = {}
for spelling, value in sorted(vars(model_api).items()):
    if isinstance(value, Entity):
        spellings.setdefault(("entity", value.key), []).append(spelling)
for spelling in ("DAY", "MONTH", "YEAR", "ETERNITY"):
    value = getattr(model_api, spelling)
    spellings.setdefault(("period", value), []).append(spelling)
system = CountryTaxBenefitSystem()


def naming(value):
    if value is None or not isinstance(value, str):
        return None if value is None else list(value)
    return value


def listed(value):
    if not isinstance(value, str):
        return None
    parameter = get_parameter(system.parameters, value)
    return sorted({item for row in parameter.values_list for item in row.value})


observed = []
for name in json.load(sys.stdin):
    variable = system.variables[name]
    default = variable.default_value
    observed.append({
        "name": name,
        "value_type": variable.value_type.__name__,
        "default": getattr(default, "name", default),
        "default_type": (
            "member"
            if isinstance(default, enum.Enum)
            else type(default).__name__
        ),
        "entity": spellings.get(("entity", variable.entity.key)),
        "period": spellings.get(("period", variable.definition_period)),
        "is_input": variable.is_input_variable(),
        "adds": naming(variable.adds),
        "subtracts": naming(variable.subtracts),
        "defined_for": variable.defined_for,
        "adds_listed": listed(variable.adds),
        "subtracts_listed": listed(variable.subtracts),
    })
json.dump(observed, sys.stdout)
"""


def engine_default_type(record):
    """The type of the default the engine holds for an inventory record,
    derived from the record's own default and value_type.

    The pinned ``Variable.set`` converts only a value the class binds, and
    only an int, bool included, for a float variable, with float(); it
    returns the core type default unconverted. So an explicit int or bool
    default of a float variable is a float in the engine; every other
    default keeps the record's type; and an enum default is a member of
    its class."""
    default = record["default"]
    if record["value_type"] == "Enum":
        return "member"
    if (
        record["value_type"] == "float"
        and record["default_origin"] == "explicit"
        and isinstance(default, int)
    ):
        return "float"
    return type(default).__name__


def test_inventory_attributes_match_the_pinned_engine():
    """Differential: each inventoried variable's value_type, default, entity
    and period against what the pinned engine gives it. The static read
    names them by spelling, which reflection could change. Defaults compare
    by value and by type, as ``engine_default_type`` gives it: False == 0
    and 40 == 40.0, but the engine keeps each type."""
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
    # The release has an int default that the engine converts: age's 40.
    assert any(
        r["value_type"] == "float"
        and r["default_origin"] == "explicit"
        and type(r["default"]) is int
        for r in records
    )
    inputs = {r["name"] for r in inventory["inputs"]}
    boundaries = set(inventory["explicit_formula_boundaries"])
    # Round 12's M1 and L1 need both kinds, and a string adds.
    assert {pinned["is_input"] for pinned in observed} == {False, True}
    assert any(isinstance(pinned["adds"], str) for pinned in observed)
    for record, pinned in zip(records, observed, strict=True):
        assert pinned["name"] == record["name"]
        assert pinned["value_type"] == record["value_type"]
        assert pinned["default"] == record["default"]
        assert pinned["default_type"] == engine_default_type(record)
        # The model API binds each entity and period under one spelling,
        # the one the source names.
        assert pinned["entity"] == [record["entity"]]
        assert pinned["period"] == [record["period"]]
        name = record["name"]
        if name in boundaries:
            # A boundary is an input by the contract's choice, whatever
            # the engine computes for it, and its dependencies are bypassed.
            assert name in inputs
            continue
        # Round 12's M1: an input exactly when the engine holds it to be.
        assert (name in inputs) == pinned["is_input"], name
        # Round 12's L1: the tracer records no parameter that a string adds
        # or subtracts names, so the attributes are compared here. Each
        # names a parameter on the record, and the names the parameter lists
        # on any date are its dependencies; each list item names a variable
        # among them, or, holding a period, a parameter on the record.
        for attribute in ("adds", "subtracts"):
            value = pinned[attribute]
            if isinstance(value, str):
                assert value in record["parameter_dependencies"], name
                assert set(pinned[f"{attribute}_listed"]) <= set(
                    record["dependencies"]
                ), name
            for item in value if isinstance(value, list) else ():
                assert item in (
                    record["parameter_dependencies"]
                    if "." in item
                    else record["dependencies"]
                ), name
        if pinned["defined_for"] is not None:
            assert pinned["defined_for"] in record["dependencies"], name


# Runs in the pinned interpreter: where the installed policyengine_us is.
# Finding a top-level package runs none of its code.
PACKAGE_CHILD = (
    "import importlib.util\n"
    'spec = importlib.util.find_spec("policyengine_us")\n'
    "print(spec.submodule_search_locations[0])\n"
)


def pinned_package(python):
    """The pinned interpreter's policyengine_us folder."""
    completed = subprocess.run(
        [str(python), "-I", "-c", PACKAGE_CHILD],
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    return Path(completed.stdout.strip())


def test_inventory_defaults_are_the_pinned_source_literals():
    """Each record's default, by value and type, is the literal the pinned
    source binds to default_value, or the core type default where it
    binds none. The engine holds one float for an explicit 40 and 40.0 of
    a float variable, so the attribute oracle cannot tell a record's 40.0
    from the source's 40; this reads the source and runs no engine."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    package = pinned_package(python)
    inventory = json.loads(
        CONTRACT_PATH.with_name("inventory.json").read_text()
    )
    records = [r for key in ("inputs", "variables") for r in inventory[key]]
    origins = set()
    for record in records:
        name = record["name"]
        path = package / record["path"]
        source = path.read_bytes()
        assert hashlib.sha256(source).hexdigest() == record["sha256"], name
        (variable,) = [
            node
            for node in ast.parse(source).body
            if isinstance(node, ast.ClassDef) and node.name == name
        ]
        assert variable.lineno == record["line"], name
        bound = [
            item.value
            for item in variable.body
            if isinstance(item, ast.Assign)
            and [ast.unparse(target) for target in item.targets]
            == ["default_value"]
        ]
        if bound:
            (value,) = bound
            expected = (
                value.attr
                if record["value_type"] == "Enum"
                else ast.literal_eval(value)
            )
            assert record["default_origin"] == "explicit", name
        else:
            expected = inventory_script.TYPE_DEFAULTS[record["value_type"]]
            assert record["default_origin"] == "core type", name
        assert record["default"] == expected, name
        assert type(record["default"]) is type(expected), name
        origins.add(record["default_origin"])
    assert origins == {"core type", "explicit"}


# Runs in the pinned interpreter. It loads each invented module through the
# engine's own loader and reports what the engine gives its one new
# variable, or the error that stopped the load. A module may change the
# builtins, so they are restored after each.
ATTRIBUTE_ROUTE_CHILD = """
import builtins, json, sys, tempfile
from pathlib import Path
from policyengine_us import CountryTaxBenefitSystem

namespace = vars(builtins)
saved = dict(namespace)
system = CountryTaxBenefitSystem()
observed = []
with tempfile.TemporaryDirectory() as folder:
    for index, source in enumerate(json.load(sys.stdin)):
        path = Path(folder) / f"invented_route_{index}.py"
        path.write_text(source)
        before = set(system.variables)
        try:
            system.add_variables_from_file(str(path))
            (name,) = set(system.variables) - before
            variable = system.variables[name]
            default = variable.default_value
            observed.append({
                "value_type": variable.value_type.__name__,
                "entity": variable.entity.key,
                "period": variable.definition_period,
                "default": getattr(default, "name", default),
            })
        except Exception as error:
            observed.append({"error": type(error).__name__})
        finally:
            for key in [key for key in namespace if key not in saved]:
                del namespace[key]
            namespace.update(saved)
json.dump(observed, sys.stdout)
"""


def test_attribute_routes_change_what_the_engine_loads():
    """Differential: the plain invented module loads in the pinned engine as
    the reader records it, and each route the reader refuses loads, without
    an error, with another value_type, entity, period or default."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    kinds = sorted(ATTRIBUTE_ROUTES)
    sources = [
        source.replace("invented_age", f"invented_age_{index}")
        for index, source in enumerate(
            [invented_age_module()]
            + [
                invented_age_module(ATTRIBUTE_ROUTES[kind][0])
                for kind in kinds
            ]
        )
    ]
    completed = subprocess.run(
        [str(python), "-I", "-c", ATTRIBUTE_ROUTE_CHILD],
        input=json.dumps(sources),
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    plain, *routes = json.loads(completed.stdout)
    assert read_attributes(invented_age_module()) == INVENTED_AGE_RECORD
    assert plain == {
        "value_type": "int",
        "entity": "person",
        "period": "year",
        "default": 41,
    }
    for kind, engine in zip(kinds, routes, strict=True):
        assert (
            read_attributes(invented_age_module(ATTRIBUTE_ROUTES[kind][0]))
            is None
        )
        assert "error" not in engine, kind
        assert engine != plain, kind


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
    path = Path(completed.stdout.strip())
    tree = ast.parse(path.read_bytes())
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
    # The constructor takes as formulas the names with this prefix, which
    # the reader reads by its spelling.
    config = ast.parse(path.with_name("config.py").read_bytes())
    (prefix,) = [
        item.value
        for item in config.body
        if isinstance(item, ast.Assign)
        and [ast.unparse(target) for target in item.targets]
        == ["FORMULA_NAME_PREFIX"]
    ]
    assert ast.literal_eval(prefix) == "formula"


def core_constant(path, name):
    """The value of the one top-level assignment of ``name`` in ``path``,
    read statically: a literal, or the literal a re.compile call takes."""
    (value,) = [
        item.value
        for item in ast.parse(path.read_bytes()).body
        if isinstance(item, ast.Assign)
        and [ast.unparse(target) for target in item.targets] == [name]
    ]
    if isinstance(value, ast.Call):
        assert ast.unparse(value.func) == "re.compile"
        (value,) = value.args
    if isinstance(value, ast.Tuple):
        return {ast.unparse(item) for item in value.elts}
    return ast.literal_eval(value)


def test_parameter_tree_rules_are_the_pinned_cores():
    """The constants the reader mirrors against the pinned core's source,
    read statically: the suffixes the parameter node walk loads, the names
    it skips, an index file as a node's metadata, the pattern of dated
    keys, and the value types a defined_for may name."""
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
    core = Path(completed.stdout.strip()).parents[1]
    parameters = core / "parameters"
    assert core_constant(parameters / "config.py", "FILE_EXTENSIONS") == set(
        inventory_script.PARAMETER_SUFFIXES
    )
    skipped = core_constant(
        parameters / "parameter_node.py", "EXCLUDED_PARAMETER_CHILD_NAMES"
    )
    walk = ast.unparse(
        ast.parse((parameters / "parameter_node.py").read_bytes())
    )
    assert "if child_name == 'index':" in walk
    assert set(skipped) | {"index"} == inventory_script.PARAMETER_SKIPPED
    assert (
        core_constant(core / "periods/config.py", "INSTANT_PATTERN")
        == inventory_script.INSTANT_PATTERN.pattern
    )
    assert (
        core_constant(core / "variables/variable.py", "NUMERIC_VALUE_TYPES")
        == inventory_script.NUMERIC_VALUE_TYPES
    )


# Runs in the pinned interpreter. It loads each invented module through the
# engine's own loader and reports the default the engine gives its one new
# variable. policyengine_core's type defaults and the builtins are restored
# after each module, so no change reaches the next.
CORE_DEFAULT_CHILD = """
import builtins, json, sys, tempfile
from pathlib import Path
from policyengine_core.variables import config
from policyengine_us import CountryTaxBenefitSystem

namespace = vars(builtins)
saved = dict(namespace)
saved_types = {key: dict(value) for key, value in config.VALUE_TYPES.items()}
system = CountryTaxBenefitSystem()
observed = []
with tempfile.TemporaryDirectory() as folder:
    for index, source in enumerate(json.load(sys.stdin)):
        path = Path(folder) / f"invented_core_default_{index}.py"
        path.write_text(source)
        before = set(system.variables)
        try:
            system.add_variables_from_file(str(path))
            (name,) = set(system.variables) - before
            variable = system.variables[name]
            observed.append({
                "value_type": variable.value_type.__name__,
                "default": variable.default_value,
                "default_type": type(variable.default_value).__name__,
            })
        except Exception as error:
            observed.append({"error": type(error).__name__})
        finally:
            for key in [key for key in namespace if key not in saved]:
                del namespace[key]
            namespace.update(saved)
            for key, value in saved_types.items():
                config.VALUE_TYPES[key].clear()
                config.VALUE_TYPES[key].update(value)
json.dump(observed, sys.stdout)
"""


def test_core_default_changes_change_what_the_engine_loads():
    """Differential: a module that reaches policyengine_core's type
    defaults, without changing them, loads in the pinned engine as the
    reader records it; each change the reader refuses, through the core
    import or through the model API, gives the engine's variable another
    default."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    controls = {
        value_type: core_default_module(
            value_type, CORE_DEFAULT_BINDINGS["model_api"]
        )
        for value_type in ("bool", "float", "int")
    }
    changes = [
        (change, binding)
        for change in sorted(CORE_DEFAULT_CHANGES)
        for binding in sorted(CORE_DEFAULT_BINDINGS)
    ]
    sources = list(controls.values()) + [
        core_default_module(
            CORE_DEFAULT_CHANGES[change][0],
            CORE_DEFAULT_BINDINGS[binding],
            CORE_DEFAULT_CHANGES[change][1],
        )
        for change, binding in changes
    ]
    completed = subprocess.run(
        [str(python), "-I", "-c", CORE_DEFAULT_CHILD],
        input=json.dumps(
            [
                source.replace("invented_age", f"invented_age_{index}")
                for index, source in enumerate(sources)
            ]
        ),
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    observed = json.loads(completed.stdout)
    for (value_type, source), engine in zip(
        controls.items(), observed, strict=False
    ):
        read = read_attributes(source)
        assert read["default"] == inventory_script.TYPE_DEFAULTS[value_type]
        assert engine == {
            "value_type": value_type,
            "default": read["default"],
            "default_type": type(read["default"]).__name__,
        }
    for (change, binding), engine in zip(
        changes, observed[len(controls) :], strict=True
    ):
        value_type, text, value = CORE_DEFAULT_CHANGES[change]
        source = core_default_module(
            value_type, CORE_DEFAULT_BINDINGS[binding], text
        )
        assert read_attributes(source) is None
        assert "error" not in engine, (change, binding)
        assert engine["default"] == value, (change, binding)
        assert engine["default"] != inventory_script.TYPE_DEFAULTS[value_type]


# Runs in the pinned interpreter: the files the engine's own directory walk
# loads from an invented variables folder, and the default it gives each
# variable they define. The folder joins the end of
# policyengine_us.variables' path, so a module there that imports from
# policyengine_us.variables.<name> imports the folder's own <name>.py
# when the installed release has none.
WALK_CHILD = """
import json, sys
import policyengine_us.variables as variables_package
from policyengine_core.taxbenefitsystems import TaxBenefitSystem
from policyengine_us.entities import entities

tree = sys.argv[1]
variables_package.__path__.append(tree)
loaded = []
load = TaxBenefitSystem.add_variables_from_file


def recording(self, file_path):
    loaded.append(str(file_path))
    return load(self, file_path)


TaxBenefitSystem.add_variables_from_file = recording


class InventedSystem(TaxBenefitSystem):
    variables_dir = tree


system = InventedSystem(entities)
json.dump(
    {
        "files": loaded,
        "variables": {
            name: {
                "default": variable.default_value,
                "default_type": type(variable.default_value).__name__,
            }
            for name, variable in sorted(system.variables.items())
        },
    },
    sys.stdout,
)
"""
INVENTED_WALK_FILES = {
    "input/invented_walk_one.py": "invented_walk_one",
    ".invented_hidden/invented_walk_two.py": "invented_walk_two",
    "input/.invented_walk_three.py": "invented_walk_three",
    "gov/__init__.py": "invented_walk_four",
    "gov/invented_walk_five.py": "invented_walk_five",
    "gov/deeper/_invented_walk_six.py": "invented_walk_six",
    "gov/deeper/.invented_hidden/invented_walk_seven.py": (
        "invented_walk_seven"
    ),
    # Its name ends in __init__.py, but it is not the folder's own init.
    "gov/invented__init__.py": "invented_walk_eight",
}


def write_walk_file(path, name):
    """An invented variables file the engine can load, defining ``name``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Invented label\n"
        "from policyengine_us.model_api import *\n\n\n"
        f"class {name}(Variable):\n"
        "    value_type = float\n"
        "    entity = Person\n"
        "    definition_period = YEAR\n"
        '    label = "Invented walk"\n'
    )


def engine_walk(python, tree):
    """What the pinned engine's directory walk does with ``tree``."""
    completed = subprocess.run(
        [str(python), "-I", "-c", WALK_CHILD, str(tree)],
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    return json.loads(completed.stdout)


def test_variable_files_are_those_the_engine_walk_loads(tmp_path):
    """Differential: the reader's file index against the pinned engine's
    directory walk, on an invented folder with hidden names, a package init
    that defines a variable, a file whose name ends in __init__.py, and a
    helper-named module."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    tree = tmp_path / "variables"
    for relative, name in INVENTED_WALK_FILES.items():
        write_walk_file(tree / relative, name)
    engine = engine_walk(python, tree)
    read = inventory_script.variable_files(tree)
    assert len(read) == len(set(read))
    assert sorted(Path(file) for file in engine["files"]) == sorted(read)
    assert list(engine["variables"]) == [
        "invented_walk_eight",
        "invented_walk_five",
        "invented_walk_one",
        "invented_walk_six",
    ]


# Runs in the pinned interpreter: the files, relative to its variables
# folder and in the order loaded, that the country system's own directory
# walk loads as it is built.
RELEASE_WALK_CHILD = """
import json, sys
from pathlib import Path
from policyengine_core.taxbenefitsystems import TaxBenefitSystem

loaded = []
load = TaxBenefitSystem.add_variables_from_file


def recording(self, file_path):
    loaded.append(str(file_path))
    return load(self, file_path)


TaxBenefitSystem.add_variables_from_file = recording
from policyengine_us import CountryTaxBenefitSystem

loaded.clear()
system = CountryTaxBenefitSystem()
root = Path(CountryTaxBenefitSystem.variables_dir)
json.dump(
    {
        "variables_dir": str(root),
        "files": [Path(file).relative_to(root).as_posix() for file in loaded],
    },
    sys.stdout,
)
"""


def test_variable_files_are_the_pinned_release_walk():
    """Differential: the reader's file index of the pinned release's
    variables folder, in order, against the files the country system's own
    walk loads from it."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    folder = pinned_package(python) / "variables"
    completed = subprocess.run(
        [str(python), "-I", "-c", RELEASE_WALK_CHILD],
        capture_output=True,
        text=True,
        timeout=1800,
        check=True,
    )
    engine = json.loads(completed.stdout)
    assert Path(engine["variables_dir"]).resolve() == folder.resolve()
    read = [
        path.relative_to(folder).as_posix()
        for path in inventory_script.variable_files(folder)
    ]
    assert len(read) == len(set(read))
    assert read == engine["files"]


def test_folder_whose_path_is_a_glob_pattern_splits_the_engine_walk(
    tmp_path,
):
    """Differential, round 9's repro: the engine's walk of invented_a[b]/
    globs invented_a[b]/*.py, which matches invented_ab/__init__.py and
    not the path it joins for the folder's own init, so it loads that init
    as variables, as no walk of invented_ab/ does. The reader refuses the
    folder."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    tree = tmp_path / "variables"
    (tree / "invented_a[b]").mkdir(parents=True)
    (tree / "invented_a[b]/NOTE.txt").write_text("Invented note\n")
    write_walk_file(tree / "invented_ab/__init__.py", "invented_walk_glob")
    engine = engine_walk(python, tree)
    assert engine["files"] == [str(tree / "invented_ab/__init__.py")]
    assert list(engine["variables"]) == ["invented_walk_glob"]
    with pytest.raises(
        ValueError,
        match=r"Glob pattern in variables folder .*/invented_a\[b\]$",
    ):
        inventory_script.variable_files(tree)
    # Without that folder, the walk and the reader load nothing.
    (tree / "invented_a[b]/NOTE.txt").unlink()
    (tree / "invented_a[b]").rmdir()
    assert engine_walk(python, tree) == {"files": [], "variables": {}}
    assert inventory_script.variable_files(tree) == []


def test_followed_variable_class_override_changes_what_the_engine_loads(
    tmp_path,
):
    """Differential, round 9's repro: employment_income imports from
    invented_tools.py, which the engine's walk loads first, building its
    invented_trigger. With a plain trigger the engine gives
    employment_income the core type default the reader records; with an
    override of Variable.set it gives another, and the reader refuses."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    engine = {}
    for kind in ("plain", "set_override"):
        tree = tmp_path / kind / "variables"
        (tree / "input").mkdir(parents=True)
        (tree / "invented_tools.py").write_text(
            trigger_module(None if kind == "plain" else kind)
        )
        (tree / "input/employment_income.py").write_text(
            INVENTED_EMPLOYMENT_INCOME
        )
        engine[kind] = engine_walk(python, tree)
        assert [Path(file) for file in engine[kind]["files"]] == [
            tree / "invented_tools.py",
            tree / "input/employment_income.py",
        ]
    package = package_with_trigger(tmp_path / "plain_read", trigger_module())
    record = next(
        v
        for v in inventory_script.inventory_release(package)["inputs"]
        if v["name"] == "employment_income"
    )
    assert record["default_origin"] == "core type"
    assert engine["plain"]["variables"]["employment_income"] == {
        "default": record["default"],
        "default_type": type(record["default"]).__name__,
    }
    changed = engine["set_override"]["variables"]["employment_income"]
    assert changed == {"default": 7, "default_type": "int"}
    assert changed["default"] != inventory_script.TYPE_DEFAULTS["float"]
    package = package_with_trigger(
        tmp_path / "override_read", trigger_module("set_override")
    )
    with pytest.raises(
        ValueError,
        match="Unread variable invented_trigger in variables/invented_tools.py",
    ):
        inventory_script.inventory_release(package)


def test_variable_class_on_a_bound_enum_changes_what_the_engine_loads(
    tmp_path,
):
    """Differential, round 10's M1 repro: invented_tools.py binds Enum to
    Variable, so its class on Enum is a variable class whose override of
    Variable.set the engine's walk runs before it loads employment_income.
    The engine gives employment_income 7, and the reader refuses."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    files, refused, _ = ENUM_ALIAS_LAYOUTS["followed_assign"]
    tree = tmp_path / "walk" / "variables"
    for relative, source in files.items():
        (tree / relative).parent.mkdir(parents=True, exist_ok=True)
        (tree / relative).write_text(source)
    engine = engine_walk(python, tree)
    assert [Path(file) for file in engine["files"]] == [
        tree / "invented_tools.py",
        tree / "input/employment_income.py",
    ]
    assert engine["variables"]["invented_trigger"] == {
        "default": 7,
        "default_type": "int",
    }
    changed = engine["variables"]["employment_income"]
    assert changed == {"default": 7, "default_type": "int"}
    assert changed["default"] != inventory_script.TYPE_DEFAULTS["float"]
    package = package_with_layout(tmp_path / "read", files)
    with pytest.raises(
        ValueError, match=f"^Unread module code in variables/{refused}$"
    ):
        inventory_script.inventory_release(package)


# Runs in the pinned interpreter, importing only its Enum: the members, in
# order, and whether the class's encode is still callable, for each
# invented class source.
ENUM_ENCODE_CHILD = """
import json, sys
from policyengine_core.enums import Enum

observed = []
for source in json.load(sys.stdin):
    namespace = {"Enum": Enum}
    exec(source, namespace)
    cls = namespace["InventedStatus"]
    observed.append({
        "members": list(cls.__members__),
        "canonical": [member.name for member in cls],
        "indices": [member.index for member in cls],
        "encode_callable": callable(cls.encode),
    })
json.dump(observed, sys.stdout)
"""


def test_enum_member_named_encode_replaces_the_engine_encode():
    """Differential: the engine's own Enum loads a member named encode in
    the order written, and that member takes the class's encode, which
    formulas and the engine call by its spelling; the reader refuses the
    class. Under another name the member leaves encode the method."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    renamed = INVENTED_ENCODE_MEMBER_CLASS.replace(
        "    encode = ", "    INVENTED_ENCODE = "
    )
    completed = subprocess.run(
        [str(python), "-I", "-c", ENUM_ENCODE_CHILD],
        input=json.dumps([INVENTED_ENCODE_MEMBER_CLASS, renamed]),
        capture_output=True,
        text=True,
        timeout=600,
        check=True,
    )
    member, control = json.loads(completed.stdout)
    assert member == {
        "members": ["INVENTED_FIRST", "encode"],
        "canonical": ["INVENTED_FIRST", "encode"],
        "indices": [0, 1],
        "encode_callable": False,
    }
    assert control == {
        "members": ["INVENTED_FIRST", "INVENTED_ENCODE"],
        "canonical": ["INVENTED_FIRST", "INVENTED_ENCODE"],
        "indices": [0, 1],
        "encode_callable": True,
    }
    for source, read in (
        (INVENTED_ENCODE_MEMBER_CLASS, None),
        (renamed, control["members"]),
    ):
        module = invented_enum_module(
            source, "InventedStatus", "INVENTED_FIRST"
        )
        assert read_members(module) == read


# Runs in the pinned interpreter. It loads each invented module through the
# engine's own loader and reports the adds, subtracts and defined_for the
# engine holds for its one new variable, and what each formula it holds
# returns when called with no arguments it reads.
LOADED_ATTRIBUTES_CHILD = """
import json, sys, tempfile
from pathlib import Path
from policyengine_us import CountryTaxBenefitSystem


def plain(value):
    if value is None or isinstance(value, str):
        return value
    return sorted(value) if isinstance(value, set) else list(value)


system = CountryTaxBenefitSystem()
observed = []
with tempfile.TemporaryDirectory() as folder:
    for index, source in enumerate(json.load(sys.stdin)):
        path = Path(folder) / f"invented_loaded_{index}.py"
        path.write_text(source)
        before = set(system.variables)
        try:
            system.add_variables_from_file(str(path))
            (name,) = set(system.variables) - before
            variable = system.variables[name]
            observed.append({
                "adds": plain(variable.adds),
                "subtracts": plain(variable.subtracts),
                "defined_for": plain(variable.defined_for),
                "formulas": [
                    formula(None, None, None)
                    for formula in variable.formulas.values()
                ],
            })
        except Exception as error:
            observed.append({"error": type(error).__name__})
json.dump(observed, sys.stdout)
"""
# What the engine loads for each naming-attribute form that loads without
# an error, as (attribute, value).
LOADED_NAMING_ATTRIBUTES = {
    "adds_name": ("adds", ["employment_income"]),
    "adds_sum": ("adds", ["employment_income", "pension_income"]),
    "adds_comprehension": ("adds", ["invented_one", "invented_two"]),
    "subtracts_name": ("subtracts", ["pension_income"]),
    "defined_for_name": ("defined_for", "employment_income"),
    "defined_for_member": ("defined_for", "employment_income"),
}
INVENTED_FORMULAS_TWICE = [
    (
        "body_tail",
        "def formula(person, period, parameters):\n"
        '    return person("employment_income", period)',
    ),
    ("body_tail", "def formula(person, period, parameters):\n    return 0"),
]


def test_naming_attributes_and_formulas_load_as_the_engine_reads_them(
    tmp_path,
):
    """Differential: each adds, subtracts or defined_for the reader refuses
    for a variable that is not a boundary loads in the pinned engine naming
    the variables the record would not list, and of two formulas of one
    name the engine holds only the last, where the record would list two.
    The plain module loads with none of them."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    kinds = sorted(LOADED_NAMING_ATTRIBUTES)
    forms = [[]] + [NAMING_ATTRIBUTE_FORMS[kind][0] for kind in kinds]
    forms.append(INVENTED_FORMULAS_TWICE)
    sources = [invented_age_module(form) for form in forms]
    completed = subprocess.run(
        [str(python), "-I", "-c", LOADED_ATTRIBUTES_CHILD],
        input=json.dumps(
            [
                source.replace("invented_age", f"invented_age_{index}")
                for index, source in enumerate(sources)
            ]
        ),
        capture_output=True,
        text=True,
        timeout=1800,
        check=True,
    )
    plain, *naming, twice = json.loads(completed.stdout)
    assert plain == {
        "adds": None,
        "subtracts": None,
        "defined_for": None,
        "formulas": [],
    }
    for index, (kind, engine) in enumerate(zip(kinds, naming, strict=True)):
        attribute, value = LOADED_NAMING_ATTRIBUTES[kind]
        assert "error" not in engine, kind
        assert engine[attribute] == value, kind
        package = invented_package(tmp_path / kind)
        (package / "variables/input/invented_age.py").write_text(
            sources[index + 1]
        )
        with pytest.raises(
            ValueError, match=f"Unresolved {attribute} for invented_age"
        ):
            inventory_script.inventory_release(package)
    # The last formula, which reads nothing, is the only one.
    assert twice == plain | {"formulas": [0]}
    assert read_attributes(sources[-1]) is None
    assert read_attributes(invented_age_module(INVENTED_FORMULAS_TWICE[:1]))


# An invented stand-in for the model API, for the core harness below: the
# names invented modules take, bound to policyengine_core directly, so that
# no country system is built.
INVENTED_SHIM_MODEL_API = """from policyengine_core.entities import build_entity
from policyengine_core.enums import Enum
from policyengine_core.periods import ETERNITY, MONTH, YEAR
from policyengine_core.variables import Variable

Person = build_entity(
    key="person", plural="people", label="Person", is_person=True
)
Household = build_entity(
    key="household",
    plural="households",
    label="Household",
    roles=[{"key": "member", "plural": "members", "label": "Member"}],
)
ENTITIES = [Person, Household]
"""
INVENTED_SHIM_IMPORT = "from policyengine_us.model_api import *\n\n\n"
# Runs in the pinned interpreter with the shim first on its path, and builds
# no country system: policyengine_core's own TaxBenefitSystem loads each
# invented package through its walks of variables/ and parameters/, and a
# simulation of one invented person calculates invented_named for 2026. It
# reports the error that stopped the load, or whether the engine holds
# invented_named to be an input, whether it holds a parameter
# gov.ssa.ssi.invented, and the value or the error of the calculation.
CORE_HARNESS_CHILD = """
import json, sys
sys.path.insert(0, sys.argv[1])
from policyengine_core.parameters import get_parameter
from policyengine_core.simulations import Simulation
from policyengine_core.taxbenefitsystems import TaxBenefitSystem
from policyengine_us.model_api import ENTITIES

observed = []
for root in json.load(sys.stdin):
    class InventedSystem(TaxBenefitSystem):
        variables_dir = root + "/variables"
        parameters_dir = root + "/parameters"

    try:
        system = InventedSystem(ENTITIES)
    except Exception as error:
        observed.append({"load_error": type(error).__name__})
        continue
    row = {"is_input": system.variables["invented_named"].is_input_variable()}
    try:
        get_parameter(system.parameters, "gov.ssa.ssi.invented")
        row["invented_parameter"] = True
    except Exception:
        row["invented_parameter"] = False
    person = {"employment_income": {"2026": 5.0}, "invented_age": {"2026": 41}}
    situation = {
        "people": {"invented": person},
        "households": {"unit": {"members": ["invented"]}},
    }
    try:
        simulation = Simulation(tax_benefit_system=system, situation=situation)
        values = simulation.calculate("invented_named", "2026")
        row["value"] = [float(value) for value in values]
    except Exception as error:
        row["error"] = type(error).__name__
    observed.append(row)
json.dump(observed, sys.stdout)
"""


def engine_ready(source):
    """An invented variables module the pinned core can load: with the
    model API's star import, and a label in each variable class that has
    none, since the engine refuses a variable without one. The reader
    admits both, and neither changes a record."""
    lines = source.splitlines(keepends=True)
    for node in reversed(ast.parse(source).body):
        if (
            isinstance(node, ast.ClassDef)
            and [ast.unparse(base) for base in node.bases] == ["Variable"]
            and not any(
                isinstance(item, ast.Assign)
                and [ast.unparse(target) for target in item.targets]
                == ["label"]
                for item in node.body
            )
        ):
            lines.insert(node.lineno, '    label = "Invented label"\n')
    return INVENTED_SHIM_IMPORT + "".join(lines)


def core_harness(tmp_path, cases):
    """The pinned core's load and calculation, and the reader's record of
    invented_named or its refusal, for each invented package that
    ``cases``, a list of (body lines, files), gives. Every variables file
    is made ``engine_ready``, so both read the same bytes."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    shim = tmp_path / "shim" / "policyengine_us"
    shim.mkdir(parents=True)
    (shim / "__init__.py").write_text("")
    (shim / "model_api.py").write_text(INVENTED_SHIM_MODEL_API)
    packages = []
    for index, (lines, files) in enumerate(cases):
        package = package_with_named_lines(
            tmp_path / f"case_{index}", lines, files
        )
        for path in sorted((package / "variables").rglob("*.py")):
            path.write_text(engine_ready(path.read_text()))
        packages.append(package)
    completed = subprocess.run(
        [str(python), "-I", "-c", CORE_HARNESS_CHILD, str(shim.parent)],
        input=json.dumps([str(package) for package in packages]),
        capture_output=True,
        text=True,
        timeout=1800,
        check=True,
    )
    read = []
    for package in packages:
        try:
            result = inventory_script.inventory_release(package)
        except ValueError as error:
            read.append(f"refused: {error}")
            continue
        inputs = {row["name"] for row in result["inputs"]}
        (record,) = [
            row
            for row in result["variables"]
            if row["name"] == "invented_named"
        ]
        read.append(record | {"is_input": "invented_named" in inputs})
    return json.loads(completed.stdout), read


# What the pinned core does with each form of INPUT_RULE_FORMS: the value it
# gives invented_named for one invented person, aged 41, with no other input.
ENGINE_INPUT_RULE_VALUES = {
    "plain": 0.0,
    "defined_for_only": 7.0,
    "label_equal_to_a_stem": 7.0,
    "formula_only": 41.0,
    "adds_parameters_only": 3.0,
    "string_adds_empty_list": 0.0,
    "adds_empty_list": 7.0,
    "subtracts_only": -41.0,
}


def test_inputs_are_those_the_core_engine_holds_to_be_inputs(tmp_path):
    """Differential, round 12's M1: for each invented form, the reader's
    input status against the pinned core's is_input_variable, with no
    country build. The engine gives the default of an unsupplied input,
    defined_for or not, and calculates every form that sets adds or
    subtracts, so a record read the old way would leave its default to the
    calculation or supply data over a value the engine computes."""
    kinds = sorted(INPUT_RULE_FORMS)
    engine, read = core_harness(
        tmp_path, [INPUT_RULE_FORMS[kind][:2] for kind in kinds]
    )
    for kind, observed, record in zip(kinds, engine, read, strict=True):
        assert observed == {
            "is_input": INPUT_RULE_FORMS[kind][2],
            "invented_parameter": False,
            "value": [ENGINE_INPUT_RULE_VALUES[kind]],
        }, kind
        assert record["is_input"] == observed["is_input"], kind


# What the pinned core does with each form of REFUSED_NAMING_FORMS, which
# the reader refuses: raises as it calculates, refuses to load, or reads.
ENGINE_REFUSED_NAMING = {
    "string_empty_part": {"error": "ValueError"},
    "string_other_case": {"error": "ValueError"},
    "list_names_itself": {"error": "CycleError"},
    "defined_for_names_itself": {"error": "RecursionError"},
    "list_item_absent": {"error": "ValueError"},
    "list_item_folder": {"error": "ValueError"},
    "list_item_node_key": {"value": [44.0]},
    "subtracts_names_itself": {"error": "CycleError"},
    "string_lists_itself": {"value": [41.0]},
    "list_item_other_case": {"error": "ValueError"},
    "list_item_empty_part": {"error": "ValueError"},
    "list_item_file_beside_folder": {"load_error": "ValueError"},
    "list_item_yaml_beside_yml": {"load_error": "ValueError"},
    "string_folder": {"error": "ValueError"},
    "string_node_file": {"error": "ValueError"},
    "string_dated_keys_only": {"value": [41.0]},
    "string_yml": {"value": [41.0]},
    "string_expected_entry": {"value": [41.0]},
    "string_lists_a_parameter": {"value": [44.0]},
    "list_item_top_level": {"value": [44.0]},
    "string_empty": {"value": [0.0]},
    "list_item_built_parameter": {"value": [41.0]},
    "string_empty_values": {"load_error": "ParameterParsingError"},
    "string_undated_key": {"load_error": "ParameterParsingError"},
    "string_repeated_key": {"load_error": "ParameterParsingError"},
    "string_number": {"error": "TypeError"},
    "string_skipped_name": {"error": "ValueError"},
    "defined_for_names_a_parameter": {"error": "ValueError"},
    "string_lists_a_class_of_another_stem": {"value": [7.0]},
    "gate_of_another_stem_beside_adds": {"value": [41.0]},
}
# The value the pinned core gives for each form of ADMITTED_NAMING_FORMS.
# Where the record's names differ from the engine's reads, the record lists
# more: the union over dates, and a repeated item once, which the engine
# sums twice.
ENGINE_ADMITTED_NAMING = {
    "list_item_parameter": 44.0,
    "list_item_outside_gov": -44.0,
    "string_union_over_dates": 41.0,
    "string_value_mappings": 41.0,
    "string_repeated_item": 82.0,
    "gate_beside_adds": 0.0,
}


def test_naming_forms_load_in_the_core_engine_as_the_reader_reads_them(
    tmp_path,
):
    """Differential, round 12's M3, with no country build: every name the
    reader refuses makes the pinned core raise, refuse to load, or read a
    value, which is the safe direction; every name it admits calculates."""
    refused = sorted(REFUSED_NAMING_FORMS)
    admitted = sorted(ADMITTED_NAMING_FORMS)
    engine, read = core_harness(
        tmp_path,
        [REFUSED_NAMING_FORMS[kind][:2] for kind in refused]
        + [ADMITTED_NAMING_FORMS[kind][:2] for kind in admitted],
    )
    rows = dict(
        zip(refused + admitted, zip(engine, read, strict=True), strict=True)
    )
    # The review's six forms and the self-names: the engine raises on all
    # but the key inside a YAML node, which it reads.
    for kind in refused:
        observed, record = rows[kind]
        assert record == f"refused: {REFUSED_NAMING_FORMS[kind][2]}", kind
        expected = ENGINE_REFUSED_NAMING[kind]
        assert {key: observed[key] for key in expected} == expected, kind
    for kind in admitted:
        observed, record = rows[kind]
        assert observed["value"] == [ENGINE_ADMITTED_NAMING[kind]], kind
        assert record["dependencies"] == ADMITTED_NAMING_FORMS[kind][2]


def test_load_time_refusals_are_the_core_engines(tmp_path):
    """Differential, with no country build: the pinned core refuses to load
    a defined_for that names an Enum or str variable, a variable of two
    computation modes, a variable name in two files and a parameter file
    that repeats a key, and the reader refuses each; each control loads in
    both. A .yml file in the federal SSI tree loads as a parameter in the
    engine, which the reader's table would leave out, so it refuses."""
    cases = {}
    for gate, (files, numeric) in DEFINED_FOR_GATES.items():
        cases[f"gate_{gate}"] = (
            [f'defined_for = "{gate}"'],
            files,
            not numeric,
        )
    for kind, lines in MIXED_MODE_FORMS.items():
        cases[kind] = (lines, {INVENTED_AMOUNT_PATH: INVENTED_AMOUNT}, True)
    for kind, lines in SINGLE_MODE_FORMS.items():
        cases[kind] = (lines, {INVENTED_AMOUNT_PATH: INVENTED_AMOUNT}, False)
    cases["class_in_two_files"] = (
        ['adds = ["invented_other", "invented_twin"]'],
        {
            "variables/input/invented_twin.py": INVENTED_TWIN,
            "variables/input/invented_other.py": (
                INVENTED_TWIN.replace("invented_twin", "invented_other")
                + "\n\n"
                + INVENTED_TWIN
            ),
        },
        True,
    )
    cases["repeated_key"] = (
        [],
        {INVENTED_AMOUNT_PATH: "values:\n  2020-01-01: 3\n  2020-01-01: 4\n"},
        True,
    )
    kinds = sorted(cases)
    engine, read = core_harness(tmp_path, [cases[kind][:2] for kind in kinds])
    for kind, observed, record in zip(kinds, engine, read, strict=True):
        refused = cases[kind][2]
        assert ("load_error" in observed) == refused, (kind, observed)
        assert isinstance(record, str) == refused, (kind, record)
        if not refused:
            assert "error" not in observed, (kind, observed)
    (yml,), (yml_read,) = core_harness(
        tmp_path / "yml",
        [([], {"parameters/gov/ssa/ssi/invented.yml": INVENTED_AMOUNT})],
    )
    assert yml["invented_parameter"] is True
    assert yml_read.startswith("refused: Unread .yml parameter file under")


# Import-time code with no Call node, which the reader admits: each form
# reaches policyengine_core's type defaults only by reads, through the
# model API's warnings module. Round 9 tried eleven such forms and found
# none that changes what the engine loads. One, a with statement over
# sys.stdin, is left out here, since it closes the stdin the child reads.
NO_CALL_TABLE = (
    'warnings.sys.modules["policyengine_core.variables.config"].VALUE_TYPES'
)
NO_CALL_FORMS = {
    "operator": f"INVENTED_OP = {NO_CALL_TABLE}[float] | {{'default': 7}}",
    "comparison": (
        f"INVENTED_CMP = {NO_CALL_TABLE}[float] == {{}} < 1 if 0 "
        "else Person == YEAR"
    ),
    "for_loop": (
        f"for INVENTED_KEY in {NO_CALL_TABLE}:\n"
        "    INVENTED_LAST = INVENTED_KEY"
    ),
    "match": (
        f"match {NO_CALL_TABLE}[float]:\n"
        "    case {'default': INVENTED_D}:\n"
        "        pass\n"
        "    case _:\n"
        "        INVENTED_D = 0"
    ),
    "comprehension": (
        f"INVENTED_COMP = [k for k in {NO_CALL_TABLE} "
        f"if {NO_CALL_TABLE}[k]]"
    ),
    "f_string": f"INVENTED_FMT = f'{{{NO_CALL_TABLE}[float]!r:>10}}{{YEAR}}'",
    "unpacking": f"INVENTED_A, *INVENTED_REST = {NO_CALL_TABLE}",
    "assert": f"assert {NO_CALL_TABLE}[float]['default'] == 0",
    "global": "global INVENTED_G\nINVENTED_G = 1",
    "walrus": f"(INVENTED_W := {NO_CALL_TABLE}[float])",
}


def test_admitted_import_time_forms_load_as_the_reader_reads_them():
    """Differential: each admitted form of the invented age module, async
    helper included, and each form of import-time code with no call, one
    at a time and all together, loads in the pinned engine with the
    value_type, entity, period and default the reader records."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    admitted = [
        ADMITTED_AGE_FORMS[kind] for kind in sorted(ADMITTED_AGE_FORMS)
    ]
    no_call = [("tail", NO_CALL_FORMS[kind]) for kind in sorted(NO_CALL_FORMS)]
    cases = (
        [[]]
        + [[form] for form in admitted]
        + [admitted]
        + [[form] for form in no_call]
        + [no_call]
    )
    sources = [invented_age_module(forms) for forms in cases]
    completed = subprocess.run(
        [str(python), "-I", "-c", ATTRIBUTE_ROUTE_CHILD],
        input=json.dumps(
            [
                source.replace("invented_age", f"invented_age_{index}")
                for index, source in enumerate(sources)
            ]
        ),
        capture_output=True,
        text=True,
        timeout=1800,
        check=True,
    )
    plain, *observed = json.loads(completed.stdout)
    assert read_attributes(sources[0]) == INVENTED_AGE_RECORD
    assert plain == {
        "value_type": "int",
        "entity": "person",
        "period": "year",
        "default": 41,
    }
    for source, engine in zip(sources[1:], observed, strict=True):
        read = read_attributes(source)
        assert read is not None
        assert read == INVENTED_AGE_RECORD | {"default": read["default"]}
        assert engine == plain | {"default": read["default"]}
        assert type(engine["default"]) is type(read["default"])


TRACE_CHILD = r"""
import json
import sys

from policyengine_us import Simulation

job = json.load(sys.stdin)


def walk(node, names, parameters, edges):
    names.add(node.name)
    parameters.update(row.name for row in node.parameters)
    for child in node.children:
        edges.add((node.name, child.name))
        walk(child, names, parameters, edges)


def trace(**options):
    names, parameters, edges, amounts = set(), set(), set(), set()
    response = 0.0
    for case in job["cases"]:
        simulation = Simulation(situation=case, trace=True, **options)
        for name, period in job["targets"]:
            simulation.calculate(name, period)
        for tree in simulation.tracer.trees:
            walk(tree, names, parameters, edges)
        values = simulation.calculate(
            "labor_supply_behavioral_response", job["year"]
        )
        response = max(response, float(abs(values).max()))
        # Read from the simulation's own tree, past the tracer, so that the
        # reform shows it took: an empty one would leave the baseline.
        tree = simulation.tax_benefit_system.parameters(f"{job['year']}-01-01")
        amounts.add(float(tree.gov.ssa.ssi.amount.individual))
    return {
        "variables": sorted(names),
        "parameters": sorted(parameters),
        "edges": sorted(edges),
        "response": response,
        "amounts": sorted(amounts),
    }


json.dump(
    {"plain": trace(), "reform": trace(reform=job["reform"])}, sys.stdout
)
"""

# The engine's own route for three inputs, which no record names. At start
# a simulation moves each one's values to its _before_lsr variable
# (policyengine_us/system.py), and each input's adds then sum that and a
# behavioral response. Without a reform the response returns 0 at once.
# Under one it reads its elasticities first. The runner passes a reform
# whenever a case has an override: policyengine's compile_reform gives none
# for no overrides, and each scalar override from 1 January of the year.
ENGINE_INPUT_ROUTE = frozenset(
    {
        "employment_income_before_lsr",
        "employment_income_behavioral_response",
        "labor_supply_behavioral_response",
        "self_employment_income_before_lsr",
        "self_employment_income_behavioral_response",
        "sstb_self_employment_income_before_lsr",
        "sstb_self_employment_income_behavioral_response",
    }
)
ENGINE_RESPONSE_PREFIX = "gov.simulation.labor_supply_responses."
# The engine reads gov.abolitions.<name> before it calculates each variable
# that has one (policyengine_core/simulations/simulation.py), and these are
# no formula's dependency.
ENGINE_GATE_PREFIX = "gov.abolitions."
TRACE_YEAR = "2026"


def trace_person(**changes):
    """Every input of one invented person, for the trace's one year."""
    row = INVENTED_INPUTS | {"is_tax_unit_head": False} | changes
    return {name: {TRACE_YEAR: value} for name, value in row.items()}


def trace_case(people, couples=()):
    """One invented household of ``people``, married as ``couples`` say."""
    names = list(people)
    paired = {name for pair in couples for name in pair}
    units = {
        f"couple_{i}": {"members": list(p)} for i, p in enumerate(couples)
    }
    units |= {
        f"single_{name}": {"members": [name]}
        for name in names
        if name not in paired
    }
    return {
        "people": people,
        "marital_units": units,
        "tax_units": {"unit": {"members": names}},
        "families": {"unit": {"members": names}},
        "spm_units": {"unit": {"members": names}},
        "households": {
            "unit": {"members": names, "state_name": {TRACE_YEAR: "TX"}}
        },
    }


# Invented households that between them reach every listed name: aged,
# disabled, blind and student claimants, a couple, deeming from a spouse and
# from parents, the living arrangements and a noncitizen.
INVENTED_TRACE_CASES = (
    trace_case(
        {
            "claimant": trace_person(
                is_tax_unit_head=True,
                social_security=9000,
                interest_income=400,
            )
        }
    ),
    trace_case(
        {
            "claimant": trace_person(
                age=40,
                is_tax_unit_head=True,
                meets_ssi_disability_criteria=True,
                employment_income=6000,
                self_employment_income=500,
            )
        }
    ),
    trace_case(
        {
            "first": trace_person(is_tax_unit_head=True, pension_income=3000),
            "second": trace_person(
                is_tax_unit_spouse=True, rental_income=1200
            ),
        },
        [("first", "second")],
    ),
    trace_case(
        {
            "claimant": trace_person(
                is_tax_unit_head=True, social_security=6000
            ),
            "spouse": trace_person(
                age=55, is_tax_unit_spouse=True, employment_income=14000
            ),
        },
        [("claimant", "spouse")],
    ),
    trace_case(
        {
            "parent": trace_person(
                age=38, is_tax_unit_head=True, employment_income=30000
            ),
            "other": trace_person(
                age=36, is_tax_unit_spouse=True, dividend_income=800
            ),
            "child": trace_person(
                age=9,
                meets_ssi_disability_criteria=True,
                child_support_received=900,
            ),
        },
        [("parent", "other")],
    ),
    trace_case(
        {
            "claimant": trace_person(
                is_tax_unit_head=True,
                ssi_lives_in_another_persons_household=True,
                ssi_receives_food_from_others=True,
                ssi_receives_shelter_from_others_in_household=True,
                ssi_shelter_support_value=2400,
                gi_cash_assistance=300,
            ),
            "host": trace_person(age=30, employment_income=45000),
        }
    ),
    trace_case(
        {
            "claimant": trace_person(
                age=50,
                is_blind=True,
                is_tax_unit_head=True,
                is_in_medicaid_facility=True,
                ssi_lives_in_medical_treatment_facility=True,
                ssi_medicaid_pays_majority_of_care=True,
                workers_compensation=500,
            )
        }
    ),
    trace_case(
        {
            "claimant": trace_person(
                age=20,
                is_tax_unit_head=True,
                meets_ssi_disability_criteria=True,
                is_full_time_college_student=True,
                employment_income=4000,
                bank_account_assets=900,
                stock_assets=800,
                bond_assets=700,
            )
        }
    ),
    trace_case(
        {
            "claimant": trace_person(
                is_tax_unit_head=True,
                immigration_status="LEGAL_PERMANENT_RESIDENT",
                ssi_qualifying_quarters_earnings=12,
                veterans_benefits=600,
                survivor_benefits=300,
                unemployment_compensation=200,
                alimony_income=100,
                financial_assistance=50,
                disability_benefits=70,
                retirement_distributions=90,
                sstb_self_employment_income=20,
            )
        }
    ),
)


def trace_gaps(inventory, trace, engine_prefixes=(ENGINE_GATE_PREFIX,)):
    """Every way the engine's trace and the inventory disagree, apart from
    parameters under ``engine_prefixes``, which only the engine reads."""
    records = {row["name"]: row for row in inventory["variables"]}
    inputs = {row["name"] for row in inventory["inputs"]}
    bypassed = inputs | set(inventory["explicit_formula_boundaries"])
    listed = set(records) | inputs
    read = set(trace["variables"])
    parameters = [row["name"] for row in inventory["parameters"]]
    return {
        "unlisted": sorted(read - listed - ENGINE_INPUT_ROUTE),
        # Round 12's N5: this can fail on a correct record, in the safe
        # direction, when the record lists a name the engine skips here: a
        # list member dated after 2026, since the record lists the union
        # over dates; a variable a formula reads under a defined_for mask
        # false for all nine households; a read made only outside January,
        # where MONTH targets run at 2026-01; and an input's dependency or a
        # body literal no code reads, which the inventory follows.
        "unread": sorted((listed | ENGINE_INPUT_ROUTE) - read),
        "edges": sorted(
            f"{parent} -> {child}"
            for parent, child in trace["edges"]
            if parent in records and parent not in bypassed
            # A variable can read itself at another period.
            and child != parent
            and child not in records[parent]["dependencies"]
        ),
        "parameters": sorted(
            name
            for name in trace["parameters"]
            if not name.startswith(engine_prefixes)
            and not any(
                name == parameter or name.startswith(f"{parameter}.")
                for parameter in parameters
            )
        ),
    }


def test_engine_trace_reads_only_what_the_inventory_lists():
    """Differential: the record's dependencies come from a static read of
    string literals, so a formula could reach a variable the record leaves
    out. Over invented households, with every input the contract names set
    and only the federal SSI variables calculated, the pinned engine's tracer
    reads exactly the listed variables and the named route for three inputs,
    and every edge, and every parameter the tracer records, is on the record.
    The tracer records only a formula's reads, and no parameter that adds or
    subtracts names, which test_inventory_attributes_match_the_pinned_engine
    compares instead. So it does under the reform of every override the
    runner admits, apart from the elasticity parameters the route then
    reads, which leave the response at 0; the reformed tree holds the
    reform's individual FBR."""
    python = Path(os.environ.get(PYTHON_ENV, str(DEFAULT_PYTHON))).expanduser()
    if not python.is_file():
        pytest.skip(f"SSI0 interpreter absent: {python}")
    inventory = json.loads(
        CONTRACT_PATH.with_name("inventory.json").read_text()
    )
    assert {row["name"] for row in inventory["inputs"]} == set(INVENTED_INPUTS)
    assert set(INVENTED_POLICY) == OVERRIDABLE_PARAMETERS
    assert not any(
        name.startswith(ENGINE_RESPONSE_PREFIX)
        for name in OVERRIDABLE_PARAMETERS
    )
    job = {
        "cases": INVENTED_TRACE_CASES,
        "year": TRACE_YEAR,
        "reform": {
            name: {f"{TRACE_YEAR}-01-01.2100-12-31": value}
            for name, value in INVENTED_POLICY.items()
        },
        "targets": [
            [
                row["name"],
                f"{TRACE_YEAR}-01" if row["period"] == "MONTH" else TRACE_YEAR,
            ]
            for row in inventory["variables"]
            if row["path"].startswith("variables/gov/ssa/ssi/")
        ],
    }
    # Round 12's L5: the targets are the federal SSI roots, and only those,
    # so the check that the engine reads every listed name can fail.
    assert len(job["targets"]) == inventory["federal_ssi_variable_count"]
    completed = subprocess.run(
        [str(python), "-I", "-c", TRACE_CHILD],
        input=json.dumps(job),
        capture_output=True,
        text=True,
        timeout=1800,
        check=True,
    )
    traces = json.loads(completed.stdout)
    trace = traces["plain"]
    no_gaps = {"unlisted": [], "unread": [], "edges": [], "parameters": []}
    assert trace_gaps(inventory, trace) == no_gaps
    assert trace["response"] == 0
    reformed = traces["reform"]
    assert (
        trace_gaps(
            inventory,
            reformed,
            (ENGINE_GATE_PREFIX, ENGINE_RESPONSE_PREFIX),
        )
        == no_gaps
    )
    assert reformed["response"] == 0
    # The reformed trace took the route's other branch.
    gated = trace_gaps(inventory, reformed)["parameters"]
    assert gated and all(
        name.startswith(ENGINE_RESPONSE_PREFIX) for name in gated
    )
    # Round 12's L2: the reform took, which an empty one would not; the
    # branch above shows only that a reform was passed.
    individual = INVENTED_POLICY["gov.ssa.ssi.amount.individual"]
    assert reformed["amounts"] == [individual]
    assert len(trace["amounts"]) == 1 and trace["amounts"] != [individual]

    # Controls: each kind of gap would show on these traces.
    target = "ssi_countable_income"
    without_record = copy.deepcopy(inventory)
    without_record["variables"] = [
        row for row in inventory["variables"] if row["name"] != target
    ]
    assert trace_gaps(without_record, trace)["unlisted"] == [target]
    without_edge = copy.deepcopy(inventory)
    record = next(
        row for row in without_edge["variables"] if row["name"] == target
    )
    assert record["dependencies"]
    dropped = record["dependencies"].pop()
    assert trace_gaps(without_edge, trace)["edges"] == [
        f"{target} -> {dropped}"
    ]
    unread = copy.deepcopy(inventory)
    unread["variables"].append(unread["variables"][0] | {"name": "invented"})
    assert trace_gaps(unread, trace)["unread"] == ["invented"]
    without_parameter = copy.deepcopy(inventory)
    without_parameter["parameters"] = []
    assert trace_gaps(without_parameter, trace)["parameters"]
