"""Structure and arithmetic checks against the pinned public POMS captures.

The committed files under data/external are public parameter documentation.
Assertions and failures disclose identifiers and structure only.
"""

import re
from collections import defaultdict
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest

from populace_dynamics.income_resources.aggregate_poms import (
    poms_living_arrangements,
)
from populace_dynamics.income_resources.aggregate_tables import (
    load_registry,
    parse_table,
    read_verified,
)


class RawPomsCells(HTMLParser):
    """Independent physical-cell locator; it does not use the table parser."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.active = False
        self.row = None
        self.parts = None
        self.sup = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
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

    def handle_endtag(self, tag):
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
    assert all(
        spec.selector["definitions_table_index"] is not None for spec in specs
    )
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


def test_poms_latest_california_living_arrangement_codes_resolve():
    specs = [
        spec
        for spec in poms_specs()
        if spec.selector["nominal_year"] == 2026
        and spec.selector["state"] == "California"
    ]
    _require(bool(specs), "Latest California payment tables are present")
    for spec in specs:
        definitions = poms_living_arrangements(spec, read_verified(spec))
        codes = {
            cell.row_key.split("State OS code=", 1)[1].split(" | ", 1)[0]
            for cell in parse_table(spec)
        }
        _require(codes <= set(definitions), spec.identifier)
