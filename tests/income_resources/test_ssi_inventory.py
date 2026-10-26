"""Invented miniature source packages exercise the static SSI inventory.

No survey records or installed rules engines are used. The fixtures below
are Python source text invented solely to check extraction invariants.
"""

from __future__ import annotations

import ast
import builtins
import enum
import importlib.machinery
import importlib.util
import os
import py_compile
import subprocess
import symtable
import sys
import types
import typing
import warnings
from collections import defaultdict
from pathlib import Path

import pytest
import yaml
from hypothesis import assume, given, settings
from hypothesis import strategies as st

SCRIPT = (
    Path(__file__).parents[2] / "scripts/income_resources/inventory_ssi.py"
)
SPEC = importlib.util.spec_from_file_location("ssi_inventory_script", SCRIPT)
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


def invented_package(tmp_path: Path) -> Path:
    package = tmp_path / "policyengine_us"
    (package / "variables/gov/ssa/ssi").mkdir(parents=True)
    (package / "variables/input").mkdir(parents=True)
    (package / "variables/gov/states/ca").mkdir(parents=True)
    metadata = tmp_path / "policyengine_us-0.0.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Version: 0.0.0\n")
    for name, members in {
        inventory.SOURCE_LISTS[0]: ["employment_income"],
        inventory.SOURCE_LISTS[1]: ["pension_income"],
        inventory.SOURCE_LISTS[2]: ["bank_account_assets"],
    }.items():
        path = package / "parameters" / Path(*name.split("."))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_suffix(".yaml").write_text(
            "values:\n  1975-01-01:\n"
            + "".join(f"    - {member}\n" for member in members)
        )
    (package / "variables/input/invented_inputs.py").write_text(
        """class employment_income(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR

class pension_income(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR
    def formula(person, period, parameters):
        return person("hidden_pension_award_input", period)

class hidden_pension_award_input(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR

class bank_account_assets(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR

class invented_age(Variable):
    value_type = int
    entity = Person
    definition_period = YEAR
    default_value = 41
"""
    )
    (package / "variables/gov/ssa/ssi/invented_ssi.py").write_text(
        """class invented_ssi(Variable):
    value_type = float
    entity = Person
    definition_period = MONTH
    adds = "gov.ssa.ssi.income.sources.earned"

class invented_intermediate(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR
    def formula(person, period, parameters):
        return person("pension_income", period) + person("invented_age", period)
"""
    )
    source = package / "variables/input/invented_inputs.py"
    text = source.read_text()
    for node in ast.parse(text).body:
        if isinstance(node, ast.ClassDef):
            (source.parent / f"{node.name}.py").write_text(
                ast.get_source_segment(text, node) + "\n"
            )
    source.unlink()
    return package


def test_invented_inventory_is_complete_and_explicit(tmp_path):
    package = invented_package(tmp_path)
    result = inventory.inventory_release(package)
    assert result["federal_ssi_variable_count"] == 2
    assert {v["name"] for v in result["variables"]} == {
        "invented_ssi",
        "invented_intermediate",
        "employment_income",
        "pension_income",
        "invented_age",
    }
    inputs = {v["name"]: v for v in result["inputs"]}
    assert set(inputs) == {
        "employment_income",
        "pension_income",
        "invented_age",
    }
    assert inputs["employment_income"]["default"] == 0
    assert inputs["invented_age"]["default"] == 41
    assert inputs["invented_age"]["read_by"] == ["invented_intermediate"]
    assert inputs["pension_income"]["formula_names"] == ["formula"]
    assert result == inventory.inventory_release(package)


@settings(deadline=None, max_examples=12)
@given(st.integers(min_value=-1000, max_value=1000))
def test_explicit_defaults_survive_source_extraction(tmp_path_factory, value):
    package = invented_package(tmp_path_factory.mktemp("invented_inventory"))
    source = package / "variables/input/invented_age.py"
    source.write_text(
        source.read_text().replace(
            "default_value = 41", f"default_value = {value}"
        )
    )
    result = inventory.inventory_release(package)
    age = next(v for v in result["inputs"] if v["name"] == "invented_age")
    assert age["default"] == value


def test_comparison_names_missing_capabilities():
    invented_current = {
        "policyengine_us_version": "0.0.0",
        "variables": [{"name": "common", "sha256": "a"}],
        "parameters": [],
        "inputs": [],
    }
    invented_other = {
        "policyengine_us_version": "0.0.1",
        "variables": [
            {"name": "common", "sha256": "b"},
            {"name": "new_capability", "sha256": "c"},
        ],
        "parameters": [],
        "inputs": [],
    }
    result = inventory.compare_releases(invented_current, invented_other)
    assert result["missing_variables"] == ["new_capability"]
    assert result["source_changed_variables"] == ["common"]


def test_unresolved_formula_input_refuses_inventory(tmp_path):
    package = invented_package(tmp_path)
    path = package / "variables/gov/ssa/ssi/invented_ssi.py"
    path.write_text(
        path.read_text().replace('"invented_age"', '"absent_required_input"')
    )
    with pytest.raises(ValueError, match="Unresolved dependency"):
        inventory.inventory_release(package)


def test_historical_parameter_dates_remain_serializable():
    invented_parameter = "values:\n  0000-01-01: 0\n  1975-01-01: 20\n"
    result = yaml.load(invented_parameter, Loader=inventory.ParameterLoader)
    assert result == {"values": {"0000-01-01": 0, "1975-01-01": 20}}


def test_core_default_drift_refuses_inventory(tmp_path):
    package = tmp_path / "policyengine_us"
    config = tmp_path / "policyengine_core/variables/config.py"
    config.parent.mkdir(parents=True)
    invented_source = (
        'VALUE_TYPES = {bool: {"default": False}, int: {"default": 0}, '
        'float: {"default": 0}, str: {"default": ""}}\n'
    )
    config.write_text(invented_source)
    assert inventory.validate_core_defaults(package)["sha256"] == (
        inventory.sha256(config)
    )
    config.write_text(
        invented_source.replace(
            'float: {"default": 0}', 'float: {"default": 1}'
        )
    )
    with pytest.raises(ValueError, match="Core primitive defaults differ"):
        inventory.validate_core_defaults(package)


INVENTED_ENUM_INPUT = """class InventedStatus(Enum):
    INVENTED_FIRST = "Invented first"
    INVENTED_SECOND = "Invented second"


class invented_status(Variable):
    value_type = Enum
    entity = Person
    possible_values = {possible_values}
    default_value = {possible_values}.INVENTED_FIRST
    definition_period = YEAR
"""


def package_with_enum_input(tmp_path, possible_values):
    package = invented_package(tmp_path)
    (package / "variables/input/invented_status.py").write_text(
        INVENTED_ENUM_INPUT.format(possible_values=possible_values)
    )
    path = package / "variables/gov/ssa/ssi/invented_ssi.py"
    path.write_text(
        path.read_text().replace(
            'person("invented_age", period)',
            'person("invented_age", period) + '
            'person("invented_status", period)',
        )
    )
    return package


def test_enum_input_members_are_read_from_its_source(tmp_path):
    package = package_with_enum_input(tmp_path, "InventedStatus")
    result = inventory.inventory_release(package)
    status = next(
        v for v in result["inputs"] if v["name"] == "invented_status"
    )
    assert status["enum_members"] == ["INVENTED_FIRST", "INVENTED_SECOND"]
    assert status["default"] == "INVENTED_FIRST"
    numeric = next(v for v in result["inputs"] if v["name"] == "invented_age")
    assert "enum_members" not in numeric


def test_enum_input_without_readable_members_refuses_inventory(tmp_path):
    package = package_with_enum_input(tmp_path, "InventedImportedStatus")
    with pytest.raises(ValueError, match="Unresolved enum members"):
        inventory.inventory_release(package)


ENUM_NAMES = st.from_regex(r"Invented[A-Z][a-z]{1,10}", fullmatch=True)
MEMBER_NAMES = st.lists(
    st.from_regex(r"INVENTED_[A-Z]{1,8}", fullmatch=True),
    min_size=1,
    max_size=6,
    unique=True,
)


def invented_enum_module(
    class_source, name, default, forms=(), late_class=False
):
    """Source of a module holding an invented enum class and its variable.

    ``forms`` are ``(place, text)`` pairs inserted at the module's head,
    between the class and the variable, at its tail, or at the head or tail
    of the variable's body. ``late_class`` defines the class last.
    """
    placed = defaultdict(list)
    for place, form in forms:
        placed[place].append(form)
    body = "".join(
        "    " + line.replace("\n", "\n    ") + "\n"
        for line in placed["body_head"]
        + [
            "value_type = Enum",
            "entity = Person",
            f"possible_values = {name}",
            f"default_value = {name}.{default}",
            "definition_period = YEAR",
        ]
        + placed["body_tail"]
    )
    variable = "class invented_status(Variable):\n" + body
    middle = [class_source, *placed["between"], variable]
    if late_class:
        middle = middle[::-1]
    parts = [*placed["head"], *middle, *placed["tail"]]
    return "\n\n".join(part.rstrip("\n") for part in parts) + "\n"


def write_enum_module(package, source):
    """Write an invented enum module and make the invented SSI read it."""
    (package / "variables/input/invented_status.py").write_text(source)
    path = package / "variables/gov/ssa/ssi/invented_ssi.py"
    path.write_text(
        path.read_text().replace(
            'person("invented_age", period)',
            'person("invented_age", period) + '
            'person("invented_status", period)',
        )
    )


def write_enum_input(package, class_source, possible_values, default):
    """``default`` is the member name, or a dotted reference to a class."""
    module, _, member = default.rpartition(".")
    source = invented_enum_module(class_source, possible_values, member)
    if module:
        source = source.replace(
            f"default_value = {possible_values}.", f"default_value = {module}."
        )
    write_enum_module(package, source)


def enum_class(name, members, base="Enum"):
    body = "".join(
        f'    {member} = "{member.lower()}"\n' for member in members
    )
    return f"class {name}({base}):\n" + (body or "    pass\n")


def input_record(package):
    result = inventory.inventory_release(package)
    return next(v for v in result["inputs"] if v["name"] == "invented_status")


@settings(deadline=None, max_examples=25)
@given(name=ENUM_NAMES, members=MEMBER_NAMES)
def test_enum_members_round_trip_from_source(tmp_path_factory, name, members):
    package = invented_package(tmp_path_factory.mktemp("invented_enum"))
    write_enum_input(package, enum_class(name, members), name, members[0])
    assert input_record(package)["enum_members"] == members


@settings(deadline=None, max_examples=25)
@given(
    name=ENUM_NAMES,
    members=MEMBER_NAMES,
    defect=st.sampled_from(("absent", "empty", "not_an_enum")),
)
def test_enum_input_with_unreadable_members_refuses_inventory(
    tmp_path_factory, name, members, defect
):
    package = invented_package(tmp_path_factory.mktemp("invented_enum"))
    if defect == "absent":
        # possible_values names a class this module does not define.
        source = enum_class(name + "Other", members)
    elif defect == "empty":
        source = enum_class(name, [])
    else:
        source = enum_class(name, members, base="InventedBase")
    # The default names a member of the intended class, so the defect alone
    # refuses; an empty class has no member to name, so either check does.
    # The module rules refuse a class with another base first.
    write_enum_input(package, source, name, members[0])
    message = {
        "absent": "Unresolved enum members for invented_status",
        "empty": "Unresolved enum members for invented_status",
        "not_an_enum": "Unread module code in variables/input/invented_status",
    }[defect]
    with pytest.raises(ValueError, match=message):
        inventory.inventory_release(package)


# Statement kinds for invented Enum class bodies. The reader admits the
# first three; each of the rest must make it refuse.
ADMITTED_STATEMENTS = ("literal", "integer", "pass")
REFUSED_STATEMENTS = (
    "alias",
    "equal_value",
    "chained",
    "method",
    "decorated",
    "dunder",
    "annotated",
    "tuple",
    "private",
    "sunder",
    "call",
    "lambda",
    "boolean",
    "nested",
    "late_docstring",
    "duplicate",
    "mro",
)


def class_statement(kind, name, index, earlier):
    """One invented class-body line, and the member value it adds if any.

    ``earlier`` is the latest member's ``(name, value source)``, or None.
    Kinds that need an earlier member fall back to ``pass`` without one.
    """
    if kind == "literal":
        return f'{name} = "{name.lower()}"', f'"{name.lower()}"'
    if kind == "integer":
        return f"{name} = {index}", str(index)
    if kind in ("pass", "alias", "equal_value", "duplicate") and not earlier:
        return "pass", None
    lines = {
        "pass": "pass",
        "alias": f"{name} = {earlier[0]}" if earlier else "",
        "equal_value": f"{name} = {earlier[1]}" if earlier else "",
        "duplicate": f'{earlier[0]} = "invented repeat"' if earlier else "",
        "chained": f'{name} = {name}_TWIN = "{name.lower()}"',
        "method": f"def invented_method_{index}(self):\n    return {index}",
        "decorated": f"@str\ndef {name}(self):\n    return {index}",
        # Each later member's creation drops the first one.
        "dunder": (
            "def __init__(self, *args):\n"
            "    members = type(self)._member_map_\n"
            "    members.pop(next(iter(members), None), None)"
        ),
        "annotated": f'{name}: str = "{name.lower()}"',
        "tuple": f"{name}, {name}_PAIR = 1, 2",
        "private": f"_{name} = {index}",
        "sunder": '_ignore_ = ["INVENTED_IGNORED"]',
        "call": f"{name} = auto()",
        "lambda": f"{name} = lambda self: {index}",
        "boolean": f"{name} = True",
        "nested": f"class {name.title()}:\n    pass",
        "late_docstring": '"""Invented later string."""',
        "mro": 'mro = "invented mro"',
    }
    return lines[kind], None


@st.composite
def invented_enum_body(draw):
    """An invented Enum class, its first member, and whether it is refused."""
    names = draw(
        st.lists(
            st.from_regex(r"INVENTED_[A-Z]{1,6}", fullmatch=True),
            min_size=8,
            max_size=8,
            unique=True,
        )
    )
    # Admitted statements, with at most one refused kind among them, so
    # that about half the bodies are read and each refusal has one cause.
    kinds = draw(
        st.lists(st.sampled_from(ADMITTED_STATEMENTS), min_size=1, max_size=7)
    )
    refused_kind = draw(st.none() | st.sampled_from(REFUSED_STATEMENTS))
    if refused_kind:
        kinds.insert(draw(st.integers(0, len(kinds))), refused_kind)
    docstring = draw(st.booleans())
    lines = ['"""Invented enum."""'] if docstring else []
    members = []
    refused = False
    for index, kind in enumerate(kinds):
        line, value = class_statement(
            kind, names[index], index, (members[-1] if members else None)
        )
        if value is not None:
            members.append((names[index], value))
        # A string that opens the body is a docstring, not a refused form.
        if kind == "late_docstring":
            refused = refused or docstring or index > 0
        elif kind in REFUSED_STATEMENTS:
            refused = refused or line != "pass"
        lines.append(line)
    source = "class InventedEnum(Enum):\n" + "".join(
        "    " + line.replace("\n", "\n    ") + "\n" for line in lines
    )
    first = members[0][0] if members else "INVENTED_NONE"
    return source, first, refused or not members


# Module and variable forms: (place, text, observable). The reader admits
# the first six. Each of the rest must make it refuse; an observable one
# also changes what Python gives the variable. Some unobservable ones change
# what the engine gives it, which the harness's Variable cannot show.
ADMITTED_FORMS = {
    "model_api": ("head", "from policyengine_us.model_api import *", False),
    "member_read": ("tail", "INVENTED_CHOICE = {name}.{member}", False),
    "helper": (
        "tail",
        "def invented_helper():\n    return {name}.{member}",
        False,
    ),
    "formula": (
        "body_tail",
        "def formula(person, period, parameters):\n"
        "    return {name}.encode(person)",
        False,
    ),
    "dated_formula": (
        "body_tail",
        "def formula_2020(person, period, parameters):\n"
        "    return {name}.{member}",
        False,
    ),
    # A literal is not an identifier, whatever it spells.
    "underscore_text": ("body_tail", 'label = "_invented exec"', False),
    # A function shaped like Variable.set is harmless until a variable
    # binds it; see "chained_method".
    "set_function": (
        "between",
        "def invented_set(self, attributes, name, **options):\n"
        '    attributes.pop("set", None)\n'
        '    if name == "possible_values":\n'
        "        attributes.pop(name)\n"
        "        return InventedOtherEnum\n"
        '    if name == "default_value":\n'
        "        attributes.pop(name)\n"
        "        return InventedOtherEnum.INVENTED_OTHER\n"
        "    return Variable.set(self, attributes, name, **options)",
        False,
    ),
}
REFUSED_FORMS = {
    "rebind": ("between", "{name} = InventedOtherEnum", True),
    "walrus": (
        "between",
        "INVENTED_SPARE = ({name} := InventedOtherEnum)",
        True,
    ),
    "conditional_class": (
        "between",
        'if True:\n    class {name}(Enum):\n        INVENTED_OTHER = "other"',
        True,
    ),
    "try_import": (
        "between",
        "try:\n    from invented_module import {name}\n"
        "except ImportError:\n    pass",
        True,
    ),
    "plain_import": ("between", "from invented_module import {name}", True),
    "aliased_import": (
        "between",
        "from invented_module import InventedOtherEnum as {name}",
        True,
    ),
    "guarded_import": (
        "between",
        "if True:\n    from invented_module import {name}",
        True,
    ),
    "star_import": ("between", "from invented_module import *", True),
    "late_model_api": (
        "between",
        "from policyengine_us.model_api import *",
        False,
    ),
    "function_global": (
        "between",
        "def invented_rebind():\n    global {name}\n"
        "    {name} = InventedOtherEnum\n\n\ninvented_rebind()",
        True,
    ),
    "class_global": (
        "between",
        "class InventedShadow:\n    global {name}\n"
        "    {name} = InventedOtherEnum",
        True,
    ),
    "match_capture": (
        "between",
        "match InventedOtherEnum:\n    case {name}:\n        pass",
        True,
    ),
    "mapping_rest": (
        "between",
        'match {{"key": InventedOtherEnum}}:\n'
        "    case {{**{name}}}:\n        pass",
        True,
    ),
    "match_star": (
        "between",
        "match [InventedOtherEnum]:\n    case [*{name}]:\n        pass",
        True,
    ),
    "parameter": ("tail", "def invented_helper({name}):\n    pass", False),
    "for_target": (
        "between",
        "for {name} in (InventedOtherEnum,):\n    pass",
        True,
    ),
    "except_name": (
        "between",
        "try:\n    raise ValueError\nexcept ValueError as {name}:\n    pass",
        True,
    ),
    "delete": ("tail", "del {name}", False),
    "alias_read": ("between", "InventedAlias = {name}", False),
    # Outside its body the class is read only as a member or encode.
    "class_method_read": ("tail", "INVENTED_ORDER = {name}.mro()", False),
    "member_pop": ("between", '{name}._member_map_.pop("{member}")', True),
    "globals": (
        "between",
        'globals()["{name}"] = InventedOtherEnum',
        True,
    ),
    "exec": ("between", 'exec("{name} = InventedOtherEnum")', True),
    "function_globals": (
        "between",
        '(lambda: None).__globals__["{name}"] = InventedOtherEnum',
        True,
    ),
    "frame_globals": (
        "between",
        "(item for item in ()).gi_frame"
        '.f_globals["{name}"] = InventedOtherEnum',
        True,
    ),
    "attribute_store": (
        "between",
        "InventedOtherBase.{name} = InventedOtherEnum",
        False,
    ),
    "enum_bound": ("head", "Enum = InventedOtherBase", False),
    "body_rebind": ("body_head", "{name} = InventedOtherEnum", True),
    "body_import": (
        "body_head",
        "from invented_module import InventedOtherEnum as {name}",
        True,
    ),
    "annotated_twice": (
        "body_tail",
        "possible_values: type = InventedOtherEnum",
        True,
    ),
    "body_walrus": (
        "body_tail",
        "invented_spare = (possible_values := InventedOtherEnum)",
        True,
    ),
    "default_twice": (
        "body_tail",
        "default_value = InventedOtherEnum.INVENTED_OTHER",
        True,
    ),
    "value_type_twice": ("body_tail", "value_type = float", False),
    "global_declared": ("body_head", "global possible_values", True),
    "variable_attribute_store": (
        "tail",
        "invented_status.possible_values = InventedOtherEnum",
        True,
    ),
    "variable_rebind": ("tail", "invented_status = None", True),
    # Attribute names held as strings in the tree: pattern keywords and
    # definitions.
    "pattern_keyword": (
        "between",
        "match (lambda: None):\n"
        "    case object(__globals__=invented_globals):\n"
        '        invented_globals["{name}"] = InventedOtherEnum',
        True,
    ),
    "pattern_frame": (
        "between",
        "try:\n    raise ValueError\n"
        "except ValueError as invented_error:\n"
        "    match invented_error:\n"
        "        case object(__traceback__=object(\n"
        "            tb_frame=object(f_locals=invented_names)\n"
        "        )):\n"
        '            invented_names["{name}"] = InventedOtherEnum',
        True,
    ),
    "module_getattr": (
        "tail",
        "def __getattr__(name):\n    return InventedOtherEnum",
        False,
    ),
    # The variable's base is read by its spelling, and the engine reads the
    # variable's attributes through Variable.set.
    "variable_bound": ("head", "Variable = InventedOtherBase", True),
    "variable_subclass": (
        "between",
        "class Variable(Variable, metaclass=InventedVariableMeta):\n    pass",
        True,
    ),
    "variable_set": (
        "between",
        "class Variable(Variable):\n"
        "    def set(self, attributes, name, **options):\n"
        "        return InventedOtherEnum",
        False,
    ),
    # The engine's loader takes this one silently, since it also drops its
    # own name from the attributes the engine checks; see test_ssi_engine.
    "variable_method": (
        "body_tail",
        "def set(self, attributes, name, **options):\n"
        '    attributes.pop("set", None)\n'
        '    if name == "possible_values":\n'
        "        attributes.pop(name)\n"
        "        return InventedOtherEnum\n"
        '    if name == "default_value":\n'
        "        attributes.pop(name)\n"
        "        return InventedOtherEnum.INVENTED_OTHER\n"
        "    return super().set(attributes, name, **options)",
        False,
    ),
    "assigned_method": ("body_tail", "set = InventedOtherBase", False),
    "unknown_attribute": ("body_tail", 'invented_note = "note"', False),
    # A chained assignment binds every target, so an engine attribute can
    # carry another name with it, such as set.
    "chained_attribute": (
        "body_tail",
        'label = invented_note = "note"',
        False,
    ),
    "chained_method": ("body_tail", "reference = set = invented_set", False),
    # A decorator runs code as the class body runs, and a string after the
    # docstring is no attribute; the reader refuses even harmless ones.
    "decorated_formula": (
        "body_tail",
        "@staticmethod\ndef formula(person, period, parameters):\n"
        "    return {name}.{member}",
        False,
    ),
    "late_body_text": ("body_tail", '"""Invented note."""', False),
    "base_store": ("tail", "Variable.set = None", False),
    # A store through a member changes its encoding index, not membership.
    "member_store": ("tail", "{name}.{member}.index = 0", False),
    "member_attribute_delete": ("tail", "del {name}.{member}.index", False),
    # The identifier scan reads keyword and parameter names too.
    "keyword_underscore": (
        "tail",
        "INVENTED_SPARE = dict(_invented=1)",
        False,
    ),
    "parameter_underscore": (
        "tail",
        "def invented_helper(_invented):\n    pass",
        False,
    ),
    "member_alias_store": (
        "tail",
        "INVENTED_SPARE = {name}.{member}\nINVENTED_SPARE.index = 0",
        False,
    ),
    # Only the model API's absolute star import may come before the class.
    "helper_star_import": ("head", "from invented_helpers import *", True),
    "relative_model_api": (
        "head",
        "from .policyengine_us.model_api import *",
        False,
    ),
}


class InventedOtherEnum(enum.Enum):
    INVENTED_OTHER = "other"


class InventedOtherBase(enum.Enum):
    """An invented Enum base that is not the model API's."""


class InventedVariableMeta(type):
    """Answers a variable's enum attributes ahead of the variable's body."""

    possible_values = property(lambda cls: InventedOtherEnum)
    default_value = property(lambda cls: InventedOtherEnum.INVENTED_OTHER)


def invented_import(name, *args, **kwargs):
    """Stand-in imports: the model API, a module that shadows the class, and
    one that shadows Variable."""
    module = types.ModuleType(name)
    if name == inventory.MODEL_API:
        vars(module).update(
            Enum=enum.Enum,
            Variable=type("Variable", (), {}),
            Person=None,
            YEAR=None,
        )
    elif name == "invented_module":
        module.InventedEnum = module.InventedOtherEnum = InventedOtherEnum
    elif name == "invented_helpers":
        module.Variable = InventedVariableMeta("Variable", (), {})
    else:
        raise ImportError(name)
    return module


def python_enum_members(source):
    """``(members, canonical names, default)`` Python gives the variable.

    None if the module fails, or the variable's class or default is not an
    Enum and one of its members.
    """
    namespace = {
        "__builtins__": vars(builtins) | {"__import__": invented_import},
        "Enum": enum.Enum,
        "Variable": type("Variable", (), {}),
        "Person": None,
        "YEAR": None,
        "auto": enum.auto,
        "InventedOtherEnum": InventedOtherEnum,
        "InventedOtherBase": InventedOtherBase,
        "InventedVariableMeta": InventedVariableMeta,
    }
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            exec(source, namespace)  # noqa: S102 - invented source only
        variable = namespace["invented_status"]
        cls = variable.possible_values
        default = variable.default_value
        if not (isinstance(cls, enum.EnumMeta) and isinstance(default, cls)):
            return None
        return list(cls.__members__), [item.name for item in cls], default.name
    except Exception:
        return None


def read_members(source):
    """The reader's members for the invented variable in a module source."""
    tree = ast.parse(source)
    variable = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "invented_status"
    )
    return inventory.enum_members(tree, variable)


@st.composite
def invented_enum_source(draw):
    """An invented module, and whether a refused form occurs in it."""
    class_source, member, refused = draw(invented_enum_body())
    chosen = draw(
        st.lists(st.sampled_from(sorted(ADMITTED_FORMS)), unique=True)
    )
    refused_form = draw(st.none() | st.sampled_from(sorted(REFUSED_FORMS)))
    if refused_form:
        chosen.insert(draw(st.integers(0, len(chosen))), refused_form)
    late_class = draw(st.sampled_from((False, False, False, True)))
    forms = [
        (place, text.format(name="InventedEnum", member=member))
        for kind in chosen
        for place, text, _ in [(ADMITTED_FORMS | REFUSED_FORMS)[kind]]
    ]
    source = invented_enum_module(
        class_source, "InventedEnum", member, forms, late_class
    )
    refused = refused or late_class or bool(set(chosen) & set(REFUSED_FORMS))
    return source, member, refused


@settings(deadline=None, max_examples=400)
@given(invented_enum_source())
def test_static_enum_members_agree_with_python_enum(generated):
    """Differential: the static reader against the module as Python runs it."""
    source, member, refused = generated
    read = read_members(source)
    python = python_enum_members(source)
    if read is not None:
        # Whatever the reader admits, Python defines identically, with no
        # alias that the engine's encode would refuse, and the same default.
        assert python == (read, read, member)
    if refused:
        assert read is None
    else:
        # The admitted forms, with at least one member, are read.
        assert python is not None
        assert read == python[0]


INVENTED_ENUM_CLASS = 'class InventedEnum(Enum):\n    INVENTED_ONE = "one"\n'
INVENTED_ENUM_MODULE = invented_enum_module(
    INVENTED_ENUM_CLASS, "InventedEnum", "INVENTED_ONE"
)


def test_invented_enum_module_is_read():
    assert read_members(INVENTED_ENUM_MODULE) == ["INVENTED_ONE"]
    assert python_enum_members(INVENTED_ENUM_MODULE) == (
        ["INVENTED_ONE"],
        ["INVENTED_ONE"],
        "INVENTED_ONE",
    )


@pytest.mark.parametrize("kind", sorted(REFUSED_FORMS))
def test_forms_that_can_change_the_class_are_unread(kind):
    place, text, observable = REFUSED_FORMS[kind]
    form = text.format(name="InventedEnum", member="INVENTED_ONE")
    source = invented_enum_module(
        INVENTED_ENUM_CLASS, "InventedEnum", "INVENTED_ONE", [(place, form)]
    )
    assert read_members(source) is None
    if observable:
        # The form is not only refused: Python gives a different answer.
        assert python_enum_members(source) != python_enum_members(
            INVENTED_ENUM_MODULE
        )


INVENTED_NAME = "InventedName"
# The constructs that bind a name under the language reference's "Naming and
# binding", with global declarations, then forms that only read it. Star
# imports, which bind every public name of a module, are refused outright.
BINDING_FORMS = (
    "{n} = 1",
    "{n} += 1",
    "{n}: int",
    "{n}: int = 1",
    "x = ({n} := 1)",
    "for {n} in x:\n    pass",
    "with x as {n}:\n    pass",
    "with x as ({n}, y):\n    pass",
    "try:\n    pass\nexcept E as {n}:\n    pass",
    "import {n}",
    "import {n}.sub",
    "import m as {n}",
    "from m import {n}",
    "from m import x as {n}",
    "def {n}():\n    pass",
    "async def {n}():\n    pass",
    "class {n}:\n    pass",
    "def f({n}):\n    pass",
    "def f(*{n}):\n    pass",
    "def f(**{n}):\n    pass",
    "def f(*, {n}):\n    pass",
    "lambda {n}: 0",
    "[{n} for {n} in x]",
    "match x:\n    case {n}:\n        pass",
    "match x:\n    case [*{n}]:\n        pass",
    "match x:\n    case {{**{n}}}:\n        pass",
    "match x:\n    case [y] as {n}:\n        pass",
    "del {n}",
    "global {n}",
)
READING_FORMS = (
    "print({n})",
    "{n}.attr",
    "{n}[0] = 1",
    "x = {n}",
    "import m.{n}",
    "from m import {n} as y",
    "def f():\n    return {n}",
    "f(**{n})",
)


def symtable_binds(source, name):
    """Whether CPython's symbol table binds or declares ``name`` anywhere."""
    pending = [symtable.symtable(source, "<invented>", "exec")]
    while pending:
        table = pending.pop()
        pending.extend(table.get_children())
        if name in table.get_identifiers():
            symbol = table.lookup(name)
            if (
                symbol.is_assigned()
                or symbol.is_imported()
                or symbol.is_parameter()
                or symbol.is_declared_global()
            ):
                return True
    return False


@pytest.mark.parametrize("form", BINDING_FORMS + READING_FORMS)
def test_binding_sites_agree_with_the_symbol_table(form):
    """Differential: binding sites against CPython's own scope analysis."""
    text = form.format(n=INVENTED_NAME)
    nested = "    " + text.replace("\n", "\n    ")
    for source in (text, "def g():\n" + nested, "class G:\n" + nested):
        expected = form in BINDING_FORMS
        assert symtable_binds(source, INVENTED_NAME) is expected
        sites = inventory.binding_sites(ast.parse(source), INVENTED_NAME)
        assert bool(sites) is expected


@pytest.mark.parametrize(
    "form",
    (
        pytest.param(
            "try:\n    pass\nexcept* E as {n}:\n    pass",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 11), reason="except* syntax"
            ),
        ),
        *(
            pytest.param(
                form,
                marks=pytest.mark.skipif(
                    sys.version_info < (3, 12), reason="PEP 695 syntax"
                ),
            )
            for form in (
                "type {n} = int",
                "def f[{n}]():\n    pass",
                "class C[*{n}]:\n    pass",
                "def f[**{n}]():\n    pass",
            )
        ),
    ),
)
def test_newer_binding_syntax_gives_binding_sites(form):
    source = form.format(n=INVENTED_NAME)
    assert symtable_binds(source, INVENTED_NAME)
    assert inventory.binding_sites(ast.parse(source), INVENTED_NAME)


def test_attribute_stores_count_as_binding_sites():
    # The symbol table does not track them, but one module can rebind
    # another's global through one, so they count.
    for form in ("x.{n} = 1", "del x.{n}", "x.{n} += 1"):
        source = form.format(n=INVENTED_NAME)
        assert not symtable_binds(source, INVENTED_NAME)
        assert inventory.binding_sites(ast.parse(source), INVENTED_NAME)


def test_enum_class_defined_after_its_variable_is_unread():
    source = invented_enum_module(
        INVENTED_ENUM_CLASS, "InventedEnum", "INVENTED_ONE", late_class=True
    )
    assert python_enum_members(source) is None
    assert read_members(source) is None


def test_enum_class_nested_in_a_block_is_unread():
    # Its one binding is not a top-level statement, so the reader does not
    # place it before the variable.
    nested = "if True:\n    " + INVENTED_ENUM_CLASS.replace("\n", "\n    ")
    source = INVENTED_ENUM_MODULE.replace(INVENTED_ENUM_CLASS, nested)
    assert python_enum_members(source) is not None
    assert read_members(source) is None


def test_variable_of_another_value_type_is_unread():
    # The engine ignores possible_values unless value_type is Enum.
    source = INVENTED_ENUM_MODULE.replace(
        "value_type = Enum", "value_type = int"
    )
    assert read_members(source) is None


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 syntax")
@pytest.mark.parametrize(
    "form",
    (
        "class InventedEnum[InventedType](Enum):",
        "def invented_helper[InventedEnum]():\n    pass\n\n\n"
        "class InventedEnum(Enum):",
    ),
)
def test_type_parameters_are_unread(form):
    source = INVENTED_ENUM_MODULE.replace("class InventedEnum(Enum):", form)
    assert read_members(source) is None


@pytest.mark.parametrize("kind", sorted(REFUSED_STATEMENTS))
def test_class_statements_that_can_change_membership_are_unread(kind):
    line, _ = class_statement(
        kind, "INVENTED_TWO", 1, ("INVENTED_ONE", '"one"')
    )
    source = invented_enum_module(
        INVENTED_ENUM_CLASS + "    " + line.replace("\n", "\n    ") + "\n",
        "InventedEnum",
        "INVENTED_ONE",
    )
    assert read_members(source) is None


def test_methods_that_change_membership_are_refused():
    # A reader that skipped methods as non-members would give these classes
    # INVENTED_ONE and INVENTED_LAST. A decorator makes the method a member,
    # and the __init__ hook drops members as later ones are created.
    for kind in ("decorated", "dunder"):
        line, _ = class_statement(
            kind, "INVENTED_MID", 1, ("INVENTED_ONE", '"one"')
        )
        source = (
            INVENTED_ENUM_CLASS
            + "    "
            + line.replace("\n", "\n    ")
            + '\n    INVENTED_LAST = "last"\n'
        )
        namespace = {"Enum": enum.Enum}
        exec(source, namespace)  # noqa: S102 - invented source only
        members = list(namespace["InventedEnum"].__members__)
        assert members != ["INVENTED_ONE", "INVENTED_LAST"]
        module = invented_enum_module(source, "InventedEnum", "INVENTED_ONE")
        assert read_members(module) is None


@pytest.mark.parametrize(
    "header",
    (
        "class InventedEnum(Enum, InventedMixin):",
        "class InventedEnum(InventedBase):",
        "class InventedEnum(Enum, metaclass=InventedMeta):",
        "@invented_decorator\nclass InventedEnum(Enum):",
    ),
)
def test_enum_class_with_other_bases_or_decorators_is_unread(header):
    source = INVENTED_ENUM_MODULE.replace("class InventedEnum(Enum):", header)
    assert read_members(source) is None


@pytest.mark.parametrize(
    "header",
    (
        "class invented_status(Variable, InventedMixin):",
        "class invented_status(InventedBase):",
        "class invented_status(Variable, metaclass=InventedMeta):",
        "@invented_decorator\nclass invented_status(Variable):",
    ),
)
def test_enum_variable_with_other_bases_or_decorators_is_unread(header):
    # A decorator or another base can replace or change the variable that
    # the engine loads.
    source = INVENTED_ENUM_MODULE.replace(
        "class invented_status(Variable):", header
    )
    assert read_members(source) is None


def test_enum_member_named_mro_is_unread():
    # Python's Enum refuses this name, so the reader must not admit it.
    source = INVENTED_ENUM_MODULE.replace(
        '    INVENTED_ONE = "one"\n',
        '    INVENTED_ONE = "one"\n    mro = "x"\n',
    )
    assert python_enum_members(source) is None
    assert read_members(source) is None


@pytest.mark.parametrize(
    ("kind", "message"),
    (
        ("body_rebind", "Unread variable invented_status"),
        ("body_import", "Unread module code"),
        ("annotated_twice", "Unread variable invented_status"),
        ("walrus", "Unresolved enum members for invented_status"),
        ("try_import", "Unread module code"),
    ),
)
def test_enum_input_bound_outside_a_plain_read_refuses_inventory(
    tmp_path, kind, message
):
    # The five forms that put one member list in the input record while the
    # variable held another, end to end through the inventory. Each refuses
    # by the first rule it breaks.
    place, text, _ = REFUSED_FORMS[kind]
    form = text.format(name="InventedStatus", member="INVENTED_FIRST")
    source = invented_enum_module(
        enum_class("InventedStatus", ["INVENTED_FIRST", "INVENTED_SECOND"]),
        "InventedStatus",
        "INVENTED_FIRST",
        [(place, form)],
    )
    package = invented_package(tmp_path / "control")
    write_enum_module(package, source.replace(form, ""))
    assert input_record(package)["enum_members"] == [
        "INVENTED_FIRST",
        "INVENTED_SECOND",
    ]
    package = invented_package(tmp_path / "form")
    write_enum_module(package, source)
    with pytest.raises(ValueError, match=message):
        inventory.inventory_release(package)


@settings(deadline=None, max_examples=25)
@given(
    name=ENUM_NAMES,
    members=MEMBER_NAMES,
    foreign=st.booleans(),
)
def test_enum_default_outside_its_members_refuses_inventory(
    tmp_path_factory, name, members, foreign
):
    package = invented_package(tmp_path_factory.mktemp("invented_enum"))
    # Either a name the class lacks, or a member of another class.
    default = f"{name}Other.{members[0]}" if foreign else "INVENTED_ABSENT_"
    write_enum_input(package, enum_class(name, members), name, default)
    with pytest.raises(ValueError, match="Unresolved enum members"):
        inventory.inventory_release(package)


def python_variable(source):
    """The invented variable class Python defines from a module source.

    Bytes are decoded as Python decodes a source file, cookie included.
    """
    namespace = {
        "Enum": enum.Enum,
        "Variable": type("Variable", (), {}),
        "Person": None,
        "YEAR": None,
        # A name a star import of the model API could bind to Enum.
        "InventedModelApiEnum": enum.Enum,
    }
    code = compile(source, "<invented>", "exec")
    exec(code, namespace)  # noqa: S102 - invented source only
    return namespace["invented_status"]


# value_type bindings that leave Enum in the class namespace, where the
# engine reads it, though no single plain assignment says so, with the
# refusal each meets first.
VALUE_TYPE_FORMS = {
    "annotated": ("value_type: type = Enum", [], "Unread variable"),
    "alias": (
        "value_type = InventedEnumType",
        [("head", "InventedEnumType = Enum")],
        "Unresolved value_type",
    ),
    "rebound": (
        "value_type = float",
        [("body_tail", "value_type: type = Enum")],
        "Unread variable",
    ),
    "attribute_store": (
        "value_type = float",
        [("tail", "invented_status.value_type = Enum")],
        "Unread module code",
    ),
    # A name the module never binds, neither a primitive type nor Enum.
    "model_api_alias": (
        "value_type = InventedModelApiEnum",
        [],
        "Unresolved value_type",
    ),
} | {
    # A primitive type is read by its spelling, so the module may not
    # rebind it.
    f"{primitive}_rebound": (
        f"value_type = {primitive}",
        [("head", f"{primitive} = Enum")],
        "Unresolved value_type",
    )
    for primitive in inventory.TYPE_DEFAULTS
}


@pytest.mark.parametrize("kind", sorted(VALUE_TYPE_FORMS))
def test_value_type_outside_one_plain_assignment_refuses_inventory(
    tmp_path, kind
):
    line, forms, message = VALUE_TYPE_FORMS[kind]
    source = invented_enum_module(
        enum_class("InventedStatus", ["INVENTED_FIRST", "INVENTED_SECOND"]),
        "InventedStatus",
        "INVENTED_FIRST",
        forms,
    ).replace("    value_type = Enum\n", f"    {line}\n")
    assert vars(python_variable(source))["value_type"] is enum.Enum
    package = invented_package(tmp_path)
    write_enum_module(package, source)
    with pytest.raises(ValueError, match=f"{message} .*invented_status"):
        inventory.inventory_release(package)


def test_source_is_decoded_as_python_decodes_it(tmp_path):
    # Under this cookie "+AAo-" is a newline, so Python reads a second
    # member where a UTF-8 read sees a comment.
    source = "# coding: utf-7\n" + invented_enum_module(
        "class InventedStatus(Enum):\n"
        '    INVENTED_FIRST = "first"\n'
        '    # +AAo-    INVENTED_SECOND = "second"\n',
        "InventedStatus",
        "INVENTED_FIRST",
    )
    raw = source.encode("ascii")
    members = ["INVENTED_FIRST", "INVENTED_SECOND"]
    assert list(python_variable(raw).possible_values.__members__) == members
    assert read_members(raw.decode("utf-8")) == members[:1]
    assert read_members(raw) == members
    package = invented_package(tmp_path)
    write_enum_module(package, source)
    assert input_record(package)["enum_members"] == members


def spelling_binding(form, name):
    """A module-level binding of ``name``, and the refusal it meets first.

    An aliased import takes the one policyengine_core name the module rules
    admit, and a class subclasses Enum. A plain import, an import of any
    other name and an augmented assignment are refused before any spelling
    is read; the message is None when the spelling rule refuses first.
    """
    text = (
        form.format(n=name)
        .replace(
            "from m import x as",
            "from policyengine_core.simulations import Simulation as",
        )
        .replace("from m import", "from policyengine_core.simulations import")
    )
    if text.startswith("class "):
        text = text.replace(":", "(Enum):", 1)
    module_rule = (
        text.startswith("import ")
        or (text.startswith("from ") and " as " not in text)
        or "+=" in text
    )
    return text, "Unread module code" if module_rule else None


@pytest.mark.parametrize("form", BINDING_FORMS)
@pytest.mark.parametrize(
    ("attribute", "name"),
    [
        ("value_type", "float"),
        ("entity", "Person"),
        ("definition_period", "YEAR"),
    ],
)
def test_spelled_name_bound_in_its_module_refuses_inventory(
    tmp_path, attribute, name, form
):
    """The record names each by its spelling, so every binding form of the
    spelled name refuses, in the variable's own module."""
    binding, message = spelling_binding(form, name)
    package = invented_package(tmp_path)
    path = package / "variables/input/employment_income.py"
    assert f"{attribute} = {name}\n" in path.read_text()
    path.write_text(f"{binding}\n\n\n" + path.read_text())
    expected = message or f"Unresolved {attribute} for employment_income"
    with pytest.raises(ValueError, match=expected):
        inventory.inventory_release(package)


INVENTED_AGE_MODULE = """from policyengine_us.model_api import *


class invented_age(Variable):
    value_type = int
    entity = Person
    definition_period = YEAR
    default_value = 41
    label = "Invented age"
"""
INVENTED_SET_OVERRIDE = (
    "def set(self, attributes, name, **options):\n"
    '    attributes.pop("set", None)\n'
    '    if name == "value_type":\n'
    "        attributes.pop(name)\n"
    "        return {value_type}\n"
    "    return super().set(attributes, name, **options)"
)
# Routes by which a variable's value_type, entity, period or default can
# differ from the plain assignment's spelling: (forms, the refusal each
# meets first, and whether Python's class namespace shows the change). A
# form is a (place, text) pair, inserted at the module's head or tail or at
# the variable body's tail, or an (old, new) replacement. Each changes what
# the pinned engine loads; see test_ssi_engine.
ATTRIBUTE_ROUTES = {
    # The engine reads every attribute through the variable's own set.
    "set_override": (
        [("body_tail", INVENTED_SET_OVERRIDE.format(value_type="float"))],
        "Unread variable invented_age",
        False,
    ),
    "set_override_enum": (
        [
            (
                "head",
                "class InventedStatus(Enum):\n"
                '    INVENTED_FIRST = "first"\n'
                '    INVENTED_SECOND = "second"',
            ),
            (
                "body_tail",
                "def set(self, attributes, name, **options):\n"
                '    attributes.pop("set", None)\n'
                '    if name == "value_type":\n'
                "        attributes.pop(name)\n"
                "        return Enum\n"
                '    if name == "possible_values":\n'
                "        return InventedStatus\n"
                '    if name == "default_value":\n'
                "        attributes.pop(name)\n"
                "        return InventedStatus.INVENTED_FIRST\n"
                "    return super().set(attributes, name, **options)",
            ),
        ],
        "Unread variable invented_age",
        False,
    ),
    "setattr": (
        [("tail", 'setattr(invented_age, "value_type", float)')],
        "Unread module code",
        True,
    ),
    "globals_type": (
        [("head", 'globals()["int"] = float')],
        "Unread module code",
        True,
    ),
    # Restored at the tail, so the change reaches only this module's class
    # body and not the engine's own code.
    "builtins_type": (
        [
            ("head", 'invented_int = int\n__builtins__["int"] = float'),
            ("tail", '__builtins__["int"] = invented_int'),
        ],
        "Unread module code",
        True,
    ),
    "match_type": (
        [("head", "match float:\n    case int:\n        pass")],
        "Unresolved value_type for invented_age",
        True,
    ),
    "annotated_entity": (
        [("body_tail", "entity: object = TaxUnit")],
        "Unread variable invented_age",
        True,
    ),
    "annotated_period": (
        [("body_tail", "definition_period: str = MONTH")],
        "Unread variable invented_age",
        True,
    ),
    "annotated_default": (
        [("body_tail", "default_value: int = 7")],
        "Unread variable invented_age",
        True,
    ),
    # A class body runs as its module is imported, so the import-time rule
    # refuses the in-place assignment before the attribute rules read it.
    "augmented_default": (
        [("body_tail", "default_value += 1")],
        "Unread module code in variables/input/invented_age.py",
        True,
    ),
    "second_default": (
        [("body_tail", "default_value = 7")],
        "Unresolved default_value for invented_age",
        True,
    ),
    "tuple_attributes": (
        [("body_tail", "entity, definition_period = TaxUnit, MONTH")],
        "Unread variable invented_age",
        True,
    ),
    "entity_store": (
        [("tail", "invented_age.entity = TaxUnit")],
        "Unread module code",
        True,
    ),
    "default_store": (
        [("tail", "invented_age.default_value = 7")],
        "Unread module code",
        True,
    ),
    "entity_item": (
        [("entity = Person", "entity = entities[3]")],
        "Unresolved entity for invented_age",
        True,
    ),
    "globals_entity": (
        [("head", 'globals()["Person"] = TaxUnit')],
        "Unread module code",
        True,
    ),
    "match_entity": (
        [("head", "match TaxUnit:\n    case Person:\n        pass")],
        "Unresolved entity for invented_age",
        True,
    ),
    "match_period": (
        [("head", "match MONTH:\n    case YEAR:\n        pass")],
        "Unresolved definition_period for invented_age",
        True,
    ),
    # The engine takes a bool as an int.
    "bool_default": (
        [("default_value = 41", "default_value = True")],
        "Unresolved default for invented_age",
        True,
    ),
}


def invented_age_module(forms=()):
    """The invented age module with ``forms`` placed as ATTRIBUTE_ROUTES
    places them."""
    source = INVENTED_AGE_MODULE
    placed = defaultdict(list)
    for place, text in forms:
        if place in ("head", "tail", "body_tail"):
            placed[place].append(text)
        else:
            assert source.count(place) == 1
            source = source.replace(place, text)
    head, _, rest = source.partition("\n\n\nclass ")
    body = "".join(
        "    " + text.replace("\n", "\n    ") + "\n"
        for text in placed["body_tail"]
    )
    parts = [head, *placed["head"], "class " + rest + body, *placed["tail"]]
    return "\n\n\n".join(part.rstrip("\n") for part in parts) + "\n"


class InventedEntity:
    """A stand-in for one of the model API's entities."""

    def __init__(self, name):
        self.name = name


INVENTED_ENTITIES = [
    InventedEntity(name)
    for name in (
        "Household",
        "SPMUnit",
        "Family",
        "TaxUnit",
        "MaritalUnit",
        "Person",
    )
]
INVENTED_MODEL_API = {
    "Enum": enum.Enum,
    "Variable": type("Variable", (), {}),
    "entities": INVENTED_ENTITIES,
    **{entity.name: entity for entity in INVENTED_ENTITIES},
    **{name: name.lower() for name in ("DAY", "MONTH", "YEAR", "ETERNITY")},
}


def python_attributes(source):
    """What Python binds the invented variable's class namespace to, in the
    record's spellings, or None if the module fails.

    Builtins are a copy, so a module that changes them changes only its own.
    """
    module = types.ModuleType(inventory.MODEL_API)
    vars(module).update(INVENTED_MODEL_API)

    simulations = types.ModuleType("policyengine_core.simulations")
    simulations.Simulation = type("Simulation", (), {})

    def stand_in_import(name, *args, **kwargs):
        stand_ins = {
            inventory.MODEL_API: module,
            "policyengine_core.simulations": simulations,
        }
        if name in stand_ins:
            return stand_ins[name]
        raise ImportError(name)

    namespace = {
        "__builtins__": vars(builtins) | {"__import__": stand_in_import}
    }
    spelled = {
        id(value): name
        for name, value in INVENTED_MODEL_API.items()
        if name != "entities"
    } | {id(kind): kind.__name__ for kind in (bool, int, float, str)}
    try:
        exec(source, namespace)  # noqa: S102 - invented source only
        attributes = vars(namespace["invented_age"])
        return {
            "value_type": spelled[id(attributes["value_type"])],
            "entity": spelled[id(attributes["entity"])],
            "period": spelled[id(attributes["definition_period"])],
            "default": attributes.get("default_value"),
        }
    except Exception:
        return None


def read_attributes(source):
    """The reader's attributes for the invented age variable, or None if it
    refuses the module or the variable. Imports are not followed here."""
    tree = ast.parse(source)
    if inventory.module_imports(tree) is None:
        return None
    variable = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "invented_age"
    )
    try:
        record = inventory.variable_attributes(tree, variable)
    except ValueError:
        return None
    return {key: record[key] for key in ("value_type", "entity", "period")} | {
        "default": record["default"]
    }


INVENTED_AGE_RECORD = {
    "value_type": "int",
    "entity": "Person",
    "period": "YEAR",
    "default": 41,
}


def test_invented_age_module_is_read_as_python_binds_it():
    assert read_attributes(INVENTED_AGE_MODULE) == INVENTED_AGE_RECORD
    assert python_attributes(INVENTED_AGE_MODULE) == INVENTED_AGE_RECORD


@pytest.mark.parametrize("kind", sorted(ATTRIBUTE_ROUTES))
def test_attribute_routes_refuse_inventory(tmp_path, kind):
    """Each route refuses end to end, by the rule named; an observable one
    also changes what Python binds."""
    forms, message, observable = ATTRIBUTE_ROUTES[kind]
    source = invented_age_module(forms)
    assert read_attributes(source) is None
    if observable:
        assert python_attributes(source) not in (None, INVENTED_AGE_RECORD)
    package = invented_package(tmp_path / "control")
    (package / "variables/input/invented_age.py").write_text(
        invented_age_module()
    )
    record = next(
        v
        for v in inventory.inventory_release(package)["inputs"]
        if v["name"] == "invented_age"
    )
    assert {key: record[key] for key in ("value_type", "entity", "period")} | {
        "default": record["default"]
    } == INVENTED_AGE_RECORD
    package = invented_package(tmp_path / "route")
    (package / "variables/input/invented_age.py").write_text(source)
    with pytest.raises(ValueError, match=message):
        inventory.inventory_release(package)


INVENTED_SECOND_CLASS = (
    "class invented_age(Variable):\n"
    "    value_type = float\n"
    "    entity = Person\n"
    "    definition_period = YEAR"
)


@pytest.mark.parametrize(
    "form",
    (
        "invented_age = None",
        "def invented_age():\n    return 0",
        INVENTED_SECOND_CLASS,
    ),
    ids=["name", "function", "second_class"],
)
def test_variable_name_bound_again_refuses_inventory(tmp_path, form):
    """After a second binding of the variable's name, the module's name no
    longer gives the class the reader reads, so the inventory refuses. (The
    pinned engine raises ValueError on loading the second class.)"""
    source = invented_age_module([("tail", form)])
    assert read_attributes(source) is None
    assert python_attributes(source) != INVENTED_AGE_RECORD
    package = invented_package(tmp_path)
    (package / "variables/input/invented_age.py").write_text(source)
    with pytest.raises(ValueError, match="Unread variable invented_age"):
        inventory.inventory_release(package)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 syntax")
def test_variable_with_type_parameters_refuses_inventory(tmp_path):
    """Python adds Generic to the bases of a class with type parameters, so
    the variable's bases are not the one written."""
    header = "class invented_age[InventedType](Variable):"
    source = invented_age_module([("class invented_age(Variable):", header)])
    assert read_attributes(source) is None
    namespace = {"Variable": type("Variable", (), {})}
    exec(header + "\n    pass", namespace)  # noqa: S102 - invented source only
    assert typing.Generic in namespace["invented_age"].__bases__
    package = invented_package(tmp_path)
    (package / "variables/input/invented_age.py").write_text(source)
    with pytest.raises(ValueError, match="Unread variable invented_age"):
        inventory.inventory_release(package)


# Forms the reader admits in a primitive variable's module, as (place, text).
ADMITTED_AGE_FORMS = {
    "second_label": ("body_tail", 'label = "Invented note"'),
    "formula": (
        "body_tail",
        "def formula(person, period, parameters):\n"
        '    return person("invented_other", period)',
    ),
    "dated_formula": (
        "body_tail",
        "def formula_2020(person, period, parameters):\n    return 0",
    ),
    "names_as_text": (
        "body_tail",
        'documentation = "globals setattr __builtins__ int = float"',
    ),
    "helper": ("tail", "def invented_helper():\n    return int, Person, YEAR"),
    "private_helper": ("tail", "def _invented_helper():\n    return float"),
    "core_import": (
        "head",
        "from policyengine_core.simulations import Simulation",
    ),
    "aliased_core_import": (
        "head",
        "from policyengine_core.simulations import Simulation as InventedSim",
    ),
    "reading": ("tail", "INVENTED_READ = (entities[3], TaxUnit, MONTH)"),
    # Function and lambda bodies run only when called, so calls, item
    # stores and in-place assignments there are admitted.
    "helper_call": ("tail", "def invented_caller():\n    return max_(1, 2)"),
    "lambda_body_call": ("tail", "INVENTED_LATER = lambda: max_(1, 2)"),
    "function_body_store": (
        "tail",
        "def invented_store(table):\n"
        '    table["int"] = 1\n'
        '    table |= {"float": 1}\n'
        '    del table["int"]',
    ),
    "nested_decorator": (
        "tail",
        "def invented_outer():\n"
        "    @invented_decorator\n"
        "    def invented_inner():\n"
        "        return 1\n"
        "    return invented_inner",
    ),
    "enum_class": (
        "head",
        'class InventedStatus(Enum):\n    INVENTED_FIRST = "first"',
    ),
    "negative_default": ("default_value = 41", "default_value = -41"),
}


@settings(deadline=None, max_examples=300)
@given(
    admitted=st.lists(
        st.sampled_from(sorted(ADMITTED_AGE_FORMS)), unique=True
    ),
    route=st.none() | st.sampled_from(sorted(ATTRIBUTE_ROUTES)),
    position=st.integers(0, 12),
)
def test_static_attributes_agree_with_python(admitted, route, position):
    """Differential: whatever the reader admits, Python binds the same
    value_type, entity, period and default; any route refuses."""
    # Both replace the same default.
    assume(not (route == "bool_default" and "negative_default" in admitted))
    forms = [ADMITTED_AGE_FORMS[kind] for kind in admitted]
    if route:
        forms[position % (len(forms) + 1) : 0] = ATTRIBUTE_ROUTES[route][0]
    source = invented_age_module(forms)
    read = read_attributes(source)
    if read is not None:
        assert read == python_attributes(source)
    if route:
        assert read is None
    else:
        assert read is not None


@pytest.mark.parametrize(
    ("value_type", "default", "expected"),
    [
        ("int", "-41", -41),
        ("int", "(41)", 41),
        ("int", "True", None),
        ("int", "41.0", None),
        ("int", 'int("41")', None),
        ("int", "invented_default", None),
        ("float", "41", 41),
        ("float", "41.5", 41.5),
        ("float", "-0.5", -0.5),
        ("float", "False", None),
        ("float", '"41"', None),
        # The engine's float() of an int must give back the same number.
        ("float", str(2**53), 2**53),
        ("float", str(2**53 + 1), None),
        ("float", str(-(2**53) - 1), None),
        pytest.param("float", "1" + "0" * 400, None, id="float-overflow"),
        pytest.param(
            "float", "-1" + "0" * 400, None, id="float-negative-overflow"
        ),
        ("bool", "True", True),
        ("bool", "1", None),
        ("bool", "not False", None),
        ("str", '"invented"', "invented"),
        ("str", "0", None),
        ("str", 'b"invented"', None),
        ("str", "invented_default", None),
    ],
)
def test_primitive_default_is_a_literal_of_its_type(
    value_type, default, expected
):
    """The engine converts an int default of a float and refuses most other
    mismatches; the reader admits only a literal of the variable's type."""
    source = invented_age_module(
        [
            ("value_type = int", f"value_type = {value_type}"),
            ("default_value = 41", f"default_value = {default}"),
        ]
    )
    read = read_attributes(source)
    if expected is None:
        assert read is None
    else:
        assert read["default"] == expected
        assert type(read["default"]) is type(expected)


@settings(deadline=None, max_examples=200)
@given(
    st.one_of(
        st.integers(-(2**60), 2**60),
        st.integers(2**53 - 8, 2**53 + 8),
        st.integers(2**1023, 2**1025),
    ),
    st.booleans(),
)
def test_int_default_of_a_float_is_read_only_when_it_converts_exactly(
    value, negative
):
    """The engine holds float(value) for an int default of a float
    variable, or raises OverflowError; the reader admits the int only when
    that float equals it, so the record and the engine agree."""
    value = -value if negative else value
    source = invented_age_module(
        [
            ("value_type = int", "value_type = float"),
            ("default_value = 41", f"default_value = {value}"),
        ]
    )
    read = read_attributes(source)
    try:
        engine = float(value)
    except OverflowError:
        engine = None
    if engine is not None and engine == value:
        assert read["default"] == value == engine
    else:
        assert read is None


@pytest.mark.parametrize(
    "attribute", ["value_type", "entity", "definition_period"]
)
def test_required_attribute_absent_refuses_inventory(tmp_path, attribute):
    # The engine refuses a variable without one; the record must name it.
    package = invented_package(tmp_path)
    path = package / "variables/input/invented_age.py"
    text = path.read_text()
    line = next(
        line for line in text.splitlines() if f" {attribute} = " in line
    )
    path.write_text(text.replace(line + "\n", ""))
    with pytest.raises(
        ValueError, match=f"Unresolved {attribute} for invented_age"
    ):
        inventory.inventory_release(package)


# Module code the reader refuses, wherever the module sits in the closure:
# (place, text) as in ATTRIBUTE_ROUTES.
REFUSED_MODULE_FORMS = {
    "plain_import": ("head", "import invented_module"),
    "plain_core_import": ("head", "import policyengine_core.variables.config"),
    "other_star_import": ("head", "from invented_module import *"),
    "core_star_import": (
        "head",
        "from policyengine_core.simulations import *",
    ),
    # policyengine_core names other than the one the closure imports.
    "core_package_import": (
        "head",
        "from policyengine_core import invented_tool",
    ),
    "core_prefix_import": (
        "head",
        "from policyengine_coreinvented import invented_tool",
    ),
    "core_defaults_import": (
        "head",
        "from policyengine_core.variables.config import VALUE_TYPES",
    ),
    "core_other_name": (
        "head",
        "from policyengine_core.simulations import invented_tool",
    ),
    "core_extra_name": (
        "head",
        "from policyengine_core.simulations import Simulation, invented_tool",
    ),
    "core_module_prefix": (
        "head",
        "from policyengine_core.simulationsinvented import Simulation",
    ),
    "core_submodule": (
        "head",
        "from policyengine_core.simulations.invented import Simulation",
    ),
    "relative_import": ("head", "from .invented_module import invented_tool"),
    # Relative imports whose module is spelled like an admitted one.
    "relative_variables_import": (
        "head",
        "from .policyengine_us.variables.input.invented_age import "
        "invented_age",
    ),
    "relative_model_api": ("head", "from .policyengine_us.model_api import *"),
    "other_package_import": (
        "head",
        "from policyengine_us.invented import invented_tool",
    ),
    "nested_import": (
        "body_tail",
        "def formula(person, period, parameters):\n"
        "    from policyengine_core.simulations import Simulation\n"
        "    return Simulation",
    ),
    "guarded_import": (
        "head",
        "if True:\n    from policyengine_core.simulations import Simulation",
    ),
    "dunder_name": ("tail", "INVENTED_NAME = __name__"),
    "dunder_attribute": ("tail", "INVENTED_NAMES = Variable.__dict__"),
    "dotted_dunder": (
        "head",
        "from policyengine_core.__invented__ import invented_tool",
    ),
    "reflective_name": ("tail", "INVENTED_READER = vars"),
    "frame_attribute": (
        "tail",
        "def invented_frame(frame):\n    return frame.f_globals",
    ),
    # Names held in a list of strings rather than in a node of their own.
    "match_keyword_dunder": (
        "tail",
        "match invented_age:\n"
        "    case object(__invented__=invented_value):\n"
        "        pass",
    ),
    "global_dunder": (
        "tail",
        "def invented_scope():\n    global __invented__",
    ),
    "attribute_delete": ("tail", "del invented_age.label"),
    "plain_class": ("tail", "class InventedHelper:\n    pass"),
    "other_base": ("tail", "class InventedHelper(Variable, Enum):\n    pass"),
    "decorated_enum": (
        "tail",
        '@invented_decorator\nclass InventedStatus(Enum):\n    INVENTED = "x"',
    ),
    "keyword_class": (
        "tail",
        "class InventedStatus(Enum, metaclass=type):\n    INVENTED = 'x'",
    ),
    "nested_class": (
        "tail",
        "if True:\n    class invented_spare(Variable):\n"
        "        value_type = float",
    ),
    "variable_bound": ("tail", "Variable = None"),
    # Code that runs as the module is imported and can change what another
    # module holds: calls, decorators, item stores and deletes, and
    # augmented assignments, at module level, in class bodies, and in the
    # decorators, defaults and annotations of functions and lambdas.
    "item_store": ("tail", 'INVENTED_TABLE = {}\nINVENTED_TABLE["int"] = 1'),
    "item_delete": (
        "tail",
        'INVENTED_TABLE = {"int": 1}\ndel INVENTED_TABLE["int"]',
    ),
    "item_store_target": (
        "tail",
        'INVENTED_TABLE = {}\nfor INVENTED_TABLE["int"] in (1,):\n    pass',
    ),
    "augmented_assignment": (
        "tail",
        'INVENTED_TABLE = {}\nINVENTED_TABLE |= {"int": 1}',
    ),
    "module_call": ("tail", "INVENTED_SPARE = max_(1, 2)"),
    "method_call": (
        "tail",
        "INVENTED_TABLE = {}\nINVENTED_TABLE.update(int=1)",
    ),
    "class_body_call": ("body_tail", 'label = str("Invented age")'),
    "enum_body_call": (
        "tail",
        'class InventedStatus(Enum):\n    INVENTED = str("x")',
    ),
    "comprehension_call": (
        "tail",
        "INVENTED_SPARE = [max_(1, 2) for invented_item in (1,)]",
    ),
    "decorated_function": (
        "tail",
        "@invented_decorator\ndef invented_helper():\n    return 1",
    ),
    "default_argument_call": (
        "tail",
        "def invented_helper(value=max_(1, 2)):\n    return value",
    ),
    "keyword_default_call": (
        "tail",
        "def invented_helper(*, value=max_(1, 2)):\n    return value",
    ),
    "annotation_call": (
        "tail",
        "def invented_helper(value: max_(1, 2)):\n    return value",
    ),
    "return_annotation_call": (
        "tail",
        "def invented_helper() -> max_(1, 2):\n    return 1",
    ),
    "lambda_default_call": (
        "tail",
        "INVENTED_SPARE = lambda value=max_(1, 2): value",
    ),
}


@pytest.mark.parametrize("kind", sorted(REFUSED_MODULE_FORMS))
def test_module_code_outside_the_rules_refuses_inventory(tmp_path, kind):
    source = invented_age_module([REFUSED_MODULE_FORMS[kind]])
    assert read_attributes(source) is None
    package = invented_package(tmp_path)
    (package / "variables/input/invented_age.py").write_text(source)
    with pytest.raises(
        ValueError,
        match="Unread module code in variables/input/invented_age.py",
    ):
        inventory.inventory_release(package)


INVENTED_TOOLS_IMPORT = (
    "from policyengine_us.variables.invented.invented_tools import "
    "invented_tool"
)


def package_importing_tools(tmp_path, tools, init=None):
    """An invented package whose age module imports a tools module that is
    neither an SSI root nor a variable, with an optional package init."""
    package = invented_package(tmp_path)
    folder = package / "variables/invented"
    folder.mkdir()
    (folder / "invented_tools.py").write_text(tools)
    if init is not None:
        (folder / "__init__.py").write_text(init)
    (package / "variables/input/invented_age.py").write_text(
        invented_age_module([("head", INVENTED_TOOLS_IMPORT)])
    )
    return package


INVENTED_TOOLS = "def invented_tool():\n    return 1\n"


@pytest.mark.parametrize("position", ["tools", "init"])
@pytest.mark.parametrize("kind", sorted(REFUSED_MODULE_FORMS))
def test_module_code_outside_the_rules_refuses_inventory_when_imported(
    tmp_path, kind, position
):
    """Each refused form, in a module the age module imports or in the
    package init that import runs, where only ``module_imports`` reads it."""
    place, text = REFUSED_MODULE_FORMS[kind]
    if place == "head":
        code = f"{text}\n\n\n{INVENTED_TOOLS}"
    else:
        code = f"{INVENTED_TOOLS}\n\n{text}\n"
    if position == "tools":
        package = package_importing_tools(tmp_path, code)
        relative = "invented_tools.py"
    else:
        package = package_importing_tools(tmp_path, INVENTED_TOOLS, code)
        relative = "__init__.py"
    with pytest.raises(
        ValueError,
        match=f"Unread module code in variables/invented/{relative}",
    ):
        inventory.inventory_release(package)


def test_literals_are_not_read_as_names(tmp_path):
    """A string literal may spell a reflective or dunder name: it is data,
    in the variable module, a module it imports or a package init."""
    notes = 'INVENTED_NOTES = ("vars", "__invented__", "invented.f_globals")'
    source = invented_age_module([("tail", notes)])
    assert read_attributes(source) == INVENTED_AGE_RECORD
    package = invented_package(tmp_path / "variable")
    (package / "variables/input/invented_age.py").write_text(source)
    assert inventory.inventory_release(package)
    code = f"{INVENTED_TOOLS}\n\n{notes}\n"
    package = package_importing_tools(tmp_path / "tools", code)
    assert inventory.inventory_release(package)
    package = package_importing_tools(tmp_path / "init", INVENTED_TOOLS, code)
    assert inventory.inventory_release(package)


def test_imported_variables_module_is_read_by_the_same_rules(tmp_path):
    tools = "def invented_tool():\n    return 1\n"
    package = package_importing_tools(tmp_path / "plain", tools)
    assert inventory.inventory_release(package)
    package = package_importing_tools(tmp_path / "tools_init", tools, "")
    assert inventory.inventory_release(package)
    # The imported module, or a package init its import runs, may change
    # the importer's variables, so each is read too.
    for folder, code, init in (
        ("store", tools + "invented_tool.cache = None\n", None),
        ("reflective", tools + 'globals()["int"] = float\n', None),
        ("init", tools, '__builtins__["int"] = float\n'),
    ):
        package = package_importing_tools(tmp_path / folder, code, init)
        relative = "invented_tools.py" if init is None else "__init__.py"
        with pytest.raises(
            ValueError,
            match=f"Unread module code in variables/invented/{relative}",
        ):
            inventory.inventory_release(package)
    # The import runs every package init on its path, not only the nearest.
    package = package_importing_tools(tmp_path / "outer_init", tools, "")
    (package / "variables/__init__.py").write_text("import invented_module\n")
    with pytest.raises(
        ValueError, match="Unread module code in variables/__init__.py"
    ):
        inventory.inventory_release(package)


def test_import_cycles_are_read_once(tmp_path):
    tools = (
        "from policyengine_us.variables.input.invented_age import "
        "invented_age\n"
    )
    package = package_importing_tools(tmp_path, tools)
    assert inventory.inventory_release(package)


def test_imports_are_followed_through_imported_modules(tmp_path):
    tools = (
        "from policyengine_us.variables.invented.invented_more import "
        "invented_more\n"
    )
    package = package_importing_tools(tmp_path, tools)
    more = package / "variables/invented/invented_more.py"
    more.write_text("def invented_more():\n    return 1\n")
    assert inventory.inventory_release(package)
    more.write_text("import invented_module\n")
    with pytest.raises(ValueError, match="invented/invented_more.py"):
        inventory.inventory_release(package)


def test_unresolved_variables_import_refuses_inventory(tmp_path):
    package = invented_package(tmp_path)
    (package / "variables/input/invented_age.py").write_text(
        invented_age_module([("head", INVENTED_TOOLS_IMPORT)])
    )
    with pytest.raises(
        ValueError,
        match="Unresolved import of policyengine_us.variables.invented",
    ):
        inventory.inventory_release(package)


def python_finds(root, module):
    """The loader and file Python's own import system finds for ``module``,
    in a fresh interpreter with ``root`` first on its path and no site
    packages. Finding runs only the parent packages, here invented
    namespace folders or empty inits."""
    code = (
        "import importlib.util, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "spec = importlib.util.find_spec(sys.argv[2])\n"
        "print(type(spec.loader).__name__, spec.origin)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", code, str(root), module],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    loader, origin = completed.stdout.strip().split(" ", 1)
    return loader, Path(origin)


# Round 8's frame-walking init, which rebinds int in the module importing
# it, from the review's repro of a package that shadows a module.
INVENTED_SHADOW_INIT = """import sys

frame = sys._getframe()
while frame is not None and not frame.f_globals.get("__file__", "").endswith(
    "invented_age.py"
):
    frame = frame.f_back
frame.f_globals["int"] = float


def invented_tool():
    return 1
"""


@pytest.mark.parametrize(
    "init",
    [INVENTED_SHADOW_INIT, f"{INVENTED_TOOLS}\nINVENTED_NAME = __name__\n"],
    ids=["frame_walk", "dunder_name"],
)
def test_package_that_shadows_a_module_is_read_as_python_finds_it(
    tmp_path, init
):
    """With both invented_tools/__init__.py and invented_tools.py, Python
    imports the package; the reader reads its init, not the module."""
    package = package_importing_tools(tmp_path, INVENTED_TOOLS)
    assert inventory.inventory_release(package)
    shadow = package / "variables/invented/invented_tools"
    shadow.mkdir()
    (shadow / "__init__.py").write_text(init)
    module = "policyengine_us.variables.invented.invented_tools"
    assert python_finds(tmp_path, module) == (
        "SourceFileLoader",
        shadow / "__init__.py",
    )
    with pytest.raises(
        ValueError,
        match="Unread module code in "
        "variables/invented/invented_tools/__init__.py",
    ):
        inventory.inventory_release(package)


def test_import_caches_do_not_outlive_a_folder_change(tmp_path):
    """The import system's finder keeps a folder's listing until the
    folder's modification time changes, which a copy that keeps times can
    prevent. The reader clears those caches before each read, so a second
    read in one process finds what a fresh interpreter finds."""
    package = package_importing_tools(tmp_path, INVENTED_TOOLS)
    folder = package / "variables/invented"
    before = folder.stat()
    assert inventory.inventory_release(package)
    shadow = folder / "invented_tools"
    shadow.mkdir()
    (shadow / "__init__.py").write_text(INVENTED_SHADOW_INIT)
    os.utime(folder, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert folder.stat().st_mtime_ns == before.st_mtime_ns
    module = "policyengine_us.variables.invented.invented_tools"
    assert python_finds(tmp_path, module) == (
        "SourceFileLoader",
        shadow / "__init__.py",
    )
    with pytest.raises(
        ValueError,
        match="Unread module code in "
        "variables/invented/invented_tools/__init__.py",
    ):
        inventory.inventory_release(package)


def test_sourceless_package_init_refuses_inventory(tmp_path):
    """Python runs a package's __init__.pyc when no __init__.py is there;
    the reader has no source to read, so it refuses."""
    package = package_importing_tools(tmp_path, INVENTED_TOOLS)
    folder = package / "variables/invented"
    source = tmp_path / "invented_init_source.py"
    source.write_text("INVENTED_MARK = 1\n")
    py_compile.compile(
        str(source), cfile=str(folder / "__init__.pyc"), doraise=True
    )
    source.unlink()
    assert python_finds(tmp_path, "policyengine_us.variables.invented") == (
        "SourcelessFileLoader",
        folder / "__init__.pyc",
    )
    with pytest.raises(
        ValueError,
        match="Unread non-source module variables/invented/__init__.pyc",
    ):
        inventory.inventory_release(package)


def test_extension_module_beside_the_source_refuses_inventory(tmp_path):
    """Python's finder takes an extension module before source of the same
    name; the reader refuses rather than read the source."""
    package = package_importing_tools(tmp_path, INVENTED_TOOLS)
    suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    (package / f"variables/invented/invented_tools{suffix}").write_bytes(b"")
    with pytest.raises(
        ValueError,
        match=f"Unread non-source module variables/invented/invented_tools"
        f"{suffix}",
    ):
        inventory.inventory_release(package)


@pytest.mark.parametrize("init", [None, ""], ids=["namespace", "package"])
def test_name_a_submodule_supplies_refuses_inventory(tmp_path, init):
    """``from <package> import invented_tools`` runs invented_tools.py when
    the package's own code does not bind the name."""
    package = package_importing_tools(tmp_path, INVENTED_TOOLS, init)
    (package / "variables/input/invented_age.py").write_text(
        invented_age_module(
            [
                (
                    "head",
                    "from policyengine_us.variables.invented import "
                    "invented_tools",
                )
            ]
        )
    )
    module = "policyengine_us.variables.invented.invented_tools"
    assert python_finds(tmp_path, module) == (
        "SourceFileLoader",
        package / "variables/invented/invented_tools.py",
    )
    with pytest.raises(
        ValueError,
        match="Unread submodule import of "
        "policyengine_us.variables.invented.invented_tools",
    ):
        inventory.inventory_release(package)


@pytest.mark.parametrize(
    ("layout", "module"),
    [
        # A step past a module, which is not a package.
        ("invented_more", "invented.invented_tools.invented_more"),
        # The import system matches names by case, as the folder lists them.
        ("Invented_Tools", "invented.invented_tools"),
    ],
)
def test_import_python_cannot_resolve_refuses_inventory(
    tmp_path, layout, module
):
    package = package_importing_tools(tmp_path, INVENTED_TOOLS)
    folder = package / "variables/invented"
    if layout == "Invented_Tools":
        (folder / "invented_tools.py").rename(folder / "Invented_Tools.py")
    else:
        (folder / "invented_more.py").write_text(INVENTED_TOOLS)
    (package / "variables/input/invented_age.py").write_text(
        invented_age_module(
            [
                (
                    "head",
                    f"from policyengine_us.variables.{module} import "
                    "invented_tool",
                )
            ]
        )
    )
    with pytest.raises(
        ValueError,
        match=f"Unresolved import of policyengine_us.variables.{module}",
    ):
        inventory.inventory_release(package)


@pytest.mark.parametrize("position", ["tools", "init"])
def test_followed_modules_are_decoded_as_python_decodes_them(
    tmp_path, position
):
    """Under this cookie "+AAo-" is a newline, so Python runs a statement
    where a UTF-8 read sees a comment, in a followed module or in the
    package init its import runs."""
    code = (
        b"# coding: utf-7\n"
        + INVENTED_TOOLS.encode("ascii")
        + b'# +AAo-globals()["int"] = float\n'
    )
    assert len(ast.parse(code).body) == 2
    assert len(ast.parse(code.decode("utf-8")).body) == 1
    if position == "tools":
        package = package_importing_tools(tmp_path, INVENTED_TOOLS)
        path = package / "variables/invented/invented_tools.py"
    else:
        package = package_importing_tools(tmp_path, INVENTED_TOOLS, "")
        path = package / "variables/invented/__init__.py"
    path.write_bytes(code)
    relative = path.relative_to(package).as_posix()
    with pytest.raises(ValueError, match=f"Unread module code in {relative}"):
        inventory.inventory_release(package)


def test_enum_variable_with_a_formula_needs_readable_members(tmp_path):
    """Members are read for every enum variable, not only inputs."""
    for possible, refused in (
        ("InventedStatus", False),
        ("InventedImportedStatus", True),
    ):
        package = package_with_enum_input(tmp_path / possible, possible)
        path = package / "variables/input/invented_status.py"
        path.write_text(
            path.read_text()
            + "\n    def formula(person, period, parameters):\n"
            + '        return person("invented_age", period)\n'
        )
        if refused:
            with pytest.raises(
                ValueError,
                match="Unresolved enum members for invented_status",
            ):
                inventory.inventory_release(package)
            continue
        result = inventory.inventory_release(package)
        assert "invented_status" not in {v["name"] for v in result["inputs"]}
        status = next(
            v for v in result["variables"] if v["name"] == "invented_status"
        )
        assert status["enum_members"] == ["INVENTED_FIRST", "INVENTED_SECOND"]


def test_helper_roots_are_decoded_as_python_decodes_them(tmp_path):
    # Under this cookie "+AAo-" is a newline, so Python defines a helper
    # where a UTF-8 read sees a comment.
    package = invented_package(tmp_path)
    helpers = package / "variables/gov/ssa/ssi/invented_helpers.py"
    helpers.write_bytes(
        b"# coding: utf-7\n"
        b"# +AAo-def invented_helper(person, period):"
        b'+AAo-    return person("bank_account_assets", period)\n'
    )
    namespace = {}
    exec(compile(helpers.read_bytes(), helpers, "exec"), namespace)
    assert "invented_helper" in namespace
    assert not ast.parse(helpers.read_text(encoding="utf-8")).body
    path = package / "variables/gov/ssa/ssi/invented_ssi.py"
    path.write_text(
        path.read_text().replace(
            'person("invented_age", period)',
            'person("invented_age", period) + invented_helper(person, period)',
        )
    )
    result = inventory.inventory_release(package)
    record = next(
        v for v in result["variables"] if v["name"] == "invented_intermediate"
    )
    assert record["helper_functions"] == ["invented_helper"]
    assert "bank_account_assets" in record["dependencies"]


INVENTED_CORE_DEFAULTS = (
    'VALUE_TYPES = {bool: {"default": False}, int: {"default": 0}, '
    'float: {"default": 0}, str: {"default": ""}}\n'
)


def test_core_defaults_are_decoded_as_python_decodes_them(tmp_path):
    # Under this cookie the table is code; a UTF-8 read sees a comment.
    package = tmp_path / "policyengine_us"
    config = tmp_path / "policyengine_core/variables/config.py"
    config.parent.mkdir(parents=True)
    config.write_bytes(
        b"# coding: utf-7\n# +AAo-" + INVENTED_CORE_DEFAULTS.encode("ascii")
    )
    assert not ast.parse(config.read_text(encoding="utf-8")).body
    assert inventory.validate_core_defaults(package)["sha256"] == (
        inventory.sha256(config)
    )


INVENTED_CHANGED_TABLE = INVENTED_CORE_DEFAULTS.removeprefix(
    "VALUE_TYPES = "
).replace('float: {"default": 0}', 'float: {"default": 1}')


@pytest.mark.parametrize(
    ("second", "python_float_default"),
    [
        (f"VALUE_TYPES = {INVENTED_CHANGED_TABLE}", 1),
        (f"VALUE_TYPES: dict = {INVENTED_CHANGED_TABLE}", 1),
        ("VALUE_TYPES |= {}", 0),
        (
            f"match {INVENTED_CHANGED_TABLE.strip()}:\n"
            "    case VALUE_TYPES:\n"
            "        pass\n",
            1,
        ),
        ("from invented_core import invented_table as VALUE_TYPES\n", None),
        ("def invented_reset(VALUE_TYPES):\n    pass\n", 0),
    ],
)
def test_core_defaults_bound_twice_refuse_inventory(
    tmp_path, second, python_float_default
):
    """Python keeps the last of two bindings; the reader reads neither,
    whatever the second binding's form."""
    if python_float_default is not None:
        namespace = {"bool": bool, "int": int, "float": float, "str": str}
        exec(INVENTED_CORE_DEFAULTS + second, namespace)  # noqa: S102
        table = namespace["VALUE_TYPES"]
        assert table[float]["default"] == python_float_default
    package = tmp_path / "policyengine_us"
    config = tmp_path / "policyengine_core/variables/config.py"
    config.parent.mkdir(parents=True)
    config.write_text(INVENTED_CORE_DEFAULTS + second)
    with pytest.raises(ValueError, match="not one plain table"):
        inventory.validate_core_defaults(package)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('bool: {"default": False}', 'bool: {"default": 0}'),
        ('int: {"default": 0}', 'int: {"default": False}'),
        ('float: {"default": 0}', 'float: {"default": 0.0}'),
        ('str: {"default": ""}', 'str: {"default": b""}'),
    ],
)
def test_core_defaults_compare_by_type(tmp_path, old, new):
    """False == 0 in Python, but the engine keeps the default's type, and
    the record keeps the extractor's."""
    package = tmp_path / "policyengine_us"
    config = tmp_path / "policyengine_core/variables/config.py"
    config.parent.mkdir(parents=True)
    config.write_text(INVENTED_CORE_DEFAULTS.replace(old, new))
    with pytest.raises(ValueError, match="Core primitive defaults differ"):
        inventory.validate_core_defaults(package)


# Round 8's repros: a variable module that changes policyengine_core's
# table of type defaults as it is imported. The engine then gives every
# variable of that type without a default of its own the changed value,
# while a reader that admitted the module would record the table's.
CORE_DEFAULT_BINDINGS = {
    # The review's spelling, which the import rules also refuse.
    "core_import": (
        "from policyengine_core.variables.config import VALUE_TYPES"
    ),
    # A spelling the import rules admit: the model API exports warnings,
    # whose module holds sys.
    "model_api": (
        "VALUE_TYPES = warnings.sys.modules[\n"
        '    "policyengine_core.variables.config"\n'
        "].VALUE_TYPES"
    ),
}
# (value_type, the change, the default it gives the engine's variable)
CORE_DEFAULT_CHANGES = {
    "item_store": ("float", 'VALUE_TYPES[float]["default"] = 7', 7),
    "method_call": ("int", "VALUE_TYPES[int].update(default=7)", 7),
    "bool_default": ("bool", 'VALUE_TYPES[bool]["default"] = True', True),
    "augmented_assignment": (
        "float",
        "INVENTED_DEFAULTS = VALUE_TYPES[float]\n"
        'INVENTED_DEFAULTS |= {"default": 7}',
        7,
    ),
}


def core_default_module(value_type, binding, change=None):
    """The invented age module as a ``value_type`` variable with no default
    of its own, after ``binding`` and, if given, ``change``."""
    forms = [
        ("value_type = int", f"value_type = {value_type}"),
        ("    default_value = 41\n", ""),
        ("head", binding),
    ]
    if change is not None:
        forms.append(("head", change))
    return invented_age_module(forms)


@pytest.mark.parametrize("binding", sorted(CORE_DEFAULT_BINDINGS))
@pytest.mark.parametrize("change", sorted(CORE_DEFAULT_CHANGES))
def test_core_default_changes_refuse_inventory(tmp_path, change, binding):
    """Each change refuses, unit and end to end, whichever way the module
    reaches the table; see test_ssi_engine for what the engine loads."""
    value_type, text, _ = CORE_DEFAULT_CHANGES[change]
    source = core_default_module(
        value_type, CORE_DEFAULT_BINDINGS[binding], text
    )
    assert read_attributes(source) is None
    package = invented_package(tmp_path)
    (package / "variables/input/invented_age.py").write_text(source)
    with pytest.raises(
        ValueError,
        match="Unread module code in variables/input/invented_age.py",
    ):
        inventory.inventory_release(package)


@pytest.mark.parametrize("value_type", ["bool", "float", "int"])
def test_core_default_table_read_without_a_change_is_admitted(
    tmp_path, value_type
):
    """Reaching the table through the model API, with no change, is read,
    so the import-time rule, not the import rules, refuses the changes."""
    source = core_default_module(
        value_type, CORE_DEFAULT_BINDINGS["model_api"]
    )
    expected = INVENTED_AGE_RECORD | {
        "value_type": value_type,
        "default": inventory.TYPE_DEFAULTS[value_type],
    }
    assert read_attributes(source) == expected
    package = invented_package(tmp_path)
    (package / "variables/input/invented_age.py").write_text(source)
    record = next(
        v
        for v in inventory.inventory_release(package)["inputs"]
        if v["name"] == "invented_age"
    )
    assert record["default_origin"] == "core type"
    assert record["default"] == expected["default"]
    assert type(record["default"]) is type(expected["default"])


INVENTED_HIDDEN_AGE = (
    "class invented_age(Variable):\n"
    "    value_type = float\n"
    "    entity = Person\n"
    "    definition_period = MONTH\n"
    "    default_value = 7\n"
)


def test_hidden_folders_are_outside_the_file_index(tmp_path):
    """The engine's walk skips names with a leading dot, so a same-stem
    file in a hidden folder is never the one the engine loads."""
    package = invented_package(tmp_path)
    hidden = package / "variables/.invented_old"
    hidden.mkdir()
    (hidden / "invented_age.py").write_text(INVENTED_HIDDEN_AGE)
    hidden_root = package / "variables/gov/ssa/ssi/.invented_old"
    hidden_root.mkdir()
    (hidden_root / "invented_hidden_ssi.py").write_text(
        INVENTED_HIDDEN_AGE.replace("invented_age", "invented_hidden_ssi")
    )
    (package / "variables/gov/ssa/ssi/.invented_hidden_file.py").write_text(
        INVENTED_HIDDEN_AGE.replace("invented_age", "invented_hidden_file")
    )
    result = inventory.inventory_release(package)
    assert result["federal_ssi_variable_count"] == 2
    assert not {"invented_hidden_ssi", "invented_hidden_file"} & {
        v["name"] for v in result["variables"]
    }
    record = next(v for v in result["inputs"] if v["name"] == "invented_age")
    assert record["path"] == "variables/input/invented_age.py"
    assert {key: record[key] for key in ("value_type", "period")} | {
        "default": record["default"]
    } == {"value_type": "int", "period": "YEAR", "default": 41}
    # Without the visible file, the hidden one is not read in its place.
    (package / "variables/input/invented_age.py").unlink()
    with pytest.raises(
        ValueError,
        match="Unresolved dependency: invented_intermediate: invented_age",
    ):
        inventory.inventory_release(package)


def test_package_init_in_the_ssi_tree_is_not_a_root(tmp_path):
    """The engine's walk reads a folder's __init__.py as metadata only, so
    a variable defined there is not loaded and is not an SSI root."""
    package = invented_package(tmp_path)
    (package / "variables/gov/ssa/ssi/__init__.py").write_text(
        "class invented_init_ssi(Variable):\n"
        "    value_type = float\n"
        "    entity = Person\n"
        "    definition_period = YEAR\n"
    )
    result = inventory.inventory_release(package)
    assert result["federal_ssi_variable_count"] == 2
    assert "invented_init_ssi" not in {v["name"] for v in result["variables"]}
    assert result == inventory.inventory_release(
        invented_package(tmp_path / "plain")
    )


@pytest.mark.parametrize("root", ["invented_aa_dup", "invented_zz_dup"])
def test_dependency_whose_stem_names_two_files_refuses_inventory(
    tmp_path, root
):
    """Two files of one stem refuse a dependency on it, whether or not the
    reader has already read one of them: which file the engine's variable
    comes from is not settled by the stem."""
    package = invented_package(tmp_path)
    other = package / "variables/invented_other"
    other.mkdir()
    (other / "invented_age.py").write_text(INVENTED_HIDDEN_AGE)
    with pytest.raises(
        ValueError,
        match="Dependency invented_age of invented_intermediate names more "
        "than one file",
    ):
        inventory.inventory_release(package)
    # A duplicate stem that is also an SSI root, read before or after the
    # variable that depends on it, as the roots' order puts it.
    package = invented_package(tmp_path / "root")
    for folder in ("gov/ssa/ssi", "input"):
        (package / f"variables/{folder}/{root}.py").write_text(
            INVENTED_HIDDEN_AGE.replace("invented_age", root)
        )
    path = package / "variables/gov/ssa/ssi/invented_ssi.py"
    path.write_text(
        path.read_text().replace(
            'person("invented_age", period)',
            f'person("invented_age", period) + person("{root}", period)',
        )
    )
    with pytest.raises(
        ValueError,
        match=f"Dependency {root} of invented_intermediate names more than "
        "one file",
    ):
        inventory.inventory_release(package)


def test_stem_no_dependency_names_may_repeat(tmp_path):
    """As puf.py does in the pinned release, outside the closure."""
    package = invented_package(tmp_path)
    for folder in ("input", "gov/states/ca"):
        (package / f"variables/{folder}/invented_unused.py").write_text(
            INVENTED_HIDDEN_AGE.replace("invented_age", "invented_unused")
        )
    assert inventory.inventory_release(package) == inventory.inventory_release(
        invented_package(tmp_path / "plain")
    )


def test_state_supplement_files_are_those_the_walk_loads(tmp_path):
    package = invented_package(tmp_path)
    states = package / "variables/gov/states"
    (states / "ca/ca_state_supplement.py").write_text("")
    (states / ".invented_old").mkdir()
    (states / ".invented_old/ny_state_supplement.py").write_text("")
    result = inventory.inventory_release(package)
    assert result["state_supplement_paths"] == [
        "variables/gov/states/ca/ca_state_supplement.py"
    ]
    assert result["states_with_named_ssi_supplement_files"] == ["CA"]


@pytest.mark.parametrize("attribute", ["adds", "subtracts", "possible_values"])
def test_list_attribute_bound_twice_refuses_inventory(tmp_path, attribute):
    """Python keeps the second binding, which the reader would not read;
    the inventory refuses rather than read the first."""
    package = invented_package(tmp_path)
    path = package / "variables/gov/ssa/ssi/invented_ssi.py"
    line = '    adds = "gov.ssa.ssi.income.sources.earned"\n'
    text = path.read_text()
    assert text.count(line) == 1
    path.write_text(
        text.replace(
            line,
            line
            + f'    {attribute} = ["pension_income"]\n'
            + f'    {attribute} = ["bank_account_assets"]\n',
        )
    )
    namespace = {"Variable": object, "Person": None}
    namespace |= {"MONTH": None, "YEAR": None}
    exec(path.read_text(), namespace)  # noqa: S102 - invented source only
    assert getattr(namespace["invented_ssi"], attribute) == [
        "bank_account_assets"
    ]
    with pytest.raises(
        ValueError, match=f"Unresolved {attribute} for invented_ssi"
    ):
        inventory.inventory_release(package)
