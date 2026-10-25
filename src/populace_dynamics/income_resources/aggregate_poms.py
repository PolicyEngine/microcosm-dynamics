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
State OS code identifies the living arrangement defined in the State's
code-definition tables (``definitions_table_indexes`` in selectors). A State's
definitions may span more than one physical table; the reader merges them and
refuses a code whose tables define it differently. Definitions come only from
the chart's own State section, and a State named only in a date line, with no
section heading, refuses. Paragraphs and headings end where HTML ends them,
end tag or not, and every block that ends a paragraph, apart from a table or
rule, is read from its own text. So a State heading in a block left open
still names its State, and a list item, section or blockquote reads the same
after a closed heading as inside one left open. A block is read whole and
also line by line, a line being its text between ``br`` tags and the blocks
HTML keeps inside it, without zero-width characters, so a block or ``br``
after a heading's words does not hide its State, claimant or date. Every
line passes the same State guards: a line that dates another State refuses,
a claimant line that names a State other than its section's refuses, since
the heading of the State it names was not read, and a block whose lines head
two States refuses. A heading whose first line names a State other than its
section's, as "New York (NJ)" does in Nevada's section, refuses too. Before
any State heading, the chart refuses instead. A postal code after a State's
name must be that State's, and "Washington, D.C." names the District.
Every definition table of a section precedes its first chart; a definition
table after a chart refuses, because the source does not say which earlier
chart it serves. A jointly published code
("C/H" in a definition table, "A or B" in a chart) names each single code it
lists. A chart code that no definition table defines stays undefined and is
recorded in ``poms_open_questions.json``; no definition is inferred for it.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any
from xml.etree import ElementTree as ET

from .aggregate_tables import (
    PARAGRAPH_CLOSERS,
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
_POSTAL_CODES = dict(
    zip(
        _STATES,
        "CA DE DC HI IA MA MI MT NV NJ NY PA RI UT VT WA WI".split(),
        strict=True,
    )
)
# "Washington, D.C." and "Washington DC" name the District, not the State.
_DISTRICT_ALIAS = r"Washington,?\s+D\.?\s?C\b\.?"
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
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
# Every block that ends a paragraph, apart from a table or rule, is read
# from its own text, so a list item, section or blockquote reads the same
# after a heading as inside one left open, where HTML keeps it.
_BLOCKS = _HEADINGS | (PARAGRAPH_CLOSERS - {"table", "hr"})
# What ends a block's own text. A block other than a heading ends at the
# next block. HTML keeps any other block inside a heading left open, so a
# heading's text runs on through them and ends at a heading or table; a
# table, which HTML also nests in a heading left open, is never heading text.
_TEXT_STOPS = {block: PARAGRAPH_CLOSERS for block in _BLOCKS} | {
    heading: _HEADINGS | {"table"} for heading in _HEADINGS
}


# A br ends a line as a block nested in a heading does.
_LINE_BREAKS = PARAGRAPH_CLOSERS | {"br"}


def _lines(element: ET.Element) -> list[str]:
    """A block's own text, split at a ``br`` and where a block nested in it
    starts or ends, without zero-width characters.

    Within a line, the text of inline elements joins without a separator,
    as HTML renders it, so ``U<span>tah</span>`` reads "Utah"; whitespace in
    the source is collapsed. The text stops at the first block that ends the
    element (``_TEXT_STOPS``). Before that only a heading can hold a nested
    block, so a block other than a heading splits only at a ``br``. The walk
    does not recurse, so deep nesting cannot exhaust the interpreter stack.
    """
    stops = _TEXT_STOPS[element.tag]
    lines: list[list[str]] = [[element.text or ""]]
    walk = [(element, iter(element))]
    while walk:
        node, children = walk[-1]
        child = next(children, None)
        if child is None:
            walk.pop()
            if walk:
                if node.tag in _LINE_BREAKS:
                    lines.append([])
                lines[-1].append(node.tail or "")
            continue
        if child.tag in stops:
            break
        if child.tag in _LINE_BREAKS:
            lines.append([])
        lines[-1].append(child.text or "")
        walk.append((child, iter(child)))
    texts = (" ".join(_blank("".join(line)).split()) for line in lines)
    return [text for text in texts if text]


def _own_text(element: ET.Element) -> str:
    """Normalize a block's own text, up to the first block that ends it.

    When no block or ``br`` nests inside the element, this is its text
    content with whitespace collapsed and zero-width characters removed.
    Unlike ``normalized_text``, which separates every text node, inline
    elements join without a separator. A heading left open is read without
    the next heading or the table the tree nests under it.
    """
    return " ".join(_lines(element))


# What may come before a State's name in its section heading.
_HEADING_PREFIX = (
    r"(?:[A-Z]\.\s*)?"
    r"(?:Description of supplements(?:\s+for\s+(?:the\s+)?|\s*-\s*)"
    r"|Procedure\s*-\s*)?"
)


def _state_name(name: str) -> str:
    """A pattern for a State's name, or for the District, an alias."""
    if name == "District of Columbia":
        return rf"(?:{re.escape(name)}|{_DISTRICT_ALIAS})"
    return re.escape(name)


def _state_reference(name: str) -> str:
    """A pattern for a State's name with its optional postal suffix. The
    2009 and 2010 sections append the code, as in "New Jersey (NJ)"."""
    return _state_name(name) + rf"(?:\s*\({_POSTAL_CODES[name]}\))?"


def _state_heading(name: str, text: str) -> bool:
    return bool(
        re.fullmatch(
            _HEADING_PREFIX + _state_reference(name), text, re.IGNORECASE
        )
    )


def _misnamed_heading(text: str) -> bool:
    """Whether a line has a State heading's shape with a postal code that
    is not that State's, as in "New York (NJ)"."""
    return any(
        re.fullmatch(
            _HEADING_PREFIX + _state_name(name) + r"\s*\([A-Z]{2}\)",
            text,
            re.IGNORECASE,
        )
        and not _state_heading(name, text)
        for name in _STATES
    )


def _state_date_line(text: str) -> str | None:
    """The State a line such as "Nevada Effective 1/1/30" opens with, by
    the names, aliases and postal suffixes its section heading may take."""
    for name in _STATES:
        if re.match(_state_reference(name) + r"\s+Effective\b", text, re.I):
            return name
    return None


def _effective_line(text: str) -> bool:
    return (
        "effective" in text.lower()
        and "Effective Dates:" not in text
        and len(text) < 400
        and bool(
            re.search(r"payments? levels?", text, re.I)
            or text.lower().startswith("effective ")
            or _state_date_line(text)
        )
    )


def _claimant_line(text: str) -> re.Match[str] | None:
    if len(text) >= 250:
        return None
    return re.search(
        r"(?:^|\s)(Individual|Recipient|Couple)"
        r"(?:\s+payments?)?(?:\s+levels)?"
        r"(?:\s+(?:for|or)\s+.+)?$",
        text,
        re.IGNORECASE,
    )


def _named_states(text: str) -> list[str]:
    text = re.sub(
        r"\b" + _DISTRICT_ALIAS, "District of Columbia", text, flags=re.I
    )
    return [
        name
        for name in _STATES
        if re.search(rf"\b{re.escape(name)}\b", text, re.I)
    ]


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
    definitions: list[int] = []
    charted = False
    table_indexes = {id(table): i for i, table in enumerate(tables)}
    contexts: list[dict[str, Any]] = []

    def visit(element: ET.Element) -> bool:
        """Read one element; return whether to read its children."""
        nonlocal state, claimant, effective_text, dates, definitions, charted
        if element.tag == "table":
            index = table_indexes[id(element)]
            grid = expand_html_table(element)
            if not grid:
                return False
            first = tuple(_blank(c.text) for c in grid[0])
            if any(
                tuple(_blank(c.text) for c in row) == ("Code", "Definition")
                for row in grid[:3]
            ):
                if charted:
                    # Which of the section's earlier charts a later table
                    # defines codes for is not stated, so refuse rather than
                    # apply it to some charts and not others.
                    raise TableStructureError(
                        f"POMS definition table {index} follows a payment "
                        "chart in its State section"
                    )
                definitions.append(index)
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
                        "definitions_table_indexes": list(definitions),
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
                charted = True
            return False
        if element.tag in _BLOCKS:
            # Only the block's own text: a table or heading nested under a
            # heading left open is read in turn, not as part of it.
            text = _own_text(element)
            # HTML keeps other blocks inside a heading left open, after its
            # words or around them, and a br breaks a line, so a block is
            # also read line by line. Its whole text comes first. Every line
            # passes the State guards, but a whole-text State date line stays
            # a date line: its lines do not head a section.
            lines = _lines(element)
            candidates = [text, *lines]
            heading_lines = [text] if _state_date_line(text) else candidates
            headed = [
                name
                for name in _STATES
                if any(_state_heading(name, line) for line in heading_lines)
            ]
            if len(headed) > 1:
                raise TableStructureError("POMS heading names two States")
            if headed and state != headed[0]:
                state = headed[0]
                claimant = None
                effective_text = ""
                dates = ()
                definitions = []
                charted = False
            if any(_misnamed_heading(line) for line in candidates):
                # A line shaped as a State heading whose postal code is not
                # its State's heads no section, so its section was not read.
                raise TableStructureError(
                    "POMS heading names a State it does not head"
                )
            # Every line is checked, so a date line nested in a heading
            # cannot carry another State's date into this section, and an
            # effective-date sentence may name no State but this section's.
            if any(
                _state_date_line(line) not in {None, state}
                or state is not None
                and _effective_line(line)
                and set(_named_states(line)) - {state}
                for line in candidates
            ):
                # Definitions are collected per section heading; a State
                # named only in a date line has none of its own, so the
                # reader refuses rather than reuse another State's.
                raise TableStructureError(
                    "POMS State changes without a section heading"
                )
            for line in candidates:
                if _effective_line(line):
                    effective_text = line
                    dates = tuple(
                        dict.fromkeys(
                            _date_string(m[0]) for m in _DATE.finditer(line)
                        )
                    )
                    break
            matches = []
            for line in candidates:
                match = _claimant_line(line)
                if not match:
                    continue
                # Every claimant line is guarded, not only the first, so a
                # block's whole text cannot cover a line nested in it, and a
                # line may name no State but this section's.
                if state is not None and set(_named_states(line)) - {state}:
                    # The section heading that should have named this State
                    # was not read, so refuse rather than chart it under the
                    # State before it.
                    raise TableStructureError(
                        "POMS claimant line names another State"
                    )
                matches.append(match)
            if matches:
                claimant = (
                    "couple"
                    if matches[0][1].lower() == "couple"
                    else "individual"
                )
            if (
                element.tag in _HEADINGS
                and state is not None
                and lines
                and set(_named_states(lines[0])) - {state}
            ):
                # A heading's own first words name a State in a form no
                # section heading takes, so its section was not read.
                raise TableStructureError(
                    "POMS heading names a State it does not head"
                )
        return True

    # Document order without recursion, so deep nesting cannot exhaust the
    # interpreter stack.
    pending = [document]
    while pending:
        element = pending.pop()
        if visit(element):
            pending.extend(list(element)[::-1])
    return tuple(contexts)


def _payment_rows(table: ET.Element) -> tuple[tuple[CellToken, ...], ...]:
    """Split publisher-stacked subrows while reusing the shared span logic."""
    # The span logic reads a skeleton of the table whose cells hold only a
    # key to the original cell. It is built without recursion, as deepcopy
    # is not, so a deeply nested cell cannot crash the interpreter.
    lookup = {}
    skeleton = ET.Element(table.tag, table.attrib)
    pending = [(table, skeleton)]
    while pending:
        original, copy = pending.pop()
        for child in original:
            node = ET.SubElement(copy, child.tag, child.attrib)
            if child.tag in {"td", "th"}:
                node.text = f"poms-cell-{len(lookup)}"
                lookup[node.text] = child
            else:
                pending.append((child, node))
    rows = []
    for row in expand_html_table(skeleton):
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
    """Return cited State OS code definitions from the same verified section.

    A State's definitions may span several physical tables. Each table is
    read in full and the tables are merged; a code two tables define
    differently raises rather than choosing either definition. A row that
    defines codes jointly, such as "C/H", defines each code it names, and a
    full-width note row defines no code.
    """
    verify_payload(spec, payload)
    _, tables = _document(payload)
    indexes = spec.selector.get("definitions_table_indexes")
    if not indexes:
        raise TableStructureError("POMS definition table is not identified")
    merged: dict[str, str] = {}
    for index in indexes:
        for published, definition in _definitions_table(tables[index]).items():
            for code in poms_code_alternatives(published):
                if merged.get(code, definition) != definition:
                    raise TableStructureError(
                        "POMS living-arrangement code has conflicting "
                        "definitions"
                    )
                merged[code] = definition
    return merged


def poms_code_alternatives(code: str) -> tuple[str, ...]:
    """Return the single State OS codes that a published code names.

    POMS writes some codes jointly: a definition row "C/H" defines both C
    and H, and a chart row "A or B" pays either code the same amount. Any
    other code, joint or not, is returned unchanged.
    """
    parts = tuple(re.split(r"\s*/\s*|\s+or\s+", code.strip()))
    if len(parts) > 1 and all(re.fullmatch(r"[A-Z]", part) for part in parts):
        return parts
    return (code,)


def _definitions_table(table: ET.Element) -> dict[str, str]:
    grid = expand_html_table(table)
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
    physical_rows = list(table.iter("tr"))
    for row_index, row in enumerate(
        grid[header_index + 1 :], header_index + 1
    ):
        code = _blank(row[0].text)
        definition = _blank(row[1].text)
        cells = [
            cell
            for cell in physical_rows[row_index]
            if cell.tag in {"td", "th"}
        ]
        if len(cells) == 1 and int(cells[0].get("colspan", "1")) >= 2:
            # A full-width row is a note on the table, not a code.
            continue
        if not code and previous:
            definitions[previous] += " " + definition
            continue
        if code == previous and len(cells) == 1:
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
