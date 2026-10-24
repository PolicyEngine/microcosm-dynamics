"""POMS SI 01415 federally administered supplement payment tables.

Invariants
----------
* Both the public dispatcher and this parser verify the pinned bytes.
* A payment table retains its state, claimant type, Federal living-arrangement
  code, State supplement code, category and original numeric column labels.
  Blank code cells continue the preceding code; categories never continue.
* Payment effective dates and the section's revision dates remain distinct.
  Conflicting payment dates remain named alternatives, with no chosen date.
* Missing and malformed amounts remain explicit missing cells. Source
  footnotes survive. Stacked subrows retain each separately published amount.
* Published component/total discrepancies are flagged, never corrected.
* No parser prints or logs source amounts, and no amount is reconstructed.

Only federally administered optional supplement tables are represented.
State-administered programs described in prose are cited by the capture but
are not silently represented as a complete state parameter series. The
State OS code identifies the living arrangement defined in the section's
associated code-definition table (``definitions_table_index`` in selectors).
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any
from xml.etree import ElementTree as ET

from .aggregate_tables import (
    AggregateCell,
    CellToken,
    TableSpec,
    TableStructureError,
    _cell_token,
    expand_html_table,
    normalized_text,
    parse_html,
    parse_number,
    verify_payload,
)

_STATES = (
    "California",
    "Delaware",
    "District of Columbia",
    "Hawaii",
    "Iowa",
    "Massachusetts",
    "Michigan",
    "Montana",
    "Nevada",
    "New Jersey",
    "New York",
    "Pennsylvania",
    "Rhode Island",
    "Utah",
    "Vermont",
    "Washington",
    "Wisconsin",
)
_MONTHS = (
    "January February March April May June July August September October "
    "November December"
).split()
_DATE = re.compile(
    r"\b(?:"
    + "|".join(_MONTHS)
    + r")\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{2,4}\b",
    re.IGNORECASE,
)
_BLOCKS = frozenset({"p", "h1", "h2", "h3", "h4", "h5", "h6"})


def _blank(text: str) -> str:
    return text.replace("\u200b", "").replace("\ufeff", "").strip()


def _date_string(text: str) -> str:
    text = re.sub(r"\s*/\s*", "/", text).replace(",", "")
    for fmt in ("%B %d %Y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise TableStructureError("Unrecognized POMS effective date")


@lru_cache(maxsize=32)
def _document(payload: bytes) -> tuple[ET.Element, tuple[ET.Element, ...]]:
    document = parse_html(payload)
    return document, tuple(document.iter("table"))


def describe_poms_tables(payload: bytes) -> tuple[dict[str, Any], ...]:
    """Return structural selectors for payment tables, without amounts.

    The selectors retain the original chart effective-date text and the
    section revision range. More than one chart date is an explicit open
    alternative; it does not silently select either date.
    """
    document, tables = _document(payload)
    section_text = normalized_text(document)
    revision = re.search(
        r"Effective Dates:\s*(\d{2}/\d{2}/\d{4})\s*-\s*"
        r"(Present|\d{2}/\d{2}/\d{4})",
        section_text,
    )
    revision_start = _date_string(revision[1]) if revision else None
    revision_end = (
        _date_string(revision[2])
        if revision and revision[2] != "Present"
        else None
    )
    state = None
    claimant = None
    effective_text = ""
    dates: tuple[str, ...] = ()
    definitions = None
    table_indexes = {id(table): i for i, table in enumerate(tables)}
    contexts: list[dict[str, Any]] = []

    def walk(element: ET.Element) -> None:
        nonlocal state, claimant, effective_text, dates, definitions
        if element.tag == "table":
            index = table_indexes[id(element)]
            grid = expand_html_table(element)
            if not grid:
                return
            first = tuple(_blank(c.text) for c in grid[0])
            if any(
                tuple(_blank(c.text) for c in row) == ("Code", "Definition")
                for row in grid[:3]
            ):
                definitions = index
            if len(first) >= 5 and first[0] == "Federal Code":
                if state is None or claimant is None:
                    raise TableStructureError(
                        f"POMS payment table {index} lacks state or claimant context"
                    )
                contexts.append(
                    {
                        "table_index": index,
                        "state": state,
                        "claimant_type": claimant,
                        "header_labels": list(first),
                        "definitions_table_index": definitions,
                        "effective_from": (
                            dates[0]
                            if len(dates) == 1
                            or len(dates) == 2
                            and re.search(
                                r"effective from .+ to ", effective_text, re.I
                            )
                            else None
                        ),
                        "effective_to": (
                            dates[1]
                            if len(dates) == 2
                            and re.search(
                                r"effective from .+ to ", effective_text, re.I
                            )
                            else None
                        ),
                        "parameter_effective_date_text": effective_text,
                        "date_options": (
                            {
                                f"source_date_{i + 1}": value
                                for i, value in enumerate(dates)
                            }
                            if len(dates) > 1
                            and not re.search(
                                r"effective from .+ to ", effective_text, re.I
                            )
                            else {"not_stated": None} if not dates else {}
                        ),
                        "section_effective_from": revision_start,
                        "section_effective_to": revision_end,
                    }
                )
            return
        if element.tag in _BLOCKS:
            text = normalized_text(element)
            for name in _STATES:
                if re.fullmatch(
                    r"(?:[A-Z]\.\s*)?"
                    r"(?:Description of supplements(?:\s+for\s+(?:the\s+)?|\s*-\s*)"
                    r"|Procedure\s*-\s*)?" + re.escape(name),
                    text,
                    re.IGNORECASE,
                ):
                    if state != name:
                        state = name
                        claimant = None
                        effective_text = ""
                        dates = ()
                        definitions = None
                    break
            for name in _STATES:
                if re.match(re.escape(name) + r"\s+Effective\b", text, re.I):
                    if state != name:
                        state, claimant = name, None
                    break
            if (
                "effective" in text.lower()
                and "Effective Dates:" not in text
                and len(text) < 400
                and (
                    re.search(r"payments? levels?", text, re.I)
                    or text.lower().startswith("effective ")
                    or any(
                        re.match(
                            re.escape(name) + r"\s+effective\b", text, re.I
                        )
                        for name in _STATES
                    )
                )
            ):
                effective_text = text
                dates = tuple(
                    dict.fromkeys(
                        _date_string(m[0]) for m in _DATE.finditer(text)
                    )
                )
            if len(text) < 250:
                match = re.search(
                    r"(?:^|\s)(Individual|Recipient|Couple)"
                    r"(?:\s+payments?)?(?:\s+levels)?"
                    r"(?:\s+(?:for|or)\s+.+)?$",
                    text,
                    re.IGNORECASE,
                )
                if match:
                    claimant = (
                        "couple"
                        if match[1].lower() == "couple"
                        else "individual"
                    )
        for child in element:
            walk(child)

    walk(document)
    return tuple(contexts)


def _payment_rows(table: ET.Element) -> tuple[tuple[CellToken, ...], ...]:
    """Split publisher-stacked subrows while reusing the shared span logic."""
    clone = deepcopy(table)
    originals = [c for c in table.iter() if c.tag in {"td", "th"}]
    copied = [c for c in clone.iter() if c.tag in {"td", "th"}]
    lookup = {}
    for index, (original, cell) in enumerate(
        zip(originals, copied, strict=True)
    ):
        key = f"poms-cell-{index}"
        lookup[key] = original
        cell.text = key
        for child in list(cell):
            cell.remove(child)
    rows = []
    for row in expand_html_table(clone):
        elements = [lookup.get(token.text) for token in row]
        tokens = [
            _cell_token(element) if element is not None else CellToken("")
            for element in elements
        ]
        segments = [
            (
                [
                    _cell_token(p)
                    for p in element.findall("p")
                    if _blank(normalized_text(p))
                ]
                if element is not None
                else []
            )
            for element in elements
        ]
        grouped = []
        for element in elements:
            groups: list[list[CellToken]] = []
            group: list[CellToken] = []
            for paragraph in (
                element.findall("p") if element is not None else []
            ):
                if _blank(normalized_text(paragraph)):
                    group.append(_cell_token(paragraph))
                elif group:
                    groups.append(group)
                    group = []
            if group:
                groups.append(group)
            grouped.append(groups)
        # Numeric columns determine the subrow count. A single paragraph in
        # the source remains a single cell even when its punctuation is bad.
        count = max([len(parts) for parts in segments[3:]] or [1])
        if count <= 1:
            rows.append(tuple(tokens))
            continue
        for subrow in range(count):
            result = []
            for column, (token, parts, groups) in enumerate(
                zip(tokens, segments, grouped, strict=True)
            ):
                if len(parts) in {0, 1}:
                    result.append(token)
                elif len(parts) == count:
                    result.append(parts[subrow])
                elif (
                    column == 2
                    and count == 2
                    and len(parts) == 3
                    and parts[0].text.startswith(parts[1].text + " ")
                ):
                    # Washington prints the repeated category prefix and its
                    # second county label in adjacent continuation paragraphs.
                    group = parts[:1] if subrow == 0 else parts[1:]
                    result.append(
                        CellToken(
                            " ".join(p.text for p in group),
                            tuple(
                                dict.fromkeys(
                                    f for p in group for f in p.flags
                                )
                            ),
                            token.is_header,
                        )
                    )
                elif len(groups) == count:
                    group = groups[subrow]
                    result.append(
                        CellToken(
                            " ".join(p.text for p in group),
                            tuple(
                                dict.fromkeys(
                                    f for p in group for f in p.flags
                                )
                            ),
                            token.is_header,
                        )
                    )
                elif len(parts) % count == 0:
                    width = len(parts) // count
                    group = parts[subrow * width : (subrow + 1) * width]
                    result.append(
                        CellToken(
                            " ".join(p.text for p in group),
                            tuple(
                                dict.fromkeys(
                                    f for p in group for f in p.flags
                                )
                            ),
                            token.is_header,
                        )
                    )
                else:
                    raise TableStructureError(
                        "POMS stacked rows do not align: "
                        f"subrows={count}, paragraphs={len(parts)}, groups={len(groups)}"
                    )
            rows.append(tuple(result))
    return tuple(rows)


def poms_living_arrangements(
    spec: TableSpec, payload: bytes
) -> dict[str, str]:
    """Return cited State OS code definitions from the same verified section."""
    verify_payload(spec, payload)
    _, tables = _document(payload)
    index = spec.selector.get("definitions_table_index")
    if index is None:
        raise TableStructureError("POMS definition table is not identified")
    grid = expand_html_table(tables[index])
    header_index = next(
        (
            index
            for index, row in enumerate(grid[:3])
            if tuple(_blank(c.text) for c in row) == ("Code", "Definition")
        ),
        None,
    )
    if header_index is None:
        raise TableStructureError("POMS code definition headers differ")
    definitions = {}
    previous = None
    physical_rows = list(tables[index].iter("tr"))
    for row_index, row in enumerate(
        grid[header_index + 1 :], header_index + 1
    ):
        code = _blank(row[0].text)
        definition = _blank(row[1].text)
        if not code and previous:
            definitions[previous] += " " + definition
            continue
        if (
            code == previous
            and len(
                [
                    cell
                    for cell in physical_rows[row_index]
                    if cell.tag in {"td", "th"}
                ]
            )
            == 1
        ):
            definitions[previous] += " " + definition
            continue
        if not code and not definition:
            continue
        if not code or code in definitions:
            raise TableStructureError(
                "POMS living-arrangement code is blank or repeats"
            )
        definitions[code] = definition
        previous = code
    return definitions


def _is_header_row(row: tuple[CellToken, ...]) -> bool:
    return all(token.is_header for token in row[3:]) or _blank(
        row[3].text
    ) in {
        "FBR",
        "Federal Benefit Rate (FBR)",
    }


def parse_poms(spec: TableSpec, payload: bytes) -> tuple[AggregateCell, ...]:
    """Verify and parse one State/claimant payment chart into typed cells."""
    verify_payload(spec, payload)
    _, tables = _document(payload)
    selector = spec.selector
    try:
        table = tables[selector["table_index"]]
    except (IndexError, KeyError):
        raise TableStructureError("Missing registered POMS table") from None
    grid = expand_html_table(table)
    header = tuple(_blank(c.text) for c in grid[0]) if grid else ()
    if (
        header != tuple(selector["header_labels"])
        or header[0] != "Federal Code"
    ):
        raise TableStructureError("POMS payment headers differ from registry")
    if len(header) < 5 or len(header) > 8:
        raise TableStructureError("Unexpected POMS payment column count")
    effective = selector.get("effective_from")
    alternate_years = {
        date.fromisoformat(value).year
        for value in selector.get("date_options", {}).values()
        if value
    }
    year = (
        date.fromisoformat(effective).year
        if effective
        else (
            next(iter(alternate_years))
            if len(alternate_years) == 1
            else selector.get("nominal_year") if not alternate_years else None
        )
    )
    if year is not None and year not in spec.years:
        raise TableStructureError("POMS chart year is outside registry")
    federal_code = ""
    state_code = ""
    federal_flags = ()
    state_flags = ()
    logical_rows = _payment_rows(table)
    header_rows = [logical_rows[0]] + [
        row for row in logical_rows[1:] if _is_header_row(row)
    ]
    column_labels = [
        " | ".join(
            dict.fromkeys(
                _blank(row[ci].text)
                for row in header_rows
                if _blank(row[ci].text)
            )
        )
        for ci in range(len(header))
    ]
    repeated_labels = {
        label
        for label in column_labels[3:]
        if label and column_labels[3:].count(label) > 1
    }
    for ci in range(3, len(header)):
        if not column_labels[ci]:
            column_labels[ci] = f"Unlabelled amount column {ci + 1}"
        elif column_labels[ci] in repeated_labels:
            column_labels[ci] += f" | source column={ci + 1}"
    column_flags = [
        tuple(
            dict.fromkeys(
                flag for row in header_rows for flag in row[ci].flags
            )
        )
        for ci in range(len(header))
    ]
    output = []
    for ordinal, row in enumerate(logical_rows[1:], start=1):
        if len(row) != len(header):
            raise TableStructureError("POMS payment row width differs")
        if _is_header_row(row):
            continue
        if _blank(row[0].text):
            federal_code = _blank(row[0].text)
            federal_flags = row[0].flags
        else:
            federal_flags = tuple(dict.fromkeys(federal_flags + row[0].flags))
        if _blank(row[1].text):
            state_code = _blank(row[1].text)
            state_flags = row[1].flags
        else:
            state_flags = tuple(dict.fromkeys(state_flags + row[1].flags))
        category = _blank(row[2].text)
        missing_category = not category
        category = category or "<missing>"
        # The ordinal preserves separately published rows with identical labels.
        key = " | ".join(
            (
                selector["state"],
                selector["claimant_type"],
                f"Federal code={federal_code}",
                f"State OS code={state_code}",
                f"Category={category}",
                f"source row={ordinal}",
            )
        )
        row_cells = []
        for ci, token in enumerate(row[3:], start=3):
            raw = _blank(token.text)
            malformed = bool(re.fullmatch(r"\d{1,3}\.\d{3}\.\d{2}", raw))
            # The source prints two decimal points in these cells. Choosing
            # which punctuation to change would invent an amount.
            try:
                parsed = parse_number("") if malformed else parse_number(raw)
            except TableStructureError:
                raise TableStructureError(
                    f"Unrecognized POMS numeric cell at row {ordinal}, "
                    f"column {ci + 1}"
                ) from None
            label = column_labels[ci]
            flags = (
                federal_flags
                + state_flags
                + row[2].flags
                + token.flags
                + tuple(f for flags in column_flags[:3] for f in flags)
                + column_flags[ci]
            )
            flags += parsed.footnote_flags
            if missing_category:
                flags += ("missing_category",)
            if malformed:
                flags += ("source_numeric_punctuation", "unresolved_amount")
            if not header[ci]:
                flags += ("unlabelled_column",)
            if not effective:
                flags += ("ambiguous_effective_date",)
            row_cells.append(
                AggregateCell(
                    table=spec.identifier,
                    row_key=key,
                    column_key=label,
                    year=year,
                    unit="USD per month",
                    value=parsed.value,
                    footnote_flags=tuple(dict.fromkeys(flags)),
                    effective_from=effective,
                    effective_to=selector.get("effective_to"),
                )
            )
        if (
            len(row_cells) == 3
            and "Total Payment Level" in column_labels[-1]
            and all(cell.value is not None for cell in row_cells)
            and abs(
                row_cells[0].value + row_cells[1].value - row_cells[2].value
            )
            > Decimal("0.02")
        ):
            row_cells = [
                replace(
                    cell,
                    footnote_flags=cell.footnote_flags
                    + ("published_identity_discrepancy",),
                )
                for cell in row_cells
            ]
        output.extend(row_cells)
    return tuple(output)
