"""Check OP1's slots drawing from ``DirectRNGStreams`` (design §§2.1, 5.4).

The coordinator's ruling of 24 October 2026 put the substitution in OP1's
harness wrapper: the sealed loop builds its registry (``engine/loop.py:217``)
and places it on each period's context (``:292``), and each OP1 slot receives
that context with ``DirectRNGStreams`` in its place. The substitution is safe
while sealed code behaves the same with either class. This module pins the
shared public surface, runs each sealed reader of a context's streams with
both classes, and checks the projection itself; those runs are the guarantee.

The AST scan is a heuristic beside them. It reads ``src/populace_dynamics/``
outside ``open_population/`` for code that could tell the classes apart other
than by behaviour, and tracks both classes, since a check against either
tells them apart.
Specific checks name each type check they find, and each read of a place
the catch-all trusts: export lists, docstrings, annotations, namespaces and
source text. Under them a catch-all reports every other use of either
class, of an instance built from one, of a module object that can reach
one, and of their names as text once literal expressions are folded. It
trusts imports, string statements, literal ``__all__`` listings,
annotations that no unknown decorator or base class reads, construction,
plain attribute reads on a module and the plain uses of an instance. The
evidence report's §6 lists what it cannot see, as classes of limit.
The project's data-access record keeps two modules out of automated reads,
and the scan also skips the depletion-cut modules, so that what it reads does
not depend on who runs it. It drops all of them by path before anything opens
them; a fresh-process run shows a projection imports none of them. Every
message names a module path, line number and node kind only, never source
text or literal values.
"""

from __future__ import annotations

import ast
import builtins
import dataclasses
import fnmatch
import hashlib
import importlib.util
import inspect
import json
import linecache
import os
import re
import string
import subprocess
import sys
import textwrap
import tracemalloc
import warnings
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

from populace_dynamics.assembled_history_observer import capture_fertility
from populace_dynamics.baselines.fertility import (
    AsfrFertilityStep,
    draw_asfr_births,
)
from populace_dynamics.cola_track_a.adapters import di_aware_claiming
from populace_dynamics.engine import claiming as engine_claiming
from populace_dynamics.engine import loop as engine_loop
from populace_dynamics.engine import rng as engine_rng
from populace_dynamics.engine.composition import (
    composition_rngs_from_registry,
)
from populace_dynamics.engine.di_entitlement import _person_uniforms
from populace_dynamics.engine.earnings_domain import EARNINGS_DOMAIN_COLUMN
from populace_dynamics.engine.loop import PeriodContext, PeriodModules
from populace_dynamics.engine.rng import (
    ProjectionModule,
    ProjectionRNGRegistry,
)
from populace_dynamics.engine.steps import (
    AgeSexMortalityModel,
    ClaimingSchedule,
    advance_age,
    apply_claiming,
    apply_earnings,
    apply_mortality,
)
from populace_dynamics.mortality_observer import observe_mortality
from populace_dynamics.mortality_ses.step import apply_differential_mortality
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
DIRECT_MODULE = "populace_dynamics.open_population.streams"
DIRECT_NAME = "DirectRNGStreams"
# A check against either class tells the two apart, so the scan tracks
# both. OP1's own package holds the direct class and is not scanned, so
# sealed code that names it, as text or as a module, counts as well.
TRACKED_CLASSES = frozenset(
    {(REGISTRY_MODULE, REGISTRY_NAME), (DIRECT_MODULE, DIRECT_NAME)}
)
TRACKED_NAMES = frozenset(name for _, name in TRACKED_CLASSES)
TRACKED_MODULES = frozenset(module for module, _ in TRACKED_CLASSES)
OWN_MODULE = "populace_dynamics.open_population"
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
# Text names a tracked class or module whatever its case.
_CLASS_TEXTS = tuple(sorted(name.casefold() for name in TRACKED_NAMES))
_MODULE_TEXTS = (REGISTRY_MODULE, OWN_MODULE)
_TYPE_CHECK_CALLS = frozenset({"isinstance", "issubclass"})
_DUNDER_CHECKS = frozenset({"__instancecheck__", "__subclasscheck__"})
_NAME_ATTRIBUTES = frozenset({"__name__", "__qualname__"})
_CONTAINER_CALLS = frozenset({"tuple", "list", "set", "frozenset", "dict"})
# The places the catch-all treats as benign can still be read at run time:
# ``__all__``, docstrings and annotations. These reads are checked instead.
_EXPORT_NAME = "__all__"
_DOC_ATTRIBUTES = frozenset(
    {"__doc__", "__code__", "co_consts", "__dict__", "__globals__"}
)
_ANNOTATION_ATTRIBUTES = frozenset(
    {
        "__annotations__",
        "__annotate__",
        "__dataclass_fields__",
        "__signature__",
        "__dict__",
    }
)
_NAMESPACE_CALLS = frozenset({"globals", "locals", "vars", "dir"})
_DOC_CALLS = _NAMESPACE_CALLS | {"getdoc", "getmembers", "getmembers_static"}
_ANNOTATION_CALLS = _NAMESPACE_CALLS | {
    "get_type_hints",
    "get_annotations",
    "signature",
    "fields",
    "getfullargspec",
    "getargspec",
    "get_overloads",
    "call_annotate_function",
    "getmembers",
    "getmembers_static",
}
_SOURCE_CALLS = frozenset(
    {"getsource", "getsourcelines", "findsource", "getcomments", "getblock"}
)
_SOURCE_MODULES = frozenset({"linecache", "dis", "marshal", "tokenize"})
_INTROSPECTION_CALLS = (
    frozenset(
        {
            "getmodule",
            "getfile",
            "getsourcefile",
            "getattr",
            "getattr_static",
            "hasattr",
        }
    )
    | _DOC_CALLS
    | _ANNOTATION_CALLS
    | _SOURCE_CALLS
)
# Calls that compare an instance, look it up, render it as text or
# introspect it: an instance passed to one of these counts.
_INSTANCE_SINKS = frozenset(
    {
        "type",
        "isinstance",
        "issubclass",
        "repr",
        "str",
        "ascii",
        "format",
        "dir",
        "vars",
        "getattr",
        "getattr_static",
        "hasattr",
        "getmodule",
        "dumps",
        "eq",
        "ne",
        "lt",
        "le",
        "gt",
        "ge",
        "is_",
        "is_not",
        "contains",
        "countOf",
        "indexOf",
        "count",
        "index",
        "get",
        "pop",
        "remove",
        "discard",
        "setdefault",
        "__eq__",
        "__ne__",
        "__contains__",
        "__getitem__",
    }
)
# Decorators that leave a function's or a class's annotations unread, by
# the path they resolve to. A name the module rebinds resolves to nothing.
_BENIGN_DECORATORS = frozenset(
    {
        "builtins.staticmethod",
        "builtins.classmethod",
        "builtins.property",
        "functools.cached_property",
        "functools.cache",
        "functools.lru_cache",
        "functools.wraps",
        "functools.singledispatch",
        "functools.singledispatchmethod",
        "functools.total_ordering",
        "abc.abstractmethod",
        "typing.overload",
        "typing.override",
        "typing.final",
        "typing_extensions.overload",
        "typing_extensions.override",
        "typing_extensions.final",
        "contextlib.contextmanager",
        "contextlib.asynccontextmanager",
        "dataclasses.dataclass",
    }
)
# A property's own decorators; one is trusted only on a property defined
# above it in the same class body (find_accessors).
_PROPERTY_METHODS = frozenset({"setter", "getter", "deleter"})
# Calls whose literal first argument is code; the scan parses and checks it.
_CODE_CALLS = frozenset({"eval", "exec", "compile", "ForwardRef"})
# Literal code is parsed this many levels deep: code in a module's literal,
# code in that code's literal, and so on.
_EMBED_DEPTH = 5


def _code_call(func: ast.expr) -> bool:
    """Return whether a callee runs code: ``re.compile`` does not."""
    if isinstance(func, ast.Name):
        return func.id in _CODE_CALLS
    return isinstance(func, ast.Attribute) and func.attr in (
        _CODE_CALLS - {"compile"}
    )


# Strings a read of a benign place may spell; a literal holding one is
# never pruned.
_SPECIAL_STRINGS = (
    frozenset({_EXPORT_NAME}) | _DOC_ATTRIBUTES | _ANNOTATION_ATTRIBUTES
)
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
    ast.ClassDef,
)
# Re-exports are followed at most this many steps, so a cycle ends.
_RESOLVE_STEPS = 16
# A hint's nested strings are parsed into at most this many parts.
_HINT_PARTS = 64
# Every kind of hit. A specific check names what the code does; the
# catch-all names any other use of a tracked class, module or instance.
SPECIFIC_KINDS = frozenset(
    {
        "isinstance",
        "issubclass",
        "type-compare",
        "__class__-compare",
        "class-compare",
        "name-compare",
        "module-compare",
        "match-class",
        "dispatch-register",
        "dispatch-annotation",
        "dunder-check",
        "private-member-probe",
        "export-read",
        "docstring-read",
        "annotation-read",
        "namespace-read",
        "dynamic-code",
        "source-read",
        "member-introspection",
    }
)
CATCH_ALL_KINDS = frozenset(
    {
        "class-reference",
        "class-name-string",
        "module-name-string",
        "module-reference",
        "instance-reference",
    }
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


def _names_class(text: str) -> bool:
    folded = text.casefold()
    return any(name in folded for name in _CLASS_TEXTS)


def _names_module(text: str) -> bool:
    folded = text.casefold()
    return any(module in folded for module in _MODULE_TEXTS)


def _names_probe(text: str) -> bool:
    """Return whether ``text`` holds a probe name as a whole word."""
    return any(
        re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text)
        for name in PROBE_NAMES
    )


# ---------------------------------------------------------------------------
# The folder: the text an expression holds before run time.
# ---------------------------------------------------------------------------

# Each value the folder computes holds no text longer than this, no larger
# integer and no more items, and it formats no template longer than the
# template limit or with a four-digit field width. A source literal is kept
# as written, at any length: the parser already holds it.
_FOLD_TEXT_LIMIT = 1 << 16
_FOLD_INT_LIMIT = 4096
_FOLD_TEMPLATE_LIMIT = 4096
_FOLD_ITEMS_LIMIT = 256
# The values one memo (a module's, or one expression's) keeps may weigh
# this much in all, in characters and items; past it, the scan stops with
# an error rather than hold more, so many values within the limits cannot
# add up to much either.
_FOLD_BUDGET = 16 * _FOLD_TEXT_LIMIT
# A field width or precision of 1000 or more, in each kind of template.
_WIDE_FIELDS = {
    "percent": re.compile(r"%[^a-zA-Z%]*\d{4}"),
    "brace": re.compile(r"\{[^{}]*\d{4}"),
    "spec": re.compile(r"\d{4}"),
}
_FOLD_METHODS = frozenset(
    {
        "capitalize",
        "casefold",
        "center",
        "decode",
        "encode",
        "format",
        "fromhex",
        "join",
        "ljust",
        "lower",
        "lstrip",
        "partition",
        "removeprefix",
        "removesuffix",
        "replace",
        "rjust",
        "rpartition",
        "rsplit",
        "rstrip",
        "split",
        "splitlines",
        "strip",
        "swapcase",
        "title",
        "upper",
        "zfill",
    }
)
_FOLD_FUNCTIONS = frozenset(
    {
        "str",
        "bytes",
        "repr",
        "ascii",
        "format",
        "chr",
        "reversed",
        "sorted",
        "tuple",
        "list",
    }
)
_CONVERSIONS = {-1: None, ord("s"): str, ord("r"): repr, ord("a"): ascii}
_UNKNOWN = object()


class _Items(tuple):
    """The items an iterator such as ``reversed(...)`` yields.

    Only a consumer reads them: ``tuple``, ``list``, ``sorted``, ``join``
    or unpacking. Anything else would see the iterator object itself, so
    the folder gives it no value.
    """


_SEQUENCES = (str, bytes, tuple, list)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _plain(value) -> bool:
    return value is not _UNKNOWN and not isinstance(value, _Items)


def _weight(value) -> int:
    """Measure a folded value: its characters, bytes and items, nested."""
    if isinstance(value, str | bytes):
        return len(value)
    if isinstance(value, tuple | list):
        return len(value) + sum(map(_weight, value))
    return 1


def _sized(value):
    """Return ``value`` if the folder may hold it, else ``_UNKNOWN``."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) <= _FOLD_INT_LIMIT else _UNKNOWN
    if isinstance(value, str | bytes):
        return value if len(value) <= _FOLD_TEXT_LIMIT else _UNKNOWN
    if isinstance(value, tuple | list):
        if len(value) > _FOLD_ITEMS_LIMIT:
            return _UNKNOWN
        items = [_sized(item) for item in value]
        if not all(map(_plain, items)):
            return _UNKNOWN
        if _weight(items) > _FOLD_TEXT_LIMIT:
            return _UNKNOWN
        kind = _Items if isinstance(value, _Items) else type(value)
        return kind(items) if kind in (_Items, tuple, list) else _UNKNOWN
    return _UNKNOWN


def _apply(operation):
    """Run a pure operation on folded values; any failure is unknown."""
    try:
        return _sized(operation())
    except Exception:
        return _UNKNOWN


def _template(value, kind: str) -> bool:
    """Return whether a format template is small with narrow fields.

    ``kind`` is ``"percent"`` for ``%`` templates, ``"brace"`` for
    ``str.format`` and ``"spec"`` for a format spec.
    """
    if isinstance(value, bytes):
        value = value.decode("latin-1")
    return (
        isinstance(value, str)
        and len(value) <= _FOLD_TEMPLATE_LIMIT
        and not _WIDE_FIELDS[kind].search(value)
    )


def _fold_binop(left, op, right):
    if not (_plain(left) and _plain(right)):
        return _UNKNOWN
    if _is_int(left) and _is_int(right):
        operations = {
            ast.Add: lambda: left + right,
            ast.Sub: lambda: left - right,
            ast.Mult: lambda: left * right,
        }
        operation = operations.get(type(op))
        return _UNKNOWN if operation is None else _apply(operation)
    if isinstance(op, ast.Add):
        if type(left) is not type(right) or not isinstance(left, _SEQUENCES):
            return _UNKNOWN
        # Each side is within the limits, so the sum is at most twice them.
        return _apply(lambda: left + right)
    if isinstance(op, ast.Mult):
        sequence, count = (left, right) if _is_int(right) else (right, left)
        if not (isinstance(sequence, _SEQUENCES) and _is_int(count)):
            return _UNKNOWN
        if _weight(sequence) * max(count, 0) > _FOLD_TEXT_LIMIT:
            return _UNKNOWN
        return _apply(lambda: sequence * count)
    if isinstance(op, ast.Mod) and isinstance(left, str | bytes):
        if not _template(left, "percent"):
            return _UNKNOWN
        return _apply(lambda: left % right)
    return _UNKNOWN


class _BoundedFormatter(string.Formatter):
    """``str.format``, refusing a field spec or text past the limits.

    A template can read one argument in many fields, so its text can far
    outgrow its arguments; each field is checked as it is formatted, and
    the first one past the limit stops the call.
    """

    def __init__(self):
        super().__init__()
        self.size = 0

    def format_field(self, value, format_spec):
        if not _template(format_spec, "spec"):
            raise ValueError("format spec past the folder's limits")
        text = super().format_field(value, format_spec)
        self.size += len(text)
        if self.size > _FOLD_TEXT_LIMIT:
            raise ValueError("formatted text past the folder's limits")
        return text


def _fold_method(receiver, name, args, keywords):
    """Call a pure ``str`` or ``bytes`` method within the size limits."""
    if not isinstance(receiver, str | bytes):
        return _UNKNOWN
    if name == "join" and len(args) == 1 and not keywords:
        # join reads an iterator's items; nothing else may take one.
        parts = args[0]
        if not isinstance(parts, _SEQUENCES):
            return _UNKNOWN
        separators = len(receiver) * max(len(parts) - 1, 0)
        if sum(map(_weight, parts)) + separators > _FOLD_TEXT_LIMIT:
            return _UNKNOWN
        return _apply(lambda: receiver.join(parts))
    if not all(map(_plain, (*args, *keywords.values()))):
        return _UNKNOWN
    if name == "format":
        if not (isinstance(receiver, str) and _template(receiver, "brace")):
            return _UNKNOWN
        return _apply(
            lambda: _BoundedFormatter().vformat(receiver, args, keywords)
        )
    if name == "replace" and len(args) >= 2:
        old, new = args[0], args[1]
        if type(old) is not type(receiver) or type(new) is not type(receiver):
            return _UNKNOWN
        count = receiver.count(old) if old else len(receiver) + 1
        if len(receiver) + count * len(new) > _FOLD_TEXT_LIMIT:
            return _UNKNOWN
    method = getattr(receiver, name, None)
    if method is None:
        return _UNKNOWN
    return _apply(lambda: method(*args, **keywords))


def _fold_function(name, args, keywords):
    """Call a pure builtin on folded values within the size limits."""
    if name in {"reversed", "sorted", "tuple", "list"}:
        if keywords or len(args) != 1:
            return _UNKNOWN
        if not isinstance(args[0], _SEQUENCES):
            return _UNKNOWN
        build = {
            "reversed": lambda items: _Items(reversed(items)),
            "sorted": sorted,
            "tuple": tuple,
            "list": list,
        }[name]
        return _apply(lambda: build(args[0]))
    if not all(map(_plain, (*args, *keywords.values()))):
        return _UNKNOWN
    if name == "format" and len(args) >= 2 and not _template(args[1], "spec"):
        return _UNKNOWN
    function = {
        "str": str,
        "bytes": bytes,
        "repr": repr,
        "ascii": ascii,
        "format": format,
        "chr": chr,
    }[name]
    return _apply(lambda: function(*args, **keywords))


def _fold_callee(func: ast.expr) -> bool:
    """Return whether the folder calls this callee."""
    if isinstance(func, ast.Attribute):
        return func.attr in _FOLD_METHODS
    return isinstance(func, ast.Name) and func.id in _FOLD_FUNCTIONS


def _fold_children(node: ast.AST) -> list[ast.AST]:
    """List the children whose values ``_fold_value`` reads."""
    if isinstance(node, ast.Tuple | ast.List):
        return list(node.elts)
    if isinstance(node, ast.UnaryOp):
        return [node.operand]
    if isinstance(node, ast.BinOp):
        return [node.left, node.right]
    if isinstance(node, ast.JoinedStr):
        return list(node.values)
    if isinstance(node, ast.FormattedValue):
        return [node.value] + ([node.format_spec] if node.format_spec else [])
    if isinstance(node, ast.Starred):
        return [node.value]
    if isinstance(node, ast.Subscript):
        index = node.slice
        if isinstance(index, ast.Slice):
            parts = [index.lower, index.upper, index.step]
            return [node.value, *(part for part in parts if part is not None)]
        return [node.value, index]
    if isinstance(node, ast.Call) and _fold_callee(node.func):
        func = node.func
        receiver = [func.value] if isinstance(func, ast.Attribute) else []
        return [
            *receiver,
            *node.args,
            *(keyword.value for keyword in node.keywords),
        ]
    return []


def _unpacked(nodes: list[ast.expr], value) -> list | None:
    """Return the values of call arguments or display items, unpacked.

    A starred item spreads its items, an iterator's among them; ``None``
    means some item has no value.
    """
    items = []
    for item in nodes:
        if isinstance(item, ast.Starred):
            inner = value(item.value)
            if not isinstance(inner, _SEQUENCES):
                return None
            items.extend(inner)
        else:
            items.append(value(item))
    return items if all(map(_plain, items)) else None


def _fold_value(node: ast.AST, value):
    """Fold one node, given ``value`` for each child it reads."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str | bytes):
            # The source's own text, kept as is: folding allocates nothing.
            return node.value
        if node.value is None or _is_int(node.value):
            return _sized(node.value)
        return _UNKNOWN
    if isinstance(node, ast.Tuple | ast.List):
        items = _unpacked(node.elts, value)
        if items is None:
            return _UNKNOWN
        return _sized(tuple(items) if isinstance(node, ast.Tuple) else items)
    if isinstance(node, ast.UnaryOp):
        operand = value(node.operand)
        if not _is_int(operand):
            return _UNKNOWN
        if isinstance(node.op, ast.USub):
            return _sized(-operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.Invert):
            return _sized(~operand)
        return _UNKNOWN
    if isinstance(node, ast.BinOp):
        return _fold_binop(value(node.left), node.op, value(node.right))
    if isinstance(node, ast.JoinedStr):
        parts = [value(item) for item in node.values]
        if not all(isinstance(part, str) for part in parts):
            return _UNKNOWN
        if sum(map(len, parts)) > _FOLD_TEXT_LIMIT:
            return _UNKNOWN
        return "".join(parts)
    if isinstance(node, ast.FormattedValue):
        inner = value(node.value)
        spec = value(node.format_spec) if node.format_spec else ""
        convert = _CONVERSIONS.get(node.conversion, _UNKNOWN)
        if not _plain(inner) or convert is _UNKNOWN:
            return _UNKNOWN
        if not _template(spec, "spec"):
            return _UNKNOWN
        return _apply(
            lambda: format(convert(inner) if convert else inner, spec)
        )
    if isinstance(node, ast.Subscript):
        sequence = value(node.value)
        if not (_plain(sequence) and isinstance(sequence, _SEQUENCES)):
            return _UNKNOWN
        index = node.slice
        if isinstance(index, ast.Slice):
            parts = [
                None if part is None else value(part)
                for part in (index.lower, index.upper, index.step)
            ]
            if not all(part is None or _is_int(part) for part in parts):
                return _UNKNOWN
            return _apply(lambda: sequence[slice(*parts)])
        position = value(index)
        if not _is_int(position):
            return _UNKNOWN
        return _apply(lambda: sequence[position])
    if isinstance(node, ast.Call) and _fold_callee(node.func):
        return _fold_call(node, value)
    return _UNKNOWN


def _fold_call(node: ast.Call, value):
    args = []
    for item in node.args:
        if isinstance(item, ast.Starred):
            inner = value(item.value)
            if not isinstance(inner, _SEQUENCES):
                return _UNKNOWN
            args.extend(inner)
        else:
            args.append(value(item))
    keywords = {}
    for keyword in node.keywords:
        if keyword.arg is None:
            return _UNKNOWN
        keywords[keyword.arg] = value(keyword.value)
    if any(item is _UNKNOWN for item in (*args, *keywords.values())):
        return _UNKNOWN
    func = node.func
    if isinstance(func, ast.Attribute):
        owner = func.value
        if isinstance(owner, ast.Name) and owner.id in {"str", "bytes"}:
            # An unbound method: str.join(sep, parts), bytes.fromhex(text).
            if func.attr == "fromhex" and owner.id == "bytes":
                if not all(map(_plain, args)) or keywords:
                    return _UNKNOWN
                return _apply(lambda: bytes.fromhex(*args))
            if not args:
                return _UNKNOWN
            return _fold_method(args[0], func.attr, args[1:], keywords)
        return _fold_method(value(owner), func.attr, args, keywords)
    return _fold_function(func.id, args, keywords)


class _FoldMemo(dict):
    """Each folded node's value, by node id, and the weight kept so far.

    ``path`` names the module in the error raised past the budget.
    """

    def __init__(self, path: str = "<expression>"):
        super().__init__()
        self.path = path
        self.held = 0


def _fold(node: ast.AST, memo: _FoldMemo):
    """Return the value an expression holds before run time, or unknown.

    Literals fold, and so do the pure operations a module might build
    text with: ``+``, ``*`` and ``%``, f-strings with their conversions and
    format specs, indexing and slicing, the ``str`` and ``bytes`` methods
    in ``_FOLD_METHODS`` and the builtins in ``_FOLD_FUNCTIONS``. Names
    are not followed. The walk keeps its own stack, so a deep expression
    cannot exhaust recursion, and ``memo`` keeps each node's value. Every
    value but a source literal counts against ``_FOLD_BUDGET``.
    """

    def known(item):
        entry = memo.get(id(item))
        return entry is not None and entry[0] is item

    stack = [(node, False)]
    while stack:
        item, ready = stack.pop()
        if known(item):
            continue
        children = [
            child for child in _fold_children(item) if not known(child)
        ]
        if ready or not children:
            value = _fold_value(item, lambda child: memo[id(child)][1])
            if not isinstance(item, ast.Constant):
                memo.held += _weight(value)
                if memo.held > _FOLD_BUDGET:
                    raise ScanError(
                        f"{memo.path}: literal expressions past the "
                        "folder's budget"
                    )
            memo[id(item)] = (item, value)
        else:
            stack.append((item, True))
            stack.extend((child, False) for child in children)
    return memo[id(node)][1]


def _static_text(node: ast.expr, memo: _FoldMemo | None = None) -> str | None:
    """Return the text a string expression holds before run time, if any.

    The parser already joins adjacent literals and decodes escapes; the
    folder does the rest. Bytes are read as Latin-1, so an ASCII name
    matches in either.
    """
    value = _fold(node, _FoldMemo() if memo is None else memo)
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("latin-1")
    return None


def _value_texts(value) -> list[str]:
    """List the texts a folded value holds, inside tuples too."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, bytes):
        return [value.decode("latin-1")]
    if isinstance(value, tuple | list):
        return [text for item in value for text in _value_texts(item)]
    return []


# ---------------------------------------------------------------------------
# Syntax helpers.
# ---------------------------------------------------------------------------


def _is_all(target: ast.expr) -> bool:
    return isinstance(target, ast.Name) and target.id == _EXPORT_NAME


def _is_string_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(
        node.value, str | bytes
    )


def _is_name_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _literal_names(node: ast.AST) -> bool:
    """Return whether ``node`` is a list or tuple of string literals."""
    return isinstance(node, ast.List | ast.Tuple) and all(
        map(_is_name_literal, node.elts)
    )


def _lists_exports(statement: ast.stmt) -> bool:
    """Return whether a statement sets or adds to ``__all__`` by literal.

    That is ``__all__ = [...]``, ``__all__: list[str] = [...]`` or
    ``__all__ += [...]``, with a list or tuple of string literals.
    """
    if isinstance(statement, ast.Assign):
        targets = statement.targets
    elif isinstance(statement, ast.AnnAssign) or (
        isinstance(statement, ast.AugAssign)
        and isinstance(statement.op, ast.Add)
    ):
        targets = [statement.target]
    else:
        return False
    return all(map(_is_all, targets)) and _literal_names(statement.value)


def _extends_exports(node: ast.expr) -> bool:
    """Return whether ``node`` is ``__all__.append`` or ``.extend`` of a
    literal name or literal names."""
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and _is_all(node.func.value)
        and len(node.args) == 1
        and not node.keywords
    ):
        return False
    if node.func.attr == "append":
        return _is_name_literal(node.args[0])
    return node.func.attr == "extend" and _literal_names(node.args[0])


def _statements(body: list[ast.stmt]) -> Iterable[ast.stmt]:
    """Yield the statements of a body, inside compound statements too.

    Nested functions and classes are not entered: they are other scopes.
    """
    stack = list(reversed(body))
    while stack:
        statement = stack.pop()
        yield statement
        if isinstance(
            statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            continue
        inner = []
        for field in ("body", "orelse", "finalbody"):
            inner += getattr(statement, field, [])
        for handler in getattr(statement, "handlers", []):
            inner += handler.body
        for case in getattr(statement, "cases", []):
            inner += case.body
        stack.extend(reversed(inner))


def _bound_names(statement: ast.stmt) -> set[str]:
    """Name everything a statement may bind, in nested scopes too."""
    names = set()
    for node in ast.walk(statement):
        if isinstance(node, ast.Name) and isinstance(
            node.ctx, ast.Store | ast.Del
        ):
            names.add(node.id)
        elif isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            names.add(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names.update(
                (alias.asname or alias.name).split(".")[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ExceptHandler | ast.MatchAs | ast.MatchStar):
            if node.name:
                names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
    return names


def _hints(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.expr]:
    """List a function's hints in the order Python stores them.

    That is the parameters in order (positional, ``*args``, keyword-only,
    ``**kwargs``), then the return hint; ``singledispatch`` dispatches on
    the first.
    """
    arguments = node.args
    parameters = [*arguments.posonlyargs, *arguments.args]
    if arguments.vararg is not None:
        parameters.append(arguments.vararg)
    parameters += arguments.kwonlyargs
    if arguments.kwarg is not None:
        parameters.append(arguments.kwarg)
    hints = [item.annotation for item in parameters if item.annotation]
    if node.returns is not None:
        hints.append(node.returns)
    return hints


def _class_annotations(node: ast.ClassDef) -> list[ast.expr]:
    return [
        statement.annotation
        for statement in _statements(node.body)
        if isinstance(statement, ast.AnnAssign)
    ]


def _parts(node: ast.expr) -> list[ast.expr]:
    """List the parts an expression holds or picks one of."""
    if isinstance(node, ast.Tuple | ast.List | ast.Set):
        return list(node.elts)
    if isinstance(node, ast.Dict):
        return [item for item in (*node.keys, *node.values) if item]
    if isinstance(node, ast.Starred | ast.NamedExpr | ast.Subscript):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return [node.body, node.orelse]
    if isinstance(node, ast.BoolOp):
        return list(node.values)
    return []


def _binds_by_name(target: ast.expr) -> bool:
    """Return whether an assignment target only binds names."""
    if isinstance(target, ast.Name | ast.Attribute):
        return True
    if isinstance(target, ast.Starred):
        return _binds_by_name(target.value)
    if isinstance(target, ast.Tuple | ast.List):
        return all(map(_binds_by_name, target.elts))
    return False


def _relocate(tree: ast.AST, origin: ast.AST) -> None:
    """Give every node in ``tree`` the location of ``origin``."""
    for node in ast.walk(tree):
        for field in ("lineno", "col_offset", "end_lineno", "end_col_offset"):
            if field in node._attributes:
                setattr(node, field, getattr(origin, field, None))


def _annotation_nodes(tree: ast.AST) -> set[int]:
    """Return the ids of every node inside an annotation."""
    hints = []
    for node in ast.walk(tree):
        if isinstance(node, ast.arg | ast.AnnAssign) and node.annotation:
            hints.append(node.annotation)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.returns is not None:
                hints.append(node.returns)
    return {id(item) for hint in hints for item in ast.walk(hint)}


def _embedded(
    tree: ast.AST, memo: _FoldMemo, unexpanded: set[int], depth: int = 1
) -> list[ast.Module]:
    """Parse the literal code a module evaluates, nested code too.

    A literal passed to ``eval``, ``exec``, ``compile`` or ``ForwardRef``
    is code the module runs, so the scan checks it as part of the module;
    each parsed tree takes its call's location. Inside an annotation the
    hint checks parse such literals instead, so they are skipped here.
    Code nested more than ``_EMBED_DEPTH`` deep is not parsed: its call
    goes in ``unexpanded``, and the scan reports it as dynamic code.
    """
    found = []
    hinted = _annotation_nodes(tree)
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and node.args
            and _code_call(node.func)
            and id(node) not in hinted
        ):
            continue
        text = _static_text(node.args[0], memo)
        if text is None:
            continue
        try:
            parsed = ast.parse(text)
        except (SyntaxError, ValueError):
            continue
        if depth > _EMBED_DEPTH:
            unexpanded.add(id(node))
            continue
        _relocate(parsed, node)
        found.append(parsed)
        found += _embedded(parsed, memo, unexpanded, depth + 1)
    return found


class _ModuleBindings:
    """Resolve, flow-insensitively, what a module binds to a tracked class.

    Seven kinds of binding are tracked: modules; the tracked classes
    themselves; containers that may hold one (tuples, unions, mappings and
    anything read or rebuilt from them); strings that hold a tracked name;
    aliases of ``isinstance`` and ``issubclass``; instances built from a
    tracked class; and aliases of a dispatcher's ``register``.
    Over-approximation is deliberate: a binding anywhere in the module
    counts everywhere in it, an attribute counts wherever a name spelled
    like it is bound, a loop over class info binds its variable to the
    class, and any name or attribute spelled exactly like a tracked class
    counts, whatever it came from. Imported names are followed through
    other modules' re-exports.
    """

    def __init__(
        self,
        source: ScanSource,
        exports: set[tuple[str, str]],
        instance_exports: set[tuple[str, str]],
        module_exports: dict[tuple[str, str], str],
        memo: dict,
    ):
        self.source = source
        self.exports = exports
        self.instance_exports = instance_exports
        self.module_exports = module_exports
        self.memo = memo
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
        self.instances: set[str] = set()
        self.registrars: set[str] = set()
        # Names bound other than by importing a name under its own name; a
        # decorator so named may not be the one it looks like.
        self.assigned: set[str] = set()
        # Set by facts(): what the module holds in the places the catch-all
        # treats as benign, and the statements that list its exports.
        self.holds_docstring = False
        self.holds_annotations = False
        self.listing_values: set[int] = set()
        self.listing_calls: set[int] = set()
        self.listing_loads: set[int] = set()
        # Set by scan_sources: the modules whose objects and members count,
        # the modules the scan reads, and the code calls nested too deep to
        # parse.
        self.introspected: frozenset[str] = frozenset()
        self.known_modules: frozenset[str] = frozenset()
        self.unexpanded: set[int] = set()
        # Set by find_accessors: the decorators that are a property's own.
        self.accessors: set[int] = set()
        self.parents: dict[int, ast.AST] = {}
        # Each hint's parsed parts, kept so that their nodes stay alive and
        # their parents stay known.
        self.hint_cache: dict[int, tuple[ast.expr, list[ast.expr]]] = {}
        self.hint_parents: dict[int, ast.AST] = {}

    def _from_base(self, node: ast.ImportFrom) -> str:
        if not node.level:
            return node.module or ""
        parts = self.package.split(".")
        if node.level > 1:
            parts = parts[: len(parts) - (node.level - 1)]
        base = ".".join(parts)
        return f"{base}.{node.module}" if node.module else base

    def text(self, node: ast.expr) -> str | None:
        return _static_text(node, self.memo)

    def texts(self, node: ast.expr) -> list[str]:
        return _value_texts(_fold(node, self.memo))

    def _resolve(self, path: str) -> str:
        """Follow re-exports: ``a.b`` is what module ``a`` binds to ``b``."""
        for _ in range(_RESOLVE_STEPS):
            parent, _, name = path.rpartition(".")
            target = self.module_exports.get((parent, name))
            if target is None or target == path:
                break
            path = target
        return path

    def module_path(self, node: ast.expr) -> str | None:
        """Return the dotted path a name, attribute or import denotes."""
        if isinstance(node, ast.Name):
            path = self.modules.get(node.id)
            return None if path is None else self._resolve(path)
        if isinstance(node, ast.Attribute):
            # Unwound in a loop, so a long chain cannot exhaust recursion.
            attributes = []
            while isinstance(node, ast.Attribute):
                attributes.append(node.attr)
                node = node.value
            path = self.module_path(node)
            for attribute in reversed(attributes):
                if not path:
                    return None
                path = self._resolve(f"{path}.{attribute}")
            return path
        if isinstance(node, ast.Call):
            return self._imported(node)
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "modules"
            and self.module_path(node.value.value) == "sys"
        ):
            return self.text(node.slice)
        return None

    def _imported(self, node: ast.Call) -> str | None:
        """Name the module a literal ``import_module`` or ``__import__`` gives."""
        name = _call_name(node.func)
        if name not in {"import_module", "__import__"} or not node.args:
            return None
        target = self.text(node.args[0])
        if target is None:
            return None
        if name == "import_module":
            package = node.args[1] if len(node.args) > 1 else None
            for keyword in node.keywords:
                if keyword.arg == "package":
                    package = keyword.value
            anchor = None if package is None else self.text(package)
            try:
                return importlib.util.resolve_name(target, anchor)
            except (ImportError, ValueError):
                return None
        fromlist = node.args[3] if len(node.args) > 3 else None
        for keyword in node.keywords:
            if keyword.arg == "fromlist":
                fromlist = keyword.value
        listed = None if fromlist is None else _fold(fromlist, self.memo)
        return target if listed else target.split(".")[0]

    def is_tracked(self, node: ast.expr) -> bool:
        """Return whether ``node`` denotes a tracked class itself."""
        if isinstance(node, ast.Name):
            return node.id in self.classes or node.id in TRACKED_NAMES
        if isinstance(node, ast.Attribute):
            if node.attr in TRACKED_NAMES or node.attr in self.classes:
                return True
            if node.attr == "__class__" and self.instance_valued(node.value):
                return True
            base = self.module_path(node.value)
            return base is not None and (base, node.attr) in self.exports
        if isinstance(node, ast.NamedExpr):
            return self.is_tracked(node.value)
        if isinstance(node, ast.Call):
            if _is_type_call(node) and self.instance_valued(node.args[0]):
                return True
            if _call_name(node.func) == "getattr" and len(node.args) >= 2:
                name = self.text(node.args[1])
                base = self.module_path(node.args[0])
                return name is not None and (
                    name in TRACKED_NAMES
                    or (base is not None and (base, name) in self.exports)
                )
        return False

    def instance_valued(self, node: ast.expr) -> bool:
        """Return whether ``node`` may be an instance of a tracked class.

        The walk keeps its own stack, so a long chain of conditionals
        cannot exhaust recursion.
        """
        stack = [node]
        while stack:
            item = stack.pop()
            if isinstance(item, ast.Call):
                if self.is_tracked(item.func):
                    return True
            elif isinstance(item, ast.Name):
                if item.id in self.instances:
                    return True
            elif isinstance(item, ast.Attribute):
                if item.attr in self.instances:
                    return True
                base = self.module_path(item.value)
                if base is not None and (base, item.attr) in (
                    self.instance_exports
                ):
                    return True
            elif isinstance(item, ast.NamedExpr):
                stack.append(item.value)
            elif isinstance(item, ast.IfExp):
                stack += [item.body, item.orelse]
            elif isinstance(item, ast.BoolOp):
                stack += item.values
        return False

    def _any_part(self, node: ast.expr, test, more=None) -> bool:
        """Apply ``test`` to ``node`` and to each part it holds or picks.

        ``more``, if given, lists further parts of a node to test. The walk
        keeps its own stack, so a deep expression cannot exhaust recursion.
        """
        stack = [node]
        while stack:
            item = stack.pop()
            if test(item):
                return True
            stack += _parts(item)
            if more is not None:
                stack += more(item)
        return False

    def _class_part(self, node: ast.expr) -> bool:
        if self.is_tracked(node):
            return True
        if isinstance(node, ast.Name):
            return node.id in self.containers
        if isinstance(node, ast.Attribute):
            return node.attr in self.containers
        return False

    @staticmethod
    def _class_info_parts(node: ast.expr) -> list[ast.expr]:
        """List the class info a node builds from or reads."""
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, ast.BitOr | ast.Add
        ):
            # A union, or class-info tuples joined with "+".
            return [node.left, node.right]
        if isinstance(node, ast.Subscript):
            # Union[int, cls] holds the class in its subscript.
            return [node.slice]
        if isinstance(node, ast.Call):
            # Class info read or rebuilt: KINDS.get(key), tuple(KINDS).
            parts = []
            if isinstance(node.func, ast.Attribute):
                parts.append(node.func.value)
            if _call_name(node.func) in _CONTAINER_CALLS:
                parts += node.args
            return parts
        return []

    def contains_tracked(self, node: ast.expr) -> bool:
        """Return whether a class-info expression may include either class."""
        return self._any_part(node, self._class_part, self._class_info_parts)

    def _name_part(self, node: ast.expr) -> bool:
        texts = self.texts(node)
        if texts:
            return any(map(_names_class, texts))
        if isinstance(node, ast.Name):
            return node.id in self.names
        if isinstance(node, ast.Attribute):
            return node.attr in self.names or (
                node.attr in _NAME_ATTRIBUTES and self.is_tracked(node.value)
            )
        return False

    def names_class(self, node: ast.expr) -> bool:
        """Return whether ``node`` may hold a tracked class's name as text."""
        return self._any_part(node, self._name_part)

    def _tracked_module(self, path: str | None) -> bool:
        return path is not None and (
            path == REGISTRY_MODULE
            or path == OWN_MODULE
            or path.startswith(f"{OWN_MODULE}.")
        )

    def _owner(self, path: str | None) -> str | None:
        """Return the module that defines a member path, if the scan knows it."""
        if path is None or path in self.known_modules:
            return None
        parts = path.split(".")
        for size in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:size])
            if prefix in self.known_modules or prefix in self.introspected:
                return prefix
        return None

    def _module_part(self, node: ast.expr) -> bool:
        texts = self.texts(node)
        if texts:
            return any(map(_names_module, texts))
        if isinstance(node, ast.Attribute) and node.attr == "__name__":
            return self._tracked_module(self.module_path(node.value))
        if isinstance(node, ast.Attribute) and node.attr == "__module__":
            # Anything a tracked module defines carries its name, and so
            # does a tracked class or its instance.
            if self.is_tracked(node.value) or self.instance_valued(node.value):
                return True
            path = self.module_path(node.value)
            return self._tracked_module(path) or self._tracked_module(
                self._owner(path)
            )
        return self._tracked_module(self.module_path(node))

    def names_module(self, node: ast.expr) -> bool:
        """Return whether ``node`` may denote a tracked class's module."""
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

    def registrar(self, node: ast.expr) -> bool:
        """Return whether ``node`` denotes a dispatcher's ``register``."""
        if isinstance(node, ast.Attribute):
            return node.attr == "register" or node.attr in self.registrars
        if isinstance(node, ast.Name):
            return node.id == "register" or node.id in self.registrars
        if isinstance(node, ast.Call) and _call_name(node.func) == "getattr":
            return (
                len(node.args) >= 2 and self.text(node.args[1]) == "register"
            )
        return False

    def _bind(self, name: str, value: ast.expr, module: bool = True) -> None:
        if self.instance_valued(value):
            self.instances.add(name)
        if self.registrar(value):
            self.registrars.add(name)
        if self.is_tracked(value):
            self.classes.add(name)
        elif self.contains_tracked(value):
            self.containers.add(name)
        elif self.names_class(value):
            self.names.add(name)
        elif (checker := self.checker(value)) is not None:
            self.checkers.setdefault(name, checker)
        elif module and (path := self.module_path(value)) is not None:
            # First binding wins, so a cycle such as ``a = b.c; b = a``
            # cannot grow a path forever: each pass only adds names.
            self.modules.setdefault(name, path)

    def _bind_targets(self, target: ast.expr, value: ast.expr) -> None:
        if isinstance(target, ast.Name):
            self.assigned.add(target.id)
            self._bind(target.id, value)
        elif isinstance(target, ast.Attribute):
            self.assigned.add(target.attr)
            self._bind(target.attr, value, module=False)
        elif isinstance(target, ast.Subscript):
            # TABLE[key] = cls puts class info in TABLE.
            base = target.value
            if isinstance(base, ast.Name | ast.Attribute):
                name = base.id if isinstance(base, ast.Name) else base.attr
                if self.contains_tracked(value):
                    self.containers.add(name)
                elif self.names_class(value):
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
                    self.assigned.add(alias.asname)
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
                    self.instances.update(
                        name
                        for module, name in self.instance_exports
                        if module == base
                    )
                    continue
                local = alias.asname or alias.name
                if local != alias.name:
                    self.assigned.add(local)
                if (
                    alias.name in TRACKED_NAMES
                    or (base, alias.name) in self.exports
                ):
                    self.classes.add(local)
                elif (base, alias.name) in self.instance_exports:
                    self.instances.add(local)
                elif alias.name in _TYPE_CHECK_CALLS:
                    self.checkers.setdefault(local, alias.name)
                elif alias.name == "register":
                    self.registrars.add(local)
                else:
                    self.modules.setdefault(local, f"{base}.{alias.name}")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                self._bind_targets(target, node.value)
        elif isinstance(node, ast.AnnAssign | ast.NamedExpr | ast.AugAssign):
            if node.value is not None:
                self._bind_targets(node.target, node.value)
            elif isinstance(node.target, ast.Name):
                self.assigned.add(node.target.id)
        elif isinstance(node, ast.For | ast.AsyncFor | ast.comprehension):
            for item in ast.walk(node.target):
                if isinstance(item, ast.Name):
                    self.assigned.add(item.id)
            if self.contains_tracked(node.iter):
                self._bind_loop(node.target)
        elif isinstance(node, ast.ClassDef):
            self.assigned.add(node.name)
        elif isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
        ):
            if not isinstance(node, ast.Lambda):
                self.assigned.add(node.name)
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

    def imports(self, tree: ast.AST) -> dict[str, str]:
        """Name the path each import statement binds, unresolved."""
        bound: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        bound.setdefault(alias.asname, alias.name)
                    else:
                        top = alias.name.split(".")[0]
                        bound.setdefault(top, top)
            elif isinstance(node, ast.ImportFrom):
                base = self._from_base(node)
                for alias in node.names:
                    if alias.name != "*":
                        bound.setdefault(
                            alias.asname or alias.name, f"{base}.{alias.name}"
                        )
        return bound

    def _state(self) -> tuple:
        return (
            dict(self.modules),
            set(self.classes),
            set(self.containers),
            set(self.names),
            dict(self.checkers),
            set(self.instances),
            set(self.registrars),
            set(self.assigned),
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

    def _decorator_path(self, target: ast.expr) -> str | None:
        """Return the path a decorator resolves to, if it can be trusted.

        A name the module binds other than by import resolves to nothing,
        and a bare name it does not import is a builtin.
        """
        root = target
        while isinstance(root, ast.Attribute):
            root = root.value
        if not isinstance(root, ast.Name) or root.id in self.assigned:
            return None
        if isinstance(target, ast.Name) and target.id not in self.modules:
            return f"builtins.{target.id}"
        return self.module_path(target)

    def _accessor_of(self, node: ast.expr, properties: set[str]) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and node.attr in _PROPERTY_METHODS
            and isinstance(node.value, ast.Name)
            and node.value.id in properties
        )

    def find_accessors(self, roots: Iterable[ast.AST]) -> None:
        """Record the decorators that are a property's own accessors.

        ``@name.setter``, ``.getter`` or ``.deleter`` counts only in a
        class body where ``name`` is, at that point, a function whose
        outermost decorator is ``property`` or such an accessor. Any other
        binding of the name in that body ends it.
        """
        for root in roots:
            for node in ast.walk(root):
                if not isinstance(node, ast.ClassDef):
                    continue
                properties: set[str] = set()
                for statement in _statements(node.body):
                    if not isinstance(
                        statement, ast.FunctionDef | ast.AsyncFunctionDef
                    ):
                        properties -= _bound_names(statement)
                        continue
                    decorators = statement.decorator_list
                    for decorator in decorators:
                        if self._accessor_of(decorator, properties):
                            self.accessors.add(id(decorator))
                    if decorators and (
                        id(decorators[0]) in self.accessors
                        or self._decorator_path(decorators[0])
                        == "builtins.property"
                    ):
                        properties.add(statement.name)
                    else:
                        properties.discard(statement.name)

    def _benign_decorator(self, node: ast.expr) -> bool:
        """Return whether a decorator leaves annotations unread.

        A dispatcher's ``register`` reads only the hint it dispatches on,
        which is checked on its own; called with a class, it reads none.
        Any ``register`` is taken for a dispatcher's, by its spelling.
        """
        if self.registrar(node) or (
            isinstance(node, ast.Call) and self.registrar(node.func)
        ):
            return True
        if id(node) in self.accessors:
            return True
        target = node.func if isinstance(node, ast.Call) else node
        return self._decorator_path(target) in _BENIGN_DECORATORS

    def trusts_class(self, node: ast.ClassDef) -> bool:
        """Return whether a class leaves its annotations unread.

        Its decorators must all be benign, and it may have no base but
        ``object`` and no keywords, since a base or metaclass may read them.
        """
        return (
            all(map(self._benign_decorator, node.decorator_list))
            and not node.keywords
            and all(
                isinstance(base, ast.Name)
                and base.id == "object"
                and base.id not in self.assigned
                and base.id not in self.modules
                for base in node.bases
            )
        )

    def registers(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Return whether a decorator dispatches on the function's hints."""
        return any(map(self.registrar, node.decorator_list))

    def dispatch_hint(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ast.expr | None:
        """Return the hint a ``register`` decorator dispatches on, if any."""
        if not self.registers(node):
            return None
        hints = _hints(node)
        return hints[0] if hints else None

    def _hint_parts(self, hint: ast.expr) -> list[ast.expr]:
        """Return a hint and each expression its strings spell, nested too.

        Python evaluates a string hint as the expression it spells, and a
        string inside that again, so ``"'R'"`` and ``ForwardRef("R")`` both
        name ``R``. Each parsed part takes the hint's location.
        """
        cached = self.hint_cache.get(id(hint))
        if cached is not None and cached[0] is hint:
            return cached[1]
        parts = [hint]
        index = 0
        while index < len(parts) and len(parts) < _HINT_PARTS:
            for node in ast.walk(parts[index]):
                text = self.text(node) if isinstance(node, ast.expr) else None
                if text is None:
                    continue
                try:
                    parsed = ast.parse(text.strip(), mode="eval").body
                except (SyntaxError, ValueError):
                    continue
                _relocate(parsed, hint)
                for item in ast.walk(parsed):
                    for child in ast.iter_child_nodes(item):
                        self.hint_parents[id(child)] = item
                parts.append(parsed)
            index += 1
        self.hint_cache[id(hint)] = (hint, parts)
        return parts

    def _names_tracked(self, node: ast.expr) -> bool:
        """Return whether a node names a tracked class, as code or text."""
        if self.is_tracked(node) or (
            isinstance(node, ast.Name | ast.Attribute)
            and self._class_part(node)
        ):
            return True
        text = self.text(node)
        return text is not None and (_names_class(text) or _names_module(text))

    def mentions(self, hint: ast.expr) -> bool:
        """Return whether a hint names a tracked class, strings included."""
        return any(
            isinstance(node, ast.expr) and self._names_tracked(node)
            for part in self._hint_parts(hint)
            for node in ast.walk(part)
        )

    def walked_hints(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[ast.expr]:
        """Return the hints the catch-all reads.

        A decorator outside the benign ones may read any hint, so all of a
        function's hints count then, except the one dispatched on, which
        has its own check.
        """
        if all(map(self._benign_decorator, node.decorator_list)):
            return []
        dispatch = self.dispatch_hint(node)
        return [hint for hint in _hints(node) if hint is not dispatch]

    def facts(self, tree: ast.Module) -> None:
        """Record what the module holds where the catch-all does not look.

        That is its export listings, whether any docstring names a tracked
        class or module or a probe name, and whether any annotation left to
        Python (not read by a decorator the catch-all distrusts) names a
        tracked class. Reads of these are then checked.
        """
        for statement in _statements(tree.body):
            if _lists_exports(statement):
                self.listing_values.add(id(statement.value))
            elif isinstance(statement, ast.Expr) and _extends_exports(
                statement.value
            ):
                self.listing_calls.add(id(statement.value))
                self.listing_loads.add(id(statement.value.func.value))
        docstrings = [
            ast.get_docstring(node, clean=False)
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.Module
                | ast.FunctionDef
                | ast.AsyncFunctionDef
                | ast.ClassDef,
            )
        ]
        self.holds_docstring = any(
            _names_class(text) or _names_module(text) or _names_probe(text)
            for text in docstrings
            if text is not None
        )
        hints = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if all(map(self._benign_decorator, node.decorator_list)):
                    dispatch = self.dispatch_hint(node)
                    hints += [h for h in _hints(node) if h is not dispatch]
            elif isinstance(node, ast.ClassDef) and self.trusts_class(node):
                hints += _class_annotations(node)
        hints += [
            statement.annotation
            for statement in _statements(tree.body)
            if isinstance(statement, ast.AnnAssign)
        ]
        self.holds_annotations = any(map(self.mentions, hints))

    def binds_tracked(self) -> bool:
        return bool(self.classes or self.containers or self.names) or bool(
            self.instances
        )

    def _module_object(self, node: ast.expr) -> bool:
        """Return whether ``node`` is a module object whose use counts."""
        if not isinstance(
            node, ast.Name | ast.Attribute | ast.Call | ast.Subscript
        ):
            return False
        path = self.module_path(node)
        return path is not None and (
            path in self.introspected
            or path == OWN_MODULE
            or path.startswith(f"{OWN_MODULE}.")
        )

    def _member(self, node: ast.expr) -> bool:
        """Return whether ``node`` is defined by a module whose use counts."""
        path = self.module_path(node)
        return path is not None and (
            path.startswith(f"{OWN_MODULE}.")
            or self._owner(path) in self.introspected
        )

    def _parent(self, node: ast.AST) -> ast.AST | None:
        parent = self.parents.get(id(node))
        return (
            parent if parent is not None else self.hint_parents.get(id(node))
        )

    def _benign_module_use(self, node: ast.expr) -> bool:
        parent = self._parent(node)
        return (
            isinstance(parent, ast.Attribute)
            and parent.value is node
            and not parent.attr.startswith("__")
        )

    def _benign_instance_use(self, node: ast.expr) -> bool:
        """Return whether an instance is only used, not compared or shown.

        It may be bound to a name (which is then tracked) or a parameter
        default, returned, passed to a call that is not a comparison,
        lookup, text or introspection function, have a public attribute
        read, be tested for truth or be compared with ``None`` by identity.
        Every other use counts.
        """
        parent = self._parent(node)
        if isinstance(parent, ast.Attribute):
            return parent.value is node and not parent.attr.startswith("__")
        if isinstance(parent, ast.arguments):
            return True
        if isinstance(parent, ast.keyword):
            parent = self._parent(parent)
            return isinstance(parent, ast.Call) and (
                _call_name(parent.func) not in _INSTANCE_SINKS
            )
        if isinstance(parent, ast.Call):
            return node is not parent.func and (
                _call_name(parent.func) not in _INSTANCE_SINKS
            )
        if isinstance(parent, ast.Assign | ast.AnnAssign | ast.NamedExpr):
            targets = (
                parent.targets
                if isinstance(parent, ast.Assign)
                else [parent.target]
            )
            return node is parent.value and all(map(_binds_by_name, targets))
        if isinstance(parent, ast.Compare):
            others = [
                item
                for item in (parent.left, *parent.comparators)
                if item is not node
            ]
            return all(
                isinstance(op, ast.Is | ast.IsNot) for op in parent.ops
            ) and all(
                isinstance(item, ast.Constant) and item.value is None
                for item in others
            )
        if isinstance(parent, ast.UnaryOp):
            return isinstance(parent.op, ast.Not)
        return isinstance(
            parent,
            ast.If
            | ast.While
            | ast.IfExp
            | ast.Assert
            | ast.BoolOp
            | ast.Return
            | ast.Yield
            | ast.YieldFrom
            | ast.Lambda
            | ast.Expr,
        )

    def _kind(self, node: ast.AST) -> str | None:
        """Name the specific check ``node`` makes, if it makes one."""
        if isinstance(node, ast.expr) and not isinstance(
            node, ast.Name | ast.Attribute
        ):
            text = self.text(node)
            if text in PROBE_NAMES:
                return "private-member-probe"
            if text is not None and (kind := self._read_string(text)):
                return kind
        if isinstance(node, ast.Call):
            return self._call_kind(node)
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            if any(self.contains_tracked(item) for item in operands):
                if any(_is_type_call(item) for item in operands):
                    return "type-compare"
                if any(
                    isinstance(item, ast.Attribute)
                    and item.attr == "__class__"
                    for item in operands
                ):
                    return "__class__-compare"
                return "class-compare"
            if any(self.names_class(item) for item in operands):
                return "name-compare"
            if any(self.names_module(item) for item in operands):
                return "module-compare"
        elif isinstance(node, ast.MatchValue):
            # case rng.ProjectionRNGRegistry: compares the subject by ==.
            if self.contains_tracked(node.value):
                return "class-compare"
            if self.names_class(node.value):
                return "name-compare"
            if self.names_module(node.value):
                return "module-compare"
        elif isinstance(node, ast.MatchClass):
            if self.contains_tracked(node.cls):
                return "match-class"
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            hint = self.dispatch_hint(node)
            if hint is not None and self.mentions(hint):
                return "dispatch-annotation"
        elif isinstance(node, ast.ImportFrom):
            if any(alias.name == _EXPORT_NAME for alias in node.names):
                return "export-read"
        elif isinstance(node, ast.Name):
            return self._read_name(node)
        elif isinstance(node, ast.Attribute):
            return self._read_attribute(node)
        return None

    def _call_kind(self, node: ast.Call) -> str | None:
        checker = self.checker(node.func)
        if (
            checker is not None
            and len(node.args) >= 2
            and self.contains_tracked(node.args[1])
        ):
            return checker
        name = _call_name(node.func)
        if (
            name in _DUNDER_CHECKS
            and isinstance(node.func, ast.Attribute)
            and (
                self.is_tracked(node.func.value)
                or any(map(self.contains_tracked, node.args[:1]))
            )
        ):
            return "dunder-check"
        if (
            self.registrar(node.func)
            and node.args
            and self.contains_tracked(node.args[0])
        ):
            return "dispatch-register"
        path = self.module_path(node.func)
        if name in _SOURCE_CALLS or (
            path is not None and path.split(".")[0] in _SOURCE_MODULES
        ):
            return "source-read"
        if self.holds_docstring and name in _DOC_CALLS:
            return "docstring-read"
        if self.holds_annotations and name in _ANNOTATION_CALLS:
            return "annotation-read"
        if (
            name in _NAMESPACE_CALLS
            and not node.args
            and not node.keywords
            and self.binds_tracked()
        ):
            return "namespace-read"
        if (
            _code_call(node.func)
            and node.args
            and (
                id(node) in self.unexpanded
                or (self.text(node.args[0]) is None and self.binds_tracked())
            )
        ):
            # Code the folder cannot read may name what the module binds,
            # and code nested past the depth the scan parses may name
            # anything.
            return "dynamic-code"
        if (
            name in _INTROSPECTION_CALLS
            and node.args
            and self._member(node.args[0])
        ):
            return "member-introspection"
        return None

    def _read_string(self, text: str) -> str | None:
        """Name the read a string spells: an export, docstring or hint."""
        if text == _EXPORT_NAME:
            return "export-read"
        if self.holds_docstring and text in _DOC_ATTRIBUTES:
            return "docstring-read"
        if self.holds_annotations and text in _ANNOTATION_ATTRIBUTES:
            return "annotation-read"
        return None

    def _read_name(self, node: ast.Name) -> str | None:
        if not isinstance(node.ctx, ast.Load):
            return None
        if node.id == _EXPORT_NAME and id(node) not in self.listing_loads:
            return "export-read"
        if node.id == "__doc__" and self.holds_docstring:
            return "docstring-read"
        if node.id in {"__annotations__", "__annotate__"} and (
            self.holds_annotations
        ):
            return "annotation-read"
        return None

    def _read_attribute(self, node: ast.Attribute) -> str | None:
        attribute = node.attr
        if attribute in PROBE_NAMES and (
            self.source.module not in TRACKED_MODULES
        ):
            return "private-member-probe"
        if not isinstance(node.ctx, ast.Load):
            return None
        if attribute == _EXPORT_NAME:
            return "export-read"
        if self.holds_docstring and attribute in _DOC_ATTRIBUTES:
            return "docstring-read"
        if self.holds_annotations and attribute in _ANNOTATION_ATTRIBUTES:
            return "annotation-read"
        if attribute.startswith("__") and self._member(node.value):
            return "member-introspection"
        return None

    def _mention(self, node: ast.expr, listing: bool) -> str | None:
        """Name what a node outside every specific check says of a class.

        A reference to a tracked class or to class info, a string holding a
        tracked class's or module's name, a module object put to any use
        but a plain attribute read, and an instance put to any use the
        benign list leaves out each count.
        """
        if self.is_tracked(node) or (
            isinstance(node, ast.Name | ast.Attribute)
            and self._class_part(node)
        ):
            return "class-reference"
        text = None if listing else self.text(node)
        if text is not None and _names_class(text):
            return "class-name-string"
        if text is not None and _names_module(text):
            return "module-name-string"
        if self._module_object(node) and not self._benign_module_use(node):
            return "module-reference"
        if self.instance_valued(node) and not self._benign_instance_use(node):
            return "instance-reference"
        return None

    def _children(self, node: ast.AST) -> Iterable[tuple[ast.AST, bool]]:
        """Yield the children a mention can hide in, and which list names.

        Annotations are skipped, except where a decorator the catch-all
        does not trust may read them; so is the callee of a construction.
        Strings inside a module-level ``__all__`` listing are flagged as
        listing names.
        """
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            arguments = node.args
            yield from ((item, False) for item in node.decorator_list)
            yield from ((item, False) for item in node.type_params)
            yield from ((item, False) for item in arguments.defaults)
            yield from (
                (item, False) for item in arguments.kw_defaults if item
            )
            for hint in self.walked_hints(node):
                yield from ((part, False) for part in self._hint_parts(hint))
            yield from ((item, False) for item in node.body)
        elif isinstance(node, ast.ClassDef):
            yield from ((item, False) for item in node.decorator_list)
            yield from ((item, False) for item in node.type_params)
            yield from ((item, False) for item in node.bases)
            yield from ((item.value, False) for item in node.keywords)
            if not self.trusts_class(node):
                for hint in _class_annotations(node):
                    yield from (
                        (part, False) for part in self._hint_parts(hint)
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
                yield node.value, id(node.value) in self.listing_values
        elif isinstance(node, ast.Assign | ast.AugAssign):
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            yield from ((item, False) for item in targets)
            yield node.value, id(node.value) in self.listing_values
        elif isinstance(node, ast.Call) and self.is_tracked(node.func):
            yield from ((item, False) for item in node.args)
            yield from ((item.value, False) for item in node.keywords)
        elif isinstance(node, ast.Call) and id(node) in self.listing_calls:
            yield node.func, False
            yield from ((item, True) for item in node.args)
        else:
            yield from ((item, False) for item in ast.iter_child_nodes(node))

    def references(self, tree: ast.Module, claimed: set[int]) -> set[ScanHit]:
        """Report every other use of a tracked class, module or instance.

        This is the catch-all under the specific checks. Benign places are
        imports, string statements (a docstring is the only one Python
        keeps, and reading one is a specific check), module-level
        ``__all__`` listings, annotations no distrusted decorator reads,
        the callee of a construction, plain attribute reads on a module,
        and the uses of an instance ``_benign_instance_use`` lists. A node
        a specific check reported is skipped with everything under it. The
        walk keeps its own stack, so deep expressions cannot exhaust
        recursion.
        """
        found = set()
        stack: list[tuple[ast.AST, bool]] = [(tree, False)]
        while stack:
            node, listing = stack.pop()
            if id(node) in claimed or isinstance(
                node, ast.Import | ast.ImportFrom
            ):
                continue
            if isinstance(node, ast.Expr) and _is_string_constant(node.value):
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
        """Report the specific checks, then every other use.

        A specific check is reported at the outermost node that makes it,
        and nothing under that node is reported again, except in the body
        of a function whose dispatch hint was reported.
        """
        self.parents = {
            id(child): node
            for node in ast.walk(tree)
            for child in ast.iter_child_nodes(node)
        }
        try:
            found = set()
            claimed: set[int] = set()
            stack: list[ast.AST] = [tree]
            while stack:
                node = stack.pop()
                kind = self._kind(node)
                if kind is not None:
                    found.add(ScanHit(self.source.path, node.lineno, kind))
                    if not isinstance(
                        node, ast.FunctionDef | ast.AsyncFunctionDef
                    ):
                        claimed.add(id(node))
                        continue
                stack.extend(ast.iter_child_nodes(node))
            return found | self.references(tree, claimed)
        finally:
            self.parents = {}


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
    it is inert when none names a tracked class or module, whatever the
    case, and none is a probe name or a name a read of a benign place
    spells.
    """
    if not isinstance(node, ast.Tuple | ast.List | ast.Set | ast.Dict):
        return False
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, ast.Constant):
            value = item.value
            if isinstance(value, bytes):
                value = value.decode("latin-1")
            if isinstance(value, str) and (
                _names_class(value)
                or _names_module(value)
                or value in PROBE_NAMES
                or value in _SPECIAL_STRINGS
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


def _folds_through(parent: ast.AST, field: str) -> bool:
    """Return whether the folder or a hint parser reads this child.

    It reads operands, subscripts, f-string parts, method receivers, the
    arguments of the calls it folds and of the calls whose literal is
    code, the items of a container it reads, and annotations, whose
    strings are parsed as code.
    """
    if isinstance(
        parent,
        ast.BinOp
        | ast.UnaryOp
        | ast.Subscript
        | ast.Starred
        | ast.Attribute
        | ast.FormattedValue
        | ast.JoinedStr
        | ast.Tuple
        | ast.List
        | ast.Set
        | ast.Dict
        | ast.arg,
    ):
        return True
    if isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
        return field == "returns"
    if isinstance(parent, ast.AnnAssign):
        return field == "annotation"
    if isinstance(parent, ast.Call) and field in {"args", "keywords"}:
        return (
            _call_name(parent.func)
            in _FOLD_FUNCTIONS | _FOLD_METHODS | _CODE_CALLS
        )
    return False


def _prune(tree: ast.Module) -> ast.Module:
    """Replace each inert literal container with ``None``, in place.

    No check reports or binds anything from an inert container, and none
    is pruned where the folder or a hint parser could read it, so the hits
    are unchanged (a differential test pins that); the data modules' large
    tables stop costing time and memory.
    """
    stack: list[tuple[ast.AST, bool]] = [(tree, False)]
    while stack:
        node, inherited = stack.pop()
        for field, value in ast.iter_fields(node):
            items = value if isinstance(value, list) else [value]
            for index, item in enumerate(items):
                if not isinstance(item, ast.AST):
                    continue
                # A keyword's value is read as its call's arguments are.
                read = (
                    inherited
                    if isinstance(node, ast.keyword)
                    else _folds_through(node, field)
                )
                if not read and _inert(item):
                    stub = ast.copy_location(ast.Constant(None), item)
                    if isinstance(value, list):
                        value[index] = stub
                    else:
                        setattr(node, field, stub)
                else:
                    stack.append((item, read))
    return tree


def scan_sources(
    sources: Iterable[ScanSource], prune: bool = True
) -> tuple[ScanHit, ...]:
    """Find type checks on either class across ``sources`` (condition 2).

    Every module is parsed. No text filter runs first, because the parser
    joins adjacent literals, decodes escapes and normalizes identifiers, so
    a module can spell a class without its text holding the name. Inert
    literal containers are pruned unless ``prune`` is false. Literal code a
    module evaluates is parsed and checked with it. Re-exports of the
    classes and of instances are followed to a fixed point across modules;
    modules re-exported by import statements are followed too.
    """
    sources = tuple(sources)
    trees = {}
    embedded = {}
    memos = {source.path: _FoldMemo(source.path) for source in sources}
    unexpanded: dict[str, set[int]] = {}
    for source in sources:
        tree = _parse(source)
        trees[source.path] = _prune(tree) if prune else tree
        embedded[source.path] = _embedded(
            trees[source.path],
            memos[source.path],
            unexpanded.setdefault(source.path, set()),
        )
    binders = {
        path: [
            node
            for root in (tree, *embedded[path])
            for node in ast.walk(root)
            if isinstance(node, _BINDING_NODES)
        ]
        for path, tree in trees.items()
    }
    exports = set(TRACKED_CLASSES)
    instance_exports: set[tuple[str, str]] = set()
    # What each module's import statements bind: fixed before the loop, so
    # a path never changes between passes and the loop settles.
    module_exports: dict[tuple[str, str], str] = {}
    for source in sources:
        reader = _ModuleBindings(source, set(), set(), {}, memos[source.path])
        for root in (trees[source.path], *embedded[source.path]):
            for name, target in reader.imports(root).items():
                module_exports.setdefault((source.module, name), target)
    while True:
        scopes = {}
        for source in sources:
            scope = _ModuleBindings(
                source,
                exports,
                instance_exports,
                module_exports,
                memos[source.path],
            )
            scope.bind(binders[source.path])
            scopes[source.path] = scope
        found = {
            (scope.source.module, name)
            for scope in scopes.values()
            for name in scope.classes
        }
        found_instances = {
            (scope.source.module, name)
            for scope in scopes.values()
            for name in scope.instances
        }
        if found <= exports and found_instances <= instance_exports:
            break
        exports = exports | found
        instance_exports = instance_exports | found_instances
    known = frozenset(source.module for source in sources) | TRACKED_MODULES
    for path, scope in scopes.items():
        scope.known_modules = known
        scope.unexpanded = unexpanded[path]
        scope.find_accessors((trees[path], *embedded[path]))
        scope.facts(trees[path])
    introspected = frozenset(
        {module for module, _ in exports}
        | TRACKED_MODULES
        | {
            scope.source.module
            for scope in scopes.values()
            if scope.holds_docstring or scope.holds_annotations
        }
    )
    hits = set()
    for path, scope in scopes.items():
        scope.introspected = introspected
        for root in (trees[path], *embedded[path]):
            hits |= scope.hits(root)
    return tuple(sorted(hits))


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
_DIRECT_IMPORT = (
    "from populace_dynamics.open_population.streams import DirectRNGStreams"
)
_INSTANCE_IMPORT = f"{_IMPORT}\nREFERENCE = ProjectionRNGRegistry(0, 2)"


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
    "class info read by a method": (
        _check(
            "isinstance(x, KINDS.get('registry', int))",
            f"{_IMPORT}\nKINDS = {{'registry': ProjectionRNGRegistry}}"
            "  # alias",
        ),
        "isinstance",
    ),
    "class info rebuilt": (
        _check(
            "isinstance(x, tuple(KINDS))",
            f"{_IMPORT}\nKINDS = [int, ProjectionRNGRegistry]  # alias",
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
    "single-dispatch annotation in nested quotes": (
        _dispatch("\"'R'\"", f"{_IMPORT} as R"),
        "dispatch-annotation",
    ),
    "single-dispatch annotation through ForwardRef": (
        _dispatch(
            'ForwardRef("R")',
            f"{_IMPORT} as R\nfrom typing import ForwardRef",
        ),
        "dispatch-annotation",
    ),
    "register bound to a name": (
        textwrap.dedent("""
            from functools import singledispatch
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @singledispatch
            def f(x):
                return 0
            reg = f.register
            @reg
            def _(x: ProjectionRNGRegistry):  # check
                return 1
        """),
        "dispatch-annotation",
    ),
    "register read through getattr": (
        textwrap.dedent("""
            from functools import singledispatch
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @singledispatch
            def f(x):
                return 0
            @getattr(f, "register")
            def _(x: ProjectionRNGRegistry):  # check
                return 1
        """),
        "dispatch-annotation",
    ),
    "dispatch on the return hint": (
        textwrap.dedent("""
            from functools import singledispatch
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @singledispatch
            def f(x):
                return 0
            @f.register
            def _(x) -> ProjectionRNGRegistry:  # check
                return 1
        """),
        "dispatch-annotation",
    ),
    "dispatch on *args": (
        textwrap.dedent("""
            from functools import singledispatch
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @singledispatch
            def f(x):
                return 0
            @f.register
            def _(*args: ProjectionRNGRegistry):  # check
                return 1
        """),
        "dispatch-annotation",
    ),
    "dispatch on the first, keyword-only hint": (
        textwrap.dedent("""
            from functools import singledispatch
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @singledispatch
            def f(x):
                return 0
            @f.register
            def _(x, *, y: ProjectionRNGRegistry = None):  # check
                return 1
        """),
        "dispatch-annotation",
    ),
    "register wrapped in partial": (
        # An unknown decorator may read any hint, so the hint itself counts.
        textwrap.dedent("""
            from functools import partial, singledispatch
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @singledispatch
            def f(x):
                return 0
            @partial(f.register)
            def _(x: ProjectionRNGRegistry):  # check
                return 1
        """),
        "class-reference",
    ),
    "local decorator named like a trusted one": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            def property(function):
                function.kind = function.__annotations__["x"]
                return function
            @property
            def g(x: ProjectionRNGRegistry):  # check
                pass
            def f(x):
                return isinstance(x, g.kind)
        """),
        "class-reference",
    ),
    "annotation of a class with a base": (
        textwrap.dedent("""
            from typing import NamedTuple
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            class Holder(NamedTuple):
                kind: ProjectionRNGRegistry  # check
            def f(x):
                return isinstance(x, Holder.__annotations__["kind"])
        """),
        "class-reference",
    ),
    "the direct class": (
        _check("not isinstance(x, DirectRNGStreams)", _DIRECT_IMPORT),
        "isinstance",
    ),
    "the direct class's name": (
        _check("type(x).__name__ == 'DirectRNGStreams'", ""),
        "name-compare",
    ),
    "module of the direct class": (
        _check(
            "type(x).__module__ == DirectRNGStreams.__module__", _DIRECT_IMPORT
        ),
        "module-compare",
    ),
    "module of another class in the registry's module": (
        _check(
            "type(x).__module__ == ProjectionModule.__module__",
            "from populace_dynamics.engine.rng import ProjectionModule",
        ),
        "module-compare",
    ),
    "module found by inspect": (
        _check(
            "type(x).__module__ == inspect.getmodule(ProjectionModule).__name__",
            "import inspect\n"
            "from populace_dynamics.engine.rng import ProjectionModule",
        ),
        "member-introspection",
    ),
    "module name passed to operator.eq": (
        _check(
            "operator.eq(type(x).__module__, rng.__name__)",
            "from populace_dynamics.engine import rng\nimport operator",
        ),
        "module-reference",
    ),
    "module of a member of the registry's module": (
        _check(
            "operator.eq(type(x).__module__, rng.ProjectionModule.__module__)",
            "from populace_dynamics.engine import rng\nimport operator",
        ),
        "member-introspection",
    ),
    "exports read from a module": (
        _check(
            "type(x).__name__ in engine.__all__",
            "from populace_dynamics import engine",
        ),
        "export-read",
    ),
    "module passed to getattr with a computed name": (
        _check(
            "isinstance(x, getattr(rng, ''.join(PARTS)))",
            "from populace_dynamics.engine import rng\n"
            "PARTS = ['Projection', 'RNGRegistry']",
        ),
        "module-reference",
    ),
    "module namespace read": (
        textwrap.dedent("""
            from populace_dynamics.engine import rng
            def f(x):
                table = vars(rng)  # check
                return isinstance(x, table["ProjectionRNGRegistry"])  # label
        """),
        "module-reference",
    ),
    "module name tested by a method": (
        _check(
            "type(x).__module__.startswith('populace_dynamics.open_population')",
            "",
        ),
        "module-name-string",
    ),
    "class name tested by a method": (
        _check("type(x).__name__.endswith('ProjectionRNGRegistry')", ""),
        "class-name-string",
    ),
    "equality with an instance": (
        _check("x == ProjectionRNGRegistry(0, 2)"),
        "instance-reference",
    ),
    "membership in a set of instances": (
        _check("x in {ProjectionRNGRegistry(0, 2)}"),
        "instance-reference",
    ),
    "lookup keyed by an instance": (
        _check("{ProjectionRNGRegistry(0, 2): True}.get(x, False)"),
        "instance-reference",
    ),
    "equality with an instance bound to a name": (
        _check("x == REFERENCE", _INSTANCE_IMPORT),
        "instance-reference",
    ),
    "type of an instance bound to a name": (
        _check("type(x) is type(REFERENCE)", _INSTANCE_IMPORT),
        "type-compare",
    ),
    "type of an instance bound in a conditional": (
        _check(
            "type(x) is type(REFERENCE)",
            f"{_IMPORT}\nREFERENCE = ProjectionRNGRegistry(0, 2) if 1 else 0",
        ),
        "type-compare",
    ),
    "type of an instance bound in a boolean": (
        _check(
            "type(x) is type(REFERENCE)",
            f"{_IMPORT}\nREFERENCE = 1 and ProjectionRNGRegistry(0, 2)",
        ),
        "type-compare",
    ),
    "class of an instance bound to a name": (
        _check("isinstance(x, REFERENCE.__class__)", _INSTANCE_IMPORT),
        "isinstance",
    ),
    "module of an instance bound to a name": (
        _check("type(x).__module__ == REFERENCE.__module__", _INSTANCE_IMPORT),
        "module-compare",
    ),
    "instance passed to operator.eq": (
        _check(
            "operator.eq(REFERENCE, x)", f"{_INSTANCE_IMPORT}\nimport operator"
        ),
        "instance-reference",
    ),
    "instance rendered as text": (
        _check("repr(x)[:4] == repr(REFERENCE)[:4]", _INSTANCE_IMPORT),
        "instance-reference",
    ),
    "exports appended, then read": (
        textwrap.dedent("""
            __all__ = []
            __all__.append("ProjectionRNGRegistry")
            def f(x):
                return type(x).__name__ in __all__  # check
        """),
        "export-read",
    ),
    "exports extended, then read": (
        textwrap.dedent("""
            __all__ = []
            __all__.extend(["ProjectionRNGRegistry"])
            def f(x):
                return type(x).__name__ in __all__  # check
        """),
        "export-read",
    ),
    "exports counted": (
        textwrap.dedent("""
            __all__ = ["ProjectionRNGRegistry"]
            def f(x):
                return bool(__all__.count(type(x).__name__))  # check
        """),
        "export-read",
    ),
    "exports held as a mapping": (
        textwrap.dedent("""
            __all__ = {"ProjectionRNGRegistry": True}  # label
            def f(x):
                return __all__.get(type(x).__name__, False)  # check
        """),
        "export-read",
    ),
    "a local named __all__": (
        textwrap.dedent("""
            def f(x):
                name = type(x).__name__
                __all__ = [name.endswith("ProjectionRNGRegistry")]  # label
                return __all__[0]  # check
        """),
        "export-read",
    ),
    "a local __all__ unpacked into operator.eq": (
        textwrap.dedent("""
            import operator
            def f(x):
                __all__ = ("ProjectionRNGRegistry", type(x).__name__)  # label
                return operator.eq(*__all__)  # check
        """),
        "export-read",
    ),
    "function docstring read from code constants": (
        textwrap.dedent("""
            def f(x):
                "ProjectionRNGRegistry"
                return type(x).__name__ in f.__code__.co_consts  # check
        """),
        "docstring-read",
    ),
    "function docstring read": (
        textwrap.dedent("""
            def label():
                "ProjectionRNGRegistry"
            def f(x):
                return type(x).__name__ == label.__doc__  # check
        """),
        "docstring-read",
    ),
    "class docstring read": (
        textwrap.dedent("""
            class Label:
                "ProjectionRNGRegistry"
            def f(x):
                return type(x).__name__ == Label.__doc__  # check
        """),
        "docstring-read",
    ),
    "module docstring read": (
        textwrap.dedent('''
            """ProjectionRNGRegistry"""
            def f(x):
                return type(x).__name__ == __doc__  # check
        '''),
        "docstring-read",
    ),
    "docstring read by inspect": (
        textwrap.dedent("""
            import inspect
            def label():
                "ProjectionRNGRegistry"
            def f(x):
                return type(x).__name__ == inspect.getdoc(label)  # check
        """),
        "docstring-read",
    ),
    "annotation evaluated as a check": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            check = lambda c: lambda y: isinstance(y, c)
            def inner(x: check(ProjectionRNGRegistry)):
                pass
            def f(x):
                return inner.__annotations__["x"](x)  # check
        """),
        "annotation-read",
    ),
    "type hints read": (
        textwrap.dedent("""
            import typing
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            class Holder:
                kind: ProjectionRNGRegistry
            def f(x):
                hints = typing.get_type_hints(Holder)  # check
                return isinstance(x, hints["kind"])
        """),
        "annotation-read",
    ),
    "dataclass fields read": (
        textwrap.dedent("""
            from dataclasses import dataclass, fields
            from populace_dynamics.engine.rng import ProjectionRNGRegistry
            @dataclass
            class Holder:
                kind: ProjectionRNGRegistry | None = None
            def f(x):
                return isinstance(x, fields(Holder)[0].type)  # check
        """),
        "annotation-read",
    ),
    "module namespace searched": (
        _check("type(x) in globals().values()"),
        "namespace-read",
    ),
    "source text read": (
        textwrap.dedent("""
            import inspect
            def label():
                pass  # ProjectionRNGRegistry
            def f(x):
                return type(x).__name__ in inspect.getsource(label)  # check
        """),
        "source-read",
    ),
    "code passed to eval": (
        _check("eval('isinstance(x, R)')", f"{_IMPORT} as R"),
        "isinstance",
    ),
    "code held in a name, passed to eval": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry as R
            CODE = "isinstance(x, " + "R)"
            def f(x):
                return eval(CODE)  # check
        """),
        "dynamic-code",
    ),
    "code passed to exec": (
        textwrap.dedent("""
            from populace_dynamics.engine.rng import ProjectionRNGRegistry as R
            exec("def f(x):\\n    return type(x) is R")  # check
        """),
        "type-compare",
    ),
    "class name built by format": (
        _check(
            "type(x).__name__ == '{}RNG{}'.format('Projection', 'Registry')",
            "",
        ),
        "name-compare",
    ),
    "class name built by %": (
        _check("type(x).__name__ == '%sRNGRegistry' % 'Projection'", ""),
        "name-compare",
    ),
    "class name built by join": (
        _check(
            "type(x).__name__ == ''.join(('Projection', 'RNG', 'Registry'))",
            "",
        ),
        "name-compare",
    ),
    "class name built in an f-string": (
        _check("type(x).__name__ == f\"{'Projection'}RNG{'Registry'!s}\"", ""),
        "name-compare",
    ),
    "class name reversed by a slice": (
        _check("type(x).__name__ == 'yrtsigeRGNRnoitcejorP'[::-1]", ""),
        "name-compare",
    ),
    "class name built by replace": (
        _check(
            "type(x).__name__ == 'ProjectionRNG-'.replace('-', 'Registry')", ""
        ),
        "name-compare",
    ),
    "class name in lower case": (
        _check("type(x).__name__.lower() == 'projectionrngregistry'", ""),
        "name-compare",
    ),
    "class name as bytes": (
        _check("type(x).__name__.encode() == b'ProjectionRNGRegistry'", ""),
        "name-compare",
    ),
    "class name as bytes in a nested tuple": (
        _check(
            "type(x).__name__.encode() in (b'a', (b'ProjectionRNGRegistry',))[1]",
            "",
        ),
        "name-compare",
    ),
    "module name built by join": (
        _check(
            "type(x).__module__ == '.'.join(('populace_dynamics', 'engine', 'rng'))",
            "",
        ),
        "module-compare",
    ),
    "module name built by format": (
        _check(
            "type(x).__module__ == "
            "'{}.{}.{}'.format('populace_dynamics', 'engine', 'rng')",
            "",
        ),
        "module-compare",
    ),
    "module name as bytes": (
        _check(
            "type(x).__module__.encode() == b'populace_dynamics.engine.rng'",
            "",
        ),
        "module-compare",
    ),
    "probe name as bytes": (
        _check("b'_period_sequence'.decode() in dir(x)", ""),
        "private-member-probe",
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
    filename = "invented_case.py"
    namespace = {"__name__": "invented_case"}
    # Compiled without this module's future imports, as a module of its own
    # would be; its text is registered so that source reads find it.
    linecache.cache[filename] = (
        len(text),
        None,
        text.splitlines(True),
        filename,
    )
    try:
        exec(compile(text, filename, "exec", dont_inherit=True), namespace)
        outcomes = [
            bool(namespace["f"](cls(0, 2)))
            for cls in (ProjectionRNGRegistry, DirectRNGStreams)
        ]
    finally:
        linecache.cache.pop(filename, None)
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
    # Trusted decorators, and a class with no base, leave hints unread.
    "import functools\n"
    "from dataclasses import dataclass\n"
    "class Holder(object):\n"
    "    registry: ProjectionRNGRegistry\n"
    "    @property\n"
    "    def current(self) -> ProjectionRNGRegistry:\n"
    "        return ProjectionRNGRegistry(draw_index=0, n_periods=1)\n"
    "    @current.setter\n"
    "    def current(self, value: ProjectionRNGRegistry) -> None:\n"
    "        pass\n"
    "@functools.lru_cache(maxsize=None)\n"
    "def g(n: int) -> 'ProjectionRNGRegistry':\n"
    "    return ProjectionRNGRegistry(draw_index=0, n_periods=n)\n"
    "@dataclass(frozen=True)\n"
    "class Config:\n"
    "    registry: ProjectionRNGRegistry | None = None\n",
    # An instance bound, tested for truth or None, passed on, read and
    # returned.
    "def f(n, sink):\n"
    "    registry = ProjectionRNGRegistry(draw_index=0, n_periods=n)\n"
    "    if registry is None or not registry:\n"
    "        return None\n"
    "    sink(registry, label=registry.n_periods)\n"
    "    other = registry if n else None\n"
    "    return registry.person_generator(1, 'aging', 0) or other\n",
    "def f(registry=ProjectionRNGRegistry(draw_index=0, n_periods=1)):\n"
    "    return registry.n_periods\n",
    # Folds that would build large text are refused, not computed.
    "def f(x):\n"
    "    a = 'ab' * 10 ** 12\n"
    "    b = 'ab' * 4096 * 4096\n"
    "    c = '{:99999}'.format(x) + '%99999s' % 'x'\n"
    "    d = 'x'.center(10 ** 9) + 'x'.center(99999)\n"
    "    e = 'abc'.replace('', 'x' * 4096) * 4096\n"
    "    return type(x).__name__ in (a, b, c, d, e)\n",
)


@pytest.mark.parametrize("body", NEGATIVE_BODIES)
def test_scan_ignores_unrelated_checks_and_ordinary_registry_use(body):
    """Each negative names the registry, so the scan parses it."""
    hits = scan_sources([_invented(_REGISTRY_IMPORT + body)])
    assert hits == (), describe(hits)


# A property's accessor is trusted only where its receiver is a property
# defined above it in the same class body. Each body follows the registry
# import and lists the lines of its hits: a distrusted accessor leaves the
# function's hints to the catch-all.
ACCESSOR_CASES = {
    "a property's own accessors": (
        "class C:\n"
        "    @property\n"
        "    def p(self) -> ProjectionRNGRegistry:\n"
        "        return ProjectionRNGRegistry(0, 1)\n"
        "    @p.setter\n"
        "    def p(self, value: ProjectionRNGRegistry) -> None:\n"
        "        pass\n"
        "    @p.deleter\n"
        "    def p(self) -> None:\n"
        "        pass\n"
        "    @p.getter\n"
        "    def p(self) -> ProjectionRNGRegistry:\n"
        "        return ProjectionRNGRegistry(0, 1)\n",
        [],
    ),
    "an accessor of a receiver bound nowhere": (
        "class C:\n"
        "    @unrelated.setter\n"
        "    def p(self, value: ProjectionRNGRegistry) -> None:\n"
        "        pass\n",
        [4],
    ),
    "an accessor of a plain method": (
        "class C:\n"
        "    def p(self):\n"
        "        return 0\n"
        "    @p.setter\n"
        "    def p(self, value: ProjectionRNGRegistry) -> None:\n"
        "        pass\n",
        [6],
    ),
    "an accessor of a property rebound": (
        "class C:\n"
        "    @property\n"
        "    def p(self):\n"
        "        return 0\n"
        "    p = staticmethod(len)\n"
        "    @p.setter\n"
        "    def p(self, value: ProjectionRNGRegistry) -> None:\n"
        "        pass\n",
        [8],
    ),
    "an accessor of a property under another decorator": (
        "class C:\n"
        "    @wrap\n"
        "    @property\n"
        "    def p(self):\n"
        "        return 0\n"
        "    @p.setter\n"
        "    def p(self, value: ProjectionRNGRegistry) -> None:\n"
        "        pass\n",
        [8],
    ),
    "an accessor outside a class": (
        "@property\n"
        "def p(self):\n"
        "    return 0\n"
        "@p.setter\n"
        "def q(self, value: ProjectionRNGRegistry) -> None:\n"
        "    pass\n",
        [6],
    ),
    "an accessor of a local property": (
        "def property(function):\n"
        "    return function\n"
        "class C:\n"
        "    @property\n"
        "    def p(self):\n"
        "        return 0\n"
        "    @p.setter\n"
        "    def p(self, value: ProjectionRNGRegistry) -> None:\n"
        "        pass\n",
        [9],
    ),
}


@pytest.mark.parametrize("case", tuple(ACCESSOR_CASES))
def test_scan_trusts_an_accessor_only_of_a_property_above_it(case):
    body, lines = ACCESSOR_CASES[case]
    hits = scan_sources([_invented(_REGISTRY_IMPORT + body)])
    assert [(hit.line, hit.kind) for hit in hits] == [
        (line, "class-reference") for line in lines
    ], describe(hits)


def _nested_code(depth):
    """Invent a module whose check sits in ``depth`` nested literal execs."""
    code = "def f(x):\n    return isinstance(x, R)"
    for _ in range(depth):
        code = f"exec({code!r})"
    return f"{_IMPORT} as R\n{code}\n"


def _answers(text):
    """Run an invented module's ``f`` on the registry and the direct class."""
    namespace = {"__name__": "invented_case"}
    exec(
        compile(text, "invented_case.py", "exec", dont_inherit=True), namespace
    )
    return [
        bool(namespace["f"](cls(0, 2)))
        for cls in (ProjectionRNGRegistry, DirectRNGStreams)
    ]


@pytest.mark.parametrize("depth", range(1, 8))
def test_scan_parses_five_levels_of_literal_code_and_flags_deeper(depth):
    """Code nested past five levels is reported as dynamic code.

    At every depth the module is a working check, so the scan must report
    it either way: as the check while it parses the code, and as dynamic
    code where it stops.
    """
    text = _nested_code(depth)
    assert _answers(text) == [True, False]
    hits = scan_sources([_invented(text)])
    kind = "isinstance" if depth <= 5 else "dynamic-code"
    assert [(hit.line, hit.kind) for hit in hits] == [(2, kind)], describe(
        hits
    )


_CHAIN = 3000
_RUN_ANY = "isinstance(x, ProjectionRNGRegistry) if x else x"
# Checks inside, or next to, chains 3000 links long. The recursive walks
# r3 found stopped at about 500 links; the scan walks these with its own
# stacks. Markers are those of SPELLINGS.
LONG_CHAINS = {
    "a sum of literals": (
        f"{_IMPORT}\nNAME = 'ProjectionRNG' + 'Registry'"
        + " + ''" * _CHAIN
        + "  # label\ndef f(x):\n    return type(x).__name__ == NAME  # check\n",
        "name-compare",
    ),
    "a union": (
        f"{_IMPORT}\nKINDS = int"
        + " | int" * _CHAIN
        + " | ProjectionRNGRegistry  # alias\n"
        "def f(x):\n    return isinstance(x, KINDS)  # check\n",
        "isinstance",
    ),
    "a chain of slices": (
        f"{_IMPORT}\nKINDS = (ProjectionRNGRegistry,)  # alias\n"
        "def f(x):\n    return isinstance(x, KINDS"
        + "[:]" * _CHAIN
        + ")  # check\n",
        "isinstance",
    ),
    "a chain of conditionals": (
        f"{_IMPORT}\ndef f(x):\n    return isinstance(x, "
        + "ProjectionRNGRegistry if x else " * _CHAIN
        + "ProjectionRNGRegistry)  # check\n",
        "isinstance",
    ),
    "a chain of attributes": (
        f"{_IMPORT}\ndef f(x):\n    return {_RUN_ANY}"
        + ".real" * _CHAIN
        + "  # check\n",
        "isinstance",
    ),
    "a chain of calls": (
        f"{_IMPORT}\ndef f(x):\n    return {_RUN_ANY[:-1]}(lambda: x)"
        + "()" * _CHAIN
        + "  # check\n",
        "isinstance",
    ),
    "a chain of negations": (
        f"{_IMPORT}\ndef f(x):\n    return "
        + "not " * _CHAIN
        + "isinstance(x, ProjectionRNGRegistry)  # check\n",
        "isinstance",
    ),
}


@pytest.mark.parametrize("shape", tuple(LONG_CHAINS))
def test_scan_reads_long_chains_without_exhausting_recursion(shape):
    """Each chain is a working check, and the scan finds it."""
    text, kind = LONG_CHAINS[shape]
    assert _answers(text) == [True, False]
    hits = scan_sources([_invented(text)])
    assert [(hit.line, hit.kind) for hit in hits] == _expected(
        text, kind
    ), describe(hits)


# Inert-literal pruning must not change any result. The leaves include the
# class's name, its module's name and a probe name, so some generated
# literals are inert and some are not.
_LITERAL_LEAVES = st.one_of(
    st.integers(-3, 3),
    st.none(),
    st.binary(max_size=2),
    st.sampled_from(
        [
            "a",
            "RNG",
            "Projection",
            "RNGRegistry",
            REGISTRY_NAME,
            REGISTRY_NAME.lower(),
            REGISTRY_MODULE,
            DIRECT_NAME,
            OWN_MODULE,
            "_period_sequence",
            "__all__",
            "__doc__",
            "__annotations__",
            REGISTRY_NAME.encode(),
            DIRECT_NAME.encode(),
            REGISTRY_MODULE.encode(),
            b"_period_sequence",
        ]
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
    + "    a = type(x).__name__ in {0} or isinstance(x, {0}) or g({0})\n"
    + "    b = ''.join({0}) == type(x).__name__ or ({0},)[0] == x\n"
    + "    c = '%s' % ({0},) == '{{}}'.format({0}) == str({0}).lower()\n"
    + "    return a or b or c or g(key={0})\n"
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


def test_every_kind_has_a_spelling():
    """Each kind of hit is pinned by at least one invented spelling."""
    kinds = {kind for _, kind in SPELLINGS.values()} | set(MARKERS.values())
    assert not SPECIFIC_KINDS & CATCH_ALL_KINDS
    assert kinds == SPECIFIC_KINDS | CATCH_ALL_KINDS


_HIT = re.compile(r"invented/[a-z_]+\.py:[1-9][0-9]*: [a-z_-]+")


def test_every_hit_names_only_a_path_a_line_and_a_kind():
    for text, _ in SPELLINGS.values():
        for hit in scan_sources([_invented(text)]):
            assert hit.kind in SPECIFIC_KINDS | CATCH_ALL_KINDS
            assert _HIT.fullmatch(str(hit)), hit


# Modules that track nothing: their reads of namespaces, docstrings,
# annotations and source cannot reach either class.
UNTRACKED_READS = (
    '"""A module that tracks nothing."""\n'
    "__all__ = ['f']\n"
    "def f():\n"
    "    'Return the namespace.'\n"
    "    return globals(), locals(), vars(), dir(), __doc__, f.__doc__\n",
    "import inspect\n"
    "def f(x: int) -> int:\n"
    "    return inspect.signature(f), f.__annotations__, inspect.getdoc(f)\n",
)


@pytest.mark.parametrize("text", UNTRACKED_READS)
def test_reads_count_only_where_something_is_tracked(text):
    hits = scan_sources([_invented(text)])
    assert hits == (), describe(hits)


# Each expression would build text, a tuple or an integer past the
# folder's limits, so the folder must refuse it before building it. Long
# text is built from integers within the integer limit, so that each case
# reaches the check it is listed under.
FOLD_LIMIT_CASES = (
    # Integers.
    "'ab' * 10 ** 12",
    "'x'.center(10 ** 9)",
    "'x'.center(99999)",
    "4096 * 4096",
    # Repetition, concatenation, replacement and joining.
    "'ab' * 4096 * 4096",
    "('ab',) * 4096",
    "'abc'.replace('', 'x' * 4096) * 4096",
    "('x' * 4096).replace('', 'y' * 1024)",
    "'x' * 4096 + 'y' * 4096 * 16",
    "('x' * 4096 * 15).join(('a',) * 200)",
    # Widths, and text formatted field by field.
    "'{:9999999}'.format(1)",
    "'%9999999s' % 'x'",
    "f'{1:9999999}'",
    "'{:{}}'.format('x', '9' * 7)",
    "('{0}' * 64).format('x' * 4096 * 15)",
    "f\"{'x' * 4096 * 10}{'y' * 4096 * 10}\"",
    # Tuples, and text built from their items.
    "('x' * 4096 * 10, 'y' * 4096 * 10)",
    "str(('x' * 4096 * 15, 'y' * 4096 * 15))",
    "('x' * 4096 * 4).join(('a' * 4096 * 4, 'b' * 4096 * 4, 'c'))",
)


@pytest.mark.parametrize("expression", FOLD_LIMIT_CASES)
def test_folder_refuses_results_past_its_limits(expression):
    """The folder gives no value, and never holds much memory on the way.

    Built and then refused, the width cases would take about 10 MB, the
    join 12 MB, and the replacement and the repeated field about 4 MB
    each; the bound is 1 MB.
    """
    node = ast.parse(expression, mode="eval").body
    tracing = tracemalloc.is_tracing()
    if not tracing:
        tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        start = tracemalloc.get_traced_memory()[0]
        folded = _fold(node, _FoldMemo())
        peak = tracemalloc.get_traced_memory()[1] - start
    finally:
        if not tracing:
            tracemalloc.stop()
    assert folded is _UNKNOWN
    assert peak < 16 * _FOLD_TEXT_LIMIT


# The folder's operations, over small literals. Python evaluates each
# expression too; where it succeeds within the limits the folder must give
# the same value, and where it fails the folder must give none.
_FOLD_BUILTINS = {
    name: getattr(builtins, name)
    for name in ("str", "repr", "ascii", "tuple", "reversed", "sorted")
}
_FOLD_LEAVES = st.one_of(
    st.text("aZß-{}%s", max_size=3).map(repr),
    st.binary(max_size=3).map(repr),
    st.integers(-3, 12).map(str),
)
_FOLD_METHOD_NAMES = (
    "lower",
    "upper",
    "casefold",
    "capitalize",
    "strip",
    "lstrip",
    "rstrip",
    "title",
    "swapcase",
    "split",
    "rsplit",
    "splitlines",
    "encode",
    "decode",
)
# Methods taking one argument: another expression, or a width.
_FOLD_ARGUMENT_METHODS = (
    "partition",
    "rpartition",
    "removeprefix",
    "removesuffix",
    "split",
    "rsplit",
    "strip",
    "lstrip",
    "rstrip",
)
_FOLD_WIDTH_METHODS = ("center", "ljust", "rjust", "zfill")


def _fold_operations(inner):
    pairs = st.tuples(inner, inner)
    return st.one_of(
        pairs.map(lambda p: f"({p[0]} + {p[1]})"),
        st.tuples(inner, st.integers(-1, 4)).map(
            lambda p: f"({p[0]} * {p[1]})"
        ),
        pairs.map(lambda p: f"({p[0]} % ({p[1]},))"),
        st.tuples(inner, st.integers(-3, 3)).map(
            lambda p: f"({p[0]})[{p[1]}]"
        ),
        st.tuples(inner, st.integers(-3, 3), st.integers(-3, 3)).map(
            lambda p: f"({p[0]})[{p[1]}:{p[2]}]"
        ),
        st.tuples(inner, st.sampled_from(_FOLD_METHOD_NAMES)).map(
            lambda p: f"({p[0]}).{p[1]}()"
        ),
        st.tuples(inner, st.sampled_from(_FOLD_ARGUMENT_METHODS), inner).map(
            lambda p: f"({p[0]}).{p[1]}({p[2]})"
        ),
        st.tuples(
            inner, st.sampled_from(_FOLD_WIDTH_METHODS), st.integers(-2, 8)
        ).map(lambda p: f"({p[0]}).{p[1]}({p[2]})"),
        st.tuples(inner, inner, inner).map(
            lambda p: f"({p[0]}).replace({p[1]}, {p[2]})"
        ),
        st.tuples(inner, inner, inner).map(
            lambda p: f"({p[0]}).join(({p[1]}, {p[2]}))"
        ),
        pairs.map(lambda p: f"'{{}}-{{!r}}'.format({p[0]}, {p[1]})"),
        pairs.map(lambda p: f"'{{0}}{{1!a:>3}}{{0}}'.format({p[0]}, {p[1]})"),
        pairs.map(lambda p: f"'{{:{{}}}}'.format({p[0]}, {p[1]})"),
        pairs.map(lambda p: f"f'{{{p[0]}}}{{{p[1]}!a:>3}}'"),
        pairs.map(lambda p: f"({p[0]}, {p[1]})"),
        pairs.map(lambda p: f"[{p[0]}, *{p[1]}]"),
        inner.map(lambda e: f"tuple(reversed({e}))"),
        inner.map(lambda e: f"''.join(reversed({e}))"),
        inner.map(lambda e: f"sorted({e})"),
        inner.map(lambda e: f"str({e})"),
        inner.map(lambda e: f"repr({e})"),
    )


_FOLD_EXPRESSIONS = st.recursive(_FOLD_LEAVES, _fold_operations, max_leaves=6)


@settings(max_examples=300, deadline=None)
@given(expression=_FOLD_EXPRESSIONS)
def test_folder_agrees_with_python_on_literal_expressions(expression):
    folded = _fold(ast.parse(expression, mode="eval").body, _FoldMemo())
    with warnings.catch_warnings():
        # Python warns of subscripting an integer literal; it then fails.
        warnings.simplefilter("ignore", SyntaxWarning)
        code = compile(expression, "<fold>", "eval", dont_inherit=True)
    try:
        expected = eval(code, {"__builtins__": _FOLD_BUILTINS})
    except Exception:
        assert folded is _UNKNOWN
        return
    if _sized(expected) is _UNKNOWN:
        assert folded is _UNKNOWN
        return
    if folded is _UNKNOWN:
        # The folder refuses by design any template whose width or
        # precision has four digits, which Python may still format within
        # the limits; without that rule, the folder must agree.
        with pytest.MonkeyPatch.context() as patch:
            for kind in _WIDE_FIELDS:
                patch.setitem(_WIDE_FIELDS, kind, re.compile(r"(?!)"))
            folded = _fold(
                ast.parse(expression, mode="eval").body, _FoldMemo()
            )
    assert type(folded) is type(expected)
    assert folded == expected


# Each limit at its edge: the first expression of a pair is within it and
# folds to Python's value; the second is one step past it and gives none.
FOLD_EDGE_CASES = (
    ("'x' * 4096 * 16", "'x' * 4096 * 16 + 'y'"),
    ("tuple('ab' * 128)", "tuple('ab' * 128 + 'c')"),
    ("4096", "4097"),
    ("-4096", "-4097"),
    ("2048 * 2", "2049 * 2"),
    ("('{}' + 'x' * 4094).format(1)", "('{}' + 'x' * 4095).format(1)"),
    ("'{:999}'.format(1)", "'{:1000}'.format(1)"),
    ("'%999s' % 'x'", "'%1000s' % 'x'"),
    ("f'{1:999}'", "f'{1:1000}'"),
)


@pytest.mark.parametrize(("within", "past"), FOLD_EDGE_CASES)
def test_folder_limits_hold_at_their_edges(within, past):
    folded = _fold(ast.parse(within, mode="eval").body, _FoldMemo())
    expected = eval(compile(within, "<edge>", "eval", dont_inherit=True), {})
    assert type(folded) is type(expected)
    assert folded == expected
    assert _fold(ast.parse(past, mode="eval").body, _FoldMemo()) is _UNKNOWN


def test_folder_keeps_a_source_literal_of_any_length():
    """A literal past the text limit is the parser's own text, kept as is.

    The limits bound what the folder builds, not what the source holds,
    so the scan still reads code in a long literal.
    """
    code = "def f(x):\n    return isinstance(x, R)\n#" + "x" * 70000
    node = ast.parse(repr(code), mode="eval").body
    assert _fold(node, _FoldMemo()) is node.value
    hits = scan_sources([_invented(f"{_IMPORT} as R\nexec({code!r})\n")])
    assert [(hit.line, hit.kind) for hit in hits] == [
        (2, "isinstance")
    ], describe(hits)


def test_folder_budget_bounds_what_one_expression_keeps():
    """Values each within the limits stop at the budget, loudly.

    r3's tuple of 512 texts of 60 KiB each kept about 34 MB before the
    item limit refused it; now the fold stops near 1 MiB.
    """
    node = ast.parse("(" + "'x' * 4096 * 15, " * 512 + ")", mode="eval").body
    tracing = tracemalloc.is_tracing()
    if not tracing:
        tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        start = tracemalloc.get_traced_memory()[0]
        with pytest.raises(ScanError) as raised:
            _fold(node, _FoldMemo())
        peak = tracemalloc.get_traced_memory()[1] - start
    finally:
        if not tracing:
            tracemalloc.stop()
    assert str(raised.value) == (
        "<expression>: literal expressions past the folder's budget"
    )
    assert peak < _FOLD_BUDGET + 16 * _FOLD_TEXT_LIMIT


# Each built text is 64 KiB, so 16 fill the budget; a literal costs none.
_BUDGET_TEXTS = {"built": "'x' * 4096 * 16", "literal": repr("x" * 65536)}


@pytest.mark.parametrize(
    ("form", "count", "fits"),
    (("built", 12, True), ("built", 20, False), ("literal", 20, True)),
)
def test_scan_stops_at_the_folder_budget_naming_only_the_path(
    form, count, fits
):
    """A module's values share one budget; past it the scan stops.

    The error names the module's path and nothing of its text.
    """
    text = f"{_IMPORT}\n" + "".join(
        f"TEXT_{index} = {_BUDGET_TEXTS[form]}\n" for index in range(count)
    )
    if fits:
        assert scan_sources([_invented(text)]) == ()
        return
    with pytest.raises(ScanError) as raised:
        scan_sources([_invented(text)])
    assert str(raised.value) == (
        "invented/invented_case.py: literal expressions past the folder's "
        "budget"
    )


# One call to each method and builtin the folder runs; a name dropped from
# its lists stops folding here.
FOLD_CALLS = (
    ("capitalize", "'ab'.capitalize()"),
    ("casefold", "'Aß'.casefold()"),
    ("center", "'ab'.center(6, '*')"),
    ("decode", "b'ab'.decode()"),
    ("encode", "'ab'.encode()"),
    ("format", "'{}-{!r}'.format(1, 'a')"),
    ("format", "format(5, '03')"),
    ("fromhex", "bytes.fromhex('6162')"),
    ("join", "'-'.join(('a', 'b'))"),
    ("ljust", "'ab'.ljust(4)"),
    ("lower", "'AB'.lower()"),
    ("lstrip", "'  ab'.lstrip()"),
    ("partition", "'a-b-c'.partition('-')"),
    ("removeprefix", "'abc'.removeprefix('a')"),
    ("removesuffix", "'abc'.removesuffix('c')"),
    ("replace", "'abc'.replace('b', 'x')"),
    ("rjust", "'ab'.rjust(4)"),
    ("rpartition", "'a-b-c'.rpartition('-')"),
    ("rsplit", "'a b c'.rsplit(' ', 1)"),
    ("rstrip", "'ab  '.rstrip()"),
    ("split", "'a b'.split()"),
    ("splitlines", "'a\\nb'.splitlines()"),
    ("strip", "' ab '.strip()"),
    ("swapcase", "'aB'.swapcase()"),
    ("title", "'ab cd'.title()"),
    ("upper", "'ab'.upper()"),
    ("zfill", "'7'.zfill(3)"),
    ("ascii", "ascii('ß')"),
    ("bytes", "bytes('ab', 'ascii')"),
    ("chr", "chr(97)"),
    ("list", "list('ab')"),
    ("repr", "repr('a')"),
    ("reversed", "tuple(reversed('ab'))"),
    ("sorted", "sorted('ba')"),
    ("str", "str(12)"),
    ("tuple", "tuple('ab')"),
)


def test_every_listed_method_and_builtin_has_a_call():
    assert {name for name, _ in FOLD_CALLS} == _FOLD_METHODS | _FOLD_FUNCTIONS


@pytest.mark.parametrize(("name", "expression"), FOLD_CALLS)
def test_folder_runs_each_listed_method_and_builtin(name, expression):
    folded = _fold(ast.parse(expression, mode="eval").body, _FoldMemo())
    code = compile(expression, "<call>", "eval", dont_inherit=True)
    expected = eval(code, {})
    assert type(folded) is type(expected)
    assert folded == expected


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


# ---------------------------------------------------------------------------
# Condition 4, by reader: each sealed reader of a context's streams gives the
# same output whichever class serves it.
# ---------------------------------------------------------------------------

# The names through which sealed code reaches a context's streams. The census
# finds each use of one as an attribute, a name, a keyword or a string. A
# function handed the registry under another name is found through the call
# that hands it over, which is why the composition helper is listed. Like the
# scan, the census only says where to look; the runs below are the check.
STREAM_NAMES = frozenset(
    {"rng_registry", "person_generator", "composition_rngs_from_registry"}
)
_RUN = "run below with both classes"
_OWN = "builds its own registry and reads only that one"
_CERTIFIED = (
    "needs certified fitted inputs; reads only generator, child_generator, "
    "n_periods and composition_rngs_from_registry, each checked at every "
    "address by test_streams.py and the composition run below"
)
# Every reader the census finds, by path under the package and qualified
# name, with the run that checks it or the reason none does. A new reader, a
# moved one or a removed one fails the census and comes back for a decision.
STREAM_READERS = {
    ("assembled_history_observer.py", "FertilityCapture._call"): _RUN,
    ("baselines/fertility.py", "draw_asfr_births"): _RUN,
    ("cola_track_a/adapters.py", "di_aware_claiming"): _RUN,
    ("engine/__init__.py", "<module>"): "names the helper in __all__",
    (
        "engine/assembly.py",
        "assemble_period_modules.disability_step",
    ): _CERTIFIED,
    (
        "engine/assembly.py",
        "assemble_period_modules.household_step",
    ): _CERTIFIED,
    ("engine/assembly.py", "assemble_period_modules.marital_step"): _CERTIFIED,
    ("engine/claiming.py", "apply_claiming"): _RUN,
    (
        "engine/composition.py",
        "simulate_candidate9_internal_reference",
    ): _OWN,
    ("engine/di_entitlement.py", "_person_uniforms"): _RUN,
    ("engine/forward_earnings_p2_v1.py", "resume_p2_projection"): _OWN,
    ("engine/loop.py", "PeriodContext"): "declares the field",
    ("engine/loop.py", "PeriodContext.person_generator"): _RUN,
    ("engine/loop.py", "ProjectionEngine.project"): _OWN,
    ("engine/steps.py", "apply_claiming"): _RUN,
    ("engine/steps.py", "apply_earnings"): _RUN,
    ("engine/steps.py", "apply_mortality"): _RUN,
    (
        "graph/runtime.py",
        "_GraphPeriodContext.__init__",
    ): "binds its own adapter, never either class",
    ("harness/m6_preflight.py", "run_candidate9_recertification"): _OWN,
    (
        "harness/m6_projection.py",
        "project_earnings_on_realized_support",
    ): _OWN,
    ("mortality_observer.py", "observe_mortality"): (
        "the pinned check, which refuses the direct class loudly"
    ),
    ("mortality_ses/step.py", "apply_differential_mortality"): _RUN,
    ("track_b/replay.py", "replay_earnings_on_realized_support"): _OWN,
}


def _stream_name_use(node):
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.keyword):
        return node.arg
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def stream_reader_census(sources):
    """Each function, class or module that uses a stream name, by path
    under the package and qualified name. Names only, never source text."""
    places = set()
    for source in sources:
        path = source.path.removeprefix("src/populace_dynamics/")
        stack = [(ast.parse(source.text), "")]
        while stack:
            node, qualified = stack.pop()
            for child in ast.iter_child_nodes(node):
                name = qualified
                if isinstance(
                    child,
                    ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
                ):
                    name = (
                        f"{qualified}.{child.name}"
                        if qualified
                        else child.name
                    )
                stack.append((child, name))
                if _stream_name_use(child) in STREAM_NAMES:
                    places.add((path, qualified or "<module>"))
    return places


def test_every_stream_reader_is_run_or_named():
    """The census finds exactly the pinned readers, and each one marked to
    run has a run below."""
    found = stream_reader_census(repository_sources())
    pinned = set(STREAM_READERS)
    assert found == pinned, sorted(found ^ pinned)
    assert set(READER_RUNS) == {
        place for place, reason in STREAM_READERS.items() if reason == _RUN
    }


_READER_PERIODS = 3
_READER_MORTALITY = AgeSexMortalityModel(
    ((0, 64), (65, 120)),
    {
        ("0-64", "female"): 0.3,
        ("0-64", "male"): 0.3,
        ("65+", "female"): 0.6,
        ("65+", "male"): 0.6,
    },
)
_READER_SCHEDULE = ClaimingSchedule(
    {
        ("female", START + 1): {62: 0.2, 65: 0.3, 70: 0.5},
        ("male", START + 1): {62: 0.4, 67: 0.6},
    }
)
_READER_RATES = {age: 0.5 for age in range(15, 50)}


def _reader_roster(size, shift):
    """Invented people, in descending ID order: women of child-bearing age,
    people past fifty, DI entitlement and conversions."""
    index = np.arange(size)
    age = 16 + (index * 13 + shift) % 70
    return pd.DataFrame(
        {
            "person_id": (100 + 3 * (size - index)).astype("int64"),
            "age": age.astype("int64"),
            "sex": np.where(index % 2, "male", "female"),
            "weight": 0.5 + index / 4,
            "di_entitled": index % 4 == 3,
            "di_converted": index % 5 == 4,
        }
    )


class _InventedEarnings:
    def generate(self, frame, year, rng):
        return rng.gamma(2.0, 1000.0, len(frame))


class _InventedRefreshEarnings:
    earnings_frame_update_columns = ("refresh",)

    def generate_with_frame_updates(self, frame, year, rng):
        earnings = rng.gamma(2.0, 1000.0, len(frame))
        refresh = (rng.random(len(frame)) < 0.5).astype(np.float64)
        return earnings, {"refresh": refresh}


class _InventedDomainEarnings(_InventedEarnings):
    def validate_domain(self, frame):
        return frame["age"].to_numpy() < 70


class _InventedDifferentialMortality:
    weight_column = "weight"

    def evaluate(self, frame, context):
        probability = np.where(frame["age"].to_numpy() >= 65, 0.6, 0.3)
        cells = pd.DataFrame(
            {"person_id": frame["person_id"].to_numpy(), "q": probability}
        )
        return probability, cells


def _invented_fertility(frame, context, marital, rng):
    draws = [
        context.person_generator(ProjectionModule.FERTILITY, person).random()
        for person in frame["person_id"]
    ]
    return frame.assign(fertility_draw=np.asarray(draws, dtype=np.float64))


def _read_person_generator(context, frame, rng):
    return [
        np.asarray(
            [
                context.person_generator(module, person).random(2)
                for module in ProjectionModule
                for person in frame["person_id"]
            ]
        )
    ]


def _read_mortality(context, frame, rng):
    return [apply_mortality(frame, context, rng, model=_READER_MORTALITY)]


def _read_differential_mortality(context, frame, rng):
    deaths, cells = {}, {}
    survivors = apply_differential_mortality(
        frame,
        context,
        rng,
        model=_InventedDifferentialMortality(),
        weight_column="weight",
        death_log=deaths,
        cell_log=cells,
    )
    return [survivors, *deaths.values(), *cells.values()]


def _read_earnings(context, frame, rng):
    domain = frame.assign(**{EARNINGS_DOMAIN_COLUMN: True})
    return [
        apply_earnings(frame, context, rng, model=_InventedEarnings()),
        apply_earnings(frame, context, rng, model=_InventedRefreshEarnings()),
        apply_earnings(domain, context, rng, model=_InventedDomainEarnings()),
    ]


def _claiming_reader(apply):
    def read(context, frame, rng):
        return [apply(frame, context, rng, schedule=_READER_SCHEDULE)]

    return read


def _read_person_uniforms(context, frame, rng):
    person_ids = np.sort(frame["person_id"].to_numpy())
    needed = np.arange(len(person_ids)) % 3 != 1
    return [
        _person_uniforms(person_ids, needed, context, rng, module, tag)
        for module in (ProjectionModule.DISABILITY, ProjectionModule.CLAIMING)
        for tag in (None, 0xD1)
    ]


def _read_composition(context, frame, rng):
    out = []
    for period in (0, context.period_index):
        streams = composition_rngs_from_registry(context.rng_registry, period)
        out.append(
            np.asarray(
                [
                    getattr(streams, field.name).random(3)
                    for field in dataclasses.fields(streams)
                ]
            )
        )
    return out


def _read_asfr_births(context, frame, rng):
    return [draw_asfr_births(frame, context, _READER_RATES)]


def _read_fertility_capture(context, frame, rng):
    """The capture checks period order and its calendar, so it runs every
    period of the registry from the first, as a projection does."""
    wrapped, capture = capture_fertility(
        replace(_modules(), fertility=_invented_fertility)
    )
    for period in range(1, context.rng_registry.n_periods + 1):
        step = replace(context, period_index=period, year=2014 + period)
        wrapped.fertility(frame, step, None, rng)
    return [capture.to_json()]


READER_RUNS = {
    ("assembled_history_observer.py", "FertilityCapture._call"): (
        _read_fertility_capture
    ),
    ("baselines/fertility.py", "draw_asfr_births"): _read_asfr_births,
    ("cola_track_a/adapters.py", "di_aware_claiming"): _claiming_reader(
        di_aware_claiming
    ),
    ("engine/claiming.py", "apply_claiming"): _claiming_reader(
        engine_claiming.apply_claiming
    ),
    ("engine/di_entitlement.py", "_person_uniforms"): _read_person_uniforms,
    ("engine/loop.py", "PeriodContext.person_generator"): (
        _read_person_generator
    ),
    ("engine/steps.py", "apply_claiming"): _claiming_reader(apply_claiming),
    ("engine/steps.py", "apply_earnings"): _read_earnings,
    ("engine/steps.py", "apply_mortality"): _read_mortality,
    ("mortality_ses/step.py", "apply_differential_mortality"): (
        _read_differential_mortality
    ),
}
# The composition helper has no reader place of its own; its callers are
# listed above, and it runs here so that their streams are checked too.
_COMPOSITION = ("engine/composition.py", "composition_rngs_from_registry")


def _run_reader(place, streams_class, size, shift, draw, period, seed):
    frame = _reader_roster(size, shift)
    ordinals = {
        person: ordinal
        for ordinal, person in enumerate(sorted(frame["person_id"]))
    }
    context = PeriodContext(
        period,
        START + period,
        draw,
        {},
        rng_registry=streams_class(draw, _READER_PERIODS),
        person_ordinals=ordinals,
    )
    reader = _read_composition if place == _COMPOSITION else READER_RUNS[place]
    return reader(context, frame, np.random.default_rng(seed))


def _assert_same_outputs(actual, expected):
    for got, want in zip(actual, expected, strict=True):
        if isinstance(want, pd.DataFrame):
            pd.testing.assert_frame_equal(got, want, check_exact=True)
        elif isinstance(want, np.ndarray):
            np.testing.assert_array_equal(got, want, strict=True)
        else:
            assert got == want


def _outputs_differ(first, second):
    try:
        _assert_same_outputs(first, second)
    except AssertionError:
        return True
    return False


_READER_PLACES = (*sorted(READER_RUNS), _COMPOSITION)


@pytest.mark.parametrize("place", _READER_PLACES)
@settings(max_examples=12, deadline=None)
@given(
    size=st.integers(0, 12),
    shift=st.integers(0, 69),
    draw=st.integers(0, 2**20),
    period=st.integers(1, _READER_PERIODS),
    seed=st.integers(0, 2**32 - 1),
)
def test_each_stream_reader_gives_the_same_output_from_either_class(
    place, size, shift, draw, period, seed
):
    """The invariant: each sealed reader the census marks to run gives
    exactly the same output from either class, for any invented roster,
    draw, period and injected generator seed."""
    registry = _run_reader(
        place, ProjectionRNGRegistry, size, shift, draw, period, seed
    )
    direct = _run_reader(
        place, DirectRNGStreams, size, shift, draw, period, seed
    )
    _assert_same_outputs(direct, registry)


@pytest.mark.parametrize("place", _READER_PLACES)
def test_each_stream_reader_draws_from_the_streams(place):
    """Two draw indices give different output for each reader, so each run
    above reads the streams rather than passing them by."""
    first, second = (
        _run_reader(place, DirectRNGStreams, 24, 0, draw, 1, 0)
        for draw in (0, 1)
    )
    assert _outputs_differ(first, second)
