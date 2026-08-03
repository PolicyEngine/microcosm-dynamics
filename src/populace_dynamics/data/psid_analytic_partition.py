"""§22 lossless analytic range partitions.

Revision 9 required every exhaustive numeric-range member relation to be a
bare JSON array.  §22.4.5 measured that requirement at 820,709,179,087
mandatory members and proved it physically unconstructible.  Amendment 8
replaces only the wire form: a relation with at most 4,096 logical members
keeps its inherited explicit array, and a larger one takes the closed
``analytic_closed_intervals_v1`` object whose expansion is byte-identical.

Nothing here narrows a relation.  Every consumer still sees the complete
member sequence, and every retained ``*_member_domain_sha256`` remains the
SHA-256 of the complete logical member array under §10.1.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .psid_canonical_stream import (
    LazyArray,
    canonical_stream_digest,
)

ANALYTIC_REPRESENTATION = "analytic_closed_intervals_v1"
MEMBER_THRESHOLD = 4_096
EMPTY_MEMBER_DOMAIN_SHA256 = (
    "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
)
ANALYTIC_KEYS = (
    "literal_member_rows",
    "range_interval_rows",
    "representation",
    "total_member_count",
)
RANGE_INTERVAL_ROW_KEYS = ("source_entry_ref", "intervals", "member_count")
VALUE_TYPES = ("json_integer", "rational")

# Section 22.2.2 admits no plus, whitespace, grouping, exponent, leading
# zero, negative zero, or zero denominator, and spells zero exactly `0/1`.
_RATIONAL_ATOM = re.compile(r"(0|-?[1-9][0-9]*)/[1-9][0-9]*\Z")


def is_json_integer(value: Any) -> bool:
    """Return whether *value* is a JSON integer, excluding booleans."""

    return isinstance(value, int) and not isinstance(value, bool)


def encode_atom(value: Fraction, value_type: str) -> int | str:
    """Encode one interval atom under the normalized entry's value type."""

    if value_type == "json_integer":
        if value.denominator != 1:
            raise ValueError("json_integer atom must be integral")
        return value.numerator
    if value_type == "rational":
        reduced = Fraction(value)
        return f"{reduced.numerator}/{reduced.denominator}"
    raise ValueError(f"unsupported entry value type: {value_type}")


def decode_atom(atom: Any, value_type: str) -> Fraction:
    """Decode one interval atom, rejecting every noncanonical spelling."""

    if value_type == "json_integer":
        if not is_json_integer(atom):
            raise ValueError("json_integer atom must be a JSON integer")
        return Fraction(atom, 1)
    if value_type == "rational":
        if not isinstance(atom, str) or not _RATIONAL_ATOM.fullmatch(atom):
            raise ValueError(f"noncanonical rational atom: {atom!r}")
        numerator_text, denominator_text = atom.split("/")
        numerator = int(numerator_text)
        denominator = int(denominator_text)
        value = Fraction(numerator, denominator)
        if value.numerator != numerator or value.denominator != denominator:
            raise ValueError(f"unreduced rational atom: {atom!r}")
        return value
    raise ValueError(f"unsupported entry value type: {value_type}")


@dataclass(frozen=True)
class NormalizedRange:
    """One normalized numeric-range entry addressed by an analytic row."""

    source_entry_ref: str
    lower: Fraction
    step: Fraction
    source_member_count: int
    value_type: str

    def __post_init__(self) -> None:
        if self.step <= 0:
            raise ValueError("normalized range step must be positive")
        if self.source_member_count < 0:
            raise ValueError("source member count must be nonnegative")
        if self.value_type not in VALUE_TYPES:
            raise ValueError(f"unsupported value type: {self.value_type}")

    def value(self, index: int) -> Fraction:
        """Return the exact scalar at a zero-based source-member index."""

        if not 0 <= index < self.source_member_count:
            raise ValueError(f"member index outside range: {index}")
        return self.lower + index * self.step

    def index(self, value: Fraction) -> int:
        """Return the exact zero-based index of an exact source member."""

        offset = (value - self.lower) / self.step
        if offset.denominator != 1 or offset < 0:
            raise ValueError(f"value is not a source member: {value}")
        index = offset.numerator
        if index >= self.source_member_count:
            raise ValueError(f"value is not a source member: {value}")
        return index


@dataclass(frozen=True)
class LiteralEntry:
    """One normalized literal entry contributing at most one complete row."""

    source_entry_ref: str
    row: dict[str, Any] | None


@dataclass(frozen=True)
class RangeEntry:
    """One normalized range entry plus this relation's included indexes."""

    normalized: NormalizedRange
    runs: tuple[tuple[int, int], ...]
    build_row: Callable[[NormalizedRange, int], dict[str, Any]]

    @property
    def member_count(self) -> int:
        return sum(count for _, count in self.runs)


@dataclass(frozen=True)
class AnalyticRelation:
    """One logical member relation in complete normalized source-entry order."""

    entries: tuple[LiteralEntry | RangeEntry, ...]

    @property
    def literal_rows(self) -> list[dict[str, Any]]:
        return [
            entry.row
            for entry in self.entries
            if isinstance(entry, LiteralEntry) and entry.row is not None
        ]

    @property
    def range_entries(self) -> list[RangeEntry]:
        return [
            entry for entry in self.entries if isinstance(entry, RangeEntry)
        ]

    @property
    def member_count(self) -> int:
        return len(self.literal_rows) + sum(
            entry.member_count for entry in self.range_entries
        )

    def iter_rows(self) -> Iterator[dict[str, Any]]:
        """Yield every complete member row in §22.2.3 inverse order."""

        for entry in self.entries:
            if isinstance(entry, LiteralEntry):
                if entry.row is not None:
                    yield entry.row
                continue
            for start, count in entry.runs:
                for offset in range(count):
                    yield entry.build_row(entry.normalized, start + offset)


def maximal_runs(indexes: Sequence[int]) -> tuple[tuple[int, int], ...]:
    """Group ascending unique indexes into unique maximal consecutive runs."""

    runs: list[tuple[int, int]] = []
    previous: int | None = None
    start = 0
    count = 0
    for index in indexes:
        if previous is not None and index <= previous:
            raise ValueError("member indexes must strictly ascend")
        if previous is not None and index == previous + 1:
            count += 1
        else:
            if count:
                runs.append((start, count))
            start = index
            count = 1
        previous = index
    if count:
        runs.append((start, count))
    return tuple(runs)


def merge_runs(
    runs: Iterator[tuple[int, int]] | Sequence[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    """Merge ascending disjoint runs that are index-adjacent.

    Two bands that each render completely and abut in index space form one
    maximal run; leaving them split would be the noncanonical encoding
    §22.2.2 rejects.
    """

    merged: list[tuple[int, int]] = []
    for start, count in runs:
        if count <= 0:
            raise ValueError("a run must be nonempty")
        if merged:
            previous_start, previous_count = merged[-1]
            end = previous_start + previous_count
            if start < end:
                raise ValueError("runs must be disjoint and ascending")
            if start == end:
                merged[-1] = (previous_start, previous_count + count)
                continue
        merged.append((start, count))
    return tuple(merged)


def subtract_runs(
    runs: Sequence[tuple[int, int]],
    removed: Sequence[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    """Return ``runs`` minus ``removed`` as unique maximal runs."""

    result: list[tuple[int, int]] = []
    pending = list(removed)
    position = 0
    for start, count in runs:
        cursor = start
        end = start + count
        while position < len(pending) and sum(pending[position]) <= cursor:
            position += 1
        index = position
        while index < len(pending) and pending[index][0] < end:
            hole_start, hole_count = pending[index]
            hole_end = hole_start + hole_count
            if hole_start > cursor:
                result.append((cursor, hole_start - cursor))
            cursor = max(cursor, hole_end)
            index += 1
        if cursor < end:
            result.append((cursor, end - cursor))
    return merge_runs(result)


def complement_runs(
    runs: Sequence[tuple[int, int]],
    total: int,
) -> tuple[tuple[int, int], ...]:
    """Return the maximal runs of ``[0,total)`` not covered by *runs*."""

    result: list[tuple[int, int]] = []
    cursor = 0
    for start, count in runs:
        if start < cursor:
            raise ValueError("runs must be disjoint and ascending")
        if start > cursor:
            result.append((cursor, start - cursor))
        cursor = start + count
    if cursor > total:
        raise ValueError("runs exceed the source member domain")
    if cursor < total:
        result.append((cursor, total - cursor))
    return tuple(result)


def _interval_rows(entry: RangeEntry) -> dict[str, Any]:
    normalized = entry.normalized
    value_type = normalized.value_type
    intervals = [
        [
            encode_atom(normalized.value(start), value_type),
            encode_atom(normalized.value(start + count - 1), value_type),
            encode_atom(normalized.step, value_type),
            count,
        ]
        for start, count in entry.runs
    ]
    return {
        "source_entry_ref": normalized.source_entry_ref,
        "intervals": intervals,
        "member_count": entry.member_count,
    }


def analytic_object(relation: AnalyticRelation) -> dict[str, Any]:
    """Build the closed four-member analytic arm for *relation*."""

    return {
        "literal_member_rows": relation.literal_rows,
        "range_interval_rows": [
            _interval_rows(entry) for entry in relation.range_entries
        ],
        "representation": ANALYTIC_REPRESENTATION,
        "total_member_count": relation.member_count,
    }


def explicit_array(relation: AnalyticRelation) -> list[dict[str, Any]]:
    """Build the inherited explicit member array for *relation*."""

    return list(relation.iter_rows())


def serialize_relation(relation: AnalyticRelation) -> Any:
    """Return the one canonical production arm fixed by the 4,096 threshold."""

    if relation.member_count <= MEMBER_THRESHOLD:
        return explicit_array(relation)
    return analytic_object(relation)


def member_domain_digest(relation: AnalyticRelation) -> tuple[int, str]:
    """Return the complete logical member array's byte count and SHA-256.

    The relation is never materialized: §22.2.4's byte stream is fed one
    member object at a time, so an analytic arm and its explicit equivalent
    agree by construction rather than by comparison.
    """

    return canonical_stream_digest(LazyArray(relation.iter_rows))


def expand_intervals(
    normalized: NormalizedRange,
    intervals: Sequence[Sequence[Any]],
) -> Iterator[tuple[int, Fraction]]:
    """Yield ``(source_member_index, scalar)`` for one validated interval row."""

    value_type = normalized.value_type
    for interval in intervals:
        lower = decode_atom(interval[0], value_type)
        step = decode_atom(interval[2], value_type)
        count = interval[3]
        for offset in range(count):
            scalar = lower + offset * step
            yield normalized.index(scalar), scalar


def validate_analytic_object(
    value: Any,
    normalized_ranges: Sequence[NormalizedRange],
    *,
    expected_literal_count: int | None = None,
) -> dict[str, Any]:
    """Validate one analytic arm before any semantic member digest exists.

    Every §22.2.1 and §22.2.2 equation is checked here — closed keyset,
    integer-typed counts, atom grammar, exact bound arithmetic, source
    membership, unique maximal runs, and the count identities — so a lossy,
    ambiguous, type-invalid, or count-inconsistent encoding is rejected before
    it can be expanded or hashed.
    """

    if not isinstance(value, dict):
        raise ValueError("analytic arm must be a JSON object")
    if tuple(sorted(value)) != tuple(sorted(ANALYTIC_KEYS)):
        raise ValueError(f"analytic keyset mismatch: {sorted(value)}")
    if value["representation"] != ANALYTIC_REPRESENTATION:
        raise ValueError("unknown analytic representation tag")
    total = value["total_member_count"]
    if not is_json_integer(total) or total < 0:
        raise ValueError("total_member_count must be a nonnegative integer")

    literal_rows = value["literal_member_rows"]
    if not isinstance(literal_rows, list) or any(
        not isinstance(row, dict) for row in literal_rows
    ):
        raise ValueError("literal_member_rows must be complete member rows")
    if (
        expected_literal_count is not None
        and len(literal_rows) != expected_literal_count
    ):
        raise ValueError("literal_member_rows count mismatch")

    interval_rows = value["range_interval_rows"]
    if not isinstance(interval_rows, list):
        raise ValueError("range_interval_rows must be an array")
    if len(interval_rows) != len(normalized_ranges):
        raise ValueError("range_interval_rows must cover every range entry")

    running = len(literal_rows)
    resolved: list[tuple[NormalizedRange, tuple[tuple[int, int], ...]]] = []
    for row, normalized in zip(interval_rows, normalized_ranges, strict=True):
        if not isinstance(row, dict):
            raise ValueError("range interval row must be an object")
        if tuple(sorted(row)) != tuple(sorted(RANGE_INTERVAL_ROW_KEYS)):
            raise ValueError(f"interval row keyset mismatch: {sorted(row)}")
        if row["source_entry_ref"] != normalized.source_entry_ref:
            raise ValueError("interval row reference resolves out of order")
        member_count = row["member_count"]
        if not is_json_integer(member_count) or member_count < 0:
            raise ValueError("interval member_count must be an integer")
        intervals = row["intervals"]
        if not isinstance(intervals, list):
            raise ValueError("intervals must be an array")

        displayed: list[tuple[int, int]] = []
        counted = 0
        for interval in intervals:
            if not isinstance(interval, list) or len(interval) != 4:
                raise ValueError("interval must be a four-position array")
            count = interval[3]
            if not is_json_integer(count) or count < 1:
                raise ValueError("interval member_count must be positive")
            lower = decode_atom(interval[0], normalized.value_type)
            upper = decode_atom(interval[1], normalized.value_type)
            step = decode_atom(interval[2], normalized.value_type)
            if step != normalized.step:
                raise ValueError("interval step must equal the source step")
            if upper != lower + (count - 1) * step:
                raise ValueError("interval bound arithmetic is inconsistent")
            first = normalized.index(lower)
            if normalized.index(upper) != first + count - 1:
                raise ValueError("interval members are not consecutive")
            displayed.append((first, count))
            counted += count
        if counted != member_count:
            raise ValueError("interval counts disagree with member_count")
        previous_end: int | None = None
        for first, count in displayed:
            if previous_end is not None and first <= previous_end:
                raise ValueError("intervals are not the unique maximal runs")
            previous_end = first + count
        resolved.append((normalized, tuple(displayed)))
        running += member_count

    if running != total:
        raise ValueError("member counts do not sum to total_member_count")
    return {
        "total_member_count": total,
        "literal_member_row_count": len(literal_rows),
        "resolved_range_runs": resolved,
    }
