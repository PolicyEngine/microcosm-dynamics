"""Check OP1's slots drawing from ``DirectRNGStreams`` (design §§2.1, 5.4).

The coordinator's ruling of 24 October 2026 put the substitution in OP1's
harness wrapper: the sealed loop builds its registry (``engine/loop.py:217``)
and places it on each period's context (``:292``), and each OP1 slot receives
that context with ``DirectRNGStreams`` in its place. Duck typing is safe only
while the two classes share a public surface and no sealed code checks the
registry's type, so this module pins both, then checks the projection itself.

The AST scan reads ``src/populace_dynamics/`` outside ``open_population/``.
Specific checks name each type check they find; under them a catch-all
reports every other mention of the class, or of its name or module as text,
outside imports, docstrings, ``__all__``, annotations and construction. The
evidence report's §6 lists what it cannot see.
The project's data-access record keeps two modules out of automated reads,
and the scan also skips the depletion-cut modules, so that what it reads does
not depend on who runs it. It drops all of them by path before anything opens
them; a fresh-process run shows a projection imports none of them. Every
message names a module path, line number and node kind only, never source
text or literal values.
"""

from __future__ import annotations

import ast
import dataclasses
import fnmatch
import hashlib
import inspect
import json
import os
import subprocess
import sys
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass, replace
from functools import partial
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.baselines.fertility import AsfrFertilityStep
from populace_dynamics.engine import loop as engine_loop
from populace_dynamics.engine import rng as engine_rng
from populace_dynamics.engine.loop import PeriodContext, PeriodModules
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import (
    AgeSexMortalityModel,
    advance_age,
    apply_mortality,
)
from populace_dynamics.mortality_observer import observe_mortality
from populace_dynamics.open_population import exits
from populace_dynamics.open_population.errors import IdOrStreamCollision
from populace_dynamics.open_population.exits import no_marital_transitions
from populace_dynamics.open_population.gates import GateRunRequest, run_gate
from populace_dynamics.open_population.harness import (
    RNG_STREAM_MODES,
    SEALED_REGISTRY_REFUSAL,
    ProductionRequest,
    _AdapterStreams,
    run_production,
)
from populace_dynamics.open_population.streams import DirectRNGStreams
from populace_dynamics.person_identity import PersonIdentity, PersonIdentityMap

ROOT = Path(__file__).resolve().parents[2]
START = 2025
DIRECT_CLASS = "populace_dynamics.open_population.streams.DirectRNGStreams"
REGISTRY_CLASS = "populace_dynamics.engine.rng.ProjectionRNGRegistry"

# ---------------------------------------------------------------------------
# Condition 2, part 1: the two classes share the registry's public surface.
# ---------------------------------------------------------------------------

EXPECTED_FIELDS = ("draw_index", "n_periods")
EXPECTED_MEMBERS = frozenset(
    {
        "draw_seed",
        "seed_sequence",
        "generator",
        "child_generator",
        "tagged_generator",
        "tagged_child_generator",
        "person_generator",
    }
)


def _field_surface(cls):
    """Describe each dataclass field as a caller sees it."""
    return tuple(
        (
            field.name,
            field.type,
            field.default,
            field.default_factory,
            field.init,
            field.kw_only,
        )
        for field in dataclasses.fields(cls)
    )


def _member_surface(cls):
    """Describe every public class member by kind and signature."""
    surface = {}
    for name in dir(cls):
        if name.startswith("_"):
            continue
        member = inspect.getattr_static(cls, name)
        if isinstance(member, property):
            surface[name] = (
                "property",
                inspect.signature(member.fget),
                member.fset is None,
                member.fdel is None,
            )
        elif isinstance(member, staticmethod | classmethod):
            surface[name] = (
                type(member).__name__,
                inspect.signature(member.__func__),
            )
        elif inspect.isfunction(member):
            surface[name] = ("method", inspect.signature(member))
        else:
            surface[name] = ("attribute", type(member))
    return surface


def _dataclass_parameters(cls):
    params = cls.__dataclass_params__
    return {
        name: getattr(params, name)
        for name in ("init", "repr", "eq", "order", "unsafe_hash", "frozen")
    }


def test_direct_streams_share_the_registry_public_surface():
    """Every public registry member exists on the direct class (§2.1).

    The surface is derived by introspection, so a member added to the
    registry fails here until the direct class has it with the same
    signature. The pinned names make additions and removals loud as well.
    """
    registry_fields = _field_surface(ProjectionRNGRegistry)
    registry_members = _member_surface(ProjectionRNGRegistry)
    assert tuple(field[0] for field in registry_fields) == EXPECTED_FIELDS
    assert set(registry_members) == EXPECTED_MEMBERS
    assert _field_surface(DirectRNGStreams) == registry_fields
    direct_members = _member_surface(DirectRNGStreams)
    for name, description in registry_members.items():
        assert name in direct_members, name
        assert direct_members[name] == description, name
    assert set(direct_members) == set(registry_members)
    assert inspect.signature(DirectRNGStreams) == inspect.signature(
        ProjectionRNGRegistry
    )
    assert _dataclass_parameters(DirectRNGStreams) == _dataclass_parameters(
        ProjectionRNGRegistry
    )
    for streams in (ProjectionRNGRegistry(3, 7), DirectRNGStreams(3, 7)):
        public = {name for name in vars(streams) if not name.startswith("_")}
        assert public == set(EXPECTED_FIELDS)


def test_direct_streams_are_not_a_registry_subclass():
    """Condition 1: no registry subclass, and no sealed attribute patched."""
    assert ProjectionRNGRegistry not in DirectRNGStreams.__mro__
    assert DirectRNGStreams.__module__ == (
        "populace_dynamics.open_population.streams"
    )


# ---------------------------------------------------------------------------
# Condition 2, part 2: no sealed code checks the registry's type.
# ---------------------------------------------------------------------------

REGISTRY_MODULE = "populace_dynamics.engine.rng"
REGISTRY_NAME = "ProjectionRNGRegistry"
OWN_PACKAGE = Path("src/populace_dynamics/open_population")
# The project's data-access record keeps these two modules out of automated
# reads. The scan skips them by path, before anything opens them; the
# fresh-process test below shows a projection imports neither.
CLOSED_MODULES = (
    Path("src/populace_dynamics/estimates/adjusted_poverty.py"),
    Path("src/populace_dynamics/uniform_cut_track_u/rows.py"),
)
# The scan also skips the depletion-cut modules by path, so that its input
# does not depend on who runs it. The pattern decides; the list pins what it
# matches today, so a new match comes back for a decision.
EXCLUDED_PATTERNS = ("src/populace_dynamics/bridge/depletion_cut*.py",)
PATTERN_EXCLUDED_MODULES = (
    Path("src/populace_dynamics/bridge/depletion_cut.py"),
    Path("src/populace_dynamics/bridge/depletion_cut_population.py"),
    Path("src/populace_dynamics/bridge/depletion_cut_population_child.py"),
)
# Private names that exist on only one class: probing for one tells the
# classes apart without a type check.
PROBE_NAMES = frozenset(
    name
    for name in set(dir(ProjectionRNGRegistry)) ^ set(dir(DirectRNGStreams))
    if name.startswith("_") and not name.startswith("__")
) | {"_root"}
_TYPE_CHECK_CALLS = frozenset({"isinstance", "issubclass"})
_DUNDER_CHECKS = frozenset({"__instancecheck__", "__subclasscheck__"})
_NAME_ATTRIBUTES = frozenset({"__name__", "__qualname__"})
_CONTAINER_CALLS = frozenset({"tuple", "list", "set", "frozenset", "dict"})
_LISTING_CALLS = frozenset({"append", "extend"})
# The nodes that can bind a name; binding revisits only these.
_BINDING_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.NamedExpr,
    ast.For,
    ast.AsyncFor,
    ast.comprehension,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
)


class ScanError(AssertionError):
    """A scanned module could not be read; the message carries no source."""


@dataclass(frozen=True, order=True)
class ScanHit:
    """One type check on the registry, located without its source text."""

    path: str
    line: int
    kind: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.kind}"


@dataclass(frozen=True)
class ScanSource:
    """A module to scan: its dotted name, display path and text."""

    module: str
    path: str
    text: str
    is_package: bool = False


def describe(hits: Iterable[ScanHit]) -> str:
    """Format hits for an assertion message: paths, lines and kinds only."""
    return "\n".join(str(hit) for hit in sorted(hits)) or "(no hits)"


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_type_call(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "type"
        and len(node.args) == 1
    )


def _static_text(node: ast.expr) -> str | None:
    """Return the text a string expression holds before run time, if any.

    The parser already joins adjacent literals and decodes escapes; this
    also folds ``+`` and f-strings whose parts are all literals. Bytes are
    read as Latin-1, so an ASCII name matches in either.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        if isinstance(node.value, bytes):
            return node.value.decode("latin-1")
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_text(node.left)
        right = _static_text(node.right)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                if value.conversion != -1 or value.format_spec is not None:
                    return None
                value = value.value
            text = _static_text(value)
            if text is None:
                return None
            parts.append(text)
        return "".join(parts)
    return None


def _is_all(target: ast.expr) -> bool:
    return isinstance(target, ast.Name) and target.id == "__all__"


def _lists_names(node: ast.Call) -> bool:
    """Return whether a call is ``__all__.append`` or ``__all__.extend``."""
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in _LISTING_CALLS
        and _is_all(node.func.value)
    )


def _registers(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a bare ``register`` decorator dispatches on a hint."""
    return any(
        (isinstance(decorator, ast.Attribute) and decorator.attr == "register")
        or (isinstance(decorator, ast.Name) and decorator.id == "register")
        for decorator in node.decorator_list
    )


class _ModuleBindings:
    """Resolve, flow-insensitively, what a module binds to the registry.

    Five kinds of binding are tracked: modules; the class itself;
    containers that may hold it (tuples, unions, mappings and anything read
    or rebuilt from them); strings that hold its name; and aliases of
    ``isinstance`` and ``issubclass``. Over-approximation is deliberate: a
    binding anywhere in the module counts everywhere in it, an attribute
    counts wherever a name spelled like it is bound, a loop over class info
    binds its variable to the class, and any name or attribute spelled
    exactly ``ProjectionRNGRegistry`` counts, whatever it came from.
    """

    def __init__(self, source: ScanSource, exports: set[tuple[str, str]]):
        self.source = source
        self.exports = exports
        self.package = (
            source.module
            if source.is_package
            else source.module.rpartition(".")[0]
        )
        self.modules: dict[str, str] = {}
        self.classes: set[str] = set()
        self.containers: set[str] = set()
        self.names: set[str] = set()
        self.checkers: dict[str, str] = {}

    def _from_base(self, node: ast.ImportFrom) -> str:
        if not node.level:
            return node.module or ""
        parts = self.package.split(".")
        if node.level > 1:
            parts = parts[: len(parts) - (node.level - 1)]
        base = ".".join(parts)
        return f"{base}.{node.module}" if node.module else base

    def module_path(self, node: ast.expr) -> str | None:
        """Return the dotted module a name or attribute chain denotes."""
        if isinstance(node, ast.Name):
            return self.modules.get(node.id)
        if isinstance(node, ast.Attribute):
            base = self.module_path(node.value)
            return f"{base}.{node.attr}" if base else None
        return None

    def is_registry(self, node: ast.expr) -> bool:
        """Return whether ``node`` denotes the registry class itself."""
        if isinstance(node, ast.Name):
            return node.id in self.classes or node.id == REGISTRY_NAME
        if isinstance(node, ast.Attribute):
            if node.attr == REGISTRY_NAME or node.attr in self.classes:
                return True
            if (
                node.attr == "__class__"
                and isinstance(node.value, ast.Call)
                and self.is_registry(node.value.func)
            ):
                return True
            base = self.module_path(node.value)
            return base is not None and (base, node.attr) in self.exports
        if isinstance(node, ast.NamedExpr):
            return self.is_registry(node.value)
        if isinstance(node, ast.Call):
            if _is_type_call(node) and isinstance(node.args[0], ast.Call):
                return self.is_registry(node.args[0].func)
            if (
                _call_name(node.func) == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                name = node.args[1].value
                base = self.module_path(node.args[0])
                return name == REGISTRY_NAME or (
                    base is not None and (base, name) in self.exports
                )
        return False

    def _any_part(self, node: ast.expr, test) -> bool:
        """Apply ``test`` to ``node`` and to each part it holds or picks."""
        if test(node):
            return True
        if isinstance(node, ast.Tuple | ast.List | ast.Set):
            parts = node.elts
        elif isinstance(node, ast.Dict):
            parts = [item for item in (*node.keys, *node.values) if item]
        elif isinstance(node, ast.Starred | ast.NamedExpr | ast.Subscript):
            parts = [node.value]
        elif isinstance(node, ast.IfExp):
            parts = [node.body, node.orelse]
        elif isinstance(node, ast.BoolOp):
            parts = node.values
        else:
            return False
        return any(self._any_part(part, test) for part in parts)

    def _class_part(self, node: ast.expr) -> bool:
        if self.is_registry(node):
            return True
        if isinstance(node, ast.Name):
            return node.id in self.containers
        if isinstance(node, ast.Attribute):
            return node.attr in self.containers
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, ast.BitOr | ast.Add
        ):
            # A union, or class-info tuples joined with "+".
            return self.contains_registry(node.left) or self.contains_registry(
                node.right
            )
        if isinstance(node, ast.Subscript):
            # Union[int, cls] holds the class in its subscript.
            return self.contains_registry(node.slice)
        if isinstance(node, ast.Call):
            # Class info read or rebuilt: KINDS.get(key), tuple(KINDS).
            if isinstance(node.func, ast.Attribute) and self.contains_registry(
                node.func.value
            ):
                return True
            return _call_name(node.func) in _CONTAINER_CALLS and any(
                self.contains_registry(item) for item in node.args
            )
        return False

    def contains_registry(self, node: ast.expr) -> bool:
        """Return whether a class-info expression may include the registry."""
        return self._any_part(node, self._class_part)

    def _name_part(self, node: ast.expr) -> bool:
        text = _static_text(node)
        if text is not None:
            return REGISTRY_NAME in text
        if isinstance(node, ast.Name):
            return node.id in self.names
        if isinstance(node, ast.Attribute):
            return node.attr in self.names or (
                node.attr in _NAME_ATTRIBUTES and self.is_registry(node.value)
            )
        return False

    def names_registry(self, node: ast.expr) -> bool:
        """Return whether ``node`` may hold the class's name as text."""
        return self._any_part(node, self._name_part)

    def _module_part(self, node: ast.expr) -> bool:
        text = _static_text(node)
        if text is not None:
            return REGISTRY_MODULE in text
        if isinstance(node, ast.Attribute) and node.attr == "__name__":
            node = node.value
        return self.module_path(node) == REGISTRY_MODULE

    def names_module(self, node: ast.expr) -> bool:
        """Return whether ``node`` may denote the registry's module."""
        return self._any_part(node, self._module_part)

    def checker(self, node: ast.expr) -> str | None:
        """Name the type check a callee denotes, through any alias."""
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        else:
            return None
        return name if name in _TYPE_CHECK_CALLS else self.checkers.get(name)

    def _bind(self, name: str, value: ast.expr, module: bool = True) -> None:
        if self.is_registry(value):
            self.classes.add(name)
        elif self.contains_registry(value):
            self.containers.add(name)
        elif self.names_registry(value):
            self.names.add(name)
        elif (checker := self.checker(value)) is not None:
            self.checkers.setdefault(name, checker)
        elif module and (path := self.module_path(value)) is not None:
            # First binding wins, so a cycle such as ``a = b.c; b = a``
            # cannot grow a path forever: each pass only adds names.
            self.modules.setdefault(name, path)

    def _bind_targets(self, target: ast.expr, value: ast.expr) -> None:
        if isinstance(target, ast.Name):
            self._bind(target.id, value)
        elif isinstance(target, ast.Attribute):
            self._bind(target.attr, value, module=False)
        elif isinstance(target, ast.Subscript):
            # TABLE[key] = cls puts class info in TABLE.
            base = target.value
            if isinstance(base, ast.Name | ast.Attribute):
                name = base.id if isinstance(base, ast.Name) else base.attr
                if self.contains_registry(value):
                    self.containers.add(name)
                elif self.names_registry(value):
                    self.names.add(name)
        elif isinstance(target, ast.Tuple | ast.List):
            items = (*target.elts, *getattr(value, "elts", ()))
            if (
                isinstance(value, ast.Tuple | ast.List)
                and len(target.elts) == len(value.elts)
                and not any(isinstance(item, ast.Starred) for item in items)
            ):
                for item, item_value in zip(
                    target.elts, value.elts, strict=True
                ):
                    self._bind_targets(item, item_value)
            else:
                # Any other unpacking: each target may take any part.
                for item in target.elts:
                    if isinstance(item, ast.Starred):
                        item = item.value
                    self._bind_targets(item, value)
        elif isinstance(target, ast.Starred):
            self._bind_targets(target.value, value)

    def _bind_loop(self, target: ast.expr) -> None:
        """Bind a loop variable that iterates over class info to the class."""
        if isinstance(target, ast.Name):
            self.classes.add(target.id)
        elif isinstance(target, ast.Attribute):
            self.classes.add(target.attr)
        elif isinstance(target, ast.Starred):
            self._bind_loop(target.value)
        elif isinstance(target, ast.Tuple | ast.List):
            for item in target.elts:
                self._bind_loop(item)

    def _visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    self.modules.setdefault(alias.asname, alias.name)
                else:
                    top = alias.name.split(".")[0]
                    self.modules.setdefault(top, top)
        elif isinstance(node, ast.ImportFrom):
            base = self._from_base(node)
            for alias in node.names:
                if alias.name == "*":
                    self.classes.update(
                        name for module, name in self.exports if module == base
                    )
                    continue
                local = alias.asname or alias.name
                if (
                    alias.name == REGISTRY_NAME
                    or (base, alias.name) in self.exports
                ):
                    self.classes.add(local)
                elif alias.name in _TYPE_CHECK_CALLS:
                    self.checkers.setdefault(local, alias.name)
                else:
                    self.modules.setdefault(local, f"{base}.{alias.name}")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                self._bind_targets(target, node.value)
        elif isinstance(node, ast.AnnAssign | ast.NamedExpr | ast.AugAssign):
            if node.value is not None:
                self._bind_targets(node.target, node.value)
        elif isinstance(node, ast.For | ast.AsyncFor | ast.comprehension):
            if self.contains_registry(node.iter):
                self._bind_loop(node.target)
        elif isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
        ):
            arguments = node.args
            positional = [*arguments.posonlyargs, *arguments.args]
            defaults = list(arguments.defaults)
            pairs = list(
                zip(
                    positional[len(positional) - len(defaults) :],
                    defaults,
                    strict=True,
                )
            )
            pairs += [
                (argument, default)
                for argument, default in zip(
                    arguments.kwonlyargs, arguments.kw_defaults, strict=True
                )
                if default is not None
            ]
            for argument, default in pairs:
                self._bind(argument.arg, default, module=False)

    def _state(self) -> tuple:
        return (
            dict(self.modules),
            set(self.classes),
            set(self.containers),
            set(self.names),
            dict(self.checkers),
        )

    def bind(self, nodes: list[ast.AST]) -> None:
        """Bind to a fixed point, so chained aliases resolve in any order.

        ``nodes`` are the module's binding nodes. Bindings only accumulate,
        over the module's finitely many names, so the loop ends.
        """
        while True:
            before = self._state()
            for node in nodes:
                self._visit(node)
            if before == self._state():
                return

    def dispatch_annotations(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[ast.expr]:
        """Return the hints a ``register`` decorator may dispatch on.

        A string hint is parsed as the expression it names, so an alias in
        quotes counts too.
        """
        if not _registers(node):
            return []
        found = []
        for argument in (*node.args.posonlyargs, *node.args.args):
            hint = argument.annotation
            if hint is None:
                continue
            text = _static_text(hint)
            if text is not None:
                try:
                    hint_value = ast.parse(text, mode="eval").body
                except (SyntaxError, ValueError):
                    hint_value = hint
            else:
                hint_value = hint
            if self.contains_registry(hint_value) or self.names_registry(hint):
                found.append(hint)
        return found

    def _kind(self, node: ast.AST) -> str | None:
        """Name the specific check ``node`` makes, if it makes one."""
        if isinstance(node, ast.Call):
            checker = self.checker(node.func)
            if (
                checker is not None
                and len(node.args) >= 2
                and self.contains_registry(node.args[1])
            ):
                return checker
            name = _call_name(node.func)
            if (
                name in _DUNDER_CHECKS
                and isinstance(node.func, ast.Attribute)
                and (
                    self.is_registry(node.func.value)
                    or any(map(self.contains_registry, node.args[:1]))
                )
            ):
                return "dunder-check"
            if (
                name == "register"
                and node.args
                and self.contains_registry(node.args[0])
            ):
                return "dispatch-register"
        elif isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            if any(self.contains_registry(item) for item in operands):
                if any(_is_type_call(item) for item in operands):
                    return "type-compare"
                if any(
                    isinstance(item, ast.Attribute)
                    and item.attr == "__class__"
                    for item in operands
                ):
                    return "__class__-compare"
                return "class-compare"
            if any(self.names_registry(item) for item in operands):
                return "name-compare"
            if any(self.names_module(item) for item in operands):
                return "module-compare"
        elif isinstance(node, ast.MatchValue):
            # case rng.ProjectionRNGRegistry: compares the subject by ==.
            if self.contains_registry(node.value):
                return "class-compare"
            if self.names_registry(node.value):
                return "name-compare"
            if self.names_module(node.value):
                return "module-compare"
        elif isinstance(node, ast.MatchClass):
            if self.contains_registry(node.cls):
                return "match-class"
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if self.dispatch_annotations(node):
                return "dispatch-annotation"
        elif isinstance(node, ast.Attribute):
            if node.attr in PROBE_NAMES and self.source.module != (
                REGISTRY_MODULE
            ):
                return "private-member-probe"
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str) and node.value in PROBE_NAMES:
                return "private-member-probe"
        return None

    def _mention(self, node: ast.expr, listing: bool) -> str | None:
        """Name what a node outside every specific check says of the class.

        A reference to the class or to class info, a string holding the
        class's name and a string holding its module's name each count.
        """
        if self.is_registry(node) or (
            isinstance(node, ast.Name | ast.Attribute)
            and self._class_part(node)
        ):
            return "class-reference"
        text = None if listing else _static_text(node)
        if text is not None and REGISTRY_NAME in text:
            return "class-name-string"
        if text is not None and REGISTRY_MODULE in text:
            return "module-name-string"
        return None

    def _children(self, node: ast.AST) -> Iterable[tuple[ast.AST, bool]]:
        """Yield the children a mention can hide in, and which list names.

        Annotations are skipped, except the hints a ``register`` decorator
        dispatches on; so is the callee of a construction. Strings inside
        an ``__all__`` listing are flagged as listing names.
        """
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            arguments = node.args
            yield from ((item, False) for item in node.decorator_list)
            yield from ((item, False) for item in arguments.defaults)
            yield from (
                (item, False) for item in arguments.kw_defaults if item
            )
            if _registers(node):
                yield from (
                    (argument.annotation, False)
                    for argument in (*arguments.posonlyargs, *arguments.args)
                    if argument.annotation is not None
                )
            yield from ((item, False) for item in node.body)
        elif isinstance(node, ast.Lambda):
            yield from ((item, False) for item in node.args.defaults)
            yield from (
                (item, False) for item in node.args.kw_defaults if item
            )
            yield node.body, False
        elif isinstance(node, ast.AnnAssign):
            yield node.target, False
            if node.value is not None:
                yield node.value, _is_all(node.target)
        elif isinstance(node, ast.Assign | ast.AugAssign):
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            yield from ((item, False) for item in targets)
            yield node.value, any(map(_is_all, targets))
        elif isinstance(node, ast.Call) and (
            self.is_registry(node.func) or _lists_names(node)
        ):
            listing = _lists_names(node)
            if listing:
                yield node.func, False
            yield from ((item, listing) for item in node.args)
            yield from ((item.value, listing) for item in node.keywords)
        else:
            yield from ((item, False) for item in ast.iter_child_nodes(node))

    def references(self, tree: ast.Module, claimed: set[int]) -> set[ScanHit]:
        """Report every other mention of the class outside a benign place.

        This is the catch-all under the specific checks: a reference to the
        class, or a string holding its name, counts wherever it is not
        benign. Benign places are imports, string statements (docstrings
        among them), ``__all__`` listings, annotations other than dispatch
        hints, and the callee of a construction. A node a specific check
        reported is skipped with everything under it. The walk keeps its
        own stack, so deep expressions cannot exhaust recursion.
        """
        found = set()
        stack: list[tuple[ast.AST, bool]] = [(tree, False)]
        while stack:
            node, listing = stack.pop()
            if id(node) in claimed or isinstance(
                node, ast.Import | ast.ImportFrom
            ):
                continue
            if (
                isinstance(node, ast.Expr)
                and _static_text(node.value) is not None
            ):
                continue
            if isinstance(node, ast.expr) and not isinstance(
                getattr(node, "ctx", None), ast.Store | ast.Del
            ):
                kind = self._mention(node, listing)
                if kind is not None:
                    found.add(ScanHit(self.source.path, node.lineno, kind))
                    continue
            stack.extend(
                (child, listing or listed)
                for child, listed in self._children(node)
            )
        return found

    def hits(self, tree: ast.Module) -> set[ScanHit]:
        """Report the specific checks, then every other mention."""
        found = set()
        claimed: set[int] = set()
        for node in ast.walk(tree):
            kind = self._kind(node)
            if kind is None:
                continue
            found.add(ScanHit(self.source.path, node.lineno, kind))
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                claimed.update(map(id, self.dispatch_annotations(node)))
            else:
                claimed.add(id(node))
        return found | self.references(tree, claimed)


def _parse(source: ScanSource) -> ast.Module:
    try:
        return ast.parse(source.text)
    except (SyntaxError, ValueError) as error:
        line = getattr(error, "lineno", None)
        raise ScanError(f"{source.path}:{line}: unparsable source") from None


def _inert(node: ast.AST) -> bool:
    """Return whether a literal container can matter to no check.

    A container of constants (tuples, lists, sets, dicts and signed
    numbers, nested) refers to nothing, so only its strings could matter;
    it is inert when none holds the class's name or its module's, and none
    is a probe name.
    """
    if not isinstance(node, ast.Tuple | ast.List | ast.Set | ast.Dict):
        return False
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, ast.Constant):
            text = _static_text(item)
            if text is not None and (
                REGISTRY_NAME in text
                or REGISTRY_MODULE in text
                or text in PROBE_NAMES
            ):
                return False
        elif isinstance(item, ast.Tuple | ast.List | ast.Set):
            stack.extend(item.elts)
        elif isinstance(item, ast.Dict):
            if any(key is None for key in item.keys):
                return False
            stack.extend((*item.keys, *item.values))
        elif isinstance(item, ast.UnaryOp):
            stack.append(item.operand)
        else:
            return False
    return True


def _prune(tree: ast.Module) -> ast.Module:
    """Replace each inert literal container with ``None``, in place.

    No check reports or binds anything from an inert container, so the
    hits are unchanged (a differential test pins that); the data modules'
    large tables stop costing time and memory.
    """
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        for field, value in ast.iter_fields(node):
            items = value if isinstance(value, list) else [value]
            for index, item in enumerate(items):
                if not isinstance(item, ast.AST):
                    continue
                if _inert(item):
                    stub = ast.copy_location(ast.Constant(None), item)
                    if isinstance(value, list):
                        value[index] = stub
                    else:
                        setattr(node, field, stub)
                else:
                    stack.append(item)
    return tree


def scan_sources(
    sources: Iterable[ScanSource], prune: bool = True
) -> tuple[ScanHit, ...]:
    """Find type checks on the registry across ``sources`` (condition 2).

    Every module is parsed. No text filter runs first, because the parser
    joins adjacent literals, decodes escapes and normalizes identifiers, so
    a module can spell the class without its text holding the name. Inert
    literal containers are pruned unless ``prune`` is false. Re-exports of
    the class are followed to a fixed point across modules.
    """
    sources = tuple(sources)
    trees = {
        source.path: _prune(_parse(source)) if prune else _parse(source)
        for source in sources
    }
    binders = {
        path: [
            node for node in ast.walk(tree) if isinstance(node, _BINDING_NODES)
        ]
        for path, tree in trees.items()
    }
    exports = {(REGISTRY_MODULE, REGISTRY_NAME)}
    while True:
        scopes = {}
        for source in sources:
            scope = _ModuleBindings(source, exports)
            scope.bind(binders[source.path])
            scopes[source.path] = scope
        found = {
            (scope.source.module, name)
            for scope in scopes.values()
            for name in scope.classes
        }
        if found <= exports:
            break
        exports |= found
    return tuple(
        sorted(
            hit
            for path, scope in scopes.items()
            for hit in scope.hits(trees[path])
        )
    )


def _read(path: Path, relative: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise ScanError(f"{relative.as_posix()}: not UTF-8") from None


def _excluded(relative: Path) -> bool:
    """Decide from the path alone whether the scan skips a module."""
    return relative in CLOSED_MODULES or any(
        fnmatch.fnmatchcase(relative.as_posix(), pattern)
        for pattern in EXCLUDED_PATTERNS
    )


def _walk(root: Path) -> Iterable[tuple[Path, Path, bool]]:
    """List ``.py`` paths under ``src/populace_dynamics/`` by name only.

    ``__pycache__`` folders and OP1's own package are pruned. Each path comes
    with whether ``_excluded`` drops it; nothing here opens or stats a file.
    """
    package = root / "src" / "populace_dynamics"
    own = root / OWN_PACKAGE
    for directory, subdirectories, files in os.walk(package):
        current = Path(directory)
        subdirectories[:] = sorted(
            name
            for name in subdirectories
            if name != "__pycache__" and current / name != own
        )
        for name in sorted(files):
            if name.endswith(".py"):
                path = current / name
                relative = path.relative_to(root)
                yield path, relative, _excluded(relative)


def excluded_paths(root: Path = ROOT) -> tuple[str, ...]:
    """Name the modules the scan skips, from directory listings alone."""
    return tuple(
        sorted(
            relative.as_posix() for _, relative, skip in _walk(root) if skip
        )
    )


def repository_sources(root: Path = ROOT) -> tuple[ScanSource, ...]:
    """Collect ``src/populace_dynamics/`` outside OP1's own package.

    ``__pycache__`` folders are pruned, and each excluded module is dropped
    by its path before anything opens, reads, parses, hashes or stats it.
    """
    sources = []
    for path, relative, skip in _walk(root):
        if skip:
            continue
        parts = path.relative_to(root / "src").with_suffix("").parts
        is_package = path.name == "__init__.py"
        sources.append(
            ScanSource(
                module=".".join(parts[:-1] if is_package else parts),
                path=relative.as_posix(),
                text=_read(path, relative),
                is_package=is_package,
            )
        )
    return tuple(sources)


# The exact set of type checks the scan finds in master's sealed code: one.
# It refuses the direct class loudly instead of diverging (pinned by the
# behaviour tests below), so an OP1 run that composes it must pass
# rng_streams="registry". A new hit, a moved line or a removed hit fails the
# scan test, so any such change to sealed code comes back for a decision.
KNOWN_SEALED_TYPE_CHECKS = frozenset(
    {
        ScanHit(
            "src/populace_dynamics/mortality_observer.py", 381, "type-compare"
        )
    }
)


def test_closed_module_exclusions_are_pinned_exactly():
    assert CLOSED_MODULES == (
        Path("src/populace_dynamics/estimates/adjusted_poverty.py"),
        Path("src/populace_dynamics/uniform_cut_track_u/rows.py"),
    )
    assert EXCLUDED_PATTERNS == (
        "src/populace_dynamics/bridge/depletion_cut*.py",
    )
    assert PATTERN_EXCLUDED_MODULES == (
        Path("src/populace_dynamics/bridge/depletion_cut.py"),
        Path("src/populace_dynamics/bridge/depletion_cut_population.py"),
        Path("src/populace_dynamics/bridge/depletion_cut_population_child.py"),
    )
    assert OWN_PACKAGE == Path("src/populace_dynamics/open_population")
    assert all(_excluded(path) for path in CLOSED_MODULES)
    assert all(_excluded(path) for path in PATTERN_EXCLUDED_MODULES)
    for neighbour in (
        "src/populace_dynamics/bridge/__init__.py",
        "src/populace_dynamics/bridge/depletion.py",
        "src/populace_dynamics/bridge/depletion_cut.pyc",
        "src/populace_dynamics/engine/depletion_cut.py",
        "src/populace_dynamics/estimates/adjusted_poverty_other.py",
    ):
        assert not _excluded(Path(neighbour)), neighbour


def test_the_tree_excludes_exactly_the_pinned_modules():
    """The pattern matches exactly the pinned list, by directory listing."""
    assert excluded_paths() == tuple(
        sorted(
            path.as_posix()
            for path in (*CLOSED_MODULES, *PATTERN_EXCLUDED_MODULES)
        )
    )


def test_sealed_code_holds_only_the_known_registry_type_check():
    """No sealed module checks the registry's type, except the pinned one.

    A new check in any reachable sealed module fails this test, by path,
    line and node kind, before the direct default could silently diverge.
    """
    sources = repository_sources()
    paths = {source.path for source in sources}
    assert not paths & set(excluded_paths())
    assert not paths & {
        path.as_posix()
        for path in (*CLOSED_MODULES, *PATTERN_EXCLUDED_MODULES)
    }
    assert not any(path.startswith(f"{OWN_PACKAGE}/") for path in paths)
    assert "src/populace_dynamics/engine/rng.py" in paths
    assert "src/populace_dynamics/baselines/asfr.py" in paths
    hits = scan_sources(sources)
    assert sorted(hits) == sorted(KNOWN_SEALED_TYPE_CHECKS), describe(hits)


_REGISTRY_IMPORT = (
    "from populace_dynamics.engine.rng import ProjectionRNGRegistry\n"
)
_IMPORT = "from populace_dynamics.engine.rng import ProjectionRNGRegistry"


def _check(expression, imports=_IMPORT):
    """Wrap one expression as an invented module; mark the expected line."""
    return f"{imports}\ndef f(x):\n    return {expression}  # check\n"


def _dispatch(hint, imports=_IMPORT):
    """Invent a single-dispatch registration whose hint is ``hint``."""
    return (
        f"from functools import singledispatch\n{imports}\n"
        "@singledispatch\ndef f(x):\n    return 0\n"
        f"@f.register\ndef _(x: {hint}):  # check\n    return 1\n"
    )


# Each invented module marks the line of its check with "# check". A line
# that binds the class or class info to a name ends "# alias" and adds a
# class-reference hit; a line that holds the class's name as text ends
# "# label" and adds a class-name-string hit.
MARKERS = {"# alias": "class-reference", "# label": "class-name-string"}
SPELLINGS = {
    "isinstance": (
        _check("isinstance(x, ProjectionRNGRegistry)"),
        "isinstance",
    ),
    "isinstance through an import alias": (
        _check("isinstance(x, X)", f"{_IMPORT} as X"),
        "isinstance",
    ),
    "isinstance with a tuple": (
        _check("isinstance(x, (int, ProjectionRNGRegistry))"),
        "isinstance",
    ),
    "isinstance with a union": (
        _check("isinstance(x, int | ProjectionRNGRegistry)"),
        "isinstance",
    ),
    "isinstance with typing.Union": (
        _check(
            "isinstance(x, typing.Union[int, ProjectionRNGRegistry])",
            f"{_IMPORT}\nimport typing",
        ),
        "isinstance",
    ),
    "builtins.isinstance": (
        _check(
            "builtins.isinstance(x, ProjectionRNGRegistry)",
            f"{_IMPORT}\nimport builtins",
        ),
        "isinstance",
    ),
    "isinstance bound to a name": (
        _check(
            "check(x, ProjectionRNGRegistry)", f"{_IMPORT}\ncheck = isinstance"
        ),
        "isinstance",
    ),
    "issubclass": (
        _check("issubclass(type(x), ProjectionRNGRegistry)"),
        "issubclass",
    ),
    "issubclass imported under another name": (
        _check(
            "check(type(x), ProjectionRNGRegistry)",
            f"{_IMPORT}\nfrom builtins import issubclass as check",
        ),
        "issubclass",
    ),
    "class-info tuple bound to a name": (
        _check(
            "isinstance(x, KINDS)",
            f"{_IMPORT}\nKINDS = (int, ProjectionRNGRegistry)  # alias",
        ),
        "isinstance",
    ),
    "union bound to a name": (
        _check(
            "isinstance(x, KINDS)",
            f"{_IMPORT}\nKINDS = int | ProjectionRNGRegistry  # alias",
        ),
        "isinstance",
    ),
    "class-info tuples joined with +": (
        _check("isinstance(x, (int,) + (ProjectionRNGRegistry,))"),
        "isinstance",
    ),
    "subscript of a literal": (
        _check("isinstance(x, (ProjectionRNGRegistry,)[0])"),
        "isinstance",
    ),
    "named expression": (
        _check("isinstance(x, kind := ProjectionRNGRegistry)"),
        "isinstance",
    ),
    "class attribute": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            class Holder:
                kind = ProjectionRNGRegistry  # alias
            def f(x):
                return isinstance(x, Holder.kind)  # check
        """),
        "isinstance",
    ),
    "loop over class info": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            def f(x):
                for kind in (int, ProjectionRNGRegistry):  # alias
                    if isinstance(x, kind):  # check
                        return True
                return False
        """),
        "isinstance",
    ),
    "identifier the parser normalizes": (
        # A fullwidth first letter, which the parser folds to "P" (NFKC).
        _check("isinstance(x, ＰrojectionRNGRegistry)"),
        "isinstance",
    ),
    "type is": (_check("type(x) is ProjectionRNGRegistry"), "type-compare"),
    "type is not": (
        _check("type(x) is not ProjectionRNGRegistry"),
        "type-compare",
    ),
    "type ==": (_check("type(x) == ProjectionRNGRegistry"), "type-compare"),
    "type !=": (_check("type(x) != ProjectionRNGRegistry"), "type-compare"),
    "type, reversed operands": (
        _check("ProjectionRNGRegistry is type(x)"),
        "type-compare",
    ),
    "type in a tuple": (
        _check("type(x) in (ProjectionRNGRegistry, int)"),
        "type-compare",
    ),
    "type in a chained comparison": (
        # One comparison whose first operator is "<".
        _check("0 < x.n_periods != type(x) is ProjectionRNGRegistry"),
        "type-compare",
    ),
    "__class__ is": (
        _check("x.__class__ is ProjectionRNGRegistry"),
        "__class__-compare",
    ),
    "__class__ ==": (
        _check("x.__class__ == ProjectionRNGRegistry"),
        "__class__-compare",
    ),
    "__class__ !=": (
        _check("x.__class__ != ProjectionRNGRegistry"),
        "__class__-compare",
    ),
    "module attribute": (
        _check(
            "isinstance(x, rng.ProjectionRNGRegistry)",
            "from populace_dynamics.engine import rng",
        ),
        "isinstance",
    ),
    "aliased module attribute": (
        _check(
            "type(x) is streams.ProjectionRNGRegistry",
            "from populace_dynamics.engine import rng as streams",
        ),
        "type-compare",
    ),
    "dotted module attribute": (
        textwrap.dedent("""
            import populace_dynamics.engine.rng
            def f(x):
                return isinstance(  # check
                    x, populace_dynamics.engine.rng.ProjectionRNGRegistry
                )
        """),
        "isinstance",
    ),
    "aliased dotted module": (
        _check(
            "x.__class__ == r.ProjectionRNGRegistry",
            "import populace_dynamics.engine.rng as r",
        ),
        "__class__-compare",
    ),
    "relative import": (
        _check(
            "isinstance(x, R)", "from .rng import ProjectionRNGRegistry as R"
        ),
        "isinstance",
    ),
    "chained local alias": (
        _check(
            "isinstance(x, S)",
            f"{_IMPORT}\nS = R  # alias\nR = ProjectionRNGRegistry  # alias",
        ),
        "isinstance",
    ),
    "type of an instance": (
        _check(
            "isinstance(x, T)",
            f"{_IMPORT}\nT = type(ProjectionRNGRegistry(0, 0))  # alias",
        ),
        "isinstance",
    ),
    "getattr on the module": (
        _check(
            "isinstance(x, getattr(rng, 'ProjectionRNGRegistry'))",
            "from populace_dynamics.engine import rng",
        ),
        "isinstance",
    ),
    "class name comparison": (
        _check("type(x).__name__ == 'ProjectionRNGRegistry'", ""),
        "name-compare",
    ),
    "class name in a tuple": (
        _check("type(x).__name__ in ('ProjectionRNGRegistry',)", ""),
        "name-compare",
    ),
    "class name attribute": (
        _check("type(x).__name__ == ProjectionRNGRegistry.__name__"),
        "name-compare",
    ),
    "escaped class name": (
        _check("type(x).__name__ == '\\x50rojectionRNGRegistry'", ""),
        "name-compare",
    ),
    "adjacent literals": (
        _check("type(x).__name__ == 'Projection' 'RNGRegistry'", ""),
        "name-compare",
    ),
    "concatenated literals": (
        _check("type(x).__qualname__ == 'Projection' + 'RNGRegistry'", ""),
        "name-compare",
    ),
    "class name bound to a name": (
        _check(
            "type(x).__name__ == LABEL",
            "LABEL = 'ProjectionRNGRegistry'  # label",
        ),
        "name-compare",
    ),
    "module name comparison": (
        _check("type(x).__module__ == 'populace_dynamics.engine.rng'", ""),
        "module-compare",
    ),
    "private-member probe": (
        _check("hasattr(x, '_period_sequence')", ""),
        "private-member-probe",
    ),
    "private member read": (
        textwrap.dedent("""
            def f(x):
                try:
                    return x._period_sequence is not None  # check
                except AttributeError:
                    return False
        """),
        "private-member-probe",
    ),
    "private member in a listing": (
        _check("'_period_sequence' in dir(x)", ""),
        "private-member-probe",
    ),
    "instance-check dunder": (
        _check("ProjectionRNGRegistry.__instancecheck__(x)"),
        "dunder-check",
    ),
    "subclass-check dunder through type": (
        _check("type.__subclasscheck__(ProjectionRNGRegistry, type(x))"),
        "dunder-check",
    ),
    "default argument": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            def f(x, cls=ProjectionRNGRegistry):  # alias
                return isinstance(x, cls)  # check
        """),
        "isinstance",
    ),
    "two-step type comparison": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            def f(x):
                kind = type(x)
                return kind is ProjectionRNGRegistry  # check
        """),
        "class-compare",
    ),
    "dictionary dispatch": (
        _check("{ProjectionRNGRegistry: True}.get(type(x), False)"),
        "class-reference",
    ),
    "match class pattern": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            def f(x):
                match x:
                    case ProjectionRNGRegistry():  # check
                        return 1
        """),
        "match-class",
    ),
    "match value pattern": (
        textwrap.dedent("""
            from populace_dynamics.engine import rng
            def f(x):
                match type(x):
                    case rng.ProjectionRNGRegistry:  # check
                        return 1
        """),
        "class-compare",
    ),
    "match on the class name": (
        textwrap.dedent("""
            def f(x):
                match type(x).__name__:
                    case "ProjectionRNGRegistry":  # check
                        return 1
        """),
        "name-compare",
    ),
    "single-dispatch registration": (
        textwrap.dedent("""
            from functools import singledispatch
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @singledispatch
            def f(x):
                return 0
            @f.register(ProjectionRNGRegistry)  # check
            def _(x):
                return 1
        """),
        "dispatch-register",
    ),
    "single-dispatch annotation": (
        _dispatch("ProjectionRNGRegistry"),
        "dispatch-annotation",
    ),
    "single-dispatch string annotation": (
        _dispatch("'ProjectionRNGRegistry'"),
        "dispatch-annotation",
    ),
    "single-dispatch string annotation through an alias": (
        _dispatch("'int | R'", f"{_IMPORT} as R"),
        "dispatch-annotation",
    ),
}


def _invented(text, module="populace_dynamics.engine.invented_case"):
    return ScanSource(module, f"invented/{module.rpartition('.')[2]}.py", text)


def _expected(text, kind):
    """The (line, kind) pairs an invented module's markers ask for."""
    expected = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.endswith("# check"):
            expected.append((number, kind))
        expected += [
            (number, marked)
            for marker, marked in MARKERS.items()
            if line.endswith(marker)
        ]
    return sorted(expected)


@pytest.mark.parametrize("spelling", tuple(SPELLINGS))
def test_scan_catches_every_spelling_of_a_registry_type_check(spelling):
    """Each spelling gives exactly the hits its markers ask for.

    That is one hit of its kind on its check line, plus one on each line
    that binds the class or holds its name.
    """
    text, kind = SPELLINGS[spelling]
    assert sum(line.endswith("# check") for line in text.splitlines()) == 1
    hits = scan_sources([_invented(text)])
    assert [(hit.line, hit.kind) for hit in hits] == _expected(
        text, kind
    ), describe(hits)


# Two spellings cannot run: a relative import needs a package, and the
# chained alias binds a name before the name it copies, to show the scan's
# bindings do not depend on order.
_NOT_RUN = frozenset({"relative import", "chained local alias"})


@pytest.mark.parametrize("spelling", sorted(set(SPELLINGS) - _NOT_RUN))
def test_every_spelling_tells_the_two_classes_apart(spelling):
    """Each invented check answers differently for the two classes.

    So every spelling is a working type check that the scan must catch,
    not a pattern that only looks like one. (Negated spellings answer
    false for the registry and true for the direct class.)
    """
    text, _ = SPELLINGS[spelling]
    namespace = {"__name__": "invented_case"}
    exec(compile(text, "invented_case.py", "exec"), namespace)
    outcomes = [
        bool(namespace["f"](cls(0, 2)))
        for cls in (ProjectionRNGRegistry, DirectRNGStreams)
    ]
    assert outcomes[0] != outcomes[1]


def test_scan_follows_re_exports_across_modules():
    """A module that never spells the class can still check its type."""
    package = "populace_dynamics.invented"
    sources = [
        ScanSource(
            f"{package}.reexport",
            "invented/reexport.py",
            "from populace_dynamics.engine.rng import "
            "ProjectionRNGRegistry as Streams\n",
        ),
        ScanSource(
            f"{package}.second",
            "invented/second.py",
            "from populace_dynamics.invented.reexport import "
            "Streams as Streams2\n",
        ),
        ScanSource(
            f"{package}.by_name",
            "invented/by_name.py",
            "from populace_dynamics.invented.reexport import Streams\n"
            "def f(x):\n    return isinstance(x, Streams)\n",
        ),
        ScanSource(
            f"{package}.by_module",
            "invented/by_module.py",
            "from populace_dynamics.invented import reexport as rx\n"
            "def f(x):\n    return type(x) is rx.Streams\n",
        ),
        ScanSource(
            f"{package}.by_star",
            "invented/by_star.py",
            "from populace_dynamics.invented.reexport import *\n"
            "def f(x):\n    return isinstance(x, Streams)\n",
        ),
        ScanSource(
            f"{package}.by_chain",
            "invented/by_chain.py",
            "from populace_dynamics.invented.second import Streams2\n"
            "def f(x):\n    return x.__class__ == Streams2\n",
        ),
        ScanSource(
            f"{package}.own_class",
            "invented/own_class.py",
            "class Streams:\n    pass\n"
            "def f(x):\n    return isinstance(x, Streams)\n",
        ),
    ]
    hits = scan_sources(sources)
    assert [(hit.path, hit.kind) for hit in hits] == [
        ("invented/by_chain.py", "__class__-compare"),
        ("invented/by_module.py", "type-compare"),
        ("invented/by_name.py", "isinstance"),
        ("invented/by_star.py", "isinstance"),
    ], describe(hits)


NEGATIVE_BODIES = (
    "def f(x):\n    return isinstance(x, int)\n",
    "from populace_dynamics.engine.rng import ProjectionModule\n"
    "def f(x):\n    return isinstance(x, ProjectionModule)\n",
    "def f(x):\n    return type(x) is dict or x.__class__ == list\n",
    "def f(n):\n    return ProjectionRNGRegistry(0, n)\n",
    "def f(registry: ProjectionRNGRegistry | None = None):\n"
    "    return registry is None or registry.n_periods == 3\n",
    "def f(context):\n"
    "    if context.rng_registry is None:\n        return None\n"
    "    return context.rng_registry.person_generator(1, 'aging', 0)\n",
    "def f(x):\n    return hasattr(x, 'person_generator')\n",
    "class Streams:\n    pass\n"
    "def f(x):\n    return isinstance(x, Streams) or x == 'Registry'\n",
    # A binding cycle that would grow a module path on every pass.
    "import os as b\na = b.path\nb = a\n"
    "def f(x):\n    return isinstance(x, a.sep)\n",
    # Listings, docstrings and annotations name the class harmlessly.
    "__all__ = ['ProjectionRNGRegistry']\n"
    "__all__ += ['ProjectionRNGRegistry']\n"
    "__all__.extend(['ProjectionRNGRegistry'])\n",
    'def f(x):\n    """Draw from a ProjectionRNGRegistry."""\n    return x\n',
    "class Holder:\n    registry: ProjectionRNGRegistry | None = None\n"
    "def f() -> 'ProjectionRNGRegistry':\n"
    "    return ProjectionRNGRegistry(draw_index=0, n_periods=1)\n",
    # A dispatch hint on a keyword-only parameter is never dispatched on.
    "from functools import singledispatch\n"
    "@singledispatch\ndef f(x):\n    return 0\n"
    "@f.register\ndef _(x: int, *, registry: ProjectionRNGRegistry):\n"
    "    return 1\n",
    # A module function that shares a probe's name, called by name.
    "def _sequence(n):\n    return list(range(n))\n"
    "def f(x):\n    return _sequence(x)\n",
    # The registry's module, used for something else.
    "from populace_dynamics.engine import rng\n"
    "def f(x):\n    return x is rng.ProjectionModule.EARNINGS\n",
    # Literal tables that name nothing the scan tracks; pruning drops them.
    "TABLE = {'a': (1, -2.5, None), 'b': [b'x', {3}]}\n"
    "def f(x):\n    return isinstance(x, (int, str)) and x in TABLE\n",
)


@pytest.mark.parametrize("body", NEGATIVE_BODIES)
def test_scan_ignores_unrelated_checks_and_ordinary_registry_use(body):
    """Each negative names the registry, so the scan parses it."""
    hits = scan_sources([_invented(_REGISTRY_IMPORT + body)])
    assert hits == (), describe(hits)


# Inert-literal pruning must not change any result. The leaves include the
# class's name, its module's name and a probe name, so some generated
# literals are inert and some are not.
_LITERAL_LEAVES = st.one_of(
    st.integers(-3, 3),
    st.none(),
    st.binary(max_size=2),
    st.sampled_from(
        ["a", REGISTRY_NAME, REGISTRY_MODULE, "_period_sequence", "RNG"]
    ),
)
_LITERALS = st.recursive(
    _LITERAL_LEAVES,
    lambda inner: st.one_of(
        st.lists(inner, max_size=3),
        st.tuples(inner, inner),
        st.dictionaries(st.text("ab", max_size=2), inner, max_size=3),
    ),
    max_leaves=8,
)
_LITERAL_PLACES = (
    _REGISTRY_IMPORT
    + "TABLE = {0}\n"
    + "KINDS = ({0}, ProjectionRNGRegistry)\n"
    + "__all__ = {0}\n"
    + "def f(x, default={0}):\n"
    + "    for item in {0}:\n"
    + "        pass\n"
    + "    return type(x).__name__ in {0} or isinstance(x, {0}) or g({0})\n"
)


def test_pruning_leaves_every_invented_scan_unchanged():
    """Pruned and unpruned scans agree on every invented module here."""
    texts = [text for text, _ in SPELLINGS.values()]
    texts += [_REGISTRY_IMPORT + body for body in NEGATIVE_BODIES]
    for text in texts:
        assert scan_sources([_invented(text)]) == scan_sources(
            [_invented(text)], prune=False
        )


@settings(max_examples=200, deadline=None)
@given(literal=_LITERALS)
def test_pruning_leaves_scans_unchanged_for_any_literal(literal):
    """Inert literals contribute nothing, wherever they sit.

    Each generated literal is placed in every position a check could read
    it from: a binding, a container beside the class, a listing, a
    default, a loop, a comparison, a type check and a call.
    """
    text = _LITERAL_PLACES.format(repr(literal))
    pruned = scan_sources([_invented(text)])
    assert pruned == scan_sources([_invented(text)], prune=False)
    assert ScanHit("invented/invented_case.py", 3, "class-reference") in (
        pruned
    )


def test_scan_messages_never_show_source_text():
    """Hits and refusals give a path, line and node kind only."""
    sentinel = "ZQX_INVENTED_LITERAL_7781"
    text = (
        _REGISTRY_IMPORT
        + f"LABEL = {sentinel!r}\n"
        + "def f(x, y):\n"
        + "    return isinstance(x, ProjectionRNGRegistry) and (\n"
        + f"        y == {sentinel!r}\n"
        + "    )\n"
    )
    hits = scan_sources([_invented(text)])
    assert [str(hit) for hit in hits] == [
        "invented/invented_case.py:4: isinstance"
    ]
    message = describe(hits)
    assert sentinel not in message
    assert all(sentinel not in repr(hit) for hit in hits)
    assert {field.name for field in dataclasses.fields(ScanHit)} == {
        "path",
        "line",
        "kind",
    }
    for broken in (
        f"isinstance(x, ProjectionRNGRegistry) {sentinel} (\n",
        f"ProjectionRNGRegistry = {sentinel!r}\x00\n",
    ):
        with pytest.raises(ScanError) as refused:
            scan_sources([_invented(broken)])
        assert sentinel not in str(refused.value)
        assert refused.value.__cause__ is None
        assert refused.value.__suppress_context__


def test_scan_walk_skips_excluded_modules_without_opening_them(
    tmp_path, monkeypatch
):
    """The walk drops excluded paths before any read of them.

    Decoys sit at the closed paths, at the pinned depletion-cut paths and at
    one more name the pattern matches. Every read is recorded, and the
    decoys are also made unreadable where the process is not the superuser,
    so a read would fail either way.
    """
    package = tmp_path / "src" / "populace_dynamics"
    check = (
        _REGISTRY_IMPORT
        + "def f(x):\n    return isinstance(x, ProjectionRNGRegistry)\n"
    )
    files = {
        "engine/__init__.py": "",
        "engine/checks.py": check,
        "open_population/own.py": check,
        "engine/__pycache__/cached.py": check,
        "bridge/depletion.py": "",
    }
    for relative, text in files.items():
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    unpinned = Path("src/populace_dynamics/bridge/depletion_cut_invented.py")
    decoys = [
        tmp_path / relative
        for relative in (*CLOSED_MODULES, *PATTERN_EXCLUDED_MODULES, unpinned)
    ]
    for decoy in decoys:
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_text(check)
    read = []
    original = Path.read_bytes

    def recording(path):
        read.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", recording)
    unreadable = os.geteuid() != 0
    try:
        for decoy in decoys if unreadable else ():
            decoy.chmod(0)
        sources = repository_sources(tmp_path)
    finally:
        for decoy in decoys:
            decoy.chmod(0o600)
    assert not set(read) & set(decoys)
    assert {path.relative_to(tmp_path).as_posix() for path in read} == {
        "src/populace_dynamics/bridge/depletion.py",
        "src/populace_dynamics/engine/__init__.py",
        "src/populace_dynamics/engine/checks.py",
    }
    assert [source.path for source in sources] == [
        "src/populace_dynamics/bridge/depletion.py",
        "src/populace_dynamics/engine/__init__.py",
        "src/populace_dynamics/engine/checks.py",
    ]
    assert [source.module for source in sources] == [
        "populace_dynamics.bridge.depletion",
        "populace_dynamics.engine",
        "populace_dynamics.engine.checks",
    ]
    assert excluded_paths(tmp_path) == tuple(
        sorted(decoy.relative_to(tmp_path).as_posix() for decoy in decoys)
    )
    hits = scan_sources(sources)
    assert [str(hit) for hit in hits] == [
        "src/populace_dynamics/engine/checks.py:3: isinstance"
    ]


# ---------------------------------------------------------------------------
# The pinned sealed check refuses the direct class loudly.
# ---------------------------------------------------------------------------


def _observer_inputs(size=3):
    identities = [PersonIdentity("int64", value) for value in range(size)]
    frame = pd.DataFrame(
        {
            "person_id": np.arange(size, dtype="int64"),
            "age": np.full(size, 40, dtype="int64"),
            "year": np.full(size, START, dtype="int64"),
            "sex": ["female", "male", "female"][:size],
            "weight": np.ones(size),
        }
    )
    model = AgeSexMortalityModel(
        ((0, 64), (65, 120)),
        {
            ("0-64", "female"): 0.4,
            ("0-64", "male"): 0.4,
            ("65+", "female"): 0.4,
            ("65+", "male"): 0.4,
        },
    )
    keywords = dict(
        model=model,
        identity_map=PersonIdentityMap.from_identities(identities),
        realization_id="invented-draw-0",
        source_contract_digest="a" * 64,
    )
    return frame, keywords


def test_pinned_sealed_check_refuses_direct_streams_loudly():
    frame, keywords = _observer_inputs()
    ordinals = {person: index for index, person in enumerate(frame.person_id)}
    base = PeriodContext(1, START + 1, 0, {}, person_ordinals=ordinals)
    registry = replace(base, rng_registry=ProjectionRNGRegistry(0, 2))
    direct = replace(base, rng_registry=DirectRNGStreams(0, 2))
    rng = np.random.default_rng(0)
    survivors, _ = observe_mortality(frame, registry, rng, **keywords)
    expected = apply_mortality(frame, registry, rng, model=keywords["model"])
    pd.testing.assert_frame_equal(survivors, expected)
    with pytest.raises(ValueError, match="existing RNG registry required"):
        observe_mortality(frame, direct, rng, **keywords)


def _assert_observer_refusal(refused):
    """The OP1 refusal names the fix and chains the sealed refusal."""
    assert str(refused.value) == (
        "ID_OR_STREAM_COLLISION: a composed step requires the projection's "
        "own ProjectionRNGRegistry (observe_mortality does, "
        'mortality_observer.py:381); pass rng_streams="registry"'
    )
    cause = refused.value.__cause__
    assert type(cause) is ValueError
    assert cause.args == (SEALED_REGISTRY_REFUSAL,)


def test_pinned_sealed_check_refuses_a_direct_op1_run_loudly():
    """Composed into OP1, the observer runs on the registry and refuses
    the direct default before any draw, rather than diverging. The harness
    re-raises the refusal as its own, naming ``rng_streams="registry"``."""
    frame, keywords = _observer_inputs()
    draws = []

    def observed(frame, context, rng):
        draws.append(context.year)
        return observe_mortality(frame, context, rng, **keywords)[0]

    modules = replace(_modules(), mortality=observed, fertility=_unchanged)
    request = GateRunRequest(START + 2)
    result = run_gate(frame, modules, request, rng_streams="registry")
    assert result.rng_stream_class == REGISTRY_CLASS
    assert len(result.accounting.periods) == 2
    assert draws == [START + 1, START + 2]
    draws.clear()
    with pytest.raises(IdOrStreamCollision) as refused:
        run_gate(frame, modules, request)
    _assert_observer_refusal(refused)
    assert draws == [START + 1]
    with pytest.raises(IdOrStreamCollision) as refused:
        run_production(
            frame, modules, ProductionRequest("tr2026_intermediate")
        )
    _assert_observer_refusal(refused)
    assert draws == [START + 1, START + 1]


def test_only_the_sealed_refusal_under_direct_streams_is_re_raised():
    """Other errors, the same text from a subclass, and the same refusal
    under the registry all pass through as the very object raised."""

    class Subclass(ValueError):
        pass

    def raising(error):
        def step(frame, context, rng):
            raise error

        return step

    registry = ProjectionRNGRegistry(0, 2)
    rng = np.random.default_rng(0)
    for mode, error in (
        ("direct", ValueError("another refusal")),
        ("direct", ValueError(SEALED_REGISTRY_REFUSAL, "extra")),
        ("direct", Subclass(SEALED_REGISTRY_REFUSAL)),
        ("direct", TypeError(SEALED_REGISTRY_REFUSAL)),
        ("registry", ValueError(SEALED_REGISTRY_REFUSAL)),
    ):
        step = _AdapterStreams(mode).wrap(raising(error))
        with pytest.raises(type(error)) as passed:
            step(None, _context(registry), rng)
        assert passed.value is error, (mode, error)
    step = _AdapterStreams("direct").wrap(
        raising(ValueError(SEALED_REGISTRY_REFUSAL))
    )
    with pytest.raises(IdOrStreamCollision) as refused:
        step(None, _context(registry), rng)
    _assert_observer_refusal(refused)


# ---------------------------------------------------------------------------
# The fresh-process check: a projection imports neither closed module.
# ---------------------------------------------------------------------------

_FRESH_PROCESS_RUN = textwrap.dedent("""
    import json
    import sys
    from functools import partial

    import numpy as np
    import pandas as pd

    from populace_dynamics.baselines.fertility import AsfrFertilityStep
    from populace_dynamics.engine.loop import PeriodModules
    from populace_dynamics.engine.steps import advance_age, apply_mortality
    from populace_dynamics.open_population.exits import no_marital_transitions
    from populace_dynamics.open_population.gates import (
        GateRunRequest,
        run_gate,
    )
    from populace_dynamics.open_population.harness import (
        ProductionRequest,
        run_production,
    )

    class Constant:
        def probabilities(self, frame):
            return np.full(len(frame), 0.1)

    def unchanged(frame, *args):
        return frame

    modules = PeriodModules(
        mortality=partial(apply_mortality, model=Constant()),
        aging=advance_age,
        marital_core=no_marital_transitions,
        fertility=AsfrFertilityStep(
            asfr=lambda year: {age: 0.2 for age in range(18, 45)}
        ),
        disability=unchanged,
        earnings=unchanged,
        claiming=unchanged,
        household_composition=unchanged,
    )
    initial = pd.DataFrame(
        {
            "person_id": [1, 2, 3],
            "year": 2025,
            "age": [25, 30, 35],
            "sex": ["female", "male", "female"],
            "weight": [1.0, 1.5, 2.0],
        }
    )
    hazard = lambda frame, context: np.full(len(frame), 0.05)
    production = run_production(
        initial,
        modules,
        ProductionRequest("tr2026_intermediate"),
        emigration_hazard=hazard,
    )
    classes = [production.rng_stream_class]
    for streams in ("registry", "direct"):
        gate = run_gate(
            initial,
            modules,
            GateRunRequest(2027),
            emigration_hazard=hazard,
            rng_streams=streams,
        )
        classes.append(gate.rng_stream_class)
    closed = (
        "populace_dynamics.estimates.adjusted_poverty",
        "populace_dynamics.uniform_cut_track_u.rows",
    )
    print(json.dumps({
        "loaded": {name: name in sys.modules for name in closed},
        "depletion_cut": sorted(
            name for name in sys.modules if "depletion_cut" in name
        ),
        "classes": classes,
    }))
""")


def test_projection_runs_import_no_excluded_module():
    """A fresh process runs OP1 to 2100 and both ways to 2027, then
    checks ``sys.modules`` for the closed and depletion-cut modules.

    Code a projection never imports cannot check its registry's type, so
    this closes the gap the path exclusions leave in the scan.
    """
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", _FRESH_PROCESS_RUN],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["loaded"] == {
        "populace_dynamics.estimates.adjusted_poverty": False,
        "populace_dynamics.uniform_cut_track_u.rows": False,
    }
    assert report["depletion_cut"] == []
    assert report["classes"] == [DIRECT_CLASS, REGISTRY_CLASS, DIRECT_CLASS]


# ---------------------------------------------------------------------------
# The binding: one direct instance, one context per period, loop generators.
# ---------------------------------------------------------------------------


def _unchanged(frame, *args):
    return frame


class _ConstantMortality:
    def __init__(self, probability):
        self.probability = probability

    def probabilities(self, frame):
        return np.full(len(frame), self.probability)


def _modules(death=0.1, birth=0.2, probe=None):
    return PeriodModules(
        mortality=partial(apply_mortality, model=_ConstantMortality(death)),
        aging=advance_age,
        marital_core=no_marital_transitions,
        fertility=AsfrFertilityStep(
            asfr=lambda year: {age: birth for age in range(18, 45)}
        ),
        disability=_unchanged,
        earnings=probe or _unchanged,
        claiming=_unchanged,
        household_composition=_unchanged,
    )


def _roster(size, *, first_id=1, year=START):
    index = np.arange(size)
    return pd.DataFrame(
        {
            "person_id": (first_id + index).astype("int64"),
            "year": year,
            "age": 20 + (index * 7) % 30,
            "sex": np.where(index % 2, "male", "female"),
            "birth_year": year - 20 - (index * 7) % 30,
            "weight": 0.5 + index / 4,
        }
    )


def _entrants(years):
    return {
        year: _roster(2, first_id=10_001 + 2 * offset, year=year - 1)
        for offset, year in enumerate(years)
    }


_SLOT_MODULES = {
    "mortality": ProjectionModule.MORTALITY,
    "aging": ProjectionModule.AGING,
    "marital_core": ProjectionModule.MARITAL_CORE,
    "fertility": ProjectionModule.FERTILITY,
    "disability": ProjectionModule.DISABILITY,
    "earnings": ProjectionModule.EARNINGS,
    "claiming": ProjectionModule.CLAIMING,
    "household_composition": ProjectionModule.HOUSEHOLD_COMPOSITION,
}


def _recording(modules, calls):
    def record(slot, step):
        def recorded(frame, context, *args):
            rng = args[-1]
            calls.append((slot, context, dict(rng.bit_generator.state)))
            return step(frame, context, *args)

        return recorded

    return replace(
        modules,
        **{
            slot: record(slot, getattr(modules, slot))
            for slot in _SLOT_MODULES
        },
    )


@pytest.mark.parametrize("mode", RNG_STREAM_MODES)
def test_each_period_gives_every_slot_one_context_and_the_loop_generators(
    mode, monkeypatch
):
    """Condition 1: only ``context.rng_registry`` changes, and only in
    direct mode; the loop's positional module generators pass unchanged.

    The loop's own context is recorded where the harness receives it, and
    every other field of each slot's context is compared with it.
    """
    calls = []
    originals = {}
    bind = _AdapterStreams.bind

    def recorded_bind(self, context):
        served = bind(self, context)
        originals[id(served)] = context
        return served

    monkeypatch.setattr(_AdapterStreams, "bind", recorded_bind)
    modules = _recording(_modules(), calls)
    draw, end = 2, START + 3
    result = run_gate(
        _roster(4),
        modules,
        GateRunRequest(end, draw_index=draw),
        rng_streams=mode,
    )
    loop_streams = ProjectionRNGRegistry(draw, end - START)
    assert len(calls) == 8 * (end - START)
    contexts = {}
    for slot, context, state in calls:
        contexts.setdefault(context.period_index, set()).add(id(context))
        expected = loop_streams.generator(
            context.period_index, _SLOT_MODULES[slot]
        )
        assert state == expected.bit_generator.state, (slot, context.year)
    assert all(len(ids) == 1 for ids in contexts.values())
    for _, context, _ in calls:
        original = originals[id(context)]
        for item in dataclasses.fields(PeriodContext):
            if item.name != "rng_registry":
                assert getattr(context, item.name) == getattr(
                    original, item.name
                ), item.name
        assert context.metadata is original.metadata
        assert context.person_ordinals is original.person_ordinals
        assert context.draw_index == original.draw_index == draw
        assert type(original.rng_registry) is ProjectionRNGRegistry
        assert (context is original) is (mode == "registry")
        assert (context.rng_registry is original.rng_registry) is (
            mode == "registry"
        )
    streams = {id(context.rng_registry) for _, context, _ in calls}
    assert len(streams) == 1
    served = calls[0][1].rng_registry
    expected_class = (
        DirectRNGStreams if mode == "direct" else (ProjectionRNGRegistry)
    )
    assert type(served) is expected_class
    assert (served.draw_index, served.n_periods) == (draw, end - START)
    assert len({id(context.metadata) for _, context, _ in calls}) == 1
    assert len({id(context.person_ordinals) for _, context, _ in calls}) == 1
    assert result.rng_streams == mode
    assert result.rng_stream_class == (
        DIRECT_CLASS if mode == "direct" else REGISTRY_CLASS
    )


def _context(registry, period=1):
    return PeriodContext(period, START + period, 0, {}, rng_registry=registry)


@pytest.mark.parametrize("mode", RNG_STREAM_MODES)
def test_binding_builds_once_and_refuses_an_unstable_loop_registry(mode):
    registry = ProjectionRNGRegistry(0, 4)
    binding = _AdapterStreams(mode)
    with pytest.raises(IdOrStreamCollision, match="no period bound"):
        _ = binding.stream_class
    first = binding.bind(_context(registry, 1))
    again = binding.bind(_context(registry, 1))
    later = binding.bind(_context(registry, 2))
    assert first.rng_registry is again.rng_registry is later.rng_registry
    if mode == "direct":
        assert type(first.rng_registry) is DirectRNGStreams
        same_period = _context(registry, 3)
        assert binding.bind(same_period) is binding.bind(same_period)
    else:
        assert first.rng_registry is registry
    with pytest.raises(IdOrStreamCollision, match="changed its RNG registry"):
        binding.bind(_context(ProjectionRNGRegistry(0, 4), 3))
    with pytest.raises(IdOrStreamCollision, match="person-keyed RNG"):
        binding.bind(_context(None, 3))


@pytest.mark.parametrize("value", ("Direct", "", None, 1, ("direct",)))
def test_unknown_stream_modes_are_refused_before_any_adapter(value):
    def refuses(*args):
        raise AssertionError("an adapter ran")

    modules = replace(_modules(), initialize=refuses, mortality=refuses)
    with pytest.raises(ValueError, match="rng_streams must be one of"):
        run_gate(
            _roster(2), modules, GateRunRequest(START + 1), rng_streams=value
        )
    with pytest.raises(ValueError, match="rng_streams must be one of"):
        run_production(
            _roster(2),
            modules,
            ProductionRequest("tr2026_intermediate"),
            rng_streams=value,
        )


@pytest.mark.parametrize("mode", RNG_STREAM_MODES)
def test_emigration_draws_stay_direct_in_both_modes(mode, monkeypatch):
    built = []

    class Recording(DirectRNGStreams):
        def __post_init__(self):
            built.append((self.draw_index, self.n_periods))
            super().__post_init__()

    monkeypatch.setattr(exits, "DirectRNGStreams", Recording)
    run_gate(
        _roster(6),
        _modules(),
        GateRunRequest(START + 2, draw_index=1),
        emigration_hazard=lambda frame, context: np.full(len(frame), 0.3),
        rng_streams=mode,
    )
    assert built == [(1, 2), (1, 2)]


def test_a_direct_run_patches_no_sealed_module_attribute():
    """Condition 1: the engine's modules and class are untouched by a run."""

    def snapshot():
        return (
            {name: id(value) for name, value in vars(engine_rng).items()},
            {name: id(value) for name, value in vars(engine_loop).items()},
            {
                name: id(value)
                for name, value in vars(ProjectionRNGRegistry).items()
            },
            {name: id(value) for name, value in vars(PeriodContext).items()},
        )

    before = snapshot()
    result = run_gate(
        _roster(5),
        _modules(),
        GateRunRequest(START + 2),
        emigration_hazard=lambda frame, context: np.full(len(frame), 0.05),
    )
    assert result.rng_stream_class == DIRECT_CLASS
    assert snapshot() == before
    assert engine_loop.ProjectionRNGRegistry is ProjectionRNGRegistry


# ---------------------------------------------------------------------------
# Condition 4: the projection is identical whichever class serves the draws.
# ---------------------------------------------------------------------------

PROBE_TAG = 0xE1
SIZES = (1, 3, 6)
DRAWS = (0, 3, 17)
SHORT_HORIZON = START + 2
LONG_HORIZON = 2100
# Every size with every draw, at the short horizon and at the registered one.
IDENTITY_GRID = tuple(
    (size, draw, horizon)
    for horizon in (SHORT_HORIZON, LONG_HORIZON)
    for size, draw in product(SIZES, DRAWS)
)


def _stream_probe(served):
    """Exercise every stream method the context carries, in the earnings
    slot, and keep the draws as a column; IDs and weights are unchanged."""

    def probe(frame, context, rng):
        streams = context.rng_registry
        served.add(type(streams))
        out = frame.copy()
        values = np.zeros(len(out))
        if len(out):
            period, module = context.period_index, ProjectionModule.EARNINGS
            first = int(out["person_id"].min())
            ordinal = context.person_ordinals[first]
            values[:] = (
                streams.draw_seed
                + streams.generator(period, module).random()
                + streams.seed_sequence(period, module).generate_state(1)[0]
                + streams.child_generator(period, module, ordinal).random()
                + streams.person_generator(period, module, ordinal).random()
                + streams.tagged_generator(period, module, PROBE_TAG).random()
                + streams.tagged_child_generator(
                    period, module, PROBE_TAG, ordinal
                ).random()
                + context.person_generator(module, first).random()
            )
        out["stream_probe"] = values
        return out

    return probe


def _digest(result):
    """Hash every projected slice, as ``op1_run_size.py`` does."""
    digest = hashlib.sha256()
    for frame in result.projection.slices:
        digest.update(repr(list(frame.columns)).encode())
        digest.update(pd.util.hash_pandas_object(frame, index=False).values)
    return digest.hexdigest()


def _run(size, draw, horizon, mode, *, death=0.05, birth=0.1, emigrate=0.05):
    served = set()
    modules = _modules(death, birth, probe=_stream_probe(served))
    midpoint = START + 1 + (horizon - START - 1) // 2
    entrant_years = sorted({START + 1, midpoint, horizon})
    keywords = dict(
        scheduled_entries=_entrants(entrant_years),
        emigration_hazard=lambda frame, context: np.full(len(frame), emigrate),
        rng_streams=mode,
    )
    if horizon == LONG_HORIZON:
        result = run_production(
            _roster(size),
            modules,
            ProductionRequest(
                "tr2026_intermediate", draw_index=draw, start_year=START
            ),
            **keywords,
        )
    else:
        result = run_gate(
            _roster(size),
            modules,
            GateRunRequest(horizon, draw_index=draw, start_year=START),
            **keywords,
        )
    return result, served


def _assert_identical(direct, registry):
    (direct, direct_served), (registry, registry_served) = direct, registry
    assert direct_served == {DirectRNGStreams}
    assert registry_served == {ProjectionRNGRegistry}
    assert (direct.rng_stream_class, registry.rng_stream_class) == (
        DIRECT_CLASS,
        REGISTRY_CLASS,
    )
    assert _digest(direct) == _digest(registry)
    for expected, actual in zip(
        registry.projection.slices, direct.projection.slices, strict=True
    ):
        pd.testing.assert_frame_equal(actual, expected)
    assert direct.events == registry.events
    assert direct.accounting.to_dict() == registry.accounting.to_dict()


@pytest.mark.parametrize(("size", "draw", "horizon"), IDENTITY_GRID)
def test_projection_hash_is_identical_for_both_stream_classes(
    size, draw, horizon
):
    """Three sizes, three draws and two horizons, one of them 2100 (§7).

    The invariant: OP1's projection is identical whichever stream class
    serves the adapters' person and tagged draws.
    """
    direct = _run(size, draw, horizon, "direct")
    registry = _run(size, draw, horizon, "registry")
    _assert_identical(direct, registry)
    result = direct[0]
    assert result.horizon == horizon
    assert len(result.projection.slices) == horizon - START + 1
    assert result.events, "the invented run declares no flow"


@settings(max_examples=10, deadline=None)
@given(
    size=st.integers(0, 8),
    draw=st.integers(0, 2**20),
    horizon=st.integers(START + 1, START + 4),
    death=st.sampled_from((0.0, 0.2, 1.0)),
    birth=st.sampled_from((0.0, 0.4, 1.0)),
    emigrate=st.sampled_from((0.0, 0.3, 1.0)),
)
def test_projection_identity_holds_on_generated_runs(
    size, draw, horizon, death, birth, emigrate
):
    """Hypothesis extends the grid's rosters, draws and rates (§7)."""
    rates = dict(death=death, birth=birth, emigrate=emigrate)
    direct = _run(size, draw, horizon, "direct", **rates)
    registry = _run(size, draw, horizon, "registry", **rates)
    _assert_identical(direct, registry)
