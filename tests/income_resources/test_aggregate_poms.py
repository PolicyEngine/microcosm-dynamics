"""Structure and arithmetic checks against the pinned public POMS captures.

The committed files under data/external are public parameter documentation.
Assertions and failures disclose identifiers and structure only.
"""

import json
import re
from collections import defaultdict
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest

from populace_dynamics.income_resources.aggregate_poms import (
    _STATES,
    describe_poms_tables,
    poms_code_alternatives,
    poms_living_arrangements,
)
from populace_dynamics.income_resources.aggregate_tables import (
    load_registry,
    parse_table,
    read_verified,
)

RAW_BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6"}


class RawPomsCells(HTMLParser):
    """Independent physical-cell locator; it does not use the table parser.

    It also records, in document order, each table and the text of each
    paragraph or heading outside a table. A block ends at its end tag or at
    the next block or table, as an unclosed paragraph does in HTML.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.events = []
        self.active = False
        self.row = None
        self.parts = None
        self.sup = 0
        self.block = None

    def _end_block(self):
        if self.block is not None:
            self.events.append(
                ("block", " ".join("".join(self.block).split()))
            )
            self.block = None

    def handle_starttag(self, tag, attrs):
        if tag in RAW_BLOCKS and not self.active:
            self._end_block()
            self.block = []
        if tag == "table":
            self._end_block()
            self.events.append(("table", len(self.tables)))
            self.tables.append([])
            self.active = True
        elif tag == "tr" and self.active:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.parts = []
        elif tag == "sup":
            self.sup += 1

    def handle_data(self, text):
        if self.parts is not None and not self.sup:
            self.parts.append(text)
        if self.block is not None and not self.active:
            self.block.append(text)

    def handle_endtag(self, tag):
        if tag in RAW_BLOCKS and not self.active:
            self._end_block()
        if tag == "sup":
            self.sup -= 1
        elif tag in {"td", "th"} and self.parts is not None:
            self.row.append(" ".join(self.parts))
            self.parts = None
        elif tag == "tr" and self.row is not None:
            self.tables[-1].append(self.row)
            self.row = None
        elif tag == "table":
            self.active = False

    def close(self):
        super().close()
        self._end_block()


def raw_state_heading(text):
    """The State a section heading names, found without the reader's regex."""
    words = text.strip()
    if len(words) > 2 and words[0].isupper() and words[1] == ".":
        words = words[2:].strip()
    lowered = words.lower()
    for prefix in (
        "description of supplements for the ",
        "description of supplements for ",
        "description of supplements -",
        "description of supplements-",
        "procedure -",
        "procedure-",
    ):
        if lowered.startswith(prefix):
            words = words[len(prefix) :].strip()
            break
    if len(words) > 5 and words[-4] == "(" and words.endswith(")"):
        if words[-3:-1].isalpha() and words[-3:-1].isupper():
            words = words[:-4].strip()
    return next(
        (state for state in _STATES if words.lower() == state.lower()), None
    )


def raw_alternatives(code):
    """Split a joint code ("C/H", "A or B") with string operations."""
    parts = [part.strip() for part in code.replace(" or ", "/").split("/")]
    if len(parts) > 1 and all(
        len(part) == 1 and part.isalpha() and part.isupper() for part in parts
    ):
        return parts
    return [code]


def raw_sections(payload):
    """Map each raw payment chart to its State section's definition tables.

    A section runs from a heading naming a new State to the next heading
    naming another. Every Code/Definition table in it belongs to it, before
    or after a chart.
    """
    locator = RawPomsCells()
    locator.feed(payload.decode("utf-8"))
    locator.close()
    sections = []
    state = None
    for kind, value in locator.events:
        if kind == "block":
            named = raw_state_heading(value)
            if named is not None and named != state:
                state = named
                sections.append({"charts": [], "definitions": []})
            continue
        rows = [
            [" ".join(cell.replace("\u200b", "").split()) for cell in row]
            for row in locator.tables[value]
        ]
        if any(row[:2] == ["Code", "Definition"] for row in rows[:3]):
            sections[-1]["definitions"].append(value)
        if rows and rows[0] and rows[0][0] == "Federal Code":
            sections[-1]["charts"].append(value)
    charts = {
        chart: section["definitions"]
        for section in sections
        for chart in section["charts"]
    }
    return charts, locator.tables


def poms_specs():
    return [
        spec
        for spec in load_registry().values()
        if spec.parser == "poms" and spec.record_kind == "table"
    ]


def _require(condition, structural_message):
    if not condition:
        pytest.fail(structural_message, pytrace=False)


def test_poms_registry_spans_every_requested_annual_section():
    specs = poms_specs()
    assert {spec.selector["nominal_year"] for spec in specs} == set(
        range(1999, 2027)
    )
    assert len(specs) == 777
    assert all(spec.units == ("USD per month",) for spec in specs)
    assert all(spec.selector["section_effective_from"] for spec in specs)
    assert all(spec.selector["definitions_table_indexes"] for spec in specs)
    for spec in specs:
        assert Path(spec.capture_file).is_relative_to(
            Path("data") / "external"
        )
        read_verified(spec)


@pytest.mark.parametrize("nominal_year", range(1999, 2027))
def test_poms_payment_shape_headers_years_and_component_identities(
    nominal_year,
):
    specs = [
        spec
        for spec in poms_specs()
        if spec.selector["nominal_year"] == nominal_year
    ]
    assert specs
    for spec in specs:
        cells = parse_table(spec)
        assert cells, spec.identifier
        columns = [
            label or f"Unlabelled amount column {index + 1}"
            for index, label in enumerate(spec.selector["header_labels"])
            if index >= 3
        ]
        columns = spec.selector.get("column_labels", columns)
        assert set(cell.column_key for cell in cells) == set(columns)
        assert len(cells) % len(columns) == 0
        assert len({(c.row_key, c.column_key) for c in cells}) == len(cells)
        assert all(c.unit == "USD per month" for c in cells)
        assert all(c.year in spec.years or c.year is None for c in cells)
        assert all("State OS code=" in c.row_key for c in cells)
        assert all("Category=" in c.row_key for c in cells)
        rows = defaultdict(list)
        for cell in cells:
            rows[cell.row_key].append(cell)
        discrepancies = []
        for key, row in rows.items():
            if (
                len(row) != 3
                or "Total Payment Level" not in row[-1].column_key
                or any(c.value is None for c in row)
            ):
                continue
            reconciles = abs(
                row[0].value + row[1].value - row[2].value
            ) <= Decimal("0.02")
            flagged = all(
                "published_identity_discrepancy" in c.footnote_flags
                for c in row
            )
            _require(reconciles != flagged, spec.identifier)
            if flagged:
                discrepancies.append(key)
        assert discrepancies == spec.selector.get(
            "published_identity_discrepancies", []
        ), spec.identifier


def test_poms_first_payment_cell_matches_independently_located_raw_html():
    raw_by_file = {}
    for spec in poms_specs():
        if spec.capture_file not in raw_by_file:
            raw = RawPomsCells()
            raw.feed(read_verified(spec).decode("utf-8"))
            raw_by_file[spec.capture_file] = raw.tables
        tables = raw_by_file[spec.capture_file]
        physical_rows = tables[spec.selector["table_index"]]
        match = next(
            (
                candidate
                for row in physical_rows[1:]
                if len(row) >= 4
                and (
                    candidate := re.match(
                        r"\s*\$?([+-]?\d[\d,]*(?:\.\d*)?)", row[3]
                    )
                )
            ),
            None,
        )
        _require(match is not None, spec.identifier)
        independently_located = Decimal(match[1].replace(",", ""))
        parsed = parse_table(spec)[0]
        if parsed.value != independently_located:
            pytest.fail(
                f"Raw-cell comparison differs: {spec.identifier}",
                pytrace=False,
            )


def test_poms_living_arrangement_codes_are_available_from_verified_sections():
    for spec in poms_specs():
        definitions = poms_living_arrangements(spec, read_verified(spec))
        _require(bool(definitions), spec.identifier)
        _require(
            all(
                code and definition for code, definition in definitions.items()
            ),
            spec.identifier,
        )


def _chart_codes(spec):
    return {
        cell.row_key.split("State OS code=", 1)[1].split(" | ", 1)[0]
        for cell in parse_table(spec)
    }


def _open_questions():
    path = (
        Path("data")
        / "external"
        / "snapshots"
        / "income_resources_d4_v1"
        / "poms_open_questions.json"
    )
    return json.loads(path.read_text())


def test_poms_chart_codes_resolve_or_are_recorded_as_open_questions():
    """Every chart code is defined, or its absence is a recorded question.

    A jointly published chart code ("A or B") resolves when each code it
    names is defined. The recorded charts publish codes that no definition
    table in their section defines; nothing infers a definition for them.
    """
    recorded = {
        entry["table"]: entry["undefined_living_arrangement_codes"]
        for entry in _open_questions()
        if "undefined_living_arrangement_codes" in entry
    }
    undefined = {}
    for spec in poms_specs():
        definitions = poms_living_arrangements(spec, read_verified(spec))
        named = {
            code
            for published in _chart_codes(spec)
            for code in poms_code_alternatives(published)
        }
        if named - set(definitions):
            undefined[spec.identifier] = sorted(named - set(definitions))
    _require(undefined == recorded, "undefined chart codes differ")
    assert len(recorded) == 15
    assert {identifier.split("_")[4] for identifier in recorded} == {
        "iowa",
        "pennsylvania",
    }


def test_poms_2004_california_definitions_span_both_published_tables():
    """Regression: the reader once kept only the last definition table."""
    specs = [
        spec
        for spec in poms_specs()
        if spec.selector["nominal_year"] == 2004
        and spec.selector["state"] == "California"
    ]
    assert len(specs) == 2
    for spec in specs:
        assert spec.selector["definitions_table_indexes"] == [1, 2]
        definitions = poms_living_arrangements(spec, read_verified(spec))
        assert set("ABCDEF") <= set(definitions)
        assert set("GJYZ") <= set(definitions)
        _require(_chart_codes(spec) <= set(definitions), spec.identifier)


def test_poms_definition_codes_match_independently_located_raw_html():
    """Sections, charts and definition tables are located independently.

    The raw locator finds each chart's State section and every definition
    table in it, without the reader's selectors. Its tables must equal both
    the registry's and the reader's, and its codes the reader's mapping.
    """
    raw = {}
    described = {}
    for spec in poms_specs():
        payload = read_verified(spec)
        if spec.capture_file not in raw:
            raw[spec.capture_file] = raw_sections(payload)
            described[spec.capture_file] = {
                selector["table_index"]: selector
                for selector in describe_poms_tables(payload)
            }
        charts, tables = raw[spec.capture_file]
        index = spec.selector["table_index"]
        _require(index in charts, spec.identifier)
        for selector in (spec.selector, described[spec.capture_file][index]):
            _require(
                charts[index] == selector["definitions_table_indexes"],
                spec.identifier,
            )
        raw_codes = set()
        for table in charts[index]:
            rows = tables[table]
            header = next(
                i
                for i, row in enumerate(rows)
                if [cell.strip() for cell in row[:2]] == ["Code", "Definition"]
            )
            for row in rows[header + 1 :]:
                code = " ".join(row[0].replace("\u200b", "").split())
                if len(row) >= 2 and code:
                    raw_codes.update(raw_alternatives(code))
        definitions = poms_living_arrangements(spec, payload)
        _require(raw_codes == set(definitions), spec.identifier)
    by_capture = defaultdict(set)
    for spec in poms_specs():
        by_capture[spec.capture_file].add(spec.selector["table_index"])
    for capture_file, registered in by_capture.items():
        _require(set(raw[capture_file][0]) == registered, capture_file)


def test_poms_registry_selectors_match_the_structural_reader():
    specs = poms_specs()
    by_capture = defaultdict(dict)
    for spec in specs:
        by_capture[spec.capture_file][spec.selector["table_index"]] = spec
    for capture_file, registered in by_capture.items():
        described = {
            selector["table_index"]: selector
            for selector in describe_poms_tables(
                read_verified(next(iter(registered.values())))
            )
        }
        _require(set(described) == set(registered), capture_file)
        for index, spec in registered.items():
            _require(
                all(
                    spec.selector[key] == value
                    for key, value in described[index].items()
                ),
                spec.identifier,
            )
            state = spec.selector["state"]
            _require(spec.geography == (state,), spec.identifier)
            _require(
                f"_{state.lower().replace(' ', '_')}_" in spec.identifier,
                spec.identifier,
            )


def test_poms_chart_state_agrees_with_its_effective_date_text():
    """A chart's state matches the one State its date sentence names.

    Regression: the 2009 and 2010 headings "New Jersey (NJ)" were not
    recognized, so four New Jersey charts were attributed to Nevada.
    """
    checked = 0
    for spec in poms_specs():
        text = spec.selector["parameter_effective_date_text"]
        named = {
            state
            for state in _STATES
            if re.search(r"\b" + re.escape(state) + r"\b", text)
        }
        if len(named) == 1:
            checked += 1
            _require(named == {spec.selector["state"]}, spec.identifier)
    assert checked == 775
    relabeled = {
        spec.identifier
        for spec in poms_specs()
        if spec.selector["nominal_year"] in {2009, 2010}
        and spec.selector["state"] == "New Jersey"
    }
    assert relabeled == {
        "poms_si_01415_2009_new_jersey_individual_t33",
        "poms_si_01415_2009_new_jersey_couple_t34",
        "poms_si_01415_2010_new_jersey_individual_t35",
        "poms_si_01415_2010_new_jersey_couple_t36",
    }


def test_poms_open_question_dates_match_registry_selectors():
    specs = {spec.identifier: spec for spec in poms_specs()}
    entries = [entry for entry in _open_questions() if "date_options" in entry]
    assert len(entries) == 2
    for entry in entries:
        spec = specs[entry["table"]]
        assert spec.selector["date_options"] == entry["date_options"]
        assert spec.selector["effective_from"] is None
