"""Invented miniature source packages exercise the static SSI inventory.

No survey records or installed rules engines are used. The fixtures below
are Python source text invented solely to check extraction invariants.
"""

from __future__ import annotations

import ast
import builtins
import enum
import importlib.util
import symtable
import sys
import types
import warnings
from collections import defaultdict
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
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
    write_enum_input(package, source, name, members[0])
    with pytest.raises(ValueError, match="Unresolved enum members"):
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
    "kind",
    ("body_rebind", "body_import", "annotated_twice", "walrus", "try_import"),
)
def test_enum_input_bound_outside_a_plain_read_refuses_inventory(
    tmp_path, kind
):
    # The five forms that put one member list in the input record while the
    # variable held another, end to end through the inventory.
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
    with pytest.raises(ValueError, match="Unresolved enum members"):
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
# engine reads it, though no single plain assignment says so.
VALUE_TYPE_FORMS = {
    "annotated": ("value_type: type = Enum", []),
    "alias": (
        "value_type = InventedEnumType",
        [("head", "InventedEnumType = Enum")],
    ),
    "rebound": (
        "value_type = float",
        [("body_tail", "value_type: type = Enum")],
    ),
    "attribute_store": (
        "value_type = float",
        [("tail", "invented_status.value_type = Enum")],
    ),
    # A name the module never binds, neither a primitive type nor Enum.
    "model_api_alias": ("value_type = InventedModelApiEnum", []),
} | {
    # A primitive type is read by its spelling, so the module may not
    # rebind it.
    f"{primitive}_rebound": (
        f"value_type = {primitive}",
        [("head", f"{primitive} = Enum")],
    )
    for primitive in inventory.TYPE_DEFAULTS
}


@pytest.mark.parametrize("kind", sorted(VALUE_TYPE_FORMS))
def test_value_type_outside_one_plain_assignment_refuses_inventory(
    tmp_path, kind
):
    line, forms = VALUE_TYPE_FORMS[kind]
    source = invented_enum_module(
        enum_class("InventedStatus", ["INVENTED_FIRST", "INVENTED_SECOND"]),
        "InventedStatus",
        "INVENTED_FIRST",
        forms,
    ).replace("    value_type = Enum\n", f"    {line}\n")
    assert vars(python_variable(source))["value_type"] is enum.Enum
    package = invented_package(tmp_path)
    write_enum_module(package, source)
    with pytest.raises(ValueError, match="Unresolved value_type"):
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


@pytest.mark.parametrize(
    ("attribute", "binding"),
    [("entity", "Person = TaxUnit"), ("definition_period", "YEAR = MONTH")],
)
def test_entity_or_period_bound_in_its_module_refuses_inventory(
    tmp_path, attribute, binding
):
    """The record names both by their spelling, as with value_type."""
    package = invented_package(tmp_path)
    path = package / "variables/input/invented_age.py"
    path.write_text(f"{binding}\n\n\n" + path.read_text())
    with pytest.raises(ValueError, match=f"Unresolved {attribute}"):
        inventory.inventory_release(package)


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


def test_core_defaults_bound_twice_refuse_inventory(tmp_path):
    """Python keeps the last of two tables; the reader reads neither."""
    package = tmp_path / "policyengine_us"
    config = tmp_path / "policyengine_core/variables/config.py"
    config.parent.mkdir(parents=True)
    config.write_text(
        INVENTED_CORE_DEFAULTS
        + INVENTED_CORE_DEFAULTS.replace(
            'float: {"default": 0}', 'float: {"default": 1}'
        )
    )
    with pytest.raises(ValueError, match="not one plain table"):
        inventory.validate_core_defaults(package)
