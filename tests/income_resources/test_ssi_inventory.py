"""Invented miniature source packages exercise the static SSI inventory.

No survey records or installed rules engines are used. The fixtures below
are Python source text invented solely to check extraction invariants.
"""

from __future__ import annotations

import ast
import enum
import importlib.util
import warnings
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


def write_enum_input(
    package, class_source, possible_values, default="INVENTED_DEFAULT"
):
    """Write an invented enum input and make the invented SSI read it.

    ``default`` is the member name, or a dotted reference to another class.
    """
    reference = default if "." in default else f"{possible_values}.{default}"
    (package / "variables/input/invented_status.py").write_text(
        class_source + f"""

class invented_status(Variable):
    value_type = Enum
    entity = Person
    possible_values = {possible_values}
    default_value = {reference}
    definition_period = YEAR
"""
    )
    path = package / "variables/gov/ssa/ssi/invented_ssi.py"
    path.write_text(
        path.read_text().replace(
            'person("invented_age", period)',
            'person("invented_age", period) + '
            'person("invented_status", period)',
        )
    )


def enum_class(name, members, base="Enum"):
    body = "".join(
        f'    {member} = "{member.lower()}"\n' for member in members
    )
    return f"class {name}({base}):\n" + (body or "    pass\n")


@settings(deadline=None, max_examples=25)
@given(name=ENUM_NAMES, members=MEMBER_NAMES)
def test_enum_members_round_trip_from_source(tmp_path_factory, name, members):
    package = invented_package(tmp_path_factory.mktemp("invented_enum"))
    write_enum_input(package, enum_class(name, members), name, members[0])
    result = inventory.inventory_release(package)
    status = next(
        v for v in result["inputs"] if v["name"] == "invented_status"
    )
    assert status["enum_members"] == members


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
    write_enum_input(package, source, name)
    with pytest.raises(ValueError, match="Unresolved enum members"):
        inventory.inventory_release(package)


# Statement kinds for invented Enum class bodies. The first five are the
# forms the reader admits; the rest must make it refuse.
ADMITTED_STATEMENTS = ("literal", "integer", "alias", "method", "pass")
REFUSED_STATEMENTS = (
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
)


@st.composite
def invented_enum_source(draw):
    """Source of an invented Enum class, and whether a refused form occurs."""
    names = draw(
        st.lists(
            st.from_regex(r"INVENTED_[A-Z]{1,6}", fullmatch=True),
            min_size=8,
            max_size=8,
            unique=True,
        )
    )
    kinds = draw(
        st.lists(
            st.sampled_from(ADMITTED_STATEMENTS + REFUSED_STATEMENTS),
            min_size=1,
            max_size=8,
        )
    )
    docstring = draw(st.booleans())
    lines = ['    """Invented enum."""'] if docstring else []
    members = []
    refused = False
    for index, kind in enumerate(kinds):
        name = names[index]
        earlier = members[-1] if members else None
        if kind == "literal":
            line = f'{name} = "{name.lower()}"'
        elif kind == "integer":
            line = f"{name} = {index}"
        elif kind == "alias":
            line = f"{name} = {earlier}" if earlier else "pass"
        elif kind == "method":
            line = (
                f"def invented_method_{index}(self):\n        return {index}"
            )
        elif kind == "pass":
            line = "pass"
        elif kind == "annotated":
            line = f'{name}: str = "{name.lower()}"'
        elif kind == "tuple":
            line = f"{name}, {name}_PAIR = 1, 2"
        elif kind == "private":
            line = f"_{name} = {index}"
        elif kind == "sunder":
            line = '_ignore_ = ["INVENTED_IGNORED"]'
        elif kind == "call":
            line = f"{name} = auto()"
        elif kind == "lambda":
            line = f"{name} = lambda self: {index}"
        elif kind == "boolean":
            line = f"{name} = True"
        elif kind == "nested":
            line = f"class {name.title()}:\n        pass"
        elif kind == "late_docstring":
            line = '"""Invented later string."""'
        else:
            line = f'{earlier} = "invented repeat"' if earlier else "pass"
        if kind in ("literal", "integer") or (kind == "alias" and earlier):
            members.append(name)
        # A string that opens the body is a docstring, not a refused form.
        late = kind == "late_docstring" and (docstring or index > 0)
        if kind in REFUSED_STATEMENTS and kind not in (
            "late_docstring",
            "duplicate",
        ):
            refused = True
        refused = refused or late or (kind == "duplicate" and bool(earlier))
        lines.append("    " + line)
    source = "class InventedEnum(Enum):\n" + "\n".join(lines) + "\n"
    return source, kinds, refused


def python_enum_members(source):
    """Members Python's own Enum gives the source, or None if it refuses."""
    namespace = {"Enum": enum.Enum, "auto": enum.auto}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            exec(source, namespace)  # noqa: S102 - invented source only
    except Exception:
        return None
    return list(namespace["InventedEnum"].__members__)


@settings(deadline=None, max_examples=300)
@given(invented_enum_source())
def test_static_enum_members_agree_with_python_enum(generated):
    """Differential: the static reader against Python's Enum semantics."""
    source, kinds, refused = generated
    read = inventory.enum_members(ast.parse(source), "InventedEnum")
    if read is not None:
        # Whatever the reader admits, Python's Enum defines identically.
        assert read == python_enum_members(source)
    if refused:
        assert read is None
    elif set(kinds) <= set(ADMITTED_STATEMENTS) and python_enum_members(
        source
    ):
        # The admitted forms, with at least one member, are read.
        assert read == python_enum_members(source)


INVENTED_ENUM_CLASS = 'class InventedEnum(Enum):\n    INVENTED_ONE = "one"\n'


@pytest.mark.parametrize(
    "other",
    (
        INVENTED_ENUM_CLASS,
        "InventedEnum = InventedOtherEnum\n",
        "from invented_module import InventedEnum\n",
        "if INVENTED_FLAG:\n    InventedEnum = InventedOtherEnum\n",
        "InventedEnum.INVENTED_TWO = 2\n",
    ),
)
def test_enum_name_bound_twice_in_its_module_is_unread(other):
    for source in (INVENTED_ENUM_CLASS + other, other + INVENTED_ENUM_CLASS):
        assert (
            inventory.enum_members(ast.parse(source), "InventedEnum") is None
        )
    assert inventory.enum_members(
        ast.parse(INVENTED_ENUM_CLASS), "InventedEnum"
    ) == ["INVENTED_ONE"]


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
    source = header + '\n    INVENTED_ONE = "one"\n'
    assert inventory.enum_members(ast.parse(source), "InventedEnum") is None


def test_enum_member_named_mro_is_unread():
    # Python's Enum refuses this name, so the reader must not admit it.
    source = 'class InventedEnum(Enum):\n    mro = "one"\n'
    assert python_enum_members(source) is None
    assert inventory.enum_members(ast.parse(source), "InventedEnum") is None


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
