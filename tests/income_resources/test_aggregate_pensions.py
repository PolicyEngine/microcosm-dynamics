"""Real aggregate captures and clearly INVENTED workbook/CSV fixtures.

No survey microdata are read. Assertions involving published values use
boolean helpers so failures disclose table structure only. Artifact reads
are confined to data/external snapshots.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import openpyxl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.income_resources.aggregate_pensions import (
    parse_dol,
    parse_fed,
    parse_irs,
)
from populace_dynamics.income_resources.aggregate_tables import (
    AggregateCell,
    CaptureMismatchError,
    TableSpec,
    TableStructureError,
    load_registry,
    parse_table,
    read_verified,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = (
    ROOT
    / "data"
    / "external"
    / "snapshots"
    / "income_resources_d4_v1"
    / "pensions_registry.json"
)
PENSION_SPECS = tuple(
    TableSpec(
        **{
            **entry,
            **{k: tuple(entry[k]) for k in ("units", "years", "geography")},
        }
    )
    for entry in json.loads(REGISTRY_PATH.read_text())
)
TABLE_SPECS = tuple(s for s in PENSION_SPECS if s.record_kind == "table")


def _require(condition: bool, structure: str) -> None:
    if not condition:
        pytest.fail(structure, pytrace=False)


def _invented_spec(payload: bytes, parser: str, selector: dict) -> TableSpec:
    return TableSpec(
        "INVENTED_PENSION_TABLE",
        "INVENTED publisher",
        "INVENTED edition",
        "https://example.invalid/INVENTED",
        "INVENTED_unused",
        hashlib.sha256(payload).hexdigest(),
        len(payload),
        "2026-01-01T00:00:00Z",
        ("usd", "percent", "taxpayers"),
        (2023,),
        ("INVENTED geography",),
        parser,
        "report_only_wp8",
        selector,
    )


def _invented_workbook(number: int = 12345) -> tuple[bytes, dict]:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "INVENTED"
    sheet.append(["INVENTED row", "INVENTED group [1] 3", None, None])
    sheet.merge_cells("B1:D1")
    sheet.append([None, "Taxpayers", "Amount", "Share"])
    sheet.append(["INVENTED category [2]", number, 0, 0.25])
    sheet.append(["INVENTED missing category", "N/A", "*/", "**/"])
    sheet.append(["INVENTED combined estimate", 0, number, 0.5])
    sheet["B3"].number_format = '"* "#,##0'
    sheet["C3"].number_format = '"** "#,##0;;"**"'
    sheet["D3"].number_format = "0.0%"
    sheet["D5"].number_format = "0.0%"
    sheet["C5"].number_format = '"** "#,##0'
    out = io.BytesIO()
    book.save(out)
    selector = {
        "regions": [
            {
                "sheet": "INVENTED",
                "header_rows": [1, 2],
                "data_rows": [3, 4, 5],
                "columns": [2, 3, 4],
                "column_units": {
                    "2": "taxpayers",
                    "3": "usd",
                    "4": "percent",
                },
                "year": 2023,
            }
        ]
    }
    return out.getvalue(), selector


@pytest.mark.parametrize("spec", PENSION_SPECS, ids=lambda s: s.identifier)
def test_pension_capture_identity(spec):
    raw = read_verified(spec, ROOT)
    assert len(raw) == spec.byte_size
    assert hashlib.sha256(raw).hexdigest() == spec.sha256


@pytest.mark.parametrize("spec", TABLE_SPECS, ids=lambda s: s.identifier)
def test_pension_real_capture_shape_labels_units_years(spec):
    cells = parse_table(spec, ROOT)
    assert cells
    assert all(isinstance(cell, AggregateCell) for cell in cells)
    assert {cell.table for cell in cells} == {spec.identifier}
    assert all(cell.row_key and cell.column_key for cell in cells)
    assert {cell.unit for cell in cells} <= set(spec.units)
    assert {cell.year for cell in cells} <= set(spec.years)
    keys = [(c.row_key, c.column_key, c.year) for c in cells]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    "parser", [parse_dol, parse_irs, parse_fed], ids=["dol", "irs", "fed"]
)
def test_pension_public_readers_refuse_hash_drift(parser):
    payload, selector = _invented_workbook()
    spec = _invented_spec(payload, "dol", selector)
    with pytest.raises(CaptureMismatchError, match="identity mismatch"):
        parser(spec, payload + b"INVENTED drift")


@pytest.mark.parametrize("parser", [parse_dol, parse_irs], ids=["dol", "irs"])
def test_invented_workbook_merged_headers_suppression_and_format_flags(parser):
    payload, selector = _invented_workbook()
    cells = parser(_invented_spec(payload, "dol", selector), payload)
    assert len(cells) == 9
    assert all("INVENTED group [1]" in c.column_key for c in cells)
    _require(cells[0].value == Decimal(12345), "INVENTED estimate magnitude")
    assert set(cells[0].footnote_flags) == {"*", "1", "2", "3"}
    assert cells[1].value is None
    assert "suppressed" in cells[1].footnote_flags
    _require(cells[2].value == Decimal(25), "INVENTED percent scale")
    assert all(c.value is None for c in cells[3:6])
    assert "below_reporting_threshold" in cells[4].footnote_flags
    _require(cells[6].value == 0, "INVENTED published zero preserved")
    _require(cells[7].value == Decimal(12345), "INVENTED combined estimate")
    assert "**" in cells[7].footnote_flags


@given(st.integers(min_value=1, max_value=10**9))
@settings(deadline=None, max_examples=30)
def test_invented_workbook_estimate_marker_preserves_number(number):
    payload, selector = _invented_workbook(number)
    cells = parse_irs(_invented_spec(payload, "irs", selector), payload)
    _require(cells[0].value == Decimal(number), "INVENTED estimate marker")
    assert cells[1].value is None


def test_invented_fed_duplicate_series_remain_positional():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("INVENTED.csv", "date,X.Q,X.Q\n2023:Q1,1,ND\n")
        archive.writestr(
            "INVENTED.txt",
            "X.Q\tINVENTED first\tLine 1\tINVENTED table\tusd\n"
            "X.Q\tINVENTED repeated\tLine 2\tINVENTED table\tusd\n",
        )
    payload = output.getvalue()
    spec = _invented_spec(
        payload,
        "fed",
        {"csv_member": "INVENTED.csv", "dictionary_member": "INVENTED.txt"},
    )
    cells = parse_fed(spec, payload)
    assert len(cells) == 2
    assert cells[0].row_key != cells[1].row_key
    _require(cells[0].value == 1, "INVENTED first dictionary position")
    assert cells[1].value is None


@pytest.mark.parametrize("field", ["units", "years"])
def test_invented_workbook_refuses_registry_coverage_drift(field):
    payload, selector = _invented_workbook()
    spec = _invented_spec(payload, "irs", selector)
    spec = replace(spec, **{field: ()})
    with pytest.raises(TableStructureError, match="coverage"):
        parse_irs(spec, payload)


def test_fed_pension_liability_sector_components_reconcile():
    grouped = defaultdict(dict)
    for cell in parse_table("FED_Z1_F6.2.s", ROOT):
        line = int(cell.row_key.split(" | ")[0].split()[-1])
        grouped[cell.column_key][line] = cell.value
    checked = 0
    for lines in grouped.values():
        values = [lines[line] for line in range(1, 7)]
        if all(value is not None for value in values):
            checked += 1
            _require(
                abs(values[0] - sum(values[1:])) <= 3,
                "Z.1 pension liability/sector component identity",
            )
    assert checked


def test_dol_a1_plan_type_components_reconcile_with_rounding():
    cells = parse_table("DOL_PPPB_2023_A1", ROOT)
    by_row = {}
    for cell in cells:
        label = cell.row_key.split(": ", 1)[1]
        by_row.setdefault(label, {})[cell.column_key] = cell.value
    for col in by_row["Total"]:
        total = by_row["Total"][col]
        components = [
            by_row[label][col]
            for label in ("Defined Benefit", "Defined Contribution")
        ]
        _require(
            total is not None
            and all(c is not None for c in components)
            and abs(total - sum(components)) <= 2,
            "DOL A1 total/plan-type component identity",
        )


def test_irs_ira_amount_components_reconcile_with_rounding():
    cells = parse_table("IRS_IRA_2023_1", ROOT)
    groups = {}
    for cell in cells:
        if cell.unit == "thousand_usd":
            groups.setdefault(cell.column_key, []).append(cell.value)
    for values in groups.values():
        known = [v for v in values[1:] if v is not None]
        _require(
            values[0] is not None and abs(values[0] - sum(known)) <= 3,
            "IRS IRA Table 1 amount total/plan-type identity",
        )


def test_irs_workbook_cells_match_independent_raw_xml():
    spec = load_registry(ROOT)["IRS_IRA_2023_1"]
    payload = read_verified(spec, ROOT)
    cells = parse_irs(spec, payload)
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        tree = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    raw = tree.find(".//s:c[@r='B6']/s:v", ns)
    assert raw is not None
    _require(cells[0].value == Decimal(raw.text), "IRS raw XML differential")


def test_fed_csv_cell_matches_independent_positional_read():
    spec = load_registry(ROOT)["FED_Z1_F6.2.s"]
    payload = read_verified(spec, ROOT)
    cells = parse_fed(spec, payload)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        reader = csv.reader(
            io.StringIO(archive.read(spec.selector["csv_member"]).decode())
        )
        next(reader)
        first = next(reader)
    if first[1] == "ND":
        assert cells[0].value is None
    else:
        _require(cells[0].value == Decimal(first[1]), "Z.1 CSV differential")
