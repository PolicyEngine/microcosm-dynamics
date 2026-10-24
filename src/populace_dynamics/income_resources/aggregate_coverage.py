"""Pinned public-pension tables and Section 218 cited references.

Invariants:

* Every entry point verifies the registered byte size and SHA-256 before
  examining its payload.
* Reference prose remains cited text. State authority lists are never
  interpreted as observed coverage, membership or a coverage probability.
* Table columns require explicit units and published row labels. Missing
  or suppressed cells remain missing, with their source flags.
* Expanded HTML headers retain their full hierarchy, and duplicate cell
  identities are refused. Parser errors and representations disclose
  structure only.

The captured RS 01505 sections concern administrative procedures. The
state authority lists and mandatory-coverage rules are in the State and
Local Coverage Handbook's SL sections. These references support CE1 and
provide CE3 context; they do not supply state noncoverage observations.
The Census parser accepts explicitly mapped CSV, API JSON or HTML; a
blocked Census source does not create a registry table or invented data.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .aggregate_tables import (
    AggregateCell,
    TableSpec,
    TableStructureError,
    expand_html_table,
    load_registry,
    normalized_text,
    parse_html,
    parse_number,
    read_verified,
    verify_payload,
)


@dataclass(frozen=True)
class ReferenceText:
    """One cited subsection; its prose is excluded from representations."""

    table: str
    section: str
    citation: str
    text: str = field(repr=False)


def parse_reference(
    spec: TableSpec, payload: bytes
) -> tuple[ReferenceText, ...]:
    """Extract POMS subsection text without treating prose as table cells."""
    verify_payload(spec, payload)
    if spec.record_kind != "reference":
        raise TableStructureError("Reference parser requires reference entry")
    document = parse_html(payload)
    bodies = [el for el in document.iter("div") if el.get("class") == "poms"]
    if len(bodies) != 1:
        raise TableStructureError("Expected one POMS reference body")
    body = bodies[0]
    titles = [normalized_text(el) for el in body.iter("h1")]
    if titles != [spec.selector["title"]]:
        raise TableStructureError("POMS reference title differs")
    sections = [el for el in body if el.get("class") == "poms-subsection1"]
    result = []
    for section in sections:
        headings = [normalized_text(el) for el in section.iter("h2")]
        texts = [
            el for el in section if el.get("class") == "poms-subsection1-body"
        ]
        if len(headings) != 1 or len(texts) != 1:
            raise TableStructureError("POMS subsection structure differs")
        result.append(
            ReferenceText(
                spec.identifier,
                headings[0],
                f"{spec.url} ({headings[0]})",
                normalized_text(texts[0]),
            )
        )
    if not sections:
        result.append(
            ReferenceText(
                spec.identifier, titles[0], spec.url, normalized_text(body)
            )
        )
    expected = spec.selector.get("sections")
    if expected is not None and [row.section for row in result] != expected:
        raise TableStructureError("POMS reference section labels differ")
    if not all(row.text for row in result):
        raise TableStructureError("Empty POMS cited text")
    return tuple(result)


def read_reference(
    table: str | TableSpec, root: Path | None = None
) -> tuple[ReferenceText, ...]:
    """Read and verify a registered reference, then return cited text."""
    spec = load_registry(root)[table] if isinstance(table, str) else table
    return parse_reference(spec, read_verified(spec, root))


def _html_cells(spec: TableSpec, payload: bytes) -> tuple[AggregateCell, ...]:
    document = parse_html(payload)
    tables = [
        el
        for el in document.iter("table")
        if el.get("id") == spec.selector["table_id"]
    ]
    if len(tables) != 1:
        raise TableStructureError("Expected one identified coverage table")
    grid = expand_html_table(tables[0])
    header_rows = spec.selector["header_rows"]
    row_columns = spec.selector.get("row_columns", 1)
    if (
        not grid
        or not 1 <= header_rows < len(grid)
        or not 1 <= row_columns < len(grid[0])
    ):
        raise TableStructureError("Invalid coverage table dimensions")
    labels = []
    header_flags = []
    for column in range(row_columns, len(grid[0])):
        parts = []
        for row in grid[:header_rows]:
            label = row[column].text
            if label and (not parts or parts[-1] != label):
                parts.append(label)
        labels.append(" | ".join(parts))
        header_flags.append(
            tuple(
                dict.fromkeys(
                    flag
                    for row in grid[:header_rows]
                    for flag in row[column].flags
                )
            )
        )
    if not all(labels) or len(set(labels)) != len(labels):
        raise TableStructureError("Missing or duplicate coverage headers")
    units = spec.selector.get("column_units", [spec.units[0]] * len(labels))
    if len(units) != len(labels) or any(u not in spec.units for u in units):
        raise TableStructureError("Coverage units differ from registry")
    year = spec.selector.get("year")
    if year is not None and year not in spec.years:
        raise TableStructureError("Coverage year differs from registry")
    cells = []
    seen = set()
    for row in grid[header_rows:]:
        if not any(cell.text for cell in row):
            continue
        key = " | ".join(cell.text for cell in row[:row_columns] if cell.text)
        if not key:
            raise TableStructureError("Missing coverage row label")
        row_flags = tuple(
            flag for token in row[:row_columns] for flag in token.flags
        )
        for offset, (label, unit) in enumerate(
            zip(labels, units, strict=True)
        ):
            identity = key, label, year
            if identity in seen:
                raise TableStructureError("Duplicate coverage cell identity")
            seen.add(identity)
            token = row[row_columns + offset]
            number = parse_number(token.text)
            cells.append(
                AggregateCell(
                    spec.identifier,
                    key,
                    label,
                    year,
                    unit,
                    number.value,
                    tuple(
                        dict.fromkeys(
                            header_flags[offset]
                            + row_flags
                            + token.flags
                            + number.footnote_flags
                        )
                    ),
                )
            )
    if not cells:
        raise TableStructureError("No coverage table cells")
    return tuple(cells)


def parse_coverage(
    spec: TableSpec, payload: bytes
) -> tuple[AggregateCell, ...]:
    """Parse an explicitly identified numeric coverage table, if supplied."""
    verify_payload(spec, payload)
    if spec.record_kind != "table":
        raise TableStructureError(
            "Cited coverage prose is not a numeric table"
        )
    return _html_cells(spec, payload)


def parse_census(spec: TableSpec, payload: bytes) -> tuple[AggregateCell, ...]:
    """Parse explicitly mapped public-pension CSV, API JSON or HTML cells."""
    verify_payload(spec, payload)
    if spec.record_kind != "table":
        raise TableStructureError("Census parser requires table entry")
    format_name = spec.selector["format"]
    if format_name == "html":
        return _html_cells(spec, payload)
    try:
        if format_name == "csv":
            rows = list(csv.reader(io.StringIO(payload.decode("utf-8-sig"))))
        elif format_name == "json":
            rows = json.loads(payload)
        else:
            raise TableStructureError("Unsupported Census capture format")
    except (UnicodeError, json.JSONDecodeError, csv.Error):
        raise TableStructureError("Unreadable Census table payload") from None
    if not isinstance(rows, list) or len(rows) < 2:
        raise TableStructureError("Census table lacks headers or rows")
    header = rows[0]
    if (
        not isinstance(header, list)
        or not all(isinstance(label, str) for label in header)
        or len(set(header)) != len(header)
    ):
        raise TableStructureError("Invalid Census header schema")
    mapping = spec.selector["data_columns"]
    fields = spec.selector["row_fields"]
    if not mapping or not fields:
        raise TableStructureError("Census mapping lacks rows or columns")
    year_field = spec.selector.get("year_field")
    required = fields + [column["field"] for column in mapping]
    if year_field:
        required.append(year_field)
    if any(field not in header for field in required):
        raise TableStructureError("Census mapped field absent")
    if any(column["unit"] not in spec.units for column in mapping):
        raise TableStructureError("Census units differ from registry")
    cells = []
    seen = set()
    for row in rows[1:]:
        if not isinstance(row, list) or len(row) != len(header):
            raise TableStructureError("Census row width differs from header")
        record = dict(zip(header, row, strict=True))
        labels = [
            "" if record[field] is None else str(record[field]).strip()
            for field in fields
        ]
        if not all(labels):
            raise TableStructureError("Missing Census geography label")
        key = " | ".join(labels)
        raw_year = record[year_field] if year_field else spec.selector["year"]
        if not isinstance(raw_year, (str, int)) or not re.fullmatch(
            r"\d{4}", str(raw_year).strip()
        ):
            raise TableStructureError("Invalid Census reference year")
        year = int(raw_year)
        if year not in spec.years:
            raise TableStructureError("Census year differs from registry")
        for column in mapping:
            identity = key, column["label"], year
            if identity in seen:
                raise TableStructureError("Duplicate Census cell identity")
            seen.add(identity)
            raw = record[column["field"]]
            number = parse_number("" if raw is None else str(raw))
            cells.append(
                AggregateCell(
                    spec.identifier,
                    key,
                    column["label"],
                    year,
                    column["unit"],
                    number.value,
                    number.footnote_flags,
                )
            )
    return tuple(cells)
