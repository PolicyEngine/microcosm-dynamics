"""Invented miniature source packages exercise the static SSI inventory.

No survey records or installed rules engines are used. The fixtures below
are Python source text invented solely to check extraction invariants.
"""

from __future__ import annotations

import ast
import importlib.util
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
