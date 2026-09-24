"""The Census threshold capture parser, exercised on INVENTED workbooks.

The Census spreadsheets (``thresh04.xlsx`` ... ``thresh12.xlsx``) were not
downloaded by the builder, so these workbooks are INVENTED in the layout
the parser expects (a title naming the year, a weighted-average column,
children columns "None" ... "Eight or more", and the eleven size rows).
Every threshold below is made up; none is a Census value.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import openpyxl
import pytest

from populace_dynamics.estimates import adjusted_poverty as ap

ROOT = Path(__file__).resolve().parents[2]


def _script():
    path = ROOT / "scripts" / "capture_track_u_parameters.py"
    spec = importlib.util.spec_from_file_location("capture_track_u", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHILD_HEADERS = [
    "None",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight or more",
]


def _invented_rows(year: int, *, drop: str | None = None) -> list[list]:
    """INVENTED threshold table: base 1000 + 100 * size, minus 10/child."""

    rows = [
        [f"Poverty Thresholds for {year} by Size of Family (INVENTED)"],
        [],
        ["Size of family unit", "Weighted average thresholds", "Related"],
        [None, None, *CHILD_HEADERS],
    ]

    def cells(base: float, columns: int) -> list:
        return [base - 10 * k for k in range(columns)]

    rows.append(["One person (unrelated individual).......", 1050])
    rows.append(["  Under 65 years.........", 1100, *cells(1110, 1)])
    rows.append(["  65 years and over......", 1000, *cells(1010, 1)])
    rows.append(["Two people.......", 1350])
    rows.append(["  Householder under 65 years....", 1400, *cells(1410, 2)])
    rows.append(["  Householder 65 years and over.", 1300, *cells(1310, 2)])
    words = ["Three", "Four", "Five", "Six", "Seven", "Eight"]
    for size, word in enumerate(words, start=3):
        base = 1000 + 300 * size
        rows.append(
            [f"{word} people.....", base, *cells(base + 5, min(size, 9))]
        )
    rows.append(["Nine people or more...", 4000, *cells(4005, 9)])
    if drop is not None:
        rows = [
            row for row in rows if not (row and str(row[0]).startswith(drop))
        ]
    return rows


def _write(path: Path, rows: list[list]) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "INVENTED"
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def test_parser_reads_an_invented_table():
    module = _script()
    parsed = module.parse_threshold_rows(_invented_rows(2010), 2010)
    weighted = parsed["weighted_average"]
    assert weighted["one_65_plus"] == 1000
    assert weighted["two_under_65"] == 1400
    assert weighted["three"] == 1900
    assert weighted["nine_plus"] == 4000
    assert parsed["matrix"]["four"] == {0: 2205, 1: 2195, 2: 2185, 3: 2175}
    assert sorted(parsed["matrix"]["nine_plus"]) == list(range(9))
    assert parsed["matrix"]["two_65_plus"] == {0: 1310, 1: 1300}


@pytest.mark.parametrize(
    "rows, message",
    [
        (lambda: _invented_rows(2010), "title"),
        (lambda: _invented_rows(2011, drop="Five"), "rows missing"),
    ],
)
def test_parser_refuses_unrecognized_layouts(rows, message):
    module = _script()
    with pytest.raises(ValueError, match=message):
        module.parse_threshold_rows(rows(), 2011)


def test_parser_refuses_a_nonmonotone_table():
    module = _script()
    rows = _invented_rows(2010)
    for row in rows:
        if row and str(row[0]).startswith("Four"):
            row[1] = 100
    with pytest.raises(ValueError, match="increasing"):
        module.parse_threshold_rows(rows, 2010)


def test_capture_round_trips_through_the_loader(tmp_path):
    module = _script()
    for year in module.YEARS:
        _write(tmp_path / f"thresh{year % 100:02d}.xlsx", _invented_rows(year))
    capture = module.build_threshold_capture(tmp_path)
    assert capture["sources"]["2004"]["url"].endswith("thresh04.xlsx")
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(capture, indent=2) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    thresholds = ap.load_poverty_thresholds(path, expected_sha256=digest)
    assert ap.threshold_for(
        thresholds, 2012, 2, 0, "census_weighted_average_65plus"
    ) == (1300.0, "two_65_plus")
    with pytest.raises(ap.AdjustedPovertyError, match="sha256"):
        ap.load_poverty_thresholds(path, expected_sha256="0" * 64)
