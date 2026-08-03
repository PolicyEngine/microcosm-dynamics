"""Streaming §10.1 canonical JSON.

Amendment 8 keeps every logical member relation exhaustive while allowing a
compact wire form.  Both the analytic object and the streaming member digest
therefore have to be produced without materializing the relation, so this
module emits canonical bytes incrementally.

A value tree may contain :class:`LazyArray` nodes.  Each such node supplies a
fresh iterator every time the tree is walked, so the same tree can be hashed,
measured, and written without ever holding its expansion.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from typing import Any, BinaryIO


class LazyArray:
    """A JSON array whose members are produced on demand.

    ``factory`` must return a fresh iterator on every call and must yield the
    exact same value sequence each time; the canonical bytes would otherwise
    depend on traversal count.
    """

    __slots__ = ("_factory",)

    def __init__(self, factory: Callable[[], Iterator[Any]]) -> None:
        self._factory = factory

    def __iter__(self) -> Iterator[Any]:
        return self._factory()


def _scalar_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def iter_canonical_chunks(value: Any) -> Iterator[bytes]:
    """Yield the §10.1 canonical encoding of *value* without a terminal LF."""

    if isinstance(value, LazyArray):
        yield b"["
        first = True
        for member in value:
            if not first:
                yield b","
            first = False
            yield from iter_canonical_chunks(member)
        yield b"]"
        return
    if isinstance(value, dict):
        yield b"{"
        first = True
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError("canonical object keys must be strings")
            if not first:
                yield b","
            first = False
            yield _scalar_bytes(key)
            yield b":"
            yield from iter_canonical_chunks(value[key])
        yield b"}"
        return
    if isinstance(value, (list, tuple)):
        yield b"["
        for index, member in enumerate(value):
            if index:
                yield b","
            yield from iter_canonical_chunks(member)
        yield b"]"
        return
    if isinstance(value, float):
        raise TypeError("canonical JSON admits no floating-point value")
    yield _scalar_bytes(value)


def canonical_stream_digest(value: Any) -> tuple[int, str]:
    """Return the terminal-LF canonical byte length and SHA-256 of *value*."""

    digest = hashlib.sha256()
    length = 0
    for chunk in iter_canonical_chunks(value):
        digest.update(chunk)
        length += len(chunk)
    digest.update(b"\n")
    return length + 1, digest.hexdigest()


def write_canonical(value: Any, sink: BinaryIO) -> tuple[int, str]:
    """Write terminal-LF canonical bytes and return their length and SHA-256."""

    digest = hashlib.sha256()
    length = 0
    for chunk in iter_canonical_chunks(value):
        digest.update(chunk)
        sink.write(chunk)
        length += len(chunk)
    digest.update(b"\n")
    sink.write(b"\n")
    return length + 1, digest.hexdigest()


def member_array_digest(members: Any) -> tuple[int, str]:
    """Hash a complete member array under the §22.2.4 streaming construction.

    The byte stream is exactly ``[`` , the canonical member objects separated
    by ``,``, then ``]\\n`` — identical to canonical serialization of the
    stored array, so an explicit and an analytic arm agree by construction.
    """

    return canonical_stream_digest(LazyArray(lambda: iter(members)))
