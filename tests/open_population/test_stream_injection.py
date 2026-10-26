"""Check OP1's slots drawing from ``DirectRNGStreams`` (design §§2.1, 5.4).

The coordinator's ruling of 24 October 2026 put the substitution in OP1's
harness wrapper: the sealed loop builds its registry (``engine/loop.py:217``)
and places it on each period's context (``:292``), and each OP1 slot receives
that context with ``DirectRNGStreams`` in its place. Duck typing is safe only
while the two classes share a public surface and no sealed code checks the
registry's type, so this module pins both, then checks the projection itself.

The AST scan reads ``src/populace_dynamics/`` outside ``open_population/``.
The project's data-access record keeps two modules out of automated reads, so
the scan skips them by path before anything opens them; a fresh-process run
shows a projection imports neither. Every message names a module path, line
number and node kind only, never source text or literal values.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass, replace
from functools import partial
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
# Private names that exist on only one class: probing for one tells the
# classes apart without a type check.
PROBE_NAMES = frozenset(
    name
    for name in set(dir(ProjectionRNGRegistry)) ^ set(dir(DirectRNGStreams))
    if name.startswith("_") and not name.startswith("__")
) | {"_root"}
_TYPE_CHECK_CALLS = frozenset({"isinstance", "issubclass"})
_DUNDER_CHECKS = frozenset({"__instancecheck__", "__subclasscheck__"})
_COMPARISONS = (ast.Is, ast.IsNot, ast.Eq, ast.NotEq, ast.In, ast.NotIn)


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


class _ModuleBindings:
    """Resolve, flow-insensitively, the names a module binds to the registry.

    Over-approximation is deliberate: any binding anywhere in the module
    counts everywhere in it, and any name or attribute spelled exactly
    ``ProjectionRNGRegistry`` counts, whatever it was imported from.
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
            if node.attr == REGISTRY_NAME:
                return True
            if (
                node.attr == "__class__"
                and isinstance(node.value, ast.Call)
                and self.is_registry(node.value.func)
            ):
                return True
            base = self.module_path(node.value)
            return base is not None and (base, node.attr) in self.exports
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

    def contains_registry(self, node: ast.expr) -> bool:
        """Return whether a class-info expression includes the registry."""
        if self.is_registry(node):
            return True
        if isinstance(node, ast.Tuple | ast.List | ast.Set):
            return any(self.contains_registry(item) for item in node.elts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self.contains_registry(node.left) or self.contains_registry(
                node.right
            )
        if isinstance(node, ast.Starred):
            return self.contains_registry(node.value)
        return False

    def _bind(self, name: str, value: ast.expr) -> None:
        if self.is_registry(value):
            self.classes.add(name)
            return
        path = self.module_path(value)
        if path is not None:
            self.modules[name] = path

    def _bind_targets(self, target: ast.expr, value: ast.expr) -> None:
        if isinstance(target, ast.Name):
            self._bind(target.id, value)
        elif (
            isinstance(target, ast.Tuple | ast.List)
            and isinstance(value, ast.Tuple | ast.List)
            and len(target.elts) == len(value.elts)
        ):
            for item, item_value in zip(target.elts, value.elts, strict=True):
                self._bind_targets(item, item_value)

    def _visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    self.modules[alias.asname] = alias.name
                else:
                    top = alias.name.split(".")[0]
                    self.modules[top] = top
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
                else:
                    self.modules[local] = f"{base}.{alias.name}"
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                self._bind_targets(target, node.value)
        elif isinstance(node, ast.AnnAssign | ast.NamedExpr):
            if node.value is not None:
                self._bind_targets(node.target, node.value)
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
                if self.is_registry(default):
                    self.classes.add(argument.arg)

    def bind(self, tree: ast.Module) -> None:
        """Bind to a fixed point, so chained aliases resolve in any order."""
        while True:
            before = (dict(self.modules), set(self.classes))
            for node in ast.walk(tree):
                self._visit(node)
            if before == (self.modules, self.classes):
                return

    def _kind(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if (
                name in _TYPE_CHECK_CALLS
                and len(node.args) >= 2
                and self.contains_registry(node.args[1])
            ):
                return name
            if (
                name in _DUNDER_CHECKS
                and isinstance(node.func, ast.Attribute)
                and self.is_registry(node.func.value)
            ):
                return "dunder-check"
            if (
                name == "register"
                and node.args
                and self.contains_registry(node.args[0])
            ):
                return "dispatch-register"
            if (
                name in {"hasattr", "getattr"}
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in PROBE_NAMES
            ):
                return "private-member-probe"
        elif isinstance(node, ast.Compare) and isinstance(
            node.ops[0], _COMPARISONS
        ):
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
            if any(
                isinstance(item, ast.Constant)
                and isinstance(item.value, str)
                and REGISTRY_NAME in item.value
                for item in operands
            ):
                return "name-compare"
        elif isinstance(node, ast.MatchClass):
            if self.is_registry(node.cls):
                return "match-class"
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            registers = any(
                isinstance(decorator, ast.Attribute)
                and decorator.attr == "register"
                for decorator in node.decorator_list
            )
            positional = [*node.args.posonlyargs, *node.args.args]
            if (
                registers
                and positional
                and positional[0].annotation is not None
                and self.contains_registry(positional[0].annotation)
            ):
                return "dispatch-annotation"
        return None

    def hits(self, tree: ast.Module) -> list[ScanHit]:
        found = []
        for node in ast.walk(tree):
            kind = self._kind(node)
            if kind is not None:
                found.append(ScanHit(self.source.path, node.lineno, kind))
        return found


def _parse(source: ScanSource) -> ast.Module:
    try:
        return ast.parse(source.text)
    except (SyntaxError, ValueError) as error:
        line = getattr(error, "lineno", None)
        raise ScanError(f"{source.path}:{line}: unparsable source") from None


def scan_sources(sources: Iterable[ScanSource]) -> tuple[ScanHit, ...]:
    """Find type checks on the registry across ``sources`` (condition 2).

    A module is parsed only if its text holds a tracked identifier as a
    word: the registry's name, a name some scanned module re-exports it
    under, or a probe name. Every static spelling of the class holds one, so
    the filter skips only modules that cannot name it. Re-exports are
    followed to a fixed point across modules.
    """
    sources = tuple(sources)
    exports = {(REGISTRY_MODULE, REGISTRY_NAME)}
    parsed: dict[str, ast.Module] = {}
    while True:
        tokens = sorted({name for _, name in exports} | PROBE_NAMES)
        pattern = re.compile(
            r"(?<![\w])(?:" + "|".join(map(re.escape, tokens)) + r")(?![\w])"
        )
        scopes = {}
        for source in sources:
            if source.path not in parsed:
                if not pattern.search(source.text):
                    continue
                parsed[source.path] = _parse(source)
            scope = _ModuleBindings(source, exports)
            scope.bind(parsed[source.path])
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
            for hit in scope.hits(parsed[path])
        )
    )


def _read(path: Path, relative: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise ScanError(f"{relative.as_posix()}: not UTF-8") from None


def repository_sources(root: Path = ROOT) -> tuple[ScanSource, ...]:
    """Collect ``src/populace_dynamics/`` outside OP1's own package.

    ``__pycache__`` folders are pruned, and each closed module is dropped by
    its path before anything opens, reads, parses, hashes or stats it.
    """
    package = root / "src" / "populace_dynamics"
    own = root / OWN_PACKAGE
    closed = {root / path for path in CLOSED_MODULES}
    sources = []
    for directory, subdirectories, files in os.walk(package):
        current = Path(directory)
        subdirectories[:] = sorted(
            name
            for name in subdirectories
            if name != "__pycache__" and current / name != own
        )
        for name in sorted(files):
            path = current / name
            if not name.endswith(".py") or path in closed:
                continue
            relative = path.relative_to(root)
            parts = path.relative_to(root / "src").with_suffix("").parts
            is_package = name == "__init__.py"
            sources.append(
                ScanSource(
                    module=".".join(parts[:-1] if is_package else parts),
                    path=relative.as_posix(),
                    text=_read(path, relative),
                    is_package=is_package,
                )
            )
    return tuple(sources)


# The one type check the scan finds in master's sealed code. It refuses the
# direct class loudly instead of diverging (pinned by the behaviour tests
# below), so an OP1 run that composes it must pass rng_streams="registry".
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
    assert OWN_PACKAGE == Path("src/populace_dynamics/open_population")


def test_sealed_code_holds_only_the_known_registry_type_check():
    """No sealed module checks the registry's type, except the pinned one.

    A new check in any reachable sealed module fails this test, by path,
    line and node kind, before the direct default could silently diverge.
    """
    sources = repository_sources()
    paths = {source.path for source in sources}
    assert not paths & {path.as_posix() for path in CLOSED_MODULES}
    assert not any(path.startswith(f"{OWN_PACKAGE}/") for path in paths)
    assert "src/populace_dynamics/engine/rng.py" in paths
    assert "src/populace_dynamics/baselines/asfr.py" in paths
    hits = scan_sources(sources)
    assert set(hits) == KNOWN_SEALED_TYPE_CHECKS, describe(hits)


_REGISTRY_IMPORT = (
    "from populace_dynamics.engine.rng import ProjectionRNGRegistry\n"
)
_IMPORT = "from populace_dynamics.engine.rng import ProjectionRNGRegistry"


def _check(expression, imports=_IMPORT):
    """Wrap one expression as an invented module; mark the expected line."""
    return f"{imports}\ndef f(x):\n    return {expression}  # check\n"


# Each invented module marks the line the scan must report with "# check".
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
    "builtins.isinstance": (
        _check(
            "builtins.isinstance(x, ProjectionRNGRegistry)",
            f"{_IMPORT}\nimport builtins",
        ),
        "isinstance",
    ),
    "issubclass": (
        _check("issubclass(type(x), ProjectionRNGRegistry)"),
        "issubclass",
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
            "isinstance(x, S)", f"{_IMPORT}\nS = R\nR = ProjectionRNGRegistry"
        ),
        "isinstance",
    ),
    "type of an instance": (
        _check(
            "isinstance(x, T)",
            f"{_IMPORT}\nT = type(ProjectionRNGRegistry(0, 0))",
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
    "private-member probe": (
        _check("hasattr(x, '_period_sequence')", ""),
        "private-member-probe",
    ),
    "instance-check dunder": (
        _check("ProjectionRNGRegistry.__instancecheck__(x)"),
        "dunder-check",
    ),
    "default argument": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            def f(x, cls=ProjectionRNGRegistry):
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
        textwrap.dedent("""
            from functools import singledispatch
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @singledispatch
            def f(x):
                return 0
            @f.register
            def _(x: ProjectionRNGRegistry):  # check
                return 1
        """),
        "dispatch-annotation",
    ),
}


def _invented(text, module="populace_dynamics.engine.invented_case"):
    return ScanSource(module, f"invented/{module.rpartition('.')[2]}.py", text)


@pytest.mark.parametrize("spelling", tuple(SPELLINGS))
def test_scan_catches_every_spelling_of_a_registry_type_check(spelling):
    """Each spelling gives exactly one hit, of its kind, on its line."""
    text, kind = SPELLINGS[spelling]
    marked = [
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if line.endswith("# check")
    ]
    hits = scan_sources([_invented(text)])
    assert [(hit.line, hit.kind) for hit in hits] == [
        (marked[0], kind)
    ], describe(hits)


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


@pytest.mark.parametrize(
    "body",
    (
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
    ),
)
def test_scan_ignores_unrelated_checks_and_ordinary_registry_use(body):
    """Each negative names the registry, so the scan parses it."""
    hits = scan_sources([_invented(_REGISTRY_IMPORT + body)])
    assert hits == (), describe(hits)


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


def test_scan_walk_skips_closed_modules_without_opening_them(
    tmp_path, monkeypatch
):
    """The walk drops closed paths before any read of them.

    Every read is recorded, and the decoys are also made unreadable where
    the process is not the superuser, so a read would fail either way.
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
    }
    for relative, text in files.items():
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    decoys = [tmp_path / relative for relative in CLOSED_MODULES]
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
        "src/populace_dynamics/engine/__init__.py",
        "src/populace_dynamics/engine/checks.py",
    }
    assert [source.path for source in sources] == [
        "src/populace_dynamics/engine/__init__.py",
        "src/populace_dynamics/engine/checks.py",
    ]
    assert [source.module for source in sources] == [
        "populace_dynamics.engine",
        "populace_dynamics.engine.checks",
    ]
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


def test_pinned_sealed_check_refuses_a_direct_op1_run_loudly():
    """Composed into OP1, the observer runs on the registry and refuses
    the direct default before any draw, rather than diverging."""
    frame, keywords = _observer_inputs()

    def observed(frame, context, rng):
        return observe_mortality(frame, context, rng, **keywords)[0]

    modules = replace(_modules(), mortality=observed, fertility=_unchanged)
    request = GateRunRequest(START + 2)
    result = run_gate(frame, modules, request, rng_streams="registry")
    assert result.rng_stream_class == REGISTRY_CLASS
    assert len(result.accounting.periods) == 2
    with pytest.raises(ValueError, match="existing RNG registry required"):
        run_gate(frame, modules, request)


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
        "classes": classes,
    }))
""")


def test_projection_runs_import_neither_closed_module():
    """A fresh process runs OP1 to 2100 and both ways to 2027, then
    checks ``sys.modules``.

    Code a projection never imports cannot check its registry's type, so
    this closes the gap the path exclusion leaves in the scan.
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
    mode,
):
    """Condition 1: only ``context.rng_registry`` changes, and only in
    direct mode; the loop's positional module generators pass unchanged."""
    calls = []
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
# Every size with every draw at the short horizon. At 2100 each size runs
# with its own draw, so all three sizes and all three draws reach the
# registered horizon: one 2100 run costs about as much as 35 short ones.
IDENTITY_GRID = (
    *((size, draw, SHORT_HORIZON) for size in SIZES for draw in DRAWS),
    *(
        (size, draw, LONG_HORIZON)
        for size, draw in zip(SIZES, DRAWS, strict=True)
    ),
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
