#!/usr/bin/env python3
"""Track B B0.1 addendum: build and audit the Q6 blinded-review root.

Max's ruling d693 set the form of the addendum's blinded review (Q6): an
independent read-only lane on a cleaned root. This script has two commands.

``build`` extracts ``git archive`` of one commit into a new directory that
is not a git repository, and removes, whole:

- every file on the audit's Q6 exclusion list and every further file the
  exposure inventory flags when rerun at that commit;
- ``data/external/psid_codebook_field_evidence/``, whose code maps carry
  frequency columns for B2's 2012 and 2014 labor-income variables;
- any other file that holds both a code map and frequencies, unless it
  is named with ``--allow``. An allowed file must be one this pull
  request adds or changes (``git diff --name-only BASE HEAD``), and the
  record lists it. The token test cannot tell a codebook table from code
  or records that name the tokens, such as this script.

It then copies in the named context files, refuses the root if a denied
path or a code map with frequencies remains, and writes a manifest of
every file with its SHA-256.

``readlog`` reads a review lane's stream-json transcript and lists every
path its tool calls named and every path its Glob and Grep results
returned. A review counts only if all of them lie inside the root. With
``--format codex`` it reads a Codex lane's ``exec --json`` events instead,
whose tools are shell commands run from the root, and flags every command
word that leaves the root: an absolute path outside it, a home path or a
``..`` segment.

Neither command prints file content. Listed files are removed by path,
unread. The codebook check reads each remaining file only to test for the
two tokens.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import re
import shutil
import string
import subprocess
import sys
import tarfile
from collections.abc import Iterable, Mapping, Sequence
from fnmatch import fnmatchcase
from itertools import pairwise
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "track_b_b0_1_review_root.v1"
CODEBOOK_DIR = "data/external/psid_codebook_field_evidence"
CONTEXT_DIR = "_review_context"
#: A file holding both of these is a codebook table and is removed.
CODE_MAP_RX = re.compile(r"code_map", re.IGNORECASE)
FREQUENCY_RX = re.compile(r"frequenc", re.IGNORECASE)
#: Tool-call fields of the read-only lane that name a path or a pattern.
PATH_FIELDS = ("file_path", "path", "pattern", "glob")
ABSOLUTE_RX = re.compile(r"(/(?:Users|private|tmp|var|opt|etc)/[^\s\"'<>:]+)")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def denied_paths(inventories: Iterable[Mapping[str, Any]]) -> list[str]:
    """Every inventoried exclusion, whole, whatever its listed scope."""
    paths: set[str] = set()
    for inventory in inventories:
        for entry in inventory["q6_exclusions"]:
            paths.add(str(entry["path"]))
    return sorted(paths)


def remove_denied(root: Path, denied: Sequence[str]) -> list[str]:
    """Delete the denied files and the codebook directory from ``root``."""
    removed: list[str] = []
    for relative in denied:
        target = root / relative
        if target.is_file():
            target.unlink()
            removed.append(relative)
    codebook = root / CODEBOOK_DIR
    if codebook.is_dir():
        for path in sorted(codebook.rglob("*")):
            if path.is_file():
                removed.append(path.relative_to(root).as_posix())
        shutil.rmtree(codebook)
    return sorted(removed)


def codebook_tables(root: Path, allowed: Sequence[str] = ()) -> list[str]:
    """Files under ``root`` that hold a code map and frequencies."""
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or CONTEXT_DIR in path.parts:
            continue
        if path.relative_to(root).as_posix() in allowed:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if CODE_MAP_RX.search(text) and FREQUENCY_RX.search(text):
            hits.append(path.relative_to(root).as_posix())
    return hits


def manifest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def changed_files(base: str, head: str) -> set[str]:
    """Files the pull request adds or changes between ``base`` and ``head``."""
    listed = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {line for line in listed.splitlines() if line}


def build(
    head: str,
    out: Path,
    inventories: Sequence[Path],
    context: Mapping[str, Path],
    allowed: Sequence[str] = (),
    base: str | None = None,
) -> dict[str, Any]:
    if allowed:
        if base is None:
            raise ValueError("--allow needs --base")
        outside = sorted(set(allowed) - changed_files(base, head))
        if outside:
            raise ValueError(f"not changed by this pull request: {outside}")
    out = out.resolve()
    if out.exists():
        raise FileExistsError(f"{out} exists")
    if out.is_relative_to(ROOT):
        raise RuntimeError("the review root must be outside the repository")
    out.mkdir(parents=True)
    archive = out.parent / f"{out.name}.tar"
    subprocess.run(
        ["git", "archive", "--format=tar", "-o", str(archive), head],
        cwd=ROOT,
        check=True,
    )
    with tarfile.open(archive) as tar:
        tar.extractall(out, filter="data")
    archive.unlink()
    denied = denied_paths(
        json.loads(path.read_text(encoding="utf-8")) for path in inventories
    )
    removed = remove_denied(out, denied)
    denied_set = set(denied)
    if denied_set & set(allowed):
        raise ValueError("an allowed file is on an exclusion list")
    tables = codebook_tables(out, allowed)
    for relative in tables:
        (out / relative).unlink()
    context_dir = out / CONTEXT_DIR
    context_dir.mkdir()
    copies: dict[str, dict[str, str]] = {}
    for name, source in sorted(context.items()):
        target = context_dir / name
        shutil.copyfile(source, target)
        copies[name] = {"source": str(source), "sha256": _sha256(target)}
    remaining = [p for p in denied if (out / p).exists()]
    if (
        remaining
        or (out / CODEBOOK_DIR).exists()
        or codebook_tables(out, allowed)
    ):
        raise AssertionError("a denied path or codebook table remains")
    if (out / ".git").exists():
        raise AssertionError("the review root holds a git directory")
    files = manifest(out)
    return {
        "schema": SCHEMA,
        "head": head,
        "root": str(out),
        "denied_paths": denied,
        "removed": removed,
        "removed_codebook_tables": tables,
        "codebook_check_allowed": sorted(allowed),
        "base": base,
        "context_copies": copies,
        "n_files": len(files),
        "manifest_sha256": hashlib.sha256(
            json.dumps(files, sort_keys=True).encode()
        ).hexdigest(),
    }


def _strings(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, Mapping):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list | tuple):
        for value in node:
            yield from _strings(value)


#: The harness's notice when a tool result is too large to return inline.
PERSISTED_RX = re.compile(r"(?:Full output saved to|saved to):?\s+(/\S+)")


def _result_paths(name: str | None, text: str) -> list[str]:
    """Paths a Glob or Grep result returned: each line's leading path.

    Absolute lines are taken as they are. A line that looks like a path
    relative to the root (word characters, dots, slashes) is taken too,
    because the harness returns Glob and Grep paths relative to the root.
    A Read result is file content, so paths quoted in it are not reads.
    A result whose call is unknown is treated like a Grep result.
    """
    if name not in (None, "Glob", "Grep"):
        return []
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        head = re.split(r":\d", line, maxsplit=1)[0].rstrip(":")
        if line.startswith("/"):
            out.append(head)
        elif re.fullmatch(r"[\w.@+-][\w./@+-]*", head):
            # A path relative to the root, as the harness returns them.
            out.append(head)
    return out


#: A pattern whose brace groups expand to more alternatives than this is
#: not classified, and voids the review.
BRACE_LIMIT = 4096
#: A pattern longer than this is not classified, and voids the review:
#: no Glob pattern a review needs is that long.
PATTERN_LIMIT = 1024
#: The scan steps one classification may take: characters scanned,
#: alternatives built, automaton states read. Past it the pattern is not
#: classified, and voids the review.
WORK_LIMIT = 1 << 22
#: A bracket class of more characters than this, counted over all its
#: ranges and members, is not read, and its pattern is not classified
#: (``[ -\U0010ffff]``).
CLASS_LIMIT = 1024
#: Characters no file name holds. A class member among them is no other
#: character at a stem position.
NOT_IN_NAMES = frozenset("/\0")


class _Work:
    """The scan steps left to the classification under way, if any.

    ``pattern_kind`` sets ``left`` for its call; outside one, spending is
    free, so the helpers can be called on their own.
    """

    left: int | None = None

    def spend(self, steps: int = 1) -> None:
        if self.left is not None:
            self.left -= steps
            if self.left < 0:
                raise OverflowError("past the work limit")


_WORK = _Work()


@functools.lru_cache(maxsize=1 << 16)
def class_end(text: str, start: int, escapes: bool = False) -> int:
    """Where the bracket class opening at ``text[start]`` closes.

    Returns the index of its ``]``, or -1 if it never closes, when the
    ``[`` is literal text. A ``]`` right after ``[``, ``[!`` or ``[^`` is
    a member, and a POSIX class such as ``[:punct:]`` is one member, as
    ripgrep, Bun and Node read them. With ``escapes`` a backslash inside
    the class escapes the next character, so ``[.\\]]`` closes at its last
    ``]``, as Bun reads it.
    """
    index = start + 1
    if index < len(text) and text[index] in "!^":
        index += 1
    if index < len(text) and text[index] == "]":
        index += 1
    while index < len(text):
        _WORK.spend()
        if text[index] == "]":
            return index
        if escapes and text[index] == "\\":
            index += 2
            continue
        if text.startswith("[:", index):
            close = text.find(":]", index + 2)
            if close != -1:
                index = close + 2
                continue
        index += 1
    return -1


def _next_token(
    text: str, index: int, glob: bool, escapes: bool = False
) -> int:
    """The index after the token at ``text[index]``.

    In a glob engine's reading a backslash escape and a closed bracket
    class are each one token, so the braces, commas and parentheses
    inside them are not syntax. Otherwise every character is one token.
    ``escapes`` is ``class_end``'s.
    """
    _WORK.spend()
    if glob and text[index] == "\\":
        return index + 2
    if glob and text[index] == "[":
        close = class_end(text, index, escapes)
        if close != -1:
            return close + 1
    return index + 1


def _find_open(text: str, index: int, glob: bool, escapes: bool) -> int:
    """The first ``{`` at or after ``index`` that is brace syntax."""
    if not glob:
        _WORK.spend(len(text) - index)
        return text.find("{", index)
    while index < len(text):
        if text[index] == "{":
            return index
        index = _next_token(text, index, glob, escapes)
    return -1


#: A brace sequence, ``{a..e}``, ``{1..10}`` or ``{1..10..2}``.
_SEQUENCE_RX = re.compile(
    r"([+-]?\d+|[A-Za-z])\.\.([+-]?\d+|[A-Za-z])(?:\.\.([+-]?\d+))?"
)


def _sequence(body: str, limit: int) -> list[str] | None:
    """The items of the brace sequence ``{body}`` as bash and Node read it,
    or ``None`` if ``body`` is not a sequence. If either end is
    zero-padded, every item is padded to the longer end's width. A number
    too long to read raises ``OverflowError``."""
    match = _SEQUENCE_RX.fullmatch(body)
    if match is None:
        return None
    low, high, step = match.groups()
    numeric = [end.lstrip("+-").isdigit() for end in (low, high)]
    if numeric[0] != numeric[1]:
        return None
    try:
        if numeric[0]:
            first, last = int(low), int(high)
        else:
            first, last = ord(low), ord(high)
        stride = abs(int(step or 1)) or 1
    except ValueError as error:
        raise OverflowError("a sequence number too long to read") from error
    values = range(
        first,
        last + (1 if last >= first else -1),
        stride if last >= first else -stride,
    )
    if len(values) > limit:
        raise OverflowError("too many sequence items")
    if not numeric[0]:
        return [chr(value) for value in values]
    padded = any(
        len(end.lstrip("+-")) > 1 and end.lstrip("+-").startswith("0")
        for end in (low, high)
    )
    width = max(len(low), len(high)) if padded else 0
    return [str(value).zfill(width) for value in values]


def brace_expansions(
    pattern: str,
    limit: int = BRACE_LIMIT,
    *,
    glob: bool = False,
    escapes: bool = False,
    sequences: bool = False,
) -> list[str]:
    """Every alternative a glob pattern's brace groups stand for.

    ``a{b,c}d`` stands for ``abd`` and ``acd``; groups nest. An unbalanced
    brace is literal text, and the scan goes on after it, so a later
    group still expands.

    By default braces are read as bash and Node's brace expansion read
    them: a group with no comma at its own depth is literal text, and so
    are backslashes and bracket classes. With ``sequences`` such a group
    that is a sequence (``{a..c}``, ``{1..3}``) stands for its items, as
    bash and Node read it. With ``glob`` braces are read as ripgrep and
    Bun read them: a group with no comma stands for its content (``{x}``
    for ``x``), and a brace or comma inside a bracket class or after a
    backslash is not syntax (``{a[.,]b,c}`` has two alternatives);
    ``escapes`` is ``class_end``'s. Raises ``OverflowError`` past
    ``limit`` alternatives.
    """
    start = _find_open(pattern, 0, glob, escapes)
    while start != -1:
        depth = 0
        commas: list[int] = []
        end = -1
        index = start
        while index < len(pattern):
            char = pattern[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index
                    break
            elif char == "," and depth == 1:
                commas.append(index)
            index = _next_token(pattern, index, glob, escapes)
        parts = None
        if end != -1 and (commas or glob):
            cuts = [start, *commas, end]
            parts = [
                pattern[left + 1 : right] for left, right in pairwise(cuts)
            ]
        elif end != -1 and sequences:
            parts = _sequence(pattern[start + 1 : end], limit)
        if parts is not None:
            out: list[str] = []
            for part in parts:
                _WORK.spend(len(pattern))
                out.extend(
                    brace_expansions(
                        pattern[:start] + part + pattern[end + 1 :],
                        limit,
                        glob=glob,
                        escapes=escapes,
                        sequences=sequences,
                    )
                )
                if len(out) > limit:
                    raise OverflowError("too many brace alternatives")
            return out
        start = _find_open(pattern, start + 1, glob, escapes)
    return [pattern]


#: The characters that open an extglob group before a ``(``, as Node's
#: minimatch reads them.
_EXTGLOB = "@+?*!"


@functools.lru_cache(maxsize=1 << 16)
def _extglob_group(
    text: str, index: int, escapes: bool = False
) -> tuple[int, tuple[int, ...]] | None:
    """If an extglob group opens at ``text[index]``, its closing index and
    the ``|`` at its own depth.

    As Node's minimatch reads it, only an extglob opener (``@(``, ``!(``
    and the like) nests; a plain ``(`` is literal, so ``@(a|(b)`` closes
    at the ``)`` after ``b``. Parentheses inside a bracket class or after
    a backslash are not syntax, and a group that never closes is literal
    text (``None``)."""
    if text[index] not in _EXTGLOB or not text.startswith("(", index + 1):
        return None
    depth = 1
    bars: list[int] = []
    scan = index + 2
    while scan < len(text):
        char = text[scan]
        if char in _EXTGLOB and text.startswith("(", scan + 1):
            depth += 1
            scan += 2
            continue
        if char == ")":
            depth -= 1
            if depth == 0:
                return scan, tuple(bars)
        elif char == "|" and depth == 1:
            bars.append(scan)
        scan = _next_token(text, scan, True, escapes)
    return None


def extglob_expansions(text: str, limit: int = BRACE_LIMIT) -> list[str]:
    """Every one-occurrence reading of ``text``'s extglob groups.

    Node's minimatch reads ``@(a|b)`` as ``a`` or ``b``, ``+(...)`` as one
    or more of them, ``?(...)`` and ``*(...)`` as none or some, and
    ``!(...)`` as anything else. Here ``@`` and ``+`` stand for each
    alternative once, ``?`` and ``*`` for each or nothing, and ``!`` for
    ``*``; ``glob_tokens`` reads repetition exactly. Raises
    ``OverflowError`` past ``limit``.
    """
    index = 0
    while index < len(text):
        group = _extglob_group(text, index)
        if group is not None:
            end, bars = group
            alternatives = [
                text[left + 1 : right]
                for left, right in pairwise([index + 1, *bars, end])
            ]
            if text[index] == "!":
                alternatives = ["*"]
            elif text[index] in "?*":
                alternatives = ["", *alternatives]
            out: list[str] = []
            for alternative in alternatives:
                _WORK.spend(len(text))
                out.extend(
                    extglob_expansions(
                        text[:index] + alternative + text[end + 1 :],
                        limit,
                    )
                )
                if len(out) > limit:
                    raise OverflowError("too many extglob readings")
            return out
        index = _next_token(text, index, True)
    return [text]


#: POSIX classes inside a bracket class, as Node's minimatch reads them.
#: A name it does not know stands for every printable character here.
_POSIX_CLASSES = {
    "alnum": string.ascii_letters + string.digits,
    "alpha": string.ascii_letters,
    "ascii": "".join(map(chr, range(128))),
    "blank": " \t",
    "cntrl": "".join(map(chr, range(32))) + "\x7f",
    "digit": string.digits,
    "graph": "".join(map(chr, range(33, 127))),
    "lower": string.ascii_lowercase,
    "print": "".join(map(chr, range(32, 127))),
    "punct": string.punctuation,
    "space": " \t\n\r\f\v",
    "upper": string.ascii_uppercase,
    "word": string.ascii_letters + string.digits + "_",
    "xdigit": string.hexdigits,
}

#: An automaton whose split closures hold more entries than this in all
#: is not built, and its pattern is ``unclassified``.
CLOSURE_LIMIT = 100_000

#: A token of a pattern as a glob engine reads it: ``("lit", c)`` one
#: character; ``("cut", c)`` a brace or comma left as literal text;
#: ``("any", "")`` ``?``; ``("star", "")`` ``*``; ``("set", chars)`` and
#: ``("notset", chars)`` a bracket class and a negated one; and
#: ``("group", (op, alternatives))`` an extglob, each alternative a
#: tuple of tokens.
Token = tuple[str, Any]


def _class_token(body: str, fold: bool, escapes: bool = False) -> Token:
    """The token for a bracket class whose text inside ``[...]`` is
    ``body``.

    A leading ``!`` or ``^`` negates it. ``a-z`` is a range and
    ``[:name:]`` a POSIX class. ``\\x`` stands for ``x`` and, read
    literally as ripgrep reads it, for a backslash too; with ``escapes``,
    as Bun reads it, for ``x`` alone, so ``[\\d]`` is ``d``. A class of
    one character is that character.
    """
    negated = body[:1] in ("!", "^")
    if negated:
        body = body[1:]
    items: list[tuple[Any, ...]] = []
    index = 0
    while index < len(body):
        if body.startswith("[:", index):
            close = body.find(":]", index + 2)
            if close != -1:
                name = body[index + 2 : close]
                members = _POSIX_CLASSES.get(name, _POSIX_CLASSES["print"])
                items.append(("set", frozenset(members)))
                index = close + 2
                continue
        if body[index] == "\\" and index + 1 < len(body):
            if not escapes:
                items.append(("set", frozenset("\\")))
            items.append(("char", body[index + 1], True))
            index += 2
            continue
        items.append(("char", body[index], False))
        index += 1
    chars: set[str] = set()
    index = 0
    while index < len(items):
        item = items[index]
        if (
            item[0] == "char"
            and index + 2 < len(items)
            and items[index + 1] == ("char", "-", False)
            and items[index + 2][0] == "char"
        ):
            low, high = ord(item[1]), ord(items[index + 2][1])
            if high - low + 1 > CLASS_LIMIT:
                raise OverflowError("a class too large to read")
            if (
                index + 4 < len(items)
                and items[index + 3] == ("char", "-", False)
                and items[index + 4][0] == "char"
            ):
                # ripgrep reads a chain (``d-d-d``) unlike Node and Bun.
                raise OverflowError("a chained range")
            _WORK.spend(max(high - low + 1, 1))
            chars.update(map(chr, range(low, high + 1)))
            if len(chars) > CLASS_LIMIT:
                raise OverflowError("a class too large to read")
            index += 3
            continue
        members = item[1] if item[0] == "set" else {item[1]}
        _WORK.spend(len(members))
        chars.update(members)
        if len(chars) > CLASS_LIMIT:
            raise OverflowError("a class too large to read")
        index += 1
    if fold:
        chars = {char.casefold() for char in chars}
    if negated:
        return ("notset", frozenset(chars))
    if len(chars) == 1:
        return ("lit", next(iter(chars)))
    return ("set", frozenset(chars))


def glob_tokens(
    text: str, fold: bool = False, escapes: bool = False
) -> tuple[Token, ...]:
    """``text`` as a glob engine reads it, one token per character matched.

    A backslash escapes the next character, a closed bracket class is one
    token, and an extglob group is one token holding its alternatives. A
    brace or comma left in the text after expansion is literal; it is
    marked so that segments are cut at it, as the plain reading cuts
    them. With ``fold`` every character is case-folded; ``escapes`` is
    ``class_end``'s.
    """
    tokens: list[Token] = []
    index = 0
    while index < len(text):
        _WORK.spend()
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            escaped = text[index + 1]
            tokens.append(("lit", escaped.casefold() if fold else escaped))
            index += 2
            continue
        if char == "[":
            close = class_end(text, index, escapes)
            if close != -1:
                tokens.append(
                    _class_token(text[index + 1 : close], fold, escapes)
                )
                index = close + 1
                continue
        group = _extglob_group(text, index, escapes)
        if group is not None:
            end, bars = group
            alternatives = tuple(
                glob_tokens(text[left + 1 : right], fold, escapes)
                for left, right in pairwise([index + 1, *bars, end])
            )
            tokens.append(("group", (char, alternatives)))
            index = end + 1
            continue
        if char == "*":
            tokens.append(("star", ""))
        elif char == "?":
            tokens.append(("any", ""))
        elif char in "{},":
            tokens.append(("cut", char))
        else:
            tokens.append(("lit", char.casefold() if fold else char))
        index += 1
    return tuple(tokens)


@functools.lru_cache(maxsize=512)
def _automaton(tokens: tuple[Token, ...]) -> tuple[Any, ...]:
    """A Thompson automaton for ``tokens`` read as one path segment.

    A state is ``("char", chars, negated, next)``, which reads one
    character in (or, negated, not in) ``chars``; ``("split", targets)``;
    or ``("match",)``. ``!(...)`` reads as ``*``. Returns the states, the
    start, the match state, each state's closure over splits and, for
    each state, the states whose closure holds it.
    """
    states: list[Any] = [("match",)]

    def new(state: Any) -> int:
        states.append(state)
        return len(states) - 1

    def loop(body: Any, after: int) -> int:
        """A split that may read ``body`` (built towards the split) any
        number of times before ``after``."""
        split = new(None)
        starts = body(split)
        states[split] = ("split", (*starts, after))
        return split

    def build(sequence: tuple[Token, ...], after: int) -> int:
        for kind, value in reversed(sequence):
            if kind in ("lit", "cut"):
                after = new(("char", frozenset(value), False, after))
            elif kind == "set":
                after = new(("char", value, False, after))
            elif kind == "notset":
                after = new(("char", value, True, after))
            elif kind == "any":
                after = new(("char", frozenset(), True, after))
            elif kind == "star" or (kind == "group" and value[0] == "!"):
                after = loop(
                    lambda back: [new(("char", frozenset(), True, back))],
                    after,
                )
            else:
                op, alternatives = value
                if op in "@?":
                    starts = [build(alt, after) for alt in alternatives]
                    if op == "?":
                        starts.append(after)
                    after = new(("split", tuple(starts)))
                else:
                    split = loop(
                        lambda back, alternatives=alternatives: [
                            build(alt, back) for alt in alternatives
                        ],
                        after,
                    )
                    if op == "+":
                        once = states[split][1][:-1]
                        split = new(("split", once))
                    after = split
        return after

    start = build(tokens, 0)
    closures = []
    total = 0
    for state in range(len(states)):
        seen, stack = set(), [state]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            if states[current][0] == "split":
                stack.extend(states[current][1])
        total += len(seen)
        _WORK.spend(len(seen))
        if total > CLOSURE_LIMIT:
            raise OverflowError("automaton too large")
        closures.append(frozenset(seen))
    holders: list[set[int]] = [set() for _ in states]
    for state, closure in enumerate(closures):
        for held in closure:
            holders[held].add(state)
    return (
        tuple(states),
        start,
        0,
        tuple(closures),
        tuple(map(frozenset, holders)),
    )


def _reads(state: Any, char: str) -> bool:
    return state[0] == "char" and (char in state[1]) != state[2]


def _forward(tokens: tuple[Token, ...], name: str) -> list[frozenset[int]]:
    """The closed state sets after each prefix of ``name``."""
    states, start, _, closures, _ = _automaton(tokens)
    current = closures[start]
    out = [current]
    for char in name:
        _WORK.spend(len(current))
        current = frozenset().union(
            *(
                closures[states[s][3]]
                for s in current
                if _reads(states[s], char)
            )
        )
        out.append(current)
    return out


def glob_match(name: str, tokens: Sequence[Token]) -> bool:
    """Whether ``tokens``, read as one path segment, match ``name``."""
    return 0 in _forward(tuple(tokens), name)[-1]


def pins_stem(name: str, tokens: Sequence[Token]) -> bool:
    """Whether ``tokens`` match ``name`` and, at every position of its
    stem, read no other character, case aside.

    That is the test of a segment that names ``name``: the stem is spelled
    whatever syntax spells it (``[d]eep``, ``d+(e)p``, ``{d}eep``), while
    a wildcard, a negated class or a class of two characters that differ
    other than in case stands for part of it. No file name holds ``/`` or
    a NUL, so a class's ``/`` or NUL is no other character here
    (``[d/]eep`` pins, as ripgrep reads it).
    """
    tokens = tuple(tokens)
    states, _, accept, closures, holders = _automaton(tokens)
    forward = _forward(tokens, name)
    if accept not in forward[-1]:
        return False
    # finishing[j]: the states from whose closure name[j:] is read whole.
    finishing = [frozenset()] * (len(name) + 1)
    finishing[-1] = holders[accept]
    for j in range(len(name) - 1, -1, -1):
        _WORK.spend(len(states))
        finishing[j] = frozenset().union(
            *(
                holders[s]
                for s in range(len(states))
                if _reads(states[s], name[j])
                and states[s][3] in finishing[j + 1]
            )
        )
    for i in range(len(Path(name).stem)):
        for s in forward[i]:
            state = states[s]
            if state[0] != "char" or state[3] not in finishing[i + 1]:
                continue
            if state[2] or any(
                char.casefold() != name[i].casefold()
                for char in state[1]
                if char not in NOT_IN_NAMES
            ):
                return False
    return True


def _letters(tokens: Sequence[Token]) -> set[str]:
    """Every character a token of ``tokens`` names: literals and class
    members, inside extglob groups too."""
    out: set[str] = set()
    for kind, value in tokens:
        if kind in ("lit", "cut"):
            out.add(value)
        elif kind == "set":
            _WORK.spend(len(value))
            out |= value
        elif kind == "group":
            for alternative in value[1]:
                out |= _letters(alternative)
    return out


def _negation_text(text: str) -> bool:
    """Whether ``text`` holds ``!(`` outside a class or an escape, whether
    or not the group parses."""
    index = 0
    while index < len(text):
        if text.startswith("!(", index):
            return True
        index = _next_token(text, index, True)
    return False


def _negates(tokens: Sequence[Token]) -> bool:
    """Whether ``tokens`` hold an extglob ``!(...)``, at any depth."""
    return any(
        kind == "group"
        and (
            value[0] == "!"
            or any(_negates(alternative) for alternative in value[1])
        )
        for kind, value in tokens
    )


def _view(tokens: Sequence[Token]) -> str:
    """The literal characters of ``tokens``; a wildcard, a class of more
    than one character or an extglob group shows as a NUL, which no path
    holds."""
    return "".join(
        value if kind in ("lit", "cut") else "\0" for kind, value in tokens
    )


def glob_segments(tokens: Sequence[Token]) -> list[tuple[Token, ...]]:
    """Every segment of ``tokens``.

    A ``/``, and a brace or comma left as literal text, always cut. A
    class that may stand for ``/`` both cuts and does not, so every
    segment between such classes is returned too. Raises
    ``OverflowError`` past ``BRACE_LIMIT`` segments.
    """

    def may_be_slash(token: Token) -> bool:
        kind, value = token
        return (kind == "set" and "/" in value) or (
            kind == "notset" and "/" not in value
        )

    runs: list[list[Token]] = [[]]
    for token in tokens:
        if token[0] == "cut" or token == ("lit", "/"):
            runs.append([])
        else:
            runs[-1].append(token)
    out: list[tuple[Token, ...]] = []
    for run in runs:
        maybe = [i for i, token in enumerate(run) if may_be_slash(token)]
        starts = [0, *(i + 1 for i in maybe)]
        ends = [*maybe, len(run)]
        if len(out) + (len(maybe) + 1) * (len(maybe) + 2) // 2 > BRACE_LIMIT:
            raise OverflowError("too many segments")
        _WORK.spend(len(starts) * len(ends))
        out.extend(tuple(run[a:b]) for a in starts for b in ends if a <= b)
    return out


def _written_kinds(
    text: str,
    denied: Sequence[str],
    names: set[str],
    stems: set[str],
) -> set[str]:
    """The v6 rule: ``text`` cut at every ``/``, brace and comma, and
    each segment read with ``fnmatchcase``. Round 10's smallest fix adds
    the whole-stem test on ``text``'s ``/``-segments, uncut at braces or
    commas, so a class holding one (``stem[.,]md``) is read whole."""
    kinds = set()
    _WORK.spend(len(text) * (len(names) + 1))
    segments = re.split(r"[/{},]", text)
    if text.startswith(("/", "~")) or ".." in segments:
        kinds.add("outside_root")
    if any(d in text for d in denied) or CODEBOOK_DIR in text:
        kinds.add("denied")
    for segment in segments:
        if segment in names or any(
            segment.startswith(f"{stem}.") for stem in stems
        ):
            kinds.add("denied")
    if any(
        Path(name).stem in segment and fnmatchcase(name, segment)
        for segment in {*segments, *text.split("/")}
        for name in names
    ):
        kinds.add("denied")
    return kinds


def _engine_kinds(
    tokens: Sequence[Token],
    denied: Sequence[str],
    names: set[str],
    stems: set[str],
) -> set[str]:
    """The same tests on a reading's tokens. A segment names a denied file
    if its literal view equals the name or starts with its stem and a dot,
    if it holds the whole stem and matches the name, or if it pins the
    name's stem (``pins_stem``)."""
    kinds = set()
    segments = glob_segments(tokens)
    if (tokens and tokens[0] in (("lit", "/"), ("lit", "~"))) or any(
        _view(segment) == ".." for segment in segments
    ):
        kinds.add("outside_root")
    view = _view(tokens)
    if any(d in view for d in denied):
        kinds.add("denied")
    for segment in segments:
        _WORK.spend(len(segment) + len(names))
        literal = _view(segment)
        if literal in names or any(
            literal.startswith(f"{stem}.") for stem in stems
        ):
            kinds.add("denied")
        letters = _letters(segment)
        for name in names:
            stem = Path(name).stem
            if (stem in literal and glob_match(name, segment)) or (
                set(stem) <= letters and pins_stem(name, segment)
            ):
                kinds.add("denied")
    return kinds


def pattern_kind(pattern: str, denied: Sequence[str]) -> str:
    """How a Glob pattern or a Grep file filter is classed.

    The pattern is expanded every way a glob engine might read it: its
    brace groups as bash and Node read them, with and without sequences
    (``{a..c}``), and as ripgrep and Bun read them, a backslash inside a
    class escaping or not (``brace_expansions``); each result also with
    its backslashes as ``/``, as Node reads them on any platform; then
    its extglobs, once each (``extglob_expansions``). The pattern and
    every text so produced are read two ways, and flagged if either
    reading flags them:

    1. With ``fnmatchcase``, on segments cut at ``/`` and at every brace
       or comma (the v6 rule), and, for the whole-stem test below, also on
       segments cut at ``/`` only (round 10's smallest fix).
    2. As the engines read it (``glob_tokens``): each backslash escape
       and bracket class is one character, a class of one character is
       that character, an extglob is read exactly, repetition included,
       and segments are cut at ``/`` and at any brace or comma left as
       literal text, never inside a class. This reading runs with and
       without escapes inside classes, and again with case folded: the
       root's file system ignores case, and so does Node's glob on macOS.

    In any reading:

    - A text leaves the root if it is absolute or holds a ``..`` segment.
    - It names a denied path, even to confirm the path's absence, if that
      path's text appears in it, or if one of its segments is a denied
      basename, a denied stem followed by a dot, or the codebook
      directory's last segment.
    - So does a segment that holds a denied name's whole stem and, read
      as a wildcard, matches that name (``stem*``, ``stem?md``,
      ``stem[.,]md``), and, in the engines' reading, one that matches the
      name and reads no other character at any position of its stem
      (``pins_stem``: ``[d]eep``, ``d+(e)p``).

    In the automaton ``!(...)`` reads as ``*``, so a filter that
    excludes a name beside a whole denied stem (``stem!(.md)``) is
    classed as naming it. Any other pattern holding ``!(`` outside a
    class or escape, whether or not the group closes, is
    ``unclassified``: a negation can spell a name by excluding everything
    else (``!(|[!d]|??*)`` is ``d``). A literal ``!(`` is written
    ``![(]``. A wildcard, a negated class or a
    class of two or more characters that stands at a position of the
    stem (``*name_part*``, ``[xy]tem.md``) is not classified. A pattern
    is ``unclassified`` if it is longer than
    ``PATTERN_LIMIT``, has more than ``BRACE_LIMIT`` readings or segments
    in one reading, takes more than ``WORK_LIMIT`` scan steps (charged as
    the work is done), has a class of more than ``CLASS_LIMIT``
    characters or a chained range (``[d-d-d]``, which ripgrep reads
    unlike Node and Bun), is nested too deep to read, has an automaton
    past ``CLOSURE_LIMIT`` or has a sequence number too long to read.
    """
    names = {Path(d).name for d in denied} | {Path(CODEBOOK_DIR).name}
    stems = {Path(d).stem for d in denied if Path(d).suffix}
    plain = ([*denied, CODEBOOK_DIR], names, stems)
    folded = (
        [d.casefold() for d in plain[0]],
        {name.casefold() for name in names},
        {stem.casefold() for stem in stems},
    )
    kinds = set()
    if len(pattern) > PATTERN_LIMIT:
        return "unclassified"
    _WORK.left = WORK_LIMIT
    try:
        alternatives = {
            *brace_expansions(pattern),
            *brace_expansions(pattern, sequences=True),
            *brace_expansions(pattern, glob=True),
            *brace_expansions(pattern, glob=True, escapes=True),
        }
        alternatives |= {text.replace("\\", "/") for text in alternatives}
        readings: set[str] = set()
        for alternative in sorted(alternatives):
            readings.update(extglob_expansions(alternative))
            if len(readings) > BRACE_LIMIT:
                raise OverflowError("too many readings")
        negated = False
        for text in {pattern, *alternatives, *readings}:
            negated = negated or _negation_text(text)
            kinds |= _written_kinds(text, denied, names, stems)
            for escapes in (False, True):
                tokens = glob_tokens(text, escapes=escapes)
                negated = negated or _negates(tokens)
                kinds |= _engine_kinds(tokens, *plain)
                kinds |= _engine_kinds(
                    glob_tokens(text, fold=True, escapes=escapes), *folded
                )
    except (OverflowError, RecursionError):
        return "unclassified"
    finally:
        # The memo tables hold this pattern's texts and automata only.
        _WORK.left = None
        for memo in (class_end, _extglob_group, _automaton):
            memo.cache_clear()
    for kind in ("outside_root", "denied"):
        if kind in kinds:
            return kind
    # ``!(...)`` can spell a name by excluding everything else
    # (``!(|[!d]|??*)`` is ``d``), which the automaton does not read.
    return "unclassified" if negated else "inside_root"


def denied_from_record(record: Mapping[str, Any]) -> list[str]:
    """Every path a root record keeps out of the review root.

    That is the exclusion lists' ``denied_paths``, every file the builder
    removed (``removed``, the codebook files among them) and every other
    code-map table it removed (``removed_codebook_tables``).
    """
    return sorted(
        {
            *record["denied_paths"],
            *record["removed"],
            *record["removed_codebook_tables"],
        }
    )


def read_log(
    transcript: Path, root: Path, denied: Sequence[str]
) -> dict[str, Any]:
    """Every path a review lane's tool calls named or its results returned.

    ``transcript`` is the lane's stream-json record: one JSON object per
    line. Tool calls are ``tool_use`` blocks; results are ``tool_result``
    blocks. A call's path fields must lie inside the root and outside the
    denied paths; so must every path a Glob or Grep result returns,
    absolute or relative to the root. A Glob's pattern and a Grep's file
    filter must not be absolute, hold a ``..`` segment or name a denied
    path, by its path, its basename or its stem before a dot, even to
    confirm its absence; ``pattern_kind`` reads each pattern as the glob
    engines might. ``denied`` is every path the root record keeps out
    (``denied_from_record``), and paths are compared without case, as the
    root's file system compares them.
    Paths quoted inside a file the lane read are content, not reads. When the
    harness saves an oversized result outside the root, the log records
    the notice; the review is void only if a later call opens that file.
    No content is copied into the log, only paths.
    """
    root = root.resolve()
    calls: list[dict[str, Any]] = []
    names: dict[str, str] = {}
    named: set[str] = set()
    patterns: set[str] = set()
    returned: set[str] = set()
    persisted: set[str] = set()
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = event.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, Mapping):
                continue
            if block.get("type") == "tool_use":
                names[str(block.get("id"))] = str(block.get("name"))
                fields = {
                    key: str(value)
                    for key, value in (block.get("input") or {}).items()
                    if key in PATH_FIELDS
                }
                calls.append({"tool": block.get("name"), **fields})
                for key in ("file_path", "path"):
                    if key in fields:
                        named.add(fields[key])
                # A Glob's pattern and a Grep's file filter name paths too.
                # A Grep's regex is searched text, not a path.
                if block.get("name") == "Glob" and "pattern" in fields:
                    patterns.add(fields["pattern"])
                if "glob" in fields:
                    patterns.add(fields["glob"])
            elif block.get("type") == "tool_result":
                name = names.get(str(block.get("tool_use_id")))
                for text in _strings(block.get("content")):
                    found = set(PERSISTED_RX.findall(text))
                    persisted.update(found)
                    returned.update(
                        p for p in _result_paths(name, text) if p not in found
                    )

    denied_folded = {d.casefold() for d in denied}

    def classify(path: str) -> str:
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = root / path
        try:
            relative = resolved.resolve().relative_to(root)
        except ValueError:
            return "outside_root"
        folded = relative.as_posix().casefold()
        if folded in denied_folded or folded.startswith(
            CODEBOOK_DIR.casefold()
        ):
            return "denied"
        return "inside_root"

    paths = {path: classify(path) for path in sorted(named | returned)}
    paths.update(
        {
            f"pattern:{pattern}": pattern_kind(pattern, denied)
            for pattern in sorted(patterns)
        }
    )
    bad = sorted(path for path, kind in paths.items() if kind != "inside_root")
    return {
        "schema": "track_b_b0_1_review_read_log.v7",
        "root": str(root),
        "n_denied": len(denied_folded),
        "n_tool_calls": len(calls),
        "tool_calls": calls,
        "paths": paths,
        "harness_persisted_outputs": sorted(persisted),
        "persisted_outputs_opened": sorted(persisted & named),
        "paths_outside_root_or_denied": bad,
        "review_counts": not bad,
    }


#: A shell word that names a path outside the working directory: an
#: absolute path, a home-relative one, or any ``..`` segment.
_ESCAPE_RX = re.compile(r"(?:^|/)\.\.(?:/|$)")
#: Executables in the system's bin directories. In program position they
#: are programs, not data the lane reads.
_PROGRAM_RX = re.compile(
    r"^(?:/(?:usr/(?:local/)?)?s?bin/[^/]+|/opt/homebrew/bin/[^/]+)$"
)
#: Devices a command may write to or read nothing from.
_DEVICES = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr"})


#: A shell expansion: $NAME, ${...}, $(...), ANSI-C $'...', locale
#: $"..." or a backquote.
_EXPANSION_RX = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*|\{|\(|'|\")|`")


def _expansions(script: str) -> list[str]:
    """Shell expansions in ``script`` that are not inside single quotes.

    Inside single quotes the shell expands nothing (``sed -n '1,$p'``);
    bare or inside double quotes it does. A backslash escapes the next
    character outside single quotes.
    """
    found: list[str] = []
    state = None  # None, "'" or '"'
    index = 0
    while index < len(script):
        char = script[index]
        if state == "'":
            if char == "'":
                state = None
        elif char == "\\":
            index += 2
            continue
        elif char == "'" and state is None:
            state = "'"
        elif char == '"':
            state = None if state == '"' else '"'
        else:
            match = _EXPANSION_RX.match(script, index)
            if match:
                found.append(match.group(0))
        index += 1
    return found


def _shell_words(command: str) -> list[str]:
    """Split a shell command into words, keeping quoted text together.

    ``shlex`` fails on unbalanced quotes; the fallback is a plain split, so
    a malformed command is still scanned word by word.
    """
    import shlex

    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


#: Programs that run their ``-c`` argument as a shell script.
_SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "fish"})


def _scripts(command: str) -> list[str]:
    """The shell scripts inside ``command``, at every depth.

    After a shell program (``sh``, ``bash``, ``zsh`` and the like), every
    later word is treated as a script, whatever options come between
    (``bash -o errexit -c '...'``). So are the words after ``eval``. Each
    is split again for nested shells. Code given to other interpreters
    (``python3 -c``) is not a shell script, so its dollars are not
    expansions; its paths are still scanned by ``_path_words``.
    """
    found: list[str] = []
    words = _shell_words(command)
    for index, word in enumerate(words):
        name = word.rsplit("/", 1)[-1]
        if name == "eval" and index + 1 < len(words):
            script = " ".join(words[index + 1 :])
            found.append(script)
            found.extend(_scripts(script))
            break
        if name in _SHELLS:
            for script in words[index + 1 :]:
                found.append(script)
                if re.search(r"\s", script):
                    found.extend(_scripts(script))
            break
    return found


#: Tokens that end a simple command, so the next word is a program.
_SEPARATORS = frozenset({";", "&&", "||", "|", "&", "(", ")", "\n"})
#: Commands that change the working directory.
_DIRECTORY_CHANGES = frozenset({"cd", "pushd", "popd", "chdir"})


def _program_words(script: str) -> set[str]:
    """The words of ``script`` in program position.

    That is each simple command's first word, after any ``NAME=value``
    assignments and an ``env`` or ``command`` prefix, split at shell
    separators.
    """
    import shlex

    lexer = shlex.shlex(script, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = script.split()
    programs: set[str] = set()
    expect = True
    for token in tokens:
        if token in _SEPARATORS or set(token) <= set(";&|()"):
            expect = True
            continue
        if expect:
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
                continue
            if token in ("env", "command", "exec", "nice"):
                programs.add(token)
                continue
            programs.add(token)
            expect = False
    return programs


def _path_words(command: str) -> list[str]:
    """Words of a shell command, and of any ``-c`` script inside it, that
    could name a path: every word, split again at ``=``, ``:``, brace
    expansion's ``{``, ``,`` and ``}`` and shell separators, so
    ``--out=/x``, ``a:/x``, ``{a,/x}`` and ``cd /x;ls`` are seen."""
    words: list[str] = []
    for word in _shell_words(command):
        if re.search(r"\s", word):
            # A script or code: its own words are the candidates.
            words.extend(_path_words(word))
            continue
        for piece in re.split(r"[=:;&|()<>`{},]", word):
            piece = piece.strip().strip("'\"")
            if piece:
                words.append(piece)
    return words


def read_log_codex(
    transcript: Path, root: Path, denied: Sequence[str]
) -> dict[str, Any]:
    """The read log for a Codex review lane, whose tools are shell commands.

    ``transcript`` is ``codex exec --json``'s event stream: one JSON object
    per line, each command an ``item`` of type ``command_execution``. The
    lane runs with the root as its working directory. Each command, and
    each shell script inside it at every depth, is scanned, and any of
    these voids the review:

    - a word that leaves the root or names a denied path: an absolute
      path (an executable in a system bin directory is exempt only in
      program position), a ``..`` segment, or any word starting with
      ``~``;
    - an unquoted shell expansion: ``$NAME``, ``${...}``, ``$(...)``,
      ``$'...'``, ``$"..."``, a backquote, or zsh's ``=program``;
    - a directory change (``cd``, ``pushd``, ``popd``).

    A relative word resolves inside the root, where no denied file exists,
    so naming a denied file there reads nothing. Brace expansion is split
    into its parts, and words are re-split at any whitespace.

    This is a conservative detector for shell lanes, not a sandbox. It
    cannot see a path a program builds at run time
    (``open('/' + 'etc')`` in Python code), so it cannot certify a shell
    lane as blind. The Q6 review of record runs on a lane with no shell
    (d693); this log supplements reviews on other lanes. Command output is
    not read. No content is copied into the log, only commands.
    """
    root = root.resolve()
    denied_set = set(denied)
    commands: list[str] = []
    seen: set[tuple[str, str]] = set()
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, Mapping) else None
        if not isinstance(item, Mapping):
            continue
        if item.get("type") != "command_execution":
            continue
        identifier = str(item.get("id", len(commands)))
        command = str(item.get("command", ""))
        if (identifier, command) in seen:
            continue
        seen.add((identifier, command))
        commands.append(command)

    def classify(word: str, programs: set[str]) -> str | None:
        absolute = word.startswith("/")
        if word in _DEVICES:
            return None
        if absolute and _PROGRAM_RX.match(word) and word in programs:
            return None
        if not absolute and not _ESCAPE_RX.search(word):
            # Resolves inside the root, where no denied file exists.
            return None
        target = Path(word) if absolute else root / word
        try:
            relative = target.resolve().relative_to(root).as_posix()
        except ValueError:
            return "outside_root"
        if relative in denied_set or relative.startswith(CODEBOOK_DIR):
            return "denied"
        return "inside_root"

    flagged: dict[str, str] = {}
    for command in commands:
        scripts = _scripts(command)
        programs: set[str] = set()
        for script in [command, *scripts]:
            programs |= _program_words(script)
        # Unquoted expansions in a shell script cannot be resolved here.
        for script in scripts:
            for expansion in _expansions(script):
                flagged[expansion] = "shell_expansion"
        # A directory change moves the working directory off the root.
        for program in programs:
            if program.rsplit("/", 1)[-1] in _DIRECTORY_CHANGES:
                flagged[program] = "directory_change"
        for script in [command, *scripts]:
            for word in _shell_words(script):
                for piece in re.split(r"[;&|()<>{},]", word):
                    if piece.startswith("~"):
                        # Tilde expansion: a home directory, any user's.
                        flagged[piece] = "outside_root"
                if re.fullmatch(r"=[A-Za-z0-9_.+-]+", word):
                    # zsh's =program expands to the program's path.
                    flagged[word] = "shell_expansion"
        for word in _path_words(command):
            kind = classify(word, programs)
            if kind not in (None, "inside_root"):
                flagged[word] = kind
    return {
        "schema": "track_b_b0_1_review_read_log_codex.v2",
        "root": str(root),
        "n_commands": len(commands),
        "commands": commands,
        "paths_outside_root_or_denied": sorted(flagged),
        "flagged_kinds": dict(sorted(flagged.items())),
        "review_counts": not flagged,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    b = commands.add_parser("build")
    b.add_argument("--head", required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--inventory", type=Path, action="append", required=True)
    b.add_argument("--context", action="append", default=[])
    b.add_argument("--record", type=Path, required=True)
    b.add_argument("--allow", action="append", default=[])
    b.add_argument("--base")
    r = commands.add_parser("readlog")
    r.add_argument("--transcript", type=Path, required=True)
    r.add_argument("--root", type=Path, required=True)
    r.add_argument("--root-record", type=Path, required=True)
    r.add_argument("--record", type=Path, required=True)
    r.add_argument(
        "--format",
        choices=("claude", "codex"),
        default="claude",
        help="the lane's transcript format (default: claude stream-json)",
    )
    args = parser.parse_args(argv)
    if args.command == "build":
        context = {}
        for item in args.context:
            name, _, source = item.partition("=")
            context[name] = Path(source)
        record = build(
            args.head,
            args.out,
            args.inventory,
            context,
            allowed=args.allow,
            base=args.base,
        )
    else:
        denied = denied_from_record(
            json.loads(args.root_record.read_text(encoding="utf-8"))
        )
        reader = read_log_codex if args.format == "codex" else read_log
        record = reader(args.transcript, args.root, denied)
    with args.record.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=1, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps({k: v for k, v in record.items() if k.startswith("n_")}),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
