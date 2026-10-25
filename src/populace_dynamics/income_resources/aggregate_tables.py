"""Pinned aggregate sources for income and resources, D4.

Invariants
----------
* Every public reader verifies SHA-256 and byte size before parsing.
* One cell retains its table, row, column, year, unit and footnote flags;
  missing and suppressed cells are explicit ``None``, never zero.
* Numeric decoration (separators and footnote markers) changes neither
  magnitude nor sign. Unrecognized numeric text is refused without echoing it.
* HTML merged headers expand to a rectangular grid without losing flags.
* Parsing never prints or logs values. Cell representations omit values.
* Registry roles describe intended use, never admission by an empirical gate.

Registry fragments live with the captures so part 2 can add sources and
parser dispatch entries without changing existing source identities. Annual
Supplement 4.B uses the existing vintage-1 capture without fetching it again.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
CAPTURE_DIRECTORY = Path("data/external/snapshots/income_resources_d4_v1")


@dataclass(frozen=True)
class ParsedNumber:
    """A decimal or an explicit missing marker, with source flags."""

    value: Decimal | None = field(repr=False)
    footnote_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class AggregateCell:
    """One published cell; representations disclose structure only."""

    table: str
    row_key: str
    column_key: str
    year: int | None
    unit: str
    value: Decimal | None = field(repr=False)
    footnote_flags: tuple[str, ...] = ()
    effective_from: str | None = None
    effective_to: str | None = None


@dataclass(frozen=True)
class CellToken:
    """An HTML cell after superscript extraction and span expansion."""

    text: str = field(repr=False)
    flags: tuple[str, ...] = ()
    is_header: bool = False


@dataclass(frozen=True)
class TableSpec:
    """Identity, coverage and intended role of one captured table."""

    identifier: str
    publisher: str
    edition: str
    url: str
    capture_file: str
    sha256: str
    byte_size: int
    retrieved_at: str
    units: tuple[str, ...]
    years: tuple[int, ...]
    geography: tuple[str, ...]
    parser: str
    role: str
    selector: dict[str, Any] = field(default_factory=dict)
    record_kind: str = "table"


class CaptureMismatchError(ValueError):
    """Capture bytes differ from the registered identity."""


class TableStructureError(ValueError):
    """A source no longer has the adjudicated structure."""


_MISSING = {
    "": "missing",
    "...": "not_available",
    "..": "not_available",
    "…": "not_available",
    "—": "not_available",
    "–": "not_available",
    "-": "not_available",
    "--": "not_available",
    "n/a": "not_available",
    "na": "not_available",
    "none": "not_available",
    "nd": "not_available",
    "n.a.": "not_available",
    "(na)": "not_available",
    "(x)": "not_applicable",
    "(d)": "suppressed",
    "d": "suppressed",
    "s": "suppressed",
    "(s)": "suppressed",
    "*": "suppressed",
    "**": "suppressed",
    "(z)": "rounded_nonzero",
}


def parse_number(raw: str) -> ParsedNumber:
    """Parse publisher numeric tokens without treating missing as zero.

    Letter/symbol suffixes and bracketed footnote numbers are retained as
    flags. Numeric superscripts must be extracted from HTML before this call;
    a trailing ordinary digit always remains part of the numeric value.
    """
    token = raw.strip().replace("−", "-")
    compact = re.sub(r"\s+", "", token).lower()
    if compact in _MISSING:
        return ParsedNumber(None, (_MISSING[compact],))
    flags = []
    while match := re.search(
        r"\[([^\]]+)\]$|([a-zA-Z*†‡¹²³⁴⁵⁶⁷⁸⁹⁰]+)$"
        r"|(?<=\d)\s*\(([a-zA-Z0-9]+)\)$",
        token,
    ):
        if re.sub(r"\s+", "", token).lower() in _MISSING:
            break
        if match.start() == 0:
            raise TableStructureError("Unrecognized numeric cell")
        flags.append(next(group for group in match.groups() if group))
        token = token[: match.start()].strip()
    compact = re.sub(r"\s+", "", token).lower()
    if compact in _MISSING:
        return ParsedNumber(None, (_MISSING[compact], *reversed(flags)))
    if token.endswith("%"):
        token = token[:-1].strip()
    negative = token.startswith("(") and token.endswith(")")
    if negative:
        token = token[1:-1].strip()
    token = re.sub(r"^([+-]?)\s*\$\s*", r"\1", token).strip()
    if negative and token.startswith(("-", "+")):
        raise TableStructureError("Unrecognized numeric cell")
    # Commas and spaces may separate groups, but malformed commas are refused.
    token = re.sub(r"[\s\u00a0\u202f]", "", token)
    if not re.fullmatch(
        r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)", token
    ):
        raise TableStructureError("Unrecognized numeric cell")
    try:
        value = Decimal(token.replace(",", ""))
    except InvalidOperation:
        raise TableStructureError("Unrecognized numeric cell") from None
    if negative:
        value = -value
    return ParsedNumber(value, tuple(reversed(flags)))


# Start tags that close an open paragraph in the WHATWG HTML parsing rules
# ("in body" insertion mode), with table as in standards mode.
PARAGRAPH_CLOSERS = frozenset(
    """address article aside blockquote center dd details dialog dir div dl
    dt fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header
    hgroup hr li listing main menu nav ol p plaintext pre search section
    summary table ul xmp""".split()
)


class _HTMLTree(HTMLParser):
    """Build a tolerant stdlib tree; publishers' void tags never nest.

    Paragraphs, headings, cells and rows end where the WHATWG parsing rules
    end them, even when the source omits the end tag, so a paragraph never
    holds the headings and tables that follow it. ``table`` closes an open
    paragraph as in standards mode; every pinned HTML capture declares a
    doctype. Inline end tags misnested across an open paragraph, which HTML
    resolves with its adoption agency rules, are not modelled: here they
    close at the matching element.
    """

    _VOID = frozenset(
        "area base br col embed hr img input link meta param source track wbr".split()
    )
    _HEADINGS = frozenset("h1 h2 h3 h4 h5 h6".split())
    # A paragraph is in button scope unless one of these encloses it.
    _BUTTON_SCOPE = frozenset(
        "applet button caption html marquee object select table td template th".split()
    )
    _TABLE_SECTIONS = frozenset("table thead tbody tfoot".split())

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = ET.Element("document")
        self.stack = [self.root]

    def _close_paragraph(self) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == "p":
                del self.stack[i:]
                return
            if self.stack[i].tag in self._BUTTON_SCOPE:
                return

    def _close_open(self, closes: set[str], bounds: frozenset[str]) -> None:
        """Pop the innermost open ``closes`` element below ``bounds``."""
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag in bounds:
                return
            if self.stack[i].tag in closes:
                del self.stack[i:]
                return

    def handle_starttag(self, tag, attrs):
        if tag in PARAGRAPH_CLOSERS:
            self._close_paragraph()
        if tag in self._HEADINGS and self.stack[-1].tag in self._HEADINGS:
            self.stack.pop()
        if tag in {"td", "th"}:
            # A new cell closes the open one, with anything left open in it.
            self._close_open({"td", "th"}, self._TABLE_SECTIONS | {"tr"})
        if tag == "tr":
            self._close_open({"td", "th", "tr"}, self._TABLE_SECTIONS)
            self._close_open({"tr"}, self._TABLE_SECTIONS)
        el = ET.SubElement(self.stack[-1], tag, {k: v or "" for k, v in attrs})
        if tag not in self._VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        parent = self.stack[-1]
        if len(parent):
            parent[-1].tail = (parent[-1].tail or "") + data
        else:
            parent.text = (parent.text or "") + data


def parse_html(payload: bytes | str) -> ET.Element:
    """Build a tolerant HTML tree without fetching external resources."""
    parser = _HTMLTree()
    parser.feed(
        payload.decode("utf-8", errors="replace")
        if isinstance(payload, bytes)
        else payload
    )
    return parser.root


def normalized_text(element: ET.Element) -> str:
    """Normalize whitespace in a label or cited passage."""
    return " ".join(" ".join(element.itertext()).split())


def _cell_token(element: ET.Element) -> CellToken:
    flags = []

    def visit(el):
        parts = [el.text or ""]
        for child in el:
            if child.tag == "sup" or (
                child.tag == "a" and "fn" in child.get("href", "").lower()
            ):
                flag = normalized_text(child)
                if flag:
                    flags.append(flag)
            else:
                parts.append(visit(child))
            parts.append(child.tail or "")
        return " ".join(parts)

    text = " ".join(visit(element).split())
    return CellToken(text, tuple(flags), element.tag == "th")


def expand_html_table(table: ET.Element) -> tuple[tuple[CellToken, ...], ...]:
    """Expand row/column spans, retaining header and footnote identity."""
    grid: dict[tuple[int, int], CellToken] = {}
    rows = list(table.iter("tr"))
    width = 0
    for ri, row in enumerate(rows):
        ci = 0
        for el in row:
            if el.tag not in {"th", "td"}:
                continue
            while (ri, ci) in grid:
                ci += 1
            try:
                rowspan = int(el.get("rowspan", "1"))
                colspan = int(el.get("colspan", "1"))
            except ValueError:
                raise TableStructureError("Invalid HTML span") from None
            if not (1 <= rowspan <= 1000 and 1 <= colspan <= 1000):
                raise TableStructureError("Invalid HTML span")
            token = _cell_token(el)
            for rr in range(ri, ri + rowspan):
                for cc in range(ci, ci + colspan):
                    if (rr, cc) in grid:
                        raise TableStructureError("Overlapping HTML spans")
                    grid[rr, cc] = token
            ci += colspan
            width = max(width, ci)
    if any(ri >= len(rows) for ri, _ in grid):
        raise TableStructureError("HTML rowspan exceeds table")
    empty = CellToken("")
    return tuple(
        tuple(grid.get((ri, ci), empty) for ci in range(width))
        for ri in range(len(rows))
    )


def load_registry(root: Path | None = None) -> dict[str, TableSpec]:
    """Load additive registry fragments; duplicate identifiers are refused."""
    directory = (root or ROOT) / CAPTURE_DIRECTORY
    registry = {}
    for path in sorted(directory.glob("*_registry.json")):
        for entry in json.loads(path.read_text()):
            for key in ("units", "years", "geography"):
                entry[key] = tuple(entry[key])
            spec = TableSpec(**entry)
            if spec.identifier in registry:
                raise TableStructureError("Duplicate registry identifier")
            registry[spec.identifier] = spec
    return registry


def read_verified(spec: TableSpec, root: Path | None = None) -> bytes:
    """Read only registered bytes, checking hash and length before parsing."""
    root = (root or ROOT).resolve()
    path = (root / spec.capture_file).resolve()
    if not path.is_relative_to(root):
        raise CaptureMismatchError(
            f"Capture path escapes root: {spec.identifier}"
        )
    raw = path.read_bytes()
    verify_payload(spec, raw)
    return raw


def verify_payload(spec: TableSpec, payload: bytes) -> None:
    """Refuse unregistered bytes even when a parser is called directly."""
    if (
        len(payload) != spec.byte_size
        or hashlib.sha256(payload).hexdigest() != spec.sha256
    ):
        raise CaptureMismatchError(
            f"Capture identity mismatch: {spec.identifier}"
        )


def parse_table(
    table: str | TableSpec, root: Path | None = None
) -> tuple[AggregateCell, ...]:
    """Verify capture identity then dispatch one registered table parser."""
    spec = load_registry(root)[table] if isinstance(table, str) else table
    payload = read_verified(spec, root)
    if spec.record_kind != "table":
        raise TableStructureError(
            f"Reference is not a numeric table: {spec.identifier}"
        )
    if spec.parser == "ssa_4b":
        return parse_ssa_4b(spec, payload)
    if spec.parser == "poms":
        from .aggregate_poms import parse_poms

        return parse_poms(spec, payload)
    if spec.parser in {"coverage", "census"}:
        from . import aggregate_coverage

        return getattr(aggregate_coverage, f"parse_{spec.parser}")(
            spec, payload
        )
    if spec.parser in {"fed", "dol", "irs"}:
        from . import aggregate_pensions

        return getattr(aggregate_pensions, f"parse_{spec.parser}")(
            spec, payload
        )
    raise TableStructureError(f"Unregistered parser: {spec.identifier}")


def parse_ssa_4b(spec: TableSpec, payload: bytes) -> tuple[AggregateCell, ...]:
    """Parse four Supplement 4.B tables with hierarchical column labels."""
    verify_payload(spec, payload)
    document = parse_html(payload)
    section = next(
        (el for el in document.iter() if el.get("id") == spec.selector["id"]),
        None,
    )
    if section is None:
        raise TableStructureError(f"Missing HTML section: {spec.identifier}")
    table = section.find(".//table")
    if table is None:
        raise TableStructureError(f"Missing HTML table: {spec.identifier}")
    head = table.find("thead")
    body = table.find("tbody")
    if head is None or body is None:
        raise TableStructureError(f"Missing table sections: {spec.identifier}")
    header_grid = expand_html_table(head)
    columns = []
    column_flags = []
    for ci in range(1, len(header_grid[0])):
        tokens = [row[ci] for row in header_grid]
        labels = list(dict.fromkeys(t.text for t in tokens if t.text))
        columns.append(" | ".join(labels))
        column_flags.append(
            tuple(dict.fromkeys(f for t in tokens for f in t.flags))
        )
    units = spec.selector["column_units"]
    if (
        len(columns) != len(units)
        or len(set(columns)) != len(columns)
        or any(unit not in spec.units for unit in units)
    ):
        raise TableStructureError(f"Column layout mismatch: {spec.identifier}")
    cells = []
    for row in expand_html_table(body):
        if len(row) != len(columns) + 1:
            raise TableStructureError(f"Row width mismatch: {spec.identifier}")
        key = row[0].text
        year = int(key) if re.fullmatch(r"\d{4}", key) else spec.years[0]
        if year not in spec.years:
            raise TableStructureError(
                f"Year outside registry: {spec.identifier}"
            )
        for ci, token in enumerate(row[1:]):
            number = parse_number(token.text)
            flags = tuple(
                dict.fromkeys(
                    row[0].flags
                    + column_flags[ci]
                    + token.flags
                    + number.footnote_flags
                )
            )
            cells.append(
                AggregateCell(
                    spec.identifier,
                    key,
                    columns[ci],
                    year,
                    units[ci],
                    number.value,
                    flags,
                )
            )
    keys = [(cell.row_key, cell.column_key, cell.year) for cell in cells]
    if len(keys) != len(set(keys)):
        raise TableStructureError(
            f"Duplicate cell identity: {spec.identifier}"
        )
    return tuple(cells)
