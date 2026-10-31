"""Public-interface oracle checks on invented households only.

POPULACE_DYNAMICS_PE_US_PYTHON_SSI0 deliberately contains the static oracle
tier substring without reusing the older bridge environment variable.
"""

import ast
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
    PYTHON_ENV,
    SSIRunner,
)

from .ssi_invented import invented_case
from .test_ssi_inventory import (
    ADMITTED_AGE_FORMS,
    ADMITTED_FORMS,
    ATTRIBUTE_ROUTES,
    CORE_DEFAULT_BINDINGS,
    CORE_DEFAULT_CHANGES,
    INVENTED_AGE_RECORD,
    INVENTED_EMPLOYMENT_INCOME,
    REFUSED_FORMS,
    core_default_module,
    invented_age_module,
    invented_enum_module,
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
# as the inventory records them.
ATTRIBUTE_CHILD = """
import enum, json, sys
import policyengine_us.model_api as model_api
from policyengine_core.entities import Entity
from policyengine_us import CountryTaxBenefitSystem

spellings = {}
for spelling, value in sorted(vars(model_api).items()):
    if isinstance(value, Entity):
        spellings.setdefault(("entity", value.key), []).append(spelling)
for spelling in ("DAY", "MONTH", "YEAR", "ETERNITY"):
    value = getattr(model_api, spelling)
    spellings.setdefault(("period", value), []).append(spelling)
system = CountryTaxBenefitSystem()
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
    for record, pinned in zip(records, observed, strict=True):
        assert pinned["name"] == record["name"]
        assert pinned["value_type"] == record["value_type"]
        assert pinned["default"] == record["default"]
        assert pinned["default_type"] == engine_default_type(record)
        # The model API binds each entity and period under one spelling,
        # the one the source names.
        assert pinned["entity"] == [record["entity"]]
        assert pinned["period"] == [record["period"]]


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
