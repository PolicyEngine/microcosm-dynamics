"""Inventory installed SSI source without importing the country model.

Invariants: every variable and parameter in the federal SSI trees appears;
every dependency reaches another inventoried variable or an explicit input;
formula boundaries are named, rather than allowing an implicit model default;
an enum input's members come only from a class whose membership a static
read settles, and include its default, or the inventory refuses; the output
is deterministic for the same source and distribution metadata.

This is source inspection only. SSI calculations use policyengine.py. Run
with the clone's interpreter and point ``--package`` at installed source::

    .venv/bin/python scripts/income_resources/inventory_ssi.py \
      --package /path/to/site-packages/policyengine_us \
      --compare /path/to/other/site-packages/policyengine_us \
      --policyengine-version 6.10.2 --output /path/to/inventory.json

Income and resource list members are observed inputs, even when PE-US also
offers formulas for them. Immigration status and take-up are explicit input
boundaries: SSI0 supplies status and a receipt decision, and does not simulate
immigration or fit a take-up model. All other dependencies are followed.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


class ParameterLoader(yaml.SafeLoader):
    """Keep effective-date keys as strings, including PE-US year zero."""


ParameterLoader.yaml_implicit_resolvers = copy.deepcopy(
    yaml.SafeLoader.yaml_implicit_resolvers
)
for initial, resolvers in ParameterLoader.yaml_implicit_resolvers.items():
    ParameterLoader.yaml_implicit_resolvers[initial] = [
        (tag, pattern)
        for tag, pattern in resolvers
        if tag != "tag:yaml.org,2002:timestamp"
    ]


SSI_VARIABLES = Path("variables/gov/ssa/ssi")
SSI_PARAMETERS = Path("parameters/gov/ssa/ssi")
SOURCE_LISTS = (
    "gov.ssa.ssi.income.sources.earned",
    "gov.ssa.ssi.income.sources.unearned",
    "gov.ssa.ssi.eligibility.resources.countable",
)
EXPLICIT_BOUNDARIES = {
    "is_tax_unit_head": "Explicit head role derived from typed tax-unit links",
    "is_tax_unit_spouse": "Explicit spouse role derived from typed tax-unit links",
    "immigration_status": "Observed immigration status, not its text adapter",
    "takes_up_ssi_if_eligible": "Explicit receipt decision; SSI4 fits take-up",
}
TYPE_DEFAULTS = {"float": 0, "int": 0, "bool": False, "str": ""}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_core_defaults(package: Path) -> dict[str, str]:
    """Refuse drift in the source of implicit primitive defaults."""
    path = package.parent / "policyengine_core/variables/config.py"
    tree = ast.parse(path.read_text())
    table = next(
        item.value
        for item in tree.body
        if isinstance(item, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "VALUE_TYPES"
            for target in item.targets
        )
    )
    actual = {}
    for key, value in zip(table.keys, table.values, strict=True):
        name = ast.unparse(key)
        if name not in TYPE_DEFAULTS:
            continue
        for field, default in zip(value.keys, value.values, strict=True):
            if ast.literal_eval(field) == "default":
                actual[name] = ast.literal_eval(default)
    if actual != TYPE_DEFAULTS:
        raise ValueError("Core primitive defaults differ from the extractor")
    return {
        "path": "policyengine_core/variables/config.py",
        "sha256": sha256(path),
    }


def expression(node: ast.AST | None) -> Any:
    """Return literal values or stable Python source for symbolic metadata."""
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return ast.unparse(node)


def module_bindings(tree: ast.Module, name: str) -> list[ast.stmt]:
    """Top-level statements that bind ``name`` in a module."""
    bound = []
    for node in tree.body:
        if isinstance(
            node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [
                item.id
                for target in node.targets
                for item in ast.walk(target)
                if isinstance(item, ast.Name)
            ]
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            names = [
                item.id
                for item in ast.walk(node.target)
                if isinstance(item, ast.Name)
            ]
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [
                alias.asname or alias.name.split(".")[0]
                for alias in node.names
            ]
        else:
            # Conditional, looped or guarded bindings cannot be read
            # statically, so any mention of the name counts against it.
            names = [
                item.id
                for item in ast.walk(node)
                if isinstance(item, ast.Name)
            ]
        if name in names:
            bound.append(node)
    return bound


def enum_members(tree: ast.Module, name: Any) -> list[str] | None:
    """Member names of an Enum class defined in the variable's own module.

    Returns None, so that an input whose members cannot be read is refused
    rather than left open, unless ``possible_values`` names a class that:

    - is the module's only binding of that name, subclasses ``Enum`` alone
      and has no decorators or class keywords;
    - holds only a leading docstring, ``pass``, methods and assignments of
      a string or integer literal, or of an earlier member, to public names;
    - names each member once, and no member shares a method's name.

    Annotated, tuple, private and ``_sunder_`` targets, nested classes and
    other values can change membership in ways a static read cannot settle.
    """
    if not isinstance(name, str):
        return None
    bindings = module_bindings(tree, name)
    if len(bindings) != 1:
        return None
    node = bindings[0]
    if (
        not isinstance(node, ast.ClassDef)
        or [expression(base) for base in node.bases] != ["Enum"]
        or node.keywords
        or node.decorator_list
    ):
        return None
    members = []
    methods = set()
    for index, item in enumerate(node.body):
        if (
            index == 0
            and isinstance(item, ast.Expr)
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        ):
            continue
        if isinstance(item, ast.Pass):
            continue
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.add(item.name)
            continue
        literal = (
            isinstance(item, ast.Assign)
            and isinstance(item.value, ast.Constant)
            and type(item.value.value) in (str, int)
        )
        alias = (
            isinstance(item, ast.Assign)
            and isinstance(item.value, ast.Name)
            and item.value.id in members
        )
        if not (literal or alias) or not all(
            isinstance(target, ast.Name) and not target.id.startswith("_")
            for target in item.targets
        ):
            return None
        members.extend(target.id for target in item.targets)
    # Enum itself refuses a member named ``mro``.
    if len(set(members)) != len(members) or set(members) & (methods | {"mro"}):
        return None
    return members or None


def distribution_version(package: Path) -> str:
    """Read installed metadata, without importing policyengine_us."""
    matches = sorted(package.parent.glob("policyengine_us-*.dist-info"))
    if len(matches) != 1:
        raise ValueError("Expected one policyengine_us dist-info directory")
    for line in (matches[0] / "METADATA").read_text().splitlines():
        if line.startswith("Version: "):
            return line.removeprefix("Version: ")
    raise ValueError("Installed metadata has no version")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def parameter_values(package: Path, name: str) -> list[str]:
    path = package / "parameters" / Path(*name.split("."))
    data = yaml.load(
        path.with_suffix(".yaml").read_text(), Loader=ParameterLoader
    )
    return sorted(
        {
            item
            for dated in data["values"].values()
            for item in (
                dated.get("value", []) if isinstance(dated, dict) else dated
            )
        }
    )


def parameter_path(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "parameters":
            return ""
    if isinstance(node, ast.Attribute):
        parent = parameter_path(node.value, aliases)
        if parent is not None:
            return f"{parent}.{node.attr}".lstrip(".")
    return None


def parse_variables(
    package: Path, boundaries: set[str]
) -> dict[str, dict[str, Any]]:
    """Read only the SSI closure, using variable filenames as the index."""
    paths = {
        path.stem: path
        for path in (package / "variables").rglob("*.py")
        if not path.name.startswith("_")
    }
    roots = sorted((package / SSI_VARIABLES).rglob("*.py"))
    records = {}
    helpers = {}
    # Federal helper functions are also part of the static dependency closure.
    for path in roots:
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.FunctionDef):
                helpers[node.name] = node
    pending = list(roots)
    visited = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        tree = ast.parse(path.read_text())
        classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and any(expression(base) == "Variable" for base in node.bases)
        ]
        # Several classes per file are supported, as in the invented fixtures.
        names = set(paths) | set(records) | {node.name for node in classes}
        for node in classes:
            attrs = {
                target.id: item.value
                for item in node.body
                if isinstance(item, ast.Assign)
                for target in item.targets
                if isinstance(target, ast.Name)
            }
            dtype = expression(attrs.get("value_type"))
            default = expression(attrs.get("default_value"))
            if "default_value" not in attrs:
                if dtype not in TYPE_DEFAULTS:
                    raise ValueError(f"Unresolved default for {node.name}")
                default = TYPE_DEFAULTS[dtype]
            if dtype == "Enum" and isinstance(default, str):
                default = default.rsplit(".", 1)[-1]
            bodies = [node]
            visited_helpers = set()
            for body in bodies:
                for item in ast.walk(body):
                    if (
                        isinstance(item, ast.Call)
                        and isinstance(item.func, ast.Name)
                        and item.func.id in helpers
                        and item.func.id not in visited_helpers
                    ):
                        visited_helpers.add(item.func.id)
                        bodies.append(helpers[item.func.id])
            strings = {
                item.value
                for body in bodies
                for item in ast.walk(body)
                if isinstance(item, ast.Constant)
                and isinstance(item.value, str)
            }
            dependencies = (strings & names) - {node.name}
            entity_accessors = {
                "person",
                "household",
                "tax_unit",
                "family",
                "spm_unit",
                "marital_unit",
            }
            for body in bodies:
                for item in ast.walk(body):
                    if not isinstance(item, ast.Call) or not item.args:
                        continue
                    func = item.func
                    accessor = (
                        func.id
                        if isinstance(func, ast.Name)
                        else (
                            func.attr
                            if isinstance(func, ast.Attribute)
                            else None
                        )
                    )
                    first = item.args[0]
                    if (
                        accessor in entity_accessors
                        and isinstance(first, ast.Constant)
                        and isinstance(first.value, str)
                    ):
                        dependencies.add(first.value)
            aliases = {}
            parameter_dependencies = set()
            for body in bodies:
                for item in ast.walk(body):
                    if isinstance(item, ast.Assign):
                        prefix = parameter_path(item.value, aliases)
                        if prefix is not None:
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    aliases[target.id] = prefix
                for item in ast.walk(body):
                    prefix = parameter_path(item, aliases)
                    if prefix:
                        parameter_dependencies.add(prefix)
            for attr in ("adds", "subtracts"):
                value = expression(attrs.get(attr))
                if isinstance(value, str) and value.startswith("gov."):
                    parameter_dependencies.add(value)
                    dependencies.update(parameter_values(package, value))
            records[node.name] = {
                "name": node.name,
                "path": path.relative_to(package).as_posix(),
                "line": node.lineno,
                "sha256": sha256(path),
                "entity": expression(attrs.get("entity")),
                "period": expression(attrs.get("definition_period")),
                "value_type": dtype,
                "default": default,
                "default_origin": (
                    "explicit" if "default_value" in attrs else "core type"
                ),
                "formula_names": [
                    item.name
                    for item in node.body
                    if isinstance(item, ast.FunctionDef)
                    and item.name.startswith("formula")
                ],
                "dependencies": sorted(dependencies),
                "parameter_dependencies": sorted(
                    p
                    for p in parameter_dependencies
                    if not any(
                        other.startswith(p + ".")
                        for other in parameter_dependencies
                    )
                ),
                "helper_functions": sorted(visited_helpers),
            }
            if dtype == "Enum":
                possible = expression(attrs.get("possible_values"))
                members = enum_members(tree, possible)
                # A default outside its own class's members would enter
                # unchecked, so the members stay unresolved.
                if members is not None and (
                    expression(attrs.get("default_value"))
                    != f"{possible}.{default}"
                    or default not in members
                ):
                    members = None
                records[node.name]["enum_members"] = members
            if node.name not in boundaries:
                pending.extend(
                    paths[name]
                    for name in dependencies
                    if name in paths and name not in records
                )
    return records


def inventory_release(
    package: Path, *, include_parameters: bool = True
) -> dict[str, Any]:
    sources = {name: parameter_values(package, name) for name in SOURCE_LISTS}
    boundaries = {
        item: f"Observed source listed by {name}"
        for name, items in sources.items()
        for item in items
    } | EXPLICIT_BOUNDARIES
    records = parse_variables(package, set(boundaries))
    roots = {
        name
        for name, record in records.items()
        if record["path"].startswith(SSI_VARIABLES.as_posix() + "/")
    }
    seen = set()
    inputs = {}
    readers = defaultdict(set)
    pending = sorted(roots)
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        record = records[name]
        if name in boundaries:
            record["bypassed_formula_dependencies"] = record["dependencies"]
            record["dependencies"] = []
        if name in boundaries or (
            not record["formula_names"] and not record["dependencies"]
        ):
            inputs[name] = record | {
                "reason": boundaries.get(name, "No formula or aggregation")
            }
            continue
        for dependency in record["dependencies"]:
            if dependency not in records:
                raise ValueError(
                    f"Unresolved dependency: {name}: {dependency}"
                )
            readers[dependency].add(name)
            pending.append(dependency)
    # Record direct read edges even for roots reached before their readers.
    for name in seen - set(inputs):
        for dependency in records[name]["dependencies"]:
            readers[dependency].add(name)
    for name, record in inputs.items():
        record["read_by"] = sorted(readers[name])
        if record["value_type"] == "Enum" and not record.get("enum_members"):
            raise ValueError(f"Unresolved enum members for input {name}")
    parameters = []
    prefixes = {
        p
        for name in seen - set(inputs)
        for p in records[name]["parameter_dependencies"]
    }
    parameter_paths = (
        set((package / SSI_PARAMETERS).rglob("*.yaml"))
        if include_parameters
        else set()
    )
    for prefix in prefixes if include_parameters else ():
        path = package / "parameters" / Path(*prefix.split("."))
        if path.with_suffix(".yaml").is_file():
            parameter_paths.add(path.with_suffix(".yaml"))
        elif path.is_dir():
            parameter_paths.update(path.rglob("*.yaml"))
    for path in sorted(parameter_paths):
        relative = path.relative_to(package)
        name = ".".join(relative.with_suffix("").parts[1:])
        in_tree = relative.is_relative_to(SSI_PARAMETERS)
        if not in_tree and not any(
            name == p or name.startswith(p + ".") for p in prefixes
        ):
            continue
        data = yaml.load(path.read_text(), Loader=ParameterLoader)
        parameters.append(
            {
                "name": name,
                "path": relative.as_posix(),
                "sha256": sha256(path),
                "in_federal_ssi_tree": in_tree,
                "values": json_safe(data.get("values")),
            }
        )
    state_paths = sorted(
        path.relative_to(package).as_posix()
        for path in (package / "variables/gov/states").rglob("*.py")
        if "state_supplement" in path.name
    )
    return {
        "policyengine_us_version": distribution_version(package),
        "source_lists": sources,
        "explicit_formula_boundaries": boundaries,
        "variables": [records[name] for name in sorted(seen)],
        "inputs": [inputs[name] for name in sorted(inputs)],
        "parameters": parameters,
        "states_with_named_ssi_supplement_files": sorted(
            {path.split("/")[3].upper() for path in state_paths}
        ),
        "state_supplement_paths": state_paths,
        "federal_ssi_variable_count": len(roots),
    }


def compare_releases(current: dict, other: dict) -> dict:
    result = {"reference_version": other["policyengine_us_version"]}
    for kind in ("variables", "parameters", "inputs"):
        left = {record["name"]: record for record in current[kind]}
        right = {record["name"]: record for record in other[kind]}
        result[f"missing_{kind}"] = sorted(right.keys() - left.keys())
        result[f"added_{kind}"] = sorted(left.keys() - right.keys())
        result[f"source_changed_{kind}"] = sorted(
            name
            for name in left.keys() & right.keys()
            if left[name]["sha256"] != right[name]["sha256"]
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--compare", type=Path, required=True)
    parser.add_argument("--policyengine-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    default_source = validate_core_defaults(args.package)
    current = inventory_release(args.package)
    reference = (
        current
        if args.compare.resolve() == args.package.resolve()
        else inventory_release(args.compare)
    )
    result = {
        "schema_version": 1,
        "policyengine_version": args.policyengine_version,
        "extraction": {
            "method": "Static AST closure plus parameter source-list expansion",
            "roots": "Every Variable class in variables/gov/ssa/ssi",
            "defaults": "Class default_value, else policyengine_core type default",
            "core_default_source": default_source,
            "scope": "Source inspection; no country-model runtime imports",
        },
        **current,
        "comparison_2_18_0": compare_releases(current, reference),
        "rules_engine_gaps": [
            {
                "id": "resource_deeming",
                "condition": "RULES_ENGINE_GAP",
                "details": (
                    "Refuse ineligible-spouse or parental resource deeming: "
                    "the certified release has no SSI resource-deeming tree."
                ),
            }
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
