"""Inventory installed SSI source without importing the country model.

Invariants: every variable and parameter in the federal SSI trees appears;
the variable files are those the engine's directory walk loads, and a
dependency whose file stem names more than one of them refuses; every
dependency reaches another inventoried variable or an explicit input;
formula boundaries are named, rather than allowing an implicit model default;
each variable's value_type, entity and period are one plain assignment each,
of a name its module never binds, the value_type naming a primitive type or
Enum, or the inventory refuses; its default is absent, a literal of its
primitive type, or a member of its enum class, by one plain assignment, or
the inventory refuses, and an int default of a float variable converts to
the same float; an enum variable's members come only from a class whose
membership a static read settles, and include its default, or the
inventory refuses; source is decoded as Python decodes it; the output is
deterministic for the same source and distribution metadata.

The static read covers each variable module's own code, and every module
under ``policyengine_us/variables`` that it imports, found as the import
system finds it, with the package ``__init__`` files that import runs; a
step that is not Python source refuses. That code may not override a
Variable method, store an attribute, or name a reflective builtin, a frame
attribute or a dunder name, and the part of it that runs as the module is
imported may not call anything, apply a decorator, store or delete an
item, or assign in place. The read does not follow code in other modules:
the model API, the one policyengine_core name a closure module may import
(``Simulation``), and reflection through objects they export, including
the implicit calls that operators, iteration and attribute or item reads
make on them. The engine's directory walk also runs every module under
``policyengine_us/variables`` outside the closure, and such a module can
change what the engine loads; the reader does not read those modules, and
only the pinned-engine oracle covers them. Python's source loader can also
run a module's cached bytecode in ``__pycache__`` instead of its source: a
timestamp file that records the source's modification time and size, or
an unchecked hash-based file, is never compared with the source. The reader
reads only source, so only the pinned-engine oracle covers cached bytecode
too. The oracle tests cover what the
read leaves out only for the pinned release: they check each inventoried
variable's value_type, default (its value and type), entity and period,
and each enum variable's members, against what the engine loads.

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
import glob
import hashlib
import importlib.machinery
import json
import os
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


def typed(values: dict[str, Any]) -> dict[str, tuple[type, Any]]:
    return {key: (type(value), value) for key, value in values.items()}


def validate_core_defaults(package: Path) -> dict[str, str]:
    """Refuse drift in the source of implicit primitive defaults.

    The table must be the module's only binding of ``VALUE_TYPES``: with
    two, Python keeps the last. Item stores and calls that change the table
    as the module runs are not read; for the pinned release, the oracle
    compares every inventoried default with the engine's.
    """
    path = package.parent / "policyengine_core/variables/config.py"
    tree = ast.parse(path.read_bytes())
    if len(binding_sites(tree, "VALUE_TYPES")) != 1:
        raise ValueError("Core primitive defaults are not one plain table")
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
    # By type as well as value: False == 0, but the engine keeps the type.
    if typed(actual) != typed(TYPE_DEFAULTS):
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


MODEL_API = "policyengine_us.model_api"
# A variable module may import names from a module under FOLLOWED_IMPORTS,
# which the inventory reads by the same rules, and only the names listed
# here from any other module, which it does not read. The SSI closure
# imports Simulation and nothing else from policyengine_core.
FOLLOWED_IMPORTS = "policyengine_us.variables."
UNFOLLOWED_IMPORTS = {
    "policyengine_core.simulations": frozenset({"Simulation"}),
}
# Forms that bind a name in some scope: definitions, except handlers, match
# captures and, from Python 3.12, type parameters.
DEFINITIONS = (
    ast.ClassDef,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ExceptHandler,
    ast.MatchAs,
    ast.MatchStar,
) + tuple(
    getattr(ast, kind)
    for kind in ("TypeVar", "ParamSpec", "TypeVarTuple")
    if hasattr(ast, kind)
)
# Builtins and frame attributes that reach a namespace without a static
# binding. Reflection past these is left to the pinned-engine oracle.
REFLECTIVE = frozenset(
    {
        "compile",
        "delattr",
        "eval",
        "exec",
        "f_builtins",
        "f_globals",
        "f_locals",
        "getattr",
        "globals",
        "locals",
        "setattr",
        "vars",
    }
)
# The Enum class method that PE-US formulas call.
ENUM_API = frozenset({"encode"})
# The attribute names that policyengine_core's Variable constructor reads,
# through set or by popping them; the SSI0 oracle checks this against the
# pinned release.
ENGINE_ATTRIBUTES = frozenset(
    {
        "adds",
        "calculate_output",
        "category",
        "cerfa_field",
        "default_value",
        "defined_for",
        "definition_period",
        "documentation",
        "end",
        "entity",
        "exhaustive_parameter_dependencies",
        "hidden_input",
        "index_in_module",
        "is_period_size_independent",
        "label",
        "max_length",
        "max_value",
        "metadata",
        "min_value",
        "module_name",
        "possible_values",
        "quantity_type",
        "reference",
        "requires_computation_after",
        "set_input",
        "subtracts",
        "unit",
        "uprating",
        "value_type",
    }
)
# The engine attributes the inventory reads from each variable's body.
READ_ATTRIBUTES = (
    "value_type",
    "entity",
    "definition_period",
    "default_value",
    "possible_values",
    "adds",
    "subtracts",
)
# The literal types each primitive's default may have. The engine converts
# an int default of a float variable with float(), and the read admits one
# only when that gives back the same number, so the recorded int equals the
# engine's float. The engine also takes a bool for an int, which it keeps,
# or for a float, which it converts; the read refuses both.
DEFAULT_TYPES = {
    "float": (int, float),
    "int": (int,),
    "bool": (bool,),
    "str": (str,),
}


def binding_sites(tree: ast.AST, name: str) -> list[ast.AST]:
    """Every node under ``tree`` that binds or declares ``name``, in any scope.

    Counting every scope refuses more than Python would rebind, which is the
    safe direction. An attribute store counts, since code can rebind a class
    attribute or another module's global through it.
    """
    sites = []
    for item in ast.walk(tree):
        if isinstance(item, ast.Name):
            names = [] if isinstance(item.ctx, ast.Load) else [item.id]
        elif isinstance(item, ast.Attribute):
            names = [] if isinstance(item.ctx, ast.Load) else [item.attr]
        elif isinstance(item, DEFINITIONS):
            names = [item.name]
        elif isinstance(item, ast.MatchMapping):
            names = [item.rest]
        elif isinstance(item, (ast.Global, ast.Nonlocal)):
            names = item.names
        elif isinstance(item, ast.alias):
            names = [item.asname or item.name.split(".")[0]]
        elif isinstance(item, ast.arg):
            names = [item.arg]
        else:
            names = []
        if name in names:
            sites.append(item)
    return sites


def plain_attribute(variable: ast.ClassDef, attr: str) -> ast.expr | None:
    """The value a variable binds to ``attr`` by its one plain assignment."""
    sites = binding_sites(variable, attr)
    for item in variable.body:
        if (
            isinstance(item, ast.Assign)
            and len(item.targets) == 1
            and sites == item.targets
        ):
            return item.value
    return None


def static_module(tree: ast.Module, cls: ast.ClassDef) -> bool:
    """Whether a module's own code can change ``cls`` only in ways read here.

    The module imports nothing but the model API, and that only before the
    class; it binds neither ``Enum`` nor ``Variable``, whose spellings the
    reader takes to be the model API's; it stores or deletes no attribute,
    since a store can reach the class, a member, the variable or a base
    through any alias; and no identifier in it is a reflective builtin or
    frame attribute or has a leading underscore. Identifiers are every
    string field of the syntax tree outside literals: names, attributes,
    definitions, parameters, keywords and pattern keywords.
    """
    position = tree.body.index(cls)
    imports = [
        item
        for item in ast.walk(tree)
        if isinstance(item, (ast.Import, ast.ImportFrom))
    ]
    if any(
        not (
            isinstance(item, ast.ImportFrom)
            and item.module == MODEL_API
            and item.level == 0
            and [alias.name for alias in item.names] == ["*"]
            and any(item is top for top in tree.body[:position])
        )
        for item in imports
    ):
        return False
    for item in ast.walk(tree):
        if isinstance(item, ast.Attribute) and not isinstance(
            item.ctx, ast.Load
        ):
            return False
        if isinstance(item, ast.Constant):
            continue
        for _, value in ast.iter_fields(item):
            for name in value if isinstance(value, list) else [value]:
                if isinstance(name, str) and (
                    name in REFLECTIVE or name.startswith("_")
                ):
                    return False
    return not (binding_sites(tree, "Enum") or binding_sites(tree, "Variable"))


def import_time_nodes(tree: ast.AST) -> list[ast.AST]:
    """The nodes of ``tree`` that run as its module is imported.

    That is the module level and class bodies, with the decorators, default
    arguments, annotations and type parameters of each function and lambda
    defined there, but not the bodies of functions and lambdas, which run
    only when called.
    """
    nodes = []
    pending = [tree]
    while pending:
        node = pending.pop()
        nodes.append(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pending.extend(node.decorator_list)
            pending.append(node.args)
            pending.extend(getattr(node, "type_params", []))
            if node.returns is not None:
                pending.append(node.returns)
        elif isinstance(node, ast.Lambda):
            pending.append(node.args)
        else:
            pending.extend(ast.iter_child_nodes(node))
    return nodes


def runs_on_import(node: ast.AST) -> bool:
    """Whether ``node``, run as its module is imported, can change what
    another module holds.

    A call can, and so can a decorator, which its statement calls; so can
    an item store or delete, and an augmented assignment, which can change
    its target in place. Any of them can change a table such as
    policyengine_core's ``VALUE_TYPES``, whose defaults the engine gives
    every variable without one of its own.
    """
    return (
        isinstance(node, (ast.Call, ast.AugAssign))
        or (
            isinstance(node, ast.Subscript)
            and not isinstance(node.ctx, ast.Load)
        )
        or bool(getattr(node, "decorator_list", None))
    )


def module_imports(tree: ast.Module) -> list[str] | None:
    """The modules under policyengine_us.variables that a module imports.

    None, so that the inventory refuses, unless the module's own code can
    change its variables only in ways read here:

    - every import is a top-level statement: the model API's absolute star
      import, one that imports names from a module under
      ``FOLLOWED_IMPORTS``, or one that imports names that
      ``UNFOLLOWED_IMPORTS`` lists for its module;
    - every class is a top-level statement that subclasses ``Variable`` or
      ``Enum`` alone, with no decorators or keywords, and the module binds
      no ``Variable``, whose spelling the reader takes to be the model API's;
    - it stores or deletes no attribute;
    - no identifier in it, or part of a dotted one, is a reflective builtin
      or frame attribute or starts with two underscores, as ``__builtins__``
      and ``__dict__`` do. Identifiers are as in ``static_module``, which
      also refuses one underscore; helpers such as ``_apply_ssi_exclusions``
      have one;
    - nothing in ``import_time_nodes`` meets ``runs_on_import``: as the
      module is imported it calls nothing, applies no decorator, stores or
      deletes no item, and assigns nothing in place.
    """
    followed = []
    for item in ast.walk(tree):
        if isinstance(item, ast.Import):
            return None
        if isinstance(item, ast.ImportFrom):
            star = [alias.name for alias in item.names] == ["*"]
            module = item.module or ""
            if not (
                item.level == 0
                and any(item is top for top in tree.body)
                and (
                    module == MODEL_API
                    if star
                    else module.startswith(FOLLOWED_IMPORTS)
                    or {alias.name for alias in item.names}
                    <= UNFOLLOWED_IMPORTS.get(module, frozenset())
                )
            ):
                return None
            if not star and module.startswith(FOLLOWED_IMPORTS):
                followed.append(module)
        if isinstance(item, ast.ClassDef) and not (
            any(item is top for top in tree.body)
            and [expression(base) for base in item.bases]
            in (["Variable"], ["Enum"])
            and not item.keywords
            and not item.decorator_list
        ):
            return None
        if isinstance(item, ast.Attribute) and not isinstance(
            item.ctx, ast.Load
        ):
            return None
        if isinstance(item, ast.Constant):
            continue
        for _, value in ast.iter_fields(item):
            for name in value if isinstance(value, list) else [value]:
                if isinstance(name, str) and any(
                    part in REFLECTIVE or part.startswith("__")
                    for part in name.split(".")
                ):
                    return None
    if binding_sites(tree, "Variable"):
        return None
    if any(runs_on_import(node) for node in import_time_nodes(tree)):
        return None
    return followed


def relative_path(package: Path, path: Path) -> str:
    """``path`` relative to ``package``, both made absolute as the import
    system makes them."""
    return (
        Path(os.path.abspath(path))
        .relative_to(os.path.abspath(package))
        .as_posix()
    )


def import_sources(package: Path, module: str, names: set[str]) -> list[Path]:
    """The source files that importing ``names`` from ``module`` runs.

    Each step below ``policyengine_us`` is found as the import system finds
    it, by ``PathFinder``, which runs no code, in the folder the step before
    gives: a package folder comes before a module file, and an extension
    module before source. A namespace package runs no code. Every other
    step must be a ``.py`` file that ``SourceFileLoader`` loads, which the
    caller parses; otherwise this refuses. It also refuses a step past a
    module, which is not a package, and a name that a submodule of the
    imported package could supply, since the import would run that
    submodule when the package's own code does not bind the name.
    """
    directory = package
    sources = []
    spec = None
    for part in module.split(".")[1:]:
        if spec is not None and spec.submodule_search_locations is None:
            raise ValueError(f"Unresolved import of {module}")
        spec = importlib.machinery.PathFinder.find_spec(part, [str(directory)])
        if spec is None:
            raise ValueError(f"Unresolved import of {module}")
        if spec.loader is None:
            # A namespace package, whose one portion here is this folder.
            directory = directory / part
            continue
        origin = Path(spec.origin)
        if not (
            isinstance(spec.loader, importlib.machinery.SourceFileLoader)
            and origin.suffix == ".py"
        ):
            relative = relative_path(package, origin)
            raise ValueError(f"Unread non-source module {relative}")
        sources.append(origin)
        directory = origin.parent
    if spec is not None and spec.submodule_search_locations is not None:
        for name in sorted(names):
            if importlib.machinery.PathFinder.find_spec(
                name, [str(directory)]
            ):
                raise ValueError(f"Unread submodule import of {module}.{name}")
    return sources


def check_module(
    package: Path, path: Path, tree: ast.Module, checked: set[Path]
) -> None:
    """Refuse a module that ``module_imports`` refuses, or one it imports.

    A module imported from under ``FOLLOWED_IMPORTS`` is read by the same
    rules, with the package ``__init__`` files its import runs, as
    ``import_sources`` finds them.
    """
    pending = [(path, tree)]
    while pending:
        path, tree = pending.pop()
        if path in checked:
            continue
        checked.add(path)
        followed = module_imports(tree)
        if followed is None:
            relative = relative_path(package, path)
            raise ValueError(f"Unread module code in {relative}")
        names = defaultdict(set)
        for item in tree.body:
            if isinstance(item, ast.ImportFrom) and item.module in followed:
                names[item.module].update(alias.name for alias in item.names)
        for module in followed:
            for source in import_sources(package, module, names[module]):
                pending.append((source, ast.parse(source.read_bytes())))


def class_members(cls: ast.ClassDef) -> list[str] | None:
    """Members of an Enum class body that holds only literal assignments.

    The body holds a leading docstring, ``pass`` and single assignments of
    distinct string or integer literals to public names, each named once.
    Methods are refused: a decorator can make one a member, and creation
    hooks such as ``__init__`` can add or drop members. An equal value would
    make an alias, which the engine's ``Enum.encode`` does not accept.
    """
    members = []
    values = []
    for index, item in enumerate(cls.body):
        if (
            index == 0
            and isinstance(item, ast.Expr)
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        ) or isinstance(item, ast.Pass):
            continue
        if not (
            isinstance(item, ast.Assign)
            and len(item.targets) == 1
            and isinstance(item.targets[0], ast.Name)
            and isinstance(item.value, ast.Constant)
            and type(item.value.value) in (str, int)
        ):
            return None
        members.append(item.targets[0].id)
        values.append(item.value.value)
    # Enum itself refuses a member named ``mro``.
    if (
        not members
        or any(name.startswith("_") or name == "mro" for name in members)
        or len(set(members)) < len(members)
        or len(set(values)) < len(values)
    ):
        return None
    return members


def plain_variable_body(variable: ast.ClassDef) -> bool:
    """Whether a variable's body holds only engine attributes and formulas.

    That is a leading docstring, single assignments to names in
    ``ENGINE_ATTRIBUTES``, and formula functions with no decorators. Any
    other binding could override one of ``Variable``'s methods, such as
    ``set``, which the engine calls to read ``value_type``,
    ``possible_values`` and ``default_value``. The engine refuses a name it
    does not read, but an override can remove its own name first.
    """
    return all(
        (
            index == 0
            and isinstance(item, ast.Expr)
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        )
        or (
            isinstance(item, ast.Assign)
            and len(item.targets) == 1
            and isinstance(item.targets[0], ast.Name)
            and item.targets[0].id in ENGINE_ATTRIBUTES
        )
        or (
            isinstance(item, ast.FunctionDef)
            and item.name.startswith("formula")
            and not item.decorator_list
        )
        for index, item in enumerate(variable.body)
    )


def enum_members(tree: ast.Module, variable: ast.ClassDef) -> list[str] | None:
    """Member names of the Enum class an enum variable names in its module.

    Returns None, so that an input whose members cannot be read is refused
    rather than left open, unless:

    - the variable is its name's one binding in the module, subclasses
      ``Variable`` alone with no decorators or keywords, meets
      ``plain_variable_body``, and binds ``value_type``, ``possible_values``
      and ``default_value`` once each, by plain assignment, to ``Enum``, a
      class name and one of that class's members;
    - the class name has one binding anywhere in the module: a top-level
      class, before the variable, that subclasses ``Enum`` alone, with no
      decorators, keywords or type parameters;
    - the module's own code meets ``static_module``, and outside the class
      reads it only as ``possible_values``, a member or ``encode``;
    - the class body meets ``class_members``.

    Code in another module that changes the class is beyond a read of this
    one; the pinned-engine oracle checks the release as the engine loads it.
    """
    attrs = ("value_type", "possible_values", "default_value")
    value_type, possible, default = (
        plain_attribute(variable, attr) for attr in attrs
    )
    if not (
        binding_sites(tree, variable.name) == [variable]
        and [expression(base) for base in variable.bases] == ["Variable"]
        and not variable.keywords
        and not variable.decorator_list
        and plain_variable_body(variable)
        and isinstance(value_type, ast.Name)
        and value_type.id == "Enum"
        and isinstance(possible, ast.Name)
        and isinstance(default, ast.Attribute)
        and isinstance(default.value, ast.Name)
        and default.value.id == possible.id
    ):
        return None
    sites = binding_sites(tree, possible.id)
    cls = sites[0] if len(sites) == 1 else None
    if not (
        isinstance(cls, ast.ClassDef)
        and any(cls is item for item in tree.body)
        and tree.body.index(cls) < tree.body.index(variable)
        and [expression(base) for base in cls.bases] == ["Enum"]
        and not cls.keywords
        and not cls.decorator_list
        and not getattr(cls, "type_params", None)
        and static_module(tree, cls)
    ):
        return None
    members = class_members(cls)
    if members is None or default.attr not in members:
        return None
    reads = {id(possible), id(default.value)} | {
        id(item.value)
        for item in ast.walk(tree)
        if isinstance(item, ast.Attribute)
        and isinstance(item.ctx, ast.Load)
        and isinstance(item.value, ast.Name)
        and item.value.id == possible.id
        and (item.attr in members or item.attr in ENUM_API)
    }
    if any(
        isinstance(item, ast.Name)
        and item.id == possible.id
        and id(item) not in reads
        for item in ast.walk(tree)
    ):
        return None
    return members


def plain_variable(
    tree: ast.Module, variable: ast.ClassDef
) -> dict[str, ast.expr]:
    """The values a variable binds to the attributes in ``READ_ATTRIBUTES``.

    The engine copies the class's own namespace, without dunder names, and
    reads each attribute from that copy through the variable's ``set``
    method. So the variable must be its name's one binding in the module,
    subclass ``Variable`` alone with no decorators, keywords or type
    parameters, and meet ``plain_variable_body``, which keeps ``set`` the
    engine's; and it must bind each such attribute it binds by one plain
    assignment. Otherwise this refuses.
    """
    if not (
        binding_sites(tree, variable.name) == [variable]
        and [expression(base) for base in variable.bases] == ["Variable"]
        and not variable.keywords
        and not variable.decorator_list
        and not getattr(variable, "type_params", None)
        and plain_variable_body(variable)
    ):
        raise ValueError(f"Unread variable {variable.name}")
    attrs = {}
    for attr in READ_ATTRIBUTES:
        if binding_sites(variable, attr):
            value = plain_attribute(variable, attr)
            if value is None:
                raise ValueError(f"Unresolved {attr} for {variable.name}")
            attrs[attr] = value
    return attrs


def variable_attributes(
    tree: ast.Module, variable: ast.ClassDef
) -> dict[str, Any]:
    """The value_type, entity, period and default a variable's record names.

    The record keeps the spelling of each name, so each must be one the
    module never binds. The primitive types are builtins, which the model
    API's star import does not rebind; it binds Enum, the entities and the
    periods under these spellings. A primitive default is a literal of a
    type in ``DEFAULT_TYPES``, an int for a float variable only when
    ``exact_float`` holds, and an enum variable's default a member of the
    class whose members ``enum_members`` reads. Otherwise, or when
    ``plain_variable`` refuses, this refuses.
    """
    attrs = plain_variable(tree, variable)
    spelled = {}
    for attr in ("value_type", "entity", "definition_period"):
        value = attrs.get(attr)
        if not (
            isinstance(value, ast.Name) and not binding_sites(tree, value.id)
        ):
            raise ValueError(f"Unresolved {attr} for {variable.name}")
        spelled[attr] = value.id
    dtype = spelled["value_type"]
    default = attrs.get("default_value")
    record = {
        "entity": spelled["entity"],
        "period": spelled["definition_period"],
        "value_type": dtype,
        "default_origin": "core type" if default is None else "explicit",
    }
    if dtype == "Enum":
        members = enum_members(tree, variable)
        if members is None:
            raise ValueError(f"Unresolved enum members for {variable.name}")
        # enum_members admits only a default that names one of the members.
        return record | {"default": default.attr, "enum_members": members}
    if dtype not in TYPE_DEFAULTS:
        raise ValueError(f"Unresolved value_type for {variable.name}")
    if default is None:
        return record | {"default": TYPE_DEFAULTS[dtype]}
    try:
        value = ast.literal_eval(default)
    except (ValueError, TypeError):
        value = None
    if type(value) not in DEFAULT_TYPES[dtype]:
        raise ValueError(f"Unresolved default for {variable.name}")
    if dtype == "float" and type(value) is int and not exact_float(value):
        raise ValueError(f"Unresolved default for {variable.name}")
    return record | {"default": value}


def exact_float(value: int) -> bool:
    """Whether ``float(value)``, which the engine applies to an int default
    of a float variable, gives back the same number; an int too large for
    a float raises OverflowError there, so it does not."""
    try:
        return float(value) == value
    except OverflowError:
        return False


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


def variable_files(directory: Path) -> list[Path]:
    """The files the engine's directory walk loads as variables, in order.

    ``add_variables_from_directory`` takes each folder's ``*.py`` and then
    its ``*/`` glob matches, which skip names with a leading dot, and reads
    a folder's ``__init__.py`` as metadata, not as variables.
    """
    files = [
        Path(name)
        for name in glob.glob(os.path.join(directory, "*.py"))
        if os.path.basename(name) != "__init__.py"
    ]
    for subdirectory in glob.glob(os.path.join(directory, "*/")):
        files.extend(variable_files(Path(subdirectory)))
    return files


def parse_variables(
    package: Path, boundaries: set[str]
) -> dict[str, dict[str, Any]]:
    """Read only the SSI closure, using variable filenames as the index.

    The index holds the files the engine's walk loads, by stem, leaving out
    helper modules whose names start with an underscore. A dependency whose
    stem names more than one file refuses, since the reader could not say
    which the engine's variable comes from.
    """
    # Folder listings the import system cached may predate this read.
    importlib.machinery.PathFinder.invalidate_caches()
    files = variable_files(package / "variables")
    index = defaultdict(list)
    for path in files:
        if not path.name.startswith("_"):
            index[path.stem].append(path)
    roots = sorted(
        path for path in files if path.is_relative_to(package / SSI_VARIABLES)
    )
    records = {}
    helpers = {}
    # Federal helper functions are also part of the static dependency closure.
    for path in roots:
        for node in ast.parse(path.read_bytes()).body:
            if isinstance(node, ast.FunctionDef):
                helpers[node.name] = node
    pending = list(roots)
    visited = set()
    checked = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        tree = ast.parse(path.read_bytes())
        check_module(package, path, tree, checked)
        classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and any(expression(base) == "Variable" for base in node.bases)
        ]
        # Several classes per file are supported, as in the invented fixtures.
        names = set(index) | set(records) | {node.name for node in classes}
        for node in classes:
            # An annotated, aliased, repeated or stored binding, an override
            # of set, or a module that rebinds a spelled name, as
            # ``float = Enum`` does, could give the engine an attribute
            # other than the one recorded.
            attrs = plain_variable(tree, node)
            fields = variable_attributes(tree, node)
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
                **fields,
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
            if node.name not in boundaries:
                for name in sorted(dependencies & set(index)):
                    if len(index[name]) > 1:
                        raise ValueError(
                            f"Dependency {name} of {node.name} names more "
                            "than one file"
                        )
                pending.extend(
                    index[name][0]
                    for name in dependencies
                    if name in index and name not in records
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
        for path in variable_files(package / "variables/gov/states")
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
